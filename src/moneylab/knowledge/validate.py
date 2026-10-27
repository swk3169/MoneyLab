"""Deterministic validator for knowledge records (15 preregistered rules, WORK_ORDER VALIDATOR_CONTRACT).

Nothing is repaired, dropped or inferred: every violation becomes a Problem(rule, record_id, message), sorted.
Source checks (rule 13) read committed blob bytes through git (`git cat-file blob HEAD:<path>`), so line-ending
conversion in a checkout does not matter. Without git the source checks cannot run; the result is then
SOURCE_UNVERIFIED, never a silent pass."""

from __future__ import annotations

import hashlib
import re
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from moneylab.knowledge.load import LoadResult
from moneylab.knowledge.model import (
    COMMIT_RE,
    ENVELOPE_FIELDS,
    EVIDENCE_AVAILABILITY,
    EVIDENCE_FIELDS,
    EXTERNAL_LOCATOR_RE,
    GITHUB_LOCATOR_RE,
    ID_RE,
    LAYER_RANK,
    PAYLOAD_ENUMS,
    PAYLOAD_FIELDS,
    PROVENANCE_CLASSES,
    SCHEMA,
    SHA256_RE,
    TOPICS,
    Record,
    canonical_json,
    record_path,
)

# Same patterns as tests/test_repo_hygiene.py SECRET_PATTERNS (a test checks that the two lists are equal).
SECRET_PATTERNS = [
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("aws access key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("github token", r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    ("slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ("anthropic/openai key", r"\bsk-(ant-)?[A-Za-z0-9_-]{20,}"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ("assigned secret", r"(?i)[a-z0-9_]*(secret|api[_-]?key|access[_-]?key|token|password|passwd)[a-z0-9_]*"
                        r"\s*[:=]\s*['\"][A-Za-z0-9/+_.=-]{16,}['\"]"),
    ("personal email", r"[\w.+-]+@(gmail|naver|daum|hanmail|kakao|outlook|hotmail|yahoo)\.[a-z.]+"),
    ("user home path", r"(?i)\b[a-z]:[\\/]+users[\\/]+[^\\/\s'\"]+"),
]
ABSOLUTE_PATH_PATTERNS = [
    ("windows drive path", r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]"),
    ("unc path", r"\\\\"),
    ("absolute posix path", r"(?:^|[\s'\"(=,;])/(?!\s)"),
    ("home-relative path", r"(?:^|[\s'\"(=,;])~[\\/]"),
    ("local file uri", r"(?i)\bfile:/"),
]

VERIFIED, SOURCE_UNVERIFIED, NO_SOURCES = "VERIFIED", "SOURCE_UNVERIFIED", "NO_SOURCES"


@dataclass(frozen=True, order=True)
class Problem:
    rule: int
    record_id: str
    message: str


@dataclass(frozen=True)
class Report:
    problems: tuple[Problem, ...]
    source_status: str
    unverified: tuple[str, ...]
    invalid_ids: frozenset[str]

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def exit_code(self) -> int:
        if self.problems:
            return 1
        return 3 if self.source_status == SOURCE_UNVERIFIED else 0

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "exit_code": self.exit_code, "source_status": self.source_status,
                "problems": [{"rule": p.rule, "record_id": p.record_id, "message": p.message} for p in self.problems],
                "unverified": list(self.unverified)}


class Git:
    """Read-only git access to committed objects of one repository."""

    def __init__(self, root: Path, enabled: bool = True) -> None:
        self.root = Path(root)
        self._cache: dict[tuple[str, str], bytes | None] = {}
        out = self._run("rev-parse", "--is-inside-work-tree") if enabled else None
        self.available = out is not None and out.strip() == b"true"

    def _run(self, *args: str) -> bytes | None:
        try:
            proc = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        return proc.stdout if proc.returncode == 0 else None

    def blob(self, rev: str, path: str) -> bytes | None:
        key = (rev, path)
        if key not in self._cache:
            self._cache[key] = self._run("cat-file", "blob", f"{rev}:{path}")
        return self._cache[key]

    def has_commit(self, sha: str) -> bool:
        return self._run("cat-file", "-e", f"{sha}^{{commit}}") is not None

    def tree_of(self, sha: str) -> str | None:
        out = self._run("rev-parse", f"{sha}^{{tree}}")
        return out.decode().strip() if out is not None else None


def _strings(value: Any, where: str) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield where, value
    elif isinstance(value, dict):
        for key in sorted(value):
            yield f"{where}.{key}" if where else str(key), str(key)
            yield from _strings(value[key], f"{where}.{key}" if where else str(key))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from _strings(item, f"{where}[{i}]")


def _is_ascii_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.isascii()


def _id_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) for v in value) and len(set(value)) == len(value)


def _relative_posix(path: Any) -> bool:
    return (isinstance(path, str) and bool(path) and not path.startswith("/") and "\\" not in path
            and ":" not in path and ".." not in path.split("/") and "" not in path.split("/"))


def _evidence_problems(ev: Any, where: str) -> list[str]:
    if not isinstance(ev, dict):
        return [f"{where}: EvidenceRef must be an object"]
    kind = ev.get("type")
    if kind not in EVIDENCE_FIELDS:
        return [f"{where}: unknown EvidenceRef type {kind!r}"]
    required, optional = EVIDENCE_FIELDS[kind]
    out = [f"{where}: missing field {f}" for f in required if f not in ev]
    out += [f"{where}: unknown field {f}" for f in sorted(ev) if f not in required and f not in optional]
    if ev.get("provenance_class") not in PROVENANCE_CLASSES:
        out.append(f"{where}: provenance_class not in {PROVENANCE_CLASSES}")
    if ev.get("availability") not in EVIDENCE_AVAILABILITY[kind]:
        out.append(f"{where}: availability for {kind} must be one of {EVIDENCE_AVAILABILITY[kind]}")
    if kind == "git_blob":
        if not (isinstance(ev.get("rev"), str) and COMMIT_RE.match(ev["rev"])):
            out.append(f"{where}: rev must be a 40-hex commit SHA")
        if not _relative_posix(ev.get("path")):
            out.append(f"{where}: path must be a repository-relative POSIX path")
        if "locator" in ev and ev["locator"] is not None and not isinstance(ev["locator"], str):
            out.append(f"{where}: locator must be a string or null")
    if kind == "github" and not (isinstance(ev.get("locator"), str) and GITHUB_LOCATOR_RE.match(ev["locator"])):
        out.append(f"{where}: github locator must look like github:<owner>/<repo>/pull/<n>")
    if kind == "external" and not (isinstance(ev.get("locator"), str) and EXTERNAL_LOCATOR_RE.match(ev["locator"])):
        out.append(f"{where}: external locator must look like external:<artifact-class>/<relative path>")
    if kind in ("git_blob", "external") and not (isinstance(ev.get("sha256"), str) and SHA256_RE.match(ev["sha256"])):
        out.append(f"{where}: sha256 must be 64 lowercase hex characters")
    return out


def _structure_problems(rec: Record) -> list[str]:
    d = rec.data
    out = [f"missing field {f}" for f in ENVELOPE_FIELDS if f not in d]
    out += [f"unknown field {f}" for f in sorted(d) if f not in ENVELOPE_FIELDS]
    m = ID_RE.match(rec.id)
    if d.get("kind") not in PAYLOAD_FIELDS:
        out.append(f"kind not in {tuple(sorted(PAYLOAD_FIELDS))}")
    elif m and d["kind"] != m.group(1):
        out.append("kind does not match the record ID")
    if d.get("layer") not in LAYER_RANK:
        out.append(f"layer not in {tuple(sorted(LAYER_RANK))}")
    for f in ("title", "statement"):
        if f in d and not _is_ascii_text(d[f]):
            out.append(f"{f} must be a non-empty ASCII string")
    topics = d.get("topics")
    if "topics" in d and not (isinstance(topics, list) and topics and _id_list(topics)
                              and all(t in TOPICS for t in topics)):
        out.append(f"topics must be a non-empty list of distinct values from {TOPICS}")
    for f in ("supersedes", "derived_from"):
        if f in d and not _id_list(d[f]):
            out.append(f"{f} must be a list of distinct record IDs")
    if "labels" in d and not (isinstance(d["labels"], dict)
                              and all(isinstance(k, str) and isinstance(v, str) for k, v in d["labels"].items())):
        out.append("labels must map strings to strings")
    if "evidence" in d:
        if not isinstance(d["evidence"], list):
            out.append("evidence must be a list")
        else:
            for i, ev in enumerate(d["evidence"]):
                out += _evidence_problems(ev, f"evidence[{i}]")
    payload, kind = d.get("payload"), d.get("kind")
    if "payload" in d and kind in PAYLOAD_FIELDS:
        if not isinstance(payload, dict):
            out.append("payload must be an object")
        else:
            fields = PAYLOAD_FIELDS[kind]
            out += [f"payload: missing field {f}" for f in fields if f not in payload]
            out += [f"payload: unknown field {f}" for f in sorted(payload) if f not in fields]
            for (k, f), allowed in PAYLOAD_ENUMS.items():
                if k == kind and f in payload and payload[f] not in allowed:
                    out.append(f"payload.{f} not in {allowed}")
            if kind == "task":
                for f in ("implementation_commit", "merge_commit", "tree"):
                    if f in payload and not (isinstance(payload[f], str) and COMMIT_RE.match(payload[f])):
                        out.append(f"payload.{f} must be 40 lowercase hex characters")
                if "task_id" in payload and payload["task_id"] != rec.namespace:
                    out.append("payload.task_id must equal the record namespace")
            if kind == "decision" and "local_id" in payload and not (
                    payload["local_id"] is None or isinstance(payload["local_id"], str)):
                out.append("payload.local_id must be a string or null")
    if not out and rec.text != canonical_json(d):
        out.append("file is not in canonical JSON form (sort_keys, indent=2, ensure_ascii, trailing newline)")
    return out


def _cycle_members(edges: dict[str, list[str]]) -> set[str]:
    """IDs that lie on a supersession cycle (iterative DFS, deterministic order)."""
    on_cycle: set[str] = set()
    state: dict[str, int] = {}  # 1 = on stack, 2 = done
    for start in sorted(edges):
        if state.get(start):
            continue
        stack: list[tuple[str, Iterator[str]]] = [(start, iter(sorted(edges.get(start, []))))]
        path = [start]
        state[start] = 1
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                state[node] = 2
                stack.pop()
                path.pop()
            elif child in edges and state.get(child) == 1:
                on_cycle.update(path[path.index(child):])
            elif child in edges and not state.get(child):
                state[child] = 1
                path.append(child)
                stack.append((child, iter(sorted(edges.get(child, [])))))
    return on_cycle


def _qualifying(ev: Any) -> bool:
    return (isinstance(ev, dict) and ev.get("type") == "git_blob" and ev.get("provenance_class") == "GIT_VERIFIABLE"
            and ev.get("availability") == "IN_GIT")


def validate(loaded: LoadResult, root: Path, *, use_git: bool = True, full_history: bool = False) -> Report:
    problems: list[Problem] = [Problem(5, issue.path, issue.message) for issue in loaded.issues]
    unverified: list[str] = []

    # rules 14 and 15 apply to every parsed record, whatever else is wrong with it; messages never echo the value
    for rec in loaded.records:
        for where, text in _strings(rec.data, ""):
            for label, pattern in ABSOLUTE_PATH_PATTERNS:
                if re.search(pattern, text):
                    problems.append(Problem(14, rec.id, f"{where or 'value'}: {label}"))
            for label, pattern in SECRET_PATTERNS:
                if re.search(pattern, text):
                    problems.append(Problem(15, rec.id, f"{where or 'value'}: secret-like content ({label})"))

    counts: dict[str, int] = {}
    for rec in loaded.records:
        counts[rec.id] = counts.get(rec.id, 0) + 1
    all_ids = set(counts)
    structured: dict[str, Record] = {}
    for rec in loaded.records:
        if rec.data.get("schema") != SCHEMA:
            problems.append(Problem(1, rec.id, f"unsupported schema {rec.data.get('schema')!r}"))
            continue
        if counts[rec.id] > 1:
            problems.append(Problem(2, rec.id, f"duplicate record ID ({rec.path})"))
            continue
        if not isinstance(rec.data.get("id"), str) or not ID_RE.match(rec.id):
            problems.append(Problem(3, rec.id, "record ID does not match <kind>/<NAMESPACE>/<slug>"))
            continue
        if rec.path != record_path(rec.id):
            problems.append(Problem(4, rec.id, f"path {rec.path} does not match ID (expected {record_path(rec.id)})"))
            continue
        found = _structure_problems(rec)
        problems += [Problem(5, rec.id, msg) for msg in found]
        if not found:
            structured[rec.id] = rec

    # references and supersession graph (over structurally valid records)
    edges: dict[str, list[str]] = {}
    superseders: dict[str, list[str]] = {}
    for rid, rec in sorted(structured.items()):
        for f in ("supersedes", "derived_from"):
            for ref in rec.data[f]:
                if ref not in all_ids:
                    problems.append(Problem(6, rid, f"{f} references nonexistent record {ref}"))
        edges[rid] = [ref for ref in rec.data["supersedes"] if ref in structured]
        for old in edges[rid]:
            superseders.setdefault(old, []).append(rid)
    for rid in sorted(_cycle_members(edges)):
        problems.append(Problem(7, rid, "record lies on a supersession cycle"))
    for old, news in sorted(superseders.items()):
        if len(news) > 1:
            problems.append(Problem(8, old, f"superseded by more than one record: {', '.join(sorted(news))}"))
    for rid, olds in sorted(edges.items()):
        new = structured[rid].data
        for old in olds:
            prev = structured[old].data
            if new["kind"] != prev["kind"]:
                problems.append(Problem(9, rid, f"supersedes {old} of a different kind ({prev['kind']})"))
            if LAYER_RANK[new["layer"]] < LAYER_RANK[prev["layer"]]:
                problems.append(Problem(9, rid, f"{new['layer']} cannot supersede {prev['layer']} record {old}"))

    # epistemic layers
    for rid, rec in sorted(structured.items()):
        d = rec.data
        if d["layer"] == "DERIVED_SUMMARY" and not d["derived_from"]:
            problems.append(Problem(10, rid, "DERIVED_SUMMARY must list at least one record in derived_from"))
        if d["layer"] == "SOURCE_FACT" and not any(_qualifying(ev) for ev in d["evidence"]):
            problems.append(Problem(11, rid, "SOURCE_FACT needs a git_blob / GIT_VERIFIABLE / IN_GIT EvidenceRef"))
        if d["layer"] != "HYPOTHESIS":
            for ref in d["derived_from"]:
                if ref in structured and structured[ref].data["layer"] == "HYPOTHESIS":
                    problems.append(Problem(12, rid, f"{d['layer']} cannot be derived from HYPOTHESIS {ref}"))

    # sources (rule 13)
    git = Git(root, enabled=use_git)
    has_sources = False
    for rid, rec in sorted(structured.items()):
        for i, ev in enumerate(rec.data["evidence"]):
            if ev["type"] != "git_blob":
                continue
            has_sources = True
            where = f"evidence[{i}] {ev['path']}"
            if not git.available:
                unverified.append(f"{rid}: {where}: git unavailable")
                continue
            data = git.blob("HEAD", ev["path"])
            if data is None:
                problems.append(Problem(13, rid, f"{where}: path missing at HEAD"))
            elif hashlib.sha256(data).hexdigest() != ev["sha256"]:
                problems.append(Problem(13, rid, f"{where}: committed blob sha256 at HEAD differs from the record"))
            if full_history:
                if not git.has_commit(ev["rev"]):
                    unverified.append(f"{rid}: {where}: commit {ev['rev']} not available")
                else:
                    at_rev = git.blob(ev["rev"], ev["path"])
                    if at_rev is None or hashlib.sha256(at_rev).hexdigest() != ev["sha256"]:
                        problems.append(Problem(13, rid, f"{where}: blob at rev {ev['rev'][:12]} does not match"))
        if full_history and rec.data["kind"] == "task" and git.available:
            p = rec.data["payload"]
            for f in ("merge_commit", "implementation_commit"):
                if not git.has_commit(p[f]):
                    unverified.append(f"{rid}: payload.{f} {p[f]} not available")
            if git.has_commit(p["merge_commit"]) and git.tree_of(p["merge_commit"]) != p["tree"]:
                problems.append(Problem(13, rid, "payload.tree is not the tree of payload.merge_commit"))

    # Grounding is transitive: a record derived from an invalid record is not validly grounded either (so a
    # HYPOTHESIS cannot be laundered through an invalid intermediate). Only derived_from carries this; supersedes
    # does not. Iterated to a fixed point in ID order.
    invalid = {p.record_id for p in problems}
    changed = True
    while changed:
        changed = False
        for rid, rec in sorted(structured.items()):
            if rid in invalid:
                continue
            bad = sorted(ref for ref in rec.data["derived_from"] if ref in invalid)
            if bad:
                problems.append(Problem(6, rid, f"derived_from depends on invalid record(s): {', '.join(bad)}"))
                invalid.add(rid)
                changed = True

    problems = sorted(set(problems))
    status = (SOURCE_UNVERIFIED if unverified else VERIFIED) if has_sources or unverified else NO_SOURCES
    return Report(tuple(problems), status, tuple(sorted(unverified)), frozenset(p.record_id for p in problems))
