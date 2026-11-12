"""AUTO-02 AC13: the workstate package imports only the standard library, storage.atomic and itself, runs
git from one Popen call without a shell, limits every git call while reading, and reaps its children."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from moneylab.workstate import collect

PACKAGE = Path(collect.__file__).resolve().parent
STDLIB_ALLOWED = {"__future__", "argparse", "collections.abc", "datetime", "hashlib", "json", "os", "pathlib", "re",
                  "shutil", "stat", "subprocess", "sys", "threading", "time", "typing"}
OWN_ALLOWED = {"moneylab.storage", "moneylab.storage.atomic", "moneylab.workstate", "moneylab.workstate.collect",
               "moneylab.workstate.store"}
FORBIDDEN_LOADED = ("moneylab.automation", "moneylab.providers", "requests", "websockets", "urllib.request",
                    "http.client", "socket")


def _modules() -> dict[str, ast.Module]:
    return {path.name: ast.parse(path.read_text(encoding="utf-8")) for path in sorted(PACKAGE.glob("*.py"))}


def test_package_has_exactly_the_planned_modules():
    assert set(_modules()) == {"__init__.py", "__main__.py", "collect.py", "store.py"}


def test_imports_are_the_allowlist_only():
    for name, tree in _modules().items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported = {node.module or ""}
            else:
                continue
            assert imported <= STDLIB_ALLOWED | OWN_ALLOWED, (name, imported)


def test_one_popen_call_no_shell_and_no_other_process_api():
    popen_calls = 0
    for name, tree in _modules().items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"system", "popen", "run", "call", "check_output", "check_call",
                                              "startfile", "spawnv", "execv"}, name
                if node.func.attr == "Popen":
                    popen_calls += 1
                    shell = [kw for kw in node.keywords if kw.arg == "shell"]
                    assert len(shell) == 1 and isinstance(shell[0].value, ast.Constant)
                    assert shell[0].value.value is False
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec", "compile", "__import__"}, name
    assert popen_calls == 1


def test_fresh_interpreter_loads_no_network_provider_or_automation_module():
    script = ("import sys, moneylab.workstate.__main__\n"
              f"print(sorted(m for m in sys.modules if m.startswith({FORBIDDEN_LOADED!r})))\n")
    out = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, check=True, timeout=120)
    assert out.stdout.strip() == b"[]"


def test_git_subcommand_allowlist():
    assert collect.GIT_SUBCOMMANDS == {"rev-parse", "status", "ls-files", "ls-tree", "cat-file", "check-ignore"}


def test_a_subcommand_outside_the_allowlist_starts_nothing(tmp_path, monkeypatch):
    started: list[object] = []
    monkeypatch.setattr(collect, "_base_argv", lambda: started.append(True) or ["git"])
    with pytest.raises(collect.WorkstateError) as info:
        collect.run_git(tmp_path, "commit", ["-m", "x"])
    assert info.value.code == "GIT_FAILED" and started == []


def _fake_git(monkeypatch, script: str) -> list[subprocess.Popen[bytes]]:
    reaped: list[subprocess.Popen[bytes]] = []
    monkeypatch.setattr(collect, "_base_argv", lambda: [sys.executable, "-B", "-c", script])
    monkeypatch.setattr(collect, "_on_reaped", reaped.append)
    return reaped


def test_git_gets_optional_locks_off_fixed_config_and_no_inherited_git_variables(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "elsewhere"))
    _fake_git(monkeypatch, "import os, sys\n"
                           "sys.stdout.write(os.environ.get('GIT_OPTIONAL_LOCKS', '') + '|' "
                           "+ str('GIT_DIR' in os.environ) + '|' + ' '.join(sys.argv[1:]))")
    code, out = collect.run_git(tmp_path, "rev-parse", ["HEAD"])
    assert code == 0
    assert out.decode() == ("0|False|-C " + str(tmp_path)
                            + " -c core.fsmonitor=false -c core.untrackedCache=false rev-parse HEAD")


@pytest.mark.parametrize("stream, attr", [("stdout", "STDOUT_LIMIT"), ("stderr", "STDERR_LIMIT")])
def test_output_over_the_limit_kills_and_reaps_the_child(tmp_path, monkeypatch, stream, attr):
    monkeypatch.setattr(collect, attr, 1000)
    reaped = _fake_git(monkeypatch, f"import sys, time\nsys.{stream}.buffer.write(b'x' * (1 << 20))\n"
                                    f"sys.{stream}.flush()\ntime.sleep(60)\n")
    with pytest.raises(collect.WorkstateError) as info:
        collect.run_git(tmp_path, "status", [])
    assert info.value.code == "LIMIT_EXCEEDED" and stream in info.value.detail
    assert len(reaped) == 1 and reaped[0].returncode is not None


def test_timeout_kills_and_reaps_the_child(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "TIMEOUT_SECONDS", 0.5)
    reaped = _fake_git(monkeypatch, "import time\ntime.sleep(60)\n")
    with pytest.raises(collect.WorkstateError) as info:
        collect.run_git(tmp_path, "status", [])
    assert info.value.code == "GIT_FAILED" and "timed out" in info.value.detail
    assert len(reaped) == 1 and reaped[0].returncode is not None


def test_unexpected_exit_code_is_git_failed(tmp_path, monkeypatch):
    reaped = _fake_git(monkeypatch, "import sys\nsys.exit(3)\n")
    with pytest.raises(collect.WorkstateError) as info:
        collect.run_git(tmp_path, "status", [])
    assert info.value.code == "GIT_FAILED" and "exited with 3" in info.value.detail
    assert len(reaped) == 1
