"""Inventory risk for binary markets (pure functions).

Holding NO is economically short YES: a YES+NO pair is worth exactly 1 at resolution
(and can be merged), so only the net YES delta carries outcome risk.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryRisk:
    yes_shares: float
    no_shares: float
    net_delta: float  # yes - no (YES-equivalent shares)
    paired_shares: float  # min(yes, no): worth 1.0 each at resolution, no outcome risk
    mark_value: float  # yes * yes_mark + no * no_mark
    value_if_yes: float
    value_if_no: float
    worst_case_value: float
    worst_case_loss: float  # mark_value - worst_case_value (>= 0 for sane marks)
    gross_notional: float  # mark value of all shares held


def assess_binary_inventory(yes_shares: float, no_shares: float, yes_mark: float, no_mark: float | None = None) -> InventoryRisk:
    if no_mark is None:
        no_mark = 1.0 - yes_mark
    mark = yes_shares * yes_mark + no_shares * no_mark
    v_yes, v_no = yes_shares * 1.0, no_shares * 1.0
    worst = min(v_yes, v_no)
    return InventoryRisk(
        yes_shares=yes_shares,
        no_shares=no_shares,
        net_delta=yes_shares - no_shares,
        paired_shares=min(yes_shares, no_shares),
        mark_value=mark,
        value_if_yes=v_yes,
        value_if_no=v_no,
        worst_case_value=worst,
        worst_case_loss=mark - worst,
        gross_notional=mark,
    )


def reservation_price(fair: float, net_delta: float, skew_per_share: float, tick: float = 0.01) -> float:
    """Inventory-skewed fair value: fair - skew * delta, clipped to [tick, 1 - tick].

    Long YES -> lower reservation -> quotes move down -> more likely to sell, less to buy.
    (Linear simplification of Avellaneda-Stoikov's r = s - q * gamma * sigma^2 * (T - t).)
    """
    return min(max(fair - skew_per_share * net_delta, tick), 1.0 - tick)


def inventory_room(net_delta: float, side_delta: float, limit: float) -> float:
    """How many more shares may be added in the direction `side_delta` (+1 adds YES delta,
    -1 adds NO delta) before |net delta| would exceed `limit`. Reducing trades are unlimited."""
    if side_delta * net_delta < 0:  # reduces exposure first
        return abs(net_delta) + limit
    return max(limit - abs(net_delta), 0.0)
