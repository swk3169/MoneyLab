"""WebSocket transport mapping, failure classification, rate limiter and the shared recorder core."""

import random

import pytest

from moneylab.core.ratelimit import SlidingWindowLimiter
from moneylab.providers.upbit import ws_client
from moneylab.providers.upbit.recorder import UpbitRecorderConfig, classify_ws_error
from moneylab.providers.upbit.ws_client import WsClosed, WsConnectError, WsHandshakeError
from moneylab.recording import core
from moneylab.recording.core import RecorderStatus, backoff_delay

CFG = UpbitRecorderConfig()


class FakeClock:
    def __init__(self, t: float = 1000.0):
        self.t = t
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.t += s


def test_handshake_error_redacts_headers_and_body():
    e = WsHandshakeError(403, "Forbidden", {"Set-Cookie": "session=abc", "Server": "x"},
                         b'{"error":"denied","api_key":"abcdef","client":"203.0.113.7"}', "wss://h/p")
    assert e.headers["Set-Cookie"] != "session=abc" and e.headers["Server"] == "x"
    assert "abcdef" not in e.body_excerpt and "203.0.113.7" not in e.body_excerpt
    assert e.diagnostics()["status_code"] == 403 and "403" in str(e)


def test_classify_policy_statuses():
    f451 = classify_ws_error(WsHandshakeError(451, "Unavailable For Legal Reasons", {}, "blocked"), 0, CFG)
    assert f451.fatal_status == RecorderStatus.BLOCKED_HTTP_451 and "does not infer" in f451.diagnostics["note"]
    for code in (401, 403):
        assert classify_ws_error(WsHandshakeError(code), 0, CFG).fatal_status == RecorderStatus.ACCESS_DENIED
    f429 = classify_ws_error(WsHandshakeError(429), 0, CFG)
    assert f429.category == "rate_limited" and f429.retry_after == 1.0  # docs: retry from the next second
    f429h = classify_ws_error(WsHandshakeError(429, headers={"Retry-After": "7"}), 0, CFG)
    assert f429h.retry_after == 7.0
    f418 = classify_ws_error(WsHandshakeError(418, headers={"Retry-After": "120"}), 0, CFG)
    assert f418.category == "banned" and f418.retry_after == 120.0 and f418.fatal_status is None
    assert f418.diagnostics["ban_duration_source"] == "Retry-After header"
    f418d = classify_ws_error(WsHandshakeError(418), 0, CFG)
    assert f418d.retry_after is None and f418d.diagnostics["ban_duration_source"].startswith("default")
    assert classify_ws_error(WsHandshakeError(502), 0, CFG).category == "http"
    assert classify_ws_error(WsConnectError("dns"), 0, CFG).category == "network"
    closed = classify_ws_error(WsClosed(1006, "abnormal"), 0, CFG)
    assert closed.category == "disconnected" and closed.diagnostics["close_code"] == 1006


def test_websockets_connector_maps_errors_and_disables_proxy(monkeypatch):
    from websockets.datastructures import Headers
    from websockets.exceptions import InvalidStatus
    from websockets.http11 import Response

    seen = {}

    def fake_connect(url, **kwargs):
        seen.update(kwargs, url=url)
        if url.endswith("/451"):
            raise InvalidStatus(Response(451, "Unavailable For Legal Reasons", Headers({"Server": "s"}), b"no"))
        raise OSError("connection refused")

    import websockets.sync.client as sync_client
    monkeypatch.setattr(sync_client, "connect", fake_connect)
    connect = ws_client.websockets_connector(ws_client.WsOptions(ping_interval=25))
    with pytest.raises(WsHandshakeError) as info:
        connect("wss://example.invalid/451")
    assert info.value.status_code == 451 and info.value.body_excerpt == "no"
    assert seen["proxy"] is None and seen["ping_interval"] == 25 and seen["legacy"] is True
    assert "additional_headers" not in seen
    with pytest.raises(WsConnectError):
        connect("wss://example.invalid/down")


def test_websockets_connection_maps_close(monkeypatch):
    from websockets.exceptions import ConnectionClosedError
    from websockets.frames import Close

    class Dead:
        def recv(self, timeout):
            raise ConnectionClosedError(Close(1011, "server error"), None)

        def send(self, text):
            raise ConnectionClosedError(None, None)

        def close(self):
            raise RuntimeError("already broken")

    conn = ws_client._WebsocketsConnection(Dead())
    with pytest.raises(WsClosed) as info:
        conn.recv(1.0)
    assert info.value.code == 1011
    with pytest.raises(WsClosed):
        conn.send("PING")
    conn.close()  # never raises


def test_sliding_window_limiter_enforces_both_windows():
    clock = FakeClock(0.0)
    lim = SlidingWindowLimiter([(5, 1.0), (100, 60.0)], clock=clock, sleep=clock.sleep)
    for _ in range(5):
        assert lim.acquire() == 0
    assert lim.acquire() == pytest.approx(1.0)  # 6th within the same second waits
    clock.t = 0.0
    lim2 = SlidingWindowLimiter([(5, 1.0), (100, 60.0)], clock=clock, sleep=clock.sleep)
    for _ in range(100):
        lim2.acquire()
    assert clock.t < 60.0
    waited = lim2.acquire()  # the 101st must wait until the first leaves the minute window
    assert waited > 0 and clock.t >= 60.0
    with pytest.raises(ValueError):
        SlidingWindowLimiter([(0, 1.0)])


def test_limiter_does_not_spin_with_a_frozen_clock():
    slept = []
    lim = SlidingWindowLimiter([(1, 1.0)], clock=lambda: 0.0, sleep=slept.append)
    lim.acquire()
    lim.acquire()
    assert slept == [1.0]


def test_backoff_delay_grows_caps_and_honours_retry_after():
    rng = random.Random(0)
    delays = [backoff_delay(n, 1.0, 60.0, rng) for n in range(1, 10)]
    assert all(0.5 * min(60, 2 ** (n - 1)) <= d <= min(60, 2 ** (n - 1)) for n, d in zip(range(1, 10), delays))
    assert backoff_delay(1, 1.0, 60.0, rng, retry_after=500.0) == 500.0  # server wins, even above the cap
    assert backoff_delay(1, 0.1, 60.0, rng, floor=2.0) == 2.0


def test_polymarket_recorder_reexports_shared_core():
    from moneylab.providers.polymarket.recorder import base, store

    assert base.RecorderStatus is core.RecorderStatus and base.classify is core.classify
    assert base.Failure is core.Failure and store.with_checksum is core.with_checksum
    assert RecorderStatus.BANNED_HTTP_418 in core.FATAL_STATUSES
