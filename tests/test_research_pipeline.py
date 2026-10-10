"""research-build / research-stats / research-final: provenance, test lock, manifests, raw immutability,
Upbit export flags and quality report. All data SYNTHETIC (scripted sessions / generated events)."""

import ast
import json
import os
from pathlib import Path

import pytest

from moneylab.cli import main
from moneylab.domain.market_events import (
    CROSSED_BOOK,
    DUPLICATE,
    LOCKED_BOOK,
    RECONNECT_BOUNDARY,
    SEQUENCE_GAP,
    STALE_BOOK,
    TIMESTAMP_REVERSE,
    WARMUP,
)
from moneylab.providers.upbit.recorder.quality import quality_report
from moneylab.providers.upbit.research_export import iter_market_events, raw_manifest
from moneylab.research import pipeline
from moneylab.research.config import load_config
from moneylab.research.io import write_jsonl_gz
from moneylab.research.leaderboard import PAPER_CANDIDATE
from moneylab.research.manifest import NOT_EVIDENCE, read_manifest
from moneylab.research.split import LOCKED_DIR, TEST_FILE, SplitLockedError, load_segment
from research_helpers import session
from upbit_helpers import T0, book, make_recorder, scripted, trade

SRC = Path(__file__).resolve().parents[1] / "src" / "moneylab"


# --- helpers ------------------------------------------------------------------------------------

def short_config(tmp_path: Path, embargo: float = 5.0, resamples: int = 50) -> Path:
    """A registered-style study (own config + preregistration copy) with a short embargo for tests."""
    base = load_config()
    root = tmp_path / "study"
    (root / "configs").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    text = base.config_path.read_text(encoding="utf-8")
    text = text.replace("embargo_seconds = 300", f"embargo_seconds = {embargo:g}")
    text = text.replace("bootstrap_resamples = 1000", f"bootstrap_resamples = {resamples}")
    (root / "configs" / "study.toml").write_text(text, encoding="utf-8")
    (root / "docs" / "research_v04_preregistration.md").write_bytes(base.preregistration_path.read_bytes())
    return root / "configs" / "study.toml"


def events_file(tmp_path: Path, evs, name="events.jsonl.gz") -> Path:
    p = tmp_path / name
    write_jsonl_gz(p, {"schema": "test"}, (e.to_dict() for e in evs))
    return p


def built_run(tmp_path, provenance="real", allow_fixture=False, seconds=240.0):
    cfg = load_config(short_config(tmp_path))
    evs = session(seconds, provenance=provenance)
    run = tmp_path / "run"
    m = pipeline.build(events_file(tmp_path, evs), run, cfg, session_id="s1",
                       source={"provenance": provenance, "market": "KRW-BTC", "raw_manifest_sha256": "x"},
                       allow_fixture=allow_fixture)
    return cfg, run, m


# --- provenance ---------------------------------------------------------------------------------

def test_fixture_events_are_refused_unless_explicitly_allowed_and_then_not_evidence(tmp_path):
    with pytest.raises(pipeline.ProvenanceError):
        built_run(tmp_path, provenance="fixture")
    _, run, m = built_run(tmp_path / "b", provenance="fixture", allow_fixture=True)
    assert m["evidence"] == NOT_EVIDENCE and m["provenance"] == "fixture"


def test_mixed_or_contradicting_provenance_is_refused(tmp_path):
    cfg = load_config(short_config(tmp_path))
    evs = session(60) + [e for e in session(60, start=T0 + 100, provenance="fixture")]
    with pytest.raises(pipeline.ProvenanceError):
        pipeline.build(events_file(tmp_path, evs), tmp_path / "r", cfg, session_id="s",
                       source={"provenance": "real"}, allow_fixture=True)
    with pytest.raises(pipeline.ProvenanceError):
        pipeline.build(events_file(tmp_path, session(60), "b.gz"), tmp_path / "r2", cfg, session_id="s",
                       source={"provenance": "fixture"}, allow_fixture=True)


def test_overrides_only_for_dry_runs(tmp_path):
    cfg = load_config(short_config(tmp_path), embargo_seconds=7.0)
    with pytest.raises(ValueError):
        pipeline.build(events_file(tmp_path, session(240)), tmp_path / "r", cfg, session_id="s",
                       source={"provenance": "real"})


# --- manifest + test lock -----------------------------------------------------------------------

def test_manifest_records_hashes_split_exclusions_and_scenarios(tmp_path):
    cfg, run, m = built_run(tmp_path)
    for key in ("dataset_sha256", "raw_manifest_sha256", "preregistration_sha256", "config_sha256", "git",
                "session_id", "collection", "provenance", "feature_registry", "horizons", "split", "exclusions",
                "fee_scenarios_bps", "delay_scenarios_ms", "test_access_count"):
        assert key in m, key
    assert m["preregistration_sha256"] == cfg.preregistration_sha256 and m["test_access_count"] == 0
    assert m["fee_scenarios_bps"] == [5.0, 15.0, 25.0] and m["delay_scenarios_ms"] == [0, 100, 250]
    assert m["exclusions"]["by_reason"]["warmup"] > 0 and m["evidence"] == "INSUFFICIENT_EVIDENCE"
    assert (run / LOCKED_DIR / TEST_FILE).exists() and m["split"]["rows"]["test"] > 0


def test_test_split_is_locked_until_final_and_opens_exactly_once(tmp_path):
    cfg, run, _ = built_run(tmp_path)
    with pytest.raises(SplitLockedError):
        load_segment(run, "test")
    with pytest.raises(SplitLockedError):  # validation not completed yet
        pipeline.final(run, cfg)
    assert read_manifest(run)["test_access_count"] == 0
    res = pipeline.stats(run, cfg)
    assert all(r["test_result"] == "LOCKED" for r in res["leaderboard"])
    assert read_manifest(run)["test_access_count"] == 0  # stats never touched it
    out = pipeline.final(run, cfg)
    assert read_manifest(run)["test_access_count"] == 1
    assert all(r["test_result"] in ("PASS", "FAIL", "INCONCLUSIVE") for r in out["leaderboard"])
    assert all(r["decision"] != PAPER_CANDIDATE for r in out["leaderboard"])  # one short session
    with pytest.raises(SplitLockedError):
        pipeline.final(run, cfg)
    with pytest.raises(ValueError):  # validation leaderboard is frozen after the test was opened
        pipeline.stats(run, cfg)


def test_final_refuses_changed_preregistration(tmp_path):
    cfg, run, _ = built_run(tmp_path)
    pipeline.stats(run, cfg)
    cfg.preregistration_path.write_text("edited after the fact", encoding="utf-8")
    with pytest.raises(ValueError):
        pipeline.config_for_run(run)
    changed = load_config(cfg.config_path)
    with pytest.raises(SplitLockedError):
        pipeline.final(run, changed)
    assert read_manifest(run)["test_access_count"] == 0


def test_tampered_trainval_file_is_refused(tmp_path):
    cfg, run, _ = built_run(tmp_path)
    p = run / "grid_trainval.jsonl.gz"
    p.write_bytes(p.read_bytes() + b"\x00")
    with pytest.raises(ValueError):
        load_segment(run, "train")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.update(f"{node.module}.{a.name}" for a in node.names)
        elif isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
    return names


def test_no_code_path_bypasses_the_test_lock():
    """Only split.py knows where the test file lives; only pipeline.final uses the vault;
    stats/leaderboard/features/labels never import the split module's readers."""
    for f in list((SRC / "research").rglob("*.py")) + [SRC / "cli.py"]:
        text = f.read_text(encoding="utf-8")
        if f.name != "split.py":
            assert "test.jsonl" not in text and "TEST_FILE" not in text and "LOCKED_DIR" not in text, f
            assert "open_once" not in text or f.name == "pipeline.py", f
            assert "LockedTestVault" not in text or f.name == "pipeline.py", f
    src = (SRC / "research" / "pipeline.py").read_text(encoding="utf-8")
    final_body = src[src.index("def final("):]
    assert "LockedTestVault(" in final_body and src.count("LockedTestVault(") == 1
    for name in ("stats.py", "leaderboard.py", "features.py", "labels.py", "sampling.py", "book_state.py"):
        assert not any(m.startswith("moneylab.research.split") for m in _imports(SRC / "research" / name)), name


# --- Upbit export flags + quality ---------------------------------------------------------------

def flagged_dataset(tmp_path: Path, provenance="fixture") -> Path:
    def at(dt, raw):
        return {"t": T0 + dt, "raw": raw}
    ms = int(T0 * 1000)
    c1 = [at(0.1, book(ms + 100, stream_type="SNAPSHOT")), at(0.2, book(ms + 200)), at(0.3, trade(1, ms + 250)),
          at(6.0, book(ms + 6000)), at(6.1, book(ms + 6100, bid=101.0, ask=101.0)),
          at(6.2, book(ms + 6200, bid=102.0, ask=101.0)), at(6.3, book(ms + 5000)),  # exchange ts goes back
          at(9.0, book(ms + 9000)),  # 2.7 s after the previous book: stale
          {"t": T0 + 9.1, "raw_text": "{not json"}, at(9.2, trade(2, ms + 9150))]
    c2 = [at(12.0, book(ms + 9000, stream_type="SNAPSHOT")), at(12.1, trade(2, ms + 9150, stream_type="SNAPSHOT")),
          at(12.2, book(ms + 12200))]
    src = scripted([{"frames": c1, "close": {"code": 1006, "reason": "x"}}, {"frames": c2}])
    out = tmp_path / "raw" / "sess"
    make_recorder(src, out, provenance=provenance, origin="fixture:flags").run()
    return out / "KRW-BTC"


def test_export_flags_quality_problems_without_dropping_them(tmp_path):
    ds = flagged_dataset(tmp_path)
    evs = list(iter_market_events(ds))
    books = [e for e in evs if e.event_type == "book"]
    assert WARMUP in books[0].flags and books[0].stream_type == "SNAPSHOT"
    assert LOCKED_BOOK in books[3].flags and CROSSED_BOOK in books[4].flags
    assert TIMESTAMP_REVERSE in books[5].flags and STALE_BOOK in books[6].flags
    after_malformed = next(e for e in evs if e.event_type == "trade" and e.trade.trade_id == 2)
    assert SEQUENCE_GAP in after_malformed.flags
    dups = [e for e in evs if DUPLICATE in e.flags]
    assert len(dups) == 2  # the re-sent SNAPSHOT book and trade after the reconnect are kept, flagged
    assert sum(1 for e in evs if e.event_type == "connection") == 2
    assert all(RECONNECT_BOUNDARY in e.flags for e in evs if e.event_type in ("connection", "disconnect"))
    first_after = [e for e in evs if e.is_market_data and e.connection_id == evs[-1].connection_id][0]
    assert RECONNECT_BOUNDARY in first_after.flags
    assert {e.provenance for e in evs} == {"fixture"}
    q = quality_report(ds).to_dict()
    assert q["export"]["flags"]["duplicate"] == 2 and q["export"]["skipped"].get("malformed_parse_error") == 1
    assert q["recv_minus_exchange_ms"]["book"]["n"] > 0 and "not latency" in q["note"]


def test_research_build_never_modifies_raw_data(tmp_path, monkeypatch):
    ds = flagged_dataset(tmp_path)
    before = raw_manifest(ds)
    mtimes = {p: p.stat().st_mtime_ns for p in ds.rglob("*") if p.is_file()}
    monkeypatch.setenv("MONEYLAB_DATA_DIR", str(tmp_path / "data"))
    main(["research-build", str(ds), "--allow-fixture", "--dry-run", "--embargo-seconds", "1",
          "--out", str(tmp_path / "processed")])  # too short to split: refused, raw still untouched
    assert raw_manifest(ds) == before
    assert {p: p.stat().st_mtime_ns for p in ds.rglob("*") if p.is_file()} == mtimes


# --- CLI end to end on a scripted (fixture) session ---------------------------------------------

def long_fixture_dataset(tmp_path: Path, seconds: int = 240) -> Path:
    ms = int(T0 * 1000)
    frames, sid = [], 10
    for i in range(seconds * 5):
        t = 0.1 + 0.2 * i
        mid = 100_000_000 + 1000 * ((i // 7) % 9 - 4)
        frames.append({"t": T0 + t, "raw": book(ms + int(t * 1000), bid=mid - 1000.0, ask=mid + 1000.0, size=0.5,
                                                stream_type="SNAPSHOT" if i == 0 else "REALTIME")})
        if i % 4 == 1:
            sid += 1
            frames.append({"t": T0 + t + 0.05, "raw": trade(sid, ms + int(t * 1000) + 40, price=float(mid),
                                                            volume=0.001 * (1 + i % 3), side="BID" if i % 3 else "ASK")})
    src = scripted([{"frames": frames, "ping_reply": True}])
    out = tmp_path / "raw" / "fixture_session"
    make_recorder(src, out, provenance="fixture", origin="fixture:long", orderbook_units=1).run()
    return out / "KRW-BTC"


def test_cli_research_workflow_on_fixture_data(tmp_path, capsys):
    ds = long_fixture_dataset(tmp_path)
    cfgp = short_config(tmp_path)
    out = tmp_path / "processed"
    raw_before = raw_manifest(ds)
    assert main(["research-build", str(ds), "--config", str(cfgp), "--out", str(out)]) == 1  # fixture refused
    assert "research needs real data" in capsys.readouterr().out
    assert main(["research-build", str(ds), "--config", str(cfgp), "--out", str(out), "--allow-fixture"]) == 0
    assert "NOT_EVIDENCE" in capsys.readouterr().out
    assert raw_manifest(ds) == raw_before  # raw dataset untouched by a successful build
    run = next((out / "research").iterdir())
    m = read_manifest(run)
    assert m["capture"]["termination_reasons"] == ["source_exhausted"] and m["capture"]["all_final"]
    assert m["clock_quality_status"] == "NOT_MEASURED"  # fixture sessions run without the clock monitor
    proc = out / "upbit" / "fixture_session" / "KRW-BTC"
    assert (proc / "events.jsonl.gz").exists() and (proc / "raw_manifest.json").exists()
    assert json.loads((proc / "quality.json").read_text(encoding="utf-8"))["provenance"] == "fixture"
    assert main(["research-stats", str(run)]) == 0
    printed = capsys.readouterr().out
    assert "NOT_EVIDENCE" in printed and "LOCKED" in printed
    board = json.loads((run / "stats" / "leaderboard.json").read_text(encoding="utf-8"))["rows"]
    assert len(board) == 29 * 4 and all(r["decision"] != PAPER_CANDIDATE for r in board)
    assert set(board[0]) >= {"feature", "horizon", "N", "missing_rate", "Spearman_IC", "IC_CI_low", "IC_CI_high",
                             "BH_q", "top_bottom_bps", "directional_accuracy", "gross_edge_bps",
                             "estimated_cost_bps", "net_edge_bps", "fee_sensitivity", "delay_sensitivity",
                             "validation_result", "test_result", "decision"}
    assert set(board[0]["fee_sensitivity"]) == {"5bp", "15bp", "25bp"}
    assert set(board[0]["delay_sensitivity"]) == {"0ms", "100ms", "250ms"}
    assert main(["research-final", str(run)]) == 0
    capsys.readouterr()
    assert main(["research-final", str(run)]) == 1
    assert "already opened" in capsys.readouterr().out
    assert read_manifest(run)["test_access_count"] == 1


def test_cli_embargo_override_requires_dry_run(tmp_path, capsys):
    ds = long_fixture_dataset(tmp_path, seconds=60)
    assert main(["research-build", str(ds), "--allow-fixture", "--embargo-seconds", "5",
                 "--out", str(tmp_path / "p")]) == 1
    assert "only allowed with --dry-run" in capsys.readouterr().out


def test_processed_outputs_are_git_ignored():
    root = Path(__file__).resolve().parents[1]
    ignore = (root / ".gitignore").read_text(encoding="utf-8")
    assert "data/processed/*" in ignore and "data/raw/*" in ignore
    assert os.path.isdir(root / "configs") and (root / "configs" / "research_v04.toml").exists()


def test_market_event_round_trip_and_validation():
    from moneylab.domain.market_events import MarketEvent

    ev = session(10)[3]
    assert MarketEvent.from_dict(json.loads(json.dumps(ev.to_dict()))) == ev
    with pytest.raises(ValueError):
        MarketEvent(market="KRW-BTC", event_type="book", provenance="real", received_timestamp=1.0,
                    local_sequence=1, flags=frozenset({"made_up"}))
    with pytest.raises(ValueError):
        MarketEvent(market="KRW-BTC", event_type="book", provenance="simulated", received_timestamp=1.0,
                    local_sequence=1)


# --- Phase 1.1 ------------------------------------------------------------------------------------

def test_short_dry_run_no_longer_mass_rejects(tmp_path):
    """Regression: a 5-minute dry run used to REJECT 97/116 tests only because CIs were not computable."""
    cfg = load_config(short_config(tmp_path), embargo_seconds=15.0)
    run = tmp_path / "dry"
    pipeline.build(events_file(tmp_path, session(300)), run, cfg, session_id="dry",
                   source={"provenance": "real", "market": "KRW-BTC"}, dry_run=True)
    board = pipeline.stats(run, cfg)["leaderboard"]
    assert len(board) == 116
    assert not [r for r in board if r["decision"] == "REJECT"]
    assert {r["evidence_class"] for r in board} == {"INSUFFICIENT_EVIDENCE"}
    assert {r["decision_reason"] for r in board} == {"INSUFFICIENT_EVIDENCE"}
    assert {r["evidence"] for r in board} == {"DRY_RUN/INSUFFICIENT_EVIDENCE"}


def test_dry_runs_never_open_the_test_split(tmp_path):
    cfg = load_config(short_config(tmp_path))
    run = tmp_path / "dry"
    pipeline.build(events_file(tmp_path, session(240)), run, cfg, session_id="dry",
                   source={"provenance": "real", "market": "KRW-BTC"}, dry_run=True)
    pipeline.stats(run, cfg)
    with pytest.raises(SplitLockedError):
        pipeline.final(run, cfg)
    assert read_manifest(run)["test_access_count"] == 0


def test_manifest_carries_clock_quality_metadata_only(tmp_path):
    _, _, m = built_run(tmp_path)
    assert m["clock_quality_status"] == "NOT_MEASURED" and m["clock_measurements"] == 0
    cfg = load_config(short_config(tmp_path / "c"))
    clock = {"clock_offset_start_ms": -6.0, "clock_offset_end_ms": -202.0, "clock_offset_min_ms": -202.0,
             "clock_offset_max_ms": -6.0, "clock_offset_median_ms": -100.0, "clock_measurements": 12,
             "clock_quality_status": "WARNING", "clock_drift_ppm": -38.0}
    evs = session(240)
    m2 = pipeline.build(events_file(tmp_path, evs, "c.gz"), tmp_path / "r2", cfg, session_id="s",
                        source={"provenance": "real", "market": "KRW-BTC", "clock": clock})
    for k in ("clock_offset_start_ms", "clock_offset_end_ms", "clock_offset_min_ms", "clock_offset_max_ms",
              "clock_offset_median_ms", "clock_measurements", "clock_quality_status"):
        assert m2[k] == clock[k], k
    # quality metadata only: identical grid rows (features, labels, reasons) with or without a clock record
    from moneylab.research.io import iter_jsonl_gz

    _, plain_run, _ = built_run(tmp_path / "again")
    rows_clock = list(iter_jsonl_gz(tmp_path / "r2" / "grid_trainval.jsonl.gz")[1])
    rows_plain = list(iter_jsonl_gz(plain_run / "grid_trainval.jsonl.gz")[1])
    assert rows_clock == rows_plain and len(rows_clock) > 100
