"""Pre-registered study configuration (configs/research_v04.toml) and its hashes.

The config file and the preregistration document are hashed byte for byte; both hashes go into
every run manifest, and `research-final` compares them before it opens the test split.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from moneylab.storage.atomic import sha256_file

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "configs" / "research_v04.toml"


@dataclass(frozen=True)
class StudyConfig:
    name: str
    version: int
    market: str
    provenance_required: str
    min_sessions_for_paper: int
    nominal_session_seconds: float
    grid_seconds: float
    warmup_seconds: float
    stale_book_seconds: float
    gap_seconds: float
    horizons: tuple[int, ...]
    sizes_btc: tuple[float, ...]
    delays_ms: tuple[int, ...]
    train: float
    validation: float
    test: float
    embargo_seconds: float
    fee_bps_scenarios: tuple[float, ...]
    account_fee_bps: float | None
    decision_size_btc: float
    decision_delay_ms: int
    quantiles: int
    ci_level: float
    bootstrap_resamples: int
    bootstrap_seed: int
    block_seconds_min: float
    block_horizon_multiple: float
    hac_extra_lag_seconds: float
    fdr_alpha: float
    min_valid_share: float
    min_quantile_monotonicity: float
    min_gross_to_cost: float
    robust_delay_ms: int
    robust_fee_buffer_bps: float
    min_nonoverlapping_triggers: int
    min_evidence_triggers: int
    max_missing_rate: float
    clock_warn_ms: float
    clock_unstable_ms: float
    clock_unstable_seconds: float
    clock_unstable_min_measurements: int
    clock_stale_seconds: float
    signals: tuple[str, ...]
    state: tuple[str, ...]
    config_path: Path | None = None
    preregistration_path: Path | None = None
    config_sha256: str | None = None
    preregistration_sha256: str | None = None
    overrides: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if abs(self.train + self.validation + self.test - 1.0) > 1e-9:
            raise ValueError("train + validation + test must be 1")
        if min(self.train, self.validation, self.test) <= 0:
            raise ValueError("every split share must be > 0")
        if self.grid_seconds <= 0 or any(h <= 0 for h in self.horizons):
            raise ValueError("grid and horizons must be > 0")
        if any(abs(h / self.grid_seconds - round(h / self.grid_seconds)) > 1e-9 for h in self.horizons):
            raise ValueError("horizons must be multiples of grid_seconds")
        if not self.fee_bps_scenarios or min(self.fee_bps_scenarios) < 0:
            raise ValueError("fee_bps_scenarios must be non-empty and >= 0")
        if self.decision_size_btc not in self.sizes_btc or self.decision_delay_ms not in self.delays_ms:
            raise ValueError("decision size/delay must be among the label scenarios")
        if self.robust_delay_ms not in self.delays_ms:
            raise ValueError("robust_delay_ms must be among delays_ms")
        if self.provenance_required != "real":
            raise ValueError("the study only accepts provenance = real as evidence")

    @property
    def decision_fee_bps(self) -> float:
        """Confirmed account fee if set, otherwise the most expensive scenario (conservative)."""
        return self.account_fee_bps if self.account_fee_bps is not None else max(self.fee_bps_scenarios)

    @property
    def max_delay_seconds(self) -> float:
        return max(self.delays_ms) / 1000.0

    def hashes(self) -> dict[str, str | None]:
        return {"config_sha256": self.config_sha256, "preregistration_sha256": self.preregistration_sha256}


def load_config(path: str | Path = DEFAULT_CONFIG, **overrides: Any) -> StudyConfig:
    """Load and hash the config. `overrides` (dry runs only) are recorded, never silent."""
    path = Path(path)
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    st, sa, la, sp, co, sx, de, fe, ck = (raw[k] for k in ("study", "sampling", "labels", "split", "costs", "stats",
                                                           "decision", "features", "clock"))
    prereg = (path.parent.parent / st["preregistration"]).resolve()
    values: dict[str, Any] = dict(
        name=st["name"], version=int(st["version"]), market=st["market"],
        provenance_required=st["provenance_required"], min_sessions_for_paper=int(st["min_sessions_for_paper"]),
        nominal_session_seconds=float(st["nominal_session_seconds"]),
        grid_seconds=float(sa["grid_seconds"]), warmup_seconds=float(sa["warmup_seconds"]),
        stale_book_seconds=float(sa["stale_book_seconds"]), gap_seconds=float(sa["gap_seconds"]),
        horizons=tuple(int(h) for h in la["horizons_seconds"]), sizes_btc=tuple(float(s) for s in la["sizes_btc"]),
        delays_ms=tuple(int(d) for d in la["delays_ms"]),
        train=float(sp["train"]), validation=float(sp["validation"]), test=float(sp["test"]),
        embargo_seconds=float(sp["embargo_seconds"]),
        fee_bps_scenarios=tuple(float(f) for f in co["fee_bps_scenarios"]),
        account_fee_bps=None if co.get("account_fee_bps") is None else float(co["account_fee_bps"]),
        decision_size_btc=float(co["decision_size_btc"]), decision_delay_ms=int(co["decision_delay_ms"]),
        quantiles=int(sx["quantiles"]), ci_level=float(sx["ci_level"]),
        bootstrap_resamples=int(sx["bootstrap_resamples"]), bootstrap_seed=int(sx["bootstrap_seed"]),
        block_seconds_min=float(sx["block_seconds_min"]), block_horizon_multiple=float(sx["block_horizon_multiple"]),
        hac_extra_lag_seconds=float(sx["hac_extra_lag_seconds"]), fdr_alpha=float(sx["fdr_alpha"]),
        min_valid_share=float(de["min_valid_share"]), min_quantile_monotonicity=float(de["min_quantile_monotonicity"]),
        min_gross_to_cost=float(de["min_gross_to_cost"]), robust_delay_ms=int(de["robust_delay_ms"]),
        robust_fee_buffer_bps=float(de["robust_fee_buffer_bps"]),
        min_nonoverlapping_triggers=int(de["min_nonoverlapping_triggers"]),
        min_evidence_triggers=int(de["min_evidence_triggers"]), max_missing_rate=float(de["max_missing_rate"]),
        clock_warn_ms=float(ck["warn_ms"]), clock_unstable_ms=float(ck["unstable_ms"]),
        clock_unstable_seconds=float(ck["unstable_seconds"]),
        clock_unstable_min_measurements=int(ck["unstable_min_measurements"]),
        clock_stale_seconds=float(ck["stale_seconds"]),
        signals=tuple(fe["signals"]), state=tuple(fe["state"]),
    )
    unknown = set(overrides) - set(values)
    if unknown:
        raise ValueError(f"unknown config overrides {sorted(unknown)}")
    changed = {k: v for k, v in overrides.items() if values[k] != v}
    values.update(changed)
    return StudyConfig(**values, config_path=path, preregistration_path=prereg,
                       config_sha256=sha256_file(path),
                       preregistration_sha256=sha256_file(prereg) if prereg.exists() else None,
                       overrides=changed)
