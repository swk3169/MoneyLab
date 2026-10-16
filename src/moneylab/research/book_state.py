"""As-of market state on the local receive clock, with no look-ahead.

Events are applied in ARRIVAL order (local_sequence). An event becomes available at
`available_at = max(received_timestamp of it and of every event that arrived before it)`, so a
receive-clock step backwards can delay an event but never make it visible early. The state at
time s contains exactly the events with available_at <= s; `advance_to` only moves forward.

Duplicates are never applied. SNAPSHOT trades are re-sends of past trades and are not added to
the trade window. Connection/disconnect/failure events and `sequence_gap` flags advance a
discontinuity counter: two samples with different counters have a break between them.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from moneylab.domain.market_events import (
    BOOK,
    CONNECTION,
    CROSSED_BOOK,
    DISCONNECT,
    DUPLICATE,
    FAILURE,
    LOCKED_BOOK,
    SEQUENCE_GAP,
    TIMESTAMP_REVERSE,
    TRADE,
    MarketEvent,
)

# Row exclusion reasons. DISCONTINUITY reasons also invalidate every window that contains the row.
NO_BOOK, GAP, WARMUP_ROW, STALE, CROSSED, LOCKED, TS_REVERSE = (
    "no_book", "gap", "warmup", "stale_book", "crossed_book", "locked_book", "timestamp_reverse")
DISCONTINUITY = frozenset({NO_BOOK, GAP, WARMUP_ROW})
REASONS = (NO_BOOK, GAP, WARMUP_ROW, STALE, CROSSED, LOCKED, TS_REVERSE)


@dataclass(frozen=True)
class StateParams:
    warmup_seconds: float = 5.0
    stale_book_seconds: float = 1.0
    gap_seconds: float = 10.0
    trade_memory_seconds: float = 60.0


@dataclass(frozen=True)
class AsOf:
    """What was known at `time`."""

    time: float
    book: MarketEvent | None
    book_available_at: float | None
    break_counter: int
    reasons: frozenset[str]
    trades: tuple[tuple[float, int, float], ...]  # (available_at, sign, volume), REALTIME, non-duplicate

    @property
    def book_age(self) -> float | None:
        return None if self.book_available_at is None else self.time - self.book_available_at

    @property
    def ok(self) -> bool:
        return not self.reasons


class AsOfReplayer:
    def __init__(self, events: Iterable[MarketEvent], params: StateParams = StateParams()):
        self.params = params
        self._it: Iterator[MarketEvent] = iter(events)
        self._next: MarketEvent | None = None
        self._next_at: float | None = None
        self._avail = float("-inf")
        self._now = float("-inf")
        self.book: MarketEvent | None = None
        self.book_at: float | None = None
        self.in_gap = False
        self.conn_first_realtime: float | None = None
        self.seen_connection = False
        self.breaks = 0
        self.trades: deque[tuple[float, int, float]] = deque()
        self.applied = 0
        self.skipped_duplicates = 0
        self._peek()

    def _peek(self) -> None:
        self._next = next(self._it, None)
        if self._next is not None:
            self._avail = max(self._avail, self._next.received_timestamp)
            self._next_at = self._avail

    @property
    def exhausted(self) -> bool:
        return self._next is None

    def _apply(self, ev: MarketEvent, at: float) -> None:
        self.applied += 1
        if SEQUENCE_GAP in ev.flags:
            self.breaks += 1
        if ev.event_type == CONNECTION:
            self.breaks += 1
            self.in_gap, self.seen_connection, self.conn_first_realtime = False, True, None
            return
        if ev.event_type in (DISCONNECT, FAILURE):
            self.breaks += 1
            self.in_gap = True
            return
        if DUPLICATE in ev.flags:
            self.skipped_duplicates += 1
            return
        if ev.event_type == BOOK:
            self.book, self.book_at = ev, at
            if ev.stream_type == "REALTIME" and self.conn_first_realtime is None:
                self.conn_first_realtime = at
        elif ev.event_type == TRADE and ev.stream_type != "SNAPSHOT" and ev.trade is not None:
            self.trades.append((at, ev.trade.sign, ev.trade.volume))

    def advance_to(self, s: float) -> AsOf:
        if s < self._now:
            raise ValueError("advance_to must not go back in time")
        self._now = s
        while self._next is not None and self._next_at <= s:
            ev, at = self._next, self._next_at
            self._apply(ev, at)
            self._peek()
        horizon = s - self.params.trade_memory_seconds
        while self.trades and self.trades[0][0] <= horizon:
            self.trades.popleft()
        return AsOf(s, self.book, self.book_at, self.breaks, self._reasons(s), tuple(self.trades))

    def _reasons(self, s: float) -> frozenset[str]:
        p = self.params
        r: set[str] = set()
        bb = ba = None
        if self.book is not None:
            bb, ba = self.book.best_bid, self.book.best_ask
        if bb is None or ba is None:  # no book yet, or a one-sided book: no mid
            r.add(NO_BOOK)
            if self.book is None:
                return frozenset(r)
        age = s - self.book_at
        if self.in_gap or age > p.gap_seconds:
            r.add(GAP)
        if (self.conn_first_realtime is None or s < self.conn_first_realtime + p.warmup_seconds
                or self.book.stream_type == "SNAPSHOT"):
            r.add(WARMUP_ROW)
        if age > p.stale_book_seconds:
            r.add(STALE)
        if CROSSED_BOOK in self.book.flags or (bb is not None and ba is not None and bb > ba):
            r.add(CROSSED)
        if LOCKED_BOOK in self.book.flags or (bb is not None and ba is not None and bb == ba):
            r.add(LOCKED)
        if TIMESTAMP_REVERSE in self.book.flags:
            r.add(TS_REVERSE)
        return frozenset(r)
