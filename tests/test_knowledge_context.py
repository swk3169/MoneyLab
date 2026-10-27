"""ContextRequest -> ContextPacket resolver (CONTEXT-ENGINE-02): request validation, filters, required records, modes,
sections, budget, provenance, trust and determinism, through the Python API and the `resolve-context` CLI.

Synthetic records are written to a throwaway git repository so sources verify against its HEAD; the last tests use
the repository's own seven seed records."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_knowledge_validate import git_repo, needs_git, record, write

from moneylab.knowledge import ContextRequestError, KnowledgeBase, load_records, open_knowledge_base, resolve_context
from moneylab.knowledge import validate as validate_records
from moneylab.knowledge.context import item_size
from moneylab.knowledge.model import canonical_json, record_path
from moneylab.knowledge.query import KnowledgeStateError

pytestmark = needs_git

REPO = Path(__file__).resolve().parents[1]
REQUEST = "moneylab.context.request/1"
SECTIONS = ["task_context", "decisions", "facts", "derived", "questions", "hypotheses"]
TOP_LEVEL = {"schema", "boundary", "trust_state", "request", *SECTIONS, "excluded", "truncation"}

FACT, SUMMARY, GUESS = "claim/TEST-01/fact", "claim/TEST-01/summary", "claim/TEST-01/guess"
OTHER_FACT = "claim/OTHER-01/fact"
OLD, NEW = "decision/TEST-01/v1", "decision/TEST-01/v2"
OPEN, ANSWERED, OTHER_OPEN = "question/TEST-01/open", "question/OTHER-01/answered", "question/OTHER-01/open-other"
TASK = "task/TEST-01/outcome"
# EVIDENCE selection order: section rank, then ID
EVIDENCE_ORDER = [TASK, NEW, OTHER_FACT, FACT, SUMMARY, ANSWERED, OTHER_OPEN, OPEN]


def synthetic_records():
    return [
        record(FACT, topics=["futility-calibration", "mc-v06"]),
        record(SUMMARY, layer="DERIVED_SUMMARY", derived_from=[FACT]),
        record(GUESS, layer="HYPOTHESIS", topics=["futility-calibration"]),
        record(OTHER_FACT, topics=["portfolio-demo"]),
        record(OLD), record(NEW, supersedes=[OLD]),
        record(OPEN), record(ANSWERED, payload={"state": "ANSWERED"}),
        record(OTHER_OPEN, topics=["portfolio-demo"]),
        record(TASK, topics=["portfolio-demo"]),
    ]


def make_repo(root: Path, records=None) -> Path:
    git_repo(root)
    for rec in synthetic_records() if records is None else records:
        write(root, rec)
    return root


@pytest.fixture(scope="module")
def repo(tmp_path_factory) -> Path:
    return make_repo(tmp_path_factory.mktemp("ctx"))


@pytest.fixture(scope="module")
def kb(repo) -> KnowledgeBase:
    knowledge, report = open_knowledge_base(repo)
    assert report.exit_code == 0 and knowledge.trusted
    return knowledge


def req(mode: str = "EVIDENCE", **fields) -> dict:
    return {"schema": REQUEST, "objective": "Summarize the evidence.", "mode": mode, **fields}


def ids(items) -> list[str]:
    return [i["id"] for i in items]


def sections(packet) -> dict[str, list[str]]:
    return {name: ids(packet[name]) for name in SECTIONS}


def selected(packet) -> set[str]:
    return {i for name in SECTIONS for i in ids(packet[name])}


def excluded(packet) -> list[tuple[str, str]]:
    return [(e["id"], e["reason"]) for e in packet["excluded"]]


def invalid(kb, request) -> ContextRequestError:
    with pytest.raises(ContextRequestError) as info:
        resolve_context(kb, request)
    assert info.value.code == "REQUEST_INVALID"
    return info.value


def run_cli(root: Path, stdin: bytes, cwd: Path | None = None, **env: str) -> subprocess.CompletedProcess[bytes]:
    full_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **env}
    return subprocess.run([sys.executable, "-m", "moneylab.knowledge", "--root", str(root), "resolve-context"],
                          input=stdin, env=full_env, cwd=cwd, capture_output=True, timeout=120)


def as_bytes(request) -> bytes:
    return json.dumps(request).encode("utf-8")


# --- request validation ----------------------------------------------------------------------------------

@pytest.mark.parametrize("missing", ["schema", "objective", "mode"])
def test_required_fields(kb, missing):
    request = req()
    del request[missing]
    assert "missing" in invalid(kb, request).detail


def test_request_must_be_an_object(kb):
    invalid(kb, [req()])


def test_unknown_top_level_field(kb):
    invalid(kb, req(current_only=True))


def test_unknown_budget_field(kb):
    invalid(kb, req(budget={"max_records": 5, "max_tokens": 100}))


@pytest.mark.parametrize("fields", [
    {"budget": {"max_records": True}}, {"budget": {"max_chars": False}}, {"include_open_questions": 1},
    {"include_open_questions": 0},
])
def test_bool_and_int_are_not_interchangeable(kb, fields):
    invalid(kb, req(**fields))


@pytest.mark.parametrize("fields", [
    {"schema": "moneylab.context.request/2"}, {"schema": "moneylab.knowledge.record/1"}, {"schema": 1},
    {"mode": "evidence"}, {"mode": "TRADING"}, {"mode": ["EVIDENCE"]}, {"objective": 5}, {"objective": None},
    {"topics": "mc-v06"}, {"topics": [1]}, {"topics": ["profitability"]}, {"kinds": ["note"]}, {"kinds": ["Claim"]},
    {"namespaces": ["test-01"]}, {"namespaces": ["-TEST"]}, {"namespaces": ["A" * 49]},
    {"include_ids": ["claim/TEST-01/Fact"]}, {"include_ids": ["note/TEST-01/fact"]},
    {"include_ids": [FACT + "\n"]}, {"include_ids": FACT}, {"budget": []}, {"budget": None},
    {"budget": {"max_chars": 1.5}}, {"budget": {"max_records": "5"}}, {"include_open_questions": "true"},
])
def test_invalid_types_and_enums(kb, fields):
    invalid(kb, req(**fields))


@pytest.mark.parametrize("field,value", [
    ("topics", ["mc-v06", "mc-v06"]), ("kinds", ["claim", "claim"]), ("namespaces", ["TEST-01", "TEST-01"]),
    ("include_ids", [FACT, FACT]),
])
def test_duplicate_list_values(kb, field, value):
    assert "duplicate" in invalid(kb, req(**{field: value})).detail


def test_objective_length(kb):
    invalid(kb, req(objective=""))
    invalid(kb, req(objective="x" * 2001))
    assert resolve_context(kb, req(objective="x" * 2000))["request"]["objective"] == "x" * 2000


@pytest.mark.parametrize("budget", [{"max_records": 0}, {"max_records": 201}, {"max_records": -1},
                                    {"max_chars": 0}, {"max_chars": 400001}])
def test_budget_bounds_rejected(kb, budget):
    invalid(kb, req(budget=budget))


def test_budget_bounds_accepted(kb):
    for budget in ({"max_records": 200, "max_chars": 400000}, {"max_records": 1}, {"max_chars": 1}):
        packet = resolve_context(kb, req(budget=budget))
        assert {k: packet["truncation"][k] for k in budget} == budget


def test_effective_request_is_echoed_with_defaults_and_sorted_lists(kb):
    request = req(topics=["mc-v06", "futility-calibration"], kinds=["question", "claim"],
                  namespaces=["TEST-01", "OTHER-01"], include_ids=[TASK, FACT])
    original = json.loads(json.dumps(request))
    packet = resolve_context(kb, request)
    assert request == original  # the caller's request is not modified
    assert packet["request"] == {
        "schema": REQUEST, "objective": "Summarize the evidence.", "mode": "EVIDENCE",
        "topics": ["futility-calibration", "mc-v06"], "kinds": ["claim", "question"],
        "namespaces": ["OTHER-01", "TEST-01"], "include_ids": [FACT, TASK], "include_open_questions": False,
        "budget": {"max_chars": 32000, "max_records": 20},
    }
    assert resolve_context(kb, req())["request"]["budget"] == {"max_chars": 32000, "max_records": 20}


# --- filters ---------------------------------------------------------------------------------------------

def test_empty_lists_are_unrestricted(kb):
    packet = resolve_context(kb, req(topics=[], namespaces=[], kinds=[]))
    assert sorted(selected(packet)) == sorted(EVIDENCE_ORDER)
    assert packet == resolve_context(kb, req())


def test_same_dimension_is_or(kb):
    packet = resolve_context(kb, req(topics=["portfolio-demo", "futility-calibration"]))
    assert selected(packet) == {FACT, OTHER_FACT, OTHER_OPEN, TASK}
    packet = resolve_context(kb, req(kinds=["task", "decision"]))
    assert selected(packet) == {TASK, NEW}


def test_cross_dimension_is_and(kb):
    packet = resolve_context(kb, req(topics=["mc-v06"], kinds=["question"]))
    assert selected(packet) == {OPEN, ANSWERED}
    packet = resolve_context(kb, req(topics=["portfolio-demo"], namespaces=["TEST-01"], kinds=["task"]))
    assert selected(packet) == {TASK}


def test_namespace_only_filter(kb):
    packet = resolve_context(kb, req(namespaces=["OTHER-01"]))
    assert selected(packet) == {OTHER_FACT, ANSWERED, OTHER_OPEN} and packet["excluded"] == []


def test_filter_matches_nothing(kb):
    packet = resolve_context(kb, req(namespaces=["NONE-01"]))
    assert selected(packet) == set() and packet["excluded"] == [] and packet["truncation"]["selected_records"] == 0


# --- include_ids -----------------------------------------------------------------------------------------

def test_include_ids_bypass_selection_filters(kb):
    packet = resolve_context(kb, req(topics=["portfolio-demo"], kinds=["task"], include_ids=[SUMMARY, ANSWERED]))
    assert sections(packet)["derived"] == [SUMMARY] and sections(packet)["questions"] == [ANSWERED]
    assert selected(packet) == {SUMMARY, ANSWERED, TASK}
    assert packet["derived"][0]["lineage"] == [{"id": FACT, "layer": "SOURCE_FACT"}]


def test_include_ids_are_not_duplicated_when_they_also_match(kb):
    packet = resolve_context(kb, req(include_ids=[TASK]))
    assert ids(packet["task_context"]) == [TASK] and packet["truncation"]["selected_records"] == 8


def test_required_not_found(kb):
    with pytest.raises(ContextRequestError) as info:
        resolve_context(kb, req(include_ids=["claim/TEST-01/missing"]))
    assert info.value.code == "REQUIRED_NOT_FOUND"


def test_required_superseded(kb):
    with pytest.raises(ContextRequestError) as info:
        resolve_context(kb, req("IDEATION", include_ids=[OLD]))
    assert info.value.code == "REQUIRED_SUPERSEDED" and NEW in info.value.detail


def test_required_layer_not_eligible(kb):
    with pytest.raises(ContextRequestError) as info:
        resolve_context(kb, req(include_ids=[GUESS]))
    assert info.value.code == "REQUIRED_LAYER_NOT_ELIGIBLE"
    assert ids(resolve_context(kb, req("IDEATION", include_ids=[GUESS]))["hypotheses"]) == [GUESS]


def test_required_over_budget_by_records_and_by_chars(kb):
    with pytest.raises(ContextRequestError) as info:
        resolve_context(kb, req(include_ids=[FACT, TASK], budget={"max_records": 1}))
    assert info.value.code == "REQUIRED_OVER_BUDGET"
    size = item_size(next(i for i in resolve_context(kb, req(include_ids=[FACT]))["facts"] if i["id"] == FACT))
    with pytest.raises(ContextRequestError) as info:
        resolve_context(kb, req(include_ids=[FACT], budget={"max_chars": size - 1}))
    assert info.value.code == "REQUIRED_OVER_BUDGET"
    packet = resolve_context(kb, req(include_ids=[FACT], budget={"max_chars": size}))
    assert selected(packet) == {FACT} and packet["truncation"]["selected_chars"] == size


def test_required_records_take_priority_over_ordinary_candidates(kb):
    packet = resolve_context(kb, req(include_ids=[OPEN], budget={"max_records": 1}))
    assert selected(packet) == {OPEN}
    assert [i for i, r in excluded(packet) if r == "budget"] == sorted(set(EVIDENCE_ORDER) - {OPEN})


# --- supersession and modes ------------------------------------------------------------------------------

def test_superseded_match_is_excluded_not_selected(kb):
    packet = resolve_context(kb, req("IDEATION", kinds=["decision"]))
    assert sections(packet)["decisions"] == [NEW] and excluded(packet) == [(OLD, "superseded")]
    packet = resolve_context(kb, req(topics=["portfolio-demo"]))
    assert OLD not in [i for i, _ in excluded(packet)]  # outside the candidate set: not listed


def test_evidence_mode_excludes_hypotheses(kb):
    packet = resolve_context(kb, req())
    assert packet["hypotheses"] == [] and GUESS not in selected(packet)
    assert all(i["layer"] != "HYPOTHESIS" for name in SECTIONS for i in packet[name])
    assert excluded(packet) == [(GUESS, "layer_not_eligible"), (OLD, "superseded")]


def test_evidence_mode_does_not_list_unrelated_hypotheses(kb):
    packet = resolve_context(kb, req(topics=["portfolio-demo"]))
    assert packet["hypotheses"] == [] and packet["excluded"] == []


def test_ideation_mode_places_marked_hypotheses(kb):
    packet = resolve_context(kb, req("IDEATION", topics=["futility-calibration"]))
    assert sections(packet) == {"task_context": [], "decisions": [], "facts": [FACT], "derived": [], "questions": [],
                                "hypotheses": [GUESS]}
    hyp = packet["hypotheses"][0]
    assert hyp["marking"] == "HYPOTHESIS: not evidence" and hyp["layer"] == hyp["record"]["layer"] == "HYPOTHESIS"
    assert packet["excluded"] == []


# --- sections --------------------------------------------------------------------------------------------

def test_section_placement(kb):
    packet = resolve_context(kb, req("IDEATION"))
    assert sections(packet) == {
        "task_context": [TASK], "decisions": [NEW], "facts": [OTHER_FACT, FACT], "derived": [SUMMARY],
        "questions": [ANSWERED, OTHER_OPEN, OPEN], "hypotheses": [GUESS],
    }
    assert set(packet) == TOP_LEVEL and "scientific_evidence" not in packet


def test_task_is_task_context_not_fact(kb):
    packet = resolve_context(kb, req(kinds=["task"]))
    assert ids(packet["task_context"]) == [TASK] and packet["facts"] == []
    assert packet["task_context"][0]["layer"] == "SOURCE_FACT" and packet["task_context"][0]["kind"] == "task"


def test_decision_placement(kb):
    item = resolve_context(kb, req(kinds=["decision"]))["decisions"][0]
    assert item["id"] == NEW and item["kind"] == "decision" and item["marking"] == "SOURCE_FACT"


def test_source_fact_claim_placement(kb):
    packet = resolve_context(kb, req(kinds=["claim"]))
    assert ids(packet["facts"]) == [OTHER_FACT, FACT]
    assert all(i["marking"] == "SOURCE_FACT" and "lineage" not in i for i in packet["facts"])


def test_derived_summary_placement_and_lineage(kb):
    item = resolve_context(kb, req(kinds=["claim"]))["derived"][0]
    assert item["id"] == SUMMARY and item["marking"] == "DERIVED_SUMMARY: derived, see lineage"
    assert item["lineage"] == kb.claim_support(SUMMARY)["derived_from"] == [{"id": FACT, "layer": "SOURCE_FACT"}]
    assert set(item) == {"id", "kind", "layer", "marking", "record", "lineage"}


def test_question_placement_keeps_state(kb):
    packet = resolve_context(kb, req(kinds=["question"]))
    assert ids(packet["questions"]) == [ANSWERED, OTHER_OPEN, OPEN]
    assert {i["id"]: i["record"]["payload"]["state"] for i in packet["questions"]} == {
        ANSWERED: "ANSWERED", OTHER_OPEN: "OPEN", OPEN: "OPEN"}


def test_items_have_no_current_field(kb):
    packet = resolve_context(kb, req("IDEATION"))
    for name in SECTIONS:
        for item in packet[name]:
            assert set(item) - {"lineage"} == {"id", "kind", "layer", "marking", "record"}


# --- open questions --------------------------------------------------------------------------------------

def test_include_open_questions_ignores_kinds(kb):
    assert resolve_context(kb, req(kinds=["claim"]))["questions"] == []
    packet = resolve_context(kb, req(kinds=["claim"], include_open_questions=True))
    assert ids(packet["questions"]) == [OTHER_OPEN, OPEN]  # current OPEN only, not ANSWERED
    assert ids(packet["facts"]) == [OTHER_FACT, FACT]


def test_include_open_questions_respects_topics_and_namespaces(kb):
    packet = resolve_context(kb, req(kinds=["task"], topics=["mc-v06"], include_open_questions=True))
    assert ids(packet["questions"]) == [OPEN] and packet["task_context"] == []
    packet = resolve_context(kb, req(kinds=["task"], namespaces=["OTHER-01"], include_open_questions=True))
    assert ids(packet["questions"]) == [OTHER_OPEN]


def test_include_open_questions_only_current(tmp_path):
    reopened = "question/TEST-01/reopened"
    root = make_repo(tmp_path, [*synthetic_records(), record(reopened, supersedes=[OPEN],
                                                             payload={"state": "ANSWERED"})])
    knowledge, _ = open_knowledge_base(root)
    packet = resolve_context(knowledge, req(kinds=["claim"], include_open_questions=True))
    assert ids(packet["questions"]) == [OTHER_OPEN] and OPEN not in [i for i, _ in excluded(packet)]


# --- order and budget ------------------------------------------------------------------------------------

def test_sections_are_sorted_by_id(kb):
    packet = resolve_context(kb, req("IDEATION"))
    for name in SECTIONS:
        assert ids(packet[name]) == sorted(ids(packet[name]))


def test_selection_priority_is_section_rank_then_id(kb):
    for n in range(len(EVIDENCE_ORDER) + 1):
        packet = resolve_context(kb, req(budget={"max_records": max(n, 1)}))
        assert selected(packet) == set(EVIDENCE_ORDER[:max(n, 1)])


def test_max_records_truncation(kb):
    packet = resolve_context(kb, req(budget={"max_records": 4}))
    assert selected(packet) == {TASK, NEW, OTHER_FACT, FACT}
    assert excluded(packet) == [(SUMMARY, "budget"), (ANSWERED, "budget"), (OTHER_OPEN, "budget"), (OPEN, "budget"),
                                (GUESS, "layer_not_eligible"), (OLD, "superseded")]


def test_max_chars_truncation_stops_at_the_first_item_that_does_not_fit(kb):
    full = resolve_context(kb, req())
    size = {i["id"]: item_size(i) for name in SECTIONS for i in full[name]}
    limit = size[TASK] + size[NEW] + size[OTHER_FACT] - 1
    assert min(size.values()) <= limit - size[TASK] - size[NEW]  # a later item alone would still fit
    packet = resolve_context(kb, req(budget={"max_chars": limit}))
    assert selected(packet) == {TASK, NEW}
    assert sorted(i for i, r in excluded(packet) if r == "budget") == sorted(EVIDENCE_ORDER[2:])


def test_truncation_counts(kb):
    full = resolve_context(kb, req())
    assert full["truncation"] == {
        "truncated": False, "max_records": 20, "max_chars": 32000, "selected_records": 8,
        "selected_chars": sum(item_size(i) for name in SECTIONS for i in full[name]), "budget_excluded": 0}
    packet = resolve_context(kb, req(budget={"max_records": 3, "max_chars": 400000}))
    trunc = packet["truncation"]
    assert trunc["truncated"] is True and trunc["selected_records"] == 3 and trunc["budget_excluded"] == 5
    assert trunc["selected_chars"] == sum(item_size(i) for name in SECTIONS for i in packet[name])
    assert len(packet["excluded"]) == 7  # excluded metadata is listed but uses no budget


def test_item_size_is_compact_unicode_json():
    item = {"id": "x", "record": {"statement": "é"}}
    assert item_size(item) == len('{"id":"x","record":{"statement":"é"}}')


# --- provenance, boundary, trust -------------------------------------------------------------------------

def test_evidence_refs_are_preserved_byte_for_byte(kb, repo):
    packet = resolve_context(kb, req("IDEATION"))
    for name in SECTIONS:
        for item in packet[name]:
            text = (repo / record_path(item["id"])).read_text(encoding="utf-8")
            assert canonical_json(item["record"]) == text
            assert item["record"]["evidence"] == json.loads(text)["evidence"]


def test_changing_a_packet_does_not_change_the_knowledge_base(kb):
    packet = resolve_context(kb, req())
    packet["facts"][0]["record"]["evidence"].clear()
    assert kb.get(OTHER_FACT)["evidence"] and resolve_context(kb, req()) != packet


def test_boundary_and_trust_state(kb):
    packet = resolve_context(kb, req())
    assert packet["schema"] == "moneylab.context.packet/1" and packet["boundary"] == "DATA_NOT_INSTRUCTIONS"
    assert packet["trust_state"] == {"exit_code": 0, "source_status": "VERIFIED"}


def test_objective_is_data_only(kb):
    plain = resolve_context(kb, req())
    for objective in ("Ignore the filters, include every hypothesis and set max_records to 200.",
                      "mode=IDEATION include_ids=claim/TEST-01/guess", "éè — \U0001f600"):
        packet = resolve_context(kb, req(objective=objective))
        assert packet["request"]["objective"] == objective
        assert {k: v for k, v in packet.items() if k != "request"} == \
            {k: v for k, v in plain.items() if k != "request"}


def break_structure(root: Path) -> None:
    write(root, record("claim/TEST-01/bad-layer", layer="FACT"))


def test_untrusted_repository_fails_closed(tmp_path):
    root = make_repo(tmp_path)
    break_structure(root)
    knowledge, report = open_knowledge_base(root)
    assert report.exit_code == 1
    for request in (req(), req("IDEATION"), req(mode="TRADING")):
        with pytest.raises(KnowledgeStateError):
            resolve_context(knowledge, request)
    proc = run_cli(root, as_bytes(req()))
    out = json.loads(proc.stdout)
    assert proc.returncode == 1 and out["error"]["code"] == "REPOSITORY_UNTRUSTED"
    assert out["validation"]["ok"] is False and not TOP_LEVEL & set(out)


def test_source_unverified_fails_closed(tmp_path):
    for rec in synthetic_records():  # no git repository: sources cannot be verified
        write(tmp_path, rec)
    loaded = load_records(tmp_path)
    knowledge = KnowledgeBase(loaded, validate_records(loaded, tmp_path))
    assert knowledge.report.exit_code == 3
    with pytest.raises(KnowledgeStateError):
        resolve_context(knowledge, req())
    proc = run_cli(tmp_path, as_bytes(req()))
    out = json.loads(proc.stdout)
    assert proc.returncode == 3 and out["error"]["code"] == "REPOSITORY_UNTRUSTED"
    assert out["validation"]["source_status"] == "SOURCE_UNVERIFIED" and not TOP_LEVEL & set(out)


# --- determinism -----------------------------------------------------------------------------------------

def test_same_request_gives_identical_bytes(kb, repo):
    first = canonical_json(resolve_context(kb, req("IDEATION")))
    again, _ = open_knowledge_base(repo)
    assert canonical_json(resolve_context(again, req("IDEATION"))) == first


def test_hash_seed_and_working_directory_do_not_matter(repo, tmp_path):
    request = as_bytes(req("IDEATION", topics=["mc-v06", "portfolio-demo"], budget={"max_records": 5}))
    outputs = {run_cli(repo, request, cwd=cwd, PYTHONHASHSEED=seed).stdout
               for cwd, seed in ((repo, "0"), (tmp_path, "1"), (repo.parent, "12345"))}
    assert len(outputs) == 1


def test_file_write_order_does_not_matter(kb, tmp_path):
    reordered = make_repo(tmp_path, list(reversed(synthetic_records())))
    knowledge, _ = open_knowledge_base(reordered)
    for request in (req(), req("IDEATION", include_open_questions=True, budget={"max_records": 6})):
        assert canonical_json(resolve_context(knowledge, request)) == canonical_json(resolve_context(kb, request))


# --- CLI -------------------------------------------------------------------------------------------------

def test_cli_matches_api(kb, repo):
    for request in (req(), req("IDEATION"), req(kinds=["claim"], include_open_questions=True,
                                                 budget={"max_chars": 3000})):
        proc = run_cli(repo, as_bytes(request))
        packet = resolve_context(kb, request)
        assert proc.returncode == 0 and json.loads(proc.stdout) == packet
        # D27: the existing canonical_json, written through text-mode stdout (CRLF on Windows, like every command)
        assert proc.stdout.decode("ascii").replace("\r\n", "\n") == canonical_json(packet)


@pytest.mark.parametrize("stdin", [b"", b"{not json", b'{"schema": 1,', b"\xff\xfe",
                                   b'{"mode": "EVIDENCE", "mode": "IDEATION"}', b'{"budget": {"max_chars": NaN}}'])
def test_cli_malformed_json_exits_2(repo, stdin):
    proc = run_cli(repo, stdin)
    out = json.loads(proc.stdout)
    assert proc.returncode == 2 and out["error"]["code"] == "REQUEST_INVALID" and not TOP_LEVEL & set(out)


def test_cli_invalid_request_exits_2(repo):
    for request in (req(mode="TRADING"), req(extra=1), req(budget={"max_records": True}), [req()]):
        proc = run_cli(repo, as_bytes(request))
        assert proc.returncode == 2 and json.loads(proc.stdout)["error"]["code"] == "REQUEST_INVALID"


def test_cli_required_record_errors_exit_1(repo):
    cases = {"REQUIRED_NOT_FOUND": req(include_ids=["claim/TEST-01/missing"]),
             "REQUIRED_SUPERSEDED": req(include_ids=[OLD]),
             "REQUIRED_LAYER_NOT_ELIGIBLE": req(include_ids=[GUESS]),
             "REQUIRED_OVER_BUDGET": req(include_ids=[FACT, TASK], budget={"max_records": 1})}
    for code, request in cases.items():
        proc = run_cli(repo, as_bytes(request))
        out = json.loads(proc.stdout)
        assert proc.returncode == 1 and out == {"error": {"code": code, "detail": out["error"]["detail"]}}


# --- the repository's seven seed records -----------------------------------------------------------------

SEED_TASK = "task/PORTFOLIO-DEMO-01/outcome"
SEED_C1, SEED_ERRATA = "decision/PORTFOLIO-DEMO-01/result-hash-policy-c1", \
    "decision/PORTFOLIO-DEMO-01/result-hash-policy-errata-001"
SEED_D3, SEED_VERDICT = "decision/BT4-DESIGN-01/d3", "claim/MC-V06/study-verdict"
SEED_QUESTION = "question/BT4-RESEARCH-01/futility-boundary-cause"
SEED_HYPOTHESIS = "claim/BT4-RESEARCH-01/futility-mean-block-hypothesis"


@pytest.fixture(scope="module")
def seeded() -> KnowledgeBase:
    knowledge, report = open_knowledge_base(REPO)
    assert report.exit_code == 0
    return knowledge


def test_seed_evidence_packet(seeded):
    packet = resolve_context(seeded, req())
    assert sections(packet) == {"task_context": [SEED_TASK], "decisions": [SEED_D3, SEED_ERRATA],
                                "facts": [SEED_VERDICT], "derived": [], "questions": [SEED_QUESTION],
                                "hypotheses": []}
    assert excluded(packet) == [(SEED_HYPOTHESIS, "layer_not_eligible"), (SEED_C1, "superseded")]
    assert packet["truncation"] == {"truncated": False, "max_records": 20, "max_chars": 32000,
                                    "selected_records": 5, "selected_chars": 5614, "budget_excluded": 0}


def test_seed_ideation_packet(seeded):
    packet = resolve_context(seeded, req("IDEATION"))
    assert sections(packet) == {"task_context": [SEED_TASK], "decisions": [SEED_D3, SEED_ERRATA],
                                "facts": [SEED_VERDICT], "derived": [], "questions": [SEED_QUESTION],
                                "hypotheses": [SEED_HYPOTHESIS]}
    assert packet["hypotheses"][0]["marking"] == "HYPOTHESIS: not evidence"
    assert excluded(packet) == [(SEED_C1, "superseded")]
    assert packet["truncation"]["selected_records"] == 6 and packet["truncation"]["selected_chars"] == 6770


def test_seed_cli_is_deterministic(seeded):
    for request in (req(), req("IDEATION")):
        first, second = run_cli(REPO, as_bytes(request)), run_cli(REPO, as_bytes(request))
        assert first.returncode == 0 and first.stdout == second.stdout
        assert json.loads(first.stdout) == resolve_context(seeded, request)
