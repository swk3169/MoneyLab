"""Paper execution engine: simulated orders against order-book snapshots. No funds, no network.

* Marketable orders (taker) walk the current book up to the limit price, VWAP-filled, taker fee
  per level. Liquidity consumed in a snapshot is not reused within that snapshot.
* Resting orders (maker) are filled by a MakerFillModel when a *later* snapshot arrives
  (default: conservative trade-through). Fill price = our limit price.
* No shorting: sells need inventory. Buys need cash (open bids reserve cash).
* Limitation: our trades do not change the following snapshots (no market impact replay).
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass

from moneylab.analytics.costs import fee_equivalent, maker_fee, taker_fee_for_fills
from moneylab.domain.market_params import MarketParams
from moneylab.domain.orderbook import BookSnapshot, OrderBook
from moneylab.execution.base import ExecutionClient, Fill, OrderRequest
from moneylab.paper.fill_models import Liquidity, MakerFillModel, TradeThroughFillModel
from moneylab.strategy.context import on_tick

log = logging.getLogger(__name__)
EPS = 1e-9


class OrderRejected(ValueError):
    """Paper order failed validation (never placed)."""


@dataclass
class RestingOrder:
    order_id: str
    request: OrderRequest
    remaining: float
    placed_at: float
    ref_mid: float  # last mid observed while resting -> spread-captured reference

    @property
    def side(self) -> str:
        return self.request.side


class PaperExecutionClient(ExecutionClient):
    def __init__(self, params: MarketParams, starting_cash: float, fill_model: MakerFillModel | None = None):
        self.params = params
        self.cash = starting_cash
        self.fill_model = fill_model or TradeThroughFillModel()
        self.books: dict[str, OrderBook] = {}
        self.now = 0.0
        self.orders: dict[str, RestingOrder] = {}
        self.positions: dict[str, float] = {t.token_id: 0.0 for t in params.tokens}
        self.fills: list[Fill] = []
        self.rejections: list[tuple[OrderRequest, str]] = []
        self.halted = False
        self._liq: dict[tuple[str, str], list[Liquidity]] = {}
        self._ids = itertools.count(1)

    # --- market data ------------------------------------------------------
    def _opposite(self, token_id: str, side: str) -> list[Liquidity]:
        """Opposite-side liquidity remaining in the current snapshot (shared, mutable)."""
        key = (token_id, side)
        if key not in self._liq:
            book = self.books.get(token_id)
            levels = (book.asks if side == "buy" else book.bids) if book else ()
            self._liq[key] = [Liquidity(lv.price, lv.size) for lv in levels]
        return self._liq[key]

    def on_snapshot(self, snapshot: BookSnapshot) -> list[Fill]:
        """Install new books and fill resting orders that the new books trade through."""
        self.now = snapshot.timestamp
        self.books.update(snapshot.books)
        self._liq.clear()
        new: list[Fill] = []
        # Best-priced orders first: they would be hit first.
        for o in sorted(self.orders.values(), key=lambda o: -o.request.price if o.side == "buy" else o.request.price):
            if o.placed_at >= snapshot.timestamp or o.request.token_id not in snapshot.books:
                continue
            qty = self.fill_model.fill_quantity(o.side, o.request.price, o.remaining, self._opposite(o.request.token_id, o.side))
            if qty > EPS:
                new.append(self._maker_fill(o, qty))
        for o in self.orders.values():
            book = self.books.get(o.request.token_id)
            if book is not None and book.mid is not None:
                o.ref_mid = book.mid
        return new

    def _maker_fill(self, o: RestingOrder, qty: float) -> Fill:
        r = o.request
        fee = maker_fee(qty, r.price, self.params.fee)
        fill = Fill(
            order_id=o.order_id, market_id=r.market_id, token_id=r.token_id, side=r.side, price=r.price,
            size=qty, liquidity="maker", fee=fee, mid_ref=o.ref_mid, top_ref=r.price, timestamp=self.now,
            fee_equivalent=fee_equivalent(qty, r.price, self.params.fee), group_id=r.group_id or o.order_id,
        )
        o.remaining -= qty
        if o.remaining <= EPS:
            del self.orders[o.order_id]
        self._apply(fill)
        return fill

    def _apply(self, fill: Fill) -> None:
        self.positions[fill.token_id] = self.positions.get(fill.token_id, 0.0) + fill.sign * fill.size
        self.cash -= fill.sign * fill.price * fill.size + fill.fee
        self.fills.append(fill)

    # --- order entry ------------------------------------------------------
    def _reject(self, order: OrderRequest, reason: str) -> None:
        self.rejections.append((order, reason))
        raise OrderRejected(reason)

    def reserved_cash(self) -> float:
        return sum(o.remaining * o.request.price for o in self.orders.values() if o.side == "buy")

    def reserved_shares(self, token_id: str) -> float:
        return sum(o.remaining for o in self.orders.values() if o.side == "sell" and o.request.token_id == token_id)

    def submit(self, order: OrderRequest) -> str:
        p = self.params
        if self.halted:
            self._reject(order, "halted by kill switch")
        if order.token_id not in self.positions:
            self._reject(order, f"unknown token {order.token_id}")
        book = self.books.get(order.token_id)
        if book is None:
            self._reject(order, "no order book")
        tick = book.tick_size or p.tick_size
        if not 0 < order.price < 1 or not on_tick(order.price, tick):
            self._reject(order, f"price {order.price} not on tick {tick} in (0, 1)")
        min_size = max(book.min_order_size, p.min_order_size)
        if order.size <= 0 or order.size < min_size - EPS:
            self._reject(order, f"size {order.size} below min order size {min_size}")
        if order.side == "sell":
            free = self.positions[order.token_id] - self.reserved_shares(order.token_id)
            if order.size > free + EPS:
                self._reject(order, f"sell {order.size} exceeds free inventory {free:.4f} (no shorting)")
        else:
            worst_fee = taker_fee_for_fills([(order.price, order.size)], p.fee)
            if order.price * order.size + worst_fee > self.cash - self.reserved_cash() + EPS:
                self._reject(order, "insufficient paper cash")

        opposite = self._opposite(order.token_id, order.side)
        top = next((lv for lv in opposite if lv.size > EPS), None)
        marketable = top is not None and (
            top.price <= order.price + EPS if order.side == "buy" else top.price >= order.price - EPS
        )
        if marketable and order.post_only:
            self._reject(order, "post-only order would take liquidity")

        oid = f"paper-{next(self._ids)}"
        remaining = order.size
        if marketable:
            taken = self._walk(opposite, order)
            fills = [(opposite[i].price, q) for i, q in taken]
            filled = sum(q for _, q in fills)
            if order.order_type == "FOK" and filled < order.size - EPS:
                self._reject(order, f"FOK: only {filled:.4f}/{order.size} available")
            for i, q in taken:
                opposite[i].size -= q
            if filled > EPS:
                vwap = sum(px * q for px, q in fills) / filled
                self._apply(Fill(
                    order_id=oid, market_id=order.market_id, token_id=order.token_id, side=order.side, price=vwap,
                    size=filled, liquidity="taker", fee=taker_fee_for_fills(fills, p.fee),
                    mid_ref=book.mid if book.mid is not None else vwap, top_ref=fills[0][0], timestamp=self.now,
                    group_id=order.group_id or oid,
                ))
            remaining -= filled
        if remaining > EPS and order.order_type in ("GTC", "GTD"):
            self.orders[oid] = RestingOrder(oid, order, remaining, self.now, book.mid if book.mid is not None else order.price)
        return oid

    @staticmethod
    def _walk(opposite: list[Liquidity], order: OrderRequest) -> list[tuple[int, float]]:
        """[(level index, shares)] a marketable order would take, up to its limit price."""
        fills, remaining = [], order.size
        for i, lvl in enumerate(opposite):
            if remaining <= EPS:
                break
            ok = lvl.price <= order.price + EPS if order.side == "buy" else lvl.price >= order.price - EPS
            if not ok:
                break
            take = min(lvl.size, remaining)
            if take > EPS:
                fills.append((i, take))
                remaining -= take
        return fills

    def cancel(self, order_id: str) -> None:
        self.orders.pop(order_id, None)

    def cancel_all(self) -> int:
        n = len(self.orders)
        self.orders.clear()
        return n

    def halt(self, reasons: list[str] | None = None) -> None:
        """Kill-switch hook: cancel everything and refuse new orders."""
        self.halted = True
        n = self.cancel_all()
        log.warning("Paper engine halted, %d orders cancelled: %s", n, reasons)
