"""AUTO-03 AC3, AC5: the CLI result format, statuses and exit codes. Internal tests inject a tmp root and an
input stream into the private CLI function; the real entry point is run only for cases that write nothing
(--help, bad arguments, bad evidence). Internal tests do not verify the production root decision."""

from __future__ import annotations

import errno
import inspect
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from moneylab.automation import evidence as ev
from moneylab.runlog import store as rl
from moneylab.runlog.__main__ import _main, main
from moneylab.storage import atomic

TASK = "T-1"
RO_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
RAW = ev.executed("knowledge_validate", "SUCCEEDED", 0, 5, b"out", b"").encode("utf-8")
PACKAGE_ROOT = Path(rl.__file__).resolve().parents[3]


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True, env=RO_ENV)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    for key, value in (("user.email", "t@example.invalid"), ("user.name", "T"), ("core.autocrlf", "false"),
                       ("commit.gpgsign", "false")):
        git(path, "config", key, value)
    (path / ".gitignore").write_bytes(b"data/processed/*\n")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "init")
    return path


class _NoRead(io.RawIOBase):
    def read(self, size: int = -1) -> bytes:
        raise AssertionError("stdin must not be read")


def cli(capsys, repo: Path, args: list[str], stdin: io.IOBase | None = None) -> tuple[dict, bytes]:
    code = _main(args, root=repo, stdin=stdin if stdin is not None else _NoRead())  # type: ignore[arg-type]
    captured = capsys.readouterr()
    assert captured.err == ""
    out = captured.out.encode("utf-8")
    result = json.loads(out)
    assert result["exit_code"] == code
    return result, out


def check_shape(result: dict, out: bytes) -> None:
    assert tuple(result) == tuple(sorted(rl.RESULT_KEYS))
    assert out == ev.canonical_json(result).encode("utf-8") + b"\n"
    assert result["schema"] == "moneylab.runlog.result/1" and result["authority"] == "NONE"
    if result["error"] is None:
        assert result["status"] in ("STORED", "ALREADY_STORED", "FOUND")
        assert result["exit_code"] == (1 if result["warnings"] else 0)
    else:
        assert result["status"] == result["error"]["code"] in rl.ERROR_CODES
        assert result["exit_code"] == 2 and result["evidence"] is None
        assert set(result["error"]) == {"code", "detail"}


def test_cli_store_then_show(repo, capsys):
    stored, out = cli(capsys, repo, ["store", "--task-id", TASK], io.BytesIO(RAW + b"\n"))
    check_shape(stored, out)
    assert stored["status"] == "STORED" and stored["evidence"] is None and stored["command"] == "store"
    found, out = cli(capsys, repo, ["show", "--task-id", TASK, "--record-id", stored["record_id"]])
    check_shape(found, out)
    assert found["status"] == "FOUND" and found["evidence"] == json.loads(RAW)
    assert found["command"] == "show" and found["file_sha256"] == stored["file_sha256"]
    again, out = cli(capsys, repo, ["store", "--task-id", TASK], io.BytesIO(RAW))
    check_shape(again, out)
    assert again["status"] == "ALREADY_STORED" and again["record_id"] == stored["record_id"]


def test_cli_and_api_give_the_same_record(repo, capsys):
    stored, _ = cli(capsys, repo, ["store", "--task-id", TASK], io.BytesIO(RAW))
    assert rl.show_at(repo, TASK, stored["record_id"])["evidence"] == json.loads(RAW)
    assert stored["record_id"] == rl.record_id_for(TASK, json.loads(RAW))


def test_store_reads_at_most_the_limit_plus_one(repo, capsys):
    class Counting(io.BytesIO):
        sizes: list[int] = []

        def read(self, size: int | None = -1) -> bytes:
            self.sizes.append(-1 if size is None else size)
            return super().read(size)

    stream = Counting(b" " * (rl.STDIN_LIMIT * 2))
    result, out = cli(capsys, repo, ["store", "--task-id", TASK], stream)
    check_shape(result, out)
    assert result["status"] == "LIMIT_EXCEEDED" and stream.sizes == [rl.STDIN_LIMIT + 1]


@pytest.mark.parametrize("args", [
    [],
    ["list"],
    ["store"],
    ["store", "--task-id", TASK, "--root", "x"],
    ["store", "--task-id", "lower"],
    ["store", "--task-id", "T" * 65],
    ["show", "--task-id", TASK],
    ["show", "--task-id", TASK, "--record-id", "A" * 64],
    ["show", "--task-id", TASK, "--record-id", "a" * 63],
    ["show", "--task-id", TASK, "--record-id", "../" + "a" * 61],
])
def test_bad_arguments_are_argument_invalid(repo, capsys, args):
    result, out = cli(capsys, repo, args)
    check_shape(result, out)
    assert result["status"] == "ARGUMENT_INVALID"
    assert not (repo / "data").exists()


def test_show_does_not_read_stdin(repo, capsys):
    result, out = cli(capsys, repo, ["show", "--task-id", TASK, "--record-id", "a" * 64], _NoRead())
    check_shape(result, out)
    assert result["status"] == "NOT_FOUND" and result["exit_code"] == 2


def test_errors_carry_no_input_text_or_absolute_path(repo, capsys):
    canary = b'{"canary_text_abc":"' + str(repo).encode().replace(b"\\", b"/") + b'"}'
    result, out = cli(capsys, repo, ["store", "--task-id", TASK], io.BytesIO(canary))
    check_shape(result, out)
    assert result["status"] == "INPUT_INVALID"
    assert b"canary_text_abc" not in out and str(repo).encode() not in out


def test_warning_success_exits_with_one(repo, capsys, monkeypatch):
    real = os.unlink

    def unlink(path, *args, **kwargs):
        if str(path).endswith(atomic.TMP_SUFFIX):
            raise PermissionError(errno.EACCES, "injected")
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", unlink)
    result, out = cli(capsys, repo, ["store", "--task-id", TASK], io.BytesIO(RAW))
    monkeypatch.undo()
    check_shape(result, out)
    assert result["status"] == "STORED" and result["exit_code"] == 1 and result["final_file_created"] is True


def test_production_main_has_no_root_or_test_option():
    assert list(inspect.signature(main).parameters) == ["argv"]
    help_text = subprocess.run([sys.executable, "-B", "-m", "moneylab.runlog", "store", "--help"],
                               capture_output=True, cwd=PACKAGE_ROOT).stdout.decode()
    assert "--root" not in help_text and "--task-id" in help_text


# ------------------------------------------------------------------------------------------- real entry point


def entry(args: list[str], stdin: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([sys.executable, "-B", "-m", "moneylab.runlog", *args], input=stdin,
                          capture_output=True, timeout=120, cwd=PACKAGE_ROOT)


def test_entry_point_help_is_plain_text_with_exit_zero():
    proc = entry(["--help"])
    assert proc.returncode == 0 and proc.stderr == b"" and b"usage" in proc.stdout


@pytest.mark.parametrize("args", [[], ["show", "--task-id", TASK, "--record-id", "bad"], ["store"]])
def test_entry_point_bad_arguments(args):
    proc = entry(args)
    result = json.loads(proc.stdout)
    assert proc.returncode == 2 and proc.stderr == b""
    assert result["status"] == "ARGUMENT_INVALID" and tuple(result) == tuple(sorted(rl.RESULT_KEYS))
    assert proc.stdout == ev.canonical_json(result).encode("utf-8") + b"\n"


# ------------------------------------------------------------------------------------------- ERRATA-001 D1, D16-D18


class _ReadFails(io.RawIOBase):
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc

    def read(self, size: int = -1) -> bytes:
        raise self.exc


@pytest.mark.parametrize("exc", [OSError(errno.EIO, "canary_read_xyz"), ValueError("canary_read_xyz")])
def test_unreadable_stdin_is_environment_invalid(repo, capsys, exc):
    result, out = cli(capsys, repo, ["store", "--task-id", TASK], _ReadFails(exc))
    check_shape(result, out)
    assert result["status"] == "ENVIRONMENT_INVALID" and result["error"]["detail"] == "input stream unavailable"
    assert result["evidence"] is None and result["final_file_created"] is None and result["task_id"] == TASK
    assert b"canary_read_xyz" not in out and not (repo / "data").exists()


@pytest.mark.parametrize("stdin_object", [None, object()])
def test_missing_stdin_buffer_is_environment_invalid(repo, capsys, monkeypatch, stdin_object):
    monkeypatch.setattr(sys, "stdin", stdin_object)
    code = _main(["store", "--task-id", TASK], root=repo, stdin=None)
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    check_shape(result, captured.out.encode("utf-8"))
    assert code == 2 and captured.err == ""
    assert result["status"] == "ENVIRONMENT_INVALID" and result["error"]["detail"] == "input stream unavailable"
    assert result["final_file_created"] is None


def test_undefined_internal_exception_has_no_result_and_a_fixed_line(repo, capsys, monkeypatch):
    def broken(root, task_id, raw):
        raise RuntimeError(f"canary_internal_xyz {repo}")

    monkeypatch.setattr(rl, "store_at", broken)
    code = _main(["store", "--task-id", TASK], root=repo, stdin=io.BytesIO(RAW))
    captured = capsys.readouterr()
    assert code == 2 and captured.out == ""
    assert captured.err == "runlog: internal failure; outcome unknown\n"
    assert "canary_internal_xyz" not in captured.err and str(repo) not in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("exc", [KeyboardInterrupt, SystemExit(3)])
def test_keyboard_interrupt_and_system_exit_are_not_turned_into_internal_failure(repo, capsys, monkeypatch, exc):
    def interrupted(root, task_id, raw):
        raise exc

    monkeypatch.setattr(rl, "store_at", interrupted)
    with pytest.raises(type(exc) if isinstance(exc, BaseException) else exc):
        _main(["store", "--task-id", TASK], root=repo, stdin=io.BytesIO(RAW))
    assert capsys.readouterr().err == ""


class _FailingBuffer:
    """Fake stdout buffer (not a real pipe): raises, or returns a short count, 0 or None."""

    def __init__(self, message: str, mode: str) -> None:
        self.message = message
        self.mode = mode
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> int | None:
        self.writes.append(data)
        if self.mode == "raise":
            raise OSError(errno.EPIPE, self.message)
        if self.mode == "short":
            return len(data) - 1
        if self.mode == "zero":
            return 0
        return None

    def flush(self) -> None:
        pass


class _FailingStdout:
    def __init__(self, message: str, mode: str) -> None:
        self.buffer = _FailingBuffer(message, mode)

    def flush(self) -> None:
        pass


@pytest.mark.parametrize("mode", ["raise", "short", "zero", "none"])
def test_stdout_failure_after_the_file_was_created_is_unknown_without_retry(repo, monkeypatch, mode):
    calls: list[str] = []
    real_store = rl.store_at

    def counting(root, task_id, raw):
        calls.append(task_id)
        return real_store(root, task_id, raw)

    monkeypatch.setattr(rl, "store_at", counting)
    fake_out = _FailingStdout(f"canary_output_xyz {repo}", mode)
    fake_err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", fake_out)
    monkeypatch.setattr(sys, "stderr", fake_err)
    code = _main(["store", "--task-id", TASK], root=repo, stdin=io.BytesIO(RAW))
    monkeypatch.undo()
    assert code == 2
    assert calls == [TASK]  # stored once, never re-run
    assert len(fake_out.buffer.writes) == 1  # one result attempted, no second result
    err = fake_err.getvalue()
    assert err == "runlog: output failure; outcome unknown\n"
    assert "canary_output_xyz" not in err and str(repo) not in err and "Traceback" not in err
    record_id = rl.record_id_for(TASK, json.loads(RAW))
    assert (repo / rl.record_rel(TASK, record_id)).is_file()  # read-only check, no store re-run
    assert rl.show_at(repo, TASK, record_id)["status"] == "FOUND"


def test_real_closed_stdout_pipe_gives_exit_two_and_only_the_fixed_line():
    """Real child process (not a fake stream): its stdout is a pipe whose read end is already closed, so the
    result write fails. Uses the bad-argument path, which stores nothing. The parent's own stdout is untouched."""
    from moneylab.runlog import __main__ as cli_main

    read_end, write_end = os.pipe()
    os.close(read_end)
    try:
        proc = subprocess.Popen([sys.executable, "-B", "-m", "moneylab.runlog"], stdin=subprocess.DEVNULL,
                                stdout=write_end, stderr=subprocess.PIPE, cwd=PACKAGE_ROOT)
    finally:
        os.close(write_end)
    try:
        _, err = proc.communicate(timeout=120)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=30)
    assert proc.returncode == 2
    lines = err.decode("utf-8").splitlines()
    assert lines == [cli_main.OUTPUT_FAILURE]
    assert b"Exception ignored" not in err and b"Traceback" not in err and b"OSError" not in err


class _FdStdout:
    def __init__(self, fd: int) -> None:
        self.fd = fd

    def fileno(self) -> int:
        return self.fd


def _silence_with(monkeypatch, stdout_fd: int, open_result, dup2_error: BaseException | None = None):
    """Run _silence_broken_stdout against a fake stdout fd with fake os.open/dup2/close; nothing real moves."""
    from moneylab.runlog import __main__ as cli_main

    calls: list[tuple] = []

    def fake_open(path, flags, *args):
        calls.append(("open", path, flags, args))
        if isinstance(open_result, BaseException):
            raise open_result
        return open_result

    def fake_dup2(src, dst, *args):
        calls.append(("dup2", src, dst))
        if dup2_error is not None:
            raise dup2_error

    def fake_close(fd):
        calls.append(("close", fd))

    monkeypatch.setattr(sys, "stdout", _FdStdout(stdout_fd))
    monkeypatch.setattr(cli_main.os, "open", fake_open)
    monkeypatch.setattr(cli_main.os, "dup2", fake_dup2)
    monkeypatch.setattr(cli_main.os, "close", fake_close)
    try:
        cli_main._silence_broken_stdout()
    finally:
        monkeypatch.undo()
    return calls


def test_silence_opens_devnull_write_only_and_closes_the_extra_fd(monkeypatch):
    calls = _silence_with(monkeypatch, 41, 97)
    assert calls == [("open", os.devnull, os.O_WRONLY, ()), ("dup2", 97, 41), ("close", 97)]


def test_silence_does_not_close_stdout_when_devnull_got_the_same_number(monkeypatch):
    calls = _silence_with(monkeypatch, 41, 41)
    assert ("close", 41) not in calls


def test_silence_survives_open_and_dup2_failures(monkeypatch):
    assert _silence_with(monkeypatch, 41, OSError("no devnull")) == [("open", os.devnull, os.O_WRONLY, ())]
    calls = _silence_with(monkeypatch, 41, 97, OSError("dup2 failed"))
    assert calls[-1] == ("close", 97)


def test_silence_ignores_a_stream_without_a_usable_fd(monkeypatch):
    from moneylab.runlog import __main__ as cli_main

    monkeypatch.setattr(sys, "stdout", object())
    cli_main._silence_broken_stdout()
    monkeypatch.setattr(sys, "stdout", _FdStdout(-1))
    cli_main._silence_broken_stdout()


def test_api_passes_undefined_exceptions_to_the_caller_without_output(repo, capsys, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("canary_api_xyz")

    monkeypatch.setattr(rl, "package_root", lambda: repo)
    monkeypatch.setattr(rl, "save_record", broken)
    with pytest.raises(RuntimeError, match="canary_api_xyz"):
        rl.store_evidence(TASK, RAW)
    monkeypatch.setattr(rl, "load_record", broken)
    with pytest.raises(RuntimeError, match="canary_api_xyz"):
        rl.load_evidence(TASK, "a" * 64)
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
    assert not (repo / "data" / "processed" / "runlog" / TASK).exists()


def _sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _schema_ok(o: dict) -> bool:
    """D16-D17 (as replaced by ERRATA-001) for one parsed result object; test helper only."""
    if o["schema"] != rl.RESULT_SCHEMA or o["authority"] != "NONE" or o["command"] not in (None, "store", "show"):
        return False
    if type(o["exit_code"]) is not int or not isinstance(o["status"], str):
        return False
    if not isinstance(o["warnings"], list) or not all(isinstance(w, str) for w in o["warnings"]):
        return False
    if o["task_id"] is not None and not rl.valid_task_id(o["task_id"]):
        return False
    if o["record_id"] is not None and not rl.valid_record_id(o["record_id"]):
        return False
    if o["file_sha256"] is not None and not _sha(o["file_sha256"]):
        return False
    if o["final_file_created"] is not None and type(o["final_file_created"]) is not bool:
        return False
    success = {"STORED": "store", "ALREADY_STORED": "store", "FOUND": "show"}
    if o["status"] in success:
        if o["error"] is not None or o["command"] != success[o["status"]]:
            return False
        if o["exit_code"] != (1 if o["warnings"] else 0):
            return False
        if o["task_id"] is None or o["record_id"] is None or o["file_sha256"] is None:
            return False
        if o["status"] == "FOUND":
            return (o["final_file_created"] is None and isinstance(o["evidence"], dict)
                    and rl._evidence_problem(o["evidence"]) is None)
        return o["evidence"] is None and o["final_file_created"] is (o["status"] == "STORED")
    if o["status"] not in rl.ERROR_CODES or o["exit_code"] != 2 or o["evidence"] is not None:
        return False
    err = o["error"]
    return (isinstance(err, dict) and set(err) == {"code", "detail"} and err["code"] == o["status"]
            and isinstance(err["detail"], str))


def accept(stdout: bytes, stderr: bytes, code: int) -> dict | None:
    """The D18 caller rule, as a test helper only (not production code and not evidence of production
    behaviour): a result is accepted when stdout is exactly one canonical result object plus LF that passes the
    D16-D17 schema, its exit_code equals the process exit code and stderr is empty. Otherwise UNKNOWN."""
    if stderr != b"" or not stdout.endswith(b"\n") or stdout.count(b"\n") != 1:
        return None
    try:
        obj = json.loads(stdout[:-1])
    except ValueError:
        return None
    if not isinstance(obj, dict) or tuple(obj) != tuple(sorted(rl.RESULT_KEYS)):
        return None
    if ev.canonical_json(obj).encode("utf-8") != stdout[:-1]:
        return None
    if not _schema_ok(obj) or obj["exit_code"] != code:
        return None
    return obj


def run_captured(capsys, repo: Path, args: list[str], stdin=None) -> tuple[bytes, bytes, int]:
    code = _main(args, root=repo, stdin=stdin if stdin is not None else _NoRead())  # type: ignore[arg-type]
    captured = capsys.readouterr()
    return captured.out.encode("utf-8"), captured.err.encode("utf-8"), code


def test_caller_rule_accepts_real_success_and_defined_error(repo, capsys):
    ok = accept(*run_captured(capsys, repo, ["store", "--task-id", TASK], io.BytesIO(RAW)))
    assert ok is not None and ok["status"] == "STORED"
    err = accept(*run_captured(capsys, repo, ["show", "--task-id", TASK, "--record-id", "f" * 64]))
    assert err is not None and err["status"] == "NOT_FOUND" and err["exit_code"] == 2


def test_caller_rule_refuses_damaged_or_ambiguous_output(repo, capsys):
    out, err, code = run_captured(capsys, repo, ["store", "--task-id", TASK], io.BytesIO(RAW))
    assert accept(out, err, code) is not None
    assert accept(out[:-10] + b"\n", err, code) is None  # partial JSON
    assert accept(out[:-1], err, code) is None  # final LF missing
    assert accept(out + out, err, code) is None  # two result objects
    assert accept(out, err, 2) is None  # object exit_code differs from the process exit code
    assert accept(out, b"runlog: output failure; outcome unknown\n", code) is None
    assert accept(out, b"runlog: internal failure; outcome unknown\n", code) is None
    assert accept(b"usage: python -m moneylab.runlog\n", b"", 0) is None  # --help text is not a result


def test_caller_rule_does_not_treat_the_phrase_inside_json_data_as_failure(repo, capsys):
    phrase = rl.result("store", "STORED", warnings=["TMP_LEFTOVER:runlog: output failure; outcome unknown"],
                       task_id=TASK, record_id="a" * 64, file_sha256="b" * 64, final_file_created=True)
    out = ev.canonical_json(phrase).encode("utf-8") + b"\n"
    assert phrase["exit_code"] == 1 and accept(out, b"", 1) is not None


FOUND_OK = rl.result("show", "FOUND", file_sha256="c" * 64, evidence=json.loads(RAW), task_id=TASK,
                     record_id="d" * 64)
STORED_OK = rl.result("store", "STORED", file_sha256="c" * 64, final_file_created=True, task_id=TASK,
                      record_id="d" * 64)
ERROR_OK = rl.result("show", "NOT_FOUND", error={"code": "NOT_FOUND", "detail": "no such record"}, task_id=TASK,
                     record_id="d" * 64)


def test_caller_rule_accepts_the_valid_examples():
    for obj in (FOUND_OK, STORED_OK, ERROR_OK):
        assert accept(ev.canonical_json(obj).encode("utf-8") + b"\n", b"", obj["exit_code"]) is not None


@pytest.mark.parametrize("base, change", [
    (FOUND_OK, {"exit_code": True}),
    (FOUND_OK, {"status": "OK"}),
    (FOUND_OK, {"command": "list"}),
    (FOUND_OK, {"authority": "ALL"}),
    (FOUND_OK, {"schema": "moneylab.runlog.result/2"}),
    (FOUND_OK, {"evidence": None}),
    (FOUND_OK, {"evidence": {**json.loads(RAW), "exit_code": 1}}),
    (FOUND_OK, {"final_file_created": False}),
    (FOUND_OK, {"file_sha256": "XYZ"}),
    (FOUND_OK, {"record_id": "D" * 64}),
    (FOUND_OK, {"task_id": "lower"}),
    (FOUND_OK, {"warnings": "TMP_LEFTOVER:x"}),
    (FOUND_OK, {"warnings": ["x"]}),
    (FOUND_OK, {"error": {"code": "NOT_FOUND", "detail": "x"}}),
    (STORED_OK, {"evidence": json.loads(RAW)}),
    (STORED_OK, {"final_file_created": False}),
    (STORED_OK, {"final_file_created": 1}),
    (STORED_OK, {"command": "show"}),
    (STORED_OK, {"record_id": None}),
    (ERROR_OK, {"exit_code": 0}),
    (ERROR_OK, {"error": None}),
    (ERROR_OK, {"error": {"code": "RECORD_CORRUPT", "detail": "x"}}),
    (ERROR_OK, {"error": {"code": "NOT_FOUND"}}),
    (ERROR_OK, {"status": "UNKNOWN", "error": {"code": "UNKNOWN", "detail": "x"}}),
    (ERROR_OK, {"evidence": json.loads(RAW)}),
])
def test_caller_rule_refuses_complete_json_that_breaks_the_schema(base, change):
    obj = {**base, **change}
    out = ev.canonical_json(obj).encode("utf-8") + b"\n"
    code = obj["exit_code"] if type(obj["exit_code"]) is int else 0
    assert accept(out, b"", code) is None


def test_exit_two_defined_error_differs_from_unknown(repo, capsys, monkeypatch):
    defined = run_captured(capsys, repo, ["show", "--task-id", TASK, "--record-id", "e" * 64])
    assert defined[2] == 2 and accept(*defined) is not None

    def broken(root, task_id, record_id):
        raise RuntimeError("canary_unknown_xyz")

    monkeypatch.setattr(rl, "show_at", broken)
    unknown = run_captured(capsys, repo, ["show", "--task-id", TASK, "--record-id", "e" * 64])
    assert unknown[2] == 2 and unknown[0] == b"" and accept(*unknown) is None


def test_entry_point_bad_evidence_writes_nothing():
    task = "RUNLOG-ENTRY-POINT-PROBE"
    target = PACKAGE_ROOT / "data" / "processed" / "runlog" / task
    assert not target.exists()
    proc = entry(["store", "--task-id", task], b'{"schema":"x"}')
    result = json.loads(proc.stdout)
    assert proc.returncode == 2 and proc.stderr == b""
    assert result["status"] == "INPUT_INVALID" and result["record_id"] is None
    assert not target.exists()
