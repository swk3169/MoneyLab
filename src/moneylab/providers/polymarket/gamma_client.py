"""Raw access to Polymarket Gamma market data.

Gamma API (public, no auth): https://gamma-api.polymarket.com
  GET /markets?limit=&offset=&active=&closed=&order=&ascending=

Two interchangeable sources return the *raw* list of market dicts:
  * GammaApiSource  - live HTTP
  * GammaFileSource - a saved JSON response (data/raw/... or tests/fixtures/...)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Protocol

from moneylab.core.http import HttpClient

log = logging.getLogger(__name__)

PAGE_SIZE = 100


class GammaSource(Protocol):
    def fetch_markets(
        self, max_markets: int, active_only: bool, order: str | None, ascending: bool
    ) -> list[dict[str, Any]]: ...


def _extract_list(payload: Any) -> list[dict[str, Any]]:
    """/markets returns a JSON array. Accept {"data": [...]} too, in case the shape changes."""
    if isinstance(payload, list):
        return [m for m in payload if isinstance(m, dict)]
    if isinstance(payload, dict):
        for key in ("data", "markets"):
            if isinstance(payload.get(key), list):
                return [m for m in payload[key] if isinstance(m, dict)]
    raise ValueError(f"Unexpected /markets payload type: {type(payload).__name__}")


class GammaApiSource:
    def __init__(self, http: HttpClient, raw_sink=None):
        """raw_sink(name, payload) is called with every raw page (e.g. to save to data/raw)."""
        self.http = http
        self.raw_sink = raw_sink

    def fetch_markets(
        self, max_markets: int, active_only: bool = True, order: str | None = None, ascending: bool = False
    ) -> list[dict[str, Any]]:
        markets: list[dict[str, Any]] = []
        offset = 0
        while len(markets) < max_markets:
            limit = min(PAGE_SIZE, max_markets - len(markets))
            params: dict[str, Any] = {"limit": limit, "offset": offset}
            if active_only:
                params.update(active="true", closed="false")
            if order:
                params.update(order=order, ascending=str(ascending).lower())
            payload = self.http.get_json("/markets", params=params)
            if self.raw_sink:
                self.raw_sink(f"gamma_markets_offset{offset}", payload)
            page = _extract_list(payload)
            markets.extend(page)
            log.info("Gamma /markets offset=%d -> %d markets", offset, len(page))
            if len(page) < limit:
                break
            offset += len(page)
        return markets[:max_markets]

    def close(self) -> None:
        self.http.close()


class GammaFileSource:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def fetch_markets(
        self, max_markets: int, active_only: bool = True, order: str | None = None, ascending: bool = False
    ) -> list[dict[str, Any]]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        markets = _extract_list(payload)
        if active_only:  # mirror the API's active=true&closed=false filter
            from moneylab.providers.polymarket.parser import to_bool

            markets = [m for m in markets if to_bool(m.get("active"), True) and not to_bool(m.get("closed"), False)]
        return markets[:max_markets]

    def close(self) -> None:
        pass
