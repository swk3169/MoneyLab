"""BT-2b-3 performance metrics (bt-metrics/1): fixed answers, edge cases, research cross-checks.
Pure functions on hand-made series; SYNTHETIC / NOT_EVIDENCE, nothing is read or written."""

from __future__ import annotations

import math
import random

import pytest

from moneylab.backtest.performance import (
    ANNUALIZATION_DAYS,
    METRICS_VERSION,
    MetricError,
    cagr,
    calmar,
    check_positive,
    exposure,
    max_drawdown_log,
    series_metrics,
    sharpe,
    simple_returns,
    sortino,
    total_return_log,
    turnover,
    value,
    volatility,
)
from moneylab.research.v06 import procedures

R = [0.01, -0.02, 0.03, 0.0]
SQ = math.sqrt(365)


def close(a: float, b: float, rel: float = 1e-12) -> bool:
    return abs(a - b) <= rel * max(1.0, abs(a), abs(b))


def test_constants():
    assert METRICS_VERSION == "bt-metrics/1" and ANNUALIZATION_DAYS == 365


def test_fixed_sharpe_sortino_volatility():
    sd = math.sqrt(0.0013 / 3)  # deviations 0.005, -0.025, 0.025, -0.005 from the mean 0.005
    assert close(sharpe(R)["value"], 0.005 / sd * SQ)
    assert sharpe(R)["value"] == pytest.approx(4.588866, abs=1e-5)
    assert close(volatility(R)["value"], sd * SQ)
    assert close(sortino(R)["value"], 0.005 / 0.01 * SQ)  # DD = sqrt(0.02^2 / 4) = 0.01 (all n days)
    assert sortino(R)["value"] == pytest.approx(9.552487, abs=1e-5)


def test_fixed_cagr_and_total_return():
    r = [math.log(1.1)]
    c = cagr(r, 182.5)
    assert close(c["value"], 0.21) and c["short_period"] is True
    assert close(cagr([math.log(1.1)] * 2, 730)["value"], 0.1) and cagr(r, 730)["short_period"] is False
    assert close(total_return_log(r)["value"], 0.1)
    for bad in (0.0, -1.0, float("nan")):
        assert cagr(r, bad) == {"value": None, "reason": "non_positive_period", "short_period": None}


def test_fixed_mdd_matches_research_definition():
    equity = [100, 120, 90, 130, 104]
    r = [math.log(b / a) for a, b in zip(equity, equity[1:])]
    assert close(max_drawdown_log(r)["value"], 0.25)
    rng = random.Random(3)
    x = [rng.gauss(0.0, 0.02) for _ in range(500)]
    assert close(max_drawdown_log(x)["value"], procedures.max_drawdown(x))
    assert max_drawdown_log([0.01, 0.02])["value"] == 0.0 and max_drawdown_log([])["value"] == 0.0


def test_sharpe_matches_research_when_sd_positive():
    rng = random.Random(11)
    x = [rng.gauss(0.0005, 0.03) for _ in range(400)]
    assert close(sharpe(x)["value"], procedures.annual_sharpe(x))


def test_simple_sharpe_is_secondary_on_simple_returns():
    assert simple_returns([0.0, math.log(2)]) == [0.0, pytest.approx(1.0, abs=1e-15)]
    assert close(series_metrics(R, 4)["sharpe_simple"]["value"], sharpe([math.expm1(v) for v in R])["value"])
    assert series_metrics(R, 4)["sharpe_simple"]["value"] != series_metrics(R, 4)["sharpe_log"]["value"]


@pytest.mark.parametrize("series", [[0.001] * 10, [0.1] * 3, [0.0] * 5])
def test_zero_sd_gives_none_with_reason(series):
    assert sharpe(series) == {"value": None, "reason": "zero_sample_sd"}


def test_short_series():
    assert sharpe([]) == {"value": None, "reason": "fewer_than_2_returns"}
    assert sharpe([0.01]) == {"value": None, "reason": "fewer_than_2_returns"}
    assert volatility([0.01]) == {"value": None, "reason": "fewer_than_2_returns"}
    assert sortino([]) == {"value": None, "reason": "no_returns"}
    assert sharpe([0.01, 0.02])["value"] is not None
    m = series_metrics([], 0.0)
    assert m["n_returns"] == 0 and m["mean_log_return"]["value"] is None and m["total_return"]["value"] == 0.0


def test_no_downside_and_calmar():
    assert sortino([0.01, 0.0, 0.02]) == {"value": None, "reason": "no_downside"}
    assert calmar(None, 0.1) == {"value": None, "reason": "cagr_unavailable"}
    assert calmar(0.2, 0.0) == {"value": None, "reason": "zero_drawdown"}
    assert calmar(0.2, 0.1)["value"] == pytest.approx(2.0)


def test_non_finite_and_non_positive_inputs_raise():
    for bad in ([0.01, float("nan")], [float("inf")], [1]):
        with pytest.raises(MetricError):
            sharpe(bad)
    with pytest.raises(MetricError):
        check_positive([1.0, 0.0], "equity")
    with pytest.raises(MetricError):
        check_positive([1.0, -2.0], "equity")
    with pytest.raises(MetricError):
        value(float("inf"))


def test_exposure():
    assert exposure([0, 1, 1, 0])["value"] == 0.5
    assert exposure([]) == {"value": None, "reason": "no_returns"}
    with pytest.raises(MetricError):
        exposure([0, 2])


def test_turnover_primary_and_legs():
    t = turnover([100.0, 110.0], [100.0, 110.0], [100.0, 100.0, 110.0, 110.0], 365.0)
    assert t["period"]["value"] == pytest.approx(2.0) and t["annualized"]["value"] == pytest.approx(2.0)
    assert t["legs_period"]["value"] == pytest.approx(2.0)
    half = turnover([100.0, 110.0], [100.0, 110.0], [100.0, 100.0, 110.0, 110.0], 182.5)
    assert half["annualized"]["value"] == pytest.approx(4.0) and half["legs_annualized"]["value"] == pytest.approx(4.0)
    none = turnover([], [], [100.0, 100.0], 30.0)
    assert none["period"]["value"] == 0.0 and none["legs_annualized"]["value"] == 0.0
    assert turnover([1.0], [1.0], [1.0], 0.0)["annualized"] == {"value": None, "reason": "non_positive_period"}
    with pytest.raises(MetricError):
        turnover([1.0], [], [1.0], 1.0)
    with pytest.raises(MetricError):
        turnover([1.0], [1.0], [0.0], 1.0)


def test_series_metrics_is_json_safe():
    import json
    m = series_metrics(R, 4.0)
    json.dumps(m, allow_nan=False)
    assert close(m["mdd"]["value"], -math.expm1(-0.02))  # peak level 0.01, trough -0.01
    assert m["calmar"]["value"] == pytest.approx(m["cagr"]["value"] / m["mdd"]["value"])
