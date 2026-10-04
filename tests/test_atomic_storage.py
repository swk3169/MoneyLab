import json
import os

import pytest

from moneylab.storage import atomic
from moneylab.storage.atomic import atomic_write_json, atomic_write_text, cleanup_tmp, sha256_of


def test_atomic_write_creates_and_overwrites_without_leftovers(tmp_path):
    p = tmp_path / "a" / "b.json"
    atomic_write_json(p, {"x": 1})
    atomic_write_json(p, {"x": 2})
    assert json.loads(p.read_text(encoding="utf-8")) == {"x": 2}
    assert list(p.parent.iterdir()) == [p]


def test_failed_replace_keeps_old_content_and_removes_tmp(tmp_path, monkeypatch):
    p = tmp_path / "state.json"
    atomic_write_text(p, "old")

    def broken(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(atomic.os, "replace", broken)
    with pytest.raises(OSError):
        atomic_write_text(p, "new")
    assert p.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.iterdir()) == [p]


def test_replace_retries_transient_permission_error(tmp_path, monkeypatch):
    calls = []
    real = os.replace

    def flaky(src, dst):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError("locked by another process")
        real(src, dst)

    monkeypatch.setattr(atomic.os, "replace", flaky)
    monkeypatch.setattr(atomic.time, "sleep", lambda s: None)
    atomic_write_text(tmp_path / "f.txt", "ok")
    assert (tmp_path / "f.txt").read_text(encoding="utf-8") == "ok" and len(calls) == 3


def test_cleanup_tmp_removes_interrupted_writes(tmp_path):
    (tmp_path / "records").mkdir()
    leftover = tmp_path / "records" / ".0000000001.json.abc.tmp"
    leftover.write_text("{partial", encoding="utf-8")
    keep = tmp_path / "records" / "0000000001.json"
    keep.write_text("{}", encoding="utf-8")
    assert cleanup_tmp(tmp_path) == [leftover]
    assert keep.exists() and not leftover.exists()


def test_sha256_is_key_order_independent():
    assert sha256_of({"a": 1, "b": [1, 2]}) == sha256_of({"b": [1, 2], "a": 1})
    assert sha256_of({"a": 1}) != sha256_of({"a": 2})
