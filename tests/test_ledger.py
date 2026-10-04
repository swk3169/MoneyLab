"""PnL decomposition: gross = spread_captured - slippage + inventory_pnl == cash + positions*marks."""

import random

import pytest

from moneylab.execution.base import Fill
from moneylab.pnl.ledger import Ledger


def fill(side, price, size, liq="maker", mid=None, top=None, fee=0.0, token="Y", group=None, oid="o"):
    return Fill(oid, "m", token, side, price, size, liq, fee, mid_ref=price if mid is None else mid,
                top_ref=price if top is None else top, timestamp=0.0, group_id=group)


def test_maker_round_trip_decomposition():
    led = Ledger(1000)
    led.record_fill(fill("buy", 0.49, 100, mid=0.50, oid="a"))  # +1 spread
    led.record_fill(fill("sell", 0.53, 100, mid=0.52, oid="b"))  # +1 spread
    b = led.breakdown({"Y": 0.60})
    assert b.spread_captured == pytest.approx(2.0)
    assert b.inventory_pnl == pytest.approx(100 * (0.60 - 0.50) - 100 * (0.60 - 0.52))  # = 2.0
    assert b.gross_trading_pnl == pytest.approx(4.0)  # 0.53 - 0.49 on 100
    assert b.identity_holds
    assert led.trade_pnls()[0] == [pytest.approx(4.0)]


def test_taker_spread_and_slippage_are_costs():
    led = Ledger(1000)
    # mid 0.50, best ask 0.51, VWAP 0.515, fee 1.0
    led.record_fill(fill("buy", 0.515, 100, liq="taker", mid=0.50, top=0.51, fee=1.0))
    b = led.breakdown({"Y": 0.50})
    assert b.spread_captured == pytest.approx(-1.0)  # half spread paid
    assert b.slippage == pytest.approx(0.5)
    assert b.inventory_pnl == pytest.approx(0.0)
    assert b.gross_trading_pnl == pytest.approx(-1.5)
    assert b.net_trading_pnl_after_cost == pytest.approx(-2.5)
    assert b.trading_costs == 1.0 and b.identity_holds


def test_identity_holds_for_random_fill_sequences():
    rng = random.Random(7)
    for _ in range(50):
        led = Ledger(1000)
        held = {"Y": 0.0, "N": 0.0}
        for i in range(40):
            token = rng.choice(["Y", "N"])
            side = "sell" if held[token] > 10 and rng.random() < 0.4 else "buy"
            size = min(rng.uniform(1, 50), held[token]) if side == "sell" else rng.uniform(1, 50)
            price = round(rng.uniform(0.05, 0.95), 2)
            liq = rng.choice(["maker", "taker"])
            led.record_fill(fill(side, price, size, liq, mid=price + rng.uniform(-0.03, 0.03),
                                 top=price - rng.uniform(0, 0.02), fee=rng.uniform(0, 0.5), token=token, oid=f"o{i}"))
            held[token] += size if side == "buy" else -size
        marks = {"Y": rng.random(), "N": rng.random()}
        b = led.breakdown(marks)
        assert b.identity_holds
        assert led.trading_equity(marks) == pytest.approx(1000 + b.net_trading_pnl_after_cost)


def test_settlement_realizes_inventory_and_closes_trades():
    led = Ledger(1000)
    led.record_fill(fill("buy", 0.40, 100, liq="taker", mid=0.39, top=0.40, fee=0.96, token="Y", group="g1"))
    led.record_fill(fill("buy", 0.55, 100, liq="taker", mid=0.54, top=0.55, fee=0.99, token="N", group="g1"))
    led.settle({"Y": 1.0, "N": 0.0}, timestamp=10)
    b = led.breakdown({})
    assert led.positions() == {"Y": 0.0, "N": 0.0}
    assert b.gross_trading_pnl == pytest.approx(100 - 40 - 55)
    assert b.identity_holds
    pnls, open_n = led.trade_pnls({})
    assert pnls == [pytest.approx(5 - 0.96 - 0.99)] and open_n == 0  # one paired trade
    assert led.taker_fills == 2 and led.maker_fills == 0  # settlement is not a fill


def test_open_lots_marked_for_trade_stats():
    led = Ledger(1000)
    led.record_fill(fill("buy", 0.40, 10, oid="a"))
    assert led.trade_pnls() == ([], 0)
    pnls, open_n = led.trade_pnls({"Y": 0.45})
    assert pnls == [pytest.approx(0.5)] and open_n == 1


def test_equity_curve():
    led = Ledger(100)
    led.record_fill(fill("buy", 0.5, 10, fee=0.1))
    assert led.mark(1, {"Y": 0.6}) == pytest.approx(100 - 5 - 0.1 + 6)
    assert led.equity_curve == [(1, pytest.approx(100.9))]
