"""AUTO-12-CONTROLLED-READ-NONTEXT T1-T10: profile ECON-FWD-M20-WO/2 and the non-text item scan (N1-N6).

Every input is a synthetic session in tmp_path or a synthetic object; the real home, real session records
and the repository data/ are never opened. Non-ASCII synthetic input uses explicit escapes."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from moneylab.controlled_read import ControlledReadError, diagnose, profiles, transcript
from moneylab.controlled_read import __main__ as cli
from moneylab.controlled_read import selector as grammar

PK = "C--synthetic-project"
SID = "0a1b2c3d-0000-4000-8000-00000000abcd"
UUID2 = "22222222-2222-4333-8444-555555555555"
UUID3 = "33333333-2222-4333-8444-555555555555"
TASK = "AUTO-12-SYNTH"
V1, PREREG, V2 = "ECON-FWD-M20-WO/1", "ECON-FWD-M20-PREREG/1", "ECON-FWD-M20-WO/2"
WB = "-----BEGIN ECON-FWD-M20 WORK ORDER CANDIDATE-----"
WE = "-----END ECON-FWD-M20 WORK ORDER CANDIDATE-----"
TID, TID2 = "toolu_nt01", "toolu_nt02"
LEAK = b"LEAKTOKEN"  # every synthetic type name, key, value and body below contains it; no output may
LEAK_TYPE = "LEAKTOKEN-NT-TYPE-4b1e"
LEAK_KEY = "LEAKTOKEN-NT-KEY-90c3"
LEAK_VALUE = "LEAKTOKEN-NT-VALUE-27da"
LEAK_NONASCII = "LEAKTOKEN-NT-\N{LATIN SMALL LETTER E WITH ACUTE}\N{HIRAGANA LETTER A}\U0001f600-NONASCII"
NONASCII_BYTES = "\N{LATIN SMALL LETTER E WITH ACUTE}\N{HIRAGANA LETTER A}".encode("utf-8")
BODY_A = "LEAKTOKEN-NT-BODY-A-61f0"
BODY_B = "LEAKTOKEN-NT-BODY-B-0d8c"
TEXT_A = {"type": "text", "text": f"{WB}\n{BODY_A}\n{WE}\n"}
TEXT_B = {"type": "text", "text": f"{WB}\n{BODY_B}\n{WE}\n"}
PLAIN = {"type": "text", "text": "LEAKTOKEN-NT-PLAIN-5e44"}
E = "SELECTED_ENTRY_ONLY"
FU = "FORMAT_UNSUPPORTED"
V2_PROFILE = profiles.PROFILES[V2]


# ------------------------------------------------------------------------------------------ helpers


def line(obj: object) -> bytes:
    return json.dumps(obj).encode("utf-8") + b"\n"


def nt(**extra: object) -> dict[str, Any]:
    """A non-text item: an object whose type is a string other than "text" (5 nodes without `extra`)."""
    return {"type": LEAK_TYPE, LEAK_KEY: LEAK_VALUE, **extra}


def tr(content: object, tid: str = TID) -> dict[str, Any]:
    return {"type": "tool_result", "tool_use_id": tid, "content": content}


def entry(*blocks: dict[str, Any]) -> bytes:
    return line({"type": "user", "uuid": UUID3, "message": {"content": list(blocks)}})


NOISE = line({"type": "user", "uuid": UUID2, "message": {"content": "LEAKTOKEN-NT-NOISE-7a2c"}})


def vals(body: str) -> dict[str, Any]:
    data = (body + "\n").encode("ascii")
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "lf": 1}


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


def run_args(selector: str, profile: str = V2, attempt: str = "001") -> list[str]:
    return ["run", "--task", TASK, "--project-key", PK, "--session", SID, "--selector", selector,
            "--profile", profile, "--attempt", attempt]


def precheck_args(profile: str = V2) -> list[str]:
    return ["precheck", "--task", TASK, "--project-key", PK, "--session", SID, "--profile", profile]


def diagnose_args(home: Path, profile: str = V2) -> list[str]:
    data = session_path(home).read_bytes()
    return ["diagnose", "--task", TASK, "--project-key", PK, "--session", SID, "--profile", profile,
            "--expect-prefix-bytes", str(len(data)), "--expect-prefix-sha256", hashlib.sha256(data).hexdigest()]


@pytest.fixture
def call(capsysbinary):
    """One CLI call through main(): one document on stdout, nothing on stderr, no synthetic text (T9)."""
    def run(root: Path, home: Path, args: list[str]) -> dict[str, Any]:
        code = cli.main(args, root=root, home=home)
        out = capsysbinary.readouterr()
        assert out.err == b""
        assert LEAK not in out.out and NONASCII_BYTES not in out.out
        doc = json.loads(out.out)
        assert code == doc["exit_code"]
        return doc
    return run


def viol(check_id: str, field_path: str, expected: str, actual: str, block: int | None, item: int | None,
         line_no: int) -> dict[str, Any]:
    return {"check_id": check_id, "applicability": E, "field_path": field_path, "expected": expected,
            "actual_json_type": actual, "block_index": block, "item_index": item, "line": line_no}


def s4e(block: int, item: int, line_no: int) -> dict[str, Any]:
    return viol("S4e", "tool_result.content[]", "marker_free_nontext", "object", block, item, line_no)


def s4f(block: int, item: int, line_no: int) -> dict[str, Any]:
    return viol("S4f", "tool_result.content[]", "within_nontext_scan_limits", "object", block, item, line_no)


def policy(deadline: Any = None) -> transcript.NontextPolicy:
    return transcript.NontextPolicy(V2_PROFILE.begin, V2_PROFILE.end,
                                    transcript.Deadline() if deadline is None else deadline)


def check_id_of(item: dict[str, Any], pol: transcript.NontextPolicy | None = None) -> str | None:
    """None when the item may be skipped, else the check ID of the violation."""
    try:
        (policy() if pol is None else pol).check(item, 1)
    except transcript.FormatViolation as exc:
        return exc.check_id
    return None


def deep(depth: int, leaf: dict[str, Any] | None = None) -> dict[str, Any]:
    """A non-text root (depth 1) whose innermost object, `leaf` or {"v": "x"}, is at `depth`."""
    node: dict[str, Any] = dict(leaf) if leaf is not None else {"v": "x"}
    for _ in range(depth - 1):
        node = {"c": node}
    return {"type": LEAK_TYPE, **node}


def is_candidate(text: str) -> bool:
    return profiles.marker_line_present(V2_PROFILE, text)


class Clock:
    """transcript._monotonic seam."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


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


@pytest.fixture
def made(monkeypatch) -> list[transcript.NontextPolicy]:
    """Every NontextPolicy the CLI makes, in order (the class is looked up at call time)."""
    objects: list[transcript.NontextPolicy] = []

    class Recording(transcript.NontextPolicy):
        def __init__(self, *args: Any) -> None:
            super().__init__(*args)
            objects.append(self)
    monkeypatch.setattr(transcript, "NontextPolicy", Recording)
    return objects


@pytest.fixture
def nontext_calls(monkeypatch) -> list[tuple[str, object]]:
    """The nontext argument of every scan_candidates and select_text call the CLI makes."""
    calls: list[tuple[str, object]] = []
    scan, select = transcript.scan_candidates, transcript.select_text

    def spy_scan(*args: Any, **kwargs: Any):
        calls.append(("scan", kwargs.get("nontext", "ABSENT")))
        return scan(*args, **kwargs)

    def spy_select(*args: Any, **kwargs: Any):
        calls.append(("select", kwargs.get("nontext", "ABSENT")))
        return select(*args, **kwargs)
    monkeypatch.setattr(transcript, "scan_candidates", spy_scan)
    monkeypatch.setattr(transcript, "select_text", spy_select)
    return calls


def place(exc: transcript.FormatViolation) -> tuple[Any, ...]:
    return (exc.check_id, exc.field_path, exc.expected, exc.actual_json_type, exc.block_index, exc.item_index,
            exc.line)


# ------------------------------------------------------------------------------ the profile itself


def test_v2_profile_definition():
    v1 = profiles.PROFILES[V1]
    assert (V2_PROFILE.id, V2_PROFILE.version, V2_PROFILE.skip_marker_free_nontext) == (V2, 2, True)
    assert (V2_PROFILE.begin, V2_PROFILE.end, V2_PROFILE.kinds, V2_PROFILE.trim_empty_edges) == (
        v1.begin, v1.end, v1.kinds, v1.trim_empty_edges)
    assert v1.skip_marker_free_nontext is False and profiles.PROFILES[PREREG].skip_marker_free_nontext is False
    assert grammar.valid_profile(V2) and not grammar.valid_profile("ECON-FWD-M20-WO/3")
    assert (transcript.NONTEXT_DEPTH_LIMIT, transcript.NONTEXT_ITEM_NODE_LIMIT, transcript.NONTEXT_CALL_NODE_LIMIT,
            transcript.NONTEXT_CHECK_INTERVAL) == (64, 100_000, 2_000_000, 1024)


# ------------------------------------------------------------------------------ T1: /1 preserved


@pytest.mark.parametrize("profile", [V1, PREREG])
def test_t1_v1_and_prereg_direct_calls_are_unchanged(tmp_path, profile):
    prefix = NOISE + entry(tr([TEXT_A, nt()]))
    prof = profiles.PROFILES[profile]
    expected = ("S4d", "tool_result.content[].type", "text_literal", "string_unlisted", 1, 2, 2)
    places = []
    for kwargs in ({}, {"nontext": None}):
        with pytest.raises(transcript.FormatViolation) as err:
            transcript.scan_candidates(prefix, prof.kinds, lambda t: profiles.marker_line_present(prof, t),
                                       transcript.Deadline(), **kwargs)
        places.append(place(err.value))
        with pytest.raises(transcript.FormatViolation) as err:
            transcript.select_text(prefix, grammar.parse_selector(f"tool_result:{TID}:text:1"),
                                   transcript.Deadline(), **kwargs)
        assert err.value.code == FU and err.value.item_index == 2
    assert places == [expected, expected]
    assert cli._nontext(prof, transcript.Deadline()) == {}  # the CLI calls exactly as before
    made_v2 = cli._nontext(V2_PROFILE, transcript.Deadline())
    assert set(made_v2) == {"nontext"} and isinstance(made_v2["nontext"], transcript.NontextPolicy)


@pytest.mark.parametrize("profile", [V1, PREREG])
def test_t1_v1_and_prereg_documents_are_unchanged(tmp_path, root, call, nontext_calls, profile):
    home = make_home(tmp_path, [NOISE, entry(tr([TEXT_A, nt()]))])
    doc = call(root, home, diagnose_args(home, profile))
    assert doc["status"] == "DIAGNOSE_VIOLATION_FOUND"
    assert doc["violation"] == viol("S4d", "tool_result.content[].type", "text_literal", "string_unlisted", 1, 2, 2)
    assert doc["profile"] == {"id": profile, "version": 1}
    doc = call(root, home, precheck_args(profile))
    assert (doc["status"], doc["checks"]["scan"], doc["candidate_count"]) == (FU, "FAILED", None)
    doc = call(root, home, run_args(f"tool_result:{TID}:text:1", profile))
    assert (doc["status"], doc["values"]) == (FU, None)
    assert [kind for kind, _ in nontext_calls] == ["scan", "scan", "select"]
    assert all(value == "ABSENT" for _, value in nontext_calls)  # the keyword is not even passed


# ------------------------------------------------------------------------------ T2: order


def test_t2_scan_and_run_use_the_same_text_index(tmp_path, root, call):
    content = [nt(), TEXT_A, nt(), TEXT_B]
    prefix = NOISE + entry(tr(content))
    found = transcript.scan_candidates(prefix, V2_PROFILE.kinds, is_candidate, transcript.Deadline(),
                                       nontext=policy())
    assert found == [transcript.Candidate("tool_result", TID, 1, False),
                     transcript.Candidate("tool_result", TID, 2, False)]
    for k, text in ((1, TEXT_A["text"]), (2, TEXT_B["text"])):  # never joined
        assert transcript.select_text(prefix, grammar.parse_selector(f"tool_result:{TID}:text:{k}"),
                                      transcript.Deadline(), nontext=policy()) == text
    home = make_home(tmp_path, [NOISE, entry(tr(content))])
    first = call(root, home, run_args(f"tool_result:{TID}:text:1", attempt="001"))
    second = call(root, home, run_args(f"tool_result:{TID}:text:2", attempt="002"))
    assert (first["status"], first["values"]) == ("SUCCEEDED", vals(BODY_A))
    assert (second["status"], second["values"]) == ("SUCCEEDED", vals(BODY_B))
    assert first["profile"] == {"id": V2, "version": 2}
    third = call(root, home, run_args(f"tool_result:{TID}:text:3", attempt="003"))
    assert third["status"] == "TEXT_BLOCK_NOT_FOUND"


# ------------------------------------------------------------------------------ T3: S4e


@pytest.mark.parametrize("item", [
    nt(a={"b": ["x", f"pre {WB} post"]}),  # nested string value
    nt(a={f"k{WE}": 1}),  # object key
    nt(a=[1, None, WB]),  # array element
    {"type": LEAK_TYPE, WE: "x"},  # key of the root
    nt(a=WB + WE),
    deep(64, {"v": f"x{WE}"}),  # a string in a container at depth 64
    deep(64, {f"{WB}": 1}),
], ids=["nested-value", "key", "array-element", "root-key", "both", "depth-64-value", "depth-64-key"])
def test_t3_a_whole_marker_is_s4e(item):
    assert check_id_of(item) == "S4e"


@pytest.mark.parametrize("item", [
    nt(a=WB[:-1]), nt(a=WE[1:]),  # part of a marker
    nt(a=["-----BEGIN ECON-FWD-M20", " WORK ORDER CANDIDATE-----"]),  # split over two strings
    nt(a={"-----BEGIN ECON-FWD-M20": " WORK ORDER CANDIDATE-----"}),  # split over a key and its value
    nt(a=base64.b64encode(WB.encode("ascii")).decode("ascii")),  # base64
    nt(a=WB.replace("B", "\\u0042")),  # a double escape (backslash-u text after parsing)
    nt(a=WB.lower()), nt(a=[1, 2.5, True, None]),  # other case, non-strings
], ids=["prefix", "suffix", "split-strings", "split-key-value", "base64", "double-escape", "lower", "scalars"])
def test_t3_limits_are_fixed_these_are_not_detected(item):
    assert check_id_of(item) is None


def test_t3_s4e_location(tmp_path, root, call):
    bad = entry({"type": "text", "text": "LEAKTOKEN-NT-USER-1f2e"}, tr([PLAIN, nt(a={"b": f"x{WE}"})]))
    home = make_home(tmp_path, [NOISE, NOISE, bad])
    doc = call(root, home, diagnose_args(home))
    assert doc["status"] == "DIAGNOSE_VIOLATION_FOUND" and doc["violation"] == s4e(2, 2, 3)
    assert doc["profile"] == {"id": V2, "version": 2} and doc["target"]["prefix_check"] == "MATCHED"
    doc = call(root, home, precheck_args())
    assert (doc["status"], doc["checks"]["scan"]) == (FU, "FAILED")


def test_t3_a_json_escaped_marker_is_detected_after_parsing(tmp_path, root, call):
    raw = entry(tr([PLAIN, nt(a=WB)])).replace(b"BEGIN", b"\\u0042EGIN")
    assert WB.encode("ascii") not in raw
    home = make_home(tmp_path, [NOISE, raw])
    assert call(root, home, diagnose_args(home))["violation"] == s4e(1, 2, 2)


def test_t3_the_first_violation_is_reported(tmp_path, root, call):
    bad = entry(tr([nt(), nt(a=WB), nt(a=deep(70))]), tr([nt(a=WE)], TID2))
    home = make_home(tmp_path, [NOISE, bad, entry(tr([nt(a=WB)]))])
    assert call(root, home, diagnose_args(home))["violation"] == s4e(1, 2, 2)


# ------------------------------------------------------------------------------ T4: S4f and the scan


def test_t4_depth_limit():
    assert check_id_of(deep(64)) is None
    assert check_id_of(deep(65)) == "S4f"
    assert check_id_of(nt(a=deep(63))) is None  # root 1, "a" 2, its chain ends at 64
    assert check_id_of(nt(a=deep(64))) == "S4f"
    lists: Any = "x"
    for _ in range(63):
        lists = [lists]
    assert check_id_of({"type": LEAK_TYPE, "a": lists}) is None  # 63 arrays below the root: depth 64
    assert check_id_of({"type": LEAK_TYPE, "a": [lists]}) == "S4f"


def test_t4_keys_and_scalars_do_not_add_depth():
    leaf = {"v": "x", "n": 1, "f": 1.5, "z": None, "b": True, "s": "LEAKTOKEN-NT-LEAF-33aa"}
    assert check_id_of(deep(64, leaf)) is None
    assert check_id_of(deep(64, {**leaf, "a": []})) == "S4f"  # an empty array is still a container


def test_t4_item_node_limit():
    # root 1 + "type" key and value 2 + "a" key and value 2 = 5 nodes, then one per element
    assert check_id_of({"type": LEAK_TYPE, "a": [0] * 99_995}) is None  # 100000 nodes
    assert check_id_of({"type": LEAK_TYPE, "a": [0] * 99_996}) == "S4f"  # 100001 nodes
    pol = policy()
    pol.check({"type": LEAK_TYPE, "a": [0] * 99_995}, 1)
    assert pol.item_nodes == 100_000


def test_t4_call_node_limit(monkeypatch):
    monkeypatch.setattr(transcript, "NONTEXT_ITEM_NODE_LIMIT", 10)
    monkeypatch.setattr(transcript, "NONTEXT_CALL_NODE_LIMIT", 25)
    pol = policy()
    pol.check({"type": LEAK_TYPE, "a": [0] * 5}, 1)  # 10
    pol.check({"type": LEAK_TYPE, "a": [0] * 5}, 2)  # 20
    pol.check({"type": LEAK_TYPE, "a": []}, 3)  # 25: the sum may equal the limit
    assert pol.call_nodes == 25
    assert check_id_of({"type": LEAK_TYPE}, pol) == "S4f"  # the 26th node
    assert check_id_of({"type": LEAK_TYPE}) is None  # a new policy starts at 0
    assert check_id_of({"type": LEAK_TYPE, "a": [0] * 6}) == "S4f"  # the item limit holds alone


def test_t4_call_node_limit_through_the_text_list(monkeypatch):
    monkeypatch.setattr(transcript, "NONTEXT_CALL_NODE_LIMIT", 12)
    block = tr([nt(), PLAIN, nt(), nt()])  # 5 + 5 + 5 nodes
    with pytest.raises(transcript.FormatViolation) as err:
        transcript._tool_result_content_texts(block, nontext=policy())
    assert (err.value.check_id, err.value.item_index) == ("S4f", 4)
    assert transcript._tool_result_content_texts(tr([nt(), PLAIN, nt()]), nontext=policy()) == [PLAIN["text"]]


class CountingList(list):
    """An array that counts the elements taken from its iterator."""

    taken = 0

    def __iter__(self):
        for value in list.__iter__(self):
            self.taken += 1
            yield value


class CountingDict(dict):
    """An object that counts the pairs taken from items()."""

    taken = 0

    def items(self):  # type: ignore[override]
        for pair in dict.items(self):
            self.taken += 1
            yield pair


def test_t4_no_child_is_taken_after_a_limit_or_a_marker(monkeypatch):
    monkeypatch.setattr(transcript, "NONTEXT_ITEM_NODE_LIMIT", 10)
    elements = CountingList(range(20))
    assert check_id_of({"type": LEAK_TYPE, "a": elements}) == "S4f"
    assert elements.taken == 6  # node 11 is the sixth element
    root_object = CountingDict({"type": LEAK_TYPE, **{f"k{i}": i for i in range(20)}})
    assert check_id_of(root_object) == "S4f"
    assert root_object.taken == 5  # node 11 is the value of the fifth pair
    marked = CountingList(["x", WB, "y", "z"])
    assert check_id_of({"type": LEAK_TYPE, "a": marked}) == "S4e"
    assert marked.taken == 2
    too_deep = CountingList([[1], "y", "z"])
    monkeypatch.setattr(transcript, "NONTEXT_DEPTH_LIMIT", 2)
    assert check_id_of({"type": LEAK_TYPE, "a": too_deep}) == "S4f"
    assert too_deep.taken == 1


def test_t4_deep_input_has_no_recursion_error(tmp_path, root, call):
    assert check_id_of(deep(64)) is None
    home = make_home(tmp_path, [NOISE, entry(tr([TEXT_A, deep(64)]))])
    assert call(root, home, diagnose_args(home))["status"] == "DIAGNOSE_NO_VIOLATION"
    home = make_home(tmp_path, [NOISE, entry(tr([TEXT_A, deep(65)]))], "home65")
    assert call(root, home, diagnose_args(home))["violation"] == s4f(1, 2, 2)


# ------------------------------------------------------------------------------ T5: Deadline


class RecordingDeadline:
    """A Deadline seam: records the policy's item node count at every check and expires after `allow` checks."""

    def __init__(self, allow: int = 10**9) -> None:
        self.allow = allow
        self.at: list[int] = []
        self.policy: transcript.NontextPolicy | None = None

    def check(self) -> None:
        assert self.policy is not None
        self.at.append(self.policy.item_nodes)
        if len(self.at) > self.allow:
            raise ControlledReadError("TIME_LIMIT_EXCEEDED")


def test_t5_the_deadline_is_checked_before_the_root_and_every_1024_nodes():
    dl = RecordingDeadline()
    pol = dl.policy = policy(dl)
    pol.check({"type": LEAK_TYPE, "a": [0] * 5000}, 1)  # 5005 nodes
    assert dl.at == [0, 1024, 2048, 3072, 4096]
    dl.at.clear()
    pol.check({"type": LEAK_TYPE, "a": [0] * 1019}, 2)  # 1024 nodes: only the root check
    assert dl.at == [5005]  # checked before the counter of the new item is reset


def test_t5_expiry_during_the_scan_is_time_limit_exceeded():
    dl = RecordingDeadline(allow=2)
    pol = dl.policy = policy(dl)
    with pytest.raises(ControlledReadError) as err:
        pol.check({"type": LEAK_TYPE, "a": [0] * 5000}, 1)
    assert err.value.code == "TIME_LIMIT_EXCEEDED" and not isinstance(err.value, transcript.FormatViolation)
    assert dl.at == [0, 1024, 2048]


@pytest.fixture
def expire_in_scan(monkeypatch, clock):
    """The caller's Deadline expires when the policy starts on an item."""
    original = transcript.NontextPolicy.check

    def expiring(self, item, item_index):
        clock.now += 1000.0
        return original(self, item, item_index)
    monkeypatch.setattr(transcript.NontextPolicy, "check", expiring)


def test_t5_precheck_and_diagnose_are_incomplete_without_rehash(tmp_path, root, call, expire_in_scan,
                                                                  rehash_calls):
    home = make_home(tmp_path, [NOISE, entry(tr([TEXT_A, nt()]))])
    doc = call(root, home, precheck_args())
    assert (doc["status"], doc["checks"]["scan"], doc["target"]["prefix_check"]) == (
        "TIME_LIMIT_EXCEEDED", "FAILED", "INCOMPLETE")
    doc = call(root, home, diagnose_args(home))
    assert (doc["status"], doc["checks"], doc["target"]["prefix_check"], doc["violation"]) == (
        "TIME_LIMIT_EXCEEDED", {"prefix": "PASSED", "scan": "FAILED"}, "INCOMPLETE", None)
    assert rehash_calls == []


def test_t5_run_keeps_its_time_limit_handling(tmp_path, root, call, expire_in_scan, rehash_calls):
    home = make_home(tmp_path, [NOISE, entry(tr([TEXT_A, nt()]))])
    doc = call(root, home, run_args(f"tool_result:{TID}:text:1"))
    assert (doc["status"], doc["values"], doc["target"]["prefix_check"]) == (
        "TIME_LIMIT_EXCEEDED", None, "INCOMPLETE")
    assert rehash_calls == []


# ------------------------------------------------------------------------------ T6: no shared state


def test_t6_each_call_gets_a_new_policy(tmp_path, root, call, made):
    eight = {"type": LEAK_TYPE, "a": [1, 2, 3]}  # 8 nodes
    home = make_home(tmp_path, [NOISE, entry(tr([TEXT_A, nt()]), tr([PLAIN, eight], TID2))])
    for _ in range(2):
        assert call(root, home, precheck_args())["status"] == "PRECHECK_OK"
    assert [p.call_nodes for p in made] == [13, 5, 13, 5]  # scan: both blocks; selected check: one block
    assert len({id(p) for p in made}) == 4
    assert call(root, home, diagnose_args(home))["status"] == "DIAGNOSE_NO_VIOLATION"
    assert call(root, home, run_args(f"tool_result:{TID}:text:1"))["status"] == "SUCCEEDED"
    assert [p.call_nodes for p in made[4:]] == [13, 5]
    assert len({id(p) for p in made}) == 6


def test_t6_counters_do_not_carry_over_between_direct_calls(monkeypatch):
    monkeypatch.setattr(transcript, "NONTEXT_CALL_NODE_LIMIT", 12)
    prefix = NOISE + entry(tr([TEXT_A, nt(), nt()]))  # 10 nodes per call
    for _ in range(3):
        pol = policy()
        transcript.scan_candidates(prefix, V2_PROFILE.kinds, is_candidate, transcript.Deadline(), nontext=pol)
        assert pol.call_nodes == 10
    pol = policy()
    transcript.scan_candidates(prefix, V2_PROFILE.kinds, is_candidate, transcript.Deadline(), nontext=pol)
    with pytest.raises(transcript.FormatViolation) as err:  # the same object again: 20 > 12
        transcript.scan_candidates(prefix, V2_PROFILE.kinds, is_candidate, transcript.Deadline(), nontext=pol)
    assert err.value.check_id == "S4f"


# ------------------------------------------------------------------------------ T7: S4d kept


@pytest.mark.parametrize("content, v", [
    ([PLAIN, "LEAKTOKEN-NT-STRING-ITEM-6c1d"], ("tool_result.content[]", "object", "string")),
    ([PLAIN, 5], ("tool_result.content[]", "object", "number")),
    ([nt(), [LEAK_TYPE]], ("tool_result.content[]", "object", "array")),
    ([PLAIN, {"type": 5}], ("tool_result.content[].type", "text_literal", "number")),
    ([nt(), {"type": None}], ("tool_result.content[].type", "text_literal", "null")),
    ([PLAIN, {"type": [LEAK_TYPE]}], ("tool_result.content[].type", "text_literal", "array")),
    ([nt(), {LEAK_KEY: "x"}], ("tool_result.content[].type", "text_literal", "missing")),
    ([PLAIN, {"type": "text", "text": 5}], ("tool_result.content[].text", "string", "number")),
    ([nt(), {"type": "text"}], ("tool_result.content[].text", "string", "missing")),
], ids=["string", "number", "array", "type-number", "type-null", "type-array", "type-missing", "text-number",
        "text-missing"])
def test_t7_s4d_is_kept_under_v2(tmp_path, root, call, content, v):
    home = make_home(tmp_path, [NOISE, NOISE, entry(tr(content))])
    assert call(root, home, diagnose_args(home))["violation"] == viol("S4d", *v, 1, 2, 3)


# ------------------------------------------------------------------------------ T8: uniqueness scope


def test_t8_one_candidate_and_a_marked_non_text_item_is_format_unsupported(tmp_path, root, call):
    home = make_home(tmp_path, [NOISE, entry(tr([TEXT_A]), tr([nt(a=WE)], TID2))])
    doc = call(root, home, precheck_args())
    assert (doc["status"], doc["checks"], doc["candidate_count"]) == (
        FU, {"scan": "FAILED", "selected": "NOT_REACHED"}, None)


def test_t8_two_candidates_are_multiple(tmp_path, root, call):
    home = make_home(tmp_path, [NOISE, entry(tr([TEXT_A, nt(), TEXT_B]))])
    doc = call(root, home, precheck_args())
    assert (doc["status"], doc["candidate_count"], doc["selector"]) == ("PRECHECK_MULTIPLE_CANDIDATES", 2, None)


def test_t8_one_candidate_and_a_marker_free_non_text_item_is_ok(tmp_path, root, call):
    home = make_home(tmp_path, [NOISE, entry(tr([nt(), TEXT_A, nt(a={"b": [1, "x"]})]))])
    doc = call(root, home, precheck_args())
    assert (doc["status"], doc["candidate_count"], doc["selector"], doc["values"]) == (
        "PRECHECK_OK", 1, f"tool_result:{TID}:text:1", vals(BODY_A))
    assert doc["checks"] == {"scan": "PASSED", "selected": "PASSED"}
    assert doc["profile"] == {"id": V2, "version": 2}
    assert call(root, home, precheck_args(V1))["status"] == FU  # /1 keeps S4d for the same session


# ------------------------------------------------------------------------------ T9: no leak


@pytest.mark.parametrize("item", [
    nt(u=LEAK_NONASCII, v={LEAK_NONASCII: [LEAK_VALUE]}),  # skipped
    nt(u=LEAK_NONASCII, v=f"{LEAK_NONASCII}{WB}"),  # S4e
    {**deep(65), LEAK_KEY: LEAK_NONASCII},  # S4f
], ids=["skip", "s4e", "s4f"])
def test_t9_no_type_name_key_value_or_body_is_output(tmp_path, root, call, item):
    raw = entry(tr([TEXT_A, item]))
    assert b"\\u00e9" in raw  # json.dumps escapes the non-ASCII input
    home = make_home(tmp_path, [NOISE, raw])
    for args in (diagnose_args(home), precheck_args(), run_args(f"tool_result:{TID}:text:1")):
        call(root, home, args)  # `call` asserts no LEAK marker and no non-ASCII bytes on stdout, empty stderr
    try:
        policy().check(item, 1)
    except transcript.FormatViolation as exc:
        assert "LEAKTOKEN" not in repr(exc.args) + str(exc) + repr(vars(exc))


# ------------------------------------------------------------------------------ T10: diagnose /2


def test_t10_s4e_and_s4f_objects(tmp_path, root, call):
    home = make_home(tmp_path, [NOISE, entry(tr([PLAIN, PLAIN, nt(a=[WB])]))])
    assert call(root, home, diagnose_args(home))["violation"] == {
        "check_id": "S4e", "applicability": "SELECTED_ENTRY_ONLY", "field_path": "tool_result.content[]",
        "expected": "marker_free_nontext", "actual_json_type": "object", "block_index": 1, "item_index": 3,
        "line": 2}
    home = make_home(tmp_path, [NOISE, NOISE, entry(tr([PLAIN]), tr([deep(65)], TID2))], "home2")
    assert call(root, home, diagnose_args(home))["violation"] == {
        "check_id": "S4f", "applicability": "SELECTED_ENTRY_ONLY", "field_path": "tool_result.content[]",
        "expected": "within_nontext_scan_limits", "actual_json_type": "object", "block_index": 2,
        "item_index": 1, "line": 3}


@pytest.mark.parametrize("make", [s4e, s4f])
@pytest.mark.parametrize("change", [
    {"expected": "object"}, {"expected": "marker_free"}, {"field_path": "tool_result.content[].type"},
    {"actual_json_type": "string_unlisted"}, {"actual_json_type": "other"}, {"applicability": "GLOBAL"},
    {"block_index": None}, {"block_index": 0}, {"item_index": None}, {"item_index": 0}, {"line": None},
    {"check_id": "S4g"},
], ids=lambda c: next(iter(c)) + "=" + str(next(iter(c.values()))))
def test_t10_other_values_are_value_errors(make, change):
    good = make(1, 1, 1)
    diagnose.check_violation(good)
    with pytest.raises(ValueError):
        diagnose.check_violation({**good, **change})


def test_t10_run_and_precheck_codes_are_format_unsupported(tmp_path, root, call):
    home = make_home(tmp_path, [NOISE, entry(tr([TEXT_A, nt(a=WE)]))])
    assert call(root, home, run_args(f"tool_result:{TID}:text:1"))["status"] == FU
    home = make_home(tmp_path, [NOISE, entry(tr([TEXT_A, deep(65)]))], "home2")
    assert call(root, home, run_args(f"tool_result:{TID}:text:1", attempt="002"))["status"] == FU
    assert call(root, home, precheck_args())["status"] == FU
