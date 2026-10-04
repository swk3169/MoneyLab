"""Inputs and outputs shared by order-book strategies (provider-neutral)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from moneylab.domain.market_params import MarketParams
from moneylab.domain.orderbook import BookSnapshot, OrderBook


@dataclass(frozen=True)
class StrategyContext:
    params: MarketParams
    snapshot: BookSnapshot
    positions: Mapping[str, float] = field(default_factory=dict)  # token_id -> shares held

    def book(self, token_id: str | None) -> OrderBook | None:
        return self.snapshot.books.get(token_id) if token_id else None

    def position(self, token_id: str | None) -> float:
        return self.positions.get(token_id, 0.0) if token_id else 0.0

    @property
    def net_yes_delta(self) -> float:
        """YES-equivalent exposure: YES shares minus NO shares."""
        return self.position(self.params.yes_token) - self.position(self.params.no_token)


@dataclass(frozen=True)
class Quote:
    """A resting order the market maker wants live after this step."""

    token_id: str
    side: Literal["buy", "sell"]
    price: float
    size: float


@dataclass(frozen=True)
class TradeIntent:
    """An immediate (taker) trade idea before sizing."""

    token_id: str
    side: Literal["buy", "sell"]
    limit_price: float  # worst acceptable price
    max_size: float  # shares available up to limit_price
    fair_probability: float  # strategy's estimate for this token
    edge_per_share: float  # net of taker fees at the expected fill price
    all_in_price: float  # expected price per share including fees
    kind: Literal["directional", "arbitrage"] = "directional"
    group_id: str | None = None
    rationale: str = ""


def floor_to_tick(price: float, tick: float) -> float:
    return round(math.floor(price / tick + 1e-9) * tick, 6)


def ceil_to_tick(price: float, tick: float) -> float:
    return round(math.ceil(price / tick - 1e-9) * tick, 6)


def on_tick(price: float, tick: float) -> bool:
    return abs(price / tick - round(price / tick)) < 1e-6
