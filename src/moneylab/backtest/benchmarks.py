"""Benchmarks B1-B4 and the seed rule for B1 (BT-2b-3; draft section 8; docs/backtest_bt2b3_metrics.md).

All benchmarks use the run's own reference times, market log returns m_i = ln(P_{i+1} / P_i) of the
valuation prices, and the run's cost per trade as log multipliers (backtest.costs.CostModel.buy / sell):
  buy  inclusive  c_b = ln((1 - f_b)(1 - kappa - iota))      on_top  c_b = ln((1 - kappa - iota) / (1 + f_b))
  sell            c_s = ln((1 - kappa - iota)(1 - f_s))
A position series p_0..p_{n-1} earns r_i = p_i m_i, plus c_b on a day the position opens, c_s on a day it
closes and c_s on the last day if it is still open (virtual exit, draft 8.1): the convention of the ledger
returns and of research/v06/procedures.segment_returns.

  B1  matched random exposure: holding spells and inner cash gaps shuffled independently, leading +
      trailing cash split at random; K placements. The random draws are consumed in the order of
      research/v06/procedures.b1_positions (shuffle spells, shuffle gaps, randint), which is not imported.
  B2  buy-and-hold: long every day, one entry and one exit cost.
  B3  cash: r_i = 0.
  B4  B2 scaled by the strategy's mean exposure w, no rebalancing (REPORT_ONLY):
      W2(k) = exp(sum_{i<k} r2_i), W4(k) = (1 - w) + w * W2(k), r4_k = ln(W4(k+1) / W4(k)).
      Cash earns 0; costs fall on the B2 part only.

Seed rule bt-seed/1: SHA-256 of the UTF-8 bytes of
  json.dumps(["moneylab.bt_seed", 1, str(seed), *labels], ensure_ascii=False, separators=(",", ":"))
first 8 bytes as a big-endian unsigned integer, passed to random.Random. 0 <= seed < 2**64. Unlike
research/stats.derived_seed (crc32 of "|".join) the encoding cannot merge different label lists.

Benchmark comparisons need the ledger returns to be exactly the position-series returns above
(alignment). If they are not (a fill booked after its reference time, a missing day, a price
mismatch), no comparison is produced: the result says not_aligned with the reasons. No p-values.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from moneylab.backtest.costs import BP, CostModel
from moneylab.backtest.ledger import Ledger
from moneylab.backtest.performance import ANNUALIZATION_DAYS, mean, series_metrics, value

BT_SEED_ALGORITHM = "bt-seed/1"
SEED_LIMIT = 2**64
B1_QUANTILES = (0.05, 0.50, 0.95)
ALIGNMENT_TOLERANCE = 1e-9  # absolute, on daily log returns (the ledger is Decimal, the benchmarks float)


class BenchmarkError(ValueError):
    """Benchmark inputs are not usable (seed out of range, lengths differ, bad weight)."""


# --- seed -----------------------------------------------------------------------------------------------

def bt_seed_payload(seed: int, *labels: str) -> bytes:
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < SEED_LIMIT:
        raise BenchmarkError(f"seed must be an integer with 0 <= seed < 2**64, got {seed!r}")
    if not all(isinstance(x, str) for x in labels):
        raise BenchmarkError("seed labels must be strings")
    return json.dumps(["moneylab.bt_seed", 1, str(seed), *labels], ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def bt_seed(seed: int, *labels: str) -> int:
    return int.from_bytes(hashlib.sha256(bt_seed_payload(seed, *labels)).digest()[:8], "big")


# --- position series ------------------------------------------------------------------------------------

def runs(positions: Sequence[int]) -> tuple[int, list[int], list[int], int]:
    """(leading cash days, holding spell lengths, inner cash gap lengths, trailing cash days)."""
    spells: list[int] = []
    gaps: list[int] = []
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


def b1_positions(positions: Sequence[int], rng: random.Random) -> list[int]:
    """One B1 placement: same exposure days, spell lengths and number of trades."""
    lead, spells, gaps, trail = runs(positions)
    if not spells:
        return [0] * len(positions)
    sp, gp = spells[:], gaps[:]
    rng.shuffle(sp)
    rng.shuffle(gp)
    out = [0] * rng.randint(0, lead + trail)
    for i, s in enumerate(sp):
        out.extend([1] * s)
        if i < len(gp):
            out.extend([0] * gp[i])
    out.extend([0] * (len(positions) - len(out)))
    return out


def leg_cost_logs(costs: CostModel) -> tuple[float, float]:
    """(c_b, c_s): log wealth multiplier of one buy and one sell under the run's cost model."""
    k = float((costs.slippage_bps + costs.impact_bps) / BP)
    fb, fs = float(costs.buy_fee_bps / BP), float(costs.sell_fee_bps / BP)
    c_b = math.log1p(-fb) + math.log1p(-k) if costs.fee_basis == "inclusive" else math.log1p(-k) - math.log1p(fb)
    return c_b, math.log1p(-k) + math.log1p(-fs)


def position_returns(market: Sequence[float], positions: Sequence[int], c_buy: float, c_sell: float) -> list[float]:
    if len(market) != len(positions):
        raise BenchmarkError("market and positions differ in length")
    out, prev = [], 0
    for m, p in zip(market, positions):
        v = p * m
        if p == 1 and prev == 0:
            v += c_buy
        elif p == 0 and prev == 1:
            v += c_sell
        out.append(v)
        prev = p
    if out and prev == 1:
        out[-1] += c_sell
    return out


def b2_returns(market: Sequence[float], c_buy: float, c_sell: float) -> list[float]:
    return position_returns(market, [1] * len(market), c_buy, c_sell)


def b3_returns(n: int) -> list[float]:
    return [0.0] * n


def b4_returns(market: Sequence[float], w: float, c_buy: float, c_sell: float) -> list[float]:
    if not 0.0 <= w <= 1.0:
        raise BenchmarkError(f"B4 weight must be within [0, 1], got {w!r}")
    wealth = [1.0]
    level = 0.0
    for r in b2_returns(market, c_buy, c_sell):
        level += r
        wealth.append((1.0 - w) + w * math.exp(level))
    return [math.log(wealth[k + 1] / wealth[k]) for k in range(len(market))]


def quantile(xs: Sequence[float], q: float) -> float:
    """Linear interpolation between order statistics: h = (n - 1) q, x_(lo) + (h - lo)(x_(lo+1) - x_(lo))."""
    if not xs:
        raise BenchmarkError("quantile of an empty list")
    if not 0.0 <= q <= 1.0:
        raise BenchmarkError("q must be within [0, 1]")
    s = sorted(xs)
    h = (len(s) - 1) * q
    lo = math.floor(h)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (h - lo) * (s[hi] - s[lo])


# --- ledger alignment -----------------------------------------------------------------------------------

def market_log_returns(ledger: Ledger) -> list[float]:
    d = ledger.daily
    return [math.log(float(d[i + 1].price / d[i].price)) for i in range(len(d) - 1)]


def ledger_positions(ledger: Ledger) -> list[int]:
    return [row.position for row in ledger.daily[:-1]]


def alignment(ledger: Ledger, returns: Sequence[float], costs: CostModel) -> dict[str, Any]:
    """Whether the ledger returns equal the position-series returns, with every reason they do not."""
    reasons: list[str] = []
    d = ledger.daily
    if len(d) < 2:
        return {"aligned": False, "reasons": ["fewer than 2 daily valuations"], "max_identity_error": None}
    for a, b in zip(d, d[1:]):
        if b.ref_time - a.ref_time != timedelta(days=1):
            reasons.append(f"daily valuations {a.ref_time.isoformat()} -> {b.ref_time.isoformat()} are not one day apart")
    rows = {row.ref_time: row for row in d}
    for t in ledger.trades:
        row = rows.get(t.fill_time)
        if row is None:
            reasons.append(f"leg {t.leg} ({t.fill_kind}) filled at {t.fill_time.isoformat()}, not at a valuation time")
        elif t.ref_price != row.price:
            reasons.append(f"leg {t.leg} fill price {t.ref_price} differs from the valuation price {row.price}")
    max_err = None
    if not reasons:
        c_b, c_s = leg_cost_logs(costs)
        expected = position_returns(market_log_returns(ledger), ledger_positions(ledger), c_b, c_s)
        if len(expected) != len(returns):
            reasons.append(f"{len(returns)} ledger returns but {len(expected)} position-series returns")
        else:
            errs = [abs(a - b) for a, b in zip(returns, expected)]
            max_err = max(errs) if errs else 0.0
            bad = [i for i, e in enumerate(errs) if e > ALIGNMENT_TOLERANCE]
            if bad:
                reasons.append(f"return identity r = p m + c fails on {len(bad)} day(s), first at index {bad[0]} "
                               f"(error {errs[bad[0]]!r})")
    return {"aligned": not reasons, "reasons": reasons, "max_identity_error": max_err,
            "tolerance": ALIGNMENT_TOLERANCE}


# --- comparison -----------------------------------------------------------------------------------------

def _diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    if a["value"] is None or b["value"] is None:
        return value(None, "operand_unavailable")
    return value(a["value"] - b["value"])


def compare(r_strategy: Sequence[float], market: Sequence[float], positions: Sequence[int], c_buy: float,
            c_sell: float, t_days: float, *, draws: int, seed: int, labels: Sequence[str]) -> dict[str, Any]:
    """B1-B4 next to the strategy, all with the same metric definitions (MDD on the P basis)."""
    n = len(r_strategy)
    if len(market) != n or len(positions) != n:
        raise BenchmarkError("strategy returns, market returns and positions differ in length")
    if n == 0:
        raise BenchmarkError("no returns to compare")
    if isinstance(draws, bool) or not isinstance(draws, int) or draws < 1:
        raise BenchmarkError("draws must be a positive integer")
    derived = bt_seed(seed, *labels)
    rng = random.Random(derived)
    b1_means = [mean(position_returns(market, b1_positions(positions, rng), c_buy, c_sell)) for _ in range(draws)]
    lead, spells, gaps, trail = runs(positions)
    m_s = mean(r_strategy)
    w = sum(positions) / n
    strategy = series_metrics(r_strategy, t_days)
    b2 = series_metrics(b2_returns(market, c_buy, c_sell), t_days)
    b3 = series_metrics(b3_returns(n), t_days)
    b4 = series_metrics(b4_returns(market, w, c_buy, c_sell), t_days)
    return {
        "status": "compared",
        "mdd_basis": "P (research/v06/procedures.max_drawdown) for the strategy and every benchmark",
        "strategy": strategy,
        "b1": {
            "draws": draws,
            "structure": {"lead_plus_trail_cash_days": lead + trail, "spells": sorted(spells),
                          "inner_gaps": sorted(gaps), "exposure_days": sum(spells), "trades": 2 * len(spells)},
            "mean_log_return": {"mean": value(mean(b1_means)),
                                **{f"q{round(q * 100):02d}": value(quantile(b1_means, q)) for q in B1_QUANTILES}},
            "quantile_method": "linear interpolation, h = (K - 1) q",
            "strategy_minus_mean_b1": value(m_s - mean(b1_means)),
            "p_value": "not computed",
        },
        "b2": b2 | {"trades": 2},
        "b3": b3 | {"trades": 0},
        "b4": b4 | {"weight": value(w), "label": "REPORT_ONLY", "rebalancing": "none"},
        "differences": {
            "sum_log_return_minus_b2": _diff(strategy["sum_log_return"], b2["sum_log_return"]),
            "cagr_minus_b2": _diff(strategy["cagr"], b2["cagr"]),
            "sum_log_return_minus_b3": _diff(strategy["sum_log_return"], b3["sum_log_return"]),
            "mdd_minus_b2": _diff(strategy["mdd"], b2["mdd"]),
        },
        "annualization_days": ANNUALIZATION_DAYS,
    }
