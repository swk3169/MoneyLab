"""BT-3e forward monthly risk check (docs/tasks/BT-3E/WORK_ORDER.md T1-T24). SYNTHETIC / NOT_EVIDENCE, offline.

Synthetic timeline (T0 = 2020-01-01): public end C = T0+100d, holdout end H = T0+130d, freeze L = T0+150d
(2020-05-30, mid-month). Daily and hourly prices zigzag around 100 before L. Forward prices start at 4321.00 and
rise 1 % a day, then crash to 20 % on T0+175d (2020-06-24): M20 holds through the crash (VIOLATION from 202006),
R5 is in cash (PASS). Forward prices contain "4321", which must never appear in any output.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from backtest_helpers import DAY, HOUR, T0, flat_bar, series

from moneylab.backtest import risk_check as rmod
from moneylab.backtest import vault as vmod
from moneylab.backtest.vault import (
    ALREADY_RECORDED_IDENTICAL,
    ALREADY_SEALED_IDENTICAL,
    COMPLETED,
    CONSUMED_NO_RESULT,
    PASS,
    RECORDED,
    UNCHECKED,
    VIOLATION,
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
    record_risk_policy,
    record_risk_strategies,
    risk_status,
    vault_status,
)
from moneylab.domain.bars import NOT_EVIDENCE, canonical_bar_rows, utc_iso
from moneylab.storage.atomic import sha256_file

C, H, L = T0 + 100 * DAY, T0 + 130 * DAY, T0 + 150 * DAY
W_I, W_F = T0 + 200 * DAY, T0 + 215 * DAY
PRE, CFG, EV = "a" * 64, "b" * 64, "e" * 64
CRASH_DAY = 175
ENGINE_ID = "moneylab.backtest.engine/gap-free-window-signal+bt3b-boundary+scenario-ref-time/1"
CAND = {"scenario": "E0", "initial_cash": "1000000", "fee_bps": 0, "kappa_bps": "0", "impact_bps": "0",
        "fill_substitution": "none", "capacity_verified": True}
POLICY = dict(preregistration_sha256=PRE, config_sha256=CFG, metric_id="MAX_DRAWDOWN_LOG", threshold_ratio="1.5",
              comparison_operator="gt", accumulation_mode="CUMULATIVE_FROM_L", window_mapping_id="ENGINE_WINDOW_BT3B",
              engine_semantics_id=ENGINE_ID, confirmatory_first_day=T0 + 25 * DAY,
              confirmatory_last_day=T0 + 97 * DAY, check_window_end_utc=datetime(2020, 8, 1, tzinfo=UTC),
              candidates={"M20": dict(CAND), "R5": dict(CAND)}, f_rule_sha256="f" * 64)
SECRETS = ("4321", "2020-06-1", "2020-06-2", "2020-07-", "mdd", "drawdown")

# the exact post-BT-3e public surface, written out here (not derived from the module)
PUBLIC_28 = {
    "VaultSpec", "build_vault", "vault_status", "record_evidence", "HistoricalHoldoutVault", "ForwardVault",
    "VaultError", "VaultLockedError", "VaultPreconditionError", "VaultIntegrityError", "VaultExistsError",
    "CREATED", "ALREADY_SEALED_IDENTICAL", "RECORDED", "ALREADY_RECORDED_IDENTICAL", "UNOPENED", "OPENED",
    "RECORD_UNREADABLE", "ABSENT", "PASS", "FAIL",
    "record_risk_policy", "record_risk_strategies", "risk_status",
    "UNCHECKED", "CONSUMED_NO_RESULT", "COMPLETED", "VIOLATION",
}


def price(d: int) -> Decimal:
    if d < 150:
        return Decimal(f"{100 + 10 * math.sin(2 * math.pi * d / 30):.2f}")
    if d < CRASH_DAY:
        return Decimal(f"{4321.00 * 1.01 ** (d - 150):.2f}")
    return Decimal(f"{0.2 * 4321.00 * 1.01 ** (CRASH_DAY - 1 - 150):.2f}")


def bars(first: int, last: int):
    daily = [flat_bar("day", T0 + d * DAY, price(d)) for d in range(first, last)]
    hourly = [flat_bar("hour", T0 + d * DAY + h * HOUR, price(d)) for d in range(first, last) for h in range(24)]
    return daily, hourly


def write_bars(root: Path, name: str, rows, kind: str = "fixture") -> Path:
    d = root / name
    d.mkdir(parents=True)
    interval = rows[0].interval
    data = canonical_bar_rows(rows)
    srt = sorted(rows, key=lambda b: b.start_utc)
    bars_file = f"bars_{interval}.jsonl"
    manifest = {"schema": "moneylab.backtest.bars/1", "evidence": NOT_EVIDENCE, "provenance": kind,
                "market": "KRW-BTC", "interval": interval, "bars": len(srt),
                "first_start": utc_iso(srt[0].start_utc), "last_start": utc_iso(srt[-1].start_utc),
                "bars_file": bars_file, "bars_sha256": hashlib.sha256(data).hexdigest(),
                "source_pull": {"pull_id": name}, "confirmation_rule": "hand written (tests)"}
    (d / bars_file).write_bytes(data)
    (d / "bars_manifest.json").write_bytes((json.dumps(manifest, sort_keys=True, indent=1) + "\n").encode())
    sums = "".join(f"{sha256_file(d / n)}  {n}\n" for n in sorted([bars_file, "bars_manifest.json"]))
    (d / "SHA256SUMS.txt").write_text(sums, encoding="utf-8", newline="\n")
    return d


def source(root: Path, kind: str = "fixture"):
    daily, hourly = bars(0, 150)
    return write_bars(root, "day_src", daily, kind), write_bars(root, "hour_src", hourly, kind)


FWD_DAILY, FWD_HOURLY = bars(150, 215)
FWD = (series(FWD_DAILY, "fixture"), series(FWD_HOURLY, "fixture"))
SPEC = VaultSpec(C, H, L, W_I, W_F, PRE, CFG)


def build(tmp: Path, name: str = "vault-fixture") -> Path:
    return build_vault(*source(tmp / f"src-{name}"), SPEC, tmp / name).dir


def evidence_all(v: Path) -> None:
    record_evidence(v, "confirmatory_results", EV)
    record_evidence(v, "row9_strategy", EV, detail=["M20", "R5"])
    record_evidence(v, "q12_done", EV)


def open_h(v: Path):
    return HistoricalHoldoutVault(v).open_once(preregistration_sha256=PRE, config_sha256=CFG, caller="tests")


def bind_f(v: Path, strategies=("M20", "R5"), basis: str = "c" * 64):
    return record_risk_strategies(v, strategies=list(strategies), basis_sha256=basis, preregistration_sha256=PRE,
                                  config_sha256=CFG)


def ready(tmp: Path, name: str = "vault-fixture", *, policy=None, strategies=("M20", "R5"),
          months=("202005", "202006", "202007")) -> Path:
    v = build(tmp, name)
    assert record_risk_policy(v, **(policy or POLICY)) == RECORDED
    evidence_all(v)
    open_h(v)
    assert bind_f(v, strategies) == RECORDED
    for mo in months:
        ForwardVault(v).seal(*FWD, mo)
    return v


def check(v: Path, month: str, pre: str = PRE, cfg: str = CFG):
    return ForwardVault(v).check_risk(month, preregistration_sha256=pre, config_sha256=cfg, caller="tests")


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def no_secret(text: str) -> None:
    for s in SECRETS:
        assert s not in text, s


# --- T1 / T2 public surface ------------------------------------------------------------------------------------

def test_t1_vault_public_surface_is_exactly_28_names():
    assert len(vmod.__all__) == 28 and set(vmod.__all__) == PUBLIC_28
    assert {n for n in vars(vmod) if not n.startswith("_")} - {"annotations"} == PUBLIC_28
    assert {n for n in vars(ForwardVault) if not n.startswith("_")} == {"seal", "open_analysis", "check_risk"}
    assert (vmod.UNCHECKED, vmod.CONSUMED_NO_RESULT, vmod.COMPLETED, vmod.VIOLATION) == \
        ("UNCHECKED", "CONSUMED_NO_RESULT", "COMPLETED", "VIOLATION")


def test_t2_risk_check_has_no_public_api():
    assert rmod.__all__ == []
    assert {n for n in vars(rmod) if not n.startswith("_")} == {"annotations"}


# --- T3 / T4 policy values ------------------------------------------------------------------------------------

@pytest.mark.parametrize("key", sorted(POLICY))
def test_t3_every_policy_value_is_required(tmp_path, key):
    v = build(tmp_path)
    args = {k: val for k, val in POLICY.items() if k != key}
    with pytest.raises(VaultPreconditionError, match="no default"):
        record_risk_policy(v, **args)
    assert not (v / "evidence" / "risk_policy.json").exists()


@pytest.mark.parametrize("change", [
    dict(threshold_ratio=1.5), dict(threshold_ratio="0"), dict(threshold_ratio="x"),
    dict(confirmatory_first_day=T0 + 25 * DAY + HOUR), dict(check_window_end_utc="2020-08-01"),
    dict(candidates={}), dict(candidates={"M20": {**CAND, "fee_bps": 7}}), dict(candidates={"M20": {**CAND, "extra": 1}}),
    dict(candidates={"M20": {k: val for k, val in CAND.items() if k != "kappa_bps"}}),
    dict(candidates={"M20": {**CAND, "initial_cash": 1000000}}), dict(candidates={"M20": {**CAND, "capacity_verified": 1}}),
    dict(f_rule_sha256="nothex"),
])
def test_t3_malformed_policy_values_are_refused(tmp_path, change):
    v = build(tmp_path)
    with pytest.raises(VaultPreconditionError):
        record_risk_policy(v, **{**POLICY, **change})
    assert not (v / "evidence" / "risk_policy.json").exists()


@pytest.mark.parametrize("change", [
    dict(metric_id="MAX_DRAWDOWN"), dict(window_mapping_id="CALENDAR"), dict(comparison_operator="lt"),
    dict(accumulation_mode="ROLLING"), dict(engine_semantics_id="other"),
    dict(candidates={"M20": {**CAND, "scenario": "E9"}}), dict(candidates={"M20": {**CAND, "fill_substitution": "x"}}),
    dict(candidates={"M99": dict(CAND)}),
])
def test_t4_unsupported_enums_and_engine_identity_are_refused(tmp_path, change):
    v = build(tmp_path)
    with pytest.raises(VaultPreconditionError):
        record_risk_policy(v, **{**POLICY, **change})


# --- T5 - T8 binding order and immutability ------------------------------------------------------------------

def test_t5_policy_after_holdout_is_refused_and_risk_stays_unavailable(tmp_path):
    v = build(tmp_path)
    evidence_all(v)
    open_h(v)
    with pytest.raises(VaultPreconditionError, match="before the historical holdout"):
        record_risk_policy(v, **POLICY)
    with pytest.raises(VaultPreconditionError, match="risk policy is not recorded"):
        bind_f(v)
    ForwardVault(v).seal(*FWD, "202005")
    with pytest.raises(VaultPreconditionError, match="risk policy is not recorded"):
        check(v, "202005")


def test_t6_realized_f_timing(tmp_path):
    v = build(tmp_path)
    record_risk_policy(v, **POLICY)
    with pytest.raises(VaultPreconditionError, match="after the holdout"):
        bind_f(v)
    evidence_all(v)
    open_h(v)
    for mo in ("202005", "202006", "202007"):
        ForwardVault(v).seal(*FWD, mo)
    ForwardVault(v).open_analysis("interim", preregistration_sha256=PRE, config_sha256=CFG)
    with pytest.raises(VaultPreconditionError, match="before any forward access"):
        bind_f(v)
    w = build(tmp_path, "w-fixture")
    record_risk_policy(w, **POLICY)
    evidence_all(w)
    open_h(w)
    (w / "access" / "risk_202005.json").write_bytes(b"{}")
    with pytest.raises(VaultPreconditionError, match="before any forward access"):
        bind_f(w)


@pytest.mark.parametrize("strategies, basis", [
    (["R5", "M20"], "c" * 64), (["M20", "M20"], "c" * 64), ([], "c" * 64), (["M60"], "c" * 64), (["M20"], "xyz"),
])
def test_t7_realized_f_must_be_canonical(tmp_path, strategies, basis):
    v = build(tmp_path)
    record_risk_policy(v, **POLICY)
    evidence_all(v)
    open_h(v)
    with pytest.raises(VaultPreconditionError):
        bind_f(v, strategies, basis)
    assert not (v / "evidence" / "risk_strategies.json").exists()


def test_t8_policy_and_f_are_write_once(tmp_path):
    v = build(tmp_path)
    assert record_risk_policy(v, **POLICY) == RECORDED
    before = (v / "evidence" / "risk_policy.json").read_bytes()
    assert record_risk_policy(v, **POLICY) == ALREADY_RECORDED_IDENTICAL
    assert (v / "evidence" / "risk_policy.json").read_bytes() == before
    with pytest.raises(VaultExistsError):
        record_risk_policy(v, **{**POLICY, "threshold_ratio": "2"})
    evidence_all(v)
    open_h(v)
    assert bind_f(v) == RECORDED
    assert bind_f(v) == ALREADY_RECORDED_IDENTICAL
    with pytest.raises(VaultExistsError):
        bind_f(v, ("M20",))


# --- T9 - T12 preconditions -----------------------------------------------------------------------------------

def _tamper(path: Path, change) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    change(doc)
    path.write_text(json.dumps(doc, sort_keys=True, indent=1) + "\n", encoding="utf-8")


def test_t9a_preregistration_mismatch(tmp_path):
    v = ready(tmp_path)
    with pytest.raises(VaultPreconditionError, match="preregistration/config"):
        check(v, "202005", pre="d" * 64)
    assert not (v / "access" / "risk_202005.json").exists()


def test_t9b_top_level_config_mismatch(tmp_path):
    v = ready(tmp_path)
    with pytest.raises(VaultPreconditionError, match="preregistration/config"):
        check(v, "202005", cfg="d" * 64)
    assert not (v / "access" / "risk_202005.json").exists()


@pytest.mark.parametrize("label, target, change", [
    ("c_policy_vault_sha", "risk_policy.json", lambda d: d.update(vault_content_sha256="0" * 64)),
    ("d_f_policy_sha", "risk_strategies.json", lambda d: d.update(risk_policy_sha256="0" * 64)),
    ("e_candidate_hash_substituted", "risk_policy.json",
     lambda d: d["candidates"]["M20"].update(config_sha256="0" * 64)),
    ("f_candidate_settings_changed_hash_kept", "risk_policy.json",
     lambda d: d["candidates"]["M20"].update(initial_cash="2000000")),
])
def test_t9cdef_record_identity_mismatch_does_not_consume(tmp_path, label, target, change):
    v = ready(tmp_path)
    _tamper(v / "evidence" / target, change)
    with pytest.raises(VaultPreconditionError):
        check(v, "202005")
    assert not (v / "access" / "risk_202005.json").exists(), label
    assert risk_status(v)["integrity"] == "FAIL"


def _fields(**over):
    args = {k: val for k, val in POLICY.items()
            if k not in ("preregistration_sha256", "config_sha256", "f_rule_sha256")}
    args.update(over)
    return rmod._policy_record_fields(**args, public_end=C)


def test_t9g_candidate_config_identity_is_date_independent():
    a = _fields()["candidates"]
    b = _fields(confirmatory_first_day=T0 + 30 * DAY, confirmatory_last_day=T0 + 90 * DAY)["candidates"]
    assert a["M20"]["config_sha256"] == b["M20"]["config_sha256"] == a["R5"]["config_sha256"]
    expected = hashlib.sha256(json.dumps(CAND, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False).encode("utf-8")).hexdigest()
    assert a["M20"]["config_sha256"] == expected  # exactly the seven settings: no strategy id, no dates
    for key, value in (("scenario", "E1"), ("initial_cash", "2000000"), ("fee_bps", 5), ("kappa_bps", "1"),
                       ("impact_bps", "1"), ("fill_substitution", "prereg_6_3"), ("capacity_verified", False)):
        changed = _fields(candidates={"M20": {**CAND, key: value}})["candidates"]["M20"]["config_sha256"]
        assert changed != expected, key


def test_t10_month_eligibility(tmp_path):
    v = ready(tmp_path, months=("202005", "202007"))
    with pytest.raises(VaultPreconditionError, match="before the month"):
        check(v, "202004")
    with pytest.raises(VaultPreconditionError, match="check_window_end_utc"):
        check(v, "202008")
    with pytest.raises(VaultPreconditionError, match="202006 is not sealed"):
        check(v, "202007")  # cumulative: every month from month(L) must be sealed
    assert not list((v / "access").glob("risk_*"))


# MONTH_ONLY (ERRATA-001): target 202007 -> F = 2020-06-29, n_max = 21 (M20), T_day = 2020-06-09, T_hour = F,
# T_req = T_day. Required forward lookback: 202006 (next = 07-01 > T_req). 202005 (next = 06-01) is irrelevant.
MONTH_ONLY = {**POLICY, "accumulation_mode": "MONTH_ONLY"}


def test_t10_month_only_lookback_bounds():
    policy = rmod._policy_from_fields(_fields(accumulation_mode="MONTH_ONLY"), C)
    t_day, t_hour, t_req = rmod._month_only_lookback(policy, ["M20", "R5"], datetime(2020, 7, 1, tzinfo=UTC),
                                                     datetime(2020, 8, 1, tzinfo=UTC))
    assert (t_day, t_hour, t_req) == (datetime(2020, 6, 9, tzinfo=UTC), datetime(2020, 6, 29, tzinfo=UTC),
                                      datetime(2020, 6, 9, tzinfo=UTC))


def test_t10a_d_required_lookback_present_irrelevant_month_absent(tmp_path):
    v = ready(tmp_path, policy=MONTH_ONLY, months=("202006", "202007"))  # 202005 absent and irrelevant
    # July alone starts after the 06-24 crash (flat prices): month-only evaluation does not accumulate June
    assert check(v, "202007") == {"M20": PASS, "R5": PASS}
    files = json.loads((v / "access" / "risk_202007.json").read_text(encoding="utf-8"))["files"]
    assert {p.split("/")[1] for p in files if p.startswith("locked_forward/")} == {"forward_202006", "forward_202007"}


def test_t10b_f_required_lookback_absent_is_refused_not_skipped(tmp_path, monkeypatch):
    v = ready(tmp_path, policy=MONTH_ONLY, months=("202005", "202007"))  # required 202006 absent
    called = []
    monkeypatch.setattr(vmod, "_risk_evaluate", lambda *a, **k: called.append(1))
    with pytest.raises(VaultPreconditionError, match="202006 is not sealed"):
        check(v, "202007")
    assert called == [] and not (v / "access" / "risk_202007.json").exists()


def test_t10c_required_lookback_corrupt_is_refused_before_consumption(tmp_path):
    v = ready(tmp_path, policy=MONTH_ONLY, months=("202006", "202007"))
    f = v / "locked_forward" / "forward_202006" / "forward_day.jsonl"
    f.write_bytes(f.read_bytes() + b"\n")
    with pytest.raises(VaultIntegrityError):
        check(v, "202007")
    assert not (v / "access" / "risk_202007.json").exists()


def test_t10e_irrelevant_month_present_is_neither_touched_nor_listed(tmp_path, monkeypatch):
    v = ready(tmp_path, policy=MONTH_ONLY)  # 202005, 202006, 202007 all sealed
    seals_loaded, files_read = [], []
    real_seal, real_read = vmod._load_seal, vmod._read_locked
    monkeypatch.setattr(vmod, "_load_seal", lambda view, m: (seals_loaded.append(m.month), real_seal(view, m))[1])
    monkeypatch.setattr(vmod, "_read_locked", lambda path, *a: (files_read.append(path.as_posix()),
                                                                 real_read(path, *a))[1])
    decisions = check(v, "202007")
    assert 5 not in seals_loaded and not any("forward_202005" in p for p in files_read)
    files = json.loads((v / "access" / "risk_202007.json").read_text(encoding="utf-8"))["files"]
    assert not any("forward_202005" in p for p in files)
    w = ready(tmp_path, "w-fixture", policy=MONTH_ONLY, months=("202006", "202007"))
    assert decisions == check(w, "202007")  # the irrelevant month does not change the result


def test_t10_month_only_first_month_needs_no_forward_lookback(tmp_path):
    v = ready(tmp_path, policy=MONTH_ONLY, months=("202005",))
    assert check(v, "202005") == {"M20": PASS, "R5": PASS}


def test_t11_confirmatory_reference_is_recomputed_internally(tmp_path):
    params = set(inspect.signature(ForwardVault.check_risk).parameters)
    assert params == {"self", "month", "preregistration_sha256", "config_sha256", "caller"}
    assert not any("mdd" in p or "reference" in p for p in inspect.signature(record_risk_policy).parameters)
    v = ready(tmp_path)
    pub = next((v / "public").glob("day_*")) / "bars_day.jsonl"
    pub.write_bytes(pub.read_bytes().replace(b'"close":"100.00"', b'"close":"100.01"', 1))
    with pytest.raises(VaultIntegrityError):
        check(v, "202005")
    assert not (v / "access" / "risk_202005.json").exists()


def test_t12_confirmatory_interval_must_end_inside_the_public_boundary(tmp_path):
    v = build(tmp_path)
    with pytest.raises(VaultPreconditionError, match="public boundary"):
        record_risk_policy(v, **{**POLICY, "confirmatory_last_day": T0 + 98 * DAY})


# --- T13 - T19 consumption ------------------------------------------------------------------------------------

def test_t13_failure_after_the_access_record_consumes(tmp_path, monkeypatch):
    v = ready(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("injected")

    monkeypatch.setattr(vmod, "_read_locked", boom)
    with pytest.raises(VaultIntegrityError, match="single use is consumed"):
        check(v, "202005")
    monkeypatch.undo()
    assert risk_status(v)["months"]["202005"] == {"state": CONSUMED_NO_RESULT, "decisions": None}


class Crash(BaseException):
    pass


def test_t14_base_exception_after_the_access_record_consumes(tmp_path, monkeypatch):
    v = ready(tmp_path)

    def crash(*a, **k):
        raise Crash()

    monkeypatch.setattr(vmod, "_read_locked", crash)
    with pytest.raises(Crash):
        check(v, "202005")
    monkeypatch.undo()
    assert (v / "access" / "risk_202005.json").exists()
    with pytest.raises(VaultLockedError):
        check(v, "202005")


def test_t15_losing_the_exclusive_create_is_locked(tmp_path, monkeypatch):
    v = ready(tmp_path)
    (v / "access" / "risk_202005.json").write_bytes(b"{}")
    real = vmod._record_present
    monkeypatch.setattr(vmod, "_record_present", lambda p: False if p.name.startswith("risk_") else real(p))
    with pytest.raises(VaultLockedError):
        check(v, "202005")
    assert (v / "access" / "risk_202005.json").read_bytes() == b"{}"


def test_t16_consumed_no_result_is_never_retried(tmp_path, monkeypatch):
    v = ready(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("injected")

    monkeypatch.setattr(vmod, "_risk_evaluate", boom)
    with pytest.raises(VaultIntegrityError):
        check(v, "202005")
    monkeypatch.undo()
    reads = []
    monkeypatch.setattr(vmod, "_read_locked", lambda *a, **k: reads.append(1))
    with pytest.raises(VaultLockedError):
        check(v, "202005")
    assert reads == []


def test_t17_result_without_access_is_an_integrity_failure(tmp_path):
    v = ready(tmp_path)
    (v / "access" / "risk_202005.result.json").write_bytes(b"{}")
    st = risk_status(v)
    assert st["integrity"] == "FAIL" and st["months"]["202005"]["state"] == UNCHECKED
    with pytest.raises(VaultIntegrityError, match="without its access record"):
        check(v, "202005")


def test_t18_malformed_state_fails_closed(tmp_path):
    v = ready(tmp_path)
    p = v / "evidence" / "risk_policy.json"
    good = p.read_bytes()
    p.write_bytes(b"{bad")
    with pytest.raises(VaultPreconditionError, match="risk policy is unreadable"):
        check(v, "202005")
    assert risk_status(v)["integrity"] == "FAIL"
    p.write_bytes(good)
    s = v / "evidence" / "risk_strategies.json"
    s.write_text(json.dumps({**json.loads(s.read_text(encoding="utf-8")), "extra": 1}), encoding="utf-8")
    with pytest.raises(VaultPreconditionError, match="realized strategy set is unreadable"):
        check(v, "202005")
    w = ready(tmp_path, "w-fixture")
    (w / "access" / "risk_202006.json").write_bytes(b"[]")
    with pytest.raises(VaultLockedError):
        check(w, "202006")
    assert risk_status(w)["months"]["202006"]["state"] == CONSUMED_NO_RESULT
    assert risk_status(w)["integrity"] == "FAIL"
    check(w, "202005")
    (w / "access" / "risk_202005.result.json").write_bytes(b'{"kind": "risk_result"}')
    assert risk_status(w)["months"]["202005"] == {"state": CONSUMED_NO_RESULT, "decisions": None}


def test_t19_second_check_of_a_completed_month_is_locked(tmp_path, monkeypatch):
    v = ready(tmp_path)
    check(v, "202005")
    reads = []
    monkeypatch.setattr(vmod, "_read_locked", lambda *a, **k: reads.append(1))
    with pytest.raises(VaultLockedError):
        check(v, "202005")
    assert reads == []
    assert risk_status(v)["months"]["202005"]["state"] == COMPLETED


# --- T20 / T21 decisions --------------------------------------------------------------------------------------

def test_t20_deterministic_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(vmod, "_now", lambda: "2026-10-17T00:00:00Z")
    a, b = ready(tmp_path, "a-fixture"), ready(tmp_path, "b-fixture")
    assert check(a, "202005") == check(b, "202005") == {"M20": PASS, "R5": PASS}
    ra = (a / "access" / "risk_202005.result.json").read_bytes()
    assert ra == (b / "access" / "risk_202005.result.json").read_bytes()
    doc = json.loads(ra)
    assert set(doc) == {"kind", "month", "access_record_sha256", "risk_policy_sha256", "risk_strategies_sha256",
                        "decisions"}
    assert doc["access_record_sha256"] == sha256_file(a / "access" / "risk_202005.json")
    st = risk_status(a)
    assert st == {"policy": RECORDED, "strategies": RECORDED, "integrity": "PASS",
                  "months": {"202005": {"state": COMPLETED, "decisions": {"M20": PASS, "R5": PASS}}}}


def test_t21_deterministic_mixed_violation(tmp_path):
    v = ready(tmp_path)
    assert check(v, "202006") == {"M20": VIOLATION, "R5": PASS}
    assert check(v, "202007") == {"M20": VIOLATION, "R5": PASS}  # later months stay checkable (E10)
    w = ready(tmp_path, "single-fixture", strategies=("R5",))
    assert check(w, "202006") == {"R5": PASS}


# --- T22 non-disclosure ---------------------------------------------------------------------------------------

def test_t22_outputs_records_status_and_errors_disclose_nothing(tmp_path, monkeypatch):
    v = ready(tmp_path)
    texts = [json.dumps(check(v, "202006")), json.dumps(risk_status(v))]
    for name in ("risk_policy.json", "risk_strategies.json"):
        texts.append((v / "evidence" / name).read_text(encoding="utf-8"))
    for p in (v / "access").glob("risk_*"):
        texts.append(p.read_text(encoding="utf-8"))
    acc = json.loads((v / "access" / "risk_202006.json").read_text(encoding="utf-8"))
    assert set(acc) == {"kind", "month", "vault_content_sha256", "risk_policy_sha256", "risk_strategies_sha256",
                        "preregistration_sha256", "config_sha256", "files", "checked_at_utc", "caller"}
    pol = json.loads((v / "evidence" / "risk_policy.json").read_text(encoding="utf-8"))
    assert set(pol) == {"kind", "vault_content_sha256", "preregistration_sha256", "config_sha256", "metric_id",
                        "threshold_ratio", "comparison_operator", "accumulation_mode", "window_mapping_id",
                        "engine_semantics_id", "confirmatory_first_day", "confirmatory_last_day",
                        "check_window_end_utc", "candidates", "f_rule_sha256"}
    assert set(json.loads((v / "evidence" / "risk_strategies.json").read_text(encoding="utf-8"))) == \
        {"kind", "vault_content_sha256", "risk_policy_sha256", "strategies", "basis_sha256"}

    def boom(*a, **k):
        raise RuntimeError("4321.00 at 2020-06-15T00:00:00Z")

    monkeypatch.setattr(vmod, "_read_locked", boom)
    for call in (lambda: check(v, "202007"), lambda: check(v, "202006"), lambda: check(v, "202004")):
        with pytest.raises(VaultError) as e:
            call()
        texts.append(str(e.value))
    for t in texts:
        no_secret(t)


# --- T23 provenance, vault_status and D14 -----------------------------------------------------------------------

def test_t23_real_refused_vault_status_and_identical_unchanged(tmp_path):
    with pytest.raises(VaultError, match="real"):
        build_vault(*source(tmp_path / "real", kind="real"), SPEC, tmp_path / "real-fixture")
    src = source(tmp_path / "src")
    v = build_vault(*src, SPEC, tmp_path / "vault-fixture").dir
    record_risk_policy(v, **POLICY)
    evidence_all(v)
    open_h(v)
    bind_f(v)
    ForwardVault(v).seal(*FWD, "202005")
    check(v, "202005")
    st = vault_status(v)
    assert set(st) == {"vault_id", "vault_content_sha256", "provenance", "spec", "public_bars", "locked", "integrity",
                       "access", "evidence_records", "forward_months"}
    assert set(st["evidence_records"]) == {"confirmatory_results", "row9_strategy", "q12_done"}
    assert set(st["access"]) == {"holdout_open", "forward_interim", "forward_final"} and st["integrity"] == "PASS"
    before = tree_bytes(v)
    again = build_vault(*src, SPEC, tmp_path / "vault-fixture")
    assert again.status == ALREADY_SEALED_IDENTICAL and tree_bytes(v) == before


# --- T24 BT-3D regression -------------------------------------------------------------------------------------

def test_t24_bt3d_flows_unchanged_alongside_risk_records(tmp_path):
    v = ready(tmp_path)
    check(v, "202005")
    with pytest.raises(VaultLockedError):
        open_h(v)  # the holdout stays single-use
    analysis = ForwardVault(v).open_analysis("interim", preregistration_sha256=PRE, config_sha256=CFG)
    assert all(L < b.end_utc <= W_I for b in analysis.forward["day"])
    assert vault_status(v)["access"] == {"holdout_open": "OPENED", "forward_interim": "OPENED",
                                         "forward_final": "UNOPENED"}
