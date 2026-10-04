from __future__ import annotations

import logging

from moneylab.core.exceptions import ApiError, NetworkError, ProviderError
from moneylab.domain.models import Market
from moneylab.providers.base import MarketDataProvider, MarketQuery
from moneylab.providers.polymarket.gamma_client import GammaSource
from moneylab.providers.polymarket.parser import parse_gamma_market

log = logging.getLogger(__name__)


class PolymarketProvider(MarketDataProvider):
    name = "polymarket"

    def __init__(self, source: GammaSource):
        self.source = source

    def get_markets(self, query: MarketQuery) -> list[Market]:
        try:
            raw = self.source.fetch_markets(
                max_markets=query.max_markets,
                active_only=query.active_only,
                order=query.order_by,
                ascending=query.ascending,
            )
        except (ApiError, NetworkError) as exc:
            raise ProviderError(self.name, str(exc), exc) from exc
        except (OSError, ValueError) as exc:  # unreadable file / unexpected payload
            raise ProviderError(self.name, f"Bad market payload: {exc}", exc) from exc

        markets = [m for m in (parse_gamma_market(r) for r in raw) if m is not None]
        skipped = len(raw) - len(markets)
        if skipped:
            log.warning("Skipped %d unparseable markets", skipped)
        return markets

    def close(self) -> None:
        close = getattr(self.source, "close", None)
        if close:
            close()
