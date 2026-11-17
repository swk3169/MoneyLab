"""Append-only event ledger of taskctl (GOV-AUTOMATION-03 D4).

One event is one file `events/NNNNNN.json` under `<repo>/data/processed/taskctl/<TASK>/`, written once with
`atomic_create_new_bytes` (temp file + fsync + hard link; never replaces an existing file). Events carry the
SHA-256 of the previous event file, so an accidental gap, edit or truncation is detected. This is damage
detection only: the chain does not stop a deliberate rewrite of the whole ledger and proves no approval.

Only hashes, commit ids, UTC times, codes, counts and repository-relative paths are stored. Absolute paths,
URLs, environment values, command output and exception text are never stored.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from moneylab.storage.atomic import CreateNewError, atomic_create_new_bytes
from moneylab.workstate.collect import WorkstateError, check_tree_path
from moneylab.workstate.store import valid_task_id

EVENT_SCHEMA = "moneylab.taskctl.event/1"
LEDGER_ROOT = "data/processed/taskctl"
MAX_EVENT_BYTES = 8 * 1024
MAX_EVENTS = 10_000
MAX_CHANGED = 200
MAX_RELPATH = 240
MAX_TEXT = 200
ZERO_SHA = "0" * 64
EVENT_NAME_RE = re.compile(r"(\d{6})\.json")

# Result codes (D3-D8).
OK = "OK"
INVALID = "INVALID"
LEDGER_EXISTS = "LEDGER_EXISTS"
LEDGER_MISSING = "LEDGER_MISSING"
LEDGER_GAP = "LEDGER_GAP"
LEDGER_CHAIN = "LEDGER_CHAIN"
LEDGER_FORMAT = "LEDGER_FORMAT"
LEDGER_TASK = "LEDGER_TASK"
LEDGER_FULL = "LEDGER_FULL"
EVENT_TOO_LARGE = "EVENT_TOO_LARGE"
STATE_TOO_LARGE = "STATE_TOO_LARGE"
CONCURRENT = "CONCURRENT"
CREATED_CLEANUP_FAILED = "CREATED_CLEANUP_FAILED"
IO_ERROR = "IO_ERROR"
PATH_INVALID = "PATH_INVALID"

STEPS = ("SETUP_ENV", "IMPLEMENT", "TEST_TARGETED", "TEST_FULL", "LINT", "TYPECHECK", "LOCAL_AUDIT",
         "LOCAL_COMMIT", "CLEAN_E2E", "PUSH", "PR_CREATE", "CI_WAIT", "PREMERGE_CHECK", "MERGE",
         "POST_MERGE_AUDIT")
PHASES = ("NONE", "DELEGATED", "SETUP_DONE", "LOCAL_DONE", "READY_TO_PUBLISH", "PUBLISHING", "MERGED",
          "AUDITED", "TERMINAL")
TERMINAL_STATUSES = ("COMPLETE", "CLOSED_WITH_VIOLATION", "STOPPED")
KINDS = ("DELEGATE", "PUBLISH", "RESUME", "STEP_START", "STEP_END", "PHASE", "PR_TEXT", "LEASE_CLEARED")

_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_HEX32 = re.compile(r"[0-9a-f]{32}")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_CODE = re.compile(r"[A-Z0-9_]{1,40}")
_RELPATH = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*")
_CONCLUSION = re.compile(r"[a-z_]{1,20}")
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TaskctlError(Exception):
    """A defined failure with a result code. Never a success and never a partial result."""

    def __init__(self, code: str, detail: str = "", **extra: Any) -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail
        self.extra = extra


# ------------------------------------------------------------------------------------------- values


def is_hex40(value: object) -> bool:
    return isinstance(value, str) and _HEX40.fullmatch(value) is not None


def is_hex64(value: object) -> bool:
    return isinstance(value, str) and _HEX64.fullmatch(value) is not None


def is_hex32(value: object) -> bool:
    return isinstance(value, str) and _HEX32.fullmatch(value) is not None


def is_utc(value: object) -> bool:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        return False
    try:
        datetime.strptime(value, UTC_FORMAT)
    except ValueError:
        return False
    return True


def parse_utc(value: str) -> datetime:
    return datetime.strptime(value, UTC_FORMAT).replace(tzinfo=UTC)


def format_utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime(UTC_FORMAT)


def is_code(value: object) -> bool:
    return isinstance(value, str) and _CODE.fullmatch(value) is not None


def is_count(value: object) -> bool:
    return type(value) is int and value >= 0


def is_relpath(value: object) -> bool:
    """A repository-relative POSIX path of plain segments (no drive, no '..', no absolute or home path)."""
    if not isinstance(value, str) or not value or len(value) > MAX_RELPATH:
        return False
    if _RELPATH.fullmatch(value) is None:
        return False
    return all(part not in (".", "..") for part in value.split("/"))


def is_text(value: object) -> bool:
    return (isinstance(value, str) and len(value) <= MAX_TEXT and value.isascii()
            and all(" " <= ch <= "~" for ch in value) and "://" not in value)


def _nullable(check: Callable[[object], bool]) -> Callable[[object], bool]:
    return lambda value: value is None or check(value)


def _one_of(*options: str) -> Callable[[object], bool]:
    return lambda value: isinstance(value, str) and value in options


def is_state(value: object) -> bool:
    """D4 STATE: collected by taskctl itself, never supplied by the agent."""
    keys = {"head", "tree", "index_empty", "status_sha256", "changed", "outside_changes",
            "untracked_unexpected", "ignored_top_sha256"}
    if not isinstance(value, dict) or set(value) != keys:
        return False
    if not (_nullable(is_hex40)(value["head"]) and _nullable(is_hex40)(value["tree"])):
        return False
    if type(value["index_empty"]) is not bool or not is_hex64(value["status_sha256"]):
        return False
    if not (is_count(value["outside_changes"]) and is_count(value["untracked_unexpected"])):
        return False
    if not is_hex64(value["ignored_top_sha256"]):
        return False
    changed = value["changed"]
    if not isinstance(changed, list) or len(changed) > MAX_CHANGED:
        return False
    paths = []
    for entry in changed:
        if not (isinstance(entry, list) and len(entry) == 3):
            return False
        path, kind, digest = entry
        if not is_relpath(path) or kind not in ("A", "M", "D"):
            return False
        if kind == "D" and digest is not None:
            return False
        if kind != "D" and not is_hex64(digest):
            return False
        paths.append(path)
    return paths == sorted(set(paths))


REMOTE_KEYS: dict[str, Callable[[object], bool]] = {
    "agent_reported": lambda value: value is True,
    "pushed_head": is_hex40,
    "merge_sha": is_hex40,
    "run_head_sha": is_hex40,
    "checkout_sha": is_hex40,
    "merge_tree_recomputed": is_hex40,
    "merge_parents": lambda value: isinstance(value, list) and len(value) == 2 and all(map(is_hex40, value)),
    "pr_number": lambda value: type(value) is int and value >= 1,
    "run_id": lambda value: type(value) is int and value >= 1,
    "required_conclusion": lambda value: isinstance(value, str) and _CONCLUSION.fullmatch(value) is not None,
}


def is_remote(value: object) -> bool:
    """Agent-reported remote observations. taskctl checks their form only, never the remote facts."""
    if not isinstance(value, dict):
        return False
    if not value:
        return True
    if value.get("agent_reported") is not True:
        return False
    return all(key in REMOTE_KEYS and REMOTE_KEYS[key](item) for key, item in value.items())


_STEP = _one_of(*STEPS)
_PHASE = _one_of(*PHASES)

SCHEMAS: dict[str, dict[str, Callable[[object], bool]]] = {
    "DELEGATE": {"c1": is_hex40, "wo_sha256": is_hex64, "base": is_hex40, "expires_utc": is_utc,
                 "session_nonce": is_hex32, "delegation_sha256": is_hex64, "state": is_state},
    "PUBLISH": {"wo_c1": is_hex40, "head": is_hex40, "tree": is_hex40, "base": is_hex40,
                "pr_text_sha256": is_hex64, "expires_utc": is_utc},
    "RESUME": {"wo_sha256": is_hex64, "delegation_id": is_hex64, "phase": _PHASE, "head": is_hex40,
               "session_nonce": is_hex32, "state": is_state},
    "STEP_START": {"step": _STEP, "session_nonce": is_hex32, "input_sha256": is_hex64, "pre_state": is_state},
    "STEP_END": {"step": _STEP, "start_seq": lambda value: type(value) is int and value >= 1,
                 "session_nonce": is_hex32, "result": _one_of("ok", "fail"),
                 "failure_sig": _nullable(is_hex64), "post_state": is_state, "remote": is_remote},
    "PHASE": {"from": _PHASE, "to": _PHASE, "terminal_status": _nullable(_one_of(*TERMINAL_STATUSES)),
              "code": _nullable(is_code), "violations": _nullable(is_count)},
    "PR_TEXT": {"sha256": is_hex64, "bytes": is_count},
    "LEASE_CLEARED": {"lease_id": is_hex32},
}


def check_payload(kind: str, payload: object) -> None:
    schema = SCHEMAS.get(kind)
    if schema is None or not isinstance(payload, dict) or set(payload) != set(schema):
        raise TaskctlError(INVALID, f"payload keys do not match kind {kind}")
    for key, check in schema.items():
        if not check(payload[key]):
            if key in ("state", "pre_state", "post_state") and isinstance(payload[key], dict):
                changed = payload[key].get("changed")
                if isinstance(changed, list) and len(changed) > MAX_CHANGED:
                    raise TaskctlError(STATE_TOO_LARGE, "too many changed paths")
            raise TaskctlError(INVALID, f"payload value {key} is not valid for kind {kind}")


# ------------------------------------------------------------------------------------------- events


def event_bytes(event: dict[str, Any]) -> bytes:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_event(task_id: str, seq: int, prev_sha256: str, kind: str, utc: str,
                payload: dict[str, Any]) -> bytes:
    check_payload(kind, payload)
    event = {"schema": EVENT_SCHEMA, "task_id": task_id, "seq": seq, "prev_sha256": prev_sha256,
             "kind": kind, "utc": utc, "payload": payload}
    data = event_bytes(event)
    if len(data) > MAX_EVENT_BYTES:
        raise TaskctlError(EVENT_TOO_LARGE, f"event {seq} would be {len(data)} bytes")
    return data


def task_dir(root: Path, task_id: str) -> Path:
    if not valid_task_id(task_id):
        raise TaskctlError(INVALID, "task id is not valid")
    return Path(root) / LEDGER_ROOT / task_id


def check_dir(root: Path, rel: str) -> bool:
    """True when root/rel exists as a plain directory chain; raises PATH_INVALID on links or non-directories."""
    try:
        st = check_tree_path(Path(root), rel, PATH_INVALID, require_regular=False)
    except WorkstateError as exc:
        raise TaskctlError(PATH_INVALID, exc.detail) from exc
    return st is not None


def read_events(root: Path, task_id: str) -> list[tuple[dict[str, Any], str, bytes]]:
    """Read and verify every event. Returns [(event, file sha256, raw bytes)] in seq order."""
    base = task_dir(root, task_id)
    if not check_dir(root, f"{LEDGER_ROOT}/{task_id}/events"):
        raise TaskctlError(LEDGER_MISSING, "no ledger for this task")
    found: dict[int, Path] = {}
    for entry in (base / "events").iterdir():
        if entry.name.startswith("."):
            continue  # an interrupted create-new may leave its own temp file; it is never an event
        match = EVENT_NAME_RE.fullmatch(entry.name)
        if match is None:
            raise TaskctlError(LEDGER_FORMAT, "unexpected file in the events directory")
        found[int(match.group(1))] = entry
    if len(found) > MAX_EVENTS:
        raise TaskctlError(LEDGER_FULL, "too many events")
    out: list[tuple[dict[str, Any], str, bytes]] = []
    prev = ZERO_SHA
    for seq in range(1, len(found) + 1):
        path = found.get(seq)
        if path is None:
            raise TaskctlError(LEDGER_GAP, f"event {seq} is missing")
        try:
            check_tree_path(Path(root), f"{LEDGER_ROOT}/{task_id}/events/{path.name}", PATH_INVALID,
                            require_regular=True)
            raw = path.read_bytes()
        except WorkstateError as exc:
            raise TaskctlError(PATH_INVALID, exc.detail) from exc
        except OSError as exc:
            raise TaskctlError(IO_ERROR, f"event {seq} could not be read: {type(exc).__name__}") from exc
        if len(raw) > MAX_EVENT_BYTES:
            raise TaskctlError(LEDGER_FORMAT, f"event {seq} is too large")
        try:
            event = json.loads(raw.decode("ascii"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise TaskctlError(LEDGER_FORMAT, f"event {seq} is not canonical JSON") from exc
        if not isinstance(event, dict) or event_bytes(event) != raw:
            raise TaskctlError(LEDGER_FORMAT, f"event {seq} is not canonical JSON")
        if set(event) != {"schema", "task_id", "seq", "prev_sha256", "kind", "utc", "payload"}:
            raise TaskctlError(LEDGER_FORMAT, f"event {seq} has unexpected keys")
        if event["schema"] != EVENT_SCHEMA or event["seq"] != seq or event["kind"] not in KINDS:
            raise TaskctlError(LEDGER_FORMAT, f"event {seq} header is not valid")
        if not is_utc(event["utc"]):
            raise TaskctlError(LEDGER_FORMAT, f"event {seq} time is not valid")
        if event["task_id"] != task_id:
            raise TaskctlError(LEDGER_TASK, f"event {seq} belongs to another task")
        if event["prev_sha256"] != prev:
            raise TaskctlError(LEDGER_CHAIN, f"event {seq} does not chain to event {seq - 1}")
        try:
            check_payload(event["kind"], event["payload"])
        except TaskctlError as exc:
            raise TaskctlError(LEDGER_FORMAT, f"event {seq}: {exc.detail}") from exc
        prev = sha256_hex(raw)
        out.append((event, prev, raw))
    return out


def create_new(path: Path, data: bytes, label: str) -> None:
    """atomic_create_new_bytes with the D4 handling of every failure. Nothing is retried."""
    try:
        atomic_create_new_bytes(path, data)
    except CreateNewError as exc:
        cause = getattr(exc, "cause", None) or exc.__cause__
        if exc.final_created:
            raise TaskctlError(CREATED_CLEANUP_FAILED, f"{label} was created but its temp file was not removed",
                               created=label, created_sha256=sha256_hex(data), tmp_leftover_possible=True) from exc
        if isinstance(cause, FileExistsError):
            raise TaskctlError(CONCURRENT, f"{label} already exists") from exc
        raise TaskctlError(IO_ERROR, f"{label} was not created", created=None,
                           tmp_leftover_possible=getattr(exc, "tmp_leftover", None) is not None) from exc


def append_event(root: Path, task_id: str, events: list[tuple[dict[str, Any], str, bytes]], kind: str,
                 utc: str, payload: dict[str, Any]) -> tuple[dict[str, Any], str, bytes]:
    """Write the next event. The caller holds the lease and has just verified `events`."""
    if len(events) >= MAX_EVENTS:
        raise TaskctlError(LEDGER_FULL, "the ledger is full")
    seq = len(events) + 1
    prev = events[-1][1] if events else ZERO_SHA
    data = build_event(task_id, seq, prev, kind, utc, payload)
    path = task_dir(root, task_id) / "events" / f"{seq:06d}.json"
    create_new(path, data, f"event {seq:06d}")
    return json.loads(data), sha256_hex(data), data
