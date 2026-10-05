"""Expected-value calculator for binary outcome shares (pure functions).

All results separate trading EV (after fees and slippage) from *estimated* incentives
(maker rebate, liquidity reward). Strategy decisions use `net_trading_ev` only; incentives
are reported next to it but never needed for a positive decision.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from moneylab.analytics.costs import fee_equivalent, maker_fee, taker_fee_for_fills
from moneylab.analytics.metrics import walk_book
from moneylab.domain.market_params import FeeSchedule


@dataclass(frozen=True)
class TakerEV:
    shares: float  # shares actually fillable (<= requested)
    vwap: float | None
    gross_edge: float  # shares * (fair - vwap) for buys; before fees
    slippage: float  # shares * |vwap - best|, already inside gross_edge
    fees: float
    net_trading_ev: float  # gross_edge - fees

    @property
    def net_ev_per_share(self) -> float:
        return self.net_trading_ev / self.shares if self.shares > 0 else 0.0


def taker_ev(
    fair_prob: float,
    levels: Sequence,
    shares: float,
    side: Literal["buy", "sell"],
    schedule: FeeSchedule,
    limit_price: float | None = None,
) -> TakerEV:
    """EV of taking `shares` of an outcome token whose fair probability is `fair_prob`.

    buy  consumes asks: gross = sum q * (fair - price)
    sell consumes bids: gross = sum q * (price - fair)
    """
    if not 0 <= fair_prob <= 1:
        raise ValueError("fair_prob must be in [0, 1]")
    fills = walk_book(levels, shares, limit_price, side)
    filled = sum(q for _, q in fills)
    if filled <= 0:
        return TakerEV(0.0, None, 0.0, 0.0, 0.0, 0.0)
    vwap = sum(p * q for p, q in fills) / filled
    sign = 1.0 if side == "buy" else -1.0
    gross = sign * sum(q * (fair_prob - p) for p, q in fills)
    best = fills[0][0]
    slip = sign * (vwap - best) * filled
    fees = taker_fee_for_fills(fills, schedule)
    return TakerEV(filled, vwap, gross, slip, fees, gross - fees)


def all_in_price(price: float, shares: float, schedule: FeeSchedule) -> float:
    """Per-share buy cost including the taker fee at that price."""
    if shares <= 0:
        return price
    return price + taker_fee_for_fills([(price, shares)], schedule) / shares


@dataclass(frozen=True)
class MakerEV:
    net_trading_ev: float  # fill_prob * shares * (edge - adverse_selection) - maker fees
    estimated_rebate: float
    estimated_reward: float

    @property
    def all_in_estimated_ev(self) -> float:
        """For information only. Never use this alone to adopt a strategy."""
        return self.net_trading_ev + self.estimated_rebate + self.estimated_reward


def maker_ev(
    fair_prob: float,
    price: float,
    shares: float,
    side: Literal["buy", "sell"],
    fill_prob: float,
    schedule: FeeSchedule,
    adverse_selection: float = 0.0,
    estimated_reward: float = 0.0,
) -> MakerEV:
    """EV of a resting order.

    adverse_selection: expected move of fair value against you *conditional on being filled*
    (per share, >= 0). Ignoring it overstates maker EV.
    """
    if not 0 <= fill_prob <= 1:
        raise ValueError("fill_prob must be in [0, 1]")
    edge = (fair_prob - price) if side == "buy" else (price - fair_prob)
    trading = fill_prob * (shares * (edge - adverse_selection) - maker_fee(shares, price, schedule))
    rebate = fill_prob * schedule.rebate_rate * fee_equivalent(shares, price, schedule) if schedule.enabled else 0.0
    return MakerEV(trading, rebate, estimated_reward)
