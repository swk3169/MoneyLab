"""Deterministic upper-bound input segments (BT-3c; docs/backtest_design.md section 4). Files only.

A segment is the part of two verified bar directories (daily, hourly) that a run may see:
  validated source (backtest.bars_io.load_bars: hashes, rows, duplicates, real refused)
  -> canonical Bar objects with bar.end_utc <= cut_end_utc, cut_end_utc = last_day + 3 days (the run's G_end)
  -> canonical rows (domain.bars.canonical_bar_rows) and bars_sha256
There is no lower bound: every bar before the cut is kept (lookback and warm-up are unchanged). The whole
source is parsed and checked before anything is cut, so a broken row after the cut still refuses the export.

Layout of <out_root>/<segment_id>/ (out_root must end with "-fixture" for fixture/synthetic bars):
  segment_manifest.json      moneylab.backtest.segment/1
  SHA256SUMS.txt             the 7 files below and segment_manifest.json, "<sha256>  <relative/path>", sorted
  <source day dir name>/     a bars/1 directory (bars_day.jsonl, bars_manifest.json, SHA256SUMS.txt)
  <source hour dir name>/    a bars/1 directory (bars_hour.jsonl, bars_manifest.json, SHA256SUMS.txt)
The child directories keep the source directory names, so a run on the segment has the same provenance
description as a run on the source; load_bars reads them unchanged.

Identity (computed in this order, nothing refers to itself):
  identity payload: what the segment holds (schema, market, provenance, cut, rule, per interval: dir name,
  bars file, segment hash, segment row count, first / last start; no source lineage, no paths, no times)
  -> segment_content_sha256 = SHA-256 of the canonical JSON of the payload (storage.atomic.sha256_of)
  -> segment_id = segment_<market>_cut<YYYYMMDDTHHMMZ>_<content sha[:12]>
  -> segment_manifest.json = payload + per-interval source lineage (source bar hash, source manifest hash, source
     row count) + evidence + segment_content_sha256 + segment_id + source_locator
  -> segment_manifest_sha256 = SHA-256 of the manifest bytes
Source lineage and source_locator (absolute source directories) are manifest metadata only. Valid bars appended
to a source after the cut change the lineage and the manifest hash but not the content hash, the id or the rows;
the same source copied to another path changes only the locator and the manifest hash.
All segments of fixture or synthetic bars are SYNTHETIC / NOT_EVIDENCE.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from moneylab.backtest.bars_io import MANIFEST_FILE as BARS_MANIFEST_FILE
from moneylab.backtest.bars_io import SCHEMA as BARS_SCHEMA
from moneylab.backtest.bars_io import SUMS_FILE, load_bars
from moneylab.backtest.data import BarSeries
from moneylab.domain.bars import NOT_EVIDENCE, Bar, bars_sha256, canonical_bar_rows, require_utc, utc_iso
from moneylab.storage.atomic import atomic_write_bytes, sha256_file, sha256_of

SEGMENT_SCHEMA = "moneylab.backtest.segment/1"
SEGMENT_MANIFEST = "segment_manifest.json"
RULE = "bar.end_utc <= cut_end_utc"
FIXTURE_ROOT_SUFFIX = "-fixture"
INTERVALS = ("day", "hour")
PAYLOAD_INTERVAL_KEYS = ("dir_name", "bars_file", "segment_bars_sha256", "segment_bars", "first_start", "last_start")
LINEAGE_INTERVAL_KEYS = ("source_bars_sha256", "source_bars_manifest_sha256", "source_bars")  # manifest only
CREATED, ALREADY_EXISTS_IDENTICAL = "CREATED", "ALREADY_EXISTS_IDENTICAL"


class SegmentError(ValueError):
    """The segment cannot be made, read or trusted."""


class SourceUnavailable(SegmentError):
    """A segment's source directory cannot be found at its locator (not a corruption)."""


def cut_for(last_day: datetime) -> datetime:
    """cut_end_utc = last_day + 3 days, the G_end of every run with this last_day."""
    require_utc(last_day, "last_day")
    if last_day.hour or last_day.minute or last_day.second or last_day.microsecond:
        raise SegmentError("last_day must be 00:00 UTC")
    return last_day + timedelta(days=3)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest_bytes(doc: dict[str, Any]) -> bytes:
    return (json.dumps(doc, sort_keys=True, indent=1) + "\n").encode("utf-8")


def _sums(entries: dict[str, bytes]) -> bytes:
    return "".join(f"{_sha(data)}  {name}\n" for name, data in sorted(entries.items(), key=lambda kv: kv[0].encode()))


def _bars_file(interval: str) -> str:
    return f"bars_{interval}.jsonl"


def content_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    """The identity payload carried inside a segment manifest (the keys that define the content)."""
    return {"schema": manifest["schema"], "market": manifest["market"], "provenance": manifest["provenance"],
            "cut_end_utc": manifest["cut_end_utc"], "rule": manifest["rule"],
            "intervals": {iv: {k: manifest["intervals"][iv][k] for k in PAYLOAD_INTERVAL_KEYS} for iv in INTERVALS}}


def segment_id_for(market: str, cut: datetime, content_sha256: str) -> str:
    return f"segment_{market}_cut{cut.strftime('%Y%m%dT%H%MZ')}_{content_sha256[:12]}"


def select(series: BarSeries, cut: datetime) -> list[Bar]:
    return [b for b in series.bars if b.end_utc <= cut]


@dataclass(frozen=True)
class SegmentPlan:
    segment_id: str
    content_sha256: str
    manifest_sha256: str
    manifest: dict[str, Any]
    files: dict[str, bytes]  # relative path -> exact bytes, including the top-level SHA256SUMS.txt
    provenance: str


def plan_segment(daily_dir: Path, hourly_dir: Path, last_day: datetime) -> SegmentPlan:
    """Every byte of the segment, computed in memory (nothing is written)."""
    cut = cut_for(last_day)
    dirs = {"day": Path(daily_dir), "hour": Path(hourly_dir)}
    series = {iv: load_bars(d) for iv, d in dirs.items()}  # the whole source is validated first
    for iv, s in series.items():
        if s.interval != iv:
            raise SegmentError(f"{dirs[iv]} holds {s.interval} bars, expected {iv}")
    if series["day"].market != series["hour"].market:
        raise SegmentError("daily and hourly sources are of different markets")
    kind = series["day"].provenance.kind
    if series["hour"].provenance.kind != kind:
        raise SegmentError("daily and hourly sources have different provenance kinds")
    if dirs["day"].name == dirs["hour"].name:
        raise SegmentError("daily and hourly source directories must have different names")
    market = series["day"].market

    files: dict[str, bytes] = {}
    intervals: dict[str, dict[str, Any]] = {}
    for iv in INTERVALS:
        src_manifest_bytes = (dirs[iv] / BARS_MANIFEST_FILE).read_bytes()
        src_manifest = json.loads(src_manifest_bytes.decode("utf-8"))
        bars = select(series[iv], cut)
        if not bars:
            raise SegmentError(f"no {iv} bar ends at or before the cut {utc_iso(cut)}")
        body = canonical_bar_rows(bars)
        seg_sha = bars_sha256(bars)
        if _sha(body) != seg_sha:
            raise SegmentError("canonical rows do not hash to the bar content hash")
        bars_file = _bars_file(iv)
        child = {
            "schema": BARS_SCHEMA, "evidence": src_manifest.get("evidence", NOT_EVIDENCE), "provenance": kind,
            "market": market, "interval": iv, "bars": len(bars), "first_start": utc_iso(bars[0].start_utc),
            "last_start": utc_iso(bars[-1].start_utc), "bars_file": bars_file, "bars_sha256": seg_sha,
        }
        for key in ("source_pull", "confirmation_rule"):  # copied as is; candle_report describes the whole pull
            if key in src_manifest:
                child[key] = src_manifest[key]
        child_bytes = _manifest_bytes(child)
        name = dirs[iv].name
        files[f"{name}/{bars_file}"] = body
        files[f"{name}/{BARS_MANIFEST_FILE}"] = child_bytes
        files[f"{name}/{SUMS_FILE}"] = _sums({bars_file: body, BARS_MANIFEST_FILE: child_bytes}).encode("utf-8")
        intervals[iv] = {"dir_name": name, "bars_file": bars_file,
                         "source_bars_sha256": series[iv].provenance.bars_sha256,
                         "source_bars_manifest_sha256": _sha(src_manifest_bytes), "source_bars": len(series[iv]),
                         "segment_bars_sha256": seg_sha, "segment_bars": len(bars),
                         "first_start": child["first_start"], "last_start": child["last_start"]}

    payload = {"schema": SEGMENT_SCHEMA, "market": market, "provenance": kind, "cut_end_utc": utc_iso(cut),
               "rule": RULE,
               "intervals": {iv: {k: intervals[iv][k] for k in PAYLOAD_INTERVAL_KEYS} for iv in INTERVALS}}
    content_sha = sha256_of(payload)
    seg_id = segment_id_for(market, cut, content_sha)
    manifest = {**payload, "intervals": intervals,  # content keys plus the source lineage of each interval
                "evidence": NOT_EVIDENCE, "segment_content_sha256": content_sha, "segment_id": seg_id,
                "source_locator": {iv: str(dirs[iv].resolve()) for iv in INTERVALS}}
    manifest_bytes = _manifest_bytes(manifest)
    files[SEGMENT_MANIFEST] = manifest_bytes
    files[SUMS_FILE] = _sums(dict(files)).encode("utf-8")
    return SegmentPlan(seg_id, content_sha, _sha(manifest_bytes), manifest, files, kind)


@dataclass(frozen=True)
class SegmentExport:
    dir: Path
    status: str  # CREATED or ALREADY_EXISTS_IDENTICAL
    plan: SegmentPlan


def _tree(root: Path) -> dict[str, Path]:
    return {p.relative_to(root).as_posix(): p for p in root.rglob("*") if p.is_file()}


def export_segment(daily_dir: Path, hourly_dir: Path, last_day: datetime, out_root: Path) -> SegmentExport:
    """Write the segment to <out_root>/<segment_id>/ (temporary directory, then one rename). An existing
    directory is accepted only when it holds exactly the expected files with identical bytes; it is never
    overwritten. Sources and existing directories are only read."""
    out_root = Path(out_root)
    plan = plan_segment(daily_dir, hourly_dir, last_day)
    if plan.provenance in ("fixture", "synthetic") and not out_root.name.endswith(FIXTURE_ROOT_SUFFIX):
        raise SegmentError(f"fixture/synthetic segments must go under a '*{FIXTURE_ROOT_SUFFIX}' root, not {out_root}")
    final = out_root / plan.segment_id
    if final.exists():
        tree = _tree(final)
        if set(tree) == set(plan.files) and all(tree[n].read_bytes() == data for n, data in plan.files.items()):
            return SegmentExport(final, ALREADY_EXISTS_IDENTICAL, plan)
        raise SegmentError(f"{final} exists with different content (same segment id; source_locator or files "
                           "differ); refusing to overwrite")
    out_root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-seg-", dir=out_root))
    written: list[Path] = []
    made: list[Path] = []
    try:
        for name, data in plan.files.items():
            path = tmp / name
            if not path.parent.exists():
                path.parent.mkdir()
                made.append(path.parent)
            atomic_write_bytes(path, data)
            written.append(path)
        for name, data in plan.files.items():
            if sha256_file(tmp / name) != _sha(data):
                raise SegmentError(f"written {name} does not match its planned bytes")
        os.rename(tmp, final)  # never overwrites
    except BaseException:
        for p in written:
            p.unlink(missing_ok=True)
        for d in reversed(made):
            try:
                d.rmdir()
            except OSError:
                pass
        try:
            tmp.rmdir()
        except OSError:
            pass
        raise
    return SegmentExport(final, CREATED, plan)


@dataclass(frozen=True)
class SegmentInfo:
    dir: Path
    manifest: dict[str, Any]
    segment_id: str
    content_sha256: str
    manifest_sha256: str
    cut_end_utc: datetime
    series: dict[str, BarSeries]


def _utc(text: Any) -> datetime:
    t = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    return require_utc(t, "time")


def read_segment(segment_dir: Path) -> SegmentInfo:
    """Check a segment directory on its own files: exact file set, top-level SHA256SUMS, schema, child bars/1
    directories (load_bars), every row at or before the cut, payload values = the files, content hash and id."""
    segment_dir = Path(segment_dir)
    try:
        manifest_bytes = (segment_dir / SEGMENT_MANIFEST).read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        sums: dict[str, str] = {}
        for line in (segment_dir / SUMS_FILE).read_text(encoding="utf-8").splitlines():
            digest, sep, name = line.partition("  ")
            if not sep or len(digest) != 64 or name in sums:
                raise SegmentError(f"malformed line in {SUMS_FILE}: {line!r}")
            sums[name] = digest
    except (OSError, ValueError) as exc:
        raise SegmentError(f"{segment_dir}: cannot read the segment manifest or {SUMS_FILE}: {exc}") from exc
    if manifest.get("schema") != SEGMENT_SCHEMA:
        raise SegmentError(f"{segment_dir}: not a {SEGMENT_SCHEMA} directory")
    try:
        names = {iv: manifest["intervals"][iv]["dir_name"] for iv in INTERVALS}
        files = {iv: manifest["intervals"][iv]["bars_file"] for iv in INTERVALS}
        cut = _utc(manifest["cut_end_utc"])
        payload = content_payload(manifest)
        missing = [f"{iv}.{k}" for iv in INTERVALS for k in LINEAGE_INTERVAL_KEYS if k not in manifest["intervals"][iv]]
        if missing:
            raise KeyError(f"source lineage {missing}")
    except (KeyError, TypeError, ValueError) as exc:
        raise SegmentError(f"{segment_dir}: incomplete segment manifest: {exc}") from exc
    expected = {SEGMENT_MANIFEST} | {f"{names[iv]}/{n}" for iv in INTERVALS
                                     for n in (files[iv], BARS_MANIFEST_FILE, SUMS_FILE)}
    if set(sums) != expected or len(sums) != 7:
        raise SegmentError(f"{segment_dir}: {SUMS_FILE} must list exactly {sorted(expected)}")
    if set(_tree(segment_dir)) != expected | {SUMS_FILE}:
        raise SegmentError(f"{segment_dir}: the directory holds missing or extra files")
    bad = [n for n in sorted(expected) if sha256_file(segment_dir / n) != sums[n]]
    if bad:
        raise SegmentError(f"{segment_dir}: hash mismatch: {bad}")
    if payload["rule"] != RULE or manifest.get("evidence") != NOT_EVIDENCE:
        raise SegmentError(f"{segment_dir}: unexpected rule or evidence label")

    series: dict[str, BarSeries] = {}
    for iv in INTERVALS:
        try:
            s = load_bars(segment_dir / names[iv])
        except ValueError as exc:
            raise SegmentError(f"{segment_dir}: {iv} child is not a valid bar directory: {exc}") from exc
        rec = payload["intervals"][iv]
        late = [b for b in s.bars if b.end_utc > cut]
        if late:
            raise SegmentError(f"{segment_dir}: {len(late)} {iv} bars end after the cut")
        if s.interval != iv or s.market != payload["market"] or s.provenance.kind != payload["provenance"]:
            raise SegmentError(f"{segment_dir}: {iv} child does not match the manifest market / interval / kind")
        if (s.provenance.bars_sha256, len(s), utc_iso(s.bars[0].start_utc), utc_iso(s.bars[-1].start_utc)) != \
                (rec["segment_bars_sha256"], rec["segment_bars"], rec["first_start"], rec["last_start"]):
            raise SegmentError(f"{segment_dir}: {iv} child does not match the manifest identity values")
        series[iv] = s
    content_sha = sha256_of(payload)
    if manifest.get("segment_content_sha256") != content_sha:
        raise SegmentError(f"{segment_dir}: segment_content_sha256 does not match the payload")
    if manifest.get("segment_id") != segment_id_for(payload["market"], cut, content_sha) or \
            segment_dir.name != manifest["segment_id"]:
        raise SegmentError(f"{segment_dir}: segment_id does not follow the content hash or the directory name")
    return SegmentInfo(segment_dir, manifest, manifest["segment_id"], content_sha, _sha(manifest_bytes), cut, series)


def verify_derivation(info: SegmentInfo) -> str:
    """Re-derive the segment from the sources at source_locator. SourceUnavailable when a source directory is
    missing (no search elsewhere); SegmentError when a source exists but does not give this segment."""
    locator = info.manifest.get("source_locator") or {}
    for iv in INTERVALS:
        if not locator.get(iv) or not Path(locator[iv]).is_dir():
            raise SourceUnavailable(f"{iv} source not found at its locator {locator.get(iv)!r}")
    for iv in INTERVALS:
        src = Path(locator[iv])
        rec = info.manifest["intervals"][iv]
        try:
            s = load_bars(src)
            manifest_sha = sha256_file(src / BARS_MANIFEST_FILE)
        except (OSError, ValueError) as exc:
            raise SegmentError(f"{iv} source at {src} does not load: {exc}") from exc
        if (s.provenance.bars_sha256, manifest_sha, len(s)) != \
                (rec["source_bars_sha256"], rec["source_bars_manifest_sha256"], rec["source_bars"]):
            raise SegmentError(f"{iv} source at {src} differs from the one the segment was cut from")
        if bars_sha256(select(s, info.cut_end_utc)) != rec["segment_bars_sha256"]:
            raise SegmentError(f"{iv} source at {src} cut at {utc_iso(info.cut_end_utc)} does not give the segment")
    return "source -> segment derivation re-verified"
