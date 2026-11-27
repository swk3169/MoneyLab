"""AUTO-10-CONTROLLED-READ-DIAGNOSE (D1, D5-D8, ERRATA-001 E2): the first unsupported structure of a fixed
prefix.

`diagnose` reads exactly the approved prefix [0, N) of one session file, checks its SHA-256 and that it ends
with LF, runs the precheck scan checks in the same order and reports only where the first FORMAT_UNSUPPORTED
violation is: its line, check ID, applicability, fixed field path, expected type, actual JSON type and
block/item position. No string value, key name, uuid, tool_use_id or text is reported, no selector or values
are made and nothing is recorded. DIAGNOSE_NO_VIOLATION means only that the scan checks found nothing in the
fixed prefix: it is neither PRECHECK_OK nor a selector nor a run success."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from moneylab.controlled_read import APPROVAL, AUTHORITY, BOUNDARY, DETAILS, ControlledReadError, transcript
from moneylab.controlled_read import selector as grammar
from moneylab.workstate import collect
from moneylab.workstate.collect import WorkstateError

DIAGNOSE_OPTIONS = ("--task", "--project-key", "--session", "--profile", "--expect-prefix-bytes",
                    "--expect-prefix-sha256")
DIAGNOSE_SCHEMA = "moneylab.controlled_read.diagnose/1"
DIAGNOSE_VIOLATION_FOUND = "DIAGNOSE_VIOLATION_FOUND"
DIAGNOSE_NO_VIOLATION = "DIAGNOSE_NO_VIOLATION"
# D8: diagnose-only codes. They never become a ControlledReadError and never overlap DETAILS.
DIAGNOSE_DETAILS: dict[str, str] = {
    DIAGNOSE_VIOLATION_FOUND: "the first unsupported structure in the fixed prefix is described in violation",
    DIAGNOSE_NO_VIOLATION: "no unsupported structure was found in the fixed prefix by the scan checks",
    "DIAGNOSE_PREFIX_MISMATCH": "the bytes at the expected prefix do not have the expected sha256",
    "DIAGNOSE_PREFIX_NOT_LINE_ALIGNED": "the expected prefix does not end with LF",
}
DIAGNOSE_KEYS = frozenset({"schema", "command", "status", "exit_code", "task_id", "target", "profile", "checks",
                           "violation", "error", "authority", "approval", "boundary"})
TARGET_KEYS = ("project_key", "session_id", "expected_prefix_bytes", "expected_prefix_sha256",
               "observed_size_at_open", "trailing_bytes_excluded", "line_count", "prefix_check")
VIOLATION_KEYS = frozenset({"check_id", "applicability", "field_path", "expected", "actual_json_type",
                            "block_index", "item_index", "line"})

PREFIX_LIMIT = 64 * 1024 * 1024  # D1: the largest N
PREFIX_BYTES = re.compile(r"[1-9][0-9]{0,7}", re.ASCII)
PREFIX_SHA256 = re.compile(r"[0-9a-f]{64}", re.ASCII)

GLOBAL = "GLOBAL"
SELECTOR_KIND_DEPENDENT = "SELECTOR_KIND_DEPENDENT"
SELECTED_ENTRY_ONLY = "SELECTED_ENTRY_ONLY"
# D4 and ERRATA-001 E2.1: the fixed applicability of each check ID (a report table, not a verdict).
APPLICABILITY: dict[str, str] = {
    "S1": GLOBAL, "S2": GLOBAL, "S3a": SELECTED_ENTRY_ONLY, "S3b": SELECTED_ENTRY_ONLY, "S3c": SELECTED_ENTRY_ONLY,
    "S4a": SELECTOR_KIND_DEPENDENT, "S4b": SELECTED_ENTRY_ONLY, "S4c": SELECTED_ENTRY_ONLY,
    "S4d": SELECTED_ENTRY_ONLY, "S4e": SELECTED_ENTRY_ONLY, "S4f": SELECTED_ENTRY_ONLY,  # AUTO-12 N6
}
# D5: the only (check_id, field_path, expected) triples that are ever printed.
FIELDS = frozenset({
    ("S1", "entry.uuid", "string"),
    ("S2", "user.content[]", "object"), ("S2", "user.content[].type", "string"),
    ("S3a", "assistant.message", "object"), ("S3a", "assistant.message.content", "array"),
    ("S3b", "assistant.content[]", "object"), ("S3b", "assistant.content[].type", "listed_block_type"),
    ("S3c", "assistant.content[].text", "string"),
    ("S4a", "tool_result.tool_use_id", "string"),
    ("S4b", "tool_result.is_error", "bool"),
    ("S4c", "tool_result.content", "string_or_array"),
    ("S4d", "tool_result.content[]", "object"), ("S4d", "tool_result.content[].type", "text_literal"),
    ("S4d", "tool_result.content[].text", "string"),
    ("S4e", "tool_result.content[]", "marker_free_nontext"),  # AUTO-12 N6: a whole marker in a non-text item
    ("S4f", "tool_result.content[]", "within_nontext_scan_limits"),  # AUTO-12 N6: a non-text scan limit
})
JSON_TYPES = frozenset({"missing", "null", "bool", "number", "string", "array", "object"})
UNLISTED_FIELDS = frozenset({"assistant.content[].type", "tool_result.content[].type"})  # string_unlisted
BLOCK_INDEX_CHECKS = frozenset({"S2", "S3b", "S3c", "S4a", "S4b", "S4c", "S4d", "S4e", "S4f"})
ITEM_INDEX_CHECKS = frozenset({"S4d", "S4e", "S4f"})
_NEVER = frozenset({"STORE_PATH_INVALID", "STORE_FAILED", "ATTEMPT_EXISTS"})


class DiagnoseError(Exception):
    """A diagnose-only defined failure (D3). Only DIAGNOSE_DETAILS codes; never used by run or precheck."""

    def __init__(self, code: str) -> None:
        if code not in DIAGNOSE_DETAILS:
            raise ValueError("undefined diagnose error code")
        super().__init__(code)
        self.code = code
        self.detail = DIAGNOSE_DETAILS[code]


@dataclass(frozen=True)
class DiagnoseArgs:
    task_id: str
    project_key: str
    session_id: str
    profile: str
    prefix_bytes: int
    prefix_sha256: str


def parse_diagnose(argv: list[str]) -> DiagnoseArgs:
    """D1: the fixed option order and the run value grammar, plus N and SHA."""
    task_id, project_key, session_id, profile, size, sha = grammar._values(argv, "diagnose", DIAGNOSE_OPTIONS)
    if not (grammar.valid_task_id(task_id) and grammar.valid_project_key(project_key)
            and grammar.valid_session(session_id) and grammar.valid_profile(profile)):
        raise ControlledReadError("ARGUMENT_INVALID")
    if PREFIX_BYTES.fullmatch(size) is None or not 1 <= int(size) <= PREFIX_LIMIT:
        raise ControlledReadError("ARGUMENT_INVALID")
    if PREFIX_SHA256.fullmatch(sha) is None:
        raise ControlledReadError("ARGUMENT_INVALID")
    return DiagnoseArgs(task_id, project_key, session_id, profile, int(size), sha)


def open_fixed_prefix(home: Path, project_key: str, session_id: str, size: int, sha: str,
                      target: dict[str, Any], deadline: transcript.Deadline) -> transcript.Session:
    """D6. Reads [0, size) only. The caller closes `Session.handle`; on any failure after the open the handle
    is closed here before the exception propagates."""
    rel = transcript.session_rel(project_key, session_id)
    try:
        before = collect.check_tree_path(home, rel, "SESSION_PATH_INVALID", require_regular=True)
    except WorkstateError:
        raise ControlledReadError("SESSION_PATH_INVALID") from None
    if before is None:
        raise ControlledReadError("SESSION_NOT_FOUND")
    try:
        handle = open(home / rel, "rb")  # noqa: SIM115 - closed by the caller or below
    except FileNotFoundError:
        raise ControlledReadError("SESSION_NOT_FOUND") from None
    except OSError:
        raise ControlledReadError("SESSION_PATH_INVALID") from None
    try:
        opened = transcript._fstat(handle.fileno())
        if (before.st_size, before.st_dev, before.st_ino) != (opened.st_size, opened.st_dev, opened.st_ino):
            raise ControlledReadError("SESSION_PATH_INVALID")
        observed = opened.st_size
        target["observed_size_at_open"] = observed
        if observed < size:
            raise ControlledReadError("SESSION_TRUNCATED")
        try:
            data = transcript._read_exactly(handle, size, deadline)
        except OSError:
            raise ControlledReadError("SESSION_UNREADABLE") from None
        if len(data) < size:
            raise ControlledReadError("SESSION_TRUNCATED")
        if hashlib.sha256(data).hexdigest() != sha:
            raise DiagnoseError("DIAGNOSE_PREFIX_MISMATCH")
        if data[-1:] != b"\n":
            raise DiagnoseError("DIAGNOSE_PREFIX_NOT_LINE_ALIGNED")
    except BaseException:
        handle.close()
        raise
    target.update(trailing_bytes_excluded=observed - size, line_count=data.count(b"\n"))
    return transcript.Session(handle, data, target)


def _count(value: object, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def violation_object(exc: transcript.FormatViolation) -> dict[str, Any]:
    """D5 violation object of one FormatViolation (checked again by diagnose_document)."""
    return {"check_id": exc.check_id, "applicability": APPLICABILITY.get(exc.check_id), "field_path": exc.field_path,
            "expected": exc.expected, "actual_json_type": exc.actual_json_type, "block_index": exc.block_index,
            "item_index": exc.item_index, "line": exc.line}


def check_violation(violation: dict[str, Any]) -> None:
    """D5 and ERRATA-001 E2.2: every value must be on the fixed lists and in range; ValueError otherwise."""
    if set(violation) != VIOLATION_KEYS:
        raise ValueError("violation keys")
    check_id = violation["check_id"]
    if (check_id, violation["field_path"], violation["expected"]) not in FIELDS:
        raise ValueError("violation field")
    if violation["applicability"] != APPLICABILITY[check_id]:
        raise ValueError("violation applicability")
    actual = violation["actual_json_type"]
    if not (actual in JSON_TYPES or (actual == "string_unlisted" and violation["field_path"] in UNLISTED_FIELDS)):
        raise ValueError("violation actual type")
    limit = transcript.LINE_LIMIT
    if check_id in BLOCK_INDEX_CHECKS:
        if not _count(violation["block_index"], 1, limit):
            raise ValueError("violation block_index")
    elif violation["block_index"] is not None:
        raise ValueError("violation block_index")
    if check_id in ITEM_INDEX_CHECKS:
        if not _count(violation["item_index"], 1, limit):
            raise ValueError("violation item_index")
    elif violation["item_index"] is not None:
        raise ValueError("violation item_index")
    if not _count(violation["line"], 1, transcript.ENTRY_LIMIT):
        raise ValueError("violation line")


def diagnose_document(status: str, *, task_id: str | None = None, target: dict[str, Any] | None = None,
                      profile: dict[str, Any] | None = None, checks: dict[str, str] | None = None,
                      violation: dict[str, Any] | None = None) -> dict[str, Any]:
    """D7 diagnose/1. Nothing is written: this document only goes to stdout. `target`, `checks` and
    `violation` are copied so a later change of the caller's dicts cannot alter this document."""
    ok = status == DIAGNOSE_NO_VIOLATION
    found = status == DIAGNOSE_VIOLATION_FOUND
    if found != (violation is not None):
        raise ValueError("violation must be given exactly when one was found")
    if (ok or found) and (target is None or target["prefix_check"] != transcript.MATCHED):
        raise ValueError("a diagnosis needs a matched prefix")
    if status in DIAGNOSE_DETAILS:
        detail = DIAGNOSE_DETAILS[status]
    elif status in DETAILS and status not in _NEVER:
        detail = DETAILS[status]
    else:
        raise ValueError("not a diagnose status")
    if violation is not None:
        check_violation(violation)
    if target is not None and tuple(target) != TARGET_KEYS:
        raise ValueError("target keys")
    return {"schema": DIAGNOSE_SCHEMA, "command": "diagnose", "status": status, "exit_code": 0 if ok else 2,
            "task_id": task_id, "target": None if target is None else dict(target), "profile": profile,
            "checks": None if checks is None else dict(checks),
            "violation": None if violation is None else dict(violation),
            "error": None if ok else {"code": status, "detail": detail},
            "authority": AUTHORITY, "approval": APPROVAL, "boundary": BOUNDARY}
