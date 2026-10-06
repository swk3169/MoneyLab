"""UpbitRecorder over scripted (SYNTHETIC) WebSocket sessions: storage, heartbeat, reconnect/backoff,
rate-limit policy, duplicates, restart/resume and provenance separation. No network."""

import json
import random
from pathlib import Path

import pytest

from moneylab.providers.upbit.endpoints import WS_PUBLIC_URL
from moneylab.providers.upbit.recorder import (
    DatasetMismatch,
    ScriptedWsSource,
    UpbitRecorder,
    UpbitRecorderConfig,
    UpbitStore,
    verify_upbit_recording,
)
from moneylab.providers.upbit.recorder.store import read_json, read_segment, segment_paths
from moneylab.recording.core import RecorderStatus
from upbit_helpers import FIXTURE, T0, book, frames, lines, make_recorder, scripted, sleeps_of, trade


# --- end to end over the generated fixture -----------------------------------------------

def test_fixture_session_end_to_end(tmp_path):
    src = ScriptedWsSource(FIXTURE)
    rec = UpbitRecorder(src, WS_PUBLIC_URL, tmp_path, UpbitRecorderConfig(ping_text_interval=3.0),
                        provenance="fixture", origin=f"fixture:{FIXTURE.name}", clock=src.clock, sleep=src.sleep,
                        rng=random.Random(1))
    rep = rec.run()
    assert rep.status == RecorderStatus.SOURCE_EXHAUSTED and rep.ok
    assert rep.connections == 2 and rep.connect_failures == 1 and rep.rate_limited == 1
    assert rep.orderbook_events == 33 and rep.trade_events == 13 and rep.disconnects == 1
    assert rep.duplicate_trades == 1 and rep.duplicate_orderbooks == 1 and rep.parse_errors == 1
    assert rep.pings_sent >= 3 and rep.status_replies == rep.pings_sent
    ds = read_json(tmp_path / "KRW-BTC" / "dataset.json")
    assert ds["provenance"] == "fixture" and ds["synthetic"] is True and ds["orderbook_units"] == 30
    assert ds["origin"] == "fixture:upbit_ws_timeline_synthetic.json"
    all_lines = lines(tmp_path)
    assert [ln["local_sequence"] for ln in all_lines] == list(range(1, len(all_lines) + 1))
    assert {ln["provenance"] for ln in all_lines} == {"fixture"}
    assert verify_upbit_recording(tmp_path / "KRW-BTC").ok


def test_raw_messages_are_stored_verbatim_with_required_fields(tmp_path):
    raw_trade = ('{"type":"trade","code":"KRW-BTC","timestamp":1800000000105,"trade_timestamp":1800000000100,'
                 '"trade_price":116409000.00000000,"trade_volume":0.00054978,"ask_bid":"ASK",'
                 '"sequential_id":17912821512190000,"stream_type":"REALTIME"}')
    src = scripted([{"frames": frames(book(1_800_000_000_050, 116_378_000.0, 116_408_000.0, 0.5),
                                      {"raw_text": raw_trade})}])
    make_recorder(src, tmp_path).run()
    ob, tr = [ln for ln in lines(tmp_path) if ln["event_type"] in ("orderbook", "trade")]
    assert tr["raw"] == raw_trade  # exact server text, including "116409000.00000000"
    for ln in (ob, tr):
        for key in ("raw", "event_type", "market", "exchange_timestamp", "received_timestamp", "connection_id",
                    "local_sequence", "provenance", "received_at", "raw_sha256", "checksum"):
            assert key in ln, key
        assert ln["market"] == "KRW-BTC" and ln["frame"] == "binary"
    assert ob["exchange_timestamp"] == 1_800_000_000_050 and ob["received_timestamp"] == pytest.approx(T0 + 0.1)
    assert ob["orderbook"]["best_bid"] == 116_378_000.0 and ob["orderbook"]["best_ask"] == 116_408_000.0
    assert ob["orderbook"]["spread"] == 30_000.0
    assert ob["orderbook"]["bid_depth"] == 0.5 and ob["orderbook"]["ask_depth"] == 0.5
    assert tr["trade"] == {"sequential_id": 17912821512190000, "trade_price": 116409000.0,
                           "trade_volume": 0.00054978, "ask_bid": "ASK", "trade_timestamp": 1800000000100,
                           "stream_type": "REALTIME"}
    assert tr["exchange_timestamp"] == 1800000000105  # documented `timestamp`, kept apart from trade_timestamp
    assert ob["connection_id"] == tr["connection_id"]


def test_subscription_request_is_sent_first(tmp_path):
    src = scripted([{"frames": frames(book(1))}])
    make_recorder(src, tmp_path, orderbook_units=30).run()
    assert json.loads(src.sent[0]) == [{"ticket": "ticket"}, {"type": "orderbook", "codes": ["KRW-BTC.30"]},
                                       {"type": "trade", "codes": ["KRW-BTC"]}, {"format": "DEFAULT"}]
    conn = next(ln for ln in lines(tmp_path) if ln["event_type"] == "connection")
    assert conn["detail"]["url"] == WS_PUBLIC_URL and conn["raw"] is None


# --- heartbeat / stale -------------------------------------------------------------------

def test_ping_text_heartbeat_and_status_reply(tmp_path):
    many = [book(1_800_000_000_000 + i * 1000, bid=100 + i % 2) for i in range(40)]
    src = scripted([{"ping_reply": True, "frames": frames(*many, step=1.0)}])
    rep = make_recorder(src, tmp_path, ping_text_interval=10.0).run()
    pings = [s for s in src.sent if s == "PING"]
    assert len(pings) == rep.pings_sent and 3 <= len(pings) <= 4  # every 10 s over ~40 s
    assert rep.status_replies == len(pings)
    status = [ln for ln in lines(tmp_path) if ln["event_type"] == "status"]
    assert status and status[0]["raw"] == '{"status":"UP"}' and status[0]["market"] is None


def test_ping_interval_must_stay_below_idle_timeout():
    with pytest.raises(ValueError):
        UpbitRecorderConfig(ping_text_interval=120.0)


def test_stale_stream_triggers_reconnect(tmp_path):
    first = frames(book(1), start=T0)
    later = frames(book(2, bid=99.0), start=T0 + 100)  # 100 s of silence
    src = scripted([{"frames": first + later}, {"frames": frames(book(3, bid=98.0), start=T0 + 200)}])
    rep = make_recorder(src, tmp_path, stale_timeout=30.0, ping_text_interval=60.0).run()
    assert rep.disconnects >= 1 and rep.connections == 2
    disc = [ln for ln in lines(tmp_path) if ln["event_type"] == "disconnect"]
    assert disc[0]["detail"]["category"] == "stale"


# --- failure policy ----------------------------------------------------------------------

def test_http_451_stops_immediately_without_retry(tmp_path):
    src = scripted([{"handshake": {"status": 451, "reason": "Unavailable For Legal Reasons", "body": "blocked"}},
                    {"frames": frames(book(1))}])
    rep = make_recorder(src, tmp_path).run()
    assert rep.status == RecorderStatus.BLOCKED_HTTP_451 and not rep.ok
    assert len(src.urls) == 1
    state = read_json(tmp_path / "KRW-BTC" / "state.json")
    assert state["status"] == "blocked_http_451" and state["blocked"]["status_code"] == 451
    assert "does not infer" in state["blocked"]["diagnostics"]["note"]


@pytest.mark.parametrize("code", [401, 403])
def test_access_denied_stops(tmp_path, code):
    src = scripted([{"handshake": {"status": code}}, {"frames": frames(book(1))}])
    assert make_recorder(src, tmp_path).run().status == RecorderStatus.ACCESS_DENIED
    assert len(src.urls) == 1


def test_429_waits_at_least_one_second(tmp_path):
    src = scripted([{"handshake": {"status": 429}}, {"frames": frames(book(1), start=T0 + 5)}])
    waits, src.sleep = sleeps_of(src)
    rep = make_recorder(src, tmp_path).run()
    assert rep.rate_limited == 1 and rep.orderbook_events == 1
    assert max(waits) >= 1.0


def test_418_honours_stated_ban(tmp_path):
    src = scripted([{"handshake": {"status": 418, "headers": {"Retry-After": "45"}}},
                    {"frames": frames(book(1), start=T0 + 100)}])
    waits, src.sleep = sleeps_of(src)
    rep = make_recorder(src, tmp_path).run()
    assert rep.banned == 1 and rep.orderbook_events == 1 and 45.0 in waits


def test_418_without_duration_uses_default_wait(tmp_path):
    src = scripted([{"handshake": {"status": 418}}, {"frames": frames(book(1), start=T0 + 100)}])
    waits, src.sleep = sleeps_of(src)
    make_recorder(src, tmp_path, ban_default_wait=75.0).run()
    assert 75.0 in waits


def test_418_ban_longer_than_allowed_stops(tmp_path):
    src = scripted([{"handshake": {"status": 418, "headers": {"Retry-After": "3600"}}}, {"frames": frames(book(1))}])
    waits, src.sleep = sleeps_of(src)
    rep = make_recorder(src, tmp_path, max_ban_wait=600.0).run()
    assert rep.status == RecorderStatus.BANNED_HTTP_418 and not rep.ok
    assert len(src.urls) == 1 and not any(w >= 600 for w in waits)


def test_max_consecutive_failures_ends_reconnect_loop(tmp_path):
    src = scripted([{"connect_error": "refused"}] * 50)
    waits, src.sleep = sleeps_of(src)
    rep = make_recorder(src, tmp_path, max_consecutive_failures=4, backoff_base=1.0, backoff_max=8.0).run()
    assert rep.status == RecorderStatus.FAILED and len(src.urls) == 4
    backoffs = [w for w in waits if w >= 0.5]
    assert len(backoffs) == 3 and backoffs == sorted(backoffs)  # exponential (with jitter), then stop
    fails = [ln for ln in lines(tmp_path) if ln["event_type"] == "failure"]
    assert [f["detail"]["consecutive_failures"] for f in fails] == [1, 2, 3, 4]


def test_connects_are_spaced_by_rate_limit(tmp_path):
    src = scripted([{"connect_error": "x"}] * 3)
    connect_times = []
    orig = src.__call__

    def connector(url):
        connect_times.append(src.now)
        return orig(url)

    rec = UpbitRecorder(connector, WS_PUBLIC_URL, tmp_path, UpbitRecorderConfig(
        orderbook_units=1, backoff_base=0.01, backoff_max=0.01, max_consecutive_failures=3, min_connect_spacing=1.0),
        provenance="fixture", origin="fixture:test", clock=src.clock, sleep=src.sleep, rng=random.Random(1))
    rec.run()
    assert all(b - a >= 1.0 - 1e-9 for a, b in zip(connect_times, connect_times[1:]))


def test_session_with_data_resets_failure_count(tmp_path):
    conns = []
    for i in range(6):  # each session delivers data, then the server closes it
        conns.append({"frames": frames(book(i + 1, bid=100 - i), start=T0 + i * 10), "close": {"code": 1006}})
    rep = make_recorder(scripted(conns), tmp_path, max_consecutive_failures=2).run()
    assert rep.status == RecorderStatus.SOURCE_EXHAUSTED and rep.connections == 6


def test_server_error_message_reconnects_then_gives_up(tmp_path):
    err = {"raw_text": '{"error":{"name":"INVALID_PARAM","message":"synthetic"}}'}
    src = scripted([{"frames": frames(err)}] * 5)
    rep = make_recorder(src, tmp_path, max_consecutive_failures=3).run()
    assert rep.status == RecorderStatus.FAILED and rep.server_errors == 3
    se = [ln for ln in lines(tmp_path) if ln["event_type"] == "server_error"]
    assert se[0]["detail"] == {"name": "INVALID_PARAM", "message": "synthetic"}


# --- stop rules ----------------------------------------------------------------------------

def test_duration_and_max_events_and_stop(tmp_path):
    many = [book(1_800_000_000_000 + i * 1000, bid=100 + i % 3) for i in range(30)]
    rep = make_recorder(scripted([{"frames": frames(*many, step=1.0)}]), tmp_path / "a", duration=10.0).run()
    assert rep.status == RecorderStatus.COMPLETED and 8 <= rep.orderbook_events <= 11
    rep = make_recorder(scripted([{"frames": frames(*many)}]), tmp_path / "b", max_market_events=5).run()
    assert rep.status == RecorderStatus.COMPLETED and rep.orderbook_events == 5
    rec = make_recorder(scripted([{"frames": frames(*many)}]), tmp_path / "c")
    rec.stop()
    assert rec.run().status == RecorderStatus.STOPPED


# --- duplicates ----------------------------------------------------------------------------

def test_trade_duplicates_by_sequential_id(tmp_path):
    src = scripted([{"frames": frames(trade(10, 1), trade(11, 2), trade(10, 1, stream_type="SNAPSHOT"),
                                      trade(12, 3))}])
    rep = make_recorder(src, tmp_path).run()
    assert rep.trade_events == 4 and rep.duplicate_trades == 1
    trades = [ln for ln in lines(tmp_path) if ln["event_type"] == "trade"]
    dup = [t for t in trades if t["duplicate"]]
    assert len(dup) == 1 and dup[0]["trade"]["sequential_id"] == 10
    assert dup[0]["duplicate_of"] == trades[0]["local_sequence"]
    assert dup[0]["raw"]  # kept on disk (lossless), only flagged


def test_orderbook_duplicates_are_conservative(tmp_path):
    src = scripted([{"frames": frames(
        book(1000), book(1000, stream_type="SNAPSHOT"),  # same ts + same content -> duplicate
        book(2000),  # same content, new timestamp -> a normal unchanged book, kept
        book(2000, size=2.0),  # same timestamp, different content -> kept
        book(3000), book(1000),  # an old (ts, content) seen before -> duplicate
    )}])
    rep = make_recorder(src, tmp_path).run()
    flags = [ln["duplicate"] for ln in lines(tmp_path) if ln["event_type"] == "orderbook"]
    assert flags == [False, True, False, False, False, True] and rep.duplicate_orderbooks == 2


# --- malformed / routing -------------------------------------------------------------------

def test_malformed_frames_are_kept_and_flagged(tmp_path):
    bad_book = book(5)
    bad_book["orderbook_units"][0]["bid_size"] = "lots"
    src = scripted([{"frames": frames({"raw_bytes_hex": "fffe00"}, {"raw_text": "{oops"}, bad_book,
                                      book(6, code="KRW-ETH"), {"raw_text": '{"type":"ticker","code":"KRW-BTC"}'},
                                      book(7))}])
    rep = make_recorder(src, tmp_path).run()
    assert rep.parse_errors == 3 and rep.unknown_messages == 2 and rep.orderbook_events == 1
    by_type = {}
    for ln in lines(tmp_path):
        by_type.setdefault(ln["event_type"], []).append(ln)
    binary = by_type["malformed"][0]
    assert binary["raw"] is None and binary["raw_base64"] == "//4A"
    assert by_type["malformed"][1]["raw"] == "{oops"
    ob_bad = by_type["orderbook"][0]
    assert ob_bad["parse_error"] and "orderbook" not in ob_bad and ob_bad["exchange_timestamp"] == 5
    assert "unsubscribed market" in by_type["unknown"][0]["parse_error"]
    assert verify_upbit_recording(tmp_path / "KRW-BTC").ok


def test_multiple_markets_are_routed_to_their_datasets(tmp_path):
    src = scripted([{"frames": frames(book(1), book(2, code="KRW-ETH"), trade(5, 3, code="KRW-ETH"))}])
    make_recorder(src, tmp_path, markets=("KRW-BTC", "KRW-ETH")).run()
    assert [ln["event_type"] for ln in lines(tmp_path, "KRW-BTC") if ln["event_type"] in ("orderbook", "trade")] \
        == ["orderbook"]
    assert [ln["event_type"] for ln in lines(tmp_path, "KRW-ETH") if ln["event_type"] in ("orderbook", "trade")] \
        == ["orderbook", "trade"]
    assert json.loads(src.sent[0])[1]["codes"] == ["KRW-BTC.1", "KRW-ETH.1"]


# --- storage: segments, restart/resume, crash ---------------------------------------------

def test_segments_flush_on_size_and_time(tmp_path):
    many = [book(1_800_000_000_000 + i, bid=100 + i % 2) for i in range(25)]
    make_recorder(scripted([{"frames": frames(*many, step=0.01)}]), tmp_path, flush_max_events=10,
                  flush_interval=999).run()
    sizes = [len(read_segment(p)) for p in segment_paths(tmp_path / "KRW-BTC")]
    assert max(sizes) <= 10 + 1 and sum(sizes) == len(lines(tmp_path))
    for p in segment_paths(tmp_path / "KRW-BTC"):
        assert int(p.stem) == read_segment(p)[0]["local_sequence"]


def test_restart_resumes_sequence_and_dedupes_across_runs(tmp_path):
    first = scripted([{"frames": frames(trade(1, 1), book(10), trade(2, 2))}])
    make_recorder(first, tmp_path).run()
    n1 = len(lines(tmp_path))
    # new process: the server re-sends the last trade as SNAPSHOT after reconnecting
    second = scripted([{"frames": frames(trade(2, 2, stream_type="SNAPSHOT"), trade(3, 3), start=T0 + 50)}],
                      start=T0 + 50)
    rec = make_recorder(second, tmp_path)
    rep = rec.run()
    assert rec.stores["KRW-BTC"].resumed and rep.duplicate_trades == 1
    all_lines = lines(tmp_path)
    assert [ln["local_sequence"] for ln in all_lines] == list(range(1, len(all_lines) + 1)) and len(all_lines) > n1
    state = read_json(tmp_path / "KRW-BTC" / "state.json")
    assert len(state["runs"]) == 2 and state["last_seq"] == len(all_lines)
    assert verify_upbit_recording(tmp_path / "KRW-BTC").ok


def test_fixture_resume_skips_already_recorded_frames(tmp_path):
    data = {"meta": {"synthetic": True}, "start": T0,
            "connections": [{"frames": frames(book(1), book(2, bid=99.0), book(3, bid=98.0))}]}
    make_recorder(ScriptedWsSource(data=data), tmp_path, max_market_events=2).run()
    rep = make_recorder(ScriptedWsSource(data=data), tmp_path).run()
    obs = [ln["exchange_timestamp"] for ln in lines(tmp_path) if ln["event_type"] == "orderbook"]
    assert obs == [1, 2, 3] and rep.orderbook_events == 1


def test_crash_leftovers_are_cleaned_and_disk_wins(tmp_path):
    make_recorder(scripted([{"frames": frames(book(1), book(2, bid=99.0))}]), tmp_path).run()
    ds = tmp_path / "KRW-BTC"
    (ds / "segments" / "junk.jsonl.tmp").write_text("partial", encoding="utf-8")
    state = read_json(ds / "state.json")
    state["last_seq"] = 1
    (ds / "state.json").write_text(json.dumps(state), encoding="utf-8")
    store = UpbitStore.open(tmp_path, "KRW-BTC", provenance="fixture", origin="fixture:test", orderbook_units=1,
                            source="t", now=T0)
    assert store.removed_tmp and store.cursor.last_seq == len(lines(tmp_path))
    assert any("using disk" in w for w in store.warnings)


# --- provenance ---------------------------------------------------------------------------

def test_real_and_fixture_data_never_share_a_dataset(tmp_path):
    UpbitStore.open(tmp_path, "KRW-BTC", provenance="real", origin=WS_PUBLIC_URL, orderbook_units=30,
                    source="t", now=T0)
    with pytest.raises(DatasetMismatch, match="refusing to mix fixture"):
        UpbitStore.open(tmp_path, "KRW-BTC", provenance="fixture", origin=WS_PUBLIC_URL, orderbook_units=30,
                        source="t", now=T0)
    with pytest.raises(DatasetMismatch, match="recorded from"):
        UpbitStore.open(tmp_path, "KRW-BTC", provenance="real", origin="wss://other", orderbook_units=30,
                        source="t", now=T0)
    with pytest.raises(DatasetMismatch, match="orderbook units"):
        UpbitStore.open(tmp_path, "KRW-BTC", provenance="real", origin=WS_PUBLIC_URL, orderbook_units=15,
                        source="t", now=T0)
    with pytest.raises(ValueError):
        UpbitStore.open(tmp_path / "x", "KRW-BTC", provenance="synthetic", origin="o", orderbook_units=30,
                        source="t", now=T0)
    # the recorder reports the mismatch as a storage failure and records nothing
    rep = make_recorder(scripted([{"frames": frames(book(1))}]), tmp_path, origin=WS_PUBLIC_URL,
                        orderbook_units=30).run()
    assert rep.status == RecorderStatus.FAILED and rep.last_error["category"] == "storage"
    assert segment_paths(tmp_path / "KRW-BTC") == []


def test_dataset_flags_real_vs_fixture(tmp_path):
    real = UpbitStore.open(tmp_path / "r", "KRW-BTC", provenance="real", origin=WS_PUBLIC_URL, orderbook_units=30,
                           source="t", now=T0)
    fix = UpbitStore.open(tmp_path / "f", "KRW-BTC", provenance="fixture", origin="fixture:x", orderbook_units=30,
                          source="t", now=T0)
    assert real.dataset["synthetic"] is False and fix.dataset["synthetic"] is True
