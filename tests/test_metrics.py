import math

import pytest

from moneylab.analytics import metrics as mx


def test_net_return():
    assert mx.net_return(1000, 1100) == pytest.approx(0.10)
    with pytest.raises(ValueError):
        mx.net_return(0, 1)


def test_win_rate_profit_factor_ev():
    pnls = [10, -5, 20, -5, 0]
    assert mx.win_rate(pnls) == pytest.approx(0.4)
    assert mx.profit_factor(pnls) == pytest.approx(3.0)
    assert mx.expected_value_trades(pnls) == pytest.approx(4.0)
    assert mx.win_rate([]) is None
    assert math.isinf(mx.profit_factor([1, 2]))


def test_max_drawdown():
    assert mx.max_drawdown([100, 120, 90, 130, 104]) == pytest.approx(0.25)
    assert mx.max_drawdown([100, 110, 120]) == 0.0


def test_expected_value_binary_includes_costs():
    # buy YES at 0.60, believe 70%: gross edge 0.10, minus 1% fee on 0.60 and 0.01 slippage
    ev = mx.expected_value_binary(0.70, 0.60, fee_rate=0.01, slippage=0.01)
    assert ev == pytest.approx(0.70 - 0.60 - 0.006 - 0.01)


def test_spread_slippage_costs():
    assert mx.spread(0.61, 0.63) == pytest.approx(0.02)
    assert mx.relative_spread(0.61, 0.63) == pytest.approx(0.02 / 0.62)
    assert mx.slippage(0.50, 0.52, "buy") == pytest.approx(0.02)
    assert mx.slippage(0.50, 0.48, "sell") == pytest.approx(0.02)
    assert mx.transaction_cost(0.5, 100, 0.02, fixed_fee=0.1) == pytest.approx(1.1)


def test_vwap_fill():
    book = [(0.50, 100), (0.52, 100)]
    assert mx.vwap_fill(book, 150) == pytest.approx((50 + 26) / 150)
    assert mx.vwap_fill(book, 300) is None
