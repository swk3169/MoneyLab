"""Simple trading cost model for BT-1 (docs/backtest_design.md section 7). All values are ASSUMED.

Per trade (one leg), with fee f and slippage s as fractions and reference price P (the bar close
the fill is approximated by):
  buy   spend cash K:  fee = K*f;  effective price = P/(1 - s);  quantity = K(1-f)(1-s)/P
        slippage cost (valued at P) = K(1-f)*s
  sell  quantity Q:    effective price = P(1 - s);  notional = Q*P(1-s);  fee = notional*f
        proceeds = Q*P(1-s)(1-f);  slippage cost (valued at P) = Q*P*s
So every leg multiplies wealth (valued at P) by exactly (1-f)(1-s), the rule of the v0.6 draft
section 7 with kappa = s and no market impact. Fee and slippage are separate ledger items and each
is charged once: the fee is taken on the cash actually exchanged, the slippage only moves the price.

The account fee is unknown: every result carries fee_status FEE_UNCONFIRMED and the costs are
labelled ASSUMED. Scenarios 0 / 5 / 15 / 25 bp per side are the sensitivity grid.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext

FEE_STATUS_UNCONFIRMED = "FEE_UNCONFIRMED"
FEE_SCENARIOS_BPS = (0, 5, 15, 25)
COST_LABEL = "ASSUMED"
PRECISION = 50  # Decimal digits for cost arithmetic
BP = Decimal(10000)


def _bps(v: Decimal | int | str, name: str) -> Decimal:
    d = Decimal(v)
    if not d.is_finite() or d < 0 or d >= BP:
        raise ValueError(f"{name} must be in [0, 10000) bp, got {v!r}")
    return d


@dataclass(frozen=True)
class LegCost:
    side: str  # "buy" or "sell"
    ref_price: Decimal
    exec_price: Decimal
    quantity: Decimal
    cash_out: Decimal  # cash paid (buy, fee included) or 0
    cash_in: Decimal  # cash received (sell, after fee) or 0
    fee: Decimal
    slippage_cost: Decimal


@dataclass(frozen=True)
class CostModel:
    buy_fee_bps: Decimal
    sell_fee_bps: Decimal
    slippage_bps: Decimal
    fee_status: str = FEE_STATUS_UNCONFIRMED
    label: str = COST_LABEL

    def __post_init__(self) -> None:
        for name in ("buy_fee_bps", "sell_fee_bps", "slippage_bps"):
            object.__setattr__(self, name, _bps(getattr(self, name), name))
        if self.fee_status != FEE_STATUS_UNCONFIRMED:
            raise ValueError("BT-1 has no confirmed account fee; fee_status must stay FEE_UNCONFIRMED")
        if self.label != COST_LABEL:
            raise ValueError("BT-1 costs are assumptions; label must stay ASSUMED")

    @classmethod
    def scenario(cls, fee_bps: int, slippage_bps: Decimal | int | str = 0) -> CostModel:
        if fee_bps not in FEE_SCENARIOS_BPS:
            raise ValueError(f"fee scenario must be one of {FEE_SCENARIOS_BPS} bp")
        return cls(Decimal(fee_bps), Decimal(fee_bps), Decimal(slippage_bps))

    def to_dict(self) -> dict[str, str]:
        return {"buy_fee_bps": str(self.buy_fee_bps), "sell_fee_bps": str(self.sell_fee_bps),
                "slippage_bps": str(self.slippage_bps), "fee_status": self.fee_status, "label": self.label}

    def buy(self, cash: Decimal, ref_price: Decimal) -> LegCost:
        """Spend all of `cash` (fee included) at the reference price."""
        if cash <= 0 or ref_price <= 0:
            raise ValueError("buy needs positive cash and price")
        with localcontext() as ctx:
            ctx.prec = PRECISION
            f, s = self.buy_fee_bps / BP, self.slippage_bps / BP
            fee = cash * f
            spend = cash - fee
            exec_price = ref_price / (1 - s)
            quantity = spend / exec_price
            slippage_cost = spend * s
        return LegCost("buy", ref_price, exec_price, quantity, cash, Decimal(0), fee, slippage_cost)

    def sell(self, quantity: Decimal, ref_price: Decimal) -> LegCost:
        """Sell all of `quantity` at the reference price."""
        if quantity <= 0 or ref_price <= 0:
            raise ValueError("sell needs positive quantity and price")
        with localcontext() as ctx:
            ctx.prec = PRECISION
            f, s = self.sell_fee_bps / BP, self.slippage_bps / BP
            exec_price = ref_price * (1 - s)
            notional = quantity * exec_price
            fee = notional * f
            proceeds = notional - fee
            slippage_cost = quantity * ref_price * s
        return LegCost("sell", ref_price, exec_price, quantity, Decimal(0), proceeds, fee, slippage_cost)
