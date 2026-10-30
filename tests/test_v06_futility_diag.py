"""BT4-FUTILITY-01 DIAG numerical core (G3a): light, deterministic tests.

Heavy validation (N1-c, N2-a, N2-b, N2-c, DC14 long-path reproduction) runs only with FUTDIAG_HEAVY=1.
"""

import functools
import hashlib
import json
import math
import os
import platform
import queue
import random
import shutil
import subprocess
import sys
import threading
from pathlib import Path as FsPath

import pytest

from moneylab.research.stats import _blocks, derived_seed, percentile
from moneylab.research.v06 import futility_diag as fd
from moneylab.research.v06.montecarlo import (
    Costs,
    Layout,
    Procedure,
    SimulationCalendar,
    _window_stats,
    source_identity,
    theta_key,
)
from moneylab.research.v06.procedures import bootstrap_means, futility_delta, futility_pvalue, mean
from moneylab.research.v06.synthetic import DGP, make_path, strategy_signals

HEAVY = os.environ.get("FUTDIAG_HEAVY") == "1"
heavy = pytest.mark.skipif(not HEAVY, reason="heavy validation: set FUTDIAG_HEAVY=1 (separately authorized gate)")


def _close(a, b, atol, rtol=1e-10):
    return abs(a - b) <= atol + rtol * max(abs(a), abs(b))


def _rng(case):
    return random.Random(fd.seed_for(fd.seed_path("FUTDIAG-TEST", "light", 0, "all", case)))


def _series(kind, n):
    rng = _rng(f"{kind}-{n}")
    if kind == "iid":
        return [rng.gauss(0.0, 0.02) for _ in range(n)]
    if kind == "ar1":
        out, prev = [], 0.0
        for _ in range(n):
            prev = 0.5 * prev + rng.gauss(0.0, 0.02)
            out.append(prev)
        return out
    if kind == "zero_inflated":
        return [rng.gauss(0.001, 0.02) if rng.random() < 0.5 else 0.0 for _ in range(n)]
    if kind == "constant":
        return [0.003] * n
    if kind == "single":
        x = [0.0] * n
        x[n // 2] = 0.05
        return x
    if kind == "tiny8":
        return [v * 1e-8 for v in _series("iid", n)]
    if kind == "tiny150":
        return [v * 1e-150 for v in _series("iid", n)]
    raise ValueError(kind)


KINDS = ["iid", "ar1", "zero_inflated", "constant", "single", "tiny8", "tiny150"]


# --- N1-a: F1 / F2 / truncation -------------------------------------------------------------------------------

@pytest.mark.parametrize("n", [2, 365, 2227])
@pytest.mark.parametrize("kind", KINDS)
def test_n1a_f1_f2_truncation(kind, n):
    x = _series(kind, n)
    v0 = fd.variance_scale(x)
    for mb in (1.0, 20.0, 60.0):
        f1_full = fd.f1_variance(x, mb, full=True)
        f1_k = fd.f1_variance(x, mb)
        f2 = fd.f2_variance(x, mb)
        if v0 == 0.0:
            assert f1_full == 0.0 and f2 == 0.0 and f1_k == 0.0
            continue
        assert _close(f1_full, f2, 1e-12 * v0)                                        # (i)
        assert abs(f1_k - f1_full) <= fd.f1_truncation_bound(x, mb) + 1e-12 * v0       # (ii)
        assert f1_full >= -1e-12 * v0 and f1_k >= -1e-12 * v0                          # (iii)
        if mb == 1.0:
            assert f1_k == f1_full == v0                                               # p = 1: C(0)/n exactly


def test_n1a_p_equal_one_has_no_lags():
    assert fd.f1_lag_limit(365, 1.0) == 0
    assert fd.f1_lag_limit(365, 0.5) == 0
    assert fd.f1_lag_limit(2, 20.0) == 1
    assert fd.f1_lag_limit(2227, 20.0) == math.ceil(math.log(1e-15) / math.log(0.95))


# --- F1 numerical policy (preregistration 5) ---------------------------------------------------------------------

def test_f1_effective_policy():
    assert fd.f1_effective(2.0, 1.0) == 2.0
    assert fd.f1_effective(-0.5e-12, 1.0) == 0.0
    assert fd.f1_effective(-1e-12, 1.0) == 0.0
    with pytest.raises(fd.StopImplementation):
        fd.f1_effective(-1.01e-12, 1.0)
    assert fd.f1_effective(0.0, 0.0) == 0.0
    with pytest.raises(fd.StopImplementation):
        fd.f1_effective(1e-30, 0.0)
    for bad in (float("nan"), float("inf")):
        with pytest.raises(fd.StopImplementation):
            fd.f1_effective(bad, 1.0)


# --- N1-b: resample se recomputed directly -----------------------------------------------------------------------

def _direct_se2(r, blocks):
    n = len(r)
    sums = [sum(r[(s + i) % n] for i in range(length)) for s, length in blocks]
    m_star = sum(sums) / n
    c_l = 1.0 / (1.0 - sum(length * length for _, length in blocks) / (n * n))
    return m_star, c_l * sum((v - length * m_star) ** 2 for v, (_, length) in zip(sums, blocks)) / (n * n)


@pytest.mark.parametrize("mb", [1.0, 20.0, 60.0])
@pytest.mark.parametrize("kind", ["iid", "ar1", "zero_inflated"])
def test_n1b_resample_se_direct(kind, mb):
    r = _series(kind, 365)
    pre = fd._Prefix(r)
    seed = fd.seed_for(fd.seed_path("FUTDIAG-TEST", "N1b", 0, kind, f"b{int(mb)}"))
    for blocks in fd.resample_blocks(len(r), mb, 25, seed):
        m_star, se2 = fd.resample_mean_and_se2(pre, len(r), blocks)
        if len(blocks) < 2:                                   # J_b = 1 occurs naturally for long blocks: RD path
            assert se2 is None
            continue
        dm, dse2 = _direct_se2(r, blocks)
        x_star = [r[(s + i) % len(r)] for s, length in blocks for i in range(length)]
        v0_star = fd.variance_scale(x_star)
        assert se2 is not None
        assert _close(m_star, dm, 1e-12 * abs(dm) + 1e-300)
        assert _close(se2, dse2, 1e-12 * v0_star)
        n = len(r)
        lengths = [length for _, length in blocks]
        assert _close(fd.c_l_factor(lengths, n), 1.0 / (1.0 - sum(x * x for x in lengths) / n ** 2), 0.0)
        if mb == 1.0:
            assert all(length == 1 for length in lengths)
            assert _close(fd.c_l_factor(lengths, n), n / (n - 1), 0.0)
        assert blocks[-1][1] >= 1 and sum(lengths) == n                       # last block truncated to fit


def test_n1b_c_l_factor_direct():
    assert fd.c_l_factor([5, 5, 5, 5], 20) == pytest.approx(4 / 3, rel=1e-15)          # equal lengths: J/(J-1)
    assert fd.c_l_factor([1] * 10, 10) == pytest.approx(10 / 9, rel=1e-15)             # p = 1: n/(n-1)
    assert fd.c_l_factor([3, 7], 10) == pytest.approx(1 / (1 - 58 / 100), rel=1e-15)   # variable lengths
    for bad in ([10], [3, 3]):
        with pytest.raises(ValueError):
            fd.c_l_factor(bad, 10)


def test_n1b_single_block_is_degenerate():
    r = _series("iid", 50)
    m_star, se2 = fd.resample_mean_and_se2(fd._Prefix(r), 50, [(7, 50)])
    assert se2 is None and math.isclose(m_star, mean(r), rel_tol=1e-12)


# --- V0 / S1 block identity and N1-d -----------------------------------------------------------------------------

@pytest.mark.parametrize("mb", [20.0, 60.0])
def test_s1_blocks_reproduce_bootstrap_means(mb):
    r = _series("zero_inflated", 365)
    seed = fd.seed_for(fd.seed_path("FUTDIAG-TEST", "blocks", 0, "f12", f"b{int(mb)}"))
    boot = bootstrap_means([r], mean_block=mb, resamples=200, seed=seed)[0]
    pre = fd._Prefix(r)
    mine = [fd.resample_mean_and_se2(pre, len(r), b)[0] for b in fd.resample_blocks(len(r), mb, 200, seed)]
    assert mine == boot                                                           # bit-identical


def test_v0b60_block_lengths():
    rng = random.Random(fd.seed_for(fd.seed_path("FUTDIAG-TEST", "b60", 0, "all", "len")))
    firsts = [_blocks(100_000, 60.0, rng)[0][1] for _ in range(4000)]
    m = sum(firsts) / len(firsts)
    se = math.sqrt(60.0 * 59.0) / math.sqrt(len(firsts))                           # geometric(1/60) sd
    assert abs(m - 60.0) <= 4 * se
    seed = fd.seed_for(fd.seed_path("FUTDIAG-TEST", "b60", 0, "f36", "b60"))
    r = _series("iid", 1096)
    assert bootstrap_means([r], mean_block=60.0, resamples=50, seed=seed) != \
        bootstrap_means([r], mean_block=20.0, resamples=50, seed=seed)


@pytest.mark.parametrize("kind", ["iid", "ar1", "zero_inflated"])
@pytest.mark.parametrize("n", [365, 1096])
def test_n1d_fixed_se_equals_v0(kind, n):
    r = _series(kind, n)
    theta = 0.7
    seed = fd.seed_for(fd.seed_path("FUTDIAG-TEST", "N1d", 0, f"{kind}-{n}", "b20"))
    v0 = fd.v0_family(r, theta, 20.0, 199, seed)
    se = math.sqrt(fd.f1_effective(fd.f1_variance(r, 20.0), fd.variance_scale(r)))
    hooked = fd.s1_from_blocks(r, v0.delta_hat, 20.0, fd.resample_blocks(n, 20.0, 199, seed), se_override=se)
    assert hooked.p_hi == hooked.p_lo == v0.p_v0


def test_n1d_boundary_adjacent():
    """delta placed exactly on, and one ulp around, a resample's boundary: hook and V0 agree bit for bit."""
    r = _series("ar1", 365)
    seed = fd.seed_for(fd.seed_path("FUTDIAG-TEST", "N1d", 0, "boundary", "b20"))
    boot = bootstrap_means([r], mean_block=20.0, resamples=99, seed=seed)[0]
    m = mean(r)
    se = math.sqrt(fd.f1_effective(fd.f1_variance(r, 20.0), fd.variance_scale(r)))
    pre = fd._Prefix(r)
    assert [fd.resample_mean_and_se2(pre, len(r), b)[0] for b in fd.resample_blocks(len(r), 20.0, 99, seed)] == boot
    for k in (0, 17, 50):
        exact = m - (boot[k] - m)                                             # boot_k - m + delta == m (up to rounding)
        for delta in (math.nextafter(exact, -math.inf), exact, math.nextafter(exact, math.inf)):
            v0 = futility_pvalue(m, boot, delta)
            hooked = fd.s1_from_blocks(r, delta, 20.0, fd.resample_blocks(len(r), 20.0, 99, seed), se_override=se)
            assert hooked.p_hi == hooked.p_lo == v0


# --- N1-e: degeneracy ------------------------------------------------------------------------------------------

def test_n1e_sample_degeneracy():
    res = fd.s1_from_blocks([0.0] * 30, 0.0, 20.0, fd.resample_blocks(30, 20.0, 9, 1))
    assert (res.p_hi, res.p_lo, res.d, res.reason, res.se) == (1.0, 1.0, 0, fd.SD, None)


def test_n1e_resample_degeneracy_and_p_bounds():
    r = [0.0] * 20 + [0.01, -0.02, 0.015, 0.0, 0.03, -0.01, 0.02, 0.005, -0.015, 0.01]
    n = len(r)
    zero_blocks = [(i % 20, 1) for i in range(n)]             # every block inside the zero run
    single = [(3, n)]                                         # J_b = 1
    normal = [(0, 10), (10, 10), (20, 10)]
    delta = 0.0
    res = fd.s1_from_blocks(r, delta, 20.0, [zero_blocks, single, normal])
    assert res.d == 2
    assert res.p_lo == res.p_hi - res.d / 4
    assert res.p_lo <= res.p_hi
    assert res.reason is None and res.se is not None
    assert res.nd_share == pytest.approx(1 / 3)               # the all-zero resample has se* = 0 < 0.25 se
    assert res.nd_flag


def test_n1e_classify_resample_boundaries():
    se = 2.0
    assert fd.classify_resample(None, se) == (True, False)                    # J_b < 2: RD, never ND
    assert fd.classify_resample(0.0, se) == (True, True)                      # se* = 0: RD and ND
    assert fd.classify_resample((1e-6 * se) ** 2, se) == (True, True)         # se* = 1e-6 se: RD (<=) and ND
    assert fd.classify_resample((0.25 * se) ** 2, se) == (False, False)       # se* = 0.25 se: not ND (strict <)
    assert fd.classify_resample((0.2499 * se) ** 2, se) == (False, True)
    with pytest.raises(fd.StopImplementation):
        fd.classify_resample(float("nan"), se)


def test_n1e_nd_denominator_is_b():
    r = [0.0] * 20 + [0.01, -0.02, 0.015, 0.0, 0.03, -0.01, 0.02, 0.005, -0.015, 0.01]
    n = len(r)
    zero = [(i % 20, 1) for i in range(n)]
    single = [(3, n)]
    res = fd.s1_from_blocks(r, 0.0, 20.0, [zero, single, single, single])
    assert res.d == 4 and res.nd_share == pytest.approx(1 / 4)               # ND counts only the defined se* (zero)


def test_finite_or_stop():
    assert fd.finite_or_stop(1.5, "x") == 1.5
    for bad in (float("nan"), float("-inf")):
        with pytest.raises(fd.StopImplementation):
            fd.finite_or_stop(bad, "x")


# --- T3 parity with MC-V06 _window_stats -------------------------------------------------------------------------

def test_t3_parity_with_window_stats():
    cal, lay = SimulationCalendar(), Layout()
    seed = derived_seed(20261012, "normal_M60_+0p7", "rep", "0")
    dgp = DGP(garch_alpha=0.0, garch_beta=0.0, t_df=None, edge_kind="momentum", edge_lookback=60, edge_annual=0.7)
    path = make_path(dgp, lay.total_days(cal), seed)
    sigs = strategy_signals(path)
    lc = Costs().log_costs()
    proc = Procedure(bootstrap=99, draws=9)
    for tag, (g0, g1) in (("holdout", lay.bounds(cal)["holdout"]), ("forward_12m", lay.bounds(cal)["forward_12m"])):
        ref = _window_stats(path, sigs, lc, proc, g0, g1, seed, tag)["M60"]["p_fut"]
        r = fd.window_e0_returns(path, sigs["M60"], g0, g1, lc["E0"])
        for theta in proc.theta_min_options:
            mine = fd.v0_family(r, theta, proc.mean_block, proc.bootstrap, derived_seed(seed, tag, "boot"))
            assert mine.p_v0 == ref[theta_key(theta)]
            assert mine.delta_hat == futility_delta(theta, r)


def test_dc7_window_bounds():
    b = Layout().bounds(SimulationCalendar())
    assert b["confirmatory"] == (122, 2349)
    assert b["forward_12m"] == (3323, 3688)
    assert b["forward_24m"][1] - b["forward_24m"][0] == 731
    assert b["forward_36m"][1] - b["forward_36m"][0] == 1096


def test_v0d_uses_delta_true():
    r = _series("iid", 365)
    seed = fd.seed_for(fd.seed_path("FUTDIAG-TEST", "v0d", 0, "f12", "b20"))
    res = fd.v0_family(r, 0.7, 20.0, 99, seed, sigma_pop=0.03)
    assert res.delta_true == pytest.approx(0.7 * 0.03 / math.sqrt(365), rel=1e-15)
    boot = bootstrap_means([r], mean_block=20.0, resamples=99, seed=seed)[0]
    assert res.p_v0d == (1 + sum(1 for x in boot if x - res.m + res.delta_true <= res.m)) / 100


# --- V-1 order and exclusivity -----------------------------------------------------------------------------------

def test_v1_order_and_exclusivity():
    rng = random.Random(fd.seed_for(fd.seed_path("FUTDIAG-TEST", "v1", 0, "all", "labels")))
    for _ in range(300):
        big_r = rng.randint(5, 60)
        v0 = [rng.random() < 0.3 for _ in range(big_r)]
        hi = [rng.random() < 0.2 for _ in range(big_r)]
        lo = [h or rng.random() < 0.1 for h in hi]               # p_lo <= p_hi => I_lo >= I_hi
        c_lo, c_hi = fd.mcnemar(v0, lo), fd.mcnemar(v0, hi)
        assert c_lo.d_hat <= c_hi.d_hat
        for rej_lo in (False, True):
            label, _ = fd.label_v1(rej_lo, c_lo, c_hi, fd.eff_threshold(0.12), rej_lo)
            supported = rej_lo and c_lo.d_hat >= fd.eff_threshold(0.12)
            assert not (supported and c_hi.upper < fd.MIN_EFFECT)
            assert label in (fd.SUPPORTED, fd.WEAKENED, fd.INCONCLUSIVE)


def test_v1_degeneracy_ambiguous_branch():
    def c(d, upper):
        return fd.Contrast(d, 0.005, 0.0, upper, 0, 0, None)
    eff = 0.01
    # lo fails Holm, hi would be SUPPORTED: label from lo/hi rules, flagged ambiguous
    label, reason = fd.label_v1(False, c(0.005, 0.02), c(0.03, 0.04), eff, True)
    assert (label, reason) == (fd.INCONCLUSIVE, fd.DEGENERACY_AMBIGUOUS)
    # hi upper >= 0.01 but lo upper < 0.01: would be WEAKENED under lo, flagged
    label, reason = fd.label_v1(False, c(0.0, 0.008), c(0.004, 0.012), eff, False)
    assert (label, reason) == (fd.INCONCLUSIVE, fd.DEGENERACY_AMBIGUOUS)
    # both treatments agree
    assert fd.label_v1(True, c(0.02, 0.03), c(0.03, 0.04), eff, True) == (fd.SUPPORTED, None)
    assert fd.label_v1(False, c(0.0, 0.005), c(0.001, 0.006), eff, False) == (fd.WEAKENED, None)


def test_mcnemar_zero_discordance_reason_only():
    z = fd.mcnemar([True, False, True, False], [True, False, True, False])
    assert (z.n10, z.n01, z.d_hat, z.se, z.p_one_sided, z.reason) == (0, 0, 0.0, 0.0, 1.0, fd.NO_DISCORDANCE)


def test_mcnemar_zero_discordance_follows_work_order_weakened_rule():
    """R2 option A: no discordant pair -> D = 0, SE = 0, p = 1, U_D = 0, reason NO_DISCORDANCE (internal only);
    the Work Order rule U_D < 0.01 then gives WEAKENED. No new research state is produced."""
    base = [True] * 40 + [False] * 60
    z = fd.mcnemar(base, list(base))
    assert (z.n10, z.n01) == (0, 0)
    assert z.d_hat == 0.0 and z.se == 0.0 and z.p_one_sided == 1.0 and z.upper == 0.0
    assert z.reason == fd.NO_DISCORDANCE
    states = {fd.SUPPORTED, fd.WEAKENED, fd.INCONCLUSIVE}
    for holm in (False, True):
        for eff in (0.01, 0.03):
            label = fd.label_mcnemar(holm, z, eff)
            assert label == fd.WEAKENED and label in states
            assert fd.label_mcnemar(holm, z, eff, extra_ok=False) == fd.WEAKENED
    assert fd.NO_DISCORDANCE not in states
    rej = fd.holm_rejections({"V-1": 0.001, "V-2": z.p_one_sided})
    assert rej == {"V-1": True, "V-2": False}                                 # p = 1 never rejects


def test_mcnemar_and_holm():
    c = fd.mcnemar([True] * 30 + [False] * 70, [False] * 10 + [True] * 20 + [False] * 70)
    assert (c.n10, c.n01) == (10, 0) and c.d_hat == pytest.approx(0.1)
    assert c.se == pytest.approx(math.sqrt(10 - 100 * 0.01) / 100)
    none = fd.mcnemar([True, False], [True, False])
    assert none.reason == fd.NO_DISCORDANCE and none.p_one_sided == 1.0
    rej = fd.holm_rejections({"a": 0.001, "b": 0.006, "c": 0.02, "d": 0.5, "e": 0.9})
    assert rej == {"a": True, "b": True, "c": False, "d": False, "e": False}
    assert fd.eff_threshold(0.09) == 0.01 and fd.eff_threshold(0.15) == pytest.approx(0.025)


# --- V-4 pure functions ------------------------------------------------------------------------------------------

def test_v4_delta_rej_monotone_and_corners():
    assert fd.delta_rej(0.0, 0.4) == pytest.approx(0.0, abs=1e-15)
    assert fd.delta_rej(-0.1, 0.4) > 0 > fd.delta_rej(0.1, 0.4)
    assert fd.delta_rej(-0.1, 0.3) > fd.delta_rej(-0.1, 0.5)          # Delta < 0: decreasing in sigma
    assert fd.delta_rej(0.1, 0.3) < fd.delta_rej(0.1, 0.5)            # Delta > 0: increasing in sigma
    lo, hi = fd.rect_extrema(-0.08, 0.02, 0.35, 0.45)
    grid = [fd.delta_rej(-0.08 + 0.1 * i / 20, 0.35 + 0.1 * j / 20) for i in range(21) for j in range(21)]
    assert lo == pytest.approx(min(grid)) and hi == pytest.approx(max(grid))
    assert fd.v4_effect_gate(-0.05, 0.35, 0.45) == fd.delta_rej(-0.05, 0.45)
    assert fd.v4_weakened_max(-0.05, 0.35, 0.45) == fd.delta_rej(-0.05, 0.35)
    assert fd.v4_weakened_max(0.02, 0.35, 0.45) == fd.delta_rej(0.02, 0.45)
    d_star = -0.4 * (fd.Z_ALPHA + fd._N.inv_cdf(0.06))
    assert fd.delta_rej(d_star, 0.4) == pytest.approx(0.01, abs=1e-12)
    assert fd.v4_approx_ok(-0.2, 0.4) and not fd.v4_approx_ok(-0.21, 0.4)


def test_v4_t_distribution_and_inference():
    assert fd.t_ppf(0.975, 39) == pytest.approx(2.0227, abs=1e-4)
    assert fd.t_ppf(0.995, 39) == pytest.approx(2.7079, abs=1e-4)
    assert fd.t_cdf(0.0, 39) == pytest.approx(0.5)
    vals = [0.70 + 0.05 * math.sin(i) for i in range(40)]
    inf = fd.v4_inference(0.68, 0.7, vals)
    assert inf.delta_hat == pytest.approx(-0.02)
    assert inf.delta_lower < inf.delta_hat < inf.delta_upper
    assert inf.p_one_sided == pytest.approx(fd.t_cdf(inf.delta_hat / inf.se, 39))


def test_v4_batches_and_sigma_interval():
    x = list(range(103))
    parts = fd.split_batches(x, 10)
    assert [len(p) for p in parts] == [11, 11, 11] + [10] * 7 and sum(parts, []) == x
    srs, lengths = fd.batch_sharpes([math.sin(i) + 0.01 for i in range(1_459_876 // 100)], 40)
    assert len(srs) == 40 and sum(lengths) == 14_598 and set(lengths) == {364, 365}
    assert lengths == sorted(lengths, reverse=True)                           # remainder goes to the first batches
    vals = [math.sin(i) for i in range(2000)]
    s_hat, kappa, s_lo, s_hi = fd.sigma_interval(vals)
    half = fd.Z_SIGMA * math.sqrt((kappa - 1) / (4 * 2000))
    assert s_lo == pytest.approx(s_hat * math.exp(-half)) and s_hi == pytest.approx(s_hat * math.exp(half))
    assert fd.Z_SIGMA == pytest.approx(3.023341, abs=1e-6)


def test_kurtosis_non_excess_normal_and_zero_variance():
    rng = _rng("kurtosis")
    vals = [rng.gauss(0.0, 1.0) for _ in range(20_000)]
    _, kappa, _, _ = fd.sigma_interval(vals)
    assert abs(kappa - 3.0) <= 4 * math.sqrt(24 / 20_000)                     # non-excess: about 3 for a normal
    d = [v - sum(vals) / len(vals) for v in vals]
    m2 = sum(v * v for v in d) / len(d)
    assert kappa == pytest.approx(sum(v ** 4 for v in d) / len(d) / m2 ** 2, rel=1e-12)
    with pytest.raises(fd.StopImplementation):
        fd.sigma_interval([0.5] * 10)


def test_pilot_r_rule():
    assert fd.clopper_pearson_upper(0, 200) == pytest.approx(1 - 0.05 ** (1 / 200), rel=1e-9)
    assert fd.Z_HOLM_WORST == pytest.approx(2.575829, abs=1e-6) and fd.Z_POWER == pytest.approx(0.841621, abs=1e-6)
    assert (fd.Z_HOLM_WORST + fd.Z_POWER) ** 2 == pytest.approx(11.6790, abs=1e-4)
    assert fd.required_reps(0.0149) == (10_000, False)
    r, over = fd.required_reps(0.15)
    assert r == 18_000 and not over
    assert fd.required_reps(0.40)[1]


# --- seeds -------------------------------------------------------------------------------------------------------

def test_seed_namespaces():
    fd.check_namespaces()
    with pytest.raises(fd.StopImplementation):
        fd.check_namespaces(("FUTDIAG", "FUTDIAG"))
    with pytest.raises(fd.StopImplementation):
        fd.check_namespaces(("FUTDIAG", "FUTVAL"))
    with pytest.raises(fd.StopImplementation):
        fd.seed_path("FUTVAL", "c", 0, "w", "r")
    p = fd.seed_path("FUTDIAG", "E1-theta0.7", 3, "f12", "b20")
    assert fd.seed_for(p) == derived_seed(20261029, "FUTDIAG", "E1-theta0.7", "3", "f12", "b20")
    assert fd.seed_for(p) != fd.seed_for(fd.seed_path("FUTDIAG-PILOT", "E1-theta0.7", 3, "f12", "b20"))


def test_seed_collision_report_duplicates_and_external():
    paths = [fd.seed_path("FUTDIAG", "E1-theta0.7", i, "all", "path") for i in range(50)]
    paths.append(paths[7])                                                    # same logical path twice
    ext = {fd.seed_for(paths[3]): ["MC-V06", "normal_M60_+0p7", "rep", "x"]}
    rep = fd.seed_collisions(paths, ext)
    assert rep["policy"] == "report_only"
    assert rep["count_within_diag"] == 0                                      # a duplicate is not a collision
    assert rep["count_duplicate_paths"] == 1 and rep["duplicates"] == [{"path": list(paths[7]), "times": 2}]
    assert rep["count_vs_external"] == 1 and rep["vs_external"][0]["external"] == ext[fd.seed_for(paths[3])]
    assert rep["n_paths"] == 50 and rep["n_values"] == 50 and len(rep["sorted_list_sha256"]) == 64
    assert fd.seed_collisions(paths, ext) == rep                                # deterministic


def _find_real_collision():
    # CRC32 separates equal-length inputs that differ within 32 bits, so a lone rep counter never collides with
    # itself; varying several fields spreads the differences and the birthday bound (~8e4 draws) applies.
    seen = {}
    for i in range(600_000):
        p = fd.seed_path("FUTDIAG-TEST", f"cell{i % 997}", i, f"w{(i * 7919) % 100_003}", "path")
        v = fd.seed_for(p)
        if v in seen:
            return seen[v], p
        seen[v] = p
    raise AssertionError("no 32-bit collision found in 400,000 paths")


def test_seed_collision_between_different_logical_paths():
    a, b = _find_real_collision()                                             # birthday bound: ~8e4 expected
    assert a != b and fd.seed_for(a) == fd.seed_for(b)
    rep = fd.seed_collisions([a, b, fd.seed_path("FUTDIAG", "E1-theta0.7", 0, "all", "path")])
    assert rep["count_within_diag"] == 1 and rep["count_duplicate_paths"] == 0
    assert rep["within"] == [{"seed": fd.seed_for(a), "paths": sorted([list(a), list(b)])}]
    assert rep["n_paths"] == 3 and rep["n_values"] == 2


# --- heavy validation (FUTDIAG_HEAVY=1 only) ---------------------------------------------------------------------

@heavy
def test_heavy_placeholder_guard():
    """Heavy N1-c / N2 / DC14 checks are implemented in G3c; this guard keeps the env gate exercised."""
    assert HEAVY


# Heavy tests (WORK_ORDER TEST_GATES :372-383, preregistration §2 / §6, ERRATA-002 :80-83). Every R, B, n, seed string
# and bound is the contract's; a failure is reported as STOP_FOR_USER_DECISION (never retried with another seed,
# never a wider tolerance) except T12, whose mismatch is a STOP. Single process: no pool, no worker.
# Interpretations the documents leave open (reported as UNSPECIFIED with the G3 report, not contract values):
#   * series generators: the N1-a light forms of _series (iid N(0, 0.02^2); AR(1) rho 0.5 with N(0, 0.02^2)
#     innovations; zero-inflated: N(0.001, 0.02^2) with probability 0.5, else 0), drawn from the contract seed;
#   * N1-c: its single seed drives one random.Random stream, the series first, then the B resample block lists;
#   * N1-c SE_MC: the large-sample sd of the sample variance, sqrt((m4 - v^2 (B - 3)/(B - 1)) / B), v with ddof 1; a
#     negative or non-finite radicand is N1C_SE_INVALID (STOP_FOR_USER_DECISION, nothing substituted), exactly 0
#     gives SE_MC = 0 and the unchanged rule;
#   * N2-a: a resample with J_b < 2 has no se*^2 and makes rho_hat NaN (N2A_INVALID);
#   * N2-b / N2-c: T = (m - delta_hat)/se and T*_b = (m*_b - m)/se*_b as in S1; T* only for S1's normal resamples
#     (RD by classify_resample counted as d), quantiles by stats.percentile over the finite values with every
#     excluded count reported;
#   * N2-c: S1 at mean_block 20 with V0's delta_hat (as in every record); rejection is PD-1's primary p, p_hi <= 0.05
#     (p_lo reported only).

N1C_B, N2A_B, N2C_R, N2C_B = 200_000, 20_000, 2_000, 999
N1C_CASES = [(s, 365, mb) for s in fd.CASE_SERIES for mb in (1.0, 20.0)]
N2A_CASES = [(s, n) for s in fd.CASE_SERIES for n in (365, 2227)]
N2C_NS = (365, 2227)
N2B_QUANTILES = (0.01, 0.05, 0.5, 0.95, 0.99)
STOP_FOR_USER = "STOP_FOR_USER_DECISION"


def _heavy_series(kind, n, rng):
    """The N1-a light series forms (_series) drawn from a given generator (contract seed)."""
    if kind == "iid":
        return [rng.gauss(0.0, 0.02) for _ in range(n)]
    if kind == "ar1":
        out, prev = [], 0.0
        for _ in range(n):
            prev = 0.5 * prev + rng.gauss(0.0, 0.02)
            out.append(prev)
        return out
    if kind == "zero_inflated":
        return [rng.gauss(0.001, 0.02) if rng.random() < 0.5 else 0.0 for _ in range(n)]
    raise AssertionError(kind)


def n2b_report_values(values, excluded=None):
    """N2-b report of one sample: counts of NaN and +/-Inf (kept out of the ordering and reported, never dropped
    silently), the other exclusions given by the caller (e.g. S1's RD resamples), the finite values used and
    their stats.percentile quantiles; UNDEFINED when no finite value is left. No range, no verdict."""
    vals = list(values)
    finite = [v for v in vals if math.isfinite(v)]
    out = {"n_total": len(vals) + sum((excluded or {}).values()), "excluded": dict(excluded or {}),
           "n_nan": sum(1 for v in vals if v != v), "n_pos_inf": sum(1 for v in vals if v == math.inf),
           "n_neg_inf": sum(1 for v in vals if v == -math.inf), "n_valid": len(finite)}
    out["quantiles"] = ({str(q): percentile(finite, q) for q in N2B_QUANTILES} if finite else "UNDEFINED")
    return out


def n1c_se_mc(var_mc, m4, b):
    """N1-c SE_MC = sqrt((m4 - v^2 (B - 3)/(B - 1)) / B). Negative or non-finite radicand: N1C_SE_INVALID (no
    epsilon, no absolute value, no clamp); exactly 0: SE_MC = 0."""
    radicand = m4 - var_mc ** 2 * (b - 3) / (b - 1)
    if not math.isfinite(radicand) or radicand < 0:
        return "N1C_SE_INVALID", radicand, math.nan
    return "OK", radicand, math.sqrt(radicand / b)


def _n1c_case(series, n, mean_block):
    """F1 and the Monte Carlo variance of B = 200,000 resample means m* (bit-identical to bootstrap_means)."""
    parts = fd.n1c_seed_parts(series, n, mean_block)
    seed = fd.explicit_seed(parts)
    rng = random.Random(seed)
    x = _heavy_series(series, n, rng)
    pre = fd._Prefix(x)
    ms = [fd.resample_mean_and_se2(pre, n, _blocks(n, mean_block, rng))[0] for _ in range(N1C_B)]
    mbar = sum(ms) / N1C_B
    dev = [m - mbar for m in ms]
    var_mc = sum(d * d for d in dev) / (N1C_B - 1)
    m4 = sum(d ** 4 for d in dev) / N1C_B
    status, radicand, se_mc = n1c_se_mc(var_mc, m4, N1C_B)
    f1 = fd.f1_variance(x, mean_block)
    return {"case_id": fd.case_id(series, n, mean_block), "seed_parts": list(parts), "seed": seed, "F1": f1,
            "Var_MC": var_mc, "m4": m4, "radicand": radicand, "se_status": status, "SE_MC": se_mc,
            "error": abs(f1 - var_mc), "tolerance": 4 * se_mc}


@heavy
@pytest.mark.parametrize("series, n, mean_block", N1C_CASES)
def test_heavy_n1c_empirical_variance(series, n, mean_block):
    """N1-c (WO:372-377): |F1 - Var_MC(m*)| <= 4 SE_MC, B = 200,000, n = 365, mean_block {1, 20}, fixed seed
    ("FUTDIAG-TEST", "N1c", case). A failure keeps its seed and is a STOP_FOR_USER_DECISION (no other seed)."""
    r = _n1c_case(series, n, mean_block)
    print(json.dumps({"N1-c": r}))
    if r["se_status"] != "OK":
        pytest.fail(f"{STOP_FOR_USER}: N1C_SE_INVALID {json.dumps(r)}")
    if not r["error"] <= r["tolerance"]:
        pytest.fail(f"{STOP_FOR_USER}: N1-c {json.dumps(r)}")


def test_n1c_se_mc_radicand_rules():
    """Light: a negative or non-finite radicand is N1C_SE_INVALID (not replaced), exactly 0 gives SE_MC = 0."""
    assert n1c_se_mc(1.0, 1.0 * 199_997 / 199_999, 200_000)[0] == "OK"                    # radicand 0
    assert n1c_se_mc(1.0, 1.0 * 199_997 / 199_999, 200_000)[2] == 0.0
    assert n1c_se_mc(1.0, 0.5, 200_000)[0] == "N1C_SE_INVALID"
    assert n1c_se_mc(math.nan, 1.0, 200_000)[0] == "N1C_SE_INVALID"
    assert n1c_se_mc(1.0, math.inf, 200_000)[0] == "N1C_SE_INVALID"
    status, radicand, se = n1c_se_mc(1.0, 3.0, 200_000)
    assert status == "OK" and se == math.sqrt(radicand / 200_000) and radicand > 0


@functools.lru_cache(maxsize=None)
def _n2a_case(series, n):
    """N2-a fixed sample ("N2a-data", case) and its B_N2a = 20,000 resamples ("N2a-boot", case), mean_block 20."""
    data_seed = fd.explicit_seed(fd.n2a_seed_parts("data", series, n))
    boot_seed = fd.explicit_seed(fd.n2a_seed_parts("boot", series, n))
    x = _heavy_series(series, n, random.Random(data_seed))
    se2 = fd.f1_effective(fd.f1_variance(x, fd.MEAN_BLOCK), fd.variance_scale(x))
    pre, m = fd._Prefix(x), mean(x)
    se = math.sqrt(se2)
    star_se2, t_star, rd = [], [], 0
    for blocks in fd.resample_blocks(n, fd.MEAN_BLOCK, N2A_B, boot_seed):
        m_star, s2 = fd.resample_mean_and_se2(pre, n, blocks)
        star_se2.append(math.nan if s2 is None else s2)
        if se2 == 0.0:                                    # SD: no T* at all (S1 returns p = 1 without resamples)
            continue
        if fd.classify_resample(s2, se)[0]:               # S1's RD (J_b < 2 or se* <= 1e-6 se): no T*, counted
            rd += 1
            continue
        assert s2 is not None
        t_star.append((m_star - m) / math.sqrt(s2))
    return {"case_id": fd.case_id(series, n, fd.MEAN_BLOCK), "data_seed": data_seed, "boot_seed": boot_seed,
            "se2": se2, "star_se2": tuple(star_se2), "t_star": tuple(t_star), "rd": rd, "sd": se2 == 0.0}


def n2a_verdict(se2, star_se2):
    """Preregistration §6 N2-a, in order: N2A_UNDEFINED_DENOMINATOR, N2A_INVALID, N2A_IMPRECISE, N2A_FAIL, N2A_PASS."""
    b = len(star_se2)
    if se2 == 0.0:
        return "N2A_UNDEFINED_DENOMINATOR", math.nan, math.nan
    mean_s = sum(star_se2) / b
    rho = mean_s / se2
    se_rho = math.sqrt(sum((v - mean_s) ** 2 for v in star_se2) / (b - 1)) / (math.sqrt(b) * se2)
    if not (math.isfinite(rho) and math.isfinite(se_rho)):
        return "N2A_INVALID", rho, se_rho
    if 3 * se_rho > 0.02:
        return "N2A_IMPRECISE", rho, se_rho
    if rho + 3 * se_rho < 0.95 or rho - 3 * se_rho > 1.05:
        return "N2A_FAIL", rho, se_rho
    return "N2A_PASS", rho, se_rho


@heavy
@pytest.mark.parametrize("series, n", N2A_CASES)
def test_heavy_n2a_resample_variance_ratio(series, n):
    """N2-a (preregistration §6): rho_hat = mean_b(se*_b^2)/se^2, SE_rho = sd_b(se*_b^2, ddof 1)/(sqrt(B) se^2), se^2 =
    F1_effective; only N2A_PASS passes, every other verdict is a STOP_FOR_USER_DECISION (not called a code error)."""
    c = _n2a_case(series, n)
    verdict, rho, se_rho = n2a_verdict(c["se2"], c["star_se2"])
    r = {"case_id": c["case_id"], "data_seed": c["data_seed"], "boot_seed": c["boot_seed"], "verdict": verdict,
         "rho_hat": rho, "SE_rho": se_rho}
    print(json.dumps({"N2-a": r}))
    if verdict != "N2A_PASS":
        pytest.fail(f"{STOP_FOR_USER}: N2-a {json.dumps(r)}")


def test_n2a_verdict_order():
    """The N2-a verdict order on hand-made inputs (light, no heavy computation)."""
    assert n2a_verdict(0.0, [1.0, 2.0])[0] == "N2A_UNDEFINED_DENOMINATOR"
    assert n2a_verdict(1.0, [1.0, math.nan])[0] == "N2A_INVALID"
    assert n2a_verdict(1.0, [0.0, 2.0])[0] == "N2A_IMPRECISE"                  # 3 SE_rho = 3 sqrt(2)/sqrt(2) > 0.02
    assert n2a_verdict(1.0, [0.8] * 1000)[0] == "N2A_FAIL"
    assert n2a_verdict(1.0, [1.0] * 1000)[0] == "N2A_PASS"
    assert n2a_verdict(1.0, [1.0, 1.0001] * 500)[0] == "N2A_PASS"


@functools.lru_cache(maxsize=None)
def _n2c_run(n):
    """N2-c at one n: R = 2,000 iid Normal P0 series ("N2c", n<n>, rep, data), S1 with B = 999 ("..., boot"), mean_block
    20 and V0's delta_hat at theta 0.7; the rejection counts for p_hi (PD-1 primary) and p_lo (report only) and the T
    of every non-SD replication (an SD replication has no se, so no T: counted)."""
    rej_lo = rej_hi = sd_reps = 0
    t_obs = []
    for rep in range(N2C_R):
        r = fd.p0_daily_returns(n, fd.explicit_seed(fd.n2c_seed_parts(n, rep, "data")), fd.CORE_THETA)
        delta = futility_delta(fd.CORE_THETA, r)
        s1 = fd.s1_pvalue(r, delta, fd.MEAN_BLOCK, N2C_B, fd.explicit_seed(fd.n2c_seed_parts(n, rep, "boot")))
        rej_lo += s1.p_lo <= fd.PRIMARY_ALPHA
        rej_hi += s1.p_hi <= fd.PRIMARY_ALPHA
        if s1.se is None:
            sd_reps += 1
        else:
            t_obs.append((mean(r) - delta) / s1.se)
    return {"n": n, "rejections_p_lo": rej_lo, "rejections_p_hi": rej_hi, "t": tuple(t_obs), "sd": sd_reps}


def n2c_bounds(alpha=fd.PRIMARY_ALPHA, reps=N2C_R):
    """alpha -/+ 3 sqrt(alpha (1 - alpha) / R), unrounded: [0.035379810..., 0.064620190...] at R = 2,000."""
    half = 3 * math.sqrt(alpha * (1 - alpha) / reps)
    return alpha - half, alpha + half


def test_n2c_bounds_and_pass_set():
    """The judged bounds are the formula's (unrounded). Preregistration §6:358 prints them as [0.035379810...,
    0.064620190...], 1.5e-9 off the formula's 0.0353798084... / 0.0646201915...; the pass set k in 71..129 of k/2000
    (§6:359) is the same for both, so only the formula is used."""
    lo, hi = n2c_bounds()
    assert (lo, hi) == (0.05 - 3 * math.sqrt(0.05 * 0.95 / 2000), 0.05 + 3 * math.sqrt(0.05 * 0.95 / 2000))
    assert f"{lo:.10f}" == "0.0353798085" and f"{hi:.10f}" == "0.0646201915"
    assert [k for k in range(N2C_R + 1) if lo <= k / N2C_R <= hi] == list(range(71, 130))   # preregistration §6


@heavy
@pytest.mark.parametrize("n", N2C_NS)
def test_heavy_n2c_s1_null_rejection_rate(n):
    """N2-c (preregistration §6): per n, the S1 rejection rate of R = 2,000 P0 replications, rejection = PD-1's
    primary p_hi <= 0.05 (WO:202), lies in the unrounded alpha -/+ 3 sqrt(alpha (1 - alpha)/R), i.e. k in 71..129 of
    2,000 (§6:359); outside is a STOP_FOR_USER_DECISION. p_lo (PD-2) is reported only. §6:358 prints the bounds as
    [0.035379810..., 0.064620190...], 1.5e-9 off the formula's values; the pass set is the same (see
    test_n2c_bounds_and_pass_set), the formula is used."""
    run = _n2c_run(n)
    lo, hi = n2c_bounds()
    k = run["rejections_p_hi"]
    ok = lo <= k / N2C_R <= hi
    assert ok == (71 <= k <= 129)                                             # the formula and the §6 pass set agree
    r = {"n": n, "k_p_hi": k, "rate_p_hi": k / N2C_R, "bounds": [lo, hi], "verdict": "PASS" if ok else STOP_FOR_USER,
         "report_only": {"k_p_lo": run["rejections_p_lo"], "rate_p_lo": run["rejections_p_lo"] / N2C_R,
                         "sd_replications": run["sd"]}}
    print(json.dumps({"N2-c": r}))
    if not ok:
        pytest.fail(f"{STOP_FOR_USER}: N2-c {json.dumps(r)}")


@heavy
def test_heavy_n2b_report_only():
    """N2-b (preregistration §6, REPORT_ONLY_DIAGNOSTIC): per N2-a case the coefficient of variation of se* and the
    T* quantiles {0.01, 0.05, 0.5, 0.95, 0.99}; the same quantiles of the N2-c replications' T. No range, no verdict:
    NaN / Inf are reported as they are. Reuses the N2-a / N2-c computations of this session (lru_cache)."""
    report = {"N2-a": {}, "N2-c": {}}
    for series, n in N2A_CASES:
        c = _n2a_case(series, n)
        defined = [v for v in c["star_se2"] if v == v]                        # J_b >= 2 (se* defined)
        se_star = [math.sqrt(v) for v in defined if math.isfinite(v)]
        mu = sum(se_star) / len(se_star) if se_star else None
        sdv = math.sqrt(sum((v - mu) ** 2 for v in se_star) / (len(se_star) - 1)) if mu is not None and \
            len(se_star) > 1 else None
        cv = sdv / mu if sdv is not None and mu else "UNDEFINED"
        excluded = {"rd": c["rd"]} if not c["sd"] else {"sd_all_resamples": N2A_B}
        report["N2-a"][c["case_id"]] = {
            "cv_se_star": cv, "cv_n_used": len(se_star), "cv_n_undefined_j_b_lt_2": N2A_B - len(defined),
            "cv_n_non_finite": len(defined) - len(se_star),
            "t_star": n2b_report_values(c["t_star"], excluded)}
    for n in N2C_NS:
        run = _n2c_run(n)
        report["N2-c"][f"n{n}"] = n2b_report_values(run["t"], {"sd_replications": run["sd"]})
    print(json.dumps({"N2-b": report}, allow_nan=True))


def test_n2b_report_values_counts_and_undefined():
    """Light: NaN / Inf are counted and kept out of the quantiles, the caller's exclusions are listed, the quantiles
    are stats.percentile of the finite values, no finite value gives UNDEFINED; no verdict."""
    r = n2b_report_values([3.0, math.nan, 1.0, math.inf, 2.0, -math.inf], {"rd": 4})
    assert (r["n_total"], r["n_nan"], r["n_pos_inf"], r["n_neg_inf"], r["n_valid"]) == (10, 1, 1, 1, 3)
    assert r["excluded"] == {"rd": 4}
    assert r["quantiles"] == {str(q): percentile([1.0, 2.0, 3.0], q) for q in N2B_QUANTILES}
    assert r["quantiles"]["0.5"] == 2.0
    u = n2b_report_values([math.nan, math.inf], {"sd_replications": 0})
    assert u["quantiles"] == "UNDEFINED" and u["n_valid"] == 0
    assert n2b_report_values([])["quantiles"] == "UNDEFINED"
    assert "verdict" not in r and "pass" not in json.dumps(r).lower()


@heavy
def test_heavy_t12_dc14_e_cal_reproduction():
    """T12 / DC14 (WO:265, preregistration §2): montecarlo.resolve with the MC-V06 seed rule (seed 20261012,
    normal_M60_+0p7, truth_years 400, default costs) must give exactly the preregistered e_cal and SR_ach (the
    values read from summary.json, compared as floats bit for bit); otherwise STOP. MC-V06 code is only called."""
    from moneylab.research.v06.montecarlo import mc_v06_scenarios, resolve
    scenario = [s for s in mc_v06_scenarios() if s.name == fd.MCV06_INPUTS["scenario"]]
    assert len(scenario) == 1, "STOP: MC-V06 scenario normal_M60_+0p7 not found exactly once"
    _, _, calib = resolve(scenario[0], Costs(), 400, fd.MCV06_INPUTS["seed"])
    got = {"edge_annual": calib.get("edge_annual"), "achieved_sharpe": calib.get("achieved_sharpe")}
    want = {"edge_annual": fd.E_CAL, "achieved_sharpe": fd.MCV06_INPUTS["sr_ach"]}
    print(json.dumps({"T12": {"got": got, "want": want}}))
    assert got == want, f"STOP: DC14 reproduction differs {got} != {want}"


# --- G3b-2: seed policy S-A and run_spec ---------------------------------------------------------------------

def test_explicit_seed_n1c_string():
    parts = fd.n1c_seed_parts("ar1", 365, 20.0)
    assert parts == ("FUTDIAG-TEST", "N1c", "ar1-n365-b20")
    assert fd.explicit_seed(parts) == derived_seed(20261029, "FUTDIAG-TEST", "N1c", "ar1-n365-b20")
    assert fd.n1c_seed_parts("iid", 365, 1.0)[2] == "iid-n365-b1"


def test_explicit_seed_n2a_data_boot_separated():
    data = fd.n2a_seed_parts("data", "zero_inflated", 2227)
    boot = fd.n2a_seed_parts("boot", "zero_inflated", 2227)
    assert data == ("FUTDIAG-TEST", "N2a-data", "zero_inflated-n2227-b20")
    assert boot == ("FUTDIAG-TEST", "N2a-boot", "zero_inflated-n2227-b20")
    assert fd.explicit_seed(data) != fd.explicit_seed(boot)
    with pytest.raises(fd.StopImplementation):
        fd.n2a_seed_parts("both", "iid", 365)


def test_explicit_seed_e1_calib_keeps_theta_utf8():
    assert fd.E1_CALIB_SEED_PARTS == ("FUTDIAG", "E1-θ0.7", "calib")
    assert fd.E1_CALIB_SEED_PARTS[1].encode("utf-8") == b"E1-\xce\xb80.7"
    assert fd.explicit_seed(fd.E1_CALIB_SEED_PARTS) == derived_seed(20261029, "FUTDIAG", "E1-θ0.7", "calib")
    assert fd.explicit_seed(fd.E1_CALIB_SEED_PARTS) != fd.explicit_seed(("FUTDIAG", "E1-theta0.7", "calib"))


def test_explicit_seed_v4_eval():
    assert fd.V4_EVAL_SEED_PARTS == ("FUTDIAG", "v4eval")
    assert fd.explicit_seed(fd.V4_EVAL_SEED_PARTS) == derived_seed(20261029, "FUTDIAG", "v4eval")


def test_explicit_seed_n2c_rep_length_role():
    a = fd.n2c_seed_parts(365, 0, "data")
    assert a == ("FUTDIAG-TEST", "N2c", "n365", "0", "data")
    seeds = {fd.explicit_seed(fd.n2c_seed_parts(n, rep, role))
             for n in (365, 2227) for rep in range(50) for role in fd.N2C_ROLES}
    assert len(seeds) == 2 * 50 * 2                                           # every (n, rep, role) distinct
    for bad in ((365, 0, "path"), (365, -1, "data"), (365, True, "data"), ("365", 0, "data")):
        with pytest.raises(fd.StopImplementation):
            fd.n2c_seed_parts(*bad)


def test_case_format_validation():
    ids = {fd.case_id(s, n, b) for s in fd.CASE_SERIES for n in (365, 2227) for b in (1.0, 20.0, 60)}
    assert len(ids) == 3 * 2 * 3                                              # no two cases share an id
    for bad in (("normal", 365, 20.0), ("iid", 365.0, 20.0), ("iid", 0, 20.0), ("iid", 365, 20.5),
                ("iid", 365, 0.5), ("iid", True, 20.0)):
        with pytest.raises(fd.StopImplementation):
            fd.case_id(*bad)


def test_general_dc10_six_parts():
    p = fd.seed_path("FUTDIAG", "E1-theta0.7", 12, "f36", "b60")
    assert p == ("FUTDIAG", "E1-theta0.7", "12", "f36", "b60") and len(p) == 5
    assert fd.seed_for(p) == derived_seed(20261029, "FUTDIAG", "E1-theta0.7", "12", "f36", "b60")


def test_seed_parts_reject_pipe_and_non_str():
    with pytest.raises(fd.StopImplementation):
        fd.seed_path("FUTDIAG", "E1|theta0.7", 0, "f12", "b20")
    with pytest.raises(fd.StopImplementation):
        fd.explicit_seed(("FUTDIAG-TEST", "N1c", "a|b"))
    with pytest.raises(fd.StopImplementation):
        fd.explicit_seed(("FUTDIAG-TEST", "N2c", 365))                        # non-str part
    with pytest.raises(fd.StopImplementation):
        fd.seed_path("FUTDIAG", "E1-theta0.7", 1.5, "f12", "b20")             # rep must be int or str
    with pytest.raises(fd.StopImplementation):
        fd.seed_for(("FUTDIAG", "c", 3, "w", "r"))                             # non-str rep in a raw tuple
    with pytest.raises(fd.StopImplementation):
        fd.explicit_seed(("FUTVAL", "x"))
    with pytest.raises(fd.StopImplementation):
        fd.explicit_seed(())


def test_seed_independent_of_worker_count():
    from concurrent.futures import ProcessPoolExecutor
    paths = [fd.seed_path("FUTDIAG", "E1-theta0.7", i, w, "b20") for i in range(20) for w in fd.WINDOWS]
    serial = [fd.seed_for(p) for p in paths]
    for workers in (1, 2):
        with ProcessPoolExecutor(max_workers=workers) as pool:
            assert list(pool.map(fd.seed_for, paths)) == serial


def _spec(**over):
    kw = dict(mode="core", code_sha="a" * 40, code_tree="b" * 40, config_sha256="c" * 64, prereg_sha256="d" * 64,
              cells=list(fd.CORE_CELLS), windows=list(fd.WINDOWS), rules=list(fd.RULES), reps=10_000,
              bootstrap=1999, unit_size=500)
    kw.update(over)
    return fd.build_run_spec(**kw)


def test_run_spec_required_fields_and_validation():
    spec = _spec()
    assert tuple(sorted(spec)) == tuple(sorted(fd.RUN_SPEC_FIELDS))
    assert spec["base_seed"] == 20261029 and spec["seed_policy"]["rule"] == "S-A"
    for k in fd.RUN_SPEC_FIELDS:
        broken = {key: v for key, v in spec.items() if key != k}
        with pytest.raises(fd.StopImplementation):
            fd.validate_run_spec(broken)
    for over in ({"mode": "smoke"}, {"code_sha": "A" * 40}, {"config_sha256": "c" * 63}, {"reps": 0},
                 {"bootstrap": True}, {"unit_size": 2.5}, {"cells": ["E2-theta0.7"]}, {"windows": ["f12", "f12"]},
                 {"rules": []}):
        with pytest.raises(fd.StopImplementation):
            _spec(**over)
    explo = _spec(mode="exploratory", cells=["E2-theta0.7"], reps=5000)
    assert explo["cells"] == ["E2-theta0.7"]


def test_run_spec_deterministic_bytes():
    a, b = _spec(), _spec()
    assert fd.run_spec_bytes(a) == fd.run_spec_bytes(b)
    raw = fd.run_spec_bytes(a)
    expected = (json.dumps(a, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
                + "\n").encode("utf-8")
    assert raw == expected                                                    # exact canonical form
    reordered = dict(reversed(list(a.items())))
    assert fd.run_spec_bytes(reordered) == raw                                # key order does not matter
    assert "E1-θ0.7".encode("utf-8") in raw                              # literal theta kept (ensure_ascii off)


def test_run_spec_excludes_runtime_and_results():
    spec = _spec()
    assert not set(fd.RUN_SPEC_FORBIDDEN) & set(spec)
    for k in fd.RUN_SPEC_FORBIDDEN:
        with pytest.raises(fd.StopImplementation):
            fd.validate_run_spec({**spec, k: 1})


# --- G3b-3: replication engine (ERRATA-002) ----------------------------------------------------------------------

E1 = fd.e1_cell(0.73, 0.70 / math.sqrt(365))      # stand-in edge / sigma_pop: the real ones come from G5 calibration
P0 = fd.p0_cell()
B = 19
NS = "FUTDIAG-TEST"


def _seeds(cell, rep, windows=fd.WINDOWS):
    return {k: fd.seed_for(p) for k, p in fd.rep_seed_paths(NS, cell.name, rep, windows).items()}


def test_engine_window_bounds_and_days():
    assert fd.window_bounds() == {"conf": (122, 2349), "f12": (3323, 3688), "f24": (3323, 4054),
                                  "f36": (3323, 4419)}
    assert fd.path_days() == Layout().total_days(SimulationCalendar())
    assert all(g1 <= fd.path_days() for _, g1 in fd.window_bounds().values())


def test_p0_iid_normal_cost_free(monkeypatch):
    """ERRATA-002 P0_COST / AC-1: generated values used as is; no strategy, positions or cost."""
    def boom(*a, **k):
        raise AssertionError("P0 must not use strategy / positions / costs")
    for name in ("segment_returns", "segment_market_positions", "window_e0_returns", "signals", "make_path"):
        monkeypatch.setattr(fd, name, boom)
    seed = _seeds(P0, 0)["path"]
    rets = fd.cell_window_returns(P0, seed)
    rng = random.Random(seed)
    sd_ = 0.70 / math.sqrt(365)
    mu = 0.7 * sd_ / math.sqrt(365)
    daily = [mu + sd_ * rng.gauss(0.0, 1.0) for _ in range(fd.path_days())]
    for w, (g0, g1) in fd.window_bounds().items():
        assert rets[w] == daily[g0:g1]
    assert fd.P0_DAILY_SD == sd_ and mu / sd_ * math.sqrt(365) == pytest.approx(0.7, rel=1e-15)   # analytic SR = theta


def test_e1_uses_m60_e0_default_costs():
    seed = _seeds(E1, 1)["path"]
    rets = fd.cell_window_returns(E1, seed, ("f12", "f36"))
    path = make_path(DGP(garch_alpha=0.0, garch_beta=0.0, t_df=None, edge_kind="momentum", edge_lookback=60,
                         edge_annual=0.73), fd.path_days(), seed)
    sig = strategy_signals(path)["M60"]
    for w in ("f12", "f36"):
        g0, g1 = fd.window_bounds()[w]
        assert rets[w] == fd.window_e0_returns(path, sig, g0, g1, Costs().log_costs()["E0"])
        assert len(rets[w]) == g1 - g0


def test_one_path_per_rep_shared_by_windows(monkeypatch):
    calls = []
    real = fd.p0_daily_returns
    monkeypatch.setattr(fd, "p0_daily_returns", lambda *a: calls.append(a) or real(*a))
    recs = fd.run_reps(P0, [0, 1], NS, B, ("f12", "f24"))
    assert [(c[1]) for c in calls] == [_seeds(P0, 0)["path"], _seeds(P0, 1)["path"]]   # once per rep, path seed
    f12 = fd.cell_window_returns(P0, _seeds(P0, 0)["path"])
    assert f12["f24"][:365] == f12["f12"]                                         # nested windows of one path
    assert [(r["rep"], r["window"]) for r in recs] == [(0, "f12"), (0, "f24"), (1, "f12"), (1, "f24")]


def test_errata002_seed_strings():
    p = fd.rep_seed_paths("FUTDIAG", "E1-theta0.7", 5, ("conf", "f12"))
    assert p == {"path": ("FUTDIAG", "E1-theta0.7", "5", "all", "path"),
                 "conf/b20": ("FUTDIAG", "E1-theta0.7", "5", "conf", "b20"),
                 "conf/b60": ("FUTDIAG", "E1-theta0.7", "5", "conf", "b60"),
                 "f12/b20": ("FUTDIAG", "E1-theta0.7", "5", "f12", "b20"),
                 "f12/b60": ("FUTDIAG", "E1-theta0.7", "5", "f12", "b60")}
    assert fd.seed_for(p["path"]) == derived_seed(20261029, "FUTDIAG", "E1-theta0.7", "5", "all", "path")
    assert fd.rep_seed_paths("FUTDIAG-PILOT", "P0-theta0.7", 0, ("f36",))["f36/b60"] == \
        ("FUTDIAG-PILOT", "P0-theta0.7", "0", "f36", "b60")
    assert fd.sigma_seed_path(1999) == ("FUTDIAG-SIGMA", "E1-ecal", "1999", "all", "path")
    assert fd.E1_CALIB_SEED_PARTS == ("FUTDIAG", "E1-θ0.7", "calib")             # unchanged explicit tuples
    assert fd.V4_EVAL_SEED_PARTS == ("FUTDIAG", "v4eval")
    gs = fd.seed_policy()["general_strings"]
    assert gs["path"][3:] == ["all", "path"] and gs["sigma"] == ["FUTDIAG-SIGMA", "E1-ecal", "<rep>", "all", "path"]
    assert gs["shared_b20"] == ["V0", "V0d", "S1"] and gs["separate_b60"] == ["V0b60"]
    assert _spec()["seed_policy"] == fd.seed_policy()


def test_b20_shared_and_b60_separate():
    """AC-5: V0, V0d, S1 from the b20 seed; V0b60 from the b60 seed."""
    s = _seeds(E1, 2, ("f12",))
    r = fd.cell_window_returns(E1, s["path"], ("f12",))["f12"]
    rec = fd.window_record(E1, 2, "f12", r, s["f12/b20"], s["f12/b60"], B)
    v0 = fd.v0_family(r, 0.7, 20.0, B, s["f12/b20"], sigma_pop=E1.sigma_pop)
    s1 = fd.s1_pvalue(r, v0.delta_hat, 20.0, B, s["f12/b20"])
    v60 = fd.v0_family(r, 0.7, 60.0, B, s["f12/b60"])
    assert rec["variants"]["V0"]["p"] == v0.p_v0 and rec["variants"]["V0d"]["p"] == v0.p_v0d
    assert (rec["variants"]["S1"]["p_hi"], rec["variants"]["S1"]["p_lo"]) == (s1.p_hi, s1.p_lo)
    assert rec["variants"]["V0b60"]["p"] == v60.p_v0
    assert s["f12/b20"] != s["f12/b60"]
    boot20 = bootstrap_means([r], mean_block=20.0, resamples=B, seed=s["f12/b20"])[0]
    pre = fd._Prefix(r)
    assert [fd.resample_mean_and_se2(pre, len(r), b)[0]
            for b in fd.resample_blocks(len(r), 20.0, B, s["f12/b20"])] == boot20       # one block sequence


def test_se_fields_and_boot_sd():
    """AC-2 / AC-3: S1 se = sqrt(F1_effective); V0 family se null NOT_APPLICABLE; boot_sd = sd (B - 1)."""
    s = _seeds(P0, 3, ("f12",))
    r = fd.cell_window_returns(P0, s["path"], ("f12",))["f12"]
    rec = fd.window_record(P0, 3, "f12", r, s["f12/b20"], s["f12/b60"], B)
    for v in ("V0", "V0d", "V0b60"):
        assert rec["variants"][v]["se"] is None and rec["variants"][v]["se_reason"] == fd.NOT_APPLICABLE
    se = math.sqrt(fd.f1_effective(fd.f1_variance(r, 20.0), fd.variance_scale(r)))
    assert rec["variants"]["S1"]["se"] == se and rec["variants"]["S1"]["se_reason"] is None
    for rule, mb in (("b20", 20.0), ("b60", 60.0)):
        boot = bootstrap_means([r], mean_block=mb, resamples=B, seed=s[f"f12/{rule}"])[0]
        mb_ = sum(boot) / B
        assert rec[f"boot_sd_{rule}"] == math.sqrt(sum((x - mb_) ** 2 for x in boot) / (B - 1))
    assert rec["sd"] is False
    assert rec["annual_sharpe"] == fd.annual_sharpe(r) and rec["m"] == mean(r)
    assert rec["delta_true"] == pytest.approx(0.7 * fd.P0_DAILY_SD / math.sqrt(365), rel=1e-15)


def test_sd_record_keeps_dc41():
    """SD sample: p_S1 = 1, S1 se = 0 recorded, sd flag set; V0 family stays NOT_APPLICABLE (not a degeneracy)."""
    rec = fd.window_record(P0, 0, "f12", [0.001] * 365, 11, 12, B)
    s1 = rec["variants"]["S1"]
    assert rec["sd"] is True and (s1["p_hi"], s1["p_lo"], s1["d"], s1["se"]) == (1.0, 1.0, 0, 0.0)
    assert all(rec["variants"][v]["se_reason"] == fd.NOT_APPLICABLE for v in ("V0", "V0d", "V0b60"))


def test_record_fields_exact():
    rec = fd.run_reps(P0, [0], NS, B, ("f12",))[0]
    assert tuple(rec) == fd.RECORD_FIELDS
    assert tuple(rec["variants"]) == fd.VARIANTS
    assert tuple(rec["variants"]["S1"]) == fd.S1_FIELDS
    assert all(tuple(rec["variants"][v]) == fd.V0_FAMILY_FIELDS for v in ("V0", "V0d", "V0b60"))
    assert (rec["cell"], rec["rep"], rec["window"]) == ("P0-theta0.7", 0, "f12")
    json.loads(fd.records_bytes([rec]))                                        # finite, canonical JSON


def test_engine_determinism_and_workers():
    """Same seeds -> same bytes; worker 1 and 2 give identical output."""
    for cell in (P0, E1):
        a = fd.records_bytes(fd.run_reps(cell, [0, 1, 2], NS, B, ("f12",), workers=1))
        b = fd.records_bytes(fd.run_reps(cell, [0, 1, 2], NS, B, ("f12",), workers=1))
        c = fd.records_bytes(fd.run_reps(cell, [0, 1, 2], NS, B, ("f12",), workers=2))
        assert a == b == c
    assert fd.records_bytes(fd.run_reps(P0, [0], NS, B, ("f12",))) != \
        fd.records_bytes(fd.run_reps(P0, [0], "FUTDIAG-PILOT", B, ("f12",)))   # namespace changes the stream


def test_engine_all_windows_one_rep():
    recs = fd.run_reps(E1, [0], NS, B)
    assert [r["window"] for r in recs] == list(fd.WINDOWS)
    assert len({r["m"] for r in recs}) == 4                                    # distinct windows, one path


def test_engine_input_validation():
    bad_runs = [dict(cell=fd.CellSpec("E2-theta0.7", 0.7, 0.1, 0.03)), dict(cell=fd.CellSpec("E1-theta0.7", 0.7)),
                dict(cell=fd.CellSpec("E1-theta0.7", 0.3, 0.7, 0.03)),
                dict(cell=fd.CellSpec("P0-theta0.7", 0.7, None, 0.03)), dict(namespace="FUTDIAG-X"),
                dict(namespace="FUTVAL"), dict(windows=("f12", "conf")), dict(windows=()), dict(bootstrap=0),
                dict(reps=[1, 0]), dict(reps=[0, 0]), dict(reps=[-1]), dict(workers=0)]
    for over in bad_runs:
        kw = dict(cell=P0, reps=[0], namespace=NS, bootstrap=B, windows=("f12",), workers=1)
        kw.update(over)
        with pytest.raises(fd.StopImplementation):
            fd.run_reps(**kw)


# --- G3b-4: storage, resume, integrity (TEST_FIXTURE runs in tmp_path only) ------------------------------------

def _store_spec(**over):
    kw = dict(cells=list(fd.CORE_CELLS), windows=["f12"], reps=5, bootstrap=9, unit_size=2)
    kw.update(over)
    return _spec(**kw)


def _inputs(spec, edge=0.73, namespace=NS, provenance=None):
    cells = [fd.e1_cell(edge, E1.sigma_pop) if n.startswith("E1") else P0 for n in spec["cells"]]
    return fd.build_run_inputs(spec, cells, namespace, provenance or {"kind": fd.TEST_FIXTURE})


def _files(run_dir):
    """Deterministic files: everything except execution.json and leftover *.tmp."""
    return {p.relative_to(run_dir).as_posix(): p.read_bytes() for p in sorted(run_dir.rglob("*"))
            if p.is_file() and p.name != fd.EXECUTION_FILE and not p.name.endswith(".tmp")}


@pytest.fixture(scope="module")
def ref(tmp_path_factory):
    spec = _store_spec()
    inputs = _inputs(spec)
    d = tmp_path_factory.mktemp("ref") / "run"
    out = fd.run_units(d, spec, inputs, workers=1)
    return d, spec, inputs, _files(d), out


def _copy(ref, tmp_path, name="run"):
    d = tmp_path / name
    shutil.copytree(ref[0], d)
    return d


def _drop_final(d):
    (d / fd.MANIFEST_FILE).unlink()
    (d / fd.SUMS_FILE).unlink()


def test_unit_ranges_and_paths(tmp_path):
    assert fd.unit_ranges(5, 2) == [(0, 0, 2), (1, 2, 4), (2, 4, 5)]
    assert fd.unit_ranges(4, 4) == [(0, 0, 4)]
    for bad in ((0, 2), (5, 0), (5, True)):
        with pytest.raises(fd.StopImplementation):
            fd.unit_ranges(*bad)
    j, i = fd.unit_paths(tmp_path, "P0-theta0.7", 3)
    assert j == tmp_path / "units" / "P0-theta0.7" / "u00003.jsonl" and i.name == "u00003.index.json"


def test_run_inputs_contract():
    spec = _store_spec()
    inp = _inputs(spec)
    assert tuple(sorted(inp)) == tuple(sorted(fd.RUN_INPUTS_FIELDS))
    assert inp["python"] == platform.python_version() and inp["namespace"] == NS
    assert inp["cells"]["E1-theta0.7"] == {"theta": 0.7, "edge_annual": 0.73, "sigma_pop": E1.sigma_pop}
    assert inp["cells"]["P0-theta0.7"]["sigma_pop"] == fd.P0_DAILY_SD and inp["cells"]["P0-theta0.7"]["edge_annual"] is None
    assert inp["futility_diag_source"]["sha256"] == hashlib.sha256(FsPath(fd.__file__).read_bytes()).hexdigest()
    assert inp["mcv06_source_identity"] == source_identity()
    with pytest.raises(fd.StopImplementation):
        _inputs(spec, namespace="FUTDIAG")                                    # TEST_FIXTURE only in FUTDIAG-TEST
    with pytest.raises(fd.StopImplementation):
        _inputs(spec, provenance={"kind": "CALIBRATION"})                     # real provenance: G3b-5
    with pytest.raises(fd.StopImplementation):
        _inputs(_store_spec(mode="pilot"), namespace="FUTDIAG")               # (pilot, FUTDIAG) not allowed
    with pytest.raises(fd.StopImplementation):
        fd.build_run_inputs(spec, [P0, E1], NS, {"kind": fd.TEST_FIXTURE})    # cells out of run_spec order
    with pytest.raises(fd.StopImplementation):
        fd.build_run_inputs(spec, [fd.CellSpec("E1-theta0.7", 0.7), P0], NS, {"kind": fd.TEST_FIXTURE})
    with pytest.raises(fd.StopImplementation):
        fd.build_manifest(spec, {**inp, "calibration_provenance": {"kind": "CALIBRATION"}}, [], "0", "0")


def _axes(**over):
    """verify_run's separate axes for a fully written ref copy (G3b-5-1), with overrides."""
    out = {"unit_status": "COMPLETE", "execution": "RECORDED", "sessions": 1, "time_accounting": "COMPLETE",
           "g6": "ABSENT", "missing_units": [], "tmp": []}
    out.update(over)
    return out


def test_r1_complete_run_and_verify(ref):
    d, spec, inputs, files, out = ref
    assert out == {"init": "created", "computed": 6, "reused": 0, "index_completed": 0, "tmp": []}
    assert fd.verify_run(d) == {"status": "COMPLETE", "units": 6, **_axes()}
    assert files[fd.RUN_SPEC_FILE] == fd.run_spec_bytes(spec)
    assert files[fd.RUN_INPUTS_FILE] == fd.canonical_bytes(inputs)
    sums = files[fd.SUMS_FILE].decode().splitlines()
    listed = [line.split("  ", 1)[1] for line in sums]
    assert listed == sorted(set(files) - {fd.SUMS_FILE})                      # no execution.json, no SHA256SUMS
    man = json.loads(files[fd.MANIFEST_FILE])
    assert man["fixture"] == fd.TEST_FIXTURE and man["pending_for_research_run"] == list(fd.MANIFEST_PENDING)
    assert [u["unit"] for u in man["units"]] == [0, 1, 2, 0, 1, 2] and man["evidence"] == fd.EVIDENCE
    ex = json.loads((d / fd.EXECUTION_FILE).read_bytes())
    assert [s["workers"] for s in ex["sessions"]] == [1]
    p0_u1 = files["units/P0-theta0.7/u00001.jsonl"]
    assert p0_u1 == fd.records_bytes(fd.run_reps(P0, range(2, 4), NS, 9, ["f12"]))   # G3b-3 records unchanged


def test_r1_rerun_reuses_everything(ref, tmp_path):
    d = _copy(ref, tmp_path)
    out = fd.run_units(d, ref[1], ref[2])
    assert (out["reused"], out["computed"], out["init"]) == (6, 0, "resumed") and _files(d) == ref[3]
    assert len(json.loads((d / fd.EXECUTION_FILE).read_bytes())["sessions"]) == 2


def test_r2_resume_after_interruption(ref, tmp_path, monkeypatch):
    d = tmp_path / "run"
    real, calls = fd.run_reps_timed, []

    def flaky(*a, **k):
        calls.append(1)
        if len(calls) == 3:
            raise KeyboardInterrupt
        return real(*a, **k)
    monkeypatch.setattr(fd, "run_reps_timed", flaky)
    with pytest.raises(KeyboardInterrupt):
        fd.run_units(d, ref[1], ref[2])
    monkeypatch.setattr(fd, "run_reps_timed", real)
    status = fd.verify_run(d)
    assert status["status"] == "INCOMPLETE" and len(status["missing_units"]) == 4
    out = fd.run_units(d, ref[1], ref[2])
    assert (out["reused"], out["computed"]) == (2, 4) and _files(d) == ref[3]


def test_r3_tmp_from_interrupted_write_is_reported_not_deleted(ref, tmp_path):
    d = tmp_path / "run"
    fd.init_run(d, ref[1], ref[2])
    orphan = d / "units" / "P0-theta0.7" / ".u00002.jsonl.x1y2.tmp"
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b"partial")
    out = fd.run_units(d, ref[1], ref[2])
    assert out["tmp"] == ["units/P0-theta0.7/.u00002.jsonl.x1y2.tmp"] and orphan.read_bytes() == b"partial"
    assert _files(d) == ref[3] and fd.verify_run(d)["tmp"] == out["tmp"]


def test_r4_jsonl_without_index_completed_only_if_identical(ref, tmp_path):
    d = _copy(ref, tmp_path)
    _drop_final(d)
    fd.unit_paths(d, "E1-theta0.7", 1)[1].unlink()
    out = fd.run_units(d, ref[1], ref[2])
    assert (out["index_completed"], out["reused"], out["computed"]) == (1, 5, 0) and _files(d) == ref[3]

    d2 = _copy(ref, tmp_path, "run2")
    _drop_final(d2)
    jsonl, index = fd.unit_paths(d2, "P0-theta0.7", 0)
    index.unlink()
    bad = jsonl.read_bytes().replace(b'"rep":1', b'"rep":7', 1)
    jsonl.write_bytes(bad)
    with pytest.raises(fd.StopImplementation, match="differs from the recomputed"):
        fd.run_units(d2, ref[1], ref[2])
    assert jsonl.read_bytes() == bad and not index.exists()                   # never overwritten


def test_r5_units_complete_manifest_missing(ref, tmp_path):
    d = _copy(ref, tmp_path)
    _drop_final(d)
    assert fd.verify_run(d) == {"status": "INCOMPLETE", **_axes()}
    out = fd.run_units(d, ref[1], ref[2])
    assert (out["reused"], out["computed"]) == (6, 0) and _files(d) == ref[3]


def test_r6_workers_do_not_change_bytes(ref, tmp_path):
    d = tmp_path / "run"
    fd.run_units(d, ref[1], ref[2], workers=2)
    assert _files(d) == ref[3]
    d2 = _copy(ref, tmp_path, "run2")
    _drop_final(d2)
    for p in fd.unit_paths(d2, "E1-theta0.7", 2):
        p.unlink()
    fd.run_units(d2, ref[1], ref[2], workers=2)                               # resume with another worker count
    assert _files(d2) == ref[3]
    assert [s["workers"] for s in json.loads((d2 / fd.EXECUTION_FILE).read_bytes())["sessions"]] == [1, 2]


def test_r7_different_run_spec_or_inputs_stops(ref, tmp_path, monkeypatch):
    d = _copy(ref, tmp_path)
    with pytest.raises(fd.StopImplementation, match="run_spec differs"):
        fd.run_units(d, _store_spec(bootstrap=19), _inputs(_store_spec(bootstrap=19)))
    with pytest.raises(fd.StopImplementation, match="run_inputs differs"):
        fd.run_units(d, ref[1], _inputs(ref[1], edge=0.74))
    import platform
    monkeypatch.setattr(platform, "python_version", lambda: "3.0.0")
    with pytest.raises(fd.StopImplementation, match="run_inputs differs"):
        fd.run_units(d, ref[1], _inputs(ref[1]))
    assert _files(d) == ref[3]


def test_r8_tampered_jsonl_stops_without_repair(ref, tmp_path):
    d = _copy(ref, tmp_path)
    jsonl = fd.unit_paths(d, "E1-theta0.7", 0)[0]
    bad = jsonl.read_bytes().replace(b'"sd":false', b'"sd":true', 1)
    jsonl.write_bytes(bad)
    for call in (lambda: fd.run_units(d, ref[1], ref[2]), lambda: fd.verify_run(d)):
        with pytest.raises(fd.StopImplementation, match="index does not match"):
            call()
    assert jsonl.read_bytes() == bad


def test_r9_tampered_or_orphan_index_stops(ref, tmp_path):
    d = _copy(ref, tmp_path)
    index = fd.unit_paths(d, "P0-theta0.7", 2)[1]
    index.write_bytes(index.read_bytes().replace(b'"rep_stop":5', b'"rep_stop":6'))
    for call in (lambda: fd.run_units(d, ref[1], ref[2]), lambda: fd.verify_run(d)):
        with pytest.raises(fd.StopImplementation, match="index does not match"):
            call()
    d2 = _copy(ref, tmp_path, "run2")
    fd.unit_paths(d2, "P0-theta0.7", 1)[0].unlink()                           # index without its jsonl
    with pytest.raises(fd.StopImplementation, match="not complete"):
        fd.verify_run(d2)


def _rewrite_unit(d, cell, unit, lines):
    """Replace a unit's records and give it a self-consistent index, so only the record checks can catch it."""
    jsonl, index = fd.unit_paths(d, cell, unit)
    data = b"".join(lines)
    jsonl.write_bytes(data)
    idx = json.loads(index.read_bytes())
    idx.update(n_records=len(lines), jsonl_sha256=hashlib.sha256(data).hexdigest())
    index.write_bytes(fd.canonical_bytes(idx))


def test_r10_duplicate_reps_or_units_stop(ref, tmp_path):
    d = _copy(ref, tmp_path)
    lines = fd.unit_paths(d, "E1-theta0.7", 1)[0].read_bytes().splitlines(keepends=True)
    _rewrite_unit(d, "E1-theta0.7", 1, [*lines, lines[-1]])
    with pytest.raises(fd.StopImplementation, match="not exactly reps x windows"):
        fd.verify_run(d)
    d2 = _copy(ref, tmp_path, "run2")
    shutil.copy(fd.unit_paths(d2, "P0-theta0.7", 0)[0], d2 / "units" / "P0-theta0.7" / "u00009.jsonl")
    for call in (lambda: fd.run_units(d2, ref[1], ref[2]), lambda: fd.verify_run(d2)):
        with pytest.raises(fd.StopImplementation, match="unexpected files"):
            call()


def test_r11_missing_reps_stop_missing_units_resume(ref, tmp_path):
    d = _copy(ref, tmp_path)
    lines = fd.unit_paths(d, "P0-theta0.7", 1)[0].read_bytes().splitlines(keepends=True)
    _rewrite_unit(d, "P0-theta0.7", 1, lines[:-1])
    with pytest.raises(fd.StopImplementation, match="not exactly reps x windows"):
        fd.verify_run(d)
    d2 = _copy(ref, tmp_path, "run2")
    _drop_final(d2)
    for p in fd.unit_paths(d2, "P0-theta0.7", 1):
        p.unlink()
    assert fd.verify_run(d2)["missing_units"] == ["P0-theta0.7/u00001"]
    out = fd.run_units(d2, ref[1], ref[2])
    assert (out["computed"], out["reused"]) == (1, 5) and _files(d2) == ref[3]


def test_r12_only_tmp_files(ref, tmp_path):
    d = tmp_path / "run"
    d.mkdir()
    (d / ".run_spec.json.abc.tmp").write_bytes(b"x")
    out = fd.run_units(d, ref[1], ref[2])
    assert out["init"] == "created" and out["tmp"] == [".run_spec.json.abc.tmp"]
    assert (d / ".run_spec.json.abc.tmp").exists() and _files(d) == ref[3]


def test_manifest_with_missing_unit_and_bad_sums_stop(ref, tmp_path):
    d = _copy(ref, tmp_path)
    for p in fd.unit_paths(d, "E1-theta0.7", 0):
        p.unlink()
    with pytest.raises(fd.StopImplementation, match="is not complete"):
        fd.run_units(d, ref[1], ref[2])
    with pytest.raises(fd.StopImplementation, match="incomplete run"):
        fd.verify_run(d)
    d2 = _copy(ref, tmp_path, "run2")
    sums = d2 / fd.SUMS_FILE
    sums.write_bytes(sums.read_bytes().replace(b"run_spec.json", b"run_spec.jsonx"))
    with pytest.raises(fd.StopImplementation, match="SHA256SUMS"):
        fd.verify_run(d2)
    with pytest.raises(fd.StopImplementation, match="SHA256SUMS"):
        fd.run_units(d2, ref[1], ref[2])


def test_init_run_refuses_foreign_or_half_initialised_dirs(ref, tmp_path):
    d = tmp_path / "foreign"
    d.mkdir()
    (d / "notes.txt").write_text("x")
    with pytest.raises(fd.StopImplementation, match="no run_spec.json"):
        fd.run_units(d, ref[1], ref[2])
    d2 = tmp_path / "half"
    d2.mkdir()
    (d2 / fd.RUN_INPUTS_FILE).write_bytes(fd.canonical_bytes(ref[2]))
    with pytest.raises(fd.StopImplementation):
        fd.init_run(d2, ref[1], ref[2])
    assert sorted(p.name for p in d.iterdir()) == ["notes.txt"]                # nothing written


# --- G3b-5-1: crash window, calibration artifact, research identity (no calibration MC, no git writes) -----------

def test_crash_execution_missing_is_incomplete_then_resume(ref, tmp_path):
    d = _copy(ref, tmp_path)
    (d / fd.EXECUTION_FILE).unlink()                                         # execution record lost
    assert fd.verify_run(d) == {"status": "INCOMPLETE", "units": 6,
                                **_axes(execution="MISSING", sessions=0, time_accounting="INCOMPLETE")}
    out = fd.run_units(d, ref[1], ref[2])
    assert (out["reused"], out["computed"]) == (6, 0) and _files(d) == ref[3]
    # status COMPLETE again; the units' completion records stay lost, so time accounting stays INCOMPLETE
    assert fd.verify_run(d) == {"status": "COMPLETE", "units": 6, **_axes(time_accounting="INCOMPLETE")}


def _session(**over):
    s = {"started_utc": "2026-01-01T00:00:00+00:00", "workers": 1, "init": "created", "init_s": 0.5, "git": {},
         "python": "3", "platform": "x", "tmp_reported": [], "units": [], "end": None}
    s.update(over)
    return s


def _execution(**over):
    ex = {"schema_version": fd.EXECUTION_SCHEMA, "evidence": fd.EVIDENCE, "sessions": [_session()]}
    ex.update(over)
    return fd.canonical_bytes(ex)


@pytest.mark.parametrize("bad, match", [
    (b"{", "malformed"), (b"\xff\xfe", "malformed"),
    (_execution(schema_version="x"), "schema error"), (_execution(evidence="REAL"), "schema error"),
    (_execution(extra=1), "schema error"), (_execution(sessions={"a": 1}), "schema error"),
    (_execution(sessions=[1]), "schema error"), (fd.canonical_bytes([]), "schema error"),
    (_execution(sessions=[_session(units=[{"cell": "x"}])]), "schema error"),
    (_execution(sessions=[_session(end={"elapsed_s": 1.0})]), "schema error"),
    (_execution(sessions=[{"workers": 1}]), "schema error"),
    (_execution(sessions=[]), "no session")])
def test_crash_execution_damage_stops(ref, tmp_path, bad, match):
    d = _copy(ref, tmp_path)
    (d / fd.EXECUTION_FILE).write_bytes(bad)
    for call in (lambda: fd.verify_run(d), lambda: fd.run_units(d, ref[1], ref[2])):
        with pytest.raises(fd.StopImplementation, match=match):
            call()
    assert (d / fd.EXECUTION_FILE).read_bytes() == bad and _files(d) == ref[3]   # never rewritten
    _drop_final(d)                                                             # also in an unfinished run
    with pytest.raises(fd.StopImplementation, match=match):
        fd.verify_run(d)


def test_crash_execution_axes_are_separate(ref, tmp_path):
    d = _copy(ref, tmp_path, "run")
    _drop_final(d)
    for p in fd.unit_paths(d, "E1-theta0.7", 2):
        p.unlink()
    got = fd.verify_run(d)
    assert got == {"status": "INCOMPLETE", **_axes(unit_status="INCOMPLETE", missing_units=["E1-theta0.7/u00002"])}
    (d / fd.EXECUTION_FILE).unlink()
    assert fd.verify_run(d)["execution"] == "MISSING" and fd.verify_run(d)["time_accounting"] == "INCOMPLETE"


@pytest.fixture(scope="module")
def sigma3():
    return fd.sigma_calibration(3, "FUTDIAG-TEST")


def _fixture_cal(sigma):
    return fd.build_calibration(fd.TEST_FIXTURE, fd.fixture_e1(), sigma, fd.fixture_identity())


def test_cal_sigma_seeds_values_and_workers(sigma3):
    assert sigma3["seed_path"] == ["FUTDIAG-TEST", "E1-ecal", "<rep>", "all", "path"] and sigma3["reps"] == 3
    for i, v in enumerate(sigma3["sharpes"]):
        seed = derived_seed(20261029, "FUTDIAG-TEST", "E1-ecal", str(i), "all", "path")
        r = fd.e1_window_returns(0.728515625, seed, ("conf",))["conf"]
        assert len(r) == 2227 and v == fd.annual_sharpe(r)
    assert [sigma3[k] for k in ("sigma_hat", "kappa_hat", "sigma_L", "sigma_U")] == \
        list(fd.sigma_interval(sigma3["sharpes"]))
    assert fd.sigma_calibration(3, "FUTDIAG-TEST", workers=2) == sigma3          # worker count does not matter
    assert fd.seed_for(fd.sigma_seed_path(0)) == derived_seed(20261029, "FUTDIAG-SIGMA", "E1-ecal", "0", "all", "path")
    assert fd.seed_for(fd.sigma_seed_path(0)) != fd.seed_for(fd.sigma_seed_path(0, "FUTDIAG-TEST"))
    for bad in ((3, "FUTDIAG"), (3, "FUTDIAG-X"), (1, "FUTDIAG-TEST"), (True, "FUTDIAG-TEST")):
        with pytest.raises(fd.StopImplementation):
            fd.sigma_calibration(*bad)


def test_cal_fixture_canonical_bytes_sha_and_provenance(sigma3, tmp_path):
    cal = _fixture_cal(sigma3)
    assert cal["kind"] == fd.TEST_FIXTURE and cal["identity"]["git"] is None
    assert (cal["e1"]["edge_annual"], cal["e1"]["sigma_pop"]) == (0.728515625, 0.70 / math.sqrt(365))   # R-7
    raw = fd.calibration_bytes(cal)
    assert raw == (json.dumps(cal, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
                   + "\n").encode("utf-8")
    assert fd.calibration_bytes(_fixture_cal(fd.sigma_calibration(3, "FUTDIAG-TEST"))) == raw
    sha = fd.write_calibration(tmp_path, cal)
    path = tmp_path / fd.CALIBRATION_FILE
    assert sha == hashlib.sha256(raw).hexdigest() and path.read_bytes() == raw
    assert fd.write_calibration(tmp_path, cal) == sha                          # same bytes: accepted
    assert fd.load_calibration(path, sha) == (cal, sha)
    assert fd.calibration_provenance(cal, sha) == {"kind": fd.TEST_FIXTURE, "calibration_sha256": sha,
                                                   "edge_annual": 0.728515625, "sigma_pop": 0.70 / math.sqrt(365)}
    with pytest.raises(fd.StopImplementation):
        fd.calibration_provenance(cal, "0" * 64)
    other = _fixture_cal(fd.sigma_calibration(4, "FUTDIAG-TEST"))
    with pytest.raises(fd.StopImplementation, match="refusing to change"):
        fd.write_calibration(tmp_path, other)
    assert path.read_bytes() == raw                                            # never overwritten
    with pytest.raises(fd.StopImplementation, match="not the expected"):
        fd.load_calibration(path, "0" * 64)
    for bad, match in ((json.dumps(cal, indent=1).encode(), "not canonical"), (b"{", "malformed")):
        p = tmp_path / "bad.json"
        p.write_bytes(bad)
        with pytest.raises(fd.StopImplementation, match=match):
            fd.load_calibration(p)


def test_cal_fixture_is_never_research(sigma3):
    cal = _fixture_cal(sigma3)
    with pytest.raises(fd.StopImplementation, match="not a research input"):
        fd.research_e1_cell(cal)
    sigma_research_ns = {**sigma3, "namespace": "FUTDIAG-SIGMA",
                         "seed_path": ["FUTDIAG-SIGMA", "E1-ecal", "<rep>", "all", "path"]}
    for kind, e1, sigma, ident in (
            (fd.RESEARCH, fd.fixture_e1(), sigma3, fd.fixture_identity()),        # fixture values as research
            (fd.TEST_FIXTURE, fd.fixture_e1(), sigma_research_ns, fd.fixture_identity()),   # FUTDIAG-SIGMA
            (fd.TEST_FIXTURE, {**fd.fixture_e1(), "edge_annual": 0.73}, sigma3, fd.fixture_identity()),
            (fd.TEST_FIXTURE, fd.fixture_e1(), sigma3, {**fd.fixture_identity(), "git": {"commit": "a" * 40}}),
            (fd.TEST_FIXTURE, fd.fixture_e1(), {**sigma3, "sigma_hat": sigma3["sigma_hat"] * 2}, fd.fixture_identity()),
            ("CALIBRATION", fd.fixture_e1(), sigma3, fd.fixture_identity())):
        with pytest.raises(fd.StopImplementation):
            fd.build_calibration(kind, e1, sigma, ident)
    prov = fd.calibration_provenance(cal, hashlib.sha256(fd.calibration_bytes(cal)).hexdigest())
    spec = _store_spec()
    assert _inputs(spec, provenance=prov)["calibration_provenance"] == prov    # FUTDIAG-TEST: allowed
    for namespace, mode in (("FUTDIAG", "core"), ("FUTDIAG-PILOT", "pilot")):
        with pytest.raises(fd.StopImplementation):
            _inputs(_store_spec(mode=mode), namespace=namespace, provenance=prov)


def _fake_git(head="1" * 40, tree="2" * 40, status="", blobs=None, base_blobs=None):
    """A read-only git stand-in: HEAD / base blobs equal the working files unless overridden."""
    work = {fd.MODULE_PATH: fd._blob_lf(FsPath(fd.__file__).read_bytes()),
            **{f"src/{k}": v["git_blob_lf"] for k, v in source_identity().items()}}
    tables = {head: {**work, **(blobs or {})}, fd.BASE_SHA: {**work, **(base_blobs or {})}}

    def git(root, *args):
        if args == ("rev-parse", "HEAD"):
            return head + "\n"
        if args == ("rev-parse", "HEAD^{tree}"):
            return tree + "\n"
        if args == ("status", "--porcelain"):
            return status
        if args[0] == "ls-tree" and args[2] == "--":
            table = tables.get(args[1], {})
            return "".join(f"100644 blob {table[p]}\t{p}\n" for p in args[3:] if p in table)
        raise AssertionError(f"unexpected git call {args}")
    return git


def test_identity_research_identity_and_mismatch_stops(tmp_path):
    ident = fd.research_identity(git=_fake_git())
    assert tuple(sorted(ident)) == tuple(sorted(fd.IDENTITY_FIELDS))
    assert ident["contract_sha256"] == fd.CONTRACT_SHA256                      # the real contract files
    assert ident["mcv06_source_identity"] == source_identity() and ident["worktree_clean"] is True
    assert fd.verify_research_identity(ident, git=_fake_git()) == ident
    montecarlo = "src/moneylab/research/v06/montecarlo.py"
    for git, match in ((_fake_git(status=" M src/x.py\n"), "not clean"), (_fake_git(status="?? new.txt\n"), "not clean"),
                       (_fake_git(head="HEAD"), "not readable"),
                       (_fake_git(blobs={fd.MODULE_PATH: "0" * 40}), "HEAD blobs"),
                       (_fake_git(blobs={montecarlo: "0" * 40}), "HEAD blobs"),
                       (_fake_git(base_blobs={montecarlo: "0" * 40}), "base commit")):
        with pytest.raises(fd.StopImplementation, match=match):
            fd.research_identity(git=git)
    with pytest.raises(fd.StopImplementation, match=r"differs from the recorded one: \['git_head'\]"):
        fd.verify_research_identity(ident, git=_fake_git(head="3" * 40))
    with pytest.raises(fd.StopImplementation, match="identity fields"):
        fd.verify_research_identity({**ident, "extra": 1}, git=_fake_git())
    root = fd.repo_root()
    for rel in fd.CONTRACT_FILES.values():                                    # a copy elsewhere: the module is not there
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / rel, tmp_path / rel)
    with pytest.raises(fd.StopImplementation, match="imported from"):
        fd.research_identity(tmp_path, git=_fake_git())
    errata = tmp_path / fd.CONTRACT_FILES["ERRATA-003"]
    errata.write_bytes(errata.read_bytes() + b"\n")
    with pytest.raises(fd.StopImplementation, match=r"accepted sha256: \['ERRATA-003'\]"):
        fd.research_identity(tmp_path, git=_fake_git())
    with pytest.raises(fd.StopImplementation, match="git rev-parse HEAD failed"):
        fd._git(tmp_path, "rev-parse", "HEAD")                                # real git, read-only, not a repo


def test_identity_check_run_identity():
    ident = fd.research_identity(git=_fake_git(), calibration_sha256="e" * 64)
    spec = _spec(code_sha=ident["git_head"], code_tree=ident["git_tree"],
                 config_sha256=ident["contract_sha256"]["config"], prereg_sha256=ident["contract_sha256"]["prereg"])
    inputs = {"futility_diag_source": fd.module_source(), "mcv06_source_identity": source_identity(),
              "calibration_provenance": {"kind": fd.RESEARCH, "calibration_sha256": "e" * 64}}
    fd.check_run_identity(spec, inputs, ident)
    for over_spec, over_inputs in (({"code_sha": "f" * 40}, {}), ({"prereg_sha256": "0" * 64}, {}),
                                   ({}, {"calibration_provenance": {"kind": fd.RESEARCH, "calibration_sha256": "0" * 64}}),
                                   ({}, {"futility_diag_source": {"sha256": "0", "sha256_lf": "0"}})):
        with pytest.raises(fd.StopImplementation, match="do not match the research identity"):
            fd.check_run_identity({**spec, **over_spec}, {**inputs, **over_inputs}, ident)


def _research_parts(sigma_reps=2000, namespace="FUTDIAG-SIGMA", **e1_over):
    rng = random.Random(7)
    values = [0.4 + 0.4 * rng.gauss(0.0, 1.0) for _ in range(sigma_reps)]
    s_hat, kappa, lo, hi = fd.sigma_interval(values)
    sigma = {"namespace": namespace, "cell": "E1-ecal", "window": "conf", "edge_annual": 0.728515625,
             "reps": sigma_reps, "seed_path": [namespace, "E1-ecal", "<rep>", "all", "path"], "z": fd.Z_SIGMA,
             "sharpes": values, "sigma_hat": s_hat, "kappa_hat": kappa, "sigma_L": lo, "sigma_U": hi}
    e1 = {"cell": "E1-theta0.7", "theta": 0.7, "strategy": "M60", "target": "E0", "years": 4000,
          "seed_parts": list(fd.E1_CALIB_SEED_PARTS), "seed": fd.explicit_seed(fd.E1_CALIB_SEED_PARTS),
          "edge_annual": 0.731, "achieved_sharpe": 0.7004, "residual": 0.7004 - 0.7, "sigma_pop": 0.0367}
    e1.update(e1_over)
    return e1, sigma


def test_cal_research_contract_and_identity_gate(tmp_path):
    """Synthetic stand-in values (no calibration MC): the RESEARCH rules, the E1 cell and the identity gate."""
    ident = fd.research_identity(git=_fake_git())
    e1, sigma = _research_parts()
    cal = fd.build_calibration(fd.RESEARCH, e1, sigma, ident)
    assert fd.research_e1_cell(cal) == fd.e1_cell(0.731, 0.0367)
    for e1_over, sigma_kw, ident_x in (({"years": 3999}, {}, ident),
                                       ({"seed_parts": ["FUTDIAG-TEST", "calib"]}, {}, ident),
                                       ({"achieved_sharpe": 0.7011, "residual": 0.7011 - 0.7}, {}, ident),
                                       ({"residual": 0.0}, {}, ident),
                                       ({}, {"sigma_reps": 1999}, ident),
                                       ({}, {"namespace": "FUTDIAG-TEST"}, ident),
                                       ({}, {}, fd.fixture_identity()),
                                       ({}, {}, {**ident, "worktree_clean": False}),
                                       ({}, {}, {**ident, "calibration_sha256": "e" * 64})):
        e1_x, sigma_x = _research_parts(**sigma_kw, **e1_over)
        with pytest.raises(fd.StopImplementation):
            fd.build_calibration(fd.RESEARCH, e1_x, sigma_x, ident_x)
    with pytest.raises(fd.StopImplementation, match="not clean"):
        fd.write_calibration(tmp_path, cal, git=_fake_git(status=" M x\n"))
    with pytest.raises(fd.StopImplementation, match="differs from the recorded one"):
        fd.write_calibration(tmp_path, cal, git=_fake_git(head="4" * 40))
    assert not (tmp_path / fd.CALIBRATION_FILE).exists()                       # nothing written on STOP
    sha = fd.write_calibration(tmp_path, cal, git=_fake_git())
    assert fd.load_calibration(tmp_path / fd.CALIBRATION_FILE, sha)[0] == cal


def test_cal_calibrate_e1_small_test_path(monkeypatch):
    """calibrate_e1 plumbing on a 3-year FUTDIAG-TEST path (not the G5 4,000-year calibration)."""
    parts = ("FUTDIAG-TEST", "calib-test")
    e1 = fd.calibrate_e1(3, parts)
    assert (e1["years"], e1["seed_parts"], e1["seed"]) == (3, list(parts), derived_seed(20261029, *parts))
    assert abs(e1["residual"]) <= fd.CALIB_TOLERANCE and e1["sigma_pop"] > 0
    assert e1["residual"] == e1["achieved_sharpe"] - 0.7
    real = fd.calibrate_edge
    monkeypatch.setattr(fd, "calibrate_edge", lambda *a, **k: (real(*a, **k)[0], 0.75))
    with pytest.raises(fd.StopImplementation, match="does not reproduce"):
        fd.calibrate_e1(3, parts)

    def fail(*a, **k):
        raise ValueError("cannot reach Sharpe")
    monkeypatch.setattr(fd, "calibrate_edge", fail)
    with pytest.raises(fd.StopImplementation, match="calibration failed"):
        fd.calibrate_e1(3, parts)
    for bad in ((0, parts), (3, ("FUTVAL", "x"))):
        with pytest.raises(fd.StopImplementation):
            fd.calibrate_e1(*bad)


def test_cal_achieved_comparison_follows_mcv06_arithmetic(monkeypatch):
    """calibrate_edge returns achieved = (Sharpe - theta) + theta; the check rebuilds exactly that, no tolerance."""
    theta = fd.CORE_THETA
    assert theta == 0.7
    for s in (0.7, 0.7004, 0.69931, 0.70007463504927):                       # A: converged values pass
        assert fd.achieved_reproduced(s, (s - theta) + theta)
        assert (s - theta) + theta == s                                       # Sterbenz: exact near theta
    s = 1e-17                                                                  # B: finite counterexample
    achieved = (s - theta) + theta
    assert math.isfinite(achieved) and achieved != s                          # old `s != achieved` would STOP
    assert fd.achieved_reproduced(s, achieved)                                # MC-V06 arithmetic passes
    assert not fd.achieved_reproduced(0.7004, math.nextafter((0.7004 - theta) + theta, 1.0))   # C: real difference
    real = fd.calibrate_edge

    def off_by_one_ulp(*a, **k):
        edge, ach = real(*a, **k)
        return edge, math.nextafter(ach, 1.0)
    monkeypatch.setattr(fd, "calibrate_edge", off_by_one_ulp)
    with pytest.raises(fd.StopImplementation, match="does not reproduce"):
        fd.calibrate_e1(3, ("FUTDIAG-TEST", "calib-test"))


def test_identity_not_applied_to_fixture_runs(ref, tmp_path, monkeypatch, sigma3):
    def no_git(*a, **k):
        raise AssertionError("git must not run for TEST_FIXTURE work")
    monkeypatch.setattr(fd.subprocess, "run", no_git)
    fd.write_calibration(tmp_path, _fixture_cal(sigma3))
    d = _copy(ref, tmp_path, "run")
    (d / fd.EXECUTION_FILE).unlink()
    fd.run_units(d, ref[1], ref[2])
    assert fd.verify_run(d)["status"] == "COMPLETE" and _files(d) == ref[3]


# --- G3b-5-2: G6 nuisance summary, g6/ storage, timing (fake clock), decision functions (no pilot / MC) -----------

def _srec(cell, rep, window, v0=1.0, v0d=1.0, v60=1.0, lo=1.0, hi=1.0, nd=False, sd=False):
    """A synthetic record carrying only what the summaries read (p = 0.01 rejects, 1.0 does not)."""
    return {"cell": cell, "rep": rep, "window": window, "sd": sd,
            "variants": {"V0": {"p": v0}, "V0d": {"p": v0d}, "V0b60": {"p": v60},
                         "S1": {"p_lo": lo, "p_hi": hi, "nd_flag": nd}}}


def _rej(flag):
    return 0.01 if flag else 1.0


def _synthetic(n, e1_f12, e1_f36, p0, e1_conf=None):
    """by_cell from per-rep functions returning the _srec keyword arguments."""
    e1 = [_srec("E1-theta0.7", i, w, **f(i)) for i in range(n)
          for w, f in (("conf", e1_conf or (lambda i: {})), ("f12", e1_f12), ("f36", e1_f36))]
    p0_recs = [_srec("P0-theta0.7", i, w, **p0(i, w)) for i in range(n) for w in ("conf", "f12")]
    return {"E1-theta0.7": e1, "P0-theta0.7": p0_recs}


def test_g6_pilot_r_c_v1_max_and_required_items():
    n = 200
    by_cell = _synthetic(
        n, lambda i: {"v0": _rej(i < 20), "lo": _rej(i < 30), "hi": _rej(i < 15), "v0d": _rej(i < 25)},
        lambda i: {"v0": _rej(i < 10), "v60": _rej(5 <= i < 15)},
        lambda i, w: {"v0": _rej(i < (10 if w == "f12" else 5))})
    out = fd.pilot_r_c(by_cell, n)
    h = out["hypotheses"]
    assert (h["V-1"]["x_lo"], h["V-1"]["x_hi"], h["V-1"]["x_disc"]) == (10, 5, 10)        # max(lo, hi)
    assert [h[k]["x_disc"] for k in ("V-2", "V-3", "V-8")] == [5, 10, 5]
    for v in h.values():
        assert v["pi_upper"] == fd.clopper_pearson_upper(v["x_disc"], n)
        assert v["r_h"] == fd.required_reps(v["pi_upper"])[0]
    assert out["r_c"] == {"E1-theta0.7": max(h[k]["r_h"] for k in ("V-1", "V-2", "V-3")),
                          "P0-theta0.7": h["V-8"]["r_h"]} and out["over_max"] == []
    every = _synthetic(n, lambda i: {"v0": 0.01}, lambda i: {}, lambda i, w: {"v0": _rej(w == "f12")})
    assert fd.pilot_r_c(every, n)["over_max"] == ["E1-theta0.7", "P0-theta0.7"]          # x = n: R_c > 40,000
    for broken in ({**by_cell, "P0-theta0.7": [r for r in by_cell["P0-theta0.7"] if r["window"] != "conf"]},
                   {**by_cell, "E1-theta0.7": [r for r in by_cell["E1-theta0.7"] if r["rep"] != 7]},
                   {"E1-theta0.7": by_cell["E1-theta0.7"]}):
        with pytest.raises(fd.StopImplementation, match="required records missing"):
            fd.pilot_r_c(broken, n)


def test_g6_pd5_boundaries():
    n = 100

    def deg(split, nd, sd):
        return fd.pd5_degeneracy(_synthetic(
            n, lambda i: {"lo": _rej(i < split), "nd": i < nd, "sd": i < sd},
            lambda i: {}, lambda i, w: {}), n)
    ok = deg(2, 5, 5)                                                          # exactly at the thresholds
    assert ok["windows"]["f12"] == {"lo_hi_split": 0.02, "nd_flag": 0.05, "sd": 0.05} and not ok["stop"]
    for args in ((3, 0, 0), (0, 6, 0), (0, 0, 6)):
        assert deg(*args)["stop"]


def test_g6_p2_spell_rule():
    assert fd.interior_spells([1, 1, 0, 0, 0, 1, 0, 0]) == [(0, 3), (1, 1)]   # first and last runs dropped
    out = fd.p2_spell([[0, 1, 1, 0, 0, 1], [1, 0, 0, 0, 1, 1, 1, 0, 1]])
    # hold: [2], [3] -> mean 2.5 -> 3; cash: [2], [3, 1] -> mean 2 -> 2
    assert out == {"status": "OK", "hold": {"spells": 2, "mean": 2.5, "rounded": 3, "transition_probability": 1 / 3},
                   "cash": {"spells": 3, "mean": 2.0, "rounded": 2, "transition_probability": 0.5}}
    assert fd.p2_spell([[0, 0, 0], [1, 0, 1]])["status"] == fd.P2_UNDEFINED          # no interior hold spell


@pytest.fixture(scope="module")
def pilot(tmp_path_factory, sigma3):
    cal = _fixture_cal(sigma3)
    sha = hashlib.sha256(fd.calibration_bytes(cal)).hexdigest()
    spec = _store_spec(mode="pilot", windows=["conf", "f12", "f36"], reps=6, unit_size=3)
    inputs = fd.build_run_inputs(spec, [fd.e1_cell(fd.E_CAL, fd.P0_DAILY_SD), P0], NS,
                                 fd.calibration_provenance(cal, sha))
    d = tmp_path_factory.mktemp("pilot") / "run"
    fd.run_units(d, spec, inputs)
    return d, spec, inputs, cal, sha, _files(d)


def _keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _keys(v)


def test_g6_summary_storage_and_nuisance_only(pilot, tmp_path):
    d0, spec, inputs, cal, sha, files = pilot
    d = tmp_path / "run"
    shutil.copytree(d0, d)
    assert fd.verify_run(d)["g6"] == "ABSENT" and fd.verify_run(d)["status"] == "COMPLETE"   # pilot without G6
    summary = fd.write_g6(d, cal, sha)
    raw = (d / "g6" / "g6_summary.json").read_bytes()
    assert raw == fd.canonical_bytes(summary)
    assert (d / "g6" / "SHA256SUMS").read_bytes() == f"{hashlib.sha256(raw).hexdigest()}  g6_summary.json\n".encode()
    assert _files(d) == {**files, "g6/g6_summary.json": raw, "g6/SHA256SUMS": (d / "g6" / "SHA256SUMS").read_bytes()}
    assert fd.sha256sums_bytes(d) == files["SHA256SUMS"]                       # top level never covers g6/
    status = fd.verify_run(d)
    assert (status["status"], status["g6"]) == ("COMPLETE", "VERIFIED")
    assert summary["pilot"]["manifest_sha256"] == hashlib.sha256(files["manifest.json"]).hexdigest()
    assert summary["pilot"]["sha256sums_sha256"] == hashlib.sha256(files["SHA256SUMS"]).hexdigest()
    assert summary["calibration"]["sha256"] == sha and summary["content"] == fd.G6_CONTENT
    forbidden = {"rate", "rates", "d_hat", "p_one_sided", "u_d", "label", "labels", "holm", "contrasts", "n10", "n01"}
    assert not forbidden & set(_keys(summary))                                 # no effect values (DC11)
    by_cell = fd.read_records(d, spec)
    assert summary["r_c"] == json.loads(fd.canonical_bytes(fd.pilot_r_c(by_cell, 6)))
    assert fd.write_g6(d, cal, sha) == summary and (d / "g6" / "g6_summary.json").read_bytes() == raw   # rerun


def test_g6_bytes_do_not_depend_on_workers(pilot, tmp_path):
    d0, spec, inputs, cal, sha, files = pilot
    d1, d2 = tmp_path / "w1", tmp_path / "w2"
    shutil.copytree(d0, d1)
    fd.run_units(d2, spec, inputs, workers=2)
    assert _files(d2) == files
    fd.write_g6(d1, cal, sha)
    fd.write_g6(d2, cal, sha)
    assert _files(d1) == _files(d2)


def test_g6_damage_and_mismatch_stop(pilot, tmp_path, sigma3):
    d0, spec, inputs, cal, sha, files = pilot

    def fresh(name):
        d = tmp_path / name
        shutil.copytree(d0, d)
        fd.write_g6(d, cal, sha)
        return d, d / "g6" / "g6_summary.json", d / "g6" / "SHA256SUMS"
    d, summ, sums = fresh("a")
    summ.write_bytes(summ.read_bytes().replace(b'"reps":6', b'"reps":7', 1))
    with pytest.raises(fd.StopImplementation, match="g6"):
        fd.verify_run(d)
    with pytest.raises(fd.StopImplementation, match="g6"):
        fd.write_g6(d, cal, sha)                                               # never repaired
    d, summ, sums = fresh("b")
    sums.write_bytes(b"0" * 64 + b"  g6_summary.json\n")
    with pytest.raises(fd.StopImplementation, match="does not match"):
        fd.verify_run(d)
    d, summ, sums = fresh("c")
    summ.unlink()
    with pytest.raises(fd.StopImplementation, match="without"):
        fd.verify_run(d)
    d, summ, sums = fresh("d")
    raw = summ.read_bytes()
    sums.unlink()                                                              # interrupted between the two writes
    assert fd.verify_run(d)["g6"] == "INCOMPLETE"
    fd.write_g6(d, cal, sha)
    assert fd.verify_run(d)["g6"] == "VERIFIED" and summ.read_bytes() == raw
    d, summ, sums = fresh("e")                                                 # consistent pair, different content
    changed = fd.canonical_bytes({**json.loads(summ.read_bytes()), "stop_for_user_decision": ["X"]})
    summ.write_bytes(changed)
    sums.write_bytes(fd.g6_sums_bytes(changed))
    assert fd.verify_run(d)["g6"] == "VERIFIED"
    with pytest.raises(fd.StopImplementation, match="refusing to change"):
        fd.write_g6(d, cal, sha)                                               # rerun bytes differ: STOP
    assert summ.read_bytes() == changed
    d, summ, sums = fresh("f")
    (d / "g6" / "notes.txt").write_text("x")
    with pytest.raises(fd.StopImplementation, match="unexpected files"):
        fd.verify_run(d)
    d, summ, sums = fresh("g")
    for p in fd.unit_paths(d, "P0-theta0.7", 1):
        p.unlink()
    (d / "manifest.json").unlink()
    (d / "SHA256SUMS").unlink()
    with pytest.raises(fd.StopImplementation, match="g6/ present for an incomplete run"):
        fd.verify_run(d)
    d = tmp_path / "h"
    shutil.copytree(d0, d)
    other = _fixture_cal(fd.sigma_calibration(4, "FUTDIAG-TEST"))
    with pytest.raises(fd.StopImplementation, match="do not name this calibration"):
        fd.write_g6(d, other, hashlib.sha256(fd.calibration_bytes(other)).hexdigest())
    assert not (d / "g6").exists()


class FakeClock:
    def __init__(self, step=1.0):
        self.t, self.step = 0.0, step

    def __call__(self):
        self.t += self.step
        return self.t


def test_timing_fake_clock_records_and_bytes(ref, tmp_path, monkeypatch):
    monkeypatch.setattr(fd, "_clock", FakeClock())
    d = tmp_path / "run"
    fd.run_units(d, ref[1], ref[2])
    assert _files(d) == ref[3]                                                 # time never reaches unit bytes
    (s,) = json.loads((d / fd.EXECUTION_FILE).read_bytes())["sessions"]
    assert s["init_s"] == 1.0 and [u["rep_seconds"] for u in s["units"]] == [[1.0, 1.0], [1.0, 1.0], [1.0]] * 2
    # each rep: 2 clock reads; each unit: one more for its elapsed time since T_wall start
    assert [u["elapsed_s"] for u in s["units"]] == [5.0, 10.0, 13.0, 18.0, 23.0, 26.0]
    assert s["end"]["elapsed_s"] == 26.0 and s["end"]["stop"] is None and s["end"]["finalize_s"] > 0
    assert s["units"][-1]["progress_projection_s"] == 26.0                     # cumulative x total / done
    # ERRATA-004 R-1: clock 1 = before init_run, 3 = T_wall start, 29 = last index, 30 / 31 = SHA256SUMS start / end
    assert (s["end"]["pre_wall_s"], s["end"]["post_wall_s"], s["end"]["finalize_s"]) == (2.0, 2.0, 1.0)
    assert s["end"]["post_wall_scope"] == fd.POST_WALL_FULL
    t = fd.g6_timing({"sessions": [s]}, ref[1], {"E1-theta0.7": 10_000, "P0-theta0.7": 20_000}, workers_required=1)
    assert t["t_hat_s"] == {"E1-theta0.7": 1.0, "P0-theta0.7": 1.0}            # sd = 0: the mean
    assert (t["sum_t_s"], t["t_wall_s"], t["eta_hat"]) == (10.0, 26.0, 10.0 / (1 * 26.0))
    assert t["worker_hours"] == (10_000 * 1.0 + 20_000 * 1.0) * 1.3 / 3600
    assert t["wall_hours"] == t["worker_hours"] / (12 * t["eta_hat"]) and t["budget_pass"]


def test_timing_pre_post_wall_never_enter_budget_values(ref, tmp_path, monkeypatch):
    """ERRATA-004 R-1: pre_wall_s / post_wall_s are diagnostics only (W, t_hat, eta_hat, cumulative unchanged)."""
    monkeypatch.setattr(fd, "_clock", FakeClock())
    d = tmp_path / "run"
    fd.run_units(d, ref[1], ref[2])
    ex = fd.read_execution(d)
    r_c = {"E1-theta0.7": 10_000, "P0-theta0.7": 20_000}
    base = fd.g6_timing(ex, ref[1], r_c, workers_required=1)
    (s,) = ex["sessions"]
    changed = {**ex, "sessions": [{**s, "end": {**s["end"], "pre_wall_s": 1e9, "post_wall_s": 1e9}}]}
    assert fd.g6_timing(changed, ref[1], r_c, workers_required=1) == base
    assert fd.time_accounting(changed)["cumulative_s"] == fd.time_accounting(ex)["cumulative_s"] == 26.0
    assert base["t_wall_s"] == 26.0                                           # T_wall boundary unchanged


def test_g6_unit_size_recorded_and_g7_gate(pilot, tmp_path):
    """ERRATA-004 R-4: G6 records the pilot run_spec.unit_size (no G7 run_spec needed); G7 entry compares it."""
    d0, spec, inputs, cal, sha, files = pilot
    d = tmp_path / "run"
    shutil.copytree(d0, d)
    with pytest.raises(fd.StopImplementation, match="VERIFIED g6"):
        fd.check_g7_unit_size(d, _spec(unit_size=3))                          # before G6
    summary = fd.write_g6(d, cal, sha)                                         # no G7 run_spec involved
    assert summary["pilot"]["unit_size"] == spec["unit_size"] == 3
    assert {k: v for k, v in _files(d).items() if not k.startswith("g6/")} == files   # pilot files untouched
    assert fd.check_g7_unit_size(d, _spec(unit_size=3)) == 3
    with pytest.raises(fd.StopImplementation, match="differs from the pilot"):
        fd.check_g7_unit_size(d, _spec(unit_size=2))
    with pytest.raises(fd.StopImplementation, match="CORE run_spec"):
        fd.check_g7_unit_size(d, _spec(mode="pilot", unit_size=3))
    summ, sums = d / "g6" / "g6_summary.json", d / "g6" / "SHA256SUMS"
    forged = json.loads(summ.read_bytes())
    forged["pilot"]["unit_size"] = 2                                           # consistent pair, wrong unit_size
    summ.write_bytes(fd.canonical_bytes(forged))
    sums.write_bytes(fd.g6_sums_bytes(summ.read_bytes()))
    with pytest.raises(fd.StopImplementation, match="does not reference"):
        fd.check_g7_unit_size(d, _spec(unit_size=2))


def test_timing_t_upper_and_budget_boundaries():
    times = [1.0, 2.0, 3.0, 4.0]
    m, s = 2.5, math.sqrt(sum((x - 2.5) ** 2 for x in times) / 3)
    assert fd.t_upper(times) == m + fd.t_ppf(0.95, 3) * s / math.sqrt(4)
    assert fd.t_upper([2.0] * 5) == 2.0
    for bad in ([1.0], [1.0, -0.1], [1.0, math.nan], [1.0, math.inf], [1.0, None]):
        with pytest.raises(fd.StopForUserDecision):
            fd.t_upper(bad)
    assert fd.budget_ok(1152, 96) and fd.budget_ok(1152.0, 96.0)
    assert not fd.budget_ok(math.nextafter(1152.0, 2000.0), 96.0)
    assert not fd.budget_ok(1152.0, math.nextafter(96.0, 200.0))
    assert not fd.wall_exceeded(3.0, 2.0) and fd.wall_exceeded(math.nextafter(3.0, 4.0), 2.0)   # exactly 1.5 x passes


def _timed_session(spec, rep_seconds=1.0, t_wall=100.0, workers=12, end=True):
    units = [{"cell": c, "unit": k, "how": "computed", "rep_seconds": [rep_seconds] * (e - s), "elapsed_s": t_wall,
              "utc": "u", "progress_projection_s": 0.0} for c, k, s, e in fd._expected_units(spec)]
    return _session(workers=workers, units=units, end={
        "finished_utc": "f", "elapsed_s": t_wall, "computed": len(units), "reused": 0, "index_completed": 0,
        "finalize_s": 0.1, "stop": None, "pre_wall_s": 0.2, "post_wall_s": 0.3,
        "post_wall_scope": fd.POST_WALL_FULL} if end else None)


def test_timing_g6_stops_for_user_decision():
    spec = _store_spec(mode="pilot", reps=4, unit_size=2)
    r_c = {"E1-theta0.7": 10_000, "P0-theta0.7": 10_000}
    ok = fd.g6_timing({"sessions": [_timed_session(spec)]}, spec, r_c)
    assert ok["eta_hat"] == 8.0 / (12 * 100.0) and ok["workers"] == 12
    bad_sessions = (
        [_timed_session(spec), _timed_session(spec)],                         # two sessions
        [_timed_session(spec, end=False)],                                    # TIME_ACCOUNTING_INCOMPLETE
        [_timed_session(spec, workers=8)],                                    # not 12 workers
        [_timed_session(spec, t_wall=0.5)],                                   # eta > 1: never capped
        [_timed_session(spec, t_wall=0.0)],                                   # eta undefined
        [_timed_session(spec, rep_seconds=-1.0)],                             # invalid time
        [{**_timed_session(spec), "units": _timed_session(spec)["units"][:-1]}])   # a unit without its record
    for sessions in bad_sessions:
        with pytest.raises(fd.StopForUserDecision):
            fd.g6_timing({"sessions": sessions}, spec, r_c)
    with pytest.raises(fd.StopImplementation):
        fd.g6_timing({"sessions": [_timed_session(spec)]}, spec, {"E1-theta0.7": 10_000})


def test_timing_g6_record_once_and_kept_on_resume(pilot, tmp_path):
    d0, spec, inputs, cal, sha, files = pilot
    d = tmp_path / "run"
    shutil.copytree(d0, d)
    with pytest.raises(fd.StopImplementation, match="VERIFIED g6"):
        fd.write_g6_timing(d, workers_required=1)
    fd.write_g6(d, cal, sha)
    t = fd.write_g6_timing(d, workers_required=1)
    ex = json.loads((d / fd.EXECUTION_FILE).read_bytes())
    assert ex["g6_timing"] == json.loads(fd.canonical_bytes(t)) and 0 < t["eta_hat"] <= 1
    assert t["r_c"] == json.loads((d / "g6" / "g6_summary.json").read_bytes())["r_c"]["r_c"]
    assert fd.write_g6_timing(d, workers_required=1) == t                     # recomputed, equal
    assert fd.sha256sums_bytes(d) == files["SHA256SUMS"]
    with pytest.raises(fd.StopForUserDecision):
        fd.write_g6_timing(d)                                                 # the pilot did not use 12 workers
    original = (d / fd.EXECUTION_FILE).read_bytes()
    (d / fd.EXECUTION_FILE).write_bytes(fd.canonical_bytes({**ex, "g6_timing": {**ex["g6_timing"], "eta_hat": 0.5}}))
    with pytest.raises(fd.StopImplementation, match="g6_timing differs"):
        fd.write_g6_timing(d, workers_required=1)
    (d / fd.EXECUTION_FILE).write_bytes(original)
    fd.run_units(d, spec, inputs)                                             # a later session keeps g6_timing
    ex2 = json.loads((d / fd.EXECUTION_FILE).read_bytes())
    assert ex2["g6_timing"] == ex["g6_timing"] and len(ex2["sessions"]) == 2
    with pytest.raises(fd.StopForUserDecision):
        fd.write_g6_timing(d, workers_required=1)                             # two sessions now: T_wall undefined


def test_core_wall_budget_stop_and_resume(ref, tmp_path, monkeypatch):
    monkeypatch.setattr(fd, "_clock", FakeClock())
    d = tmp_path / "run"
    with pytest.raises(fd.StopImplementation, match="CORE wall-clock budget"):
        fd.run_units(d, ref[1], ref[2], expected_wall_s=6.0)                   # 1.5 x 6 = 9 < 10 after unit 2
    (s,) = json.loads((d / fd.EXECUTION_FILE).read_bytes())["sessions"]
    assert [u["elapsed_s"] for u in s["units"]] == [5.0, 10.0] and s["end"]["stop"].startswith("CORE wall-clock")
    # ERRATA-004 R-1 after a budget STOP: last index at clock 13, then only the unit record (clock 14); no SHA256SUMS
    assert (s["end"]["pre_wall_s"], s["end"]["post_wall_s"], s["end"]["finalize_s"]) == (2.0, 1.0, None)
    assert s["end"]["post_wall_scope"] == fd.POST_WALL_BUDGET_STOP
    assert fd.verify_run(d)["missing_units"] == ["E1-theta0.7/u00002", "P0-theta0.7/u00000", "P0-theta0.7/u00001",
                                                 "P0-theta0.7/u00002"]
    acct = fd.time_accounting(fd.read_execution(d))
    assert (acct["status"], acct["cumulative_s"]) == ("COMPLETE", 10.0)       # a budget STOP closes its session
    with pytest.raises(fd.StopImplementation, match="CORE wall-clock budget"):
        fd.run_units(d, ref[1], ref[2], expected_wall_s=6.0)                   # resume: recorded 10 > 9 at once
    assert len(fd.read_execution(d)["sessions"]) == 1                         # nothing started
    fd.run_units(d, ref[1], ref[2], expected_wall_s=100.0)
    acct = fd.time_accounting(fd.read_execution(d))
    assert acct["session_elapsed_s"][0] == 10.0 and acct["cumulative_s"] == sum(acct["session_elapsed_s"])
    assert acct["status"] == "COMPLETE" and _files(d) == ref[3]


def test_core_incomplete_time_accounting_never_passes(ref, tmp_path, monkeypatch):
    monkeypatch.setattr(fd, "_clock", FakeClock())
    d = tmp_path / "run"
    real, calls = fd.run_reps_timed, []

    def flaky(*a, **k):
        calls.append(1)
        if len(calls) == 3:
            raise KeyboardInterrupt
        return real(*a, **k)
    monkeypatch.setattr(fd, "run_reps_timed", flaky)
    with pytest.raises(KeyboardInterrupt):
        fd.run_units(d, ref[1], ref[2], expected_wall_s=100.0)
    monkeypatch.setattr(fd, "run_reps_timed", real)
    acct = fd.time_accounting(fd.read_execution(d))
    assert acct["status"] == "INCOMPLETE" and acct["lower_bound"] and not acct["budget_pass_allowed"]
    assert acct["cumulative_s"] == 10.0 and acct["open_sessions"] == [0]
    assert acct["unaccounted"][0]["session"] == 0                             # after the last completed unit
    with pytest.raises(fd.StopForUserDecision, match="TIME_ACCOUNTING_INCOMPLETE"):
        fd.run_units(d, ref[1], ref[2], expected_wall_s=100.0)                 # resume is the user's decision
    with pytest.raises(fd.StopImplementation, match="lower bound"):
        fd.run_units(d, ref[1], ref[2], expected_wall_s=6.0, resume_after_incomplete=True)   # 10 > 9
    fd.run_units(d, ref[1], ref[2], expected_wall_s=100.0, resume_after_incomplete=True)
    status = fd.verify_run(d)
    assert (status["status"], status["time_accounting"]) == ("COMPLETE", "INCOMPLETE")   # independent axes
    assert not fd.time_accounting(fd.read_execution(d))["budget_pass_allowed"] and _files(d) == ref[3]


def _decision_inputs():
    n = 400
    by_cell = _synthetic(
        n, lambda i: {"v0": _rej(i < 60), "lo": _rej(i < 30), "hi": _rej(i < 20), "v0d": _rej(i < 40)},
        lambda i: {"v0": _rej(i < 50), "v60": _rej(i < 30)},
        lambda i, w: {"v0": _rej(i < (60 if w == "f12" else 20))})
    rng = random.Random(3)
    v4 = {"sr_eval": 0.62, "batch_sharpes": [0.62 + 0.3 * rng.gauss(0.0, 1.0) for _ in range(40)]}
    sigma = {"sigma_L": 0.38, "sigma_U": 0.44}
    return by_cell, v4, sigma


def test_decision_summary_rules_and_bytes():
    by_cell, v4, sigma = _decision_inputs()
    out = fd.decision_summary(by_cell, v4, sigma)
    assert out["rates"]["E1-theta0.7"]["f12"]["V0"] == {"rate": 0.15, "mc_se": math.sqrt(0.15 * 0.85 / 400),
                                                         "reps": 400}
    lo = fd.mcnemar([i < 60 for i in range(400)], [i < 30 for i in range(400)])
    assert out["contrasts"]["V-1_lo"]["d_hat"] == lo.d_hat == 0.075 and out["contrasts"]["V-1_lo"]["u_d"] == lo.upper
    assert out["contrasts"]["V-8"]["d_hat"] == 0.1                             # r(f12) - r(conf)
    assert out["holm"]["p"]["V-1"] == out["contrasts"]["V-1_lo"]["p_one_sided"]   # p1 from D1_lo
    assert out["holm"]["rejected"] == fd.holm_rejections(out["holm"]["p"])
    assert out["eff"] == {"V-1": fd.eff_threshold(0.15), "V-2": fd.eff_threshold(0.15),
                          "V-3": fd.eff_threshold(0.125), "V-8": fd.eff_threshold(0.15)}
    assert out["v8_extra_condition"] is True
    inf = fd.v4_inference(0.62, 0.7, v4["batch_sharpes"])
    assert out["v4"]["delta_hat"] == inf.delta_hat and out["v4"]["delta_lower"] == inf.delta_lower
    assert out["labels"]["V-4"]["label"] == fd.label_v4(out["holm"]["rejected"]["V-4"], inf.delta_hat,
                                                         inf.delta_lower, 0.38, 0.44)[0]
    assert {v["label"] for v in out["labels"].values()} <= {"SUPPORTED", "WEAKENED", "INCONCLUSIVE"}
    assert fd.canonical_bytes(out) == fd.canonical_bytes(fd.decision_summary(*_decision_inputs()))
    with pytest.raises(fd.StopImplementation, match="required records missing"):
        fd.decision_summary({"E1-theta0.7": by_cell["E1-theta0.7"]}, v4, sigma)


def test_decision_label_v4_branches():
    assert fd.label_v4(True, -0.3, -0.35, 0.4, 0.45) == ("INCONCLUSIVE", "APPROX_OUT_OF_RANGE")   # 0.75 > 0.5
    assert fd.label_v4(True, -0.1, -0.15, 0.4, 0.45)[0] == "SUPPORTED"
    assert fd.label_v4(False, -0.1, -0.15, 0.4, 0.45)[0] == "INCONCLUSIVE"     # no Holm rejection
    assert fd.label_v4(True, 0.05, 0.02, 0.4, 0.45)[0] == "WEAKENED"           # Delta >= 0 never SUPPORTED
    assert fd.label_v4(False, -0.005, -0.08, 0.4, 0.45)[0] == "INCONCLUSIVE"


def test_decision_v4_evaluation_small_test_path():
    """v4_evaluation plumbing on a 3-year FUTDIAG-TEST path (not the G7 4,000-year evaluation)."""
    from dataclasses import replace
    out = fd.v4_evaluation(3, ("FUTDIAG-TEST", "v4eval-test"))
    path = make_path(replace(fd.E1_DGP, edge_annual=0.728515625), 3 * 365,
                     derived_seed(20261029, "FUTDIAG-TEST", "v4eval-test"))
    rets = fd.window_e0_returns(path, strategy_signals(path)["M60"], 123, path.days - 1, Costs().log_costs()["E0"])
    assert out["sr_eval"] == fd.annual_sharpe(rets)                           # _target_sharpe(path, "M60", "E0")
    assert (out["batch_sharpes"], out["batch_lengths"]) == tuple(map(list, fd.batch_sharpes(rets)))
    assert len(out["batch_sharpes"]) == 40 and sum(out["batch_lengths"]) == 3 * 365 - 124


# --- G3b-5-2F2: ERRATA-004 R-2, R-3, R-5, R-6 (fake clock, small fixtures; no calibration, pilot or CORE run) ------

def _v4_estimate(seconds):
    return {"name": fd.V4_ESTIMATE_NAME, "method": fd.V4_ESTIMATE_METHOD, "kind": "ESTIMATE", "seconds": seconds}


def _cal_record(seconds=1.5, minute=1):
    from datetime import UTC, datetime
    return fd.calibration_run_record(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, 0, minute, tzinfo=UTC),
                                     60.0 * minute, 4, {"e1_noise_s": 1.0, "e1_search_s": 50.0},
                                     _v4_estimate(seconds) if seconds is not None else None)


def test_r2_calibration_execution_record_separate_and_preserved(sigma3, tmp_path):
    cal = _fixture_cal(sigma3)
    sha = fd.write_calibration(tmp_path, cal)
    raw = (tmp_path / fd.CALIBRATION_FILE).read_bytes()
    first = _cal_record(1.5)
    fd.record_calibration_run(tmp_path, first)
    assert sorted(p.name for p in tmp_path.iterdir()) == [fd.CALIBRATION_FILE, fd.EXECUTION_FILE]
    assert (tmp_path / fd.CALIBRATION_FILE).read_bytes() == raw                # calibration.json untouched
    assert fd.load_calibration(tmp_path / fd.CALIBRATION_FILE, sha) == (cal, sha)
    assert fd.calibration_provenance(cal, sha)["calibration_sha256"] == sha    # execution.json is not provenance
    fd.record_calibration_run(tmp_path, _cal_record(2.5, minute=2))
    ex = fd.read_calibration_execution(tmp_path)
    assert ex["runs"][0] == json.loads(fd.canonical_bytes(first)) and len(ex["runs"]) == 2   # earlier run kept
    assert fd.v4_eval_time_estimate(tmp_path) == 2.5
    assert fd.write_calibration(tmp_path, cal) == sha                          # still the same bytes
    with pytest.raises(fd.StopImplementation, match="schema error"):
        fd.record_calibration_run(tmp_path, {**first, "v4_eval_time_estimate": {**_v4_estimate(1.0), "method": "M1"}})
    good = (tmp_path / fd.EXECUTION_FILE).read_bytes()
    for bad, match in ((b"{", "malformed"), (fd.canonical_bytes({**ex, "extra": 1}), "schema error"),
                       (fd.canonical_bytes({**ex, "runs": []}), "no run"),
                       (fd.canonical_bytes({**ex, "runs": [{**first, "workers": 0}]}), "schema error")):
        (tmp_path / fd.EXECUTION_FILE).write_bytes(bad)
        for call in (lambda: fd.read_calibration_execution(tmp_path),
                     lambda: fd.record_calibration_run(tmp_path, first)):
            with pytest.raises(fd.StopImplementation, match=match):
                call()
        assert (tmp_path / fd.EXECUTION_FILE).read_bytes() == bad              # never rewritten
    (tmp_path / fd.EXECUTION_FILE).write_bytes(good)
    (tmp_path / "notes.txt").write_text("x")
    for call in (lambda: fd.record_calibration_run(tmp_path, first), lambda: fd.write_calibration(tmp_path, cal)):
        with pytest.raises(fd.StopImplementation, match="unexpected files in the calibration directory"):
            call()


def test_r3_same_evaluation_replay_once_with_fake_clock(monkeypatch):
    from dataclasses import replace
    from moneylab.research.v06 import montecarlo, synthetic
    protected = {"calibrate_edge": montecarlo.calibrate_edge, "_target_sharpe": montecarlo._target_sharpe,
                 "add_drift": synthetic.add_drift, "draw_noise": synthetic.draw_noise,
                 "strategy_signals": synthetic.strategy_signals, "Path": synthetic.Path}
    monkeypatch.setattr(fd, "_clock", FakeClock())
    calls, real = [], fd._replay_evaluation

    def counting(edge, noise, costs):                                          # our own helper, not an MC-V06 object
        calls.append((edge, noise))
        return real(edge, noise, costs)
    monkeypatch.setattr(fd, "_replay_evaluation", counting)
    parts = ("FUTDIAG-TEST", "calib-test")
    e1, times = fd.calibrate_e1_timed(3, parts)
    assert len(calls) == 1                                                     # exactly one replay
    edge, noise = calls[0]
    assert edge == e1["edge_annual"]
    assert noise.a == synthetic.draw_noise(fd.E1_DGP, 3 * 365, derived_seed(20261029, *parts)).a   # same noise
    # clock reads: 1 before draw_noise, 2 search start, 3 search end, 4 / 5 around the replay, 6 after the post step
    assert times == {"e1_noise_s": 1.0, "e1_search_s": 1.0, "e1_post_s": 1.0,
                     "v4_eval_time_estimate": _v4_estimate(1.0)}
    s = montecarlo._target_sharpe(synthetic.Path(*synthetic.add_drift(replace(fd.E1_DGP, edge_annual=edge), noise)),
                                  "M60", "E0", Costs().log_costs())
    assert (s - 0.7) + 0.7 == e1["achieved_sharpe"]                            # MC-V06 arithmetic, no tolerance
    assert {"calibrate_edge": montecarlo.calibrate_edge, "_target_sharpe": montecarlo._target_sharpe,
            "add_drift": synthetic.add_drift, "draw_noise": synthetic.draw_noise,
            "strategy_signals": synthetic.strategy_signals, "Path": synthetic.Path} == protected
    assert all(protected[k] is v for k, v in (("calibrate_edge", montecarlo.calibrate_edge),
                                              ("_target_sharpe", montecarlo._target_sharpe),
                                              ("add_drift", synthetic.add_drift)))
    assert fd._target_sharpe is montecarlo._target_sharpe and fd.calibrate_edge is montecarlo.calibrate_edge


def test_r3_replay_mismatch_stops(monkeypatch):
    real = fd._replay_evaluation
    monkeypatch.setattr(fd, "_replay_evaluation", lambda *a: math.nextafter(real(*a), 2.0))
    with pytest.raises(fd.StopImplementation, match="replayed evaluation does not reproduce"):
        fd.calibrate_e1_timed(3, ("FUTDIAG-TEST", "calib-test"))


def test_r3_v4_estimate_never_in_w():
    spec = _store_spec(mode="pilot", reps=4, unit_size=2)
    r_c = {"E1-theta0.7": 10_000, "P0-theta0.7": 10_000}
    ex = {"sessions": [_timed_session(spec)]}
    without, with_v4 = fd.g6_timing(ex, spec, r_c), fd.g6_timing(ex, spec, r_c, v4_eval_estimate_s=123.0)
    assert {k: v for k, v in with_v4.items() if not k.startswith("v4_")} == \
        {k: v for k, v in without.items() if not k.startswith("v4_")}
    assert (with_v4["v4_eval_estimate_s"], with_v4["v4_eval_estimate_kind"]) == (123.0, "ESTIMATE")


def test_r5_g7_manifest_section_and_g6_timing_revalidation(pilot, tmp_path):
    d0, spec, inputs, cal, sha, files = pilot
    d = tmp_path / "run"
    shutil.copytree(d0, d)
    fd.write_g6(d, cal, sha)
    recorded = json.loads(fd.canonical_bytes(fd.write_g6_timing(d, workers_required=1)))
    section = fd.g7_manifest_g6_section(d)
    raw = (d / "g6" / "g6_summary.json").read_bytes()
    assert section["g6_summary_sha256"] == hashlib.sha256(raw).hexdigest() and section["unit_size"] == 3
    assert section["pilot"]["manifest_sha256"] == hashlib.sha256(files["manifest.json"]).hexdigest()
    assert section["r_c_inputs"]["hypotheses"]["V-1"].keys() == {"x_lo", "x_hi", "x_disc"}
    assert not set(fd.TIME_KEYS) & set(_keys(section))                         # no time value of any kind
    ex_sha = hashlib.sha256((d / fd.EXECUTION_FILE).read_bytes()).hexdigest()
    assert ex_sha.encode() not in fd.canonical_bytes(section)                  # no execution.json content hash
    assert section["g6_timing_reference"] == {"file": "execution.json", "key": "g6_timing"}
    assert fd.revalidate_g6_timing(d, workers_required=1) == recorded
    original = (d / fd.EXECUTION_FILE).read_bytes()
    ex = json.loads(original)
    (d / fd.EXECUTION_FILE).write_bytes(fd.canonical_bytes({**ex, "g6_timing": {**ex["g6_timing"], "eta_hat": 0.5}}))
    with pytest.raises(fd.StopImplementation, match="differs from the recorded one"):
        fd.revalidate_g6_timing(d, workers_required=1)
    (d / fd.EXECUTION_FILE).write_bytes(fd.canonical_bytes({k: v for k, v in ex.items() if k != "g6_timing"}))
    with pytest.raises(fd.StopImplementation, match="no g6_timing"):
        fd.revalidate_g6_timing(d, workers_required=1)
    (d / fd.EXECUTION_FILE).write_bytes(original)
    fd.run_units(d, spec, inputs)                                              # execution.json changes ...
    assert fd.canonical_bytes(fd.g7_manifest_g6_section(d)) == fd.canonical_bytes(section)   # ... the section not


def _run(spec, *walls, open_last=False, tag="r"):
    """One session per wall value; session i completed unit i only (a resumed run never re-records a unit)."""
    sessions = []
    for i, w in enumerate(walls):
        base = _timed_session(spec, t_wall=w, end=not (open_last and i == len(walls) - 1))
        sessions.append({**base, "started_utc": f"{tag}{i}", "units": [{**base["units"][0], "unit": i}]})
    return {"sessions": sessions}


def test_r6_core_global_budget(tmp_path):
    spec = _store_spec(reps=4, unit_size=2)
    timing = {"worker_hours": 12.0, "eta_hat": 1.0}                            # expected wall = 12 / (12 x 1) h
    e1, p0 = ["E1-theta0.7"], ["P0-theta0.7"]
    assert fd.g6_expected_wall_s(timing) == 3600.0
    ok = fd.core_global_budget({"E1": (e1, _run(spec, 2000.0, 700.0, tag="e")), "P0": (p0, _run(spec, 2700.0))},
                               timing, [6, 6])
    assert ok["t_core_cumulative_s"] == 5400.0 == ok["limit_s"]                # two cells, resumed session added
    assert not ok["exceeded"] and ok["budget_pass_allowed"]                    # exactly 1.5 x passes
    fd.g7_budget_gate(ok)
    over = fd.core_global_budget({"E1": (e1, _run(spec, 2700.0, tag="e")),
                                  "P0": (p0, _run(spec, math.nextafter(5400.0, 6000.0) - 2700.0))}, timing, [12])
    assert over["t_core_cumulative_s"] == math.nextafter(5400.0, 6000.0)       # one float above 1.5 x
    assert over["exceeded"] and not over["budget_pass_allowed"]
    with pytest.raises(fd.StopImplementation, match="CORE global wall-clock"):
        fd.g7_budget_gate(over)
    single = fd.core_global_budget({"core": (list(fd.CORE_CELLS), _run(spec, 100.0))}, timing, [12])
    assert single["t_core_cumulative_s"] == 100.0                              # one run for both cells also works
    partial = fd.core_global_budget({"E1": (e1, _run(spec, 100.0, 50.0, open_last=True, tag="e")),
                                     "P0": (p0, None)}, timing, [12])
    assert partial["lower_bound"] and not partial["budget_pass_allowed"] and partial["t_core_cumulative_s"] == 150.0
    with pytest.raises(fd.StopForUserDecision, match="TIME_ACCOUNTING_INCOMPLETE"):
        fd.g7_budget_gate(partial)                                             # incomplete time: no PASS
    with pytest.raises(fd.StopForUserDecision, match="not wired"):
        fd.g7_budget_gate(None)
    shared = _run(spec, 100.0, tag="same")
    with pytest.raises(fd.StopImplementation, match="counted twice"):
        fd.core_global_budget({"E1": (e1, shared), "P0": (p0, shared)}, timing, [12])
    for workers in ([8, 6], [13], [6, 0]):
        with pytest.raises(fd.StopImplementation, match="concurrent CORE workers"):
            fd.core_global_budget({"core": (list(fd.CORE_CELLS), None)}, timing, workers)
    for runs in ({"E1": (e1, None)}, {"E1": (e1, None), "P0": (p0, None), "again": (e1, None)},
                 {"core": (list(fd.CORE_CELLS), None), "V-4": ([], _run(spec, 9.0, tag="v"))}):
        with pytest.raises(fd.StopImplementation):
            fd.core_global_budget(runs, timing, [12])


# --- G3b-5-3A: entry point smoke / verify (small fixture parameters only; not the G4c run) ---------------------------

SMALL = ["--reps", "3", "--bootstrap", "9", "--sigma-reps", "3", "--unit-size", "2"]
S1, C1 = "g4c-smoke-111111111111", "g4c-cal-111111111111"       # ERRATA-005 R-7 names for the fake HEAD 1 x 40


def _out_root(tmp_path, name="research_v06_futility_diag"):
    root = tmp_path / name
    root.mkdir()
    return root.resolve()


def _cli(argv, root, capsys):
    code = fd.main([str(a) for a in argv], output_root=root, git=_fake_git())
    return code, json.loads(capsys.readouterr().out)


def _snapshot(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns) if p.is_file() else None
            for p in sorted(root.rglob("*"))}


def _make_link(target, link):
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        try:
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
        except (ImportError, OSError):
            pytest.skip("cannot create a symlink or junction here")


@pytest.fixture(scope="module")
def smoked(tmp_path_factory):
    import io
    import contextlib
    root = _out_root(tmp_path_factory.mktemp("smoke"))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fd.main(["smoke", "--run", str(root / S1), "--calibration", str(root / C1), *SMALL],
                       output_root=root, git=_fake_git())
    assert code == 0, buf.getvalue()
    return root, _files(root / S1), (root / C1 / fd.CALIBRATION_FILE).read_bytes(), json.loads(buf.getvalue())


def test_entry_commands_and_arguments(tmp_path, capsys):
    root = _out_root(tmp_path)
    r, c = str(root / "r"), str(root / "c")
    for argv in ([], ["calibrate"], ["pilot"], ["summarize"], ["core"], ["decision"], ["g7"], ["g8a"],
                 ["smoke"], ["smoke", "--run", r], ["smoke", "--run", r, "--calibration", c],    # no --unit-size
                 ["smoke", "--run", r, "--calibration", c, "--unit-size", "x"], ["verify"],
                 ["smoke", "--run", r, "--calibration", c, *SMALL, "--namespace", "FUTDIAG"],   # no research path
                 ["smoke", "--run", r, "--calibration", c, *SMALL, "--provenance", "RESEARCH"],
                 ["verify", "--run", r, "--extra"]):
        with pytest.raises(SystemExit) as exc:
            fd.main(argv, output_root=root, git=_fake_git())
        assert exc.value.code == 2
    capsys.readouterr()
    assert list(root.iterdir()) == []                                          # nothing written
    code, out = _cli(["smoke", "--run", r, "--calibration", c, *SMALL, "--workers", "13"], root, capsys)
    assert (code, out["result"]) == (2, "STOP") and "workers" in out["reason"]
    code, out = _cli(["smoke", "--run", r, "--calibration", r, *SMALL], root, capsys)
    assert (code, out["result"]) == (2, "STOP")


def test_entry_output_path_boundary(tmp_path, capsys):
    root = _out_root(tmp_path)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    bad = ["relative_run", f"{root}/../escape", f"{root}/./x", f"{root}\\..\\escape", str(root / "a" / "b"),
           str(outside / "run"), str(root), str(root / ".hidden"), str(root / "bad name")]
    for path in bad:
        code, out = _cli(["smoke", "--run", path, "--calibration", str(root / "c"), *SMALL], root, capsys)
        assert (code, out["result"]) == (2, "STOP"), path
        code, out = _cli(["verify", "--run", path], root, capsys)
        assert (code, out["result"]) == (2, "STOP"), path
    code, out = _cli(["verify", "--run", str(root / "missing")], root, capsys)
    assert (code, out["result"]) == (2, "STOP")
    assert list(root.iterdir()) == [] and list(outside.iterdir()) == []      # nothing created anywhere
    target = tmp_path / "target"
    target.mkdir()
    _make_link(target, root / "link")
    for argv in (["smoke", "--run", str(root / "link"), "--calibration", str(root / "c"), *SMALL],
                 ["verify", "--run", str(root / "link")]):
        code, out = _cli(argv, root, capsys)
        assert (code, out["result"]) == (2, "STOP") and "symlink or junction" in out["reason"]
    assert list(target.iterdir()) == []
    link_root = tmp_path / "root_link"
    _make_link(root, link_root)
    code, out = _cli(["verify", "--run", str(link_root / "x")], link_root, capsys)
    assert (code, out["result"]) == (2, "STOP")


def test_entry_smoke_fixture_reproducible_and_never_overwrites(smoked, tmp_path, capsys):
    root0, files, cal_raw, out0 = smoked
    contracts = {k: hashlib.sha256((fd.repo_root() / rel).read_bytes()).hexdigest()
                 for k, rel in fd.CONTRACT_FILES.items()}
    mcv = source_identity()
    assert out0["status"] == "COMPLETE" and out0["verify"]["time_accounting"] == "COMPLETE"
    spec, inputs = json.loads(files["run_spec.json"]), json.loads(files["run_inputs.json"])
    assert (spec["mode"], spec["reps"], spec["bootstrap"], spec["unit_size"]) == ("core", 3, 9, 2)
    assert spec["cells"] == list(fd.CORE_CELLS) and spec["windows"] == list(fd.WINDOWS)
    assert (spec["code_sha"], spec["config_sha256"]) == ("1" * 40, fd.CONTRACT_SHA256["config"])
    assert inputs["namespace"] == "FUTDIAG-TEST" and inputs["calibration_provenance"]["kind"] == fd.TEST_FIXTURE
    assert out0["calibration_sha256"] == hashlib.sha256(cal_raw).hexdigest()
    assert json.loads(cal_raw)["sigma"]["namespace"] == "FUTDIAG-TEST" and json.loads(cal_raw)["sigma"]["reps"] == 3
    root = _out_root(tmp_path)
    shutil.copytree(root0 / S1, root / S1)
    shutil.copytree(root0 / C1, root / C1)
    code, out = _cli(["smoke", "--run", root / S1, "--calibration", root / C1, *SMALL], root, capsys)
    assert code == 0 and out["run_units"]["reused"] == 4 and out["run_units"]["computed"] == 0   # 2 cells x 2 units
    assert _files(root / S1) == files and (root / C1 / fd.CALIBRATION_FILE).read_bytes() == cal_raw
    assert len(fd.read_calibration_execution(root / C1)["runs"]) == 2
    assert len(fd.read_execution(root / S1)["sessions"]) == 2
    root2 = _out_root(tmp_path, "fresh")
    code, out = _cli(["smoke", "--run", root2 / S1, "--calibration", root2 / C1, *SMALL], root2, capsys)
    assert code == 0 and _files(root2 / S1) == files                          # fresh directories: same bytes
    assert (root2 / C1 / fd.CALIBRATION_FILE).read_bytes() == cal_raw
    root3 = _out_root(tmp_path, "cal_only")
    shutil.copytree(root0 / C1, root3 / C1)
    before = {**_snapshot(root), **{f"3/{k}": v for k, v in _snapshot(root3).items()}}
    code, out = _cli(["smoke", "--run", root / S1, "--calibration", root / C1, "--reps", "4", "--bootstrap", "9",
                      "--sigma-reps", "3", "--unit-size", "2"], root, capsys)
    assert (code, out["result"]) == (2, "STOP") and "run_spec differs" in out["reason"]
    code, out = _cli(["smoke", "--run", root3 / S1, "--calibration", root3 / C1, "--reps", "3", "--bootstrap", "9",
                      "--sigma-reps", "4", "--unit-size", "2"], root3, capsys)
    assert (code, out["result"]) == (2, "STOP") and "refusing to change" in out["reason"]
    after = {**_snapshot(root), **{f"3/{k}": v for k, v in _snapshot(root3).items()}}
    assert {k: v for k, v in after.items() if k in before} == before          # nothing existing was changed
    for bad in ("s1", "g4c-smoke-222222222222", "g4c-smoke-111111111111-attempt2", "g5-pilot-111111111111"):
        code, out = _cli(["smoke", "--run", root2 / bad, "--calibration", root2 / C1, *SMALL], root2, capsys)
        assert (code, out["result"]) in ((2, "STOP"), (3, "STOP_FOR_USER_DECISION")), bad   # R-7 names only
    assert {k: hashlib.sha256((fd.repo_root() / rel).read_bytes()).hexdigest()
            for k, rel in fd.CONTRACT_FILES.items()} == contracts == fd.CONTRACT_SHA256
    assert source_identity() == mcv


def test_entry_verify_read_only_states(smoked, pilot, tmp_path, capsys):
    root0 = smoked[0]
    root = _out_root(tmp_path)
    for name in ("ok", "inc", "bad", "exb"):
        shutil.copytree(root0 / S1, root / name)
    before = _snapshot(root)
    code, out = _cli(["verify", "--run", root / "ok"], root, capsys)
    assert code == 0 and (out["status"], out["unit_status"], out["time_accounting"], out["g6"]) == \
        ("COMPLETE", "COMPLETE", "COMPLETE", "ABSENT")
    assert _snapshot(root) == before                                           # read-only (bytes and mtimes)
    for p in fd.unit_paths(root / "inc", "P0-theta0.7", 1):
        p.unlink()
    (root / "inc" / fd.MANIFEST_FILE).unlink()
    (root / "inc" / fd.SUMS_FILE).unlink()
    code, out = _cli(["verify", "--run", root / "inc"], root, capsys)
    assert code == 1 and (out["status"], out["unit_status"]) == ("INCOMPLETE", "INCOMPLETE")
    sums = root / "bad" / fd.SUMS_FILE
    sums.write_bytes(sums.read_bytes().replace(b"run_spec.json", b"run_spec.jsonx"))
    (root / "exb" / fd.EXECUTION_FILE).write_bytes(b"{")
    for name, match in (("bad", "SHA256SUMS"), ("exb", "malformed")):
        snap = _snapshot(root / name)
        code, out = _cli(["verify", "--run", root / name], root, capsys)
        assert (code, out["result"]) == (2, "STOP") and match in out["reason"]
        assert _snapshot(root / name) == snap                                  # never repaired
    d0, spec, inputs, cal, sha, files = pilot
    shutil.copytree(d0, root / "pilot")
    fd.write_g6(root / "pilot", cal, sha)
    code, out = _cli(["verify", "--run", root / "pilot"], root, capsys)
    assert code == 0 and out["g6"] == "VERIFIED"
    summ = root / "pilot" / "g6" / "g6_summary.json"
    summ.write_bytes(summ.read_bytes().replace(b'"reps":6', b'"reps":7', 1))
    code, out = _cli(["verify", "--run", root / "pilot"], root, capsys)
    assert (code, out["result"]) == (2, "STOP") and "g6" in out["reason"]


def test_research_inputs_namespace_and_calibration():
    """ERRATA-005 [C]: RESEARCH provenance only as (pilot, FUTDIAG-PILOT) or (core, FUTDIAG), naming the E1 cell's
    calibration values; never in FUTDIAG-TEST."""
    prov = {"kind": fd.RESEARCH, "calibration_sha256": "e" * 64, "edge_annual": 0.73, "sigma_pop": E1.sigma_pop}
    for mode, ns in (("pilot", "FUTDIAG-PILOT"), ("core", "FUTDIAG")):
        assert _inputs(_store_spec(mode=mode), namespace=ns, provenance=prov)["calibration_provenance"] == prov
    for mode, ns, p in (("core", "FUTDIAG-TEST", prov), ("pilot", "FUTDIAG", prov), ("core", "FUTDIAG-PILOT", prov),
                        ("core", "FUTDIAG", {**prov, "edge_annual": 0.74}),
                        ("core", "FUTDIAG", {**prov, "calibration_sha256": "e" * 63}),
                        ("core", "FUTDIAG", {**prov, "extra": 1}), ("core", "FUTDIAG", {"kind": fd.RESEARCH})):
        with pytest.raises(fd.StopImplementation):
            _inputs(_store_spec(mode=mode), namespace=ns, provenance=p)
    helptext = fd._parser().format_help()
    assert all(c in helptext for c in ("calibrate", "pilot", "summarize", "g7", "g8a", "udr", "lock-abandon"))


# --- ERRATA-005 [C] (G3): FAKE tests run light. IT groups A-D and RB-1 run only after their own execution approval
# (FUTDIAG_IT_GROUP=A|B|C|D, FUTDIAG_RB1=1, ERRATA-005 R-9); by default nothing here starts a process, pool or job.

IT_GROUP = os.environ.get("FUTDIAG_IT_GROUP", "")
ON_WINDOWS = sys.platform == "win32"


def _it_group(group, windows=True):
    return pytest.mark.skipif(IT_GROUP != group or (windows and not ON_WINDOWS),
                              reason=f"IT group {group}: separately approved execution only (ERRATA-005 R-9)")


it_group_a, it_group_b, it_group_c = _it_group("A"), _it_group("B"), _it_group("C")
it_group_d = _it_group("D", windows=False)
rb1_check = pytest.mark.skipif(os.environ.get("FUTDIAG_RB1") != "1" or not ON_WINDOWS,
                               reason="RB-1: separately approved read-only check (ERRATA-005 R-9)")
SHA12, CODE = "1" * 12, "1" * 40              # the fake HEAD of _fake_git
TS = 134 * 10 ** 15                            # a FILETIME value in 2025 (100 ns units since 1601)
SEC = 10_000_000                               # one second in FILETIME units


class _FakeApi:
    """The Windows API stand-in of the FAKE tests: processes (pid -> creation time), parents, target-job members,
    job flags and boot readings. No real process, job or handle exists."""

    def __init__(self, s1=TS, now=TS + 3600 * SEC, host=("HOST", "guid-1")):
        self.driver_pid, self.driver_ct = 100, 5_000
        self.procs, self.parent = {100: 5_000}, {100: 1}
        self.members, self.extra_job_pids, self.fail, self.ct_fail = set(), [], set(), set()
        self.exited_set, self.wait_fail, self.sync_denied = set(), set(), set()
        self.job, self.flags, self.inherit, self.assigned = 77, fd.JOB_KILL_ON_CLOSE, False, False
        self.host, self.s1, self.now = host, s1, now
        self.tick_ms = (now - s1) // 10_000

    def add_worker(self, pid, ct=None, parent=None, member=True):
        self.procs[pid] = self.driver_ct + pid if ct is None else ct
        self.parent[pid] = self.driver_pid if parent is None else parent
        if member:
            self.members.add(pid)
        return pid, self.procs[pid]

    def job_create(self):
        return self.job

    def inheritable(self, handle):
        return self.inherit

    def job_set_kill_on_close(self, job):
        pass

    def job_limit_flags(self, job):
        return self.flags

    def assign_current(self, job):
        if "assign" in self.fail:
            raise fd.StopImplementation("AssignProcessToJobObject failed")
        self.assigned = True

    def in_job(self, handle, job):
        if handle is None:
            return self.assigned if job is not None else True
        return handle in self.members

    def job_pids(self, job):
        return [self.driver_pid, *sorted(self.members), *self.extra_job_pids]

    def open_process(self, pid):
        if pid in self.fail or pid in self.sync_denied:                      # query or SYNCHRONIZE right refused
            raise fd.ProcessOpenError(pid, 5)                                 # ERROR_ACCESS_DENIED
        if pid not in self.procs:
            raise fd.ProcessOpenError(pid, 87)                                # ERROR_INVALID_PARAMETER
        return pid

    def close(self, handle):
        pass

    def exited(self, handle):
        if handle in self.wait_fail:
            raise fd.StopImplementation("WaitForSingleObject returned 0xffffffff")   # WAIT_FAILED
        return handle in self.exited_set

    def creation_time(self, handle):
        if handle in self.ct_fail:
            raise fd.StopImplementation("GetProcessTimes failed")
        return self.driver_ct if handle is None else self.procs[handle]

    def snapshot(self):
        return dict(self.parent)

    def computer_name(self):
        if "host" in self.fail:
            raise fd.StopImplementation("GetComputerNameExW failed")
        return self.host[0]

    def machine_guid(self):
        return self.host[1]

    def boot_time_s1(self):
        return self.s1

    def now_and_tick(self):
        return self.now, self.tick_ms


class _LazyFuture:
    def __init__(self, fn, arg, release):
        self.fn, self.arg, self.release = fn, arg, release

    def result(self):
        assert self.release.is_set(), "a result was read before the release"
        return self.fn(self.arg)


class _FakeExecutor:
    """ProcessPoolExecutor stand-in: one fake worker per submit up to max_workers (the 3.14.8 behaviour), reporting
    (pid, creation time) through the initializer's ready queue unless silent. No process is created."""

    def __init__(self, api, silent=False, extra=None, *, max_workers, mp_context, initializer, initargs):
        self.api, self.n, self.silent, self.extra = api, max_workers, silent, extra
        self.ready, self.release, _ = initargs
        self.workers = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, fn, arg):
        if len(self.workers) < self.n:
            w = self.api.add_worker(1000 + len(self.workers))
            self.workers.append(w)
            if not self.silent:
                self.ready.put(w)
            if self.extra is not None and len(self.workers) == 1:
                self.ready.put(self.extra)
        return _LazyFuture(fn, arg, self.release)


class _FakeCtx:
    def Queue(self):
        return queue.Queue()

    def Event(self):
        return threading.Event()


def _env(api, base, io=fd.REAL_IO, **executor_kw):
    d = base / "records"
    d.mkdir(parents=True, exist_ok=True)
    return fd.BarrierEnv(api=api, job=api.job, record_dir=d, lock_number=1, lock_sha256="a" * 64,
                         driver_pid=api.driver_pid, driver_creation_time=api.driver_ct,
                         run_id=f"g7-E1-theta0.7-{SHA12}", ready_timeout_s=0.05, context=_FakeCtx(), io=io,
                         events=[], executor_factory=lambda **kw: _FakeExecutor(api, **executor_kw, **kw))


def _double(x):
    return 2 * x


def _oserror(*args):
    raise OSError("injected")


def _udr_line(n, kind, target, decision):
    return f"USER_DECISION: BT4-FUTILITY-01 UDR#{n:06d} {kind} {target} {decision}"


def _lock(api, code=CODE):
    return fd.lock_content(api=api, code_sha=code, run_ids=[f"g7-E1-theta0.7-{SHA12}"], prior_job_membership=True,
                           job_policy_readback=True, driver_creation_time=api.driver_ct)


def _lock_bytes(api, n, **over):
    """Canonical bytes of a /2 lock file for number n (token {"lock_number": n}, ERRATA-006), fields overridable."""
    return fd.canonical_bytes({**_lock(api), "token": {"lock_number": n}, **over})


def _invalid_lock_variants(api, n):
    """ERRATA-006 T-6b: label -> (bytes, reason) of structurally invalid contents for an allowed name NNNNNN.lock."""
    good = _lock_bytes(api, n)
    bad, malformed = fd.LOCK_INVALID_CONTENT, fd.LOCK_MALFORMED
    return {"schema /1": (_lock_bytes(api, n, schema_version="moneylab.bt4_futility_diag.g7_lock/1"), bad),
            "string token": (_lock_bytes(api, n, token="ab" * 16), bad),
            "no token": (fd.canonical_bytes(_lock(api)), bad),
            "extra token key": (_lock_bytes(api, n, token={"lock_number": n, "x": 1}), bad),
            "bool": (_lock_bytes(api, n, token={"lock_number": True}), bad),
            "zero": (_lock_bytes(api, n, token={"lock_number": 0}), bad),
            "negative": (_lock_bytes(api, n, token={"lock_number": -1}), bad),
            "float": (_lock_bytes(api, n, token={"lock_number": float(n)}), bad),
            "other number": (_lock_bytes(api, n, token={"lock_number": n + 1}), bad),
            "extra field": (_lock_bytes(api, n, extra=1), bad),
            "empty": (b"", malformed),
            "partial": (good[:len(good) // 2], malformed),
            "not canonical": (good.replace(b",", b", ", 1), malformed)}


def _set_mtime(path, filetime):
    ns = (filetime - fd._FILETIME_UNIX_EPOCH) * 100
    os.utime(path, ns=(ns, ns))


def test_exclusive_create_writes_once_and_never_overwrites(tmp_path):
    p = tmp_path / "rec"
    one_byte = fd.ExclusiveIO(writer=lambda handle, view: os.write(handle, bytes(view[:1])))
    assert fd.create_exclusive(p, b"abc", one_byte) == hashlib.sha256(b"abc").hexdigest()
    assert p.read_bytes() == b"abc"                                           # every byte, over several writes
    with pytest.raises(fd.StopImplementation, match="already exists"):
        fd.create_exclusive(p, b"zzz")
    assert p.read_bytes() == b"abc"


def test_udr_record_parse_and_verification(tmp_path):
    """AC-0: one approval line, one file, the next number; kind / target / decision checked; reuse, summary targets
    and damage STOP; a UDR names one full target only."""
    g6 = "a" * 64
    line = _udr_line(1, "PD5_PROCEED", f"g6={g6}", "PROCEED")
    path, sha = fd.write_udr(tmp_path, f"승인합니다\n{line}\n", "user's reason", CODE)
    assert path.name == "000001-PD5_PROCEED.json" and path.parent.name == fd.UDR_DIR
    udr, sha2 = fd.load_udr(path)
    assert sha2 == sha == hashlib.sha256(path.read_bytes()).hexdigest()
    assert (udr["approval_text"], udr["target"], udr["approved_by"], udr["recorded_by"]) == \
        (line, {"g6": g6}, "USER", "CLAUDE")
    assert udr["approval_text_sha256"] == hashlib.sha256(line.encode()).hexdigest()
    assert fd.find_udr(tmp_path, [1], "PD5_PROCEED", {"g6": g6}) == sha
    assert fd.find_udr(tmp_path, [1], "PD5_PROCEED", {"g6": "b" * 64}) is None      # never another target
    fd.recheck_udrs(tmp_path, [sha])
    attempt = f"new=g7-v4-{SHA12}-attempt2,prev=g7-v4-{SHA12},reason=ABNORMAL_TERMINATION"
    for text, match in ((line, "not the next number"),
                        (_udr_line(3, "PD5_PROCEED", f"g6={g6}", "PROCEED"), "not the next number"),
                        (_udr_line(2, "PD5_PROCEED", "g6=aaaa", "PROCEED"), "full values only"),
                        (_udr_line(2, "PD5_PROCEED", f"g6={g6}", "RESUME"), "decision"),
                        (_udr_line(2, "LOCK_ABANDON", f"lock=1,lock_sha256={g6}", "ABANDON"), "full values only"),
                        (_udr_line(2, "ATTEMPT", "prev=x,new=y,reason=ABNORMAL_TERMINATION", "NEW_ATTEMPT"), "R-7"),
                        (_udr_line(2, "ATTEMPT", attempt, "NEW_ATTEMPT"), "target must be"),
                        (_udr_line(2, "PASS_BUDGET", f"g6={g6}", "PROCEED"), "format / kind"),
                        (line.replace(" PROCEED", "  PROCEED"), "format"),
                        (f"{line}\n{line}", "exactly one"), ("no decision here", "exactly one")):
        with pytest.raises(fd.StopImplementation, match=match):
            fd.write_udr(tmp_path, text, "r", CODE)
    with pytest.raises(fd.StopImplementation, match="40 hex"):
        fd.write_udr(tmp_path, _udr_line(2, "PD5_PROCEED", f"g6={g6}", "PROCEED"), "r", "HEAD")
    assert [p.name for p in (tmp_path / fd.UDR_DIR).iterdir()] == ["000001-PD5_PROCEED.json"]   # nothing else
    raw = path.read_bytes()
    path.write_bytes(raw.replace(g6.encode(), b"b" * 64, 1))                  # damage: no longer its approval line
    with pytest.raises(fd.StopImplementation):
        fd.load_udr(path)
    with pytest.raises(fd.StopImplementation):
        fd.recheck_udrs(tmp_path, [sha])
    path.write_bytes(raw)
    (tmp_path / fd.UDR_DIR / "notes.txt").write_text("x")
    with pytest.raises(fd.StopImplementation, match="unexpected entry"):
        fd.find_udr(tmp_path, [1], "PD5_PROCEED", {"g6": g6})


def test_udr_command_records_the_line(tmp_path, capsys):
    root = _out_root(tmp_path)
    line = _udr_line(1, "PD5_PROCEED", f"g6={'c' * 64}", "PROCEED")
    code, out = _cli(["udr", "--line", line, "--reason", "PD-5 accepted"], root, capsys)
    assert code == 0 and out["udr"] == "000001-PD5_PROCEED.json"
    assert fd.load_udr(root / fd.UDR_DIR / out["udr"])[0]["code_sha"] == CODE
    code, out = _cli(["udr", "--line", line, "--reason", "again"], root, capsys)
    assert (code, out["result"]) == (2, "STOP")                                # one line, one record


def test_run_names_and_attempt_udr(tmp_path):
    """AC-7: R-7 names; attempt k >= 2 only after attempt k - 1 and with an ATTEMPT UDR; nothing automatic."""
    assert fd.run_id("g7", "E1-theta0.7", CODE) == f"g7-E1-theta0.7-{SHA12}"
    assert fd.run_id("g8a", None, CODE, 3) == f"g8a-{SHA12}-attempt3"
    assert fd.parse_run_id(f"g5-pilot-{SHA12}-attempt2") == ("g5", "pilot", SHA12, 2)
    for bad in (f"g7-E1-theta0.7-{SHA12[:11]}", f"g7-pilot-{SHA12}", f"g8a-v4-{SHA12}", f"g7-v4-{SHA12}-attempt1",
                f"g5-cal-{SHA12}-attempt0", "s1", f"g7-E1-theta0.7-{SHA12}/x"):
        with pytest.raises(fd.StopImplementation):
            fd.parse_run_id(bad)
    assert fd.check_run_name(tmp_path, f"g5-pilot-{SHA12}", "g5", "pilot", CODE) == \
        {"attempt": 1, "udr_sha256": None}
    for name, stage, part in ((f"g5-pilot-{SHA12}", "g5", "cal"), (f"g5-pilot-{'2' * 12}", "g5", "pilot")):
        with pytest.raises(fd.StopImplementation):
            fd.check_run_name(tmp_path, name, stage, part, CODE)
    new = f"g7-v4-{SHA12}-attempt2"
    with pytest.raises(fd.StopImplementation, match="needs attempt 1"):
        fd.check_run_name(tmp_path, new, "g7", "v4", CODE)
    (tmp_path / f"g7-v4-{SHA12}").mkdir()
    with pytest.raises(fd.StopForUserDecision, match="no ATTEMPT UDR"):
        fd.check_run_name(tmp_path, new, "g7", "v4", CODE)
    _, sha = fd.write_udr(tmp_path, _udr_line(1, "ATTEMPT", f"prev=g7-v4-{SHA12},new={new},reason=ABNORMAL_TERMINATION",
                                              "NEW_ATTEMPT"), "crash", CODE)
    with pytest.raises(fd.StopForUserDecision):
        fd.check_run_name(tmp_path, new, "g7", "v4", CODE)                    # the UDR number must be given
    assert fd.check_run_name(tmp_path, new, "g7", "v4", CODE, [1]) == \
        {"attempt": 2, "udr_sha256": sha, "reason": "ABNORMAL_TERMINATION"}
    with pytest.raises(fd.StopImplementation, match="needs attempt 2"):
        fd.check_run_name(tmp_path, f"g7-v4-{SHA12}-attempt3", "g7", "v4", CODE, [1])   # no skipping
    (tmp_path / new).mkdir()
    assert [p.name for p in fd.attempt_dirs(tmp_path, "g7", "v4", CODE)] == [f"g7-v4-{SHA12}", new]


def test_p0_conf_check_boundaries():
    """AC-8 (R-8 [B-STAT]): |p_hat - 0.05| <= 3 sqrt(0.05 x 0.95 / n) is PASS (boundary PASS), else STOP; only the
    label leaves the function."""
    def by_cell(n, x):
        return {"P0-theta0.7": [_srec("P0-theta0.7", i, "conf", v0=_rej(i < x)) for i in range(n)]}
    limit = 3 * math.sqrt(0.05 * 0.95 / 200)
    for x in range(30):
        assert fd.p0_conf_check(by_cell(200, x), 200) == ("PASS" if abs(x / 200 - 0.05) <= limit else "STOP")
    assert [fd.p0_conf_check(by_cell(200, x), 200) for x in (0, 1, 19, 20)] == ["STOP", "PASS", "PASS", "STOP"]
    with pytest.raises(fd.StopImplementation, match="required records missing"):
        fd.p0_conf_check(by_cell(199, 3), 200)


def test_g6_summary_p0_conf_label_only(pilot, tmp_path):
    d0, spec, inputs, cal, sha, files = pilot
    d = tmp_path / "pilot"
    shutil.copytree(d0, d)
    summary = fd.write_g6(d, cal, sha)
    assert summary["P0_CONF_CHECK"] in ("PASS", "STOP") and tuple(sorted(summary)) == tuple(sorted(fd.G6_FIELDS))
    assert not {"p_hat", "rate", "p0_conf_rate"} & set(_keys(summary))       # the label, never the rate
    assert fd.verify_run(d)["g6"] == "VERIFIED"


@pytest.fixture(scope="module")
def research_cal():
    cal = fd.build_calibration(fd.RESEARCH, *_research_parts(), fd.research_identity(git=_fake_git()))
    return cal, hashlib.sha256(fd.calibration_bytes(cal)).hexdigest()


def test_research_pilot_manifest_block_and_verify(research_cal, tmp_path):
    """O-1 / O-2: a RESEARCH run writes its research block (calibration values, A1-c report; a pilot has no G6 and
    no UDR); verify_run rechecks it; a research CORE run without the lock handle STOPs before writing anything."""
    cal, sha = research_cal
    spec = _store_spec(mode="pilot", reps=2, unit_size=2)
    inputs = fd.build_run_inputs(spec, [fd.research_e1_cell(cal), P0], "FUTDIAG-PILOT",
                                 fd.calibration_provenance(cal, sha))
    block = fd.research_block(spec, inputs, cal, sha, None, [])
    assert block["calibration"]["sha256"] == sha and block["calibration"]["sigma"]["reps"] == 2000
    a1c = block["seed_collisions"]
    assert a1c["policy"] == "report_only" and a1c["n_paths"] == 2 * 2 * 3 + 2000
    assert [e["parts"] for e in a1c["explicit"]] == [list(fd.E1_CALIB_SEED_PARTS), list(fd.V4_EVAL_SEED_PARTS)]
    with pytest.raises(fd.StopImplementation, match="research block"):
        fd.run_units(tmp_path / "x", spec, inputs)
    assert not (tmp_path / "x").exists()
    d = tmp_path / "run"
    fd.run_units(d, spec, inputs, research=block)
    manifest = json.loads((d / fd.MANIFEST_FILE).read_bytes())
    assert "pending_for_research_run" not in manifest and manifest["research"]["g6"] is None
    assert fd.verify_run(d)["status"] == "COMPLETE"
    for bad in ({**block, "g6": {"g6_summary_sha256": "x"}}, {**block, "udr_sha256": ["a" * 64]},
                {**block, "calibration": {**block["calibration"], "sha256": "f" * 64}},
                {k: v for k, v in block.items() if k != "g6"},
                {**block, "seed_collisions": {**a1c, "n_values": 1}}):
        with pytest.raises(fd.StopImplementation):
            fd.validate_research_block(spec, inputs, bad)
    raw = (d / fd.MANIFEST_FILE).read_bytes()
    (d / fd.MANIFEST_FILE).write_bytes(raw.replace(b'"policy":"report_only"', b'"policy":"report-only"'))
    with pytest.raises(fd.StopImplementation):
        fd.verify_run(d)
    core = _store_spec(mode="core", reps=2, unit_size=2, cells=["P0-theta0.7"])
    core_inputs = fd.build_run_inputs(core, [P0], "FUTDIAG", fd.calibration_provenance(cal, sha))
    core_block = fd.research_block(core, core_inputs, cal, sha, {"g6_summary_sha256": "c" * 64}, [])
    with pytest.raises(fd.StopImplementation, match="lock handle"):
        fd.run_units(tmp_path / "core", core, core_inputs, research=core_block)
    assert not (tmp_path / "core").exists()


def test_lock_acquire_ownership_release_and_abnormal_states(tmp_path):
    """AC-4: O_EXCL lock with host_id / boot identity / sys.version, one unpaired lock blocks the next driver, the
    ownership check, released kept with its lock, every abnormal directory state a STOP_FOR_USER_DECISION."""
    api = _FakeApi()
    content = _lock(api)                                     # ERRATA-006: the token is added at acquisition
    assert tuple(sorted(content)) == tuple(sorted(set(fd.LOCK_FIELDS) - {"token"})) and "token" not in content
    assert content["python_version"] == sys.version
    assert content["host_id"] == {"computer_name": "HOST", "machine_guid": "guid-1"} and "host" not in content
    h = fd.acquire_lock(tmp_path, content)
    lock_dir = tmp_path / fd.LOCK_DIR
    assert h.number == 1 and h.sha256 == fd.sha256_file(lock_dir / "000001.lock")
    assert fd.read_lock(lock_dir / "000001.lock") == {**content, "token": {"lock_number": 1}} == h.content
    h.check()
    with pytest.raises(fd.StopForUserDecision, match="not released"):
        fd.acquire_lock(tmp_path, _lock(api))
    rec = dict(run_id_="r", unit_id=["E1-theta0.7", 0, 2], driver_pid=100, driver_creation_time=5000)
    fd.write_pool_start(lock_dir, 1, h.sha256, 1, planned_max_workers=2, **rec)
    with pytest.raises(fd.StopImplementation, match="no record, no release"):
        fd.write_pool_workers(lock_dir, 1, h.sha256, 1, expected=2, workers=[(1000, 6000)], **rec)
    assert not (lock_dir / "000001.workers-000001").exists()
    fd.write_pool_workers(lock_dir, 1, h.sha256, 1, expected=2, workers=[(1000, 6000), (1001, 6001)], **rec)
    fd.scan_lock_dir(tmp_path)
    fd.release_lock(h)
    with pytest.raises(fd.StopForUserDecision, match="already released"):
        h.check()
    h2 = fd.acquire_lock(tmp_path, _lock(api))
    assert h2.number == 2 and (lock_dir / "000001.lock").exists()             # never deleted
    start_raw = (lock_dir / "000001.pool-000001.start").read_bytes()
    workers_raw = (lock_dir / "000001.workers-000001").read_bytes()
    lock_raw = (lock_dir / "000001.lock").read_bytes()
    lsha = hashlib.sha256(lock_raw).hexdigest()
    rel = fd.canonical_bytes({"lock": 1, "lock_sha256": lsha})
    other_workers = workers_raw.replace(b'"driver_pid":100', b'"driver_pid":101')
    other_start = start_raw.replace(b'"pool_id":1', b'"pool_id":2')
    for i, (files, match) in enumerate((
            ({"notes.txt": b"x"}, "allowed name"), ({"000001.pool-000001": b"x"}, "allowed name"),
            ({"000002.lock": lock_raw}, "gap"),
            ({"000001.lock": lock_raw, "000002.released": rel}, "without the lock"),
            ({"000001.lock": lock_raw, "000001.released": rel, "000001.abandoned": rel}, "both"),
            ({"000001.lock": lock_raw, "000001.released": fd.canonical_bytes({"lock_sha256": "0" * 64})},
             "not a record"),
            ({"000001.lock": lock_raw, "000001.abandoned": rel}, "UDR is missing"),
            ({"000001.lock": lock_raw, "000001.released": rel, "000002.lock": _lock_bytes(api, 2),
              "000003.lock": _lock_bytes(api, 3)}, "more than one unpaired"),        # valid /2 locks 2, 3 (ERRATA-006)
            ({"000001.lock": lock_raw, "000001.workers-000001": workers_raw}, "without its start"),
            ({"000001.lock": lock_raw, "000001.pool-000002.start": start_raw}, "gap"),
            ({"000001.lock": lock_raw, "000001.pool-000001.start": other_start}, "disagree"),
            ({"000001.lock": lock_raw, "000001.pool-000001.start": start_raw,
              "000001.workers-000001": other_workers}, "disagrees"))):
        root = tmp_path / f"state{i}"
        (root / fd.LOCK_DIR).mkdir(parents=True)
        for name, data in files.items():
            (root / fd.LOCK_DIR / name).write_bytes(data)
        with pytest.raises(fd.StopForUserDecision, match=match):
            fd.scan_lock_dir(root)


def test_errata006_lock_schema_token_bytes_and_released(tmp_path):
    """ERRATA-006 T-6a / T-6c / T-6d: the /2 schema and token {"lock_number": n} (an int, the file number) set at
    acquisition; the same input content gives different lock bytes for different numbers (only the token differs);
    n.released carries the lock's token; lock 1's released under lock 2 is not a record of lock 2."""
    api = _FakeApi()
    content = _lock(api)
    assert fd.LOCK_SCHEMA == "moneylab.bt4_futility_diag.g7_lock/2" and content["schema_version"] == fd.LOCK_SCHEMA
    with pytest.raises(fd.StopImplementation, match="token is set at acquisition"):
        fd.acquire_lock(tmp_path / "caller-token", {**content, "token": {"lock_number": 1}})
    assert not (tmp_path / "caller-token" / fd.LOCK_DIR).exists()
    d = tmp_path / fd.LOCK_DIR
    h1 = fd.acquire_lock(tmp_path, content)
    raw1 = (d / "000001.lock").read_bytes()
    lock1 = json.loads(raw1)
    assert lock1["schema_version"] == fd.LOCK_SCHEMA and lock1["token"] == {"lock_number": 1}
    assert type(lock1["token"]["lock_number"]) is int and set(lock1) == set(fd.LOCK_FIELDS)
    assert fd.read_lock(d / "000001.lock") == h1.content == lock1 and h1.token == {"lock_number": 1}
    assert fd.check_lock_structure(d / "000001.lock") == (lock1, None)
    fd.release_lock(h1)
    rel1 = (d / "000001.released").read_bytes()
    assert json.loads(rel1)["token"] == lock1["token"] and json.loads(rel1)["lock_sha256"] == h1.sha256
    h2 = fd.acquire_lock(tmp_path, content)                                   # the same input content
    raw2 = (d / "000002.lock").read_bytes()
    lock2 = json.loads(raw2)
    assert raw1 != raw2 and hashlib.sha256(raw1).hexdigest() != hashlib.sha256(raw2).hexdigest() != h1.sha256
    assert {k for k in lock1 if lock1[k] != lock2[k]} == {"token"} and lock2["token"] == {"lock_number": 2}
    assert h2.sha256 == hashlib.sha256(raw2).hexdigest() and h2.token == {"lock_number": 2}
    (d / "000002.released").write_bytes(rel1)                                 # lock 1's released under lock 2
    with pytest.raises(fd.StopForUserDecision, match="not a record"):
        fd.scan_lock_dir(tmp_path)


def test_errata006_structural_validity_variants(tmp_path, monkeypatch):
    """ERRATA-006 T-6b: check_lock_structure / read_lock reject every invalid variant with its reason (content, a
    malformed file, a name that is not NNNNNN.lock with n >= 1, an OSError while reading); the valid control passes."""
    api = _FakeApi()
    for i, (label, (data, reason)) in enumerate(_invalid_lock_variants(api, 1).items()):
        p = tmp_path / f"v{i}" / "000001.lock"
        p.parent.mkdir()
        p.write_bytes(data)
        assert fd.read_lock(p) is None and fd.check_lock_structure(p) == (None, reason), label
    for name in ("000001.lck", "1.lock", "000000.lock", "0000001.lock"):
        p = tmp_path / "names" / name
        p.parent.mkdir(exist_ok=True)
        p.write_bytes(_lock_bytes(api, 1))
        assert fd.check_lock_structure(p) == (None, fd.LOCK_BAD_NAME), name
    ok = tmp_path / "ok" / "000001.lock"
    ok.parent.mkdir()
    good = _lock_bytes(api, 1)
    ok.write_bytes(good)
    assert fd.check_lock_structure(ok) == (json.loads(good), None)
    real = fd._read_canonical

    def unreadable(path, what):
        if FsPath(path) == ok:
            raise PermissionError("read denied (test)")
        return real(path, what)
    monkeypatch.setattr(fd, "_read_canonical", unreadable)
    assert fd.check_lock_structure(ok) == (None, fd.LOCK_READ_FAILED) and fd.read_lock(ok) is None


def test_errata006_scan_rule_ownership_and_investigation(tmp_path, monkeypatch):
    """ERRATA-006 T-6e: a structurally invalid lock, paired or not, stops the directory check, the next acquisition
    and abandon (STOP_FOR_USER_DECISION, nothing written); a paired /1 lock blocks the next number; LockHandle.check
    finds an invalid other lock after its own three checks, and a changed or missing own lock never passes;
    lock_investigation alone reports lock_valid False with the reason and keeps every other directory check; an
    unreadable lock stops it too; a name that is not allowed still stops."""
    api = _FakeApi()
    good1 = _lock_bytes(api, 1)
    rel1 = fd.canonical_bytes({"lock": 1, "lock_sha256": hashlib.sha256(good1).hexdigest(),
                               "token": {"lock_number": 1}, "utc": "x"})
    for i, (label, (bad, reason)) in enumerate(_invalid_lock_variants(api, 2).items()):
        for paired in (False, True):
            root = tmp_path / f"v{i}-{int(paired)}"
            d = root / fd.LOCK_DIR
            d.mkdir(parents=True)
            files = {"000001.lock": good1, "000001.released": rel1, "000002.lock": bad}
            if paired:
                bad_sha = hashlib.sha256(bad).hexdigest()
                files["000002.released"] = fd.canonical_bytes({"lock": 2, "lock_sha256": bad_sha})
            for name, data in files.items():
                (d / name).write_bytes(data)
            for call in (lambda: fd.scan_lock_dir(root), lambda: fd.acquire_lock(root, _lock(api)),
                         lambda: fd.abandon_lock(root, 2, [], api, rb1_verified=True)):
                with pytest.raises(fd.StopForUserDecision, match=f"not a valid lock \\({reason}"):
                    call()
            rep = fd.lock_investigation(root, 2, api)
            assert rep["lock_valid"] is False and rep["lock_invalid_reason"] == reason, label
            first = fd.lock_investigation(root, 1, api)
            assert first["lock_valid"] is True and first["lock_invalid_reason"] is None
            assert sorted(p.name for p in d.iterdir()) == sorted(files), label      # nothing written
    legacy = tmp_path / "legacy"                                              # a paired /1 lock 1
    (legacy / fd.LOCK_DIR).mkdir(parents=True)
    old = _lock_bytes(api, 1, schema_version="moneylab.bt4_futility_diag.g7_lock/1", token="ab" * 16)
    (legacy / fd.LOCK_DIR / "000001.lock").write_bytes(old)
    (legacy / fd.LOCK_DIR / "000001.released").write_bytes(
        fd.canonical_bytes({"lock": 1, "lock_sha256": hashlib.sha256(old).hexdigest()}))
    with pytest.raises(fd.StopForUserDecision, match="not a valid lock"):
        fd.acquire_lock(legacy, _lock(api))
    assert sorted(p.name for p in (legacy / fd.LOCK_DIR).iterdir()) == ["000001.lock", "000001.released"]
    both = tmp_path / "both"                                                  # investigation keeps the other checks
    (both / fd.LOCK_DIR).mkdir(parents=True)
    for name, data in (("000001.lock", _invalid_lock_variants(api, 1)["bool"][0]), ("000001.released", rel1),
                       ("000001.abandoned", rel1)):
        (both / fd.LOCK_DIR / name).write_bytes(data)
    with pytest.raises(fd.StopForUserDecision, match="both"):
        fd.lock_investigation(both, 1, api)
    named = tmp_path / "named"
    (named / fd.LOCK_DIR).mkdir(parents=True)
    (named / fd.LOCK_DIR / "000001.lck").write_bytes(good1)
    for call in (lambda: fd.scan_lock_dir(named), lambda: fd.lock_investigation(named, 1, api)):
        with pytest.raises(fd.StopForUserDecision, match="allowed name"):
            call()
    own = tmp_path / "own"                                                    # LockHandle.check
    h1 = fd.acquire_lock(own, _lock(api))
    fd.release_lock(h1)
    h2 = fd.acquire_lock(own, _lock(api))
    h2.check()
    d = own / fd.LOCK_DIR
    lock1_raw = (d / "000001.lock").read_bytes()
    for label, (bad, reason) in _invalid_lock_variants(api, 1).items():
        (d / "000001.lock").write_bytes(bad)
        with pytest.raises(fd.StopForUserDecision, match=f"lock 000001 is not a valid lock \\({reason}"):
            h2.check()
    (d / "000001.lock").write_bytes(lock1_raw)
    h2.check()
    own_raw = (d / "000002.lock").read_bytes()
    (d / "000002.lock").write_bytes(own_raw.replace(b'"pid":', b'"pid":9', 1))   # own lock changed
    with pytest.raises(fd.StopForUserDecision, match="not the one this driver holds"):
        h2.check()
    (d / "000002.lock").write_bytes(own_raw)
    h2.check()
    gone = fd.LockHandle(own, 3, h2.sha256, {"lock_number": 3}, dict(h2.content))   # its lock file does not exist
    with pytest.raises(fd.StopForUserDecision, match="not the one this driver holds"):
        gone.check()
    real = fd._read_canonical

    def unreadable(path, what):
        if FsPath(path).name == "000001.lock" and FsPath(path).parent == d:
            raise PermissionError("read denied (test)")
        return real(path, what)
    monkeypatch.setattr(fd, "_read_canonical", unreadable)
    for call in (h2.check, lambda: fd.scan_lock_dir(own), lambda: fd.lock_investigation(own, 1, api)):
        with pytest.raises(fd.StopForUserDecision, match=f"not a valid lock \\({fd.LOCK_READ_FAILED}"):
            call()


def test_e_boot_only_with_udr_and_every_condition(tmp_path):
    """AC-J13 / AC-J7 / AC-4: E-BOOT needs the same host_id, S1 and S2 within 120 s, a new boot session (> 120 s past
    the lock's), boot strictly after every lock / pool record mtime, no future mtime and RB-1 verified; abandon also
    needs the LOCK_ABANDON UDR of exactly that lock. A UDR alone, or audit evidence, never abandons."""
    old = _FakeApi()
    h = fd.acquire_lock(tmp_path, _lock(old))
    d = tmp_path / fd.LOCK_DIR
    fd.write_pool_start(d, 1, h.sha256, 1, run_id_="r", unit_id=["u"], driver_pid=100, driver_creation_time=5000,
                        planned_max_workers=1)
    files = [d / "000001.lock", d / "000001.pool-000001.start"]
    written = TS + 1800 * SEC                                                 # 30 min after the old boot
    for f in files:
        _set_mtime(f, written)
    new = _FakeApi(s1=TS + 7200 * SEC, now=TS + 9000 * SEC)                  # rebooted 2 h after the old boot
    lock = fd.read_lock(d / "000001.lock")
    ok = fd.e_boot(lock, files, new, rb1_verified=True)
    assert ok["established"] and ok["reasons"] == [] and ok["host_id_match"] is True
    assert ok["mtimes"] == {"000001.lock": written, "000001.pool-000001.start": written}
    assert fd.RB1_VERIFIED is True and fd.e_boot(lock, files, new)["reasons"] == []    # default: RB-1 passed
    assert fd.e_boot(lock, files, new, rb1_verified=False)["reasons"] == ["RB1_PENDING"]   # not passed: never holds
    for reason, api in (("HOST_ID_MISMATCH", _FakeApi(TS + 7200 * SEC, TS + 9000 * SEC, ("OTHER", "guid-1"))),
                        ("HOST_ID_MISMATCH", _FakeApi(TS + 7200 * SEC, TS + 9000 * SEC, ("HOST", "guid-2"))),
                        ("BOOT_SESSION_UNCHANGED", _FakeApi(TS + 60 * SEC, TS + 9000 * SEC)),
                        ("BOOT_NOT_AFTER_RECORDS", _FakeApi(TS + 1000 * SEC, TS + 9000 * SEC)),
                        ("BOOT_NOT_AFTER_RECORDS", _FakeApi(written, TS + 9000 * SEC)),      # equal: not after
                        ("FUTURE_MTIME", _FakeApi(TS + 600 * SEC, TS + 1000 * SEC))):
        assert reason in fd.e_boot(lock, files, api, rb1_verified=True)["reasons"]
    skew = _FakeApi(TS + 7200 * SEC, TS + 9000 * SEC)
    skew.tick_ms -= 121 * 1000                                                # S2 121 s after S1: clock change?
    fail = _FakeApi(TS + 7200 * SEC, TS + 9000 * SEC)
    fail.fail.add("host")
    for api in (skew, fail):
        assert fd.e_boot(lock, files, api, rb1_verified=True)["reasons"][0].startswith("READ_FAILED")
    assert fd.e_boot(None, files, new, rb1_verified=True)["reasons"] == ["INVALID_LOCK"]
    with pytest.raises(fd.StopForUserDecision, match="no LOCK_ABANDON UDR"):
        fd.abandon_lock(tmp_path, 1, [], new, rb1_verified=True)
    fd.write_udr(tmp_path, _udr_line(1, "LOCK_ABANDON", f"lock=000001,lock_sha256={'0' * 64}", "ABANDON"), "x", CODE)
    with pytest.raises(fd.StopForUserDecision):
        fd.abandon_lock(tmp_path, 1, [1], new, rb1_verified=True)            # a UDR for another lock sha256
    fd.write_udr(tmp_path, _udr_line(2, "LOCK_ABANDON", f"lock=000001,lock_sha256={h.sha256}", "ABANDON"), "x", CODE)
    for api, rb1 in ((old, True), (new, False)):                              # no new boot / RB-1 pending
        with pytest.raises(fd.StopImplementation, match="E-BOOT does not hold"):
            fd.abandon_lock(tmp_path, 1, [1, 2], api, rb1_verified=rb1)
    assert not (d / "000001.abandoned").exists()
    driver = (lock["pid"], lock["driver_creation_time"])
    for setup, match in ((lambda a: a.procs.__setitem__(driver[0], driver[1]), "driver ALIVE"),
                         (lambda a: (a.procs.__setitem__(4400, driver[1] + 1),
                                     a.parent.__setitem__(4400, driver[0])), "descendant 4400")):
        alive = _FakeApi(TS + 7200 * SEC, TS + 9000 * SEC)                    # E-BOOT holds, a process is alive
        setup(alive)
        assert fd.e_boot(lock, files, alive)["established"]
        with pytest.raises(fd.StopImplementation, match=match):
            fd.abandon_lock(tmp_path, 1, [1, 2], alive)                       # UDR + E-BOOT, still refused
        assert not (d / "000001.abandoned").exists()
    assert fd.live_processes(fd.investigate(new, driver, [])) == []
    rec = fd.abandon_lock(tmp_path, 1, [1, 2], new, rb1_verified=True)
    assert rec["e_boot"]["established"] and (d / "000001.abandoned").exists() and (d / "000001.lock").exists()
    fd.scan_lock_dir(tmp_path)
    assert fd.acquire_lock(tmp_path, _lock(new)).number == 2
    with pytest.raises(fd.StopImplementation, match="not an unpaired lock"):
        fd.abandon_lock(tmp_path, 1, [1, 2], new, rb1_verified=True)


def test_investigation_is_audit_only():
    """AC-J7 (FAKE): E-PID / E-WORKERS / E-TREE report state for the audit; seeds are the driver and every recorded
    worker with their creation times; an older process under a reused parent pid is not a descendant."""
    api = _FakeApi()
    w = api.add_worker(1000)
    api.add_worker(2000, parent=1000)
    api.add_worker(3000, ct=1, parent=1000)
    rep = fd.investigate(api, (api.driver_pid, api.driver_ct), [w, (1001, 9)])
    assert rep["evidence_use"] == "AUDIT_ONLY" and rep["e_pid"] == "ALIVE"
    assert rep["e_workers"] == [[1000, w[1], "ALIVE"], [1001, 9, "GONE"]]
    assert [p for p, _ in rep["e_tree"]] == [1000, 2000] and rep["e_tree_snapshots_agree"]


def test_process_liveness_classification_and_abandon_refusal(tmp_path):
    """R-4 E-PID / E-WORKERS (FAKE): GONE needs both the pid's absence from the snapshot and OpenProcess failing with
    ERROR_INVALID_PARAMETER; access denied, a pid still listed or an unreadable creation time is UNVERIFIABLE. A live
    or unverifiable driver / worker refuses the abandon even with the UDR and E-BOOT (no .abandoned, no signal)."""
    old = _FakeApi()
    h = fd.acquire_lock(tmp_path, _lock(old))
    d = tmp_path / fd.LOCK_DIR
    rec = dict(run_id_="r", unit_id=["u"], driver_pid=100, driver_creation_time=5000)
    fd.write_pool_start(d, 1, h.sha256, 1, planned_max_workers=1, **rec)
    fd.write_pool_workers(d, 1, h.sha256, 1, expected=1, workers=[(7000, 9000)], **rec)
    files = sorted(d.iterdir())
    for f in files:
        _set_mtime(f, TS + 1800 * SEC)
    fd.write_udr(tmp_path, _udr_line(1, "LOCK_ABANDON", f"lock=000001,lock_sha256={h.sha256}", "ABANDON"), "x", CODE)
    lock = fd.read_lock(d / "000001.lock")
    pid, ct = lock["pid"], lock["driver_creation_time"]

    def rebooted():
        return _FakeApi(TS + 7200 * SEC, TS + 9000 * SEC)

    cases = (("A gone", lambda a: None, {"e_pid": "GONE", "worker": "GONE"}),
             ("B denied", lambda a: (a.parent.__setitem__(pid, 1), a.fail.add(pid)), {"e_pid": "UNVERIFIABLE"}),
             ("B worker denied", lambda a: (a.parent.__setitem__(7000, 1), a.fail.add(7000)),
              {"worker": "UNVERIFIABLE"}),
             ("C alive", lambda a: a.procs.__setitem__(pid, ct), {"e_pid": "ALIVE"}),
             ("C reused", lambda a: (a.procs.__setitem__(pid, ct + 1), a.parent.__setitem__(pid, 1)),
              {"e_pid": "PID_REUSED"}),
             ("D no time", lambda a: (a.procs.__setitem__(pid, ct), a.ct_fail.add(pid)), {"e_pid": "UNVERIFIABLE"}),
             ("listed but 87", lambda a: a.parent.__setitem__(pid, 1), {"e_pid": "UNVERIFIABLE"}))
    for name, setup, want in cases:
        api = rebooted()
        setup(api)
        rep = fd.investigate(api, (pid, ct), [(7000, 9000)])
        got = {"e_pid": rep["e_pid"], "worker": rep["e_workers"][0][2]}
        assert {k: got[k] for k in want} == want, name
        assert fd.e_boot(lock, files, api)["established"], name               # E-BOOT holds in every case
        if name in ("A gone", "C reused"):
            continue
        with pytest.raises(fd.StopImplementation, match="live processes"):
            fd.abandon_lock(tmp_path, 1, [1], api)                            # B, C, D: refused
        assert not (d / "000001.abandoned").exists(), name
    out = fd.abandon_lock(tmp_path, 1, [1], rebooted())                       # A: absence confirmed, UDR, E-BOOT
    assert out["e_boot"]["established"] and (d / "000001.abandoned").exists()


def test_exit_state_classification_e_pid_and_e_tree(tmp_path):
    """E-PID / E-WORKERS / E-TREE exit state (FAKE): for the same pid and creation time WaitForSingleObject decides
    EXITED (terminated, object kept by a handle) or ALIVE; PID_REUSED unchanged; access denied, SYNCHRONIZE denied
    and a failed wait are UNVERIFIABLE (never GONE or EXITED). An exited descendant is not a live one but its own
    descendants are still searched; an uncertain descendant stays a live one. EXITED never refuses an abandon,
    ALIVE / UNVERIFIABLE always do (with the UDR and E-BOOT unchanged)."""
    def state(setup, pid=4000, ct=7000):
        api = _FakeApi()
        api.parent[pid] = 1
        setup(api)
        return fd.investigate(api, (pid, ct), [])["e_pid"]

    assert state(lambda a: a.procs.__setitem__(4000, 7000)) == "ALIVE"
    assert state(lambda a: (a.procs.__setitem__(4000, 7000), a.exited_set.add(4000))) == "EXITED"
    assert state(lambda a: a.procs.__setitem__(4000, 7001)) == "PID_REUSED"
    assert state(lambda a: (a.procs.__setitem__(4000, 7001), a.exited_set.add(4000))) == "PID_REUSED"
    assert state(lambda a: (a.procs.__setitem__(4000, 7000), a.fail.add(4000))) == "UNVERIFIABLE"
    assert state(lambda a: (a.procs.__setitem__(4000, 7000), a.sync_denied.add(4000))) == "UNVERIFIABLE"
    assert state(lambda a: (a.procs.__setitem__(4000, 7000), a.wait_fail.add(4000))) == "UNVERIFIABLE"
    assert state(lambda a: (a.procs.__setitem__(4000, 7000), a.exited_set.add(4000),
                            a.ct_fail.add(4000))) == "UNVERIFIABLE"
    api = _FakeApi()
    api.add_worker(1000)
    api.add_worker(2000, parent=1000)
    api.exited_set.add(2000)                                                  # exited, handle kept
    api.add_worker(2100, parent=2000)                                         # its child still runs
    api.add_worker(2200, parent=1000)
    api.wait_fail.add(2200)                                                   # state uncertain
    rep = fd.investigate(api, (api.driver_pid, api.driver_ct), [])
    assert sorted(p for p, _ in rep["e_tree"]) == [1000, 2100, 2200]
    assert [2200, None] in rep["e_tree"] and fd.live_processes(rep)           # uncertain kept, refuses
    h = fd.acquire_lock(tmp_path, _lock(_FakeApi()))
    d = tmp_path / fd.LOCK_DIR
    _set_mtime(d / "000001.lock", TS + 1800 * SEC)
    fd.write_udr(tmp_path, _udr_line(1, "LOCK_ABANDON", f"lock=000001,lock_sha256={h.sha256}", "ABANDON"), "x", CODE)
    lock = fd.read_lock(d / "000001.lock")
    pid, ct = lock["pid"], lock["driver_creation_time"]
    for setup, refused in ((lambda a: a.wait_fail.add(pid), True), (lambda a: a.sync_denied.add(pid), True),
                           (lambda a: a.exited_set.add(pid), False)):
        api = _FakeApi(TS + 7200 * SEC, TS + 9000 * SEC)
        api.procs[pid], api.parent[pid] = ct, 1
        setup(api)
        if refused:
            with pytest.raises(fd.StopImplementation, match="live processes"):
                fd.abandon_lock(tmp_path, 1, [1], api)
            assert not (d / "000001.abandoned").exists()
        else:
            assert fd.abandon_lock(tmp_path, 1, [1], api)["e_boot"]["established"]   # EXITED: not a refusal


def test_target_job_setup_and_stops():
    """AC-J1 / AC-J4 / AC-J5 (FAKE): flags read back exactly KILL_ON_JOB_CLOSE, prior membership recorded, the
    driver confirmed in the target job, the handle not inheritable; each failure STOPs."""
    api = _FakeApi()
    assert fd.setup_target_job(api) == {"job": 77, "prior_job_membership": True, "flags": fd.JOB_KILL_ON_CLOSE}
    assert api.assigned

    def no_assign(a):
        a.assign_current = lambda job: None

    for change, match in ((lambda a: setattr(a, "flags", fd.JOB_KILL_ON_CLOSE | fd.JOB_SILENT_BREAKAWAY_OK), "flags"),
                          (lambda a: setattr(a, "flags", fd.JOB_KILL_ON_CLOSE | fd.JOB_BREAKAWAY_OK), "flags"),
                          (lambda a: setattr(a, "flags", 0), "flags"),
                          (lambda a: setattr(a, "inherit", True), "inheritable"),
                          (lambda a: a.fail.add("assign"), "Assign"), (no_assign, "not in the target job")):
        a = _FakeApi()
        change(a)
        with pytest.raises(fd.StopImplementation, match=match):
            fd.setup_target_job(a)


def test_pool_worker_verification_failures(tmp_path):
    """AC-J2 / AC-J6 (FAKE): (A) per worker and (B) over the job list and the driver's children; a failure STOPs."""
    def setup():
        api = _FakeApi()
        return api, _env(api, tmp_path), [api.add_worker(1000), api.add_worker(1001)]

    api, env, ws = setup()
    assert fd.verify_pool_workers(env, ws, 2, {}) == ws
    for change, reported, match in (
            (lambda a: None, lambda ws: ws[:1], "reported"),
            (lambda a: a.fail.add(1001), lambda ws: ws, "cannot be opened"),
            (lambda a: None, lambda ws: [ws[0], (1001, 1)], "creation time"),
            (lambda a: a.parent.__setitem__(1001, 999), lambda ws: ws, "direct child"),
            (lambda a: a.members.discard(1001), lambda ws: ws, "not in the target job"),
            (lambda a: setattr(a, "job_pids", lambda job: [100, 1000]), lambda ws: ws, "missing")):
        api, env, ws = setup()
        change(api)
        with pytest.raises(fd.StopImplementation, match=match):
            fd.verify_pool_workers(env, reported(ws), 2, {})


def test_start_barrier_fake_workers_and_timeout(tmp_path):
    """AC-J3 (FAKE): min(w, tasks) workers, results only after the release, the unit's results in task order; no
    ready report in time is a STOP without a release."""
    api = _FakeApi()
    env = _env(api, tmp_path / "a")
    assert fd.barrier_pool_run(env, _double, [1, 2, 3], 2, ["u", 0, 3]) == [2, 4, 6]
    assert sorted(api.members) == [1000, 1001] and env.next_pool == 2
    api = _FakeApi()
    env = _env(api, tmp_path / "b", silent=True)
    with pytest.raises(fd.StopImplementation, match="ready timeout"):
        fd.barrier_pool_run(env, _double, [1, 2], 2, ["u"])
    assert "released" not in env.events and not (env.record_dir / "000001.workers-000001").exists()


def test_core_budget_counts_every_attempt(tmp_path):
    """AC-3 / AC-J8 (OPTION I): T_CORE sums every attempt of both cells (no reset on retry), exactly 1.5 x passes,
    an open session is a lower bound with no PASS, a budget STOP is listed (no restart)."""
    spec = _store_spec(reps=2, unit_size=2, cells=["E1-theta0.7"])
    timing = {"worker_hours": 12.0, "eta_hat": 1.0}                           # expected 3,600 s, limit 5,400 s

    def put(root, name, ex):
        (root / name).mkdir(parents=True)
        (root / name / fd.EXECUTION_FILE).write_bytes(fd.canonical_bytes(
            {"schema_version": fd.EXECUTION_SCHEMA, "evidence": fd.EVIDENCE, **ex}))

    for root, p0_wall, exceeded in ((tmp_path / "a", 900.0, False), (tmp_path / "b", 900.5, True)):
        put(root, f"g7-E1-theta0.7-{SHA12}", _run(spec, 2700.0, tag="a"))
        put(root, f"g7-E1-theta0.7-{SHA12}-attempt2", _run(spec, 1800.0, tag="b"))
        put(root, f"g7-P0-theta0.7-{SHA12}", _run(spec, p0_wall, tag="c"))
        put(root, f"g7-v4-{SHA12}", _run(spec, 10 ** 6, tag="v"))             # V-4 is never in T_CORE
        b = fd.core_attempts_budget(root, CODE, timing)
        assert (b["t_core_cumulative_s"], b["exceeded"], b["budget_pass_allowed"]) == \
            (2700.0 + 1800.0 + p0_wall, exceeded, not exceeded)
        assert b["limit_s"] == 5400.0 and len(b["per_run"]) == 3
    put(tmp_path / "c", f"g7-E1-theta0.7-{SHA12}", _run(spec, 100.0, open_last=True, tag="o"))
    b = fd.core_attempts_budget(tmp_path / "c", CODE, timing)
    assert b["lower_bound"] and not b["budget_pass_allowed"] and not b["time_accounting_complete"]
    stopped = _run(spec, 100.0, tag="s")
    stopped["sessions"][0]["end"]["stop"] = "CORE wall-clock budget: ..."
    put(tmp_path / "d", f"g7-P0-theta0.7-{SHA12}", stopped)
    assert fd.core_attempts_budget(tmp_path / "d", CODE, timing)["budget_stopped_runs"] == [f"g7-P0-theta0.7-{SHA12}"]


def test_g7_entry_checks_each_stop(pilot, tmp_path):
    """AC-1: the R-1 entry checks (one cell, reps = R_c, unit_size = the pilot's with g6 VERIFIED, budget PASS,
    R_c <= 40,000, P0_CONF_CHECK PASS) each STOP."""
    d0, spec, inputs, cal, sha, files = pilot
    d = tmp_path / "pilot"
    shutil.copytree(d0, d)
    summary = json.loads(fd.canonical_bytes(fd.write_g6(d, cal, sha)))
    summary["r_c"]["r_c"], summary["r_c"]["over_max"] = {"E1-theta0.7": 6, "P0-theta0.7": 6}, []
    summary["P0_CONF_CHECK"] = "PASS"

    def core(**over):
        return _spec(**{"cells": ["E1-theta0.7"], "reps": 6, "unit_size": spec["unit_size"], **over})

    fd.g7_entry_checks(d, core(), "E1-theta0.7", summary, {"budget_pass": True})
    for c, s, t, match in ((core(cells=list(fd.CORE_CELLS)), summary, {"budget_pass": True}, "exactly one cell"),
                           (core(reps=7), summary, {"budget_pass": True}, "R_c"),
                           (core(unit_size=spec["unit_size"] + 1), summary, {"budget_pass": True}, "unit_size"),
                           (core(), summary, {"budget_pass": False}, "WO:419"),
                           (core(), {**summary, "r_c": {**summary["r_c"], "over_max": ["E1-theta0.7"]}},
                            {"budget_pass": True}, "WO:457"),
                           (core(), {**summary, "P0_CONF_CHECK": "STOP"}, {"budget_pass": True}, "P0_CONF_CHECK")):
        with pytest.raises(fd.StopImplementation, match=match):
            fd.g7_entry_checks(d, c, "E1-theta0.7", s, t)
    (d / "g6" / fd.SUMS_FILE).unlink()
    with pytest.raises(fd.StopImplementation, match="VERIFIED"):
        fd.g7_entry_checks(d, core(), "E1-theta0.7", summary, {"budget_pass": True})


def test_g7_driver_refuses_before_any_write(tmp_path, monkeypatch):
    """AC-2 / AC-J12 / AC-J14: no exact G7_POOL_FAILURE_POLICY, a platform other than Windows, a Python other than
    3.14.8, or workers outside 1..12 STOP before anything is read, created or written."""
    kw = dict(pilot_dir=tmp_path / "p", cal_dir=tmp_path / "c", e1_dir=tmp_path / f"g7-E1-theta0.7-{SHA12}",
              p0_dir=tmp_path / f"g7-P0-theta0.7-{SHA12}", v4_dir=tmp_path / f"g7-v4-{SHA12}", git=_fake_git(),
              api=_FakeApi())
    for policy in (None, "allow", fd.G7_POOL_FAILURE_POLICY.lower(), fd.G7_POOL_FAILURE_POLICY + " "):
        with pytest.raises(fd.StopImplementation, match="G7_POOL_FAILURE_POLICY"):
            fd.g7_core(tmp_path, workers=2, pool_failure_policy=policy, **kw)
    policy = fd.G7_POOL_FAILURE_POLICY
    monkeypatch.setattr(fd.platform, "python_version", lambda: "3.14.7")
    with pytest.raises(fd.StopImplementation, match="3.14.8"):
        fd.g7_core(tmp_path, workers=2, pool_failure_policy=policy, **kw)
    monkeypatch.setattr(fd.platform, "python_version", lambda: "3.14.8")
    monkeypatch.setattr(fd.sys, "platform", "linux")
    with pytest.raises(fd.StopImplementation, match="Windows"):
        fd.g7_core(tmp_path, workers=2, pool_failure_policy=policy, **kw)
    monkeypatch.setattr(fd.sys, "platform", "win32")
    for w in (0, 13):
        with pytest.raises(fd.StopImplementation, match="workers"):
            fd.g7_core(tmp_path, workers=w, pool_failure_policy=policy, **kw)
    assert list(tmp_path.iterdir()) == []


def test_no_termination_or_signal_call_in_module():
    """AC-J14 (static): the module (and so the ctypes wrapper) calls no process-ending, job-ending or signal API and
    no executor method that ends workers; the test file's only direct ending is IT-5 (group C); the IT timeout
    path ends nothing."""
    import inspect
    import re as re_
    src = FsPath(fd.__file__).read_text(encoding="utf-8")
    for pattern in (r"TerminateProcess", r"TerminateJobObject", r"os\.kill", r"\.terminate\(", r"\.kill\(",
                    r"terminate_workers", r"kill_workers", r"\bimport signal\b", r"signal\.", r"send_signal",
                    r"GenerateConsoleCtrlEvent", r"CREATE_BREAKAWAY_FROM_JOB\s*\|", r"DuplicateHandle"):
        assert not re_.search(pattern, src), pattern
    token = "proc." + "terminate()"
    test_src = FsPath(__file__).read_text(encoding="utf-8")
    assert test_src.count(token) == 1 and token in inspect.getsource(test_it5_driver_forced_end_and_kill_on_job_close)
    assert not re_.search(r"\.terminate\(|\.kill\(", inspect.getsource(_it_timeout_stop))


def _resolve_import_from(node, package):
    """The absolute module of an ImportFrom: level 0 as written, level k > 0 against the module's package (level 1 =
    the package itself); None when the level climbs above the top package (not resolvable, never allowed)."""
    if node.level == 0:
        return node.module
    parts = package.split(".")
    if node.level - 1 >= len(parts):
        return None
    base = parts[:len(parts) - (node.level - 1)]
    return ".".join([*base, node.module] if node.module else base)


def test_module_imports_stdlib_or_moneylab_only():
    """WO:117 / WO:390 (stdlib only, no added dependency): every direct import of futility_diag.py, top level and inside
    functions (ast.walk over Import / ImportFrom), is a sys.stdlib_module_names module or moneylab / moneylab.*.
    Layer rules stay in the architecture tests; imports made by moneylab modules (transitive) are out of scope.
    Static limits: a real __import__ / importlib.import_module / exec / eval call node (not a word in a string or
    comment) cannot be decided statically and is a STOP_FOR_USER_DECISION, as is a relative import that does not
    resolve; imports made at run time by child processes (subprocess, multiprocessing) are not seen by this check."""
    import ast
    path = FsPath(fd.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    package = fd.__name__.rpartition(".")[0]
    seen, bad, unresolved, dynamic = [], [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_import_from(node, package)
            if resolved is None:
                unresolved.append((node.lineno, node.level, node.module))
                continue
            names = [resolved]
        elif isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Name) and f.id in {"__import__", "exec", "eval", "import_module"}) or \
                    (isinstance(f, ast.Attribute) and f.attr in {"__import__", "import_module"}):
                dynamic.append((node.lineno, ast.unparse(f)))
            continue
        else:
            continue
        for name in names:
            seen.append((node.lineno, name))
            if not (name.split(".")[0] in sys.stdlib_module_names or name == "moneylab"
                    or name.startswith("moneylab.")):
                bad.append((node.lineno, name))
    print(json.dumps({"stdlib_check": {"imports": seen, "dynamic_calls": dynamic, "unresolved_relative": unresolved}}))
    assert seen, "no import found: the parse did not see the module"
    if dynamic or unresolved:
        pytest.fail(f"STOP_FOR_USER_DECISION: not statically decidable: dynamic={dynamic} unresolved={unresolved}")
    assert not bad, bad


def test_v4_run_storage_reuse_and_damage(tmp_path, monkeypatch):
    """AC-5 (R-5): v4.json (deterministic, K = 40) and SHA256SUMS (that file only), the time in execution.json only;
    a verified run is reused without recomputing; v4.json alone is recomputed byte for byte; damage STOPs."""
    d = tmp_path / f"g7-v4-{SHA12}"
    ident = {"git_head": CODE}
    first = fd.write_v4_run(d, ident, [], years=40)
    assert first["status"] == "VERIFIED" and first["v4"]["years"] == 40 and len(first["v4"]["batch_sharpes"]) == 40
    raw = (d / fd.V4_FILE).read_bytes()
    assert (d / fd.SUMS_FILE).read_bytes() == f"{hashlib.sha256(raw).hexdigest()}  v4.json\n".encode()
    assert "seconds" not in raw.decode() and "v4_seconds" in (d / fd.EXECUTION_FILE).read_text()
    real = fd.v4_evaluation
    monkeypatch.setattr(fd, "v4_evaluation", lambda *a, **k: (_ for _ in ()).throw(AssertionError("recomputed")))
    assert fd.write_v4_run(d, ident, [], years=40)["sha256"] == first["sha256"]          # reused
    monkeypatch.setattr(fd, "v4_evaluation", real)
    (d / fd.SUMS_FILE).unlink()
    assert fd.write_v4_run(d, ident, [], years=40)["status"] == "VERIFIED" and (d / fd.V4_FILE).read_bytes() == raw
    with pytest.raises(fd.StopImplementation, match="differs"):
        (d / fd.SUMS_FILE).unlink()
        fd.write_v4_run(d, {"git_head": "2" * 40}, [], years=40)               # other identity: other bytes
    (d / fd.SUMS_FILE).write_bytes(f"{hashlib.sha256(raw).hexdigest()}  v4.json\n".encode())
    (d / fd.V4_FILE).write_bytes(raw.replace(b'"years":40', b'"years":41'))
    with pytest.raises(fd.StopImplementation):
        fd.verify_v4_run(d)
    (d / fd.V4_FILE).write_bytes(raw)
    (d / "extra.txt").write_text("x")
    with pytest.raises(fd.StopImplementation, match="unexpected files"):
        fd.verify_v4_run(d)


def test_g8a_targets_only_the_highest_attempt(research_cal, tmp_path):
    """AC-6 (R-6): G8a's target set is the highest attempt of each stage; anything else STOPs before writing."""
    cal, _ = research_cal
    cal_dir = tmp_path / f"g5-cal-{SHA12}"
    cal_dir.mkdir()
    fd.write_calibration(cal_dir, cal, git=_fake_git())
    for part in ("E1-theta0.7", "P0-theta0.7", "v4"):
        (tmp_path / f"g7-{part}-{SHA12}").mkdir()
    (tmp_path / f"g7-E1-theta0.7-{SHA12}-attempt2").mkdir()
    decision = tmp_path / f"g8a-{SHA12}"
    with pytest.raises(fd.StopImplementation, match="highest attempt"):
        fd.g8a_decide(tmp_path, decision_dir=decision, pilot_dir=tmp_path / "p", cal_dir=cal_dir,
                      e1_dir=tmp_path / f"g7-E1-theta0.7-{SHA12}", p0_dir=tmp_path / f"g7-P0-theta0.7-{SHA12}",
                      v4_dir=tmp_path / f"g7-v4-{SHA12}", git=_fake_git())
    assert not decision.exists()


def _decision_payload(attempts_e1=0):
    """A decision_summary.json payload of the R-6 shape from the synthetic decision inputs (no run is computed)."""
    run = {k: "c" * 64 for k in fd.DECISION_RUN_FIELDS[1:]}
    e1_attempts = [{"run_id": fd.run_id("g7", "E1-theta0.7", CODE, k), "status": "INCOMPLETE", "udr_sha256": []}
                   for k in range(1, attempts_e1 + 1)]
    return {"schema_version": fd.DECISION_SCHEMA, "study_id": fd.STUDY_ID, "evidence": fd.EVIDENCE,
            "decision": fd.decision_summary(*_decision_inputs()),
            "provenance": {"runs": {"E1-theta0.7": {"run_id": fd.run_id("g7", "E1-theta0.7", CODE, attempts_e1 + 1),
                                                    **run},
                                    "P0-theta0.7": {"run_id": fd.run_id("g7", "P0-theta0.7", CODE), **run}},
                           "v4_sha256": "d" * 64, "g6_summary_sha256": "e" * 64, "calibration_sha256": "f" * 64,
                           "code_sha": CODE, "attempts": {"E1-theta0.7": e1_attempts, "P0-theta0.7": [], "v4": []},
                           "udr_sha256": ["a" * 64, "b" * 64]}}


def _write_decision(d, payload):
    d.mkdir(parents=True, exist_ok=True)
    data = fd.canonical_bytes(json.loads(fd.canonical_bytes(payload)))
    (d / fd.DECISION_FILE).write_bytes(data)
    (d / fd.SUMS_FILE).write_bytes(f"{hashlib.sha256(data).hexdigest()}  {fd.DECISION_FILE}\n".encode())
    return data


def test_g8a_decision_directory_verify(tmp_path, monkeypatch, capsys):
    """R-6 / ERRATA-005 [C] "각 디렉터리 verify": a G8a directory verifies from its files alone (only the decision and
    its SHA256SUMS, canonical, the R-6 structure: five labels, target run hashes, attempts in order with state and
    UDR, the CODE_SHA its name carries, the sorted UDR set); damage STOPs and is never repaired; reverify_g8a
    recomputes and requires identical bytes."""
    root = _out_root(tmp_path)
    d = root / f"g8a-{SHA12}"
    assert fd.verify_g8a_dir(d)["status"] == "ABSENT"
    data = _write_decision(d, _decision_payload(attempts_e1=1))
    state = fd.verify_g8a_dir(d)
    assert state == {"status": "VERIFIED", "tmp": [], "decision_sha256": hashlib.sha256(data).hexdigest()}
    snap = _snapshot(root)
    code, out = _cli(["verify", "--run", d], root, capsys)
    assert code == 0 and (out["directory"], out["sha256"]) == ("VERIFIED", state["decision_sha256"])
    assert _snapshot(root) == snap                                             # read-only
    good = _decision_payload(attempts_e1=1)
    bad_payloads = (
        {**good, "extra": 1},
        {**good, "evidence": "REAL"},
        {**good, "decision": {**good["decision"], "labels": {k: v for k, v in good["decision"]["labels"].items()
                                                             if k != "V-4"}}},
        {**good, "provenance": {**good["provenance"], "code_sha": "2" * 40}},              # not this directory's
        {**good, "provenance": {**good["provenance"], "udr_sha256": ["b" * 64, "a" * 64]}},  # not sorted
        {**good, "provenance": {**good["provenance"], "v4_sha256": "d" * 63}},
        {**good, "provenance": {**good["provenance"], "attempts": {"E1-theta0.7": [], "P0-theta0.7": [], "v4": []}}},
        {**good, "provenance": {**good["provenance"],
                                "runs": {**good["provenance"]["runs"],
                                         "P0-theta0.7": {**good["provenance"]["runs"]["P0-theta0.7"],
                                                         "run_id": f"g7-P0-theta0.7-{'2' * 12}"}}}})
    for i, payload in enumerate(bad_payloads):
        bd = root / f"g8a-{SHA12}-attempt{i + 2}"
        _write_decision(bd, payload)
        with pytest.raises(fd.StopImplementation):
            fd.verify_g8a_dir(bd)
    for name, change in (("sums", lambda p: p.joinpath(fd.SUMS_FILE).write_bytes(b"0" * 64 + b"  x\n")),
                         ("extra", lambda p: p.joinpath("notes.txt").write_text("x")),
                         ("orphan", lambda p: p.joinpath(fd.DECISION_FILE).unlink()),
                         ("noncanon", lambda p: p.joinpath(fd.DECISION_FILE).write_bytes(
                             json.dumps(json.loads(data), indent=1).encode()))):
        cd = tmp_path / name / f"g8a-{SHA12}"
        shutil.copytree(d, cd)
        change(cd)
        snap = _snapshot(cd)
        with pytest.raises(fd.StopImplementation):
            fd.verify_g8a_dir(cd)
        assert _snapshot(cd) == snap                                           # never repaired
    inc = tmp_path / "inc" / f"g8a-{SHA12}"
    shutil.copytree(d, inc)
    (inc / fd.SUMS_FILE).unlink()
    assert fd.verify_g8a_dir(inc)["status"] == "INCOMPLETE"
    kw = dict(decision_dir=d, pilot_dir=root / "p", cal_dir=root / "c", e1_dir=root / "e", p0_dir=root / "q",
              v4_dir=root / "v")
    monkeypatch.setattr(fd, "g8a_payload", lambda *a, **k: (data, {}))
    assert fd.reverify_g8a(root, **kw)["recomputed"] == "IDENTICAL"
    monkeypatch.setattr(fd, "g8a_payload", lambda *a, **k: (data.replace(b'"c', b'"C', 1), {}))
    with pytest.raises(fd.StopImplementation, match="differs from the recorded one"):
        fd.reverify_g8a(root, **kw)
    with pytest.raises(fd.StopImplementation, match="INCOMPLETE"):
        fd.reverify_g8a(root, **{**kw, "decision_dir": inc})


def test_v4_directory_verify_command(tmp_path, capsys):
    root = _out_root(tmp_path)
    d = root / f"g7-v4-{SHA12}"
    fd.write_v4_run(d, {"git_head": CODE}, [], years=40)
    code, out = _cli(["verify", "--run", d], root, capsys)
    assert code == 0 and out["directory"] == "VERIFIED" and out["sha256"] == fd.verify_v4_run(d)["sha256"]


def test_rb1_reading_consistency_fake():
    """RB-1 reading path (FAKE): S1 / S2 within 120 s is reported; more is a STOP (clock change suspected)."""
    r = fd.rb1_reading(_FakeApi())
    assert r["s1"] == r["s2"] == TS and r["s1_minus_s2_s"] == 0.0 and r["host_id"]["machine_guid"] == "guid-1"
    api = _FakeApi()
    api.tick_ms -= 121 * 1000
    with pytest.raises(fd.StopImplementation, match="disagree"):
        fd.rb1_reading(api)


# --- group D (FAKE, separately approved): IT-6 unexpected process, IT-7 E-POOL-START, IT-8 E-WORKERS ----------------

@it_group_d
def test_it6_unexpected_process_stops(tmp_path):
    """IT-6 (AC-J2 unexpected PID, AC-J6): a process in the target job or a driver child that is not a verified
    worker STOPs before the release; one that appears after the release STOPs before the unit is written."""
    for i, (setup, kw, match) in enumerate((
            (lambda a: a.extra_job_pids.append(4242), {}, "unexpected"),
            (lambda a: a.add_worker(4243, member=False), {}, "driver children"),
            (lambda a: None, {"extra": (6000, 1)}, "unexpected worker reported"))):
        api = _FakeApi()
        setup(api)
        env = _env(api, tmp_path / str(i), **kw)
        with pytest.raises(fd.StopImplementation, match=match):
            fd.barrier_pool_run(env, _double, [1, 2], 2, ["u"])
        assert "released" not in env.events
    api = _FakeApi()
    env = _env(api, tmp_path / "late")

    def spawn_late(x):
        api.add_worker(5000)
        return x

    with pytest.raises(fd.StopImplementation, match="unexpected"):
        fd.barrier_pool_run(env, spawn_late, [1], 1, ["u"])
    assert "released" in env.events and "rechecked" not in env.events


@it_group_d
def test_it7_pool_start_order_and_failure_injection(tmp_path):
    """IT-7 (AC-J9, AC-J11): E-POOL-START is O_EXCL, written and fsync'ed before the pool; an existing file, a failed
    open / write / fsync or a short write means no pool and no worker; a start record without a workers record
    never reads as "no worker" (abandon still needs E-BOOT)."""
    api = _FakeApi()
    env = _env(api, tmp_path / "ok")
    fd.barrier_pool_run(env, _double, [1], 1, ["E1-theta0.7", 0, 1])
    assert env.events.index("pool_start_fsynced") < env.events.index("pool_created")
    rec = json.loads((env.record_dir / "000001.pool-000001.start").read_bytes())
    assert tuple(sorted(rec)) == tuple(sorted(fd.POOL_START_FIELDS)) and (rec["pool_id"], rec["planned_max_workers"]) \
        == (1, 1) and rec["unit_id"] == ["E1-theta0.7", 0, 1]
    for name, io in (("exists", fd.REAL_IO), ("open", fd.ExclusiveIO(opener=_oserror)),
                     ("write", fd.ExclusiveIO(writer=_oserror)), ("short", fd.ExclusiveIO(writer=lambda h, v: 0)),
                     ("fsync", fd.ExclusiveIO(syncer=_oserror))):
        a = _FakeApi()
        e = _env(a, tmp_path / name, io=io)
        if name == "exists":
            (e.record_dir / "000001.pool-000001.start").write_bytes(b"x")
        with pytest.raises(fd.StopImplementation):
            fd.barrier_pool_run(e, _double, [1], 1, ["u"])
        assert e.events == [] and not a.members                              # no pool, no worker
    root = tmp_path / "abandon"
    h = fd.acquire_lock(root, _lock(_FakeApi()))
    fd.write_pool_start(root / fd.LOCK_DIR, 1, h.sha256, 1, run_id_="r", unit_id=["u"], driver_pid=100,
                        driver_creation_time=5000, planned_max_workers=2)
    fd.write_udr(root, _udr_line(1, "LOCK_ABANDON", f"lock=000001,lock_sha256={h.sha256}", "ABANDON"), "x", CODE)
    with pytest.raises(fd.StopImplementation, match="E-BOOT does not hold"):
        fd.abandon_lock(root, 1, [1], _FakeApi(), rb1_verified=True)          # same boot: start-only is not "none"


@it_group_d
def test_it8_workers_record_order_and_failure_injection(tmp_path):
    """IT-8 (AC-J10): (A) / (B) verified -> O_EXCL -> write -> fsync -> release; any failure of the workers record
    means no release; verified != expected writes nothing; the record has exactly its fields."""
    api = _FakeApi()
    env = _env(api, tmp_path / "ok")
    fd.barrier_pool_run(env, _double, [1, 2, 3], 2, ["u"])
    assert env.events == ["pool_start_fsynced", "pool_created", "workers_verified", "workers_fsynced", "released",
                          "rechecked"]
    rec = json.loads((env.record_dir / "000001.workers-000001").read_bytes())
    assert tuple(sorted(rec)) == tuple(sorted(fd.WORKERS_FIELDS)) and "barrier_release_pending" not in rec
    assert rec["expected_worker_count"] == rec["verified_worker_count"] == 2
    assert rec["target_job_membership_verified"] is True and rec["python_version"] == sys.version
    assert rec["workers"] == [{"pid": 1000, "creation_time": 6000}, {"pid": 1001, "creation_time": 6001}]
    for name, fail_write, fail_sync, short in (("write", True, False, False), ("fsync", False, True, False),
                                               ("short", False, False, True), ("exists", False, False, False)):
        state = {}

        def opener(path, flags, mode, state=state):
            state["path"] = path
            return os.open(path, flags, mode)

        def is_workers_record(state):                       # the file name only (the tmp path holds the test name)
            return os.path.basename(state["path"]).startswith("000001.workers-")

        def writer(handle, view, state=state, fail=fail_write, short=short):
            if is_workers_record(state) and (fail or short):
                if fail:
                    raise OSError("injected")
                return 0
            return os.write(handle, view)

        def syncer(handle, state=state, fail=fail_sync):
            if is_workers_record(state) and fail:
                raise OSError("injected")
            os.fsync(handle)

        a = _FakeApi()
        e = _env(a, tmp_path / name, io=fd.ExclusiveIO(opener=opener, writer=writer, syncer=syncer))
        workers_file = e.record_dir / "000001.workers-000001"
        if name == "exists":
            workers_file.write_bytes(b"x")
        with pytest.raises(fd.StopImplementation, match={"write": "write / fsync failed", "fsync": "write / fsync failed",
                                                         "short": "short write", "exists": "already exists"}[name]):
            fd.barrier_pool_run(e, _double, [1, 2], 2, ["u"])
        assert e.events == ["pool_start_fsynced", "pool_created", "workers_verified"], name   # start record intact
        assert set(json.loads((e.record_dir / "000001.pool-000001.start").read_bytes())) == set(fd.POOL_START_FIELDS)
        assert workers_file.read_bytes() == {"write": b"", "short": b"", "exists": b"x"}.get(
            name, workers_file.read_bytes()), name                              # partial / foreign file left as is
        if name == "fsync":
            assert set(json.loads(workers_file.read_bytes())) == set(fd.WORKERS_FIELDS)   # written, fsync failed


# --- groups A-C (real Windows job, test-only processes) and RB-1: separately approved execution only --------------

TESTS_DIR = FsPath(__file__).resolve().parent
IT_TIMEOUT_S = 180
IT_CASES = {"it1": (1, 1), "it2": (2, 2), "it3a": (2, 5), "it3b": (2, 2), "it3c": (2, 2), "it4": (1, 1),
            "it5": (2, 2)}                                                   # case -> (workers, tasks)


def _it_task(x):
    """IT worker task: what the worker sees of itself (no file, no research function)."""
    api = fd.win_api()
    now, _ = api.now_and_tick()
    return {"x": x, "pid": os.getpid(), "creation_time": api.creation_time(None), "barrier_passed": now,
            "in_any_job": api.in_job(None, None), "innermost_flags": api.job_limit_flags(None)}


def _it_wait_long(x):
    import time
    time.sleep(3600)
    return x


def _it4_plain_pool(api, job):
    """IT-4 without pool records (R-9 allows them for IT-2 / IT-3a only): one test-only worker through a plain spawn
    pool started inside the target job; while the pool is still open the driver checks that worker against the
    target job (same pid and creation time, IsProcessInJob, the job's pid list). Writes no file."""
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=1, mp_context=ctx) as pool:
        r = pool.submit(_it_task, 0).result(timeout=60)
        h = api.open_process(r["pid"])
        try:
            r["creation_matches"] = api.creation_time(h) == r["creation_time"]
            r["in_target_job"] = api.in_job(h, job)
        finally:
            api.close(h)
        r["job_pids"] = api.job_pids(job)
    return [r]


class _MemoryIO:
    """ExclusiveIO stand-in for IT-3b / IT-3c / IT-5 (R-9: their driver writes no file). Records live in memory by file
    name with the O_EXCL rule kept; when emit is set, the fsync of a pool workers record publishes that record on
    stdout (IT-5). Its "fsync" touches no disk and is never evidence of an NTFS fsync."""

    def __init__(self, emit=None):
        self.files, self.handles, self.next, self.emit = {}, {}, 1, emit

    def io(self):
        return fd.ExclusiveIO(opener=self.open, writer=self.write, syncer=self.sync, closer=self.close)

    def open(self, path, flags, mode):
        name = os.path.basename(path)
        if name in self.files:
            raise FileExistsError(name)
        self.files[name], self.handles[self.next] = bytearray(), name
        self.next += 1
        return self.next - 1

    def write(self, handle, view):
        self.files[self.handles[handle]] += bytes(view)
        return len(view)

    def sync(self, handle):
        name = self.handles[handle]
        if self.emit is not None and name.startswith("000001.workers-"):
            self.emit(json.loads(bytes(self.files[name])))

    def close(self, handle):
        self.handles.pop(handle)


IT_MEMORY_CASES = ("it3b", "it3c", "it5")
IT5_STAGE = "workers_verified_record_fsynced_in_memory_before_release"


def _it_driver(case, record_dir):
    """The IT test driver (a test-only process, never pytest itself): assigns itself to a test-only target job, runs
    one case and prints one JSON line. Only IT-2 / IT-3a write the two pool records into record_dir (R-9); IT-3b,
    IT-3c and IT-5 keep them in memory (_MemoryIO), IT-1 and IT-4 have none. IT-5 also prints the verified workers
    record, before the release, as its evidence line."""
    api = fd.win_api()
    workers, tasks = IT_CASES[case]
    out = {"case": case, "driver_pid": os.getpid()}
    job = fd.setup_target_job(api)
    out.update(prior_job=job["prior_job_membership"], flags=job["flags"], in_target=api.in_job(None, job["job"]),
               inheritable=api.inheritable(job["job"]))
    if case == "it4":
        try:
            out["results"] = _it4_plain_pool(api, job["job"])
        except Exception as exc:                 # reported, never retried; the pool closes normally
            out["error"] = f"{type(exc).__name__}: {exc}"
    elif case != "it1":
        driver_ct = api.creation_time(None)

        def emit(record):                        # IT-5 evidence: one JSON line, before the release
            print(json.dumps({"stage": IT5_STAGE, "storage": "MEMORY_NOT_DISK", "driver_pid": os.getpid(),
                              "driver_creation_time": driver_ct, "driver_executable": sys.executable,
                              "prior_job_membership": job["prior_job_membership"],
                              "job": {"handle": job["job"], "limit_flags": api.job_limit_flags(job["job"]),
                                      "inheritable": api.inheritable(job["job"]), "pids": api.job_pids(job["job"])},
                              "workers": record["workers"], "record": record}), flush=True)

        memory = _MemoryIO(emit if case == "it5" else None) if case in IT_MEMORY_CASES else None
        env = fd.BarrierEnv(api=api, job=job["job"], record_dir=FsPath(record_dir), lock_number=1,
                            lock_sha256="a" * 64, driver_pid=os.getpid(), driver_creation_time=driver_ct,
                            run_id="it", ready_timeout_s=0.001 if case == "it3b" else 60.0,
                            release_timeout_s={"it3b": 5.0, "it3c": 0.0}.get(case, 60.0), events=[],
                            io=memory.io() if memory else fd.REAL_IO)
        try:
            out["results"] = fd.barrier_pool_run(env, _it_wait_long if case == "it5" else _it_task,
                                                 list(range(tasks)), workers, ["it", 0, tasks])
        except Exception as exc:                 # IT-3b / IT-3c observe the STOP or BrokenProcessPool itself
            out["error"] = f"{type(exc).__name__}: {exc}"
        out["events"] = env.events
        if memory:
            out["memory_records"] = sorted(memory.files)
            out["memory_record_contents"] = {name: _parsed_or_unparseable(data) for name, data in memory.files.items()}
    print(json.dumps(out), flush=True)


def _parsed_or_unparseable(data):
    try:
        return json.loads(bytes(data))
    except ValueError:
        return "UNPARSEABLE"


def _it_record_dir(tmp_path):
    """R-9 isolation: a fresh, empty pytest directory outside the worktree, data/, the research output root, every
    g7-core-lock/ and user-decisions/ and the scratchpad (STOP otherwise)."""
    d = (tmp_path / "it_records").resolve()
    root = fd.repo_root().resolve()
    for other in (root, root / "data", root / fd.RESEARCH_OUTPUT_DIR):
        assert other not in d.parents and d != other and d not in other.parents, other
    assert not any(part in (fd.LOCK_DIR, fd.UDR_DIR, "scratchpad") for part in d.parts)
    d.mkdir()
    assert not any(d.iterdir())
    return d


def _it_timeout_stop(proc, record_dir):
    """R-9 timeout: no process is ended. The residual test processes (pid, creation time, parent, executable) are
    reported read-only and the whole test session STOPs."""
    residual = []
    try:
        api = fd.win_api()
        snap = api.snapshot_names()
        family, frontier = {proc.pid}, [proc.pid]
        while frontier:
            p = frontier.pop()
            kids = [c for c, (parent, _) in snap.items() if parent == p and c not in family]
            family.update(kids)
            frontier += kids
        for pid in sorted(family & set(snap)):
            h = api.open_process(pid)
            try:
                residual.append([pid, api.creation_time(h), snap[pid][0], snap[pid][1]])
            finally:
                api.close(h)
    except Exception as exc:                     # the report itself must not end anything
        residual.append(f"read failed: {exc}")
    pytest.exit(f"IT timeout: STOP (no process ended); residual test processes {residual}; records in {record_dir}",
                returncode=3)


def _it_start(case, record_dir):
    code = (f"import sys; sys.path.insert(0, {str(TESTS_DIR)!r}); import test_v06_futility_diag as t; "
            f"t._it_driver({case!r}, {str(record_dir)!r})")
    return subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _it_start_direct(case, record_dir):
    """IT-5 only: start the driver as the base interpreter itself, not through the venv launcher, so the process
    pytest holds IS the driver (proc.pid == driver pid). As multiprocessing's spawn does in a venv
    (popen_spawn_win32.py:62-67), __PYVENV_LAUNCHER__ keeps the venv's site-packages. close_fds (the Popen default)
    passes no handle, so the driver holds no job handle but the target job it creates."""
    code = (f"import sys; sys.path.insert(0, {str(TESTS_DIR)!r}); import test_v06_futility_diag as t; "
            f"t._it_driver({case!r}, {str(record_dir)!r})")
    env = {**os.environ, "__PYVENV_LAUNCHER__": sys.executable}
    return subprocess.Popen([sys._base_executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env, close_fds=True)


IT_EVIDENCE = os.environ.get("FUTDIAG_IT_EVIDENCE") == "1"   # opt-in structured evidence (IT-3b, IT-3c, IT-5)
NOT_RECORDED = "NOT_RECORDED"


def _it_evidence(test_id, out):
    """The driver JSON of a memory-IO case, as recorded: nothing is inferred; a value the driver did not record is
    NOT_RECORDED (the driver creation time and workers come only from the in-memory pool records it wrote)."""
    mem = out.get("memory_record_contents", {})
    start, workers = mem.get("000001.pool-000001.start"), mem.get("000001.workers-000001")
    err = out.get("error")
    return {"test_id": test_id, "driver_pid": out.get("driver_pid", NOT_RECORDED),
            "driver_creation_time": start["driver_creation_time"] if isinstance(start, dict) else NOT_RECORDED,
            "workers": workers["workers"] if isinstance(workers, dict) else NOT_RECORDED,
            "error_type": err.split(": ", 1)[0] if err else NOT_RECORDED,
            "error_message": err.split(": ", 1)[1] if err and ": " in err else (err or NOT_RECORDED),
            "events": out.get("events", NOT_RECORDED),
            "released": ("released" in out["events"]) if "events" in out else NOT_RECORDED,
            "job": {k: out.get(k, NOT_RECORDED) for k in ("prior_job", "flags", "in_target", "inheritable")},
            "storage": "MEMORY_NOT_DISK" if out.get("case") in IT_MEMORY_CASES else "REAL_IO",
            "memory_records": out.get("memory_records", NOT_RECORDED)}


def _it_run(case, tmp_path):
    rec = _it_record_dir(tmp_path)
    proc = _it_start(case, rec)
    try:
        out, err = proc.communicate(timeout=IT_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        _it_timeout_stop(proc, rec)
    assert proc.returncode == 0, err
    result = json.loads(out.strip().splitlines()[-1])
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(rec.iterdir())}
    print(json.dumps({"case": case, "record_dir": str(rec), "files": files}))       # evidence for the report
    if IT_EVIDENCE and case in ("it3b", "it3c"):                              # printed before the test's asserts
        print(json.dumps({"it_evidence": _it_evidence(case, result)}))
    return result, rec


def _record_mtime(path):
    return path.stat().st_mtime_ns // 100 + fd._FILETIME_UNIX_EPOCH


@it_group_a
def test_it1_nested_job_assignment_and_readback(tmp_path):
    """IT-1 (AC-J4, AC-J1): inside the observed outer job, the test driver's own target job is created, read back as
    exactly KILL_ON_JOB_CLOSE and joined."""
    out, _ = _it_run("it1", tmp_path)
    assert (out["flags"], out["in_target"], out["inheritable"]) == (fd.JOB_KILL_ON_CLOSE, True, False)
    assert isinstance(out["prior_job"], bool)


def _check_real_records(out, rec, workers, tasks):
    assert "error" not in out, out
    results = out["results"]
    assert [r["x"] for r in results] == list(range(tasks))
    seen = sorted({(r["pid"], r["creation_time"]) for r in results})
    wk = json.loads((rec / "000001.workers-000001").read_bytes())
    assert sorted((w["pid"], w["creation_time"]) for w in wk["workers"]) == seen and len(seen) == workers
    assert wk["verified_worker_count"] == wk["expected_worker_count"] == workers
    assert _record_mtime(rec / "000001.pool-000001.start") <= min(ct for _, ct in seen)
    assert all(_record_mtime(rec / "000001.workers-000001") <= r["barrier_passed"] for r in results)
    assert sorted(p.name for p in rec.iterdir()) == ["000001.pool-000001.start", "000001.workers-000001"]
    assert out["events"] == ["pool_start_fsynced", "pool_created", "workers_verified", "workers_fsynced", "released",
                             "rechecked"]


@it_group_a
def test_it2_workers_are_driver_children_in_the_target_job(tmp_path):
    """IT-2 (AC-J1, AC-J2; AC-J9 / AC-J10 integration part): real workers, verified as direct children in the target
    job before the real O_EXCL / write / fsync records, released only after them."""
    out, rec = _it_run("it2", tmp_path)
    _check_real_records(out, rec, 2, 2)


@it_group_a
def test_it3a_barrier_worker_count_and_order(tmp_path):
    """IT-3a (AC-J3; AC-J9 / AC-J10 integration part): five tasks, two workers created one per submit, every result
    after the release, the real records in order."""
    out, rec = _it_run("it3a", tmp_path)
    _check_real_records(out, rec, 2, 5)


@it_group_a
def test_it4_job_handle_not_inherited(tmp_path):
    """IT-4 (AC-J5): the target job handle is not inheritable; the worker started inside the target job is in it (the
    driver's IsProcessInJob and the job's pid list) and its innermost job is the target policy. No pool record is
    written (R-9: records are IT-2 / IT-3a only)."""
    out, rec = _it_run("it4", tmp_path)
    assert out["inheritable"] is False and "error" not in out, out
    (r,) = out["results"]
    assert r["in_any_job"] and r["innermost_flags"] & fd.JOB_KILL_ON_CLOSE
    assert r["creation_matches"] and r["in_target_job"]
    assert out["driver_pid"] in r["job_pids"] and r["pid"] in r["job_pids"]
    assert not any(rec.iterdir())                                             # nothing written (R-9)


@it_group_b
def test_it3b_ready_timeout_stops_without_release(tmp_path):
    """IT-3b (AC-J3, R-4c B1): the driver's ready timeout is a STOP without a release; the workers' barrier wait
    then fails and the pool breaks (stdlib may end its own test workers)."""
    out, rec = _it_run("it3b", tmp_path)
    assert "ready timeout" in out.get("error", "") and "results" not in out
    assert "released" not in out["events"] and "workers_fsynced" not in out["events"]
    assert out["memory_records"] == ["000001.pool-000001.start"]               # no workers record (memory, R-9)
    assert not any(rec.iterdir())                                             # no file written (R-9)


@it_group_b
def test_it3c_initializer_failure_breaks_the_pool(tmp_path):
    """IT-3c (AC-J3, R-4c B1): an initializer that fails (no release in time) breaks the pool before any release; no
    unit result. Expected: the failed workers are gone by the verification (after the 0.5 s extra-report wait), so
    the verification STOPs; the timing is UNVERIFIED until run."""
    out, rec = _it_run("it3c", tmp_path)
    assert "results" not in out and out.get("error"), out
    assert "released" not in out["events"] and "workers_fsynced" not in out["events"], out
    assert "000001.workers-000001" not in out["memory_records"]
    assert not any(rec.iterdir())                                             # no file written (R-9)


@it_group_c
def test_it5_driver_forced_end_and_kill_on_job_close(tmp_path):
    """IT-5 (AC-J7, R-4c B2 / B3): the test driver is ended while its released workers run; KILL_ON_JOB_CLOSE must
    leave none of the verified workers alive (audit evidence only, never an abandon basis). The workers are known
    from the driver's stdout evidence line (stage, driver, target job, workers' pid and creation time), printed
    before the release; the driver writes no file (R-9). The same (pid, creation time) are checked before (ALIVE)
    and after the driver is ended.
    Causality: the driver is started directly (no venv launcher), so the process ended is the driver itself
    (proc.pid == driver pid, its creation time checked); Windows does not end children with their parent, the
    driver holds no handle of any other job (close_fds; it creates only the target job, non-inheritable), and the
    jobs of pytest / Claude Code stay open because their own processes keep running. The only job whose last
    handle closes is the target job, which the evidence shows the workers belong to."""
    import time
    rec = _it_record_dir(tmp_path)
    proc = _it_start_direct("it5", rec)
    lines = queue.Queue()
    threading.Thread(target=lambda: [lines.put(line) for line in proc.stdout], daemon=True).start()
    deadline, evidence = time.monotonic() + IT_TIMEOUT_S, None
    while evidence is None:
        try:
            line = json.loads(lines.get(timeout=max(0.1, deadline - time.monotonic())))
        except queue.Empty:
            _it_timeout_stop(proc, rec)
        evidence = line if line.get("stage") == IT5_STAGE else None
        assert proc.poll() is None or evidence is not None, proc.stderr.read()
    print(json.dumps(evidence))
    api = fd.win_api()
    if IT_EVIDENCE:                                                           # phase 1: the driver's own line
        parents = api.snapshot()
        print(json.dumps({"it_evidence": {
            "test_id": "it5", "phase": "evidence_line_before_release", "storage": evidence["storage"],
            "proc_pid": proc.pid, "driver_pid": evidence["driver_pid"],
            "driver_creation_time": evidence["driver_creation_time"],
            "workers": evidence["workers"], "job": evidence["job"],
            "worker_parent_pid_in_snapshot": {str(w["pid"]): parents.get(w["pid"], NOT_RECORDED)
                                              for w in evidence["workers"]}}}))
    assert evidence["storage"] == "MEMORY_NOT_DISK" and evidence["job"]["limit_flags"] == fd.JOB_KILL_ON_CLOSE
    assert evidence["driver_pid"] == proc.pid and evidence["driver_pid"] != os.getpid()   # the driver, not pytest
    h = api.open_process(proc.pid)
    try:
        assert api.creation_time(h) == evidence["driver_creation_time"]      # the same driver process
    finally:
        api.close(h)
    assert evidence["job"]["inheritable"] is False
    recorded = [(w["pid"], w["creation_time"]) for w in evidence["workers"]]
    assert len(recorded) == 2 and sorted(evidence["job"]["pids"]) == sorted([proc.pid, *(p for p, _ in recorded)])
    assert all(parent == proc.pid for p, parent in api.snapshot().items() if p in {q for q, _ in recorded})
    time.sleep(2.0)                                                           # released: the workers run the task
    before = fd.investigate(api, (evidence["driver_pid"], evidence["driver_creation_time"]), recorded)
    print(json.dumps({"before": before}))
    if IT_EVIDENCE:                                                           # phase 2: observed before the end
        print(json.dumps({"it_evidence": {"test_id": "it5", "phase": "before_driver_end",
                                          "driver": before["e_pid"], "workers": before["e_workers"]}}))
    assert before["e_pid"] == "ALIVE" and all(s == "ALIVE" for _, _, s in before["e_workers"]), before
    proc.terminate()                                                          # group C only (R-4c B3)
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        _it_timeout_stop(proc, rec)
    time.sleep(2.0)
    after = fd.investigate(fd.win_api(), (evidence["driver_pid"], evidence["driver_creation_time"]), recorded)
    print(json.dumps({"after": after}))
    if IT_EVIDENCE:                                                           # phase 3: a separate later observation
        print(json.dumps({"it_evidence": {"test_id": "it5", "phase": "after_driver_end",
                                          "driver": after["e_pid"], "workers": after["e_workers"],
                                          "causality": "NOT_PROVEN_BY_OUTPUT (see the test's docstring argument)"}}))
    assert after["e_pid"] == "EXITED", after                                  # same driver (pid, ct), signalled
    assert all(state != "ALIVE" for _, _, state in after["e_workers"]), after
    assert [[p, c] for p, c, _ in after["e_workers"]] == [list(x) for x in recorded]   # the same workers compared
    assert not any(rec.iterdir())                                             # no file written (R-9)


@rb1_check
def test_rb1_boot_reading_on_this_host():
    """RB-1 (R-9): read-only S1 / S2 / host_id on this host, for the chat report. No process, job or file."""
    r = fd.rb1_reading()
    print(json.dumps(r))
    assert abs(r["s1_minus_s2_s"]) <= 120 and set(r["host_id"]) == {"computer_name", "machine_guid"}


# --- ERRATA-007 (G3): contract hash scope and identity across G5 pilot, G6 and G7 (FAKE git, no MC run) ----------

CAL_FILE_SHA = "e" * 64
ERRATA007_KEYS = ["config", "prereg", *(f"ERRATA-{i:03d}" for i in range(1, 8))]
PILOT_VARIANTS = {"code_sha": "f" * 40, "code_tree": "f" * 40, "config_sha256": "0" * 64, "prereg_sha256": "0" * 64}


def _stage_parts(**pilot_over):
    """CAL (null calibration_sha256), NOW (the used file's sha256) and a PILOT run_spec of the same identity."""
    cal_ident = fd.research_identity(git=_fake_git())
    now = fd.research_identity(git=_fake_git(), calibration_sha256=CAL_FILE_SHA)
    pilot = _spec(**{"mode": "pilot", "code_sha": now["git_head"], "code_tree": now["git_tree"],
                     "config_sha256": now["contract_sha256"]["config"],
                     "prereg_sha256": now["contract_sha256"]["prereg"], **pilot_over})
    return cal_ident, now, pilot


def _invariant_variants(ident):
    """One different value per stage-invariant field."""
    return {"git_head": "3" * 40, "git_tree": "4" * 40, "worktree_clean": False, "base_sha": "0" * 40,
            "futility_diag_source": {**ident["futility_diag_source"], "sha256": "0" * 64},
            "mcv06_source_identity": {}, "contract_sha256": {**ident["contract_sha256"], "ERRATA-007": "0" * 64}}


def test_errata007_t7a_contract_scope_and_tamper_stops(tmp_path):
    """T-7a: exactly config, prereg, ERRATA-001..007 with the LF sha256 of the real files; a changed ERRATA-006 or
    ERRATA-007 stops research_identity."""
    assert list(fd.CONTRACT_FILES) == ERRATA007_KEYS and list(fd.CONTRACT_SHA256) == ERRATA007_KEYS
    assert fd.CONTRACT_FILES["ERRATA-006"] == "docs/tasks/BT4-FUTILITY-01/ERRATA-006.md"
    assert fd.CONTRACT_FILES["ERRATA-007"] == "docs/tasks/BT4-FUTILITY-01/ERRATA-007.md"
    assert fd.CONTRACT_SHA256["ERRATA-006"] == "63c08d10131a71911e849f60b4ff09c542853821c1a3458a68369ffa1bc6fd11"
    assert fd.CONTRACT_SHA256["ERRATA-007"] == "25841248dae87d0f5568c72e9b35b00ea1a79530f1e546c7d5c312cb67d56cda"
    root = fd.repo_root()
    for k, rel in fd.CONTRACT_FILES.items():
        lf = (root / rel).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(lf).hexdigest() == fd.CONTRACT_SHA256[k], k
    ident = fd.research_identity(git=_fake_git())
    assert list(ident["contract_sha256"]) == ERRATA007_KEYS and ident["contract_sha256"] == fd.CONTRACT_SHA256
    for name in ("ERRATA-006", "ERRATA-007"):
        base = tmp_path / name
        for rel in fd.CONTRACT_FILES.values():
            (base / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / rel, base / rel)
        p = base / fd.CONTRACT_FILES[name]
        p.write_bytes(p.read_bytes() + b"\n")
        with pytest.raises(fd.StopImplementation, match=rf"accepted sha256: \['{name}'\]"):
            fd.research_identity(base, git=_fake_git())


def test_errata007_t7b_t7e_matching_identity_passes_and_calibration_sha_is_per_stage():
    """T-7b: CAL, PILOT and NOW in agreement pass the G5 pilot (no PILOT) and G6 / G7 (PILOT) checks. T-7e:
    calibration_sha256 is null in CAL and the used file's sha256 in NOW; the two are never compared."""
    cal_ident, now, pilot = _stage_parts()
    assert cal_ident["calibration_sha256"] is None and now["calibration_sha256"] == CAL_FILE_SHA
    fd.check_stage_identity(cal_ident, now, CAL_FILE_SHA)                      # G5 pilot
    fd.check_stage_identity(cal_ident, now, CAL_FILE_SHA, pilot)               # G6, G7
    other = "f" * 64                                                           # another file: NOW follows the file
    fd.check_stage_identity(cal_ident, {**now, "calibration_sha256": other}, other, pilot)
    with pytest.raises(fd.StopImplementation, match="not null"):              # CAL = NOW's value is not accepted
        fd.check_stage_identity({**cal_ident, "calibration_sha256": CAL_FILE_SHA}, now, CAL_FILE_SHA, pilot)
    assert fd.STAGE_INVARIANT_FIELDS == ("git_head", "git_tree", "worktree_clean", "base_sha",
                                         "futility_diag_source", "mcv06_source_identity", "contract_sha256")
    assert set(fd.IDENTITY_FIELDS) - set(fd.STAGE_INVARIANT_FIELDS) == {"calibration_sha256"}


def test_errata007_t7c_each_field_mismatch_stops():
    """T-7c: each of the 7 stage-invariant fields (in CAL or in NOW) and each PILOT field stops, naming the field."""
    cal_ident, now, pilot = _stage_parts()
    for field, value in _invariant_variants(now).items():
        for c, n in (({**cal_ident, field: value}, now), (cal_ident, {**now, field: value})):
            for spec in (None, pilot):
                with pytest.raises(fd.StopImplementation, match=rf"G5 calibration identity: \['{field}'\]"):
                    fd.check_stage_identity(c, n, CAL_FILE_SHA, spec)
    for field, value in PILOT_VARIANTS.items():
        with pytest.raises(fd.StopImplementation, match=rf"pilot run_spec differs .*: \['{field}'\]"):
            fd.check_stage_identity(cal_ident, now, CAL_FILE_SHA, {**pilot, field: value})


def test_errata007_t7d_missing_extra_and_format_stop(tmp_path):
    """T-7d: CAL / NOW fields missing or extra, CAL.git_tree not 40 lowercase hex (also in validate_calibration),
    PILOT run_spec absent / not canonical / missing a field / malformed, NOW.calibration_sha256 not the file's: each
    a STOP."""
    cal_ident, now, pilot = _stage_parts()
    drop = {k: v for k, v in cal_ident.items() if k != "git_tree"}
    for c, n, match in ((drop, now, r"calibration identity fields: missing \['git_tree'\]"),
                        ({**cal_ident, "extra": 1}, now, r"calibration identity fields: .*unexpected \['extra'\]"),
                        (cal_ident, {k: v for k, v in now.items() if k != "base_sha"}, "current identity fields"),
                        (cal_ident, {**now, "extra": 1}, "current identity fields"),
                        ([], now, "calibration identity fields")):
        with pytest.raises(fd.StopImplementation, match=match):
            fd.check_stage_identity(c, n, CAL_FILE_SHA, pilot)
    for tree in ("A" * 40, "2" * 39, int("2" * 40), None):
        with pytest.raises(fd.StopImplementation, match="git_tree is not 40 lowercase hex"):
            fd.check_stage_identity({**cal_ident, "git_tree": tree}, now, CAL_FILE_SHA, pilot)
        with pytest.raises(fd.StopImplementation, match="research identity"):
            fd.build_calibration(fd.RESEARCH, *_research_parts(), {**cal_ident, "git_tree": tree})
    fd.build_calibration(fd.RESEARCH, *_research_parts(), cal_ident)          # the valid tree still passes
    with pytest.raises(fd.StopImplementation, match=r"\['calibration_sha256'\]"):
        fd.check_stage_identity(cal_ident, now, "0" * 64, pilot)
    with pytest.raises(fd.StopImplementation, match=r"\['calibration_sha256'\]"):
        fd.check_stage_identity(cal_ident, {**now, "calibration_sha256": None}, CAL_FILE_SHA)
    for spec in ({k: v for k, v in pilot.items() if k != "code_tree"}, {**pilot, "workers": 2}):
        with pytest.raises(fd.StopImplementation, match="run_spec fields"):
            fd.check_stage_identity(cal_ident, now, CAL_FILE_SHA, spec)
    for spec in ({**pilot, "code_sha": "A" * 40}, {**pilot, "prereg_sha256": "d" * 63}):
        with pytest.raises(fd.StopImplementation, match="invalid run_spec fields"):
            fd.check_stage_identity(cal_ident, now, CAL_FILE_SHA, spec)
    with pytest.raises(fd.StopImplementation, match="not an object"):
        fd.check_stage_identity(cal_ident, now, CAL_FILE_SHA, [pilot])
    d = tmp_path / "pilot"
    d.mkdir()
    with pytest.raises(fd.StopImplementation, match="is missing"):
        fd.read_pilot_spec(d)
    for data, match in ((json.dumps(pilot, indent=1).encode(), "not canonical"), (b"{", "malformed"),
                        (fd.canonical_bytes([pilot]), "not canonical"),
                        (fd.canonical_bytes({**pilot, "code_sha": "A" * 40}), "invalid run_spec fields"),
                        (fd.canonical_bytes({k: v for k, v in pilot.items() if k != "reps"}), "run_spec fields")):
        (d / fd.RUN_SPEC_FILE).write_bytes(data)
        with pytest.raises(fd.StopImplementation, match=match):
            fd.read_pilot_spec(d)
    spec_bytes = fd.run_spec_bytes(pilot)
    (d / fd.RUN_SPEC_FILE).write_bytes(spec_bytes)
    assert fd.read_pilot_spec(d) == (pilot, hashlib.sha256(spec_bytes).hexdigest())


def _stage_dirs(tmp_path, research_cal, **pilot_over):
    """Output root with the RESEARCH calibration (fake HEAD 1 x 40) and a pilot directory holding only its run_spec."""
    cal, sha = research_cal
    tmp_path.mkdir(parents=True, exist_ok=True)
    root = _out_root(tmp_path)
    cal_dir = root / f"g5-cal-{SHA12}"
    assert fd.write_calibration(cal_dir, cal, git=_fake_git()) == sha
    pilot_dir = root / f"g5-pilot-{SHA12}"
    pilot_dir.mkdir()
    ident = cal["identity"]
    spec = _spec(**{"mode": "pilot", "code_sha": ident["git_head"], "code_tree": ident["git_tree"],
                    "config_sha256": ident["contract_sha256"]["config"],
                    "prereg_sha256": ident["contract_sha256"]["prereg"], **pilot_over})
    (pilot_dir / fd.RUN_SPEC_FILE).write_bytes(fd.run_spec_bytes(spec))
    return root, cal_dir, pilot_dir


class _Reached(Exception):
    """Raised by the step that follows the ERRATA-007 check: the check passed and nothing was written yet."""


def _reach(*a, **k):
    raise _Reached


class _NoApi:
    """A G7 api that records any use: the ERRATA-007 check must STOP before the target job is set up."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        self.calls.append(name)
        raise AssertionError(f"api.{name} used before the identity check")


def test_errata007_t7f_g5_pilot_checks_before_the_run_directory(research_cal, tmp_path, monkeypatch):
    """T-7b / T-7f (G5 pilot): CAL = NOW passes to the next step; a different HEAD or tree stops before the run
    directory exists and leaves the calibration directory unchanged."""
    root, cal_dir, _ = _stage_dirs(tmp_path, research_cal)
    before = _snapshot(root)
    for git, field in ((_fake_git(head="3" * 40), "git_head"), (_fake_git(tree="4" * 40), "git_tree")):
        run_dir = root / f"g5-pilot-{git(root, 'rev-parse', 'HEAD')[:12]}-x"
        with pytest.raises(fd.StopImplementation, match=rf"G5 calibration identity: \['{field}'\]"):
            fd.g5_pilot(run_dir, cal_dir, unit_size=2, workers=1, git=git)
        assert not run_dir.exists() and _snapshot(root) == before
    monkeypatch.setattr(fd, "check_run_name", _reach)                        # the step after the check
    with pytest.raises(_Reached):
        fd.g5_pilot(root / f"g5-pilot-{SHA12}-new", cal_dir, unit_size=2, workers=1, git=_fake_git())
    assert _snapshot(root) == before


def test_errata007_t7f_g6_checks_before_g6_and_execution(research_cal, tmp_path, monkeypatch):
    """T-7b / T-7f (G6): CAL / PILOT / NOW in agreement reach write_g6; every mismatch, a missing or non-canonical
    pilot run_spec stops with g6/ and execution.json neither created nor changed."""
    cases = [({}, _fake_git(head="3" * 40), r"\['git_head'\]"), ({}, _fake_git(tree="4" * 40), r"\['git_tree'\]")]
    cases += [({k: v}, _fake_git(), rf"pilot run_spec differs .*\['{k}'\]") for k, v in PILOT_VARIANTS.items()]
    for i, (over, git, match) in enumerate(cases):
        root, cal_dir, pilot_dir = _stage_dirs(tmp_path / f"c{i}", research_cal, **over)
        before = _snapshot(root)
        with pytest.raises(fd.StopImplementation, match=match):
            fd.g6_summarize(pilot_dir, cal_dir, git=git)
        assert _snapshot(root) == before and not (pilot_dir / fd.G6_DIR).exists()
        assert not (pilot_dir / fd.EXECUTION_FILE).exists()
    for i, (data, match) in enumerate(((None, "is missing"), (b'{"mode": "pilot"}\n', "not canonical"))):
        root, cal_dir, pilot_dir = _stage_dirs(tmp_path / f"f{i}", research_cal)
        (pilot_dir / fd.RUN_SPEC_FILE).unlink()
        if data is not None:
            (pilot_dir / fd.RUN_SPEC_FILE).write_bytes(data)
        before = _snapshot(root)
        with pytest.raises(fd.StopImplementation, match=match):
            fd.g6_summarize(pilot_dir, cal_dir, git=_fake_git())
        assert _snapshot(root) == before and not (pilot_dir / fd.G6_DIR).exists()
    root, cal_dir, pilot_dir = _stage_dirs(tmp_path / "ok", research_cal)
    monkeypatch.setattr(fd, "write_g6", _reach)                               # the step after the check
    with pytest.raises(_Reached):
        fd.g6_summarize(pilot_dir, cal_dir, git=_fake_git())
    assert not (pilot_dir / fd.G6_DIR).exists() and not (pilot_dir / fd.EXECUTION_FILE).exists()


def _g7_at(root, cal_dir, pilot_dir, git, api):
    sha12 = git(root, "rev-parse", "HEAD").strip()[:12]
    return fd.g7_core(root, pilot_dir=pilot_dir, cal_dir=cal_dir, e1_dir=root / f"g7-E1-theta0.7-{sha12}",
                      p0_dir=root / f"g7-P0-theta0.7-{sha12}", v4_dir=root / f"g7-v4-{sha12}", workers=2,
                      pool_failure_policy=fd.G7_POOL_FAILURE_POLICY, git=git, api=api)


def _g7_untouched(root, before, api):
    assert api.calls == [] and not (root / fd.LOCK_DIR).exists() and _snapshot(root) == before
    assert not any(p.name.startswith("g7-") for p in root.iterdir())


def test_errata007_t7f_g7_missing_or_bad_pilot_run_spec_stops_first(research_cal, tmp_path, monkeypatch):
    """T-7d / T-7f (G7): the pilot run_spec is read before _verified_g6, so a missing or non-canonical file is a
    StopImplementation (not an OSError from verify_run), before the job, the lock or any G7 directory."""
    monkeypatch.setattr(fd.platform, "python_version", lambda: fd.G7_PYTHON)
    monkeypatch.setattr(fd.sys, "platform", "win32")
    for i, (data, match) in enumerate(((None, "pilot run_spec.json is missing"),
                                       (b'{"mode": "pilot"}\n', "pilot run_spec.json is not canonical"))):
        root, cal_dir, pilot_dir = _stage_dirs(tmp_path / f"f{i}", research_cal)
        (pilot_dir / fd.RUN_SPEC_FILE).unlink()
        if data is not None:
            (pilot_dir / fd.RUN_SPEC_FILE).write_bytes(data)
        before, api = _snapshot(root), _NoApi()
        with pytest.raises(fd.StopImplementation, match=match):                # the real _verified_g6 is not reached
            _g7_at(root, cal_dir, pilot_dir, _fake_git(), api)
        _g7_untouched(root, before, api)


def test_errata007_t7f_g7_checks_before_job_and_lock(research_cal, tmp_path, monkeypatch):
    """T-7b / T-7c / T-7f (G7): the check uses the NOW already computed and the pilot run_spec its VERIFIED g6/
    references; any mismatch stops before the api is used (no target job) and before the lock directory or a G7
    run directory exists."""
    monkeypatch.setattr(fd.platform, "python_version", lambda: fd.G7_PYTHON)
    monkeypatch.setattr(fd.sys, "platform", "win32")

    def g6_ref(pilot_dir, ref=None):                                         # a VERIFIED g6/ naming ref (or the file)
        sha = ref or hashlib.sha256((pilot_dir / fd.RUN_SPEC_FILE).read_bytes()).hexdigest()
        monkeypatch.setattr(fd, "_verified_g6", lambda d: ({"pilot": {"run_spec_sha256": sha}}, "a" * 64))

    cases = [({}, _fake_git(head="3" * 40), r"G5 calibration identity: \['git_head'\]", None),
             ({}, _fake_git(tree="4" * 40), r"G5 calibration identity: \['git_tree'\]", None),
             ({}, _fake_git(), "not the one g6/ references", "0" * 64)]
    cases += [({k: v}, _fake_git(), rf"pilot run_spec differs .*\['{k}'\]", None) for k, v in PILOT_VARIANTS.items()]
    for i, (over, git, match, ref) in enumerate(cases):
        root, cal_dir, pilot_dir = _stage_dirs(tmp_path / f"c{i}", research_cal, **over)
        g6_ref(pilot_dir, ref)
        before, api = _snapshot(root), _NoApi()
        with pytest.raises(fd.StopImplementation, match=match):
            _g7_at(root, cal_dir, pilot_dir, git, api)
        _g7_untouched(root, before, api)
    root, cal_dir, pilot_dir = _stage_dirs(tmp_path / "ok", research_cal)
    g6_ref(pilot_dir)
    monkeypatch.setattr(fd, "_load_spec_inputs", _reach)                      # the step after the check
    git_calls = []
    fake = _fake_git()

    def counting(root_, *args):
        git_calls.append(args)
        return fake(root_, *args)

    before, api = _snapshot(root), _NoApi()
    with pytest.raises(_Reached):
        _g7_at(root, cal_dir, pilot_dir, counting, api)
    _g7_untouched(root, before, api)
    assert git_calls.count(("rev-parse", "HEAD")) == 2                        # _g7_at's name + research_identity
    assert git_calls.count(("status", "--porcelain")) == 1                    # NOW once, no second git pass


def test_errata007_t7g_fixture_path_and_shared_functions_untouched():
    """T-7g / PRESERVED: the check is only in the research entry functions (G5 pilot, G6 summarize, G7 core), never
    in the TEST_FIXTURE smoke path or the shared g6_summary / write_g6 / verify_g6 / run_units; it calls no git."""
    import inspect
    for f in (fd.g5_pilot, fd.g6_summarize, fd.g7_core):
        assert inspect.getsource(f).count("check_stage_identity(") == 1, f.__name__
    for f in (fd.smoke, fd.g6_summary, fd.write_g6, fd.verify_g6, fd.run_units, fd.check_run_identity,
              fd.validate_calibration, fd.write_calibration, fd.g5_calibrate, fd.fixture_identity):
        assert "check_stage_identity" not in inspect.getsource(f), f.__name__
    src = inspect.getsource(fd.check_stage_identity) + inspect.getsource(fd.read_pilot_spec)
    assert "git(" not in src and "research_identity(" not in src and "subprocess" not in src
