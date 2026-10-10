"""Data-quality report of an Upbit recording for research (offline, read-only).

Built from the same event stream the research export writes (research_export.iter_market_events),
so the counts here are exactly the flags the research layer will see. Complements
`verify_upbit_recording` (integrity: checksums, sequence, raw/summary agreement), which must pass
before a dataset is used for research.

"recv - timestamp" is a QUALITY figure only: it mixes the local clock offset, exchange-side
processing and network time, and the documented meaning of Upbit's `timestamp` is not specific
enough to call it latency. It is never a predictive feature.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from moneylab.domain.market_events import BOOK, CONNECTION, DISCONNECT, DUPLICATE, FAILURE, TRADE
from moneylab.providers.upbit.recorder.store import read_json
from moneylab.providers.upbit.research_export import ExportParams, ExportStats, iter_market_events

MAX_GAPS_LISTED = 20


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    k = (len(xs) - 1) * q
    lo = math.floor(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def _dist(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    return {"n": len(values), "mean": sum(values) / len(values), "p50": _pct(values, 0.5),
            "p95": _pct(values, 0.95), "p99": _pct(values, 0.99), "min": min(values), "max": max(values),
            "negative": sum(1 for v in values if v < 0)}


@dataclass
class UpbitQualityReport:
    path: Path
    market: str | None = None
    provenance: str | None = None
    synthetic: bool | None = None
    first_received: float | None = None
    last_received: float | None = None
    stream_types: Counter = field(default_factory=Counter)
    book_levels: Counter = field(default_factory=Counter)
    expected_units: int | None = None
    book_interarrival_ms: dict[str, Any] = field(default_factory=dict)
    recv_minus_exchange_ms: dict[str, dict[str, Any]] = field(default_factory=dict)
    gaps: list[dict[str, Any]] = field(default_factory=list)
    gap_count: int = 0
    export: ExportStats = field(default_factory=ExportStats)

    @property
    def duration_seconds(self) -> float | None:
        if self.first_received is None or self.last_received is None:
            return None
        return self.last_received - self.first_received

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path), "market": self.market, "provenance": self.provenance,
            "synthetic": self.synthetic, "first_received": self.first_received,
            "last_received": self.last_received, "duration_seconds": self.duration_seconds,
            "stream_types": dict(self.stream_types), "book_levels": {str(k): v for k, v in self.book_levels.items()},
            "expected_units": self.expected_units, "book_interarrival_ms": self.book_interarrival_ms,
            "recv_minus_exchange_ms": self.recv_minus_exchange_ms, "gap_count": self.gap_count,
            "gaps": self.gaps, "export": self.export.to_dict(),
            "note": "recv_minus_exchange_ms is a quality figure (clock offset + exchange + network), not latency",
        }


def quality_report(dataset_dir: str | Path, params: ExportParams = ExportParams(),
                   gap_seconds: float = 10.0) -> UpbitQualityReport:
    path = Path(dataset_dir)
    ds = read_json(path / "dataset.json")
    rep = UpbitQualityReport(path, market=ds.get("market"), provenance=ds.get("provenance"),
                             synthetic=ds.get("synthetic"), expected_units=ds.get("orderbook_units"))
    inter: list[float] = []
    lat: dict[str, list[float]] = {BOOK: [], TRADE: []}
    prev_book: float | None = None
    prev_any: float | None = None
    for ev in iter_market_events(path, params, rep.export):
        r = ev.received_timestamp
        rep.first_received = r if rep.first_received is None else rep.first_received
        rep.last_received = r
        if ev.event_type in (CONNECTION, DISCONNECT, FAILURE):
            prev_book = None  # inter-arrival only within a connection
        if prev_any is not None and r - prev_any > gap_seconds:
            rep.gap_count += 1
            if len(rep.gaps) < MAX_GAPS_LISTED:
                rep.gaps.append({"after": prev_any, "seconds": r - prev_any, "before_seq": ev.local_sequence})
        prev_any = r
        if not ev.is_market_data:
            continue
        rep.stream_types[f"{ev.event_type}:{ev.stream_type}"] += 1
        if DUPLICATE in ev.flags:
            continue
        if ev.event_type == BOOK:
            rep.book_levels[min(len(ev.bids), len(ev.asks))] += 1
            if prev_book is not None and ev.stream_type == "REALTIME":
                inter.append((r - prev_book) * 1000.0)
            prev_book = r
        if ev.stream_type == "REALTIME" and ev.exchange_timestamp_ms is not None:
            lat[ev.event_type].append(r * 1000.0 - ev.exchange_timestamp_ms)
    rep.book_interarrival_ms = _dist(inter)
    rep.recv_minus_exchange_ms = {"book": _dist(lat[BOOK]), "trade": _dist(lat[TRADE])}
    return rep
