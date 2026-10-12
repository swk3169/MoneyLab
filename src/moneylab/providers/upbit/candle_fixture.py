"""Scripted, SYNTHETIC stand-in for the Upbit candle endpoints (`candles-pull --source fixture`).

A fixture file describes a series per interval instead of listing every row:

    {"meta": {"synthetic": true, "market": "KRW-BTC", "now_utc": "...Z", "inclusive_to": false},
     "series": {"day":  {"first_start": "...Z", "open": "140000000", "step": "250000", "omit": ["...Z"]},
                "hour": {...}}}

Rows run from `first_start` up to the bucket that contains `now_utc`, which is served still in
progress (last tick = now), exactly as the live endpoint does. `omit` drops buckets (no trades),
`inclusive_to` makes `to` inclusive so page boundaries repeat a row. Every response carries a
`Date` header equal to `now_utc`. Prices, volumes and times are invented: nothing produced from a
fixture is market evidence. Files without `meta.synthetic = true` are refused.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import format_datetime
from pathlib import Path
from typing import Any

import requests
from requests.structures import CaseInsensitiveDict

from moneylab.providers.upbit.candles import INTERVALS, KST, is_aligned
from moneylab.providers.upbit.endpoints import REST_BASE_URL, validate_market

_TS = "%Y-%m-%dT%H:%M:%S"
_SPREAD = Decimal("100000")
_EIGHT = Decimal("0.00000001")


def _utc(text: str) -> datetime:
    t = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError(f"fixture time {text!r} needs a timezone (use Z)")
    return t.astimezone(UTC)


def _num(d: Decimal) -> str:
    return str(d.quantize(_EIGHT))  # 8 decimals, like Upbit's 113317000.00000000


@dataclass(frozen=True)
class CandleFixture:
    path: Path
    market: str
    now: datetime
    inclusive_to: bool
    rows: dict[str, list[dict[str, Any]]]  # interval -> rows, newest first, values already JSON text

    @classmethod
    def load(cls, path: Path) -> CandleFixture:
        path = Path(path)
        doc = json.loads(path.read_text(encoding="utf-8"))
        meta = doc.get("meta") or {}
        if meta.get("synthetic") is not True:
            raise ValueError(f"{path} is not marked synthetic; fixtures must never pose as real data")
        market = validate_market(meta["market"])
        now = _utc(meta["now_utc"])
        rows = {iv: cls._rows(market, iv, spec, now) for iv, spec in (doc.get("series") or {}).items()}
        return cls(path, market, now, bool(meta.get("inclusive_to", False)), rows)

    @staticmethod
    def _rows(market: str, interval: str, spec: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
        if interval not in INTERVALS:
            raise ValueError(f"unknown interval {interval!r} in fixture")
        step = INTERVALS[interval][1]
        start = _utc(spec["first_start"])
        if not is_aligned(start, interval):
            raise ValueError(f"{interval} first_start {spec['first_start']} is not on a bucket boundary")
        omit = {_utc(t) for t in spec.get("omit", ())}
        base, delta = Decimal(spec["open"]), Decimal(spec["step"])
        out = []
        i = 0
        while start + i * step <= now:
            s = start + i * step
            o = base + i * delta
            c = o + delta
            tick = min(s + step - timedelta(seconds=1), now)
            vol = Decimal("10.12345678") + i
            if s not in omit:
                row = {"market": market, "candle_date_time_utc": s.strftime(_TS),
                       "candle_date_time_kst": (s + KST).strftime(_TS),
                       "opening_price": _num(o), "high_price": _num(max(o, c) + _SPREAD),
                       "low_price": _num(min(o, c) - _SPREAD), "trade_price": _num(c),
                       "timestamp": int(tick.timestamp() * 1000),
                       "candle_acc_trade_price": _num(vol * c), "candle_acc_trade_volume": _num(vol)}
                if interval == "hour":
                    row["unit"] = 60
                out.append(row)
            i += 1
        return out[::-1]

    def session(self) -> ScriptedCandleSession:
        return ScriptedCandleSession(self)


def _body(rows: list[dict[str, Any]]) -> bytes:
    """JSON with prices as bare numbers (no quotes), the way the live endpoint writes them."""
    parts = []
    for r in rows:
        fields = []
        for k, v in r.items():
            if k in ("market", "candle_date_time_utc", "candle_date_time_kst"):
                fields.append(f"{json.dumps(k)}:{json.dumps(v)}")
            else:
                fields.append(f"{json.dumps(k)}:{v}")
        parts.append("{" + ",".join(fields) + "}")
    return ("[" + ",".join(parts) + "]").encode("utf-8")


class ScriptedCandleSession(requests.Session):
    """Answers GET /v1/candles/days and /v1/candles/minutes/60 from a CandleFixture. No network."""

    def __init__(self, fixture: CandleFixture):
        super().__init__()
        self.fixture = fixture
        self.calls: list[dict[str, Any]] = []
        self._paths = {REST_BASE_URL + path: iv for iv, (path, _) in INTERVALS.items()}

    def request(self, method, url, params=None, **kwargs):  # type: ignore[override]
        params = dict(params or {})
        self.calls.append({"method": method, "url": url, "params": params})
        interval = self._paths.get(url)
        if method != "GET" or interval is None or interval not in self.fixture.rows:
            return _response(404, b'{"error":{"name":"not_found"}}', url, self.fixture.now)
        if params.get("market") != self.fixture.market:
            return _response(400, b'{"error":{"name":"invalid_market"}}', url, self.fixture.now)
        rows = self.fixture.rows[interval]
        if "to" in params:
            to = params["to"].rstrip("Z")
            rows = [r for r in rows if r["candle_date_time_utc"] < to
                    or (self.fixture.inclusive_to and r["candle_date_time_utc"] == to)]
        return _response(200, _body(rows[: int(params.get("count", 200))]), url, self.fixture.now)


def _response(status: int, body: bytes, url: str, now: datetime) -> requests.Response:
    r = requests.Response()
    r.status_code = status
    r.reason = "OK" if status == 200 else "Error"
    r._content = body
    r.headers = CaseInsensitiveDict({"Content-Type": "application/json; charset=utf-8",
                                     "Date": format_datetime(now, usegmt=True)})
    r.url = url
    r.encoding = "utf-8"
    req = requests.PreparedRequest()
    req.prepare(method="GET", url=url)
    r.request = req
    return r
