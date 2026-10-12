"""Monte Carlo operating characteristics of the v0.6 DRAFT decision rules on SYNTHETIC paths.

One replication = one synthetic path covering warmup, confirmatory, historical holdout, excluded
days and forward, generated without breaks (dependence across boundaries is kept). Every rule of
the draft that the decision table needs is applied: 8.1 segment accounting, H1, B1/H2, IUT + Holm
(S), E-a/E-b/E-c, R1-A REJECT combination (candidate), holdout futility, forward risk limit,
interim and final forward failure checks (Bonferroni alpha_fut / 2 each), forward H1 efficacy.

Two track modes are decided on the same path (common random numbers):
  "A"    confirmatory track only (E = PASS and S = PASS go forward)
  "A+B"  plus the exploratory track (E = PASS, S = FAIL go forward); a forward pass from the
         exploratory track is FORWARD_EXPLORATORY_PASS, never CONFIRMED / PAPER_CANDIDATE

Not simulated: data quality (Q = VALID assumed), fee confirmation (decision fee only), E_op
(operating costs assumed covered), missing data and revisions.
"""

from __future__ import annotations

import math
import platform
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from moneylab import __version__
from moneylab.research.stats import derived_seed
from moneylab.research.v06.procedures import (
    STRATEGIES,
    annual_sharpe,
    b1_means,
    bootstrap_means,
    futility_delta,
    futility_pvalue,
    h1_pvalue,
    holm,
    iut_holm,
    max_drawdown,
    maxt_futility_pvalue,
    mean,
    r1a_reject_pvalue,
    randomization_pvalues,
    roundtrips,
    segment_returns,
    trade_cost_log,
)
from moneylab.research.v06.synthetic import (
    DGP,
    SCENARIOS,
    Noise,
    Path,
    add_drift,
    draw_noise,
    make_path,
    min_warmup,
    segment_market_positions,
    strategy_signals,
    true_metrics,
)

NAMES = tuple(STRATEGIES)
REJECT_CODES = frozenset({"UNPROFITABLE", "NOT_ROBUST", "HOLDOUT_FAIL", "FORWARD_FAIL", "RISK_LIMIT"})
CONFIRMATORY_REJECT = frozenset({"UNPROFITABLE", "NOT_ROBUST"})
LATER_FUTILITY_REJECT = frozenset({"HOLDOUT_FAIL", "FORWARD_FAIL"})
PAPER_CODES = frozenset({"CONFIRMED"})
EXPLORATORY_PASS = "FORWARD_EXPLORATORY_PASS"
MODES = ("A", "A+B")


@dataclass(frozen=True)
class Costs:
    fee_bps: float = 25.0                                  # decision fee until the account fee is confirmed
    slip_bps: tuple[float, float, float] = (5.0, 10.0, 10.0)  # E0, E1, E2 one-way spread + slippage
    impact_bps: float = 3.2                                # iota at 10M KRW (assumption, draft 7)

    def log_costs(self) -> dict[str, float]:
        return {s: trade_cost_log(self.fee_bps, k, self.impact_bps) for s, k in zip(SCENARIOS, self.slip_bps)}


@dataclass(frozen=True)
class Procedure:
    """Simulation comparison baseline (draft 18.1 D1-D9), NOT preregistered values."""
    theta_min: float = 0.3          # D1
    alpha_fut: float = 0.05         # D2
    alpha_s: float = 0.05           # confirmatory S (fixed in the draft)
    alpha_f: float = 0.05           # D5
    mean_block: float = 20.0
    bootstrap: int = 1999
    draws: int = 999                # B1 placements per test
    min_roundtrips: int = 20
    min_positive_year_share: float = 0.60
    mdd_ratio: float = 1.5
    risk_check_days: int = 30


@dataclass(frozen=True)
class Layout:
    warmup: int = 122               # draft 8: M120 lookback 120 + 2-day execution lag (see min_warmup)
    confirmatory: int = 2227        # ~6.1 years (listing date unverified)
    holdout: int = 914              # 2024-04-01 .. 2026-10-02 (D9)
    excluded: int = 40              # exposed days up to the freeze date
    forward: int = 730              # D6: 24 months
    interim: int = 365

    @property
    def total_days(self) -> int:
        return self.warmup + self.confirmatory + self.holdout + self.excluded + self.forward + 3

    def bounds(self) -> dict[str, tuple[int, int]]:
        c0 = self.warmup
        c1 = c0 + self.confirmatory
        h1 = c1 + self.holdout
        f0 = h1 + self.excluded
        return {"confirmatory": (c0, c1), "holdout": (c1, h1), "interim": (f0, f0 + self.interim),
                "final": (f0, f0 + self.forward)}


@dataclass(frozen=True)
class Scenario:
    name: str
    dgp: DGP
    calibrate: tuple[str, str, float] | None = None   # (strategy, "E0" | "min", target annual Sharpe)
    force_forward: bool = False                        # selection stress: every strategy goes forward
    description: str = ""


def tier1_scenarios(theta_min: float = 0.3) -> list[Scenario]:
    garch = DGP(edge_kind="momentum", edge_lookback=60)
    normal = DGP(garch_alpha=0.0, garch_beta=0.0, t_df=None, edge_kind="momentum", edge_lookback=60)
    out = [
        Scenario("null_flat", DGP(), description="GARCH-t random walk, no drift: H1 and H2 nulls true"),
        Scenario("null_drift", DGP(drift_annual=0.35), description="drift only: H2 null true, H1 may be false"),
        Scenario("boundary", garch, ("M60", "min", theta_min),
                 description="M60 min(E0,E1,E2) Sharpe = theta_min: REJECT null at its boundary"),
        Scenario("selection_stress", garch, ("M60", "E0", 0.0), force_forward=True,
                 description="M60 E0 Sharpe 0, every strategy forced forward"),
    ]
    for theta in (-0.3, 0.0, 0.3, 0.5, 0.7, 1.0):
        tag = f"{theta:+.1f}".replace(".", "p")
        out.append(Scenario(f"garch_t_M60_{tag}", garch, ("M60", "E0", theta), description="GARCH(1,1)-t4"))
        out.append(Scenario(f"normal_M60_{tag}", normal, ("M60", "E0", theta),
                            description="iid normal (comparison with the normal approximation)"))
    return out


# --- calibration and truth ----------------------------------------------------------------------

def _target_sharpe(path: Path, strategy: str, target: str, costs: dict[str, float]) -> float:
    sig = strategy_signals(path)[strategy]
    g0, g1 = min_warmup() + 1, path.days - 1
    vals = []
    for scn in (SCENARIOS if target == "min" else ("E0",)):
        market, pos = segment_market_positions(path, sig, scn, g0, g1)
        vals.append(annual_sharpe(segment_returns(market, pos, costs[scn])))
    return min(vals)


def calibrate_edge(dgp: DGP, noise: Noise, strategy: str, target: str, theta: float,
                   costs: dict[str, float], tol: float = 1e-3, max_iter: int = 40) -> tuple[float, float]:
    """Edge (annual log drift by signal sign) giving the target Sharpe on this noise. Bisection on
    common random numbers. The map is not continuous (signals flip discretely as the edge changes
    the path), so the closest edge seen is returned with the Sharpe it actually achieves; the
    scenario truth is computed on that same path. Returns (edge, achieved Sharpe)."""
    def f(x: float) -> float:
        return _target_sharpe(Path(*add_drift(replace(dgp, edge_annual=x), noise)), strategy, target, costs) - theta
    lo, hi = -2.0, 2.0
    flo, fhi = f(lo), f(hi)
    while flo > 0 and lo > -16:
        lo *= 2
        flo = f(lo)
    while fhi < 0 and hi < 16:
        hi *= 2
        fhi = f(hi)
    if flo > 0 or fhi < 0:
        raise ValueError(f"cannot reach Sharpe {theta} for {strategy}")
    best = (lo, flo) if abs(flo) < abs(fhi) else (hi, fhi)
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        fmid = f(mid)
        if abs(fmid) < abs(best[1]):
            best = (mid, fmid)
        if abs(fmid) < tol:
            break
        if fmid < 0:
            lo = mid
        else:
            hi = mid
    return best[0], best[1] + theta


def resolve(scenario: Scenario, costs: Costs, truth_years: int, seed: int) -> tuple[DGP, dict, dict]:
    """Final DGP (edge calibrated if requested) and per-strategy truth on a long path."""
    lc = costs.log_costs()
    noise = draw_noise(scenario.dgp, truth_years * 365, derived_seed(seed, scenario.name, "truth"))
    dgp, calib = scenario.dgp, {}
    if scenario.calibrate:
        strategy, target, theta = scenario.calibrate
        edge, achieved = calibrate_edge(dgp, noise, strategy, target, theta, lc)
        dgp = replace(dgp, edge_annual=edge)
        calib = {"strategy": strategy, "target": target, "theta": theta, "edge_annual": edge,
                 "achieved_sharpe": achieved, "truth_years": truth_years,
                 "truth_se_sharpe": 1 / math.sqrt(truth_years)}
    truth = true_metrics(Path(*add_drift(dgp, noise)), lc, seed=derived_seed(seed, scenario.name, "truth-b1"))
    return dgp, truth, calib


# --- one replication -----------------------------------------------------------------------------

def _yearly_positive_share(r: Sequence[float], min_days: int = 180) -> float:
    chunks = [r[i:i + 365] for i in range(0, len(r), 365)]
    chunks = [ch for ch in chunks if len(ch) >= min_days]
    return sum(1 for ch in chunks if sum(ch) > 0) / len(chunks) if chunks else 0.0


def _window_stats(path: Path, sigs: dict, lc: dict, proc: Procedure, g0: int, g1: int, seed: int,
                  tag: str) -> dict[str, dict[str, float]]:
    """E0 statistics of every strategy on one later window (holdout, interim, final)."""
    data = {}
    for name in NAMES:
        market, pos = segment_market_positions(path, sigs[name], "E0", g0, g1)
        data[name] = (market, pos, segment_returns(market, pos, lc["E0"]))
    boots = bootstrap_means([data[n][2] for n in NAMES], mean_block=proc.mean_block,
                            resamples=proc.bootstrap, seed=derived_seed(seed, tag, "boot"))
    out = {}
    for i, name in enumerate(NAMES):
        market, pos, r = data[name]
        m = mean(r)
        draws = b1_means(market, pos, lc["E0"], proc.draws, derived_seed(seed, tag, "b1", name))
        p2, p2low = randomization_pvalues(m, draws)
        out[name] = {"m": m, "p1": h1_pvalue(m, boots[i]),
                     "p_fut": futility_pvalue(m, boots[i], futility_delta(proc.theta_min, r)),
                     "p2": p2, "p2low": p2low, "excess": m - mean(draws), "returns": r}
    return out


def run_replication(dgp: DGP, costs: Costs, proc: Procedure, layout: Layout, force_forward: bool,
                    seed: int) -> dict[str, Any]:
    path = make_path(dgp, layout.total_days, seed)
    sigs = strategy_signals(path)
    lc = costs.log_costs()
    b = layout.bounds()
    c0, c1 = b["confirmatory"]

    conf: dict[str, dict[str, tuple]] = {}
    flat = []
    for name in NAMES:
        conf[name] = {}
        for scn in SCENARIOS:
            market, pos = segment_market_positions(path, sigs[name], scn, c0, c1)
            r = segment_returns(market, pos, lc[scn])
            conf[name][scn] = (market, pos, r)
            flat.append(r)
    boots = bootstrap_means(flat, mean_block=proc.mean_block, resamples=proc.bootstrap,
                            seed=derived_seed(seed, "conf", "boot"))

    st: dict[str, dict[str, Any]] = {}
    for i, name in enumerate(NAMES):
        market0, pos0, r0 = conf[name]["E0"]
        ms = [mean(conf[name][s][2]) for s in SCENARIOS]
        bs = boots[3 * i:3 * i + 3]
        deltas = [futility_delta(proc.theta_min, conf[name][s][2]) for s in SCENARIOS]
        draws = b1_means(market0, pos0, lc["E0"], proc.draws, derived_seed(seed, "conf", "b1", name))
        p2, p2low = randomization_pvalues(ms[0], draws)
        p_maxt = maxt_futility_pvalue(ms, bs, deltas)
        st[name] = {
            "m": ms, "p1": h1_pvalue(ms[0], bs[0]), "p2": p2, "p2low": p2low, "p_maxt": p_maxt,
            "p_rej": r1a_reject_pvalue(p_maxt, p2low), "rej_path": "B1" if p2low < p_maxt else "futility",
            "b1_mean": mean(draws), "roundtrips": roundtrips(pos0),
            "year_share": _yearly_positive_share(r0), "mdd": max_drawdown(r0),
        }
    s_adj = iut_holm([st[n]["p1"] for n in NAMES], [st[n]["p2"] for n in NAMES])
    rej_adj = holm([st[n]["p_rej"] for n in NAMES])

    status: dict[str, str] = {}
    for i, name in enumerate(NAMES):
        s = st[name]
        s["s_pass"] = s_adj[i] <= proc.alpha_s
        ea = s["m"][0] > 0 and s["m"][0] > s["b1_mean"]
        eb = s["m"][1] > 0 and s["m"][2] > 0
        ec = s["year_share"] >= proc.min_positive_year_share
        if s["roundtrips"] < proc.min_roundtrips:
            status[name] = "INSUFFICIENT_SAMPLE"
        elif (not ea or not eb) and rej_adj[i] <= proc.alpha_fut:
            status[name] = "UNPROFITABLE" if not ea else "NOT_ROBUST"
        elif not (ea and eb and ec):
            status[name] = "ECONOMIC_INCONCLUSIVE"
        else:
            status[name] = "TRACK_A" if s["s_pass"] else "UNDERPOWERED"

    later = {}
    hb, ib, fb = b["holdout"], b["interim"], b["final"]
    later["holdout"] = _window_stats(path, sigs, lc, proc, *hb, seed, "holdout")
    later["interim"] = _window_stats(path, sigs, lc, proc, *ib, seed, "interim")
    later["final"] = _window_stats(path, sigs, lc, proc, *fb, seed, "final")

    out: dict[str, Any] = {"strategies": {}}
    for name in NAMES:
        out["strategies"][name] = {
            "p1": st[name]["p1"], "p2": st[name]["p2"], "s_pass": st[name]["s_pass"],
            "p_rej": st[name]["p_rej"], "rej_path": st[name]["rej_path"],
            "conf_status": status[name], "roundtrips": st[name]["roundtrips"],
        }
    for mode in MODES:
        out[mode] = _decide(status, st, later, proc, mode, force_forward)
    return out


def _decide(status: dict[str, str], st: dict, later: dict, proc: Procedure, mode: str,
            force_forward: bool) -> dict[str, str]:
    codes: dict[str, str] = {}
    track: dict[str, str] = {}
    for name in NAMES:
        s = status[name]
        if force_forward:
            track[name] = "A"
        elif s == "TRACK_A":
            track[name] = "A"
        elif s == "UNDERPOWERED" and mode == "A+B":
            track[name] = "B"
        else:
            codes[name] = s
    cand = [n for n in NAMES if n in track]
    if not cand:
        return codes
    hold = later["holdout"]
    h_adj = holm([hold[n]["p_fut"] for n in cand])
    fwd = []
    for n, p in zip(cand, h_adj):
        if p <= proc.alpha_fut:
            codes[n] = "HOLDOUT_FAIL"
        else:
            fwd.append(n)
    if not fwd:
        return codes
    final = later["final"]
    alive = []
    for n in fwd:
        r_fwd = final[n]["returns"]
        limit = proc.mdd_ratio * st[n]["mdd"]
        breach = any(max_drawdown(r_fwd[:k]) > limit for k in range(proc.risk_check_days, len(r_fwd) + 1,
                                                                    proc.risk_check_days))
        if breach:
            codes[n] = "RISK_LIMIT"
        else:
            alive.append(n)
    for look in ("interim", "final"):
        if not alive:
            break
        w = later[look]
        adj = holm([r1a_reject_pvalue(w[n]["p_fut"], w[n]["p2low"]) for n in alive])
        survivors = []
        for n, p in zip(alive, adj):
            if p <= proc.alpha_fut / 2:
                codes[n] = "FORWARD_FAIL"
            else:
                survivors.append(n)
        alive = survivors
    eff = holm([final[n]["p1"] for n in fwd])   # family = every strategy that went forward
    for n, p in zip(fwd, eff):
        if n not in alive:
            continue
        if p <= proc.alpha_f:
            codes[n] = "CONFIRMED" if track[n] == "A" else EXPLORATORY_PASS
        else:
            codes[n] = "FORWARD_INCONCLUSIVE"
    return codes


def _run_task(task: tuple) -> dict[str, Any]:
    return run_replication(*task)


# --- aggregation ---------------------------------------------------------------------------------

def _rate(hits: int, n: int) -> dict[str, float]:
    p = hits / n if n else float("nan")
    return {"estimate": p, "mc_se": math.sqrt(p * (1 - p) / n) if n else float("nan"), "n": n}


def truth_flags(truth: dict[str, dict[str, float]], theta_min: float) -> dict[str, dict[str, bool]]:
    out = {}
    for name, t in truth.items():
        sr = [t[f"sr_{s}"] for s in SCENARIOS]
        out[name] = {
            "h1_null": sr[0] <= 0,
            "h2_null": t["excess_E0"] <= 0,
            "reject_null": min(sr) >= theta_min and t["excess_E0"] >= 0,   # no REJECT should happen
            "later_reject_null": sr[0] >= theta_min,                       # holdout/forward futility null
            "unprofitable": sr[0] <= 0,                                    # PAPER would be false
        }
    return out


def aggregate(records: list[dict[str, Any]], truth: dict, proc: Procedure) -> dict[str, Any]:
    n = len(records)
    flags = truth_flags(truth, proc.theta_min)
    res: dict[str, Any] = {"per_strategy": {}, "study": {}}
    for name in NAMES:
        recs = [r["strategies"][name] for r in records]
        row = {
            "truth": {**truth[name], **flags[name]},
            "h1_unadjusted_rejection": _rate(sum(r["p1"] <= proc.alpha_s for r in recs), n),
            "h2_unadjusted_rejection": _rate(sum(r["p2"] <= proc.alpha_s for r in recs), n),
            "s_pass": _rate(sum(r["s_pass"] for r in recs), n),
            "confirmatory_status": {},
        }
        for code in sorted({r["conf_status"] for r in recs}):
            row["confirmatory_status"][code] = _rate(sum(r["conf_status"] == code for r in recs), n)
        for mode in MODES:
            codes = [r[mode].get(name, "?") for r in records]
            row[mode] = {
                "reject": _rate(sum(c in REJECT_CODES for c in codes), n),
                "paper": _rate(sum(c in PAPER_CODES for c in codes), n),
                "exploratory_pass": _rate(sum(c == EXPLORATORY_PASS for c in codes), n),
                "research_more": _rate(sum(c not in REJECT_CODES and c not in PAPER_CODES for c in codes), n),
                "codes": {c: _rate(codes.count(c), n) for c in sorted(set(codes))},
            }
        res["per_strategy"][name] = row

    def any_hit(pred) -> int:
        return sum(1 for r in records if any(pred(r, name) for name in NAMES))

    s_null = [nm for nm in NAMES if flags[nm]["h1_null"] or flags[nm]["h2_null"]]
    rej_null = [nm for nm in NAMES if flags[nm]["reject_null"]]
    later_null = [nm for nm in NAMES if flags[nm]["later_reject_null"]]
    unprof = [nm for nm in NAMES if flags[nm]["unprofitable"]]
    study = res["study"]
    study["s_fwer"] = _rate(any_hit(lambda r, nm: nm in s_null and r["strategies"][nm]["s_pass"]), n) \
        if s_null else None
    study["false_reject_confirmatory_fwer"] = _rate(any_hit(
        lambda r, nm: nm in rej_null and r["strategies"][nm]["conf_status"] in CONFIRMATORY_REJECT), n) \
        if rej_null else None
    for mode in MODES:
        m: dict[str, Any] = {}
        m["false_reject_later_fwer"] = _rate(any_hit(
            lambda r, nm: nm in later_null and r[mode].get(nm) in LATER_FUTILITY_REJECT), n) if later_null else None
        m["risk_limit_any"] = _rate(any_hit(lambda r, nm: r[mode].get(nm) == "RISK_LIMIT"), n)
        m["false_paper_fwer"] = _rate(any_hit(
            lambda r, nm: nm in unprof and r[mode].get(nm) in PAPER_CODES), n) if unprof else None
        m["false_exploratory_pass_fwer"] = _rate(any_hit(
            lambda r, nm: nm in unprof and r[mode].get(nm) == EXPLORATORY_PASS), n) if unprof else None
        rejected = sum(1 for r in records if all(r[mode].get(nm) in REJECT_CODES for nm in NAMES))
        papered = sum(1 for r in records if any(r[mode].get(nm) in PAPER_CODES for nm in NAMES))
        m["study_reject"] = _rate(rejected, n)
        m["study_paper"] = _rate(papered, n)
        m["study_research_more"] = _rate(n - rejected - papered, n)
        study[mode] = m
    return res


# --- scenario runner -------------------------------------------------------------------------------

@dataclass
class RunConfig:
    reps: int
    seed: int = 20261012
    workers: int = 1
    truth_years: int = 400
    costs: Costs = field(default_factory=Costs)
    procedure: Procedure = field(default_factory=Procedure)
    layout: Layout = field(default_factory=Layout)


def run_scenario(scenario: Scenario, cfg: RunConfig) -> dict[str, Any]:
    if cfg.layout.warmup < min_warmup():
        raise ValueError(f"warmup {cfg.layout.warmup} < {min_warmup()} (first scenario day needs a signal)")
    started = datetime.now(UTC)
    dgp, truth, calib = resolve(scenario, cfg.costs, cfg.truth_years, cfg.seed)
    tasks = [(dgp, cfg.costs, cfg.procedure, cfg.layout, scenario.force_forward,
              derived_seed(cfg.seed, scenario.name, "rep", str(i))) for i in range(cfg.reps)]
    if cfg.workers > 1:
        with ProcessPoolExecutor(max_workers=cfg.workers) as pool:
            records = list(pool.map(_run_task, tasks, chunksize=max(1, cfg.reps // (cfg.workers * 4))))
    else:
        records = [_run_task(t) for t in tasks]
    return {
        "scenario": {"name": scenario.name, "description": scenario.description,
                     "force_forward": scenario.force_forward, "dgp": asdict(dgp), "calibration": calib},
        "evidence": "NOT_EVIDENCE (synthetic)",
        "metrics": aggregate(records, truth, cfg.procedure),
        "records": records,
        "started_utc": started.isoformat(), "finished_utc": datetime.now(UTC).isoformat(),
    }


def manifest(cfg: RunConfig, scenarios: Sequence[Scenario]) -> dict[str, Any]:
    return {
        "schema": "moneylab.research_v06_sim/1",
        "evidence": "NOT_EVIDENCE (synthetic Monte Carlo of the v0.6 DRAFT rules)",
        "baseline_note": "procedure values are simulation comparison baselines (draft 18.1), not preregistered",
        "moneylab_version": __version__, "python": platform.python_version(),
        "reps": cfg.reps, "seed": cfg.seed, "workers": cfg.workers, "truth_years": cfg.truth_years,
        "costs": asdict(cfg.costs), "procedure": asdict(cfg.procedure), "layout": asdict(cfg.layout),
        "scenarios": [s.name for s in scenarios],
    }
