"""Spot taker round-trip costs (pure functions, no exchange-specific constants).

The fee rate is ALWAYS a parameter: the account fee of an exchange is not hard-coded anywhere.
Research scenarios come from configs/research_v04.toml (5 / 15 / 25 bp per side by default).

Round trip, size Q, fee f per side (fraction), entry/exit VWAPs from the order book:
  buy  then sell:  net = bid_exit * (1 - f) / (ask_entry * (1 + f)) - 1
  sell then buy :  net = bid_entry * (1 - f) / (ask_exit * (1 + f)) - 1   (inventory round trip; spot has no short)
Executable labels store the pre-fee ratio; `apply_fee_bps` turns it into the net return.
Decomposition used for reporting (additive approximation, small returns):
  cost ~= spread + entry slippage + exit slippage + 2 * fee   (+ adverse move during the delay)
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from moneylab.analytics.metrics import vwap_fill


@dataclass(frozen=True)
class CostScenario:
    fee_bps: float  # per side
    size: float
    delay_ms: int = 0

    def __post_init__(self):
        if self.fee_bps < 0 or self.size <= 0 or self.delay_ms < 0:
            raise ValueError("fee_bps >= 0, size > 0, delay_ms >= 0 required")

    @property
    def label(self) -> str:
        return f"fee{self.fee_bps:g}bp_q{self.size:g}_d{self.delay_ms}ms"


def scenarios(fees_bps: Iterable[float], sizes: Iterable[float], delays_ms: Iterable[int]) -> list[CostScenario]:
    return [CostScenario(f, q, d) for f in fees_bps for q in sizes for d in delays_ms]


def apply_fee_bps(pre_fee_bps: float, fee_bps: float) -> float:
    """Net round-trip return in bp after paying `fee_bps` on both legs (multiplicative)."""
    if fee_bps < 0:
        raise ValueError("fee_bps must be >= 0")
    if math.isnan(pre_fee_bps):
        return math.nan
    f = fee_bps / 1e4
    return 1e4 * ((1.0 + pre_fee_bps / 1e4) * (1.0 - f) / (1.0 + f) - 1.0)


def round_trip_bps(entry_price: float, exit_price: float, side: str, fee_bps: float = 0.0) -> float:
    """side 'buy': pay entry (ask VWAP), receive exit (bid VWAP); 'sell': receive entry (bid), pay exit (ask)."""
    if not (entry_price > 0 and exit_price > 0):
        return math.nan
    if side == "buy":
        pre = 1e4 * (exit_price / entry_price - 1.0)
    elif side == "sell":
        pre = 1e4 * (entry_price / exit_price - 1.0)
    else:
        raise ValueError("side must be 'buy' or 'sell'")
    return apply_fee_bps(pre, fee_bps)


def slippage_bps(levels: Sequence[tuple[float, float]], size: float) -> float:
    """Distance of the VWAP for `size` from the best level, in bp of the best price (>= 0).
    NaN when the visible levels cannot fill `size`."""
    if not levels:
        return math.nan
    vwap = vwap_fill(levels, size)
    if vwap is None:
        return math.nan
    best = levels[0][0]
    return 1e4 * abs(vwap - best) / best


def round_trip_cost_bps(spread_bps: float, entry_slippage_bps: float, exit_slippage_bps: float,
                        fee_bps: float) -> float:
    """Additive estimate of a taker round trip at an unchanged mid: spread + slippage + 2 fees."""
    return spread_bps + entry_slippage_bps + exit_slippage_bps + 2.0 * fee_bps
