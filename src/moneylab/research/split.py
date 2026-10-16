"""Chronological train / validation / test split with embargo, purge and a test lock.

Segments on the receive clock (session [start, end], length D):
  train       [start, start + 0.6 D)
  validation  [start + 0.6 D + embargo, start + 0.8 D)
  test        [start + 0.8 D + embargo, end]
Rows in an embargo belong to no segment and are dropped.
  purge      a label of horizon h at row t is NaN when t + h + max_delay > its segment's end
  lookback   a feature with lookback L at row t is NaN when t - L < the previous segment's end
So no training label window overlaps a validation feature window, and likewise for test.

Test lock: test rows are written only to locked/test.jsonl.gz. `load_segment` refuses "test".
Only `LockedTestVault.open_once` (used by research-final) reads it, and only once per run, after the
validation stage is complete and with unchanged preregistration/config hashes. The access is
recorded in the manifest BEFORE the file is read.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from moneylab.research.features import NAN, REGISTRY
from moneylab.research.io import iter_jsonl_gz, write_jsonl_gz
from moneylab.research.manifest import now_iso, read_manifest, write_manifest
from moneylab.storage.atomic import sha256_file

TRAIN, VALIDATION, TEST = "train", "validation", "test"
SEGMENTS = (TRAIN, VALIDATION, TEST)
TRAINVAL_FILE = "grid_trainval.jsonl.gz"
LOCKED_DIR = "locked"
TEST_FILE = "test.jsonl.gz"


class InsufficientDataError(ValueError):
    """The session is too short for the pre-registered split."""


class SplitLockedError(PermissionError):
    """The test split was requested outside `research-final`, or a second time."""


@dataclass(frozen=True)
class SplitBoundaries:
    start: float
    end: float
    train_end: float
    validation_start: float
    validation_end: float
    test_start: float
    embargo_seconds: float

    def segment_of(self, t: float) -> str | None:
        if self.start <= t < self.train_end:
            return TRAIN
        if self.validation_start <= t < self.validation_end:
            return VALIDATION
        if self.test_start <= t <= self.end:
            return TEST
        return None

    def bounds(self, segment: str) -> tuple[float, float]:
        return {TRAIN: (self.start, self.train_end), VALIDATION: (self.validation_start, self.validation_end),
                TEST: (self.test_start, self.end)}[segment]

    def previous_end(self, segment: str) -> float | None:
        return {TRAIN: None, VALIDATION: self.train_end, TEST: self.validation_end}[segment]

    def to_dict(self) -> dict[str, float]:
        return dict(self.__dict__)


def compute_boundaries(start: float, end: float, train: float, validation: float,
                       embargo_seconds: float) -> SplitBoundaries:
    d = end - start
    b = SplitBoundaries(start=start, end=end, train_end=start + train * d,
                        validation_start=start + train * d + embargo_seconds,
                        validation_end=start + (train + validation) * d,
                        test_start=start + (train + validation) * d + embargo_seconds,
                        embargo_seconds=embargo_seconds)
    if d <= 0 or b.validation_start >= b.validation_end or b.test_start >= b.end:
        raise InsufficientDataError(
            f"session of {d:.0f}s is too short for a {train:.0%}/{validation:.0%} split with "
            f"{embargo_seconds:.0f}s embargo (validation or test would be empty)")
    return b


def split_rows(times: list[float], cols: dict[str, list[float]], label_horizons: dict[str, int],
               boundaries: SplitBoundaries, max_delay_seconds: float,
               extra: dict[str, list[Any]] | None = None) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Rows with `segment`; features beyond their segment and purged labels set to NaN.

    `cols` holds features (names in the registry) and labels; `label_horizons` maps every label
    column to its horizon in seconds. Returns (rows, counts).
    """
    counts = {"embargo_rows": 0, "feature_values_cut_at_segment_start": 0, "label_values_purged": 0}
    rows = []
    for k, t in enumerate(times):
        seg = boundaries.segment_of(t)
        if seg is None:
            counts["embargo_rows"] += 1
            continue
        lo, hi = boundaries.bounds(seg)
        prev_end = boundaries.previous_end(seg)
        row: dict[str, Any] = {"t": t, "segment": seg}
        for name, col in cols.items():
            v = col[k]
            if name in label_horizons:
                if t + label_horizons[name] + max_delay_seconds > hi and v == v:
                    v = NAN
                    counts["label_values_purged"] += 1
            elif name in REGISTRY and prev_end is not None and t - REGISTRY[name].lookback_seconds < prev_end:
                if v == v:
                    counts["feature_values_cut_at_segment_start"] += 1
                v = NAN
            row[name] = v
        for name, col in (extra or {}).items():
            row[name] = col[k]
        rows.append(row)
    return rows, counts


def write_split(run_dir: Path, header: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """train+validation -> grid_trainval.jsonl.gz, test -> locked/test.jsonl.gz. Returns hashes and counts."""
    run_dir = Path(run_dir)
    tv = [r for r in rows if r["segment"] in (TRAIN, VALIDATION)]
    test = [r for r in rows if r["segment"] == TEST]
    tv_hash = write_jsonl_gz(run_dir / TRAINVAL_FILE, header, tv)
    test_hash = write_jsonl_gz(run_dir / LOCKED_DIR / TEST_FILE, header, test)
    counts = {s: sum(1 for r in rows if r["segment"] == s) for s in SEGMENTS}
    return {"trainval_file": TRAINVAL_FILE, "trainval_sha256": tv_hash,
            "test_file": f"{LOCKED_DIR}/{TEST_FILE}", "test_sha256": test_hash, "rows": counts}


def load_segment(run_dir: Path, segment: str) -> list[dict[str, Any]]:
    """Train or validation rows (hash-checked). The test split is never served here."""
    if segment not in (TRAIN, VALIDATION):
        raise SplitLockedError(f"segment {segment!r} is locked; only `research-final` opens the test split")
    run_dir = Path(run_dir)
    manifest = read_manifest(run_dir)
    path = run_dir / TRAINVAL_FILE
    if sha256_file(path) != manifest["outputs"]["trainval_sha256"]:
        raise ValueError(f"{path} does not match the manifest hash (modified after research-build)")
    _, rows = iter_jsonl_gz(path)
    return [r for r in rows if r["segment"] == segment]


class LockedTestVault:
    """The only reader of the test split. One use per run."""

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)

    def open_once(self, *, config_sha256: str, preregistration_sha256: str) -> list[dict[str, Any]]:
        m = read_manifest(self.run_dir)
        if m.get("test_access_count", 0) != 0:
            raise SplitLockedError(f"test split of {self.run_dir.name} was already opened "
                                  f"({m.get('test_access_count')}x at {m.get('test_accessed_at')}); it is single-use")
        if not (m.get("validation") or {}).get("completed"):
            raise SplitLockedError("validation stage not completed (run research-stats first)")
        if m.get("kind") == "DRY_RUN":
            raise SplitLockedError("dry runs never open the test split")
        if m.get("config_overrides"):
            raise SplitLockedError(f"run was built with config overrides {m['config_overrides']}; not a registered run")
        if m.get("config_sha256") != config_sha256 or m.get("preregistration_sha256") != preregistration_sha256:
            raise SplitLockedError("preregistration/config hash differs from the one this run was built with")
        m["test_access_count"] = 1
        m["test_accessed_at"] = now_iso()
        write_manifest(self.run_dir, m)  # recorded before reading: a crash still counts as the one use
        path = self.run_dir / LOCKED_DIR / TEST_FILE
        if sha256_file(path) != m["outputs"]["test_sha256"]:
            raise ValueError(f"{path} does not match the manifest hash")
        _, rows = iter_jsonl_gz(path)
        return [r for r in rows if r["segment"] == TEST]
