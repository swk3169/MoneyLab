"""Read an Upbit recording back as provider-neutral events (RecordedBookSource).

Books and trades are rebuilt from the stored raw message text (not from the derived summary),
so a replay is exactly as good as what the exchange sent.

Ordering (`order`):
  "exchange" (default)  by (exchange_timestamp, received_timestamp, local_sequence). There is
                        no exchange-wide sequence across orderbook and trade, so this key only
                        uses what each event really carries; equal exchange timestamps are
                        broken deterministically by local receive time, then arrival order.
                        Streaming: events are held in a heap and released once the newest
                        exchange timestamp seen is `reorder_window_ms` ahead; an event delayed
                        more than that is released late and counted in `stats.late_events`
                        (ReplayBookStream then skips it as out of order).
  "received"            arrival order (local_sequence); event timestamps are receive times.

Local events (disconnect, failure, server error, malformed frame) become error events stamped
with the newest exchange time received before them, so a replay sees every gap in place. Duplicates and
unparseable market messages are skipped (counted). connection/status lines carry no market data.
"""

from __future__ import annotations

import heapq
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from moneylab.core.exceptions import ProviderError
from moneylab.domain.market_params import FeeSchedule, MarketParams, TokenInfo
from moneylab.domain.orderbook import BookSnapshot
from moneylab.providers.base import RecordedBookSource, RecordedEvent
from moneylab.providers.upbit.parser import UpbitParseError, load_message, parse_orderbook, parse_trade
from moneylab.providers.upbit.recorder.store import SCHEMA_DATASET, line_ok, read_json, read_segment, segment_paths

log = logging.getLogger(__name__)

ERROR_EVENTS = ("disconnect", "failure", "server_error", "malformed")


@dataclass
class ReaderStats:
    lines: int = 0
    orderbooks: int = 0
    trades: int = 0
    errors: int = 0
    duplicates_skipped: int = 0
    parse_errors_skipped: int = 0
    non_market_skipped: int = 0
    late_events: int = 0


def is_upbit_recording(path: str | Path) -> bool:
    try:
        return read_json(Path(path) / "dataset.json").get("schema") == SCHEMA_DATASET
    except (OSError, ValueError, AttributeError):
        return False


class UpbitRecordingReader(RecordedBookSource):
    name = "upbit-recording"

    def __init__(self, path: str | Path, verify_checksums: bool = True, order: str = "exchange",
                 reorder_window_ms: int = 5000):
        if order not in ("exchange", "received"):
            raise ValueError("order must be 'exchange' or 'received'")
        self.path = Path(path)
        self.verify_checksums = verify_checksums
        self.order = order
        self.reorder_window_ms = int(reorder_window_ms)
        self.warnings: list[str] = []
        self.stats = ReaderStats()
        try:
            self.dataset = read_json(self.path / "dataset.json")
            if self.dataset.get("schema") != SCHEMA_DATASET:
                raise ValueError(f"unknown schema {self.dataset.get('schema')!r}")
            self.market = str(self.dataset["market"])
            self.provenance = str(self.dataset["provenance"])
            self._paths = segment_paths(self.path)
        except (OSError, KeyError, ValueError) as exc:
            raise ProviderError(self.name, f"Not a readable Upbit recording {self.path}: {exc}", exc) from exc
        self.synthetic = bool(self.dataset.get("synthetic"))
        if self.synthetic != (self.provenance != "real"):
            raise ProviderError(self.name, f"{self.path}: provenance {self.provenance!r} contradicts "
                                           f"synthetic={self.synthetic}")
        # Spot market: no outcomes, no resolution, fees NOT modelled. Never feed this to the
        # prediction-market strategies (the CLI refuses to).
        self.params = MarketParams(condition_id=self.market, tokens=(TokenInfo(self.market, self.market),),
                                   tick_size=0.0, min_order_size=0.0, fee=FeeSchedule.free(),
                                   question=f"Upbit {self.market} spot order book (not a prediction market)")
        self.description = (
            f"{'SYNTHETIC ' if self.synthetic else ''}Upbit recording {self.market} ({self.provenance}): "
            f"{len(self._paths)} segments, origin {self.dataset.get('origin')}"
        )

    # --- raw lines --------------------------------------------------------------------
    def iter_lines(self) -> Iterator[dict[str, Any]]:
        """Every stored line in arrival (local_sequence) order, checksum-verified."""
        for p in self._paths:
            try:
                lines = read_segment(p)
            except (OSError, ValueError) as exc:
                raise ProviderError(self.name, f"Unreadable segment {p}: {exc}", exc) from exc
            for line in lines:
                if self.verify_checksums and not line_ok(line):
                    raise ProviderError(self.name, f"Checksum mismatch in {p} seq {line.get('local_sequence')} "
                                                   "(run `moneylab record-verify`)")
                if line.get("provenance") != self.provenance:
                    raise ProviderError(self.name, f"{p}: line {line.get('local_sequence')} has provenance "
                                                   f"{line.get('provenance')!r}, dataset is {self.provenance!r}")
                yield line

    # --- events -----------------------------------------------------------------------
    def _to_event(self, line: dict[str, Any]) -> RecordedEvent | None:
        et = line.get("event_type")
        seq, recv = int(line["local_sequence"]), float(line["received_timestamp"])
        if et in ("orderbook", "trade"):
            if line.get("duplicate"):
                self.stats.duplicates_skipped += 1
                return None
            if line.get("parse_error"):
                self.stats.parse_errors_skipped += 1
                return None
            try:
                obj = load_message(line["raw"])
                if et == "orderbook":
                    msg = parse_orderbook(obj)
                    book = msg.to_order_book()
                    self.stats.orderbooks += 1
                    return RecordedEvent(msg.exchange_timestamp, snapshot=BookSnapshot(msg.exchange_timestamp,
                                                                                      {book.token_id: book}),
                                         received_timestamp=recv, local_sequence=seq)
                tr = parse_trade(obj)
                self.stats.trades += 1
                return RecordedEvent(tr.exchange_timestamp, trades=(tr.to_trade_tick(recv),),
                                     received_timestamp=recv, local_sequence=seq)
            except (UpbitParseError, KeyError, TypeError) as exc:
                raise ProviderError(self.name, f"{self.path}: stored {et} {seq} no longer parses: {exc}", exc) from exc
        if et in ERROR_EVENTS:
            self.stats.errors += 1
            d = line.get("detail") or {}
            msg = d.get("message") or line.get("parse_error") or ""
            return RecordedEvent(recv, error=f"recorded {et} ({d.get('category') or d.get('name') or et}): {msg}",
                                 received_timestamp=recv, local_sequence=seq)
        self.stats.non_market_skipped += 1
        return None

    def iter_events(self) -> Iterator[RecordedEvent]:
        self.stats = ReaderStats()
        if self.order == "received":
            for line in self.iter_lines():
                self.stats.lines += 1
                ev = self._to_event(line)
                if ev is not None:
                    yield RecordedEvent(ev.received_timestamp or ev.timestamp, ev.snapshot, ev.error, ev.trades,
                                        ev.received_timestamp, ev.local_sequence)
            return
        yield from self._exchange_order()

    def _exchange_order(self) -> Iterator[RecordedEvent]:
        heap: list[tuple[int, float, int, RecordedEvent]] = []
        newest_ms: int | None = None  # newest exchange time seen so far
        last_out: tuple[int, float, int] | None = None

        def release(limit_ms: int | None) -> Iterator[RecordedEvent]:
            nonlocal last_out
            while heap and (limit_ms is None or heap[0][0] <= limit_ms):
                ts, recv, seq, ev = heapq.heappop(heap)
                if last_out is not None and (ts, recv, seq) < last_out:
                    self.stats.late_events += 1
                last_out = max(last_out or (ts, recv, seq), (ts, recv, seq))
                yield ev

        for line in self.iter_lines():
            self.stats.lines += 1
            ev = self._to_event(line)
            if ev is None:
                continue
            recv, seq = float(line["received_timestamp"]), int(line["local_sequence"])
            if ev.error is None:
                ts_ms = int(line["exchange_timestamp"])
                newest_ms = ts_ms if newest_ms is None else max(newest_ms, ts_ms)
            else:  # local event: after every market event received before it
                ts_ms = newest_ms if newest_ms is not None else int(recv * 1000)
                ev = RecordedEvent(ts_ms / 1000.0, error=ev.error, received_timestamp=recv, local_sequence=seq)
            heapq.heappush(heap, (ts_ms, recv, seq, ev))
            if newest_ms is not None:
                yield from release(newest_ms - self.reorder_window_ms)
        yield from release(None)


def open_upbit_recording(path: str | Path, verify_checksums: bool = True, order: str = "exchange") -> UpbitRecordingReader:
    return UpbitRecordingReader(path, verify_checksums, order)
