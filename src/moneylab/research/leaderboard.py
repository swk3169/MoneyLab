"""Feature x horizon evaluation and the pre-registered decision rules (preregistration, sections 9-10).

Everything that is fitted (signal direction, quantile edges, median) is fitted on TRAIN only and
then applied unchanged to validation (research-stats) and test (research-final).

Trigger: d = sign(Spearman IC on train). A row whose feature falls in the top train quintile
trades in direction +d, the bottom quintile in direction -d (direction +1 = buy round trip,
-1 = sell-inventory round trip). For trigger rows:
  gross = direction * future_mid_move_bps
  net   = executable label of that side with the fee applied (analytics.spot_costs)  <- decision
  estimated cost = gross - net  (spread + depth slippage + delay move + fees)

Evidence classes (Phase 1.1, preregistration section 10):
  INSUFFICIENT_EVIDENCE    the sample cannot support a judgement (CI / BH q / net or gross CI not
                           computable, too few non-overlapping triggers, too much missing data,
                           too few valid labels, no train direction) -> RESEARCH_MORE, never REJECT
  NEGATIVE_EVIDENCE        sufficient sample AND (validation net edge <= 0 OR gross < estimated cost)
                           -> REJECT
  POSITIVE_BUT_UNCONFIRMED sufficient sample, net > 0 and gross >= cost; some or all pre-registered
                           criteria met, but the test split is locked / failed, or sessions or
                           evidence are not enough -> RESEARCH_MORE
  CONFIRMED                every criterion, test PASS, provenance real, >= min sessions -> PAPER_CANDIDATE
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from moneylab.analytics.metrics import net_edge_bps
from moneylab.analytics.spot_costs import apply_fee_bps
from moneylab.research.config import StudyConfig
from moneylab.research.io import num
from moneylab.research.labels import exec_label_name, mid_label_names
from moneylab.research.manifest import EVIDENCE
from moneylab.research.stats import (
    NAN,
    benjamini_hochberg,
    bootstrap_corr_ci,
    bootstrap_ratio_ci,
    derived_seed,
    directional_accuracy,
    hac_correlation_test,
    mean,
    nonoverlapping_count,
    pearson,
    percentile,
    quantile_analysis,
    quantile_edges,
    spearman,
    std,
)

REJECT, RESEARCH_MORE, PAPER_CANDIDATE = "REJECT", "RESEARCH_MORE", "PAPER_CANDIDATE"
DECISIONS = (REJECT, RESEARCH_MORE, PAPER_CANDIDATE)
LOCKED = "LOCKED"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
NEGATIVE_EVIDENCE = "NEGATIVE_EVIDENCE"
POSITIVE_BUT_UNCONFIRMED = "POSITIVE_BUT_UNCONFIRMED"
CONFIRMED = "CONFIRMED"
EVIDENCE_CLASSES = (INSUFFICIENT_EVIDENCE, NEGATIVE_EVIDENCE, POSITIVE_BUT_UNCONFIRMED, CONFIRMED)
COLUMNS = ("feature", "horizon", "N", "missing_rate", "Spearman_IC", "IC_CI_low", "IC_CI_high", "BH_q",
           "top_bottom_bps", "directional_accuracy", "gross_edge_bps", "estimated_cost_bps", "net_edge_bps",
           "fee_sensitivity", "delay_sensitivity", "validation_result", "test_result", "decision",
           "evidence_class", "decision_reason")


@dataclass(frozen=True)
class TrainFit:
    feature: str
    horizon: int
    direction: int  # +1 / -1 / 0 (no usable signal)
    edges: tuple[float, ...]
    median: float
    stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"feature": self.feature, "horizon": self.horizon, "direction": self.direction,
                "edges": list(self.edges), "median": self.median, "train": self.stats}


def _ok(row: dict[str, Any]) -> bool:
    return not row.get("reasons")


def _sample(rows: Sequence[dict[str, Any]], feature: str, label: str) -> tuple[list[dict], list[float], list[float], float]:
    """Clean rows with a valid label; returns (rows with feature, x, y, missing_rate)."""
    base = [r for r in rows if _ok(r) and num(r.get(label)) == num(r.get(label))]
    used = [r for r in base if num(r.get(feature)) == num(r.get(feature))]
    missing = 1 - len(used) / len(base) if base else NAN
    return used, [num(r[feature]) for r in used], [num(r[label]) for r in used], missing


def _summary(x: list[float], y: list[float], missing: float) -> dict[str, Any]:
    return {"N": len(x), "missing_rate": missing, "feature_mean": mean(x), "feature_std": std(x),
            "label_mean": mean(y), "label_std": std(y), "pearson": pearson(x, y), "spearman_ic": spearman(x, y)}


def fit_train(train_rows: Sequence[dict[str, Any]], feature: str, horizon: int, cfg: StudyConfig) -> TrainFit:
    _, move = mid_label_names(horizon)
    _, x, y, missing = _sample(train_rows, feature, move)
    s = _summary(x, y, missing)
    ic = s["spearman_ic"]
    direction = 0 if not ic == ic or ic == 0 else (1 if ic > 0 else -1)
    edges = tuple(quantile_edges(x, cfg.quantiles)) if len(x) >= cfg.quantiles else ()
    if edges:
        qa = quantile_analysis(x, y, edges)
        s.update(quantile_counts=list(qa.counts), quantile_means=list(qa.means), top_bottom_bps=qa.top_bottom,
                 monotonicity=qa.monotonicity)
    return TrainFit(feature, horizon, direction, edges, percentile(x, 0.5), s)


def _block_rows(cfg: StudyConfig, horizon: int) -> float:
    return max(cfg.block_seconds_min, cfg.block_horizon_multiple * horizon) / cfg.grid_seconds


def evaluate(rows: Sequence[dict[str, Any]], fit: TrainFit, cfg: StudyConfig, segment: str) -> dict[str, Any]:
    """Statistics and trading edges of one feature x horizon on one segment, using `fit` only."""
    h, f = fit.horizon, fit.feature
    _, move = mid_label_names(h)
    used, x, y, missing = _sample(rows, f, move)
    m = _summary(x, y, missing)
    seg_rows = list(rows)
    dec_label = exec_label_name("buy", h, cfg.decision_size_btc, cfg.decision_delay_ms)
    m["valid_share"] = (sum(1 for r in seg_rows if _ok(r) and num(r.get(dec_label)) == num(r.get(dec_label)))
                        / len(seg_rows)) if seg_rows else NAN
    m["effective_N"] = len(x) / h if x else 0
    seed = derived_seed(cfg.bootstrap_seed, segment, f, str(h))
    block = _block_rows(cfg, h)
    m["ic_ci"] = bootstrap_corr_ci(x, y, mean_block=block, resamples=cfg.bootstrap_resamples, seed=seed,
                                   level=cfg.ci_level, rank=True)
    lag = int(round((h + cfg.hac_extra_lag_seconds) / cfg.grid_seconds))
    m["hac_t"], m["hac_p"] = hac_correlation_test(x, y, lag)
    if fit.edges:
        qa = quantile_analysis(x, y, fit.edges)
        m.update(quantile_counts=list(qa.counts), quantile_means=list(qa.means), top_bottom_bps=qa.top_bottom,
                 monotonicity=qa.monotonicity)
    else:
        m.update(quantile_counts=[], quantile_means=[], top_bottom_bps=NAN, monotonicity=NAN)
    m["directional_accuracy"], m["directional_rows"] = directional_accuracy(x, y, fit.median, fit.direction)
    m.update(_edges(used, fit, cfg, segment, seed))
    return m


def _trigger(v: float, fit: TrainFit) -> int:
    if fit.direction == 0 or not fit.edges or v != v:
        return 0
    if v >= fit.edges[-1]:
        return fit.direction
    if v < fit.edges[0]:
        return -fit.direction
    return 0


def _net(row: dict[str, Any], d: int, h: int, size: float, delay: int, fee: float) -> float:
    side = "buy" if d > 0 else "sell"
    return apply_fee_bps(num(row.get(exec_label_name(side, h, size, delay))), fee)


def _edges(used: list[dict[str, Any]], fit: TrainFit, cfg: StudyConfig, segment: str, seed: int) -> dict[str, Any]:
    h = fit.horizon
    _, move = mid_label_names(h)
    fee, q, dl = cfg.decision_fee_bps, cfg.decision_size_btc, cfg.decision_delay_ms
    trig = [_trigger(num(r[fit.feature]), fit) for r in used]
    gross, net, num_s, gross_s, den_s, times = [], [], [], [], [], []
    for r, d in zip(used, trig):
        n_ = _net(r, d, h, q, dl, fee) if d else NAN
        ok = d != 0 and n_ == n_
        num_s.append(n_ if ok else 0.0)
        gross_s.append(d * num(r[move]) if ok else 0.0)
        den_s.append(1.0 if ok else 0.0)
        if ok:
            gross.append(d * num(r[move]))
            net.append(n_)
            times.append(float(r["t"]))
    g, n_mean = mean(gross), mean(net)
    out: dict[str, Any] = {
        "triggers": len(net), "nonoverlapping_triggers": nonoverlapping_count(times, h),
        "gross_edge_bps": g, "net_edge_bps": n_mean,
        "estimated_cost_bps": g - n_mean if net else NAN,
        "net_ci": bootstrap_ratio_ci(num_s, den_s, mean_block=_block_rows(cfg, h), resamples=cfg.bootstrap_resamples,
                                     seed=seed + 1, level=cfg.ci_level),
        "gross_ci": bootstrap_ratio_ci(gross_s, den_s, mean_block=_block_rows(cfg, h),
                                       resamples=cfg.bootstrap_resamples, seed=seed + 2, level=cfg.ci_level),
    }

    def scenario(fee_bps: float, size: float, delay: int) -> float:
        vals = [_net(r, d, h, size, delay, fee_bps) for r, d in zip(used, trig) if d]
        v = net_edge_bps(vals)
        return NAN if v is None else v

    out["fee_sensitivity"] = {f"{fb:g}bp": scenario(fb, q, dl) for fb in cfg.fee_bps_scenarios}
    out["delay_sensitivity"] = {f"{d}ms": scenario(fee, q, d) for d in cfg.delays_ms}
    out["size_sensitivity"] = {f"{s:g}BTC": scenario(fee, s, dl) for s in cfg.sizes_btc}
    out["robust_net_bps"] = scenario(fee + cfg.robust_fee_buffer_bps, q, cfg.robust_delay_ms)
    return out


# --- decisions --------------------------------------------------------------------------------

def _pos(v: float) -> bool:
    return v == v and v > 0


def _nan(v: float) -> bool:
    return v != v


def insufficiency(fit: TrainFit, v: dict[str, Any], bh_q: float, cfg: StudyConfig) -> list[str]:
    """Why this sample cannot support a judgement (empty list = sufficient)."""
    out = []
    if fit.direction == 0:
        out.append("no train direction (train IC zero or not computable)")
    if any(_nan(x) for x in v["ic_ci"]):
        out.append("IC bootstrap CI not computable")
    if _nan(bh_q):
        out.append("BH q-value not computable")
    if any(_nan(x) for x in v["net_ci"]) or any(_nan(x) for x in v.get("gross_ci", (NAN, NAN))):
        out.append("net/gross edge CI not computable")
    if v["nonoverlapping_triggers"] < cfg.min_evidence_triggers:
        out.append(f"non-overlapping triggers {v['nonoverlapping_triggers']} < {cfg.min_evidence_triggers}")
    if _nan(v["missing_rate"]) or v["missing_rate"] > cfg.max_missing_rate:
        out.append(f"missing rate {v['missing_rate']} > {cfg.max_missing_rate}")
    if _nan(v["valid_share"]) or v["valid_share"] < cfg.min_valid_share:
        out.append(f"valid label share {v['valid_share']} < {cfg.min_valid_share}")
    return out


def unmet_criteria(fit: TrainFit, v: dict[str, Any], bh_q: float, cfg: StudyConfig) -> list[str]:
    """Pre-registered PAPER_CANDIDATE criteria 2-6 (section 10) that the validation result misses."""
    d = fit.direction
    lo, hi = v["ic_ci"]
    ic = v["spearman_ic"]
    out = []
    if not (d != 0 and ic == ic and (ic > 0) == (d > 0)):
        out.append("validation IC sign differs from train")
    if not ((d > 0 and _pos(lo)) or (d < 0 and hi == hi and hi < 0)):
        out.append("IC CI includes 0 (or wrong sign)")
    if not (bh_q == bh_q and bh_q < cfg.fdr_alpha):
        out.append(f"BH q >= {cfg.fdr_alpha}")
    if not ((fit.stats.get("monotonicity", NAN) * d) >= cfg.min_quantile_monotonicity
            and (v.get("monotonicity", NAN) * d) >= cfg.min_quantile_monotonicity):
        out.append(f"quintile monotonicity < {cfg.min_quantile_monotonicity}")
    g, c = v["gross_edge_bps"], v["estimated_cost_bps"]
    if not _pos(v["net_ci"][0]):
        out.append("net edge CI lower bound <= 0")
    if not (g == g and c == c and g >= cfg.min_gross_to_cost * max(c, 0.0)):
        out.append(f"gross < {cfg.min_gross_to_cost} x cost")
    if not _pos(v["robust_net_bps"]):
        out.append(f"net <= 0 at {cfg.robust_delay_ms} ms / fee + {cfg.robust_fee_buffer_bps} bp")
    if v["nonoverlapping_triggers"] < cfg.min_nonoverlapping_triggers:
        out.append(f"non-overlapping triggers < {cfg.min_nonoverlapping_triggers}")
    if _nan(v["valid_share"]) or v["valid_share"] < cfg.min_valid_share:
        out.append(f"valid label share < {cfg.min_valid_share}")
    return out


def validation_verdict(fit: TrainFit, v: dict[str, Any], bh_q: float, cfg: StudyConfig) -> tuple[str, str, list[str]]:
    """(evidence_class, validation_result, reasons). Insufficient evidence is never negative evidence."""
    missing = insufficiency(fit, v, bh_q, cfg)
    if missing:
        return INSUFFICIENT_EVIDENCE, "INCONCLUSIVE", missing
    g, n_, c = v["gross_edge_bps"], v["net_edge_bps"], v["estimated_cost_bps"]
    negative = []
    if n_ <= 0:
        negative.append(f"validation net edge {n_:.2f} bp <= 0")
    if g < c:
        negative.append(f"gross {g:.2f} bp < estimated cost {c:.2f} bp")
    if negative:
        return NEGATIVE_EVIDENCE, "FAIL", negative
    unmet = unmet_criteria(fit, v, bh_q, cfg)
    return POSITIVE_BUT_UNCONFIRMED, ("PASS" if not unmet else "PARTIAL"), unmet


def evaluate_test_verdict(fit: TrainFit, t: dict[str, Any]) -> str:
    ic, n_ = t["spearman_ic"], t["net_edge_bps"]
    if ic != ic or n_ != n_:
        return "INCONCLUSIVE"
    return "PASS" if fit.direction != 0 and (ic > 0) == (fit.direction > 0) and n_ > 0 else "FAIL"


def decide(evidence_class: str, validation_result: str, test_result: str, evidence: str, sessions: int,
           cfg: StudyConfig) -> tuple[str, str, str]:
    """(decision, evidence_class, decision_reason). PAPER_CANDIDATE only for real evidence from at least
    `min_sessions_for_paper` sessions with every criterion met and the test split passed."""
    if evidence_class == NEGATIVE_EVIDENCE:
        return REJECT, NEGATIVE_EVIDENCE, NEGATIVE_EVIDENCE
    if evidence_class == INSUFFICIENT_EVIDENCE:
        return RESEARCH_MORE, INSUFFICIENT_EVIDENCE, INSUFFICIENT_EVIDENCE
    blockers = []
    if validation_result != "PASS":
        blockers.append("validation criteria partially met")
    if test_result != "PASS":
        blockers.append(f"test {test_result}")
    if evidence != EVIDENCE:
        blockers.append(f"evidence {evidence}")
    if sessions < cfg.min_sessions_for_paper:
        blockers.append(f"sessions {sessions} < {cfg.min_sessions_for_paper}")
    if blockers:
        return RESEARCH_MORE, POSITIVE_BUT_UNCONFIRMED, f"{POSITIVE_BUT_UNCONFIRMED}: " + "; ".join(blockers)
    return PAPER_CANDIDATE, CONFIRMED, CONFIRMED


def build_leaderboard(train_rows: Sequence[dict[str, Any]], val_rows: Sequence[dict[str, Any]], cfg: StudyConfig,
                      evidence: str, sessions: int) -> tuple[list[dict[str, Any]], list[TrainFit], list[dict]]:
    """Validation leaderboard (test LOCKED). Returns (rows, fits, details)."""
    fits, vals = [], []
    for f in cfg.signals:
        for h in cfg.horizons:
            fit = fit_train(train_rows, f, h, cfg)
            fits.append(fit)
            vals.append(evaluate(val_rows, fit, cfg, "validation"))
    qs = benjamini_hochberg([v["hac_p"] for v in vals])
    board, details = [], []
    for fit, v, q in zip(fits, vals, qs):
        eclass, result, reasons = validation_verdict(fit, v, q, cfg)
        decision, eclass2, why = decide(eclass, result, LOCKED, evidence, sessions, cfg)
        board.append(_row(fit, v, q, result, LOCKED, decision, evidence, eclass2, why))
        details.append({"fit": fit.to_dict(), "validation": v, "bh_q": q, "validation_evidence_class": eclass,
                        "validation_reasons": reasons})
    return board, fits, details


def _row(fit: TrainFit, v: dict[str, Any], q: float, vres: str, tres: str, decision: str,
         evidence: str, evidence_class: str, reason: str) -> dict[str, Any]:
    return {
        "feature": fit.feature, "horizon": fit.horizon, "N": v["N"], "missing_rate": v["missing_rate"],
        "Spearman_IC": v["spearman_ic"], "IC_CI_low": v["ic_ci"][0], "IC_CI_high": v["ic_ci"][1], "BH_q": q,
        "top_bottom_bps": v["top_bottom_bps"], "directional_accuracy": v["directional_accuracy"],
        "gross_edge_bps": v["gross_edge_bps"], "estimated_cost_bps": v["estimated_cost_bps"],
        "net_edge_bps": v["net_edge_bps"], "fee_sensitivity": v["fee_sensitivity"],
        "delay_sensitivity": v["delay_sensitivity"], "validation_result": vres, "test_result": tres,
        "decision": decision, "evidence_class": evidence_class, "decision_reason": reason, "evidence": evidence,
    }


def finalize_with_test(board: list[dict[str, Any]], fits: list[TrainFit], details: list[dict[str, Any]],
                       test_rows: Sequence[dict[str, Any]], cfg: StudyConfig, evidence: str,
                       sessions: int) -> list[dict[str, Any]]:
    """Apply the frozen train fits to the test rows once; nothing is re-fitted or re-thresholded."""
    out = []
    for row, fit, det in zip(board, fits, details):
        t = evaluate(test_rows, fit, cfg, "test")
        tres = evaluate_test_verdict(fit, t)
        decision, eclass, why = decide(det["validation_evidence_class"], row["validation_result"], tres, evidence,
                                       sessions, cfg)
        out.append({**row, "test_result": tres, "decision": decision, "evidence_class": eclass,
                    "decision_reason": why, "test_net_edge_bps": t["net_edge_bps"],
                    "test_Spearman_IC": t["spearman_ic"], "test_N": t["N"]})
    return out


def fit_from_dict(d: dict[str, Any]) -> TrainFit:
    return TrainFit(d["feature"], int(d["horizon"]), int(d["direction"]), tuple(d["edges"]), float(d["median"])
                    if d["median"] is not None else math.nan, d.get("train") or {})
