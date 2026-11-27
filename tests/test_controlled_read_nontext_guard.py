"""AUTO-12-CONTROLLED-READ-NONTEXT T11 and T12: the guard's profile alternative ECON-FWD-M20-WO/2 (N7).

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

_spec = importlib.util.spec_from_file_location("moneylab_guard_nontext", GUARD_PATH)
guard = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = guard  # dataclasses look the module up while the class is created
_spec.loader.exec_module(guard)

CR = ".venv/Scripts/python.exe -B -m moneylab.controlled_read"
SID = "0a1b2c3d-0000-4000-8000-00000000abcd"
SHA = "0123456789abcdef" * 4
V1, PREREG, V2 = "ECON-FWD-M20-WO/1", "ECON-FWD-M20-PREREG/1", "ECON-FWD-M20-WO/2"
RUN_REASON = "controlled read call; confirm the CONTROLLED_READ_AUTHORIZATION message first"
PRECHECK_REASON = "controlled read precheck; confirm the CONTROLLED_READ_PRECHECK_AUTHORIZATION message first"
DIAGNOSE_REASON = "controlled read diagnose; confirm the CONTROLLED_READ_DIAGNOSE_AUTHORIZATION message first"
DENY = ("deny", "controlled-read-form")


def run_form(profile: str = V2) -> str:
    return (f"{CR} run --task ECON-FWD-M20 --project-key C--MoneyLab-auto-08 --session {SID}"
            f" --selector tool_result:toolu_01:text:1 --profile {profile} --attempt 001")


def precheck_form(profile: str = V2) -> str:
    return f"{CR} precheck --task ECON-FWD-M20 --project-key C--MoneyLab-auto-08 --session {SID} --profile {profile}"


def diagnose_form(profile: str = V2) -> str:
    return (f"{CR} diagnose --task ECON-FWD-M20 --project-key C--MoneyLab-auto-08 --session {SID} --profile {profile}"
            f" --expect-prefix-bytes 44113503 --expect-prefix-sha256 {SHA}")


FORMS = [(run_form, RUN_REASON), (precheck_form, PRECHECK_REASON), (diagnose_form, DIAGNOSE_REASON)]
FORM_IDS = ["run", "precheck", "diagnose"]


def decide(cmd: str, tool: str = "Bash"):
    return guard.decide({"tool_name": tool, "tool_input": {"command": cmd}}, REPO)


def classify(cmd: str, tool: str = "Bash") -> tuple[str, str]:
    d = decide(cmd, tool)
    return d.action, d.rule


# ------------------------------------------------------------------------------ T11: in-process


@pytest.mark.parametrize("make, reason", FORMS, ids=FORM_IDS)
def test_t11_v2_exact_form_asks_with_the_existing_reason(make, reason):
    d = decide(make(V2))
    assert (d.action, d.rule, d.reason) == ("ask", "controlled-read", reason)


@pytest.mark.parametrize("make, reason", FORMS, ids=FORM_IDS)
@pytest.mark.parametrize("profile", [V1, PREREG])
def test_t11_v1_and_prereg_keep_their_decision_and_reason(make, reason, profile):
    d = decide(make(profile))
    assert (d.action, d.rule, d.reason) == ("ask", "controlled-read", reason)


@pytest.mark.parametrize("make", [f for f, _ in FORMS], ids=FORM_IDS)
@pytest.mark.parametrize("profile", ["ECON-FWD-M20-WO/3", "econ-fwd-m20-wo/2", "ECON-FWD-M20-WO/02",
                                     "ECON-FWD-M20-WO/2 ", "ECON-FWD-M20-WO/0", "ECON-FWD-M20-WO/22",
                                     "ECON-FWD-M20-PREREG/2", "ECON-FWD-M20-WO"])
def test_t11_other_profiles_deny(make, profile):
    assert classify(make(profile)) == DENY


@pytest.mark.parametrize("make", [f for f, _ in FORMS], ids=FORM_IDS)
def test_t11_trailing_space_and_extra_tokens_deny(make):
    for cmd in (make(V2) + " ", make(V2) + "\t", make(V2) + " extra", make(V2) + " ; ls"):
        assert classify(cmd) == DENY


@pytest.mark.parametrize("make", [f for f, _ in FORMS], ids=FORM_IDS)
def test_t11_powershell_is_denied(make):
    assert classify(make(V2), "PowerShell") == DENY


def test_t11_status_form_is_unchanged():
    d = decide(f"{CR} status --task ECON-FWD-M20 --attempt 001")
    assert (d.action, d.rule, d.reason) == ("ask", "controlled-read", RUN_REASON)


# --------------------------------------------------------------------------- T12: hook process


def run_hook(cmd: str):
    stdin = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}).encode()
    return subprocess.run([sys.executable, str(GUARD_PATH)], input=stdin, capture_output=True, timeout=30)


@pytest.mark.parametrize("make, reason", FORMS, ids=FORM_IDS)
def test_t12_process_v2_ask_outputs_json(make, reason):
    r = run_hook(make(V2))
    assert r.returncode == 0
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse" and out["permissionDecision"] == "ask"
    assert out["permissionDecisionReason"] == "MoneyLab guard [controlled-read]: " + reason


@pytest.mark.parametrize("cmd", [run_form("ECON-FWD-M20-WO/3"), precheck_form("econ-fwd-m20-wo/2"),
                                 diagnose_form("ECON-FWD-M20-WO/02"), precheck_form(V2) + " "])
def test_t12_process_deny_exit_code_2(cmd):
    r = run_hook(cmd)
    assert r.returncode == 2 and b"controlled-read-form" in r.stderr and r.stdout == b""
