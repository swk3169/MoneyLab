"""v0.6 Monte Carlo harness (research/v06/montecarlo.py, MC-V06 schema moneylab.research_v06_sim/2): per-rep records,
post-processed decisions for every draft 18.1 candidate, calendar-month risk, the four repetition axes, the
manifest / summary / per-rep artifact set, reproducibility (serial vs parallel, byte-identical artifacts) and the CLI
smoke path. SYNTHETIC / NOT_EVIDENCE only, tiny sizes."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from moneylab.cli import main
from moneylab.research.v06 import montecarlo as MC
from moneylab.research.v06 import risk_model as RM
from moneylab.research.v06.procedures import segment_returns
from moneylab.research.v06.synthetic import DGP

TINY_PROC = MC.Procedure(bootstrap=19, draws=9)
TINY_LAYOUT = MC.Layout(warmup=125, confirmatory=500, holdout=200, excluded=10)
TINY_CAL = MC.SimulationCalendar(interim_months=2, final_months=(2, 4, 6))
PROC, CAL = MC.Procedure(), MC.SimulationCalendar()
TK = MC.theta_key
CUM_GT = RM.RiskPolicy(RM.MAX_DRAWDOWN_LOG, 1.5, RM.GT, RM.CUMULATIVE_FROM_L)
MONTH_GT = RM.RiskPolicy(RM.MAX_DRAWDOWN_LOG, 1.5, RM.GT, RM.MONTH_ONLY)


def record(proc=PROC, cal=CAL):
    """A neutral per-rep record (nothing rejects, nothing passes) to be edited by a test."""
    th = {TK(t): 0.5 for t in proc.theta_min_options}
    strategies = {}
    for n in MC.NAMES:
        strategies[n] = {
            "p1": 0.5, "p2": 0.5, "p2low": 0.5, "p_maxt": dict(th), "p_fut_E0": dict(th),
            "ea": True, "eb": True, "ec": True,
            "roundtrips": 30, "risk_reference_mdd": 0.3, "s_pass": True, "holdout_p_fut": dict(th),
            "forward": {str(m): {"p1": 0.5, "p2": 0.5, "p2low": 0.5, "p_fut": dict(th)} for m in cal.final_months},
            "risk": {MC.PRIMARY: {p.key: None for p in proc.risk_policies()},
                     MC.SENSITIVITY: {p.key: {str(m): False for m in cal.final_months} for p in proc.risk_policies()}},
            MC.LEGACY: {"first_breach_day": None},
        }
    return {"strategies": strategies}


def policy(**kw):
    return replace(MC.comparison_baseline(PROC, CAL), **kw)


def decide(rec, status, mode="A", force=False, **kw):
    return MC.decide(rec, status, policy(**kw), mode, force, CAL)


STATUS = {"M20": "TRACK_A", "M60": "UNDERPOWERED", "M120": "ECONOMIC_INCONCLUSIVE", "R5": "UNPROFITABLE"}
ONLY_M20 = {**STATUS, "M60": "ECONOMIC_INCONCLUSIVE"}


# --- repetition axes, calendar, scenarios -----------------------------------------------------------------------

def test_the_four_repetition_axes_are_separate_named_normative_values():
    assert (MC.R_OUTER, MC.B_BOOT, MC.K_RAND, MC.TRUTH_YEARS) == (10_000, 9_999, 9_999, 400)
    assert MC.TARGET_MAX_MC_SE == 0.005 and MC.ADAPTIVE_STOPPING == "PROHIBITED"
    assert (PROC.bootstrap, PROC.draws, MC.RunConfig(reps=1).truth_years) == (MC.B_BOOT, MC.K_RAND, MC.TRUTH_YEARS)
    m = MC.manifest(MC.RunConfig(reps=MC.R_OUTER), [])
    assert set(m["repetition_axes"]) == {"R_OUTER", "B_BOOT", "K_RAND", "TRUTH_YEARS"}
    assert m["normative_run"] and all(v["matches_normative"] for v in m["repetition_axes"].values())
    tiny = MC.manifest(MC.RunConfig(reps=3, procedure=replace(TINY_PROC, draws=7), truth_years=5), [])
    assert {k: v["run"] for k, v in tiny["repetition_axes"].items()} == {"R_OUTER": 3, "B_BOOT": 19, "K_RAND": 7,
                                                                         "TRUTH_YEARS": 5}
    assert not tiny["normative_run"] and not any(v["matches_normative"] for v in tiny["repetition_axes"].values())


def test_full_run_mc_se_bound_meets_the_target_at_r_outer():
    assert MC._rate(MC.R_OUTER // 2, MC.R_OUTER)["mc_se"] <= MC.TARGET_MAX_MC_SE   # worst case p = 0.5
    assert MC._rate(MC.R_OUTER // 2 - 1, MC.R_OUTER - 1)["mc_se"] > MC.TARGET_MAX_MC_SE


def test_rate_with_no_cases_is_none_not_nan():
    assert MC._rate(0, 0) == {"estimate": None, "mc_se": None, "n": 0}
    assert MC._rate(1, 4)["mc_se"] == pytest.approx((0.25 * 0.75 / 4) ** 0.5)


def test_primary_calendar_starts_on_a_month_start_and_counts_calendar_days():
    assert CAL.forward_start == "2026-12-01" and CAL.final_months == (12, 24, 36) and CAL.interim_months == 12
    assert [CAL.forward_days(m) for m in CAL.final_months] == [365, 731, 1096] and CAL.risk_days == 1096
    d = CAL.to_dict()
    assert d["status"] == "NOT_A_BT4_DECISION" and d["primary"] == MC.PRIMARY and d["sensitivity"] == MC.SENSITIVITY
    with pytest.raises(ValueError, match="first day"):
        MC.SimulationCalendar(forward_start="2026-11-11")
    with pytest.raises(ValueError, match="mid-month"):
        MC.SimulationCalendar(sensitivity_forward_start="2027-01-01")
    with pytest.raises(ValueError):
        MC.SimulationCalendar(interim_months=13)
    b = MC.Layout().bounds(CAL)
    assert b["forward_12m"][0] == b["forward_36m"][0] == b["risk"][0] == b["holdout"][1] + MC.Layout().excluded
    assert b["forward_24m"][1] - b["forward_24m"][0] == 731


def test_warmup_matches_the_draft_and_the_minimum_lookback():
    import re

    from moneylab.research.v06.synthetic import min_warmup

    draft = (Path(__file__).resolve().parents[1] / "docs" / "research_v06_preregistration_draft.md").read_text(
        encoding="utf-8")
    (doc_value,) = re.findall(r"^warmup_days = (\d+)", draft, flags=re.M)
    assert int(doc_value) == MC.Layout().warmup == min_warmup() == 122


def test_tier1_scenarios_cover_nulls_boundary_stress_and_theta_grid():
    names = {s.name for s in MC.tier1_scenarios()}
    assert {"null_flat", "null_drift", "boundary", "selection_stress"} <= names
    assert {f"garch_t_M60_{t}" for t in ("-0p3", "+0p0", "+0p3", "+0p5", "+0p7", "+1p0")} <= names


def test_mc_v06_scenarios_are_tier1_with_one_boundary_per_d1_candidate():
    tier1 = {s.name: s for s in MC.tier1_scenarios()}
    mc = MC.mc_v06_scenarios()
    names = [s.name for s in mc]
    assert len(names) == len(set(names)) == len(tier1) - 1 + len(PROC.theta_min_options)
    assert {n for n in names if n.startswith("boundary")} == {"boundary_theta_0p3", "boundary_theta_0p5",
                                                              "boundary_theta_0p7"}
    for s in mc:
        if s.name.startswith("boundary"):
            assert s.calibrate[:2] == ("M60", "min") and s.dgp == tier1["boundary"].dgp
        else:
            assert s == tier1[s.name]
    assert {s.calibrate[2] for s in mc if s.name.startswith("boundary")} == set(PROC.theta_min_options)


def test_calibration_reaches_the_target_sharpe():
    cfg_costs = MC.Costs().log_costs()
    dgp = DGP(edge_kind="momentum", edge_lookback=60)
    from moneylab.research.v06.synthetic import draw_noise
    noise = draw_noise(dgp, 365 * 30, seed=3)
    edge, achieved = MC.calibrate_edge(dgp, noise, "M60", "E0", 0.5, cfg_costs)
    assert achieved == pytest.approx(0.5, abs=2e-3)
    edge_min, achieved_min = MC.calibrate_edge(dgp, noise, "M60", "min", 0.3, cfg_costs)
    assert achieved_min == pytest.approx(0.3, abs=2e-3)


# --- decision grid (post-processing) ------------------------------------------------------------------------------

def test_decision_grid_is_every_candidate_combination_once():
    grid = MC.decision_grid(PROC, CAL)
    keys = [p.key for p in grid]
    assert len(keys) == len(set(keys)) == 3 * 2 * 2 * 2 * 3 * (1 + 3 + 3) * 4
    assert {p.interim for p in grid if p.final_months == 12} == {MC.INTERIM_NONE}   # T_F 12: no interim (D6)
    assert {p.interim for p in grid if p.final_months == 24} == set(MC.INTERIM_OPTIONS)
    assert {p.risk.key for p in grid} == {r.key for r in PROC.risk_policies()} and len(PROC.risk_policies()) == 4
    assert MC.comparison_baseline(PROC, CAL).key in keys
    assert "LEGACY" not in "".join(keys) and "30" not in "".join(keys)


def test_an_interim_needs_a_final_analysis_after_it():
    with pytest.raises(ValueError, match="interim"):
        decide(record(), ONLY_M20, final_months=12, interim=MC.INTERIM_HALF)


def test_track_a_forward_pass_is_confirmed_and_track_b_is_only_exploratory():
    r = record()
    for n in ("M20", "M60"):
        r["strategies"][n]["forward"]["24"]["p1"] = 0.001
    assert decide(r, STATUS, "A") == {"M20": "CONFIRMED", "M60": "UNDERPOWERED", "M120": "ECONOMIC_INCONCLUSIVE",
                                      "R5": "UNPROFITABLE"}
    ab = decide(r, STATUS, "A+B")
    assert ab["M20"] == "CONFIRMED" and ab["M60"] == MC.EXPLORATORY_PASS and ab["M60"] not in MC.PAPER_CODES


def test_no_candidates_means_holdout_and_forward_stay_closed():
    status = {n: "ECONOMIC_INCONCLUSIVE" for n in MC.NAMES}
    assert decide(record(), status, "A+B") == status


def test_d3_holm_on_holdout_futility():
    r = record()
    r["strategies"]["M20"]["holdout_p_fut"][TK(0.3)] = 0.03
    r["strategies"]["M60"]["holdout_p_fut"][TK(0.3)] = 0.04
    holm = decide(r, STATUS, "A+B", futility_holm=True)
    raw = decide(r, STATUS, "A+B", futility_holm=False)
    assert holm["M20"] != "HOLDOUT_FAIL" and holm["M60"] != "HOLDOUT_FAIL"   # Holm: 0.06, 0.06
    assert raw["M20"] == raw["M60"] == "HOLDOUT_FAIL"


def test_d1_theta_selects_the_futility_p_values_of_that_candidate():
    r = record()
    r["strategies"]["M20"]["holdout_p_fut"][TK(0.7)] = 0.001
    assert decide(r, ONLY_M20, theta_min=0.3)["M20"] == "FORWARD_INCONCLUSIVE"
    assert decide(r, ONLY_M20, theta_min=0.7)["M20"] == "HOLDOUT_FAIL"


def test_d2_alpha_fut_threshold():
    r = record()
    r["strategies"]["M20"]["holdout_p_fut"][TK(0.3)] = 0.08
    assert decide(r, ONLY_M20, alpha_fut=0.05)["M20"] != "HOLDOUT_FAIL"
    assert decide(r, ONLY_M20, alpha_fut=0.10)["M20"] == "HOLDOUT_FAIL"


@pytest.mark.parametrize("p_fut, interim, code", [
    (0.012, MC.INTERIM_HALF, "FORWARD_FAIL"),            # R1-A doubles: 0.024 <= 0.025
    (0.013, MC.INTERIM_HALF, "FORWARD_INCONCLUSIVE"),    # 0.026 > 0.025
    (0.013, MC.INTERIM_FULL, "FORWARD_FAIL"),            # 0.026 <= 0.05
    (0.001, MC.INTERIM_NONE, "FORWARD_INCONCLUSIVE"),    # no interim look
])
def test_d7_interim_alpha_split(p_fut, interim, code):
    r = record()
    r["strategies"]["M20"]["forward"]["12"]["p_fut"][TK(0.3)] = p_fut
    assert decide(r, ONLY_M20, interim=interim)["M20"] == code


def test_d7_alpha_split_also_applies_at_the_final_analysis():
    r = record()
    r["strategies"]["M20"]["forward"]["24"]["p_fut"][TK(0.3)] = 0.02     # combined 0.04
    assert decide(r, ONLY_M20, interim=MC.INTERIM_HALF)["M20"] == "FORWARD_INCONCLUSIVE"
    assert decide(r, ONLY_M20, interim=MC.INTERIM_FULL)["M20"] == "FORWARD_FAIL"
    assert decide(r, ONLY_M20, interim=MC.INTERIM_NONE)["M20"] == "FORWARD_FAIL"


def test_d6_final_analysis_reads_the_window_of_t_f():
    r = record()
    r["strategies"]["M20"]["forward"]["12"]["p1"] = 0.001
    r["strategies"]["M20"]["forward"]["36"]["p_fut"][TK(0.3)] = 0.001
    assert decide(r, ONLY_M20, final_months=12, interim=MC.INTERIM_NONE)["M20"] == "CONFIRMED"
    assert decide(r, ONLY_M20, final_months=24)["M20"] == "FORWARD_INCONCLUSIVE"
    assert decide(r, ONLY_M20, final_months=36)["M20"] == "FORWARD_FAIL"


def test_d4_forward_s_f_with_or_without_h2():
    r = record()
    r["strategies"]["M20"]["forward"]["24"]["p1"] = 0.001
    assert decide(r, ONLY_M20, forward_h2=False)["M20"] == "CONFIRMED"
    assert decide(r, ONLY_M20, forward_h2=True)["M20"] == "FORWARD_INCONCLUSIVE"   # max(p1, p2) = 0.5
    r["strategies"]["M20"]["forward"]["24"]["p2"] = 0.002
    assert decide(r, ONLY_M20, forward_h2=True)["M20"] == "CONFIRMED"


def test_d5_alpha_f_and_the_efficacy_family_is_every_strategy_that_went_forward():
    r = record()
    r["strategies"]["M20"]["forward"]["24"]["p1"] = 0.03
    r["strategies"]["M60"]["forward"]["12"]["p_fut"][TK(0.3)] = 0.001     # M60 fails at the interim
    status = {**STATUS, "M60": "TRACK_A"}
    out = decide(r, status, alpha_f=0.05)
    assert out["M60"] == "FORWARD_FAIL" and out["M20"] == "FORWARD_INCONCLUSIVE"   # Holm over {M20, M60}: 0.06
    assert decide(r, status, alpha_f=0.10)["M20"] == "CONFIRMED"


def test_risk_limit_is_checked_monthly_in_time_order():
    r = record()
    s = r["strategies"]["M20"]
    s["forward"]["24"]["p1"] = 0.001
    s["risk"][MC.PRIMARY][CUM_GT.key] = 15                                   # first violation in month 16
    assert decide(r, ONLY_M20, final_months=12, interim=MC.INTERIM_NONE)["M20"] != "RISK_LIMIT"   # forward over
    assert decide(r, ONLY_M20, final_months=24)["M20"] == "RISK_LIMIT"     # before the final analysis
    s["forward"]["12"]["p_fut"][TK(0.3)] = 0.001                             # interim failure at month 12
    assert decide(r, ONLY_M20, final_months=24)["M20"] == "FORWARD_FAIL"   # happened before the violation
    s["risk"][MC.PRIMARY][CUM_GT.key] = 11                                   # violation in month 12
    assert decide(r, ONLY_M20, final_months=24)["M20"] == "RISK_LIMIT"     # row 12 before row 14
    assert decide(r, ONLY_M20, final_months=24, risk=MONTH_GT)["M20"] == "FORWARD_FAIL"   # other policy: no violation


def test_selection_stress_forces_every_strategy_forward_as_track_a():
    r = record()
    for n in MC.NAMES:
        r["strategies"][n]["forward"]["24"]["p1"] = 0.001
    out = decide(r, {n: "ECONOMIC_INCONCLUSIVE" for n in MC.NAMES}, "A", force=True)
    assert set(out.values()) == {"CONFIRMED"}


def test_confirmatory_status_by_theta_alpha_and_holm():
    r = record()
    s = r["strategies"]
    s["M20"]["ea"] = False
    s["M20"]["p_maxt"][TK(0.7)] = 0.02                  # R1-A: 0.04
    assert MC.confirmatory_status(r, 0.3, 0.05, False, PROC)["M20"] == "ECONOMIC_INCONCLUSIVE"
    assert MC.confirmatory_status(r, 0.7, 0.05, False, PROC)["M20"] == "UNPROFITABLE"
    assert MC.confirmatory_status(r, 0.7, 0.05, True, PROC)["M20"] == "ECONOMIC_INCONCLUSIVE"   # Holm 0.16
    s["M60"]["eb"] = False
    s["M60"]["p2low"] = 0.001                            # R1-A: 0.002
    assert MC.confirmatory_status(r, 0.3, 0.05, True, PROC)["M60"] == "NOT_ROBUST"
    s["R5"]["roundtrips"] = 19
    s["M120"]["s_pass"] = False
    st = MC.confirmatory_status(r, 0.3, 0.05, True, PROC)
    assert st["R5"] == "INSUFFICIENT_SAMPLE" and st["M120"] == "UNDERPOWERED"


# --- summary --------------------------------------------------------------------------------------------------

TRUTH = {
    "M20": {"sr_E0": -0.1, "sr_E1": -0.2, "sr_E2": -0.2, "excess_E0": -1e-5},   # null for S, unprofitable
    "M60": {"sr_E0": 0.8, "sr_E1": 0.7, "sr_E2": 0.6, "excess_E0": 1e-4},       # REJECT null true for every theta
    "M120": {"sr_E0": 0.5, "sr_E1": 0.4, "sr_E2": 0.35, "excess_E0": 5e-5},     # REJECT null true for theta 0.3
    "R5": {"sr_E0": -0.5, "sr_E1": -0.6, "sr_E2": -0.6, "excess_E0": -2e-4},
}


def test_summary_counts_only_true_nulls_for_fwer_and_reports_mc_se():
    a = record()
    b = record()
    b["strategies"]["M20"]["s_pass"] = True
    a["strategies"]["M20"]["s_pass"] = False
    b["strategies"]["M60"]["ea"] = False
    b["strategies"]["M60"]["p_maxt"] = {k: 0.001 for k in b["strategies"]["M60"]["p_maxt"]}   # REJECTed in b
    for r in (a, b):
        r["strategies"]["R5"]["s_pass"] = False
    s = MC.summarize([a, a, a, b], TRUTH, PROC, CAL, False)
    common = s["combination_independent"]
    assert common["study"]["s_fwer"]["estimate"] == pytest.approx(0.25)   # M20 null: passes S once
    assert common["study"]["s_fwer"]["mc_se"] == pytest.approx((0.25 * 0.75 / 4) ** 0.5)
    base = s["decision_grid"][s["comparison_baseline_key"]]
    assert base["study"]["false_reject_confirmatory_fwer"]["estimate"] == pytest.approx(0.25)
    assert base["per_strategy"]["M60"]["A"]["reject"]["estimate"] == pytest.approx(0.25)
    assert base["per_strategy"]["M60"]["A"]["code_counts"]["UNPROFITABLE"] == 1
    m = MC.baseline_metrics(s)
    assert m["study"]["A"]["study_paper"]["estimate"] == 0.0 and "s_fwer" in m["study"]
    assert s["mc_se_check"]["target_max_mc_se"] == 0.005 and s["mc_se_check"]["rates"] > 0
    assert s["mc_se_check"]["worst_case_bound"] == pytest.approx(0.25)


def test_summary_keeps_legacy_and_sensitivity_apart_from_normative_keys():
    r = record()
    r["strategies"]["M20"][MC.LEGACY]["first_breach_day"] = 30
    r["strategies"]["M20"]["risk"][MC.SENSITIVITY][CUM_GT.key]["24"] = True
    r["strategies"]["M20"]["risk"][MC.PRIMARY][CUM_GT.key] = 20
    s = MC.summarize([r, record()], TRUTH, PROC, CAL, False)
    assert s[MC.LEGACY]["per_strategy"]["M20"] == {"12": MC._rate(1, 2), "24": MC._rate(1, 2), "36": MC._rate(1, 2)}
    assert MC.LEGACY not in json.dumps({k: v for k, v in s.items() if k != MC.LEGACY})
    rs = s["risk_semantics"]
    assert rs[MC.PRIMARY]["M20"][CUM_GT.key] == {"12": MC._rate(0, 2), "24": MC._rate(1, 2), "36": MC._rate(1, 2)}
    assert rs[MC.SENSITIVITY]["M20"][CUM_GT.key]["24"] == MC._rate(1, 2)


# --- test-level (single-test, unconditional) results ----------------------------------------------------------

AK = MC.alpha_key


def _level_records():
    """Four records; M20 is INSUFFICIENT_SAMPLE in all of them (never reaches holdout/forward), which must not
    change its unconditional test-level rates."""
    recs = [record() for _ in range(4)]
    for r in recs:
        r["strategies"]["M20"]["roundtrips"] = 5
    s0, s1 = recs[0]["strategies"]["M20"], recs[1]["strategies"]["M20"]
    s0["p_fut_E0"][TK(0.5)] = 0.03          # E0 futility rejects at 0.05 and 0.10 for theta 0.5
    s0["p_maxt"][TK(0.5)] = 0.9             # ... while the joint max-T over E0/E1/E2 does not
    s1["p_fut_E0"][TK(0.5)] = 0.08          # only at 0.10
    s0["holdout_p_fut"][TK(0.3)] = 0.04
    f = s0["forward"]["24"]
    f["p1"], f["p2"] = 0.01, 0.15            # H1 passes at 0.05; H2 only at 0.20; max only at 0.20
    s1["forward"]["24"]["p2"] = 0.04         # H2 alone at 0.05 while H1 = 0.5
    s0["forward"]["12"]["p_fut"][TK(0.3)] = 0.02   # interim futility rejects at every look alpha (0.025 .. 0.10)
    s1["forward"]["36"]["p_fut"][TK(0.7)] = 0.03   # final 36: 0.05 and 0.10, not 0.025
    return recs


def test_level_confirmatory_e0_is_its_own_quantity_not_max_t_or_a_decision():
    recs = _level_records()
    s = MC.summarize(recs, TRUTH, PROC, CAL, False)
    e0 = s["test_level"]["per_strategy"]["M20"]["confirmatory_e0_futility"]
    assert set(e0) == {TK(t) for t in PROC.theta_min_options} and set(e0[TK(0.5)]) == {AK(0.05), AK(0.1)}
    assert e0[TK(0.5)][AK(0.05)] == MC._rate(1, 4) and e0[TK(0.5)][AK(0.1)] == MC._rate(2, 4)
    assert e0[TK(0.3)][AK(0.1)] == MC._rate(0, 4)
    base = s["decision_grid"][s["comparison_baseline_key"]]["per_strategy"]["M20"]["A"]
    assert base["code_counts"] == {"INSUFFICIENT_SAMPLE": 4} and base["reject"] == MC._rate(0, 4)   # decision differs


def test_level_holdout_and_forward_futility_are_unconditional():
    s = MC.summarize(_level_records(), TRUTH, PROC, CAL, False)["test_level"]["per_strategy"]["M20"]
    assert s["holdout_futility"][TK(0.3)] == {AK(0.05): MC._rate(1, 4), AK(0.1): MC._rate(1, 4)}
    ff = s["forward_futility"]
    assert set(ff["interim"]) == {"12"} and set(ff["final"]) == {"12", "24", "36"}
    looks = set(map(AK, MC.forward_futility_alphas(PROC)))
    assert set(ff["interim"]["12"][TK(0.3)]) == {AK(0.025), AK(0.05), AK(0.1)} == looks
    assert ff["interim"]["12"][TK(0.3)][AK(0.025)] == MC._rate(1, 4)
    assert ff["final"]["36"][TK(0.7)] == {AK(0.025): MC._rate(0, 4), AK(0.05): MC._rate(1, 4), AK(0.1): MC._rate(1, 4)}
    assert ff["final"]["24"][TK(0.7)][AK(0.1)] == MC._rate(0, 4)


def test_level_forward_h1_h2_and_max_are_separate():
    fwd = MC.summarize(_level_records(), TRUTH, PROC, CAL, False)["test_level"]["per_strategy"]["M20"]["forward_pass"]
    assert set(fwd) == {"12", "24", "36"} and set(fwd["24"]) == {AK(a) for a in PROC.alpha_f_options}
    at05, at20 = fwd["24"][AK(0.05)], fwd["24"][AK(0.2)]
    assert (at05["h1"], at05["h2"], at05["h1_h2_max"]) == (MC._rate(1, 4), MC._rate(1, 4), MC._rate(0, 4))
    assert (at20["h1"], at20["h2"], at20["h1_h2_max"]) == (MC._rate(1, 4), MC._rate(2, 4), MC._rate(1, 4))
    assert fwd["12"][AK(0.2)]["h2"] == MC._rate(0, 4)
    # D4 is still a grid dimension next to the separate H1 / H2 rates
    assert {p.forward_h2 for p in MC.decision_grid(PROC, CAL)} == {True, False}


def test_level_rates_carry_the_binomial_mc_se_and_enter_the_mc_se_check():
    s = MC.summarize(_level_records(), TRUTH, PROC, CAL, False)
    worst, count = MC._max_mc_se(s["test_level"])
    # per strategy: e0 and holdout (theta x alpha_fut), forward pass (T_F x alpha_F x 3), futility (4 looks x theta x 3)
    assert count == 4 * (3 * 2 + 3 * 2 + 3 * 3 * 3 + (1 + 3) * 3 * 3)
    assert worst == pytest.approx((0.5 * 0.5 / 4) ** 0.5)          # the 2-of-4 rates
    assert s["mc_se_check"]["max_mc_se"] >= worst
    full = MC.test_level([record()["strategies"]] * MC.R_OUTER, PROC, CAL)["per_strategy"]["R5"]
    assert full["holdout_futility"][TK(0.5)][AK(0.05)] == {"estimate": 0.0, "mc_se": 0.0, "n": MC.R_OUTER}


def test_level_thresholds_are_post_processing_of_the_same_records():
    recs = _level_records()
    before = json.dumps(recs, sort_keys=True)
    a = MC.test_level([r["strategies"] for r in recs], PROC, CAL)
    b = MC.test_level([r["strategies"] for r in recs], replace(PROC, alpha_fut_options=(0.07,), alpha_f_options=(0.2,)),
                      CAL)
    assert json.dumps(recs, sort_keys=True) == before                              # records untouched
    assert a["per_strategy"]["M20"]["confirmatory_e0_futility"][TK(0.5)][AK(0.05)] == MC._rate(1, 4)
    assert b["per_strategy"]["M20"]["confirmatory_e0_futility"][TK(0.5)] == {AK(0.07): MC._rate(1, 4)}   # 0.03 only
    a24 = a["per_strategy"]["M20"]["forward_pass"]["24"]
    assert b["per_strategy"]["M20"]["forward_pass"]["24"] == {AK(0.2): a24[AK(0.2)]}


def test_record_e0_futility_is_the_single_scenario_test_on_the_shared_resamples():
    from moneylab.research.stats import derived_seed
    from moneylab.research.v06.procedures import bootstrap_means, futility_delta, futility_pvalue
    from moneylab.research.v06.synthetic import SCENARIOS, make_path, segment_market_positions, strategy_signals

    rec = tiny_record(seed=5)
    path = make_path(DGP(), TINY_LAYOUT.total_days(TINY_CAL), 5)
    sigs = strategy_signals(path)
    lc = MC.Costs().log_costs()
    c0, c1 = TINY_LAYOUT.bounds(TINY_CAL)["confirmatory"]
    flat = []
    for n in MC.NAMES:
        for scn in SCENARIOS:
            market, pos = segment_market_positions(path, sigs[n], scn, c0, c1)
            flat.append(segment_returns(market, pos, lc[scn]))
    boots = bootstrap_means(flat, mean_block=TINY_PROC.mean_block, resamples=TINY_PROC.bootstrap,
                            seed=derived_seed(5, "conf", "boot"))
    for i, n in enumerate(MC.NAMES):
        r0 = flat[3 * i]
        m0 = sum(r0) / len(r0)
        for t in TINY_PROC.theta_min_options:
            expected = futility_pvalue(m0, boots[3 * i], futility_delta(t, r0))
            assert rec["strategies"][n]["p_fut_E0"][TK(t)] == expected
    assert any(rec["strategies"][n]["p_fut_E0"] != rec["strategies"][n]["p_maxt"] for n in MC.NAMES)


# --- per-rep record -------------------------------------------------------------------------------------------

def tiny_record(seed=5, dgp=DGP()):
    return MC.run_replication(dgp, MC.Costs(), TINY_PROC, TINY_LAYOUT, False, seed, calendar=TINY_CAL)


def test_replication_record_is_deterministic_serializable_and_holds_no_decision():
    a, b = tiny_record(), tiny_record()
    assert a == b and MC.canonical_bytes(a) == MC.canonical_bytes(b)
    assert a != tiny_record(seed=6)
    assert json.loads(MC.canonical_bytes(a)) == a
    text = json.dumps(a)
    assert not any(code in text for code in ("CONFIRMED", "RISK_LIMIT", "HOLDOUT_FAIL", "UNPROFITABLE"))
    s = a["strategies"]["M20"]
    assert set(s["forward"]) == {"2", "4", "6"} and set(s["p_maxt"]) == {TK(t) for t in TINY_PROC.theta_min_options}
    assert set(s["risk"]) == {MC.PRIMARY, MC.SENSITIVITY} and set(s[MC.LEGACY]) == {"first_breach_day"}


def test_v1_call_shape_is_accepted_and_changes_nothing_in_the_record():
    """tests/test_v06_randomness.py (protected) still calls run_replication(dgp, costs, proc, layout, force_forward,
    seed) with Layout(forward=, interim=). /2 decides force_forward in post-processing and takes the forward period
    from SimulationCalendar, so neither changes the per-rep record."""
    a = tiny_record()
    b = MC.run_replication(DGP(), MC.Costs(), TINY_PROC, replace(TINY_LAYOUT, forward=150, interim=75), True, 5,
                           calendar=TINY_CAL)
    assert a == b
    assert MC.run_replication(DGP(), MC.Costs(), TINY_PROC, TINY_LAYOUT, False, 5) == \
        MC.run_replication(DGP(), MC.Costs(), TINY_PROC, TINY_LAYOUT, False, 5, calendar=MC.SimulationCalendar())


def test_replication_risk_outcomes_come_from_the_research_risk_model():
    rec = tiny_record(seed=18)   # seed with a violation inside the 6-month tiny forward path
    from moneylab.research.v06.synthetic import make_path, segment_market_positions, strategy_signals
    path = make_path(DGP(), TINY_LAYOUT.total_days(TINY_CAL), 18)
    sigs = strategy_signals(path)
    k0, k1 = TINY_LAYOUT.bounds(TINY_CAL)["risk"]
    lc = MC.Costs().log_costs()["E0"]
    L = RM.parse_date(TINY_CAL.forward_start)
    for name, s in rec["strategies"].items():
        r = MC._mark_to_market(*segment_market_positions(path, sigs[name], "E0", k0, k1), lc)
        for p in TINY_PROC.risk_policies():
            assert s["risk"][MC.PRIMARY][p.key] == RM.first_violation(r, L, s["risk_reference_mdd"], p)
    assert rec["strategies"]["R5"]["risk"][MC.PRIMARY][CUM_GT.key] == 3


def test_mark_to_market_drops_only_the_final_virtual_exit():
    cost = -0.003
    market, pos = [0.01, -0.02, 0.03, 0.01], [0, 1, 1, 1]
    seg = segment_returns(market, pos, cost)
    mtm = MC._mark_to_market(market, pos, cost)
    assert mtm[:3] == seg[:3] and mtm[3] == pytest.approx(seg[3] - cost)
    assert MC._mark_to_market(market, [0, 1, 1, 0], cost) == segment_returns(market, [0, 1, 1, 0], cost)


def test_legacy_check_is_the_old_30_day_cumulative_rule():
    r = [0.0] * 89 + [-0.5]
    assert MC._legacy_first_breach(r, 0.1, PROC) == 90
    assert MC._legacy_first_breach([0.0] * 29 + [-0.5], 0.1, PROC) == 30
    assert MC._legacy_first_breach([-0.5] + [0.0] * 28, 0.1, PROC) is None   # fewer than 30 days: never checked


# --- runner and artifacts -------------------------------------------------------------------------------------

SCN = MC.Scenario("tiny", DGP(edge_kind="momentum", edge_lookback=60), ("M60", "E0", 0.5))


def tiny_cfg(**kw):
    return MC.RunConfig(reps=3, truth_years=20, procedure=TINY_PROC, layout=TINY_LAYOUT, calendar=TINY_CAL, **kw)


def test_run_scenario_serial_and_parallel_give_identical_records_and_summary():
    serial = MC.run_scenario(SCN, tiny_cfg())
    parallel = MC.run_scenario(SCN, tiny_cfg(workers=2))
    assert serial["records"] == parallel["records"] and serial["summary"] == parallel["summary"]
    assert [r["rep"] for r in serial["records"]] == [0, 1, 2]
    assert serial["schema"] == MC.SCHEMA == "moneylab.research_v06_sim/2"
    assert serial["evidence"] == "SYNTHETIC / NOT_EVIDENCE"
    assert serial["metrics"]["study"]["A"]["study_paper"]["n"] == 3
    # a 20-year calibration path is coarse (discontinuous map): the achieved value is recorded
    assert serial["scenario"]["calibration"]["achieved_sharpe"] == pytest.approx(0.5, abs=0.01)


def test_run_scenario_refuses_a_warmup_shorter_than_the_lookback():
    cfg = MC.RunConfig(reps=1, truth_years=5, procedure=TINY_PROC, layout=replace(TINY_LAYOUT, warmup=120))
    with pytest.raises(ValueError, match="warmup"):
        MC.run_scenario(MC.Scenario("x", DGP()), cfg)


def _files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_write_study_artifact_set_provenance_and_integrity(tmp_path):
    out = MC.write_study(tmp_path / "run", tiny_cfg(), [SCN, MC.Scenario("flat", DGP())])
    files = _files(out)
    assert set(files) == {"manifest.json", "execution.json", "SHA256SUMS", "scenarios/tiny/summary.json",
                          "scenarios/tiny/records.jsonl", "scenarios/flat/summary.json", "scenarios/flat/records.jsonl"}
    sums = dict(reversed(line.split("  ", 1)) for line in files["SHA256SUMS"].decode().splitlines())
    assert set(sums) == set(files) - {"SHA256SUMS"}
    assert all(hashlib.sha256(files[k]).hexdigest() == v for k, v in sums.items())

    m = json.loads(files["manifest.json"])
    assert m["schema"] == "moneylab.research_v06_sim/2" and m["evidence"] == "SYNTHETIC / NOT_EVIDENCE"
    assert m["artifact_layout"].startswith("SEPARATED")
    for key in ("repetition_axes", "seeds", "procedure", "layout", "simulation_calendar", "scenarios", "source_sha256",
                "python", "moneylab_version", "reproduction", "decision_grid", "bt3e_equivalence", "costs",
                "target_max_mc_se", "adaptive_stopping"):
        assert key in m, key
    assert m["seeds"]["seed"] == 20261012 and "derived_seed" in m["seeds"]["derived_seed_rule"]
    assert m["simulation_calendar"]["status"] == "NOT_A_BT4_DECISION"
    assert m["bt3e_equivalence"]["bt4_q18"] == "UNRESOLVED"
    assert [s["name"] for s in m["scenarios"]] == ["tiny", "flat"]
    assert m["scenarios"][0]["calibrate"] == ["M60", "E0", 0.5]
    src = m["source_sha256"]
    assert set(src) == {f"moneylab/{p}" for p in MC._SOURCE_FILES}
    mc_file = Path(MC.__file__)
    assert src["moneylab/research/v06/montecarlo.py"]["sha256"] == hashlib.sha256(mc_file.read_bytes()).hexdigest()
    assert src["moneylab/research/v06/montecarlo.py"]["sha256_lf"] == \
        hashlib.sha256(mc_file.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

    ex = json.loads(files["execution.json"])
    assert ex["evidence"] == "SYNTHETIC / NOT_EVIDENCE" and ex["started_utc"] <= ex["finished_utc"]
    assert set(ex["git"]) == {"commit", "ref", "method", "worktree_state"}

    lines = files["scenarios/tiny/records.jsonl"].decode().splitlines()
    assert len(lines) == 3 and [json.loads(x)["rep"] for x in lines] == [0, 1, 2]
    assert all(MC.canonical_bytes(json.loads(x)) == (x + "\n").encode() for x in lines)
    summ = json.loads(files["scenarios/tiny/summary.json"])
    assert summ["kind"] == "scenario_summary" and summ["evidence"] == "SYNTHETIC / NOT_EVIDENCE"
    assert summ["records"] == {"file": "records.jsonl", "count": 3,
                               "sha256": hashlib.sha256(files["scenarios/tiny/records.jsonl"]).hexdigest()}
    assert "strategies" not in json.dumps(summ)                    # no per-rep record inside the summary
    assert summ["scenario"]["resolved_dgp"]["edge_annual"] != 0.0
    assert summ["test_level"]["per_strategy"]["M60"]["forward_pass"]["4"][AK(0.05)]["h2"]["n"] == 3
    with pytest.raises(FileExistsError):
        MC.write_study(out, tiny_cfg(), [SCN])


def test_write_study_is_byte_identical_for_the_same_seed_serial_or_parallel(tmp_path):
    a = _files(MC.write_study(tmp_path / "a", tiny_cfg(), [SCN]))
    b = _files(MC.write_study(tmp_path / "b", tiny_cfg(workers=2), [SCN]))
    for f in a:
        if f not in ("execution.json", "SHA256SUMS"):
            assert a[f] == b[f], f
    def sums(d):
        return [x for x in d["SHA256SUMS"].decode().splitlines() if not x.endswith("execution.json")]

    assert sums(a) == sums(b)
    c = _files(MC.write_study(tmp_path / "c", tiny_cfg(seed=1), [SCN]))
    assert c["scenarios/tiny/records.jsonl"] != a["scenarios/tiny/records.jsonl"]


def test_git_identity_reads_a_worktree_gitdir_without_subprocess(tmp_path):
    common = tmp_path / "repo" / ".git"
    wt_git = common / "worktrees" / "wt"
    wt_git.mkdir(parents=True)
    (wt_git / "HEAD").write_text("ref: refs/heads/feature/x\n", encoding="utf-8")
    (wt_git / "commondir").write_text("../..\n", encoding="utf-8")
    (common / "packed-refs").write_text("# pack-refs\n" + "1" * 40 + " refs/heads/feature/x\n", encoding="utf-8")
    wt = tmp_path / "wt"
    (wt / "src").mkdir(parents=True)
    (wt / ".git").write_text(f"gitdir: {wt_git}\n", encoding="utf-8")
    g = MC.git_identity(wt / "src" / "file.py")
    assert g["commit"] == "1" * 40 and g["ref"] == "refs/heads/feature/x"
    (common / "refs" / "heads" / "feature").mkdir(parents=True)
    (common / "refs" / "heads" / "feature" / "x").write_text("2" * 40 + "\n", encoding="utf-8")
    assert MC.git_identity(wt / "src" / "file.py")["commit"] == "2" * 40
    assert MC.git_identity(tmp_path / "nowhere" / "f.py")["commit"] is None   # outside any repository


def test_cli_smoke_writes_manifest_and_results(tmp_path):
    out = tmp_path / "sim"
    assert main(["research-v06-sim", "--scenario", "null_flat", "--reps", "2", "--bootstrap", "9",
                 "--draws", "5", "--truth-years", "10", "--out", str(out)]) == 0
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "moneylab.research_v06_sim/2" and manifest["evidence"] == "SYNTHETIC / NOT_EVIDENCE"
    assert "not preregistered" in manifest["baseline_note"] and manifest["artifact_layout"].startswith("COMBINED")
    assert not manifest["normative_run"]
    result = json.loads((out / "null_flat.json").read_text(encoding="utf-8"))
    assert len(result["records"]) == 2 and "s_fwer" in result["metrics"]["study"]
    assert "records" not in result["summary"] and result["summary"]["replications"] == 2
    assert main(["research-v06-sim", "--list"]) == 0
    assert main(["research-v06-sim", "--scenario", "nope"]) == 1
    assert main(["research-v06-sim", "--scenario", "null_flat", "--reps", "0", "--out", str(tmp_path / "x")]) == 1
    assert not (tmp_path / "x").exists()


def test_record_helper_matches_the_real_record_shape():
    real = tiny_record()
    fake = record(TINY_PROC, TINY_CAL)

    def keys(x):
        return {k: keys(v) for k, v in x.items()} if isinstance(x, dict) else None

    assert keys(fake) == keys(real)
