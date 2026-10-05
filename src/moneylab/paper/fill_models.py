"""Maker fill models for paper trading against *external* order-book snapshots.

Our paper orders are not in the recorded book, so we must infer whether they would have been
hit. The interface is separate so a queue-position model can be added once enough real
order-book (and trade) data exists.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

EPS = 1e-9


@dataclass
class Liquidity:
    """Mutable view of opposite-side levels within one snapshot, so two of our resting orders
    cannot both claim the same crossing liquidity."""

    price: float
    size: float


class MakerFillModel(ABC):
    name: str = "abstract"

    @abstractmethod
    def fill_quantity(self, side: str, price: float, remaining: float, opposite: Sequence[Liquidity]) -> float:
        """Shares of a resting order (side, price) filled by this snapshot.

        `opposite` = levels on the other side, best first (asks for a bid, bids for an ask).
        Implementations must decrement `Liquidity.size` for what they consume.
        """


class TradeThroughFillModel(MakerFillModel):
    """Conservative default: fill only when the opposite side trades *through* our price.

    A resting bid at b is filled only by asks priced strictly below b (sellers who would have
    hit us first); an ask at a only by bids strictly above a. Touching (best ask == b) is NOT
    a fill - we would be at the back of an unknown queue. Fill size is capped by the crossing
    size. Ignores queue position entirely, so it under-fills relative to reality.
    """

    name = "trade-through"

    def fill_quantity(self, side: str, price: float, remaining: float, opposite: Sequence[Liquidity]) -> float:
        filled = 0.0
        for lvl in opposite:
            if remaining - filled <= EPS:
                break
            crosses = lvl.price < price - EPS if side == "buy" else lvl.price > price + EPS
            if not crosses:
                break
            take = min(lvl.size, remaining - filled)
            lvl.size -= take
            filled += take
        return filled


# A QueuePositionFillModel (fill when traded volume at our level exceeds the queue ahead of
# us) needs per-level trade prints and queue snapshots we do not have yet. Implement it as
# another MakerFillModel once recorded live data is available.
