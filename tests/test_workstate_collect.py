"""AUTO-02 AC6, AC7, AC10, AC11: what a snapshot compares, which states are refused, and that taking a
snapshot neither changes the compared state nor stores contents. All repositories are tmp repositories."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import subprocess
import types
from pathlib import Path

import pytest

from moneylab.workstate import collect, store
from moneylab.workstate.__main__ import main

TASK = "T-1"
RO_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=check, env=RO_ENV)


def init_repo(path: Path) -> Path:
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    for key, value in (("user.email", "t@example.invalid"), ("user.name", "T"), ("core.autocrlf", "false"),
                       ("commit.gpgsign", "false")):
        git(path, "config", key, value)
    (path / ".gitignore").write_bytes(b"data/processed/*\n")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = init_repo(tmp_path / "repo")
    (path / "a.txt").write_bytes(b"alpha\n")
    (path / "docs" / "tasks" / TASK).mkdir(parents=True)
    (path / "docs" / "tasks" / TASK / "WORK_ORDER.md").write_bytes(b"# WO\n")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "init")
    return path


def cli(capsys, repo: Path, *args: str) -> dict:
    code = main(list(args), root=repo)
    result = json.loads(capsys.readouterr().out)
    assert result["exit_code"] == code
    return result


def snap(capsys, repo: Path, *extra: str) -> dict:
    return cli(capsys, repo, "snapshot", "--task-id", TASK, *extra)


def verify(capsys, repo: Path, snapshot_id: str) -> dict:
    return cli(capsys, repo, "verify", "--task-id", TASK, "--snapshot-id", snapshot_id)


def make_symlink(target: Path, link: Path, case: str) -> None:
    try:
        os.symlink(target, link)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314 or exc.errno in (errno.EPERM, errno.ENOTSUP):
            pytest.skip(f"NOT_RUN_PLATFORM: {case}")
        raise


def make_dir_link(target: Path, link: Path, case: str) -> None:
    """A junction on Windows, a directory symlink elsewhere."""
    if os.name == "nt":
        import _winapi

        try:
            _winapi.CreateJunction(str(target), str(link))
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                pytest.skip(f"NOT_RUN_PLATFORM: {case}")
            raise
    else:
        make_symlink(target, link, case)


# ------------------------------------------------------------------------------------------------ AC6


def test_clean_snapshot_then_verify_is_a_match(repo, capsys):
    first = snap(capsys, repo)
    assert first["status"] == "STORED" and first["exit_code"] == 0
    result = verify(capsys, repo, first["snapshot_id"])
    assert result["status"] == "MATCH" and result["exit_code"] == 0 and result["differences"] == []
    assert result["state_sha256_stored"] == result["state_sha256_current"]


def _modify(repo):
    (repo / "a.txt").write_bytes(b"changed\n")


def _stage(repo):
    (repo / "a.txt").write_bytes(b"staged\n")
    git(repo, "add", "a.txt")


def _delete(repo):
    (repo / "a.txt").unlink()


def _rename(repo):
    git(repo, "mv", "a.txt", "b.txt")


def _untracked(repo):
    (repo / "c.txt").write_bytes(b"new\n")


def _commit(repo):
    (repo / "a.txt").write_bytes(b"next content\n")
    git(repo, "commit", "-q", "-am", "content change")


def _branch(repo):
    git(repo, "switch", "-q", "-c", "other")


def _detach(repo):
    git(repo, "switch", "-q", "--detach")


def _contract(repo):
    (repo / "docs" / "tasks" / TASK / "WORK_ORDER.md").write_bytes(b"# WO changed\n")


CHANGES = {
    "modify": (_modify, {"entries"}),
    "stage": (_stage, {"entries"}),
    "delete": (_delete, {"entries"}),
    "rename": (_rename, {"entries"}),
    "untracked": (_untracked, {"untracked"}),
    "commit-with-content": (_commit, {"head", "tree"}),
    "branch": (_branch, {"branch"}),
    "detached": (_detach, {"branch"}),
    "contract": (_contract, {"contract"}),
}


@pytest.mark.parametrize("name", sorted(CHANGES))
def test_each_change_is_a_mismatch_naming_its_field(repo, capsys, name):
    base = snap(capsys, repo)
    change, fields = CHANGES[name]
    change(repo)
    result = verify(capsys, repo, base["snapshot_id"])
    assert result["status"] == "MISMATCH" and result["exit_code"] == 1
    reported = {item["field"] for item in result["differences"]}
    assert fields <= reported
    if name == "rename":
        paths = {(item["stored"] or item["current"])["path"] for item in result["differences"]
                 if item["field"] == "entries"}
        assert paths == {"a.txt", "b.txt"}
    if name == "detached":
        assert result["differences"][0] == {"field": "branch", "stored": "main", "current": None}


def test_meta_and_reported_do_not_change_the_verdict(repo, capsys, monkeypatch):
    first = snap(capsys, repo)
    monkeypatch.setattr(store, "_now", lambda: "2001-01-01T00:00:00Z")
    second = snap(capsys, repo, "--reported-gate", "IMPLEMENTATION", "--reported-result", "PASS")
    assert second["status"] == "STORED" and second["snapshot_id"] != first["snapshot_id"]
    assert second["reported_status"] == "REPORTED_UNVERIFIED"
    for snapshot_id in (first["snapshot_id"], second["snapshot_id"]):
        assert verify(capsys, repo, snapshot_id)["status"] == "MATCH"


def test_a_b_a_gives_the_same_id_and_matches(repo, capsys):
    state_a = snap(capsys, repo)
    (repo / "a.txt").write_bytes(b"state b\n")
    state_b = snap(capsys, repo)
    (repo / "a.txt").write_bytes(b"alpha\n")
    again = snap(capsys, repo)
    assert state_b["snapshot_id"] != state_a["snapshot_id"]
    assert again["snapshot_id"] == state_a["snapshot_id"] and again["status"] == "ALREADY_STORED"
    assert verify(capsys, repo, state_a["snapshot_id"])["status"] == "MATCH"


# ------------------------------------------------------------------------------------------------ AC7


def _assert_refused(result: dict, repo: Path, code: str) -> None:
    assert result["status"] == code and result["exit_code"] == 2
    assert result["error"]["code"] == code
    assert not (repo / "data").exists()


def test_unborn_repository_is_unsupported(tmp_path, capsys):
    repo = init_repo(tmp_path / "unborn")
    _assert_refused(snap(capsys, repo), repo, "UNSUPPORTED_STATE")


def _branch_commit(repo: Path, branch: str, name: str, content: bytes) -> None:
    git(repo, "switch", "-q", "-c", branch)
    (repo / name).write_bytes(content)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", branch)
    git(repo, "switch", "-q", "main")


def test_unmerged_entries_are_unsupported(repo, capsys):
    _branch_commit(repo, "side", "a.txt", b"side\n")
    (repo / "a.txt").write_bytes(b"main side\n")
    git(repo, "commit", "-q", "-am", "main")
    git(repo, "merge", "-q", "side", check=False)
    assert b"u " in git(repo, "status", "--porcelain=v2").stdout
    _assert_refused(snap(capsys, repo), repo, "UNSUPPORTED_STATE")


def test_merge_in_progress_without_conflict_is_unsupported(repo, capsys):
    _branch_commit(repo, "side", "other.txt", b"other\n")
    git(repo, "merge", "-q", "--no-commit", "--no-ff", "side")
    result = snap(capsys, repo)
    _assert_refused(result, repo, "UNSUPPORTED_STATE")
    assert "MERGE_HEAD" in result["error"]["detail"]


@pytest.mark.parametrize("flag", ["--skip-worktree", "--assume-unchanged"])
def test_hidden_index_flags_are_unsupported(repo, capsys, flag):
    git(repo, "update-index", flag, "a.txt")
    _assert_refused(snap(capsys, repo), repo, "UNSUPPORTED_STATE")


def test_islink_on_an_untracked_path_is_unsupported(repo, capsys, monkeypatch):
    (repo / "c.txt").write_bytes(b"x\n")
    real = os.path.islink
    monkeypatch.setattr(os.path, "islink", lambda p: Path(p).name == "c.txt" or real(p))
    _assert_refused(snap(capsys, repo), repo, "UNSUPPORTED_STATE")


def test_junction_parent_of_a_changed_path_is_unsupported(repo, capsys, monkeypatch):
    _contract(repo)
    real = Path.is_junction
    monkeypatch.setattr(Path, "is_junction", lambda self: self.name == "docs" or real(self))
    _assert_refused(snap(capsys, repo), repo, "UNSUPPORTED_STATE")


def test_reparse_point_attribute_is_unsupported(repo, capsys, monkeypatch):
    _modify(repo)
    real = os.lstat

    def fake_lstat(path):
        st = real(path)
        if Path(path).name != "a.txt":
            return st
        return types.SimpleNamespace(st_mode=st.st_mode, st_size=st.st_size, st_mtime_ns=st.st_mtime_ns,
                                     st_file_attributes=collect.FILE_ATTRIBUTE_REPARSE_POINT)

    monkeypatch.setattr(collect, "_lstat", fake_lstat)
    _assert_refused(snap(capsys, repo), repo, "UNSUPPORTED_STATE")


def test_non_regular_work_file_is_unsupported(repo, capsys, monkeypatch):
    _modify(repo)
    monkeypatch.setattr(collect.stat, "S_ISREG", lambda mode: False)
    result = snap(capsys, repo)
    monkeypatch.undo()
    _assert_refused(result, repo, "UNSUPPORTED_STATE")
    assert "not a regular file" in result["error"]["detail"]


def test_real_untracked_symlink_is_unsupported(repo, capsys):
    make_symlink(repo / "a.txt", repo / "link.txt", "collect-untracked-symlink")
    _assert_refused(snap(capsys, repo), repo, "UNSUPPORTED_STATE")


def test_real_untracked_directory_link_is_unsupported(repo, capsys, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "f.txt").write_bytes(b"outside\n")
    make_dir_link(outside, repo / "jdir", "collect-untracked-directory-link")
    _assert_refused(snap(capsys, repo), repo, "UNSUPPORTED_STATE")


def test_file_changed_while_hashed_is_unstable(repo, capsys, monkeypatch):
    _modify(repo)
    done: list[bool] = []

    def change_once(path):
        if not done:
            done.append(True)
            path.write_bytes(b"changed again with another size\n")

    monkeypatch.setattr(collect, "_after_hash", change_once)
    _assert_refused(snap(capsys, repo), repo, "UNSTABLE_STATE")


def test_two_different_collections_are_unstable(monkeypatch):
    results = iter([{"head": "1"}, {"head": "2"}])
    monkeypatch.setattr(collect, "_collect_once", lambda root, task: next(results))
    with pytest.raises(collect.WorkstateError) as info:
        collect.collect_state(Path("."), TASK)
    assert info.value.code == "UNSTABLE_STATE"


def _limit_case(repo: Path, monkeypatch, name: str) -> str:
    """Prepare one limit case; return a fragment the error detail must contain."""
    if name == "entries":
        _modify(repo)
        monkeypatch.setattr(collect, "MAX_ENTRIES", 0)
        return "changed paths"
    if name == "untracked":
        _untracked(repo)
        monkeypatch.setattr(collect, "MAX_UNTRACKED", 0)
        return "untracked paths"
    if name == "contract":
        monkeypatch.setattr(collect, "MAX_CONTRACT", 0)
        return "contract files"
    if name == "path-length":
        (repo / "a-rather-long-untracked-name.txt").write_bytes(b"x\n")
        monkeypatch.setattr(collect, "MAX_PATH_BYTES", 10)
        return "longer than the limit"
    if name == "work-file":
        (repo / "a.txt").write_bytes(b"w" * 100)
        monkeypatch.setattr(collect, "OBJECT_LIMIT", 50)
        return "work file larger"
    if name == "blob":
        (repo / "a.txt").write_bytes(b"s" * 100)
        git(repo, "add", "a.txt")
        monkeypatch.setattr(collect, "OBJECT_LIMIT", 50)
        return "stdout exceeded"
    monkeypatch.setattr(collect, "TOTAL_LIMIT", 1)
    return "total limit"


@pytest.mark.parametrize("name", ["entries", "untracked", "contract", "path-length", "work-file", "blob", "total"])
def test_each_limit_is_an_explicit_error(repo, monkeypatch, name):
    fragment = _limit_case(repo, monkeypatch, name)
    with pytest.raises(collect.WorkstateError) as info:
        collect.collect_state(repo, TASK)
    assert info.value.code == "LIMIT_EXCEEDED"
    assert fragment in info.value.detail


# ----------------------------------------------------------------------------------------------- AC10


def test_snapshot_changes_neither_status_nor_index_nor_head(repo, capsys):
    _modify(repo)
    _untracked(repo)
    index = repo / ".git" / "index"

    def observe():
        return (git(repo, "status", "--porcelain=v2", "--ignored=no").stdout,
                hashlib.sha256(index.read_bytes()).hexdigest(), git(repo, "rev-parse", "HEAD").stdout)

    before = observe()
    assert snap(capsys, repo)["status"] == "STORED"
    assert observe() == before


# ----------------------------------------------------------------------------------------------- AC11


def test_record_holds_no_contents_environment_or_absolute_paths(repo, capsys, monkeypatch):
    monkeypatch.setenv("WORKSTATE_TEST_MARKER", "env-marker-91c7")
    (repo / "a.txt").write_bytes(b"content-marker-5d2e\n")
    (repo / "c.txt").write_bytes(b"untracked-marker-77aa\n")
    result = snap(capsys, repo)
    raw = (repo / store.record_rel(TASK, result["snapshot_id"])).read_bytes()
    for marker in (b"content-marker-5d2e", b"untracked-marker-77aa", b"env-marker-91c7"):
        assert marker not in raw
    for form in (str(repo), str(repo).replace("\\", "/"), json.dumps(str(repo))[1:-1]):
        assert form.encode("utf-8") not in raw
    assert set(json.loads(raw)) == store.TOP_KEYS
