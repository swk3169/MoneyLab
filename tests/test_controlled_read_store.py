"""AUTO-08 D14-D16 audit records and status (TEST_GATES S1-S9).

`root` is a temporary git repository whose .gitignore ignores data/processed/*, and `home` is a tmp_path
directory: the real repository data/ and the real home are never used."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from moneylab.controlled_read import __main__ as cli
from moneylab.controlled_read import store

PK = "C--synthetic-project"
SID = "0a1b2c3d-0000-4000-8000-00000000abcd"
UUID = "11111111-2222-4333-8444-555555555555"
TASK = "AUTO-08-SYNTH"
WB = "-----BEGIN ECON-FWD-M20 WORK ORDER CANDIDATE-----"
WE = "-----END ECON-FWD-M20 WORK ORDER CANDIDATE-----"


def make_repo(path: Path, ignored: bool = True) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    if ignored:
        (path / ".gitignore").write_bytes(b"data/processed/*\n")
    return path


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return make_repo(tmp_path / "repo")


@pytest.fixture
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    d = h / ".claude" / "projects" / PK
    d.mkdir(parents=True)
    entry = {"type": "assistant", "uuid": UUID, "message": {"content": [{"type": "text", "text": WB + "\nA\n" + WE}]}}
    (d / f"{SID}.jsonl").write_bytes(json.dumps(entry).encode("utf-8") + b"\n")
    return h


def run_argv(attempt: str = "001", selector: str = f"assistant:{UUID}", profile: str = "ECON-FWD-M20-WO/1",
             task: str = TASK) -> list[str]:
    return ["run", "--task", task, "--project-key", PK, "--session", SID, "--selector", selector,
            "--profile", profile, "--attempt", attempt]


def status_argv(attempt: str = "001", task: str = TASK) -> list[str]:
    return ["status", "--task", task, "--attempt", attempt]


def call(capsysbinary, argv: list[str], root: Path, home: Path | None = None) -> tuple[int, bytes, dict]:
    code = cli.main(argv, root=root, home=home)
    out = capsysbinary.readouterr()
    assert out.err == b""
    assert out.out.endswith(b"\n") and out.out.count(b"\n") == 1
    return code, out.out, json.loads(out.out)


def attempt_dir(root: Path, attempt: str = "001", task: str = TASK) -> Path:
    return root / "data" / "processed" / "controlled_read" / task / attempt


def rewrite(path: Path, change) -> None:
    obj = json.loads(path.read_bytes())
    change(obj)
    path.write_bytes(store.canonical_bytes(obj))


def status_of(capsysbinary, root: Path, attempt: str = "001") -> dict:
    code, _raw, doc = call(capsysbinary, status_argv(attempt), root)
    assert code == 0
    return doc


# ------------------------------------------------------------------------------------- S1-S5


def test_s1_success_record_is_found_and_matches_stdout(capsysbinary, root, home):
    code, raw, doc = call(capsysbinary, run_argv(), root, home)
    assert code == 0 and doc["status"] == "SUCCEEDED"
    st = status_of(capsysbinary, root)
    assert st["state"] == "RESULT_FOUND"
    assert store.canonical_bytes(st["result"]) == raw
    d = attempt_dir(root)
    assert st["intent_sha256"] == hashlib.sha256((d / "intent.json").read_bytes()).hexdigest()
    assert st["result_sha256"] == hashlib.sha256((d / "result.json").read_bytes()).hexdigest()
    assert set(st) == {"schema", "command", "task_id", "attempt", "state", "intent_sha256", "result_sha256",
                       "result", "authority", "boundary"}
    assert (st["schema"], st["command"], st["authority"], st["boundary"]) == (
        "moneylab.controlled_read.status/1", "status", "NONE", "DATA_NOT_INSTRUCTIONS")


def test_records_have_the_exact_schemas(capsysbinary, root, home):
    _code, raw, _doc = call(capsysbinary, run_argv(), root, home)
    d = attempt_dir(root)
    intent = json.loads((d / "intent.json").read_bytes())
    assert set(intent) == store.INTENT_KEYS
    assert intent["schema"] == "moneylab.controlled_read.intent/1"
    assert (intent["authority"], intent["approval"], intent["boundary"]) == (
        "NONE", "NOT_VERIFIED_BY_PROGRAM", "DATA_NOT_INSTRUCTIONS")
    assert intent["profile"] == {"id": "ECON-FWD-M20-WO/1", "version": 1}
    stored = json.loads((d / "result.json").read_bytes())
    assert set(stored) == {"schema", "finished_utc", "result"}
    assert stored["schema"] == "moneylab.controlled_read.stored_result/1"
    assert store.canonical_bytes(stored["result"]) == raw
    for name in ("intent.json", "result.json"):
        data = (d / name).read_bytes()
        assert data == store.canonical_bytes(json.loads(data))
    assert sorted(p.name for p in d.iterdir()) == ["intent.json", "result.json"]


def test_s2_defined_failure_is_found_and_stays_a_failure(capsysbinary, root, home):
    entry = {"type": "assistant", "uuid": UUID, "message": {"content": [{"type": "text", "text": "no markers"}]}}
    (home / ".claude" / "projects" / PK / f"{SID}.jsonl").write_bytes(json.dumps(entry).encode() + b"\n")
    code, raw, doc = call(capsysbinary, run_argv(), root, home)
    assert code == 2 and doc["status"] == "MARKER_MISSING"
    st = status_of(capsysbinary, root)
    assert st["state"] == "RESULT_FOUND"
    assert st["result"]["status"] == "MARKER_MISSING"
    assert st["result"]["exit_code"] == 2 and st["result"]["values"] is None
    assert store.canonical_bytes(st["result"]) == raw


def test_s3_intent_only_is_outcome_unknown(capsysbinary, root, home):
    call(capsysbinary, run_argv(), root, home)
    (attempt_dir(root) / "result.json").unlink()
    st = status_of(capsysbinary, root)
    assert (st["state"], st["result"], st["result_sha256"]) == ("OUTCOME_UNKNOWN", None, None)


def test_s4_nothing_is_not_found(capsysbinary, root):
    st = status_of(capsysbinary, root)
    assert (st["state"], st["result"], st["intent_sha256"], st["result_sha256"]) == ("NOT_FOUND", None, None, None)


def test_s5_result_without_intent_is_corrupt(capsysbinary, root, home):
    call(capsysbinary, run_argv(), root, home)
    (attempt_dir(root) / "intent.json").unlink()
    st = status_of(capsysbinary, root)
    assert (st["state"], st["result"]) == ("RECORD_CORRUPT", None)


# ------------------------------------------------------------------------------------------- S6


@pytest.mark.parametrize("field, value", [
    ("session_id", "0a1b2c3d-0000-4000-8000-00000000abce"),
    ("selector", f"assistant:{UUID}:text:1"),
    ("project_key", "C--other"),
    ("profile", {"id": "ECON-FWD-M20-PREREG/1", "version": 1}),
    ("profile", {"id": "ECON-FWD-M20-WO/1", "version": 2}),
    ("task_id", "AUTO-08-OTHER"),
    ("attempt", "002"),
])
def test_s6_identity_mismatch_between_intent_and_result(capsysbinary, root, home, field, value):
    call(capsysbinary, run_argv(), root, home)

    def change(obj):
        obj[field] = value
    rewrite(attempt_dir(root) / "intent.json", change)
    assert status_of(capsysbinary, root)["state"] == "RECORD_CORRUPT"


def test_s6_identity_mismatch_with_the_attempt_path(capsysbinary, root, home):
    call(capsysbinary, run_argv(), root, home)
    shutil.copytree(attempt_dir(root), attempt_dir(root, "002"))
    assert status_of(capsysbinary, root, "002")["state"] == "RECORD_CORRUPT"
    assert status_of(capsysbinary, root, "001")["state"] == "RESULT_FOUND"


def test_s6_intent_only_with_wrong_path_is_corrupt(capsysbinary, root, home):
    call(capsysbinary, run_argv(), root, home)
    (attempt_dir(root) / "result.json").unlink()
    shutil.copytree(attempt_dir(root), attempt_dir(root, "003"))
    assert status_of(capsysbinary, root, "003")["state"] == "RECORD_CORRUPT"


# ------------------------------------------------------------------------------------------- S7


def _corrupt_stored(capsysbinary, root, home, mutate) -> str:
    call(capsysbinary, run_argv(), root, home)
    mutate(attempt_dir(root) / "result.json")
    return status_of(capsysbinary, root)["state"]


@pytest.mark.parametrize("mutate", [
    lambda p: rewrite(p, lambda o: o.update(schema="moneylab.controlled_read.stored_result/2")),
    lambda p: rewrite(p, lambda o: o.update(extra=1)),
    lambda p: rewrite(p, lambda o: o.pop("finished_utc")),
    lambda p: rewrite(p, lambda o: o.update(finished_utc="2026-11-25 00:00:00")),
    lambda p: p.write_bytes(json.dumps(json.loads(p.read_bytes()), indent=1).encode() + b"\n"),
    lambda p: p.write_bytes(p.read_bytes()[:-1]),
    lambda p: p.write_bytes(p.read_bytes()[:20]),
    lambda p: p.write_bytes(p.read_bytes() + b"\n"),
    lambda p: p.write_bytes(b""),
], ids=["schema", "extra-field", "finished-missing", "finished-format", "non-canonical", "no-final-lf",
        "truncated", "two-lf", "empty"])
def test_s7_stored_result_violations(capsysbinary, root, home, mutate):
    assert _corrupt_stored(capsysbinary, root, home, mutate) == "RECORD_CORRUPT"


def test_s7_intent_violations(capsysbinary, root, home):
    call(capsysbinary, run_argv(), root, home)
    p = attempt_dir(root) / "intent.json"
    original = p.read_bytes()
    for mutate in (lambda: rewrite(p, lambda o: o.update(approval="VERIFIED")),
                   lambda: rewrite(p, lambda o: o.update(selector="assistant:x")),
                   lambda: p.write_bytes(original.replace(b"\"approval\"", b"\"approval\" ")),
                   lambda: p.write_bytes(original[:-1])):
        mutate()
        assert status_of(capsysbinary, root)["state"] == "RECORD_CORRUPT"
        p.write_bytes(original)
    assert status_of(capsysbinary, root)["state"] == "RESULT_FOUND"


# ------------------------------------------------------------------------------------------- S8


@pytest.mark.parametrize("change", [
    lambda r: r.update(values=None),  # SUCCEEDED without values
    lambda r: r.update(status="MARKER_MISSING", values=None,
                       error={"code": "MARKER_MISSING", "detail": store.DETAILS["MARKER_MISSING"]}),  # exit 0
    lambda r: r.update(extra=1),
    lambda r: r.update(exit_code=2),
    lambda r: r.update(authority="ALL"),
    lambda r: r.update(approval="VERIFIED"),
    lambda r: r.update(boundary="INSTRUCTIONS"),
    lambda r: r.update(status="DONE"),
    lambda r: r.update(error={"code": "X", "detail": "y"}),
    lambda r: r["values"].update(bytes=True),
    lambda r: r["values"].update(sha256="ABC"),
    lambda r: r["target"].update(prefix_bytes=None),
    lambda r: r["target"].update(extra=1),
], ids=["succeeded-values-null", "error-exit-0", "extra-key", "succeeded-exit-2", "authority", "approval",
        "boundary", "unknown-status", "error-on-success", "bool-count", "bad-sha", "measured-null", "target-key"])
def test_s8_inner_result_violations(capsysbinary, root, home, change):
    def mutate(p):
        rewrite(p, lambda o: change(o["result"]))
    assert _corrupt_stored(capsysbinary, root, home, mutate) == "RECORD_CORRUPT"


def test_s8_failure_with_values_or_wrong_detail(capsysbinary, root, home):
    entry = {"type": "assistant", "uuid": UUID, "message": {"content": [{"type": "text", "text": "x"}]}}
    (home / ".claude" / "projects" / PK / f"{SID}.jsonl").write_bytes(json.dumps(entry).encode() + b"\n")
    call(capsysbinary, run_argv(), root, home)
    p = attempt_dir(root) / "result.json"
    original = p.read_bytes()
    for change in (lambda r: r.update(values={"sha256": "0" * 64, "bytes": 1, "lf": 1}),
                   lambda r: r["error"].update(detail="other"),
                   lambda r: r.update(exit_code=0, status="SUCCEEDED")):
        rewrite(p, lambda o, c=change: c(o["result"]))
        assert status_of(capsysbinary, root)["state"] == "RECORD_CORRUPT"
        p.write_bytes(original)
    assert status_of(capsysbinary, root)["state"] == "RESULT_FOUND"


# ------------------------------------------------------------------------------------------- S9


def test_s9_path_that_is_not_ignored(capsysbinary, tmp_path, home):
    bare = make_repo(tmp_path / "plain", ignored=False)
    code, _raw, doc = call(capsysbinary, run_argv(), bare, home)
    assert (code, doc["status"]) == (2, "STORE_PATH_INVALID")
    assert not (bare / "data").exists()


def test_s9_attempt_exists_and_nothing_is_overwritten(capsysbinary, root, home):
    call(capsysbinary, run_argv(), root, home)
    d = attempt_dir(root)
    before = {p.name: p.read_bytes() for p in d.iterdir()}
    code, _raw, doc = call(capsysbinary, run_argv(), root, home)
    assert (code, doc["status"]) == (2, "ATTEMPT_EXISTS")
    assert {p.name: p.read_bytes() for p in d.iterdir()} == before


def test_s9_empty_attempt_directory_already_exists(capsysbinary, root, home):
    attempt_dir(root).mkdir(parents=True)
    code, _raw, doc = call(capsysbinary, run_argv(), root, home)
    assert (code, doc["status"]) == (2, "ATTEMPT_EXISTS")
    assert list(attempt_dir(root).iterdir()) == []


def test_s9_link_like_record_parent(capsysbinary, root, home, monkeypatch):
    from moneylab.workstate import collect
    attempt_dir(root).parent.mkdir(parents=True)
    real = collect.is_link_like
    monkeypatch.setattr(collect, "is_link_like", lambda p, st: Path(p).name == TASK or real(p, st))
    code, _raw, doc = call(capsysbinary, run_argv(), root, home)
    assert (code, doc["status"]) == (2, "STORE_PATH_INVALID")
    assert not attempt_dir(root).exists()


# ------------------------------------------------------------------- ERRATA-001 E3 store failures
#
# Each case fixes the initial state (empty repository, no attempt directory) and the failure point. The seam
# replaces atomic_create_new_bytes for ONE file: it writes exactly the files listed for the case (or none),
# then raises CreateNewError. Expected files and status hold only under that fixed condition.

TMP_BYTES = b"synthetic partial temp bytes\n"


class Seam:
    def __init__(self, monkeypatch, name: str, write_final: bool, write_tmp: bool) -> None:
        from moneylab.storage.atomic import CreateNewError
        self.written: dict[str, bytes] = {}
        self.deleting: list[str] = []
        real = store.atomic_create_new_bytes

        def fake(path, data):
            path = Path(path)
            if path.name != name:
                return real(path, data)
            tmp = None
            if write_final:
                path.write_bytes(data)
                self.written[path.name] = data
            if write_tmp:
                tmp = path.parent / f".{path.name}.synthetic.tmp"
                tmp.write_bytes(TMP_BYTES)
                self.written[tmp.name] = TMP_BYTES
            raise CreateNewError(OSError("synthetic"), write_final, tmp)

        monkeypatch.setattr(store, "atomic_create_new_bytes", fake)
        import os
        for fn in ("remove", "unlink", "replace", "rename"):
            original = getattr(os, fn)

            def track(*args, _fn=fn, _orig=original, **kwargs):
                self.deleting.append(f"{_fn}:{args[0]}")
                return _orig(*args, **kwargs)
            monkeypatch.setattr(os, fn, track)

    def touched_written(self) -> list[str]:
        return [d for d in self.deleting if any(name in d for name in self.written)]


def _injected(capsysbinary, root, home, monkeypatch, name, write_final, write_tmp, session_text=None):
    from moneylab.controlled_read import transcript
    if session_text is not None:
        entry = {"type": "assistant", "uuid": UUID, "message": {"content": [{"type": "text", "text": session_text}]}}
        (home / ".claude" / "projects" / PK / f"{SID}.jsonl").write_bytes(json.dumps(entry).encode() + b"\n")
    opened: list = []
    real_open = transcript.open_session

    def track_open(*args, **kwargs):
        opened.append(args[2])
        return real_open(*args, **kwargs)
    monkeypatch.setattr(transcript, "open_session", track_open)
    seam = Seam(monkeypatch, name, write_final, write_tmp)
    code, _raw, doc = call(capsysbinary, run_argv(), root, home)
    monkeypatch.undo()
    d = attempt_dir(root)
    files = {p.name: p.read_bytes() for p in d.iterdir()}
    assert code == 2 and doc["status"] == "STORE_FAILED" and doc["exit_code"] == 2 and doc["values"] is None
    assert doc["error"] == {"code": "STORE_FAILED", "detail": store.DETAILS["STORE_FAILED"]}
    for fname, data in seam.written.items():
        assert files[fname] == data  # bytes the seam wrote are kept exactly
    assert seam.touched_written() == []
    state = status_of(capsysbinary, root)["state"]
    assert {p.name: p.read_bytes() for p in d.iterdir()} == files  # status changes nothing
    return doc, files, state, opened


def test_e3_case1_intent_failed_without_files(capsysbinary, root, home, monkeypatch):
    doc, files, state, opened = _injected(capsysbinary, root, home, monkeypatch, "intent.json", False, False)
    assert doc["record"] == {"file": "intent", "final_created": False, "tmp_leftover": False}
    assert doc["target"]["prefix_bytes"] is None and doc["target"]["prefix_check"] is None
    assert (files, state, opened) == ({}, "NOT_FOUND", [])


def test_e3_case2_intent_completed_with_a_temp_file_left(capsysbinary, root, home, monkeypatch):
    doc, files, state, opened = _injected(capsysbinary, root, home, monkeypatch, "intent.json", True, True)
    assert doc["record"] == {"file": "intent", "final_created": True, "tmp_leftover": True}
    assert doc["target"]["prefix_bytes"] is None and doc["target"]["prefix_check"] is None
    assert set(files) == {"intent.json", ".intent.json.synthetic.tmp"}
    assert files[".intent.json.synthetic.tmp"] == TMP_BYTES
    assert (state, opened) == ("OUTCOME_UNKNOWN", [])


def test_e3_case3_result_failed_without_files_after_success(capsysbinary, root, home, monkeypatch):
    doc, files, state, opened = _injected(capsysbinary, root, home, monkeypatch, "result.json", False, False)
    assert doc["record"] == {"file": "result", "final_created": False, "tmp_leftover": False}
    assert doc["target"]["prefix_check"] == "MATCHED" and doc["target"]["prefix_bytes"] is not None
    assert (set(files), state, len(opened)) == ({"intent.json"}, "OUTCOME_UNKNOWN", 1)


def test_e3_case4_result_completed_then_failed(capsysbinary, root, home, monkeypatch):
    doc, files, state, _opened = _injected(capsysbinary, root, home, monkeypatch, "result.json", True, False)
    assert doc["record"] == {"file": "result", "final_created": True, "tmp_leftover": False}
    assert set(files) == {"intent.json", "result.json"}
    stored = json.loads(files["result.json"])["result"]
    assert stored["status"] == "SUCCEEDED" and stored["record"] is None  # the defined stdout/record mismatch
    assert state == "RESULT_FOUND"


def test_e3_case5_processing_failure_and_result_failure(capsysbinary, root, home, monkeypatch):
    doc, files, state, _opened = _injected(capsysbinary, root, home, monkeypatch, "result.json", False, False,
                                           session_text="no markers")
    assert doc["status"] == "STORE_FAILED" and doc["target"]["prefix_check"] == "MATCHED"
    assert (set(files), state) == ({"intent.json"}, "OUTCOME_UNKNOWN")


# ------------------------------------------------------------------------- ERRATA-001 E4 checks


@pytest.mark.parametrize("change", [
    lambda r: r.clear() or r.update(store.status_error_document("ARGUMENT_INVALID", task_id=TASK, attempt="001")),
    lambda r: r.update(schema="moneylab.controlled_read.status/1"),
    lambda r: r.update(command="status"),
    lambda r: r.update(record={"file": "result", "final_created": True, "tmp_leftover": False}),
    lambda r: r.update(status="STORE_FAILED", values=None, exit_code=2,
                       error={"code": "STORE_FAILED", "detail": store.DETAILS["STORE_FAILED"]}),
    lambda r: r.update(status="ATTEMPT_EXISTS", values=None, exit_code=2,
                       error={"code": "ATTEMPT_EXISTS", "detail": store.DETAILS["ATTEMPT_EXISTS"]}),
    lambda r: r["target"].update(prefix_check="INCOMPLETE"),  # SUCCEEDED needs MATCHED
    lambda r: r["target"].update(prefix_check=None),
    lambda r: r["target"].update(prefix_check="OTHER"),
    lambda r: r.update(task_id=None),
    lambda r: r.update(profile=None),
], ids=["status-error-doc", "status-schema", "status-command", "record", "store-failed", "attempt-exists",
        "succeeded-incomplete", "check-null-measured", "check-unknown", "task-null", "profile-null"])
def test_e4_rejected_inner_results(capsysbinary, root, home, change):
    def mutate(p):
        rewrite(p, lambda o: change(o["result"]))
    assert _corrupt_stored(capsysbinary, root, home, mutate) == "RECORD_CORRUPT"


def test_e4_matched_with_a_processing_failure_is_found(capsysbinary, root, home):
    entry = {"type": "assistant", "uuid": UUID, "message": {"content": [{"type": "text", "text": "x"}]}}
    (home / ".claude" / "projects" / PK / f"{SID}.jsonl").write_bytes(json.dumps(entry).encode() + b"\n")
    call(capsysbinary, run_argv(), root, home)
    st = status_of(capsysbinary, root)
    assert st["state"] == "RESULT_FOUND"
    assert (st["result"]["status"], st["result"]["target"]["prefix_check"]) == ("MARKER_MISSING", "MATCHED")


@pytest.mark.parametrize("check, status, ok", [
    ("CHANGED", "SESSION_CHANGED", True), ("CHANGED", "MARKER_MISSING", False),
    ("TRUNCATED", "SESSION_TRUNCATED", True), ("TRUNCATED", "SESSION_CHANGED", False),
    ("INCOMPLETE", "TIME_LIMIT_EXCEEDED", True), ("INCOMPLETE", "SESSION_UNREADABLE", True),
    ("INCOMPLETE", "MARKER_MISSING", False), ("MATCHED", "TIME_LIMIT_EXCEEDED", True),
])
def test_e4_prefix_check_and_status_pairs(capsysbinary, root, home, check, status, ok):
    def mutate(p):
        def change(o):
            r = o["result"]
            r.update(status=status, exit_code=2, values=None, error={"code": status, "detail": store.DETAILS[status]})
            r["target"]["prefix_check"] = check
        rewrite(p, change)
    assert _corrupt_stored(capsysbinary, root, home, mutate) == ("RESULT_FOUND" if ok else "RECORD_CORRUPT")


def test_status_of_a_link_like_record_is_corrupt(capsysbinary, root, home, monkeypatch):
    from moneylab.workstate import collect
    call(capsysbinary, run_argv(), root, home)
    real = collect.is_link_like
    monkeypatch.setattr(collect, "is_link_like", lambda p, st: Path(p).name == "intent.json" or real(p, st))
    assert status_of(capsysbinary, root)["state"] == "RECORD_CORRUPT"


# ------------------------------------------------------- ERRATA-002 F3 directory preparation failures


def _prep_failure(capsysbinary, repo, home, monkeypatch, expected):
    """Run once with the seams already set; check the F3 outcome and that nothing was created or removed."""
    import os

    from moneylab.controlled_read import transcript
    creates: list = []
    opens: list = []
    removals: list = []
    real_create = store.atomic_create_new_bytes
    real_open = transcript.open_session

    def track_create(path, data):
        creates.append(Path(path).name)
        return real_create(path, data)

    def track_open(*args, **kwargs):
        opens.append(args[2])
        return real_open(*args, **kwargs)

    monkeypatch.setattr(store, "atomic_create_new_bytes", track_create)
    monkeypatch.setattr(transcript, "open_session", track_open)
    for fn in ("rmdir", "removedirs", "remove", "unlink"):
        original = getattr(os, fn)

        def track(*args, _fn=fn, _orig=original, **kwargs):
            removals.append(_fn)
            return _orig(*args, **kwargs)
        monkeypatch.setattr(os, fn, track)
    before = sorted(str(p.relative_to(repo)) for p in repo.rglob("*") if ".git" not in p.parts)
    code, _raw, doc = call(capsysbinary, run_argv(), repo, home)
    monkeypatch.undo()
    after = sorted(str(p.relative_to(repo)) for p in repo.rglob("*") if ".git" not in p.parts)
    assert (code, doc["status"], doc["exit_code"]) == (2, expected, 2)
    assert doc["values"] is None and doc["record"] is None
    assert doc["error"] == {"code": expected, "detail": store.DETAILS[expected]}
    assert (creates, opens, removals) == ([], [], [])
    assert set(before) <= set(after)  # nothing that existed was removed
    assert not any(name.endswith(("intent.json", "result.json")) for name in after)
    return after


def test_f3_intermediate_mkdir_oserror(capsysbinary, root, home, monkeypatch):
    real_mkdir = Path.mkdir

    def failing(self, *args, **kwargs):
        if self.name == TASK:
            raise PermissionError("synthetic")
        return real_mkdir(self, *args, **kwargs)
    monkeypatch.setattr(Path, "mkdir", failing)
    after = _prep_failure(capsysbinary, root, home, monkeypatch, "STORE_PATH_INVALID")
    assert (root / "data" / "processed" / "controlled_read").is_dir()  # created before the failure, kept
    assert "data/processed/controlled_read/" + TASK not in [p.replace("\\", "/") for p in after]


def test_f3_recheck_after_creation_fails(capsysbinary, root, home, monkeypatch):
    from moneylab.workstate import collect
    real = collect.check_tree_path
    calls: list = []

    def second_none(base, rel, code, *, require_regular):
        if rel == store.attempt_rel(TASK, "001"):
            calls.append(rel)
            if len(calls) == 2:
                return None
        return real(base, rel, code, require_regular=require_regular)
    monkeypatch.setattr(collect, "check_tree_path", second_none)
    _prep_failure(capsysbinary, root, home, monkeypatch, "STORE_PATH_INVALID")
    assert attempt_dir(root).is_dir() and list(attempt_dir(root).iterdir()) == []  # left as it is


def test_f3_link_like_component(capsysbinary, root, home, monkeypatch):
    from moneylab.workstate import collect
    attempt_dir(root).parent.mkdir(parents=True)
    real = collect.is_link_like
    monkeypatch.setattr(collect, "is_link_like", lambda p, st: Path(p).name == TASK or real(p, st))
    _prep_failure(capsysbinary, root, home, monkeypatch, "STORE_PATH_INVALID")
    assert attempt_dir(root).parent.is_dir() and not attempt_dir(root).exists()


def test_f3_path_not_ignored(capsysbinary, tmp_path, home, monkeypatch):
    plain = make_repo(tmp_path / "plain", ignored=False)
    _prep_failure(capsysbinary, plain, home, monkeypatch, "STORE_PATH_INVALID")
    assert not (plain / "data").exists()


def test_f3_attempt_already_exists(capsysbinary, root, home, monkeypatch):
    attempt_dir(root).mkdir(parents=True)
    _prep_failure(capsysbinary, root, home, monkeypatch, "ATTEMPT_EXISTS")
    assert attempt_dir(root).is_dir() and list(attempt_dir(root).iterdir()) == []
