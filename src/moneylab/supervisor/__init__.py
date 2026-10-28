"""MoneyLab Supervisor, first vertical slice (SUPERVISOR-01).

Deterministic, read-only and non-authoritative: from a trusted KnowledgeBase and one CE-02 ContextRequest it lists
candidate research problems as `moneylab.supervisor.proposal/1` documents, validates them and reports whether their
inputs are still current. It executes nothing and approves nothing. Proposal != Work Order != Authorization; the
Git-tracked knowledge records stay the only authority."""

from __future__ import annotations

from moneylab.supervisor.proposal import SupervisorError, check_proposal, propose, validate_proposal

__all__ = ["SupervisorError", "check_proposal", "propose", "validate_proposal"]
