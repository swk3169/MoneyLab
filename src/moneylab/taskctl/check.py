"""Read-only checks of taskctl (GOV-AUTOMATION-03 D2, D6-D8).

git runs only through `workstate.collect.run_git` (rev-parse, status, ls-files, ls-tree, cat-file,
check-ignore): no network, no other process, no `moneylab.providers`. STATE is collected here from the
working tree; the agent never supplies it. Remote facts (push, PR, CI, merge) are agent-reported values whose
form and fixed values are checked; taskctl cannot verify them. Local Git objects are verified directly.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from moneylab.taskctl.ledger import (
    LEDGER_FORMAT,
    LEDGER_ROOT,
    MAX_CHANGED,
    PATH_INVALID,
    STATE_TOO_LARGE,
    TaskctlError,
    is_hex40,
    is_relpath,
    parse_utc,
    sha256_hex,
)
from moneylab.workstate.collect import WorkstateError, check_tree_path, run_git

GIT_FAILED = "GIT_FAILED"
DELEGATION_INVALID = "DELEGATION_INVALID"
CONTRACT_MISMATCH = "CONTRACT_MISMATCH"
BASE_MISMATCH = "BASE_MISMATCH"
HEAD_MISMATCH = "HEAD_MISMATCH"
OUT_OF_SCOPE = "OUT_OF_SCOPE"
PROTECTED_CHANGED = "PROTECTED_CHANGED"
UNTRACKED = "UNTRACKED"
HASH_MISMATCH = "HASH_MISMATCH"
STATE_CHANGED = "STATE_CHANGED"
NOT_CLEAN = "NOT_CLEAN"
IGNORED_UNEXPECTED = "IGNORED_UNEXPECTED"
UNSUPPORTED_STATE = "UNSUPPORTED_STATE"
PUBLISH_MISMATCH = "PUBLISH_MISMATCH"
REMOTE_INVALID = "REMOTE_INVALID"
INVALID_TRANSITION = "INVALID_TRANSITION"
STEP_OPEN = "STEP_OPEN"
STEP_NOT_OPEN = "STEP_NOT_OPEN"
UNKNOWN_STEP = "UNKNOWN_STEP"
SESSION_MISMATCH = "SESSION_MISMATCH"
REVOKED = "REVOKED"
EXPIRED = "EXPIRED"
TERMINAL = "TERMINAL"
BUDGET_TIME = "BUDGET_TIME"
BUDGET_FIX = "BUDGET_FIX"
BUDGET_PYTEST = "BUDGET_PYTEST"
BUDGET_SAME_FAIL = "BUDGET_SAME_FAIL"

DELEGATION_SCHEMA = "moneylab.delegation/1"
DEFAULT_BUDGET = {"BUDGET_TIME_SECONDS": 4 * 3600, "BUDGET_FIX": 5, "BUDGET_PYTEST": 3, "BUDGET_SAME_FAIL": 2}
ALLOWED_IGNORED = frozenset({".venv/", "src/moneylab.egg-info/"})
PROTECTED_PREFIXES = ("docs/tasks/", ".claude/", ".github/")
PROTECTED_NAMES = frozenset({"CLAUDE.md", "docs/agent_workflow.md", ".gitignore", ".gitattributes",
                             "requirements.txt", "requirements-dev.txt"})
CHECK_STEPS = ("TEST_TARGETED", "TEST_FULL", "LINT", "TYPECHECK")
LOCAL_STEPS = ("IMPLEMENT", *CHECK_STEPS, "LOCAL_AUDIT", "LOCAL_COMMIT", "CLEAN_E2E")
PUBLISH_STEPS = ("PUSH", "PR_CREATE", "CI_WAIT", "PREMERGE_CHECK", "MERGE")
_KEY_LINE = re.compile(r"([A-Z][A-Z0-9_]*): (.+)")
_COMMAND_KEY = re.compile(r"(SETUP|CHECK)_COMMAND_([1-9])")
_REQUIRED_CI = re.compile(r"[A-Za-z0-9_.-]{1,40}")


# ------------------------------------------------------------------------------------------- git


def git(root: Path, sub: str, args: list[str], ok_codes: tuple[int, ...] = (0,)) -> tuple[int, bytes]:
    try:
        return run_git(Path(root), sub, args, ok_codes=ok_codes)
    except WorkstateError as exc:
        raise TaskctlError(GIT_FAILED, exc.detail) from exc


def rev(root: Path, ref: str) -> str | None:
    code, out = git(root, "rev-parse", ["--verify", "-q", ref], ok_codes=(0, 1))
    value = out.decode("ascii", errors="replace").strip()
    return value if code == 0 and is_hex40(value) else None


def confirm_root(root: Path) -> Path:
    """root must be the top level of its Git worktree."""
    _, out = git(root, "rev-parse", ["--show-toplevel"])
    top = Path(out.decode("utf-8", errors="replace").strip())
    if top.resolve() != Path(root).resolve():
        raise TaskctlError(PATH_INVALID, "--repo is not the top level of a Git worktree")
    return Path(root).resolve()


def commit_info(root: Path, sha: str) -> tuple[str, list[str]]:
    """(tree, parents) of one commit, read with cat-file."""
    _, out = git(root, "cat-file", ["commit", sha])
    tree = ""
    parents: list[str] = []
    for line in out.split(b"\n"):
        if not line:
            break
        if line.startswith(b"tree "):
            tree = line[5:].decode("ascii")
        elif line.startswith(b"parent "):
            parents.append(line[7:].decode("ascii"))
    if not is_hex40(tree):
        raise TaskctlError(GIT_FAILED, "commit has no tree")
    return tree, parents


def tree_files(root: Path, commit: str) -> dict[str, str]:
    """path -> blob id for every file of a commit."""
    _, out = git(root, "ls-tree", ["-r", "-z", "--full-tree", commit])
    files: dict[str, str] = {}
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, _, path = record.partition(b"\t")
        parts = meta.split(b" ")
        if len(parts) != 3:
            raise TaskctlError(GIT_FAILED, "unexpected ls-tree record")
        files[path.decode("utf-8")] = parts[2].decode("ascii")
    return files


def blob_bytes(root: Path, oid: str) -> bytes:
    return git(root, "cat-file", ["blob", oid])[1]


def wo_path(task_id: str) -> str:
    return f"docs/tasks/{task_id}/WORK_ORDER.md"


# ------------------------------------------------------------------------------------------- Work Order


def _section(text: str, title: str) -> list[str] | None:
    lines = text.split("\n")
    try:
        start = lines.index(f"## {title}")
    except ValueError:
        return None
    body = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        body.append(line)
    return body


def parse_allowed_files(text: str) -> dict[str, str]:
    """ALLOWED_FILES of a Work Order: path -> 'A' | 'M'."""
    body = _section(text, "ALLOWED_FILES")
    if body is None:
        raise TaskctlError(CONTRACT_MISMATCH, "Work Order has no ALLOWED_FILES section")
    allowed: dict[str, str] = {}
    for line in body:
        match = re.match(r"- ([AM]) (\S+)", line)
        if match and is_relpath(match.group(2)):
            allowed[match.group(2)] = match.group(1)
    if not allowed:
        raise TaskctlError(CONTRACT_MISMATCH, "ALLOWED_FILES is empty")
    return allowed


def parse_delegation(text: str, task_id: str) -> dict[str, Any]:
    """D2: KEY: VALUE lines of the DELEGATION section. Any defect is DELEGATION_INVALID; nothing is defaulted."""
    body = _section(text, "DELEGATION")
    if body is None:
        raise TaskctlError(DELEGATION_INVALID, "no DELEGATION section")
    values: dict[str, str] = {}
    for line in body:
        if not line.strip():
            continue
        match = _KEY_LINE.fullmatch(line)
        if match is None:
            raise TaskctlError(DELEGATION_INVALID, "a DELEGATION line is not KEY: VALUE")
        key, value = match.group(1), match.group(2)
        if key in values:
            raise TaskctlError(DELEGATION_INVALID, f"duplicate key {key}")
        values[key] = value
    known = {"DELEGATION_SCHEMA", "LEDGER_TASK_ID", "REQUIRED_CI", "PR_TITLE", *DEFAULT_BUDGET}
    setup: dict[int, str] = {}
    checks: dict[int, str] = {}
    for key, value in values.items():
        command = _COMMAND_KEY.fullmatch(key)
        if command:
            if len(value) > 500:
                raise TaskctlError(DELEGATION_INVALID, f"{key} is longer than 500 characters")
            (setup if command.group(1) == "SETUP" else checks)[int(command.group(2))] = value
        elif key not in known:
            raise TaskctlError(DELEGATION_INVALID, f"unknown key {key}")
    missing = [key for key in sorted(known) if key not in values]
    if missing or not setup or not checks:
        raise TaskctlError(DELEGATION_INVALID, "required keys are missing")
    if values["DELEGATION_SCHEMA"] != DELEGATION_SCHEMA or values["LEDGER_TASK_ID"] != task_id:
        raise TaskctlError(DELEGATION_INVALID, "schema or ledger task id does not match")
    budget: dict[str, int] = {}
    for key, limit in DEFAULT_BUDGET.items():
        if not values[key].isdigit() or int(values[key]) > limit:
            raise TaskctlError(DELEGATION_INVALID, f"{key} must be an integer not above {limit}")
        budget[key] = int(values[key])
    if _REQUIRED_CI.fullmatch(values["REQUIRED_CI"]) is None:
        raise TaskctlError(DELEGATION_INVALID, "REQUIRED_CI is not valid")
    if len(values["PR_TITLE"]) > 200:
        raise TaskctlError(DELEGATION_INVALID, "PR_TITLE is longer than 200 characters")
    if sorted(setup) != list(range(1, len(setup) + 1)) or sorted(checks) != list(range(1, len(checks) + 1)):
        raise TaskctlError(DELEGATION_INVALID, "command numbers must start at 1 without gaps")
    return {"budget": budget, "required_ci": values["REQUIRED_CI"], "pr_title": values["PR_TITLE"],
            "setup_commands": [setup[n] for n in sorted(setup)],
            "check_commands": [checks[n] for n in sorted(checks)]}


def delegation_sha256(delegation: dict[str, Any]) -> str:
    text = "\n".join([*delegation["setup_commands"], "--", *delegation["check_commands"], "--",
                      delegation["required_ci"], delegation["pr_title"],
                      *(f"{k}={v}" for k, v in sorted(delegation["budget"].items()))])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Contract:
    c1: str
    wo_sha256: str
    allowed: dict[str, str]
    delegation: dict[str, Any]


def load_contract(root: Path, task_id: str, c1: str) -> Contract:
    files = tree_files(root, c1)
    oid = files.get(wo_path(task_id))
    if oid is None:
        raise TaskctlError(CONTRACT_MISMATCH, "C1 has no Work Order for this task")
    raw = blob_bytes(root, oid)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TaskctlError(CONTRACT_MISMATCH, "Work Order is not UTF-8") from exc
    return Contract(c1, sha256_hex(raw), parse_allowed_files(text), parse_delegation(text, task_id))


# ------------------------------------------------------------------------------------------- STATE


@dataclass
class Snapshot:
    state: dict[str, Any]
    outside: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)


def _file_sha256(root: Path, rel: str) -> str:
    try:
        check_tree_path(Path(root), rel, PATH_INVALID, require_regular=True)
        return sha256_hex((Path(root) / rel).read_bytes())
    except WorkstateError as exc:
        raise TaskctlError(PATH_INVALID, exc.detail) from exc
    except OSError as exc:
        raise TaskctlError(PATH_INVALID, f"cannot read a changed file: {type(exc).__name__}") from exc


def collect(root: Path, allowed: dict[str, str] | set[str]) -> Snapshot:
    head = rev(root, "HEAD")
    tree = rev(root, "HEAD^{tree}") if head else None
    _, status = git(root, "status", ["--porcelain=v2", "-z", "--untracked-files=all", "--no-renames"])
    changed: list[list[Any]] = []
    outside: list[str] = []
    untracked: list[str] = []
    index_empty = True
    for record in status.split(b"\0"):
        if not record:
            continue
        text = record.decode("utf-8", errors="replace")
        if text.startswith("1 "):
            parts = text.split(" ", 8)
            if len(parts) != 9:
                raise TaskctlError(UNSUPPORTED_STATE, "unexpected status record")
            xy, path = parts[1], parts[8]
            if xy[0] != ".":
                index_empty = False
            if path in allowed and is_relpath(path):
                kind = "A" if "A" in xy else "D" if "D" in xy else "M"
                digest = None if kind == "D" else _file_sha256(root, path)
                changed.append([path, kind, digest])
            else:
                outside.append(path)
        elif text.startswith("? "):
            path = text[2:]
            if path in allowed and is_relpath(path):
                changed.append([path, "A", _file_sha256(root, path)])
            else:
                untracked.append(path)
        else:
            raise TaskctlError(UNSUPPORTED_STATE, "rename, unmerged or unknown status record")
    _, ignored_raw = git(root, "status", ["--porcelain=v2", "-z", "--untracked-files=normal", "--ignored=matching"])
    ignored = sorted(record.decode("utf-8", errors="replace")[2:] for record in ignored_raw.split(b"\0")
                     if record.startswith(b"! ")
                     and not record[2:].decode("utf-8", errors="replace").startswith(LEDGER_ROOT + "/"))
    changed.sort(key=lambda entry: entry[0])
    if len(changed) > MAX_CHANGED:
        raise TaskctlError(STATE_TOO_LARGE, "too many changed paths")
    state = {"head": head, "tree": tree, "index_empty": index_empty,
             "status_sha256": sha256_hex(status), "changed": changed, "outside_changes": len(outside),
             "untracked_unexpected": len(untracked),
             "ignored_top_sha256": sha256_hex("\n".join(ignored).encode("utf-8"))}
    return Snapshot(state, outside, untracked, ignored)


def scope_code(snapshot: Snapshot) -> str | None:
    """PROTECTED_CHANGED, OUT_OF_SCOPE or UNTRACKED for changes outside ALLOWED_FILES, else None."""
    for path in snapshot.outside + snapshot.untracked:
        if path.startswith(PROTECTED_PREFIXES) or path in PROTECTED_NAMES:
            return PROTECTED_CHANGED
    if snapshot.outside:
        return OUT_OF_SCOPE
    if snapshot.untracked:
        return UNTRACKED
    return None


def is_clean(state: dict[str, Any]) -> bool:
    return (state["index_empty"] and not state["changed"] and state["outside_changes"] == 0
            and state["untracked_unexpected"] == 0)


# ------------------------------------------------------------------------------------------- replay


@dataclass
class Step:
    name: str
    start_seq: int
    nonce: str
    pre_state: dict[str, Any]
    end_seq: int | None = None
    result: str | None = None
    failure_sig: str | None = None
    post_state: dict[str, Any] | None = None
    remote: dict[str, Any] = field(default_factory=dict)
    start_utc: str = ""


@dataclass
class Context:
    task_id: str
    events: list[tuple[dict[str, Any], str, bytes]]
    delegate: dict[str, Any]
    delegate_utc: str
    delegation_id: str
    nonce: str
    nonces: list[str]
    phase: str
    steps: list[Step]
    publish: dict[str, Any] | None
    pr_text: dict[str, Any] | None
    terminal: dict[str, Any] | None

    @property
    def open_steps(self) -> list[Step]:
        return [step for step in self.steps if step.end_seq is None]

    @property
    def last_state(self) -> dict[str, Any]:
        ended = [step for step in self.steps if step.post_state is not None]
        latest = max(ended, key=lambda step: step.end_seq or 0) if ended else None
        if latest is None:
            return self.delegate["state"]
        return latest.post_state or self.delegate["state"]

    def last_ok(self, name: str) -> Step | None:
        done = [step for step in self.steps if step.name == name and step.result == "ok"]
        return done[-1] if done else None

    @property
    def commit_i(self) -> str | None:
        step = self.last_ok("LOCAL_COMMIT")
        return step.post_state["head"] if step and step.post_state else None

    def expires(self) -> datetime:
        if self.publish is not None:
            return parse_utc(self.publish["expires_utc"])
        return parse_utc(self.delegate["expires_utc"])


def replay(task_id: str, events: list[tuple[dict[str, Any], str, bytes]]) -> Context:
    if not events or events[0][0]["kind"] != "DELEGATE":
        raise TaskctlError(LEDGER_FORMAT, "the first event must be DELEGATE")
    first = events[0][0]
    ctx = Context(task_id, events, first["payload"], first["utc"], events[0][1], first["payload"]["session_nonce"],
                  [first["payload"]["session_nonce"]], "DELEGATED", [], None, None, None)
    for event, _, _ in events[1:]:
        kind, payload = event["kind"], event["payload"]
        if kind == "DELEGATE":
            raise TaskctlError(LEDGER_FORMAT, "a second DELEGATE event")
        if kind == "RESUME":
            ctx.nonce = payload["session_nonce"]
            ctx.nonces.append(ctx.nonce)
        elif kind == "STEP_START":
            ctx.steps.append(Step(payload["step"], event["seq"], payload["session_nonce"], payload["pre_state"],
                                  start_utc=event["utc"]))
        elif kind == "STEP_END":
            match = [step for step in ctx.steps if step.start_seq == payload["start_seq"]]
            if len(match) != 1 or match[0].end_seq is not None or match[0].name != payload["step"]:
                raise TaskctlError(LEDGER_FORMAT, "STEP_END without its open STEP_START")
            step = match[0]
            step.end_seq, step.result = event["seq"], payload["result"]
            step.failure_sig, step.post_state = payload["failure_sig"], payload["post_state"]
            step.remote = payload["remote"]
        elif kind == "PHASE":
            if payload["from"] != ctx.phase:
                raise TaskctlError(LEDGER_FORMAT, "PHASE event does not start from the current phase")
            ctx.phase = payload["to"]
            if payload["to"] == "TERMINAL":
                ctx.terminal = payload
        elif kind == "PUBLISH":
            ctx.publish = payload
        elif kind == "PR_TEXT":
            ctx.pr_text = payload
    return ctx


# ------------------------------------------------------------------------------------------- budget


def budget_report(ctx: Context, budget: dict[str, int], now: datetime) -> dict[str, Any]:
    elapsed = int((now - parse_utc(ctx.delegate_utc)).total_seconds())
    fixes = 0
    last_check: Step | None = None
    for step in sorted(ctx.steps, key=lambda s: s.start_seq):
        if step.name == "IMPLEMENT" and last_check is not None and last_check.result == "fail":
            fixes += 1
        if step.name in CHECK_STEPS and step.result is not None:
            last_check = step
    pytest_runs = sum(1 for step in ctx.steps if step.name == "TEST_FULL")
    checks = [step for step in sorted(ctx.steps, key=lambda s: s.end_seq or 0)
              if step.name in CHECK_STEPS and step.result is not None]
    same_fail = 0
    if checks and checks[-1].result == "fail":
        same_fail = 1
        for step in reversed(checks[:-1]):
            if step.result == "fail" and step.failure_sig is not None and step.failure_sig == checks[-1].failure_sig:
                same_fail += 1
            else:
                break
    return {"elapsed_seconds": elapsed, "time_limit_seconds": budget["BUDGET_TIME_SECONDS"], "fixes": fixes,
            "fix_limit": budget["BUDGET_FIX"], "full_pytest_runs": pytest_runs,
            "full_pytest_limit": budget["BUDGET_PYTEST"], "same_failures": same_fail,
            "same_failure_limit": budget["BUDGET_SAME_FAIL"],
            "_last_check_failed": bool(checks and checks[-1].result == "fail")}


def check_budget_for_start(report: dict[str, Any], step: str) -> None:
    """D7: a limit allows that many; the next start is refused."""
    if report["elapsed_seconds"] >= report["time_limit_seconds"]:
        raise TaskctlError(BUDGET_TIME, "total elapsed time limit reached")
    if step in ("IMPLEMENT", *CHECK_STEPS) and report["same_failures"] >= report["same_failure_limit"]:
        raise TaskctlError(BUDGET_SAME_FAIL, "the same failure repeated up to the limit")
    if step == "IMPLEMENT" and report["_last_check_failed"] and report["fixes"] + 1 > report["fix_limit"]:
        raise TaskctlError(BUDGET_FIX, "repair iteration limit reached")
    if step == "TEST_FULL" and report["full_pytest_runs"] + 1 > report["full_pytest_limit"]:
        raise TaskctlError(BUDGET_PYTEST, "full pytest run limit reached")


# ------------------------------------------------------------------------------------------- step conditions


def allowed_step(ctx: Context, step: str) -> None:
    """Which step may start in the current phase (D6)."""
    phase = ctx.phase
    if step == "SETUP_ENV":
        ok = phase == "DELEGATED" and ctx.last_ok("SETUP_ENV") is None
    elif step in LOCAL_STEPS:
        committed = ctx.last_ok("LOCAL_COMMIT") is not None
        ok = phase == "SETUP_DONE" and (step == "CLEAN_E2E" if committed else step != "CLEAN_E2E")
        if step == "LOCAL_COMMIT" and ok:
            last = max(ctx.steps, key=lambda s: s.end_seq or 0) if ctx.steps else None
            ok = last is not None and last.name == "LOCAL_AUDIT" and last.result == "ok"
    elif step in PUBLISH_STEPS:
        done = [s.name for s in ctx.steps if s.result == "ok" and s.name in PUBLISH_STEPS]
        position = PUBLISH_STEPS.index(step)
        ok = phase == "PUBLISHING" and done == list(PUBLISH_STEPS[:position])
    else:
        ok = phase == "MERGED" and ctx.last_ok("POST_MERGE_AUDIT") is None
    if not ok:
        raise TaskctlError(INVALID_TRANSITION, f"{step} cannot start in phase {phase}")


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise TaskctlError(code, detail)


def check_scope(snapshot: Snapshot) -> None:
    code = scope_code(snapshot)
    if code is not None:
        raise TaskctlError(code, "changes outside ALLOWED_FILES")


def check_pre(ctx: Context, step: str, snapshot: Snapshot) -> None:
    state, c1 = snapshot.state, ctx.delegate["c1"]
    check_scope(snapshot)
    if step == "SETUP_ENV":
        _require(state["head"] == c1, HEAD_MISMATCH, "HEAD is not C1")
        _require(is_clean(state), NOT_CLEAN, "the worktree is not clean")
    elif step in ("IMPLEMENT", *CHECK_STEPS, "LOCAL_AUDIT"):
        _require(state["head"] == c1, HEAD_MISMATCH, "HEAD is not C1")
        _require(state["index_empty"], NOT_CLEAN, "the index is not empty")
    elif step == "LOCAL_COMMIT":
        audit = ctx.last_ok("LOCAL_AUDIT")
        _require(state["head"] == c1, HEAD_MISMATCH, "HEAD is not C1")
        _require(audit is not None and audit.post_state is not None
                 and state["changed"] == audit.post_state["changed"], HASH_MISMATCH, "changes differ from W_audit")
    else:
        _require(state["head"] == ctx.commit_i, HEAD_MISMATCH, "HEAD is not the implementation commit")
        _require(is_clean(state), NOT_CLEAN, "the worktree is not clean")
    _require(state == ctx.last_state, STATE_CHANGED, "the state changed since the last recorded step")


def _commit_matches_audit(root: Path, ctx: Context, head: str) -> None:
    c1 = ctx.delegate["c1"]
    audit = ctx.last_ok("LOCAL_AUDIT")
    _require(audit is not None and audit.post_state is not None, HASH_MISMATCH, "no W_audit")
    assert audit is not None and audit.post_state is not None
    _, parents = commit_info(root, head)
    _require(parents == [c1], HEAD_MISMATCH, "the commit's parent is not C1")
    before, after = tree_files(root, c1), tree_files(root, head)
    changed_paths = {path for path in set(before) | set(after) if before.get(path) != after.get(path)}
    expected = {entry[0]: entry for entry in audit.post_state["changed"]}
    _require(changed_paths == set(expected), HASH_MISMATCH, "commit files differ from W_audit")
    for path, (_, kind, digest) in expected.items():
        if kind == "D":
            _require(path not in after, HASH_MISMATCH, "a deleted file is still in the commit")
        else:
            _require(sha256_hex(blob_bytes(root, after[path])) == digest, HASH_MISMATCH,
                     "a committed blob differs from W_audit")


REMOTE_REQUIRED = {"PUSH": ("pushed_head",), "PR_CREATE": ("pr_number",),
                   "CI_WAIT": ("run_id", "run_head_sha", "required_conclusion"), "PREMERGE_CHECK": (),
                   "MERGE": ("merge_sha", "merge_parents"), "POST_MERGE_AUDIT": ("merge_sha", "merge_tree_recomputed")}


def check_remote(ctx: Context, step: str, remote: dict[str, Any]) -> None:
    """Form and fixed values of agent-reported remote facts. The facts themselves are not verified."""
    publish = ctx.publish
    needed = REMOTE_REQUIRED.get(step, ())
    if step not in REMOTE_REQUIRED:
        _require(not remote, REMOTE_INVALID, f"{step} takes no remote values")
        return
    _require(publish is not None, PUBLISH_MISMATCH, "no PUBLISH event")
    assert publish is not None
    _require(all(key in remote for key in needed), REMOTE_INVALID, f"{step} needs {', '.join(needed)}")
    if "pushed_head" in remote:
        _require(remote["pushed_head"] == publish["head"], PUBLISH_MISMATCH, "pushed head differs from PUBLISH")
    if "run_head_sha" in remote:
        _require(remote["run_head_sha"] == publish["head"], PUBLISH_MISMATCH, "run head differs from PUBLISH")
    if "required_conclusion" in remote:
        _require(remote["required_conclusion"] == "success", PUBLISH_MISMATCH, "required CI did not succeed")
    if "merge_parents" in remote:
        _require(remote["merge_parents"] == [publish["base"], publish["head"]], PUBLISH_MISMATCH,
                 "merge parents differ from [BASE, HEAD]")
    if "merge_tree_recomputed" in remote:
        _require(remote["merge_tree_recomputed"] == publish["tree"], PUBLISH_MISMATCH,
                 "recomputed merge tree differs from PUBLISH tree")
    if step == "POST_MERGE_AUDIT":
        merged = ctx.last_ok("MERGE")
        _require(merged is not None and merged.remote.get("merge_sha") == remote["merge_sha"], PUBLISH_MISMATCH,
                 "audited merge differs from the recorded merge")


def check_post(root: Path, ctx: Context, step: Step, snapshot: Snapshot, remote: dict[str, Any]) -> None:
    """End conditions of a step reported ok (D6). A failed check refuses the ok record."""
    state, pre, c1 = snapshot.state, step.pre_state, ctx.delegate["c1"]
    check_scope(snapshot)
    name = step.name
    if name == "SETUP_ENV":
        _require(state["head"] == c1, HEAD_MISMATCH, "HEAD is not C1")
        _require(is_clean(state), NOT_CLEAN, "the worktree is not clean")
        _require(set(snapshot.ignored) <= ALLOWED_IGNORED, IGNORED_UNEXPECTED, "unexpected ignored entries")
    elif name == "IMPLEMENT":
        _require(state["head"] == c1, HEAD_MISMATCH, "HEAD is not C1")
        _require(state["index_empty"], NOT_CLEAN, "the index is not empty")
    elif name in (*CHECK_STEPS, "LOCAL_AUDIT"):
        _require(state["head"] == c1, HEAD_MISMATCH, "HEAD is not C1")
        _require(state["changed"] == pre["changed"], STATE_CHANGED, "a check step changed files")
        _require(state["ignored_top_sha256"] == pre["ignored_top_sha256"], STATE_CHANGED,
                 "a check step changed the ignored entries")
    elif name == "LOCAL_COMMIT":
        head = state["head"]
        _require(head is not None and head != c1, HEAD_MISMATCH, "no new commit")
        _commit_matches_audit(root, ctx, head)
        _require(is_clean(state), NOT_CLEAN, "the worktree is not clean after the commit")
    elif name == "CLEAN_E2E":
        _require(state["head"] == ctx.commit_i, HEAD_MISMATCH, "HEAD is not the implementation commit")
        _require(state["status_sha256"] == pre["status_sha256"]
                 and state["ignored_top_sha256"] == pre["ignored_top_sha256"], STATE_CHANGED,
                 "status changed during the clean-commit check")
    elif name in PUBLISH_STEPS:
        _require(state == pre, STATE_CHANGED, "the local state changed during a publish step")
        check_remote(ctx, name, remote)
    elif name == "POST_MERGE_AUDIT":
        _require(state == pre, STATE_CHANGED, "the local state changed during the audit")
        check_remote(ctx, name, remote)
        publish = ctx.publish
        assert publish is not None
        merge = remote["merge_sha"]
        _require(rev(root, "refs/remotes/origin/main") == merge, PUBLISH_MISMATCH, "origin/main is not the merge")
        tree, parents = commit_info(root, merge)
        _require(parents == [publish["base"], publish["head"]] and tree == publish["tree"], PUBLISH_MISMATCH,
                 "the merge commit's parents or tree differ from PUBLISH")


# ------------------------------------------------------------------------------------------- phases


def _sequence_ok(ctx: Context, names: tuple[str, ...]) -> bool:
    ordered = sorted((s for s in ctx.steps if s.end_seq is not None), key=lambda s: s.end_seq or 0)
    position = 0
    for step in ordered:
        if position < len(names) and step.name == names[position] and step.result == "ok":
            position += 1
    return position == len(names)


def check_transition(ctx: Context, to: str, snapshot: Snapshot, terminal_status: str | None,
                     violations: int | None) -> None:
    """D6 phase transitions. TERMINAL(STOPPED) is checked by the caller's exception list."""
    phase = ctx.phase
    state = snapshot.state
    if to == "SETUP_DONE" and phase == "DELEGATED":
        setup = ctx.last_ok("SETUP_ENV")
        _require(setup is not None and setup.post_state == state, INVALID_TRANSITION, "SETUP_ENV ok is required")
    elif to == "LOCAL_DONE" and phase == "SETUP_DONE":
        implements = [s.end_seq or 0 for s in ctx.steps if s.name == "IMPLEMENT"]
        after = max(implements) if implements else 0
        later = [s for s in ctx.steps if (s.end_seq or 0) > after and s.result == "ok"]
        names = {s.name for s in later}
        needed = {*CHECK_STEPS, "LOCAL_AUDIT", "LOCAL_COMMIT", "CLEAN_E2E"}
        e2e = ctx.last_ok("CLEAN_E2E")
        commit = ctx.last_ok("LOCAL_COMMIT")
        _require(needed <= names and e2e is not None and commit is not None
                 and (e2e.end_seq or 0) > (commit.end_seq or 0) and e2e.post_state == state,
                 INVALID_TRANSITION, "checks, audit, commit and clean-commit check are required")
    elif to == "READY_TO_PUBLISH" and phase == "LOCAL_DONE":
        _require(ctx.pr_text is not None and state["head"] == ctx.commit_i and is_clean(state),
                 INVALID_TRANSITION, "PR text and a clean implementation commit are required")
    elif to == "PUBLISHING" and phase == "READY_TO_PUBLISH":
        _require(ctx.publish is not None, INVALID_TRANSITION, "PUBLISH is required")
    elif to == "MERGED" and phase == "PUBLISHING":
        _require(_sequence_ok(ctx, PUBLISH_STEPS), INVALID_TRANSITION, "publish steps must all be ok in order")
    elif to == "AUDITED" and phase == "MERGED":
        _require(ctx.last_ok("POST_MERGE_AUDIT") is not None, INVALID_TRANSITION, "POST_MERGE_AUDIT ok is required")
    elif to == "TERMINAL" and phase == "AUDITED" and terminal_status in ("COMPLETE", "CLOSED_WITH_VIOLATION"):
        _require(violations is not None and (violations == 0) == (terminal_status == "COMPLETE"),
                 INVALID_TRANSITION, "COMPLETE needs 0 violations, CLOSED_WITH_VIOLATION at least 1")
        _require(not ctx.open_steps, INVALID_TRANSITION, "open steps remain")
    else:
        raise TaskctlError(INVALID_TRANSITION, f"{phase} -> {to} is not a defined transition")


def state_matches_contract(ctx: Context, contract: Contract) -> None:
    if contract.wo_sha256 != ctx.delegate["wo_sha256"]:
        raise TaskctlError(CONTRACT_MISMATCH, "Work Order differs from DELEGATE")
    if delegation_sha256(contract.delegation) != ctx.delegate["delegation_sha256"]:
        raise TaskctlError(CONTRACT_MISMATCH, "DELEGATION differs from DELEGATE")
