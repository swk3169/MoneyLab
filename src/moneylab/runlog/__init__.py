"""Non-authoritative evidence records (AUTO-03).

`store_evidence(task_id, raw)` validates `moneylab.automation.evidence/1` bytes supplied by the caller and stores
them under the ignored `data/processed/runlog/<task_id>/`; `load_evidence(task_id, record_id)` reads exactly one
named record. A stored record proves neither that an action ran, nor who wrote it, nor any approval, gate PASS
or resume right. NOT_FOUND means only that no record is stored. Nothing here runs an action."""

from moneylab.runlog.store import load_evidence, store_evidence

__all__ = ["load_evidence", "store_evidence"]
