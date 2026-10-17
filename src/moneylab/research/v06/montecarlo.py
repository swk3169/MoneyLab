"""Monte Carlo operating characteristics of the v0.6 DRAFT decision rules on SYNTHETIC paths (MC-V06).

Contract: docs/tasks/MC-V06/WORK_ORDER.md. Every output is SYNTHETIC / NOT_EVIDENCE.

One replication = one synthetic path covering warmup, confirmatory, historical holdout, excluded days and the
longest forward period, generated without breaks (dependence across boundaries is kept). The replication stores
p-values and risk outcomes only (the per-rep record); every draft 18.1 candidate option is then decided from the
stored values by deterministic post-processing (common random numbers, no extra simulation):
  D1 theta_min       futility p-values from the same bootstrap resamples for every candidate
  D2 alpha_fut, D3 Holm on futility, D5 alpha_F, D7 interim alpha split: thresholds on the stored p-values
  D4 forward S_F with or without H2: both p-values are stored
  D6 T_F: forward windows of 12 / 24 / 36 calendar months from the same forward path
  risk: MAX_DRAWDOWN_LOG, CUMULATIVE_FROM_L | MONTH_ONLY, gt | ge (research/v06/risk_model.py)
D8 and D9 are not Monte Carlo dimensions here (BT-4); D10 is out of scope.

Rules applied per candidate: 8.1 segment accounting, H1, B1/H2, IUT + Holm (S), E-a/E-b/E-c, R1-A REJECT
combination (candidate), holdout futility, monthly forward risk limit, interim and final forward failure checks,
forward S_F efficacy. Forward events are evaluated in time order (draft 11.3: risk is checked every month,
futility only at the interim and final analyses): risk violations up to the interim, interim failure, risk
violations up to T_F, final failure, efficacy.

Two track modes are decided on the same path:
  "A"    confirmatory track only (E = PASS and S = PASS go forward)
  "A+B"  plus the exploratory track (E = PASS, S = FAIL go forward); a forward pass from the
         exploratory track is FORWARD_EXPLORATORY_PASS, never CONFIRMED / PAPER_CANDIDATE

Simulation calendar (NOT_A_BT4_DECISION): forward start L on the first day of a UTC month, one synthetic daily
observation per calendar day, risk checked per calendar month. A mid-month L is a separately labelled,
risk-only sensitivity; the old 30-day risk check is kept only under LEGACY_30D_COMPARISON.

Not simulated: data quality (Q = VALID assumed), fee confirmation (decision fee only), E_op (operating costs
assumed covered), missing data and revisions, engine return generation (hourly bars, ENGINE_WINDOW_BT3B shifts).
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import platform
from collections import Counter
from collections.abc import Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path as FsPath
from typing import Any

from moneylab import __version__
from moneylab.research.stats import derived_seed
from moneylab.research.v06 import risk_model as RM
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
from moneylab.storage.atomic import atomic_open, atomic_write_bytes, sha256_file

SCHEMA = "moneylab.research_v06_sim/2"
EVIDENCE = "SYNTHETIC / NOT_EVIDENCE"
BASELINE_NOTE = "procedure values and candidate options are simulation comparison baselines (draft 18.1), " \
                "not preregistered; MC-V06 selects no D1-D9 value"

# PRECISION_REPETITION_CONTRACT: four separate axes, never interchanged
R_OUTER = 10_000          # outer synthetic-path replications
B_BOOT = 9_999            # stationary bootstrap resamples per test
K_RAND = 9_999            # B1 random placements per test
TRUTH_YEARS = 400         # long path for the scenario truth and the calibration
TARGET_MAX_MC_SE = 0.005
ADAPTIVE_STOPPING = "PROHIBITED"

PRIMARY = "PRIMARY_MONTH_START"
SENSITIVITY = "SENSITIVITY_MID_MONTH"
LEGACY = "LEGACY_30D_COMPARISON"
LEGACY_CHECK_DAYS = 30
CALENDAR_STATUS = "NOT_A_BT4_DECISION"

NAMES = tuple(STRATEGIES)
REJECT_CODES = frozenset({"UNPROFITABLE", "NOT_ROBUST", "HOLDOUT_FAIL", "FORWARD_FAIL", "RISK_LIMIT"})
CONFIRMATORY_REJECT = frozenset({"UNPROFITABLE", "NOT_ROBUST"})
LATER_FUTILITY_REJECT = frozenset({"HOLDOUT_FAIL", "FORWARD_FAIL"})
PAPER_CODES = frozenset({"CONFIRMED"})
EXPLORATORY_PASS = "FORWARD_EXPLORATORY_PASS"
MODES = ("A", "A+B")

INTERIM_HALF = "ALPHA_FUT_HALF_EACH"   # D7: alpha_fut / 2 at the interim and at the final analysis
INTERIM_FULL = "ALPHA_FUT_EACH"        # D7: alpha_fut at both
INTERIM_NONE = "NO_INTERIM"            # D7: final analysis only (also forced when T_F = the interim time)
INTERIM_OPTIONS = (INTERIM_HALF, INTERIM_FULL, INTERIM_NONE)

_SOURCE_FILES = ("research/stats.py", "research/v06/__init__.py", "research/v06/montecarlo.py",
                 "research/v06/procedures.py", "research/v06/risk_model.py", "research/v06/synthetic.py")


@dataclass(frozen=True)
class Costs:
    fee_bps: float = 25.0                                  # decision fee until the account fee is confirmed
    slip_bps: tuple[float, float, float] = (5.0, 10.0, 10.0)  # E0, E1, E2 one-way spread + slippage
    impact_bps: float = 3.2                                # iota at 10M KRW (assumption, draft 7)

    def log_costs(self) -> dict[str, float]:
        return {s: trade_cost_log(self.fee_bps, k, self.impact_bps) for s, k in zip(SCENARIOS, self.slip_bps)}


@dataclass(frozen=True)
class Procedure:
    """Fixed procedure values and the draft 18.1 candidate options evaluated by post-processing. Simulation
    comparison baselines, NOT preregistered values; no option is selected here."""
    alpha_s: float = 0.05                                   # confirmatory S (fixed in the draft)
    mean_block: float = 20.0
    bootstrap: int = B_BOOT                                 # B_BOOT
    draws: int = K_RAND                                     # K_RAND (B1 placements per test)
    min_roundtrips: int = 20
    min_positive_year_share: float = 0.60
    theta_min_options: tuple[float, ...] = (0.3, 0.5, 0.7)          # D1
    alpha_fut_options: tuple[float, ...] = (0.05, 0.10)             # D2
    futility_holm_options: tuple[bool, ...] = (True, False)         # D3
    forward_h2_options: tuple[bool, ...] = (True, False)            # D4
    alpha_f_options: tuple[float, ...] = (0.05, 0.10, 0.20)         # D5
    interim_options: tuple[str, ...] = INTERIM_OPTIONS              # D7 (D6 = SimulationCalendar.final_months)
    risk_ratio: float = 1.5                                         # draft 11.3 row 12
    risk_accumulation_options: tuple[str, ...] = RM.ACCUMULATION_MODES
    risk_comparison_options: tuple[str, ...] = RM.COMPARISONS

    def risk_policies(self) -> list[RM.RiskPolicy]:
        return [RM.RiskPolicy(RM.MAX_DRAWDOWN_LOG, self.risk_ratio, cmp, acc)
                for acc in self.risk_accumulation_options for cmp in self.risk_comparison_options]


@dataclass(frozen=True)
class Layout:
    """Day counts before the forward start L. The forward period is set by SimulationCalendar (months), not here."""
    warmup: int = 122               # draft 8: M120 lookback 120 + 2-day execution lag (see min_warmup)
    confirmatory: int = 2227        # ~6.1 years (listing date unverified)
    holdout: int = 914              # 2024-04-01 .. 2026-10-02 (D9)
    excluded: int = 60              # 2026-10-02 .. L = 2026-12-01 (>= the 40 exposed days, rounded up to a month start)
    # /1 day counts, accepted so /1 callers keep working (tests/test_v06_randomness.py); NOT used by /2
    forward: int | None = None
    interim: int | None = None

    def bounds(self, calendar: SimulationCalendar) -> dict[str, tuple[int, int]]:
        c0 = self.warmup
        c1 = c0 + self.confirmatory
        h1 = c1 + self.holdout
        f0 = h1 + self.excluded
        out = {"confirmatory": (c0, c1), "holdout": (c1, h1), "risk": (f0, f0 + calendar.risk_days)}
        for months in calendar.final_months:
            out[f"forward_{months}m"] = (f0, f0 + calendar.forward_days(months))
        return out

    def total_days(self, calendar: SimulationCalendar) -> int:
        return self.warmup + self.confirmatory + self.holdout + self.excluded + calendar.risk_days + 3


@dataclass(frozen=True)
class SimulationCalendar:
    """MC-V06 simulation calendar (NOT_A_BT4_DECISION). Forward observation t is on date L + t."""
    forward_start: str = "2026-12-01"               # L, PRIMARY: first day of a UTC calendar month
    interim_months: int = 12                        # draft 10.7: interim analysis, failure checks only
    final_months: tuple[int, ...] = (12, 24, 36)    # D6 candidates
    sensitivity_forward_start: str = "2026-12-16"   # SENSITIVITY: mid-month L, risk grouping only

    def __post_init__(self) -> None:
        L = RM.parse_date(self.forward_start)
        if L.day != 1:
            raise ValueError("forward_start must be the first day of a UTC month (primary convention)")
        if RM.parse_date(self.sensitivity_forward_start).day == 1:
            raise ValueError("sensitivity_forward_start must be mid-month")
        if not self.final_months or list(self.final_months) != sorted(set(self.final_months)):
            raise ValueError("final_months must be sorted, unique and non-empty")
        if not 1 <= self.interim_months <= self.final_months[0]:
            raise ValueError("interim_months must be >= 1 and <= the shortest final_months")

    def forward_days(self, months: int, convention: str = PRIMARY) -> int:
        start = self.forward_start if convention == PRIMARY else self.sensitivity_forward_start
        return RM.forward_days(RM.parse_date(start), months)

    @property
    def risk_days(self) -> int:
        """Length of the forward path: the longest T_F under either convention."""
        return max(self.forward_days(self.final_months[-1], c) for c in (PRIMARY, SENSITIVITY))

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "status": CALENDAR_STATUS, "primary": PRIMARY, "sensitivity": SENSITIVITY,
                "observation_rule": "forward daily observation t has UTC calendar date L + t days",
                "risk_check": "calendar months of the forward dates (research/v06/risk_model.py)",
                "forward_days": {str(m): {c: self.forward_days(m, c) for c in (PRIMARY, SENSITIVITY)}
                                 for m in self.final_months},
                "risk_days": self.risk_days}


@dataclass(frozen=True)
class Scenario:
    name: str
    dgp: DGP
    calibrate: tuple[str, str, float] | None = None   # (strategy, "E0" | "min", target annual Sharpe)
    force_forward: bool = False                        # selection stress: every strategy goes forward
    description: str = ""

    def identity(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "force_forward": self.force_forward,
                "dgp": asdict(self.dgp), "calibrate": list(self.calibrate) if self.calibrate else None}


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


def mc_v06_scenarios(proc: Procedure | None = None) -> list[Scenario]:
    """The tier1 family with the REJECT-boundary scenario instantiated once per D1 candidate (the boundary sits
    at theta_min, so one boundary per candidate). Every other tier1 scenario is unchanged."""
    proc = proc or Procedure()
    out = []
    for s in tier1_scenarios():
        if s.name != "boundary":
            out.append(s)
            continue
        for theta in proc.theta_min_options:
            (b,) = [x for x in tier1_scenarios(theta) if x.name == "boundary"]
            out.append(replace(b, name=f"boundary_theta_{theta:.1f}".replace(".", "p"),
                               description=f"{b.description} (D1 candidate {theta!r})"))
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


# --- one replication (the per-rep record) ---------------------------------------------------------

def theta_key(theta: float) -> str:
    return repr(float(theta))


def _yearly_positive_share(r: Sequence[float], min_days: int = 180) -> float:
    chunks = [r[i:i + 365] for i in range(0, len(r), 365)]
    chunks = [ch for ch in chunks if len(ch) >= min_days]
    return sum(1 for ch in chunks if sum(ch) > 0) / len(chunks) if chunks else 0.0


def _window_stats(path: Path, sigs: dict, lc: dict, proc: Procedure, g0: int, g1: int, seed: int,
                  tag: str) -> dict[str, dict[str, Any]]:
    """E0 statistics of every strategy on one later window (holdout or a forward window). The futility
    p-value of every D1 candidate uses the same bootstrap resamples."""
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
        out[name] = {"p1": h1_pvalue(m, boots[i]), "p2": p2, "p2low": p2low,
                     "p_fut": {theta_key(t): futility_pvalue(m, boots[i], futility_delta(t, r))
                               for t in proc.theta_min_options}}
    return out


def _mark_to_market(market: list[float], pos: list[int], cost: float) -> list[float]:
    """Segment returns (virtual entry included) without the virtual exit on the last day: the forward path is an
    ongoing operation whose wealth is marked to market at every monthly check. A held extra day of zero return
    carries the exit and is dropped, so the other days are exactly segment_returns' values."""
    if not market:
        return []
    return segment_returns([*market, 0.0], [*pos, pos[-1]], cost)[:-1]


def _risk_outcomes(r: list[float], reference: float, proc: Procedure,
                   calendar: SimulationCalendar) -> dict[str, Any]:
    """Primary: first violating calendar month (0 = month of L) per risk policy. Sensitivity (mid-month L):
    violation within each T_F. Both on the same forward observations; only the dates differ."""
    L = RM.parse_date(calendar.forward_start)
    Ls = RM.parse_date(calendar.sensitivity_forward_start)
    primary, sens = {}, {}
    for pol in proc.risk_policies():
        primary[pol.key] = RM.first_violation(r, L, reference, pol)
        sens[pol.key] = {str(m): RM.first_violation(r[:calendar.forward_days(m, SENSITIVITY)], Ls, reference, pol)
                         is not None for m in calendar.final_months}
    return {PRIMARY: primary, SENSITIVITY: sens}


def _legacy_first_breach(r: list[float], reference: float, proc: Procedure) -> int | None:
    """LEGACY_30D_COMPARISON: the old harness check, cumulative MDD after every 30 days > ratio * reference.
    Returns the first breaching day count k (30, 60, ...) or None."""
    pol = RM.RiskPolicy(RM.MAX_DRAWDOWN_LOG, proc.risk_ratio, RM.GT, RM.CUMULATIVE_FROM_L)
    running = RM.running_max_drawdown_log(r)
    for k in range(LEGACY_CHECK_DAYS, len(r) + 1, LEGACY_CHECK_DAYS):
        if RM.decide(running[k - 1], reference, pol) == RM.VIOLATION:
            return k
    return None


def run_replication(dgp: DGP, costs: Costs, proc: Procedure, layout: Layout, force_forward: bool, seed: int,
                    calendar: SimulationCalendar | None = None) -> dict[str, Any]:
    """The per-rep record: every stored value needed to decide any candidate combination. No decision codes, so
    force_forward (a decision rule, applied in post-processing from Scenario.force_forward) does not change it; the
    /1 positional signature is kept for existing callers. calendar defaults to the primary SimulationCalendar."""
    calendar = calendar or SimulationCalendar()
    path = make_path(dgp, layout.total_days(calendar), seed)
    sigs = strategy_signals(path)
    lc = costs.log_costs()
    b = layout.bounds(calendar)
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
        draws = b1_means(market0, pos0, lc["E0"], proc.draws, derived_seed(seed, "conf", "b1", name))
        p2, p2low = randomization_pvalues(ms[0], draws)
        st[name] = {
            "p1": h1_pvalue(ms[0], bs[0]), "p2": p2, "p2low": p2low,
            "p_maxt": {theta_key(t): maxt_futility_pvalue(ms, bs, [futility_delta(t, conf[name][s][2])
                                                                   for s in SCENARIOS])
                       for t in proc.theta_min_options},
            # draft 10.6 (1) on E0 alone (same resamples as p_maxt); test-level reporting only, not the decision input
            "p_fut_E0": {theta_key(t): futility_pvalue(ms[0], bs[0], futility_delta(t, r0))
                         for t in proc.theta_min_options},
            "ea": ms[0] > 0 and ms[0] > mean(draws), "eb": ms[1] > 0 and ms[2] > 0,
            "ec": _yearly_positive_share(r0) >= proc.min_positive_year_share,
            "roundtrips": roundtrips(pos0), "risk_reference_mdd": RM.max_drawdown_log(r0),
        }
    s_adj = iut_holm([st[n]["p1"] for n in NAMES], [st[n]["p2"] for n in NAMES])

    hold = _window_stats(path, sigs, lc, proc, *b["holdout"], seed, "holdout")
    fwd = {str(m): _window_stats(path, sigs, lc, proc, *b[f"forward_{m}m"], seed, f"forward_{m}m")
           for m in calendar.final_months}
    k0, k1 = b["risk"]

    out: dict[str, Any] = {}
    for i, name in enumerate(NAMES):
        market, pos = segment_market_positions(path, sigs[name], "E0", k0, k1)
        r_risk = _mark_to_market(market, pos, lc["E0"])
        ref = st[name]["risk_reference_mdd"]
        out[name] = {
            **st[name], "s_pass": s_adj[i] <= proc.alpha_s,
            "holdout_p_fut": hold[name]["p_fut"],
            "forward": {m: fwd[m][name] for m in fwd},
            "risk": _risk_outcomes(r_risk, ref, proc, calendar),
            LEGACY: {"first_breach_day": _legacy_first_breach(r_risk, ref, proc)},
        }
    return {"strategies": out}


# --- decisions (post-processing of the stored record) -------------------------------------------------

@dataclass(frozen=True)
class DecisionPolicy:
    """One combination of draft 18.1 candidate options plus a risk policy (a simulation point, not a choice)."""
    theta_min: float        # D1
    alpha_fut: float        # D2
    futility_holm: bool     # D3
    forward_h2: bool        # D4
    alpha_f: float          # D5
    final_months: int       # D6
    interim: str            # D7
    risk: RM.RiskPolicy

    @property
    def key(self) -> str:
        return (f"D1={self.theta_min!r};D2={self.alpha_fut!r};D3={'HOLM' if self.futility_holm else 'NO_HOLM'};"
                f"D4={'H1_H2' if self.forward_h2 else 'H1_ONLY'};D5={self.alpha_f!r};D6={self.final_months};"
                f"D7={self.interim};RISK={self.risk.key}")

    def to_dict(self) -> dict[str, Any]:
        return {"D1_theta_min": self.theta_min, "D2_alpha_fut": self.alpha_fut,
                "D3_futility_holm": self.futility_holm, "D4_forward_h2": self.forward_h2,
                "D5_alpha_f": self.alpha_f, "D6_final_months": self.final_months, "D7_interim": self.interim,
                "risk": asdict(self.risk)}


def decision_grid(proc: Procedure, calendar: SimulationCalendar) -> list[DecisionPolicy]:
    """Every candidate combination, in a fixed order. T_F equal to the interim time has no interim (draft 18.1 D6)."""
    out = []
    for theta, af, fh, h2, a_f, tf in itertools.product(
            proc.theta_min_options, proc.alpha_fut_options, proc.futility_holm_options, proc.forward_h2_options,
            proc.alpha_f_options, calendar.final_months):
        interims = proc.interim_options if tf > calendar.interim_months else (INTERIM_NONE,)
        for interim in interims:
            for risk in proc.risk_policies():
                out.append(DecisionPolicy(theta, af, fh, h2, a_f, tf, interim, risk))
    return out


def comparison_baseline(proc: Procedure, calendar: SimulationCalendar) -> DecisionPolicy:
    """The point reported as `metrics` (old harness comparison values): first option of each list, Holm, H1 only,
    middle T_F, alpha_fut / 2 per look, cumulative gt risk. A comparison point only, NOT a selection."""
    tf = calendar.final_months[len(calendar.final_months) // 2]
    return DecisionPolicy(proc.theta_min_options[0], proc.alpha_fut_options[0], True, False,
                          proc.alpha_f_options[0], tf, INTERIM_HALF if tf > calendar.interim_months else INTERIM_NONE,
                          RM.RiskPolicy(RM.MAX_DRAWDOWN_LOG, proc.risk_ratio, RM.GT, RM.CUMULATIVE_FROM_L))


def _adjust(pvalues: list[float], use_holm: bool) -> list[float]:
    return holm(pvalues) if use_holm else list(pvalues)


def confirmatory_status(record: dict[str, Any], theta_min: float, alpha_fut: float, futility_holm: bool,
                        proc: Procedure) -> dict[str, str]:
    s = record["strategies"]
    tk = theta_key(theta_min)
    rej = _adjust([r1a_reject_pvalue(s[n]["p_maxt"][tk], s[n]["p2low"]) for n in NAMES], futility_holm)
    status: dict[str, str] = {}
    for name, p in zip(NAMES, rej):
        x = s[name]
        if x["roundtrips"] < proc.min_roundtrips:
            status[name] = "INSUFFICIENT_SAMPLE"
        elif (not x["ea"] or not x["eb"]) and p <= alpha_fut:
            status[name] = "UNPROFITABLE" if not x["ea"] else "NOT_ROBUST"
        elif not (x["ea"] and x["eb"] and x["ec"]):
            status[name] = "ECONOMIC_INCONCLUSIVE"
        else:
            status[name] = "TRACK_A" if x["s_pass"] else "UNDERPOWERED"
    return status


def decide(record: dict[str, Any], status: dict[str, str], policy: DecisionPolicy, mode: str, force_forward: bool,
           calendar: SimulationCalendar) -> dict[str, str]:
    """Decision code of every strategy for one candidate combination and track mode."""
    if policy.interim != INTERIM_NONE and policy.final_months <= calendar.interim_months:
        raise ValueError("an interim analysis needs T_F > the interim time")
    s = record["strategies"]
    tk = theta_key(policy.theta_min)
    codes: dict[str, str] = {}
    track: dict[str, str] = {}
    for name in NAMES:
        st = status[name]
        if force_forward or st == "TRACK_A":
            track[name] = "A"
        elif st == "UNDERPOWERED" and mode == "A+B":
            track[name] = "B"
        else:
            codes[name] = st
    cand = [n for n in NAMES if n in track]
    if not cand:
        return codes
    fwd = []
    for n, p in zip(cand, _adjust([s[n]["holdout_p_fut"][tk] for n in cand], policy.futility_holm)):
        if p <= policy.alpha_fut:
            codes[n] = "HOLDOUT_FAIL"
        else:
            fwd.append(n)
    if not fwd:
        return codes
    look_alpha = policy.alpha_fut / 2 if policy.interim == INTERIM_HALF else policy.alpha_fut
    looks = ([calendar.interim_months] if policy.interim != INTERIM_NONE else []) + [policy.final_months]
    rk = policy.risk.key
    alive = list(fwd)
    for months in looks:
        survivors = []
        for n in alive:   # risk is checked every month up to this analysis and comes first (draft 11.3 row 12)
            idx = s[n]["risk"][PRIMARY][rk]
            if idx is not None and idx < months:
                codes[n] = "RISK_LIMIT"
            else:
                survivors.append(n)
        alive = survivors
        if not alive:
            break
        w = str(months)
        adj = _adjust([r1a_reject_pvalue(s[n]["forward"][w]["p_fut"][tk], s[n]["forward"][w]["p2low"])
                       for n in alive], policy.futility_holm)
        survivors = []
        for n, p in zip(alive, adj):
            if p <= look_alpha:
                codes[n] = "FORWARD_FAIL"
            else:
                survivors.append(n)
        alive = survivors
    w = str(policy.final_months)
    eff = holm([max(s[n]["forward"][w]["p1"], s[n]["forward"][w]["p2"]) if policy.forward_h2
                else s[n]["forward"][w]["p1"] for n in fwd])   # S_F family = every strategy that went forward
    for n, p in zip(fwd, eff):
        if n in alive:
            if p <= policy.alpha_f:
                codes[n] = "CONFIRMED" if track[n] == "A" else EXPLORATORY_PASS
            else:
                codes[n] = "FORWARD_INCONCLUSIVE"
    return codes


# --- aggregation (the summary) ------------------------------------------------------------------------

def _rate(hits: int, n: int) -> dict[str, float | None]:
    """Proportion with its Monte Carlo standard error. n = 0 (a conditional rate with no cases)
    gives None, not NaN: NaN breaks equality checks and is not valid JSON."""
    if not n:
        return {"estimate": None, "mc_se": None, "n": 0}
    p = hits / n
    return {"estimate": p, "mc_se": math.sqrt(p * (1 - p) / n), "n": n}


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


class _Tally:
    """Counts of one candidate combination, accumulated record by record (no record is kept here)."""

    def __init__(self) -> None:
        self.codes = {name: {mode: Counter() for mode in MODES} for name in NAMES}
        self.study = {mode: Counter() for mode in MODES}
        self.false_reject_confirmatory = 0


def _add(t: _Tally, codes: dict[str, dict[str, str]], status: dict[str, str],
         flags: dict[str, dict[str, bool]]) -> None:
    if any(flags[n]["reject_null"] and status[n] in CONFIRMATORY_REJECT for n in NAMES):
        t.false_reject_confirmatory += 1
    for mode in MODES:
        c = codes[mode]
        for n in NAMES:
            t.codes[n][mode][c[n]] += 1
        sc = t.study[mode]
        sc["study_reject"] += all(c[n] in REJECT_CODES for n in NAMES)
        sc["study_paper"] += any(c[n] in PAPER_CODES for n in NAMES)
        sc["risk_limit_any"] += any(c[n] == "RISK_LIMIT" for n in NAMES)
        sc["false_reject_later"] += any(flags[n]["later_reject_null"] and c[n] in LATER_FUTILITY_REJECT for n in NAMES)
        sc["false_paper"] += any(flags[n]["unprofitable"] and c[n] in PAPER_CODES for n in NAMES)
        sc["false_exploratory_pass"] += any(flags[n]["unprofitable"] and c[n] == EXPLORATORY_PASS for n in NAMES)


def _combo_metrics(t: _Tally, n: int, flags: dict[str, dict[str, bool]]) -> dict[str, Any]:
    has = {k: any(flags[nm][k] for nm in NAMES) for k in ("reject_null", "later_reject_null", "unprofitable")}
    per = {}
    for name in NAMES:
        per[name] = {}
        for mode in MODES:
            cc = t.codes[name][mode]
            rej = sum(v for c, v in cc.items() if c in REJECT_CODES)
            pap = sum(v for c, v in cc.items() if c in PAPER_CODES)
            per[name][mode] = {"reject": _rate(rej, n), "paper": _rate(pap, n),
                               "exploratory_pass": _rate(cc[EXPLORATORY_PASS], n),
                               "research_more": _rate(n - rej - pap, n), "risk_limit": _rate(cc["RISK_LIMIT"], n),
                               "code_counts": dict(sorted(cc.items()))}
    study: dict[str, Any] = {"false_reject_confirmatory_fwer":
                             _rate(t.false_reject_confirmatory, n) if has["reject_null"] else None}
    for mode in MODES:
        sc = t.study[mode]
        study[mode] = {
            "study_reject": _rate(sc["study_reject"], n), "study_paper": _rate(sc["study_paper"], n),
            "study_research_more": _rate(n - sc["study_reject"] - sc["study_paper"], n),
            "risk_limit_any": _rate(sc["risk_limit_any"], n),
            "false_reject_later_fwer": _rate(sc["false_reject_later"], n) if has["later_reject_null"] else None,
            "false_paper_fwer": _rate(sc["false_paper"], n) if has["unprofitable"] else None,
            "false_exploratory_pass_fwer": _rate(sc["false_exploratory_pass"], n) if has["unprofitable"] else None,
        }
    return {"per_strategy": per, "study": study}


def _max_mc_se(node: Any) -> tuple[float, int]:
    """(largest mc_se, number of rates) over every rate in a summary subtree."""
    if isinstance(node, dict):
        if set(node) == {"estimate", "mc_se", "n"}:
            return (node["mc_se"], 1) if node["mc_se"] is not None else (0.0, 0)
        worst, count = 0.0, 0
        for v in node.values():
            w, c = _max_mc_se(v)
            worst, count = max(worst, w), count + c
        return worst, count
    return 0.0, 0


def alpha_key(alpha: float) -> str:
    return repr(float(alpha))


def forward_futility_alphas(proc: Procedure) -> tuple[float, ...]:
    """Per-look thresholds of the D2 x D7 candidates: alpha_fut / 2 and alpha_fut."""
    return tuple(sorted({a / 2 for a in proc.alpha_fut_options} | set(proc.alpha_fut_options)))


def test_level(strat: Sequence[dict[str, Any]], proc: Procedure, calendar: SimulationCalendar) -> dict[str, Any]:
    """Single-test rejection rates over EVERY replication (unconditional: whether or not the strategy reached that
    stage, no Holm, no R1-A combination, no economic condition). These are the quantities of the draft 10.6 / 10.7
    approximation tables; the decision grid holds the combined decision rates."""
    n = len(strat)

    def rate(pred) -> dict[str, float | None]:
        return _rate(sum(1 for s in strat if pred(s)), n)

    thetas = [theta_key(t) for t in proc.theta_min_options]
    fut_alphas = [alpha_key(a) for a in forward_futility_alphas(proc)]
    per = {}
    for nm in NAMES:
        def by_theta(get, alphas):
            return {tk: {ak: rate(lambda s, tk=tk, a=float(ak): get(s[nm], tk) <= a) for ak in alphas}
                    for tk in thetas}

        fut = [alpha_key(a) for a in proc.alpha_fut_options]
        forward = {}
        for m in calendar.final_months:
            w = str(m)
            forward[w] = {alpha_key(a): {
                "h1": rate(lambda s, w=w, a=a: s[nm]["forward"][w]["p1"] <= a),
                "h2": rate(lambda s, w=w, a=a: s[nm]["forward"][w]["p2"] <= a),
                "h1_h2_max": rate(lambda s, w=w, a=a: max(s[nm]["forward"][w]["p1"], s[nm]["forward"][w]["p2"]) <= a),
            } for a in proc.alpha_f_options}
        per[nm] = {
            "confirmatory_e0_futility": by_theta(lambda x, tk: x["p_fut_E0"][tk], fut),
            "holdout_futility": by_theta(lambda x, tk: x["holdout_p_fut"][tk], fut),
            "forward_pass": forward,
            "forward_futility": {
                "interim": {str(calendar.interim_months): by_theta(
                    lambda x, tk: x["forward"][str(calendar.interim_months)]["p_fut"][tk], fut_alphas)},
                "final": {str(m): by_theta(lambda x, tk, w=str(m): x["forward"][w]["p_fut"][tk], fut_alphas)
                          for m in calendar.final_months},
            },
        }
    return {"note": "unconditional single-test rejection rates: p <= alpha over all replications; keys theta_min -> "
                    "alpha (futility) and T_F -> alpha_F (forward pass); forward futility thresholds are the per-look "
                    "alphas of D2 x D7 (alpha_fut / 2, alpha_fut)",
            "per_strategy": per}


def summarize(records: Sequence[dict[str, Any]], truth: dict, proc: Procedure, calendar: SimulationCalendar,
              force_forward: bool) -> dict[str, Any]:
    """Every candidate combination decided on every record (deterministic post-processing)."""
    n = len(records)
    grid = decision_grid(proc, calendar)
    flags = {theta_key(t): truth_flags(truth, t) for t in proc.theta_min_options}
    tallies = {p.key: _Tally() for p in grid}
    by_stage: dict[tuple, list[DecisionPolicy]] = {}
    for p in grid:
        by_stage.setdefault((p.theta_min, p.alpha_fut, p.futility_holm), []).append(p)
    for rec in records:
        for (theta, af, fh), policies in by_stage.items():
            status = confirmatory_status(rec, theta, af, fh, proc)
            fl = flags[theta_key(theta)]
            for p in policies:
                codes = {mode: decide(rec, status, p, mode, force_forward, calendar) for mode in MODES}
                _add(tallies[p.key], codes, status, fl)
    combos = {p.key: {"policy": p.to_dict(), **_combo_metrics(tallies[p.key], n, flags[theta_key(p.theta_min)])}
              for p in grid}

    strat = [r["strategies"] for r in records]
    s_null = [nm for nm in NAMES if flags[theta_key(proc.theta_min_options[0])][nm]["h1_null"]
              or flags[theta_key(proc.theta_min_options[0])][nm]["h2_null"]]
    common = {
        "per_strategy": {nm: {"h1_unadjusted_rejection": _rate(sum(s[nm]["p1"] <= proc.alpha_s for s in strat), n),
                              "h2_unadjusted_rejection": _rate(sum(s[nm]["p2"] <= proc.alpha_s for s in strat), n),
                              "s_pass": _rate(sum(s[nm]["s_pass"] for s in strat), n)} for nm in NAMES},
        "study": {"s_fwer": _rate(sum(any(nm in s_null and s[nm]["s_pass"] for nm in NAMES) for s in strat), n)
                  if s_null else None},
    }
    risk_sem: dict[str, Any] = {PRIMARY: {}, SENSITIVITY: {}}
    for nm in NAMES:
        risk_sem[PRIMARY][nm] = {pol.key: {str(m): _rate(sum(1 for s in strat if s[nm]["risk"][PRIMARY][pol.key]
                                                             is not None and s[nm]["risk"][PRIMARY][pol.key] < m), n)
                                           for m in calendar.final_months} for pol in proc.risk_policies()}
        risk_sem[SENSITIVITY][nm] = {pol.key: {str(m): _rate(sum(s[nm]["risk"][SENSITIVITY][pol.key][str(m)]
                                                                 for s in strat), n)
                                               for m in calendar.final_months} for pol in proc.risk_policies()}
    legacy = {nm: {str(m): _rate(sum(1 for s in strat if s[nm][LEGACY]["first_breach_day"] is not None
                                     and s[nm][LEGACY]["first_breach_day"] <= calendar.forward_days(m)), n)
                   for m in calendar.final_months} for nm in NAMES}
    baseline = comparison_baseline(proc, calendar)
    out = {
        "replications": n,
        "truth": {nm: {**truth[nm], "flags": {tk: flags[tk][nm] for tk in flags}} for nm in NAMES},
        "comparison_baseline_key": baseline.key,
        "decision_grid": combos,
        "combination_independent": common,
        "test_level": test_level(strat, proc, calendar),
        "risk_semantics": {"note": "unconditional: path-level violation by T_F for every strategy, whether or not "
                                   "it went forward", **risk_sem},
        LEGACY: {"note": "old harness check (cumulative MDD every 30 days, gt); comparison only, not normative",
                 "per_strategy": legacy},
    }
    worst, count = _max_mc_se({k: v for k, v in out.items() if k != LEGACY})
    out["mc_se_check"] = {"target_max_mc_se": TARGET_MAX_MC_SE, "max_mc_se": worst, "rates": count,
                          "worst_case_bound": math.sqrt(0.25 / n) if n else None, "met": worst <= TARGET_MAX_MC_SE}
    return out


# --- runner ---------------------------------------------------------------------------------------------

@dataclass
class RunConfig:
    reps: int
    seed: int = 20261012
    workers: int = 1                  # execution only: results do not depend on it
    truth_years: int = TRUTH_YEARS
    costs: Costs = field(default_factory=Costs)
    procedure: Procedure = field(default_factory=Procedure)
    layout: Layout = field(default_factory=Layout)
    calendar: SimulationCalendar = field(default_factory=SimulationCalendar)


def _validate(cfg: RunConfig) -> None:
    if cfg.layout.warmup < min_warmup():
        raise ValueError(f"warmup {cfg.layout.warmup} < {min_warmup()} (first scenario day needs a signal)")
    if cfg.reps < 1 or cfg.workers < 1 or cfg.truth_years < 1:
        raise ValueError("reps, workers and truth_years must be >= 1")


def _run_task(task: tuple) -> dict[str, Any]:
    i, seed, (dgp, costs, proc, layout, force_forward, calendar) = task
    return {"rep": i, "seed": seed, **run_replication(dgp, costs, proc, layout, force_forward, seed, calendar)}


def replications(dgp: DGP, scenario: Scenario, cfg: RunConfig) -> Iterator[dict[str, Any]]:
    """Per-rep records in rep order (serial and parallel give the same records)."""
    tasks = ((i, derived_seed(cfg.seed, scenario.name, "rep", str(i)),
              (dgp, cfg.costs, cfg.procedure, cfg.layout, scenario.force_forward, cfg.calendar))
             for i in range(cfg.reps))
    if cfg.workers > 1:
        with ProcessPoolExecutor(max_workers=cfg.workers) as pool:
            yield from pool.map(_run_task, tasks, chunksize=max(1, cfg.reps // (cfg.workers * 4)))
    else:
        for t in tasks:
            yield _run_task(t)


def _scenario_summary(scenario: Scenario, dgp: DGP, calib: dict, truth: dict, records: Sequence[dict],
                      cfg: RunConfig) -> dict[str, Any]:
    return {"schema": SCHEMA, "kind": "scenario_summary", "evidence": EVIDENCE,
            "scenario": {**scenario.identity(), "resolved_dgp": asdict(dgp), "calibration": calib},
            **summarize(records, truth, cfg.procedure, cfg.calendar, scenario.force_forward)}


def baseline_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    """The comparison-baseline combination in the old `metrics` shape (per_strategy / study)."""
    combo = summary["decision_grid"][summary["comparison_baseline_key"]]
    common = summary["combination_independent"]
    return {"policy": combo["policy"],
            "per_strategy": {n: {**common["per_strategy"][n], **combo["per_strategy"][n]} for n in NAMES},
            "study": {**common["study"], **combo["study"]}}


def run_scenario(scenario: Scenario, cfg: RunConfig) -> dict[str, Any]:
    """One scenario in memory (development path, used by the `research-v06-sim` CLI): summary and records are
    returned side by side under separate keys. The normative artifact set is written by write_study."""
    _validate(cfg)
    started = datetime.now(UTC)
    dgp, truth, calib = resolve(scenario, cfg.costs, cfg.truth_years, cfg.seed)
    records = list(replications(dgp, scenario, cfg))
    summary = _scenario_summary(scenario, dgp, calib, truth, records, cfg)
    return {"schema": SCHEMA, "evidence": EVIDENCE, "scenario": summary["scenario"],
            "metrics": baseline_metrics(summary), "summary": summary, "records": records,
            "started_utc": started.isoformat(), "finished_utc": datetime.now(UTC).isoformat()}


def source_identity() -> dict[str, dict[str, str]]:
    """Identity of the research/v06 code and research/stats.py without a git subprocess: SHA-256 of the exact
    working-tree bytes (depends on the checkout's line endings), SHA-256 with CRLF normalized to LF, and the git
    blob id of the LF bytes (comparable with `git ls-tree` of the executing commit)."""
    root = FsPath(__file__).resolve().parents[2]
    out = {}
    for rel in _SOURCE_FILES:
        raw = (root / rel).read_bytes()
        lf = raw.replace(b"\r\n", b"\n")
        out[f"moneylab/{rel}"] = {"sha256": hashlib.sha256(raw).hexdigest(),
                                  "sha256_lf": hashlib.sha256(lf).hexdigest(),
                                  "git_blob_lf": hashlib.sha1(b"blob %d\0" % len(lf) + lf).hexdigest()}
    return out


def git_identity(start: FsPath | None = None) -> dict[str, Any]:
    """Executing commit read from the .git files (no subprocess). The working-tree state is not checked here;
    the source SHA-256 in manifest.json identifies the code that ran."""
    out: dict[str, Any] = {"commit": None, "ref": None, "method": "filesystem (.git HEAD/refs, no subprocess)",
                           "worktree_state": "NOT_CHECKED (see manifest source_sha256)"}
    try:
        here = (start or FsPath(__file__)).resolve()
        for d in (here, *here.parents):
            if (d / ".git").exists():
                dotgit = d / ".git"
                break
        else:
            return out
        gitdir = dotgit
        if dotgit.is_file():
            text = dotgit.read_text(encoding="utf-8").strip()
            if not text.startswith("gitdir:"):
                return out
            gitdir = (dotgit.parent / text[len("gitdir:"):].strip()).resolve()
        common = gitdir
        if (gitdir / "commondir").is_file():
            common = (gitdir / (gitdir / "commondir").read_text(encoding="utf-8").strip()).resolve()
        head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
        if not head.startswith("ref: "):
            out["commit"] = head
            return out
        ref = head[len("ref: "):]
        out["ref"] = ref
        for base in (gitdir, common):
            if (base / ref).is_file():
                out["commit"] = (base / ref).read_text(encoding="utf-8").strip()
                return out
        packed = common / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref:
                    out["commit"] = parts[0]
    except OSError:
        pass
    return out


ARTIFACT_SEPARATED = "SEPARATED: manifest.json, scenarios/<name>/summary.json, scenarios/<name>/records.jsonl, " \
                     "execution.json, SHA256SUMS"
ARTIFACT_COMBINED = "COMBINED (research-v06-sim CLI development path: manifest.json + one JSON per scenario with " \
                    "separate summary / records keys, no SHA256SUMS)"


def manifest(cfg: RunConfig, scenarios: Sequence[Scenario], *,
             artifact_layout: str = ARTIFACT_COMBINED) -> dict[str, Any]:
    """Run provenance that does not depend on when or where the run executes (see execution_info)."""
    proc = cfg.procedure
    run_axes = {"R_OUTER": cfg.reps, "B_BOOT": proc.bootstrap, "K_RAND": proc.draws, "TRUTH_YEARS": cfg.truth_years}
    normative = {"R_OUTER": R_OUTER, "B_BOOT": B_BOOT, "K_RAND": K_RAND, "TRUTH_YEARS": TRUTH_YEARS}
    grid = decision_grid(proc, cfg.calendar)
    return {
        "schema": SCHEMA, "evidence": EVIDENCE, "baseline_note": BASELINE_NOTE,
        "artifact_layout": artifact_layout,
        "repetition_axes": {k: {"run": run_axes[k], "normative": normative[k],
                                "matches_normative": run_axes[k] == normative[k]} for k in normative},
        "normative_run": all(run_axes[k] == normative[k] for k in normative),
        "target_max_mc_se": TARGET_MAX_MC_SE, "adaptive_stopping": ADAPTIVE_STOPPING,
        "seeds": {"seed": cfg.seed,
                  "derived_seed_rule": "moneylab.research.stats.derived_seed(seed, *parts) = "
                                       "(seed * 1000003 + crc32('|'.join(parts))) mod 2**32",
                  "replication": "rep_seed = derived_seed(seed, scenario, 'rep', str(i)), i = 0 .. R_OUTER - 1",
                  "truth": "derived_seed(seed, scenario, 'truth'), derived_seed(seed, scenario, 'truth-b1')",
                  "within_replication": "path: rep_seed; bootstrap: derived_seed(rep_seed, tag, 'boot'); B1: "
                                        "derived_seed(rep_seed, tag, 'b1', strategy); tag = conf | holdout | "
                                        "forward_<T>m"},
        "costs": asdict(cfg.costs), "procedure": asdict(proc), "layout": asdict(cfg.layout),
        "simulation_calendar": cfg.calendar.to_dict(),
        "decision_grid": {"combinations": len(grid), "comparison_baseline": comparison_baseline(proc, cfg.calendar).key,
                          "monte_carlo_dimensions": "D1-D7 + risk policy, by post-processing of the per-rep records",
                          "not_dimensions": {"D8": "BT-4", "D9": "BT-4", "D10": "out of scope"}},
        "bt3e_equivalence": {"normative": ["MAX_DRAWDOWN_LOG", "calendar-month grouping", RM.CUMULATIVE_FROM_L,
                                           RM.MONTH_ONLY, RM.GT, RM.GE],
                             "excluded": ["engine equity", "hourly-bar engine path", "scenario reference times",
                                          "ENGINE_WINDOW_BT3B F = P - 2 days",
                                          "ENGINE_WINDOW_BT3B last_day = N - 3 days"],
                             "bt4_q18": "UNRESOLVED"},
        "scenarios": [s.identity() for s in scenarios],
        "source_sha256": source_identity(),
        "moneylab_version": __version__, "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "reproduction": {"entry_point": "moneylab.research.v06.montecarlo.write_study(out_dir, RunConfig(...), "
                                        "scenarios)",
                         "deterministic_files": "every file except execution.json (and its SHA256SUMS line) is "
                                                "byte-identical for the same source SHA-256, Python version, "
                                                "config and scenarios; workers do not change results"},
    }


def execution_info(started: datetime, finished: datetime, workers: int) -> dict[str, Any]:
    return {"schema": SCHEMA, "kind": "execution", "evidence": EVIDENCE, "started_utc": started.isoformat(),
            "finished_utc": finished.isoformat(), "workers": workers, "git": git_identity(),
            "python": platform.python_version(), "platform": platform.platform()}


def canonical_bytes(payload: Any) -> bytes:
    """Deterministic JSON (sorted keys, no whitespace, no NaN) plus a newline."""
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            + "\n").encode("utf-8")


def write_study(out_dir: FsPath, cfg: RunConfig, scenarios: Sequence[Scenario]) -> FsPath:
    """The /2 artifact set in a NEW directory. Records are streamed to records.jsonl (one canonical JSON line per
    rep, rep order); the summary is a separate file. No resume or checkpoint (MC-V06 NO_RESUME_FEATURE)."""
    _validate(cfg)
    out = FsPath(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    started = datetime.now(UTC)
    atomic_write_bytes(out / "manifest.json",
                       canonical_bytes(manifest(cfg, scenarios, artifact_layout=ARTIFACT_SEPARATED)))
    for s in scenarios:
        d = out / "scenarios" / s.name
        dgp, truth, calib = resolve(s, cfg.costs, cfg.truth_years, cfg.seed)
        records = []
        digest = hashlib.sha256()
        with atomic_open(d / "records.jsonl") as f:
            for rec in replications(dgp, s, cfg):
                line = canonical_bytes(rec)
                f.write(line)
                digest.update(line)
                records.append(rec)
        summary = _scenario_summary(s, dgp, calib, truth, records, cfg)
        summary["records"] = {"file": "records.jsonl", "count": len(records), "sha256": digest.hexdigest()}
        del records
        atomic_write_bytes(d / "summary.json", canonical_bytes(summary))
    atomic_write_bytes(out / "execution.json", canonical_bytes(execution_info(started, datetime.now(UTC), cfg.workers)))
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    sums = "".join(f"{sha256_file(out / rel)}  {rel}\n" for rel in files)
    atomic_write_bytes(out / "SHA256SUMS", sums.encode("utf-8"))
    return out
