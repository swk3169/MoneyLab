"""Code state of a backtest run: commit plus a classified working tree (BT-2b-2 follow-up).

The caller (cli.py) runs `git rev-parse HEAD` and `git status --porcelain=v1 -z --untracked-files=all`;
this module only parses and classifies the output (no subprocess in backtest/).

Policy CODE_STATE_POLICY:
  tracked change (staged or unstaged, any status except ?? and !!)              blocking
  untracked file under src/, configs/ or tests/                                   blocking
  untracked file with an execution-relevant suffix anywhere (.py, .toml, ...)     blocking
  untracked text document under docs/ (.md, .rst, .txt)                           allowed, listed
  any other untracked file                                                        blocking (unclassified)
Ignored files (.gitignore: .venv, data/, caches) are not listed by git and are not considered; run inputs
and the settings file are pinned by their own hashes. A run's code is pinned only when the commit is known,
git status was read and nothing blocking exists, both at run time and at verification.
"""

from __future__ import annotations

from typing import Any

CODE_STATE_POLICY = "bt-code-state/v1"
BLOCKING_DIRS = ("src/", "configs/", "tests/")
EXECUTION_SUFFIXES = (".py", ".pyi", ".pyc", ".pth", ".pyd", ".so", ".dll", ".toml", ".cfg", ".ini", ".json",
                      ".yaml", ".yml", ".env")
ALLOWED_DOC_DIR = "docs/"
ALLOWED_DOC_SUFFIXES = (".md", ".rst", ".txt")
_LIST_LIMIT = 5


def parse_porcelain_z(text: str) -> list[tuple[str, str]]:
    """`git status --porcelain=v1 -z` -> [(XY, path)]. A rename or copy also yields its source path."""
    tokens = text.split("\0")
    out: list[tuple[str, str]] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        i += 1
        if not tok:
            continue
        if len(tok) < 4 or tok[2] != " ":
            raise ValueError(f"unexpected porcelain entry {tok!r}")
        xy, path = tok[:2], tok[3:]
        out.append((xy, path))
        if xy[0] in "RC" and i < len(tokens):
            out.append((xy, tokens[i]))
            i += 1
    return out


def untracked_is_allowed(path: str) -> bool:
    p = path.replace("\\", "/")
    low = p.lower()
    if p.startswith(BLOCKING_DIRS) or low.endswith(EXECUTION_SUFFIXES):
        return False
    return p.startswith(ALLOWED_DOC_DIR) and low.endswith(ALLOWED_DOC_SUFFIXES)


def classify_worktree(commit: str | None, entries: list[tuple[str, str]] | None) -> dict[str, Any]:
    """Code state recorded in the run manifest. `entries` is None when git status could not be read."""
    tracked: set[str] = set()
    blocking: set[str] = set()
    allowed: set[str] = set()
    for xy, path in entries or ():
        if xy == "!!":
            continue
        if xy == "??":
            (allowed if untracked_is_allowed(path) else blocking).add(path)
        else:
            tracked.add(path)
    status_read = entries is not None
    return {
        "policy": CODE_STATE_POLICY,
        "commit": commit,
        "status_read": status_read,
        "tracked_changes": sorted(tracked),
        "untracked_blocking": sorted(blocking),
        "untracked_allowed": sorted(allowed),
        "dirty": (bool(tracked or blocking) if status_read else None),
    }


def _short(paths: list[str]) -> str:
    more = f" (+{len(paths) - _LIST_LIMIT} more)" if len(paths) > _LIST_LIMIT else ""
    return ", ".join(paths[:_LIST_LIMIT]) + more


def code_state_problems(state: dict[str, Any]) -> list[str]:
    """Reasons why the code of this state cannot be pinned (empty list: pinned)."""
    if state.get("policy") != CODE_STATE_POLICY:
        return [f"code state has no {CODE_STATE_POLICY} worktree classification"]
    problems = []
    if not state.get("commit"):
        problems.append("commit unknown")
    if state.get("status_read") is not True:
        problems.append("git status could not be read")
    if state.get("tracked_changes"):
        problems.append(f"tracked changes: {_short(state['tracked_changes'])}")
    if state.get("untracked_blocking"):
        problems.append(f"untracked files that can affect execution: {_short(state['untracked_blocking'])}")
    if not problems and state.get("dirty") is not False:
        problems.append("dirty flag is not False")
    return problems
