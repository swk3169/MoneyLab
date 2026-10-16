"""UpbitRecorder: Upbit public WebSocket (orderbook + trade) -> UpbitStore datasets. Read-only.

Per connection:
  connect (connect rate limit, backoff) -> send the documented subscription -> receive frames;
  every frame is timestamped right after `recv` returns, parsed, checked for duplicates and
  appended (raw text kept verbatim). A "PING" text message is sent every `ping_text_interval`
  seconds (documented keep-alive, answered with {"status":"UP"}); the transport also sends
  WebSocket PING frames. No market data for `stale_timeout` seconds -> reconnect.

Failure policy (recording.core): 451 / 401 / 403 stop immediately; 418 waits the ban the server
states (Retry-After) or `ban_default_wait`, and stops when the ban is longer than
`max_ban_wait`; 429 waits Retry-After or at least 1 s ("retry from the next second"); everything
else backs off exponentially with jitter. `max_consecutive_failures` connection attempts in a
row without market data end the run with status `failed` (no endless reconnect loop).

Long runs (v0.4): graceful stop on Ctrl+C (KeyboardInterrupt) and on SIGBREAK/SIGTERM via
`stop(reason)` (installed by the CLI, recording.shutdown); free disk space is checked every
`disk_check_interval` s and the run stops below `min_free_bytes` (reason disk_low); a heartbeat
every `status_interval` s logs counts (books, trades, reconnects, gaps, stale/crossed/locked
books, disk, clock quality) and rewrites `capture_manifest.json`. On every exit the buffer is
flushed, state saved and the capture manifest finalized with the termination reason and the
sha256 of every raw file. An optional read-only ClockMonitor (core.clock_monitor) runs alongside;
with `stop_on_clock_unstable` a CLOCK_UNSTABLE status stops the run. The raw line format is
unchanged; the new counters are not written into raw lines.

Deliberately absent: API keys, JWT, private endpoints, orders, proxies.
"""

from __future__ import annotations

import base64
import json
import logging
import random
import shutil
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.core.clock_monitor import CLOCK_UNSTABLE as CLOCK_STATUS_UNSTABLE
from moneylab.core.ratelimit import SlidingWindowLimiter
from moneylab.core.redaction import redact_text
from moneylab.providers.upbit.endpoints import (
    DEFAULT_MARKET,
    DOC_REFS,
    IDLE_TIMEOUT_SECONDS,
    NO_AGGREGATION_LEVEL,
    ORDERBOOK_UNITS_ALLOWED,
    PING_TEXT,
    WS_CONNECT_LIMITS,
    WS_MESSAGE_LIMITS,
    validate_market,
)
from moneylab.providers.upbit.parser import (
    UpbitParseError,
    build_subscription,
    decode_frame,
    load_message,
    message_kind,
    parse_error,
    parse_orderbook,
    parse_trade,
)
from moneylab.providers.upbit.recorder.store import (
    CAPTURE_MANIFEST,
    CLOCK_LOG,
    UpbitStore,
    book_content_key,
    raw_file_manifest,
    read_json,
)
from moneylab.providers.upbit.ws_client import Connector, WsClosed, WsConnectError, WsConnection, WsHandshakeError
from moneylab.recording.core import (
    FATAL_STATUSES,
    NOTE_451,
    Failure,
    RecorderStatus,
    SourceExhausted,
    backoff_delay,
    header,
    iso,
    parse_retry_after,
)
from moneylab.recording import shutdown as term
from moneylab.storage.atomic import atomic_write_json, sha256_of

log = logging.getLogger(__name__)

SOURCE_LABEL = "upbit-ws-public"


@dataclass(frozen=True)
class UpbitRecorderConfig:
    markets: tuple[str, ...] = (DEFAULT_MARKET,)
    orderbook_units: int = 30
    duration: float | None = None  # seconds; None = until stopped
    max_market_events: int | None = None  # stop after N orderbook+trade messages (tests, smoke)
    ping_text_interval: float = 60.0  # "PING" text keep-alive; must stay below the 120 s idle timeout
    stale_timeout: float = 60.0  # no market data for this long -> reconnect
    recv_timeout: float = 1.0
    flush_interval: float = 2.0
    flush_max_events: int = 500
    backoff_base: float = 1.0
    backoff_max: float = 60.0
    min_connect_spacing: float = 1.0  # docs allow 5 connects/s per IP; we use at most 1/s
    max_consecutive_failures: int = 10
    rate_limit_min_wait: float = 1.0  # 429: docs say retry from the next second
    ban_default_wait: float = 60.0  # 418 without a parseable ban duration (format unverified)
    max_ban_wait: float = 600.0  # 418 bans longer than this stop the recorder
    status_interval: float = 300.0  # heartbeat log + capture manifest update
    disk_check_interval: float = 600.0
    min_free_bytes: int = 5 * 1024**3  # free space below this -> graceful stop (disk_low)
    stale_book_seconds: float = 1.0  # counters only; research flags are computed offline
    gap_seconds: float = 10.0  # no frame for this long -> counted as a gap
    stop_on_clock_unstable: bool = False

    def __post_init__(self):
        if not self.markets:
            raise ValueError("at least one market is required")
        for m in self.markets:
            validate_market(m)
        if len(set(self.markets)) != len(self.markets):
            raise ValueError("duplicate markets")
        if self.orderbook_units not in ORDERBOOK_UNITS_ALLOWED:
            raise ValueError(f"orderbook_units must be one of {ORDERBOOK_UNITS_ALLOWED}")
        if not 0 < self.ping_text_interval < IDLE_TIMEOUT_SECONDS:
            raise ValueError(f"ping_text_interval must be in (0, {IDLE_TIMEOUT_SECONDS:g}) seconds")
        if self.stale_timeout <= 0 or self.recv_timeout <= 0:
            raise ValueError("timeouts must be > 0")
        if self.max_consecutive_failures < 1:
            raise ValueError("max_consecutive_failures must be >= 1")
        if self.status_interval <= 0 or self.disk_check_interval <= 0 or self.min_free_bytes < 0:
            raise ValueError("status/disk intervals must be > 0 and min_free_bytes >= 0")


@dataclass
class UpbitRecorderReport:
    recorder: str = "upbit-ws"
    status: RecorderStatus = RecorderStatus.IDLE
    started_at: float | None = None
    stopped_at: float | None = None
    connections: int = 0
    connect_failures: int = 0
    messages: int = 0
    orderbook_events: int = 0
    trade_events: int = 0
    duplicate_orderbooks: int = 0
    duplicate_trades: int = 0
    status_replies: int = 0
    pings_sent: int = 0
    server_errors: int = 0
    parse_errors: int = 0
    unknown_messages: int = 0
    disconnects: int = 0
    failures: int = 0
    rate_limited: int = 0
    banned: int = 0
    segments_written: int = 0
    crossed_books: int = 0
    locked_books: int = 0
    stale_books: int = 0
    gaps: int = 0
    heartbeats: int = 0
    termination_reason: str | None = None
    disk_free_start: int | None = None
    disk_free_end: int | None = None
    last_heartbeat: dict[str, Any] | None = None
    clock: dict[str, Any] | None = None
    last_error: dict[str, Any] | None = None
    datasets: dict[str, Path] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status not in FATAL_STATUSES

    @property
    def market_events(self) -> int:
        return self.orderbook_events + self.trade_events

    def counters(self) -> dict[str, int]:
        keys = ("connections", "connect_failures", "messages", "orderbook_events", "trade_events",
                "duplicate_orderbooks", "duplicate_trades", "status_replies", "pings_sent", "server_errors",
                "parse_errors", "unknown_messages", "disconnects", "failures", "rate_limited", "banned",
                "segments_written", "crossed_books", "locked_books", "stale_books", "gaps", "heartbeats")
        return {k: getattr(self, k) for k in keys}


def classify_ws_error(exc: Exception, now: float, config: UpbitRecorderConfig) -> Failure:
    """Map transport errors to recorder failures following the documented rate-limit policy."""
    if isinstance(exc, WsHandshakeError):
        code, diag = exc.status_code, exc.diagnostics()
        if code == 451:
            return Failure("http_451", str(exc), 451, diagnostics={**diag, "note": NOTE_451})
        if code in (401, 403):
            return Failure("access_denied", str(exc), code, diagnostics=diag)
        retry_after = parse_retry_after(header(exc.headers, "Retry-After"), now)
        if code == 418:
            # Docs: the response states the ban duration. Its exact form is not documented;
            # a standard Retry-After header is honoured, otherwise a conservative default.
            source = "Retry-After header" if retry_after is not None else "default (no Retry-After header)"
            return Failure("banned", str(exc), 418, retry_after=retry_after,
                           diagnostics={**diag, "ban_duration_source": source})
        if code == 429:
            return Failure("rate_limited", str(exc), 429,
                           retry_after=max(retry_after or 0.0, config.rate_limit_min_wait), diagnostics=diag)
        return Failure("http", str(exc), code, diagnostics=diag)
    if isinstance(exc, WsConnectError):
        return Failure("network", str(exc))
    if isinstance(exc, WsClosed):
        return Failure("disconnected", str(exc), diagnostics={"close_code": exc.code, "close_reason": exc.reason})
    return Failure("network", redact_text(f"{type(exc).__name__}: {exc}"))


class UpbitRecorder:
    name = "upbit-ws"

    def __init__(
        self, connector: Connector, url: str, out_dir: Path, config: UpbitRecorderConfig, *, provenance: str,
        origin: str | None = None, clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep, rng: random.Random | None = None,
        ticket_factory: Callable[[], str] = lambda: str(uuid.uuid4()),
        disk_free: Callable[[Path], int] | None = None, clock_monitor: Any = None,
    ):
        self.connector, self.url = connector, url
        self.out_dir = Path(out_dir)
        self.config = config
        self.provenance = provenance
        self.origin = origin or url
        self.clock, self.sleep = clock, sleep
        self.rng = rng or random.Random()
        self.ticket_factory = ticket_factory
        self.stores: dict[str, UpbitStore] = {}
        self.report = UpbitRecorderReport(self.name)
        self.consecutive_failures = 0
        self._stop_requested = False
        self._last_connect: float | None = None
        self._connect_limiter = SlidingWindowLimiter(WS_CONNECT_LIMITS, clock=clock, sleep=sleep)
        self._started = 0.0
        self._connection_seq = 0
        self._disk_free_fn = disk_free or _disk_free_bytes
        self.clock_monitor = clock_monitor
        self._stop_reason: str | None = None
        self._last_disk = self._last_status = 0.0
        self._last_frame: float | None = None
        self._last_book: dict[str, float] = {}

    # --- public API ---------------------------------------------------------------------
    def stop(self, reason: str = term.STOPPED) -> None:
        """Request a graceful stop (safe from signal handlers and other threads)."""
        if self._stop_reason is None:
            self._stop_reason = reason
        self._stop_requested = True

    def run(self) -> UpbitRecorderReport:
        now = self.clock()
        self.report = UpbitRecorderReport(self.name, RecorderStatus.RUNNING, started_at=now)
        try:
            self._open_stores(now)
        except (OSError, ValueError) as exc:
            self.report.status = RecorderStatus.FAILED
            self.report.termination_reason = term.UNEXPECTED_ERROR
            self.report.last_error = {"category": "storage", "message": redact_text(str(exc))}
            self.report.stopped_at = self.clock()
            log.error("Recorder cannot open datasets: %s", exc)
            return self.report
        self.report.disk_free_start = self._disk_free()
        self._last_disk = self._last_status = self._started
        self._write_capture(final=False)
        status, reason = RecorderStatus.FAILED, None
        try:
            status = self._run_loop()
        except KeyboardInterrupt:
            status, reason = RecorderStatus.STOPPED, term.KEYBOARD_INTERRUPT
            log.warning("Recorder interrupted; buffered events flushed and state saved")
        except Exception as exc:  # last resort: still flush, save state and finalize the manifest
            status, reason = RecorderStatus.FAILED, term.UNEXPECTED_ERROR
            self.report.last_error = {"category": "unexpected", "message": redact_text(f"{type(exc).__name__}: {exc}")}
            log.error("Recorder stopped by an unexpected error: %s", self.report.last_error["message"])
        finally:
            end = self.clock()
            self.report.status, self.report.stopped_at = status, end
            self.report.termination_reason = reason or self._reason_for(status)
            self.report.disk_free_end = self._disk_free()
            if self.clock_monitor is not None:
                try:
                    self.clock_monitor.stop(final_measurement=True)
                    self.report.clock = self.clock_monitor.summary()
                except Exception as exc:  # the clock monitor never blocks a clean shutdown
                    log.warning("clock monitor shutdown: %s", exc)
            for store in self.stores.values():
                try:
                    store.flush()
                    store.end_run(end, status.value, termination_reason=self.report.termination_reason)
                except OSError as exc:  # pragma: no cover - disk full etc.
                    log.error("Could not save %s: %s", store.market, exc)
                self.report.segments_written += store.segments_written
            self._write_capture(final=True)
        return self.report

    def _reason_for(self, status: RecorderStatus) -> str:
        if status == RecorderStatus.COMPLETED:
            return term.COMPLETED
        if status == RecorderStatus.SOURCE_EXHAUSTED:
            return term.SOURCE_EXHAUSTED
        if status == RecorderStatus.STOPPED:
            return self._stop_reason or term.STOPPED
        return term.CONNECTION_FAILURE  # failed / blocked / access denied / banned

    # --- long-run safety ----------------------------------------------------------------
    def _disk_free(self) -> int | None:
        try:
            return int(self._disk_free_fn(self.out_dir))
        except OSError as exc:
            log.warning("cannot read free disk space: %s", exc)
            return None

    def _periodic(self) -> None:
        c, now = self.config, self.clock()
        if now - self._last_disk >= c.disk_check_interval:
            self._last_disk = now
            free = self._disk_free()
            if free is not None and free < c.min_free_bytes:
                msg = f"free disk space {free / 1e9:.2f} GB below {c.min_free_bytes / 1e9:.2f} GB; stopping"
                log.error(msg)
                self.report.warnings.append(msg)
                self.stop(term.DISK_LOW)
        if (self.clock_monitor is not None and c.stop_on_clock_unstable
                and self.clock_monitor.status == CLOCK_STATUS_UNSTABLE):
            log.error("clock quality CLOCK_UNSTABLE; stopping")
            self.stop(term.CLOCK_UNSTABLE)
        if now - self._last_status >= c.status_interval:
            self._last_status = now
            self._heartbeat(now)

    def _heartbeat(self, now: float) -> None:
        r = self.report
        clock = self.clock_monitor.summary() if self.clock_monitor is not None else None
        hb = {"at": iso(now), "runtime_seconds": round(now - self._started, 3), "books": r.orderbook_events,
              "trades": r.trade_events, "reconnects": max(0, r.connections - 1), "disconnects": r.disconnects,
              "gaps": r.gaps, "stale_books": r.stale_books, "crossed_books": r.crossed_books,
              "locked_books": r.locked_books, "disk_free_bytes": self._disk_free(),
              "clock_quality_status": None if clock is None else clock["clock_quality_status"],
              "clock_offset_ms": None if clock is None else clock["clock_offset_end_ms"]}
        r.heartbeats += 1
        r.last_heartbeat = hb
        log.info("heartbeat %s", hb)
        self._write_capture(final=False)

    def _write_capture(self, final: bool) -> None:
        """Recorder-owned run summary next to the raw data (atomic). Raw lines are not touched."""
        r = self.report
        started = iso(r.started_at) if r.started_at else None
        run = {"run_id": started, "started_at": started, "stopped_at": iso(r.stopped_at) if r.stopped_at else None,
               "final": final, "status": r.status.value, "termination_reason": r.termination_reason,
               "counters": r.counters(), "disk_free_start_bytes": r.disk_free_start,
               "disk_free_end_bytes": r.disk_free_end, "min_free_bytes": self.config.min_free_bytes,
               "last_heartbeat": r.last_heartbeat,
               "clock": r.clock if final else (self.clock_monitor.summary() if self.clock_monitor is not None else None),
               "clock_log": CLOCK_LOG if self.clock_monitor is not None else None,
               "config": {k: v for k, v in self.config.__dict__.items() if k != "markets"},
               "last_error": r.last_error, "warnings": r.warnings[:20]}
        for store in self.stores.values():
            path = store.path / CAPTURE_MANIFEST
            try:
                doc = read_json(path) if path.exists() else {}
            except (OSError, ValueError):
                doc = {}
            doc.update(schema="moneylab.upbit.capture_manifest/1", market=store.market, provenance=store.provenance)
            runs = doc.setdefault("runs", [])
            if runs and runs[-1].get("run_id") == run["run_id"]:
                runs[-1] = dict(run)
            else:
                runs.append(dict(run))
            if final:
                try:
                    manifest = raw_file_manifest(store.path)
                    runs[-1]["raw_manifest"] = manifest
                    doc["raw_manifest_sha256"] = manifest["manifest_sha256"]
                except (OSError, ValueError) as exc:
                    runs[-1]["raw_manifest_error"] = str(exc)
            try:
                atomic_write_json(path, doc)
            except OSError as exc:  # pragma: no cover - disk full
                log.error("cannot write %s: %s", path, exc)

    # --- setup --------------------------------------------------------------------------
    def _open_stores(self, now: float) -> None:
        for market in self.config.markets:
            store = UpbitStore.open(self.out_dir, market, provenance=self.provenance, origin=self.origin,
                                    orderbook_units=self.config.orderbook_units, source=SOURCE_LABEL, now=now,
                                    doc_refs=DOC_REFS)
            if store.resumed:
                log.info("Resuming %s at local_sequence %d", market, store.cursor.last_seq + 1)
            if store.removed_tmp:
                log.warning("%s: removed %d leftover temp files", market, len(store.removed_tmp))
            self.report.warnings.extend(f"{market}: {w}" for w in store.warnings)
            self.stores[market] = store
            self.report.datasets[market] = store.path
        resume_after = getattr(self.connector, "resume_after", None)
        done = [s.cursor.last_received for s in self.stores.values() if s.cursor.last_received is not None]
        if resume_after is not None and done:  # finite (fixture) sources restart from their beginning
            skipped = resume_after(max(done))
            if skipped:
                log.info("source fast-forwarded past %d already recorded frames", skipped)
        self._started = self.clock()
        self.report.started_at = self._started
        for store in self.stores.values():
            store.begin_run(self._started, self.name)

    # --- stop rules ---------------------------------------------------------------------
    def _remaining(self) -> float | None:
        if self.config.duration is None:
            return None
        return self.config.duration - (self.clock() - self._started)

    def _should_stop(self) -> RecorderStatus | None:
        if self._stop_requested:
            return RecorderStatus.STOPPED
        self._periodic()
        if self._stop_requested:
            return RecorderStatus.STOPPED
        c = self.config
        if c.max_market_events is not None and self.report.market_events >= c.max_market_events:
            return RecorderStatus.COMPLETED
        remaining = self._remaining()
        if remaining is not None and remaining <= 0:
            return RecorderStatus.COMPLETED
        return None

    def _wait(self, seconds: float) -> None:
        remaining = self._remaining()
        if remaining is not None:
            seconds = min(seconds, max(0.0, remaining))
        if seconds > 0 and not self._stop_requested:
            self.sleep(seconds)

    # --- event helpers ------------------------------------------------------------------
    def _append_all(self, event: dict[str, Any]) -> None:
        for store in self.stores.values():
            store.append({**event, "market": None})

    def _local_event(self, event_type: str, now: float, conn_id: str | None, detail: dict[str, Any]) -> None:
        self._append_all({"event_type": event_type, "exchange_timestamp": None, "received_timestamp": now,
                          "connection_id": conn_id, "raw": None, "detail": detail})

    def _record_failure(self, failure: Failure, now: float, conn_id: str | None) -> None:
        self.report.failures += 1
        self.report.last_error = failure.to_record()
        if failure.category == "rate_limited":
            self.report.rate_limited += 1
        if failure.category == "banned":
            self.report.banned += 1
        log.warning("Upbit WebSocket failure (%s): %s", failure.category, failure.message)
        disconnect = failure.category in ("disconnected", "stale", "server_error")
        if disconnect:
            self.report.disconnects += 1
        self._local_event("disconnect" if disconnect else "failure", now, conn_id,
                          {**failure.to_record(), "consecutive_failures": self.consecutive_failures})
        for store in self.stores.values():
            store.flush()
            extra: dict[str, Any] = {"last_error": failure.to_record(), "consecutive_failures": self.consecutive_failures}
            if failure.fatal_status is not None:
                extra["blocked"] = {"at": datetime.fromtimestamp(now, UTC).isoformat(), **failure.to_record()}
            store.update_state(now, **extra)

    # --- main loop ----------------------------------------------------------------------
    def _run_loop(self) -> RecorderStatus:
        c = self.config
        while True:
            stop = self._should_stop()
            if stop is not None:
                return stop
            conn_id: str | None = None
            try:
                conn, conn_id = self._connect()
            except SourceExhausted:
                return RecorderStatus.SOURCE_EXHAUSTED
            except (WsHandshakeError, WsConnectError) as exc:
                self.report.connect_failures += 1
                failure, got_data, status = classify_ws_error(exc, self.clock(), c), False, None
            else:
                try:
                    status, failure, got_data = self._session(conn, conn_id)
                except SourceExhausted:
                    status, failure, got_data = RecorderStatus.SOURCE_EXHAUSTED, None, False
                finally:
                    conn.close()
                    for store in self.stores.values():
                        store.flush()
                if status is not None:
                    self._local_event("disconnect", self.clock(), conn_id, {"category": "shutdown",
                                                                            "status": status.value})
                    return status
            if got_data:
                self.consecutive_failures = 0
            self.consecutive_failures += 1
            now = self.clock()
            self._record_failure(failure, now, conn_id)
            if failure.fatal_status is not None:
                log.error("Recorder stopped: %s", failure.message)
                return failure.fatal_status
            if failure.category == "banned":
                ban = failure.retry_after if failure.retry_after is not None else c.ban_default_wait
                if ban > c.max_ban_wait:
                    log.error("HTTP 418 ban of %.0fs exceeds max_ban_wait %.0fs; stopping", ban, c.max_ban_wait)
                    return RecorderStatus.BANNED_HTTP_418
                if self.consecutive_failures >= c.max_consecutive_failures:
                    return RecorderStatus.FAILED
                self._wait(ban)
                continue
            if self.consecutive_failures >= c.max_consecutive_failures:
                log.error("Recorder stopped after %d consecutive failures", self.consecutive_failures)
                return RecorderStatus.FAILED
            self._wait(backoff_delay(self.consecutive_failures, c.backoff_base, c.backoff_max, self.rng,
                                     failure.retry_after, floor=c.min_connect_spacing))

    def _connect(self) -> tuple[WsConnection, str]:
        c = self.config
        if self._last_connect is not None:
            gap = c.min_connect_spacing - (self.clock() - self._last_connect)
            if gap > 0:
                self.sleep(gap)
        self._connect_limiter.acquire()
        self._last_connect = self.clock()
        self._connection_seq += 1
        conn_id = f"{datetime.fromtimestamp(self._last_connect, UTC).strftime('%Y%m%dT%H%M%S')}-{self._connection_seq}"
        conn = self.connector(self.url)
        self.report.connections += 1
        return conn, conn_id

    def _session(self, conn: WsConnection, conn_id: str) -> tuple[RecorderStatus | None, Failure | None, bool]:
        """Returns (final status, None, got_data) to end the run, or (None, failure, got_data)."""
        c = self.config
        limiter = SlidingWindowLimiter(WS_MESSAGE_LIMITS, clock=self.clock, sleep=self.sleep)  # per connection
        request = build_subscription(self.ticket_factory(), list(c.markets), orderbook_units=c.orderbook_units)
        try:
            limiter.acquire()
            conn.send(json.dumps(request, separators=(",", ":")))
        except WsClosed as exc:
            return None, classify_ws_error(exc, self.clock(), c), False
        opened = self.clock()
        self._last_book.clear()  # stale-book counting is per connection
        self._local_event("connection", opened, conn_id, {"url": self.url, "request": request})
        last_market = last_ping = opened
        got_data = False
        while True:
            stop = self._should_stop()
            if stop is not None:
                return stop, None, got_data
            now = self.clock()
            if now - last_ping >= c.ping_text_interval:
                try:
                    limiter.acquire()
                    conn.send(PING_TEXT)
                except WsClosed as exc:
                    return None, classify_ws_error(exc, self.clock(), c), got_data
                self.report.pings_sent += 1
                last_ping = now
            if now - last_market >= c.stale_timeout:
                return None, Failure("stale", f"no market data for {now - last_market:.0f}s; reconnecting"), got_data
            for store in self.stores.values():
                if store.flush_due(now, c.flush_interval, c.flush_max_events):
                    store.flush()
            try:
                frame = conn.recv(c.recv_timeout)
            except TimeoutError:
                continue
            except WsClosed as exc:
                return None, classify_ws_error(exc, self.clock(), c), got_data
            received = self.clock()  # as close to the receive as possible, before any parsing
            kind, detail = self._handle_frame(frame, received, conn_id)
            if kind in ("orderbook", "trade"):
                got_data = True
                last_market = received
            elif kind == "server_error":
                return None, Failure("server_error", f"server error message {detail}"), got_data

    # --- frames -------------------------------------------------------------------------
    def _handle_frame(self, frame: bytes | str, received: float, conn_id: str) -> tuple[str, str | None]:
        self.report.messages += 1
        if self._last_frame is not None and received - self._last_frame > self.config.gap_seconds:
            self.report.gaps += 1
        self._last_frame = received
        base: dict[str, Any] = {"received_timestamp": received, "connection_id": conn_id}
        try:
            text, frame_type = decode_frame(frame)
        except UpbitParseError as exc:
            raw_bytes = bytes(frame) if isinstance(frame, (bytes, bytearray, memoryview)) else repr(frame).encode()
            self.report.parse_errors += 1
            self._append_all({**base, "event_type": "malformed", "exchange_timestamp": None, "frame": "binary",
                              "raw": None, "raw_base64": base64.b64encode(raw_bytes).decode("ascii"),
                              "raw_sha256": sha256_of(raw_bytes.hex()), "parse_error": str(exc)})
            return "malformed", None
        base.update(frame=frame_type, raw=text, raw_sha256=sha256_of(text))
        try:
            obj = load_message(text)
        except UpbitParseError as exc:
            self.report.parse_errors += 1
            self._append_all({**base, "event_type": "malformed", "exchange_timestamp": None, "parse_error": str(exc)})
            return "malformed", None
        kind = message_kind(obj)
        if kind == "orderbook":
            return self._orderbook(obj, base), None
        if kind == "trade":
            return self._trade(obj, base), None
        if kind == "status":
            self.report.status_replies += 1
            self._append_all({**base, "event_type": "status", "exchange_timestamp": None})
            return "status", None
        if kind == "error":
            name, message = parse_error(obj)
            self.report.server_errors += 1
            self._append_all({**base, "event_type": "server_error", "exchange_timestamp": None,
                              "detail": {"name": name, "message": message}})
            return "server_error", f"{name}: {message}"
        self.report.unknown_messages += 1
        store = self.stores.get(str(obj.get("code")))
        event = {**base, "event_type": "unknown", "exchange_timestamp": None}
        if store is not None:
            store.append({**event, "market": store.market})
        else:
            self._append_all(event)
        return "unknown", None

    def _route(self, obj: dict[str, Any], base: dict[str, Any], event_type: str) -> UpbitStore | None:
        store = self.stores.get(str(obj.get("code")))
        if store is None:  # a market we did not subscribe to, or no code at all
            self.report.unknown_messages += 1
            self._append_all({**base, "event_type": "unknown", "exchange_timestamp": None,
                              "parse_error": f"{event_type} for unsubscribed market {obj.get('code')!r}"})
        return store

    def _orderbook(self, obj: dict[str, Any], base: dict[str, Any]) -> str:
        store = self._route(obj, base, "orderbook")
        if store is None:
            return "unknown"
        ts = obj.get("timestamp") if isinstance(obj.get("timestamp"), int) else None
        event: dict[str, Any] = {**base, "event_type": "orderbook", "market": store.market,
                                 "exchange_timestamp": ts, "stream_type": obj.get("stream_type")}
        try:
            msg = parse_orderbook(obj)
        except UpbitParseError as exc:
            self.report.parse_errors += 1
            store.append({**event, "parse_error": str(exc), "duplicate": False})
            return "malformed"
        key = book_content_key(obj)
        dup_of = store.duplicate_book(msg.exchange_timestamp_ms, key)
        summary = msg.summary()
        if msg.level not in (None, NO_AGGREGATION_LEVEL):
            self.report.warnings.append(f"orderbook level={msg.level} received (aggregation was not requested)")
        store.append({**event, "orderbook": summary, "book_key": key, "duplicate": dup_of is not None,
                      "duplicate_of": dup_of, "parse_error": None})
        if dup_of is not None:
            self.report.duplicate_orderbooks += 1
        else:
            bb, ba = summary.get("best_bid"), summary.get("best_ask")
            if bb is not None and ba is not None:
                self.report.crossed_books += bb > ba
                self.report.locked_books += bb == ba
            recv = float(base["received_timestamp"])
            prev = self._last_book.get(store.market)
            if prev is not None and recv - prev > self.config.stale_book_seconds:
                self.report.stale_books += 1
            self._last_book[store.market] = recv
        self.report.orderbook_events += 1
        return "orderbook"

    def _trade(self, obj: dict[str, Any], base: dict[str, Any]) -> str:
        store = self._route(obj, base, "trade")
        if store is None:
            return "unknown"
        ts = obj.get("timestamp") if isinstance(obj.get("timestamp"), int) else None
        event: dict[str, Any] = {**base, "event_type": "trade", "market": store.market, "exchange_timestamp": ts,
                                 "stream_type": obj.get("stream_type")}
        try:
            msg = parse_trade(obj)
        except UpbitParseError as exc:
            self.report.parse_errors += 1
            store.append({**event, "parse_error": str(exc), "duplicate": False})
            return "malformed"
        dup_of = store.duplicate_trade(msg.sequential_id)
        store.append({**event, "trade": msg.summary(), "duplicate": dup_of is not None, "duplicate_of": dup_of,
                      "parse_error": None})
        if dup_of is not None:
            self.report.duplicate_trades += 1
        self.report.trade_events += 1
        return "trade"


def _disk_free_bytes(path: Path) -> int:
    p = Path(path)
    while not p.exists() and p.parent != p:
        p = p.parent
    return shutil.disk_usage(p).free
