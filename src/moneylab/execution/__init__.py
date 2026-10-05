"""Execution (interface only). NO live implementation exists.

The only implementation is the paper engine (moneylab.paper.engine). A future live
implementation is described in docs/live_execution_design.md and must:
  * load credentials only from the environment / OS keystore, never from code,
  * never log keys, signatures or seed phrases,
  * require an explicit opt-in flag plus RiskCheck approval for every order,
  * provide a kill switch.
"""

from moneylab.execution.base import ExecutionClient, Fill, OrderRequest

__all__ = ["ExecutionClient", "Fill", "OrderRequest"]
