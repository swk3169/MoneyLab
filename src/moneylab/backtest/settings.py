"""Cost and market impact settings file (BT-2b-2; configs/backtest_costs.toml).

Two hashes are recorded for the file:
  sha256_raw_bytes        SHA-256 of the file bytes as they are on disk
  sha256_lf_normalized    SHA-256 of the bytes after replacing CRLF and lone CR by LF
The normalized hash is the integrity reference (a Windows checkout may store the same content with
CRLF); the raw hash is kept as evidence of the exact file that was read.

Validation: fee scenarios within 0 / 5 / 15 / 25 bp, basis inclusive or on_top, fee status
FEE_UNCONFIRMED, impact status ASSUMED, kappa equal to backtest.execution.SCENARIOS (the two places
cannot drift apart), positive impact references. Decimal values must be strings or integers.
"""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from moneylab.backtest.costs import (
    FEE_BASES,
    FEE_SCENARIOS_BPS,
    FEE_STATUS_UNCONFIRMED,
    CostModel,
    impact_bps_for_capital,
)
from moneylab.backtest.execution import SCENARIOS

DEFAULT_SETTINGS_FILE = Path(__file__).resolve().parents[3] / "configs" / "backtest_costs.toml"
NORMALIZATION = "CRLF and lone CR replaced by LF, then SHA-256 of the UTF-8 bytes"


class SettingsError(ValueError):
    """The settings file is missing, malformed or outside the allowed values."""


@dataclass(frozen=True)
class CostSettings:
    fee_scenarios_bps: tuple[int, ...]
    fee_basis: str
    fee_status: str
    kappa_bps: tuple[tuple[str, Decimal], ...]
    impact_ref_bps: Decimal
    impact_ref_capital: Decimal
    capacity_limit: Decimal
    impact_status: str

    def kappa(self, scenario: str) -> Decimal:
        return dict(self.kappa_bps)[scenario]


def settings_hashes(path: Path) -> dict[str, str]:
    raw = Path(path).read_bytes()
    norm = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return {"path": str(Path(path).resolve()), "file_name": Path(path).name, "normalization": NORMALIZATION,
            "sha256_lf_normalized": hashlib.sha256(norm).hexdigest(),
            "sha256_raw_bytes": hashlib.sha256(raw).hexdigest()}


def _dec(v: Any, name: str) -> Decimal:
    if isinstance(v, bool) or not isinstance(v, (int, str)):
        raise SettingsError(f"{name} must be an integer or a decimal string, got {v!r}")
    try:
        d = Decimal(v)
    except InvalidOperation as exc:
        raise SettingsError(f"{name} is not a number: {v!r}") from exc
    if not d.is_finite() or d < 0:
        raise SettingsError(f"{name} must be a finite non-negative number")
    return d


def load_cost_settings(path: Path = DEFAULT_SETTINGS_FILE) -> tuple[CostSettings, dict[str, str]]:
    try:
        hashes = settings_hashes(path)
        text = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n").decode("utf-8")
        doc = tomllib.loads(text)
        fees, kappa, impact = doc["fees"], doc["kappa_bps"], doc["impact"]
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise SettingsError(f"cannot read settings {path}: {exc}") from exc
    scen = tuple(fees.get("scenarios_bps", ()))
    if not scen or any(not isinstance(x, int) or x not in FEE_SCENARIOS_BPS for x in scen):
        raise SettingsError(f"fees.scenarios_bps must be a subset of {FEE_SCENARIOS_BPS}")
    if fees.get("basis") not in FEE_BASES:
        raise SettingsError(f"fees.basis must be one of {FEE_BASES}")
    if fees.get("status") != FEE_STATUS_UNCONFIRMED:
        raise SettingsError("fees.status must stay FEE_UNCONFIRMED (no Upbit account fee is confirmed)")
    if impact.get("status") != "ASSUMED":
        raise SettingsError("impact.status must stay ASSUMED")
    if set(kappa) != set(SCENARIOS):
        raise SettingsError(f"kappa_bps must list exactly {sorted(SCENARIOS)}")
    kap = tuple(sorted((k, _dec(v, f"kappa_bps.{k}")) for k, v in kappa.items()))
    for k, v in kap:
        if v != SCENARIOS[k].kappa_bps:
            raise SettingsError(f"kappa_bps.{k} = {v} differs from the scenario table ({SCENARIOS[k].kappa_bps})")
    ref_bps = _dec(impact.get("ref_bps"), "impact.ref_bps")
    ref_cap = _dec(impact.get("ref_capital_krw"), "impact.ref_capital_krw")
    limit = _dec(impact.get("capacity_limit_krw"), "impact.capacity_limit_krw")
    if ref_cap <= 0 or limit <= 0:
        raise SettingsError("impact capital references must be positive")
    return CostSettings(scen, fees["basis"], fees["status"], kap, ref_bps, ref_cap, limit, impact["status"]), hashes


def cost_model(settings: CostSettings, fee_bps: int, scenario: str, capital: Decimal, *, impact: bool = True,
               fee_basis: str | None = None) -> tuple[CostModel, bool]:
    """CostModel for one fee scenario, fill scenario and planned capital. Returns (model, capacity_verified)."""
    if fee_bps not in settings.fee_scenarios_bps:
        raise SettingsError(f"fee {fee_bps} bp is not a configured scenario {settings.fee_scenarios_bps}")
    if scenario not in SCENARIOS:
        raise SettingsError(f"unknown scenario {scenario!r}")
    if impact:
        iota, verified = impact_bps_for_capital(capital, settings.impact_ref_bps, settings.impact_ref_capital,
                                                settings.capacity_limit)
    else:
        iota, verified = Decimal(0), True
    basis = fee_basis or settings.fee_basis
    return CostModel.scenario(fee_bps, settings.kappa(scenario), iota, basis), verified
