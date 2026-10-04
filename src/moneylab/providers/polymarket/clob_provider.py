from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from moneylab.core.exceptions import ApiError, NetworkError, ProviderError
from moneylab.domain.market_params import MarketParams
from moneylab.domain.orderbook import BookSnapshot, MarketTimeline, OrderBook
from moneylab.providers.base import OrderBookProvider
from moneylab.providers.polymarket.clob_client import ClobSource
from moneylab.providers.polymarket.clob_parser import (
    parse_clob_market_info,
    parse_order_book,
    parse_order_books,
    parse_rewards,
)

log = logging.getLogger(__name__)

# Documented maker rebate share per category (docs "Fees", checked 2026-10-04).
# /clob-markets does not return it; Gamma `feeSchedule.rebateRate` does (when available).
CATEGORY_REBATE_RATE = {
    "crypto": 0.20, "sports": 0.15, "finance": 0.25, "politics": 0.25, "economics": 0.25,
    "culture": 0.25, "weather": 0.25, "other": 0.25, "mentions": 0.25, "tech": 0.25, "geopolitics": 0.0,
}


class PolymarketClobProvider(OrderBookProvider):
    name = "polymarket-clob"

    def __init__(self, source: ClobSource, rebate_rate: float = 0.0):
        self.source = source
        self.rebate_rate = rebate_rate

    def _call(self, what: str, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except (ApiError, NetworkError) as exc:
            raise ProviderError(self.name, str(exc), exc) from exc
        except (OSError, LookupError, ValueError, TypeError) as exc:
            raise ProviderError(self.name, f"Bad {what} payload: {exc}", exc) from exc

    def get_order_book(self, token_id: str) -> OrderBook:
        return self._call("book", lambda: parse_order_book(self.source.fetch_book(token_id)))

    def get_order_books(self, token_ids: list[str]) -> dict[str, OrderBook]:
        return self._call("books", lambda: parse_order_books(self.source.fetch_books(token_ids)))

    def get_market_params(self, condition_id: str) -> MarketParams:
        try:
            rewards = parse_rewards(self.source.fetch_rewards(condition_id))
        except (ApiError, NetworkError, OSError, ValueError) as exc:
            log.warning("Rewards config unavailable for %s: %s", condition_id, exc)
            rewards = None
        return self._call(
            "market info",
            lambda: parse_clob_market_info(
                self.source.fetch_market_info(condition_id), condition_id, rewards, self.rebate_rate
            ),
        )

    def close(self) -> None:
        close = getattr(self.source, "close", None)
        if close:
            close()


def load_timeline(path: str | Path) -> MarketTimeline:
    """Load a replay timeline. Raw payloads inside use the exact CLOB response shapes, so a
    recorder saving live /books responses produces the same format:

    {
      "meta": {"synthetic": true, "description": "...", "rebate_rate": 0.25},
      "condition_id": "...",
      "market_info": <GET /clob-markets/{condition_id} response>,
      "rewards": <GET /rewards/markets/{condition_id} response> | null,
      "snapshots": [{"ts": <unix s>, "books": [<GET /book response>, ...], "signals": {...}}],
      "resolution": {"<token_id>": 1.0, "<token_id>": 0.0} | null
    }
    Raises ProviderError on unreadable or malformed files.
    """
    name = "polymarket-timeline"
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        meta = raw.get("meta") or {}
        condition_id = str(raw["condition_id"])
        rewards = parse_rewards(raw["rewards"]) if raw.get("rewards") else None
        params = parse_clob_market_info(raw["market_info"], condition_id, rewards, float(meta.get("rebate_rate", 0.0)))
        snapshots = []
        for snap in raw["snapshots"]:
            ts = float(snap["ts"])
            books = {b.token_id: b for b in (parse_order_book(x) for x in snap["books"])}
            # A book without its own timestamp is treated as observed at snapshot time.
            books = {k: b if b.timestamp is not None else _with_ts(b, ts) for k, b in books.items()}
            signals = {str(k): float(v) for k, v in (snap.get("signals") or {}).items()}
            snapshots.append(BookSnapshot(timestamp=ts, books=books, signals=signals))
        resolution = {str(k): float(v) for k, v in raw["resolution"].items()} if raw.get("resolution") else None
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ProviderError(name, f"Bad timeline {path}: {exc}", exc) from exc
    snapshots.sort(key=lambda s: s.timestamp)
    return MarketTimeline(
        params=params,
        snapshots=tuple(snapshots),
        resolution=resolution,
        synthetic=bool(meta.get("synthetic", True)),
        description=str(meta.get("description", "")),
    )


def _with_ts(book: OrderBook, ts: float) -> OrderBook:
    return replace(book, timestamp=ts)
