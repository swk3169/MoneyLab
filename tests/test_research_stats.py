"""Statistics (ranks, correlations, BH, HAC, deterministic block bootstrap), spot cost model,
pre-registered decision rules and config hashing. SYNTHETIC inputs."""

import math
import random
from pathlib import Path

import pytest

from moneylab.analytics.spot_costs import (
    CostScenario,
    apply_fee_bps,
    round_trip_bps,
    round_trip_cost_bps,
    scenarios,
    slippage_bps,
)
from moneylab.research import stats as S
from moneylab.research.config import load_config
from moneylab.research.leaderboard import (
    CONFIRMED,
    INSUFFICIENT_EVIDENCE,
    LOCKED,
    NEGATIVE_EVIDENCE,
    PAPER_CANDIDATE,
    POSITIVE_BUT_UNCONFIRMED,
    REJECT,
    RESEARCH_MORE,
    TrainFit,
    decide,
    validation_verdict,
)
from moneylab.research.manifest import DRY_RUN, EVIDENCE, INSUFFICIENT, NOT_EVIDENCE, evidence_label

SRC = Path(__file__).resolve().parents[1] / "src" / "moneylab"


# --- basic statistics -----------------------------------------------------------------------

def test_rankdata_ties_and_spearman():
    assert S.rankdata([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]
    assert S.spearman([1, 2, 3, 4, 5], [5, 6, 7, 8, 7]) == pytest.approx(0.8207826816681233)
    assert S.pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)
    assert math.isnan(S.pearson([1, 1, 1], [1, 2, 3]))


def test_quantiles_bins_and_monotonicity():
    edges = S.quantile_edges(list(range(100)), 5)
    assert edges == pytest.approx([19.8, 39.6, 59.4, 79.2])
    assert S.assign_bin(19.8, edges) == 1 and S.assign_bin(-5, edges) == 0 and S.assign_bin(500, edges) == 4
    x = [float(i) for i in range(100)]
    qa = S.quantile_analysis(x, [v / 10 for v in x], edges)
    assert qa.counts == (20, 20, 20, 20, 20) and qa.monotonicity == pytest.approx(1.0)
    assert qa.top_bottom == pytest.approx((89.5 - 9.5) / 10)
    heavy_ties = S.quantile_analysis([0.0] * 50 + [1.0] * 50, [0.0] * 100, S.quantile_edges([0.0] * 80 + [1.0] * 20, 5))
    assert sum(heavy_ties.counts) == 100 and math.isnan(heavy_ties.monotonicity)  # < 3 filled bins


def test_directional_accuracy_skips_zero_moves_and_median_values():
    acc, used = S.directional_accuracy([1, 2, 3, 4, 3], [-1, 0, 2, 5, 9], median=3, direction=1)
    # (1,-1): below median -> down, hit; (2,0) zero move; (3,2) and (3,9) at the median; (4,5) up, hit
    assert used == 2 and acc == 1.0
    acc2, _ = S.directional_accuracy([1, 4], [-1, 5], median=3, direction=-1)
    assert acc2 == 0.0


def test_benjamini_hochberg_matches_reference_values():
    p = [0.01, 0.04, 0.03, 0.005, 0.5, float("nan")]
    q = S.benjamini_hochberg(p)
    # m = 5 tests: sorted 0.005,0.01,0.03,0.04,0.5 -> 0.025,0.025,0.05,0.05,0.5
    assert q[:5] == pytest.approx([0.025, 0.05, 0.05, 0.025, 0.5]) and math.isnan(q[5])


def test_newey_west_reduces_to_iid_se_without_autocorrelation():
    rng = random.Random(3)
    u = [rng.gauss(0, 1) for _ in range(4000)]
    iid = S.std(u) / math.sqrt(len(u))
    assert S.newey_west_se(u, 0) == pytest.approx(iid, rel=0.01)
    ar = [0.0]
    for _ in range(3999):
        ar.append(0.9 * ar[-1] + rng.gauss(0, 1))
    assert S.newey_west_se(ar, 50) > 3 * S.std(ar) / math.sqrt(len(ar))  # autocorrelation widens the SE


def test_hac_test_needs_enough_rows_for_its_lag():
    x = [float(i % 7) for i in range(50)]
    assert all(math.isnan(v) for v in S.hac_correlation_test(x, x, lag=90))
    t, p = S.hac_correlation_test(x * 10, [v + 0.1 * (i % 3) for i, v in enumerate(x * 10)], lag=10)
    assert t > 5 and p < 1e-6


def test_block_bootstrap_is_deterministic_and_needs_enough_blocks():
    rng = random.Random(11)
    x = [rng.gauss(0, 1) for _ in range(2000)]
    y = [0.3 * a + rng.gauss(0, 1) for a in x]
    a = S.bootstrap_corr_ci(x, y, mean_block=60, resamples=300, seed=42)
    b = S.bootstrap_corr_ci(x, y, mean_block=60, resamples=300, seed=42)
    c = S.bootstrap_corr_ci(x, y, mean_block=60, resamples=300, seed=43)
    assert a == b and a != c
    assert a[0] < S.spearman(x, y) < a[1] and a[0] > 0
    assert all(math.isnan(v) for v in S.bootstrap_corr_ci(x[:100], y[:100], mean_block=60, resamples=50, seed=1))
    num = [1.0 if i % 10 == 0 else 0.0 for i in range(1000)]
    den = [1.0 if i % 10 == 0 else 0.0 for i in range(1000)]
    assert S.bootstrap_ratio_ci(num, den, mean_block=20, resamples=100, seed=1) == pytest.approx((1.0, 1.0))
    assert S.derived_seed(7, "validation", "obi_5", "5") == S.derived_seed(7, "validation", "obi_5", "5")


def test_no_random_shuffle_in_research_code():
    for f in (SRC / "research").rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "shuffle" not in text and "random.sample" not in text, f


def test_nonoverlapping_count():
    assert S.nonoverlapping_count([0, 1, 2, 5, 6, 10, 10.5], 5) == 3


# --- spot costs -------------------------------------------------------------------------------

def test_fee_is_applied_on_both_legs_and_never_hard_coded():
    assert apply_fee_bps(0.0, 5.0) == pytest.approx(1e4 * ((1 - 5e-4) / (1 + 5e-4) - 1))  # ~ -10 bp
    assert apply_fee_bps(0.0, 0.0) == 0.0 and math.isnan(apply_fee_bps(float("nan"), 5))
    assert round_trip_bps(100.0, 101.0, "buy") == pytest.approx(100.0)
    assert round_trip_bps(101.0, 100.0, "sell") == pytest.approx(100.0)
    assert round_trip_cost_bps(2.5, 0.1, 0.2, 5.0) == pytest.approx(12.8)
    assert slippage_bps([(100.0, 1.0), (101.0, 1.0)], 2.0) == pytest.approx(50.0)
    assert math.isnan(slippage_bps([(100.0, 1.0)], 2.0))
    assert len(scenarios([5, 15, 25], [0.001, 0.01], [0, 100, 250])) == 18
    with pytest.raises(ValueError):
        CostScenario(-1, 0.001)
    for name in ("spot_costs.py",):
        text = (SRC / "analytics" / name).read_text(encoding="utf-8")
        assert "0.0005" not in text and "0.05%" not in text and "5e-4" not in text


def test_config_fee_scenarios_and_conservative_decision_fee():
    cfg = load_config()
    assert cfg.fee_bps_scenarios == (5.0, 15.0, 25.0) and cfg.delays_ms == (0, 100, 250)
    assert cfg.sizes_btc == (0.001, 0.01) and cfg.horizons == (1, 5, 10, 30)
    assert cfg.account_fee_bps is None and cfg.decision_fee_bps == 25.0  # unconfirmed -> most expensive
    assert load_config(account_fee_bps=5.0).decision_fee_bps == 5.0


# --- config / hashes --------------------------------------------------------------------------

def test_config_hashes_and_recorded_overrides(tmp_path):
    cfg = load_config()
    assert len(cfg.config_sha256) == 64 and len(cfg.preregistration_sha256) == 64 and not cfg.overrides
    assert (cfg.train, cfg.validation, cfg.test, cfg.embargo_seconds) == (0.6, 0.2, 0.2, 300.0)
    assert load_config(embargo_seconds=15.0).overrides == {"embargo_seconds": 15.0}
    with pytest.raises(ValueError):
        load_config(not_a_field=1)
    root = tmp_path / "study"
    (root / "configs").mkdir(parents=True)
    (root / "docs").mkdir()
    src = cfg.config_path.read_text(encoding="utf-8")
    (root / "configs" / "c.toml").write_text(src, encoding="utf-8")
    (root / "docs" / "research_v04_preregistration.md").write_text("prereg A", encoding="utf-8")
    h1 = load_config(root / "configs" / "c.toml").preregistration_sha256
    (root / "docs" / "research_v04_preregistration.md").write_text("prereg B", encoding="utf-8")
    assert load_config(root / "configs" / "c.toml").preregistration_sha256 != h1
    (root / "configs" / "c.toml").write_text(src.replace('provenance_required = "real"',
                                                         'provenance_required = "fixture"'), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(root / "configs" / "c.toml")


# --- decisions (Phase 1.1 evidence classes) ---------------------------------------------------

def passing_validation(**kw):
    v = {"N": 4000, "missing_rate": 0.01, "spearman_ic": 0.2, "ic_ci": (0.1, 0.3), "monotonicity": 1.0,
         "gross_edge_bps": 90.0, "net_edge_bps": 30.0, "estimated_cost_bps": 50.0, "net_ci": (10.0, 50.0),
         "gross_ci": (60.0, 120.0), "robust_net_bps": 20.0, "valid_share": 0.99, "nonoverlapping_triggers": 500}
    v.update(kw)
    return v


FIT = TrainFit("obi_5", 5, 1, (0.0, 0.1, 0.2, 0.3), 0.15, {"monotonicity": 1.0})
NAN2 = (float("nan"), float("nan"))


def test_all_criteria_met_gives_paper_candidate_only_with_real_evidence_three_sessions_and_test():
    cfg = load_config()
    eclass, result, reasons = validation_verdict(FIT, passing_validation(), 0.001, cfg)
    assert (eclass, result, reasons) == (POSITIVE_BUT_UNCONFIRMED, "PASS", [])
    assert decide(eclass, result, "PASS", EVIDENCE, 3, cfg) == (PAPER_CANDIDATE, CONFIRMED, CONFIRMED)
    d, c, why = decide(eclass, result, LOCKED, EVIDENCE, 3, cfg)  # test not opened yet
    assert (d, c) == (RESEARCH_MORE, POSITIVE_BUT_UNCONFIRMED) and "test LOCKED" in why
    assert decide(eclass, result, "FAIL", EVIDENCE, 3, cfg)[0] == RESEARCH_MORE


@pytest.mark.parametrize("evidence", [NOT_EVIDENCE, DRY_RUN, INSUFFICIENT])
def test_synthetic_fixture_and_dry_run_never_become_paper_candidates(evidence):
    cfg = load_config()
    d, c, why = decide(POSITIVE_BUT_UNCONFIRMED, "PASS", "PASS", evidence, 99, cfg)
    assert d == RESEARCH_MORE and c == POSITIVE_BUT_UNCONFIRMED and evidence in why


def test_single_six_hour_session_is_capped_at_research_more():
    cfg = load_config()
    assert cfg.min_sessions_for_paper == 3
    d, c, why = decide(POSITIVE_BUT_UNCONFIRMED, "PASS", "PASS", EVIDENCE, 1, cfg)
    assert d == RESEARCH_MORE and "sessions 1 < 3" in why


@pytest.mark.parametrize("change, expected_reason", [
    ({"ic_ci": NAN2}, "IC bootstrap CI not computable"),
    ({"net_ci": NAN2}, "net/gross edge CI not computable"),
    ({"nonoverlapping_triggers": 5}, "non-overlapping triggers 5 < 30"),
    ({"missing_rate": 0.8}, "missing rate 0.8 > 0.5"),
    ({"valid_share": 0.4}, "valid label share 0.4 < 0.9"),
])
def test_insufficient_evidence_is_not_a_reject_even_when_the_point_estimate_is_negative(change, expected_reason):
    cfg = load_config()
    v = passing_validation(net_edge_bps=-50.0, gross_edge_bps=1.0, **change)  # would be negative if sufficient
    eclass, result, reasons = validation_verdict(FIT, v, 0.001, cfg)
    assert eclass == INSUFFICIENT_EVIDENCE and result == "INCONCLUSIVE" and expected_reason in reasons
    assert decide(eclass, result, LOCKED, EVIDENCE, 3, cfg) == (RESEARCH_MORE, INSUFFICIENT_EVIDENCE,
                                                                 INSUFFICIENT_EVIDENCE)


def test_missing_bh_q_or_train_direction_is_insufficient():
    cfg = load_config()
    assert validation_verdict(FIT, passing_validation(), float("nan"), cfg)[0] == INSUFFICIENT_EVIDENCE
    flat = TrainFit("obi_5", 5, 0, (0.0, 0.1, 0.2, 0.3), 0.15, {})
    assert validation_verdict(flat, passing_validation(), 0.001, cfg)[0] == INSUFFICIENT_EVIDENCE


def test_negative_economic_evidence_on_a_sufficient_sample_is_rejected():
    cfg = load_config()
    for v in (passing_validation(net_edge_bps=-3.0, net_ci=(-8.0, 2.0)),  # net <= 0
              passing_validation(gross_edge_bps=10.0, estimated_cost_bps=50.0)):  # gross < cost
        eclass, result, reasons = validation_verdict(FIT, v, 0.001, cfg)
        assert eclass == NEGATIVE_EVIDENCE and result == "FAIL" and reasons
        assert decide(eclass, result, "PASS", EVIDENCE, 3, cfg)[0] == REJECT
    # a significant IC does not rescue a non-tradable edge
    eclass, _, _ = validation_verdict(FIT, passing_validation(net_edge_bps=-1.0), 0.0001, cfg)
    assert eclass == NEGATIVE_EVIDENCE


def test_positive_but_unconfirmed_when_only_some_criteria_are_met():
    cfg = load_config()
    v = passing_validation(robust_net_bps=-1.0, net_ci=(-2.0, 40.0))  # fails 250 ms / fee+2 bp and CI low
    eclass, result, reasons = validation_verdict(FIT, v, 0.2, cfg)  # BH q too high as well
    assert eclass == POSITIVE_BUT_UNCONFIRMED and result == "PARTIAL"
    assert any("BH q" in r for r in reasons) and any("250 ms" in r for r in reasons)
    d, c, why = decide(eclass, result, "PASS", EVIDENCE, 3, cfg)
    assert d == RESEARCH_MORE and c == POSITIVE_BUT_UNCONFIRMED and "partially" in why


def test_evidence_labels():
    assert evidence_label("fixture", 99999, 21600, False) == NOT_EVIDENCE
    assert evidence_label("real", 300, 21600, True) == DRY_RUN
    assert evidence_label("real", 300, 21600, False) == INSUFFICIENT
    assert evidence_label("real", 21600, 21600, False) == EVIDENCE
