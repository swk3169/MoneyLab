"""Deterministic, read-only, non-authoritative ResearchTaskProposal generator (SUPERVISOR-01).

`propose` resolves one CE-02 ContextRequest against a trusted KnowledgeBase and turns each eligible packet item (an
OPEN question, a PENDING decision or, in IDEATION mode, a HYPOTHESIS) into one `moneylab.supervisor.proposal/1`
document. `validate_proposal` checks a proposal's structure only; `check_proposal` additionally re-resolves its
request and reports whether its source and context are still current. Record text is quoted as data and never
interpreted. Nothing here executes research, dispatches work, writes files, touches the network or grants approval:
a proposal is not a Work Order and not an authorization."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from moneylab.knowledge import ContextRequestError, KnowledgeBase, resolve_context
from moneylab.knowledge.context import PACKET_SCHEMA, REQUEST_INVALID, normalize_request
from moneylab.knowledge.model import CONTEXT_BOUNDARY
from moneylab.knowledge.query import KnowledgeStateError

RESULT_SCHEMA = "moneylab.supervisor.result/1"
PROPOSAL_SCHEMA = "moneylab.supervisor.proposal/1"
CHECK_SCHEMA = "moneylab.supervisor.check/1"
BOUNDARY = "NON_AUTHORITATIVE_PROPOSAL"
GENERATOR = {"name": "moneylab.supervisor", "rules_version": 1}

# error codes (D24)
PACKET_INVALID = "PACKET_INVALID"
PACKET_TRUNCATED = "PACKET_TRUNCATED"
SOURCE_RECORD_MISSING = "SOURCE_RECORD_MISSING"
SOURCE_RECORD_SUPERSEDED = "SOURCE_RECORD_SUPERSEDED"
SOURCE_RECORD_MISMATCH = "SOURCE_RECORD_MISMATCH"
CANDIDATE_DUPLICATE = "CANDIDATE_DUPLICATE"
PROPOSAL_INVALID = "PROPOSAL_INVALID"
CHECK_REQUEST_REJECTED = "CHECK_REQUEST_REJECTED"

# candidate types and their epistemic classification (D4, D7, D17)
CANDIDATE_RANK = {"OPEN_QUESTION": 1, "PENDING_DECISION": 2, "HYPOTHESIS": 3}
CLASSIFICATION = {"OPEN_QUESTION": "QUESTION_NOT_EVIDENCE", "PENDING_DECISION": "PENDING_NOT_APPROVED",
                  "HYPOTHESIS": "HYPOTHESIS_NOT_EVIDENCE"}

# deterministic templates and fixed lists (D18, D19)
OBJECTIVE_TEMPLATES = {
    "OPEN_QUESTION": ("Investigate open question ", ". The question is not evidence."),
    "PENDING_DECISION": ("Gather information a human reviewer may use for pending decision ",
                         ". The decision is not approved."),
    "HYPOTHESIS": ("Design a test of hypothesis ", ". The hypothesis is not evidence."),
}
UNSPECIFIED = "UNSPECIFIED_REQUIRES_HUMAN"
EXPECTED_EVIDENCE_QUESTIONS = (
    "What observation would answer or advance the source record?",
    "What data, with what provenance, would be required?",
    "Which frozen or preregistered contract constrains this work?",
)
FAILURE_CRITERIA_QUESTIONS = (
    "What result would count as failure or falsification?",
    "What result would make further work on this candidate not worthwhile?",
    "What is explicitly out of scope?",
)
SCOPE_LIMITATIONS = ("SINGLE_SOURCE_RECORD", "CONTEXT_SCOPED_TO_REQUEST", "NO_DEPENDENCY_OR_BLOCKING_INFERENCE",
                     "NO_PRIORITY_OR_RANKING")
PROHIBITED_ACTIONS = ("EXECUTE_RESEARCH", "DISPATCH_WORKER", "MODIFY_REPOSITORY", "MODIFY_KNOWLEDGE_RECORDS",
                      "CREATE_OR_APPROVE_WORK_ORDER", "PROMOTE_EPISTEMIC_STATUS", "ALLOCATE_CAPITAL", "PLACE_ORDERS",
                      "CONNECT_PAPER_OR_LIVE", "CLAIM_PROFITABILITY_OR_ALPHA")
FIXED_LIMITATIONS = ("NOT_VALIDATED", "NOT_READY_TO_RUN", "NOT_A_WORK_ORDER", "DETERMINISTIC_TEMPLATE_ONLY",
                     "KNOWLEDGE_TREE_NOT_VERIFIED")
FIXED_ASSUMPTIONS = ("EXPECTED_EVIDENCE_NOT_DEFINED", "FAILURE_CRITERIA_NOT_DEFINED")
HYPOTHESIS_ONLY_BASIS = "HYPOTHESIS_ONLY_BASIS"
DERIVED_LIMITATION_RE = re.compile(r"^(EXCLUDED_COUNT:(layer_not_eligible|superseded):[1-9][0-9]*|HYPOTHESIS_ONLY_BASIS)$")
DERIVED_ASSUMPTION_RE = re.compile(r"^SOURCE_EVIDENCE_MISSING:evidence\[(0|[1-9][0-9]*)\]$")

# keys that would make a proposal look authorized or executable (D2)
PROHIBITED_KEYS = frozenset({
    "approved", "approval", "authorization", "authorized", "status", "work_order", "work_order_id", "gate",
    "allowed_files", "branch", "commit", "command", "commands", "script", "shell", "execute", "run", "worker",
    "dispatch", "order", "orders", "capital", "allocation", "priority", "score", "rank",
})

TRUST_SOURCE_STATUS = ("VERIFIED", "NO_SOURCES")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
PACKET_SECTIONS = ("task_context", "decisions", "facts", "derived", "questions", "hypotheses")
TRUNCATION_KEYS = frozenset({"truncated", "max_records", "max_chars", "selected_records", "selected_chars",
                             "budget_excluded"})

PROPOSAL_KEYS = frozenset({"schema", "boundary", "proposal_id", "candidate_key", "candidate_type",
                           "epistemic_classification", "source", "objective", "expected_evidence", "failure_criteria",
                           "scope_limitations", "prohibited_actions", "limitations", "unresolved_assumptions",
                           "provenance"})
SOURCE_KEYS = frozenset({"record_ids", "record_sha256", "quoted_text", "text_role"})
QUOTE_KEYS = frozenset({"title", "statement"})
OBJECTIVE_KEYS = frozenset({"form", "text"})
CRITERIA_KEYS = frozenset({"specification", "reviewer_questions"})
PROVENANCE_KEYS = frozenset({"mode", "request", "packet_sha256", "trust_state", "generator"})
TRUST_KEYS = frozenset({"exit_code", "source_status"})
GENERATOR_KEYS = frozenset({"name", "rules_version"})

# check reason codes (D16): a namespace separate from the error codes
SOURCE_STALE_REASONS = ("SOURCE_MISSING", "SOURCE_SUPERSEDED", "SOURCE_INELIGIBLE", "SOURCE_MODIFIED")
SOURCE_NOT_IN_CONTEXT = "SOURCE_NOT_IN_CONTEXT"
KNOWLEDGE_TREE = "NOT_VERIFIED"


class SupervisorError(Exception):
    """A fail-closed Supervisor error; no result or partial result is produced."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def canonical_bytes(obj: Any) -> bytes:
    """The bytes every Supervisor hash is computed over (D10); not the CLI display form."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def content_sha256(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(obj)).hexdigest()


def proposal_identity(proposal: dict[str, Any]) -> str:
    """`proposal_id`: the hash of the whole proposal except `proposal_id` itself (D11)."""
    return content_sha256({k: v for k, v in proposal.items() if k != "proposal_id"})


def objective_text(candidate_type: str, record_id: str) -> str:
    head, tail = OBJECTIVE_TEMPLATES[candidate_type]
    return head + record_id + tail


def _copy(obj: Any) -> Any:
    return json.loads(json.dumps(obj))


def _state(item: dict[str, Any]) -> Any:
    payload = item["record"].get("payload")
    return payload.get("state") if isinstance(payload, dict) else None


def _eligible(candidate_type: str, kind: Any, layer: Any, state: Any) -> bool:
    if candidate_type == "OPEN_QUESTION":
        return kind == "question" and layer != "HYPOTHESIS" and state == "OPEN"
    if candidate_type == "PENDING_DECISION":
        return kind == "decision" and layer != "HYPOTHESIS" and state == "PENDING"
    return layer == "HYPOTHESIS" and (kind == "claim" or (kind == "question" and state == "OPEN")
                                      or (kind == "decision" and state == "PENDING"))


def _check_packet(packet: Any) -> None:
    """Structural packet invariants only (D6); record-level checks apply to candidates."""
    def bad(detail: str) -> SupervisorError:
        return SupervisorError(PACKET_INVALID, detail)

    if not isinstance(packet, dict):
        raise bad("packet must be an object")
    if packet.get("schema") != PACKET_SCHEMA or packet.get("boundary") != CONTEXT_BOUNDARY:
        raise bad(f"packet schema must be {PACKET_SCHEMA!r} with boundary {CONTEXT_BOUNDARY!r}")
    trust = packet.get("trust_state")
    if not isinstance(trust, dict) or trust.get("exit_code") != 0 or isinstance(trust.get("exit_code"), bool):
        raise bad("packet trust_state.exit_code must be 0")
    try:
        normalized = normalize_request(packet.get("request"))
    except ContextRequestError as exc:
        raise bad(f"packet request is not a normalized request: {exc.detail}") from None
    if packet["request"] != normalized:
        raise bad("packet request is not in normalized form")
    for name in PACKET_SECTIONS:
        section = packet.get(name)
        if not isinstance(section, list) or not all(
                isinstance(i, dict) and isinstance(i.get("id"), str) and isinstance(i.get("record"), dict)
                for i in section):
            raise bad(f"packet section {name} must be a list of items with an id and a record")
    if normalized["mode"] == "EVIDENCE" and packet["hypotheses"]:
        raise bad("an EVIDENCE packet must not carry hypotheses")
    truncation = packet.get("truncation")
    if not isinstance(truncation, dict) or set(truncation) != TRUNCATION_KEYS:
        raise bad(f"packet truncation must have exactly the keys {sorted(TRUNCATION_KEYS)}")
    if not isinstance(packet.get("excluded"), list):
        raise bad("packet excluded must be a list")


def _candidates(packet: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Eligible items by packet section (D4), in D7 order."""
    found = [("OPEN_QUESTION", i) for i in packet["questions"] if _state(i) == "OPEN"]
    found += [("PENDING_DECISION", i) for i in packet["decisions"] if _state(i) == "PENDING"]
    if packet["request"]["mode"] == "IDEATION":
        found += [("HYPOTHESIS", i) for i in packet["hypotheses"]
                  if _eligible("HYPOTHESIS", i["record"].get("kind"), "HYPOTHESIS", _state(i))]
    return sorted(found, key=lambda c: (CANDIDATE_RANK[c[0]], c[1]["id"]))


def _verify_source(kb: KnowledgeBase, candidate_type: str, item: dict[str, Any]) -> None:
    rid = item["id"]
    data = kb.get(rid)
    if data is None:
        raise SupervisorError(SOURCE_RECORD_MISSING, f"no record {rid}")
    if not kb.is_current(rid):
        raise SupervisorError(SOURCE_RECORD_SUPERSEDED, f"{rid} is superseded")
    rec = item["record"]
    same = (item.get("kind") == data["kind"] == rec.get("kind") and item.get("layer") == data["layer"] == rec.get("layer")
            and rec == data and _eligible(candidate_type, data["kind"], data["layer"], _state(item)))
    if not same:
        raise SupervisorError(SOURCE_RECORD_MISMATCH, f"packet item {rid} does not match the trusted record")


def _limitations(candidate_type: str, packet: dict[str, Any]) -> list[str]:
    counts: dict[str, int] = {}
    for entry in packet["excluded"]:
        reason = entry.get("reason") if isinstance(entry, dict) else None
        if reason in ("layer_not_eligible", "superseded"):
            counts[reason] = counts.get(reason, 0) + 1
    derived = [f"EXCLUDED_COUNT:{reason}:{n}" for reason, n in counts.items()]
    if candidate_type == "HYPOTHESIS":
        derived.append(HYPOTHESIS_ONLY_BASIS)
    return [*FIXED_LIMITATIONS, *sorted(derived)]


def _assumptions(rec: dict[str, Any]) -> list[str]:
    evidence = rec.get("evidence")
    derived = [f"SOURCE_EVIDENCE_MISSING:evidence[{i}]" for i, ev in enumerate(evidence if isinstance(evidence, list) else [])
               if isinstance(ev, dict) and ev.get("availability") == "MISSING"]
    return [*FIXED_ASSUMPTIONS, *sorted(derived)]


def _proposal(candidate_type: str, item: dict[str, Any], packet: dict[str, Any], packet_sha256: str) -> dict[str, Any]:
    rid, rec = item["id"], item["record"]
    request = _copy(packet["request"])
    proposal: dict[str, Any] = {
        "schema": PROPOSAL_SCHEMA,
        "boundary": BOUNDARY,
        "candidate_key": f"{candidate_type}:{rid}",
        "candidate_type": candidate_type,
        "epistemic_classification": CLASSIFICATION[candidate_type],
        "source": {"record_ids": [rid], "record_sha256": {rid: content_sha256(item)},
                   "quoted_text": {rid: {"title": rec["title"], "statement": rec["statement"]}},
                   "text_role": "QUOTED_RECORD_DATA"},
        "objective": {"form": "DETERMINISTIC_TEMPLATE", "text": objective_text(candidate_type, rid)},
        "expected_evidence": {"specification": UNSPECIFIED, "reviewer_questions": list(EXPECTED_EVIDENCE_QUESTIONS)},
        "failure_criteria": {"specification": UNSPECIFIED, "reviewer_questions": list(FAILURE_CRITERIA_QUESTIONS)},
        "scope_limitations": list(SCOPE_LIMITATIONS),
        "prohibited_actions": list(PROHIBITED_ACTIONS),
        "limitations": _limitations(candidate_type, packet),
        "unresolved_assumptions": _assumptions(rec),
        "provenance": {"mode": request["mode"], "request": request, "packet_sha256": packet_sha256,
                       "trust_state": {"exit_code": packet["trust_state"]["exit_code"],
                                       "source_status": packet["trust_state"]["source_status"]},
                       "generator": dict(GENERATOR)},
    }
    proposal["proposal_id"] = proposal_identity(proposal)
    return proposal


def propose(kb: KnowledgeBase, request: dict[str, Any]) -> dict[str, Any]:
    """One ContextRequest -> one `moneylab.supervisor.result/1` (all or nothing).

    CE-02 errors (KnowledgeStateError, ContextRequestError) propagate unchanged; Supervisor errors are
    SupervisorError."""
    packet = resolve_context(kb, request)
    _check_packet(packet)
    if packet["truncation"]["truncated"] is not False:
        raise SupervisorError(PACKET_TRUNCATED, "the packet was truncated by its budget; no proposal is produced")
    candidates = _candidates(packet)
    for candidate_type, item in candidates:
        _verify_source(kb, candidate_type, item)
    keys = [f"{t}:{i['id']}" for t, i in candidates]
    duplicates = sorted({k for k in keys if keys.count(k) > 1})
    if duplicates:
        raise SupervisorError(CANDIDATE_DUPLICATE, f"duplicate candidates {duplicates}")
    packet_sha256 = content_sha256(packet)
    proposals = [_proposal(t, i, packet, packet_sha256) for t, i in candidates]
    return {"schema": RESULT_SCHEMA, "boundary": BOUNDARY,
            "outcome": "PROPOSALS_CREATED" if proposals else "NO_CANDIDATES",
            "proposal_count": len(proposals), "proposals": proposals}


def _invalid(detail: str) -> SupervisorError:
    return SupervisorError(PROPOSAL_INVALID, detail)


def _json_compatible(value: Any, where: str) -> None:
    if isinstance(value, dict):
        for key, inner in value.items():
            if not isinstance(key, str):
                raise _invalid(f"{where}: object keys must be strings")
            _json_compatible(inner, f"{where}.{key}")
    elif isinstance(value, list):
        for i, inner in enumerate(value):
            _json_compatible(inner, f"{where}[{i}]")
    elif not (value is None or isinstance(value, (str, bool, int))):
        raise _invalid(f"{where}: {type(value).__name__} is not an allowed JSON value")


def _keys(obj: Any, expected: frozenset[str], where: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise _invalid(f"{where} must be an object")
    if set(obj) != expected:
        raise _invalid(f"{where} keys must be exactly {sorted(expected)}, got {sorted(obj)}")
    return obj


def _string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise _invalid(f"{where} must be a non-empty string")
    return value


def _string_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise _invalid(f"{where} must be a list of strings")
    return value


def _prohibited(value: Any, where: str) -> None:
    if isinstance(value, dict):
        for key, inner in value.items():
            if key in PROHIBITED_KEYS:
                raise _invalid(f"{where}: prohibited key {key!r}")
            _prohibited(inner, f"{where}.{key}")
    elif isinstance(value, list):
        for i, inner in enumerate(value):
            _prohibited(inner, f"{where}[{i}]")


def _fixed_then_derived(value: list[str], fixed: tuple[str, ...], pattern: re.Pattern[str], where: str) -> None:
    if value[:len(fixed)] != list(fixed):
        raise _invalid(f"{where} must start with {list(fixed)}")
    derived = value[len(fixed):]
    if derived != sorted(set(derived)) or not all(pattern.fullmatch(v) for v in derived):
        raise _invalid(f"{where} has entries outside the allowed patterns or out of order")


def validate_proposal(obj: Any) -> None:
    """Structural and deterministic validation of one proposal (D29), in a fixed order.

    No KnowledgeBase, file or git access. Passing says nothing about source authenticity, currency or approval."""
    # 1 JSON compatibility
    _json_compatible(obj, "proposal")
    # 2 strict schema
    p = _keys(obj, PROPOSAL_KEYS, "proposal")
    for name in ("schema", "boundary", "proposal_id", "candidate_key", "candidate_type", "epistemic_classification"):
        _string(p[name], name)
    source = _keys(p["source"], SOURCE_KEYS, "source")
    record_ids = _string_list(source["record_ids"], "source.record_ids")
    if len(record_ids) != 1:
        raise _invalid("source.record_ids must hold exactly one record ID")
    rid = _string(record_ids[0], "source.record_ids[0]")
    digests = _keys(source["record_sha256"], frozenset({rid}), "source.record_sha256")
    quotes = _keys(source["quoted_text"], frozenset({rid}), "source.quoted_text")
    quote = _keys(quotes[rid], QUOTE_KEYS, f"source.quoted_text.{rid}")
    _string(quote["title"], "quoted title")
    _string(quote["statement"], "quoted statement")
    _string(digests[rid], "source.record_sha256")
    _string(source["text_role"], "source.text_role")
    objective = _keys(p["objective"], OBJECTIVE_KEYS, "objective")
    _string(objective["form"], "objective.form")
    _string(objective["text"], "objective.text")
    criteria = {name: _keys(p[name], CRITERIA_KEYS, name) for name in ("expected_evidence", "failure_criteria")}
    for name, value in criteria.items():
        _string(value["specification"], f"{name}.specification")
        _string_list(value["reviewer_questions"], f"{name}.reviewer_questions")
    for name in ("scope_limitations", "prohibited_actions", "limitations", "unresolved_assumptions"):
        _string_list(p[name], name)
    provenance = _keys(p["provenance"], PROVENANCE_KEYS, "provenance")
    _string(provenance["mode"], "provenance.mode")
    _string(provenance["packet_sha256"], "provenance.packet_sha256")
    if not isinstance(provenance["request"], dict):
        raise _invalid("provenance.request must be an object")
    trust = _keys(provenance["trust_state"], TRUST_KEYS, "provenance.trust_state")
    generator = _keys(provenance["generator"], GENERATOR_KEYS, "provenance.generator")
    # 3 constants
    if p["schema"] != PROPOSAL_SCHEMA or p["boundary"] != BOUNDARY:
        raise _invalid(f"schema must be {PROPOSAL_SCHEMA!r} and boundary {BOUNDARY!r}")
    if generator["name"] != GENERATOR["name"] or isinstance(generator["rules_version"], bool) or \
            generator["rules_version"] != GENERATOR["rules_version"]:
        raise _invalid(f"generator must be {GENERATOR}; this validator supports rules_version 1 only")
    if source["text_role"] != "QUOTED_RECORD_DATA" or objective["form"] != "DETERMINISTIC_TEMPLATE":
        raise _invalid("source.text_role must be QUOTED_RECORD_DATA and objective.form DETERMINISTIC_TEMPLATE")
    if any(value["specification"] != UNSPECIFIED for value in criteria.values()):
        raise _invalid(f"expected_evidence and failure_criteria specification must be {UNSPECIFIED}")
    # 4 prohibited keys
    _prohibited(p, "proposal")
    # 5 consistency
    ctype = p["candidate_type"]
    if ctype not in CLASSIFICATION or p["epistemic_classification"] != CLASSIFICATION[ctype]:
        raise _invalid("candidate_type and epistemic_classification are not a valid pair")
    if p["candidate_key"] != f"{ctype}:{rid}":
        raise _invalid("candidate_key must be <candidate_type>:<record_id>")
    if provenance["mode"] != provenance["request"].get("mode"):
        raise _invalid("provenance.mode must equal provenance.request.mode")
    if ctype == "HYPOTHESIS" and (provenance["mode"] != "IDEATION" or HYPOTHESIS_ONLY_BASIS not in p["limitations"]):
        raise _invalid("a HYPOTHESIS proposal needs IDEATION mode and the HYPOTHESIS_ONLY_BASIS limitation")
    # 6 normalized request
    try:
        normalized = normalize_request(provenance["request"])
    except ContextRequestError as exc:
        raise _invalid(f"provenance.request is not a valid ContextRequest: {exc.detail}") from None
    if provenance["request"] != normalized:
        raise _invalid("provenance.request is not in normalized form")
    # 7 template
    if objective["text"] != objective_text(ctype, rid):
        raise _invalid("objective.text does not match the deterministic template")
    if criteria["expected_evidence"]["reviewer_questions"] != list(EXPECTED_EVIDENCE_QUESTIONS) or \
            criteria["failure_criteria"]["reviewer_questions"] != list(FAILURE_CRITERIA_QUESTIONS):
        raise _invalid("reviewer_questions do not match the fixed lists")
    # 8 lists
    if p["scope_limitations"] != list(SCOPE_LIMITATIONS) or p["prohibited_actions"] != list(PROHIBITED_ACTIONS):
        raise _invalid("scope_limitations and prohibited_actions must be the fixed lists in order")
    _fixed_then_derived(p["limitations"], FIXED_LIMITATIONS, DERIVED_LIMITATION_RE, "limitations")
    _fixed_then_derived(p["unresolved_assumptions"], FIXED_ASSUMPTIONS, DERIVED_ASSUMPTION_RE,
                        "unresolved_assumptions")
    # 9 hash formats and trust state
    for name, value in (("proposal_id", p["proposal_id"]), ("provenance.packet_sha256", provenance["packet_sha256"]),
                        ("source.record_sha256", digests[rid])):
        if not HASH_RE.fullmatch(value):
            raise _invalid(f"{name} must match {HASH_RE.pattern}")
    if trust["exit_code"] != 0 or isinstance(trust["exit_code"], bool) or \
            trust["source_status"] not in TRUST_SOURCE_STATUS:
        raise _invalid(f"trust_state must be exit_code 0 with source_status in {TRUST_SOURCE_STATUS}")
    # 10 identity
    if p["proposal_id"] != proposal_identity(p):
        raise _invalid("proposal_id does not match the canonical hash of the proposal")


def _find_item(packet: dict[str, Any], rid: str) -> dict[str, Any] | None:
    for name in PACKET_SECTIONS:
        for item in packet[name]:
            if item["id"] == rid:
                return item
    return None


def check_proposal(kb: KnowledgeBase, proposal: Any) -> dict[str, Any]:
    """Whether a valid proposal's source and request-scoped context are still current (D16, D30).

    Reads only; never writes or records anything. CURRENT means the request-scoped inputs are unchanged, nothing
    more; the Knowledge tree as a whole is NOT_VERIFIED."""
    validate_proposal(proposal)
    if not kb.trusted:
        raise KnowledgeStateError(kb.report)
    rid = proposal["source"]["record_ids"][0]
    ctype = proposal["candidate_type"]
    reasons: list[str] = []
    # S1 source
    data = kb.get(rid)
    if data is None:
        reasons.append("SOURCE_MISSING")
    elif not kb.is_current(rid):
        reasons.append("SOURCE_SUPERSEDED")
    elif not _eligible(ctype, data["kind"], data["layer"],
                       data["payload"].get("state") if isinstance(data.get("payload"), dict) else None):
        reasons.append("SOURCE_INELIGIBLE")
    source_reason = bool(reasons)
    # S2 re-resolve
    packet: dict[str, Any] | None
    try:
        packet = resolve_context(kb, proposal["provenance"]["request"])
    except ContextRequestError as exc:
        if exc.code == REQUEST_INVALID:
            raise SupervisorError(CHECK_REQUEST_REJECTED, f"the recorded request was rejected: {exc.detail}") from None
        reasons.append(f"CONTEXT_UNRESOLVABLE:{exc.code}")
        packet = None
    # S3 packet, S4 source item
    item = None
    if packet is not None:
        if packet["truncation"]["truncated"]:
            reasons.append("CONTEXT_TRUNCATED")
        if content_sha256(packet) != proposal["provenance"]["packet_sha256"]:
            reasons.append("PACKET_HASH_CHANGED")
        item = _find_item(packet, rid)
    if item is not None:
        if content_sha256(item) != proposal["source"]["record_sha256"][rid]:
            reasons.append("SOURCE_MODIFIED")
        elif {"title": item["record"].get("title"), "statement": item["record"].get("statement")} != \
                proposal["source"]["quoted_text"][rid]:
            raise _invalid("the source digest matches but the quoted text does not")
    elif not source_reason:
        reasons.append(SOURCE_NOT_IN_CONTEXT)
    reasons.sort()
    if any(r in SOURCE_STALE_REASONS for r in reasons):
        source_status = "STALE_SOURCE"
    elif SOURCE_NOT_IN_CONTEXT in reasons:
        source_status = "NOT_VERIFIED"
    else:
        source_status = "CURRENT"
    context_status = "STALE_CONTEXT" if any(r.startswith("CONTEXT_") or r == "PACKET_HASH_CHANGED"
                                            for r in reasons) else "CURRENT"
    if source_status == "STALE_SOURCE":
        staleness = "STALE_SOURCE"
    elif context_status == "STALE_CONTEXT" or source_status == "NOT_VERIFIED":
        staleness = "STALE_CONTEXT"
    else:
        staleness = "CURRENT"
    return {"schema": CHECK_SCHEMA, "boundary": BOUNDARY, "proposal_id": proposal["proposal_id"],
            "staleness": staleness, "source_status": source_status, "context_status": context_status,
            "knowledge_tree": KNOWLEDGE_TREE, "reasons": reasons}
