import pytest

from moneylab.analytics.ev import all_in_price, maker_ev, taker_ev
from moneylab.domain.market_params import FeeSchedule
from moneylab.risk.inventory import assess_binary_inventory, inventory_room, reservation_price
from moneylab.sizing.position import (
    PortfolioState,
    SizingLimits,
    kelly_fraction_binary,
    size_capped,
    size_directional,
)

POL = FeeSchedule(rate=0.04, rebate_rate=0.25)
ASKS = [(0.50, 100), (0.51, 100), (0.52, 100)]


# --- EV --------------------------------------------------------------------------

def test_taker_ev_buy_walks_book_and_subtracts_fees():
    ev = taker_ev(0.60, ASKS, 250, "buy", POL)
    assert ev.shares == 250
    assert ev.vwap == pytest.approx((50 + 51 + 0.52 * 50) / 250)
    assert ev.gross_edge == pytest.approx(100 * 0.10 + 100 * 0.09 + 50 * 0.08)
    assert ev.slippage == pytest.approx((ev.vwap - 0.50) * 250)
    assert ev.fees == pytest.approx(1.0 + 0.04 * 100 * 0.51 * 0.49 + 0.04 * 50 * 0.52 * 0.48, abs=1e-5)
    assert ev.net_trading_ev == pytest.approx(ev.gross_edge - ev.fees)


def test_taker_ev_sell_and_thin_book():
    ev = taker_ev(0.40, [(0.45, 10)], 50, "sell", POL)
    assert ev.shares == 10 and ev.gross_edge == pytest.approx(0.5)
    assert taker_ev(0.5, [], 10, "buy", POL).shares == 0
    with pytest.raises(ValueError):
        taker_ev(1.5, ASKS, 1, "buy", POL)


def test_fee_can_kill_a_small_gross_edge():
    ev = taker_ev(0.505, ASKS, 100, "buy", POL)
    assert ev.gross_edge > 0 > ev.net_trading_ev


def test_all_in_price():
    assert all_in_price(0.5, 100, POL) == pytest.approx(0.51)


def test_maker_ev_separates_incentives():
    ev = maker_ev(0.50, 0.49, 100, "buy", fill_prob=0.5, schedule=POL, adverse_selection=0.015, estimated_reward=0.3)
    assert ev.net_trading_ev == pytest.approx(0.5 * 100 * (0.01 - 0.015))  # negative: adverse selection
    assert ev.estimated_rebate == pytest.approx(0.5 * 0.25 * 100 * 0.04 * 0.49 * 0.51)
    assert ev.all_in_estimated_ev > ev.net_trading_ev


# --- inventory risk ----------------------------------------------------------------

def test_inventory_assessment():
    r = assess_binary_inventory(yes_shares=300, no_shares=100, yes_mark=0.6)
    assert r.net_delta == 200 and r.paired_shares == 100
    assert r.mark_value == pytest.approx(300 * 0.6 + 100 * 0.4)
    assert r.value_if_yes == 300 and r.value_if_no == 100
    assert r.worst_case_loss == pytest.approx(220 - 100)
    flat = assess_binary_inventory(100, 100, 0.3)
    assert flat.net_delta == 0 and flat.worst_case_loss == pytest.approx(0)


def test_reservation_price_skews_against_inventory():
    assert reservation_price(0.5, 100, 0.0002) == pytest.approx(0.48)
    assert reservation_price(0.5, -100, 0.0002) == pytest.approx(0.52)
    assert reservation_price(0.02, 1000, 0.01) == 0.01  # clipped to [tick, 1 - tick]


def test_inventory_room():
    assert inventory_room(100, +1, 300) == 200
    assert inventory_room(100, -1, 300) == 400  # reducing first
    assert inventory_room(350, +1, 300) == 0


# --- fractional Kelly with caps ------------------------------------------------------

STATE = PortfolioState(equity=1000, peak_equity=1000)
LOOSE = SizingLimits(max_position_per_market=1e9, max_portfolio_exposure=1e9, max_inventory_shares=1e9, depth_fraction=1.0)


def test_kelly_formula():
    assert kelly_fraction_binary(0.6, 0.5) == pytest.approx(0.2)
    assert kelly_fraction_binary(0.5, 0.5) == 0
    assert kelly_fraction_binary(0.4, 0.5) == 0
    assert kelly_fraction_binary(0.9, 1.0) == 0


def test_default_is_quarter_kelly():
    assert SizingLimits().kelly_fraction == 0.25
    d = size_directional("m", 0.6, 0.5, 1e9, STATE, LOOSE)
    assert d.binding == "kelly" and d.size == pytest.approx(0.25 * 0.2 * 1000 / 0.5)  # 100 shares
    with pytest.raises(ValueError):
        SizingLimits(kelly_fraction=1.5)
    with pytest.raises(ValueError):
        SizingLimits(kelly_fraction=0)


def test_no_edge_no_order():
    assert size_directional("m", 0.5, 0.5, 1e9, STATE, LOOSE).size == 0
    assert size_directional("m", 0.5, 0.51, 1e9, STATE, LOOSE).binding == "no_edge"
    assert size_capped("m", 100, 0.5, 0.0, 1e9, STATE, LOOSE).size == 0
    assert size_capped("m", 100, 0.5, -0.01, 1e9, STATE, LOOSE).binding == "no_edge"


@pytest.mark.parametrize(("limits", "state", "depth", "binding", "size"), [
    (SizingLimits(max_position_per_market=20, max_portfolio_exposure=1e9, max_inventory_shares=1e9, depth_fraction=1),
     STATE, 1e9, "max_position_per_market", 40),
    (SizingLimits(max_position_per_market=1e9, max_portfolio_exposure=30, max_inventory_shares=1e9, depth_fraction=1),
     PortfolioState(1000, 1000, market_exposure={"other": 10}), 1e9, "max_portfolio_exposure", 40),
    (SizingLimits(max_position_per_market=1e9, max_portfolio_exposure=1e9, max_inventory_shares=1e9, depth_fraction=0.5),
     STATE, 60, "depth", 30),
    (SizingLimits(max_position_per_market=1e9, max_portfolio_exposure=1e9, max_inventory_shares=50, depth_fraction=1),
     PortfolioState(1000, 1000, net_delta={"m": 20}), 1e9, "inventory", 30),
])
def test_each_cap_binds(limits, state, depth, binding, size):
    d = size_directional("m", 0.6, 0.5, depth, state, limits)
    assert d.binding == binding and d.size == pytest.approx(size)
    assert d.kelly_size == pytest.approx(100)


def test_daily_loss_and_drawdown_gates():
    lim = SizingLimits(daily_loss_limit=50, max_drawdown=0.2)
    assert size_directional("m", 0.6, 0.5, 1e9, PortfolioState(950, 1000, daily_pnl=-50), lim).binding == "daily_loss_limit"
    assert size_directional("m", 0.6, 0.5, 1e9, PortfolioState(790, 1000, daily_pnl=0), lim).binding == "max_drawdown"
    assert size_capped("m", 10, 0.5, 0.01, 1e9, PortfolioState(790, 1000), lim).size == 0


def test_min_order_size_and_flooring():
    lim = SizingLimits(max_position_per_market=2.0, max_portfolio_exposure=1e9, max_inventory_shares=1e9, depth_fraction=1)
    d = size_directional("m", 0.6, 0.5, 1e9, STATE, lim, min_order_size=5)
    assert d.size == 0 and d.binding.startswith("below_min_order_size")
    lim2 = SizingLimits(max_position_per_market=3.333, max_portfolio_exposure=1e9, max_inventory_shares=1e9, depth_fraction=1)
    assert size_directional("m", 0.6, 0.5, 1e9, STATE, lim2).size == pytest.approx(6.66)


def test_capped_sizing_for_arbitrage_ignores_inventory():
    lim = SizingLimits(max_position_per_market=1e9, max_portfolio_exposure=1e9, max_inventory_shares=1, depth_fraction=1)
    d = size_capped("m", 100, 0.98, 0.01, 100, STATE, lim, delta_direction=0.0)
    assert d.size == 100 and d.binding == "requested"
