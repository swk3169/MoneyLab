"""taskctl lease: create-new races, owner-only release, interruptions and lease-clear (GOV-AUTOMATION-03 D5)."""

from __future__ import annotations

import errno
import os
import stat
import threading
from pathlib import Path

import pytest
from test_taskctl_cli import (
    NOW,
    PR_BODY,
    TASK,
    Taskctl,
    make_repo,
    needs_git,
    record_publish,
    sha,
    taskctl_templates,  # noqa: F401  (autouse: checks the shared templates after each test)
    to_local_done,
    to_ready,
    to_setup_done,
)

from moneylab.storage.atomic import CreateNewError
from moneylab.taskctl import lease as LS
from moneylab.taskctl import ledger as LG
from moneylab.taskctl.ledger import TaskctlError
from moneylab.workstate.collect import is_link_like

UTC_TEXT = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_concurrent_acquire_has_exactly_one_winner(tmp_path):
    results: list[str] = []
    barrier = threading.Barrier(8)

    def worker():
        barrier.wait()
        try:
            results.append(LS.acquire(tmp_path, "STEP_START", UTC_TEXT))
        except TaskctlError as exc:
            results.append(exc.code)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    winners = [r for r in results if r != "LEASE_PRESENT"]
    assert len(winners) == 1 and results.count("LEASE_PRESENT") == 7
    assert LS.read_lease(tmp_path)["lease_id"] == winners[0]


def test_only_the_owner_releases(tmp_path):
    lease_id = LS.acquire(tmp_path, "STEP_START", UTC_TEXT)
    with pytest.raises(TaskctlError) as err:
        LS.release(tmp_path, "f" * 32)
    assert err.value.code == "LEASE_NOT_OWNER"
    LS.release(tmp_path, lease_id)
    assert LS.read_lease(tmp_path) is None


@pytest.mark.parametrize("final_created, code", [(True, "CREATED_CLEANUP_FAILED"), (False, "IO_ERROR")])
def test_create_new_failure_on_lease(tmp_path, monkeypatch, final_created, code):
    real = LG.atomic_create_new_bytes

    def broken(path, data):
        if final_created:
            real(path, data)
        raise CreateNewError(OSError("injected"), final_created, None)

    monkeypatch.setattr(LG, "atomic_create_new_bytes", broken)
    with pytest.raises(TaskctlError) as err:
        LS.acquire(tmp_path, "STEP_START", UTC_TEXT)
    assert err.value.code == code
    assert (tmp_path / "LEASE").exists() is final_created  # a created lease is kept, never released here


@pytest.fixture
def env(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    to_setup_done(repo, base, c1, tc)
    return repo, tc, repo.root / LG.LEDGER_ROOT / TASK


@needs_git
def test_interruption_after_lease_before_event(env):
    repo, tc, directory = env
    before = len(LG.read_events(repo.root, TASK))
    left = LS.acquire(directory, "STEP_START", UTC_TEXT)  # a command that stopped after step 1 of D5
    out = tc.start("IMPLEMENT")
    assert out["code"] == "LEASE_PRESENT"
    assert len(LG.read_events(repo.root, TASK)) == before
    status = tc("status")
    assert status["code"] == "OK" and "LEASE_PRESENT" in status["blockers"] and status["lease_id"] == left
    assert tc.phase("TERMINAL", "--terminal-status", "STOPPED", "--code", "X")["code"] == "LEASE_PRESENT"
    assert tc("lease-clear", "--lease-id", "f" * 32)["code"] == "LEASE_MISMATCH"
    assert tc("lease-clear", "--lease-id", left)["code"] == "OK"
    events = LG.read_events(repo.root, TASK)
    assert events[-1][0]["kind"] == "LEASE_CLEARED" and len(events) == before + 1
    assert tc.start("IMPLEMENT")["code"] == "OK"


@needs_git
def test_interruption_after_event_before_release(env, monkeypatch):
    repo, tc, directory = env
    before = len(LG.read_events(repo.root, TASK))

    def stop(directory, lease_id):
        raise KeyboardInterrupt

    original = LS.release
    monkeypatch.setattr(LS, "release", stop)
    with pytest.raises(KeyboardInterrupt):
        tc.start("IMPLEMENT")
    monkeypatch.setattr(LS, "release", original)
    assert len(LG.read_events(repo.root, TASK)) == before + 1  # the event was written
    assert tc.end("IMPLEMENT")["code"] == "LEASE_PRESENT"


@needs_git
def test_lease_clear_interrupted_between_record_and_delete(env, monkeypatch):
    repo, tc, directory = env
    left = LS.acquire(directory, "STEP_START", UTC_TEXT)

    def stop(directory, lease_id):
        raise KeyboardInterrupt

    original = LS.delete_cleared
    monkeypatch.setattr(LS, "delete_cleared", stop)
    with pytest.raises(KeyboardInterrupt):
        tc("lease-clear", "--lease-id", left)
    monkeypatch.setattr(LS, "delete_cleared", original)
    assert LG.read_events(repo.root, TASK)[-1][0]["kind"] == "LEASE_CLEARED"
    assert tc.start("IMPLEMENT")["code"] == "LEASE_PRESENT"  # a second CLEAR_LEASE is needed
    assert tc("lease-clear", "--lease-id", left)["code"] == "OK"
    assert tc.start("IMPLEMENT")["code"] == "OK"


@needs_git
def test_lease_clear_without_lease(env):
    _, tc, _ = env
    assert tc("lease-clear", "--lease-id", "a" * 32)["code"] == "LEASE_ABSENT"


# ------------------------------------------------------------------------------------------- ERRATA-001 P1-P8
# D4 for LEASE, REVOKED and pr_text.md. Links and their targets are made only inside the tmp_path repository
# (the ledger directory of the task). A link that cannot be made is NOT_RUN_PLATFORM, never a pass.


def make_symlink(target: Path, link: Path, case: str) -> None:
    try:
        os.symlink(target, link)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314 or exc.errno in (errno.EPERM, errno.ENOTSUP):
            pytest.skip(f"NOT_RUN_PLATFORM: {case}")
        raise


def make_junction(target: Path, link: Path, case: str) -> None:
    if os.name != "nt":
        pytest.skip(f"NOT_RUN_PLATFORM: {case} (junctions are Windows only)")
    import _winapi

    try:
        _winapi.CreateJunction(str(target), str(link))
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip(f"NOT_RUN_PLATFORM: {case}")
        raise


def events_of(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted((directory / "events").iterdir())}


def file_target(directory: Path) -> Path:
    target = directory / "link-target.txt"
    target.write_bytes(b"target bytes\n")
    return target


def assert_refused(tc: Taskctl, commands: list[tuple], directory: Path, target: Path | None) -> None:
    """Every command is PATH_INVALID; the link target, the events and the absence of a new LEASE are kept."""
    before = events_of(directory)
    kept = target.read_bytes() if target is not None and target.is_file() else None
    had_lease = os.path.lexists(directory / "LEASE")
    for args, stdin in commands:
        out = tc(*args, stdin=stdin)
        assert out["code"] == "PATH_INVALID", (args, out)
    assert events_of(directory) == before
    assert os.path.lexists(directory / "LEASE") is had_lease
    if kept is not None:
        assert target.read_bytes() == kept


STATUS_AND_START = [(("status",), b""), (("step", "start", "--step", "IMPLEMENT", "--session-nonce", "a" * 32,
                                          "--input-sha256", "c" * 64), b"")]
REVOKE = [(("revoke",), b"")]
PR_TEXT = [(("pr-text", "--sha256", sha(PR_BODY)), PR_BODY)]


@needs_git
def test_p1_lease_symlink_is_refused(env):
    _, tc, directory = env
    target = file_target(directory)
    make_symlink(target, directory / "LEASE", "taskctl-lease-symlink")
    assert_refused(tc, STATUS_AND_START, directory, target)


@needs_git
def test_p2_broken_lease_symlink_is_not_an_absent_lease(env):
    _, tc, directory = env
    make_symlink(directory / "missing-target", directory / "LEASE", "taskctl-lease-broken-symlink")
    assert_refused(tc, STATUS_AND_START, directory, None)
    assert os.path.lexists(directory / "LEASE") and not (directory / "missing-target").exists()


@needs_git
def test_p3_revoked_symlink_is_refused(env):
    _, tc, directory = env
    target = file_target(directory)
    make_symlink(target, directory / "REVOKED", "taskctl-revoked-symlink")
    assert_refused(tc, STATUS_AND_START + REVOKE, directory, target)


@needs_git
def test_p4_broken_revoked_symlink_is_not_an_unrevoked_task(env):
    _, tc, directory = env
    make_symlink(directory / "missing-target", directory / "REVOKED", "taskctl-revoked-broken-symlink")
    assert_refused(tc, STATUS_AND_START + REVOKE, directory, None)


@pytest.fixture
def local_done(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    to_local_done(repo, base, c1, tc)
    return repo, tc, repo.root / LG.LEDGER_ROOT / TASK


def replace_pr_text(directory: Path, make_link) -> None:
    """Test setup only: the regular pr_text.md of this tmp_path ledger is replaced by a link."""
    (directory / "pr_text.md").unlink()
    make_link(directory / "pr_text.md")


def publish_commands(c1: str, i: str, tree: str, base: str) -> list[tuple]:
    return [(("record-message", "--kind", "PUBLISH", "--wo-c1", c1, "--head", i, "--tree", tree, "--base", base,
              "--pr-text-sha256", sha(PR_BODY), "--expires-utc", "2026-11-16T20:00:00Z"), b""),
            (("publish-draft",), b"")]


@needs_git
def test_p5_pr_text_symlink_is_refused_for_pr_text(local_done):
    _, tc, directory = local_done
    target = file_target(directory)
    make_symlink(target, directory / "pr_text.md", "taskctl-pr-text-symlink")
    assert_refused(tc, PR_TEXT, directory, target)


@needs_git
def test_p5_pr_text_symlink_is_refused_for_publish_and_draft(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    i, tree = to_ready(repo, base, c1, tc)
    directory = repo.root / LG.LEDGER_ROOT / TASK
    target = file_target(directory)
    replace_pr_text(directory, lambda link: make_symlink(target, link, "taskctl-pr-text-symlink-publish"))
    assert_refused(tc, publish_commands(c1, i, tree, base), directory, target)


@needs_git
def test_p6_broken_pr_text_symlink_is_refused_for_pr_text(local_done):
    _, tc, directory = local_done
    make_symlink(directory / "missing-target", directory / "pr_text.md", "taskctl-pr-text-broken-symlink")
    assert_refused(tc, PR_TEXT, directory, None)


@needs_git
def test_p6_broken_pr_text_symlink_is_refused_for_publish_and_draft(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    i, tree = to_ready(repo, base, c1, tc)
    directory = repo.root / LG.LEDGER_ROOT / TASK
    replace_pr_text(directory, lambda link: make_symlink(directory / "missing-target", link,
                                                         "taskctl-pr-text-broken-symlink-publish"))
    assert_refused(tc, publish_commands(c1, i, tree, base), directory, None)


def dir_target(directory: Path) -> Path:
    target = directory / "link-target-dir"
    target.mkdir()
    (target / "inside.txt").write_bytes(b"inside\n")
    return target


@needs_git
@pytest.mark.parametrize("name, commands", [("LEASE", STATUS_AND_START), ("REVOKED", STATUS_AND_START + REVOKE)])
@pytest.mark.parametrize("broken", [False, True])
def test_p7_junction_for_lease_and_revoked_is_refused(env, name, commands, broken):
    _, tc, directory = env
    target = dir_target(directory)
    make_junction(target, directory / name, f"taskctl-{name.lower()}-junction")
    if broken:  # a junction whose target directory is gone (test setup inside tmp_path only)
        (target / "inside.txt").unlink()
        target.rmdir()
    assert_refused(tc, commands, directory, None if broken else target / "inside.txt")
    assert os.path.lexists(directory / name)


@needs_git
@pytest.mark.parametrize("broken", [False, True])
def test_p7_junction_for_pr_text_is_refused(local_done, broken):
    _, tc, directory = local_done
    target = dir_target(directory)
    make_junction(target, directory / "pr_text.md", "taskctl-pr-text-junction")
    if broken:
        (target / "inside.txt").unlink()
        target.rmdir()
    assert_refused(tc, PR_TEXT, directory, None if broken else target / "inside.txt")


@needs_git
def test_p7_junction_for_pr_text_is_refused_for_publish_and_draft(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    i, tree = to_ready(repo, base, c1, tc)
    directory = repo.root / LG.LEDGER_ROOT / TASK
    target = dir_target(directory)
    replace_pr_text(directory, lambda link: make_junction(target, link, "taskctl-pr-text-junction-publish"))
    assert_refused(tc, publish_commands(c1, i, tree, base), directory, target / "inside.txt")


@needs_git
def test_p8_regular_lease_and_revoked_keep_their_behaviour(env):
    repo, tc, directory = env
    left = LS.acquire(directory, "STEP_START", UTC_TEXT)
    assert tc.start("IMPLEMENT")["code"] == "LEASE_PRESENT"
    assert tc("status")["lease_id"] == left
    assert tc("lease-clear", "--lease-id", left)["code"] == "OK"
    out = tc("revoke")
    assert out["code"] == "OK" and out["newly_revoked"] is True
    assert tc("revoke")["newly_revoked"] is False
    assert "REVOKED" in tc("status")["blockers"]


@needs_git
def test_p8_regular_pr_text_and_publish_keep_their_behaviour(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    i = to_local_done(repo, base, c1, tc)
    assert tc("pr-text", "--sha256", sha(PR_BODY), stdin=PR_BODY)["code"] == "OK"  # pr-text OK on a regular file
    assert tc.phase("READY_TO_PUBLISH")["code"] == "OK"
    tree = repo.git("rev-parse", f"{i}^{{tree}}")
    directory = repo.root / LG.LEDGER_ROOT / TASK
    assert (directory / "pr_text.md").read_bytes() == PR_BODY
    assert tc("publish-draft")["code"] == "OK"
    assert record_publish(tc, c1, i, tree, base)["code"] == "OK"


@needs_git
def test_p8_existing_regular_pr_text_is_never_replaced(local_done):
    _, tc, directory = local_done
    (directory / "pr_text.md").write_bytes(b"left before\n")
    before = events_of(directory)
    assert tc("pr-text", "--sha256", sha(PR_BODY), stdin=PR_BODY)["code"] == "PR_TEXT_EXISTS"
    assert (directory / "pr_text.md").read_bytes() == b"left before\n" and events_of(directory) == before
    assert not (directory / "LEASE").exists()


# ------------------------------------------------------------------------------------------- PILOT-DELEGATION-01 IL1-IL6
# init on a ledger path whose existing component is a link, a broken link or a junction (D4 of GOV-AUTOMATION-03).
# Every test uses make_repo, Taskctl and TASK ("PILOT-X") from test_taskctl_cli: make_repo commits the temporary
# Work Order docs/tasks/PILOT-X/WORK_ORDER.md and Taskctl.init passes --task-id PILOT-X, so the path init checks is
# LEDGER_ROOT/TASK. Links and their targets are made only inside the tmp_path repository.


def make_dir_symlink(target: Path, link: Path, case: str) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314 or exc.errno in (errno.EPERM, errno.ENOTSUP):
            pytest.skip(f"NOT_RUN_PLATFORM: {case}")
        raise


def init_env(tmp_path, monkeypatch):
    repo, base, c1 = make_repo(tmp_path)
    tc = Taskctl(repo, monkeypatch)
    ledger_root = repo.root / LG.LEDGER_ROOT  # data/processed/taskctl
    return repo, base, c1, tc, ledger_root, ledger_root / TASK


def dir_with_file(path: Path) -> Path:
    path.mkdir()
    (path / "kept.txt").write_bytes(b"target bytes\n")
    return path


def files_of(path: Path) -> dict[str, bytes]:
    if not path.exists():
        return {}
    return {p.relative_to(path).as_posix(): p.read_bytes() for p in sorted(path.rglob("*")) if p.is_file()}


def assert_init_refused(repo, base, c1, tc, link: Path, target: Path) -> None:
    """init is PATH_INVALID; the link, its target's files, HEAD and git status are unchanged; no ledger is made."""
    before = (os.path.lexists(link), target.exists(), files_of(target), repo.git("rev-parse", "HEAD"),
              repo.git("status", "--porcelain=v2", "--untracked-files=all", "--ignored=matching"))
    out = tc.init(base, c1)
    assert out["code"] == "PATH_INVALID", out
    after = (os.path.lexists(link), target.exists(), files_of(target), repo.git("rev-parse", "HEAD"),
             repo.git("status", "--porcelain=v2", "--untracked-files=all", "--ignored=matching"))
    assert after == before
    assert before[0] is True
    assert not any(p.name in ("events", "LEASE") for p in target.rglob("*")) if target.exists() else True


@needs_git
def test_init_il1_ledger_root_symlink_is_refused(tmp_path, monkeypatch):
    repo, base, c1, tc, ledger_root, _ = init_env(tmp_path, monkeypatch)
    target = dir_with_file(repo.root / "data/processed/il1-target")
    make_dir_symlink(target, ledger_root, "taskctl-init-ledger-root-symlink")
    assert_init_refused(repo, base, c1, tc, ledger_root, target)


@needs_git
def test_init_il2_broken_ledger_root_symlink_is_refused(tmp_path, monkeypatch):
    repo, base, c1, tc, ledger_root, _ = init_env(tmp_path, monkeypatch)
    target = repo.root / "data/processed/il2-missing"
    make_dir_symlink(target, ledger_root, "taskctl-init-ledger-root-broken-symlink")
    assert_init_refused(repo, base, c1, tc, ledger_root, target)
    assert not target.exists()


@needs_git
def test_init_il3_task_dir_symlink_is_refused(tmp_path, monkeypatch):
    repo, base, c1, tc, ledger_root, task_dir = init_env(tmp_path, monkeypatch)
    ledger_root.mkdir()
    target = dir_with_file(repo.root / "data/processed/il3-target")
    make_dir_symlink(target, task_dir, "taskctl-init-task-dir-symlink")
    assert_init_refused(repo, base, c1, tc, task_dir, target)


@needs_git
@pytest.mark.parametrize("broken", [False, True])
def test_init_il4_ledger_root_junction_is_refused(tmp_path, monkeypatch, broken):
    repo, base, c1, tc, ledger_root, _ = init_env(tmp_path, monkeypatch)
    target = dir_with_file(repo.root / "data/processed/il4-target")
    make_junction(target, ledger_root, "taskctl-init-ledger-root-junction")
    if broken:  # a junction whose target directory is gone (test setup inside tmp_path only)
        (target / "kept.txt").unlink()
        target.rmdir()
    assert_init_refused(repo, base, c1, tc, ledger_root, target)


@needs_git
def test_init_il5_task_dir_junction_is_refused(tmp_path, monkeypatch):
    repo, base, c1, tc, ledger_root, task_dir = init_env(tmp_path, monkeypatch)
    ledger_root.mkdir()
    target = dir_with_file(repo.root / "data/processed/il5-target")
    make_junction(target, task_dir, "taskctl-init-task-dir-junction")
    assert_init_refused(repo, base, c1, tc, task_dir, target)


@needs_git
def test_init_il6_regular_path_creates_plain_directories(tmp_path, monkeypatch):
    repo, base, c1, tc, ledger_root, task_dir = init_env(tmp_path, monkeypatch)
    assert not os.path.lexists(ledger_root)
    assert tc.init(base, c1)["code"] == "OK"
    for path in (ledger_root, task_dir, task_dir / "events"):
        st = os.lstat(path)
        assert not is_link_like(path, st) and stat.S_ISDIR(st.st_mode), path.name
    event = task_dir / "events" / "000001.json"
    st = os.lstat(event)
    assert not is_link_like(event, st) and stat.S_ISREG(st.st_mode)
