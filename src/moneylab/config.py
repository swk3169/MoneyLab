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
    user_agent: str = "MoneyLab/0.1 (+research; read-only)"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

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
    )
