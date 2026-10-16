"""BT-2b-4 gross / cost analysis and the break-even fee f* (SYNTHETIC / NOT_EVIDENCE).

f* is checked against its closed form on hand-made ledgers and by re-simulating the same bars with the fee
set to f*, which must give sum r = 0 (m_s = 0) within tolerance."""

from __future__ import annotations

import json
import math

import pytest
from test_backtest_round_trips import ONE_TRIP, RISING, TWO_TRIPS, hand_ledger, model, random_ledger

from moneylab.backtest import metrics as bt_metrics
from moneylab.backtest.cost_analysis import break_even_fee, cost_analysis, gross_log_return
from moneylab.backtest.costs import CostModel
from moneylab.backtest.ledger import Ledger
from moneylab.backtest.round_trips import pair_round_trips

K5 = math.log1p(-0.0005)  # kappa 5 bp, iota 0


def analyse(led: Ledger, costs: CostModel, t_days: float = 365.0, returns=None):
    rts, open_end = pair_round_trips(led)
    r = bt_metrics.daily_log_returns(led) if returns is None else returns
    return cost_analysis(rts, open_end, r, costs, t_days, {"total": "0"})


def resim_sum(closes, fills, fee_bps: float, basis: str, *, last: int = 23) -> float:
    led = hand_ledger(closes, fills, model(repr(fee_bps), 5, 0, basis), last=last)
    return sum(bt_metrics.daily_log_returns(led))


# --- f* --------------------------------------------------------------------------------------------------

def test_break_even_fee_inclusive_closed_form_and_resimulation():
    costs = model(25, 5, 0, "inclusive")
    c = analyse(hand_ledger(ONE_TRIP, {21: 100, 23: 121}, costs), costs)
    f = c["break_even_fee"]
    want = 1 - 1 / (1.1 * 0.9995)  # A = ln 1.21 + 2 ln 0.9995, f* = 1 - exp(-A / 2)
    assert f["value"] == pytest.approx(want, rel=1e-12) and f["value_bps"] == pytest.approx(want * 1e4, rel=1e-12)
    assert f["condition"] == "m_s = 0" and f["method"] == "analytic" and f["fee_basis"] == "inclusive"
    assert f["capital_krw"] == "1000000" and f["round_trips"] == 1
    assert abs(resim_sum(ONE_TRIP, {21: 100, 23: 121}, f["value_bps"], "inclusive")) < 1e-9


def test_break_even_fee_on_top_closed_form_and_resimulation():
    costs = model(25, 5, 0, "on_top")
    c = analyse(hand_ledger(ONE_TRIP, {21: 100, 23: 121}, costs), costs)
    f = c["break_even_fee"]
    e = 1.21 * 0.9995 ** 2
    want = (e - 1) / (e + 1)  # f* = tanh(A / 2), A = ln(1.21 * 0.9995^2)
    assert f["value"] == pytest.approx(want, rel=1e-12) and f["fee_basis"] == "on_top"
    assert abs(resim_sum(ONE_TRIP, {21: 100, 23: 121}, f["value_bps"], "on_top")) < 1e-9
    inclusive = analyse(hand_ledger(ONE_TRIP, {21: 100, 23: 121}, model(25)), model(25))["break_even_fee"]["value"]
    assert f["value"] != pytest.approx(inclusive, rel=1e-6)  # the basis matters


@pytest.mark.parametrize("basis", ["inclusive", "on_top"])
def test_break_even_fee_with_two_round_trips_and_impact(basis):
    costs = model(15, 10, 2, basis)
    closes, fills = TWO_TRIPS, {21: 100, 23: 140, 25: 100, 27: 95}
    led = hand_ledger(closes, fills, costs, last=27)
    f = analyse(led, costs)["break_even_fee"]
    assert f["round_trips"] == 2 and f["value"] is not None
    led2 = hand_ledger(closes, fills, model(repr(f["value_bps"]), 10, 2, basis), last=27)
    assert abs(sum(bt_metrics.daily_log_returns(led2))) < 1e-9


def test_virtual_close_round_trip_counts_for_f_star():
    costs = model(25)
    c = analyse(hand_ledger(RISING, {21: 100, 25: 130}, costs), costs)
    assert c["break_even_fee"]["round_trips"] == 1 and c["break_even_fee"]["value"] == pytest.approx(
        1 - 1 / (math.sqrt(1.3) * 0.9995), rel=1e-12)


def test_negative_gross_and_no_trades():
    costs = model(25)
    c = analyse(hand_ledger(ONE_TRIP, {21: 121, 23: 91}, costs), costs)
    assert c["break_even_fee"]["value"] is None and c["break_even_fee"]["reason"] == "net_negative_at_zero_fee"
    assert c["break_even_fee"]["zero_fee_round_trip_log_return"] < 0
    assert c["gross_to_cost_ratio"] == {"value": None, "reason": "non_positive_gross"}
    assert c["gross_log_return"]["value"] == pytest.approx(math.log(91 / 121), rel=1e-12)
    none = analyse(hand_ledger(ONE_TRIP, {}, costs, last=19), costs)
    assert none["break_even_fee"]["reason"] == "no_round_trips"
    assert none["gross_to_cost_ratio"] == {"value": None, "reason": "zero_cost"}
    assert none["cost_log"]["value"] == 0.0 and none["annual_round_trips"]["value"] == 0.0


def test_zero_cost_run():
    costs = CostModel.scenario(0, 0)
    c = analyse(hand_ledger(ONE_TRIP, {21: 100, 23: 121}, costs), costs)
    assert c["cost_log"]["value"] == 0.0 and math.copysign(1, c["cost_log"]["value"]) == 1.0  # not -0.0
    assert c["gross_to_cost_ratio"] == {"value": None, "reason": "zero_cost"}
    assert c["net_log_return"]["value"] == pytest.approx(c["gross_log_return"]["value"], rel=1e-12)  # net = gross
    assert c["break_even_fee"]["value"] == pytest.approx(1 - 1 / 1.1, rel=1e-12)
    flat = analyse(hand_ledger(ONE_TRIP, {21: 100, 23: 100}, costs), costs)  # A = 0: break-even at zero fee
    assert flat["break_even_fee"]["value"] == 0.0 and math.copysign(1, flat["break_even_fee"]["value"]) == 1.0


def test_break_even_fee_function_edges():
    assert break_even_fee(0.1, 0, K5, "inclusive")["reason"] == "no_round_trips"
    assert break_even_fee(-0.1, 1, 0.0, "on_top")["reason"] == "net_negative_at_zero_fee"
    assert break_even_fee(0.0, 1, 0.0, "inclusive")["value"] == 0.0
    with pytest.raises(ValueError):
        break_even_fee(0.1, 1, 0.0, "other")


# --- gross / cost and annual burden ----------------------------------------------------------------------

def test_gross_cost_ratio_and_annual_burden():
    costs = model(25)
    led = hand_ledger(ONE_TRIP, {21: 100, 23: 121}, costs)
    c = analyse(led, costs, t_days=182.5)
    cost_log = -2 * (math.log1p(-0.0025) + K5)
    assert c["consistent"] and c["decomposition_error"] < 1e-12 and c["basis"] == "log"
    assert c["gross_log_return"]["value"] == pytest.approx(math.log(1.21), rel=1e-12)
    assert c["cost_log"]["value"] == pytest.approx(cost_log, rel=1e-12)
    assert c["net_log_return"]["value"] == pytest.approx(math.log(1.21) - cost_log, rel=1e-12)
    assert c["gross_to_cost_ratio"]["value"] == pytest.approx(math.log(1.21) / cost_log, rel=1e-12)
    assert c["annual_cost_log"]["value"] == pytest.approx(2 * cost_log, rel=1e-12)  # * 365 / 182.5
    assert c["annual_cost_fraction"]["value"] == pytest.approx(-math.expm1(-2 * cost_log), rel=1e-12)
    assert c["annual_round_trips"]["value"] == pytest.approx(2.0)
    zero_period = analyse(led, costs, t_days=0.0)
    assert zero_period["annual_cost_log"] == {"value": None, "reason": "non_positive_period"}
    json.dumps(c, allow_nan=False)


def test_decomposition_mismatch_and_open_position_give_no_numbers():
    costs = model(25)
    led = hand_ledger(ONE_TRIP, {21: 100, 23: 121}, costs)
    r = list(bt_metrics.daily_log_returns(led))
    r[3] += 1e-6
    bad = analyse(led, costs, returns=r)
    assert bad["consistent"] is False and bad["decomposition_error"] == pytest.approx(1e-6, rel=1e-3)
    for k in ("gross_log_return", "cost_log", "gross_to_cost_ratio", "annual_cost_log", "annual_cost_fraction"):
        assert bad[k] == {"value": None, "reason": "decomposition_mismatch"}
    assert bad["break_even_fee"]["value"] is None and bad["break_even_fee"]["reason"] == "decomposition_mismatch"
    only_buy = Ledger(led.initial_cash, led.trades[:1], [], [], led.daily)
    rts, open_end = pair_round_trips(only_buy)
    c = cost_analysis(rts, open_end, bt_metrics.daily_log_returns(led), costs, 365.0, {})
    assert c["break_even_fee"]["reason"] == "open_position_at_end" and c["decomposition_error"] is None


@pytest.mark.parametrize("scenario,sub", [("E0", "none"), ("E1", "none"), ("E2", "none"), ("E3", "none"),
                                          ("DIAG", "none"), ("E0", "prereg_6_3")])
def test_decomposition_holds_whatever_the_fill_timing(scenario, sub):
    costs = CostModel.scenario(25, 10, 1, "on_top")
    led = random_ledger(7, costs, scenario=scenario, fill_substitution=sub)
    c = analyse(led, costs)
    assert c["consistent"] and c["decomposition_error"] < 1e-10
    rts, _ = pair_round_trips(led)
    assert c["gross_log_return"]["value"] == pytest.approx(gross_log_return(rts), rel=1e-15)
