"""Provider-agnostic market scanner.

Depends only on MarketDataProvider and domain.Market. Provider failures are
returned inside ScanResult (never raised), so callers cannot crash on API outages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from moneylab.core.exceptions import ProviderError
from moneylab.domain.models import Market
from moneylab.providers.base import MarketDataProvider, MarketQuery

log = logging.getLogger(__name__)

SORT_KEYS = {
    "volume": lambda m: m.volume or 0.0,
    "volume24h": lambda m: m.volume_24h or 0.0,
    "liquidity": lambda m: m.liquidity or 0.0,
    "end": lambda m: m.end_date.timestamp() if m.end_date else float("inf"),
    "spread": lambda m: m.spread if m.spread is not None else float("inf"),
}


@dataclass(frozen=True)
class ScanCriteria:
    min_volume: float = 0.0
    min_liquidity: float = 0.0
    min_days_to_end: float | None = 0.0  # drop already-expired markets by default
    max_days_to_end: float | None = None
    min_yes_price: float | None = None
    max_yes_price: float | None = None
    binary_only: bool = False
    sort_by: str = "volume24h"
    descending: bool = True
    top_n: int = 30
    # flags (informational, do not filter)
    wide_spread_threshold: float = 0.05
    price_sum_tolerance: float = 0.02


@dataclass
class Candidate:
    market: Market
    flags: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    provider: str
    fetched: int = 0
    candidates: list[Candidate] = field(default_factory=list)
    error: ProviderError | None = None
    scanned_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def ok(self) -> bool:
        return self.error is None


class MarketScanner:
    def __init__(self, provider: MarketDataProvider):
        self.provider = provider

    def scan(self, criteria: ScanCriteria, query: MarketQuery | None = None) -> ScanResult:
        result = ScanResult(provider=self.provider.name)
        try:
            markets = self.provider.get_markets(query or MarketQuery())
        except ProviderError as exc:
            log.error("Provider failed: %s", exc)
            result.error = exc
            return result
        result.fetched = len(markets)
        result.candidates = self.select(markets, criteria, now=result.scanned_at)
        return result

    @staticmethod
    def select(markets: list[Market], c: ScanCriteria, now: datetime | None = None) -> list[Candidate]:
        now = now or datetime.now(UTC)
        selected: list[Candidate] = []
        for m in markets:
            if m.closed or not m.active:
                continue
            if (m.volume or 0.0) < c.min_volume or (m.liquidity or 0.0) < c.min_liquidity:
                continue
            days = m.days_to_end(now)
            if days is None:
                if c.max_days_to_end is not None:  # "ends within N days" requires a known end
                    continue
            else:
                if c.min_days_to_end is not None and days < c.min_days_to_end:
                    continue
                if c.max_days_to_end is not None and days > c.max_days_to_end:
                    continue
            if c.binary_only and not m.is_binary_yes_no:
                continue
            yes = m.yes_price
            if c.min_yes_price is not None and (yes is None or yes < c.min_yes_price):
                continue
            if c.max_yes_price is not None and (yes is None or yes > c.max_yes_price):
                continue
            selected.append(Candidate(m, MarketScanner.flags_for(m, c)))

        key = SORT_KEYS.get(c.sort_by, SORT_KEYS["volume24h"])
        selected.sort(key=lambda cand: key(cand.market), reverse=c.descending)
        return selected[: c.top_n]

    @staticmethod
    def flags_for(m: Market, c: ScanCriteria) -> list[str]:
        flags: list[str] = []
        if m.spread is not None and m.spread >= c.wide_spread_threshold:
            flags.append("WIDE_SPREAD")
        ps = m.price_sum
        if ps is not None and abs(ps - 1.0) > c.price_sum_tolerance:
            flags.append(f"PRICE_SUM={ps:.3f}")
        if m.accepting_orders is False:
            flags.append("NOT_ACCEPTING")
        if not m.is_binary_yes_no:
            flags.append("NON_BINARY")
        return flags
