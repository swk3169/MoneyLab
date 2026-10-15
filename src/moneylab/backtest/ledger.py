"""Trade ledger and daily valuations with accounting invariants (BT-1).

Every trade row keeps the cash and quantity before and after the leg, the fee and the slippage cost
as separate items, and the equity valued at the leg's reference price before and after. `verify`
checks, for every row:
  cash >= 0, quantity >= 0                         (no shorting, no leverage, no overdraft)
  equity = cash + quantity * price                 (valuation identity, before and after)
  equity_after = equity_before - fee - slippage - impact   (each cost charged exactly once)
and for every daily valuation: equity = cash + quantity * price and the holdings equal those left
by the last FILLED trade (an unfilled order never changes cash or quantity).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, localcontext

from moneylab.backtest.costs import PRECISION, LegCost

# Relative tolerance of the Decimal identities (50-digit arithmetic, so far below one KRW).
TOLERANCE = Decimal("1e-30")


class AccountingError(AssertionError):
    """An accounting invariant does not hold."""


@dataclass(frozen=True)
class TradeRow:
    leg: int
    side: str
    day: datetime  # signal day D
    signal_time: datetime
    order_time: datetime
    fill_time: datetime
    fill_bar_start: datetime
    ref_price: Decimal
    exec_price: Decimal
    quantity: Decimal
    fee: Decimal
    slippage_cost: Decimal
    cash_before: Decimal
    cash_after: Decimal
    qty_before: Decimal
    qty_after: Decimal
    virtual: bool = False  # forced exit at the end of the evaluation range
    impact_cost: Decimal = Decimal(0)  # market impact, separate from fee and slippage (BT-2a)
    scenario: str = "E0"
    fill_kind: str = "primary"  # primary / substituted / virtual_fallback
    fee_basis: str = "inclusive"


@dataclass(frozen=True)
class UnfilledRow:
    day: datetime
    order_time: datetime
    side: str
    reason: str


@dataclass(frozen=True)
class DailyRow:
    ref_time: datetime
    price: Decimal
    price_source: str  # "fill_bar" or "last_close" (fallback when the fill bar is missing)
    position: int
    cash: Decimal
    quantity: Decimal
    equity_before_trade: Decimal
    equity: Decimal  # after any trade at ref_time


def _close(a: Decimal, b: Decimal) -> bool:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        scale = max(abs(a), abs(b), Decimal(1))
        return abs(a - b) <= TOLERANCE * scale


@dataclass
class Ledger:
    initial_cash: Decimal
    trades: list[TradeRow] = field(default_factory=list)
    unfilled: list[UnfilledRow] = field(default_factory=list)  # one row per failed fill attempt
    cancelled: list[UnfilledRow] = field(default_factory=list)  # pending orders withdrawn (never filled)
    daily: list[DailyRow] = field(default_factory=list)

    def add_trade(self, *, leg: LegCost, day: datetime, signal_time: datetime, order_time: datetime,
                  fill_time: datetime, fill_bar_start: datetime, cash_before: Decimal, qty_before: Decimal,
                  virtual: bool = False, scenario: str = "E0", fill_kind: str = "primary") -> TradeRow:
        with localcontext() as ctx:
            ctx.prec = PRECISION
            if leg.side == "buy":
                cash_after, qty_after = cash_before - leg.cash_out, qty_before + leg.quantity
            else:
                cash_after, qty_after = cash_before + leg.cash_in, qty_before - leg.quantity
        row = TradeRow(len(self.trades), leg.side, day, signal_time, order_time, fill_time, fill_bar_start,
                       leg.ref_price, leg.exec_price, leg.quantity, leg.fee, leg.slippage_cost,
                       cash_before, cash_after, qty_before, qty_after, virtual, leg.impact_cost, scenario,
                       fill_kind, leg.fee_basis)
        self._check_trade(row)
        self.trades.append(row)
        return row

    def add_daily(self, row: DailyRow) -> None:
        self._check_daily(row)
        self.daily.append(row)

    @staticmethod
    def _check_trade(r: TradeRow) -> None:
        if r.cash_after < 0 or r.qty_after < 0 or r.cash_before < 0 or r.qty_before < 0:
            raise AccountingError(f"leg {r.leg}: negative cash or quantity")
        if r.fee < 0 or r.slippage_cost < 0 or r.impact_cost < 0:
            raise AccountingError(f"leg {r.leg}: negative cost")
        if not (r.signal_time < r.order_time < r.fill_time):
            raise AccountingError(f"leg {r.leg}: signal, order and fill times are not strictly ordered")
        with localcontext() as ctx:
            ctx.prec = PRECISION
            before = r.cash_before + r.qty_before * r.ref_price
            after = r.cash_after + r.qty_after * r.ref_price
            if not _close(after, before - r.fee - r.slippage_cost - r.impact_cost):
                raise AccountingError(f"leg {r.leg}: equity_after {after} != equity_before {before}"
                                      " - fee - slippage - impact")

    @staticmethod
    def _check_daily(d: DailyRow) -> None:
        if d.cash < 0 or d.quantity < 0:
            raise AccountingError(f"{d.ref_time}: negative cash or quantity")
        with localcontext() as ctx:
            ctx.prec = PRECISION
            if not _close(d.equity, d.cash + d.quantity * d.price):
                raise AccountingError(f"{d.ref_time}: equity != cash + quantity * price")

    def verify(self) -> None:
        """Re-check every row and that holdings only change through filled trades."""
        cash, qty = self.initial_cash, Decimal(0)
        trades = iter(self.trades)
        pending = next(trades, None)
        for d in self.daily:
            while pending is not None and pending.fill_time <= d.ref_time:
                self._check_trade(pending)
                if pending.cash_before != cash or pending.qty_before != qty:
                    raise AccountingError(f"leg {pending.leg}: does not start from the previous holdings")
                cash, qty = pending.cash_after, pending.qty_after
                pending = next(trades, None)
            self._check_daily(d)
            if d.cash != cash or d.quantity != qty:
                raise AccountingError(f"{d.ref_time}: holdings differ from the filled trades")
            if d.position != (1 if qty > 0 else 0):
                raise AccountingError(f"{d.ref_time}: position flag does not match the quantity")
        if pending is not None:
            raise AccountingError("trades after the last daily valuation")
