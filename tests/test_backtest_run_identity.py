"""BT-3c run manifest /2 identity, the independent identity check, run/1 legacy and missing sources
(SYNTHETIC / NOT_EVIDENCE). Inputs are fixture pulls exported in tmp_path; nothing is fetched."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_bar_export import fixture_pull

from moneylab import cli
from moneylab.backtest import run as runmod
from moneylab.backtest.code_state import classify_worktree
from moneylab.backtest.data import CONFIRM_DELAY
from moneylab.backtest.portfolio import RunConfig
from moneylab.backtest.run import (
    INITIAL_CASH_KRW,
    LEGACY_SCHEMA,
    SCHEMA,
    VERIFY_CHECKS,
    config_sha256,
    run_backtest,
    verify_run,
)
from moneylab.backtest.segment import export_segment
from moneylab.backtest.settings import DEFAULT_SETTINGS_FILE, cost_model, load_cost_settings
from moneylab.providers.upbit.bar_export import export_bars
from moneylab.storage.atomic import sha256_file

CODE = classify_worktree("c" * 40, [])
OLD = classify_worktree("d" * 40, [])
NOW = datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)
FIRST, LAST = datetime(2025, 6, 26, tzinfo=UTC), datetime(2025, 11, 28, tzinfo=UTC)


@pytest.fixture(scope="module")
def source(tmp_path_factory):
    root = tmp_path_factory.mktemp("bt3c-id")
    pulls = {iv: fixture_pull(root / "pulls", iv) for iv in ("day", "hour")}
    return {iv: export_bars(p, root / "bars-fixture").dir for iv, p in pulls.items()}


def model():
    s, _ = load_cost_settings()
    return cost_model(s, 25, "E0", INITIAL_CASH_KRW)


def cfg(**kw) -> RunConfig:
    m, verified = model()
    return RunConfig("sma20", FIRST, LAST, INITIAL_CASH_KRW, m, capacity_verified=verified, **kw)


def make_run(day, hour, out: Path, code=CODE):
    return run_backtest(day, hour, cfg(), out, code_state=code, settings_file=DEFAULT_SETTINGS_FILE, now=NOW)


def rewrite_manifest(run_dir: Path, change) -> None:
    """Edit manifest.json and re-sign it in SHA256SUMS.txt, so only the targeted check can notice."""
    p = run_dir / "manifest.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    change(m)
    p.write_bytes((json.dumps(m, sort_keys=True, indent=1) + "\n").encode("utf-8"))
    sums = run_dir / "SHA256SUMS.txt"
    lines = [f"{sha256_file(p)}  manifest.json" if ln.endswith("  manifest.json") else ln
             for ln in sums.read_text(encoding="utf-8").splitlines()]
    sums.write_text("".join(ln + "\n" for ln in lines), encoding="utf-8", newline="\n")


def segment_run(source, tmp_path):
    copy = tmp_path / "src" / "bars-fixture"  # own copy of the sources so they can be moved or changed
    for iv in ("day", "hour"):
        shutil.copytree(source[iv], copy / Path(source[iv]).name)
    exp = export_segment(copy / Path(source["day"]).name, copy / Path(source["hour"]).name, LAST,
                         tmp_path / "seg-fixture")
    m = exp.plan.manifest["intervals"]
    out = make_run(exp.dir / m["day"]["dir_name"], exp.dir / m["hour"]["dir_name"], tmp_path / "runs-fixture")
    return out, copy


# --- I1: config identity ---------------------------------------------------------------------------------------

def test_i1_equivalent_resolved_configs_have_one_sha():
    plain = cfg()
    explicit = cfg(scenario="E0", fill_substitution="none", confirm_delay=CONFIRM_DELAY)
    assert config_sha256(plain.to_dict()) == config_sha256(explicit.to_dict())
    assert config_sha256(plain.to_dict()) != config_sha256(cfg(scenario="E1").to_dict())


# --- I5: normal run/2 ------------------------------------------------------------------------------------------

def test_i5_full_input_run2_manifest_and_verify(source, tmp_path):
    out = make_run(source["day"], source["hour"], tmp_path / "runs-fixture")
    m = out.manifest
    assert m["schema"] == SCHEMA and m["config_sha256"] == config_sha256(m["config"])
    assert m["boundary"] == {"g_start": "2025-06-28T00:00:00Z", "g_end": "2025-12-01T00:00:00Z",
                             "first_ref": "2025-06-27T01:00:00Z", "valuation_end": "2025-11-30T01:00:00Z"}
    for iv in ("day", "hour"):
        rec = m["inputs"][iv]
        assert rec["segment"] is None and rec["consumed_sha256"] != rec["bars_sha256"] and rec["consumed_bars"] > 0
    assert "config_sha256" not in json.loads((out.dir / "result.json").read_text(encoding="utf-8"))
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.status == "OK" and rep.ok and list(rep.checks)[:9] == list(VERIFY_CHECKS)
    assert all(rep.checks[k]["ok"] is True for k in VERIFY_CHECKS)


def test_i5_segment_run_verifies_with_derivation(source, tmp_path):
    out, _ = segment_run(source, tmp_path)
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.status == "OK" and all(rep.checks[k]["ok"] is True for k in VERIFY_CHECKS)
    assert "source -> segment re-derived" in rep.checks["identity"]["detail"]
    for iv in ("day", "hour"):
        rec = out.manifest["inputs"][iv]
        assert rec["bars_sha256"] == rec["consumed_sha256"]
        assert set(rec["segment"]) == {"segment_id", "segment_content_sha256", "segment_manifest_sha256",
                                       "cut_end_utc", "source_bars_sha256", "source_bars_manifest_sha256"}


# --- I2-I4: tampering ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("change,text", [
    (lambda m: m["config"].update(scenario="E1"), "config_sha256"),
    (lambda m: m.update(config_sha256="0" * 64), "config_sha256"),
    (lambda m: m["inputs"]["hour"].update(consumed_sha256="0" * 64), "consumed identity"),
    (lambda m: m["inputs"]["day"].update(consumed_bars=1), "consumed identity"),
    (lambda m: m["boundary"].update(g_end="2025-12-02T00:00:00Z"), "boundary"),
], ids=["config", "config_sha", "consumed_sha", "consumed_bars", "boundary"])
def test_i2_i4_tampered_identity_fields_fail(source, tmp_path, change, text):
    out = make_run(source["day"], source["hour"], tmp_path / "runs-fixture")
    rewrite_manifest(out.dir, change)
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.checks["files"]["ok"] is True
    assert rep.checks["identity"]["ok"] is False and text in rep.checks["identity"]["detail"]
    assert rep.status == "FAILED" and not rep.ok


# --- I6, I7: run/1 legacy -------------------------------------------------------------------------------------

def to_run1(run_dir: Path) -> None:
    def change(m):
        m["schema"] = LEGACY_SCHEMA
        for key in ("config_sha256", "boundary"):
            m.pop(key)
        for rec in m["inputs"].values():
            for key in ("consumed_sha256", "consumed_bars", "segment"):
                rec.pop(key)
    rewrite_manifest(run_dir, change)


def test_i6_run1_is_legacy_not_failed(source, tmp_path, monkeypatch, capsys):
    out = make_run(source["day"], source["hour"], tmp_path / "runs-fixture", code=OLD)
    to_run1(out.dir)
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.status == "LEGACY_REQUIRES_COMMIT_ddddddd" and not rep.ok
    for k in ("files", "inputs", "settings", "reproducibility", "accounting", "boundary", "engine_self_check"):
        assert rep.checks[k]["ok"] is True, k
    for k in ("identity", "code"):
        assert rep.checks[k]["ok"] is None and "d" * 40 in rep.checks[k]["detail"]
    assert "not a corruption" in rep.checks["identity"]["detail"]
    assert rep.to_dict()["status"] == rep.status
    monkeypatch.setattr(cli, "backtest_code_state", lambda: CODE)
    assert cli.main(["backtest-verify", str(out.dir)]) == 1
    text = capsys.readouterr().out
    assert "LEGACY_REQUIRES_COMMIT_ddddddd" in text and "NOTE identity" in text


def test_i6_run1_at_its_own_commit_still_lacks_run2_identity(source, tmp_path):
    out = make_run(source["day"], source["hour"], tmp_path / "runs-fixture", code=CODE)
    to_run1(out.dir)
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.checks["code"]["ok"] is True and rep.checks["identity"]["ok"] is None
    assert rep.status == "LEGACY_REQUIRES_COMMIT_ccccccc"


def test_i7_corrupted_run1_is_failed(source, tmp_path):
    out = make_run(source["day"], source["hour"], tmp_path / "runs-fixture", code=OLD)
    to_run1(out.dir)
    p = out.dir / "trades.jsonl"
    p.write_bytes(p.read_bytes() + b"\n")
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.checks["files"]["ok"] is False and rep.status == "FAILED"


def test_unknown_run_schema_is_failed(source, tmp_path):
    out = make_run(source["day"], source["hour"], tmp_path / "runs-fixture")
    rewrite_manifest(out.dir, lambda m: m.update(schema="moneylab.backtest.run/9"))
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.checks["files"]["ok"] is False and rep.status == "FAILED"


# --- I8: missing or different source of a segment ------------------------------------------------------------

def test_i8_missing_source_is_source_unavailable(source, tmp_path, monkeypatch, capsys):
    out, copy = segment_run(source, tmp_path)
    moved = tmp_path / "moved"
    shutil.move(str(copy), str(moved))
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.status == "SOURCE_UNAVAILABLE" and not rep.ok
    assert rep.checks["identity"]["ok"] is None and rep.checks["identity"]["detail"].startswith("SOURCE_UNAVAILABLE")
    assert all(rep.checks[k]["ok"] is True for k in VERIFY_CHECKS if k != "identity")
    monkeypatch.setattr(cli, "backtest_code_state", lambda: CODE)
    assert cli.main(["backtest-verify", str(out.dir)]) == 1 and "SOURCE_UNAVAILABLE" in capsys.readouterr().out


def test_i8_changed_source_is_failed(source, tmp_path):
    out, copy = segment_run(source, tmp_path)
    day_src = copy / Path(source["day"]).name
    shutil.rmtree(day_src)
    shutil.copytree(copy / Path(source["hour"]).name, day_src)  # a valid bar directory, but not the source
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.checks["identity"]["ok"] is False and rep.status == "FAILED"


# --- I9: identity does not depend on the simulation ----------------------------------------------------------

def test_i9_identity_does_not_run_the_backtest(source, tmp_path, monkeypatch):
    out, _ = segment_run(source, tmp_path)

    def boom(*a, **k):
        raise ValueError("simulate is disabled in this test")

    monkeypatch.setattr(runmod, "simulate", boom)
    monkeypatch.setattr(runmod, "engine_self_check", lambda: "skipped (simulate disabled)")
    rep = verify_run(out.dir, code_state=CODE)
    assert rep.checks["identity"]["ok"] is True
    assert rep.checks["reproducibility"]["ok"] is False and rep.status == "FAILED"
