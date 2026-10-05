"""PnL report types and the strategy adoption rule."""

from __future__ import annotations

from dataclasses import asdict, dataclass

EPS = 1e-6


@dataclass(frozen=True)
class PnLBreakdown:
    spread_captured: float
    slippage: float
    inventory_pnl: float
    taker_fees: float
    maker_fees: float
    estimated_maker_rebate: float
    realized_maker_rebate: float
    estimated_liquidity_reward: float
    realized_liquidity_reward: float
    cash_identity_check: float  # trade cash flows + positions * marks; must equal gross_trading_pnl

    @property
    def gross_trading_pnl(self) -> float:
        return self.spread_captured - self.slippage + self.inventory_pnl

    trading_pnl = gross_trading_pnl

    @property
    def trading_costs(self) -> float:
        """Explicit costs outside gross PnL (fees). Slippage is already inside gross."""
        return self.taker_fees + self.maker_fees

    @property
    def net_trading_pnl_after_cost(self) -> float:
        return self.gross_trading_pnl - self.trading_costs

    @property
    def all_in_realized_pnl(self) -> float:
        """Net trading PnL + incentives actually paid. Estimates are never included."""
        return self.net_trading_pnl_after_cost + self.realized_maker_rebate + self.realized_liquidity_reward

    @property
    def all_in_estimated_pnl(self) -> float:
        """INFORMATIONAL ONLY: includes unconfirmed incentive estimates."""
        return self.net_trading_pnl_after_cost + self.estimated_maker_rebate + self.estimated_liquidity_reward

    @property
    def identity_holds(self) -> bool:
        return abs(self.gross_trading_pnl - self.cash_identity_check) < EPS

    def rows(self) -> list[tuple[str, float]]:
        return [
            ("spread_captured", self.spread_captured),
            ("slippage (cost)", 0.0 - self.slippage),
            ("inventory_pnl", self.inventory_pnl),
            ("gross_trading_pnl", self.gross_trading_pnl),
            ("taker_fees", 0.0 - self.taker_fees),
            ("maker_fees", 0.0 - self.maker_fees),
            ("net_trading_pnl_after_cost", self.net_trading_pnl_after_cost),
            ("estimated_maker_rebate", self.estimated_maker_rebate),
            ("realized_maker_rebate", self.realized_maker_rebate),
            ("estimated_liquidity_reward", self.estimated_liquidity_reward),
            ("realized_liquidity_reward", self.realized_liquidity_reward),
            ("all_in_realized_pnl", self.all_in_realized_pnl),
            ("all_in_estimated_pnl (info only)", self.all_in_estimated_pnl),
        ]

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(
            gross_trading_pnl=self.gross_trading_pnl,
            net_trading_pnl_after_cost=self.net_trading_pnl_after_cost,
            all_in_realized_pnl=self.all_in_realized_pnl,
            all_in_estimated_pnl=self.all_in_estimated_pnl,
        )
        return d


@dataclass(frozen=True)
class AdoptionVerdict:
    status: str  # "REJECT" | "INSUFFICIENT_EVIDENCE" | "CANDIDATE"
    reasons: tuple[str, ...]

    @property
    def adopt(self) -> bool:
        return self.status == "CANDIDATE"


def evaluate_adoption(
    breakdown: PnLBreakdown, n_trades: int, synthetic_data: bool, min_trades: int = 100
) -> AdoptionVerdict:
    """Adoption rule: the strategy must survive WITHOUT incentives.

    * net_trading_pnl_after_cost <= 0 -> REJECT, whatever the rebates/rewards say.
    * synthetic data or too few trades -> INSUFFICIENT_EVIDENCE (never CANDIDATE).
    """
    reasons: list[str] = []
    net = breakdown.net_trading_pnl_after_cost
    if net <= 0:
        reasons.append(f"net_trading_pnl_after_cost={net:.4f} <= 0 (incentives excluded)")
        if breakdown.all_in_estimated_pnl > 0:
            reasons.append("positive only with estimated incentives - not accepted")
        return AdoptionVerdict("REJECT", tuple(reasons))
    if synthetic_data:
        reasons.append("synthetic fixture data is not evidence of profitability")
    if n_trades < min_trades:
        reasons.append(f"only {n_trades} trades (< {min_trades})")
    if reasons:
        return AdoptionVerdict("INSUFFICIENT_EVIDENCE", tuple(reasons))
    return AdoptionVerdict("CANDIDATE", ("net trading PnL after cost > 0 without incentives",))
