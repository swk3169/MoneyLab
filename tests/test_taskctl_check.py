"""taskctl checks: scope, protected paths, HEAD, hashes, state changes, step conditions and boundaries
(GOV-AUTOMATION-03 D6, D8)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from test_taskctl_cli import (
    CHECKS,
    N1,
    Taskctl,
    implement,
    make_repo,
    needs_git,
    sha,
    taskctl_templates,  # noqa: F401  (autouse: checks the shared templates after each test)
    to_setup_done,
)

import moneylab.taskctl as taskctl_pkg

PKG = Path(taskctl_pkg.__file__).parent


@pytest.fixture
def env(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    to_setup_done(repo, base, c1, tc)
    return repo, tc


@needs_git
def test_read_only_check_codes(env):
    repo, tc = env
    assert tc("check", "--read-only", "--phase", "SETUP_DONE")["code"] == "OK"
    repo.write("src/pkg/new.py", "x\n")  # allowed path but outside a step: the state changed
    assert tc("check", "--read-only", "--phase", "SETUP_DONE")["code"] == "STATE_CHANGED"
    (repo.root / "src/pkg/new.py").unlink()
    repo.write("src/pkg/other.py", "x\n")
    assert tc("check", "--read-only", "--phase", "SETUP_DONE")["code"] == "UNTRACKED"
    (repo.root / "src/pkg/other.py").unlink()
    repo.write("src/pkg/__init__.py", "changed\n")
    assert tc("check", "--read-only", "--phase", "SETUP_DONE")["code"] == "OUT_OF_SCOPE"
    repo.git("checkout", "--", "src/pkg/__init__.py")
    repo.write("docs/tasks/OTHER/WORK_ORDER.md", "edited\n")
    assert tc("check", "--read-only", "--phase", "SETUP_DONE")["code"] == "PROTECTED_CHANGED"
    repo.git("checkout", "--", "docs/tasks/OTHER/WORK_ORDER.md")
    repo.write("README.md", "x\n")
    repo.commit("README.md", message="unexpected")
    assert tc("check", "--read-only", "--phase", "SETUP_DONE")["code"] == "HEAD_MISMATCH"


@needs_git
def test_implement_may_change_allowed_files_but_check_steps_may_not(env):
    repo, tc = env
    assert tc.start("IMPLEMENT")["code"] == "OK"
    implement(repo)
    assert tc.end("IMPLEMENT")["code"] == "OK"
    assert tc.start("TEST_TARGETED")["code"] == "OK"
    repo.write("src/pkg/new.py", "changed by a check\n")
    assert tc.end("TEST_TARGETED")["code"] == "STATE_CHANGED"
    assert tc.end("TEST_TARGETED", "fail", N1, "--failure-sig", "1" * 64)["code"] == "OK"


@needs_git
def test_implement_rejects_out_of_scope_and_staged_changes(env):
    repo, tc = env
    assert tc.start("IMPLEMENT")["code"] == "OK"
    repo.write("src/pkg/__init__.py", "outside\n")
    assert tc.end("IMPLEMENT")["code"] == "OUT_OF_SCOPE"
    repo.git("checkout", "--", "src/pkg/__init__.py")
    implement(repo)
    repo.git("add", "--", "README.md")
    assert tc.end("IMPLEMENT")["code"] == "NOT_CLEAN"
    repo.git("reset", "-q", "--", "README.md")
    assert tc.end("IMPLEMENT")["code"] == "OK"


@needs_git
def test_state_change_between_steps_is_refused(env):
    repo, tc = env
    tc.run_step("IMPLEMENT", lambda: implement(repo))
    repo.write("src/pkg/new.py", "edited outside any step\n")
    assert tc.start("TEST_TARGETED")["code"] == "STATE_CHANGED"


@needs_git
def test_check_step_needs_a_delegation_command_hash(env):
    _, tc = env
    out = tc("step", "start", "--step", "LINT", "--session-nonce", N1, "--input-sha256", sha("rm -rf /"))
    assert out["code"] == "CONTRACT_MISMATCH"
    out = tc("step", "start", "--step", "LINT", "--session-nonce", N1, "--input-sha256", sha(CHECKS["LINT"]))
    assert out["code"] == "OK"


@needs_git
def test_local_commit_must_match_w_audit(env):
    repo, tc = env
    tc.run_step("IMPLEMENT", lambda: implement(repo))
    tc.run_step("LOCAL_AUDIT")
    assert tc.start("LOCAL_COMMIT")["code"] == "OK"
    repo.write("README.md", "different content\n")
    repo.commit("src/pkg/new.py", "README.md", message="impl")
    assert tc.end("LOCAL_COMMIT")["code"] == "HASH_MISMATCH"


@needs_git
def test_local_commit_with_a_missing_file_is_refused(env):
    repo, tc = env
    tc.run_step("IMPLEMENT", lambda: implement(repo))
    tc.run_step("LOCAL_AUDIT")
    tc.start("LOCAL_COMMIT")
    repo.commit("src/pkg/new.py", message="partial")
    assert tc.end("LOCAL_COMMIT")["code"] in ("HASH_MISMATCH", "NOT_CLEAN")


@needs_git
def test_setup_env_rejects_unexpected_ignored_entries(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    assert tc.init(base, c1)["code"] == "OK"
    tc.start("SETUP_ENV")
    (repo.root / ".venv").mkdir()
    repo.write("data/processed/other/x.json", "{}")
    assert tc.end("SETUP_ENV")["code"] == "IGNORED_UNEXPECTED"
    (repo.root / "data/processed/other/x.json").unlink()
    (repo.root / "data/processed/other").rmdir()
    assert tc.end("SETUP_ENV")["code"] == "OK"


@needs_git
def test_work_order_change_after_delegation_is_a_contract_mismatch(env):
    repo, tc = env
    repo.write("docs/tasks/PILOT-X/WORK_ORDER.md", "rewritten\n")
    assert tc("check", "--read-only", "--phase", "SETUP_DONE")["code"] == "PROTECTED_CHANGED"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_boundaries_no_providers_network_or_own_processes():
    modules = sorted(PKG.glob("*.py"))
    assert {p.name for p in modules} == {"__init__.py", "__main__.py", "check.py", "lease.py", "ledger.py"}
    for path in modules:
        names = _imports(path)
        assert not any(n.startswith("moneylab.providers") for n in names), path.name
        assert not names & {"subprocess", "socket", "urllib", "urllib.request", "http.client", "requests",
                            "shutil", "ctypes", "importlib"}, path.name
    check_names = _imports(PKG / "check.py")
    assert "moneylab.workstate.collect" in check_names  # git only through run_git
