"""BT-2b-4 UTC calendar-year net performance (SYNTHETIC / NOT_EVIDENCE).

Reference times are built by hand; the ledger case crosses a year boundary on synthetic bars."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from backtest_helpers import DAY, daily_bars, hourly_bars, series

from moneylab.backtest import metrics as bt_metrics
from moneylab.backtest.costs import CostModel
from moneylab.backtest.performance import MetricError
from moneylab.backtest.portfolio import RunConfig, simulate
from moneylab.backtest.yearly import yearly_report


def refs(start: datetime, n: int, step: timedelta = DAY) -> list[datetime]:
    return [start + i * step for i in range(n)]


def test_interval_end_year_assignment_across_new_year():
    t = refs(datetime(2019, 12, 30, 1, tzinfo=UTC), 4)  # ends 12-31, 01-01, 01-02 (all 01:00 UTC)
    y = yearly_report(t, [0.01, 0.02, -0.005])
    rows = {r["year"]: r for r in y["years"]}
    assert rows[2019]["n_returns"] == 1 and rows[2019]["sum_log_return"]["value"] == pytest.approx(0.01)
    assert rows[2020]["n_returns"] == 2 and rows[2020]["sum_log_return"]["value"] == pytest.approx(0.015)
    assert rows[2020]["net_return"]["value"] == pytest.approx(math.expm1(0.015))
    assert rows[2019]["partial_year"] and rows[2020]["partial_year"] and rows[2020]["days_in_year"] == 366
    assert y["midnight_reference_times"] is False and y["note"] is None and y["verdict"] == "not computed"


def test_full_and_partial_years_and_leap_year():
    t = refs(datetime(2018, 12, 31, 1, tzinfo=UTC), 366 + 366 + 3)  # all of 2019 (365) and 2020 (366), part of 2021
    r = [0.001] * 365 + [-0.001] * 366 + [0.002] * 3
    y = yearly_report(t, r)
    rows = {row["year"]: row for row in y["years"]}
    assert (rows[2019]["n_returns"], rows[2019]["days_in_year"], rows[2019]["partial_year"]) == (365, 365, False)
    assert (rows[2020]["n_returns"], rows[2020]["days_in_year"], rows[2020]["partial_year"]) == (366, 366, False)
    assert rows[2021]["partial_year"] and rows[2021]["n_returns"] == 3  # ends 01-01, 01-02, 01-03
    assert y["positive_year_ratio_all_years"]["value"] == pytest.approx(2 / 3)
    assert y["positive_year_ratio_all_years"]["positive_years"] == 2
    assert y["positive_year_ratio_full_years"]["value"] == 0.5 and y["positive_year_ratio_full_years"]["years"] == 2


def test_e2_midnight_boundary_has_no_exception():
    """E2 values at 00:00 UTC: the interval (2019-12-31 00:00, 2020-01-01 00:00] lies in 2019 but goes to 2020."""
    t = [datetime(2019, 12, 30, tzinfo=UTC), datetime(2019, 12, 31, tzinfo=UTC), datetime(2020, 1, 1, tzinfo=UTC)]
    y = yearly_report(t, [0.01, 0.03])
    rows = {r["year"]: r for r in y["years"]}
    assert rows[2019]["sum_log_return"]["value"] == pytest.approx(0.01)
    assert rows[2020]["sum_log_return"]["value"] == pytest.approx(0.03)  # assigned to the end year
    assert y["midnight_reference_times"] is True and "00:00 UTC" in y["note"]


def test_zero_year_is_not_positive_and_no_full_years():
    t = refs(datetime(2020, 3, 1, 1, tzinfo=UTC), 4)
    y = yearly_report(t, [0.0, 0.0, 0.0])
    assert y["positive_year_ratio_all_years"]["value"] == 0.0
    assert y["positive_year_ratio_full_years"] == {"value": None, "reason": "no_full_years", "positive_years": 0,
                                                   "years": 0}
    empty = yearly_report([datetime(2020, 1, 1, 1, tzinfo=UTC)], [])
    assert empty["years"] == [] and empty["positive_year_ratio_all_years"]["reason"] == "no_years"


def test_irregular_interval_is_flagged():
    t = [datetime(2020, 5, 1, 1, tzinfo=UTC), datetime(2020, 5, 2, 1, tzinfo=UTC), datetime(2020, 5, 4, 1, tzinfo=UTC)]
    assert yearly_report(t, [0.01, 0.01])["years"][0]["irregular"] is True


def test_input_checks():
    with pytest.raises(MetricError):
        yearly_report(refs(datetime(2020, 1, 1, tzinfo=UTC), 3), [0.0])
    with pytest.raises(MetricError):
        yearly_report([datetime(2020, 1, 1), datetime(2020, 1, 2)], [0.0])
    kst = timezone(timedelta(hours=9))
    with pytest.raises(MetricError):
        yearly_report([datetime(2020, 1, 1, tzinfo=kst), datetime(2020, 1, 2, tzinfo=kst)], [0.0])
    with pytest.raises(MetricError):
        yearly_report(refs(datetime(2020, 1, 1, tzinfo=UTC), 2), [float("nan")])


def test_ledger_across_a_year_boundary_sums_back():
    start = datetime(2019, 10, 1, tzinfo=UTC)
    closes = [Decimal(100 + (i % 17) - (i % 5)) for i in range(140)]
    day = daily_bars(closes, start)
    hour = hourly_bars(140, lambda d, h: closes[d], start)
    led = simulate(series(day), series(hour), RunConfig("sma20", start + 25 * DAY, start + 130 * DAY,
                                                        Decimal(1_000_000), CostModel.scenario(25, 5))).ledger
    r = bt_metrics.daily_log_returns(led)
    y = yearly_report([d.ref_time for d in led.daily], r)
    assert [row["year"] for row in y["years"]] == [2019, 2020]
    assert sum(row["n_returns"] for row in y["years"]) == len(r)
    assert sum(row["sum_log_return"]["value"] for row in y["years"]) == pytest.approx(sum(r), abs=1e-12)
    assert all(row["partial_year"] for row in y["years"])
    json.dumps(y, allow_nan=False)
