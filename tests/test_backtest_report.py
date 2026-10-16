"""BT-2b-3 reports: build_report / check_report and the CLI (SYNTHETIC / NOT_EVIDENCE).

Runs are made in tmp_path from fixture bars (test_backtest_run); nothing is written elsewhere.
backtest_code_state is replaced by a fixed value in the CLI tests."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from test_backtest_run import CODE, NOW, bars, make_run  # noqa: F401  (bars is a fixture)
from test_bar_export import tree_hashes

from moneylab import cli
from moneylab.backtest import report as rpt
from moneylab.backtest.benchmarks import bt_seed
from moneylab.backtest.code_state import classify_worktree
from moneylab.backtest.report import REPORT_FILES, ReportError, build_report, check_report, report_bytes
from moneylab.cli import main
from moneylab.domain.bars import NOT_EVIDENCE

SEED = 20261016
LATER = NOW + timedelta(minutes=5)


def report(run_dir, root, *, now=LATER, seed=SEED, draws=99, code=CODE):
    return build_report(run_dir, root, seed=seed, draws=draws, code_state=code, now=now)


@pytest.fixture(scope="module")
def run(bars, tmp_path_factory):
    return make_run(bars, tmp_path_factory.mktemp("rep") / "runs-fixture")


def body_of(d):
    return json.loads((d / "report.json").read_text(encoding="utf-8"))


def resum(d):
    (d / "SHA256SUMS.txt").write_text("".join(f"{hashlib.sha256((d / n).read_bytes()).hexdigest()}  {n}\n"
                                              for n in REPORT_FILES), encoding="utf-8")


# --- build ----------------------------------------------------------------------------------------------

def test_report_files_labels_and_definitions(tmp_path, run):
    out = report(run.dir, tmp_path / "reports-fixture")
    assert out.dir.name == f"{run.dir.name}-report-20261016T120500Z"
    assert sorted(p.name for p in out.dir.iterdir()) == sorted([*REPORT_FILES, "SHA256SUMS.txt"])
    raw = (out.dir / "report.json").read_bytes()
    assert raw.endswith(b"}\n") and not raw.endswith(b"\n\n") and b"\r" not in raw
    assert raw == report_bytes(out.body) and hashlib.sha256(raw).hexdigest() == out.report_sha256
    b = body_of(out.dir)
    assert b["evidence"] == NOT_EVIDENCE and NOT_EVIDENCE in b["labels"] and "DESCRIPTIVE_ONLY" in b["labels"]
    assert b["metrics_definition"]["version"] == "bt-metrics/1" and b["metrics_definition"]["annualization_days"] == 365
    assert b["metrics_definition"]["risk_free_rate"] == 0.0 and "generally differ" in b["metrics_definition"]["mdd_note"]
    s = b["seed"]
    assert s["algorithm"] == "bt-seed/1" and s["seed"] == str(SEED) and s["labels"] == ["B1", "sma20", "E0"]
    assert s["derived_seed"] == str(bt_seed(SEED, "B1", "sma20", "E0")) and s["b1_draws"] == 99
    assert b["p_values"] == "not computed" and b["benchmarks"]["status"] == "compared"
    assert b["run"]["result_sha256"] == run.result_sha256
    meta = json.loads((out.dir / "report_meta.json").read_text(encoding="utf-8"))
    assert meta["report_sha256"] == out.report_sha256 and meta["python"] and meta["code_state"] == CODE
    assert meta["created_utc"] == LATER.isoformat()
    md = (out.dir / "report.md").read_text(encoding="utf-8")
    assert md.splitlines()[2].startswith(f"**{NOT_EVIDENCE}**") and "no p-values" in md and "REPORT_ONLY" in md


def test_metrics_agree_with_the_ledger(tmp_path, run):
    b = report(run.dir, tmp_path / "reports-fixture").body
    m = b["metrics"]
    total = Decimal(m["total_return_ledger"])
    assert total == Decimal(m["final_equity"]) / Decimal(m["initial_cash"]) - 1
    assert abs(m["total_return"]["value"] - float(total)) <= 1e-12
    assert math.isclose(math.exp(m["sum_log_return"]["value"]) * 1_000_000, float(m["final_equity"]), rel_tol=1e-12)
    assert m["mdd_ledger_after_trade"]["value"] == json.loads((run.dir / "metrics.json").read_text())["max_drawdown"]
    assert m["legs"] == len((run.dir / "trades.jsonl").read_text().splitlines())
    assert b["benchmarks"]["strategy"]["sum_log_return"] == m["sum_log_return"]
    assert b["alignment"]["aligned"] is True


def test_report_bytes_are_reproducible(tmp_path, run):
    a = report(run.dir, tmp_path / "reports-fixture", now=LATER)
    b = report(run.dir, tmp_path / "reports-fixture", now=LATER + timedelta(seconds=1))
    for name in ("report.json", "report.md"):
        assert (a.dir / name).read_bytes() == (b.dir / name).read_bytes()
    assert (a.dir / "report_meta.json").read_bytes() != (b.dir / "report_meta.json").read_bytes()  # time only


def test_run_directory_is_unchanged(tmp_path, run):
    before = tree_hashes(run.dir)
    report(run.dir, tmp_path / "reports-fixture")
    assert check_report(next((tmp_path / "reports-fixture").iterdir()), run.dir, code_state=CODE).ok
    assert tree_hashes(run.dir) == before


def test_no_trades_report(tmp_path, bars):
    from test_backtest_run import config
    from moneylab.backtest.run import run_backtest
    from moneylab.backtest.settings import DEFAULT_SETTINGS_FILE
    cfg = config()
    short = type(cfg)(cfg.rule, datetime(2025, 6, 2, tzinfo=UTC), datetime(2025, 6, 12, tzinfo=UTC),
                      cfg.initial_cash, cfg.costs, scenario=cfg.scenario, capacity_verified=cfg.capacity_verified)
    r = run_backtest(bars["day"], bars["hour"], short, tmp_path / "runs-fixture", code_state=CODE,
                     settings_file=DEFAULT_SETTINGS_FILE, now=NOW)  # sma20 has no 20-day history: no signal
    b = report(r.dir, tmp_path / "reports-fixture").body
    m = b["metrics"]
    assert m["no_trades"] is True and m["legs"] == 0 and m["total_return"]["value"] == 0.0
    assert m["sharpe_log"] == {"value": None, "reason": "zero_sample_sd"}
    assert m["sortino"] == {"value": None, "reason": "no_downside"}
    assert m["turnover"]["period"]["value"] == 0.0 and m["exposure"]["value"] == 0.0
    assert m["calmar"] == {"value": None, "reason": "zero_drawdown"}
    q = b["benchmarks"]["b1"]["mean_log_return"]
    assert q["mean"]["value"] == 0.0 and b["benchmarks"]["b1"]["structure"]["trades"] == 0


def test_fee_zero_vs_positive(tmp_path, bars):
    r0 = make_run(bars, tmp_path / "runs-fixture", fee=0)
    r25 = make_run(bars, tmp_path / "runs-fixture", fee=25, now=NOW + timedelta(seconds=1))
    b0 = report(r0.dir, tmp_path / "reports-fixture").body
    b25 = report(r25.dir, tmp_path / "reports-fixture").body
    legs = b25["metrics"]["legs"]
    assert legs == b0["metrics"]["legs"] and legs > 0
    diff = b25["metrics"]["sum_log_return"]["value"] - b0["metrics"]["sum_log_return"]["value"]
    assert math.isclose(diff, legs * math.log1p(-0.0025), rel_tol=1e-9)
    assert b25["cost_logs"]["buy"] < b0["cost_logs"]["buy"] < 0  # kappa and iota still cost at fee 0


def test_not_aligned_run_has_no_comparison(tmp_path, bars):
    diag = make_run(bars, tmp_path / "runs-fixture", scenario="DIAG")  # fills at the hour open, valued at the close
    out = report(diag.dir, tmp_path / "reports-fixture")
    b = out.body
    assert b["alignment"]["aligned"] is False and b["benchmarks"]["status"] == "not_aligned"
    assert b["benchmarks"]["reasons"] and set(b["benchmarks"]) == {"status", "reasons"}  # no numbers, not 0
    assert any("differs from the valuation price" in x for x in b["benchmarks"]["reasons"])
    assert b["metrics"]["sharpe_log"]["value"] is not None  # the metrics themselves are kept
    assert "not_aligned" in (out.dir / "report.md").read_text(encoding="utf-8")
    assert check_report(out.dir, diag.dir, code_state=CODE).ok


# --- refusals and atomicity ------------------------------------------------------------------------------

def test_refusals_leave_nothing(tmp_path, run):
    root = tmp_path / "reports-fixture"
    with pytest.raises(ReportError, match="does not verify"):
        report(run.dir, root, code=classify_worktree("b" * 40, []))
    with pytest.raises(ReportError, match="-fixture"):
        report(run.dir, tmp_path / "reports")
    with pytest.raises(ReportError, match="inside the run directory"):
        report(run.dir, run.dir / "x-fixture")
    with pytest.raises(ReportError, match="2\\*\\*64"):
        report(run.dir, root, seed=2**64)
    with pytest.raises(ReportError, match="draws"):
        report(run.dir, root, draws=0)
    assert not root.exists() and not (tmp_path / "reports").exists() and not (run.dir / "x-fixture").exists()
    first = report(run.dir, root)
    before = tree_hashes(first.dir)
    with pytest.raises(ReportError, match="already exists"):
        report(run.dir, root)
    assert tree_hashes(first.dir) == before


def test_failed_write_leaves_no_report_directory(tmp_path, run, monkeypatch):
    calls = {"n": 0}
    real = rpt.atomic_write_bytes

    def flaky(path, data):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk full (simulated)")
        return real(path, data)

    monkeypatch.setattr(rpt, "atomic_write_bytes", flaky)
    root = tmp_path / "reports-fixture"
    before = tree_hashes(run.dir)
    with pytest.raises(OSError):
        report(run.dir, root)
    assert list(root.iterdir()) == [] and tree_hashes(run.dir) == before


# --- check_report ----------------------------------------------------------------------------------------

def test_check_report_ok_and_writes_nothing(tmp_path, run):
    out = report(run.dir, tmp_path / "reports-fixture")
    before, run_before = tree_hashes(out.dir), tree_hashes(run.dir)
    rep = check_report(out.dir, run.dir, code_state=CODE)
    assert rep.ok and set(rep.checks) == {"files", "meta", "versions", "run_refs", "run_verify", "content"}
    assert "same Python version" in rep.checks["meta"]["detail"]
    assert tree_hashes(out.dir) == before and tree_hashes(run.dir) == run_before


def test_check_report_detects_report_tampering(tmp_path, run):
    out = report(run.dir, tmp_path / "reports-fixture")
    p = out.dir / "report.json"
    b = body_of(out.dir)
    b["metrics"]["legs"] += 1
    p.write_bytes(report_bytes(b))
    assert check_report(out.dir, run.dir, code_state=CODE).checks["files"]["ok"] is False
    resum(out.dir)  # consistent sums: the meta hash still catches it
    rep = check_report(out.dir, run.dir, code_state=CODE)
    assert rep.checks["files"]["ok"] and rep.checks["meta"]["ok"] is False and not rep.ok
    meta = json.loads((out.dir / "report_meta.json").read_text(encoding="utf-8"))
    meta["report_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out.dir / "report_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    resum(out.dir)  # every hash consistent: only the recomputation catches it
    rep = check_report(out.dir, run.dir, code_state=CODE)
    assert rep.checks["meta"]["ok"] and rep.checks["content"]["ok"] is False and not rep.ok


def test_check_report_detects_markdown_and_extra_files(tmp_path, run):
    out = report(run.dir, tmp_path / "reports-fixture")
    md = out.dir / "report.md"
    md.write_text(md.read_text(encoding="utf-8") + "edited\n", encoding="utf-8")
    resum(out.dir)
    assert check_report(out.dir, run.dir, code_state=CODE).checks["content"]["ok"] is False
    (out.dir / "extra.txt").write_text("x", encoding="utf-8")
    assert check_report(out.dir, run.dir, code_state=CODE).checks["files"]["ok"] is False


def test_check_report_detects_run_tampering(tmp_path, bars):
    r = make_run(bars, tmp_path / "runs-fixture")
    out = report(r.dir, tmp_path / "reports-fixture")
    res = r.dir / "result.json"
    res.write_bytes(res.read_bytes() + b" ")
    rep = check_report(out.dir, r.dir, code_state=CODE)
    assert rep.checks["run_refs"]["ok"] is False and rep.checks["run_verify"]["ok"] is False and not rep.ok


def test_check_report_refuses_unknown_versions(tmp_path, run):
    for key, path in (("metrics_definition", "version"), ("seed", "algorithm")):
        out = report(run.dir, tmp_path / f"r-{key}-fixture")
        b = body_of(out.dir)
        b[key][path] = "future/2"
        (out.dir / "report.json").write_bytes(report_bytes(b))
        meta = json.loads((out.dir / "report_meta.json").read_text(encoding="utf-8"))
        meta["report_sha256"] = hashlib.sha256((out.dir / "report.json").read_bytes()).hexdigest()
        (out.dir / "report_meta.json").write_text(json.dumps(meta), encoding="utf-8")
        resum(out.dir)
        rep = check_report(out.dir, run.dir, code_state=CODE)
        assert rep.checks["versions"]["ok"] is False and "future/2" in rep.checks["versions"]["detail"]
        assert rep.checks["content"]["ok"] is False and not rep.ok


def test_check_report_fails_when_code_changed(tmp_path, run):
    out = report(run.dir, tmp_path / "reports-fixture")
    rep = check_report(out.dir, run.dir, code_state=classify_worktree("d" * 40, []))
    assert rep.checks["run_verify"]["ok"] is False and not rep.ok


# --- CLI -------------------------------------------------------------------------------------------------

def test_cli_report_and_verify(tmp_path, run, monkeypatch, capsys):
    monkeypatch.setattr(cli, "backtest_code_state", lambda *a, **k: dict(CODE))
    root = tmp_path / "reports-fixture"
    assert main(["backtest-report", str(run.dir), "--seed", "7", "--b1-draws", "20", "--out", str(root)]) == 0
    d = next(root.iterdir())
    assert body_of(d)["seed"]["b1_draws"] == 20 and body_of(d)["seed"]["seed"] == "7"
    assert main(["backtest-report-verify", str(d), str(run.dir)]) == 0
    out = capsys.readouterr().out
    assert NOT_EVIDENCE in out and "backtest-report-verify" in out and "PASS content" in out
    assert main(["backtest-report-verify", str(d), str(run.dir), "--json"]) == 0
    with pytest.raises(SystemExit):  # --seed is required (no default)
        main(["backtest-report", str(run.dir), "--out", str(root)])
    assert main(["backtest-report", str(run.dir), "--seed", "-1", "--out", str(root)]) == 1
    assert main(["backtest-report", str(run.dir), "--seed", "7", "--out", str(tmp_path / "plain")]) == 1
    assert not (tmp_path / "plain").exists()
