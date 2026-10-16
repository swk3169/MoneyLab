"""BT-1 backtest core (SYNTHETIC / NOT_EVIDENCE): data integrity, look-ahead safety, SMA and R5
signals, costs, accounting invariants, reproducibility. All inputs are synthetic, nothing touches
the network, no result here says anything about profitability."""

from __future__ import annotations

import dataclasses
import math
import random
from datetime import timedelta
from decimal import Decimal, localcontext

import pytest
from backtest_helpers import DAY, HOUR, T0, daily_bars, flat_bar, hourly_bars, random_market, series

from moneylab.backtest import metrics
from moneylab.backtest.costs import FEE_SCENARIOS_BPS, CostModel
from moneylab.backtest.data import (
    AsOfView,
    BarSeries,
    DataIntegrityError,
    DuplicateBarError,
    bars_sha256,
    inspect_bars,
    provenance_for,
)
from moneylab.backtest.ledger import AccountingError, DailyRow, Ledger
from moneylab.backtest.portfolio import RunConfig, simulate
from moneylab.backtest.strategy import RULES, decide, sma
from moneylab.domain.bars import NOT_EVIDENCE, Bar, BarProvenance

D = Decimal
CASH = D(1_000_000)


def near(a: Decimal, b: Decimal, tol: str = "1e-30") -> bool:
    """Equal up to 50-digit Decimal rounding (relative to max(|a|, |b|, 1))."""
    with localcontext() as ctx:
        ctx.prec = 50
        return abs(a - b) <= D(tol) * max(abs(a), abs(b), D(1))


def run(daily, hourly, rule="sma20", first=0, last=None, fee=25, slip=5, cash=CASH):
    last = len(daily.bars) - 3 if last is None else last
    cfg = RunConfig(rule, T0 + first * DAY, T0 + last * DAY, cash, CostModel.scenario(fee, slip))
    return simulate(daily, hourly, cfg)


# --- 1. Bar immutability and validation ------------------------------------------------------------

def test_bar_is_immutable_and_validated():
    b = flat_bar("day", T0, D(100))
    with pytest.raises(dataclasses.FrozenInstanceError):
        b.close = D(1)  # type: ignore[misc]
    with pytest.raises(ValueError, match="UTC"):
        flat_bar("day", T0.replace(tzinfo=None), D(100))
    with pytest.raises(ValueError, match="aligned"):
        flat_bar("day", T0 + HOUR, D(100))
    with pytest.raises(ValueError, match="aligned"):
        flat_bar("hour", T0 + timedelta(minutes=30), D(100))
    with pytest.raises(ValueError, match="OHLC"):
        Bar("KRW-BTC", "day", T0, D(100), D(99), D(98), D(100), D(1), D(1))
    with pytest.raises(ValueError, match="Decimal"):
        Bar("KRW-BTC", "day", T0, 100.0, D(100), D(100), D(100), D(1), D(1))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="positive"):
        flat_bar("day", T0, D(0))


def test_series_is_immutable():
    s = series(daily_bars([1, 2, 3]))
    assert isinstance(s.bars, tuple)
    with pytest.raises(AttributeError):
        s.market = "X"
    with pytest.raises(TypeError):
        BarSeries(s.bars, s.provenance)
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.provenance.kind = "real"  # type: ignore[misc]


# --- 2. Ordering and duplicates --------------------------------------------------------------------

def test_series_sorts_input_and_sha_is_order_independent():
    bars = daily_bars(range(1, 11))
    shuffled = bars[:]
    random.Random(1).shuffle(shuffled)
    assert bars_sha256(bars) == bars_sha256(shuffled)
    s = series(shuffled)
    assert [b.start_utc for b in s.bars] == [b.start_utc for b in bars]


def test_duplicates_are_detected_and_refused():
    bars = daily_bars([1, 2, 3])
    rep = inspect_bars(bars + [bars[1]])
    assert rep.identical_duplicates == 1 and rep.conflicting_duplicates == ()
    other = flat_bar("day", bars[1].start_utc, D(9))
    rep = inspect_bars(bars + [other])
    assert rep.conflicting_duplicates == (bars[1].start_utc,)
    for extra in (bars[1], other):
        dup = bars + [extra]
        with pytest.raises(DuplicateBarError):
            BarSeries.build(dup, provenance_for(dup, "synthetic", "dup"))


def test_mixed_market_or_interval_is_refused():
    bars = daily_bars([1, 2]) + [flat_bar("day", T0 + 2 * DAY, D(3), market="KRW-ETH")]
    with pytest.raises(DataIntegrityError, match="more than one"):
        series(bars)


# --- 3. Missing buckets ------------------------------------------------------------------------------

def test_gaps_are_reported_not_filled():
    bars = daily_bars(range(1, 11))
    kept = bars[:3] + bars[5:9] + bars[9:]  # drop days 3, 4
    s = series(kept)
    assert s.gaps == ((T0 + 3 * DAY, 2),)
    assert len(s) == 8
    hourly = hourly_bars(2, lambda d, h: D(100))
    del hourly[5]
    assert series(hourly).gaps == ((T0 + 5 * HOUR, 1),)


# --- 4. AsOfView ---------------------------------------------------------------------------------------

def test_asof_view_hides_unconfirmed_and_future_bars():
    s = series(daily_bars(range(1, 31)))
    day10_end = T0 + 11 * DAY  # bar of day 10 ends here
    before = AsOfView(s, day10_end + timedelta(seconds=119))
    after = AsOfView(s, day10_end + timedelta(seconds=120))
    assert before.latest().start_utc == T0 + 9 * DAY
    assert after.latest().start_utc == T0 + 10 * DAY
    assert len(after) == 11
    assert after.last(1000) == s.bars[:11]
    capped = AsOfView(s, T0 + 25 * DAY, horizon=day10_end + timedelta(seconds=120))
    assert capped.latest().start_utc == T0 + 10 * DAY


def test_asof_view_has_no_path_to_later_bars():
    s = series(daily_bars(range(1, 31)))
    v = AsOfView(s, T0 + 6 * DAY)
    reachable = [getattr(v, name) for name in type(v).__slots__]
    assert not any(x is s for x in reachable)
    bars = [b for x in reachable if isinstance(x, tuple) for b in x]
    assert bars and all(b.end_utc <= v.as_of for b in bars)
    assert not hasattr(v, "__dict__")
    with pytest.raises(AttributeError):
        v.as_of = T0 + 20 * DAY
    with pytest.raises(ValueError, match="UTC"):
        AsOfView(s, (T0 + 6 * DAY).replace(tzinfo=None))


# --- 5. SMA and R5 signals ----------------------------------------------------------------------------

def test_sma_exact_and_hand_signals():
    assert sma([D("1.1"), D("2.2"), D("3.3")]) == D("2.2")
    closes = [100] * 20 + [120, 130, 90]
    s = series(daily_bars(closes))
    rule = RULES["sma20"]

    def sig(day):
        return decide(rule, AsOfView(s, T0 + (day + 1) * DAY + timedelta(minutes=2)), T0 + day * DAY)

    assert sig(18).value is None and sig(18).reason == "insufficient_history"
    assert sig(19).value == 0  # close 100 == SMA 100: cash (strict >)
    assert sig(20).value == 1 and "sma20=101" in sig(20).detail  # (19*100 + 120) / 20
    assert sig(21).value == 1  # 130 > 102.5
    assert sig(22).value == 0  # 90 < 102


def test_sma_matches_independent_float_computation():
    daily, _ = random_market(200, seed=7)
    s = series(daily)
    closes = [float(b.close) for b in daily]
    for name in ("sma20", "sma60", "sma120"):
        n = RULES[name].length
        for day in range(n - 1, 200):
            got = decide(RULES[name], AsOfView(s, T0 + (day + 1) * DAY + timedelta(minutes=2)), T0 + day * DAY)
            want = 1 if closes[day] > sum(closes[day - n + 1:day + 1]) / n else 0
            assert got.value == want, (name, day)


def test_r5_and_missing_data_reasons():
    closes = [100, 101, 102, 103, 104, 99, 110]
    s = series(daily_bars(closes))
    rule = RULES["r5"]

    def sig(ser, day):
        return decide(rule, AsOfView(ser, T0 + (day + 1) * DAY + timedelta(minutes=2)), T0 + day * DAY)

    assert sig(s, 4).reason == "insufficient_history"
    assert sig(s, 5).value == 1  # 99 < 100 (5 days earlier)
    assert sig(s, 6).value == 0  # 110 > 101
    gappy = series([b for i, b in enumerate(daily_bars(closes)) if i != 3])
    assert sig(gappy, 6).reason == "gap_in_window"
    assert sig(gappy, 3).reason == "missing_bar"


def test_unregistered_rule_is_refused():
    s = series(daily_bars([1] * 30))
    with pytest.raises(ValueError, match="unregistered"):
        decide(dataclasses.replace(RULES["sma20"], length=3), AsOfView(s, T0 + 10 * DAY), T0 + 8 * DAY)
    with pytest.raises(ValueError, match="unknown rule"):
        RunConfig("sma3", T0, T0, CASH, CostModel.scenario(0))


# --- hand-checked run used by several tests -----------------------------------------------------------

HAND_CLOSES = [100] * 20 + [120, 130, 90, 90, 90, 90, 90]
HAND_FILL = {20: 100, 21: 121, 22: 129, 23: 91, 24: 90, 25: 89, 26: 88}  # hour-0 close of day d


def hand_market():
    daily = series(daily_bars(HAND_CLOSES))
    hourly = series(hourly_bars(27, lambda d, h: D(HAND_FILL.get(d, 100))))
    return daily, hourly


def test_hand_calculated_run():
    daily, hourly = hand_market()
    res = run(daily, hourly, first=19, last=23)
    led = res.ledger
    assert [s.value for s in res.signals] == [0, 1, 1, 0, 0]
    assert [(t.side, t.ref_price, t.day) for t in led.trades] == [("buy", D(121), T0 + 20 * DAY),
                                                                  ("sell", D(91), T0 + 22 * DAY)]
    f, s = D("0.0025"), D("0.0005")
    with localcontext() as ctx:
        ctx.prec = 50
        expected = CASH * (1 - f) ** 2 * (1 - s) ** 2 * D(91) / D(121)
        assert near(led.daily[-1].equity, expected)
        assert led.trades[0].fee == CASH * f
        assert near(led.trades[1].fee, led.trades[1].quantity * D(91) * (1 - s) * f)
    assert [d.position for d in led.daily] == [0, 1, 1, 0, 0, 0]
    assert len(led.daily) == 6 and led.daily[-1].ref_time == T0 + 25 * DAY + HOUR
    summ = metrics.summary(led)
    assert summ["trade_counts"] == {"legs": 2, "buys": 1, "sells": 1, "round_trips": 1, "virtual_exits": 0,
                                    "unfilled": 0}
    assert D(summ["cost_totals"]["total"]) == sum((t.fee + t.slippage_cost for t in led.trades), D(0))
    assert res.to_dict()["evidence"] == NOT_EVIDENCE


def test_virtual_exit_at_the_end():
    daily, hourly = hand_market()
    res = run(daily, hourly, first=19, last=21)  # still long after day 21
    last = res.ledger.trades[-1]
    assert last.side == "sell" and last.virtual and last.ref_price == D(91)
    assert res.ledger.daily[-1].quantity == 0


# --- 6. Signal time vs order time --------------------------------------------------------------------

def test_signal_order_fill_are_separated_and_fill_bar_is_after_signal_bar():
    daily, hourly = random_market(160, seed=3)
    res = run(series(daily), series(hourly), rule="sma20", first=0, last=150)
    assert res.ledger.trades
    for t in res.ledger.trades:
        assert t.signal_time < t.order_time < t.fill_time
        assert t.fill_bar_start >= t.day + DAY  # the close of bar D is never the fill
        assert t.signal_time >= t.day + DAY + timedelta(seconds=120)
        assert t.fill_time - t.order_time == timedelta(minutes=1)


# --- 7, 8. Fees and slippage -----------------------------------------------------------------------------

@pytest.mark.parametrize("fee", FEE_SCENARIOS_BPS)
def test_fee_and_slippage_per_leg(fee):
    cm = CostModel.scenario(fee, 5)
    f, s = D(fee) / 10000, D(5) / 10000
    with localcontext() as ctx:
        ctx.prec = 50
        b = cm.buy(D(1_000_000), D(50_000_000))
        assert b.fee == D(1_000_000) * f
        assert b.exec_price == D(50_000_000) / (1 - s)
        assert b.slippage_cost == (D(1_000_000) - b.fee) * s
        assert abs(b.quantity * D(50_000_000) - D(1_000_000) * (1 - f) * (1 - s)) < D("1e-35")
        q = D("0.0123")
        sl = cm.sell(q, D(50_000_000))
        assert sl.exec_price == D(50_000_000) * (1 - s)
        assert sl.fee == q * sl.exec_price * f
        assert sl.slippage_cost == q * D(50_000_000) * s
        assert sl.cash_in == q * D(50_000_000) * (1 - s) * (1 - f)
    assert cm.fee_status == "FEE_UNCONFIRMED" and cm.label == "ASSUMED"


def test_zero_cost_scenario_is_frictionless_and_costs_are_not_double_counted():
    daily, hourly = hand_market()
    free = run(daily, hourly, first=19, last=23, fee=0, slip=0).ledger
    assert free.trades[0].exec_price == D(121) and free.trades[0].fee == 0
    with localcontext() as ctx:
        ctx.prec = 50
        assert near(free.daily[-1].equity, CASH * D(91) / D(121))
    fee_only = run(daily, hourly, first=19, last=23, fee=25, slip=0).ledger
    slip_only = run(daily, hourly, first=19, last=23, fee=0, slip=5).ledger
    both = run(daily, hourly, first=19, last=23, fee=25, slip=5).ledger
    with localcontext() as ctx:
        ctx.prec = 50
        g = free.daily[-1].equity
        ratio = (fee_only.daily[-1].equity / g) * (slip_only.daily[-1].equity / g)
        assert abs(both.daily[-1].equity / g - ratio) < D("1e-30")


def test_cost_model_refuses_confirmed_status_and_bad_values():
    with pytest.raises(ValueError):
        CostModel(D(5), D(5), D(0), fee_status="CONFIRMED")
    with pytest.raises(ValueError):
        CostModel(D(-1), D(5), D(0))
    with pytest.raises(ValueError):
        CostModel.scenario(10)


# --- 9, 10. Accounting -------------------------------------------------------------------------------------

@pytest.mark.parametrize("rule", sorted(RULES))
def test_accounting_invariants_hold_on_random_paths(rule):
    daily, hourly = random_market(200, seed=11)
    led = run(series(daily), series(hourly), rule=rule, first=0, last=195, fee=15, slip=5).ledger
    led.verify()
    for t in led.trades:
        assert t.cash_after >= 0 and t.qty_after >= 0
    for d in led.daily:
        with localcontext() as ctx:
            ctx.prec = 50
            assert near(d.equity, d.cash + d.quantity * d.price)
        assert d.position in (0, 1) and (d.position == 1) == (d.quantity > 0)
        assert d.cash == 0 or d.quantity == 0  # long/cash: all in or all out
    assert metrics.equity_curve(led)[-1] == led.daily[-1].equity
    total = sum(metrics.daily_log_returns(led))
    assert math.isclose(total, math.log(led.daily[-1].equity / CASH), rel_tol=0, abs_tol=1e-12)


def test_ledger_rejects_broken_rows():
    led = Ledger(CASH)
    with pytest.raises(AccountingError, match="equity"):
        led.add_daily(DailyRow(T0, D(100), "fill_bar", 1, D(0), D(1), D(100), D(99)))
    with pytest.raises(AccountingError, match="negative"):
        led.add_daily(DailyRow(T0, D(100), "fill_bar", 0, D(-1), D(0), D(-1), D(-1)))
    leg = CostModel.scenario(25, 5).buy(CASH, D(100))
    bad = dataclasses.replace(leg, fee=leg.fee / 2)  # fee recorded smaller than charged
    with pytest.raises(AccountingError, match="equity_after"):
        led.add_trade(leg=bad, day=T0, signal_time=T0 + DAY, order_time=T0 + DAY + HOUR,
                      fill_time=T0 + DAY + 2 * HOUR, fill_bar_start=T0 + DAY + HOUR, cash_before=CASH,
                      qty_before=D(0))
    with pytest.raises(AccountingError, match="ordered"):
        led.add_trade(leg=leg, day=T0, signal_time=T0 + DAY, order_time=T0 + DAY,
                      fill_time=T0 + DAY + HOUR, fill_bar_start=T0 + DAY, cash_before=CASH, qty_before=D(0))


def test_unfilled_order_does_not_change_holdings():
    daily = series(daily_bars(HAND_CLOSES))
    bars = [b for b in hourly_bars(27, lambda d, h: D(HAND_FILL.get(d, 100)))
            if b.start_utc != T0 + 21 * DAY]  # the fill bar of the day-20 buy signal is missing
    res = run(daily, series(bars), first=19, last=23)
    led = res.ledger
    assert [(u.day, u.side, u.reason) for u in led.unfilled] == [(T0 + 20 * DAY, "buy", "fill_bar_missing")]
    row = next(d for d in led.daily if d.ref_time == T0 + 21 * DAY + HOUR)
    assert row.quantity == 0 and row.position == 0 and row.cash == CASH and row.price_source == "last_close"
    assert led.trades[0].day == T0 + 21 * DAY  # bought one day later, when the signal was still long
    led.verify()


def test_cross_check_with_v06_segment_returns():
    """Independent implementation check (tests only import research code; backtest/ never does)."""
    from moneylab.research.v06 import procedures

    daily, hourly = random_market(220, seed=5)
    for rule in sorted(RULES):
        led = run(series(daily), series(hourly), rule=rule, first=0, last=215, fee=15, slip=5).ledger
        rows = led.daily
        market = [math.log(rows[i + 1].price / rows[i].price) for i in range(len(rows) - 1)]
        positions = [rows[i].position for i in range(len(rows) - 1)]
        want = procedures.segment_returns(market, positions, procedures.trade_cost_log(15, 5, 0))
        got = metrics.daily_log_returns(led)
        assert len(got) == len(want)
        assert max(abs(a - b) for a, b in zip(got, want)) < 1e-12, rule


# --- look-ahead: perturbing the future does not change the past --------------------------------------

@pytest.mark.parametrize("rule", sorted(RULES))
def test_future_bars_cannot_change_earlier_decisions(rule):
    daily, hourly = random_market(200, seed=21)
    cut = T0 + 150 * DAY
    rng = random.Random(99)

    def perturb(bars):
        out = []
        for b in bars:
            if b.start_utc >= cut:
                p = (b.close * D(str(round(rng.uniform(0.5, 1.5), 4)))).quantize(D("0.01"))
                b = dataclasses.replace(b, open=p, high=p, low=p, close=p)
            out.append(b)
        return out

    base = run(series(daily), series(hourly), rule=rule, first=0, last=195)
    alt = run(series(perturb(daily)), series(perturb(hourly)), rule=rule, first=0, last=195)
    assert base.ledger.daily != alt.ledger.daily  # the perturbation did change the future

    def early(res):
        return ([s for s in res.signals if s.decided_at < cut],
                [t for t in res.ledger.trades if t.fill_time <= cut],
                [d for d in res.ledger.daily if d.ref_time <= cut])

    assert early(base) == early(alt)


# --- 11. Reproducibility --------------------------------------------------------------------------------

def test_same_input_same_output():
    daily, hourly = random_market(150, seed=8)
    a = run(series(daily), series(hourly), rule="sma60", first=0, last=145)
    shuffled = daily[:]
    random.Random(2).shuffle(shuffled)
    b = run(series(shuffled), series(hourly), rule="sma60", first=0, last=145)
    assert a.canonical_json() == b.canonical_json()
    assert a.sha256() == b.sha256()


# --- 12. Integrity ----------------------------------------------------------------------------------------

def test_wrong_sha_is_refused():
    bars = daily_bars([1, 2, 3])
    with pytest.raises(DataIntegrityError, match="SHA-256"):
        BarSeries.build(bars, BarProvenance("synthetic", "x", "0" * 64))


def test_tampered_bar_stops_the_run():
    daily, hourly = random_market(60, seed=4)
    d, h = series(daily), series(hourly)
    object.__setattr__(d.bars[10], "close", D("12345.67"))  # bypasses frozen on purpose
    with pytest.raises(DataIntegrityError, match="no longer match"):
        run(d, h, first=0, last=50)


def test_real_or_mixed_provenance_is_refused():
    daily, hourly = random_market(40, seed=4)
    with pytest.raises(DataIntegrityError, match="BT-1 accepts only"):
        run(series(daily, kind="real"), series(hourly, kind="real"), first=0, last=30)
    with pytest.raises(DataIntegrityError, match="same provenance"):
        run(series(daily, kind="fixture"), series(hourly, kind="synthetic"), first=0, last=30)
