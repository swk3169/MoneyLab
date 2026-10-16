"""BT-2a fills and costs (SYNTHETIC / NOT_EVIDENCE): fee bases, market impact, E0-E3/DIAG timing,
pending / substituted / cancelled orders, accounting, and a cross-check of the scenario timing against
the v0.6 synthetic path definitions. Nothing here says anything about profitability."""

from __future__ import annotations

import dataclasses
import math
import random
from datetime import timedelta
from decimal import Decimal, localcontext

import pytest
from backtest_helpers import DAY, HOUR, T0, daily_bars, flat_bar, hourly_bars, random_market, series

from moneylab.backtest import metrics
from moneylab.backtest.costs import CAPACITY_LIMIT, CostModel, impact_bps_for_capital
from moneylab.backtest.execution import SCENARIOS, prereg_costs
from moneylab.backtest.portfolio import RunConfig, simulate
from moneylab.backtest.strategy import RULES
from moneylab.domain.bars import Bar

D = Decimal
CASH = D(1_000_000)
MIN = timedelta(minutes=1)


def near(a: Decimal, b: Decimal, tol: str = "1e-30") -> bool:
    with localcontext() as ctx:
        ctx.prec = 50
        return abs(a - b) <= D(tol) * max(abs(a), abs(b), D(1))


def run(daily, hourly, *, rule="sma20", first=0, last=None, costs=None, scenario="E0", substitution="none",
        cash=CASH):
    last = len(daily.bars) - 3 if last is None else last
    costs = costs or CostModel.scenario(25, 5)
    cfg = RunConfig(rule, T0 + first * DAY, T0 + last * DAY, cash, costs, scenario=scenario,
                    fill_substitution=substitution)
    return simulate(daily, hourly, cfg)


# --- fee bases ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("fee", [0, 5, 15, 25])
def test_fee_bases_buy_multipliers_and_difference(fee):
    f = D(fee) / 10000
    with localcontext() as ctx:
        ctx.prec = 50
        inc = CostModel.scenario(fee, 0, fee_basis="inclusive").buy(CASH, D(100))
        top = CostModel.scenario(fee, 0, fee_basis="on_top").buy(CASH, D(100))
        assert near(inc.quantity * 100, CASH * (1 - f))
        assert near(top.quantity * 100, CASH / (1 + f))
        assert near(top.fee, CASH - CASH / (1 + f)) and near(top.fee, (CASH / (1 + f)) * f)
        assert near(inc.quantity * 100 - top.quantity * 100, -CASH * f * f / (1 + f))
        assert inc.cash_out == top.cash_out == CASH
        assert inc.fee_basis == "inclusive" and top.fee_basis == "on_top"


def test_sell_is_the_same_for_both_bases_and_default_is_inclusive():
    q = D("3.5")
    a = CostModel.scenario(15, 10, fee_basis="inclusive").sell(q, D(200))
    b = CostModel.scenario(15, 10, fee_basis="on_top").sell(q, D(200))
    assert (a.cash_in, a.fee, a.slippage_cost) == (b.cash_in, b.fee, b.slippage_cost)
    assert CostModel.scenario(15).fee_basis == "inclusive"
    with pytest.raises(ValueError, match="fee_basis"):
        CostModel.scenario(15, fee_basis="maker")


def test_fee_status_stays_unconfirmed():
    cm = CostModel.scenario(5, 5)
    assert cm.fee_status == "FEE_UNCONFIRMED" and cm.label == "ASSUMED"
    assert cm.to_dict()["fee_status"] == "FEE_UNCONFIRMED"


# --- impact and per-leg cost separation ----------------------------------------------------------------

def test_impact_assumption_values_and_capacity_flag():
    assert impact_bps_for_capital(D(1_000_000)) == (D(1), True)
    i5, ok5 = impact_bps_for_capital(D(5_000_000))
    i10, ok10 = impact_bps_for_capital(D(10_000_000))
    assert ok5 and ok10 and abs(float(i5) - math.sqrt(5)) < 1e-15 and abs(float(i10) - math.sqrt(10)) < 1e-15
    assert impact_bps_for_capital(CAPACITY_LIMIT + 1)[1] is False
    with pytest.raises(ValueError):
        impact_bps_for_capital(D(0))


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_prereg_costs_use_the_scenario_kappa(scenario):
    cm, ok = prereg_costs(25, scenario, D(10_000_000))
    assert cm.slippage_bps == SCENARIOS[scenario].kappa_bps and ok
    assert abs(float(cm.impact_bps) - math.sqrt(10)) < 1e-15
    assert prereg_costs(25, scenario, D(20_000_000))[1] is False
    assert prereg_costs(25, scenario, D(10_000_000), impact=False)[0].impact_bps == 0


@pytest.mark.parametrize("basis", ["inclusive", "on_top"])
def test_each_cost_is_charged_once(basis):
    cm = CostModel(D(25), D(15), D(10), impact_bps=D(3), fee_basis=basis)
    f_b, f_s, k, i = D("0.0025"), D("0.0015"), D("0.0010"), D("0.0003")
    with localcontext() as ctx:
        ctx.prec = 50
        b = cm.buy(CASH, D(100))
        exchanged = CASH - b.fee
        assert near(b.slippage_cost, exchanged * k) and near(b.impact_cost, exchanged * i)
        assert near(b.quantity * 100, CASH - b.fee - b.slippage_cost - b.impact_cost)
        want = CASH * (1 - f_b) * (1 - k - i) if basis == "inclusive" else CASH / (1 + f_b) * (1 - k - i)
        assert near(b.quantity * 100, want)
        s = cm.sell(b.quantity, D(100))
        assert near(s.cash_in, b.quantity * 100 - s.fee - s.slippage_cost - s.impact_cost)
        assert near(s.cash_in, b.quantity * 100 * (1 - k - i) * (1 - f_s))


# --- scenario timing -------------------------------------------------------------------------------------

def ohlc_market():
    """Hand market: sma20 goes long on day 20 and back to cash on day 22. Hourly bars carry distinct
    open/high/low/close so E3 and DIAG prices are distinguishable."""
    closes = [100] * 20 + [120, 130, 90, 90, 90, 90, 90]
    daily = series(daily_bars(closes))
    hours = []
    for d in range(27):
        for h in range(24):
            c = D(1000 + 10 * d + h)
            hours.append(Bar("KRW-BTC", "hour", T0 + d * DAY + h * HOUR, c - 1, c + 5, c - 5, c, D(1), D(1)))
    return daily, series(hours)


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_scenario_times_and_prices(scenario):
    daily, hourly = ohlc_market()
    spec = SCENARIOS[scenario]
    res = run(daily, hourly, first=19, last=23, costs=CostModel.scenario(0, 0), scenario=scenario)
    buy, sell = res.ledger.trades
    assert (buy.day, sell.day) == (T0 + 20 * DAY, T0 + 22 * DAY)
    for t in (buy, sell):
        assert t.signal_time == t.day + DAY + timedelta(seconds=120)
        assert t.order_time == t.day + DAY + spec.order_offset
        assert t.fill_time == t.day + DAY + spec.ref_offset
        assert t.signal_time < t.order_time < t.fill_time
        assert t.fill_bar_start >= t.day + DAY  # never the bar the signal used
        assert t.scenario == scenario and t.fill_kind == "primary"
    d1 = 21  # the buy's fill falls on day 21 (D+1)
    if scenario == "E0":
        assert buy.ref_price == D(1000 + 10 * d1 + 0)
    elif scenario == "E1":
        assert buy.ref_price == D(1000 + 10 * d1 + 1)
    elif scenario == "E2":
        assert buy.ref_price == D(130)  # close of daily bar D+1
        assert buy.fill_time == T0 + 22 * DAY
    elif scenario == "E3":
        assert buy.ref_price == D(1000 + 10 * d1) + 5  # high of [00:00, 01:00)
        assert sell.ref_price == D(1000 + 10 * 23) - 5  # low
    else:
        assert buy.ref_price == D(1000 + 10 * d1) - 1  # open, before the signal: optimistic
    assert ("REPORT_ONLY" in res.labels) == spec.report_only
    assert [d.ref_time for d in res.ledger.daily] == [T0 + (k + 1) * DAY + spec.ref_offset for k in range(19, 25)]


def path_bars(path, days):
    """Bars whose hour-0 / hour-1 / day closes follow the synthetic components a, b, c."""
    level, hours, closes = 0.0, [], []
    for d in range(days):
        start = level
        for h in range(24):
            if h == 0:
                x = start + path.a[d]
            elif h == 1:
                x = start + path.a[d] + path.b[d]
            else:
                x = start + path.a[d] + path.b[d] + path.c[d] * (h - 1) / 22
            hours.append(flat_bar("hour", T0 + d * DAY + h * HOUR, D(repr(100 * math.exp(x)))))
        level = start + path.a[d] + path.b[d] + path.c[d]
        closes.append(hours[-1].close)
    return series(daily_bars(closes)), series(hours)


@pytest.mark.parametrize("scenario", ["E0", "E1", "E2"])
@pytest.mark.parametrize("rule", sorted(RULES))
def test_scenario_timing_matches_v06_synthetic_definitions(scenario, rule):
    """Independent check (tests only import research code): market returns and the position lag of
    E0 / E1 / E2 equal research/v06/synthetic.segment_market_positions, and the net daily returns equal
    procedures.segment_returns with the same fee, kappa and impact."""
    from moneylab.research.v06 import procedures, synthetic

    days, first, last = 300, 0, 290
    path = synthetic.make_path(synthetic.DGP(), days, seed=17)
    daily, hourly = path_bars(path, days)
    costs, _ = prereg_costs(15, scenario, D(5_000_000))
    res = run(daily, hourly, rule=rule, first=first, last=last, costs=costs, scenario=scenario)
    sig: list[int | None] = [None] * days
    for s in res.signals:
        sig[(s.day - T0).days] = s.value
    market, pos = synthetic.segment_market_positions(path, sig, scenario, first + 2, last + 3)
    rows = res.ledger.daily
    ours_market = [math.log(rows[i + 1].price / rows[i].price) for i in range(len(rows) - 1)]
    assert len(ours_market) == len(market)
    assert max(abs(x - y) for x, y in zip(ours_market, market)) < 1e-10
    assert [rows[i].position for i in range(len(rows) - 1)] == pos
    cost = procedures.trade_cost_log(15, float(costs.slippage_bps), float(costs.impact_bps))
    want = procedures.segment_returns(market, pos, cost)
    got = metrics.daily_log_returns(res.ledger)
    assert max(abs(x - y) for x, y in zip(got, want)) < 1e-10


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_future_bars_cannot_change_earlier_records(scenario):
    daily, hourly = random_market(200, seed=31)
    cut = T0 + 150 * DAY
    rng = random.Random(5)

    def perturb(bars):
        out = []
        for b in bars:
            if b.start_utc >= cut:
                p = (b.close * D(str(round(rng.uniform(0.5, 1.5), 4)))).quantize(D("0.01"))
                b = dataclasses.replace(b, open=p, high=p, low=p, close=p)
            out.append(b)
        return out

    def early(res):
        return ([s for s in res.signals if s.decided_at < cut],
                [t for t in res.ledger.trades if t.fill_time <= cut],
                [d for d in res.ledger.daily if d.ref_time <= cut])

    base = run(series(daily), series(hourly), first=0, last=195, scenario=scenario, substitution="prereg_6_3")
    alt = run(series(perturb(daily)), series(perturb(hourly)), first=0, last=195, scenario=scenario,
              substitution="prereg_6_3")
    assert early(base) == early(alt)
    assert base.ledger.daily != alt.ledger.daily


# --- pending, substituted, cancelled ---------------------------------------------------------------------

HAND_CLOSES = [100] * 20 + [120, 130, 90, 90, 90, 90, 90]


def hand_hourly(drop=(), price=lambda d, h: D(1000 + 10 * d + h)):
    return series([b for b in hourly_bars(27, price) if b.start_utc not in set(drop)])


def test_substituted_fill_uses_the_next_hourly_close_and_is_booked_after_the_reference_time():
    daily = series(daily_bars(HAND_CLOSES))
    hourly = hand_hourly(drop=[T0 + 21 * DAY, T0 + 21 * DAY + HOUR])  # fill hour and the next one missing
    res = run(daily, hourly, first=19, last=23, costs=CostModel.scenario(0, 0), substitution="prereg_6_3")
    buy = res.ledger.trades[0]
    assert buy.fill_kind == "substituted" and buy.day == T0 + 20 * DAY
    assert buy.fill_bar_start == T0 + 21 * DAY + 2 * HOUR and buy.fill_time == T0 + 21 * DAY + 3 * HOUR
    assert buy.ref_price == D(1000 + 210 + 2)
    ref_row = next(d for d in res.ledger.daily if d.ref_time == T0 + 21 * DAY + HOUR)
    assert ref_row.quantity == 0 and ref_row.cash == CASH  # holdings at R(D) are still the old ones
    assert res.ledger.unfilled == [] and res.ledger.cancelled == []
    res.ledger.verify()


def test_no_substitute_before_next_decision_means_next_reference_time():
    daily = series(daily_bars(HAND_CLOSES))
    hourly = hand_hourly(drop=[T0 + 21 * DAY + h * HOUR for h in range(24)])  # whole day 21 missing
    res = run(daily, hourly, first=19, last=23, substitution="prereg_6_3")
    assert [(u.day, u.side) for u in res.ledger.unfilled] == [(T0 + 20 * DAY, "buy")]
    buy = res.ledger.trades[0]
    assert buy.day == T0 + 21 * DAY and buy.fill_time == T0 + 22 * DAY + HOUR and buy.fill_kind == "primary"


def test_pending_order_is_cancelled_when_the_signal_reverts():
    closes = [100] * 20 + [120, 90, 90, 90, 90, 90, 90]  # long on day 20 only
    daily = series(daily_bars(closes))
    hourly = hand_hourly(drop=[T0 + 21 * DAY])  # the day-20 buy cannot fill
    res = run(daily, hourly, first=19, last=23)
    assert [(u.day, u.side) for u in res.ledger.unfilled] == [(T0 + 20 * DAY, "buy")]
    assert [(c.day, c.side, c.reason) for c in res.ledger.cancelled] == [(T0 + 20 * DAY, "buy", "signal_reverted")]
    assert res.ledger.trades == []
    assert all(d.cash == CASH and d.quantity == 0 for d in res.ledger.daily)
    res.ledger.verify()


def test_pending_order_at_the_end_is_cancelled_and_virtual_exit_falls_back():
    daily = series(daily_bars(HAND_CLOSES))
    res = run(daily, hand_hourly(drop=[T0 + 21 * DAY]), first=19, last=20)  # day-20 buy pending at the end
    assert [c.reason for c in res.ledger.cancelled] == ["end_of_run"] and res.ledger.trades == []
    res2 = run(daily, hand_hourly(drop=[T0 + 23 * DAY]), first=19, last=21)  # long; final fill bar missing
    last = res2.ledger.trades[-1]
    assert last.virtual and last.fill_kind == "virtual_fallback" and last.side == "sell"
    assert last.ref_price == D(1000 + 220 + 23)  # last hourly close before R(E+1)
    assert res2.ledger.daily[-1].quantity == 0
    res2.ledger.verify()


# --- accounting over scenarios, bases and impact -----------------------------------------------------------

@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
@pytest.mark.parametrize("basis", ["inclusive", "on_top"])
def test_accounting_invariants_with_gaps_and_substitution(scenario, basis):
    daily, hourly = random_market(220, seed=41)
    rng = random.Random(3)
    kept = [b for b in hourly if rng.random() > 0.08]  # ~8 % of hourly bars missing
    costs, _ = prereg_costs(25, scenario, D(5_000_000), fee_basis=basis)
    for rule in sorted(RULES):
        res = run(series(daily), series(kept), rule=rule, first=0, last=215, costs=costs, scenario=scenario,
                  substitution="prereg_6_3")
        led = res.ledger
        led.verify()
        for t in led.trades:
            assert t.cash_after >= 0 and t.qty_after >= 0 and t.fee_basis == basis
            assert t.signal_time < t.order_time < t.fill_time
        with localcontext() as ctx:
            ctx.prec = 50
            for d in led.daily:
                assert near(d.equity, d.cash + d.quantity * d.price)
                assert d.cash == 0 or d.quantity == 0
        totals = metrics.cost_totals(led)
        assert totals["total"] == totals["fees"] + totals["slippage"] + totals["impact"]


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_same_input_same_output_per_scenario(scenario):
    daily, hourly = random_market(150, seed=8)
    a = run(series(daily), series(hourly), rule="sma60", first=0, last=145, scenario=scenario,
            substitution="prereg_6_3")
    b = run(series(daily), series(hourly), rule="sma60", first=0, last=145, scenario=scenario,
            substitution="prereg_6_3")
    assert a.sha256() == b.sha256()


def test_run_config_refuses_unknown_scenario_and_substitution():
    with pytest.raises(ValueError, match="scenario"):
        RunConfig("sma20", T0, T0, CASH, CostModel.scenario(0), scenario="E9")
    with pytest.raises(ValueError, match="fill_substitution"):
        RunConfig("sma20", T0, T0, CASH, CostModel.scenario(0), fill_substitution="always")
