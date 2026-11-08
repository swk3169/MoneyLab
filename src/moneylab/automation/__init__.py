"""Deterministic read-only automation MVP (AUTO-01).

`run_action(action_id)` runs the one registered offline action, `knowledge_validate`, with a fixed argv and returns
`moneylab.automation.evidence/1` canonical JSON. No queue, scheduler, loop, CLI, git change or gate approval."""

from moneylab.automation.executor import run_action
from moneylab.automation.policy import ACTION_KNOWLEDGE_VALIDATE, ALLOWED_ACTIONS, AutomationError

__all__ = ["ACTION_KNOWLEDGE_VALIDATE", "ALLOWED_ACTIONS", "AutomationError", "run_action"]
