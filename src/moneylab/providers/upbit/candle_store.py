"""Raw evidence for candle pulls (v0.6). Nothing is overwritten; every write is atomic.

    <root>/<pull_id>/                 root is normally data/raw/upbit/candles_v06
      pull.json                       identity, provenance, source, requested range, page list,
                                      status (running | complete | failed), quality report, error
      pages/0000.json                 exact response bytes, as received
      pages/0000.meta.json            request url + params, status, redacted headers, received
                                      time, server Date, attempts, byte count, SHA-256 of the bytes

`pull_id` = <interval>_<market>_<UTC start stamp>. A new pull always gets a new directory; an
existing directory or page file is an error, never replaced. Pages are written before they are
parsed, so a pull that fails on a malformed page still keeps that page.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.core.exceptions import MoneyLabError
from moneylab.domain.market_events import PROVENANCES
from moneylab.providers.upbit.candles import (
    INTERVALS,
    PROVIDER,
    CandlePage,
    CandlePull,
    PageSink,
    UpbitCandleClient,
    pull_candles,
    utc_iso,
)
from moneylab.providers.upbit.endpoints import REST_BASE_URL, validate_market
from moneylab.storage.atomic import atomic_write_bytes, atomic_write_json, sha256_file

log = logging.getLogger(__name__)

SCHEMA = "moneylab.upbit.candle_pull/1"
DEFAULT_SUBDIR = Path("upbit") / "candles_v06"


class CandleStoreError(MoneyLabError):
    """Raw evidence could not be written (or would overwrite something). The pull must stop."""


class CandleRawStore(PageSink):
    def __init__(self, pull_dir: Path, doc: dict[str, Any]):
        self.dir = Path(pull_dir)
        self.doc = doc

    @classmethod
    def create(
        cls, root: Path, market: str, interval: str, start: datetime, end: datetime, *, provenance: str,
        utcnow: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> CandleRawStore:
        market = validate_market(market)
        if interval not in INTERVALS:
            raise ValueError(f"interval must be one of {sorted(INTERVALS)}, got {interval!r}")
        if provenance not in PROVENANCES:
            raise ValueError(f"provenance must be one of {PROVENANCES}, got {provenance!r}")
        created = utcnow().astimezone(UTC)
        pull_id = f"{interval}_{market}_{created.strftime('%Y%m%dT%H%M%S%fZ')}"
        pull_dir = Path(root) / pull_id
        try:
            Path(root).mkdir(parents=True, exist_ok=True)
            pull_dir.mkdir(exist_ok=False)
            (pull_dir / "pages").mkdir(exist_ok=False)
        except FileExistsError as exc:
            raise CandleStoreError(f"{pull_dir} already exists; refusing to overwrite") from exc
        except OSError as exc:
            raise CandleStoreError(f"cannot create {pull_dir}: {exc}") from exc
        doc = {
            "schema": SCHEMA, "pull_id": pull_id, "provenance": provenance, "synthetic": provenance != "real",
            "source": {"provider": PROVIDER, "base_url": REST_BASE_URL, "endpoint": INTERVALS[interval][0],
                       "public_market_data_only": True},
            "market": market, "interval": interval,
            "requested_start": utc_iso(start), "requested_end": utc_iso(end),
            "created_utc": created.isoformat(), "finished_utc": None,
            "status": "running", "pages": [], "report": None, "error": None,
        }
        store = cls(pull_dir, doc)
        store._write_doc()
        return store

    def _write_doc(self) -> None:
        try:
            atomic_write_json(self.dir / "pull.json", self.doc)
        except OSError as exc:
            raise CandleStoreError(f"cannot write {self.dir / 'pull.json'}: {exc}") from exc

    def save_page(self, index: int, page: CandlePage) -> None:
        body_path = self.dir / "pages" / f"{index:04d}.json"
        meta_path = self.dir / "pages" / f"{index:04d}.meta.json"
        if body_path.exists() or meta_path.exists():
            raise CandleStoreError(f"{body_path} already exists; refusing to overwrite")
        try:
            atomic_write_bytes(body_path, page.body)
            digest = sha256_file(body_path)
            meta = page.meta() | {"index": index, "file": body_path.name, "sha256": digest}
            atomic_write_json(meta_path, meta)
        except OSError as exc:
            raise CandleStoreError(f"cannot write raw page {index}: {exc}") from exc
        self.doc["pages"].append({"index": index, "file": f"pages/{body_path.name}", "sha256": digest,
                                  "bytes": len(page.body), "params": page.params,
                                  "received_utc": page.received_utc.isoformat()})
        self._write_doc()

    def finish(self, pull: CandlePull | None, error: str | None = None,
               utcnow: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self.doc.update(status="failed" if error else "complete", error=error,
                        finished_utc=utcnow().astimezone(UTC).isoformat(),
                        report=pull.report.to_dict() if pull else None)
        self._write_doc()


def pull_to_store(
    client: UpbitCandleClient, root: Path, market: str, interval: str, start: datetime, end: datetime, *,
    provenance: str, **pull_kwargs: Any,
) -> tuple[CandlePull, CandleRawStore]:
    """pull_candles with every raw page preserved; pull.json records success or the failure."""
    store = CandleRawStore.create(root, market, interval, start, end, provenance=provenance)
    try:
        pull = pull_candles(client, market, interval, start, end, sink=store, **pull_kwargs)
    except Exception as exc:
        try:
            store.finish(None, error=f"{type(exc).__name__}: {exc}")
        except CandleStoreError as store_exc:  # keep the original error; the disk is the problem
            log.error("could not record failure in pull.json: %s", store_exc)
        raise
    store.finish(pull)
    return pull, store
