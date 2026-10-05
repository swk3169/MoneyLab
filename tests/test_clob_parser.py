import json

import pytest
from conftest import FIXTURES, FakeSession, make_response

from moneylab.core.exceptions import ProviderError
from moneylab.core.http import HttpClient
from moneylab.domain.orderbook import OrderBook
from moneylab.providers.polymarket import (
    ClobApiSource,
    ClobFileSource,
    PolymarketClobProvider,
    load_timeline,
    parse_gamma_market,
)
from moneylab.providers.polymarket.clob_parser import (
    parse_clob_market_info,
    parse_order_book,
    parse_rewards,
    parse_timestamp,
)
from moneylab.providers.polymarket.parser import parse_gamma_fee_schedule, parse_gamma_reward_config

BOOKS = json.loads((FIXTURES / "clob_books_sample.json").read_text(encoding="utf-8"))
INFO = json.loads((FIXTURES / "clob_market_info_sample.json").read_text(encoding="utf-8"))
REWARDS = json.loads((FIXTURES / "clob_rewards_market_sample.json").read_text(encoding="utf-8"))


# --- order book sorting / normalization ----------------------------------------

def test_book_sorted_best_first_even_when_payload_is_ascending():
    raw = BOOKS[0]
    assert [lv["price"] for lv in raw["bids"]] == sorted(lv["price"] for lv in raw["bids"])  # fixture is ascending
    book = parse_order_book(raw)
    assert [lv.price for lv in book.bids] == sorted((lv.price for lv in book.bids), reverse=True)
    assert [lv.price for lv in book.asks] == sorted(lv.price for lv in book.asks)
    assert book.best_bid == 0.45 and book.best_ask == 0.47
    assert book.best_bid_size == 140 and book.best_ask_size == 340
    assert book.tick_size == 0.01 and book.min_order_size == 5
    assert book.timestamp == 1791072000.0  # ms -> s
    assert book.mid == pytest.approx(0.46) and book.spread == pytest.approx(0.02)


def test_book_merges_duplicates_and_drops_bad_levels():
    raw = {
        "asset_id": "T",
        "bids": [{"price": "0.40", "size": "10"}, {"price": "0.40", "size": "5"}, {"price": "0.41", "size": "0"},
                 {"price": "1.5", "size": "9"}, {"price": "x", "size": "1"}, "junk"],
        "asks": [{"price": 0.6, "size": 7}, {"price": "0.55", "size": "3"}],
    }
    book = parse_order_book(raw)
    assert [(lv.price, lv.size) for lv in book.bids] == [(0.40, 15.0)]
    assert [(lv.price, lv.size) for lv in book.asks] == [(0.55, 3.0), (0.6, 7.0)]
    assert book.tick_size == 0.01  # default when missing


def test_empty_and_one_sided_books():
    book = parse_order_book({"asset_id": "T", "bids": [], "asks": [{"price": "0.5", "size": "1"}]})
    assert book.best_bid is None and book.mid is None and book.spread is None
    assert OrderBook.build("T", [], []).best_ask is None


def test_book_without_asset_id_rejected():
    with pytest.raises(ValueError):
        parse_order_book({"bids": [], "asks": []})


def test_timestamp_units():
    assert parse_timestamp("1700000000") == 1700000000.0
    assert parse_timestamp("1700000000123") == pytest.approx(1700000000.123)
    assert parse_timestamp(None) is None


# --- market params / rewards ----------------------------------------------------

def test_clob_market_info():
    params = parse_clob_market_info(INFO, "0xc", rebate_rate=0.25)
    assert params.yes_token.endswith("0001") and params.no_token.endswith("0002")
    assert params.tick_size == 0.01 and params.min_order_size == 5
    assert params.fee.rate == 0.04 and params.fee.exponent == 1 and params.fee.taker_only
    assert params.fee.rebate_rate == 0.25 and params.fee.enabled
    assert params.complement(params.yes_token) == params.no_token


def test_clob_market_info_without_fee_details_is_free():
    params = parse_clob_market_info({"t": [{"t": "a", "o": "Yes"}, {"t": "b", "o": "No"}]}, "0xc")
    assert not params.fee.enabled
    with pytest.raises(ValueError):
        parse_clob_market_info({"t": []}, "0xc")


def test_rewards_config():
    from datetime import date

    cfg = parse_rewards(REWARDS)
    assert cfg.max_spread_cents == 3 and cfg.min_size == 50
    assert cfg.daily_rate(date(2026, 10, 4)) == 20
    assert cfg.daily_rate(date(2026, 11, 5)) == 0
    assert parse_rewards({"data": []}) is None
    assert parse_rewards({"data": [{"rewards_min_size": 1}]}) is None


def test_gamma_fee_and_reward_fields_from_docs_example():
    raw = {
        "id": "1", "question": "Q?", "feesEnabled": True,
        "feeSchedule": {"rate": 0.04, "exponent": 1, "takerOnly": True, "rebateRate": 0.25},
        "rewardsMinSize": "100", "rewardsMaxSpread": 3,
        "clobRewards": [{"rewardsDailyRate": "100", "startDate": "2026-07-01", "endDate": "2026-07-31"}],
    }
    m = parse_gamma_market(raw)
    assert m.fee_schedule.rate == 0.04 and m.fee_schedule.rebate_rate == 0.25 and m.fee_schedule.enabled
    assert m.reward_config.min_size == 100 and m.reward_config.daily_rate() == 100
    assert parse_gamma_fee_schedule({"feesEnabled": False}).enabled is False
    assert parse_gamma_fee_schedule({}) is None  # unknown, not free
    assert parse_gamma_reward_config({}) is None


def test_existing_gamma_fixture_has_no_fee_fields(gamma_sample):
    markets = [parse_gamma_market(r) for r in gamma_sample]
    assert all(m is None or m.fee_schedule is None for m in markets)


# --- provider / HTTP -------------------------------------------------------------

def test_api_source_requests_and_provider_parsing():
    def handler(method, url, params):
        if url.endswith("/book"):
            assert method == "GET" and params == {"token_id": BOOKS[0]["asset_id"]}
            return make_response(200, json.dumps(BOOKS[0]), url=url)
        if url.endswith("/books"):
            assert method == "POST"
            return make_response(200, json.dumps(BOOKS), url=url)
        if "/clob-markets/" in url:
            return make_response(200, json.dumps(INFO), url=url)
        if "/rewards/markets/" in url:
            return make_response(200, json.dumps(REWARDS), url=url)
        raise AssertionError(url)

    saved = []
    session = FakeSession(handler)
    http = HttpClient("https://clob.example", session=session)
    provider = PolymarketClobProvider(ClobApiSource(http, raw_sink=lambda n, p: saved.append(n)), rebate_rate=0.25)
    book = provider.get_order_book(BOOKS[0]["asset_id"])
    assert book.best_bid == 0.45
    books = provider.get_order_books([b["asset_id"] for b in BOOKS])
    assert len(books) == 2
    params = provider.get_market_params("0xc")
    assert params.rewards.min_size == 50 and params.fee.rebate_rate == 0.25
    assert saved == ["clob_book", "clob_books", "clob_rewards", "clob_market_info"]
    assert [c[0] for c in session.calls] == ["GET", "POST", "GET", "GET"]


def test_http_451_becomes_provider_error_with_diagnostics(response_451_json):
    http = HttpClient("https://clob.example", session=FakeSession(lambda m, u, p: response_451_json))
    provider = PolymarketClobProvider(ClobApiSource(http))
    with pytest.raises(ProviderError) as exc:
        provider.get_order_book("tok")
    assert exc.value.diagnostics.status_code == 451


def test_rewards_failure_does_not_block_market_params(response_451_json):
    def handler(method, url, params):
        if "/rewards/" in url:
            return response_451_json
        return make_response(200, json.dumps(INFO), url=url)

    provider = PolymarketClobProvider(ClobApiSource(HttpClient("https://x", session=FakeSession(handler))))
    params = provider.get_market_params("0xc")
    assert params.rewards is None and params.fee.rate == 0.04


@pytest.mark.parametrize("body", ["not json", json.dumps({"asset_id": None}), json.dumps([1, 2])])
def test_bad_payloads_become_provider_error(body):
    http = HttpClient("https://x", session=FakeSession(lambda m, u, p: make_response(200, body, url=u)))
    provider = PolymarketClobProvider(ClobApiSource(http))
    with pytest.raises(ProviderError):
        provider.get_order_book("tok")


def test_file_source():
    src = ClobFileSource(FIXTURES / "clob_books_sample.json", FIXTURES / "clob_market_info_sample.json",
                         FIXTURES / "clob_rewards_market_sample.json")
    provider = PolymarketClobProvider(src)
    token = BOOKS[1]["asset_id"]
    assert provider.get_order_book(token).token_id == token
    assert provider.get_market_params("0xc").rewards is not None
    with pytest.raises(ProviderError):
        provider.get_order_book("missing")


def test_load_timeline_fixtures():
    tl = load_timeline(FIXTURES / "clob_timeline_mm.json")
    assert tl.synthetic and len(tl.snapshots) == 120 and tl.resolution is None
    assert tl.params.fee.rebate_rate == 0.25 and tl.params.rewards.max_spread_cents == 3
    ts = [s.timestamp for s in tl.snapshots]
    assert ts == sorted(ts)
    tl2 = load_timeline(FIXTURES / "clob_timeline_mispricing.json")
    assert tl2.resolution[tl2.params.yes_token] == 1.0
    assert "fair_yes" in tl2.snapshots[0].signals


def test_load_timeline_errors(tmp_path):
    with pytest.raises(ProviderError):
        load_timeline(tmp_path / "missing.json")
    bad = tmp_path / "bad.json"
    bad.write_text('{"condition_id": "x"}', encoding="utf-8")
    with pytest.raises(ProviderError):
        load_timeline(bad)
