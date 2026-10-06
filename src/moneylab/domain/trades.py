"""Provider-neutral executed trade (public trade print)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradeTick:
    """One public trade as reported by an exchange.

    `side` is the exchange's own buy/sell label mapped to "buy" | "sell" (None if absent).
    Whether that label is the aggressor (taker) side depends on the exchange and is documented
    by the provider that builds the tick. Timestamps are unix seconds.
    """

    market: str
    price: float
    volume: float
    side: str | None
    exchange_timestamp: float  # when the exchange says the trade happened
    trade_id: int | str | None = None  # exchange's unique trade identifier, if any
    received_timestamp: float | None = None  # local receive time (UTC epoch), if recorded live

    @property
    def notional(self) -> float:
        return self.price * self.volume
