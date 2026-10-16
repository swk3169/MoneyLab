"""Trading cost model (BT-1, extended in BT-2a; docs/backtest_design.md section 7,
docs/backtest_bt2_review.md sections A and B). All values are ASSUMED.

Per trade (one leg), with reference price P (the bar price the fill is approximated by), fee f,
spread+slippage kappa and market impact iota (fractions):
  sell  quantity Q:   effective price = P(1 - kappa - iota);  notional = Q*P(1 - kappa - iota)
                      fee = notional * f;  proceeds = notional - fee
  buy, fee_basis "inclusive" (default; the v0.6 draft section 7 rule), spend cash K:
                      fee = K*f;  N = K - fee is exchanged;  effective price = P/(1 - kappa - iota)
                      quantity = N(1 - kappa - iota)/P
  buy, fee_basis "on_top" (the fee is charged on top of the exchanged amount):
                      N = K/(1 + f);  fee = K - N;  quantity as above
Price costs, valued at P: spread+slippage = N*kappa (buy) or Q*P*kappa (sell); impact likewise with iota.
A leg therefore multiplies wealth (valued at P) by (1-f)(1-kappa-iota) ("inclusive" buy, every sell)
or (1-kappa-iota)/(1+f) ("on_top" buy). The fee is charged once, on the cash actually exchanged; kappa
and iota only move the price; there is no separate spread term (candles carry no bid/ask).

Market impact (draft section 7, ASSUMED): iota(C) = 1.0 bp * sqrt(C / 1,000,000 KRW) for planned
capital C. Above 10,000,000 KRW the assumption has no basis: CAPACITY_UNVERIFIED.

The Upbit account fee and how Upbit charges it are NOT confirmed: every cost model carries
fee_status FEE_UNCONFIRMED and label ASSUMED. Scenarios 0 / 5 / 15 / 25 bp per side.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext

FEE_STATUS_UNCONFIRMED = "FEE_UNCONFIRMED"
FEE_SCENARIOS_BPS = (0, 5, 15, 25)
FEE_BASES = ("inclusive", "on_top")
COST_LABEL = "ASSUMED"
PRECISION = 50  # Decimal digits for cost arithmetic
BP = Decimal(10000)
IMPACT_REF_BPS = Decimal(1)  # iota_ref, ASSUMED (v0.6 draft section 7)
IMPACT_REF_CAPITAL = Decimal(1_000_000)  # C_ref, KRW
CAPACITY_LIMIT = Decimal(10_000_000)  # above this, iota has no basis


def _bps(v: Decimal | int | str, name: str) -> Decimal:
    d = Decimal(v)
    if not d.is_finite() or d < 0 or d >= BP:
        raise ValueError(f"{name} must be in [0, 10000) bp, got {v!r}")
    return d


def impact_bps_for_capital(capital: Decimal, ref_bps: Decimal = IMPACT_REF_BPS,
                           ref_capital: Decimal = IMPACT_REF_CAPITAL,
                           limit: Decimal = CAPACITY_LIMIT) -> tuple[Decimal, bool]:
    """(iota in bp, capacity_verified). capacity_verified is False above `limit`. The defaults are the
    v0.6 draft assumption; configs/backtest_costs.toml carries the same values (backtest.settings)."""
    if not isinstance(capital, Decimal) or capital <= 0:
        raise ValueError("capital must be a positive Decimal (KRW)")
    if ref_bps < 0 or ref_capital <= 0 or limit <= 0:
        raise ValueError("impact reference values must be positive")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        iota = ref_bps * (capital / ref_capital).sqrt()
    return iota, capital <= limit


@dataclass(frozen=True)
class LegCost:
    side: str  # "buy" or "sell"
    ref_price: Decimal
    exec_price: Decimal
    quantity: Decimal
    cash_out: Decimal  # cash paid (buy, fee included) or 0
    cash_in: Decimal  # cash received (sell, after fee) or 0
    fee: Decimal
    slippage_cost: Decimal  # spread + slippage (kappa), valued at the reference price
    impact_cost: Decimal = Decimal(0)  # market impact (iota), valued at the reference price
    fee_basis: str = "inclusive"


@dataclass(frozen=True)
class CostModel:
    buy_fee_bps: Decimal
    sell_fee_bps: Decimal
    slippage_bps: Decimal  # kappa: spread + slippage per side
    fee_status: str = FEE_STATUS_UNCONFIRMED
    label: str = COST_LABEL
    impact_bps: Decimal = Decimal(0)  # iota per side
    fee_basis: str = "inclusive"

    def __post_init__(self) -> None:
        for name in ("buy_fee_bps", "sell_fee_bps", "slippage_bps", "impact_bps"):
            object.__setattr__(self, name, _bps(getattr(self, name), name))
        if self.slippage_bps + self.impact_bps >= BP:
            raise ValueError("slippage + impact must stay below 10000 bp")
        if self.fee_basis not in FEE_BASES:
            raise ValueError(f"fee_basis must be one of {FEE_BASES}")
        if self.fee_status != FEE_STATUS_UNCONFIRMED:
            raise ValueError("no Upbit account fee is confirmed; fee_status must stay FEE_UNCONFIRMED")
        if self.label != COST_LABEL:
            raise ValueError("costs are assumptions; label must stay ASSUMED")

    @classmethod
    def scenario(cls, fee_bps: int, slippage_bps: Decimal | int | str = 0, impact_bps: Decimal | int | str = 0,
                 fee_basis: str = "inclusive") -> CostModel:
        if fee_bps not in FEE_SCENARIOS_BPS:
            raise ValueError(f"fee scenario must be one of {FEE_SCENARIOS_BPS} bp")
        return cls(Decimal(fee_bps), Decimal(fee_bps), Decimal(slippage_bps), impact_bps=Decimal(impact_bps),
                   fee_basis=fee_basis)

    def to_dict(self) -> dict[str, str]:
        return {"buy_fee_bps": str(self.buy_fee_bps), "sell_fee_bps": str(self.sell_fee_bps),
                "slippage_bps": str(self.slippage_bps), "impact_bps": str(self.impact_bps),
                "fee_basis": self.fee_basis, "fee_status": self.fee_status, "label": self.label}

    def buy(self, cash: Decimal, ref_price: Decimal) -> LegCost:
        """Spend all of `cash` (fee included) at the reference price."""
        if cash <= 0 or ref_price <= 0:
            raise ValueError("buy needs positive cash and price")
        with localcontext() as ctx:
            ctx.prec = PRECISION
            f = self.buy_fee_bps / BP
            k, i = self.slippage_bps / BP, self.impact_bps / BP
            if self.fee_basis == "inclusive":
                fee = cash * f
                exchanged = cash - fee
            else:
                exchanged = cash / (1 + f)
                fee = cash - exchanged
            exec_price = ref_price / (1 - k - i)
            quantity = exchanged / exec_price
            slippage_cost = exchanged * k
            impact_cost = exchanged * i
        return LegCost("buy", ref_price, exec_price, quantity, cash, Decimal(0), fee, slippage_cost, impact_cost,
                       self.fee_basis)

    def sell(self, quantity: Decimal, ref_price: Decimal) -> LegCost:
        """Sell all of `quantity` at the reference price."""
        if quantity <= 0 or ref_price <= 0:
            raise ValueError("sell needs positive quantity and price")
        with localcontext() as ctx:
            ctx.prec = PRECISION
            f = self.sell_fee_bps / BP
            k, i = self.slippage_bps / BP, self.impact_bps / BP
            exec_price = ref_price * (1 - k - i)
            notional = quantity * exec_price
            fee = notional * f
            proceeds = notional - fee
            slippage_cost = quantity * ref_price * k
            impact_cost = quantity * ref_price * i
        return LegCost("sell", ref_price, exec_price, quantity, Decimal(0), proceeds, fee, slippage_cost, impact_cost,
                       self.fee_basis)
