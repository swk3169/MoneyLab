"""Provider-neutral order book.

Levels are always normalized here: bids sorted best (highest) first, asks best (lowest)
first, zero/negative sizes dropped, duplicate prices merged. Callers never rely on the
order a provider sent (Polymarket's REST spec says bids are descending, while its WS
example shows them ascending).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from moneylab.domain.market_params import MarketParams


@dataclass(frozen=True)
class PriceLevel:
    price: float
    size: float


def _normalize(levels: Iterable[PriceLevel | tuple[float, float]], descending: bool) -> tuple[PriceLevel, ...]:
    merged: dict[float, float] = {}
    for lvl in levels:
        price, size = (lvl.price, lvl.size) if isinstance(lvl, PriceLevel) else lvl
        if size is None or price is None or size <= 0:
            continue
        key = round(float(price), 6)
        merged[key] = merged.get(key, 0.0) + float(size)
    return tuple(PriceLevel(p, s) for p, s in sorted(merged.items(), reverse=descending))


@dataclass(frozen=True)
class OrderBook:
    token_id: str
    bids: tuple[PriceLevel, ...] = ()
    asks: tuple[PriceLevel, ...] = ()
    tick_size: float = 0.01
    min_order_size: float = 0.0
    market_id: str | None = None  # condition id
    timestamp: float | None = None  # unix seconds
    last_trade_price: float | None = None
    neg_risk: bool = False

    @classmethod
    def build(cls, token_id: str, bids: Iterable, asks: Iterable, **kwargs: Any) -> OrderBook:
        return cls(token_id=token_id, bids=_normalize(bids, True), asks=_normalize(asks, False), **kwargs)

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def best_bid_size(self) -> float:
        return self.bids[0].size if self.bids else 0.0

    @property
    def best_ask_size(self) -> float:
        return self.asks[0].size if self.asks else 0.0

    @property
    def mid(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def is_crossed(self) -> bool:
        return self.best_bid is not None and self.best_ask is not None and self.best_bid >= self.best_ask

    def levels(self, side: str) -> tuple[PriceLevel, ...]:
        """Liquidity a taker on `side` would consume: buy -> asks, sell -> bids."""
        return self.asks if side == "buy" else self.bids


@dataclass(frozen=True)
class BookSnapshot:
    """All books of one market at one point in time, plus optional external signals
    (e.g. a model's fair probability). Signals are never derived from the books."""

    timestamp: float
    books: Mapping[str, OrderBook]
    signals: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketTimeline:
    """A replayable sequence of snapshots for one market (fixture or recorded live data)."""

    params: MarketParams
    snapshots: tuple[BookSnapshot, ...]
    resolution: Mapping[str, float] | None = None  # token_id -> payout (1.0 / 0.0)
    synthetic: bool = True
    description: str = ""
