"""AUTO-10-CONTROLLED-READ-DIAGNOSE T10: the guard's diagnose form (D11).

In-process classification and the hook process only: nothing here runs moneylab.controlled_read, opens a
session or uses the network. The guard judges the call form only; it does not authenticate any approval."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GUARD_PATH = REPO / ".claude" / "hooks" / "guard.py"

_spec = importlib.util.spec_from_file_location("moneylab_guard_diagnose", GUARD_PATH)
guard = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = guard  # dataclasses look the module up while the class is created
_spec.loader.exec_module(guard)

CR = ".venv/Scripts/python.exe -B -m moneylab.controlled_read"
SID = "0a1b2c3d-0000-4000-8000-00000000abcd"
SHA = "0123456789abcdef" * 4
REASON = "controlled read diagnose; confirm the CONTROLLED_READ_DIAGNOSE_AUTHORIZATION message first"
RUN_REASON = "controlled read call; confirm the CONTROLLED_READ_AUTHORIZATION message first"
PRECHECK_REASON = "controlled read precheck; confirm the CONTROLLED_READ_PRECHECK_AUTHORIZATION message first"
DENY = ("deny", "controlled-read-form")


def form(n: str = "44113503", sha: str = SHA, task: str = "ECON-FWD-M20", profile: str = "ECON-FWD-M20-WO/1") -> str:
    return (f"{CR} diagnose --task {task} --project-key C--MoneyLab-auto-08 --session {SID} --profile {profile}"
            f" --expect-prefix-bytes {n} --expect-prefix-sha256 {sha}")


def decide(cmd: str, tool: str = "Bash"):
    return guard.decide({"tool_name": tool, "tool_input": {"command": cmd}}, REPO)


def classify(cmd: str, tool: str = "Bash") -> tuple[str, str]:
    d = decide(cmd, tool)
    return d.action, d.rule


@pytest.mark.parametrize("cmd", [form(), form(n="1"), form(n="67108864"), form(profile="ECON-FWD-M20-PREREG/1"),
                                 form(task="A" * 64), form(task="AUTO-10-CONTROLLED-READ-DIAGNOSE")])
def test_t10_exact_form_asks_with_the_diagnose_reason(cmd):
    d = decide(cmd)
    assert (d.action, d.rule, d.reason) == ("ask", "controlled-read", REASON)


@pytest.mark.parametrize("cmd", [
    form(n="0"), form(n="67108865"), form(n="99999999"), form(n="012"), form(n="123456789"), form(n="-1"),
    form(n="1.0"), form(sha=SHA.upper()), form(sha=SHA[:-1]), form(sha=SHA + "0"), form(sha="g" * 64),
    form().replace("--profile ECON-FWD-M20-WO/1 --expect-prefix-bytes 44113503",
                   "--expect-prefix-bytes 44113503 --profile ECON-FWD-M20-WO/1"),  # option order
    form().replace(f"--expect-prefix-bytes 44113503 --expect-prefix-sha256 {SHA}",
                   f"--expect-prefix-sha256 {SHA} --expect-prefix-bytes 44113503"),
    form().replace(" --expect-prefix-bytes 44113503", ""),  # missing
    form().replace(f" --expect-prefix-sha256 {SHA}", ""),
    form() + " --expect-prefix-bytes 1",  # duplicate
    form() + " extra", form() + f" --selector assistant:{SID}:text:1", form() + " --attempt 001",
    form().replace("--expect-prefix-bytes ", "--expect-prefix-bytes="),
    form().replace("--task ", "--task="),
    form().replace(SHA, f"\"{SHA}\""), form().replace("44113503", "'44113503'"),
    form().replace(" --expect-prefix-sha256", "\t--expect-prefix-sha256"),
    form().replace(" --expect-prefix-sha256", "  --expect-prefix-sha256"),
    form() + " ; ls", form() + " && ls", form() + " | cat", form() + " > out.json", form() + " 2>&1",
    form() + "\n", " " + form(), "ls && " + form(),
    form().replace(".venv/Scripts/python.exe", "python"),
    form().replace(".venv/Scripts/python.exe", "./.venv/Scripts/python.exe"),
    form().replace(".venv/Scripts/python.exe", ".venv\\Scripts\\python.exe"),
    form().replace(".venv/Scripts/python.exe", "C:/MoneyLab-auto-10/.venv/Scripts/python.exe"),
    form().replace("-B -m moneylab", "-B -mmoneylab"), form().replace("-B -m moneylab", "-Bm moneylab"),
    form().replace(" -B", ""), form().replace("-B -m", "-I -B -m"),
    form().replace("moneylab.controlled_read", "moneylab.controlled_read.__main__"),
    form(task="A" * 65), form(task="econ-fwd"), form(profile="OTHER-DOC/1"),
    form().replace("diagnose", "DIAGNOSE"), form().replace("--expect-prefix-bytes", "--expect-prefix-size"),
    form().replace("C--MoneyLab-auto-08", "../x"),
])
def test_t10_other_forms_deny(cmd):
    assert classify(cmd) == DENY


@pytest.mark.parametrize("cmd", [form(), form(n="1")])
def test_t10_powershell_is_denied(cmd):
    assert classify(cmd, "PowerShell") == DENY


def test_t10_existing_forms_keep_their_decision_and_reason():
    run = (f"{CR} run --task ECON-FWD-M20 --project-key C--MoneyLab-auto-08 --session {SID}"
           f" --selector assistant:{SID}:text:2 --profile ECON-FWD-M20-WO/1 --attempt 001")
    status = f"{CR} status --task ECON-FWD-M20 --attempt 001"
    precheck = f"{CR} precheck --task ECON-FWD-M20 --project-key C--MoneyLab-auto-08 --session {SID} --profile ECON-FWD-M20-WO/1"
    for cmd in (run, status):
        d = decide(cmd)
        assert (d.action, d.rule, d.reason) == ("ask", "controlled-read", RUN_REASON)
    d = decide(precheck)
    assert (d.action, d.rule, d.reason) == ("ask", "controlled-read", PRECHECK_REASON)
    assert classify(precheck + " --expect-prefix-bytes 1") == DENY
    assert classify(f"{CR} precheck --task ECON-FWD-M20 --project-key C--MoneyLab-auto-08 --session {SID}"
                    f" --profile ECON-FWD-M20-WO/1 --expect-prefix-bytes 1 --expect-prefix-sha256 {SHA}") == DENY


@pytest.mark.parametrize("cmd", ["grep -n diagnose src/moneylab/controlled_read/diagnose.py",
                                 ".venv/Scripts/python.exe -m pytest tests/test_controlled_read_diagnose.py -q",
                                 "git diff -- src/moneylab/controlled_read/diagnose.py"])
def test_t10_rule_does_not_catch_other_commands(cmd):
    assert classify(cmd) == ("pass", "")


def run_hook(stdin: bytes):
    return subprocess.run([sys.executable, str(GUARD_PATH)], input=stdin, capture_output=True, timeout=30)


def test_t10_process_ask_outputs_json():
    r = run_hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": form()}}).encode())
    assert r.returncode == 0
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse" and out["permissionDecision"] == "ask"
    assert out["permissionDecisionReason"] == "MoneyLab guard [controlled-read]: " + REASON


@pytest.mark.parametrize("cmd", [form(n="0"), form(n="67108865"), form() + " extra"])
def test_t10_process_deny_exit_code_2(cmd):
    r = run_hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}).encode())
    assert r.returncode == 2 and b"controlled-read-form" in r.stderr and r.stdout == b""
