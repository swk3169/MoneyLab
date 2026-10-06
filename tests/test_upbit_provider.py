"""UpbitMarketDataProvider (REST GET /v1/market/all) with a FakeSession. Payloads are SYNTHETIC,
shaped like the docs' response fields."""

import json

import pytest
from conftest import FakeSession, make_response

from moneylab.core.exceptions import NetworkError, ProviderError
from moneylab.core.http import HttpClient
from moneylab.providers.base import MarketQuery
from moneylab.providers.upbit import UpbitMarketDataProvider
from moneylab.providers.upbit.endpoints import REST_BASE_URL

MARKETS = [
    {"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin",
     "market_event": {"warning": False, "caution": {"PRICE_FLUCTUATIONS": False}}},
    {"market": "KRW-ETH", "korean_name": "이더리움", "english_name": "Ethereum"},
    {"market": "BTC-ETH", "korean_name": "이더리움", "english_name": "Ethereum"},
    {"market": "bad code"},
    "not an object",
]


def provider(handler) -> tuple[UpbitMarketDataProvider, FakeSession]:
    session = FakeSession(handler)
    return UpbitMarketDataProvider(HttpClient(REST_BASE_URL, session=session)), session


def test_get_markets_parses_and_filters_quote_currency():
    p, session = provider(lambda m, u, params: make_response(200, json.dumps(MARKETS)))
    markets = p.get_markets(MarketQuery())
    assert [m.market_id for m in markets] == ["KRW-BTC", "KRW-ETH"]
    btc = markets[0]
    assert btc.source == "upbit" and btc.question == "Bitcoin" and btc.outcomes == ()
    assert btc.extra["korean_name"] == "비트코인" and btc.extra["market_event"]["warning"] is False
    method, url, params = session.calls[0]
    assert method == "GET" and url == "https://api.upbit.com/v1/market/all" and params == {"is_details": "true"}
    assert "Authorization" not in session.headers
    assert len(p.get_markets(MarketQuery(max_markets=1))) == 1


@pytest.mark.parametrize("handler", [
    lambda m, u, p: make_response(451, "blocked", reason="Unavailable For Legal Reasons"),
    lambda m, u, p: make_response(200, "{not json"),
    lambda m, u, p: make_response(200, json.dumps({"error": "x"})),
    lambda m, u, p: NetworkError("down"),
])
def test_get_markets_failures_become_provider_errors(handler):
    p, _ = provider(handler)
    with pytest.raises(ProviderError):
        p.get_markets(MarketQuery())
