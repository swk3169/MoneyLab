"""Supervisor execution isolation (SUPERVISOR-01, T17-T20 of the Work Order).

Boundary A, the Supervisor package itself, has no shell, network, file-write, worker or trading capability. Boundary
B, the existing knowledge validator's read-only git calls inside `open_knowledge_base`, is a separate, already reviewed
boundary: these tests open the KnowledgeBase before any tripwire and do not count its git calls as Supervisor
capability. These are regression tests, not a sandbox."""

from __future__ import annotations

import ast
import builtins
import json
import multiprocessing
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from test_knowledge_validate import needs_git
from test_supervisor_proposal import OPEN, REQ, as_bytes, by_key, make_repo, open_kb, run_cli

from moneylab.supervisor import check_proposal, propose, validate_proposal

pytestmark = needs_git

SRC = Path(__file__).resolve().parents[1] / "src" / "moneylab"
SUPERVISOR = sorted((SRC / "supervisor").glob("*.py"))

STDLIB = {"__future__", "json", "hashlib", "re", "typing"}
MAIN_ONLY_STDLIB = {"argparse", "sys", "pathlib"}
KNOWLEDGE_NAMES = {
    "moneylab.knowledge": {"REPO_ROOT", "KnowledgeBase", "ContextRequestError", "open_knowledge_base",
                           "resolve_context"},
    "moneylab.knowledge.context": {"normalize_request", "REQUEST_INVALID", "REPOSITORY_UNTRUSTED", "PACKET_SCHEMA"},
    "moneylab.knowledge.query": {"KnowledgeStateError"},
    "moneylab.knowledge.model": {"CONTEXT_BOUNDARY", "canonical_json"},
}
MAIN_ONLY_NAMES = {"open_knowledge_base"}
FORBIDDEN_CALLS = {"open", "eval", "exec", "compile", "__import__", "breakpoint", "input"}
FORBIDDEN_ATTRIBUTE_CALLS = {"write_text", "write_bytes", "mkdir", "unlink", "touch", "rename", "replace", "rmdir"}
SYS_ATTRIBUTES = {"stdin", "stdout", "stderr", "exit", "argv"}
FORBIDDEN_MODULES = ("moneylab.execution", "moneylab.paper", "moneylab.providers", "moneylab.recording",
                     "moneylab.core.http", "moneylab.sizing", "moneylab.risk", "moneylab.research", "moneylab.backtest",
                     "moneylab.scanner", "moneylab.strategy")


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _import_problems(path: Path) -> list[str]:
    main = path.name == "__main__.py"
    stdlib = STDLIB | (MAIN_ONLY_STDLIB if main else set())
    problems = []
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            problems += [a.name for a in node.names if a.name not in stdlib]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in stdlib or module == "moneylab.supervisor" or module.startswith("moneylab.supervisor."):
                continue
            allowed = KNOWLEDGE_NAMES.get(module, set()) - (set() if main else MAIN_ONLY_NAMES)
            problems += [f"{module}.{a.name}" for a in node.names if a.name not in allowed or a.name.startswith("_")]
    return problems


def _call_problems(path: Path) -> list[str]:
    problems = []
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                problems.append(f"call {node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_ATTRIBUTE_CALLS:
                problems.append(f"call .{node.func.attr}")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "sys" \
                and node.attr not in SYS_ATTRIBUTES:
            problems.append(f"sys.{node.attr}")
    return problems


# T17 capability absence, statically

def test_t17_the_package_has_the_expected_modules():
    assert [p.name for p in SUPERVISOR] == ["__init__.py", "__main__.py", "proposal.py"]


@pytest.mark.parametrize("path", SUPERVISOR, ids=lambda p: p.name)
def test_t17_imports_are_on_the_allowlist(path):
    assert _import_problems(path) == []


@pytest.mark.parametrize("path", SUPERVISOR, ids=lambda p: p.name)
def test_t17_no_dynamic_execution_file_writes_or_sys_access(path):
    assert _call_problems(path) == []


def test_t17_the_checks_catch_violations(tmp_path):
    bad = tmp_path / "proposal.py"
    bad.write_text("import os\nimport subprocess\nfrom moneylab.knowledge.query import _x\n"
                   "from moneylab.knowledge import open_knowledge_base\nimport sys\n"
                   "open('f', 'w')\nexec('1')\nPath('x').write_text('y')\nsys.modules\n", encoding="utf-8")
    assert _import_problems(bad) == ["os", "subprocess", "moneylab.knowledge.query._x",
                                     "moneylab.knowledge.open_knowledge_base", "sys"]
    assert sorted(_call_problems(bad)) == ["call .write_text", "call exec", "call open", "sys.modules"]


def test_t17_knowledge_does_not_import_the_supervisor():
    for path in sorted((SRC / "knowledge").glob("*.py")):
        for node in ast.walk(_tree(path)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            assert not [n for n in names if n.startswith("moneylab.supervisor")], path.name


# T18 runtime tripwire around the Supervisor (boundary A only)

def _tripwire(*args, **kwargs):
    raise AssertionError("the Supervisor attempted a forbidden capability")


@pytest.fixture(scope="module")
def repo(tmp_path_factory) -> Path:
    return make_repo(tmp_path_factory.mktemp("iso") / "repo")


def test_t18_supervisor_runs_with_shell_network_files_and_workers_disabled(repo, monkeypatch):
    kb = open_kb(repo)  # boundary B: read-only git validation happens here, before the tripwire
    with monkeypatch.context() as m:
        for target, name in ((subprocess, "Popen"), (os, "system"), (os, "popen"), (socket, "socket"),
                             (socket, "create_connection"), (builtins, "open"), (threading.Thread, "start"),
                             (multiprocessing.Process, "start")):
            m.setattr(target, name, _tripwire)
        results = [propose(kb, REQ("EVIDENCE")), propose(kb, REQ("IDEATION"))]
        for result in results:
            for p in result["proposals"]:
                validate_proposal(p)
        checks = [check_proposal(kb, p) for result in results for p in result["proposals"]]
    assert [r["proposal_count"] for r in results] == [3, 5]
    assert {c["staleness"] for c in checks} == {"CURRENT"}


# T19 no trading or worker module is loaded, in a fresh interpreter

SCRIPT = """
import json, sys
from pathlib import Path
from moneylab.knowledge import open_knowledge_base
from moneylab.supervisor import check_proposal, propose
kb, _ = open_knowledge_base(Path(sys.argv[1]))
result = propose(kb, json.loads(sys.argv[2]))
checks = [check_proposal(kb, p)["staleness"] for p in result["proposals"]]
prefixes = json.loads(sys.argv[3])
loaded = sorted(m for m in sys.modules if any(m == p or m.startswith(p + ".") for p in prefixes))
print(json.dumps({"count": result["proposal_count"], "checks": sorted(set(checks)), "loaded": loaded}))
"""


def test_t19_no_trading_or_worker_module_is_loaded(repo):
    proc = subprocess.run([sys.executable, "-c", SCRIPT, str(repo), json.dumps(REQ("IDEATION")),
                           json.dumps(FORBIDDEN_MODULES)], capture_output=True, check=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert json.loads(proc.stdout) == {"count": 5, "checks": ["CURRENT"], "loaded": []}


# T20 no file is created or changed

def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def test_t20_api_and_cli_leave_the_filesystem_unchanged(repo, tmp_path):
    before = _snapshot(repo)
    kb = open_kb(repo)
    result = propose(kb, REQ("IDEATION"))
    for p in result["proposals"]:
        check_proposal(kb, p)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    assert run_cli(repo, "propose", as_bytes(REQ("IDEATION")), cwd=cwd)[0] == 0
    assert run_cli(repo, "check", as_bytes(by_key(result, f"OPEN_QUESTION:{OPEN}")), cwd=cwd)[0] == 0
    assert _snapshot(repo) == before
    assert list(cwd.iterdir()) == []


def test_t20_the_cli_has_no_file_output_option():
    from moneylab.supervisor.__main__ import build_parser

    parser = build_parser()
    options = {s for a in parser._actions for s in a.option_strings}
    assert options == {"-h", "--help", "--root"}
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["propose", "--output", "x.json"])
    assert exc.value.code == 2
