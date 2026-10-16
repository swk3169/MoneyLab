"""Stored Upbit candle pull -> provider-neutral Bar files for the backtest (BT-2b-1).

Read-only on the pull, offline (no request is sent: the stored pages are replayed), fixture pulls
only until BT-5. Steps:
  1. `verify_candle_pull` must pass (page hashes, file set, replay = stored report)
  2. provenance must be allowed (default: fixture only; "real" is refused in BT-2b-1)
  3. the stored pages are replayed with the pull's own settings (`pull_candles` over
     `StoredPageClient`), which yields the closed candles exactly as the verify replay does
  4. Candle -> domain Bar (prices and amounts stay Decimal)
  5. files are written into a temporary directory next to the target, their hashes are checked,
     and only then is the directory renamed to <out_root>/<pull_id>/ (never overwritten). A failure
     leaves no final directory; the temporary files are removed by name.

Output (all SYNTHETIC / NOT_EVIDENCE for fixture pulls):
  bars_<interval>.jsonl   domain canonical rows; the file SHA-256 equals the bar content hash
  bars_manifest.json      source pull, page hashes, settings, candle quality report, bar count, hashes
  SHA256SUMS.txt          file hashes (LF, relative names)
Fixture output must go under a root whose name ends with "-fixture" (real and fixture paths never mix).
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from moneylab.core.exceptions import MoneyLabError
from moneylab.domain.bars import NOT_EVIDENCE, Bar, bars_sha256, canonical_bar_rows
from moneylab.providers.upbit.candle_store import PULL_FILE, SETTING_KEYS, StoredPageClient, verify_candle_pull
from moneylab.providers.upbit.candles import Candle, pull_candles
from moneylab.storage.atomic import atomic_write_bytes, sha256_file

SCHEMA = "moneylab.backtest.bars/1"
MANIFEST_FILE = "bars_manifest.json"
SUMS_FILE = "SHA256SUMS.txt"
FIXTURE_ROOT_SUFFIX = "-fixture"


class BarExportError(MoneyLabError):
    """The pull cannot be exported (failed verification, provenance, path or write problem)."""


@dataclass(frozen=True)
class BarsExport:
    dir: Path
    interval: str
    bars: int
    bars_sha256: str
    manifest: dict[str, Any]


def bars_file_name(interval: str) -> str:
    return f"bars_{interval}.jsonl"


def candle_to_bar(c: Candle) -> Bar:
    return Bar(c.market, c.interval, c.start_utc, c.open, c.high, c.low, c.close, c.acc_trade_price,
               c.acc_trade_volume, c.last_tick_ms)


def _utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def export_bars(pull_dir: Path, out_root: Path, *, allowed_provenance: tuple[str, ...] = ("fixture",)) -> BarsExport:
    pull_dir, out_root = Path(pull_dir), Path(out_root)
    if "real" in allowed_provenance:
        raise BarExportError("real pulls are not exported before BT-5")
    rep = verify_candle_pull(pull_dir)
    if not rep.ok:
        raise BarExportError(f"pull verification failed: {rep.problems}")
    doc = json.loads((pull_dir / PULL_FILE).read_text(encoding="utf-8"))
    provenance = doc.get("provenance")
    if provenance not in allowed_provenance:
        raise BarExportError(f"provenance {provenance!r} is not allowed (allowed: {allowed_provenance})")
    if provenance == "fixture" and not out_root.name.endswith(FIXTURE_ROOT_SUFFIX):
        raise BarExportError(f"fixture bars must go under a '*{FIXTURE_ROOT_SUFFIX}' root, not {out_root}")
    report = doc.get("report") or {}
    if not report.get("ok"):
        raise BarExportError("the pull's candle quality report is not ok (conflicting duplicates or invalid values)")
    final = out_root / doc["pull_id"]
    if final.exists():
        raise BarExportError(f"{final} already exists; refusing to overwrite")

    settings = doc["settings"]
    metas = [json.loads((pull_dir / "pages" / f"{p['index']:04d}.meta.json").read_text(encoding="utf-8"))
             for p in doc["pages"]]
    replay = pull_candles(StoredPageClient(pull_dir, metas), doc["market"], doc["interval"],
                          _utc(doc["requested_start"]), _utc(doc["requested_end"]),
                          **{k: settings[k] for k in SETTING_KEYS})
    if json.loads(json.dumps(replay.report.to_dict())) != report:
        raise BarExportError("the replayed candles differ from the stored report")
    bars = [candle_to_bar(c) for c in replay.candles]
    if not bars:
        raise BarExportError("the pull holds no closed candles")
    content_sha = bars_sha256(bars)
    body = canonical_bar_rows(bars)
    interval = doc["interval"]
    manifest = {
        "schema": SCHEMA, "evidence": NOT_EVIDENCE, "provenance": provenance, "market": doc["market"],
        "interval": interval, "bars": len(bars), "first_start": bars[0].to_record()["start_utc"],
        "last_start": bars[-1].to_record()["start_utc"], "bars_file": bars_file_name(interval),
        "bars_sha256": content_sha, "source_pull": {
            "pull_id": doc["pull_id"], "dir_name": pull_dir.name, "origin": doc.get("origin"),
            "requested_start": doc["requested_start"], "requested_end": doc["requested_end"],
            "settings": settings, "pages": [{"index": p["index"], "sha256": p["sha256"]} for p in doc["pages"]]},
        "confirmation_rule": f"bucket end + {settings['settle_seconds']} s <= page reference time "
                             "(earlier of local receive time and server Date)",
        "candle_report": report,
    }

    out_root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-bars-", dir=out_root))
    written: list[Path] = []
    try:
        bars_path = tmp / bars_file_name(interval)
        atomic_write_bytes(bars_path, body)
        written.append(bars_path)
        man_path = tmp / MANIFEST_FILE
        atomic_write_bytes(man_path, (json.dumps(manifest, sort_keys=True, indent=1) + "\n").encode("utf-8"))
        written.append(man_path)
        if sha256_file(bars_path) != content_sha:
            raise BarExportError("written bar file does not hash to the bar content hash")
        sums = "".join(f"{sha256_file(p)}  {p.name}\n" for p in sorted(written, key=lambda q: q.name))
        sums_path = tmp / SUMS_FILE
        atomic_write_bytes(sums_path, sums.encode("utf-8"))
        written.append(sums_path)
        os.rename(tmp, final)  # fails if the target appeared meanwhile; never overwrites
    except BaseException:
        for p in written:
            p.unlink(missing_ok=True)
        try:
            tmp.rmdir()
        except OSError:
            pass  # an unexpected leftover keeps the hidden temp dir; the final path was never created
        raise
    return BarsExport(final, interval, len(bars), content_sha, manifest)
