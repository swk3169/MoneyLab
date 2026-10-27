"""Knowledge queries and context selection: the nine preregistered queries, the EVIDENCE / IDEATION boundary and the
fail-closed trust boundary (no query result from an invalid or unverified repository).

Records are written to a throwaway git repository in tmp_path, so sources verify against its HEAD."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
from test_knowledge_validate import git_repo, needs_git, record, write

from moneylab.knowledge import KnowledgeBase, load_records, open_knowledge_base, validate
from moneylab.knowledge.query import KnowledgeStateError

pytestmark = needs_git

FACT, SUMMARY, GUESS = "claim/TEST-01/fact", "claim/TEST-01/summary", "claim/TEST-01/guess"
OLD, MID, NEW = "decision/TEST-01/v1", "decision/TEST-01/v2", "decision/TEST-01/v3"
OPEN, ANSWERED, TASK = "question/TEST-01/open", "question/OTHER-01/answered", "task/TEST-01/outcome"


def valid_records():
    return [
        record(FACT, topics=["mc-v06", "futility-calibration"]),
        record(SUMMARY, layer="DERIVED_SUMMARY", derived_from=[FACT]),
        record(GUESS, layer="HYPOTHESIS", topics=["futility-calibration"]),
        record(OLD), record(MID, supersedes=[OLD]), record(NEW, supersedes=[MID]),
        record(OPEN), record(ANSWERED, payload={"state": "ANSWERED"}),
        record(TASK, topics=["portfolio-demo"]),
    ]


@pytest.fixture
def kb(tmp_path):
    git_repo(tmp_path)
    for rec in valid_records():
        write(tmp_path, rec)
    knowledge, report = open_knowledge_base(tmp_path)
    assert report.exit_code == 0 and knowledge.trusted
    return knowledge


def ids(items) -> list[str]:
    return [i["id"] for i in items]


def test_1_get(kb):
    assert kb.get(FACT)["id"] == FACT
    assert kb.get("claim/TEST-01/none") is None


def test_2_by_kind(kb):
    assert ids(kb.by_kind("claim")) == [FACT, GUESS, SUMMARY]
    assert ids(kb.by_kind("decision")) == [OLD, MID, NEW]
    with pytest.raises(ValueError):
        kb.by_kind("note")


def test_3_current(kb):
    assert ids(kb.current()) == [FACT, GUESS, SUMMARY, NEW, ANSWERED, OPEN, TASK]
    assert kb.is_current(NEW) and not kb.is_current(OLD)


def test_4_lineage(kb):
    assert kb.lineage(NEW) == {"id": NEW, "supersedes": [OLD, MID], "superseded_by": [], "current": NEW}
    assert kb.lineage(OLD) == {"id": OLD, "supersedes": [], "superseded_by": [MID, NEW], "current": NEW}
    with pytest.raises(KeyError):
        kb.lineage("claim/TEST-01/none")


def test_5_task_records(kb):
    assert ids(kb.task_records("TEST-01")) == [FACT, GUESS, SUMMARY, OLD, MID, NEW, OPEN, TASK]
    assert ids(kb.task_records("OTHER-01")) == [ANSWERED]


def test_6_claims_by_topic(kb):
    assert ids(kb.claims_by_topic("futility-calibration")) == [FACT, GUESS]
    assert ids(kb.claims_by_topic("portfolio-demo")) == []
    with pytest.raises(ValueError):
        kb.claims_by_topic("profitability")


def test_7_claim_support(kb):
    support = kb.claim_support(SUMMARY)
    assert support["derived_from"] == [{"id": FACT, "layer": "SOURCE_FACT"}]
    assert support["evidence"][0]["type"] == "git_blob" and kb.claim_support(FACT)["derived_from"] == []
    with pytest.raises(ValueError):
        kb.claim_support(OPEN)


def test_8_open_questions(kb):
    assert ids(kb.open_questions()) == [OPEN]


def test_9_evidence_context_excludes_hypotheses_and_superseded_records(kb):
    packet = kb.context("EVIDENCE")
    assert packet["boundary"] == "DATA_NOT_INSTRUCTIONS" and packet["mode"] == "EVIDENCE"
    assert ids(packet["items"]) == [FACT, SUMMARY, NEW, ANSWERED, OPEN, TASK]
    summary = next(i for i in packet["items"] if i["id"] == SUMMARY)
    assert summary["marking"].startswith("DERIVED_SUMMARY") and summary["lineage"] == [{"id": FACT,
                                                                                         "layer": "SOURCE_FACT"}]
    assert all(i["layer"] != "HYPOTHESIS" for i in packet["items"])


def test_9_ideation_context_keeps_hypotheses_marked(kb):
    packet = kb.context("IDEATION", topic="futility-calibration")
    assert ids(packet["items"]) == [FACT, GUESS]
    guess = next(i for i in packet["items"] if i["id"] == GUESS)
    assert guess["layer"] == "HYPOTHESIS" and guess["marking"] == "HYPOTHESIS: not evidence"
    assert guess["record"]["layer"] == "HYPOTHESIS"
    with pytest.raises(ValueError):
        kb.context("TRADING")


def test_queries_are_deterministic_and_serializable(kb, tmp_path):
    first = json.dumps([kb.current(), kb.context("EVIDENCE"), kb.context("IDEATION"), kb.lineage(OLD)], sort_keys=True)
    again = KnowledgeBase(load_records(tmp_path), validate(load_records(tmp_path), tmp_path))
    second = json.dumps([again.current(), again.context("EVIDENCE"), again.context("IDEATION"), again.lineage(OLD)],
                        sort_keys=True)
    assert first == second


# --- fail-closed trust boundary ---------------------------------------------------------------------------

def run_cli(root, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([sys.executable, "-m", "moneylab.knowledge", "--root", str(root), *args], env=env,
                          capture_output=True, text=True, timeout=120)


def break_malformed_json(root):
    (root / "knowledge/records/claim/TEST-01/broken.json").write_text("{not json", encoding="utf-8")


def break_structure(root):
    write(root, record("claim/TEST-01/bad-layer", layer="FACT"))


def break_dangling_reference(root):
    write(root, record("claim/TEST-01/dangling", derived_from=["claim/TEST-01/missing"]))


def break_provenance(root):
    rec = record("claim/TEST-01/wrong-hash")
    rec["evidence"][0]["sha256"] = "f" * 64
    write(root, rec)


QUERY_CALLS = [
    lambda k: k.get(FACT), lambda k: k.by_kind("claim"), lambda k: k.current(), lambda k: k.lineage(OLD),
    lambda k: k.task_records("TEST-01"), lambda k: k.claims_by_topic("mc-v06"), lambda k: k.claim_support(FACT),
    lambda k: k.open_questions(), lambda k: k.context("EVIDENCE"), lambda k: k.context("IDEATION"),
    lambda k: k.is_current(NEW),
]
CLI_QUERIES = [("get", FACT), ("current",), ("topic", "mc-v06"), ("open-questions",), ("context", "EVIDENCE"),
               ("context", "IDEATION")]


@pytest.mark.parametrize("breaker", [break_malformed_json, break_structure, break_dangling_reference,
                                     break_provenance])
def test_invalid_repository_fails_closed_in_api_and_cli(tmp_path, breaker):
    git_repo(tmp_path)
    for rec in valid_records():
        write(tmp_path, rec)
    breaker(tmp_path)
    knowledge, report = open_knowledge_base(tmp_path)
    assert report.exit_code == 1 and not knowledge.trusted
    for call in QUERY_CALLS:
        with pytest.raises(KnowledgeStateError):
            call(knowledge)
    assert run_cli(tmp_path, "validate").returncode == 1
    for args in CLI_QUERIES:
        proc = run_cli(tmp_path, "query", *args)
        out = json.loads(proc.stdout)
        assert proc.returncode == 1 and "error" in out and out["validation"]["ok"] is False
        assert "items" not in out and not isinstance(out, list)


def test_unverified_sources_fail_closed_with_exit_3(tmp_path):
    for rec in valid_records():  # no git repository: sources cannot be verified
        write(tmp_path, rec)
    loaded = load_records(tmp_path)
    knowledge = KnowledgeBase(loaded, validate(loaded, tmp_path))
    assert knowledge.report.exit_code == 3 and not knowledge.trusted
    with pytest.raises(KnowledgeStateError):
        knowledge.context("EVIDENCE")
    proc = run_cli(tmp_path, "query", "context", "IDEATION")
    assert proc.returncode == 3 and json.loads(proc.stdout)["validation"]["source_status"] == "SOURCE_UNVERIFIED"


def test_laundering_chain_never_reaches_a_context_packet(tmp_path):
    """H -> S1 -> S2 makes the repository invalid, so no EVIDENCE (or IDEATION) packet is produced at all."""
    git_repo(tmp_path)
    for rec in valid_records():
        write(tmp_path, rec)
    write(tmp_path, record("claim/TEST-01/s1", layer="DERIVED_SUMMARY", derived_from=[GUESS]))
    write(tmp_path, record("claim/TEST-01/s2", layer="DERIVED_SUMMARY", derived_from=["claim/TEST-01/s1"]))
    knowledge, report = open_knowledge_base(tmp_path)
    assert {"claim/TEST-01/s1", "claim/TEST-01/s2"} <= report.invalid_ids
    with pytest.raises(KnowledgeStateError):
        knowledge.context("EVIDENCE")
    assert run_cli(tmp_path, "query", "context", "EVIDENCE").returncode == 1
