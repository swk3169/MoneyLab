"""Offline Connector that replays a scripted WebSocket session file (no network).

File format (tests/fixtures/upbit_ws_timeline_synthetic.json):

    {"meta": {"synthetic": true, "description": "..."},
     "start": <unix seconds>,
     "connections": [
        {"handshake": {"status": 429, "reason": "...", "headers": {...}, "body": "..."}},
        {"connect_error": "message"},
        {"ping_reply": true,
         "frames": [{"t": <unix s>, "raw": {...}}             JSON object sent as a binary frame
                    {"t": <unix s>, "raw_text": "..."}       exact text (malformed tests)
                    {"t": <unix s>, "raw_bytes_hex": "ff"}], undecodable binary frame
         "close": {"code": 1006, "reason": "..."}}           omitted: the session just ends
     ]}

The connector owns a virtual clock: `recv` advances it to the next frame's `t` (or by the
timeout when the next frame is later), `sleep` advances it by the requested time. With
`ping_reply`, a "PING" text message is answered with {"status":"UP"} like the real server.
When every scripted connection is used up, connecting raises SourceExhausted.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from moneylab.providers.upbit.endpoints import PING_TEXT
from moneylab.providers.upbit.ws_client import WsClosed, WsConnectError, WsHandshakeError
from moneylab.recording.core import SourceExhausted


class _FixtureConnection:
    def __init__(self, source: ScriptedWsSource, spec: dict[str, Any]):
        self.source = source
        self.frames: list[dict[str, Any]] = [f for f in spec.get("frames", []) if float(f["t"]) > source.skip_until]
        self.close_spec = spec.get("close")
        self.ping_reply = bool(spec.get("ping_reply"))
        self.pending: list[bytes] = []
        self.sent: list[str] = []
        self.closed = False

    def send(self, text: str) -> None:
        if self.closed:
            raise WsClosed(1000, "closed by client")
        self.sent.append(text)
        self.source.sent.append(text)
        if text == PING_TEXT and self.ping_reply:
            self.pending.append(b'{"status":"UP"}')

    def recv(self, timeout: float) -> bytes | str:
        if self.closed:
            raise WsClosed(1000, "closed by client")
        if self.pending:
            return self.pending.pop(0)
        if not self.frames:
            if self.close_spec is not None:
                raise WsClosed(self.close_spec.get("code"), self.close_spec.get("reason", ""))
            raise SourceExhausted("scripted session has no more frames")
        nxt = self.frames[0]
        t = float(nxt["t"])
        if t > self.source.now + timeout:
            self.source.now += timeout
            raise TimeoutError
        self.frames.pop(0)
        self.source.now = max(self.source.now, t)
        if "raw_bytes_hex" in nxt:
            return bytes.fromhex(nxt["raw_bytes_hex"])
        if "raw_text" in nxt:
            return nxt["raw_text"].encode("utf-8")
        return json.dumps(copy.deepcopy(nxt["raw"]), separators=(",", ":")).encode("utf-8")

    def close(self) -> None:
        self.closed = True


class ScriptedWsSource:
    """Connector + clock for scripted sessions. Pass `source` as connector and use
    `source.clock` / `source.sleep` for the recorder."""

    def __init__(self, path: str | Path | None = None, *, data: dict[str, Any] | None = None):
        if data is None:
            if path is None:
                raise ValueError("path or data required")
            self.path = Path(path)
            data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.path = Path(path) if path else Path("<inline>")
        meta = data.get("meta") or {}
        self.synthetic = bool(meta.get("synthetic", True))
        self.description = str(meta.get("description", ""))
        self.connections: list[dict[str, Any]] = list(data["connections"])
        self.now = float(data.get("start", 0.0))
        self.skip_until = float("-inf")
        self.sent: list[str] = []
        self.urls: list[str] = []
        self.opened: list[_FixtureConnection] = []
        self._next = 0

    # --- recorder hooks ---------------------------------------------------------------
    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(0.0, seconds)

    def resume_after(self, ts: float) -> int:
        """Skip frames already recorded (received at or before `ts`) when a dataset resumes."""
        self.skip_until = ts
        self.now = max(self.now, ts)
        return sum(1 for c in self.connections for f in c.get("frames", []) if float(f["t"]) <= ts)

    def __call__(self, url: str) -> _FixtureConnection:
        self.urls.append(url)
        while self._next < len(self.connections):
            spec = self.connections[self._next]
            self._next += 1
            if "handshake" in spec:
                h = spec["handshake"]
                raise WsHandshakeError(int(h["status"]), h.get("reason", ""), h.get("headers"), h.get("body"), url)
            if "connect_error" in spec:
                raise WsConnectError(str(spec["connect_error"]))
            conn = _FixtureConnection(self, spec)
            if not conn.frames and spec.get("frames") and conn.close_spec is None:
                continue  # every frame was recorded before a restart
            self.opened.append(conn)
            return conn
        raise SourceExhausted(f"{self.path.name}: all {len(self.connections)} scripted connections used")

    def close(self) -> None:
        pass
