"""Upbit public REST candles (day, 60-minute) for v0.6: fetch, paginate, validate. Read-only.

Endpoints (https://docs.upbit.com/kr/reference/list-candles-days, checked 2026-10-12):
  GET /v1/candles/days          market, to, count (max 200)
  GET /v1/candles/minutes/60    market, to, count (max 200)
`to` returns candles *before* that time; a `to` without a timezone is ambiguous in the docs,
so MoneyLab always sends UTC with a trailing `Z`. Candles are only created for buckets that had
a trade, so a missing bucket is not necessarily a data error (it is reported, never filled).
Rate limit: 10 requests/s per IP, shared by the candle group (response header
`Remaining-Req: group=candles; ...`).

Response fields, verified against live responses on 2026-10-12 (10 day + 10 hour candles,
KRW-BTC, HTTP 200; first seen on stdout at 01:42 UTC, then stored and verified at 09:47 UTC under
data/raw/upbit/candles_v06/{day,hour}_KRW-BTC_20261012T0947*) and the docs:
  market, candle_date_time_utc, candle_date_time_kst   bucket START, "yyyy-MM-ddTHH:mm:ss", no tz
  opening_price (first trade), high_price, low_price, trade_price (close; current price while
  the bucket is open), timestamp (ms of the bucket's last tick), candle_acc_trade_price,
  candle_acc_trade_volume; day only: prev_closing_price, change_price, change_rate; minutes: unit.
Observed: newest first; day boundary 00:00 UTC (= 09:00 KST); one day candle's last tick was 7 ms
after its boundary; the newest candle is still in progress.
Unverified: sort order is not documented (we sort ourselves); whether `to` is exclusive (we
de-duplicate either way); first available date; whether past candles are revised later.

Retries happen here (not in urllib3): build the HttpClient with `retries=0` (see
`candle_http_client`). 451/401/403/418 and other 4xx are never retried.

Raw bytes: `CandlePage.body` is `requests.Response.content`, i.e. the response body AFTER the
transfer encoding is undone (Upbit sends `Content-Encoding: gzip`; urllib3 decompresses it).
That decoded body is what candle_store writes to pages/NNNN.json and what its SHA-256 covers.
The compressed wire bytes are not kept; the `Content-Encoding` header stays in the page meta.
Parsing uses the same bytes, so the stored file is exactly what the quality report was built from.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime
from typing import Any

from moneylab.core.exceptions import ApiError, NetworkError, ProviderError
from moneylab.core.http import HttpClient, HttpDiagnostics
from moneylab.core.ratelimit import SlidingWindowLimiter
from moneylab.core.redaction import redact_headers
from moneylab.providers.upbit.endpoints import REST_BASE_URL, validate_market

log = logging.getLogger(__name__)

PROVIDER = "upbit"
MAX_COUNT = 200
KST = timedelta(hours=9)
# Interval name -> (REST path, bucket length)
INTERVALS: dict[str, tuple[str, timedelta]] = {
    "day": ("/v1/candles/days", timedelta(days=1)),
    "hour": ("/v1/candles/minutes/60", timedelta(hours=1)),
}
# Below the documented 10/s so other candle-group callers on the same IP keep headroom.
DEFAULT_LIMITS = ((4, 1.0),)
RETRY_STATUSES = (429, 500, 502, 503, 504)  # everything else (401/403/418/451, other 4xx) stops at once
MAX_RETRY_WAIT_SECONDS = 60.0  # a longer Retry-After ends the pull instead of sleeping
# A bucket counts as closed only this long after its end: late ticks (7 ms observed) still land
# in the previous bucket, so a just-closed candle may change.
DEFAULT_SETTLE_SECONDS = 120.0
# timestamp (last tick) this far past the bucket end is reported as a warning.
LAST_TICK_TOLERANCE = timedelta(seconds=60)

_TS_FORMAT = "%Y-%m-%dT%H:%M:%S"
_PRICE_FIELDS = ("opening_price", "high_price", "low_price", "trade_price")
_ACC_FIELDS = ("candle_acc_trade_price", "candle_acc_trade_volume")


class CandleParseError(ValueError):
    """A candle row does not have the verified structure (missing field, wrong type, bad time)."""


def candle_http_client(timeout: float = 10.0, user_agent: str = "MoneyLab/0.3") -> HttpClient:
    """HttpClient for candles: no urllib3 retries, so `UpbitCandleClient` owns the retry policy."""
    return HttpClient(REST_BASE_URL, timeout=timeout, retries=0, user_agent=user_agent)


def utc_iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime(_TS_FORMAT) + "Z"


def _require_utc(t: datetime, name: str) -> datetime:
    if t.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware (UTC)")
    return t.astimezone(UTC)


def is_aligned(t: datetime, interval: str) -> bool:
    t = t.astimezone(UTC)
    if t.second or t.microsecond or t.minute:
        return False
    return interval != "day" or t.hour == 0


# --- parsing ----------------------------------------------------------------------------------

@dataclass(frozen=True)
class Candle:
    market: str
    interval: str
    start_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    acc_trade_price: Decimal
    acc_trade_volume: Decimal
    last_tick_ms: int

    @property
    def end_utc(self) -> datetime:
        return self.start_utc + INTERVALS[self.interval][1]

    def values(self) -> tuple:
        """Everything except identity, to tell identical duplicates from conflicting ones."""
        return (self.open, self.high, self.low, self.close, self.acc_trade_price, self.acc_trade_volume,
                self.last_tick_ms)

    def to_record(self) -> dict[str, Any]:
        """JSON-safe row; Decimals as strings so no precision is lost."""
        return {"market": self.market, "interval": self.interval, "start_utc": utc_iso(self.start_utc),
                "end_utc": utc_iso(self.end_utc), "open": str(self.open), "high": str(self.high),
                "low": str(self.low), "close": str(self.close), "acc_trade_price": str(self.acc_trade_price),
                "acc_trade_volume": str(self.acc_trade_volume), "last_tick_ms": self.last_tick_ms}


def decode_candles(body: bytes) -> list[Any]:
    """Response body -> list, numbers with a fraction as Decimal (exact, no float rounding)."""
    try:
        data = json.loads(body.decode("utf-8"), parse_float=Decimal)
    except (UnicodeDecodeError, ValueError) as exc:
        raise CandleParseError(f"body is not valid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise CandleParseError(f"expected a JSON list, got {type(data).__name__}")
    return data


def _dec(row: dict[str, Any], key: str) -> Decimal:
    v = row.get(key)
    if isinstance(v, bool) or not isinstance(v, (Decimal, int)):
        raise CandleParseError(f"{key}: expected a number, got {v!r}")
    d = Decimal(v)
    if not d.is_finite():
        raise CandleParseError(f"{key}: not finite ({v!r})")
    return d


def _time(row: dict[str, Any], key: str) -> datetime:
    v = row.get(key)
    if not isinstance(v, str):
        raise CandleParseError(f"{key}: expected a string, got {v!r}")
    try:
        return datetime.strptime(v, _TS_FORMAT)
    except ValueError as exc:
        raise CandleParseError(f"{key}: unexpected format {v!r}") from exc


def parse_candle(row: Any, market: str, interval: str) -> Candle:
    if not isinstance(row, dict):
        raise CandleParseError(f"expected an object, got {type(row).__name__}")
    if row.get("market") != market:
        raise CandleParseError(f"market {row.get('market')!r} != requested {market!r}")
    if interval == "hour" and row.get("unit") != 60:
        raise CandleParseError(f"unit {row.get('unit')!r} != 60")
    start = _time(row, "candle_date_time_utc").replace(tzinfo=UTC)
    kst = _time(row, "candle_date_time_kst")
    if kst != (start + KST).replace(tzinfo=None):
        raise CandleParseError(f"candle_date_time_kst {kst} is not candle_date_time_utc + 9 h")
    if not is_aligned(start, interval):
        raise CandleParseError(f"{interval} candle start {utc_iso(start)} is not on a bucket boundary")
    ts = row.get("timestamp")
    if isinstance(ts, bool) or not isinstance(ts, int):
        raise CandleParseError(f"timestamp: expected integer ms, got {ts!r}")
    o, h, lo, c = (_dec(row, k) for k in _PRICE_FIELDS)
    atp, atv = (_dec(row, k) for k in _ACC_FIELDS)
    return Candle(market, interval, start, o, h, lo, c, atp, atv, ts)


def value_problems(c: Candle) -> list[str]:
    """Implausible values. Reported, never corrected; the row is kept so the report is complete."""
    out = []
    if min(c.open, c.high, c.low, c.close) <= 0:
        out.append("non-positive price")
    if c.low > min(c.open, c.close) or c.high < max(c.open, c.close) or c.low > c.high:
        out.append("OHLC inconsistent")
    if c.acc_trade_volume < 0 or c.acc_trade_price < 0:
        out.append("negative accumulated trade value/volume")
    return out


def closed_as_of(candles: Iterable[Candle], t: datetime) -> list[Candle]:
    """Candles a decision at time t may use: bucket already ended (end <= t). No look-ahead."""
    t = _require_utc(t, "t")
    return [c for c in candles if c.end_utc <= t]


# --- fetching ---------------------------------------------------------------------------------

@dataclass
class CandlePage:
    url: str
    params: dict[str, Any]
    status_code: int
    headers: dict[str, str]
    body: bytes
    received_utc: datetime
    attempts: int
    rows: list[Any] = field(default_factory=list)

    @property
    def server_date(self) -> datetime | None:
        raw = self.headers.get("Date") or self.headers.get("date")
        if not raw:
            return None
        try:
            return parsedate_to_datetime(raw).astimezone(UTC)
        except (TypeError, ValueError):
            return None

    def reference_now(self) -> datetime:
        """Earlier of local receive time and server Date: a fast local clock must not make an
        open bucket look closed."""
        server = self.server_date
        return min(self.received_utc, server) if server else self.received_utc

    def meta(self) -> dict[str, Any]:
        return {"url": self.url, "params": self.params, "status_code": self.status_code,
                "headers": self.headers, "received_utc": self.received_utc.isoformat(),
                "server_date": self.server_date.isoformat() if self.server_date else None,
                "attempts": self.attempts, "bytes": len(self.body)}  # saved before parsing: no row count


class UpbitCandleClient:
    """One page per call, with client-side rate limiting and a bounded retry policy."""

    def __init__(
        self, http: HttpClient, *, limiter: SlidingWindowLimiter | None = None, max_retries: int = 2,
        backoff_seconds: float = 0.5, sleep: Callable[[float], None] = time.sleep,
        utcnow: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self.http = http
        self.limiter = limiter or SlidingWindowLimiter(DEFAULT_LIMITS, sleep=sleep)
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep
        self.utcnow = utcnow

    def _retry_wait(self, attempt: int, status: int | None, headers: dict[str, str]) -> float:
        if status == 429:  # docs: retry from the next second
            try:
                return max(1.0, float(headers.get("Retry-After", 1.0)))
            except ValueError:
                return 1.0
        return self.backoff_seconds * (2 ** attempt)

    def fetch_page(self, market: str, interval: str, to: datetime | None = None,
                   count: int = MAX_COUNT) -> CandlePage:
        market = validate_market(market)
        if interval not in INTERVALS:
            raise ValueError(f"interval must be one of {sorted(INTERVALS)}, got {interval!r}")
        if not 1 <= count <= MAX_COUNT:
            raise ValueError(f"count must be 1..{MAX_COUNT}, got {count}")
        path = INTERVALS[interval][0]
        params: dict[str, Any] = {"market": market, "count": count}
        if to is not None:
            params["to"] = utc_iso(_require_utc(to, "to"))
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self.limiter.acquire()
            try:
                resp = self.http.request("GET", path, params=params)
            except NetworkError as exc:  # timeout, connection reset: retryable
                last_error = exc
                if attempt < self.max_retries:
                    log.warning("candles %s: %s (attempt %d), retrying", interval, exc, attempt + 1)
                    self.sleep(self._retry_wait(attempt, None, {}))
                    continue
                raise ProviderError(PROVIDER, f"{path}: {exc} after {attempt + 1} attempts", exc) from exc
            headers = redact_headers(dict(resp.headers))
            why = "not retried"
            if resp.status_code in RETRY_STATUSES:
                wait = self._retry_wait(attempt, resp.status_code, headers)
                if wait > MAX_RETRY_WAIT_SECONDS:  # the server asks for a long pause: stop, do not hammer
                    why = f"server asked to wait {wait:g} s, not retried"
                elif attempt < self.max_retries:
                    log.warning("candles %s: HTTP %s (attempt %d), retrying", interval, resp.status_code, attempt + 1)
                    self.sleep(wait)
                    continue
                else:
                    why = f"after {attempt + 1} attempts"
            if not resp.ok:
                diag = HttpDiagnostics.from_response(resp, getattr(resp, "elapsed_ms", 0.0))
                err = ApiError(f"HTTP {resp.status_code} {resp.reason}: GET {resp.url}", diag)
                raise ProviderError(PROVIDER, f"{path}: {err} ({why})", err) from err
            page = CandlePage(url=resp.url, params=dict(params), status_code=resp.status_code, headers=headers,
                              body=resp.content or b"", received_utc=self.utcnow(), attempts=attempt + 1)
            return page
        raise ProviderError(PROVIDER, f"{path}: retries exhausted", last_error)  # pragma: no cover


# --- pagination + quality ---------------------------------------------------------------------

@dataclass
class CandleQualityReport:
    market: str
    interval: str
    requested_start: str
    requested_end: str
    pages: int = 0
    rows_received: int = 0
    candles: int = 0
    first_start: str | None = None
    last_start: str | None = None
    reached_earliest: bool = False
    duplicates_identical: int = 0
    duplicates_conflicting: list[str] = field(default_factory=list)
    excluded_incomplete: int = 0
    excluded_out_of_range: int = 0
    gaps: list[dict[str, Any]] = field(default_factory=list)
    invalid: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def missing_buckets(self) -> int:
        return sum(g["missing"] for g in self.gaps)

    @property
    def ok(self) -> bool:
        """No conflicting duplicates and no implausible values. Gaps are reported, not fatal
        (Upbit omits buckets without trades); the study decides how many it accepts."""
        return not self.duplicates_conflicting and not self.invalid

    def to_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        d.update(ok=self.ok, missing_buckets=self.missing_buckets)
        return d


@dataclass
class CandlePull:
    candles: list[Candle]
    report: CandleQualityReport


class PageSink:
    """Where raw pages go before they are parsed (see candle_store.CandleRawStore)."""

    def save_page(self, index: int, page: CandlePage) -> None:  # pragma: no cover - interface
        raise NotImplementedError


def _gaps(starts: list[datetime], step: timedelta) -> list[dict[str, Any]]:
    out = []
    for a, b in zip(starts, starts[1:]):
        missing = int((b - a) / step) - 1
        if missing > 0:
            out.append({"after": utc_iso(a), "before": utc_iso(b), "missing": missing})
    return out


def pull_candles(
    client: UpbitCandleClient, market: str, interval: str, start: datetime, end: datetime, *,
    sink: PageSink | None = None, settle_seconds: float = DEFAULT_SETTLE_SECONDS, max_pages: int = 10_000,
    page_count: int = MAX_COUNT,
) -> CandlePull:
    """Closed candles with start in [start, end), oldest first, de-duplicated, never filled.

    Pages of `page_count` rows are requested backwards from `end`. Each raw page goes to `sink`
    *before* parsing, so a parse failure still leaves the evidence on disk. A candle counts only if
    its bucket ended at least `settle_seconds` before the page's reference time (in-progress
    candles are dropped).
    """
    market = validate_market(market)
    if interval not in INTERVALS:
        raise ValueError(f"interval must be one of {sorted(INTERVALS)}, got {interval!r}")
    if not 1 <= page_count <= MAX_COUNT:
        raise ValueError(f"page_count must be 1..{MAX_COUNT}, got {page_count}")
    if max_pages < 1:
        raise ValueError(f"max_pages must be >= 1, got {max_pages}")
    start, end = _require_utc(start, "start"), _require_utc(end, "end")
    if not (is_aligned(start, interval) and is_aligned(end, interval)):
        raise ValueError(f"start and end must be on {interval} bucket boundaries (UTC)")
    if start >= end:
        raise ValueError("start must be before end")
    step = INTERVALS[interval][1]
    settle = timedelta(seconds=settle_seconds)
    rep = CandleQualityReport(market, interval, utc_iso(start), utc_iso(end))
    kept: dict[datetime, Candle] = {}
    closed_cutoff: datetime | None = None
    to = end
    while True:
        if rep.pages >= max_pages:
            raise ProviderError(PROVIDER, f"page limit {max_pages} reached before {utc_iso(start)}")
        page = client.fetch_page(market, interval, to, page_count)
        index = rep.pages
        rep.pages += 1
        if sink is not None:
            sink.save_page(index, page)  # storage failure aborts the pull (raises)
        page.rows = decode_candles(page.body)
        rep.rows_received += len(page.rows)
        if not page.rows:
            rep.reached_earliest = True
            break
        parsed = [parse_candle(r, market, interval) for r in page.rows]
        cutoff = page.reference_now() - settle
        closed_cutoff = cutoff if closed_cutoff is None else min(closed_cutoff, cutoff)
        for c in parsed:
            if c.end_utc > cutoff:
                rep.excluded_incomplete += 1
            elif not start <= c.start_utc < end:
                rep.excluded_out_of_range += 1
            elif c.start_utc in kept:
                if kept[c.start_utc].values() == c.values():
                    rep.duplicates_identical += 1
                else:  # keep the first received; the conflict makes the report not ok
                    rep.duplicates_conflicting.append(utc_iso(c.start_utc))
            else:
                kept[c.start_utc] = c
        earliest = min(c.start_utc for c in parsed)
        if earliest <= start:
            break
        if earliest >= to:
            raise ProviderError(PROVIDER, f"pagination did not move before {utc_iso(to)} (earliest {utc_iso(earliest)})")
        to = earliest

    candles = [kept[k] for k in sorted(kept)]
    rep.candles = len(candles)
    if candles:
        rep.first_start, rep.last_start = utc_iso(candles[0].start_utc), utc_iso(candles[-1].start_utc)
        starts = [c.start_utc for c in candles]
        rep.gaps = _gaps(starts, step)
        # Buckets after the last candle that should already be closed are missing too.
        last_expected = min(end, closed_cutoff or end) - step
        trailing = int((last_expected - starts[-1]) / step) if last_expected > starts[-1] else 0
        if trailing > 0:
            rep.gaps.append({"after": utc_iso(starts[-1]), "before": None, "missing": trailing})
        if starts[0] > start and rep.reached_earliest:  # nothing older exists: not a gap
            # An empty page is the only end-of-history signal; the listing date is unverified, so
            # say so instead of silently treating a mid-history empty page as the start.
            rep.warnings.append(f"data starts at {utc_iso(starts[0])}: empty page before it, treated as "
                                f"earliest available (unverified)")
        elif starts[0] > start:  # older candles exist, so the leading buckets are missing
            rep.gaps.insert(0, {"after": None, "before": utc_iso(starts[0]),
                                "missing": int((starts[0] - start) / step)})
    else:
        rep.warnings.append("no closed candles in the requested range")
    for c in candles:
        problems = value_problems(c)
        if problems:
            rep.invalid.append({"start_utc": utc_iso(c.start_utc), "problems": problems})
        tick = datetime.fromtimestamp(c.last_tick_ms / 1000, UTC)
        if tick < c.start_utc or tick > c.end_utc + LAST_TICK_TOLERANCE:
            rep.warnings.append(f"{utc_iso(c.start_utc)}: last tick {tick.isoformat()} outside bucket")
    return CandlePull(candles, rep)
