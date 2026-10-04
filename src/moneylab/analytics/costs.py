"""Trading cost and maker-rebate models (pure functions).

Source: Polymarket docs "Fees" and "Maker Rebates Program" (checked 2026-10-04).
  fee            = C * feeRate * p * (1 - p)          C = shares, p = share price
  fee_equivalent = same formula, for each filled *maker* order
  rebate         = your_fee_equivalent / total_fee_equivalent * rebate_pool   (per market, daily)
  Fees are rounded to 5 decimals; the smallest fee charged is 0.00001 USDC.
  Makers are never charged fees (takerOnly=true on every documented category).

Rebate estimate (DERIVED, not documented): every fill has one taker and one maker side with
the same C and p, so the sum of maker fee_equivalents in a market equals the taker fees
collected there, and the pool is rebate_rate * taker fees. Therefore
    estimated_rebate ~= rebate_rate * your_fee_equivalent.
This is an *estimate*. It must never be booked as realized PnL until the payout is
confirmed (e.g. via GET /rebates/current). Daily payouts below $1 are not paid.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

from moneylab.domain.market_params import FeeSchedule

FEE_DECIMALS = Decimal("0.00001")
MIN_PAYOUT = 1.0  # rebates and liquidity rewards: amounts below $1/day are not paid


def round_fee(amount: float) -> float:
    """Round half-up to 5 decimals. Anything below 0.000005 becomes 0."""
    return float(Decimal(repr(amount)).quantize(FEE_DECIMALS, rounding=ROUND_HALF_UP))


def fee_curve(shares: float, price: float, schedule: FeeSchedule) -> float:
    """Unrounded C * rate * (p * (1 - p)) ** exponent."""
    if not schedule.enabled or schedule.rate <= 0 or shares <= 0:
        return 0.0
    if not 0.0 <= price <= 1.0:
        raise ValueError(f"price must be in [0, 1], got {price}")
    return abs(shares) * schedule.rate * (price * (1.0 - price)) ** schedule.exponent


def taker_fee(shares: float, price: float, schedule: FeeSchedule) -> float:
    """Fee in USDC a taker pays for one match at `price`."""
    return round_fee(fee_curve(shares, price, schedule))


def maker_fee(shares: float, price: float, schedule: FeeSchedule) -> float:
    """0 when fees are taker-only (all documented categories). takerOnly=false is unverified."""
    if schedule.taker_only:
        return 0.0
    return taker_fee(shares, price, schedule)


def taker_fee_for_fills(fills: Iterable[tuple[float, float]], schedule: FeeSchedule) -> float:
    """Sum of per-level fees for [(price, shares), ...] (each level treated as one match)."""
    return sum(taker_fee(size, price, schedule) for price, size in fills)


def fee_equivalent(shares: float, price: float, schedule: FeeSchedule) -> float:
    """Maker-side fee equivalent used to weight rebates (unrounded)."""
    return fee_curve(shares, price, schedule)


def estimated_maker_rebate(fee_equivalents: Iterable[float], schedule: FeeSchedule) -> float:
    """rebate_rate * sum(fee_equivalent). ESTIMATE ONLY - see module docstring."""
    if not schedule.enabled:
        return 0.0
    return schedule.rebate_rate * sum(fee_equivalents)


def apply_payout_threshold(amount: float, minimum: float = MIN_PAYOUT) -> float:
    """Daily payouts below `minimum` are not paid."""
    return amount if amount >= minimum else 0.0
