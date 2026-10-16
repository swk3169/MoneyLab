"""research-build / research-stats / research-final, on processed events (provider-neutral).

build:  events file -> 1 s grid (as-of state, features) -> labels -> split (purge, lookback cut)
        -> train/validation file + locked test file (split.py) + manifest.json
stats:  train + validation only -> leaderboard (test LOCKED), fits frozen on train
final:  once per run: frozen fits applied to test -> final leaderboard

The exchange-specific steps (integrity check, raw manifest, quality report, event export) run
before `build` in the CLI; their results arrive here as `source` metadata.
"""

from __future__ import annotations

import csv
import io
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.research.book_state import DISCONTINUITY, REASONS
from moneylab.research.config import StudyConfig, load_config
from moneylab.research.features import FEATURES, registry_dict, validate_feature_names
from moneylab.research.io import read_events
from moneylab.research.labels import compute_labels, exec_label_name, label_names, mid_label_names
from moneylab.research.leaderboard import COLUMNS, build_leaderboard, finalize_with_test, fit_from_dict
from moneylab.research.manifest import (
    DRY_RUN,
    EVIDENCE,
    evidence_label,
    git_state,
    now_iso,
    read_manifest,
    write_manifest,
)
from moneylab.research.sampling import GridParams, build_grid
from moneylab.research.split import (
    TRAIN,
    VALIDATION,
    InsufficientDataError,
    LockedTestVault,
    compute_boundaries,
    load_segment,
    split_rows,
    write_split,
)
from moneylab.storage.atomic import atomic_write_json, atomic_write_text, sha256_file

SESSIONS_PER_RUN = 1  # a run is one recording session; walk-forward across sessions comes later
STATS_DIR, FINAL_DIR = "stats", "final"


class ProvenanceError(ValueError):
    """Research input is not provenance=real (or mixes provenances)."""


def _scan_events(path: Path) -> dict[str, Any]:
    """First pass: provenance check and the available time range (no state, no features)."""
    header, events = read_events(path)
    provs: set[str] = set()
    start = end = None
    n = 0
    for ev in events:
        n += 1
        provs.add(ev.provenance)
        start = ev.received_timestamp if start is None else start
        end = ev.received_timestamp if end is None else max(end, ev.received_timestamp)
    return {"header": header, "provenances": provs, "start": start, "end": end, "events": n}


def build(events_path: Path, run_dir: Path, cfg: StudyConfig, *, session_id: str, source: dict[str, Any],
          dry_run: bool = False, allow_fixture: bool = False) -> dict[str, Any]:
    """Build one run. `source` = {provenance, market, raw_manifest_sha256, quality, ...} from the adapter."""
    validate_feature_names(cfg.signals + cfg.state)
    if cfg.overrides and not dry_run:
        raise ValueError(f"config overrides {sorted(cfg.overrides)} are only allowed for --dry-run")
    scan = _scan_events(events_path)
    provs = scan["provenances"]
    if len(provs) > 1:
        raise ProvenanceError(f"events mix provenances {sorted(provs)}")
    provenance = next(iter(provs), source.get("provenance"))
    if provenance != source.get("provenance"):
        raise ProvenanceError(f"events are {provenance!r} but the source dataset says {source.get('provenance')!r}")
    if provenance != cfg.provenance_required and not allow_fixture:
        raise ProvenanceError(f"refusing provenance={provenance!r}: research needs {cfg.provenance_required!r} "
                              "(fixture data only with allow_fixture, and then it is NOT_EVIDENCE)")
    if scan["start"] is None:
        raise ValueError("no events")

    params = GridParams(cfg.grid_seconds, cfg.warmup_seconds, cfg.stale_book_seconds, cfg.gap_seconds,
                        cfg.delays_ms, cfg.sizes_btc)
    _, events = read_events(events_path)
    grid = build_grid(events, scan["start"], scan["end"], params)
    if not len(grid):
        raise InsufficientDataError("the events span less than one grid step")
    labels = compute_labels(grid, cfg.horizons)
    boundaries = compute_boundaries(grid.times[0], grid.times[-1], cfg.train, cfg.validation, cfg.embargo_seconds)
    horizon_of = {}
    for h in cfg.horizons:
        for name in label_names((h,), cfg.sizes_btc, cfg.delays_ms):
            horizon_of[name] = h
    cols = {**grid.cols, **labels}
    extra = {"reasons": [sorted(r) for r in grid.reasons], "book_age": grid.book_age}
    rows, split_counts = split_rows(grid.times, cols, horizon_of, boundaries, cfg.max_delay_seconds, extra)

    duration = scan["end"] - scan["start"]
    evidence = evidence_label(provenance, duration, cfg.nominal_session_seconds, dry_run)
    reason_counts = Counter(r for rs in grid.reasons for r in rs)
    exclusions = {
        "grid_rows": len(grid), "clean_rows": sum(1 for r in grid.reasons if not r),
        "excluded_rows": sum(1 for r in grid.reasons if r),
        "by_reason": {k: reason_counts.get(k, 0) for k in REASONS},
        "discontinuity_rows": sum(1 for k in range(len(grid)) if grid.is_discontinuity(k)),
        "discontinuity_reasons": sorted(DISCONTINUITY),
        **split_counts,
        "valid_mid_labels": {f"h{h}": sum(1 for v in labels[mid_label_names(h)[1]] if v == v) for h in cfg.horizons},
        "valid_exec_labels_decision": {
            f"h{h}": sum(1 for v in labels[exec_label_name("buy", h, cfg.decision_size_btc, cfg.decision_delay_ms)]
                         if v == v) for h in cfg.horizons},
        "feature_missing_rate_clean_rows": _missing_rates(grid),
        "source_flags": (source.get("quality") or {}).get("export", {}).get("flags", {}),
        "source_skipped_lines": (source.get("quality") or {}).get("export", {}).get("skipped", {}),
    }

    run_dir = Path(run_dir)
    header = {"schema": "moneylab.research.grid/1", "run_dir": run_dir.name, "session_id": session_id,
              "provenance": provenance, "evidence": evidence}
    outputs = write_split(run_dir, header, rows)
    outputs["events_file"] = str(events_path)
    outputs["events_sha256"] = sha256_file(events_path)
    manifest = {
        "run_id": run_dir.name, "kind": "DRY_RUN" if dry_run else "RESEARCH", "created_at": now_iso(),
        "evidence": evidence, "provenance": provenance, "market": source.get("market"), "session_id": session_id,
        "sessions": SESSIONS_PER_RUN,
        "collection": {"start": scan["start"], "end": scan["end"], "duration_seconds": duration,
                       "start_iso": _iso(scan["start"]), "end_iso": _iso(scan["end"])},
        "dataset_sha256": outputs["events_sha256"],
        "raw_manifest_sha256": source.get("raw_manifest_sha256"),
        "source": {k: v for k, v in source.items() if k not in ("quality", "clock", "capture")},
        "quality_summary": _quality_summary(source.get("quality") or {}),
        "preregistration_sha256": cfg.preregistration_sha256, "config_sha256": cfg.config_sha256,
        "config_path": str(cfg.config_path), "config_overrides": cfg.overrides,
        "git": git_state(),
        "feature_registry": registry_dict(), "signals": list(cfg.signals), "state_features": list(cfg.state),
        "horizons": list(cfg.horizons), "sizes_btc": list(cfg.sizes_btc),
        "grid_seconds": cfg.grid_seconds,
        "split": {**boundaries.to_dict(), "shares": [cfg.train, cfg.validation, cfg.test],
                  "rows": outputs["rows"]},
        "exclusions": exclusions,
        "fee_scenarios_bps": list(cfg.fee_bps_scenarios), "decision_fee_bps": cfg.decision_fee_bps,
        "account_fee_confirmed": cfg.account_fee_bps is not None, "delay_scenarios_ms": list(cfg.delays_ms),
        "outputs": outputs, "validation": {"completed": False}, "test_access_count": 0,
        **_clock_fields(source.get("clock")), "capture": source.get("capture"),
    }
    write_manifest(run_dir, manifest)
    return manifest


CLOCK_FIELDS = ("clock_offset_start_ms", "clock_offset_end_ms", "clock_offset_min_ms", "clock_offset_max_ms",
                "clock_offset_median_ms", "clock_measurements", "clock_quality_status")


def _clock_fields(clock: dict[str, Any] | None) -> dict[str, Any]:
    """Clock quality metadata (never used to correct timestamps, features or labels)."""
    if not clock:
        return {**{k: None for k in CLOCK_FIELDS}, "clock_measurements": 0, "clock_quality_status": "NOT_MEASURED"}
    return {**{k: clock.get(k) for k in CLOCK_FIELDS}, "clock": clock}


def _iso(ts: float | None) -> str | None:
    return None if ts is None else datetime.fromtimestamp(ts, UTC).isoformat()


def _missing_rates(grid) -> dict[str, float]:
    clean = [k for k in range(len(grid)) if not grid.reasons[k]]
    out = {}
    for f in FEATURES:
        col = grid.cols[f.name]
        out[f.name] = (sum(1 for k in clean if col[k] != col[k]) / len(clean)) if clean else math.nan
    return out


def _quality_summary(q: dict[str, Any]) -> dict[str, Any]:
    keys = ("duration_seconds", "stream_types", "book_levels", "expected_units", "book_interarrival_ms",
            "recv_minus_exchange_ms", "gap_count", "note")
    return {k: q.get(k) for k in keys if k in q}


def config_for_run(run_dir: Path, config_path: Path | None = None) -> StudyConfig:
    """The config a run was built with (same overrides); refuses if the registered files changed."""
    m = read_manifest(run_dir)
    cfg = load_config(config_path or Path(m["config_path"]), **(m.get("config_overrides") or {}))
    if cfg.config_sha256 != m["config_sha256"] or cfg.preregistration_sha256 != m["preregistration_sha256"]:
        raise ValueError("configs/research_v04.toml or the preregistration changed since research-build; "
                         "a changed study needs a new build")
    return cfg


def stats(run_dir: Path, cfg: StudyConfig) -> dict[str, Any]:
    """Train + validation only. The test split is not read (and cannot be: load_segment refuses)."""
    run_dir = Path(run_dir)
    m = read_manifest(run_dir)
    if m.get("test_access_count", 0):
        raise ValueError("the test split was already evaluated; the validation leaderboard is frozen")
    train, val = load_segment(run_dir, TRAIN), load_segment(run_dir, VALIDATION)
    board, fits, details = build_leaderboard(train, val, cfg, m["evidence"], m.get("sessions", SESSIONS_PER_RUN))
    out = run_dir / STATS_DIR
    lb = atomic_write_json(out / "leaderboard.json", {"evidence": m["evidence"], "kind": m["kind"], "rows": board})
    atomic_write_text(out / "leaderboard.csv", _csv(board))
    fp = atomic_write_json(out / "fits.json", [f.to_dict() for f in fits])
    atomic_write_json(out / "details.json", details)
    m["validation"] = {"completed": True, "completed_at": now_iso(), "leaderboard_sha256": sha256_file(lb),
                       "fits_sha256": sha256_file(fp), "train_rows": len(train), "validation_rows": len(val),
                       "tests": len(board)}
    write_manifest(run_dir, m)
    return {"manifest": m, "leaderboard": board}


def final(run_dir: Path, cfg: StudyConfig) -> dict[str, Any]:
    """Evaluate the test split exactly once with the fits frozen by `stats`."""
    run_dir = Path(run_dir)
    test_rows = LockedTestVault(run_dir).open_once(config_sha256=cfg.config_sha256,
                                                   preregistration_sha256=cfg.preregistration_sha256)
    m = read_manifest(run_dir)
    fits_path = run_dir / STATS_DIR / "fits.json"
    if sha256_file(fits_path) != m["validation"]["fits_sha256"]:
        raise ValueError("fits.json changed after research-stats")
    fits = [fit_from_dict(d) for d in json.loads(fits_path.read_text(encoding="utf-8"))]
    board = json.loads((run_dir / STATS_DIR / "leaderboard.json").read_text(encoding="utf-8"))["rows"]
    details = json.loads((run_dir / STATS_DIR / "details.json").read_text(encoding="utf-8"))
    rows = finalize_with_test(board, fits, details, test_rows, cfg, m["evidence"], m.get("sessions", 1))
    out = run_dir / FINAL_DIR
    p = atomic_write_json(out / "leaderboard_final.json", {"evidence": m["evidence"], "rows": rows})
    atomic_write_text(out / "leaderboard_final.csv", _csv(rows))
    m["final"] = {"completed_at": now_iso(), "test_rows": len(test_rows), "leaderboard_sha256": sha256_file(p)}
    write_manifest(run_dir, m)
    return {"manifest": m, "leaderboard": rows}


def _csv(rows: list[dict[str, Any]]) -> str:
    cols = list(COLUMNS) + sorted({k for r in rows for k in r} - set(COLUMNS))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: json.dumps(v) if isinstance(v, dict) else v for k, v in r.items()})
    return buf.getvalue()


def is_evidence(manifest: dict[str, Any]) -> bool:
    return manifest.get("evidence") == EVIDENCE


__all__ = ["ProvenanceError", "build", "stats", "final", "config_for_run", "is_evidence", "DRY_RUN"]
