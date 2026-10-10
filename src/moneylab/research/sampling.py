"""1 s wall-clock grid on the local receive clock, built in one forward pass (no look-ahead).

Row k sits at t_k = ceil(start) + k * grid_seconds. For every row the replayer is advanced to
t_k (features, reasons, book_age) and to t_k + delay for each execution delay (entry/exit VWAPs
used by executable labels). Sample times only increase, so nothing received after a sample time
can influence it.

Discontinuity: a row whose reasons include no_book/gap/warmup, or whose break counter differs
from the previous row (a reconnect or a lost message in between). A feature with lookback L at
row k is NaN unless rows k-L..k contain no discontinuity.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field

from moneylab.analytics.metrics import vwap_fill
from moneylab.domain.market_events import MarketEvent
from moneylab.research.book_state import DISCONTINUITY, AsOfReplayer, StateParams
from moneylab.research.features import (
    FEATURES,
    MAX_TRADE_LOOKBACK,
    NAN,
    REGISTRY,
    book_features,
    series_features,
    trade_features,
)


@dataclass(frozen=True)
class GridParams:
    grid_seconds: float = 1.0
    warmup_seconds: float = 5.0
    stale_book_seconds: float = 1.0
    gap_seconds: float = 10.0
    delays_ms: tuple[int, ...] = (0, 100, 250)
    sizes_btc: tuple[float, ...] = (0.001, 0.01)

    def __post_init__(self):
        if self.grid_seconds <= 0 or abs(1 / self.grid_seconds - round(1 / self.grid_seconds)) > 1e-9:
            raise ValueError("grid_seconds must divide one second (1, 0.5, 0.25, ...)")
        if 0 not in self.delays_ms or min(self.delays_ms) < 0:
            raise ValueError("delays_ms must contain 0 and be >= 0")
        if max(self.delays_ms) / 1000 >= self.grid_seconds:
            raise ValueError("every delay must be shorter than one grid step")

    @property
    def rows_per_second(self) -> int:
        return round(1 / self.grid_seconds)


@dataclass
class ExecSamples:
    """Book as known at t_k + delay, for every row k."""

    ok: list[bool] = field(default_factory=list)
    breaks: list[int] = field(default_factory=list)
    vwap_ask: dict[float, list[float]] = field(default_factory=dict)  # size -> per row
    vwap_bid: dict[float, list[float]] = field(default_factory=dict)


@dataclass
class Grid:
    params: GridParams
    times: list[float] = field(default_factory=list)
    reasons: list[frozenset[str]] = field(default_factory=list)
    book_age: list[float] = field(default_factory=list)
    breaks: list[int] = field(default_factory=list)
    cols: dict[str, list[float]] = field(default_factory=dict)
    exec: dict[int, ExecSamples] = field(default_factory=dict)  # delay_ms -> samples
    _disc_prefix: list[int] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.times)

    def is_discontinuity(self, k: int) -> bool:
        return bool(self.reasons[k] & DISCONTINUITY) or (k > 0 and self.breaks[k] != self.breaks[k - 1])

    def finalize_index(self) -> None:
        self._disc_prefix = [0]
        for k in range(len(self)):
            self._disc_prefix.append(self._disc_prefix[-1] + self.is_discontinuity(k))

    def clean(self, lo: int, hi: int) -> bool:
        """No discontinuity in rows lo..hi (inclusive)."""
        if lo < 0 or hi >= len(self):
            return False
        return self._disc_prefix[hi + 1] == self._disc_prefix[lo]

    def window_ok(self, k: int, lookback_rows: int) -> bool:
        return self.clean(k - lookback_rows, k)

    def lookback_rows(self, seconds: float) -> int:
        return math.ceil(seconds * self.params.rows_per_second - 1e-9)


def _vwap(levels, size: float) -> float:
    v = vwap_fill(levels, size)
    return NAN if v is None else v


def build_grid(events: Iterable[MarketEvent], start: float, end: float, params: GridParams = GridParams()) -> Grid:
    """`start`/`end`: first and last availability time of the events (receive clock)."""
    g = params.grid_seconds
    state = AsOfReplayer(events, StateParams(params.warmup_seconds, params.stale_book_seconds, params.gap_seconds,
                                             trade_memory_seconds=MAX_TRADE_LOOKBACK + 1.0))
    grid = Grid(params)
    names = [f.name for f in FEATURES if f.kind in ("book", "trade")]
    grid.cols = {n: [] for n in names}
    delays = sorted(params.delays_ms)
    grid.exec = {d: ExecSamples(vwap_ask={q: [] for q in params.sizes_btc}, vwap_bid={q: [] for q in params.sizes_btc})
                 for d in delays}
    t0 = math.ceil(start / g) * g
    n = int(math.floor((end - t0) / g + 1e-9)) + 1 if end >= t0 else 0
    for k in range(n):
        t = t0 + k * g
        for d in delays:
            a = state.advance_to(t + d / 1000.0)
            book = a.book
            ex = grid.exec[d]
            ex.ok.append(a.ok)
            ex.breaks.append(a.break_counter)
            for q in params.sizes_btc:
                ex.vwap_ask[q].append(_vwap(book.asks, q) if book is not None else NAN)
                ex.vwap_bid[q].append(_vwap(book.bids, q) if book is not None else NAN)
            if d != 0:
                continue
            grid.times.append(t)
            grid.reasons.append(a.reasons)
            grid.breaks.append(a.break_counter)
            grid.book_age.append(NAN if a.book_age is None else a.book_age)
            bf = book_features(book.bids, book.asks) if book is not None else {}
            tf = trade_features(a.trades, t)
            for name in names:
                grid.cols[name].append(bf.get(name, tf.get(name, NAN)))
    grid.finalize_index()
    _apply_lookbacks(grid)
    return grid


def _apply_lookbacks(grid: Grid) -> None:
    """NaN every lookback>0 value whose window crosses a discontinuity; add series features."""
    for f in FEATURES:
        if f.kind == "trade":
            L = grid.lookback_rows(f.lookback_seconds)
            col = grid.cols[f.name]
            for k in range(len(grid)):
                if not grid.window_ok(k, L):
                    col[k] = NAN
    grid.cols.update(series_features(grid.cols["mid_price"], grid.window_ok, grid.params.rows_per_second))
    assert set(grid.cols) == set(REGISTRY)
