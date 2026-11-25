"""AUTO-08 D4-D8, D12 on synthetic session files under a tmp_path home (TEST_GATES: transcript, paths).

The home directory is always a seam argument: the real home and real session records are never opened."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from moneylab.controlled_read import ControlledReadError, transcript
from moneylab.controlled_read.selector import parse_selector
from moneylab.workstate import collect

PK = "C--synthetic-project"
SID = "0a1b2c3d-0000-4000-8000-00000000abcd"
UUID = "11111111-2222-4333-8444-555555555555"


def line(obj: object) -> bytes:
    return json.dumps(obj).encode("utf-8") + b"\n"


TARGET = line({"type": "assistant", "uuid": UUID, "message": {"content": [{"type": "text", "text": "body"}]}})
OTHER = line({"type": "user", "uuid": "22222222-2222-4333-8444-555555555555", "message": {"content": "hi"}})


@pytest.fixture
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    (h / ".claude" / "projects" / PK).mkdir(parents=True)
    return h


def session_path(home: Path) -> Path:
    return home / ".claude" / "projects" / PK / f"{SID}.jsonl"


def write(home: Path, data: bytes) -> Path:
    path = session_path(home)
    path.write_bytes(data)
    return path


def read(home: Path, measurement: dict | None = None) -> str:
    """open_session + select_text + rehash (ERRATA-001 E2.3). A replacing status is raised as that code."""
    m = {} if measurement is None else measurement
    deadline = transcript.Deadline()
    session = transcript.open_session(home, PK, SID, m, deadline)
    try:
        text = transcript.select_text(session.prefix, parse_selector(f"assistant:{UUID}"), deadline)
        replaced, check = session.rehash(deadline)
    finally:
        session.handle.close()
    m["prefix_check"] = check
    if replaced is not None:
        raise ControlledReadError(replaced)
    return text


def rehash_of(home: Path) -> tuple[str | None, str]:
    """open_session + rehash only."""
    deadline = transcript.Deadline()
    session = transcript.open_session(home, PK, SID, {}, deadline)
    try:
        return session.rehash(deadline)
    finally:
        session.handle.close()


def code(home: Path, measurement: dict | None = None) -> str:
    with pytest.raises(ControlledReadError) as info:
        read(home, measurement)
    return info.value.code


def test_reads_target_and_measures_prefix(home):
    data = OTHER + TARGET + b"{\"partial"
    write(home, data)
    m: dict = {}
    assert read(home, m) == "body"
    prefix = OTHER + TARGET
    assert m == {"prefix_bytes": len(prefix), "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
                 "line_count": 2, "trailing_partial_bytes": len(b"{\"partial"), "prefix_check": "MATCHED"}


# ------------------------------------------------------------------------------------- D6 corrupt


@pytest.mark.parametrize("bad", [
    b"{not json}", b"{\"a\": 1, \"a\": 2}", b"{\"a\": NaN}", b"{\"a\": Infinity}", b"{\"a\": -Infinity}",
    b"{\"a\": 1e999}", b"\xff\xfe{}", b"[1, 2]", b"\"text\"", b"", b"\xef\xbb\xbf{}", b"{\"a\": \"\xc3\"}",
])
def test_non_target_line_corruption(home, bad):
    write(home, OTHER + bad + b"\n" + TARGET)
    assert code(home) == "SESSION_CORRUPT"


def test_target_only_in_the_unfinished_last_line(home):
    write(home, OTHER + TARGET[:-1])
    m: dict = {}
    assert code(home, m) == "ENTRY_NOT_FOUND"
    assert m["trailing_partial_bytes"] == len(TARGET) - 1
    assert m["prefix_bytes"] == len(OTHER)


def test_file_without_any_lf_has_an_empty_prefix(home):
    write(home, TARGET[:-1])
    m: dict = {}
    assert code(home, m) == "ENTRY_NOT_FOUND"
    assert (m["prefix_bytes"], m["line_count"], m["trailing_partial_bytes"]) == (0, 0, len(TARGET) - 1)


# --------------------------------------------------------------------------- D5 second read


def test_append_after_the_prefix_is_not_a_failure(home, monkeypatch):
    path = write(home, OTHER + TARGET)

    def append(_handle):
        with open(path, "ab") as f:
            f.write(OTHER + b"{\"more")
    monkeypatch.setattr(transcript, "_before_rehash", append)
    assert read(home) == "body"


def test_change_inside_the_prefix(home, monkeypatch):
    path = write(home, OTHER + TARGET)

    def change(_handle):
        with open(path, "r+b") as f:
            f.seek(2)
            f.write(b"X")
    monkeypatch.setattr(transcript, "_before_rehash", change)
    assert code(home) == "SESSION_CHANGED"


def test_truncation_below_the_prefix(home, monkeypatch):
    path = write(home, OTHER + TARGET)
    monkeypatch.setattr(transcript, "_before_rehash", lambda _handle: os.truncate(path, 5))
    assert code(home) == "SESSION_TRUNCATED"


def test_truncation_and_change_together_is_truncation(home, monkeypatch):
    path = write(home, OTHER + TARGET)

    def both(_handle):
        with open(path, "r+b") as f:
            f.seek(0)
            f.write(b"X")
        os.truncate(path, len(OTHER + TARGET) - 1)
    monkeypatch.setattr(transcript, "_before_rehash", both)
    assert rehash_of(home) == ("SESSION_TRUNCATED", "TRUNCATED")


def test_rehash_fstat_error_is_unreadable_and_incomplete(home, monkeypatch):
    write(home, OTHER + TARGET)
    real = transcript._fstat

    def fail(_handle):
        def boom(_fd):
            raise OSError("gone")
        monkeypatch.setattr(transcript, "_fstat", boom)
    monkeypatch.setattr(transcript, "_before_rehash", fail)
    assert rehash_of(home) == ("SESSION_UNREADABLE", "INCOMPLETE")
    monkeypatch.setattr(transcript, "_fstat", real)


def test_rehash_read_error_is_unreadable_and_incomplete(home, monkeypatch):
    write(home, OTHER + TARGET)
    real = transcript._read_exactly
    calls: list[int] = []

    def second_fails(handle, size, deadline):
        calls.append(size)
        if len(calls) > 1:
            raise OSError("read")
        return real(handle, size, deadline)
    monkeypatch.setattr(transcript, "_read_exactly", second_fails)
    assert rehash_of(home) == ("SESSION_UNREADABLE", "INCOMPLETE")


def test_first_read_error_is_unreadable_without_a_prefix(home, monkeypatch):
    write(home, OTHER + TARGET)

    def fail(*_args):
        raise OSError("read")
    monkeypatch.setattr(transcript, "_read_exactly", fail)
    m: dict = {}
    assert code(home, m) == "SESSION_UNREADABLE"
    assert m == {}


def test_time_out_after_a_match_keeps_matched(home, monkeypatch):
    write(home, OTHER + TARGET)
    deadline = transcript.Deadline()
    session = transcript.open_session(home, PK, SID, {}, deadline)
    real_read = transcript._read_exactly

    def read_then_expire(handle, size, dl):
        data = real_read(handle, size, dl)
        monkeypatch.setattr(transcript, "_monotonic", lambda: dl.end + 1.0)
        return data
    monkeypatch.setattr(transcript, "_read_exactly", read_then_expire)
    try:
        assert session.rehash(deadline) == ("TIME_LIMIT_EXCEEDED", "MATCHED")
    finally:
        session.handle.close()


def test_time_out_before_the_rehash_is_incomplete(home, monkeypatch):
    write(home, OTHER + TARGET)
    deadline = transcript.Deadline()
    session = transcript.open_session(home, PK, SID, {}, deadline)
    called: list = []
    monkeypatch.setattr(transcript, "_before_rehash", lambda h: called.append(h))
    monkeypatch.setattr(transcript, "_monotonic", lambda: deadline.end + 1.0)
    try:
        assert session.rehash(deadline) == ("TIME_LIMIT_EXCEEDED", "INCOMPLETE")
    finally:
        session.handle.close()
    assert called == []


def test_short_read_at_open_is_truncation(home, monkeypatch):
    write(home, OTHER + TARGET)
    real = transcript._fstat

    class Bigger:
        def __init__(self, st):
            self._st = st

        def __getattr__(self, name):
            return self._st.st_size + 10 if name == "st_size" else getattr(self._st, name)

    monkeypatch.setattr(collect, "_lstat", lambda p: Bigger(os.lstat(p)) if str(p).endswith(".jsonl")
                        else os.lstat(p))
    monkeypatch.setattr(transcript, "_fstat", lambda fd: Bigger(real(fd)))
    assert code(home) == "SESSION_TRUNCATED"


# ------------------------------------------------------------------------------------ D12 limits


def test_session_limit(home, monkeypatch):
    write(home, OTHER + TARGET)
    monkeypatch.setattr(transcript, "SESSION_LIMIT", len(OTHER + TARGET) - 1)
    m: dict = {}
    assert code(home, m) == "SESSION_LIMIT_EXCEEDED"
    assert m == {}
    monkeypatch.setattr(transcript, "SESSION_LIMIT", len(OTHER + TARGET))
    assert read(home) == "body"


def test_line_limit(home, monkeypatch):
    write(home, OTHER + TARGET)
    monkeypatch.setattr(transcript, "LINE_LIMIT", len(TARGET) - 2)
    assert code(home) == "LINE_LIMIT_EXCEEDED"
    monkeypatch.setattr(transcript, "LINE_LIMIT", len(TARGET) - 1)
    assert read(home) == "body"


def test_entry_limit(home, monkeypatch):
    write(home, OTHER + OTHER + TARGET)
    monkeypatch.setattr(transcript, "ENTRY_LIMIT", 2)
    assert code(home) == "ENTRY_LIMIT_EXCEEDED"
    monkeypatch.setattr(transcript, "ENTRY_LIMIT", 3)
    assert read(home) == "body"


@pytest.mark.parametrize("calls_before_timeout", [1, 2, 3, 5, 6])
def test_time_limit_with_a_fake_clock(home, monkeypatch, calls_before_timeout):
    """Deadline creation is call 0; the per-line and second-read checks come after it."""
    write(home, OTHER + OTHER + TARGET)
    ticks = iter(range(10_000))
    monkeypatch.setattr(transcript, "TIME_LIMIT", 0.5)
    monkeypatch.setattr(transcript, "_monotonic",
                        lambda: 0.0 if next(ticks) < calls_before_timeout else 100.0)
    assert code(home) == "TIME_LIMIT_EXCEEDED"


def test_time_limit_not_reached(home, monkeypatch):
    write(home, OTHER + TARGET)
    monkeypatch.setattr(transcript, "_monotonic", lambda: 5.0)
    assert read(home) == "body"


# ------------------------------------------------------------------------------------- D4 paths


def test_missing_components(tmp_path):
    assert code(tmp_path / "nohome") == "SESSION_NOT_FOUND"
    h = tmp_path / "h"
    (h / ".claude" / "projects").mkdir(parents=True)
    assert code(h) == "SESSION_NOT_FOUND"
    (h / ".claude" / "projects" / PK).mkdir()
    assert code(h) == "SESSION_NOT_FOUND"


def test_session_path_that_is_a_directory(home):
    session_path(home).mkdir()
    assert code(home) == "SESSION_PATH_INVALID"


def test_parent_that_is_a_file(tmp_path):
    h = tmp_path / "h"
    (h / ".claude").mkdir(parents=True)
    (h / ".claude" / "projects").write_bytes(b"x")
    assert code(h) == "SESSION_PATH_INVALID"


@pytest.mark.parametrize("component", [".claude", "projects", PK, f"{SID}.jsonl"])
def test_link_like_component_via_seam(home, monkeypatch, component):
    write(home, OTHER + TARGET)
    real = collect.is_link_like
    monkeypatch.setattr(collect, "is_link_like", lambda p, st: Path(p).name == component or real(p, st))
    assert code(home) == "SESSION_PATH_INVALID"


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="junctions are a Windows feature")
def test_real_junction_in_the_path(tmp_path):
    import _winapi
    real = tmp_path / "elsewhere"
    real.mkdir()
    (real / f"{SID}.jsonl").write_bytes(OTHER + TARGET)
    h = tmp_path / "h"
    (h / ".claude" / "projects").mkdir(parents=True)
    _winapi.CreateJunction(str(real), str(h / ".claude" / "projects" / PK))
    assert code(h) == "SESSION_PATH_INVALID"


def test_real_symlink_file(home, tmp_path):
    target = tmp_path / "t.jsonl"
    target.write_bytes(OTHER + TARGET)
    try:
        os.symlink(target, session_path(home))
    except (OSError, NotImplementedError):
        pytest.skip("symlinks cannot be created on this platform")
    assert code(home) == "SESSION_PATH_INVALID"


@pytest.mark.parametrize("field", ["st_size", "st_dev", "st_ino"])
def test_lstat_and_fstat_mismatch(home, monkeypatch, field):
    write(home, OTHER + TARGET)
    real = transcript._fstat

    class Shifted:
        def __init__(self, st):
            self.st_size, self.st_dev, self.st_ino = st.st_size, st.st_dev, st.st_ino
            setattr(self, field, getattr(st, field) + 1)

    monkeypatch.setattr(transcript, "_fstat", lambda fd: Shifted(real(fd)))
    assert code(home) == "SESSION_PATH_INVALID"


def test_session_rel_is_fixed():
    assert transcript.session_rel(PK, SID) == f".claude/projects/{PK}/{SID}.jsonl"
