"""Round trips of a research-mode ledger: KRW net P&L, Profit Factor, win rate (BT-2b-4; bt-metrics/2).

Engine facts this module relies on (backtest.portfolio.simulate, backtest.costs, backtest.ledger.verify):
  * a buy spends all cash and a sell sells the whole quantity: no partial fills
  * legs alternate buy, sell, buy, ... (a buy is only ordered from cash, a sell only from a position)
  * the run ends flat: the last step sells an open position (TradeRow.virtual = True, fill_kind
    "primary" or "virtual_fallback")
A round trip is one buy leg and the next sell leg. Its net P&L is sell.cash_after - buy.cash_before (KRW):
every fee, slippage and impact of both legs is inside. Outcomes: win > 0, loss < 0, zero = 0 (exact Decimal).

Views: completed_only (round trips closed by a real sell) and including_virtual_close (also the forced
close at the end). Win rate = wins / all round trips of the view (zeros included). Profit Factor =
sum of wins / |sum of losses|; None with a reason when there is no loss or no round trip (never Infinity).

Invariant (exact): cash only changes through trades and each buy starts from the previous sell's cash, so
sum(net P&L, including_virtual_close) = final equity - initial cash. For completed_only the sum equals
final equity - initial cash - (P&L of the virtual-close round trips).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any

from moneylab.backtest.ledger import Ledger
from moneylab.backtest.performance import value
from moneylab.domain.bars import utc_iso

INVARIANT_PRECISION = 100  # sums of 50-digit ledger values stay exact


class RoundTripError(ValueError):
    """The ledger does not have the alternating buy / sell structure of the engine."""


@dataclass(frozen=True)
class RoundTrip:
    entry_leg: int
    exit_leg: int
    entry_time: Any
    exit_time: Any
    entry_price: Decimal
    exit_price: Decimal
    entry_cash: Decimal  # buy.cash_before
    exit_cash: Decimal  # sell.cash_after
    virtual_close: bool
    exit_fill_kind: str

    @property
    def net_pnl(self) -> Decimal:
        with localcontext() as ctx:
            ctx.prec = INVARIANT_PRECISION
            return self.exit_cash - self.entry_cash

    @property
    def outcome(self) -> str:
        p = self.net_pnl
        return "win" if p > 0 else "loss" if p < 0 else "zero"


def pair_round_trips(ledger: Ledger) -> tuple[list[RoundTrip], bool]:
    """(round trips, open position at the end). Refuses a ledger that is not buy, sell, buy, sell, ..."""
    legs = ledger.trades
    out: list[RoundTrip] = []
    for i in range(0, len(legs), 2):
        buy = legs[i]
        if buy.side != "buy":
            raise RoundTripError(f"leg {buy.leg} is a {buy.side}, expected a buy (legs must alternate)")
        if i + 1 == len(legs):
            return out, True
        sell = legs[i + 1]
        if sell.side != "sell":
            raise RoundTripError(f"leg {sell.leg} is a {sell.side}, expected a sell (legs must alternate)")
        if buy.qty_before != 0 or sell.qty_after != 0 or sell.quantity != buy.qty_after:
            raise RoundTripError(f"legs {buy.leg}/{sell.leg} are not one full position (partial fill?)")
        out.append(RoundTrip(buy.leg, sell.leg, buy.fill_time, sell.fill_time, buy.ref_price, sell.ref_price,
                             buy.cash_before, sell.cash_after, sell.virtual, sell.fill_kind))
    return out, False


def view_stats(rts: list[RoundTrip]) -> dict[str, Any]:
    with localcontext() as ctx:
        ctx.prec = INVARIANT_PRECISION
        wins = [rt.net_pnl for rt in rts if rt.outcome == "win"]
        losses = [rt.net_pnl for rt in rts if rt.outcome == "loss"]
        profit = sum(wins, Decimal(0))
        loss = -sum(losses, Decimal(0))
        if not rts:
            pf = value(None, "no_round_trips")
        elif loss == 0:
            pf = value(None, "no_losing_round_trips" if profit > 0 else "no_profit_and_no_loss")
        else:
            pf = value(float(profit / loss))
        total = sum((rt.net_pnl for rt in rts), Decimal(0))
    return {
        "count": len(rts),
        "wins": len(wins),
        "losses": len(losses),
        "zeros": len(rts) - len(wins) - len(losses),
        "win_rate": value(len(wins) / len(rts)) if rts else value(None, "no_round_trips"),
        "profit_factor": pf,
        "gross_profit_krw": str(profit),
        "gross_loss_krw": str(loss),
        "net_pnl_krw": str(total),
    }


def round_trip_report(ledger: Ledger) -> dict[str, Any]:
    rts, open_at_end = pair_round_trips(ledger)
    completed = [rt for rt in rts if not rt.virtual_close]
    with localcontext() as ctx:
        ctx.prec = INVARIANT_PRECISION
        total = sum((rt.net_pnl for rt in rts), Decimal(0))
        virtual = sum((rt.net_pnl for rt in rts if rt.virtual_close), Decimal(0))
        change = ledger.daily[-1].equity - ledger.initial_cash if ledger.daily else Decimal(0)
        if open_at_end:
            invariant = {"holds": None, "reason": "open_position_at_end", "final_minus_initial": str(change)}
        else:
            invariant = {"holds": total == change, "reason": None,
                         "sum_net_pnl_including_virtual": str(total), "final_minus_initial": str(change),
                         "sum_net_pnl_completed_only": str(total - virtual),
                         "virtual_close_net_pnl": str(virtual)}
    return {
        "unit": "KRW",
        "count": len(rts),
        "virtual_close_count": len(rts) - len(completed),
        "open_position_at_end": open_at_end,
        "rows": [{"entry_leg": rt.entry_leg, "exit_leg": rt.exit_leg, "entry_time": utc_iso(rt.entry_time),
                  "exit_time": utc_iso(rt.exit_time), "entry_price": str(rt.entry_price),
                  "exit_price": str(rt.exit_price), "virtual_close": rt.virtual_close,
                  "exit_fill_kind": rt.exit_fill_kind, "net_pnl_krw": str(rt.net_pnl), "outcome": rt.outcome}
                 for rt in rts],
        "views": {"completed_only": view_stats(completed), "including_virtual_close": view_stats(rts)},
        "invariant": invariant,
    }
