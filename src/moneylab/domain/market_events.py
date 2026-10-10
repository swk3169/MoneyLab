"""Provider-neutral market events for research (one line of a processed event file).

An exchange adapter turns each recorded line into a `MarketEvent`: the book (best-first levels)
or the trade it carried, its two clocks, the connection it arrived on, and quality flags. Flags
only describe; nothing is dropped here. The research layer decides what to exclude.

Clocks:
  received_timestamp  local UTC epoch seconds taken when the message arrived (research time axis)
  exchange_timestamp_ms  the exchange's message timestamp in integer ms (None for local events);
                         its exact meaning is exchange-specific and is NOT used as a time axis
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Any

from moneylab.domain.orderbook import OrderBook

BOOK, TRADE = "book", "trade"
CONNECTION, DISCONNECT, FAILURE = "connection", "disconnect", "failure"
EVENT_TYPES = (BOOK, TRADE, CONNECTION, DISCONNECT, FAILURE)
LOCAL_EVENT_TYPES = (CONNECTION, DISCONNECT, FAILURE)
STREAM_TYPES = ("SNAPSHOT", "REALTIME")
PROVENANCES = ("real", "fixture")

# Quality flags (see docs/research_v04_preregistration.md, section 4).
WARMUP = "warmup"
STALE_BOOK = "stale_book"
CROSSED_BOOK = "crossed_book"
LOCKED_BOOK = "locked_book"
TIMESTAMP_REVERSE = "timestamp_reverse"
SEQUENCE_GAP = "sequence_gap"
DUPLICATE = "duplicate"
RECONNECT_BOUNDARY = "reconnect_boundary"
QUALITY_FLAGS = (WARMUP, STALE_BOOK, CROSSED_BOOK, LOCKED_BOOK, TIMESTAMP_REVERSE, SEQUENCE_GAP, DUPLICATE,
                 RECONNECT_BOUNDARY)

Level = tuple[float, float]  # (price, size)


@dataclass(frozen=True)
class TradePrint:
    price: float
    volume: float
    side: str | None  # "buy" | "sell" as labelled by the exchange (aggressor meaning is exchange-specific)
    trade_id: int | str | None = None
    trade_timestamp_ms: int | None = None

    @property
    def sign(self) -> int:
        return 1 if self.side == "buy" else -1 if self.side == "sell" else 0


@dataclass(frozen=True)
class MarketEvent:
    market: str | None
    event_type: str
    provenance: str
    received_timestamp: float
    local_sequence: int
    exchange_timestamp_ms: int | None = None
    stream_type: str | None = None
    connection_id: str | None = None
    bids: tuple[Level, ...] = ()  # best (highest) first
    asks: tuple[Level, ...] = ()  # best (lowest) first
    trade: TradePrint | None = None
    flags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        if self.event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type {self.event_type!r}")
        if self.provenance not in PROVENANCES:
            raise ValueError(f"unknown provenance {self.provenance!r}")
        unknown = set(self.flags) - set(QUALITY_FLAGS)
        if unknown:
            raise ValueError(f"unknown quality flags {sorted(unknown)}")
        if self.event_type == TRADE and self.trade is None:
            raise ValueError("trade event without a trade")

    @classmethod
    def book_event(cls, *, bids: Iterable, asks: Iterable, **kwargs: Any) -> MarketEvent:
        """Levels normalized like `OrderBook` (sorted best-first, sizes <= 0 dropped, prices merged)."""
        ob = OrderBook.build(kwargs.get("market") or "?", bids, asks)
        return cls(event_type=BOOK, bids=tuple((lv.price, lv.size) for lv in ob.bids),
                   asks=tuple((lv.price, lv.size) for lv in ob.asks), **kwargs)

    @property
    def is_market_data(self) -> bool:
        return self.event_type in (BOOK, TRADE)

    @property
    def best_bid(self) -> float | None:
        return self.bids[0][0] if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0][0] if self.asks else None

    def with_flags(self, *flags: str) -> MarketEvent:
        if not flags:
            return self
        return replace(self, flags=self.flags | frozenset(flags))

    def to_order_book(self) -> OrderBook:
        return OrderBook.build(self.market or "?", self.bids, self.asks, tick_size=0.0, market_id=self.market,
                               timestamp=self.received_timestamp)

    # --- serialization (one JSON object per line) ------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "market": self.market, "event_type": self.event_type, "provenance": self.provenance,
            "received_timestamp": self.received_timestamp, "local_sequence": self.local_sequence,
            "exchange_timestamp_ms": self.exchange_timestamp_ms, "stream_type": self.stream_type,
            "connection_id": self.connection_id, "flags": sorted(self.flags),
        }
        if self.event_type == BOOK:
            out["bids"] = [list(lv) for lv in self.bids]
            out["asks"] = [list(lv) for lv in self.asks]
        if self.trade is not None:
            t = self.trade
            out["trade"] = {"price": t.price, "volume": t.volume, "side": t.side, "trade_id": t.trade_id,
                            "trade_timestamp_ms": t.trade_timestamp_ms}
        return out

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MarketEvent:
        tr = d.get("trade")
        return cls(
            market=d.get("market"), event_type=d["event_type"], provenance=d["provenance"],
            received_timestamp=float(d["received_timestamp"]), local_sequence=int(d["local_sequence"]),
            exchange_timestamp_ms=d.get("exchange_timestamp_ms"), stream_type=d.get("stream_type"),
            connection_id=d.get("connection_id"),
            bids=tuple((float(p), float(s)) for p, s in d.get("bids") or ()),
            asks=tuple((float(p), float(s)) for p, s in d.get("asks") or ()),
            trade=None if tr is None else TradePrint(float(tr["price"]), float(tr["volume"]), tr.get("side"),
                                                     tr.get("trade_id"), tr.get("trade_timestamp_ms")),
            flags=frozenset(d.get("flags") or ()),
        )
