"""BT-2b-2 CLI: bars-export, backtest, backtest-verify (SYNTHETIC / NOT_EVIDENCE, offline, tmp_path only).
backtest_code_state is replaced by a fixed value so the tests do not depend on the working tree."""

from __future__ import annotations

import json

import pytest
from test_bar_export import fixture_pull

from moneylab import cli
from moneylab.backtest.code_state import classify_worktree
from moneylab.cli import main
from moneylab.domain.bars import NOT_EVIDENCE

CODE = classify_worktree("c" * 40, [])


@pytest.fixture()
def clean_git(monkeypatch):
    monkeypatch.setattr(cli, "backtest_code_state", lambda *a, **k: dict(CODE))


@pytest.fixture()
def exported(tmp_path, clean_git):
    out = tmp_path / "bars-fixture"
    dirs = {}
    for iv in ("day", "hour"):
        pull = fixture_pull(tmp_path / "pulls", iv)
        assert main(["bars-export", str(pull), "--out", str(out)]) == 0
        dirs[iv] = out / pull.name
    return dirs


def backtest_args(exported, out, *extra):
    return ["backtest", "--daily", str(exported["day"]), "--hourly", str(exported["hour"]), "--rule", "sma20",
            "--first-day", "2025-06-26", "--last-day", "2025-11-28", "--out", str(out), *extra]


def only_dir(root):
    dirs = [p for p in root.iterdir() if p.is_dir()]
    assert len(dirs) == 1
    return dirs[0]


def test_export_backtest_verify_end_to_end(tmp_path, exported, capsys):
    runs = tmp_path / "runs-fixture"
    assert main(backtest_args(exported, runs)) == 0
    run = only_dir(runs)
    assert run.name.startswith("sma20-E0-25bp-") and run.name.endswith("Z")
    m = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert m["code_state"] == CODE and m["config"]["initial_cash"] == "1000000"
    assert m["config"]["fill_substitution"] == "none" and m["config"]["costs"]["fee_basis"] == "inclusive"
    assert main(["backtest-verify", str(run)]) == 0
    out = capsys.readouterr().out
    assert NOT_EVIDENCE in out and "backtest-verify" in out
    assert main(["backtest-verify", str(run), "--json"]) == 0


def test_cli_options_reach_the_run(tmp_path, exported):
    runs = tmp_path / "runs-fixture"
    assert main(backtest_args(exported, runs, "--scenario", "E1", "--fee-bps", "5", "--fee-basis", "on_top",
                              "--no-impact", "--fill-substitution", "prereg_6_3")) == 0
    m = json.loads((only_dir(runs) / "manifest.json").read_text(encoding="utf-8"))
    c = m["config"]
    assert (c["scenario"], c["costs"]["buy_fee_bps"], c["costs"]["fee_basis"], c["costs"]["impact_bps"],
            c["fill_substitution"]) == ("E1", "5", "on_top", "0", "prereg_6_3")


def test_cli_refusals(tmp_path, exported):
    assert main(backtest_args(exported, tmp_path / "runs")) == 1  # not a -fixture root
    assert not (tmp_path / "runs").exists()
    real = fixture_pull(tmp_path / "realpulls", "day", provenance="real")
    assert main(["bars-export", str(real), "--out", str(tmp_path / "r-fixture")]) == 1
    assert not (tmp_path / "r-fixture").exists() or not any((tmp_path / "r-fixture").iterdir())
    with pytest.raises(SystemExit):  # the CLI has no initial-cash option (fixed at 1,000,000 KRW)
        main(backtest_args(exported, tmp_path / "x-fixture", "--cash", "5000000"))


def test_verify_fails_after_a_commit_change(tmp_path, exported, monkeypatch):
    runs = tmp_path / "runs-fixture"
    assert main(backtest_args(exported, runs)) == 0
    monkeypatch.setattr(cli, "backtest_code_state", lambda *a, **k: classify_worktree("d" * 40, []))
    assert main(["backtest-verify", str(only_dir(runs))]) == 1
