"""BT4-FUTILITY-01 DIAG: numerical core of the futility-boundary diagnostic study (G3a), its deterministic
replication engine (G3b-3), storage and resume (G3b-4), the calibration artifact and research identity (G3b-5-1),
and the G5-G8a execution contract of ERRATA-005 (user decisions, run names, the G7 lock, the Windows job and E-BOOT).

Contract: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md (C1 7ac09a6), docs/research_bt4_futility_diag_preregistration.md and
configs/bt4_futility_diag.toml (C2 321b54b), ERRATA-001 (616ed51), ERRATA-002 (2eb876e), ERRATA-003 (b9932dc),
ERRATA-004 (a1b15ff), ERRATA-005 (02aa62b), ERRATA-006 (31d15ed) and ERRATA-007 (59f62ee).
Every result is SYNTHETIC / NOT_EVIDENCE.

The numerical part holds pure functions: the V0 / V0d / V0b60 / S1 p-values (DC2-DC4.1), the F1 / F2 stationary
bootstrap variance (DC4, preregistration 5), the paired-contrast and V-4 numbers used by the decision rules, the
seed namespace / collision bookkeeping (DC10, preregistration 3, ERRATA-002 SEED_STRINGS) and the per-(cell, rep,
window) records of the CORE cells (DC6, DC11, ERRATA-002). Timing, the G6 summary and the command line come later.
The MC-V06 sources (research/stats.py, research/v06/*.py) are imported, never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import os
import queue
import re
import operator
import platform
import random
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path as FsPath
from statistics import NormalDist
from typing import Any

from moneylab.research.stats import _blocks, _Prefix, derived_seed
from moneylab.research.v06.montecarlo import (
    R_OUTER as MCV06_R_OUTER,
    Costs,
    Layout,
    SimulationCalendar,
    _target_sharpe,
    calibrate_edge,
    git_identity,
    source_identity,
)
from moneylab.storage.atomic import TMP_SUFFIX, atomic_write_bytes, sha256_file
from moneylab.research.v06.procedures import (
    ANNUALIZATION_DAYS,
    STRATEGIES,
    annual_sharpe,
    bootstrap_means,
    futility_delta,
    futility_pvalue,
    mean,
    sd,
    segment_returns,
    signals,
)
from moneylab.research.v06.synthetic import (
    DGP,
    Path,
    add_drift,
    draw_noise,
    make_path,
    min_warmup,
    segment_market_positions,
)

EVIDENCE = "SYNTHETIC / NOT_EVIDENCE"

# --- preregistered constants (configs/bt4_futility_diag.toml) -------------------------------------------------

BASE_SEED = 20261029
NAMESPACES = ("FUTDIAG", "FUTDIAG-PILOT", "FUTDIAG-SIGMA", "FUTDIAG-X", "FUTDIAG-TEST")
FORBIDDEN_NAMESPACES = ("FUTVAL",)

PRIMARY_ALPHA = 0.05
SUPPORTED_FWER = 0.025
WEAKENED_PER_HYPOTHESIS = 0.005
MIN_EFFECT = 0.01
MEAN_BLOCK = 20.0
MEAN_BLOCK_V3 = 60.0

F1_NEGATIVE_TOLERANCE_REL = 1e-12
F1_TRUNCATION_EPS = 1e-15
RD_REL = 1e-6
ND_REL = 0.25
ND_FLAG_SHARE = 0.01

R_MIN, R_MAX, R_ROUND = 10_000, 40_000, 1_000
TARGET_MAX_MC_SE_PAIRED = 0.0035
V4_GAMMA_DELTA = 0.0025
V4_GAMMA_SIGMA = 0.0025
V4_BATCHES = 40
V4_APPROX_MAX = 0.5

_N = NormalDist()
Z_HOLM_WORST = _N.inv_cdf(1 - SUPPORTED_FWER / 5)          # 2.575829...
Z_POWER = _N.inv_cdf(0.80)                                 # 0.841621...
Z_WEAKENED = _N.inv_cdf(1 - WEAKENED_PER_HYPOTHESIS)       # z_{0.995}
Z_SIGMA = _N.inv_cdf(1 - V4_GAMMA_SIGMA / 2)               # 3.023341...
Z_ALPHA = _N.inv_cdf(1 - PRIMARY_ALPHA)                    # z_{0.95}

# degeneracy reason codes (DC4.1) and NOT_APPLICABLE (ERRATA-002 SE_FIELDS): the only states allowed to serialize
# as null + reason. NOT_APPLICABLE is not a degeneracy: it marks a quantity a variant does not define.
SD = "DEGENERATE_SAMPLE"
RD = "DEGENERATE_RESAMPLE"
NO_DISCORDANCE = "NO_DISCORDANCE"
NOT_APPLICABLE = "NOT_APPLICABLE"


class StopImplementation(RuntimeError):
    """A preregistered STOP_IMPLEMENTATION condition (e.g. F1 below its negative tolerance, unexpected NaN/Inf)."""


class StopForUserDecision(RuntimeError):
    """A STOP_FOR_USER_DECISION condition (e.g. ERRATA-003 R-1 / R-2 invalid timing, R-4 resume over an abnormal
    end): nothing is estimated, capped or substituted; the user decides."""


class ProcessOpenError(StopImplementation):
    """OpenProcess failed; winerror is the Win32 last error (87 ERROR_INVALID_PARAMETER, 5 ERROR_ACCESS_DENIED, ...)."""

    def __init__(self, pid: int, winerror: int) -> None:
        super().__init__(f"OpenProcess({pid}) failed (Win32 error {winerror})")
        self.pid, self.winerror = pid, winerror


def finite_or_stop(x: float, what: str) -> float:
    if not math.isfinite(x):
        raise StopImplementation(f"non-finite {what}: {x!r}")
    return x


# --- seeds (DC10, preregistration 3) --------------------------------------------------------------------------

SeedPath = tuple[str, str, str, str, str]   # (namespace, cell, rep, window, rule)


def check_namespaces(namespaces: Sequence[str] = NAMESPACES) -> None:
    """Namespace strings must be distinct and never a forbidden one (violation = STOP)."""
    if len(set(namespaces)) != len(namespaces):
        raise StopImplementation(f"duplicate seed namespace in {namespaces!r}")
    bad = sorted(set(namespaces) & set(FORBIDDEN_NAMESPACES))
    if bad:
        raise StopImplementation(f"forbidden seed namespace {bad!r}")


def validate_seed_parts(parts: Sequence[object]) -> tuple[str, ...]:
    """Seed parts must be str, never contain the derived_seed join separator "|", and start with a DC10 namespace."""
    if not parts:
        raise StopImplementation("empty seed parts")
    for p in parts:
        if not isinstance(p, str):
            raise StopImplementation(f"seed part must be str, got {type(p).__name__}: {p!r}")
        if "|" in p:
            raise StopImplementation(f"seed part contains '|': {p!r}")
    if parts[0] not in NAMESPACES:
        raise StopImplementation(f"unknown seed namespace {parts[0]!r}")
    return tuple(str(p) for p in parts)


def seed_path(namespace: str, cell: str, rep: int | str, window: str, rule: str) -> SeedPath:
    """A general DIAG path in the DC10 six-part form (base, namespace, cell, str(rep), window, rule)."""
    if isinstance(rep, bool) or not isinstance(rep, (int, str)):
        raise StopImplementation(f"rep must be int or str, got {rep!r}")
    ns, c, r, w, ru = validate_seed_parts((namespace, cell, str(rep), window, rule))
    return (ns, c, r, w, ru)


def seed_for(path: SeedPath, base: int = BASE_SEED) -> int:
    """derived_seed(base, namespace, cell, str(rep), window, rule): the DC10 six-part rule."""
    return derived_seed(base, *validate_seed_parts(path))


def explicit_seed(parts: Sequence[str], base: int = BASE_SEED) -> int:
    """A seed whose parts the contract states verbatim (S-A): derived_seed(base, *parts), nothing added."""
    return derived_seed(base, *validate_seed_parts(parts))


# Contract-stated seed parts (WORK_ORDER TEST_GATES N1-c; preregistration 6, 7). E1_CALIB keeps the literal "θ".
E1_CALIB_SEED_PARTS = ("FUTDIAG", "E1-θ0.7", "calib")
V4_EVAL_SEED_PARTS = ("FUTDIAG", "v4eval")
CASE_SERIES = ("iid", "ar1", "zero_inflated")
N2C_ROLES = ("data", "boot")          # data: the iid Normal draws; boot: the S1 / V0 index blocks


def case_id(series: str, n: int, mean_block: float) -> str:
    """N1-c / N2-a case string f"{series}-n{n}-b{int(mean_block)}"; mean_block must be a whole number."""
    if series not in CASE_SERIES:
        raise StopImplementation(f"unknown case series {series!r}")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise StopImplementation(f"n must be a positive int, got {n!r}")
    if not (mean_block >= 1 and float(mean_block).is_integer()):
        raise StopImplementation(f"mean_block must be a whole number >= 1, got {mean_block!r}")
    return f"{series}-n{n}-b{int(mean_block)}"


def n1c_seed_parts(series: str, n: int, mean_block: float) -> tuple[str, ...]:
    return ("FUTDIAG-TEST", "N1c", case_id(series, n, mean_block))


def n2a_seed_parts(kind: str, series: str, n: int) -> tuple[str, ...]:
    if kind not in ("data", "boot"):
        raise StopImplementation(f"N2-a seed kind must be data or boot, got {kind!r}")
    return ("FUTDIAG-TEST", f"N2a-{kind}", case_id(series, n, MEAN_BLOCK))


def n2c_seed_parts(n: int, rep: int, role: str) -> tuple[str, ...]:
    """("FUTDIAG-TEST", "N2c", f"n{n}", str(rep), role): the stated prefix "N2c" extended per length, rep and role."""
    if role not in N2C_ROLES:
        raise StopImplementation(f"N2-c role must be one of {N2C_ROLES}, got {role!r}")
    if isinstance(n, bool) or not isinstance(n, int) or isinstance(rep, bool) or not isinstance(rep, int) or rep < 0:
        raise StopImplementation("N2-c n and rep must be ints, rep >= 0")
    return ("FUTDIAG-TEST", "N2c", f"n{n}", str(rep), role)


def seed_collisions(paths: Iterable[SeedPath], external: Mapping[int, Sequence[str]] | None = None,
                    base: int = BASE_SEED) -> dict[str, object]:
    """Report-only check of 32-bit derived seed values (no reseeding). `external` maps seed values used elsewhere
    (e.g. MC-V06 rep / truth seeds) to a label. A collision is two DIFFERENT logical paths with the same value; the
    same path listed twice is reported separately as a duplicate. Returns counts, inputs and the sorted-list sha256."""
    listed = list(paths)
    seen: dict[SeedPath, int] = {}
    for p in listed:
        seen[p] = seen.get(p, 0) + 1
    duplicates = [{"path": list(p), "times": k} for p, k in sorted(seen.items()) if k > 1]
    by_value: dict[int, list[SeedPath]] = {}
    for p in seen:
        by_value.setdefault(seed_for(p, base), []).append(p)
    count_within = sum(len(ps) - 1 for ps in by_value.values() if len(ps) > 1)
    within = [{"seed": v, "paths": [list(p) for p in sorted(ps)]} for v, ps in sorted(by_value.items()) if len(ps) > 1]
    ext = external or {}
    cross = [{"seed": v, "paths": [list(p) for p in sorted(by_value[v])], "external": list(ext[v])}
             for v in sorted(by_value) if v in ext]
    values = sorted(by_value)
    digest = hashlib.sha256("\n".join(str(v) for v in values).encode("ascii")).hexdigest()
    return {"policy": "report_only", "count_within_diag": count_within,
            "count_vs_external": len(cross), "count_duplicate_paths": len(duplicates), "within": within,
            "vs_external": cross, "duplicates": duplicates, "n_paths": len(seen), "n_values": len(values),
            "sorted_list_sha256": digest}


# --- segment returns --------------------------------------------------------------------------------------------

def window_e0_returns(path: Path, sig: Sequence[int | None], g0: int, g1: int, cost: float) -> list[float]:
    """E0 net log returns of one strategy on segment [g0, g1) (draft 8.1 accounting, as in MC-V06)."""
    market, pos = segment_market_positions(path, sig, "E0", g0, g1)
    return segment_returns(market, pos, cost)


# --- F1 / F2: exact stationary-bootstrap variance of the mean (DC4, preregistration 5) ---------------------------

def _restart_prob(mean_block: float) -> float:
    return 1.0 / max(mean_block, 1.0)


def _centered(x: Sequence[float]) -> list[float]:
    m = mean(x)
    return [v - m for v in x]


def _circ_acov(d: Sequence[float], k: int) -> float:
    """C(k) = n^-1 sum_j d_j d_{(j+k) mod n} of an already centered series."""
    n = len(d)
    return sum(map(operator.mul, d, list(d[k:]) + list(d[:k]))) / n


def f1_lag_limit(n: int, mean_block: float) -> int:
    p = _restart_prob(mean_block)
    if p >= 1.0:
        return 0
    return min(n - 1, math.ceil(math.log(F1_TRUNCATION_EPS) / math.log(1.0 - p)))


def f1_variance(x: Sequence[float], mean_block: float, full: bool = False) -> float:
    """F1: Var*(m*) = n^-1 [C(0) + 2 sum_{k=1}^{K} (1 - k/n)(1-p)^k C(k)]; K = f1_lag_limit (or n - 1 if full)."""
    n = len(x)
    if n < 1:
        raise ValueError("empty series")
    p = _restart_prob(mean_block)
    d = _centered(x)
    total = _circ_acov(d, 0)
    if p < 1.0:
        lag_max = n - 1 if full else f1_lag_limit(n, mean_block)
        q = 1.0 - p
        for k in range(1, lag_max + 1):
            total += 2.0 * (1.0 - k / n) * q ** k * _circ_acov(d, k)
    return total / n


def f2_variance(x: Sequence[float], mean_block: float) -> float:
    """F2 (cross-check only): n^-1 [C(0) + sum_{k=1}^{n-1} b(k) C(k)], b(k) = (1-k/n)(1-p)^k + (k/n)(1-p)^(n-k)."""
    n = len(x)
    if n < 1:
        raise ValueError("empty series")
    q = 1.0 - _restart_prob(mean_block)
    d = _centered(x)
    total = _circ_acov(d, 0)
    for k in range(1, n):
        total += ((1.0 - k / n) * q ** k + (k / n) * q ** (n - k)) * _circ_acov(d, k)
    return total / n


def f1_truncation_bound(x: Sequence[float], mean_block: float) -> float:
    """Upper bound of |F1_K - F1_full|: 2 C(0) (1-p)^(K+1) / (n p); zero when p = 1."""
    n = len(x)
    p = _restart_prob(mean_block)
    if p >= 1.0:
        return 0.0
    c0 = _circ_acov(_centered(x), 0)
    return 2.0 * c0 * (1.0 - p) ** (f1_lag_limit(n, mean_block) + 1) / (n * p)


def variance_scale(x: Sequence[float]) -> float:
    """v0 = C(0)/n."""
    return _circ_acov(_centered(x), 0) / len(x)


def f1_effective(f1: float, v0: float) -> float:
    """Preregistration 5: clamp tiny negative F1 to 0, STOP below -1e-12 v0, exact zero required when v0 = 0."""
    finite_or_stop(f1, "F1")
    finite_or_stop(v0, "v0")
    if v0 == 0.0:
        if f1 != 0.0:
            raise StopImplementation(f"v0 = 0 but F1 = {f1!r}")
        return 0.0
    if f1 >= 0.0:
        return f1
    if f1 >= -F1_NEGATIVE_TOLERANCE_REL * v0:
        return 0.0
    raise StopImplementation(f"F1 = {f1!r} below -1e-12 * v0 = {-F1_NEGATIVE_TOLERANCE_REL * v0!r}")


# --- V0 family (DC2, DC3) ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class V0Result:
    m: float
    s: float
    delta_hat: float
    p_v0: float
    delta_true: float | None
    p_v0d: float | None
    boot_sd: float


def delta_true(theta: float, sigma_pop: float) -> float:
    return theta * sigma_pop / math.sqrt(ANNUALIZATION_DAYS)


def v0_family(r: Sequence[float], theta: float, mean_block: float, resamples: int, seed: int,
              sigma_pop: float | None = None) -> V0Result:
    """V0 (and V0d when sigma_pop is given) from ONE bootstrap_means call: futility_pvalue / futility_delta are
    called as-is (DC2). V0b60 is this function with mean_block = 60 and its own seed."""
    boot = bootstrap_means([r], mean_block=mean_block, resamples=resamples, seed=seed)[0]
    m = mean(r)
    dh = futility_delta(theta, r)
    dt = delta_true(theta, sigma_pop) if sigma_pop is not None else None
    return V0Result(m=m, s=sd(r), delta_hat=dh, p_v0=futility_pvalue(m, boot, dh), delta_true=dt,
                    p_v0d=futility_pvalue(m, boot, dt) if dt is not None else None, boot_sd=sd(boot))


# --- S1 bootstrap-t (DC4, DC4.1) --------------------------------------------------------------------------------

def resample_blocks(n: int, mean_block: float, resamples: int, seed: int) -> Iterator[list[tuple[int, int]]]:
    """The block lists bootstrap_means draws for the same (n, mean_block, resamples, seed): one random.Random(seed),
    one stats._blocks call per resample, nothing else consumes the generator."""
    rng = random.Random(seed)
    for _ in range(resamples):
        yield _blocks(n, mean_block, rng)


def c_l_factor(lengths: Sequence[int], n: int) -> float:
    """c_L = (1 - sum_j L_j^2 / n^2)^-1 for J_b >= 2 blocks covering n rows."""
    if len(lengths) < 2 or sum(lengths) != n:
        raise ValueError("c_L needs at least two blocks covering exactly n rows")
    return 1.0 / (1.0 - sum(length * length for length in lengths) / (n * n))


def resample_mean_and_se2(pre: _Prefix, n: int, blocks: Sequence[tuple[int, int]]) -> tuple[float, float | None]:
    """(m*_b, se*_b^2). se*^2 = c_L n^-2 sum_j (S*_j - L_j m*)^2; None if J_b < 2.
    m* accumulates block sums in the same order as bootstrap_means, so it is bit-identical to it."""
    sums = [pre.block(0, s, length) for s, length in blocks]
    total = 0.0
    for v in sums:
        total += v
    m_star = total / n
    if len(blocks) < 2:
        return m_star, None
    c_l = c_l_factor([length for _, length in blocks], n)
    ss = sum((v - length * m_star) ** 2 for v, (_, length) in zip(sums, blocks))
    return m_star, c_l * ss / (n * n)


def classify_resample(se2_star: float | None, se: float) -> tuple[bool, bool]:
    """(is_RD, is_ND) of one resample (DC4.1). RD: J_b < 2 (se2_star None) or se* <= 1e-6 se. ND: defined se* with
    se* < 0.25 se, so a tiny-se* RD resample is counted in both; J_b < 2 has no se* and is never ND."""
    if se2_star is None:
        return True, False
    se_star = math.sqrt(finite_or_stop(se2_star, "se*^2"))
    return se_star <= RD_REL * se, se_star < ND_REL * se


@dataclass(frozen=True)
class S1Result:
    p_hi: float               # PD-1: RD resamples counted as T* = -inf
    p_lo: float               # PD-2: RD resamples counted as T* = +inf
    d: int                    # RD resamples
    nd_share: float           # share of resamples with defined se* < 0.25 se
    nd_flag: bool
    se: float | None          # None when SD
    reason: str | None        # SD or None


def s1_from_blocks(r: Sequence[float], delta: float, mean_block: float, block_lists: Iterable[Sequence[tuple[int, int]]],
                   se_override: float | None = None) -> S1Result:
    """S1 partial studentization (DC4): T = (m - delta)/se, T*_b = (m*_b - m)/se*_b, left tail.
    se^2 = F1_effective(F1). se_override (the N1-d test hook) replaces every se*_b by se; T*_b <= T is then
    m*_b - m <= m - delta, evaluated with V0's own expression m*_b - m + delta <= m so the p-value is bit-identical."""
    n = len(r)
    m = mean(r)
    s = sd(r)
    se2 = f1_effective(f1_variance(r, mean_block), variance_scale(r))
    blocks_all = list(block_lists)
    b_total = len(blocks_all)
    if s == 0.0 or se2 == 0.0:
        return S1Result(p_hi=1.0, p_lo=1.0, d=0, nd_share=0.0, nd_flag=False, se=None, reason=SD)
    se = math.sqrt(se2)
    t_obs = (m - delta) / se
    pre = _Prefix(r)
    count = d = nd = 0
    for blocks in blocks_all:
        m_star, se2_star = resample_mean_and_se2(pre, n, blocks)
        if se_override is not None:
            if m_star - m + delta <= m:
                count += 1
            continue
        is_rd, is_nd = classify_resample(se2_star, se)
        nd += is_nd
        if is_rd:
            d += 1
            continue
        assert se2_star is not None
        if (m_star - m) / math.sqrt(se2_star) <= t_obs:
            count += 1
    p_lo = (1 + count) / (b_total + 1)
    p_hi = (1 + count + d) / (b_total + 1)
    share = nd / b_total if b_total else 0.0
    return S1Result(p_hi=p_hi, p_lo=p_lo, d=d, nd_share=share, nd_flag=share > ND_FLAG_SHARE, se=se, reason=None)


def s1_pvalue(r: Sequence[float], delta: float, mean_block: float, resamples: int, seed: int) -> S1Result:
    """S1 on the same index blocks as V0 (same seed and mean_block)."""
    return s1_from_blocks(r, delta, mean_block, resample_blocks(len(r), mean_block, resamples, seed))


# --- paired McNemar contrasts and labels (STATISTICAL_HYPOTHESES) ----------------------------------------------

@dataclass(frozen=True)
class Contrast:
    d_hat: float
    se: float
    p_one_sided: float
    upper: float              # U_D = D + z_{0.995} SE
    n10: int
    n01: int
    reason: str | None


def mcnemar(base: Sequence[bool], other: Sequence[bool]) -> Contrast:
    """D = r(base) - r(other) from paired rejection indicators; SE_D = sqrt((n10 + n01) - R D^2)/R, one-sided
    p = 1 - Phi(D/SE). With no discordant pair SE = 0: D = 0 and p is reported as 1 (reason NO_DISCORDANCE)."""
    if len(base) != len(other) or not base:
        raise ValueError("paired indicators must be non-empty and of equal length")
    big_r = len(base)
    n10 = sum(1 for a, b in zip(base, other) if a and not b)
    n01 = sum(1 for a, b in zip(base, other) if b and not a)
    d_hat = (n10 - n01) / big_r
    var = max((n10 + n01) - big_r * d_hat * d_hat, 0.0)
    se = math.sqrt(var) / big_r
    if se == 0.0:
        return Contrast(d_hat, 0.0, 1.0 if d_hat <= 0 else 0.0, d_hat, n10, n01, NO_DISCORDANCE)
    return Contrast(d_hat, se, 1.0 - _N.cdf(d_hat / se), d_hat + Z_WEAKENED * se, n10, n01, None)


def eff_threshold(r_reference: float) -> float:
    return max(MIN_EFFECT, 0.25 * (r_reference - PRIMARY_ALPHA))


def holm_rejections(pvalues: Mapping[str, float], fwer: float = SUPPORTED_FWER) -> dict[str, bool]:
    """Holm step-down at family-wise level fwer."""
    order = sorted(pvalues, key=lambda k: (pvalues[k], k))
    m = len(order)
    out = {k: False for k in pvalues}
    for i, k in enumerate(order):
        if pvalues[k] <= fwer / (m - i):
            out[k] = True
        else:
            break
    return out


SUPPORTED, WEAKENED, INCONCLUSIVE = "SUPPORTED", "WEAKENED", "INCONCLUSIVE"


def label_mcnemar(holm_rejected: bool, c: Contrast, eff: float, extra_ok: bool = True) -> str:
    """V-2 / V-3 / V-8: SUPPORTED = Holm rejection and D >= EFF (and V-8's extra condition); WEAKENED = U_D < 0.01."""
    if holm_rejected and c.d_hat >= eff and extra_ok:
        return SUPPORTED
    if c.upper < MIN_EFFECT:
        return WEAKENED
    return INCONCLUSIVE


DEGENERACY_AMBIGUOUS = "DEGENERACY_AMBIGUOUS"


def label_v1(holm_rejected_lo: bool, lo: Contrast, hi: Contrast, eff: float,
             holm_rejected_hi: bool) -> tuple[str, str | None]:
    """H-V1: SUPPORTED from D1_lo (Holm input p1 = lo.p_one_sided), WEAKENED from D1_hi. DEGENERACY_AMBIGUOUS is a
    report-only reason code: the opposite treatment would have given SUPPORTED or WEAKENED."""
    if holm_rejected_lo and lo.d_hat >= eff:
        label = SUPPORTED
    elif hi.upper < MIN_EFFECT:
        label = WEAKENED
    else:
        label = INCONCLUSIVE
    alt_supported = holm_rejected_hi and hi.d_hat >= eff
    alt_weakened = lo.upper < MIN_EFFECT
    ambiguous = (label != SUPPORTED and alt_supported) or (label != WEAKENED and alt_weakened)
    return label, DEGENERACY_AMBIGUOUS if ambiguous else None


# --- V-4 (H-V4, DC14) -------------------------------------------------------------------------------------------

def delta_rej(delta: float, sigma: float) -> float:
    """DeltaRej(Delta, sigma) = Phi(-z_{0.95} - Delta/sigma) - 0.05."""
    if not sigma > 0:
        raise ValueError("sigma must be > 0")
    return _N.cdf(-Z_ALPHA - delta / sigma) - PRIMARY_ALPHA


def rect_extrema(delta_lo: float, delta_hi: float, sigma_lo: float, sigma_hi: float) -> tuple[float, float]:
    """(min, max) of DeltaRej over [delta_lo, delta_hi] x [sigma_lo, sigma_hi]: attained at a corner."""
    vals = [delta_rej(dl, sg) for dl in (delta_lo, delta_hi) for sg in (sigma_lo, sigma_hi)]
    return min(vals), max(vals)


def v4_effect_gate(delta_hat: float, sigma_lo: float, sigma_hi: float) -> float:
    """min over sigma in [sigma_lo, sigma_hi] of DeltaRej(delta_hat, sigma) (monotone in sigma -> an endpoint)."""
    return min(delta_rej(delta_hat, sigma_lo), delta_rej(delta_hat, sigma_hi))


def v4_weakened_max(delta_lower: float, sigma_lo: float, sigma_hi: float) -> float:
    """DeltaRej_max over {L_Delta} x {sigma_L, sigma_U}."""
    return max(delta_rej(delta_lower, sigma_lo), delta_rej(delta_lower, sigma_hi))


def v4_approx_ok(delta_hat: float, sigma_lo: float) -> bool:
    return abs(delta_hat) / sigma_lo <= V4_APPROX_MAX


def split_batches(x: Sequence[float], k: int) -> list[list[float]]:
    """k contiguous batches; the first len(x) % k batches are one element longer."""
    if k < 2 or len(x) < k:
        raise ValueError("need k >= 2 and len(x) >= k")
    size, extra = divmod(len(x), k)
    out, i = [], 0
    for j in range(k):
        step = size + (1 if j < extra else 0)
        out.append(list(x[i:i + step]))
        i += step
    return out


def batch_sharpes(returns: Sequence[float], k: int = V4_BATCHES) -> tuple[list[float], list[int]]:
    """Unweighted per-batch annual Sharpe ratios and the actual batch lengths (for the record)."""
    batches = split_batches(returns, k)
    return [annual_sharpe(b) for b in batches], [len(b) for b in batches]


def batch_means_se(batch_values: Sequence[float]) -> float:
    """sd(batch values, ddof = 1) / sqrt(K)."""
    return sd(batch_values) / math.sqrt(len(batch_values))


def sigma_interval(values: Sequence[float], z: float = Z_SIGMA) -> tuple[float, float, float, float]:
    """(sigma_hat, kappa_hat, sigma_L, sigma_U): sample sd (ddof 1), moment kurtosis m4/m2^2, and
    exp(log sigma_hat -/+ z sqrt((kappa - 1)/(4R)))."""
    big_r = len(values)
    if big_r < 2:
        raise ValueError("need at least two values")
    d = _centered(values)
    m2 = sum(v * v for v in d) / big_r
    m4 = sum(v ** 4 for v in d) / big_r
    if not m2 > 0:
        raise StopImplementation("sigma calibration has zero variance")
    kappa = m4 / (m2 * m2)
    s_hat = sd(values)
    half = z * math.sqrt(max(kappa - 1.0, 0.0) / (4 * big_r))
    return s_hat, kappa, s_hat * math.exp(-half), s_hat * math.exp(half)


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction of the regularized incomplete beta function (modified Lentz)."""
    tiny, eps = 1e-300, 1e-15
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, dd = 1.0, 1.0 - qab * x / qap
    dd = 1.0 / (dd if abs(dd) > tiny else tiny)
    h = dd
    for m in range(1, 1000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        dd = 1.0 + aa * dd
        dd = 1.0 / (dd if abs(dd) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= dd * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        dd = 1.0 + aa * dd
        dd = 1.0 / (dd if abs(dd) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = dd * c
        h *= delta
        if abs(delta - 1.0) < eps:
            return h
    raise StopImplementation("incomplete beta continued fraction did not converge")


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(t: float, df: int) -> float:
    """Student t CDF via the regularized incomplete beta function."""
    tail = 0.5 * _betai(df / 2.0, 0.5, df / (df + t * t))
    return 1.0 - tail if t > 0 else tail


def t_ppf(q: float, df: int) -> float:
    if not 0.0 < q < 1.0:
        raise ValueError("q must be in (0, 1)")
    lo, hi = -1e3, 1e3
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < q:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


@dataclass(frozen=True)
class V4Inference:
    delta_hat: float
    se: float
    p_one_sided: float        # H0: Delta >= 0
    delta_lower: float        # L_Delta (one-sided, gamma_delta)
    delta_upper: float        # U_Delta (descriptive only)


def v4_inference(sr_eval: float, theta: float, batch_values: Sequence[float]) -> V4Inference:
    """Delta = SR_eval - theta with batch-means SE and t(K-1)."""
    k = len(batch_values)
    se = batch_means_se(batch_values)
    if not se > 0:
        raise StopImplementation("batch-means SE is zero")
    dh = sr_eval - theta
    tq = t_ppf(1 - V4_GAMMA_DELTA, k - 1)
    return V4Inference(dh, se, t_cdf(dh / se, k - 1), dh - tq * se, dh + tq * se)


# --- pilot R_c (DC12) -------------------------------------------------------------------------------------------

def _binom_cdf(x: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if x >= n else 0.0
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(x + 1))


def clopper_pearson_upper(x: int, n: int, conf: float = 0.95) -> float:
    """One-sided upper bound: the p with P(X <= x | n, p) = 1 - conf (1 if x = n)."""
    if not 0 <= x <= n:
        raise ValueError("need 0 <= x <= n")
    if x == n:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _binom_cdf(x, n, mid) > 1 - conf:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def required_reps(pi_upper: float) -> tuple[int, bool]:
    """R_c = round up to 1,000 of max(10,000, ceil((z_{0.995}+z_{0.80})^2 pi_U / 0.01^2), ceil(pi_U / 0.0035^2));
    second value True when R_c > CORE_R_MAX (STOP)."""
    r = max(R_MIN, math.ceil((Z_HOLM_WORST + Z_POWER) ** 2 * pi_upper / MIN_EFFECT ** 2),
            math.ceil(pi_upper / TARGET_MAX_MC_SE_PAIRED ** 2))
    r = math.ceil(r / R_ROUND) * R_ROUND
    return r, r > R_MAX


# --- run_spec.json: what is fixed before a run starts (G3b-1 MANIFEST-SPLIT) ------------------------------------

RUN_SPEC_SCHEMA = "moneylab.bt4_futility_diag.run_spec/1"
STUDY_ID = "BT4-FUTILITY-01-DIAG"
RUN_MODES = ("pilot", "core", "exploratory")
CORE_CELLS = ("E1-theta0.7", "P0-theta0.7")
EXPLORATORY_CELLS = ("P1-theta0.7", "P2-theta0.7", "E2-theta0.7", "E1-theta0.3", "P0-theta0.3", "E1-int",
                     "E1-theta0.7-holdout914")
WINDOWS = ("conf", "f12", "f24", "f36")
RULES = ("b20", "b60")
RUN_SPEC_FIELDS = ("schema_version", "study_id", "mode", "code_sha", "code_tree", "config_sha256",
                   "prereg_sha256", "seed_policy", "base_seed", "cells", "windows", "rules", "reps", "bootstrap",
                   "unit_size")
# never in run_spec: they depend on when / where / how the run executes, or on its results
RUN_SPEC_FORBIDDEN = ("started_utc", "finished_utc", "workers", "elapsed", "timings", "unit_sha256", "units",
                      "results", "eta_hat", "host")
_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")


PATH_WINDOW, PATH_RULE = "all", "path"     # ERRATA-002 SEED_STRINGS: one DGP path per (namespace, cell, rep)
SIGMA_NAMESPACE, SIGMA_CELL = "FUTDIAG-SIGMA", "E1-ecal"   # ERRATA-002: new fixed string for the e_cal DGP path


def seed_policy() -> dict[str, object]:
    return {"rule": "S-A", "algorithm": "moneylab.research.stats.derived_seed",
            "general": "derived_seed(base, namespace, cell, str(rep), window, rule)",
            "namespaces": list(NAMESPACES), "forbidden_namespaces": list(FORBIDDEN_NAMESPACES),
            "explicit": {"N1c": ["FUTDIAG-TEST", "N1c", "<case>"], "N2a-data": ["FUTDIAG-TEST", "N2a-data", "<case>"],
                         "N2a-boot": ["FUTDIAG-TEST", "N2a-boot", "<case>"],
                         "N2c": ["FUTDIAG-TEST", "N2c", "n<n>", "<rep>", "<role>"],
                         "E1-calib": list(E1_CALIB_SEED_PARTS), "V4-eval": list(V4_EVAL_SEED_PARTS)},
            "case": "{series}-n{n}-b{int(mean_block)}", "n2c_roles": list(N2C_ROLES),
            "general_strings": {"path": ["<namespace>", "<cell>", "<rep>", PATH_WINDOW, PATH_RULE],
                                "bootstrap": ["<namespace>", "<cell>", "<rep>", "<window>", "<rule>"],
                                "windows": list(WINDOWS), "rules": list(RULES),
                                "shared_b20": ["V0", "V0d", "S1"], "separate_b60": ["V0b60"],
                                "sigma": [SIGMA_NAMESPACE, SIGMA_CELL, "<rep>", PATH_WINDOW, PATH_RULE]},
            "part_rules": ["str only", "no '|'", "first part is a DC10 namespace"],
            "collisions": "report_only, no reseeding"}


def build_run_spec(*, mode: str, code_sha: str, code_tree: str, config_sha256: str, prereg_sha256: str,
                   cells: Sequence[str], windows: Sequence[str], rules: Sequence[str], reps: int, bootstrap: int,
                   unit_size: int) -> dict[str, object]:
    spec: dict[str, object] = {
        "schema_version": RUN_SPEC_SCHEMA, "study_id": STUDY_ID, "mode": mode, "code_sha": code_sha,
        "code_tree": code_tree, "config_sha256": config_sha256, "prereg_sha256": prereg_sha256,
        "seed_policy": seed_policy(), "base_seed": BASE_SEED, "cells": list(cells), "windows": list(windows),
        "rules": list(rules), "reps": reps, "bootstrap": bootstrap, "unit_size": unit_size}
    validate_run_spec(spec)
    return spec


def _positive_int(x: object) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x > 0


def validate_run_spec(spec: Mapping[str, object]) -> None:
    """Exactly RUN_SPEC_FIELDS, typed and in range; nothing run-time or result-dependent (STOP otherwise)."""
    keys = set(spec)
    missing = [k for k in RUN_SPEC_FIELDS if k not in keys]
    extra = sorted(keys - set(RUN_SPEC_FIELDS))
    if missing or extra:
        raise StopImplementation(f"run_spec fields: missing {missing}, unexpected {extra}")
    errors = []
    if spec["schema_version"] != RUN_SPEC_SCHEMA:
        errors.append("schema_version")
    if spec["study_id"] != STUDY_ID:
        errors.append("study_id")
    if spec["mode"] not in RUN_MODES:
        errors.append("mode")
    for k, rx in (("code_sha", _HEX40), ("code_tree", _HEX40), ("config_sha256", _HEX64), ("prereg_sha256", _HEX64)):
        v = spec[k]
        if not (isinstance(v, str) and rx.fullmatch(v)):
            errors.append(k)
    if spec["seed_policy"] != seed_policy():
        errors.append("seed_policy")
    if spec["base_seed"] != BASE_SEED:
        errors.append("base_seed")
    allowed_cells = CORE_CELLS if spec["mode"] in ("pilot", "core") else EXPLORATORY_CELLS
    for k, allowed in (("cells", allowed_cells), ("windows", WINDOWS), ("rules", RULES)):
        v = spec[k]
        if not (isinstance(v, list) and v and len(set(v)) == len(v) and all(x in allowed for x in v)):
            errors.append(k)
    for k in ("reps", "bootstrap", "unit_size"):
        if not _positive_int(spec[k]):
            errors.append(k)
    if errors:
        raise StopImplementation(f"invalid run_spec fields: {errors}")


def canonical_bytes(payload: object) -> bytes:
    """Deterministic JSON (sorted keys, no whitespace, no NaN) plus a newline, as MC-V06 writes its artifacts."""
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            + "\n").encode("utf-8")


def run_spec_bytes(spec: Mapping[str, object]) -> bytes:
    validate_run_spec(spec)
    return canonical_bytes(dict(spec))


# --- G3b-3: deterministic replication engine (DC6, DC7, DC10, DC11, ERRATA-002) ---------------------------------

CORE_THETA = 0.7
ENGINE_NAMESPACES = ("FUTDIAG", "FUTDIAG-PILOT", "FUTDIAG-TEST")    # CORE main run, pilot, offline tests
E1_DGP = DGP(garch_alpha=0.0, garch_beta=0.0, t_df=None, edge_kind="momentum", edge_lookback=60)   # DC6 normal_M60
E1_STRATEGY = "M60"
P0_DAILY_SD = 0.70 / math.sqrt(ANNUALIZATION_DAYS)                  # DC6; also P0's analytic sigma_pop
WINDOW_BOUNDS_KEYS = {"conf": "confirmatory", "f12": "forward_12m", "f24": "forward_24m", "f36": "forward_36m"}
VARIANTS = ("V0", "V0d", "V0b60", "S1")
RECORD_ID_FIELDS = ("cell", "rep", "window")
RECORD_STAT_FIELDS = ("m", "s", "delta_hat", "delta_true", "annual_sharpe", "variants", "sd", "boot_sd_b20",
                      "boot_sd_b60")
RECORD_FIELDS = RECORD_ID_FIELDS + RECORD_STAT_FIELDS
S1_FIELDS = ("p_hi", "p_lo", "d", "nd_share", "nd_flag", "se", "se_reason")
V0_FAMILY_FIELDS = ("p", "se", "se_reason")


def window_bounds() -> dict[str, tuple[int, int]]:
    """DC7 windows from MC-V06 Layout / SimulationCalendar defaults (E and P cells alike)."""
    b = Layout().bounds(SimulationCalendar())
    return {w: b[k] for w, k in WINDOW_BOUNDS_KEYS.items()}


def path_days() -> int:
    """DC7: every cell uses the MC-V06 total_days."""
    return Layout().total_days(SimulationCalendar())


SIGMA_NAMESPACES = (SIGMA_NAMESPACE, "FUTDIAG-TEST")     # research; G4c smoke and tests (ERRATA-003 R-7)


def sigma_seed_path(rep: int, namespace: str = SIGMA_NAMESPACE) -> SeedPath:
    """sigma calibration path seed (ERRATA-002): (FUTDIAG-SIGMA, E1-ecal, str(rep), all, path), no bootstrap. The
    smoke run uses the same strings in FUTDIAG-TEST (ERRATA-003 R-7)."""
    if namespace not in SIGMA_NAMESPACES:
        raise StopImplementation(f"sigma calibration namespace must be one of {SIGMA_NAMESPACES}, got {namespace!r}")
    return seed_path(namespace, SIGMA_CELL, rep, PATH_WINDOW, PATH_RULE)


@dataclass(frozen=True)
class CellSpec:
    """One CORE cell (DC6). E1: edge_annual and sigma_pop come from its 4,000-year calibration path (computed once,
    outside this engine). P0: no edge, sigma_pop is the analytic daily sd (ERRATA-002 P0_COST)."""
    name: str
    theta: float
    edge_annual: float | None = None
    sigma_pop: float | None = None


def e1_cell(edge_annual: float, sigma_pop: float) -> CellSpec:
    return CellSpec("E1-theta0.7", CORE_THETA, edge_annual, sigma_pop)


def p0_cell() -> CellSpec:
    return CellSpec("P0-theta0.7", CORE_THETA, None, P0_DAILY_SD)


def check_cell(cell: CellSpec) -> None:
    if cell.name not in CORE_CELLS:
        raise StopImplementation(f"not a CORE cell: {cell.name!r}")
    if cell.theta != CORE_THETA:
        raise StopImplementation(f"{cell.name} needs theta {CORE_THETA}, got {cell.theta!r}")
    if cell.name.startswith("E1"):
        if cell.edge_annual is None or cell.sigma_pop is None:
            raise StopImplementation("E1 needs its calibrated edge_annual and sigma_pop")
        finite_or_stop(cell.edge_annual, "edge_annual")
        if not finite_or_stop(cell.sigma_pop, "sigma_pop") > 0:
            raise StopImplementation("E1 sigma_pop must be > 0")
    elif cell.edge_annual is not None or cell.sigma_pop != P0_DAILY_SD:
        raise StopImplementation("P0 has no edge and the analytic sigma_pop 0.70/sqrt(365)")


def p0_daily_returns(days: int, seed: int, theta: float) -> list[float]:
    """P0 (DC6, ERRATA-002 P0_COST): iid Normal, sd 0.70/sqrt(365), mean theta sd/sqrt(365), used as generated.
    Constant exposure 1, no strategy, no positions, no cost; the population annual Sharpe is exactly theta."""
    rng = random.Random(seed)
    mu = theta * P0_DAILY_SD / math.sqrt(ANNUALIZATION_DAYS)
    return [mu + P0_DAILY_SD * rng.gauss(0.0, 1.0) for _ in range(days)]


def e1_window_returns(edge_annual: float, seed: int, windows: Sequence[str] = WINDOWS) -> dict[str, list[float]]:
    """M60 E0 net log returns with the MC-V06 default costs (DC1) on every window of ONE normal_M60 path with this
    edge: the E1 cell and the sigma calibration's e_cal DGP."""
    bounds = window_bounds()
    path = make_path(replace(E1_DGP, edge_annual=edge_annual), path_days(), seed)
    sig = signals(path.log_close, *STRATEGIES[E1_STRATEGY])
    cost = Costs().log_costs()["E0"]
    return {w: window_e0_returns(path, sig, *bounds[w], cost) for w in windows}


def cell_window_returns(cell: CellSpec, seed: int, windows: Sequence[str] = WINDOWS) -> dict[str, list[float]]:
    """The returns of every window, cut from ONE path generated from the (all, path) seed.
    E1: e1_window_returns. P0: the generated values on [g0, g1)."""
    bounds = window_bounds()
    if cell.name.startswith("E1"):
        assert cell.edge_annual is not None                                    # check_cell
        return e1_window_returns(cell.edge_annual, seed, windows)
    daily = p0_daily_returns(path_days(), seed, cell.theta)
    return {w: daily[bounds[w][0]:bounds[w][1]] for w in windows}


def rep_seed_paths(namespace: str, cell: str, rep: int, windows: Sequence[str] = WINDOWS) -> dict[str, SeedPath]:
    """ERRATA-002 SEED_STRINGS for one replication: "path" -> (ns, cell, rep, all, path); "<window>/<rule>" ->
    (ns, cell, rep, window, b20 | b60). b20 is shared by V0, V0d and S1; b60 is V0b60's own."""
    out = {PATH_RULE: seed_path(namespace, cell, rep, PATH_WINDOW, PATH_RULE)}
    for w in windows:
        for rule in RULES:
            out[f"{w}/{rule}"] = seed_path(namespace, cell, rep, w, rule)
    return out


def _na_variant(p: float) -> dict[str, object]:
    return {"p": p, "se": None, "se_reason": NOT_APPLICABLE}


def window_record(cell: CellSpec, rep: int, window: str, r: Sequence[float], seed_b20: int, seed_b60: int,
                  bootstrap: int) -> dict[str, object]:
    """DC11 record of one (cell, rep, window). V0, V0d and S1 use the b20 block sequence; V0b60 its own b60 one.
    S1's se is sqrt(F1_effective) (0 under SD, where p_S1 = 1); V0-family se is null / NOT_APPLICABLE
    (ERRATA-002 SE_FIELDS). boot_sd_* is the sd (B - 1) of that rule's B resample means (BOOTSTRAP_SD)."""
    v0 = v0_family(r, cell.theta, MEAN_BLOCK, bootstrap, seed_b20, sigma_pop=cell.sigma_pop)
    s1 = s1_pvalue(r, v0.delta_hat, MEAN_BLOCK, bootstrap, seed_b20)
    v60 = v0_family(r, cell.theta, MEAN_BLOCK_V3, bootstrap, seed_b60)
    assert v0.delta_true is not None and v0.p_v0d is not None
    se_s1 = s1.se if s1.se is not None else math.sqrt(f1_effective(f1_variance(r, MEAN_BLOCK), variance_scale(r)))
    for name, x in (("m", v0.m), ("s", v0.s), ("delta_hat", v0.delta_hat), ("S1 se", se_s1),
                    ("boot_sd_b20", v0.boot_sd), ("boot_sd_b60", v60.boot_sd)):
        finite_or_stop(x, name)
    s1_rec = {"p_hi": s1.p_hi, "p_lo": s1.p_lo, "d": s1.d, "nd_share": s1.nd_share, "nd_flag": s1.nd_flag,
              "se": se_s1, "se_reason": None}
    return {"cell": cell.name, "rep": rep, "window": window,
            "m": v0.m, "s": v0.s, "delta_hat": v0.delta_hat, "delta_true": v0.delta_true,
            "annual_sharpe": annual_sharpe(r),
            "variants": {"V0": _na_variant(v0.p_v0), "V0d": _na_variant(v0.p_v0d), "V0b60": _na_variant(v60.p_v0),
                         "S1": s1_rec},
            "sd": s1.reason == SD, "boot_sd_b20": v0.boot_sd, "boot_sd_b60": v60.boot_sd}


def _check_windows(windows: Sequence[str]) -> None:
    if not windows or list(windows) != [w for w in WINDOWS if w in windows] or len(set(windows)) != len(windows):
        raise StopImplementation(f"windows must be a non-empty ordered subset of {WINDOWS}, got {windows!r}")


def rep_records(cell: CellSpec, rep: int, namespace: str, bootstrap: int,
                windows: Sequence[str] = WINDOWS) -> list[dict[str, object]]:
    """All window records of one replication, in WINDOWS order, from one path."""
    seeds = {k: seed_for(p) for k, p in rep_seed_paths(namespace, cell.name, rep, windows).items()}
    rets = cell_window_returns(cell, seeds[PATH_RULE], windows)
    return [window_record(cell, rep, w, rets[w], seeds[f"{w}/b20"], seeds[f"{w}/b60"], bootstrap) for w in windows]


_clock: Callable[[], float] = time.perf_counter      # ERRATA-003 R-1, R-2, R-4 clock; tests inject a fake one


def _rep_task(args: tuple[CellSpec, int, str, int, tuple[str, ...]]) -> tuple[list[dict[str, object]], float]:
    """One replication's records and its compute-only time (ERRATA-003 R-1: path, every window and variant, the
    records), measured by the process that computes it. The time is never part of a record."""
    t0 = _clock()
    records = rep_records(*args)
    return records, _clock() - t0


def run_reps(cell: CellSpec, reps: Sequence[int], namespace: str, bootstrap: int,
             windows: Sequence[str] = WINDOWS, workers: int = 1) -> list[dict[str, object]]:
    """Records of the given replications, ordered by (rep, window). A record depends only on its seeds, so the
    output does not depend on the worker count (ordered map, nothing shared between replications)."""
    return run_reps_timed(cell, reps, namespace, bootstrap, windows, workers)[0]


def run_reps_timed(cell: CellSpec, reps: Sequence[int], namespace: str, bootstrap: int,
                   windows: Sequence[str] = WINDOWS,
                   workers: int = 1) -> tuple[list[dict[str, object]], list[float]]:
    """run_reps plus the per-replication compute times (same order as reps)."""
    check_cell(cell)
    if namespace not in ENGINE_NAMESPACES:
        raise StopImplementation(f"engine namespace must be one of {ENGINE_NAMESPACES}, got {namespace!r}")
    _check_windows(windows)
    if not _positive_int(bootstrap):
        raise StopImplementation(f"bootstrap must be a positive int, got {bootstrap!r}")
    if not _positive_int(workers):
        raise StopImplementation(f"workers must be a positive int, got {workers!r}")
    reps = list(reps)
    if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in reps) or reps != sorted(set(reps)):
        raise StopImplementation("reps must be strictly increasing ints >= 0")
    tasks = [(cell, i, namespace, bootstrap, tuple(windows)) for i in reps]
    if workers == 1:
        done = [_rep_task(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            done = list(pool.map(_rep_task, tasks))
    return [rec for chunk, _ in done for rec in chunk], [seconds for _, seconds in done]


def records_bytes(records: Iterable[Mapping[str, object]]) -> bytes:
    """JSON Lines in canonical form (sorted keys, no NaN): the byte-identity check across worker counts."""
    return b"".join(canonical_bytes(dict(rec)) for rec in records)


# --- G3b-4: storage, resume and integrity (DC11, REPRODUCIBILITY_REQUIREMENTS, STOP_CONDITIONS) -----------------
#
# <run_dir>/run_spec.json              before any unit; never changed (resume: byte comparison)
# <run_dir>/run_inputs.json            before any unit; never changed (resume: byte comparison)
# <run_dir>/units/<cell>/uNNNNN.jsonl  one unit = (cell, reps [start, stop)), records in (rep, window) order
# <run_dir>/units/<cell>/uNNNNN.index.json   written after its jsonl: the unit's completion marker
# <run_dir>/manifest.json              after every unit is complete
# <run_dir>/execution.json             sessions (time, workers, platform): the only non-deterministic file
# <run_dir>/SHA256SUMS                 every file except execution.json, itself and g6/
# <run_dir>/g6/                        pilot only, after the run is complete (G3b-5-2, G1 layout): own SHA256SUMS
# Every write goes through storage.atomic. Nothing is deleted or overwritten: a leftover *.tmp is reported, a
# damaged complete unit or any mismatch is a STOP (no automatic repair).

RUN_SPEC_FILE, RUN_INPUTS_FILE = "run_spec.json", "run_inputs.json"
MANIFEST_FILE, EXECUTION_FILE, SUMS_FILE, UNITS_DIR = "manifest.json", "execution.json", "SHA256SUMS", "units"
RUN_INPUTS_SCHEMA = "moneylab.bt4_futility_diag.run_inputs/1"
UNIT_INDEX_SCHEMA = "moneylab.bt4_futility_diag.unit_index/1"
MANIFEST_SCHEMA = "moneylab.bt4_futility_diag.manifest/1"
EXECUTION_SCHEMA = "moneylab.bt4_futility_diag.execution/2"     # /2: session start, unit and end records
TEST_FIXTURE = "TEST_FIXTURE"
# (mode, namespace): pilot and CORE main run (preregistration 7, ERRATA-002); FUTDIAG-TEST is test-only (DC10)
MODE_NAMESPACES = (("pilot", "FUTDIAG-PILOT"), ("core", "FUTDIAG"), ("pilot", "FUTDIAG-TEST"),
                   ("core", "FUTDIAG-TEST"))
RUN_INPUTS_FIELDS = ("schema_version", "evidence", "namespace", "cells", "python", "futility_diag_source",
                     "mcv06_source_identity", "calibration_provenance")
CELL_INPUT_FIELDS = ("theta", "edge_annual", "sigma_pop")
# WORK_ORDER REPRODUCIBILITY_REQUIREMENTS items a research manifest needs and only calibration (G3b-5) provides
MANIFEST_PENDING = ("e_cal and SR_ach (source)", "calibrated edge and achieved SR", "sigma_pop of the calibration path",
                    "sigma_hat, kappa_hat, sigma_L, sigma_U", "R_c inputs", "A1-c seed collision report")
_UNIT_FILE = re.compile(r"u(\d{5})\.(jsonl|index\.json)")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unit_ranges(reps: int, unit_size: int) -> list[tuple[int, int, int]]:
    """(unit, rep_start, rep_stop) covering reps 0 .. reps - 1 in blocks of unit_size (the last may be shorter)."""
    if not (_positive_int(reps) and _positive_int(unit_size)):
        raise StopImplementation(f"reps and unit_size must be positive ints, got {reps!r}, {unit_size!r}")
    return [(k, start, min(start + unit_size, reps)) for k, start in enumerate(range(0, reps, unit_size))]


def unit_paths(run_dir: FsPath, cell: str, unit: int) -> tuple[FsPath, FsPath]:
    base = FsPath(run_dir) / UNITS_DIR / cell
    return base / f"u{unit:05d}.jsonl", base / f"u{unit:05d}.index.json"


def module_source() -> dict[str, str]:
    """SHA-256 of this module's working-tree bytes and with CRLF normalized to LF (as montecarlo.source_identity)."""
    raw = FsPath(__file__).read_bytes()
    return {"sha256": _sha256(raw), "sha256_lf": _sha256(raw.replace(b"\r\n", b"\n"))}


def build_run_inputs(spec: Mapping[str, object], cells: Sequence[CellSpec], namespace: str,
                     calibration_provenance: Mapping[str, object]) -> dict[str, Any]:
    """What a run depends on besides run_spec: the cell inputs, namespace, Python and source identity, and where
    the calibration values came from. Unit runs take TEST_FIXTURE provenance only until the research manifest
    exists; research provenance comes from calibration_provenance (G3b-5-1)."""
    inputs: dict[str, Any] = {
        "schema_version": RUN_INPUTS_SCHEMA, "evidence": EVIDENCE, "namespace": namespace,
        "cells": {c.name: {"theta": c.theta, "edge_annual": c.edge_annual, "sigma_pop": c.sigma_pop} for c in cells},
        "python": platform.python_version(), "futility_diag_source": module_source(),
        "mcv06_source_identity": source_identity(), "calibration_provenance": dict(calibration_provenance)}
    validate_run_inputs(inputs, spec)
    return inputs


def validate_run_inputs(inputs: Mapping[str, Any], spec: Mapping[str, object]) -> None:
    keys = set(inputs)
    if keys != set(RUN_INPUTS_FIELDS):
        raise StopImplementation(f"run_inputs fields: missing {sorted(set(RUN_INPUTS_FIELDS) - keys)}, "
                                 f"unexpected {sorted(keys - set(RUN_INPUTS_FIELDS))}")
    if inputs["schema_version"] != RUN_INPUTS_SCHEMA or inputs["evidence"] != EVIDENCE:
        raise StopImplementation("run_inputs schema_version / evidence")
    if (spec["mode"], inputs["namespace"]) not in MODE_NAMESPACES:
        raise StopImplementation(f"mode {spec['mode']!r} cannot run in namespace {inputs['namespace']!r}")
    cells = inputs["cells"]
    if not isinstance(cells, dict) or list(cells) != spec["cells"]:
        raise StopImplementation("run_inputs cells must be the run_spec cells, in order")
    for name, c in cells.items():
        if not isinstance(c, dict) or set(c) != set(CELL_INPUT_FIELDS):
            raise StopImplementation(f"run_inputs cell {name!r} fields")
        check_cell(CellSpec(name, c["theta"], c["edge_annual"], c["sigma_pop"]))
    prov = inputs["calibration_provenance"]
    kind = prov.get("kind") if isinstance(prov, dict) else None
    if kind == TEST_FIXTURE:
        if inputs["namespace"] != "FUTDIAG-TEST":
            raise StopImplementation("TEST_FIXTURE inputs run only in the FUTDIAG-TEST namespace")
        return
    if kind != RESEARCH:
        raise StopImplementation("calibration_provenance kind must be TEST_FIXTURE or RESEARCH")
    e1 = cells.get(E1_CELL)
    if not (set(prov) == set(CAL_PROVENANCE_FIELDS) and _HEX64.fullmatch(str(prov["calibration_sha256"]))
            and RESEARCH_NAMESPACES.get(str(spec["mode"])) == inputs["namespace"]
            and (e1 is None or (e1["edge_annual"], e1["sigma_pop"]) == (prov["edge_annual"], prov["sigma_pop"]))):
        raise StopImplementation("RESEARCH run_inputs: provenance fields, namespace FUTDIAG-PILOT (pilot) / FUTDIAG "
                                 "(core) and the E1 cell of that calibration")


def cells_from_inputs(inputs: Mapping[str, Any]) -> list[CellSpec]:
    return [CellSpec(name, c["theta"], c["edge_annual"], c["sigma_pop"]) for name, c in inputs["cells"].items()]


def _write_or_compare(path: FsPath, data: bytes, what: str) -> str:
    """Write data atomically if path is absent; otherwise the existing bytes must be identical (never overwrite)."""
    if path.exists():
        if path.read_bytes() != data:
            raise StopImplementation(f"{what} differs from the existing {path.name}: refusing to change it")
        return "same"
    atomic_write_bytes(path, data)
    return "written"


def init_run(run_dir: FsPath, spec: Mapping[str, object], inputs: Mapping[str, Any]) -> str:
    """Create run_spec.json then run_inputs.json in an empty or new run_dir, or check both byte for byte."""
    validate_run_spec(spec)
    validate_run_inputs(inputs, spec)
    run_dir = FsPath(run_dir)
    spec_path, inputs_path = run_dir / RUN_SPEC_FILE, run_dir / RUN_INPUTS_FILE
    files = [p for p in run_dir.rglob("*") if p.is_file() and not p.name.endswith(TMP_SUFFIX)] \
        if run_dir.exists() else []
    if files and not spec_path.exists():
        raise StopImplementation(f"{run_dir} has files but no {RUN_SPEC_FILE}")
    if not spec_path.exists() and inputs_path.exists():
        raise StopImplementation(f"{RUN_INPUTS_FILE} without {RUN_SPEC_FILE}")
    new = not spec_path.exists()
    _write_or_compare(spec_path, run_spec_bytes(spec), "run_spec")
    if not inputs_path.exists() and (run_dir / UNITS_DIR).exists():
        raise StopImplementation(f"units exist but {RUN_INPUTS_FILE} is missing")
    _write_or_compare(inputs_path, canonical_bytes(dict(inputs)), "run_inputs")
    return "created" if new else "resumed"


def _expected_units(spec: Mapping[str, Any]) -> list[tuple[str, int, int, int]]:
    return [(cell, k, s, e) for cell in spec["cells"] for k, s, e in unit_ranges(spec["reps"], spec["unit_size"])]


def scan_run_dir(run_dir: FsPath, spec: Mapping[str, Any]) -> dict[str, Any]:
    """Classify every file under run_dir (read-only): known top-level files, expected unit files, leftover *.tmp
    (reported, never deleted) and anything else (unexpected: the caller STOPs)."""
    run_dir = FsPath(run_dir)
    top = {RUN_SPEC_FILE, RUN_INPUTS_FILE, MANIFEST_FILE, EXECUTION_FILE, SUMS_FILE}
    expected = {(cell, k) for cell, k, _, _ in _expected_units(spec)}
    tmp, unexpected, present = [], [], set()
    for p in sorted(run_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(run_dir).as_posix()
        parts = rel.split("/")
        if p.name.endswith(TMP_SUFFIX):
            tmp.append(rel)
            continue
        if (len(parts) == 1 and rel in top) or (len(parts) == 2 and parts[0] == G6_DIR and parts[1] in G6_FILES):
            present.add(rel)
            continue
        m = _UNIT_FILE.fullmatch(parts[-1]) if len(parts) == 3 and parts[0] == UNITS_DIR else None
        if m and (parts[1], int(m.group(1))) in expected:
            present.add(rel)
            continue
        unexpected.append(rel)
    return {"present": sorted(present), "tmp": tmp, "unexpected": unexpected}


def _unit_index(spec: Mapping[str, Any], cell: str, unit: int, start: int, stop: int, n_records: int,
                jsonl_sha256: str, spec_sha256: str, inputs_sha256: str) -> dict[str, Any]:
    return {"schema_version": UNIT_INDEX_SCHEMA, "cell": cell, "unit": unit, "rep_start": start, "rep_stop": stop,
            "windows": list(spec["windows"]), "n_records": n_records, "jsonl_sha256": jsonl_sha256,
            "run_spec_sha256": spec_sha256, "run_inputs_sha256": inputs_sha256}


def write_unit(run_dir: FsPath, spec: Mapping[str, Any], cell: str, unit: int, start: int, stop: int, data: bytes,
               spec_sha256: str, inputs_sha256: str) -> None:
    """jsonl first, then its index (the completion marker). An existing jsonl is never overwritten."""
    jsonl, index = unit_paths(run_dir, cell, unit)
    _write_or_compare(jsonl, data, f"unit {cell}/{unit}")
    n = (stop - start) * len(spec["windows"])
    atomic_write_bytes(index, canonical_bytes(_unit_index(spec, cell, unit, start, stop, n, _sha256(data),
                                                          spec_sha256, inputs_sha256)))


def _check_unit_records(data: bytes, spec: Mapping[str, Any], cell: str, start: int, stop: int) -> None:
    """Every line canonical, and the (cell, rep, window) sequence exactly the expected one (no gap, no duplicate)."""
    lines = data.splitlines(keepends=True)
    want = [(cell, r, w) for r in range(start, stop) for w in spec["windows"]]
    got = []
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError as exc:
            raise StopImplementation(f"unit {cell} [{start}, {stop}): unreadable line") from exc
        if not isinstance(rec, dict) or canonical_bytes(rec) != line:
            raise StopImplementation(f"unit {cell} [{start}, {stop}): non-canonical line")
        got.append((rec.get("cell"), rec.get("rep"), rec.get("window")))
    if got != want:
        raise StopImplementation(f"unit {cell} [{start}, {stop}): records are not exactly reps x windows in order")


def verify_unit(run_dir: FsPath, spec: Mapping[str, Any], cell: str, unit: int, start: int, stop: int,
                spec_sha256: str, inputs_sha256: str) -> str:
    """A complete unit: jsonl and index present, records exactly (rep, window) over [start, stop), index bytes equal
    to the index rebuilt from the jsonl. Returns the jsonl sha256; any mismatch is a STOP (read-only)."""
    jsonl, index = unit_paths(run_dir, cell, unit)
    if not (jsonl.exists() and index.exists()):
        raise StopImplementation(f"unit {cell}/{unit} is not complete")
    data = jsonl.read_bytes()
    _check_unit_records(data, spec, cell, start, stop)
    want = canonical_bytes(_unit_index(spec, cell, unit, start, stop, len(data.splitlines()), _sha256(data),
                                       spec_sha256, inputs_sha256))
    if index.read_bytes() != want:
        raise StopImplementation(f"unit {cell}/{unit}: index does not match its jsonl / run_spec / run_inputs")
    return _sha256(data)


def build_manifest(spec: Mapping[str, Any], inputs: Mapping[str, Any], units: Sequence[Mapping[str, Any]],
                   spec_sha256: str, inputs_sha256: str, research: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run provenance from run_spec, run_inputs and the unit hashes. A TEST_FIXTURE manifest lists what a research
    run would add (MANIFEST_PENDING); a RESEARCH manifest carries those items in its research block (ERRATA-005 [C]:
    calibration values, the A1-c seed collision report, the G6 section of a CORE run and the UDR sha256 used)."""
    if inputs["calibration_provenance"].get("kind") == TEST_FIXTURE:
        if research is not None:
            raise StopImplementation("a TEST_FIXTURE manifest has no research block")
        head: dict[str, Any] = {"fixture": TEST_FIXTURE, "pending_for_research_run": list(MANIFEST_PENDING)}
    else:
        validate_research_block(spec, inputs, research)
        assert research is not None
        head = {"research": json.loads(canonical_bytes(dict(research)))}
    return {"schema_version": MANIFEST_SCHEMA, "study_id": STUDY_ID, "evidence": EVIDENCE, **head,
            "run_spec_sha256": spec_sha256, "run_inputs_sha256": inputs_sha256,
            "code_sha": spec["code_sha"], "code_tree": spec["code_tree"],
            "futility_diag_source": inputs["futility_diag_source"],
            "mcv06_source_identity": inputs["mcv06_source_identity"],
            "prereg_sha256": spec["prereg_sha256"], "config_sha256": spec["config_sha256"],
            "python": inputs["python"], "seed_policy": spec["seed_policy"], "base_seed": spec["base_seed"],
            "mode": spec["mode"], "namespace": inputs["namespace"],
            "cells": {name: {**c, "reps": spec["reps"], "bootstrap": spec["bootstrap"], "windows": spec["windows"]}
                      for name, c in inputs["cells"].items()},
            "calibration_provenance": inputs["calibration_provenance"], "units": list(units)}


def sha256sums_bytes(run_dir: FsPath) -> bytes:
    """'<sha256>  <posix path>' lines, path-sorted, over every file except execution.json, SHA256SUMS, *.tmp and
    g6/ (verified by its own SHA256SUMS, so writing G6 never changes this file)."""
    run_dir = FsPath(run_dir)
    rels = sorted(rel for rel in (p.relative_to(run_dir).as_posix() for p in run_dir.rglob("*")
                                  if p.is_file() and not p.name.endswith(TMP_SUFFIX))
                  if rel not in (EXECUTION_FILE, SUMS_FILE) and rel.split("/")[0] != G6_DIR)
    return "".join(f"{sha256_file(run_dir / rel)}  {rel}\n" for rel in rels).encode("utf-8")


def write_sha256sums(run_dir: FsPath) -> str:
    return _write_or_compare(FsPath(run_dir) / SUMS_FILE, sha256sums_bytes(run_dir), SUMS_FILE)


# execution.json (ERRATA-003 R-5): every non-deterministic value, nothing else. One session per run_units call:
# a start record (written before T_wall starts), one record per unit completed in that session (its per-rep compute
# times and the parent's elapsed time since T_wall start, written right after the unit's index) and an end record
# (after manifest and SHA256SUMS). A session without an end record is an abnormal end: TIME_ACCOUNTING_INCOMPLETE.
# The G6 timing judgment is added once as g6_timing. Every write is atomic and keeps the earlier records.
EXECUTION_FIELDS = ("schema_version", "evidence", "sessions")
G6_TIMING_KEY = "g6_timing"
SESSION_FIELDS = ("started_utc", "workers", "init", "init_s", "git", "python", "platform", "tmp_reported", "units",
                  "end")
UNIT_EVENT_FIELDS = ("cell", "unit", "how", "rep_seconds", "elapsed_s", "utc", "progress_projection_s")
SESSION_END_FIELDS = ("finished_utc", "elapsed_s", "computed", "reused", "index_completed", "finalize_s", "stop",
                      "pre_wall_s", "post_wall_s", "post_wall_scope")
# ERRATA-004 R-1 diagnostics (never in W, t_hat, eta_hat, the G6 expected wall-clock or the 1.5 x STOP). The end
# record's own write cannot be timed inside that record, so it is in neither value.
POST_WALL_FULL = "THROUGH_SHA256SUMS"               # last index .. SHA256SUMS written (normal end)
POST_WALL_BUDGET_STOP = "THROUGH_LAST_UNIT_RECORD"  # budget STOP: no manifest / SHA256SUMS, so up to the unit record


def _num(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _session_ok(s: object) -> bool:
    if not (isinstance(s, dict) and set(s) == set(SESSION_FIELDS) and isinstance(s["units"], list)):
        return False
    for u in s["units"]:
        if not (isinstance(u, dict) and set(u) == set(UNIT_EVENT_FIELDS) and isinstance(u["rep_seconds"], list)
                and all(_num(v) for v in u["rep_seconds"]) and _num(u["elapsed_s"])):
            return False
    end = s["end"]
    return end is None or (isinstance(end, dict) and set(end) == set(SESSION_END_FIELDS) and _num(end["elapsed_s"]))


def read_execution(run_dir: FsPath) -> dict[str, Any] | None:
    """execution.json, or None when it is absent (the run stopped before its first session was recorded).
    Unreadable JSON, a schema error or a file without any session is damage: STOP, never rewritten."""
    path = FsPath(run_dir) / EXECUTION_FILE
    if not path.exists():
        return None
    try:
        ex = json.loads(path.read_bytes())
    except ValueError as exc:
        raise StopImplementation(f"{EXECUTION_FILE} is malformed") from exc
    if not (isinstance(ex, dict) and set(EXECUTION_FIELDS) <= set(ex) <= {*EXECUTION_FIELDS, G6_TIMING_KEY}
            and ex["schema_version"] == EXECUTION_SCHEMA and ex["evidence"] == EVIDENCE
            and isinstance(ex["sessions"], list) and all(_session_ok(s) for s in ex["sessions"])):
        raise StopImplementation(f"{EXECUTION_FILE} schema error")
    if not ex["sessions"]:
        raise StopImplementation(f"{EXECUTION_FILE} has no session")
    return ex


def _save_execution(run_dir: FsPath, sessions: Sequence[Mapping[str, Any]], **extra: Any) -> None:
    """Rewrite execution.json atomically with these sessions, keeping any g6_timing already recorded."""
    ex = read_execution(run_dir)
    kept = {G6_TIMING_KEY: ex[G6_TIMING_KEY]} if ex is not None and G6_TIMING_KEY in ex else {}
    atomic_write_bytes(FsPath(run_dir) / EXECUTION_FILE, canonical_bytes(
        {"schema_version": EXECUTION_SCHEMA, "evidence": EVIDENCE, "sessions": [dict(s) for s in sessions],
         **kept, **extra}))


def write_execution(run_dir: FsPath, session: Mapping[str, Any]) -> None:
    """Append one session to execution.json: the run's only non-deterministic file. Earlier sessions are kept as
    they are; a damaged file is a STOP (read_execution)."""
    ex = read_execution(run_dir)
    _save_execution(run_dir, [*(ex["sessions"] if ex is not None else []), session])


def _replace_last_session(run_dir: FsPath, session: Mapping[str, Any]) -> None:
    ex = read_execution(run_dir)
    assert ex is not None
    _save_execution(run_dir, [*ex["sessions"][:-1], session])


INCOMPLETE_TIME = "TIME_ACCOUNTING_INCOMPLETE"


def time_accounting(ex: Mapping[str, Any] | None,
                    completed_units: Iterable[tuple[str, int]] | None = None) -> dict[str, Any]:
    """ERRATA-003 R-4 / R-5, from execution.json alone. Session elapsed = the parent's time from T_wall start to the
    last unit index of that session (0 if it completed none); the cumulative wall-clock is their sum and never resets
    on resume. COMPLETE: every session has its end record and every completed unit has exactly one completion record.
    Otherwise INCOMPLETE: the cumulative value is a lower bound, the time after an open session's last record is
    reported as unaccounted (UTC differences are not run time) and no budget PASS is allowed."""
    if ex is None:
        missing = sorted(completed_units or [])
        return {"status": "INCOMPLETE", "reason": "NO_EXECUTION_RECORD", "cumulative_s": 0.0, "lower_bound": True,
                "session_elapsed_s": [], "open_sessions": [], "unaccounted": [],
                "unrecorded_units": [list(u) for u in missing], "budget_pass_allowed": False}
    sessions = ex["sessions"]
    elapsed = [s["units"][-1]["elapsed_s"] if s["units"] else 0.0 for s in sessions]
    if any(not (math.isfinite(x) and x >= 0) for x in elapsed):
        raise StopImplementation(f"{EXECUTION_FILE}: session elapsed time not finite and >= 0")
    recorded = [(u["cell"], u["unit"]) for s in sessions for u in s["units"]]
    if len(set(recorded)) != len(recorded):
        raise StopImplementation(f"{EXECUTION_FILE}: a unit has more than one completion record")
    open_ = [i for i, s in enumerate(sessions) if s["end"] is None]
    unrecorded = sorted(set(completed_units) - set(recorded)) if completed_units is not None else []
    complete = not open_ and not unrecorded
    return {"status": "COMPLETE" if complete else "INCOMPLETE",
            "reason": None if complete else INCOMPLETE_TIME, "cumulative_s": sum(elapsed),
            "lower_bound": not complete, "session_elapsed_s": elapsed, "open_sessions": open_,
            "unaccounted": [{"session": i, "after_utc": (sessions[i]["units"][-1]["utc"] if sessions[i]["units"]
                                                         else sessions[i]["started_utc"])} for i in open_],
            "unrecorded_units": [list(u) for u in unrecorded], "budget_pass_allowed": complete}


RUNTIME_STOP_MULTIPLE = 1.5        # config budget.runtime_stop_multiple (WO:421)


def wall_exceeded(cumulative_s: float, expected_wall_s: float) -> bool:
    """ERRATA-003 R-4: STOP when the CORE cumulative wall-clock is strictly greater than 1.5 x the G6 expected
    wall-clock; exactly 1.5 x passes. No rounding."""
    return cumulative_s > RUNTIME_STOP_MULTIPLE * expected_wall_s


def _load_spec_inputs(run_dir: FsPath) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    """run_spec and run_inputs from disk, each required to be in canonical form (bytes re-serialize identically)."""
    run_dir = FsPath(run_dir)
    raw_spec, raw_inputs = (run_dir / RUN_SPEC_FILE).read_bytes(), (run_dir / RUN_INPUTS_FILE).read_bytes()
    spec, inputs = json.loads(raw_spec), json.loads(raw_inputs)
    if run_spec_bytes(spec) != raw_spec or canonical_bytes(inputs) != raw_inputs:
        raise StopImplementation("run_spec / run_inputs on disk are not canonical")
    validate_run_inputs(inputs, spec)
    return spec, inputs, _sha256(raw_spec), _sha256(raw_inputs)


def _unit_entries(run_dir: FsPath, spec: Mapping[str, Any], spec_sha: str, inputs_sha: str) -> list[dict[str, Any]]:
    out = []
    for cell, k, s, e in _expected_units(spec):
        jsonl_sha = verify_unit(run_dir, spec, cell, k, s, e, spec_sha, inputs_sha)
        out.append({"cell": cell, "unit": k, "rep_start": s, "rep_stop": e, "jsonl_sha256": jsonl_sha,
                    "index_sha256": sha256_file(unit_paths(run_dir, cell, k)[1])})
    return out


UnitRunner = Callable[[CellSpec, Sequence[int], str, int, Sequence[str], int],
                      tuple[list[dict[str, object]], list[float]]]


def run_units(run_dir: FsPath, spec: Mapping[str, Any], inputs: Mapping[str, Any], workers: int = 1,
              expected_wall_s: float | None = None, resume_after_incomplete: bool = False, *,
              research: Mapping[str, Any] | None = None, lock: LockHandle | None = None,
              unit_runner: UnitRunner | None = None, budget_offset_s: float = 0.0) -> dict[str, Any]:
    """Run or resume: check run_spec / run_inputs byte for byte, reuse verified complete units, compute only the
    missing ones, then write manifest and SHA256SUMS. Units do not depend on workers.
    Time goes to execution.json only (ERRATA-003 R-5): the session start record, then T_wall / session elapsed starts
    (after init_run and the directory checks, before the first unit's pool, R-2); one record per unit completed here
    with its per-rep compute times (R-1); the end record after manifest and SHA256SUMS, with the ERRATA-004 R-1
    diagnostics pre_wall_s (init_run call .. T_wall start) and post_wall_s (last index .. SHA256SUMS, or .. the last
    unit record after a budget STOP), which no budget value uses.
    expected_wall_s (G7 CORE only: the G6 expected wall-clock in seconds) turns on R-4: STOP after the unit at which
    the cumulative wall-clock of all sessions exceeds 1.5 x expected (that unit and the earlier ones are kept), and
    no resume over an earlier abnormally ended session unless the user decided so (resume_after_incomplete).
    ERRATA-005: a RESEARCH run needs its research block (the manifest's); a RESEARCH CORE run needs the G7 lock
    handle, checked with the last-session rule at the start, before each unit file and before each execution.json
    write; budget_offset_s adds every other CORE run's recorded cumulative (R-3); unit_runner replaces the plain
    pool (the G7 start barrier). Nothing is written when a precondition fails."""
    started = datetime.now(UTC)
    t_init = _clock()
    run_dir = FsPath(run_dir)
    is_research = inputs["calibration_provenance"].get("kind") == RESEARCH
    if is_research:
        validate_research_block(spec, inputs, research)
        if spec["mode"] == "core" and lock is None:
            raise StopImplementation("a research CORE run needs the G7 lock handle (ERRATA-005 R-4)")
    elif research is not None or lock is not None or unit_runner is not None:
        raise StopImplementation("research block, lock and unit runner belong to RESEARCH runs only")
    written: list[Any] = []                            # the last session this process wrote (owner check)

    def owned() -> None:
        if lock is None:
            return
        lock.check()
        if written:
            ex = read_execution(run_dir)
            if ex is None or ex["sessions"][-1] != written[-1]:
                raise StopForUserDecision("execution.json's last session is not the one this process opened")

    def save(first: bool) -> None:
        owned()
        (write_execution if first else _replace_last_session)(run_dir, session)
        written.append(json.loads(canonical_bytes(session)))

    owned()
    state = init_run(run_dir, spec, inputs)
    scan = scan_run_dir(run_dir, spec)
    if scan["unexpected"]:
        raise StopImplementation(f"unexpected files in the run directory: {scan['unexpected']}")
    if (run_dir / SUMS_FILE).exists() and not (run_dir / MANIFEST_FILE).exists():
        raise StopImplementation(f"{SUMS_FILE} without {MANIFEST_FILE}")
    prior = time_accounting(read_execution(run_dir))  # a damaged execution.json STOPs before any work
    if expected_wall_s is not None:
        if prior["open_sessions"] and not resume_after_incomplete:
            raise StopForUserDecision(f"{INCOMPLETE_TIME}: sessions {prior['open_sessions']} ended abnormally; "
                                      "resuming is the user's decision")
        if wall_exceeded(prior["cumulative_s"] + budget_offset_s, expected_wall_s):
            raise StopImplementation(f"CORE wall-clock budget: recorded {prior['cumulative_s'] + budget_offset_s!r} s "
                                     f"(lower bound) > {RUNTIME_STOP_MULTIPLE} x expected {expected_wall_s!r} s")
    spec_sha, inputs_sha = _sha256(run_spec_bytes(spec)), _sha256(canonical_bytes(dict(inputs)))
    cells = {c.name: c for c in cells_from_inputs(inputs)}
    counts = {"computed": 0, "reused": 0, "index_completed": 0}
    session: dict[str, Any] = {
        "started_utc": started.isoformat(), "workers": workers, "init": state, "init_s": _clock() - t_init,
        "git": git_identity(), "python": platform.python_version(), "platform": platform.platform(),
        "tmp_reported": scan["tmp"], "units": [], "end": None}
    save(True)
    t0 = _clock()                                      # T_wall and session elapsed start here
    t_last_index = t0                                  # T_wall end so far (no unit computed yet)
    total_reps, done_reps, stop = len(spec["cells"]) * spec["reps"], 0, None
    for cell, k, s, e in _expected_units(spec):
        jsonl, index = unit_paths(run_dir, cell, k)
        if index.exists():
            verify_unit(run_dir, spec, cell, k, s, e, spec_sha, inputs_sha)
            counts["reused"] += 1
            done_reps += e - s
            continue
        if (run_dir / MANIFEST_FILE).exists():
            raise StopImplementation(f"{MANIFEST_FILE} exists but unit {cell}/{k} is not complete")
        runner = unit_runner or run_reps_timed
        records, seconds = runner(cells[cell], range(s, e), inputs["namespace"], spec["bootstrap"],
                                  spec["windows"], workers)
        data = records_bytes(records)
        if jsonl.exists() and jsonl.read_bytes() != data:
            raise StopImplementation(f"unit {cell}/{k}: existing jsonl differs from the recomputed records")
        how = "index_completed" if jsonl.exists() else "computed"
        counts[how] += 1
        owned()
        write_unit(run_dir, spec, cell, k, s, e, data, spec_sha, inputs_sha)
        t_last_index = _clock()
        elapsed = t_last_index - t0
        done_reps += e - s
        cumulative = prior["cumulative_s"] + elapsed + budget_offset_s
        session["units"].append({"cell": cell, "unit": k, "how": how, "rep_seconds": seconds, "elapsed_s": elapsed,
                                 "utc": datetime.now(UTC).isoformat(),
                                 "progress_projection_s": cumulative * total_reps / done_reps})   # diagnostic only
        save(False)
        if expected_wall_s is not None and wall_exceeded(cumulative, expected_wall_s):
            stop = (f"CORE wall-clock budget: cumulative {cumulative!r} s > {RUNTIME_STOP_MULTIPLE} x expected "
                    f"{expected_wall_s!r} s after unit {cell}/{k}")
            break
    finalize_s = None
    if stop is None:
        t_fin = _clock()
        units = _unit_entries(run_dir, spec, spec_sha, inputs_sha)
        owned()
        _write_or_compare(run_dir / MANIFEST_FILE, canonical_bytes(build_manifest(spec, inputs, units, spec_sha,
                                                                                 inputs_sha, research)), MANIFEST_FILE)
        write_sha256sums(run_dir)                     # before the end record, which it does not cover
        t_post = _clock()
        finalize_s, scope = t_post - t_fin, POST_WALL_FULL
    else:
        t_post, scope = _clock(), POST_WALL_BUDGET_STOP   # the unit record is already written
    session["end"] = {"finished_utc": datetime.now(UTC).isoformat(),
                      "elapsed_s": session["units"][-1]["elapsed_s"] if session["units"] else 0.0, **counts,
                      "finalize_s": finalize_s, "stop": stop, "pre_wall_s": t0 - t_init,
                      "post_wall_s": t_post - t_last_index, "post_wall_scope": scope}
    save(False)
    if stop is not None:
        raise StopImplementation(stop)
    return {"init": state, **counts, "tmp": scan["tmp"]}


def verify_run(run_dir: FsPath) -> dict[str, Any]:
    """Read-only check from the files alone, on separate axes:
    unit_status   COMPLETE when every expected unit is present and verified (deterministic);
    execution     RECORDED / MISSING: execution.json (damaged, wrong schema or no session = STOP);
    status        COMPLETE only when the units, manifest and SHA256SUMS verify AND the execution is recorded;
                  INCOMPLETE is a normal unfinished state (missing units, no manifest yet, or no execution.json);
    time_accounting  COMPLETE / INCOMPLETE (time_accounting(): an abnormally ended session or a completed unit
                  without its completion record); independent of status, and INCOMPLETE never allows a budget PASS;
    g6            ABSENT (a pilot without G6 is still COMPLETE) / VERIFIED / INCOMPLETE (summary written, its
                  SHA256SUMS not yet); damaged or inconsistent g6/ is a STOP.
    Damage or inconsistency raises StopImplementation."""
    run_dir = FsPath(run_dir)
    spec, inputs, spec_sha, inputs_sha = _load_spec_inputs(run_dir)
    scan = scan_run_dir(run_dir, spec)
    if scan["unexpected"]:
        raise StopImplementation(f"unexpected files in the run directory: {scan['unexpected']}")
    execution = read_execution(run_dir)
    missing, completed = [], []
    for cell, k, s, e in _expected_units(spec):
        jsonl, index = unit_paths(run_dir, cell, k)
        if index.exists():
            verify_unit(run_dir, spec, cell, k, s, e, spec_sha, inputs_sha)
            completed.append((cell, k))
        else:
            missing.append(f"{cell}/u{k:05d}")
    axes = {"unit_status": "INCOMPLETE" if missing else "COMPLETE",
            "execution": "MISSING" if execution is None else "RECORDED",
            "sessions": 0 if execution is None else len(execution["sessions"]),
            "time_accounting": time_accounting(execution, completed)["status"], "missing_units": missing,
            "tmp": scan["tmp"]}
    has_manifest, has_sums = (run_dir / MANIFEST_FILE).exists(), (run_dir / SUMS_FILE).exists()
    if missing or not has_manifest:
        if has_manifest or has_sums:
            raise StopImplementation("manifest / SHA256SUMS present for an incomplete run")
        if _g6_files(run_dir):
            raise StopImplementation("g6/ present for an incomplete run")
        return {"status": "INCOMPLETE", "g6": "ABSENT", **axes}
    units = _unit_entries(run_dir, spec, spec_sha, inputs_sha)
    raw_manifest = (run_dir / MANIFEST_FILE).read_bytes()
    research = None
    if inputs["calibration_provenance"].get("kind") == RESEARCH:
        try:                       # the research block is checked against this run (validate_research_block)
            research = json.loads(raw_manifest)["research"]
        except (ValueError, KeyError, TypeError) as exc:
            raise StopImplementation(f"{MANIFEST_FILE} of a research run has no readable research block") from exc
    if raw_manifest != canonical_bytes(build_manifest(spec, inputs, units, spec_sha, inputs_sha, research)):
        raise StopImplementation(f"{MANIFEST_FILE} does not match run_spec / run_inputs / units")
    if not has_sums or (run_dir / SUMS_FILE).read_bytes() != sha256sums_bytes(run_dir):
        raise StopImplementation(f"{SUMS_FILE} missing or does not match the files")
    return {"status": "INCOMPLETE" if execution is None else "COMPLETE", "units": len(units),
            "g6": verify_g6(run_dir, spec, spec_sha, inputs_sha), **axes}


# --- G3b-5-1: research identity (REPRODUCIBILITY_REQUIREMENTS, WO:392, WO:403-404) ------------------------------
#
# A research execution (G5 calibration and pilot, G7) runs from a clean CODE_SHA worktree. research_identity reads
# git (rev-parse, status, ls-tree only) and the contract files and STOPs unless everything matches; tests and the
# G4c smoke run (FUTDIAG-TEST, TEST_FIXTURE) never call it.

BASE_SHA = "15957207a592e062aaa51a6610b7e748ce136ca0"      # config study.base_sha (WO:392 MC-V06 diff base)
MODULE_PATH = "src/moneylab/research/v06/futility_diag.py"
CONTRACT_FILES = {"config": "configs/bt4_futility_diag.toml",
                  "prereg": "docs/research_bt4_futility_diag_preregistration.md",
                  "ERRATA-001": "docs/tasks/BT4-FUTILITY-01/ERRATA-001.md",
                  "ERRATA-002": "docs/tasks/BT4-FUTILITY-01/ERRATA-002.md",
                  "ERRATA-003": "docs/tasks/BT4-FUTILITY-01/ERRATA-003.md",
                  "ERRATA-004": "docs/tasks/BT4-FUTILITY-01/ERRATA-004.md",
                  "ERRATA-005": "docs/tasks/BT4-FUTILITY-01/ERRATA-005.md",
                  "ERRATA-006": "docs/tasks/BT4-FUTILITY-01/ERRATA-006.md",
                  "ERRATA-007": "docs/tasks/BT4-FUTILITY-01/ERRATA-007.md"}
# sha256 of the LF bytes, fixed at C2 (321b54b) and the Ce commits (616ed51, 2eb876e, b9932dc, a1b15ff, 02aa62b,
# 31d15ed, 59f62ee); ERRATA-007 1: every ACCEPTED ERRATA fixed before C3, ERRATA-007 computed from the Ce7 blob
CONTRACT_SHA256 = {"config": "3df664508e117ae25b05d7de49b3f62dec1c6ef55eab185ce0cf52f631351723",
                   "prereg": "6da9e20088b1a6ca5c9ce9696c0baadd0850d7aa409f962f2583b188b322189f",
                   "ERRATA-001": "9fcac5a97605a85be68612ba4a465c5f24b8c5b5594f3a801ca5e551993d24bf",
                   "ERRATA-002": "0ca8ab961af350b10a2660ca8ee7b8c4bfab2757ee2b6b1ae61ffcfeee7308fe",
                   "ERRATA-003": "9b8fcf9f30d8b525237a63b00f599add0a2fbcb33cb0f9ce900642a5a349823d",
                   "ERRATA-004": "4b8de161474139cd24976897804a717ad94c9beaa89a2f74da492e0e845b2061",
                   "ERRATA-005": "34408e04bf832446d376cc5dd679a4fc4f4afc20b8d1be472c640d75be1d194e",
                   "ERRATA-006": "63c08d10131a71911e849f60b4ff09c542853821c1a3458a68369ffa1bc6fd11",
                   "ERRATA-007": "25841248dae87d0f5568c72e9b35b00ea1a79530f1e546c7d5c312cb67d56cda"}
IDENTITY_FIELDS = ("git_head", "git_tree", "worktree_clean", "base_sha", "futility_diag_source",
                   "mcv06_source_identity", "contract_sha256", "calibration_sha256")
GitRunner = Callable[..., str]


def repo_root() -> FsPath:
    return FsPath(__file__).resolve().parents[4]


def _git(root: FsPath, *args: str) -> str:
    """One read-only git query in root; a failure is a STOP."""
    try:
        proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8")
    except OSError as exc:
        raise StopImplementation(f"git {' '.join(args)} could not run: {exc}") from exc
    if proc.returncode != 0:
        raise StopImplementation(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _lf(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n")


def _blob_lf(raw: bytes) -> str:
    """git blob id of the LF bytes (as montecarlo.source_identity)."""
    lf = _lf(raw)
    return hashlib.sha1(b"blob %d\0" % len(lf) + lf).hexdigest()


def _ls_tree(git: GitRunner, root: FsPath, commit: str, paths: Sequence[str]) -> dict[str, str]:
    out = {}
    for line in git(root, "ls-tree", commit, "--", *paths).splitlines():
        meta, path = line.split("\t", 1)
        out[path] = meta.split()[2]
    return out


def research_identity(root: FsPath | None = None, git: GitRunner = _git,
                      calibration_sha256: str | None = None) -> dict[str, Any]:
    """Identity of a research execution. STOP unless: `git status --porcelain` is empty (WO:403); the contract files
    have their accepted sha256; this module is the one under root; it and the MC-V06 _SOURCE_FILES equal their HEAD
    blobs; the _SOURCE_FILES equal the base commit's (WO:392)."""
    root = FsPath(root) if root is not None else repo_root()
    head, tree = git(root, "rev-parse", "HEAD").strip(), git(root, "rev-parse", "HEAD^{tree}").strip()
    if not (_HEX40.fullmatch(head) and _HEX40.fullmatch(tree)):
        raise StopImplementation(f"git HEAD / tree not readable: {head!r}, {tree!r}")
    dirty = git(root, "status", "--porcelain").splitlines()
    if dirty:
        raise StopImplementation(f"worktree is not clean ({len(dirty)} entries): research runs need CODE_SHA clean")
    contracts = {k: _sha256(_lf((root / rel).read_bytes())) for k, rel in CONTRACT_FILES.items()}
    bad = sorted(k for k, v in contracts.items() if v != CONTRACT_SHA256[k])
    if bad:
        raise StopImplementation(f"contract files differ from their accepted sha256: {bad}")
    here = FsPath(__file__).resolve()
    if here != (root / MODULE_PATH).resolve():
        raise StopImplementation(f"futility_diag imported from {here}, not from {root}")
    src = {**module_source(), "git_blob_lf": _blob_lf(here.read_bytes())}
    mcv = source_identity()
    mcv_paths = [f"src/{k}" for k in mcv]
    working = {MODULE_PATH: src["git_blob_lf"], **{f"src/{k}": v["git_blob_lf"] for k, v in mcv.items()}}
    if _ls_tree(git, root, head, list(working)) != working:
        raise StopImplementation("futility_diag.py / MC-V06 _SOURCE_FILES differ from their HEAD blobs")
    if _ls_tree(git, root, BASE_SHA, mcv_paths) != {p: working[p] for p in mcv_paths}:
        raise StopImplementation("MC-V06 _SOURCE_FILES differ from the base commit")
    return {"git_head": head, "git_tree": tree, "worktree_clean": True, "base_sha": BASE_SHA,
            "futility_diag_source": src, "mcv06_source_identity": mcv, "contract_sha256": contracts,
            "calibration_sha256": calibration_sha256}


def verify_research_identity(recorded: Mapping[str, Any], root: FsPath | None = None,
                             git: GitRunner = _git) -> dict[str, Any]:
    """Recompute the identity now and require it to equal the recorded one (STOP on any difference)."""
    if set(recorded) != set(IDENTITY_FIELDS):
        raise StopImplementation("research identity fields")
    current = research_identity(root, git, recorded["calibration_sha256"])
    diff = sorted(k for k in IDENTITY_FIELDS if current[k] != recorded[k])
    if diff:
        raise StopImplementation(f"research identity differs from the recorded one: {diff}")
    return current


def check_run_identity(spec: Mapping[str, Any], inputs: Mapping[str, Any], identity: Mapping[str, Any]) -> None:
    """A research run's run_spec / run_inputs must name the identity it runs under (STOP otherwise)."""
    src = identity["futility_diag_source"]
    pairs = {"code_sha": (spec["code_sha"], identity["git_head"]),
             "code_tree": (spec["code_tree"], identity["git_tree"]),
             "config_sha256": (spec["config_sha256"], identity["contract_sha256"]["config"]),
             "prereg_sha256": (spec["prereg_sha256"], identity["contract_sha256"]["prereg"]),
             "futility_diag_source": (inputs["futility_diag_source"],
                                      {"sha256": src["sha256"], "sha256_lf": src["sha256_lf"]}),
             "mcv06_source_identity": (inputs["mcv06_source_identity"], identity["mcv06_source_identity"]),
             "calibration_sha256": (inputs["calibration_provenance"].get("calibration_sha256"),
                                    identity["calibration_sha256"])}
    diff = sorted(k for k, (a, b) in pairs.items() if a != b)
    if diff:
        raise StopImplementation(f"run_spec / run_inputs do not match the research identity: {diff}")


# ERRATA-007 2-3: identity across stages. CAL = the G5 calibration.json identity, PILOT = the G5 pilot run_spec,
# NOW = the identity computed at entry. Checked at G5 pilot, G6 summarize and G7 core entry, after NOW and before
# any research output of that stage; no git call here (NOW is the caller's). Not used by the TEST_FIXTURE path.
STAGE_INVARIANT_FIELDS = ("git_head", "git_tree", "worktree_clean", "base_sha", "futility_diag_source",
                          "mcv06_source_identity", "contract_sha256")


def read_pilot_spec(pilot_dir: FsPath) -> tuple[dict[str, Any], str]:
    """PILOT: the pilot's run_spec.json, present, canonical and valid (STOP otherwise). Returns (spec, sha256); G7
    compares the sha256 with the one its VERIFIED g6/ references."""
    path = FsPath(pilot_dir) / RUN_SPEC_FILE
    if not path.is_file():
        raise StopImplementation(f"pilot {RUN_SPEC_FILE} is missing")
    spec, raw = _read_canonical(path, f"pilot {RUN_SPEC_FILE}")
    validate_run_spec(spec)
    return spec, _sha256(raw)


def check_stage_identity(cal_identity: Mapping[str, Any], now: Mapping[str, Any], calibration_sha256: str,
                         pilot_spec: Mapping[str, Any] | None = None) -> None:
    """CAL and NOW agree on the 7 stage-invariant fields; calibration_sha256 is null in CAL and the used file's sha256
    in NOW (never compared between them); with PILOT (G6, G7), its code_sha / code_tree / config_sha256 /
    prereg_sha256 are NOW's. Anything else is a STOP naming the fields."""
    for what, ident in (("calibration identity", cal_identity), ("current identity", now)):
        keys = set(ident) if isinstance(ident, Mapping) else set()
        if keys != set(IDENTITY_FIELDS):
            raise StopImplementation(f"{what} fields: missing {sorted(set(IDENTITY_FIELDS) - keys)}, "
                                     f"unexpected {sorted(keys - set(IDENTITY_FIELDS))}")
    if not (isinstance(cal_identity["git_tree"], str) and _HEX40.fullmatch(cal_identity["git_tree"])):
        raise StopImplementation("calibration identity git_tree is not 40 lowercase hex")
    if cal_identity["calibration_sha256"] is not None:
        raise StopImplementation("calibration identity calibration_sha256 is not null")
    if now["calibration_sha256"] != calibration_sha256:
        raise StopImplementation("current identity differs from the calibration file used: ['calibration_sha256']")
    diff = sorted(k for k in STAGE_INVARIANT_FIELDS if cal_identity[k] != now[k])
    if diff:
        raise StopImplementation(f"current identity differs from the G5 calibration identity: {diff}")
    if pilot_spec is None:
        return
    if not isinstance(pilot_spec, Mapping):
        raise StopImplementation("pilot run_spec is not an object")
    validate_run_spec(pilot_spec)
    contracts = now["contract_sha256"]
    pairs = {"code_sha": now["git_head"], "code_tree": now["git_tree"], "config_sha256": contracts["config"],
             "prereg_sha256": contracts["prereg"]}
    diff = sorted(k for k, v in pairs.items() if pilot_spec[k] != v)
    if diff:
        raise StopImplementation(f"pilot run_spec differs from the current identity: {diff}")


# --- G3b-5-1: calibration artifact (DC6, DC14, preregistration 7, ERRATA-002, ERRATA-003 R-7) --------------------
#
# <calibration dir>/calibration.json   canonical JSON, written once; an existing file must be byte-identical.
# RESEARCH: the E1 edge on the 4,000-year FUTDIAG path and the R_sigma = 2,000 FUTDIAG-SIGMA sigma calibration, with
# the research identity of the code and contract files that produced them. TEST_FIXTURE (G4c smoke, tests): the
# ERRATA-003 R-7 values with a FUTDIAG-TEST sigma calibration; never a research input.

CALIBRATION_FILE = "calibration.json"
CALIBRATION_SCHEMA = "moneylab.bt4_futility_diag.calibration/1"
RESEARCH = "RESEARCH"
CALIBRATION_KINDS = (RESEARCH, TEST_FIXTURE)
CALIBRATION_FIELDS = ("schema_version", "study_id", "evidence", "kind", "e1", "sigma", "mcv06_inputs", "identity")
E1_CAL_FIELDS = ("cell", "theta", "strategy", "target", "years", "seed_parts", "seed", "edge_annual",
                 "achieved_sharpe", "residual", "sigma_pop")
SIGMA_CAL_FIELDS = ("namespace", "cell", "window", "edge_annual", "reps", "seed_path", "z", "sharpes", "sigma_hat",
                    "kappa_hat", "sigma_L", "sigma_U")
FIXTURE_IDENTITY_FIELDS = ("git", "futility_diag_source", "mcv06_source_identity")
CALIB_YEARS = 4000                 # config core.calib_years
CALIB_TOLERANCE = 1e-3             # |SR_ach - theta| (preregistration 2); larger = unconverged calibration (STOP)
SIGMA_R = 2000                     # config core.sigma_calibration_r
SIGMA_WINDOW = "conf"
E_CAL = 0.728515625                # config mcv06_inputs.e_cal (preregistration 2)
MCV06_INPUTS = {"source": "configs/bt4_futility_diag.toml [mcv06_inputs]",
                "run_unit": "mc_v06_full_2d6ed0a/16_normal_M60_+0p7_attempt1",
                "manifest_sha256": "2025f9aace9960f14efcbef1543d3eb719124b114bef86f4fcff27c1b3b3acb2",
                "summary_sha256": "f5680e8abdbaa06a77c1bd8d01b6060c76865e0261ab264c8739f6ac347fc613",
                "seed": 20261012, "scenario": "normal_M60_+0p7", "e_cal": E_CAL, "sr_ach": 0.70007463504927}


def achieved_reproduced(sharpe: float, achieved: float) -> bool:
    """montecarlo.calibrate_edge returns achieved = (Sharpe - theta) + theta (f(x) = _target_sharpe - theta, then
    best[1] + theta), so a recomputed Sharpe is compared in that same arithmetic, bit for bit, no tolerance."""
    return (sharpe - CORE_THETA) + CORE_THETA == achieved


V4_ESTIMATE_NAME, V4_ESTIMATE_METHOD = "V4_EVAL_TIME_ESTIMATE", "SAME_EVALUATION_REPLAY"   # ERRATA-004 R-3


def _replay_evaluation(edge_annual: float, noise: Any, costs: Mapping[str, float]) -> float:
    """ERRATA-004 R-3 SAME_EVALUATION_REPLAY: calibrate_edge's f(x) evaluation, once, without the "- theta":
    replace, add_drift, Path, _target_sharpe (strategy_signals over every STRATEGIES entry, M60, E0 segment returns,
    annual Sharpe). The MC-V06 functions are called as they are, never wrapped or replaced."""
    return _target_sharpe(Path(*add_drift(replace(E1_DGP, edge_annual=edge_annual), noise)), E1_STRATEGY, "E0",
                          dict(costs))


def calibrate_e1(years: int = CALIB_YEARS, seed_parts: Sequence[str] = E1_CALIB_SEED_PARTS) -> dict[str, Any]:
    """The calibration.json e1 section of calibrate_e1_timed (its times go to the calibration execution record)."""
    return calibrate_e1_timed(years, seed_parts)[0]


def calibrate_e1_timed(years: int = CALIB_YEARS,
                       seed_parts: Sequence[str] = E1_CALIB_SEED_PARTS) -> tuple[dict[str, Any], dict[str, Any]]:
    """E1 edge (DC6, preregistration 7): montecarlo.calibrate_edge on one noise path of years x 365 days (as
    montecarlo.resolve) from seed_parts, M60 / E0 / theta 0.7, default costs. sigma_pop is the sd of the E0 segment
    returns of the calibrated path on _target_sharpe's segment [min_warmup() + 1, days - 1), whose annual Sharpe
    must reproduce the achieved one. Failure or |achieved - theta| > 1e-3 is a STOP.
    Times (ERRATA-004 R-2, R-3; never in W): noise, the calibrate_edge search, the V4_EVAL_TIME_ESTIMATE (one
    SAME_EVALUATION_REPLAY after the search, on the same noise and the returned edge; its Sharpe s must satisfy
    (s - theta) + theta == achieved, else STOP) and the post-processing (achieved SR check and sigma_pop)."""
    if not _positive_int(years):
        raise StopImplementation(f"years must be a positive int, got {years!r}")
    parts = list(validate_seed_parts(seed_parts))
    seed = explicit_seed(parts)
    t_noise = _clock()
    noise = draw_noise(E1_DGP, years * 365, seed)
    t_search = _clock()
    lc = Costs().log_costs()
    try:
        edge, achieved = calibrate_edge(E1_DGP, noise, E1_STRATEGY, "E0", CORE_THETA, lc)
    except ValueError as exc:
        raise StopImplementation(f"E1 calibration failed: {exc}") from exc
    t_search_end = _clock()
    t_replay = _clock()
    s_replay = _replay_evaluation(edge, noise, lc)
    t_replay_end = _clock()
    if not achieved_reproduced(s_replay, achieved):
        raise StopImplementation("the replayed evaluation does not reproduce the achieved Sharpe")
    path = Path(*add_drift(replace(E1_DGP, edge_annual=edge), noise))
    rets = window_e0_returns(path, signals(path.log_close, *STRATEGIES[E1_STRATEGY]), min_warmup() + 1,
                             path.days - 1, lc["E0"])
    if not achieved_reproduced(annual_sharpe(rets), achieved):
        raise StopImplementation("the sigma_pop segment does not reproduce the achieved Sharpe")
    residual = finite_or_stop(achieved, "achieved Sharpe") - CORE_THETA
    if abs(residual) > CALIB_TOLERANCE:
        raise StopImplementation(f"E1 calibration did not converge: achieved - theta = {residual!r}")
    e1 = {"cell": "E1-theta0.7", "theta": CORE_THETA, "strategy": E1_STRATEGY, "target": "E0", "years": years,
          "seed_parts": parts, "seed": seed, "edge_annual": finite_or_stop(edge, "edge"),
          "achieved_sharpe": achieved, "residual": residual, "sigma_pop": finite_or_stop(sd(rets), "sigma_pop")}
    times = {"e1_noise_s": t_search - t_noise, "e1_search_s": t_search_end - t_search,
             "e1_post_s": _clock() - t_replay_end,
             "v4_eval_time_estimate": {"name": V4_ESTIMATE_NAME, "method": V4_ESTIMATE_METHOD, "kind": "ESTIMATE",
                                       "seconds": t_replay_end - t_replay}}
    return e1, times


def fixture_e1() -> dict[str, Any]:
    """ERRATA-003 R-7 TEST_FIXTURE: edge = e_cal, sigma_pop = 0.70/sqrt(365); nothing is calibrated."""
    return {"cell": "E1-theta0.7", "theta": CORE_THETA, "strategy": E1_STRATEGY, "target": "E0", "years": None,
            "seed_parts": None, "seed": None, "edge_annual": E_CAL, "achieved_sharpe": None, "residual": None,
            "sigma_pop": P0_DAILY_SD}


def _sigma_task(args: tuple[str, int, float]) -> float:
    namespace, rep, edge = args
    r = e1_window_returns(edge, seed_for(sigma_seed_path(rep, namespace)), (SIGMA_WINDOW,))[SIGMA_WINDOW]
    return finite_or_stop(annual_sharpe(r), "sigma calibration Sharpe")


def sigma_calibration(reps: int, namespace: str = SIGMA_NAMESPACE, edge_annual: float = E_CAL,
                      workers: int = 1) -> dict[str, Any]:
    """DC14 / preregistration 7: conf-window annual SR_hat of reps e_cal DGP paths (seed (namespace, E1-ecal,
    str(rep), all, path), rep = 0 .. reps - 1, no bootstrap), with sigma_hat, kappa_hat and [sigma_L, sigma_U].
    Ordered by rep, so the result does not depend on workers."""
    if not (_positive_int(reps) and reps >= 2 and _positive_int(workers)):
        raise StopImplementation(f"sigma calibration needs reps >= 2 and workers >= 1, got {reps!r}, {workers!r}")
    sigma_seed_path(0, namespace)
    tasks = [(namespace, i, edge_annual) for i in range(reps)]
    if workers == 1:
        values = [_sigma_task(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            values = list(pool.map(_sigma_task, tasks))
    s_hat, kappa, lo, hi = sigma_interval(values)
    return {"namespace": namespace, "cell": SIGMA_CELL, "window": SIGMA_WINDOW, "edge_annual": edge_annual,
            "reps": reps, "seed_path": [namespace, SIGMA_CELL, "<rep>", PATH_WINDOW, PATH_RULE], "z": Z_SIGMA,
            "sharpes": values, "sigma_hat": s_hat, "kappa_hat": kappa, "sigma_L": lo, "sigma_U": hi}


def fixture_identity() -> dict[str, Any]:
    """Identity recorded by a TEST_FIXTURE calibration: the sources only, no git condition."""
    return {"git": None, "futility_diag_source": module_source(), "mcv06_source_identity": source_identity()}


def build_calibration(kind: str, e1: Mapping[str, Any], sigma: Mapping[str, Any],
                      identity: Mapping[str, Any]) -> dict[str, Any]:
    cal = {"schema_version": CALIBRATION_SCHEMA, "study_id": STUDY_ID, "evidence": EVIDENCE, "kind": kind,
           "e1": dict(e1), "sigma": dict(sigma), "mcv06_inputs": dict(MCV06_INPUTS), "identity": dict(identity)}
    validate_calibration(cal)
    return cal


def _finite(x: object) -> bool:
    return isinstance(x, float) and math.isfinite(x)


def validate_calibration(cal: Mapping[str, Any]) -> None:
    """Exact fields; sigma values reproduce their interval; RESEARCH = 4,000-year FUTDIAG E1 path, converged, and
    R_sigma = 2,000 in FUTDIAG-SIGMA with a research identity; TEST_FIXTURE = ERRATA-003 R-7 values with a
    FUTDIAG-TEST sigma calibration and no git identity. Anything else is a STOP."""
    if set(cal) != set(CALIBRATION_FIELDS):
        raise StopImplementation("calibration fields")
    e1, sg, kind = cal["e1"], cal["sigma"], cal["kind"]
    if (cal["schema_version"], cal["study_id"], cal["evidence"]) != (CALIBRATION_SCHEMA, STUDY_ID, EVIDENCE) \
            or kind not in CALIBRATION_KINDS or cal["mcv06_inputs"] != MCV06_INPUTS:
        raise StopImplementation("calibration schema / kind / MC-V06 inputs")
    if not (isinstance(e1, dict) and set(e1) == set(E1_CAL_FIELDS) and isinstance(sg, dict)
            and set(sg) == set(SIGMA_CAL_FIELDS)):
        raise StopImplementation("calibration e1 / sigma fields")
    if (e1["cell"], e1["theta"], e1["strategy"], e1["target"]) != ("E1-theta0.7", CORE_THETA, E1_STRATEGY, "E0") \
            or not (_finite(e1["edge_annual"]) and _finite(e1["sigma_pop"]) and e1["sigma_pop"] > 0):
        raise StopImplementation("calibration e1 values")
    values = sg["sharpes"]
    if not (sg["cell"] == SIGMA_CELL and sg["window"] == SIGMA_WINDOW and sg["edge_annual"] == E_CAL
            and sg["z"] == Z_SIGMA and sg["namespace"] in SIGMA_NAMESPACES
            and sg["seed_path"] == [sg["namespace"], SIGMA_CELL, "<rep>", PATH_WINDOW, PATH_RULE]
            and isinstance(values, list) and _positive_int(sg["reps"]) and len(values) == sg["reps"] >= 2
            and all(_finite(v) for v in values)):
        raise StopImplementation("calibration sigma values")
    if list(sigma_interval(values)) != [sg["sigma_hat"], sg["kappa_hat"], sg["sigma_L"], sg["sigma_U"]]:
        raise StopImplementation("calibration sigma interval does not match its values")
    ident = cal["identity"]
    if kind == RESEARCH:
        if not (e1["years"] == CALIB_YEARS and e1["seed_parts"] == list(E1_CALIB_SEED_PARTS)
                and e1["seed"] == explicit_seed(E1_CALIB_SEED_PARTS) and _finite(e1["achieved_sharpe"])
                and e1["residual"] == e1["achieved_sharpe"] - CORE_THETA
                and abs(e1["residual"]) <= CALIB_TOLERANCE):
            raise StopImplementation("RESEARCH calibration needs the converged 4,000-year FUTDIAG E1 path")
        if not (sg["namespace"] == SIGMA_NAMESPACE and sg["reps"] == SIGMA_R):
            raise StopImplementation("RESEARCH calibration needs R_sigma = 2,000 in FUTDIAG-SIGMA")
        if not (isinstance(ident, dict) and set(ident) == set(IDENTITY_FIELDS) and ident["worktree_clean"] is True
                and ident["calibration_sha256"] is None and _HEX40.fullmatch(str(ident["git_head"]))
                and isinstance(ident["git_tree"], str) and _HEX40.fullmatch(ident["git_tree"])   # ERRATA-007 3
                and ident["contract_sha256"] == CONTRACT_SHA256):
            raise StopImplementation("RESEARCH calibration needs a research identity")
    else:
        if dict(e1) != fixture_e1() or sg["namespace"] != "FUTDIAG-TEST":
            raise StopImplementation("TEST_FIXTURE calibration: ERRATA-003 R-7 values in FUTDIAG-TEST only")
        if not (isinstance(ident, dict) and set(ident) == set(FIXTURE_IDENTITY_FIELDS) and ident["git"] is None):
            raise StopImplementation("TEST_FIXTURE calibration identity")


def calibration_bytes(cal: Mapping[str, Any]) -> bytes:
    validate_calibration(cal)
    return canonical_bytes(dict(cal))


def write_calibration(cal_dir: FsPath, cal: Mapping[str, Any], root: FsPath | None = None,
                      git: GitRunner = _git) -> str:
    """Write calibration.json atomically, or require the existing file to be byte-identical (never overwritten).
    A RESEARCH calibration is written only while its recorded identity still holds. Returns the file's sha256."""
    data = calibration_bytes(cal)
    if cal["kind"] == RESEARCH:
        verify_research_identity(cal["identity"], root, git)
    scan_calibration_dir(cal_dir)
    _write_or_compare(FsPath(cal_dir) / CALIBRATION_FILE, data, "calibration")
    return _sha256(data)


# --- ERRATA-004 R-2: the calibration directory's execution record (non-deterministic, not in any provenance) -------
#
# <calibration dir>/calibration.json   deterministic (schema unchanged); its sha256 is the provenance
# <calibration dir>/execution.json     runs: start / end UTC, elapsed, workers, phase times, V4_EVAL_TIME_ESTIMATE
# Nothing else is allowed in the directory. Calibration time is never part of the CORE W (ERRATA-003 R-3).

CAL_EXECUTION_SCHEMA = "moneylab.bt4_futility_diag.calibration_execution/1"
CAL_EXECUTION_FIELDS = ("schema_version", "evidence", "runs")
CAL_RUN_FIELDS = ("started_utc", "finished_utc", "elapsed_s", "workers", "phases", "v4_eval_time_estimate", "git",
                  "python", "platform")
V4_ESTIMATE_FIELDS = ("name", "method", "kind", "seconds")


def scan_calibration_dir(cal_dir: FsPath) -> list[str]:
    """Only calibration.json and execution.json (leftover *.tmp are reported, never deleted); anything else STOPs."""
    cal_dir = FsPath(cal_dir)
    if not cal_dir.exists():
        return []
    tmp, other = [], []
    for p in sorted(cal_dir.rglob("*")):
        rel = p.relative_to(cal_dir).as_posix()
        if p.is_file() and p.name.endswith(TMP_SUFFIX):
            tmp.append(rel)
        elif not (p.is_file() and rel in (CALIBRATION_FILE, EXECUTION_FILE)):
            other.append(rel)
    if other:
        raise StopImplementation(f"unexpected files in the calibration directory: {other}")
    return tmp


def _cal_run_ok(r: object) -> bool:
    if not (isinstance(r, dict) and set(r) == set(CAL_RUN_FIELDS) and _num(r["elapsed_s"])
            and _positive_int(r["workers"]) and isinstance(r["phases"], dict)
            and all(isinstance(k, str) and _num(v) for k, v in r["phases"].items())):
        return False
    v4 = r["v4_eval_time_estimate"]
    return v4 is None or (isinstance(v4, dict) and set(v4) == set(V4_ESTIMATE_FIELDS)
                          and (v4["name"], v4["method"], v4["kind"]) == (V4_ESTIMATE_NAME, V4_ESTIMATE_METHOD,
                                                                        "ESTIMATE") and _num(v4["seconds"]))


def read_calibration_execution(cal_dir: FsPath) -> dict[str, Any] | None:
    """The calibration execution record, or None when absent. Malformed, a schema error or no run: STOP."""
    path = FsPath(cal_dir) / EXECUTION_FILE
    if not path.exists():
        return None
    try:
        ex = json.loads(path.read_bytes())
    except ValueError as exc:
        raise StopImplementation(f"calibration {EXECUTION_FILE} is malformed") from exc
    if not (isinstance(ex, dict) and set(ex) == set(CAL_EXECUTION_FIELDS)
            and ex["schema_version"] == CAL_EXECUTION_SCHEMA and ex["evidence"] == EVIDENCE
            and isinstance(ex["runs"], list) and all(_cal_run_ok(r) for r in ex["runs"])):
        raise StopImplementation(f"calibration {EXECUTION_FILE} schema error")
    if not ex["runs"]:
        raise StopImplementation(f"calibration {EXECUTION_FILE} has no run")
    return ex


def calibration_run_record(started: datetime, finished: datetime, elapsed_s: float, workers: int,
                           phases: Mapping[str, float], v4_estimate: Mapping[str, Any] | None) -> dict[str, Any]:
    return {"started_utc": started.isoformat(), "finished_utc": finished.isoformat(), "elapsed_s": elapsed_s,
            "workers": workers, "phases": dict(phases),
            "v4_eval_time_estimate": dict(v4_estimate) if v4_estimate is not None else None,
            "git": git_identity(), "python": platform.python_version(), "platform": platform.platform()}


def record_calibration_run(cal_dir: FsPath, record: Mapping[str, Any]) -> None:
    """Append one run to the calibration directory's execution.json atomically, keeping earlier runs. The record is
    validated first; a damaged existing file is a STOP and is never rewritten. calibration.json is not touched."""
    scan_calibration_dir(cal_dir)
    if not _cal_run_ok(dict(record)):
        raise StopImplementation("calibration run record schema error")
    ex = read_calibration_execution(cal_dir)
    runs = [*(ex["runs"] if ex is not None else []), dict(record)]
    atomic_write_bytes(FsPath(cal_dir) / EXECUTION_FILE, canonical_bytes(
        {"schema_version": CAL_EXECUTION_SCHEMA, "evidence": EVIDENCE, "runs": runs}))


def v4_eval_time_estimate(cal_dir: FsPath) -> float | None:
    """The V4_EVAL_TIME_ESTIMATE of the latest calibration run that recorded one (for g6_timing), else None."""
    ex = read_calibration_execution(cal_dir)
    for r in reversed(ex["runs"] if ex is not None else []):
        if r["v4_eval_time_estimate"] is not None:
            return float(r["v4_eval_time_estimate"]["seconds"])
    return None


def load_calibration(path: FsPath, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    """calibration.json from disk: canonical bytes, valid, and (when given) the expected sha256. Returns (cal, sha)."""
    raw = FsPath(path).read_bytes()
    try:
        cal = json.loads(raw)
    except ValueError as exc:
        raise StopImplementation(f"{CALIBRATION_FILE} is malformed") from exc
    if not isinstance(cal, dict) or canonical_bytes(cal) != raw:
        raise StopImplementation(f"{CALIBRATION_FILE} is not canonical")
    validate_calibration(cal)
    sha = _sha256(raw)
    if expected_sha256 is not None and sha != expected_sha256:
        raise StopImplementation(f"{CALIBRATION_FILE} sha256 {sha} is not the expected {expected_sha256}")
    return cal, sha


def calibration_provenance(cal: Mapping[str, Any], sha256: str) -> dict[str, Any]:
    """run_inputs.calibration_provenance: the calibration kind, its file sha256 and the E1 values it fixes."""
    if _sha256(calibration_bytes(cal)) != sha256:
        raise StopImplementation("calibration sha256 does not match its bytes")
    return {"kind": cal["kind"], "calibration_sha256": sha256, "edge_annual": cal["e1"]["edge_annual"],
            "sigma_pop": cal["e1"]["sigma_pop"]}


def research_e1_cell(cal: Mapping[str, Any]) -> CellSpec:
    """The E1 cell of a research run. A TEST_FIXTURE calibration is never a research input (STOP)."""
    validate_calibration(cal)
    if cal["kind"] != RESEARCH:
        raise StopImplementation("a TEST_FIXTURE calibration is not a research input")
    return e1_cell(cal["e1"]["edge_annual"], cal["e1"]["sigma_pop"])


# --- G3b-5-2: records, rejection indicators and paired contrasts (DC8, STATISTICAL_HYPOTHESES) -------------------

E1_CELL, P0_CELL = CORE_CELLS
# contrast: (cell, (window, base indicator), (window, other indicator)); D = r(base) - r(other)
CONTRASTS = {"V-1_lo": (E1_CELL, ("f12", "V0"), ("f12", "S1_lo")),
             "V-1_hi": (E1_CELL, ("f12", "V0"), ("f12", "S1_hi")),
             "V-2": (E1_CELL, ("f12", "V0"), ("f12", "V0d")),
             "V-3": (E1_CELL, ("f36", "V0"), ("f36", "V0b60")),
             "V-8": (P0_CELL, ("f12", "V0"), ("conf", "V0"))}
INDICATORS = ("V0", "V0d", "V0b60", "S1_lo", "S1_hi")


def read_records(run_dir: FsPath, spec: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Every record of a run whose units verify, by cell, in (rep, window) order."""
    run_dir = FsPath(run_dir)
    _, _, spec_sha, inputs_sha = _load_spec_inputs(run_dir)
    out: dict[str, list[dict[str, Any]]] = {c: [] for c in spec["cells"]}
    for cell, k, s, e in _expected_units(spec):
        verify_unit(run_dir, spec, cell, k, s, e, spec_sha, inputs_sha)
        out[cell] += [json.loads(line) for line in unit_paths(run_dir, cell, k)[0].read_bytes().splitlines()]
    return out


def rejects(rec: Mapping[str, Any], indicator: str) -> bool:
    """I_v = 1{p_v <= 0.05} (DC8). S1_lo / S1_hi: S1 with p_lo / p_hi (DC4.1, H-V1)."""
    v = rec["variants"]
    p = v["S1"]["p_lo"] if indicator == "S1_lo" else v["S1"]["p_hi"] if indicator == "S1_hi" else v[indicator]["p"]
    return bool(p <= PRIMARY_ALPHA)


def window_records(by_cell: Mapping[str, Sequence[Mapping[str, Any]]], cell: str, window: str,
                   reps: int | None = None) -> list[Mapping[str, Any]]:
    """The records of (cell, window), one per rep 0 .. R - 1 in order; a required item missing is a STOP."""
    recs = [r for r in by_cell.get(cell, []) if r["window"] == window]
    n = len(recs) if reps is None else reps
    if not recs or [r["rep"] for r in recs] != list(range(n)):
        raise StopImplementation(f"required records missing: {cell} {window} reps 0..{n - 1}")
    return recs


def paired_indicators(by_cell: Mapping[str, Sequence[Mapping[str, Any]]], contrast: str,
                      reps: int | None = None) -> tuple[list[bool], list[bool]]:
    cell, (w_a, v_a), (w_b, v_b) = CONTRASTS[contrast]
    a, b = window_records(by_cell, cell, w_a, reps), window_records(by_cell, cell, w_b, reps)
    if len(a) != len(b):
        raise StopImplementation(f"{contrast}: windows have different replication counts")
    return [rejects(r, v_a) for r in a], [rejects(r, v_b) for r in b]


# --- G3b-5-2: G6 pilot audit, nuisance values only (WO:69, DC11, DC12, PD-5, preregistration 7) ------------------
#
# <pilot run>/g6/g6_summary.json   canonical JSON: discordance counts, pi_U, R_h, R_c, PD-5 degeneracy shares, P2
#                                  spells and the calibration's sigma interval; references the pilot's run_spec,
#                                  run_inputs, manifest and SHA256SUMS sha256. No rejection rate, contrast, p-value
#                                  or label (effect values are G8a only). No time: the budget judgment uses times,
#                                  so it is execution.json's g6_timing.
# <pilot run>/g6/SHA256SUMS        that file only. Both written once; existing bytes must be identical.

G6_DIR, G6_SUMMARY_FILE = "g6", "g6_summary.json"
G6_FILES = (G6_SUMMARY_FILE, SUMS_FILE)
G6_SCHEMA = "moneylab.bt4_futility_diag.g6_summary/1"
G6_FIELDS = ("schema_version", "study_id", "evidence", "content", "pilot", "calibration", "r_c", "pd5", "p2_spell",
             "stop_for_user_decision", "P0_CONF_CHECK")
G6_CONTENT = "NUISANCE_ONLY (DC11): no rejection rate, contrast, p-value or label"
PILOT_REPS = 200                   # config core.pilot_reps_per_cell
R_C_HYPOTHESES = {E1_CELL: ("V-1", "V-2", "V-3"), P0_CELL: ("V-8",)}      # ERRATA-003 R-6
PD5_WINDOWS = ("f12", "f36")
PD5_MAX_SPLIT, PD5_MAX_ND_FLAG, PD5_MAX_SD = 0.02, 0.05, 0.05             # config degeneracy.pilot_stop_*
P2_WINDOW = "conf"
P2_OK, P2_UNDEFINED, P2_INVALID = "OK", "P2_UNDEFINED", "P2_INVALID"


def pilot_r_c(by_cell: Mapping[str, Sequence[Mapping[str, Any]]], n: int) -> dict[str, Any]:
    """DC12 from the pilot discordance counts only: pi_U = Clopper-Pearson one-sided 95% upper(x_disc, n),
    R_h = required_reps(pi_U), V-1 x_disc = max(x_lo, x_hi); R_c = max over the cell's hypotheses (ERRATA-003 R-6).
    Only the discordant total enters (no direction). R_c > 40,000 is listed for the STOP."""
    disc = {}
    for name in CONTRASTS:
        a, b = paired_indicators(by_cell, name, n)
        disc[name] = sum(1 for x, y in zip(a, b) if x != y)
    hyp: dict[str, dict[str, Any]] = {
        "V-1": {"x_lo": disc["V-1_lo"], "x_hi": disc["V-1_hi"], "x_disc": max(disc["V-1_lo"], disc["V-1_hi"])},
        "V-2": {"x_disc": disc["V-2"]}, "V-3": {"x_disc": disc["V-3"]}, "V-8": {"x_disc": disc["V-8"]}}
    for h in hyp.values():
        h["pi_upper"] = clopper_pearson_upper(h["x_disc"], n)
        h["r_h"] = required_reps(h["pi_upper"])[0]
    r_c = {c: max(hyp[h]["r_h"] for h in hs) for c, hs in R_C_HYPOTHESES.items()}
    return {"n": n, "hypotheses": hyp, "r_c": r_c, "over_max": sorted(c for c, r in r_c.items() if r > R_MAX)}


def pd5_degeneracy(by_cell: Mapping[str, Sequence[Mapping[str, Any]]], n: int) -> dict[str, Any]:
    """PD-5 on E1 f12 and f36: shares of replications whose S1 p_lo / p_hi rejection decisions differ, with an ND flag
    and with SD. Any share strictly above 0.02 / 0.05 / 0.05 is a STOP_FOR_USER_DECISION."""
    out: dict[str, Any] = {}
    for w in PD5_WINDOWS:
        recs = window_records(by_cell, E1_CELL, w, n)
        out[w] = {"lo_hi_split": sum(1 for r in recs if rejects(r, "S1_lo") != rejects(r, "S1_hi")) / n,
                  "nd_flag": sum(1 for r in recs if r["variants"]["S1"]["nd_flag"]) / n,
                  "sd": sum(1 for r in recs if r["sd"]) / n}
    stop = any(v["lo_hi_split"] > PD5_MAX_SPLIT or v["nd_flag"] > PD5_MAX_ND_FLAG or v["sd"] > PD5_MAX_SD
               for v in out.values())
    return {"windows": out, "thresholds": {"lo_hi_split": PD5_MAX_SPLIT, "nd_flag": PD5_MAX_ND_FLAG,
                                           "sd": PD5_MAX_SD}, "stop": stop}


P0_CONF_WINDOW, P0_CONF_PASS, P0_CONF_STOP = "conf", "PASS", "STOP"


def p0_conf_check(by_cell: Mapping[str, Sequence[Mapping[str, Any]]], n: int, alpha: float = PRIMARY_ALPHA) -> str:
    """ERRATA-005 R-8 [B-STAT] (WO:455): p_hat = share of the n pilot replications whose P0 conf V0 rejects
    (I = 1{p_V0 <= alpha}, DC8), SE = sqrt(alpha (1 - alpha) / n) under the null, PASS iff |p_hat - alpha| <= 3 SE
    (boundary PASS, no rounding), else STOP. Only the label leaves this function: the rate is part of the V-8 effect
    (DC11, WO:69) and is never stored or reported."""
    recs = window_records(by_cell, P0_CELL, P0_CONF_WINDOW, n)
    p_hat = sum(1 for r in recs if rejects(r, "V0")) / n
    return P0_CONF_PASS if abs(p_hat - alpha) <= 3 * math.sqrt(alpha * (1 - alpha) / n) else P0_CONF_STOP


def e1_window_positions(edge_annual: float, seed: int, window: str = P2_WINDOW) -> list[int]:
    """M60 E0 positions (1 hold, 0 cash) on one window of the E1 path from this seed: the same path the records
    were computed on, regenerated (records do not keep positions)."""
    path = make_path(replace(E1_DGP, edge_annual=edge_annual), path_days(), seed)
    sig = signals(path.log_close, *STRATEGIES[E1_STRATEGY])
    return segment_market_positions(path, sig, "E0", *window_bounds()[window])[1]


def interior_spells(positions: Sequence[int]) -> list[tuple[int, int]]:
    """(state, length) of every maximal run, without the truncated first and last ones."""
    runs: list[list[int]] = []
    for p in positions:
        if runs and runs[-1][0] == p:
            runs[-1][1] += 1
        else:
            runs.append([p, 1])
    return [(s, n) for s, n in runs[1:-1]]


def p2_spell(position_paths: Iterable[Sequence[int]]) -> dict[str, Any]:
    """Preregistration 7 P2 rule: pooled arithmetic mean of hold / cash spell lengths over every pilot replication,
    round half up (floor(x + 0.5)), transition probability 1 / rounded mean in (0, 1]. No spell of a state:
    P2_UNDEFINED; a probability outside (0, 1]: P2_INVALID. No default substitution."""
    lengths: dict[int, list[int]] = {1: [], 0: []}
    for pos in position_paths:
        for state, length in interior_spells(pos):
            lengths[state].append(length)
    out: dict[str, Any] = {}
    undefined = invalid = False
    for name, state in (("hold", 1), ("cash", 0)):
        ls = lengths[state]
        if not ls:
            undefined = True
            out[name] = {"spells": 0, "mean": None, "rounded": None, "transition_probability": None}
            continue
        m = sum(ls) / len(ls)
        rounded = math.floor(m + 0.5)
        prob = 1.0 / rounded if rounded > 0 else None
        invalid |= prob is None or not 0.0 < prob <= 1.0
        out[name] = {"spells": len(ls), "mean": m, "rounded": rounded, "transition_probability": prob}
    return {"status": P2_UNDEFINED if undefined else P2_INVALID if invalid else P2_OK, **out}


def g6_summary(run_dir: FsPath, calibration: Mapping[str, Any], calibration_sha256: str) -> dict[str, Any]:
    """The G6 nuisance summary of a COMPLETE pilot run made with this calibration (run_inputs must name it)."""
    run_dir = FsPath(run_dir)
    if verify_run(run_dir)["status"] != "COMPLETE":
        raise StopImplementation("G6 needs a COMPLETE pilot run")
    spec, inputs, spec_sha, inputs_sha = _load_spec_inputs(run_dir)
    if spec["mode"] != "pilot" or list(spec["cells"]) != list(CORE_CELLS):
        raise StopImplementation("G6 summarizes a pilot run of both CORE cells")
    if inputs["calibration_provenance"] != calibration_provenance(calibration, calibration_sha256):
        raise StopImplementation("the pilot's run_inputs do not name this calibration")
    e1 = inputs["cells"][E1_CELL]
    if (e1["edge_annual"], e1["sigma_pop"]) != (calibration["e1"]["edge_annual"], calibration["e1"]["sigma_pop"]):
        raise StopImplementation("the pilot's E1 cell is not the calibration's")
    n = spec["reps"]
    if calibration["kind"] == RESEARCH and (n != PILOT_REPS or inputs["namespace"] != "FUTDIAG-PILOT"):
        raise StopImplementation("a research pilot has 200 replications per cell in FUTDIAG-PILOT")
    by_cell = read_records(run_dir, spec)
    r_c = pilot_r_c(by_cell, n)
    pd5 = pd5_degeneracy(by_cell, n)
    window_records(by_cell, E1_CELL, P2_WINDOW, n)
    p2 = p2_spell(e1_window_positions(e1["edge_annual"],
                                      seed_for(seed_path(inputs["namespace"], E1_CELL, i, PATH_WINDOW, PATH_RULE)))
                  for i in range(n))
    sg = calibration["sigma"]
    stops = (["R_C_OVER_MAX"] if r_c["over_max"] else []) + (["PD5_DEGENERACY"] if pd5["stop"] else []) \
        + ([p2["status"] + " (P2 / G5X only, CORE G7 not blocked)"] if p2["status"] != P2_OK else [])
    return {"schema_version": G6_SCHEMA, "study_id": STUDY_ID, "evidence": EVIDENCE, "content": G6_CONTENT,
            "pilot": {"run_spec_sha256": spec_sha, "run_inputs_sha256": inputs_sha,
                      "manifest_sha256": sha256_file(run_dir / MANIFEST_FILE),
                      "sha256sums_sha256": sha256_file(run_dir / SUMS_FILE), "mode": spec["mode"],
                      "namespace": inputs["namespace"], "reps": n, "bootstrap": spec["bootstrap"],
                      "unit_size": spec["unit_size"]},                    # ERRATA-004 R-4
            "calibration": {"sha256": calibration_sha256, "kind": calibration["kind"],
                            "edge_annual": calibration["e1"]["edge_annual"],
                            "achieved_sharpe": calibration["e1"]["achieved_sharpe"],
                            "sigma_pop": calibration["e1"]["sigma_pop"],
                            "sigma": {k: sg[k] for k in ("namespace", "reps", "sigma_hat", "kappa_hat", "sigma_L",
                                                         "sigma_U")}},
            "r_c": r_c, "pd5": pd5, "p2_spell": p2, "stop_for_user_decision": stops,
            "P0_CONF_CHECK": p0_conf_check(by_cell, n)}                   # ERRATA-005 R-8: label only


def _g6_files(run_dir: FsPath) -> list[str]:
    g6 = FsPath(run_dir) / G6_DIR
    return sorted(name for name in G6_FILES if (g6 / name).exists())


def g6_sums_bytes(summary_bytes: bytes) -> bytes:
    return f"{_sha256(summary_bytes)}  {G6_SUMMARY_FILE}\n".encode("utf-8")


def write_g6(run_dir: FsPath, calibration: Mapping[str, Any], calibration_sha256: str) -> dict[str, Any]:
    """Write g6/g6_summary.json then g6/SHA256SUMS. A rerun recomputes and must produce the same bytes (STOP
    otherwise); a damaged g6/ STOPs in verify_run first and is never rewritten. The pilot's files are untouched."""
    run_dir = FsPath(run_dir)
    summary = g6_summary(run_dir, calibration, calibration_sha256)
    data = canonical_bytes(summary)
    g6 = run_dir / G6_DIR
    _write_or_compare(g6 / G6_SUMMARY_FILE, data, "g6 summary")
    _write_or_compare(g6 / SUMS_FILE, g6_sums_bytes(data), "g6 SHA256SUMS")
    return summary


def verify_g6(run_dir: FsPath, spec: Mapping[str, Any], spec_sha: str, inputs_sha: str) -> str:
    """ABSENT / VERIFIED / INCOMPLETE (summary without its SHA256SUMS: the write was interrupted; write_g6 finishes
    it). SHA256SUMS without the summary, non-canonical or foreign content, or references that are not this pilot's
    files: STOP."""
    run_dir = FsPath(run_dir)
    present = _g6_files(run_dir)
    if not present:
        return "ABSENT"
    if G6_SUMMARY_FILE not in present:
        raise StopImplementation("g6/SHA256SUMS without g6/g6_summary.json")
    raw = (run_dir / G6_DIR / G6_SUMMARY_FILE).read_bytes()
    try:
        summary = json.loads(raw)
    except ValueError as exc:
        raise StopImplementation("g6/g6_summary.json is malformed") from exc
    if not (isinstance(summary, dict) and canonical_bytes(summary) == raw and set(summary) == set(G6_FIELDS)
            and summary["schema_version"] == G6_SCHEMA and summary["content"] == G6_CONTENT
            and spec["mode"] == "pilot"):
        raise StopImplementation("g6/g6_summary.json is not a canonical G6 summary of a pilot run")
    pilot = summary["pilot"]
    if (pilot.get("run_spec_sha256"), pilot.get("run_inputs_sha256"), pilot.get("manifest_sha256"),
            pilot.get("sha256sums_sha256"), pilot.get("unit_size")) != (
            spec_sha, inputs_sha, sha256_file(run_dir / MANIFEST_FILE), sha256_file(run_dir / SUMS_FILE),
            spec["unit_size"]):
        raise StopImplementation("g6/g6_summary.json does not reference this pilot's files")
    if SUMS_FILE not in present:
        return "INCOMPLETE"
    if (run_dir / G6_DIR / SUMS_FILE).read_bytes() != g6_sums_bytes(raw):
        raise StopImplementation("g6/SHA256SUMS does not match g6/g6_summary.json")
    return "VERIFIED"


def check_g7_unit_size(pilot_run_dir: FsPath, core_spec: Mapping[str, Any]) -> int:
    """ERRATA-004 R-4 G7 CORE entry gate: the CORE run_spec.unit_size must equal the pilot unit_size recorded in the
    pilot's VERIFIED g6/g6_summary.json (ERRATA-003 R-2 "G7과 같은 unit_size"); otherwise STOP. Read-only; the pilot
    run_spec and manifest are untouched and G6 never needed a G7 run_spec. Returns the unit_size."""
    validate_run_spec(core_spec)
    if core_spec["mode"] != "core":
        raise StopImplementation("the G7 unit_size gate takes a CORE run_spec")
    status = verify_run(pilot_run_dir)
    if status["status"] != "COMPLETE" or status["g6"] != "VERIFIED":
        raise StopImplementation("the G7 unit_size gate needs a COMPLETE pilot with a VERIFIED g6/")
    unit_size = json.loads((FsPath(pilot_run_dir) / G6_DIR / G6_SUMMARY_FILE).read_bytes())["pilot"]["unit_size"]
    if core_spec["unit_size"] != unit_size:
        raise StopImplementation(f"G7 CORE unit_size {core_spec['unit_size']!r} differs from the pilot's "
                                 f"{unit_size!r} fixed at G6 (ERRATA-004 R-4)")
    return int(unit_size)


# --- G3b-5-2: G6 timing and budget judgment (ERRATA-003 R-1..R-5), execution.json only ------------------------------

SAFETY_FACTOR = 1.3                # config budget.safety_factor
CORE_MAX_WORKERS = 12              # config budget.core_max_workers
CORE_MAX_WORKER_HOURS = 1152       # config budget.core_max_worker_hours
CORE_MAX_WALLTIME_HOURS = 96       # config budget.core_max_walltime_hours


def budget_ok(worker_hours: float, wall_hours: float) -> bool:
    """WO:417-419: both W <= 1,152 and wall <= 96 ("<=", no rounding)."""
    return worker_hours <= CORE_MAX_WORKER_HOURS and wall_hours <= CORE_MAX_WALLTIME_HOURS


def _valid_time(t: object) -> bool:
    return isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t) and t >= 0


def t_upper(times: Sequence[float]) -> float:
    """ERRATA-003 R-1: t_hat = mean + t_{0.95, n-1} sd(ddof 1) / sqrt(n); mean when sd = 0. A missing, non-finite
    or negative time is a STOP_FOR_USER_DECISION (nothing substituted)."""
    n = len(times)
    if n < 2 or not all(_valid_time(t) for t in times):
        raise StopForUserDecision(f"per-replication times invalid or fewer than two ({n})")
    m, s = mean(times), sd(times)
    return m if s == 0.0 else m + t_ppf(0.95, n - 1) * s / math.sqrt(n)


def g6_timing(ex: Mapping[str, Any], spec: Mapping[str, Any], r_c: Mapping[str, int],
              workers_required: int = CORE_MAX_WORKERS, v4_eval_estimate_s: float | None = None) -> dict[str, Any]:
    """ERRATA-003 R-1..R-3 G6 budget judgment from the pilot's execution record. The pilot ran in ONE complete
    session with w = 12 workers and computed every unit there; otherwise T_wall is undefined (STOP_FOR_USER_DECISION).
    eta_hat = sum of all per-rep times / (w T_wall), used only in (0, 1] (never capped);
    W = sum_c R_c t_hat_c 1.3 / 3600 <= 1,152 and wall = W / (12 eta_hat) <= 96 (no rounding). Calibration time is
    not in W; the V-4 evaluation estimate (G5 calibration's 4,000-year single-path time) is reported separately."""
    sessions = ex["sessions"]
    if len(sessions) != 1:
        raise StopForUserDecision(f"the pilot ran in {len(sessions)} sessions; T_wall needs exactly one")
    s = sessions[0]
    if s["end"] is None:
        raise StopForUserDecision(f"{INCOMPLETE_TIME}: the pilot session has no end record")
    if s["end"]["stop"] is not None or s["workers"] != workers_required:
        raise StopForUserDecision(f"the pilot session must finish with {workers_required} workers")
    if [(u["cell"], u["unit"]) for u in s["units"]] != [(c, k) for c, k, _, _ in _expected_units(spec)]:
        raise StopForUserDecision("the pilot session did not compute every unit itself")
    if set(r_c) != set(spec["cells"]):
        raise StopImplementation("R_c must cover exactly the pilot cells")
    times = {c: [t for u in s["units"] if u["cell"] == c for t in u["rep_seconds"]] for c in spec["cells"]}
    if any(len(v) != spec["reps"] for v in times.values()):
        raise StopForUserDecision("per-replication times missing")
    t_hat = {c: t_upper(v) for c, v in times.items()}
    total = sum(t for v in times.values() for t in v)
    t_wall, w = s["units"][-1]["elapsed_s"], s["workers"]
    eta = total / (w * t_wall) if _valid_time(t_wall) and t_wall > 0 else math.nan
    if not (math.isfinite(eta) and 0.0 < eta <= 1.0):
        raise StopForUserDecision(f"eta_hat = {eta!r} is not in (0, 1]; not capped")
    worker_hours = sum(r_c[c] * t_hat[c] for c in spec["cells"]) * SAFETY_FACTOR / 3600
    wall_hours = worker_hours / (CORE_MAX_WORKERS * eta)
    return {"t_hat_s": t_hat, "n_reps": {c: len(v) for c, v in times.items()}, "sum_t_s": total, "t_wall_s": t_wall,
            "workers": w, "eta_hat": eta, "r_c": dict(r_c), "worker_hours": worker_hours, "wall_hours": wall_hours,
            "expected_wall_s": wall_hours * 3600,
            "limits": {"worker_hours": CORE_MAX_WORKER_HOURS, "wall_hours": CORE_MAX_WALLTIME_HOURS},
            "budget_pass": budget_ok(worker_hours, wall_hours),
            "diagnostic": {"init_s": s["init_s"], "finalize_s": s["end"]["finalize_s"]},
            "v4_eval_estimate_s": v4_eval_estimate_s,
            "v4_eval_estimate_kind": "ESTIMATE" if v4_eval_estimate_s is not None else "NOT_RECORDED"}


def write_g6_timing(run_dir: FsPath, workers_required: int = CORE_MAX_WORKERS,
                    v4_eval_estimate_s: float | None = None) -> dict[str, Any]:
    """Add g6_timing to execution.json once, from the verified g6 summary's R_c. A rerun recomputes it from the
    same records and must be equal (STOP otherwise). Over budget is recorded with budget_pass = false: STOP and ask
    for a contract decision (WO:419)."""
    run_dir = FsPath(run_dir)
    status = verify_run(run_dir)
    if status["status"] != "COMPLETE" or status["g6"] != "VERIFIED":
        raise StopImplementation("g6_timing needs a COMPLETE pilot with a VERIFIED g6/")
    spec, _, _, _ = _load_spec_inputs(run_dir)
    r_c = json.loads((run_dir / G6_DIR / G6_SUMMARY_FILE).read_bytes())["r_c"]["r_c"]
    ex = read_execution(run_dir)
    assert ex is not None
    timing = g6_timing(ex, spec, r_c, workers_required, v4_eval_estimate_s)
    if G6_TIMING_KEY in ex:
        if ex[G6_TIMING_KEY] != json.loads(canonical_bytes(timing)):
            raise StopImplementation("execution.json g6_timing differs from the recomputed one")
        return timing
    _save_execution(run_dir, ex["sessions"], **{G6_TIMING_KEY: timing})
    return timing


# --- ERRATA-004 R-5: what a G7 research manifest may fix from G6, and the g6_timing revalidation ---------------------
#
# Builders and checks only: the G7 manifest schema and the G7 run layout stay open (ERRATA-004 O-1..O-3).

TIME_KEYS = ("t_hat_s", "eta_hat", "worker_hours", "wall_hours", "expected_wall_s", "t_wall_s", "sum_t_s",
             "budget_pass", "elapsed_s", "cumulative_s", "seconds")
G6_TIMING_REFERENCE = {"file": EXECUTION_FILE, "key": G6_TIMING_KEY}


def _verified_g6(pilot_run_dir: FsPath) -> tuple[dict[str, Any], str]:
    status = verify_run(pilot_run_dir)
    if status["status"] != "COMPLETE" or status["g6"] != "VERIFIED":
        raise StopImplementation("needs a COMPLETE pilot with a VERIFIED g6/")
    raw = (FsPath(pilot_run_dir) / G6_DIR / G6_SUMMARY_FILE).read_bytes()
    return json.loads(raw), _sha256(raw)


def g7_manifest_g6_section(pilot_run_dir: FsPath) -> dict[str, Any]:
    """ERRATA-004 R-5: the deterministic G6 values a G7 research manifest fixes: the g6 summary sha256, the G5 pilot
    sha256 it references, the pilot unit_size, the nuisance values (R_c, sigma interval, PD-5, P2 status) and the R_c
    inputs. No time, expected or actual wall-clock, t_hat, eta_hat, W or budget judgment, and no execution.json
    hash: only a deterministic reference to where g6_timing is (that file, that key)."""
    summary, sha = _verified_g6(pilot_run_dir)
    pilot, r_c = summary["pilot"], summary["r_c"]
    section = {"g6_summary_sha256": sha,
               "pilot": {k: pilot[k] for k in ("run_spec_sha256", "run_inputs_sha256", "manifest_sha256",
                                               "sha256sums_sha256")},
               "unit_size": pilot["unit_size"],
               "nuisance": {"r_c": r_c["r_c"], "r_c_over_max": r_c["over_max"],
                            "sigma": summary["calibration"]["sigma"], "pd5": summary["pd5"],
                            "p2_status": summary["p2_spell"]["status"]},
               "r_c_inputs": {"n": r_c["n"], "hypotheses": {h: {k: v[k] for k in v if k in ("x_lo", "x_hi", "x_disc")}
                                                            for h, v in r_c["hypotheses"].items()}},
               "g6_timing_reference": dict(G6_TIMING_REFERENCE)}
    if set(TIME_KEYS) & _all_keys(section):
        raise StopImplementation("a G7 manifest section must not carry time values")
    return section


def _all_keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _all_keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _all_keys(v)}
    return set()


def revalidate_g6_timing(pilot_run_dir: FsPath, workers_required: int = CORE_MAX_WORKERS) -> dict[str, Any]:
    """ERRATA-004 R-5 G7 entry check: recompute g6_timing from the pilot execution.json session records (and the
    recorded V-4 estimate, which no session holds) and require it to equal the recorded one; otherwise STOP."""
    summary, _ = _verified_g6(pilot_run_dir)
    spec, _, _, _ = _load_spec_inputs(FsPath(pilot_run_dir))
    ex = read_execution(pilot_run_dir)
    if ex is None or G6_TIMING_KEY not in ex:
        raise StopImplementation("the pilot execution.json has no g6_timing")
    recorded = ex[G6_TIMING_KEY]
    timing = g6_timing(ex, spec, summary["r_c"]["r_c"], workers_required, recorded.get("v4_eval_estimate_s"))
    if json.loads(canonical_bytes(timing)) != recorded:
        raise StopImplementation("g6_timing recomputed from the pilot sessions differs from the recorded one")
    return recorded


# --- ERRATA-004 R-6: the CORE global budget over every CORE run (structure: O-1; where it is kept: O-3) --------------

def g6_expected_wall_s(timing: Mapping[str, Any]) -> float:
    """Expected wall-clock in seconds from the G6 worker-hours: W_G6 / (12 eta_hat) hours (WO:418)."""
    return float(timing["worker_hours"]) / (CORE_MAX_WORKERS * float(timing["eta_hat"])) * 3600


def core_global_budget(runs: Mapping[str, tuple[Sequence[str], Mapping[str, Any] | None]],
                       timing: Mapping[str, Any], concurrent_workers: Sequence[int]) -> dict[str, Any]:
    """ERRATA-004 R-6. runs: label -> (CORE cells the run covers, its execution.json or None if not started); one
    run for both cells or one per cell (O-1 is not decided here), together covering each CORE cell exactly once.
    T_CORE = sum of every run's cumulative session elapsed (ERRATA-003 R-4; resumed sessions add up, no session
    counted twice, V-4 time is in no CORE run). exceeded: T_CORE > 1.5 x W_G6 / (12 eta_hat) (exactly 1.5 x passes).
    Concurrent CORE workers above 12 in total, or cells not covered exactly once, STOP."""
    if sum(concurrent_workers) > CORE_MAX_WORKERS or any(not _positive_int(w) for w in concurrent_workers):
        raise StopImplementation(f"concurrent CORE workers {list(concurrent_workers)} exceed {CORE_MAX_WORKERS}")
    for label, (cells, _) in runs.items():
        if not cells or not set(cells) <= set(CORE_CELLS):
            raise StopImplementation(f"run {label!r} is not a CORE run (V-4 and other stages are never in T_CORE)")
    covered = [c for cells, _ in runs.values() for c in cells]
    if sorted(covered) != sorted(CORE_CELLS):
        raise StopImplementation(f"the global budget must cover each CORE cell exactly once, got {covered}")
    seen: set[bytes] = set()
    per_run: dict[str, dict[str, Any]] = {}
    complete = True
    for label, (_, ex) in runs.items():
        for s in (ex["sessions"] if ex is not None else []):
            key = canonical_bytes(s)
            if key in seen:
                raise StopImplementation(f"run {label!r}: a session is counted twice")
            seen.add(key)
        acct = time_accounting(ex) if ex is not None else None
        per_run[label] = {"cumulative_s": acct["cumulative_s"] if acct else 0.0,
                          "time_accounting": acct["status"] if acct else "NOT_STARTED"}
        complete &= acct is None or acct["status"] == "COMPLETE"
    total = sum(float(r["cumulative_s"]) for r in per_run.values())
    expected = g6_expected_wall_s(timing)
    exceeded = wall_exceeded(total, expected)
    return {"t_core_cumulative_s": total, "per_run": per_run, "expected_wall_s": expected,
            "limit_s": RUNTIME_STOP_MULTIPLE * expected, "exceeded": exceeded, "time_accounting_complete": complete,
            "lower_bound": not complete, "budget_pass_allowed": complete and not exceeded}


def g7_budget_gate(budget: Mapping[str, Any] | None) -> None:
    """G7 may start (or resume) only with a global budget result: none (not wired) or incomplete time accounting
    is a STOP_FOR_USER_DECISION, an exceeded budget a STOP."""
    if budget is None:
        raise StopForUserDecision("the CORE global budget check is not wired: G7 must not start (ERRATA-004 R-6)")
    if budget["exceeded"]:
        raise StopImplementation(f"CORE global wall-clock {budget['t_core_cumulative_s']!r} s > "
                                 f"{budget['limit_s']!r} s")
    if not budget["time_accounting_complete"]:
        raise StopForUserDecision(f"{INCOMPLETE_TIME}: the CORE cumulative is a lower bound; no budget PASS")


# --- G3b-5-2: CORE decision summary (STATISTICAL_HYPOTHESES, 판정 규칙; G8a function, not run or stored here) --------

V4_EVAL_YEARS = 4000               # config core.v4_eval_years


def v4_evaluation(years: int = V4_EVAL_YEARS, seed_parts: Sequence[str] = V4_EVAL_SEED_PARTS,
                  edge_annual: float = E_CAL) -> dict[str, Any]:
    """H-V4 input: SR_eval = _target_sharpe(path, "M60", "E0") on the e_cal path from seed_parts (the same segment as
    calibrate_e1) and the K = 40 contiguous batch Sharpes of those returns (100-year batches for 4,000 years)."""
    if not _positive_int(years):
        raise StopImplementation(f"years must be a positive int, got {years!r}")
    parts = list(validate_seed_parts(seed_parts))
    path = make_path(replace(E1_DGP, edge_annual=edge_annual), years * 365, explicit_seed(parts))
    rets = window_e0_returns(path, signals(path.log_close, *STRATEGIES[E1_STRATEGY]), min_warmup() + 1,
                             path.days - 1, Costs().log_costs()["E0"])
    values, lengths = batch_sharpes(rets, V4_BATCHES)
    return {"years": years, "seed_parts": parts, "edge_annual": edge_annual,
            "sr_eval": finite_or_stop(annual_sharpe(rets), "SR_eval"), "batch_sharpes": values,
            "batch_lengths": lengths}


def _contrast_dict(c: Contrast) -> dict[str, Any]:
    return {"d_hat": c.d_hat, "se": c.se, "p_one_sided": c.p_one_sided, "u_d": c.upper, "n10": c.n10, "n01": c.n01,
            "reason": c.reason}


def label_v4(holm_rejected: bool, delta_hat: float, delta_lower: float, sigma_lo: float,
             sigma_hi: float) -> tuple[str, str | None]:
    """H-V4: outside |Delta|/sigma_L <= 0.5 at most INCONCLUSIVE (APPROX_OUT_OF_RANGE); SUPPORTED = Holm rejection and
    min over sigma of DeltaRej(Delta_hat, sigma) >= 0.01; WEAKENED = DeltaRej_max over {L_Delta} x {sigma_L,
    sigma_U} < 0.01."""
    if not v4_approx_ok(delta_hat, sigma_lo):
        return INCONCLUSIVE, "APPROX_OUT_OF_RANGE"
    if holm_rejected and v4_effect_gate(delta_hat, sigma_lo, sigma_hi) >= MIN_EFFECT:
        return SUPPORTED, None
    if v4_weakened_max(delta_lower, sigma_lo, sigma_hi) < MIN_EFFECT:
        return WEAKENED, None
    return INCONCLUSIVE, None


def decision_summary(by_cell: Mapping[str, Sequence[Mapping[str, Any]]], v4: Mapping[str, Any],
                     sigma: Mapping[str, Any]) -> dict[str, Any]:
    """The preregistered CORE decisions (G8a): rejection rates with MC SE sqrt(r(1-r)/R), the McNemar contrasts
    (D, SE, one-sided p, U_D), EFF, Holm over the five primary p (V-1 uses p1 from D1_lo) at FWER 0.025, and the
    labels of V-1 (DEGENERACY_AMBIGUOUS from the hi treatment), V-2, V-3, V-8 (r(f12) - 0.05 >= 0.01) and V-4.
    sigma is the calibration's sigma section (sigma_L, sigma_U). Every required item missing is a STOP."""
    if v4 is None or sigma is None:
        raise StopImplementation("V-4 evaluation and sigma interval are required")
    rates: dict[str, Any] = {}
    for cell, recs in by_cell.items():
        for w in [w for w in WINDOWS if any(r["window"] == w for r in recs)]:
            wr = window_records(by_cell, cell, w)
            n = len(wr)
            for ind in INDICATORS:
                r = sum(1 for x in wr if rejects(x, ind)) / n
                rates.setdefault(cell, {}).setdefault(w, {})[ind] = {"rate": r, "mc_se": math.sqrt(r * (1 - r) / n),
                                                                     "reps": n}
    con = {name: mcnemar(*paired_indicators(by_cell, name)) for name in CONTRASTS}
    r_v0 = {w: rates[E1_CELL][w]["V0"]["rate"] for w in ("f12", "f36")}
    r_p0_f12 = rates[P0_CELL]["f12"]["V0"]["rate"]
    eff = {"V-1": eff_threshold(r_v0["f12"]), "V-2": eff_threshold(r_v0["f12"]), "V-3": eff_threshold(r_v0["f36"]),
           "V-8": eff_threshold(r_p0_f12)}
    inf = v4_inference(v4["sr_eval"], CORE_THETA, v4["batch_sharpes"])
    pvals = {"V-1": con["V-1_lo"].p_one_sided, "V-2": con["V-2"].p_one_sided, "V-3": con["V-3"].p_one_sided,
             "V-8": con["V-8"].p_one_sided, "V-4": inf.p_one_sided}
    holm = holm_rejections(pvals)
    holm_hi = holm_rejections({**pvals, "V-1": con["V-1_hi"].p_one_sided})["V-1"]
    s_lo, s_hi = sigma["sigma_L"], sigma["sigma_U"]
    v1 = label_v1(holm["V-1"], con["V-1_lo"], con["V-1_hi"], eff["V-1"], holm_hi)
    v8_extra = r_p0_f12 - PRIMARY_ALPHA >= MIN_EFFECT
    labels = {"V-1": {"label": v1[0], "reason": v1[1]},
              "V-2": {"label": label_mcnemar(holm["V-2"], con["V-2"], eff["V-2"]), "reason": None},
              "V-3": {"label": label_mcnemar(holm["V-3"], con["V-3"], eff["V-3"]), "reason": None},
              "V-8": {"label": label_mcnemar(holm["V-8"], con["V-8"], eff["V-8"], v8_extra), "reason": None}}
    v4_label = label_v4(holm["V-4"], inf.delta_hat, inf.delta_lower, s_lo, s_hi)
    labels["V-4"] = {"label": v4_label[0], "reason": v4_label[1]}
    sr_ach = MCV06_INPUTS["sr_ach"]
    assert isinstance(sr_ach, float)
    rect = rect_extrema(inf.delta_lower, inf.delta_upper, s_lo, s_hi)
    return {"evidence": EVIDENCE, "rates": rates, "contrasts": {k: _contrast_dict(c) for k, c in con.items()},
            "eff": eff, "v8_extra_condition": v8_extra, "holm": {"fwer": SUPPORTED_FWER, "p": pvals,
                                                                 "rejected": holm, "v1_hi_rejected": holm_hi},
            "v4": {"sr_eval": v4["sr_eval"], "delta_hat": inf.delta_hat, "se": inf.se, "p_one_sided": inf.p_one_sided,
                   "delta_lower": inf.delta_lower, "delta_upper": inf.delta_upper,
                   "effect_gate": v4_effect_gate(inf.delta_hat, s_lo, s_hi),
                   "weakened_max": v4_weakened_max(inf.delta_lower, s_lo, s_hi),
                   "rect_min": rect[0], "rect_max": rect[1], "approx_ok": v4_approx_ok(inf.delta_hat, s_lo),
                   "a_sr_eval_minus_sr_ach": v4["sr_eval"] - sr_ach, "residual_sr_ach_minus_theta": sr_ach - CORE_THETA,
                   "residual_flag": abs(sr_ach - CORE_THETA) > CALIB_TOLERANCE, "sigma_L": s_lo, "sigma_U": s_hi,
                   "batches": len(v4["batch_sharpes"])},
            "labels": labels}


# --- ERRATA-005 [C]: exclusive records, user decisions (R-0), run names (R-7), research inputs (O-1, O-2) ----------
#
# <output root>/user-decisions/NNNNNN-<kind>.json   UDR, O_CREAT | O_EXCL, never changed (R-0)
# <output root>/g7-core-lock/                       the G7 execution lock and its pool records (R-4)
# Append-only records are created exclusively, written, fsync'ed and closed; they are never replaced, so they do not
# go through storage.atomic (whose os.replace would overwrite). A partial file is left as it is and is a STOP.

_EXCL_FLAGS = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)


@dataclass(frozen=True)
class ExclusiveIO:
    """The calls of one exclusive create: the real os functions, replaced only by FAKE tests (IT-7, IT-8)."""
    opener: Callable[[str, int, int], int] = os.open
    writer: Callable[[int, Any], int] = os.write
    syncer: Callable[[int], None] = os.fsync
    closer: Callable[[int], None] = os.close


REAL_IO = ExclusiveIO()


def create_exclusive(path: FsPath, data: bytes, io: ExclusiveIO = REAL_IO) -> str:
    """O_CREAT | O_EXCL, write every byte, fsync, close. An existing file, a failed or short write or a failed fsync
    is a STOP (nothing is retried or deleted). Returns the sha256 of data."""
    name = FsPath(path).name
    try:
        handle = io.opener(str(path), _EXCL_FLAGS, 0o644)
    except FileExistsError as exc:
        raise StopImplementation(f"{name} already exists: never overwritten") from exc
    except OSError as exc:
        raise StopImplementation(f"cannot create {name}: {exc}") from exc
    try:
        view, done = memoryview(data), 0
        while done < len(data):
            n = io.writer(handle, view[done:])
            if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
                raise StopImplementation(f"{name}: short write")
            done += n
        io.syncer(handle)
    except OSError as exc:
        raise StopImplementation(f"{name}: write / fsync failed: {exc}") from exc
    finally:
        io.closer(handle)
    return _sha256(data)


def _read_canonical(path: FsPath, what: str) -> tuple[dict[str, Any], bytes]:
    raw = FsPath(path).read_bytes()
    try:
        obj = json.loads(raw)
    except ValueError as exc:
        raise StopImplementation(f"{what} is malformed") from exc
    if not isinstance(obj, dict) or canonical_bytes(obj) != raw:
        raise StopImplementation(f"{what} is not canonical JSON")
    return obj, raw


# R-0 user decision records. Claude writes one only for an approval line that is in a real user message; the line
# is the evidence (CLAUDE_REPORTED record, the chat line is checked by approval_text / approval_text_sha256).
UDR_DIR = "user-decisions"
UDR_SCHEMA = "moneylab.bt4_futility_diag.user_decision/1"
UDR_DECISIONS = {"PD5_PROCEED": "PROCEED", "RESUME_AFTER_INCOMPLETE": "RESUME", "LOCK_ABANDON": "ABANDON",
                 "ATTEMPT": "NEW_ATTEMPT"}
UDR_TARGETS = {"PD5_PROCEED": ("g6",), "RESUME_AFTER_INCOMPLETE": ("run", "run_spec"),
               "LOCK_ABANDON": ("lock", "lock_sha256"), "ATTEMPT": ("prev", "new", "reason")}
UDR_FIELDS = ("schema_version", "study_id", "evidence", "number", "kind", "target", "decision", "reason",
              "approval_text", "approval_text_sha256", "approved_by", "recorded_by", "code_sha", "approved_utc")
ATTEMPT_REASONS = ("ABNORMAL_TERMINATION", "INTEGRITY_FAILURE")
UDR_PREFIX = "USER_DECISION: BT4-FUTILITY-01 "
_UDR_LINE = re.compile(r"USER_DECISION: BT4-FUTILITY-01 UDR#(\d{6}) ([A-Z0-9_]+) (\S+) (\S+)")
_UDR_FILE = re.compile(r"(\d{6})-([A-Z0-9_]+)\.json")
_LOCK_NO = re.compile(r"\d{6}")


def _udr_target(kind: str, full: str) -> dict[str, str]:
    """The structured full_target of one kind; every sha256 64 hex, run ids valid R-7 names (STOP otherwise)."""
    items = full.split(",")
    pairs = [i.split("=", 1) for i in items if "=" in i]
    want = UDR_TARGETS[kind]
    if len(pairs) != len(items) or [k for k, _ in pairs] != list(want):
        raise StopImplementation(f"UDR {kind} target must be {','.join(k + '=…' for k in want)}")
    t = dict(pairs)
    for k, v in t.items():
        ok = {"g6": _HEX64.fullmatch(v), "run_spec": _HEX64.fullmatch(v), "lock_sha256": _HEX64.fullmatch(v),
              "lock": _LOCK_NO.fullmatch(v), "reason": v in ATTEMPT_REASONS}.get(k)
        if k in ("run", "prev", "new"):
            parse_run_id(v)
            ok = True
        if not ok:
            raise StopImplementation(f"UDR {kind} target {k}={v!r} is not valid (full values only)")
    return t


def parse_udr_line(text: str) -> dict[str, Any]:
    """Exactly one approval line `USER_DECISION: BT4-FUTILITY-01 UDR#NNNNNN <kind> <full_target> <decision>`, tokens
    separated by one space; kind, target and decision checked (R-0). Returns the parsed line."""
    lines = [ln for ln in text.splitlines() if ln.startswith("USER_DECISION:")]
    if len(lines) != 1:
        raise StopImplementation(f"exactly one USER_DECISION line is needed, got {len(lines)}")
    m = _UDR_LINE.fullmatch(lines[0])
    if not m or m.group(2) not in UDR_DECISIONS:
        raise StopImplementation("USER_DECISION line format / kind")
    kind = m.group(2)
    if m.group(4) != UDR_DECISIONS[kind]:
        raise StopImplementation(f"UDR {kind} decision must be {UDR_DECISIONS[kind]}")
    return {"number": int(m.group(1)), "kind": kind, "target": _udr_target(kind, m.group(3)),
            "decision": m.group(4), "approval_text": lines[0]}


def scan_udr_dir(output_root: FsPath) -> list[tuple[int, str, FsPath]]:
    """(number, kind, path) of every UDR, numbers 1..n without a gap; any other file is a STOP."""
    d = FsPath(output_root) / UDR_DIR
    if not d.exists():
        return []
    out = []
    for p in sorted(d.iterdir()):
        m = _UDR_FILE.fullmatch(p.name)
        if not (p.is_file() and m and m.group(2) in UDR_DECISIONS):
            raise StopImplementation(f"unexpected entry in {UDR_DIR}/: {p.name}")
        out.append((int(m.group(1)), m.group(2), p))
    if [n for n, _, _ in out] != list(range(1, len(out) + 1)):
        raise StopImplementation(f"{UDR_DIR}/ numbers are not 1..n without a gap")
    return out


def load_udr(path: FsPath) -> tuple[dict[str, Any], str]:
    """A UDR file: canonical, schema, and its approval line re-parsed equal to every recorded field and the file
    name. Returns (udr, file sha256)."""
    udr, raw = _read_canonical(path, f"UDR {FsPath(path).name}")
    if set(udr) != set(UDR_FIELDS) or (udr["schema_version"], udr["study_id"], udr["evidence"], udr["approved_by"],
                                        udr["recorded_by"]) != (UDR_SCHEMA, STUDY_ID, EVIDENCE, "USER", "CLAUDE"):
        raise StopImplementation(f"UDR {FsPath(path).name}: schema")
    line = parse_udr_line(str(udr["approval_text"]))
    m = _UDR_FILE.fullmatch(FsPath(path).name)
    if not (m and (int(m.group(1)), m.group(2)) == (line["number"], line["kind"])
            and (udr["number"], udr["kind"], udr["target"], udr["decision"]) == (line["number"], line["kind"],
                                                                                 line["target"], line["decision"])
            and udr["approval_text_sha256"] == _sha256(udr["approval_text"].encode("utf-8"))):
        raise StopImplementation(f"UDR {FsPath(path).name}: fields differ from its approval line")
    return udr, _sha256(raw)


def _udr_index(output_root: FsPath) -> dict[int, tuple[dict[str, Any], str]]:
    entries = {n: load_udr(p) for n, _, p in scan_udr_dir(output_root)}
    texts = [u["approval_text_sha256"] for u, _ in entries.values()]
    if len(set(texts)) != len(texts):
        raise StopImplementation("an approval line is recorded twice (reuse is not allowed)")
    return entries


def write_udr(output_root: FsPath, approval_text: str, reason: str, code_sha: str,
              io: ExclusiveIO = REAL_IO) -> tuple[FsPath, str]:
    """Record one approval line as UDR number n (= the next number) with O_EXCL. One line writes one file only; it
    grants no other change, gate or execution. Returns (path, file sha256)."""
    line = parse_udr_line(approval_text)
    if not (isinstance(code_sha, str) and _HEX40.fullmatch(code_sha)):
        raise StopImplementation("UDR code_sha must be 40 hex")
    entries = _udr_index(output_root)
    if line["number"] != len(entries) + 1:
        raise StopImplementation(f"UDR#{line['number']:06d} is not the next number ({len(entries) + 1:06d})")
    text_sha = _sha256(line["approval_text"].encode("utf-8"))
    if any(u["approval_text_sha256"] == text_sha for u, _ in entries.values()):
        raise StopImplementation("this approval line is already recorded")
    udr = {"schema_version": UDR_SCHEMA, "study_id": STUDY_ID, "evidence": EVIDENCE, "number": line["number"],
           "kind": line["kind"], "target": line["target"], "decision": line["decision"], "reason": str(reason),
           "approval_text": line["approval_text"], "approval_text_sha256": text_sha, "approved_by": "USER",
           "recorded_by": "CLAUDE", "code_sha": code_sha, "approved_utc": datetime.now(UTC).isoformat()}
    d = FsPath(output_root) / UDR_DIR
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{line['number']:06d}-{line['kind']}.json"
    return path, create_exclusive(path, canonical_bytes(udr), io)


def find_udr(output_root: FsPath, numbers: Sequence[int], kind: str, target: Mapping[str, str]) -> str | None:
    """The file sha256 of the UDR among numbers whose kind and full target equal these, or None (R-0: never a
    different target)."""
    entries = _udr_index(output_root)
    for n in numbers:
        if n not in entries:
            raise StopImplementation(f"UDR#{n:06d} does not exist")
        udr, sha = entries[n]
        if udr["kind"] == kind and udr["target"] == dict(target):
            return sha
    return None


def recheck_udrs(output_root: FsPath, shas: Iterable[str]) -> None:
    """A later stage: every recorded UDR sha256 is still a valid UDR file of the directory (STOP otherwise)."""
    present = {sha for _, sha in _udr_index(output_root).values()}
    missing = sorted(set(shas) - present)
    if missing:
        raise StopImplementation(f"recorded UDR files are missing or changed: {missing}")


# R-7 run names: <stage>-<part>-<CODE_SHA 12>[-attempt<k>] directly under the output root.
RUN_PARTS = {"g4c": ("smoke", "cal"), "g5": ("cal", "pilot"), "g7": ("E1-theta0.7", "P0-theta0.7", "v4"), "g8a": ()}
_RUN_ID = re.compile(r"(g4c|g5|g7|g8a)-(?:(smoke|cal|pilot|E1-theta0\.7|P0-theta0\.7|v4)-)?([0-9a-f]{12})"
                     r"(?:-attempt([1-9][0-9]*))?")


def run_id(stage: str, part: str | None, code_sha: str, attempt: int = 1) -> str:
    base = f"{stage}-{part}-{code_sha[:12]}" if part else f"{stage}-{code_sha[:12]}"
    name = base if attempt == 1 else f"{base}-attempt{attempt}"
    parse_run_id(name)
    return name


def parse_run_id(name: str) -> tuple[str, str | None, str, int]:
    """(stage, part, sha12, attempt); attempt 1 has no suffix, a suffix is k >= 2 (STOP otherwise)."""
    m = _RUN_ID.fullmatch(name)
    if not m:
        raise StopImplementation(f"run name {name!r} is not <stage>-<part>-<CODE_SHA 12>[-attempt<k>] (R-7)")
    stage, part, sha12, k = m.group(1), m.group(2), m.group(3), m.group(4)
    if (part is None) != (stage == "g8a") or (part is not None and part not in RUN_PARTS[stage]):
        raise StopImplementation(f"run name {name!r}: part does not belong to stage {stage}")
    if k is not None and int(k) < 2:
        raise StopImplementation(f"run name {name!r}: the first attempt has no suffix")
    return stage, part, sha12, int(k) if k else 1


def check_run_name(output_root: FsPath, name: str, stage: str, part: str | None, code_sha: str,
                   udr_numbers: Sequence[int] = ()) -> dict[str, Any]:
    """R-7 entry check: the name is this stage / part / CODE_SHA; attempt k >= 2 needs the directory of attempt k - 1
    and an ATTEMPT UDR whose target is exactly (prev, new, reason). Nothing is created or numbered automatically."""
    s, p, sha12, k = parse_run_id(name)
    if (s, p, sha12) != (stage, part, code_sha[:12]):
        raise StopImplementation(f"run name {name!r} is not {stage} / {part} / {code_sha[:12]}")
    if k == 1:
        return {"attempt": 1, "udr_sha256": None}
    prev = run_id(stage, part, code_sha, k - 1)
    if not (FsPath(output_root) / prev).is_dir():
        raise StopImplementation(f"attempt {k} needs attempt {k - 1} ({prev}) first")
    for reason in ATTEMPT_REASONS:
        sha = find_udr(output_root, udr_numbers, "ATTEMPT", {"prev": prev, "new": name, "reason": reason})
        if sha is not None:
            return {"attempt": k, "udr_sha256": sha, "reason": reason}
    raise StopForUserDecision(f"{name}: no ATTEMPT UDR with prev={prev}, new={name}")


def attempt_dirs(output_root: FsPath, stage: str, part: str | None, code_sha: str) -> list[FsPath]:
    """Every existing attempt directory of one stage / part / CODE_SHA, in attempt order (1, 2, ...)."""
    found = []
    for p in FsPath(output_root).iterdir() if FsPath(output_root).is_dir() else []:
        try:
            s, pt, sha12, k = parse_run_id(p.name)
        except StopImplementation:
            continue
        if (s, pt, sha12) == (stage, part, code_sha[:12]) and p.is_dir():
            found.append((k, p))
    return [p for _, p in sorted(found)]


# O-1, O-2: research run_inputs and the research manifest block.
CAL_PROVENANCE_FIELDS = ("kind", "calibration_sha256", "edge_annual", "sigma_pop")
RESEARCH_NAMESPACES = {"pilot": "FUTDIAG-PILOT", "core": "FUTDIAG"}
RESEARCH_BLOCK_FIELDS = ("calibration", "seed_collisions", "g6", "udr_sha256")
BOOTSTRAP_B = 1999                 # WO:39 BOOTSTRAP_B


def research_calibration_section(cal: Mapping[str, Any], sha256: str) -> dict[str, Any]:
    """WORK_ORDER REPRODUCIBILITY items a research manifest takes from its calibration (MANIFEST_PENDING 1-4)."""
    research_e1_cell(cal)
    if _sha256(calibration_bytes(cal)) != sha256:
        raise StopImplementation("calibration sha256 does not match its bytes")
    e1, sg = cal["e1"], cal["sigma"]
    return {"sha256": sha256, "kind": RESEARCH, "mcv06_inputs": dict(MCV06_INPUTS),
            "e1": {k: e1[k] for k in ("years", "seed", "edge_annual", "achieved_sharpe", "residual", "sigma_pop")},
            "sigma": {k: sg[k] for k in ("namespace", "reps", "sigma_hat", "kappa_hat", "sigma_L", "sigma_U")}}


def mcv06_external_seeds() -> dict[int, list[str]]:
    """Preregistration A1-c (a): the MC-V06 normal_M60_+0p7 rep and truth seeds (montecarlo derived_seed rule)."""
    seed, name = MCV06_INPUTS["seed"], MCV06_INPUTS["scenario"]
    assert isinstance(seed, int) and isinstance(name, str)
    out: dict[int, list[str]] = {}
    for i in range(MCV06_R_OUTER):
        out.setdefault(derived_seed(seed, name, "rep", str(i)), ["MC-V06", name, "rep", str(i)])
    for tag in ("truth", "truth-b1"):
        out.setdefault(derived_seed(seed, name, tag), ["MC-V06", name, tag])
    return out


def a1c_seed_report(spec: Mapping[str, Any], namespace: str) -> dict[str, Any]:
    """Preregistration A1-c (report only, never a STOP): the run's path and bootstrap seeds and the sigma calibration
    seeds against each other and the MC-V06 seeds, plus where the explicit E1 calibration and V-4 seeds fall."""
    paths = [p for cell in spec["cells"] for rep in range(spec["reps"])
             for p in rep_seed_paths(namespace, cell, rep, spec["windows"]).values()]
    paths += [sigma_seed_path(i) for i in range(SIGMA_R)]
    ext = mcv06_external_seeds()
    report = seed_collisions(paths, ext)
    values = {seed_for(p) for p in paths}
    report["explicit"] = [{"parts": list(parts), "seed": explicit_seed(parts),
                           "in_paths": explicit_seed(parts) in values, "in_external": explicit_seed(parts) in ext}
                          for parts in (E1_CALIB_SEED_PARTS, V4_EVAL_SEED_PARTS)]
    return report


def research_block(spec: Mapping[str, Any], inputs: Mapping[str, Any], cal: Mapping[str, Any], cal_sha: str,
                   g6: Mapping[str, Any] | None, udr_sha256: Sequence[str]) -> dict[str, Any]:
    block = {"calibration": research_calibration_section(cal, cal_sha),
             "seed_collisions": a1c_seed_report(spec, inputs["namespace"]),
             "g6": dict(g6) if g6 is not None else None, "udr_sha256": list(udr_sha256)}
    validate_research_block(spec, inputs, block)
    return block


def validate_research_block(spec: Mapping[str, Any], inputs: Mapping[str, Any],
                            block: Mapping[str, Any] | None) -> None:
    """The research block of this run: exact fields; the calibration it names is the run_inputs one; the A1-c report
    recomputes; a pilot has no G6 section and no UDR, a CORE run has the G6 section (ERRATA-004 R-5)."""
    prov = inputs["calibration_provenance"]
    if not (isinstance(block, Mapping) and set(block) == set(RESEARCH_BLOCK_FIELDS)):
        raise StopImplementation("a RESEARCH run needs its research block (calibration, seeds, G6, UDR)")
    c = block["calibration"]
    if not (isinstance(c, Mapping) and c.get("sha256") == prov["calibration_sha256"] and c.get("kind") == RESEARCH
            and (c["e1"]["edge_annual"], c["e1"]["sigma_pop"]) == (prov["edge_annual"], prov["sigma_pop"])):
        raise StopImplementation("research block calibration is not the run_inputs calibration")
    if json.loads(canonical_bytes(block["seed_collisions"])) != \
            json.loads(canonical_bytes(a1c_seed_report(spec, inputs["namespace"]))):
        raise StopImplementation("research block A1-c report does not recompute")
    udrs = block["udr_sha256"]
    if not (isinstance(udrs, list) and all(isinstance(u, str) and _HEX64.fullmatch(u) for u in udrs)
            and len(set(udrs)) == len(udrs)):
        raise StopImplementation("research block udr_sha256 must be distinct 64-hex values")
    if spec["mode"] == "pilot" and (block["g6"] is not None or udrs):
        raise StopImplementation("a pilot research block has no G6 section and no UDR")
    if spec["mode"] == "core" and not (isinstance(block["g6"], Mapping) and "g6_summary_sha256" in block["g6"]):
        raise StopImplementation("a CORE research block needs the G6 section")


# --- ERRATA-005 R-4a: Windows job object and process queries (ctypes, kernel32 / ntdll / advapi via winreg) -------
#
# Query and job-setup calls only: no process termination and no signal API is declared here (R-4c A). The target job
# handle stays in the driver: created non-inheritable, never duplicated, never closed while the driver runs.

JOB_KILL_ON_CLOSE, JOB_BREAKAWAY_OK, JOB_SILENT_BREAKAWAY_OK = 0x2000, 0x800, 0x1000
_FILETIME_UNIX_EPOCH = 116444736000000000            # 1970-01-01 in 100 ns since 1601-01-01 (FILETIME)


class _Win32:
    """x64 Windows calls with explicit argtypes / restype (structure sizes checked: 64 / 48 / 144 / 568 / 48)."""

    def __init__(self) -> None:
        import ctypes
        import ctypes.wintypes as w
        if sys.platform != "win32" or ctypes.sizeof(ctypes.c_void_p) != 8:
            raise StopImplementation("the G7 job / process API needs 64-bit Windows")
        self.ct, self.w = ctypes, w
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        nt = ctypes.WinDLL("ntdll")

        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                        ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", w.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]

        class Io(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ("RO", "WO", "OO", "RT", "WT", "OT")]

        class Ext(ctypes.Structure):
            _fields_ = [("Basic", Basic), ("Io", Io), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        class Pe32w(ctypes.Structure):
            _fields_ = [("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
                        ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", w.DWORD), ("cntThreads", w.DWORD),
                        ("th32ParentProcessID", w.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
                        ("szExeFile", ctypes.c_wchar * 260)]

        class TimeOfDay(ctypes.Structure):
            _fields_ = [("BootTime", ctypes.c_longlong), ("CurrentTime", ctypes.c_longlong),
                        ("TimeZoneBias", ctypes.c_longlong), ("TimeZoneId", ctypes.c_ulong),
                        ("Reserved", ctypes.c_ulong), ("BootTimeBias", ctypes.c_ulonglong),
                        ("SleepTimeBias", ctypes.c_ulonglong)]

        if tuple(ctypes.sizeof(s) for s in (Basic, Io, Ext, Pe32w, TimeOfDay)) != (64, 48, 144, 568, 48):
            raise StopImplementation("Windows structure sizes differ from the x64 layout")
        self.Ext, self.Pe32w, self.TimeOfDay = Ext, Pe32w, TimeOfDay
        h, b, d, p = w.HANDLE, w.BOOL, w.DWORD, ctypes.POINTER
        sig = {"GetCurrentProcess": ([], h), "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], h),
               "SetInformationJobObject": ([h, ctypes.c_int, ctypes.c_void_p, d], b),
               "QueryInformationJobObject": ([h, ctypes.c_int, ctypes.c_void_p, d, p(d)], b),
               "AssignProcessToJobObject": ([h, h], b), "IsProcessInJob": ([h, h, p(b)], b),
               "OpenProcess": ([d, b, d], h), "GetProcessTimes": ([h] + [p(w.FILETIME)] * 4, b),
               "CreateToolhelp32Snapshot": ([d, d], h), "Process32FirstW": ([h, p(Pe32w)], b),
               "Process32NextW": ([h, p(Pe32w)], b), "CloseHandle": ([h], b),
               "GetHandleInformation": ([h, p(d)], b), "GetTickCount64": ([], ctypes.c_ulonglong),
               "GetSystemTimePreciseAsFileTime": ([p(w.FILETIME)], None),
               "GetComputerNameExW": ([ctypes.c_int, w.LPWSTR, p(d)], b),
               "WaitForSingleObject": ([h, d], d)}
        for name, (args, res) in sig.items():
            fn = getattr(k, name)
            fn.argtypes, fn.restype = args, res
        nt.NtQuerySystemInformation.argtypes = [ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong,
                                                p(ctypes.c_ulong)]
        nt.NtQuerySystemInformation.restype = ctypes.c_long
        self.k, self.nt = k, nt

    def _fail(self, what: str) -> StopImplementation:
        return StopImplementation(f"{what} failed (Win32 error {self.ct.get_last_error()})")

    def _ft(self, f: Any) -> int:
        return (f.dwHighDateTime << 32) | f.dwLowDateTime

    def job_create(self) -> int:
        job = self.k.CreateJobObjectW(None, None)      # no security attributes: not inheritable; no name
        if not job:
            raise self._fail("CreateJobObjectW")
        return int(job)

    def job_set_kill_on_close(self, job: int) -> None:
        info = self.Ext()
        info.Basic.LimitFlags = JOB_KILL_ON_CLOSE
        if not self.k.SetInformationJobObject(job, 9, self.ct.byref(info), self.ct.sizeof(info)):
            raise self._fail("SetInformationJobObject")

    def job_limit_flags(self, job: int | None) -> int:
        info, ret = self.Ext(), self.w.DWORD()
        if not self.k.QueryInformationJobObject(job, 9, self.ct.byref(info), self.ct.sizeof(info),
                                                self.ct.byref(ret)):
            raise self._fail("QueryInformationJobObject")
        return int(info.Basic.LimitFlags)

    def assign_current(self, job: int) -> None:
        if not self.k.AssignProcessToJobObject(job, self.k.GetCurrentProcess()):
            raise self._fail("AssignProcessToJobObject")

    def in_job(self, process: int | None, job: int | None) -> bool:
        res = self.w.BOOL()
        proc = process if process is not None else self.k.GetCurrentProcess()
        if not self.k.IsProcessInJob(proc, job, self.ct.byref(res)):
            raise self._fail("IsProcessInJob")
        return bool(res.value)

    def job_pids(self, job: int) -> list[int]:
        n = 64
        while True:
            buf = (self.ct.c_ulonglong * (n + 1))()
            ret = self.w.DWORD()
            if self.k.QueryInformationJobObject(job, 3, buf, self.ct.sizeof(buf), self.ct.byref(ret)):
                assigned, listed = buf[0] & 0xFFFFFFFF, buf[0] >> 32
                if listed == assigned:
                    return [int(buf[1 + i]) for i in range(listed)]
            elif self.ct.get_last_error() != 234:              # ERROR_MORE_DATA: read again with a larger buffer
                raise self._fail("QueryInformationJobObject(ProcessIdList)")
            n *= 4

    def open_process(self, pid: int) -> int:
        h = self.k.OpenProcess(0x1000 | 0x00100000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE
        if not h:
            raise ProcessOpenError(pid, self.ct.get_last_error())
        return int(h)

    def exited(self, process: int) -> bool:
        """The process object's signal state: WAIT_OBJECT_0 = terminated, WAIT_TIMEOUT = running; WAIT_FAILED or any
        other value is a STOP (the caller classifies it UNVERIFIABLE). Not GetExitCodeProcess: 259 is ambiguous."""
        rc = self.k.WaitForSingleObject(process, 0)
        if rc == 0:                                              # WAIT_OBJECT_0
            return True
        if rc == 0x102:                                          # WAIT_TIMEOUT (258)
            return False
        raise StopImplementation(f"WaitForSingleObject returned {rc:#x} (Win32 error {self.ct.get_last_error()})")

    def close(self, handle: int) -> None:
        """Process and snapshot handles only; the target job handle is never passed here."""
        self.k.CloseHandle(handle)

    def creation_time(self, process: int | None) -> int:
        c, e, kt, ut = (self.w.FILETIME() for _ in range(4))
        proc = process if process is not None else self.k.GetCurrentProcess()
        if not self.k.GetProcessTimes(proc, *(self.ct.byref(x) for x in (c, e, kt, ut))):
            raise self._fail("GetProcessTimes")
        return self._ft(c)

    def snapshot_names(self) -> dict[int, tuple[int, str]]:
        """pid -> (parent pid, executable name) of every process (one CreateToolhelp32Snapshot)."""
        snap = self.k.CreateToolhelp32Snapshot(0x2, 0)
        if not snap or int(snap) == self.ct.c_void_p(-1).value:
            raise self._fail("CreateToolhelp32Snapshot")
        out = {}
        try:
            pe = self.Pe32w()
            pe.dwSize = self.ct.sizeof(self.Pe32w)
            ok = self.k.Process32FirstW(snap, self.ct.byref(pe))
            while ok:
                out[int(pe.th32ProcessID)] = (int(pe.th32ParentProcessID), str(pe.szExeFile))
                ok = self.k.Process32NextW(snap, self.ct.byref(pe))
        finally:
            self.k.CloseHandle(snap)
        return out

    def snapshot(self) -> dict[int, int]:
        """pid -> parent pid of every process."""
        return {pid: parent for pid, (parent, _) in self.snapshot_names().items()}

    def inheritable(self, handle: int) -> bool:
        flags = self.w.DWORD()
        if not self.k.GetHandleInformation(handle, self.ct.byref(flags)):
            raise self._fail("GetHandleInformation")
        return bool(flags.value & 1)                             # HANDLE_FLAG_INHERIT

    def computer_name(self) -> str:
        size = self.w.DWORD(0)
        self.k.GetComputerNameExW(4, None, self.ct.byref(size))   # ComputerNamePhysicalNetBIOS
        buf = self.ct.create_unicode_buffer(size.value + 1)
        if not self.k.GetComputerNameExW(4, buf, self.ct.byref(size)):
            raise self._fail("GetComputerNameExW")
        return buf.value

    def machine_guid(self) -> str:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
        except OSError as exc:
            raise StopImplementation(f"MachineGuid not readable: {exc}") from exc
        return str(value)

    def boot_time_s1(self) -> int:
        info, ret = self.TimeOfDay(), self.ct.c_ulong()
        status = self.nt.NtQuerySystemInformation(3, self.ct.byref(info), self.ct.sizeof(info),
                                                  self.ct.byref(ret))   # SystemTimeOfDayInformation
        if status != 0:
            raise StopImplementation(f"NtQuerySystemInformation(SystemTimeOfDayInformation) status {status}")
        return int(info.BootTime)

    def now_and_tick(self) -> tuple[int, int]:
        f = self.w.FILETIME()
        self.k.GetSystemTimePreciseAsFileTime(self.ct.byref(f))
        return self._ft(f), int(self.k.GetTickCount64())


_WIN: list[_Win32] = []


def win_api() -> _Win32:
    """The process-wide Windows API object (built on first use; STOP off Windows)."""
    if not _WIN:
        _WIN.append(_Win32())
    return _WIN[0]


# --- ERRATA-005 R-4: host identity, E-BOOT, and the investigation evidence (audit only, never an abandon basis) -----

EBOOT_TOLERANCE = 120 * 10_000_000            # 120 s in FILETIME units (R-4 E-BOOT 2, 3)
ERROR_INVALID_PARAMETER = 87                   # OpenProcess on a pid with no process (with snapshot absence: GONE)
# R-4 / R-9 RB-1: E-BOOT never holds until the read-only RB-1 check on this host has passed and this is set in G3.
# RB-1 PASS (user-approved run): S1 - S2 = 52.68 s <= 120 s on DESKTOP-31T80SB. Only lifts RB1_PENDING; every other
# E-BOOT check and the LOCK_ABANDON UDR still apply; Fast Startup behaviour stays UNVERIFIED.
RB1_VERIFIED = True


def host_id(api: Any) -> dict[str, str]:
    """R-4 host identity: (computer_name, machine_guid). A failure is a STOP."""
    return {"computer_name": api.computer_name(), "machine_guid": api.machine_guid()}


def boot_reading(api: Any) -> dict[str, int]:
    """S1 = NtQuerySystemInformation BootTime, S2 = now - GetTickCount64 x 10^4 (both FILETIME UTC); now is the
    same precise system time reading. |S1 - S2| > 120 s is a STOP (clock change suspected). S1 and S2 are not
    independent evidence; their agreement is a consistency check only (actual Windows behaviour UNVERIFIED)."""
    s1 = api.boot_time_s1()
    now, tick_ms = api.now_and_tick()
    s2 = now - tick_ms * 10_000
    if abs(s1 - s2) > EBOOT_TOLERANCE:
        raise StopImplementation(f"boot time readings disagree by {abs(s1 - s2) / 1e7!r} s (clock change?)")
    return {"s1": int(s1), "s2": int(s2), "now": int(now)}


def _mtime_filetime(path: FsPath) -> int:
    return FsPath(path).stat().st_mtime_ns // 100 + _FILETIME_UNIX_EPOCH


def e_boot(lock: Mapping[str, Any] | None, files: Sequence[FsPath], api: Any,
           rb1_verified: bool | None = None) -> dict[str, Any]:
    """R-4 E-BOOT. Holds only when: host_id equals the lock's; S1 / S2 readable and within 120 s; both moved more than
    120 s past the lock's boot_identity; both strictly after every file's mtime; no mtime in the future (now = the
    S2 reading's GetSystemTimePreciseAsFileTime); RB-1 verified. An invalid lock (None) never holds. Any read
    failure is a failed check. Returns the evidence and the verdict; it never reboots or signals anything."""
    out: dict[str, Any] = {"established": False, "reasons": [], "host_id_match": None, "lock_boot_identity": None,
                           "boot": None, "mtimes": {}}
    reasons = out["reasons"]
    if lock is None:
        reasons.append("INVALID_LOCK")
        return out
    out["lock_boot_identity"] = lock.get("boot_identity")
    try:
        out["host_id_match"] = host_id(api) == lock.get("host_id")
        boot = boot_reading(api)
        out["boot"] = boot
        out["mtimes"] = {FsPath(f).name: _mtime_filetime(f) for f in files}
    except (StopImplementation, OSError) as exc:
        reasons.append(f"READ_FAILED: {exc}")
        return out
    if not out["host_id_match"]:
        reasons.append("HOST_ID_MISMATCH")
    lb = lock.get("boot_identity")
    if not (isinstance(lb, dict) and boot["s1"] - lb.get("s1", boot["s1"]) > EBOOT_TOLERANCE
            and boot["s2"] - lb.get("s2", boot["s2"]) > EBOOT_TOLERANCE):
        reasons.append("BOOT_SESSION_UNCHANGED")
    latest = max(out["mtimes"].values(), default=None)
    if latest is None or not (boot["s1"] > latest and boot["s2"] > latest):
        reasons.append("BOOT_NOT_AFTER_RECORDS")
    if latest is not None and latest > boot["now"]:
        reasons.append("FUTURE_MTIME")
    if not (RB1_VERIFIED if rb1_verified is None else rb1_verified):
        reasons.append("RB1_PENDING")
    out["established"] = not reasons
    return out


def investigate(api: Any, driver: tuple[int, int] | None, workers: Sequence[tuple[int, int]]) -> dict[str, Any]:
    """Audit only (E-PID, E-WORKERS, E-TREE): which recorded processes are still alive and which live descendants
    the snapshot shows. Seeds are the driver and every recorded worker as (pid, creation time); descendants are found
    recursively by parent pid with a creation time not before the parent's. Two snapshots; an unreadable creation
    time is UNVERIFIABLE. Limits: a finished unrecorded middle process breaks the tree, and snapshots are not atomic.
    Recorded processes: PID_REUSED (same pid, other creation time); for the same pid and creation time the process
    object's signal state decides (WaitForSingleObject(h, 0)): EXITED (terminated, its object only kept by an open
    handle) or ALIVE (still running); GONE only when the pid is absent from a process snapshot taken first AND
    OpenProcess then fails with ERROR_INVALID_PARAMETER (two sources); every other failure (access denied,
    SYNCHRONIZE denied, other errors, the pid still listed, an unreadable creation time, a failed or unexpected wait
    result) is UNVERIFIABLE. Nothing here can allow an abandon (NON_BOOT_ABANDON = DISALLOWED); no process is
    signalled."""
    present = set(api.snapshot())

    def alive(pid: int, ct: int) -> str:
        try:
            h = api.open_process(pid)
        except ProcessOpenError as exc:
            gone = exc.winerror == ERROR_INVALID_PARAMETER and pid not in present
            return "GONE" if gone else "UNVERIFIABLE"
        except (StopImplementation, OSError):
            return "UNVERIFIABLE"
        try:
            if api.creation_time(h) != ct:
                return "PID_REUSED"
            return "EXITED" if api.exited(h) else "ALIVE"          # only for the same process (pid, creation time)
        except (StopImplementation, OSError):
            return "UNVERIFIABLE"
        finally:
            api.close(h)

    seeds = ([driver] if driver else []) + list(workers)
    trees = []
    for _ in range(2):
        snap = api.snapshot()
        live, frontier, seen = [], list(seeds), set()
        while frontier:
            pid, ct = frontier.pop()
            for child, parent in snap.items():
                if parent != pid or child in seen:
                    continue
                seen.add(child)
                state = "UNVERIFIABLE"
                try:
                    h = api.open_process(child)
                    try:
                        cct = api.creation_time(h)
                        state = "OLDER_THAN_PARENT" if cct < ct else "EXITED" if api.exited(h) else "DESCENDANT"
                    finally:
                        api.close(h)
                except (StopImplementation, OSError):
                    pass
                if state == "DESCENDANT":
                    live.append([child, cct])
                    frontier.append((child, cct))
                elif state == "EXITED":                    # not running; its own descendants are still searched
                    frontier.append((child, cct))
                elif state == "UNVERIFIABLE":
                    live.append([child, None])
        trees.append(sorted(live, key=lambda x: x[0]))
    return {"evidence_use": "AUDIT_ONLY", "e_pid": alive(*driver) if driver else None,
            "e_workers": [[pid, ct, alive(pid, ct)] for pid, ct in workers], "e_tree": trees[1],
            "e_tree_snapshots_agree": trees[0] == trees[1],
            "limits": ["tree break after an unrecorded middle process", "snapshots are not atomic"]}


# --- ERRATA-005 R-4: the G7 execution lock (append-only, g7-core-lock/) -----------------------------------------------

LOCK_DIR = "g7-core-lock"
LOCK_SCHEMA = "moneylab.bt4_futility_diag.g7_lock/2"         # ERRATA-006: token {"lock_number": n}
LOCK_FIELDS = ("schema_version", "token", "pid", "driver_creation_time", "started_utc", "code_sha", "run_ids",
               "target_job", "prior_job_membership", "job_policy_readback", "python_version", "host_id",
               "boot_identity")
POOL_START_SCHEMA = "moneylab.bt4_futility_diag.pool_start/1"
POOL_START_FIELDS = ("schema_version", "run_id", "unit_id", "pool_id", "driver_pid", "driver_creation_time",
                     "lock_sha256", "planned_max_workers", "written_utc")
WORKERS_SCHEMA = "moneylab.bt4_futility_diag.pool_workers/1"
WORKERS_FIELDS = ("schema_version", "run_id", "unit_id", "pool_id", "driver_pid", "driver_creation_time",
                  "lock_sha256", "python_version", "expected_worker_count", "verified_worker_count", "workers",
                  "target_job_membership_verified", "written_utc")
POOL_SHARED = ("run_id", "unit_id", "pool_id", "driver_pid", "driver_creation_time", "lock_sha256")
_LOCK_ENTRY = re.compile(r"(\d{6})\.(lock|released|abandoned)|(\d{6})\.(pool|workers)-(\d{6})(\.start)?")


def _lock_entries(d: FsPath) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    if not d.exists():
        return out
    for p in sorted(d.iterdir()):
        m = _LOCK_ENTRY.fullmatch(p.name)
        if not p.is_file() or not m or (m.group(4) == "pool") != bool(m.group(6)):
            raise StopForUserDecision(f"{LOCK_DIR}/ has a file that is not an allowed name: {p.name}")
        n = int(m.group(1) or m.group(3))
        e = out.setdefault(n, {"lock": None, "released": None, "abandoned": None, "start": {}, "workers": {}})
        if m.group(2):
            e[m.group(2)] = p
        else:
            e["start" if m.group(4) == "pool" else "workers"][int(m.group(5))] = p
    return out


LOCK_BAD_NAME, LOCK_READ_FAILED, LOCK_MALFORMED, LOCK_INVALID_CONTENT = (
    "BAD_NAME", "READ_FAILED", "MALFORMED", "INVALID_CONTENT")
_LOCK_FILE = re.compile(r"(\d{6})\.lock")


def lock_content_valid(lock: Mapping[str, Any], number: int) -> bool:
    """ERRATA-006 STRUCTURAL_VALIDITY 3-5 of lock content for file number n: exactly LOCK_FIELDS, the /2 schema and
    token exactly {"lock_number": n} with n an int (not a bool), at least 1."""
    token = lock.get("token")
    return (set(lock) == set(LOCK_FIELDS) and lock.get("schema_version") == LOCK_SCHEMA and type(token) is dict
            and set(token) == {"lock_number"} and type(token["lock_number"]) is int and token["lock_number"] >= 1
            and token["lock_number"] == number)


def check_lock_structure(path: FsPath) -> tuple[dict[str, Any] | None, str | None]:
    """ERRATA-006 STRUCTURAL_VALIDITY, the one check used by read_lock, scan_lock_dir, LockHandle.check, abandon and
    the investigation: (lock, None) for a valid lock, else (None, reason): BAD_NAME (not NNNNNN.lock, n >= 1),
    READ_FAILED (OSError while reading), MALFORMED (empty, partial or not canonical JSON) or INVALID_CONTENT
    (fields, schema or token)."""
    m = _LOCK_FILE.fullmatch(FsPath(path).name)
    number = int(m.group(1)) if m else 0
    if number < 1:
        return None, LOCK_BAD_NAME
    try:
        lock, _ = _read_canonical(path, "lock")
    except OSError:
        return None, LOCK_READ_FAILED
    except StopImplementation:
        return None, LOCK_MALFORMED
    if not lock_content_valid(lock, number):
        return None, LOCK_INVALID_CONTENT
    return lock, None


def read_lock(path: FsPath) -> dict[str, Any] | None:
    """A valid lock (ERRATA-006 STRUCTURAL_VALIDITY) or None (invalid for any reason of check_lock_structure)."""
    return check_lock_structure(path)[0]


def _invalid_lock_stop(n: int, reason: str) -> StopForUserDecision:
    return StopForUserDecision(f"lock {n:06d} is not a valid lock ({reason}, ERRATA-006 STRUCTURAL_VALIDITY): no "
                               "conversion, deletion or abandon; the user decides")


def scan_lock_dir(output_root: FsPath, *, structural: bool = True) -> dict[int, dict[str, Any]]:
    """R-4 directory state; every abnormal state is a STOP_FOR_USER_DECISION: unknown names, a lock number gap,
    released / abandoned / pool records without their lock, a lock that is not structurally valid (ERRATA-006
    SCAN_RULE, paired or not), released and abandoned together, a released or abandoned record not of that lock,
    more than one unpaired lock, pool number gaps, workers without start, start / workers fields that disagree (with
    each other, the file name or the lock sha256). structural=False is the read-only investigation only: an invalid
    lock (except an unreadable one, whose sha256 cannot be taken) is left to the caller to report; every other check
    stays."""
    d = FsPath(output_root) / LOCK_DIR
    entries = _lock_entries(d)
    if sorted(entries) != list(range(1, len(entries) + 1)):
        raise StopForUserDecision(f"{LOCK_DIR}/ lock numbers have a gap")
    unpaired = []
    for n, e in entries.items():
        if e["lock"] is None:
            raise StopForUserDecision(f"{LOCK_DIR}/ records of lock {n:06d} without the lock")
        _, why = check_lock_structure(e["lock"])
        if why is not None and (structural or why == LOCK_READ_FAILED):
            raise _invalid_lock_stop(n, why)
        lock_sha = sha256_file(e["lock"])
        if e["released"] and e["abandoned"]:
            raise StopForUserDecision(f"lock {n:06d} is both released and abandoned")
        for tag in ("released", "abandoned"):
            if e[tag]:
                rec, _ = _read_canonical(e[tag], f"{n:06d}.{tag}")
                if rec.get("lock_sha256") != lock_sha:
                    raise StopForUserDecision(f"{n:06d}.{tag} is not a record of that lock")
                if tag == "abandoned":
                    try:
                        recheck_udrs(output_root, [str(rec.get("udr_sha256"))])
                    except StopImplementation as exc:
                        raise StopForUserDecision(f"{n:06d}.abandoned: its LOCK_ABANDON UDR is missing") from exc
        if not (e["released"] or e["abandoned"]):
            unpaired.append(n)
        starts, workers = e["start"], e["workers"]
        if sorted(starts) != list(range(1, len(starts) + 1)) or not set(workers) <= set(starts):
            raise StopForUserDecision(f"lock {n:06d}: pool number gap or workers record without its start")
        for p, path in starts.items():
            s, _ = _read_canonical(path, path.name)
            if set(s) != set(POOL_START_FIELDS) or s["pool_id"] != p or s["lock_sha256"] != lock_sha:
                raise StopForUserDecision(f"{path.name}: fields, pool_id or lock sha256 disagree")
            if p in workers:
                wk, _ = _read_canonical(workers[p], workers[p].name)
                if set(wk) != set(WORKERS_FIELDS) or any(wk[k] != s[k] for k in POOL_SHARED):
                    raise StopForUserDecision(f"{workers[p].name} disagrees with its pool start record")
    if len(unpaired) > 1:
        raise StopForUserDecision(f"{LOCK_DIR}/ has more than one unpaired lock: {unpaired}")
    return entries


@dataclass
class LockHandle:
    """The lock this driver owns: number, lock byte sha256 and token ({"lock_number": n}, ERRATA-006). check() is the
    R-4 ownership rule plus the ERRATA-006 SCAN_RULE."""
    output_root: FsPath
    number: int
    sha256: str
    token: dict[str, int]
    content: dict[str, Any]
    next_pool: int = 1

    @property
    def dir(self) -> FsPath:
        return FsPath(self.output_root) / LOCK_DIR

    def check(self) -> None:
        d, n = self.dir, self.number
        lock = d / f"{n:06d}.lock"
        if not lock.exists() or sha256_file(lock) != self.sha256:
            raise StopForUserDecision(f"lock {n:06d} is not the one this driver holds")
        if (d / f"{n:06d}.released").exists() or (d / f"{n:06d}.abandoned").exists():
            raise StopForUserDecision(f"lock {n:06d} is already released or abandoned")
        entries = _lock_entries(d)
        if any(k > n for k in entries):
            raise StopForUserDecision(f"a lock after {n:06d} exists")
        for k, e in sorted(entries.items()):                  # ERRATA-006 SCAN_RULE: every lock structurally valid
            if e["lock"] is not None:
                _, why = check_lock_structure(e["lock"])
                if why is not None:
                    raise _invalid_lock_stop(k, why)


def lock_content(*, api: Any, code_sha: str, run_ids: Sequence[str], prior_job_membership: bool,
                 job_policy_readback: bool, driver_creation_time: int) -> dict[str, Any]:
    """R-4 lock content without the token (no budget value): acquire_lock adds {"lock_number": n} once n is known
    (ERRATA-006). host_id and boot_identity must be readable, else STOP before writing."""
    boot = boot_reading(api)
    return {"schema_version": LOCK_SCHEMA, "pid": os.getpid(),
            "driver_creation_time": driver_creation_time, "started_utc": datetime.now(UTC).isoformat(),
            "code_sha": code_sha, "run_ids": list(run_ids), "target_job": True,
            "prior_job_membership": prior_job_membership, "job_policy_readback": job_policy_readback,
            "python_version": sys.version, "host_id": host_id(api), "boot_identity": {"s1": boot["s1"],
                                                                                      "s2": boot["s2"]}}


def acquire_lock(output_root: FsPath, content: Mapping[str, Any], io: ExclusiveIO = REAL_IO) -> LockHandle:
    """R-4 acquisition: valid directory state (every lock structurally valid, ERRATA-006); the highest lock paired
    (else STOP_FOR_USER_DECISION); n+1.lock created with O_EXCL (a failure is a STOP, never retried) holding the
    canonical content with token {"lock_number": n+1} (set here, once the number is known), fsync'ed and closed."""
    entries = scan_lock_dir(output_root)
    if entries:
        top = entries[max(entries)]
        if not (top["released"] or top["abandoned"]):
            raise StopForUserDecision(f"lock {max(entries):06d} is not released: a G7 driver may still run, or it "
                                      "ended abnormally (abandon needs LOCK_ABANDON UDR and E-BOOT)")
    if set(content) != set(LOCK_FIELDS) - {"token"}:
        raise StopImplementation("lock content fields (the token is set at acquisition, ERRATA-006)")
    n = max(entries, default=0) + 1
    full = {**content, "token": {"lock_number": n}}
    if not lock_content_valid(full, n):
        raise StopImplementation("lock content is not structurally valid (ERRATA-006)")
    d = FsPath(output_root) / LOCK_DIR
    d.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(full)
    sha = create_exclusive(d / f"{n:06d}.lock", data, io)
    return LockHandle(FsPath(output_root), n, sha, {"lock_number": n}, full)


def release_lock(handle: LockHandle, io: ExclusiveIO = REAL_IO) -> None:
    """Normal end, budget STOP or a handled exception: n.released with the token and lock sha256 (lock kept)."""
    handle.check()
    create_exclusive(handle.dir / f"{handle.number:06d}.released", canonical_bytes(
        {"lock": handle.number, "lock_sha256": handle.sha256, "token": handle.token,
         "utc": datetime.now(UTC).isoformat()}), io)


def write_pool_start(directory: FsPath, lock_number: int, lock_sha256: str, pool_id: int, *, run_id_: str,
                     unit_id: Sequence[object], driver_pid: int, driver_creation_time: int, planned_max_workers: int,
                     io: ExclusiveIO = REAL_IO) -> str:
    """E-POOL-START: written and fsync'ed before the pool exists; a failure means no pool (STOP)."""
    rec = {"schema_version": POOL_START_SCHEMA, "run_id": run_id_, "unit_id": list(unit_id), "pool_id": pool_id,
           "driver_pid": driver_pid, "driver_creation_time": driver_creation_time, "lock_sha256": lock_sha256,
           "planned_max_workers": planned_max_workers, "written_utc": datetime.now(UTC).isoformat()}
    return create_exclusive(FsPath(directory) / f"{lock_number:06d}.pool-{pool_id:06d}.start", canonical_bytes(rec), io)


def write_pool_workers(directory: FsPath, lock_number: int, lock_sha256: str, pool_id: int, *, run_id_: str,
                       unit_id: Sequence[object], driver_pid: int, driver_creation_time: int, expected: int,
                       workers: Sequence[tuple[int, int]], io: ExclusiveIO = REAL_IO) -> str:
    """E-WORKERS, after the (A) / (B) checks and before the release. verified != expected: nothing is written
    (STOP). release status is not recorded (the verdict assumes released)."""
    if len(workers) != expected or len({p for p, _ in workers}) != len(workers):
        raise StopImplementation(f"verified workers {len(workers)} != expected {expected}: no record, no release")
    rec = {"schema_version": WORKERS_SCHEMA, "run_id": run_id_, "unit_id": list(unit_id), "pool_id": pool_id,
           "driver_pid": driver_pid, "driver_creation_time": driver_creation_time, "lock_sha256": lock_sha256,
           "python_version": sys.version, "expected_worker_count": expected, "verified_worker_count": len(workers),
           "workers": [{"pid": p, "creation_time": c} for p, c in workers],
           "target_job_membership_verified": True, "written_utc": datetime.now(UTC).isoformat()}
    return create_exclusive(FsPath(directory) / f"{lock_number:06d}.workers-{pool_id:06d}", canonical_bytes(rec), io)


def abandon_lock(output_root: FsPath, number: int, udr_numbers: Sequence[int], api: Any,
                 io: ExclusiveIO = REAL_IO, rb1_verified: bool | None = None) -> dict[str, Any]:
    """R-4 abandon (NON_BOOT_ABANDON = DISALLOWED): only an unpaired lock, only with a LOCK_ABANDON UDR for exactly
    this lock number and lock byte sha256, and only when E-BOOT holds. Never automatic; no reboot and no signal; the
    investigation (E-PID / E-WORKERS / E-TREE) can only refuse: a live or unverifiable driver, worker or descendant
    is a STOP (R-4 "조사에서 살아 있는 … 보이면 abandon을 신청하지 않는다"); it is never the basis."""
    entries = scan_lock_dir(output_root)
    e = entries.get(number)
    if e is None or e["released"] or e["abandoned"]:
        raise StopImplementation(f"lock {number:06d} is not an unpaired lock")
    lock_sha = sha256_file(e["lock"])
    udr = find_udr(output_root, udr_numbers, "LOCK_ABANDON", {"lock": f"{number:06d}", "lock_sha256": lock_sha})
    if udr is None:
        raise StopForUserDecision(f"lock {number:06d}: no LOCK_ABANDON UDR for lock_sha256 {lock_sha}")
    lock = read_lock(e["lock"])
    files = [e["lock"], *e["start"].values(), *e["workers"].values()]
    verdict = e_boot(lock, files, api, rb1_verified)
    if not verdict["established"]:
        raise StopImplementation(f"E-BOOT does not hold for lock {number:06d}: {verdict['reasons']}")
    alive = live_processes(investigate(api, *_recorded_processes(lock, e)))
    if alive:                      # R-4: a live driver / worker / descendant is never abandoned (refusal only)
        raise StopImplementation(f"lock {number:06d}: investigation shows live processes {alive}: no abandon "
                                 "(no process is signalled)")
    rec = {"lock": number, "lock_sha256": lock_sha, "udr_sha256": udr, "e_boot": verdict,
           "utc": datetime.now(UTC).isoformat()}
    create_exclusive(FsPath(output_root) / LOCK_DIR / f"{number:06d}.abandoned", canonical_bytes(rec), io)
    return rec


def _recorded_processes(lock: Mapping[str, Any] | None,
                        entry: Mapping[str, Any]) -> tuple[tuple[int, int] | None, list[tuple[int, int]]]:
    """The driver (from a valid lock) and every recorded worker of one lock entry, as (pid, creation time)."""
    workers = []
    for path in entry["workers"].values():
        wk, _ = _read_canonical(path, path.name)
        workers += [(int(w["pid"]), int(w["creation_time"])) for w in wk["workers"]]
    driver = (int(lock["pid"]), int(lock["driver_creation_time"])) if lock else None
    return driver, workers


def live_processes(report: Mapping[str, Any]) -> list[str]:
    """What an investigation shows alive or unverifiable (R-4 E-PID / E-WORKERS / E-TREE). Used only to refuse an
    abandon, never to allow one; a process reached through a reused parent pid counts as remaining."""
    out = [f"driver {report['e_pid']}"] if report["e_pid"] in ("ALIVE", "UNVERIFIABLE") else []
    out += [f"worker {pid} {state}" for pid, _, state in report["e_workers"] if state in ("ALIVE", "UNVERIFIABLE")]
    out += [f"descendant {pid}" for pid, _ in report["e_tree"]]
    if not report["e_tree_snapshots_agree"]:
        out.append("snapshots disagree")
    return out


def lock_investigation(output_root: FsPath, number: int, api: Any) -> dict[str, Any]:
    """Read-only audit of one lock: its recorded driver and workers through investigate() (no abandon basis). The
    only path that reports a structurally invalid lock instead of stopping (lock_valid False and the reason, same
    check_lock_structure); every other directory check still stops. Its result approves no G7 run or lock change."""
    e = scan_lock_dir(output_root, structural=False).get(number)
    if e is None:
        raise StopImplementation(f"lock {number:06d} does not exist")
    lock, why = check_lock_structure(e["lock"])
    report = investigate(api, *_recorded_processes(lock, e))
    return {"lock": number, "lock_valid": lock is not None, "lock_invalid_reason": why, "pools": len(e["start"]),
            "workers_records": len(e["workers"]), "investigation": report, "live": live_processes(report)}


# --- ERRATA-005 R-4a: target job setup and the start barrier ---------------------------------------------------------

G7_PYTHON = "3.14.8"
G7_POOL_FAILURE_POLICY = "ALLOW_STDLIB_OWN_WORKER_TERMINATION"     # R-4c: set only in the G7 GATE_AUTHORIZATION


def setup_target_job(api: Any) -> dict[str, Any]:
    """Create the target job (no security attributes, no name), set KILL_ON_JOB_CLOSE, read the flags back (exactly
    KILL_ON_JOB_CLOSE, no breakaway flag), record the prior job membership, assign the driver and confirm it with
    IsProcessInJob(current, target). Any failure is a STOP. The handle is kept by the caller for the whole run."""
    job = api.job_create()
    if not job or api.inheritable(job):
        raise StopImplementation("target job handle missing or inheritable")
    api.job_set_kill_on_close(job)
    flags = api.job_limit_flags(job)
    if not flags & JOB_KILL_ON_CLOSE or flags & (JOB_BREAKAWAY_OK | JOB_SILENT_BREAKAWAY_OK):
        raise StopImplementation(f"target job flags read back as {flags:#x}")
    prior = api.in_job(None, None)
    api.assign_current(job)
    if not api.in_job(None, job):
        raise StopImplementation("the driver is not in the target job after assignment")
    return {"job": job, "prior_job_membership": prior, "flags": flags}


def _barrier_init(ready: Any, release: Any, timeout_s: float) -> None:
    """Worker initializer (R-4a step 4): report (pid, creation time), wait for the release; no release in time raises
    (BrokenProcessPool, R-4c). The research function runs only after this returns. Writes no file (R-4b)."""
    ready.put((os.getpid(), win_api().creation_time(None)))
    if not release.wait(timeout_s):
        raise StopImplementation("start barrier: not released in time")


@dataclass
class BarrierEnv:
    """What a barrier pool needs. api / executor_factory / context are the real ones in G7 and fakes in FAKE tests;
    record_dir is g7-core-lock/ in G7 and a test-only temporary directory in IT-2 / IT-3a (R-9)."""
    api: Any
    job: Any
    record_dir: FsPath
    lock_number: int
    lock_sha256: str
    driver_pid: int
    driver_creation_time: int
    run_id: str
    ready_timeout_s: float = 300.0
    release_timeout_s: float = 600.0
    executor_factory: Callable[..., Any] = ProcessPoolExecutor
    context: Any = None
    io: ExclusiveIO = REAL_IO
    next_pool: int = 1
    events: list[str] | None = None

    def mark(self, event: str) -> None:
        if self.events is not None:
            self.events.append(event)


def verify_pool_workers(env: BarrierEnv, reported: Sequence[tuple[int, int]], expected: int,
                        handles: dict[int, int]) -> list[tuple[int, int]]:
    """(A) per worker: open it (the handle is kept, so the pid cannot be reused), creation time equal to the reported
    one and not before the driver's, parent = the driver in the snapshot, IsProcessInJob(worker, target) TRUE.
    (B) the target job's pid list is exactly the driver and these workers, and the driver's children created after it
    started are exactly these workers. Any failure, an unexpected pid, a missing worker or an unverifiable process is
    a STOP (the unit is not written)."""
    api = env.api
    if len(reported) != expected or len({p for p, _ in reported}) != expected:
        raise StopImplementation(f"start barrier: {len(reported)} workers reported, {expected} expected")
    snap = api.snapshot()
    out = []
    for pid, ct in reported:
        try:
            h = handles.get(pid) or api.open_process(pid)
        except (StopImplementation, OSError) as exc:
            raise StopImplementation(f"worker {pid} cannot be opened: {exc}") from exc
        handles[pid] = h
        if api.creation_time(h) != ct or ct < env.driver_creation_time:
            raise StopImplementation(f"worker {pid}: creation time differs from the reported one")
        if snap.get(pid) != env.driver_pid:
            raise StopImplementation(f"worker {pid} is not a direct child of the driver")
        if not api.in_job(h, env.job):
            raise StopImplementation(f"worker {pid} is not in the target job")
        out.append((pid, ct))
    want = {env.driver_pid, *(p for p, _ in out)}
    listed = set(api.job_pids(env.job))
    if listed != want:
        raise StopImplementation(f"target job pids {sorted(listed)} are not the driver and the verified workers "
                                 f"(unexpected {sorted(listed - want)}, missing {sorted(want - listed)})")
    children = set()
    for child, parent in snap.items():
        if parent != env.driver_pid:
            continue
        try:
            h = api.open_process(child)
        except (StopImplementation, OSError) as exc:
            raise StopImplementation(f"child {child} of the driver is unverifiable: {exc}") from exc
        try:
            if api.creation_time(h) >= env.driver_creation_time:
                children.add(child)
        finally:
            api.close(h)
    if children != {p for p, _ in out}:
        raise StopImplementation(f"driver children {sorted(children)} are not exactly the verified workers")
    return out


def barrier_pool_run(env: BarrierEnv, fn: Callable[[Any], Any], tasks: Sequence[Any], workers: int,
                     unit_id: Sequence[object]) -> list[Any]:
    """One unit through a fresh pool (R-4a): E-POOL-START, pool, submit every task (min(w, tasks) workers start one by
    one), collect the ready reports, verify (A) and (B), E-WORKERS (O_EXCL, write, fsync), then release; after the
    results, re-check the job pid list and every worker before the caller writes the unit. A STOP never releases;
    the pool then breaks when the workers' barrier wait times out (stdlib may end its own workers: R-4c)."""
    pool_id = env.next_pool
    env.next_pool += 1
    expected = min(workers, len(tasks))
    shared: dict[str, Any] = {"run_id_": env.run_id, "unit_id": unit_id, "driver_pid": env.driver_pid,
                              "driver_creation_time": env.driver_creation_time}
    write_pool_start(env.record_dir, env.lock_number, env.lock_sha256, pool_id, planned_max_workers=workers,
                     io=env.io, **shared)
    env.mark("pool_start_fsynced")
    ctx = env.context or multiprocessing.get_context("spawn")
    ready, release = ctx.Queue(), ctx.Event()
    handles: dict[int, int] = {}
    try:
        with env.executor_factory(max_workers=workers, mp_context=ctx, initializer=_barrier_init,
                                  initargs=(ready, release, env.release_timeout_s)) as pool:
            env.mark("pool_created")
            futures = [pool.submit(fn, t) for t in tasks]
            reported = []
            for _ in range(expected):
                try:
                    reported.append(tuple(ready.get(timeout=env.ready_timeout_s)))
                except queue.Empty as exc:
                    raise StopImplementation("start barrier: ready timeout (no release)") from exc
            try:
                extra = ready.get(timeout=0.5)
            except queue.Empty:
                extra = None
            if extra is not None:
                raise StopImplementation(f"start barrier: an unexpected worker reported {extra}")
            verified = verify_pool_workers(env, reported, expected, handles)
            env.mark("workers_verified")
            write_pool_workers(env.record_dir, env.lock_number, env.lock_sha256, pool_id, expected=expected,
                               workers=verified, io=env.io, **shared)
            env.mark("workers_fsynced")
            release.set()
            env.mark("released")
            results = [f.result() for f in futures]
            verify_pool_workers(env, verified, expected, handles)      # before the caller writes the unit
            env.mark("rechecked")
    finally:
        for h in handles.values():
            env.api.close(h)
    return results


def barrier_unit_runner(env: BarrierEnv) -> UnitRunner:
    """run_units' unit runner for G7: the unit's replications through barrier_pool_run (one pool per unit)."""
    def run(cell: CellSpec, reps: Sequence[int], namespace: str, bootstrap: int, windows: Sequence[str],
            workers: int) -> tuple[list[dict[str, object]], list[float]]:
        reps = list(reps)
        tasks = [(cell, i, namespace, bootstrap, tuple(windows)) for i in reps]
        done = barrier_pool_run(env, _rep_task, tasks, workers, [cell.name, reps[0], reps[-1] + 1])
        return [rec for chunk, _ in done for rec in chunk], [seconds for _, seconds in done]
    return run


# --- ERRATA-005 R-5 V-4 run, R-3 CORE budget over every attempt, R-6 G8a ----------------------------------------------

V4_FILE, V4_SCHEMA = "v4.json", "moneylab.bt4_futility_diag.v4/1"
V4_EXECUTION_SCHEMA = "moneylab.bt4_futility_diag.v4_execution/1"
V4_DIR_FILES = (V4_FILE, EXECUTION_FILE, SUMS_FILE)
DECISION_FILE, DECISION_SCHEMA = "decision_summary.json", "moneylab.bt4_futility_diag.decision_summary/1"


def _only_files(d: FsPath, allowed: Sequence[str]) -> list[str]:
    tmp, other = [], []
    for p in sorted(FsPath(d).rglob("*")) if FsPath(d).exists() else []:
        rel = p.relative_to(d).as_posix()
        if p.is_file() and p.name.endswith(TMP_SUFFIX):
            tmp.append(rel)
        elif not (p.is_file() and rel in allowed):
            other.append(rel)
    if other:
        raise StopImplementation(f"unexpected files in {FsPath(d).name}: {other}")
    return tmp


def build_v4(ev: Mapping[str, Any], identity: Mapping[str, Any], udr_sha256: Sequence[str]) -> dict[str, Any]:
    if len(ev["batch_sharpes"]) != V4_BATCHES:
        raise StopImplementation(f"V-4 needs K = {V4_BATCHES} batches (WO:454)")
    return {"schema_version": V4_SCHEMA, "study_id": STUDY_ID, "evidence": EVIDENCE, "years": ev["years"],
            "seed_parts": list(ev["seed_parts"]), "seed": explicit_seed(ev["seed_parts"]),
            "edge_annual": ev["edge_annual"], "edge_source": MCV06_INPUTS["source"], "sr_eval": ev["sr_eval"],
            "batch_sharpes": list(ev["batch_sharpes"]), "batch_lengths": list(ev["batch_lengths"]),
            "identity": dict(identity), "udr_sha256": list(udr_sha256)}


def verify_v4_run(v4_dir: FsPath) -> dict[str, Any]:
    """R-5: VERIFIED (v4.json canonical with its SHA256SUMS), PENDING (v4.json only) or ABSENT; anything else STOP."""
    d = FsPath(v4_dir)
    tmp = _only_files(d, V4_DIR_FILES)
    has_v4, has_sums = (d / V4_FILE).exists(), (d / SUMS_FILE).exists()
    if has_sums and not has_v4:
        raise StopImplementation("V-4 SHA256SUMS without v4.json")
    if not has_v4:
        return {"status": "ABSENT", "tmp": tmp}
    v4, raw = _read_canonical(d / V4_FILE, V4_FILE)
    if v4.get("schema_version") != V4_SCHEMA or len(v4.get("batch_sharpes", [])) != V4_BATCHES:
        raise StopImplementation("v4.json schema / K")
    if not has_sums:
        return {"status": "PENDING", "tmp": tmp, "v4": v4, "sha256": _sha256(raw)}
    if (d / SUMS_FILE).read_bytes() != f"{_sha256(raw)}  {V4_FILE}\n".encode("utf-8"):
        raise StopImplementation("V-4 SHA256SUMS does not match v4.json")
    return {"status": "VERIFIED", "tmp": tmp, "v4": v4, "sha256": _sha256(raw)}


def write_v4_run(v4_dir: FsPath, identity: Mapping[str, Any], udr_sha256: Sequence[str],
                 years: int = V4_EVAL_YEARS) -> dict[str, Any]:
    """R-5: a verified v4.json is reused (not recomputed); v4.json alone is recomputed and must be byte-identical
    before SHA256SUMS is written; damage is a STOP (never repaired). The V-4 time goes to its execution.json only
    and is in no CORE budget value."""
    d = FsPath(v4_dir)
    state = verify_v4_run(d)
    if state["status"] == "VERIFIED":
        return state
    started, t0 = datetime.now(UTC), _clock()
    data = canonical_bytes(build_v4(v4_evaluation(years), identity, udr_sha256))
    seconds = _clock() - t0
    d.mkdir(parents=True, exist_ok=True)
    _write_or_compare(d / V4_FILE, data, V4_FILE)
    _write_or_compare(d / SUMS_FILE, f"{_sha256(data)}  {V4_FILE}\n".encode("utf-8"), "V-4 SHA256SUMS")
    path = d / EXECUTION_FILE
    runs = []
    if path.exists():
        ex, _ = _read_canonical(path, f"V-4 {EXECUTION_FILE}")
        if set(ex) != {"schema_version", "evidence", "runs"} or ex["schema_version"] != V4_EXECUTION_SCHEMA:
            raise StopImplementation(f"V-4 {EXECUTION_FILE} schema")
        runs = list(ex["runs"])
    runs.append({"started_utc": started.isoformat(), "finished_utc": datetime.now(UTC).isoformat(),
                 "v4_seconds": seconds, "git": git_identity(), "python": platform.python_version(),
                 "platform": platform.platform()})
    atomic_write_bytes(path, canonical_bytes({"schema_version": V4_EXECUTION_SCHEMA, "evidence": EVIDENCE,
                                              "runs": runs}))
    return verify_v4_run(d)


def core_attempt_runs(output_root: FsPath, code_sha: str) -> dict[str, FsPath]:
    """Every CORE run directory (E1 and P0, every attempt) of this CODE_SHA: name -> path."""
    return {p.name: p for cell in CORE_CELLS for p in attempt_dirs(output_root, "g7", cell, code_sha)}


def core_attempts_budget(output_root: FsPath, code_sha: str, timing: Mapping[str, Any]) -> dict[str, Any]:
    """R-3 (OPTION I): T_CORE = the cumulative session elapsed of every CORE run of this CODE_SHA, every attempt
    included (no reset on retry), V-4 excluded; exceeded = T_CORE > 1.5 x W_G6 / (12 eta_hat), exactly 1.5 x
    passes; an incomplete run makes it a lower bound and never a PASS."""
    seen: set[bytes] = set()
    per_run, complete, budget_stop = {}, True, []
    for name, path in core_attempt_runs(output_root, code_sha).items():
        ex = read_execution(path)
        for s in (ex["sessions"] if ex is not None else []):
            key = canonical_bytes(s)
            if key in seen:
                raise StopImplementation(f"run {name!r}: a session is counted twice")
            seen.add(key)
            if s["end"] is not None and s["end"]["stop"] is not None:
                budget_stop.append(name)
        acct = time_accounting(ex)
        per_run[name] = {"cumulative_s": acct["cumulative_s"], "time_accounting": acct["status"]}
        complete &= acct["status"] == "COMPLETE"
    total = sum(float(r["cumulative_s"]) for r in per_run.values())
    expected = g6_expected_wall_s(timing)
    exceeded = wall_exceeded(total, expected)
    return {"t_core_cumulative_s": total, "per_run": per_run, "expected_wall_s": expected,
            "limit_s": RUNTIME_STOP_MULTIPLE * expected, "exceeded": exceeded, "time_accounting_complete": complete,
            "lower_bound": not complete, "budget_pass_allowed": complete and not exceeded,
            "budget_stopped_runs": sorted(set(budget_stop))}


def g7_entry_checks(pilot_dir: FsPath, core_spec: Mapping[str, Any], cell: str, summary: Mapping[str, Any],
                    timing: Mapping[str, Any]) -> None:
    """R-1 G7 entry checks (each a STOP): one cell; reps = G6 R_c[cell]; unit_size = the pilot's; g6 VERIFIED;
    g6_timing recomputes (revalidate_g6_timing, done by the caller); budget_pass true (WO:419); R_c <= 40,000
    (WO:457); identity (check_run_identity, by the caller); P0_CONF_CHECK PASS (R-8)."""
    if core_spec["cells"] != [cell]:
        raise StopImplementation("a G7 CORE run covers exactly one cell (R-1)")
    if core_spec["reps"] != summary["r_c"]["r_c"][cell]:
        raise StopImplementation(f"{cell} reps {core_spec['reps']} != G6 R_c {summary['r_c']['r_c'][cell]}")
    check_g7_unit_size(pilot_dir, core_spec)
    if timing.get("budget_pass") is not True:
        raise StopImplementation("G6 budget judgment is not a PASS (WO:419: contract decision needed)")
    if summary["r_c"]["over_max"]:
        raise StopImplementation(f"G6 R_c over {R_MAX}: {summary['r_c']['over_max']} (WO:457)")
    if summary.get("P0_CONF_CHECK") != P0_CONF_PASS:
        raise StopImplementation("G6 P0_CONF_CHECK is STOP (WO:455, ERRATA-005 R-8)")


def g7_core(output_root: FsPath, *, pilot_dir: FsPath, cal_dir: FsPath, e1_dir: FsPath, p0_dir: FsPath,
            v4_dir: FsPath, workers: int, pool_failure_policy: str | None, udr_numbers: Sequence[int] = (),
            git: GitRunner = _git, api: Any = None, executor_factory: Callable[..., Any] = ProcessPoolExecutor,
            ready_timeout_s: float = 300.0) -> dict[str, Any]:
    """The G7 driver (R-1..R-5): one process, E1 run -> P0 run -> V-4, one CORE pool at a time, on one Windows host.
    Order: policy / platform / Python / workers; calibration, research identity (git runs before the job), the pilot
    run_spec, the VERIFIED g6/ and its run_spec sha256, the ERRATA-007 stage identity (CAL / PILOT / NOW), G6 checks,
    PD-5 UDR, run names and ATTEMPT UDR, no retry after a budget STOP or G8a, global budget over every attempt; then
    the target job, the lock, and each CORE run through run_units with the lock handle and the start barrier; then
    V-4 and the release. A handled STOP releases the lock; an unhandled crash leaves it (abandon: UDR + E-BOOT)."""
    if pool_failure_policy != G7_POOL_FAILURE_POLICY:
        raise StopImplementation("G7_POOL_FAILURE_POLICY must be given exactly as set in the G7 GATE_AUTHORIZATION")
    if sys.platform != "win32" or platform.python_version() != G7_PYTHON:
        raise StopImplementation(f"G7 runs on Windows with Python {G7_PYTHON} only (sys.version {sys.version!r})")
    if not (_positive_int(workers) and workers <= CORE_MAX_WORKERS):
        raise StopImplementation(f"workers must be 1..{CORE_MAX_WORKERS}, got {workers!r}")
    output_root = FsPath(output_root)
    cal, cal_sha = load_calibration(FsPath(cal_dir) / CALIBRATION_FILE)
    e1 = research_e1_cell(cal)
    ident = research_identity(None, git, cal_sha)
    code_sha = ident["git_head"]
    pilot_spec, pilot_spec_sha = read_pilot_spec(pilot_dir)        # ERRATA-007: a missing / bad run_spec STOPs first
    summary, g6_sha = _verified_g6(pilot_dir)
    if summary["pilot"]["run_spec_sha256"] != pilot_spec_sha:
        raise StopImplementation(f"pilot {RUN_SPEC_FILE} is not the one g6/ references")
    # ERRATA-007: NOW as computed above (no second git call), before the target job and the lock
    check_stage_identity(cal["identity"], ident, cal_sha, pilot_spec)
    _, pilot_inputs, _, _ = _load_spec_inputs(FsPath(pilot_dir))
    if pilot_inputs["calibration_provenance"] != calibration_provenance(cal, cal_sha):
        raise StopImplementation("the pilot was not made with this calibration")
    timing = revalidate_g6_timing(pilot_dir)
    udrs: list[str] = []
    if summary["pd5"]["stop"]:
        sha = find_udr(output_root, udr_numbers, "PD5_PROCEED", {"g6": g6_sha})
        if sha is None:
            raise StopForUserDecision(f"PD-5 STOP: G7 needs a PD5_PROCEED UDR for g6={g6_sha}")
        udrs.append(sha)
    dirs = {E1_CELL: FsPath(e1_dir), P0_CELL: FsPath(p0_dir), "v4": FsPath(v4_dir)}
    names = {k: check_run_name(output_root, p.name, "g7", k, code_sha, udr_numbers) for k, p in dirs.items()}
    if any(p.parent != output_root for p in dirs.values()):
        raise StopImplementation("G7 run directories are direct children of the output root")
    if attempt_dirs(output_root, "g8a", None, code_sha):
        raise StopImplementation("G8a has run for this CODE_SHA: no further G7 attempt (R-7)")
    budget = core_attempts_budget(output_root, code_sha, timing)
    if budget["budget_stopped_runs"]:
        raise StopImplementation(f"a CORE run stopped on the budget ({budget['budget_stopped_runs']}): no restart")
    if budget["exceeded"]:
        raise StopImplementation(f"CORE global wall-clock {budget['t_core_cumulative_s']!r} s > {budget['limit_s']!r}")
    resume: dict[str, str] = {}
    for name, acct in budget["per_run"].items():
        if acct["time_accounting"] == "COMPLETE":
            continue
        current = name in (dirs[E1_CELL].name, dirs[P0_CELL].name)
        if current:
            run_spec_sha = sha256_file(output_root / name / RUN_SPEC_FILE)
            sha = find_udr(output_root, udr_numbers, "RESUME_AFTER_INCOMPLETE", {"run": name, "run_spec": run_spec_sha})
            if sha is None:
                raise StopForUserDecision(f"{INCOMPLETE_TIME}: {name} needs a RESUME_AFTER_INCOMPLETE UDR")
            resume[name] = sha
        elif not any(n["attempt"] > 1 for n in names.values()):
            raise StopForUserDecision(f"{INCOMPLETE_TIME}: earlier run {name} is incomplete and not superseded")
    api = api or win_api()
    job = setup_target_job(api)
    driver_ct = api.creation_time(None)
    content = lock_content(api=api, code_sha=code_sha, run_ids=[p.name for p in dirs.values()],
                           prior_job_membership=job["prior_job_membership"], job_policy_readback=True,
                           driver_creation_time=driver_ct)
    handle = acquire_lock(output_root, content)
    results: dict[str, Any] = {"lock": handle.number, "runs": {}}
    try:
        for cell, cell_spec in ((E1_CELL, e1), (P0_CELL, p0_cell())):
            d = dirs[cell]
            spec = build_run_spec(mode="core", code_sha=code_sha, code_tree=ident["git_tree"],
                                  config_sha256=ident["contract_sha256"]["config"],
                                  prereg_sha256=ident["contract_sha256"]["prereg"], cells=[cell],
                                  windows=list(WINDOWS), rules=list(RULES), reps=summary["r_c"]["r_c"][cell],
                                  bootstrap=BOOTSTRAP_B, unit_size=summary["pilot"]["unit_size"])
            g7_entry_checks(pilot_dir, spec, cell, summary, timing)
            inputs = build_run_inputs(spec, [cell_spec], RESEARCH_NAMESPACES["core"],
                                      calibration_provenance(cal, cal_sha))
            check_run_identity(spec, inputs, ident)
            run_udrs = udrs + [s for s in (names[cell]["udr_sha256"], resume.get(d.name)) if s]
            block = research_block(spec, inputs, cal, cal_sha, g7_manifest_g6_section(pilot_dir), run_udrs)
            budget = core_attempts_budget(output_root, code_sha, timing)        # E1 done -> before P0, and at start
            if budget["exceeded"]:
                raise StopImplementation(f"CORE global wall-clock {budget['t_core_cumulative_s']!r} s exceeded")
            offset = sum(v["cumulative_s"] for n, v in budget["per_run"].items() if n != d.name)
            env = BarrierEnv(api=api, job=job["job"], record_dir=handle.dir, lock_number=handle.number,
                             lock_sha256=handle.sha256, driver_pid=os.getpid(), driver_creation_time=driver_ct,
                             run_id=d.name, ready_timeout_s=ready_timeout_s, executor_factory=executor_factory,
                             next_pool=handle.next_pool)
            results["runs"][cell] = run_units(
                d, spec, inputs, workers, g6_expected_wall_s(timing), d.name in resume, research=block, lock=handle,
                unit_runner=barrier_unit_runner(env), budget_offset_s=offset)
            handle.next_pool = env.next_pool
        handle.check()
        results["v4"] = write_v4_run(dirs["v4"], ident, udrs + [s for s in (names["v4"]["udr_sha256"],) if s])["status"]
    except (StopImplementation, StopForUserDecision):
        release_lock(handle)
        raise
    release_lock(handle)
    return {"command": "g7", "evidence": EVIDENCE, "status": "COMPLETE", **results}


DECISION_FIELDS = ("schema_version", "study_id", "evidence", "decision", "provenance")
DECISION_PROVENANCE_FIELDS = ("runs", "v4_sha256", "g6_summary_sha256", "calibration_sha256", "code_sha", "attempts",
                              "udr_sha256")
DECISION_RUN_FIELDS = ("run_id", "run_spec_sha256", "run_inputs_sha256", "manifest_sha256", "sha256sums_sha256")
ATTEMPT_FIELDS = ("run_id", "status", "udr_sha256")
HYPOTHESES = ("V-1", "V-2", "V-3", "V-8", "V-4")


def _earlier_attempt(path: FsPath, part: str) -> dict[str, Any]:
    """R-6 provenance of one earlier attempt: run_id, state (COMPLETE / INCOMPLETE / DAMAGED, V-4: VERIFIED / PENDING /
    ABSENT / DAMAGED) and the UDR sha256 it recorded (read-only)."""
    udrs: list[str] = []
    try:
        if part == "v4":
            st = verify_v4_run(path)
            status = st["status"]
            udrs = list(st["v4"]["udr_sha256"]) if "v4" in st else []
        elif (path / RUN_SPEC_FILE).exists():
            status = verify_run(path)["status"]
            if (path / MANIFEST_FILE).exists():
                udrs = list(json.loads((path / MANIFEST_FILE).read_bytes())["research"]["udr_sha256"])
        else:
            status = "INCOMPLETE"
    except (StopImplementation, ValueError, KeyError, TypeError):
        status = "DAMAGED"
    return {"run_id": path.name, "status": status, "udr_sha256": udrs}


def g8a_payload(output_root: FsPath, *, decision_dir: FsPath, pilot_dir: FsPath, cal_dir: FsPath, e1_dir: FsPath,
                p0_dir: FsPath, v4_dir: FsPath, git: GitRunner = _git) -> tuple[bytes, dict[str, Any]]:
    """R-6 G8a, read-only: the target set is the highest attempt of E1, P0 and V-4; every earlier attempt goes to the
    provenance with its state and UDR. Entry (each a STOP): target runs COMPLETE, pilot g6 VERIFIED, V-4 VERIFIED,
    recorded UDR files re-verified, both G6 sections equal and equal to the pilot's, calibration sha256 in each
    run_inputs, earlier attempts' units byte-identical, every CORE attempt's time accounting COMPLETE and the global
    budget not exceeded. Returns the canonical decision_summary.json bytes and the decision."""
    output_root = FsPath(output_root)
    cal, cal_sha = load_calibration(FsPath(cal_dir) / CALIBRATION_FILE)
    ident = research_identity(None, git, cal_sha)
    code_sha = ident["git_head"]
    check_run_name(output_root, FsPath(decision_dir).name, "g8a", None, code_sha)
    targets = {E1_CELL: FsPath(e1_dir), P0_CELL: FsPath(p0_dir), "v4": FsPath(v4_dir)}
    attempts: dict[str, list[dict[str, Any]]] = {}
    for part, path in targets.items():
        found = attempt_dirs(output_root, "g7", part, code_sha)
        if not found or found[-1].resolve() != path.resolve():
            raise StopImplementation(f"G8a target for {part} must be its highest attempt "
                                     f"({found[-1].name if found else None})")
        attempts[part] = [_earlier_attempt(p, part) for p in found[:-1]]
    summary, g6_sha = _verified_g6(pilot_dir)
    timing = revalidate_g6_timing(pilot_dir)
    v4 = verify_v4_run(targets["v4"])
    if v4["status"] != "VERIFIED":
        raise StopImplementation("V-4 run is not VERIFIED")
    section = g7_manifest_g6_section(pilot_dir)
    by_cell: dict[str, list[dict[str, Any]]] = {}
    prov: dict[str, Any] = {}
    used = list(v4["v4"]["udr_sha256"])
    for cell in CORE_CELLS:
        d = targets[cell]
        if verify_run(d)["status"] != "COMPLETE":
            raise StopImplementation(f"{d.name} is not COMPLETE")
        spec, inputs, spec_sha, inputs_sha = _load_spec_inputs(d)
        manifest = json.loads((d / MANIFEST_FILE).read_bytes())
        if manifest["research"]["g6"] != json.loads(canonical_bytes(section)):
            raise StopImplementation(f"{d.name}: G6 section differs from the pilot's")
        if inputs["calibration_provenance"]["calibration_sha256"] != cal_sha:
            raise StopImplementation(f"{d.name}: calibration sha256 differs")
        used += manifest["research"]["udr_sha256"]
        for earlier in attempts[cell]:
            e = output_root / earlier["run_id"]
            for c, k, _, _ in _expected_units(spec):
                old, new = unit_paths(e, c, k)[0], unit_paths(d, c, k)[0]
                if old.exists() and unit_paths(e, c, k)[1].exists() and old.read_bytes() != new.read_bytes():
                    raise StopImplementation(f"{earlier['run_id']} unit {c}/{k} differs from {d.name}")
        by_cell[cell] = read_records(d, spec)[cell]
        prov[cell] = {"run_id": d.name, "run_spec_sha256": spec_sha, "run_inputs_sha256": inputs_sha,
                      "manifest_sha256": sha256_file(d / MANIFEST_FILE), "sha256sums_sha256": sha256_file(d / SUMS_FILE)}
    recheck_udrs(output_root, used)
    budget = core_attempts_budget(output_root, code_sha, timing)
    if not budget["time_accounting_complete"]:
        raise StopImplementation(f"{INCOMPLETE_TIME} in a CORE attempt: no G8a (R-6)")
    if budget["exceeded"]:
        raise StopImplementation("CORE global budget exceeded: no G8a")
    decision = decision_summary(by_cell, v4["v4"], cal["sigma"])
    payload = {"schema_version": DECISION_SCHEMA, "study_id": STUDY_ID, "evidence": EVIDENCE, "decision": decision,
               "provenance": {"runs": prov, "v4_sha256": v4["sha256"], "g6_summary_sha256": g6_sha,
                              "calibration_sha256": cal_sha, "code_sha": code_sha, "attempts": attempts,
                              "udr_sha256": sorted(set(used))}}
    data = canonical_bytes(json.loads(canonical_bytes(payload)))
    validate_decision_payload(json.loads(data), FsPath(decision_dir).name)
    return data, decision


def _decision_sums(data: bytes) -> bytes:
    return f"{_sha256(data)}  {DECISION_FILE}\n".encode("utf-8")


def g8a_decide(output_root: FsPath, *, decision_dir: FsPath, pilot_dir: FsPath, cal_dir: FsPath, e1_dir: FsPath,
               p0_dir: FsPath, v4_dir: FsPath, git: GitRunner = _git) -> dict[str, Any]:
    """R-6 G8a: g8a_payload, then decision_summary.json and its SHA256SUMS write-or-compare (a rerun recomputes and
    must produce the same bytes; damage is a STOP and is never repaired)."""
    d = FsPath(decision_dir)
    _only_files(d, (DECISION_FILE, SUMS_FILE))
    data, decision = g8a_payload(output_root, decision_dir=d, pilot_dir=pilot_dir, cal_dir=cal_dir, e1_dir=e1_dir,
                                 p0_dir=p0_dir, v4_dir=v4_dir, git=git)
    if (d / SUMS_FILE).exists() and not (d / DECISION_FILE).exists():
        raise StopImplementation("G8a SHA256SUMS without decision_summary.json")
    d.mkdir(parents=True, exist_ok=True)
    _write_or_compare(d / DECISION_FILE, data, DECISION_FILE)
    _write_or_compare(d / SUMS_FILE, _decision_sums(data), "G8a SHA256SUMS")
    return {"command": "g8a", "evidence": EVIDENCE, "status": "COMPLETE", "decision_sha256": _sha256(data),
            "labels": decision["labels"]}


def validate_decision_payload(payload: Mapping[str, Any], dir_name: str) -> None:
    """R-6 structure of decision_summary.json: exact fields; a label for each of the five hypotheses; provenance with
    the E1 / P0 target run hashes (run ids of this CODE_SHA's G7 runs), V-4 / G6 / calibration sha256, the CODE_SHA
    named by the directory, every earlier attempt of E1 / P0 / V-4 (run_id, state, UDR) and the sorted UDR set."""
    if not (isinstance(payload, Mapping) and set(payload) == set(DECISION_FIELDS)
            and (payload["schema_version"], payload["study_id"], payload["evidence"]) ==
            (DECISION_SCHEMA, STUDY_ID, EVIDENCE)):
        raise StopImplementation(f"{DECISION_FILE}: schema")
    labels = payload["decision"].get("labels") if isinstance(payload["decision"], Mapping) else None
    if not (isinstance(labels, Mapping) and set(labels) == set(HYPOTHESES) and all(
            isinstance(v, Mapping) and v.get("label") in (SUPPORTED, WEAKENED, INCONCLUSIVE, DEGENERACY_AMBIGUOUS)
            for v in labels.values())):
        raise StopImplementation(f"{DECISION_FILE}: labels of V-1, V-2, V-3, V-8 and V-4")
    prov = payload["provenance"]
    if not (isinstance(prov, Mapping) and set(prov) == set(DECISION_PROVENANCE_FIELDS)
            and isinstance(prov["code_sha"], str) and _HEX40.fullmatch(prov["code_sha"])
            and all(isinstance(prov[k], str) and _HEX64.fullmatch(prov[k])
                    for k in ("v4_sha256", "g6_summary_sha256", "calibration_sha256"))):
        raise StopImplementation(f"{DECISION_FILE}: provenance fields")
    code_sha = prov["code_sha"]
    if parse_run_id(dir_name)[:3] != ("g8a", None, code_sha[:12]):
        raise StopImplementation(f"{DECISION_FILE}: directory {dir_name} is not the G8a run of {code_sha[:12]}")
    runs, attempts, udrs = prov["runs"], prov["attempts"], prov["udr_sha256"]
    if not (isinstance(runs, Mapping) and set(runs) == set(CORE_CELLS)):
        raise StopImplementation(f"{DECISION_FILE}: target runs of both CORE cells")
    for cell, r in runs.items():
        if not (isinstance(r, Mapping) and set(r) == set(DECISION_RUN_FIELDS)
                and parse_run_id(str(r["run_id"]))[:3] == ("g7", cell, code_sha[:12])
                and all(isinstance(r[k], str) and _HEX64.fullmatch(r[k]) for k in DECISION_RUN_FIELDS[1:])):
            raise StopImplementation(f"{DECISION_FILE}: target run provenance of {cell}")
    if not (isinstance(attempts, Mapping) and set(attempts) == {*CORE_CELLS, "v4"}):
        raise StopImplementation(f"{DECISION_FILE}: earlier attempts of E1, P0 and V-4")
    for part, items in attempts.items():
        target_k = parse_run_id(str(runs[part]["run_id"]))[3] if part in runs else None
        for k, a in enumerate(items, 1):
            if not (isinstance(a, Mapping) and set(a) == set(ATTEMPT_FIELDS)
                    and parse_run_id(str(a["run_id"])) == ("g7", part, code_sha[:12], k)
                    and isinstance(a["udr_sha256"], list)):
                raise StopImplementation(f"{DECISION_FILE}: earlier attempt {k} of {part}")
        if target_k is not None and target_k != len(items) + 1:
            raise StopImplementation(f"{DECISION_FILE}: {part} target is not the attempt after the earlier ones")
    if not (isinstance(udrs, list) and udrs == sorted(set(udrs))
            and all(isinstance(u, str) and _HEX64.fullmatch(u) for u in udrs)):
        raise StopImplementation(f"{DECISION_FILE}: udr_sha256 must be the sorted distinct 64-hex set")


def verify_g8a_dir(decision_dir: FsPath) -> dict[str, Any]:
    """Read-only check of a G8a decision directory from its files alone: only decision_summary.json and SHA256SUMS
    (leftover *.tmp reported), canonical JSON with the R-6 structure (validate_decision_payload), SHA256SUMS exactly
    that file. ABSENT / INCOMPLETE (decision without SHA256SUMS) / VERIFIED; anything else is a STOP. reverify_g8a
    recomputes the decision from the runs."""
    d = FsPath(decision_dir)
    tmp = _only_files(d, (DECISION_FILE, SUMS_FILE))
    has_dec, has_sums = (d / DECISION_FILE).exists(), (d / SUMS_FILE).exists()
    if has_sums and not has_dec:
        raise StopImplementation("G8a SHA256SUMS without decision_summary.json")
    if not has_dec:
        return {"status": "ABSENT", "tmp": tmp}
    payload, raw = _read_canonical(d / DECISION_FILE, DECISION_FILE)
    validate_decision_payload(payload, d.name)
    if not has_sums:
        return {"status": "INCOMPLETE", "tmp": tmp, "decision_sha256": _sha256(raw)}
    if (d / SUMS_FILE).read_bytes() != _decision_sums(raw):
        raise StopImplementation("G8a SHA256SUMS does not match decision_summary.json")
    return {"status": "VERIFIED", "tmp": tmp, "decision_sha256": _sha256(raw)}


def reverify_g8a(output_root: FsPath, *, decision_dir: FsPath, pilot_dir: FsPath, cal_dir: FsPath, e1_dir: FsPath,
                 p0_dir: FsPath, v4_dir: FsPath, git: GitRunner = _git) -> dict[str, Any]:
    """Read-only re-verification (R-6 "재실행하면 다시 계산하고 바이트가 다르면 STOP"): the directory VERIFIED, then the
    whole decision recomputed from the target runs with every entry condition, byte-identical to the file."""
    state = verify_g8a_dir(decision_dir)
    if state["status"] != "VERIFIED":
        raise StopImplementation(f"G8a decision directory is {state['status']}")
    data, _ = g8a_payload(output_root, decision_dir=decision_dir, pilot_dir=pilot_dir, cal_dir=cal_dir,
                          e1_dir=e1_dir, p0_dir=p0_dir, v4_dir=v4_dir, git=git)
    if data != (FsPath(decision_dir) / DECISION_FILE).read_bytes():
        raise StopImplementation("recomputed decision_summary.json differs from the recorded one")
    return {**state, "recomputed": "IDENTICAL"}


# --- ERRATA-005 [C]: G5 calibration and pilot, G6 summarize -----------------------------------------------------------

def g5_calibrate(cal_dir: FsPath, *, workers: int, git: GitRunner = _git, udr_numbers: Sequence[int] = ()
                 ) -> dict[str, Any]:
    """G5 RESEARCH calibration (DC6, DC14): E1 edge on the 4,000-year FUTDIAG path and R_sigma = 2,000 FUTDIAG-SIGMA,
    under a clean CODE_SHA identity; calibration.json write-or-compare, times to its execution.json (never in W)."""
    if not (_positive_int(workers) and workers <= CORE_MAX_WORKERS):
        raise StopImplementation(f"workers must be 1..{CORE_MAX_WORKERS}, got {workers!r}")
    ident = research_identity(None, git)
    check_run_name(FsPath(cal_dir).parent, FsPath(cal_dir).name, "g5", "cal", ident["git_head"], udr_numbers)
    scan_calibration_dir(cal_dir)
    started, t0 = datetime.now(UTC), _clock()
    e1, times = calibrate_e1_timed(CALIB_YEARS)
    t_sigma = _clock()
    sigma = sigma_calibration(SIGMA_R, SIGMA_NAMESPACE, E_CAL, workers)
    phases = {"e1_noise_s": times["e1_noise_s"], "e1_search_s": times["e1_search_s"],
              "e1_post_s": times["e1_post_s"], "sigma_s": _clock() - t_sigma}
    cal = build_calibration(RESEARCH, e1, sigma, ident)
    sha = write_calibration(cal_dir, cal, None, git)
    record_calibration_run(cal_dir, calibration_run_record(started, datetime.now(UTC), _clock() - t0, workers, phases,
                                                           times["v4_eval_time_estimate"]))
    return {"command": "calibrate", "evidence": EVIDENCE, "status": "COMPLETE", "calibration": str(cal_dir),
            "calibration_sha256": sha}


def g5_pilot(run_dir: FsPath, cal_dir: FsPath, *, unit_size: int, workers: int, git: GitRunner = _git,
             udr_numbers: Sequence[int] = ()) -> dict[str, Any]:
    """G5 CORE pilot: both CORE cells, 200 replications each in FUTDIAG-PILOT, B = 1,999, from the RESEARCH
    calibration, under the clean CODE_SHA identity, with the research manifest block (no G6, no UDR)."""
    if not (_positive_int(workers) and workers <= CORE_MAX_WORKERS):
        raise StopImplementation(f"workers must be 1..{CORE_MAX_WORKERS}, got {workers!r}")
    cal, cal_sha = load_calibration(FsPath(cal_dir) / CALIBRATION_FILE)
    e1 = research_e1_cell(cal)
    ident = research_identity(None, git, cal_sha)
    check_stage_identity(cal["identity"], ident, cal_sha)                  # ERRATA-007: before the run directory
    check_run_name(FsPath(run_dir).parent, FsPath(run_dir).name, "g5", "pilot", ident["git_head"], udr_numbers)
    spec = build_run_spec(mode="pilot", code_sha=ident["git_head"], code_tree=ident["git_tree"],
                          config_sha256=ident["contract_sha256"]["config"],
                          prereg_sha256=ident["contract_sha256"]["prereg"], cells=list(CORE_CELLS),
                          windows=list(WINDOWS), rules=list(RULES), reps=PILOT_REPS, bootstrap=BOOTSTRAP_B,
                          unit_size=unit_size)
    inputs = build_run_inputs(spec, [e1, p0_cell()], RESEARCH_NAMESPACES["pilot"], calibration_provenance(cal, cal_sha))
    check_run_identity(spec, inputs, ident)
    block = research_block(spec, inputs, cal, cal_sha, None, [])
    counts = run_units(run_dir, spec, inputs, workers, research=block)
    status = verify_run(run_dir)
    if status["status"] != "COMPLETE":
        raise StopImplementation(f"pilot is not COMPLETE after run_units: {status}")
    return {"command": "pilot", "evidence": EVIDENCE, "status": "COMPLETE", "run": str(run_dir), "run_units": counts,
            "manifest_sha256": sha256_file(FsPath(run_dir) / MANIFEST_FILE)}


def g6_summarize(pilot_dir: FsPath, cal_dir: FsPath, *, git: GitRunner = _git) -> dict[str, Any]:
    """G6: write g6/ and execution.json g6_timing with the committed code, and report nuisance values, the P0 conf
    label, the budget judgment and the stops (no rejection rate, contrast, p-value or label of a hypothesis)."""
    cal, cal_sha = load_calibration(FsPath(cal_dir) / CALIBRATION_FILE)
    research_e1_cell(cal)
    ident = research_identity(None, git, cal_sha)
    check_stage_identity(cal["identity"], ident, cal_sha, read_pilot_spec(pilot_dir)[0])   # ERRATA-007: before g6/
    summary = write_g6(pilot_dir, cal, cal_sha)
    timing = write_g6_timing(pilot_dir, CORE_MAX_WORKERS, v4_eval_time_estimate(cal_dir))
    status = "COMPLETE" if not summary["stop_for_user_decision"] and timing["budget_pass"] \
        and summary["P0_CONF_CHECK"] == P0_CONF_PASS else "STOP_FOR_USER_DECISION"
    return {"command": "summarize", "evidence": EVIDENCE, "status": status, "r_c": summary["r_c"]["r_c"],
            "r_c_over_max": summary["r_c"]["over_max"], "pd5_stop": summary["pd5"]["stop"],
            "p2_status": summary["p2_spell"]["status"], "P0_CONF_CHECK": summary["P0_CONF_CHECK"],
            "stop_for_user_decision": summary["stop_for_user_decision"], "budget_pass": timing["budget_pass"],
            "worker_hours": timing["worker_hours"], "wall_hours": timing["wall_hours"]}


def rb1_reading(api: Any = None) -> dict[str, Any]:
    """RB-1 (R-9, separately approved, read-only): host_id and the S1 / S2 boot readings of this host, for the chat
    report. Creates no process, job or file."""
    api = api or win_api()
    reading = boot_reading(api)
    return {"host_id": host_id(api), **reading, "s1_minus_s2_s": (reading["s1"] - reading["s2"]) / 1e7}


# --- entry point (python -m moneylab.research.v06.futility_diag) ----------------------------------------------------
#
# cli.py and __main__.py are PROTECTED (WO:144); analysis runs only from committed code (WO:118). Commands:
#   smoke     the G4c fixture path (WO:397): TEST_FIXTURE calibration with a FUTDIAG-TEST sigma calibration, then both
#             CORE cells in FUTDIAG-TEST through run_units, then verify_run. A rerun on the same directories reuses
#             everything and must reproduce every deterministic byte (write-or-compare, never overwrite).
#   verify    read-only verify_run of an existing run directory (units, manifest, SHA256SUMS, execution record, g6/).
#   calibrate / pilot (G5), summarize (G6), g7 (G7), g8a (G8a): ERRATA-005, each only under its own gate.
#   udr       record one user approval line (R-0); lock-abandon (R-4, UDR + E-BOOT); lock-investigate (audit only).
# Every output directory is a direct child of data/processed/research_v06_futility_diag/ (WO:245), given as an
# absolute path; relative paths, "." / "..", nesting and symlinks / junctions are refused; run names follow R-7.

RESEARCH_OUTPUT_DIR = FsPath("data", "processed", "research_v06_futility_diag")
SMOKE_NAMESPACE = "FUTDIAG-TEST"
G4C_REPS, G4C_BOOTSTRAP, G4C_SIGMA_REPS = 20, 99, 20      # E2E_GATES G4c (WO:397)
_OUTPUT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
EXIT_COMPLETE, EXIT_INCOMPLETE, EXIT_STOP, EXIT_USER_DECISION = 0, 1, 2, 3


def _is_link(p: FsPath) -> bool:
    return p.is_symlink() or p.is_junction()


def checked_output_dir(arg: str, root: FsPath, must_exist: bool) -> FsPath:
    """An output directory: absolute, no "." / ".." part, a direct child of root named [A-Za-z0-9][A-Za-z0-9._-]*,
    neither it nor root a symlink / junction, and resolving exactly there. Anything else is a STOP."""
    if any(part in (".", "..") for part in re.split(r"[\\/]", arg)):
        raise StopImplementation(f"output path must not contain '.' or '..': {arg!r}")
    p, root = FsPath(arg), FsPath(root)
    if not p.is_absolute():
        raise StopImplementation(f"output path must be absolute: {arg!r}")
    if not root.is_dir() or _is_link(root) or root.resolve() != root.absolute():
        raise StopImplementation(f"output root {root} must be an existing real directory")
    if p.parent != root or not _OUTPUT_NAME.fullmatch(p.name):
        raise StopImplementation(f"output path must be a direct child of {root} with a plain name: {arg!r}")
    if _is_link(p):
        raise StopImplementation(f"output path is a symlink or junction: {arg!r}")
    if p.exists() and not p.is_dir():
        raise StopImplementation(f"output path is not a directory: {arg!r}")
    if must_exist and not p.is_dir():
        raise StopImplementation(f"run directory does not exist: {arg!r}")
    if p.resolve() != root.resolve() / p.name:
        raise StopImplementation(f"output path does not resolve inside {root}: {arg!r}")
    return p


def smoke(run_dir: FsPath, cal_dir: FsPath, *, unit_size: int, reps: int = G4C_REPS, bootstrap: int = G4C_BOOTSTRAP,
          sigma_reps: int = G4C_SIGMA_REPS, workers: int = 1, git: GitRunner = _git,
          udr_numbers: Sequence[int] = ()) -> dict[str, Any]:
    """The G4c fixture run. run_spec carries the clean CODE_SHA identity (research_identity: WO:403, G4c "clean C3");
    the calibration is TEST_FIXTURE (ERRATA-003 R-7) in FUTDIAG-TEST only, so nothing here is a research input.
    Directory names are g4c-smoke-<sha12> and g4c-cal-<sha12> (ERRATA-005 R-7)."""
    if not (_positive_int(workers) and workers <= CORE_MAX_WORKERS):
        raise StopImplementation(f"workers must be 1..{CORE_MAX_WORKERS}, got {workers!r}")
    if FsPath(run_dir) == FsPath(cal_dir):
        raise StopImplementation("the run and calibration directories must differ")
    ident = research_identity(None, git)
    for d, part in ((FsPath(run_dir), "smoke"), (FsPath(cal_dir), "cal")):
        check_run_name(d.parent, d.name, "g4c", part, ident["git_head"], udr_numbers)
    started, t0 = datetime.now(UTC), _clock()
    sigma = sigma_calibration(sigma_reps, SMOKE_NAMESPACE, E_CAL, workers)
    t_sigma = _clock()
    cal = build_calibration(TEST_FIXTURE, fixture_e1(), sigma, fixture_identity())
    cal_sha = _sha256(calibration_bytes(cal))
    spec = build_run_spec(mode="core", code_sha=ident["git_head"], code_tree=ident["git_tree"],
                          config_sha256=ident["contract_sha256"]["config"],
                          prereg_sha256=ident["contract_sha256"]["prereg"], cells=list(CORE_CELLS),
                          windows=list(WINDOWS), rules=list(RULES), reps=reps, bootstrap=bootstrap,
                          unit_size=unit_size)
    inputs = build_run_inputs(spec, [e1_cell(E_CAL, P0_DAILY_SD), p0_cell()], SMOKE_NAMESPACE,
                              calibration_provenance(cal, cal_sha))
    # nothing is written before both directories are known to accept these exact bytes
    for path, data, what in ((FsPath(cal_dir) / CALIBRATION_FILE, calibration_bytes(cal), "calibration"),
                             (FsPath(run_dir) / RUN_SPEC_FILE, run_spec_bytes(spec), "run_spec"),
                             (FsPath(run_dir) / RUN_INPUTS_FILE, canonical_bytes(dict(inputs)), "run_inputs")):
        if path.exists() and path.read_bytes() != data:
            raise StopImplementation(f"{what} differs from the existing {path.name}: refusing to change it")
    scan_calibration_dir(cal_dir)
    write_calibration(cal_dir, cal)
    record_calibration_run(cal_dir, calibration_run_record(started, datetime.now(UTC), _clock() - t0, workers,
                                                           {"sigma_s": t_sigma - t0}, None))
    counts = run_units(run_dir, spec, inputs, workers)
    status = verify_run(run_dir)
    if status["status"] != "COMPLETE":
        raise StopImplementation(f"smoke run is not COMPLETE after run_units: {status}")
    return {"command": "smoke", "evidence": EVIDENCE, "status": status["status"], "run": str(run_dir),
            "calibration": str(cal_dir), "calibration_sha256": cal_sha,
            "manifest_sha256": sha256_file(FsPath(run_dir) / MANIFEST_FILE),
            "sha256sums_sha256": sha256_file(FsPath(run_dir) / SUMS_FILE), "run_units": counts, "verify": status}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m moneylab.research.v06.futility_diag",
                                description="BT4-FUTILITY-01 DIAG (SYNTHETIC / NOT_EVIDENCE); each command runs only "
                                            "under its own gate authorization")
    sub = p.add_subparsers(dest="command", required=True)

    def cmd(name: str, help_: str, *dirs: str, udr: bool = True) -> argparse.ArgumentParser:
        c = sub.add_parser(name, help=help_)
        for d in dirs:
            c.add_argument(f"--{d}", required=True, help="absolute directory under the output root")
        if udr:
            c.add_argument("--udr", type=int, action="append", default=[], help="UDR number (repeatable)")
        return c

    s = cmd("smoke", "G4c fixture run (TEST_FIXTURE, FUTDIAG-TEST)", "run", "calibration")
    s.add_argument("--unit-size", type=int, required=True)
    s.add_argument("--reps", type=int, default=G4C_REPS)
    s.add_argument("--bootstrap", type=int, default=G4C_BOOTSTRAP)
    s.add_argument("--sigma-reps", type=int, default=G4C_SIGMA_REPS)
    s.add_argument("--workers", type=int, default=1)
    cmd("verify", "read-only check of an existing run directory", "run", udr=False)
    cmd("calibrate", "G5 RESEARCH calibration", "calibration").add_argument("--workers", type=int, required=True)
    pl = cmd("pilot", "G5 CORE pilot (FUTDIAG-PILOT)", "run", "calibration")
    pl.add_argument("--unit-size", type=int, required=True)
    pl.add_argument("--workers", type=int, required=True)
    cmd("summarize", "G6 nuisance summary and budget judgment", "run", "calibration", udr=False)
    g7 = cmd("g7", "G7 CORE main run (Windows, job object, lock)", "pilot", "calibration", "e1-run", "p0-run",
             "v4-run")
    g7.add_argument("--workers", type=int, required=True)
    g7.add_argument("--pool-failure-policy", required=True, help="exactly as in the G7 GATE_AUTHORIZATION")
    cmd("g8a", "G8a decision summary", "decision", "pilot", "calibration", "e1-run", "p0-run", "v4-run", udr=False)
    u = sub.add_parser("udr", help="record one USER_DECISION approval line (R-0)")
    u.add_argument("--line", required=True)
    u.add_argument("--reason", required=True)
    la = sub.add_parser("lock-abandon", help="abandon one unpaired G7 lock (LOCK_ABANDON UDR and E-BOOT only)")
    la.add_argument("--lock", type=int, required=True)
    la.add_argument("--udr", type=int, action="append", required=True)
    sub.add_parser("lock-investigate", help="read-only audit of one G7 lock").add_argument("--lock", type=int,
                                                                                           required=True)
    return p


def _dispatch(args: argparse.Namespace, root: FsPath, git: GitRunner) -> dict[str, Any]:
    def out(name: str, must_exist: bool = False) -> FsPath:
        return checked_output_dir(getattr(args, name), root, must_exist)

    if args.command == "smoke":
        root.mkdir(parents=True, exist_ok=True)
        return smoke(out("run"), out("calibration"), unit_size=args.unit_size, reps=args.reps,
                     bootstrap=args.bootstrap, sigma_reps=args.sigma_reps, workers=args.workers, git=git,
                     udr_numbers=args.udr)
    if args.command == "verify":
        run_dir = out("run", True)
        stage: str | None
        part: str | None
        try:
            stage, part = parse_run_id(run_dir.name)[:2]
        except StopImplementation:
            stage = part = None
        if stage == "g8a" or (stage, part) == ("g7", "v4"):     # R-6 / R-5 directories have their own files
            st = verify_g8a_dir(run_dir) if stage == "g8a" else verify_v4_run(run_dir)
            return {"command": "verify", "evidence": EVIDENCE, "run": str(run_dir), "directory": st["status"],
                    "sha256": st.get("decision_sha256", st.get("sha256")), "tmp": st["tmp"],
                    "status": "COMPLETE" if st["status"] == "VERIFIED" else "INCOMPLETE"}
        return {"command": "verify", "evidence": EVIDENCE, "run": str(run_dir), **verify_run(run_dir)}
    if args.command == "calibrate":
        root.mkdir(parents=True, exist_ok=True)
        return g5_calibrate(out("calibration"), workers=args.workers, git=git, udr_numbers=args.udr)
    if args.command == "pilot":
        return g5_pilot(out("run"), out("calibration", True), unit_size=args.unit_size, workers=args.workers,
                        git=git, udr_numbers=args.udr)
    if args.command == "summarize":
        return g6_summarize(out("run", True), out("calibration", True), git=git)
    if args.command == "g7":
        return g7_core(root, pilot_dir=out("pilot", True), cal_dir=out("calibration", True), e1_dir=out("e1_run"),
                       p0_dir=out("p0_run"), v4_dir=out("v4_run"), workers=args.workers,
                       pool_failure_policy=args.pool_failure_policy, udr_numbers=args.udr, git=git)
    if args.command == "g8a":
        return g8a_decide(root, decision_dir=out("decision"), pilot_dir=out("pilot", True),
                          cal_dir=out("calibration", True), e1_dir=out("e1_run", True), p0_dir=out("p0_run", True),
                          v4_dir=out("v4_run", True), git=git)
    if args.command == "udr":
        root.mkdir(parents=True, exist_ok=True)
        path, sha = write_udr(root, args.line, args.reason, research_identity(None, git)["git_head"])
        return {"command": "udr", "evidence": EVIDENCE, "status": "COMPLETE", "udr": path.name, "sha256": sha}
    if args.command == "lock-abandon":
        rec = abandon_lock(root, args.lock, args.udr, win_api())
        return {"command": "lock-abandon", "evidence": EVIDENCE, "status": "COMPLETE", **rec}
    return {"command": "lock-investigate", "evidence": EVIDENCE, "status": "COMPLETE",
            **lock_investigation(root, args.lock, win_api())}


def main(argv: Sequence[str] | None = None, *, output_root: FsPath | None = None, git: GitRunner = _git) -> int:
    """Exit 0 COMPLETE, 1 INCOMPLETE (verify), 2 STOP, 3 STOP_FOR_USER_DECISION; one canonical JSON line on stdout.
    output_root and git exist for tests; the command line always uses the repository's research output root."""
    args = _parser().parse_args(argv)
    root = FsPath(output_root) if output_root is not None else repo_root() / RESEARCH_OUTPUT_DIR
    try:
        result = _dispatch(args, root, git)
        if result.get("status") == "STOP_FOR_USER_DECISION":
            sys.stdout.write(canonical_bytes(result).decode("utf-8"))
            return EXIT_USER_DECISION
    except StopForUserDecision as exc:
        sys.stdout.write(canonical_bytes({"result": "STOP_FOR_USER_DECISION", "reason": str(exc)}).decode("utf-8"))
        return EXIT_USER_DECISION
    except StopImplementation as exc:
        sys.stdout.write(canonical_bytes({"result": "STOP", "reason": str(exc)}).decode("utf-8"))
        return EXIT_STOP
    sys.stdout.write(canonical_bytes(result).decode("utf-8"))
    return EXIT_COMPLETE if result["status"] == "COMPLETE" else EXIT_INCOMPLETE


if __name__ == "__main__":
    raise SystemExit(main())
