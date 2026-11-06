"""Research gate report conformance validator: T01–T29 of the QUALITY-GATES-02 TEST_GATES.

Every profile and report is synthetic and built in code; no real study value, BT4 result or fixture file is used.
Levels and hypothesis ids are deliberately unlike any preregistered value. run() also checks, for every call, that
each message comes from MESSAGES (T24) and that no input produces QG-X01 (T29a)."""

from __future__ import annotations

import ast
import copy
import itertools
import json
import math
import re
import threading
from collections.abc import Mapping
from pathlib import Path

import pytest

from moneylab.research import report_conformance as rc
from moneylab.research import report_schema
from moneylab.research.report_conformance import Problem, Result, check_report
from moneylab.research.report_schema import MESSAGES, PROFILE_SCHEMA, REPORT_SCHEMA, RESULT_SCHEMA

SENTINEL = "ZZQ-SENTINEL-4F1B"
IDS = ("H-A", "H-B", "H-C", "H-D", "H-E")
# DC13, written out independently of report_schema.
ALL_CODES = ("QG-T01", "QG-X01", "QG-P01", "QG-A01", "QG-A02", "QG-A03", "QG-A04", "QG-B01", "QG-B02", "QG-B03",
             "QG-B04", "QG-C01", "QG-C02", "QG-C03", "QG-C04", "QG-D01", "QG-D02", "QG-D03", "QG-E01", "QG-E02",
             "QG-E03", "QG-E04", "QG-F01", "QG-F02", "QG-F03", "QG-G01", "QG-G02", "QG-G03", "QG-H01", "QG-H02",
             "QG-I01", "QG-J01")
ALLOWED_IMPORTS = {"dataclasses", "decimal", "json", "re", "collections.abc", "typing",
                   "moneylab.research.report_schema"}


def profile() -> dict:
    return {"schema": PROFILE_SCHEMA, "study_id": "SYNTH-STUDY", "hypothesis_ids": list(IDS),
            "required_hypothesis_fields": ["effect", "uncertainty", "p_value"],
            "labels": ["SUPPORTED", "WEAKENED", "INCONCLUSIVE"], "reason_codes": ["R_ALPHA", "R_BETA"],
            "evidence_grade": "SYNTHETIC / NOT_EVIDENCE",
            "required_sections": ["labels_table", "multiplicity_rules", "evidence_note"],
            "multiplicity": {"SUPPORTED": {"method": "HOLM", "fwer": "0.03"},
                             "WEAKENED": {"method": "BONFERRONI", "fwer": "0.02", "per_hypothesis": "0.004"},
                             "union_bound": "0.05",
                             "special": {"H-D": {"components": {"gamma_one": "0.001", "gamma_two": "0.003"}}}},
            "forbidden_terms": ["VALIDATED", "calibrated"]}


def hypothesis(hid: str, label: str = "SUPPORTED", reason: str | None = None) -> dict:
    return {"id": hid, "label": label, "reason": reason, "effect": 101.5, "uncertainty": [100.25, 102.75],
            "p_value": 0.777}


def report() -> dict:
    return {"schema": REPORT_SCHEMA, "study_id": "SYNTH-STUDY", "evidence_grade": "SYNTHETIC / NOT_EVIDENCE",
            "sections": ["labels_table", "multiplicity_rules", "evidence_note"],
            "hypotheses": [hypothesis("H-A"), hypothesis("H-B", "WEAKENED"),
                           hypothesis("H-C", "INCONCLUSIVE", "R_ALPHA"), hypothesis("H-D", "WEAKENED"),
                           hypothesis("H-E")],
            "multiplicity": copy.deepcopy(profile()["multiplicity"])}


def run(rep: dict, prof: dict | None = None) -> Result:
    result = check_report(rep, profile() if prof is None else prof)
    for p in result.problems:
        assert p.message == MESSAGES[p.code]
        assert p.code != "QG-X01"
    assert result.ok is (not result.problems)
    assert result.exit_code == (0 if result.ok else 1)
    return result


def found(result: Result) -> list[tuple[str, str]]:
    return [(p.code, p.where) for p in result.problems]


def nest(depth: int) -> list:
    inner: list = []
    for _ in range(depth - 1):
        inner = [inner]
    return inner


# --- T01–T08: valid report, multiplicity families, union bound, special rules, profile consistency ---

def test_t01_valid_report_passes():
    result = run(report())
    assert result.ok and result.exit_code == 0 and result.problems == ()
    assert result.to_dict() == {"schema": RESULT_SCHEMA, "ok": True, "exit_code": 0, "problems": []}


def test_t02_missing_weakened_family():
    rep = report()
    del rep["multiplicity"]["WEAKENED"]
    assert found(run(rep)) == [("QG-E01", "multiplicity.WEAKENED")]


def test_t03_supported_family_method_and_holm_level():
    rep = report()
    del rep["multiplicity"]["SUPPORTED"]
    assert found(run(rep)) == [("QG-D01", "multiplicity.SUPPORTED")]
    rep = report()
    rep["multiplicity"]["SUPPORTED"]["method"] = "BONFERRONI"
    assert found(run(rep)) == [("QG-D02", "multiplicity.SUPPORTED.method")]
    rep = report()
    rep["multiplicity"]["SUPPORTED"]["fwer"] = "0.04"
    assert found(run(rep)) == [("QG-D03", "multiplicity.SUPPORTED.fwer")]


def test_t04_bonferroni_per_hypothesis_and_weakened_fwer():
    rep = report()
    rep["multiplicity"]["WEAKENED"]["per_hypothesis"] = "0.005"
    assert found(run(rep)) == [("QG-E04", "multiplicity.WEAKENED.per_hypothesis")]
    rep = report()
    rep["multiplicity"]["WEAKENED"]["fwer"] = "0.03"
    assert found(run(rep)) == [("QG-E03", "multiplicity.WEAKENED.fwer")]


def test_t05_weakened_method_mismatch():
    rep = report()
    rep["multiplicity"]["WEAKENED"]["method"] = "HOLM"
    assert found(run(rep)) == [("QG-E02", "multiplicity.WEAKENED.method")]


def test_t06_union_bound_missing_and_mismatch():
    rep = report()
    del rep["multiplicity"]["union_bound"]
    assert found(run(rep)) == [("QG-F01", "multiplicity.union_bound")]
    rep = report()
    rep["multiplicity"]["union_bound"] = "0.06"
    assert found(run(rep)) == [("QG-F02", "multiplicity.union_bound")]


def test_t07_special_rule_missing_and_level_mismatch():
    rep = report()
    del rep["multiplicity"]["special"]["H-D"]
    assert found(run(rep)) == [("QG-G01", "multiplicity.special.H-D")]
    rep = report()
    del rep["multiplicity"]["special"]
    assert found(run(rep)) == [("QG-G01", "multiplicity.special.H-D")]
    rep = report()
    del rep["multiplicity"]["special"]["H-D"]["components"]["gamma_two"]
    assert found(run(rep)) == [("QG-G01", "multiplicity.special.H-D.components.gamma_two")]
    rep = report()
    rep["multiplicity"]["special"]["H-D"]["components"]["gamma_one"] = "0.002"
    assert found(run(rep)) == [("QG-G02", "multiplicity.special.H-D.components.gamma_one")]


def test_t08_inconsistent_profile_stops_before_report_checks():
    broken = report()
    del broken["evidence_grade"]
    del broken["multiplicity"]["WEAKENED"]
    prof = profile()
    prof["multiplicity"]["union_bound"] = "0.06"
    assert found(run(broken, prof)) == [("QG-F03", "profile.multiplicity.union_bound")]
    prof = profile()
    prof["multiplicity"]["special"]["H-D"]["components"]["gamma_one"] = "0.002"
    assert found(run(broken, prof)) == [("QG-G03", "profile.multiplicity.special.H-D")]


# --- T09–T15: hypotheses, fields, labels, evidence grade, forbidden terms, sections, schemas ---

def test_t09_hypothesis_count_missing_unknown_and_duplicate_ids():
    rep = report()
    rep["hypotheses"].pop()
    assert found(run(rep)) == [("QG-B01", "hypotheses"), ("QG-B02", "hypotheses.H-E")]
    rep = report()
    rep["hypotheses"][4]["id"] = SENTINEL
    result = run(rep)
    assert found(result) == [("QG-B02", "hypotheses.H-E"), ("QG-B03", "hypotheses[4].id")]
    assert SENTINEL not in result.to_json()
    rep = report()
    rep["hypotheses"][4]["id"] = "H-A"
    assert found(run(rep)) == [("QG-B02", "hypotheses.H-E"), ("QG-B04", "hypotheses[4].id")]


def test_t10_fields_labels_and_reasons():
    rep = report()
    del rep["hypotheses"][0]["reason"]
    del rep["hypotheses"][1]["effect"]
    assert found(run(rep)) == [("QG-C01", "hypotheses[0].reason"), ("QG-C01", "hypotheses[1].effect")]
    rep = report()
    rep["hypotheses"][0]["label"] = "MAYBE"
    assert found(run(rep)) == [("QG-C02", "hypotheses[0].label")]
    rep = report()
    rep["hypotheses"][2]["reason"] = None
    assert found(run(rep)) == [("QG-C03", "hypotheses[2].reason")]
    rep = report()
    rep["hypotheses"][2]["reason"] = "R_GAMMA"
    assert found(run(rep)) == [("QG-C04", "hypotheses[2].reason")]
    rep = report()
    rep["hypotheses"][0]["reason"] = "R_ALPHA"
    assert found(run(rep)) == [("QG-C04", "hypotheses[0].reason")]


def test_t11_evidence_grade_and_study_id():
    rep = report()
    del rep["evidence_grade"]
    assert found(run(rep)) == [("QG-H01", "evidence_grade")]
    rep = report()
    rep["evidence_grade"] = "SYNTHETIC"
    assert found(run(rep)) == [("QG-H02", "evidence_grade")]
    rep = report()
    rep["study_id"] = "OTHER-STUDY"
    assert found(run(rep)) == [("QG-A04", "study_id")]


@pytest.mark.parametrize(("value", "where"), [
    ({"comment": "the run is VALIDATED now"}, "hypotheses:forbidden_terms[0]"),
    (["see note", ["validated."]], "hypotheses:forbidden_terms[0]"),
    ("calibrated", "hypotheses:forbidden_terms[1]"),
    ({"calibrated": 1}, "hypotheses:forbidden_terms[1]"),
    ("VALIDATED-ish", "hypotheses:forbidden_terms[0]"),
])
def test_t12_forbidden_terms_are_found(value, where):
    rep = report()
    rep["hypotheses"][0]["note"] = value
    assert found(run(rep)) == [("QG-I01", where)]


def test_t12_forbidden_term_outside_known_sections():
    rep = report()
    rep["notes"] = "Validated"
    assert found(run(rep)) == [("QG-I01", "report:forbidden_terms[0]")]


@pytest.mark.parametrize("value", ["NOT_VALIDATED", "uncalibrated", "limitation: NOT_VALIDATED, uncalibrated"])
def test_t13_other_tokens_are_not_forbidden(value):
    rep = report()
    rep["hypotheses"][0]["note"] = value
    rep["notes"] = {value: value}
    assert run(rep).ok


def test_t14_required_section_missing():
    rep = report()
    rep["sections"].remove("evidence_note")
    assert found(run(rep)) == [("QG-J01", "sections.evidence_note")]


def test_t15_schemas_return_one_problem_and_stop():
    broken = report()
    del broken["evidence_grade"]
    rep = copy.deepcopy(broken)
    del rep["schema"]
    assert found(run(rep)) == [("QG-A01", "schema")]
    for schema in ("moneylab.research.gate_report/2", 7, None):
        rep = copy.deepcopy(broken)
        rep["schema"] = schema
        assert found(run(rep)) == [("QG-A02", "schema")]
    prof = profile()
    del prof["schema"]
    assert found(run(rep, prof)) == [("QG-A03", "profile.schema")]
    prof["schema"] = "moneylab.research.report_profile/9"
    assert found(run(broken, prof)) == [("QG-A03", "profile.schema")]


# --- T16–T23: types, arguments, determinism, ordering, immutability, non-disclosure, imports ---

@pytest.mark.parametrize("level", [0.03, 3, True, math.nan, None, ["0.03"]])
def test_t16_level_types(level):
    rep = report()
    rep["multiplicity"]["SUPPORTED"]["fwer"] = level
    assert found(run(rep)) == [("QG-T01", "multiplicity.SUPPORTED.fwer")]
    prof = profile()
    prof["multiplicity"]["union_bound"] = level
    assert found(run(report(), prof)) == [("QG-T01", "profile.multiplicity.union_bound")]


class _SubDict(dict):
    pass


@pytest.mark.parametrize("bad", [[SENTINEL], SENTINEL, None, (SENTINEL,), _SubDict(schema=SENTINEL)])
def test_t17_non_dict_argument_raises_type_error(bad):
    with pytest.raises(TypeError) as report_error:
        check_report(bad, profile())
    with pytest.raises(TypeError) as profile_error:
        check_report(report(), bad)
    for error in (report_error.value, profile_error.value):
        assert SENTINEL not in str(error) and SENTINEL not in repr(error)
        assert error.__cause__ is None and error.__context__ is None


def violating() -> dict:
    rep = report()
    rep["hypotheses"][1]["label"] = "MAYBE"
    rep["multiplicity"]["union_bound"] = "0.06"
    rep["sections"] = []
    rep["notes"] = "calibrated"
    return rep


def test_t18_deterministic_serialization():
    first, second = run(violating()).to_json(), run(violating()).to_json()
    assert first == second and first.endswith("\n") and "\n" not in first[:-1]
    reordered = dict(reversed(list(violating().items())))
    reordered["multiplicity"] = dict(reversed(list(reordered["multiplicity"].items())))
    assert run(reordered).to_json() == first
    assert json.loads(first) == run(violating()).to_dict()


def test_t19_problems_are_sorted_whatever_the_input_order():
    a = report()
    a["notes"] = "calibrated"
    a["hypotheses"][0]["label"] = "MAYBE"
    del a["evidence_grade"]
    b = {key: report()[key] for key in reversed(list(report()))}
    del b["evidence_grade"]
    b["hypotheses"][0]["label"] = "MAYBE"
    b["notes"] = "calibrated"
    ra, rb = run(a), run(b)
    assert ra.problems == rb.problems == tuple(sorted(ra.problems))
    assert Result((ra.problems[0], ra.problems[0])).problems == (ra.problems[0],)


def test_t20_inputs_are_not_modified():
    for rep, prof in ((report(), profile()), (violating(), profile()), (report(), {**profile(), "labels": []})):
        rep_before, prof_before = copy.deepcopy(rep), copy.deepcopy(prof)
        check_report(rep, prof)
        assert rep == rep_before and prof == prof_before


def test_t21_report_values_never_reach_the_output():
    rep = report()
    rep["hypotheses"][0]["effect"] = SENTINEL + "-EFFECT"
    rep["hypotheses"][1]["id"] = SENTINEL + "-ID"
    rep["hypotheses"][2]["label"] = SENTINEL + "-LABEL"
    rep["hypotheses"][3]["reason"] = SENTINEL + "-REASON"
    rep["hypotheses"][4][SENTINEL + "-FIELD"] = 1
    rep[SENTINEL + "-KEY"] = {SENTINEL + "-NESTED": SENTINEL}
    rep["multiplicity"]["SUPPORTED"]["method"] = SENTINEL + "-METHOD"
    rep["sections"].append(SENTINEL + "-SECTION")
    result = run(rep)
    assert not result.ok
    assert SENTINEL not in result.to_json() and SENTINEL not in json.dumps(result.to_dict())
    assert all(SENTINEL not in p.where and SENTINEL not in p.message for p in result.problems)


class _Trap:
    """Records and refuses every call; used to prove that no method of a foreign object is invoked."""
    calls: list[str] = []
    armed = False

    @classmethod
    def hit(cls, name: str) -> None:
        if cls.armed:
            cls.calls.append(name)
            raise RuntimeError(SENTINEL)


class _HostileMapping(Mapping):
    def __getitem__(self, key):
        _Trap.hit("getitem")

    def __iter__(self):
        _Trap.hit("iter")
        return iter(())

    def __len__(self):
        _Trap.hit("len")
        return 0

    def __eq__(self, other):
        _Trap.hit("eq")
        return False

    def __hash__(self):
        _Trap.hit("hash")
        return 1

    def __repr__(self):
        _Trap.hit("repr")
        return SENTINEL


class _HostileDict(dict):
    def __getitem__(self, key):
        _Trap.hit("dict.getitem")

    def __iter__(self):
        _Trap.hit("dict.iter")
        return iter(())

    def items(self):
        _Trap.hit("dict.items")
        return iter(())

    def get(self, key, default=None):
        _Trap.hit("dict.get")


class _HostileStr(str):
    def __eq__(self, other):
        _Trap.hit("str.eq")
        return False

    def __hash__(self):
        _Trap.hit("str.hash")
        return 1


class _HostileKey:
    def __hash__(self):
        return hash("schema")

    def __eq__(self, other):
        _Trap.hit("key.eq")
        return False


def hostile_cases() -> list[tuple[dict, str]]:
    cases = []
    rep = report()
    rep["hypotheses"][0] = _HostileDict(id="H-A", note=SENTINEL)
    cases.append((rep, "hypotheses[0]"))
    rep = report()
    rep["multiplicity"] = _HostileMapping()
    cases.append((rep, "multiplicity"))
    rep = report()
    rep["sections"] = tuple(rep["sections"])
    cases.append((rep, "sections"))
    rep = report()
    rep["hypotheses"] = "H-A,H-B,H-C,H-D,H-E"
    cases.append((rep, "hypotheses"))
    rep = report()
    rep["hypotheses"][0]["label"] = _HostileStr("SUPPORTED")
    cases.append((rep, "hypotheses[0].label"))
    rep = report()
    rep["hypotheses"][0][7] = SENTINEL
    cases.append((rep, "hypotheses"))
    rep = report()
    rep[_HostileKey()] = SENTINEL
    cases.append((rep, "report"))
    return cases


def test_t27_abnormal_containers_are_type_problems_without_calls():
    cases = hostile_cases()
    _Trap.calls, _Trap.armed = [], True
    try:
        for rep, where in cases:
            result = run(rep)
            assert ("QG-T01", where) in found(result)
            assert SENTINEL not in result.to_json()
        assert _Trap.calls == []
    finally:
        _Trap.armed = False


def test_t22_exception_and_problem_strings_hold_no_sentinel():
    with pytest.raises(TypeError) as error:
        check_report([SENTINEL], profile())
    assert SENTINEL not in str(error.value)
    cases = hostile_cases()
    _Trap.calls, _Trap.armed = [], True
    try:
        for rep, _ in cases:
            result = run(rep)
            assert all(SENTINEL not in p.code + p.where + p.message for p in result.problems)
    finally:
        _Trap.armed = False


def imported(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            names.add(node.module or "")
    return names


def test_t23_imports_stay_inside_dc1():
    for module in (rc, report_schema):
        assert imported(Path(module.__file__)) <= ALLOWED_IMPORTS


# --- T24–T29: message table, profile identifiers, canonical levels, containers, cycles, internal errors ---

def test_t24_message_table_covers_every_code():
    assert len(ALL_CODES) == len(set(ALL_CODES))
    assert set(MESSAGES) == set(ALL_CODES)
    assert all(message and message.isascii() for message in MESSAGES.values())
    for rep in (violating(), report()):
        for p in check_report(rep, profile()).problems:
            assert p.message == MESSAGES[p.code]


@pytest.mark.parametrize(("path", "value", "where"), [
    (("hypothesis_ids", 0), "1H", "profile.hypothesis_ids[0]"),
    (("hypothesis_ids", 0), "H.1", "profile.hypothesis_ids[0]"),
    (("required_sections", 0), "sec.one", "profile.required_sections[0]"),
    (("required_hypothesis_fields", 1), "0.25", "profile.required_hypothesis_fields[1]"),
    (("reason_codes", 0), "R ALPHA", "profile.reason_codes[0]"),
])
def test_t25_profile_identifiers(path, value, where):
    prof = profile()
    prof[path[0]][path[1]] = value
    broken = report()
    del broken["evidence_grade"]
    result = run(broken, prof)
    assert ("QG-P01", where) in found(result)
    assert {p.code for p in result.problems} <= {"QG-P01"}
    assert value not in result.to_json()


def test_t25_special_keys_must_be_declared_identifiers():
    prof = profile()
    prof["multiplicity"]["special"]["H.D"] = prof["multiplicity"]["special"].pop("H-D")
    assert found(run(report(), prof)) == [("QG-P01", "profile.multiplicity.special")]


@pytest.mark.parametrize("level", ["0.050", "1.0", ".05", "5E-2", "0.03\n", " 0.03", "0"])
def test_t26_non_canonical_levels(level):
    rep = report()
    rep["multiplicity"]["SUPPORTED"]["fwer"] = level
    assert found(run(rep)) == [("QG-T01", "multiplicity.SUPPORTED.fwer")]
    prof = profile()
    prof["multiplicity"]["WEAKENED"]["fwer"] = level
    assert found(run(report(), prof)) == [("QG-T01", "profile.multiplicity.WEAKENED.fwer")]


def test_t28_cycles_and_depth():
    rep = report()
    loop: dict = {}
    loop["self"] = loop
    rep["hypotheses"][0]["effect"] = loop
    assert found(run(rep)) == [("QG-T01", "hypotheses")]
    rep = report()
    ring: list = []
    ring.append(ring)
    rep["multiplicity"]["extra"] = ring
    assert found(run(rep)) == [("QG-T01", "multiplicity")]
    # report = depth 1, hypotheses = 2, hypotheses[0] = 3, so nest(n) there reaches depth 3 + n.
    rep = report()
    rep["hypotheses"][0]["uncertainty"] = nest(61)
    assert run(rep).ok
    rep = report()
    rep["hypotheses"][0]["uncertainty"] = nest(62)
    assert found(run(rep)) == [("QG-T01", "hypotheses")]
    rep = report()
    rep["hypotheses"][0]["uncertainty"] = nest(20000)
    assert found(run(rep)) == [("QG-T01", "hypotheses")]


# --- T28 (continued): shared references are not cycles (MC1–MC9) ---

def chain(levels: int, leaf: object) -> list:
    """levels nested lists; the innermost one holds leaf."""
    inner = [leaf]
    for _ in range(levels - 1):
        inner = [inner]
    return inner


def wrap(obj: object, levels: int) -> object:
    for _ in range(levels):
        obj = [obj]
    return obj


def depth_report(shallow_first: bool) -> dict:
    # hypotheses[i]["effect"] starts at depth 4. Shallow: shared innermost list at 33, its string is scanned. Deep:
    # 32 extra levels put that list at 65, so it is QG-T01 and its string is never reached on that path.
    shared = chain(30, "VALIDATED")
    rep = report()
    shallow, deep = (0, 1) if shallow_first else (1, 0)
    rep["hypotheses"][shallow]["effect"] = shared
    rep["hypotheses"][deep]["effect"] = wrap(shared, 32)
    return rep


def term_report() -> dict:
    shared = {"note": "VALIDATED"}
    rep = report()
    rep["hypotheses"][0]["effect"] = shared
    rep["multiplicity"]["extra"] = shared
    return rep


def shared_report() -> dict:
    empty: list = []
    across = {"k": [1, 2]}
    interval = [1.0, 2.0]
    rep = report()
    rep["hypotheses"][0]["effect"] = [empty, empty, [empty]]
    rep["hypotheses"][1]["effect"] = across
    rep["multiplicity"]["extra"] = across
    for item in rep["hypotheses"]:
        item["uncertainty"] = interval
    return rep


def doubling(levels: int, leaf: object) -> list:
    """A DAG of levels lists, each holding the next one twice: 2**(levels - 1) paths, levels distinct lists."""
    node = [leaf]
    for _ in range(levels - 1):
        node = [node, node]
    return node


def dag_report(levels: int) -> dict:
    rep = report()
    rep["hypotheses"][0]["effect"] = doubling(levels, "VALIDATED")
    return rep


@pytest.mark.parametrize("shallow_first", [True, False])
def test_t28_mc1_shared_object_at_two_depths(shallow_first):
    assert found(run(depth_report(shallow_first))) == [("QG-I01", "hypotheses:forbidden_terms[0]"),
                                                       ("QG-T01", "hypotheses")]
    rep = report()
    rep["hypotheses"][0]["effect"] = chain(30, "VALIDATED")
    assert found(run(rep)) == [("QG-I01", "hypotheses:forbidden_terms[0]")]


def test_t28_mc2_shared_object_reports_terms_in_every_section():
    assert found(run(term_report())) == [("QG-I01", "hypotheses:forbidden_terms[0]"),
                                         ("QG-I01", "multiplicity:forbidden_terms[0]")]


def test_t28_mc3_shared_references_without_a_cycle_pass():
    assert run(shared_report()).ok


def test_t28_mc4_real_cycles_are_type_problems():
    rep = report()
    first: list = []
    second = [first]
    first.append(second)
    rep["hypotheses"][0]["effect"] = first
    assert found(run(rep)) == [("QG-T01", "hypotheses")]
    rep = report()
    loop: list = []
    entry = [loop]
    loop.append(entry)
    rep["hypotheses"][0]["effect"] = [entry, [loop]]   # one cycle entered from two paths
    assert found(run(rep)) == [("QG-T01", "hypotheses")]
    rep = report()
    rep["multiplicity"]["extra"] = [rep]
    assert found(run(rep)) == [("QG-T01", "multiplicity")]
    rep = report()
    rep["appendix"] = {"back": rep}
    assert found(run(rep)) == [("QG-T01", "report")]


def test_t28_mc5_terms_inside_a_cycle_are_still_found():
    rep = report()
    first: list = []
    second = [first, "VALIDATED"]
    first.append(second)
    rep["hypotheses"][0]["effect"] = [first, second]
    assert found(run(rep)) == [("QG-I01", "hypotheses:forbidden_terms[0]"), ("QG-T01", "hypotheses")]


@pytest.mark.parametrize("build", [lambda: depth_report(True), lambda: depth_report(False), term_report,
                                   shared_report, lambda: dag_report(8)])
def test_t28_mc6_shared_input_matches_its_json_round_trip(build):
    rep = build()
    copied = json.loads(json.dumps(rep))
    assert run(rep).to_json() == run(copied).to_json()


def test_t28_mc7_shared_dag_is_not_walked_path_by_path():
    # Innermost list at depth 4 + 59 = 63. A path-by-path walk would take 2**59 steps.
    rep = dag_report(60)
    box: list = []
    worker = threading.Thread(target=lambda: box.append(check_report(rep, profile())), daemon=True)
    worker.start()
    worker.join(timeout=60)
    assert not worker.is_alive(), "the shared DAG was walked path by path"
    assert found(box[0]) == [("QG-I01", "hypotheses:forbidden_terms[0]")]


def path_oracle(root: dict, terms: tuple[str, ...], max_depth: int) -> set[tuple[str, str]]:
    """Independent reference for DC12/DC12a: walk every path, stop at a container already on the path or deeper
    than max_depth. Recursive, so only for small inputs."""
    out: set[tuple[str, str]] = set()
    folded = [term.casefold() for term in terms]

    def scan(text: str, section: str) -> None:
        for token in re.findall(r"[A-Za-z0-9_]+", text, flags=re.ASCII):
            out.update(("QG-I01", f"{section}:forbidden_terms[{i}]") for i, term in enumerate(folded)
                       if token.casefold() == term)

    def visit(obj: object, depth: int, section: str, path: tuple[int, ...]) -> None:
        if isinstance(obj, str):
            scan(obj, section)
        elif isinstance(obj, (list, dict)):
            if id(obj) in path or depth > max_depth:
                out.add(("QG-T01", section))
                return
            children = list(obj) if isinstance(obj, list) else list(obj.values())
            if isinstance(obj, dict):
                for key in obj:
                    scan(key, section)
            for child in children:
                visit(child, depth + 1, section, path + (id(obj),))

    for key, value in root.items():
        section = key if key in report_schema.REPORT_FIELDS else "report"
        scan(key, section)
        visit(value, 2, section, (id(root),))
    return out


def test_t28_mc8_walk_matches_a_path_by_path_oracle_on_every_small_graph(monkeypatch):
    # Three lists, each with at most two children chosen from the lists, a forbidden term and the root, shared by
    # three sections. A section value sits at depth 2, so with a depth limit of 3 the acyclic chain
    # nodes[0] -> nodes[1] -> nodes[2] already puts a container at depth 4: depth overflow without any cycle.
    monkeypatch.setattr(rc, "MAX_DEPTH", 3)
    terms = ("VALIDATED", "calibrated")
    nodes: list[list] = [[], [], []]
    root = {"hypotheses": nodes[0], "multiplicity": nodes[1], "appendix": nodes[2]}
    nodes[0].append(nodes[1])
    nodes[1].append(nodes[2])
    overflow = {("QG-T01", "hypotheses")}
    assert path_oracle(root, terms, 3) == overflow
    assert {(p.code, p.where) for p in rc._walk(root, report_schema.REPORT_FIELDS, "report", terms)} == overflow
    choices = [spec for size in range(3) for spec in itertools.product(range(5), repeat=size)]
    checked = 0
    for specs in itertools.product(choices, repeat=3):
        nodes: list[list] = [[], [], []]
        root = {"hypotheses": nodes[0], "multiplicity": nodes[1], "appendix": nodes[2]}
        for node, spec in zip(nodes, specs):
            node.extend(nodes[c] if c < 3 else ("calibrated" if c == 3 else root) for c in spec)
        got = {(p.code, p.where) for p in rc._walk(root, report_schema.REPORT_FIELDS, "report", terms)}
        assert got == path_oracle(root, terms, 3), specs
        checked += 1
    assert checked == 31 ** 3


def test_t28_mc9_profile_shares_references_and_still_rejects_cycles():
    prof = profile()
    codes = ["R_ALPHA", "R_BETA"]
    prof["reason_codes"] = codes
    prof["required_sections"] = codes
    rep = report()
    rep["sections"] = ["R_ALPHA", "R_BETA"]
    rep["multiplicity"] = prof["multiplicity"]   # shared between the two inputs as well
    assert run(rep, prof).ok
    prof = profile()
    loop: list = []
    loop.append(loop)
    prof["multiplicity"]["extra"] = loop
    assert found(run(report(), prof)) == [("QG-T01", "profile.multiplicity")]


def test_t29_internal_error_is_one_opaque_problem(monkeypatch):
    for rep, _ in hostile_cases():
        run(rep)

    def explode(*args, **kwargs):
        raise RuntimeError(SENTINEL)

    for name in ("_check_report_fields", "_parse_profile", "_walk"):
        with monkeypatch.context() as patch:
            patch.setattr(rc, name, explode)
            result = check_report(report(), profile())
        assert result.problems == (Problem("QG-X01", "check_report", MESSAGES["QG-X01"]),)
        assert not result.ok and result.exit_code == 1
        assert SENTINEL not in result.to_json()
