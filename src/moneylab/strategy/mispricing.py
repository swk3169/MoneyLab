"""Mispricing strategy interface and reference implementations.

All edges are measured NET of taker fees at the price actually paid (book walk), never on
the quoted mid. Incentives (rebates/rewards) play no part in these decisions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from moneylab.analytics.costs import fee_curve, taker_fee_for_fills
from moneylab.analytics.metrics import walk_book
from moneylab.domain.market_params import FeeSchedule
from moneylab.domain.orderbook import OrderBook
from moneylab.strategy.context import StrategyContext, TradeIntent


class MispricingStrategy(ABC):
    name: str = "abstract-mispricing"

    @abstractmethod
    def evaluate(self, ctx: StrategyContext) -> list[TradeIntent]:
        """Trade ideas for this snapshot. Pure: no I/O, no order placement."""


def fee_per_share(price: float, schedule: FeeSchedule) -> float:
    return fee_curve(1.0, price, schedule)


def _cum_breaks(book: OrderBook) -> list[float]:
    out, total = [], 0.0
    for lvl in book.asks:
        total += lvl.size
        out.append(total)
    return out


def _cost(book: OrderBook, shares: float, schedule: FeeSchedule) -> tuple[float, float] | None:
    """(total cost incl. fees, worst price) for buying `shares`; None if the book is too thin."""
    fills = walk_book(book.asks, shares)
    if sum(q for _, q in fills) < shares - 1e-9:
        return None
    return sum(p * q for p, q in fills) + taker_fee_for_fills(fills, schedule), fills[-1][0]


@dataclass
class ComplementArbitrage(MispricingStrategy):
    """Buy YES and NO together when ask_yes + ask_no + fees < 1 (redeemable for 1 per pair).

    Size grows level by level (book breakpoints) while the *marginal* edge per pair of each
    slice, after fees, stays >= min_edge_per_share.

    Hypothesis to verify on live data: CLOB V2 matches complementary orders (mint/merge), so on
    a single binary market this gap may almost never be observable.
    """

    min_edge_per_share: float = 0.005
    name: str = "complement-arb"

    def evaluate(self, ctx: StrategyContext) -> list[TradeIntent]:
        p = ctx.params
        yb, nb = ctx.book(p.yes_token), ctx.book(p.no_token)
        if yb is None or nb is None or not yb.asks or not nb.asks:
            return []
        if yb.best_ask + nb.best_ask >= 1.0:
            return []
        best, prev_s, prev_edge = None, 0.0, 0.0
        for s in sorted(set(_cum_breaks(yb) + _cum_breaks(nb))):
            cy, cn = _cost(yb, s, p.fee), _cost(nb, s, p.fee)
            if cy is None or cn is None:
                break
            edge = s - cy[0] - cn[0]
            if (edge - prev_edge) / (s - prev_s) < self.min_edge_per_share:
                break  # the extra pairs in this slice are not worth it
            best, prev_s, prev_edge = (s, edge, cy, cn), s, edge
        if best is None:
            return []
        s, edge, (cost_y, worst_y), (cost_n, worst_n) = best
        gid = f"arb-{int(ctx.snapshot.timestamp)}"
        why = f"ask_yes+ask_no+fees={(cost_y + cost_n) / s:.4f} < 1"
        half = edge / s / 2  # pair edge split evenly across the two legs
        return [
            TradeIntent(p.yes_token, "buy", worst_y, s, cost_y / s + half, half, cost_y / s, "arbitrage", gid, why),
            TradeIntent(p.no_token, "buy", worst_n, s, cost_n / s + half, half, cost_n / s, "arbitrage", gid, why),
        ]


@dataclass
class FairValueDeviation(MispricingStrategy):
    """Buy the token whose fee-inclusive ask is below an external fair probability.

    The fair probability comes from `snapshot.signals[signal_key]` (YES probability) - a model
    outside this code base. Without a signal, nothing is traded. Positions are held to
    resolution (no exit logic in this reference implementation).
    """

    signal_key: str = "fair_yes"
    min_edge_per_share: float = 0.02
    name: str = "fair-value"

    def _intent(self, ctx: StrategyContext, token: str | None, fair: float) -> TradeIntent | None:
        book = ctx.book(token)
        if token is None or book is None or not book.asks:
            return None
        sched = ctx.params.fee
        limit, depth = None, 0.0
        for lvl in book.asks:  # walk while the *marginal* level still clears the edge
            if fair - lvl.price - fee_per_share(lvl.price, sched) < self.min_edge_per_share:
                break
            limit, depth = lvl.price, depth + lvl.size
        if limit is None:
            return None
        top = book.best_ask
        all_in = top + fee_per_share(top, sched)
        return TradeIntent(
            token, "buy", limit, depth, fair, fair - all_in, all_in, "directional",
            rationale=f"fair={fair:.3f} vs all-in ask={all_in:.4f}",
        )

    def evaluate(self, ctx: StrategyContext) -> list[TradeIntent]:
        q = ctx.snapshot.signals.get(self.signal_key)
        if q is None or not 0 <= q <= 1:
            return []
        p = ctx.params
        candidates = [i for i in (self._intent(ctx, p.yes_token, q), self._intent(ctx, p.no_token, 1 - q)) if i]
        return [max(candidates, key=lambda i: i.edge_per_share)] if candidates else []


@dataclass
class CombinedMispricing(MispricingStrategy):
    """Runs several mispricing strategies; arbitrage legs first, then directional ideas."""

    strategies: tuple[MispricingStrategy, ...] = ()
    name: str = "mispricing"

    def evaluate(self, ctx: StrategyContext) -> list[TradeIntent]:
        intents = [i for s in self.strategies for i in s.evaluate(ctx)]
        return sorted(intents, key=lambda i: i.kind != "arbitrage")
