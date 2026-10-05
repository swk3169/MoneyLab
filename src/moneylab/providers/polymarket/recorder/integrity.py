"""Offline integrity check of a recorded dataset (no network).

Errors make a dataset unfit for replay; warnings describe data quality worth knowing
(time gaps, crossed books, missing tokens, leftover temp files).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.providers.polymarket.recorder.store import (
    RECORD_KINDS,
    SCHEMA_DATASET,
    SCHEMA_METADATA,
    SCHEMA_RECORD,
    checksum_ok,
    content_hash,
    metadata_paths,
    read_json,
    record_paths,
    record_seq,
    summarize_book,
    summarize_metadata,
)
from moneylab.storage.atomic import TMP_SUFFIX, sha256_of

MAX_ISSUES_PER_KIND = 20


@dataclass
class IntegrityReport:
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    first_ts: float | None = None
    last_ts: float | None = None
    status: str | None = None
    synthetic: bool | None = None

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {"path": str(self.path), "ok": self.ok, "status": self.status, "synthetic": self.synthetic,
                "counts": self.counts, "first_ts": self.first_ts, "last_ts": self.last_ts,
                "errors": self.errors, "warnings": self.warnings}


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y%m%d")


def _book_problems(summary: dict[str, Any]) -> list[str]:
    out = []
    bb, ba = summary.get("best_bid"), summary.get("best_ask")
    if bb is not None and ba is not None and bb >= ba:
        out.append(f"crossed/locked book on {summary['token_id']} (bid {bb} >= ask {ba})")
    if bb is None or ba is None:
        out.append(f"one-sided book on {summary['token_id']}")
    return out


def verify_recording(path: str | Path, max_gap_factor: float = 3.0) -> IntegrityReport:
    path = Path(path)
    rep = IntegrityReport(path)
    counts = rep.counts

    def warn(msg: str) -> None:
        if len(rep.warnings) < MAX_ISSUES_PER_KIND * 5:
            rep.warnings.append(msg)
        counts["warnings_total"] = counts.get("warnings_total", 0) + 1

    # dataset identity
    try:
        dataset = read_json(path / "dataset.json")
    except (OSError, ValueError) as exc:
        rep.errors.append(f"dataset.json unreadable: {exc}")
        return rep
    if dataset.get("schema") != SCHEMA_DATASET:
        rep.errors.append(f"unknown dataset schema {dataset.get('schema')!r}")
    cid = dataset.get("condition_id")
    rep.synthetic = bool(dataset.get("synthetic"))
    interval = float(dataset.get("interval_seconds") or 0) or None

    tmp = list(path.rglob(f"*{TMP_SUFFIX}"))
    if tmp:
        warn(f"{len(tmp)} leftover temp file(s) from an interrupted write (removed on next recorder start)")

    # metadata versions
    meta_hashes: set[str] = set()
    tokens: set[str] = set()
    for p in metadata_paths(path):
        try:
            doc = read_json(p)
        except (OSError, ValueError) as exc:
            rep.errors.append(f"metadata {p.name} unreadable: {exc}")
            continue
        h = doc.get("hash")
        if doc.get("schema") != SCHEMA_METADATA:
            rep.errors.append(f"metadata {p.name}: unknown schema")
        expect = sha256_of({"market_info": doc.get("market_info"), "rewards": doc.get("rewards"),
                            "rebate_rate": doc.get("rebate_rate")})
        if h != expect or not p.stem.endswith(str(h)[:12]):
            rep.errors.append(f"metadata {p.name}: hash mismatch")
        try:
            summary = summarize_metadata(cid, doc.get("market_info"), doc.get("rewards"),
                                         float(doc.get("rebate_rate") or 0.0))
            tokens.update(t["token_id"] for t in summary["tokens"])
        except (TypeError, ValueError) as exc:
            rep.errors.append(f"metadata {p.name}: unparseable market_info: {exc}")
        meta_hashes.add(str(h))
    counts["metadata_versions"] = len(meta_hashes)

    # records
    seen: dict[int, Path] = {}
    books: dict[int, str] = {}  # seq -> content hash of book records
    prev_ts: float | None = None
    prev_seq = 0
    prev_book_key: tuple[str, Any] | None = None
    for p in record_paths(path):
        seq = record_seq(p)
        if seq in seen:
            rep.errors.append(f"duplicate seq {seq}: {seen[seq]} and {p}")
            continue
        seen[seq] = p
        try:
            rec = read_json(p)
        except (OSError, ValueError) as exc:
            rep.errors.append(f"record {p.name} unreadable: {exc}")
            continue
        kind = rec.get("kind")
        counts[kind or "unknown"] = counts.get(kind or "unknown", 0) + 1
        if rec.get("schema") != SCHEMA_RECORD or kind not in RECORD_KINDS:
            rep.errors.append(f"record {seq}: unknown schema/kind ({rec.get('schema')!r}, {kind!r})")
            continue
        if not checksum_ok(rec):
            rep.errors.append(f"record {seq}: checksum mismatch (file modified or corrupted)")
        if rec.get("seq") != seq:
            rep.errors.append(f"record file {p.name} contains seq {rec.get('seq')}")
        if rec.get("condition_id") != cid:
            rep.errors.append(f"record {seq}: condition_id {rec.get('condition_id')} != {cid}")
        if seq != prev_seq + 1:
            rep.errors.append(f"seq gap: {prev_seq} -> {seq} (records missing)")
        prev_seq = seq
        try:
            ts = float(rec["recorded_at"])
        except (KeyError, TypeError, ValueError):
            rep.errors.append(f"record {seq}: missing recorded_at")
            continue
        if p.parent.name != _day(ts):
            warn(f"record {seq} stored under {p.parent.name} but recorded on {_day(ts)}")
        if prev_ts is not None:
            if ts < prev_ts:
                rep.errors.append(f"record {seq}: time goes backwards ({prev_ts} -> {ts})")
            elif interval and ts - prev_ts > max_gap_factor * interval:
                warn(f"gap of {ts - prev_ts:.0f}s before record {seq} (interval {interval:.0f}s)")
        prev_ts = ts
        rep.first_ts = ts if rep.first_ts is None else rep.first_ts
        rep.last_ts = ts
        mh = rec.get("metadata_hash")
        if kind != "error" and mh not in meta_hashes:
            rep.errors.append(f"record {seq}: metadata {mh} not found")

        if kind == "book":
            raw = rec.get("books") or []
            if content_hash(raw) != rec.get("content_hash"):
                rep.errors.append(f"record {seq}: content_hash does not match books")
            for b in raw:
                tid = str(b.get("asset_id"))
                if tokens and tid not in tokens:
                    rep.errors.append(f"record {seq}: token {tid} not in market metadata")
                try:
                    for msg in _book_problems(summarize_book(b, None)):
                        warn(f"record {seq}: {msg}")
                except (TypeError, ValueError) as exc:
                    rep.errors.append(f"record {seq}: unparseable book: {exc}")
            key = (rec.get("content_hash"), {str(b.get("asset_id")): b.get("timestamp") for b in raw})
            if key == prev_book_key:
                warn(f"record {seq}: identical to the previous observation (should have been deduplicated)")
            prev_book_key = key
            books[seq] = str(rec.get("content_hash"))
        elif kind == "unchanged":
            ref = rec.get("ref_seq")
            if ref not in books:
                rep.errors.append(f"record {seq}: ref_seq {ref} is not an earlier book record")
            elif books[ref] != rec.get("content_hash"):
                rep.errors.append(f"record {seq}: content_hash differs from referenced record {ref}")
        if kind in ("book", "unchanged") and rec.get("missing_tokens"):
            warn(f"record {seq}: no book for {rec['missing_tokens']}")
    counts["records"] = len(seen)

    # checkpoint
    try:
        state = read_json(path / "state.json")
    except FileNotFoundError:
        warn("state.json missing (rebuilt from records on next start)")
        state = {}
    except (OSError, ValueError) as exc:
        rep.errors.append(f"state.json unreadable: {exc}")
        state = {}
    rep.status = state.get("status")
    last = max(seen) if seen else 0
    if state and state.get("last_seq") is not None:
        if state["last_seq"] > last:
            rep.errors.append(f"state.json last_seq={state['last_seq']} but only {last} records exist")
        elif state["last_seq"] < last:
            warn(f"state.json last_seq={state['last_seq']} behind disk ({last}); interrupted before checkpoint")
    if not meta_hashes and counts.get("book"):
        rep.errors.append("book records exist but no metadata was stored")
    return rep
