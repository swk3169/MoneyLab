"""Statistics for feature x horizon research (pure functions, stdlib only, deterministic).

No random shuffling anywhere. Uncertainty under overlapping labels and autocorrelation:
  * stationary block bootstrap (Politis & Romano 1994): blocks of geometric length with mean
    `mean_block` rows, circular wrap, seeded `random.Random`. Each statistic is computed from
    block sums (prefix sums), so a resample costs O(number of blocks).
    For Spearman IC the ranks are computed once on the full sample and the resampled statistic
    is the Pearson correlation of those ranks (standard approximation, avoids re-ranking).
  * Newey-West HAC standard error of the mean of z_x * z_y (whose mean is the correlation),
    Bartlett weights, lag = h + extra; two-sided normal p-value.
  * Benjamini-Hochberg q-values over every tested feature x horizon.
"""

from __future__ import annotations

import math
import random
import zlib
from collections.abc import Sequence
from dataclasses import dataclass

NAN = float("nan")
# Below these sample sizes the estimates are not meaningful and are reported as NaN (inconclusive):
MIN_BLOCKS = 5  # bootstrap: n >= MIN_BLOCKS * mean block length
MIN_LAG_MULTIPLE = 2  # HAC: n >= MIN_LAG_MULTIPLE * (lag + 1)


def finite_pairs(x: Sequence[float], y: Sequence[float]) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for a, b in zip(x, y, strict=True):
        if a == a and b == b and math.isfinite(a) and math.isfinite(b):
            xs.append(a)
            ys.append(b)
    return xs, ys


def mean(x: Sequence[float]) -> float:
    return sum(x) / len(x) if x else NAN


def std(x: Sequence[float]) -> float:
    if len(x) < 2:
        return NAN
    m = mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def rankdata(x: Sequence[float]) -> list[float]:
    """Average ranks (1-based), ties share their mean rank."""
    order = sorted(range(len(x)), key=lambda i: x[i])
    ranks = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    n = len(x)
    if n < 3:
        return NAN
    mx, my = mean(x), mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx <= 0 or syy <= 0:
        return NAN
    return sxy / math.sqrt(sxx * syy)


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    return pearson(rankdata(x), rankdata(y)) if len(x) >= 3 else NAN


def percentile(x: Sequence[float], q: float) -> float:
    if not x:
        return NAN
    xs = sorted(x)
    k = (len(xs) - 1) * q
    lo = math.floor(k)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


# --- quantiles (edges fitted on train only) ------------------------------------------------

def quantile_edges(train_x: Sequence[float], q: int) -> list[float]:
    """q-1 interior cut points of the training distribution."""
    return [percentile(train_x, i / q) for i in range(1, q)]


def assign_bin(v: float, edges: Sequence[float]) -> int:
    """0 .. len(edges); a value equal to an edge goes to the upper bin."""
    lo, hi = 0, len(edges)
    while lo < hi:
        mid = (lo + hi) // 2
        if v < edges[mid]:
            hi = mid
        else:
            lo = mid + 1
    return lo


@dataclass(frozen=True)
class QuantileResult:
    counts: tuple[int, ...]
    means: tuple[float, ...]  # mean future return per bin (NaN when empty)
    top_bottom: float  # mean(highest non-empty bin) - mean(lowest non-empty bin)
    monotonicity: float  # Spearman(bin index, bin mean) over non-empty bins (>= 3 needed)


def quantile_analysis(x: Sequence[float], y: Sequence[float], edges: Sequence[float]) -> QuantileResult:
    nb = len(edges) + 1
    sums, counts = [0.0] * nb, [0] * nb
    for a, b in zip(x, y):
        i = assign_bin(a, edges)
        sums[i] += b
        counts[i] += 1
    means = tuple(sums[i] / counts[i] if counts[i] else NAN for i in range(nb))
    filled = [i for i in range(nb) if counts[i]]
    tb = means[filled[-1]] - means[filled[0]] if len(filled) >= 2 else NAN
    mono = spearman([float(i) for i in filled], [means[i] for i in filled]) if len(filled) >= 3 else NAN
    return QuantileResult(tuple(counts), means, tb, mono)


def directional_accuracy(x: Sequence[float], y: Sequence[float], median: float, direction: int) -> tuple[float, int]:
    """Share of rows where sign(direction * (x - median)) == sign(y); zero moves and x == median
    are excluded. Returns (accuracy, rows used)."""
    hits = used = 0
    for a, b in zip(x, y):
        s = (a > median) - (a < median)
        if s == 0 or b == 0 or direction == 0:
            continue
        used += 1
        hits += (s * direction > 0) == (b > 0)
    return (hits / used if used else NAN), used


# --- HAC -------------------------------------------------------------------------------------

def newey_west_se(u: Sequence[float], lag: int) -> float:
    """HAC standard error of mean(u) with Bartlett weights."""
    n = len(u)
    if n < 3:
        return NAN
    m = mean(u)
    d = [v - m for v in u]
    s = sum(v * v for v in d) / n
    for L in range(1, min(lag, n - 1) + 1):
        w = 1 - L / (lag + 1)
        s += 2 * w * sum(d[i] * d[i - L] for i in range(L, n)) / n
    return math.sqrt(max(s, 0.0) / n)


def normal_two_sided_p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2)) if z == z else NAN


def hac_correlation_test(x: Sequence[float], y: Sequence[float], lag: int) -> tuple[float, float]:
    """(t statistic, p value) for corr(x, y) = 0 via the HAC mean of standardized products."""
    n = len(x)
    sx, sy = std(x), std(y)
    if n < max(3, MIN_LAG_MULTIPLE * (lag + 1)) or not (sx > 0 and sy > 0):
        return NAN, NAN
    mx, my = mean(x), mean(y)
    u = [(a - mx) / sx * (b - my) / sy for a, b in zip(x, y)]
    se = newey_west_se(u, lag)
    if not se > 0:
        return NAN, NAN
    t = mean(u) / se
    return t, normal_two_sided_p(t)


# --- stationary block bootstrap ---------------------------------------------------------------

def derived_seed(seed: int, *parts: str) -> int:
    """Stable per-test seed (crc32 is deterministic across runs, unlike hash())."""
    return (seed * 1_000_003 + zlib.crc32("|".join(parts).encode())) % (2**32)


def _blocks(n: int, mean_block: float, rng: random.Random) -> list[tuple[int, int]]:
    """Stationary bootstrap index blocks (start, length) covering exactly n rows (circular)."""
    p = 1.0 / max(mean_block, 1.0)
    out, total = [], 0
    while total < n:
        start = rng.randrange(n)
        length = 1
        while rng.random() >= p:
            length += 1
        length = min(length, n - total)
        out.append((start, length))
        total += length
    return out


class _Prefix:
    """Circular range sums of several series."""

    def __init__(self, *series: Sequence[float]):
        self.n = len(series[0])
        self.p = []
        for s in series:
            acc = [0.0]
            for v in s:
                acc.append(acc[-1] + v)
            self.p.append(acc)

    def block(self, i: int, start: int, length: int) -> float:
        p, n = self.p[i], self.n
        end = start + length
        if end <= n:
            return p[end] - p[start]
        return (p[n] - p[start]) + p[end - n]


def _ci(values: list[float], level: float) -> tuple[float, float]:
    vals = [v for v in values if v == v]
    if len(vals) < 10:
        return NAN, NAN
    a = (1 - level) / 2
    return percentile(vals, a), percentile(vals, 1 - a)


def bootstrap_corr_ci(x: Sequence[float], y: Sequence[float], *, mean_block: float, resamples: int, seed: int,
                      level: float = 0.95, rank: bool = True) -> tuple[float, float]:
    """Stationary-bootstrap percentile CI of Spearman (rank=True) or Pearson correlation."""
    n = len(x)
    if n < max(10, MIN_BLOCKS * mean_block):
        return NAN, NAN
    a, b = (rankdata(x), rankdata(y)) if rank else (list(x), list(y))
    pre = _Prefix(a, b, [u * v for u, v in zip(a, b)], [u * u for u in a], [v * v for v in b])
    rng = random.Random(seed)
    stats = []
    for _ in range(resamples):
        s = [0.0] * 5
        for start, length in _blocks(n, mean_block, rng):
            for i in range(5):
                s[i] += pre.block(i, start, length)
        sx, sy, sxy, sxx, syy = s
        vx, vy = sxx - sx * sx / n, syy - sy * sy / n
        stats.append((sxy - sx * sy / n) / math.sqrt(vx * vy) if vx > 0 and vy > 0 else NAN)
    return _ci(stats, level)


def bootstrap_ratio_ci(num: Sequence[float], den: Sequence[float], *, mean_block: float, resamples: int,
                       seed: int, level: float = 0.95) -> tuple[float, float]:
    """CI of sum(num) / sum(den) over a time-ordered series, e.g. mean net return per trigger
    with num = net * trigger, den = trigger (non-trigger rows keep the time structure)."""
    n = len(num)
    if n < max(10, MIN_BLOCKS * mean_block) or sum(den) <= 0:
        return NAN, NAN
    pre = _Prefix(num, den)
    rng = random.Random(seed)
    stats = []
    for _ in range(resamples):
        sn = sd = 0.0
        for start, length in _blocks(n, mean_block, rng):
            sn += pre.block(0, start, length)
            sd += pre.block(1, start, length)
        stats.append(sn / sd if sd > 0 else NAN)
    return _ci(stats, level)


# --- multiple testing ---------------------------------------------------------------------------

def benjamini_hochberg(pvalues: Sequence[float]) -> list[float]:
    """BH q-values in the input order; NaN p-values stay NaN and do not count as tests."""
    idx = [i for i, p in enumerate(pvalues) if p == p]
    m = len(idx)
    q = [NAN] * len(pvalues)
    if not m:
        return q
    order = sorted(idx, key=lambda i: pvalues[i])
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, pvalues[i] * m / rank)
        q[i] = min(running, 1.0)
    return q


def nonoverlapping_count(times: Sequence[float], spacing: float) -> int:
    """Greedy count of events at least `spacing` apart (times ascending)."""
    count, last = 0, -math.inf
    for t in times:
        if t - last >= spacing:
            count += 1
            last = t
    return count
