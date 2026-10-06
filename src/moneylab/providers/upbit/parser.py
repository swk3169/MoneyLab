"""Upbit public WebSocket messages -> typed messages -> provider-neutral OrderBook / TradeTick.

Only fields listed in the official docs are read (DEFAULT format, full field names):

orderbook  (https://docs.upbit.com/kr/reference/websocket-orderbook)
  type, code, total_ask_size, total_bid_size, timestamp (ms), level, stream_type,
  orderbook_units[{ask_price, bid_price, ask_size, bid_size}]
trade      (https://docs.upbit.com/kr/reference/websocket-trade)
  type, code, trade_price, trade_volume, ask_bid (ASK = 매도/sell, BID = 매수/buy),
  prev_closing_price, change, change_price, trade_date, trade_time (UTC), trade_timestamp (ms),
  timestamp (ms), sequential_id (체결 번호, unique), best_ask_price, best_ask_size,
  best_bid_price, best_bid_size, stream_type
status     {"status": "UP"}  reply to a "PING" text message (websocket-guide)
error      {"error": {"name": ..., "message": ...}}  (websocket-guide)

`exchange_timestamp` is the documented message field `timestamp` for both kinds, so the two
streams share one clock field. A trade's execution time (`trade_timestamp`) is kept separately.

Not stated by the docs (UNVERIFIED, do not rely on it without checking recorded data):
  * that every REALTIME orderbook message carries the full top-N book (not a delta);
  * that `ask_bid` is the aggressor (taker) side; MoneyLab only maps ASK -> "sell", BID -> "buy";
  * that `sequential_id` increases monotonically (the docs only say it is unique).

Prices are KRW (or the market's quote currency) per unit, NOT probabilities: these books must
not be fed to the prediction-market strategies.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from moneylab.domain.orderbook import OrderBook
from moneylab.domain.trades import TradeTick
from moneylab.providers.upbit.endpoints import WS_FORMAT, orderbook_code, validate_market

STREAM_TYPES = ("SNAPSHOT", "REALTIME")
ASK_BID_SIDE = {"ASK": "sell", "BID": "buy"}


class UpbitParseError(ValueError):
    """A message is not valid JSON or lacks/garbles a documented field."""


# --- framing --------------------------------------------------------------------------------

def decode_frame(frame: bytes | str) -> tuple[str, str]:
    """Return (text, frame_type). Upbit was observed sending binary frames of UTF-8 JSON."""
    if isinstance(frame, str):
        return frame, "text"
    if isinstance(frame, (bytes, bytearray, memoryview)):
        try:
            return bytes(frame).decode("utf-8"), "binary"
        except UnicodeDecodeError as exc:
            raise UpbitParseError(f"binary frame is not UTF-8: {exc}") from exc
    raise UpbitParseError(f"unexpected frame type {type(frame).__name__}")


def load_message(text: str) -> dict[str, Any]:
    try:
        obj = json.loads(text)
    except ValueError as exc:
        raise UpbitParseError(f"not JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise UpbitParseError(f"expected a JSON object, got {type(obj).__name__}")
    return obj


def message_kind(obj: dict[str, Any]) -> str:
    """orderbook | trade | status | error | unknown"""
    t = obj.get("type")
    if t in ("orderbook", "trade"):
        return t
    if "error" in obj:
        return "error"
    if "status" in obj and len(obj) == 1:
        return "status"
    return "unknown"


# --- field helpers --------------------------------------------------------------------------

def _num(obj: dict[str, Any], key: str, *, required: bool = True) -> float | None:
    v = obj.get(key)
    if v is None:
        if required:
            raise UpbitParseError(f"missing field {key!r}")
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise UpbitParseError(f"field {key!r} is not a finite number: {v!r}")
    return float(v)


def _int(obj: dict[str, Any], key: str) -> int:
    v = obj.get(key)
    if isinstance(v, bool) or not isinstance(v, int):
        raise UpbitParseError(f"field {key!r} must be an integer, got {v!r}")
    return v


def _str(obj: dict[str, Any], key: str, *, required: bool = True) -> str | None:
    v = obj.get(key)
    if v is None and not required:
        return None
    if not isinstance(v, str) or not v:
        raise UpbitParseError(f"field {key!r} must be a non-empty string, got {v!r}")
    return v


def _market(obj: dict[str, Any]) -> str:
    try:
        return validate_market(_str(obj, "code") or "")
    except ValueError as exc:
        raise UpbitParseError(str(exc)) from exc


def _stream_type(obj: dict[str, Any]) -> str | None:
    st = obj.get("stream_type")
    if st is not None and st not in STREAM_TYPES:
        raise UpbitParseError(f"unknown stream_type {st!r}")
    return st


# --- orderbook ------------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderbookUnit:
    ask_price: float
    bid_price: float
    ask_size: float
    bid_size: float


@dataclass(frozen=True)
class UpbitOrderbookMessage:
    market: str
    exchange_timestamp_ms: int
    stream_type: str | None
    level: float | None
    total_ask_size: float
    total_bid_size: float
    units: tuple[OrderbookUnit, ...]

    @property
    def exchange_timestamp(self) -> float:
        return self.exchange_timestamp_ms / 1000.0

    def to_order_book(self) -> OrderBook:
        """Provider-neutral book. token_id = market id = the Upbit pair code. Tick size is not
        part of the WS message, so it is left at 0 (= unknown)."""
        return OrderBook.build(
            self.market,
            bids=[(u.bid_price, u.bid_size) for u in self.units],
            asks=[(u.ask_price, u.ask_size) for u in self.units],
            tick_size=0.0, market_id=self.market, timestamp=self.exchange_timestamp,
        )

    def summary(self) -> dict[str, Any]:
        return summarize_book(self.to_order_book(), self)


def summarize_book(book: OrderBook, msg: UpbitOrderbookMessage | None = None) -> dict[str, Any]:
    """Derived values stored next to the raw message (and recomputed by replay checks)."""
    out: dict[str, Any] = {
        "best_bid": book.best_bid,
        "best_ask": book.best_ask,
        "best_bid_size": book.best_bid_size if book.bids else None,
        "best_ask_size": book.best_ask_size if book.asks else None,
        "spread": None if book.spread is None else book.spread,
        "mid": book.mid,
        "bid_depth": sum(lv.size for lv in book.bids),  # visible size over all received levels
        "ask_depth": sum(lv.size for lv in book.asks),
        "bid_levels": len(book.bids),
        "ask_levels": len(book.asks),
    }
    if msg is not None:
        out.update(units=len(msg.units), total_bid_size=msg.total_bid_size, total_ask_size=msg.total_ask_size,
                   level=msg.level, stream_type=msg.stream_type)
    return out


def parse_orderbook(obj: dict[str, Any]) -> UpbitOrderbookMessage:
    if obj.get("type") != "orderbook":
        raise UpbitParseError(f"not an orderbook message (type={obj.get('type')!r})")
    raw_units = obj.get("orderbook_units")
    if not isinstance(raw_units, list):
        raise UpbitParseError("orderbook_units must be a list")
    units = []
    for i, u in enumerate(raw_units):
        if not isinstance(u, dict):
            raise UpbitParseError(f"orderbook_units[{i}] is not an object")
        unit = OrderbookUnit(_num(u, "ask_price"), _num(u, "bid_price"), _num(u, "ask_size"), _num(u, "bid_size"))
        if min(unit.ask_price, unit.bid_price, unit.ask_size, unit.bid_size) < 0:
            raise UpbitParseError(f"orderbook_units[{i}] has a negative value")
        units.append(unit)
    return UpbitOrderbookMessage(
        market=_market(obj), exchange_timestamp_ms=_int(obj, "timestamp"), stream_type=_stream_type(obj),
        level=_num(obj, "level", required=False), total_ask_size=_num(obj, "total_ask_size"),
        total_bid_size=_num(obj, "total_bid_size"), units=tuple(units),
    )


# --- trade ----------------------------------------------------------------------------------

@dataclass(frozen=True)
class UpbitTradeMessage:
    market: str
    sequential_id: int
    trade_price: float
    trade_volume: float
    ask_bid: str
    trade_timestamp_ms: int
    exchange_timestamp_ms: int
    stream_type: str | None
    trade_date: str | None = None
    trade_time: str | None = None
    best_bid_price: float | None = None
    best_ask_price: float | None = None

    @property
    def side(self) -> str:
        return ASK_BID_SIDE[self.ask_bid]

    @property
    def exchange_timestamp(self) -> float:
        return self.exchange_timestamp_ms / 1000.0

    def to_trade_tick(self, received_timestamp: float | None = None) -> TradeTick:
        return TradeTick(market=self.market, price=self.trade_price, volume=self.trade_volume, side=self.side,
                         exchange_timestamp=self.trade_timestamp_ms / 1000.0, trade_id=self.sequential_id,
                         received_timestamp=received_timestamp)

    def summary(self) -> dict[str, Any]:
        return {
            "sequential_id": self.sequential_id, "trade_price": self.trade_price,
            "trade_volume": self.trade_volume, "ask_bid": self.ask_bid,
            "trade_timestamp": self.trade_timestamp_ms, "stream_type": self.stream_type,
        }


def parse_trade(obj: dict[str, Any]) -> UpbitTradeMessage:
    if obj.get("type") != "trade":
        raise UpbitParseError(f"not a trade message (type={obj.get('type')!r})")
    ask_bid = obj.get("ask_bid")
    if ask_bid not in ASK_BID_SIDE:
        raise UpbitParseError(f"ask_bid must be ASK or BID, got {ask_bid!r}")
    price, volume = _num(obj, "trade_price"), _num(obj, "trade_volume")
    if price <= 0 or volume <= 0:
        raise UpbitParseError(f"non-positive trade price/volume ({price}, {volume})")
    return UpbitTradeMessage(
        market=_market(obj), sequential_id=_int(obj, "sequential_id"), trade_price=price, trade_volume=volume,
        ask_bid=ask_bid, trade_timestamp_ms=_int(obj, "trade_timestamp"), exchange_timestamp_ms=_int(obj, "timestamp"),
        stream_type=_stream_type(obj), trade_date=_str(obj, "trade_date", required=False),
        trade_time=_str(obj, "trade_time", required=False),
        best_bid_price=_num(obj, "best_bid_price", required=False),
        best_ask_price=_num(obj, "best_ask_price", required=False),
    )


# --- error / status -------------------------------------------------------------------------

def parse_error(obj: dict[str, Any]) -> tuple[str, str]:
    err = obj.get("error")
    if not isinstance(err, dict):
        return "UNKNOWN", str(err)
    return str(err.get("name") or "UNKNOWN"), str(err.get("message") or "")


# --- requests -------------------------------------------------------------------------------

def build_subscription(
    ticket: str, markets: list[str] | tuple[str, ...], *, orderbook_units: int = 30, orderbook: bool = True,
    trades: bool = True,
) -> list[dict[str, Any]]:
    """Documented request: [ticket, type objects..., format]. `level` is never sent, so the
    server's default (0, no price grouping) applies."""
    if not ticket:
        raise ValueError("ticket must be non-empty")
    if not markets:
        raise ValueError("at least one market is required")
    if not (orderbook or trades):
        raise ValueError("subscribe to orderbook and/or trade")
    req: list[dict[str, Any]] = [{"ticket": ticket}]
    if orderbook:
        req.append({"type": "orderbook", "codes": [orderbook_code(m, orderbook_units) for m in markets]})
    if trades:
        req.append({"type": "trade", "codes": [validate_market(m) for m in markets]})
    req.append({"format": WS_FORMAT})
    return req
