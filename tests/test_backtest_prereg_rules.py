"""BT-3a: the preregistered v0.6 rules M20 / M60 / M120 / R5 in the backtest engine (SYNTHETIC / NOT_EVIDENCE).

Definitions from docs/research_v06_preregistration_draft.md 6.1 (not changed). Every path here is written by
hand: no random numbers. The research implementation is imported only inside the cross-validation tests as
an independent oracle (backtest/ never imports research code)."""

from __future__ import annotations

import math
from datetime import timedelta
from decimal import Decimal

import pytest
from backtest_helpers import DAY, T0, daily_bars, series

from moneylab.backtest.data import AsOfView
from moneylab.backtest.strategy import ENGINE_VALIDATION_RULES, PREREG_V06_RULES, RULES, decide

D = Decimal
PREREG = ("M20", "M60", "M120", "R5")
NEED = {"M20": 21, "M60": 61, "M120": 121, "R5": 6}


def signal(name, ser, day):
    return decide(RULES[name], AsOfView(ser, T0 + (day + 1) * DAY + timedelta(minutes=2)), T0 + day * DAY)


def tri(i: int, period: int) -> int:
    """Integer triangle wave 0 .. period // 2 .. 0."""
    k = i % period
    return min(k, period - k)


def varied_closes(n: int) -> list[int]:
    """Gap-free deterministic path whose N-day changes take both signs for every N used here."""
    return [10_000 + 40 * tri(i, 17) + 25 * tri(i, 47) + 15 * tri(i, 130) + 3 * i - 9 * tri(i, 9) for i in range(n)]


# --- identity -------------------------------------------------------------------------------------------

def test_rule_families_are_disjoint_and_cover_the_registry():
    assert ENGINE_VALIDATION_RULES == {"sma20", "sma60", "sma120", "r5"}
    assert PREREG_V06_RULES == set(PREREG)
    assert ENGINE_VALIDATION_RULES.isdisjoint(PREREG_V06_RULES)
    assert ENGINE_VALIDATION_RULES | PREREG_V06_RULES == set(RULES)


@pytest.mark.parametrize("name", PREREG)
def test_required_history(name):
    assert RULES[name].bars_needed == NEED[name]


def test_existing_engine_validation_rules_are_unchanged():
    assert [(RULES[n].kind, RULES[n].length, RULES[n].bars_needed) for n in ("sma20", "sma60", "sma120", "r5")] == [
        ("sma", 20, 20), ("sma", 60, 60), ("sma", 120, 120), ("reversal", 5, 6)]


# --- A, B, G: momentum rules on hand paths ------------------------------------------------------------------

@pytest.mark.parametrize("name,n", [("M20", 20), ("M60", 60), ("M120", 120)])
def test_momentum_hand_path(name, n):
    closes = [100] * n + [101, 100, 99, 102]  # day n compares with day 0, day n + k with day k (all 100)
    s = series(daily_bars(closes))
    first = signal(name, s, n - 1)
    assert first.value is None and first.reason == "insufficient_history"  # n of n + 1 closes
    assert signal(name, s, n).value == 1  # 101 > 100
    assert signal(name, s, n).detail == f"close=101 close_{n}d_ago=100"
    assert signal(name, s, n + 1).value == 0  # 100 == 100: cash (strict >)
    assert signal(name, s, n + 2).value == 0  # 99 < 100
    assert signal(name, s, n + 3).value == 1  # 102 > 100


@pytest.mark.parametrize("name,n", [("M20", 20), ("M60", 60), ("M120", 120)])
def test_momentum_equal_close_is_cash(name, n):
    closes = [D("123.45")] + [D("200")] * (n - 1) + [D("123.45")]
    s = series(daily_bars(closes))
    sig = signal(name, s, n)
    assert sig.value == 0 and sig.reason is None


@pytest.mark.parametrize("name", PREREG)
def test_insufficient_history_then_first_signal(name):
    need = NEED[name]
    s = series(daily_bars([100 + i for i in range(need)]))
    short = signal(name, s, need - 2)
    assert short.value is None and short.reason == "insufficient_history"
    assert short.detail == f"{need - 1} of {need} daily bars"
    assert signal(name, s, need - 1).value is not None


@pytest.mark.parametrize("name", PREREG)
def test_missing_bar_and_gap_give_no_signal(name):
    need = NEED[name]
    bars = daily_bars([100 + i for i in range(need + 2)])
    gappy = series([b for i, b in enumerate(bars) if i != 1])
    assert signal(name, gappy, need).reason == "gap_in_window"  # the window holds days 0, 2, ..., need
    assert signal(name, gappy, 1).reason == "missing_bar"


# --- C, D: R5 ----------------------------------------------------------------------------------------------

def test_r5_prereg_hand_path():
    closes = [100, 101, 102, 103, 104, 99, 101, 102]
    s = series(daily_bars(closes))
    assert signal("R5", s, 4).reason == "insufficient_history"
    assert signal("R5", s, 5).value == 1  # 99 < 100
    assert signal("R5", s, 6).value == 0  # 101 == 101: cash (strict <)
    assert signal("R5", s, 7).value == 0  # 102 == 102 (day 2): cash
    rising = series(daily_bars([100, 100, 100, 100, 100, 101]))
    assert signal("R5", rising, 5).value == 0  # 101 > 100


def test_r5_prereg_and_engine_r5_give_the_same_signal():
    s = series(daily_bars(varied_closes(80)))
    for day in range(80):
        a, b = signal("R5", s, day), signal("r5", s, day)
        assert (a.rule, b.rule) == ("R5", "r5")
        assert (a.day, a.decided_at, a.value, a.reason, a.detail) == (b.day, b.decided_at, b.value, b.reason, b.detail)


# --- K: SMA is a different strategy -------------------------------------------------------------------------

def test_sma20_and_m20_differ_on_a_hand_path():
    closes = [100] + [200] * 19 + [150]
    s = series(daily_bars(closes))
    assert signal("M20", s, 20).value == 1  # 150 > 100 (close 20 days earlier)
    assert signal("sma20", s, 20).value == 0  # 150 <= (19 * 200 + 150) / 20 = 197.5


# --- H: look-ahead ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", PREREG)
def test_later_closes_cannot_change_a_signal(name):
    closes = varied_closes(200)
    day = 150
    base = series(daily_bars(closes))
    changed = closes[:day + 1] + [1 + 7 * i for i in range(len(closes) - day - 1)] + [5, 50_000]
    alt = series(daily_bars(changed))
    assert signal(name, base, day) == signal(name, alt, day)
    assert signal(name, base, day + 1) != signal(name, alt, day + 1)  # the change is visible one day later


# --- E: cross-validation with the research implementation (oracle only) -------------------------------------

def _oracle(name: str, closes: list) -> list:
    from moneylab.research.v06 import procedures

    kind, lookback = procedures.STRATEGIES[name]
    return procedures.signals([math.log(float(D(c))) for c in closes], kind, lookback)


def test_prereg_ids_match_the_research_strategy_table():
    from moneylab.research.v06 import procedures

    assert set(procedures.STRATEGIES) == PREREG_V06_RULES
    for name, (kind, lookback) in procedures.STRATEGIES.items():
        assert (RULES[name].kind, RULES[name].length) == (kind, lookback)


@pytest.mark.parametrize("name", PREREG)
@pytest.mark.parametrize("path", ["varied", "falling", "periodic"])
def test_signals_match_research_procedures(name, path):
    n = 260
    closes = {
        "varied": varied_closes(n),
        "falling": [50_000 - 7 * i for i in range(n)],
        "periodic": [D("1000.5") + 10 * tri(i, 20) for i in range(n)],  # period 20: M20 / M60 / M120 ties
    }[path]
    want = _oracle(name, closes)
    s = series(daily_bars(closes))
    got = [signal(name, s, day).value for day in range(n)]
    assert got == want
    if path == "varied":
        assert {0, 1} <= set(got)  # both decisions occur, so the comparison is not vacuous
