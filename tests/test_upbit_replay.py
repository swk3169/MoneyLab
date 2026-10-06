"""Upbit recording -> UpbitRecordingReader -> ReplayBookStream, integrity checks, CLI. No network."""

import json
import random
import shutil
from pathlib import Path

import pytest

from moneylab.cli import main
from moneylab.core.exceptions import ProviderError
from moneylab.domain.market_params import MarketParams, TokenInfo
from moneylab.domain.trades import TradeTick
from moneylab.paper.book_stream import ReplayBookStream, StreamEvent
from moneylab.providers.upbit.endpoints import WS_PUBLIC_URL
from moneylab.providers.upbit.recorder import (
    ScriptedWsSource,
    UpbitRecorder,
    UpbitRecorderConfig,
    UpbitRecordingReader,
    is_upbit_recording,
    replay_check,
    verify_upbit_recording,
)
from moneylab.providers.upbit.recorder.store import read_segment, segment_paths
from moneylab.recording.core import with_checksum
from upbit_helpers import FIXTURE, book, frames, make_recorder, scripted, trade


@pytest.fixture
def fixture_dataset(tmp_path) -> Path:
    src = ScriptedWsSource(FIXTURE)
    UpbitRecorder(src, WS_PUBLIC_URL, tmp_path, UpbitRecorderConfig(ping_text_interval=3.0), provenance="fixture",
                  origin=f"fixture:{FIXTURE.name}", clock=src.clock, sleep=src.sleep, rng=random.Random(1)).run()
    return tmp_path / "KRW-BTC"


def rewrite_line(dataset: Path, seq: int, mutate, rechecksum: bool = True) -> None:
    for p in segment_paths(dataset):
        lines = read_segment(p)
        for i, ln in enumerate(lines):
            if ln["local_sequence"] == seq:
                mutate(ln)
                lines[i] = with_checksum(ln) if rechecksum else ln
                p.write_text("".join(json.dumps(x, separators=(",", ":")) + "\n" for x in lines), encoding="utf-8")
                return
    raise AssertionError(seq)


def test_replay_matches_original(fixture_dataset):
    rep = replay_check(fixture_dataset)
    assert rep.ok, rep.mismatches
    assert rep.provenance == "fixture" and rep.synthetic is True
    assert rep.counts["compared_orderbooks"] == rep.counts["original_orderbooks"] == 32
    assert rep.counts["compared_trades"] == rep.counts["original_trades"] == 12
    assert rep.replay_stats["skipped_out_of_order"] == 0 and rep.reader_stats["duplicates_skipped"] == 2
    assert rep.units_histogram == {30: 32} and rep.latency_ms["orderbook"]["median"] == pytest.approx(30.0)
    assert rep.latency_ms["orderbook"]["n"] == 31 and rep.latency_ms["trade"]["n"] == 11  # REALTIME only
    assert rep.first_exchange_ms < rep.last_exchange_ms and rep.size_bytes > 0


def test_reader_events_follow_exchange_time_with_deterministic_ties(tmp_path):
    # trade (exchange 1000) arrives after book (exchange 1050); book and trade share exchange 2000
    src = scripted([{"frames": frames(book(1050), trade(1, 995), book(2000, bid=99.0), trade(2, 1995))}])
    make_recorder(src, tmp_path).run()
    reader = UpbitRecordingReader(tmp_path / "KRW-BTC")
    evs = list(ReplayBookStream(reader))
    kinds = [("book" if e.snapshot else "trade" if e.trades else "error") for e in evs]
    assert kinds[:4] == ["trade", "book", "book", "trade"]  # trade msg ts = 1000 < 1050; tie at 2000 by receive
    keys = [(e.timestamp, e.received_timestamp, e.local_sequence) for e in evs]
    assert keys == sorted(keys)
    assert evs[0].trades[0].trade_id == 1 and evs[0].trades[0].side == "buy"
    assert list(ReplayBookStream(UpbitRecordingReader(tmp_path / "KRW-BTC"))) == evs  # deterministic
    by_arrival = list(UpbitRecordingReader(tmp_path / "KRW-BTC", order="received").iter_events())
    seqs = [e.local_sequence for e in by_arrival]
    assert seqs == sorted(seqs) and by_arrival[0].timestamp == by_arrival[0].received_timestamp


def test_reader_reports_events_later_than_reorder_window(tmp_path):
    src = scripted([{"frames": frames(book(10_000), book(20_000, bid=99.0), trade(1, 5_000))}])
    make_recorder(src, tmp_path).run()
    reader = UpbitRecordingReader(tmp_path / "KRW-BTC", reorder_window_ms=1000)
    stream = ReplayBookStream(reader)
    evs = list(stream)
    assert reader.stats.late_events == 1 and stream.stats.skipped_out_of_order == 1
    assert len([e for e in evs if e.snapshot]) == 2
    wide = UpbitRecordingReader(tmp_path / "KRW-BTC", reorder_window_ms=60_000)
    assert [bool(e.trades) for e in wide.iter_events() if e.error is None][0] is True


def test_recorded_gaps_become_error_events(fixture_dataset):
    reader = UpbitRecordingReader(fixture_dataset)
    stream = ReplayBookStream(reader)
    errors = [e for e in stream if e.error]
    assert any("disconnected" in e.error for e in errors) and any("malformed" in e.error for e in errors)
    assert stream.stats.errors == len(errors)
    no_err = ReplayBookStream(UpbitRecordingReader(fixture_dataset), include_errors=False)
    assert not any(e.error for e in no_err)


def test_reader_exposes_provenance_and_params(fixture_dataset):
    reader = UpbitRecordingReader(fixture_dataset)
    assert reader.synthetic is True and reader.provenance == "fixture" and "SYNTHETIC" in reader.description
    assert reader.params.condition_id == "KRW-BTC" and reader.params.yes_token is None
    assert is_upbit_recording(fixture_dataset) and not is_upbit_recording(fixture_dataset / "nope")


def test_tampering_is_detected(fixture_dataset):
    rewrite_line(fixture_dataset, 3, lambda ln: ln.update(raw=ln["raw"].replace("99999000", "99998000")),
                 rechecksum=False)
    with pytest.raises(ProviderError, match="Checksum"):
        list(UpbitRecordingReader(fixture_dataset).iter_events())
    assert any("checksum" in e for e in verify_upbit_recording(fixture_dataset).errors)


def test_integrity_detects_raw_summary_disagreement_and_gaps(fixture_dataset):
    rewrite_line(fixture_dataset, 3, lambda ln: ln["orderbook"].update(best_bid=1.0))
    rep = verify_upbit_recording(fixture_dataset)
    assert any("summary differs" in e for e in rep.errors)
    seg = segment_paths(fixture_dataset)[1]
    seg.unlink()
    assert any("gap" in e for e in verify_upbit_recording(fixture_dataset).errors)


def test_mixed_provenance_line_is_rejected(fixture_dataset):
    rewrite_line(fixture_dataset, 4, lambda ln: ln.update(provenance="real"))
    with pytest.raises(ProviderError, match="provenance"):
        list(UpbitRecordingReader(fixture_dataset).iter_events())
    assert any("provenance" in e for e in verify_upbit_recording(fixture_dataset).errors)


def test_contradictory_dataset_flags_rejected(fixture_dataset):
    ds = json.loads((fixture_dataset / "dataset.json").read_text(encoding="utf-8"))
    ds["synthetic"] = False  # claims real while provenance says fixture
    (fixture_dataset / "dataset.json").write_text(json.dumps(ds), encoding="utf-8")
    with pytest.raises(ProviderError, match="contradicts"):
        UpbitRecordingReader(fixture_dataset)
    assert not verify_upbit_recording(fixture_dataset).ok


def test_unflagged_duplicate_trade_is_an_integrity_error(tmp_path):
    make_recorder(scripted([{"frames": frames(trade(1, 1), trade(1, 1))}]), tmp_path).run()
    ds = tmp_path / "KRW-BTC"
    dup_seq = next(ln["local_sequence"] for p in segment_paths(ds) for ln in read_segment(p) if ln.get("duplicate"))
    rewrite_line(ds, dup_seq, lambda ln: ln.update(duplicate=False, duplicate_of=None))
    assert any("not flagged duplicate" in e for e in verify_upbit_recording(ds).errors)


def test_runner_ignores_trade_only_events():
    from moneylab.paper.runner import SimulationRunner
    from moneylab.strategy.market_making import SymmetricMarketMaker

    params = MarketParams(condition_id="c", tokens=(TokenInfo("Y", "Yes"), TokenInfo("N", "No")))
    runner = SimulationRunner(params, SymmetricMarketMaker())
    tick = TradeTick("Y", 0.5, 1.0, "buy", 1.0)
    runner.run([StreamEvent(1.0, trades=(tick,))])
    assert runner.kill.consecutive_errors == 0


# --- CLI ----------------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("MONEYLAB_DATA_DIR", str(tmp_path / "data"))
    return tmp_path / "data"


def test_cli_fixture_record_verify_replay(data_dir, capsys):
    assert main(["record", "--provider", "upbit", "--source", "fixture", "--ping-interval", "3"]) == 0
    ds = data_dir / "raw" / "upbit" / "recordings-fixture" / "upbit_ws_timeline_synthetic" / "KRW-BTC"
    assert (ds / "dataset.json").exists()
    assert main(["record-verify", str(ds)]) == 0
    assert "Integrity OK" in capsys.readouterr().out
    assert main(["replay-check", str(ds)]) == 0
    out = capsys.readouterr().out
    assert "Replay check OK" in out and "SYNTHETIC/FIXTURE" in out
    assert main(["simulate", "--recording", str(ds)]) == 1  # strategies are not connected to Upbit
    assert "not prediction markets" in capsys.readouterr().out


def test_cli_rejects_bad_upbit_options(data_dir, tmp_path, capsys):
    assert main(["record", "--provider", "upbit", "--source", "polymarket"]) == 1
    assert main(["record", "--provider", "upbit", "--source", "fixture", "--market", "btc"]) == 1
    assert main(["record", "--provider", "upbit", "--source", "fixture", "--orderbook-units", "10"]) == 1
    assert main(["record", "--market", "KRW-BTC", "--source", "fixture"]) == 1  # Upbit option on Polymarket
    not_synthetic = tmp_path / "claims_real.json"
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["meta"]["synthetic"] = False
    not_synthetic.write_text(json.dumps(data), encoding="utf-8")
    assert main(["record", "--provider", "upbit", "--source", "fixture", "--fixture", str(not_synthetic)]) == 1
    assert "never pose as real" in capsys.readouterr().out
    assert main(["replay-check", str(tmp_path)]) == 1


def test_cli_polymarket_fixture_recording_still_works(data_dir):
    assert main(["record", "--source", "fixture", "--max-polls", "3"]) == 0


def test_fixture_file_is_marked_synthetic():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["meta"]["synthetic"] is True and "SYNTHETIC" in data["meta"]["description"]


def test_real_recordings_are_git_ignored():
    gitignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "data/raw/*" in gitignore.splitlines()


def test_copy_of_dataset_replays_identically(fixture_dataset, tmp_path):
    copy = tmp_path / "copy" / "KRW-BTC"
    shutil.copytree(fixture_dataset, copy)
    a = [(e.timestamp, e.local_sequence) for e in ReplayBookStream(UpbitRecordingReader(fixture_dataset))]
    b = [(e.timestamp, e.local_sequence) for e in ReplayBookStream(UpbitRecordingReader(copy))]
    assert a == b and len(a) > 40
