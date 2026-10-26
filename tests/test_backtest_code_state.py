"""Backtest code-state policy: tracked changes vs untracked files (BT-2b-2 follow-up; SYNTHETIC / NOT_EVIDENCE).

Run directories are written in tmp_path from fixture bars (test_backtest_run). The git integration test
uses a throwaway repository in tmp_path; the MoneyLab working tree is never read or changed by these tests."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from test_backtest_run import CODE, bars, make_run  # noqa: F401  (bars is a fixture)
from test_bar_export import tree_hashes

from moneylab.backtest.code_state import (
    CODE_STATE_POLICY,
    classify_worktree,
    code_state_problems,
    parse_porcelain_z,
    untracked_is_allowed,
)
from moneylab.backtest.run import verify_run
from moneylab.backtest.settings import DEFAULT_SETTINGS_FILE
from moneylab.cli import backtest_code_state

COMMIT = CODE["commit"]
DOCS = [("??", "docs/backtest_bt2_review.md"), ("??", "docs/backtest_bt2b_review.md")]


# --- parsing and classification ---------------------------------------------------------------------------

def test_parse_porcelain_z_handles_renames_and_spaces():
    text = "?? docs/review notes.md\0 M src/x.py\0R  src/new.py\0src/old.py\0M  configs/a.toml\0"
    assert parse_porcelain_z(text) == [("??", "docs/review notes.md"), (" M", "src/x.py"), ("R ", "src/new.py"),
                                       ("R ", "src/old.py"), ("M ", "configs/a.toml")]
    assert parse_porcelain_z("") == []
    with pytest.raises(ValueError):
        parse_porcelain_z("garbage\0")


@pytest.mark.parametrize("path,allowed", [
    ("docs/backtest_bt2_review.md", True),
    ("docs/sub/notes.txt", True),
    ("docs/guide.rst", True),
    ("docs/helper.py", False),         # Python code is never allowed
    ("docs/data.json", False),         # execution-relevant suffix
    ("scratch.py", False),
    ("src/moneylab/backtest/x.md", False),  # anything under src/
    ("configs/backtest_costs.toml", False),
    ("configs/notes.md", False),       # anything under configs/
    ("tests/notes.md", False),
    ("pyproject.toml", False),
    (".env", False),
    ("notes.md", False),               # outside docs/: unclassified -> blocking
    ("data.csv", False),
])
def test_untracked_policy(path, allowed):
    assert untracked_is_allowed(path) is allowed


def test_classify_separates_tracked_untracked_and_ignored():
    s = classify_worktree(COMMIT, [*DOCS, (" M", "src/a.py"), ("A ", "src/b.py"), ("??", "x.py"),
                                   ("!!", "data/raw/ignored.json")])
    assert s["policy"] == CODE_STATE_POLICY and s["status_read"] is True and s["dirty"] is True
    assert s["tracked_changes"] == ["src/a.py", "src/b.py"]
    assert s["untracked_blocking"] == ["x.py"]
    assert s["untracked_allowed"] == ["docs/backtest_bt2_review.md", "docs/backtest_bt2b_review.md"]
    docs_only = classify_worktree(COMMIT, DOCS)
    assert docs_only["dirty"] is False and code_state_problems(docs_only) == []
    assert classify_worktree(COMMIT, None)["dirty"] is None
    assert code_state_problems(classify_worktree(COMMIT, None)) == ["git status could not be read"]
    assert code_state_problems({"commit": COMMIT, "dirty": False})[0].startswith("code state has no")


# --- verify_run under the policy --------------------------------------------------------------------------

def test_review_documents_only_do_not_fail_verification(tmp_path, bars):  # noqa: F811
    state = classify_worktree(COMMIT, DOCS)
    out = make_run(bars, tmp_path / "runs-fixture", code=state)
    m = json.loads((out.dir / "manifest.json").read_text(encoding="utf-8"))
    assert m["code_state"]["untracked_allowed"] == [p for _, p in DOCS]
    assert m["code_state"]["tracked_changes"] == [] and m["code_state"]["dirty"] is False
    rep = verify_run(out.dir, code_state=state)
    assert rep.ok and "allowed untracked documents: run time 2, now 2" in rep.checks["code"]["detail"]
    rep = verify_run(out.dir, code_state=classify_worktree(COMMIT, DOCS[:1]))  # a document removed since
    assert rep.ok and "the lists differ" in rep.checks["code"]["detail"]


@pytest.mark.parametrize("extra", [("??", "scratch.py"), ("??", "src/moneylab/backtest/patch.py"),
                                   ("??", "configs/backtest_costs_alt.toml"), ("??", "notes.md")])
def test_untracked_execution_files_fail_now_and_at_run_time(tmp_path, bars, extra):  # noqa: F811
    bad = classify_worktree(COMMIT, [*DOCS, extra])
    out = make_run(bars, tmp_path / "runs-fixture")
    rep = verify_run(out.dir, code_state=bad)
    assert rep.checks["code"]["ok"] is False and not rep.ok
    assert f"now: untracked files that can affect execution: {extra[1]}" in rep.checks["code"]["detail"]
    out2 = make_run(bars, tmp_path / "runs2-fixture", code=bad)
    rep = verify_run(out2.dir, code_state=classify_worktree(COMMIT, DOCS))
    assert rep.checks["code"]["ok"] is False and "run time: untracked files" in rep.checks["code"]["detail"]
    assert rep.checks["reproducibility"]["ok"] is True  # only the code check fails


@pytest.mark.parametrize("xy", [" M", "M ", "MM", " D", "A "])
def test_tracked_changes_fail(tmp_path, bars, xy):  # noqa: F811
    out = make_run(bars, tmp_path / "runs-fixture")
    rep = verify_run(out.dir, code_state=classify_worktree(COMMIT, [(xy, "src/moneylab/backtest/portfolio.py")]))
    assert rep.checks["code"]["ok"] is False and "now: tracked changes" in rep.checks["code"]["detail"]


def test_commit_change_fails(tmp_path, bars):  # noqa: F811
    out = make_run(bars, tmp_path / "runs-fixture", code=classify_worktree(COMMIT, DOCS))
    rep = verify_run(out.dir, code_state=classify_worktree("b" * 40, DOCS))
    assert rep.checks["code"]["ok"] is False and "!= run commit" in rep.checks["code"]["detail"]


def test_settings_change_fails_in_settings_and_code(tmp_path, bars):  # noqa: F811
    s = tmp_path / "costs.toml"
    s.write_bytes(DEFAULT_SETTINGS_FILE.read_bytes())
    out = make_run(bars, tmp_path / "runs-fixture", settings_file=s)
    s.write_bytes(s.read_bytes().replace(b"# MoneyLab", b"# Changed MoneyLab", 1))
    rep = verify_run(out.dir, code_state=CODE)  # a settings file outside the repository: the hash catches it
    assert rep.checks["settings"]["ok"] is False and rep.checks["code"]["ok"] is True and not rep.ok
    # the repository settings file edited after the run is a tracked change as well
    rep = verify_run(out.dir, code_state=classify_worktree(COMMIT, [(" M", "configs/backtest_costs.toml")]))
    assert rep.checks["code"]["ok"] is False and "configs/backtest_costs.toml" in rep.checks["code"]["detail"]


def test_clean_run_reverifies_without_writing(tmp_path, bars):  # noqa: F811
    out = make_run(bars, tmp_path / "runs-fixture", code=classify_worktree(COMMIT, DOCS))
    before = tree_hashes(tmp_path / "runs-fixture")
    for _ in range(2):
        rep = verify_run(out.dir, code_state=classify_worktree(COMMIT, DOCS))
        assert rep.ok and all(c["ok"] is not False for c in rep.checks.values())
    assert tree_hashes(tmp_path / "runs-fixture") == before


# --- the CLI helper against a throwaway git repository -----------------------------------------------------

@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_backtest_code_state_reads_a_real_repository(tmp_path):
    repo = tmp_path / "repo"
    hooks = tmp_path / "no-hooks"
    (repo / "src").mkdir(parents=True)
    hooks.mkdir()

    def git(*args):
        subprocess.run(["git", "-c", f"core.hooksPath={hooks}", "-c", "commit.gpgsign=false", "-c", "user.name=t",
                        "-c", "user.email=t@example.invalid", *args], cwd=repo, check=True, capture_output=True)

    git("init", "-q")
    (repo / "src" / "m.py").write_text("x = 1\n", encoding="utf-8")
    (repo / ".gitignore").write_text("data/\n", encoding="utf-8")
    git("add", "src/m.py", ".gitignore")
    git("commit", "-q", "-m", "init")
    s = backtest_code_state(repo)
    assert len(s["commit"]) == 40 and s["dirty"] is False and s["status_read"] is True

    (repo / "docs" / "sub").mkdir(parents=True)
    (repo / "docs" / "review notes.md").write_text("review\n", encoding="utf-8")
    (repo / "docs" / "sub" / "검토.md").write_text("review\n", encoding="utf-8")
    (repo / "data").mkdir()
    (repo / "data" / "ignored.json").write_text("{}\n", encoding="utf-8")
    s = backtest_code_state(repo)
    assert s["dirty"] is False and s["untracked_allowed"] == ["docs/review notes.md", "docs/sub/검토.md"]

    (repo / "src" / "extra.py").write_text("y = 2\n", encoding="utf-8")
    s = backtest_code_state(repo)
    assert s["dirty"] is True and s["untracked_blocking"] == ["src/extra.py"] and s["tracked_changes"] == []

    (repo / "src" / "extra.py").unlink()
    (repo / "src" / "m.py").write_text("x = 2\n", encoding="utf-8")
    s = backtest_code_state(repo)
    assert s["dirty"] is True and s["tracked_changes"] == ["src/m.py"] and s["untracked_blocking"] == []


def test_backtest_code_state_outside_a_repository(tmp_path):
    s = backtest_code_state(tmp_path)
    assert s["commit"] is None and s["status_read"] is False and s["dirty"] is None
    assert "commit unknown" in code_state_problems(s)
