"""AUTO-02 AC5, AC12: argument errors and every other outcome are one canonical result object on stdout with
the fixed keys and `authority: "NONE"`; there is no latest or list path."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from moneylab.workstate import __main__ as cli_module
from moneylab.workstate import store

ZERO = "0" * 64
TASK = "T-1"
RO_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}


def run_module(*args: str, cwd: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, "-B", "-m", "moneylab.workstate", *args], capture_output=True,
                          cwd=cwd, timeout=120)


def assert_result_shape(result: dict) -> None:
    assert set(result) == cli_module.RESULT_KEYS
    assert result["schema"] == "moneylab.workstate.result/1"
    assert result["authority"] == "NONE"
    assert result["compared"] == list(cli_module.COMPARED)
    assert result["not_compared"] == list(cli_module.NOT_COMPARED)


BAD_ARGS = [
    [],
    ["latest"],
    ["verify", "--task-id", TASK],
    ["verify", "--snapshot-id", ZERO],
    ["verify", "--task-id", "bad id", "--snapshot-id", ZERO],
    ["verify", "--task-id", TASK, "--snapshot-id", "XYZ"],
    ["snapshot", "--task-id", TASK, "--bogus"],
    ["snapshot", "--task-id", TASK, "--reported-gate", "COMMIT"],
    ["snapshot", "--task-id", TASK, "--reported-gate", "NOPE", "--reported-result", "PASS"],
]


@pytest.mark.parametrize("args", BAD_ARGS, ids=[" ".join(a) or "empty" for a in BAD_ARGS])
def test_argument_errors_are_one_canonical_result(args, tmp_path):
    proc = run_module(*args, cwd=tmp_path)
    assert proc.returncode == 2
    assert proc.stderr == b""
    text = proc.stdout.decode("utf-8")
    assert text.endswith("\n") and text.count("\n") == 1
    result = json.loads(text)
    assert text == store.canonical_text(result) + "\n"
    assert_result_shape(result)
    assert result["status"] == "ARGUMENT_INVALID" and result["exit_code"] == 2
    assert result["error"]["code"] == "ARGUMENT_INVALID"
    assert list(tmp_path.iterdir()) == []


def test_only_snapshot_and_verify_exist():
    parser = cli_module.build_parser()
    choices = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]
    assert len(choices) == 1 and set(choices[0].choices) == {"snapshot", "verify"}


def test_help_is_the_only_plain_text_output(tmp_path):
    proc = run_module("--help", cwd=tmp_path)
    assert proc.returncode == 0
    assert b"snapshot" in proc.stdout and b"verify" in proc.stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@example.invalid"],
                 ["config", "user.name", "T"], ["config", "core.autocrlf", "false"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=RO_ENV)
    (repo / ".gitignore").write_bytes(b"data/processed/*\n")
    (repo / "a.txt").write_bytes(b"alpha\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True, env=RO_ENV)
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "commit", "-q", "-m", "init"],
                   check=True, capture_output=True, env=RO_ENV)
    return repo


def test_every_outcome_has_the_fixed_keys_and_exit_codes(tmp_path, capsys, monkeypatch):
    repo = _repo(tmp_path)

    def call(*args: str) -> dict:
        code = cli_module.main(list(args), root=repo)
        out = capsys.readouterr().out
        result = json.loads(out)
        assert out == store.canonical_text(result) + "\n"
        assert result["exit_code"] == code
        assert_result_shape(result)
        return result

    stored = call("snapshot", "--task-id", TASK, "--reported-gate", "COMMIT", "--reported-result", "NO")
    assert (stored["status"], stored["exit_code"]) == ("STORED", 0)
    assert stored["reported"] == {"gate": "COMMIT", "result": "NO"}
    assert stored["reported_status"] == "REPORTED_UNVERIFIED"
    again = call("snapshot", "--task-id", TASK, "--reported-gate", "COMMIT", "--reported-result", "NO")
    assert (again["status"], again["exit_code"]) == ("ALREADY_STORED", 0)
    match = call("verify", "--task-id", TASK, "--snapshot-id", stored["snapshot_id"])
    assert (match["status"], match["exit_code"], match["warnings"]) == ("MATCH", 0, [])
    assert match["reported"] == stored["reported"] and match["final_file_created"] is None
    (repo / "a.txt").write_bytes(b"changed\n")
    mismatch = call("verify", "--task-id", TASK, "--snapshot-id", stored["snapshot_id"])
    assert (mismatch["status"], mismatch["exit_code"]) == ("MISMATCH", 1)
    assert all(set(item) == {"field", "stored", "current"} for item in mismatch["differences"])
    missing = call("verify", "--task-id", TASK, "--snapshot-id", ZERO)
    assert (missing["status"], missing["exit_code"], missing["file_sha256"]) == ("SNAPSHOT_NOT_FOUND", 2, None)
    real = os.unlink

    def unlink(path, *args, **kwargs):
        if str(path).endswith(".tmp"):
            raise PermissionError("injected")
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", unlink)
    warned = call("snapshot", "--task-id", TASK)
    monkeypatch.undo()
    assert (warned["status"], warned["exit_code"]) == ("STORED", 1)
    assert warned["warnings"][0].startswith("TMP_LEFTOVER:")


def _verify_call(repo: Path, capsys, snapshot_id: str) -> dict:
    code = cli_module.main(["verify", "--task-id", TASK, "--snapshot-id", snapshot_id], root=repo)
    result = json.loads(capsys.readouterr().out)
    assert result["exit_code"] == code
    assert_result_shape(result)
    return result


def test_match_is_decided_by_the_whole_state_not_by_the_differences(tmp_path, capsys, monkeypatch):
    """D11 step 10: the description of differences cannot turn a changed state into MATCH, and a spurious
    description cannot turn an equal state into MISMATCH."""
    repo = _repo(tmp_path)
    assert cli_module.main(["snapshot", "--task-id", TASK], root=repo) == 0
    stored = json.loads(capsys.readouterr().out)
    monkeypatch.setattr(store, "compare_states", lambda before, after: [{"field": "x", "stored": 1, "current": 2}])
    same = _verify_call(repo, capsys, stored["snapshot_id"])
    assert (same["status"], same["exit_code"], same["differences"]) == ("MATCH", 0, [])
    monkeypatch.setattr(store, "compare_states", lambda before, after: [])
    (repo / "a.txt").write_bytes(b"changed\n")
    changed = _verify_call(repo, capsys, stored["snapshot_id"])
    assert (changed["status"], changed["exit_code"]) == ("MISMATCH", 1)
    assert changed["differences"] == [{"field": "state", "stored": stored["state_sha256_current"],
                                       "current": changed["state_sha256_current"]}]
    assert changed["state_sha256_current"] != stored["state_sha256_current"]


def test_root_that_is_not_a_worktree_top_level_is_an_environment_error(tmp_path, capsys):
    repo = _repo(tmp_path)
    (repo / "sub").mkdir()
    code = cli_module.main(["verify", "--task-id", TASK, "--snapshot-id", ZERO], root=repo / "sub")
    result = json.loads(capsys.readouterr().out)
    assert code == 2 and result["status"] == "ENVIRONMENT_INVALID"


def test_real_checkout_verify_of_an_unknown_id_writes_nothing(tmp_path):
    checkout = Path(cli_module.__file__).resolve().parents[3]
    store_dir = checkout / "data" / "processed" / "workstate"
    existed = store_dir.exists()
    proc = run_module("verify", "--task-id", "AUTO-02", "--snapshot-id", ZERO, cwd=tmp_path)
    result = json.loads(proc.stdout)
    assert proc.returncode == 2 and proc.stderr == b""
    assert result["status"] == "SNAPSHOT_NOT_FOUND"
    assert result["file_sha256"] is None and result["final_file_created"] is None
    assert store_dir.exists() == existed
