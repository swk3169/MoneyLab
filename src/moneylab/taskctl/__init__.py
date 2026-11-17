"""taskctl: cooperative check-and-record tool for v1.4 Task Delegation (GOV-AUTOMATION-03).

`python -m moneylab.taskctl <command> --task-id T` keeps an append-only, hash-chained ledger under the ignored
`data/processed/taskctl/<T>/`, collects the worktree STATE itself and checks recorded fields against Git.

Limits (README §15): taskctl executes no work and cannot stop an agent from skipping a check, changing
state between a check and an action, or running tools directly. It cannot authenticate user messages; it only
checks that the fields the agent passes match the ledger and the worktree. Remote facts are agent-reported.
Atomic writes rely on hard links on a local volume; the hash chain detects accidental damage, not a
deliberate rewrite, and proves no approval. Exactly-once execution is not guaranteed. Output always carries
authority "NONE".
"""
