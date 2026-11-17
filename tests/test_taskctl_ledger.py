"""taskctl ledger: chain, gaps, format, size and value limits, create-new failures (GOV-AUTOMATION-03 D4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_taskctl_cli import (
    TASK,
    Taskctl,
    make_repo,
    needs_git,
    taskctl_templates,  # noqa: F401  (autouse: checks the shared templates after each test)
    to_setup_done,
)

from moneylab.storage.atomic import CreateNewError
from moneylab.taskctl import ledger as LG
from moneylab.taskctl.ledger import TaskctlError

H40 = "1" * 40
H64 = "2" * 64
STATE = {"head": H40, "tree": H40, "index_empty": True, "status_sha256": H64, "changed": [],
         "outside_changes": 0, "untracked_unexpected": 0, "ignored_top_sha256": H64}


def events_dir(root: Path) -> Path:
    return root / LG.LEDGER_ROOT / TASK / "events"


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    to_setup_done(repo, base, c1, tc)
    return repo, tc


@needs_git
def test_valid_chain_reads_in_order(ledger):
    repo, _ = ledger
    events = LG.read_events(repo.root, TASK)
    assert [event["seq"] for event, _, _ in events] == list(range(1, len(events) + 1))
    assert events[0][0]["prev_sha256"] == LG.ZERO_SHA
    for (_, sha, _), (nxt, _, _) in zip(events, events[1:]):
        assert nxt["prev_sha256"] == sha


@needs_git
def test_gap_is_detected(ledger):
    repo, tc = ledger
    (events_dir(repo.root) / "000002.json").unlink()
    assert tc("status")["code"] == "LEDGER_GAP"


@needs_git
def test_chain_break_is_detected(ledger):
    repo, tc = ledger
    path = events_dir(repo.root) / "000003.json"
    event = json.loads(path.read_bytes())
    event["prev_sha256"] = "0" * 64
    path.write_bytes(LG.event_bytes(event))
    assert tc("status")["code"] == "LEDGER_CHAIN"


@needs_git
@pytest.mark.parametrize("damage", [
    lambda raw: raw + b"\n",                       # not canonical
    lambda raw: b"{not json",
    lambda raw: raw.replace(b'"kind":"STEP_START"', b'"kind":"OTHER"'),
])
def test_format_damage_is_detected(ledger, damage):
    repo, tc = ledger
    path = events_dir(repo.root) / "000002.json"
    path.write_bytes(damage(path.read_bytes()))
    assert tc("status")["code"] == "LEDGER_FORMAT"


@needs_git
def test_unexpected_file_in_events_is_format_damage_but_temp_files_are_ignored(ledger):
    repo, tc = ledger
    (events_dir(repo.root) / ".000009.json.abc.tmp").write_bytes(b"partial")
    assert tc("status")["code"] == "OK"
    (events_dir(repo.root) / "notes.txt").write_bytes(b"x")
    assert tc("status")["code"] == "LEDGER_FORMAT"


@needs_git
def test_existing_event_is_never_overwritten(ledger):
    repo, _ = ledger
    events = LG.read_events(repo.root, TASK)
    with pytest.raises(TaskctlError) as err:
        LG.append_event(repo.root, TASK, events[:-1], "PR_TEXT", "2026-11-16T12:00:00Z", {"sha256": H64, "bytes": 1})
    assert err.value.code == "CONCURRENT"
    assert LG.read_events(repo.root, TASK) == events


def test_event_too_large_is_not_written(tmp_path):
    many = [[f"a/{n:03d}" + "x" * 200, "M", H64] for n in range(30)]
    with pytest.raises(TaskctlError) as err:
        LG.build_event(TASK, 2, H64, "STEP_START", "2026-11-16T12:00:00Z",
                       {"step": "IMPLEMENT", "session_nonce": "a" * 32, "input_sha256": H64,
                        "pre_state": {**STATE, "changed": many}})
    assert err.value.code == "EVENT_TOO_LARGE"


def test_state_too_large():
    many = [[f"p{n:03d}", "M", H64] for n in range(201)]
    with pytest.raises(TaskctlError) as err:
        LG.check_payload("STEP_START", {"step": "IMPLEMENT", "session_nonce": "a" * 32, "input_sha256": H64,
                                        "pre_state": {**STATE, "changed": many}})
    assert err.value.code == "STATE_TOO_LARGE"


@pytest.mark.parametrize("payload", [
    {"sha256": H64, "bytes": 1, "extra": 1},                      # unknown key
    {"sha256": "XYZ", "bytes": 1},                                 # bad hex
    {"sha256": H64, "bytes": True},                                # bool is not a count
    {"sha256": H64, "bytes": -1},
])
def test_payload_keys_and_types(payload):
    with pytest.raises(TaskctlError) as err:
        LG.check_payload("PR_TEXT", payload)
    assert err.value.code == "INVALID"


@pytest.mark.parametrize("path", ["X:/synthetic/x.py", "/abs/x.py", "../x.py", "a/../b", "a\\b", "a//b",
                                  "https://host/x", "~/x"])
def test_paths_in_state_are_repository_relative_only(path):
    assert not LG.is_relpath(path)
    with pytest.raises(TaskctlError):
        LG.check_payload("DELEGATE", {"c1": H40, "wo_sha256": H64, "base": H40, "expires_utc": "2026-11-16T20:00:00Z",
                                      "session_nonce": "a" * 32, "delegation_sha256": H64,
                                      "state": {**STATE, "changed": [[path, "M", H64]]}})


@pytest.mark.parametrize("remote", [{"url": "https://x", "agent_reported": True}, {"pushed_head": H40},
                                    {"pr_number": 0, "agent_reported": True},
                                    {"merge_parents": [H40], "agent_reported": True}])
def test_remote_values_are_limited(remote):
    assert not LG.is_remote(remote)


def test_text_values_reject_urls_and_non_ascii():
    assert LG.is_text("plain words")
    assert not LG.is_text("see https://example.invalid")
    assert not LG.is_text("한글")


@needs_git
@pytest.mark.parametrize("final_created, code", [(True, "CREATED_CLEANUP_FAILED"), (False, "IO_ERROR")])
def test_create_new_failure_on_event(ledger, monkeypatch, final_created, code):
    repo, tc = ledger
    before = len(LG.read_events(repo.root, TASK))
    real = LG.atomic_create_new_bytes

    def broken(path, data):
        if path.parent.name == "events":
            if final_created:
                real(path, data)
            raise CreateNewError(OSError("injected"), final_created, path.with_suffix(".tmp") if final_created else None)
        return real(path, data)

    monkeypatch.setattr(LG, "atomic_create_new_bytes", broken)
    out = tc.start("IMPLEMENT")
    assert out["code"] == code
    after = len(LG.read_events(repo.root, TASK))
    assert after == before + (1 if final_created else 0)  # the observation is kept, nothing is rewritten
    if final_created:
        assert out["created"] == "event " + f"{after:06d}" and out["tmp_leftover_possible"] is True
    assert (repo.root / LG.LEDGER_ROOT / TASK / "LEASE").exists()  # the lease is not released
    monkeypatch.setattr(LG, "atomic_create_new_bytes", real)
    assert tc.start("IMPLEMENT")["code"] == "LEASE_PRESENT"
