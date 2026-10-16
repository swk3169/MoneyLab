"""PreToolUse guard for Claude Code in MoneyLab. Fail-closed: any internal error blocks the call.

Claude Code pipes one JSON object to stdin ({"tool_name", "tool_input", "cwd", ...}). This script
answers with one of:
  deny  exit code 2, reason on stderr (a hook denial is enforced in every permission mode)
  ask   exit code 0 + {"hookSpecificOutput": {"permissionDecision": "ask", ...}} on stdout
  pass  exit code 0 and no output; the normal permission flow decides

.claude/settings.json runs this script as `timeout -k 1 8 python guard.py || exit 2` under Git Bash,
so a crash, a missing interpreter, a hang or a kill also ends in exit 2. Claude Code's own failure
handling ("onFailure": "block", hook timeout) was observed NOT to block on v2.1.295, so it is not
relied on.

This is ONE layer, not a sandbox. Commands are matched as text, so a command can hide a path or a
verb from it (string concatenation, variables, scripts written to disk first). The other layers are
the permission rules in .claude/settings.json and tests/test_repo_hygiene.py, which pins the frozen
study hashes. Known gaps are kept as strict xfail tests in tests/test_agent_guard.py.

Standard library only. Keep the rules in sync with docs/agent_workflow.md.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DENY, ASK, PASS = "deny", "ask", "pass"

# Project-relative paths: lower case, forward slashes.
FROZEN = ("configs/research_v04.toml", "docs/research_v04_preregistration.md")
FROZEN_IF_EXISTS = ("configs/research_v05.toml", "docs/research_v05_preregistration.md")
ASK_EDIT_FILES = ("docs/research_v05_preregistration_draft.md", "claude.md", "pyproject.toml",
                  "requirements.txt", "requirements-dev.txt", ".gitignore", ".gitattributes")
ASK_EDIT_PREFIXES = (".claude/", ".github/", "data/processed/")
DENY_WRITE_PREFIXES = ("data/raw/", ".git/")

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "Grep"}
SHELL_TOOLS = {"Bash", "PowerShell"}


@dataclass(frozen=True)
class Decision:
    action: str
    rule: str = ""
    reason: str = ""


# ----------------------------------------------------------------------------------------- paths


def _real(path: str) -> str:
    """Absolute, symlink/junction-resolved, lower-case path with forward slashes."""
    return os.path.realpath(os.path.abspath(path)).replace("\\", "/").lower()


def _relative(path: str, root: Path) -> str | None:
    p, r = _real(path), _real(str(root)).rstrip("/")
    if p == r:
        return ""
    return p[len(r) + 1:] if p.startswith(r + "/") else None


def _is_env_file(name: str) -> bool:
    return name == ".env" or (name.startswith(".env.") and name != ".env.example")


def check_path(tool: str, path: str, root: Path) -> Decision:
    full = _real(path)
    name = full.rsplit("/", 1)[-1]
    if "/locked/" in full + "/":
        return Decision(DENY, "locked", "test split files under locked/ are opened only by research-final")
    if _is_env_file(name):
        return Decision(DENY, "env", ".env files hold secrets and are never read or written by the agent")
    if tool not in WRITE_TOOLS:
        return Decision(PASS)
    rel = _relative(path, root)
    if rel is None:
        # Claude Code settings outside this project (user-wide ~/.claude, other projects) can switch
        # hooks off; the agent never changes them.
        if re.search(r"/\.claude/(settings[^/]*\.json$|hooks/)|/\.claude\.json$", full):
            return Decision(DENY, "claude-settings", "Claude Code settings outside this project are not changed")
        return Decision(PASS)
    if rel in FROZEN:
        return Decision(DENY, "frozen", f"{rel} is a frozen preregistration file (a change is a new study)")
    if rel in FROZEN_IF_EXISTS and os.path.exists(path):
        return Decision(DENY, "frozen", f"{rel} is frozen once it exists")
    if rel.startswith(DENY_WRITE_PREFIXES):
        return Decision(DENY, "raw-or-git", f"{rel} is immutable raw data or git internals")
    if rel in FROZEN_IF_EXISTS or rel in ASK_EDIT_FILES or rel.startswith(ASK_EDIT_PREFIXES):
        return Decision(ASK, "protected-edit", f"{rel} needs user approval to change")
    return Decision(PASS)


# -------------------------------------------------------------------------------------- commands

_HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?\n.*?\n\s*\1\b", re.S)
_COMMIT_MSG = re.compile(r"(-m|--message)\s*(\"[^\"]*\"|'[^']*')")


def normalize(cmd: str) -> str:
    """Lower case, '/' separators, quotes/escapes removed, whitespace collapsed. Removing quotes
    joins split spellings such as "data"/"raw" or d'a'ta/raw back into one token."""
    if re.match(r"\s*git\s+commit\b", cmd):  # the message text is not a command
        cmd = _COMMIT_MSG.sub(" ", _HEREDOC.sub(" ", cmd))
    c = cmd.lower().replace("\\", "/")
    c = re.sub(r"[\"'`^]", "", c)
    c = re.sub(r"/+", "/", c)
    c = re.sub(r"\s+", " ", c).strip()
    # full-path executables (/usr/bin/git, c:/program files/git/cmd/git.exe) -> bare names
    c = re.sub(r"[^\s;&|()]*/(git|python[\d.]*|py|powershell|pwsh|bash|sh|cmd|node)(\.exe)?(?=[\s;&|)]|$)", r"\1", c)
    c = re.sub(r"\b(git|python[\d.]*|py|powershell|pwsh|bash|cmd|node)\.exe\b", r"\1", c)
    # git global options before the subcommand (git -C . push, git -c k=v push, git --git-dir=x push)
    return re.sub(r"\bgit((\s+(-c\s+\S+|--git-dir(=|\s+)\S+|--work-tree(=|\s+)\S+|--namespace(=|\s+)\S+"
                  r"|--no-pager|-p|--paginate|--bare|--no-replace-objects|--literal-pathspecs))+)(?=\s)", "git", c)


PROTECTED = (r"(data/raw\b|/locked\b|locked/|research_v04\.toml|research_v04_preregistration"
             r"|research_v05\.toml|research_v05_preregistration\.md|\.claude/settings|\.claude/hooks)")
MUTATE = (r"(\b(rm|rmdir|rd|del|erase|mv|move|ren|rename|cp|copy|xcopy|robocopy|tee|touch|truncate|shred"
          r"|attrib|icacls|takeown|chmod|chown|ln|mklink|sed|perl|dd|unlink|rmtree|gunzip)\b"
          r"|\b(remove|move|rename|copy|set|clear|new)-item\b|\b(set|add|clear)-content\b|\bout-file\b"
          r"|\bopen\([^)]*,\s*(mode\s*=\s*)?[rwabxt+]*[wax+][rwabxt+]*\s*[,)]"
          r"|\.write\(|write_text|write_bytes|os\.replace|os\.rename|os\.remove)")
DELETE_MOVE = (r"(\b(rm|rmdir|rd|del|erase|mv|move|ren|rename|unlink|rmtree)\b|\b(remove|move|rename)-item\b"
               r"|os\.remove|shutil\.move)")
RECURSIVE_DELETE = (r"(\brm\s+(-\w*r\w*|--recursive)\b|\bremove-item\b.*-r(ecurse)?\b|\b(rmdir|rd)\s+/s\b"
                    r"|\brmtree\b|\bdel\s+/s\b)")

DENY_RULES: list[tuple[str, str]] = [
    # system clock, time service, registry, power (read-only queries stay allowed)
    ("clock", r"\bw32tm(\.exe)?\b(?!\s+[-/](query|stripchart|monitor|tz|ntte|ntpte|dumpreg)\b)"),
    ("clock", r"\bset-date\b|\bdate\s+(-s|--set)\b|\btimedatectl\s+set|\bhwclock\b"),
    ("clock", r"(^|[;&|(]\s*)(cmd(\.exe)?\s+/c\s+)?(date|time)\s+\d"),
    ("clock", r"\b(stop|start|restart|set)-service\b.*\bw32time\b|\bnet\s+(stop|start)\s+w32time\b"
              r"|\bsc(\.exe)?\s+(config|stop|start|delete|failure)\s+w32time\b"),
    ("registry", r"\breg(\.exe)?\s+(add|delete|import|restore|load|unload|copy|save)\b|\bregedit\b"
                 r"|\b(set|new|remove|rename|copy|move|clear)-item(property)?\b.*\b(hk(lm|cu|cr|u|cc):|registry::)"),
    ("power", r"\bpowercfg(\.exe)?\b(?!\s+[-/](q|query|a|availablesleepstates|requests|getactivescheme|l|list)\b)"),
    ("power", r"\b(shutdown|restart-computer|stop-computer|bcdedit|diskpart)\b|\bformat\s+[a-z]:"),
    # git history and working-tree destruction
    ("git", r"\bgit\s+push\b.*(\s--force\b|\s--force-with-lease\b|\s-f\b|\s\+\S)"),
    ("git", r"\bgit\s+push\b.*\s(origin\s+)?(head:)?(main|master)\b"),
    ("git", r"\bgit\s+add\s+(.*\s)?(-a|--all|\.|\*)(\s|$)"),
    ("git", r"\bgit\s+(clean|filter-branch|filter-repo)\b|\bgit\s+reset\s+.*--hard\b|\bgit\s+reset\s+--hard\b"),
    ("git", r"\bgit\s+stash\s+(drop|clear)\b|\bgit\s+branch\s+.*--delete\s+--force\b|\bgit\s+update-ref\s+-d\b"),
    ("git", r"\bgit\s+commit\b.*(--no-verify|\s-n\b|--no-gpg-sign)"),
    # trading, keys, secrets (the project is read-only; see CLAUDE.md absolute rules)
    ("trading", r"/v1/orders?\b|\b(place|create|submit|cancel)_order\b|\bupbit_(access|secret)_key\b"
                r"|\bprivate_key\b|\bseed[_ ]?phrase\b|\bmnemonic\b"),
    ("env", r"(^|[\s/=<>])\.env(?!\.example)\b"),
    # remote code and obfuscation
    ("exec", r"\b(invoke-expression|iex)\b|\s-enc(odedcommand)?\s"
             r"|\b(curl|wget|iwr|invoke-webrequest|irm|invoke-restmethod)\b.*\|\s*(sh|bash|pwsh|powershell|python|py)\b"),
    ("hooks", r"disableallhooks"),
]

# Inline code (python -c, python - <<EOF) is opaque to path matching. Read-only analysis passes;
# anything that can change files, start processes or run generated code needs approval.
INLINE_CODE = r"(^|[\s;&|(])(python[\d.]*|py)\s+(-[a-z]+\s+)*(-c|-)(\s|$)"
INLINE_EFFECT = (r"\bos\.(remove|unlink|rmdir|removedirs|rename|renames|replace|chmod|truncate|system|popen"
                 r"|exec\w*|spawn\w*|startfile|makedirs|mkdir|link|symlink)\b|\bshutil\.\w+"
                 r"|\.(unlink|rmdir|write_text|write_bytes|write|writelines|touch|rename|replace|chmod|mkdir"
                 r"|symlink_to|hardlink_to)\("
                 r"|\bopen\([^)]*,\s*(mode\s*=\s*)?[rwabxt+]*[wax+][rwabxt+]*\s*[,)]"
                 r"|\b(subprocess|ctypes|importlib|__import__|socket|urllib|requests|http\.client)\b"
                 r"|\b(exec|eval|compile)\(|\batomic_write\w*|\bdump\(|\bsave\w*\(")
# Running a script file: approval unless git tracks it (reviewed code).
SCRIPT_RUN = (r"(^|[\s;&|(])(python[\d.]*|py|bash|sh|node|pwsh|powershell)\s+((-[a-z]+\s+)*)"
              r"(-file\s+)?(?P<script>[^\s;&|()]+\.(py|sh|ps1|js|bat|cmd))(?=[\s;&|)]|$)"
              r"|(^|[;&|(]\s*)(&\s*)?(?P<direct>[^\s;&|()]+\.(ps1|sh|bat|cmd))(?=[\s;&|)]|$)")

ASK_RULES: list[tuple[str, str]] = [
    ("git-commit", r"\bgit\s+commit\b"),
    ("git-push", r"\bgit\s+push\b"),
    ("git-history", r"\bgit\s+(merge|rebase|cherry-pick|revert|tag|am|apply|reset|restore|rm|stash)\b"
                    r"|\bgit\s+checkout\s+(--|\.)|\bgit\s+branch\s+(-d|-m|--delete|--move)\b"),
    ("git-config", r"\bgit\s+(config|remote\s+(add|set-url|remove|rm))\b"),
    ("github", r"\bgh\s+(?!(--version|auth\s+status|pr\s+(view|list|status|diff|checks)|run\s+(view|list))\b)"),
    ("deps", r"\b(pip|pip3|uv)\s+(install|uninstall)\b|-m\s+pip\s+(install|uninstall)\b"),
    ("schedule", r"\b(schtasks|register-scheduledtask|crontab)\b"),
    ("recursive-delete", RECURSIVE_DELETE),
]


def _moneylab(c: str) -> Decision:
    if "moneylab" not in c:
        return Decision(PASS)
    if re.search(r"\bresearch-final\b", c):
        return Decision(ASK, "research-final", "research-final opens the test split exactly once per run")
    if re.search(r"\bresearch-build\b", c) and "--dry-run" not in c:
        return Decision(ASK, "research-build", "a non-dry-run research-build creates an evidence run")
    if re.search(r"\brecord(?![-\w])", c) and not re.search(r"--source\s+fixture\b", c):
        return Decision(ASK, "record-live", "live recording opens a real market connection")
    return Decision(PASS)


def _tracked_files(root: Path) -> set[str] | None:
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return {p.lower() for p in r.stdout.decode("utf-8", errors="replace").split("\0") if p}


def _untracked_scripts(c: str, root: Path, cwd: str | None) -> list[str]:
    scripts = [m.group("script") or m.group("direct") for m in re.finditer(SCRIPT_RUN, c)]
    scripts = [s for s in scripts if s]
    if not scripts:
        return []
    tracked = _tracked_files(root)
    base = cwd or str(root)
    out = []
    for s in scripts:
        rel = _relative(s if os.path.isabs(s) or re.match(r"[a-z]:/", s) else os.path.join(base, s), root)
        if tracked is None or rel is None or rel not in tracked:
            out.append(s)
    return out


def check_command(cmd: str, root: Path = ROOT, cwd: str | None = None) -> Decision:
    if re.search(r"\bgit\s+branch\s+(.*\s)?-[a-zA-Z]*D", cmd):  # case matters: -D force-deletes, -d does not
        return Decision(DENY, "git", "blocked by guard rule 'git' (force branch delete)")
    c = normalize(cmd)
    for rule, pattern in DENY_RULES:
        if re.search(pattern, c):
            return Decision(DENY, rule, f"blocked by guard rule '{rule}'")
    if re.search(PROTECTED, c):
        # locked/: hashing or listing is allowed, any other access is not
        if re.search(r"/locked\b|locked/", c) and not re.fullmatch(
                r"(sha256sum|certutil -hashfile|get-filehash|ls|dir|get-childitem)\s[^;|&><]*", c):
            return Decision(DENY, "locked", "test split files under locked/ are opened only by research-final")
        if re.search(MUTATE, c) or re.search(r">>?\s*\S*" + PROTECTED, c):
            return Decision(DENY, "protected-path", "command would change a protected path")
    if re.search(DELETE_MOVE, c) and re.search(r"\b(raw|locked)\b", c):
        return Decision(DENY, "protected-word", "delete/move next to 'raw' or 'locked' (path may be hidden)")
    for rule, pattern in ASK_RULES:
        if re.search(pattern, c):
            return Decision(ASK, rule, f"guard rule '{rule}' needs user approval")
    if re.search(INLINE_CODE, c) and re.search(INLINE_EFFECT, c):
        return Decision(ASK, "inline-code", "inline code that can change files or run other code")
    untracked = _untracked_scripts(c, root, cwd)
    if untracked:
        return Decision(ASK, "untracked-script", f"runs a script git does not track: {', '.join(untracked)}")
    return _moneylab(c)


# ----------------------------------------------------------------------------------------- entry


def decide(payload: dict, root: Path = ROOT) -> Decision:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool, str) or not isinstance(tool_input, dict):
        return Decision(DENY, "malformed", "hook input has no tool_name/tool_input")
    if tool in SHELL_TOOLS:
        cmd = tool_input.get("command")
        if not isinstance(cmd, str):
            return Decision(DENY, "malformed", "shell tool call without a command")
        cwd = payload.get("cwd")
        return check_command(cmd, root, cwd if isinstance(cwd, str) else None)
    if tool in WRITE_TOOLS or tool in READ_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path")
        if not path:
            return Decision(DENY, "malformed", f"{tool} call without a path") if tool in WRITE_TOOLS \
                else Decision(PASS)
        return check_path(tool, str(path), root)
    return Decision(PASS)


def main(stdin=None, stdout=None, stderr=None) -> int:
    stdin, stdout, stderr = stdin or sys.stdin, stdout or sys.stdout, stderr or sys.stderr
    try:
        raw = stdin.buffer.read() if hasattr(stdin, "buffer") else stdin.read()
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        d = decide(json.loads(text))
    except Exception as exc:  # fail closed
        stderr.write(f"MoneyLab guard error ({type(exc).__name__}); call blocked\n")
        return 2
    if d.action == DENY:
        stderr.write(f"MoneyLab guard [{d.rule}]: {d.reason}\n")
        return 2
    if d.action == ASK:
        stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "ask",
            "permissionDecisionReason": f"MoneyLab guard [{d.rule}]: {d.reason}"}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
