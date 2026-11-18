"""CLI: python -m moneylab.runwatch --watch-dir DIR --max-seconds N --start-min-available-bytes N
--abort-below-available-bytes N --poll-seconds N --verify-seconds N [--forbid-under DIR]... -- ARGV...

Prints one line `RUNWATCH <reason> <exit code>` and exits with the watcher exit code (RUNWATCH-01 D10).
There is no option to fake memory values.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from moneylab.runwatch.watch import EXIT_CODES, Config, supervise


class _ArgumentError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise _ArgumentError(message)


def _parser() -> _Parser:
    parser = _Parser(prog="python -m moneylab.runwatch", add_help=False)
    parser.add_argument("--watch-dir", required=True)
    parser.add_argument("--max-seconds", type=int, required=True)
    parser.add_argument("--start-min-available-bytes", type=int, required=True)
    parser.add_argument("--abort-below-available-bytes", type=int, required=True)
    parser.add_argument("--poll-seconds", type=int, required=True)
    parser.add_argument("--verify-seconds", type=int, required=True)
    parser.add_argument("--forbid-under", action="append", default=[])
    return parser


def _reason(code: int) -> str:
    return next(name for name, value in EXIT_CODES.items() if value == code)


def _report(code: int) -> int:
    print(f"RUNWATCH {_reason(code)} {code}")
    return code


def parse(argv: Sequence[str]) -> Config:
    """Split at the first `--` and build the Config. Raises _ArgumentError for malformed input."""
    args = list(argv)
    if "--" not in args:
        raise _ArgumentError("missing -- before the command")
    split = args.index("--")
    ns = _parser().parse_args(args[:split])
    return Config(watch_dir=Path(ns.watch_dir), max_seconds=ns.max_seconds,
                  start_min_available_bytes=ns.start_min_available_bytes,
                  abort_below_available_bytes=ns.abort_below_available_bytes, poll_seconds=ns.poll_seconds,
                  verify_seconds=ns.verify_seconds, argv=tuple(args[split + 1:]), cwd=Path(os.getcwd()),
                  forbid_under=tuple(Path(p) for p in ns.forbid_under))


def main(argv: Sequence[str] | None = None) -> int:
    if sys.platform != "win32":
        sys.stderr.write("UNSUPPORTED_PLATFORM\n")
        return _report(EXIT_CODES["UNSUPPORTED_PLATFORM"])
    try:
        cfg = parse(sys.argv[1:] if argv is None else argv)
    except _ArgumentError:
        sys.stderr.write("ARGUMENT_REJECTED\n")
        return _report(EXIT_CODES["ARGUMENT_REJECTED"])
    from moneylab.runwatch.winjob import LayoutError, WinPlatform

    try:
        platform = WinPlatform()
    except (LayoutError, OSError):
        sys.stderr.write("JOB_SETUP_FAILED\n")
        return _report(EXIT_CODES["JOB_SETUP_FAILED"])
    return _report(supervise(cfg, platform))


if __name__ == "__main__":
    raise SystemExit(main())
