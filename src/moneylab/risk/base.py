from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from moneylab.strategy.base import Signal


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    max_size: float = 0.0
    reason: str = ""


class RiskCheck(ABC):
    @abstractmethod
    def evaluate(self, signal: Signal, proposed_size: float) -> RiskDecision:
        """Approve, shrink or reject a proposed position."""
