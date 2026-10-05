"""Recorder: storage format, duplicates, resume, rate limits, backoff, HTTP 451 (all offline)."""

import json
import random
from email.utils import formatdate

import pytest
import requests
from conftest import FIXTURES, FakeSession, load_captured_response, make_response

from moneylab.core.exceptions import NetworkError
from moneylab.core.http import HttpClient
from moneylab.providers.polymarket import ClobApiSource
from moneylab.providers.polymarket.recorder import (
    RecorderConfig,
    RecorderStatus,
    RestBookRecorder,
    TimelineFixtureSource,
    verify_recording,
)
from moneylab.providers.polymarket.recorder.base import classify, parse_retry_after
from moneylab.providers.polymarket.recorder.store import read_json, record_paths

CID = "0xMARKET-A"
YES, NO = "TOK-A-YES", "TOK-A-NO"
MARKET_INFO = json.loads((FIXTURES / "clob_market_info_sample.json").read_text(encoding="utf-8"))
MARKET_INFO = {**MARKET_INFO, "t": [{"t": YES, "o": "Yes"}, {"t": NO, "o": "No"}]}
REWARDS = json.loads((FIXTURES / "clob_rewards_market_sample.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network access attempted in an offline recorder test")

    monkeypatch.setattr(requests.Session, "request", boom)


class FakeClock:
    def __init__(self, now=1_791_104_400.0):
        self.now = now
        self.sleeps: list[float] = []

    def __call__(self):
        return self.now

    def sleep(self, s):
        self.sleeps.append(s)
        self.now += s


def raw_book(asset, bid=0.48, ask=0.52, ts=None, market=CID, last="0.5"):
    b = {"market": market, "asset_id": asset, "hash": f"h-{asset}-{ts}",
         "bids": [{"price": str(bid), "size": "100"}, {"price": str(round(bid - 0.01, 2)), "size": "200"}],
         "asks": [{"price": str(ask), "size": "120"}, {"price": str(round(ask + 0.01, 2)), "size": "220"}],
         "min_order_size": "5", "tick_size": "0.01", "neg_risk": False, "last_trade_price": last}
    if ts is not None:
        b["timestamp"] = str(int(ts * 1000))
    return b


def pair(bid=0.48, ts=None):
    return [raw_book(YES, bid, round(bid + 0.04, 2), ts), raw_book(NO, round(1 - bid - 0.04, 2), round(1 - bid, 2), ts)]


class ScriptedClob:
    """ClobSource whose fetch_books answers come from a script (payload or exception per call)."""

    def __init__(self, books_script, clock, market_info=None, rewards=REWARDS, infos=None):
        self.books_script = list(books_script)
        self.clock = clock
        self.market_info = {CID: MARKET_INFO} if infos is None else infos
        self.rewards = rewards
        self.calls: list[tuple[str, float]] = []

    def _next(self, script):
        item = script.pop(0) if script else StopIteration
        if item is StopIteration:
            from moneylab.providers.polymarket.recorder import SourceExhausted
            raise SourceExhausted("script done")
        if isinstance(item, BaseException):
            raise item
        return item(self.clock()) if callable(item) else item

    def fetch_books(self, token_ids):
        self.calls.append(("books", self.clock()))
        return self._next(self.books_script)

    def fetch_market_info(self, cid):
        self.calls.append(("info", self.clock()))
        if isinstance(self.market_info, Exception):
            raise self.market_info
        return self.market_info[cid]

    def fetch_rewards(self, cid):
        self.calls.append(("rewards", self.clock()))
        if isinstance(self.rewards, Exception):
            raise self.rewards
        return self.rewards

    def close(self):
        pass


def recorder(tmp_path, source, clock, cids=(CID,), **cfg):
    cfg.setdefault("interval", 60.0)
    cfg.setdefault("min_request_spacing", 0.0)
    return RestBookRecorder(source, tmp_path, RecorderConfig(tuple(cids), **cfg), synthetic=False,
                            clock=clock, sleep=clock.sleep, rng=random.Random(7))


def records(path):
    return [read_json(p) for p in record_paths(path)]


def api_error(status, headers=None, body="{}"):
    """An ApiError exactly as HttpClient produces it."""
    session = FakeSession(lambda m, u, p: make_response(status, body, headers or {}, url=u))
    try:
        HttpClient("https://clob.example", session=session).get_json("/books")
    except Exception as exc:  # noqa: BLE001
        return exc
    raise AssertionError("expected an error")


# --- storage format -------------------------------------------------------------------------

def test_record_contains_raw_books_summary_and_metadata(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([lambda t: pair(0.48, t), lambda t: pair(0.47, t)], clock)
    rep = recorder(tmp_path, src, clock, max_polls=2).run()
    assert rep.status == RecorderStatus.COMPLETED and rep.books_written == 2
    ds = rep.datasets[CID]
    assert ds == tmp_path / "0xMARKET-A"
    first = records(ds)[0]
    assert first["kind"] == "book" and first["seq"] == 1 and first["condition_id"] == CID
    assert first["recorded_at"] == 1_791_104_400.0 and first["recorded_at_iso"].endswith("Z")
    assert first["books"][0]["asset_id"] == NO and first["books"][0]["bids"]  # raw, unmodified, sorted by token
    tok = {t["token_id"]: t for t in first["tokens"]}
    assert tok[YES] == {
        "token_id": YES, "outcome": "Yes", "best_bid": 0.48, "best_ask": 0.52, "spread": 0.04,
        "bid_depth_levels": 2, "ask_depth_levels": 2, "last_trade_price": 0.5, "tick_size": 0.01,
        "min_order_size": 5.0, "neg_risk": False, "server_timestamp": 1_791_104_400.0,
    }
    meta = read_json(next((ds / "metadata").glob("*.json")))
    assert meta["hash"] == first["metadata_hash"]
    s = meta["summary"]
    assert s["fee_schedule"]["rate"] == 0.04 and s["tick_size"] == 0.01 and s["min_order_size"] == 5
    assert s["reward_config"]["max_spread_cents"] == 3 and s["reward_config"]["daily_rate_total"] == 20
    assert meta["market_info"] == MARKET_INFO and meta["rewards"] == REWARDS  # raw payloads kept
    state = read_json(ds / "state.json")
    assert state["status"] == "completed" and state["last_seq"] == 2 and state["counters"]["book"] == 2
    assert verify_recording(ds).ok


def test_poll_interval_is_kept(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([lambda t: pair(0.48, t)] * 3, clock)
    recorder(tmp_path, src, clock, max_polls=3).run()
    assert [t for k, t in src.calls if k == "books"] == [1_791_104_400.0, 1_791_104_460.0, 1_791_104_520.0]


def test_client_side_request_spacing(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([lambda t: pair(0.48, t)], clock)
    recorder(tmp_path, src, clock, max_polls=1, min_request_spacing=0.5).run()
    times = [t for _, t in src.calls]  # info, rewards, books
    assert all(b - a >= 0.5 for a, b in zip(times, times[1:], strict=False))


def test_metadata_only_rewritten_when_changed(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([lambda t: pair(0.48, t)] * 4, clock)
    recorder(tmp_path, src, clock, max_polls=4, metadata_refresh=60.0).run()
    assert len(list((tmp_path / "0xMARKET-A" / "metadata").glob("*.json"))) == 1
    assert sum(1 for k, _ in src.calls if k == "info") == 4
    src2 = ScriptedClob([lambda t: pair(0.48, t)], clock,
                        infos={CID: {**MARKET_INFO, "fd": {"r": 0.05, "e": 1, "to": True}}})
    recorder(tmp_path, src2, clock, max_polls=1).run()
    assert len(list((tmp_path / "0xMARKET-A" / "metadata").glob("*.json"))) == 2


def test_rewards_failure_is_recorded_but_not_fatal(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([lambda t: pair(0.48, t)], clock, rewards=api_error(404))
    rep = recorder(tmp_path, src, clock, max_polls=1).run()
    assert rep.status == RecorderStatus.COMPLETED and rep.books_written == 1
    meta = read_json(next((tmp_path / "0xMARKET-A" / "metadata").glob("*.json")))
    assert meta["rewards"] is None and "404" in meta["rewards_error"]
    assert meta["summary"]["reward_config"] is None


# --- duplicates -----------------------------------------------------------------------------

def test_duplicate_and_unchanged_snapshots(tmp_path):
    clock = FakeClock()
    same_ts = pair(0.48, 1_791_104_400.0)
    src = ScriptedClob([same_ts, same_ts, lambda t: pair(0.48, t), lambda t: pair(0.47, t)], clock)
    rep = recorder(tmp_path, src, clock, max_polls=4).run()
    assert (rep.books_written, rep.duplicates_skipped, rep.unchanged_written) == (2, 1, 1)
    recs = records(tmp_path / "0xMARKET-A")
    assert [r["kind"] for r in recs] == ["book", "unchanged", "book"]
    assert recs[1]["ref_seq"] == 1 and recs[1]["content_hash"] == recs[0]["content_hash"]
    assert recs[1]["server_timestamps"][YES] == str(int(1_791_104_520.0 * 1000))
    st = read_json(tmp_path / "0xMARKET-A" / "state.json")
    assert st["counters"]["duplicates_skipped"] == 1
    assert verify_recording(tmp_path / "0xMARKET-A").ok


def test_books_without_server_timestamp_are_never_dropped(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([pair(0.48), pair(0.48)], clock)
    rep = recorder(tmp_path, src, clock, max_polls=2).run()
    assert (rep.books_written, rep.unchanged_written, rep.duplicates_skipped) == (1, 1, 0)


# --- resume ---------------------------------------------------------------------------------

def test_restart_resumes_sequence_and_dedup_state(tmp_path):
    clock = FakeClock()
    recorder(tmp_path, ScriptedClob([lambda t: pair(0.48, t)] * 2, clock), clock, max_polls=2).run()
    ds = tmp_path / "0xMARKET-A"
    # simulate a crash: leftover temp file, lost checkpoint
    (ds / "records" / "x.tmp").write_text("{partial", encoding="utf-8")
    (ds / "state.json").unlink()
    same = pair(0.48, clock.now - 60)  # identical to the last stored observation
    rep = recorder(tmp_path, ScriptedClob([same, lambda t: pair(0.40, t)], clock), clock, max_polls=2).run()
    assert rep.duplicates_skipped == 1 and rep.books_written == 1
    assert [r["seq"] for r in records(ds)] == [1, 2, 3]
    assert not list(ds.rglob("*.tmp"))
    state = read_json(ds / "state.json")
    assert state["last_seq"] == 3 and len(state["runs"]) == 1  # history restarted with the lost checkpoint
    assert verify_recording(ds).ok


def test_resume_refuses_to_mix_synthetic_and_real(tmp_path):
    clock = FakeClock()
    recorder(tmp_path, ScriptedClob([lambda t: pair(0.48, t)], clock), clock, max_polls=1).run()
    rec = RestBookRecorder(ScriptedClob([], clock), tmp_path, RecorderConfig((CID,)), synthetic=True,
                           clock=clock, sleep=clock.sleep)
    rep = rec.run()
    assert rep.status == RecorderStatus.FAILED and rep.last_error["category"] == "storage"
    assert "refusing to mix" in rep.last_error["message"]


def test_fixture_source_recording_resumes_across_runs(tmp_path):
    src = TimelineFixtureSource(FIXTURES / "clob_timeline_mm.json")
    cfg = RecorderConfig((src.condition_id,), max_polls=50, rebate_rate=src.rebate_rate)
    for _ in range(3):
        rep = RestBookRecorder(src, tmp_path, cfg, synthetic=True, clock=src.clock, sleep=src.no_sleep).run()
    assert rep.status == RecorderStatus.SOURCE_EXHAUSTED
    ds = rep.datasets[src.condition_id]
    assert [r["seq"] for r in records(ds)] == list(range(1, 121))
    assert len(read_json(ds / "state.json")["runs"]) == 3
    assert verify_recording(ds).ok


# --- failures -------------------------------------------------------------------------------

def test_http_451_stops_immediately_and_records_state(tmp_path):
    resp = load_captured_response("http_451_cloudflare_json.json")
    session = FakeSession(lambda m, u, p: resp)
    http = HttpClient("https://clob.polymarket.com", session=session)
    clock = FakeClock()
    rep = recorder(tmp_path, ClobApiSource(http), clock, max_polls=100).run()
    assert rep.status == RecorderStatus.BLOCKED_HTTP_451 and not rep.ok
    assert len(session.calls) == 1  # no retry of a policy decision
    assert clock.sleeps == []
    ds = tmp_path / "0xMARKET-A"
    state = read_json(ds / "state.json")
    assert state["status"] == "blocked_http_451"
    blocked = state["blocked"]
    assert blocked["status_code"] == 451 and "legal_block" in blocked["diagnostics"]["body_excerpt"]
    assert "does not infer" in blocked["diagnostics"]["note"]
    recs = records(ds)
    assert [r["kind"] for r in recs] == ["error"] and recs[0]["error"]["category"] == "http_451"
    rep2 = verify_recording(ds)
    assert rep2.ok and rep2.status == "blocked_http_451"


def test_http_451_mid_recording_keeps_collected_data(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([lambda t: pair(0.48, t), api_error(451), lambda t: pair(0.47, t)], clock)
    rep = recorder(tmp_path, src, clock).run()
    assert rep.status == RecorderStatus.BLOCKED_HTTP_451 and rep.books_written == 1
    assert len(src.books_script) == 1  # stopped before the next poll
    assert [r["kind"] for r in records(tmp_path / "0xMARKET-A")] == ["book", "error"]


def test_http_403_is_access_denied_without_retry(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([api_error(403), lambda t: pair(0.48, t)], clock)
    rep = recorder(tmp_path, src, clock).run()
    assert rep.status == RecorderStatus.ACCESS_DENIED and rep.books_written == 0


def test_rate_limit_respects_retry_after_then_recovers(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([api_error(429, {"Retry-After": "600"}), lambda t: pair(0.48, t)], clock)
    rep = recorder(tmp_path, src, clock, max_polls=2, backoff_max=300).run()
    assert rep.status == RecorderStatus.COMPLETED and rep.rate_limited == 1 and rep.books_written == 1
    assert max(clock.sleeps) >= 600  # Retry-After wins even above backoff_max
    recs = records(tmp_path / "0xMARKET-A")
    assert recs[0]["error"]["category"] == "rate_limited" and recs[0]["error"]["retry_after"] == 600
    assert read_json(tmp_path / "0xMARKET-A" / "state.json")["counters"]["rate_limited"] == 1


def test_parse_retry_after_forms():
    now = 1_791_104_400.0
    assert parse_retry_after("12", now) == 12
    assert parse_retry_after(formatdate(now + 60, usegmt=True), now) == pytest.approx(60)
    assert parse_retry_after("garbage", now) is None and parse_retry_after(None, now) is None


def test_network_errors_back_off_exponentially_then_recover(tmp_path):
    clock = FakeClock()
    err = NetworkError("Connection failed")
    src = ScriptedClob([err, err, err, err, lambda t: pair(0.48, t)], clock)
    rep = recorder(tmp_path, src, clock, max_polls=5, interval=1.0, backoff_base=2.0, backoff_max=10.0).run()
    assert rep.status == RecorderStatus.COMPLETED and rep.errors == 4 and rep.books_written == 1
    backoffs = clock.sleeps[:4]
    assert backoffs[0] < backoffs[2] and all(1.0 <= b <= 10.0 for b in backoffs)
    assert read_json(tmp_path / "0xMARKET-A" / "state.json")["consecutive_failures"] == 0


def test_too_many_consecutive_failures_fail(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([api_error(503)] * 10, clock)
    rep = recorder(tmp_path, src, clock, max_consecutive_failures=3).run()
    assert rep.status == RecorderStatus.FAILED and rep.errors == 3
    assert read_json(tmp_path / "0xMARKET-A" / "state.json")["status"] == "failed"


def test_bad_payload_is_recorded_and_recording_continues(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([{"unexpected": "shape"}, [{"no": "asset"}], lambda t: pair(0.48, t)], clock)
    rep = recorder(tmp_path, src, clock, max_polls=3).run()
    assert rep.status == RecorderStatus.COMPLETED and rep.books_written == 1
    errs = [r for r in records(tmp_path / "0xMARKET-A") if r["kind"] == "error"]
    assert len(errs) == 2 and all(e["error"]["category"] == "bad_payload" for e in errs)
    assert "unexpected" in errs[0]["error"]["diagnostics"]["body_excerpt"]


def test_market_info_unavailable_without_stored_metadata_is_an_error(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([lambda t: pair(0.48, t)], clock, infos=api_error(404))
    src.market_info = api_error(404)
    rep = recorder(tmp_path, src, clock, max_consecutive_failures=2).run()
    assert rep.status == RecorderStatus.FAILED and rep.books_written == 0
    assert not [k for k, _ in src.calls if k == "books"]


def test_missing_token_is_recorded(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([lambda t: [raw_book(YES, ts=t)]], clock)
    recorder(tmp_path, src, clock, max_polls=1).run()
    rec = records(tmp_path / "0xMARKET-A")[0]
    assert rec["missing_tokens"] == [NO]
    assert any("no book for" in w for w in verify_recording(tmp_path / "0xMARKET-A").warnings)


def test_two_markets_share_one_request(tmp_path):
    cid_b, yb, nb = "0xMARKET-B", "TOK-B-YES", "TOK-B-NO"
    infos = {CID: MARKET_INFO, cid_b: {**MARKET_INFO, "t": [{"t": yb, "o": "Yes"}, {"t": nb, "o": "No"}]}}
    clock = FakeClock()
    payload = pair(0.48, clock.now) + [raw_book(yb, ts=clock.now, market=cid_b), raw_book(nb, ts=clock.now, market=cid_b),
                                       raw_book("STRANGER", ts=clock.now)]
    src = ScriptedClob([payload], clock, infos=infos)
    rep = recorder(tmp_path, src, clock, cids=(CID, cid_b), max_polls=1).run()
    assert rep.books_written == 2 and sum(1 for k, _ in src.calls if k == "books") == 1
    b = records(tmp_path / "0xMARKET-B")[0]
    assert sorted(x["asset_id"] for x in b["books"]) == [nb, yb]
    assert verify_recording(tmp_path / "0xMARKET-A").ok and verify_recording(tmp_path / "0xMARKET-B").ok


def test_stop_and_duration(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([lambda t: pair(0.48, t)] * 10, clock)
    rep = recorder(tmp_path, src, clock, duration=150).run()
    assert rep.status == RecorderStatus.COMPLETED and rep.polls == 3
    rec = recorder(tmp_path, ScriptedClob([lambda t: pair(0.4, t)] * 10, clock), clock)
    rec.stop()
    assert rec.run().status == RecorderStatus.STOPPED


def test_keyboard_interrupt_saves_state(tmp_path):
    clock = FakeClock()
    src = ScriptedClob([lambda t: pair(0.48, t), KeyboardInterrupt()], clock)
    rep = recorder(tmp_path, src, clock).run()
    assert rep.status == RecorderStatus.STOPPED and rep.books_written == 1
    assert read_json(tmp_path / "0xMARKET-A" / "state.json")["status"] == "stopped"


def test_classify_does_not_leak_secrets():
    f = classify(ValueError("api_key=abcd1234 broke"), 0.0)
    assert f.category == "bad_payload" and "abcd1234" not in f.message


def test_config_validation():
    with pytest.raises(ValueError):
        RecorderConfig(())
    with pytest.raises(ValueError):
        RecorderConfig(("x",), interval=0)


def test_live_source_uses_post_books_only(tmp_path):
    """The live source sends read-only requests only (GET metadata, POST /books query)."""
    clock = FakeClock()
    calls = []

    def handler(method, url, params):
        calls.append((method, url.split("clob.example")[1]))
        if "/books" in url:
            return make_response(200, json.dumps(pair(0.48, clock.now)), url=url)
        if "/rewards/" in url:
            return make_response(200, json.dumps(REWARDS), url=url)
        return make_response(200, json.dumps(MARKET_INFO), url=url)

    http = HttpClient("https://clob.example", session=FakeSession(handler))
    rep = recorder(tmp_path, ClobApiSource(http), clock, max_polls=1).run()
    assert rep.books_written == 1
    assert calls == [("GET", f"/clob-markets/{CID}"), ("GET", f"/rewards/markets/{CID}"), ("POST", "/books")]
