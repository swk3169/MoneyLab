"""AUTO-01 policy: fixed allowlist, fixed argv, minimal environment, git path, Guard compatibility (D1/D2/D4/D5)."""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from test_knowledge_validate import needs_git

from moneylab.automation import policy
from moneylab.automation.policy import AutomationError

REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "src" / "moneylab" / "automation"
GUARD_PATH = REPO / ".claude" / "hooks" / "guard.py"


def _load_guard():
    """Same importlib loading as tests/test_agent_guard.py, under its own module name."""
    spec = importlib.util.spec_from_file_location("moneylab_guard_auto01", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Str(str):
    pass


def test_only_knowledge_validate_is_registered():
    assert policy.ALLOWED_ACTIONS == frozenset({"knowledge_validate"})
    assert isinstance(policy.ALLOWED_ACTIONS, frozenset)
    assert policy.decide("knowledge_validate") == "ALLOW"


@pytest.mark.parametrize("action_id", [
    "", "Knowledge_validate", "KNOWLEDGE_VALIDATE", " knowledge_validate", "knowledge_validate ", "knowledge_validate\n",
    "knowledge_validate --full-history", "knowledge_validate; rm -rf .", "knowledge_validate && git push",
    "knowledge.validate", "supervisor_check", "automation_selftest", "python -m moneylab.knowledge validate",
    "knowledge_validate\x00", "ｋnowledge_validate", None, 1, b"knowledge_validate", ["knowledge_validate"],
    _Str("knowledge_validate"),
])
def test_everything_else_is_denied(action_id):
    assert policy.decide(action_id) == "DENY"


@pytest.mark.parametrize("code, status", [
    (0, "SUCCEEDED"), (1, "VALIDATION_FAILED"), (3, "SOURCE_UNVERIFIED"), (2, "UNEXPECTED_EXIT"),
    (4, "UNEXPECTED_EXIT"), (-9, "UNEXPECTED_EXIT"), (255, "UNEXPECTED_EXIT"), (0xC000013A, "UNEXPECTED_EXIT"),
])
def test_exit_code_mapping(code, status):
    assert policy.status_for_exit_code(code) == status


@pytest.mark.parametrize("code", [True, False, 0.0, "0", None])
def test_exit_code_must_be_a_plain_int(code):
    with pytest.raises(AutomationError):
        policy.status_for_exit_code(code)


def test_repo_root_is_this_checkout():
    root = policy.repo_root()
    assert root.is_absolute() and root == REPO
    assert (root / "src" / "moneylab" / "automation").resolve() == PACKAGE.resolve()


def test_argv_is_fixed():
    root = policy.repo_root()
    argv = policy.build_argv(root)
    assert argv == [sys.executable, "-m", "moneylab.knowledge", "--root", str(root), "validate"]
    assert "--full-history" not in argv
    assert os.path.isabs(argv[0]) and os.path.isabs(argv[4])
    assert all(type(a) is str for a in argv)


def test_interpreter_must_be_an_existing_absolute_file(monkeypatch):
    for bad in ("", "python", str(REPO / "no-such-python.exe")):
        monkeypatch.setattr(policy.sys, "executable", bad)
        with pytest.raises(AutomationError):
            policy.build_argv(REPO)


@needs_git
def test_env_is_a_minimal_allowlist_with_git(monkeypatch):
    monkeypatch.setenv("MONEYLAB_AUTO01_CANARY", "do-not-inherit")
    monkeypatch.setenv("PYTHONPATH", "do-not-inherit")
    env = policy.build_env()
    expected = {"PATH", "SYSTEMROOT"} if os.name == "nt" else {"PATH"}
    assert set(env) == expected
    assert "do-not-inherit" not in env.values()
    assert env["PATH"] == os.path.dirname(os.path.abspath(shutil.which("git")))
    assert os.pathsep not in env["PATH"]  # one directory, not the inherited search path
    found = shutil.which("git", path=env["PATH"])
    assert found is not None
    assert subprocess.run([found, "--version"], capture_output=True, env=env, timeout=30).returncode == 0
    if os.name == "nt":
        assert env["SYSTEMROOT"] == os.environ["SYSTEMROOT"]


def test_missing_git_stops(monkeypatch):
    monkeypatch.setattr(policy.shutil, "which", lambda name: None)
    with pytest.raises(AutomationError, match="git"):
        policy.build_env()


@pytest.mark.skipif(os.name != "nt", reason="SYSTEMROOT is Windows only")
def test_missing_systemroot_stops(monkeypatch):
    monkeypatch.delenv("SYSTEMROOT", raising=False)
    with pytest.raises(AutomationError, match="SYSTEMROOT"):
        policy.build_env()


def test_no_windows_path_is_hardcoded():
    for path in sorted(PACKAGE.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\b[A-Za-z]:[\\/]", text), path.name
        assert "Program Files" not in text and ".venv" not in text, path.name


# D5: Guard compatibility of the fixed command, loaded the existing way (importlib) in tests only.

def test_guard_passes_the_fixed_command():
    guard = _load_guard()
    argv = policy.build_argv(policy.repo_root())
    for command in (subprocess.list2cmdline(argv), " ".join(argv), " ".join(a.replace("\\", "/") for a in argv)):
        decision = guard.check_command(command, REPO, str(REPO))
        assert decision.action == guard.PASS, (command, decision)
        payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(REPO)}
        assert guard.decide(payload, REPO).action == guard.PASS


def test_guard_still_stops_the_forbidden_variant():
    """The check above is meaningful: Guard does flag a dangerous neighbour of the fixed command."""
    guard = _load_guard()
    argv = policy.build_argv(policy.repo_root())
    assert guard.check_command(subprocess.list2cmdline(argv) + " && git push --force", REPO).action == guard.DENY
