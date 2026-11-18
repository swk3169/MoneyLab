"""FUTVAL-V8-01: finite-sample rejection rate of the V0 futility test on iid Normal boundaries.

Implements the frozen preregistration docs/research_futval_v8_01_preregistration.md (sha256
d77549ed4cc732f0b2fb0151fcf17913d319ce8e0de929827fc3a8c9c7ea9b91). The section numbers in the comments
(§2 .. §10) refer to that document. The procedures and stats modules are called unchanged.

Operational sub-commands (seed-check, smoke, perf, run) exist for later, separately approved gates.
Small R, B and cell sets are accepted only in the FUTVAL-V8-01-TEST namespace.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import multiprocessing
import os
import platform
import random
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

from moneylab.research import stats
from moneylab.research.v06 import procedures as P
from moneylab.storage import atomic

# --- identity and fixed design (§0, §1, §3, §4, §6) ---------------------------------------------------------------

STUDY_ID = "FUTVAL-V8-01"
PREREG_PATH = "docs/research_futval_v8_01_preregistration.md"
PREREG_SHA256 = "d77549ed4cc732f0b2fb0151fcf17913d319ce8e0de929827fc3a8c9c7ea9b91"
PREREG_VERSION = "v1"
DECISION_VERSION = "FUTVAL-V8-01-decision/1"

NS_MAIN = "FUTVAL-V8-01"
NS_PERF = "FUTVAL-V8-01-PERF"
NS_TEST = "FUTVAL-V8-01-TEST"
NAMESPACES = (NS_MAIN, NS_PERF, NS_TEST)
STREAMS = ("data", "boot")

BASE = 20261118
N_VALUES = (365, 731, 1096, 2227)
THETAS = ("0.3", "0.5", "0.7")
CELLS: tuple[tuple[int, str], ...] = tuple((n, th) for n in N_VALUES for th in THETAS)  # n, then theta, ascending
R = 10_000
B = 9_999
MEAN_BLOCK = 20
SIGMA = 0.70 / math.sqrt(365.0)

ALPHA = Fraction(1, 20)
EPSILON = Fraction(1, 100)
TOLERANCE = ALPHA + EPSILON  # 3/50
LAMBDA = Fraction(1, 40)
REJECT_P = float(ALPHA)  # the nearest double to 0.05; p = (1 + count)/(B + 1) <= 0.05  <=>  count <= 499 for B 9999

REL_TOL = 1e-9
CP_WIDTH = 1e-10
CP_MAX_ITER = 200
CP_LEVEL = 0.025

SMOKE_REPS = 2
PERF_THETA = "0.5"
PERF_REPS = 20
CHUNK = 250

SMOKE_SCHEMA = "moneylab.futval_v8_01.smoke/1"
PERF_SCHEMA = "moneylab.futval_v8_01.perf/1"
RESULT_FILES = ("manifest.json", "design.json", "cells.json", "summary.json")
SUMS_FILE = "SHA256SUMS"
EXECUTION_FILE = "execution.json"

SERIALIZATION = 'ns + "|v1|BASE=" + str(BASE) + "|n=" + str(n) + "|theta=" + th + "|rep=" + str(rep) + "|stream=" + st'
RNG_PATH = "random.Random (MT19937): data via gauss(0.0, 1.0); boot via procedures.bootstrap_means -> stats._blocks"

SOURCE_FILES = ("src/moneylab/research/v06/procedures.py", "src/moneylab/research/stats.py",
                "src/moneylab/research/v06/futval_v8_01.py", "tests/test_futval_v8_01.py")
EXPECTED_SOURCE_BLOBS = {"src/moneylab/research/v06/procedures.py": "bf6dfddea822f3af0d6e50274c8b3b5b0c767daf",
                         "src/moneylab/research/stats.py": "01b6472cadb2ce2437a613b09d419a999398c685"}
TARGETS: tuple[tuple[str, Any], ...] = (
    ("procedures.mean", P.mean), ("procedures.sd", P.sd), ("procedures.futility_delta", P.futility_delta),
    ("procedures.bootstrap_means", P.bootstrap_means), ("procedures.futility_pvalue", P.futility_pvalue),
    ("procedures._mc_p", P._mc_p), ("stats._blocks", stats._blocks), ("stats._Prefix", stats._Prefix))

NORMAL = "NORMAL"
DEGENERATE = "DEGENERATE"
SIZE_EXCESS_CONFIRMED = "SIZE_EXCESS_CONFIRMED"
SIZE_EXCESS_NOT_CONFIRMED = "SIZE_EXCESS_NOT_CONFIRMED"
WITHIN_TOLERANCE_SHOWN = "WITHIN_TOLERANCE_SHOWN"
WITHIN_TOLERANCE_NOT_SHOWN = "WITHIN_TOLERANCE_NOT_SHOWN"


class StopRun(Exception):
    """A preregistered STOP. The code is fixed text; no values are carried in the message."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ComputationFailure(StopRun):
    """§7: a numerical computation failure. It is not a research result and no judgment is made."""

    def __init__(self) -> None:
        super().__init__("COMPUTATION_FAILURE")


# --- §4 seeds -------------------------------------------------------------------------------------------------------

def seed_string(ns: str, n: int, th: str, rep: int, stream: str) -> str:
    if ns not in NAMESPACES or th not in THETAS or stream not in STREAMS:
        raise ValueError("namespace, theta or stream outside the preregistered sets")
    if n < 1 or rep < 0:
        raise ValueError("n must be positive and rep non-negative")
    return ns + "|v1|BASE=" + str(BASE) + "|n=" + str(n) + "|theta=" + th + "|rep=" + str(rep) + "|stream=" + stream


def seed(ns: str, n: int, th: str, rep: int, stream: str) -> int:
    return int.from_bytes(hashlib.sha256(seed_string(ns, n, th, rep, stream).encode("utf-8")).digest()[:8], "big")


def seed_uniqueness(ns: str, cells: Sequence[tuple[int, str]], reps: int,
                    seed_fn: Callable[[str, int, str, int, str], int] = seed) -> dict[str, Any]:
    """Seed values only: no data, no p values. A duplicate is a STOP (§4)."""
    values = [seed_fn(ns, n, th, rep, st) for n, th in cells for rep in range(reps) for st in STREAMS]
    distinct = len(set(values))
    result = {"namespace": ns, "count": len(values), "distinct": distinct, "pass": distinct == len(values)}
    if not result["pass"]:
        raise StopRun("SEED_DUPLICATE")
    return result


# --- §3 data and §2 V0 ----------------------------------------------------------------------------------------------

def p0_parameters(th: str) -> tuple[float, float]:
    """(mu, sigma) with annual Sharpe mu / sigma * sqrt(365) = theta."""
    return float(th) * SIGMA / math.sqrt(365.0), SIGMA


def generate_p0(n: int, th: str, data_seed: int) -> list[float]:
    mu, sigma = p0_parameters(th)
    rng = random.Random(data_seed)
    return [mu + sigma * rng.gauss(0.0, 1.0) for _ in range(n)]


def v0_statistics(r: Sequence[float], th: str, boot_seed: int, b: int) -> tuple[float, float, float, float]:
    """(m, s, delta_hat, p) by calling the preregistered procedures functions unchanged (§2)."""
    m = P.mean(r)
    s = P.sd(r)
    delta = P.futility_delta(float(th), r)
    boot = P.bootstrap_means([r], mean_block=MEAN_BLOCK, resamples=b, seed=boot_seed)[0]
    p = P.futility_pvalue(m, boot, delta)
    return m, s, delta, p


def v0_replicate(r: Sequence[float], th: str, boot_seed: int, b: int) -> tuple[str, int | None]:
    """NORMAL with the rejection indicator, or DEGENERATE (§5). Exceptions propagate and stop the run."""
    m, s, delta, p = v0_statistics(r, th, boot_seed, b)
    if not s > 0 or not all(math.isfinite(x) for x in (m, delta, p)):
        return DEGENERATE, None
    return NORMAL, 1 if p <= REJECT_P else 0


# --- §7 method 1: exact integer tails and thresholds ----------------------------------------------------------------

def _pmf_numerators(reps: int, prob: Fraction) -> tuple[list[int], int]:
    """Integer numerators C(R, i) a^i (d - a)^(R - i) over the common denominator d^R."""
    a, d = prob.numerator, prob.denominator
    q = d - a
    pa = [1] * (reps + 1)
    pq = [1] * (reps + 1)
    for i in range(1, reps + 1):
        pa[i] = pa[i - 1] * a
        pq[i] = pq[i - 1] * q
    out, c = [], 1
    for i in range(reps + 1):
        out.append(c * pa[i] * pq[reps - i])
        c = c * (reps - i) // (i + 1)
    return out, d ** reps


def exact_upper_tail(reps: int, prob: Fraction, k: int) -> Fraction:
    """P(Bin(R, prob) >= k), exact."""
    if k <= 0:
        return Fraction(1)
    if k > reps:
        return Fraction(0)
    nums, den = _pmf_numerators(reps, prob)
    return Fraction(sum(nums[k:]), den)


def exact_lower_tail(reps: int, prob: Fraction, x: int) -> Fraction:
    """P(Bin(R, prob) <= x), exact."""
    if x < 0:
        return Fraction(0)
    if x >= reps:
        return Fraction(1)
    nums, den = _pmf_numerators(reps, prob)
    return Fraction(sum(nums[:x + 1]), den)


def holm_levels(m: int) -> list[Fraction]:
    """t_j = lambda / (m + 1 - j), j = 1..m. With m = 12 this is lambda / (13 - j) (§6)."""
    return [LAMBDA / (m + 1 - j) for j in range(1, m + 1)]


def axis_a_thresholds(reps: int, levels: Sequence[Fraction]) -> list[int]:
    """a_j = the smallest integer a with P(Bin(R, alpha) >= a) <= t_j (R + 1 if none)."""
    nums, den = _pmf_numerators(reps, ALPHA)
    suffix = [0] * (reps + 2)
    for i in range(reps, -1, -1):
        suffix[i] = suffix[i + 1] + nums[i]
    out = []
    for t in levels:
        a = reps + 1
        for k in range(reps, -1, -1):
            if suffix[k] * t.denominator <= t.numerator * den:  # exact: suffix/den <= t
                a = k
            else:
                break
        out.append(a)
    return out


def axis_b_threshold(reps: int) -> int:
    """b = the largest integer x with P(Bin(R, 3/50) <= x) <= lambda (-1 if none)."""
    nums, den = _pmf_numerators(reps, TOLERANCE)
    b, total = -1, 0
    for x in range(reps + 1):
        total += nums[x]
        if total * LAMBDA.denominator <= LAMBDA.numerator * den:  # exact: total/den <= lambda
            b = x
        else:
            break
    return b


# --- §7 method 2: log-space tails (verification and reporting) ------------------------------------------------------

def _log_pmf(reps: int, prob: float, i: int) -> float:
    return (math.lgamma(reps + 1) - math.lgamma(i + 1) - math.lgamma(reps - i + 1)
            + i * math.log(prob) + (reps - i) * math.log1p(-prob))


def _log_sum_exp(values: Iterable[float]) -> float:
    vs = list(values)
    if not vs:
        return -math.inf
    top = max(vs)
    return top + math.log(sum(math.exp(v - top) for v in vs))


def log_upper_tail(reps: int, prob: float, k: int) -> float:
    if k <= 0:
        return 1.0
    if k > reps:
        return 0.0
    return math.exp(_log_sum_exp(_log_pmf(reps, prob, i) for i in range(k, reps + 1)))


def log_lower_tail(reps: int, prob: float, x: int) -> float:
    if x < 0:
        return 0.0
    if x >= reps:
        return 1.0
    return math.exp(_log_sum_exp(_log_pmf(reps, prob, i) for i in range(0, x + 1)))


def _check_point(kind: str, reps: int, point: int, level: Fraction) -> dict[str, Any]:
    if kind == "A":
        exact = exact_upper_tail(reps, ALPHA, point)
        approx = log_upper_tail(reps, float(ALPHA), point)
    else:
        exact = exact_lower_tail(reps, TOLERANCE, point)
        approx = log_lower_tail(reps, float(TOLERANCE), point)
    if not math.isfinite(approx):
        raise ComputationFailure()
    ex = float(exact)
    rel = abs(approx - ex) / ex if ex > 0 else abs(approx)
    same = (exact <= level) == (approx <= float(level))
    if rel > REL_TOL or not same:
        raise ComputationFailure()
    return {"axis": kind, "point": point, "level": str(level), "method1": repr(ex), "method2": repr(approx),
            "relative_error": repr(rel), "same_direction": same}


def verify_thresholds(reps: int, a: Sequence[int], levels: Sequence[Fraction], b: int) -> list[dict[str, Any]]:
    """Check each threshold and its neighbour with both methods (§7). Any disagreement is COMPUTATION_FAILURE."""
    records = []
    for aj, t in zip(a, levels):
        for point in (aj, aj - 1):
            if 0 <= point <= reps:
                records.append(_check_point("A", reps, point, t))
    for point in (b, b + 1):
        if 0 <= point <= reps:
            records.append(_check_point("B", reps, point, LAMBDA))
    return records


# --- §6 decisions ---------------------------------------------------------------------------------------------------

def holm_axis_a(k: Sequence[int], a: Sequence[int]) -> list[bool]:
    """Holm via counts: sort by K descending (ties by fixed cell order), reject while K_(j) >= a_j."""
    if len(a) != len(k):
        raise ValueError("one threshold per cell is required")
    order = sorted(range(len(k)), key=lambda c: (-k[c], c))
    rejected = [False] * len(k)
    for j, c in enumerate(order):
        if k[c] >= a[j]:
            rejected[c] = True
        else:
            break
    return rejected


def axis_b(x: Sequence[int], b: int) -> list[bool]:
    return [v <= b for v in x]


def cp_interval(reps: int, x: int, max_iter: int = CP_MAX_ITER) -> dict[str, Any]:
    """Two-sided 95% Clopper-Pearson by bisection on method-2 tails; report only (§6, §7)."""
    def bisect(f: Callable[[float], bool]) -> tuple[float, float, bool]:
        lo, hi = 0.0, 1.0  # f(lo) is False, f(hi) is True
        for _ in range(max_iter):
            if hi - lo <= CP_WIDTH:
                return lo, hi, True
            mid = (lo + hi) / 2.0
            if f(mid):
                hi = mid
            else:
                lo = mid
        return lo, hi, hi - lo <= CP_WIDTH

    converged = True
    if x == 0:
        lower = 0.0
    else:
        _, lower, ok = bisect(lambda p: log_upper_tail(reps, p, x) > CP_LEVEL)
        converged = converged and ok
    if x == reps:
        upper = 1.0
    else:
        upper, _, ok = bisect(lambda p: not log_lower_tail(reps, p, x) > CP_LEVEL)
        converged = converged and ok
    return {"x": x, "lower": round(lower, 6), "upper": round(upper, 6),
            "status": "CONVERGED" if converged else "CP_NOT_CONVERGED"}


def evaluate(counts: Sequence[tuple[int, int]], reps: int, cells: Sequence[tuple[int, str]]
             ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    """Thresholds, verification and both axes for (K_c, D_c) per cell. Returns design part, cells and summary."""
    levels = holm_levels(len(cells))
    a = axis_a_thresholds(reps, levels)
    b = axis_b_threshold(reps)
    checks = verify_thresholds(reps, a, levels, b)
    ks = [k for k, _ in counts]
    xb = [k + d for k, d in counts]
    rej_a = holm_axis_a(ks, a)
    ok_b = axis_b(xb, b)
    cell_rows = []
    for (n, th), (k, d), ra, rb in zip(cells, counts, rej_a, ok_b):
        p_a = log_upper_tail(reps, float(ALPHA), k)
        p_b = log_lower_tail(reps, float(TOLERANCE), k + d)
        if not (math.isfinite(p_a) and math.isfinite(p_b)):
            raise ComputationFailure()
        cell_rows.append({"n": n, "theta": th, "K": k, "D": d, "p_A_report": repr(p_a), "p_B_report": repr(p_b),
                          "axis_A": SIZE_EXCESS_CONFIRMED if ra else SIZE_EXCESS_NOT_CONFIRMED,
                          "axis_B": WITHIN_TOLERANCE_SHOWN if rb else WITHIN_TOLERANCE_NOT_SHOWN,
                          "cp_K": cp_interval(reps, k), "cp_K_plus_D": cp_interval(reps, k + d)})
    design = {"holm_levels": [str(t) for t in levels], "a": a, "b": b, "threshold_checks": checks}
    summary = {"ANY_SIZE_EXCESS_CONFIRMED": "YES" if any(rej_a) else "NO",
               "ALL_CELLS_WITHIN_TOLERANCE_SHOWN": "YES" if all(ok_b) else "NO"}
    return design, cell_rows, summary


# --- workers --------------------------------------------------------------------------------------------------------

def _peak_memory_bytes() -> int | None:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class _Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

        counters = _Counters()
        counters.cb = ctypes.sizeof(counters)
        try:
            handle = ctypes.windll.kernel32.GetCurrentProcess()  # type: ignore[attr-defined]
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters),  # type: ignore[attr-defined]
                                                          counters.cb)
        except (AttributeError, OSError):
            return None
        return int(counters.PeakWorkingSetSize) if ok else None
    try:
        import resource
    except ImportError:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak) * (1 if sys.platform == "darwin" else 1024)


def _work(task: tuple[str, int, str, int, int, int]) -> tuple[int, int, float, int | None, list[float]]:
    """One chunk of one cell: (K, D, cpu seconds, peak memory, per-rep wall seconds)."""
    ns, n, th, start, stop, b = task
    cpu0 = time.process_time()
    k = d = 0
    walls = []
    for rep in range(start, stop):
        w0 = time.perf_counter()
        r = generate_p0(n, th, seed(ns, n, th, rep, "data"))
        kind, ind = v0_replicate(r, th, seed(ns, n, th, rep, "boot"), b)
        walls.append(time.perf_counter() - w0)
        if kind == DEGENERATE:
            d += 1
        elif ind == 1:
            k += 1
    return k, d, time.process_time() - cpu0, _peak_memory_bytes(), walls


def _tasks(ns: str, cells: Sequence[tuple[int, str]], reps: int, b: int) -> list[tuple[str, int, str, int, int, int]]:
    return [(ns, n, th, s, min(s + CHUNK, reps), b) for n, th in cells for s in range(0, reps, CHUNK)]


def _execute(tasks: Sequence[tuple[str, int, str, int, int, int]], workers: int
             ) -> list[tuple[int, int, float, int | None, list[float]]]:
    if workers < 1:
        raise ValueError("workers must be at least 1")
    if workers == 1:
        return [_work(t) for t in tasks]
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        return list(pool.map(_work, tasks))


# --- §9 provenance --------------------------------------------------------------------------------------------------

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


LOADED_SOURCES = ("src/moneylab/research/v06/procedures.py", "src/moneylab/research/stats.py",
                  "src/moneylab/research/v06/futval_v8_01.py")


def _loaded_files() -> dict[str, Path]:
    return {LOADED_SOURCES[0]: Path(P.__file__), LOADED_SOURCES[1]: Path(stats.__file__),
            LOADED_SOURCES[2]: Path(__file__)}


def _same_file(a: Path, b: Path) -> bool:
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def git_provenance(root: Path | None = None, loaded: dict[str, Path] | None = None) -> dict[str, Any]:
    """Verify the sources before any data, bootstrap or result work (§2, §9), then return the provenance.

    STOP when a loaded module is not the file under `root`, when a protected file's HEAD blob is not the
    preregistered blob, or when any source file's working bytes (CRLF read as LF, in memory only) differ from its
    HEAD blob. Limitation: this compares files on disk. It does not authenticate code already in memory, other
    imported modules, or changes made while the run is in progress.
    """
    root = Path(root) if root is not None else _repo_root()
    loaded = _loaded_files() if loaded is None else loaded
    for rel in LOADED_SOURCES:
        if rel not in loaded or not _same_file(loaded[rel], root / rel):
            raise StopRun("SOURCE_LOCATION_MISMATCH")

    def git(*args: str) -> bytes:
        try:
            return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise StopRun("SOURCE_GIT_FAILED") from exc

    commit = git("rev-parse", "HEAD").decode("ascii").strip()
    files = {}
    for rel in SOURCE_FILES:
        blob = git("rev-parse", f"HEAD:{rel}").decode("ascii").strip()
        if rel in EXPECTED_SOURCE_BLOBS and blob != EXPECTED_SOURCE_BLOBS[rel]:
            raise StopRun("SOURCE_BLOB_MISMATCH")
        head = git("cat-file", "blob", blob)
        try:
            work = (root / rel).read_bytes().replace(b"\r\n", b"\n")
        except OSError as exc:
            raise StopRun("SOURCE_WORKTREE_MISMATCH") from exc
        if work != head:
            raise StopRun("SOURCE_WORKTREE_MISMATCH")
        files[rel] = {"blob": blob, "sha256_lf": hashlib.sha256(head).hexdigest()}
    return {"commit": commit, "files": files}


def target_sources() -> dict[str, str]:
    return {name: hashlib.sha256(inspect.getsource(obj).encode("utf-8")).hexdigest() for name, obj in TARGETS}


def _manifest(ns: str, provenance: dict[str, Any]) -> dict[str, Any]:
    for path, blob in EXPECTED_SOURCE_BLOBS.items():
        if provenance["files"].get(path, {}).get("blob") != blob:
            raise StopRun("SOURCE_BLOB_MISMATCH")
    return {"study": STUDY_ID, "preregistration": {"path": PREREG_PATH, "sha256": PREREG_SHA256,
                                                   "version": PREREG_VERSION},
            "decision_version": DECISION_VERSION, "code": provenance, "targets_getsource_sha256": target_sources(),
            "environment": {"sys_version": sys.version, "implementation": platform.python_implementation(),
                            "sys_platform": sys.platform, "dependencies": "python standard library and moneylab only"},
            "rng": {"serialization": SERIALIZATION, "namespace": ns, "namespaces": list(NAMESPACES), "base": BASE,
                    "path": RNG_PATH}}


# --- output ---------------------------------------------------------------------------------------------------------

def canonical(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def _sums(out: Path, names: Sequence[str]) -> bytes:
    return "".join(f"{hashlib.sha256((out / n).read_bytes()).hexdigest()}  {n}\n" for n in names).encode("ascii")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fresh_dir(out_dir: Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    return out


def _check_scope(ns: str, cells: Sequence[tuple[int, str]], reps: int, b: int, allowed: Sequence[str],
                 defaults: tuple[Sequence[tuple[int, str]], int, int]) -> None:
    if ns not in allowed:
        raise ValueError("namespace not allowed here")
    if ns != NS_TEST and (tuple(cells), reps, b) != (tuple(defaults[0]), defaults[1], defaults[2]):
        raise ValueError("non-preregistered R, B or cells are accepted only in the TEST namespace")


def run(out_dir: Path, *, workers: int = 1, namespace: str = NS_MAIN, cells: Sequence[tuple[int, str]] = CELLS,
        reps: int = R, b: int = B, provenance: dict[str, Any] | None = None, source_root: Path | None = None,
        loaded_sources: dict[str, Path] | None = None) -> dict[str, str]:
    """§9 main run. Sources are verified first; then manifest, design, cells, summary, execution.json, SHA256SUMS."""
    _check_scope(namespace, cells, reps, b, (NS_MAIN, NS_TEST), (CELLS, R, B))
    if namespace != NS_TEST and (provenance, source_root, loaded_sources) != (None, None, None):
        raise ValueError("provenance and source overrides are accepted only in the TEST namespace")
    out = _fresh_dir(out_dir)
    started, t0 = _now(), time.perf_counter()
    status, code = "STOP", "INTERNAL_ERROR"
    try:
        verified = provenance if provenance is not None else git_provenance(source_root, loaded_sources)
        manifest = _manifest(namespace, verified)
        seeds = seed_uniqueness(namespace, cells, reps)
        results = _execute(_tasks(namespace, cells, reps, b), workers)
        per_cell: dict[tuple[int, str], list[int]] = {c: [0, 0] for c in cells}
        for task, (k, d, _cpu, _mem, _walls) in zip(_tasks(namespace, cells, reps, b), results):
            per_cell[(task[1], task[2])][0] += k
            per_cell[(task[1], task[2])][1] += d
        counts = [(per_cell[c][0], per_cell[c][1]) for c in cells]
        decision_design, cell_rows, summary = evaluate(counts, reps, cells)
        design = {"cells": [[n, th] for n, th in cells], "R": reps, "rep_range": [0, reps - 1], "B": b,
                  "mean_block": MEAN_BLOCK, "alpha": str(ALPHA), "epsilon": str(EPSILON), "lambda": str(LAMBDA),
                  "seed_check": seeds, **decision_design}
        for name, obj in zip(RESULT_FILES, (manifest, design, {"cells": cell_rows}, summary)):
            atomic.atomic_write_bytes(out / name, canonical(obj))
        status, code = "COMPLETE", "NONE"
        return summary
    except StopRun as exc:
        code = exc.code
        raise
    finally:
        meta = {"status": status, "code": code, "started_utc": started, "finished_utc": _now(),
                "elapsed_seconds": time.perf_counter() - t0, "workers": workers, "host": platform.node(),
                "output_dir": str(out.resolve()), "os": platform.platform(), "parallel_efficiency": None}
        atomic.atomic_write_bytes(out / EXECUTION_FILE, canonical(meta))
        if status == "COMPLETE":
            atomic.atomic_write_bytes(out / SUMS_FILE, _sums(out, RESULT_FILES))


# --- §10 smoke and performance (no results recorded) ----------------------------------------------------------------

def smoke(out_dir: Path, *, cells: Sequence[tuple[int, str]] = CELLS, reps: int = SMOKE_REPS, b: int = B) -> None:
    """Structure check in the TEST namespace. Records completion counts and structure only."""
    out = _fresh_dir(out_dir)
    rows = []
    for n, th in cells:
        done, ok = 0, True
        for rep in range(reps):
            r = generate_p0(n, th, seed(NS_TEST, n, th, rep, "data"))
            kind, ind = v0_replicate(r, th, seed(NS_TEST, n, th, rep, "boot"), b)
            ok = ok and len(r) == n and kind in (NORMAL, DEGENERATE) and (ind in (0, 1) if kind == NORMAL else
                                                                           ind is None)
            done += 1
        rows.append({"n": n, "theta": th, "completed": done, "structure_ok": ok})
    doc = {"schema": SMOKE_SCHEMA, "study": STUDY_ID, "namespace": NS_TEST, "cells": rows,
           "all_structure_ok": all(row["structure_ok"] for row in rows)}
    atomic.atomic_write_bytes(out / "smoke.json", canonical(doc))
    atomic.atomic_write_bytes(out / SUMS_FILE, _sums(out, ["smoke.json"]))


def perf(out_dir: Path, workers: int | None, *, namespace: str = NS_PERF, reps: int = PERF_REPS, b: int = B) -> None:
    """M1 (worker 1) and M2 (worker W) on the same 80 seeds; time and resources only (§10)."""
    cells = tuple((n, PERF_THETA) for n in N_VALUES)
    _check_scope(namespace, cells, reps, b, (NS_PERF, NS_TEST), (cells, PERF_REPS, B))
    cpu = os.cpu_count()
    if workers is None or cpu is None or cpu < 3 or not 2 <= workers <= cpu - 1:
        raise StopRun("PERF_WORKERS_INVALID")
    out = _fresh_dir(out_dir)
    tasks = _tasks(namespace, cells, reps, b)
    measures: list[dict[str, Any]] = []
    walls: list[float] = []
    per_rep: dict[str, list[float]] = {}
    for label, w in (("M1", 1), ("M2", workers)):
        t0 = time.perf_counter()
        results = _execute(tasks, w)
        wall = time.perf_counter() - t0
        walls.append(wall)
        cpu_sum = sum(r[2] for r in results)
        mems = [r[3] for r in results if r[3] is not None]
        own = _peak_memory_bytes()
        if own is not None:
            mems.append(own)
        measures.append({"label": label, "workers": w, "wall_seconds": wall, "cpu_seconds_sum": cpu_sum,
                         "max_memory_bytes": max(mems) if mems else None})
        if label == "M1":
            for task, r in zip(tasks, results):
                per_rep.setdefault(str(task[1]), []).extend(r[4])
    t1, t2 = walls[0], walls[1]
    doc = {"schema": PERF_SCHEMA, "study": STUDY_ID, "namespace": namespace, "measures": measures,
           "per_rep_wall_seconds_mean_by_n": {k: sum(v) / len(v) for k, v in per_rep.items()},
           "W": workers, "parallel_efficiency": t1 / (workers * t2) if t2 > 0 else None}
    atomic.atomic_write_bytes(out / "perf.json", canonical(doc))


# --- CLI (operational sub-commands run only under their own approvals) ----------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m moneylab.research.v06.futval_v8_01")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed-check")
    for name in ("smoke", "perf", "run"):
        p = sub.add_parser(name)
        p.add_argument("--out", required=True)
        if name != "smoke":
            p.add_argument("--workers", type=int, required=name == "perf", default=1)
    args = parser.parse_args(argv)
    try:
        if args.command == "seed-check":
            print(json.dumps(seed_uniqueness(NS_MAIN, CELLS, R), sort_keys=True))
        elif args.command == "smoke":
            smoke(Path(args.out))
        elif args.command == "perf":
            perf(Path(args.out), args.workers)
        else:
            run(Path(args.out), workers=args.workers)
    except StopRun as exc:
        print(json.dumps({"status": "STOP", "code": exc.code}, sort_keys=True))
        return 2
    print(json.dumps({"status": "COMPLETE", "command": args.command}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
