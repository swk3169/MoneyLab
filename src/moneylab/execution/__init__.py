"""Execution (interface only). NO live implementation exists in v0.1.

A future live implementation must:
  * load credentials only from the environment / OS keystore, never from code,
  * never log keys, signatures or seed phrases,
  * require an explicit opt-in flag plus RiskCheck approval for every order,
  * provide a kill switch.
"""

from moneylab.execution.base import ExecutionClient, OrderRequest

__all__ = ["ExecutionClient", "OrderRequest"]
