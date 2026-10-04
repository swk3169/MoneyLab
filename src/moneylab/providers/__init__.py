"""Market data providers. Everything above this layer depends only on MarketDataProvider."""

from moneylab.providers.base import MarketDataProvider, MarketQuery

__all__ = ["MarketDataProvider", "MarketQuery"]
