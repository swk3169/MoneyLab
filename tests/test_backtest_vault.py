"""BT-3d vault locking (docs/tasks/BT-3D/WORK_ORDER.md T1-T20). SYNTHETIC / NOT_EVIDENCE, offline.

Locked rows carry prices that appear nowhere else (7777.77 daily, 8888.88 hourly), so a leak shows up as text.
"""

from __future__ import annotations

import dataclasses
import hashlib
import inspect
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from backtest_helpers import DAY, HOUR, T0, flat_bar, series
from test_bar_export import fixture_pull

from moneylab.backtest import vault as vmod
from moneylab.backtest.bars_io import load_bars
from moneylab.backtest.code_state import classify_worktree
from moneylab.backtest.data import DataIntegrityError
from moneylab.backtest.portfolio import RunConfig
from moneylab.backtest.run import INITIAL_CASH_KRW, run_backtest, verify_run
from moneylab.backtest.segment import export_segment
from moneylab.backtest.settings import DEFAULT_SETTINGS_FILE, cost_model, load_cost_settings
from moneylab.backtest.vault import (
    ALREADY_RECORDED_IDENTICAL,
    ALREADY_SEALED_IDENTICAL,
    CREATED,
    OPENED,
    RECORD_UNREADABLE,
    RECORDED,
    UNOPENED,
    ForwardVault,
    HistoricalHoldoutVault,
    VaultError,
    VaultExistsError,
    VaultIntegrityError,
    VaultLockedError,
    VaultPreconditionError,
    VaultSpec,
    build_vault,
    record_evidence,
    vault_status,
)
from moneylab.domain.bars import NOT_EVIDENCE, canonical_bar_rows, utc_iso
from moneylab.providers.upbit.bar_export import export_bars
from moneylab.storage.atomic import sha256_file, sha256_of

CODE = classify_worktree("c" * 40, [])
NOW = datetime(2026, 10, 17, 12, 0, 0, tzinfo=UTC)
C = T0 + 40 * DAY  # 2020-02-10
H = T0 + 55 * DAY  # 2020-02-25
L = T0 + 70 * DAY  # 2020-03-11, not the first of a month
W_I = datetime(2020, 4, 15, tzinfo=UTC)
W_F = datetime(2020, 5, 20, tzinfo=UTC)
PRE, CFG, EV = "a" * 64, "b" * 64, "e" * 64
LOCKED_DAY, LOCKED_HOUR, FWD = Decimal("7777.77"), Decimal("8888.88"), Decimal("5555.55")
LOCKED_TIME = utc_iso(T0 + 47 * DAY)  # a locked bar start that is not a spec boundary
SECRETS = ("7777.77", "8888.88", "5555.55", LOCKED_TIME)


def write_bars(root: Path, name: str, bars, kind: str = "fixture") -> Path:
    d = root / name
    d.mkdir(parents=True)
    interval = bars[0].interval
    data = canonical_bar_rows(bars)
    rows = sorted(bars, key=lambda b: b.start_utc)
    bars_file = f"bars_{interval}.jsonl"
    manifest = {"schema": "moneylab.backtest.bars/1", "evidence": NOT_EVIDENCE, "provenance": kind,
                "market": "KRW-BTC", "interval": interval, "bars": len(rows),
                "first_start": utc_iso(rows[0].start_utc), "last_start": utc_iso(rows[-1].start_utc),
                "bars_file": bars_file, "bars_sha256": hashlib.sha256(data).hexdigest(),
                "source_pull": {"pull_id": name}, "confirmation_rule": "hand written (tests)"}
    (d / bars_file).write_bytes(data)
    (d / "bars_manifest.json").write_bytes((json.dumps(manifest, sort_keys=True, indent=1) + "\n").encode())
    sums = "".join(f"{sha256_file(d / n)}  {n}\n" for n in sorted([bars_file, "bars_manifest.json"]))
    (d / "SHA256SUMS.txt").write_text(sums, encoding="utf-8", newline="\n")
    return d


def make_bars(days: int = 70):
    daily = [flat_bar("day", T0 + i * DAY, Decimal(100 + (i * 7) % 13) if T0 + (i + 1) * DAY <= C else LOCKED_DAY)
             for i in range(days)]
    hourly = []
    for d in range(days):
        for h in range(24):
            start = T0 + d * DAY + h * HOUR
            hourly.append(flat_bar("hour", start, Decimal(1000 + d) if start + HOUR <= C else LOCKED_HOUR))
    return daily, hourly


def source(root: Path, days: int = 70, *, kinds=("fixture", "fixture"), bars=None):
    daily, hourly = bars if bars is not None else make_bars(days)
    return write_bars(root, "day_src", daily, kinds[0]), write_bars(root, "hour_src", hourly, kinds[1])


def spec(**kw) -> VaultSpec:
    args = dict(confirmatory_data_end_utc=C, holdout_end_utc=H, locked_end_utc=L, forward_interim_end_utc=W_I,
                forward_final_end_utc=W_F, preregistration_sha256=PRE, config_sha256=CFG)
    args.update(kw)
    return VaultSpec(**args)


def build(tmp_path: Path, name: str = "vault-fixture", sp: VaultSpec | None = None, **kw):
    return build_vault(*source(tmp_path / f"src-{name}", **kw), sp or spec(), tmp_path / name)


def evidence_all(vdir: Path) -> None:
    assert record_evidence(vdir, "confirmatory_results", EV) == RECORDED
    assert record_evidence(vdir, "row9_strategy", EV, detail=["M20", "R5"]) == RECORDED
    assert record_evidence(vdir, "q12_done", EV) == RECORDED


def open_h(vdir: Path, pre: str = PRE, cfg: str = CFG):
    return HistoricalHoldoutVault(vdir).open_once(preregistration_sha256=pre, config_sha256=cfg, caller="tests")


def analyse(vdir: Path, kind: str, pre: str = PRE):
    return ForwardVault(vdir).open_analysis(kind, preregistration_sha256=pre, config_sha256=CFG, caller="tests")


def fwd_series(start: datetime = T0 + 64 * DAY, end: datetime = datetime(2020, 6, 2, tzinfo=UTC),
               price: Decimal = FWD, kind: str = "synthetic", skip=lambda t: False):
    days = [start + i * DAY for i in range((end - start) // DAY) if not skip(start + i * DAY)]
    daily = [flat_bar("day", t, price) for t in days]
    hourly = [flat_bar("hour", t + h * HOUR, price) for t in days for h in range(24)]
    return series(daily, kind), series(hourly, kind)


def seal(vdir: Path, month: str, fwd=None):
    d, h = fwd if fwd is not None else fwd_series()
    return ForwardVault(vdir).seal(d, h, month)


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def sealed_bytes(vdir: Path) -> dict[str, bytes]:
    names = [ln.partition("  ")[2] for ln in (vdir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()]
    return {n: (vdir / n).read_bytes() for n in names + ["SHA256SUMS.txt"]}


def no_secret(text: str) -> None:
    for s in SECRETS:
        assert s not in text, s


# --- T1 determinism ------------------------------------------------------------------------------------------

def test_t1_deterministic_and_path_independent(tmp_path):
    a = source(tmp_path / "a")
    b = source(tmp_path / "elsewhere" / "deeper")
    v1 = build_vault(*a, spec(), tmp_path / "one-fixture")
    v2 = build_vault(*b, spec(), tmp_path / "two-fixture")
    assert v1.status == v2.status == CREATED
    assert (v1.vault_id, v1.content_sha256, v1.manifest_sha256) == (v2.vault_id, v2.content_sha256, v2.manifest_sha256)
    assert sealed_bytes(v1.dir) == sealed_bytes(v2.dir)
    assert sha256_file(v1.dir / "vault_manifest.json") == v1.manifest_sha256
    assert v1.vault_id == f"vault_KRW-BTC_lock20200311T0000Z_{v1.content_sha256[:12]}"
    manifest = (v1.dir / "vault_manifest.json").read_text(encoding="utf-8")
    assert "elsewhere" not in manifest and str(tmp_path.name) not in manifest and "source_locator" not in manifest
    assert json.loads(manifest)["evidence"] == NOT_EVIDENCE


# --- T2 / T3 boundaries and partition ---------------------------------------------------------------------------

def test_t2_boundaries_are_exact(tmp_path):
    v = build(tmp_path)
    evidence_all(v.dir)
    st = vault_status(v.dir)
    assert st["public_bars"] == {"day": 40, "hour": 960}
    assert st["locked"]["day"]["holdout_eval_bars"] == 15 and st["locked"]["day"]["excluded_bars"] == 15
    assert st["locked"]["hour"]["holdout_eval_bars"] == 360 and st["locked"]["hour"]["excluded_bars"] == 360
    pub = load_bars(v.dir / "public" / "day_src")
    assert pub.last_end == C
    opened = open_h(v.dir).rows
    for iv, step in (("day", DAY), ("hour", HOUR)):
        held = [x.bar for x in opened[iv] if x.label == "HOLDOUT_EVAL"]
        excl = [x.bar for x in opened[iv] if x.label == "EXCLUDED"]
        assert held[0].end_utc == C + step and held[-1].end_utc == H
        assert excl[0].end_utc == H + step and excl[-1].end_utc == L
    assert load_bars(v.dir / "public" / "hour_src").last_end == C
    w = build(tmp_path, "equal-fixture", sp=spec(holdout_end_utc=L))
    assert vault_status(w.dir)["locked"]["day"]["excluded_bars"] == 0


def test_t3_partition_union_and_refusals(tmp_path):
    daily, hourly = make_bars()
    v = build(tmp_path, bars=(daily, hourly))
    evidence_all(v.dir)
    opened = open_h(v.dir).rows
    for iv, bars in (("day", daily), ("hour", hourly)):
        public = load_bars(v.dir / "public" / f"{iv}_src").bars
        locked = tuple(x.bar for x in opened[iv])
        assert not set(public) & set(locked)
        assert sorted(public + locked, key=lambda b: b.start_utc) == sorted(bars, key=lambda b: b.start_utc)
    with pytest.raises(VaultPreconditionError, match="after locked_end_utc"):
        build(tmp_path, "late-fixture", sp=spec(locked_end_utc=L - DAY))
    with pytest.raises(VaultPreconditionError, match="confirmatory_data_end_utc"):
        build(tmp_path, "nopub-fixture", sp=spec(confirmatory_data_end_utc=T0))
    with pytest.raises(VaultPreconditionError, match="historical holdout"):
        build(tmp_path, "nohold-fixture", days=40, sp=spec(holdout_end_utc=C + DAY, locked_end_utc=C + DAY))


# --- T4 public bars/1 compatibility -----------------------------------------------------------------------------

def test_t4_public_is_standard_bars_for_segment_run_and_verify(tmp_path):
    v = build(tmp_path)
    day, hour = v.dir / "public" / "day_src", v.dir / "public" / "hour_src"
    assert len(load_bars(day)) == 40 and len(load_bars(hour)) == 960
    seg = export_segment(day, hour, C - 3 * DAY, tmp_path / "seg-fixture")
    assert seg.status == CREATED
    s, _ = load_cost_settings()
    model, verified = cost_model(s, 25, "E0", INITIAL_CASH_KRW)
    cfg = RunConfig("sma20", T0 + 25 * DAY, C - 3 * DAY, INITIAL_CASH_KRW, model, capacity_verified=verified)
    out = run_backtest(day, hour, cfg, tmp_path / "runs-fixture", code_state=CODE,
                       settings_file=DEFAULT_SETTINGS_FILE, now=NOW)
    assert out.manifest["inputs"]["day"]["segment"] is None and out.manifest["inputs"]["hour"]["segment"] is None
    assert verify_run(out.dir, code_state=CODE).status == "OK"
    assert not (v.dir / "public" / "segment_manifest.json").exists()


# --- T5 / T16 leakage ---------------------------------------------------------------------------------------

def test_t5_t16_build_status_and_errors_carry_no_locked_values(tmp_path):
    v = build(tmp_path)
    no_secret(repr(v) + json.dumps(vault_status(v.dir)))
    errors = []
    for call in (lambda: open_h(v.dir), lambda: analyse(v.dir, "interim")):
        with pytest.raises(VaultError) as e:
            call()
        errors.append(str(e.value))
    evidence_all(v.dir)
    locked = v.dir / "locked" / "holdout_day.jsonl"
    original = locked.read_bytes()
    locked.write_bytes(original.replace(b"7777.77", b"7777.78", 1))
    with pytest.raises(VaultIntegrityError) as e:
        open_h(v.dir)
    errors.append(str(e.value))
    st = vault_status(v.dir)
    assert st["integrity"] == "FAIL"
    errors.append(json.dumps(st))
    locked.write_bytes(original)
    open_h(v.dir)
    with pytest.raises(VaultLockedError) as e:
        open_h(v.dir)
    errors.append(str(e.value))
    seal(v.dir, "202003")
    errors.append(json.dumps(vault_status(v.dir)))
    for text in errors:
        no_secret(text)


# --- T6 - T10 single use ----------------------------------------------------------------------------------------

def test_t6_open_once_then_refused(tmp_path):
    v = build(tmp_path)
    evidence_all(v.dir)
    assert vault_status(v.dir)["access"]["holdout_open"] == UNOPENED
    opened = open_h(v.dir)
    assert opened.vault_id == v.vault_id and len(opened.rows["day"]) == 30 and len(opened.rows["hour"]) == 720
    with pytest.raises(VaultLockedError):
        open_h(v.dir)
    assert vault_status(v.dir)["access"]["holdout_open"] == OPENED
    record = json.loads((v.dir / "access" / "holdout_open.json").read_text(encoding="utf-8"))
    assert record["vault_content_sha256"] == v.content_sha256 and record["caller"] == "tests"
    assert set(record["evidence"]) == {"confirmatory_results", "row9_strategy", "q12_done"}


def test_t7_failures_before_the_record_do_not_consume(tmp_path):
    v = build(tmp_path)
    access = v.dir / "access" / "holdout_open.json"
    with pytest.raises(VaultPreconditionError, match="evidence confirmatory_results"):
        open_h(v.dir)
    evidence_all(v.dir)
    with pytest.raises(VaultPreconditionError, match="preregistration/config"):
        open_h(v.dir, pre="d" * 64)
    with pytest.raises(VaultPreconditionError, match="64 lowercase hex"):
        open_h(v.dir, cfg="nothex")
    locked = v.dir / "locked" / "holdout_hour.jsonl"
    original = locked.read_bytes()
    locked.write_bytes(original + b"\n")
    with pytest.raises(VaultIntegrityError):
        open_h(v.dir)
    assert not access.exists()
    locked.write_bytes(original)
    assert len(open_h(v.dir).rows["day"]) == 30
    w = build(tmp_path, "bad-evidence-fixture")
    record_evidence(w.dir, "confirmatory_results", EV)
    record_evidence(w.dir, "row9_strategy", EV, detail=["M20"])
    (w.dir / "evidence" / "q12_done.json").write_bytes(b"{not json")
    with pytest.raises(VaultPreconditionError, match="q12_done is unreadable"):
        open_h(w.dir)
    assert vault_status(w.dir)["evidence_records"]["q12_done"] == RECORDED  # presence only (D16)
    assert not (w.dir / "access" / "holdout_open.json").exists()


class Crash(BaseException):
    pass


def test_t8_failure_after_the_record_consumes(tmp_path, monkeypatch):
    v = build(tmp_path)
    evidence_all(v.dir)

    def boom(*a, **k):
        raise RuntimeError("injected")

    monkeypatch.setattr(vmod, "_read_locked", boom)
    with pytest.raises(VaultIntegrityError, match="single use is consumed"):
        open_h(v.dir)
    monkeypatch.undo()
    with pytest.raises(VaultLockedError):
        open_h(v.dir)
    w = build(tmp_path, "crash-fixture")
    evidence_all(w.dir)

    def crash(*a, **k):
        raise Crash()

    monkeypatch.setattr(vmod, "_read_locked", crash)
    with pytest.raises(Crash):
        open_h(w.dir)
    monkeypatch.undo()
    assert vault_status(w.dir)["access"]["holdout_open"] == OPENED
    with pytest.raises(VaultLockedError):
        open_h(w.dir)


def test_t9_losing_the_exclusive_create_is_locked(tmp_path, monkeypatch):
    v = build(tmp_path)
    evidence_all(v.dir)
    open_h(v.dir)
    monkeypatch.setattr(vmod, "_record_present", lambda p: False)  # a racer passed the check before the record
    with pytest.raises(VaultLockedError):
        open_h(v.dir)
    assert [p.name for p in (v.dir / "access").iterdir()] == ["holdout_open.json"]


def test_t10_unreadable_record_counts_as_opened(tmp_path):
    v = build(tmp_path)
    evidence_all(v.dir)
    (v.dir / "access").mkdir()
    (v.dir / "access" / "holdout_open.json").write_bytes(b"")
    assert vault_status(v.dir)["access"]["holdout_open"] == RECORD_UNREADABLE
    with pytest.raises(VaultLockedError):
        open_h(v.dir)


# --- T11 / T17 / T19 existing vaults and identity ---------------------------------------------------------------

def test_t11_t17_identical_existing_keeps_state_and_refuses_differences(tmp_path):
    src = source(tmp_path / "src")
    v = build_vault(*src, spec(), tmp_path / "vault-fixture")
    sums_before = (v.dir / "SHA256SUMS.txt").read_bytes()
    evidence_all(v.dir)
    open_h(v.dir)
    seal(v.dir, "202003")
    before = tree_bytes(v.dir)
    again = build_vault(*src, spec(), tmp_path / "vault-fixture")
    assert again.status == ALREADY_SEALED_IDENTICAL and again.dir == v.dir
    assert again.state["access"]["holdout_open"] == OPENED
    assert tree_bytes(v.dir) == before  # (a) nothing written, (d) build_record kept
    # T17: content identity and sums never change with state
    assert again.content_sha256 == v.content_sha256 and (v.dir / "SHA256SUMS.txt").read_bytes() == sums_before
    assert vault_status(v.dir)["vault_content_sha256"] == v.content_sha256
    # (b) unexpected entries
    for stray in (v.dir / "stray.txt", v.dir / "public" / "extra.txt", v.dir / "locked" / "extra.jsonl"):
        stray.write_bytes(b"x")
        with pytest.raises(VaultExistsError):
            build_vault(*src, spec(), tmp_path / "vault-fixture")
        stray.unlink()
    # (e) forward month directory
    assert seal(v.dir, "202003").status == ALREADY_SEALED_IDENTICAL
    assert tree_bytes(v.dir) == before
    (v.dir / "locked_forward" / "forward_202003" / "extra.txt").write_bytes(b"x")
    with pytest.raises(VaultExistsError):
        seal(v.dir, "202003")
    (v.dir / "locked_forward" / "forward_202003" / "extra.txt").unlink()
    with pytest.raises(VaultExistsError):
        seal(v.dir, "202003", fwd_series(price=Decimal("5555.56")))
    # (c) a sealed byte differs
    child = v.dir / "public" / "day_src" / "bars_manifest.json"
    child.write_bytes(child.read_bytes() + b" ")
    with pytest.raises(VaultExistsError):
        build_vault(*src, spec(), tmp_path / "vault-fixture")
    assert (v.dir / "access" / "holdout_open.json").exists()


def test_t19_build_never_writes_access_or_evidence(tmp_path, monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError("build must not create records")

    monkeypatch.setattr(vmod, "_create_exclusive", forbidden)
    src = source(tmp_path / "src")
    v = build_vault(*src, spec(), tmp_path / "vault-fixture")
    assert build_vault(*src, spec(), tmp_path / "vault-fixture").status == ALREADY_SEALED_IDENTICAL
    assert not (v.dir / "access").exists() and not (v.dir / "evidence").exists()
    assert sorted(p.name for p in v.dir.iterdir()) == ["SHA256SUMS.txt", "build_record.json", "locked", "public",
                                                       "vault_manifest.json"]


# --- T12 evidence -----------------------------------------------------------------------------------------------

def test_t12_evidence_is_write_once(tmp_path):
    v = build(tmp_path)
    assert record_evidence(v.dir, "q12_done", EV) == RECORDED
    before = tree_bytes(v.dir)
    assert record_evidence(v.dir, "q12_done", EV) == ALREADY_RECORDED_IDENTICAL
    assert tree_bytes(v.dir) == before
    with pytest.raises(VaultExistsError):
        record_evidence(v.dir, "q12_done", "f" * 64)
    with pytest.raises(VaultPreconditionError):
        record_evidence(v.dir, "row9_strategy", EV)
    with pytest.raises(VaultPreconditionError):
        record_evidence(v.dir, "row9_strategy", EV, detail=[])
    with pytest.raises(VaultPreconditionError):
        record_evidence(v.dir, "confirmatory_results", EV, detail=["x"])
    with pytest.raises(VaultPreconditionError):
        record_evidence(v.dir, "unknown", EV)
    with pytest.raises(VaultPreconditionError):
        record_evidence(v.dir, "confirmatory_results", "ABC")
    doc = json.loads((v.dir / "evidence" / "q12_done.json").read_text(encoding="utf-8"))
    assert doc["vault_content_sha256"] == v.content_sha256 and doc["sha256"] == EV


# --- T13 provenance and roots -----------------------------------------------------------------------------------

def test_t13_real_roots_and_mixed_provenance_are_refused(tmp_path):
    with pytest.raises(VaultPreconditionError, match="real"):
        build_vault(*source(tmp_path / "real", kinds=("real", "real")), spec(), tmp_path / "vault-fixture")
    with pytest.raises(VaultPreconditionError, match="-fixture"):
        build_vault(*source(tmp_path / "plain"), spec(), tmp_path / "vault")
    with pytest.raises(VaultPreconditionError, match="different provenance"):
        build_vault(*source(tmp_path / "mixed", kinds=("fixture", "synthetic")), spec(), tmp_path / "vault-fixture")
    v = build(tmp_path)
    with pytest.raises(VaultPreconditionError, match="real"):
        seal(v.dir, "202003", fwd_series(kind="real"))
    d, _ = fwd_series(kind="synthetic")
    _, h = fwd_series(kind="fixture")
    with pytest.raises(VaultPreconditionError, match="different provenance"):
        seal(v.dir, "202003", (d, h))


# --- T14 seal ---------------------------------------------------------------------------------------------------

def test_t14_seal_windows(tmp_path):
    v = build(tmp_path)
    fwd = fwd_series()  # starts 2020-03-05: six daily bars end at or before L
    s = seal(v.dir, "202003", fwd)
    assert s.status == CREATED and s.bars == {"day": 21, "hour": 504}
    assert s.outside_window == {"day": len(fwd[0]) - 21, "hour": len(fwd[1]) - 504}
    no_secret(repr(s))
    with pytest.raises(VaultPreconditionError, match="before the month"):
        seal(v.dir, "202002", fwd)
    with pytest.raises(VaultPreconditionError, match="has not ended"):
        seal(v.dir, "202004", fwd_series(end=datetime(2020, 4, 20, tzinfo=UTC)))
    gap = fwd_series(end=datetime(2020, 8, 2, tzinfo=UTC),
                     skip=lambda t: datetime(2020, 4, 1, tzinfo=UTC) <= t < datetime(2020, 7, 1, tzinfo=UTC))
    with pytest.raises(VaultPreconditionError, match="no day bar"):
        seal(v.dir, "202005", gap)
    with pytest.raises(VaultPreconditionError, match="YYYYMM"):
        seal(v.dir, "2020-05", fwd)
    st = vault_status(v.dir)
    assert st["forward_months"] == {"202003": {"day": 21, "hour": 504}} and st["integrity"] == "PASS"


# --- T15 analysis -----------------------------------------------------------------------------------------------

def test_t15_open_analysis(tmp_path):
    v = build(tmp_path)
    evidence_all(v.dir)
    seal(v.dir, "202003")
    with pytest.raises(VaultPreconditionError, match="holdout must be opened"):
        analyse(v.dir, "interim")
    open_h(v.dir)
    with pytest.raises(VaultPreconditionError, match="202004 is not sealed"):
        analyse(v.dir, "interim")
    seal(v.dir, "202004")
    with pytest.raises(VaultPreconditionError, match="preregistration/config"):
        analyse(v.dir, "interim", pre="d" * 64)
    a = analyse(v.dir, "interim")
    assert a.analysis_end_utc == W_I and len(a.lookback["day"]) == 30
    assert len(a.forward["day"]) == 35 and len(a.forward["hour"]) == 35 * 24
    for iv in ("day", "hour"):
        assert all(L < b.end_utc <= W_I for b in a.forward[iv])
        assert max(b.end_utc for b in a.forward[iv]) == W_I
    with pytest.raises(VaultLockedError):
        analyse(v.dir, "interim")
    with pytest.raises(VaultPreconditionError, match="202005 is not sealed"):
        analyse(v.dir, "final")
    seal(v.dir, "202005")
    f = analyse(v.dir, "final")
    assert len(f.forward["day"]) == 70 and max(b.end_utc for b in f.forward["day"]) == W_F
    with pytest.raises(VaultLockedError):
        analyse(v.dir, "final")
    st = vault_status(v.dir)
    assert st["access"] == {"holdout_open": OPENED, "forward_interim": OPENED, "forward_final": OPENED}
    # a missing middle month refuses; an analysis without an end refuses
    w = build(tmp_path, "gap-fixture", sp=spec(forward_interim_end_utc=None))
    evidence_all(w.dir)
    open_h(w.dir)
    seal(w.dir, "202003")
    seal(w.dir, "202005")
    with pytest.raises(VaultPreconditionError, match="202004 is not sealed"):
        analyse(w.dir, "final")
    with pytest.raises(VaultPreconditionError, match="no end boundary"):
        analyse(w.dir, "interim")
    assert vault_status(w.dir)["access"]["forward_final"] == UNOPENED


# --- T18 spec -------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("change", [
    dict(confirmatory_data_end_utc=C + HOUR),
    dict(confirmatory_data_end_utc=C.replace(tzinfo=None)),
    dict(confirmatory_data_end_utc=H),
    dict(holdout_end_utc=L + DAY),
    dict(forward_interim_end_utc=L),
    dict(forward_interim_end_utc=W_F),
    dict(forward_final_end_utc=L - DAY),
    dict(preregistration_sha256="A" * 64),
    dict(config_sha256="b" * 63),
])
def test_t18_spec_validation(change):
    with pytest.raises(VaultPreconditionError):
        spec(**change)


def test_t18_spec_allows_disabled_analyses_and_round_trips():
    s = spec(forward_interim_end_utc=None, forward_final_end_utc=None)
    assert VaultSpec.from_dict(s.to_dict()) == s
    assert s.analysis_end("final") is None
    assert spec().to_dict()["locked_end_utc"] == "2020-03-11T00:00:00Z"


# --- T20 fixture end to end -------------------------------------------------------------------------------------

def test_t20_fixture_end_to_end(tmp_path):
    pulls = {iv: fixture_pull(tmp_path / "pulls", iv) for iv in ("day", "hour")}
    full = {iv: export_bars(p, tmp_path / "bars-fixture").dir for iv, p in pulls.items()}
    lk = datetime(2025, 11, 1, tzinfo=UTC)
    seg = export_segment(full["day"], full["hour"], lk - 3 * DAY, tmp_path / "seg-fixture")
    m = seg.plan.manifest
    day_in, hour_in = seg.dir / m["intervals"]["day"]["dir_name"], seg.dir / m["intervals"]["hour"]["dir_name"]
    c = datetime(2025, 9, 1, tzinfo=UTC)
    sp = VaultSpec(c, datetime(2025, 10, 15, tzinfo=UTC), lk, datetime(2025, 11, 20, tzinfo=UTC),
                   datetime(2025, 12, 10, tzinfo=UTC), PRE, CFG)
    v = build_vault(day_in, hour_in, sp, tmp_path / "vault-fixture")
    assert v.status == CREATED and v.state["integrity"] == "PASS" and v.state["provenance"] == "fixture"
    pub = v.dir / "public"
    s, _ = load_cost_settings()
    model, verified = cost_model(s, 25, "E0", INITIAL_CASH_KRW)
    cfg = RunConfig("sma20", datetime(2025, 6, 26, tzinfo=UTC), c - 3 * DAY, INITIAL_CASH_KRW, model,
                    capacity_verified=verified)
    out = run_backtest(pub / day_in.name, pub / hour_in.name, cfg, tmp_path / "runs-fixture", code_state=CODE,
                       settings_file=DEFAULT_SETTINGS_FILE, now=NOW)
    assert verify_run(out.dir, code_state=CODE).status == "OK"
    evidence_all(v.dir)
    opened = open_h(v.dir)
    assert all(c < x.bar.end_utc <= lk for x in opened.rows["hour"])
    with pytest.raises(VaultLockedError):
        open_h(v.dir)
    fwd = (load_bars(full["day"]), load_bars(full["hour"]))
    assert seal(v.dir, "202511", fwd).status == CREATED
    with pytest.raises(VaultPreconditionError, match="has not ended"):
        seal(v.dir, "202512", fwd)
    with pytest.raises(VaultPreconditionError, match="202512 is not sealed"):
        analyse(v.dir, "final")
    a = analyse(v.dir, "interim")
    assert a.forward["day"] and all(lk < b.end_utc <= datetime(2025, 11, 20, tzinfo=UTC) for b in a.forward["day"])
    with pytest.raises(VaultLockedError):
        analyse(v.dir, "interim")
    st = vault_status(v.dir)
    assert st["integrity"] == "PASS" and st["access"]["holdout_open"] == OPENED
    assert st["forward_months"]["202511"]["day"] > 0


# --- rollback regressions (R1-R4) and strengthened checks (R5) ------------------------------------------------------

def rewrite_bars_file(d: Path, body: bytes) -> None:
    """Replace a bars/1 file body and re-sign its manifest and sums (so load_bars reaches the rows)."""
    name = next(p.name for p in d.glob("bars_*.jsonl"))
    (d / name).write_bytes(body)
    m = json.loads((d / "bars_manifest.json").read_text(encoding="utf-8"))
    m["bars_sha256"] = hashlib.sha256(body).hexdigest()
    (d / "bars_manifest.json").write_bytes((json.dumps(m, sort_keys=True, indent=1) + "\n").encode())
    sums = "".join(f"{sha256_file(d / n)}  {n}\n" for n in sorted([name, "bars_manifest.json"]))
    (d / "SHA256SUMS.txt").write_text(sums, encoding="utf-8", newline="\n")


# D1, written out here (not derived from the module): the APIs, the five exceptions and the ten status constants.
D1_PUBLIC = {
    "VaultSpec", "build_vault", "vault_status", "record_evidence", "HistoricalHoldoutVault", "ForwardVault",
    "VaultError", "VaultLockedError", "VaultPreconditionError", "VaultIntegrityError", "VaultExistsError",
    "CREATED", "ALREADY_SEALED_IDENTICAL", "RECORDED", "ALREADY_RECORDED_IDENTICAL", "UNOPENED", "OPENED",
    "RECORD_UNREADABLE", "ABSENT", "PASS", "FAIL",
}


def test_r1_r8_public_api_is_exactly_the_d1_enumeration():
    assert len(vmod.__all__) == len(set(vmod.__all__)) and set(vmod.__all__) == D1_PUBLIC
    # every non-underscore module attribute is a D1 name (only the compiler's `annotations` feature flag is exempt)
    public_attrs = {n for n in vars(vmod) if not n.startswith("_")} - {"annotations"}
    assert public_attrs == D1_PUBLIC
    for name in ("load_bars", "BarSeries", "sha256_of", "Bar", "Path", "datetime", "json", "os",
                 "SCHEMA", "SEAL_SCHEMA", "ACCESS_SCHEMA", "VAULT_MANIFEST", "PUBLIC_DIR", "INTERVALS", "EVIDENCE_KINDS",
                 "HOLDOUT_EVAL", "EXCLUDED",
                 "VaultBuild", "HoldoutOpening", "LabeledBar", "ForwardSeal", "ForwardAnalysis", "content_payload"):
        assert not hasattr(vmod, name), name
    assert {n for n in vars(HistoricalHoldoutVault) if not n.startswith("_")} == {"open_once"}
    assert {n for n in vars(ForwardVault) if not n.startswith("_")} == {"seal", "open_analysis"}
    assert all(getattr(vmod, n) == n for n in D1_PUBLIC if n.isupper())  # status constants keep their values
    # returned objects keep their shape although their type names are private
    assert [f.name for f in dataclasses.fields(vmod._LabeledBar)] == ["label", "bar"]
    assert vmod._HOLDOUT_EVAL == "HOLDOUT_EVAL" and vmod._EXCLUDED == "EXCLUDED"


D7_ACCESS_KEYS = {"kind", "vault_content_sha256", "preregistration_sha256", "config_sha256", "evidence", "files",
                  "opened_at_utc", "caller"}


def test_r7_access_records_hold_exactly_the_d7_keys(tmp_path):
    v = build(tmp_path)
    evidence_all(v.dir)
    open_h(v.dir)
    seal(v.dir, "202003")
    seal(v.dir, "202004")
    analyse(v.dir, "interim")
    for kind in ("holdout_open", "forward_interim"):
        doc = json.loads((v.dir / "access" / f"{kind}.json").read_text(encoding="utf-8"))
        assert set(doc) == D7_ACCESS_KEYS, kind
        assert doc["kind"] == kind and doc["vault_content_sha256"] == v.content_sha256
        assert (doc["preregistration_sha256"], doc["config_sha256"]) == (PRE, CFG) and doc["caller"] == "tests"
        assert all(k not in doc for k in ("schema", "vault_id", "evidence_label"))
    holdout = json.loads((v.dir / "access" / "holdout_open.json").read_text(encoding="utf-8"))
    assert holdout["evidence"] == {"confirmatory_results": EV, "row9_strategy": EV, "q12_done": EV}
    assert set(holdout["files"]) == {"locked/holdout_day.jsonl", "locked/holdout_hour.jsonl"}
    st = vault_status(v.dir)["access"]
    assert st == {"holdout_open": OPENED, "forward_interim": OPENED, "forward_final": UNOPENED}


@pytest.mark.parametrize("mutate", [
    lambda d: {**d, "schema": "x"},  # an extra key
    lambda d: {k: v for k, v in d.items() if k != "caller"},  # a missing key
    lambda d: {**d, "kind": "forward_final"},  # wrong kind binding
    lambda d: {**d, "vault_content_sha256": "0" * 64},  # wrong vault binding
    lambda d: [d],  # not an object
])
def test_r7_record_state_is_fail_closed_and_still_locks(tmp_path, mutate):
    v = build(tmp_path)
    evidence_all(v.dir)
    open_h(v.dir)
    path = v.dir / "access" / "holdout_open.json"
    path.write_text(json.dumps(mutate(json.loads(path.read_text(encoding="utf-8")))), encoding="utf-8")
    assert vault_status(v.dir)["access"]["holdout_open"] == RECORD_UNREADABLE
    with pytest.raises(VaultLockedError):  # an unreadable or foreign record still counts as the one use
        open_h(v.dir)


def test_r2_identity_payloads_are_exactly_the_d6_fields(tmp_path):
    v = build(tmp_path)
    m = json.loads((v.dir / "vault_manifest.json").read_text(encoding="utf-8"))
    assert set(m) == {"schema", "market", "provenance", "spec", "intervals", "lineage", "evidence",
                      "vault_content_sha256", "vault_id"}
    for iv in ("day", "hour"):
        assert set(m["intervals"][iv]) == {"public_dir", "public_bars_sha256", "public_bars", "locked_sha256",
                                           "holdout_eval_bars", "excluded_bars"}
        assert set(m["lineage"][iv]) == {"input_bars_sha256", "input_bars", "input_bars_manifest_sha256"}
    payload = {k: m[k] for k in ("schema", "market", "provenance", "spec", "intervals")}
    assert sha256_of(payload) == m["vault_content_sha256"] == v.content_sha256
    s = seal(v.dir, "202003")
    doc = json.loads((s.dir / "seal.json").read_text(encoding="utf-8"))
    assert all(set(doc["intervals"][iv]) == {"sha256", "bars"} for iv in ("day", "hour"))
    fwd_payload = {"month": doc["month"], "vault_content_sha256": doc["vault_content_sha256"],
                   "intervals": doc["intervals"]}
    assert sha256_of(fwd_payload) == doc["forward_seal_content_sha256"] == s.content_sha256
    assert doc["schema"] == vmod._SEAL_SCHEMA  # kept in seal.json, outside the identity payload


def test_r3_input_failures_are_vault_errors_without_row_values(tmp_path):
    with pytest.raises(VaultPreconditionError, match="not a readable"):
        build_vault(tmp_path / "missing-day", tmp_path / "missing-hour", spec(), tmp_path / "vault-fixture")
    d, h = source(tmp_path / "broken")
    body = (d / "bars_day.jsonl").read_bytes().replace(LOCKED_TIME.encode(), b"2020-02-17T01:00:00Z", 1)
    rewrite_bars_file(d, body)
    with pytest.raises(DataIntegrityError, match="2020-02-17"):  # the dependency's own message quotes the row
        load_bars(d)
    with pytest.raises(VaultPreconditionError) as e:
        build_vault(d, h, spec(), tmp_path / "vault-fixture")
    assert "2020-02-17" not in str(e.value) and "DataIntegrityError" in str(e.value)
    no_secret(str(e.value))
    with pytest.raises(VaultPreconditionError, match="code_state"):
        build_vault(*source(tmp_path / "cs"), spec(), tmp_path / "cs-fixture", code_state={"x": object()})
    assert not (tmp_path / "cs-fixture").exists()
    v = build(tmp_path)
    day, hour = fwd_series()
    object.__setattr__(day, "_bars", day.bars[:-1])  # altered after build: verify() fails
    with pytest.raises(VaultPreconditionError, match="provenance hash"):
        ForwardVault(v.dir).seal(day, hour, "202003")


def test_r3_record_creation_failure_is_a_precondition_and_consumes_nothing(tmp_path, monkeypatch):
    v = build(tmp_path)
    evidence_all(v.dir)
    w = build(tmp_path, "ev-fixture")

    def no_link(src, dst):
        raise PermissionError("injected")

    monkeypatch.setattr(vmod._os, "link", no_link)
    with pytest.raises(VaultPreconditionError, match="exclusive record creation"):
        open_h(v.dir)
    with pytest.raises(VaultPreconditionError, match="exclusive record creation"):
        record_evidence(w.dir, "q12_done", EV)
    monkeypatch.undo()
    assert not (v.dir / "access" / "holdout_open.json").exists()
    assert vault_status(v.dir)["access"]["holdout_open"] == UNOPENED
    assert len(open_h(v.dir).rows["day"]) == 30
    assert record_evidence(w.dir, "q12_done", EV) == RECORDED


def test_r3_r5_failed_build_publishes_nothing_and_keeps_stale_tmp(tmp_path, monkeypatch):
    src = source(tmp_path / "src")
    out = tmp_path / "vault-fixture"
    stale = out / ".tmp-vault-earlier-crash"
    stale.mkdir(parents=True)
    (stale / "partial").write_bytes(b"x")
    real = vmod._atomic_write_bytes
    calls = []

    def flaky(path, data):
        calls.append(path)
        if len(calls) == 4:
            raise OSError("disk full (injected)")
        return real(path, data)

    monkeypatch.setattr(vmod, "_atomic_write_bytes", flaky)
    with pytest.raises(VaultPreconditionError, match="nothing was published"):
        build_vault(*src, spec(), out)
    assert [p.name for p in out.iterdir()] == [stale.name]  # no vault, no new tmp; the stale tmp is untouched
    monkeypatch.undo()
    v = build_vault(*src, spec(), out)
    assert v.status == CREATED and (stale / "partial").read_bytes() == b"x"


def test_r3_failure_after_the_forward_record_consumes(tmp_path, monkeypatch):
    v = build(tmp_path)
    evidence_all(v.dir)
    open_h(v.dir)
    seal(v.dir, "202003")
    seal(v.dir, "202004")

    def boom(*a, **k):
        raise RuntimeError("injected")

    monkeypatch.setattr(vmod, "_read_locked", boom)
    with pytest.raises(VaultIntegrityError, match="single use is consumed"):
        analyse(v.dir, "interim")
    monkeypatch.undo()
    with pytest.raises(VaultLockedError):
        analyse(v.dir, "interim")


def test_r4_status_returns_exactly_the_d16_keys(tmp_path):
    v = build(tmp_path)
    evidence_all(v.dir)
    open_h(v.dir)
    seal(v.dir, "202003")
    seal(v.dir, "202004")
    st = vault_status(v.dir)
    keys = {"vault_id", "vault_content_sha256", "provenance", "spec", "public_bars", "locked", "integrity", "access",
            "evidence_records", "forward_months"}
    assert set(st) == keys and st["integrity"] == "PASS"
    assert all(set(st["locked"][iv]) == {"holdout_eval_bars", "excluded_bars", "sha256"} for iv in ("day", "hour"))
    assert set(st["evidence_records"].values()) == {RECORDED}
    assert st["forward_months"]["202003"] == {"day": 21, "hour": 504}
    f = v.dir / "locked_forward" / "forward_202004" / "forward_day.jsonl"
    f.write_bytes(f.read_bytes() + b"\n")
    bad = vault_status(v.dir)
    assert set(bad) == keys and bad["integrity"] == "FAIL"
    assert bad["forward_months"]["202004"] == {"day": None, "hour": None}
    with pytest.raises(VaultIntegrityError):  # a corrupt sealed month refuses before the record
        analyse(v.dir, "interim")
    assert not (v.dir / "access" / "forward_interim.json").exists()
    assert vault_status(v.dir)["access"]["forward_interim"] == UNOPENED
    no_secret(json.dumps(bad))


def test_r5_analysis_window_uses_explicit_w_end_only(tmp_path):
    assert {f.name for f in dataclasses.fields(VaultSpec)} == {
        "confirmatory_data_end_utc", "holdout_end_utc", "locked_end_utc", "forward_interim_end_utc",
        "forward_final_end_utc", "preregistration_sha256", "config_sha256"}
    code = Path(vmod.__file__).read_text(encoding="utf-8")
    for token in ("relativedelta", "months=", "interim_months", "final_months", "days=30", "days=31", "days=365"):
        assert token not in code, token
    # W_end one day after L: one daily bar, no rounding to a month
    a = build(tmp_path, "a-fixture", sp=spec(forward_interim_end_utc=L + DAY, forward_final_end_utc=None))
    evidence_all(a.dir)
    open_h(a.dir)
    seal(a.dir, "202003")
    got = analyse(a.dir, "interim")
    assert [b.end_utc for b in got.forward["day"]] == [L + DAY] and len(got.forward["hour"]) == 24
    # W_end on the first of a month: that month is not needed (the month of W_end - 1 s is April)
    w = datetime(2020, 5, 1, tzinfo=UTC)
    b = build(tmp_path, "b-fixture", sp=spec(forward_interim_end_utc=w, forward_final_end_utc=None))
    evidence_all(b.dir)
    open_h(b.dir)
    seal(b.dir, "202003")
    seal(b.dir, "202004")
    got = analyse(b.dir, "interim")
    assert max(x.end_utc for x in got.forward["day"]) == w and len(got.forward["day"]) == (w - L) // DAY
    assert vmod._month_start(w - timedelta(seconds=1)) == datetime(2020, 4, 1, tzinfo=UTC)
