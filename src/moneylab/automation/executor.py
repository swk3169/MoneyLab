"""Run one registered action once and return its evidence (AUTO-01, D1/D3).

Public API: `run_action(action_id: str) -> str`. The return value is a `moneylab.automation.evidence/1` canonical
JSON string; nothing is printed or written. An unregistered action is DENIED without starting a process, and the
DENIED evidence does not contain the caller's input.

The child runs with a fixed argv list, `shell=False`, a fixed cwd and an allowlisted environment. Two reader threads
read stdout and stderr in chunks at the same time; under one lock they check and add to a shared byte count, and a
chunk that would push the total over 1 MiB is dropped and ends the run as OUTPUT_LIMIT_EXCEEDED.

Time budget (D3 as replaced by ERRATA-001):
- Run limit: 60 s on the monotonic clock from process start. A child still running then is TIMEOUT.
- A child that exits within 60 s has its remaining output drained within the same deadline; if the readers are not
  done by then the result is AutomationError, not TIMEOUT.
- After TIMEOUT or OUTPUT_LIMIT_EXCEEDED: kill the direct child, wait up to REAP_SECONDS (10 s), then join both
  readers within REAP_SECONDS (10 s together). If the wait fails, one more kill and wait (up to 10 s) is tried for
  cleanup before AutomationError. This budget is outside the run limit: run_action may take about 80 s at worst.
- kill targets the direct child only; the process tree is not guaranteed to end.
Any reap or join failure raises AutomationError and no evidence is produced (never a success); the caller stops.
No retries, one run at a time."""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from moneylab.automation import evidence, policy
from moneylab.automation.policy import AutomationError

CHUNK_SIZE = 65_536
POLL_SECONDS = 0.05
REAP_SECONDS = 10.0  # after kill: wait for the process, then for each reader

_RUN_LOCK = threading.Lock()


@dataclass(frozen=True)
class RunResult:
    status: str
    exit_code: int | None
    duration_ms: int
    stdout: bytes
    stderr: bytes


class _Capture:
    """Shared, locked byte budget for both streams."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.total = 0
        self.lock = threading.Lock()
        self.exceeded = threading.Event()
        self.data = {"stdout": bytearray(), "stderr": bytearray()}
        self.errors: list[BaseException] = []

    def add(self, name: str, chunk: bytes) -> bool:
        """Keep chunk if it fits; otherwise drop it, mark the overflow and return False."""
        with self.lock:
            if self.exceeded.is_set():
                return False
            if self.total + len(chunk) > self.limit:
                self.exceeded.set()
                return False
            self.data[name] += chunk
            self.total += len(chunk)
            return True


def _read(stream: IO[bytes], name: str, capture: _Capture) -> None:
    try:
        while True:
            chunk = stream.read1(CHUNK_SIZE)  # type: ignore[attr-defined]  # BufferedReader on a pipe
            if not chunk or not capture.add(name, chunk):
                return
    except BaseException as exc:  # noqa: BLE001 - reported by the caller, never swallowed into a success
        with capture.lock:
            capture.errors.append(exc)


def _join(threads: list[threading.Thread], deadline: float) -> None:
    for t in threads:
        t.join(max(0.0, deadline - time.monotonic()))
    alive = [t.name for t in threads if t.is_alive()]
    if alive:
        raise AutomationError(f"reader threads still running: {alive}")


def _kill_and_reap(proc: subprocess.Popen[bytes], threads: list[threading.Thread]) -> None:
    try:
        proc.kill()
    except OSError:
        pass  # already gone; wait() below decides
    try:
        proc.wait(timeout=REAP_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise AutomationError("process could not be reaped after kill") from exc
    _join(threads, time.monotonic() + REAP_SECONDS)


def _execute(argv: list[str], cwd: Path, env: dict[str, str], timeout: float = policy.TIMEOUT_SECONDS,
             limit: int = policy.OUTPUT_LIMIT_BYTES) -> RunResult:
    """Run argv once. Private: run_action passes only the fixed policy values."""
    capture = _Capture(limit)
    start = time.monotonic()
    deadline = start + timeout
    try:
        proc = subprocess.Popen(argv, shell=False, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, ValueError) as exc:
        raise AutomationError(f"process could not be started: {type(exc).__name__}") from exc
    try:
        assert proc.stdout is not None and proc.stderr is not None
        threads = [threading.Thread(target=_read, args=(proc.stdout, "stdout", capture), name="stdout", daemon=True),
                   threading.Thread(target=_read, args=(proc.stderr, "stderr", capture), name="stderr", daemon=True)]
        for t in threads:
            t.start()
        stopped: str | None = None
        while True:
            if capture.exceeded.is_set():
                stopped = policy.OUTPUT_LIMIT_EXCEEDED
                break
            if proc.poll() is not None:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                stopped = policy.TIMEOUT
                break
            capture.exceeded.wait(min(POLL_SECONDS, remaining))
        if stopped is not None:
            _kill_and_reap(proc, threads)
        else:
            _join(threads, deadline)  # drain what the process wrote before it exited, within the deadline
            if capture.exceeded.is_set():
                stopped = policy.OUTPUT_LIMIT_EXCEEDED
    finally:
        if proc.poll() is None:  # only when an error is propagating: try not to leave the child running
            try:
                proc.kill()
                proc.wait(timeout=REAP_SECONDS)
            except (OSError, subprocess.TimeoutExpired):
                pass  # the error already propagating is the report; this is never a success
        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()
    if capture.errors:
        raise AutomationError(f"output reader failed: {type(capture.errors[0]).__name__}")
    duration_ms = int((time.monotonic() - start) * 1000)
    stdout, stderr = bytes(capture.data["stdout"]), bytes(capture.data["stderr"])
    if stopped is not None:
        return RunResult(stopped, None, duration_ms, stdout, stderr)
    code = proc.returncode
    if type(code) is not int:
        raise AutomationError("process finished without an int exit code")
    return RunResult(policy.status_for_exit_code(code), code, duration_ms, stdout, stderr)


def run_action(action_id: str) -> str:
    """Decide, run once if allowed, and return canonical evidence JSON. Raises AutomationError instead of
    reporting a run it could not set up, reap or describe."""
    if policy.decide(action_id) != policy.ALLOW:
        return evidence.denied()
    if not _RUN_LOCK.acquire(blocking=False):
        raise AutomationError("another action is already running")
    try:
        root = policy.repo_root()
        result = _execute(policy.build_argv(root), root, policy.build_env())
    finally:
        _RUN_LOCK.release()
    return evidence.executed(action_id, result.status, result.exit_code, result.duration_ms, result.stdout,
                             result.stderr)
