"""Feature formulas (hand-computed), NaN rules, no-trade windows, labels (wall-clock, executable,
insufficient depth) and exclusion of stale / crossed / warm-up / gap rows. SYNTHETIC events."""

import math

import pytest

from moneylab.domain.market_events import DISCONNECT
from moneylab.research.book_state import CROSSED, GAP, LOCKED, NO_BOOK, STALE, WARMUP_ROW
from moneylab.research.features import FEATURES, REGISTRY, book_features, trade_features
from moneylab.research.labels import compute_labels, exec_label_name
from moneylab.research.sampling import GridParams, build_grid
from research_helpers import T0, TICK, book, local, session, span, trade

nan = math.isnan


# --- book features ---------------------------------------------------------------------------

def test_book_features_hand_computed():
    bids = [(99_990 - 10 * i, 1.0 + i) for i in range(30)]
    asks = [(100_010 + 10 * i, 2.0) for i in range(30)]
    f = book_features(bids, asks)
    assert f["mid_price"] == 100_000 and f["spread"] == 20 and f["spread_bps"] == pytest.approx(2.0)
    assert f["microprice"] == pytest.approx((99_990 * 2 + 100_010 * 1) / 3)
    assert f["microprice_dev_bps"] == pytest.approx(1e4 * (f["microprice"] - 100_000) / 100_000)
    assert f["obi_1"] == pytest.approx((1 - 2) / 3)
    sb5 = sum(1.0 + i for i in range(5))
    assert f["obi_5"] == pytest.approx((sb5 - 10) / (sb5 + 10))
    assert f["bid_depth_10"] == pytest.approx(sum(1.0 + i for i in range(10))) and f["ask_depth_30"] == 60
    # 5 bp of 100_000 = 50: bids >= 99_950 -> 99_990..99_950 (5 levels), asks <= 100_050 -> 5 levels
    assert f["depth_imbalance_5bp"] == pytest.approx((sb5 - 10) / (sb5 + 10))
    sb30, sa30 = sum(1.0 + i for i in range(30)), 60.0
    assert f["liquidity_concentration"] == pytest.approx((sb5 + 10) / (sb30 + sa30))
    db, da = 1e4 * (100_000 - 99_900) / 100_000, 1e4 * (100_100 - 100_000) / 100_000
    assert f["book_slope"] == pytest.approx(math.log((sum(1.0 + i for i in range(10)) / db) / (20.0 / da)))


def test_book_features_are_nan_when_the_book_cannot_supply_them():
    f = book_features([(99.0, 1.0), (98.0, 2.0), (97.0, 3.0)], [(101.0, 2.0), (102.0, 1.0), (103.0, 1.0)])
    assert f["obi_1"] == pytest.approx(-1 / 3)
    for name in ("obi_5", "obi_10", "obi_30", "bid_depth_10", "ask_depth_30", "liquidity_concentration", "book_slope"):
        assert nan(f[name]), name
    assert nan(f["depth_imbalance_5bp"])  # nothing within 5 bp of the mid on either side: 0/0
    assert all(nan(v) for v in book_features([], [(1.0, 1.0)]).values())


def test_every_feature_has_lookback_metadata_and_registry_matches_config():
    from moneylab.research.config import load_config

    cfg = load_config()
    assert set(cfg.signals) | set(cfg.state) == set(REGISTRY)
    assert all(f.lookback_seconds >= 0 and f.unit and f.formula for f in FEATURES)
    assert REGISTRY["realized_vol_300s"].lookback_seconds == 300 and REGISTRY["obi_30"].lookback_seconds == 0


# --- trade features ---------------------------------------------------------------------------

def test_trade_features_windows_and_no_trade_window():
    trades = [(T0 + 9.2, 1, 1.0), (T0 + 9.9, -1, 3.0), (T0 + 6.0, 1, 2.0), (T0 + 4.0, -1, 5.0)]
    f = trade_features(trades, T0 + 10)
    assert f["signed_volume_1s"] == -2.0 and f["trade_flow_imbalance_1s"] == pytest.approx(-0.5)
    assert f["signed_volume_5s"] == 0.0 and f["trade_flow_imbalance_5s"] == 0.0  # (5, 10]: +1 -3 +2
    assert f["buy_intensity"] == pytest.approx(2 / 5) and f["sell_intensity"] == pytest.approx(1 / 5)
    empty = trade_features(trades, T0 + 100)
    assert empty["signed_volume_1s"] == 0.0 and nan(empty["trade_flow_imbalance_1s"])  # no trades: 0 and NaN
    assert empty["buy_intensity"] == 0.0


def test_no_trade_window_on_the_grid_is_zero_volume_and_nan_imbalance():
    evs = [local(1, T0)] + [book(i + 2, T0 + 0.05 + 0.1 * i, 100_000_000, 100_002_000) for i in range(200)]
    g = build_grid(evs, *span(evs))
    k = g.times.index(T0 + 15)
    assert g.cols["signed_volume_5s"][k] == 0.0 and nan(g.cols["trade_flow_imbalance_5s"][k])


# --- series features and discontinuities -------------------------------------------------------

def test_returns_and_realized_vol_use_grid_mids_and_stop_at_discontinuities():
    evs = session(200, disconnect_at=100.0)
    g = build_grid(evs, *span(evs))
    mid = g.cols["mid_price"]
    k = g.times.index(T0 + 60)
    assert g.cols["return_5s"][k] == pytest.approx(1e4 * math.log(mid[k] / mid[k - 5]))
    rv = math.sqrt(sum((1e4 * math.log(mid[j] / mid[j - 1])) ** 2 for j in range(k - 29, k + 1)))
    assert g.cols["realized_vol_30s"][k] == pytest.approx(rv)
    # rows around the reconnect are gap/warmup; windows crossing them are NaN
    after = g.times.index(T0 + 115)
    assert any(g.reasons[j] & {GAP, WARMUP_ROW} for j in range(after - 15, after))
    assert nan(g.cols["return_30s"][after]) and nan(g.cols["signed_volume_30s"][after])
    assert not nan(g.cols["obi_5"][after])  # lookback 0 is unaffected


# --- exclusions -------------------------------------------------------------------------------

def test_stale_crossed_locked_warmup_gap_rows_are_flagged():
    evs = [local(1, T0), book(2, T0 + 0.05, 100_000_000, 100_002_000, stream="SNAPSHOT")]
    seq = 3
    for i in range(1, 100):  # REALTIME every 0.1 s from 0.15 to 9.95
        evs.append(book(seq, T0 + 0.05 + 0.1 * i, 100_000_000, 100_002_000))
        seq += 1
    evs.append(book(seq, T0 + 13.0, 100_002_000, 100_002_000, flags={"locked_book"}))  # stale before, locked after
    evs.append(book(seq + 1, T0 + 14.5, 100_003_000, 100_002_000, flags={"crossed_book"}))
    evs.append(local(seq + 2, T0 + 15.2, DISCONNECT))
    evs.append(book(seq + 3, T0 + 16.9, 100_000_000, 100_002_000))
    g = build_grid(evs, T0, T0 + 17)
    r = {round(t - T0): g.reasons[k] for k, t in enumerate(g.times)}
    assert r[0] == {NO_BOOK}  # only the connection so far
    assert WARMUP_ROW in r[1] and WARMUP_ROW in r[5] and not r[6] and not r[9]  # first REALTIME 0.15 + 5 s
    assert STALE in r[12] and STALE not in r[10]
    assert LOCKED in r[13] and CROSSED in r[15]  # crossed book arrives at 14.5
    assert GAP in r[16]
    early = [local(1, T0 + 5)]
    g2 = build_grid(early + [book(2, T0 + 7.5, 1.0, 2.0)], T0 + 5, T0 + 8)
    assert NO_BOOK in g2.reasons[0]


def test_gap_seconds_turns_a_long_silence_into_a_discontinuity():
    evs = [book(1, T0 + 0.05, 100_000_000, 100_002_000), book(2, T0 + 30.0, 100_000_000, 100_002_000)]
    g = build_grid(evs, T0, T0 + 31, GridParams(gap_seconds=10.0))
    assert GAP in g.reasons[g.times.index(T0 + 20)] and g.is_discontinuity(g.times.index(T0 + 20))


# --- labels -----------------------------------------------------------------------------------

def test_mid_label_is_wall_clock_not_next_event():
    """Books at 6.05 (mid A), 9.95 (mid B), 30 (mid C). At t=7, h=1 the label uses the as-of book at 8
    (still A: move 0), not the next event (B)."""
    a, b_, c = 100_000_000, 100_010_000, 100_050_000
    evs = [book(1, T0 + 0.05, a - TICK, a + TICK)]
    evs += [book(i + 2, T0 + 0.05 + 0.5 * i, a - TICK, a + TICK) for i in range(1, 13)]  # keep fresh until 6.05
    evs += [book(20 + i, T0 + 6.55 + 0.5 * i, a - TICK, a + TICK) for i in range(6)]  # until 9.05
    evs += [book(40, T0 + 9.95, b_ - TICK, b_ + TICK)] + [book(41 + i, T0 + 10.45 + 0.5 * i, c - TICK, c + TICK)
                                                          for i in range(40)]
    g = build_grid(evs, T0, T0 + 30)
    lab = compute_labels(g, (1, 5))
    k7 = g.times.index(T0 + 7)
    assert lab["future_mid_move_bps_h1"][k7] == 0.0
    assert lab["future_mid_move_bps_h5"][k7] == pytest.approx(1e4 * (c / a - 1))  # as-of at 12: C
    assert lab["future_mid_return_h5"][k7] == pytest.approx(math.log(c / a))


def test_executable_labels_walk_the_book_and_are_nan_on_insufficient_depth():
    # 30 levels of 0.004 BTC: 0.001 fills at the best level, 0.01 needs three levels.
    m0, m1 = 100_000_000, 100_020_000
    evs = [book(i + 1, T0 + 0.05 + 0.1 * i, m0 - TICK, m0 + TICK, size=0.004) for i in range(100)]
    evs += [book(200 + i, T0 + 10.05 + 0.1 * i, m1 - TICK, m1 + TICK, size=0.004) for i in range(100)]
    g = build_grid(evs, T0, T0 + 20, GridParams(delays_ms=(0, 250)))
    lab = compute_labels(g, (5,))
    k = g.times.index(T0 + 7)  # exit at 12
    buy = lab[exec_label_name("buy", 5, 0.001, 0)][k]
    assert buy == pytest.approx(1e4 * ((m1 - TICK) / (m0 + TICK) - 1))
    sell = lab[exec_label_name("sell", 5, 0.001, 0)][k]
    assert sell == pytest.approx(1e4 * ((m0 - TICK) / (m1 + TICK) - 1))
    vwap_ask = (0.004 * (m0 + TICK) + 0.004 * (m0 + 2 * TICK) + 0.002 * (m0 + 3 * TICK)) / 0.01
    vwap_bid = (0.004 * (m1 - TICK) + 0.004 * (m1 - 2 * TICK) + 0.002 * (m1 - 3 * TICK)) / 0.01
    assert lab[exec_label_name("buy", 5, 0.01, 0)][k] == pytest.approx(1e4 * (vwap_bid / vwap_ask - 1))
    thin = [book(i + 1, T0 + 0.05 + 0.1 * i, m0 - TICK, m0 + TICK, size=0.0002) for i in range(200)]
    g2 = build_grid(thin, T0, T0 + 20)
    lab2 = compute_labels(g2, (5,))
    k2 = g2.times.index(T0 + 7)
    assert nan(lab2[exec_label_name("buy", 5, 0.01, 0)][k2])  # 30 * 0.0002 = 0.006 < 0.01: never filled
    assert not nan(lab2[exec_label_name("buy", 5, 0.001, 0)][k2])


def test_execution_delay_moves_the_entry_and_exit_samples():
    m0, m1 = 100_000_000, 100_030_000
    evs = [book(i + 1, T0 + 0.05 + 0.1 * i, m0 - TICK, m0 + TICK) for i in range(70)]  # to 6.95
    evs += [book(100, T0 + 7.1, m1 - TICK, m1 + TICK)]
    evs += [book(101 + i, T0 + 7.15 + 0.1 * i, m1 - TICK, m1 + TICK) for i in range(100)]
    g = build_grid(evs, T0, T0 + 17, GridParams(delays_ms=(0, 100, 250)))
    lab = compute_labels(g, (5,))
    k = g.times.index(T0 + 7)
    no_delay = lab[exec_label_name("buy", 5, 0.001, 0)][k]
    delayed = lab[exec_label_name("buy", 5, 0.001, 250)][k]
    assert no_delay == pytest.approx(1e4 * ((m1 - TICK) / (m0 + TICK) - 1))  # entered before the jump
    assert delayed == pytest.approx(1e4 * ((m1 - TICK) / (m1 + TICK) - 1))  # entry at 7.25 pays the jump


def test_labels_are_nan_across_gaps_and_from_excluded_rows():
    evs = session(200, disconnect_at=100.0)
    g = build_grid(evs, *span(evs))
    lab = compute_labels(g, (30,))
    k = g.times.index(T0 + 90)  # window crosses the reconnect
    assert nan(lab["future_mid_move_bps_h30"][k])
    assert all(nan(v) for name, col in lab.items() for v in [col[k]])
    w = g.times.index(T0 + 2)  # warm-up row
    assert g.reasons[w] and nan(lab["future_mid_move_bps_h30"][w])
    ok = g.times.index(T0 + 40)
    assert not nan(lab["future_mid_move_bps_h30"][ok])
    assert len(lab["future_mid_move_bps_h30"]) == len(g)
    assert all(nan(v) for v in lab["future_mid_move_bps_h30"][-30:])  # no forward fill at the end
