"""Deterministic in-memory queries and context selection over a validated knowledge repository.

Fail-closed: every query raises KnowledgeStateError unless the whole repository validated cleanly (report exit code 0:
no rule violation and sources verified). An invalid repository never yields a "valid subset" answer. Every returned
collection is ordered by record ID and is JSON-serializable. There is no natural-language or semantic search. Context
selection only retrieves, resolves and filters records: it never trades, sizes, approves capital or risk, promotes a
scientific status, rewrites records or invents evidence."""

from __future__ import annotations

from typing import Any

from moneylab.knowledge.load import LoadResult
from moneylab.knowledge.model import CONTEXT_BOUNDARY, CONTEXT_MODES, KINDS, TOPICS, Record
from moneylab.knowledge.validate import Report

MARKINGS = {"SOURCE_FACT": "SOURCE_FACT", "DERIVED_SUMMARY": "DERIVED_SUMMARY: derived, see lineage",
            "HYPOTHESIS": "HYPOTHESIS: not evidence"}


class KnowledgeStateError(Exception):
    """The repository did not validate cleanly, so no trusted query result is produced."""

    def __init__(self, report: Report) -> None:
        super().__init__(f"knowledge repository is not trusted (validation exit code {report.exit_code}, "
                         f"source status {report.source_status}, {len(report.problems)} problem(s))")
        self.report = report


class KnowledgeBase:
    def __init__(self, loaded: LoadResult, report: Report) -> None:
        self.report = report
        self.trusted = report.exit_code == 0
        self._records: dict[str, Record] = {r.id: r for r in loaded.records} if self.trusted else {}
        self._superseded_by: dict[str, str] = {}
        for rid in sorted(self._records):
            for old in self._records[rid].data["supersedes"]:
                if old in self._records:
                    self._superseded_by[old] = rid

    def _check(self) -> None:
        if not self.trusted:
            raise KnowledgeStateError(self.report)

    def _data(self, ids: Any) -> list[dict[str, Any]]:
        return [self._records[i].data for i in sorted(ids)]

    def _require(self, record_id: str) -> Record:
        self._check()
        if record_id not in self._records:
            raise KeyError(f"no record {record_id}")
        return self._records[record_id]

    # 1
    def get(self, record_id: str) -> dict[str, Any] | None:
        self._check()
        rec = self._records.get(record_id)
        return rec.data if rec else None

    # 2
    def by_kind(self, kind: str) -> list[dict[str, Any]]:
        self._check()
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}")
        return self._data(i for i, r in self._records.items() if r.kind == kind)

    # 3
    def current(self) -> list[dict[str, Any]]:
        self._check()
        return self._data(i for i in self._records if i not in self._superseded_by)

    def is_current(self, record_id: str) -> bool:
        self._require(record_id)
        return record_id not in self._superseded_by

    # 4
    def lineage(self, record_id: str) -> dict[str, Any]:
        """Older records this one replaces (transitively) and the chain of newer records that replace it."""
        self._require(record_id)
        older: set[str] = set()
        todo = [record_id]
        while todo:
            for old in self._records[todo.pop()].data["supersedes"]:
                if old in self._records and old not in older and old != record_id:
                    older.add(old)
                    todo.append(old)
        newer: list[str] = []
        node = record_id
        while node in self._superseded_by and self._superseded_by[node] not in newer:
            node = self._superseded_by[node]
            newer.append(node)
        return {"id": record_id, "supersedes": sorted(older), "superseded_by": newer,
                "current": newer[-1] if newer else record_id}

    # 5
    def task_records(self, task_id: str) -> list[dict[str, Any]]:
        self._check()
        return self._data(i for i, r in self._records.items() if r.namespace == task_id)

    # 6
    def claims_by_topic(self, topic: str) -> list[dict[str, Any]]:
        self._check()
        if topic not in TOPICS:
            raise ValueError(f"topic must be one of {TOPICS}")
        return self._data(i for i, r in self._records.items() if r.kind == "claim" and topic in r.data["topics"])

    # 7
    def claim_support(self, record_id: str) -> dict[str, Any]:
        """A claim's EvidenceRefs and its full derived_from lineage (with each ancestor's layer)."""
        rec = self._require(record_id)
        if rec.kind != "claim":
            raise ValueError(f"{record_id} is not a claim")
        return {"id": record_id, "layer": rec.layer, "evidence": rec.data["evidence"],
                "derived_from": self._derivation(record_id)}

    def _derivation(self, record_id: str) -> list[dict[str, str]]:
        seen: set[str] = set()
        todo = list(self._records[record_id].data["derived_from"])
        while todo:
            ref = todo.pop()
            if ref in seen or ref not in self._records or ref == record_id:
                continue
            seen.add(ref)
            todo.extend(self._records[ref].data["derived_from"])
        return [{"id": i, "layer": self._records[i].layer} for i in sorted(seen)]

    # 8
    def open_questions(self) -> list[dict[str, Any]]:
        self._check()
        return self._data(i for i, r in self._records.items() if r.kind == "question"
                          and r.data["payload"]["state"] == "OPEN" and i not in self._superseded_by)

    # 9
    def context(self, mode: str, topic: str | None = None) -> dict[str, Any]:
        """EVIDENCE: current SOURCE_FACT, and current DERIVED_SUMMARY marked as derived with its lineage;
        HYPOTHESIS excluded. IDEATION: all current layers, HYPOTHESIS marked as not evidence."""
        self._check()
        if mode not in CONTEXT_MODES:
            raise ValueError(f"mode must be one of {CONTEXT_MODES}")
        if topic is not None and topic not in TOPICS:
            raise ValueError(f"topic must be one of {TOPICS}")
        items = []
        for rid in sorted(self._records):
            rec = self._records[rid]
            if rid in self._superseded_by or (topic is not None and topic not in rec.data["topics"]):
                continue
            if mode == "EVIDENCE" and rec.layer == "HYPOTHESIS":
                continue
            item: dict[str, Any] = {"id": rid, "kind": rec.kind, "layer": rec.layer, "marking": MARKINGS[rec.layer],
                                    "record": rec.data}
            if rec.layer == "DERIVED_SUMMARY":
                item["lineage"] = self._derivation(rid)
            items.append(item)
        return {"mode": mode, "boundary": CONTEXT_BOUNDARY, "source_status": self.report.source_status,
                "topic": topic, "items": items}
