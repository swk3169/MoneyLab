"""SYNTHETIC price paths for the v0.6 Monte Carlo. Not market data, never evidence.

Daily log return of day d = a[d] + b[d] + c[d]: the [00:00, 01:00), [01:00, 02:00) and
[02:00, 24:00) UTC parts, with variance shares 1/24, 1/24, 22/24. The noise is GARCH(1,1) with
standardized Student-t (or normal) innovations and an optional AR(1) term; the drift is a baseline
plus an optional "edge" that depends on the sign of past returns (momentum or reversal), which is
how a strategy gets a known positive or negative true Sharpe.

Execution scenarios (draft 6.2/6.3), for a signal s[d] taken from the close of day d:
  E0  day e runs (e 01:00, e+1 01:00]: market b[e] + c[e] + a[e+1], position s[e-1]
  E1  day e runs (e 02:00, e+1 02:00]: market c[e] + a[e+1] + b[e+1], position s[e-1]
  E2  day e runs (e 00:00, e+1 00:00]: market a[e] + b[e] + c[e],     position s[e-2]
A segment [g0, g1) (calendar days) owns the scenario days whose end time is in (g0 00:00, g1 00:00]
(draft 8.1), so it never reads a component of a day >= g1.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field

from moneylab.research.v06.procedures import STRATEGIES, annual_sharpe, b1_means, segment_returns, signals

SHARES = (1 / 24, 1 / 24, 22 / 24)
SCENARIOS = ("E0", "E1", "E2")


@dataclass(frozen=True)
class DGP:
    annual_vol: float = 0.70           # assumption: "BTC-like" magnitude, not estimated from data
    garch_alpha: float = 0.08
    garch_beta: float = 0.90           # alpha = beta = 0 gives constant variance
    t_df: float | None = 4.0           # None = normal innovations
    ar1: float = 0.0
    drift_annual: float = 0.0          # baseline log drift per year
    edge_kind: str = "none"            # "momentum" | "reversal" | "none"
    edge_lookback: int = 60
    edge_annual: float = 0.0           # +/- this log drift per year by the sign of the past return


@dataclass
class Noise:
    """Mean-free part of a path, fixed by the seed (so the drift can be recalibrated on the same
    noise: common random numbers)."""
    a: list[float]
    b: list[float]
    c: list[float]


def _innovation(rng: random.Random, t_df: float | None) -> float:
    z = rng.gauss(0.0, 1.0)
    if t_df is None:
        return z
    chi2 = rng.gammavariate(t_df / 2.0, 2.0)
    return z / math.sqrt(chi2 / t_df) * math.sqrt((t_df - 2.0) / t_df)


def draw_noise(dgp: DGP, days: int, seed: int) -> Noise:
    if dgp.t_df is not None and dgp.t_df <= 2:
        raise ValueError("t_df must be > 2 (finite variance)")
    if dgp.garch_alpha + dgp.garch_beta >= 1:
        raise ValueError("GARCH must be stationary (alpha + beta < 1)")
    rng = random.Random(seed)
    h_bar = dgp.annual_vol ** 2 / 365.0
    omega = h_bar * (1.0 - dgp.garch_alpha - dgp.garch_beta)
    h, e_prev, u_prev = h_bar, 0.0, 0.0
    a, b, c = [], [], []
    for _ in range(days):
        h = omega + dgp.garch_alpha * e_prev ** 2 + dgp.garch_beta * h
        parts = [math.sqrt(h * s) * _innovation(rng, dgp.t_df) for s in SHARES]
        e = sum(parts)
        ar = dgp.ar1 * u_prev
        a.append(parts[0])
        b.append(parts[1])
        c.append(parts[2] + ar)
        u_prev = ar + e
        e_prev = e
    return Noise(a, b, c)


def add_drift(dgp: DGP, noise: Noise) -> tuple[list[float], list[float], list[float]]:
    """Components with the baseline drift and the path-dependent edge (sequential: the edge of
    day d depends on closes up to day d-1 only)."""
    days = len(noise.a)
    a, b, c = [0.0] * days, [0.0] * days, [0.0] * days
    closes: list[float] = []
    level = 0.0
    n = dgp.edge_lookback
    for d in range(days):
        mu = dgp.drift_annual / 365.0
        if dgp.edge_kind != "none" and d - 1 - n >= 0:
            past = closes[d - 1] - closes[d - 1 - n]
            sign = (past > 0) - (past < 0)
            if dgp.edge_kind == "reversal":
                sign = -sign
            mu += sign * dgp.edge_annual / 365.0
        a[d] = noise.a[d] + mu * SHARES[0]
        b[d] = noise.b[d] + mu * SHARES[1]
        c[d] = noise.c[d] + mu * SHARES[2]
        level += a[d] + b[d] + c[d]
        closes.append(level)
    return a, b, c


@dataclass
class Path:
    a: list[float]
    b: list[float]
    c: list[float]
    log_close: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.log_close:
            level, out = 0.0, []
            for x, y, z in zip(self.a, self.b, self.c):
                level += x + y + z
                out.append(level)
            self.log_close = out

    @property
    def days(self) -> int:
        return len(self.a)


def make_path(dgp: DGP, days: int, seed: int) -> Path:
    return Path(*add_drift(dgp, draw_noise(dgp, days, seed)))


def strategy_signals(path: Path) -> dict[str, list[int | None]]:
    return {name: signals(path.log_close, rule, n) for name, (rule, n) in STRATEGIES.items()}


def scenario_days(scenario: str, g0: int, g1: int) -> range:
    """Scenario day indices owned by segment [g0, g1) (end time in (g0 00:00, g1 00:00])."""
    if scenario in ("E0", "E1"):
        return range(g0 - 1, g1 - 1)
    if scenario == "E2":
        return range(g0, g1)
    raise ValueError(f"unknown scenario {scenario!r}")


def segment_market_positions(path: Path, sig: Sequence[int | None], scenario: str, g0: int,
                             g1: int) -> tuple[list[float], list[int]]:
    """Market log returns and positions of one scenario over segment [g0, g1). A missing signal
    (not enough history) counts as cash."""
    a, b, c = path.a, path.b, path.c
    market, pos = [], []
    for e in scenario_days(scenario, g0, g1):
        if scenario == "E0":
            market.append(b[e] + c[e] + a[e + 1])
            s = sig[e - 1]
        elif scenario == "E1":
            market.append(c[e] + a[e + 1] + b[e + 1])
            s = sig[e - 1]
        else:
            market.append(a[e] + b[e] + c[e])
            s = sig[e - 2]
        pos.append(int(s or 0))
    return market, pos


def min_warmup() -> int:
    """First segment day g0 must leave a defined signal for the first scenario day: E0/E1 use
    s[g0 - 2], E2 uses s[g0 - 2] as well, so g0 >= longest lookback + 2."""
    return max(n for _, n in STRATEGIES.values()) + 2


# --- truth on a long path ---------------------------------------------------------------------

def true_metrics(path: Path, costs: dict[str, float], b1_draws: int = 20,
                 seed: int = 0) -> dict[str, dict[str, float]]:
    """Per strategy: annual Sharpe of E0/E1/E2 net returns and E0 excess over B1 (daily mean),
    on one long path treated as a single segment. Used as the 'truth' of a scenario."""
    sigs = strategy_signals(path)
    g0, g1 = min_warmup() + 1, path.days - 1
    out: dict[str, dict[str, float]] = {}
    for i, (name, sig) in enumerate(sigs.items()):
        row: dict[str, float] = {}
        for scn in SCENARIOS:
            market, pos = segment_market_positions(path, sig, scn, g0, g1)
            r = segment_returns(market, pos, costs[scn])
            row[f"sr_{scn}"] = annual_sharpe(r)
            if scn == "E0":
                draws = b1_means(market, pos, costs[scn], b1_draws, seed + i)
                row["excess_E0"] = sum(r) / len(r) - sum(draws) / len(draws)
                row["exposure"] = sum(pos) / len(pos)
        out[name] = row
    return out
