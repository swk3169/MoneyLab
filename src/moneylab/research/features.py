"""Pre-registered features (docs/research_v04_preregistration.md, section 5): pure functions + registry.

Every feature has a lookback (seconds of history it needs before t). Book features look only at
the as-of book at t (lookback 0); trade features at trades received in (t - w, t]; series
features at the 1 s grid mids in [t - w, t]. A feature is NaN when its inputs do not exist
(too few levels, no trades for a ratio, empty side) or when its lookback window crosses a
discontinuity; values are never filled.

Units: prices KRW, sizes BTC, returns/vol in bp (1e-4), ratios unitless.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from moneylab.analytics.metrics import microprice

NAN = float("nan")
Level = tuple[float, float]


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    unit: str
    lookback_seconds: float
    kind: str  # book | trade | series
    formula: str


def _specs() -> tuple[FeatureSpec, ...]:
    s = [
        FeatureSpec("mid_price", "KRW", 0, "book", "(bid1 + ask1) / 2"),
        FeatureSpec("spread", "KRW", 0, "book", "ask1 - bid1"),
        FeatureSpec("spread_bps", "bp", 0, "book", "1e4 * spread / mid"),
        FeatureSpec("microprice", "KRW", 0, "book", "(bid1*qask1 + ask1*qbid1) / (qbid1 + qask1)"),
        FeatureSpec("microprice_dev_bps", "bp", 0, "book", "1e4 * (microprice - mid) / mid"),
    ]
    for k in (1, 5, 10, 30):
        s.append(FeatureSpec(f"obi_{k}", "ratio", 0, "book", f"(sum qbid[:{k}] - sum qask[:{k}]) / (sum qbid[:{k}] + sum qask[:{k}])"))
    for k in (10, 30):
        s.append(FeatureSpec(f"bid_depth_{k}", "BTC", 0, "book", f"sum qbid[:{k}]"))
        s.append(FeatureSpec(f"ask_depth_{k}", "BTC", 0, "book", f"sum qask[:{k}]"))
    for d in (5, 10):
        s.append(FeatureSpec(f"depth_imbalance_{d}bp", "ratio", 0, "book",
                             f"(Db - Da)/(Db + Da), D = size within {d} bp of mid"))
    for w in (1, 5, 30):
        s.append(FeatureSpec(f"signed_volume_{w}s", "BTC", w, "trade", f"sum sign*vol over trades in (t-{w}s, t]"))
        s.append(FeatureSpec(f"trade_flow_imbalance_{w}s", "ratio", w, "trade",
                             f"sum sign*vol / sum vol over (t-{w}s, t]; NaN without trades"))
    s.append(FeatureSpec("buy_intensity", "trades/s", 5, "trade", "count(BID trades in (t-5s, t]) / 5"))
    s.append(FeatureSpec("sell_intensity", "trades/s", 5, "trade", "count(ASK trades in (t-5s, t]) / 5"))
    for w in (1, 5, 30, 60):
        s.append(FeatureSpec(f"return_{w}s", "bp", w, "series", f"1e4 * ln(mid_t / mid_(t-{w}s))"))
    for w in (30, 60, 300):
        s.append(FeatureSpec(f"realized_vol_{w}s", "bp", w, "series",
                             f"sqrt(sum over 1 s steps in (t-{w}s, t] of (1e4 * ln(mid_k / mid_k-1))^2)"))
    s.append(FeatureSpec("liquidity_concentration", "ratio", 0, "book",
                         "(sum qbid[:5] + sum qask[:5]) / (sum qbid[:30] + sum qask[:30])"))
    s.append(FeatureSpec("book_slope", "ln-ratio", 0, "book",
                         "ln(slope_b / slope_a), slope = sum q[:10] / (1e4 * |mid - p10| / mid)"))
    return tuple(s)


FEATURES: tuple[FeatureSpec, ...] = _specs()
REGISTRY: dict[str, FeatureSpec] = {f.name: f for f in FEATURES}
TRADE_WINDOWS = (1, 5, 30)
INTENSITY_WINDOW = 5
MAX_TRADE_LOOKBACK = max(TRADE_WINDOWS + (INTENSITY_WINDOW,))


def validate_feature_names(names: Sequence[str]) -> None:
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        raise ValueError(f"features not in the registry: {unknown}")


def registry_dict() -> list[dict]:
    return [f.__dict__.copy() for f in FEATURES]


def max_lookback(names: Sequence[str] | None = None) -> float:
    return max(REGISTRY[n].lookback_seconds for n in (names or REGISTRY))


# --- book features (lookback 0) --------------------------------------------------------------

def _sum(levels: Sequence[Level], k: int) -> float:
    return sum(q for _, q in levels[:k])


def _ratio(a: float, b: float) -> float:
    return (a - b) / (a + b) if a + b > 0 else NAN


def book_features(bids: Sequence[Level], asks: Sequence[Level]) -> dict[str, float]:
    """All book features from best-first levels. NaN where the book cannot supply the input."""
    out = {f.name: NAN for f in FEATURES if f.kind == "book"}
    if not bids or not asks:
        return out
    b1, qb1 = bids[0]
    a1, qa1 = asks[0]
    mid = (b1 + a1) / 2.0
    if mid <= 0:
        return out
    mp = microprice(b1, qb1, a1, qa1)
    out.update(mid_price=mid, spread=a1 - b1, spread_bps=1e4 * (a1 - b1) / mid, microprice=mp,
               microprice_dev_bps=1e4 * (mp - mid) / mid)
    for k in (1, 5, 10, 30):
        if len(bids) >= k and len(asks) >= k:
            out[f"obi_{k}"] = _ratio(_sum(bids, k), _sum(asks, k))
    for k in (10, 30):
        if len(bids) >= k:
            out[f"bid_depth_{k}"] = _sum(bids, k)
        if len(asks) >= k:
            out[f"ask_depth_{k}"] = _sum(asks, k)
    for d in (5, 10):
        lo, hi = mid * (1 - d / 1e4), mid * (1 + d / 1e4)
        db = sum(q for p, q in bids if p >= lo)
        da = sum(q for p, q in asks if p <= hi)
        out[f"depth_imbalance_{d}bp"] = _ratio(db, da)
    if len(bids) >= 30 and len(asks) >= 30:
        total = _sum(bids, 30) + _sum(asks, 30)
        out["liquidity_concentration"] = (_sum(bids, 5) + _sum(asks, 5)) / total if total > 0 else NAN
    if len(bids) >= 10 and len(asks) >= 10:
        db, da = 1e4 * abs(mid - bids[9][0]) / mid, 1e4 * abs(asks[9][0] - mid) / mid
        sb = _sum(bids, 10) / db if db > 0 else NAN
        sa = _sum(asks, 10) / da if da > 0 else NAN
        if sb > 0 and sa > 0:
            out["book_slope"] = math.log(sb / sa)
    return out


# --- trade features ---------------------------------------------------------------------------

def trade_features(trades: Sequence[tuple[float, int, float]], t: float) -> dict[str, float]:
    """`trades` = (received_timestamp, sign, volume) of trades received at or before t, any order.
    Window (t - w, t]: a trade received exactly at t - w is outside."""
    out: dict[str, float] = {}
    for w in TRADE_WINDOWS:
        win = [(s, v) for r, s, v in trades if t - w < r <= t]
        signed = sum(s * v for s, v in win)
        vol = sum(v for _, v in win)
        out[f"signed_volume_{w}s"] = signed
        out[f"trade_flow_imbalance_{w}s"] = signed / vol if vol > 0 else NAN
    w = INTENSITY_WINDOW
    out["buy_intensity"] = sum(1 for r, s, _ in trades if t - w < r <= t and s > 0) / w
    out["sell_intensity"] = sum(1 for r, s, _ in trades if t - w < r <= t and s < 0) / w
    return out


# --- series features (on the grid) ------------------------------------------------------------

def log_return_bps(now: float, before: float) -> float:
    if not (now > 0 and before > 0):
        return NAN
    return 1e4 * math.log(now / before)


def series_features(mids: Sequence[float], window_ok, steps_per_second: int = 1) -> dict[str, list[float]]:
    """return_w and realized_vol_w for every grid row. `window_ok(k, lookback_rows)` says whether
    rows [k - lookback_rows, k] are free of discontinuities (and inside the row's segment)."""
    n = len(mids)
    out: dict[str, list[float]] = {}
    for w in (1, 5, 30, 60):
        L = w * steps_per_second
        out[f"return_{w}s"] = [log_return_bps(mids[k], mids[k - L]) if k >= L and window_ok(k, L) else NAN
                               for k in range(n)]
    sq = [NAN] + [log_return_bps(mids[k], mids[k - 1]) ** 2 for k in range(1, n)]
    prefix, missing = [0.0], [0]
    for v in sq:
        bad = math.isnan(v)
        prefix.append(prefix[-1] + (0.0 if bad else v))
        missing.append(missing[-1] + bad)
    for w in (30, 60, 300):
        L = w * steps_per_second
        col = []
        for k in range(n):
            if k >= L and window_ok(k, L) and missing[k + 1] == missing[k - L + 1]:
                col.append(math.sqrt(prefix[k + 1] - prefix[k - L + 1]))
            else:
                col.append(NAN)
        out[f"realized_vol_{w}s"] = col
    return out
