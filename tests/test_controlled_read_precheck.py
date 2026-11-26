"""AUTO-09-CONTROLLED-READ-PRECHECK: the precheck command (D1-D10).

Every input is a synthetic session in tmp_path; the real home, real session records and the repository
data/ are never opened. Each path test compares the whole precheck/1 document, so every D9 key is asserted."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from moneylab.controlled_read import DETAILS, ERROR_CODES, ControlledReadError, profiles, store, transcript
from moneylab.controlled_read import __main__ as cli
from moneylab.controlled_read import selector as grammar

PK = "C--synthetic-project"
SID = "0a1b2c3d-0000-4000-8000-00000000abcd"
UUID = "11111111-2222-4333-8444-555555555555"
UUID2 = "22222222-2222-4333-8444-555555555555"
TASK = "AUTO-09-SYNTH"
WO = "ECON-FWD-M20-WO/1"
PREREG = "ECON-FWD-M20-PREREG/1"
WB = "-----BEGIN ECON-FWD-M20 WORK ORDER CANDIDATE-----"
WE = "-----END ECON-FWD-M20 WORK ORDER CANDIDATE-----"
PB = "===== FINAL BODY BEGIN ====="
PE = "===== FINAL BODY END ====="
BODY_SENTINEL = "LEAKTOKEN-PRECHECK-BODY-5d21"
OTHER_SENTINEL = "LEAKTOKEN-PRECHECK-OTHER-9e07"
WO_TEXT = f"{WB}\n{BODY_SENTINEL}\n{WE}\n"
PRE_TEXT = f"{PB}\n{BODY_SENTINEL}\n{PE}\n"
BODY = (BODY_SENTINEL + "\n").encode("ascii")
VALUES = {"sha256": hashlib.sha256(BODY).hexdigest(), "bytes": len(BODY), "lf": 1}
NULL_MEASURED = {"prefix_bytes": None, "prefix_sha256": None, "line_count": None, "trailing_partial_bytes": None}
MISSING = object()


# ------------------------------------------------------------------------------------------ helpers


def line(obj: object) -> bytes:
    return json.dumps(obj).encode("utf-8") + b"\n"


def asst(uuid: str | None, *texts: str, extra: tuple[dict[str, Any], ...] = ()) -> bytes:
    entry: dict[str, Any] = {"type": "assistant",
                             "message": {"content": [{"type": "text", "text": t} for t in texts] + list(extra)}}
    if uuid is not None:
        entry["uuid"] = uuid
    return line(entry)


def tool(tool_use_id: object, content: object, *, is_error: object = MISSING, uuid: str | None = None) -> bytes:
    block: dict[str, Any] = {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}
    if is_error is not MISSING:
        block["is_error"] = is_error
    entry: dict[str, Any] = {"type": "user", "message": {"content": [block]}}
    if uuid is not None:
        entry["uuid"] = uuid
    return line(entry)


NOISE = line({"type": "user", "uuid": "33333333-2222-4333-8444-555555555555",
              "message": {"content": OTHER_SENTINEL}})


def make_repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    (path / ".gitignore").write_bytes(b"data/processed/*\n")
    return path


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return make_repo(tmp_path / "repo")


@pytest.fixture(autouse=True)
def no_record(monkeypatch):
    """D3: precheck never prepares an attempt or creates a record."""
    def forbidden(*_args, **_kwargs):
        raise AssertionError("precheck touched the record store")
    monkeypatch.setattr(store, "prepare_attempt", forbidden)
    monkeypatch.setattr(store, "create_record", forbidden)


def session_path(home: Path) -> Path:
    return home / ".claude" / "projects" / PK / f"{SID}.jsonl"


def make_home(tmp_path: Path, lines: list[bytes]) -> Path:
    home = tmp_path / "home"
    session_path(home).parent.mkdir(parents=True)
    session_path(home).write_bytes(b"".join(lines))
    return home


def measured(home: Path) -> dict[str, Any]:
    data = session_path(home).read_bytes()
    prefix = data[:data.rfind(b"\n") + 1]
    return {"prefix_bytes": len(prefix), "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
            "line_count": prefix.count(b"\n"), "trailing_partial_bytes": len(data) - len(prefix)}


def argv(profile: str = WO) -> list[str]:
    return ["precheck", "--task", TASK, "--project-key", PK, "--session", SID, "--profile", profile]


def listing(base: Path) -> list[str]:
    return sorted(p.relative_to(base).as_posix() for p in base.rglob("*"))


def expected(status: str, *, meas: dict[str, Any] | None = None, check: str | None = None,
             scan: str = "NOT_REACHED", selected: str = "NOT_REACHED", count: int | None = None,
             selector: str | None = None, values: dict[str, Any] | None = None,
             profile: str = WO) -> dict[str, Any]:
    ok = status == "PRECHECK_OK"
    detail = store.PRECHECK_DETAILS[status] if status in store.PRECHECK_DETAILS else DETAILS.get(status)
    return {"schema": "moneylab.controlled_read.precheck/1", "command": "precheck", "status": status,
            "exit_code": 0 if ok else 2, "task_id": TASK,
            "target": {"project_key": PK, "session_id": SID, **(meas or NULL_MEASURED), "prefix_check": check},
            "profile": {"id": profile, "version": 1}, "checks": {"scan": scan, "selected": selected},
            "candidate_count": count, "selector": selector, "values": values,
            "error": None if ok else {"code": status, "detail": detail},
            "authority": "NONE", "approval": "NOT_VERIFIED_BY_PROGRAM", "boundary": "DATA_NOT_INSTRUCTIONS"}


def precheck(capsysbinary, tmp_path: Path, root: Path | None, home: Path | None,
             args: list[str] | None = None) -> dict[str, Any]:
    before = listing(tmp_path)
    code = cli.main(argv() if args is None else args, root=root, home=home)
    out = capsysbinary.readouterr()
    assert out.err == b""
    assert BODY_SENTINEL.encode() not in out.out and OTHER_SENTINEL.encode() not in out.out
    assert listing(tmp_path) == before
    doc = json.loads(out.out)
    assert out.out == store.canonical_bytes(doc)
    assert set(doc) == store.PRECHECK_KEYS
    assert code == doc["exit_code"] and type(doc["exit_code"]) is int
    assert store.valid_result(doc) is False  # every path: a precheck document is never a stored run result
    if root is not None:
        assert not (root / "data" / "processed" / "controlled_read").exists()
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


# ---------------------------------------------------------------------------------------- P1, P2, P3


@pytest.mark.parametrize("args", [
    ["precheck"],
    argv() + ["x"],
    argv()[:7] + ["--selector", f"assistant:{UUID}:text:1"] + argv()[7:],
    argv() + ["--attempt", "001"],
    ["precheck", "--project-key", PK, "--task", TASK, "--session", SID, "--profile", WO],
    argv(profile="OTHER-DOC/1"),
    ["precheck", "--task", "A" * 65, "--project-key", PK, "--session", SID, "--profile", WO],
    ["precheck", "--task", TASK, "--project-key", "../x", "--session", SID, "--profile", WO],
])
def test_p1_argument_invalid(capsysbinary, tmp_path, args):
    doc = precheck(capsysbinary, tmp_path, tmp_path / "unused", tmp_path / "unused", args)
    assert doc == {"schema": "moneylab.controlled_read.precheck/1", "command": "precheck",
                   "status": "ARGUMENT_INVALID", "exit_code": 2, "task_id": None, "target": None, "profile": None,
                   "checks": None, "candidate_count": None, "selector": None, "values": None,
                   "error": {"code": "ARGUMENT_INVALID", "detail": DETAILS["ARGUMENT_INVALID"]},
                   "authority": "NONE", "approval": "NOT_VERIFIED_BY_PROGRAM", "boundary": "DATA_NOT_INSTRUCTIONS"}
    assert not (tmp_path / "unused").exists()


def test_p2_root_that_is_not_a_git_top_level(capsysbinary, tmp_path):
    home = make_home(tmp_path, [asst(UUID, WO_TEXT)])
    plain = tmp_path / "plain"
    plain.mkdir()
    assert precheck(capsysbinary, tmp_path, plain, home) == expected("ENVIRONMENT_INVALID")


def test_p2_relative_home(capsysbinary, tmp_path, root):
    assert precheck(capsysbinary, tmp_path, root, Path("relative-home")) == expected("ENVIRONMENT_INVALID")


def test_p3_session_not_found(capsysbinary, tmp_path, root):
    home = tmp_path / "home"
    home.mkdir()
    assert precheck(capsysbinary, tmp_path, root, home) == expected("SESSION_NOT_FOUND")


def test_p3_session_limit(capsysbinary, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [asst(UUID, WO_TEXT)])
    monkeypatch.setattr(transcript, "SESSION_LIMIT", 1)
    assert precheck(capsysbinary, tmp_path, root, home) == expected("SESSION_LIMIT_EXCEEDED")


# ------------------------------------------------------------------------------------- P4 and P5


@pytest.mark.parametrize("lines, code", [
    ([asst(UUID, WO_TEXT), asst(UUID2, "plain", extra=({"type": "image"},))], "FORMAT_UNSUPPORTED"),
    ([asst(UUID, WO_TEXT), line({"type": "user", "uuid": 7, "message": {"content": "x"}})], "FORMAT_UNSUPPORTED"),
    ([asst(UUID, WO_TEXT), tool(5, "plain")], "FORMAT_UNSUPPORTED"),
    ([asst(UUID, WO_TEXT), tool("toolu_02", "plain", is_error="yes")], "FORMAT_UNSUPPORTED"),
    ([asst(UUID, WO_TEXT), tool("toolu_02", [{"type": "image"}])], "FORMAT_UNSUPPORTED"),
    ([asst(UUID, WO_TEXT), b"not json\n"], "SESSION_CORRUPT"),
])
def test_p4_scan_failure_after_the_whole_prefix(capsysbinary, tmp_path, root, rehash_calls, lines, code):
    home = make_home(tmp_path, [NOISE, *lines])
    meas = measured(home)
    assert precheck(capsysbinary, tmp_path, root, home) == expected(code, meas=meas, check="MATCHED", scan="FAILED")
    assert len(rehash_calls) == 1


def test_p4_line_limit(capsysbinary, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [NOISE, asst(UUID, WO_TEXT)])
    meas = measured(home)
    monkeypatch.setattr(transcript, "LINE_LIMIT", 20)
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        "LINE_LIMIT_EXCEEDED", meas=meas, check="MATCHED", scan="FAILED")


def test_p4_entry_limit(capsysbinary, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [NOISE, asst(UUID, WO_TEXT)])
    meas = measured(home)
    monkeypatch.setattr(transcript, "ENTRY_LIMIT", 1)
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        "ENTRY_LIMIT_EXCEEDED", meas=meas, check="MATCHED", scan="FAILED")


def test_p5_time_out_while_scanning_skips_the_rehash(capsysbinary, tmp_path, root, monkeypatch, clock,
                                                     rehash_calls):
    home = make_home(tmp_path, [NOISE, NOISE, asst(UUID, WO_TEXT)])
    meas = measured(home)
    real = transcript.parse_line

    def parse_then_expire(raw: bytes) -> dict[str, Any]:
        clock.now = 1000.0
        return real(raw)
    monkeypatch.setattr(transcript, "parse_line", parse_then_expire)
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        "TIME_LIMIT_EXCEEDED", meas=meas, check="INCOMPLETE", scan="FAILED")
    assert rehash_calls == []


# -------------------------------------------------------------------------------- P6, P7 and P8


@pytest.mark.parametrize("lines, profile", [
    ([NOISE, asst(UUID, "no marker here", "  " + WB)], WO),
    ([NOISE, tool("toolu_02", "failed without a marker", is_error=True)], WO),
    ([NOISE, asst(UUID, WO_TEXT)], PREREG),  # PREREG reads tool_result blocks only
    ([NOISE, tool("toolu_02", WO_TEXT)], PREREG),  # another profile's markers
])
def test_p6_no_candidate(capsysbinary, tmp_path, root, lines, profile):
    home = make_home(tmp_path, lines)
    meas = measured(home)
    assert precheck(capsysbinary, tmp_path, root, home, argv(profile)) == expected(
        "PRECHECK_NO_CANDIDATE", meas=meas, check="MATCHED", scan="PASSED", count=0, profile=profile)


@pytest.mark.parametrize("lines, count", [
    ([asst(UUID, WO_TEXT, WO_TEXT)], 2),  # two text blocks of one entry
    ([asst(UUID, WO_TEXT), tool("toolu_01", WO_TEXT)], 2),  # assistant and tool_result
    ([asst(UUID, f"{WB}\nhalf\n"), asst(UUID2, WO_TEXT)], 2),  # BEGIN only and a complete block
    ([asst(UUID, f"half\n{WE}"), tool("toolu_01", [{"type": "text", "text": WO_TEXT}])], 2),  # END only
    ([tool("toolu_01", WO_TEXT, is_error=True), asst(UUID, WO_TEXT)], 2),  # an error result counts
    ([asst(UUID, WO_TEXT), NOISE, NOISE, NOISE, tool("toolu_09", WO_TEXT)], 2),  # second one on the last line
    ([asst(UUID, WO_TEXT, "x", WO_TEXT), tool("toolu_01", [{"type": "text", "text": WO_TEXT}] * 2)], 4),
])
def test_p7_multiple_candidates(capsysbinary, tmp_path, root, lines, count):
    home = make_home(tmp_path, [NOISE, *lines])
    meas = measured(home)
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        "PRECHECK_MULTIPLE_CANDIDATES", meas=meas, check="MATCHED", scan="PASSED", count=count)


def test_p7_crlf_marker_lines_count(capsysbinary, tmp_path, root):
    home = make_home(tmp_path, [asst(UUID, WO_TEXT.replace("\n", "\r\n")), asst(UUID2, WO_TEXT)])
    meas = measured(home)
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        "PRECHECK_MULTIPLE_CANDIDATES", meas=meas, check="MATCHED", scan="PASSED", count=2)


@pytest.mark.parametrize("lines", [
    [asst(None, WO_TEXT)],  # no uuid
    [tool("toolu-bad", WO_TEXT)],  # tool_use_id outside the selector grammar
    [asst(UUID, *(["plain"] * 99 + [WO_TEXT]))],  # k = 100
    [asst("NOT-A-UUID", WO_TEXT)],
])
def test_p8_selector_unrepresentable(capsysbinary, tmp_path, root, lines):
    home = make_home(tmp_path, [NOISE, *lines])
    meas = measured(home)
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        "PRECHECK_SELECTOR_UNREPRESENTABLE", meas=meas, check="MATCHED", scan="PASSED", count=1)


# ------------------------------------------------------------------------------------- P9 and P10


@pytest.mark.parametrize("lines, code", [
    ([tool("toolu_01", WO_TEXT, is_error=True)], "TOOL_RESULT_ERROR"),
    ([asst(UUID, WO_TEXT), line({"type": "user", "uuid": UUID, "message": {"content": "x"}})], "ENTRY_DUPLICATE"),
    ([asst(UUID, f"{WB}\nhalf\n")], "MARKER_MISSING"),
    ([asst(UUID, f"{WE}\nx\n{WB}\n")], "MARKER_ORDER_INVALID"),
    ([asst(UUID, f"{WB}\n\n{WE}\n")], "BODY_EMPTY"),
    ([asst(UUID, f"{WB}\nx\n{WB}\n{WE}\n")], "MARKER_DUPLICATE"),
])
def test_p9_selected_path_failure(capsysbinary, tmp_path, root, rehash_calls, lines, code):
    home = make_home(tmp_path, [NOISE, *lines])
    meas = measured(home)
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        code, meas=meas, check="MATCHED", scan="PASSED", selected="FAILED", count=1)
    assert len(rehash_calls) == 1


def test_p10_time_out_on_the_selected_path_skips_the_rehash(capsysbinary, tmp_path, root, monkeypatch, clock,
                                                            rehash_calls):
    home = make_home(tmp_path, [NOISE, asst(UUID, WO_TEXT)])
    meas = measured(home)
    real = grammar.parse_selector

    def parse_then_expire(value: str) -> grammar.Selector:
        clock.now = 1000.0
        return real(value)
    monkeypatch.setattr(grammar, "parse_selector", parse_then_expire)
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        "TIME_LIMIT_EXCEEDED", meas=meas, check="INCOMPLETE", scan="PASSED", selected="FAILED", count=1)
    assert rehash_calls == []


# ------------------------------------------------------------------------------------------------ P11


@pytest.mark.parametrize("lines, profile, selector", [
    ([NOISE, asst(UUID, "plain", WO_TEXT)], WO, f"assistant:{UUID}:text:2"),
    ([NOISE, tool("toolu_01AbC", WO_TEXT)], WO, "tool_result:toolu_01AbC:text:1"),
    ([NOISE, asst(UUID, PRE_TEXT), tool("toolu_7", [{"type": "text", "text": "x"}, {"type": "text", "text": PRE_TEXT}],
                                       is_error=False)], PREREG, "tool_result:toolu_7:text:2"),
    ([NOISE, tool("toolu_02", "failed", is_error=True), asst(UUID, WO_TEXT)], WO, f"assistant:{UUID}:text:1"),
])
def test_p11_one_candidate_passes(capsysbinary, tmp_path, root, monkeypatch, rehash_calls, lines, profile,
                                  selector):
    children: list[list[str]] = []
    real_popen = subprocess.Popen

    def track(args, *a, **k):
        children.append([str(x) for x in args])
        return real_popen(args, *a, **k)
    monkeypatch.setattr(subprocess, "Popen", track)
    home = make_home(tmp_path, lines)
    meas = measured(home)
    doc = precheck(capsysbinary, tmp_path, root, home, argv(profile))
    assert doc == expected("PRECHECK_OK", meas=meas, check="MATCHED", scan="PASSED", selected="PASSED", count=1,
                           selector=selector, values=VALUES, profile=profile)
    assert len(rehash_calls) == 1
    assert len(children) == 1 and "rev-parse" in children[0] and "check-ignore" not in children[0]  # D3


def test_p11_selector_runs_with_the_same_values(capsysbinary, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [NOISE, asst(UUID2, "plain"), asst(UUID, WO_TEXT)])
    doc = precheck(capsysbinary, tmp_path, root, home)
    assert doc["status"] == "PRECHECK_OK"
    monkeypatch.undo()  # run writes its record
    code = cli.main(["run", "--task", TASK, "--project-key", PK, "--session", SID, "--selector", doc["selector"],
                     "--profile", WO, "--attempt", "001"], root=root, home=home)
    result = json.loads(capsysbinary.readouterr().out)
    assert (code, result["status"], result["values"]) == (0, "SUCCEEDED", doc["values"])


def test_undefined_exception_propagates_without_output(capsysbinary, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [asst(UUID, WO_TEXT)])

    def boom(*_args):
        raise RuntimeError("bug")
    monkeypatch.setattr(profiles, "extract", boom)
    with pytest.raises(RuntimeError):
        cli.main(argv(), root=root, home=home)
    assert capsysbinary.readouterr() == (b"", b"")


# ---------------------------------------------------------------------------------------- R re-hash


def _truncate(home: Path):
    def change(_handle):
        os.truncate(session_path(home), 5)
    return change


def _overwrite(home: Path):
    def change(_handle):
        with open(session_path(home), "r+b") as f:
            f.write(b"[")
    return change


@pytest.mark.parametrize("kind, code, check", [
    ("truncate", "SESSION_TRUNCATED", "TRUNCATED"),
    ("overwrite", "SESSION_CHANGED", "CHANGED"),
    ("unreadable", "SESSION_UNREADABLE", "INCOMPLETE"),
    ("expired_before", "TIME_LIMIT_EXCEEDED", "INCOMPLETE"),
    ("expired_after", "TIME_LIMIT_EXCEEDED", "MATCHED"),
])
def test_r_rehash_replaces_a_pass(capsysbinary, tmp_path, root, monkeypatch, clock, kind, code, check):
    home = make_home(tmp_path, [NOISE, asst(UUID, WO_TEXT)])
    meas = measured(home)

    def fail(*_args):
        raise OSError("gone")

    def expire_after_read(_handle):
        clock.queue = [0.0]
        clock.now = 1000.0
    hooks = {"truncate": _truncate(home), "overwrite": _overwrite(home),
             "unreadable": lambda _h: monkeypatch.setattr(transcript, "_fstat", fail),
             "expired_after": expire_after_read}
    if kind == "expired_before":
        real = profiles.values

        def values_then_expire(body: bytes) -> dict[str, object]:
            clock.now = 1000.0
            return real(body)
        monkeypatch.setattr(profiles, "values", values_then_expire)
    else:
        monkeypatch.setattr(transcript, "_before_rehash", hooks[kind])
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        code, meas=meas, check=check, scan="PASSED", selected="PASSED")


def test_r_rehash_replaces_a_scan_failure_and_no_candidate(capsysbinary, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [NOISE, b"not json\n"])
    meas = measured(home)
    monkeypatch.setattr(transcript, "_before_rehash", _overwrite(home))
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        "SESSION_CHANGED", meas=meas, check="CHANGED", scan="FAILED")
    other = tmp_path / "second"
    other.mkdir()
    home2 = make_home(other, [NOISE])
    meas2 = measured(home2)
    monkeypatch.setattr(transcript, "_before_rehash", _truncate(home2))
    assert precheck(capsysbinary, tmp_path, root, home2) == expected(
        "SESSION_TRUNCATED", meas=meas2, check="TRUNCATED", scan="PASSED")


def test_r_rehash_replaces_a_selected_failure_and_multiple(capsysbinary, tmp_path, root, monkeypatch):
    home = make_home(tmp_path, [NOISE, tool("toolu_01", WO_TEXT, is_error=True)])
    meas = measured(home)
    monkeypatch.setattr(transcript, "_before_rehash", _overwrite(home))
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        "SESSION_CHANGED", meas=meas, check="CHANGED", scan="PASSED", selected="FAILED")
    session_path(home).write_bytes(NOISE + asst(UUID, WO_TEXT, WO_TEXT))
    meas = measured(home)
    assert precheck(capsysbinary, tmp_path, root, home) == expected(
        "SESSION_CHANGED", meas=meas, check="CHANGED", scan="PASSED")


# ------------------------------------------------------------------------------------- separation


def test_precheck_codes_are_separate_from_the_run_codes():
    assert set(store.PRECHECK_DETAILS) == {"PRECHECK_NO_CANDIDATE", "PRECHECK_MULTIPLE_CANDIDATES",
                                           "PRECHECK_SELECTOR_UNREPRESENTABLE"}
    assert set(store.PRECHECK_DETAILS).isdisjoint(DETAILS) and store.PRECHECK_OK not in DETAILS
    for code in [*store.PRECHECK_DETAILS, store.PRECHECK_OK]:
        with pytest.raises(ValueError):
            ControlledReadError(code)
    assert ERROR_CODES == tuple(DETAILS)
    assert store.PRECHECK_SCHEMA == "moneylab.controlled_read.precheck/1"


@pytest.mark.parametrize("status", ["STORE_PATH_INVALID", "STORE_FAILED", "ATTEMPT_EXISTS", "SUCCEEDED", "OTHER"])
def test_precheck_document_refuses_codes_it_never_produces(status):
    with pytest.raises(ValueError):
        store.precheck_document(status)


def test_precheck_document_refuses_a_pass_without_its_values():
    tgt = {"prefix_check": "MATCHED"}
    with pytest.raises(ValueError):
        store.precheck_document("PRECHECK_OK", target=tgt, candidate_count=1, selector="x")
    with pytest.raises(ValueError):
        store.precheck_document("PRECHECK_OK", target={"prefix_check": "CHANGED"}, candidate_count=1, selector="x",
                                values=VALUES)
    with pytest.raises(ValueError):
        store.precheck_document("PRECHECK_NO_CANDIDATE", selector="x")


# ------------------------------------------------------------------------------------------ units


@pytest.mark.parametrize("kind, ident, k, out", [
    ("assistant", UUID, 1, f"assistant:{UUID}:text:1"),
    ("tool_result", "toolu_01", 99, "tool_result:toolu_01:text:99"),
    ("assistant", UUID, 100, None),
    ("assistant", None, 1, None),
    ("assistant", 7, 1, None),
    ("assistant", "aaaaaaaa-2222-4333-8444-55555555beef".upper(), 1, None),
    ("tool_result", "toolu-01", 1, None),
    ("tool_result", "toolu_01:text:1", 1, None),
    ("other", "toolu_01", 1, None),
])
def test_format_selector(kind, ident, k, out):
    assert grammar.format_selector(kind, ident, k) == out
    if out is not None:
        assert grammar.parse_selector(out) == grammar.Selector(kind, ident, k)


@pytest.mark.parametrize("text, present", [
    (WO_TEXT, True), (WB, True), ("x\n" + WE, True), (WB + "\r\nx", True),
    (" " + WB, False), (WB + " ", False), (WB.lower(), False), (PB, False), ("", False), (WB + "\rx", False),
])
def test_marker_line_present(text, present):
    assert profiles.marker_line_present(profiles.WORK_ORDER, text) is present


def test_parse_precheck():
    assert grammar.parse_precheck(argv()) == grammar.PrecheckArgs(TASK, PK, SID, WO)
    assert grammar.PRECHECK_OPTIONS == ("--task", "--project-key", "--session", "--profile")
    for bad in (argv()[:-1], ["run", *argv()[1:]], argv() + ["--x"]):
        with pytest.raises(ControlledReadError) as err:
            grammar.parse_precheck(bad)
        assert err.value.code == "ARGUMENT_INVALID"


def test_candidates_hold_no_text(tmp_path):
    home = make_home(tmp_path, [NOISE, asst(UUID, WO_TEXT), tool("toolu_01", WO_TEXT, is_error=True)])
    found = transcript.scan_candidates(measured_prefix(home), profiles.WORK_ORDER.kinds,
                                       lambda t: profiles.marker_line_present(profiles.WORK_ORDER, t),
                                       transcript.Deadline())
    assert found == [transcript.Candidate("assistant", UUID, 1, False),
                     transcript.Candidate("tool_result", "toolu_01", 1, True)]
    assert BODY_SENTINEL not in repr(found)


def measured_prefix(home: Path) -> bytes:
    data = session_path(home).read_bytes()
    return data[:data.rfind(b"\n") + 1]


# -------------------------------------------------------------------------- D5 split equivalence


def _old_tool_result_texts(block: dict[str, Any]) -> list[str]:
    """_tool_result_texts as it was at d471d64, before the content part was split out."""
    if "is_error" in block:
        if not isinstance(block["is_error"], bool):
            raise ControlledReadError("FORMAT_UNSUPPORTED")
        if block["is_error"]:
            raise ControlledReadError("TOOL_RESULT_ERROR")
    content = block.get("content")
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        raise ControlledReadError("FORMAT_UNSUPPORTED")
    texts: list[str] = []
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "text" or not isinstance(item.get("text"), str):
            raise ControlledReadError("FORMAT_UNSUPPORTED")
        texts.append(item["text"])
    return texts


def _outcome(fn, block):
    try:
        return ("ok", fn(block))
    except ControlledReadError as exc:
        return ("error", exc.code)


@pytest.mark.parametrize("is_error", [MISSING, True, False, "yes", 1, None])
@pytest.mark.parametrize("content", [
    MISSING, "plain", "", [], [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}],
    [{"type": "image"}], [{"type": "text", "text": 5}], ["x"], 7, None, {"type": "text", "text": "a"},
])
def test_tool_result_texts_split_keeps_its_behaviour(is_error, content):
    block: dict[str, Any] = {"type": "tool_result", "tool_use_id": "toolu_01"}
    if is_error is not MISSING:
        block["is_error"] = is_error
    if content is not MISSING:
        block["content"] = content
    assert _outcome(transcript._tool_result_texts, block) == _outcome(_old_tool_result_texts, block)
