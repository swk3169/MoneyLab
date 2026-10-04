"""MarketDataProvider interface.

Contract for implementations:
  * return provider-neutral `Market` objects (never raw API dicts),
  * raise only `ProviderError` on failure (wrap transport/API errors),
  * be read-only: no orders, no wallets, no credentials.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from moneylab.domain.models import Market


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
