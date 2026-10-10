"""Upbit recording (raw, read-only) -> provider-neutral MarketEvents with quality flags.

The raw dataset is only read (through UpbitRecordingReader.iter_lines, which verifies every
line checksum and the provenance). Nothing is dropped silently: duplicates, SNAPSHOT messages,
stale/crossed books and reconnects are kept and flagged; the research layer decides what to
exclude. Lines that carry no usable market data (status replies, unknown messages, unparseable
frames) produce no event, are counted, and mark the next market event with `sequence_gap`
because a message may have been lost there.

Flags (domain.market_events):
  warmup              SNAPSHOT, or before first REALTIME book of the connection + warmup_seconds
  stale_book          book arriving > stale_book_seconds after the previous book of its connection
  crossed_book        best_bid > best_ask        locked_book  best_bid == best_ask
  timestamp_reverse   exchange `timestamp` below the previous one of the same stream, or a
                      receive time below the previous line's (local clock step)
  sequence_gap        local_sequence not contiguous, or an unusable line just before
  duplicate           flagged duplicate by the recorder (never applied to the book state)
  reconnect_boundary  connection / disconnect / failure events and the first market event
                      after a connection
"""

from __future__ import annotations

import gzip
import json
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from moneylab.domain.market_events import (
    BOOK,
    CONNECTION,
    CROSSED_BOOK,
    DISCONNECT,
    DUPLICATE,
    FAILURE,
    LOCKED_BOOK,
    RECONNECT_BOUNDARY,
    SEQUENCE_GAP,
    STALE_BOOK,
    TIMESTAMP_REVERSE,
    TRADE,
    WARMUP,
    MarketEvent,
    TradePrint,
)
from moneylab.providers.upbit.parser import UpbitParseError, load_message, parse_orderbook, parse_trade
from moneylab.providers.upbit.recorder.replay import UpbitRecordingReader
from moneylab.providers.upbit.recorder.store import raw_file_manifest
from moneylab.storage.atomic import atomic_open, atomic_write_json

SCHEMA_EVENTS = "moneylab.research.market_events/1"
LOCAL_LINE_TYPES = {"connection": CONNECTION, "disconnect": DISCONNECT, "failure": FAILURE}
# Lines after which a market message may be missing.
LOSSY_LINE_TYPES = ("malformed", "server_error")


@dataclass(frozen=True)
class ExportParams:
    warmup_seconds: float = 5.0
    stale_book_seconds: float = 1.0


@dataclass
class ExportStats:
    lines: int = 0
    events: int = 0
    skipped: Counter = field(default_factory=Counter)  # line event_type -> count (no event produced)
    flags: Counter = field(default_factory=Counter)
    event_types: Counter = field(default_factory=Counter)

    def to_dict(self) -> dict[str, Any]:
        return {"lines": self.lines, "events": self.events, "skipped": dict(self.skipped),
                "flags": dict(self.flags), "event_types": dict(self.event_types)}


@dataclass
class _Conn:
    first_realtime_book: float | None = None
    last_book: float | None = None
    boundary_pending: bool = True


def iter_market_events(dataset_dir: str | Path, params: ExportParams = ExportParams(),
                       stats: ExportStats | None = None) -> Iterator[MarketEvent]:
    """Events in arrival (local_sequence) order. Raises ProviderError on unreadable/tampered data."""
    reader = UpbitRecordingReader(dataset_dir, verify_checksums=True)
    stats = stats if stats is not None else ExportStats()
    provenance, market = reader.provenance, reader.market
    conns: dict[str | None, _Conn] = {}
    prev_seq: int | None = None
    prev_recv: float | None = None
    last_ex: dict[str, int] = {}
    lost_pending = False

    for line in reader.iter_lines():
        stats.lines += 1
        seq, recv, et = int(line["local_sequence"]), float(line["received_timestamp"]), line.get("event_type")
        flags: set[str] = set()
        if prev_seq is not None and seq != prev_seq + 1:
            flags.add(SEQUENCE_GAP)
        if prev_recv is not None and recv < prev_recv:
            flags.add(TIMESTAMP_REVERSE)
        prev_seq, prev_recv = seq, max(recv, prev_recv if prev_recv is not None else recv)
        conn_id = line.get("connection_id")
        base = dict(market=market, provenance=provenance, received_timestamp=recv, local_sequence=seq,
                    connection_id=conn_id)

        if et in LOCAL_LINE_TYPES:
            if et == "connection":
                conns[conn_id] = _Conn()
            ev = MarketEvent(event_type=LOCAL_LINE_TYPES[et], flags=frozenset(flags | {RECONNECT_BOUNDARY}), **base)
            yield _emit(ev, stats)
            continue
        if et not in ("orderbook", "trade") or line.get("parse_error"):
            stats.skipped[et if not line.get("parse_error") else f"{et}_parse_error"] += 1
            if et in LOSSY_LINE_TYPES or line.get("parse_error"):
                lost_pending = True
            continue
        if lost_pending:
            flags.add(SEQUENCE_GAP)
            lost_pending = False

        conn = conns.setdefault(conn_id, _Conn())
        if conn.boundary_pending:
            flags.add(RECONNECT_BOUNDARY)
            conn.boundary_pending = False
        stream_type = line.get("stream_type")
        duplicate = bool(line.get("duplicate"))
        if duplicate:
            flags.add(DUPLICATE)
        try:
            obj = load_message(line["raw"])
            if et == "orderbook":
                msg = parse_orderbook(obj)
                ev = MarketEvent.book_event(bids=[(u.bid_price, u.bid_size) for u in msg.units],
                                            asks=[(u.ask_price, u.ask_size) for u in msg.units],
                                            exchange_timestamp_ms=msg.exchange_timestamp_ms,
                                            stream_type=msg.stream_type, **base)
                ex, kind = msg.exchange_timestamp_ms, BOOK
            else:
                tr = parse_trade(obj)
                ev = MarketEvent(event_type=TRADE, exchange_timestamp_ms=tr.exchange_timestamp_ms,
                                 stream_type=tr.stream_type,
                                 trade=TradePrint(tr.trade_price, tr.trade_volume, tr.side, tr.sequential_id,
                                                  tr.trade_timestamp_ms), **base)
                ex, kind = tr.exchange_timestamp_ms, TRADE
        except UpbitParseError:  # verified datasets never get here; count instead of guessing
            stats.skipped[f"{et}_unparseable"] += 1
            lost_pending = True
            continue

        if not duplicate:
            if kind in last_ex and ex < last_ex[kind]:
                flags.add(TIMESTAMP_REVERSE)
            last_ex[kind] = max(ex, last_ex.get(kind, ex))
        if kind == BOOK:
            bb, ba = ev.best_bid, ev.best_ask
            if bb is not None and ba is not None:
                if bb > ba:
                    flags.add(CROSSED_BOOK)
                elif bb == ba:
                    flags.add(LOCKED_BOOK)
            if not duplicate:
                if conn.last_book is not None and recv - conn.last_book > params.stale_book_seconds:
                    flags.add(STALE_BOOK)
                conn.last_book = recv
                if stream_type == "REALTIME" and conn.first_realtime_book is None:
                    conn.first_realtime_book = recv
        if (stream_type == "SNAPSHOT" or conn.first_realtime_book is None
                or recv < conn.first_realtime_book + params.warmup_seconds):
            flags.add(WARMUP)
        yield _emit(ev.with_flags(*flags), stats)


def _emit(ev: MarketEvent, stats: ExportStats) -> MarketEvent:
    stats.events += 1
    stats.event_types[ev.event_type] += 1
    stats.flags.update(ev.flags)
    return ev


def export_events(dataset_dir: str | Path, out_path: str | Path,
                  params: ExportParams = ExportParams()) -> ExportStats:
    """Write every event as one JSON line into a gzip file (atomic; deterministic bytes)."""
    stats = ExportStats()
    header = {"schema": SCHEMA_EVENTS, "source": "upbit", "dataset": str(dataset_dir),
              "params": params.__dict__}
    with atomic_open(Path(out_path)) as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        gz.write((json.dumps({"header": header}, separators=(",", ":")) + "\n").encode())
        for ev in iter_market_events(dataset_dir, params, stats):
            gz.write((json.dumps(ev.to_dict(), separators=(",", ":")) + "\n").encode())
    return stats


def raw_manifest(dataset_dir: str | Path) -> dict[str, Any]:
    """sha256 + size of every raw file (dataset.json, state.json, segments). Read-only."""
    return raw_file_manifest(Path(dataset_dir))


def write_raw_manifest(dataset_dir: str | Path, out_path: str | Path) -> dict[str, Any]:
    manifest = raw_manifest(dataset_dir)
    atomic_write_json(Path(out_path), manifest)
    return manifest
