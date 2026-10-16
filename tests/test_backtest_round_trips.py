"""BT-2b-4 round trips: pairing, KRW net P&L, Profit Factor, win rate, exact invariant (SYNTHETIC / NOT_EVIDENCE).

Hand-made ledgers: sma20 on flat bars, 20 days at 100 then the closes below. The E0 fill and valuation price of
day d is the hourly price of day d (fills.get(d, 100)), so a signal on day D trades at fills[D + 1].
The helpers here are also used by test_backtest_cost_analysis.py."""

from __future__ import annotations

import dataclasses
from decimal import Decimal, localcontext

import pytest
from backtest_helpers import DAY, T0, daily_bars, hourly_bars, random_market, series

from moneylab.backtest.costs import CostModel
from moneylab.backtest.ledger import Ledger
from moneylab.backtest.portfolio import RunConfig, simulate
from moneylab.backtest.round_trips import RoundTripError, pair_round_trips, round_trip_report, view_stats

CASH = Decimal(1_000_000)
ONE_TRIP = [100] * 20 + [120, 130, 90, 90, 90, 90, 90]  # long days 20-21, cash from day 22: buy d21, sell d23
TWO_TRIPS = [100] * 20 + [120, 130, 90, 90, 120, 130, 90, 90]  # buy d21, sell d23, buy d25, sell d27
RISING = [100] * 20 + [120, 130, 140, 150, 160, 170, 180]  # long to the end: closed by the virtual exit


def hand_ledger(closes, fills, costs: CostModel, *, last: int = 23, scenario: str = "E0") -> Ledger:
    day = daily_bars(closes)
    hour = hourly_bars(len(closes) + 3, lambda d, h: Decimal(fills.get(d, 100)))
    cfg = RunConfig("sma20", T0 + 19 * DAY, T0 + last * DAY, CASH, costs, scenario=scenario)
    led = simulate(series(day), series(hour), cfg).ledger
    assert led is not None
    return led


def model(fee_bps, slippage_bps=5, impact_bps=0, fee_basis: str = "inclusive") -> CostModel:
    """Any fee in bp (not only the configured scenarios), e.g. for a re-simulation at f*."""
    f = Decimal(str(fee_bps))
    return CostModel(f, f, Decimal(str(slippage_bps)), impact_bps=Decimal(str(impact_bps)), fee_basis=fee_basis)


def random_ledger(seed: int, costs: CostModel, **kw) -> Ledger:
    day, hour = random_market(200, seed)
    led = simulate(series(day), series(hour), RunConfig("sma20", T0 + 25 * DAY, T0 + 190 * DAY, CASH, costs, **kw))
    assert led.ledger is not None
    return led.ledger


def exact_sum(xs) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 100
        return sum(xs, Decimal(0))


def exact_neg(x: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 100
        return -x


def exact_change(led: Ledger) -> Decimal:
    """final equity - initial cash without rounding to the default 28-digit context."""
    with localcontext() as ctx:
        ctx.prec = 100
        return led.daily[-1].equity - led.initial_cash


# --- pairing ---------------------------------------------------------------------------------------------

def test_one_completed_round_trip():
    led = hand_ledger(ONE_TRIP, {21: 100, 23: 121}, CostModel.scenario(25, 5))
    rts, open_end = pair_round_trips(led)
    assert not open_end and len(rts) == 1
    rt = rts[0]
    assert (rt.entry_leg, rt.exit_leg, rt.entry_price, rt.exit_price) == (0, 1, Decimal(100), Decimal(121))
    assert rt.virtual_close is False and rt.exit_fill_kind == "primary" and rt.outcome == "win"
    assert rt.entry_cash == CASH and rt.net_pnl == led.trades[1].cash_after - CASH
    m = Decimal("0.9975") * Decimal("0.9995")  # fee 25 bp and kappa 5 bp, inclusive, both legs
    with localcontext() as ctx:
        ctx.prec = 50
        assert abs(rt.net_pnl - (CASH * m * m * Decimal(121) / Decimal(100) - CASH)) < Decimal("1e-30")


def test_virtual_close_is_identified():
    led = hand_ledger(RISING, {21: 100, 25: 130}, CostModel.scenario(25, 5))
    rts, open_end = pair_round_trips(led)
    assert not open_end and len(rts) == 1 and rts[0].virtual_close and rts[0].exit_price == Decimal(130)
    rep = round_trip_report(led)
    assert rep["virtual_close_count"] == 1 and rep["rows"][0]["virtual_close"] is True
    assert rep["views"]["completed_only"]["count"] == 0
    assert rep["views"]["completed_only"]["win_rate"] == {"value": None, "reason": "no_round_trips"}
    assert rep["views"]["including_virtual_close"]["count"] == 1


def test_win_loss_profit_factor_and_win_rate():
    led = hand_ledger(TWO_TRIPS, {21: 100, 23: 121, 25: 100, 27: 90}, CostModel.scenario(25, 5), last=27)
    rts, _ = pair_round_trips(led)
    assert [rt.outcome for rt in rts] == ["win", "loss"]
    v = round_trip_report(led)["views"]["including_virtual_close"]
    assert (v["count"], v["wins"], v["losses"], v["zeros"]) == (2, 1, 1, 0)
    assert v["win_rate"]["value"] == 0.5
    with localcontext() as ctx:
        ctx.prec = 100
        want = rts[0].net_pnl / -rts[1].net_pnl
    assert v["profit_factor"]["value"] == float(want)
    assert Decimal(v["gross_profit_krw"]) == rts[0].net_pnl and Decimal(v["gross_loss_krw"]) == exact_neg(rts[1].net_pnl)


def test_no_losses_and_no_round_trips_are_null_not_infinity():
    led = hand_ledger(ONE_TRIP, {21: 100, 23: 121}, CostModel.scenario(25, 5))
    v = round_trip_report(led)["views"]["completed_only"]
    assert v["profit_factor"] == {"value": None, "reason": "no_losing_round_trips"} and v["win_rate"]["value"] == 1.0
    empty = view_stats([])
    assert empty["profit_factor"] == {"value": None, "reason": "no_round_trips"}
    assert empty["win_rate"] == {"value": None, "reason": "no_round_trips"} and empty["count"] == 0


def test_exactly_zero_round_trip():
    """Zero costs and an unchanged price: quantity 1,000,000 / 100 is exact, so P&L is exactly 0."""
    led = hand_ledger(ONE_TRIP, {21: 100, 23: 100}, CostModel.scenario(0, 0))
    rts, _ = pair_round_trips(led)
    assert rts[0].net_pnl == 0 and rts[0].outcome == "zero"
    v = round_trip_report(led)["views"]["including_virtual_close"]
    assert (v["wins"], v["losses"], v["zeros"]) == (0, 0, 1)
    assert v["win_rate"]["value"] == 0.0  # zeros are in the denominator
    assert v["profit_factor"] == {"value": None, "reason": "no_profit_and_no_loss"}


def test_loss_only_profit_factor_is_zero():
    led = hand_ledger(ONE_TRIP, {21: 121, 23: 91}, CostModel.scenario(25, 5))
    v = round_trip_report(led)["views"]["including_virtual_close"]
    assert v["profit_factor"]["value"] == 0.0 and v["win_rate"]["value"] == 0.0 and v["losses"] == 1


def test_no_trades():
    led = hand_ledger(ONE_TRIP, {}, CostModel.scenario(25, 5), last=19)  # no long signal in the range
    rep = round_trip_report(led)
    assert rep["count"] == 0 and rep["rows"] == [] and led.trades == []
    assert rep["invariant"]["holds"] is True and rep["invariant"]["final_minus_initial"] == "0"


# --- invariant -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("basis", ["inclusive", "on_top"])
def test_invariant_is_exact(seed, basis):
    led = random_ledger(seed, CostModel.scenario(25, 5, 1, basis))
    rts, open_end = pair_round_trips(led)
    assert not open_end and len(rts) >= 2
    final_minus_initial = exact_change(led)
    assert exact_sum(rt.net_pnl for rt in rts) == final_minus_initial  # exact Decimal equality
    inv = round_trip_report(led)["invariant"]
    assert inv["holds"] is True and Decimal(inv["sum_net_pnl_including_virtual"]) == final_minus_initial
    virtual = exact_sum(rt.net_pnl for rt in rts if rt.virtual_close)
    completed = exact_sum(rt.net_pnl for rt in rts if not rt.virtual_close)
    assert completed == exact_sum([final_minus_initial, exact_neg(virtual)])
    assert Decimal(inv["sum_net_pnl_completed_only"]) == completed


@pytest.mark.parametrize("scenario,sub", [("E1", "none"), ("E2", "none"), ("E3", "none"), ("DIAG", "none"),
                                          ("E0", "prereg_6_3")])
def test_invariant_holds_for_every_scenario(scenario, sub):
    led = random_ledger(4, CostModel.scenario(15, 10), scenario=scenario, fill_substitution=sub)
    assert round_trip_report(led)["invariant"]["holds"] is True


def test_open_position_and_broken_structure():
    led = hand_ledger(ONE_TRIP, {21: 100, 23: 121}, CostModel.scenario(25, 5))
    only_buy = Ledger(led.initial_cash, led.trades[:1], [], [], led.daily)
    rts, open_end = pair_round_trips(only_buy)
    assert rts == [] and open_end
    assert round_trip_report(only_buy)["invariant"] == {
        "holds": None, "reason": "open_position_at_end",
        "final_minus_initial": str(exact_change(led))}
    with pytest.raises(RoundTripError, match="expected a buy"):
        pair_round_trips(Ledger(led.initial_cash, led.trades[1:], [], [], led.daily))
    two_buys = [led.trades[0], dataclasses.replace(led.trades[0], leg=1)]
    with pytest.raises(RoundTripError, match="expected a sell"):
        pair_round_trips(Ledger(led.initial_cash, two_buys, [], [], led.daily))
