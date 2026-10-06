"""UpbitMarketDataProvider: public market list (REST `GET /v1/market/all`, read-only).

Response fields used (https://docs.upbit.com/kr/reference/list-trading-pairs):
  market, korean_name, english_name, market_event{warning, caution{...}} (with is_details=true)
Rate limit: 10 requests/s per IP (quotation group). One call per `get_markets`.

Upbit pairs are spot markets, not prediction markets: `Market.outcomes` stays empty and the
price fields are left unset (this endpoint does not serve prices).
"""

from __future__ import annotations

import logging
from typing import Any

from moneylab.core.exceptions import ApiError, NetworkError, ProviderError
from moneylab.core.http import HttpClient
from moneylab.domain.models import Market
from moneylab.providers.base import MarketDataProvider, MarketQuery
from moneylab.providers.upbit.endpoints import REST_MARKET_ALL, validate_market

log = logging.getLogger(__name__)


def parse_market(raw: Any) -> Market | None:
    if not isinstance(raw, dict):
        return None
    try:
        code = validate_market(str(raw.get("market") or ""))
    except ValueError:
        return None
    event = raw.get("market_event") if isinstance(raw.get("market_event"), dict) else None
    return Market(
        source="upbit", market_id=code, question=str(raw.get("english_name") or code),
        active=True, closed=False, slug=code, url=None,
        extra={"korean_name": raw.get("korean_name"), "english_name": raw.get("english_name"),
               "quote_currency": code.split("-", 1)[0], "market_event": event},
    )


class UpbitMarketDataProvider(MarketDataProvider):
    name = "upbit"

    def __init__(self, http: HttpClient, quote_currency: str | None = "KRW"):
        self.http = http
        self.quote_currency = quote_currency

    def get_markets(self, query: MarketQuery) -> list[Market]:
        try:
            raw = self.http.get_json(REST_MARKET_ALL, params={"is_details": "true"})
        except (ApiError, NetworkError) as exc:
            raise ProviderError(self.name, str(exc), exc) from exc
        if not isinstance(raw, list):
            raise ProviderError(self.name, f"{REST_MARKET_ALL} returned {type(raw).__name__}, expected a list")
        markets = [m for m in (parse_market(r) for r in raw) if m is not None]
        if len(markets) != len(raw):
            log.warning("Skipped %d unparseable Upbit markets", len(raw) - len(markets))
        if self.quote_currency:
            markets = [m for m in markets if m.extra.get("quote_currency") == self.quote_currency]
        return markets[: query.max_markets]

    def close(self) -> None:
        self.http.close()
