"""AUTO-03 AC6 (D7, D8, D21): the runlog package never runs an action and starts no process of its own.
Static checks plus a tripwire; regression tests, not a sandbox. Importing moneylab.automation loads the
executor module through the package initializer: that indirect load is expected and documented here."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from moneylab.automation import evidence as ev
from moneylab.automation import executor, policy
from moneylab.runlog import store as rl

REPO = Path(__file__).resolve().parents[1]
PACKAGE = sorted((REPO / "src" / "moneylab" / "runlog").glob("*.py"))
STDLIB = {"__future__", "argparse", "hashlib", "json", "math", "os", "re", "stat", "sys", "pathlib", "typing"}
ALLOWED_FROM = {
    "moneylab.automation": {"evidence"},
    "moneylab.automation.policy": {"EXIT_STATUS"},
    "moneylab.storage": {"atomic"},
    "moneylab.workstate": {"collect"},
    "moneylab.runlog": {"store", "load_evidence", "store_evidence"},
    "moneylab.runlog.store": {"ARGUMENT_INVALID", "ENVIRONMENT_INVALID", "INPUT_UNAVAILABLE", "RunlogError",
                              "load_evidence", "store_evidence"},
}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "input", "breakpoint"}
FORBIDDEN_ATTRS = {"system", "popen", "Popen", "run", "call", "check_call", "check_output", "startfile",
                   "spawnv", "execv", "run_action", "_execute"}
TASK = "T-1"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def test_package_has_exactly_the_allowed_modules():
    assert [p.name for p in PACKAGE] == ["__init__.py", "__main__.py", "store.py"]


@pytest.mark.parametrize("path", PACKAGE, ids=lambda p: p.name)
def test_imports_are_the_stdlib_allowlist_or_the_named_moneylab_names(path):
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            assert {a.name for a in node.names} <= STDLIB, path.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = {a.name for a in node.names}
            if module in STDLIB:
                continue
            assert module in ALLOWED_FROM and names <= ALLOWED_FROM[module], (path.name, module, names)


@pytest.mark.parametrize("path", PACKAGE, ids=lambda p: p.name)
def test_no_executor_shell_process_or_dynamic_execution(path):
    text = path.read_text(encoding="utf-8")
    assert "subprocess" not in text and ".claude" not in text and "guard.py" not in text
    assert "run_action" not in text and "import executor" not in text and "automation.executor" not in text
    problems = []
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                problems.append(node.func.id)
            if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_ATTRS:
                problems.append(node.func.attr)
    assert problems == []


def test_d6_status_table_matches_the_policy():
    assert rl.UNEXPECTED_EXIT == policy.UNEXPECTED_EXIT
    assert rl.NO_EXIT_CODE == (policy.TIMEOUT, policy.OUTPUT_LIMIT_EXCEEDED)
    assert rl.EXIT_STATUS is policy.EXIT_STATUS
    assert policy.EXIT_STATUS == {0: policy.SUCCEEDED, 1: policy.VALIDATION_FAILED, 3: policy.SOURCE_UNVERIFIED}
    for code, status in policy.EXIT_STATUS.items():
        good = json.loads(ev.executed("knowledge_validate", status, code, 1, b"", b""))
        assert rl.consistency_problem(good) is None
        for other in (0, 1, 3, 2):
            if other != code:
                assert rl.consistency_problem({**good, "exit_code": other}) is not None


def test_status_table_is_not_changed_by_use(tmp_path):
    before = dict(policy.EXIT_STATUS)
    rl.parse_evidence(ev.executed("knowledge_validate", "SUCCEEDED", 0, 1, b"", b"").encode())
    assert policy.EXIT_STATUS == before


def test_round_trip_never_calls_the_executor(tmp_path, monkeypatch):
    def tripwire(*args, **kwargs):
        raise AssertionError("an action was run")

    monkeypatch.setattr(executor, "run_action", tripwire)
    monkeypatch.setattr(executor, "_execute", tripwire)
    monkeypatch.setattr(policy, "build_argv", tripwire)
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@example.invalid"],
                 ["config", "user.name", "T"], ["config", "commit.gpgsign", "false"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)
    (repo / ".gitignore").write_bytes(b"data/processed/*\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True, env=env)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True, capture_output=True, env=env)
    raw = ev.executed("knowledge_validate", "SUCCEEDED", 0, 1, b"", b"").encode()
    stored = rl.store_at(repo, TASK, raw)
    assert stored["status"] == "STORED"
    assert rl.show_at(repo, TASK, stored["record_id"])["status"] == "FOUND"


def test_fresh_import_loads_the_executor_only_through_the_package_initializer():
    code = ("import sys\nimport moneylab.runlog.__main__\n"
            "print(sorted(m for m in sys.modules if m.startswith('moneylab')))\n"
            "print(any(m.split('.')[0] in ('socket', 'ssl', 'requests', 'urllib3', 'http') for m in sys.modules))\n")
    out = subprocess.run([sys.executable, "-B", "-I", "-c", code], capture_output=True, check=True,
                         timeout=120).stdout.decode().splitlines()
    loaded = set(json.loads(out[0].replace("'", '"')))
    assert "moneylab.automation.executor" in loaded  # indirect load via moneylab/automation/__init__.py
    assert not any(m.startswith(("moneylab.providers", "moneylab.execution", "moneylab.knowledge"))
                   for m in loaded)
    assert out[1] == "False"
