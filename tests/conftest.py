from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests
from requests.structures import CaseInsensitiveDict

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def make_response(status: int, body: str | bytes, headers: dict | None = None, url: str = "https://x/y", reason: str = "") -> requests.Response:
    r = requests.Response()
    r.status_code = status
    r.reason = reason
    r._content = body.encode() if isinstance(body, str) else body
    r.headers = CaseInsensitiveDict(headers or {})
    r.url = url
    r.encoding = "utf-8"
    req = requests.PreparedRequest()
    req.prepare(method="GET", url=url)
    r.request = req
    return r


class FakeSession(requests.Session):
    """Session whose request() is answered by a handler(method, url, params) -> Response | Exception."""

    def __init__(self, handler: Callable):
        super().__init__()
        self.handler = handler
        self.calls: list[tuple[str, str, dict | None]] = []

    def request(self, method, url, params=None, **kwargs):  # type: ignore[override]
        self.calls.append((method, url, params))
        out = self.handler(method, url, params)
        if isinstance(out, Exception):
            raise out
        return out


@pytest.fixture
def gamma_sample() -> list[dict]:
    return json.loads((FIXTURES / "gamma_markets_sample.json").read_text(encoding="utf-8"))


def load_captured_response(name: str) -> requests.Response:
    cap = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return make_response(cap["status_code"], cap["body"], cap["headers"],
                         url="https://gamma-api.polymarket.com/markets?limit=1", reason=cap["reason"])


@pytest.fixture
def response_451() -> requests.Response:
    """Plain-text variant (curl, no Accept header)."""
    return load_captured_response("http_451_cloudflare.json")


@pytest.fixture
def response_451_json() -> requests.Response:
    """Structured JSON variant (Accept: application/json)."""
    return load_captured_response("http_451_cloudflare_json.json")
