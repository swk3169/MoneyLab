from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class OrderRequest:
    market_id: str
    token_id: str
    side: Literal["buy", "sell"]
    price: float
    size: float


class ExecutionClient(ABC):
    """Implemented by paper (simulated) and, much later, live venues."""

    @abstractmethod
    def submit(self, order: OrderRequest) -> str:
        """Submit an order and return an order id."""

    @abstractmethod
    def cancel(self, order_id: str) -> None: ...
