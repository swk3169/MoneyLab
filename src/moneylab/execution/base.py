from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

OrderType = Literal["GTC", "GTD", "FOK", "FAK"]
# GTC/GTD are documented for CLOB V2 limit orders. FOK/FAK (immediate) semantics follow
# common exchange usage and are used here for paper simulation only (unverified naming).


@dataclass(frozen=True)
class OrderRequest:
    market_id: str
    token_id: str
    side: Literal["buy", "sell"]
    price: float
    size: float
    order_type: OrderType = "GTC"
    post_only: bool = False  # reject instead of taking liquidity (paper engine semantics)
    group_id: str | None = None  # links legs of one trade idea (e.g. both legs of an arb)


@dataclass(frozen=True)
class Fill:
    """One execution. Reference prices let the ledger decompose PnL:

    mid_ref  - mid used for spread-captured accounting (maker: last mid observed while the
               order rested, before the fill snapshot; taker: mid at decision time)
    top_ref  - best opposite price at decision time (taker only; maker = own price)
    """

    order_id: str
    market_id: str
    token_id: str
    side: Literal["buy", "sell"]
    price: float
    size: float
    liquidity: Literal["maker", "taker"]
    fee: float
    mid_ref: float
    top_ref: float
    timestamp: float
    fee_equivalent: float = 0.0  # maker fills: basis for the *estimated* rebate
    group_id: str | None = None

    @property
    def sign(self) -> int:
        return 1 if self.side == "buy" else -1


class ExecutionClient(ABC):
    """Implemented by paper (simulated) and, much later, live venues."""

    @abstractmethod
    def submit(self, order: OrderRequest) -> str:
        """Submit an order and return an order id."""

    @abstractmethod
    def cancel(self, order_id: str) -> None: ...

    @abstractmethod
    def cancel_all(self) -> int:
        """Cancel every outstanding order. Returns the number cancelled (kill-switch path)."""
