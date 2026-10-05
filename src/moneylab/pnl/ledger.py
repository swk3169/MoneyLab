"""Fills -> positions -> PnL decomposition. Same code for paper and (future) live fills.

For each fill i: sign s (+1 buy, -1 sell), shares c, price x, reference mid m, top-of-book t,
and the final mark / settlement value M of that token:

    spread_captured   = sum_maker s*c*(m - x) + sum_taker s*c*(m - t)   (taker part <= 0)
    slippage          = sum_taker s*c*(x - t)                           (cost, >= 0)
    inventory_pnl     = sum s*c*(M - m)                                 (< 0 = inventory loss)
    gross_trading_pnl = spread_captured - slippage + inventory_pnl
                      == trade cash flows + positions * M               (exact identity)
    net_trading_pnl_after_cost = gross_trading_pnl - taker_fees - maker_fees

Incentives are tracked separately and never mixed into trading PnL:
    estimated_maker_rebate / estimated_liquidity_reward   model outputs (simulation)
    realized_maker_rebate  / realized_liquidity_reward    only from confirmed payouts
    all_in_realized_pnl = net_trading_pnl_after_cost + realized rebates + realized rewards
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field

from moneylab.execution.base import Fill
from moneylab.pnl.report import PnLBreakdown

EPS = 1e-9


@dataclass
class _Lot:
    qty: float
    price: float
    fee_per_share: float
    group: str


@dataclass
class _TokenBook:
    shares: float = 0.0
    sum_scm: float = 0.0  # sum of s*c*m over fills, for inventory PnL
    lots: deque = field(default_factory=deque)


class Ledger:
    def __init__(self, starting_cash: float):
        self.starting_cash = starting_cash
        self.trade_cash = 0.0  # -sum s*c*x (fees excluded)
        self.spread_captured = 0.0
        self.slippage = 0.0
        self.taker_fees = 0.0
        self.maker_fees = 0.0
        self.estimated_maker_rebate = 0.0
        self.estimated_liquidity_reward = 0.0
        self.realized_maker_rebate = 0.0
        self.realized_liquidity_reward = 0.0
        self.maker_fills = 0
        self.taker_fills = 0
        self.tokens: dict[str, _TokenBook] = {}
        self.group_pnl: dict[str, float] = {}
        self.group_open: dict[str, float] = {}
        self.settled: dict[str, float] = {}
        self.equity_curve: list[tuple[float, float]] = []

    def _tb(self, token_id: str) -> _TokenBook:
        return self.tokens.setdefault(token_id, _TokenBook())

    # --- fills ----------------------------------------------------------------
    def record_fill(self, fill: Fill, rebate_rate: float = 0.0) -> None:
        s, c, x, m = fill.sign, fill.size, fill.price, fill.mid_ref
        tb = self._tb(fill.token_id)
        self.trade_cash -= s * c * x
        tb.shares += s * c
        tb.sum_scm += s * c * m
        if fill.liquidity == "maker":
            self.maker_fills += 1
            self.spread_captured += s * c * (m - x)
            self.maker_fees += fill.fee
            self.estimated_maker_rebate += rebate_rate * fill.fee_equivalent
        else:
            self.taker_fills += 1
            self.spread_captured += s * c * (m - fill.top_ref)
            self.slippage += s * c * (x - fill.top_ref)
            self.taker_fees += fill.fee
        self._lots(fill)

    def _lots(self, fill: Fill) -> None:
        tb = self._tb(fill.token_id)
        fps = fill.fee / fill.size if fill.size > 0 else 0.0
        group = fill.group_id or fill.order_id
        if fill.side == "buy":
            tb.lots.append(_Lot(fill.size, fill.price, fps, group))
            self.group_open[group] = self.group_open.get(group, 0.0) + fill.size
            self.group_pnl.setdefault(group, 0.0)
            return
        remaining = fill.size
        while remaining > EPS and tb.lots:
            lot = tb.lots[0]
            q = min(lot.qty, remaining)
            self.group_pnl[lot.group] += (fill.price - lot.price - lot.fee_per_share - fps) * q
            self.group_open[lot.group] -= q
            lot.qty -= q
            remaining -= q
            if lot.qty <= EPS:
                tb.lots.popleft()

    def settle(self, payouts: Mapping[str, float], timestamp: float) -> None:
        """Resolution: every share of token t is redeemed at payouts[t] (no fee assumed)."""
        for token_id, value in payouts.items():
            tb = self.tokens.get(token_id)
            self.settled[token_id] = value
            if tb is None or abs(tb.shares) <= EPS:
                continue
            qty = tb.shares
            pseudo = Fill(
                order_id=f"settle-{token_id}", market_id="", token_id=token_id, side="sell", price=value,
                size=qty, liquidity="maker", fee=0.0, mid_ref=value, top_ref=value, timestamp=timestamp,
            )
            # Settlement is not a trade: book it without touching maker/taker counters.
            self.trade_cash += qty * value
            tb.shares -= qty
            tb.sum_scm -= qty * value
            self._lots(pseudo)

    # --- incentives -----------------------------------------------------------
    def add_estimated_liquidity_reward(self, amount: float) -> None:
        self.estimated_liquidity_reward += amount

    def record_realized_maker_rebate(self, amount: float) -> None:
        """Only for payouts confirmed by the venue (e.g. GET /rebates/current)."""
        self.realized_maker_rebate += amount

    def record_realized_liquidity_reward(self, amount: float) -> None:
        """Only for payouts confirmed by the venue (rewards earnings endpoints)."""
        self.realized_liquidity_reward += amount

    # --- valuation ------------------------------------------------------------
    def _mark(self, token_id: str, marks: Mapping[str, float]) -> float:
        if token_id in self.settled:
            return self.settled[token_id]
        return marks.get(token_id, 0.0)

    def positions(self) -> dict[str, float]:
        return {t: tb.shares for t, tb in self.tokens.items()}

    def trading_equity(self, marks: Mapping[str, float]) -> float:
        """Cash after trades and fees + positions at marks. Excludes every incentive."""
        pos_value = sum(tb.shares * self._mark(t, marks) for t, tb in self.tokens.items())
        return self.starting_cash + self.trade_cash - self.taker_fees - self.maker_fees + pos_value

    def mark(self, timestamp: float, marks: Mapping[str, float]) -> float:
        eq = self.trading_equity(marks)
        self.equity_curve.append((timestamp, eq))
        return eq

    def breakdown(self, marks: Mapping[str, float]) -> PnLBreakdown:
        inventory = sum(tb.shares * self._mark(t, marks) - tb.sum_scm for t, tb in self.tokens.items())
        return PnLBreakdown(
            spread_captured=self.spread_captured,
            slippage=self.slippage,
            inventory_pnl=inventory,
            taker_fees=self.taker_fees,
            maker_fees=self.maker_fees,
            estimated_maker_rebate=self.estimated_maker_rebate,
            realized_maker_rebate=self.realized_maker_rebate,
            estimated_liquidity_reward=self.estimated_liquidity_reward,
            realized_liquidity_reward=self.realized_liquidity_reward,
            cash_identity_check=self.trade_cash + sum(tb.shares * self._mark(t, marks) for t, tb in self.tokens.items()),
        )

    def trade_pnls(self, marks: Mapping[str, float] | None = None) -> tuple[list[float], int]:
        """Per-trade net PnL (taker/maker fees included, incentives excluded).

        A trade is a fill group (one order, or all legs sharing a group_id). Closed groups are
        final; if `marks` is given, still-open lots are valued at those marks and included.
        Returns (pnls, number_of_groups_marked_open).
        """
        pnl = dict(self.group_pnl)
        open_groups = {g for g, q in self.group_open.items() if q > EPS}
        if marks is None:
            return [v for g, v in pnl.items() if g not in open_groups], 0
        for t, tb in self.tokens.items():
            for lot in tb.lots:
                pnl[lot.group] += (self._mark(t, marks) - lot.price - lot.fee_per_share) * lot.qty
        return list(pnl.values()), len(open_groups)
