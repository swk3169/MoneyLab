"""Provider-neutral OHLCV bars for spot backtests (docs/backtest_design.md section 4).

A Bar is one closed time bucket [start_utc, end_utc) of one market. Times are UTC and must be
timezone-aware; prices are Decimal so no precision is lost between the stored candle and the
backtest. Bars are immutable (frozen, slotted). Converting a provider candle into a Bar is the
provider's job (planned: providers/upbit/bar_export.py); nothing here imports a provider.

BarProvenance says where a set of bars came from. Only kind "real" can ever be evidence; "fixture"
and "synthetic" results are SYNTHETIC / NOT_EVIDENCE.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

INTERVALS: dict[str, timedelta] = {"day": timedelta(days=1), "hour": timedelta(hours=1)}
PROVENANCE_KINDS = ("real", "fixture", "synthetic")
NOT_EVIDENCE = "SYNTHETIC / NOT_EVIDENCE"


def require_utc(t: datetime, name: str) -> datetime:
    """Reject naive datetimes and non-UTC offsets (a silent local-time bar would shift every signal)."""
    if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must be a timezone-aware UTC datetime, got {t!r}")
    return t


def utc_iso(t: datetime) -> str:
    return require_utc(t, "t").strftime("%Y-%m-%dT%H:%M:%SZ")


def is_aligned(t: datetime, interval: str) -> bool:
    if t.minute or t.second or t.microsecond:
        return False
    return interval != "day" or t.hour == 0


@dataclass(frozen=True, slots=True)
class Bar:
    market: str
    interval: str
    start_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    value_krw: Decimal  # accumulated traded value of the bucket (quote currency)
    volume: Decimal  # accumulated traded quantity of the bucket (base currency)
    last_tick_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.market:
            raise ValueError("market is empty")
        if self.interval not in INTERVALS:
            raise ValueError(f"unknown interval {self.interval!r}")
        require_utc(self.start_utc, "start_utc")
        if not is_aligned(self.start_utc, self.interval):
            raise ValueError(f"{self.interval} bar start {self.start_utc} is not aligned")
        for name in ("open", "high", "low", "close", "value_krw", "volume"):
            v = getattr(self, name)
            if not isinstance(v, Decimal) or not v.is_finite():
                raise ValueError(f"{name} must be a finite Decimal, got {v!r}")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("prices must be positive")
        if not (self.low <= min(self.open, self.close) and max(self.open, self.close) <= self.high):
            raise ValueError("inconsistent OHLC (low <= open, close <= high violated)")
        if self.value_krw < 0 or self.volume < 0:
            raise ValueError("negative traded value or volume")

    @property
    def end_utc(self) -> datetime:
        return self.start_utc + INTERVALS[self.interval]

    def to_record(self) -> dict[str, Any]:
        """Canonical JSON-safe row (Decimals as strings). The bar SHA-256 is computed over these rows."""
        return {"market": self.market, "interval": self.interval, "start_utc": utc_iso(self.start_utc),
                "open": str(self.open), "high": str(self.high), "low": str(self.low), "close": str(self.close),
                "value_krw": str(self.value_krw), "volume": str(self.volume), "last_tick_ms": self.last_tick_ms}


def canonical_bar_rows(bars: Iterable[Bar]) -> bytes:
    """The canonical bytes of a set of bars: one JSON row per bar (`Bar.to_record`, sorted keys,
    separators "," and ":"), in start order, each row ended by LF, UTF-8. Bar files written by the
    exporter are exactly these bytes, so their file SHA-256 equals `bars_sha256`."""
    rows = sorted(bars, key=lambda b: b.start_utc)
    return "".join(json.dumps(b.to_record(), sort_keys=True, separators=(",", ":")) + "\n"
                   for b in rows).encode("utf-8")


def bars_sha256(bars: Iterable[Bar]) -> str:
    """Content hash of a set of bars (order of the input does not matter): SHA-256 of canonical_bar_rows."""
    return hashlib.sha256(canonical_bar_rows(bars)).hexdigest()


@dataclass(frozen=True, slots=True)
class BarProvenance:
    kind: str  # one of PROVENANCE_KINDS
    description: str  # e.g. generator and seed, or pull IDs with their page SHA-256
    bars_sha256: str  # SHA-256 of the canonical bar rows (backtest.data.bars_sha256)

    def __post_init__(self) -> None:
        if self.kind not in PROVENANCE_KINDS:
            raise ValueError(f"unknown provenance kind {self.kind!r}")
        if len(self.bars_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.bars_sha256):
            raise ValueError("bars_sha256 must be 64 lowercase hex characters")

    @property
    def evidence(self) -> str:
        return "REAL (evidence level set by the study)" if self.kind == "real" else NOT_EVIDENCE
