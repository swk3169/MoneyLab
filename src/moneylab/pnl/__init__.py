"""PnL tracking: fills -> positions -> decomposed PnL (spread, slippage, inventory, fees) with
estimated and realized incentives kept apart. Feeds moneylab.analytics.metrics."""

from moneylab.pnl.ledger import Ledger
from moneylab.pnl.report import AdoptionVerdict, PnLBreakdown, evaluate_adoption

__all__ = ["AdoptionVerdict", "Ledger", "PnLBreakdown", "evaluate_adoption"]
