"""Non-authoritative work state snapshot and verify (AUTO-02).

`python -m moneylab.workstate snapshot` stores this worktree's Git and contract state under the ignored
`data/processed/workstate/<TASK_ID>/`; `verify` compares exactly one named snapshot with the current state.
A MATCH is not an approval, a gate PASS or a restored authorization, and says nothing about the history
between snapshots."""

from moneylab.workstate.collect import WorkstateError, collect_state

__all__ = ["WorkstateError", "collect_state"]
