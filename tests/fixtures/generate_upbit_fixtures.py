"""Generate the SYNTHETIC Upbit WebSocket session fixture (seeded, deterministic).

    python tests/fixtures/generate_upbit_fixtures.py

Message shapes follow the official docs (websocket-orderbook / websocket-trade, DEFAULT format).
All prices, sizes, ids and timestamps are invented. This is NOT a capture of real Upbit data.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).parent / "upbit_ws_timeline_synthetic.json"
MARKET = "KRW-BTC"
START = 1790000000.0  # 2026-09-21T13:33:20Z, invented
TICK = 1000.0
UNITS = 30


def book(mid: float, ts_ms: int, stream_type: str, rng: random.Random) -> dict:
    best_bid = round(mid / TICK) * TICK - TICK
    units = [{"ask_price": best_bid + TICK * (i + 1), "bid_price": best_bid - TICK * i,
              "ask_size": round(rng.uniform(0.001, 0.5), 8), "bid_size": round(rng.uniform(0.001, 0.5), 8)}
             for i in range(UNITS)]
    return {"type": "orderbook", "code": MARKET, "timestamp": ts_ms,
            "total_ask_size": round(sum(u["ask_size"] for u in units), 8),
            "total_bid_size": round(sum(u["bid_size"] for u in units), 8),
            "orderbook_units": units, "stream_type": stream_type, "level": 0}


def trade(price: float, volume: float, side: str, sid: int, ts_ms: int, stream_type: str) -> dict:
    return {"type": "trade", "code": MARKET, "timestamp": ts_ms + 40, "trade_date": "2026-09-21",
            "trade_time": "13:33:20", "trade_timestamp": ts_ms, "trade_price": price, "trade_volume": volume,
            "ask_bid": side, "prev_closing_price": 99_000_000.0, "change": "RISE", "change_price": 1_000_000.0,
            "sequential_id": sid, "best_ask_price": price + TICK, "best_ask_size": 0.1,
            "best_bid_price": price - TICK, "best_bid_size": 0.1, "stream_type": stream_type}


def main() -> None:
    rng = random.Random(20261006)
    frames1, frames2 = [], []
    t = START + 2.5  # after the scripted 429 + backoff
    mid = 100_000_000.0
    sid = 17_900_000_025_000_000  # > 2**53 like real ids: must survive JSON round trips exactly
    last_book = None
    for i in range(24):
        t += 0.25
        mid += rng.choice((-TICK, 0.0, TICK))
        ts_ms = int(t * 1000) - 30
        b = book(mid, ts_ms, "SNAPSHOT" if i == 0 else "REALTIME", rng)
        if i == 6:  # identical content, new timestamp: a normal unchanged book that must be kept
            b = {**last_book, "timestamp": ts_ms, "stream_type": "REALTIME"}
        frames1.append({"t": round(t, 3), "raw": b})
        last_book = b
        if i % 3 == 1:
            sid += 1000
            # trade executed slightly before the book that preceded it: exchange timestamps of
            # the two streams interleave
            frames1.append({"t": round(t + 0.05, 3),
                            "raw": trade(b["orderbook_units"][0]["ask_price"], round(rng.uniform(0.0001, 0.05), 8),
                                         rng.choice(("ASK", "BID")), sid, ts_ms - 80,
                                         "SNAPSHOT" if i == 1 else "REALTIME")})
        if i == 10:
            frames1.append({"t": round(t + 0.1, 3), "raw_text": "{not json"})
    last_trade = next(f["raw"] for f in reversed(frames1) if "raw" in f and f["raw"]["type"] == "trade")
    t += 3.0  # reconnect after the close below (backoff)
    # reconnect: server re-sends snapshots -> duplicate trade (same sequential_id) and duplicate book
    frames2.append({"t": round(t, 3), "raw": {**last_book, "stream_type": "SNAPSHOT"}})
    frames2.append({"t": round(t + 0.01, 3), "raw": {**last_trade, "stream_type": "SNAPSHOT"}})
    for i in range(8):
        t += 0.25
        mid += rng.choice((-TICK, 0.0, TICK))
        ts_ms = int(t * 1000) - 30
        frames2.append({"t": round(t, 3), "raw": book(mid, ts_ms, "REALTIME", rng)})
        if i % 2 == 0:
            sid += 1000
            frames2.append({"t": round(t + 0.05, 3),
                            "raw": trade(mid, round(rng.uniform(0.0001, 0.05), 8), rng.choice(("ASK", "BID")),
                                         sid, ts_ms + 10, "REALTIME")})
    data = {
        "meta": {"synthetic": True, "generator": "tests/fixtures/generate_upbit_fixtures.py",
                 "description": "SYNTHETIC Upbit KRW-BTC WebSocket session: 429 handshake, session with a "
                                "malformed frame and a 1006 close, reconnect with duplicate snapshots."},
        "start": START,
        "connections": [
            {"handshake": {"status": 429, "reason": "Too Many Requests", "headers": {"Retry-After": "2"},
                           "body": "{\"error\":{\"name\":\"too_many_requests\",\"message\":\"synthetic\"}}"}},
            {"ping_reply": True, "frames": frames1, "close": {"code": 1006, "reason": "synthetic abnormal close"}},
            {"ping_reply": True, "frames": frames2},
        ],
    }
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
