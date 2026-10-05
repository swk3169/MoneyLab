"""Liquidity reward scoring model (pure functions).

Source: Polymarket docs "Liquidity Rewards" (checked 2026-10-04):
  S(v, s)  = ((v - s) / v)^2 * b                      v = max spread (cents), s = spread from
                                                       the size-cutoff-adjusted midpoint (cents)
  Q_one    = sum S * BidSize(m)  + sum S * AskSize(m')    m' = complement token
  Q_two    = sum S * AskSize(m)  + sum S * BidSize(m')
  Q_min    = max(min(Q_one, Q_two), max(Q_one / c, Q_two / c))   if mid in [0.10, 0.90]
           = min(Q_one, Q_two)                                    otherwise
  Q_normal = Q_min / sum over makers of Q_min           (per sample, once per minute)
  Q_epoch  = sum of Q_normal over up to 1,440 samples   (one UTC day)
  reward   = Q_epoch / sum over makers of Q_epoch * market daily reward

WHAT IS NOT KNOWABLE OFFLINE: the other makers' individual Q_min. Every reward computed with
an assumed competitor score is an ESTIMATE and must stay out of realized PnL.

Interpretations (unverified):
  * "size-cutoff-adjusted midpoint": midpoint of the best bid/ask after ignoring levels whose
    size is below the reward min size (`adjusted_midpoint`).
  * Orders below `min_size` do not score; orders at s >= v score 0.
  * Competitor score: visible book levels within v are aggregated as one competitor. The book
    shows per-level totals, not per-order sizes, so this can over- or under-state competition.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from moneylab.domain.market_params import RewardConfig

SAMPLES_PER_EPOCH = 1440
TWO_SIDED_ONLY_BELOW = 0.10
TWO_SIDED_ONLY_ABOVE = 0.90


@dataclass(frozen=True)
class RewardOrder:
    """A resting order as seen by the reward scorer.

    complement=False -> order on market m (e.g. YES); True -> on m' (e.g. NO).
    """

    side: Literal["bid", "ask"]
    price: float
    size: float
    complement: bool = False


def order_score(max_spread_cents: float, spread_cents: float, multiplier: float = 1.0) -> float:
    """S(v, s). 0 outside [0, v)."""
    if max_spread_cents <= 0 or spread_cents < 0 or spread_cents >= max_spread_cents:
        return 0.0
    return ((max_spread_cents - spread_cents) / max_spread_cents) ** 2 * multiplier


def adjusted_midpoint(bids: Sequence, asks: Sequence, min_size: float) -> float | None:
    """Mid of the best bid/ask levels with size >= min_size (interpretation, see module doc)."""
    def best(levels):
        for lvl in levels:
            price, size = (lvl.price, lvl.size) if hasattr(lvl, "price") else lvl
            if size >= min_size:
                return price
        return None

    b, a = best(bids), best(asks)
    if b is None or a is None:
        return None
    return (b + a) / 2


def side_scores(orders: Iterable[RewardOrder], mid_m: float, config: RewardConfig) -> tuple[float, float]:
    """(Q_one, Q_two) for one maker's orders. mid_m is the adjusted midpoint of market m."""
    q_one = q_two = 0.0
    for o in orders:
        if o.size < config.min_size:
            continue
        mid = (1.0 - mid_m) if o.complement else mid_m
        s_cents = abs(o.price - mid) * 100
        score = order_score(config.max_spread_cents, s_cents, config.in_game_multiplier) * o.size
        # Q_one: bids on m + asks on m'.  Q_two: asks on m + bids on m'.
        if (o.side == "bid") != o.complement:
            q_one += score
        else:
            q_two += score
    return q_one, q_two


def q_min(q_one: float, q_two: float, mid_m: float, c: float = 3.0) -> float:
    if TWO_SIDED_ONLY_BELOW <= mid_m <= TWO_SIDED_ONLY_ABOVE:
        return max(min(q_one, q_two), max(q_one / c, q_two / c))
    return min(q_one, q_two)


def sample_share(my_q_min: float, others_q_min: float) -> float:
    """Q_normal for one sample, assuming `others_q_min` is everyone else combined."""
    total = my_q_min + others_q_min
    return my_q_min / total if total > 0 else 0.0


def book_orders(bids: Sequence, asks: Sequence, complement: bool) -> list[RewardOrder]:
    """Visible book levels as RewardOrders (each level treated as one order)."""
    out = []
    for side, levels in (("bid", bids), ("ask", asks)):
        for lvl in levels:
            price, size = (lvl.price, lvl.size) if hasattr(lvl, "price") else lvl
            out.append(RewardOrder(side, price, size, complement))  # type: ignore[arg-type]
    return out


def estimated_reward_for_interval(daily_rate: float, share: float, seconds: float) -> float:
    """ESTIMATE: daily_rate * share * (seconds / 1 day), assuming every sample in the
    interval had the same share and some qualifying liquidity existed."""
    if daily_rate <= 0 or share <= 0 or seconds <= 0:
        return 0.0
    return daily_rate * share * min(seconds, 86400.0) / 86400.0


def estimated_epoch_reward(daily_rate: float, sample_shares: Sequence[float], samples_per_epoch: int = SAMPLES_PER_EPOCH) -> float:
    """ESTIMATE over an epoch from per-sample shares (missing samples count as 0)."""
    if daily_rate <= 0:
        return 0.0
    return daily_rate * sum(sample_shares) / samples_per_epoch
