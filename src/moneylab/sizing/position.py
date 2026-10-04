"""Position sizing: capped fractional Kelly (pure functions).

Kelly for buying a binary share at all-in price P (fees included) with probability q:
    f* = (q - P) / (1 - P)        fraction of equity to stake
We stake kelly_fraction * f* (default 0.25, never more than 1.0) and then apply hard caps.
Probability estimates are noisy; full Kelly on a wrong q is ruinous.

Caps (smallest wins; the binding one is reported):
  max_position_per_market   notional USDC per market after the trade
  max_portfolio_exposure    notional USDC across all markets after the trade
  order-book depth          depth_fraction * shares available up to the limit price
  inventory limit           |net YES delta| per market (shares)
  daily loss limit          no new risk once today's PnL <= -limit
  max drawdown limit        no new risk once drawdown from peak >= limit
edge <= 0 (after fees) -> size 0, always.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from moneylab.risk.inventory import inventory_room

DEFAULT_KELLY_FRACTION = 0.25


@dataclass(frozen=True)
class SizingLimits:
    kelly_fraction: float = DEFAULT_KELLY_FRACTION
    max_position_per_market: float = 200.0  # USDC notional
    max_portfolio_exposure: float = 600.0  # USDC notional
    depth_fraction: float = 0.5  # of visible depth up to the limit price
    max_inventory_shares: float = 400.0  # |net YES delta| per market
    daily_loss_limit: float = 50.0  # USDC
    max_drawdown: float = 0.20  # fraction of peak equity
    size_increment: float = 0.01  # shares are floored to this

    def __post_init__(self):
        if not 0 < self.kelly_fraction <= 1.0:
            raise ValueError("kelly_fraction must be in (0, 1]")


@dataclass(frozen=True)
class PortfolioState:
    equity: float
    peak_equity: float
    daily_pnl: float = 0.0
    market_exposure: Mapping[str, float] = field(default_factory=dict)  # market -> USDC notional
    net_delta: Mapping[str, float] = field(default_factory=dict)  # market -> YES-equivalent shares

    @property
    def total_exposure(self) -> float:
        return sum(self.market_exposure.values())

    @property
    def drawdown(self) -> float:
        return (self.peak_equity - self.equity) / self.peak_equity if self.peak_equity > 0 else 0.0


@dataclass(frozen=True)
class SizingDecision:
    size: float
    binding: str  # which rule set the size ("kelly", "depth", ..., or a rejection reason)
    kelly_size: float | None = None

    @property
    def ok(self) -> bool:
        return self.size > 0


def kelly_fraction_binary(prob: float, all_in_price: float) -> float:
    """Full-Kelly stake fraction for buying a binary share. 0 if there is no edge."""
    if all_in_price >= 1.0 or prob <= all_in_price:
        return 0.0
    return (prob - all_in_price) / (1.0 - all_in_price)


def _floor(x: float, inc: float) -> float:
    return math.floor(x / inc + 1e-9) * inc if x > 0 else 0.0


def _caps(
    market_id: str, price: float, delta_direction: float, available_depth: float,
    state: PortfolioState, limits: SizingLimits,
) -> dict[str, float]:
    exposure = state.market_exposure.get(market_id, 0.0)
    return {
        "max_position_per_market": max(limits.max_position_per_market - exposure, 0.0) / price,
        "max_portfolio_exposure": max(limits.max_portfolio_exposure - state.total_exposure, 0.0) / price,
        "depth": limits.depth_fraction * available_depth,
        "inventory": inventory_room(state.net_delta.get(market_id, 0.0), delta_direction, limits.max_inventory_shares),
    }


def _gate(state: PortfolioState, limits: SizingLimits) -> str | None:
    if state.daily_pnl <= -limits.daily_loss_limit:
        return "daily_loss_limit"
    if state.drawdown >= limits.max_drawdown:
        return "max_drawdown"
    return None


def _finish(target: float, caps: dict[str, float], first: str, min_order_size: float, limits: SizingLimits, kelly: float | None) -> SizingDecision:
    binding, size = first, target
    for name, cap in caps.items():
        if cap < size:
            binding, size = name, cap
    size = _floor(size, limits.size_increment)
    if size <= 0:
        return SizingDecision(0.0, binding, kelly)
    if size < min_order_size:
        return SizingDecision(0.0, f"below_min_order_size({binding})", kelly)
    return SizingDecision(size, binding, kelly)


def size_directional(
    market_id: str, prob: float, all_in_price: float, available_depth: float,
    state: PortfolioState, limits: SizingLimits, delta_direction: float = 1.0, min_order_size: float = 0.0,
) -> SizingDecision:
    """Shares to buy for a directional bet. delta_direction: +1 buying YES, -1 buying NO."""
    if prob - all_in_price <= 0:
        return SizingDecision(0.0, "no_edge")
    gate = _gate(state, limits)
    if gate:
        return SizingDecision(0.0, gate)
    f = kelly_fraction_binary(prob, all_in_price) * limits.kelly_fraction
    kelly_shares = f * state.equity / all_in_price
    caps = _caps(market_id, all_in_price, delta_direction, available_depth, state, limits)
    return _finish(kelly_shares, caps, "kelly", min_order_size, limits, kelly_shares)


def size_capped(
    market_id: str, desired: float, price: float, edge_per_share: float, available_depth: float,
    state: PortfolioState, limits: SizingLimits, delta_direction: float = 0.0, min_order_size: float = 0.0,
) -> SizingDecision:
    """Caps only, no Kelly: for arbitrage legs (delta_direction=0) and maker quotes.

    Maker quotes pass the strategy's expected edge; edge <= 0 still means no order.
    """
    if edge_per_share <= 0:
        return SizingDecision(0.0, "no_edge")
    gate = _gate(state, limits)
    if gate:
        return SizingDecision(0.0, gate)
    caps = _caps(market_id, price, delta_direction, available_depth, state, limits)
    if delta_direction == 0:
        caps.pop("inventory")
    return _finish(desired, caps, "requested", min_order_size, limits, None)
