"""REST order-book snapshot recorder (CLOB `POST /books`, read-only).

Per poll:  [metadata refresh: GET /clob-markets/{id}, GET /rewards/markets/{id}]
           -> POST /books for every token of every configured market (one request)
           -> split the response by market, store raw items (store.py handles duplicates)

Works with any ClobSource: ClobApiSource (live HTTP) or TimelineFixtureSource (offline).
Switching from fixture to live data is a configuration change only (CLI `--source`).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from moneylab.core.exceptions import ApiError, NetworkError
from moneylab.core.redaction import redact_text
from moneylab.providers.polymarket.clob_client import ClobSource
from moneylab.providers.polymarket.recorder.base import (
    Failure,
    PolymarketRecorder,
    RecorderStatus,
    SourceExhausted,
    classify,
)

log = logging.getLogger(__name__)

SOURCE_ERRORS = (ApiError, NetworkError, OSError, LookupError, ValueError, TypeError)
EXCERPT = 2000


def _excerpt(payload: Any) -> str:
    try:
        text = json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = repr(payload)
    return redact_text(text[:EXCERPT])


class RestBookRecorder(PolymarketRecorder):
    name = "rest-books"
    source_label = "rest:POST /books"

    def __init__(self, source: ClobSource, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.source = source

    def _on_resume(self) -> None:
        # Finite sources (fixtures) restart from their beginning in a new process; skip what the
        # dataset already holds so recorded time never goes backwards.
        resume_after = getattr(self.source, "resume_after", None)
        done = [s.cursor.last_recorded_at for s in self.stores.values() if s.cursor.last_recorded_at is not None]
        if resume_after is not None and done:
            skipped = resume_after(min(done))
            if skipped:
                log.info("source fast-forwarded past %d already recorded observations", skipped)

    def _call(self, fn):
        self._throttle()
        return fn()

    # --- metadata -------------------------------------------------------------------------
    def _refresh_metadata(self) -> tuple[Failure, list[str]] | None:
        """Fetch market info + rewards for every market. A market keeps its last stored
        metadata on a transient failure; without any metadata it cannot be recorded."""
        c = self.config
        for cid, store in self.stores.items():
            try:
                info = self._call(lambda cid=cid: self.source.fetch_market_info(cid))
            except SourceExhausted:
                raise
            except SOURCE_ERRORS as exc:
                f = classify(exc, self.clock())
                if f.fatal_status is None and store.metadata is not None:
                    log.warning("%s: metadata refresh failed (%s); keeping stored version", cid, f.message)
                    continue
                return f, ([cid] if f.fatal_status is None else list(self.stores))
            rewards, rewards_error = None, None
            try:
                rewards = self._call(lambda cid=cid: self.source.fetch_rewards(cid))
            except SourceExhausted:
                raise
            except SOURCE_ERRORS as exc:
                f = classify(exc, self.clock())
                if f.fatal_status is not None:
                    return f, list(self.stores)
                rewards_error = f.message  # rewards are optional: record why they are missing
                log.warning("%s: rewards unavailable: %s", cid, f.message)
            try:
                if store.save_metadata(info, rewards, fetched_at=self.clock(), rebate_rate=c.rebate_rate,
                                       rebate_rate_source=c.rebate_rate_source, rewards_error=rewards_error):
                    log.info("%s: metadata version %s stored", cid, store.metadata_hash[:12])
            except (ValueError, TypeError) as exc:
                return Failure("bad_payload", f"/clob-markets/{cid}: {exc}",
                               diagnostics={"body_excerpt": _excerpt(info)}), [cid]
        return None

    # --- books ----------------------------------------------------------------------------
    def _poll_books(self) -> Failure | None:
        owner = {t: cid for cid, s in self.stores.items() for t in s.token_outcomes}
        tokens = list(owner)
        try:
            payload = self._call(lambda: self.source.fetch_books(tokens))
        except SourceExhausted:
            raise
        except SOURCE_ERRORS as exc:
            return classify(exc, self.clock())
        recorded_at = self.clock()
        items = payload.get("data") if isinstance(payload, dict) else payload  # tolerate an envelope
        if not isinstance(items, list):
            return Failure("bad_payload", f"/books returned {type(payload).__name__}, expected a list",
                           diagnostics={"body_excerpt": _excerpt(payload)})
        grouped: dict[str, list[dict[str, Any]]] = {cid: [] for cid in self.stores}
        for item in items:
            cid = owner.get(str(item.get("asset_id"))) if isinstance(item, dict) else None
            if cid is None:
                log.warning("/books item for an unrequested or missing asset_id ignored: %s", _excerpt(item)[:200])
                continue
            grouped[cid].append(item)
        for cid, books in grouped.items():
            expected = self.stores[cid].token_outcomes
            missing = [t for t in expected if t not in {str(b.get("asset_id")) for b in books}]
            if not books:
                self._record_failure(Failure("bad_payload", f"/books returned no book for market {cid}"),
                                     recorded_at, [cid])
                continue
            try:
                self._record_books(cid, books, recorded_at, missing)
            except (ValueError, TypeError) as exc:
                self._record_failure(Failure("bad_payload", f"unusable book for {cid}: {exc}",
                                             diagnostics={"body_excerpt": _excerpt(books)}), recorded_at, [cid])
        return None

    # --- loop -----------------------------------------------------------------------------
    def _run_loop(self) -> RecorderStatus:
        c = self.config
        started = self.clock()
        next_metadata: float | None = None
        while True:
            stop = self._should_stop(started)
            if stop is not None:
                return stop
            tick = self.clock()
            self.report.polls += 1
            failure, cids = None, None
            try:
                if next_metadata is None or tick >= next_metadata:
                    meta_failure = self._refresh_metadata()
                    if meta_failure is None:
                        next_metadata = tick + c.metadata_refresh
                    else:
                        failure, cids = meta_failure
                if failure is None:
                    failure = self._poll_books()
            except SourceExhausted:
                self.report.polls -= 1
                return RecorderStatus.SOURCE_EXHAUSTED
            now = self.clock()
            if failure is None:
                self.consecutive_failures = 0
                for store in self.stores.values():
                    store.update_state(now, consecutive_failures=0, last_success_at=now)
                self._wait(tick + c.interval - self.clock())
                continue
            self.consecutive_failures += 1
            self._record_failure(failure, now, cids)
            if failure.fatal_status is not None:
                log.error("Recorder stopped: %s", failure.message)
                return failure.fatal_status
            if self.consecutive_failures >= c.max_consecutive_failures:
                log.error("Recorder stopped after %d consecutive failures", self.consecutive_failures)
                return RecorderStatus.FAILED
            self._wait(self._backoff_delay(failure))
