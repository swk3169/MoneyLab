from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from moneylab.domain.models import Market


@dataclass(frozen=True)
class Signal:
    """A trade idea. Sizing, risk checks and execution happen downstream."""

    market_id: str
    outcome: str  # e.g. "Yes"
    side: Literal["buy", "sell"]
    fair_probability: float  # strategy's estimate, 0..1
    reference_price: float  # market price the edge was measured against
    rationale: str = ""

    @property
    def edge(self) -> float:
        """Gross edge per share before costs."""
        if self.side == "buy":
            return self.fair_probability - self.reference_price
        return self.reference_price - self.fair_probability


class Strategy(ABC):
    name: str = "abstract"

    @abstractmethod
    def generate(self, markets: list[Market]) -> list[Signal]:
        """Pure function of market data -> signals. Must not perform I/O or trading."""
