"""UTC calendar-year net performance (BT-2b-4; bt-metrics/2, docs/backtest_bt2b4_metrics.md).

Each daily return r_i covers the interval (ref_i, ref_{i+1}] and is assigned to the UTC calendar year of the
interval end ref_{i+1} (draft 8.1 rule 2: a return belongs to the day of its reference time). There is no
exception for a reference time at exactly 00:00 UTC (scenario E2): the interval ending at Y-01-01 00:00,
which lies entirely in year Y-1, is assigned to year Y. Reports note this when such reference times occur.

Row per year: n_returns, days_in_year (365 / 366), sum_log_return, net_return = exp(sum) - 1,
partial_year (n_returns < days_in_year), irregular (an interval in the year is not exactly one day).
Positive-year ratios over all years and over full years only (sum_log_return > 0 counts as positive; 0 does
not). Neither is primary, and no verdict (draft E-c threshold) is computed.
"""

from __future__ import annotations

import calendar
import math
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from moneylab.backtest.performance import MetricError, check_finite, value

ASSIGNMENT = "UTC calendar year of the interval end reference time (no exception at 00:00 UTC)"
MIDNIGHT_NOTE = ("reference times at exactly 00:00 UTC (e.g. scenario E2): the interval ending at Y-01-01 00:00 "
                 "covers the last day of Y-1 but is assigned to year Y")


def _ratio(rows: list[dict[str, Any]], empty_reason: str) -> dict[str, Any]:
    if not rows:
        return value(None, empty_reason, positive_years=0, years=0)
    pos = sum(1 for r in rows if r["sum_log_return"]["value"] > 0)
    return value(pos / len(rows), positive_years=pos, years=len(rows))


def yearly_report(ref_times: Sequence[datetime], returns: Sequence[float]) -> dict[str, Any]:
    """ref_times: the N daily reference times; returns: the N - 1 interval returns."""
    check_finite(returns, "r")
    if len(ref_times) != len(returns) + 1:
        raise MetricError("one return per interval between consecutive reference times is needed")
    for t in ref_times:
        if t.tzinfo is None or t.utcoffset() != timedelta(0):
            raise MetricError(f"reference time {t!r} is not UTC")
    acc: dict[int, dict[str, Any]] = {}
    for i, r in enumerate(returns):
        end = ref_times[i + 1]
        row = acc.setdefault(end.year, {"n": 0, "sum": 0.0, "irregular": False})
        row["n"] += 1
        row["sum"] += r
        if end - ref_times[i] != timedelta(days=1):
            row["irregular"] = True
    rows = []
    for year in sorted(acc):
        a = acc[year]
        days = 366 if calendar.isleap(year) else 365
        rows.append({"year": year, "n_returns": a["n"], "days_in_year": days,
                     "sum_log_return": value(a["sum"]), "net_return": value(math.expm1(a["sum"])),
                     "partial_year": a["n"] < days, "irregular": a["irregular"]})
    full = [r for r in rows if not r["partial_year"]]
    midnight = any(t.hour == 0 and t.minute == 0 and t.second == 0 and t.microsecond == 0 for t in ref_times)
    return {
        "assignment": ASSIGNMENT,
        "midnight_reference_times": midnight,
        "note": MIDNIGHT_NOTE if midnight else None,
        "years": rows,
        "positive_year_ratio_all_years": _ratio(rows, "no_years"),
        "positive_year_ratio_full_years": _ratio(full, "no_full_years"),
        "verdict": "not computed",
    }
