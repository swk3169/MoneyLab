"""Graceful-stop signals and termination reasons for long-running recorders (provider-neutral).

`install_stop_signals(stop)` routes SIGBREAK (Windows console Ctrl+Break; platform-dependent) and
SIGTERM to `stop(reason)`, so the recorder leaves its receive loop at the next check, flushes its
buffer, saves state and writes its capture manifest. Ctrl+C keeps arriving as KeyboardInterrupt,
which the recorder handles the same way. Signals can only be installed from the main thread;
elsewhere installation is skipped and reported.

Whether closing the console window is delivered as SIGBREAK depends on the Windows C runtime and
is NOT verified here; Windows also kills the process a few seconds after a close event, so a
console close is not a reliable shutdown path. Use Ctrl+C or Ctrl+Break.
"""

from __future__ import annotations

import logging
import signal
from collections.abc import Callable

log = logging.getLogger(__name__)

# Termination reasons recorded in state.json / capture_manifest.json
COMPLETED = "completed"
KEYBOARD_INTERRUPT = "keyboard_interrupt"
SIGBREAK = "sigbreak"
SIGTERM = "sigterm"
DISK_LOW = "disk_low"
CONNECTION_FAILURE = "connection_failure"
CLOCK_UNSTABLE = "clock_unstable"
UNEXPECTED_ERROR = "unexpected_error"
STOPPED = "stopped"  # stop() called by code
SOURCE_EXHAUSTED = "source_exhausted"  # finite fixture source
TERMINATION_REASONS = (COMPLETED, KEYBOARD_INTERRUPT, SIGBREAK, SIGTERM, DISK_LOW, CONNECTION_FAILURE, CLOCK_UNSTABLE,
                       UNEXPECTED_ERROR, STOPPED, SOURCE_EXHAUSTED)

_SIGNALS = (("SIGBREAK", SIGBREAK), ("SIGTERM", SIGTERM))


def available_stop_signals() -> list[str]:
    return [name for name, _ in _SIGNALS if hasattr(signal, name)]


def install_stop_signals(stop: Callable[[str], None]) -> Callable[[], None]:
    """Install handlers; returns a function that restores the previous handlers."""
    previous: dict[int, object] = {}
    for name, reason in _SIGNALS:
        sig = getattr(signal, name, None)
        if sig is None:
            continue

        def handler(signum, frame, _reason=reason):
            log.warning("received %s; stopping gracefully", _reason)
            stop(_reason)

        try:
            previous[sig] = signal.signal(sig, handler)
        except (ValueError, OSError) as exc:  # not the main thread / not supported
            log.warning("cannot install %s handler: %s", name, exc)

    def restore() -> None:
        for sig, h in previous.items():
            try:
                signal.signal(sig, h)
            except (ValueError, OSError, TypeError):
                pass
    return restore
