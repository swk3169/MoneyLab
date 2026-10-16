"""Gross / cost analysis and the break-even one-way fee f* (BT-2b-4; bt-metrics/2, docs/backtest_bt2b4_metrics.md).

Decomposition (research mode, start in cash, end flat): equity only changes through price moves while a
position is held and through the cost of each leg, so with R round trips and leg ref prices
  sum r = G + R (c_b + c_s),     G = sum over round trips of ln(P_exit / P_entry)
where c_b, c_s are the log wealth multipliers of one buy and one sell (backtest.benchmarks.leg_cost_logs,
derived from backtest.costs.CostModel.buy / sell). G does not depend on any cost; this holds whatever the
fill timing (substituted fills, virtual_fallback, E3, DIAG), because every leg is valued at its ref price.

  gross_log_return     G (log return before any cost: equals net when fee, kappa and iota are 0)
  cost_log             -R (c_b + c_s) >= 0
  net_log_return       sum r (ledger), checked against G - cost_log (|error| <= 1e-9 * max(1, |sum r|))
  gross_to_cost_ratio  G / cost_log                       None: cost_log = 0 (zero_cost), G <= 0
  annual_cost_log      cost_log * 365 / T_d (log units per year, primary)
  annual_cost_fraction 1 - exp(-annual_cost_log) (share of wealth lost to costs per year, supplementary)
  annual_round_trips   R * 365 / T_d

Break-even fee f*: the one-way fee, equal for buy and sell, at which m_s = sum r / n = 0, with kappa,
iota, fee basis, signals and fills of the run held fixed (signals never depend on costs). With
K = ln(1 - kappa - iota) and A = (G + 2 R K) / R, the zero-fee net log return per round trip:
  inclusive  c_b = ln(1 - f) + K,  c_s = ln(1 - f) + K   =>  2 R ln(1 - f) = -(G + 2 R K)  =>  f* = 1 - exp(-A / 2)
  on_top     c_b = K - ln(1 + f),  c_s = ln(1 - f) + K   =>  ln((1 - f) / (1 + f)) = -A    =>  f* = tanh(A / 2)
f* is None (with a reason) without round trips, with an open position at the end, when the
decomposition does not hold, or when A < 0 (a loss even at zero fee). f* uses the run's capital
(C = 1,000,000 KRW, iota(C) of the run); no capital-size sensitivity.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from moneylab.backtest.benchmarks import leg_cost_logs
from moneylab.backtest.costs import BP, CostModel
from moneylab.backtest.performance import ANNUALIZATION_DAYS, check_finite, value
from moneylab.backtest.round_trips import RoundTrip
from moneylab.backtest.run import INITIAL_CASH_KRW

DECOMPOSITION_TOLERANCE = 1e-9


def gross_log_return(rts: Sequence[RoundTrip]) -> float:
    return sum(math.log(float(rt.exit_price / rt.entry_price)) for rt in rts)


def break_even_fee(gross: float, round_trips: int, k_log: float, fee_basis: str) -> dict[str, Any]:
    """f* as a fraction (and in bp) from G, R and K = ln(1 - kappa - iota)."""
    if round_trips == 0:
        return value(None, "no_round_trips", value_bps=None, zero_fee_round_trip_log_return=None)
    a = (gross + 2 * round_trips * k_log) / round_trips
    if a < 0:
        return value(None, "net_negative_at_zero_fee", value_bps=None, zero_fee_round_trip_log_return=a)
    if fee_basis == "inclusive":
        f = -math.expm1(-a / 2)
    elif fee_basis == "on_top":
        f = math.tanh(a / 2)
    else:
        raise ValueError(f"unknown fee basis {fee_basis!r}")
    f += 0.0  # -0.0 (A = 0) -> 0.0
    return value(f, value_bps=f * 10_000, zero_fee_round_trip_log_return=a)


def cost_analysis(rts: Sequence[RoundTrip], open_at_end: bool, returns: Sequence[float], costs: CostModel,
                  t_days: float, cost_totals_krw: dict[str, Any]) -> dict[str, Any]:
    check_finite(returns, "r")
    r_count = len(rts)
    c_b, c_s = leg_cost_logs(costs)
    k_log = math.log1p(-float((costs.slippage_bps + costs.impact_bps) / BP))
    net = sum(returns)
    gross = gross_log_return(rts)
    cost_log = -(r_count * (c_b + c_s)) + 0.0  # + 0.0 turns -0.0 into 0.0
    error = abs(net - (gross - cost_log))
    consistent = not open_at_end and error <= DECOMPOSITION_TOLERANCE * max(1.0, abs(net))
    fee_info = {"condition": "m_s = 0", "method": "analytic", "fee_basis": costs.fee_basis,
                "kappa_bps": str(costs.slippage_bps), "impact_bps": str(costs.impact_bps),
                "capital_krw": str(INITIAL_CASH_KRW), "round_trips": r_count, "symmetric_fee": True}
    if open_at_end:
        reason = "open_position_at_end"
    elif not consistent:
        reason = "decomposition_mismatch"
    else:
        reason = None
    if reason is not None:
        null = value(None, reason)
        return {"basis": "log", "consistent": False, "decomposition_error": error if not open_at_end else None,
                "gross_log_return": null, "cost_log": null, "net_log_return": value(net),
                "gross_to_cost_ratio": null, "annual_cost_log": null, "annual_cost_fraction": null,
                "annual_round_trips": null, "costs_krw": cost_totals_krw,
                "break_even_fee": fee_info | value(None, reason, value_bps=None, zero_fee_round_trip_log_return=None)}
    if cost_log == 0.0:
        ratio = value(None, "zero_cost")
    elif gross <= 0.0:
        ratio = value(None, "non_positive_gross")
    else:
        ratio = value(gross / cost_log)
    if math.isfinite(t_days) and t_days > 0:
        scale = ANNUALIZATION_DAYS / t_days
        annual = value(cost_log * scale)
        annual_fraction = value(-math.expm1(-cost_log * scale))
        annual_rt = value(r_count * scale)
    else:
        annual = annual_fraction = annual_rt = value(None, "non_positive_period")
    return {
        "basis": "log",
        "consistent": True,
        "decomposition_error": error,
        "gross_log_return": value(gross),
        "cost_log": value(cost_log),
        "net_log_return": value(net),
        "gross_to_cost_ratio": ratio,
        "annual_cost_log": annual,
        "annual_cost_fraction": annual_fraction,
        "annual_round_trips": annual_rt,
        "costs_krw": cost_totals_krw,
        "break_even_fee": fee_info | break_even_fee(gross, r_count, k_log, costs.fee_basis),
    }
