"""Offline / paper simulation loop.

Per event:  maker fills (fill model) -> ledger -> marks & equity -> kill switch
            -> strategy -> sizing caps -> paper orders -> reward-score sampling
At the end: cancel all, settle at resolution if known, final marks.

Only domain types and base interfaces are used here; the data source (fixture timeline or a
live polling stream) is chosen by the caller.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from moneylab.analytics import metrics
from moneylab.analytics.rewards import (
    RewardOrder,
    adjusted_midpoint,
    book_orders,
    estimated_reward_for_interval,
    q_min,
    sample_share,
    side_scores,
)
from moneylab.domain.market_params import MarketParams
from moneylab.domain.orderbook import BookSnapshot
from moneylab.execution.base import Fill, OrderRequest
from moneylab.paper.book_stream import StreamEvent
from moneylab.paper.engine import OrderRejected, PaperExecutionClient
from moneylab.paper.fill_models import MakerFillModel
from moneylab.pnl.ledger import Ledger
from moneylab.pnl.report import AdoptionVerdict, PnLBreakdown, evaluate_adoption
from moneylab.risk.kill_switch import KillSwitch, KillSwitchConfig, RiskSnapshot
from moneylab.sizing.position import PortfolioState, SizingLimits, size_capped, size_directional
from moneylab.strategy.context import Quote, StrategyContext, TradeIntent
from moneylab.strategy.market_making import MarketMakingStrategy
from moneylab.strategy.mispricing import MispricingStrategy

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimulationConfig:
    starting_cash: float = 1000.0
    sizing: SizingLimits = field(default_factory=SizingLimits)
    kill_switch: KillSwitchConfig = field(default_factory=KillSwitchConfig)
    estimate_rewards: bool = True
    min_trades_for_adoption: int = 100


@dataclass
class SimulationResult:
    strategy: str
    breakdown: PnLBreakdown
    equity_curve: list[tuple[float, float]]
    fills: list[Fill]
    trade_pnls: list[float]
    open_trades_marked: int
    rejections: list[tuple[OrderRequest, str]]
    kill_switch_reasons: list[str]
    kill_switch_tripped_at: float | None
    final_positions: dict[str, float]
    verdict: AdoptionVerdict
    synthetic: bool

    @property
    def max_drawdown(self) -> float:
        return metrics.max_drawdown([e for _, e in self.equity_curve])

    @property
    def max_drawdown_abs(self) -> float:
        return metrics.max_drawdown_abs([e for _, e in self.equity_curve])

    @property
    def win_rate(self) -> float | None:
        return metrics.win_rate(self.trade_pnls)

    @property
    def profit_factor(self) -> float | None:
        return metrics.profit_factor(self.trade_pnls)

    @property
    def maker_fills(self) -> int:
        return sum(1 for f in self.fills if f.liquidity == "maker")

    @property
    def taker_fills(self) -> int:
        return sum(1 for f in self.fills if f.liquidity == "taker")


def _day(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).date().isoformat()


class SimulationRunner:
    def __init__(
        self,
        params: MarketParams,
        strategy: MarketMakingStrategy | MispricingStrategy,
        config: SimulationConfig | None = None,
        fill_model: MakerFillModel | None = None,
        synthetic: bool = True,
    ):
        self.params = params
        self.strategy = strategy
        self.config = config or SimulationConfig()
        self.synthetic = synthetic
        self.engine = PaperExecutionClient(params, self.config.starting_cash, fill_model)
        self.ledger = Ledger(self.config.starting_cash)
        self.kill = KillSwitch(self.config.kill_switch)
        self.kill.on_trip(self.engine.halt)
        self.marks: dict[str, float] = {}
        self.peak = self.config.starting_cash
        self.day: str | None = None
        self.day_start_equity = self.config.starting_cash
        self._reward_state: tuple[float, BookSnapshot, list[RewardOrder]] | None = None
        self._recorded = 0

    # --- helpers --------------------------------------------------------------
    @property
    def market_id(self) -> str:
        return self.params.condition_id

    def _net_delta(self) -> float:
        pos = self.engine.positions
        return pos.get(self.params.yes_token, 0.0) - pos.get(self.params.no_token, 0.0)

    def _exposure(self) -> float:
        return sum(abs(q) * self.marks.get(t, 0.0) for t, q in self.engine.positions.items())

    def _state(self, equity: float) -> PortfolioState:
        return PortfolioState(
            equity=equity, peak_equity=self.peak, daily_pnl=equity - self.day_start_equity,
            market_exposure={self.market_id: self._exposure()}, net_delta={self.market_id: self._net_delta()},
        )

    def _delta_direction(self, token_id: str, side: str) -> float:
        d = 1.0 if token_id == self.params.yes_token else -1.0
        return d if side == "buy" else -d

    def _sync_fills(self) -> None:
        """Book every engine fill not yet in the ledger."""
        for f in self.engine.fills[self._recorded:]:
            self.ledger.record_fill(f, self.params.fee.rebate_rate)
        self._recorded = len(self.engine.fills)

    def _update_marks(self, snap: BookSnapshot) -> None:
        for token, book in snap.books.items():
            m = book.mid if book.mid is not None else book.last_trade_price
            if m is not None:
                self.marks[token] = m

    # --- incentives (estimates only) -----------------------------------------
    def _accrue_reward(self, now: float) -> None:
        """Score the orders that rested during [prev, now] against the previous books."""
        cfg = self.params.rewards
        if not self.config.estimate_rewards or cfg is None or self._reward_state is None:
            return
        prev_ts, snap, mine = self._reward_state
        yes_book, no_book = snap.books.get(self.params.yes_token), snap.books.get(self.params.no_token)
        if not mine or yes_book is None:
            return
        mid = adjusted_midpoint(yes_book.bids, yes_book.asks, cfg.min_size)
        if mid is None:
            return
        my_q = q_min(*side_scores(mine, mid, cfg), mid, cfg.scaling_c)
        others = book_orders(yes_book.bids, yes_book.asks, False)
        if no_book is not None:
            others += book_orders(no_book.bids, no_book.asks, True)
        other_q = q_min(*side_scores(others, mid, cfg), mid, cfg.scaling_c)
        share = sample_share(my_q, other_q)
        day = datetime.fromtimestamp(prev_ts, UTC).date()
        self.ledger.add_estimated_liquidity_reward(
            estimated_reward_for_interval(cfg.daily_rate(day), share, now - prev_ts)
        )

    def _remember_resting(self, snap: BookSnapshot) -> None:
        mine = [
            RewardOrder("bid" if o.side == "buy" else "ask", o.request.price, o.remaining,
                        complement=o.request.token_id == self.params.no_token)
            for o in self.engine.orders.values()
        ]
        self._reward_state = (snap.timestamp, snap, mine)

    # --- strategy dispatch ----------------------------------------------------
    def _submit(self, order: OrderRequest) -> str | None:
        try:
            oid = self.engine.submit(order)
        except OrderRejected as exc:
            log.debug("order rejected: %s", exc)
            return None
        self._sync_fills()
        return oid

    def _run_market_maker(self, ctx: StrategyContext, equity: float) -> None:
        quotes: list[Quote] = self.strategy.quote(ctx)  # type: ignore[union-attr]
        wanted: list[Quote] = []
        state = self._state(equity)
        for q in quotes:
            book = ctx.book(q.token_id)
            if book is None or book.mid is None:
                continue
            fair = book.mid  # edge of a maker quote vs the token's mid
            edge = fair - q.price if q.side == "buy" else q.price - fair
            dec = size_capped(self.market_id, q.size, q.price, edge, float("inf"), state, self.config.sizing,
                              self._delta_direction(q.token_id, q.side), self.params.min_order_size)
            if dec.ok:
                wanted.append(Quote(q.token_id, q.side, q.price, dec.size))
        # Reconcile: keep identical live orders (preserves queue/reward age), cancel the rest.
        live = {(o.request.token_id, o.side, o.request.price): oid for oid, o in self.engine.orders.items()}
        keep: set[str] = set()
        for q in wanted:
            oid = live.get((q.token_id, q.side, q.price))
            if oid is not None:
                keep.add(oid)
        for oid in list(self.engine.orders):
            if oid not in keep:
                self.engine.cancel(oid)
        for q in wanted:
            if live.get((q.token_id, q.side, q.price)) in keep:
                continue
            self._submit(OrderRequest(self.market_id, q.token_id, q.side, q.price, q.size, "GTC", post_only=True))

    def _run_mispricing(self, ctx: StrategyContext, equity: float) -> None:
        intents: list[TradeIntent] = self.strategy.evaluate(ctx)  # type: ignore[union-attr]
        state = self._state(equity)
        groups: dict[str, list[TradeIntent]] = {}
        for it in intents:
            groups.setdefault(it.group_id or f"{it.token_id}-{ctx.snapshot.timestamp}", []).append(it)
        for gid, legs in groups.items():
            if all(leg.kind == "arbitrage" for leg in legs):
                pair_cost = sum(leg.all_in_price for leg in legs)
                dec = size_capped(self.market_id, min(leg.max_size for leg in legs), pair_cost,
                                  min(leg.edge_per_share for leg in legs), min(leg.max_size for leg in legs),
                                  state, self.config.sizing, 0.0, self.params.min_order_size)
                if dec.ok:
                    done = 0
                    for leg in legs:
                        if self._submit(OrderRequest(self.market_id, leg.token_id, leg.side, leg.limit_price,
                                                     dec.size, "FOK", group_id=gid)) is not None:
                            done += 1
                    if 0 < done < len(legs):  # one leg filled, the other did not: unhedged position
                        log.warning("arbitrage %s legged: %d/%d legs filled", gid, done, len(legs))
                continue
            for leg in legs:
                dec = size_directional(self.market_id, leg.fair_probability, leg.all_in_price, leg.max_size, state,
                                       self.config.sizing, self._delta_direction(leg.token_id, leg.side),
                                       self.params.min_order_size)
                if dec.ok:
                    self._submit(OrderRequest(self.market_id, leg.token_id, leg.side, leg.limit_price, dec.size, "FAK"))

    # --- main loop ------------------------------------------------------------
    def run(self, events: Iterable[StreamEvent], resolution: dict[str, float] | None = None) -> SimulationResult:
        last_ts = None
        watched = [t for t in (self.params.yes_token, self.params.no_token) if t]
        for ev in events:
            last_ts = ev.timestamp
            if ev.snapshot is None:
                if ev.trades and ev.error is None:  # trade prints only: no book to act on, not a failure
                    continue
                self.kill.record_error(ev.timestamp)
                continue
            self.kill.record_success()
            snap = ev.snapshot
            self._accrue_reward(snap.timestamp)

            self.engine.on_snapshot(snap)
            self._sync_fills()
            self._update_marks(snap)
            equity = self.ledger.mark(snap.timestamp, self.marks)
            if self.day != _day(snap.timestamp):
                self.day, self.day_start_equity = _day(snap.timestamp), equity
            self.peak = max(self.peak, equity)

            self.kill.check(RiskSnapshot(
                now=snap.timestamp, equity=equity, peak_equity=self.peak, daily_pnl=equity - self.day_start_equity,
                net_delta={self.market_id: self._net_delta()}, books={t: snap.books.get(t) for t in watched},
            ))
            if self.kill.allows_new_orders:
                ctx = StrategyContext(self.params, snap, dict(self.engine.positions))
                if isinstance(self.strategy, MarketMakingStrategy):
                    self._run_market_maker(ctx, equity)
                else:
                    self._run_mispricing(ctx, equity)
                # Re-mark: taker fills this step change positions.
                self.ledger.equity_curve[-1] = (snap.timestamp, self.ledger.trading_equity(self.marks))
            self._remember_resting(snap)

        self.engine.cancel_all()
        if resolution and last_ts is not None:
            self.ledger.settle(resolution, last_ts)
            self.marks.update(resolution)
            self.ledger.mark(last_ts, self.marks)
        breakdown = self.ledger.breakdown(self.marks)
        pnls, open_marked = self.ledger.trade_pnls(self.marks)
        return SimulationResult(
            strategy=getattr(self.strategy, "name", type(self.strategy).__name__),
            breakdown=breakdown,
            equity_curve=list(self.ledger.equity_curve),
            fills=list(self.engine.fills),
            trade_pnls=pnls,
            open_trades_marked=open_marked,
            rejections=list(self.engine.rejections),
            kill_switch_reasons=list(self.kill.reasons),
            kill_switch_tripped_at=self.kill.tripped_at,
            final_positions={t: q for t, q in self.ledger.positions().items()},
            verdict=evaluate_adoption(breakdown, len(pnls), self.synthetic, self.config.min_trades_for_adoption),
            synthetic=self.synthetic,
        )
