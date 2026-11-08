"""Fixed action policy for the read-only automation API (AUTO-01, D1/D2/D4/D9).

The only registered action is `knowledge_validate`. Its argv, cwd and environment are derived here from the running
interpreter and this checkout; nothing is taken from callers, configuration files or user strings. These are code
constants: this module does not protect itself against a process with the same rights editing it (D9)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ACTION_KNOWLEDGE_VALIDATE = "knowledge_validate"
ALLOWED_ACTIONS: frozenset[str] = frozenset({ACTION_KNOWLEDGE_VALIDATE})

ALLOW = "ALLOW"
DENY = "DENY"

SUCCEEDED = "SUCCEEDED"
VALIDATION_FAILED = "VALIDATION_FAILED"
SOURCE_UNVERIFIED = "SOURCE_UNVERIFIED"
TIMEOUT = "TIMEOUT"
OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
UNEXPECTED_EXIT = "UNEXPECTED_EXIT"
DENIED = "DENIED"

# moneylab.knowledge exit codes (see its __main__ docstring); everything else, 2 included, is unexpected.
EXIT_STATUS: dict[int, str] = {0: SUCCEEDED, 1: VALIDATION_FAILED, 3: SOURCE_UNVERIFIED}

TIMEOUT_SECONDS = 60.0
OUTPUT_LIMIT_BYTES = 1_048_576  # stdout + stderr together

_PACKAGE_DIR = Path(__file__).resolve().parent


class AutomationError(RuntimeError):
    """The run could not be set up, reaped or reported. Never a success: the caller must stop."""


def decide(action_id: object) -> str:
    """ALLOW only the exact registered string; any other value (other types included) is DENY."""
    return ALLOW if type(action_id) is str and action_id in ALLOWED_ACTIONS else DENY


def status_for_exit_code(code: int) -> str:
    if type(code) is not int:
        raise AutomationError(f"exit code must be an int, got {type(code).__name__}")
    return EXIT_STATUS.get(code, UNEXPECTED_EXIT)


def repo_root() -> Path:
    """The checkout this package was imported from: <root>/src/moneylab/automation. Verified, not configurable."""
    root = _PACKAGE_DIR.parents[2]
    if not root.is_absolute():
        raise AutomationError("repository root is not absolute")
    if (root / "src" / "moneylab" / "automation").resolve() != _PACKAGE_DIR:
        raise AutomationError("package is not inside <root>/src/moneylab/automation")
    if not (root / ".git").exists() or not (root / "src" / "moneylab" / "knowledge").is_dir():
        raise AutomationError("repository root has no .git or no knowledge package")
    return root


def interpreter() -> str:
    exe = sys.executable
    if not exe or not os.path.isabs(exe) or not os.path.isfile(exe):
        raise AutomationError("sys.executable is not an absolute path to a file")
    return exe


def build_argv(root: Path) -> list[str]:
    """D2: the one fixed command. No --full-history."""
    return [interpreter(), "-m", "moneylab.knowledge", "--root", str(root), "validate"]


def git_directory() -> str:
    """Directory of the git executable the validator will run; raises when git cannot be found."""
    git = shutil.which("git")
    if git is None:
        raise AutomationError("git executable not found on PATH")
    directory = os.path.dirname(os.path.abspath(git))
    if not os.path.isdir(directory):
        raise AutomationError("git directory does not exist")
    return directory


def build_env() -> dict[str, str]:
    """D4 allowlist: PATH reduced to the git directory, plus SYSTEMROOT on Windows. Nothing else is inherited."""
    env = {"PATH": git_directory()}
    if os.name == "nt":
        system_root = os.environ.get("SYSTEMROOT")
        if not system_root:
            raise AutomationError("SYSTEMROOT is not set")
        env["SYSTEMROOT"] = system_root
    return env
