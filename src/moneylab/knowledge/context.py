"""Deterministic ContextRequest -> ContextPacket resolver (CONTEXT-ENGINE-02).

A request (`moneylab.context.request/1`) names filters, a mode and a budget; the resolver selects current records of a
trusted KnowledgeBase, places each in one section, bounds the packet by record count and characters and lists what it
left out (`moneylab.context.packet/1`). The objective is echoed as data and never interpreted. The packet is derived,
ephemeral output: the Git-tracked records stay the only authority, and every item carries its complete record."""

from __future__ import annotations

import json
import re
from typing import Any

from moneylab.knowledge.model import CONTEXT_BOUNDARY, CONTEXT_MODES, ID_RE, KINDS, TOPICS
from moneylab.knowledge.query import MARKINGS, KnowledgeBase, KnowledgeStateError

REQUEST_SCHEMA = "moneylab.context.request/1"
PACKET_SCHEMA = "moneylab.context.packet/1"

OBJECTIVE_MAX_CHARS = 2000
DEFAULT_BUDGET = {"max_records": 20, "max_chars": 32000}
BUDGET_CAPS = {"max_records": 200, "max_chars": 400000}
NAMESPACE_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,47}$")

SECTIONS = ("task_context", "decisions", "facts", "derived", "questions", "hypotheses")

REQUEST_INVALID = "REQUEST_INVALID"
REPOSITORY_UNTRUSTED = "REPOSITORY_UNTRUSTED"
REQUIRED_NOT_FOUND = "REQUIRED_NOT_FOUND"
REQUIRED_SUPERSEDED = "REQUIRED_SUPERSEDED"
REQUIRED_LAYER_NOT_ELIGIBLE = "REQUIRED_LAYER_NOT_ELIGIBLE"
REQUIRED_OVER_BUDGET = "REQUIRED_OVER_BUDGET"

_REQUIRED_FIELDS = ("mode", "objective", "schema")
_LIST_FIELDS = ("include_ids", "kinds", "namespaces", "topics")
_OPTIONAL_FIELDS = (*_LIST_FIELDS, "budget", "include_open_questions")


class ContextRequestError(Exception):
    """An invalid request or an unsatisfiable required record; no packet is produced."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _invalid(detail: str) -> ContextRequestError:
    return ContextRequestError(REQUEST_INVALID, detail)


def _check_list(name: str, value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise _invalid(f"{name} must be a list of strings")
    if len(set(value)) != len(value):
        raise _invalid(f"{name} contains duplicate values")
    allowed: tuple[str, ...] | None = {"topics": TOPICS, "kinds": KINDS}.get(name)
    pattern = {"namespaces": NAMESPACE_RE, "include_ids": ID_RE}.get(name)
    for v in value:
        if allowed is not None and v not in allowed:
            raise _invalid(f"{name} value {v!r} is not one of {allowed}")
        if pattern is not None and not pattern.fullmatch(v):
            raise _invalid(f"{name} value {v!r} does not match {pattern.pattern}")
    return sorted(value)


def normalize_request(request: Any) -> dict[str, Any]:
    """The effective request: validated, defaults filled, list fields sorted. Malformed input is rejected, never
    repaired."""
    if not isinstance(request, dict):
        raise _invalid("request must be a JSON object")
    unknown = sorted(set(request) - set(_REQUIRED_FIELDS) - set(_OPTIONAL_FIELDS))
    if unknown:
        raise _invalid(f"unknown fields {unknown}")
    missing = [f for f in _REQUIRED_FIELDS if f not in request]
    if missing:
        raise _invalid(f"missing required fields {missing}")
    if not isinstance(request["schema"], str) or request["schema"] != REQUEST_SCHEMA:
        raise _invalid(f"schema must be {REQUEST_SCHEMA!r}")
    objective = request["objective"]
    if not isinstance(objective, str) or not objective or len(objective) > OBJECTIVE_MAX_CHARS:
        raise _invalid(f"objective must be a non-empty string of at most {OBJECTIVE_MAX_CHARS} characters")
    if not isinstance(request["mode"], str) or request["mode"] not in CONTEXT_MODES:
        raise _invalid(f"mode must be one of {CONTEXT_MODES}")
    effective: dict[str, Any] = {"schema": REQUEST_SCHEMA, "objective": objective, "mode": request["mode"]}
    for name in _LIST_FIELDS:
        effective[name] = _check_list(name, request.get(name, []))
    include_open = request.get("include_open_questions", False)
    if not isinstance(include_open, bool):
        raise _invalid("include_open_questions must be a boolean")
    effective["include_open_questions"] = include_open
    budget = request.get("budget", {})
    if not isinstance(budget, dict):
        raise _invalid("budget must be an object")
    unknown = sorted(set(budget) - set(DEFAULT_BUDGET))
    if unknown:
        raise _invalid(f"unknown budget fields {unknown}")
    effective["budget"] = {}
    for name in sorted(DEFAULT_BUDGET):
        value = budget.get(name, DEFAULT_BUDGET[name])
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= BUDGET_CAPS[name]:
            raise _invalid(f"budget.{name} must be an integer from 1 to {BUDGET_CAPS[name]}")
        effective["budget"][name] = value
    return effective


def _section(kind: Any, layer: Any) -> str:
    if layer == "HYPOTHESIS":
        return "hypotheses"
    if kind == "task":
        return "task_context"
    if kind == "decision":
        return "decisions"
    if kind == "question":
        return "questions"
    return "facts" if layer == "SOURCE_FACT" else "derived"


def _derivation(records: dict[str, dict[str, Any]], record_id: str) -> list[dict[str, str]]:
    """Every record this one is derived from, transitively, with its layer (the meaning of query's derivation)."""
    seen: set[str] = set()
    todo = list(records[record_id]["derived_from"])
    while todo:
        ref = todo.pop()
        if ref in seen or ref not in records or ref == record_id:
            continue
        seen.add(ref)
        todo.extend(records[ref]["derived_from"])
    return [{"id": i, "layer": records[i]["layer"]} for i in sorted(seen)]


def _item(records: dict[str, dict[str, Any]], record_id: str) -> dict[str, Any]:
    data = records[record_id]
    # An independent copy, so that changing a packet can never change the trusted KnowledgeBase.
    item: dict[str, Any] = {"id": record_id, "kind": data["kind"], "layer": data["layer"],
                            "marking": MARKINGS[data["layer"]], "record": json.loads(json.dumps(data))}
    if data["layer"] == "DERIVED_SUMMARY":
        item["lineage"] = _derivation(records, record_id)
    return item


def item_size(item: dict[str, Any]) -> int:
    """Characters an item uses of the `max_chars` budget."""
    return len(json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def _namespace(record_id: str) -> str:
    match = ID_RE.fullmatch(record_id)
    return match.group(2) if match else ""


def resolve_context(kb: KnowledgeBase, request: dict[str, Any]) -> dict[str, Any]:
    """Resolve one ContextRequest against a trusted KnowledgeBase into a ContextPacket.

    Raises KnowledgeStateError for an untrusted repository and ContextRequestError for an invalid request or a
    required record that is missing, superseded, not eligible in this mode or over the budget."""
    if not kb.trusted:
        raise KnowledgeStateError(kb.report)
    req = normalize_request(request)
    mode, budget = req["mode"], req["budget"]
    records = {r["id"]: r for kind in KINDS for r in kb.by_kind(kind)}
    current = {r["id"] for r in kb.current()}

    def eligible(record_id: str) -> bool:
        return mode == "IDEATION" or records[record_id]["layer"] != "HYPOTHESIS"

    def in_scope(record_id: str) -> bool:
        data = records[record_id]
        return (not req["topics"] or any(t in data["topics"] for t in req["topics"])) and \
            (not req["namespaces"] or _namespace(record_id) in req["namespaces"])

    def rank(record_id: str) -> tuple[int, str]:
        return SECTIONS.index(_section(records[record_id]["kind"], records[record_id]["layer"])), record_id

    required = req["include_ids"]
    for rid in required:
        if rid not in records:
            raise ContextRequestError(REQUIRED_NOT_FOUND, f"no record {rid}")
        if rid not in current:
            raise ContextRequestError(REQUIRED_SUPERSEDED, f"{rid} is superseded by {kb.lineage(rid)['current']}")
        if not eligible(rid):
            raise ContextRequestError(REQUIRED_LAYER_NOT_ELIGIBLE, f"{rid} is {records[rid]['layer']}, "
                                                                   f"not eligible in {mode} mode")
    selected = [_item(records, rid) for rid in sorted(required, key=rank)]
    selected_chars = sum(item_size(i) for i in selected)
    if len(selected) > budget["max_records"] or selected_chars > budget["max_chars"]:
        raise ContextRequestError(REQUIRED_OVER_BUDGET, f"{len(selected)} required records of {selected_chars} "
                                                        f"characters exceed max_records {budget['max_records']} or "
                                                        f"max_chars {budget['max_chars']}")

    excluded: list[dict[str, str]] = []
    ordinary: list[str] = []
    for rid in sorted(records):
        if rid in required:
            continue
        matched = in_scope(rid) and (not req["kinds"] or records[rid]["kind"] in req["kinds"])
        open_question = req["include_open_questions"] and records[rid]["kind"] == "question" and \
            records[rid]["payload"]["state"] == "OPEN" and rid in current and in_scope(rid)
        if not (matched or open_question):
            continue
        if rid not in current:
            excluded.append({"id": rid, "reason": "superseded"})
        elif not eligible(rid):
            excluded.append({"id": rid, "reason": "layer_not_eligible"})
        else:
            ordinary.append(rid)

    budget_excluded = 0
    for rid in sorted(ordinary, key=rank):
        item = _item(records, rid)
        size = item_size(item)
        if budget_excluded or len(selected) + 1 > budget["max_records"] or \
                selected_chars + size > budget["max_chars"]:
            excluded.append({"id": rid, "reason": "budget"})
            budget_excluded += 1
            continue
        selected.append(item)
        selected_chars += size

    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA, "boundary": CONTEXT_BOUNDARY,
        "trust_state": {"exit_code": kb.report.exit_code, "source_status": kb.report.source_status},
        "request": req,
    }
    for name in SECTIONS:
        packet[name] = sorted((i for i in selected if _section(i["kind"], i["layer"]) == name), key=lambda i: i["id"])
    packet["excluded"] = sorted(excluded, key=lambda e: (e["reason"], e["id"]))
    packet["truncation"] = {"truncated": budget_excluded > 0, "max_records": budget["max_records"],
                            "max_chars": budget["max_chars"], "selected_records": len(selected),
                            "selected_chars": selected_chars, "budget_excluded": budget_excluded}
    return packet
