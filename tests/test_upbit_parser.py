"""Upbit WebSocket message parsing (SYNTHETIC messages shaped like the official docs examples)."""

import json

import pytest

from moneylab.providers.upbit.parser import (
    UpbitParseError,
    build_subscription,
    decode_frame,
    load_message,
    message_kind,
    parse_error,
    parse_orderbook,
    parse_trade,
)

# Shape of the docs' orderbook example (values invented)
BOOK = {
    "type": "orderbook", "code": "KRW-BTC", "timestamp": 1787727947526,
    "total_ask_size": 0.6, "total_bid_size": 0.9,
    "orderbook_units": [
        {"ask_price": 101.0, "bid_price": 99.0, "ask_size": 0.1, "bid_size": 0.4},
        {"ask_price": 103.0, "bid_price": 97.0, "ask_size": 0.2, "bid_size": 0.3},
        {"ask_price": 102.0, "bid_price": 98.0, "ask_size": 0.3, "bid_size": 0.2},  # deliberately out of order
    ],
    "stream_type": "SNAPSHOT", "level": 0,
}
TRADE = {
    "type": "trade", "code": "KRW-BTC", "timestamp": 1791282151281, "trade_date": "2026-10-06",
    "trade_time": "10:22:31", "trade_timestamp": 1791282151219, "trade_price": 100.0, "trade_volume": 0.5,
    "ask_bid": "BID", "prev_closing_price": 95.0, "change": "RISE", "change_price": 5.0,
    "sequential_id": 17912821512190000, "best_ask_price": 101.0, "best_ask_size": 0.2,
    "best_bid_price": 99.0, "best_bid_size": 0.1, "stream_type": "REALTIME",
}


def test_decode_frame_binary_text_and_invalid():
    assert decode_frame(b'{"a":1}') == ('{"a":1}', "binary")
    assert decode_frame('{"a":1}') == ('{"a":1}', "text")
    with pytest.raises(UpbitParseError):
        decode_frame(b"\xff\xfe")
    with pytest.raises(UpbitParseError):
        decode_frame(123)  # type: ignore[arg-type]


@pytest.mark.parametrize("text", ["{not json", "[1, 2]", '"x"', ""])
def test_load_message_rejects_non_objects(text):
    with pytest.raises(UpbitParseError):
        load_message(text)


def test_message_kind():
    assert message_kind(BOOK) == "orderbook"
    assert message_kind(TRADE) == "trade"
    assert message_kind({"status": "UP"}) == "status"
    assert message_kind({"error": {"name": "X", "message": "y"}}) == "error"
    assert message_kind({"type": "ticker"}) == "unknown"
    assert parse_error({"error": {"name": "INVALID_PARAM", "message": "bad"}}) == ("INVALID_PARAM", "bad")
    assert parse_error({"error": "weird"})[0] == "UNKNOWN"


def test_parse_orderbook_and_conversion():
    msg = parse_orderbook(BOOK)
    assert msg.market == "KRW-BTC" and msg.exchange_timestamp_ms == 1787727947526
    assert msg.stream_type == "SNAPSHOT" and msg.level == 0 and len(msg.units) == 3
    book = msg.to_order_book()
    assert book.token_id == "KRW-BTC" and book.market_id == "KRW-BTC"
    assert [lv.price for lv in book.bids] == [99.0, 98.0, 97.0]  # sorted best first
    assert [lv.price for lv in book.asks] == [101.0, 102.0, 103.0]
    assert book.timestamp == pytest.approx(1787727947.526)
    s = msg.summary()
    assert s["best_bid"] == 99.0 and s["best_ask"] == 101.0 and s["spread"] == 2.0
    assert s["bid_depth"] == pytest.approx(0.9) and s["ask_depth"] == pytest.approx(0.6)
    assert s["units"] == 3 and s["total_bid_size"] == 0.9 and s["level"] == 0


def test_parse_orderbook_drops_zero_size_levels_and_allows_empty():
    raw = {**BOOK, "orderbook_units": [{"ask_price": 101.0, "bid_price": 99.0, "ask_size": 0.0, "bid_size": 1.0}]}
    s = parse_orderbook(raw).summary()
    assert s["best_ask"] is None and s["spread"] is None and s["best_bid"] == 99.0
    assert parse_orderbook({**BOOK, "orderbook_units": []}).summary()["bid_levels"] == 0


@pytest.mark.parametrize("mutate", [
    lambda b: b.pop("timestamp"),
    lambda b: b.update(timestamp="1787727947526"),
    lambda b: b.update(timestamp=1.5),
    lambda b: b.update(code="krw-btc"),
    lambda b: b.pop("total_bid_size"),
    lambda b: b.update(orderbook_units="nope"),
    lambda b: b["orderbook_units"].append({"ask_price": 1.0}),
    lambda b: b["orderbook_units"].append("x"),
    lambda b: b["orderbook_units"][0].update(bid_size=-1.0),
    lambda b: b["orderbook_units"][0].update(bid_price="99"),
    lambda b: b["orderbook_units"][0].update(bid_price=True),
    lambda b: b["orderbook_units"][0].update(bid_price=float("nan")),
    lambda b: b.update(stream_type="DELTA"),
    lambda b: b.update(type="trade"),
])
def test_parse_orderbook_malformed(mutate):
    raw = json.loads(json.dumps(BOOK))
    mutate(raw)
    with pytest.raises(UpbitParseError):
        parse_orderbook(raw)


def test_parse_trade_and_conversion():
    tr = parse_trade(TRADE)
    assert tr.sequential_id == 17912821512190000  # > 2**53, exact as an int
    assert tr.side == "buy" and parse_trade({**TRADE, "ask_bid": "ASK"}).side == "sell"
    assert tr.exchange_timestamp_ms == 1791282151281 and tr.trade_timestamp_ms == 1791282151219
    tick = tr.to_trade_tick(received_timestamp=1791282151.3)
    assert tick.trade_id == 17912821512190000 and tick.price == 100.0 and tick.volume == 0.5
    assert tick.exchange_timestamp == pytest.approx(1791282151.219)  # execution time
    assert tick.received_timestamp == 1791282151.3 and tick.notional == 50.0
    assert tr.summary() == {"sequential_id": 17912821512190000, "trade_price": 100.0, "trade_volume": 0.5,
                            "ask_bid": "BID", "trade_timestamp": 1791282151219, "stream_type": "REALTIME"}


def test_sequential_id_survives_raw_json_round_trip():
    text = json.dumps(TRADE)
    assert parse_trade(load_message(text)).sequential_id == TRADE["sequential_id"]


@pytest.mark.parametrize("mutate", [
    lambda t: t.update(ask_bid="SELL"),
    lambda t: t.pop("sequential_id"),
    lambda t: t.update(sequential_id="17912821512190000"),
    lambda t: t.update(trade_price=0),
    lambda t: t.update(trade_volume=-1.0),
    lambda t: t.pop("trade_timestamp"),
    lambda t: t.pop("timestamp"),
    lambda t: t.update(code=""),
    lambda t: t.update(type="orderbook"),
])
def test_parse_trade_malformed(mutate):
    raw = dict(TRADE)
    mutate(raw)
    with pytest.raises(UpbitParseError):
        parse_trade(raw)


def test_build_subscription_matches_documented_shape():
    req = build_subscription("ticket-1", ["KRW-BTC"], orderbook_units=30)
    assert req == [
        {"ticket": "ticket-1"},
        {"type": "orderbook", "codes": ["KRW-BTC.30"]},
        {"type": "trade", "codes": ["KRW-BTC"]},
        {"format": "DEFAULT"},
    ]
    assert all("level" not in part for part in req)  # no price aggregation requested
    multi = build_subscription("t", ["KRW-BTC", "KRW-ETH"], orderbook_units=15, trades=False)
    assert multi[1]["codes"] == ["KRW-BTC.15", "KRW-ETH.15"] and len(multi) == 3


@pytest.mark.parametrize("kwargs", [
    {"ticket": "", "markets": ["KRW-BTC"]},
    {"ticket": "t", "markets": []},
    {"ticket": "t", "markets": ["KRW-BTC"], "orderbook_units": 10},
    {"ticket": "t", "markets": ["krw-btc"]},
    {"ticket": "t", "markets": ["KRW-BTC"], "orderbook": False, "trades": False},
])
def test_build_subscription_rejects_bad_input(kwargs):
    with pytest.raises(ValueError):
        build_subscription(**kwargs)
