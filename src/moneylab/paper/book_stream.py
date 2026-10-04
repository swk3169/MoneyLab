"""Sources of BookSnapshots for the simulation runner.

* TimelineBookStream - replays a MarketTimeline (fixture, or recorded live data)
* PollingBookStream  - polls an OrderBookProvider (live REST data once access works)

Both yield StreamEvent; a provider failure is an event, not an exception, so the kill switch
can count consecutive errors.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from moneylab.core.exceptions import ProviderError
from moneylab.domain.orderbook import BookSnapshot, MarketTimeline
from moneylab.providers.base import OrderBookProvider


@dataclass(frozen=True)
class StreamEvent:
    timestamp: float
    snapshot: BookSnapshot | None = None
    error: str | None = None


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
