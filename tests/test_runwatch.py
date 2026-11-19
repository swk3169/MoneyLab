"""RUNWATCH-01 tests. Synthetic work only: no research module is imported or run, memory is never exhausted.

Unit tests drive moneylab.runwatch.watch with a fake platform, a fake clock and injected writers (memory abort
and start refusal are condition injection). Windows integration tests (W1a·W1b·W2–W6) run the real CLI with
real job objects and short synthetic processes; each synthetic process ends by itself within 60 seconds once it
runs. Cleanup touches only processes the test itself created and holds a handle to (CLEANUP_EXCEPTION).
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from moneylab.runwatch import watch as W
from moneylab.runwatch.__main__ import _ArgumentError, parse

GiB = 1 << 30


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakePlatform:
    """Deterministic stand-in. Times are fake-clock seconds."""

    def __init__(self, clock: Clock, *, exit_at: float | None = None, code: int = 0,
                 leftover_until: float | None = None, available=lambda t: 16 * GiB, fail: tuple[str, ...] = (),
                 in_job: bool = True, terminate_works: bool = True) -> None:
        self.clock, self.exit_at, self.code = clock, exit_at, code
        self.leftover_until, self.available, self.fail = leftover_until, available, set(fail)
        self.in_job_result, self.terminate_works = in_job, terminate_works
        self.started = False
        self.terminated_job = False
        self.terminated_child = False
        self.calls: list[str] = []

    def _check(self, name: str) -> None:
        self.calls.append(name)
        if name in self.fail:
            raise OSError(f"injected {name}")

    def _killed(self) -> bool:
        return (self.terminated_job or self.terminated_child) and self.terminate_works

    def _exited(self) -> bool:
        return self._killed() or (self.exit_at is not None and self.clock.now >= self.exit_at)

    def available_memory(self) -> int:
        self._check("available_memory")
        return self.available(self.clock.now)

    def create_job(self) -> str:
        self._check("create_job")
        return "job"

    def start_suspended(self, argv, cwd, stdout_path, stderr_path) -> str:
        self._check("start_suspended")
        self.started = True
        return "child"

    def child_pid(self, child) -> int:
        return 4242

    def assign(self, job, child) -> None:
        self._check("assign")

    def in_job(self, job, child) -> bool:
        self._check("in_job")
        return self.in_job_result

    def resume(self, child) -> None:
        self._check("resume")

    def wait_child(self, child, seconds: float) -> bool:
        self._check("wait_child")
        if self._exited():
            return True
        if self.exit_at is not None and self.exit_at <= self.clock.now + seconds:
            self.clock.now = max(self.clock.now, self.exit_at)
            return True
        self.clock.now += seconds
        return False

    def exit_code(self, child) -> int:
        return 1 if self._killed() else self.code

    def job_active(self, job) -> int:
        self._check("job_active")
        if self.terminated_job:
            return 0 if self.terminate_works else 1
        if not self._exited():
            return 1
        return 1 if self.leftover_until is not None and self.clock.now < self.leftover_until else 0

    def job_peak_commit(self, job) -> int:
        self._check("job_peak_commit")
        return 123456

    def terminate_job(self, job) -> None:
        self.calls.append("terminate_job")
        self.terminated_job = True

    def terminate_child(self, child) -> None:
        self.calls.append("terminate_child")
        self.terminated_child = True

    def close_thread(self, child) -> None:
        self.calls.append("close_thread")

    def close_child(self, child) -> None:
        self.calls.append("close_child")

    def close_job(self, job) -> None:
        self.calls.append("close_job")


def make_cfg(tmp_path: Path, name: str = "w", **over) -> W.Config:
    base = dict(watch_dir=tmp_path / name, max_seconds=10, start_min_available_bytes=4 * GiB,
                abort_below_available_bytes=2 * GiB, poll_seconds=1, verify_seconds=5,
                argv=("C:/x/python.exe", "-c", "pass"), cwd=tmp_path, forbid_under=())
    base.update(over)
    return W.Config(**base)


def run_fake(tmp_path: Path, platform: FakePlatform, clock: Clock, cfg: W.Config | None = None, **kw):
    cfg = cfg or make_cfg(tmp_path)
    err = io.StringIO()
    code = W.supervise(cfg, platform, clock=clock, sleep=clock.sleep, utcnow=lambda: "T", err=err, **kw)
    final_path = cfg.watch_dir / W.FINAL_FILE
    final = json.loads(final_path.read_bytes()) if final_path.exists() else None
    return code, final, err.getvalue()


# --- unit: decision paths ------------------------------------------------------------------------------------------

def test_exit_code_table_is_fixed():
    assert W.EXIT_CODES == {"COMPLETED": 0, "CHILD_EXIT_NONZERO": 10, "COMPLETED_WITH_LEFTOVER": 11,
                            "ABORT_TIME": 20, "ABORT_MEMORY": 21, "ABORT_MONITOR_FAILURE": 22,
                            "ABORT_STATE_WRITE_FAILURE": 23, "ARGUMENT_REJECTED": 29, "START_REFUSED": 30,
                            "START_PATH_REJECTED": 31, "JOB_SETUP_FAILED": 32, "CHILD_START_FAILED": 33,
                            "ASSIGN_FAILED": 34, "ASSIGN_UNCONFIRMED": 35, "RESUME_FAILED": 36,
                            "FINAL_WRITE_FAILURE": 40, "TERMINATION_UNVERIFIED": 50, "UNSUPPORTED_PLATFORM": 60,
                            "INTERNAL_ERROR": 70}


def test_completed_and_record_fields(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, exit_at=3.5)
    code, final, _ = run_fake(tmp_path, p, clock)
    assert code == 0 and final["reason"] == "COMPLETED" and final["termination"] == "VERIFIED"
    assert final["child_exit_code"] == 0 and final["child_pid"] == 4242 and final["peak_job_commit_bytes"] == 123456
    assert set(final) == {"schema", "reason", "watcher_exit_code", "child_exit_code", "child_pid", "termination",
                          "started_utc", "finished_utc", "elapsed_seconds", "min_available_bytes",
                          "peak_job_commit_bytes", "argv", "cwd", "limits"}
    state = json.loads((tmp_path / "w" / W.STATE_FILE).read_bytes())
    assert set(state) == {"schema", "utc", "elapsed_seconds", "available_bytes", "min_available_bytes",
                          "job_active_processes", "peak_job_commit_bytes", "child_pid"}
    assert sorted(os.listdir(tmp_path / "w")) == [W.FINAL_FILE, W.STATE_FILE]
    assert p.calls.index("assign") < p.calls.index("in_job") < p.calls.index("resume")
    assert p.calls[-1] == "close_job" and "terminate_job" not in p.calls


def test_child_exit_nonzero(tmp_path):
    clock = Clock()
    code, final, _ = run_fake(tmp_path, FakePlatform(clock, exit_at=2, code=3), clock)
    assert code == 10 and final["child_exit_code"] == 3 and final["termination"] == "VERIFIED"


def test_leftover_is_terminated(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, exit_at=2, leftover_until=100)
    code, final, _ = run_fake(tmp_path, p, clock)
    assert code == 11 and final["reason"] == "COMPLETED_WITH_LEFTOVER" and "terminate_job" in p.calls
    assert final["termination"] == "VERIFIED"


def test_nonzero_with_leftover(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, exit_at=2, code=5, leftover_until=100)
    code, final, _ = run_fake(tmp_path, p, clock)
    assert code == 10 and "terminate_job" in p.calls and final["termination"] == "VERIFIED"


def test_abort_time(tmp_path):
    clock = Clock()
    p = FakePlatform(clock)
    code, final, _ = run_fake(tmp_path, p, clock, make_cfg(tmp_path, max_seconds=5))
    assert code == 20 and final["reason"] == "ABORT_TIME" and final["termination"] == "VERIFIED"
    assert "terminate_job" in p.calls and 5 <= final["elapsed_seconds"] < 7


def test_abort_memory_by_injection(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, available=lambda t: 8 * GiB if t < 2 else GiB)
    code, final, _ = run_fake(tmp_path, p, clock)
    assert code == 21 and final["reason"] == "ABORT_MEMORY" and final["min_available_bytes"] == GiB
    assert "terminate_job" in p.calls and final["termination"] == "VERIFIED"


def test_time_is_checked_before_memory(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, available=lambda t: 8 * GiB if t < 3 else GiB)
    code, _, _ = run_fake(tmp_path, p, clock, make_cfg(tmp_path, max_seconds=3))
    assert code == 20


def test_start_refused_by_injection(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, available=lambda t: 3 * GiB)
    code, final, _ = run_fake(tmp_path, p, clock)
    assert code == 30 and final["reason"] == "START_REFUSED" and not p.started and final["child_pid"] is None
    assert "create_job" not in p.calls


def test_monitor_failure(tmp_path):
    clock = Clock()
    p = FakePlatform(clock)
    real = p.available_memory

    def flaky() -> int:
        if clock.now >= 2:
            raise OSError("injected query failure")
        return real()

    p.available_memory = flaky
    code, final, _ = run_fake(tmp_path, p, clock)
    assert code == 22 and final["reason"] == "ABORT_MONITOR_FAILURE" and "terminate_job" in p.calls


def test_state_write_failure_stops_the_child(tmp_path):
    clock = Clock()
    p = FakePlatform(clock)

    def broken(path, data):
        raise OSError("injected state write failure")

    code, final, _ = run_fake(tmp_path, p, clock, write_state=broken)
    assert code == 23 and final["reason"] == "ABORT_STATE_WRITE_FAILURE" and "terminate_job" in p.calls


def test_final_write_failure(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, exit_at=2)

    def broken(path, data):
        raise OSError("injected final write failure")

    code, final, err = run_fake(tmp_path, p, clock, write_final=broken)
    assert code == 40 and final is None and err == "FINAL_WRITE_FAILURE\n" and p.calls[-1] == "close_job"


def test_assign_failure_terminates_the_child_handle(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, fail=("assign",))
    code, final, _ = run_fake(tmp_path, p, clock)
    assert code == 34 and final["termination"] == "VERIFIED"
    assert "terminate_child" in p.calls and "resume" not in p.calls and "close_thread" in p.calls


def test_assign_unconfirmed(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, in_job=False)
    code, final, _ = run_fake(tmp_path, p, clock)
    assert code == 35 and "terminate_child" in p.calls and "resume" not in p.calls


def test_resume_failure_terminates_the_job(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, fail=("resume",))
    code, final, _ = run_fake(tmp_path, p, clock)
    assert code == 36 and "terminate_job" in p.calls and final["termination"] == "VERIFIED"


def test_job_setup_and_child_start_failures(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, fail=("create_job",))
    code, final, _ = run_fake(tmp_path, p, clock, make_cfg(tmp_path, "a"))
    assert code == 32 and not p.started
    p = FakePlatform(clock, fail=("start_suspended",))
    code, final, _ = run_fake(tmp_path, p, clock, make_cfg(tmp_path, "b"))
    assert code == 33 and final["child_pid"] is None


def test_verification_timeout_is_unverified(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, terminate_works=False)
    code, final, _ = run_fake(tmp_path, p, clock, make_cfg(tmp_path, max_seconds=3, verify_seconds=2))
    assert code == 50 and final["reason"] == "ABORT_TIME" and final["termination"] == "UNVERIFIED"


def test_unverified_wins_over_final_write_failure(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, terminate_works=False)

    def broken(path, data):
        raise OSError("injected")

    code, _, err = run_fake(tmp_path, p, clock, make_cfg(tmp_path, max_seconds=3, verify_seconds=2),
                            write_final=broken)
    assert code == 50 and err == "FINAL_WRITE_FAILURE\n"


def test_internal_error_terminates_the_job(tmp_path):
    clock = Clock()
    p = FakePlatform(clock)
    calls = {"n": 0}
    real = p.wait_child

    def boom(child, seconds):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("injected internal error")
        return real(child, seconds)

    p.wait_child = boom
    code, final, _ = run_fake(tmp_path, p, clock)
    assert code == 70 and final["reason"] == "INTERNAL_ERROR" and "terminate_job" in p.calls


@pytest.mark.parametrize("over", [{"max_seconds": 0}, {"poll_seconds": -1}, {"verify_seconds": 0},
                                  {"start_min_available_bytes": -1}, {"abort_below_available_bytes": -1},
                                  {"start_min_available_bytes": GiB, "abort_below_available_bytes": 2 * GiB},
                                  {"argv": ()}, {"max_seconds": True}])
def test_argument_rejected(tmp_path, over):
    clock = Clock()
    p = FakePlatform(clock)
    code, final, err = run_fake(tmp_path, p, clock, make_cfg(tmp_path, **over))
    assert code == 29 and final is None and err == "ARGUMENT_REJECTED\n"
    assert not (tmp_path / "w").exists() and not p.calls


def test_cli_parse_rules(tmp_path):
    base = ["--watch-dir", str(tmp_path / "w"), "--max-seconds", "5", "--start-min-available-bytes", "0",
            "--abort-below-available-bytes", "0", "--poll-seconds", "1", "--verify-seconds", "2"]
    cfg = parse(base + ["--forbid-under", str(tmp_path / "out"), "--", "C:/x/python.exe", "-c", "pass"])
    assert cfg.argv == ("C:/x/python.exe", "-c", "pass") and cfg.forbid_under == (tmp_path / "out",)
    for bad in (base, base + ["--max-seconds", "x", "--", "a"], base + ["--fake-memory", "1", "--", "a"]):
        with pytest.raises(_ArgumentError):
            parse(bad)


def test_existing_watch_dir_is_rejected_unchanged(tmp_path):
    clock = Clock()
    target = tmp_path / "w"
    target.mkdir()
    (target / "keep.txt").write_bytes(b"keep\n")
    p = FakePlatform(clock)
    code, _, err = run_fake(tmp_path, p, clock)
    assert code == 31 and err == "START_PATH_REJECTED\n" and not p.calls
    assert os.listdir(target) == ["keep.txt"] and (target / "keep.txt").read_bytes() == b"keep\n"


def test_reparse_ancestor_is_rejected(tmp_path):
    clock = Clock()
    p = FakePlatform(clock)
    marked = tmp_path
    code, _, _ = run_fake(tmp_path, p, clock, is_reparse=lambda path: Path(path) == marked)
    assert code == 31 and not (tmp_path / "w").exists() and not p.calls


@pytest.mark.parametrize("forbid", ["same", "inside", "contains"])
def test_forbid_under_nesting_is_rejected(tmp_path, forbid):
    clock = Clock()
    p = FakePlatform(clock)
    watch = tmp_path / "out" / "w"
    target = {"same": watch, "inside": tmp_path / "out", "contains": watch / "deeper"}[forbid]
    cfg = make_cfg(tmp_path, watch_dir=watch, forbid_under=(target,))
    (tmp_path / "out").mkdir()
    code, _, _ = run_fake(tmp_path, p, clock, cfg)
    assert code == 31 and not watch.exists()


def test_argv_is_redacted_in_the_final_record(tmp_path):
    clock = Clock()
    p = FakePlatform(clock, exit_at=1)
    cfg = make_cfg(tmp_path, argv=("C:/x/python.exe", "password=hunter2", "0x" + "ab" * 32))
    code, final, _ = run_fake(tmp_path, p, clock, cfg)
    assert code == 0 and "hunter2" not in json.dumps(final) and ("ab" * 32) not in json.dumps(final)


# --- Windows integration (real job objects, synthetic processes) ---------------------------------------------------

win_only = pytest.mark.skipif(sys.platform != "win32", reason="Windows job objects")

SYNTHETIC = r'''
import ctypes, json, os, subprocess, sys, time
from ctypes import wintypes
mode, ids_dir, depth = sys.argv[1], sys.argv[2], int(sys.argv[3])
start = time.monotonic()
k = ctypes.WinDLL("kernel32", use_last_error=True)
k.GetCurrentProcess.restype = wintypes.HANDLE
k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
k.GetProcessTimes.restype = wintypes.BOOL
times = [wintypes.FILETIME() for _ in range(4)]
k.GetProcessTimes(k.GetCurrentProcess(), *[ctypes.byref(t) for t in times])
created = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
if ids_dir != "-":
    tmp = os.path.join(ids_dir, f"{os.getpid()}.part")
    with open(tmp, "w", encoding="ascii") as fh:
        json.dump({"pid": os.getpid(), "created": created, "depth": depth}, fh)
    os.replace(tmp, os.path.join(ids_dir, f"{os.getpid()}.json"))
child = None
if depth > 0:
    child = subprocess.Popen([sys.executable, "-B", __file__, mode, ids_dir, str(depth - 1)])
def rest(seconds):
    time.sleep(max(0.0, min(seconds, 60.0 - (time.monotonic() - start))))
if mode == "normal":
    if child is not None:
        child.wait()
    rest(0.5)
elif mode == "leftover":
    rest(3.0 if depth == 2 else 60.0)
elif mode == "brief":
    rest(3.0)
else:
    rest(60.0)
'''


def _k32():
    import ctypes
    from ctypes import wintypes

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    k.GetProcessTimes.restype = wintypes.BOOL
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.WaitForSingleObject.restype = wintypes.DWORD
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL
    return k


def _open_identified(ids_dir: Path, count: int, timeout: float = 20.0) -> list[int]:
    """Open SYNCHRONIZE handles to the synthetic processes and confirm identity by creation time."""
    import ctypes
    from ctypes import wintypes

    deadline = time.monotonic() + timeout
    while len(list(ids_dir.glob("*.json"))) < count:
        if time.monotonic() > deadline:
            pytest.fail(f"synthetic identities not complete: {len(list(ids_dir.glob('*.json')))}/{count}")
        time.sleep(0.05)
    k = _k32()
    handles = []
    for path in sorted(ids_dir.glob("*.json")):
        ident = json.loads(path.read_text(encoding="ascii"))
        h = k.OpenProcess(0x00100000 | 0x1000, False, ident["pid"])   # SYNCHRONIZE | QUERY_LIMITED_INFORMATION
        if not h:
            pytest.fail(f"identity unconfirmed: cannot open {ident['pid']}")
        times = [wintypes.FILETIME() for _ in range(4)]
        ok = k.GetProcessTimes(h, *[ctypes.byref(t) for t in times])
        created = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
        if not ok or created != ident["created"]:
            k.CloseHandle(h)
            pytest.fail(f"identity unconfirmed: {ident['pid']}")
        handles.append(h)
    return handles


def _all_gone(handles: list[int], timeout: float) -> bool:
    k = _k32()
    deadline = time.monotonic() + timeout
    gone = True
    for h in handles:
        remaining = max(0, int((deadline - time.monotonic()) * 1000))
        if k.WaitForSingleObject(h, remaining) != 0:
            gone = False
    for h in handles:
        k.CloseHandle(h)
    return gone


def _synthetic(tmp_path: Path) -> Path:
    script = tmp_path / "synthetic_child.py"
    script.write_text(SYNTHETIC, encoding="ascii")
    return script


def _watch_cmd(watch: Path, mode: str, ids: str, depth: int, script: Path, max_s: int, start: int = 0,
               abort: int = 0, verify: int = 10) -> list[str]:
    return [sys.executable, "-B", "-m", "moneylab.runwatch", "--watch-dir", str(watch), "--max-seconds", str(max_s),
            "--start-min-available-bytes", str(start), "--abort-below-available-bytes", str(abort),
            "--poll-seconds", "1", "--verify-seconds", str(verify), "--", sys.executable, "-B", str(script), mode, ids,
            str(depth)]


def _start(cmd: list[str], cwd: Path) -> subprocess.Popen:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _finish(proc: subprocess.Popen, timeout: float = 120) -> tuple[int, str]:
    try:
        out, _ = proc.communicate(timeout=timeout)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(10)
    return proc.returncode, out.decode("ascii", "replace")


def _final(watch: Path) -> dict:
    return json.loads((watch / W.FINAL_FILE).read_bytes())


@win_only
def test_w1a_normal_exit_code_0(tmp_path):
    script, ids = _synthetic(tmp_path), tmp_path / "ids"
    ids.mkdir()
    rc, out = _finish(_start(_watch_cmd(tmp_path / "w", "normal", str(ids), 2, script, 60), tmp_path))
    final = _final(tmp_path / "w")
    assert rc == 0 and out.strip() == "RUNWATCH COMPLETED 0", out
    assert final["reason"] == "COMPLETED" and final["termination"] == "VERIFIED" and final["child_exit_code"] == 0
    assert len(list(ids.glob("*.json"))) == 3
    assert sorted(os.listdir(tmp_path / "w")) == sorted([W.FINAL_FILE, W.STATE_FILE, W.STDOUT_FILE, W.STDERR_FILE])


@win_only
def test_w1b_leftover_exit_code_11(tmp_path):
    script, ids = _synthetic(tmp_path), tmp_path / "ids"
    ids.mkdir()
    proc = _start(_watch_cmd(tmp_path / "w", "leftover", str(ids), 2, script, 60), tmp_path)
    try:
        handles = _open_identified(ids, 3)
    finally:
        rc, out = _finish(proc)
    assert rc == 11 and out.strip() == "RUNWATCH COMPLETED_WITH_LEFTOVER 11", out
    assert _final(tmp_path / "w")["termination"] == "VERIFIED"
    assert _all_gone(handles, 10)


@win_only
def test_w2_timeout_stops_children_and_grandchildren(tmp_path):
    script, ids = _synthetic(tmp_path), tmp_path / "ids"
    ids.mkdir()
    proc = _start(_watch_cmd(tmp_path / "w", "long", str(ids), 2, script, 4), tmp_path)
    try:
        handles = _open_identified(ids, 3)
    finally:
        rc, out = _finish(proc)
    assert rc == 20 and out.strip() == "RUNWATCH ABORT_TIME 20", out
    assert _final(tmp_path / "w")["termination"] == "VERIFIED"
    assert _all_gone(handles, 10)


@win_only
def test_w3_real_memory_and_job_queries(tmp_path):
    script = _synthetic(tmp_path)
    rc, out = _finish(_start(_watch_cmd(tmp_path / "w", "brief", "-", 0, script, 60), tmp_path))
    assert rc == 0, out
    state = json.loads((tmp_path / "w" / W.STATE_FILE).read_bytes())
    assert isinstance(state["available_bytes"], int) and state["available_bytes"] > 0
    assert state["job_active_processes"] >= 1 and isinstance(state["peak_job_commit_bytes"], int)
    assert _final(tmp_path / "w")["peak_job_commit_bytes"] > 0


@win_only
def test_w4_start_refused_creates_no_child(tmp_path):
    script, ids = _synthetic(tmp_path), tmp_path / "ids"
    ids.mkdir()
    huge = 1 << 62
    rc, out = _finish(_start(_watch_cmd(tmp_path / "w", "brief", str(ids), 0, script, 60, start=huge, abort=huge),
                             tmp_path))
    final = _final(tmp_path / "w")
    assert rc == 30 and final["reason"] == "START_REFUSED" and final["child_pid"] is None, out
    assert os.listdir(tmp_path / "w") == [W.FINAL_FILE] and list(ids.iterdir()) == []


@win_only
def test_w5_killed_watcher_leaves_no_child(tmp_path):
    script, ids = _synthetic(tmp_path), tmp_path / "ids"
    ids.mkdir()
    proc = _start(_watch_cmd(tmp_path / "w", "long", str(ids), 2, script, 120), tmp_path)
    try:
        handles = _open_identified(ids, 3)
        proc.kill()
        proc.wait(10)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(10)
    assert _all_gone(handles, 15)
    assert not (tmp_path / "w" / W.FINAL_FILE).exists()


@win_only
def test_w6_unrelated_process_survives_a_job_stop(tmp_path):
    script, ids = _synthetic(tmp_path), tmp_path / "ids"
    ids.mkdir()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    sleeper = subprocess.Popen([sys.executable, "-B", str(script), "long", "-", "0"], cwd=str(tmp_path), env=env)
    try:
        rc, out = _finish(_start(_watch_cmd(tmp_path / "w", "long", str(ids), 2, script, 3), tmp_path))
        assert rc == 20, out
        assert sleeper.poll() is None
    finally:
        sleeper.kill()
        sleeper.wait(10)
    assert sleeper.poll() is not None
