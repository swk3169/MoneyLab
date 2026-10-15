"""SYNTHETIC bar builders for the BT-1 backtest tests. Not market data, never evidence."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from moneylab.backtest.data import BarSeries, provenance_for
from moneylab.domain.bars import Bar

T0 = datetime(2020, 1, 1, tzinfo=UTC)
DAY = timedelta(days=1)
HOUR = timedelta(hours=1)


def flat_bar(interval: str, start: datetime, price: Decimal, market: str = "KRW-BTC") -> Bar:
    return Bar(market, interval, start, price, price, price, price, Decimal(1), Decimal(1))


def daily_bars(closes: Sequence[Decimal | int | str], start: datetime = T0) -> list[Bar]:
    return [flat_bar("day", start + i * DAY, Decimal(c)) for i, c in enumerate(closes)]


def hourly_bars(days: int, price_of: Callable[[int, int], Decimal], start: datetime = T0) -> list[Bar]:
    """24 hourly bars per day; price_of(day_index, hour) gives the close (open = high = low = close)."""
    return [flat_bar("hour", start + d * DAY + h * HOUR, Decimal(price_of(d, h)))
            for d in range(days) for h in range(24)]


def series(bars: Sequence[Bar], kind: str = "synthetic", description: str = "tests/backtest_helpers") -> BarSeries:
    return BarSeries.build(bars, provenance_for(bars, kind, description))


def random_market(days: int, seed: int) -> tuple[list[Bar], list[Bar]]:
    """Seeded random walk. Daily close C_d; hourly closes interpolate geometrically from C_{d-1} to C_d,
    so the hour-23 close equals the daily close. Prices are rounded to 0.01."""
    rng = random.Random(seed)
    closes = [100.0]
    for _ in range(days - 1):
        closes.append(closes[-1] * math.exp(rng.gauss(0.0, 0.03)))
    dec = [Decimal(f"{c:.2f}") for c in closes]

    def price(d: int, h: int) -> Decimal:
        prev = closes[d - 1] if d else closes[0]
        w = (h + 1) / 24
        return Decimal(f"{prev ** (1 - w) * closes[d] ** w:.2f}")

    return daily_bars(dec), hourly_bars(days, price)
