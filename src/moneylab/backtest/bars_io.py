"""Read exported Bar files into a BarSeries (BT-2b-1). Files only: no provider, no network.

A bar directory (written by providers/upbit/bar_export.py) holds bars_<interval>.jsonl,
bars_manifest.json and SHA256SUMS.txt. `load_bars` refuses the directory unless
  * SHA256SUMS.txt lists exactly the other two files and every file hash matches   (file bytes)
  * the manifest's bars_sha256 equals the bar file's byte hash                     (file bytes)
  * the bars rebuilt from the rows hash to the same value                          (bar content)
  * the provenance is not "real" (real data is refused until BT-5)
The byte hash and the content hash are compared separately: a file can only pass if its bytes are
exactly the canonical rows of the bars it contains.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from moneylab.backtest.data import BarSeries, DataIntegrityError
from moneylab.domain.bars import PROVENANCE_KINDS, Bar, BarProvenance, bars_sha256
from moneylab.storage.atomic import sha256_file

SCHEMA = "moneylab.backtest.bars/1"
MANIFEST_FILE = "bars_manifest.json"
SUMS_FILE = "SHA256SUMS.txt"
REFUSED_KINDS = ("real",)  # until BT-5


def _bar(row: dict[str, Any]) -> Bar:
    return Bar(row["market"], row["interval"], datetime.fromisoformat(row["start_utc"].replace("Z", "+00:00")),
               Decimal(row["open"]), Decimal(row["high"]), Decimal(row["low"]), Decimal(row["close"]),
               Decimal(row["value_krw"]), Decimal(row["volume"]), row.get("last_tick_ms"))


def _sums(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, sep, name = line.partition("  ")
        if not sep or len(digest) != 64 or not name or name in out:
            raise DataIntegrityError(f"malformed line in {path.name}: {line!r}")
        out[name] = digest
    return out


def load_bars(bars_dir: Path) -> BarSeries:
    bars_dir = Path(bars_dir)
    try:
        manifest = json.loads((bars_dir / MANIFEST_FILE).read_text(encoding="utf-8"))
        sums = _sums(bars_dir / SUMS_FILE)
    except (OSError, ValueError) as exc:
        raise DataIntegrityError(f"{bars_dir}: cannot read {MANIFEST_FILE} / {SUMS_FILE}: {exc}") from exc
    if manifest.get("schema") != SCHEMA:
        raise DataIntegrityError(f"{bars_dir}: not a {SCHEMA} directory")
    kind = manifest.get("provenance")
    if kind not in PROVENANCE_KINDS:
        raise DataIntegrityError(f"{bars_dir}: unknown provenance {kind!r}")
    if kind in REFUSED_KINDS:
        raise DataIntegrityError(f"{bars_dir}: provenance {kind!r} is refused before BT-5")
    bars_file = manifest.get("bars_file")
    if set(sums) != {bars_file, MANIFEST_FILE}:
        raise DataIntegrityError(f"{bars_dir}: {SUMS_FILE} must list exactly {bars_file} and {MANIFEST_FILE}")
    for name, digest in sums.items():
        try:
            actual = sha256_file(bars_dir / name)
        except OSError as exc:
            raise DataIntegrityError(f"{bars_dir}: cannot read {name}: {exc}") from exc
        if actual != digest:
            raise DataIntegrityError(f"{bars_dir}: {name} does not match {SUMS_FILE}")
    if sums[bars_file] != manifest.get("bars_sha256"):
        raise DataIntegrityError(f"{bars_dir}: bar file bytes do not hash to the manifest bars_sha256")
    try:
        rows = [json.loads(line) for line in (bars_dir / bars_file).read_text(encoding="utf-8").splitlines()]
        bars = [_bar(r) for r in rows]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DataIntegrityError(f"{bars_dir}: unreadable bar rows: {exc}") from exc
    if bars_sha256(bars) != manifest["bars_sha256"] or len(bars) != manifest.get("bars"):
        raise DataIntegrityError(f"{bars_dir}: bar content does not match the manifest")
    description = f"{manifest.get('source_pull', {}).get('pull_id')} via {bars_dir.name} ({manifest.get('evidence')})"
    return BarSeries.build(bars, BarProvenance(kind, description, manifest["bars_sha256"]))
