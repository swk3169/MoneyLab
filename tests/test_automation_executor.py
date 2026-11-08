"""AUTO-01 executor: DENY without a process, fixed Popen call, exit-code mapping, timeout, 1 MiB output limit,
kill/wait/join (D1/D3). Fake Popen for the mapping; small real child processes for timeout and the limit."""

from __future__ import annotations

import hashlib
import inspect
import io
import json
import os
import subprocess
import sys
import threading
import time

import pytest

from moneylab.automation import executor, policy
from moneylab.automation.policy import AutomationError

LIMIT = policy.OUTPUT_LIMIT_BYTES
sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731


class FakePopen:
    """Stands in for subprocess.Popen; records each call."""

    calls: list[tuple[list[str], dict]] = []
    instances: list[FakePopen] = []
    stdout_bytes = b""
    stderr_bytes = b""
    exit_code: int | None = 0  # None: runs until killed
    wait_hangs = False

    def __init__(self, argv, **kwargs):
        type(self).calls.append((argv, kwargs))
        type(self).instances.append(self)
        self.stdout = io.BufferedReader(io.BytesIO(type(self).stdout_bytes))
        self.stderr = io.BufferedReader(io.BytesIO(type(self).stderr_bytes))
        self.returncode = None
        self.killed = False
        self.waited = False

    def poll(self):
        if self.returncode is None and not self.killed and type(self).exit_code is not None:
            self.returncode = type(self).exit_code
        return self.returncode

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        if type(self).wait_hangs:
            raise subprocess.TimeoutExpired("fake", timeout)
        if self.killed and self.returncode is None:
            self.returncode = 1
        self.waited = True
        return self.returncode


@pytest.fixture
def fake(monkeypatch):
    class Fake(FakePopen):
        calls = []
        instances = []

    monkeypatch.setattr(executor.subprocess, "Popen", Fake)
    return Fake


def _no_popen(*args, **kwargs):
    raise AssertionError("a subprocess was started for a denied action")


def _reader_threads():
    return [t for t in threading.enumerate() if t.name in ("stdout", "stderr") and t.is_alive()]


# D1: deny without a process

@pytest.mark.parametrize("action_id", ["", "supervisor_check", "knowledge_validate --full-history",
                                       "knowledge_validate; whoami", None, 0])
def test_denied_action_starts_no_process(monkeypatch, action_id):
    monkeypatch.setattr(executor.subprocess, "Popen", _no_popen)
    doc = json.loads(executor.run_action(action_id))
    assert doc["decision"] == "DENY" and doc["status"] == "DENIED"
    assert doc["action_id"] is None
    assert doc["exit_code"] is doc["duration_ms"] is doc["stdout_sha256"] is doc["stderr_sha256"] is None


@pytest.mark.parametrize("canary", ["MONEYLAB-CANARY-7f3a9c", "token=MONEYLAB-CANARY-7f3a9c",
                                    "knowledge_validate MONEYLAB-CANARY-7f3a9c", "MONEYLAB-CANARY-7f3a9c\n\"}"])
def test_denied_evidence_does_not_contain_the_callers_input(monkeypatch, canary):
    monkeypatch.setattr(executor.subprocess, "Popen", _no_popen)
    text = executor.run_action(canary)
    assert "CANARY" not in text and "7f3a9c" not in text and "token" not in text
    assert hashlib.sha256(canary.encode()).hexdigest() not in text
    assert text == executor.run_action("anything else")  # identical for every denied input


def test_run_action_takes_only_the_action_id():
    assert list(inspect.signature(executor.run_action).parameters) == ["action_id"]
    assert inspect.signature(executor.run_action).return_annotation in (str, "str")


def test_execute_defaults_are_the_policy_limits():
    params = inspect.signature(executor._execute).parameters
    assert params["timeout"].default == policy.TIMEOUT_SECONDS == 60.0
    assert params["limit"].default == policy.OUTPUT_LIMIT_BYTES == 1_048_576


# D2/D3: the fixed Popen call

def test_fixed_popen_call(fake):
    fake.stdout_bytes, fake.stderr_bytes, fake.exit_code = b'{"ok": true}\n', b"", 0
    doc = json.loads(executor.run_action("knowledge_validate"))
    (argv, kwargs), = fake.calls
    root = policy.repo_root()
    assert argv == [sys.executable, "-m", "moneylab.knowledge", "--root", str(root), "validate"]
    assert kwargs["shell"] is False
    assert kwargs["cwd"] == str(root)
    assert kwargs["env"] == policy.build_env()
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["stdout"] is subprocess.PIPE and kwargs["stderr"] is subprocess.PIPE
    assert set(kwargs) == {"shell", "cwd", "env", "stdin", "stdout", "stderr"}
    assert doc["status"] == "SUCCEEDED" and doc["exit_code"] == 0
    assert doc["stdout_sha256"] == sha(b'{"ok": true}\n') and doc["stderr_sha256"] == sha(b"")


@pytest.mark.parametrize("code, status", [(0, "SUCCEEDED"), (1, "VALIDATION_FAILED"), (3, "SOURCE_UNVERIFIED"),
                                          (2, "UNEXPECTED_EXIT"), (5, "UNEXPECTED_EXIT"), (-1, "UNEXPECTED_EXIT")])
def test_exit_code_mapping_with_fake_popen(fake, code, status):
    fake.stdout_bytes, fake.stderr_bytes, fake.exit_code = b"out", b"err", code
    doc = json.loads(executor.run_action("knowledge_validate"))
    assert (doc["decision"], doc["status"], doc["exit_code"]) == ("ALLOW", status, code)
    assert doc["stdout_sha256"] == sha(b"out") and doc["stderr_sha256"] == sha(b"err")
    assert type(doc["duration_ms"]) is int and doc["duration_ms"] >= 0
    assert len(fake.calls) == 1  # no retry


def test_timeout_with_fake_popen(fake):
    fake.stdout_bytes, fake.exit_code = b"partial", None
    root = policy.repo_root()
    result = executor._execute(policy.build_argv(root), root, policy.build_env(), timeout=0.2)
    assert result.status == "TIMEOUT" and result.exit_code is None and result.stdout == b"partial"
    (proc,) = fake.instances
    assert proc.killed and proc.waited
    assert _reader_threads() == []


def test_output_limit_with_fake_popen(fake):
    fake.stdout_bytes, fake.stderr_bytes, fake.exit_code = b"o" * LIMIT, b"e" * 10, 0
    doc = json.loads(executor.run_action("knowledge_validate"))
    assert doc["status"] == "OUTPUT_LIMIT_EXCEEDED" and doc["exit_code"] is None


def test_exactly_the_limit_is_allowed(fake):
    fake.stdout_bytes, fake.stderr_bytes, fake.exit_code = b"o" * (LIMIT - 10), b"e" * 10, 0
    doc = json.loads(executor.run_action("knowledge_validate"))
    assert doc["status"] == "SUCCEEDED"
    assert doc["stdout_sha256"] == sha(b"o" * (LIMIT - 10)) and doc["stderr_sha256"] == sha(b"e" * 10)


def test_unreaped_process_is_not_a_success(fake):
    fake.exit_code, fake.wait_hangs = None, True
    root = policy.repo_root()
    with pytest.raises(AutomationError, match="reaped"):
        executor._execute(policy.build_argv(root), root, policy.build_env(), timeout=0.1)


class BlockingStream:
    """A pipe whose reader never sees EOF until released: models output that cannot be drained."""

    def __init__(self):
        self.release = threading.Event()

    def read1(self, size):
        self.release.wait(30)
        return b""

    def close(self):
        pass  # closing does not wake the reader, like a pipe still held open elsewhere


@pytest.fixture
def blocking(monkeypatch):
    """Fake Popen whose stdout blocks; executed evidence is a tripwire (no success may be produced)."""
    streams = []

    class Fake(FakePopen):
        calls = []
        instances = []

        def __init__(self, argv, **kwargs):
            super().__init__(argv, **kwargs)
            self.stdout = BlockingStream()
            streams.append(self.stdout)

    def no_evidence(*args, **kwargs):
        raise AssertionError("evidence was produced for a run that could not be reaped")

    monkeypatch.setattr(executor.subprocess, "Popen", Fake)
    monkeypatch.setattr(executor.evidence, "executed", no_evidence)
    monkeypatch.setattr(executor, "REAP_SECONDS", 0.3)
    yield Fake
    for s in streams:
        s.release.set()


def test_join_failure_after_kill_is_an_error_without_evidence(blocking, monkeypatch):
    blocking.exit_code = None  # runs until killed -> TIMEOUT -> kill, wait ok, join fails
    monkeypatch.setattr(executor._execute, "__defaults__", (0.2, LIMIT))
    t0 = time.monotonic()
    with pytest.raises(AutomationError, match="reader threads still running"):
        executor.run_action("knowledge_validate")
    (proc,) = blocking.instances
    assert proc.killed and proc.waited
    assert time.monotonic() - t0 < 5
    assert not executor._RUN_LOCK.locked()


def test_drain_not_finished_by_the_deadline_is_an_error_not_timeout(blocking, monkeypatch):
    blocking.exit_code = 0  # exits at once, but its output cannot be drained before the deadline
    monkeypatch.setattr(executor._execute, "__defaults__", (0.3, LIMIT))
    t0 = time.monotonic()
    with pytest.raises(AutomationError, match="reader threads still running"):
        executor.run_action("knowledge_validate")
    (proc,) = blocking.instances
    assert not proc.killed and proc.returncode == 0  # normal exit path, no kill: not reported as TIMEOUT
    assert time.monotonic() - t0 < 5


def test_reap_failure_is_an_error_without_evidence(blocking, monkeypatch):
    blocking.exit_code, blocking.wait_hangs = None, True
    monkeypatch.setattr(executor._execute, "__defaults__", (0.1, LIMIT))
    with pytest.raises(AutomationError, match="reaped"):
        executor.run_action("knowledge_validate")
    assert not executor._RUN_LOCK.locked()


def test_reap_budget_constants():
    assert executor.REAP_SECONDS == 10.0
    assert policy.TIMEOUT_SECONDS == 60.0


def test_start_failure_is_not_a_success(monkeypatch):
    def broken(*args, **kwargs):
        raise FileNotFoundError("no interpreter")

    monkeypatch.setattr(executor.subprocess, "Popen", broken)
    with pytest.raises(AutomationError, match="started"):
        executor.run_action("knowledge_validate")


def test_one_run_at_a_time(fake):
    assert executor._RUN_LOCK.acquire(blocking=False)
    try:
        with pytest.raises(AutomationError, match="already running"):
            executor.run_action("knowledge_validate")
    finally:
        executor._RUN_LOCK.release()
    assert fake.calls == []
    json.loads(executor.run_action("knowledge_validate"))  # the lock is released afterwards


def test_capture_never_stores_an_overflowing_chunk():
    cap = executor._Capture(10)
    assert cap.add("stdout", b"12345") and cap.add("stderr", b"12345")
    assert not cap.add("stdout", b"x")
    assert not cap.add("stderr", b"")  # after overflow nothing more is taken
    assert cap.total == 10 and bytes(cap.data["stdout"]) == b"12345" and cap.exceeded.is_set()


def test_capture_lock_serialises_both_readers():
    cap = executor._Capture(1000)
    barrier = threading.Barrier(8)

    def worker(name):
        barrier.wait()
        while cap.add(name, b"x" * 7):
            pass

    threads = [threading.Thread(target=worker, args=("stdout" if i % 2 else "stderr",)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert cap.exceeded.is_set()
    assert cap.total == len(cap.data["stdout"]) + len(cap.data["stderr"]) <= 1000
    assert cap.total == 1000 - 1000 % 7


# Limited real child processes (the policy environment, a short `python -c`, never the shell)

def _child(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def _run_real(code, monkeypatch, **kw):
    started = []
    real = subprocess.Popen

    def spy(*args, **kwargs):
        proc = real(*args, **kwargs)
        started.append(proc)
        return proc

    monkeypatch.setattr(executor.subprocess, "Popen", spy)
    t0 = time.monotonic()
    result = executor._execute(_child(code), policy.repo_root(), policy.build_env(), **kw)
    return result, started, time.monotonic() - t0


@pytest.mark.parametrize("code, status", [(0, "SUCCEEDED"), (1, "VALIDATION_FAILED"), (3, "SOURCE_UNVERIFIED"),
                                          (2, "UNEXPECTED_EXIT"), (7, "UNEXPECTED_EXIT")])
def test_real_child_exit_codes(monkeypatch, code, status):
    result, (proc,), _ = _run_real(f"import sys; sys.stdout.write('hi'); sys.exit({code})", monkeypatch)
    assert (result.status, result.exit_code, result.stdout, result.stderr) == (status, code, b"hi", b"")
    assert proc.returncode == code


def test_real_child_timeout_kills_and_reaps(monkeypatch):
    result, (proc,), elapsed = _run_real("import sys, time\nsys.stdout.write('a'); sys.stdout.flush()\n"
                                         "time.sleep(60)", monkeypatch, timeout=1.0)
    assert result.status == "TIMEOUT" and result.exit_code is None
    assert result.stdout == b"a" and result.stderr == b""
    assert proc.returncode is not None and elapsed < 20
    assert _reader_threads() == []


WRITER = ("import sys, threading\n"
          "def w(s):\n"
          "    while True:\n"
          "        s.write(b'z' * 4096); s.flush()\n"
          "threading.Thread(target=w, args=(sys.stderr.buffer,), daemon=True).start()\n"
          "w(sys.stdout.buffer)\n")


def test_real_endless_output_on_both_streams_is_stopped_during_execution(monkeypatch):
    result, (proc,), elapsed = _run_real(WRITER, monkeypatch, timeout=30.0)
    assert result.status == "OUTPUT_LIMIT_EXCEEDED" and result.exit_code is None
    kept = len(result.stdout) + len(result.stderr)
    assert 0 < kept <= LIMIT and result.stdout and result.stderr  # both streams were read concurrently
    assert set(result.stdout) == {ord("z")} and set(result.stderr) == {ord("z")}
    assert proc.returncode is not None  # killed and reaped
    assert elapsed < 30  # stopped by the limit, not by the timeout
    assert _reader_threads() == []


def test_real_output_just_over_the_limit_after_exit(monkeypatch):
    code = (f"import sys\nsys.stdout.buffer.write(b'a' * {LIMIT // 2})\n"
            f"sys.stderr.buffer.write(b'b' * {LIMIT // 2 + 1})\n")
    result, (proc,), _ = _run_real(code, monkeypatch)
    assert result.status == "OUTPUT_LIMIT_EXCEEDED" and result.exit_code is None
    assert len(result.stdout) + len(result.stderr) <= LIMIT
    assert proc.returncode is not None and _reader_threads() == []


def test_real_output_under_the_limit_is_hashed_exactly(monkeypatch):
    code = ("import sys\nfor i in range(40):\n"
            "    sys.stdout.buffer.write(b'o' * 10000); sys.stdout.flush()\n"
            "    sys.stderr.buffer.write(b'e' * 10000); sys.stderr.flush()\n")
    result, _, _ = _run_real(code, monkeypatch)
    assert result.status == "SUCCEEDED" and result.exit_code == 0
    assert result.stdout == b"o" * 400_000 and result.stderr == b"e" * 400_000


# On POSIX a child interpreter started without LC_ALL/LANG/LC_CTYPE coerces the C locale (PEP 538) and sets
# LC_CTYPE in its own environment, to one of these values. That variable is added by the child at start-up,
# not passed by the executor; nothing else may appear.
POSIX_RUNTIME_ADDED = {"LC_CTYPE": {"C.UTF-8", "C.utf8", "UTF-8"}}


def test_real_child_sees_only_the_allowlisted_environment(monkeypatch):
    monkeypatch.setenv("MONEYLAB_AUTO01_CANARY", "secret-looking-value")
    passed: list[dict[str, str]] = []
    real = subprocess.Popen

    def record(*args, **kwargs):  # what the executor hands to Popen, before the child can change anything
        passed.append(dict(kwargs["env"]))
        return real(*args, **kwargs)

    monkeypatch.setattr(executor.subprocess, "Popen", record)
    code = "import os, sys, json; sys.stdout.write(json.dumps(dict(os.environ)))"
    result, _, _ = _run_real(code, monkeypatch)  # _run_real's spy wraps record
    assert result.status == "SUCCEEDED"
    # 1. passed by the executor: exactly the allowlist, no canary
    (env,) = passed
    assert env == policy.build_env()
    assert "MONEYLAB_AUTO01_CANARY" not in {k.upper() for k in env}
    # 2. seen by the child: the passed variables, plus on POSIX only the interpreter's own locale coercion
    seen = json.loads(result.stdout)
    assert "MONEYLAB_AUTO01_CANARY" not in {k.upper() for k in seen}
    assert "secret-looking-value" not in seen.values()
    passed_upper = {k.upper() for k in env}
    extra = {k: v for k, v in seen.items() if k.upper() not in passed_upper}
    if os.name == "nt":
        assert extra == {}
    else:
        assert set(extra) <= set(POSIX_RUNTIME_ADDED), extra
        for name, value in extra.items():
            assert value in POSIX_RUNTIME_ADDED[name], (name, value)
    for name, value in env.items():
        assert seen.get(name) == value  # passed values arrive unchanged


def test_posix_runtime_allowance_is_narrow():
    """The POSIX allowance is one locale variable with fixed values: it cannot admit a leaked variable."""
    assert POSIX_RUNTIME_ADDED == {"LC_CTYPE": {"C.UTF-8", "C.utf8", "UTF-8"}}
    assert not set(POSIX_RUNTIME_ADDED) & {k.upper() for k in policy.build_env()}
