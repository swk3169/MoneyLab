"""Snapshot records (AUTO-02 D9-D12): canonical bytes, storage under the ignored data/processed/workstate,
and validation of one named record.

A record is content-addressed: its file name is `snapshot_id`, the hash of schema, task_id, state and
reported (meta excluded). The canonical-bytes check detects accidental damage and the id/state hashes tie
the content to the name; a valid edit of `meta` cannot be detected without an expected file_sha256 kept
elsewhere. Local hashes prove neither authenticity nor authority."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from moneylab.storage import atomic
from moneylab.workstate import collect
from moneylab.workstate.collect import (LIMIT_EXCEEDED, SNAPSHOT_CORRUPT, SNAPSHOT_INCOMPATIBLE, SNAPSHOT_NOT_FOUND,
                                        SNAPSHOT_UNREADABLE, STORE_FAILED, STORE_PATH_INVALID, WorkstateError)

SNAPSHOT_SCHEMA = "moneylab.workstate.snapshot/1"
TOOL_VERSION = "1"
FILE_LIMIT = 1024 * 1024
STORE_PARTS = ("data", "processed", "workstate")
GATES = ("DESIGN_INVESTIGATION", "CONTRACT_REVIEW", "WORKSPACE_SETUP", "IMPLEMENTATION", "PRECOMMIT_AUDIT",
         "COMMIT", "CLEAN_COMMIT_E2E", "PUSH", "PR_CI", "MERGE", "POST_MERGE_AUDIT", "COMPLETE")
RESULTS = ("PASS", "NO")
TASK_ID_RE = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*")
SNAPSHOT_ID_RE = re.compile(r"[0-9a-f]{64}")
_OID_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_TIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
# Values the collector can produce for a porcelain v2 "1" record (submodule, gitlink and symlink changes are
# refused, renames are off, unmerged entries are "u" records and refused).
_MODES = frozenset({"000000", "100644", "100755"})
_XY_CHARS = frozenset(".MTAD")

TOP_KEYS = frozenset({"schema", "task_id", "snapshot_id", "state_sha256", "state", "reported", "meta"})
STATE_KEYS = frozenset({"branch", "head", "tree", "entries", "untracked", "contract"})
ENTRY_KEYS = frozenset({"path", "xy", "head_mode", "head_blob", "index_mode", "index_blob", "w_sha256", "s_sha256"})
CONTRACT_KEYS = frozenset({"path", "head_sha256", "work_sha256"})
META_KEYS = frozenset({"created_at_utc", "tool_version"})

_mkdir = os.mkdir


def valid_task_id(value: object) -> bool:
    return isinstance(value, str) and len(value) <= 64 and TASK_ID_RE.fullmatch(value) is not None


def valid_snapshot_id(value: object) -> bool:
    return isinstance(value, str) and SNAPSHOT_ID_RE.fullmatch(value) is not None


def canonical_text(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def record_bytes(obj: Any) -> bytes:
    return (canonical_text(obj) + "\n").encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def state_sha256(state: dict[str, Any]) -> str:
    return sha256_hex(canonical_text(state).encode("utf-8"))


def identity(task_id: str, state: dict[str, Any], reported: dict[str, str] | None) -> dict[str, Any]:
    return {"schema": SNAPSHOT_SCHEMA, "task_id": task_id, "state": state, "reported": reported}


def snapshot_id_for(task_id: str, state: dict[str, Any], reported: dict[str, str] | None) -> str:
    return sha256_hex(canonical_text(identity(task_id, state, reported)).encode("utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime(_TIME_FORMAT)


def build_record(task_id: str, state: dict[str, Any], reported: dict[str, str] | None) -> dict[str, Any]:
    return {"schema": SNAPSHOT_SCHEMA, "task_id": task_id, "snapshot_id": snapshot_id_for(task_id, state, reported),
            "state_sha256": state_sha256(state), "state": state, "reported": reported,
            "meta": {"created_at_utc": _now(), "tool_version": TOOL_VERSION}}


def record_rel(task_id: str, snapshot_id: str) -> str:
    return "/".join((*STORE_PARTS, task_id, f"{snapshot_id}.json"))


def _lexically_inside(root: Path, path: Path) -> bool:
    """String boundary of a path built from validated ids: below root, no `..`, no other drive.
    Touches nothing on disk, so it does not depend on which components exist yet."""
    try:
        rel = os.path.relpath(path, root)
    except ValueError:  # another drive
        return False
    parts = Path(rel).parts
    return bool(parts) and not os.path.isabs(rel) and rel != os.curdir and os.pardir not in parts


def _resolved_inside(root: Path, path: Path) -> bool:
    """For an existing path: with links resolved, it must lie strictly below the resolved root."""
    base = os.path.normcase(os.path.realpath(root))
    target = os.path.normcase(os.path.realpath(path))
    try:
        return target != base and os.path.commonpath([base, target]) == base
    except ValueError:  # another drive
        return False


def _inspect_dirs(root: Path, task_id: str) -> int:
    """Check the existing store directories top-down; return the index of the first missing one."""
    parts = (*STORE_PARTS, task_id)
    current = Path(root)
    for index, part in enumerate(parts):
        current = current / part
        shown = "/".join(parts[:index + 1])
        try:
            st = collect._lstat(current)
        except FileNotFoundError:
            return index
        except OSError as exc:
            raise WorkstateError(STORE_PATH_INVALID, f"cannot inspect {shown}: {type(exc).__name__}") from exc
        if collect.is_link_like(current, st):
            raise WorkstateError(STORE_PATH_INVALID, f"link or reparse point: {shown}")
        if not stat.S_ISDIR(st.st_mode):
            raise WorkstateError(STORE_PATH_INVALID, f"not a directory: {shown}")
    return len(parts)


def _read_bytes(path: Path) -> bytes:
    with open(path, "rb") as handle:
        return handle.read(FILE_LIMIT + 1)


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate key {key!r}")
        obj[key] = value
    return obj


def _reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not valid JSON")


def _strings(item: object, keys: frozenset[str]) -> bool:
    return isinstance(item, dict) and set(item) == keys and all(isinstance(v, str) for v in item.values())


def _valid_time(value: str) -> bool:
    """RFC 3339 UTC to the second, and a real calendar date and time (no Feb 30, hour 24 or second 60)."""
    if _TIME_RE.fullmatch(value) is None:
        return False
    try:
        datetime.strptime(value, _TIME_FORMAT)
    except ValueError:
        return False
    return True


def _hash_or_absent(value: str) -> bool:
    return value == collect.ABSENT or _SHA256_RE.fullmatch(value) is not None


def _valid_path(value: object) -> bool:
    """A repository-relative path as git prints it: '/'-separated, no empty, '.' or '..' component, no NUL,
    valid UTF-8 within the collector's length limit."""
    if not isinstance(value, str) or not value or "\0" in value:
        return False
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:  # lone surrogate
        return False
    return size <= collect.MAX_PATH_BYTES and all(part not in ("", ".", "..") for part in value.split("/"))


def _strictly_sorted(paths: list[str]) -> bool:
    """Sorted as the collector sorts (str order) and without duplicates."""
    return all(a < b for a, b in zip(paths, paths[1:]))


def _entry_problem(entry: dict[str, str], oid_len: int) -> str | None:
    if not _valid_path(entry["path"]):
        return "an entry path is malformed"
    xy = entry["xy"]
    if len(xy) != 2 or not set(xy) <= _XY_CHARS or xy == "..":
        return "an entry xy is malformed"
    for side in ("head", "index"):
        if entry[f"{side}_mode"] not in _MODES:
            return f"an entry {side}_mode is malformed"
        blob = entry[f"{side}_blob"]
        if _OID_RE.fullmatch(blob) is None or len(blob) != oid_len:
            return f"an entry {side}_blob is malformed"
    if not _hash_or_absent(entry["w_sha256"]):
        return "an entry w_sha256 is malformed"
    s_sha = entry["s_sha256"]
    if (s_sha == collect.ABSENT) != (entry["index_mode"] == "000000") or not _hash_or_absent(s_sha):
        return "an entry s_sha256 is malformed"
    return None


def _state_problem(state: object, task_id: str) -> str | None:
    if not isinstance(state, dict) or set(state) != STATE_KEYS:
        return "state keys are malformed"
    branch = state["branch"]
    if branch is not None and not (isinstance(branch, str) and branch and branch == branch.strip()
                                   and "\0" not in branch):
        return "branch is malformed"
    for key in ("head", "tree"):
        if not isinstance(state[key], str) or _OID_RE.fullmatch(state[key]) is None:
            return f"{key} is malformed"
    oid_len = len(state["head"])
    if len(state["tree"]) != oid_len:
        return "tree is malformed"
    entries, untracked, contract = state["entries"], state["untracked"], state["contract"]
    if not isinstance(entries, list) or len(entries) > collect.MAX_ENTRIES \
            or not all(_strings(e, ENTRY_KEYS) for e in entries):
        return "entries are malformed"
    for entry in entries:
        problem = _entry_problem(entry, oid_len)
        if problem is not None:
            return problem
    if not _strictly_sorted([e["path"] for e in entries]):
        return "entries are not sorted by path or repeat a path"
    if not isinstance(untracked, list) or len(untracked) > collect.MAX_UNTRACKED \
            or not all(_valid_path(p) for p in untracked):
        return "untracked is malformed"
    if not _strictly_sorted(untracked):
        return "untracked is not sorted or repeats a path"
    if set(untracked) & {e["path"] for e in entries}:
        return "a path is both changed and untracked"
    if not isinstance(contract, list) or len(contract) > collect.MAX_CONTRACT \
            or not all(_strings(c, CONTRACT_KEYS) for c in contract):
        return "contract is malformed"
    prefix = f"docs/tasks/{task_id}/"
    for item in contract:
        if not _valid_path(item["path"]) or not item["path"].startswith(prefix):
            return "a contract path is malformed"
        if not _hash_or_absent(item["head_sha256"]) or not _hash_or_absent(item["work_sha256"]):
            return "a contract hash is malformed"
    if not _strictly_sorted([c["path"] for c in contract]):
        return "contract is not sorted by path or repeats a path"
    return None


def _shape_problem(obj: dict[str, Any]) -> str | None:
    """D11 step 8: key allowlist, types and formats, matching what the collector and build_record produce."""
    if set(obj) != TOP_KEYS:
        return "unexpected top-level keys"
    if not valid_task_id(obj["task_id"]):
        return "task_id is malformed"
    if not valid_snapshot_id(obj["snapshot_id"]) or not valid_snapshot_id(obj["state_sha256"]):
        return "snapshot_id or state_sha256 is malformed"
    reported = obj["reported"]
    if reported is not None and not (_strings(reported, frozenset({"gate", "result"}))
                                     and reported["gate"] in GATES and reported["result"] in RESULTS):
        return "reported is malformed"
    meta = obj["meta"]
    if not _strings(meta, META_KEYS) or not meta["tool_version"] or not _valid_time(meta["created_at_utc"]):
        return "meta is malformed"
    return _state_problem(obj["state"], obj["task_id"])


def parse_record(raw: bytes, task_id: str, snapshot_id: str, file_sha256: str) -> dict[str, Any]:
    """D11 steps 6-8 on bytes already read from `<snapshot_id>.json`."""
    def corrupt(detail: str) -> WorkstateError:
        return WorkstateError(SNAPSHOT_CORRUPT, detail, file_sha256)

    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    except ValueError as exc:  # UnicodeDecodeError and JSONDecodeError included
        raise corrupt("record is not strict UTF-8 JSON") from exc
    if not isinstance(obj, dict):
        raise corrupt("record is not a JSON object")
    schema = obj.get("schema")
    if not isinstance(schema, str):
        raise corrupt("schema is missing")
    if schema != SNAPSHOT_SCHEMA:
        raise WorkstateError(SNAPSHOT_INCOMPATIBLE, "unknown snapshot schema", file_sha256)
    problem = _shape_problem(obj)
    if problem is not None:
        raise corrupt(problem)
    try:
        canonical = record_bytes(obj)
    except ValueError as exc:
        raise corrupt("record cannot be serialized canonically") from exc
    if canonical != raw:
        raise corrupt("record bytes are not canonical")
    expected = snapshot_id_for(obj["task_id"], obj["state"], obj["reported"])
    if obj["snapshot_id"] != expected or snapshot_id != expected:
        raise corrupt("snapshot_id does not match the content or the file name")
    if obj["state_sha256"] != state_sha256(obj["state"]):
        raise corrupt("state_sha256 does not match the state")
    if obj["task_id"] != task_id:
        raise corrupt("task_id does not match")
    return obj


def load_record(root: Path, task_id: str, snapshot_id: str) -> tuple[dict[str, Any], str]:
    """D11 steps 3-8 for exactly one record; returns (record, file_sha256). Creates nothing."""
    first_missing = _inspect_dirs(root, task_id)
    path = Path(root) / record_rel(task_id, snapshot_id)
    if first_missing < len(STORE_PARTS) + 1:
        raise WorkstateError(SNAPSHOT_NOT_FOUND, "no such snapshot")
    try:
        st = collect._lstat(path)
    except FileNotFoundError:
        raise WorkstateError(SNAPSHOT_NOT_FOUND, "no such snapshot") from None
    except OSError as exc:
        raise WorkstateError(SNAPSHOT_UNREADABLE, f"cannot inspect the record: {type(exc).__name__}") from exc
    if collect.is_link_like(path, st) or not _lexically_inside(root, path) or not _resolved_inside(root, path):
        raise WorkstateError(STORE_PATH_INVALID, "the record is a link or outside the root")
    if not stat.S_ISREG(st.st_mode):
        raise WorkstateError(SNAPSHOT_CORRUPT, "the record is not a regular file")
    if st.st_size > FILE_LIMIT:
        raise WorkstateError(SNAPSHOT_CORRUPT, "the record is larger than the limit")
    try:
        raw = _read_bytes(path)
    except OSError as exc:
        raise WorkstateError(SNAPSHOT_UNREADABLE, f"cannot read the record: {type(exc).__name__}") from exc
    if len(raw) > FILE_LIMIT:
        raise WorkstateError(SNAPSHOT_CORRUPT, "the record is larger than the limit")
    file_sha = sha256_hex(raw)
    return parse_record(raw, task_id, snapshot_id, file_sha), file_sha


def _create(root: Path, record: dict[str, Any], data: bytes, path: Path) -> dict[str, Any]:
    task_id, snapshot_id = record["task_id"], record["snapshot_id"]
    try:
        atomic.atomic_create_new_bytes(path, data)
    except atomic.CreateNewError as exc:
        warnings = [] if exc.tmp_leftover is None else [f"TMP_LEFTOVER:{exc.tmp_leftover.name}"]
        if exc.final_created:
            return {"status": "STORED", "file_sha256": sha256_hex(data), "final_file_created": True,
                    "warnings": warnings, "state_sha256_stored": None}
        if isinstance(exc.cause, FileExistsError):
            try:
                existing, file_sha = load_record(root, task_id, snapshot_id)
            except WorkstateError as err:
                err.final_file_created = False
                err.warnings.extend(warnings)
                raise
            if identity(existing["task_id"], existing["state"], existing["reported"]) != \
                    identity(task_id, record["state"], record["reported"]):
                mismatch = WorkstateError(SNAPSHOT_CORRUPT, "an existing record with this id differs", file_sha)
                mismatch.final_file_created = False
                mismatch.warnings.extend(warnings)
                raise mismatch from None
            return {"status": "ALREADY_STORED", "file_sha256": file_sha, "final_file_created": False,
                    "warnings": warnings, "state_sha256_stored": existing["state_sha256"]}
        failure = WorkstateError(STORE_FAILED, f"the record could not be created: {type(exc.cause).__name__}")
        failure.final_file_created = False
        failure.warnings.extend(warnings)
        raise failure from exc
    return {"status": "STORED", "file_sha256": sha256_hex(data), "final_file_created": True, "warnings": [],
            "state_sha256_stored": None}


def save_record(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    """D10: check ignore and the path, create the missing directories top-down, then create the record
    without ever replacing a file. Directories this call created stay on error and are reported."""
    data = record_bytes(record)
    if len(data) > FILE_LIMIT:
        raise WorkstateError(LIMIT_EXCEEDED, "the record is larger than the limit")
    task_id = record["task_id"]
    rel = record_rel(task_id, record["snapshot_id"])
    code, _out = collect.run_git(root, "check-ignore", ["-q", "--no-index", "--", rel], ok_codes=(0, 1))
    if code != 0:
        raise WorkstateError(STORE_PATH_INVALID, "the store path is not ignored by git")
    path = Path(root) / rel
    if not _lexically_inside(root, path):
        raise WorkstateError(STORE_PATH_INVALID, "the store path is outside the root")
    parts = (*STORE_PARTS, task_id)
    first_missing = _inspect_dirs(root, task_id)
    created: list[str] = []
    try:
        current = Path(root).joinpath(*parts[:first_missing])
        for index in range(first_missing, len(parts)):
            current = current / parts[index]
            shown = "/".join(parts[:index + 1])
            try:
                _mkdir(current)
                created.append(shown)
            except FileExistsError:
                pass
            except OSError as exc:
                raise WorkstateError(STORE_FAILED, f"cannot create {shown}: {type(exc).__name__}") from exc
            try:
                st = collect._lstat(current)
            except OSError as exc:
                raise WorkstateError(STORE_PATH_INVALID, f"cannot inspect {shown}: {type(exc).__name__}") from exc
            if collect.is_link_like(current, st) or not stat.S_ISDIR(st.st_mode):
                raise WorkstateError(STORE_PATH_INVALID, f"not a plain directory: {shown}")
        if not _resolved_inside(root, current):
            raise WorkstateError(STORE_PATH_INVALID, "the store directory resolves outside the root")
        return _create(root, record, data, path)
    except WorkstateError as exc:
        exc.warnings.extend(f"DIR_LEFT:{shown}" for shown in created)
        raise


def _list_hash(items: list[Any]) -> str:
    return sha256_hex(canonical_text(items).encode("utf-8"))


def compare_states(stored: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    """Differences of the compared fields only; values are hashes, paths and status codes.

    Whether the states are equal is decided by comparing them whole (see `__main__`); this only describes
    the difference. A field whose lists differ always yields at least one item: when the per-path view
    loses the difference (a repeated path or an order change), the item carries the hashes of both lists."""
    differences: list[dict[str, Any]] = []
    for key in ("branch", "head", "tree"):
        if stored[key] != current[key]:
            differences.append({"field": key, "stored": stored[key], "current": current[key]})
    for key in ("entries", "contract", "untracked"):
        if stored[key] == current[key]:
            continue
        found = len(differences)
        if key == "untracked":
            old, new = set(stored[key]), set(current[key])
            if old != new:
                differences.append({"field": key, "stored": sorted(old - new), "current": sorted(new - old)})
        else:
            before = {item["path"]: item for item in stored[key]}
            after = {item["path"]: item for item in current[key]}
            for path in sorted(set(before) | set(after)):
                if before.get(path) != after.get(path):
                    differences.append({"field": key, "stored": before.get(path), "current": after.get(path)})
        if len(differences) == found:
            differences.append({"field": key, "stored": _list_hash(stored[key]), "current": _list_hash(current[key])})
    return differences
