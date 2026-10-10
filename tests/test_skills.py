"""Offline consistency tests for Claude Code Skills (.claude/skills/*/SKILL.md).

A Skill is a procedure, not a security boundary: only the guard hook and the permission rules in
.claude/settings.json enforce anything. These tests keep the two in step. Every command in a Skill's
```bash blocks carries a tier tag (docs/agent_workflow.md section 2) and the tag must match what the
guard and the permission rules actually decide:

  [A]        guard pass, no permission ask/deny rule matches        runs without a prompt
  [B]        guard ask, or guard pass and a permission ask matches  approval prompt is enforced
  [B-skill]  guard pass, no permission ask/deny rule matches        approval only by the procedure

A guard deny or a permission deny is never allowed in a Skill. The permission-rule matcher below
is an approximation of Claude Code's `Bash(prefix *)` matching (fnmatch on the whole command).
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / ".claude" / "skills"
SETTINGS = REPO / ".claude" / "settings.json"
WORKFLOW_DOC = REPO / "docs" / "agent_workflow.md"
GUARD_PATH = REPO / ".claude" / "hooks" / "guard.py"

_spec = importlib.util.spec_from_file_location("moneylab_guard_for_skills", GUARD_PATH)
guard = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = guard  # dataclasses look the module up while the class is created
_spec.loader.exec_module(guard)

# name -> may the model invoke it on its own? (False: `disable-model-invocation: true`, user only)
EXPECTED_SKILLS = {
    "incident": True,
    "research-run": False,
    "collect-session": False,
    "git-ship": False,
}
REQUIRED_SECTIONS = ("## 입력", "## 절차", "## 검증 기준", "## 실패 처리", "## 승인 조건", "## 복구 절차")
EXTRA_SECTIONS = {"git-ship": ("### commit 전", "### commit 후", "### push 후")}
READ_ONLY_TOOLS = {"Read", "Grep", "Glob"}
TIERS = ("A", "B", "B-skill")

_FENCE = re.compile(r"^```bash[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)
_TAGGED = re.compile(r"^(?P<cmd>.+?)\s+#\s*\[(?P<tier>[A-Za-z-]+)\]\s*$")
_MONEYLAB_SUB = re.compile(r"-m\s+moneylab\s+(?P<sub>[\w-]+)")

BYPASS = [
    ("--no-verify", r"--no-verify\b"),
    ("command substitution", r"\$\(|`"),
    ("variable-built path", r"\$\{?\w+"),
    ("shell -c", r"\b(bash|sh|pwsh|powershell|cmd)(\.exe)?\s+(-c|/c|-command)\b"),
    ("python -c", r"\bpython[\d.]*(\.exe)?\s+(-\w+\s+)*-c\b"),
    ("eval", r"\b(eval|iex|invoke-expression)\b"),
    ("encoded command", r"\s-enc(odedcommand)?\b|\bbase64\b"),
    ("pipe into interpreter", r"\|\s*(sh|bash|pwsh|powershell|python|py)\b"),
    ("force", r"(?-i:--force\b|\s-f\b)"),  # case-sensitive: `git commit -F <file>` is fine
]
FORBIDDEN_ANYWHERE = [
    ("hook switch", r"(?i)disableallhooks"),
    ("permission skip", r"(?i)dangerously"),
    ("hooks path override", r"(?i)core\.hookspath"),
]


# ------------------------------------------------------------------------------------- helpers


def cli_subcommands() -> set[str]:
    from moneylab.cli import build_parser

    for action in build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    return set()


def permission_rules() -> dict[str, list[str]]:
    perms = json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]
    out = {}
    for kind in ("allow", "ask", "deny"):
        out[kind] = [m.group(1) for r in perms.get(kind, []) if (m := re.fullmatch(r"Bash\((.*)\)", r))]
    return out


def permission_match(cmd: str, rules: dict[str, list[str]]) -> dict[str, list[str]]:
    return {kind: [p for p in pats if fnmatch.fnmatchcase(cmd, p)] for kind, pats in rules.items()}


def parse_frontmatter(text: str) -> dict[str, object] | None:
    m = re.match(r"---\n(.*?)\n---\n", text.replace("\r\n", "\n"), re.S)
    if not m:
        return None
    fm: dict[str, object] = {}
    key = None
    for line in m.group(1).splitlines():
        if (item := re.match(r"\s+-\s+(.+)", line)) and key:
            fm.setdefault(key, [])
            if isinstance(fm[key], list):
                fm[key].append(item.group(1).strip())
        elif kv := re.match(r"([\w-]+):\s*(.*)", line):
            key, value = kv.group(1), kv.group(2).strip().strip("\"'")
            fm[key] = value if value else []
    return fm


def tagged_commands(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    commands, problems = [], []
    for block in _FENCE.findall(text.replace("\r\n", "\n")):
        for line in block.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = _TAGGED.match(line.strip())
            if not m:
                problems.append(f"command without tier tag: {line.strip()}")
            elif m.group("tier") not in TIERS:
                problems.append(f"unknown tier [{m.group('tier')}]: {line.strip()}")
            else:
                commands.append((m.group("cmd").strip(), m.group("tier")))
    return commands, problems


def check_command_tier(cmd: str, tier: str, rules: dict[str, list[str]], root: Path = REPO) -> list[str]:
    g = guard.check_command(cmd, root).action
    p = permission_match(cmd, rules)
    if g == guard.DENY:
        return [f"guard denies: {cmd}"]
    if p["deny"]:
        return [f"permission deny {p['deny']}: {cmd}"]
    enforced_ask = g == guard.ASK or bool(p["ask"])
    if tier == "B" and not enforced_ask:
        return [f"[B] but nothing enforces a prompt (guard {g}, no permission ask): {cmd}"]
    if tier in ("A", "B-skill") and enforced_ask:
        layer = "guard" if g == guard.ASK else f"permission ask {p['ask']}"
        return [f"[{tier}] but {layer} prompts: {cmd}"]
    return []


def validate_skill(text: str, name: str, model_invocable: bool, subcommands: set[str],
                   rules: dict[str, list[str]], root: Path = REPO) -> list[str]:
    problems = []
    fm = parse_frontmatter(text)
    if fm is None:
        return ["missing frontmatter"]
    if fm.get("name") != name:
        problems.append(f"frontmatter name {fm.get('name')!r} != folder {name!r}")
    if not fm.get("description"):
        problems.append("frontmatter description missing")
    user_only = str(fm.get("disable-model-invocation", "")).lower() == "true"
    if not model_invocable and not user_only:
        problems.append("disable-model-invocation: true is required")
    tools = fm.get("allowed-tools", [])
    tools = tools if isinstance(tools, list) else re.split(r"[,\s]+", tools)
    extra = {t.split("(")[0] for t in tools if t} - READ_ONLY_TOOLS
    if extra:
        problems.append(f"allowed-tools may only list read tools, found {sorted(extra)}")
    for section in REQUIRED_SECTIONS + EXTRA_SECTIONS.get(name, ()):
        if not re.search(rf"^{re.escape(section)}\s*$", text, re.M):
            problems.append(f"missing section {section!r}")
    for label, pattern in FORBIDDEN_ANYWHERE:
        if re.search(pattern, text):
            problems.append(f"forbidden text ({label})")
    commands, tag_problems = tagged_commands(text)
    problems += tag_problems
    for cmd, tier in commands:
        problems += check_command_tier(cmd, tier, rules, root)
        for label, pattern in BYPASS:
            if re.search(pattern, cmd, re.I):
                problems.append(f"bypass pattern ({label}): {cmd}")
        for m in _MONEYLAB_SUB.finditer(cmd):
            if m.group("sub") not in subcommands:
                problems.append(f"unknown moneylab subcommand {m.group('sub')!r}: {cmd}")
    return problems


# --------------------------------------------------------------------------- validator self-tests

VALID = """---
name: demo
description: demo skill
disable-model-invocation: true
allowed-tools:
  - Read
  - Grep
---

## 입력
## 절차

```bash
git status --short  # [A]
./.venv/Scripts/python.exe -m moneylab record-verify data/raw/upbit/research/<session>/KRW-BTC  # [A]
./.venv/Scripts/python.exe -m moneylab research-build <dataset> --dry-run  # [A]
./.venv/Scripts/python.exe -m moneylab research-final <run>  # [B]
./.venv/Scripts/python.exe -m moneylab record --provider upbit --source fixture --out <dir>  # [B]
git add -- docs/agent_workflow.md  # [B-skill]
git commit -m "<message>"  # [B]
```

## 검증 기준
## 실패 처리
## 승인 조건
## 복구 절차
"""


@pytest.fixture(scope="module")
def subcommands():
    return cli_subcommands()


@pytest.fixture(scope="module")
def rules():
    return permission_rules()


def _check(text, subcommands, rules, name="demo", model_invocable=False):
    return validate_skill(text, name, model_invocable, subcommands, rules)


def test_cli_subcommands_are_discovered(subcommands):
    assert {"record", "record-verify", "replay-check", "research-build", "research-stats",
            "research-final"} <= subcommands


def test_valid_skill_passes(subcommands, rules):
    assert _check(VALID, subcommands, rules) == []


@pytest.mark.parametrize("old, new, expected", [
    ("## 승인 조건\n", "", "missing section '## 승인 조건'"),
    ("name: demo", "name: other", "frontmatter name"),
    ("disable-model-invocation: true\n", "", "disable-model-invocation: true is required"),
    ("  - Grep", "  - Bash", "allowed-tools may only list read tools"),
    ("git status --short  # [A]", "git status --short", "command without tier tag"),
    ("git status --short  # [A]", "git status --short  # [C]", "unknown tier"),
    ("git status --short  # [A]", "git status --short  # [B]", "nothing enforces a prompt"),
    ('git commit -m "<message>"  # [B]', 'git commit -m "<message>"  # [A]', "guard prompts"),
    ("git add -- docs/agent_workflow.md  # [B-skill]", "git push origin <branch>  # [B-skill]",
     "guard prompts"),
    ("--source fixture --out <dir>  # [B]", "--source fixture --out <dir>  # [A]", "permission ask"),
    ("git status --short  # [A]", "git push --force origin <branch>  # [B]", "guard denies"),
    ("git status --short  # [A]", "git clean -n  # [B]", "guard denies"),
    ("git status --short  # [A]", "rm data/raw/upbit/x  # [B]", "guard denies"),
    ("git status --short  # [A]", "bash -c git status  # [A]", "bypass pattern (shell -c)"),
    ("git status --short  # [A]", "cat $(echo data)/raw/x  # [A]", "bypass pattern (command substitution)"),
    ("git status --short  # [A]", "cat ${ROOT}/x  # [A]", "bypass pattern (variable-built path)"),
    ('git commit -m "<message>"  # [B]', 'git commit --no-verify -m "<message>"  # [B]', "guard denies"),
    ("record-verify data", "record-publish data", "unknown moneylab subcommand 'record-publish'"),
    ("## 입력\n", "## 입력\nset disableAllHooks\n", "forbidden text (hook switch)"),
])
def test_validator_catches(old, new, expected, subcommands, rules):
    assert old in VALID
    problems = _check(VALID.replace(old, new, 1), subcommands, rules)
    assert any(expected in p for p in problems), problems


def test_model_invocable_skill_does_not_need_the_flag(subcommands, rules):
    text = VALID.replace("disable-model-invocation: true\n", "")
    assert _check(text, subcommands, rules, model_invocable=True) == []


def test_extra_sections_for_git_ship(subcommands, rules):
    text = VALID.replace("name: demo", "name: git-ship")
    problems = _check(text, subcommands, rules, name="git-ship")
    assert {p for p in problems} == {f"missing section '### {s}'" for s in ("commit 전", "commit 후", "push 후")}


def test_missing_frontmatter(subcommands, rules):
    assert _check("## 입력\n", subcommands, rules) == ["missing frontmatter"]


# ------------------------------------------------------------------------------- real skills


def test_no_unexpected_skills():
    found = {p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md")} if SKILLS_DIR.exists() else set()
    assert found <= set(EXPECTED_SKILLS), f"unregistered skills: {sorted(found - set(EXPECTED_SKILLS))}"


def test_skill_folders_hold_no_scripts():
    if not SKILLS_DIR.exists():
        return
    scripts = [p for p in SKILLS_DIR.rglob("*") if p.suffix.lower() in {".py", ".sh", ".ps1", ".bat", ".cmd", ".js"}]
    assert scripts == []


@pytest.mark.parametrize("name", sorted(EXPECTED_SKILLS))
def test_skill_is_consistent_with_guard_and_permissions(name, subcommands, rules):
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        pytest.skip(f"{name} not written yet (2-4 phases 2-5)")
    text = path.read_text(encoding="utf-8")
    assert validate_skill(text, name, EXPECTED_SKILLS[name], subcommands, rules) == []


# --------------------------------------------------------------------------------- incident

INCIDENTS_DIR = REPO / "docs" / "incidents"
REPORT_SECTIONS = ("## 요약", "## 분류", "## 사실", "## 가설", "## 증거", "## 영향", "## 무결성", "## 복구 제안")


def test_incident_skill_is_read_only():
    path = SKILLS_DIR / "incident" / "SKILL.md"
    if not path.exists():
        pytest.skip("incident not written yet")
    text = path.read_text(encoding="utf-8")
    commands, problems = tagged_commands(text)
    assert problems == []
    assert commands, "incident has no commands"
    assert [c for c, tier in commands if tier != "A"] == [], "incident may only run [A] commands"
    assert "docs/incidents/" in text
    for section in REPORT_SECTIONS:
        assert f"`{section}`" in text, f"incident does not require report section {section}"


def test_incident_reports_have_required_sections():
    if not INCIDENTS_DIR.exists():
        pytest.skip("docs/incidents/ not created yet")
    for report in sorted(INCIDENTS_DIR.glob("*.md")):
        assert re.fullmatch(r"\d{8}-[a-z0-9-]+\.md", report.name), report.name
        text = report.read_text(encoding="utf-8")
        missing = [s for s in REPORT_SECTIONS if not re.search(rf"^{re.escape(s)}\s*$", text, re.M)]
        assert missing == [], f"{report.name} misses {missing}"
        facts = text.split("## 사실", 1)[1].split("\n## ", 1)[0]
        assert facts.strip(), f"{report.name}: empty facts section"


# ------------------------------------------------------------------------------ workflow doc


def guard_rule_names() -> set[str]:
    names = {rule for rule, _ in guard.DENY_RULES + guard.ASK_RULES}
    names |= set(re.findall(r'Decision\((?:DENY|ASK), "([\w-]+)"', GUARD_PATH.read_text(encoding="utf-8")))
    return names


def test_workflow_doc_lists_every_guard_rule():
    doc = WORKFLOW_DOC.read_text(encoding="utf-8")
    missing = sorted(n for n in guard_rule_names() if f"`{n}`" not in doc)
    assert missing == [], f"docs/agent_workflow.md does not mention guard rules {missing}"


def test_workflow_doc_lists_every_tier_and_expected_skill():
    doc = WORKFLOW_DOC.read_text(encoding="utf-8")
    for tier in TIERS:
        assert f"`[{tier}]`" in doc
    for name in EXPECTED_SKILLS:
        assert name in doc
    for section in REQUIRED_SECTIONS:
        assert f"`{section}`" in doc
