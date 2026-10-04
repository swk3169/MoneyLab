"""Normalized market model shared by scanner, strategies, backtest and execution.

Prices are probabilities in [0, 1] (USDC per share for binary prediction markets).
Money amounts are in the market's quote currency (USDC for Polymarket).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from moneylab.domain.market_params import FeeSchedule, RewardConfig


@dataclass(frozen=True)
class Outcome:
    name: str
    price: float | None
    token_id: str | None = None


@dataclass(frozen=True)
class Market:
    source: str  # provider name, e.g. "polymarket"
    market_id: str  # provider's primary id
    question: str
    outcomes: tuple[Outcome, ...] = ()
    volume: float | None = None  # lifetime volume
    volume_24h: float | None = None
    liquidity: float | None = None
    end_date: datetime | None = None
    best_bid: float | None = None  # for the first ("YES") outcome
    best_ask: float | None = None
    last_trade_price: float | None = None
    active: bool = True
    closed: bool = False
    accepting_orders: bool | None = None
    slug: str | None = None
    condition_id: str | None = None
    url: str | None = None
    fee_schedule: FeeSchedule | None = None  # None = unknown, not "free"
    reward_config: RewardConfig | None = None
    extra: dict = field(default_factory=dict, compare=False, repr=False)

    # --- binary helpers -------------------------------------------------
    def outcome(self, name: str) -> Outcome | None:
        lname = name.lower()
        return next((o for o in self.outcomes if o.name.lower() == lname), None)

    @property
    def is_binary_yes_no(self) -> bool:
        return len(self.outcomes) == 2 and self.outcome("yes") is not None and self.outcome("no") is not None

    @property
    def yes_price(self) -> float | None:
        o = self.outcome("yes")
        return o.price if o else None

    @property
    def no_price(self) -> float | None:
        o = self.outcome("no")
        return o.price if o else None

    # --- microstructure -------------------------------------------------
    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def mid_price(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_ask + self.best_bid) / 2

    @property
    def price_sum(self) -> float | None:
        """Sum of outcome prices. Deviation from 1.0 is a rough overround/mispricing signal."""
        prices = [o.price for o in self.outcomes]
        if not prices or any(p is None for p in prices):
            return None
        return sum(prices)

    def days_to_end(self, now: datetime | None = None) -> float | None:
        if self.end_date is None:
            return None
        now = now or datetime.now(UTC)
        return (self.end_date - now).total_seconds() / 86400
