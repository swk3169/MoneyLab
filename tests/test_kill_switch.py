import pytest
from conftest import YES_TOKEN, make_book, make_params, make_snapshot

from moneylab.execution.base import OrderRequest
from moneylab.paper.engine import PaperExecutionClient
from moneylab.risk.kill_switch import KillSwitch, KillSwitchConfig, RiskSnapshot

GOOD = make_book(YES_TOKEN, [(0.49, 100)], [(0.51, 100)], ts=1000)


def snap(**kw):
    base = dict(now=1000, equity=1000, peak_equity=1000, daily_pnl=0.0, net_delta={"m": 0}, books={YES_TOKEN: GOOD})
    base.update(kw)
    return RiskSnapshot(**base)


def test_healthy_state_does_not_trip():
    ks = KillSwitch()
    assert not ks.check(snap()) and ks.allows_new_orders


@pytest.mark.parametrize(("kw", "reason"), [
    (dict(daily_pnl=-50), "daily_loss_limit"),
    (dict(equity=790), "max_drawdown"),
    (dict(net_delta={"m": -501}), "inventory_limit"),
    (dict(now=1121), "stale_market_data"),
    (dict(books={YES_TOKEN: None}), "stale_market_data"),
    (dict(books={YES_TOKEN: make_book(YES_TOKEN, [(0.30, 1)], [(0.55, 1)], ts=1000)}), "abnormal_spread"),
    (dict(books={YES_TOKEN: make_book(YES_TOKEN, [], [(0.55, 1)], ts=1000)}), "abnormal_spread"),
    (dict(books={YES_TOKEN: make_book(YES_TOKEN, [(0.56, 1)], [(0.55, 1)], ts=1000)}), "abnormal_spread"),
])
def test_each_condition_trips(kw, reason):
    ks = KillSwitch()
    assert ks.check(snap(**kw))
    assert any(r.startswith(reason) for r in ks.reasons)
    assert not ks.allows_new_orders


def test_spread_at_limit_is_allowed():
    book = make_book(YES_TOKEN, [(0.40, 1)], [(0.60, 1)], ts=1000)
    assert not KillSwitch(KillSwitchConfig(max_spread=0.20)).check(snap(books={YES_TOKEN: book}))


def test_manual_kill_flag(tmp_path):
    flag = tmp_path / "KILL"
    ks = KillSwitch(KillSwitchConfig(kill_flag_path=flag))
    assert not ks.check(snap())
    flag.write_text("stop", encoding="utf-8")
    assert ks.check(snap())
    assert ks.reasons[0].startswith("manual_kill_flag")


def test_consecutive_provider_errors():
    ks = KillSwitch(KillSwitchConfig(max_consecutive_errors=3))
    ks.record_error()
    ks.record_error()
    ks.record_success()  # resets the streak
    ks.record_error()
    ks.record_error()
    assert not ks.tripped
    assert ks.record_error()
    assert ks.reasons[0].startswith("provider_errors")


def test_latched_until_manual_reset():
    ks = KillSwitch()
    ks.check(snap(daily_pnl=-100))
    assert ks.check(snap())  # still tripped on a healthy snapshot
    with pytest.raises(ValueError):
        ks.reset("yes")
    ks.reset("RESET")
    assert ks.allows_new_orders and not ks.reasons


def test_trip_cancels_paper_orders_and_blocks_new_ones():
    engine = PaperExecutionClient(make_params(), 1000)
    engine.on_snapshot(make_snapshot(1000, [(0.49, 100)], [(0.51, 100)]))
    engine.submit(OrderRequest("0xcond", YES_TOKEN, "buy", 0.48, 10, post_only=True))
    engine.submit(OrderRequest("0xcond", YES_TOKEN, "buy", 0.47, 10, post_only=True))
    calls = []
    ks = KillSwitch()
    ks.on_trip(engine.halt)
    ks.on_trip(calls.append)
    ks.check(snap(equity=700))
    assert not engine.orders and engine.halted
    assert calls and calls[0][0].startswith("max_drawdown")
    ks.check(snap(equity=600))
    assert len(calls) == 1  # callbacks fire once
