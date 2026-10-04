import pytest

from moneylab.analytics import metrics as m
from moneylab.domain.orderbook import OrderBook

BOOK = OrderBook.build(
    "T",
    bids=[(0.45, 140), (0.44, 100), (0.43, 220), (0.42, 130)],
    asks=[(0.47, 340), (0.48, 360), (0.49, 300)],
)


def test_spread_and_ticks():
    assert m.spread(BOOK.best_bid, BOOK.best_ask) == pytest.approx(0.02)
    assert m.spread_ticks(BOOK.best_bid, BOOK.best_ask, 0.01) == 2
    assert m.spread_ticks(None, 0.5, 0.01) is None


def test_microprice_leans_to_thin_side():
    mp = m.microprice(0.45, 140, 0.47, 340)
    assert mp == pytest.approx((0.45 * 340 + 0.47 * 140) / 480)
    assert mp < BOOK.mid  # bid side thinner -> price more likely to tick down
    assert m.microprice(0.45, 0, 0.47, 0) == pytest.approx(0.46)
    assert m.microprice(None, 1, 0.5, 1) is None


def test_depth_within_and_imbalance():
    bid_sh, bid_usd = m.depth_within(BOOK.bids, BOOK.mid, 0.02)  # 0.45, 0.44
    assert bid_sh == 240 and bid_usd == pytest.approx(0.45 * 140 + 0.44 * 100)
    ask_sh, _ = m.depth_within(BOOK.asks, BOOK.mid, 0.02)  # 0.47, 0.48
    assert ask_sh == 700
    assert m.book_imbalance(bid_sh, ask_sh) == pytest.approx((240 - 700) / 940)
    assert m.book_imbalance(0, 0) is None


def test_walk_book_and_price_impact():
    fills = m.walk_book(BOOK.asks, 500)
    assert fills == [(0.47, 340), (0.48, 160)]
    assert m.walk_book(BOOK.asks, 500, limit_price=0.47) == [(0.47, 340)]
    assert m.walk_book(BOOK.bids, 200, limit_price=0.45, side="sell") == [(0.45, 140)]
    impact = m.price_impact(BOOK.asks, 500)
    assert impact == pytest.approx((0.47 * 340 + 0.48 * 160) / 500 - 0.47)
    assert m.price_impact(BOOK.asks, 10_000) is None  # too thin


def test_drawdown_series_and_abs():
    eq = [100, 110, 99, 105, 120, 90]
    dd = m.drawdown_series(eq)
    assert dd[2] == pytest.approx(11 / 110) and dd[-1] == pytest.approx(30 / 120)
    assert max(dd) == pytest.approx(m.max_drawdown(eq))
    assert m.max_drawdown_abs(eq) == 30
