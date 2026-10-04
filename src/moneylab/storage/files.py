from __future__ import annotations

import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.domain.models import Market

log = logging.getLogger(__name__)


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


class RawStore:
    """Writes raw provider payloads to data/raw/<provider>/<timestamp>_<name>.json."""

    def __init__(self, raw_dir: Path, provider: str):
        self.dir = Path(raw_dir) / provider

    def save(self, name: str, payload: Any) -> Path | None:
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            path = self.dir / f"{_stamp()}_{name}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return path
        except OSError as exc:  # storage problems must not abort a scan
            log.warning("Could not save raw payload %s: %s", name, exc)
            return None

    __call__ = save


def save_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


CSV_FIELDS = [
    "source", "market_id", "question", "yes_price", "no_price", "best_bid", "best_ask",
    "spread", "volume", "volume_24h", "liquidity", "end_date", "slug", "condition_id", "url",
]


def save_markets_csv(markets: list[Market], processed_dir: Path, name: str = "scan") -> Path:
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    path = processed_dir / f"{_stamp()}_{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for m in markets:
            w.writerow({
                "source": m.source,
                "market_id": m.market_id,
                "question": m.question,
                "yes_price": m.yes_price,
                "no_price": m.no_price,
                "best_bid": m.best_bid,
                "best_ask": m.best_ask,
                "spread": m.spread,
                "volume": m.volume,
                "volume_24h": m.volume_24h,
                "liquidity": m.liquidity,
                "end_date": m.end_date.isoformat() if m.end_date else None,
                "slug": m.slug,
                "condition_id": m.condition_id,
                "url": m.url,
            })
    return path
