"""On-disk format of an Upbit WebSocket recording (one market per directory).

    <root>/<market>/
      dataset.json                              identity: market, provenance, origin, units, schema
      state.json                                recorder checkpoint: status, counters, runs, last seq
      segments/<YYYYMMDD>/<first_seq>.jsonl     immutable JSON-lines segments, written atomically

Every received WebSocket message becomes one line, in arrival order, with the original message
text stored verbatim in `raw` (lossless: prices such as "116409000.00000000" and 17-digit
`sequential_id`s keep their exact server representation). Recorder-local events (connection
opened, disconnect, failure) are lines too, so a replay sees every gap.

Line fields (all lines):
  local_sequence      1, 2, 3, ... per dataset, contiguous across segments and restarts
  event_type          orderbook | trade | status | server_error | unknown | malformed |
                      connection | disconnect | failure
  market              Upbit pair code (None for messages that carry none)
  exchange_timestamp  documented message field `timestamp`, integer ms (None for local events)
  received_timestamp  local UTC epoch seconds taken right after the frame was received
  received_at         the same as ISO-8601 UTC
  connection_id       WebSocket connection the message arrived on
  provenance          real | fixture   (dataset-wide; a dataset never mixes the two)
  raw                 original message text (None for local events), `raw_sha256` its hash
  checksum            sha256 of the line without this field
plus, for orderbook: `orderbook` {best_bid, best_ask, spread, bid_depth, ask_depth, ...}
      for trade:     `trade` {sequential_id, trade_price, trade_volume, ask_bid, trade_timestamp}
      for market events: `duplicate` (+ `duplicate_of`), `parse_error`, `stream_type`;
                         orderbook also `book_key` (content hash used for duplicate detection)
      for local events: `detail` (subscription request, failure classification, close code)
No global exchange sequence across orderbook and trade exists, so none is invented.

Duplicates are kept on disk (lossless) but flagged, and replay skips them:
  trade      same official `sequential_id` as an earlier trade of this market
  orderbook  same `timestamp` AND identical book content (stream_type ignored) as one of the
             recent orderbook messages; identical books with different timestamps are normal
             and are never flagged.

Crash safety: lines are buffered in memory and flushed as a new segment every
`flush_interval` seconds / `flush_max_events` lines, on disconnect and on shutdown. A crash
loses at most the unflushed buffer; files on disk are always complete.
"""

from __future__ import annotations

import json
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.recording.core import checksum_ok, iso, with_checksum
from moneylab.storage.atomic import atomic_write_json, atomic_write_text, cleanup_tmp, sha256_file, sha256_of

log = logging.getLogger(__name__)

SCHEMA_DATASET = "moneylab.upbit.recording.dataset/1"
SCHEMA_STATE = "moneylab.upbit.recording.state/1"
SCHEMA_LINE = "moneylab.upbit.recording.event/1"
SCHEMA_RAW_MANIFEST = "moneylab.upbit.raw_manifest/1"
# Recorder-owned metadata next to the raw data (not part of the raw manifest itself):
CAPTURE_MANIFEST = "capture_manifest.json"  # per-run termination reason, disk, clock, counters, raw hashes
CLOCK_LOG = "clock_monitor.jsonl"  # core.clock_monitor measurements (quality metadata only)
PROVENANCES = ("real", "fixture")
MARKET_EVENTS = ("orderbook", "trade")
LOCAL_EVENTS = ("connection", "disconnect", "failure")
EVENT_TYPES = MARKET_EVENTS + ("status", "server_error", "unknown", "malformed") + LOCAL_EVENTS
MAX_RUN_HISTORY = 20
TRADE_ID_MEMORY = 100_000
BOOK_KEY_MEMORY = 256
RESUME_SCAN_SEGMENTS = 50

_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


class DatasetMismatch(ValueError):
    """An existing dataset belongs to another market, provenance, origin or configuration."""


def dataset_dirname(market: str) -> str:
    return _SAFE.sub("_", market)[:60] or "unknown"


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def segment_paths(dataset_dir: Path) -> list[Path]:
    """All segments ordered by their first local_sequence (= write order)."""
    out = []
    for p in (Path(dataset_dir) / "segments").glob("*/*.jsonl"):
        try:
            out.append((int(p.stem), p))
        except ValueError:
            continue
    return [p for _, p in sorted(out)]


def read_segment(path: Path) -> list[dict[str, Any]]:
    lines = []
    for n, text in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not text.strip():
            continue
        try:
            lines.append(json.loads(text))
        except ValueError as exc:
            raise ValueError(f"{path.name} line {n}: {exc}") from exc
    return lines


def book_content_key(obj: dict[str, Any]) -> str:
    """Hash of an orderbook message without `stream_type` (a reconnect re-sends the same book
    as SNAPSHOT that was REALTIME before)."""
    return sha256_of({k: v for k, v in obj.items() if k != "stream_type"})


@dataclass
class _Cursor:
    last_seq: int = 0
    last_received: float | None = None
    trade_ids: OrderedDict[int, int] = field(default_factory=OrderedDict)  # sequential_id -> local seq
    book_keys: OrderedDict[tuple[int, str], int] = field(default_factory=OrderedDict)


class UpbitStore:
    """Append-only writer for one market. Use `UpbitStore.open(...)`."""

    def __init__(self, path: Path, market: str, dataset: dict[str, Any]):
        self.path = Path(path)
        self.market = market
        self.dataset = dataset
        self.provenance: str = dataset["provenance"]
        self.cursor = _Cursor()
        self.state: dict[str, Any] = {}
        self.buffer: list[dict[str, Any]] = []
        self.buffer_started: float | None = None
        self.resumed = False
        self.removed_tmp: list[Path] = []
        self.warnings: list[str] = []
        self.segments_written = 0

    # -- open / resume ------------------------------------------------------------------
    @classmethod
    def open(
        cls, root: Path, market: str, *, provenance: str, origin: str, orderbook_units: int, source: str,
        now: float, doc_refs: tuple[str, ...] = (),
    ) -> UpbitStore:
        if provenance not in PROVENANCES:
            raise ValueError(f"provenance must be one of {PROVENANCES}, got {provenance!r}")
        path = Path(root) / dataset_dirname(market)
        ds_file = path / "dataset.json"
        if ds_file.exists():
            dataset = read_json(ds_file)
            if dataset.get("schema") != SCHEMA_DATASET:
                raise DatasetMismatch(f"{path} is not an Upbit recording (schema {dataset.get('schema')!r})")
            if dataset.get("market") != market:
                raise DatasetMismatch(f"{path} holds market {dataset.get('market')}, not {market}")
            if dataset.get("provenance") != provenance:
                raise DatasetMismatch(
                    f"{path} holds {dataset.get('provenance')} data; refusing to mix {provenance} records into it")
            if dataset.get("origin") != origin:
                raise DatasetMismatch(f"{path} was recorded from {dataset.get('origin')}; refusing to mix {origin}")
            if dataset.get("orderbook_units") != orderbook_units:
                raise DatasetMismatch(f"{path} was recorded with {dataset.get('orderbook_units')} orderbook units, "
                                      f"not {orderbook_units}")
            store = cls(path, market, dataset)
            store.resumed = True
        else:
            dataset = {
                "schema": SCHEMA_DATASET, "line_schema": SCHEMA_LINE, "provider": "upbit", "market": market,
                "provenance": provenance, "synthetic": provenance != "real", "source": source, "origin": origin,
                "orderbook_units": orderbook_units, "format": "DEFAULT", "level": 0,
                "created_at": iso(now), "doc_refs": list(doc_refs),
            }
            atomic_write_json(ds_file, dataset)
            store = cls(path, market, dataset)
        store.removed_tmp = cleanup_tmp(path)
        store._load_state()
        store._rebuild_cursor()
        return store

    def _load_state(self) -> None:
        try:
            self.state = read_json(self.path / "state.json")
        except FileNotFoundError:
            self.state = {}
        except (OSError, ValueError) as exc:
            self.warnings.append(f"state.json unreadable ({exc}); rebuilt from segments")
            self.state = {}
        self.state.setdefault("schema", SCHEMA_STATE)
        self.state.setdefault("market", self.market)
        self.state.setdefault("status", "idle")
        self.state.setdefault("counters", {})
        self.state.setdefault("runs", [])

    def _rebuild_cursor(self) -> None:
        """Disk is the source of truth: continue after the last line actually written, and
        remember recent trade ids / book keys so a restart does not re-record duplicates."""
        paths = segment_paths(self.path)
        c = self.cursor
        recent: list[dict[str, Any]] = []
        for p in reversed(paths[-RESUME_SCAN_SEGMENTS:]):
            try:
                lines = read_segment(p)
            except (OSError, ValueError) as exc:
                self.warnings.append(f"unreadable segment {p.name}: {exc}")
                continue
            if lines and c.last_seq == 0:
                c.last_seq = int(lines[-1]["local_sequence"])
                c.last_received = lines[-1].get("received_timestamp")
            recent[:0] = lines
            if sum(1 for ln in recent if ln.get("event_type") == "trade") >= TRADE_ID_MEMORY:
                break
        for ln in recent:
            self._remember(ln)
        if self.state.get("last_seq") not in (None, c.last_seq):
            self.warnings.append(f"state.json last_seq={self.state.get('last_seq')} but disk has {c.last_seq}; "
                                 "using disk (unflushed events of a crashed run are lost)")

    def _remember(self, line: dict[str, Any]) -> None:
        c = self.cursor
        if line.get("duplicate") or line.get("parse_error"):
            return
        if line.get("event_type") == "trade" and line.get("trade"):
            c.trade_ids[int(line["trade"]["sequential_id"])] = int(line["local_sequence"])
            while len(c.trade_ids) > TRADE_ID_MEMORY:
                c.trade_ids.popitem(last=False)
        elif line.get("event_type") == "orderbook" and line.get("book_key"):
            c.book_keys[(int(line["exchange_timestamp"]), line["book_key"])] = int(line["local_sequence"])
            while len(c.book_keys) > BOOK_KEY_MEMORY:
                c.book_keys.popitem(last=False)

    # -- duplicate checks ---------------------------------------------------------------
    def duplicate_trade(self, sequential_id: int) -> int | None:
        return self.cursor.trade_ids.get(sequential_id)

    def duplicate_book(self, exchange_timestamp: int, key: str) -> int | None:
        return self.cursor.book_keys.get((exchange_timestamp, key))

    # -- append / flush -----------------------------------------------------------------
    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        """Assign the next local_sequence, add identity fields and a checksum, buffer it."""
        seq = self.cursor.last_seq + 1
        recv = float(event["received_timestamp"])
        line = with_checksum({
            "schema": SCHEMA_LINE, "local_sequence": seq, "market": event.get("market", self.market),
            "provenance": self.provenance, "received_at": iso(recv), **event,
        })
        self.cursor.last_seq = seq
        self.cursor.last_received = recv
        if not self.buffer:
            self.buffer_started = recv
        self.buffer.append(line)
        self._remember(line)
        self._count(line["event_type"])
        if line.get("duplicate"):
            self._count(f"duplicate_{line['event_type']}")
        return line

    def flush_due(self, now: float, interval: float, max_events: int) -> bool:
        return bool(self.buffer) and (len(self.buffer) >= max_events
                                      or (self.buffer_started is not None and now - self.buffer_started >= interval))

    def flush(self) -> Path | None:
        if not self.buffer:
            return None
        first = self.buffer[0]
        day = datetime.fromtimestamp(float(first["received_timestamp"]), UTC).strftime("%Y%m%d")
        text = "".join(json.dumps(ln, ensure_ascii=False, separators=(",", ":")) + "\n" for ln in self.buffer)
        path = atomic_write_text(self.path / "segments" / day / f"{int(first['local_sequence']):012d}.jsonl", text)
        self.buffer, self.buffer_started = [], None
        self.segments_written += 1
        self._count("segments")
        return path

    # -- state --------------------------------------------------------------------------
    def _count(self, key: str, n: int = 1) -> None:
        counters = self.state.setdefault("counters", {})
        counters[key] = counters.get(key, 0) + n

    def begin_run(self, now: float, recorder: str) -> None:
        prev = self.state.get("status")
        runs = self.state.setdefault("runs", [])
        runs.append({"recorder": recorder, "started_at": iso(now), "stopped_at": None, "status": "running",
                     "previous_status": prev, "first_seq": self.cursor.last_seq + 1})
        del runs[:-MAX_RUN_HISTORY]
        self.state.pop("blocked", None)
        self.update_state(now, status="running")

    def end_run(self, now: float, status: str, termination_reason: str | None = None) -> None:
        runs = self.state.get("runs") or []
        if runs:
            runs[-1].update(stopped_at=iso(now), status=status, last_seq=self.cursor.last_seq,
                            termination_reason=termination_reason)
        self.update_state(now, status=status, termination_reason=termination_reason)

    def update_state(self, now: float, **fields: Any) -> None:
        """Checkpoint. `last_seq` is what is durable on disk, not what is still buffered."""
        self.state.update(fields)
        durable = self.cursor.last_seq - len(self.buffer)
        self.state.update(updated_at=iso(now), last_seq=durable, provenance=self.provenance)
        atomic_write_json(self.path / "state.json", self.state)


def line_ok(line: dict[str, Any]) -> bool:
    return checksum_ok(line)


def raw_file_manifest(dataset_dir: Path) -> dict[str, Any]:
    """sha256 + size of every raw file (dataset.json, state.json, segments). Read-only."""
    root = Path(dataset_dir)
    files = [root / "dataset.json", root / "state.json", *segment_paths(root)]
    entries = [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
               for p in files if p.exists()]
    ds = read_json(root / "dataset.json")
    body = {"schema": SCHEMA_RAW_MANIFEST, "market": ds.get("market"), "provenance": ds.get("provenance"),
            "synthetic": ds.get("synthetic"), "origin": ds.get("origin"), "files": entries}
    return {**body, "manifest_sha256": sha256_of(body)}
