import pytest
from conftest import NO_TOKEN, YES_TOKEN, make_book, make_params, make_snapshot, mirror_book

from moneylab.analytics.costs import taker_fee
from moneylab.domain.market_params import RewardAllocation, RewardConfig
from moneylab.domain.orderbook import BookSnapshot
from moneylab.strategy.context import StrategyContext, ceil_to_tick, floor_to_tick, on_tick
from moneylab.strategy.market_making import SymmetricMarketMaker
from moneylab.strategy.mispricing import CombinedMispricing, ComplementArbitrage, FairValueDeviation

REWARDS = RewardConfig(max_spread_cents=3, min_size=50, allocations=(RewardAllocation(20),))


def ctx(bids, asks, positions=None, signals=None, no_book=None, **kw):
    return StrategyContext(make_params(**kw), make_snapshot(1000, bids, asks, signals, no_book), positions or {})


def test_tick_helpers():
    assert floor_to_tick(0.4999, 0.01) == 0.49 and ceil_to_tick(0.4901, 0.01) == 0.50
    assert floor_to_tick(0.49, 0.01) == 0.49 and on_tick(0.49, 0.01) and not on_tick(0.495, 0.01)


# --- market making ------------------------------------------------------------------

def test_mm_flat_inventory_quotes_both_sides_without_crossing():
    c = ctx([(0.45, 100)], [(0.51, 100)])  # wide 6-tick spread, balanced -> fair 0.48
    q = {(x.token_id, x.side): x for x in SymmetricMarketMaker(quote_size=20, stay_in_reward_band=False).quote(c)}
    assert q[(YES_TOKEN, "buy")].price == 0.47
    assert q[(NO_TOKEN, "buy")].price == pytest.approx(1 - 0.49)  # YES ask 0.49 expressed as NO bid
    assert all(x.size == 20 for x in q.values())


def test_mm_never_crosses_tight_book():
    c = ctx([(0.49, 100)], [(0.50, 100)])
    for x in SymmetricMarketMaker(half_spread_ticks=0, stay_in_reward_band=False).quote(c):
        book = c.book(x.token_id)
        assert x.price < book.best_ask if x.side == "buy" else x.price > book.best_bid


def test_mm_uses_yes_inventory_to_sell_and_skews_down():
    flat = SymmetricMarketMaker(quote_size=20, skew_per_share=0.0001, stay_in_reward_band=False)
    c_flat = ctx([(0.40, 100)], [(0.60, 100)])
    c_long = ctx([(0.40, 100)], [(0.60, 100)], positions={YES_TOKEN: 200})
    q_flat = {(x.token_id, x.side): x.price for x in flat.quote(c_flat)}
    q_long = {(x.token_id, x.side): x.price for x in flat.quote(c_long)}
    assert (YES_TOKEN, "sell") in q_long and (NO_TOKEN, "buy") not in q_long
    assert q_long[(YES_TOKEN, "buy")] < q_flat[(YES_TOKEN, "buy")]  # skewed lower when long


def test_mm_inventory_limit_stops_adding():
    mm = SymmetricMarketMaker(max_inventory_shares=100, stay_in_reward_band=False)
    sides = {(x.token_id, x.side) for x in mm.quote(ctx([(0.40, 100)], [(0.60, 100)], positions={NO_TOKEN: 150}))}
    assert (NO_TOKEN, "buy") not in sides and (YES_TOKEN, "buy") in sides


def test_mm_reward_band_and_min_size():
    c = ctx([(0.40, 100)], [(0.60, 100)], rewards=REWARDS)
    quotes = SymmetricMarketMaker(quote_size=10, half_spread_ticks=8).quote(c)
    mid = 0.50
    for x in quotes:
        m = mid if x.token_id == YES_TOKEN else 1 - mid
        assert abs(x.price - m) < 0.03  # inside max qualifying spread
        assert x.size == 50  # raised to rewards min size


def test_mm_no_quotes_without_two_sided_book():
    assert SymmetricMarketMaker().quote(ctx([], [(0.6, 10)])) == []


# --- mispricing ---------------------------------------------------------------------

def test_no_arbitrage_on_mirrored_book():
    assert ComplementArbitrage().evaluate(ctx([(0.45, 100)], [(0.47, 100)])) == []


def test_complement_arbitrage_after_fees():
    yes = make_book(YES_TOKEN, [(0.45, 100)], [(0.46, 100), (0.47, 100)])
    no = make_book(NO_TOKEN, [(0.47, 100)], [(0.48, 60), (0.52, 500)])
    intents = ComplementArbitrage(min_edge_per_share=0.005).evaluate(StrategyContext(make_params(), _snap(yes, no)))
    assert {i.token_id for i in intents} == {YES_TOKEN, NO_TOKEN}
    assert all(i.kind == "arbitrage" and i.max_size == 60 for i in intents)  # 60 = cheap NO depth
    assert len({i.group_id for i in intents}) == 1
    fees = taker_fee(60, 0.46, make_params().fee) + taker_fee(60, 0.48, make_params().fee)
    pair_edge = (60 - 60 * 0.46 - 60 * 0.48 - fees) / 60
    assert sum(i.edge_per_share for i in intents) == pytest.approx(pair_edge)
    assert pair_edge > 0.005


def test_arbitrage_rejected_when_fees_eat_the_gap():
    yes = make_book(YES_TOKEN, [(0.45, 100)], [(0.50, 100)])
    no = make_book(NO_TOKEN, [(0.45, 100)], [(0.495, 100)])  # gross gap 0.005, fees ~0.02
    assert ComplementArbitrage().evaluate(StrategyContext(make_params(), _snap(yes, no))) == []


def _snap(yes, no):
    return BookSnapshot(1000, {YES_TOKEN: yes, NO_TOKEN: no})


def test_fair_value_needs_a_signal():
    assert FairValueDeviation().evaluate(ctx([(0.45, 100)], [(0.47, 100)])) == []


def test_fair_value_buys_yes_up_to_marginal_edge():
    c = ctx([(0.45, 100)], [(0.47, 100), (0.48, 100), (0.53, 100)], signals={"fair_yes": 0.52})
    [it] = FairValueDeviation(min_edge_per_share=0.02).evaluate(c)
    assert it.token_id == YES_TOKEN and it.side == "buy"
    assert it.limit_price == 0.48 and it.max_size == 200  # 0.53 level fails the edge
    assert it.edge_per_share == pytest.approx(0.52 - 0.47 - 0.04 * 0.47 * 0.53)


def test_fair_value_buys_no_when_yes_is_overpriced():
    [it] = FairValueDeviation().evaluate(ctx([(0.55, 100)], [(0.57, 100)], signals={"fair_yes": 0.45}))
    assert it.token_id == NO_TOKEN and it.fair_probability == pytest.approx(0.55)


def test_fair_value_no_trade_inside_fees():
    assert FairValueDeviation(min_edge_per_share=0.02).evaluate(
        ctx([(0.45, 100)], [(0.47, 100)], signals={"fair_yes": 0.49})) == []


def test_combined_puts_arbitrage_first():
    yes = make_book(YES_TOKEN, [(0.45, 100)], [(0.46, 100)])
    no = make_book(NO_TOKEN, [(0.40, 100)], [(0.48, 100)])
    c = StrategyContext(make_params(), BookSnapshot(1000, {YES_TOKEN: yes, NO_TOKEN: no}, {"fair_yes": 0.60}))
    intents = CombinedMispricing((FairValueDeviation(), ComplementArbitrage())).evaluate(c)
    kinds = [i.kind for i in intents]
    assert kinds[:2] == ["arbitrage", "arbitrage"] and kinds[-1] == "directional"


def test_mirror_helper():
    nb = mirror_book(make_book(YES_TOKEN, [(0.45, 1)], [(0.47, 2)]))
    assert nb.best_bid == pytest.approx(0.53) and nb.best_ask == pytest.approx(0.55)
