"""AUTO-02 D14 / AC14: atomic_create_new_bytes never replaces a file and reports what it left behind."""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from moneylab.storage import atomic
from moneylab.storage.atomic import CreateNewError, atomic_create_new_bytes


def _tmps(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.name.endswith(atomic.TMP_SUFFIX))


def test_creates_a_new_file_with_exact_bytes_and_no_temp_left(tmp_path):
    target = tmp_path / "rec.json"
    assert atomic_create_new_bytes(target, b"data\n") == target
    assert target.read_bytes() == b"data\n"
    assert _tmps(tmp_path) == []


def test_existing_target_is_never_replaced(tmp_path):
    target = tmp_path / "rec.json"
    target.write_bytes(b"old")
    with pytest.raises(CreateNewError) as info:
        atomic_create_new_bytes(target, b"new")
    assert isinstance(info.value.cause, FileExistsError)
    assert info.value.final_created is False and info.value.tmp_leftover is None
    assert target.read_bytes() == b"old"
    assert _tmps(tmp_path) == []


def test_missing_parent_is_not_created(tmp_path):
    target = tmp_path / "missing" / "rec.json"
    with pytest.raises(CreateNewError) as info:
        atomic_create_new_bytes(target, b"x")
    assert isinstance(info.value.cause, FileNotFoundError)
    assert info.value.final_created is False
    assert not (tmp_path / "missing").exists()


@pytest.mark.parametrize("step", ["fsync", "link"])
def test_failure_before_link_leaves_no_final_file_and_no_temp(tmp_path, monkeypatch, step):
    def boom(*args, **kwargs):
        raise OSError(errno.EIO, f"injected {step} failure")

    monkeypatch.setattr(os, step, boom)
    target = tmp_path / "rec.json"
    with pytest.raises(CreateNewError) as info:
        atomic_create_new_bytes(target, b"x")
    assert isinstance(info.value.cause, OSError) and "injected" in str(info.value.cause)
    assert info.value.final_created is False and info.value.tmp_leftover is None
    assert not target.exists()
    assert _tmps(tmp_path) == []


def test_link_failure_and_temp_removal_failure_keep_the_original_error(tmp_path, monkeypatch):
    def link_fails(src, dst):
        raise OSError(errno.EIO, "injected link failure")

    def unlink_fails(path, *args, **kwargs):
        raise PermissionError(errno.EACCES, "injected unlink failure")

    monkeypatch.setattr(os, "link", link_fails)
    monkeypatch.setattr(os, "unlink", unlink_fails)
    target = tmp_path / "rec.json"
    with pytest.raises(CreateNewError) as info:
        atomic_create_new_bytes(target, b"x")
    monkeypatch.undo()
    error = info.value
    assert "injected link failure" in str(error.cause)
    assert error.final_created is False
    assert error.tmp_leftover is not None and error.tmp_leftover.exists()
    assert not target.exists()


def test_unlink_failure_after_link_reports_a_complete_final_file(tmp_path, monkeypatch):
    def unlink_fails(path, *args, **kwargs):
        raise PermissionError(errno.EACCES, "injected unlink failure")

    monkeypatch.setattr(os, "unlink", unlink_fails)
    target = tmp_path / "rec.json"
    with pytest.raises(CreateNewError) as info:
        atomic_create_new_bytes(target, b"complete\n")
    monkeypatch.undo()
    error = info.value
    assert error.final_created is True
    assert error.tmp_leftover is not None and error.tmp_leftover.read_bytes() == b"complete\n"
    assert target.read_bytes() == b"complete\n"


def test_link_not_supported_never_falls_back_to_overwrite(tmp_path, monkeypatch):
    target = tmp_path / "rec.json"
    target.write_bytes(b"keep")

    def unsupported(src, dst):
        raise OSError(errno.EPERM, "injected: hard links not supported")

    monkeypatch.setattr(os, "link", unsupported)
    with pytest.raises(CreateNewError) as info:
        atomic_create_new_bytes(target, b"other")
    assert info.value.final_created is False
    assert target.read_bytes() == b"keep"
    assert _tmps(tmp_path) == []


def test_other_runs_temp_files_and_existing_files_are_left_alone(tmp_path):
    foreign_tmp = tmp_path / f".rec.json.foreign{atomic.TMP_SUFFIX}"
    foreign_tmp.write_bytes(b"other run")
    neighbour = tmp_path / "neighbour.json"
    neighbour.write_bytes(b"neighbour")
    atomic_create_new_bytes(tmp_path / "rec.json", b"x")
    with pytest.raises(CreateNewError):
        atomic_create_new_bytes(tmp_path / "rec.json", b"y")
    assert foreign_tmp.read_bytes() == b"other run"
    assert neighbour.read_bytes() == b"neighbour"
    assert (tmp_path / "rec.json").read_bytes() == b"x"
    assert _tmps(tmp_path) == [foreign_tmp]
