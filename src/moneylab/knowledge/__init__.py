"""MoneyLab knowledge layer, Phase 1 (KNOWLEDGE-WIKI-01).

Git-tracked immutable JSON records under `knowledge/records/` are the only authoritative knowledge. This package
loads, validates and queries them deterministically with the standard library only (plus read-only `git` for source
checks). It has no write API: new records are proposed and accepted only through the governed Git workflow."""

from __future__ import annotations

from pathlib import Path

from moneylab.knowledge.context import ContextRequestError, resolve_context
from moneylab.knowledge.load import LoadResult, load_records
from moneylab.knowledge.model import SCHEMA, Record
from moneylab.knowledge.query import KnowledgeBase
from moneylab.knowledge.validate import Problem, Report, validate

REPO_ROOT = Path(__file__).resolve().parents[3]

__all__ = ["REPO_ROOT", "SCHEMA", "ContextRequestError", "KnowledgeBase", "LoadResult", "Problem", "Record", "Report",
           "load_records", "open_knowledge_base", "resolve_context", "validate"]


def open_knowledge_base(root: Path = REPO_ROOT, *, use_git: bool = True,
                        full_history: bool = False) -> tuple[KnowledgeBase, Report]:
    """Load, validate and index the records of one repository."""
    loaded = load_records(root)
    report = validate(loaded, root, use_git=use_git, full_history=full_history)
    return KnowledgeBase(loaded, report), report
