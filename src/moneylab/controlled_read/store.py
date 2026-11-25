"""D14-D16: the result document, the non-authoritative audit record and its status check.

Records live in the ignored `data/processed/controlled_read/<TASK_ID>/<NNN>/` and are created once with
`atomic_create_new_bytes`; nothing is replaced, deleted or re-run. A record proves neither that a run
really happened, who wrote it, an approval nor a right to run again, and gives no exactly-once guarantee
or security isolation. `status` reads the two record files only and never touches a session file.

RESULT_FOUND only means that both record files are valid in form and identity (ERRATA-001 E3.4). It proves
neither the stdout of that call, the success of the whole call, the cleanup of temp files, that the run
really happened, an approval nor a right to run again. When result.json was completed but its create
attempt still failed, stdout says STORE_FAILED while result.json holds the processing document (E3.3)."""

from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from moneylab.controlled_read import APPROVAL, AUTHORITY, BOUNDARY, DETAILS, SUCCEEDED, ControlledReadError
from moneylab.controlled_read import selector as grammar
from moneylab.controlled_read.profiles import PROFILES
from moneylab.storage.atomic import CreateNewError, atomic_create_new_bytes
from moneylab.workstate import collect
from moneylab.workstate.collect import WorkstateError

RESULT_SCHEMA = "moneylab.controlled_read.result/1"
INTENT_SCHEMA = "moneylab.controlled_read.intent/1"
STORED_SCHEMA = "moneylab.controlled_read.stored_result/1"
STATUS_SCHEMA = "moneylab.controlled_read.status/1"
STATUS_ERROR_SCHEMA = "moneylab.controlled_read.status_error/1"

# ERRATA-001 E1.2 (result/1 as corrected before any record was published).
RESULT_KEYS = frozenset({"schema", "command", "status", "exit_code", "task_id", "attempt", "target", "profile",
                         "values", "error", "record", "authority", "approval", "boundary"})
TARGET_KEYS = frozenset({"project_key", "session_id", "selector", "prefix_bytes", "prefix_sha256", "line_count",
                         "trailing_partial_bytes", "prefix_check"})
MEASURED_KEYS = ("prefix_bytes", "prefix_sha256", "line_count", "trailing_partial_bytes")
PREFIX_CHECKS = frozenset({"MATCHED", "TRUNCATED", "CHANGED", "INCOMPLETE"})
# E1.3: the statuses each established prefix_check allows in a stored document (STORE_FAILED is never stored).
CHECK_STATUSES = {"TRUNCATED": frozenset({"SESSION_TRUNCATED"}), "CHANGED": frozenset({"SESSION_CHANGED"}),
                  "INCOMPLETE": frozenset({"TIME_LIMIT_EXCEEDED", "SESSION_UNREADABLE"})}
RECORD_KEYS = frozenset({"file", "final_created", "tmp_leftover"})
STATUS_ERROR_KEYS = frozenset({"schema", "command", "status", "exit_code", "task_id", "attempt", "error",
                               "authority", "boundary"})
STATUS_ERROR_CODES = frozenset({"ARGUMENT_INVALID", "ENVIRONMENT_INVALID"})
# E1.6: codes whose documents are never written to result.json.
NON_STORABLE = frozenset({"ARGUMENT_INVALID", "ENVIRONMENT_INVALID", "STORE_PATH_INVALID", "ATTEMPT_EXISTS",
                          "STORE_FAILED"})
INTENT_KEYS = frozenset({"schema", "task_id", "attempt", "project_key", "session_id", "selector", "profile",
                         "started_utc", "authority", "approval", "boundary"})
STORED_KEYS = frozenset({"schema", "finished_utc", "result"})

RECORD_ROOT = "data/processed/controlled_read"
INTENT_NAME = "intent.json"
RESULT_NAME = "result.json"
READ_LIMIT = 4 * 1024 * 1024  # a record is small; a larger file is not one of ours

RESULT_FOUND = "RESULT_FOUND"
OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
NOT_FOUND = "NOT_FOUND"
RECORD_CORRUPT = "RECORD_CORRUPT"

_UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", re.ASCII)
_HEX64 = re.compile(r"[0-9a-f]{64}", re.ASCII)


def canonical_bytes(obj: Any) -> bytes:
    """D14 serialization plus one LF."""
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return (text + "\n").encode("ascii")


def utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------------- result document


def target(project_key: str, session_id: str, selector: str) -> dict[str, Any]:
    return {"project_key": project_key, "session_id": session_id, "selector": selector, "prefix_bytes": None,
            "prefix_sha256": None, "line_count": None, "trailing_partial_bytes": None, "prefix_check": None}


def profile_ref(profile_id: str) -> dict[str, Any]:
    return {"id": profile_id, "version": PROFILES[profile_id].version}


def store_failure(file: str, error: ControlledReadError) -> dict[str, Any]:
    """E3.1 record object: what the failed create attempt reported, not a proof of any file state."""
    return {"file": file, "final_created": bool(error.final_created), "tmp_leftover": bool(error.tmp_leftover)}


def result_document(status: str, *, task_id: str | None = None, attempt: str | None = None,
                    target: dict[str, Any] | None = None, profile: dict[str, Any] | None = None,
                    values: dict[str, Any] | None = None, record: dict[str, Any] | None = None) -> dict[str, Any]:
    """E1.2 result/1. `target` is copied so a later change of the caller's dict cannot alter this document."""
    succeeded = status == SUCCEEDED
    if succeeded != (values is not None):
        raise ValueError("values must be given exactly when the run succeeded")
    if (status == "STORE_FAILED") != (record is not None):
        raise ValueError("record must be given exactly when storing failed")
    if succeeded and (target is None or target["prefix_check"] != "MATCHED"):
        raise ValueError("a success needs a matched prefix")
    return {"schema": RESULT_SCHEMA, "command": "run", "status": status, "exit_code": 0 if succeeded else 2,
            "task_id": task_id, "attempt": attempt, "target": None if target is None else dict(target),
            "profile": profile, "values": values,
            "error": None if succeeded else {"code": status, "detail": DETAILS[status]}, "record": record,
            "authority": AUTHORITY, "approval": APPROVAL, "boundary": BOUNDARY}


def status_error_document(status: str, *, task_id: str | None = None,
                          attempt: str | None = None) -> dict[str, Any]:
    """E1.5 status_error/1."""
    if status not in STATUS_ERROR_CODES:
        raise ValueError("status_error/1 carries ARGUMENT_INVALID or ENVIRONMENT_INVALID only")
    return {"schema": STATUS_ERROR_SCHEMA, "command": "status", "status": status, "exit_code": 2,
            "task_id": task_id, "attempt": attempt, "error": {"code": status, "detail": DETAILS[status]},
            "authority": AUTHORITY, "boundary": BOUNDARY}


def intent_document(args: grammar.RunArgs, started_utc: str) -> dict[str, Any]:
    return {"schema": INTENT_SCHEMA, "task_id": args.task_id, "attempt": args.attempt,
            "project_key": args.project_key, "session_id": args.session_id, "selector": args.selector,
            "profile": profile_ref(args.profile), "started_utc": started_utc, "authority": AUTHORITY,
            "approval": APPROVAL, "boundary": BOUNDARY}


def stored_result_document(result: dict[str, Any], finished_utc: str) -> dict[str, Any]:
    return {"schema": STORED_SCHEMA, "finished_utc": finished_utc, "result": result}


# ------------------------------------------------------------------------------------------- write


def attempt_rel(task_id: str, attempt: str) -> str:
    return f"{RECORD_ROOT}/{task_id}/{attempt}"


def prepare_attempt(root: Path, task_id: str, attempt: str) -> Path:
    """D15: the intent path must be ignored, no component may be a link, and <NNN> must not exist yet.
    Creates the missing directories and returns the new, empty <NNN> directory."""
    rel = attempt_rel(task_id, attempt)
    try:
        code, _out = collect.run_git(root, "check-ignore", ["-q", "--no-index", f"{rel}/{INTENT_NAME}"],
                                     ok_codes=(0, 1))
    except WorkstateError:
        raise ControlledReadError("STORE_PATH_INVALID") from None
    if code != 0:
        raise ControlledReadError("STORE_PATH_INVALID")
    try:
        existing = collect.check_tree_path(root, rel, "STORE_PATH_INVALID", require_regular=False)
    except WorkstateError:
        raise ControlledReadError("STORE_PATH_INVALID") from None
    if existing is not None:
        raise ControlledReadError("ATTEMPT_EXISTS")
    parts = rel.split("/")
    current = Path(root)
    for index, part in enumerate(parts):
        current = current / part
        try:
            current.mkdir()
        except FileExistsError:
            if index == len(parts) - 1:
                raise ControlledReadError("ATTEMPT_EXISTS") from None
        except OSError:
            # Not a create attempt of a record file, so not STORE_FAILED (E1.3 ties STORE_FAILED to `record`).
            raise ControlledReadError("STORE_PATH_INVALID") from None
    try:
        made = collect.check_tree_path(root, rel, "STORE_PATH_INVALID", require_regular=False)
    except WorkstateError:
        raise ControlledReadError("STORE_PATH_INVALID") from None
    if made is None:
        raise ControlledReadError("STORE_PATH_INVALID")
    return current


def create_record(path: Path, obj: dict[str, Any]) -> None:
    """Create `path` once. A CreateNewError becomes STORE_FAILED carrying what the attempt reported (E3.1),
    whatever final_created says; nothing is removed, replaced or retried."""
    try:
        atomic_create_new_bytes(path, canonical_bytes(obj))
    except CreateNewError as exc:
        error = ControlledReadError("STORE_FAILED")
        error.final_created = bool(exc.final_created)
        error.tmp_leftover = exc.tmp_leftover is not None
        raise error from None


# -------------------------------------------------------------------------------------------- read


def _read(root: Path, rel: str) -> bytes | None:
    """The bytes of a record file, None if it is absent. Raises ValueError for anything else."""
    try:
        st = collect.check_tree_path(root, rel, RECORD_CORRUPT, require_regular=True)
    except WorkstateError:
        raise ValueError("record path is not a plain file") from None
    if st is None:
        return None
    if st.st_size > READ_LIMIT:
        raise ValueError("record too large")
    try:
        with open(Path(root) / rel, "rb") as handle:
            data = handle.read(READ_LIMIT + 1)
    except FileNotFoundError:
        return None
    except OSError:
        raise ValueError("record unreadable") from None
    if len(data) > READ_LIMIT:
        raise ValueError("record too large")
    return data


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = value
    return out


def _reject_constant(name: str) -> Any:
    raise ValueError("non-finite constant")


def _canonical_object(data: bytes) -> dict[str, Any] | None:
    try:
        obj = json.loads(data.decode("ascii"), object_pairs_hook=_no_duplicate_keys,
                         parse_constant=_reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None
    if not isinstance(obj, dict):
        return None
    try:
        if canonical_bytes(obj) != data:
            return None
    except ValueError:
        return None
    return obj


def _count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _valid_profile(value: object) -> bool:
    return (isinstance(value, dict) and set(value) == {"id", "version"} and grammar.valid_profile(value["id"])
            and isinstance(value["version"], int) and not isinstance(value["version"], bool)
            and value["version"] == PROFILES[value["id"]].version)


def _valid_intent(obj: dict[str, Any]) -> bool:
    """D16 (a)."""
    return (set(obj) == INTENT_KEYS and obj["schema"] == INTENT_SCHEMA and grammar.valid_task_id(obj["task_id"])
            and grammar.valid_attempt(obj["attempt"]) and grammar.valid_project_key(obj["project_key"])
            and grammar.valid_session(obj["session_id"]) and grammar.valid_selector(obj["selector"])
            and _valid_profile(obj["profile"]) and isinstance(obj["started_utc"], str)
            and _UTC.fullmatch(obj["started_utc"]) is not None and obj["authority"] == AUTHORITY
            and obj["approval"] == APPROVAL and obj["boundary"] == BOUNDARY)


def _valid_stored(obj: dict[str, Any]) -> bool:
    """D16 (b)."""
    return (set(obj) == STORED_KEYS and obj["schema"] == STORED_SCHEMA and isinstance(obj["finished_utc"], str)
            and _UTC.fullmatch(obj["finished_utc"]) is not None and isinstance(obj["result"], dict))


def _valid_target(tgt: object) -> bool:
    """E1.2 target object with the E1.3 rule that measured fields and prefix_check are null together."""
    if not (isinstance(tgt, dict) and set(tgt) == TARGET_KEYS and grammar.valid_project_key(tgt["project_key"])
            and grammar.valid_session(tgt["session_id"]) and grammar.valid_selector(tgt["selector"])):
        return False
    measured = [tgt[key] for key in MEASURED_KEYS]
    if all(value is None for value in measured):
        return tgt["prefix_check"] is None
    return (_count(tgt["prefix_bytes"]) and isinstance(tgt["prefix_sha256"], str)
            and _HEX64.fullmatch(tgt["prefix_sha256"]) is not None and _count(tgt["line_count"])
            and _count(tgt["trailing_partial_bytes"]) and tgt["prefix_check"] in PREFIX_CHECKS)


def valid_result(doc: dict[str, Any]) -> bool:
    """ERRATA-001 E4 (replaces D16 (c)): a stored result/1 document of a run whose arguments were valid.
    status/1, status_error/1, non-storable codes and documents with a record object never pass. The success
    rule is one-way: SUCCEEDED needs prefix_check MATCHED, but MATCHED may go with any processing failure."""
    if set(doc) != RESULT_KEYS or doc["schema"] != RESULT_SCHEMA or doc["command"] != "run":
        return False
    if doc["authority"] != AUTHORITY or doc["approval"] != APPROVAL or doc["boundary"] != BOUNDARY:
        return False
    if not (grammar.valid_task_id(doc["task_id"]) and grammar.valid_attempt(doc["attempt"])
            and _valid_profile(doc["profile"]) and _valid_target(doc["target"])):
        return False
    status, exit_code, values, error = doc["status"], doc["exit_code"], doc["values"], doc["error"]
    if isinstance(exit_code, bool) or not isinstance(status, str) or doc["record"] is not None:
        return False
    check = doc["target"]["prefix_check"]
    if check in CHECK_STATUSES and status not in CHECK_STATUSES[check]:
        return False
    if status == SUCCEEDED:
        return (exit_code == 0 and error is None and check == "MATCHED" and isinstance(values, dict)
                and set(values) == {"sha256", "bytes", "lf"} and isinstance(values["sha256"], str)
                and _HEX64.fullmatch(values["sha256"]) is not None and _count(values["bytes"])
                and _count(values["lf"]))
    return (status in DETAILS and status not in NON_STORABLE and exit_code == 2 and values is None
            and isinstance(error, dict) and error == {"code": status, "detail": DETAILS[status]})


def _identity_matches(intent: dict[str, Any], result: dict[str, Any], task_id: str, attempt: str) -> bool:
    """D16 (d)."""
    tgt = result["target"]
    return (result["task_id"] == intent["task_id"] == task_id and result["attempt"] == intent["attempt"] == attempt
            and tgt["project_key"] == intent["project_key"] and tgt["session_id"] == intent["session_id"]
            and tgt["selector"] == intent["selector"] and result["profile"]["id"] == intent["profile"]["id"]
            and result["profile"]["version"] == intent["profile"]["version"])


def _sha(data: bytes | None) -> str | None:
    return None if data is None else hashlib.sha256(data).hexdigest()


def status_document(root: Path, task_id: str, attempt: str) -> dict[str, Any]:
    """D16. Reads only the two record files of one attempt."""
    rel = attempt_rel(task_id, attempt)
    intent_raw: bytes | None = None
    result_raw: bytes | None = None
    state, inner = RECORD_CORRUPT, None
    try:
        intent_raw = _read(root, f"{rel}/{INTENT_NAME}")
        result_raw = _read(root, f"{rel}/{RESULT_NAME}")
    except ValueError:
        pass
    else:
        state, inner = _judge(intent_raw, result_raw, task_id, attempt)
    return {"schema": STATUS_SCHEMA, "command": "status", "task_id": task_id, "attempt": attempt, "state": state,
            "intent_sha256": _sha(intent_raw), "result_sha256": _sha(result_raw), "result": inner,
            "authority": AUTHORITY, "boundary": BOUNDARY}


def _judge(intent_raw: bytes | None, result_raw: bytes | None, task_id: str,
           attempt: str) -> tuple[str, dict[str, Any] | None]:
    if intent_raw is None:
        return (NOT_FOUND, None) if result_raw is None else (RECORD_CORRUPT, None)
    intent = _canonical_object(intent_raw)
    if intent is None or not _valid_intent(intent) or intent["task_id"] != task_id or intent["attempt"] != attempt:
        return RECORD_CORRUPT, None
    if result_raw is None:
        return OUTCOME_UNKNOWN, None
    stored = _canonical_object(result_raw)
    if stored is None or not _valid_stored(stored):
        return RECORD_CORRUPT, None
    inner = stored["result"]
    if not valid_result(inner) or not _identity_matches(intent, inner, task_id, attempt):
        return RECORD_CORRUPT, None
    return RESULT_FOUND, inner
