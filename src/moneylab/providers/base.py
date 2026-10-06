"""MarketDataProvider interface.

Contract for implementations:
  * return provider-neutral `Market` objects (never raw API dicts),
  * raise only `ProviderError` on failure (wrap transport/API errors),
  * be read-only: no orders, no wallets, no credentials.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

from moneylab.domain.market_params import MarketParams
from moneylab.domain.models import Market
from moneylab.domain.orderbook import BookSnapshot, OrderBook
from moneylab.domain.trades import TradeTick


@dataclass(frozen=True)
class MarketQuery:
    """Server-side query hints. Providers apply what they support; the scanner filters the rest."""

    max_markets: int = 200
    active_only: bool = True
    order_by: str | None = "volume24hr"  # provider-specific key; providers may ignore
    ascending: bool = False


class MarketDataProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def get_markets(self, query: MarketQuery) -> list[Market]:
        """Fetch markets. Raises ProviderError on failure."""

    def close(self) -> None:  # noqa: B027 - optional hook
        """Release resources (sessions, files)."""


class OrderBookProvider(ABC):
    """Read-only order-book and market-parameter access. Raises only ProviderError."""

    name: str = "abstract"

    @abstractmethod
    def get_order_book(self, token_id: str) -> OrderBook: ...

    def get_order_books(self, token_ids: list[str]) -> dict[str, OrderBook]:
        return {t: self.get_order_book(t) for t in token_ids}

    @abstractmethod
    def get_market_params(self, condition_id: str) -> MarketParams: ...

    def close(self) -> None:  # noqa: B027 - optional hook
        """Release resources."""


@dataclass(frozen=True)
class RecordedEvent:
    """One entry of a recorded dataset: a book snapshot, trades, or a recorded data-source failure.

    `received_timestamp` / `local_sequence` are set by recorders that keep them (streaming
    sources); they let consumers analyse latency and order events deterministically.
    """

    timestamp: float
    snapshot: BookSnapshot | None = None
    error: str | None = None
    trades: tuple[TradeTick, ...] = ()
    received_timestamp: float | None = None
    local_sequence: int | None = None


class RecordedBookSource(ABC):
    """A previously recorded, replayable order-book dataset for one market (read-only).

    Implementations yield events in recording order; they must not touch the network.
    Raises only ProviderError.
    """

    name: str = "abstract"
    params: MarketParams
    synthetic: bool = False
    description: str = ""

    @abstractmethod
    def iter_events(self) -> Iterator[RecordedEvent]: ...
