"""BT-2b-3 benchmarks B1-B4, seed rule bt-seed/1 and ledger alignment (SYNTHETIC / NOT_EVIDENCE).

research/v06/procedures is imported here only, as an independent reference (never by backtest code).
Ledgers come from seeded random synthetic bars (tests/backtest_helpers.random_market)."""

from __future__ import annotations

import dataclasses
import hashlib
import math
import random
import statistics
from decimal import Decimal

import pytest
from backtest_helpers import DAY, HOUR, T0, random_market, series

from moneylab.backtest import metrics as bt_metrics
from moneylab.backtest.benchmarks import (
    BT_SEED_ALGORITHM,
    BenchmarkError,
    alignment,
    b1_positions,
    b2_returns,
    b3_returns,
    b4_returns,
    bt_seed,
    bt_seed_payload,
    compare,
    leg_cost_logs,
    ledger_positions,
    market_log_returns,
    position_returns,
    quantile,
    runs,
)
from moneylab.backtest.costs import CostModel
from moneylab.backtest.ledger import Ledger
from moneylab.backtest.portfolio import RunConfig, simulate
from moneylab.research.v06 import procedures

CASH = Decimal(1_000_000)


def close(a: float, b: float, rel: float = 1e-12) -> bool:
    return abs(a - b) <= rel * max(1.0, abs(a), abs(b))


def random_positions(rng: random.Random, n: int) -> list[int]:
    out, p = [], rng.randint(0, 1)
    for _ in range(n):
        if rng.random() < 0.15:
            p = 1 - p
        out.append(p)
    return out


def ledger_for(costs: CostModel, *, seed: int = 5, days: int = 200, drop_hour0_every: int = 0,
               substitution: str = "none") -> Ledger:
    day, hour = random_market(days, seed)
    if drop_hour0_every:
        hour = [b for b in hour if not (b.start_utc.hour == 0 and (b.start_utc - T0).days % drop_hour0_every == 0)]
    cfg = RunConfig("sma20", T0 + 25 * DAY, T0 + (days - 10) * DAY, CASH, costs, fill_substitution=substitution)
    return simulate(series(day), series(hour), cfg).ledger


# --- seed -----------------------------------------------------------------------------------------------

@pytest.mark.parametrize("seed,labels,digest", [
    (7, ("B1", "sma20", "E0"), "c9080007df1d7dea494653c027d90964eefa2428bfe0b439303442b19d0494f0"),
    (2**64 - 1, ("B1", "r5", "E2"), "493919c7d12a4c6eb7a4c64552a6ec4c70ee1d37089fadc1884c854e99708cbb"),
    (0, (), "aae601940926d0968a72880b1b1a59da25e3e28f2df806c0af7f0aa17dd80fb7"),
    (1, ("검증",), "2408731692c5b67a5f0eaf83c80c2639a254ca4642329146acbf98b9e2960486"),
])
def test_seed_fixed_vectors(seed, labels, digest):
    """Digests computed outside Python (printf | sha256sum) from the bt-seed/1 payload."""
    assert BT_SEED_ALGORITHM == "bt-seed/1"
    payload = bt_seed_payload(seed, *labels)
    assert hashlib.sha256(payload).hexdigest() == digest
    assert bt_seed(seed, *labels) == int(digest[:16], 16)


def test_seed_payload_encoding():
    assert bt_seed_payload(7, "B1", "sma20", "E0") == b'["moneylab.bt_seed",1,"7","B1","sma20","E0"]'
    assert bt_seed_payload(1, "검증") == '["moneylab.bt_seed",1,"1","검증"]'.encode("utf-8")  # not \\u escapes
    assert bt_seed(1, "a|b") != bt_seed(1, "a", "b")  # no separator collision (unlike "|".join)
    assert bt_seed(1, "B1", "sma20", "E0") != bt_seed(2, "B1", "sma20", "E0")
    assert 0 <= bt_seed(2**64 - 1, "x") < 2**64


@pytest.mark.parametrize("bad", [-1, 2**64, True, 1.5, "7"])
def test_seed_range(bad):
    with pytest.raises(BenchmarkError):
        bt_seed(bad, "B1")


def test_seed_labels_must_be_strings():
    with pytest.raises(BenchmarkError):
        bt_seed(1, "B1", 3)


# --- B1 against the research implementation --------------------------------------------------------------

def test_runs_and_b1_placements_match_research():
    rng = random.Random(2024)
    for _ in range(60):
        pos = random_positions(rng, rng.randint(1, 80))
        assert runs(pos) == procedures.runs(pos)
        s = rng.randrange(2**32)
        a, b = random.Random(s), random.Random(s)
        for _ in range(5):  # same rng consumption order, draw after draw
            assert b1_positions(pos, a) == procedures.b1_positions(pos, b)


def test_b1_structure_invariants():
    rng = random.Random(9)
    for _ in range(40):
        pos = random_positions(rng, 60)
        lead, spells, gaps, trail = runs(pos)
        for _ in range(10):
            q = b1_positions(pos, rng)
            l2, s2, g2, t2 = runs(q)
            assert len(q) == len(pos) and sum(q) == sum(pos)
            assert sorted(s2) == sorted(spells) and sorted(g2) == sorted(gaps) and l2 + t2 == lead + trail


def test_b1_mean_matches_research_b1_means():
    rng = random.Random(4)
    market = [rng.gauss(0.0, 0.02) for _ in range(120)]
    pos = random_positions(rng, 120)
    c = procedures.trade_cost_log(25, 5, 1)
    seed = 123456
    ours = compare(position_returns(market, pos, c, c), market, pos, c, c, 120.0, draws=50, seed=seed,
                   labels=["B1", "sma20", "E0"])
    theirs = procedures.b1_means(market, pos, c, 50, bt_seed(seed, "B1", "sma20", "E0"))
    assert close(ours["b1"]["mean_log_return"]["mean"]["value"], sum(theirs) / len(theirs), 1e-12)


def test_original_placement_reproduces_the_strategy():
    rng = random.Random(8)
    market = [rng.gauss(0.0, 0.02) for _ in range(90)]
    pos = random_positions(rng, 90)
    c = procedures.trade_cost_log(25, 5, 0)
    ours = position_returns(market, pos, c, c)
    assert all(close(a, b) for a, b in zip(ours, procedures.segment_returns(market, pos, c)))


# --- costs, B2, B3, B4 -----------------------------------------------------------------------------------

def test_leg_cost_logs_match_the_engine_cost_model():
    for basis in ("inclusive", "on_top"):
        m = CostModel.scenario(25, 10, 2, basis)
        c_b, c_s = leg_cost_logs(m)
        buy = m.buy(Decimal(1000), Decimal(50))
        assert close(c_b, math.log(float(buy.quantity * Decimal(50) / Decimal(1000))))
        sell = m.sell(Decimal(3), Decimal(50))
        assert close(c_s, math.log(float(sell.cash_in / (Decimal(3) * Decimal(50)))))
    assert close(leg_cost_logs(CostModel.scenario(25, 5, 1))[0], procedures.trade_cost_log(25, 5, 1))
    assert leg_cost_logs(CostModel.scenario(0, 0)) == (0.0, 0.0)


def test_b2_pays_entry_and_exit_once():
    market = [0.01, -0.02, 0.005, 0.03]
    c_b, c_s = -0.003, -0.004
    r = b2_returns(market, c_b, c_s)
    assert close(r[0], 0.01 + c_b) and r[1:3] == [-0.02, 0.005] and close(r[3], 0.03 + c_s)
    assert close(sum(r), sum(market) + c_b + c_s)
    assert close(b2_returns([0.01], c_b, c_s)[0], 0.01 + c_b + c_s)


def test_b3_is_cash():
    assert b3_returns(4) == [0.0] * 4
    m = compare([0.0] * 4, [0.01] * 4, [0] * 4, -0.001, -0.001, 4.0, draws=3, seed=1, labels=["B1", "x", "E0"])
    assert m["b3"]["sum_log_return"]["value"] == 0.0 and m["b3"]["sharpe_log"]["reason"] == "zero_sample_sd"


def test_b4_has_no_rebalancing():
    rng = random.Random(6)
    market = [rng.gauss(0.0, 0.03) for _ in range(50)]
    c_b, c_s = -0.003, -0.003
    b2 = b2_returns(market, c_b, c_s)
    assert b4_returns(market, 0.0, c_b, c_s) == [0.0] * 50
    assert all(close(a, b) for a, b in zip(b4_returns(market, 1.0, c_b, c_s), b2))
    w = 0.4
    r4 = b4_returns(market, w, c_b, c_s)
    level = 0.0
    for k in range(50):  # wealth path W4(k) = (1 - w) + w * W2(k) at every k
        level += b2[k]
        assert close(math.exp(sum(r4[:k + 1])), (1 - w) + w * math.exp(level), 1e-11)
    daily_rebalanced = sum(w * x for x in b2)
    assert abs(sum(r4) - daily_rebalanced) > 1e-6  # a different benchmark
    with pytest.raises(BenchmarkError):
        b4_returns(market, 1.5, c_b, c_s)


# --- quantile --------------------------------------------------------------------------------------------

def test_quantile_linear_interpolation():
    xs = [4.0, 1.0, 3.0, 2.0]
    assert quantile(xs, 0.5) == 2.5 and quantile(xs, 0.05) == pytest.approx(1.15)
    assert quantile(xs, 0.95) == pytest.approx(3.85) and quantile(xs, 0.0) == 1.0 and quantile(xs, 1.0) == 4.0
    assert quantile([7.0], 0.95) == 7.0
    rng = random.Random(1)
    ys = [rng.random() for _ in range(101)]
    cuts = statistics.quantiles(ys, n=20, method="inclusive")  # same linear rule
    assert quantile(ys, 0.05) == pytest.approx(cuts[0], abs=1e-15)
    assert quantile(ys, 0.95) == pytest.approx(cuts[18], abs=1e-15)
    with pytest.raises(BenchmarkError):
        quantile([], 0.5)


# --- compare ---------------------------------------------------------------------------------------------

def test_compare_is_reproducible_and_seed_dependent():
    rng = random.Random(10)
    market = [rng.gauss(0.0, 0.02) for _ in range(100)]
    pos = random_positions(rng, 100)
    r = position_returns(market, pos, -0.003, -0.003)
    a = compare(r, market, pos, -0.003, -0.003, 100.0, draws=99, seed=42, labels=["B1", "sma20", "E0"])
    b = compare(r, market, pos, -0.003, -0.003, 100.0, draws=99, seed=42, labels=["B1", "sma20", "E0"])
    c = compare(r, market, pos, -0.003, -0.003, 100.0, draws=99, seed=43, labels=["B1", "sma20", "E0"])
    assert a == b and a["b1"] != c["b1"]
    assert a["status"] == "compared" and a["b1"]["p_value"] == "not computed" and a["b4"]["label"] == "REPORT_ONLY"
    q = a["b1"]["mean_log_return"]
    assert q["q05"]["value"] <= q["q50"]["value"] <= q["q95"]["value"]
    st = a["b1"]["structure"]
    assert st["exposure_days"] == sum(pos) and st["trades"] == 2 * len(runs(pos)[1])
    assert close(a["b1"]["strategy_minus_mean_b1"]["value"], sum(r) / 100 - q["mean"]["value"])
    assert a["differences"]["sum_log_return_minus_b2"]["value"] == pytest.approx(
        sum(r) - sum(b2_returns(market, -0.003, -0.003)))


def test_compare_refuses_bad_input():
    with pytest.raises(BenchmarkError):
        compare([0.0], [0.0, 0.0], [0], 0.0, 0.0, 1.0, draws=1, seed=1, labels=["B1"])
    with pytest.raises(BenchmarkError):
        compare([0.0], [0.0], [0], 0.0, 0.0, 1.0, draws=0, seed=1, labels=["B1"])
    with pytest.raises(BenchmarkError):
        compare([], [], [], 0.0, 0.0, 1.0, draws=1, seed=1, labels=["B1"])


# --- ledger alignment ------------------------------------------------------------------------------------

def test_ledger_returns_equal_position_returns():
    costs = CostModel.scenario(25, 5, 1)
    led = ledger_for(costs)
    r = bt_metrics.daily_log_returns(led)
    a = alignment(led, r, costs)
    assert a["aligned"] and a["reasons"] == [] and a["max_identity_error"] < 1e-12
    assert len(led.trades) >= 4  # the series really trades


def test_zero_cost_vs_positive_cost():
    free = ledger_for(CostModel.scenario(0, 0))
    r0 = bt_metrics.daily_log_returns(free)
    p, m = ledger_positions(free), market_log_returns(free)
    assert all(close(a, pi * mi) for a, pi, mi in zip(r0, p, m))  # net = gross without costs
    costs = CostModel.scenario(25, 5)
    paid = ledger_for(costs)
    r1 = bt_metrics.daily_log_returns(paid)
    assert [t.side for t in paid.trades] == [t.side for t in free.trades]  # signals do not depend on costs
    c_b, c_s = leg_cost_logs(costs)
    buys = sum(1 for t in paid.trades if t.side == "buy")
    sells = sum(1 for t in paid.trades if t.side == "sell")
    assert close(sum(r1) - sum(r0), buys * c_b + sells * c_s, 1e-10)


def test_misaligned_ledgers_give_reasons():
    costs = CostModel.scenario(25, 5)
    led = ledger_for(costs)
    r = bt_metrics.daily_log_returns(led)
    late = dataclasses.replace(led.trades[0], fill_time=led.trades[0].fill_time + HOUR)
    moved = Ledger(led.initial_cash, [late, *led.trades[1:]], led.unfilled, led.cancelled, led.daily)
    a = alignment(moved, r, costs)
    assert not a["aligned"] and "not at a valuation time" in a["reasons"][0]
    gap = Ledger(led.initial_cash, led.trades, led.unfilled, led.cancelled, led.daily[:5] + led.daily[6:])
    assert any("not one day apart" in x for x in alignment(gap, r, costs)["reasons"])
    bent = list(r)
    bent[3] += 1e-6
    b = alignment(led, bent, costs)
    assert not b["aligned"] and "identity" in b["reasons"][0]


def test_substituted_fills_are_not_aligned():
    costs = CostModel.scenario(25, 5)
    led = ledger_for(costs, drop_hour0_every=3, substitution="prereg_6_3")
    assert any(t.fill_kind == "substituted" for t in led.trades)
    a = alignment(led, bt_metrics.daily_log_returns(led), costs)
    assert not a["aligned"] and any("substituted" in x for x in a["reasons"])


def test_alignment_needs_two_valuations():
    led = Ledger(CASH)
    assert alignment(led, [], CostModel.scenario(25, 5))["aligned"] is False
