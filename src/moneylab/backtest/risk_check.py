"""Pure calculation for the BT-3e forward monthly risk check (docs/tasks/BT-3E/WORK_ORDER.md E2, E6, E9, E11, E14).

No file access and no vault import: the vault (backtest/vault.py) owns access state, bindings, integrity and
non-disclosure, and passes bars it has already verified. This module only
  * validates a risk policy (every study-policy value is explicit; there are no defaults),
  * rebuilds an explicit RunConfig per strategy (CostModel.scenario and the RunConfig constructor, unchanged),
  * evaluates one strategy with the existing engine (portfolio.simulate) and the MAX_DRAWDOWN_LOG metric,
  * compares a forward value with the internally recomputed confirmatory reference.
Supported values (MAX_DRAWDOWN_LOG, ENGINE_WINDOW_BT3B, ...) are what the mechanism can do; supporting them
does not select them for the study (BT-4 does). The signal semantics of the engine are not changed (BT4-Q18).
Nothing here is public API (__all__ is empty). SYNTHETIC / NOT_EVIDENCE.
"""

from __future__ import annotations

import math as _math
from dataclasses import dataclass as _dataclass
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta
from decimal import Decimal as _Decimal
from decimal import InvalidOperation as _InvalidOperation
from typing import Any as _Any

from moneylab.backtest.costs import CostModel as _CostModel
from moneylab.backtest.data import BarSeries as _BarSeries
from moneylab.backtest.data import provenance_for as _provenance_for
from moneylab.backtest.execution import SCENARIOS as _SCENARIOS
from moneylab.backtest.execution import SUBSTITUTION_RULES as _SUBSTITUTION_RULES
from moneylab.backtest.performance import max_drawdown_log as _max_drawdown_log
from moneylab.backtest.portfolio import RunConfig as _RunConfig
from moneylab.backtest.portfolio import simulate as _simulate
from moneylab.backtest.strategy import RULES as _RULES
from moneylab.domain.bars import Bar as _Bar
from moneylab.domain.bars import utc_iso as _utc_iso
from moneylab.storage.atomic import sha256_of as _sha256_of

__all__: list[str] = []

_METRIC_IDS = ("MAX_DRAWDOWN_LOG",)
_WINDOW_MAPPING_IDS = ("ENGINE_WINDOW_BT3B",)
_COMPARISONS = ("gt", "ge")
_CUMULATIVE, _MONTH_ONLY = "CUMULATIVE_FROM_L", "MONTH_ONLY"
_ACCUMULATION_MODES = (_CUMULATIVE, _MONTH_ONLY)
# Identity of the unchanged engine semantics the check runs on (E13): gap-free-window signals, the BT-3b boundary,
# and scenario reference times. Recorded for binding only; it is not a switch.
_ENGINE_SEMANTICS_ID = "moneylab.backtest.engine/gap-free-window-signal+bt3b-boundary+scenario-ref-time/1"
_CANDIDATE_KEYS = ("scenario", "initial_cash", "fee_bps", "kappa_bps", "impact_bps", "fill_substitution",
                   "capacity_verified")
_PASS, _VIOLATION = "PASS", "VIOLATION"


class _RiskSpecError(ValueError):
    """A risk policy or strategy binding is malformed (messages name fields only, never data values)."""


@_dataclass(frozen=True)
class _Policy:
    metric_id: str
    threshold_ratio: _Decimal
    comparison_operator: str
    accumulation_mode: str
    window_mapping_id: str
    confirmatory_first_day: _datetime
    confirmatory_last_day: _datetime
    check_window_end_utc: _datetime | None
    candidates: dict[str, dict[str, _Any]]  # rule -> settings (record form, including config_sha256)


def _midnight(value: _Any, name: str) -> _datetime:
    if not isinstance(value, _datetime) or value.tzinfo is None or value.utcoffset() != _timedelta(0):
        raise _RiskSpecError(f"{name} must be a timezone-aware UTC datetime")
    if value.hour or value.minute or value.second or value.microsecond:
        raise _RiskSpecError(f"{name} must be 00:00:00 UTC")
    return value


def _parse_time(text: _Any, name: str) -> _datetime:
    if not isinstance(text, str):
        raise _RiskSpecError(f"{name} must be a UTC timestamp string")
    try:
        t = _datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise _RiskSpecError(f"{name} is not a timestamp") from None
    t = _midnight(t, name)
    if _utc_iso(t) != text:
        raise _RiskSpecError(f"{name} is not in canonical form")
    return t


def _decimal(text: _Any, name: str, *, positive: bool) -> _Decimal:
    if not isinstance(text, str):
        raise _RiskSpecError(f"{name} must be a decimal string")
    try:
        d = _Decimal(text)
    except _InvalidOperation:
        raise _RiskSpecError(f"{name} is not a decimal") from None
    if not d.is_finite() or (d <= 0 if positive else d < 0):
        raise _RiskSpecError(f"{name} is out of range")
    return d


def _run_config(rule: str, settings: dict[str, _Any], first_day: _datetime, last_day: _datetime) -> _RunConfig:
    """The explicit RunConfig of one candidate (no field taken from a default)."""
    try:
        costs = _CostModel.scenario(settings["fee_bps"], _Decimal(settings["kappa_bps"]),
                                    _Decimal(settings["impact_bps"]))
        return _RunConfig(rule, first_day, last_day, _Decimal(settings["initial_cash"]), costs,
                          scenario=settings["scenario"], fill_substitution=settings["fill_substitution"],
                          capacity_verified=settings["capacity_verified"])
    except (ValueError, KeyError, TypeError, _InvalidOperation):
        raise _RiskSpecError(f"candidate {rule} does not form a valid RunConfig") from None


def _candidate_config_sha256(settings: dict[str, _Any]) -> str:
    """ERRATA-001 E15: the canonical SHA-256 (storage.atomic.sha256_of) of exactly the seven date-independent
    candidate settings as recorded. No strategy id, dates, caller, timestamps, realized F or access identity."""
    return _sha256_of({k: settings[k] for k in _CANDIDATE_KEYS})


def _candidate(rule: _Any, settings: _Any, first_day: _datetime, last_day: _datetime) -> dict[str, _Any]:
    """Validate one candidate's settings (they must form a valid RunConfig over the confirmatory interval) and
    return its record form with the date-independent config_sha256 (ERRATA-001)."""
    if not isinstance(rule, str) or rule not in _RULES:
        raise _RiskSpecError("candidate strategy id is not a known rule")
    if not isinstance(settings, dict) or set(settings) != set(_CANDIDATE_KEYS):
        raise _RiskSpecError(f"candidate {rule} must hold exactly {list(_CANDIDATE_KEYS)}")
    if not isinstance(settings["scenario"], str) or settings["scenario"] not in _SCENARIOS:
        raise _RiskSpecError(f"candidate {rule}: unsupported scenario")
    if not isinstance(settings["fill_substitution"], str) or settings["fill_substitution"] not in _SUBSTITUTION_RULES:
        raise _RiskSpecError(f"candidate {rule}: unsupported fill_substitution")
    if not isinstance(settings["capacity_verified"], bool):
        raise _RiskSpecError(f"candidate {rule}: capacity_verified must be a boolean")
    if isinstance(settings["fee_bps"], bool) or not isinstance(settings["fee_bps"], int):
        raise _RiskSpecError(f"candidate {rule}: fee_bps must be an integer")
    _decimal(settings["initial_cash"], f"candidate {rule} initial_cash", positive=True)
    _decimal(settings["kappa_bps"], f"candidate {rule} kappa_bps", positive=False)
    _decimal(settings["impact_bps"], f"candidate {rule} impact_bps", positive=False)
    _run_config(rule, settings, first_day, last_day)  # validation only; the identity does not depend on dates
    return {**{k: settings[k] for k in _CANDIDATE_KEYS}, "config_sha256": _candidate_config_sha256(settings)}


def _policy_record_fields(*, metric_id: _Any, threshold_ratio: _Any, comparison_operator: _Any,
                          accumulation_mode: _Any, window_mapping_id: _Any, engine_semantics_id: _Any,
                          confirmatory_first_day: _Any, confirmatory_last_day: _Any, check_window_end_utc: _Any,
                          candidates: _Any, public_end: _datetime) -> dict[str, _Any]:
    """The policy fields of a risk_policy record built from API values (every value explicit, E14)."""
    first = _midnight(confirmatory_first_day, "confirmatory_first_day")
    last = _midnight(confirmatory_last_day, "confirmatory_last_day")
    cwe = None if check_window_end_utc is None else _midnight(check_window_end_utc, "check_window_end_utc")
    if not isinstance(candidates, dict) or not candidates:
        raise _RiskSpecError("candidates must be a non-empty mapping")
    fields = {"metric_id": metric_id, "threshold_ratio": threshold_ratio, "comparison_operator": comparison_operator,
              "accumulation_mode": accumulation_mode, "window_mapping_id": window_mapping_id,
              "engine_semantics_id": engine_semantics_id, "confirmatory_first_day": _utc_iso(first),
              "confirmatory_last_day": _utc_iso(last), "check_window_end_utc": None if cwe is None else _utc_iso(cwe),
              "candidates": {rule: _candidate(rule, s, first, last) for rule, s in sorted(candidates.items(),
                                                                                       key=lambda kv: str(kv[0]))}}
    _policy_from_fields(fields, public_end)
    return fields


def _policy_from_fields(fields: dict[str, _Any], public_end: _datetime) -> _Policy:
    """Validate the policy fields of a risk_policy record (record form) and parse them."""
    if fields.get("metric_id") not in _METRIC_IDS:
        raise _RiskSpecError("unsupported metric_id")
    if fields.get("comparison_operator") not in _COMPARISONS:
        raise _RiskSpecError("unsupported comparison_operator")
    if fields.get("accumulation_mode") not in _ACCUMULATION_MODES:
        raise _RiskSpecError("unsupported accumulation_mode")
    if fields.get("window_mapping_id") not in _WINDOW_MAPPING_IDS:
        raise _RiskSpecError("unsupported window_mapping_id")
    if fields.get("engine_semantics_id") != _ENGINE_SEMANTICS_ID:
        raise _RiskSpecError("engine_semantics_id does not match the current engine semantics")
    ratio = _decimal(fields.get("threshold_ratio"), "threshold_ratio", positive=True)
    first = _parse_time(fields.get("confirmatory_first_day"), "confirmatory_first_day")
    last = _parse_time(fields.get("confirmatory_last_day"), "confirmatory_last_day")
    if last < first:
        raise _RiskSpecError("confirmatory_last_day is before confirmatory_first_day")
    if last + _timedelta(days=3) > public_end:
        raise _RiskSpecError("the confirmatory engine interval ends after the public boundary")
    cwe_text = fields.get("check_window_end_utc")
    cwe = None if cwe_text is None else _parse_time(cwe_text, "check_window_end_utc")
    cands = fields.get("candidates")
    if not isinstance(cands, dict) or not cands or list(cands) != sorted(cands):
        raise _RiskSpecError("candidates must be a non-empty mapping in canonical order")
    for rule, rec in cands.items():
        if not isinstance(rec, dict) or set(rec) != set(_CANDIDATE_KEYS) | {"config_sha256"}:
            raise _RiskSpecError(f"candidate {rule} has an unexpected key set")
        if _candidate(rule, {k: rec[k] for k in _CANDIDATE_KEYS}, first, last)["config_sha256"] != rec["config_sha256"]:
            raise _RiskSpecError(f"candidate {rule} config_sha256 does not match its settings")
    return _Policy(fields["metric_id"], ratio, fields["comparison_operator"], fields["accumulation_mode"],
                   fields["window_mapping_id"], first, last, cwe, cands)


def _canonical_strategies(strategies: _Any, policy: _Policy) -> list[str]:
    if not isinstance(strategies, (list, tuple)) or not strategies:
        raise _RiskSpecError("strategies must be a non-empty list")
    out = list(strategies)
    if any(not isinstance(s, str) for s in out) or out != sorted(set(out)):
        raise _RiskSpecError("strategies must be sorted unique strategy ids")
    if not set(out) <= set(policy.candidates):
        raise _RiskSpecError("strategies must be a subset of the frozen candidates")
    return out


def _series(bars: list[_Bar], kind: str) -> _BarSeries:
    return _BarSeries.build(bars, _provenance_for(bars, kind, "vault risk check (internal)"))


def _metric(policy: _Policy, rule: str, daily: list[_Bar], hourly: list[_Bar], kind: str, first_day: _datetime,
            last_day: _datetime) -> float:
    """MAX_DRAWDOWN_LOG of one strategy: daily ledger equity at the scenario reference times -> log returns
    (the first one from the initial cash) -> the same formula as performance.max_drawdown_log."""
    settings = policy.candidates[rule]
    rc = _run_config(rule, settings, first_day, last_day)
    result = _simulate(_series(daily, kind), _series(hourly, kind), rc)
    prev = float(rc.initial_cash)
    returns: list[float] = []
    for row in result.ledger.daily:
        eq = float(row.equity)
        returns.append(_math.log(eq / prev))
        prev = eq
    v = _max_drawdown_log(returns)["value"]
    return 0.0 if v is None else float(v)


def _confirmatory_reference(policy: _Policy, rule: str, public_daily: list[_Bar], public_hourly: list[_Bar],
                            kind: str) -> float:
    """The confirmatory reference, recomputed from public bars with the bound settings (E2)."""
    return _metric(policy, rule, public_daily, public_hourly, kind, policy.confirmatory_first_day,
                   policy.confirmatory_last_day)


def _engine_window(policy: _Policy, protected_start: _datetime, next_month: _datetime) -> tuple[_datetime, _datetime]:
    """ENGINE_WINDOW_BT3B (E6): engine first_day = protected start - 2 days, engine last_day = next month - 3 days
    (engine G_end = next month). The first engine reference time can precede the protected start (lookback rows)
    and the last day of the month can be assigned to the following engine day."""
    if policy.window_mapping_id != "ENGINE_WINDOW_BT3B":
        raise _RiskSpecError("unsupported window_mapping_id")
    first, last = protected_start - _timedelta(days=2), next_month - _timedelta(days=3)
    if last < first:
        raise _RiskSpecError("the engine window is empty")
    return first, last


def _month_only_lookback(policy: _Policy, strategies: list[str], protected_start: _datetime,
                         next_month: _datetime) -> tuple[_datetime, _datetime, _datetime]:
    """ERRATA-001 E6 deterministic minimal forward lookback for MONTH_ONLY: (T_day, T_hour, T_req) with
    n_max = max engine daily window (strategy.RULES[rule].bars_needed) over F, F = engine first_day,
    T_day = F - (n_max - 1) days, T_hour = F, T_req = min(T_day, T_hour)."""
    first, _last = _engine_window(policy, protected_start, next_month)
    n_max = max(_RULES[rule].bars_needed for rule in strategies)
    t_day, t_hour = first - _timedelta(days=n_max - 1), first
    return t_day, t_hour, min(t_day, t_hour)


def _decide(policy: _Policy, forward_value: float, reference: float) -> str:
    limit = float(policy.threshold_ratio) * reference
    violated = forward_value > limit if policy.comparison_operator == "gt" else forward_value >= limit
    return _VIOLATION if violated else _PASS


def _forward_decisions(policy: _Policy, strategies: list[str], references: dict[str, float], daily: list[_Bar],
                       hourly: list[_Bar], kind: str, protected_start: _datetime,
                       next_month: _datetime) -> dict[str, str]:
    """strategy -> PASS | VIOLATION for one month (the only output that leaves the vault)."""
    first, last = _engine_window(policy, protected_start, next_month)
    return {rule: _decide(policy, _metric(policy, rule, daily, hourly, kind, first, last), references[rule])
            for rule in strategies}
