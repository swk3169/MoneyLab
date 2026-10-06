"""PolymarketRecorder: shared machinery for read-only market-data recorders.

A concrete recorder only decides *how* observations arrive (REST polling today, a WebSocket
`book` channel later); storage, duplicate handling, state, error classification, backoff and
stop rules live here so every transport records the same dataset format (see store.py).

Failure policy (no retries of policy decisions, no bypass of any kind):
  HTTP 451          -> stop immediately, status `blocked_http_451`, response diagnostics in
                       state.json. MoneyLab does not determine the cause; the body is recorded.
  HTTP 401 / 403    -> stop immediately, status `access_denied` (cause not determined)
  HTTP 429          -> wait Retry-After (or backoff), then continue
  other HTTP / network / bad payload -> exponential backoff with jitter, then continue;
                       `max_consecutive_failures` in a row -> status `failed`
Every failed poll is also written as an `error` record so a replay sees the same gaps.

Deliberately absent: orders, signing, wallets, credentials, proxies.
"""

from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.core.redaction import redact_text
from moneylab.providers.polymarket.recorder.store import RecordingStore
# Re-exported: these used to be defined here and are now shared by every recorder.
from moneylab.recording.core import (  # noqa: F401
    FATAL_STATUSES,
    Failure,
    RecorderStatus,
    SourceExhausted,
    backoff_delay,
    classify,
    parse_retry_after,
)
from moneylab.recording.core import header as _header  # noqa: F401

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecorderConfig:
    condition_ids: tuple[str, ...]
    interval: float = 60.0  # seconds between polls
    max_polls: int | None = None  # None = until stopped
    duration: float | None = None  # seconds; None = until stopped
    metadata_refresh: float = 3600.0  # re-fetch /clob-markets and /rewards every N seconds
    min_request_spacing: float = 0.5  # client-side rate limit between any two requests
    backoff_base: float = 2.0
    backoff_max: float = 300.0
    max_consecutive_failures: int = 30
    rebate_rate: float = 0.0  # not served by the CLOB; caller supplies (Gamma feeSchedule or docs table)
    rebate_rate_source: str = "config"

    def __post_init__(self):
        if not self.condition_ids:
            raise ValueError("at least one condition id is required")
        if self.interval <= 0:
            raise ValueError("interval must be > 0")


@dataclass
class RecorderReport:
    recorder: str
    status: RecorderStatus = RecorderStatus.IDLE
    started_at: float | None = None
    stopped_at: float | None = None
    polls: int = 0
    books_written: int = 0
    unchanged_written: int = 0
    duplicates_skipped: int = 0
    errors: int = 0
    rate_limited: int = 0
    last_error: dict[str, Any] | None = None
    datasets: dict[str, Path] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status not in FATAL_STATUSES


class PolymarketRecorder(ABC):
    """Base class. Subclasses implement `_run_loop`, using `_record_books`, `_record_failure`
    and `_wait` so storage, state and pacing are identical across transports."""

    name = "abstract"
    source_label = "abstract"

    def __init__(
        self, out_dir: Path, config: RecorderConfig, *, synthetic: bool = False, origin: str | None = None,
        clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ):
        self.out_dir = Path(out_dir)
        self.config = config
        self.synthetic = synthetic
        self.origin = origin
        self.clock, self.sleep = clock, sleep
        self.rng = rng or random.Random()
        self.stores: dict[str, RecordingStore] = {}
        self.report = RecorderReport(self.name)
        self.consecutive_failures = 0
        self._stop_requested = False
        self._last_request: float | None = None

    # --- public API ---------------------------------------------------------------------
    def stop(self) -> None:
        """Ask the loop to finish after the current step (thread-safe enough for a flag)."""
        self._stop_requested = True

    def run(self) -> RecorderReport:
        now = self.clock()
        self.report = RecorderReport(self.name, RecorderStatus.RUNNING, started_at=now)
        try:
            self._open_stores(now)
        except (OSError, ValueError) as exc:
            self.report.status = RecorderStatus.FAILED
            self.report.last_error = {"category": "storage", "message": redact_text(str(exc))}
            self.report.stopped_at = self.clock()
            log.error("Recorder cannot open datasets: %s", exc)
            return self.report
        status = RecorderStatus.FAILED
        try:
            status = self._run_loop()
        except KeyboardInterrupt:
            status = RecorderStatus.STOPPED
            log.warning("Recorder interrupted; state saved")
        finally:
            end = self.clock()
            self.report.status, self.report.stopped_at = status, end
            for store in self.stores.values():
                try:
                    store.end_run(end, status.value)
                except OSError as exc:  # pragma: no cover - disk full etc.
                    log.error("Could not save state for %s: %s", store.condition_id, exc)
        return self.report

    # --- for subclasses -----------------------------------------------------------------
    @abstractmethod
    def _run_loop(self) -> RecorderStatus:
        """Acquire observations until a stop condition; return the final status."""

    def _open_stores(self, now: float) -> None:
        for cid in self.config.condition_ids:
            store = RecordingStore.open(self.out_dir, cid, synthetic=self.synthetic, source=self.source_label,
                                        interval=self.config.interval, now=now, origin=self.origin)
            if store.resumed:
                log.info("Resuming %s at seq %d", cid, store.cursor.last_seq + 1)
            if store.removed_tmp:
                log.warning("%s: removed %d leftover temp files", cid, len(store.removed_tmp))
            self.report.warnings.extend(f"{cid}: {w}" for w in store.warnings)
            self.stores[cid] = store
            self.report.datasets[cid] = store.path
        self._on_resume()
        now = self.clock()
        self.report.started_at = now
        for store in self.stores.values():
            store.begin_run(now, self.name)

    def _on_resume(self) -> None:  # noqa: B027 - optional hook
        """Called after datasets are opened, before the run starts (e.g. to skip recorded data)."""

    def _should_stop(self, started: float) -> RecorderStatus | None:
        if self._stop_requested:
            return RecorderStatus.STOPPED
        c = self.config
        if c.max_polls is not None and self.report.polls >= c.max_polls:
            return RecorderStatus.COMPLETED
        if c.duration is not None and self.clock() - started >= c.duration:
            return RecorderStatus.COMPLETED
        return None

    def _throttle(self) -> None:
        """Client-side rate limit: keep `min_request_spacing` between requests."""
        now = self.clock()
        if self._last_request is not None:
            wait = self.config.min_request_spacing - (now - self._last_request)
            if wait > 0:
                self.sleep(wait)
        self._last_request = self.clock()

    def _record_books(self, cid: str, raw_books: list[dict[str, Any]], recorded_at: float,
                      missing: list[str] | None = None) -> None:
        res = self.stores[cid].append_books(raw_books, recorded_at, self.source_label, missing)
        if res.kind == "book":
            self.report.books_written += 1
        elif res.kind == "unchanged":
            self.report.unchanged_written += 1
        else:
            self.report.duplicates_skipped += 1

    def _record_failure(self, failure: Failure, recorded_at: float, cids: list[str] | None = None) -> None:
        self.report.errors += 1
        self.report.last_error = failure.to_record()
        if failure.category == "rate_limited":
            self.report.rate_limited += 1
        log.warning("poll failed (%s): %s", failure.category, failure.message)
        for cid in cids or list(self.stores):
            store = self.stores[cid]
            store.append_error(recorded_at, failure.to_record(), self.source_label)
            extra: dict[str, Any] = {"last_error": failure.to_record(), "consecutive_failures": self.consecutive_failures}
            if failure.fatal_status is not None:
                extra["blocked"] = {"at": datetime.fromtimestamp(recorded_at, UTC).isoformat(), **failure.to_record()}
            if failure.category == "rate_limited":
                store._count("rate_limited")
            store.update_state(recorded_at, **extra)

    def _backoff_delay(self, failure: Failure) -> float:
        c = self.config
        return backoff_delay(self.consecutive_failures, c.backoff_base, c.backoff_max, self.rng,
                             failure.retry_after, floor=c.interval)

    def _wait(self, seconds: float) -> None:
        if seconds > 0 and not self._stop_requested:
            self.sleep(seconds)
