import pytest
from conftest import NO_TOKEN, YES_TOKEN, make_params, make_snapshot

from moneylab.analytics.costs import taker_fee
from moneylab.execution.base import OrderRequest
from moneylab.paper.engine import OrderRejected, PaperExecutionClient
from moneylab.paper.fill_models import MakerFillModel, TradeThroughFillModel

BIDS = [(0.48, 100), (0.47, 100)]
ASKS = [(0.50, 100), (0.51, 100), (0.52, 100)]


def engine(cash=10_000.0, **kw):
    e = PaperExecutionClient(make_params(**kw), cash)
    e.on_snapshot(make_snapshot(1000, BIDS, ASKS))
    return e


def order(side="buy", price=0.52, size=250.0, token=YES_TOKEN, **kw):
    return OrderRequest("0xcond", token, side, price, size, **kw)


# --- taker VWAP ------------------------------------------------------------------

def test_taker_buy_vwap_fee_and_refs():
    e = engine()
    e.submit(order(order_type="FAK"))
    f = e.fills[0]
    assert f.liquidity == "taker" and f.size == 250
    assert f.price == pytest.approx((50 + 51 + 0.52 * 50) / 250)
    assert f.top_ref == 0.50 and f.mid_ref == pytest.approx(0.49)
    p = make_params()
    assert f.fee == pytest.approx(taker_fee(100, 0.50, p.fee) + taker_fee(100, 0.51, p.fee) + taker_fee(50, 0.52, p.fee))
    assert e.positions[YES_TOKEN] == 250
    assert e.cash == pytest.approx(10_000 - f.price * 250 - f.fee)


def test_limit_price_stops_the_walk_and_fak_cancels_rest():
    e = engine()
    e.submit(order(price=0.51, order_type="FAK"))
    assert e.fills[0].size == 200 and not e.orders


def test_gtc_marketable_remainder_rests():
    e = engine()
    oid = e.submit(order(price=0.51, size=250, order_type="GTC"))
    assert e.fills[0].size == 200 and e.orders[oid].remaining == 50


def test_fok_all_or_nothing():
    e = engine()
    with pytest.raises(OrderRejected, match="FOK"):
        e.submit(order(price=0.51, size=250, order_type="FOK"))
    assert not e.fills
    e.submit(order(price=0.51, size=200, order_type="FOK"))
    assert e.fills[0].size == 200


def test_liquidity_not_reused_within_a_snapshot():
    e = engine()
    e.submit(order(price=0.50, size=80, order_type="FAK"))
    e.submit(order(price=0.50, size=80, order_type="FAK"))
    assert [f.size for f in e.fills] == [80, 20]
    e.on_snapshot(make_snapshot(1060, BIDS, ASKS))  # fresh snapshot restores liquidity
    e.submit(order(price=0.50, size=80, order_type="FAK"))
    assert e.fills[-1].size == 80


def test_taker_sell_against_bids():
    e = engine()
    e.submit(order(price=0.51, size=200, order_type="FAK"))
    e.submit(order("sell", price=0.47, size=150, order_type="FAK"))
    f = e.fills[-1]
    assert f.side == "sell" and f.size == 150 and f.price == pytest.approx((48 + 0.47 * 50) / 150)


# --- conservative maker fills (trade-through) -----------------------------------

def test_maker_bid_touch_is_not_a_fill_trade_through_is():
    e = engine()
    oid = e.submit(order(price=0.49, size=50, post_only=True))
    assert not e.fills and e.orders[oid].remaining == 50
    e.on_snapshot(make_snapshot(1060, [(0.47, 100)], [(0.49, 500)]))  # ask touches 0.49
    assert not e.fills
    e.on_snapshot(make_snapshot(1120, [(0.46, 100)], [(0.48, 30), (0.49, 500)]))  # 30 trade through
    assert len(e.fills) == 1
    f = e.fills[0]
    assert f.liquidity == "maker" and f.price == 0.49 and f.size == 30 and f.fee == 0
    assert f.mid_ref == pytest.approx(0.48)  # last mid observed while resting, before the fill snapshot
    assert f.fee_equivalent == pytest.approx(30 * 0.04 * 0.49 * 0.51)
    e.on_snapshot(make_snapshot(1180, [(0.45, 100)], [(0.47, 100)]))
    assert e.fills[-1].size == 20 and oid not in e.orders


def test_maker_ask_trade_through():
    e = engine()
    e.submit(order(price=0.50, size=100, order_type="FAK"))
    e.submit(order("sell", price=0.53, size=60, post_only=True))
    e.on_snapshot(make_snapshot(1060, [(0.53, 100)], [(0.55, 100)]))  # touch
    assert len(e.fills) == 1
    e.on_snapshot(make_snapshot(1120, [(0.55, 100)], [(0.57, 100)]))
    assert e.fills[-1].side == "sell" and e.fills[-1].size == 60 and e.fills[-1].price == 0.53


def test_order_not_filled_by_the_snapshot_it_was_placed_in():
    e = engine()
    e.submit(order(price=0.49, size=50, post_only=True))
    e.on_snapshot(make_snapshot(1000, BIDS, [(0.40, 100)]))  # same timestamp as placement
    assert not e.fills


def test_two_resting_orders_share_crossing_liquidity():
    e = engine()
    e.submit(order(price=0.49, size=50, post_only=True))
    e.submit(order(price=0.49, size=50, post_only=True))
    e.on_snapshot(make_snapshot(1060, [(0.40, 10)], [(0.45, 70)]))
    assert sum(f.size for f in e.fills) == 70


def test_fill_model_is_pluggable():
    class TouchModel(MakerFillModel):
        def fill_quantity(self, side, price, remaining, opposite):
            return remaining if opposite and opposite[0].price <= price else 0.0

    e = PaperExecutionClient(make_params(), 10_000, fill_model=TouchModel())
    e.on_snapshot(make_snapshot(1000, BIDS, ASKS))
    e.submit(order(price=0.49, size=50, post_only=True))
    e.on_snapshot(make_snapshot(1060, [(0.47, 100)], [(0.49, 500)]))
    assert e.fills[0].size == 50
    assert isinstance(PaperExecutionClient(make_params(), 1).fill_model, TradeThroughFillModel)


# --- validation ----------------------------------------------------------------------

@pytest.mark.parametrize(("req", "match"), [
    (order(price=0.505, size=10), "tick"),
    (order(price=0.0, size=10), "tick"),
    (order(price=0.49, size=2), "min order size"),
    (order(price=0.50, size=10, post_only=True), "post-only"),
    (order("sell", price=0.49, size=10), "no shorting"),
    (order(price=0.49, size=10, token="nope"), "unknown token"),
])
def test_rejections(req, match):
    e = engine()
    with pytest.raises(OrderRejected, match=match):
        e.submit(req)
    assert e.rejections and not e.fills


def test_insufficient_cash_counts_open_bids():
    e = engine(cash=50.0)
    e.submit(order(price=0.40, size=100, post_only=True))  # reserves 40
    with pytest.raises(OrderRejected, match="cash"):
        e.submit(order(price=0.40, size=30, post_only=True))


def test_sells_cannot_exceed_free_inventory():
    e = engine()
    e.submit(order(price=0.50, size=100, order_type="FAK"))
    e.submit(order("sell", price=0.55, size=80, post_only=True))
    with pytest.raises(OrderRejected, match="no shorting"):
        e.submit(order("sell", price=0.56, size=30, post_only=True))


def test_cancel_cancel_all_and_halt():
    e = engine()
    a = e.submit(order(price=0.40, size=10, post_only=True))
    e.submit(order(price=0.41, size=10, post_only=True))
    e.submit(order(price=0.45, size=10, token=NO_TOKEN, post_only=True))
    e.cancel(a)
    assert len(e.orders) == 2
    e.halt(["test"])
    assert not e.orders and e.halted
    with pytest.raises(OrderRejected, match="kill switch"):
        e.submit(order(price=0.40, size=10, post_only=True))
