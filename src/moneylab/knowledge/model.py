"""Knowledge record model (`moneylab.knowledge.record/1`): constants, ID rules and canonical JSON.

The vocabulary below is the frozen Phase-1 contract (docs/tasks/KNOWLEDGE-WIKI-01/WORK_ORDER.md). The separate axes
(epistemic layer, evidence grade/availability, claim axis and data basis, task/decision/question state) are kept in
separate fields on purpose; there is no value for profitability, alpha or live readiness."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

SCHEMA = "moneylab.knowledge.record/1"
RECORDS_DIR = "knowledge/records"

KINDS = ("claim", "decision", "question", "task")
LAYER_RANK = {"SOURCE_FACT": 3, "DERIVED_SUMMARY": 2, "HYPOTHESIS": 1}
LAYERS = tuple(sorted(LAYER_RANK))
TOPICS = ("futility-calibration", "mc-v06", "portfolio-demo")

PROVENANCE_CLASSES = ("CLAUDE_REPORTED", "GIT_VERIFIABLE", "INDEPENDENT")
AVAILABILITY = ("EXTERNAL_LOCAL", "GITHUB", "IN_GIT", "MISSING")
EVIDENCE_FIELDS = {  # type -> (required fields, optional fields)
    "git_blob": (("availability", "path", "provenance_class", "rev", "sha256", "type"), ("locator",)),
    "github": (("availability", "locator", "provenance_class", "type"), ()),
    "external": (("availability", "locator", "provenance_class", "sha256", "type"), ()),
}
EVIDENCE_AVAILABILITY = {"git_blob": ("IN_GIT",), "github": ("GITHUB",), "external": ("EXTERNAL_LOCAL", "MISSING")}

ENVELOPE_FIELDS = ("derived_from", "evidence", "id", "kind", "labels", "layer", "payload", "schema", "statement",
                   "supersedes", "title", "topics")
PAYLOAD_FIELDS = {
    "task": ("implementation_commit", "merge_commit", "outcome", "task_id", "tree"),
    "claim": ("axis", "data_basis"),
    "decision": ("local_id", "state"),
    "question": ("state",),
}
PAYLOAD_ENUMS = {
    ("task", "outcome"): ("MERGED_TO_MAIN",),
    ("claim", "axis"): ("ENGINEERING", "LITERATURE", "MATURITY", "SCIENTIFIC", "WORKFLOW"),
    ("claim", "data_basis"): ("FIXTURE", "NOT_APPLICABLE", "REAL", "SYNTHETIC"),
    ("decision", "state"): ("DECIDED", "PENDING"),
    ("question", "state"): ("ANSWERED", "OPEN", "WITHDRAWN"),
}

ID_RE = re.compile(r"^(task|claim|decision|question)/([A-Z0-9][A-Z0-9-]{0,47})/([a-z0-9][a-z0-9-]{0,63})$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GITHUB_LOCATOR_RE = re.compile(r"^github:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(pull|actions/runs)/[0-9]+$")
EXTERNAL_LOCATOR_RE = re.compile(r"^external:[a-z0-9][a-z0-9-]*/[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$")

CONTEXT_MODES = ("EVIDENCE", "IDEATION")
CONTEXT_BOUNDARY = "DATA_NOT_INSTRUCTIONS"


@dataclass(frozen=True)
class Record:
    """One loaded record file: its repository-relative path, raw text (CRLF read as LF) and parsed object."""

    path: str
    text: str
    data: dict[str, Any]

    @property
    def id(self) -> str:
        value = self.data.get("id")
        return value if isinstance(value, str) else self.path

    @property
    def kind(self) -> Any:
        return self.data.get("kind")

    @property
    def layer(self) -> Any:
        return self.data.get("layer")

    @property
    def namespace(self) -> str | None:
        m = ID_RE.match(self.id)
        return m.group(2) if m else None


def record_path(record_id: str) -> str:
    """Repository-relative path a record with this ID must live at."""
    return f"{RECORDS_DIR}/{record_id}.json"


def canonical_json(obj: Any) -> str:
    """The one accepted serialization of a record."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
