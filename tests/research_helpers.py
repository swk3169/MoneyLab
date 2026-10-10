"""SYNTHETIC MarketEvent builders for the v0.4 research tests (prices, sizes and times are invented)."""

from __future__ import annotations

import math

from moneylab.domain.market_events import CONNECTION, DISCONNECT, TRADE, MarketEvent, TradePrint
from moneylab.research.config import load_config
from moneylab.research.sampling import GridParams

T0 = 1_800_000_000.0
TICK = 1000.0


class Seq:
    def __init__(self):
        self.n = 0

    def __call__(self) -> int:
        self.n += 1
        return self.n


def book(seq: int, recv: float, bid: float, ask: float, *, size: float = 0.5, levels: int = 30, stream: str = "REALTIME",
         conn: str = "c1", flags=(), provenance: str = "real", sizes=None) -> MarketEvent:
    sb = sizes or [size] * levels
    return MarketEvent.book_event(
        bids=[(bid - i * TICK, sb[i]) for i in range(levels)], asks=[(ask + i * TICK, sb[i]) for i in range(levels)],
        market="KRW-BTC", provenance=provenance, received_timestamp=recv, local_sequence=seq,
        exchange_timestamp_ms=int(recv * 1000) - 40, stream_type=stream, connection_id=conn, flags=frozenset(flags))


def trade(seq: int, recv: float, side: str = "buy", volume: float = 0.01, price: float = 100_000_000.0,
          stream: str = "REALTIME", conn: str = "c1", flags=(), provenance: str = "real") -> MarketEvent:
    return MarketEvent(market="KRW-BTC", event_type=TRADE, provenance=provenance, received_timestamp=recv,
                       local_sequence=seq, exchange_timestamp_ms=int(recv * 1000) - 40, stream_type=stream,
                       connection_id=conn, trade=TradePrint(price, volume, side, seq, int(recv * 1000) - 45),
                       flags=frozenset(flags))


def local(seq: int, recv: float, kind: str = CONNECTION, conn: str = "c1", provenance: str = "real") -> MarketEvent:
    return MarketEvent(market="KRW-BTC", event_type=kind, provenance=provenance, received_timestamp=recv,
                       local_sequence=seq, connection_id=conn, flags=frozenset({"reconnect_boundary"}))


def mid_at(i: int) -> float:
    """Deterministic wandering mid, multiple of the tick."""
    return 100_000_000.0 + TICK * round(8 * math.sin(i / 23.0) + 3 * math.sin(i / 7.0))


def session(seconds: float = 120.0, start: float = T0, step: float = 0.1, trade_every: int = 7,
            provenance: str = "real", disconnect_at: float | None = None, reconnect_after: float = 3.0) -> list[MarketEvent]:
    """connection, a SNAPSHOT book, then REALTIME books every `step` s and trades; optional reconnect."""
    seq = Seq()
    evs = [local(seq(), start, CONNECTION, "c1", provenance)]
    conn, i, t = "c1", 0, start + 0.05
    first = True
    while t < start + seconds:
        if disconnect_at is not None and conn == "c1" and t >= start + disconnect_at:
            evs.append(local(seq(), t, DISCONNECT, "c1", provenance))
            t += reconnect_after
            conn = "c2"
            evs.append(local(seq(), t, CONNECTION, "c2", provenance))
            t += 0.05
            first = True
        m = mid_at(i)
        evs.append(book(seq(), t, m - TICK, m + TICK, stream="SNAPSHOT" if first else "REALTIME", conn=conn,
                        provenance=provenance))
        first = False
        if i % trade_every == 3:
            evs.append(trade(seq(), t + 0.01, "buy" if (i // trade_every) % 3 else "sell", 0.002 * (1 + i % 5),
                             conn=conn, provenance=provenance))
        i += 1
        t = round(t + step, 6)
    return evs


def span(evs: list[MarketEvent]) -> tuple[float, float]:
    return evs[0].received_timestamp, max(e.received_timestamp for e in evs)


def params(**kw) -> GridParams:
    return GridParams(**kw)


def study_config(**overrides):
    """The registered config with test-only overrides (recorded as overrides, never silent)."""
    return load_config(**overrides)
