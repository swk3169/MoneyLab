"""D2 argument grammar and selectors.

The shell has already split the command line, so the program sees tokens only: each value must fullmatch
its ASCII grammar and the options must come in the one fixed order, once each, with no extra token. The
exact spelling of the whole command line (single spaces, no quotes or tabs, the executable path, `-B`) is
judged by the guard, not here."""

from __future__ import annotations

import re
from dataclasses import dataclass

from moneylab.controlled_read import ControlledReadError
from moneylab.controlled_read.profiles import PROFILES

TASK_ID_MAX = 64
TASK_ID = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*", re.ASCII)
PROJECT_KEY = re.compile(r"[A-Za-z0-9-]{1,200}", re.ASCII)
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
SESSION = re.compile(_UUID, re.ASCII)
SELECTOR = re.compile(rf"(?:assistant:(?P<uuid>{_UUID})|tool_result:(?P<tool>[A-Za-z0-9_]{{1,128}}))"
                      r"(?::text:(?P<k>[1-9][0-9]?))?", re.ASCII)
ATTEMPT = re.compile(r"00[1-9]|0[1-9][0-9]|[1-9][0-9]{2}", re.ASCII)

RUN_OPTIONS = ("--task", "--project-key", "--session", "--selector", "--profile", "--attempt")
STATUS_OPTIONS = ("--task", "--attempt")
PRECHECK_OPTIONS = ("--task", "--project-key", "--session", "--profile")

ASSISTANT = "assistant"
TOOL_RESULT = "tool_result"


@dataclass(frozen=True)
class Selector:
    kind: str  # ASSISTANT or TOOL_RESULT
    ident: str  # entry uuid or tool_use_id
    text_index: int | None  # 1-based `:text:<k>`, or None


@dataclass(frozen=True)
class RunArgs:
    task_id: str
    project_key: str
    session_id: str
    selector: str
    profile: str
    attempt: str


@dataclass(frozen=True)
class StatusArgs:
    task_id: str
    attempt: str


@dataclass(frozen=True)
class PrecheckArgs:
    task_id: str
    project_key: str
    session_id: str
    profile: str


def valid_task_id(value: object) -> bool:
    return isinstance(value, str) and len(value) <= TASK_ID_MAX and TASK_ID.fullmatch(value) is not None


def valid_project_key(value: object) -> bool:
    return isinstance(value, str) and PROJECT_KEY.fullmatch(value) is not None


def valid_session(value: object) -> bool:
    return isinstance(value, str) and SESSION.fullmatch(value) is not None


def valid_selector(value: object) -> bool:
    return isinstance(value, str) and SELECTOR.fullmatch(value) is not None


def valid_profile(value: object) -> bool:
    return isinstance(value, str) and value in PROFILES


def valid_attempt(value: object) -> bool:
    return isinstance(value, str) and ATTEMPT.fullmatch(value) is not None


def parse_selector(value: str) -> Selector:
    m = SELECTOR.fullmatch(value)
    if m is None:
        raise ControlledReadError("ARGUMENT_INVALID")
    k = m.group("k")
    if m.group("uuid") is not None:
        return Selector(ASSISTANT, m.group("uuid"), int(k) if k else None)
    return Selector(TOOL_RESULT, m.group("tool"), int(k) if k else None)


def _values(argv: list[str], command: str, options: tuple[str, ...]) -> list[str]:
    if len(argv) != 1 + 2 * len(options) or argv[0] != command:
        raise ControlledReadError("ARGUMENT_INVALID")
    values = []
    for index, option in enumerate(options):
        if argv[1 + 2 * index] != option:
            raise ControlledReadError("ARGUMENT_INVALID")
        values.append(argv[2 + 2 * index])
    return values


def parse_run(argv: list[str]) -> RunArgs:
    task_id, project_key, session_id, selector, profile, attempt = _values(argv, "run", RUN_OPTIONS)
    if not (valid_task_id(task_id) and valid_project_key(project_key) and valid_session(session_id)
            and valid_selector(selector) and valid_profile(profile) and valid_attempt(attempt)):
        raise ControlledReadError("ARGUMENT_INVALID")
    return RunArgs(task_id, project_key, session_id, selector, profile, attempt)


def parse_status(argv: list[str]) -> StatusArgs:
    task_id, attempt = _values(argv, "status", STATUS_OPTIONS)
    if not (valid_task_id(task_id) and valid_attempt(attempt)):
        raise ControlledReadError("ARGUMENT_INVALID")
    return StatusArgs(task_id, attempt)


def parse_precheck(argv: list[str]) -> PrecheckArgs:
    """AUTO-09 D1: the precheck form. Same value grammar as run, without --selector and --attempt."""
    task_id, project_key, session_id, profile = _values(argv, "precheck", PRECHECK_OPTIONS)
    if not (valid_task_id(task_id) and valid_project_key(project_key) and valid_session(session_id)
            and valid_profile(profile)):
        raise ControlledReadError("ARGUMENT_INVALID")
    return PrecheckArgs(task_id, project_key, session_id, profile)


def format_selector(kind: str, ident: object, text_index: int) -> str | None:
    """AUTO-09 D5: the run selector of one candidate, always with `:text:<k>`. None when the identifier is
    not a string or the written selector does not fullmatch the run grammar (for example k=100)."""
    if not isinstance(ident, str):
        return None
    if kind == ASSISTANT:
        text = f"assistant:{ident}:text:{text_index}"
    elif kind == TOOL_RESULT:
        text = f"tool_result:{ident}:text:{text_index}"
    else:
        return None
    if SELECTOR.fullmatch(text) is None:
        return None
    return text
