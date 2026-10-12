"""v0.6 Monte Carlo harness (research/v06/montecarlo.py): decision table, track labels, Holm across
strategies, aggregation of partial nulls with MC standard errors, reproducibility (serial vs
parallel) and the CLI smoke path. SYNTHETIC only, tiny sizes."""

import json
from dataclasses import replace

import pytest

from moneylab.cli import main
from moneylab.research.v06 import montecarlo as MC
from moneylab.research.v06.synthetic import DGP

TINY_PROC = MC.Procedure(bootstrap=19, draws=9)
TINY_LAYOUT = MC.Layout(warmup=125, confirmatory=500, holdout=200, excluded=10, forward=200, interim=100)


def window(p1=0.5, p_fut=0.5, p2low=0.5, returns=None):
    return {"m": 0.0, "p1": p1, "p_fut": p_fut, "p2": 0.5, "p2low": p2low, "excess": 0.0,
            "returns": returns if returns is not None else [0.0] * 60}


def later(over=None):
    base = {look: {n: window() for n in MC.NAMES} for look in ("holdout", "interim", "final")}
    for (look, name), w in (over or {}).items():
        base[look][name] = w
    return base


STATUS = {"M20": "TRACK_A", "M60": "UNDERPOWERED", "M120": "ECONOMIC_INCONCLUSIVE", "R5": "UNPROFITABLE"}
ST = {n: {"mdd": 0.5} for n in MC.NAMES}


def test_track_a_forward_pass_is_confirmed_and_track_b_is_only_exploratory():
    lw = later({("final", "M20"): window(p1=0.001), ("final", "M60"): window(p1=0.001)})
    a = MC._decide(STATUS, ST, lw, MC.Procedure(), "A", force_forward=False)
    ab = MC._decide(STATUS, ST, lw, MC.Procedure(), "A+B", force_forward=False)
    assert a == {"M20": "CONFIRMED", "M60": "UNDERPOWERED", "M120": "ECONOMIC_INCONCLUSIVE", "R5": "UNPROFITABLE"}
    assert ab["M20"] == "CONFIRMED" and ab["M60"] == MC.EXPLORATORY_PASS
    assert ab["M60"] not in MC.PAPER_CODES


def test_no_candidates_means_holdout_and_forward_stay_closed():
    status = {n: "ECONOMIC_INCONCLUSIVE" for n in MC.NAMES}
    assert MC._decide(status, ST, later(), MC.Procedure(), "A+B", False) == status


def test_holdout_futility_uses_holm_across_the_candidates():
    proc = MC.Procedure(alpha_fut=0.05)
    one = MC._decide({**STATUS, "M60": "ECONOMIC_INCONCLUSIVE"}, ST,
                     later({("holdout", "M20"): window(p_fut=0.03)}), proc, "A", False)
    assert one["M20"] == "HOLDOUT_FAIL"
    two = MC._decide(STATUS, ST, later({("holdout", "M20"): window(p_fut=0.03),
                                          ("holdout", "M60"): window(p_fut=0.04)}), proc, "A+B", False)
    assert two["M20"] != "HOLDOUT_FAIL" and two["M60"] != "HOLDOUT_FAIL"   # Holm: 0.06, 0.06


def test_forward_failure_uses_bonferroni_half_alpha_per_look():
    proc = MC.Procedure(alpha_fut=0.05)
    status = {**STATUS, "M60": "ECONOMIC_INCONCLUSIVE"}
    # R1-A combination doubles min(p_fut, p2low): 0.012 -> 0.024 <= 0.025 fails, 0.013 -> 0.026 does not
    fail = MC._decide(status, ST, later({("interim", "M20"): window(p_fut=0.012)}), proc, "A", False)
    keep = MC._decide(status, ST, later({("interim", "M20"): window(p_fut=0.013)}), proc, "A", False)
    assert fail["M20"] == "FORWARD_FAIL" and keep["M20"] == "FORWARD_INCONCLUSIVE"


def test_risk_limit_comes_before_forward_tests():
    crash = [-0.05] * 40 + [0.0] * 160
    lw = later({("final", "M20"): window(p1=0.0001, returns=crash)})
    st = {**ST, "M20": {"mdd": 0.3}}
    assert MC._decide({**STATUS, "M60": "ECONOMIC_INCONCLUSIVE"}, st, lw, MC.Procedure(), "A", False)["M20"] == "RISK_LIMIT"


def test_selection_stress_forces_every_strategy_forward_as_track_a():
    lw = later({("final", n): window(p1=0.001) for n in MC.NAMES})
    out = MC._decide({n: "ECONOMIC_INCONCLUSIVE" for n in MC.NAMES}, ST, lw, MC.Procedure(), "A", True)
    assert set(out.values()) == {"CONFIRMED"}


def test_aggregate_counts_only_true_nulls_for_fwer_and_reports_mc_se():
    truth = {
        "M20": {"sr_E0": -0.1, "sr_E1": -0.2, "sr_E2": -0.2, "excess_E0": -1e-5},   # null for S
        "M60": {"sr_E0": 0.8, "sr_E1": 0.7, "sr_E2": 0.6, "excess_E0": 1e-4},       # REJECT null true
        "M120": {"sr_E0": 0.5, "sr_E1": 0.4, "sr_E2": 0.35, "excess_E0": 5e-5},
        "R5": {"sr_E0": -0.5, "sr_E1": -0.6, "sr_E2": -0.6, "excess_E0": -2e-4},
    }

    def rec(s_pass_m20, m60_code):
        strategies = {n: {"p1": 0.5, "p2": 0.5, "s_pass": False, "p_rej": 1.0, "rej_path": "futility",
                          "conf_status": "ECONOMIC_INCONCLUSIVE", "roundtrips": 30} for n in MC.NAMES}
        strategies["M60"]["s_pass"] = True                       # true alternative: not counted in S FWER
        strategies["M20"]["s_pass"] = s_pass_m20
        strategies["M60"]["conf_status"] = m60_code
        return {"strategies": strategies, "A": {"M60": m60_code}, "A+B": {"M60": m60_code}}

    records = [rec(False, "TRACK_A")] * 3 + [rec(True, "UNPROFITABLE")]
    m = MC.aggregate(records, truth, MC.Procedure(theta_min=0.3))
    assert m["study"]["s_fwer"]["estimate"] == pytest.approx(0.25)
    assert m["study"]["s_fwer"]["mc_se"] == pytest.approx((0.25 * 0.75 / 4) ** 0.5)
    assert m["study"]["false_reject_confirmatory_fwer"]["estimate"] == pytest.approx(0.25)  # M60 rejected once
    assert m["per_strategy"]["M60"]["s_pass"]["estimate"] == 1.0


def test_replication_is_deterministic_and_codes_are_known():
    a = MC.run_replication(DGP(), MC.Costs(), TINY_PROC, TINY_LAYOUT, False, seed=5)
    b = MC.run_replication(DGP(), MC.Costs(), TINY_PROC, TINY_LAYOUT, False, seed=5)
    assert a == b
    known = MC.REJECT_CODES | MC.PAPER_CODES | {MC.EXPLORATORY_PASS, "INSUFFICIENT_SAMPLE", "ECONOMIC_INCONCLUSIVE",
                                                "UNDERPOWERED", "FORWARD_INCONCLUSIVE", "TRACK_A"}
    for mode in MC.MODES:
        assert set(a[mode].values()) <= known


def test_calibration_reaches_the_target_sharpe():
    cfg_costs = MC.Costs().log_costs()
    dgp = DGP(edge_kind="momentum", edge_lookback=60)
    from moneylab.research.v06.synthetic import draw_noise
    noise = draw_noise(dgp, 365 * 30, seed=3)
    edge, achieved = MC.calibrate_edge(dgp, noise, "M60", "E0", 0.5, cfg_costs)
    assert achieved == pytest.approx(0.5, abs=2e-3)
    edge_min, achieved_min = MC.calibrate_edge(dgp, noise, "M60", "min", 0.3, cfg_costs)
    assert achieved_min == pytest.approx(0.3, abs=2e-3)


def test_run_scenario_serial_and_parallel_give_identical_metrics():
    scn = MC.Scenario("tiny", DGP(edge_kind="momentum", edge_lookback=60), ("M60", "E0", 0.5))
    cfg = MC.RunConfig(reps=4, truth_years=20, procedure=TINY_PROC, layout=TINY_LAYOUT)
    serial = MC.run_scenario(scn, cfg)
    parallel = MC.run_scenario(scn, replace(cfg, workers=2))
    assert serial["metrics"] == parallel["metrics"] and serial["records"] == parallel["records"]
    assert serial["evidence"].startswith("NOT_EVIDENCE")
    # a 20-year calibration path is coarse (discontinuous map): the achieved value is recorded
    assert serial["scenario"]["calibration"]["achieved_sharpe"] == pytest.approx(0.5, abs=0.01)


def test_run_scenario_refuses_a_warmup_shorter_than_the_lookback():
    cfg = MC.RunConfig(reps=1, truth_years=5, procedure=TINY_PROC, layout=replace(TINY_LAYOUT, warmup=120))
    with pytest.raises(ValueError, match="warmup"):
        MC.run_scenario(MC.Scenario("x", DGP()), cfg)


def test_warmup_matches_the_draft_and_the_minimum_lookback():
    import re
    from pathlib import Path

    from moneylab.research.v06.synthetic import min_warmup

    draft = (Path(__file__).resolve().parents[1] / "docs" / "research_v06_preregistration_draft.md").read_text(
        encoding="utf-8")
    (doc_value,) = re.findall(r"^warmup_days = (\d+)", draft, flags=re.M)
    assert int(doc_value) == MC.Layout().warmup == min_warmup() == 122


def test_tier1_scenarios_cover_nulls_boundary_stress_and_theta_grid():
    names = {s.name for s in MC.tier1_scenarios()}
    assert {"null_flat", "null_drift", "boundary", "selection_stress"} <= names
    assert {f"garch_t_M60_{t}" for t in ("-0p3", "+0p0", "+0p3", "+0p5", "+0p7", "+1p0")} <= names


def test_cli_smoke_writes_manifest_and_results(tmp_path):
    out = tmp_path / "sim"
    assert main(["research-v06-sim", "--scenario", "null_flat", "--reps", "2", "--bootstrap", "9",
                 "--draws", "5", "--truth-years", "10", "--out", str(out)]) == 0
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["evidence"].startswith("NOT_EVIDENCE") and "not preregistered" in manifest["baseline_note"]
    result = json.loads((out / "null_flat.json").read_text(encoding="utf-8"))
    assert len(result["records"]) == 2 and "s_fwer" in result["metrics"]["study"]
    assert main(["research-v06-sim", "--list"]) == 0
    assert main(["research-v06-sim", "--scenario", "nope"]) == 1
