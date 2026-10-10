"""Processed research files: gzip JSON lines (header line + one object per line).

Parquet would need pyarrow (not a dependency yet), so processed data is gzip JSONL: stdlib only,
streamable, deterministic bytes (gzip mtime = 0). NaN is stored as null and read back as NaN.
"""

from __future__ import annotations

import gzip
import json
import math
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from moneylab.domain.market_events import MarketEvent
from moneylab.storage.atomic import atomic_open, sha256_file

NAN = float("nan")


def _clean(v: Any) -> Any:
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def write_jsonl_gz(path: Path, header: dict[str, Any], rows: Iterable[dict[str, Any]]) -> str:
    """Atomic write; returns the file's sha256."""
    path = Path(path)
    with atomic_open(path) as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        gz.write((json.dumps({"header": header}, separators=(",", ":"), default=str) + "\n").encode())
        for row in rows:
            gz.write((json.dumps({k: _clean(v) for k, v in row.items()}, separators=(",", ":")) + "\n").encode())
    return sha256_file(path)


def iter_jsonl_gz(path: Path) -> tuple[dict[str, Any], Iterator[dict[str, Any]]]:
    f = gzip.open(Path(path), "rt", encoding="utf-8")
    first = json.loads(f.readline())
    if "header" not in first:
        f.close()
        raise ValueError(f"{path}: missing header line")

    def rows() -> Iterator[dict[str, Any]]:
        with f:
            for line in f:
                if line.strip():
                    yield json.loads(line)
    return first["header"], rows()


def read_events(path: Path) -> tuple[dict[str, Any], Iterator[MarketEvent]]:
    header, rows = iter_jsonl_gz(path)
    return header, (MarketEvent.from_dict(r) for r in rows)


def num(v: Any) -> float:
    return NAN if v is None else float(v)
