"""AUTO-01 isolation (D5/D7/D8): no Guard import at runtime, no network/trading/wallet imports, no shell or file
writes, real `knowledge_validate` run leaves tracked and untracked files unchanged. Regression tests, not a sandbox;
git status comparison is reference evidence, not proof of file-system isolation."""

from __future__ import annotations

import ast
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from test_knowledge_validate import needs_git

from moneylab.automation import evidence, executor, policy

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "moneylab"
PACKAGE = sorted((SRC / "automation").glob("*.py"))

STDLIB = {"__future__", "dataclasses", "hashlib", "json", "os", "pathlib", "re", "shutil", "subprocess", "sys",
          "threading", "time", "typing"}
NETWORK_OR_TRADING = ("socket", "ssl", "http", "urllib", "requests", "httpx", "aiohttp", "websocket", "websockets",
                      "importlib", "ctypes", "jwt", "hmac", "web3", "eth_account", "py_clob_client",
                      "moneylab.core.http", "moneylab.providers", "moneylab.execution", "moneylab.paper",
                      "moneylab.recording", "moneylab.supervisor", "moneylab.knowledge")
FORBIDDEN_CALLS = {"open", "eval", "exec", "compile", "__import__", "input", "breakpoint"}
FORBIDDEN_ATTRS = {"system", "popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput",
                   "startfile", "write_text", "write_bytes", "mkdir", "unlink", "touch", "rename", "replace", "rmdir",
                   "remove", "spawnv", "execv"}


def _imports(path: Path) -> set[str]:
    mods = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module or "")
    return mods


def test_package_has_exactly_the_allowed_modules():
    assert [p.name for p in PACKAGE] == ["__init__.py", "evidence.py", "executor.py", "policy.py"]


@pytest.mark.parametrize("path", PACKAGE, ids=lambda p: p.name)
def test_imports_are_stdlib_allowlist_or_own_package(path):
    bad = {m for m in _imports(path) if m not in STDLIB and m != "moneylab.automation"
           and not m.startswith("moneylab.automation.")}
    assert bad == set()
    assert not {m for m in _imports(path) if any(m == f or m.startswith(f + ".") for f in NETWORK_OR_TRADING)}


@pytest.mark.parametrize("path", PACKAGE, ids=lambda p: p.name)
def test_no_guard_shell_dynamic_execution_or_file_writes(path):
    text = path.read_text(encoding="utf-8")
    assert ".claude" not in text and "guard.py" not in text
    problems = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            problems.append(node.func.id)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_ATTRS:
                problems.append(node.func.attr)
            if node.func.attr == "Popen":
                shell = [k for k in node.keywords if k.arg == "shell"]
                assert len(shell) == 1 and isinstance(shell[0].value, ast.Constant) and shell[0].value.value is False
                assert not any(k.arg is None for k in node.keywords)  # no **kwargs
                assert isinstance(node.args[0], ast.Name) and node.args[0].id == "argv"
    assert problems == []


def test_exactly_one_popen_call_in_the_package():
    calls = [n for p in PACKAGE for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "Popen"]
    assert len(calls) == 1


def test_registered_action_is_offline_by_its_imports():
    """The knowledge validator (the only action) imports no network, provider or trading code."""
    for path in sorted((SRC / "knowledge").glob("*.py")):
        net = {m for m in _imports(path) if any(m == f or m.startswith(f + ".") for f in NETWORK_OR_TRADING[:8]
                                                + ("moneylab.core.http", "moneylab.providers", "moneylab.execution"))}
        assert net == set(), path.name


SCRIPT = """
import json, sys
import moneylab.automation as a
doc = json.loads(a.run_action("not_registered"))
guard = sorted(n for n, m in list(sys.modules.items())
               if (getattr(m, "__file__", None) or "").replace("\\\\", "/").endswith(".claude/hooks/guard.py"))
prefixes = json.loads(sys.argv[1])
loaded = sorted(m for m in sys.modules if any(m == p or m.startswith(p + ".") for p in prefixes))
print(json.dumps({"status": doc["status"], "guard": guard, "loaded": loaded}))
"""


def test_fresh_interpreter_loads_no_guard_network_or_trading_module():
    prefixes = ["ssl", "http", "urllib", "requests", "moneylab.core.http", "moneylab.providers", "moneylab.execution",
                "moneylab.paper", "moneylab.recording", "moneylab.supervisor", "moneylab.knowledge", "moneylab_guard"]
    proc = subprocess.run([sys.executable, "-c", SCRIPT, json.dumps(prefixes)], capture_output=True, check=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=60)
    assert json.loads(proc.stdout) == {"status": "DENIED", "guard": [], "loaded": []}


def _git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, check=True, timeout=60).stdout


def _tripwire(*args, **kwargs):
    raise AssertionError("network capability used by the automation process")


@needs_git
def test_real_knowledge_validate_matches_a_direct_run_and_changes_nothing(monkeypatch):
    before = (_git("status", "--porcelain=v1", "-uall", "-z"), _git("diff", "--name-only", "-z"),
              _git("rev-parse", "HEAD"))
    with monkeypatch.context() as m:
        for name in ("socket", "create_connection", "getaddrinfo"):
            m.setattr(socket, name, _tripwire)
        text = executor.run_action("knowledge_validate")
    doc = json.loads(text)
    evidence.check(doc)
    assert text == evidence.canonical_json(doc)
    assert doc["action_id"] == "knowledge_validate" and doc["decision"] == "ALLOW"
    assert doc["status"] in ("SUCCEEDED", "VALIDATION_FAILED", "SOURCE_UNVERIFIED")
    assert doc["status"] == policy.status_for_exit_code(doc["exit_code"])
    # the same fixed argv/env run directly is observed to give the same exit code and output hashes
    root = policy.repo_root()
    direct = subprocess.run(policy.build_argv(root), cwd=root, env=policy.build_env(), capture_output=True,
                            stdin=subprocess.DEVNULL, timeout=60)
    assert doc["exit_code"] == direct.returncode
    assert doc["stdout_sha256"] == evidence.sha256_hex(direct.stdout)
    assert doc["stderr_sha256"] == evidence.sha256_hex(direct.stderr)
    after = (_git("status", "--porcelain=v1", "-uall", "-z"), _git("diff", "--name-only", "-z"),
             _git("rev-parse", "HEAD"))
    assert after == before
