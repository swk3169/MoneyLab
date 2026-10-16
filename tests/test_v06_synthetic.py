"""v0.6 SYNTHETIC data generator (research/v06/synthetic.py): moments, causality of the edge, and
segment boundaries (a segment never reads a day at or after its end)."""

import math
import random
from dataclasses import replace

import pytest

from moneylab.research.v06 import synthetic as S
from moneylab.research.v06.procedures import STRATEGIES, signals


def daily(path):
    return [x + y + z for x, y, z in zip(path.a, path.b, path.c)]


def kurtosis(x):
    m = sum(x) / len(x)
    v = sum((t - m) ** 2 for t in x) / len(x)
    return sum((t - m) ** 4 for t in x) / len(x) / v ** 2


def acf1(x):
    m = sum(x) / len(x)
    num = sum((x[i] - m) * (x[i - 1] - m) for i in range(1, len(x)))
    return num / sum((t - m) ** 2 for t in x)


def test_noise_is_deterministic_per_seed():
    d = S.DGP()
    assert S.draw_noise(d, 50, 1).c == S.draw_noise(d, 50, 1).c
    assert S.draw_noise(d, 50, 1).c != S.draw_noise(d, 50, 2).c


def test_garch_t_has_target_vol_fat_tails_and_clustering():
    r = daily(S.make_path(S.DGP(), 365 * 120, seed=3))
    vol = math.sqrt(sum(t * t for t in r) / len(r) * 365)
    assert vol == pytest.approx(0.70, rel=0.12)
    assert kurtosis(r) > 4.0
    assert acf1([t * t for t in r]) > 0.05


def test_normal_constant_variance_has_no_clustering():
    r = daily(S.make_path(S.DGP(garch_alpha=0, garch_beta=0, t_df=None), 365 * 60, seed=4))
    assert kurtosis(r) == pytest.approx(3.0, abs=0.3)
    assert abs(acf1([t * t for t in r])) < 0.03


def test_ar1_adds_autocorrelation():
    r = daily(S.make_path(S.DGP(garch_alpha=0, garch_beta=0, t_df=None, ar1=0.2), 365 * 60, seed=5))
    assert acf1(r) == pytest.approx(0.2, abs=0.04)


def test_invalid_dgp_rejected():
    with pytest.raises(ValueError):
        S.draw_noise(S.DGP(t_df=2.0), 10, 0)
    with pytest.raises(ValueError):
        S.draw_noise(S.DGP(garch_alpha=0.5, garch_beta=0.5), 10, 0)


def test_drift_is_added_and_edge_depends_only_on_the_past():
    d = S.DGP(garch_alpha=0, garch_beta=0, t_df=None, drift_annual=0.365)
    r = daily(S.make_path(d, 365 * 200, seed=6))
    assert sum(r) / len(r) == pytest.approx(0.001, abs=0.0003)
    edge = S.DGP(edge_kind="momentum", edge_lookback=20, edge_annual=0.5)
    noise = S.draw_noise(edge, 600, 7)
    a1, b1, c1 = S.add_drift(edge, noise)
    k = 300
    noise2 = S.Noise(noise.a[:k] + [x * 3 for x in noise.a[k:]], noise.b[:k] + noise.b[k:], noise.c[:k] + [-x for x in noise.c[k:]])
    a2, b2, c2 = S.add_drift(edge, noise2)
    assert (a1[:k], b1[:k], c1[:k]) == (a2[:k], b2[:k], c2[:k])


def test_min_warmup_covers_the_longest_lookback_plus_execution_lag():
    assert S.min_warmup() == max(n for _, n in STRATEGIES.values()) + 2 == 122


def test_scenario_day_ownership():
    assert list(S.scenario_days("E0", 10, 13)) == [9, 10, 11]
    assert list(S.scenario_days("E2", 10, 13)) == [10, 11, 12]
    with pytest.raises(ValueError):
        S.scenario_days("E9", 0, 1)


def test_e2_holds_the_signal_two_days_later_and_e0_one_day_later():
    path = S.make_path(S.DGP(), 400, seed=8)
    sig = signals(path.log_close, "momentum", 20)
    _, pos0 = S.segment_market_positions(path, sig, "E0", 200, 220)
    _, pos2 = S.segment_market_positions(path, sig, "E2", 200, 220)
    assert pos0 == [int(sig[e - 1]) for e in range(199, 219)]
    assert pos2 == [int(sig[e - 2]) for e in range(200, 220)]


@pytest.mark.parametrize("scenario", S.SCENARIOS)
def test_segment_never_reads_days_at_or_after_its_end(scenario):
    """Holdout contamination guard (draft 8.1): changing every component from day g1 on leaves the
    confirmatory market series and positions unchanged."""
    path = S.make_path(S.DGP(edge_kind="momentum", edge_annual=0.4), 900, seed=9)
    g0, g1 = 200, 600
    rng = random.Random(1)
    a = path.a[:g1] + [rng.gauss(0, 0.1) for _ in path.a[g1:]]
    b = path.b[:g1] + [rng.gauss(0, 0.1) for _ in path.b[g1:]]
    c = path.c[:g1] + [rng.gauss(0, 0.1) for _ in path.c[g1:]]
    other = S.Path(a, b, c)
    for name in STRATEGIES:
        s1, s2 = S.strategy_signals(path)[name], S.strategy_signals(other)[name]
        assert S.segment_market_positions(path, s1, scenario, g0, g1) == \
            S.segment_market_positions(other, s2, scenario, g0, g1)


def test_segment_does_read_its_own_last_day():
    """Sanity of the test above: a change on day g1 - 1 is visible."""
    path = S.make_path(S.DGP(), 900, seed=10)
    other = S.Path(path.a[:599] + [path.a[599] + 1.0] + path.a[600:], path.b, path.c)
    sig = S.strategy_signals(path)["M20"]
    assert S.segment_market_positions(path, sig, "E0", 200, 600)[0] != \
        S.segment_market_positions(other, sig, "E0", 200, 600)[0]


def test_true_metrics_shape_and_edge_direction():
    lc = {"E0": -0.003, "E1": -0.003, "E2": -0.003}
    flat = S.true_metrics(S.make_path(S.DGP(), 365 * 40, seed=11), lc)
    strong = S.true_metrics(S.make_path(replace(S.DGP(), edge_kind="momentum", edge_annual=1.0), 365 * 40, seed=11), lc)
    assert set(flat) == set(STRATEGIES)
    assert strong["M60"]["sr_E0"] > flat["M60"]["sr_E0"] + 0.3
    assert 0 < strong["M60"]["exposure"] < 1
