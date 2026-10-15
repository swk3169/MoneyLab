"""BT-1 performance numbers from a ledger (descriptive only; no profitability verdict).

  cumulative_net_return   final equity / initial cash - 1 (after all costs)
  max_drawdown            largest peak-to-trough fall of the equity curve [initial cash, daily equity
                          after trades], as a fraction; analytics.metrics.max_drawdown
  trade counts            legs, buys, sells (= closed round trips), virtual exits, unfilled orders
  cost totals             fees, slippage, both (KRW)
  daily_log_returns       ln(E_pre(R_{t+1}) / E_pre(R_t)) with E_pre the equity before the trade at a
                          reference time; the last day ends after the virtual exit. Day t thus carries
                          the trade made at its start, the convention of the v0.6 segment returns.
Sharpe, Sortino, CAGR and the rest are BT-2.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from moneylab.analytics.metrics import max_drawdown as _max_drawdown
from moneylab.backtest.ledger import Ledger


def equity_curve(ledger: Ledger) -> list[Decimal]:
    return [ledger.initial_cash] + [d.equity for d in ledger.daily]


def cumulative_net_return(ledger: Ledger) -> Decimal:
    curve = equity_curve(ledger)
    return curve[-1] / curve[0] - 1


def max_drawdown(ledger: Ledger) -> float:
    return _max_drawdown([float(v) for v in equity_curve(ledger)])


def trade_counts(ledger: Ledger) -> dict[str, int]:
    buys = sum(1 for t in ledger.trades if t.side == "buy")
    sells = sum(1 for t in ledger.trades if t.side == "sell")
    return {"legs": len(ledger.trades), "buys": buys, "sells": sells, "round_trips": sells,
            "virtual_exits": sum(1 for t in ledger.trades if t.virtual), "unfilled": len(ledger.unfilled)}


def cost_totals(ledger: Ledger) -> dict[str, Decimal]:
    fees = sum((t.fee for t in ledger.trades), Decimal(0))
    slip = sum((t.slippage_cost for t in ledger.trades), Decimal(0))
    return {"fees": fees, "slippage": slip, "total": fees + slip}


def daily_log_returns(ledger: Ledger) -> list[float]:
    rows = ledger.daily
    if len(rows) < 2:
        return []
    out = []
    for i in range(len(rows) - 1):
        end = rows[i + 1].equity if i + 1 == len(rows) - 1 else rows[i + 1].equity_before_trade
        out.append(math.log(end / rows[i].equity_before_trade))
    return out


def summary(ledger: Ledger) -> dict[str, Any]:
    costs = cost_totals(ledger)
    return {"label": "descriptive, SYNTHETIC / NOT_EVIDENCE in BT-1",
            "cumulative_net_return": str(cumulative_net_return(ledger)),
            "max_drawdown": max_drawdown(ledger), "trade_counts": trade_counts(ledger),
            "cost_totals": {k: str(v) for k, v in costs.items()},
            "final_equity": str(equity_curve(ledger)[-1]), "days_valued": len(ledger.daily)}
