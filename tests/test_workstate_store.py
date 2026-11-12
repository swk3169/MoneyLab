"""AUTO-02 AC8, AC9: storing never replaces a file, directories are created only by snapshot, and verify
reads exactly one named record without fallback, deletion or directory creation. tmp repositories only."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from moneylab.storage import atomic
from moneylab.workstate import collect, store
from moneylab.workstate.__main__ import main

TASK = "T-1"
RO_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True, env=RO_ENV)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    for key, value in (("user.email", "t@example.invalid"), ("user.name", "T"), ("core.autocrlf", "false"),
                       ("commit.gpgsign", "false")):
        git(path, "config", key, value)
    (path / ".gitignore").write_bytes(b"data/processed/*\n")
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


def snap(capsys, repo: Path) -> dict:
    return cli(capsys, repo, "snapshot", "--task-id", TASK)


def verify(capsys, repo: Path, snapshot_id: str, task: str = TASK) -> dict:
    return cli(capsys, repo, "verify", "--task-id", task, "--snapshot-id", snapshot_id)


def record_file(repo: Path, snapshot_id: str, task: str = TASK) -> Path:
    return repo / store.record_rel(task, snapshot_id)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_symlink(target: Path, link: Path, case: str) -> None:
    try:
        os.symlink(target, link)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314 or exc.errno in (errno.EPERM, errno.ENOTSUP):
            pytest.skip(f"NOT_RUN_PLATFORM: {case}")
        raise


def make_dir_link(target: Path, link: Path, case: str) -> None:
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


# ------------------------------------------------------------------------------------------- AC8 store


def test_missing_directories_are_created_top_down(repo, capsys):
    assert not (repo / "data").exists()
    result = snap(capsys, repo)
    assert result["status"] == "STORED" and result["exit_code"] == 0 and result["warnings"] == []
    assert result["final_file_created"] is True
    raw = record_file(repo, result["snapshot_id"]).read_bytes()
    assert result["file_sha256"] == sha(raw)


def test_store_path_that_git_does_not_ignore_is_refused(repo, capsys):
    (repo / ".gitignore").write_bytes(b"")
    result = snap(capsys, repo)
    assert result["status"] == "STORE_PATH_INVALID" and result["exit_code"] == 2
    assert not (repo / "data").exists()


def test_concurrent_mkdir_of_a_plain_directory_continues(repo, capsys, monkeypatch):
    def racing_mkdir(path):
        os.mkdir(path)
        raise FileExistsError(errno.EEXIST, "made by another run")

    monkeypatch.setattr(store, "_mkdir", racing_mkdir)
    assert snap(capsys, repo)["status"] == "STORED"


def test_existing_non_directory_at_a_store_component_is_refused(repo, capsys, monkeypatch):
    def racing_file(path):
        if Path(path).name == "workstate":
            Path(path).write_bytes(b"")
            raise FileExistsError(errno.EEXIST, "a file appeared")
        os.mkdir(path)

    monkeypatch.setattr(store, "_mkdir", racing_file)
    result = snap(capsys, repo)
    assert result["status"] == "STORE_PATH_INVALID"
    assert result["warnings"] == ["DIR_LEFT:data", "DIR_LEFT:data/processed"]
    assert (repo / "data" / "processed").is_dir()


def test_link_like_store_directory_is_refused(repo, capsys, monkeypatch):
    (repo / "data" / "processed" / "workstate").mkdir(parents=True)
    real = os.path.islink
    monkeypatch.setattr(os.path, "islink", lambda p: Path(p).name == "workstate" or real(p))
    result = snap(capsys, repo)
    assert result["status"] == "STORE_PATH_INVALID"
    assert not (repo / "data" / "processed" / "workstate" / TASK).exists()


def test_real_junction_as_store_directory_is_refused(repo, capsys, tmp_path):
    (repo / "data" / "processed").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    make_dir_link(outside, repo / "data" / "processed" / "workstate", "store-directory-link")
    result = snap(capsys, repo)
    assert result["status"] == "STORE_PATH_INVALID"
    assert list(outside.iterdir()) == []


def test_failure_after_creating_directories_leaves_and_reports_them(repo, capsys, monkeypatch):
    def failing_create(path, data):
        raise atomic.CreateNewError(OSError(errno.EIO, "injected"), False, None)

    monkeypatch.setattr(atomic, "atomic_create_new_bytes", failing_create)
    result = snap(capsys, repo)
    assert result["status"] == "STORE_FAILED" and result["final_file_created"] is False
    assert result["warnings"] == ["DIR_LEFT:data", "DIR_LEFT:data/processed", "DIR_LEFT:data/processed/workstate",
                                  f"DIR_LEFT:data/processed/workstate/{TASK}"]
    assert (repo / "data" / "processed" / "workstate" / TASK).is_dir()


def test_same_id_again_keeps_the_existing_file_and_meta(repo, capsys, monkeypatch):
    first = snap(capsys, repo)
    path = record_file(repo, first["snapshot_id"])
    raw = path.read_bytes()
    monkeypatch.setattr(store, "_now", lambda: "2001-01-01T00:00:00Z")
    again = snap(capsys, repo)
    assert again["status"] == "ALREADY_STORED" and again["exit_code"] == 0
    assert again["final_file_created"] is False
    assert path.read_bytes() == raw
    assert again["file_sha256"] == first["file_sha256"] == sha(raw)
    assert again["state_sha256_stored"] == first["state_sha256_current"]


@pytest.mark.parametrize("damage, code", [(lambda raw: raw[:-1] + b" \n", "SNAPSHOT_CORRUPT"),
                                          (lambda raw: raw.replace(b"snapshot/1", b"snapshot/2"),
                                           "SNAPSHOT_INCOMPATIBLE")])
def test_invalid_existing_file_with_the_same_id_is_kept(repo, capsys, damage, code):
    first = snap(capsys, repo)
    path = record_file(repo, first["snapshot_id"])
    damaged = damage(path.read_bytes())
    path.write_bytes(damaged)
    again = snap(capsys, repo)
    assert again["status"] == code and again["exit_code"] == 2
    assert again["file_sha256"] == sha(damaged)
    assert path.read_bytes() == damaged


def test_valid_existing_record_with_a_different_identity_is_corrupt_and_kept(repo, capsys, monkeypatch):
    first = snap(capsys, repo)
    path = record_file(repo, first["snapshot_id"])
    raw = path.read_bytes()
    stored = json.loads(raw)
    other_state = {**stored["state"], "branch": "elsewhere"}
    impostor = {**stored, "state": other_state, "state_sha256": store.state_sha256(other_state)}
    monkeypatch.setattr(store, "load_record", lambda root, task_id, snapshot_id: (impostor, sha(raw)))
    again = snap(capsys, repo)
    assert again["status"] == "SNAPSHOT_CORRUPT" and again["exit_code"] == 2
    assert again["error"]["detail"] == "an existing record with this id differs"
    assert again["final_file_created"] is False
    assert again["file_sha256"] == sha(raw)
    assert path.read_bytes() == raw


def test_odd_realpath_of_a_not_yet_created_path_does_not_refuse_the_store(repo, capsys, monkeypatch):
    """Injects the condition seen in a concurrent run: realpath of a path that does not exist yet answered
    with a location outside the root. The boundary of such a path is checked on the string alone."""
    real = os.path.realpath

    def odd_for_missing(path, *args, **kwargs):
        if not os.path.lexists(path):
            return real(repo.parent / "elsewhere" / Path(path).name, *args, **kwargs)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os.path, "realpath", odd_for_missing)
    result = snap(capsys, repo)
    monkeypatch.undo()
    assert result["status"] == "STORED" and result["exit_code"] == 0
    assert record_file(repo, result["snapshot_id"]).is_file()


def test_existing_store_directory_resolving_outside_the_root_is_refused(repo, capsys, monkeypatch):
    real = os.path.realpath

    def outside_for_task_dir(path, *args, **kwargs):
        if Path(path).name == TASK and os.path.lexists(path):
            return real(repo.parent / "elsewhere" / TASK, *args, **kwargs)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os.path, "realpath", outside_for_task_dir)
    result = snap(capsys, repo)
    monkeypatch.undo()
    assert result["status"] == "STORE_PATH_INVALID" and result["exit_code"] == 2
    assert result["warnings"] == ["DIR_LEFT:data", "DIR_LEFT:data/processed", "DIR_LEFT:data/processed/workstate",
                                  f"DIR_LEFT:data/processed/workstate/{TASK}"]
    assert list((repo / "data" / "processed" / "workstate" / TASK).iterdir()) == []


def test_two_threads_storing_the_same_id_create_one_file(repo, monkeypatch):
    state = collect.collect_state(repo, TASK)
    records = [store.build_record(TASK, state, None)]
    monkeypatch.setattr(store, "_now", lambda: "2001-01-01T00:00:00Z")
    records.append(store.build_record(TASK, state, None))
    barrier = threading.Barrier(2)
    outcomes: list[dict] = []

    def worker(record):
        barrier.wait()
        outcomes.append(store.save_record(repo, record))

    threads = [threading.Thread(target=worker, args=(record,)) for record in records]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(o["status"] for o in outcomes) == ["ALREADY_STORED", "STORED"]
    assert outcomes[0]["file_sha256"] == outcomes[1]["file_sha256"]
    assert len(list(record_file(repo, records[0]["snapshot_id"]).parent.glob("*.json"))) == 1


def test_two_processes_storing_the_same_id_create_one_file(repo):
    script = ("import sys\nfrom pathlib import Path\nfrom moneylab.workstate.__main__ import main\n"
              "sys.exit(main(['snapshot', '--task-id', 'T-1'], root=Path(sys.argv[1])))\n")
    procs = [subprocess.Popen([sys.executable, "-B", "-c", script, str(repo)], stdout=subprocess.PIPE)
             for _ in range(2)]
    results = [json.loads(proc.communicate(timeout=120)[0]) for proc in procs]
    assert sorted(r["status"] for r in results) == ["ALREADY_STORED", "STORED"]
    assert results[0]["file_sha256"] == results[1]["file_sha256"]
    assert len(list((repo / "data" / "processed" / "workstate" / TASK).glob("*.json"))) == 1


def test_temp_left_after_link_is_a_stored_warning(repo, capsys, monkeypatch):
    real = os.unlink

    def unlink(path, *args, **kwargs):
        if str(path).endswith(atomic.TMP_SUFFIX):
            raise PermissionError(errno.EACCES, "injected")
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", unlink)
    result = snap(capsys, repo)
    monkeypatch.undo()
    assert result["status"] == "STORED" and result["exit_code"] == 1 and result["final_file_created"] is True
    assert len(result["warnings"]) == 1 and result["warnings"][0].startswith("TMP_LEFTOVER:")
    assert verify(capsys, repo, result["snapshot_id"])["status"] == "MATCH"


def test_link_failure_and_temp_left_is_store_failed(repo, capsys, monkeypatch):
    def link_fails(src, dst):
        raise PermissionError(errno.EPERM, "injected")

    def unlink_fails(path, *args, **kwargs):
        raise PermissionError(errno.EACCES, "injected")

    monkeypatch.setattr(os, "link", link_fails)
    monkeypatch.setattr(os, "unlink", unlink_fails)
    result = snap(capsys, repo)
    monkeypatch.undo()
    assert result["status"] == "STORE_FAILED" and result["final_file_created"] is False
    assert any(w.startswith("TMP_LEFTOVER:") for w in result["warnings"])
    assert list((repo / "data" / "processed" / "workstate" / TASK).glob("*.json")) == []


def test_record_over_the_limit_is_not_stored(repo, capsys, monkeypatch):
    monkeypatch.setattr(store, "FILE_LIMIT", 100)
    result = snap(capsys, repo)
    assert result["status"] == "LIMIT_EXCEEDED" and result["final_file_created"] is None
    assert not (repo / "data").exists()


# ------------------------------------------------------------------------------------------ AC9 verify


ZERO = "0" * 64


def test_missing_record_is_not_found_and_creates_nothing(repo, capsys):
    result = verify(capsys, repo, ZERO)
    assert result["status"] == "SNAPSHOT_NOT_FOUND" and result["exit_code"] == 2
    assert result["file_sha256"] is None
    assert not (repo / "data").exists()


def test_unreadable_record(repo, capsys, monkeypatch):
    first = snap(capsys, repo)

    def unreadable(path):
        raise PermissionError(errno.EACCES, "injected")

    monkeypatch.setattr(store, "_read_bytes", unreadable)
    result = verify(capsys, repo, first["snapshot_id"])
    assert result["status"] == "SNAPSHOT_UNREADABLE" and result["file_sha256"] is None


def test_directory_at_the_record_path_is_corrupt(repo, capsys):
    record_file(repo, ZERO).mkdir(parents=True)
    result = verify(capsys, repo, ZERO)
    assert result["status"] == "SNAPSHOT_CORRUPT" and result["file_sha256"] is None
    assert record_file(repo, ZERO).is_dir()


def test_oversized_record_is_corrupt(repo, capsys, monkeypatch):
    first = snap(capsys, repo)
    monkeypatch.setattr(store, "FILE_LIMIT", 100)
    result = verify(capsys, repo, first["snapshot_id"])
    assert result["status"] == "SNAPSHOT_CORRUPT" and result["file_sha256"] is None


def _flip_head(raw: bytes) -> bytes:
    marker = b'"head":"'
    at = raw.index(marker) + len(marker)
    return raw[:at] + (b"1" if raw[at:at + 1] != b"1" else b"2") + raw[at + 1:]


DAMAGES = {
    "byte-changed": _flip_head,
    "not-canonical": lambda raw: raw[:-1] + b" \n",
    "duplicate-key": lambda raw: raw.replace(b'{"meta":', b'{"meta":null,"meta":', 1),
}


@pytest.mark.parametrize("name", sorted(DAMAGES))
def test_damaged_record_is_corrupt_and_kept(repo, capsys, name):
    first = snap(capsys, repo)
    path = record_file(repo, first["snapshot_id"])
    damaged = DAMAGES[name](path.read_bytes())
    path.write_bytes(damaged)
    result = verify(capsys, repo, first["snapshot_id"])
    assert result["status"] == "SNAPSHOT_CORRUPT" and result["exit_code"] == 2
    assert result["file_sha256"] == sha(damaged)
    assert path.read_bytes() == damaged


def test_record_under_another_name_is_corrupt(repo, capsys):
    first = snap(capsys, repo)
    raw = record_file(repo, first["snapshot_id"]).read_bytes()
    record_file(repo, "f" * 64).write_bytes(raw)
    result = verify(capsys, repo, "f" * 64)
    assert result["status"] == "SNAPSHOT_CORRUPT" and result["file_sha256"] == sha(raw)


def test_record_under_another_task_is_corrupt(repo, capsys):
    first = snap(capsys, repo)
    raw = record_file(repo, first["snapshot_id"]).read_bytes()
    other = record_file(repo, first["snapshot_id"], "T-2")
    other.parent.mkdir()
    other.write_bytes(raw)
    result = verify(capsys, repo, first["snapshot_id"], "T-2")
    assert result["status"] == "SNAPSHOT_CORRUPT" and "task_id" in result["error"]["detail"]


def test_unknown_schema_is_incompatible(repo, capsys):
    first = snap(capsys, repo)
    path = record_file(repo, first["snapshot_id"])
    damaged = path.read_bytes().replace(b"snapshot/1", b"snapshot/2")
    path.write_bytes(damaged)
    result = verify(capsys, repo, first["snapshot_id"])
    assert result["status"] == "SNAPSHOT_INCOMPATIBLE" and result["file_sha256"] == sha(damaged)
    assert path.read_bytes() == damaged


def test_real_symlinked_record_is_refused(repo, capsys):
    first = snap(capsys, repo)
    make_symlink(record_file(repo, first["snapshot_id"]), record_file(repo, "e" * 64), "verify-record-symlink")
    result = verify(capsys, repo, "e" * 64)
    assert result["status"] == "STORE_PATH_INVALID" and result["exit_code"] == 2


def test_link_like_record_is_refused(repo, capsys, monkeypatch):
    first = snap(capsys, repo)
    real = os.path.islink
    monkeypatch.setattr(os.path, "islink", lambda p: Path(p).suffix == ".json" or real(p))
    result = verify(capsys, repo, first["snapshot_id"])
    assert result["status"] == "STORE_PATH_INVALID"


# ------------------------------------------------------- D11 step 8: records consistent in every hash


def _busy_snapshot(capsys, repo: Path) -> dict:
    """A record with a changed entry, two untracked paths and one contract file."""
    (repo / "a.txt").write_bytes(b"changed\n")
    (repo / "b.txt").write_bytes(b"b\n")
    (repo / "c.txt").write_bytes(b"c\n")
    result = snap(capsys, repo)
    assert result["status"] == "STORED"
    return json.loads(record_file(repo, result["snapshot_id"]).read_bytes())


def _forge(repo: Path, record: dict, mutate) -> tuple[str, bytes]:
    """Apply `mutate`, then recompute state_sha256 and snapshot_id and write canonical bytes under the
    recomputed name: every byte, hash and name check passes, only the content is wrong."""
    forged = json.loads(json.dumps(record))
    mutate(forged)
    forged["state_sha256"] = store.state_sha256(forged["state"])
    forged["snapshot_id"] = store.snapshot_id_for(forged["task_id"], forged["state"], forged["reported"])
    raw = store.record_bytes(forged)
    assert json.loads(raw) == forged and raw == store.record_bytes(json.loads(raw))
    record_file(repo, forged["snapshot_id"]).write_bytes(raw)
    return forged["snapshot_id"], raw


def _set(*keys_and_value):
    *keys, value = keys_and_value

    def mutate(rec: dict) -> None:
        target = rec
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
    return mutate


def _entry(field: str, value: str):
    return lambda rec: rec["state"]["entries"][0].__setitem__(field, value)


def _contract(field: str, value: str):
    return lambda rec: rec["state"]["contract"][0].__setitem__(field, value)


def _append(key: str, item_of):
    return lambda rec: rec["state"][key].append(item_of(rec))


FORGED = {
    # repeated paths and order
    "entry-repeated": (_append("entries", lambda r: dict(r["state"]["entries"][0])), "repeat a path"),
    "entry-repeated-other-hash": (_append("entries", lambda r: {**r["state"]["entries"][0], "w_sha256": "f" * 64}),
                                  "repeat a path"),
    "entry-unsorted": (lambda r: r["state"]["entries"].insert(0, {**r["state"]["entries"][0], "path": "z.txt"}),
                       "not sorted"),
    "untracked-repeated": (_set("state", "untracked", ["b.txt", "b.txt", "c.txt"]), "repeats a path"),
    "untracked-unsorted": (_set("state", "untracked", ["c.txt", "b.txt"]), "not sorted"),
    "contract-repeated": (_append("contract", lambda r: dict(r["state"]["contract"][0])), "repeats a path"),
    "contract-unsorted": (_append("contract",
                                  lambda r: {**r["state"]["contract"][0], "path": f"docs/tasks/{TASK}/A.md"}),
                          "not sorted"),
    "changed-and-untracked": (_set("state", "untracked", ["a.txt", "b.txt", "c.txt"]),
                              "both changed and untracked"),
    # nested hashes
    "w-uppercase": (_entry("w_sha256", "F" * 64), "w_sha256"),
    "w-short": (_entry("w_sha256", "f" * 63), "w_sha256"),
    "w-absent-lowercase": (_entry("w_sha256", "absent"), "w_sha256"),
    "s-not-hex": (_entry("s_sha256", "g" * 64), "s_sha256"),
    "s-absent-with-index-mode": (_entry("s_sha256", "ABSENT"), "s_sha256"),
    "contract-head-hash": (_contract("head_sha256", "nope"), "contract hash"),
    "contract-work-hash": (_contract("work_sha256", "0" * 40), "contract hash"),
    # git modes, blobs and XY
    "head-mode": (_entry("head_mode", "100664"), "head_mode"),
    "index-mode-gitlink": (_entry("index_mode", "160000"), "index_mode"),
    "head-blob-not-hex": (_entry("head_blob", "g" * 40), "head_blob"),
    "index-blob-other-length": (_entry("index_blob", "0" * 64), "index_blob"),
    "xy-unknown": (_entry("xy", "XY"), "xy"),
    "xy-unchanged": (_entry("xy", ".."), "xy"),
    "xy-one-char": (_entry("xy", "M"), "xy"),
    "xy-rename": (_entry("xy", "R."), "xy"),
    # path formats
    "entry-path-parent": (_entry("path", "../a.txt"), "entry path"),
    "entry-path-absolute": (_entry("path", "/a.txt"), "entry path"),
    "entry-path-empty-part": (_entry("path", "x//a.txt"), "entry path"),
    "untracked-path-empty": (_set("state", "untracked", ["", "b.txt", "c.txt"]), "untracked is malformed"),
    "untracked-path-dot": (_set("state", "untracked", ["./b.txt", "c.txt"]), "untracked is malformed"),
    "contract-other-task": (_contract("path", "docs/tasks/T-2/WORK_ORDER.md"), "contract path"),
    "branch-empty": (_set("state", "branch", ""), "branch"),
    "tree-other-length": (_set("state", "tree", "0" * 64), "tree"),
}


@pytest.mark.parametrize("name", sorted(FORGED))
def test_forged_record_with_recomputed_hashes_is_corrupt_and_kept(repo, capsys, name):
    record = _busy_snapshot(capsys, repo)
    mutate, detail = FORGED[name]
    snapshot_id, raw = _forge(repo, record, mutate)
    assert snapshot_id != record["snapshot_id"]
    result = verify(capsys, repo, snapshot_id)
    assert result["status"] == "SNAPSHOT_CORRUPT" and result["exit_code"] == 2
    assert detail in result["error"]["detail"]
    assert result["file_sha256"] == sha(raw) and result["state_sha256_stored"] is None
    assert record_file(repo, snapshot_id).read_bytes() == raw


@pytest.mark.parametrize("created", ["2001-02-30T00:00:00Z", "2001-13-01T00:00:00Z", "2001-00-10T00:00:00Z",
                                     "2001-01-01T24:00:00Z", "2001-01-01T00:60:00Z", "2001-01-01T00:00:60Z",
                                     "0000-01-01T00:00:00Z", "2100-02-29T00:00:00Z", "2001-01-01 00:00:00Z",
                                     "2001-01-01T00:00:00+00:00", "2001-01-01T00:00:00.5Z"])
def test_meta_time_that_is_not_a_real_utc_time_is_corrupt(repo, capsys, created):
    record = _busy_snapshot(capsys, repo)
    path = record_file(repo, record["snapshot_id"])
    forged = {**record, "meta": {**record["meta"], "created_at_utc": created}}
    raw = store.record_bytes(forged)
    path.write_bytes(raw)
    result = verify(capsys, repo, record["snapshot_id"])
    assert result["status"] == "SNAPSHOT_CORRUPT" and result["error"]["detail"] == "meta is malformed"
    assert path.read_bytes() == raw


@pytest.mark.parametrize("mutate", [lambda r: None, _set("meta", "created_at_utc", "2024-02-29T23:59:59Z")],
                         ids=["unchanged", "leap-day"])
def test_forging_helper_alone_keeps_a_valid_record(repo, capsys, mutate):
    """Control for the forged cases: recomputing every hash of an unchanged (or validly re-timed) record
    still verifies, so the rejections above come from the content alone."""
    record = _busy_snapshot(capsys, repo)
    snapshot_id, raw = _forge(repo, record, mutate)
    assert snapshot_id == record["snapshot_id"]  # meta is outside the id
    result = verify(capsys, repo, snapshot_id)
    assert result["status"] == "MATCH" and result["file_sha256"] == sha(raw)


def test_existing_forged_record_with_the_same_id_is_corrupt_on_snapshot(repo, capsys):
    """D10 (b) uses the same D11 checks: a forged file sitting at the id of the next snapshot is refused."""
    record = _busy_snapshot(capsys, repo)
    path = record_file(repo, record["snapshot_id"])
    forged = {**record, "meta": {**record["meta"], "created_at_utc": "2001-02-30T00:00:00Z"}}
    path.write_bytes(store.record_bytes(forged))
    again = snap(capsys, repo)
    assert again["status"] == "SNAPSHOT_CORRUPT" and again["final_file_created"] is False


def test_compare_states_never_loses_a_difference(repo):
    state = collect.collect_state(repo, TASK)
    entry = {"path": "a.txt", "xy": ".M", "head_mode": "100644", "head_blob": "1" * 40, "index_mode": "100644",
             "index_blob": "1" * 40, "w_sha256": "2" * 64, "s_sha256": "3" * 64}
    later = {**entry, "w_sha256": "4" * 64}
    stored = {**state, "entries": [entry, later], "untracked": ["c.txt", "b.txt"]}
    current = {**state, "entries": [later], "untracked": ["b.txt", "c.txt"]}
    differences = store.compare_states(stored, current)
    assert {d["field"] for d in differences} == {"entries", "untracked"}
    assert all(set(d) == {"field", "stored", "current"} for d in differences)
    assert store.compare_states(state, json.loads(json.dumps(state))) == []


# ------------------------------------- D5 x D11: real collected states pass the record checks and MATCH


def _staged_add(repo: Path) -> None:
    (repo / "new.txt").write_bytes(b"new\n")
    git(repo, "add", "--", "new.txt")


def _work_delete(repo: Path) -> None:
    (repo / "a.txt").unlink()


def _staged_delete(repo: Path) -> None:
    git(repo, "rm", "-q", "--", "a.txt")


def _detached(repo: Path) -> None:
    git(repo, "switch", "-q", "--detach")


def _intent_to_add(repo: Path) -> None:
    (repo / "ita.txt").write_bytes(b"intent\n")
    git(repo, "add", "-N", "--", "ita.txt")


ROUND_TRIP = {
    "staged-add": (_staged_add, "new.txt"),
    "work-delete": (_work_delete, "a.txt"),
    "staged-delete": (_staged_delete, "a.txt"),
    "detached": (_detached, None),
    "intent-to-add": (_intent_to_add, "ita.txt"),
}


@pytest.mark.parametrize("name", sorted(ROUND_TRIP))
def test_collected_state_round_trips_to_a_match(repo, capsys, name):
    """Real git state -> collect -> save -> load -> verify, nothing replaced: the record the collector
    produced must pass every D11 check and the unchanged worktree must MATCH it."""
    change, path = ROUND_TRIP[name]
    change(repo)
    stored = snap(capsys, repo)
    assert stored["status"] == "STORED" and stored["exit_code"] == 0 and stored["error"] is None
    raw = record_file(repo, stored["snapshot_id"]).read_bytes()
    state = json.loads(raw)["state"]
    if path is None:
        assert state["branch"] is None and state["entries"] == []
    else:
        assert path in [entry["path"] for entry in state["entries"]] and path not in state["untracked"]
    result = verify(capsys, repo, stored["snapshot_id"])
    assert result["status"] == "MATCH" and result["exit_code"] == 0 and result["error"] is None
    assert result["differences"] == []
    assert result["file_sha256"] == stored["file_sha256"] == sha(raw)
    assert result["state_sha256_stored"] == result["state_sha256_current"] == stored["state_sha256_current"]
