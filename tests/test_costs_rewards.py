"""Fee, rebate and liquidity-reward models, and estimated/realized incentive separation."""

import pytest
from conftest import make_params

from moneylab.analytics import costs, rewards
from moneylab.analytics.rewards import RewardOrder
from moneylab.domain.market_params import FeeSchedule, RewardAllocation, RewardConfig
from moneylab.execution.base import Fill
from moneylab.pnl.ledger import Ledger
from moneylab.pnl.report import evaluate_adoption

CRYPTO = FeeSchedule(rate=0.07, rebate_rate=0.20)
POLITICS = FeeSchedule(rate=0.04, rebate_rate=0.25)
SPORTS = FeeSchedule(rate=0.05, rebate_rate=0.15)


# --- taker fees: documented 100-share tables --------------------------------------

@pytest.mark.parametrize(("sched", "price", "expected"), [
    (CRYPTO, 0.50, 1.75), (CRYPTO, 0.30, 1.47), (CRYPTO, 0.01, 0.0693),
    (POLITICS, 0.50, 1.00), (POLITICS, 0.30, 0.84), (SPORTS, 0.50, 1.25), (SPORTS, 0.10, 0.45),
])
def test_fee_matches_documented_table(sched, price, expected):
    assert costs.taker_fee(100, price, sched) == pytest.approx(expected)


def test_fee_symmetric_around_half():
    assert costs.taker_fee(100, 0.30, CRYPTO) == costs.taker_fee(100, 0.70, CRYPTO)


def test_fee_rounding_5_decimals_and_minimum():
    assert costs.taker_fee(1, 0.01, POLITICS) == 0.0004  # 0.000396 -> 0.00040
    assert costs.taker_fee(0.001, 0.01, POLITICS) == 0.0  # below 0.000005 rounds to 0
    assert costs.round_fee(0.000015) == 0.00002  # half-up
    assert costs.round_fee(0.0000049) == 0.0
    assert costs.round_fee(1.234564) == 1.23456


def test_fee_free_and_maker_fees():
    assert costs.taker_fee(100, 0.5, FeeSchedule.free()) == 0.0
    assert costs.taker_fee(100, 0.5, FeeSchedule(rate=0.0)) == 0.0  # geopolitics
    assert costs.maker_fee(100, 0.5, POLITICS) == 0.0  # makers never pay (takerOnly)
    assert costs.maker_fee(100, 0.5, FeeSchedule(rate=0.04, taker_only=False)) == 1.0
    with pytest.raises(ValueError):
        costs.taker_fee(1, 1.2, POLITICS)


def test_fee_exponent_interpretation():
    sched = FeeSchedule(rate=0.04, exponent=2)
    assert costs.fee_curve(100, 0.5, sched) == pytest.approx(100 * 0.04 * 0.25 ** 2)


def test_fee_for_fills_is_per_level():
    fills = [(0.5, 100), (0.51, 50)]
    assert costs.taker_fee_for_fills(fills, POLITICS) == pytest.approx(1.0 + costs.taker_fee(50, 0.51, POLITICS))


# --- maker rebate estimate --------------------------------------------------------

def test_estimated_rebate_and_payout_threshold():
    fe = [costs.fee_equivalent(100, 0.5, POLITICS), costs.fee_equivalent(100, 0.3, POLITICS)]
    assert costs.estimated_maker_rebate(fe, POLITICS) == pytest.approx(0.25 * (1.0 + 0.84))
    assert costs.estimated_maker_rebate(fe, FeeSchedule.free()) == 0.0
    assert costs.apply_payout_threshold(0.99) == 0.0
    assert costs.apply_payout_threshold(1.0) == 1.0


# --- liquidity rewards: documented worked example -----------------------------------

CFG = RewardConfig(max_spread_cents=3, min_size=0, allocations=(RewardAllocation(100),))


def test_order_score():
    assert rewards.order_score(3, 1) == pytest.approx((2 / 3) ** 2)
    assert rewards.order_score(3, 0) == 1.0
    assert rewards.order_score(3, 3) == 0.0 and rewards.order_score(3, 4) == 0.0
    assert rewards.order_score(3, 1, multiplier=2) == pytest.approx(2 * (2 / 3) ** 2)


def test_docs_worked_example_q_one_q_two():
    one = [RewardOrder("bid", 0.49, 100), RewardOrder("bid", 0.48, 200), RewardOrder("ask", 0.51, 100, complement=True)]
    two = [RewardOrder("bid", 0.485, 100, complement=True), RewardOrder("bid", 0.48, 100, complement=True),
           RewardOrder("ask", 0.505, 200)]
    q_one, _ = rewards.side_scores(one, 0.50, CFG)
    assert q_one == pytest.approx((2 / 3) ** 2 * 100 + (1 / 3) ** 2 * 200 + (2 / 3) ** 2 * 100)  # 111.11
    _, q_two = rewards.side_scores(two, 0.50, CFG)
    assert q_two == pytest.approx((1.5 / 3) ** 2 * 100 + (1 / 3) ** 2 * 100 + (2.5 / 3) ** 2 * 200)  # 175.0
    assert rewards.q_min(q_one, q_two, 0.50) == pytest.approx(q_one)  # min(111.1, 175) beats max/3


def test_q_min_single_sided_rules():
    assert rewards.q_min(90, 0, 0.50) == pytest.approx(30)  # in [0.10, 0.90]: Q/c still scores
    assert rewards.q_min(90, 0, 0.95) == 0  # extreme midpoint: must be two-sided
    assert rewards.q_min(90, 60, 0.05) == 60


def test_min_size_and_complement_midpoint():
    cfg = RewardConfig(max_spread_cents=3, min_size=50)
    q1, q2 = rewards.side_scores([RewardOrder("bid", 0.49, 49)], 0.5, cfg)
    assert q1 == q2 == 0.0
    # NO bid at 0.29 when YES mid is 0.70: complement mid 0.30, spread 1c -> scores in Q_two
    q1, q2 = rewards.side_scores([RewardOrder("bid", 0.29, 50, complement=True)], 0.70, cfg)
    assert q1 == 0 and q2 == pytest.approx((2 / 3) ** 2 * 50)


def test_adjusted_midpoint_ignores_small_levels():
    bids, asks = [(0.49, 10), (0.48, 100)], [(0.51, 100)]
    assert rewards.adjusted_midpoint(bids, asks, 50) == pytest.approx(0.495)
    assert rewards.adjusted_midpoint(bids, asks, 0) == pytest.approx(0.50)
    assert rewards.adjusted_midpoint([(0.49, 10)], asks, 50) is None


def test_reward_estimates():
    assert rewards.sample_share(30, 70) == pytest.approx(0.3)
    assert rewards.sample_share(0, 0) == 0
    assert rewards.estimated_reward_for_interval(100, 0.3, 3600) == pytest.approx(100 * 0.3 / 24)
    assert rewards.estimated_epoch_reward(144, [0.5] * 720) == pytest.approx(36)


# --- estimated vs realized separation in the ledger ----------------------------------

def _maker_fill(price=0.5, size=100, side="buy"):
    return Fill("o1", "m", "YES-T", side, price, size, "maker", 0.0, mid_ref=price + 0.01, top_ref=price,
                timestamp=1.0, fee_equivalent=costs.fee_equivalent(size, price, POLITICS))


def test_rebate_estimated_is_not_realized():
    led = Ledger(1000)
    led.record_fill(_maker_fill(), rebate_rate=0.25)
    b = led.breakdown({"YES-T": 0.5})
    assert b.estimated_maker_rebate == pytest.approx(0.25)  # 0.25 * 100*0.04*0.25
    assert b.realized_maker_rebate == 0.0
    assert b.all_in_realized_pnl == pytest.approx(b.net_trading_pnl_after_cost)
    assert b.all_in_estimated_pnl == pytest.approx(b.net_trading_pnl_after_cost + 0.25)
    assert led.trading_equity({"YES-T": 0.5}) == 1000  # incentives never enter equity
    led.record_realized_maker_rebate(0.20)
    b = led.breakdown({"YES-T": 0.5})
    assert b.realized_maker_rebate == 0.20 and b.estimated_maker_rebate == pytest.approx(0.25)
    assert b.all_in_realized_pnl == pytest.approx(b.net_trading_pnl_after_cost + 0.20)


def test_reward_estimated_is_not_realized():
    led = Ledger(1000)
    led.add_estimated_liquidity_reward(3.0)
    b = led.breakdown({})
    assert b.estimated_liquidity_reward == 3.0 and b.realized_liquidity_reward == 0.0
    assert b.all_in_realized_pnl == 0.0
    led.record_realized_liquidity_reward(1.5)
    assert led.breakdown({}).all_in_realized_pnl == 1.5


def test_adoption_rejects_strategy_that_needs_incentives():
    led = Ledger(1000)
    led.record_fill(_maker_fill(price=0.5), rebate_rate=0.25)
    led.add_estimated_liquidity_reward(5.0)
    b = led.breakdown({"YES-T": 0.45})  # spread +1, inventory -6
    assert b.net_trading_pnl_after_cost < 0 < b.all_in_estimated_pnl
    verdict = evaluate_adoption(b, n_trades=500, synthetic_data=False)
    assert verdict.status == "REJECT" and not verdict.adopt
    assert any("estimated incentives" in r for r in verdict.reasons)


def test_adoption_never_accepts_synthetic_or_small_samples():
    led = Ledger(1000)
    led.record_fill(_maker_fill(price=0.5), rebate_rate=0.25)
    b = led.breakdown({"YES-T": 0.6})
    assert evaluate_adoption(b, 500, synthetic_data=True).status == "INSUFFICIENT_EVIDENCE"
    assert evaluate_adoption(b, 5, synthetic_data=False).status == "INSUFFICIENT_EVIDENCE"
    assert evaluate_adoption(b, 500, synthetic_data=False).status == "CANDIDATE"


def test_params_helper_fee():
    assert make_params().fee.rate == 0.04
