"""Read-only collection of one worktree's Git and contract state (AUTO-02 D4-D8).

git runs without a shell from a fixed argv, with a subcommand allowlist, `GIT_OPTIONAL_LOCKS=0` (no index
refresh) and per-call timeout and stdout/stderr limits that are enforced while the output is read. Any error
ends the collection: a partial result is never returned. Collecting twice is a consistency check, not an
atomic snapshot."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import IO, Any

GIT_SUBCOMMANDS = frozenset({"rev-parse", "status", "ls-files", "ls-tree", "cat-file", "check-ignore"})
TIMEOUT_SECONDS = 30.0
STDOUT_LIMIT = 16 * 1024 * 1024
STDERR_LIMIT = 64 * 1024
REAP_SECONDS = 10.0
CHUNK = 65_536

MAX_ENTRIES = 2000
MAX_UNTRACKED = 2000
MAX_CONTRACT = 100
MAX_PATH_BYTES = 1024
OBJECT_LIMIT = 16 * 1024 * 1024  # one W file or one S blob
TOTAL_LIMIT = 512 * 1024 * 1024  # all hashed bytes of one collection

FILE_ATTRIBUTE_REPARSE_POINT = 0x400
ABSENT = "ABSENT"
IN_PROGRESS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG", "rebase-merge", "rebase-apply")

ARGUMENT_INVALID = "ARGUMENT_INVALID"
ENVIRONMENT_INVALID = "ENVIRONMENT_INVALID"
GIT_FAILED = "GIT_FAILED"
LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
UNSUPPORTED_STATE = "UNSUPPORTED_STATE"
UNSTABLE_STATE = "UNSTABLE_STATE"
STORE_PATH_INVALID = "STORE_PATH_INVALID"
STORE_FAILED = "STORE_FAILED"
SNAPSHOT_NOT_FOUND = "SNAPSHOT_NOT_FOUND"
SNAPSHOT_UNREADABLE = "SNAPSHOT_UNREADABLE"
SNAPSHOT_CORRUPT = "SNAPSHOT_CORRUPT"
SNAPSHOT_INCOMPATIBLE = "SNAPSHOT_INCOMPATIBLE"


class WorkstateError(Exception):
    """A defined failure with a result code (D13). Never a success and never a partial result."""

    def __init__(self, code: str, detail: str, file_sha256: str | None = None) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.file_sha256 = file_sha256
        self.final_file_created: bool | None = None
        self.warnings: list[str] = []


# Seams for tests: the platform checks and the git command prefix are looked up at call time.
_lstat = os.lstat


def _after_hash(path: Path) -> None:
    """Called between hashing a work file and re-checking its stat (tests inject a change here)."""


def _on_reaped(proc: subprocess.Popen[bytes]) -> None:
    """Called after a git child process has been waited for (tests check reaping here)."""


def _base_argv() -> list[str]:
    git = shutil.which("git")
    if git is None:
        raise WorkstateError(ENVIRONMENT_INVALID, "git executable not found on PATH")
    return [git]


def _git_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def _discard(chunk: bytes) -> None:
    del chunk


def _pump(stream: IO[bytes], limit: int, consume: Callable[[bytes], None], problems: list[WorkstateError],
          name: str) -> None:
    total = 0
    try:
        fd = stream.fileno()
        while True:
            chunk = os.read(fd, CHUNK)
            if not chunk:
                return
            total += len(chunk)
            if total > limit:
                problems.append(WorkstateError(LIMIT_EXCEEDED, f"git {name} exceeded {limit} bytes"))
                return
            consume(chunk)
    except WorkstateError as exc:
        problems.append(exc)
    except (OSError, ValueError) as exc:
        problems.append(WorkstateError(GIT_FAILED, f"git {name} could not be read: {type(exc).__name__}"))


def _close(proc: subprocess.Popen[bytes]) -> None:
    for stream in (proc.stdout, proc.stderr):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


def _kill_and_reap(proc: subprocess.Popen[bytes], threads: list[threading.Thread]) -> None:
    try:
        proc.kill()
    except OSError:
        pass
    try:
        proc.wait(timeout=REAP_SECONDS)
    except subprocess.TimeoutExpired:
        raise WorkstateError(GIT_FAILED, "child not reaped") from None
    for thread in threads:
        thread.join(REAP_SECONDS)
    if any(thread.is_alive() for thread in threads):
        raise WorkstateError(GIT_FAILED, "child not reaped")
    _close(proc)
    _on_reaped(proc)


def run_git(root: Path, sub: str, args: list[str], *, ok_codes: tuple[int, ...] = (0,),
            sink: Callable[[bytes], None] | None = None, limit: int | None = None) -> tuple[int, bytes]:
    """Run one allowlisted read-only git subcommand in `root`. Returns (exit code, stdout) unless `sink`
    consumes stdout. Raises WorkstateError on a limit, a timeout, a read error or an unexpected exit code."""
    if sub not in GIT_SUBCOMMANDS:
        raise WorkstateError(GIT_FAILED, f"git subcommand not allowed: {sub}")
    out_limit = STDOUT_LIMIT if limit is None else min(limit, STDOUT_LIMIT)
    argv = [*_base_argv(), "-C", str(root), "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
            sub, *args]
    buffer = bytearray()
    consume = sink if sink is not None else buffer.extend
    problems: list[WorkstateError] = []
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=_git_env(), shell=False)
    except OSError as exc:
        raise WorkstateError(GIT_FAILED, f"git could not start: {type(exc).__name__}") from exc
    assert proc.stdout is not None and proc.stderr is not None
    threads = [
        threading.Thread(target=_pump, args=(proc.stdout, out_limit, consume, problems, "stdout"), daemon=True),
        threading.Thread(target=_pump, args=(proc.stderr, STDERR_LIMIT, _discard, problems, "stderr"),
                         daemon=True),
    ]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + TIMEOUT_SECONDS
    timed_out = False
    while not problems:
        alive = [thread for thread in threads if thread.is_alive()]
        if not alive:
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        alive[0].join(min(0.05, remaining))
    if problems or timed_out:
        _kill_and_reap(proc, threads)
        if problems:
            raise problems[0]
        raise WorkstateError(GIT_FAILED, f"git {sub} timed out")
    try:
        code = proc.wait(timeout=max(0.0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        _kill_and_reap(proc, threads)
        raise WorkstateError(GIT_FAILED, f"git {sub} timed out") from None
    _close(proc)
    _on_reaped(proc)
    if problems:
        raise problems[0]
    if code not in ok_codes:
        raise WorkstateError(GIT_FAILED, f"git {sub} exited with {code}")
    return code, bytes(buffer)


def is_link_like(path: Path, st: Any) -> bool:
    """True for a symlink, a junction or any Windows reparse point."""
    if stat.S_ISLNK(st.st_mode) or os.path.islink(path):
        return True
    if Path(path).is_junction():
        return True
    return bool(getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)


def check_tree_path(root: Path, rel: str, code: str, *, require_regular: bool) -> Any:
    """lstat every component of root/rel. A link-like or non-directory parent raises `code`; a missing
    component returns None. With require_regular, an existing target must be a regular file."""
    parts = rel.split("/")
    current = Path(root)
    st: Any = None
    for index, part in enumerate(parts):
        current = current / part
        shown = "/".join(parts[:index + 1])
        try:
            st = _lstat(current)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise WorkstateError(code, f"cannot inspect {shown}: {type(exc).__name__}") from exc
        if is_link_like(current, st):
            raise WorkstateError(code, f"link or reparse point: {shown}")
        if index < len(parts) - 1 and not stat.S_ISDIR(st.st_mode):
            raise WorkstateError(code, f"not a directory: {shown}")
    if require_regular and not stat.S_ISREG(st.st_mode):
        raise WorkstateError(code, f"not a regular file: {rel}")
    return st


class _Budget:
    def __init__(self) -> None:
        self.used = 0

    def take(self, size: int) -> None:
        self.used += size
        if self.used > TOTAL_LIMIT:
            raise WorkstateError(LIMIT_EXCEEDED, "hashed bytes exceed the total limit")


def _path_text(raw: bytes) -> str:
    if len(raw) > MAX_PATH_BYTES:
        raise WorkstateError(LIMIT_EXCEEDED, "a path is longer than the limit")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WorkstateError(UNSUPPORTED_STATE, "a path is not valid UTF-8") from exc


def _hash_work_file(root: Path, rel: str, budget: _Budget) -> str:
    """W: SHA-256 of the work file bytes, or ABSENT. The file must not change while it is hashed."""
    before = check_tree_path(root, rel, UNSUPPORTED_STATE, require_regular=True)
    if before is None:
        return ABSENT
    if before.st_size > OBJECT_LIMIT:
        raise WorkstateError(LIMIT_EXCEEDED, f"work file larger than the limit: {rel}")
    path = Path(root) / rel
    digest = hashlib.sha256()
    size = 0
    try:
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > OBJECT_LIMIT:
                    raise WorkstateError(LIMIT_EXCEEDED, f"work file larger than the limit: {rel}")
                budget.take(len(chunk))
                digest.update(chunk)
    except OSError as exc:
        raise WorkstateError(UNSTABLE_STATE, f"work file changed while read: {rel}") from exc
    _after_hash(path)
    try:
        after = _lstat(path)
    except OSError as exc:
        raise WorkstateError(UNSTABLE_STATE, f"work file changed while read: {rel}") from exc
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or size != after.st_size:
        raise WorkstateError(UNSTABLE_STATE, f"work file changed while read: {rel}")
    return digest.hexdigest()


def _hash_blob(root: Path, oid: str, budget: _Budget) -> str:
    """S: SHA-256 of a blob's content, streamed from `git cat-file blob` under OBJECT_LIMIT."""
    digest = hashlib.sha256()

    def sink(chunk: bytes) -> None:
        budget.take(len(chunk))
        digest.update(chunk)

    run_git(root, "cat-file", ["blob", oid], sink=sink, limit=OBJECT_LIMIT)
    return digest.hexdigest()


def _text(out: bytes) -> str:
    return out.decode("utf-8").strip()


def _collect_once(root: Path, task_id: str) -> dict[str, Any]:
    budget = _Budget()
    code, out = run_git(root, "rev-parse", ["--verify", "-q", "HEAD"], ok_codes=(0, 1))
    if code != 0:
        raise WorkstateError(UNSUPPORTED_STATE, "HEAD has no commit (unborn repository)")
    head = _text(out)
    tree = _text(run_git(root, "rev-parse", ["HEAD^{tree}"])[1])
    ref = _text(run_git(root, "rev-parse", ["--symbolic-full-name", "HEAD"])[1])
    branch = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else None

    git_path_args: list[str] = []
    for name in IN_PROGRESS:
        git_path_args += ["--git-path", name]
    lines = run_git(root, "rev-parse", git_path_args)[1].decode("utf-8").splitlines()
    for name, line in zip(IN_PROGRESS, lines, strict=True):
        candidate = Path(line)
        if not candidate.is_absolute():
            candidate = Path(root) / candidate
        if os.path.lexists(candidate):
            raise WorkstateError(UNSUPPORTED_STATE, f"operation in progress: {name}")

    for record in run_git(root, "ls-files", ["-v", "-z"])[1].split(b"\0"):
        tag = record[:1].decode("ascii", "replace")
        if record and (tag == "S" or tag.islower()):
            raise WorkstateError(UNSUPPORTED_STATE, "an index entry is skip-worktree or assume-unchanged")

    status = run_git(root, "status", ["--porcelain=v2", "-z", "--untracked-files=all", "--no-renames",
                                      "--ignored=no"])[1]
    raw_entries: list[tuple[str, list[str]]] = []
    untracked: list[str] = []
    for record in status.split(b"\0"):
        if not record:
            continue
        kind = record[:2]
        if kind == b"1 ":
            fields = record.split(b" ", 8)
            if len(fields) != 9:
                raise WorkstateError(GIT_FAILED, "unexpected git status record")
            meta = [field.decode("ascii") for field in fields[1:8]]
            if not meta[1].startswith("N"):
                raise WorkstateError(UNSUPPORTED_STATE, "submodule change")
            if {"160000", "120000"} & set(meta[2:5]):
                raise WorkstateError(UNSUPPORTED_STATE, "gitlink or symlink change")
            raw_entries.append((_path_text(fields[8]), meta))
        elif kind == b"? ":
            untracked.append(_path_text(record[2:]))
        elif kind == b"u ":
            raise WorkstateError(UNSUPPORTED_STATE, "unmerged index entry")
        else:
            raise WorkstateError(UNSUPPORTED_STATE, "unsupported git status record")
    if len(raw_entries) > MAX_ENTRIES:
        raise WorkstateError(LIMIT_EXCEEDED, "too many changed paths")
    if len(untracked) > MAX_UNTRACKED:
        raise WorkstateError(LIMIT_EXCEEDED, "too many untracked paths")

    entries: list[dict[str, str]] = []
    for path, meta in sorted(raw_entries):
        xy, _sub, head_mode, index_mode, _work_mode, head_blob, index_blob = meta
        s_sha = ABSENT if index_mode == "000000" else _hash_blob(root, index_blob, budget)
        entries.append({"path": path, "xy": xy, "head_mode": head_mode, "head_blob": head_blob,
                        "index_mode": index_mode, "index_blob": index_blob,
                        "w_sha256": _hash_work_file(root, path, budget), "s_sha256": s_sha})
    for path in untracked:
        if check_tree_path(root, path, UNSUPPORTED_STATE, require_regular=True) is None:
            raise WorkstateError(UNSTABLE_STATE, f"untracked file vanished: {path}")

    prefix = f"docs/tasks/{task_id}"
    head_objects: dict[str, str] = {}
    for record in run_git(root, "ls-tree", ["-r", "-z", "--full-tree", "HEAD", "--", prefix])[1].split(b"\0"):
        if not record:
            continue
        info, _tab, raw_path = record.partition(b"\t")
        mode, kind_text, oid = info.decode("ascii").split(" ")
        if mode not in ("100644", "100755") or kind_text != "blob":
            raise WorkstateError(UNSUPPORTED_STATE, "a contract entry is not a regular file")
        head_objects[_path_text(raw_path)] = oid
    listed = run_git(root, "ls-files", ["-c", "-o", "--exclude-standard", "-z", "--", prefix])[1]
    work_paths = {_path_text(record) for record in listed.split(b"\0") if record}
    contract_paths = sorted(path for path in set(head_objects) | work_paths if path.startswith(prefix + "/"))
    if len(contract_paths) > MAX_CONTRACT:
        raise WorkstateError(LIMIT_EXCEEDED, "too many contract files")
    contract = [{"path": path,
                 "head_sha256": _hash_blob(root, head_objects[path], budget) if path in head_objects else ABSENT,
                 "work_sha256": _hash_work_file(root, path, budget)} for path in contract_paths]
    return {"branch": branch, "head": head, "tree": tree, "entries": entries, "untracked": sorted(untracked),
            "contract": contract}


def collect_state(root: Path, task_id: str) -> dict[str, Any]:
    """Collect twice and require both results to be equal (a consistency check, not an atomic snapshot)."""
    first = _collect_once(root, task_id)
    second = _collect_once(root, task_id)
    if first != second:
        raise WorkstateError(UNSTABLE_STATE, "the state changed between the two collections")
    return first
