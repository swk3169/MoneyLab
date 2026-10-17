"""Forward risk-limit model of the v0.6 Monte Carlo (MC-V06, docs/tasks/MC-V06/WORK_ORDER.md). Pure, stdlib only.

An independent research-layer implementation of the BT-3e risk semantics (docs/backtest_design.md, BT-3e): it
imports nothing from moneylab.backtest, and backtest imports nothing from here. Cross-package equivalence is
checked in tests only (tests/test_v06_risk_model.py, through the public ForwardVault).

Normative semantic scope (BT3E_SEMANTIC_EQUIVALENCE), applied to GIVEN daily log returns:
  * MAX_DRAWDOWN_LOG: 1 - exp(-worst) of the running sum of log returns (wealth starts at 1), computed as
    -expm1(-worst), the same formula as the engine metric
  * calendar-month grouping: daily observation t carries the UTC calendar date start + t days
  * CUMULATIVE_FROM_L: the value of month m is taken over every observation from L to the end of month m
  * MONTH_ONLY: the value of month m is taken over the observations of month m only (from max(month start, L))
  * gt / ge: VIOLATION if value > (or >=) threshold_ratio * reference
Not modelled (return-generation semantics, reported as a limitation): engine equity, the hourly-bar engine path,
scenario reference times, the ENGINE_WINDOW_BT3B shifts F = P - 2 days and last_day = N - 3 days. BT4-Q18 is not
resolved here. Supporting a value does not select it for the study (BT-4 does). SYNTHETIC / NOT_EVIDENCE.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

MAX_DRAWDOWN_LOG = "MAX_DRAWDOWN_LOG"
CUMULATIVE_FROM_L = "CUMULATIVE_FROM_L"
MONTH_ONLY = "MONTH_ONLY"
GT, GE = "gt", "ge"
METRIC_IDS = (MAX_DRAWDOWN_LOG,)
ACCUMULATION_MODES = (CUMULATIVE_FROM_L, MONTH_ONLY)
COMPARISONS = (GT, GE)
PASS, VIOLATION = "PASS", "VIOLATION"


@dataclass(frozen=True)
class RiskPolicy:
    """Every value explicit (no defaults), like the BT-3e policy."""
    metric_id: str
    threshold_ratio: float
    comparison_operator: str
    accumulation_mode: str

    def __post_init__(self) -> None:
        if self.metric_id not in METRIC_IDS:
            raise ValueError(f"unsupported metric_id {self.metric_id!r}")
        if self.comparison_operator not in COMPARISONS:
            raise ValueError(f"unsupported comparison_operator {self.comparison_operator!r}")
        if self.accumulation_mode not in ACCUMULATION_MODES:
            raise ValueError(f"unsupported accumulation_mode {self.accumulation_mode!r}")
        r = self.threshold_ratio
        if isinstance(r, bool) or not isinstance(r, (int, float)) or not math.isfinite(r) or r <= 0:
            raise ValueError("threshold_ratio must be a finite number > 0")

    @property
    def key(self) -> str:
        return f"{self.metric_id}|{self.threshold_ratio!r}|{self.comparison_operator}|{self.accumulation_mode}"


# --- metric ---------------------------------------------------------------------------------------------------------

def _check_finite(returns: Sequence[float]) -> None:
    if any(not math.isfinite(x) for x in returns):
        raise ValueError("returns must be finite")


def max_drawdown_log(returns: Sequence[float]) -> float:
    """MAX_DRAWDOWN_LOG: largest peak-to-trough loss of the wealth path exp(running sum), starting at 1 (0 if empty)."""
    _check_finite(returns)
    peak = level = worst = 0.0
    for x in returns:
        level += x
        peak = max(peak, level)
        worst = max(worst, peak - level)
    return -math.expm1(-worst)


def running_max_drawdown_log(returns: Sequence[float]) -> list[float]:
    """out[k] = max_drawdown_log(returns[:k + 1]) (the same operations, so the values are identical)."""
    _check_finite(returns)
    peak = level = worst = 0.0
    out = []
    for x in returns:
        level += x
        peak = max(peak, level)
        worst = max(worst, peak - level)
        out.append(-math.expm1(-worst))
    return out


def decide(value: float, reference: float, policy: RiskPolicy) -> str:
    """VIOLATION if value > (gt) or >= (ge) threshold_ratio * reference, else PASS."""
    limit = float(policy.threshold_ratio) * reference
    violated = value > limit if policy.comparison_operator == GT else value >= limit
    return VIOLATION if violated else PASS


# --- calendar -------------------------------------------------------------------------------------------------------

def parse_date(text: str) -> date:
    d = date.fromisoformat(text)
    if d.isoformat() != text:
        raise ValueError(f"{text!r} is not a canonical YYYY-MM-DD date")
    return d


def month_start(d: date) -> date:
    return d.replace(day=1)


def next_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def month_name(d: date) -> str:
    return f"{d.year:04d}{d.month:02d}"


def add_months(d: date, months: int) -> date:
    """Same day of month `months` later (clamped to the month's last day)."""
    if months < 0:
        raise ValueError("months must be >= 0")
    y, m = divmod(d.month - 1 + months, 12)
    first = date(d.year + y, m + 1, 1)
    last = (next_month(first) - timedelta(days=1)).day
    return first.replace(day=min(d.day, last))


def forward_days(start: date, months: int) -> int:
    """Number of daily observations in the first `months` calendar months from `start`."""
    return (add_months(start, months) - start).days


def calendar_months(start: date, days: int) -> list[tuple[str, int, int]]:
    """(YYYYMM, lo, hi): observation indices [lo, hi) of each calendar month, observation t on date start + t.
    The first month begins at the first observation (start may be mid-month); the last may be truncated."""
    if days < 0:
        raise ValueError("days must be >= 0")
    out = []
    lo, m = 0, month_start(start)
    while lo < days:
        hi = min(days, (next_month(m) - start).days)
        out.append((month_name(m), lo, hi))
        lo, m = hi, next_month(m)
    return out


# --- monthly checks -------------------------------------------------------------------------------------------------

def monthly_values(returns: Sequence[float], start: date, accumulation_mode: str) -> list[tuple[str, float]]:
    """(YYYYMM, MAX_DRAWDOWN_LOG) of every calendar month covered by the observations."""
    if accumulation_mode not in ACCUMULATION_MODES:
        raise ValueError(f"unsupported accumulation_mode {accumulation_mode!r}")
    groups = calendar_months(start, len(returns))
    if accumulation_mode == CUMULATIVE_FROM_L:
        running = running_max_drawdown_log(returns)
        return [(name, running[hi - 1]) for name, _lo, hi in groups]
    return [(name, max_drawdown_log(returns[lo:hi])) for name, lo, hi in groups]


def monthly_decisions(returns: Sequence[float], start: date, reference: float, policy: RiskPolicy) -> dict[str, str]:
    """YYYYMM -> PASS | VIOLATION for every calendar month covered by the observations."""
    return {name: decide(v, reference, policy) for name, v in monthly_values(returns, start, policy.accumulation_mode)}


def first_violation(returns: Sequence[float], start: date, reference: float, policy: RiskPolicy) -> int | None:
    """Index (0 = month of start) of the first violating calendar month, or None."""
    for i, (_name, v) in enumerate(monthly_values(returns, start, policy.accumulation_mode)):
        if decide(v, reference, policy) == VIOLATION:
            return i
    return None
