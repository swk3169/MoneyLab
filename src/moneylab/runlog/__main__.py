"""CLI (AUTO-03 D2, D16-D18 as replaced by ERRATA-001): `python -m moneylab.runlog store --task-id ID` reads
evidence from stdin and `python -m moneylab.runlog show --task-id ID --record-id ID` prints one stored record.

Every defined outcome, argument errors and an unreadable stdin included, is one `moneylab.runlog.result/1`
object written to stdout as canonical JSON plus LF, with nothing on stderr (`--help` alone prints argparse
text). The output always carries `authority: "NONE"`. There is no root option and no environment override: the
root is the checkout this package was imported from. Neither command runs an action.

Two cases have no result object (ERRATA-001 D18): an undefined internal exception and a failure while writing
the result to stdout. Then the outcome, including whether a record file was created, is UNKNOWN: one fixed
line goes to stderr when possible, the exit code is 2, no second result is written and nothing is retried. A
caller accepts a result only when stdout is exactly one canonical result object plus LF, its exit_code equals
the process exit code and stderr is empty."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, BinaryIO, NoReturn

from moneylab.runlog import store
from moneylab.runlog.store import ARGUMENT_INVALID, ENVIRONMENT_INVALID, INPUT_UNAVAILABLE, RunlogError

INTERNAL_FAILURE = "runlog: internal failure; outcome unknown"
OUTPUT_FAILURE = "runlog: output failure; outcome unknown"
UNKNOWN_EXIT = 2


class _ArgumentError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgumentError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="python -m moneylab.runlog", description="Non-authoritative evidence records.",
                     exit_on_error=False)
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    put = sub.add_parser("store", help="validate evidence JSON from stdin and store it", exit_on_error=False)
    put.add_argument("--task-id", required=True)
    get = sub.add_parser("show", help="print one stored record by id", exit_on_error=False)
    get.add_argument("--task-id", required=True)
    get.add_argument("--record-id", required=True)
    return parser


def _read_input(stdin: BinaryIO | None) -> bytes | None:
    """At most STDIN_LIMIT + 1 bytes; None when stdin has no binary buffer or cannot be read."""
    stream = getattr(sys.stdin, "buffer", None) if stdin is None else stdin
    if stream is None:
        return None
    try:
        data = stream.read(store.STDIN_LIMIT + 1)
    except (OSError, ValueError):
        return None
    return data


def _run(argv: list[str] | None, root: Path | None, stdin: BinaryIO | None) -> dict[str, Any]:
    """Private: tests inject a tmp root and an input stream; production passes None for both."""
    try:
        args = build_parser().parse_args(argv)
    except (_ArgumentError, argparse.ArgumentError):
        return store.failure(None, RunlogError(ARGUMENT_INVALID, "invalid arguments"))
    if args.command == "store":
        if not store.valid_task_id(args.task_id):
            return store.failure("store", RunlogError(ARGUMENT_INVALID, "invalid task id"))
        raw = _read_input(stdin)
        if raw is None:
            return store.failure("store", RunlogError(ENVIRONMENT_INVALID, INPUT_UNAVAILABLE), task_id=args.task_id)
        return store.store_at(root, args.task_id, raw)
    return store.show_at(root, args.task_id, args.record_id)


def _stderr_line(text: str) -> None:
    """Best effort: the fixed line alone, never a traceback or exception text."""
    try:
        sys.stderr.write(text + "\n")
        sys.stderr.flush()
    except Exception:  # noqa: BLE001 - nothing more can be reported
        pass


def _silence_broken_stdout() -> None:
    """Output-failure path only: point the broken stdout fd at the null device so that the interpreter's final
    flush of the unwritten buffer does not fail again (which would print "Exception ignored" and exit 120).
    The null device is opened write-only without any create flag; the extra fd is closed afterwards unless it
    is the stdout fd itself. A stream without a usable fd, or any failure here, is left as it is."""
    try:
        fd = sys.stdout.fileno()
    except Exception:  # noqa: BLE001 - no usable fd (fake or closed stream): nothing to redirect
        return
    if type(fd) is not int or fd < 0:
        return
    devnull: int | None = None
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, fd)
    except Exception:  # noqa: BLE001 - best effort; the fixed line and exit 2 still stand
        pass
    finally:
        if devnull is not None and devnull != fd:
            try:
                os.close(devnull)
            except OSError:
                pass


def _write_stdout(data: bytes) -> None:
    """One write attempt. Only an int byte count equal to len(data) counts as written; a short write, 0 or None
    is an output failure (ERRATA-001 D18). The rest is never resent."""
    sys.stdout.flush()
    written = sys.stdout.buffer.write(data)
    if type(written) is not int or written != len(data):
        raise OSError("short write")
    sys.stdout.buffer.flush()


def _main(argv: list[str] | None, *, root: Path | None, stdin: BinaryIO | None) -> int:
    try:
        out = _run(argv, root, stdin)
        data = store.canonical_bytes(out) + b"\n"
        code = int(out["exit_code"])
    except Exception:  # noqa: BLE001 - D18: undefined internal failure, outcome unknown
        _stderr_line(INTERNAL_FAILURE)
        return UNKNOWN_EXIT
    try:
        _write_stdout(data)
    except Exception:  # noqa: BLE001 - D18: output failure, outcome unknown; no second result, no retry
        _stderr_line(OUTPUT_FAILURE)
        _silence_broken_stdout()
        return UNKNOWN_EXIT
    return code


def main(argv: list[str] | None = None) -> int:
    return _main(argv, root=None, stdin=None)


if __name__ == "__main__":
    sys.exit(main())
