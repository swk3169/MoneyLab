"""Knowledge record validator: each of the 15 preregistered rules rejects a violation (KNOWLEDGE-WIKI-01).

Records are written to tmp_path; the repository's own records are tested in test_knowledge_seed.py. Secret-like
values are synthetic and assembled at run time so that no literal in this file looks like a credential."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from test_repo_hygiene import SECRET_PATTERNS as HYGIENE_SECRET_PATTERNS

from moneylab.knowledge import load_records, validate
from moneylab.knowledge.model import canonical_json, record_path
from moneylab.knowledge.validate import SECRET_PATTERNS, SOURCE_UNVERIFIED, VERIFIED

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
SOURCE = "docs/source.md"
SOURCE_TEXT = b"line one\nline two\n"
REV = "a" * 40


def record(rid: str = "claim/TEST-01/fact", **changes):
    kind = rid.split("/")[0]
    payload = {"claim": {"axis": "SCIENTIFIC", "data_basis": "SYNTHETIC"}, "decision": {"local_id": None, "state": "DECIDED"},
               "question": {"state": "OPEN"},
               "task": {"implementation_commit": "b" * 40, "merge_commit": "c" * 40, "outcome": "MERGED_TO_MAIN",
                        "task_id": rid.split("/")[1], "tree": "d" * 40}}[kind]
    rec = {"schema": "moneylab.knowledge.record/1", "id": rid, "kind": kind, "layer": "SOURCE_FACT", "title": "A title",
           "statement": "A statement.", "topics": ["mc-v06"], "supersedes": [], "derived_from": [], "labels": {},
           "evidence": [{"type": "git_blob", "rev": REV, "path": SOURCE, "sha256": hashlib.sha256(SOURCE_TEXT).hexdigest(),
                         "locator": "L1", "provenance_class": "GIT_VERIFIABLE", "availability": "IN_GIT"}],
           "payload": payload}
    rec.update(changes)
    return rec


def write(root: Path, rec, path: str | None = None, text: str | None = None) -> None:
    target = root / (path or record_path(rec["id"]))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(canonical_json(rec) if text is None else text, encoding="utf-8", newline="\n")


def check(root: Path, use_git: bool = False, full_history: bool = False):
    return validate(load_records(root), root, use_git=use_git, full_history=full_history)


def rules(report) -> set[int]:
    return {p.rule for p in report.problems}


def git_repo(root: Path) -> str:
    """A throwaway repository holding SOURCE; returns its commit."""
    hooks = root.parent / f"{root.name}-hooks"
    hooks.mkdir()

    def git(*args: str) -> str:
        out = subprocess.run(["git", "-c", f"core.hooksPath={hooks}", "-c", "commit.gpgsign=false", "-c", "user.name=t",
                              "-c", "user.email=t@example.invalid", "-c", "core.autocrlf=false", *args],
                             cwd=root, check=True, capture_output=True)
        return out.stdout.decode().strip()

    (root / SOURCE).parent.mkdir(parents=True, exist_ok=True)
    (root / SOURCE).write_bytes(SOURCE_TEXT)
    git("init", "-q")
    git("add", SOURCE)
    git("commit", "-q", "-m", "source")
    return git("rev-parse", "HEAD")


def test_secret_patterns_are_the_repository_hygiene_patterns():
    assert SECRET_PATTERNS == HYGIENE_SECRET_PATTERNS


def test_a_valid_record_passes_without_git_as_source_unverified(tmp_path):
    write(tmp_path, record())
    report = check(tmp_path)
    assert report.problems == () and report.source_status == SOURCE_UNVERIFIED and report.exit_code == 3
    assert report.unverified and "git unavailable" in report.unverified[0]


@needs_git
def test_a_valid_record_verifies_against_the_head_blob(tmp_path):
    rev = git_repo(tmp_path)
    write(tmp_path, record(evidence=[dict(record()["evidence"][0], rev=rev)]))
    report = check(tmp_path, use_git=True, full_history=True)
    assert report.ok and report.source_status == VERIFIED and report.exit_code == 0


def test_rule_1_unsupported_schema(tmp_path):
    write(tmp_path, record(schema="moneylab.knowledge.record/2"))
    assert rules(check(tmp_path)) == {1}


def test_rule_2_duplicate_id(tmp_path):
    write(tmp_path, record())
    write(tmp_path, record(), path="knowledge/records/claim/TEST-01/copy.json")
    report = check(tmp_path)
    assert rules(report) == {2} and len(report.problems) == 2


@pytest.mark.parametrize("rid", ["claim/test-01/fact", "claim/TEST-01/Fact", "note/TEST-01/fact", "claim/TEST-01",
                                 "claim/-X/fact", "claim/TEST-01/f_x"])
def test_rule_3_malformed_id(tmp_path, rid):
    write(tmp_path, record(id=rid), path="knowledge/records/claim/TEST-01/fact.json")
    assert rules(check(tmp_path)) == {3}


def test_rule_4_id_path_mismatch(tmp_path):
    write(tmp_path, record(), path="knowledge/records/claim/TEST-01/other.json")
    assert rules(check(tmp_path)) == {4}


@pytest.mark.parametrize("change", [
    {"title": ""}, {"statement": "caf\u00e9"}, {"layer": "FACT"}, {"kind": "decision"}, {"topics": []},
    {"topics": ["alpha"]}, {"topics": ["mc-v06", "mc-v06"]}, {"labels": {"x": 1}}, {"supersedes": "x"},
    {"payload": {"axis": "PROFITABLE", "data_basis": "SYNTHETIC"}}, {"payload": {"axis": "SCIENTIFIC"}},
    {"payload": {"axis": "SCIENTIFIC", "data_basis": "REAL", "status": "PASS"}}, {"extra": True},
    {"evidence": [{"type": "git_blob"}]}, {"evidence": [{"type": "web", "provenance_class": "INDEPENDENT"}]},
])
def test_rule_5_structure(tmp_path, change):
    write(tmp_path, record(**change))
    assert 5 in rules(check(tmp_path))


def test_rule_5_missing_field_and_bad_evidence_values(tmp_path):
    rec = record()
    del rec["labels"]
    write(tmp_path, rec)
    bad = record("claim/TEST-01/other")
    bad["evidence"][0].update(rev="HEAD", sha256="x", provenance_class="MEASURED", availability="GITHUB", path="../x")
    write(tmp_path, bad)
    report = check(tmp_path)
    messages = " ".join(p.message for p in report.problems)
    assert rules(report) == {5} and "missing field labels" in messages
    for word in ("rev", "sha256", "provenance_class", "availability", "path"):
        assert word in messages


def test_rule_5_task_payload(tmp_path):
    rec = record("task/TEST-01/outcome")
    rec["payload"] = dict(rec["payload"], task_id="OTHER-01", outcome="COMPLETE", tree="zz")
    write(tmp_path, rec)
    messages = " ".join(p.message for p in check(tmp_path).problems)
    assert "task_id" in messages and "outcome" in messages and "tree" in messages


def test_rule_5_non_canonical_json_and_unreadable_files(tmp_path):
    rec = record()
    write(tmp_path, rec, text=json.dumps(rec))  # valid JSON, not canonical
    (tmp_path / "knowledge/records/claim/TEST-01/broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "knowledge/records/claim/TEST-01/dup-keys.json").write_text('{"a": 1, "a": 2}', encoding="utf-8")
    (tmp_path / "knowledge/records/claim/TEST-01/notes.txt").write_text("x", encoding="utf-8")
    report = check(tmp_path)
    assert rules(report) == {5}
    assert {p.record_id for p in report.problems} == {
        "claim/TEST-01/fact", "knowledge/records/claim/TEST-01/broken.json",
        "knowledge/records/claim/TEST-01/dup-keys.json", "knowledge/records/claim/TEST-01/notes.txt"}


def test_crlf_record_is_read_as_lf(tmp_path):
    write(tmp_path, record(), text=canonical_json(record()).replace("\n", "\r\n"))
    assert check(tmp_path).problems == ()


def test_rule_6_nonexistent_reference(tmp_path):
    write(tmp_path, record(supersedes=["claim/TEST-01/missing"], derived_from=["claim/TEST-01/gone"]))
    assert rules(check(tmp_path)) == {6} and len(check(tmp_path).problems) == 2


def test_rule_7_supersession_cycle(tmp_path):
    write(tmp_path, record("claim/TEST-01/a", supersedes=["claim/TEST-01/b"]))
    write(tmp_path, record("claim/TEST-01/b", supersedes=["claim/TEST-01/a"]))
    write(tmp_path, record("claim/TEST-01/self", supersedes=["claim/TEST-01/self"]))
    report = check(tmp_path)
    assert {(p.rule, p.record_id) for p in report.problems if p.rule == 7} == {
        (7, "claim/TEST-01/a"), (7, "claim/TEST-01/b"), (7, "claim/TEST-01/self")}


def test_rule_8_supersession_branch(tmp_path):
    write(tmp_path, record("claim/TEST-01/old"))
    write(tmp_path, record("claim/TEST-01/new-a", supersedes=["claim/TEST-01/old"]))
    write(tmp_path, record("claim/TEST-01/new-b", supersedes=["claim/TEST-01/old"]))
    report = check(tmp_path)
    assert [(p.rule, p.record_id) for p in report.problems] == [(8, "claim/TEST-01/old")]


def test_merging_supersession_is_allowed(tmp_path):
    write(tmp_path, record("claim/TEST-01/old-a"))
    write(tmp_path, record("claim/TEST-01/old-b"))
    write(tmp_path, record("claim/TEST-01/merged", supersedes=["claim/TEST-01/old-a", "claim/TEST-01/old-b"]))
    assert check(tmp_path).problems == ()


def test_rule_9_kind_mismatch_and_layer_downgrade(tmp_path):
    write(tmp_path, record("claim/TEST-01/fact"))
    write(tmp_path, record("decision/TEST-01/other", supersedes=["claim/TEST-01/fact"]))
    write(tmp_path, record("claim/TEST-01/summary"))
    write(tmp_path, record("claim/TEST-01/guess", layer="HYPOTHESIS", supersedes=["claim/TEST-01/summary"]))
    report = check(tmp_path)
    assert {(p.rule, p.record_id) for p in report.problems} == {(9, "decision/TEST-01/other"), (9, "claim/TEST-01/guess")}


def test_rule_9_derived_summary_cannot_supersede_a_source_fact(tmp_path):
    write(tmp_path, record("claim/TEST-01/fact"))
    write(tmp_path, record("claim/TEST-01/summary", layer="DERIVED_SUMMARY", derived_from=["claim/TEST-01/fact"],
                           supersedes=["claim/TEST-01/fact"]))
    assert [(p.rule, p.record_id) for p in check(tmp_path).problems] == [(9, "claim/TEST-01/summary")]


def test_rule_10_derived_summary_needs_derived_from(tmp_path):
    write(tmp_path, record(layer="DERIVED_SUMMARY"))
    assert rules(check(tmp_path)) == {10}


def test_rule_11_source_fact_needs_a_qualifying_git_blob(tmp_path):
    external = {"type": "external", "locator": "external:mc-v06-run/run-1/result.json", "sha256": "e" * 64,
                "provenance_class": "CLAUDE_REPORTED", "availability": "EXTERNAL_LOCAL"}
    write(tmp_path, record("claim/TEST-01/external-only", evidence=[external]))
    weak = record("claim/TEST-01/reported")
    weak["evidence"][0]["provenance_class"] = "CLAUDE_REPORTED"
    write(tmp_path, weak)
    write(tmp_path, record("claim/TEST-01/hypothesis", layer="HYPOTHESIS", evidence=[external]))  # allowed
    report = check(tmp_path)
    assert {(p.rule, p.record_id) for p in report.problems} == {(11, "claim/TEST-01/external-only"),
                                                               (11, "claim/TEST-01/reported")}


def test_rule_12_hypothesis_cannot_support_facts_or_summaries(tmp_path):
    write(tmp_path, record("claim/TEST-01/guess", layer="HYPOTHESIS"))
    write(tmp_path, record("claim/TEST-01/fact", derived_from=["claim/TEST-01/guess"]))
    write(tmp_path, record("claim/TEST-01/summary", layer="DERIVED_SUMMARY", derived_from=["claim/TEST-01/guess"]))
    write(tmp_path, record("claim/TEST-01/guess-2", layer="HYPOTHESIS", derived_from=["claim/TEST-01/guess"]))
    report = check(tmp_path)
    assert {(p.rule, p.record_id) for p in report.problems} == {(12, "claim/TEST-01/fact"), (12, "claim/TEST-01/summary")}


@pytest.mark.parametrize("length", [2, 4])
def test_hypothesis_cannot_be_laundered_through_invalid_intermediates(tmp_path, length):
    """H -> S1 -> ... -> Sn: S1 breaks rule 12, and every later summary is invalid because its grounding is."""
    write(tmp_path, record("claim/TEST-01/guess", layer="HYPOTHESIS"))
    parent = "claim/TEST-01/guess"
    for i in range(1, length + 1):
        write(tmp_path, record(f"claim/TEST-01/s{i}", layer="DERIVED_SUMMARY", derived_from=[parent]))
        parent = f"claim/TEST-01/s{i}"
    write(tmp_path, record("claim/TEST-01/fact-on-top", derived_from=[parent]))
    report = check(tmp_path)
    expected = {(12, "claim/TEST-01/s1")} | {(6, f"claim/TEST-01/s{i}") for i in range(2, length + 1)} | {
        (6, "claim/TEST-01/fact-on-top")}
    assert {(p.rule, p.record_id) for p in report.problems} == expected
    assert "claim/TEST-01/guess" not in report.invalid_ids


def test_invalid_grounding_propagates_but_supersession_does_not(tmp_path):
    write(tmp_path, record("claim/TEST-01/broken", layer="FACT"))
    write(tmp_path, record("claim/TEST-01/summary", layer="DERIVED_SUMMARY", derived_from=["claim/TEST-01/broken"]))
    write(tmp_path, record("claim/TEST-01/replacement", supersedes=["claim/TEST-01/broken"]))
    report = check(tmp_path)
    assert report.invalid_ids == {"claim/TEST-01/broken", "claim/TEST-01/summary"}


def test_derived_from_cycle_between_valid_records_stays_deterministic(tmp_path):
    write(tmp_path, record("claim/TEST-01/a", layer="DERIVED_SUMMARY", derived_from=["claim/TEST-01/b"]))
    write(tmp_path, record("claim/TEST-01/b", layer="DERIVED_SUMMARY", derived_from=["claim/TEST-01/a"]))
    assert check(tmp_path).problems == check(tmp_path).problems == ()


@needs_git
def test_rule_13_head_blob_mismatch_and_missing_path(tmp_path):
    rev = git_repo(tmp_path)
    good = record()["evidence"][0]
    write(tmp_path, record("claim/TEST-01/changed", evidence=[dict(good, rev=rev, sha256="f" * 64)]))
    write(tmp_path, record("claim/TEST-01/missing", evidence=[dict(good, rev=rev, path="docs/absent.md")]))
    (tmp_path / SOURCE).write_bytes(b"edited but not committed\n")  # the committed blob is what counts
    write(tmp_path, record("claim/TEST-01/ok", evidence=[dict(good, rev=rev)]))
    report = check(tmp_path, use_git=True)
    assert {(p.rule, p.record_id) for p in report.problems} == {(13, "claim/TEST-01/changed"),
                                                               (13, "claim/TEST-01/missing")}


@needs_git
def test_full_history_checks_rev_and_task_commits(tmp_path):
    rev = git_repo(tmp_path)
    good = dict(record()["evidence"][0], rev=rev)
    write(tmp_path, record("claim/TEST-01/unknown-rev", evidence=[dict(good, rev="9" * 40)]))
    task = record("task/TEST-01/outcome", evidence=[good])
    task["payload"].update(merge_commit=rev, implementation_commit=rev, tree="0" * 40)
    write(tmp_path, task)
    head_only = check(tmp_path, use_git=True)
    assert head_only.ok and head_only.source_status == VERIFIED
    full = check(tmp_path, use_git=True, full_history=True)
    assert [(p.rule, p.record_id) for p in full.problems] == [(13, "task/TEST-01/outcome")]
    assert any("unknown-rev" in u for u in full.unverified)


@pytest.mark.parametrize("value", ["C:\\data\\run", "d:/runs/x", "\\\\host\\share\\x", "/srv/data/x", "see /opt/x",
                                   "~/notes/x", "file:///C:/data/x", "file:///srv/data/x", "file://host/share/x",
                                   "FILE:/srv/x", "(file:///srv/x)"])
def test_rule_14_absolute_paths(tmp_path, value):
    write(tmp_path, record(labels={"where": value}))
    report = check(tmp_path)
    assert rules(report) >= {14} and all(value not in p.message for p in report.problems)


@pytest.mark.parametrize("value", ["429/5xx", "docs/x.md", "a / b", "github:o/r/pull/1", "http://example.invalid/x",
                                   "https://example.com/x", "profile:/x is not a file uri", "and/or", "L36-L39"])
def test_rule_14_relative_text_is_not_a_path(tmp_path, value):
    write(tmp_path, record(labels={"text": value}))
    assert 14 not in rules(check(tmp_path))


def test_rule_15_secret_like_values_are_rejected_without_echo(tmp_path):
    dummy_aws = "AKIA" + "Q" * 16
    dummy_github = "ghp" + "_" + "a" * 36
    write(tmp_path, record(labels={"a": dummy_aws, "b": dummy_github}))
    report = check(tmp_path)
    assert {p.rule for p in report.problems} == {15} and len(report.problems) == 2
    assert all(dummy_aws not in p.message and dummy_github not in p.message for p in report.problems)


def test_problems_are_sorted_and_independent_of_file_order(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    recs = [record("claim/TEST-01/x", supersedes=["claim/TEST-01/y"]), record("claim/TEST-01/y", layer="FACT"),
            record("claim/TEST-01/z", derived_from=["claim/TEST-01/none"])]
    for rec in recs:
        write(a, rec)
    for rec in reversed(copy.deepcopy(recs)):
        write(b, rec)
    ra, rb = check(a), check(b)
    assert ra.problems == rb.problems and list(ra.problems) == sorted(ra.problems) and ra.problems
