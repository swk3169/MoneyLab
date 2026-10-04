"""Read a recorded dataset back as provider-neutral BookSnapshots (RecordedBookSource).

Records are read lazily in seq order, so long recordings do not have to fit in memory.
`unchanged` records re-emit the referenced book with the newly observed server timestamps;
`error` records become error events (the kill switch then sees the outage as it happened).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

from moneylab.core.exceptions import ProviderError
from moneylab.domain.market_params import MarketParams
from moneylab.domain.orderbook import BookSnapshot, OrderBook
from moneylab.providers.base import RecordedBookSource, RecordedEvent
from moneylab.providers.polymarket.clob_parser import (
    parse_clob_market_info,
    parse_order_book,
    parse_rewards,
    parse_timestamp,
)
from moneylab.providers.polymarket.recorder.store import (
    checksum_ok,
    load_metadata_versions,
    read_json,
    record_paths,
    record_seq,
)

log = logging.getLogger(__name__)


def params_from_metadata(doc: dict[str, Any]) -> MarketParams:
    rewards = parse_rewards(doc["rewards"]) if doc.get("rewards") else None
    return parse_clob_market_info(doc["market_info"], str(doc["condition_id"]), rewards,
                                  float(doc.get("rebate_rate") or 0.0))


def _books(raw_books: list[dict[str, Any]], ts: float) -> dict[str, OrderBook]:
    out = {}
    for raw in raw_books:
        b = parse_order_book(raw)
        out[b.token_id] = b if b.timestamp is not None else replace(b, timestamp=ts)
    return out


class RecordingReader(RecordedBookSource):
    name = "polymarket-recording"

    def __init__(self, path: str | Path, verify_checksums: bool = True):
        self.path = Path(path)
        self.verify_checksums = verify_checksums
        self.warnings: list[str] = []
        try:
            dataset = read_json(self.path / "dataset.json")
            self.condition_id = str(dataset["condition_id"])
            self.synthetic = bool(dataset.get("synthetic"))
            self.metadata_versions = load_metadata_versions(self.path)
            self._paths = record_paths(self.path)
        except (OSError, KeyError, ValueError) as exc:
            raise ProviderError(self.name, f"Not a readable recording {self.path}: {exc}", exc) from exc
        if not self.metadata_versions:
            raise ProviderError(self.name, f"{self.path}: no market metadata recorded (did the first poll fail?)")
        doc = self.metadata_versions.get(self._first_book_metadata_hash() or "") \
            or list(self.metadata_versions.values())[-1]
        try:
            self.params = params_from_metadata(doc)
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(self.name, f"{self.path}: bad metadata: {exc}", exc) from exc
        fees = {repr(v.get("summary", {}).get("fee_schedule")) for v in self.metadata_versions.values()}
        if len(fees) > 1:
            self.warnings.append(
                f"fee schedule changed during the recording ({len(fees)} versions); replay uses the one in effect "
                "at the first book record"
            )
        self.description = (
            f"{'SYNTHETIC ' if self.synthetic else ''}recording {self.condition_id}: {len(self._paths)} records, "
            f"source {dataset.get('source')}, interval {dataset.get('interval_seconds')}s"
        )

    def _read(self, path: Path) -> dict[str, Any]:
        try:
            rec = read_json(path)
        except (OSError, ValueError) as exc:
            raise ProviderError(self.name, f"Unreadable record {path}: {exc}", exc) from exc
        if self.verify_checksums and not checksum_ok(rec):
            raise ProviderError(self.name, f"Checksum mismatch in {path} (run `moneylab record-verify`)")
        return rec

    def _first_book_metadata_hash(self) -> str | None:
        for p in self._paths:
            try:
                rec = read_json(p)
            except (OSError, ValueError):
                continue
            if rec.get("kind") == "book":
                return rec.get("metadata_hash")
        return None

    def _load_seq(self, seq: int) -> dict[str, Any]:
        for p in self._paths:
            if record_seq(p) == seq:
                return self._read(p)
        raise ProviderError(self.name, f"{self.path}: referenced record {seq} is missing")

    def iter_events(self) -> Iterator[RecordedEvent]:
        last_book: tuple[int, list[dict[str, Any]]] | None = None  # (seq, raw books)
        for p in self._paths:
            rec = self._read(p)
            ts = float(rec["recorded_at"])
            kind = rec.get("kind")
            try:
                if kind == "book":
                    last_book = (int(rec["seq"]), rec["books"])
                    yield RecordedEvent(ts, snapshot=BookSnapshot(ts, _books(rec["books"], ts)))
                elif kind == "unchanged":
                    ref = int(rec["ref_seq"])
                    if last_book is None or last_book[0] != ref:
                        last_book = (ref, self._load_seq(ref)["books"])
                    sts = rec.get("server_timestamps") or {}
                    books = {
                        t: replace(b, timestamp=parse_timestamp(sts.get(t)) or ts)
                        for t, b in _books(last_book[1], ts).items()
                    }
                    yield RecordedEvent(ts, snapshot=BookSnapshot(ts, books))
                elif kind == "error":
                    err = rec.get("error") or {}
                    yield RecordedEvent(ts, error=f"recorded {err.get('category', 'error')}: {err.get('message', '')}")
                else:
                    self.warnings.append(f"{p.name}: unknown record kind {kind!r} skipped")
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderError(self.name, f"Bad record {p}: {exc}", exc) from exc


def open_recording(path: str | Path, verify_checksums: bool = True) -> RecordingReader:
    return RecordingReader(path, verify_checksums)
