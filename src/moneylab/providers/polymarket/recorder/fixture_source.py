"""Offline ClobSource that serves a timeline fixture one snapshot per `fetch_books` call.

Lets the whole Recorder -> dataset -> Replay -> PaperEngine pipeline run without network
access. Its `clock()` returns the timestamp of the snapshot last served, so recorded
timestamps equal the fixture's and a replay reproduces the original timeline exactly.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from moneylab.providers.polymarket.recorder.base import SourceExhausted


class TimelineFixtureSource:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        meta = raw.get("meta") or {}
        self.condition_id = str(raw["condition_id"])
        self.market_info = raw["market_info"]
        self.rewards = raw.get("rewards")
        self.snapshots: list[dict[str, Any]] = sorted(raw["snapshots"], key=lambda s: float(s["ts"]))
        self.synthetic = bool(meta.get("synthetic", True))
        self.rebate_rate = float(meta.get("rebate_rate", 0.0))
        self._next = 0
        self._now = float(self.snapshots[0]["ts"]) if self.snapshots else 0.0

    def clock(self) -> float:
        return self._now

    @staticmethod
    def no_sleep(_seconds: float) -> None:
        """Time in a fixture only advances with the data."""

    def resume_after(self, ts: float) -> int:
        """Skip snapshots already recorded (timestamp <= ts) when a dataset is resumed in a new
        process. Returns how many were skipped."""
        skipped = 0
        while self._next < len(self.snapshots) and float(self.snapshots[self._next]["ts"]) <= ts:
            self._next += 1
            skipped += 1
        if skipped:
            self._now = float(self.snapshots[self._next - 1]["ts"])
        return skipped

    @property
    def remaining(self) -> int:
        return len(self.snapshots) - self._next

    def fetch_books(self, token_ids: list[str]) -> Any:
        if self._next >= len(self.snapshots):
            raise SourceExhausted(f"{self.path.name}: all {len(self.snapshots)} snapshots served")
        snap = self.snapshots[self._next]
        self._next += 1
        self._now = float(snap["ts"])
        wanted = set(token_ids)
        return [copy.deepcopy(b) for b in snap["books"] if str(b.get("asset_id")) in wanted]

    def fetch_book(self, token_id: str) -> Any:
        books = self.fetch_books([token_id])
        if not books:
            raise LookupError(f"token {token_id} not in snapshot")
        return books[0]

    def fetch_market_info(self, condition_id: str) -> Any:
        if condition_id != self.condition_id:
            raise LookupError(f"{self.path.name} has no market {condition_id}")
        return copy.deepcopy(self.market_info)

    def fetch_rewards(self, condition_id: str) -> Any:
        if condition_id != self.condition_id or self.rewards is None:
            raise LookupError(f"{self.path.name} has no rewards for {condition_id}")
        return copy.deepcopy(self.rewards)

    def close(self) -> None:
        pass
