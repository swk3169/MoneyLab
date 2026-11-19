"""Decision logic of the run watcher (RUNWATCH-01 D4–D13).

All operating-system calls go through the Platform protocol, so every decision path can be tested with
fakes. The real Windows implementation is moneylab.runwatch.winjob.WinPlatform.
"""

from __future__ import annotations

import json
import os
import stat
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, TextIO

from moneylab.core.redaction import redact_text
from moneylab.storage import atomic

STATE_SCHEMA = "moneylab.runwatch.state/1"
FINAL_SCHEMA = "moneylab.runwatch.final/1"
STATE_FILE = "watch_state.json"
FINAL_FILE = "watch_final.json"
STDOUT_FILE = "child_stdout.bin"
STDERR_FILE = "child_stderr.bin"
LEFTOVER_SETTLE_SECONDS = 1.0
STEP_SECONDS = 0.05

EXIT_CODES: dict[str, int] = {
    "COMPLETED": 0,
    "CHILD_EXIT_NONZERO": 10,
    "COMPLETED_WITH_LEFTOVER": 11,
    "ABORT_TIME": 20,
    "ABORT_MEMORY": 21,
    "ABORT_MONITOR_FAILURE": 22,
    "ABORT_STATE_WRITE_FAILURE": 23,
    "ARGUMENT_REJECTED": 29,
    "START_REFUSED": 30,
    "START_PATH_REJECTED": 31,
    "JOB_SETUP_FAILED": 32,
    "CHILD_START_FAILED": 33,
    "ASSIGN_FAILED": 34,
    "ASSIGN_UNCONFIRMED": 35,
    "RESUME_FAILED": 36,
    "FINAL_WRITE_FAILURE": 40,
    "TERMINATION_UNVERIFIED": 50,
    "UNSUPPORTED_PLATFORM": 60,
    "INTERNAL_ERROR": 70,
}


class Rejected(Exception):
    """A start condition that ends the watcher before any child exists. `reason` is an EXIT_CODES key."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Config:
    watch_dir: Path
    max_seconds: int
    start_min_available_bytes: int
    abort_below_available_bytes: int
    poll_seconds: int
    verify_seconds: int
    argv: tuple[str, ...]
    cwd: Path
    forbid_under: tuple[Path, ...] = ()


class Platform(Protocol):
    """Operating-system calls. Every method raises an exception on failure."""

    def available_memory(self) -> int: ...
    def create_job(self) -> Any: ...
    def start_suspended(self, argv: tuple[str, ...], cwd: Path, stdout_path: Path, stderr_path: Path) -> Any: ...
    def child_pid(self, child: Any) -> int: ...
    def assign(self, job: Any, child: Any) -> None: ...
    def in_job(self, job: Any, child: Any) -> bool: ...
    def resume(self, child: Any) -> None: ...
    def wait_child(self, child: Any, seconds: float) -> bool: ...
    def exit_code(self, child: Any) -> int: ...
    def job_active(self, job: Any) -> int: ...
    def job_peak_commit(self, job: Any) -> int: ...
    def terminate_job(self, job: Any) -> None: ...
    def terminate_child(self, child: Any) -> None: ...
    def close_thread(self, child: Any) -> None: ...
    def close_child(self, child: Any) -> None: ...
    def close_job(self, job: Any) -> None: ...


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate(cfg: Config) -> None:
    """D1 argument rules. Violations raise Rejected("ARGUMENT_REJECTED") before anything is created."""
    for value in (cfg.max_seconds, cfg.poll_seconds, cfg.verify_seconds):
        if not _is_int(value) or value <= 0:
            raise Rejected("ARGUMENT_REJECTED")
    for value in (cfg.start_min_available_bytes, cfg.abort_below_available_bytes):
        if not _is_int(value) or value < 0:
            raise Rejected("ARGUMENT_REJECTED")
    if cfg.start_min_available_bytes < cfg.abort_below_available_bytes:
        raise Rejected("ARGUMENT_REJECTED")
    if not cfg.argv or not all(isinstance(a, str) and a for a in cfg.argv):
        raise Rejected("ARGUMENT_REJECTED")


def is_reparse_point(path: Path) -> bool:
    st = os.lstat(path)
    attrs = getattr(st, "st_file_attributes", 0)
    return bool(attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT) or stat.S_ISLNK(st.st_mode)


def _norm(path: Path) -> Path:
    return Path(os.path.normcase(os.path.abspath(path)))


def prepare_watch_dir(cfg: Config, is_reparse: Callable[[Path], bool] = is_reparse_point) -> Path:
    """D8: reject an existing watch-dir, reparse points or links among its existing ancestors, and nesting with
    a --forbid-under path; then create the watch-dir exclusively with os.mkdir. Only paths passed with
    --forbid-under are checked. The check-then-use race is not fully prevented."""
    watch = Path(os.path.abspath(cfg.watch_dir))
    if os.path.lexists(watch):
        raise Rejected("START_PATH_REJECTED")
    try:
        for parent in watch.parents:
            if os.path.lexists(parent) and is_reparse(parent):
                raise Rejected("START_PATH_REJECTED")
    except OSError as exc:
        raise Rejected("START_PATH_REJECTED") from exc
    w = _norm(watch)
    for forbidden in cfg.forbid_under:
        f = _norm(forbidden)
        if w == f or f in w.parents or w in f.parents:
            raise Rejected("START_PATH_REJECTED")
    try:
        os.mkdir(watch)
    except OSError as exc:
        raise Rejected("START_PATH_REJECTED") from exc
    return watch


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _dumps(obj: dict[str, Any]) -> bytes:
    return (json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=True) + "\n").encode("ascii")


class _Supervisor:
    def __init__(self, cfg: Config, watch: Path, platform: Platform, clock: Callable[[], float],
                 sleep: Callable[[float], None], utcnow: Callable[[], str],
                 write_state: Callable[[Path, bytes], object], write_final: Callable[[Path, bytes], object]) -> None:
        self.cfg, self.watch, self.platform = cfg, watch, platform
        self.clock, self.sleep, self.utcnow = clock, sleep, utcnow
        self.write_state, self.write_final = write_state, write_final
        self.job: Any = None
        self.child: Any = None
        self.thread_open = False
        self.child_pid: int | None = None
        self.child_code: int | None = None
        self.termination = "NOT_APPLICABLE"
        self.min_available: int | None = None
        self.peak_commit: int | None = None
        self.started = utcnow()
        self.t0 = clock()

    def _observe(self, available: int | None = None, peak: int | None = None) -> None:
        if available is not None:
            self.min_available = available if self.min_available is None else min(self.min_available, available)
        if peak is not None:
            self.peak_commit = peak if self.peak_commit is None else max(self.peak_commit, peak)

    def _close_thread(self) -> None:
        if self.thread_open:
            self.thread_open = False
            try:
                self.platform.close_thread(self.child)
            except Exception:
                pass

    def _verify(self, with_job: bool) -> None:
        """D6: within verify-seconds, the child handle is signaled and (with_job) the job has no active process."""
        deadline = self.clock() + self.cfg.verify_seconds
        while True:
            try:
                exited = self.platform.wait_child(self.child, 0)
                active = self.platform.job_active(self.job) if with_job else 0
            except Exception:
                exited, active = False, -1
            if exited and active == 0:
                self.termination = "VERIFIED"
                return
            if self.clock() >= deadline:
                self.termination = "UNVERIFIED"
                return
            self.sleep(STEP_SECONDS)

    def _abort_job(self) -> None:
        try:
            self.platform.terminate_job(self.job)
        except Exception:
            pass
        self._verify(with_job=True)

    def _kill_unassigned(self) -> None:
        """S3·S4: the child is not (confirmed) in the job; terminate it through its own handle."""
        try:
            self.platform.terminate_child(self.child)
        except Exception:
            pass
        self._close_thread()
        self._verify(with_job=False)

    def _start(self) -> str:
        try:
            available = self.platform.available_memory()
        except Exception:
            return "ABORT_MONITOR_FAILURE"
        self._observe(available=available)
        if available < self.cfg.start_min_available_bytes:
            return "START_REFUSED"
        try:
            self.job = self.platform.create_job()
        except Exception:
            return "JOB_SETUP_FAILED"
        try:
            self.child = self.platform.start_suspended(self.cfg.argv, self.cfg.cwd, self.watch / STDOUT_FILE,
                                                       self.watch / STDERR_FILE)
        except Exception:
            return "CHILD_START_FAILED"
        self.thread_open = True
        self.child_pid = self.platform.child_pid(self.child)
        try:
            self.platform.assign(self.job, self.child)
        except Exception:
            self._kill_unassigned()
            return "ASSIGN_FAILED"
        try:
            confirmed = self.platform.in_job(self.job, self.child)
        except Exception:
            confirmed = False
        if not confirmed:
            self._kill_unassigned()
            return "ASSIGN_UNCONFIRMED"
        try:
            self.platform.resume(self.child)
        except Exception:
            self._close_thread()
            self._abort_job()
            return "RESUME_FAILED"
        self._close_thread()
        return self._watch_loop()

    def _state(self, elapsed: float, available: int, active: int) -> bytes:
        return _dumps({"schema": STATE_SCHEMA, "utc": self.utcnow(), "elapsed_seconds": round(elapsed, 3),
                       "available_bytes": available, "min_available_bytes": self.min_available,
                       "job_active_processes": active, "peak_job_commit_bytes": self.peak_commit,
                       "child_pid": self.child_pid})

    def _watch_loop(self) -> str:
        """D5 order: root exit, time, query failure, memory, state write."""
        while True:
            if self.platform.wait_child(self.child, 0):
                return self._completed()
            elapsed = self.clock() - self.t0
            if elapsed >= self.cfg.max_seconds:
                self._abort_job()
                return "ABORT_TIME"
            try:
                available = self.platform.available_memory()
                active = self.platform.job_active(self.job)
                peak = self.platform.job_peak_commit(self.job)
            except Exception:
                self._abort_job()
                return "ABORT_MONITOR_FAILURE"
            self._observe(available=available, peak=peak)
            if available < self.cfg.abort_below_available_bytes:
                self._abort_job()
                return "ABORT_MEMORY"
            try:
                self.write_state(self.watch / STATE_FILE, self._state(elapsed, available, active))
            except Exception:
                self._abort_job()
                return "ABORT_STATE_WRITE_FAILURE"
            self.platform.wait_child(self.child, min(self.cfg.poll_seconds, self.cfg.max_seconds - elapsed))

    def _completed(self) -> str:
        code = self.platform.exit_code(self.child)
        self.child_code = code
        try:
            self._observe(peak=self.platform.job_peak_commit(self.job))
        except Exception:
            pass
        settle = self.clock() + LEFTOVER_SETTLE_SECONDS
        while self.platform.job_active(self.job) > 0 and self.clock() < settle:
            self.sleep(STEP_SECONDS)
        if self.platform.job_active(self.job) > 0:
            self._abort_job()
            return "COMPLETED_WITH_LEFTOVER" if code == 0 else "CHILD_EXIT_NONZERO"
        self.termination = "VERIFIED"
        return "COMPLETED" if code == 0 else "CHILD_EXIT_NONZERO"

    def _final(self, reason: str, code: int) -> bytes:
        return _dumps({"schema": FINAL_SCHEMA, "reason": reason, "watcher_exit_code": code,
                       "child_exit_code": self.child_code, "child_pid": self.child_pid,
                       "termination": self.termination, "started_utc": self.started, "finished_utc": self.utcnow(),
                       "elapsed_seconds": round(self.clock() - self.t0, 3),
                       "min_available_bytes": self.min_available, "peak_job_commit_bytes": self.peak_commit,
                       "argv": [redact_text(a) for a in self.cfg.argv], "cwd": str(self.cfg.cwd),
                       "limits": {"max_seconds": self.cfg.max_seconds, "poll_seconds": self.cfg.poll_seconds,
                                  "verify_seconds": self.cfg.verify_seconds,
                                  "start_min_available_bytes": self.cfg.start_min_available_bytes,
                                  "abort_below_available_bytes": self.cfg.abort_below_available_bytes}})

    def execute(self, err: TextIO) -> int:
        try:
            reason = self._start()
        except Exception:
            reason = "INTERNAL_ERROR"
            if self.job is not None and self.child is not None:
                self._close_thread()
                self._abort_job()
        if self.child is not None:
            self._close_thread()
            try:
                self.platform.close_child(self.child)
            except Exception:
                pass
        code = EXIT_CODES["TERMINATION_UNVERIFIED"] if self.termination == "UNVERIFIED" else EXIT_CODES[reason]
        final_failed = False
        try:
            self.write_final(self.watch / FINAL_FILE, self._final(reason, code))
        except Exception:
            final_failed = True
        if self.job is not None:
            try:
                self.platform.close_job(self.job)
            except Exception:
                pass
        if final_failed:
            err.write("FINAL_WRITE_FAILURE\n")
            if code != EXIT_CODES["TERMINATION_UNVERIFIED"]:
                code = EXIT_CODES["FINAL_WRITE_FAILURE"]
        return code


def supervise(cfg: Config, platform: Platform, *, clock: Callable[[], float] = time.monotonic,
              sleep: Callable[[float], None] = time.sleep, utcnow: Callable[[], str] = _utcnow,
              write_state: Callable[[Path, bytes], object] = atomic.atomic_write_bytes,
              write_final: Callable[[Path, bytes], object] = atomic.atomic_create_new_bytes,
              is_reparse: Callable[[Path], bool] = is_reparse_point, err: TextIO | None = None) -> int:
    """Run cfg.argv once under the watcher and return the watcher exit code (EXIT_CODES). No retry."""
    stream = sys.stderr if err is None else err
    try:
        validate(cfg)
        watch = prepare_watch_dir(cfg, is_reparse)
    except Rejected as exc:
        stream.write(exc.reason + "\n")
        return EXIT_CODES[exc.reason]
    return _Supervisor(cfg, watch, platform, clock, sleep, utcnow, write_state, write_final).execute(stream)
