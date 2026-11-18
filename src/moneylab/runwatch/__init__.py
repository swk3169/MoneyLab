"""Run watcher: start one command inside a Windows job object, watch elapsed time and available memory,
and stop the whole job when a limit or a monitoring failure is reached (Work Order RUNWATCH-01).

The watcher is separate from research code. It records operational information only (times, memory,
process counts, reasons) and never lists or reads research output.
"""

from moneylab.runwatch.watch import EXIT_CODES, Config, supervise

__all__ = ["EXIT_CODES", "Config", "supervise"]
