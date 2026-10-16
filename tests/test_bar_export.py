"""BT-2b-1 bar export / load (SYNTHETIC / NOT_EVIDENCE).

Fixture pulls are made offline in tmp_path from tests/fixtures/upbit_candles_backtest_synthetic.json
(the scripted candle session of `candles-pull --source fixture`; no request leaves the process).
The fixture's prices are linear: these tests check the data pipeline, not any strategy."""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from backtest_helpers import DAY, T0, random_market, series

from moneylab.backtest import bars_io
from moneylab.backtest.costs import CostModel
from moneylab.backtest.data import DataIntegrityError, bars_sha256
from moneylab.backtest.portfolio import RunConfig, simulate
from moneylab.core.http import HttpClient
from moneylab.core.ratelimit import SlidingWindowLimiter
from moneylab.domain import bars as domain_bars
from moneylab.domain.bars import NOT_EVIDENCE, canonical_bar_rows
from moneylab.providers.upbit.bar_export import BarExportError, export_bars
from moneylab.providers.upbit.candle_fixture import CandleFixture
from moneylab.providers.upbit.candle_store import pull_to_store
from moneylab.providers.upbit.candles import UpbitCandleClient
from moneylab.providers.upbit.endpoints import REST_BASE_URL
from moneylab.storage.atomic import sha256_file

FIXTURE = Path(__file__).parent / "fixtures" / "upbit_candles_backtest_synthetic.json"
SRC = Path(__file__).resolve().parents[1] / "src" / "moneylab"

# Fixed before bars_sha256 moved to domain (computed with the code of commit 57b9f05).
GOLDEN_DAILY_SHA = "4c871722fbf29c3542fdf8528bb48ff3187cbbaabe7b22f4e48c256c22dd818b"
GOLDEN_HOURLY_SHA = "a0aa8a020715c03b5e05359ae688f3471dc9c76c087e2d12d467d857840ec36f"
GOLDEN_FINAL_EQUITY = "967187.17122748782979312668640906628439134428002511"
# Generated from the fixture (rule and inputs fixed in the fixture file).
GOLDEN_FIXTURE = {  # (bars_sha256, page 0 sha256, bars): 201 days -> 1 in progress, 1 omitted; 4810 hours -> 1 omitted
    "day": ("d6a40221a2c3b810d468b0f522cc2a1ef2305315f43864e0b37e7410251ec561",
            "fe3f3601214a6facee35a581489054661a5c6e97537acf93a0b8af9e8ae76925", 199),
    "hour": ("39ad26cbb0cedfe3a647f6dc01e31d19f8bec58a9d69f460918516bad972e412",
             "bcd5f91fd1adadc98de51e34d39f8d3426eaaacf1d8d75ff8fb6c869166efc5f", 4809),
}
END = {"day": datetime(2025, 12, 19, tzinfo=UTC), "hour": datetime(2025, 12, 18, 11, tzinfo=UTC)}


def fixture_pull(root: Path, interval: str, provenance: str = "fixture") -> Path:
    fx = CandleFixture.load(FIXTURE)
    noop = lambda s: None  # noqa: E731 - scripted session, no clock to wait for
    client = UpbitCandleClient(HttpClient(REST_BASE_URL, session=fx.session()), sleep=noop, utcnow=lambda: fx.now,
                               limiter=SlidingWindowLimiter([(1000, 1.0)], clock=lambda: 0.0, sleep=noop))
    _, store = pull_to_store(client, root, "KRW-BTC", interval, datetime(2025, 6, 1, tzinfo=UTC), END[interval],
                             provenance=provenance, origin=f"fixture:{FIXTURE.name}", utcnow=lambda: fx.now)
    return store.dir


def tree_hashes(d: Path) -> dict[str, str]:
    return {p.relative_to(d).as_posix(): sha256_file(p) for p in sorted(d.rglob("*")) if p.is_file()}


@pytest.fixture(scope="module")
def pulls(tmp_path_factory):
    root = tmp_path_factory.mktemp("pulls")
    return {iv: fixture_pull(root, iv) for iv in ("day", "hour")}


# --- A. hashes -------------------------------------------------------------------------------------------

def test_golden_bt1_hashes_and_run():
    daily, hourly = random_market(60, seed=4)
    got = (bars_sha256(daily), bars_sha256(hourly))
    cfg = RunConfig("sma20", T0, T0 + 55 * DAY, Decimal(1_000_000), CostModel.scenario(25, 5))
    res = simulate(series(daily), series(hourly), cfg)
    got += (str(res.ledger.daily[-1].equity),)
    assert got == (GOLDEN_DAILY_SHA, GOLDEN_HOURLY_SHA, GOLDEN_FINAL_EQUITY), f"golden values: {got}"


def test_backtest_data_delegates_to_domain():
    from moneylab.backtest import data

    assert data.bars_sha256 is domain_bars.bars_sha256
    daily, _ = random_market(30, seed=1)
    assert domain_bars.bars_sha256(daily) == data.bars_sha256(list(reversed(daily)))


def test_fixture_generation_is_fixed_and_reproducible(tmp_path, pulls):
    got = {}
    for iv, d in pulls.items():
        exp = export_bars(d, tmp_path / "a-fixture")
        page0 = json.loads((d / "pull.json").read_text(encoding="utf-8"))["pages"][0]["sha256"]
        got[iv] = (exp.bars_sha256, page0, exp.bars)
    assert got == GOLDEN_FIXTURE, f"fixture golden values: {got}"
    again = fixture_pull(tmp_path / "again", "hour")  # same inputs -> same bytes
    assert tree_hashes(again) == tree_hashes(pulls["hour"])


# --- export ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("interval", ["day", "hour"])
def test_export_writes_three_files_and_byte_hash_equals_content_hash(tmp_path, pulls, interval):
    exp = export_bars(pulls[interval], tmp_path / "bars-fixture")
    files = sorted(p.name for p in exp.dir.iterdir())
    assert files == sorted(["SHA256SUMS.txt", "bars_manifest.json", f"bars_{interval}.jsonl"])
    byte_sha = sha256_file(exp.dir / f"bars_{interval}.jsonl")
    assert byte_sha == exp.bars_sha256 == exp.manifest["bars_sha256"]
    sums = dict(reversed(line.split("  ")) for line in (exp.dir / "SHA256SUMS.txt").read_text().splitlines())
    assert sums == {f"bars_{interval}.jsonl": byte_sha, "bars_manifest.json": sha256_file(exp.dir / "bars_manifest.json")}
    assert exp.manifest["evidence"] == NOT_EVIDENCE and exp.manifest["provenance"] == "fixture"
    assert not [p for p in exp.dir.parent.iterdir() if p.name.startswith(".tmp-")]  # temp dir gone


@pytest.mark.parametrize("interval", ["day", "hour"])
def test_export_content_matches_the_pull(tmp_path, pulls, interval):
    exp = export_bars(pulls[interval], tmp_path / "bars-fixture")
    report = json.loads((pulls[interval] / "pull.json").read_text(encoding="utf-8"))["report"]
    s = bars_io.load_bars(exp.dir)
    assert len(s) == exp.bars == report["candles"]
    assert report["excluded_incomplete"] == 1  # the bucket in progress at now_utc is not a bar
    step_td = s.bars[1].start_utc - s.bars[0].start_utc
    ours = [((start - step_td).strftime("%Y-%m-%dT%H:%M:%SZ"), n) for start, n in s.gaps]
    assert ours == [(g["after"], g["missing"]) for g in report["gaps"]]
    assert sum(n for _, n in s.gaps) == report["missing_buckets"] == 1  # the one omitted bucket
    first = s.bars[0]
    step = Decimal(240000) if interval == "day" else Decimal(10000)
    assert first.open == Decimal(100_000_000) and first.close == first.open + step
    assert first.value_krw == first.volume * first.close  # acc_trade_price -> value_krw


def test_daily_close_equals_last_hour_close(tmp_path, pulls):
    d = bars_io.load_bars(export_bars(pulls["day"], tmp_path / "b-fixture").dir)
    h = bars_io.load_bars(export_bars(pulls["hour"], tmp_path / "b-fixture").dir)
    for bar in d.bars[:30]:
        last_hour = h.at_start(bar.end_utc - (h.bars[1].start_utc - h.bars[0].start_utc))
        assert last_hour is not None and last_hour.close == bar.close


def test_load_returns_the_exported_bars_with_provenance(tmp_path, pulls):
    exp = export_bars(pulls["day"], tmp_path / "c-fixture")
    s = bars_io.load_bars(exp.dir)
    assert s.provenance.kind == "fixture" and s.provenance.bars_sha256 == exp.bars_sha256
    assert canonical_bar_rows(s.bars) == (exp.dir / "bars_day.jsonl").read_bytes()
    assert s.provenance.evidence == NOT_EVIDENCE


def test_export_is_reproducible_across_roots(tmp_path, pulls):
    a = export_bars(pulls["hour"], tmp_path / "x-fixture")
    b = export_bars(pulls["hour"], tmp_path / "y-fixture")
    assert (a.dir / "bars_hour.jsonl").read_bytes() == (b.dir / "bars_hour.jsonl").read_bytes()
    assert tree_hashes(a.dir) == tree_hashes(b.dir)


def test_export_leaves_the_pull_untouched(tmp_path, pulls):
    before = tree_hashes(pulls["day"])
    export_bars(pulls["day"], tmp_path / "d-fixture")
    assert tree_hashes(pulls["day"]) == before


# --- export refusals: nothing final is written ----------------------------------------------------------

def _no_output(root: Path) -> bool:
    return not root.exists() or not any(root.iterdir())


def test_real_pull_is_refused(tmp_path):
    real = fixture_pull(tmp_path / "p", "day", provenance="real")  # synthetic bytes labelled real, tmp only
    with pytest.raises(BarExportError, match="provenance"):
        export_bars(real, tmp_path / "e-fixture")
    with pytest.raises(BarExportError, match="BT-5"):
        export_bars(real, tmp_path / "e2", allowed_provenance=("fixture", "real"))
    assert _no_output(tmp_path / "e-fixture") and _no_output(tmp_path / "e2")


def test_tampered_or_incomplete_pull_is_refused(tmp_path):
    p = fixture_pull(tmp_path / "p", "day")
    page = p / "pages" / "0000.json"
    page.write_bytes(page.read_bytes().replace(b"100", b"101", 1))
    with pytest.raises(BarExportError, match="verification"):
        export_bars(p, tmp_path / "f-fixture")
    q = fixture_pull(tmp_path / "q", "hour")
    doc = json.loads((q / "pull.json").read_text(encoding="utf-8"))
    doc["status"] = "running"
    (q / "pull.json").write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(BarExportError, match="verification"):
        export_bars(q, tmp_path / "f-fixture")
    assert _no_output(tmp_path / "f-fixture")


def test_fixture_needs_a_fixture_root_and_never_overwrites(tmp_path, pulls):
    with pytest.raises(BarExportError, match="-fixture"):
        export_bars(pulls["day"], tmp_path / "backtest_bars")
    assert _no_output(tmp_path / "backtest_bars")
    exp = export_bars(pulls["day"], tmp_path / "g-fixture")
    before = tree_hashes(exp.dir)
    with pytest.raises(BarExportError, match="already exists"):
        export_bars(pulls["day"], tmp_path / "g-fixture")
    assert tree_hashes(exp.dir) == before


def test_failed_write_leaves_no_final_directory(tmp_path, pulls, monkeypatch):
    from moneylab.providers.upbit import bar_export

    def boom(*a, **k):
        raise OSError("disk full (simulated)")

    calls = {"n": 0}
    real_write = bar_export.atomic_write_bytes

    def second_write_fails(path, data):
        calls["n"] += 1
        if calls["n"] == 2:
            boom()
        return real_write(path, data)

    monkeypatch.setattr(bar_export, "atomic_write_bytes", second_write_fails)
    with pytest.raises(OSError, match="simulated"):
        export_bars(pulls["day"], tmp_path / "h-fixture")
    assert list((tmp_path / "h-fixture").iterdir()) == []  # no final dir, temp dir removed


# --- load refusals ---------------------------------------------------------------------------------------

@pytest.fixture()
def exported(tmp_path, pulls):
    return export_bars(pulls["day"], tmp_path / "i-fixture").dir


def test_load_refuses_a_changed_bar_byte(exported):
    f = exported / "bars_day.jsonl"
    f.write_bytes(f.read_bytes().replace(b'"close":"1', b'"close":"2', 1))
    with pytest.raises(DataIntegrityError, match="SHA256SUMS"):
        bars_io.load_bars(exported)


def test_load_refuses_consistent_sums_but_wrong_manifest_hash(exported):
    man = exported / "bars_manifest.json"
    doc = json.loads(man.read_text(encoding="utf-8"))
    doc["bars_sha256"] = "0" * 64
    man.write_text(json.dumps(doc), encoding="utf-8")
    sums = exported / "SHA256SUMS.txt"
    lines = [ln if not ln.endswith("bars_manifest.json") else f"{sha256_file(man)}  bars_manifest.json"
             for ln in sums.read_text().splitlines()]
    sums.write_text("\n".join(lines) + "\n")
    with pytest.raises(DataIntegrityError, match="manifest bars_sha256"):
        bars_io.load_bars(exported)


def test_load_refuses_non_canonical_bytes_with_the_same_bars(exported):
    """Byte hash and content hash are separate checks: reformatted rows (same bars) are refused."""
    f = exported / "bars_day.jsonl"
    rows = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()]
    f.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    new = sha256_file(f)
    man = exported / "bars_manifest.json"
    doc = json.loads(man.read_text(encoding="utf-8"))
    doc["bars_sha256"] = new
    man.write_text(json.dumps(doc), encoding="utf-8")
    (exported / "SHA256SUMS.txt").write_text(f"{new}  bars_day.jsonl\n{sha256_file(man)}  bars_manifest.json\n")
    with pytest.raises(DataIntegrityError, match="content"):
        bars_io.load_bars(exported)


def test_load_refuses_real_and_missing_files(exported):
    man = exported / "bars_manifest.json"
    doc = json.loads(man.read_text(encoding="utf-8"))
    doc["provenance"] = "real"
    man.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(DataIntegrityError, match="refused before BT-5"):
        bars_io.load_bars(exported)
    (exported / "SHA256SUMS.txt").unlink()
    with pytest.raises(DataIntegrityError, match="cannot read"):
        bars_io.load_bars(exported)


# --- end to end and dependencies -------------------------------------------------------------------------

def test_exported_bars_run_through_the_backtest(tmp_path, pulls):
    d = bars_io.load_bars(export_bars(pulls["day"], tmp_path / "j-fixture").dir)
    h = bars_io.load_bars(export_bars(pulls["hour"], tmp_path / "j-fixture").dir)
    first = d.first_start
    cfg = RunConfig("sma20", first + 25 * DAY, first + 180 * DAY, Decimal(1_000_000), CostModel.scenario(25, 5))
    res = simulate(d, h, cfg)
    res.ledger.verify()
    assert res.evidence == NOT_EVIDENCE and res.to_dict()["provenance"]["day"]["kind"] == "fixture"
    assert res.ledger.trades  # pipeline check only; linear prices say nothing about any strategy


def test_bar_export_and_bars_io_dependencies():
    def mods(path: Path) -> set[str]:
        out: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                out.add(node.module)
            elif isinstance(node, ast.Import):
                out.update(a.name for a in node.names)
        return out

    exp = mods(SRC / "providers" / "upbit" / "bar_export.py")
    assert not {m for m in exp if m.startswith(("moneylab.backtest", "moneylab.research"))}
    io = mods(SRC / "backtest" / "bars_io.py")
    assert not {m for m in io if m.startswith(("moneylab.providers", "moneylab.research", "requests", "socket"))}
