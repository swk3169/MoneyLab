"""Regenerate the SYNTHETIC CLOB fixtures (deterministic, seeded).

    .venv\\Scripts\\python.exe tests\\fixtures\\generate_clob_fixtures.py

Payload shapes follow the official CLOB OpenAPI spec (docs.polymarket.com, 2026-10-04):
GET /book, GET /clob-markets/{condition_id}, GET /rewards/markets/{condition_id}.
No value here was captured from the live API (HTTP 451 from the dev environment).
Prices, sizes, ids and paths are invented. Replace with recorded data when available.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

HERE = Path(__file__).parent
CONDITION = "0xSYNTHETIC-CONDITION-0001"  # not a real 32-byte id (avoids key-like 64-hex strings)
YES = "1" * 20 + "0001"  # fake token ids
NO = "1" * 20 + "0002"
T0 = 1_791_072_000  # 2026-10-04T00:00:00Z
TICK = 0.01

MARKET_INFO = {
    "gst": None,
    "r": {"note": "synthetic"},
    "t": [{"t": YES, "o": "Yes"}, {"t": NO, "o": "No"}],
    "mos": 5,
    "mts": 0.01,
    "mbf": 0,
    "tbf": 0,
    "rfqe": False,
    "fd": {"r": 0.04, "e": 1, "to": True},  # Politics category rate
}

REWARDS = {
    "limit": 100,
    "count": 1,
    "next_cursor": "LTE=",
    "data": [{
        "condition_id": CONDITION,
        "question": "Synthetic: will the test event happen?",
        "market_slug": "synthetic-test-event",
        "event_slug": "synthetic-test-event",
        "image": "",
        "rewards_max_spread": 3,
        "rewards_min_size": 50,
        "market_competitiveness": 0.5,
        "tokens": [{"token_id": YES, "outcome": "YES", "price": 0.5}, {"token_id": NO, "outcome": "NO", "price": 0.5}],
        "rewards_config": [{
            "id": 1, "asset_address": "0xSYNTHETIC-ASSET", "start_date": "2026-10-01", "end_date": "2026-10-31",
            "rate_per_day": 20, "total_rewards": 620, "total_days": 31,
        }],
    }],
}


def r2(x: float) -> float:
    return round(round(x / TICK) * TICK, 2)


def fmt(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))


def book(token: str, bids: list[tuple[float, float]], asks: list[tuple[float, float]], ts: int, ltp: float) -> dict:
    return {
        "market": CONDITION,
        "asset_id": token,
        "timestamp": str(ts * 1000),  # ms - unit is undocumented; parser accepts s or ms
        "hash": f"synthetic-{token[-4:]}-{ts}",
        # Bids deliberately ascending (as in the WS docs example): the parser must sort.
        "bids": [{"price": fmt(p), "size": fmt(s)} for p, s in sorted(bids)],
        "asks": [{"price": fmt(p), "size": fmt(s)} for p, s in sorted(asks)],
        "min_order_size": "5",
        "tick_size": "0.01",
        "neg_risk": False,
        "last_trade_price": fmt(ltp),
    }


def ladder(rng: random.Random, best_bid: float, best_ask: float, levels: int = 5):
    bids = [(r2(best_bid - i * TICK), float(rng.randrange(60, 400, 10))) for i in range(levels) if best_bid - i * TICK > 0]
    asks = [(r2(best_ask + i * TICK), float(rng.randrange(60, 400, 10))) for i in range(levels) if best_ask + i * TICK < 1]
    return bids, asks


def mirror(bids, asks):
    """NO book implied by complementary matching: NO bid = 1 - YES ask, NO ask = 1 - YES bid."""
    return [(r2(1 - p), s) for p, s in asks], [(r2(1 - p), s) for p, s in bids]


def timeline_mm() -> dict:
    rng = random.Random(20261004)
    snaps, mid = [], 0.50
    for i in range(120):
        ts = T0 + 9 * 3600 + i * 60
        if i < 80:  # mean-reverting phase
            mid += 0.35 * (0.50 - mid) + rng.choice([-0.02, -0.01, 0.0, 0.0, 0.01, 0.02, -0.03, 0.03])
        else:  # trending phase: inventory risk
            mid += rng.choice([0.0, 0.01, 0.01, 0.02, -0.01])
        mid = min(max(mid, 0.2), 0.8)
        half = rng.choice([1, 1, 2, 2, 3])  # spread of 2-6 ticks
        bb, ba = r2(mid - half * TICK), r2(mid + half * TICK)
        bids, asks = ladder(rng, bb, ba)
        nb, na = mirror(bids, asks)
        snaps.append({"ts": ts, "books": [book(YES, bids, asks, ts, r2(mid)), book(NO, nb, na, ts, r2(1 - mid))]})
    return {
        "meta": {
            "synthetic": True,
            "rebate_rate": 0.25,
            "description": "SYNTHETIC 2h market-making replay: 80 min mean-reverting YES mid around 0.50, "
                           "then 40 min upward drift. NO book mirrors YES. 60s snapshots. No resolution.",
        },
        "condition_id": CONDITION,
        "market_info": MARKET_INFO,
        "rewards": REWARDS,
        "snapshots": snaps,
        "resolution": None,
    }


def timeline_mispricing() -> dict:
    rng = random.Random(4265)
    snaps, mid = [], 0.45
    dislocations = {12, 13, 30, 47}
    for i in range(60):
        ts = T0 + 14 * 3600 + i * 60
        mid = min(max(mid + rng.choice([-0.01, 0.0, 0.0, 0.01]), 0.38), 0.52)
        bb, ba = r2(mid - TICK), r2(mid + TICK)
        bids, asks = ladder(rng, bb, ba)
        nb, na = mirror(bids, asks)
        if i in dislocations:
            # NO book shifted 6 ticks under its mirror (bids 7 ticks, so it stays uncrossed):
            # ask_yes + ask_no < 1 (synthetic stress case).
            na = [(r2(p - 0.06), s) for p, s in na]
            nb = [(r2(p - 0.07), s) for p, s in nb]
        # External model probability (synthetic): mostly near the market, sometimes well above.
        fair = r2(mid + rng.choice([0.0, 0.01, -0.01, 0.06, 0.08]))
        snaps.append({
            "ts": ts,
            "books": [book(YES, bids, asks, ts, r2(mid)), book(NO, nb, na, ts, r2(1 - mid))],
            "signals": {"fair_yes": fair},
        })
    return {
        "meta": {
            "synthetic": True,
            "rebate_rate": 0.25,
            "description": "SYNTHETIC 1h mispricing replay: YES mid 0.38-0.52, four snapshots with a NO ask "
                           "6 ticks below its mirror (complement gap), and a synthetic external fair_yes "
                           "signal. Resolves YES. Outcome is arbitrary; it is not evidence of edge.",
        },
        "condition_id": CONDITION,
        "market_info": MARKET_INFO,
        "rewards": REWARDS,
        "snapshots": snaps,
        "resolution": {YES: 1.0, NO: 0.0},
    }


def main() -> None:
    rng = random.Random(1)
    bids, asks = ladder(rng, 0.45, 0.47)
    nb, na = mirror(bids, asks)
    sample_books = [book(YES, bids, asks, T0, 0.46), book(NO, nb, na, T0, 0.54)]
    out = {
        "clob_books_sample.json": sample_books,
        "clob_market_info_sample.json": MARKET_INFO,
        "clob_rewards_market_sample.json": REWARDS,
        "clob_timeline_mm.json": timeline_mm(),
        "clob_timeline_mispricing.json": timeline_mispricing(),
    }
    for name, payload in out.items():
        indent = None if name.startswith("clob_timeline") else 1
        (HERE / name).write_text(json.dumps(payload, indent=indent) + "\n", encoding="utf-8")
        print("wrote", name)


if __name__ == "__main__":
    main()
