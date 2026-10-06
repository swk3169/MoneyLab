"""Client-side sliding-window rate limiter (provider-neutral).

`SlidingWindowLimiter([(5, 1.0), (100, 60.0)])` allows at most 5 acquisitions in any 1 s
window and 100 in any 60 s window; `acquire()` sleeps until both windows have room.
Clock and sleep are injectable so tests never wait.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable, Iterable


class SlidingWindowLimiter:
    def __init__(
        self, limits: Iterable[tuple[int, float]], *, clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.limits = tuple((int(n), float(w)) for n, w in limits)
        if not self.limits or any(n <= 0 or w <= 0 for n, w in self.limits):
            raise ValueError("limits must be positive (count, window_seconds) pairs")
        self.clock, self.sleep = clock, sleep
        self._events: deque[float] = deque()
        self._horizon = max(w for _, w in self.limits)
        self.waited = 0.0  # total seconds slept, for reporting

    def wait_time(self, now: float | None = None) -> float:
        now = self.clock() if now is None else now
        while self._events and now - self._events[0] >= self._horizon:
            self._events.popleft()
        wait = 0.0
        for count, window in self.limits:
            recent = [t for t in self._events if now - t < window]
            if len(recent) >= count:
                wait = max(wait, window - (now - recent[-count]))
        return wait

    def acquire(self) -> float:
        """Block until an acquisition is allowed, record it, and return the seconds waited."""
        start, total = self.clock(), 0.0
        # Advance a virtual clock by what we slept, so an injected clock that does not move
        # (tests) cannot loop forever.
        while (wait := self.wait_time(start + total)) > 0:
            self.sleep(wait)
            total += wait
        self._events.append(max(self.clock(), start + total))
        self.waited += total
        return total
