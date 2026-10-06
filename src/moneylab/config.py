"""Runtime settings loaded from environment variables (optionally via .env).

Only non-secret settings live here. v0.1 needs no credentials at all.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional at runtime
    load_dotenv = None


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    gamma_url: str = "https://gamma-api.polymarket.com"
    clob_url: str = "https://clob.polymarket.com"
    http_timeout: float = 10.0
    http_retries: int = 2
    data_dir: Path = Path("data")
    log_level: str = "INFO"
    user_agent: str = "MoneyLab/0.3 (+research; read-only)"
    # Recorder (v0.3). Switching fixture -> live recording is a settings change only.
    recorder_source: str = "polymarket"  # polymarket | fixture
    recorder_condition_ids: tuple[str, ...] = ()
    recorder_interval: float = 60.0
    recorder_metadata_refresh: float = 3600.0
    recorder_max_failures: int = 30
    # Upbit public WebSocket recorder. The endpoint is fixed to the documented public URL
    # (providers/upbit/endpoints.py) and is deliberately not configurable.
    upbit_markets: tuple[str, ...] = ("KRW-BTC",)
    upbit_orderbook_units: int = 30
    upbit_max_failures: int = 10

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def recordings_dir(self) -> Path:
        return self.raw_dir / "polymarket" / "recordings"

    @property
    def upbit_recordings_dir(self) -> Path:
        return self.raw_dir / "upbit" / "recordings"

    @property
    def upbit_fixture_recordings_dir(self) -> Path:
        return self.raw_dir / "upbit" / "recordings-fixture"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"


def load_settings() -> Settings:
    if load_dotenv is not None:
        load_dotenv(override=False)
    return Settings(
        gamma_url=os.getenv("POLYMARKET_GAMMA_URL", Settings.gamma_url).rstrip("/"),
        clob_url=os.getenv("POLYMARKET_CLOB_URL", Settings.clob_url).rstrip("/"),
        http_timeout=_env_float("MONEYLAB_HTTP_TIMEOUT", Settings.http_timeout),
        http_retries=_env_int("MONEYLAB_HTTP_RETRIES", Settings.http_retries),
        data_dir=Path(os.getenv("MONEYLAB_DATA_DIR", str(Settings.data_dir))),
        log_level=os.getenv("MONEYLAB_LOG_LEVEL", Settings.log_level).upper(),
        recorder_source=os.getenv("MONEYLAB_RECORDER_SOURCE", Settings.recorder_source).strip().lower(),
        recorder_condition_ids=tuple(
            c.strip() for c in os.getenv("MONEYLAB_RECORDER_CONDITION_IDS", "").split(",") if c.strip()
        ),
        recorder_interval=_env_float("MONEYLAB_RECORDER_INTERVAL", Settings.recorder_interval),
        recorder_metadata_refresh=_env_float("MONEYLAB_RECORDER_METADATA_REFRESH", Settings.recorder_metadata_refresh),
        recorder_max_failures=_env_int("MONEYLAB_RECORDER_MAX_FAILURES", Settings.recorder_max_failures),
        upbit_markets=tuple(
            m.strip().upper() for m in os.getenv("MONEYLAB_UPBIT_MARKETS", "KRW-BTC").split(",") if m.strip()
        ) or Settings.upbit_markets,
        upbit_orderbook_units=_env_int("MONEYLAB_UPBIT_ORDERBOOK_UNITS", Settings.upbit_orderbook_units),
        upbit_max_failures=_env_int("MONEYLAB_UPBIT_MAX_FAILURES", Settings.upbit_max_failures),
    )
