"""Minimal synchronous WebSocket transport for the Upbit public endpoint.

The recorder talks to a `WsConnection` (send / recv(timeout) / close) obtained from a
`Connector`. `websockets_connector` builds real connections with the `websockets` library;
tests and `--source fixture` use `providers.upbit.recorder.fixture_source` instead.

Policy, mirroring core/http.HttpClient (which only speaks HTTP and cannot carry a WebSocket):
  * explicit timeouts (open, close, recv);
  * `proxy=None`: no proxy, no environment proxy pick-up, no routing tricks of any kind;
  * failures become typed errors carrying redacted diagnostics (status, headers, body excerpt);
  * no credentials: no auth header of any kind is ever sent (public data only).

Keep-alive (websocket-guide): the server drops connections idle for 120 s. The connection
sends WebSocket PING frames (`ping_interval`) and the recorder additionally sends the documented
"PING" text message, answered by {"status":"UP"}.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from moneylab.core.redaction import redact_headers, redact_text

BODY_EXCERPT_LIMIT = 2000


class WsError(Exception):
    """Base class of transport errors."""


class WsConnectError(WsError):
    """No WebSocket was established and no HTTP status was received (DNS, TCP, TLS, timeout)."""


class WsHandshakeError(WsError):
    """The server answered the opening handshake with a non-101 HTTP status."""

    def __init__(self, status_code: int, reason: str = "", headers: dict[str, str] | None = None,
                 body: bytes | str | None = None, url: str = ""):
        self.status_code = status_code
        self.reason = reason
        self.headers = redact_headers(dict(headers or {}))
        text = body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else (body or "")
        self.body_excerpt = redact_text(text[:BODY_EXCERPT_LIMIT])
        self.url = url
        super().__init__(f"HTTP {status_code} {reason}".strip() + (f" during WebSocket handshake: {url}" if url else ""))

    def diagnostics(self) -> dict[str, Any]:
        return {"status_code": self.status_code, "reason": self.reason, "url": self.url,
                "headers": self.headers, "body_excerpt": self.body_excerpt}


class WsClosed(WsError):
    """The connection was closed (by the server, the network, or a keep-alive timeout)."""

    def __init__(self, code: int | None = None, reason: str = ""):
        self.code, self.reason = code, reason
        super().__init__(f"connection closed (code={code}, reason={reason!r})")


class WsConnection(Protocol):
    def send(self, text: str) -> None: ...

    def recv(self, timeout: float) -> bytes | str:
        """Next frame. Raises TimeoutError when nothing arrives in `timeout` s, WsClosed when closed."""
        ...

    def close(self) -> None: ...


Connector = Callable[[str], WsConnection]


@dataclass(frozen=True)
class WsOptions:
    open_timeout: float = 10.0
    ping_interval: float | None = 30.0  # WebSocket PING frame period (< 120 s idle timeout)
    ping_timeout: float | None = 20.0  # no PONG within this -> connection treated as dead
    close_timeout: float = 5.0
    max_size: int = 4 * 1024 * 1024
    compression: str | None = "deflate"  # permessage-deflate; the server offered it when probed
    user_agent: str = "MoneyLab/0.3 (+research; read-only)"
    extra: dict[str, Any] = field(default_factory=dict)


class _WebsocketsConnection:
    def __init__(self, ws: Any):
        self._ws = ws

    def send(self, text: str) -> None:
        from websockets.exceptions import ConnectionClosed

        try:
            self._ws.send(text)
        except ConnectionClosed as exc:
            raise _closed(exc) from exc

    def recv(self, timeout: float) -> bytes | str:
        from websockets.exceptions import ConnectionClosed

        try:
            return self._ws.recv(timeout=timeout)
        except ConnectionClosed as exc:
            raise _closed(exc) from exc

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:  # noqa: BLE001 - closing a broken socket must never raise
            pass


def _closed(exc: Exception) -> WsClosed:
    frame = getattr(exc, "rcvd", None) or getattr(exc, "sent", None)
    return WsClosed(getattr(frame, "code", None), redact_text(str(getattr(frame, "reason", "") or exc)))


def websockets_connector(options: WsOptions | None = None) -> Connector:
    """Connector backed by `websockets.sync.client.connect`."""
    opts = options or WsOptions()

    def connect(url: str) -> WsConnection:
        from websockets.exceptions import InvalidHandshake, InvalidStatus, InvalidURI
        from websockets.sync.client import connect as ws_connect

        try:
            ws = ws_connect(
                url, proxy=None, open_timeout=opts.open_timeout, ping_interval=opts.ping_interval,
                ping_timeout=opts.ping_timeout, close_timeout=opts.close_timeout, max_size=opts.max_size,
                compression=opts.compression, user_agent_header=opts.user_agent,
                legacy=True,  # a plain connection we close ourselves; reconnects are the recorder's job
                **opts.extra,
            )
        except InvalidStatus as exc:
            r = exc.response
            raise WsHandshakeError(r.status_code, r.reason_phrase, dict(r.headers.raw_items()), r.body, url) from exc
        except InvalidURI as exc:
            raise WsConnectError(f"invalid WebSocket URL {url}: {exc}") from exc
        except (InvalidHandshake, OSError, TimeoutError) as exc:
            raise WsConnectError(redact_text(f"{type(exc).__name__}: {exc} ({url})")) from exc
        return _WebsocketsConnection(ws)

    return connect
