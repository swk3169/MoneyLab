"""D4-D8, D12: open one session file safely, take its complete-line prefix, find the selected entry and
choose one text block.

UNVERIFIED: the entry structure below (D7) is the structure the synthetic tests use. Whether real Claude
Code session files have this structure has not been checked; a different structure fails with
FORMAT_UNSUPPORTED and needs a new Work Order or ERRATA. Nothing is guessed or converted.

Lines that are not the target are parsed and checked for the identifying fields only; their content is
never kept in a result or printed. That is an output limit, not memory isolation. The prefix is checked
again after processing (ERRATA-001 E2.3), which is not an atomic snapshot of the whole file: a change that
is undone between the two reads is not detected. The 64 MiB limit applies to S0, the size at open (E2.1)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO

from moneylab.controlled_read import ControlledReadError
from moneylab.controlled_read.selector import ASSISTANT, Selector
from moneylab.workstate import collect
from moneylab.workstate.collect import WorkstateError

SESSION_LIMIT = 64 * 1024 * 1024  # ERRATA-001 E2.1: bytes of S0, the file size at open
LINE_LIMIT = 8 * 1024 * 1024  # D12: bytes of one line without its LF
ENTRY_LIMIT = 200_000  # D12: complete lines in the prefix
TIME_LIMIT = 60.0  # D12: monotonic seconds
CHUNK = 1024 * 1024

ASSISTANT_BLOCK_TYPES = frozenset({"text", "thinking", "redacted_thinking", "tool_use"})

# target.prefix_check values (ERRATA-001 E1.2); None means the prefix was never established.
MATCHED = "MATCHED"
TRUNCATED = "TRUNCATED"
CHANGED = "CHANGED"
INCOMPLETE = "INCOMPLETE"

# Seams for tests, looked up at call time.
_monotonic: Callable[[], float] = time.monotonic
_fstat = os.fstat


def _before_rehash(handle: BinaryIO) -> None:
    """Called after processing and before the prefix is read again (tests change the file here)."""


class Deadline:
    """D12 time limit, checked per line and before and after the second read of the prefix."""

    def __init__(self) -> None:
        self.end = _monotonic() + TIME_LIMIT

    def expired(self) -> bool:
        return _monotonic() > self.end

    def check(self) -> None:
        if self.expired():
            raise ControlledReadError("TIME_LIMIT_EXCEEDED")


def session_rel(project_key: str, session_id: str) -> str:
    """D4. Both values already matched the D2 grammar, so neither holds '/', '\\' or '..'."""
    return f".claude/projects/{project_key}/{session_id}.jsonl"


class Session:
    """An open session file and its prefix. `measurement` is filled in as soon as the prefix is known."""

    def __init__(self, handle: BinaryIO, prefix: bytes, measurement: dict[str, Any]) -> None:
        self.handle = handle
        self.prefix = prefix
        self.measurement = measurement

    def rehash(self, deadline: Deadline) -> tuple[str | None, str]:
        """ERRATA-001 E2.3: read [0, P) again. Returns (status that replaces the processing result or None,
        prefix_check). The first step that applies ends the check."""
        if deadline.expired():
            return "TIME_LIMIT_EXCEEDED", INCOMPLETE
        _before_rehash(self.handle)
        size = len(self.prefix)
        try:
            current = _fstat(self.handle.fileno()).st_size
        except OSError:
            return "SESSION_UNREADABLE", INCOMPLETE
        if current < size:
            return "SESSION_TRUNCATED", TRUNCATED
        try:
            self.handle.seek(0)
            again = _read_exactly(self.handle, size, deadline)
        except OSError:
            return "SESSION_UNREADABLE", INCOMPLETE
        except ControlledReadError as exc:
            if exc.code == "TIME_LIMIT_EXCEEDED":
                return "TIME_LIMIT_EXCEEDED", INCOMPLETE
            raise
        if len(again) < size:
            return "SESSION_TRUNCATED", TRUNCATED
        if hashlib.sha256(again).digest() != hashlib.sha256(self.prefix).digest():
            return "SESSION_CHANGED", CHANGED
        if deadline.expired():
            return "TIME_LIMIT_EXCEEDED", MATCHED
        return None, MATCHED


def _read_exactly(handle: BinaryIO, size: int, deadline: Deadline) -> bytes:
    parts: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = handle.read(min(CHUNK, remaining))
        if not chunk:
            break
        parts.append(chunk)
        remaining -= len(chunk)
        deadline.check()
    return b"".join(parts)


def open_session(home: Path, project_key: str, session_id: str, measurement: dict[str, Any],
                 deadline: Deadline) -> Session:
    """D4 and D5. The caller closes `Session.handle`."""
    rel = session_rel(project_key, session_id)
    try:
        before = collect.check_tree_path(home, rel, "SESSION_PATH_INVALID", require_regular=True)
    except WorkstateError:
        raise ControlledReadError("SESSION_PATH_INVALID") from None
    if before is None:
        raise ControlledReadError("SESSION_NOT_FOUND")
    try:
        handle = open(home / rel, "rb")  # noqa: SIM115 - closed by the caller
    except FileNotFoundError:
        raise ControlledReadError("SESSION_NOT_FOUND") from None
    except OSError:
        raise ControlledReadError("SESSION_PATH_INVALID") from None
    try:
        opened = _fstat(handle.fileno())
        if (before.st_size, before.st_dev, before.st_ino) != (opened.st_size, opened.st_dev, opened.st_ino):
            raise ControlledReadError("SESSION_PATH_INVALID")
        size = opened.st_size
        if size > SESSION_LIMIT:
            raise ControlledReadError("SESSION_LIMIT_EXCEEDED")
        try:
            data = _read_exactly(handle, size, deadline)
        except OSError:
            raise ControlledReadError("SESSION_UNREADABLE") from None
        if len(data) < size:
            raise ControlledReadError("SESSION_TRUNCATED")
    except BaseException:
        handle.close()
        raise
    prefix = data[:data.rfind(b"\n") + 1]
    measurement.update(prefix_bytes=len(prefix), prefix_sha256=hashlib.sha256(prefix).hexdigest(),
                       line_count=prefix.count(b"\n"), trailing_partial_bytes=size - len(prefix))
    return Session(handle, prefix, measurement)


# ------------------------------------------------------------------------------------------- JSONL


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = value
    return out


def _reject_constant(name: str) -> Any:
    raise ValueError("non-finite constant")


def _finite_float(text: str) -> float:
    value = float(text)
    if value in (float("inf"), float("-inf")):
        raise ValueError("float overflow")
    return value


def parse_line(line: bytes) -> dict[str, Any]:
    """D6: strict UTF-8, strict JSON (no duplicate keys, NaN, Infinity or overflow), one object."""
    try:
        text = line.decode("utf-8")
        obj = json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_constant,
                         parse_float=_finite_float)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise ControlledReadError("SESSION_CORRUPT") from None
    if not isinstance(obj, dict):
        raise ControlledReadError("SESSION_CORRUPT")
    return obj


def _lines(prefix: bytes, deadline: Deadline) -> list[bytes]:
    lines = prefix.split(b"\n")[:-1]  # the prefix ends with LF (or is empty)
    if len(lines) > ENTRY_LIMIT:
        raise ControlledReadError("ENTRY_LIMIT_EXCEEDED")
    for line in lines:
        if len(line) > LINE_LIMIT:
            raise ControlledReadError("LINE_LIMIT_EXCEEDED")
    deadline.check()
    return lines


def _user_blocks(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """The content blocks of a user entry whose message.content is a list (D7); [] otherwise."""
    if entry.get("type") != "user":
        return []
    message = entry.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), list):
        return []
    blocks = message["content"]
    for block in blocks:
        if not isinstance(block, dict) or not isinstance(block.get("type"), str):
            raise ControlledReadError("FORMAT_UNSUPPORTED")
    return blocks


def _find(lines: list[bytes], selector: Selector, deadline: Deadline) -> dict[str, Any]:
    """The one target entry (assistant) or tool_result block (tool_result)."""
    found: list[dict[str, Any]] = []
    for line in lines:
        deadline.check()
        entry = parse_line(line)
        uuid = entry.get("uuid")
        if "uuid" in entry and not isinstance(uuid, str):
            raise ControlledReadError("FORMAT_UNSUPPORTED")
        blocks = _user_blocks(entry)
        if selector.kind == ASSISTANT:
            if uuid == selector.ident:
                found.append(entry)
        else:
            for block in blocks:
                if block["type"] != "tool_result":
                    continue
                if not isinstance(block.get("tool_use_id"), str):
                    raise ControlledReadError("FORMAT_UNSUPPORTED")
                if block["tool_use_id"] == selector.ident:
                    found.append(block)
        if len(found) > 1:
            raise ControlledReadError("ENTRY_DUPLICATE")
    if not found:
        raise ControlledReadError("ENTRY_NOT_FOUND")
    return found[0]


def _assistant_texts(entry: dict[str, Any]) -> list[str]:
    kind = entry.get("type")
    if not isinstance(kind, str):
        raise ControlledReadError("FORMAT_UNSUPPORTED")
    if kind != "assistant":
        raise ControlledReadError("SELECTOR_KIND_MISMATCH")
    message = entry.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), list):
        raise ControlledReadError("FORMAT_UNSUPPORTED")
    texts: list[str] = []
    for block in message["content"]:
        if not isinstance(block, dict) or block.get("type") not in ASSISTANT_BLOCK_TYPES:
            raise ControlledReadError("FORMAT_UNSUPPORTED")
        if block["type"] == "text":
            if not isinstance(block.get("text"), str):
                raise ControlledReadError("FORMAT_UNSUPPORTED")
            texts.append(block["text"])
    return texts


def _tool_result_texts(block: dict[str, Any]) -> list[str]:
    if "is_error" in block:
        if not isinstance(block["is_error"], bool):
            raise ControlledReadError("FORMAT_UNSUPPORTED")
        if block["is_error"]:
            raise ControlledReadError("TOOL_RESULT_ERROR")
    content = block.get("content")
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        raise ControlledReadError("FORMAT_UNSUPPORTED")
    texts: list[str] = []
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "text" or not isinstance(item.get("text"), str):
            raise ControlledReadError("FORMAT_UNSUPPORTED")
        texts.append(item["text"])
    return texts


def select_text(prefix: bytes, selector: Selector, deadline: Deadline) -> str:
    """D6-D8: the selected text exactly as stored (blocks are never joined, nothing is stripped)."""
    target = _find(_lines(prefix, deadline), selector, deadline)
    texts = _assistant_texts(target) if selector.kind == ASSISTANT else _tool_result_texts(target)
    if selector.text_index is None:
        if not texts:
            raise ControlledReadError("TEXT_BLOCK_NOT_FOUND")
        if len(texts) > 1:
            raise ControlledReadError("TEXT_BLOCK_AMBIGUOUS")
        return texts[0]
    if selector.text_index > len(texts):
        raise ControlledReadError("TEXT_BLOCK_NOT_FOUND")
    return texts[selector.text_index - 1]
