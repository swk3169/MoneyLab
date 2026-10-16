"""Performance metrics of a return series (BT-2b-3; definition version bt-metrics/1, docs/backtest_bt2b3_metrics.md).

Pure functions on floats. Inputs are the daily net log returns r_0..r_{n-1} of a run
(backtest.metrics.daily_log_returns: after every cost, the last day ends after the virtual exit), the
position held over each return day, and the calendar length T_d of the evaluation range in days.
Annualization 365 days (crypto trades every day; research/v06/procedures.ANNUALIZATION_DAYS), risk-free
rate 0 (cash earns nothing, draft section 7).

  total return (log)    exp(sum r) - 1
  CAGR                  exp(sum r * 365 / T_d) - 1                    None if T_d <= 0; short_period if T_d < 365
  volatility            sd(r) * sqrt(365), sd the sample sd (n - 1)    None if n < 2
  Sharpe (log, primary) mean(r) / sd(r) * sqrt(365)                    None if n < 2 or sd is zero
  Sharpe (simple)       the same on R = exp(r) - 1 (secondary)
  Sortino               mean(r) / DD * sqrt(365), DD = sqrt(sum(min(r, 0)^2) / n)   None if n = 0 or DD = 0
  max drawdown (P)      1 - exp(-max(peak - level)), level the running sum of r starting at 0; the same
                        definition as research/v06/procedures.max_drawdown (wealth before each day's
                        trade and after the final exit)
  Calmar                CAGR / MDD(P)                                  None if CAGR is None or MDD = 0
  exposure              sum(p) / n                                     None if n = 0
  turnover (primary)    sum(traded notional) / mean(equity), per period and * 365 / T_d
  turnover (legs)       sum(traded notional / equity before the leg) * 365 / T_d (secondary)

A metric that cannot be computed is {"value": None, "reason": ...}, never 0. Non-finite inputs raise
MetricError. All numbers are descriptive: no significance, no verdict.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

METRICS_VERSION = "bt-metrics/1"
ANNUALIZATION_DAYS = 365
RISK_FREE_RATE = 0.0
# A sample sd this small relative to the largest |r| is rounding noise of a constant series (the mean
# of identical floats is not always exact), not variation: Sharpe would be a meaningless huge number.
ZERO_SD_RELATIVE = 1e-12


class MetricError(ValueError):
    """A metric input is not usable (non-finite value, non-positive equity, inconsistent lengths)."""


def value(v: float | None, reason: str | None = None, **flags: Any) -> dict[str, Any]:
    if v is not None and not math.isfinite(v):
        raise MetricError(f"non-finite metric value {v!r}")
    out: dict[str, Any] = {"value": v, "reason": reason if v is None else None}
    out.update(flags)
    return out


def check_finite(xs: Sequence[float], name: str) -> None:
    for i, x in enumerate(xs):
        if not isinstance(x, float) or not math.isfinite(x):
            raise MetricError(f"{name}[{i}] is not a finite float: {x!r}")


def check_positive(xs: Sequence[float], name: str) -> None:
    check_finite(xs, name)
    for i, x in enumerate(xs):
        if x <= 0:
            raise MetricError(f"{name}[{i}] = {x!r} is not positive")


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def sample_sd(xs: Sequence[float]) -> float:
    n = len(xs)
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def _sd_is_zero(sd: float, xs: Sequence[float]) -> bool:
    return sd == 0.0 or sd <= ZERO_SD_RELATIVE * max(abs(x) for x in xs)


def total_return_log(r: Sequence[float]) -> dict[str, Any]:
    check_finite(r, "r")
    return value(math.expm1(sum(r)))


def cagr(r: Sequence[float], t_days: float) -> dict[str, Any]:
    check_finite(r, "r")
    if not math.isfinite(t_days) or t_days <= 0:
        return value(None, "non_positive_period", short_period=None)
    return value(math.expm1(sum(r) * ANNUALIZATION_DAYS / t_days), short_period=t_days < ANNUALIZATION_DAYS)


def volatility(r: Sequence[float]) -> dict[str, Any]:
    check_finite(r, "r")
    if len(r) < 2:
        return value(None, "fewer_than_2_returns")
    return value(sample_sd(r) * math.sqrt(ANNUALIZATION_DAYS))


def sharpe(r: Sequence[float]) -> dict[str, Any]:
    """Annualized Sharpe of the given series with risk-free rate 0."""
    check_finite(r, "r")
    if len(r) < 2:
        return value(None, "fewer_than_2_returns")
    sd = sample_sd(r)
    if _sd_is_zero(sd, r):
        return value(None, "zero_sample_sd")
    return value((mean(r) - RISK_FREE_RATE) / sd * math.sqrt(ANNUALIZATION_DAYS))


def simple_returns(r: Sequence[float]) -> list[float]:
    check_finite(r, "r")
    return [math.expm1(x) for x in r]


def sortino(r: Sequence[float]) -> dict[str, Any]:
    check_finite(r, "r")
    if not r:
        return value(None, "no_returns")
    dd = math.sqrt(sum(min(x, 0.0) ** 2 for x in r) / len(r))
    if dd == 0.0:
        return value(None, "no_downside")
    return value((mean(r) - RISK_FREE_RATE) / dd * math.sqrt(ANNUALIZATION_DAYS))


def max_drawdown_log(r: Sequence[float]) -> dict[str, Any]:
    """MDD (P): the wealth path exp(running sum of r), starting at 1."""
    check_finite(r, "r")
    peak = level = worst = 0.0
    for x in r:
        level += x
        peak = max(peak, level)
        worst = max(worst, peak - level)
    return value(-math.expm1(-worst))


def calmar(cagr_value: float | None, mdd: float) -> dict[str, Any]:
    if cagr_value is None:
        return value(None, "cagr_unavailable")
    if mdd == 0.0:
        return value(None, "zero_drawdown")
    return value(cagr_value / mdd)


def exposure(positions: Sequence[int]) -> dict[str, Any]:
    if any(p not in (0, 1) for p in positions):
        raise MetricError("positions must be 0 or 1")
    if not positions:
        return value(None, "no_returns")
    return value(sum(positions) / len(positions))


def turnover(notionals: Sequence[float], equity_before_leg: Sequence[float], equity: Sequence[float],
             t_days: float) -> dict[str, Any]:
    """Primary: sum(notional) / mean(daily equity). Secondary: sum(notional / equity before the leg)."""
    if len(notionals) != len(equity_before_leg):
        raise MetricError("one equity-before value per leg is needed")
    check_finite(notionals, "notional")
    if any(x < 0 for x in notionals):
        raise MetricError("traded notional must not be negative")
    check_positive(equity_before_leg, "equity_before_leg")
    check_positive(equity, "equity")
    if not equity:
        raise MetricError("no daily equity")
    per_period = sum(notionals) / mean(equity)
    legs = sum(q / e for q, e in zip(notionals, equity_before_leg))
    if not math.isfinite(t_days) or t_days <= 0:
        return {"period": value(per_period), "annualized": value(None, "non_positive_period"),
                "legs_period": value(legs), "legs_annualized": value(None, "non_positive_period")}
    scale = ANNUALIZATION_DAYS / t_days
    return {"period": value(per_period), "annualized": value(per_period * scale),
            "legs_period": value(legs), "legs_annualized": value(legs * scale)}


def series_metrics(r: Sequence[float], t_days: float) -> dict[str, Any]:
    """The return-based metrics shared by the strategy and every benchmark (same definitions)."""
    check_finite(r, "r")
    c = cagr(r, t_days)
    mdd = max_drawdown_log(r)
    return {
        "n_returns": len(r),
        "sum_log_return": value(sum(r)),
        "mean_log_return": value(mean(r)) if r else value(None, "no_returns"),
        "total_return": total_return_log(r),
        "cagr": c,
        "volatility": volatility(r),
        "sharpe_log": sharpe(r),
        "sharpe_simple": sharpe(simple_returns(r)),
        "sortino": sortino(r),
        "mdd": mdd,
        "calmar": calmar(c["value"], mdd["value"]),
    }
