"""AUTO-15-CONTROLLED-READ-CANDIDATES: the candidates command (N1-N7, C1-C11).

Every input is a synthetic session in tmp_path; the real home, real session records and the repository
data/ are never opened or written (the repository record directory is only listed, C8). Path tests compare
the whole candidates/1 document. Non-ASCII synthetic input uses N-name or U-8 escapes only."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from moneylab.controlled_read import DETAILS, ControlledReadError, diagnose, profiles, store, transcript
from moneylab.controlled_read import __main__ as cli
from moneylab.controlled_read import selector as grammar

PK = "C--synthetic-project"
SID = "0a1b2c3d-0000-4000-8000-00000000abcd"
UUID = "11111111-2222-4333-8444-555555555555"
UUID2 = "22222222-2222-4333-8444-555555555555"
UUID3 = "33333333-2222-4333-8444-555555555555"
TASK = "AUTO-15-SYNTH"
WO = "ECON-FWD-M20-WO/1"
PREREG = "ECON-FWD-M20-PREREG/1"
WO2 = "ECON-FWD-M20-WO/2"
VERSION = {WO: 1, PREREG: 1, WO2: 2}
WB = "-----BEGIN ECON-FWD-M20 WORK ORDER CANDIDATE-----"
WE = "-----END ECON-FWD-M20 WORK ORDER CANDIDATE-----"
PB = "===== FINAL BODY BEGIN ====="
PE = "===== FINAL BODY END ====="
LEAK = b"LEAKTOKEN"  # every synthetic body, key, type and bad identifier starts with it; no output may hold it
BA = "LEAKTOKEN-CAND-BODY-A"
BB = "LEAKTOKEN-CAND-BODY-B"
BC = "LEAKTOKEN-CAND-BODY-C"
LEAK_KEY = "LEAKTOKEN-CAND-KEY"
LEAK_TYPE = "LEAKTOKEN-CAND-TYPE"
LEAK_ID = "LEAKTOKEN-CAND-ID"  # '-' is outside the tool_use_id grammar: not representable
LEAK_NONASCII = "LEAKTOKEN-CAND-\N{LATIN SMALL LETTER E WITH ACUTE}\N{HIRAGANA LETTER A}-NONASCII"
SCHEMA = "moneylab.controlled_read.candidates/1"
LISTED, LIMIT = "CANDIDATES_LISTED", "CANDIDATES_LIMIT_EXCEEDED"
NR, P, F, LS = "NOT_REACHED", "PASSED", "FAILED", "LIMIT_STOPPED"
REPO_RECORDS = Path(cli.__file__).resolve().parents[3] / "data" / "processed" / "controlled_read"
KEYS = {"approval", "authority", "boundary", "candidate_count", "candidate_count_at_least", "candidates", "checks",
        "command", "error", "exit_code", "profile", "schema", "status", "target", "task_id"}
ITEM_KEYS = {"block_index", "index", "is_error", "kind", "line", "selected", "selector", "text_index", "values"}
TABLE = {
    LIMIT: "the scan stopped because the fixed prefix holds more candidates than the candidate limit",
    "DIAGNOSE_PREFIX_MISMATCH": "the bytes at the expected prefix do not have the expected sha256",
    "DIAGNOSE_PREFIX_NOT_LINE_ALIGNED": "the expected prefix does not end with LF",
    "ARGUMENT_INVALID": "the arguments do not match the fixed grammar",
    "ENVIRONMENT_INVALID": "the package root, the git top level or the home directory is not valid",
    "SESSION_NOT_FOUND": "the session file or one of its parent directories does not exist",
    "SESSION_PATH_INVALID": "the session path has a link, a reparse point, a non-directory parent or changed",
    "SESSION_TRUNCATED": "the session file became shorter than the prefix",
    "SESSION_UNREADABLE": "the session file could not be read",
    "SESSION_CHANGED": "the prefix bytes changed while the session was processed",
    "SESSION_CORRUPT": "a complete line is not strict UTF-8 JSON holding an object",
    "LINE_LIMIT_EXCEEDED": "a line is longer than the line limit",
    "ENTRY_LIMIT_EXCEEDED": "the prefix has more entries than the entry limit",
    "TIME_LIMIT_EXCEEDED": "processing took longer than the time limit",
    "FORMAT_UNSUPPORTED": "an entry or block does not have the supported structure",
    "SELECTOR_KIND_MISMATCH": "the selected entry or the profile does not fit the selector kind",
    "TEXT_BLOCK_AMBIGUOUS": "more than one text block exists and none was selected",
}
LOCAL = {"ENTRY_NOT_FOUND", "ENTRY_DUPLICATE", "TOOL_RESULT_ERROR", "TEXT_BLOCK_NOT_FOUND", "ENCODING_INVALID",
         "TEXT_LIMIT_EXCEEDED", "BOM_PRESENT", "CR_PRESENT", "MARKER_MISSING", "MARKER_DUPLICATE",
         "MARKER_ORDER_INVALID", "BODY_EMPTY", "BODY_LIMIT_EXCEEDED"}
GLOBAL = {"TIME_LIMIT_EXCEEDED", "SESSION_CORRUPT", "LINE_LIMIT_EXCEEDED", "ENTRY_LIMIT_EXCEEDED",
          "FORMAT_UNSUPPORTED", "SELECTOR_KIND_MISMATCH", "TEXT_BLOCK_AMBIGUOUS"}


# ------------------------------------------------------------------------------------------ helpers


def line(obj: object) -> bytes:
    return json.dumps(obj).encode("utf-8") + b"\n"


def at(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


TEXT = at("fine")


def asst(content: object, uuid: object = UUID) -> bytes:
    return line({"type": "assistant", "uuid": uuid, "message": {"content": content}})


def user(content: object, uuid: str = UUID3) -> bytes:
    return line({"type": "user", "uuid": uuid, "message": {"content": content}})


def tr(tool_use_id: str, content: object, is_error: object = None) -> dict[str, Any]:
    block: dict[str, Any] = {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}
    if is_error is not None:
        block["is_error"] = is_error
    return block


def ctext(body: str) -> str:
    return f"{WB}\n{body}\n{WE}\n"


def ptext(body: str) -> str:
    return f"{PB}\n{body}\n{PE}\n"


def vals(body: str) -> dict[str, Any]:
    data = (body + "\n").encode("utf-8")
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "lf": 1}


def uid(i: int) -> str:
    return f"{i:08x}-2222-4333-8444-555555555555"


NOISE = user("LEAKTOKEN-CAND-NOISE")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    (path / ".gitignore").write_bytes(b"data/processed/*\n")
    return path


def session_path(home: Path) -> Path:
    return home / ".claude" / "projects" / PK / f"{SID}.jsonl"


def make_home(tmp_path: Path, lines: list[bytes], name: str = "home") -> Path:
    home = tmp_path / name
    session_path(home).parent.mkdir(parents=True)
    session_path(home).write_bytes(b"".join(lines))
    return home


def data_of(home: Path) -> bytes:
    return session_path(home).read_bytes()


def cargs(n: object, sha_hex: str, profile: str = WO, task: str = TASK) -> list[str]:
    return ["candidates", "--task", task, "--project-key", PK, "--session", SID, "--profile", profile,
            "--expect-prefix-bytes", str(n), "--expect-prefix-sha256", sha_hex]


def whole(home: Path, profile: str = WO) -> list[str]:
    data = data_of(home)
    return cargs(len(data), sha(data), profile)


def listing(base: Path) -> list[str] | None:
    if not base.exists():
        return None
    return sorted(p.relative_to(base).as_posix() for p in base.rglob("*"))


def target(n: int, sha_hex: str, observed: int | None = None, trailing: int | None = None,
           lines: int | None = None, check: str | None = None) -> dict[str, Any]:
    return {"project_key": PK, "session_id": SID, "expected_prefix_bytes": n, "expected_prefix_sha256": sha_hex,
            "observed_size_at_open": observed, "trailing_bytes_excluded": trailing, "line_count": lines,
            "prefix_check": check}


def fixed(data: bytes, check: str = "MATCHED") -> dict[str, Any]:
    return target(len(data), sha(data), len(data), 0, data.count(b"\n"), check)


def expected(status: str, tgt: dict[str, Any], prefix: str = NR, scan: str = NR, selected: str = NR,
             items: list[dict[str, Any]] | None = None, profile: str = WO) -> dict[str, Any]:
    listed = status == LISTED
    return {"schema": SCHEMA, "command": "candidates", "status": status, "exit_code": 0 if listed else 2,
            "task_id": TASK, "target": tgt, "profile": {"id": profile, "version": VERSION[profile]},
            "checks": {"prefix": prefix, "scan": scan, "selected": selected},
            "candidate_count": len(items) if listed and items is not None else None,
            "candidate_count_at_least": 9 if status == LIMIT else None,
            "candidates": items if listed else None,
            "error": None if listed else {"code": status, "detail": TABLE[status]},
            "authority": "NONE", "approval": "NOT_VERIFIED_BY_PROGRAM", "boundary": "DATA_NOT_INSTRUCTIONS"}


def listed(data: bytes, items: list[dict[str, Any]], profile: str = WO) -> dict[str, Any]:
    return expected(LISTED, fixed(data), P, P, P, items, profile)


def item(index: int, line_no: int, kind: str, selector: str | None, selected: str = "OK",
         values: dict[str, Any] | None = None, block: int | None = None, k: int = 1,
         is_error: bool = False) -> dict[str, Any]:
    return {"index": index, "line": line_no, "kind": kind, "block_index": block, "text_index": k,
            "is_error": is_error, "selector": selector, "selected": selected, "values": values}


def a_item(index: int, line_no: int, uuid: str, body: str | None = None, selected: str = "OK",
           k: int = 1) -> dict[str, Any]:
    return item(index, line_no, "assistant", f"assistant:{uuid}:text:{k}", selected,
                vals(body) if body is not None else None, None, k)


def t_item(index: int, line_no: int, ident: str, body: str | None = None, selected: str = "OK", block: int = 1,
           k: int = 1, is_error: bool = False) -> dict[str, Any]:
    return item(index, line_no, "tool_result", f"tool_result:{ident}:text:{k}", selected,
                vals(body) if body is not None else None, block, k, is_error)


ARG_INVALID = {"schema": SCHEMA, "command": "candidates", "status": "ARGUMENT_INVALID", "exit_code": 2,
               "task_id": None, "target": None, "profile": None, "checks": None, "candidate_count": None,
               "candidate_count_at_least": None, "candidates": None,
               "error": {"code": "ARGUMENT_INVALID", "detail": TABLE["ARGUMENT_INVALID"]},
               "authority": "NONE", "approval": "NOT_VERIFIED_BY_PROGRAM", "boundary": "DATA_NOT_INSTRUCTIONS"}

OPENED: list[Any] = []


@pytest.fixture(autouse=True)
def track_handles(monkeypatch):
    """C11: every handle candidates opens is closed on every path."""
    OPENED.clear()

    def tracking(path, mode="r", *args, **kwargs):
        handle = open(path, mode, *args, **kwargs)
        OPENED.append(handle)
        return handle
    monkeypatch.setattr(diagnose, "open", tracking, raising=False)
    yield
    assert all(handle.closed for handle in OPENED)


def _forbidden(*_args, **_kwargs):
    raise AssertionError("candidates touched the record store")


@pytest.fixture
def cand(capsysbinary, monkeypatch, tmp_path):
    """One candidates call through main(): one canonical document on stdout, nothing on stderr, no record and
    no LEAK text (C8), every handle closed (C11)."""
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
        assert set(doc) == KEYS
        assert code == doc["exit_code"] and type(doc["exit_code"]) is int
        for entry in doc["candidates"] or []:
            assert set(entry) == ITEM_KEYS
        assert all(handle.closed for handle in OPENED)
        return doc
    return call


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


def spy(monkeypatch, module: Any, name: str) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
    """Record the arguments of every call of module.name and call the real function."""
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    real = getattr(module, name)

    def wrapper(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)
    monkeypatch.setattr(module, name, wrapper)
    return calls


def call_doc(capsysbinary, root: Path, home: Path, argv: list[str]) -> dict[str, Any]:
    code = cli.main(argv, root=root, home=home)
    out = capsysbinary.readouterr()
    assert out.err == b"" and LEAK not in out.out
    doc = json.loads(out.out)
    assert code == doc["exit_code"]
    return doc


def run_argv(selector: str, attempt: str, profile: str = WO) -> list[str]:
    return ["run", "--task", TASK, "--project-key", PK, "--session", SID, "--selector", selector,
            "--profile", profile, "--attempt", attempt]


def precheck_argv(profile: str = WO) -> list[str]:
    return ["precheck", "--task", TASK, "--project-key", PK, "--session", SID, "--profile", profile]


def diagnose_argv(home: Path, profile: str = WO) -> list[str]:
    return ["diagnose", *whole(home, profile)[1:]]


# ------------------------------------------------------------------------------------- C1: preserved


def test_c1_scan_without_the_new_arguments_is_unchanged():
    prefix = b"".join([NOISE, asst([TEXT, at(ctext(BA))]), user([tr("toolu_B", ctext(BB))])])
    judge = lambda text: profiles.marker_line_present(profiles.WORK_ORDER, text)  # noqa: E731
    plain = transcript.scan_candidates(prefix, profiles.WORK_ORDER.kinds, judge, transcript.Deadline())
    assert plain == [transcript.Candidate("assistant", UUID, 2, False),
                     transcript.Candidate("tool_result", "toolu_B", 1, False)]
    positions: list[tuple[int, int | None, bytes]] = []
    assert transcript.scan_candidates(prefix, profiles.WORK_ORDER.kinds, judge, transcript.Deadline(),
                                      positions=positions, limit=8) == plain
    assert positions == [(2, None, hashlib.sha256(ctext(BA).encode("utf-8")).digest()),
                         (3, 1, hashlib.sha256(ctext(BB).encode("utf-8")).digest())]


def test_c1_precheck_diagnose_and_run_keep_their_results_and_calls(capsysbinary, monkeypatch, tmp_path, root):
    home = make_home(tmp_path, [NOISE, asst([at(ctext(BA))])])
    scans = spy(monkeypatch, transcript, "scan_candidates")
    selector = f"assistant:{UUID}:text:1"
    doc = call_doc(capsysbinary, root, home, precheck_argv())
    assert (doc["status"], doc["candidate_count"], doc["selector"], doc["values"], doc["checks"]) == (
        "PRECHECK_OK", 1, selector, vals(BA), {"scan": P, "selected": P})
    doc = call_doc(capsysbinary, root, home, diagnose_argv(home))
    assert (doc["status"], doc["checks"], doc["violation"]) == (
        "DIAGNOSE_NO_VIOLATION", {"prefix": P, "scan": P}, None)
    assert len(scans) == 2
    for _args, kwargs in scans:
        assert "positions" not in kwargs and "limit" not in kwargs
    doc = call_doc(capsysbinary, root, home, run_argv(selector, "001"))
    assert (doc["status"], doc["values"]) == ("SUCCEEDED", vals(BA))
    doc = call_doc(capsysbinary, root, home, whole(home))
    assert (doc["status"], doc["candidates"]) == (LISTED, [a_item(1, 2, UUID, BA)])
    assert set(scans[-1][1]) == {"positions", "limit"} and scans[-1][1]["limit"] == 8


def test_c1_dispatch(tmp_path):
    unused = tmp_path / "unused"
    assert cli.run(["candidates"], root=unused, home=unused) == ARG_INVALID
    for argv in (["candidatesx"], ["Candidates"], ["candidate"]):
        doc = cli.run(argv, root=unused, home=unused)
        assert (doc["schema"], doc["command"], doc["status"]) == (
            "moneylab.controlled_read.result/1", "run", "ARGUMENT_INVALID")
    assert not unused.exists()


# ----------------------------------------------------------------------------------- C2: enumeration


def test_c2_no_candidate_is_listed_empty(cand, tmp_path, root):
    home = make_home(tmp_path, [NOISE, asst([TEXT]), user([tr("toolu_A", "plain")])])
    doc = cand(root, home, whole(home))
    assert doc == listed(data_of(home), [])
    assert (doc["candidate_count"], doc["candidates"], doc["exit_code"], doc["checks"]["selected"]) == (0, [], 0, P)


def test_c2_one_candidate(cand, tmp_path, root):
    home = make_home(tmp_path, [NOISE, user([TEXT, tr("toolu_A", [TEXT, at(ctext(BA))])])])
    assert cand(root, home, whole(home)) == listed(data_of(home), [t_item(1, 2, "toolu_A", BA, block=2, k=2)])


def test_c2_assistant_and_tool_result_mixed_in_prefix_order(cand, tmp_path, root):
    home = make_home(tmp_path, [NOISE, asst([TEXT, at(ctext(BA))]), NOISE, user([tr("toolu_B", ctext(BB))])])
    assert cand(root, home, whole(home)) == listed(data_of(home), [
        a_item(1, 2, UUID, BA, k=2), t_item(2, 4, "toolu_B", BB)])


def test_c2_wo2_text_index_after_skipped_nontext_is_the_run_index(cand, capsysbinary, tmp_path, root):
    nontext = {"type": "image", "source": {"data": "abc"}}
    home = make_home(tmp_path, [NOISE, user([tr("toolu_N", [nontext, at("plain"), at(ctext(BA))])])])
    data = data_of(home)
    assert cand(root, home, whole(home, WO2)) == listed(data, [t_item(1, 2, "toolu_N", BA, k=2)], WO2)
    doc = call_doc(capsysbinary, root, home, run_argv("tool_result:toolu_N:text:2", "001", WO2))
    assert (doc["status"], doc["values"]) == ("SUCCEEDED", vals(BA))
    assert cand(root, home, whole(home))["status"] == "FORMAT_UNSUPPORTED"  # /1 keeps S4d


# ----------------------------------------------------------------------------------------- C3: limit


def test_c3_eight_candidates_are_listed(cand, tmp_path, root):
    home = make_home(tmp_path, [asst([at(ctext(BA))], uuid=uid(i)) for i in range(1, 9)])
    doc = cand(root, home, whole(home))
    assert doc == listed(data_of(home), [a_item(i, i, uid(i), BA) for i in range(1, 9)])


@pytest.mark.parametrize("count", [9, 12])
def test_c3_more_than_eight_candidates_stop_the_scan(cand, tmp_path, root, rehash_calls, count):
    home = make_home(tmp_path, [asst([at(ctext(BA))], uuid=uid(i)) for i in range(1, count + 1)])
    doc = cand(root, home, whole(home))
    assert doc == expected(LIMIT, fixed(data_of(home)), P, LS, NR)
    assert (doc["candidate_count_at_least"], doc["candidate_count"], doc["candidates"]) == (9, None, None)
    assert len(rehash_calls) == 1


def test_c3_the_scan_stops_before_a_corrupt_line_after_the_ninth(cand, tmp_path, root):
    lines = [asst([at(ctext(BA))], uuid=uid(i)) for i in range(1, 10)] + [b"not json\n"]
    home = make_home(tmp_path, lines)
    assert cand(root, home, whole(home)) == expected(LIMIT, fixed(data_of(home)), P, LS, NR)
    eight = make_home(tmp_path, lines[:8] + [b"not json\n"], "home8")
    assert cand(root, eight, whole(eight)) == expected("SESSION_CORRUPT", fixed(data_of(eight)), P, F, NR)


def test_c3_direct_call_keeps_eight_positions():
    judge = lambda text: profiles.marker_line_present(profiles.WORK_ORDER, text)  # noqa: E731
    prefix = b"".join([asst([at(ctext(BA))], uuid=uid(i)) for i in range(1, 10)] + [b"not json\n"])
    positions: list[tuple[int, int | None, bytes]] = []
    with pytest.raises(transcript.CandidateLimitReached) as err:
        transcript.scan_candidates(prefix, profiles.WORK_ORDER.kinds, judge, transcript.Deadline(),
                                   positions=positions, limit=8)
    assert not isinstance(err.value, ControlledReadError)
    assert len(positions) == 8 and [p[0] for p in positions] == list(range(1, 9))
    with pytest.raises(ControlledReadError) as corrupt:
        transcript.scan_candidates(prefix, profiles.WORK_ORDER.kinds, judge, transcript.Deadline())
    assert corrupt.value.code == "SESSION_CORRUPT"


def test_c3_tool_result_candidates_count_toward_the_limit():
    judge = lambda text: profiles.marker_line_present(profiles.WORK_ORDER, text)  # noqa: E731
    prefix = b"".join([user([tr(f"toolu_{i}", [at(ctext(BA)), at(ctext(BB))])]) for i in range(1, 6)])
    positions: list[tuple[int, int | None, bytes]] = []
    with pytest.raises(transcript.CandidateLimitReached):
        transcript.scan_candidates(prefix, profiles.WORK_ORDER.kinds, judge, transcript.Deadline(),
                                   positions=positions, limit=8)
    assert [(p[0], p[1]) for p in positions] == [(i, 1) for i in range(1, 5) for _ in range(2)]


# -------------------------------------------------------------------- C4: position, selector, content


def test_c4_text_1_and_text_2_of_one_block(cand, tmp_path, root):
    home = make_home(tmp_path, [NOISE, user([tr("toolu_S", [at(ctext(BA)), at(ctext(BB))])])])
    assert cand(root, home, whole(home)) == listed(data_of(home), [
        t_item(1, 2, "toolu_S", BA, k=1), t_item(2, 2, "toolu_S", BB, k=2)])


def test_c4_same_content_at_two_places(cand, tmp_path, root):
    home = make_home(tmp_path, [asst([at(ctext(BA))], uuid=UUID), NOISE, asst([at(ctext(BA))], uuid=UUID2)])
    doc = cand(root, home, whole(home))
    assert doc == listed(data_of(home), [a_item(1, 1, UUID, BA), a_item(2, 3, UUID2, BA)])
    first, second = doc["candidates"]
    assert first["values"] == second["values"]
    assert first["selector"] != second["selector"] and first["line"] != second["line"]


def test_c4_equal_selectors_are_duplicates_without_selection(cand, monkeypatch, tmp_path, root):
    home = make_home(tmp_path, [asst([at(ctext(BA))], uuid=UUID), asst([at(ctext(BB))], uuid=UUID),
                                asst([at(ctext(BC))], uuid=UUID2)])
    selects = spy(monkeypatch, transcript, "select_text")
    assert cand(root, home, whole(home)) == listed(data_of(home), [
        a_item(1, 1, UUID, selected="SELECTOR_DUPLICATE"), a_item(2, 2, UUID, selected="SELECTOR_DUPLICATE"),
        a_item(3, 3, UUID2, BC)])
    assert len(selects) == 1 and selects[0][0][1] == grammar.Selector("assistant", UUID2, 1)


def test_c4_only_duplicates_select_nothing(cand, monkeypatch, tmp_path, root):
    home = make_home(tmp_path, [asst([at(ctext(BA))], uuid=UUID), asst([at(ctext(BA))], uuid=UUID)])
    selects = spy(monkeypatch, transcript, "select_text")
    assert cand(root, home, whole(home)) == listed(data_of(home), [
        a_item(1, 1, UUID, selected="SELECTOR_DUPLICATE"), a_item(2, 2, UUID, selected="SELECTOR_DUPLICATE")])
    assert selects == []


def test_c4_duplicate_ident_with_different_selectors(cand, tmp_path, root):
    home = make_home(tmp_path, [user([tr("toolu_D", [at(ctext(BA))])]),
                                user([tr("toolu_D", [at("plain"), at(ctext(BB))])])])
    assert cand(root, home, whole(home)) == listed(data_of(home), [
        t_item(1, 1, "toolu_D", selected="ENTRY_DUPLICATE", k=1),
        t_item(2, 2, "toolu_D", selected="ENTRY_DUPLICATE", k=2)])


def test_c4_ident_shared_with_a_block_that_is_no_candidate(cand, tmp_path, root):
    home = make_home(tmp_path, [user([tr("toolu_C", ctext(BA))]), user([tr("toolu_C", "plain")]),
                                asst([at(ctext(BB))])])
    assert cand(root, home, whole(home)) == listed(data_of(home), [
        t_item(1, 1, "toolu_C", selected="ENTRY_DUPLICATE"), a_item(2, 3, UUID, BB)])


def test_c4_selection_of_other_content_is_a_mismatch(cand, monkeypatch, tmp_path, root):
    home = make_home(tmp_path, [asst([at(ctext(BA))])])
    monkeypatch.setattr(transcript, "select_text", lambda *_args, **_kwargs: ctext(BB))
    assert cand(root, home, whole(home)) == listed(data_of(home), [
        a_item(1, 1, UUID, selected="SELECTION_MISMATCH")])


def test_c4_unrepresentable_selectors(cand, tmp_path, root):
    lines = [asst([TEXT] * 99 + [at(ctext(BA))], uuid=UUID),
             line({"type": "assistant", "message": {"content": [at(ctext(BB))]}}),
             user([tr(LEAK_ID, ctext(BC))]),
             asst([at(ctext(BA))], uuid=UUID2)]
    home = make_home(tmp_path, lines)
    doc = cand(root, home, whole(home))
    unrep = "SELECTOR_UNREPRESENTABLE"
    assert doc == listed(data_of(home), [
        item(1, 1, "assistant", None, unrep, None, None, 100), item(2, 2, "assistant", None, unrep),
        item(3, 3, "tool_result", None, unrep, None, 1), a_item(4, 4, UUID2, BA)])
    assert LEAK_ID not in json.dumps(doc)


def test_c4_no_choice_or_canon_fields():
    assert diagnose.CANDIDATES_KEYS == KEYS and diagnose.CANDIDATE_ITEM_KEYS == ITEM_KEYS
    for name in ("recommended", "latest", "first", "canonical", "chosen"):
        assert all(name not in key for key in KEYS | ITEM_KEYS)


# ------------------------------------------------------------------------- C5: candidate-level codes


def test_c5_candidate_level_rejections_keep_the_other_candidates(cand, tmp_path, root):
    lines = [asst([at(f"{WB}\nLEAKTOKEN-X\n")], uuid=uid(1)),
             asst([at(f"{WB}\n{WB}\nLEAKTOKEN-X\n{WE}\n")], uuid=uid(2)),
             asst([at(f"{WE}\nLEAKTOKEN-X\n{WB}\n")], uuid=uid(3)),
             asst([at(f"{WB}\n\n{WE}\n")], uuid=uid(4)),
             user([tr("toolu_E", ctext(BB), is_error=True)]),
             asst([at(ctext(BA))], uuid=uid(6)),
             asst([at("\N{ZERO WIDTH NO-BREAK SPACE}" + ctext(BC))], uuid=uid(7)),
             asst([at(f"{WB}\nLEAKTOKEN-X\rY\n{WE}\n")], uuid=uid(8))]
    home = make_home(tmp_path, lines)
    assert cand(root, home, whole(home)) == listed(data_of(home), [
        a_item(1, 1, uid(1), selected="MARKER_MISSING"), a_item(2, 2, uid(2), selected="MARKER_DUPLICATE"),
        a_item(3, 3, uid(3), selected="MARKER_ORDER_INVALID"), a_item(4, 4, uid(4), selected="BODY_EMPTY"),
        t_item(5, 5, "toolu_E", selected="TOOL_RESULT_ERROR", is_error=True), a_item(6, 6, uid(6), BA),
        a_item(7, 7, uid(7), selected="BOM_PRESENT"), a_item(8, 8, uid(8), selected="CR_PRESENT")])


def test_c5_encoding_invalid(cand, tmp_path, root):
    home = make_home(tmp_path, [asst([at(f"{WB}\n\U0000d800\n{WE}\n")], uuid=UUID), asst([at(ctext(BA))], uuid=UUID2)])
    assert cand(root, home, whole(home)) == listed(data_of(home), [
        a_item(1, 1, UUID, selected="ENCODING_INVALID"), a_item(2, 2, UUID2, BA)])


def test_c5_text_and_body_limits(cand, monkeypatch, tmp_path, root):
    big = "LEAKTOKEN-" + "x" * 200
    home = make_home(tmp_path, [asst([at(ctext(big))], uuid=UUID), asst([at(ctext(BA))], uuid=UUID2)])
    with monkeypatch.context() as m:
        m.setattr(profiles, "TEXT_LIMIT", len(ctext(BA)) + 10)
        assert cand(root, home, whole(home)) == listed(data_of(home), [
            a_item(1, 1, UUID, selected="TEXT_LIMIT_EXCEEDED"), a_item(2, 2, UUID2, BA)])
    with monkeypatch.context() as m:
        m.setattr(profiles, "BODY_LIMIT", len(BA) + 10)
        assert cand(root, home, whole(home)) == listed(data_of(home), [
            a_item(1, 1, UUID, selected="BODY_LIMIT_EXCEEDED"), a_item(2, 2, UUID2, BA)])


# ------------------------------------------------------------------- C6: whole failures drop the list


def test_c6_time_out_while_scanning_skips_the_rehash(cand, monkeypatch, tmp_path, root, clock, rehash_calls):
    home = make_home(tmp_path, [asst([at(ctext(BA))]), NOISE])
    real = transcript.parse_line

    def parse_then_expire(raw: bytes) -> dict[str, Any]:
        clock.now = 1000.0
        return real(raw)
    monkeypatch.setattr(transcript, "parse_line", parse_then_expire)
    assert cand(root, home, whole(home)) == expected(
        "TIME_LIMIT_EXCEEDED", fixed(data_of(home), "INCOMPLETE"), P, F, NR)
    assert rehash_calls == []


def _second_select(monkeypatch, effect):
    real = transcript.select_text
    calls: list[int] = []

    def seam(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            effect()
        return real(*args, **kwargs)
    monkeypatch.setattr(transcript, "select_text", seam)
    return calls


TWO = [asst([at(ctext(BA))], uuid=UUID), asst([at(ctext(BB))], uuid=UUID2)]


def test_c6_time_out_while_selecting_skips_the_rehash(cand, monkeypatch, tmp_path, root, clock, rehash_calls):
    home = make_home(tmp_path, TWO)

    def expire():
        clock.now = 1000.0
    calls = _second_select(monkeypatch, expire)
    doc = cand(root, home, whole(home))
    assert doc == expected("TIME_LIMIT_EXCEEDED", fixed(data_of(home), "INCOMPLETE"), P, P, F)
    assert rehash_calls == [] and len(calls) == 2
    assert vals(BA)["sha256"] not in json.dumps(doc)


@pytest.mark.parametrize("code", ["FORMAT_UNSUPPORTED", "SELECTOR_KIND_MISMATCH", "TEXT_BLOCK_AMBIGUOUS",
                                  "SESSION_CORRUPT", "LINE_LIMIT_EXCEEDED", "ENTRY_LIMIT_EXCEEDED",
                                  "SESSION_UNREADABLE"])
def test_c6_selection_failure_drops_every_item(cand, monkeypatch, tmp_path, root, rehash_calls, code):
    home = make_home(tmp_path, TWO)

    def fail():
        raise ControlledReadError(code)
    _second_select(monkeypatch, fail)
    doc = cand(root, home, whole(home))
    assert doc == expected(code, fixed(data_of(home)), P, P, F)
    assert len(rehash_calls) == 1 and vals(BA)["sha256"] not in json.dumps(doc)


def test_c6_format_violation_while_selecting(cand, monkeypatch, tmp_path, root):
    home = make_home(tmp_path, TWO)

    def fail():
        raise transcript.FormatViolation("S4d", "tool_result.content[]", "object", "number", item_index=1)
    _second_select(monkeypatch, fail)
    assert cand(root, home, whole(home)) == expected("FORMAT_UNSUPPORTED", fixed(data_of(home)), P, P, F)


def test_c6_extract_failure_of_a_whole_selection_code(cand, monkeypatch, tmp_path, root):
    home = make_home(tmp_path, TWO)

    def extract(_profile, _text):
        raise ControlledReadError("FORMAT_UNSUPPORTED")
    monkeypatch.setattr(profiles, "extract", extract)
    assert cand(root, home, whole(home)) == expected("FORMAT_UNSUPPORTED", fixed(data_of(home)), P, P, F)


def test_c6_scan_format_unsupported(cand, tmp_path, root, rehash_calls):
    home = make_home(tmp_path, [asst([at(ctext(BA))]), asst([TEXT, 5], uuid=UUID2)])
    assert cand(root, home, whole(home)) == expected("FORMAT_UNSUPPORTED", fixed(data_of(home)), P, F, NR)
    assert len(rehash_calls) == 1


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
@pytest.mark.parametrize("lines, scan", [
    (TWO, P), ([asst([at(ctext(BA))], uuid=uid(i)) for i in range(1, 10)], LS)])
def test_c6_rehash_replaces_the_result(cand, monkeypatch, tmp_path, root, clock, kind, code, check, lines, scan):
    home = make_home(tmp_path, lines)
    data = data_of(home)

    def fail(*_args):
        raise OSError("gone")

    def expire_after_read(_handle):
        clock.queue = [0.0]
        clock.now = 1000.0
    hooks = {"truncate": _truncate(home), "overwrite": _overwrite(home),
             "unreadable": lambda _h: monkeypatch.setattr(transcript, "_fstat", fail),
             "expired_after": expire_after_read,
             "expired_before": lambda _h: None}
    if kind == "expired_before":
        real = transcript.Session.rehash

        def expire_then_rehash(self, deadline):
            clock.now = 1000.0
            return real(self, deadline)
        monkeypatch.setattr(transcript.Session, "rehash", expire_then_rehash)
    monkeypatch.setattr(transcript, "_before_rehash", hooks[kind])
    doc = cand(root, home, whole(home))
    assert doc == expected(code, fixed(data, check), P, scan, P if scan == P else NR)
    assert (doc["candidates"], doc["candidate_count"], doc["candidate_count_at_least"]) == (None, None, None)


def test_c6_prefix_mismatch_and_not_line_aligned(cand, tmp_path, root):
    home = make_home(tmp_path, [asst([at(ctext(BA))]), NOISE])
    data = data_of(home)
    assert cand(root, home, cargs(len(data), "0" * 64)) == expected(
        "DIAGNOSE_PREFIX_MISMATCH", target(len(data), "0" * 64, len(data)), F)
    n = len(data) - 1
    assert cand(root, home, cargs(n, sha(data[:n]))) == expected(
        "DIAGNOSE_PREFIX_NOT_LINE_ALIGNED", target(n, sha(data[:n]), len(data)), F)


def test_c6_fixed_prefix_excludes_trailing_bytes(cand, tmp_path, root):
    head = [asst([at(ctext(BA))])]
    home = make_home(tmp_path, [*head, asst([at(ctext(BB))], uuid=UUID2), b'{"partial'])
    data = data_of(home)
    n = len(b"".join(head))
    tgt = target(n, sha(data[:n]), len(data), len(data) - n, 1, "MATCHED")
    assert cand(root, home, cargs(n, sha(data[:n]))) == expected(LISTED, tgt, P, P, P, [a_item(1, 1, UUID, BA)])


def test_c6_session_missing_and_shorter(cand, tmp_path, root):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert cand(root, empty, cargs(1, "0" * 64)) == expected("SESSION_NOT_FOUND", target(1, "0" * 64), F)
    home = make_home(tmp_path, [NOISE])
    data = data_of(home)
    assert cand(root, home, cargs(len(data) + 1, sha(data))) == expected(
        "SESSION_TRUNCATED", target(len(data) + 1, sha(data), len(data)), F)


def test_c6_environment_invalid(cand, tmp_path):
    home = make_home(tmp_path, [NOISE])
    plain = tmp_path / "plain"
    plain.mkdir()
    data = data_of(home)
    assert cand(plain, home, whole(home)) == expected("ENVIRONMENT_INVALID", target(len(data), sha(data)))


@pytest.mark.parametrize("args", [
    ["candidates"], cargs(1, "0" * 64) + ["x"], cargs(0, "0" * 64), cargs("012", "0" * 64),
    cargs(67108865, "0" * 64), cargs(1, "A" * 64), cargs(1, "0" * 63), cargs(1, "0" * 64, profile="OTHER/1"),
    cargs(1, "0" * 64, task="A" * 65), cargs(1, "0" * 64)[:3] + ["--project-key", "../x"] + cargs(1, "0" * 64)[5:],
    ["candidates", "--project-key", PK, "--task", TASK] + cargs(1, "0" * 64)[5:],
])
def test_c6_argument_invalid_echoes_nothing(cand, tmp_path, args):
    assert cand(tmp_path / "unused", tmp_path / "unused", args) == ARG_INVALID
    assert not (tmp_path / "unused").exists()


# -------------------------------------------------------------------- C6b: internal invariant violation


@pytest.mark.parametrize("module, name", [(grammar, "parse_selector"), (transcript, "select_text")])
def test_c6b_argument_invalid_while_selecting_ends_without_output(capsysbinary, monkeypatch, tmp_path, root,
                                                                  module, name):
    home = make_home(tmp_path, TWO)

    def refuse(*_args, **_kwargs):
        raise ControlledReadError("ARGUMENT_INVALID")
    monkeypatch.setattr(module, name, refuse)
    with pytest.raises(Exception) as err:
        cli.main(whole(home), root=root, home=home)
    assert not isinstance(err.value, ControlledReadError)
    assert capsysbinary.readouterr() == (b"", b"")
    assert len(OPENED) == 1 and OPENED[0].closed


def test_c6b_argument_invalid_from_extract_ends_without_output(capsysbinary, monkeypatch, tmp_path, root):
    home = make_home(tmp_path, TWO)

    def refuse(_profile, _text):
        raise ControlledReadError("ARGUMENT_INVALID")
    monkeypatch.setattr(profiles, "extract", refuse)
    with pytest.raises(Exception) as err:
        cli.main(whole(home), root=root, home=home)
    assert not isinstance(err.value, ControlledReadError)
    assert capsysbinary.readouterr() == (b"", b"")


def test_c6b_undefined_status_ends_without_output(capsysbinary, monkeypatch, tmp_path, root):
    home = make_home(tmp_path, TWO)

    def fail(*_args, **_kwargs):
        raise ControlledReadError("STORE_FAILED")
    monkeypatch.setattr(transcript, "select_text", fail)
    with pytest.raises(ValueError):
        cli.main(whole(home), root=root, home=home)
    assert capsysbinary.readouterr() == (b"", b"")
    assert len(OPENED) == 1 and OPENED[0].closed


# --------------------------------------------------------------------------- C7: document validation


def _valid() -> dict[str, Any]:
    return diagnose.candidates_document(
        LISTED, task_id=TASK, target=target(100, "0" * 64, 100, 0, 3, "MATCHED"), profile={"id": WO, "version": 1},
        checks={"prefix": P, "scan": P, "selected": P},
        candidates=[a_item(1, 1, UUID, BA), t_item(2, 2, "toolu_A", BB, block=2, k=3)])


def _set(path: tuple[Any, ...], value: Any):
    def change(doc: dict[str, Any]) -> None:
        node: Any = doc
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    return change


def _drop(key: str):
    def change(doc: dict[str, Any]) -> None:
        del doc[key]
    return change


def _same_selector(doc: dict[str, Any]) -> None:
    doc["candidates"][1] = {**doc["candidates"][0], "index": 2, "line": 2}


def _duplicate_alone(doc: dict[str, Any]) -> None:
    doc["candidates"][0].update(selected="SELECTOR_DUPLICATE", values=None)


C7_CHANGES = {
    "extra-key": _set(("extra",), 1), "missing-key": _drop("boundary"), "missing-candidates": _drop("candidates"),
    "status-outside": _set(("status",), "OTHER"), "status-store": _set(("status",), "STORE_FAILED"),
    "status-local": _set(("status",), "MARKER_MISSING"), "schema": _set(("schema",), "x"),
    "authority": _set(("authority",), "ALL"),
    "detail": _set(("error",), {"code": LISTED, "detail": "x"}),
    "checks-selected-failed": _set(("checks", "selected"), F), "checks-scan-limit": _set(("checks", "scan"), LS),
    "checks-extra": _set(("checks", "other"), P),
    "count-null": _set(("candidate_count",), None), "count-wrong": _set(("candidate_count",), 3),
    "at-least": _set(("candidate_count_at_least",), 9),
    "exit-bool": _set(("exit_code",), False), "exit-2": _set(("exit_code",), 2),
    "count-bool": _set(("candidate_count",), True),
    "line-bool": _set(("candidates", 0, "line"), True), "index-bool": _set(("candidates", 0, "index"), True),
    "is-error-int": _set(("candidates", 0, "is_error"), 0),
    "selector-grammar": _set(("candidates", 0, "selector"), "assistant:XYZ:text:1"),
    "selector-kind": _set(("candidates", 0, "kind"), "tool_result"),
    "selector-k": _set(("candidates", 1, "text_index"), 2),
    "index-gap": _set(("candidates", 1, "index"), 3),
    "line-decrease": _set(("candidates", 0, "line"), 3),
    "line-over": _set(("candidates", 1, "line"), 4),
    "values-without-ok": _set(("candidates", 0, "selected"), "MARKER_MISSING"),
    "ok-without-values": _set(("candidates", 0, "values"), None),
    "values-keys": _set(("candidates", 0, "values", "extra"), 1),
    "values-bytes": _set(("candidates", 0, "values", "bytes"), 1048577),
    "values-sha": _set(("candidates", 0, "values", "sha256"), "A" * 64),
    "duplicate-alone": _duplicate_alone, "selector-twice": _same_selector,
    "unrepresentable-with-selector": _set(("candidates", 0, "selected"), "SELECTOR_UNREPRESENTABLE"),
    "null-selector": _set(("candidates", 0, "selector"), None),
    "block-index-assistant": _set(("candidates", 0, "block_index"), 1),
    "block-index-tool": _set(("candidates", 1, "block_index"), None),
    "item-key": _set(("candidates", 0, "extra"), 1),
    "profile-version": _set(("profile", "version"), 2), "profile-id": _set(("profile", "id"), "OTHER/1"),
    "profile-version-bool": _set(("profile", "version"), True),
    "task-id": _set(("task_id",), "bad task"), "task-null": _set(("task_id",), None),
    "target-key": _set(("target", "extra"), 1), "target-check": _set(("target", "prefix_check"), "CHANGED"),
    "target-trailing": _set(("target", "trailing_bytes_excluded"), 1),
    "target-line-count": _set(("target", "line_count"), 0),
    "target-sha": _set(("target", "expected_prefix_sha256"), "A" * 64),
    "target-bytes-bool": _set(("target", "expected_prefix_bytes"), True),
}


@pytest.mark.parametrize("change", list(C7_CHANGES.values()), ids=list(C7_CHANGES))
def test_c7_document_check_refuses(change):
    doc = _valid()
    diagnose.check_candidates_document(copy.deepcopy(doc))
    bad = copy.deepcopy(doc)
    change(bad)
    with pytest.raises(ValueError):
        diagnose.check_candidates_document(bad)


def _error_doc(status: str, checks: dict[str, str], tgt: dict[str, Any]) -> dict[str, Any]:
    return diagnose.candidates_document(status, task_id=TASK, target=tgt, profile={"id": WO, "version": 1},
                                        checks=checks)


MATCHED_TARGET = target(100, "0" * 64, 100, 0, 3, "MATCHED")


@pytest.mark.parametrize("status, checks, tgt", [
    ("ENVIRONMENT_INVALID", {"prefix": NR, "scan": NR, "selected": NR}, target(1, "0" * 64)),
    ("SESSION_NOT_FOUND", {"prefix": F, "scan": NR, "selected": NR}, target(1, "0" * 64)),
    ("FORMAT_UNSUPPORTED", {"prefix": P, "scan": F, "selected": NR}, MATCHED_TARGET),
    ("SESSION_CHANGED", {"prefix": P, "scan": P, "selected": P}, target(100, "0" * 64, 100, 0, 3, "CHANGED")),
    (LIMIT, {"prefix": P, "scan": LS, "selected": NR}, MATCHED_TARGET),
    ("TEXT_BLOCK_AMBIGUOUS", {"prefix": P, "scan": P, "selected": F}, MATCHED_TARGET),
])
def test_c7_defined_error_documents_pass(status, checks, tgt):
    doc = _error_doc(status, checks, tgt)
    assert doc["error"] == {"code": status, "detail": TABLE[status]}
    assert doc["candidate_count_at_least"] == (9 if status == LIMIT else None)


@pytest.mark.parametrize("status, checks, tgt", [
    ("FORMAT_UNSUPPORTED", {"prefix": P, "scan": P, "selected": P}, MATCHED_TARGET),
    ("SESSION_NOT_FOUND", {"prefix": P, "scan": F, "selected": NR}, MATCHED_TARGET),
    ("ENVIRONMENT_INVALID", {"prefix": F, "scan": NR, "selected": NR}, target(1, "0" * 64)),
    (LIMIT, {"prefix": P, "scan": P, "selected": P}, MATCHED_TARGET),
    (LIMIT, {"prefix": P, "scan": LS, "selected": NR}, target(100, "0" * 64, 100, 0, 3, "CHANGED")),
    ("SESSION_TRUNCATED", {"prefix": P, "scan": P, "selected": P}, MATCHED_TARGET | {"prefix_check": "CHANGED"}),
    ("SESSION_NOT_FOUND", {"prefix": F, "scan": NR, "selected": NR}, MATCHED_TARGET),
    ("ARGUMENT_INVALID", {"prefix": NR, "scan": NR, "selected": NR}, target(1, "0" * 64)),
    ("MARKER_MISSING", {"prefix": P, "scan": P, "selected": F}, MATCHED_TARGET),
    ("SESSION_LIMIT_EXCEEDED", {"prefix": F, "scan": NR, "selected": NR}, target(1, "0" * 64)),
])
def test_c7_inconsistent_error_documents_are_refused(status, checks, tgt):
    with pytest.raises(ValueError):
        _error_doc(status, checks, tgt)


def test_c7_argument_invalid_passes_only_without_identifying_fields():
    doc = diagnose.candidates_document("ARGUMENT_INVALID")
    assert doc == ARG_INVALID
    diagnose.check_candidates_document(copy.deepcopy(doc))
    for key, value in (("task_id", TASK), ("checks", {"prefix": NR, "scan": NR, "selected": NR}),
                       ("target", target(1, "0" * 64)), ("profile", {"id": WO, "version": 1}),
                       ("candidates", []), ("candidate_count", 0)):
        with pytest.raises(ValueError):
            diagnose.check_candidates_document({**copy.deepcopy(doc), key: value})


def test_c7_listed_document_is_copied():
    items = [a_item(1, 1, UUID, BA)]
    doc = diagnose.candidates_document(
        LISTED, task_id=TASK, target=MATCHED_TARGET, profile={"id": WO, "version": 1},
        checks={"prefix": P, "scan": P, "selected": P}, candidates=items)
    items[0]["values"]["bytes"] = 0
    items.append({})
    assert doc["candidates"] == [a_item(1, 1, UUID, BA)] and doc["candidate_count"] == 1


# ---------------------------------------------------------------------------------- C8: leaks, records


def test_c8_no_body_key_type_identifier_or_non_ascii_value_is_printed(cand, tmp_path, root):
    lines = [
        line({"type": "user", "uuid": UUID3, LEAK_KEY: BC, "message": {"content": [
            tr("toolu_L", [{"type": LEAK_TYPE, LEAK_KEY: LEAK_NONASCII}, at(ctext(LEAK_NONASCII))])]}}),
        asst([at(ctext(BA)), {"type": "thinking", "thinking": LEAK_NONASCII}], uuid=UUID),
        user([tr(LEAK_ID, ctext(BB))]),
    ]
    home = make_home(tmp_path, lines)
    doc = cand(root, home, whole(home, WO2))
    assert doc == listed(data_of(home), [
        t_item(1, 1, "toolu_L", LEAK_NONASCII), a_item(2, 2, UUID, BA),
        item(3, 3, "tool_result", None, "SELECTOR_UNREPRESENTABLE", None, 1)], WO2)
    assert all(ord(ch) < 128 for ch in json.dumps(doc, ensure_ascii=False))


# -------------------------------------------------------------------------------- C9: profiles, policy


PROFILE_LINES = [NOISE, user([tr("toolu_P", ptext(BA)), tr("toolu_W", ctext(BB))]), asst([at(ctext(BC))])]


@pytest.mark.parametrize("profile", [WO, PREREG])
def test_c9_profiles_without_the_policy_pass_no_nontext(cand, monkeypatch, tmp_path, root, profile):
    home = make_home(tmp_path, PROFILE_LINES)
    scans = spy(monkeypatch, transcript, "scan_candidates")
    selects = spy(monkeypatch, transcript, "select_text")
    items = ([t_item(1, 2, "toolu_P", BA)] if profile == PREREG
             else [t_item(1, 2, "toolu_W", BB, block=2), a_item(2, 3, UUID, BC)])
    assert cand(root, home, whole(home, profile)) == listed(data_of(home), items, profile)
    assert len(scans) == 1 and len(selects) == len(items)
    assert all("nontext" not in kwargs for _args, kwargs in scans + selects)


def test_c9_wo2_makes_a_new_policy_for_every_call(cand, monkeypatch, tmp_path, root):
    home = make_home(tmp_path, PROFILE_LINES)
    made: list[Any] = []
    real = transcript.NontextPolicy

    class Recording(real):  # type: ignore[misc, valid-type]
        def __init__(self, *args: Any) -> None:
            super().__init__(*args)
            made.append(self)
    monkeypatch.setattr(transcript, "NontextPolicy", Recording)
    scans = spy(monkeypatch, transcript, "scan_candidates")
    selects = spy(monkeypatch, transcript, "select_text")
    assert cand(root, home, whole(home, WO2)) == listed(data_of(home), [
        t_item(1, 2, "toolu_W", BB, block=2), a_item(2, 3, UUID, BC)], WO2)
    assert len(made) == 1 + len(selects) == 3
    assert len({id(policy) for policy in made}) == 3
    assert [kwargs["nontext"] for _args, kwargs in scans + selects] == made


# ------------------------------------------------------------------------------------- C10: constants


def test_c10_constants():
    assert diagnose.CANDIDATES_SCHEMA == SCHEMA
    assert diagnose.CANDIDATES_OPTIONS == ("--task", "--project-key", "--session", "--profile",
                                           "--expect-prefix-bytes", "--expect-prefix-sha256")
    assert diagnose.CANDIDATE_LIMIT == 8
    assert diagnose.CANDIDATES_DETAILS == {
        LISTED: "every candidate of the fixed prefix is listed with its selection result", LIMIT: TABLE[LIMIT]}
    for other in (DETAILS, store.PRECHECK_DETAILS, diagnose.DIAGNOSE_DETAILS):
        assert set(diagnose.CANDIDATES_DETAILS).isdisjoint(other)
    assert diagnose.CANDIDATE_LOCAL_CODES == LOCAL and diagnose.CANDIDATES_GLOBAL_CODES == GLOBAL
    assert LOCAL.isdisjoint(GLOBAL) and "ARGUMENT_INVALID" not in LOCAL | GLOBAL
    assert diagnose.CANDIDATE_STATES == {"OK", "SELECTOR_UNREPRESENTABLE", "SELECTOR_DUPLICATE",
                                         "SELECTION_MISMATCH"} | LOCAL
    assert diagnose.CANDIDATES_ERROR_DETAILS == TABLE
    assert LOCAL | GLOBAL <= set(DETAILS)
    assert not issubclass(transcript.CandidateLimitReached, ControlledReadError)


def test_c10_parse_candidates():
    assert diagnose.parse_candidates(cargs(5, "a" * 64)) == diagnose.DiagnoseArgs(TASK, PK, SID, WO, 5, "a" * 64)
    assert diagnose.parse_candidates(cargs(67108864, "0" * 64, WO2)).prefix_bytes == 67108864
    for bad in (cargs(5, "a" * 64)[:-1], ["diagnose", *cargs(5, "a" * 64)[1:]], cargs(5, "a" * 64) + ["--x"]):
        with pytest.raises(ControlledReadError) as err:
            diagnose.parse_candidates(bad)
        assert err.value.code == "ARGUMENT_INVALID"


# ---------------------------------------------------------------------------------------- C11: handles


@pytest.mark.parametrize("lines", [TWO, [asst([at(ctext(BA))], uuid=uid(i)) for i in range(1, 10)],
                                   [asst([TEXT, 5])]])
def test_c11_the_handle_is_closed(cand, tmp_path, root, lines):
    home = make_home(tmp_path, lines)
    cand(root, home, whole(home))
    assert len(OPENED) == 1 and OPENED[0].closed
