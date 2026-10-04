"""Crash-safe file writes.

A reader (or a restarted recorder) sees either the complete old file or the complete new
file, never a partial one: data goes to a temp file in the same directory, is fsync'ed, then
`os.replace`d over the target (atomic on the same volume on POSIX and Windows/NTFS).

A crash can leave `*.tmp` files behind; `cleanup_tmp` removes them on the next start.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

TMP_SUFFIX = ".tmp"
# Windows: os.replace fails with PermissionError while another process (indexer, antivirus)
# briefly holds the target open. Retry a few times before giving up.
_REPLACE_ATTEMPTS = 5
_REPLACE_DELAY = 0.05


def canonical_json(payload: Any) -> str:
    """Deterministic JSON used for hashing (sorted keys, no whitespace)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def sha256_of(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=TMP_SUFFIX)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        for attempt in range(_REPLACE_ATTEMPTS):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == _REPLACE_ATTEMPTS - 1:
                    raise
                time.sleep(_REPLACE_DELAY * (attempt + 1))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def atomic_write_text(path: Path, text: str) -> Path:
    return atomic_write_bytes(path, text.encode("utf-8"))


def atomic_write_json(path: Path, payload: Any, indent: int | None = 1) -> Path:
    return atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=indent, default=str))


def cleanup_tmp(directory: Path) -> list[Path]:
    """Delete leftover temp files (from an interrupted write) below `directory`."""
    removed = []
    directory = Path(directory)
    if not directory.exists():
        return removed
    for p in directory.rglob(f"*{TMP_SUFFIX}"):
        try:
            p.unlink()
            removed.append(p)
        except OSError as exc:
            log.warning("Could not remove leftover temp file %s: %s", p, exc)
    return removed
