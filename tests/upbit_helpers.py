"""Shared helpers for the Upbit tests: SYNTHETIC message builders and scripted sessions."""

import random
from pathlib import Path

from moneylab.providers.upbit.endpoints import WS_PUBLIC_URL
from moneylab.providers.upbit.recorder import ScriptedWsSource, UpbitRecorder, UpbitRecorderConfig
from moneylab.providers.upbit.recorder.store import read_segment, segment_paths

FIXTURE = Path(__file__).parent / "fixtures" / "upbit_ws_timeline_synthetic.json"
T0 = 1_800_000_000.0


def book(ts_ms: int, bid: float = 100.0, ask: float = 101.0, size: float = 1.0, code: str = "KRW-BTC",
         stream_type: str = "REALTIME") -> dict:
    return {"type": "orderbook", "code": code, "timestamp": ts_ms, "total_ask_size": size, "total_bid_size": size,
            "orderbook_units": [{"ask_price": ask, "bid_price": bid, "ask_size": size, "bid_size": size}],
            "stream_type": stream_type, "level": 0}


def trade(sid: int, ts_ms: int, price: float = 100.5, volume: float = 0.1, side: str = "BID",
          code: str = "KRW-BTC", stream_type: str = "REALTIME") -> dict:
    return {"type": "trade", "code": code, "timestamp": ts_ms + 5, "trade_timestamp": ts_ms, "trade_price": price,
            "trade_volume": volume, "ask_bid": side, "sequential_id": sid, "stream_type": stream_type}


def frames(*items, start: float = T0, step: float = 0.1) -> list[dict]:
    out, t = [], start
    for it in items:
        t += step
        out.append({"t": round(t, 6), **({"raw": it} if isinstance(it, dict) and "type" in it else it)})
    return out


def scripted(connections: list[dict], start: float = T0) -> ScriptedWsSource:
    return ScriptedWsSource(data={"meta": {"synthetic": True}, "start": start, "connections": connections})


def make_recorder(src: ScriptedWsSource, out: Path, provenance: str = "fixture", origin: str = "fixture:test",
                  **cfg) -> UpbitRecorder:
    cfg.setdefault("orderbook_units", 1)
    return UpbitRecorder(src, WS_PUBLIC_URL, out, UpbitRecorderConfig(**cfg), provenance=provenance, origin=origin,
                         clock=src.clock, sleep=src.sleep, rng=random.Random(7), ticket_factory=lambda: "ticket")


def lines(out: Path, market: str = "KRW-BTC") -> list[dict]:
    return [ln for p in segment_paths(out / market) for ln in read_segment(p)]


def sleeps_of(src: ScriptedWsSource):
    """Wrap src.sleep to record waits."""
    waits: list[float] = []
    orig = src.sleep

    def sleep(s):
        waits.append(s)
        orig(s)
    return waits, sleep
