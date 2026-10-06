"""Provider-neutral recorder machinery shared by every market-data recorder.

What lives here is independent of any exchange: run status, failure classification of HTTP
errors, exponential backoff with jitter, Retry-After parsing and per-record checksums.
Concrete recorders (Polymarket REST, Upbit WebSocket) decide how observations arrive and how
they are stored.

Failure policy (no retries of policy decisions, no bypass of any kind):
  HTTP 451          -> stop immediately, status `blocked_http_451`; MoneyLab does not infer the cause
  HTTP 401 / 403    -> stop immediately, status `access_denied` (cause not determined)
  HTTP 418          -> temporary ban: wait the server-stated duration, or stop (`banned_http_418`)
                       when that is longer than the recorder is allowed to wait
  HTTP 429          -> wait Retry-After (or backoff), then continue
  anything else     -> exponential backoff with jitter; N consecutive failures -> `failed`
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from enum import StrEnum
from typing import Any

from moneylab.core.exceptions import ApiError, NetworkError
from moneylab.core.redaction import redact_text
from moneylab.storage.atomic import sha256_of


class RecorderStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"  # reached max_polls / duration
    STOPPED = "stopped"  # stop() or Ctrl+C
    SOURCE_EXHAUSTED = "source_exhausted"  # replay/fixture source has no more data
    BLOCKED_HTTP_451 = "blocked_http_451"
    ACCESS_DENIED = "access_denied"  # 401 / 403
    BANNED_HTTP_418 = "banned_http_418"  # temporary ban longer than the recorder may wait
    FAILED = "failed"  # too many consecutive failures, or unusable configuration


FATAL_STATUSES = frozenset({
    RecorderStatus.BLOCKED_HTTP_451, RecorderStatus.ACCESS_DENIED, RecorderStatus.BANNED_HTTP_418,
    RecorderStatus.FAILED,
})


class SourceExhausted(Exception):
    """Raised by finite (fixture/replay) sources when there is no more data."""


@dataclass(frozen=True)
class Failure:
    """A classified acquisition failure."""

    category: str  # http_451 | access_denied | banned | rate_limited | http | network | bad_payload | ...
    message: str
    status_code: int | None = None
    retry_after: float | None = None
    diagnostics: dict[str, Any] | None = None

    @property
    def fatal_status(self) -> RecorderStatus | None:
        if self.category == "http_451":
            return RecorderStatus.BLOCKED_HTTP_451
        if self.category == "access_denied":
            return RecorderStatus.ACCESS_DENIED
        return None

    def to_record(self) -> dict[str, Any]:
        out: dict[str, Any] = {"category": self.category, "status_code": self.status_code, "message": self.message}
        if self.retry_after is not None:
            out["retry_after"] = self.retry_after
        if self.diagnostics is not None:
            out["diagnostics"] = self.diagnostics
        return out


def header(headers: dict[str, str], name: str) -> str | None:
    low = name.lower()
    return next((v for k, v in headers.items() if k.lower() == low), None)


def parse_retry_after(value: str | None, now: float) -> float | None:
    """Retry-After is either delta-seconds or an HTTP-date (RFC 9110)."""
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, when.timestamp() - now)


NOTE_451 = ("HTTP 451 received. The server did not state which client attribute caused it; "
            "MoneyLab does not infer one. Recorder stopped without retrying.")


def classify(exc: Exception, now: float) -> Failure:
    """Classify an HttpClient error (ApiError / NetworkError) or a parsing error."""
    if isinstance(exc, ApiError):
        d = exc.diagnostics
        code = d.status_code
        if code == 451:
            # Facts only: status, reason, the (already redacted) body and the headers the
            # server sent. No conclusion about why access is restricted.
            return Failure("http_451", f"HTTP 451 {d.reason or ''}: {d.method} {d.url}".strip(), 451, diagnostics={
                "status_code": code, "reason": d.reason, "url": d.url, "headers": d.headers,
                "body_excerpt": d.body_excerpt, "note": NOTE_451,
            })
        if code in (401, 403):
            return Failure("access_denied", f"HTTP {code} {d.reason or ''}: {d.method} {d.url}".strip(), code,
                           diagnostics={"status_code": code, "reason": d.reason, "url": d.url,
                                        "body_excerpt": d.body_excerpt})
        if code == 429:
            return Failure("rate_limited", str(exc), 429,
                           retry_after=parse_retry_after(header(d.headers, "Retry-After"), now))
        if code is None:
            return Failure("bad_payload", f"{exc} ({d.error or 'unusable body'})",
                           diagnostics={"body_excerpt": d.body_excerpt})
        if 200 <= code < 300:  # 2xx with a body that is not JSON
            return Failure("bad_payload", f"{exc}: {d.error or ''}".strip(), code,
                           diagnostics={"body_excerpt": d.body_excerpt})
        return Failure("http", str(exc), code)
    if isinstance(exc, NetworkError):
        return Failure("network", str(exc))
    return Failure("bad_payload", redact_text(f"{type(exc).__name__}: {exc}"))


def backoff_delay(
    consecutive_failures: int, base: float, maximum: float, rng: random.Random,
    retry_after: float | None = None, floor: float = 0.0,
) -> float:
    """Exponential backoff with "equal jitter": half fixed, half random.

    The server's Retry-After always wins, even above `maximum`; `floor` is a minimum spacing
    (e.g. the poll interval, or a connect rate limit)."""
    exp = min(maximum, base * 2 ** max(0, consecutive_failures - 1))
    delay = exp * (0.5 + rng.random() / 2)
    if retry_after is not None:
        delay = max(delay, retry_after)
    return max(delay, floor)


# --- records -------------------------------------------------------------------------------

def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).isoformat().replace("+00:00", "Z")


def with_checksum(record: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in record.items() if k != "checksum"}
    return {**body, "checksum": sha256_of(body)}


def checksum_ok(record: dict[str, Any]) -> bool:
    body = {k: v for k, v in record.items() if k != "checksum"}
    return record.get("checksum") == sha256_of(body)
