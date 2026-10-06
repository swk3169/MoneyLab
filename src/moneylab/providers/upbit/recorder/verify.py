"""Recorder -> replay consistency check for an Upbit recording (offline).

Three views of every non-duplicate orderbook / trade message are compared:
  1. "original": values computed directly from the stored raw JSON with plain dict access
     (independent of providers.upbit.parser),
  2. "stored": the derived summary the recorder wrote next to the raw message,
  3. "replay": what UpbitRecordingReader -> ReplayBookStream yields (rebuilt OrderBook / TradeTick).
It also reports timing facts of the data. "Receive latency" = received_timestamp - exchange
`timestamp` over REALTIME messages; it includes any offset between the local clock and the
exchange clock, so it is an upper-level observation, not a pure network latency.
"""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from moneylab.paper.book_stream import ReplayBookStream
from moneylab.providers.upbit.recorder.replay import UpbitRecordingReader

MAX_MISMATCHES = 50


def _close(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is b
    return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)


def _original_book(raw: dict[str, Any]) -> dict[str, Any]:
    units = raw["orderbook_units"]
    bids = [(u["bid_price"], u["bid_size"]) for u in units if u["bid_size"] > 0]
    asks = [(u["ask_price"], u["ask_size"]) for u in units if u["ask_size"] > 0]
    bb = max((p for p, _ in bids), default=None)
    ba = min((p for p, _ in asks), default=None)
    return {"best_bid": bb, "best_ask": ba, "spread": None if bb is None or ba is None else ba - bb,
            "bid_depth": sum(s for _, s in bids), "ask_depth": sum(s for _, s in asks)}


def _stats(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    vs = sorted(values)
    return {"n": len(vs), "mean": statistics.fmean(vs), "median": statistics.median(vs), "min": vs[0],
            "p95": vs[min(len(vs) - 1, int(0.95 * (len(vs) - 1) + 0.5))], "max": vs[-1]}


@dataclass
class ReplayCheckReport:
    path: Path
    provenance: str | None = None
    synthetic: bool | None = None
    market: str | None = None
    counts: dict[str, int] = field(default_factory=dict)
    mismatches: list[str] = field(default_factory=list)
    first_exchange_ms: int | None = None
    last_exchange_ms: int | None = None
    first_received: float | None = None
    last_received: float | None = None
    latency_ms: dict[str, Any] = field(default_factory=dict)
    examples: dict[str, Any] = field(default_factory=dict)
    replay_stats: dict[str, int] = field(default_factory=dict)
    reader_stats: dict[str, int] = field(default_factory=dict)
    units_histogram: dict[int, int] = field(default_factory=dict)
    stream_types: dict[str, int] = field(default_factory=dict)
    size_bytes: int = 0

    @property
    def ok(self) -> bool:
        c = self.counts
        return (not self.mismatches and c.get("compared_orderbooks", 0) == c.get("original_orderbooks", 0)
                and c.get("compared_trades", 0) == c.get("original_trades", 0))

    def to_dict(self) -> dict[str, Any]:
        return {k: (str(v) if isinstance(v, Path) else v) for k, v in self.__dict__.items()} | {"ok": self.ok}


def replay_check(path: str | Path) -> ReplayCheckReport:
    path = Path(path)
    reader = UpbitRecordingReader(path)
    rep = ReplayCheckReport(path, reader.provenance, reader.synthetic, reader.market)
    c = rep.counts

    def bump(k: str, n: int = 1) -> None:
        c[k] = c.get(k, 0) + n

    def mismatch(msg: str) -> None:
        bump("mismatches")
        if len(rep.mismatches) < MAX_MISMATCHES:
            rep.mismatches.append(msg)

    originals: dict[int, tuple[str, dict[str, Any], dict[str, Any]]] = {}
    lat: dict[str, list[float]] = {"orderbook": [], "trade": []}
    for ln in reader.iter_lines():
        et, seq, recv = ln["event_type"], int(ln["local_sequence"]), float(ln["received_timestamp"])
        bump(f"lines_{et}")
        rep.first_received = recv if rep.first_received is None else rep.first_received
        rep.last_received = recv
        if et not in ("orderbook", "trade") or ln.get("duplicate") or ln.get("parse_error"):
            continue
        raw = json.loads(ln["raw"])
        ex = int(raw["timestamp"])
        rep.first_exchange_ms = ex if rep.first_exchange_ms is None else min(rep.first_exchange_ms, ex)
        rep.last_exchange_ms = ex if rep.last_exchange_ms is None else max(rep.last_exchange_ms, ex)
        st = str(raw.get("stream_type"))
        if st == "REALTIME":  # a SNAPSHOT re-sends old state on connect: not a latency sample
            lat[et].append(recv * 1000.0 - ex)
        rep.stream_types[f"{et}:{st}"] = rep.stream_types.get(f"{et}:{st}", 0) + 1
        if et == "orderbook":
            bump("original_orderbooks")
            orig = _original_book(raw)
            n = len(raw["orderbook_units"])
            rep.units_histogram[n] = rep.units_histogram.get(n, 0) + 1
            stored = ln.get("orderbook") or {}
            for k, v in orig.items():
                if not _close(v, stored.get(k)):
                    mismatch(f"seq {seq}: stored {k}={stored.get(k)} != original {v}")
            orig.update(exchange_ms=ex, received=recv, level=raw.get("level"), units=n)
        else:
            bump("original_trades")
            orig = {"sequential_id": raw["sequential_id"], "trade_price": raw["trade_price"],
                    "trade_volume": raw["trade_volume"], "ask_bid": raw["ask_bid"],
                    "trade_timestamp": raw["trade_timestamp"], "exchange_ms": ex, "received": recv}
            stored = ln.get("trade") or {}
            for k in ("sequential_id", "trade_price", "trade_volume", "ask_bid"):
                if stored.get(k) != orig[k]:
                    mismatch(f"seq {seq}: stored {k}={stored.get(k)} != original {orig[k]}")
        originals[seq] = (et, orig, raw)
        rep.examples.setdefault(f"first_{et}", {"local_sequence": seq, **orig})
        rep.examples[f"last_{et}"] = {"local_sequence": seq, **orig}

    stream = ReplayBookStream(reader)
    seen: set[int] = set()
    prev_key: tuple[float, float, int] | None = None
    for ev in stream:
        if ev.error is not None:
            bump("replay_error_events")
            continue
        seq = ev.local_sequence
        if seq is None or seq not in originals:
            mismatch(f"replay event {seq} has no original market line")
            continue
        key = (ev.timestamp, ev.received_timestamp or 0.0, seq)
        if prev_key is not None and key < prev_key:
            mismatch(f"replay order broken at seq {seq}")
        prev_key = key
        seen.add(seq)
        et, orig, _ = originals[seq]
        if not _close(ev.timestamp, orig["exchange_ms"] / 1000.0) or not _close(ev.received_timestamp, orig["received"]):
            mismatch(f"seq {seq}: replay timestamps differ from original")
        if et == "orderbook":
            bump("compared_orderbooks")
            if ev.snapshot is None or len(ev.snapshot.books) != 1:
                mismatch(f"seq {seq}: replay produced no single book")
                continue
            book = next(iter(ev.snapshot.books.values()))
            got = {"best_bid": book.best_bid, "best_ask": book.best_ask, "spread": book.spread,
                   "bid_depth": sum(lv.size for lv in book.bids), "ask_depth": sum(lv.size for lv in book.asks)}
            for k, v in got.items():
                if not _close(v, orig[k]):
                    mismatch(f"seq {seq}: replay {k}={v} != original {orig[k]}")
        else:
            bump("compared_trades")
            if len(ev.trades) != 1:
                mismatch(f"seq {seq}: replay produced {len(ev.trades)} trades")
                continue
            t = ev.trades[0]
            side = {"ASK": "sell", "BID": "buy"}[orig["ask_bid"]]
            if (t.trade_id != orig["sequential_id"] or not _close(t.price, orig["trade_price"])
                    or not _close(t.volume, orig["trade_volume"]) or t.side != side
                    or not _close(t.exchange_timestamp, orig["trade_timestamp"] / 1000.0)):
                mismatch(f"seq {seq}: replay trade {t} != original {orig}")
    missing = sorted(set(originals) - seen)
    if missing:
        mismatch(f"{len(missing)} original market events missing from replay (first: {missing[:5]})")
    rep.replay_stats = dict(stream.stats.__dict__)
    rep.reader_stats = dict(reader.stats.__dict__)
    rep.latency_ms = {"orderbook": _stats(lat["orderbook"]), "trade": _stats(lat["trade"]),
                      "all": _stats(lat["orderbook"] + lat["trade"])}
    rep.size_bytes = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    return rep
