"""ECON-SCREEN-V06-01: economic screening of the four v0.6 primary rules (BT-5S; Work Order
docs/tasks/ECON-SCREEN-V06-01-IMPL, preregistration docs/research_econ_screen_v06_01_preregistration.md).

Evidence level of a real run: L1_SCREENING / NOT_CONFIRMATORY. Fixture and synthetic runs are
SYNTHETIC / NOT_EVIDENCE. No p-value, no V0 futility test and no verdict is computed here.

Pieces (the provider side, pull checks and bar export, lives in providers/upbit/bar_export.py and the
glue in cli.py; this module reads no provider and nothing that can reach the network):
  LOCKED_SPEC         the preregistered values (rules, scenarios, fees, capitals, B1, quality, sample, flag)
  EconScreenPermit    study-only admission of provenance "real" bars. It is issued only when the study,
                      spec, preregistration hashes, approved pull identities, requested range, code state
                      (real mode: clean) and output root all match. The code checks that these values are
                      consistent; it does not authenticate any approval message and it is not a security
                      boundary. Without a permit the general "real is refused before BT-5" paths are unchanged.
  pull_stage          Q1 (candles-verify), Q6 (conflicting duplicates, invalid values; one occurrence is
                      INVALID) and the collection conditions, before any bar is built
  bar_quality         Q2, Q3, Q4, Q7 on the exported bars and the evaluation-period condition
  run_matrix          rules x scenarios x fees x capitals with the existing engine and metrics
  screen_flags        SCREEN_FLAG_PASS / SCREEN_FLAG_NOT_MET / SCREEN_NOT_EVALUABLE (preregistration 9)
  recovery_days       new metric: days from the first MDD trough until the level regains the peak before it
  measure             synthetic resource measurement (stdout only, no files)

Output directories are written under a temporary name and renamed when complete. A failure leaves the
temporary directory and every file already written in place; nothing is deleted, repaired or retried.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
import tracemalloc
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

from moneylab.backtest import metrics as bt_metrics
from moneylab.backtest.benchmarks import alignment, compare, leg_cost_logs, ledger_positions, market_log_returns
from moneylab.backtest.code_state import code_state_problems
from moneylab.backtest.cost_analysis import cost_analysis
from moneylab.backtest.data import BarSeries, provenance_for
from moneylab.backtest.performance import exposure, max_drawdown_log, mean, value
from moneylab.backtest.portfolio import BacktestResult, RunConfig, simulate
from moneylab.backtest.round_trips import pair_round_trips, round_trip_report
from moneylab.backtest.settings import cost_model, load_cost_settings, settings_hashes
from moneylab.backtest.yearly import yearly_report
from moneylab.domain.bars import NOT_EVIDENCE, Bar, utc_iso
from moneylab.storage.atomic import atomic_write_bytes, sha256_file

STUDY_ID = "ECON-SCREEN-V06-01"
SCHEMA = "moneylab.econ_screen/1"
PREREGISTRATION_PATH = "docs/research_econ_screen_v06_01_preregistration.md"
PREREGISTRATION_SHA256 = "2ff766fa8e60adbc107b1ffe9ae4df30c455b616cd5345154704ff928b74705d"
REAL_ROOT_NAME = "econ_screen_v06_01"
FIXTURE_SUFFIX = "-fixture"
EVIDENCE_REAL = "L1_SCREENING / NOT_CONFIRMATORY"
MODES = ("real", "fixture")
PASS, INVALID, NOT_EVALUATED = "PASS", "INVALID", "NOT_EVALUATED"
FLAG_PASS, FLAG_NOT_MET, FLAG_NOT_EVALUABLE = "SCREEN_FLAG_PASS", "SCREEN_FLAG_NOT_MET", "SCREEN_NOT_EVALUABLE"
REPORT_ONLY_CHECKS = ("Q5", "Q8", "Q11", "Q12", "Q13")
SUMS_FILE = "SHA256SUMS.txt"
DAY, HOUR = timedelta(days=1), timedelta(hours=1)


class EconScreenError(ValueError):
    """The study refuses to go on (spec, permit, order of checks, inconsistent prepare or run inputs)."""


class PermitError(EconScreenError):
    """A permit cannot be issued or does not admit the given input."""


class ScreenComputationError(EconScreenError):
    """A computation produced a state the preregistration calls a calculation error (section 11)."""


# --- spec -----------------------------------------------------------------------------------------------

def _utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


@dataclass(frozen=True)
class ScreenSpec:
    market: str
    requested_start: datetime
    requested_end: datetime  # exclusive; also G_end
    warmup_days: int
    rules: tuple[str, ...]
    scenarios: tuple[str, ...]
    fees_bps: tuple[int, ...]
    capitals_krw: tuple[Decimal, ...]
    base_scenario: str
    base_fee_bps: int
    base_capital_krw: Decimal
    b1_draws: int
    seed: int
    q2_max: Fraction
    q3_max: Fraction
    q4_day_run: int
    q4_hour_run: int
    q4_max_events: int
    q7_max: Fraction
    min_eval_days: int
    min_round_trips: int
    min_positive_year_ratio: Fraction

    @property
    def last_signal_day(self) -> datetime:
        """E = requested_end - 3 days, so that G = [F + 2, E + 3) ends at requested_end."""
        return self.requested_end - 3 * DAY

    def first_signal_day(self, d0: datetime) -> datetime:
        return d0 + self.warmup_days * DAY

    def g_start(self, d0: datetime) -> datetime:
        return self.first_signal_day(d0) + 2 * DAY

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market, "requested_start": utc_iso(self.requested_start),
            "requested_end": utc_iso(self.requested_end), "warmup_days": self.warmup_days,
            "rules": list(self.rules), "scenarios": list(self.scenarios), "fees_bps": list(self.fees_bps),
            "capitals_krw": [str(c) for c in self.capitals_krw], "base_scenario": self.base_scenario,
            "base_fee_bps": self.base_fee_bps, "base_capital_krw": str(self.base_capital_krw),
            "b1_draws": self.b1_draws, "seed": self.seed, "q2_max": str(self.q2_max), "q3_max": str(self.q3_max),
            "q4_day_run": self.q4_day_run, "q4_hour_run": self.q4_hour_run, "q4_max_events": self.q4_max_events,
            "q7_max": str(self.q7_max), "min_eval_days": self.min_eval_days,
            "min_round_trips": self.min_round_trips, "min_positive_year_ratio": str(self.min_positive_year_ratio),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ScreenSpec:
        try:
            return cls(
                d["market"], _utc(d["requested_start"]), _utc(d["requested_end"]), int(d["warmup_days"]),
                tuple(d["rules"]), tuple(d["scenarios"]), tuple(int(x) for x in d["fees_bps"]),
                tuple(Decimal(x) for x in d["capitals_krw"]), d["base_scenario"], int(d["base_fee_bps"]),
                Decimal(d["base_capital_krw"]), int(d["b1_draws"]), int(d["seed"]), Fraction(d["q2_max"]),
                Fraction(d["q3_max"]), int(d["q4_day_run"]), int(d["q4_hour_run"]), int(d["q4_max_events"]),
                Fraction(d["q7_max"]), int(d["min_eval_days"]), int(d["min_round_trips"]),
                Fraction(d["min_positive_year_ratio"]))
        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise EconScreenError(f"malformed spec: {exc}") from exc

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


LOCKED_SPEC = ScreenSpec(
    market="KRW-BTC",
    requested_start=datetime(2017, 1, 1, tzinfo=UTC),
    requested_end=datetime(2024, 4, 1, tzinfo=UTC),
    warmup_days=120,
    rules=("M20", "M60", "M120", "R5"),
    scenarios=("E0", "E1", "E2"),
    fees_bps=(0, 5, 15, 25),
    capitals_krw=(Decimal(1_000_000), Decimal(5_000_000), Decimal(10_000_000)),
    base_scenario="E0", base_fee_bps=25, base_capital_krw=Decimal(10_000_000),
    b1_draws=9_999, seed=20261119,
    q2_max=Fraction(1, 200), q3_max=Fraction(1, 100),
    q4_day_run=3, q4_hour_run=7, q4_max_events=3,
    q7_max=Fraction(1, 200),
    min_eval_days=5 * 365, min_round_trips=20, min_positive_year_ratio=Fraction(3, 5),
)


def evidence_label(mode: str) -> str:
    return EVIDENCE_REAL if mode == "real" else NOT_EVIDENCE


def resolve_spec(mode: str, spec: ScreenSpec | None, b1_draws: int | None) -> ScreenSpec:
    """Real mode runs LOCKED_SPEC with 9,999 B1 draws only; other specs and draws are fixture-only."""
    if mode not in MODES:
        raise EconScreenError(f"mode must be one of {MODES}")
    if mode == "real":
        if spec is not None and spec != LOCKED_SPEC:
            raise EconScreenError("real mode runs the locked preregistered spec only")
        if b1_draws is not None and b1_draws != LOCKED_SPEC.b1_draws:
            raise EconScreenError(f"real mode uses exactly {LOCKED_SPEC.b1_draws} B1 draws")
        return LOCKED_SPEC
    out = spec or LOCKED_SPEC
    if b1_draws is not None:
        if b1_draws < 1:
            raise EconScreenError("B1 draws must be >= 1")
        out = replace(out, b1_draws=b1_draws)
    return out


def lf_normalized_sha256(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


# --- permit ---------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class EconScreenPermit:
    mode: str
    study_id: str
    spec_sha256: str
    prereg_sha256: str
    market: str
    requested_start: str
    requested_end: str
    pulls: tuple[tuple[str, str, str], ...]  # (interval, pull_id, pull.json SHA-256)
    out_root: str
    bars: tuple[tuple[str, str], ...] = ()  # (interval, bars_sha256) after the bar export

    def pull_for(self, interval: str) -> tuple[str, str] | None:
        for iv, pull_id, sha in self.pulls:
            if iv == interval:
                return pull_id, sha
        return None

    def bars_for(self, interval: str) -> str | None:
        return dict(self.bars).get(interval)

    def with_bars(self, day_sha256: str, hour_sha256: str) -> EconScreenPermit:
        return replace(self, bars=(("day", day_sha256), ("hour", hour_sha256)))

    def allows_pull(self, doc: dict[str, Any], pull_json_sha256: str, out_root: Path) -> bool:
        """bar_export: may this real pull be exported into out_root?"""
        if self.mode != "real" or not isinstance(doc, dict) or doc.get("provenance") != "real":
            return False
        expected = self.pull_for(str(doc.get("interval")))
        if expected is None or expected != (doc.get("pull_id"), pull_json_sha256):
            return False
        if (doc.get("market"), doc.get("requested_start"), doc.get("requested_end")) != \
                (self.market, self.requested_start, self.requested_end):
            return False
        out_root = Path(out_root)
        return out_root.name == "bars" and Path(self.out_root).resolve() == out_root.resolve().parent.parent

    def admits_bars_dir(self, manifest: dict[str, Any]) -> bool:
        """bars_io.load_bars: may this real bar directory be loaded?"""
        if self.mode != "real" or manifest.get("provenance") != "real":
            return False
        interval = manifest.get("interval")
        expected = self.pull_for(str(interval))
        source = manifest.get("source_pull") or {}
        return (expected is not None and source.get("pull_id") == expected[0]
                and manifest.get("market") == self.market
                and self.bars_for(str(interval)) is not None and manifest.get("bars_sha256") == self.bars_for(str(interval)))

    def admits(self, daily: Any, hourly: Any) -> bool:
        """portfolio.simulate: may these real series (BarSeries) be simulated? Typed Any because BarSeries sets
        provenance, market and interval as untyped slots."""
        if self.mode != "real":
            return False
        for s in (daily, hourly):
            if s.provenance.kind != "real" or s.market != self.market:
                return False
            if self.bars_for(s.interval) is None or s.provenance.bars_sha256 != self.bars_for(s.interval):
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "study_id": self.study_id, "spec_sha256": self.spec_sha256,
                "prereg_sha256": self.prereg_sha256, "market": self.market,
                "requested_start": self.requested_start, "requested_end": self.requested_end,
                "pulls": [list(p) for p in self.pulls], "out_root": self.out_root, "bars": [list(b) for b in self.bars],
                "note": "consistency check only: no approval message is authenticated; not a security boundary"}


def issue_permit(mode: str, spec: ScreenSpec, *, prereg_file_sha256: str, prereg_blob_sha256: str | None,
                 code_state: dict[str, Any], checks: dict[str, dict[str, Any]], expected_pull_sha256: dict[str, str],
                 out_root: Path) -> EconScreenPermit:
    """A permit after every identity check; PermitError names the first mismatch."""
    if mode not in MODES:
        raise PermitError(f"mode must be one of {MODES}")
    if prereg_file_sha256 != PREREGISTRATION_SHA256:
        raise PermitError("the preregistration file does not hash to the fixed SHA-256")
    if prereg_blob_sha256 != PREREGISTRATION_SHA256:
        raise PermitError("the committed preregistration (HEAD blob) does not hash to the fixed SHA-256")
    out_root = Path(out_root)
    if mode == "real":
        if spec != LOCKED_SPEC:
            raise PermitError("real mode runs the locked spec only")
        problems = code_state_problems(code_state)
        if problems:
            raise PermitError(f"real mode needs committed, clean code: {problems}")
        if out_root.name != REAL_ROOT_NAME:
            raise PermitError(f"real output root must be named {REAL_ROOT_NAME}, not {out_root.name}")
    elif not out_root.name.endswith(FIXTURE_SUFFIX):
        raise PermitError(f"fixture output root must end with {FIXTURE_SUFFIX!r}, not {out_root.name}")
    pulls = []
    for interval in ("day", "hour"):
        c = checks.get(interval)
        if c is None:
            raise PermitError(f"no {interval} pull")
        if expected_pull_sha256.get(interval) is None:
            raise PermitError(f"no approved pull.json SHA-256 given for the {interval} pull")
        if c.get("pull_json_sha256") != expected_pull_sha256[interval]:
            raise PermitError(f"{interval} pull.json SHA-256 differs from the approved value")
        if c.get("interval") != interval:
            raise PermitError(f"the {interval} pull is a {c.get('interval')!r} pull")
        if c.get("provenance") != mode:
            raise PermitError(f"{interval} pull provenance {c.get('provenance')!r} does not match mode {mode!r}")
        if c.get("market") != spec.market:
            raise PermitError(f"{interval} pull market {c.get('market')!r} is not {spec.market}")
        if (c.get("requested_start"), c.get("requested_end")) != (utc_iso(spec.requested_start),
                                                                    utc_iso(spec.requested_end)):
            raise PermitError(f"{interval} pull range differs from the spec")
        pulls.append((interval, str(c.get("pull_id")), str(c.get("pull_json_sha256"))))
    return EconScreenPermit(mode, STUDY_ID, spec.sha256(), PREREGISTRATION_SHA256, spec.market,
                            utc_iso(spec.requested_start), utc_iso(spec.requested_end), tuple(pulls),
                            str(out_root.resolve()))


# --- quality ------------------------------------------------------------------------------------------

def _ratio_check(missing: int, expected: int, threshold: Fraction) -> dict[str, Any]:
    if expected <= 0:
        return {"status": NOT_EVALUATED, "reason": "no_expected_buckets", "missing": missing, "expected": expected}
    ratio = Fraction(missing, expected)
    return {"status": PASS if ratio <= threshold else INVALID, "missing": missing, "expected": expected,
            "ratio": str(ratio), "threshold": str(threshold),
            "sensitivity": {"x0.5": PASS if ratio <= threshold / 2 else INVALID,
                            "x2": PASS if ratio <= threshold * 2 else INVALID}}


def pull_stage(checks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Q1, Q6 and the collection conditions from the provider-side pull checks (no bar is built here)."""
    q1 = {iv: PASS if checks[iv].get("verify_ok") else INVALID for iv in ("day", "hour")}
    q6: dict[str, Any] = {}
    for iv in ("day", "hour"):
        c = checks[iv]
        if q1[iv] != PASS:
            q6[iv] = {"status": NOT_EVALUATED, "reason": "q1_not_pass"}
        else:
            bad = c.get("duplicates_conflicting", 0) + c.get("invalid", 0)
            q6[iv] = {"status": PASS if bad == 0 else INVALID, "duplicates_conflicting": c.get("duplicates_conflicting"),
                      "invalid": c.get("invalid"), "duplicates_identical": c.get("duplicates_identical")}
    if all(q1[iv] == PASS and q6[iv]["status"] == PASS for iv in ("day", "hour")):
        day_first, hour_first = checks["day"].get("first_start"), checks["hour"].get("first_start")
        conditions = {
            "status_complete": all(checks[iv].get("status") == "complete" for iv in ("day", "hour")),
            "candles_verify_ok": all(checks[iv].get("verify_ok") for iv in ("day", "hour")),
            "reached_earliest": all(checks[iv].get("reached_earliest") is True for iv in ("day", "hour")),
            "first_dates_equal": bool(day_first and hour_first and day_first[:10] == hour_first[:10]),
        }
        collection = {"status": PASS if all(conditions.values()) else "COLLECTION_RANGE_UNCONFIRMED",
                      "conditions": conditions, "note": "does not prove completeness of the exchange history"}
    else:
        collection = {"status": NOT_EVALUATED, "reason": "q1_or_q6_not_pass"}
    out_of_range = {iv: {"excluded_out_of_range": checks[iv].get("excluded_out_of_range"),
                         "at_or_after_requested_end": checks[iv].get("at_or_after_requested_end")}
                    for iv in ("day", "hour")}
    exposure_candidate = any((checks[iv].get("at_or_after_requested_end") or 0) > 0 for iv in ("day", "hour"))
    passed = collection.get("status") == PASS
    return {"Q1": q1, "Q6": q6, "collection": collection, "out_of_range": out_of_range,
            "exposure_record_candidate": exposure_candidate, "passed": passed}


def _missing_runs(starts: Sequence[datetime], lo: datetime, hi: datetime, step: timedelta) -> list[tuple[datetime, int]]:
    """Runs (first missing start, length) of buckets in [lo, hi) absent from sorted starts."""
    runs = []
    cur = lo
    for s in starts:
        if s < lo or s >= hi:
            continue
        if s > cur:
            runs.append((cur, int((s - cur) / step)))
        cur = s + step
    if cur < hi:
        runs.append((cur, int((hi - cur) / step)))
    return runs


def bar_quality(daily: BarSeries, hourly: BarSeries, spec: ScreenSpec) -> dict[str, Any]:
    """Q2, Q3, Q4, Q7 (preregistration 5) and the evaluation-period condition (6) on exported bars."""
    end = spec.requested_end
    d0 = daily.first_start
    g0 = spec.g_start(d0)
    day_starts = sorted({b.start_utc for b in daily.bars if d0 <= b.start_utc < end})
    hour_starts = sorted({b.start_utc for b in hourly.bars if d0 <= b.start_utc < end})
    exp_day, exp_hour = (end - d0) // DAY, (end - d0) // HOUR
    q2 = _ratio_check(exp_day - len(day_starts), exp_day, spec.q2_max)
    q3 = _ratio_check(exp_hour - len(hour_starts), exp_hour, spec.q3_max)

    events = []
    for iv, starts, step, min_run in (("day", day_starts, DAY, spec.q4_day_run),
                                      ("hour", hour_starts, HOUR, spec.q4_hour_run)):
        for first, n in _missing_runs(starts, d0, end, step):
            if n >= min_run and first < end and first + n * step > g0:  # overlaps G; the run is not cut to G
                events.append({"interval": iv, "first_missing": utc_iso(first), "missing": n})
    q4 = {"status": INVALID if len(events) >= spec.q4_max_events else PASS, "events": events,
          "max_events_exclusive": spec.q4_max_events}

    hours: dict[datetime, list[Bar]] = {}
    for b in hourly.bars:
        hours.setdefault(b.start_utc.replace(hour=0), []).append(b)
    comparable = mismatched = 0
    first_mismatch = None
    for d in daily.bars:
        if not (d0 <= d.start_utc <= end - DAY):
            continue
        hs = sorted(hours.get(d.start_utc, []), key=lambda b: b.start_utc)
        if len(hs) != 24:
            continue
        comparable += 1
        with localcontext() as ctx:
            ctx.prec = 100
            vol = sum((h.volume for h in hs), Decimal(0))
        same = (d.open == hs[0].open and d.close == hs[-1].close and d.high == max(h.high for h in hs)
                and d.low == min(h.low for h in hs) and d.volume == vol)
        if not same:
            mismatched += 1
            first_mismatch = first_mismatch or utc_iso(d.start_utc)
    if comparable == 0:
        q7 = {"status": NOT_EVALUATED, "reason": "no_comparable_day", "comparable_days": 0}
    else:
        q7 = _ratio_check(mismatched, comparable, spec.q7_max)
        q7.update(comparable_days=comparable, mismatched_days=mismatched, first_mismatch=first_mismatch,
                  rule="exact Decimal equality (study development rule; real-data tolerance unverified)")
    eval_days = (end - g0) // DAY
    period = {"status": PASS if eval_days >= spec.min_eval_days else "SAMPLE_NOT_MET", "eval_days": eval_days,
              "min_eval_days": spec.min_eval_days}
    required = {"Q2": q2["status"], "Q3": q3["status"], "Q4": q4["status"], "Q7": q7["status"]}
    return {"d0": utc_iso(d0), "first_signal_day": utc_iso(spec.first_signal_day(d0)),
            "last_signal_day": utc_iso(spec.last_signal_day), "g_start": utc_iso(g0), "g_end": utc_iso(end),
            "Q2": q2, "Q3": q3, "Q4": q4, "Q7": q7, "required": required,
            "report_only_not_evaluated": {k: NOT_EVALUATED for k in REPORT_ONLY_CHECKS},
            "evaluation_period": period}


def quality_summary(stage: dict[str, Any], bars: dict[str, Any] | None) -> dict[str, Any]:
    statuses = [stage["Q1"]["day"], stage["Q1"]["hour"], stage["Q6"]["day"]["status"], stage["Q6"]["hour"]["status"]]
    if bars is None:
        statuses += [NOT_EVALUATED] * 4
    else:
        statuses += list(bars["required"].values())
    collection_ok = stage["collection"].get("status") == PASS
    bundle = INVALID if INVALID in statuses else "INCOMPLETE"
    return {"bundle_status": bundle, "required_all_pass": collection_ok and all(s == PASS for s in statuses),
            "note": "VALID is never reported by this study"}


# --- metrics --------------------------------------------------------------------------------------------

def recovery_days(r: Sequence[float], ref_times: Sequence[datetime]) -> dict[str, Any]:
    """Days from the MDD trough (the first one, on ties) until the P-basis level first regains the
    peak before it. Same level definition as performance.max_drawdown_log."""
    if len(ref_times) != len(r) + 1:
        raise ScreenComputationError("one return per interval between reference times is needed")
    levels = [0.0]
    peak = level = worst = 0.0
    trough_i, trough_peak, peak_i, trough_peak_i = 0, 0.0, 0, 0
    for k, x in enumerate(r):
        level += x
        levels.append(level)
        if level > peak:
            peak, peak_i = level, k + 1
        if peak - level > worst:
            worst, trough_i, trough_peak, trough_peak_i = peak - level, k + 1, peak, peak_i
    if worst == 0.0:
        return value(None, "no_drawdown")
    if abs(-math.expm1(-worst) - max_drawdown_log(r)["value"]) > 1e-15:
        raise ScreenComputationError("recovery trough does not match the MDD")
    info = {"trough": utc_iso(ref_times[trough_i]), "peak": utc_iso(ref_times[trough_peak_i]),
            "tie_rule": "first trough"}
    for j in range(trough_i + 1, len(levels)):
        if levels[j] >= trough_peak:
            days = (ref_times[j] - ref_times[trough_i]) / DAY
            return value(days, recovered=utc_iso(ref_times[j]), **info)
    return value(None, "not_recovered", **info)


def assert_finite(obj: Any, where: str) -> None:
    """Every float inside obj (dicts, lists, tuples) must be finite; else a calculation error (prereg 11).
    Undefined metrics stay None with a reason; nothing is replaced by 0."""
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ScreenComputationError(f"{where}: non-finite value {obj!r}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            assert_finite(v, f"{where}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            assert_finite(v, f"{where}[{i}]")


def describe(res: BacktestResult, spec: ScreenSpec, rule: str, scenario: str, fee: int, capital: Decimal) -> dict[str, Any]:
    led, cfg = res.ledger, res.config
    if led is None or len(led.daily) < 2:
        raise ScreenComputationError(f"{rule} {scenario} {fee} {capital}: fewer than 2 daily valuations")
    r = bt_metrics.daily_log_returns(led)
    refs = [d.ref_time for d in led.daily]
    t_days = (refs[-1] - refs[0]) / DAY
    g_days = (spec.requested_end - (cfg.first_day + 2 * DAY)) / DAY
    if not (len(r) == t_days == g_days):
        raise ScreenComputationError(f"{rule} {scenario} {fee} {capital}: evaluation days differ "
                                     f"(n {len(r)}, T_d {t_days}, G {g_days})")
    positions = ledger_positions(led)
    align = alignment(led, r, cfg.costs)
    c_b, c_s = leg_cost_logs(cfg.costs)
    labels = ["B1", rule, scenario]
    if align["aligned"]:
        bench = compare(r, market_log_returns(led), positions, c_b, c_s, t_days, draws=spec.b1_draws,
                        seed=spec.seed, labels=labels)
        b1 = bench["b1"]
        b1_out = {"status": "compared", "draws": b1["draws"], "structure": b1["structure"],
                  "mean_log_return": b1["mean_log_return"], "strategy_minus_mean_b1": b1["strategy_minus_mean_b1"],
                  "quantile_method": b1["quantile_method"]}
        others = {k: bench[k] for k in ("b2", "b3", "b4", "differences")}
    else:
        b1_out = {"status": "not_aligned", "reasons": list(align["reasons"])}
        others = {"status": "not_aligned"}
    rts, open_at_end = pair_round_trips(led)
    costs_krw = {k: str(v) for k, v in bt_metrics.cost_totals(led).items()}
    ca = cost_analysis(rts, open_at_end, r, cfg.costs, t_days, costs_krw)
    bef = ca["break_even_fee"]
    bef["capital_krw_module_constant"] = bef["capital_krw"]
    bef["capital_krw"] = str(capital)
    bef["capital_note"] = "cost_analysis prints a 1,000,000 KRW constant; f* itself uses this run's iota(C)"
    n = len(r)
    m = mean(r) if r else None
    reasons: dict[str, int] = {}
    for s in res.signals:
        if s.value is None:
            reasons[s.reason or "none"] = reasons.get(s.reason or "none", 0) + 1
    fills: dict[str, int] = {}
    for t in led.trades:
        fills[t.fill_kind] = fills.get(t.fill_kind, 0) + 1
    rts_all = len(rts)
    rts_done = sum(1 for rt in rts if not rt.virtual_close)
    annual_rt = rts_all / (g_days / 365)
    ca_rt = ca["annual_round_trips"]["value"]
    if ca["consistent"] and ca_rt is not None and abs(ca_rt - annual_rt) > 1e-12 * max(1.0, abs(annual_rt)):
        raise ScreenComputationError(f"{rule} {scenario} {fee} {capital}: annual round trips differ "
                                     f"({annual_rt!r} vs cost_analysis {ca_rt!r})")
    out = {
        "status": "COMPUTED",
        "rule": rule, "scenario": scenario, "fee_bps": fee, "capital_krw": str(capital),
        "costs": cfg.costs.to_dict(), "capacity": cfg.to_dict()["capacity"],
        "evaluation_days": {"n_returns": n, "t_days": t_days, "g_days": g_days,
                            "definition": "G = [F + 2 days, requested_end); n = T_d = G days is checked"},
        "n_returns": n, "t_days": t_days, "first_ref": utc_iso(refs[0]), "last_ref": utc_iso(refs[-1]),
        "net_mean_log_return": value(m) if m is not None else value(None, "no_returns"),
        "annualized_net_log_return": value(365 * m) if m is not None else value(None, "no_returns"),
        "cumulative_net_return": value(math.expm1(sum(r))),
        "round_trips": {"including_virtual_exit": rts_all, "completed_only": rts_done,
                        "annual_including_virtual_exit": value(annual_rt),
                        "annual_denominator": "G days / 365"},
        "break_even_fee": bef,
        "mdd": max_drawdown_log(r),
        "recovery_days": recovery_days(r, refs),
        "yearly": yearly_report(refs, r),
        "exposure": exposure(positions),
        "cost_analysis": {k: ca[k] for k in ("consistent", "gross_log_return", "cost_log", "net_log_return",
                                               "gross_to_cost_ratio", "annual_cost_log", "annual_cost_fraction",
                                               "annual_round_trips", "costs_krw")},
        "round_trip_report": round_trip_report(led),
        "alignment": {"aligned": align["aligned"], "reasons": list(align["reasons"])},
        "b1": b1_out,
        "benchmarks_b2_b4": others,
        "seed": {"seed": str(spec.seed), "labels": labels, "algorithm": "bt-seed/1"},
        "q9_signal_none_days": {"total": sum(reasons.values()), "by_reason": reasons},
        "q10_fill_kinds": fills,
    }
    assert_finite(out, f"{rule}/{scenario}/{fee}/{capital}")
    return out


NOT_COMPUTABLE_REASON = "insufficient_data_first_signal_after_last_signal"


def not_computable(spec: ScreenSpec, d0: datetime) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """F > E: every rule x scenario x fee x capital is reported as NOT_COMPUTABLE with the data-shortage reason
    (prereg 8 and 9), and every rule is SCREEN_NOT_EVALUABLE. No value is set to 0; simulate is not called."""
    info = {"d0": utc_iso(d0), "first_signal_day": utc_iso(spec.first_signal_day(d0)),
            "last_signal_day": utc_iso(spec.last_signal_day)}
    none = value(None, NOT_COMPUTABLE_REASON)
    combos = [{"status": "NOT_COMPUTABLE", "reason": NOT_COMPUTABLE_REASON, **info, "rule": rule, "scenario": scenario,
               "fee_bps": fee, "capital_krw": str(capital), "net_mean_log_return": none,
               "annualized_net_log_return": none, "cumulative_net_return": none, "mdd": none, "recovery_days": none,
               "break_even_fee": none, "b1": {"status": "not_computable", "reason": NOT_COMPUTABLE_REASON}}
              for rule in spec.rules for scenario in spec.scenarios for fee in spec.fees_bps
              for capital in spec.capitals_krw]
    flags = {rule: {"flag": FLAG_NOT_EVALUABLE, "reason": NOT_COMPUTABLE_REASON, "data_insufficient": True, **info}
             for rule in spec.rules}
    return combos, flags


def run_matrix(daily: BarSeries, hourly: BarSeries, spec: ScreenSpec, settings_file: Path, *,
               real_permit: EconScreenPermit | None = None) -> list[dict[str, Any]]:
    """Every rule x scenario x fee x capital combination, in that order, with the existing engine."""
    settings, _ = load_cost_settings(settings_file)
    d0 = daily.first_start
    first, last = spec.first_signal_day(d0), spec.last_signal_day
    combos = []
    for rule in spec.rules:
        for scenario in spec.scenarios:
            for fee in spec.fees_bps:
                for capital in spec.capitals_krw:
                    costs, verified = cost_model(settings, fee, scenario, capital, fee_basis="inclusive")
                    cfg = RunConfig(rule, first, last, capital, costs, scenario=scenario,
                                    fill_substitution="prereg_6_3", capacity_verified=verified)
                    res = simulate(daily, hourly, cfg, real_permit=real_permit)
                    combos.append(describe(res, spec, rule, scenario, fee, capital))
    return combos


def _find(combos: list[dict[str, Any]], rule: str, scenario: str, fee: int, capital: Decimal) -> dict[str, Any]:
    for c in combos:
        if (c["rule"], c["scenario"], c["fee_bps"], c["capital_krw"]) == (rule, scenario, fee, str(capital)):
            return c
    raise ScreenComputationError(f"combination {rule} {scenario} {fee} {capital} is missing")


def screen_flags(combos: list[dict[str, Any]], spec: ScreenSpec, period_ok: bool,
                 period: dict[str, Any] | None = None) -> dict[str, Any]:
    """Preregistration 9. A full-year ratio that cannot be computed for an evaluable rule is a
    calculation error (11): ScreenComputationError, no flag. `period` (bar_quality evaluation_period) adds the
    data-shortage detail to the NOT_EVALUABLE reason."""
    out: dict[str, Any] = {}
    for rule in spec.rules:
        if not period_ok:
            out[rule] = {"flag": FLAG_NOT_EVALUABLE, "reason": "evaluation_period_below_minimum"}
            if period is not None:
                out[rule].update(data_insufficient=True, eval_days=period.get("eval_days"),
                                 min_eval_days=period.get("min_eval_days"))
            continue
        base = _find(combos, rule, spec.base_scenario, spec.base_fee_bps, spec.base_capital_krw)
        if base["round_trips"]["including_virtual_exit"] < spec.min_round_trips:
            out[rule] = {"flag": FLAG_NOT_EVALUABLE, "reason": "round_trips_below_minimum",
                         "round_trips": base["round_trips"]["including_virtual_exit"]}
            continue
        if base["b1"]["status"] != "compared":
            out[rule] = {"flag": FLAG_NOT_EVALUABLE, "reason": "b1_not_aligned"}
            continue
        ratio = base["yearly"]["positive_year_ratio_full_years"]
        if ratio["value"] is None:
            raise ScreenComputationError(f"{rule}: positive full-year ratio not computable for an evaluable rule")
        others = {s: _find(combos, rule, s, spec.base_fee_bps, spec.base_capital_krw)
                  for s in spec.scenarios if s != spec.base_scenario}
        conditions = {
            "base_net_mean_positive": base["net_mean_log_return"]["value"] > 0,
            "base_net_mean_above_b1_mean": base["b1"]["strategy_minus_mean_b1"]["value"] > 0,
            **{f"{s}_net_mean_positive": c["net_mean_log_return"]["value"] > 0 for s, c in others.items()},
            "positive_full_year_ratio_at_least_min": Fraction(ratio["positive_years"], ratio["years"])
            >= spec.min_positive_year_ratio,
        }
        out[rule] = {"flag": FLAG_PASS if all(conditions.values()) else FLAG_NOT_MET, "conditions": conditions}
    return out


# --- output directories ---------------------------------------------------------------------------------

def utc_stamp(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def check_run_lock(root: Path) -> None:
    """A run attempt (run-* or .tmp-run-*) already exists under root: no second run. prepare-* does not lock."""
    root = Path(root)
    if root.exists():
        found = sorted(p.name for p in root.iterdir() if p.name.startswith(("run-", ".tmp-run-")))
        if found:
            raise EconScreenError(f"a screening run was already attempted under {root}: {found}")


RUN_LOCK_NAME = "run-lock"


def acquire_run_lock(root: Path) -> Path:
    """Atomic one-run lock (Work Order IMPL-03 D3): the existing attempt check, then a single os.mkdir of
    <root>/run-lock. Of two runs started at the same time only one mkdir succeeds. The lock is never removed;
    its name starts with "run-", so check_run_lock keeps reporting it as an attempt."""
    root = Path(root)
    check_run_lock(root)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / RUN_LOCK_NAME
    try:
        os.mkdir(lock)
    except FileExistsError as exc:
        raise EconScreenError(f"a screening run was already attempted under {root}: {RUN_LOCK_NAME} exists") from exc
    return lock


def begin_output(root: Path, kind: str, now: datetime) -> Path:
    """Create <root>/.tmp-<kind>-<stamp>/ (the attempt marker); never reuse an existing name."""
    if kind not in ("prepare", "run"):
        raise EconScreenError(f"unknown output kind {kind!r}")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / f".tmp-{kind}-{utc_stamp(now)}"
    tmp.mkdir(exist_ok=False)
    return tmp


def json_bytes(doc: Any) -> bytes:
    return (json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def tree_files(d: Path) -> dict[str, Path]:
    return {p.relative_to(d).as_posix(): p for p in sorted(Path(d).rglob("*")) if p.is_file()}


def finish_output(tmp: Path, kind: str, files: dict[str, bytes]) -> tuple[Path, str]:
    """Write files into tmp, then SHA256SUMS.txt over every file in tmp, then rename to <kind>-<stamp>.
    On failure the temporary directory and the files already written stay where they are."""
    tmp = Path(tmp)
    for name, data in files.items():
        atomic_write_bytes(tmp / name, data)
    listing = {k: v for k, v in tree_files(tmp).items() if k != SUMS_FILE}
    sums = "".join(f"{sha256_file(p)}  {k}\n" for k, p in sorted(listing.items())).encode("utf-8")
    atomic_write_bytes(tmp / SUMS_FILE, sums)
    final = tmp.parent / tmp.name.replace(f".tmp-{kind}-", f"{kind}-", 1)
    os.rename(tmp, final)  # never overwrites
    return final, sha256_file(final / SUMS_FILE)


def verify_output(d: Path) -> dict[str, str]:
    """SHA256SUMS.txt lists exactly the other files and every hash matches. Returns path -> SHA-256."""
    d = Path(d)
    try:
        lines = (d / SUMS_FILE).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EconScreenError(f"cannot read {d / SUMS_FILE}: {exc}") from exc
    listed: dict[str, str] = {}
    for line in lines:
        digest, sep, name = line.partition("  ")
        if not sep or len(digest) != 64 or name in listed:
            raise EconScreenError(f"malformed line in {SUMS_FILE}: {line!r}")
        listed[name] = digest
    present = {k: p for k, p in tree_files(d).items() if k != SUMS_FILE}
    if set(present) != set(listed):
        raise EconScreenError(f"{d}: file set differs from {SUMS_FILE}")
    for k, p in present.items():
        if sha256_file(p) != listed[k]:
            raise EconScreenError(f"{d}: {k} does not match {SUMS_FILE}")
    return listed


# --- synthetic input and resource measurement -----------------------------------------------------------

def synthetic_bars(start: datetime, end: datetime, *, seed: int, label: str, market: str = "KRW-BTC",
                   kind: str = "synthetic", hourly_vol: float = 0.01) -> tuple[BarSeries, BarSeries]:
    """SYNTHETIC hourly random walk in integer KRW with daily bars aggregated from it exactly (Q7-consistent).
    Not market data."""
    rng = random.Random(f"{seed}|{label}")
    hours, days = [], []
    price = 50_000_000.0
    t = start
    while t < end:
        day_hours = []
        for h in range(24):
            o = Decimal(int(price))
            price = max(1_000.0, price * math.exp(rng.gauss(0.0, hourly_vol)))
            c = Decimal(int(price))
            hi = max(o, c) + Decimal(rng.randint(0, 50_000))
            lo = max(Decimal(1), min(o, c) - Decimal(rng.randint(0, 50_000)))
            vol = Decimal(rng.randint(1, 10_000_000)) / Decimal(100_000_000)
            start_h = t + h * HOUR
            day_hours.append(Bar(market, "hour", start_h, o, hi, lo, c, (vol * c).quantize(Decimal("0.00000001")), vol,
                                 int((start_h + HOUR).timestamp() * 1000) - 1000))
        hours.extend(day_hours)
        with localcontext() as ctx:
            ctx.prec = 100
            days.append(Bar(market, "day", t, day_hours[0].open, max(b.high for b in day_hours),
                            min(b.low for b in day_hours), day_hours[-1].close,
                            sum((b.value_krw for b in day_hours), Decimal(0)),
                            sum((b.volume for b in day_hours), Decimal(0)), day_hours[-1].last_tick_ms))
        t += DAY
    desc = f"econ_screen.synthetic_bars seed={seed} label={label}"
    return (BarSeries.build(days, provenance_for(days, kind, desc)),
            BarSeries.build(hours, provenance_for(hours, kind, desc)))


@dataclass
class Measurement:
    rows: list[dict[str, Any]] = field(default_factory=list)


def measure(settings_file: Path, *, spec: ScreenSpec = LOCKED_SPEC, draws: Sequence[int] = (99, 999),
            repeats: int = 2, emit: Callable[[str], None] = print,
            clock: Callable[[], float] = time.perf_counter) -> dict[str, Any]:
    """Synthetic resource measurement (Work Order D11). Takes no file input and writes no file."""
    daily, hourly = synthetic_bars(spec.requested_start, spec.requested_end, seed=spec.seed, label="MEASURE")
    settings, _ = load_cost_settings(settings_file)
    first, last = spec.first_signal_day(daily.first_start), spec.last_signal_day
    fee, capital = spec.base_fee_bps, spec.base_capital_krw

    def config(rule: str, scenario: str) -> RunConfig:
        costs, verified = cost_model(settings, fee, scenario, capital, fee_basis="inclusive")
        return RunConfig(rule, first, last, capital, costs, scenario=scenario, fill_substitution="prereg_6_3",
                         capacity_verified=verified)

    sims = [(rule, spec.base_scenario) for rule in spec.rules] + \
           [(spec.rules[0], s) for s in spec.scenarios if s != spec.base_scenario]
    out: dict[str, Any] = {"evidence": NOT_EVIDENCE, "input": {"daily_bars": len(daily), "hourly_bars": len(hourly)},
                           "rounds": []}
    emit(f"{NOT_EVIDENCE} | econ-screen-measure: synthetic input, {len(daily)} daily / {len(hourly)} hourly bars")
    for rnd in range(repeats):
        row: dict[str, Any] = {"round": rnd + 1, "simulate_s": {}, "b1_s": {}}
        base_res = None
        for rule, scenario in sims:
            t0 = clock()
            res = simulate(daily, hourly, config(rule, scenario))
            row["simulate_s"][f"{rule}/{scenario}"] = clock() - t0
            if rule == spec.rules[0] and scenario == spec.base_scenario:
                base_res = res
        assert base_res is not None and base_res.ledger is not None
        led = base_res.ledger
        r = bt_metrics.daily_log_returns(led)
        c_b, c_s = leg_cost_logs(base_res.config.costs)
        t_days = (led.daily[-1].ref_time - led.daily[0].ref_time) / DAY
        for k in draws:
            t0 = clock()
            compare(r, market_log_returns(led), ledger_positions(led), c_b, c_s, t_days, draws=k, seed=spec.seed,
                    labels=["B1", spec.rules[0], spec.base_scenario])
            row["b1_s"][str(k)] = clock() - t0
        row["n_returns"] = len(r)
        out["rounds"].append(row)
        emit(f"  round {rnd + 1}: simulate {row['simulate_s']} | B1 {row['b1_s']} | n_returns {len(r)}")
    tracemalloc.start()
    try:
        res = simulate(daily, hourly, config(spec.rules[-1] if "M120" not in spec.rules else "M120", spec.base_scenario))
        led3 = res.ledger
        assert led3 is not None
        r = bt_metrics.daily_log_returns(led3)
        c_b, c_s = leg_cost_logs(res.config.costs)
        t_days = (led3.daily[-1].ref_time - led3.daily[0].ref_time) / DAY
        compare(r, market_log_returns(led3), ledger_positions(led3), c_b, c_s, t_days, draws=min(draws),
                seed=spec.seed, labels=["B1", res.config.rule, spec.base_scenario])
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    out["python_heap_peak_bytes"] = peak
    emit(f"  M3 tracemalloc Python heap peak: {peak} bytes (not RSS)")
    per_scen: dict[str, float] = {}
    for row in out["rounds"]:
        for key, s in row["simulate_s"].items():
            scen = key.split("/")[1]
            per_scen[scen] = max(per_scen.get(scen, 0.0), s)
    sim_max = {k: max(row["simulate_s"][k] for row in out["rounds"]) for k in out["rounds"][0]["simulate_s"]}
    sim_total = 0.0
    for rule in spec.rules:
        for scen in spec.scenarios:
            sim_total += sim_max.get(f"{rule}/{scen}", per_scen.get(scen, max(per_scen.values())))
    big = max(draws)
    b1 = max(row["b1_s"][str(big)] for row in out["rounds"])
    n_combos = len(spec.rules) * len(spec.scenarios) * len(spec.fees_bps) * len(spec.capitals_krw)
    per_rs = len(spec.fees_bps) * len(spec.capitals_krw)
    t_est = per_rs * sim_total + n_combos * b1 * spec.b1_draws / big
    out["extrapolation"] = {"formula": f"{per_rs} x sum_rule,scenario t_sim + {n_combos} x t_B1({big}) x "
                                       f"{spec.b1_draws} / {big}", "t_est_s": t_est, "budget_proposal_s": 2 * t_est,
                            "note": "proposal only; not an approved budget. Limits: real gaps and substituted fills "
                                    "change trade counts, machine load, tracemalloc is not RSS, prepare not measured"}
    emit(f"  T_est {t_est:.1f} s; budget proposal x2 = {2 * t_est:.1f} s (proposal only, not approved)")
    return out


__all__ = [
    "EconScreenError", "EconScreenPermit", "LOCKED_SPEC", "PermitError", "ScreenComputationError", "ScreenSpec",
    "bar_quality", "begin_output", "check_run_lock", "describe", "evidence_label", "finish_output", "issue_permit",
    "measure", "pull_stage", "quality_summary", "recovery_days", "resolve_spec", "run_matrix", "screen_flags",
    "settings_hashes", "synthetic_bars", "verify_output",
]
