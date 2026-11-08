"""AUTO-01 evidence: `moneylab.automation.evidence/1` fields, null rules, hashes, canonical JSON (D6)."""

from __future__ import annotations

import hashlib
import inspect
import json

import pytest

from moneylab.automation import evidence
from moneylab.automation.evidence import SCHEMA, EvidenceError

EMPTY = hashlib.sha256(b"").hexdigest()
FIELDS = ["action_id", "decision", "duration_ms", "exit_code", "schema", "status", "stderr_sha256", "stdout_sha256"]


def _doc(**over):
    doc = {"schema": SCHEMA, "action_id": "knowledge_validate", "decision": "ALLOW", "status": "SUCCEEDED",
           "exit_code": 0, "duration_ms": 5, "stdout_sha256": EMPTY, "stderr_sha256": EMPTY}
    doc.update(over)
    return doc


def test_denied_has_null_action_id_and_measurements():
    text = evidence.denied()
    doc = json.loads(text)
    assert sorted(doc) == FIELDS
    assert doc == {"schema": SCHEMA, "action_id": None, "decision": "DENY", "status": "DENIED",
                   "exit_code": None, "duration_ms": None, "stdout_sha256": None, "stderr_sha256": None}
    assert text == ('{"action_id":null,"decision":"DENY","duration_ms":null,"exit_code":null,'
                    '"schema":"moneylab.automation.evidence/1","status":"DENIED","stderr_sha256":null,'
                    '"stdout_sha256":null}')


def test_denied_takes_no_caller_input():
    assert list(inspect.signature(evidence.denied).parameters) == []
    with pytest.raises(TypeError):
        evidence.denied("rm -rf /")  # type: ignore[call-arg]


def test_canonical_json_is_sorted_compact_ascii():
    text = evidence.executed("knowledge_validate", "SUCCEEDED", 0, 12, b"out", b"err")
    assert text == json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert text.isascii() and " " not in text and not text.endswith("\n")
    assert list(json.loads(text)) == FIELDS
    assert evidence.denied() == evidence.canonical_json(json.loads(evidence.denied()))


def test_hashes_are_of_the_raw_bytes_and_output_is_not_included():
    out, err = "결과 SECRET-OUT".encode(), b"\x00\xffSECRET-ERR\r\n"
    text = evidence.executed("knowledge_validate", "VALIDATION_FAILED", 1, 3, out, err)
    doc = json.loads(text)
    assert doc["stdout_sha256"] == hashlib.sha256(out).hexdigest()
    assert doc["stderr_sha256"] == hashlib.sha256(err).hexdigest()
    assert "SECRET" not in text and doc["exit_code"] == 1


@pytest.mark.parametrize("status", ["TIMEOUT", "OUTPUT_LIMIT_EXCEEDED"])
def test_stopped_runs_have_null_exit_code_and_empty_hash_when_nothing_was_kept(status):
    doc = json.loads(evidence.executed("knowledge_validate", status, None, 60000, b"", b""))
    assert doc["exit_code"] is None and doc["decision"] == "ALLOW" and doc["status"] == status
    assert doc["stdout_sha256"] == doc["stderr_sha256"] == EMPTY


def test_determinism_excludes_duration():
    a = json.loads(evidence.executed("knowledge_validate", "SUCCEEDED", 0, 1, b"x", b""))
    b = json.loads(evidence.executed("knowledge_validate", "SUCCEEDED", 0, 999, b"x", b""))
    assert a != b
    a.pop("duration_ms"), b.pop("duration_ms")
    assert a == b


@pytest.mark.parametrize("over", [
    {"status": "TIMEOUT", "exit_code": 0},
    {"status": "OUTPUT_LIMIT_EXCEEDED", "exit_code": 1},
    {"status": "SUCCEEDED", "exit_code": None},
    {"exit_code": True},
    {"exit_code": 1.0},
    {"duration_ms": -1},
    {"duration_ms": 1.5},
    {"duration_ms": True},
    {"duration_ms": None},
    {"stdout_sha256": None},
    {"stdout_sha256": "A" * 64},
    {"stderr_sha256": "0" * 63},
    {"status": "DENIED"},
    {"decision": "DENY"},
    {"decision": "MAYBE"},
    {"status": "OK"},
    {"schema": "moneylab.automation.evidence/2"},
    {"action_id": None},
    {"action_id": 7},
    {"action_id": "not_registered"},
    {"action_id": "Knowledge_validate"},
    {"action_id": "knowledge_validate "},
    {"extra": 1},
])
def test_inconsistent_documents_are_rejected(over):
    with pytest.raises(EvidenceError):
        evidence.check(_doc(**over))


def test_inconsistent_denied_is_rejected():
    denied = json.loads(evidence.denied())
    for key, value in (("action_id", "x"), ("action_id", "knowledge_validate"), ("action_id", ""),
                       ("exit_code", 0), ("duration_ms", 0), ("stdout_sha256", EMPTY), ("stderr_sha256", EMPTY)):
        with pytest.raises(EvidenceError):
            evidence.check({**denied, key: value})
    bad = dict(denied)
    del bad["exit_code"]
    with pytest.raises(EvidenceError):
        evidence.check(bad)


def test_executed_rejects_bad_inputs():
    with pytest.raises(EvidenceError):
        evidence.executed("knowledge_validate", "SUCCEEDED", 0, 1, "text", b"")
    with pytest.raises(EvidenceError):
        evidence.executed("knowledge_validate", "TIMEOUT", 3, 1, b"", b"")
    with pytest.raises(EvidenceError):
        evidence.executed("knowledge_validate", "DENIED", None, 1, b"", b"")
    with pytest.raises(EvidenceError):
        evidence.executed("not_registered", "SUCCEEDED", 0, 1, b"", b"")


def test_valid_document_passes():
    evidence.check(_doc())
    evidence.check(_doc(status="UNEXPECTED_EXIT", exit_code=2))
