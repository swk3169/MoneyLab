"""Deterministic loader for `knowledge/records/**`.

Only the record tree is read. Every file there must be a `.json` record; anything that cannot be decoded or parsed
is surfaced as a load issue instead of being skipped. Duplicate JSON keys are an error (strict parsing)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from moneylab.knowledge.model import RECORDS_DIR, Record


@dataclass(frozen=True)
class LoadIssue:
    path: str
    message: str


@dataclass(frozen=True)
class LoadResult:
    records: tuple[Record, ...]
    issues: tuple[LoadIssue, ...]


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate key {key!r}")
        obj[key] = value
    return obj


def load_records(root: Path) -> LoadResult:
    """All files under `<root>/knowledge/records`, in path order."""
    base = Path(root) / RECORDS_DIR
    records: list[Record] = []
    issues: list[LoadIssue] = []
    files = sorted((p for p in base.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix()) \
        if base.is_dir() else []
    for file in files:
        rel = file.relative_to(root).as_posix()
        if file.suffix != ".json":
            issues.append(LoadIssue(rel, "not a .json record file"))
            continue
        try:
            text = file.read_bytes().decode("utf-8").replace("\r\n", "\n")
            data = json.loads(text, object_pairs_hook=_strict_object)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            issues.append(LoadIssue(rel, f"cannot read or parse JSON: {type(exc).__name__}: {exc}"))
            continue
        if not isinstance(data, dict):
            issues.append(LoadIssue(rel, "a record must be a JSON object"))
            continue
        records.append(Record(rel, text, data))
    return LoadResult(tuple(records), tuple(issues))
