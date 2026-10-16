"""Raw evidence for candle pulls (v0.6). Nothing is overwritten; every write is atomic.

    <root>/<pull_id>/                 root is normally data/raw/upbit/candles_v06
      pull.json                       identity, provenance, origin, source, requested range, pull
                                      settings, page list, status (running | complete | failed),
                                      quality report, error
      pages/0000.json                 response body bytes as parsed: after the HTTP transfer
                                      encoding (gzip) is undone, before any JSON decoding; the
                                      SHA-256 covers these bytes, not the compressed wire bytes
      pages/0000.meta.json            request url + params, status, redacted headers, received
                                      time, server Date, attempts, byte count, SHA-256 of the bytes

`pull_id` = <interval>_<market>_<UTC start stamp>. A new pull always gets a new directory; an
existing directory or page file is an error, never replaced. Pages are written before they are
parsed, so a pull that fails on a malformed page still keeps that page.

`verify_candle_pull` only reads: it re-hashes every page, checks the file set, and replays the
stored pages through `pull_candles` (same settings, stored receive times and server Date) to show
the saved quality report follows from the saved bytes.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.core.exceptions import MoneyLabError
from moneylab.domain.market_events import PROVENANCES
from moneylab.providers.upbit.candles import (
    DEFAULT_SETTLE_SECONDS,
    INTERVALS,
    MAX_COUNT,
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
PULL_FILE = "pull.json"
SETTING_KEYS = ("settle_seconds", "page_count", "max_pages")


class CandleStoreError(MoneyLabError):
    """Raw evidence could not be written (or would overwrite something). The pull must stop."""


class CandleRawStore(PageSink):
    def __init__(self, pull_dir: Path, doc: dict[str, Any]):
        self.dir = Path(pull_dir)
        self.doc = doc

    @classmethod
    def create(
        cls, root: Path, market: str, interval: str, start: datetime, end: datetime, *, provenance: str,
        origin: str | None = None, settings: dict[str, Any] | None = None,
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
            "origin": origin,
            "source": {"provider": PROVIDER, "base_url": REST_BASE_URL, "endpoint": INTERVALS[interval][0],
                       "public_market_data_only": True},
            "market": market, "interval": interval,
            "requested_start": utc_iso(start), "requested_end": utc_iso(end),
            "settings": settings or {},
            "created_utc": created.isoformat(), "finished_utc": None,
            "status": "running", "pages": [], "report": None, "error": None,
        }
        store = cls(pull_dir, doc)
        store._write_doc()
        return store

    def _write_doc(self) -> None:
        try:
            atomic_write_json(self.dir / PULL_FILE, self.doc)
        except OSError as exc:
            raise CandleStoreError(f"cannot write {self.dir / PULL_FILE}: {exc}") from exc

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
    provenance: str, origin: str | None = None, settle_seconds: float = DEFAULT_SETTLE_SECONDS,
    page_count: int = MAX_COUNT, max_pages: int = 10_000,
    utcnow: Callable[[], datetime] = lambda: datetime.now(UTC),
    on_created: Callable[[CandleRawStore], None] | None = None,
) -> tuple[CandlePull, CandleRawStore]:
    """pull_candles with every raw page preserved; pull.json records the settings (for replay)
    and success or the failure. `on_created` learns the directory before the first request, so a
    caller can still point at the evidence of a failed pull."""
    settings = {"settle_seconds": settle_seconds, "page_count": page_count, "max_pages": max_pages}
    store = CandleRawStore.create(root, market, interval, start, end, provenance=provenance, origin=origin,
                                  settings=settings, utcnow=utcnow)
    if on_created is not None:
        on_created(store)
    try:
        pull = pull_candles(client, market, interval, start, end, sink=store, settle_seconds=settle_seconds,
                            page_count=page_count, max_pages=max_pages)
    except Exception as exc:
        try:
            store.finish(None, error=f"{type(exc).__name__}: {exc}", utcnow=utcnow)
        except CandleStoreError as store_exc:  # keep the original error; the disk is the problem
            log.error("could not record failure in pull.json: %s", store_exc)
        raise
    store.finish(pull, utcnow=utcnow)
    return pull, store


# --- verification (read-only) -----------------------------------------------------------------

class StoredPageClient:
    """Serves a pull's stored pages in order, in place of UpbitCandleClient. A request whose
    parameters differ from the stored request is an error: the replay must walk the same path."""

    def __init__(self, pull_dir: Path, metas: list[dict[str, Any]]):
        self.dir = Path(pull_dir)
        self.metas = metas
        self.served = 0

    def fetch_page(self, market: str, interval: str, to: datetime | None = None,
                   count: int = MAX_COUNT) -> CandlePage:
        if self.served >= len(self.metas):
            raise CandleStoreError(f"replay asked for page {self.served}, only {len(self.metas)} stored")
        meta = self.metas[self.served]
        params: dict[str, Any] = {"market": market, "count": count}
        if to is not None:
            params["to"] = utc_iso(to)
        if params != meta["params"]:
            raise CandleStoreError(f"page {self.served}: replay requested {params}, stored {meta['params']}")
        page = CandlePage(url=meta["url"], params=meta["params"], status_code=meta["status_code"],
                          headers=meta["headers"], body=(self.dir / "pages" / meta["file"]).read_bytes(),
                          received_utc=datetime.fromisoformat(meta["received_utc"]), attempts=meta["attempts"])
        self.served += 1
        return page


@dataclass
class CandleVerifyReport:
    pull_dir: str
    pull_id: str | None = None
    provenance: str | None = None
    status: str | None = None
    pages_checked: int = 0
    candles: int | None = None
    problems: list[str] = field(default_factory=list)
    replay: dict[str, Any] | None = None  # quality report recomputed from the stored bytes

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()} | {"ok": self.ok}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def verify_candle_pull(pull_dir: Path) -> CandleVerifyReport:
    """Hashes, file set, metadata consistency and an offline replay of one pull. Writes nothing."""
    pull_dir = Path(pull_dir)
    rep = CandleVerifyReport(str(pull_dir))
    try:
        doc = _read_json(pull_dir / PULL_FILE)
    except (OSError, ValueError) as exc:
        rep.problems.append(f"cannot read {PULL_FILE}: {exc}")
        return rep
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        rep.problems.append(f"{PULL_FILE} is not a {SCHEMA} document")
        return rep
    rep.pull_id, rep.provenance, rep.status = doc.get("pull_id"), doc.get("provenance"), doc.get("status")
    if rep.status != "complete":
        rep.problems.append(f"status is {rep.status!r}, not 'complete' (error: {doc.get('error')})")
    pages = doc.get("pages") or []
    if [p.get("index") for p in pages] != list(range(len(pages))):
        rep.problems.append("page indices are not 0..n-1 in order")
        return rep

    metas: list[dict[str, Any]] = []
    for p in pages:
        i = p["index"]
        body = pull_dir / p["file"]
        try:
            meta = _read_json(pull_dir / "pages" / f"{i:04d}.meta.json")
            digest = sha256_file(body)
            size = body.stat().st_size
        except (OSError, ValueError) as exc:
            rep.problems.append(f"page {i}: cannot read: {exc}")
            continue
        if digest != p.get("sha256") or digest != meta.get("sha256"):
            rep.problems.append(f"page {i}: SHA-256 mismatch (file {digest[:12]}, pull.json "
                                f"{str(p.get('sha256'))[:12]}, meta {str(meta.get('sha256'))[:12]})")
        if size != p.get("bytes") or size != meta.get("bytes"):
            rep.problems.append(f"page {i}: size {size} != recorded {p.get('bytes')}/{meta.get('bytes')}")
        if meta.get("index") != i or meta.get("file") != body.name or meta.get("params") != p.get("params"):
            rep.problems.append(f"page {i}: meta does not match pull.json")
        if meta.get("status_code") != 200:
            rep.problems.append(f"page {i}: HTTP {meta.get('status_code')}")
        metas.append(meta)
        rep.pages_checked += 1

    expected = {f"{p['index']:04d}{ext}" for p in pages for ext in (".json", ".meta.json")}
    try:
        present = {f.name for f in (pull_dir / "pages").iterdir()}
    except OSError as exc:
        present = set()
        rep.problems.append(f"cannot list pages/: {exc}")
    if present - expected:
        rep.problems.append(f"unlisted files in pages/: {sorted(present - expected)}")
    if expected - present:
        rep.problems.append(f"missing files in pages/: {sorted(expected - present)}")
    if rep.problems:
        return rep  # replaying damaged or incomplete evidence proves nothing

    settings = doc.get("settings") or {}
    if not set(SETTING_KEYS) <= settings.keys():
        rep.problems.append("pull.json has no pull settings; cannot replay")
        return rep
    client = StoredPageClient(pull_dir, metas)
    try:
        replay = pull_candles(
            client, doc["market"], doc["interval"],  # type: ignore[arg-type]
            _utc(doc["requested_start"]), _utc(doc["requested_end"]),
            settle_seconds=settings["settle_seconds"], page_count=settings["page_count"],
            max_pages=settings["max_pages"])
    except Exception as exc:  # any failure here means the saved report cannot be reproduced
        rep.problems.append(f"replay failed: {type(exc).__name__}: {exc}")
        return rep
    rep.replay = json.loads(json.dumps(replay.report.to_dict()))
    rep.candles = replay.report.candles
    if client.served != len(metas):
        rep.problems.append(f"replay used {client.served} of {len(metas)} stored pages")
    stored = doc.get("report") or {}
    if rep.replay != stored:
        diff = sorted(k for k in set(rep.replay) | set(stored) if rep.replay.get(k) != stored.get(k))
        rep.problems.append(f"stored report differs from replay in {diff}")
    return rep
