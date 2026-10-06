"""Sources of BookSnapshots for the simulation runner.

* TimelineBookStream - replays a MarketTimeline (fixture, or recorded live data)
* PollingBookStream  - polls an OrderBookProvider (live REST data once access works)
* ReplayBookStream   - replays a recorded dataset (RecordedBookSource) lazily, including the
                       data-source failures that happened while recording

Both yield StreamEvent; a provider failure is an event, not an exception, so the kill switch
can count consecutive errors.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from moneylab.core.exceptions import ProviderError
from moneylab.domain.orderbook import BookSnapshot, MarketTimeline
from moneylab.domain.trades import TradeTick
from moneylab.providers.base import OrderBookProvider, RecordedBookSource

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class StreamEvent:
    timestamp: float
    snapshot: BookSnapshot | None = None
    error: str | None = None
    trades: tuple[TradeTick, ...] = ()
    received_timestamp: float | None = None
    local_sequence: int | None = None


class TimelineBookStream:
    def __init__(self, timeline: MarketTimeline):
        self.timeline = timeline

    def __iter__(self) -> Iterator[StreamEvent]:
        for snap in self.timeline.snapshots:
            yield StreamEvent(snap.timestamp, snapshot=snap)


class PollingBookStream:
    """Polls `provider.get_order_books(token_ids)` every `interval` seconds, `max_polls` times.

    Read-only. `sleep`/`clock` are injectable for offline tests.
    """

    def __init__(
        self, provider: OrderBookProvider, token_ids: list[str], interval: float = 60.0, max_polls: int = 60,
        clock: Callable[[], float] = time.time, sleep: Callable[[float], None] = time.sleep,
    ):
        self.provider, self.token_ids, self.interval, self.max_polls = provider, token_ids, interval, max_polls
        self.clock, self.sleep = clock, sleep

    def __iter__(self) -> Iterator[StreamEvent]:
        for i in range(self.max_polls):
            if i:
                self.sleep(self.interval)
            now = self.clock()
            try:
                books = self.provider.get_order_books(self.token_ids)
            except ProviderError as exc:
                yield StreamEvent(now, error=str(exc))
                continue
            yield StreamEvent(now, snapshot=BookSnapshot(timestamp=now, books=books))


@dataclass
class ReplayStats:
    snapshots: int = 0
    errors: int = 0
    trade_events: int = 0
    skipped_out_of_order: int = 0
    skipped_outside_window: int = 0


class ReplayBookStream:
    """Replays a recorded dataset into the simulation runner.

    * `start`/`end` (unix seconds, inclusive) restrict the replay window.
    * Recorded failures become error events (the kill switch counts them as in live polling);
      `include_errors=False` drops them.
    * Events whose timestamp goes backwards are skipped and counted, never reordered.
    * Trade-only events (streaming recorders) are passed through with their trades.
    """

    def __init__(
        self, source: RecordedBookSource, start: float | None = None, end: float | None = None,
        include_errors: bool = True,
    ):
        self.source, self.start, self.end, self.include_errors = source, start, end, include_errors
        self.stats = ReplayStats()

    def __iter__(self) -> Iterator[StreamEvent]:
        self.stats = ReplayStats()
        last: float | None = None
        for ev in self.source.iter_events():
            if (self.start is not None and ev.timestamp < self.start) or (
                self.end is not None and ev.timestamp > self.end
            ):
                self.stats.skipped_outside_window += 1
                continue
            if last is not None and ev.timestamp < last:
                log.warning("replay: event at %s is older than %s; skipped", ev.timestamp, last)
                self.stats.skipped_out_of_order += 1
                continue
            last = ev.timestamp
            meta = {"received_timestamp": ev.received_timestamp, "local_sequence": ev.local_sequence}
            if ev.snapshot is None and not ev.trades:
                if not self.include_errors:
                    continue
                self.stats.errors += 1
                yield StreamEvent(ev.timestamp, error=ev.error or "recorded data-source failure", **meta)
                continue
            if ev.snapshot is not None:
                self.stats.snapshots += 1
            if ev.trades:
                self.stats.trade_events += 1
            yield StreamEvent(ev.timestamp, snapshot=ev.snapshot, trades=ev.trades, **meta)
