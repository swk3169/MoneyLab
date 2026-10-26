"""On-disk format of a recorded Polymarket CLOB dataset (one market per directory).

    <root>/<condition_id>/
      dataset.json                     identity: condition id, synthetic flag, source, interval
      state.json                       recorder checkpoint and status (restart/resume, HTTP 451, ...)
      metadata/<stamp>_<hash12>.json   GET /clob-markets + GET /rewards/markets payloads, new file
                                       only when the content changes
      records/<YYYYMMDD>/<seq>.json    one record per observation, seq zero-padded, never rewritten

Record kinds (field `kind`):
  book       `books` = the raw POST /books response items for this market, unmodified, plus a
             per-token `tokens` summary (outcome, best bid/ask, depth, last trade, tick, min size)
  unchanged  book content identical to record `ref_seq`; only the server timestamps changed
  error      the poll failed (network, HTTP status, bad payload); no market data

Every file is written atomically (storage.atomic) and every record carries a sha256 `checksum`
of its own canonical JSON, so integrity can be verified offline.

Duplicate handling:
  * identical content AND identical server timestamps as the last stored observation
    -> nothing is written (same server snapshot fetched twice), counted in state
  * identical content, different (or unknown) server timestamps -> `unchanged` record

Field names inside `books` / `market_info` / `rewards` are whatever the server sent. The
summary fields are derived with clob_parser, whose field mapping is UNVERIFIED against a live
response (HTTP 451 from the dev environment, see clob_parser docstring).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.providers.polymarket.clob_parser import (
    parse_clob_market_info,
    parse_order_book,
    parse_rewards,
)
from moneylab.recording.core import checksum_ok, iso, with_checksum  # noqa: F401 - re-exported
from moneylab.storage.atomic import atomic_write_json, cleanup_tmp, sha256_of

log = logging.getLogger(__name__)

SCHEMA_DATASET = "moneylab.polymarket.recording.dataset/1"
SCHEMA_STATE = "moneylab.polymarket.recording.state/1"
SCHEMA_METADATA = "moneylab.polymarket.recording.metadata/1"
SCHEMA_RECORD = "moneylab.polymarket.recording.record/1"

RECORD_KINDS = ("book", "unchanged", "error")
# Fields excluded from the content hash: they change on every poll even if the book does not.
VOLATILE_BOOK_FIELDS = ("timestamp", "hash")
MAX_RUN_HISTORY = 20

_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


class DatasetMismatch(ValueError):
    """An existing dataset directory belongs to a different market or data source."""


def dataset_dirname(condition_id: str) -> str:
    return _SAFE.sub("_", condition_id)[:120] or "unknown"


def _stamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y%m%dT%H%M%S%fZ")


# --- book helpers --------------------------------------------------------------------------

def _asset(raw: dict[str, Any]) -> str:
    return str(raw.get("asset_id"))


def book_content(raw_books: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Books without volatile fields, sorted by token: the basis of duplicate detection."""
    return [
        {k: v for k, v in b.items() if k not in VOLATILE_BOOK_FIELDS}
        for b in sorted(raw_books, key=_asset)
    ]


def content_hash(raw_books: list[dict[str, Any]]) -> str:
    return sha256_of(book_content(raw_books))


def server_timestamps(raw_books: list[dict[str, Any]]) -> dict[str, Any]:
    return {_asset(b): b.get("timestamp") for b in raw_books}


def summarize_book(raw: dict[str, Any], outcome: str | None) -> dict[str, Any]:
    """Per-token summary. Raises ValueError on an unusable book (no asset_id, not an object)."""
    b = parse_order_book(raw)
    return {
        "token_id": b.token_id,
        "outcome": outcome,
        "best_bid": b.best_bid,
        "best_ask": b.best_ask,
        "spread": None if b.spread is None else round(b.spread, 6),
        "bid_depth_levels": len(b.bids),
        "ask_depth_levels": len(b.asks),
        "last_trade_price": b.last_trade_price,
        "tick_size": b.tick_size,
        "min_order_size": b.min_order_size,
        "neg_risk": b.neg_risk,
        "server_timestamp": b.timestamp,
    }


def summarize_metadata(
    condition_id: str, market_info: Any, rewards: Any, rebate_rate: float
) -> dict[str, Any]:
    """Parsed view of the metadata payloads. Raises ValueError if market_info is unusable."""
    reward_cfg = parse_rewards(rewards) if rewards else None
    params = parse_clob_market_info(market_info, condition_id, reward_cfg, rebate_rate)
    return {
        "tokens": [{"token_id": t.token_id, "outcome": t.outcome} for t in params.tokens],
        "tick_size": params.tick_size,
        "min_order_size": params.min_order_size,
        "fee_schedule": {
            "rate": params.fee.rate, "exponent": params.fee.exponent, "taker_only": params.fee.taker_only,
            "rebate_rate": params.fee.rebate_rate, "enabled": params.fee.enabled,
        },
        "reward_config": None if reward_cfg is None else {
            "max_spread_cents": reward_cfg.max_spread_cents,
            "min_size": reward_cfg.min_size,
            "daily_rate_total": reward_cfg.daily_rate(),
            "allocations": [
                {"daily_rate": a.daily_rate,
                 "start_date": a.start_date.isoformat() if a.start_date else None,
                 "end_date": a.end_date.isoformat() if a.end_date else None}
                for a in reward_cfg.allocations
            ],
        },
    }


# --- reading -------------------------------------------------------------------------------

def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def record_seq(path: Path) -> int | None:
    try:
        return int(Path(path).stem)
    except ValueError:
        return None


def record_paths(dataset_dir: Path) -> list[Path]:
    """All record files, ordered by seq (the order they were written)."""
    paths = [p for p in (Path(dataset_dir) / "records").glob("*/*.json") if record_seq(p) is not None]
    return sorted(paths, key=lambda p: record_seq(p) or 0)


def metadata_paths(dataset_dir: Path) -> list[Path]:
    return sorted((Path(dataset_dir) / "metadata").glob("*.json"))


def load_metadata_versions(dataset_dir: Path) -> dict[str, dict[str, Any]]:
    """hash -> metadata document, in write order."""
    out: dict[str, dict[str, Any]] = {}
    for p in metadata_paths(dataset_dir):
        doc = read_json(p)
        out[str(doc.get("hash"))] = doc
    return out


# --- writing -------------------------------------------------------------------------------

@dataclass
class AppendResult:
    kind: str  # book | unchanged | duplicate | error
    seq: int | None = None
    path: Path | None = None


@dataclass
class _Cursor:
    """What the store needs to remember between observations (rebuilt from disk on resume)."""

    last_seq: int = 0
    last_book_seq: int | None = None
    last_content_hash: str | None = None
    last_server_ts: dict[str, Any] = field(default_factory=dict)
    last_recorded_at: float | None = None


class RecordingStore:
    """Append-only writer for one market's dataset. Use `RecordingStore.open(...)`."""

    def __init__(self, path: Path, condition_id: str, dataset: dict[str, Any]):
        self.path = Path(path)
        self.condition_id = condition_id
        self.dataset = dataset
        self.cursor = _Cursor()
        self.state: dict[str, Any] = {}
        self.metadata: dict[str, Any] | None = None
        self.resumed = False
        self.removed_tmp: list[Path] = []
        self.warnings: list[str] = []

    # -- open / resume --
    @classmethod
    def open(
        cls, root: Path, condition_id: str, *, synthetic: bool, source: str, interval: float, now: float,
        origin: str | None = None,
    ) -> RecordingStore:
        """`origin` identifies where data comes from (API base URL, fixture file). A dataset only
        ever holds one origin: resuming with a different one raises DatasetMismatch."""
        path = Path(root) / dataset_dirname(condition_id)
        ds_file = path / "dataset.json"
        if ds_file.exists():
            dataset = read_json(ds_file)
            if dataset.get("condition_id") != condition_id:
                raise DatasetMismatch(f"{path} holds condition {dataset.get('condition_id')}, not {condition_id}")
            if bool(dataset.get("synthetic")) != synthetic:
                raise DatasetMismatch(
                    f"{path} holds {'synthetic' if dataset.get('synthetic') else 'real'} data; "
                    f"refusing to mix {'synthetic' if synthetic else 'real'} records into it"
                )
            if origin is not None and dataset.get("origin") not in (None, origin):
                raise DatasetMismatch(f"{path} was recorded from {dataset.get('origin')}; refusing to mix {origin}")
            store = cls(path, condition_id, dataset)
            store.resumed = True
        else:
            dataset = {
                "schema": SCHEMA_DATASET, "condition_id": condition_id, "synthetic": synthetic,
                "source": source, "origin": origin, "interval_seconds": interval, "created_at": iso(now),
            }
            atomic_write_json(ds_file, dataset)
            store = cls(path, condition_id, dataset)
        store.removed_tmp = cleanup_tmp(path)
        store._load_state()
        store._rebuild_cursor()
        store._load_latest_metadata()
        return store

    def _load_state(self) -> None:
        try:
            self.state = read_json(self.path / "state.json")
        except FileNotFoundError:
            self.state = {}
        except (OSError, ValueError) as exc:
            self.warnings.append(f"state.json unreadable ({exc}); rebuilt from records")
            self.state = {}
        self.state.setdefault("schema", SCHEMA_STATE)
        self.state.setdefault("condition_id", self.condition_id)
        self.state.setdefault("status", "idle")
        self.state.setdefault("counters", {})
        self.state.setdefault("runs", [])

    def _rebuild_cursor(self) -> None:
        """Disk is the source of truth: continue after the highest seq actually written."""
        paths = record_paths(self.path)
        c = self.cursor
        c.last_seq = record_seq(paths[-1]) if paths else 0
        if self.state.get("last_seq") not in (None, c.last_seq):
            self.warnings.append(f"state.json last_seq={self.state.get('last_seq')} but disk has {c.last_seq}; using disk")
        for p in reversed(paths):
            try:
                rec = read_json(p)
            except (OSError, ValueError) as exc:
                self.warnings.append(f"unreadable record {p.name}: {exc}")
                continue
            if c.last_recorded_at is None:
                c.last_recorded_at = rec.get("recorded_at")
            if rec.get("kind") == "book":
                c.last_book_seq, c.last_content_hash = rec["seq"], rec.get("content_hash")
                c.last_server_ts = server_timestamps(rec.get("books") or [])
                break
            if rec.get("kind") == "unchanged":
                c.last_book_seq, c.last_content_hash = rec.get("ref_seq"), rec.get("content_hash")
                c.last_server_ts = dict(rec.get("server_timestamps") or {})
                break

    def _load_latest_metadata(self) -> None:
        paths = metadata_paths(self.path)
        if paths:
            try:
                self.metadata = read_json(paths[-1])
            except (OSError, ValueError) as exc:
                self.warnings.append(f"unreadable metadata {paths[-1].name}: {exc}")

    # -- metadata --
    @property
    def metadata_hash(self) -> str | None:
        return self.metadata.get("hash") if self.metadata else None

    @property
    def token_outcomes(self) -> dict[str, str]:
        tokens = (self.metadata or {}).get("summary", {}).get("tokens") or []
        return {t["token_id"]: t["outcome"] for t in tokens}

    def save_metadata(
        self, market_info: Any, rewards: Any, *, fetched_at: float, rebate_rate: float,
        rebate_rate_source: str, rewards_error: str | None = None,
    ) -> bool:
        """Store a metadata version if it differs from the latest. Returns True if written.
        Raises ValueError if market_info cannot be parsed (nothing is written)."""
        summary = summarize_metadata(self.condition_id, market_info, rewards, rebate_rate)
        h = sha256_of({"market_info": market_info, "rewards": rewards, "rebate_rate": rebate_rate})
        if h == self.metadata_hash:
            return False
        doc = {
            "schema": SCHEMA_METADATA, "condition_id": self.condition_id, "hash": h,
            "fetched_at": fetched_at, "fetched_at_iso": iso(fetched_at),
            "synthetic": self.dataset.get("synthetic"),
            "rebate_rate": rebate_rate, "rebate_rate_source": rebate_rate_source,
            "summary": summary,
            "market_info": market_info,  # raw GET /clob-markets/{condition_id}
            "rewards": rewards,  # raw GET /rewards/markets/{condition_id} (None if unavailable)
            "rewards_error": rewards_error,
        }
        atomic_write_json(self.path / "metadata" / f"{_stamp(fetched_at)}_{h[:12]}.json", doc)
        self.metadata = doc
        self._count("metadata_versions")
        return True

    # -- records --
    def _write_record(self, record: dict[str, Any]) -> AppendResult:
        seq = self.cursor.last_seq + 1
        ts = float(record["recorded_at"])
        full = with_checksum({
            "schema": SCHEMA_RECORD, "seq": seq, "condition_id": self.condition_id,
            "recorded_at_iso": iso(ts), "metadata_hash": self.metadata_hash, **record,
        })
        day = datetime.fromtimestamp(ts, UTC).strftime("%Y%m%d")
        path = atomic_write_json(self.path / "records" / day / f"{seq:010d}.json", full, indent=None)
        self.cursor.last_seq = seq
        self.cursor.last_recorded_at = ts
        self._count(record["kind"])
        return AppendResult(record["kind"], seq, path)

    def append_books(
        self, raw_books: list[dict[str, Any]], recorded_at: float, source: str, missing_tokens: list[str] | None = None
    ) -> AppendResult:
        """Record one observation of this market's books. Raises ValueError for unusable books."""
        outcomes = self.token_outcomes
        summaries = [summarize_book(b, outcomes.get(_asset(b))) for b in sorted(raw_books, key=_asset)]
        h = content_hash(raw_books)
        sts = server_timestamps(raw_books)
        c = self.cursor
        if h == c.last_content_hash:
            if sts == c.last_server_ts and all(v is not None for v in sts.values()):
                self._count("duplicates_skipped")
                return AppendResult("duplicate")
            res = self._write_record({
                "kind": "unchanged", "recorded_at": recorded_at, "source": source,
                "ref_seq": c.last_book_seq, "content_hash": h, "server_timestamps": sts,
                "missing_tokens": missing_tokens or [],
            })
        else:
            res = self._write_record({
                "kind": "book", "recorded_at": recorded_at, "source": source, "content_hash": h,
                "missing_tokens": missing_tokens or [], "tokens": summaries,
                "books": sorted(raw_books, key=_asset),  # raw server payload items, unmodified
            })
            c.last_book_seq = res.seq
        c.last_content_hash, c.last_server_ts = h, sts
        return res

    def append_error(self, recorded_at: float, error: dict[str, Any], source: str) -> AppendResult:
        return self._write_record({"kind": "error", "recorded_at": recorded_at, "source": source, "error": error})

    # -- state --
    def _count(self, key: str, n: int = 1) -> None:
        counters = self.state.setdefault("counters", {})
        counters[key] = counters.get(key, 0) + n

    def begin_run(self, now: float, recorder: str) -> None:
        prev = self.state.get("status")
        if prev and prev not in ("idle", "running", "completed", "stopped", "source_exhausted"):
            log.warning("%s: previous run ended with status %s; trying again once", self.condition_id, prev)
        runs = self.state.setdefault("runs", [])
        runs.append({"recorder": recorder, "started_at": iso(now), "stopped_at": None, "status": "running",
                     "previous_status": prev})
        del runs[:-MAX_RUN_HISTORY]
        self.state.pop("blocked", None)
        self.update_state(now, status="running")

    def end_run(self, now: float, status: str) -> None:
        runs = self.state.get("runs") or []
        if runs:
            runs[-1].update(stopped_at=iso(now), status=status)
        self.update_state(now, status=status)

    def update_state(self, now: float, **fields: Any) -> None:
        c = self.cursor
        self.state.update(fields)
        self.state.update(
            updated_at=iso(now), last_seq=c.last_seq, last_book_seq=c.last_book_seq,
            last_content_hash=c.last_content_hash, last_recorded_at=c.last_recorded_at,
            metadata_hash=self.metadata_hash,
        )
        atomic_write_json(self.path / "state.json", self.state)
