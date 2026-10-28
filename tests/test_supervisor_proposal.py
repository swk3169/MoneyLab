"""Supervisor proposal generator (SUPERVISOR-01): candidate discovery, proposal schema and identity, validation,
staleness, CLI and the repository's own seed records (T1-T16, T21-T23, T25 of the Work Order).

Synthetic records are written to throwaway git repositories under tmp_path with the existing knowledge test helpers,
so sources verify against their HEAD. The last tests read the repository's own seed records without changing them."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_knowledge_validate import git_repo, needs_git, record, write

import moneylab.supervisor.proposal as proposal_module
from moneylab.knowledge import ContextRequestError, open_knowledge_base, resolve_context
from moneylab.knowledge.model import canonical_json, record_path
from moneylab.knowledge.query import KnowledgeStateError
from moneylab.supervisor import SupervisorError, check_proposal, propose, validate_proposal
from moneylab.supervisor.proposal import (
    BOUNDARY,
    EXPECTED_EVIDENCE_QUESTIONS,
    FAILURE_CRITERIA_QUESTIONS,
    FIXED_ASSUMPTIONS,
    FIXED_LIMITATIONS,
    PROHIBITED_ACTIONS,
    PROHIBITED_KEYS,
    SCOPE_LIMITATIONS,
    canonical_bytes,
    proposal_identity,
)

pytestmark = needs_git

REPO = Path(__file__).resolve().parents[1]
REQUEST = "moneylab.context.request/1"

FACT, TASK = "claim/TEST-01/fact", "task/TEST-01/outcome"
OPEN, ANSWERED, WITHDRAWN = "question/TEST-01/open", "question/TEST-01/answered", "question/TEST-01/withdrawn"
OLD_Q, NEW_Q = "question/TEST-01/old-open", "question/TEST-01/new-open"
PENDING, DECIDED = "decision/TEST-01/pending", "decision/TEST-01/decided"
GUESS, HYP_Q = "claim/TEST-01/guess", "question/TEST-01/hyp-open"

EVIDENCE_KEYS = [f"OPEN_QUESTION:{NEW_Q}", f"OPEN_QUESTION:{OPEN}", f"PENDING_DECISION:{PENDING}"]
IDEATION_KEYS = EVIDENCE_KEYS + [f"HYPOTHESIS:{GUESS}", f"HYPOTHESIS:{HYP_Q}"]

# proposal_id of the OPEN proposal from the synthetic repository under REQ("EVIDENCE"); a regression anchor (T2)
GOLDEN_OPEN_EVIDENCE_ID = "sha256:ca9bfeb8b9b86ae9519cfc8204c4818edc8cc3d5fa72133debcbe28612efe310"


def synthetic_records():
    return [
        record(FACT), record(TASK),
        record(OPEN), record(ANSWERED, payload={"state": "ANSWERED"}), record(WITHDRAWN, payload={"state": "WITHDRAWN"}),
        record(OLD_Q), record(NEW_Q, supersedes=[OLD_Q]),
        record(PENDING, payload={"local_id": None, "state": "PENDING"}), record(DECIDED),
        record(GUESS, layer="HYPOTHESIS"), record(HYP_Q, layer="HYPOTHESIS"),
    ]


def make_repo(root: Path, records=None, extra=()) -> Path:
    root.parent.mkdir(parents=True, exist_ok=True)
    git_repo(root)
    for rec in [*(synthetic_records() if records is None else records), *extra]:
        write(root, rec)
    return root


def open_kb(root: Path):
    kb, report = open_knowledge_base(root)
    assert kb.trusted, report.to_dict()
    return kb


def REQ(mode: str, **fields):
    return {"schema": REQUEST, "objective": "List candidate research problems.", "mode": mode, **fields}


def sha(obj) -> str:
    """D10/D11 computed independently of the implementation."""
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def rehash(p):
    p["proposal_id"] = sha({k: v for k, v in p.items() if k != "proposal_id"})
    return p


def by_key(result, key):
    return next(p for p in result["proposals"] if p["candidate_key"] == key)


def keys_of(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from keys_of(v)
    elif isinstance(value, list):
        for v in value:
            yield from keys_of(v)


def run_cli(root: Path, command: str, stdin: bytes, cwd: Path | None = None, **env: str):
    proc = subprocess.run([sys.executable, "-m", "moneylab.supervisor", "--root", str(root), command], input=stdin,
                          capture_output=True, cwd=cwd or root, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **env})
    return proc.returncode, proc.stdout.replace(b"\r\n", b"\n")


def as_bytes(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


@pytest.fixture(scope="module")
def repo(tmp_path_factory) -> Path:
    return make_repo(tmp_path_factory.mktemp("sup") / "repo")


@pytest.fixture(scope="module")
def kb(repo):
    return open_kb(repo)


@pytest.fixture(scope="module")
def evidence(kb):
    return propose(kb, REQ("EVIDENCE"))


@pytest.fixture(scope="module")
def ideation(kb):
    return propose(kb, REQ("IDEATION"))


@pytest.fixture()
def valid(evidence):
    return copy.deepcopy(by_key(evidence, f"OPEN_QUESTION:{OPEN}"))


# T1 determinism

def test_t1_api_results_are_byte_identical(kb, evidence, ideation):
    assert canonical_bytes(propose(kb, REQ("EVIDENCE"))) == canonical_bytes(evidence)
    assert canonical_bytes(propose(kb, REQ("IDEATION"))) == canonical_bytes(ideation)
    assert [p["candidate_key"] for p in evidence["proposals"]] == EVIDENCE_KEYS
    assert [p["candidate_key"] for p in ideation["proposals"]] == IDEATION_KEYS


def test_t1_cli_is_repeatable_and_agrees_with_the_api(repo, ideation, tmp_path):
    stdin = as_bytes(REQ("IDEATION"))
    expected = canonical_json(ideation).encode("utf-8")
    runs = [run_cli(repo, "propose", stdin), run_cli(repo, "propose", stdin),
            run_cli(repo, "propose", stdin, cwd=tmp_path, PYTHONHASHSEED="0"),
            run_cli(repo, "propose", stdin, PYTHONHASHSEED="12345")]
    assert all(code == 0 and out == expected for code, out in runs)


# T2 hash stability

def test_t2_hashes_recompute_from_their_definitions(kb, evidence):
    packet = resolve_context(kb, REQ("EVIDENCE"))
    items = {i["id"]: i for name in ("questions", "decisions") for i in packet[name]}
    for p in evidence["proposals"]:
        rid = p["source"]["record_ids"][0]
        assert p["provenance"]["packet_sha256"] == sha(packet)
        assert p["source"]["record_sha256"][rid] == sha(items[rid])
        assert p["proposal_id"] == sha({k: v for k, v in p.items() if k != "proposal_id"}) == proposal_identity(p)


def test_t2_canonical_bytes_and_golden_identity(evidence):
    assert canonical_bytes({"b": [1, True, None], "a": "é"}) == '{"a":"é","b":[1,true,null]}'.encode("utf-8")
    with pytest.raises(ValueError):
        canonical_bytes({"x": float("nan")})
    assert by_key(evidence, f"OPEN_QUESTION:{OPEN}")["proposal_id"] == GOLDEN_OPEN_EVIDENCE_ID


# T3 identity of distinct valid v1 proposals

def test_t3_semantically_different_valid_proposals_have_different_ids(kb):
    variants = [
        by_key(propose(kb, REQ("EVIDENCE")), f"OPEN_QUESTION:{OPEN}"),
        by_key(propose(kb, REQ("IDEATION")), f"OPEN_QUESTION:{OPEN}"),
        by_key(propose(kb, REQ("EVIDENCE", objective="Another objective.")), f"OPEN_QUESTION:{OPEN}"),
        by_key(propose(kb, REQ("EVIDENCE", budget={"max_records": 50})), f"OPEN_QUESTION:{OPEN}"),
        by_key(propose(kb, REQ("EVIDENCE")), f"OPEN_QUESTION:{NEW_Q}"),
    ]
    for p in variants:
        validate_proposal(p)
    assert len({p["proposal_id"] for p in variants}) == len(variants)


# T4 candidate_key survives a snapshot change

def test_t4_candidate_key_is_stable_across_unrelated_additions(tmp_path):
    before = by_key(propose(open_kb(make_repo(tmp_path / "a")), REQ("EVIDENCE")), f"OPEN_QUESTION:{OPEN}")
    after_kb = open_kb(make_repo(tmp_path / "b", extra=[record("claim/TEST-02/fact")]))
    after = by_key(propose(after_kb, REQ("EVIDENCE")), f"OPEN_QUESTION:{OPEN}")
    assert before["candidate_key"] == after["candidate_key"]
    assert before["proposal_id"] != after["proposal_id"]


# T5 a future rules_version changes identity but is not valid v1

def test_t5_future_rules_version_hashes_differently_and_is_rejected(valid):
    future = copy.deepcopy(valid)
    future["provenance"]["generator"]["rules_version"] = 2
    rehash(future)
    assert future["proposal_id"] != valid["proposal_id"]
    validate_proposal(valid)
    with pytest.raises(SupervisorError) as exc:
        validate_proposal(future)
    assert exc.value.code == "PROPOSAL_INVALID"


# T6 strict schema

def _derived_swap(p):
    fixed = len(FIXED_LIMITATIONS)
    p["limitations"][fixed:] = list(reversed(p["limitations"][fixed:]))


def _as_hypothesis_in_evidence(p):
    rid = p["source"]["record_ids"][0]
    p.update(candidate_type="HYPOTHESIS", epistemic_classification="HYPOTHESIS_NOT_EVIDENCE",
             candidate_key=f"HYPOTHESIS:{rid}")
    p["objective"]["text"] = f"Design a test of hypothesis {rid}. The hypothesis is not evidence."
    p["limitations"].append("HYPOTHESIS_ONLY_BASIS")


def _rid(p):
    return p["source"]["record_ids"][0]


MUTATIONS = [
    ("missing_top_key", lambda p: p.pop("limitations"), True),
    ("extra_top_key", lambda p: p.update(extra=1), True),
    ("missing_proposal_id", lambda p: p.pop("proposal_id"), False),
    ("extra_source_key", lambda p: p["source"].update(extra="x"), True),
    ("extra_quote_key", lambda p: p["source"]["quoted_text"][_rid(p)].update(extra="x"), True),
    ("extra_objective_key", lambda p: p["objective"].update(extra="x"), True),
    ("extra_criteria_key", lambda p: p["expected_evidence"].update(note="x"), True),
    ("extra_provenance_key", lambda p: p["provenance"].update(extra="x"), True),
    ("extra_trust_key", lambda p: p["provenance"]["trust_state"].update(extra=1), True),
    ("extra_generator_key", lambda p: p["provenance"]["generator"].update(extra=1), True),
    ("type_error", lambda p: p.update(candidate_type=1), True),
    ("float_value", lambda p: p["provenance"]["request"]["budget"].update(max_chars=1.5), True),
    ("non_string_key", lambda p: p["source"]["quoted_text"].update({1: "x"}), False),
    ("schema", lambda p: p.update(schema="moneylab.supervisor.proposal/2"), True),
    ("boundary", lambda p: p.update(boundary="AUTHORIZED_PROPOSAL"), True),
    ("text_role", lambda p: p["source"].update(text_role="INSTRUCTIONS"), True),
    ("objective_form", lambda p: p["objective"].update(form="FREE_TEXT"), True),
    ("specification", lambda p: p["failure_criteria"].update(specification="DEFINED"), True),
    ("generator_name", lambda p: p["provenance"]["generator"].update(name="other"), True),
    ("rules_version_bool", lambda p: p["provenance"]["generator"].update(rules_version=True), True),
    ("template_text", lambda p: p["objective"].update(text=p["objective"]["text"] + " Run it now."), True),
    ("reviewer_questions", lambda p: p["expected_evidence"]["reviewer_questions"].reverse(), True),
    ("scope_order", lambda p: p["scope_limitations"].reverse(), True),
    ("prohibited_missing", lambda p: p["prohibited_actions"].pop(), True),
    ("fixed_limitation_missing", lambda p: p["limitations"].remove("NOT_VALIDATED"), True),
    ("limitation_unknown", lambda p: p["limitations"].append("VALIDATED"), True),
    ("limitation_unsorted", _derived_swap, True),
    ("assumption_unknown", lambda p: p["unresolved_assumptions"].append("SOURCE_EVIDENCE_MISSING:evidence[x]"), True),
    ("proposal_id_wrong", lambda p: p.update(proposal_id="sha256:" + "0" * 64), False),
    ("packet_sha_format", lambda p: p["provenance"].update(packet_sha256="sha256:XYZ"), True),
    ("record_sha_format", lambda p: p["source"]["record_sha256"].update({_rid(p): "md5:abc"}), True),
    ("trust_exit_code", lambda p: p["provenance"]["trust_state"].update(exit_code=3), True),
    ("trust_source_status", lambda p: p["provenance"]["trust_state"].update(source_status="SOURCE_UNVERIFIED"), True),
    ("two_record_ids", lambda p: p["source"]["record_ids"].append(NEW_Q), True),
    ("candidate_key", lambda p: p.update(candidate_key=f"OPEN_QUESTION:{NEW_Q}"), True),
    ("classification", lambda p: p.update(epistemic_classification="QUESTION_IS_EVIDENCE"), True),
    ("type_pair", lambda p: p.update(candidate_type="PENDING_DECISION"), True),
    ("mode_mismatch", lambda p: p["provenance"].update(mode="IDEATION"), True),
    ("request_unknown_field", lambda p: p["provenance"]["request"].update(extra=1), True),
    ("request_not_normalized", lambda p: p["provenance"]["request"].update(kinds=["question", "claim"]), True),
    ("hypothesis_in_evidence", _as_hypothesis_in_evidence, True),
    ("empty_quote", lambda p: p["source"]["quoted_text"][_rid(p)].update(statement=""), True),
]


@pytest.mark.parametrize("name,mutate,recompute", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_t6_schema_is_strict(valid, name, mutate, recompute):
    validate_proposal(valid)
    mutate(valid)
    if recompute:
        rehash(valid)
    with pytest.raises(SupervisorError) as exc:
        validate_proposal(valid)
    assert exc.value.code == "PROPOSAL_INVALID"


def test_t6_contract_document_lists_the_fixed_constants():
    text = (REPO / "docs" / "supervisor_proposal_contract.md").read_text(encoding="utf-8")
    constants = [*SCOPE_LIMITATIONS, *PROHIBITED_ACTIONS, *FIXED_LIMITATIONS, *FIXED_ASSUMPTIONS,
                 *EXPECTED_EVIDENCE_QUESTIONS, *FAILURE_CRITERIA_QUESTIONS, *sorted(PROHIBITED_KEYS), BOUNDARY,
                 "moneylab.supervisor.result/1", "moneylab.supervisor.proposal/1", "moneylab.supervisor.check/1"]
    assert [c for c in constants if c not in text] == []


# T7 no self-authorization

def test_t7_outputs_carry_the_boundary_and_no_prohibited_key(kb, evidence, ideation):
    for result in (evidence, ideation):
        assert result["boundary"] == BOUNDARY
        assert all(p["boundary"] == BOUNDARY for p in result["proposals"])
        assert not set(keys_of(result)) & PROHIBITED_KEYS
    check = check_proposal(kb, ideation["proposals"][0])
    assert check["boundary"] == BOUNDARY and not set(check) & {"approved", "authorization", "status"}


@pytest.mark.parametrize("key", sorted(PROHIBITED_KEYS))
def test_t7_a_prohibited_key_is_rejected(valid, key):
    valid[key] = True
    rehash(valid)
    with pytest.raises(SupervisorError) as exc:
        validate_proposal(valid)
    assert exc.value.code == "PROPOSAL_INVALID"


# T8 epistemic boundaries

def test_t8_no_hypothesis_promotion(evidence, ideation):
    assert not [p for p in evidence["proposals"] if p["candidate_type"] == "HYPOTHESIS"]
    hyps = [p for p in ideation["proposals"] if p["candidate_type"] == "HYPOTHESIS"]
    assert [p["source"]["record_ids"][0] for p in hyps] == [GUESS, HYP_Q]  # the HYPOTHESIS-layer question too
    for p in hyps:
        assert p["epistemic_classification"] == "HYPOTHESIS_NOT_EVIDENCE"
        assert "HYPOTHESIS_ONLY_BASIS" in p["limitations"]
        assert "evidence" not in set(keys_of(p))
        assert set(p["source"]["quoted_text"][p["source"]["record_ids"][0]]) == {"title", "statement"}
    pending = by_key(evidence, f"PENDING_DECISION:{PENDING}")
    assert pending["epistemic_classification"] == "PENDING_NOT_APPROVED"
    assert by_key(evidence, f"OPEN_QUESTION:{OPEN}")["epistemic_classification"] == "QUESTION_NOT_EVIDENCE"


def test_t8_derived_limitations_and_assumptions(tmp_path, evidence):
    assert by_key(evidence, f"OPEN_QUESTION:{OPEN}")["limitations"] == [
        *FIXED_LIMITATIONS, "EXCLUDED_COUNT:layer_not_eligible:2", "EXCLUDED_COUNT:superseded:1"]
    gap = record("question/TEST-02/gap")
    gap["evidence"] = gap["evidence"] + [{"type": "external", "locator": "external:lab/notes",
                                          "provenance_class": "CLAUDE_REPORTED", "availability": "MISSING",
                                          "sha256": "e" * 64}]
    kb = open_kb(make_repo(tmp_path / "gap", records=[gap]))
    p = propose(kb, REQ("EVIDENCE"))["proposals"][0]
    assert p["unresolved_assumptions"] == [*FIXED_ASSUMPTIONS, "SOURCE_EVIDENCE_MISSING:evidence[1]"]
    validate_proposal(p)


# T9 current-only selection

def test_t9_only_current_eligible_items_are_candidates(evidence, ideation, kb):
    sources = {p["source"]["record_ids"][0] for r in (evidence, ideation) for p in r["proposals"]}
    assert not sources & {OLD_Q, ANSWERED, WITHDRAWN, DECIDED, FACT, TASK}
    with pytest.raises(ContextRequestError) as exc:
        propose(kb, REQ("EVIDENCE", include_ids=[OLD_Q]))
    assert exc.value.code == "REQUIRED_SUPERSEDED"


# T10 propose-time defensive checks on a tampered packet copy

def _item_for(kb, rid):
    data = kb.get(rid)
    return {"id": rid, "kind": data["kind"], "layer": data["layer"], "marking": data["layer"],
            "record": copy.deepcopy(data)}


def _ghost(packet, kb):
    item = _item_for(kb, OPEN)
    item["id"] = item["record"]["id"] = "question/TEST-01/ghost"
    packet["questions"].append(item)


def _superseded(packet, kb):
    packet["questions"].append(_item_for(kb, OLD_Q))


def _changed(packet, kb):
    next(i for i in packet["questions"] if i["id"] == OPEN)["record"]["statement"] = "Tampered."


def _boundary(packet, kb):
    packet["boundary"] = "INSTRUCTIONS"


def _duplicate(packet, kb):
    packet["questions"].append(copy.deepcopy(next(i for i in packet["questions"] if i["id"] == OPEN)))


@pytest.mark.parametrize("tamper,code", [(_ghost, "SOURCE_RECORD_MISSING"), (_superseded, "SOURCE_RECORD_SUPERSEDED"),
                                         (_changed, "SOURCE_RECORD_MISMATCH"), (_boundary, "PACKET_INVALID"),
                                         (_duplicate, "CANDIDATE_DUPLICATE")])
def test_t10_tampered_packets_fail_closed(kb, monkeypatch, tamper, code):
    def fake(kb_, request):
        packet = resolve_context(kb_, request)
        tamper(packet, kb_)
        return packet

    monkeypatch.setattr(proposal_module, "resolve_context", fake)
    with pytest.raises(SupervisorError) as exc:
        propose(kb, REQ("EVIDENCE"))
    assert exc.value.code == code


# T11 truncation

def _exact_budget(kb, **filters):
    packet = resolve_context(kb, REQ("EVIDENCE", budget={"max_records": 200, "max_chars": 400000}, **filters))
    t = packet["truncation"]
    return {"max_records": t["selected_records"], "max_chars": t["selected_chars"]}


def test_t11_a_truncated_packet_produces_nothing(kb):
    with pytest.raises(SupervisorError) as exc:
        propose(kb, REQ("EVIDENCE", budget={"max_records": 3}))
    assert exc.value.code == "PACKET_TRUNCATED"


def test_t11_an_exactly_fitting_budget_is_not_truncation(kb):
    budget = _exact_budget(kb)
    assert propose(kb, REQ("EVIDENCE", budget=budget))["proposal_count"] == 3
    with pytest.raises(SupervisorError):
        propose(kb, REQ("EVIDENCE", budget=dict(budget, max_chars=budget["max_chars"] - 1)))


# T12 staleness precedence

def _stale(tmp_path, change, request=None, key=f"OPEN_QUESTION:{OPEN}"):
    root = make_repo(tmp_path / "repo")
    p = by_key(propose(open_kb(root), request or REQ("EVIDENCE")), key)
    change(root)
    return check_proposal(open_kb(root), p)


def test_t12_superseded_source_is_stale_source(tmp_path):
    c = _stale(tmp_path, lambda root: write(root, record("question/TEST-01/open-v2", supersedes=[OPEN])))
    assert (c["staleness"], c["source_status"], c["context_status"]) == ("STALE_SOURCE", "STALE_SOURCE", "STALE_CONTEXT")
    assert "SOURCE_SUPERSEDED" in c["reasons"] and c["knowledge_tree"] == "NOT_VERIFIED"


def test_t12_modified_source_is_stale_source(tmp_path):
    c = _stale(tmp_path, lambda root: write(root, record(OPEN, statement="A changed statement.")))
    assert c["staleness"] == "STALE_SOURCE" and "SOURCE_MODIFIED" in c["reasons"]
    c = _stale(tmp_path / "x", lambda root: write(root, record(OPEN, payload={"state": "ANSWERED"})))
    assert c["staleness"] == "STALE_SOURCE" and {"SOURCE_INELIGIBLE", "SOURCE_MODIFIED"} <= set(c["reasons"])


def test_t12_deleted_source_is_stale_source(tmp_path):
    c = _stale(tmp_path, lambda root: (root / record_path(OPEN)).unlink())
    assert c["staleness"] == "STALE_SOURCE" and c["reasons"] == ["PACKET_HASH_CHANGED", "SOURCE_MISSING"]


def test_t12_changed_context_with_current_source_is_stale_context(tmp_path):
    c = _stale(tmp_path, lambda root: write(root, record("question/TEST-01/another")))
    assert (c["staleness"], c["source_status"], c["context_status"]) == ("STALE_CONTEXT", "CURRENT", "STALE_CONTEXT")
    assert c["reasons"] == ["PACKET_HASH_CHANGED"]


def test_t12_source_cut_from_the_regenerated_packet_is_not_verified(tmp_path):
    root = make_repo(tmp_path / "repo")
    kb = open_kb(root)
    filters = {"kinds": ["question", "task"]}
    p = by_key(propose(kb, REQ("EVIDENCE", budget=_exact_budget(kb, **filters), **filters)), f"OPEN_QUESTION:{OPEN}")
    write(root, record("task/TEST-02/outcome"))
    write(root, record("task/TEST-03/outcome"))
    c = check_proposal(open_kb(root), p)
    assert (c["staleness"], c["source_status"], c["context_status"]) == ("STALE_CONTEXT", "NOT_VERIFIED", "STALE_CONTEXT")
    assert {"CONTEXT_TRUNCATED", "SOURCE_NOT_IN_CONTEXT"} <= set(c["reasons"])


# T13 unrelated change

def test_t13_out_of_scope_changes_keep_the_proposal_current(tmp_path):
    other = record("claim/OTHER-01/fact", topics=["portfolio-demo"])
    root = make_repo(tmp_path / "repo", extra=[other])
    p = by_key(propose(open_kb(root), REQ("EVIDENCE", topics=["mc-v06"])), f"OPEN_QUESTION:{OPEN}")
    write(root, dict(other, statement="Changed out of scope."))
    write(root, record("claim/OTHER-02/fact", topics=["portfolio-demo"]))
    c = check_proposal(open_kb(root), p)
    assert c == {"schema": "moneylab.supervisor.check/1", "boundary": BOUNDARY, "proposal_id": p["proposal_id"],
                 "staleness": "CURRENT", "source_status": "CURRENT", "context_status": "CURRENT",
                 "knowledge_tree": "NOT_VERIFIED", "reasons": []}


# T14 check error paths

class _Untouchable:
    def __getattr__(self, name):
        raise AssertionError(f"KnowledgeBase.{name} was used")


def test_t14_invalid_proposal_is_rejected_before_any_kb_access(valid):
    valid["boundary"] = "AUTHORIZED"
    with pytest.raises(SupervisorError) as exc:
        check_proposal(_Untouchable(), valid)
    assert exc.value.code == "PROPOSAL_INVALID"


def test_t14_same_digest_with_a_different_quote_is_invalid(kb, valid):
    valid["source"]["quoted_text"][OPEN]["statement"] = "A forged quote."
    rehash(valid)
    validate_proposal(valid)
    with pytest.raises(SupervisorError) as exc:
        check_proposal(kb, valid)
    assert exc.value.code == "PROPOSAL_INVALID"


def test_t14_a_rejected_recorded_request_is_check_request_rejected(kb, valid, monkeypatch):
    def reject(kb_, request):
        raise ContextRequestError("REQUEST_INVALID", "rejected")

    monkeypatch.setattr(proposal_module, "resolve_context", reject)
    with pytest.raises(SupervisorError) as exc:
        check_proposal(kb, valid)
    assert exc.value.code == "CHECK_REQUEST_REJECTED"


# T15 invalid input and trust

def _untrusted_repo(root: Path) -> Path:
    make_repo(root)
    write(root, record(), path="knowledge/records/claim/TEST-01/notes.txt", text="not a record\n")
    return root


def _unverified_repo(root: Path) -> Path:
    for rec in synthetic_records():
        write(root, rec)
    return root


def test_t15_invalid_requests_and_untrusted_repositories(tmp_path, repo):
    code, out = run_cli(repo, "propose", as_bytes(REQ("EVIDENCE", extra=1)))
    assert code == 2 and json.loads(out)["error"]["code"] == "REQUEST_INVALID"
    root = _untrusted_repo(tmp_path / "bad")
    kb, _ = open_knowledge_base(root)
    with pytest.raises(KnowledgeStateError):
        propose(kb, REQ("EVIDENCE"))
    code, out = run_cli(root, "propose", as_bytes(REQ("EVIDENCE")))
    assert code == 1 and json.loads(out)["error"]["code"] == "REPOSITORY_UNTRUSTED" and "proposals" not in out.decode()
    code, out = run_cli(_unverified_repo(tmp_path / "nogit"), "propose", as_bytes(REQ("EVIDENCE")))
    assert code == 3 and json.loads(out)["validation"]["source_status"] == "SOURCE_UNVERIFIED"


# T16 no candidates

def test_t16_no_candidates_invents_nothing(kb):
    result = propose(kb, REQ("EVIDENCE", kinds=["task"]))
    assert result == {"schema": "moneylab.supervisor.result/1", "boundary": BOUNDARY, "outcome": "NO_CANDIDATES",
                      "proposal_count": 0, "proposals": []}


# T21 CLI exit codes, precedence and output form

def test_t21_propose_exit_codes(repo, tmp_path):
    cases = [
        (as_bytes(REQ("EVIDENCE")), 0, None),
        (as_bytes(REQ("EVIDENCE", kinds=["task"])), 0, None),
        (as_bytes(REQ("EVIDENCE", include_ids=["question/TEST-01/none"])), 1, "REQUIRED_NOT_FOUND"),
        (as_bytes(REQ("EVIDENCE", budget={"max_records": 3})), 1, "PACKET_TRUNCATED"),
        (b"{not json", 2, "REQUEST_INVALID"),
        (b'{"a": NaN}', 2, "REQUEST_INVALID"),
        (b'{"a": 1, "a": 2}', 2, "REQUEST_INVALID"),
    ]
    for stdin, expected, error in cases:
        code, out = run_cli(repo, "propose", stdin)
        assert code == expected, (stdin, out)
        doc = json.loads(out)
        if error is None:
            assert doc["schema"] == "moneylab.supervisor.result/1" and out.decode() == canonical_json(doc)
        else:
            assert set(doc) == {"error"} and set(doc["error"]) == {"code", "detail"} and doc["error"]["code"] == error
    bad = _untrusted_repo(tmp_path / "bad")
    code, out = run_cli(bad, "propose", b"{not json")  # stdin JSON error precedes trust
    assert code == 2 and json.loads(out)["error"]["code"] == "REQUEST_INVALID"


def test_t21_check_exit_codes(tmp_path, repo, evidence):
    p = by_key(evidence, f"OPEN_QUESTION:{OPEN}")
    code, out = run_cli(repo, "check", as_bytes(p))
    assert code == 0 and json.loads(out)["staleness"] == "CURRENT" and out.decode() == canonical_json(json.loads(out))
    assert run_cli(repo, "check", b"[1")[0] == 2
    code, out = run_cli(repo, "check", as_bytes(dict(p, boundary="AUTHORIZED")))
    assert code == 2 and json.loads(out)["error"]["code"] == "PROPOSAL_INVALID"
    bad = _untrusted_repo(tmp_path / "bad")
    code, out = run_cli(bad, "check", as_bytes(dict(p, boundary="AUTHORIZED")))  # validation precedes trust
    assert code == 2 and json.loads(out)["error"]["code"] == "PROPOSAL_INVALID"
    code, out = run_cli(bad, "check", as_bytes(p))
    assert code == 1 and json.loads(out)["error"]["code"] == "REPOSITORY_UNTRUSTED"
    root = make_repo(tmp_path / "moved")
    moved = by_key(propose(open_kb(root), REQ("EVIDENCE")), f"OPEN_QUESTION:{OPEN}")
    write(root, record("question/TEST-01/another"))
    code, out = run_cli(root, "check", as_bytes(moved))
    assert code == 1 and json.loads(out)["staleness"] == "STALE_CONTEXT"


# T22 isolation of returned documents

def test_t22_returned_documents_are_independent(kb, repo):
    first = propose(kb, REQ("IDEATION"))
    expected = canonical_bytes(first)
    stored = copy.deepcopy(kb.get(OPEN))
    p = by_key(first, f"OPEN_QUESTION:{OPEN}")
    p["source"]["quoted_text"][OPEN]["statement"] = "mutated"
    p["provenance"]["request"]["mode"] = "EVIDENCE"
    first["proposals"].clear()
    check = check_proposal(kb, by_key(propose(kb, REQ("IDEATION")), f"OPEN_QUESTION:{OPEN}"))
    check["reasons"].append("mutated")
    assert canonical_bytes(propose(kb, REQ("IDEATION"))) == expected
    assert kb.get(OPEN) == stored
    assert check_proposal(kb, by_key(propose(kb, REQ("IDEATION")), f"OPEN_QUESTION:{OPEN}"))["reasons"] == []


# T23 the repository's own seed records

def test_t23_seed_records():
    kb = open_kb(REPO)
    evidence = propose(kb, REQ("EVIDENCE"))
    ideation = propose(kb, REQ("IDEATION"))
    ev_ids = [p["source"]["record_ids"][0] for p in evidence["proposals"]]
    assert ev_ids == ["question/BT4-RESEARCH-01/futility-boundary-cause", "decision/BT4-DESIGN-01/d3"]
    assert [p["source"]["record_ids"][0] for p in ideation["proposals"]] == \
        ev_ids + ["claim/BT4-RESEARCH-01/futility-mean-block-hypothesis"]
    for p in evidence["proposals"] + ideation["proposals"]:
        validate_proposal(p)
        assert check_proposal(kb, p)["staleness"] == "CURRENT"


# T25 validation does not establish source authenticity

def test_t25_fabricated_source_passes_validation_but_not_check(kb, valid):
    forged_digest = copy.deepcopy(valid)
    forged_digest["source"]["record_sha256"][OPEN] = "sha256:" + "1" * 64
    rehash(forged_digest)
    validate_proposal(forged_digest)
    c = check_proposal(kb, forged_digest)
    assert c["staleness"] == "STALE_SOURCE" and "SOURCE_MODIFIED" in c["reasons"]
    forged_quote = copy.deepcopy(valid)
    forged_quote["source"]["quoted_text"][OPEN] = {"title": "Forged", "statement": "Forged statement."}
    rehash(forged_quote)
    validate_proposal(forged_quote)
    with pytest.raises(SupervisorError) as exc:
        check_proposal(kb, forged_quote)
    assert exc.value.code == "PROPOSAL_INVALID"
