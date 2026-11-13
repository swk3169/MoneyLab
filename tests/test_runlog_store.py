"""AUTO-03 AC3, AC4, AC6: evidence validation, storage that never replaces a file, and lookup of exactly one
named record without creating anything. tmp repositories only; the real checkout is never written."""

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

from moneylab.automation import evidence as ev
from moneylab.runlog import store as rl
from moneylab.storage import atomic
from moneylab.workstate import collect

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
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "init")
    return path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def doc(**over) -> dict:
    base = json.loads(ev.executed("knowledge_validate", "SUCCEEDED", 0, 5, b"out", b"err"))
    base.update(over)
    return base


def raw_of(d: dict, suffix: bytes = b"") -> bytes:
    return ev.canonical_json(d).encode("utf-8") + suffix


RAW = raw_of(doc())


def record_path(repo: Path, record_id: str, task: str = TASK) -> Path:
    return repo / rl.record_rel(task, record_id)


def store(repo: Path, raw: bytes = RAW, task: str = TASK) -> dict:
    return rl.store_at(repo, task, raw)


def show(repo: Path, record_id: str, task: str = TASK) -> dict:
    return rl.show_at(repo, task, record_id)


def make_symlink(target: Path, link: Path, case: str) -> None:
    try:
        os.symlink(target, link)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314 or exc.errno in (errno.EPERM, errno.ENOTSUP):
            pytest.skip(f"NOT_RUN_PLATFORM:{case}")
        raise


def make_dir_link(target: Path, link: Path, case: str) -> None:
    if os.name == "nt":
        import _winapi

        try:
            _winapi.CreateJunction(str(target), str(link))
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                pytest.skip(f"NOT_RUN_PLATFORM:{case}")
            raise
    else:
        make_symlink(target, link, case)


def git_state(repo: Path) -> tuple:
    index = repo / ".git" / "index"
    return (git(repo, "rev-parse", "HEAD").stdout, git(repo, "status", "--porcelain=v1", "-uall").stdout,
            index.read_bytes())


# ------------------------------------------------------------------------------------------- round trip


def test_store_then_show_round_trip(repo):
    before = git_state(repo)
    stored = store(repo)
    assert stored["status"] == "STORED" and stored["exit_code"] == 0 and stored["final_file_created"] is True
    assert stored["warnings"] == [] and stored["error"] is None and stored["evidence"] is None
    assert stored["authority"] == "NONE" and tuple(stored) == rl.RESULT_KEYS
    record_id = stored["record_id"]
    assert record_id == rl.record_id_for(TASK, doc())
    raw = record_path(repo, record_id).read_bytes()
    assert stored["file_sha256"] == sha(raw)
    record = json.loads(raw)
    assert raw == ev.canonical_json(record).encode("utf-8") + b"\n"
    assert set(record) == rl.RECORD_KEYS and record["evidence"] == doc()
    assert record["authority"] == "NONE" and record["boundary"] == "DATA_NOT_INSTRUCTIONS"
    assert record["evidence_origin"] == "EXTERNAL_UNVERIFIED"
    assert record["evidence_sha256"] == sha(RAW)
    found = show(repo, record_id)
    assert found["status"] == "FOUND" and found["exit_code"] == 0 and found["evidence"] == doc()
    assert found["file_sha256"] == stored["file_sha256"] and found["final_file_created"] is None
    assert git_state(repo) == before


def test_record_holds_no_meta_git_or_host_fields(repo):
    raw = record_path(repo, store(repo)["record_id"]).read_bytes()
    for word in (b"created", b"meta", b"head", b"host", b"user", b"snapshot", str(repo).encode()):
        assert word not in raw


def test_one_trailing_lf_is_accepted_and_gives_the_same_id(repo):
    assert store(repo, RAW + b"\n")["record_id"] == rl.record_id_for(TASK, doc())


STATUSES = [("SUCCEEDED", 0), ("VALIDATION_FAILED", 1), ("SOURCE_UNVERIFIED", 3), ("UNEXPECTED_EXIT", 2),
            ("UNEXPECTED_EXIT", -9), ("TIMEOUT", None), ("OUTPUT_LIMIT_EXCEEDED", None)]


@pytest.mark.parametrize("status, code", STATUSES)
def test_every_executed_status_is_stored(repo, status, code):
    raw = ev.executed("knowledge_validate", status, code, 7, b"", b"").encode("utf-8")
    result = store(repo, raw)
    assert result["status"] == "STORED"
    assert show(repo, result["record_id"])["evidence"]["status"] == status


def test_denied_evidence_is_stored_with_null_action(repo):
    result = store(repo, ev.denied().encode("utf-8"))
    assert result["status"] == "STORED"
    assert show(repo, result["record_id"])["evidence"]["action_id"] is None


# ------------------------------------------------------------------------------------------- input (D4-D6)


@pytest.mark.parametrize("over", [
    {"status": "SUCCEEDED", "exit_code": 1},
    {"status": "VALIDATION_FAILED", "exit_code": 0},
    {"status": "VALIDATION_FAILED", "exit_code": 3},
    {"status": "SOURCE_UNVERIFIED", "exit_code": 1},
    {"status": "UNEXPECTED_EXIT", "exit_code": 0},
    {"status": "UNEXPECTED_EXIT", "exit_code": 1},
    {"status": "UNEXPECTED_EXIT", "exit_code": 3},
    {"status": "SUCCEEDED", "exit_code": True},
    {"status": "TIMEOUT", "exit_code": 0},
    {"action_id": "not_registered"},
    {"action_id": None},
    {"decision": "DENY"},
    {"extra": 1},
])
def test_inconsistent_evidence_is_input_invalid(repo, over):
    result = store(repo, raw_of(doc(**over)))
    assert result["status"] == "INPUT_INVALID" and result["exit_code"] == 2
    assert result["final_file_created"] is None and result["record_id"] is None
    assert not (repo / "data").exists()


def test_denied_with_measurements_is_input_invalid(repo):
    bad = {**json.loads(ev.denied()), "exit_code": 0}
    assert store(repo, raw_of(bad))["status"] == "INPUT_INVALID"


MALFORMED = {
    "bom": b"\xef\xbb\xbf" + RAW,
    "not-utf8": b"\xff" + RAW,
    "duplicate-key": RAW[:-1] + b',"status":"SUCCEEDED"}',
    "nan": RAW.replace(b'"duration_ms":5', b'"duration_ms":NaN'),
    "infinity": RAW.replace(b'"duration_ms":5', b'"duration_ms":Infinity'),
    "overflow": RAW.replace(b'"duration_ms":5', b'"duration_ms":1e400'),
    "deep": b"[" * 30000 + b"]" * 30000,  # 60000 bytes: within STDIN_LIMIT, deeper than the parser allows
    "two-lf": RAW + b"\n\n",
    "crlf": RAW + b"\r\n",
    "cr": RAW + b"\r",
    "leading-space": b" " + RAW,
    "trailing-space": RAW + b" ",
    "two-objects": RAW + b"\n" + RAW,
    "array": b"[" + RAW + b"]",
    "pretty": json.dumps(doc(), sort_keys=True, indent=1).encode("utf-8"),
    "unsorted": json.dumps(dict(reversed(list(doc().items()))), separators=(",", ":")).encode("utf-8"),
    "empty": b"",
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_input_is_refused_before_any_path_access(repo, monkeypatch, name):
    calls: list[str] = []
    real = collect.run_git
    monkeypatch.setattr(collect, "run_git", lambda *a, **k: calls.append(a[1]) or real(*a, **k))
    result = store(repo, MALFORMED[name])
    assert result["status"] == "INPUT_INVALID" and result["exit_code"] == 2
    assert calls == [] and not (repo / "data").exists()


# Real deep JSON objects within STDIN_LIMIT. Where an interpreter gives up (parser, canonical serializer or
# neither) depends on its stack limits, so the stage is observed directly and parse_evidence must report the
# fixed detail of that stage. When neither fails, no depth path ran and the input must be refused as evidence.
DEEP_OBJECTS = {
    "object-around-deep-array": b'{"a":' + b"[" * 32700 + b"]" * 32700 + b"}",
    "deep-nested-objects": b'{"a":' * 10000 + b"1" + b"}" * 10000,
}
PARSE_DETAIL = "input is not one strict UTF-8 JSON object"
CANONICAL_DETAIL = "input cannot be serialized canonically"
EVIDENCE_DETAIL = "evidence does not satisfy moneylab.automation.evidence/1"


def observed_depth_stage(raw: bytes) -> str:
    try:
        obj = rl._strict_json(raw.decode("utf-8"))
    except RecursionError:
        return "parse"
    try:
        rl.canonical_bytes(obj)
    except RecursionError:
        return "canonical"
    return "none"


@pytest.mark.parametrize("name", sorted(DEEP_OBJECTS))
def test_real_deep_object_input_reports_the_stage_that_gave_up(name):
    raw = DEEP_OBJECTS[name]
    assert len(raw) <= rl.STDIN_LIMIT and raw.startswith(b"{")
    stage = observed_depth_stage(raw)
    expected = {"parse": PARSE_DETAIL, "canonical": CANONICAL_DETAIL, "none": EVIDENCE_DETAIL}[stage]
    with pytest.raises(rl.RunlogError) as exc:
        rl.parse_evidence(raw)
    assert exc.value.code == "INPUT_INVALID" and exc.value.detail == expected


def test_injected_parser_recursion_has_the_parser_detail(monkeypatch):
    def deep(text):
        raise RecursionError("injected")

    monkeypatch.setattr(rl, "_strict_json", deep)
    with pytest.raises(rl.RunlogError) as exc:
        rl.parse_evidence(RAW)
    assert exc.value.code == "INPUT_INVALID" and exc.value.detail == PARSE_DETAIL


def test_injected_serialization_recursion_has_the_canonical_detail(monkeypatch):
    def deep(obj):
        raise RecursionError("injected")

    monkeypatch.setattr(rl, "canonical_bytes", deep)
    with pytest.raises(rl.RunlogError) as exc:
        rl.parse_evidence(RAW)
    assert exc.value.code == "INPUT_INVALID" and exc.value.detail == CANONICAL_DETAIL


def test_input_size_boundary():
    at_limit = RAW + b" " * (rl.STDIN_LIMIT - len(RAW))
    assert len(at_limit) == rl.STDIN_LIMIT
    with pytest.raises(rl.RunlogError) as exc:
        rl.parse_evidence(at_limit)
    assert exc.value.code == "INPUT_INVALID"
    with pytest.raises(rl.RunlogError) as exc:
        rl.parse_evidence(at_limit + b" ")
    assert exc.value.code == "LIMIT_EXCEEDED"


def test_input_errors_never_echo_the_input(repo):
    canary = b'{"canary_value_xyz":1}'
    result = store(repo, canary)
    assert result["status"] == "INPUT_INVALID"
    assert "canary_value_xyz" not in json.dumps(result)


# ------------------------------------------------------------------------------------------- root and ignore (D8)


def test_root_that_is_not_the_top_level_is_environment_invalid(repo):
    sub = repo / "sub"
    sub.mkdir()
    for result in (rl.store_at(sub, TASK, RAW), rl.show_at(sub, TASK, "0" * 64)):
        assert result["status"] == "ENVIRONMENT_INVALID"
        assert result["error"]["detail"] == rl.ROOT_FAILED
    assert not (sub / "data").exists() and not (repo / "data").exists()


def test_root_git_failure_has_the_fixed_detail(repo, monkeypatch):
    def failing(*args, **kwargs):
        raise collect.WorkstateError("GIT_FAILED", f"secret {repo}")

    monkeypatch.setattr(collect, "run_git", failing)
    result = store(repo)
    assert result["status"] == "ENVIRONMENT_INVALID" and result["error"]["detail"] == rl.ROOT_FAILED
    assert str(repo) not in json.dumps(result)


def test_check_ignore_failure_is_git_failed_with_the_fixed_detail(repo, monkeypatch):
    real = collect.run_git

    def failing_ignore(root, sub, args, **kwargs):
        if sub == "check-ignore":
            raise collect.WorkstateError("LIMIT_EXCEEDED", f"stderr text {repo}")
        return real(root, sub, args, **kwargs)

    monkeypatch.setattr(collect, "run_git", failing_ignore)
    result = store(repo)
    assert result["status"] == "GIT_FAILED" and result["error"]["detail"] == rl.IGNORE_FAILED
    assert str(repo) not in json.dumps(result) and not (repo / "data").exists()


def test_store_path_that_git_does_not_ignore_is_refused_without_directories(repo):
    (repo / ".gitignore").write_bytes(b"")
    result = store(repo)
    assert result["status"] == "STORE_PATH_INVALID" and result["final_file_created"] is None
    assert not (repo / "data").exists()


def test_path_check_runs_before_check_ignore(repo, monkeypatch):
    (repo / "data").write_bytes(b"not a directory")
    calls: list[str] = []
    real = collect.run_git
    monkeypatch.setattr(collect, "run_git", lambda *a, **k: calls.append(a[1]) or real(*a, **k))
    result = store(repo)
    assert result["status"] == "STORE_PATH_INVALID" and result["error"]["detail"] == rl.PATH_FAILED
    assert calls == ["rev-parse"]


def test_show_does_not_run_check_ignore_and_creates_nothing(repo, monkeypatch):
    calls: list[str] = []
    real = collect.run_git
    monkeypatch.setattr(collect, "run_git", lambda *a, **k: calls.append(a[1]) or real(*a, **k))
    before = git_state(repo)
    result = show(repo, "a" * 64)
    assert result["status"] == "NOT_FOUND" and result["exit_code"] == 2
    assert result["error"]["code"] == "NOT_FOUND" and result["final_file_created"] is None
    assert calls == ["rev-parse"] and not (repo / "data").exists()
    assert git_state(repo) == before


def test_show_still_reads_a_record_after_the_ignore_rule_changes(repo):
    record_id = store(repo)["record_id"]
    (repo / ".gitignore").write_bytes(b"")
    assert show(repo, record_id)["status"] == "FOUND"


# ------------------------------------------------------------------------------------------- paths (D11, D15)


def test_missing_parent_and_missing_file_are_not_found(repo):
    assert show(repo, "b" * 64)["status"] == "NOT_FOUND"
    store(repo)
    assert show(repo, "b" * 64)["status"] == "NOT_FOUND"


def test_parent_inspection_error_is_store_path_invalid(repo, monkeypatch):
    store(repo)
    real = collect._lstat

    def failing(path):
        if Path(path).name == "runlog":
            raise PermissionError(errno.EACCES, "injected")
        return real(path)

    monkeypatch.setattr(collect, "_lstat", failing)
    for result in (show(repo, "c" * 64), store(repo)):
        assert result["status"] == "STORE_PATH_INVALID" and result["error"]["detail"] == rl.PATH_FAILED


def test_parent_codes_do_not_depend_on_the_workstate_detail(repo, monkeypatch):
    def odd(root, rel, code, *, require_regular):
        raise collect.WorkstateError("SOMETHING_ELSE", f"leak {root}")

    monkeypatch.setattr(collect, "check_tree_path", odd)
    for result in (show(repo, "c" * 64), store(repo)):
        assert result["status"] == "STORE_PATH_INVALID" and result["error"]["detail"] == rl.PATH_FAILED
        assert str(repo) not in json.dumps(result)


def test_link_like_parent_is_refused(repo, monkeypatch):
    (repo / "data" / "processed" / "runlog").mkdir(parents=True)
    real = os.path.islink
    monkeypatch.setattr(os.path, "islink", lambda p: Path(p).name == "runlog" or real(p))
    result = store(repo)
    assert result["status"] == "STORE_PATH_INVALID"
    assert not (repo / "data" / "processed" / "runlog" / TASK).exists()


def test_real_junction_as_store_directory_is_refused(repo, tmp_path):
    (repo / "data" / "processed").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    make_dir_link(outside, repo / "data" / "processed" / "runlog", "runlog-directory-link")
    assert store(repo)["status"] == "STORE_PATH_INVALID"
    assert show(repo, "d" * 64)["status"] == "STORE_PATH_INVALID"
    assert list(outside.iterdir()) == []


def test_final_file_lstat_errors_have_distinct_codes(repo, monkeypatch):
    record_id = store(repo)["record_id"]
    real = rl._lstat

    def failing(path):
        if Path(path).suffix == ".json":
            raise PermissionError(errno.EACCES, "injected")
        return real(path)

    monkeypatch.setattr(rl, "_lstat", failing)
    assert show(repo, record_id)["status"] == "RECORD_UNREADABLE"

    def missing(path):
        if Path(path).suffix == ".json":
            raise FileNotFoundError(errno.ENOENT, "injected")
        return real(path)

    monkeypatch.setattr(rl, "_lstat", missing)
    assert show(repo, record_id)["status"] == "NOT_FOUND"


def test_link_like_final_file_is_store_path_invalid(repo, monkeypatch):
    record_id = store(repo)["record_id"]
    real = os.path.islink
    monkeypatch.setattr(os.path, "islink", lambda p: Path(p).suffix == ".json" or real(p))
    assert show(repo, record_id)["status"] == "STORE_PATH_INVALID"


def test_real_symlinked_record_is_refused(repo, tmp_path):
    record_id = store(repo)["record_id"]
    path = record_path(repo, record_id)
    outside = tmp_path / "outside.json"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    make_symlink(outside, path, "runlog-record-symlink")
    assert show(repo, record_id)["status"] == "STORE_PATH_INVALID"
    assert store(repo)["status"] == "STORE_PATH_INVALID"


def test_non_regular_final_file_is_corrupt(repo):
    record_id = store(repo)["record_id"]
    path = record_path(repo, record_id)
    path.unlink()
    path.mkdir()
    assert show(repo, record_id)["status"] == "RECORD_CORRUPT"


def test_final_file_resolving_outside_the_root_is_refused(repo, monkeypatch):
    record_id = store(repo)["record_id"]
    real = os.path.realpath

    def outside(path, *args, **kwargs):
        if Path(path).suffix == ".json":
            return real(repo.parent / "elsewhere.json", *args, **kwargs)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os.path, "realpath", outside)
    result = show(repo, record_id)
    monkeypatch.undo()
    assert result["status"] == "STORE_PATH_INVALID"


def test_store_directory_resolving_outside_the_root_is_refused(repo, monkeypatch):
    real = os.path.realpath

    def outside(path, *args, **kwargs):
        if Path(path).name == TASK and os.path.lexists(path):
            return real(repo.parent / "elsewhere" / TASK, *args, **kwargs)
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os.path, "realpath", outside)
    result = store(repo)
    monkeypatch.undo()
    assert result["status"] == "STORE_PATH_INVALID"
    assert result["warnings"] == ["DIR_LEFT:data", "DIR_LEFT:data/processed", "DIR_LEFT:data/processed/runlog",
                                  f"DIR_LEFT:data/processed/runlog/{TASK}"]
    assert list((repo / "data" / "processed" / "runlog" / TASK).iterdir()) == []


# ------------------------------------------------------------------------------------------- records (D14, D15)


def test_same_evidence_again_is_already_stored_and_keeps_the_bytes(repo):
    first = store(repo)
    path = record_path(repo, first["record_id"])
    raw = path.read_bytes()
    again = store(repo)
    assert again["status"] == "ALREADY_STORED" and again["exit_code"] == 0
    assert again["final_file_created"] is False and again["file_sha256"] == first["file_sha256"] == sha(raw)
    assert path.read_bytes() == raw


def test_other_task_gives_another_record(repo):
    assert store(repo)["record_id"] != store(repo, task="T-2")["record_id"]


def tamper(repo: Path, record_id: str, change) -> tuple[Path, bytes]:
    path = record_path(repo, record_id)
    damaged = change(path.read_bytes())
    path.write_bytes(damaged)
    return path, damaged


def rebuilt(record: dict) -> bytes:
    return ev.canonical_json(record).encode("utf-8") + b"\n"


@pytest.mark.parametrize("change, code", [
    (lambda raw: raw[:-5], "RECORD_CORRUPT"),
    (lambda raw: raw[:-1] + b" \n", "RECORD_CORRUPT"),
    (lambda raw: raw + b"\n", "RECORD_CORRUPT"),
    (lambda raw: b"[]\n", "RECORD_CORRUPT"),
    (lambda raw: raw.replace(b'"schema":"moneylab.runlog.record/1"', b'"schema":7'), "RECORD_CORRUPT"),
    (lambda raw: raw.replace(b"runlog.record/1", b"runlog.record/2"), "RECORD_INCOMPATIBLE"),
    (lambda raw: rebuilt({**json.loads(raw), "authority": "ALL"}), "RECORD_CORRUPT"),
    (lambda raw: rebuilt({**json.loads(raw), "extra": 1}), "RECORD_CORRUPT"),
    (lambda raw: rebuilt({**json.loads(raw), "evidence_sha256": "0" * 64}), "RECORD_CORRUPT"),
    (lambda raw: rebuilt({**json.loads(raw), "evidence": doc(duration_ms=6)}), "RECORD_CORRUPT"),
])
def test_damaged_record_is_reported_and_kept(repo, change, code):
    record_id = store(repo)["record_id"]
    path, damaged = tamper(repo, record_id, change)
    found = show(repo, record_id)
    assert found["status"] == code and found["file_sha256"] == sha(damaged)
    again = store(repo)
    assert again["status"] == code and again["final_file_created"] is False
    assert path.read_bytes() == damaged


def test_record_with_recomputed_id_under_its_new_name_but_invalid_evidence_is_corrupt(repo):
    bad = doc(status="SUCCEEDED", exit_code=1)
    record = {**rl.build_record(TASK, doc()), "evidence": bad, "record_id": rl.record_id_for(TASK, bad),
              "evidence_sha256": sha(raw_of(bad))}
    store(repo)
    path = record_path(repo, record["record_id"])
    path.write_bytes(rebuilt(record))
    assert show(repo, record["record_id"])["status"] == "RECORD_CORRUPT"


def test_record_under_another_task_directory_is_corrupt(repo):
    record_id = store(repo)["record_id"]
    other = record_path(repo, record_id, "T-9")
    other.parent.mkdir(parents=True)
    other.write_bytes(record_path(repo, record_id).read_bytes())
    assert show(repo, record_id, "T-9")["status"] == "RECORD_CORRUPT"


def test_record_over_the_limit_is_corrupt(repo, monkeypatch):
    record_id = store(repo)["record_id"]
    monkeypatch.setattr(rl, "FILE_LIMIT", 100)
    assert show(repo, record_id)["status"] == "RECORD_CORRUPT"


def test_read_error_is_unreadable(repo, monkeypatch):
    record_id = store(repo)["record_id"]

    def failing(path):
        raise PermissionError(errno.EACCES, "injected")

    monkeypatch.setattr(rl, "_read_limited", failing)
    assert show(repo, record_id)["status"] == "RECORD_UNREADABLE"


def test_existing_record_with_a_different_identity_is_a_conflict(repo, monkeypatch):
    first = store(repo)
    path = record_path(repo, first["record_id"])
    raw = path.read_bytes()
    impostor = {**json.loads(raw), "evidence": doc(duration_ms=99)}
    monkeypatch.setattr(rl, "load_record", lambda root, task_id, record_id: (impostor, sha(raw)))
    again = store(repo)
    assert again["status"] == "RECORD_CONFLICT" and again["exit_code"] == 2
    assert again["final_file_created"] is False and again["file_sha256"] == sha(raw)
    assert path.read_bytes() == raw


def test_existing_file_that_vanishes_before_the_lookup_is_not_found(repo, monkeypatch):
    record_id = store(repo)["record_id"]

    def vanished(root, task_id, rid):
        raise rl.RunlogError("NOT_FOUND", "no such record")

    monkeypatch.setattr(rl, "load_record", vanished)
    again = store(repo)
    assert again["status"] == "NOT_FOUND" and again["final_file_created"] is False
    assert record_path(repo, record_id).is_file()


# ------------------------------------------------------------------------------------------- concurrency and faults


def test_two_threads_storing_the_same_record_create_one_file(repo):
    barrier = threading.Barrier(2)
    outcomes: list[dict] = []

    def worker():
        barrier.wait()
        outcomes.append(store(repo))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(o["status"] for o in outcomes) == ["ALREADY_STORED", "STORED"]
    assert outcomes[0]["file_sha256"] == outcomes[1]["file_sha256"]
    assert len(list((repo / "data" / "processed" / "runlog" / TASK).glob("*.json"))) == 1


def test_two_processes_storing_the_same_record_create_one_file(repo):
    script = ("import json, sys\nfrom pathlib import Path\nfrom moneylab.runlog import store\n"
              "print(json.dumps(store.store_at(Path(sys.argv[1]), 'T-1', sys.argv[2].encode())))\n")
    procs = [subprocess.Popen([sys.executable, "-B", "-c", script, str(repo), RAW.decode()], stdout=subprocess.PIPE)
             for _ in range(2)]
    results = [json.loads(proc.communicate(timeout=120)[0]) for proc in procs]
    assert sorted(r["status"] for r in results) == ["ALREADY_STORED", "STORED"]
    assert results[0]["file_sha256"] == results[1]["file_sha256"]
    assert len(list((repo / "data" / "processed" / "runlog" / TASK).glob("*.json"))) == 1


def test_concurrent_mkdir_of_a_plain_directory_continues(repo, monkeypatch):
    def racing(path):
        os.mkdir(path)
        raise FileExistsError(errno.EEXIST, "made by another run")

    monkeypatch.setattr(rl, "_mkdir", racing)
    assert store(repo)["status"] == "STORED"


def test_mkdir_failure_leaves_and_reports_created_directories(repo, monkeypatch):
    def failing(path):
        if Path(path).name == "runlog":
            raise PermissionError(errno.EACCES, "injected")
        os.mkdir(path)

    monkeypatch.setattr(rl, "_mkdir", failing)
    result = store(repo)
    assert result["status"] == "STORE_FAILED" and result["exit_code"] == 2 and result["final_file_created"] is None
    assert result["warnings"] == ["DIR_LEFT:data", "DIR_LEFT:data/processed"]


def test_fsync_failure_is_store_failed_and_creates_no_record(repo, monkeypatch):
    def failing(fd):
        raise OSError(errno.EIO, "injected")

    monkeypatch.setattr(os, "fsync", failing)
    result = store(repo)
    monkeypatch.undo()
    assert result["status"] == "STORE_FAILED" and result["final_file_created"] is False
    assert result["warnings"] == ["DIR_LEFT:data", "DIR_LEFT:data/processed", "DIR_LEFT:data/processed/runlog",
                                  f"DIR_LEFT:data/processed/runlog/{TASK}"]
    assert list((repo / "data" / "processed" / "runlog" / TASK).iterdir()) == []


def test_link_failure_with_temp_left_is_store_failed(repo, monkeypatch):
    def link_fails(src, dst):
        raise PermissionError(errno.EPERM, "injected")

    def unlink_fails(path, *args, **kwargs):
        raise PermissionError(errno.EACCES, "injected")

    monkeypatch.setattr(os, "link", link_fails)
    monkeypatch.setattr(os, "unlink", unlink_fails)
    result = store(repo)
    monkeypatch.undo()
    assert result["status"] == "STORE_FAILED" and result["final_file_created"] is False
    assert any(w.startswith("TMP_LEFTOVER:") for w in result["warnings"])
    assert list((repo / "data" / "processed" / "runlog" / TASK).glob("*.json")) == []


def test_temp_left_after_link_is_a_stored_warning(repo, monkeypatch):
    real = os.unlink

    def unlink(path, *args, **kwargs):
        if str(path).endswith(atomic.TMP_SUFFIX):
            raise PermissionError(errno.EACCES, "injected")
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", unlink)
    result = store(repo)
    monkeypatch.undo()
    assert result["status"] == "STORED" and result["exit_code"] == 1 and result["final_file_created"] is True
    assert len(result["warnings"]) == 1 and result["warnings"][0].startswith("TMP_LEFTOVER:")
    raw = record_path(repo, result["record_id"]).read_bytes()
    assert result["file_sha256"] == sha(raw)
    assert show(repo, result["record_id"])["status"] == "FOUND"
    assert store(repo)["status"] == "ALREADY_STORED"
