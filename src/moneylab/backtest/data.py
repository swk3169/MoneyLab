"""Bar series and the look-ahead-safe view (docs/backtest_design.md section 4).

* `inspect_bars` sorts bars and reports identical / conflicting duplicates and missing buckets.
  Missing buckets are normal (the exchange omits buckets without trades) and are never filled.
* `BarSeries.build` refuses duplicates, mixed markets or intervals, and a provenance whose SHA-256
  does not match the bars. `verify()` recomputes the SHA-256 before every backtest.
* `AsOfView(series, t)` holds ONLY the bars a decision at time t may use: bucket ended and
  confirmed (end_utc + confirm_delay <= t), and t capped by an optional horizon. It keeps a copy of
  those bars and no reference to the series, so later bars are not reachable through it.
"""

from __future__ import annotations

import bisect
import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from moneylab.domain.bars import INTERVALS, Bar, BarProvenance, require_utc

# Upbit confirmation rule (CLAUDE.md, v0.6 draft section 4): a bucket is final 120 s after its end.
CONFIRM_DELAY = timedelta(seconds=120)


class DataIntegrityError(ValueError):
    """Bars and their recorded SHA-256 / provenance disagree, or the series is malformed."""


class DuplicateBarError(DataIntegrityError):
    """Two bars share a start time."""


class LookAheadError(ValueError):
    """A request for data the decision time may not see."""


def bars_sha256(bars: Iterable[Bar]) -> str:
    """SHA-256 of the canonical JSONL rows of the bars in start order (one row per bar, LF)."""
    rows = sorted(bars, key=lambda b: b.start_utc)
    body = "".join(json.dumps(b.to_record(), sort_keys=True, separators=(",", ":")) + "\n" for b in rows)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def provenance_for(bars: Sequence[Bar], kind: str, description: str) -> BarProvenance:
    return BarProvenance(kind=kind, description=description, bars_sha256=bars_sha256(bars))


@dataclass(frozen=True)
class QualityReport:
    bars: tuple[Bar, ...]  # sorted, first copy of each start time kept
    identical_duplicates: int
    conflicting_duplicates: tuple[datetime, ...]
    gaps: tuple[tuple[datetime, int], ...]  # (first missing start, number of missing buckets)

    @property
    def missing_buckets(self) -> int:
        return sum(n for _, n in self.gaps)


def inspect_bars(bars: Iterable[Bar]) -> QualityReport:
    rows = sorted(bars, key=lambda b: b.start_utc)
    kept: list[Bar] = []
    identical = 0
    conflicting: list[datetime] = []
    for b in rows:
        if kept and kept[-1].start_utc == b.start_utc:
            if kept[-1] == b:
                identical += 1
            else:
                conflicting.append(b.start_utc)
            continue
        kept.append(b)
    gaps: list[tuple[datetime, int]] = []
    if kept:
        step = INTERVALS[kept[0].interval]
        for prev, cur in zip(kept, kept[1:]):
            missing = int((cur.start_utc - prev.start_utc) / step) - 1
            if missing > 0:
                gaps.append((prev.start_utc + step, missing))
    return QualityReport(tuple(kept), identical, tuple(conflicting), tuple(gaps))


class BarSeries:
    """Immutable, sorted bars of one market and interval, tied to a provenance SHA-256."""

    __slots__ = ("_bars", "_starts", "_ends", "provenance", "market", "interval", "gaps")

    def __init__(self, *args, **kwargs):  # noqa: ARG002
        raise TypeError("use BarSeries.build(bars, provenance)")

    @classmethod
    def build(cls, bars: Iterable[Bar], provenance: BarProvenance) -> BarSeries:
        report = inspect_bars(bars)
        if not report.bars:
            raise DataIntegrityError("no bars")
        if report.identical_duplicates or report.conflicting_duplicates:
            raise DuplicateBarError(f"duplicate bars: {report.identical_duplicates} identical, "
                                    f"{len(report.conflicting_duplicates)} conflicting "
                                    f"(first conflicting start: {report.conflicting_duplicates[:1]})")
        first = report.bars[0]
        if any(b.market != first.market or b.interval != first.interval for b in report.bars):
            raise DataIntegrityError("bars of more than one market or interval")
        if bars_sha256(report.bars) != provenance.bars_sha256:
            raise DataIntegrityError("bars do not match the provenance SHA-256")
        self = object.__new__(cls)
        set_ = object.__setattr__
        set_(self, "_bars", report.bars)
        set_(self, "_starts", tuple(b.start_utc for b in report.bars))
        set_(self, "_ends", tuple(b.end_utc for b in report.bars))
        set_(self, "provenance", provenance)
        set_(self, "market", first.market)
        set_(self, "interval", first.interval)
        set_(self, "gaps", report.gaps)
        return self

    def __setattr__(self, name, value):
        raise AttributeError("BarSeries is immutable")

    def __delattr__(self, name):
        raise AttributeError("BarSeries is immutable")

    def __len__(self) -> int:
        return len(self._bars)

    @property
    def bars(self) -> tuple[Bar, ...]:
        return self._bars

    @property
    def first_start(self) -> datetime:
        return self._starts[0]

    @property
    def last_end(self) -> datetime:
        return self._ends[-1]

    def verify(self) -> None:
        """Recompute the SHA-256 (catches bars altered after build, e.g. through object.__setattr__)."""
        if bars_sha256(self._bars) != self.provenance.bars_sha256:
            raise DataIntegrityError(f"{self.market} {self.interval}: bars no longer match the provenance SHA-256")

    def at_start(self, start: datetime) -> Bar | None:
        """The bar of one bucket, or None if the bucket is missing. Used for fills and valuation,
        never as a decision input (decisions read an AsOfView)."""
        require_utc(start, "start")
        i = bisect.bisect_left(self._starts, start)
        return self._bars[i] if i < len(self._bars) and self._starts[i] == start else None

    def last_ended_by(self, t: datetime) -> Bar | None:
        """Latest bar whose bucket ended at or before t (valuation fallback, draft 6.3)."""
        require_utc(t, "t")
        i = bisect.bisect_right(self._ends, t)
        return self._bars[i - 1] if i else None

    def visible_count(self, t: datetime, confirm_delay: timedelta = CONFIRM_DELAY) -> int:
        require_utc(t, "t")
        return bisect.bisect_right(self._ends, t - confirm_delay)


class AsOfView:
    """What a decision at `as_of` may read: confirmed bars only, never anything after `as_of`
    (or after `horizon`, the end of the evaluation segment, if that is earlier)."""

    __slots__ = ("_bars", "as_of", "market", "interval")

    def __init__(self, series: BarSeries, as_of: datetime, *, horizon: datetime | None = None,
                 confirm_delay: timedelta = CONFIRM_DELAY):
        require_utc(as_of, "as_of")
        cutoff = as_of
        if horizon is not None:
            cutoff = min(cutoff, require_utc(horizon, "horizon"))
        n = series.visible_count(cutoff, confirm_delay)
        set_ = object.__setattr__
        set_(self, "_bars", series.bars[:n])
        set_(self, "as_of", cutoff)
        set_(self, "market", series.market)
        set_(self, "interval", series.interval)

    def __setattr__(self, name, value):
        raise AttributeError("AsOfView is immutable")

    def __delattr__(self, name):
        raise AttributeError("AsOfView is immutable")

    def __len__(self) -> int:
        return len(self._bars)

    def latest(self) -> Bar | None:
        return self._bars[-1] if self._bars else None

    def last(self, n: int) -> tuple[Bar, ...]:
        """The latest n visible bars, oldest first (fewer if fewer are visible)."""
        if n < 0:
            raise ValueError("n must be >= 0")
        return self._bars[max(0, len(self._bars) - n):] if n else ()
