"""v0.6 test procedures (research/v06/procedures.py): p-value formulas, resampling, B1, Holm/IUT/R1-A,
segment accounting, no look-ahead in signals. Everything is synthetic and offline."""

import math
import random

import pytest

from moneylab.research.v06 import procedures as P


def test_holm_known_vector_in_input_order():
    adj = P.holm([0.01, 0.04, 0.03, 0.005])
    # sorted: 0.005*4=0.02, 0.01*3=0.03, 0.03*2=0.06, 0.04*1=0.04 -> monotone 0.06
    assert adj == pytest.approx([0.03, 0.06, 0.06, 0.02])
    assert P.holm([0.5, 0.9]) == pytest.approx([1.0, 1.0])


def test_iut_uses_the_larger_p_then_holm_across_strategies():
    p1, p2 = [0.001, 0.2, 0.004, 0.003], [0.002, 0.001, 0.5, 0.004]
    assert P.iut_holm(p1, p2) == pytest.approx(P.holm([0.002, 0.2, 0.5, 0.004]))


def test_r1a_bonferroni_of_the_two_resampling_families():
    assert P.r1a_reject_pvalue(0.01, 0.2) == pytest.approx(0.02)
    assert P.r1a_reject_pvalue(0.3, 0.004) == pytest.approx(0.008)
    assert P.r1a_reject_pvalue(0.7, 0.9) == 1.0


def test_h1_and_futility_pvalue_formulas():
    boot = [0.0, 0.1, 0.2, 0.3]
    assert P.h1_pvalue(0.1, boot) == pytest.approx(3 / 5)          # #{x - m >= m} = #{x >= 0.2} = 2
    assert P.futility_pvalue(0.1, boot, 0.2) == pytest.approx(2 / 5)  # #{x - 0.1 + 0.2 <= 0.1} = 1


def test_randomization_pvalues_count_ties_in_both_tails():
    assert P.randomization_pvalues(2.0, [1.0, 2.0, 3.0]) == (pytest.approx(0.75), pytest.approx(0.75))


def test_maxt_with_one_scenario_equals_the_single_futility_test():
    rng = random.Random(1)
    x = [rng.gauss(0.001, 0.02) for _ in range(400)]
    (boot,) = P.bootstrap_means([x], mean_block=10, resamples=199, seed=7)
    m, d = P.mean(x), P.futility_delta(0.3, x)
    assert P.maxt_futility_pvalue([m], [boot], [d]) == pytest.approx(P.futility_pvalue(m, boot, d))


def test_maxt_skips_constant_scenarios():
    assert P.maxt_futility_pvalue([0.0], [[0.0] * 50], [0.0]) == 1.0


# --- resampling -----------------------------------------------------------------------------------

def test_every_resample_covers_exactly_n_rows():
    ones = [1.0] * 257
    (boot,) = P.bootstrap_means([ones], mean_block=20, resamples=300, seed=3)
    assert all(v == pytest.approx(1.0) for v in boot)


def test_resampling_is_shared_across_series_and_deterministic():
    rng = random.Random(2)
    x = [rng.gauss(0, 1) for _ in range(300)]
    a = P.bootstrap_means([x, [2 * v for v in x]], mean_block=20, resamples=100, seed=11)
    b = P.bootstrap_means([x, [2 * v for v in x]], mean_block=20, resamples=100, seed=11)
    assert a == b
    assert a[1] == pytest.approx([2 * v for v in a[0]])               # same indices for both series
    assert P.bootstrap_means([x], mean_block=20, resamples=100, seed=12)[0] != a[0]


def test_circular_bootstrap_mean_is_centred_on_the_sample_mean():
    rng = random.Random(4)
    x = [rng.gauss(0.5, 1) for _ in range(500)]
    (boot,) = P.bootstrap_means([x], mean_block=20, resamples=2000, seed=5)
    assert P.mean(boot) == pytest.approx(P.mean(x), abs=0.02)


def test_bootstrap_rejects_bad_input():
    with pytest.raises(ValueError):
        P.bootstrap_means([[1.0, 2.0], [1.0]], mean_block=2, resamples=5, seed=0)
    with pytest.raises(ValueError):
        P.bootstrap_means([[]], mean_block=2, resamples=5, seed=0)


def test_h1_pvalue_is_roughly_uniform_under_the_null():
    """Seeded statistical smoke: iid N(0, 1), n = 400, B = 199, 300 replications."""
    rng = random.Random(8)
    hits = 0
    for rep in range(300):
        x = [rng.gauss(0, 1) for _ in range(400)]
        (boot,) = P.bootstrap_means([x], mean_block=5, resamples=199, seed=rep)
        hits += P.h1_pvalue(P.mean(x), boot) <= 0.10
    assert 0.05 <= hits / 300 <= 0.16


def test_futility_rejects_about_alpha_at_the_boundary():
    """True mean exactly at delta (annual Sharpe theta_min): rejection rate near alpha = 0.10."""
    rng = random.Random(9)
    hits = 0
    for rep in range(300):
        s = 1.0
        delta = 0.3 * s / math.sqrt(365)
        x = [rng.gauss(delta, s) for _ in range(400)]
        (boot,) = P.bootstrap_means([x], mean_block=5, resamples=199, seed=1000 + rep)
        hits += P.futility_pvalue(P.mean(x), boot, delta) <= 0.10
    assert 0.05 <= hits / 300 <= 0.16


# --- accounting -----------------------------------------------------------------------------------

def test_segment_accounting_virtual_entry_and_exit():
    c = math.log(0.99)
    r = P.segment_returns([0.01, 0.02, 0.03, 0.04], [1, 1, 0, 1], c)
    assert r == pytest.approx([0.01 + c, 0.02, c, 0.04 + c + c])      # entry at day 0, exit day 2, re-entry + virtual exit
    assert P.segment_returns([0.01, 0.02], [0, 0], c) == [0.0, 0.0]
    with pytest.raises(ValueError):
        P.segment_returns([0.1], [1, 1], c)


def test_trade_cost_combines_fee_and_slippage_multiplicatively():
    assert P.trade_cost_log(25, 5, 3.2) == pytest.approx(math.log(0.9975) + math.log(1 - 8.2e-4))


def test_runs_decomposition():
    assert P.runs([0, 0, 1, 1, 0, 1, 0, 0]) == (2, [2, 1], [1], 2)
    assert P.runs([1, 1, 0, 1]) == (0, [2, 1], [1], 0)
    assert P.runs([0, 0, 0]) == (3, [], [], 0)
    assert P.roundtrips([0, 1, 0, 1, 1]) == 2


def test_b1_preserves_exposure_spells_and_trades():
    rng = random.Random(10)
    pos = [int(rng.random() < 0.4) for _ in range(300)]
    lead, spells, gaps, trail = P.runs(pos)
    draw_rng = random.Random(3)
    for _ in range(200):
        q = P.b1_positions(pos, draw_rng)
        l2, s2, g2, t2 = P.runs(q)
        assert len(q) == len(pos) and sum(q) == sum(pos)
        assert sorted(s2) == sorted(spells) and len(s2) == len(spells)
        assert l2 + t2 + sum(g2) == lead + trail + sum(gaps)


def test_b1_fast_means_match_the_explicit_placements():
    rng = random.Random(12)
    market = [rng.gauss(0, 0.02) for _ in range(250)]
    pos = [int(rng.random() < 0.5) for _ in range(250)]
    c = math.log(0.997)
    fast = P.b1_means(market, pos, c, 50, seed=21)
    draw_rng = random.Random(21)
    slow = [P.mean(P.segment_returns(market, P.b1_positions(pos, draw_rng), c)) for _ in range(50)]
    assert fast == pytest.approx(slow)


def test_b1_pvalue_is_roughly_uniform_when_timing_is_random():
    rng = random.Random(13)
    hits = 0
    for rep in range(300):
        market = [rng.gauss(0, 0.02) for _ in range(300)]
        pos = [int(rng.random() < 0.5) for _ in range(300)]
        r = P.segment_returns(market, pos, 0.0)
        p2, _ = P.randomization_pvalues(P.mean(r), P.b1_means(market, pos, 0.0, 99, seed=rep))
        hits += p2 <= 0.10
    assert 0.05 <= hits / 300 <= 0.16


# --- signals: no look-ahead -----------------------------------------------------------------------

def test_signals_rules():
    closes = [0.0, 0.1, 0.2, 0.15, 0.05, 0.1]
    assert P.signals(closes, "momentum", 2) == [None, None, 1, 1, 0, 0]
    assert P.signals(closes, "reversal", 2) == [None, None, 0, 0, 1, 1]


def test_signal_of_day_d_ignores_every_later_close():
    rng = random.Random(14)
    closes = [0.0]
    for _ in range(400):
        closes.append(closes[-1] + rng.gauss(0, 0.03))
    for name, (rule, n) in P.STRATEGIES.items():
        base = P.signals(closes, rule, n)
        for d in (130, 250, 399):
            changed = closes[:d + 1] + [c + 5.0 * rng.choice((-1, 1)) for c in closes[d + 1:]]
            assert P.signals(changed, rule, n)[:d + 1] == base[:d + 1], name


def test_max_drawdown_and_sharpe():
    assert P.max_drawdown([0.1, -0.2, 0.05]) == pytest.approx(1 - math.exp(-0.2))
    assert P.annual_sharpe([0.0, 0.0]) == 0.0
