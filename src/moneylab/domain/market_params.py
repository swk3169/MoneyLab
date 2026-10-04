"""Provider-neutral market trading parameters: fee schedule, reward config, tick/min size.

Polymarket sources (docs checked 2026-10-04, NOT yet verified against live responses):
  * Gamma market `feeSchedule {rate, exponent, takerOnly, rebateRate}`, `feesEnabled`
  * CLOB `GET /clob-markets/{condition_id}`: `fd {r, e, to}`, `mts`, `mos`, `t[{t, o}]`
  * CLOB `GET /rewards/markets/{condition_id}`: `rewards_max_spread`, `rewards_min_size`,
    `rewards_config[{rate_per_day, start_date, end_date}]`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class FeeSchedule:
    """Taker fee curve: fee = shares * rate * (p * (1 - p)) ** exponent.

    exponent=1 reproduces the documented formula. Other exponents are an interpretation
    of "exponent applied to the price component" (unverified).
    """

    rate: float = 0.0
    exponent: float = 1.0
    taker_only: bool = True
    rebate_rate: float = 0.0  # share of taker fees returned to makers (e.g. 0.25)
    enabled: bool = True

    @classmethod
    def free(cls) -> FeeSchedule:
        return cls(rate=0.0, enabled=False)


@dataclass(frozen=True)
class RewardAllocation:
    daily_rate: float
    start_date: date | None = None
    end_date: date | None = None

    def active_on(self, day: date) -> bool:
        if self.start_date and day < self.start_date:
            return False
        return not (self.end_date and day > self.end_date)


@dataclass(frozen=True)
class RewardConfig:
    """Liquidity reward settings. max_spread is in cents from the (adjusted) midpoint."""

    max_spread_cents: float
    min_size: float
    allocations: tuple[RewardAllocation, ...] = ()
    in_game_multiplier: float = 1.0  # `b` in S(v, s); 1.0 unless a market says otherwise
    scaling_c: float = 3.0  # documented as "currently 3.0 on all markets"

    def daily_rate(self, day: date | None = None) -> float:
        if day is None:
            return sum(a.daily_rate for a in self.allocations)
        return sum(a.daily_rate for a in self.allocations if a.active_on(day))


@dataclass(frozen=True)
class TokenInfo:
    token_id: str
    outcome: str


@dataclass(frozen=True)
class MarketParams:
    condition_id: str
    tokens: tuple[TokenInfo, ...]
    tick_size: float = 0.01
    min_order_size: float = 0.0
    fee: FeeSchedule = field(default_factory=FeeSchedule.free)
    rewards: RewardConfig | None = None
    neg_risk: bool = False
    question: str | None = None

    def token(self, outcome: str) -> TokenInfo | None:
        low = outcome.lower()
        return next((t for t in self.tokens if t.outcome.lower() == low), None)

    @property
    def yes_token(self) -> str | None:
        t = self.token("yes")
        return t.token_id if t else None

    @property
    def no_token(self) -> str | None:
        t = self.token("no")
        return t.token_id if t else None

    def complement(self, token_id: str) -> str | None:
        """The other token of a binary market."""
        if len(self.tokens) != 2:
            return None
        a, b = self.tokens
        if token_id == a.token_id:
            return b.token_id
        if token_id == b.token_id:
            return a.token_id
        return None
