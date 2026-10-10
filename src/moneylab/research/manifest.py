"""Run manifest: everything needed to know what a research run was built from.

data/processed/research/<run_id>/manifest.json holds the dataset/raw/preregistration/config
hashes, git commit, session, provenance and evidence label, feature registry, horizons, split
boundaries, exclusion counts, cost scenarios, the hashes of the output files, the validation
status and the test access count. It is rewritten atomically at every stage.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.research.config import ROOT
from moneylab.storage.atomic import atomic_write_json

SCHEMA_MANIFEST = "moneylab.research.manifest/1"
MANIFEST_FILE = "manifest.json"

# Evidence labels (decision caps in leaderboard.py)
EVIDENCE = "EVIDENCE"
NOT_EVIDENCE = "NOT_EVIDENCE"  # provenance != real
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"  # session shorter than the pre-registered nominal length
DRY_RUN = "DRY_RUN/INSUFFICIENT_EVIDENCE"  # pipeline check, never a research result


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def git_state(root: Path = ROOT) -> dict[str, Any]:
    """Commit hash and whether the working tree had uncommitted changes (local git only)."""
    def run(*args: str) -> str | None:
        try:
            out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    return {"commit": commit, "dirty": None if status is None else bool(status)}


def evidence_label(provenance: str, duration_seconds: float, nominal_seconds: float, dry_run: bool) -> str:
    if provenance != "real":
        return NOT_EVIDENCE
    if dry_run:
        return DRY_RUN
    if duration_seconds < 0.9 * nominal_seconds:
        return INSUFFICIENT
    return EVIDENCE


def manifest_path(run_dir: Path) -> Path:
    return Path(run_dir) / MANIFEST_FILE


def read_manifest(run_dir: Path) -> dict[str, Any]:
    return json.loads(manifest_path(run_dir).read_text(encoding="utf-8"))


def write_manifest(run_dir: Path, manifest: dict[str, Any]) -> Path:
    manifest = {**manifest, "schema": SCHEMA_MANIFEST, "updated_at": now_iso()}
    return atomic_write_json(manifest_path(run_dir), manifest)
