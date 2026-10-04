"""Risk management (planned): pre-trade checks (exposure caps, liquidity, max loss,
kill switch). Every order path - paper or live - must pass through RiskCheck."""

from moneylab.risk.base import RiskCheck, RiskDecision

__all__ = ["RiskCheck", "RiskDecision"]
