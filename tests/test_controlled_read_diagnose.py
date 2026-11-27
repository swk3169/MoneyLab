"""AUTO-10-CONTROLLED-READ-DIAGNOSE: the diagnose command (D1-D8, T1-T9, ERRATA-001 E2 and E3).

Every input is a synthetic session in tmp_path; the real home, real session records and the repository
data/ are never opened or written (the repository record directory is only listed, T7). Path tests compare
the whole diagnose/1 document, so every key is asserted. Non-ASCII synthetic input uses explicit escapes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from moneylab.controlled_read import DETAILS, ERROR_CODES, ControlledReadError, diagnose, profiles, store, transcript
from moneylab.controlled_read import __main__ as cli
from moneylab.workstate import collect

PK = "C--synthetic-project"
SID = "0a1b2c3d-0000-4000-8000-00000000abcd"
UUID = "11111111-2222-4333-8444-555555555555"
UUID2 = "22222222-2222-4333-8444-555555555555"
UUID3 = "33333333-2222-4333-8444-555555555555"
TASK = "AUTO-10-SYNTH"
WO = "ECON-FWD-M20-WO/1"
PREREG = "ECON-FWD-M20-PREREG/1"
WB = "-----BEGIN ECON-FWD-M20 WORK ORDER CANDIDATE-----"
WE = "-----END ECON-FWD-M20 WORK ORDER CANDIDATE-----"
LEAK = b"LEAKTOKEN"  # every marker below starts with it; no output may contain it
LEAK_BODY = "LEAKTOKEN-DIAG-BODY-3c71"
LEAK_KEY = "LEAKTOKEN-DIAG-KEY-8a20"
LEAK_TYPE = "LEAKTOKEN-DIAG-TYPE-51d9"
LEAK_UUID = "LEAKTOKEN-DIAG-UUID-0b6e"
LEAK_ID = "LEAKTOKEN_DIAG_ID_77e4"
LEAK_NONASCII = "LEAKTOKEN-DIAG-\u00e9\u3042-NONASCII"
WO_TEXT = f"{WB}\n{LEAK_BODY}\n{WE}\n"
BODY = (LEAK_BODY + "\n").encode("ascii")
VALUES = {"sha256": hashlib.sha256(BODY).hexdigest(), "bytes": len(BODY), "lf": 1}
MISSING = object()
G, K, E = "GLOBAL", "SELECTOR_KIND_DEPENDENT", "SELECTED_ENTRY_ONLY"
FU, OK = "FORMAT_UNSUPPORTED", "SUCCEEDED"
FOUND, CLEAN = "DIAGNOSE_VIOLATION_FOUND", "DIAGNOSE_NO_VIOLATION"
REPO_RECORDS = Path(cli.__file__).resolve().parents[3] / "data" / "processed" / "controlled_read"
DIAGNOSE_KEYS = {"schema", "command", "status", "exit_code", "task_id", "target", "profile", "checks", "violation",
                 "error", "authority", "approval", "boundary"}


# ------------------------------------------------------------------------------------------ helpers


def line(obj: object) -> bytes:
    return json.dumps(obj).encode("utf-8") + b"\n"


def asst(content: object, uuid: object = UUID2) -> bytes:
    return line({"type": "assistant", "uuid": uuid, "message": {"content": content}})


def user(content: object, uuid: str = UUID3) -> bytes:
    return line({"type": "user", "uuid": uuid, "message": {"content": content}})


def tr(tool_use_id: object = "toolu_ok", content: object = "fine", is_error: object = MISSING) -> dict[str, Any]:
    block: dict[str, Any] = {"type": "tool_result"}
    if tool_use_id is not MISSING:
        block["tool_use_id"] = tool_use_id
    if content is not MISSING:
        block["content"] = content
    if is_error is not MISSING:
        block["is_error"] = is_error
    return block


TEXT = {"type": "text", "text": "fine"}
OK_A = [{"type": "text", "text": "fine"}, {"type": "thinking", "thinking": "hmm"}]
OK_U = [TEXT, TEXT]
NOISE = user("LEAKTOKEN-DIAG-NOISE-4e12")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    (path / ".gitignore").write_bytes(b"data/processed/*\n")
    return path


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return make_repo(tmp_path / "repo")


def session_path(home: Path) -> Path:
    return home / ".claude" / "projects" / PK / f"{SID}.jsonl"


def make_home(tmp_path: Path, lines: list[bytes], name: str = "home") -> Path:
    home = tmp_path / name
    session_path(home).parent.mkdir(parents=True)
    session_path(home).write_bytes(b"".join(lines))
    return home


def data_of(home: Path) -> bytes:
    return session_path(home).read_bytes()


def dargs(n: object, sha_hex: str, profile: str = WO, task: str = TASK) -> list[str]:
    return ["diagnose", "--task", task, "--project-key", PK, "--session", SID, "--profile", profile,
            "--expect-prefix-bytes", str(n), "--expect-prefix-sha256", sha_hex]


def whole(home: Path, profile: str = WO) -> list[str]:
    data = data_of(home)
    return dargs(len(data), sha(data), profile)


def listing(base: Path) -> list[str] | None:
    if not base.exists():
        return None
    return sorted(p.relative_to(base).as_posix() for p in base.rglob("*"))


def target(n: int, sha_hex: str, observed: int | None = None, trailing: int | None = None,
           lines: int | None = None, check: str | None = None) -> dict[str, Any]:
    return {"project_key": PK, "session_id": SID, "expected_prefix_bytes": n, "expected_prefix_sha256": sha_hex,
            "observed_size_at_open": observed, "trailing_bytes_excluded": trailing, "line_count": lines,
            "prefix_check": check}


def fixed(data: bytes, n: int | None = None, check: str = "MATCHED") -> dict[str, Any]:
    size = len(data) if n is None else n
    return target(size, sha(data[:size]), len(data), len(data) - size, data[:size].count(b"\n"), check)


def expected(status: str, tgt: dict[str, Any], prefix: str = "NOT_REACHED", scan: str = "NOT_REACHED",
             violation: dict[str, Any] | None = None, profile: str = WO) -> dict[str, Any]:
    ok = status == CLEAN
    detail = diagnose.DIAGNOSE_DETAILS[status] if status in diagnose.DIAGNOSE_DETAILS else DETAILS[status]
    return {"schema": "moneylab.controlled_read.diagnose/1", "command": "diagnose", "status": status,
            "exit_code": 0 if ok else 2, "task_id": TASK, "target": tgt, "profile": {"id": profile, "version": 1},
            "checks": {"prefix": prefix, "scan": scan}, "violation": violation,
            "error": None if ok else {"code": status, "detail": detail},
            "authority": "NONE", "approval": "NOT_VERIFIED_BY_PROGRAM", "boundary": "DATA_NOT_INSTRUCTIONS"}


def viol(check_id: str, applicability: str, field_path: str, expected_type: str, actual: str,
         block: int | None, item: int | None, line_no: int) -> dict[str, Any]:
    return {"check_id": check_id, "applicability": applicability, "field_path": field_path,
            "expected": expected_type, "actual_json_type": actual, "block_index": block, "item_index": item,
            "line": line_no}


def found(data: bytes, v: dict[str, Any], profile: str = WO) -> dict[str, Any]:
    return expected(FOUND, fixed(data), "PASSED", "FAILED", v, profile)


def clean(data: bytes, profile: str = WO) -> dict[str, Any]:
    return expected(CLEAN, fixed(data), "PASSED", "PASSED", None, profile)


ARG_INVALID = {"schema": "moneylab.controlled_read.diagnose/1", "command": "diagnose", "status": "ARGUMENT_INVALID",
               "exit_code": 2, "task_id": None, "target": None, "profile": None, "checks": None, "violation": None,
               "error": {"code": "ARGUMENT_INVALID", "detail": DETAILS["ARGUMENT_INVALID"]},
               "authority": "NONE", "approval": "NOT_VERIFIED_BY_PROGRAM", "boundary": "DATA_NOT_INSTRUCTIONS"}

OPENED: list[Any] = []


@pytest.fixture(autouse=True)
def track_handles(monkeypatch):
    """D6 3: every handle diagnose opens is closed on every path."""
    OPENED.clear()

    def tracking(path, mode="r", *args, **kwargs):
        handle = open(path, mode, *args, **kwargs)
        OPENED.append(handle)
        return handle
    monkeypatch.setattr(diagnose, "open", tracking, raising=False)
    yield
    assert all(handle.closed for handle in OPENED)


def _forbidden(*_args, **_kwargs):
    raise AssertionError("diagnose touched the record store")


@pytest.fixture
def diag(capsysbinary, monkeypatch, tmp_path):
    """One diagnose call through main(): one canonical document on stdout, nothing on stderr, no record (D8,
    T7), no marker text (T4), every handle closed."""
    def call(root: Path, home: Path, args: list[str]) -> dict[str, Any]:
        before, repo_before = listing(tmp_path), listing(REPO_RECORDS)
        with monkeypatch.context() as m:
            m.setattr(store, "prepare_attempt", _forbidden)
            m.setattr(store, "create_record", _forbidden)
            code = cli.main(args, root=root, home=home)
        out = capsysbinary.readouterr()
        assert out.err == b""
        assert LEAK not in out.out
        assert listing(tmp_path) == before and listing(REPO_RECORDS) == repo_before
        doc = json.loads(out.out)
        assert out.out == store.canonical_bytes(doc)
        assert set(doc) == DIAGNOSE_KEYS
        assert code == doc["exit_code"] and type(doc["exit_code"]) is int
        assert store.valid_result(doc) is False
        assert all(handle.closed for handle in OPENED)
        return doc
    return call


def precheck_doc(capsysbinary, root: Path, home: Path, profile: str = WO) -> dict[str, Any]:
    code = cli.main(["precheck", "--task", TASK, "--project-key", PK, "--session", SID, "--profile", profile],
                    root=root, home=home)
    out = capsysbinary.readouterr()
    assert out.err == b"" and LEAK not in out.out
    doc = json.loads(out.out)
    assert code == doc["exit_code"]
    return doc


class Clock:
    """transcript._monotonic seam: `queue` values are used first, then `now`."""

    def __init__(self) -> None:
        self.now = 0.0
        self.queue: list[float] = []

    def __call__(self) -> float:
        return self.queue.pop(0) if self.queue else self.now


@pytest.fixture
def clock(monkeypatch) -> Clock:
    c = Clock()
    monkeypatch.setattr(transcript, "_monotonic", c)
    return c


@pytest.fixture
def rehash_calls(monkeypatch) -> list[object]:
    calls: list[object] = []
    monkeypatch.setattr(transcript, "_before_rehash", lambda handle: calls.append(handle))
    return calls


# ------------------------------------------------------------------- T1: every D5 pair, located


CASES = [
    ("s1-number", line({"type": "user", "uuid": 7, "message": {"content": "x"}}),
     "S1", G, "entry.uuid", "string", "number", None, None),
    ("s1-null", line({"type": "assistant", "uuid": None, "message": {"content": []}}),
     "S1", G, "entry.uuid", "string", "null", None, None),
    ("s1-array", line({"uuid": [LEAK_KEY]}), "S1", G, "entry.uuid", "string", "array", None, None),
    ("s2-object", user([*OK_U, LEAK_BODY]), "S2", G, "user.content[]", "object", "string", 3, None),
    ("s2-type-number", user([*OK_U, {"type": 5}]), "S2", G, "user.content[].type", "string", "number", 3, None),
    ("s2-type-missing", user([*OK_U, {LEAK_KEY: "x"}]), "S2", G, "user.content[].type", "string", "missing", 3,
     None),
    ("s3a-message", line({"type": "assistant", "uuid": UUID2, "message": LEAK_BODY}),
     "S3a", E, "assistant.message", "object", "string", None, None),
    ("s3a-message-missing", line({"type": "assistant", "uuid": UUID2}),
     "S3a", E, "assistant.message", "object", "missing", None, None),
    ("s3a-content", line({"type": "assistant", "uuid": UUID2, "message": {"content": LEAK_BODY}}),
     "S3a", E, "assistant.message.content", "array", "string", None, None),
    ("s3a-content-missing", line({"type": "assistant", "uuid": UUID2, "message": {}}),
     "S3a", E, "assistant.message.content", "array", "missing", None, None),
    ("s3b-object", asst([*OK_A, 5]), "S3b", E, "assistant.content[]", "object", "number", 3, None),
    ("s3b-unlisted", asst([*OK_A, {"type": LEAK_TYPE}]),
     "S3b", E, "assistant.content[].type", "listed_block_type", "string_unlisted", 3, None),
    ("s3b-list", asst([*OK_A, {"type": ["text", LEAK_TYPE]}]),
     "S3b", E, "assistant.content[].type", "listed_block_type", "array", 3, None),
    ("s3b-dict", asst([*OK_A, {"type": {LEAK_KEY: "text"}}]),
     "S3b", E, "assistant.content[].type", "listed_block_type", "object", 3, None),
    ("s3b-missing", asst([*OK_A, {"text": LEAK_BODY}]),
     "S3b", E, "assistant.content[].type", "listed_block_type", "missing", 3, None),
    ("s3b-null", asst([*OK_A, {"type": None}]),
     "S3b", E, "assistant.content[].type", "listed_block_type", "null", 3, None),
    ("s3b-bool", asst([*OK_A, {"type": True}]),
     "S3b", E, "assistant.content[].type", "listed_block_type", "bool", 3, None),
    ("s3b-number", asst([*OK_A, {"type": 1.5}]),
     "S3b", E, "assistant.content[].type", "listed_block_type", "number", 3, None),
    ("s3c-number", asst([*OK_A, {"type": "text", "text": 5}]),
     "S3c", E, "assistant.content[].text", "string", "number", 3, None),
    ("s3c-missing", asst([*OK_A, {"type": "text"}]),
     "S3c", E, "assistant.content[].text", "string", "missing", 3, None),
    ("s4a-number", user([*OK_U, tr(tool_use_id=5)]),
     "S4a", K, "tool_result.tool_use_id", "string", "number", 3, None),
    ("s4a-missing", user([*OK_U, tr(tool_use_id=MISSING)]),
     "S4a", K, "tool_result.tool_use_id", "string", "missing", 3, None),
    ("s4b-string", user([*OK_U, tr(is_error="yes")]), "S4b", E, "tool_result.is_error", "bool", "string", 3, None),
    ("s4b-null", user([*OK_U, tr(is_error=None)]), "S4b", E, "tool_result.is_error", "bool", "null", 3, None),
    ("s4c-number", user([*OK_U, tr(content=5)]),
     "S4c", E, "tool_result.content", "string_or_array", "number", 3, None),
    ("s4c-missing", user([*OK_U, tr(content=MISSING)]),
     "S4c", E, "tool_result.content", "string_or_array", "missing", 3, None),
    ("s4c-object", user([*OK_U, tr(content={"type": "text", "text": LEAK_BODY})]),
     "S4c", E, "tool_result.content", "string_or_array", "object", 3, None),
    ("s4d-object", user([*OK_U, tr(content=[TEXT, TEXT, LEAK_BODY])]),
     "S4d", E, "tool_result.content[]", "object", "string", 3, 3),
    ("s4d-type-unlisted", user([*OK_U, tr(content=[TEXT, TEXT, {"type": LEAK_TYPE, "text": "x"}])]),
     "S4d", E, "tool_result.content[].type", "text_literal", "string_unlisted", 3, 3),
    ("s4d-type-number", user([*OK_U, tr(content=[TEXT, TEXT, {"type": 5, "text": "x"}])]),
     "S4d", E, "tool_result.content[].type", "text_literal", "number", 3, 3),
    ("s4d-type-list", user([*OK_U, tr(content=[TEXT, TEXT, {"type": ["text"], "text": "x"}])]),
     "S4d", E, "tool_result.content[].type", "text_literal", "array", 3, 3),
    ("s4d-type-missing", user([*OK_U, tr(content=[TEXT, TEXT, {"text": "x"}])]),
     "S4d", E, "tool_result.content[].type", "text_literal", "missing", 3, 3),
    ("s4d-text", user([*OK_U, tr(content=[TEXT, TEXT, {"type": "text", "text": 5}])]),
     "S4d", E, "tool_result.content[].text", "string", "number", 3, 3),
    ("s4d-text-missing", user([*OK_U, tr(content=[TEXT, TEXT, {"type": "text"}])]),
     "S4d", E, "tool_result.content[].text", "string", "missing", 3, 3),
]
CASE_IDS = [case[0] for case in CASES]
BAD_LINES = [case[1] for case in CASES]


@pytest.mark.parametrize("bad, check_id, applicability, path, expected_type, actual, block, item",
                         [case[1:] for case in CASES], ids=CASE_IDS)
def test_t1_each_violation_is_reported_at_its_place(diag, tmp_path, root, bad, check_id, applicability, path,
                                                    expected_type, actual, block, item):
    home = make_home(tmp_path, [NOISE, NOISE, bad])
    data = data_of(home)
    assert diag(root, home, whole(home)) == found(
        data, viol(check_id, applicability, path, expected_type, actual, block, item, 3))


def test_t1_every_d5_pair_is_covered():
    assert {(c[2], c[4], c[5]) for c in CASES} | {("S4e", "tool_result.content[]", "marker_free_nontext"), ("S4f", "tool_result.content[]", "within_nontext_scan_limits")} == set(diagnose.FIELDS)
    assert {**{c[2]: c[3] for c in CASES}, "S4e": E, "S4f": E} == diagnose.APPLICABILITY


@pytest.mark.parametrize("lines, v", [
    ([NOISE, user([TEXT, "x", "x"]), user(["x"])], viol("S2", G, "user.content[]", "object", "string", 2, None, 2)),
    ([NOISE, user([TEXT, tr(content=[TEXT, 5, 5]), tr(content=[5])])],
     viol("S4d", E, "tool_result.content[]", "object", "number", 2, 2, 2)),
    ([NOISE, asst([*OK_A, 7, 7])], viol("S3b", E, "assistant.content[]", "object", "number", 3, None, 2)),
    ([NOISE, NOISE, line({"uuid": 1}), line({"uuid": 1})], viol("S1", G, "entry.uuid", "string", "number", None,
                                                               None, 3)),
])
def test_t1_the_first_of_equal_violations_is_reported(diag, tmp_path, root, lines, v):
    home = make_home(tmp_path, lines)
    assert diag(root, home, whole(home)) == found(data_of(home), v)


def test_t1_location_is_filled_only_where_it_is_none():
    exc = transcript.FormatViolation("S4d", "tool_result.content[]", "object", "number", item_index=3)
    exc._at(block_index=2)
    exc._at(block_index=9)
    exc._at(line=4)
    exc._at(line=8, block_index=7)
    assert (exc.block_index, exc.item_index, exc.line) == (2, 3, 4)
    other = transcript.FormatViolation("S2", "user.content[]", "object", "string", 5)
    other._at(line=1, block_index=1)
    assert (other.block_index, other.item_index, other.line) == (5, None, 1)


# ----------------------------------------------------------------------- T2: same as the precheck


@pytest.mark.parametrize("bad", BAD_LINES, ids=CASE_IDS)
def test_t2_precheck_fails_its_scan_on_the_same_fixture(capsysbinary, tmp_path, root, bad):
    home = make_home(tmp_path, [NOISE, NOISE, bad])
    doc = precheck_doc(capsysbinary, root, home)
    assert (doc["status"], doc["checks"]["scan"], doc["target"]["prefix_check"]) == (FU, "FAILED", "MATCHED")


def test_t2_no_violation(diag, capsysbinary, tmp_path, root):
    home = make_home(tmp_path, [NOISE, asst(OK_A), user([*OK_U, tr(content=[TEXT]), tr(is_error=False)])])
    assert diag(root, home, whole(home)) == clean(data_of(home))
    doc = precheck_doc(capsysbinary, root, home)
    assert (doc["status"], doc["checks"]["scan"]) == ("PRECHECK_NO_CANDIDATE", "PASSED")


# ------------------------------------------------------------------------------ T3: first violation


@pytest.mark.parametrize("lines, profile, v", [
    ([NOISE, user([tr(tool_use_id=5)]), line({"uuid": 7})], WO,
     viol("S4a", K, "tool_result.tool_use_id", "string", "number", 1, None, 2)),
    ([NOISE, line({"type": "user", "uuid": 7, "message": {"content": ["x"]}})], WO,
     viol("S1", G, "entry.uuid", "string", "number", None, None, 2)),
    ([NOISE, line({"type": "assistant", "uuid": 7, "message": "x"})], WO,
     viol("S1", G, "entry.uuid", "string", "number", None, None, 2)),
    ([NOISE, user([tr(tool_use_id=5), "x"])], WO, viol("S2", G, "user.content[]", "object", "string", 2, None, 2)),
    ([NOISE, user([tr(tool_use_id=5, is_error="x")])], WO,
     viol("S4a", K, "tool_result.tool_use_id", "string", "number", 1, None, 2)),
    ([NOISE, user([tr(is_error="x", content=5)])], WO,
     viol("S4b", E, "tool_result.is_error", "bool", "string", 1, None, 2)),
    ([NOISE, user([tr(content=[5]), tr(tool_use_id=5)])], WO,
     viol("S4d", E, "tool_result.content[]", "object", "number", 1, 1, 2)),
    ([NOISE, asst([*OK_A, {"type": ["x"]}]), user([tr(tool_use_id=5)])], PREREG,
     viol("S4a", K, "tool_result.tool_use_id", "string", "number", 1, None, 3)),
])
def test_t3_order_of_the_first_violation(diag, tmp_path, root, lines, profile, v):
    home = make_home(tmp_path, lines)
    assert diag(root, home, whole(home, profile)) == found(data_of(home), v, profile)


def test_t3_prereg_does_not_apply_s3(diag, capsysbinary, tmp_path, root):
    home = make_home(tmp_path, [NOISE, asst([*OK_A, {"type": ["x"]}]), asst("not a list"),
                                line({"type": "assistant", "uuid": UUID2})])
    assert diag(root, home, whole(home, PREREG)) == clean(data_of(home), PREREG)
    doc = precheck_doc(capsysbinary, root, home, PREREG)
    assert (doc["status"], doc["checks"]["scan"]) == ("PRECHECK_NO_CANDIDATE", "PASSED")


# ----------------------------------------------------------------------------------- T4: no leaks


def test_t4_no_value_key_uuid_id_or_text_is_printed(diag, tmp_path, root):
    lines = [
        line({"type": "user", "uuid": LEAK_UUID, LEAK_KEY: LEAK_BODY, "message": {"content": [
            {"type": LEAK_TYPE, "text": LEAK_BODY}, tr(LEAK_ID, LEAK_BODY),
            tr("toolu_2", [{"type": "text", "text": LEAK_NONASCII}])]}}),
        asst([{"type": "text", "text": LEAK_BODY}, {"type": "thinking", "thinking": LEAK_NONASCII},
              {"type": LEAK_TYPE, LEAK_KEY: LEAK_NONASCII}], uuid=LEAK_UUID),
    ]
    home = make_home(tmp_path, lines)
    doc = diag(root, home, whole(home))
    assert doc == found(data_of(home), viol("S3b", E, "assistant.content[].type", "listed_block_type",
                                            "string_unlisted", 3, None, 2))
    assert diag(root, home, whole(home, PREREG)) == clean(data_of(home), PREREG)


GOOD = viol("S4d", E, "tool_result.content[]", "object", "string", 3, 3, 2)


def _document(v: dict[str, Any]) -> dict[str, Any]:
    return diagnose.diagnose_document(FOUND, task_id=TASK, target=target(1, "0" * 64, 1, 0, 1, "MATCHED"),
                                      profile={"id": WO, "version": 1},
                                      checks={"prefix": "PASSED", "scan": "FAILED"}, violation=v)


@pytest.mark.parametrize("change", [
    {"check_id": "S9"}, {"field_path": "tool_result.content[].type"}, {"expected": "string"},
    {"field_path": "entry.uuid"}, {"applicability": G}, {"applicability": None},
    {"actual_json_type": "string_unlisted"}, {"actual_json_type": "integer"}, {"actual_json_type": "STRING"},
    {"block_index": None}, {"block_index": 0}, {"block_index": True}, {"block_index": 2.0},
    {"item_index": None}, {"item_index": -1}, {"line": 0}, {"line": "2"}, {"line": None}, {"extra": 1},
])
def test_t4_document_refuses_values_outside_the_d5_lists(change):
    assert _document(GOOD)["violation"] == GOOD
    with pytest.raises(ValueError):
        _document({**GOOD, **change})


@pytest.mark.parametrize("v", [
    viol("S1", G, "entry.uuid", "string", "number", 1, None, 2),
    viol("S2", G, "user.content[]", "object", "string", 1, 1, 2),
    viol("S3a", E, "assistant.message", "object", "string", 1, None, 2),
    viol("S3b", E, "assistant.content[]", "object", "string_unlisted", 1, None, 2),
    viol("S4a", E, "tool_result.tool_use_id", "string", "number", 1, None, 2),
])
def test_t4_document_refuses_wrong_index_type_or_applicability(v):
    with pytest.raises(ValueError):
        _document(v)


@pytest.mark.parametrize("status, kwargs", [
    (FOUND, {}),
    (CLEAN, {"violation": GOOD}),
    (CLEAN, {"target": target(1, "0" * 64, 1, 0, 1, "CHANGED")}),
    (FOUND, {"target": target(1, "0" * 64), "violation": GOOD}),
    ("STORE_FAILED", {}), ("ATTEMPT_EXISTS", {}), ("PRECHECK_OK", {}), (OK, {}), ("OTHER", {}),
])
def test_diagnose_document_refuses_inconsistent_documents(status, kwargs):
    with pytest.raises(ValueError):
        diagnose.diagnose_document(status, **kwargs)


# ------------------------------------------------------------------------------ T5: fixed prefix


def test_t5_trailing_bytes_are_excluded(diag, tmp_path, root):
    prefix_lines = [NOISE, asst([*OK_A, 5])]
    home = make_home(tmp_path, [*prefix_lines, b"not json\n", b'{"partial'])
    data = data_of(home)
    n = len(b"".join(prefix_lines))
    v = viol("S3b", E, "assistant.content[]", "object", "number", 3, None, 2)
    doc = diag(root, home, dargs(n, sha(data[:n])))
    assert doc == expected(FOUND, fixed(data, n), "PASSED", "FAILED", v)
    assert doc["target"]["trailing_bytes_excluded"] == len(data) - n == len(b'not json\n{"partial')
    other = make_home(tmp_path, prefix_lines, "home2")
    assert diag(root, other, whole(other)) == found(data_of(other), v)


def test_t5_hash_mismatch(diag, tmp_path, root):
    home = make_home(tmp_path, [NOISE, NOISE])
    data = data_of(home)
    assert diag(root, home, dargs(len(data), "0" * 64)) == expected(
        "DIAGNOSE_PREFIX_MISMATCH", target(len(data), "0" * 64, len(data)), "FAILED")


def test_t5_session_shorter_than_the_prefix(diag, tmp_path, root):
    home = make_home(tmp_path, [NOISE])
    data = data_of(home)
    assert diag(root, home, dargs(len(data) + 1, sha(data))) == expected(
        "SESSION_TRUNCATED", target(len(data) + 1, sha(data), len(data)), "FAILED")


def test_t5_prefix_not_line_aligned_and_mismatch_first(diag, tmp_path, root):
    home = make_home(tmp_path, [NOISE, NOISE])
    data = data_of(home)
    n = len(data) - 1
    assert diag(root, home, dargs(n, sha(data[:n]))) == expected(
        "DIAGNOSE_PREFIX_NOT_LINE_ALIGNED", target(n, sha(data[:n]), len(data)), "FAILED")
    assert diag(root, home, dargs(n, "0" * 64)) == expected(
        "DIAGNOSE_PREFIX_MISMATCH", target(n, "0" * 64, len(data)), "FAILED")
    assert diag(root, home, dargs(1, sha(data[:1]))) == expected(
        "DIAGNOSE_PREFIX_NOT_LINE_ALIGNED", target(1, sha(data[:1]), len(data)), "FAILED")


def test_t5_largest_n_is_accepted(diag, tmp_path, root):
    home = make_home(tmp_path, [NOISE])
    data = data_of(home)
    assert diag(root, home, dargs(67108864, sha(data))) == expected(
        "SESSION_TRUNCATED", target(67108864, sha(data), len(data)), "FAILED")


@pytest.mark.parametrize("n", ["0", "012", "67108865", "99999999", "123456789", "-1", "1.0", "+1", " 1", "", "1e3"])
def test_t5_n_outside_the_grammar(diag, tmp_path, n):
    args = dargs(1, "0" * 64)
    args[10] = n
    assert diag(tmp_path / "unused", tmp_path / "unused", args) == ARG_INVALID
    assert not (tmp_path / "unused").exists()


@pytest.mark.parametrize("sha_hex", ["A" * 64, "0" * 63, "0" * 65, "g" * 64, "0" * 63 + "F", ""])
def test_t5_sha_outside_the_grammar(diag, tmp_path, sha_hex):
    assert diag(tmp_path / "unused", tmp_path / "unused", dargs(1, sha_hex)) == ARG_INVALID


def test_t5_session_larger_than_64_mib(diag, capsysbinary, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [NOISE, asst([*OK_A, 5])])
    data = data_of(home)
    n = len(data)
    big = 64 * 1024 * 1024 + 7
    real = os.stat(session_path(home))
    fake = SimpleNamespace(st_size=big, st_dev=real.st_dev, st_ino=real.st_ino, st_mode=real.st_mode)
    monkeypatch.setattr(collect, "check_tree_path", lambda *_args, **_kwargs: fake)
    monkeypatch.setattr(transcript, "_fstat", lambda _fd: fake)
    calls: list[tuple[int, int]] = []
    real_read = transcript._read_exactly

    def spy(handle, size, deadline):
        got = real_read(handle, size, deadline)
        calls.append((size, len(got)))
        return got
    monkeypatch.setattr(transcript, "_read_exactly", spy)
    v = viol("S3b", E, "assistant.content[]", "object", "number", 3, None, 2)
    assert diag(root, home, dargs(n, sha(data))) == expected(
        FOUND, target(n, sha(data), big, big - n, 2, "MATCHED"), "PASSED", "FAILED", v)
    assert len(calls) == 2 and all(size == n and got <= n for size, got in calls)
    assert precheck_doc(capsysbinary, root, home)["status"] == "SESSION_LIMIT_EXCEEDED"


@pytest.mark.parametrize("args", [
    ["diagnose"],
    dargs(1, "0" * 64) + ["x"],
    dargs(1, "0" * 64)[:9] + ["--expect-prefix-sha256", "0" * 64, "--expect-prefix-bytes", "1"],
    dargs(1, "0" * 64)[:7] + ["--selector", f"assistant:{UUID}"] + dargs(1, "0" * 64)[7:],
    dargs(1, "0" * 64)[:-2],
    ["diagnose", "--project-key", PK, "--task", TASK] + dargs(1, "0" * 64)[5:],
    dargs(1, "0" * 64, profile="OTHER-DOC/1"),
    dargs(1, "0" * 64, task="A" * 65),
    dargs(1, "0" * 64)[:3] + ["--project-key", "../x"] + dargs(1, "0" * 64)[5:],
])
def test_g1_argument_invalid(diag, tmp_path, args):
    assert diag(tmp_path / "unused", tmp_path / "unused", args) == ARG_INVALID
    assert not (tmp_path / "unused").exists()


def test_g2_root_that_is_not_a_git_top_level(diag, tmp_path):
    home = make_home(tmp_path, [NOISE])
    plain = tmp_path / "plain"
    plain.mkdir()
    data = data_of(home)
    assert diag(plain, home, whole(home)) == expected("ENVIRONMENT_INVALID", target(len(data), sha(data)))


def test_g2_relative_home(diag, tmp_path, root):
    assert diag(root, Path("relative-home"), dargs(5, "0" * 64)) == expected(
        "ENVIRONMENT_INVALID", target(5, "0" * 64))


@pytest.mark.parametrize("lines, code, limit", [
    ([NOISE, b"not json\n"], "SESSION_CORRUPT", None),
    ([NOISE, b"[1]\n"], "SESSION_CORRUPT", None),
    ([NOISE, NOISE], "LINE_LIMIT_EXCEEDED", ("LINE_LIMIT", 20)),
    ([NOISE, NOISE], "ENTRY_LIMIT_EXCEEDED", ("ENTRY_LIMIT", 1)),
])
def test_g4b_scan_failures(diag, tmp_path, root, monkeypatch, rehash_calls, lines, code, limit):
    home = make_home(tmp_path, lines)
    if limit is not None:
        monkeypatch.setattr(transcript, *limit)
    assert diag(root, home, whole(home)) == expected(code, fixed(data_of(home)), "PASSED", "FAILED")
    assert len(rehash_calls) == 1


# --------------------------------------------------------------------- T6: time and the re-hash


def test_t6_time_out_while_reading_the_prefix(diag, tmp_path, root, monkeypatch, clock):
    home = make_home(tmp_path, [NOISE, NOISE])
    data = data_of(home)
    real = transcript._fstat

    def fstat_then_expire(fd):
        result = real(fd)
        clock.now = 1000.0
        return result
    monkeypatch.setattr(transcript, "_fstat", fstat_then_expire)
    assert diag(root, home, whole(home)) == expected(
        "TIME_LIMIT_EXCEEDED", target(len(data), sha(data), len(data)), "FAILED")


def test_t6_time_out_while_scanning_skips_the_rehash(diag, tmp_path, root, monkeypatch, clock, rehash_calls):
    home = make_home(tmp_path, [NOISE, NOISE, asst([*OK_A, 5])])
    real = transcript.parse_line

    def parse_then_expire(raw: bytes) -> dict[str, Any]:
        clock.now = 1000.0
        return real(raw)
    monkeypatch.setattr(transcript, "parse_line", parse_then_expire)
    assert diag(root, home, whole(home)) == expected(
        "TIME_LIMIT_EXCEEDED", fixed(data_of(home), check="INCOMPLETE"), "PASSED", "FAILED")
    assert rehash_calls == []


def _truncate(home: Path):
    def change(_handle):
        os.truncate(session_path(home), 5)
    return change


def _overwrite(home: Path):
    def change(_handle):
        with open(session_path(home), "r+b") as f:
            f.write(b"[")
    return change


@pytest.mark.parametrize("violating", [True, False])
@pytest.mark.parametrize("kind, code, check", [
    ("truncate", "SESSION_TRUNCATED", "TRUNCATED"),
    ("overwrite", "SESSION_CHANGED", "CHANGED"),
    ("unreadable", "SESSION_UNREADABLE", "INCOMPLETE"),
    ("expired_before", "TIME_LIMIT_EXCEEDED", "INCOMPLETE"),
    ("expired_after", "TIME_LIMIT_EXCEEDED", "MATCHED"),
])
def test_t6_rehash_replaces_the_diagnosis(diag, tmp_path, root, monkeypatch, clock, violating, kind, code, check):
    home = make_home(tmp_path, [NOISE, asst([*OK_A, 5]) if violating else asst(OK_A)])
    data = data_of(home)

    def fail(*_args):
        raise OSError("gone")

    def expire_after_read(_handle):
        clock.queue = [0.0]
        clock.now = 1000.0
    hooks = {"truncate": _truncate(home), "overwrite": _overwrite(home),
             "unreadable": lambda _h: monkeypatch.setattr(transcript, "_fstat", fail),
             "expired_after": expire_after_read}
    if kind == "expired_before":
        real = transcript.scan_candidates

        def scan_then_expire(*args):
            try:
                return real(*args)
            finally:
                clock.now = 1000.0
        monkeypatch.setattr(transcript, "scan_candidates", scan_then_expire)
    else:
        monkeypatch.setattr(transcript, "_before_rehash", hooks[kind])
    assert diag(root, home, whole(home)) == expected(
        code, fixed(data, check=check), "PASSED", "FAILED" if violating else "PASSED")


def test_t6_unreadable_while_opening(diag, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [NOISE])
    data = data_of(home)

    def fail(*_args):
        raise OSError("gone")
    monkeypatch.setattr(transcript, "_read_exactly", fail)
    assert diag(root, home, whole(home)) == expected(
        "SESSION_UNREADABLE", target(len(data), sha(data), len(data)), "FAILED")


def test_t6_changed_between_the_path_check_and_the_open(diag, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [NOISE])
    data = data_of(home)
    real = os.fstat

    def other_file(fd):
        st = real(fd)
        return SimpleNamespace(st_size=st.st_size, st_dev=st.st_dev, st_ino=st.st_ino + 1)
    monkeypatch.setattr(transcript, "_fstat", other_file)
    assert diag(root, home, whole(home)) == expected(
        "SESSION_PATH_INVALID", target(len(data), sha(data)), "FAILED")


@pytest.mark.parametrize("error, code", [(FileNotFoundError, "SESSION_NOT_FOUND"),
                                         (PermissionError, "SESSION_PATH_INVALID")])
def test_t6_open_failure(diag, tmp_path, root, monkeypatch, error, code):
    home = make_home(tmp_path, [NOISE])
    data = data_of(home)

    def refuse(*_args, **_kwargs):
        raise error("no")
    monkeypatch.setattr(diagnose, "open", refuse, raising=False)
    assert diag(root, home, whole(home)) == expected(code, target(len(data), sha(data)), "FAILED")


def test_undefined_exception_propagates_without_output(capsysbinary, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [NOISE])

    def boom(*_args):
        raise RuntimeError("bug")
    monkeypatch.setattr(transcript, "scan_candidates", boom)
    with pytest.raises(RuntimeError):
        cli.main(whole(home), root=root, home=home)
    assert capsysbinary.readouterr() == (b"", b"")


# ----------------------------------------------------------------------------- T8: path defence


def make_dir_link(link: Path, to: Path) -> None:
    if sys.platform == "win32":
        import _winapi
        _winapi.CreateJunction(str(to), str(link))
    else:
        os.symlink(to, link, target_is_directory=True)


def test_t8_missing_session(diag, tmp_path, root):
    home = tmp_path / "home"
    home.mkdir()
    assert diag(root, home, dargs(1, "0" * 64)) == expected("SESSION_NOT_FOUND", target(1, "0" * 64), "FAILED")


def test_t8_link_component(diag, tmp_path, root):
    real = make_home(tmp_path, [NOISE], "real")
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    make_dir_link(home / ".claude" / "projects", real / ".claude" / "projects")
    assert session_path(home).read_bytes() == data_of(real)  # the link really leads to the session
    data = data_of(real)
    assert diag(root, home, whole(real)) == expected(
        "SESSION_PATH_INVALID", target(len(data), sha(data)), "FAILED")


def test_t8_non_directory_parent_and_non_regular_session(diag, tmp_path, root):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "projects").write_bytes(b"x")
    assert diag(root, home, dargs(1, "0" * 64)) == expected("SESSION_PATH_INVALID", target(1, "0" * 64), "FAILED")
    other = tmp_path / "other"
    session_path(other).mkdir(parents=True)
    assert diag(root, other, dargs(1, "0" * 64)) == expected("SESSION_PATH_INVALID", target(1, "0" * 64), "FAILED")


# ------------------------------------------------------------------------ T9 (b): golden run tests


SA = f"assistant:{UUID}"
ST = "tool_result:toolu_T"
BASE_A = asst([{"type": "text", "text": WO_TEXT}], uuid=UUID)
BASE_T = user([tr("toolu_T", WO_TEXT)])


def target_asst(*extra: object) -> bytes:
    return asst([{"type": "text", "text": WO_TEXT}, *extra], uuid=UUID)


def run_expected(status: str, data: bytes, selector: str, attempt: str) -> dict[str, Any]:
    """AUTO-08 E1.2 result/1, written out key by key."""
    prefix = data[:data.rfind(b"\n") + 1]
    ok = status == OK
    return {"schema": "moneylab.controlled_read.result/1", "command": "run", "status": status,
            "exit_code": 0 if ok else 2, "task_id": TASK, "attempt": attempt,
            "target": {"project_key": PK, "session_id": SID, "selector": selector, "prefix_bytes": len(prefix),
                       "prefix_sha256": sha(prefix), "line_count": prefix.count(b"\n"),
                       "trailing_partial_bytes": len(data) - len(prefix), "prefix_check": "MATCHED"},
            "profile": {"id": WO, "version": 1}, "values": VALUES if ok else None,
            "error": None if ok else {"code": status, "detail": DETAILS[status]}, "record": None,
            "authority": "NONE", "approval": "NOT_VERIFIED_BY_PROGRAM", "boundary": "DATA_NOT_INSTRUCTIONS"}


def precheck_expected(data: bytes, profile: str) -> dict[str, Any]:
    """AUTO-09 D9 precheck/1 of a scan failure, written out key by key."""
    prefix = data[:data.rfind(b"\n") + 1]
    return {"schema": "moneylab.controlled_read.precheck/1", "command": "precheck", "status": FU, "exit_code": 2,
            "task_id": TASK,
            "target": {"project_key": PK, "session_id": SID, "prefix_bytes": len(prefix),
                       "prefix_sha256": sha(prefix), "line_count": prefix.count(b"\n"),
                       "trailing_partial_bytes": len(data) - len(prefix), "prefix_check": "MATCHED"},
            "profile": {"id": profile, "version": 1}, "checks": {"scan": "FAILED", "selected": "NOT_REACHED"},
            "candidate_count": None, "selector": None, "values": None,
            "error": {"code": FU, "detail": DETAILS[FU]},
            "authority": "NONE", "approval": "NOT_VERIFIED_BY_PROGRAM", "boundary": "DATA_NOT_INSTRUCTIONS"}


def run_doc(capsysbinary, root: Path, home: Path, selector: str, attempt: str) -> dict[str, Any]:
    code = cli.main(["run", "--task", TASK, "--project-key", PK, "--session", SID, "--selector", selector,
                     "--profile", WO, "--attempt", attempt], root=root, home=home)
    out = capsysbinary.readouterr()
    assert out.err == b"" and LEAK not in out.out  # ERRATA-001 E3.6 (e)
    doc = json.loads(out.out)
    assert code == doc["exit_code"]
    return doc


GOLDEN = [
    ("s1", [NOISE, BASE_A, BASE_T, line({"type": "user", "uuid": 7, "message": {"content": "x"}})], FU, FU,
     (WO, PREREG)),
    ("s2", [NOISE, BASE_A, BASE_T, user(["x"])], FU, FU, (WO, PREREG)),
    ("s3a-target", [NOISE, line({"type": "assistant", "uuid": UUID, "message": "x"}), BASE_T], FU, OK, (WO,)),
    ("s3b-target-list", [NOISE, target_asst({"type": ["text", LEAK_TYPE]}), BASE_T], FU, OK, (WO,)),
    ("s3b-target-dict", [NOISE, target_asst({"type": {LEAK_KEY: "text"}}), BASE_T], FU, OK, (WO,)),
    ("s3b-target-unlisted", [NOISE, target_asst({"type": "image"}), BASE_T], FU, OK, (WO,)),
    ("s3c-target", [NOISE, target_asst({"type": "text", "text": 5}), BASE_T], FU, OK, (WO,)),
    ("s3a-other", [NOISE, BASE_A, line({"type": "assistant", "uuid": UUID2, "message": "x"}), BASE_T], OK, OK,
     (WO,)),
    ("s3b-other-list", [NOISE, BASE_A, asst([{"type": ["text", LEAK_TYPE]}]), BASE_T], OK, OK, (WO,)),
    ("s3b-other-dict", [NOISE, BASE_A, asst([{"type": {LEAK_KEY: 1}}]), BASE_T], OK, OK, (WO,)),
    ("s3c-other", [NOISE, BASE_A, asst([{"type": "text", "text": 5}]), BASE_T], OK, OK, (WO,)),
    ("s4a", [NOISE, BASE_A, BASE_T, user([tr(tool_use_id=5)])], OK, FU, (WO, PREREG)),
    ("s4b-target", [NOISE, BASE_A, user([tr("toolu_T", WO_TEXT, is_error="yes")])], OK, FU, (WO, PREREG)),
    ("s4c-target", [NOISE, BASE_A, user([tr("toolu_T", 5)])], OK, FU, (WO, PREREG)),
    ("s4d-target", [NOISE, BASE_A, user([tr("toolu_T", [{"type": "text", "text": WO_TEXT}, 5])])], OK, FU,
     (WO, PREREG)),
    ("s4b-other", [NOISE, BASE_A, BASE_T, user([tr("toolu_N", "x", is_error="yes")])], OK, OK, (WO, PREREG)),
    ("s4c-other", [NOISE, BASE_A, BASE_T, user([tr("toolu_N", 5)])], OK, OK, (WO, PREREG)),
    ("s4d-other", [NOISE, BASE_A, BASE_T, user([tr("toolu_N", [5])])], OK, OK, (WO, PREREG)),
]


@pytest.mark.parametrize("lines, run_assistant, run_tool, precheck_profiles", [g[1:] for g in GOLDEN],
                         ids=[g[0] for g in GOLDEN])
def test_t9b_golden_run_and_precheck(capsysbinary, tmp_path, root, lines, run_assistant, run_tool,
                                     precheck_profiles):
    home = make_home(tmp_path, lines)
    data = data_of(home)
    for attempt, selector, status in (("001", SA, run_assistant), ("002", ST, run_tool)):
        assert run_doc(capsysbinary, root, home, selector, attempt) == run_expected(status, data, selector, attempt)
    for profile in precheck_profiles:
        assert precheck_doc(capsysbinary, root, home, profile) == precheck_expected(data, profile)


def test_e3_registered_block_types_still_pass(diag, capsysbinary, tmp_path, root):
    lines = [NOISE, asst([{"type": "thinking", "thinking": "t"}, {"type": "redacted_thinking", "data": "d"},
                          {"type": "tool_use", "id": "toolu_x", "name": "n", "input": {}},
                          {"type": "text", "text": WO_TEXT}], uuid=UUID)]
    home = make_home(tmp_path, lines)
    data = data_of(home)
    assert diag(root, home, whole(home)) == clean(data)
    assert run_doc(capsysbinary, root, home, SA, "001") == run_expected(OK, data, SA, "001")


@pytest.mark.parametrize("bad_type", [["text"], {"text": "text"}, ["text", LEAK_TYPE], {LEAK_KEY: LEAK_BODY}])
def test_e3_list_and_dict_type_raise_no_type_error(bad_type):
    entry = {"type": "assistant", "message": {"content": [*OK_A, {"type": bad_type}]}}
    with pytest.raises(ControlledReadError) as err:
        transcript._assistant_texts(entry)
    assert type(err.value) is transcript.FormatViolation and err.value.code == FU
    assert (err.value.check_id, err.value.actual_json_type, err.value.block_index) == (
        "S3b", "array" if isinstance(bad_type, list) else "object", 3)
    assert LEAK_TYPE not in repr(vars(err.value)) and LEAK_KEY not in repr(vars(err.value))


# --------------------------------------------------------------- T9 (c) and (d): error and dispatch


@pytest.mark.parametrize("bad", BAD_LINES, ids=CASE_IDS)
def test_t9c_a_violation_is_the_format_unsupported_error(bad):
    with pytest.raises(ControlledReadError) as err:
        transcript.scan_candidates(NOISE + bad, profiles.WORK_ORDER.kinds, lambda _text: False,
                                   transcript.Deadline())
    exc = err.value
    assert type(exc) is transcript.FormatViolation
    assert (exc.code, exc.detail, exc.args, exc.final_created, exc.tmp_leftover) == (
        FU, DETAILS[FU], (FU,), None, None)
    assert str(exc) == FU and exc.line == 2


def test_t9d_dispatch(tmp_path):
    unused = tmp_path / "unused"
    doc = cli.run(["diagnose"], root=unused, home=unused)
    assert doc == ARG_INVALID
    for argv in (["diagnosex"], ["scan"], ["Diagnose"], []):
        doc = cli.run(argv, root=unused, home=unused)
        assert (doc["schema"], doc["command"], doc["status"]) == (
            "moneylab.controlled_read.result/1", "run", "ARGUMENT_INVALID")
        assert set(doc) == store.RESULT_KEYS
    assert not unused.exists()


# ------------------------------------------------------------------------------------- separation


def test_diagnose_codes_and_constants():
    assert diagnose.DIAGNOSE_DETAILS == {
        "DIAGNOSE_VIOLATION_FOUND": "the first unsupported structure in the fixed prefix is described in violation",
        "DIAGNOSE_NO_VIOLATION": "no unsupported structure was found in the fixed prefix by the scan checks",
        "DIAGNOSE_PREFIX_MISMATCH": "the bytes at the expected prefix do not have the expected sha256",
        "DIAGNOSE_PREFIX_NOT_LINE_ALIGNED": "the expected prefix does not end with LF",
    }
    assert set(diagnose.DIAGNOSE_DETAILS).isdisjoint(DETAILS)
    assert set(diagnose.DIAGNOSE_DETAILS).isdisjoint(store.PRECHECK_DETAILS)
    for code in diagnose.DIAGNOSE_DETAILS:
        with pytest.raises(ValueError):
            ControlledReadError(code)
        assert diagnose.DiagnoseError(code).code == code
    for code in (FU, "PRECHECK_OK", "OTHER"):
        with pytest.raises(ValueError):
            diagnose.DiagnoseError(code)
    assert ERROR_CODES == tuple(DETAILS)
    assert diagnose.DIAGNOSE_SCHEMA == "moneylab.controlled_read.diagnose/1"
    assert diagnose.DIAGNOSE_OPTIONS == ("--task", "--project-key", "--session", "--profile",
                                         "--expect-prefix-bytes", "--expect-prefix-sha256")
    assert diagnose.APPLICABILITY == {"S1": G, "S2": G, "S3a": E, "S3b": E, "S3c": E, "S4a": K, "S4b": E,
                                      "S4c": E, "S4d": E, "S4e": E, "S4f": E}


def test_parse_diagnose():
    assert diagnose.parse_diagnose(dargs(5, "a" * 64)) == diagnose.DiagnoseArgs(TASK, PK, SID, WO, 5, "a" * 64)
    assert diagnose.parse_diagnose(dargs(67108864, "0" * 64, PREREG)).prefix_bytes == 67108864
    for bad in (dargs(5, "a" * 64)[:-1], ["precheck", *dargs(5, "a" * 64)[1:]], dargs(5, "a" * 64) + ["--x"]):
        with pytest.raises(ControlledReadError) as err:
            diagnose.parse_diagnose(bad)
        assert err.value.code == "ARGUMENT_INVALID"


# ----------------------------------------------------- ERRATA-002 F1.5: repository hygiene acceptance
# The hygiene module is loaded under its own name; nothing here changes the real contract files. Synthetic
# strings that match a secret pattern use explicit \x escapes so this file's own text does not (F1.5).

_HYGIENE_SPEC = importlib.util.spec_from_file_location("moneylab_repo_hygiene_for_diagnose",
                                                       Path(__file__).resolve().parent / "test_repo_hygiene.py")
hygiene = importlib.util.module_from_spec(_HYGIENE_SPEC)
_HYGIENE_SPEC.loader.exec_module(hygiene)

SYN_PATH = "docs/tasks/SYNTH-TASK/WORK_ORDER.md"
SYN_HOME = "approval folder C\x3a\x2fUsers\x2fsynthetic-user\x2fapprovals\n"
SYN_EMAIL = "contact someone\x40gmail.com\n"
HOME = "user home path"


def test_hygiene_accepts_the_home_path_only_for_the_fixed_path_and_bytes(monkeypatch):
    doc = SYN_HOME.encode("ascii")
    monkeypatch.setattr(hygiene, "HOME_PATH_ACCEPTED", {SYN_PATH: sha(doc)})
    found = hygiene.secret_hits(doc.decode("ascii"))
    assert found == [HOME]
    assert hygiene.accepted_hits(SYN_PATH, doc, found) == []
    crlf = doc.replace(b"\n", b"\r\n")
    assert hygiene.accepted_hits(SYN_PATH, crlf, hygiene.secret_hits(crlf.decode("ascii"))) == []
    changed = doc.replace(b"approval folder", b"approval Folder")
    assert hygiene.accepted_hits(SYN_PATH, changed, hygiene.secret_hits(changed.decode("ascii"))) == [HOME]
    for other in ("docs/tasks/SYNTH-TASK/ERRATA-001.md", "docs/tasks/synth-task/WORK_ORDER.md", "WORK_ORDER.md"):
        assert hygiene.accepted_hits(other, doc, found) == [HOME]


def test_hygiene_acceptance_keeps_every_other_label(monkeypatch):
    doc = (SYN_HOME + SYN_EMAIL).encode("ascii")
    monkeypatch.setattr(hygiene, "HOME_PATH_ACCEPTED", {SYN_PATH: sha(doc)})
    found = hygiene.secret_hits(doc.decode("ascii"))
    assert found == ["personal email", HOME]
    assert hygiene.accepted_hits(SYN_PATH, doc, found) == ["personal email"]


def test_hygiene_detectors_are_unchanged():
    assert hygiene.secret_hits("see C\x3a\x5cUsers\x5cbob\x5cnotes.txt") == [HOME]
    assert hygiene.secret_hits("key \x41KIAABCDEFGHIJKLMNOP here") == ["aws access key"]
    assert hygiene.secret_hits("mail bob\x40naver.com") == ["personal email"]
    assert hygiene.secret_hits("plain text") == []
    assert hygiene.accepted_hits("README.md", b"x", ["aws access key", HOME]) == ["aws access key", HOME]


def test_hygiene_real_table_and_contract_files():
    assert hygiene.HOME_PATH_ACCEPTED == {
        "docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/WORK_ORDER.md":
            "a147275224462d7cd3493cb2231b16468a1a0f0e5a64f215c00838a52d47abaf",
        "docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md":
            "1e9f312749807a370077d11ad9e7b64cb4e820a1335c2283af77a5a25996e4b2",
    }
    repo = Path(__file__).resolve().parents[1]
    for rel in hygiene.HOME_PATH_ACCEPTED:
        data = (repo / rel).read_bytes()  # read only
        found = hygiene.secret_hits(data.decode("utf-8", errors="ignore"))
        assert HOME in found
        assert hygiene.accepted_hits(rel, data, found) == []
