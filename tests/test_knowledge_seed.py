"""The repository's seed knowledge records and the package boundary (KNOWLEDGE-WIKI-01).

Validation reads committed blob bytes at HEAD through git, which also works in CI's shallow checkout."""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from moneylab.knowledge import open_knowledge_base
from moneylab.knowledge.model import TOPICS, canonical_json

REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "src" / "moneylab" / "knowledge"
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not available")

SEEDS = {
    "task/PORTFOLIO-DEMO-01/outcome": "SOURCE_FACT",
    "decision/PORTFOLIO-DEMO-01/result-hash-policy-c1": "SOURCE_FACT",
    "decision/PORTFOLIO-DEMO-01/result-hash-policy-errata-001": "SOURCE_FACT",
    "claim/MC-V06/study-verdict": "SOURCE_FACT",
    "question/BT4-RESEARCH-01/futility-boundary-cause": "SOURCE_FACT",
    "decision/BT4-DESIGN-01/d3": "SOURCE_FACT",
    "claim/BT4-RESEARCH-01/futility-mean-block-hypothesis": "HYPOTHESIS",
}
C1_POLICY, ERRATA_POLICY = "decision/PORTFOLIO-DEMO-01/result-hash-policy-c1", \
    "decision/PORTFOLIO-DEMO-01/result-hash-policy-errata-001"
HYPOTHESIS = "claim/BT4-RESEARCH-01/futility-mean-block-hypothesis"
QUESTION = "question/BT4-RESEARCH-01/futility-boundary-cause"
TASK = "task/PORTFOLIO-DEMO-01/outcome"


@pytest.fixture(scope="module")
def seeded():
    return open_knowledge_base(REPO)


def test_exactly_the_seven_seed_records_exist():
    files = sorted(p.relative_to(REPO).as_posix() for p in (REPO / "knowledge" / "records").rglob("*") if p.is_file())
    assert files == sorted(f"knowledge/records/{rid}.json" for rid in SEEDS)


@needs_git
def test_seed_records_validate_against_head(seeded):
    kb, report = seeded
    assert report.problems == () and report.source_status == "VERIFIED" and report.exit_code == 0
    assert {r["id"]: r["layer"] for r in kb.current() + [kb.get(C1_POLICY)]} == SEEDS


def test_seed_files_are_canonical_ascii_and_use_the_topic_enum():
    for rid in SEEDS:
        text = (REPO / "knowledge" / "records" / f"{rid}.json").read_bytes().decode("ascii").replace("\r\n", "\n")
        data = json.loads(text)
        assert text == canonical_json(data) and set(data["topics"]) <= set(TOPICS)


@needs_git
def test_errata_policy_supersedes_the_c1_policy(seeded):
    kb, _ = seeded
    assert kb.get(ERRATA_POLICY)["supersedes"] == [C1_POLICY]
    assert not kb.is_current(C1_POLICY) and kb.is_current(ERRATA_POLICY)
    assert kb.lineage(C1_POLICY)["current"] == ERRATA_POLICY


@needs_git
def test_futility_cause_stays_an_open_question(seeded):
    kb, _ = seeded
    assert [q["id"] for q in kb.open_questions()] == [QUESTION]


@needs_git
def test_hypothesis_stays_out_of_evidence_and_is_marked_in_ideation(seeded):
    kb, _ = seeded
    hyp = kb.get(HYPOTHESIS)
    assert hyp["layer"] == "HYPOTHESIS" and "not causally confirmed" in hyp["statement"]
    assert "does not establish profitability, alpha, or live readiness" in hyp["statement"]
    evidence = [i["id"] for i in kb.context("EVIDENCE")["items"]]
    assert HYPOTHESIS not in evidence and len(evidence) == 5
    ideation = {i["id"]: i for i in kb.context("IDEATION")["items"]}
    assert ideation[HYPOTHESIS]["marking"] == "HYPOTHESIS: not evidence" and len(ideation) == 6


@needs_git
def test_task_record_holds_identity_facts_only(seeded):
    kb, _ = seeded
    task = kb.get(TASK)
    assert task["payload"]["outcome"] == "MERGED_TO_MAIN"
    text = json.dumps(task)
    for word in ("PASS", "COMPLETE", "BLOCKED", "passed", "failed", "guard", "chat"):
        assert not re.search(rf"\b{word}\b", text), word
    assert [r["id"] for r in kb.task_records("PORTFOLIO-DEMO-01")] == [C1_POLICY, ERRATA_POLICY, TASK]


def test_no_seed_claims_profitability_or_readiness():
    for rid in SEEDS:
        text = (REPO / "knowledge" / "records" / f"{rid}.json").read_text(encoding="ascii").lower()
        for phrase in ("is profitable", "proven alpha", "edge found", "live-ready", "production-ready"):
            assert phrase not in text


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([sys.executable, "-m", "moneylab.knowledge", "--root", str(REPO), *args], env=env,
                          capture_output=True, text=True, timeout=120)


@needs_git
def test_cli_validate_and_queries_are_deterministic():
    proc = run_cli("validate")
    assert proc.returncode == 0 and json.loads(proc.stdout)["source_status"] == "VERIFIED"
    for args in (("context", "EVIDENCE"), ("lineage", C1_POLICY), ("open-questions",), ("topic", "mc-v06")):
        first, second = run_cli("query", *args), run_cli("query", *args)
        assert first.returncode == 0 and first.stdout == second.stdout and json.loads(first.stdout)
    assert run_cli("query", "get", "claim/NONE-01/x").returncode == 1
    assert run_cli("query", "kind", "note").returncode == 2


STDLIB = {"__future__", "argparse", "collections", "dataclasses", "hashlib", "json", "pathlib", "re", "subprocess",
          "sys", "typing"}


def test_knowledge_package_uses_only_the_standard_library_and_itself():
    for file in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            for name in names:
                assert name.split(".")[0] in STDLIB or name.startswith("moneylab.knowledge"), (file.name, name)
