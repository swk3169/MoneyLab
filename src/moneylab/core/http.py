"""Shared HTTP layer: timeouts, bounded retries, and structured failure diagnostics.

Every failure is converted into NetworkError or ApiError carrying an HttpDiagnostics
record (status, headers, body excerpt), already redacted, so higher layers can show
*why* a request failed without re-requesting.

Deliberately NOT supported: proxies, VPN routing or any geo-restriction bypass.
`trust_env=False` also stops requests from silently picking up HTTP(S)_PROXY.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from moneylab.core.exceptions import ApiError, NetworkError
from moneylab.core.redaction import redact_headers, redact_text

log = logging.getLogger(__name__)

BODY_EXCERPT_LIMIT = 2000
# 451/403 are policy decisions; retrying them only adds load.
RETRY_STATUSES = (429, 500, 502, 503, 504)


@dataclass
class HttpDiagnostics:
    method: str
    url: str
    status_code: int | None = None
    reason: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    body_excerpt: str = ""
    elapsed_ms: float | None = None
    error: str | None = None

    @classmethod
    def from_response(cls, resp: requests.Response, elapsed_ms: float) -> HttpDiagnostics:
        try:
            body = resp.text
        except Exception as exc:  # undecodable body
            body = f"<unreadable body: {exc}>"
        return cls(
            method=resp.request.method or "GET",
            url=resp.url,
            status_code=resp.status_code,
            reason=resp.reason,
            headers=redact_headers(dict(resp.headers)),
            body_excerpt=redact_text(body[:BODY_EXCERPT_LIMIT]),
            elapsed_ms=round(elapsed_ms, 1),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HttpClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        retries: int = 2,
        user_agent: str = "MoneyLab/0.3",
        session: requests.Session | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.trust_env = False
        self.session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})
        if session is None:
            retry = Retry(
                total=retries,
                backoff_factor=0.5,
                status_forcelist=RETRY_STATUSES,
                allowed_methods=frozenset({"GET"}),
                respect_retry_after_header=True,
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

    def request(
        self, method: str, path: str, params: dict[str, Any] | None = None, json_body: Any = None
    ) -> requests.Response:
        """Send a request and return the raw response (any status). Raises NetworkError only."""
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        extra = {} if json_body is None else {"json": json_body}
        start = time.perf_counter()
        try:
            resp = self.session.request(method, url, params=params, timeout=self.timeout, **extra)
        except requests.Timeout as exc:
            raise NetworkError(f"Timeout after {self.timeout}s: {method} {url}") from exc
        except requests.ConnectionError as exc:
            raise NetworkError(f"Connection failed: {method} {url}: {redact_text(str(exc))}") from exc
        except requests.RequestException as exc:
            raise NetworkError(f"Request error: {method} {url}: {redact_text(str(exc))}") from exc
        resp.elapsed_ms = (time.perf_counter() - start) * 1000  # type: ignore[attr-defined]
        log.debug("%s %s -> %s (%.0f ms)", method, resp.url, resp.status_code, resp.elapsed_ms)
        return resp

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._json(self.request("GET", path, params=params), "GET")

    def post_json(self, path: str, body: Any) -> Any:
        """POST a JSON body to a *read-only* query endpoint (e.g. CLOB POST /books).

        Not retried (POST is outside the retry policy). Never use for order placement.
        """
        return self._json(self.request("POST", path, json_body=body), "POST")

    @staticmethod
    def _json(resp: requests.Response, method: str) -> Any:
        elapsed = getattr(resp, "elapsed_ms", 0.0)
        if not resp.ok:
            diag = HttpDiagnostics.from_response(resp, elapsed)
            raise ApiError(f"HTTP {resp.status_code} {resp.reason}: {method} {resp.url}", diag)
        try:
            return resp.json()
        except ValueError as exc:
            diag = HttpDiagnostics.from_response(resp, elapsed)
            diag.error = "Response body is not valid JSON"
            raise ApiError(f"Invalid JSON from {method} {resp.url}", diag) from exc

    def close(self) -> None:
        self.session.close()
