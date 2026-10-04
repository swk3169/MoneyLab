"""Raw access to Polymarket CLOB public market-data endpoints (read-only, no auth).

CLOB API: https://clob.polymarket.com  (CLOB V2, live since 2026-04-28)
  GET  /book?token_id=
  POST /books                 body: [{"token_id": ...}, ...]   (read-only batch query)
  GET  /clob-markets/{condition_id}
  GET  /rewards/markets/{condition_id}

Two interchangeable sources return *raw* payloads:
  * ClobApiSource  - live HTTP through core.http.HttpClient
  * ClobFileSource - saved JSON (tests/fixtures/... or data/raw/polymarket/clob/...)

Deliberately absent: order placement, cancellation, authentication, signing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from moneylab.core.http import HttpClient


class ClobSource(Protocol):
    def fetch_book(self, token_id: str) -> Any: ...
    def fetch_books(self, token_ids: list[str]) -> Any: ...
    def fetch_market_info(self, condition_id: str) -> Any: ...
    def fetch_rewards(self, condition_id: str) -> Any: ...


class ClobApiSource:
    def __init__(self, http: HttpClient, raw_sink=None):
        """raw_sink(name, payload) receives every raw payload (e.g. RawStore for data/raw)."""
        self.http = http
        self.raw_sink = raw_sink

    def _sink(self, name: str, payload: Any) -> Any:
        if self.raw_sink:
            self.raw_sink(name, payload)
        return payload

    def fetch_book(self, token_id: str) -> Any:
        return self._sink("clob_book", self.http.get_json("/book", params={"token_id": token_id}))

    def fetch_books(self, token_ids: list[str]) -> Any:
        body = [{"token_id": t} for t in token_ids]
        return self._sink("clob_books", self.http.post_json("/books", body))

    def fetch_market_info(self, condition_id: str) -> Any:
        return self._sink("clob_market_info", self.http.get_json(f"/clob-markets/{condition_id}"))

    def fetch_rewards(self, condition_id: str) -> Any:
        return self._sink("clob_rewards", self.http.get_json(f"/rewards/markets/{condition_id}"))

    def close(self) -> None:
        self.http.close()


class ClobFileSource:
    """Serves saved payloads. `books` may be a single /book object or a /books list."""

    def __init__(self, books: str | Path, market_info: str | Path | None = None, rewards: str | Path | None = None):
        self.books_path = Path(books)
        self.market_info_path = Path(market_info) if market_info else None
        self.rewards_path = Path(rewards) if rewards else None

    @staticmethod
    def _load(path: Path | None) -> Any:
        if path is None:
            raise FileNotFoundError("no fixture file configured")
        return json.loads(path.read_text(encoding="utf-8"))

    def _all_books(self) -> list[dict[str, Any]]:
        payload = self._load(self.books_path)
        return payload if isinstance(payload, list) else [payload]

    def fetch_book(self, token_id: str) -> Any:
        for b in self._all_books():
            if isinstance(b, dict) and str(b.get("asset_id")) == token_id:
                return b
        raise LookupError(f"token {token_id} not in {self.books_path.name}")

    def fetch_books(self, token_ids: list[str]) -> Any:
        wanted = set(token_ids)
        return [b for b in self._all_books() if isinstance(b, dict) and str(b.get("asset_id")) in wanted]

    def fetch_market_info(self, condition_id: str) -> Any:
        return self._load(self.market_info_path)

    def fetch_rewards(self, condition_id: str) -> Any:
        return self._load(self.rewards_path)

    def close(self) -> None:
        pass
