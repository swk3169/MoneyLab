"""ECON-SCREEN-V06-01 (BT-5S): study permit, quality order, screening matrix, flags, recovery, output, measurement.

Offline. Inputs are SYNTHETIC: backtest.econ_screen.synthetic_bars, served as Upbit REST candle pages by an in-test
fake client and stored with pull_to_store into tmp_path (tests/fixtures/README.md). A "real" pull here is the same
synthetic data with provenance "real" inside tmp_path. Nothing here is market data or evidence."""

from __future__ import annotations

import bisect
import inspect
import json
import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import pytest

from moneylab.backtest import econ_screen as es
from moneylab.backtest.bars_io import load_bars
from moneylab.backtest import metrics as bt_metrics
from moneylab.backtest.code_state import classify_worktree
from moneylab.backtest.costs import PRECISION
from moneylab.backtest.data import BarSeries, DataIntegrityError, LookAheadError, provenance_for
from moneylab.backtest.portfolio import RunConfig, evaluation_boundary, require_within_boundary, simulate
from moneylab.backtest.settings import DEFAULT_SETTINGS_FILE, cost_model, load_cost_settings
from moneylab.cli import build_parser, main
from moneylab.domain.bars import utc_iso
from moneylab.providers.upbit.bar_export import BarExportError, econ_screen_pull_checks, export_bars
from moneylab.providers.upbit.candle_store import PULL_FILE, pull_to_store
from moneylab.providers.upbit.candles import CandlePage
from moneylab.storage.atomic import sha256_file

ROOT = Path(__file__).resolve().parents[1]
DAY, HOUR = timedelta(days=1), timedelta(hours=1)
NOW = datetime(2025, 1, 1, tzinfo=UTC)
DATA_START = datetime(2019, 1, 1, tzinfo=UTC)

# Pull-based end-to-end spec: data from 2019-01-01, request from 2018-12-01 (an empty page ends the pull),
# 2020 is a full calendar year of returns.
E2E_SPEC = replace(
    es.LOCKED_SPEC, requested_start=datetime(2018, 12, 1, tzinfo=UTC), requested_end=datetime(2021, 1, 1, tzinfo=UTC),
    rules=("M20", "R5"), fees_bps=(0, 25), capitals_krw=(Decimal(1_000_000), Decimal(10_000_000)), b1_draws=5,
    min_eval_days=365, min_round_trips=2)
# Full rule / scenario / fee / capital sets on a short period (144 combinations).
MATRIX_SPEC = replace(es.LOCKED_SPEC, requested_start=datetime(2020, 1, 1, tzinfo=UTC),
                      requested_end=datetime(2020, 9, 1, tzinfo=UTC), b1_draws=3)
CLEAN = classify_worktree("a" * 40, [])
DIRTY = classify_worktree("a" * 40, [(" M", "src/moneylab/cli.py")])


# --- synthetic candle pulls -----------------------------------------------------------------------------

def _row(b, interval: str) -> str:
    kst = (b.start_utc + timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%S")
    unit = ',"unit":60' if interval == "hour" else ""
    return (f'{{"market":"{b.market}","candle_date_time_utc":"{b.start_utc.strftime("%Y-%m-%dT%H:%M:%S")}",'
            f'"candle_date_time_kst":"{kst}","opening_price":{b.open},"high_price":{b.high},"low_price":{b.low},'
            f'"trade_price":{b.close},"timestamp":{b.last_tick_ms},"candle_acc_trade_price":{b.value_krw},'
            f'"candle_acc_trade_volume":{b.volume}{unit}}}')


class FakeCandleClient:
    """Serves synthetic bars as REST candle pages, newest first, strictly before `to`; empty when exhausted.
    after_end: also return the bar starting at the first `to` (an out-of-range row at requested_end)."""

    def __init__(self, series: dict[str, BarSeries], after_end: dict[str, object] | None = None):
        self.bars = {iv: list(s.bars) for iv, s in series.items()}
        self.starts = {iv: [b.start_utc for b in bs] for iv, bs in self.bars.items()}
        self.after_end = after_end or {}
        self.first = True

    def fetch_page(self, market: str, interval: str, to: datetime | None = None, count: int = 200) -> CandlePage:
        i = bisect.bisect_left(self.starts[interval], to)
        rows = [_row(b, interval) for b in reversed(self.bars[interval][max(0, i - count):i])]
        if self.first and interval in self.after_end:
            rows.insert(0, _row(self.after_end[interval], interval))
        self.first = False
        params = {"market": market, "count": count, "to": utc_iso(to)}
        return CandlePage(url="https://example.invalid/v1/candles", params=params, status_code=200, headers={},
                          body=("[" + ",".join(rows) + "]").encode("utf-8"), received_utc=NOW, attempts=1)


def make_pull(root: Path, series: dict[str, BarSeries], interval: str, spec: es.ScreenSpec, provenance: str = "fixture",
              after_end: dict[str, object] | None = None) -> Path:
    _, store = pull_to_store(FakeCandleClient(series, after_end), root, spec.market, interval, spec.requested_start,
                             spec.requested_end, provenance=provenance, origin="test:synthetic", utcnow=lambda: NOW)
    return store.dir


@pytest.fixture(scope="module")
def e2e_bars():
    d, h = es.synthetic_bars(DATA_START, E2E_SPEC.requested_end, seed=7, label="E2E", kind="fixture")
    return {"day": d, "hour": h}


@pytest.fixture(scope="module")
def pulls(tmp_path_factory, e2e_bars):
    root = tmp_path_factory.mktemp("pulls")
    return {iv: make_pull(root, e2e_bars, iv, E2E_SPEC) for iv in ("day", "hour")}


@pytest.fixture(scope="module")
def real_pulls(tmp_path_factory, e2e_bars):
    root = tmp_path_factory.mktemp("real_pulls")
    return {iv: make_pull(root, e2e_bars, iv, E2E_SPEC, provenance="real") for iv in ("day", "hour")}


def _checks(pulls: dict[str, Path], spec: es.ScreenSpec = E2E_SPEC) -> dict[str, dict]:
    return {iv: econ_screen_pull_checks(pulls[iv], spec.requested_end) for iv in ("day", "hour")}


def _real_permit(real_pulls: dict[str, Path], out_root: Path) -> es.EconScreenPermit:
    """A real-mode permit object for admission tests (issue_permit itself is tested separately)."""
    c = _checks(real_pulls)
    return es.EconScreenPermit("real", es.STUDY_ID, E2E_SPEC.sha256(), es.PREREGISTRATION_SHA256, "KRW-BTC",
                               utc_iso(E2E_SPEC.requested_start), utc_iso(E2E_SPEC.requested_end),
                               tuple((iv, c[iv]["pull_id"], c[iv]["pull_json_sha256"]) for iv in ("day", "hour")),
                               str(out_root.resolve()))


# --- T1 locked spec -------------------------------------------------------------------------------------

def test_t1_locked_spec_matches_the_preregistration():
    s = es.LOCKED_SPEC
    assert (s.market, s.requested_start, s.requested_end) == ("KRW-BTC", datetime(2017, 1, 1, tzinfo=UTC),
                                                              datetime(2024, 4, 1, tzinfo=UTC))
    assert s.last_signal_day == datetime(2024, 3, 29, tzinfo=UTC) and s.warmup_days == 120
    assert s.rules == ("M20", "M60", "M120", "R5") and s.scenarios == ("E0", "E1", "E2")
    assert s.fees_bps == (0, 5, 15, 25) and s.capitals_krw == (Decimal(1_000_000), Decimal(5_000_000),
                                                                 Decimal(10_000_000))
    assert (s.base_scenario, s.base_fee_bps, s.base_capital_krw) == ("E0", 25, Decimal(10_000_000))
    assert (s.b1_draws, s.seed) == (9_999, 20261119)
    assert (s.q2_max, s.q3_max, s.q7_max) == (Fraction(1, 200), Fraction(1, 100), Fraction(1, 200))
    assert (s.q4_day_run, s.q4_hour_run, s.q4_max_events) == (3, 7, 3)
    assert (s.min_eval_days, s.min_round_trips, s.min_positive_year_ratio) == (1825, 20, Fraction(3, 5))
    raw = (ROOT / es.PREREGISTRATION_PATH).read_bytes()
    assert es.lf_normalized_sha256(raw) == es.PREREGISTRATION_SHA256
    text = raw.decode("utf-8")
    for phrase in ("requested_start = 2017-01-01T00:00:00Z", "requested_end = 2024-04-01T00:00:00Z(배타)",
                   "마지막 신호일 E = 2024-03-29", "{0, 5, 15, 25} bp", "C ∈ {1,000,000, 5,000,000, 10,000,000}",
                   "반복 9,999회. seed = 20261119", "Q2 ≤ 1/200, Q3 ≤ 1/100", "1시간봉 연속 누락 7 bucket 이상",
                   "합이 3 이상이면 INVALID", "비교 가능일의 1/200", "5 × 365일", "20회 이상", "≥ 0.60",
                   "label = [\"B1\", 전략, 시나리오]"):
        assert phrase in text, phrase


# --- T2 / T3b general refusal unchanged -----------------------------------------------------------------

def test_t2_general_paths_still_refuse_real(tmp_path, real_pulls, e2e_bars):
    d = BarSeries.build(e2e_bars["day"].bars, provenance_for(e2e_bars["day"].bars, "real", "t"))
    h = BarSeries.build(e2e_bars["hour"].bars, provenance_for(e2e_bars["hour"].bars, "real", "t"))
    cfg = RunConfig("M20", DATA_START + 120 * DAY, DATA_START + 200 * DAY, Decimal(1_000_000),
                    cost_model(load_cost_settings()[0], 25, "E0", Decimal(1_000_000))[0])
    with pytest.raises(DataIntegrityError, match=r"^BT-1 accepts only \('fixture', 'synthetic'\) bars "
                                                 r"\(real data is refused until BT-5\), got \['real'\]$"):
        simulate(d, h, cfg)
    with pytest.raises(BarExportError, match="^provenance 'real' is not allowed"):
        export_bars(real_pulls["day"], tmp_path / "bars")
    with pytest.raises(BarExportError, match="^real pulls are not exported before BT-5$"):
        export_bars(real_pulls["day"], tmp_path / "bars", allowed_provenance=("real",),
                    real_permit=_real_permit(real_pulls, tmp_path))
    # a permitted export, then the general loader still refuses it without the permit
    out = tmp_path / es.REAL_ROOT_NAME
    permit = _real_permit(real_pulls, out)
    exp = export_bars(real_pulls["day"], out / "prep" / "bars", real_permit=permit)
    with pytest.raises(DataIntegrityError, match="provenance 'real' is refused before BT-5$"):
        load_bars(exp.dir)
    with pytest.raises(DataIntegrityError, match="provenance 'real' is refused before BT-5$"):
        load_bars(exp.dir, real_permit=permit)  # no bars hash in the permit yet
    full = permit.with_bars(exp.bars_sha256, "0" * 64)
    assert load_bars(exp.dir, real_permit=full).provenance.kind == "real"


def test_t3b_fixture_permit_and_other_hashes_never_admit_real(tmp_path, real_pulls, e2e_bars):
    out = tmp_path / es.REAL_ROOT_NAME
    permit = _real_permit(real_pulls, out)
    fixture_permit = replace(permit, mode="fixture")
    with pytest.raises(BarExportError, match="is not allowed"):
        export_bars(real_pulls["hour"], out / "p" / "bars", real_permit=fixture_permit)
    with pytest.raises(BarExportError, match="is not allowed"):
        export_bars(real_pulls["hour"], out / "p" / "elsewhere", real_permit=permit)  # wrong output directory
    other = replace(permit, pulls=(("day", "x", "0" * 64), ("hour", "y", "0" * 64)))
    with pytest.raises(BarExportError, match="is not allowed"):
        export_bars(real_pulls["hour"], out / "p" / "bars", real_permit=other)
    d = BarSeries.build(e2e_bars["day"].bars, provenance_for(e2e_bars["day"].bars, "real", "t"))
    h = BarSeries.build(e2e_bars["hour"].bars, provenance_for(e2e_bars["hour"].bars, "real", "t"))
    good = permit.with_bars(d.provenance.bars_sha256, h.provenance.bars_sha256)
    assert good.admits(d, h)
    assert not replace(good, mode="fixture").admits(d, h)
    assert not permit.with_bars("0" * 64, h.provenance.bars_sha256).admits(d, h)
    cfg = RunConfig("M20", DATA_START + 120 * DAY, DATA_START + 200 * DAY, Decimal(1_000_000),
                    cost_model(load_cost_settings()[0], 25, "E0", Decimal(1_000_000))[0])
    with pytest.raises(DataIntegrityError, match="^BT-1 accepts only"):
        simulate(d, h, cfg, real_permit=replace(good, mode="fixture"))
    assert simulate(d, h, cfg, real_permit=good).ledger is not None
    # the synthetic measurement takes no file input
    params = set(inspect.signature(es.measure).parameters)
    assert params == {"settings_file", "spec", "draws", "repeats", "emit", "clock"}
    with pytest.raises(SystemExit):
        build_parser().parse_args(["econ-screen-measure", "--day-pull", "x"])


# --- T3 permit refusals and locks -----------------------------------------------------------------------

def _issue(mode, spec, checks, expected, out_root, *, file_sha=es.PREREGISTRATION_SHA256,
           blob_sha=es.PREREGISTRATION_SHA256, code_state=CLEAN):
    return es.issue_permit(mode, spec, prereg_file_sha256=file_sha, prereg_blob_sha256=blob_sha,
                           code_state=code_state, checks=checks, expected_pull_sha256=expected, out_root=out_root)


def test_t3_permit_refusals(tmp_path, pulls, real_pulls):
    fx, rl = _checks(pulls), _checks(real_pulls)
    fx_exp = {iv: fx[iv]["pull_json_sha256"] for iv in fx}
    fx_root = tmp_path / "root-fixture"
    assert _issue("fixture", E2E_SPEC, fx, fx_exp, fx_root).mode == "fixture"
    cases = [
        (dict(file_sha="0" * 64), "preregistration file"),
        (dict(blob_sha=None), "HEAD blob"),
    ]
    for kw, msg in cases:
        with pytest.raises(es.PermitError, match=msg):
            _issue("fixture", E2E_SPEC, fx, fx_exp, fx_root, **kw)
    with pytest.raises(es.PermitError, match="must end with"):
        _issue("fixture", E2E_SPEC, fx, fx_exp, tmp_path / "root")
    with pytest.raises(es.PermitError, match="differs from the approved value"):
        _issue("fixture", E2E_SPEC, fx, {"day": "0" * 64, "hour": fx_exp["hour"]}, fx_root)
    with pytest.raises(es.PermitError, match="no approved pull.json"):
        _issue("fixture", E2E_SPEC, fx, {"day": fx_exp["day"]}, fx_root)
    with pytest.raises(es.PermitError, match="does not match mode"):
        _issue("fixture", E2E_SPEC, rl, {iv: rl[iv]["pull_json_sha256"] for iv in rl}, fx_root)
    swapped = {"day": fx["hour"], "hour": fx["day"]}
    with pytest.raises(es.PermitError, match="pull is a"):
        _issue("fixture", E2E_SPEC, swapped, {"day": fx["hour"]["pull_json_sha256"],
                                               "hour": fx["day"]["pull_json_sha256"]}, fx_root)
    with pytest.raises(es.PermitError, match="market"):
        _issue("fixture", replace(E2E_SPEC, market="KRW-ETH"), fx, fx_exp, fx_root)
    with pytest.raises(es.PermitError, match="range differs"):
        _issue("fixture", replace(E2E_SPEC, requested_end=datetime(2021, 2, 1, tzinfo=UTC)), fx, fx_exp, fx_root)
    rl_exp = {iv: rl[iv]["pull_json_sha256"] for iv in rl}
    real_root = tmp_path / es.REAL_ROOT_NAME
    with pytest.raises(es.PermitError, match="locked spec"):
        _issue("real", E2E_SPEC, rl, rl_exp, real_root)
    with pytest.raises(es.PermitError, match="clean code"):
        _issue("real", es.LOCKED_SPEC, rl, rl_exp, real_root, code_state=DIRTY)
    with pytest.raises(es.PermitError, match="must be named"):
        _issue("real", es.LOCKED_SPEC, rl, rl_exp, tmp_path / "other")
    with pytest.raises(es.PermitError, match="range differs"):  # synthetic pulls are not the locked range
        _issue("real", es.LOCKED_SPEC, rl, rl_exp, real_root)


def test_t3_spec_override_and_run_lock(tmp_path, capsys):
    with pytest.raises(es.EconScreenError):
        es.resolve_spec("real", E2E_SPEC, None)
    with pytest.raises(es.EconScreenError):
        es.resolve_spec("real", None, 9)
    assert es.resolve_spec("real", None, None) is es.LOCKED_SPEC
    assert es.resolve_spec("fixture", E2E_SPEC, 3).b1_draws == 3
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(E2E_SPEC.to_dict()), encoding="utf-8")
    out = tmp_path / es.REAL_ROOT_NAME
    rc = main(["econ-screen-run", "--prepare", str(tmp_path), "--expect-prepare-manifest-sha256", "0" * 64,
               "--spec-json", str(spec_file), "--out", str(out)])
    assert rc == 1 and not out.exists()
    rc = main(["econ-screen-run", "--prepare", str(tmp_path), "--expect-prepare-manifest-sha256", "0" * 64,
               "--b1-draws", "9999", "--out", str(out)])
    assert rc == 1 and not out.exists()
    assert "fixture-only" in _flat(capsys.readouterr().out)
    root = tmp_path / "lock"
    (root / "prepare-x").mkdir(parents=True)
    (root / ".tmp-prepare-y").mkdir()
    es.check_run_lock(root)  # prepare output does not lock a run
    (root / ".tmp-run-z").mkdir()
    with pytest.raises(es.EconScreenError, match="already attempted"):
        es.check_run_lock(root)
    root2 = tmp_path / "lock2"
    (root2 / "run-z").mkdir(parents=True)
    with pytest.raises(es.EconScreenError, match="already attempted"):
        es.check_run_lock(root2)
    assert ES_SPEC_ROUNDTRIP(E2E_SPEC)


def ES_SPEC_ROUNDTRIP(spec: es.ScreenSpec) -> bool:
    return es.ScreenSpec.from_dict(json.loads(json.dumps(spec.to_dict()))) == spec


# --- T4 order and quality -------------------------------------------------------------------------------

def _good_check(iv: str) -> dict:
    return {"verify_ok": True, "status": "complete", "duplicates_conflicting": 0, "invalid": 0,
            "duplicates_identical": 0, "reached_earliest": True, "first_start": "2019-01-01T00:00:00Z",
            "excluded_out_of_range": 0, "at_or_after_requested_end": 0}


def test_t4_pull_stage_order():
    good = {iv: _good_check(iv) for iv in ("day", "hour")}
    assert es.pull_stage(good)["passed"]
    bad_q1 = {**good, "day": {**good["day"], "verify_ok": False}}
    st = es.pull_stage(bad_q1)
    assert st["Q1"]["day"] == es.INVALID and st["Q6"]["day"]["status"] == es.NOT_EVALUATED
    assert st["collection"]["status"] == es.NOT_EVALUATED and not st["passed"]
    one_dup = {**good, "hour": {**good["hour"], "duplicates_conflicting": 1}}
    st = es.pull_stage(one_dup)
    assert st["Q6"]["hour"]["status"] == es.INVALID and not st["passed"]
    st = es.pull_stage({**good, "hour": {**good["hour"], "invalid": 1}})
    assert st["Q6"]["hour"]["status"] == es.INVALID
    st = es.pull_stage({**good, "day": {**good["day"], "reached_earliest": False}})
    assert st["collection"]["status"] == "COLLECTION_RANGE_UNCONFIRMED" and not st["passed"]
    st = es.pull_stage({**good, "hour": {**good["hour"], "first_start": "2019-01-02T00:00:00Z"}})
    assert st["collection"]["conditions"]["first_dates_equal"] is False and not st["passed"]
    st = es.pull_stage({**good, "day": {**good["day"], "at_or_after_requested_end": 1}})
    assert st["exposure_record_candidate"] and st["passed"]
    assert es.quality_summary(st, None)["required_all_pass"] is False


def _drop(series: BarSeries, starts: set[datetime], kind: str = "fixture") -> BarSeries:
    bars = [b for b in series.bars if b.start_utc not in starts]
    return BarSeries.build(bars, provenance_for(bars, kind, "t"))


def test_t4_q2_q3_thresholds_are_exact(e2e_bars):
    d, h = e2e_bars["day"], e2e_bars["hour"]
    n_day = (E2E_SPEC.requested_end - DATA_START) // DAY
    gone = {DATA_START + 300 * DAY, DATA_START + 500 * DAY}
    d2 = _drop(d, gone)
    assert es.bar_quality(d2, h, replace(E2E_SPEC, q2_max=Fraction(2, n_day)))["Q2"]["status"] == es.PASS
    assert es.bar_quality(d2, h, replace(E2E_SPEC, q2_max=Fraction(1, n_day)))["Q2"]["status"] == es.INVALID
    n_hour = n_day * 24
    h2 = _drop(h, {DATA_START + 10 * HOUR, DATA_START + 1000 * HOUR, DATA_START + 2000 * HOUR})
    assert es.bar_quality(d, h2, replace(E2E_SPEC, q3_max=Fraction(3, n_hour)))["Q3"]["status"] == es.PASS
    q = es.bar_quality(d, h2, replace(E2E_SPEC, q3_max=Fraction(2, n_hour)))
    assert q["Q3"]["status"] == es.INVALID and q["Q3"]["missing"] == 3


def test_t4_q4_gap_events_overlapping_g(e2e_bars):
    d, h = e2e_bars["day"], e2e_bars["hour"]
    g0 = E2E_SPEC.g_start(DATA_START)

    def run(start: datetime, n: int) -> set[datetime]:
        return {start + i * DAY for i in range(n)}

    warmup_gap = run(DATA_START + 10 * DAY, 5)  # before G: not an event
    two = run(g0 + 30 * DAY, 3) | run(g0 + 100 * DAY, 4)
    q = es.bar_quality(_drop(d, warmup_gap | two), h, E2E_SPEC)
    assert len(q["Q4"]["events"]) == 2 and q["Q4"]["status"] == es.PASS
    straddle = run(g0 - 2 * DAY, 3)  # overlaps G start: counts, length not cut to G
    q = es.bar_quality(_drop(d, two | straddle), h, E2E_SPEC)
    assert q["Q4"]["status"] == es.INVALID and {"interval": "day", "first_missing": utc_iso(g0 - 2 * DAY),
                                                 "missing": 3} in q["Q4"]["events"]
    hour_run = {g0 + 50 * DAY + i * HOUR for i in range(7)}
    short_run = {g0 + 60 * DAY + i * HOUR for i in range(6)}
    q = es.bar_quality(_drop(d, two), _drop(h, hour_run | short_run), E2E_SPEC)
    assert q["Q4"]["status"] == es.INVALID and len(q["Q4"]["events"]) == 3


def test_t4_q7_exact_and_not_evaluated(e2e_bars):
    d, h = e2e_bars["day"], e2e_bars["hour"]
    assert es.bar_quality(d, h, E2E_SPEC)["Q7"]["status"] == es.PASS
    bars = list(d.bars)
    bars[400] = replace(bars[400], volume=bars[400].volume + Decimal("0.00000001"))
    d2 = BarSeries.build(bars, provenance_for(bars, "fixture", "t"))
    q = es.bar_quality(d2, h, E2E_SPEC)
    assert q["Q7"]["mismatched_days"] == 1 and q["Q7"]["status"] == es.PASS
    q = es.bar_quality(d2, h, replace(E2E_SPEC, q7_max=Fraction(0)))
    assert q["Q7"]["status"] == es.INVALID
    only_one = _drop(h, {b.start_utc for b in h.bars if b.start_utc.hour == 5})
    q = es.bar_quality(d, only_one, E2E_SPEC)
    assert q["Q7"]["status"] == es.NOT_EVALUATED and q["Q7"]["comparable_days"] == 0
    assert es.quality_summary(es.pull_stage({iv: _good_check(iv) for iv in ("day", "hour")}),
                              q)["required_all_pass"] is False


# --- T5 boundaries --------------------------------------------------------------------------------------

def test_t5_boundaries(e2e_bars, pulls, tmp_path):
    d, h = e2e_bars["day"], e2e_bars["hour"]
    q = es.bar_quality(d, h, E2E_SPEC)
    f = DATA_START + 120 * DAY
    assert (q["d0"], q["first_signal_day"], q["g_start"], q["g_end"]) == (
        utc_iso(DATA_START), utc_iso(f), utc_iso(f + 2 * DAY), utc_iso(E2E_SPEC.requested_end))
    assert q["last_signal_day"] == utc_iso(E2E_SPEC.requested_end - 3 * DAY)
    settings = load_cost_settings()[0]
    for scen in ("E0", "E1", "E2"):
        costs, ok = cost_model(settings, 25, scen, Decimal(10_000_000))
        cfg = RunConfig("M20", f, E2E_SPEC.last_signal_day, Decimal(10_000_000), costs, scenario=scen,
                        fill_substitution="prereg_6_3", capacity_verified=ok)
        res = simulate(d, h, cfg)
        assert res.signals[0].day == f and res.signals[0].value is not None  # warmup gives a full window at F
        b = evaluation_boundary(cfg)
        c = es.describe(res, E2E_SPEC, "M20", scen, 25, Decimal(10_000_000))
        assert (c["first_ref"], c["last_ref"]) == (utc_iso(b.first_ref), utc_iso(b.valuation_end))
        assert b.valuation_end <= E2E_SPEC.requested_end
    early = RunConfig("M120", DATA_START + 100 * DAY, DATA_START + 200 * DAY, Decimal(1_000_000), costs)
    assert simulate(d, h, early).signals[0].reason == "insufficient_history"
    with pytest.raises(LookAheadError):
        require_within_boundary(E2E_SPEC.requested_end + HOUR, E2E_SPEC.requested_end, "bar")
    c = _checks(pulls)
    assert c["day"]["excluded_out_of_range"] == 0 and c["day"]["at_or_after_requested_end"] == 0
    extra = {"day": e2e_bars["day"].bars[-1]}
    shifted = replace(extra["day"], start_utc=E2E_SPEC.requested_end)
    p = make_pull(tmp_path, e2e_bars, "day", E2E_SPEC, after_end={"day": shifted})
    chk = econ_screen_pull_checks(p, E2E_SPEC.requested_end)
    assert chk["excluded_out_of_range"] == 1 and chk["at_or_after_requested_end"] == 1
    assert chk["verify_ok"]


# --- T6 capital consistency -----------------------------------------------------------------------------

def test_t6_capital_consistency(e2e_bars):
    d, h = e2e_bars["day"], e2e_bars["hour"]
    settings = load_cost_settings()[0]
    f = DATA_START + 120 * DAY
    for capital in (Decimal(1_000_000), Decimal(5_000_000), Decimal(10_000_000)):
        costs, ok = cost_model(settings, 25, "E0", capital, fee_basis="inclusive")
        cfg = RunConfig("M20", f, E2E_SPEC.last_signal_day, capital, costs, fill_substitution="prereg_6_3")
        res = simulate(d, h, cfg)
        ref = simulate(d, h, replace(cfg, initial_cash=Decimal(1_000_000)))
        buy = res.ledger.trades[0]
        with localcontext() as ctx:
            ctx.prec = PRECISION
            assert ok and costs.impact_bps == Decimal(1) * (capital / Decimal(1_000_000)).sqrt()
            fee = buy.cash_before * (costs.buy_fee_bps / 10_000)
            exchanged = buy.cash_before - fee
            assert buy.cash_before == capital and buy.fee == fee
            assert buy.slippage_cost == exchanged * (costs.slippage_bps / 10_000)
            assert buy.impact_cost == exchanged * (costs.impact_bps / 10_000)
        r, r1 = bt_metrics.daily_log_returns(res.ledger), bt_metrics.daily_log_returns(ref.ledger)
        assert max(abs(a - b) for a, b in zip(r, r1)) <= 1e-12 and len(r) == len(r1)
        c = es.describe(res, replace(E2E_SPEC, b1_draws=2), "M20", "E0", 25, capital)
        assert c["capital_krw"] == str(capital) and c["break_even_fee"]["capital_krw"] == str(capital)
        assert c["break_even_fee"]["capital_krw_module_constant"] == "1000000"
        assert c["break_even_fee"]["impact_bps"] == str(costs.impact_bps)


# --- T7 matrix ------------------------------------------------------------------------------------------

def test_t7_matrix_has_144_combinations_with_shared_b1_placements():
    d, h = es.synthetic_bars(MATRIX_SPEC.requested_start, MATRIX_SPEC.requested_end, seed=3, label="T7",
                             kind="fixture")
    combos = es.run_matrix(d, h, MATRIX_SPEC, DEFAULT_SETTINGS_FILE)
    keys = {(c["rule"], c["scenario"], c["fee_bps"], c["capital_krw"]) for c in combos}
    assert len(combos) == 144 and len(keys) == 144
    for rule in MATRIX_SPEC.rules:
        for scen in MATRIX_SPEC.scenarios:
            group = [c for c in combos if (c["rule"], c["scenario"]) == (rule, scen)]
            assert len(group) == 12
            assert len({json.dumps(c["seed"]["labels"]) for c in group}) == 1
            assert group[0]["seed"]["labels"] == ["B1", rule, scen]
            compared = [c for c in group if c["b1"]["status"] == "compared"]
            assert len({json.dumps(c["b1"]["structure"], sort_keys=True) for c in compared}) <= 1
    assert all("verdict" not in c and "p_value" not in json.dumps(c["b1"]) for c in combos)


# --- T8 flags -------------------------------------------------------------------------------------------

def _combo(rule, scen, *, mean=0.001, b1=0.0005, rts=25, ratio=(3, 5), aligned=True, fee=25, cap="10000000"):
    yr = {"value": None if ratio is None else ratio[0] / ratio[1], "positive_years": 0 if ratio is None else ratio[0],
          "years": 0 if ratio is None else ratio[1]}
    if ratio is None:
        yr["reason"] = "no_full_years"
    return {"rule": rule, "scenario": scen, "fee_bps": fee, "capital_krw": cap,
            "net_mean_log_return": {"value": mean}, "round_trips": {"including_virtual_exit": rts},
            "b1": ({"status": "compared", "strategy_minus_mean_b1": {"value": mean - b1}} if aligned
                   else {"status": "not_aligned"}),
            "yearly": {"positive_year_ratio_full_years": yr}}


def test_t8_flags():
    spec = replace(es.LOCKED_SPEC, rules=("M20",))
    base = [_combo("M20", "E0"), _combo("M20", "E1"), _combo("M20", "E2")]
    assert es.screen_flags(base, spec, True)["M20"]["flag"] == es.FLAG_PASS
    assert es.screen_flags(base, spec, False)["M20"] == {"flag": es.FLAG_NOT_EVALUABLE,
                                                          "reason": "evaluation_period_below_minimum"}
    low = [_combo("M20", "E0", rts=19)] + base[1:]
    assert es.screen_flags(low, spec, True)["M20"]["reason"] == "round_trips_below_minimum"
    edge = [_combo("M20", "E0", rts=20)] + base[1:]
    assert es.screen_flags(edge, spec, True)["M20"]["flag"] == es.FLAG_PASS
    na = [_combo("M20", "E0", aligned=False)] + base[1:]
    assert es.screen_flags(na, spec, True)["M20"]["reason"] == "b1_not_aligned"
    for bad in ([_combo("M20", "E0", mean=-0.001)] + base[1:], [_combo("M20", "E0", b1=0.002)] + base[1:],
                [base[0], _combo("M20", "E1", mean=-1e-9), base[2]], [base[0], base[1], _combo("M20", "E2", mean=0.0)],
                [_combo("M20", "E0", ratio=(2, 4))] + base[1:]):
        assert es.screen_flags(bad, spec, True)["M20"]["flag"] == es.FLAG_NOT_MET
    with pytest.raises(es.ScreenComputationError):
        es.screen_flags([_combo("M20", "E0", ratio=None)] + base[1:], spec, True)
    # computable-ratio failure only matters for an evaluable rule
    assert es.screen_flags([_combo("M20", "E0", ratio=None, rts=1)] + base[1:], spec, True)["M20"]["flag"] == \
        es.FLAG_NOT_EVALUABLE


# --- T9 recovery ----------------------------------------------------------------------------------------

def test_t9_recovery_days():
    t = [datetime(2020, 1, 1, 1, tzinfo=UTC) + i * DAY for i in range(8)]
    r = [0.5, -0.25, -0.25, 0.125, 0.375, 0.0625, -0.0625]  # binary-exact levels 0.5, 0.25, 0, 0.125, 0.5
    out = es.recovery_days(r, t)
    assert out["value"] == 2 and out["trough"] == utc_iso(t[3]) and out["peak"] == utc_iso(t[1])
    assert out["recovered"] == utc_iso(t[5])
    assert es.recovery_days([0.1, -0.2, 0.05], t[:4])["reason"] == "not_recovered"
    assert es.recovery_days([0.1, 0.0, 0.2], t[:4])["reason"] == "no_drawdown"
    tie = es.recovery_days([-0.1, 0.1, -0.1, 0.1], t[:5])
    assert tie["trough"] == utc_iso(t[1]) and tie["value"] == 1 and tie["tie_rule"] == "first trough"


# --- T10 output and CLI end to end ----------------------------------------------------------------------

def test_t10_output_rename_hashes_and_failure_keeps_files(tmp_path, monkeypatch):
    root = tmp_path / "out-fixture"
    now = datetime(2026, 1, 1, tzinfo=UTC)
    tmp = es.begin_output(root, "prepare", now)
    with pytest.raises(FileExistsError):
        es.begin_output(root, "prepare", now)
    final, _ = es.finish_output(tmp, "prepare", {"a.json": b"{}\n", "b.json": b"[]\n"})
    assert final.name.startswith("prepare-") and not tmp.exists()
    assert set(es.verify_output(final)) == {"a.json", "b.json"}
    (final / "a.json").write_bytes(b"{1}\n")
    with pytest.raises(es.EconScreenError, match="does not match"):
        es.verify_output(final)
    tmp2 = es.begin_output(root, "run", now)
    calls = []
    real_write = es.atomic_write_bytes

    def flaky(path, data):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("disk full (test)")
        return real_write(path, data)

    monkeypatch.setattr(es, "atomic_write_bytes", flaky)
    with pytest.raises(OSError):
        es.finish_output(tmp2, "run", {"x.json": b"1\n", "y.json": b"2\n"})
    assert tmp2.exists() and (tmp2 / "x.json").read_bytes() == b"1\n" and not (root / tmp2.name[5:]).exists()


def _flat(text: str) -> str:
    """Console output with the terminal line wrapping undone (rich wraps at the console width)."""
    return " ".join(text.split())


def _write_spec(tmp_path: Path, spec: es.ScreenSpec) -> Path:
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec.to_dict()), encoding="utf-8")
    return p


def test_t10_cli_fixture_end_to_end(tmp_path, pulls, capsys):
    spec_file = _write_spec(tmp_path, E2E_SPEC)
    out = tmp_path / "screen-fixture"
    shas = {iv: sha256_file(pulls[iv] / PULL_FILE) for iv in pulls}
    rc = main(["econ-screen-prepare", "--source", "fixture", "--spec-json", str(spec_file), "--out", str(out),
               "--day-pull", str(pulls["day"]), "--hour-pull", str(pulls["hour"]),
               "--expect-day-pull-sha256", shas["day"], "--expect-hour-pull-sha256", shas["hour"]])
    assert rc == 0, capsys.readouterr().out
    prep = next(out.glob("prepare-*"))
    es.verify_output(prep)
    quality = json.loads((prep / "quality.json").read_text(encoding="utf-8"))
    assert quality["summary"] == {"bundle_status": "INCOMPLETE", "required_all_pass": True,
                                  "note": "VALID is never reported by this study"}
    assert quality["bar_quality"]["report_only_not_evaluated"] == {k: "NOT_EVALUATED" for k in es.REPORT_ONLY_CHECKS}
    man = sha256_file(prep / "manifest.json")
    capsys.readouterr()
    rc = main(["econ-screen-run", "--source", "fixture", "--spec-json", str(spec_file), "--b1-draws", "5",
               "--out", str(out), "--prepare", str(prep), "--expect-prepare-manifest-sha256", man])
    printed = capsys.readouterr().out
    assert rc == 0, printed
    run = next(out.glob("run-*"))
    es.verify_output(run)
    screen = json.loads((run / "screen.json").read_text(encoding="utf-8"))
    assert screen["combinations_count"] == 2 * 3 * 2 * 2 == len(screen["combinations"])
    assert set(screen["flags"]) == {"M20", "R5"} and screen["evidence"] == "SYNTHETIC / NOT_EVIDENCE"
    assert screen["p_values"] == "not computed" and screen["verdict"] == "not computed"
    squeezed = "".join(printed.split())  # the console wraps lines; no whitespace can hide a word
    for forbidden in ("net_mean", "SCREEN_FLAG", "mdd", "break_even", "flag"):
        assert forbidden not in squeezed
    # a second run attempt in the same root is refused; the prepare directory did not lock the first one
    rc = main(["econ-screen-run", "--source", "fixture", "--spec-json", str(spec_file), "--b1-draws", "5",
               "--out", str(out), "--prepare", str(prep), "--expect-prepare-manifest-sha256", man])
    assert rc == 1 and len(list(out.glob("run-*"))) == 1 and not list(out.glob(".tmp-run-*"))


def test_t4_cli_stops_before_any_return(tmp_path, pulls, capsys, monkeypatch):
    spec_file = _write_spec(tmp_path, replace(E2E_SPEC, q7_max=Fraction(0), min_eval_days=365))
    out = tmp_path / "stop-fixture"
    shas = {iv: sha256_file(pulls[iv] / PULL_FILE) for iv in pulls}
    rc = main(["econ-screen-prepare", "--source", "fixture", "--spec-json", str(spec_file), "--out", str(out),
               "--day-pull", str(pulls["day"]), "--hour-pull", str(pulls["hour"]),
               "--expect-day-pull-sha256", "0" * 64, "--expect-hour-pull-sha256", shas["hour"]])
    assert rc == 1 and "differs from the approved value" in _flat(capsys.readouterr().out)
    kept = list(out.glob(".tmp-prepare-*"))
    assert len(kept) == 1 and not (kept[0] / "bars-fixture").exists()  # no bar conversion, partial output kept
    # a quality failure (Q2 forced INVALID) ends the run before run_matrix
    spec_file = _write_spec(tmp_path, replace(E2E_SPEC, q2_max=Fraction(-1)))
    rc = main(["econ-screen-prepare", "--source", "fixture", "--spec-json", str(spec_file), "--out", str(out),
               "--day-pull", str(pulls["day"]), "--hour-pull", str(pulls["hour"]),
               "--expect-day-pull-sha256", shas["day"], "--expect-hour-pull-sha256", shas["hour"]])
    assert rc == 1
    prep = next(out.glob("prepare-*"))
    assert json.loads((prep / "quality.json").read_text(encoding="utf-8"))["summary"]["bundle_status"] == "INVALID"

    def boom(*a, **k):
        raise AssertionError("run_matrix must not be called")

    monkeypatch.setattr(es, "run_matrix", boom)
    capsys.readouterr()
    rc = main(["econ-screen-run", "--source", "fixture", "--spec-json", str(spec_file), "--b1-draws", "2",
               "--out", str(out), "--prepare", str(prep),
               "--expect-prepare-manifest-sha256", sha256_file(prep / "manifest.json")])
    assert rc == 1 and "prepare quality did not pass" in _flat(capsys.readouterr().out)
    assert len(list(out.glob(".tmp-run-*"))) == 1 and not list(out.glob("run-*"))


# --- T11 measurement ------------------------------------------------------------------------------------

def test_t11_measure_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = replace(es.LOCKED_SPEC, requested_start=datetime(2020, 1, 1, tzinfo=UTC),
                   requested_end=datetime(2020, 8, 1, tzinfo=UTC))
    lines: list[str] = []
    out = es.measure(DEFAULT_SETTINGS_FILE, spec=spec, draws=(2, 3), repeats=1, emit=lines.append)
    assert list(tmp_path.iterdir()) == []
    assert len(out["rounds"]) == 1 and set(out["rounds"][0]["simulate_s"]) == {
        "M20/E0", "M60/E0", "M120/E0", "R5/E0", "M20/E1", "M20/E2"}
    assert out["python_heap_peak_bytes"] > 0 and math.isfinite(out["extrapolation"]["t_est_s"])
    assert "not approved" in lines[-1]
