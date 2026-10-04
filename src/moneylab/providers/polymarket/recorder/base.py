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
from email.utils import parsedate_to_datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from moneylab.core.exceptions import ApiError, NetworkError
from moneylab.core.redaction import redact_text
from moneylab.providers.polymarket.recorder.store import RecordingStore

log = logging.getLogger(__name__)


class RecorderStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"  # reached max_polls / duration
    STOPPED = "stopped"  # stop() or Ctrl+C
    SOURCE_EXHAUSTED = "source_exhausted"  # replay/fixture source has no more data
    BLOCKED_HTTP_451 = "blocked_http_451"
    ACCESS_DENIED = "access_denied"  # 401 / 403
    FAILED = "failed"  # too many consecutive failures, or unusable configuration


FATAL_STATUSES = frozenset({RecorderStatus.BLOCKED_HTTP_451, RecorderStatus.ACCESS_DENIED, RecorderStatus.FAILED})


class SourceExhausted(Exception):
    """Raised by finite (fixture/replay) sources when there is no more data."""


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


@dataclass(frozen=True)
class Failure:
    """A classified poll failure."""

    category: str  # http_451 | access_denied | rate_limited | http | network | bad_payload
    message: str
    status_code: int | None = None
    retry_after: float | None = None
    diagnostics: dict[str, Any] | None = None

    @property
    def fatal_status(self) -> RecorderStatus | None:
        if self.category == "http_451":
            return RecorderStatus.BLOCKED_HTTP_451
        if self.category == "access_denied":
            return RecorderStatus.ACCESS_DENIED
        return None

    def to_record(self) -> dict[str, Any]:
        out: dict[str, Any] = {"category": self.category, "status_code": self.status_code, "message": self.message}
        if self.retry_after is not None:
            out["retry_after"] = self.retry_after
        if self.diagnostics is not None:
            out["diagnostics"] = self.diagnostics
        return out


def _header(headers: dict[str, str], name: str) -> str | None:
    low = name.lower()
    return next((v for k, v in headers.items() if k.lower() == low), None)


def parse_retry_after(value: str | None, now: float) -> float | None:
    """Retry-After is either delta-seconds or an HTTP-date (RFC 9110)."""
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, when.timestamp() - now)


def classify(exc: Exception, now: float) -> Failure:
    if isinstance(exc, ApiError):
        d = exc.diagnostics
        code = d.status_code
        if code == 451:
            # Facts only: status, reason, the (already redacted) body and the headers the
            # server sent. No conclusion about why access is restricted.
            return Failure("http_451", f"HTTP 451 {d.reason or ''}: {d.method} {d.url}".strip(), 451, diagnostics={
                "status_code": code, "reason": d.reason, "url": d.url, "headers": d.headers,
                "body_excerpt": d.body_excerpt,
                "note": "HTTP 451 received. The server did not state which client attribute caused it; "
                        "MoneyLab does not infer one. Recorder stopped without retrying.",
            })
        if code in (401, 403):
            return Failure("access_denied", f"HTTP {code} {d.reason or ''}: {d.method} {d.url}".strip(), code,
                           diagnostics={"status_code": code, "reason": d.reason, "url": d.url,
                                        "body_excerpt": d.body_excerpt})
        if code == 429:
            return Failure("rate_limited", str(exc), 429,
                           retry_after=parse_retry_after(_header(d.headers, "Retry-After"), now))
        if code is None:
            return Failure("bad_payload", f"{exc} ({d.error or 'unusable body'})",
                           diagnostics={"body_excerpt": d.body_excerpt})
        if 200 <= code < 300:  # 2xx with a body that is not JSON
            return Failure("bad_payload", f"{exc}: {d.error or ''}".strip(), code,
                           diagnostics={"body_excerpt": d.body_excerpt})
        return Failure("http", str(exc), code)
    if isinstance(exc, NetworkError):
        return Failure("network", str(exc))
    return Failure("bad_payload", redact_text(f"{type(exc).__name__}: {exc}"))


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
        exp = min(c.backoff_max, c.backoff_base * 2 ** max(0, self.consecutive_failures - 1))
        delay = exp * (0.5 + self.rng.random() / 2)  # "equal jitter"
        if failure.retry_after is not None:  # the server's Retry-After always wins, even above backoff_max
            delay = max(delay, failure.retry_after)
        return max(delay, c.interval)

    def _wait(self, seconds: float) -> None:
        if seconds > 0 and not self._stop_requested:
            self.sleep(seconds)
