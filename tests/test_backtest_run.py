"""BT-2b-2 settings, run directories and verify_run (SYNTHETIC / NOT_EVIDENCE).

Inputs are fixture candle pulls exported in tmp_path (tests/test_bar_export.fixture_pull); nothing is
fetched and nothing is written outside tmp_path. Prices are linear: pipeline checks only."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from test_bar_export import fixture_pull, tree_hashes

from moneylab.backtest import run as runmod
from moneylab.backtest.code_state import classify_worktree
from moneylab.backtest.costs import CostModel
from moneylab.backtest.data import DataIntegrityError
from moneylab.backtest.execution import SCENARIOS, prereg_costs
from moneylab.backtest.portfolio import RunConfig
from moneylab.backtest.run import INITIAL_CASH_KRW, RUN_FILES, RunError, run_backtest, verify_run
from moneylab.backtest.settings import DEFAULT_SETTINGS_FILE, SettingsError, cost_model, load_cost_settings
from moneylab.domain.bars import NOT_EVIDENCE
from moneylab.providers.upbit.bar_export import export_bars
from moneylab.storage.atomic import sha256_file

CODE = classify_worktree("a" * 40, [])
NOW = datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def bars(tmp_path_factory):
    root = tmp_path_factory.mktemp("bt")
    pulls = {iv: fixture_pull(root / "pulls", iv) for iv in ("day", "hour")}
    out = root / "bars-fixture"
    return {iv: export_bars(p, out).dir for iv, p in pulls.items()}


def config(settings_file: Path = DEFAULT_SETTINGS_FILE, *, fee: int = 25, scenario: str = "E0",
           costs: CostModel | None = None) -> RunConfig:
    s, _ = load_cost_settings(settings_file)
    model, verified = cost_model(s, fee, scenario, INITIAL_CASH_KRW)
    first = datetime(2025, 6, 1, tzinfo=UTC)
    return RunConfig("sma20", first + timedelta(days=25), first + timedelta(days=180), INITIAL_CASH_KRW,
                     costs or model, scenario=scenario, capacity_verified=verified)


def make_run(bars, out_root: Path, *, now: datetime = NOW, settings_file: Path = DEFAULT_SETTINGS_FILE,
             code=CODE, **kw):
    return run_backtest(bars["day"], bars["hour"], config(settings_file, **kw), out_root, code_state=code,
                        settings_file=settings_file, now=now)


# --- settings ---------------------------------------------------------------------------------------------

def test_default_settings_equal_the_code_constants():
    s, h = load_cost_settings()
    assert s.fee_basis == "inclusive" and s.fee_status == "FEE_UNCONFIRMED" and s.impact_status == "ASSUMED"
    assert s.fee_scenarios_bps == (0, 5, 15, 25)
    for scen in SCENARIOS:
        for fee in (0, 5, 15, 25):
            assert cost_model(s, fee, scen, INITIAL_CASH_KRW) == prereg_costs(fee, scen, INITIAL_CASH_KRW)
    assert h["normalization"].startswith("CRLF and lone CR replaced by LF")
    assert set(h) == {"path", "file_name", "normalization", "sha256_lf_normalized", "sha256_raw_bytes"}


def test_settings_hash_lf_normalized_vs_raw(tmp_path):
    lf = DEFAULT_SETTINGS_FILE.read_bytes().replace(b"\r\n", b"\n")
    a, b = tmp_path / "lf.toml", tmp_path / "crlf.toml"
    a.write_bytes(lf)
    b.write_bytes(lf.replace(b"\n", b"\r\n"))
    _, ha = load_cost_settings(a)
    _, hb = load_cost_settings(b)
    assert ha["sha256_lf_normalized"] == hb["sha256_lf_normalized"]
    assert ha["sha256_raw_bytes"] != hb["sha256_raw_bytes"]


@pytest.mark.parametrize("old,new,match", [
    ('E0 = 5', 'E0 = 6', "differs from the scenario table"),
    ('status = "FEE_UNCONFIRMED"', 'status = "CONFIRMED"', "FEE_UNCONFIRMED"),
    ('status = "ASSUMED"', 'status = "VERIFIED"', "ASSUMED"),
    ('scenarios_bps = [0, 5, 15, 25]', 'scenarios_bps = [0, 10]', "subset"),
    ('ref_bps = "1"', 'ref_bps = 1.0', "integer or a decimal string"),
    ('basis = "inclusive"', 'basis = "maker"', "basis"),
])
def test_bad_settings_are_refused(tmp_path, old, new, match):
    text = DEFAULT_SETTINGS_FILE.read_text(encoding="utf-8")
    assert old in text
    p = tmp_path / "s.toml"
    p.write_text(text.replace(old, new), encoding="utf-8")
    with pytest.raises(SettingsError, match=match):
        load_cost_settings(p)


# --- run ----------------------------------------------------------------------------------------------------

def test_run_writes_files_manifest_and_hashes(tmp_path, bars):
    out = make_run(bars, tmp_path / "runs-fixture")
    assert out.dir.name == "sma20-E0-25bp-20261016T120000Z"
    assert re.fullmatch(r"[a-z0-9]+-[A-Z0-9]+-\d+bp-\d{8}T\d{6}Z", out.dir.name)
    assert sorted(p.name for p in out.dir.iterdir()) == sorted([*RUN_FILES, "SHA256SUMS.txt"])
    m = json.loads((out.dir / "manifest.json").read_text(encoding="utf-8"))
    assert m["evidence"] == NOT_EVIDENCE
    assert {NOT_EVIDENCE, "FEE_UNCONFIRMED", "COSTS_ASSUMED"} <= set(m["labels"])
    assert m["result_sha256"] == sha256_file(out.dir / "result.json") == out.result_sha256
    assert m["inputs"]["day"]["bars_sha256"] and m["inputs"]["hour"]["kind"] == "fixture"
    assert m["settings"]["sha256_lf_normalized"] and m["settings"]["sha256_raw_bytes"]
    assert m["settings"]["normalization"].startswith("CRLF and lone CR replaced by LF")
    assert m["code_state"] == CODE and m["config"]["initial_cash"] == "1000000"
    assert json.loads((out.dir / "result.json").read_text(encoding="utf-8"))["evidence"] == NOT_EVIDENCE
    assert not [p for p in out.dir.parent.iterdir() if p.name.startswith(".tmp-")]


def test_same_inputs_same_result_bytes(tmp_path, bars):
    a = make_run(bars, tmp_path / "runs-fixture", now=NOW)
    b = make_run(bars, tmp_path / "runs-fixture", now=NOW + timedelta(seconds=1))
    assert (a.dir / "result.json").read_bytes() == (b.dir / "result.json").read_bytes()


def test_run_refusals_leave_nothing(tmp_path, bars):
    root = tmp_path / "runs-fixture"
    cfg = config()
    with pytest.raises(RunError, match="fixed at 1000000"):
        run_backtest(bars["day"], bars["hour"], RunConfig(cfg.rule, cfg.first_day, cfg.last_day, Decimal(2_000_000),
                                                           cfg.costs), root, code_state=CODE,
                     settings_file=DEFAULT_SETTINGS_FILE, now=NOW)
    with pytest.raises(RunError, match="does not follow the settings"):
        make_run(bars, root, costs=CostModel.scenario(25, 7))
    with pytest.raises(RunError, match="-fixture"):
        make_run(bars, tmp_path / "runs")
    with pytest.raises(RunError, match="classify_worktree"):  # an unclassified {commit, dirty} dict
        make_run(bars, root, code={"commit": "a" * 40, "dirty": False})
    assert not root.exists() and not (tmp_path / "runs").exists()
    first = make_run(bars, root)
    before = tree_hashes(first.dir)
    with pytest.raises(RunError, match="already exists"):
        make_run(bars, root)
    assert tree_hashes(first.dir) == before


def test_failed_write_leaves_no_run_directory(tmp_path, bars, monkeypatch):
    real = runmod.atomic_write_bytes
    n = {"k": 0}

    def flaky(path, data):
        n["k"] += 1
        if n["k"] == 3:
            raise OSError("disk full (simulated)")
        return real(path, data)

    monkeypatch.setattr(runmod, "atomic_write_bytes", flaky)
    with pytest.raises(OSError, match="simulated"):
        make_run(bars, tmp_path / "runs-fixture")
    assert list((tmp_path / "runs-fixture").iterdir()) == []


def test_tampered_input_is_refused(tmp_path, bars):
    import shutil

    copy = tmp_path / "bars-fixture" / bars["day"].name
    shutil.copytree(bars["day"], copy)
    f = copy / "bars_day.jsonl"
    f.write_bytes(f.read_bytes().replace(b'"close":"1', b'"close":"2', 1))
    with pytest.raises(DataIntegrityError):
        run_backtest(copy, bars["hour"], config(), tmp_path / "runs-fixture", code_state=CODE,
                     settings_file=DEFAULT_SETTINGS_FILE, now=NOW)


# --- verify -------------------------------------------------------------------------------------------------

def test_verify_passes_and_writes_nothing(tmp_path, bars):
    out = make_run(bars, tmp_path / "runs-fixture")
    before = tree_hashes(out.dir)
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.ok, rep.checks
    assert [k for k, v in rep.checks.items() if v["ok"] is True] == list(runmod.VERIFY_CHECKS)
    assert rep.checks["regression_tests"]["ok"] is None
    assert "raw bytes identical" in rep.checks["settings"]["detail"]
    assert tree_hashes(out.dir) == before
    assert rep.to_dict()["evidence"] == NOT_EVIDENCE


def test_verify_fails_on_a_changed_result_file(tmp_path, bars):
    out = make_run(bars, tmp_path / "runs-fixture")
    f = out.dir / "result.json"
    f.write_bytes(f.read_bytes().replace(b'"rule":"sma20"', b'"rule":"sma60"', 1))
    rep = verify_run(out.dir, code_state=CODE)
    assert not rep.ok and rep.checks["files"]["ok"] is False
    assert rep.checks["reproducibility"]["ok"] is True  # the recomputation still matches the manifest


def test_verify_fails_when_inputs_change(tmp_path, bars):
    import shutil

    day = tmp_path / "bars-fixture" / bars["day"].name
    shutil.copytree(bars["day"], day)
    out = run_backtest(day, bars["hour"], config(), tmp_path / "runs-fixture", code_state=CODE,
                       settings_file=DEFAULT_SETTINGS_FILE, now=NOW)
    (day / "bars_day.jsonl").write_bytes((day / "bars_day.jsonl").read_bytes() + b"\n")
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.checks["inputs"]["ok"] is False and rep.checks["reproducibility"]["ok"] is False and not rep.ok


def test_verify_settings_content_vs_line_endings(tmp_path, bars):
    s = tmp_path / "costs.toml"
    s.write_bytes(DEFAULT_SETTINGS_FILE.read_bytes().replace(b"\r\n", b"\n"))
    out = make_run(bars, tmp_path / "runs-fixture", settings_file=s)
    s.write_bytes(s.read_bytes().replace(b"\n", b"\r\n"))  # line endings only
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.ok and "raw bytes differ" in rep.checks["settings"]["detail"]
    s.write_bytes(s.read_bytes().replace(b"# MoneyLab", b"# Changed MoneyLab", 1))  # content
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.checks["settings"]["ok"] is False and not rep.ok


@pytest.mark.parametrize("run_code,now_code", [
    (CODE, classify_worktree("b" * 40, [])),
    (CODE, classify_worktree("a" * 40, [(" M", "src/moneylab/backtest/run.py")])),
    (classify_worktree("a" * 40, [(" M", "src/moneylab/backtest/run.py")]), CODE),
    (classify_worktree(None, []), CODE),
    (CODE, classify_worktree("a" * 40, None)),
    (CODE, {"commit": "a" * 40, "dirty": False}),
])
def test_verify_fails_on_code_mismatch_or_uncommitted_code(tmp_path, bars, run_code, now_code):
    out = make_run(bars, tmp_path / "runs-fixture", code=run_code)
    rep = verify_run(out.dir, code_state=now_code)
    assert rep.checks["code"]["ok"] is False and not rep.ok
    assert rep.checks["reproducibility"]["ok"] is True


def test_verify_checks_stored_accounting_rows(tmp_path, bars):
    out = make_run(bars, tmp_path / "runs-fixture")
    daily = out.dir / "daily.jsonl"
    rows = [json.loads(x) for x in daily.read_text(encoding="utf-8").splitlines()]
    rows[5]["equity"] = str(Decimal(rows[5]["equity"]) + 1)
    daily.write_text("".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows),
                     encoding="utf-8")
    sums = out.dir / "SHA256SUMS.txt"  # keep the file hashes consistent: only the invariant can catch it
    sums.write_text("".join(f"{sha256_file(out.dir / n)}  {n}\n" for n in RUN_FILES), encoding="utf-8")
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.checks["files"]["ok"] is True
    assert rep.checks["accounting"]["ok"] is False and "equity = cash + quantity" in rep.checks["accounting"]["detail"]
    assert not rep.ok


def test_engine_self_check_passes():
    assert "exact final equity" in runmod.engine_self_check()
