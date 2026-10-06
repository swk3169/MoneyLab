"""Offline integrity check of an Upbit recording (no network).

Errors make a dataset unfit for replay (checksum, sequence gaps, provenance mixing, raw text
that no longer matches its hash, derived values that disagree with the raw message, two
non-duplicate trades with the same sequential_id). Warnings describe data quality: crossed
books, aggregated levels, fewer units than requested, receive-clock steps, gaps, leftovers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from moneylab.providers.upbit.parser import UpbitParseError, load_message, parse_orderbook, parse_trade
from moneylab.providers.upbit.recorder.store import (
    EVENT_TYPES,
    PROVENANCES,
    SCHEMA_DATASET,
    SCHEMA_LINE,
    line_ok,
    read_json,
    read_segment,
    segment_paths,
)
from moneylab.storage.atomic import TMP_SUFFIX, sha256_of

MAX_MESSAGES = 100


@dataclass
class UpbitIntegrityReport:
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    first_ts: float | None = None  # received timestamps (local clock)
    last_ts: float | None = None
    status: str | None = None
    synthetic: bool | None = None
    provenance: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {"path": str(self.path), "ok": self.ok, "status": self.status, "synthetic": self.synthetic,
                "provenance": self.provenance, "counts": self.counts, "first_ts": self.first_ts,
                "last_ts": self.last_ts, "errors": self.errors, "warnings": self.warnings}


def _close(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def verify_upbit_recording(path: str | Path, gap_warning_seconds: float = 10.0) -> UpbitIntegrityReport:
    path = Path(path)
    rep = UpbitIntegrityReport(path)
    counts = rep.counts

    def bump(key: str, n: int = 1) -> None:
        counts[key] = counts.get(key, 0) + n

    def error(msg: str) -> None:
        if len(rep.errors) < MAX_MESSAGES:
            rep.errors.append(msg)
        bump("errors_total")

    def warn(msg: str) -> None:
        if len(rep.warnings) < MAX_MESSAGES:
            rep.warnings.append(msg)
        bump("warnings_total")

    try:
        dataset = read_json(path / "dataset.json")
    except (OSError, ValueError) as exc:
        rep.errors.append(f"dataset.json unreadable: {exc}")
        return rep
    if dataset.get("schema") != SCHEMA_DATASET:
        rep.errors.append(f"unknown dataset schema {dataset.get('schema')!r}")
        return rep
    market, provenance = dataset.get("market"), dataset.get("provenance")
    rep.provenance, rep.synthetic = provenance, bool(dataset.get("synthetic"))
    units_wanted = dataset.get("orderbook_units")
    if provenance not in PROVENANCES:
        error(f"unknown provenance {provenance!r}")
    if rep.synthetic != (provenance != "real"):
        error(f"provenance {provenance!r} contradicts synthetic={rep.synthetic}")

    tmp = list(path.rglob(f"*{TMP_SUFFIX}"))
    if tmp:
        warn(f"{len(tmp)} leftover temp file(s) from an interrupted write (removed on next recorder start)")

    expected_seq = 1
    trade_ids: dict[int, int] = {}
    prev_recv: float | None = None
    last_ex: dict[str, int] = {}
    for p in segment_paths(path):
        try:
            lines = read_segment(p)
        except (OSError, ValueError) as exc:
            error(f"segment {p.name} unreadable: {exc}")
            continue
        bump("segments")
        if lines and int(p.stem) != lines[0].get("local_sequence"):
            error(f"segment {p.name} starts with local_sequence {lines[0].get('local_sequence')}")
        for ln in lines:
            seq = ln.get("local_sequence")
            et = ln.get("event_type")
            bump("lines")
            bump(f"event_{et}")
            if ln.get("schema") != SCHEMA_LINE or et not in EVENT_TYPES:
                error(f"line {seq}: unknown schema/event_type ({ln.get('schema')!r}, {et!r})")
                continue
            if not line_ok(ln):
                error(f"line {seq}: checksum mismatch (file modified or corrupted)")
            if seq != expected_seq:
                error(f"local_sequence gap/disorder: expected {expected_seq}, found {seq}")
            expected_seq = (seq if isinstance(seq, int) else expected_seq) + 1
            if ln.get("provenance") != provenance:
                error(f"line {seq}: provenance {ln.get('provenance')!r} != dataset {provenance!r}")
            if ln.get("market") not in (None, market):
                error(f"line {seq}: market {ln.get('market')} != {market}")
            try:
                recv = float(ln["received_timestamp"])
            except (KeyError, TypeError, ValueError):
                error(f"line {seq}: missing received_timestamp")
                continue
            if prev_recv is not None:
                if recv < prev_recv:
                    warn(f"line {seq}: received_timestamp went backwards by {prev_recv - recv:.6f}s (local clock step)")
                elif recv - prev_recv > gap_warning_seconds:
                    warn(f"gap of {recv - prev_recv:.1f}s before line {seq}")
            prev_recv = recv
            rep.first_ts = recv if rep.first_ts is None else rep.first_ts
            rep.last_ts = recv
            raw = ln.get("raw")
            if raw is not None and sha256_of(raw) != ln.get("raw_sha256"):
                error(f"line {seq}: raw text does not match raw_sha256")
            if et not in ("orderbook", "trade") or ln.get("parse_error"):
                if ln.get("parse_error"):
                    bump("parse_errors")
                continue
            if ln.get("duplicate"):
                bump(f"duplicate_{et}")
            try:
                obj = load_message(raw)
                if obj.get("timestamp") != ln.get("exchange_timestamp"):
                    error(f"line {seq}: exchange_timestamp differs from raw `timestamp`")
                if et == "orderbook":
                    msg = parse_orderbook(obj)
                    stored, again = ln.get("orderbook") or {}, msg.summary()
                    bad = [k for k in again if not _close(stored.get(k), again[k])]
                    if bad:
                        error(f"line {seq}: stored orderbook summary differs from raw for {bad}")
                    if msg.level not in (None, 0, 0.0):
                        warn(f"line {seq}: orderbook level={msg.level} (price aggregation)")
                    if units_wanted and len(msg.units) != units_wanted:
                        bump("orderbook_units_short")
                    s = again
                    if s["best_bid"] is not None and s["best_ask"] is not None and s["best_bid"] >= s["best_ask"]:
                        warn(f"line {seq}: crossed/locked book (bid {s['best_bid']} >= ask {s['best_ask']})")
                    if s["best_bid"] is None or s["best_ask"] is None:
                        warn(f"line {seq}: one-sided book")
                else:
                    tr = parse_trade(obj)
                    stored, again = ln.get("trade") or {}, tr.summary()
                    bad = [k for k in again if not _close(stored.get(k), again[k])]
                    if bad:
                        error(f"line {seq}: stored trade summary differs from raw for {bad}")
                    if not ln.get("duplicate"):
                        if tr.sequential_id in trade_ids:
                            error(f"line {seq}: sequential_id {tr.sequential_id} already recorded at line "
                                  f"{trade_ids[tr.sequential_id]} but not flagged duplicate")
                        trade_ids[tr.sequential_id] = seq
                if not ln.get("duplicate"):
                    ex = int(obj["timestamp"])
                    if et in last_ex and ex < last_ex[et]:
                        bump(f"{et}_exchange_ts_inversions")
                    last_ex[et] = max(ex, last_ex.get(et, ex))
            except (UpbitParseError, TypeError, KeyError, ValueError) as exc:
                error(f"line {seq}: stored {et} does not parse: {exc}")
    counts["records"] = expected_seq - 1

    try:
        state = read_json(path / "state.json")
    except FileNotFoundError:
        warn("state.json missing (rebuilt from segments on next start)")
        state = {}
    except (OSError, ValueError) as exc:
        error(f"state.json unreadable: {exc}")
        state = {}
    rep.status = state.get("status")
    last = expected_seq - 1
    if state.get("last_seq") is not None:
        if state["last_seq"] > last:
            error(f"state.json last_seq={state['last_seq']} but only {last} lines exist")
        elif state["last_seq"] < last:
            warn(f"state.json last_seq={state['last_seq']} behind disk ({last}); interrupted before checkpoint")
    if counts.get("orderbook_units_short"):
        warn(f"{counts['orderbook_units_short']} orderbook message(s) carried fewer than {units_wanted} units")
    return rep
