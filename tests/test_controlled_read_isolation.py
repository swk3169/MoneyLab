"""AUTO-08 D1 isolation: the package imports only the standard library, its own modules and the reused
workstate.collect / storage.atomic functions; it never loads automation, runlog or providers; it starts no
process of its own; its serialization is exactly json.dumps with the D14 arguments."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from moneylab.controlled_read import store

PACKAGE = Path(store.__file__).resolve().parent
STDLIB_ALLOWED = {"__future__", "collections.abc", "dataclasses", "datetime", "hashlib", "json", "os", "pathlib",
                  "re", "sys", "time", "typing"}
OWN_ALLOWED = {"moneylab.controlled_read", "moneylab.controlled_read.profiles", "moneylab.controlled_read.selector",
               "moneylab.controlled_read.store", "moneylab.controlled_read.transcript",
               "moneylab.storage.atomic", "moneylab.workstate", "moneylab.workstate.collect"}
FORBIDDEN_LOADED = ("moneylab.automation", "moneylab.runlog", "moneylab.providers", "requests", "websockets",
                    "urllib.request", "http.client", "socket")


def _modules() -> dict[str, ast.Module]:
    return {path.name: ast.parse(path.read_text(encoding="utf-8")) for path in sorted(PACKAGE.glob("*.py"))}


def test_package_has_exactly_the_planned_modules():
    assert set(_modules()) == {"__init__.py", "__main__.py", "profiles.py", "selector.py", "transcript.py",
                               "store.py"}


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


def test_no_process_eval_or_delete_api_in_the_package():
    for name, tree in _modules().items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner = node.func.value.id if isinstance(node.func.value, ast.Name) else None
                if owner in {"os", "shutil", "subprocess"}:
                    assert node.func.attr not in {"remove", "replace", "rename", "run", "call"}, (name, owner)
                assert node.func.attr not in {"Popen", "system", "popen", "check_output", "check_call", "startfile",
                                              "spawnv", "execv", "rmdir", "unlink", "scandir", "listdir", "rmtree",
                                              "iterdir", "glob"}, (name, node.func.attr)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec", "compile", "__import__"}, name


def test_only_rev_parse_and_check_ignore_are_requested():
    calls = set()
    for tree in _modules().values():
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run_git"
                    and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)):
                calls.add(node.args[1].value)
    assert calls == {"rev-parse", "check-ignore"}


def test_fresh_interpreter_loads_no_automation_runlog_provider_or_network_module():
    script = ("import sys, moneylab.controlled_read.__main__\n"
              f"print(sorted(m for m in sys.modules if m.startswith({FORBIDDEN_LOADED!r})))\n")
    out = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, check=True, timeout=120)
    assert out.stdout.strip() == b"[]"


@pytest.mark.parametrize("obj", [
    {"b": 1, "a": [1, 2.5, None, True], "c": {"z": "\N{LATIN SMALL LETTER E WITH ACUTE}\N{HIRAGANA LETTER A}\U0001f600", "y": "line\nbreak"}},
    {"schema": "x", "values": {"sha256": "0" * 64, "bytes": 0, "lf": 0}},
    [],
])
def test_serialization_is_json_dumps_with_the_d14_arguments(obj):
    expected = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n"
    assert store.canonical_bytes(obj) == expected.encode("utf-8")


def test_serialization_rejects_non_finite_numbers():
    with pytest.raises(ValueError):
        store.canonical_bytes({"x": float("nan")})
