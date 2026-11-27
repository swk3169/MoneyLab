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
from moneylab.controlled_read import profiles
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


# ------------------------------------------------------- candidates/1 (AUTO-15-CONTROLLED-READ-CANDIDATES)
# N3-N6: list every candidate text string of the fixed prefix (at most CANDIDATE_LIMIT) with its position,
# whether its run selector can be written, the verdict of the existing run selection and extraction path,
# and the hash and lengths of its body. No text, context, marker line, key name, type name or unwritable
# identifier is printed, nothing is recorded and no candidate is chosen. A digest match only says that the
# text the run path selected has the candidate's content; it is not evidence of the same position, which
# rests on the selector being unique among the candidates and on _find accepting exactly one target.

CANDIDATES_OPTIONS = ("--task", "--project-key", "--session", "--profile", "--expect-prefix-bytes",
                      "--expect-prefix-sha256")
CANDIDATES_SCHEMA = "moneylab.controlled_read.candidates/1"
CANDIDATES_LISTED = "CANDIDATES_LISTED"
CANDIDATES_LIMIT_EXCEEDED = "CANDIDATES_LIMIT_EXCEEDED"
CANDIDATES_DETAILS: dict[str, str] = {
    CANDIDATES_LISTED: "every candidate of the fixed prefix is listed with its selection result",
    CANDIDATES_LIMIT_EXCEEDED: "the scan stopped because the fixed prefix holds more candidates than the candidate limit",
}
CANDIDATE_LIMIT = 8
CANDIDATES_KEYS = frozenset({"approval", "authority", "boundary", "candidate_count", "candidate_count_at_least",
                             "candidates", "checks", "command", "error", "exit_code", "profile", "schema", "status",
                             "target", "task_id"})
CANDIDATE_ITEM_KEYS = frozenset({"block_index", "index", "is_error", "kind", "line", "selected", "selector",
                                 "text_index", "values"})
# N4: the ControlledReadError codes of parse_selector, select_text and extract, by class.
CANDIDATE_LOCAL_CODES = frozenset({
    "ENTRY_NOT_FOUND", "ENTRY_DUPLICATE", "TOOL_RESULT_ERROR", "TEXT_BLOCK_NOT_FOUND", "ENCODING_INVALID",
    "TEXT_LIMIT_EXCEEDED", "BOM_PRESENT", "CR_PRESENT", "MARKER_MISSING", "MARKER_DUPLICATE",
    "MARKER_ORDER_INVALID", "BODY_EMPTY", "BODY_LIMIT_EXCEEDED"})
CANDIDATES_GLOBAL_CODES = frozenset({
    "TIME_LIMIT_EXCEEDED", "SESSION_CORRUPT", "LINE_LIMIT_EXCEEDED", "ENTRY_LIMIT_EXCEEDED", "FORMAT_UNSUPPORTED",
    "SELECTOR_KIND_MISMATCH", "TEXT_BLOCK_AMBIGUOUS"})
CANDIDATE_OK = "OK"
SELECTOR_UNREPRESENTABLE = "SELECTOR_UNREPRESENTABLE"
SELECTOR_DUPLICATE = "SELECTOR_DUPLICATE"
SELECTION_MISMATCH = "SELECTION_MISMATCH"
CANDIDATE_STATES = frozenset({CANDIDATE_OK, SELECTOR_UNREPRESENTABLE, SELECTOR_DUPLICATE,
                              SELECTION_MISMATCH}) | CANDIDATE_LOCAL_CODES
LIMIT_STOPPED = "LIMIT_STOPPED"
# N6: every status besides CANDIDATES_LISTED with its error detail. Any other status is refused.
CANDIDATES_ERROR_DETAILS: dict[str, str] = {
    CANDIDATES_LIMIT_EXCEEDED: CANDIDATES_DETAILS[CANDIDATES_LIMIT_EXCEEDED],
    "DIAGNOSE_PREFIX_MISMATCH": DIAGNOSE_DETAILS["DIAGNOSE_PREFIX_MISMATCH"],
    "DIAGNOSE_PREFIX_NOT_LINE_ALIGNED": DIAGNOSE_DETAILS["DIAGNOSE_PREFIX_NOT_LINE_ALIGNED"],
    **{code: DETAILS[code] for code in (
        "ARGUMENT_INVALID", "ENVIRONMENT_INVALID", "SESSION_NOT_FOUND", "SESSION_PATH_INVALID", "SESSION_TRUNCATED",
        "SESSION_UNREADABLE", "SESSION_CHANGED", "SESSION_CORRUPT", "LINE_LIMIT_EXCEEDED", "ENTRY_LIMIT_EXCEEDED",
        "TIME_LIMIT_EXCEEDED", "FORMAT_UNSUPPORTED", "SELECTOR_KIND_MISMATCH", "TEXT_BLOCK_AMBIGUOUS")},
}
_OPEN_CODES = frozenset({"SESSION_PATH_INVALID", "SESSION_NOT_FOUND", "SESSION_TRUNCATED", "SESSION_UNREADABLE",
                         "TIME_LIMIT_EXCEEDED", "DIAGNOSE_PREFIX_MISMATCH", "DIAGNOSE_PREFIX_NOT_LINE_ALIGNED"})
_SCAN_CODES = frozenset({"SESSION_CORRUPT", "LINE_LIMIT_EXCEEDED", "ENTRY_LIMIT_EXCEEDED", "TIME_LIMIT_EXCEEDED",
                         "FORMAT_UNSUPPORTED"})
_REHASH_CODES = frozenset({"TIME_LIMIT_EXCEEDED", "SESSION_UNREADABLE", "SESSION_TRUNCATED", "SESSION_CHANGED"})
_SELECTION_CODES = frozenset(CANDIDATES_ERROR_DETAILS) - {
    CANDIDATES_LIMIT_EXCEEDED, "ARGUMENT_INVALID", "DIAGNOSE_PREFIX_MISMATCH", "DIAGNOSE_PREFIX_NOT_LINE_ALIGNED"}
_CHECK_STATUSES = {"TRUNCATED": frozenset({"SESSION_TRUNCATED"}), "CHANGED": frozenset({"SESSION_CHANGED"}),
                   "INCOMPLETE": frozenset({"TIME_LIMIT_EXCEEDED", "SESSION_UNREADABLE"}),
                   "MATCHED": frozenset(CANDIDATES_ERROR_DETAILS) | {CANDIDATES_LISTED}}
_NR, _PASSED, _FAILED = "NOT_REACHED", "PASSED", "FAILED"
_TEXT_INDEX_LIMIT = 8388608
_VALUES_BYTES_LIMIT = 1048576
_CHECK_ROWS: dict[tuple[str, str, str], frozenset[str]] = {
    (_NR, _NR, _NR): frozenset({"ENVIRONMENT_INVALID"}),
    (_FAILED, _NR, _NR): _OPEN_CODES,
    (_PASSED, _FAILED, _NR): _SCAN_CODES | _REHASH_CODES,
    (_PASSED, LIMIT_STOPPED, _NR): frozenset({CANDIDATES_LIMIT_EXCEEDED}) | _REHASH_CODES,
    (_PASSED, _PASSED, _FAILED): _SELECTION_CODES | _REHASH_CODES,
    (_PASSED, _PASSED, _PASSED): frozenset({CANDIDATES_LISTED}) | _REHASH_CODES,
}


def parse_candidates(argv: list[str]) -> DiagnoseArgs:
    """N3 1: the fixed option order and the diagnose value grammar."""
    task_id, project_key, session_id, profile, size, sha = grammar._values(argv, "candidates", CANDIDATES_OPTIONS)
    if not (grammar.valid_task_id(task_id) and grammar.valid_project_key(project_key)
            and grammar.valid_session(session_id) and grammar.valid_profile(profile)):
        raise ControlledReadError("ARGUMENT_INVALID")
    if PREFIX_BYTES.fullmatch(size) is None or not 1 <= int(size) <= PREFIX_LIMIT:
        raise ControlledReadError("ARGUMENT_INVALID")
    if PREFIX_SHA256.fullmatch(sha) is None:
        raise ControlledReadError("ARGUMENT_INVALID")
    return DiagnoseArgs(task_id, project_key, session_id, profile, int(size), sha)


def _local_candidate_code(code: str) -> bool:
    """N4: True for a candidate-level code, False for a code that fails the whole selection. ARGUMENT_INVALID
    cannot come from a selector written by format_selector: it ends the call without a document."""
    if code == "ARGUMENT_INVALID":
        raise RuntimeError("candidate selection reached an impossible state")
    return code in CANDIDATE_LOCAL_CODES


def select_candidates(prefix: bytes, profile: profiles.Profile, found: list[transcript.Candidate],
                      positions: list[tuple[int, int | None, bytes]], deadline: transcript.Deadline,
                      nontext_kwargs: Any) -> tuple[list[dict[str, Any]] | None, str | None]:
    """N3 6 and N5: the items of every candidate in prefix order, or (None, code) when a code fails the whole
    selection (every state and value found so far is dropped). `nontext_kwargs()` gives the keyword arguments
    of one select_text call (a new policy object each time, or nothing)."""
    if len(found) != len(positions):
        raise RuntimeError("candidate positions do not match the candidates")
    written = [grammar.format_selector(c.kind, c.ident, c.text_index) for c in found]
    uses: dict[str, int] = {}
    for selector in written:
        if selector is not None:
            uses[selector] = uses.get(selector, 0) + 1
    items: list[dict[str, Any]] = []
    for index, (candidate, selector, position) in enumerate(zip(found, written, positions), start=1):
        line_no, block_index, digest = position
        values: dict[str, Any] | None = None
        if selector is None:
            state = SELECTOR_UNREPRESENTABLE
        elif uses[selector] > 1:
            state = SELECTOR_DUPLICATE  # the run path cannot tell these apart: select_text is not called
        else:
            try:
                parsed = grammar.parse_selector(selector)
                text = transcript.select_text(prefix, parsed, deadline, **nontext_kwargs())
            except ControlledReadError as exc:
                if not _local_candidate_code(exc.code):
                    return None, exc.code
                state = exc.code
            else:
                if hashlib.sha256(text.encode("utf-8", "surrogatepass")).digest() != digest:
                    state = SELECTION_MISMATCH
                else:
                    try:
                        body = profiles.extract(profile, text)
                    except ControlledReadError as exc:
                        if not _local_candidate_code(exc.code):
                            return None, exc.code
                        state = exc.code
                    else:
                        state = CANDIDATE_OK
                        values = profiles.values(body)
        items.append({"index": index, "line": line_no, "kind": candidate.kind, "block_index": block_index,
                      "text_index": candidate.text_index, "is_error": candidate.is_error, "selector": selector,
                      "selected": state, "values": values})
    return items, None


def _int_in(value: object, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _check_target(target: object, checks: dict[str, Any], status: str) -> int | None:
    """N6 target rules; returns line_count (None before the prefix was fixed)."""
    if not isinstance(target, dict) or set(target) != set(TARGET_KEYS):
        raise ValueError("candidates target keys")
    if not (grammar.valid_project_key(target["project_key"]) and grammar.valid_session(target["session_id"])):
        raise ValueError("candidates target identity")
    size = target["expected_prefix_bytes"]
    if not _int_in(size, 1, PREFIX_LIMIT):
        raise ValueError("candidates expected prefix bytes")
    if not (isinstance(target["expected_prefix_sha256"], str)
            and PREFIX_SHA256.fullmatch(target["expected_prefix_sha256"]) is not None):
        raise ValueError("candidates expected prefix sha256")
    observed = target["observed_size_at_open"]
    if observed is not None and not _int_in(observed, 0, 2 ** 63):
        raise ValueError("candidates observed size")
    check = target["prefix_check"]
    if checks["prefix"] != _PASSED:
        if not (target["trailing_bytes_excluded"] is None and target["line_count"] is None and check is None):
            raise ValueError("candidates target before the prefix")
        if checks["prefix"] == _NR and observed is not None:
            raise ValueError("candidates observed size before the open")
        return None
    if (observed is None or not _int_in(target["trailing_bytes_excluded"], 0, 2 ** 63)
            or target["trailing_bytes_excluded"] != observed - size):
        raise ValueError("candidates trailing bytes")
    if not _int_in(target["line_count"], 1, size):
        raise ValueError("candidates line count")
    if check not in _CHECK_STATUSES or status not in _CHECK_STATUSES[check]:
        raise ValueError("candidates prefix check")
    if status in (CANDIDATES_LISTED, CANDIDATES_LIMIT_EXCEEDED) and check != "MATCHED":
        raise ValueError("candidates need a matched prefix")
    line_count: int = target["line_count"]
    return line_count


def _check_items(items: object, count: object, line_count: int | None, kinds: frozenset[str]) -> None:
    """N6 candidate items."""
    if not isinstance(items, list) or not _int_in(count, 0, CANDIDATE_LIMIT) or len(items) != count:
        raise ValueError("candidates count")
    if items and line_count is None:
        raise ValueError("candidates without a line count")
    uses: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict) or set(item) != CANDIDATE_ITEM_KEYS:
            raise ValueError("candidate item keys")
        if type(item["selector"]) is str:
            uses[item["selector"]] = uses.get(item["selector"], 0) + 1
    previous = 0
    for index, item in enumerate(items, start=1):
        kind, state, selector = item["kind"], item["selected"], item["selector"]
        if type(item["index"]) is not int or item["index"] != index:
            raise ValueError("candidate index")
        if line_count is None or not _int_in(item["line"], max(previous, 1), line_count):
            raise ValueError("candidate line")
        previous = item["line"]
        if kind not in (grammar.ASSISTANT, grammar.TOOL_RESULT) or kind not in kinds:
            raise ValueError("candidate kind")
        if kind == grammar.TOOL_RESULT:
            if not _int_in(item["block_index"], 1, _TEXT_INDEX_LIMIT):
                raise ValueError("candidate block index")
        elif item["block_index"] is not None:
            raise ValueError("candidate block index")
        if not _int_in(item["text_index"], 1, _TEXT_INDEX_LIMIT):
            raise ValueError("candidate text index")
        if type(item["is_error"]) is not bool or (kind == grammar.ASSISTANT and item["is_error"]):
            raise ValueError("candidate is_error")
        if not isinstance(state, str) or state not in CANDIDATE_STATES:
            raise ValueError("candidate selected")
        if state == SELECTOR_UNREPRESENTABLE:
            if selector is not None:
                raise ValueError("candidate selector")
        else:
            if type(selector) is not str or grammar.SELECTOR.fullmatch(selector) is None:
                raise ValueError("candidate selector")
            parsed = grammar.parse_selector(selector)
            if parsed.kind != kind or parsed.text_index != item["text_index"]:
                raise ValueError("candidate selector position")
            if (uses[selector] > 1) != (state == SELECTOR_DUPLICATE):
                raise ValueError("candidate selector uniqueness")
        values = item["values"]
        if state == CANDIDATE_OK:
            if not isinstance(values, dict) or set(values) != {"bytes", "lf", "sha256"}:
                raise ValueError("candidate values keys")
            if not (_int_in(values["bytes"], 1, _VALUES_BYTES_LIMIT)
                    and _int_in(values["lf"], 1, values["bytes"]) and isinstance(values["sha256"], str)
                    and PREFIX_SHA256.fullmatch(values["sha256"]) is not None):
                raise ValueError("candidate values")
        elif values is not None:
            raise ValueError("candidate values without OK")


def check_candidates_document(doc: dict[str, Any]) -> None:
    """N6: every rule of candidates/1; ValueError otherwise. Integers are `type(x) is int` (never bool)."""
    if not isinstance(doc, dict) or set(doc) != CANDIDATES_KEYS:
        raise ValueError("candidates keys")
    if (doc["schema"], doc["command"], doc["authority"], doc["approval"], doc["boundary"]) != (
            CANDIDATES_SCHEMA, "candidates", AUTHORITY, APPROVAL, BOUNDARY):
        raise ValueError("candidates fixed values")
    status = doc["status"]
    listed = status == CANDIDATES_LISTED
    if not isinstance(status, str) or not (listed or status in CANDIDATES_ERROR_DETAILS):
        raise ValueError("not a candidates status")
    if type(doc["exit_code"]) is not int or doc["exit_code"] != (0 if listed else 2):
        raise ValueError("candidates exit code")
    if doc["error"] != (None if listed else {"code": status, "detail": CANDIDATES_ERROR_DETAILS[status]}):
        raise ValueError("candidates error")
    limited = status == CANDIDATES_LIMIT_EXCEEDED
    if not listed and (doc["candidate_count"] is not None or doc["candidates"] is not None):
        raise ValueError("candidates outside CANDIDATES_LISTED")
    if doc["candidate_count_at_least"] != (CANDIDATE_LIMIT + 1 if limited else None) or (
            limited and type(doc["candidate_count_at_least"]) is not int):
        raise ValueError("candidates lower bound")
    if status == "ARGUMENT_INVALID":
        if any(doc[key] is not None for key in ("task_id", "target", "profile", "checks", "candidate_count",
                                               "candidate_count_at_least", "candidates")):
            raise ValueError("candidates ARGUMENT_INVALID carries no identifying field")
        return
    if not grammar.valid_task_id(doc["task_id"]):
        raise ValueError("candidates task_id")
    profile = doc["profile"]
    if not (isinstance(profile, dict) and set(profile) == {"id", "version"}
            and grammar.valid_profile(profile["id"]) and type(profile["version"]) is int
            and profile["version"] == profiles.PROFILES[profile["id"]].version):
        raise ValueError("candidates profile")
    checks = doc["checks"]
    if not isinstance(checks, dict) or set(checks) != {"prefix", "scan", "selected"}:
        raise ValueError("candidates checks keys")
    row = (checks["prefix"], checks["scan"], checks["selected"])
    if row not in _CHECK_ROWS or status not in _CHECK_ROWS[row]:
        raise ValueError("candidates checks")
    line_count = _check_target(doc["target"], checks, status)
    if listed:
        _check_items(doc["candidates"], doc["candidate_count"], line_count, profiles.PROFILES[profile["id"]].kinds)


def candidates_document(status: str, *, task_id: str | None = None, target: dict[str, Any] | None = None,
                        profile: dict[str, Any] | None = None, checks: dict[str, str] | None = None,
                        candidates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """N6 candidates/1, checked before it is returned. Nothing is written: this document only goes to stdout.
    Every given dict and list is copied so a later change of the caller's objects cannot alter it."""
    listed = status == CANDIDATES_LISTED
    items = None if candidates is None else [
        {**item, "values": None if item.get("values") is None else dict(item["values"])} for item in candidates]
    detail = CANDIDATES_ERROR_DETAILS.get(status)
    doc = {"schema": CANDIDATES_SCHEMA, "command": "candidates", "status": status, "exit_code": 0 if listed else 2,
           "task_id": task_id, "target": None if target is None else dict(target),
           "profile": None if profile is None else dict(profile), "checks": None if checks is None else dict(checks),
           "candidate_count": len(items) if listed and items is not None else None,
           "candidate_count_at_least": CANDIDATE_LIMIT + 1 if status == CANDIDATES_LIMIT_EXCEEDED else None,
           "candidates": items if listed else None,
           "error": None if listed else {"code": status, "detail": detail},
           "authority": AUTHORITY, "approval": APPROVAL, "boundary": BOUNDARY}
    check_candidates_document(doc)
    return doc
