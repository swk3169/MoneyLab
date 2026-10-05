"""End-to-end offline simulation on the synthetic fixture timelines (no network)."""

import pytest
import requests
from conftest import FIXTURES, NO_TOKEN, YES_TOKEN, make_params, make_snapshot

from moneylab.core.exceptions import ProviderError
from moneylab.domain.market_params import RewardAllocation, RewardConfig
from moneylab.domain.orderbook import MarketTimeline
from moneylab.paper.book_stream import PollingBookStream, TimelineBookStream
from moneylab.paper.runner import SimulationConfig, SimulationRunner
from moneylab.providers.base import OrderBookProvider
from moneylab.providers.polymarket import load_timeline
from moneylab.risk.kill_switch import KillSwitchConfig
from moneylab.sizing.position import SizingLimits
from moneylab.strategy.market_making import SymmetricMarketMaker
from moneylab.strategy.mispricing import CombinedMispricing, ComplementArbitrage, FairValueDeviation

# token ids of the synthetic fixture timelines
YES, NO = "111111111111111111110001", "111111111111111111110002"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network access attempted during offline simulation")

    monkeypatch.setattr(requests.Session, "request", boom)


def run(path, strategy, resolution="fixture", **cfg):
    tl = load_timeline(FIXTURES / path)
    res = tl.resolution if resolution == "fixture" else resolution
    runner = SimulationRunner(tl.params, strategy, SimulationConfig(**cfg), synthetic=tl.synthetic)
    return tl, runner.run(TimelineBookStream(tl), res)


def mispricing():
    return CombinedMispricing((ComplementArbitrage(), FairValueDeviation()))


# --- market making ------------------------------------------------------------------

def test_market_making_fixture_golden():
    _, r = run("clob_timeline_mm.json", SymmetricMarketMaker())
    b = r.breakdown
    assert b.identity_holds
    assert (r.maker_fills, r.taker_fills) == (3, 0)
    assert b.spread_captured == pytest.approx(2.0)
    assert b.inventory_pnl == pytest.approx(-17.5)
    assert b.net_trading_pnl_after_cost == pytest.approx(-15.5)
    assert b.estimated_maker_rebate == pytest.approx(0.37365, abs=1e-6)
    assert b.estimated_liquidity_reward == pytest.approx(0.491375, abs=1e-5)
    assert b.realized_maker_rebate == 0 and b.realized_liquidity_reward == 0
    assert b.all_in_realized_pnl == pytest.approx(b.net_trading_pnl_after_cost)
    assert r.verdict.status == "REJECT"
    assert r.max_drawdown == pytest.approx(0.0155)
    assert not r.kill_switch_reasons


def test_market_making_fills_are_all_trade_through():
    tl, r = run("clob_timeline_mm.json", SymmetricMarketMaker())
    books = {s.timestamp: s.books for s in tl.snapshots}
    for f in r.fills:
        book = books[f.timestamp][f.token_id]
        if f.side == "buy":
            assert book.best_ask < f.price  # strictly through, never a touch
        else:
            assert book.best_bid > f.price


def test_reward_estimate_can_be_disabled():
    _, r = run("clob_timeline_mm.json", SymmetricMarketMaker(), estimate_rewards=False)
    assert r.breakdown.estimated_liquidity_reward == 0


def test_market_making_is_deterministic():
    _, a = run("clob_timeline_mm.json", SymmetricMarketMaker())
    _, b = run("clob_timeline_mm.json", SymmetricMarketMaker())
    assert a.breakdown == b.breakdown and a.equity_curve == b.equity_curve


# --- mispricing ---------------------------------------------------------------------

def test_mispricing_fixture_golden():
    _, r = run("clob_timeline_mispricing.json", mispricing())
    b = r.breakdown
    assert b.identity_holds
    assert (r.maker_fills, r.taker_fills) == (0, 10)
    assert b.taker_fees == pytest.approx(4.80467, abs=1e-5)
    assert b.net_trading_pnl_after_cost == pytest.approx(203.93513, abs=1e-4)
    assert len(r.trade_pnls) == 9 and r.open_trades_marked == 0
    assert r.final_positions == {YES: 0.0, NO: 0.0}  # settled at resolution
    assert r.verdict.status == "INSUFFICIENT_EVIDENCE"  # synthetic + few trades, even though positive


def test_arbitrage_profit_is_independent_of_resolution():
    _, yes = run("clob_timeline_mispricing.json", ComplementArbitrage(), resolution={YES: 1.0, NO: 0.0})
    _, no = run("clob_timeline_mispricing.json", ComplementArbitrage(), resolution={YES: 0.0, NO: 1.0})
    assert yes.taker_fills > 0
    assert yes.breakdown.net_trading_pnl_after_cost == pytest.approx(no.breakdown.net_trading_pnl_after_cost)
    assert yes.breakdown.net_trading_pnl_after_cost > 0


def test_directional_result_flips_with_resolution():
    _, yes = run("clob_timeline_mispricing.json", FairValueDeviation(), resolution={YES: 1.0, NO: 0.0})
    _, no = run("clob_timeline_mispricing.json", FairValueDeviation(), resolution={YES: 0.0, NO: 1.0})
    assert yes.breakdown.net_trading_pnl_after_cost > 0 > no.breakdown.net_trading_pnl_after_cost
    assert no.verdict.status == "REJECT"


def test_kelly_fraction_scales_directional_size():
    _, quarter = run("clob_timeline_mispricing.json", FairValueDeviation())
    _, tenth = run("clob_timeline_mispricing.json", FairValueDeviation(), sizing=SizingLimits(kelly_fraction=0.1))
    # First order is Kelly-bound (later ones hit the per-market cap, so totals converge).
    assert tenth.fills[0].size == pytest.approx(quarter.fills[0].size * 0.4, rel=0.01)


# --- kill switch inside the loop ---------------------------------------------------------

def _timeline(snaps, rewards=None):
    return MarketTimeline(params=make_params(rewards=rewards), snapshots=tuple(snaps), synthetic=True)


def test_kill_switch_trips_mid_run_cancels_and_stops_trading():
    snaps = [make_snapshot(1000 + 60 * i, [(0.45, 100)], [(0.51, 100)]) for i in range(3)]
    snaps.append(make_snapshot(1180, [(0.20, 100)], [(0.60, 100)]))  # abnormal spread
    snaps += [make_snapshot(1240 + 60 * i, [(0.30, 100)], [(0.31, 100)]) for i in range(3)]  # would trade through
    tl = _timeline(snaps)
    runner = SimulationRunner(tl.params, SymmetricMarketMaker(stay_in_reward_band=False))
    r = runner.run(TimelineBookStream(tl))
    assert r.kill_switch_reasons and r.kill_switch_reasons[0].startswith("abnormal_spread")
    assert r.kill_switch_tripped_at == 1180
    assert runner.engine.halted and not runner.engine.orders
    assert all(f.timestamp <= 1180 for f in r.fills)  # nothing filled after the trip


def test_daily_loss_limit_trips_in_loop():
    snaps = [make_snapshot(1000, [(0.50, 1000)], [(0.51, 1000)], signals={"fair_yes": 0.70})]
    snaps += [make_snapshot(1060 + 60 * i, [(0.05, 1000)], [(0.06, 1000)]) for i in range(3)]
    tl = _timeline(snaps)
    cfg = SimulationConfig(kill_switch=KillSwitchConfig(daily_loss_limit=10, max_drawdown=0.9))
    r = SimulationRunner(tl.params, FairValueDeviation(), cfg).run(TimelineBookStream(tl))
    assert any(x.startswith("daily_loss_limit") for x in r.kill_switch_reasons)


class FlakyProvider(OrderBookProvider):
    name = "flaky"

    def get_order_book(self, token_id):
        raise ProviderError(self.name, "HTTP 451")

    def get_market_params(self, condition_id):
        raise ProviderError(self.name, "HTTP 451")


def test_polling_stream_errors_trip_kill_switch():
    clock = iter(range(1000, 2000, 60))
    stream = PollingBookStream(FlakyProvider(), [YES_TOKEN, NO_TOKEN], interval=60, max_polls=5,
                               clock=lambda: next(clock), sleep=lambda s: None)
    runner = SimulationRunner(make_params(), SymmetricMarketMaker())
    r = runner.run(stream)
    assert r.kill_switch_reasons[0].startswith("provider_errors")
    assert not r.fills


def test_reward_estimate_accrues_only_for_resting_orders():
    cfg = RewardConfig(max_spread_cents=3, min_size=50, allocations=(RewardAllocation(86.4),))
    snaps = [make_snapshot(1000 + 60 * i, [(0.48, 100)], [(0.52, 100)]) for i in range(3)]
    tl = _timeline(snaps, rewards=cfg)
    r = SimulationRunner(tl.params, SymmetricMarketMaker(quote_size=50)).run(TimelineBookStream(tl))
    est = r.breakdown.estimated_liquidity_reward
    assert 0 < est < 86.4 * 120 / 86400  # at most the whole pool for 2 minutes
    assert r.breakdown.realized_liquidity_reward == 0
