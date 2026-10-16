"""BT-3b evaluation boundary: G = [first_day + 2 days, last_day + 3 days), valuation end R(last_day + 1) <= G_end,
engine guard, end-coverage refusal and the independent boundary verifier (SYNTHETIC / NOT_EVIDENCE).

All paths are written by hand; no random numbers. "Outside the boundary" always means bar.end_utc > G_end.
Runs are compared by their signals and ledger rows, not by result_sha256 (the provenance hash covers the
whole input series, so any changed bar changes it)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from backtest_helpers import DAY, HOUR, T0, daily_bars, flat_bar, hourly_bars, series
from test_bar_export import fixture_pull

from moneylab.backtest import portfolio
from moneylab.backtest.code_state import classify_worktree
from moneylab.backtest.costs import CostModel
from moneylab.backtest.data import BarSeries, DataIntegrityError, LookAheadError
from moneylab.backtest.execution import SCENARIOS, FillResult
from moneylab.backtest.portfolio import RunConfig, evaluation_boundary, require_within_boundary, simulate
from moneylab.backtest.run import INITIAL_CASH_KRW, VERIFY_CHECKS, boundary_problems, run_backtest, verify_run
from moneylab.backtest.settings import DEFAULT_SETTINGS_FILE, cost_model, load_cost_settings
from moneylab.providers.upbit.bar_export import export_bars

D = Decimal
CASH = D(1_000_000)
HAND = [100] * 20 + [120, 130, 90, 90, 90, 90, 90, 90, 90, 90]  # sma20: long day 20-21, cash from day 22
RISING = [100] * 20 + [120 + 10 * i for i in range(10)]  # sma20 long from day 20 to the end
CODE = classify_worktree("b" * 40, [])
NOW = datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)


def hour_price(d: int, h: int) -> Decimal:
    return D(1000 + 10 * d + h)


def market(closes=HAND, days: int = 30, drop=()):
    hours = [b for b in hourly_bars(days, hour_price) if b.start_utc not in set(drop)]
    return series(daily_bars(closes)), series(hours)


def cfg(first: int = 19, last: int = 23, scenario: str = "E0", substitution: str = "none", rule: str = "sma20"):
    return RunConfig(rule, T0 + first * DAY, T0 + last * DAY, CASH, CostModel.scenario(25, 5), scenario=scenario,
                     fill_substitution=substitution)


def state(res):
    led = res.ledger
    return res.signals, led.trades, led.daily, led.unfilled, led.cancelled


def bump(bars, pick):
    """Double every price of the picked bars."""
    out = []
    for b in bars:
        if pick(b):
            b = dataclasses.replace(b, open=b.open * 2, high=b.high * 2, low=b.low * 2, close=b.close * 2)
        out.append(b)
    return out


def rows(res):
    body = res.to_dict()
    return res.config.to_dict(), body["signals"], body["daily"], body["trades"]


# --- T1: boundary equations ---------------------------------------------------------------------------------

@pytest.mark.parametrize("scenario,first_ref,r_e,val_end", [
    ("E0", T0 + DAY + HOUR, T0 + 11 * DAY + HOUR, T0 + 12 * DAY + HOUR),
    ("E1", T0 + DAY + 2 * HOUR, T0 + 11 * DAY + 2 * HOUR, T0 + 12 * DAY + 2 * HOUR),
    ("E2", T0 + 2 * DAY, T0 + 12 * DAY, T0 + 13 * DAY),
    ("E3", T0 + DAY + HOUR, T0 + 11 * DAY + HOUR, T0 + 12 * DAY + HOUR),
    ("DIAG", T0 + DAY + HOUR, T0 + 11 * DAY + HOUR, T0 + 12 * DAY + HOUR),
])
def test_boundary_equations(scenario, first_ref, r_e, val_end):
    b = evaluation_boundary(cfg(0, 10, scenario))
    assert (b.first_day, b.last_day, b.scenario) == (T0, T0 + 10 * DAY, scenario)
    assert b.g_start == T0 + 2 * DAY and b.g_end == T0 + 13 * DAY
    assert b.first_ref == first_ref and SCENARIOS[scenario].ref_time(T0 + 10 * DAY) == r_e
    assert b.valuation_end == val_end and b.valuation_end <= b.g_end
    assert (b.valuation_end == b.g_end) == (scenario == "E2")


# --- T5, T6: the guard ----------------------------------------------------------------------------------------

def test_guard_allows_g_end_and_refuses_later():
    g_end = T0 + 13 * DAY
    require_within_boundary(g_end, g_end, "bar")
    with pytest.raises(LookAheadError, match="after the evaluation end"):
        require_within_boundary(g_end + timedelta(microseconds=1), g_end, "bar")


def test_fill_after_g_end_is_refused(monkeypatch):
    daily, hourly = market()
    c = cfg()
    late = evaluation_boundary(c).g_end + HOUR
    monkeypatch.setattr(portfolio, "find_fill", lambda *a, **k: FillResult(D(100), late, late - HOUR, "primary"))
    with pytest.raises(LookAheadError, match="fill bar"):
        simulate(daily, hourly, c)


def test_valuation_bar_after_g_end_is_refused(monkeypatch):
    daily, hourly = market()
    c = cfg()
    late = flat_bar("hour", evaluation_boundary(c).g_end, D(100))  # ends one hour after G_end
    monkeypatch.setattr(BarSeries, "last_ended_by", lambda self, t: late)
    with pytest.raises(LookAheadError, match="valuation bar"):
        simulate(daily, hourly, c)


# --- T2, T3: nothing after G_end matters ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario", ["E0", "E1", "E2"])
@pytest.mark.parametrize("substitution", ["none", "prereg_6_3"])
@pytest.mark.parametrize("closes", [HAND, RISING], ids=["hand", "rising"])
def test_bars_ending_after_g_end_change_nothing(scenario, substitution, closes):
    c = cfg(19, 24, scenario, substitution)
    g_end = evaluation_boundary(c).g_end
    daily, hourly = market(closes)
    late_h = bump(hourly.bars, lambda b: b.end_utc > g_end)
    late_d = bump(daily.bars, lambda b: b.end_utc > g_end)
    assert late_h != list(hourly.bars) and late_d != list(daily.bars)  # the perturbation is real
    base = simulate(daily, hourly, c)
    assert state(simulate(daily, series(late_h), c)) == state(base)
    assert state(simulate(series(late_d), hourly, c)) == state(base)


# --- T4: bars ending at or before G_end are used (sensitivity, exact G_end allowed) -----------------------------

def test_e0_final_valuation_bar_inside_the_boundary_is_used():
    c = cfg(19, 24, "E0")
    b = evaluation_boundary(c)
    daily, hourly = market(RISING)
    final_bar = [x for x in hourly.bars if x.end_utc == b.valuation_end]
    assert len(final_bar) == 1 and final_bar[0].end_utc <= b.g_end
    alt = series(bump(hourly.bars, lambda x: x.end_utc == b.valuation_end))
    base, other = simulate(daily, hourly, c), simulate(daily, alt, c)
    assert base.ledger.trades[-1].virtual and other.ledger.trades[-1].exec_price != base.ledger.trades[-1].exec_price
    assert other.ledger.daily[-1].price == 2 * base.ledger.daily[-1].price


def test_e2_daily_bar_ending_exactly_at_g_end_is_used():
    c = cfg(19, 24, "E2")
    b = evaluation_boundary(c)
    daily, hourly = market(RISING)
    exit_bar = daily.at_start(T0 + 26 * DAY)
    assert exit_bar.end_utc == b.g_end == b.valuation_end
    alt = series(bump(daily.bars, lambda x: x.end_utc == b.g_end))
    base, other = simulate(daily, hourly, c), simulate(alt, hourly, c)
    last = base.ledger.trades[-1]
    assert last.virtual and last.fill_kind == "primary" and last.fill_time == b.g_end
    assert other.ledger.trades[-1].ref_price == 2 * last.ref_price


# --- T7, T8: end coverage -------------------------------------------------------------------------------------

@pytest.mark.parametrize("scenario", ["E0", "E1", "E2"])
def test_hourly_data_ending_before_the_valuation_end_is_refused(scenario):
    c = cfg(19, 23, scenario)
    val_end = evaluation_boundary(c).valuation_end
    daily, hourly = market()
    short = series([b for b in hourly.bars if b.end_utc <= val_end - HOUR])
    with pytest.raises(DataIntegrityError, match="before the valuation end"):
        simulate(daily, short, c)
    exact = series([b for b in hourly.bars if b.end_utc <= val_end])
    assert exact.last_end == val_end
    assert simulate(daily, exact, c).ledger.daily[-1].ref_time == val_end


def test_run_backtest_refuses_short_hourly_data_and_writes_nothing(tmp_path):
    root = tmp_path / "bt"
    pulls = {iv: fixture_pull(root / "pulls", iv) for iv in ("day", "hour")}
    bars = {iv: export_bars(p, root / "bars-fixture").dir for iv, p in pulls.items()}
    s, _ = load_cost_settings()
    model, verified = cost_model(s, 25, "E0", INITIAL_CASH_KRW)
    out = tmp_path / "runs-fixture"

    def run(last: str):
        c = RunConfig("sma20", datetime(2025, 6, 26, tzinfo=UTC), datetime.fromisoformat(last + "T00:00:00+00:00"),
                      INITIAL_CASH_KRW, model, capacity_verified=verified)
        return run_backtest(bars["day"], bars["hour"], c, out, code_state=CODE, settings_file=DEFAULT_SETTINGS_FILE,
                            now=NOW)

    with pytest.raises(DataIntegrityError, match="before the valuation end"):
        run("2025-12-17")  # R(E + 1) = 2025-12-19 01:00, the fixture hours end on 2025-12-18
    assert not out.exists()
    ok = run("2025-12-16")  # R(E + 1) = 2025-12-18 01:00
    rep = verify_run(ok.dir, code_state=CODE)
    assert rep.ok and list(rep.checks)[:len(VERIFY_CHECKS)] == list(VERIFY_CHECKS)
    assert rep.checks["boundary"]["ok"] is True


# --- T9: internal missing buckets keep the existing rules ---------------------------------------------------------

def test_internal_missing_fill_bar_stays_pending_without_refusal():
    daily, hourly = market(drop=[T0 + 21 * DAY])  # fill bar of the day-20 buy
    res = simulate(daily, hourly, cfg())
    assert [(u.day, u.side, u.reason) for u in res.ledger.unfilled] == [(T0 + 20 * DAY, "buy", "fill_bar_missing")]
    assert res.ledger.trades[0].day == T0 + 21 * DAY


def test_missing_final_fill_bar_uses_the_virtual_fallback():
    c = cfg(19, 24)
    b = evaluation_boundary(c)
    daily, hourly = market(RISING, drop=[b.valuation_end - HOUR])
    last = simulate(daily, hourly, c).ledger.trades[-1]
    assert last.virtual and last.fill_kind == "virtual_fallback" and last.fill_time == b.valuation_end


# --- T10-T13: lookback and warm-up ----------------------------------------------------------------------------

def test_lookback_sensitivity_ends_at_the_window():
    closes = [100 + (i * 7) % 13 for i in range(70)]
    daily, hourly = series(daily_bars(closes)), series(hourly_bars(75, hour_price))
    c = cfg(40, 60, rule="sma20")
    base = simulate(daily, hourly, c)

    def bumped(day):
        return simulate(series(bump(daily.bars, lambda x: x.start_utc == T0 + day * DAY)), hourly, c)

    assert bumped(40 - 19).signals[0].detail != base.signals[0].detail  # inside the 20-close window of day 40
    assert state(bumped(40 - 20)) == state(base)  # before every window of the run
    m = cfg(40, 60, rule="M20")
    m_base = simulate(daily, hourly, m)
    assert simulate(series(bump(daily.bars, lambda x: x.start_utc == T0 + 20 * DAY)), hourly, m).signals[0].detail \
        != m_base.signals[0].detail  # close 20 days before day 40
    assert state(simulate(series(bump(daily.bars, lambda x: x.start_utc == T0 + 19 * DAY)), hourly, m)) \
        == state(m_base)


def test_missing_day_before_first_day_gives_gaps_not_refusal():
    daily, hourly = market()
    gappy = series([b for b in daily.bars if b.start_utc != T0 + 18 * DAY])
    res = simulate(gappy, hourly, cfg(20, 24))
    assert [s.reason for s in res.signals] == ["gap_in_window"] * 5  # every window of days 20-24 spans day 18


def test_missing_first_and_last_day():
    daily, hourly = market(RISING)
    no_first = series([b for b in daily.bars if b.start_utc != T0 + 21 * DAY])
    assert simulate(no_first, hourly, cfg(21, 24)).signals[0].reason == "missing_bar"
    no_last = series([b for b in daily.bars if b.start_utc != T0 + 24 * DAY])
    c = cfg(20, 24)
    res = simulate(no_last, hourly, c)
    assert res.signals[-1].value is None and res.signals[-1].reason == "missing_bar"
    last = res.ledger.trades[-1]
    assert last.virtual and last.fill_time == evaluation_boundary(c).valuation_end  # the open position is closed


@pytest.mark.parametrize("rule,need", [("M120", 121), ("R5", 6)])
def test_warm_up_boundary_is_none_not_refusal(rule, need):
    closes = [1000 + i for i in range(need + 5)]
    daily, hourly = series(daily_bars(closes)), series(hourly_bars(need + 10, hour_price))
    short = simulate(daily, hourly, cfg(need - 2, need + 1, rule=rule))
    assert short.signals[0].value is None and short.signals[0].reason == "insufficient_history"
    full = simulate(daily, hourly, cfg(need - 1, need + 1, rule=rule))
    assert full.signals[0].value is not None


# --- T14: an order of the last signal day ---------------------------------------------------------------------

def test_last_day_order_without_fill_bar_is_cancelled_at_the_end():
    c = cfg(19, 20)
    g_end = evaluation_boundary(c).g_end
    daily, hourly = market(drop=[T0 + 21 * DAY])
    res = simulate(daily, hourly, c)
    assert res.ledger.trades == [] and [x.reason for x in res.ledger.cancelled] == ["end_of_run"]
    late = series(bump(hourly.bars, lambda b: b.end_utc > g_end))
    assert state(simulate(daily, late, c)) == state(res)


# --- T15: UTC --------------------------------------------------------------------------------------------------

def test_boundary_days_must_be_utc_midnight():
    with pytest.raises(ValueError, match="00:00 UTC"):
        RunConfig("sma20", T0 + HOUR, T0 + 5 * DAY, CASH, CostModel.scenario(25, 5))
    kst = timezone(timedelta(hours=9))
    with pytest.raises(ValueError):
        RunConfig("sma20", datetime(2020, 1, 2, tzinfo=kst), T0 + 5 * DAY, CASH, CostModel.scenario(25, 5))


# --- T16: the independent verifier ----------------------------------------------------------------------------

def test_verifier_passes_primary_substituted_and_virtual_fallback_runs():
    hand = simulate(*market(), cfg(19, 23))
    assert {t.fill_kind for t in hand.ledger.trades} == {"primary"}
    assert boundary_problems(*rows(hand)) == []
    c = cfg(19, 24, substitution="prereg_6_3")
    daily, hourly = market(RISING, drop=[T0 + 21 * DAY, evaluation_boundary(c).valuation_end - HOUR])
    mixed = simulate(daily, hourly, c)
    assert {t.fill_kind for t in mixed.ledger.trades} == {"substituted", "virtual_fallback"}
    assert boundary_problems(*rows(mixed)) == []
    for scenario in ("E1", "E2", "E3", "DIAG"):
        assert boundary_problems(*rows(simulate(*market(RISING), cfg(19, 24, scenario)))) == []


def tampered(change):
    res = simulate(*market(RISING), cfg(19, 24))
    config, signals, daily, trades = rows(res)
    change(signals, daily, trades)
    return boundary_problems(config, signals, daily, trades)


def test_verifier_detects_tampered_rows():
    def late_daily(s, d, t):
        d[-1]["ref_time"] = "2020-01-29T01:00:00Z"  # R(27) > valuation end R(25) = 2020-01-27 01:00

    def late_fill(s, d, t):
        t[0]["fill_time"] = "2020-01-28T00:00:01Z"  # after G_end 2020-01-28 00:00

    def two_virtual(s, d, t):
        t[0]["virtual"] = True

    def missing_signal(s, d, t):
        del s[2]

    def fallback_time(s, d, t):
        t[-1]["fill_kind"] = "virtual_fallback"
        t[-1]["fill_time"] = "2020-01-27T00:30:00Z"

    def bar_after_fill(s, d, t):
        t[0]["fill_bar_start"] = "2020-01-23T00:00:00Z"

    def unknown_kind(s, d, t):
        t[0]["fill_kind"] = "teleported"

    cases = {late_daily: "after the valuation end", late_fill: "after G_end", two_virtual: "virtual exits",
             missing_signal: "signal days", fallback_time: "not the valuation end", bar_after_fill: "fill_bar_start",
             unknown_kind: "unknown fill_kind"}
    assert tampered(lambda s, d, t: None) == []
    for change, text in cases.items():
        problems = tampered(change)
        assert any(text in p for p in problems), (change.__name__, problems)


def test_verifier_reports_a_bad_config():
    config, signals, daily, trades = rows(simulate(*market(), cfg()))
    config["first_day"] = "2020-01-20T05:00:00Z"
    assert boundary_problems(config, signals, daily, trades)[0].startswith("config:")
