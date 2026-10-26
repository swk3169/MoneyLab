"""BT-3c upper-bound input segments (SYNTHETIC / NOT_EVIDENCE).

Sources are the fixture candle pulls exported in tmp_path (as in tests/test_backtest_run.py) or bar directories
written here by hand. Nothing is fetched; nothing is written outside tmp_path. No random numbers."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from backtest_helpers import DAY, HOUR, T0, daily_bars, flat_bar, hourly_bars
from test_bar_export import fixture_pull

from moneylab import cli
from moneylab.backtest import run as runmod
from moneylab.backtest import segment as segmod
from moneylab.backtest.bars_io import load_bars
from moneylab.backtest.code_state import classify_worktree
from moneylab.backtest.costs import CostModel
from moneylab.backtest.data import DataIntegrityError
from moneylab.backtest.portfolio import RunConfig, simulate
from moneylab.backtest.run import INITIAL_CASH_KRW, RunError, run_backtest, verify_run
from moneylab.backtest.segment import (
    ALREADY_EXISTS_IDENTICAL,
    CREATED,
    SegmentError,
    cut_for,
    export_segment,
    plan_segment,
    read_segment,
)
from moneylab.backtest.settings import DEFAULT_SETTINGS_FILE, cost_model, load_cost_settings
from moneylab.domain.bars import NOT_EVIDENCE, canonical_bar_rows
from moneylab.providers.upbit.bar_export import export_bars
from moneylab.storage.atomic import sha256_file

CODE = classify_worktree("c" * 40, [])
NOW = datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)
LAST = datetime(2025, 11, 28, tzinfo=UTC)  # cut 2025-12-01 00:00; the fixture runs to 2025-12-18


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    root = tmp_path_factory.mktemp("bt3c-seg")
    pulls = {iv: fixture_pull(root / "pulls", iv) for iv in ("day", "hour")}
    return {iv: export_bars(p, root / "bars-fixture").dir for iv, p in pulls.items()}


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def write_bars(root: Path, name: str, bars, *, body: bytes | None = None) -> Path:
    """A bars/1 directory written by hand; `body` overrides the canonical rows (manifest and sums follow it)."""
    d = root / name
    d.mkdir(parents=True)
    interval = bars[0].interval
    data = canonical_bar_rows(bars) if body is None else body
    bars_file = f"bars_{interval}.jsonl"
    rows = sorted(bars, key=lambda b: b.start_utc)
    manifest = {"schema": "moneylab.backtest.bars/1", "evidence": NOT_EVIDENCE, "provenance": "fixture",
                "market": "KRW-BTC", "interval": interval, "bars": len(data.splitlines()),
                "first_start": rows[0].to_record()["start_utc"], "last_start": rows[-1].to_record()["start_utc"],
                "bars_file": bars_file, "bars_sha256": hashlib.sha256(data).hexdigest(),
                "source_pull": {"pull_id": name}, "confirmation_rule": "hand written (tests)"}
    (d / bars_file).write_bytes(data)
    (d / "bars_manifest.json").write_bytes((json.dumps(manifest, sort_keys=True, indent=1) + "\n").encode())
    sums = "".join(f"{sha256_file(d / n)}  {n}\n" for n in sorted([bars_file, "bars_manifest.json"]))
    (d / "SHA256SUMS.txt").write_text(sums, encoding="utf-8", newline="\n")
    return d


def hand_source(root: Path, days: int = 60, *, daily=None, hourly=None):
    root.mkdir(parents=True, exist_ok=True)
    daily = daily if daily is not None else daily_bars([100 + (i * 7) % 13 for i in range(days)])
    hourly = hourly if hourly is not None else hourly_bars(days + 2, lambda d, h: Decimal(1000 + d))
    return write_bars(root, "day_hand", daily), write_bars(root, "hour_hand", hourly)


def run_cfg(first: datetime, last: datetime, rule: str = "sma20") -> RunConfig:
    s, _ = load_cost_settings()
    model, verified = cost_model(s, 25, "E0", INITIAL_CASH_KRW)
    return RunConfig(rule, first, last, INITIAL_CASH_KRW, model, capacity_verified=verified)


def run(day: Path, hour: Path, cfg: RunConfig, out: Path, now: datetime = NOW):
    return run_backtest(day, hour, cfg, out, code_state=CODE, settings_file=DEFAULT_SETTINGS_FILE, now=now)


def seg_children(exp):
    m = exp.plan.manifest
    return exp.dir / m["intervals"]["day"]["dir_name"], exp.dir / m["intervals"]["hour"]["dir_name"]


def diff_paths(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        out = set()
        for k in set(a) | set(b):
            out |= diff_paths(a.get(k), b.get(k), path + (k,))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = set()
        for i, (x, y) in enumerate(zip(a, b)):
            out |= diff_paths(x, y, path + (i,))
        return out
    return set() if a == b else {path}


# --- layout, determinism, collisions (S1-S3) ------------------------------------------------------------------

def test_layout_sums_and_identity_order(source, tmp_path):
    exp = export_segment(source["day"], source["hour"], LAST, tmp_path / "seg-fixture")
    assert exp.status == CREATED
    m = exp.plan.manifest
    assert m["schema"] == "moneylab.backtest.segment/1" and m["evidence"] == NOT_EVIDENCE
    assert m["cut_end_utc"] == "2025-12-01T00:00:00Z" and m["rule"] == "bar.end_utc <= cut_end_utc"
    lines = (exp.dir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    names = [ln.split("  ", 1)[1] for ln in lines]
    assert len(names) == 7 and names == sorted(names, key=str.encode) and "SHA256SUMS.txt" not in names
    payload = segmod.content_payload(m)
    for key in ("source_locator", "segment_id", "segment_content_sha256"):
        assert key not in payload and key not in json.dumps(payload)
    assert m["segment_content_sha256"] == segmod.sha256_of(payload)
    assert exp.dir.name == m["segment_id"] and m["segment_id"].endswith(m["segment_content_sha256"][:12])
    assert exp.plan.manifest_sha256 == sha256_file(exp.dir / "segment_manifest.json")
    day_child, hour_child = seg_children(exp)
    assert day_child.name == Path(source["day"]).name and hour_child.name == Path(source["hour"]).name
    child = json.loads((day_child / "bars_manifest.json").read_text(encoding="utf-8"))
    assert "candle_report" not in child and child["source_pull"]["pull_id"]
    info = read_segment(exp.dir)
    assert info.content_sha256 == m["segment_content_sha256"] and info.manifest_sha256 == exp.plan.manifest_sha256


def test_s1_second_export_is_identical_and_writes_nothing(source, tmp_path):
    out = tmp_path / "seg-fixture"
    first = export_segment(source["day"], source["hour"], LAST, out)
    before = tree_bytes(out)
    mtimes = {p: p.stat().st_mtime_ns for p in out.rglob("*") if p.is_file()}
    second = export_segment(source["day"], source["hour"], LAST, out)
    assert second.status == ALREADY_EXISTS_IDENTICAL and second.dir == first.dir
    assert tree_bytes(out) == before and {p: p.stat().st_mtime_ns for p in out.rglob("*") if p.is_file()} == mtimes


def test_s2_same_content_from_another_path_same_id(source, tmp_path):
    copy = tmp_path / "copy" / "bars-fixture"
    for iv in ("day", "hour"):
        shutil.copytree(source[iv], copy / Path(source[iv]).name)
    a = export_segment(source["day"], source["hour"], LAST, tmp_path / "a-fixture")
    b = export_segment(copy / Path(source["day"]).name, copy / Path(source["hour"]).name, LAST, tmp_path / "b-fixture")
    assert a.plan.content_sha256 == b.plan.content_sha256 and a.plan.segment_id == b.plan.segment_id
    assert a.plan.manifest_sha256 != b.plan.manifest_sha256
    assert a.plan.manifest["source_locator"] != b.plan.manifest["source_locator"]


def test_s3_same_root_different_locator_is_refused(source, tmp_path):
    out = tmp_path / "seg-fixture"
    export_segment(source["day"], source["hour"], LAST, out)
    before = tree_bytes(out)
    copy = tmp_path / "copy" / "bars-fixture"
    for iv in ("day", "hour"):
        shutil.copytree(source[iv], copy / Path(source[iv]).name)
    with pytest.raises(SegmentError, match="refusing to overwrite"):
        export_segment(copy / Path(source["day"]).name, copy / Path(source["hour"]).name, LAST, out)
    assert tree_bytes(out) == before


# --- cut semantics (S4-S9) --------------------------------------------------------------------------------------

def test_s4_append_after_g_end_keeps_segment_and_consumed_bars(tmp_path):
    last = T0 + 30 * DAY
    cut = cut_for(last)
    days = 40
    base_d = daily_bars([100 + (i * 7) % 13 for i in range(days)])
    base_h = hourly_bars(days, lambda d, h: Decimal(1000 + d))
    a = hand_source(tmp_path / "a", daily=base_d, hourly=base_h)
    more_d = base_d + daily_bars([500, 600], start=T0 + days * DAY)
    more_h = base_h + [flat_bar("hour", T0 + days * DAY + i * HOUR, Decimal(9999)) for i in range(5)]
    b = hand_source(tmp_path / "b", daily=more_d, hourly=more_h)
    pa, pb = plan_segment(*a, last), plan_segment(*b, last)
    for iv in ("day", "hour"):
        ra, rb = pa.manifest["intervals"][iv], pb.manifest["intervals"][iv]
        # source lineage changes
        assert ra["source_bars_sha256"] != rb["source_bars_sha256"]
        assert ra["source_bars_manifest_sha256"] != rb["source_bars_manifest_sha256"]
        assert ra["source_bars"] != rb["source_bars"]
        # segment content does not
        assert ra["segment_bars_sha256"] == rb["segment_bars_sha256"] and ra["segment_bars"] == rb["segment_bars"]
        sa, sb = load_bars(a[0 if iv == "day" else 1]), load_bars(b[0 if iv == "day" else 1])
        assert runmod.consumed(sa, cut) == runmod.consumed(sb, cut)
    assert pa.content_sha256 == pb.content_sha256 and pa.segment_id == pb.segment_id
    assert pa.manifest_sha256 != pb.manifest_sha256
    for key in ("source_bars_sha256", "source_bars_manifest_sha256", "source_bars"):
        assert key not in json.dumps(segmod.content_payload(pa.manifest))
    cfg = RunConfig("sma20", T0 + 20 * DAY, last, INITIAL_CASH_KRW, CostModel.scenario(25, 5))
    ra = simulate(load_bars(a[0]), load_bars(a[1]), cfg)
    rb = simulate(load_bars(b[0]), load_bars(b[1]), cfg)
    assert (ra.signals, ra.ledger.trades, ra.ledger.daily) == (rb.signals, rb.ledger.trades, rb.ledger.daily)
    assert ra.to_dict()["metrics"] == rb.to_dict()["metrics"]
    assert cut < T0 + days * DAY


def test_s5_change_at_or_before_g_end_changes_the_segment(tmp_path):
    last = T0 + 30 * DAY
    base = daily_bars([100 + (i * 7) % 13 for i in range(40)])
    changed = list(base)
    changed[10] = flat_bar("day", T0 + 10 * DAY, Decimal(777))
    hours = hourly_bars(42, lambda d, h: Decimal(1000 + d))
    src_a = hand_source(tmp_path / "a", daily=base, hourly=hours)
    src_b = hand_source(tmp_path / "b", daily=changed, hourly=hours)
    pa, pb = plan_segment(*src_a, last), plan_segment(*src_b, last)
    a, b = pa.manifest["intervals"], pb.manifest["intervals"]
    assert a["day"]["segment_bars_sha256"] != b["day"]["segment_bars_sha256"]
    assert a["hour"]["segment_bars_sha256"] == b["hour"]["segment_bars_sha256"]
    assert pa.content_sha256 != pb.content_sha256 and pa.segment_id != pb.segment_id
    cut = cut_for(last)
    assert runmod.consumed(load_bars(src_a[0]), cut) != runmod.consumed(load_bars(src_b[0]), cut)


def test_s6_s7_bar_ending_exactly_at_the_cut_is_kept_one_bucket_later_is_not(tmp_path):
    last = T0 + 30 * DAY
    cut = cut_for(last)  # T0 + 33 days
    day_dir, hour_dir = hand_source(tmp_path / "s", 40)
    plan = plan_segment(day_dir, hour_dir, last)
    m = plan.manifest["intervals"]
    assert m["day"]["last_start"] == (cut - DAY).strftime("%Y-%m-%dT%H:%M:%SZ")  # daily bar ending at the cut
    assert m["hour"]["last_start"] == (cut - HOUR).strftime("%Y-%m-%dT%H:%M:%SZ")  # hourly bar ending at the cut
    exp = export_segment(day_dir, hour_dir, last, tmp_path / "seg-fixture")
    day_child, hour_child = seg_children(exp)
    assert max(b.end_utc for b in load_bars(day_child).bars) == cut
    assert max(b.end_utc for b in load_bars(hour_child).bars) == cut
    assert all(b.end_utc <= cut for b in load_bars(hour_child).bars)
    assert any(b.end_utc == cut + HOUR for b in load_bars(hour_dir).bars)  # the source does have the later bucket


def test_s8_broken_row_after_the_cut_refuses_both_paths(tmp_path):
    last = T0 + 30 * DAY
    good = daily_bars([100 + i for i in range(40)])
    body = canonical_bar_rows(good) + b"this is not json\n"
    day_dir = write_bars(tmp_path / "src", "day_bad", good, body=body)
    hour_dir = write_bars(tmp_path / "src", "hour_ok", hourly_bars(42, lambda d, h: Decimal(1000 + d)))
    with pytest.raises(DataIntegrityError, match="unreadable bar rows"):
        export_segment(day_dir, hour_dir, last, tmp_path / "seg-fixture")
    with pytest.raises(DataIntegrityError, match="unreadable bar rows"):
        run(day_dir, hour_dir, run_cfg(T0 + 20 * DAY, last), tmp_path / "runs-fixture")
    assert not (tmp_path / "seg-fixture").exists() or not any((tmp_path / "seg-fixture").iterdir())


@pytest.mark.parametrize("rule,first", [("M120", 122), ("sma20", 22)])  # windows that still span the day-3 gap
def test_s9_no_lower_truncation_and_same_warm_up_semantics(tmp_path, rule, first):
    days, last = 160, T0 + 140 * DAY
    daily = [b for b in daily_bars([100 + (i * 7) % 13 for i in range(days)]) if b.start_utc != T0 + 3 * DAY]
    hours = hourly_bars(days + 2, lambda d, h: Decimal(1000 + d))
    day_dir, hour_dir = hand_source(tmp_path / "s", daily=daily, hourly=hours)
    exp = export_segment(day_dir, hour_dir, last, tmp_path / "seg-fixture")
    day_child, hour_child = seg_children(exp)
    assert load_bars(day_child).first_start == load_bars(day_dir).first_start == T0
    cfg = RunConfig(rule, T0 + first * DAY, last, INITIAL_CASH_KRW, CostModel.scenario(25, 5))
    full = simulate(load_bars(day_dir), load_bars(hour_dir), cfg)
    seg = simulate(load_bars(day_child), load_bars(hour_child), cfg)
    assert full.signals == seg.signals
    assert full.ledger.trades == seg.ledger.trades and full.ledger.daily == seg.ledger.daily
    assert "gap_in_window" in {s.reason for s in full.signals}  # the early gap is still seen through the window


def test_s10_reordered_or_duplicated_rows_are_refused(tmp_path):
    last = T0 + 30 * DAY
    bars = daily_bars([100 + i for i in range(40)])
    rows = canonical_bar_rows(bars).splitlines(keepends=True)
    hour_dir = write_bars(tmp_path / "src", "hour_ok", hourly_bars(42, lambda d, h: Decimal(1000 + d)))
    reordered = write_bars(tmp_path / "src", "day_reordered", bars, body=b"".join([rows[1], rows[0], *rows[2:]]))
    duplicated = write_bars(tmp_path / "src", "day_dup", bars, body=b"".join([rows[0], rows[0], *rows[1:]]))
    for day_dir in (reordered, duplicated):
        with pytest.raises(DataIntegrityError):
            export_segment(day_dir, hour_dir, last, tmp_path / "seg-fixture")


# --- tampering, mixing, failure, equivalence (S11-S14) ------------------------------------------------------------

def _exported(source, tmp_path):
    exp = export_segment(source["day"], source["hour"], LAST, tmp_path / "seg-fixture")
    return exp, *seg_children(exp)


@pytest.mark.parametrize("tamper", ["bar_row", "child_manifest", "locator", "missing", "extra"])
def test_s11_tampered_segment_is_refused(source, tmp_path, tamper):
    exp, day_child, hour_child = _exported(source, tmp_path)
    if tamper == "bar_row":
        p = hour_child / "bars_hour.jsonl"
        p.write_bytes(p.read_bytes().replace(b'"close":"', b'"close":"1', 1))
    elif tamper == "child_manifest":
        p = day_child / "bars_manifest.json"
        p.write_bytes(p.read_bytes().replace(b'"evidence"', b'"evidence_"'))
    elif tamper == "locator":
        p = exp.dir / "segment_manifest.json"
        p.write_bytes(p.read_bytes().replace(b'"source_locator"', b'"source_locator_x"'))
    elif tamper == "missing":
        (day_child / "SHA256SUMS.txt").unlink()
    else:
        (exp.dir / "notes.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(SegmentError):
        read_segment(exp.dir)
    with pytest.raises((RunError, DataIntegrityError)):
        run(day_child, hour_child, run_cfg(datetime(2025, 6, 26, tzinfo=UTC), LAST), tmp_path / "runs-fixture")


def test_s11_segment_tampered_after_the_run_fails_identity(source, tmp_path):
    exp, day_child, hour_child = _exported(source, tmp_path)
    out = run(day_child, hour_child, run_cfg(datetime(2025, 6, 26, tzinfo=UTC), LAST), tmp_path / "runs-fixture")
    assert verify_run(out.dir, code_state=CODE).status == "OK"
    p = exp.dir / "segment_manifest.json"  # change only location metadata, and re-sign the top-level sums
    p.write_bytes(p.read_bytes().replace(b"bars-fixture", b"bars-moved-fixture"))
    sums = exp.dir / "SHA256SUMS.txt"
    lines = [ln if not ln.endswith("  segment_manifest.json") else f"{sha256_file(p)}  segment_manifest.json"
             for ln in sums.read_text(encoding="utf-8").splitlines()]
    sums.write_text("".join(ln + "\n" for ln in lines), encoding="utf-8", newline="\n")
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.checks["identity"]["ok"] is False and rep.status == "FAILED" and "identifiers" in \
        rep.checks["identity"]["detail"]


def test_s12_cut_mismatch_mixed_or_different_segments_are_refused(source, tmp_path):
    exp, day_child, hour_child = _exported(source, tmp_path)
    other = export_segment(source["day"], source["hour"], LAST - DAY, tmp_path / "seg2-fixture")
    o_day, o_hour = seg_children(other)
    first = datetime(2025, 6, 26, tzinfo=UTC)
    with pytest.raises(RunError, match="is not this run's G_end"):
        run(day_child, hour_child, run_cfg(first, LAST - DAY), tmp_path / "runs-fixture")
    with pytest.raises(RunError, match="both come from the same segment"):
        run(day_child, source["hour"], run_cfg(first, LAST), tmp_path / "runs-fixture")
    with pytest.raises(RunError, match="different segments"):
        run(day_child, o_hour, run_cfg(first, LAST), tmp_path / "runs-fixture")


def test_s13_failed_export_leaves_no_directory_and_sources_unchanged(source, tmp_path, monkeypatch):
    before = {iv: tree_bytes(Path(source[iv])) for iv in ("day", "hour")}
    calls = []

    def flaky(path, data):
        calls.append(path)
        if len(calls) == 3:
            raise OSError("disk full (injected)")
        return real(path, data)

    real = segmod.atomic_write_bytes
    monkeypatch.setattr(segmod, "atomic_write_bytes", flaky)
    out = tmp_path / "seg-fixture"
    with pytest.raises(OSError, match="injected"):
        export_segment(source["day"], source["hour"], LAST, out)
    assert list(out.iterdir()) == []
    assert {iv: tree_bytes(Path(source[iv])) for iv in ("day", "hour")} == before


def test_s14_segment_run_is_economically_identical_to_the_full_run(source, tmp_path):
    exp, day_child, hour_child = _exported(source, tmp_path)
    cfg = run_cfg(datetime(2025, 6, 26, tzinfo=UTC), LAST)
    full = run(source["day"], source["hour"], cfg, tmp_path / "full-fixture")
    seg = run(day_child, hour_child, cfg, tmp_path / "seg-runs-fixture")
    a, b = full.result.to_dict(), seg.result.to_dict()
    allowed = {("provenance", "day", "bars_sha256"), ("provenance", "hour", "bars_sha256")}
    paths = diff_paths(a, b)
    assert paths and paths <= allowed, paths  # the fixture has bars after the cut, so the source hashes differ
    for key in ("signals", "trades", "unfilled", "cancelled", "daily", "metrics", "labels", "config", "evidence"):
        assert a[key] == b[key]
    assert a["provenance"]["day"]["description"] == b["provenance"]["day"]["description"]
    assert full.manifest["inputs"]["day"]["consumed_sha256"] == seg.manifest["inputs"]["day"]["consumed_sha256"]
    assert full.manifest["inputs"]["hour"]["consumed_sha256"] == seg.manifest["inputs"]["hour"]["consumed_sha256"]
    assert seg.manifest["inputs"]["day"]["segment"]["segment_id"] == exp.plan.segment_id
    assert full.manifest["inputs"]["day"]["segment"] is None


# --- CLI ---------------------------------------------------------------------------------------------------------

def test_cli_backtest_segment_exit_codes(source, tmp_path, capsys):
    out = tmp_path / "seg-fixture"
    args = ["backtest-segment", "--daily", str(source["day"]), "--hourly", str(source["hour"]),
            "--last-day", "2025-11-28", "--out", str(out)]
    assert cli.main(args) == 0 and CREATED in capsys.readouterr().out
    assert cli.main(args) == 0 and ALREADY_EXISTS_IDENTICAL in capsys.readouterr().out
    assert cli.main([*args[:-1], str(tmp_path / "not-a-fixture-root")]) == 1
    assert "refused" in capsys.readouterr().out
