"""v0.6 test procedures (pure functions, stdlib only, deterministic given a seed).

Implements the DRAFT definitions (docs/research_v06_preregistration_draft.md, sections 8.1 and 10):
  * segment accounting (8.1): a segment starts in cash, a position held on the first day is a
    virtual entry, a position still held on the last day is a virtual exit; both pay the trade cost
  * H1: right-sided, H0 mu <= 0, centred stationary bootstrap of the mean
  * futility: left-sided, H0 mu >= delta, bootstrap shifted to the null boundary
  * max-T futility over several cost/delay scenarios that share one set of bootstrap indices
  * H2 / worse-than-random: matched random exposure (B1) randomization, right / left tail
  * Holm, IUT (S = both H1 and H2 rejected), R1-A REJECT combination (candidate, not adopted)

The stationary bootstrap index generator and prefix sums are reused unchanged from
`moneylab.research.stats` (the v0.4 module is not modified).
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from moneylab.research.stats import _blocks, _Prefix

ANNUALIZATION_DAYS = 365

# Strategy rules (draft 6.1). Signal for day d uses closes up to and including day d only.
STRATEGIES: dict[str, tuple[str, int]] = {
    "M20": ("momentum", 20),
    "M60": ("momentum", 60),
    "M120": ("momentum", 120),
    "R5": ("reversal", 5),
}


# --- signals and accounting --------------------------------------------------------------------

def signals(log_close: Sequence[float], rule: str, lookback: int) -> list[int | None]:
    """1 = hold, 0 = cash, None = not enough history. log_close[d] is the log close of day d."""
    out: list[int | None] = []
    for d, p in enumerate(log_close):
        if d < lookback:
            out.append(None)
            continue
        r = p - log_close[d - lookback]
        out.append(int(r > 0) if rule == "momentum" else int(r < 0))
    return out


def trade_cost_log(fee_bps: float, slip_bps: float, impact_bps: float) -> float:
    """Log wealth multiplier of one trade (entry or exit): ln((1 - f)(1 - kappa - iota))."""
    return math.log(1.0 - fee_bps / 1e4) + math.log(1.0 - (slip_bps + impact_bps) / 1e4)


def segment_returns(market: Sequence[float], positions: Sequence[int], trade_cost: float) -> list[float]:
    """Daily net log returns of one segment (draft 8.1). market[t] is the market log return over
    segment day t and positions[t] the position held over it. A change of position at day t pays
    the trade cost on day t; the segment starts in cash and a position open on the last day pays a
    virtual exit on that day. Nothing outside the segment is read."""
    if len(market) != len(positions):
        raise ValueError("market and positions differ in length")
    out, prev = [], 0
    for r, p in zip(market, positions):
        v = p * r
        if p != prev:
            v += trade_cost
        out.append(v)
        prev = p
    if out and prev == 1:
        out[-1] += trade_cost
    return out


def runs(positions: Sequence[int]) -> tuple[int, list[int], list[int], int]:
    """(leading cash days, holding spell lengths, inner cash gap lengths, trailing cash days)."""
    spells, gaps = [], []
    n = len(positions)
    i = 0
    while i < n and positions[i] == 0:
        i += 1
    lead = i
    while i < n:
        j = i
        while j < n and positions[j] == 1:
            j += 1
        spells.append(j - i)
        k = j
        while k < n and positions[k] == 0:
            k += 1
        if k < n:
            gaps.append(k - j)
        else:
            return lead, spells, gaps, k - j
        i = k
    return lead, spells, gaps, 0


def roundtrips(positions: Sequence[int]) -> int:
    return len(runs(positions)[1])


def mean(x: Sequence[float]) -> float:
    return sum(x) / len(x)


def sd(x: Sequence[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    m = sum(x) / n
    return math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))


def annual_sharpe(x: Sequence[float]) -> float:
    s = sd(x)
    return mean(x) / s * math.sqrt(ANNUALIZATION_DAYS) if s > 0 else 0.0


def max_drawdown(log_returns: Sequence[float]) -> float:
    """Largest peak-to-trough loss of wealth, as a fraction (0..1)."""
    peak = level = 0.0
    worst = 0.0
    for r in log_returns:
        level += r
        peak = max(peak, level)
        worst = max(worst, peak - level)
    return 1.0 - math.exp(-worst)


# --- stationary bootstrap ---------------------------------------------------------------------

def bootstrap_means(series: Sequence[Sequence[float]], *, mean_block: float, resamples: int,
                    seed: int) -> list[list[float]]:
    """Resampled means of every series with ONE shared set of stationary-bootstrap index blocks
    (so the joint dependence between series is kept). Returns [series][resample]."""
    if not series:
        return []
    n = len(series[0])
    if n == 0 or any(len(s) != n for s in series):
        raise ValueError("series must be non-empty and of equal length")
    pre = _Prefix(*series)
    rng = random.Random(seed)
    k = len(series)
    out = [[0.0] * resamples for _ in range(k)]
    for b in range(resamples):
        sums = [0.0] * k
        for start, length in _blocks(n, mean_block, rng):
            for i in range(k):
                sums[i] += pre.block(i, start, length)
        for i in range(k):
            out[i][b] = sums[i] / n
    return out


def _mc_p(count: int, total: int) -> float:
    return (1 + count) / (total + 1)


def h1_pvalue(m: float, boot: Sequence[float]) -> float:
    """H0 mu <= 0 vs mu > 0. Centred resample means boot_b - m; p = (1 + #{boot_b - m >= m}) / (B + 1)."""
    return _mc_p(sum(1 for x in boot if x - m >= m), len(boot))


def futility_pvalue(m: float, boot: Sequence[float], delta: float) -> float:
    """H0 mu >= delta vs mu < delta. The series shifted to the null boundary, r - m + delta, has
    resample means boot_b - m + delta; p = (1 + #{boot_b - m + delta <= m}) / (B + 1)."""
    return _mc_p(sum(1 for x in boot if x - m + delta <= m), len(boot))


def futility_delta(theta_min: float, series: Sequence[float]) -> float:
    """Minimum meaningful daily mean: annual Sharpe theta_min at the series' own volatility."""
    return theta_min * sd(series) / math.sqrt(ANNUALIZATION_DAYS)


def maxt_futility_pvalue(ms: Sequence[float], boots: Sequence[Sequence[float]],
                         deltas: Sequence[float]) -> float:
    """Joint futility over several scenarios (e.g. E0, E1, E2) that share bootstrap indices.
    Intersection null: every scenario has mu_j >= delta_j. Statistic min_j (m_j - delta_j) / se_j,
    se_j = bootstrap sd; null resamples (boot_jb - m_j) / se_j. Scenarios with se_j = 0 are skipped;
    if none remain p = 1."""
    paths = []
    for m, boot, delta in zip(ms, boots, deltas):
        se = sd(boot)
        if se > 0:
            paths.append((m, boot, delta, se))
    if not paths:
        return 1.0
    observed = min((m - d) / se for m, _, d, se in paths)
    resamples = len(paths[0][1])
    count = 0
    for b in range(resamples):
        if min((boot[b] - m) / se for m, boot, _, se in paths) <= observed:
            count += 1
    return _mc_p(count, resamples)


# --- matched random exposure (B1) ---------------------------------------------------------------

def b1_positions(positions: Sequence[int], rng: random.Random) -> list[int]:
    """One B1 draw: shuffle holding spells and inner cash gaps independently, split the leading +
    trailing cash at random. Same exposure days, spell lengths and number of trades."""
    lead, spells, gaps, trail = runs(positions)
    if not spells:
        return [0] * len(positions)
    sp, gp = spells[:], gaps[:]
    rng.shuffle(sp)
    rng.shuffle(gp)
    l0 = rng.randint(0, lead + trail)
    out = [0] * l0
    for i, s in enumerate(sp):
        out.extend([1] * s)
        if i < len(gp):
            out.extend([0] * gp[i])
    out.extend([0] * (len(positions) - len(out)))
    return out


def b1_means(market: Sequence[float], positions: Sequence[int], trade_cost: float, draws: int,
             seed: int) -> list[float]:
    """Mean net log return of `draws` B1 placements (same accounting as segment_returns: every
    spell pays an entry and an exit). Uses the same rng sequence as b1_positions."""
    n = len(market)
    prefix = [0.0]
    for r in market:
        prefix.append(prefix[-1] + r)
    lead, spells, gaps, trail = runs(positions)
    rng = random.Random(seed)
    if not spells:
        return [0.0] * draws
    cost = 2 * len(spells) * trade_cost
    out = []
    for _ in range(draws):
        sp, gp = spells[:], gaps[:]
        rng.shuffle(sp)
        rng.shuffle(gp)
        pos = rng.randint(0, lead + trail)
        held = 0.0
        for i, s in enumerate(sp):
            held += prefix[pos + s] - prefix[pos]
            pos += s
            if i < len(gp):
                pos += gp[i]
        out.append((held + cost) / n)
    return out


def randomization_pvalues(m: float, draws: Sequence[float]) -> tuple[float, float]:
    """(p2, p2low): right tail (better than random) and left tail (worse than random)."""
    k = len(draws)
    return (_mc_p(sum(1 for x in draws if x >= m), k), _mc_p(sum(1 for x in draws if x <= m), k))


# --- multiple testing -----------------------------------------------------------------------------

def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values in input order (valid under any dependence)."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adj = [1.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adj[i] = running
    return adj


def iut_holm(p1: Sequence[float], p2: Sequence[float]) -> list[float]:
    """S claim per strategy = reject both H1 and H2. pS = max(p1, p2) is valid for the union null;
    Holm over the strategies."""
    return holm([max(a, b) for a, b in zip(p1, p2)])


def r1a_reject_pvalue(p_maxt: float, p2low: float) -> float:
    """R1-A (candidate): the REJECT claim's null is the intersection of 'every scenario >= delta'
    (max-T bootstrap) and 'not worse than random' (B1). The two use different resampling schemes,
    so they are combined by Bonferroni."""
    return min(1.0, 2.0 * min(p_maxt, p2low))
