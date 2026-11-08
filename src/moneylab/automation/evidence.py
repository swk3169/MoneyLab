"""`moneylab.automation.evidence/1`: one canonical JSON string per run (AUTO-01, D6).

Only hashes of the captured bytes are reported, never the output itself, and nothing is written to disk. For
TIMEOUT and OUTPUT_LIMIT_EXCEEDED the hashes cover only the bytes kept within the limit, not the full process output.
An ALLOW document names the registered action ID; a DENIED document has action_id null and carries nothing derived
from the caller's input (ERRATA-001). Any inconsistent field raises EvidenceError instead of producing a document."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from moneylab.automation.policy import (
    ALLOW,
    ALLOWED_ACTIONS,
    DENIED,
    DENY,
    OUTPUT_LIMIT_EXCEEDED,
    SOURCE_UNVERIFIED,
    SUCCEEDED,
    TIMEOUT,
    UNEXPECTED_EXIT,
    VALIDATION_FAILED,
    AutomationError,
)

SCHEMA = "moneylab.automation.evidence/1"
FIELDS = ("action_id", "decision", "duration_ms", "exit_code", "schema", "status", "stderr_sha256", "stdout_sha256")
DECISIONS = (ALLOW, DENY)
STATUSES = (SUCCEEDED, VALIDATION_FAILED, SOURCE_UNVERIFIED, TIMEOUT, OUTPUT_LIMIT_EXCEEDED, UNEXPECTED_EXIT, DENIED)
NO_EXIT_CODE = (TIMEOUT, OUTPUT_LIMIT_EXCEEDED)
_SHA256 = re.compile(r"[0-9a-f]{64}")


class EvidenceError(AutomationError):
    """The evidence would be inconsistent; no document is produced."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _is_int(value: object) -> bool:
    return type(value) is int


def check(doc: dict[str, Any]) -> None:
    """Raise EvidenceError unless doc satisfies every D6 rule."""
    if sorted(doc) != list(FIELDS):
        raise EvidenceError(f"fields must be exactly {FIELDS}")
    if doc["schema"] != SCHEMA:
        raise EvidenceError("wrong schema")
    if doc["action_id"] is not None and type(doc["action_id"]) is not str:
        raise EvidenceError("action_id must be a string or null")
    if doc["decision"] not in DECISIONS or doc["status"] not in STATUSES:
        raise EvidenceError("decision or status outside its enum")
    if (doc["decision"] == DENY) != (doc["status"] == DENIED):
        raise EvidenceError("DENY and DENIED go together")
    measured = ("duration_ms", "stdout_sha256", "stderr_sha256")
    if doc["status"] == DENIED:
        if any(doc[k] is not None for k in ("action_id", "exit_code", *measured)):
            raise EvidenceError("DENIED evidence has null action_id, exit_code, duration_ms and hashes")
        return
    if type(doc["action_id"]) is not str or doc["action_id"] not in ALLOWED_ACTIONS:
        raise EvidenceError("an executed action has a registered action_id")
    if not _is_int(doc["duration_ms"]) or doc["duration_ms"] < 0:
        raise EvidenceError("duration_ms must be a non-negative int")
    for key in ("stdout_sha256", "stderr_sha256"):
        if type(doc[key]) is not str or not _SHA256.fullmatch(doc[key]):
            raise EvidenceError(f"{key} must be a lower-case SHA-256 hex digest")
    if doc["status"] in NO_EXIT_CODE:
        if doc["exit_code"] is not None:
            raise EvidenceError(f"{doc['status']} has a null exit_code")
    elif not _is_int(doc["exit_code"]):
        raise EvidenceError("a finished process has an int exit_code")


def denied() -> str:
    """Takes no argument on purpose: nothing the caller passed can reach a DENIED document."""
    doc = {"schema": SCHEMA, "action_id": None, "decision": DENY, "status": DENIED, "exit_code": None,
           "duration_ms": None, "stdout_sha256": None, "stderr_sha256": None}
    check(doc)
    return canonical_json(doc)


def executed(action_id: str, status: str, exit_code: int | None, duration_ms: int, stdout: bytes,
             stderr: bytes) -> str:
    if type(stdout) is not bytes or type(stderr) is not bytes:
        raise EvidenceError("captured output must be bytes")
    doc = {"schema": SCHEMA, "action_id": action_id, "decision": ALLOW, "status": status, "exit_code": exit_code,
           "duration_ms": duration_ms, "stdout_sha256": sha256_hex(stdout), "stderr_sha256": sha256_hex(stderr)}
    check(doc)
    return canonical_json(doc)
