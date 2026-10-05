"""Recorder -> dataset -> ReplayBookStream -> strategies -> PaperEngine, plus integrity checks (offline)."""

import json
from pathlib import Path

import pytest
import requests
from conftest import FIXTURES, make_snapshot

from moneylab.cli import main
from moneylab.core.exceptions import ProviderError
from moneylab.paper.book_stream import ReplayBookStream, TimelineBookStream
from moneylab.paper.runner import SimulationConfig, SimulationRunner
from moneylab.providers.base import RecordedBookSource, RecordedEvent
from moneylab.providers.polymarket import load_timeline
from moneylab.providers.polymarket.recorder import (
    RecorderConfig,
    RestBookRecorder,
    TimelineFixtureSource,
    open_recording,
    verify_recording,
)
from moneylab.providers.polymarket.recorder.store import read_json, record_paths
from moneylab.risk.kill_switch import KillSwitchConfig
from moneylab.storage.atomic import atomic_write_json
from moneylab.strategy.market_making import SymmetricMarketMaker
from moneylab.strategy.mispricing import ComplementArbitrage


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network access attempted during offline replay")

    monkeypatch.setattr(requests.Session, "request", boom)


def record_fixture(tmp_path, name, max_polls=None):
    src = TimelineFixtureSource(FIXTURES / name)
    cfg = RecorderConfig((src.condition_id,), max_polls=max_polls, rebate_rate=src.rebate_rate,
                         rebate_rate_source="fixture meta")
    rep = RestBookRecorder(src, tmp_path, cfg, synthetic=src.synthetic, clock=src.clock, sleep=src.no_sleep).run()
    return rep.datasets[src.condition_id]


@pytest.fixture(scope="module")
def _mm_recorded(tmp_path_factory):
    return record_fixture(tmp_path_factory.mktemp("mm"), "clob_timeline_mm.json")


@pytest.fixture
def mm_dataset(_mm_recorded, tmp_path):
    """A fresh copy per test (tests tamper with it); recorded once per module."""
    import shutil

    return Path(shutil.copytree(_mm_recorded, tmp_path / _mm_recorded.name))


def simulate(params, stream, strategy, synthetic=True, **cfg):
    return SimulationRunner(params, strategy, SimulationConfig(**cfg), synthetic=synthetic).run(stream)


# --- end-to-end equivalence -----------------------------------------------------------------

def test_replayed_recording_reproduces_the_original_timeline_exactly(mm_dataset):
    tl = load_timeline(FIXTURES / "clob_timeline_mm.json")
    reader = open_recording(mm_dataset)
    assert reader.params == tl.params and reader.synthetic is True
    a = simulate(tl.params, TimelineBookStream(tl), SymmetricMarketMaker())
    b = simulate(reader.params, ReplayBookStream(reader), SymmetricMarketMaker())
    assert a.breakdown == b.breakdown and a.equity_curve == b.equity_curve
    assert [(f.timestamp, f.token_id, f.price, f.size) for f in a.fills] == \
           [(f.timestamp, f.token_id, f.price, f.size) for f in b.fills]
    # the v0.2 golden values survive the round trip
    assert b.breakdown.net_trading_pnl_after_cost == pytest.approx(-15.5)
    assert b.verdict.status == "REJECT"


def test_arbitrage_replay_matches_timeline(tmp_path):
    ds = record_fixture(tmp_path, "clob_timeline_mispricing.json")
    tl = load_timeline(FIXTURES / "clob_timeline_mispricing.json")
    reader = open_recording(ds)
    a = simulate(tl.params, TimelineBookStream(tl), ComplementArbitrage())
    b = simulate(reader.params, ReplayBookStream(reader), ComplementArbitrage())
    assert a.taker_fills > 0 and a.breakdown == b.breakdown


def test_replay_events_are_snapshots_with_both_tokens(mm_dataset):
    reader = open_recording(mm_dataset)
    events = list(ReplayBookStream(reader))
    assert len(events) == 120 and all(e.snapshot is not None for e in events)
    snap = events[0].snapshot
    assert set(snap.books) == {reader.params.yes_token, reader.params.no_token}
    assert snap.books[reader.params.yes_token].best_bid == 0.49
    assert events[1].timestamp - events[0].timestamp == 60


# --- ReplayBookStream mechanics -------------------------------------------------------------

class ListSource(RecordedBookSource):
    def __init__(self, events):
        self._events = events

    def iter_events(self):
        yield from self._events


def snap(ts):
    return make_snapshot(ts, [(0.48, 100)], [(0.52, 100)])


def test_replay_window_out_of_order_and_errors():
    src = ListSource([RecordedEvent(10, snap(10)), RecordedEvent(20, error="recorded network: down"),
                      RecordedEvent(15, snap(15)), RecordedEvent(30, snap(30)), RecordedEvent(40, snap(40))])
    stream = ReplayBookStream(src, start=10, end=30)
    evs = list(stream)
    assert [(e.timestamp, e.error is not None) for e in evs] == [(10, False), (20, True), (30, False)]
    assert (stream.stats.skipped_out_of_order, stream.stats.skipped_outside_window, stream.stats.errors) == (1, 1, 1)
    assert [e.timestamp for e in ReplayBookStream(src, include_errors=False)] == [10, 30, 40]


def test_recorded_outage_trips_kill_switch_in_replay(tmp_path):
    from conftest import make_params

    events = [RecordedEvent(100, snap(100))] + [RecordedEvent(100 + 60 * i, error="recorded http: 503") for i in (1, 2, 3)]
    r = simulate(make_params(), ReplayBookStream(ListSource(events)), SymmetricMarketMaker(),
                 kill_switch=KillSwitchConfig(max_consecutive_errors=3))
    assert any("provider_errors" in x for x in r.kill_switch_reasons)


# --- recording reader -----------------------------------------------------------------------

def test_unchanged_records_re_emit_the_referenced_book(tmp_path):
    src = TimelineFixtureSource(FIXTURES / "clob_timeline_mm.json")
    first = src.snapshots[0]
    repeated = json.loads(json.dumps(first))
    repeated["ts"] = first["ts"] + 60
    for b in repeated["books"]:
        b["timestamp"] = str(int(repeated["ts"] * 1000))
    src.snapshots = [first, repeated]
    cfg = RecorderConfig((src.condition_id,), rebate_rate=0.25)
    rep = RestBookRecorder(src, tmp_path, cfg, synthetic=True, clock=src.clock, sleep=src.no_sleep).run()
    assert rep.unchanged_written == 1
    evs = list(open_recording(rep.datasets[src.condition_id]).iter_events())
    a, b = evs[0].snapshot, evs[1].snapshot
    tok = next(iter(a.books))
    assert a.books[tok].bids == b.books[tok].bids and a.books[tok].asks == b.books[tok].asks
    assert b.books[tok].timestamp == first["ts"] + 60 and b.timestamp == first["ts"] + 60


def test_reader_rejects_tampered_record(mm_dataset):
    p = record_paths(mm_dataset)[5]
    rec = read_json(p)
    rec["books"][0]["bids"][0]["price"] = "0.10"
    atomic_write_json(p, rec, indent=None)
    reader = open_recording(mm_dataset)
    with pytest.raises(ProviderError, match="Checksum mismatch"):
        list(reader.iter_events())
    assert len(list(open_recording(mm_dataset, verify_checksums=False).iter_events())) == 120


def test_reader_requires_metadata(tmp_path):
    with pytest.raises(ProviderError):
        open_recording(tmp_path / "nothing")
    (tmp_path / "d").mkdir()
    atomic_write_json(tmp_path / "d" / "dataset.json", {"condition_id": "x", "synthetic": False})
    with pytest.raises(ProviderError, match="no market metadata"):
        open_recording(tmp_path / "d")


# --- integrity ------------------------------------------------------------------------------

def test_clean_recording_passes(mm_dataset):
    rep = verify_recording(mm_dataset)
    assert rep.ok and rep.counts["book"] == 120 and rep.counts["records"] == 120
    assert rep.status == "source_exhausted" and rep.synthetic is True
    assert rep.last_ts - rep.first_ts == 119 * 60


def test_integrity_detects_tampering(mm_dataset):
    p = record_paths(mm_dataset)[3]
    rec = read_json(p)
    rec["books"][0]["asks"][0]["size"] = "1"
    atomic_write_json(p, rec, indent=None)
    errors = verify_recording(mm_dataset).errors
    assert any("checksum mismatch" in e for e in errors)
    assert any("content_hash does not match" in e for e in errors)


def test_integrity_detects_missing_records_and_bad_checkpoint(mm_dataset):
    record_paths(mm_dataset)[10].unlink()
    state = read_json(mm_dataset / "state.json")
    state["last_seq"] = 500
    atomic_write_json(mm_dataset / "state.json", state)
    errors = verify_recording(mm_dataset).errors
    assert any("seq gap: 10 -> 12" in e for e in errors)
    assert any("last_seq=500" in e for e in errors)


def test_integrity_detects_time_going_backwards_and_bad_metadata(mm_dataset):
    p = record_paths(mm_dataset)[20]
    rec = read_json(p)
    rec["recorded_at"] = 1.0
    from moneylab.providers.polymarket.recorder.store import with_checksum
    atomic_write_json(p, with_checksum(rec), indent=None)
    meta = next((mm_dataset / "metadata").glob("*.json"))
    doc = read_json(meta)
    doc["market_info"]["mts"] = 0.001
    atomic_write_json(meta, doc)
    errors = verify_recording(mm_dataset).errors
    assert any("time goes backwards" in e for e in errors)
    assert any("hash mismatch" in e for e in errors)


def test_integrity_warns_on_gaps_and_tmp_files(tmp_path):
    src = TimelineFixtureSource(FIXTURES / "clob_timeline_mm.json")
    del src.snapshots[5:20]  # a 16-minute hole
    cfg = RecorderConfig((src.condition_id,), rebate_rate=0.25)
    rep = RestBookRecorder(src, tmp_path, cfg, synthetic=True, clock=src.clock, sleep=src.no_sleep).run()
    ds = rep.datasets[src.condition_id]
    (ds / "records" / "junk.json.x.tmp").write_text("{", encoding="utf-8")
    report = verify_recording(ds)
    assert report.ok
    assert any("gap of 960s" in w for w in report.warnings)
    assert any("temp file" in w for w in report.warnings)


# --- CLI ------------------------------------------------------------------------------------

def test_cli_record_verify_simulate_pipeline(tmp_path, capsys):
    assert main(["record", "--source", "fixture", "--out", str(tmp_path), "--max-polls", "30"]) == 0
    out = capsys.readouterr().out
    assert "books_written" in out and "completed" in out
    ds = tmp_path / "0xSYNTHETIC-CONDITION-0001"
    assert main(["record-verify", str(ds)]) == 0
    assert "Integrity OK" in capsys.readouterr().out
    assert main(["simulate", "--strategy", "mm", "--recording", str(ds)]) == 0
    out = capsys.readouterr().out
    assert "net_trading_pnl_after_cost" in out and "SYNTHETIC" in out and "replay: 30 snapshots" in out
    assert main(["record", "--source", "fixture", "--out", str(tmp_path)]) == 0  # resume to the end
    assert len(record_paths(ds)) == 120
    assert read_json(ds / "dataset.json")["origin"] == "fixture:clob_timeline_mm.json"
    # another fixture with the same (synthetic) condition id must not be appended to this dataset
    other = str(FIXTURES / "clob_timeline_mispricing.json")
    assert main(["record", "--source", "fixture", "--fixture", other, "--out", str(tmp_path)]) == 1
    assert "refusing to mix" in capsys.readouterr().out
    assert len(record_paths(ds)) == 120


def test_cli_simulate_recording_window_and_errors(tmp_path, capsys):
    assert main(["record", "--source", "fixture", "--out", str(tmp_path)]) == 0
    ds = tmp_path / "0xSYNTHETIC-CONDITION-0001"
    capsys.readouterr()
    assert main(["simulate", "--recording", str(ds), "--start", "1791104400", "--end", "1791105000"]) == 0
    assert "replay: 11 snapshots" in capsys.readouterr().out
    assert main(["simulate", "--recording", str(tmp_path / "missing")]) == 3
    assert main(["simulate", "--recording", str(ds), "--timeline", "x.json"]) == 1
    p = record_paths(ds)[2]
    rec = read_json(p)
    rec["seq"] = 999
    atomic_write_json(p, rec, indent=None)
    assert main(["simulate", "--recording", str(ds)]) == 3  # checksum failure surfaces mid-replay
    assert main(["record-verify", str(ds), "--json"]) == 1


def test_cli_record_live_requires_condition_id(monkeypatch):
    monkeypatch.delenv("MONEYLAB_RECORDER_CONDITION_IDS", raising=False)
    monkeypatch.delenv("MONEYLAB_RECORDER_SOURCE", raising=False)
    assert main(["record"]) == 1


def test_cli_record_source_from_environment(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MONEYLAB_RECORDER_SOURCE", "fixture")
    monkeypatch.setenv("MONEYLAB_RECORDER_INTERVAL", "60")
    assert main(["record", "--out", str(tmp_path), "--max-polls", "2"]) == 0
    assert "from fixture" in capsys.readouterr().out


def test_cli_record_live_451_exit_code(tmp_path, monkeypatch, capsys):
    """Live source + captured HTTP 451 response: exit 3, status recorded, single request."""
    from conftest import load_captured_response

    calls = []

    def fake_request(self, method, url, **kw):
        calls.append((method, url))
        return load_captured_response("http_451_cloudflare_json.json")

    monkeypatch.setattr(requests.Session, "request", fake_request)
    assert main(["record", "--condition-id", "0xabc", "--out", str(tmp_path), "--max-polls", "5"]) == 3
    out = capsys.readouterr().out
    assert "blocked_http_451" in out and "does not infer" in " ".join(out.split())
    assert len(calls) == 1
    state = read_json(tmp_path / "0xabc" / "state.json")
    assert state["status"] == "blocked_http_451" and "legal_block" in state["blocked"]["diagnostics"]["body_excerpt"]
