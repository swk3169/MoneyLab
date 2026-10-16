"""v0.6 Upbit candle pull (REST /v1/candles/days, /v1/candles/minutes/60) with a FakeSession.

Payloads are SYNTHETIC, shaped like the live responses checked on 2026-10-12 (field names,
tz-less bucket-start strings, newest-first order, 8-decimal numbers). Nothing touches the network.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import format_datetime

import pytest
import requests
from conftest import FakeSession, make_response

from moneylab.core.exceptions import ProviderError
from moneylab.core.http import HttpClient
from moneylab.core.ratelimit import SlidingWindowLimiter
from moneylab.providers.upbit import candle_store
from moneylab.providers.upbit.candle_store import CandleRawStore, CandleStoreError, pull_to_store
from moneylab.providers.upbit.candles import (
    CandleParseError,
    UpbitCandleClient,
    candle_http_client,
    closed_as_of,
    decode_candles,
    parse_candle,
    pull_candles,
)
from moneylab.providers.upbit.endpoints import REST_BASE_URL
from moneylab.storage.atomic import sha256_file

NOW = datetime(2026, 10, 12, 1, 42, tzinfo=UTC)  # same moment as the live check
DAY, HOUR = timedelta(days=1), timedelta(hours=1)
STEP = {"day": DAY, "hour": HOUR}


def utc(*a) -> datetime:
    return datetime(*a, tzinfo=UTC)


# --- synthetic server -------------------------------------------------------------------------

def row(start: datetime, interval: str = "day", o="100.00000000", h="110.00000000", lo="90.00000000",
        c="105.00000000", vol="1.23456789", tick: datetime | None = None, **over) -> dict:
    end = start + STEP[interval]
    tick = tick or min(end - timedelta(seconds=1), NOW)
    r = {"market": "KRW-BTC",
         "candle_date_time_utc": start.strftime("%Y-%m-%dT%H:%M:%S"),
         "candle_date_time_kst": (start + timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%S"),
         "opening_price": Decimal(o), "high_price": Decimal(h), "low_price": Decimal(lo), "trade_price": Decimal(c),
         "timestamp": int(tick.timestamp() * 1000),
         "candle_acc_trade_price": Decimal("7191485021.06921000"), "candle_acc_trade_volume": Decimal(vol)}
    if interval == "hour":
        r["unit"] = 60
    r.update(over)
    return r


def dumps(rows) -> str:
    """JSON with Decimals written as bare numbers (like Upbit's 113317000.00000000)."""
    text = json.dumps(rows, default=lambda d: f"__D{d}D__")
    return re.sub(r'"__D(.*?)D__"', r"\1", text)


def series(first: datetime, n: int, interval: str = "day", skip=()) -> list[dict]:
    return [row(first + i * STEP[interval], interval) for i in range(n) if i not in skip]


class Server:
    """Answers like the candle endpoint: rows with start < `to` (or <= when inclusive), newest first."""

    def __init__(self, rows, inclusive_to=False, ignore_to=False, date=NOW):
        self.rows = sorted(rows, key=lambda r: r["candle_date_time_utc"], reverse=True)
        self.inclusive_to, self.ignore_to, self.date = inclusive_to, ignore_to, date

    def __call__(self, method, url, params):
        assert method == "GET" and url.startswith(REST_BASE_URL + "/v1/candles/")
        count = params["count"]
        out = self.rows
        if "to" in params and not self.ignore_to:
            to = params["to"].rstrip("Z")
            out = [r for r in out if r["candle_date_time_utc"] < to
                   or (self.inclusive_to and r["candle_date_time_utc"] == to)]
        return make_response(200, dumps(out[:count]), {"Date": format_datetime(self.date, usegmt=True)}, url=url)


def client(handler, *, max_retries=2, sleeps=None, utcnow=lambda: NOW, limiter=None):
    session = FakeSession(handler)
    sleeps = [] if sleeps is None else sleeps
    c = UpbitCandleClient(HttpClient(REST_BASE_URL, session=session), max_retries=max_retries,
                          sleep=sleeps.append, utcnow=utcnow,
                          limiter=limiter or SlidingWindowLimiter([(1000, 1.0)], clock=lambda: 0.0, sleep=sleeps.append))
    return c, session


# --- normal path ------------------------------------------------------------------------------

def test_day_pull_sorted_decimal_and_drops_in_progress_candle():
    rows = series(utc(2026, 10, 3), 10)  # 10-03 .. 10-12; 10-12 is still open at NOW
    rows[-1] = row(utc(2026, 10, 12), o="113317000.00000000", h="113640000.00000000",
                   lo="112987000.00000000", c="113048000.00000000", vol="63.47044886", tick=NOW)
    rows[0] = row(utc(2026, 10, 3), vol="343.06635870")
    c, session = client(Server(rows))
    pull = pull_candles(c, "KRW-BTC", "day", utc(2026, 10, 3), utc(2026, 10, 13))
    starts = [x.start_utc for x in pull.candles]
    assert starts == [utc(2026, 10, 3) + i * DAY for i in range(9)]  # oldest first, 10-12 excluded
    assert pull.report.excluded_incomplete == 1 and pull.report.ok and pull.report.gaps == []
    assert pull.candles[0].acc_trade_volume == Decimal("343.06635870")  # exact, not a float
    assert isinstance(pull.candles[0].open, Decimal)
    method, url, params = session.calls[0]
    assert url == "https://api.upbit.com/v1/candles/days"
    assert params == {"market": "KRW-BTC", "count": 200, "to": "2026-10-13T00:00:00Z"}
    assert "Authorization" not in session.headers


@pytest.mark.parametrize("inclusive", [False, True])
def test_hour_pagination_has_no_boundary_duplicates(inclusive):
    first = utc(2026, 9, 23)
    c, session = client(Server(series(first, 450, "hour"), inclusive_to=inclusive))
    pull = pull_candles(c, "KRW-BTC", "hour", first, first + 450 * HOUR)
    assert len(pull.candles) == 450 and len({x.start_utc for x in pull.candles}) == 450
    assert all(b.start_utc - a.start_utc == HOUR for a, b in zip(pull.candles, pull.candles[1:]))
    assert pull.report.duplicates_conflicting == [] and pull.report.gaps == []
    assert (pull.report.duplicates_identical > 0) == inclusive
    assert session.calls[0][1].endswith("/v1/candles/minutes/60")
    tos = [p["to"] for _, _, p in session.calls]
    assert tos == sorted(tos, reverse=True) and len(set(tos)) == len(tos)  # strictly backwards


def test_empty_response_is_reported_not_an_error():
    c, _ = client(Server([]))
    pull = pull_candles(c, "KRW-BTC", "day", utc(2026, 10, 1), utc(2026, 10, 5))
    assert pull.candles == [] and pull.report.reached_earliest
    assert "no closed candles" in pull.report.warnings[0]


def test_data_starting_after_requested_start_is_not_a_gap():
    c, _ = client(Server(series(utc(2026, 10, 5), 5)))
    pull = pull_candles(c, "KRW-BTC", "day", utc(2026, 9, 1), utc(2026, 10, 10))
    assert len(pull.candles) == 5 and pull.report.reached_earliest and pull.report.gaps == []
    assert any("earliest available" in w for w in pull.report.warnings)


# --- missing, duplicate, invalid --------------------------------------------------------------

def test_missing_bucket_is_reported_and_never_filled():
    c, _ = client(Server(series(utc(2026, 10, 1), 8, "hour", skip={3})))
    pull = pull_candles(c, "KRW-BTC", "hour", utc(2026, 10, 1), utc(2026, 10, 1, 8))
    assert len(pull.candles) == 7
    assert utc(2026, 10, 1, 3) not in {x.start_utc for x in pull.candles}
    assert pull.report.gaps == [{"after": "2026-10-01T02:00:00Z", "before": "2026-10-01T04:00:00Z", "missing": 1}]
    assert pull.report.missing_buckets == 1 and pull.report.ok  # gaps are reported, not fatal


def test_leading_and_trailing_missing_buckets():
    rows = series(utc(2026, 9, 28), 10, skip={0, 1, 2, 3, 8, 9})  # older rows exist before the range
    rows += series(utc(2026, 9, 20), 3)
    c, _ = client(Server(rows))
    pull = pull_candles(c, "KRW-BTC", "day", utc(2026, 9, 30), utc(2026, 10, 8))
    assert [x.start_utc.day for x in pull.candles] == [2, 3, 4, 5]
    assert pull.report.gaps[0] == {"after": None, "before": "2026-10-02T00:00:00Z", "missing": 2}
    assert pull.report.gaps[-1] == {"after": "2026-10-05T00:00:00Z", "before": None, "missing": 2}


def test_conflicting_duplicate_keeps_first_and_fails_report():
    rows = series(utc(2026, 10, 1), 3)
    dup = row(utc(2026, 10, 2), c="999.00000000", h="999.00000000")
    c, _ = client(lambda m, u, p: make_response(200, dumps(list(reversed(rows)) + [dup]),
                                                {"Date": format_datetime(NOW, usegmt=True)}))
    pull = pull_candles(c, "KRW-BTC", "day", utc(2026, 10, 1), utc(2026, 10, 4))
    assert pull.report.duplicates_conflicting == ["2026-10-02T00:00:00Z"] and not pull.report.ok
    assert pull.candles[1].close == Decimal("105")  # first received wins, nothing averaged


def test_implausible_values_are_reported_and_kept():
    rows = series(utc(2026, 10, 1), 3)
    rows[1] = row(utc(2026, 10, 2), lo="120.00000000")  # low above open/close
    rows[2] = row(utc(2026, 10, 3), vol="-1.00000000")
    c, _ = client(Server(rows))
    pull = pull_candles(c, "KRW-BTC", "day", utc(2026, 10, 1), utc(2026, 10, 4))
    assert len(pull.candles) == 3 and not pull.report.ok
    assert [i["problems"] for i in pull.report.invalid] == [["OHLC inconsistent"],
                                                            ["negative accumulated trade value/volume"]]


def test_last_tick_outside_bucket_is_a_warning():
    rows = [row(utc(2026, 10, 1), tick=utc(2026, 10, 2, 0, 0, 0) + timedelta(milliseconds=7)),  # observed live
            row(utc(2026, 10, 2), tick=utc(2026, 10, 3, 0, 5))]
    c, _ = client(Server(rows))
    pull = pull_candles(c, "KRW-BTC", "day", utc(2026, 10, 1), utc(2026, 10, 3))
    assert len(pull.report.warnings) == 1 and pull.report.warnings[0].startswith("2026-10-02T00:00:00Z")


# --- in-progress candles and look-ahead -------------------------------------------------------

def test_recently_closed_candle_waits_for_settle_time():
    rows = series(utc(2026, 10, 12), 2, "hour")  # 00:00 closed at 01:00, 01:00 still open
    c, _ = client(Server(rows), utcnow=lambda: utc(2026, 10, 12, 1, 1))
    pull = pull_candles(c, "KRW-BTC", "hour", utc(2026, 10, 12), utc(2026, 10, 12, 2))
    assert pull.candles == [] and pull.report.excluded_incomplete == 2  # 00:00 ended only 60 s ago
    c, _ = client(Server(rows), utcnow=lambda: utc(2026, 10, 12, 1, 1))
    pull = pull_candles(c, "KRW-BTC", "hour", utc(2026, 10, 12), utc(2026, 10, 12, 2), settle_seconds=30)
    assert [x.start_utc.hour for x in pull.candles] == [0]


def test_fast_local_clock_cannot_close_an_open_bucket():
    rows = series(utc(2026, 10, 12), 1, "hour")
    # local clock says 01:10, server Date says 00:59: the bucket is still open
    c, _ = client(Server(rows, date=utc(2026, 10, 12, 0, 59)), utcnow=lambda: utc(2026, 10, 12, 1, 10))
    pull = pull_candles(c, "KRW-BTC", "hour", utc(2026, 10, 12), utc(2026, 10, 12, 1))
    assert pull.candles == [] and pull.report.excluded_incomplete == 1


def test_pull_never_returns_candles_at_or_after_end_even_if_server_sends_them():
    c, _ = client(Server(series(utc(2026, 10, 1), 10), ignore_to=True))
    pull = pull_candles(c, "KRW-BTC", "day", utc(2026, 10, 1), utc(2026, 10, 5))
    assert max(x.start_utc for x in pull.candles) == utc(2026, 10, 4)
    assert all(x.end_utc <= utc(2026, 10, 5) for x in pull.candles)
    assert pull.report.excluded_out_of_range == 6


def test_closed_as_of_uses_only_finished_buckets_and_ignores_the_future():
    c, _ = client(Server(series(utc(2026, 10, 1), 6)))
    candles = pull_candles(c, "KRW-BTC", "day", utc(2026, 10, 1), utc(2026, 10, 7)).candles
    t = utc(2026, 10, 4, 12)  # mid-bucket: 10-04 is not finished yet
    visible = closed_as_of(candles, t)
    assert [x.start_utc.day for x in visible] == [1, 2, 3]
    changed = candles[:3] + [parse_candle(row(x.start_utc, c="1.00000000", lo="1.00000000"), "KRW-BTC", "day")
                             for x in candles[3:]]
    assert closed_as_of(changed, t) == visible  # future rows can change without affecting time t
    assert closed_as_of(candles, utc(2026, 10, 4)) == visible  # boundary: 10-04 ends at 10-05
    with pytest.raises(ValueError):
        closed_as_of(candles, datetime(2026, 10, 4))


# --- HTTP errors, retries, rate limit ---------------------------------------------------------

def sequence(*outs):
    it = iter(outs)

    def handler(m, u, p):
        out = next(it)
        return out() if callable(out) else out
    return handler


OK_DAY = lambda: make_response(200, dumps([row(utc(2026, 10, 1))]), {"Date": format_datetime(NOW, usegmt=True)})  # noqa: E731


def test_429_is_retried_after_at_least_one_second():
    sleeps = []
    c, session = client(sequence(make_response(429, '{"error":"too many"}', {"Retry-After": "2"}), OK_DAY), sleeps=sleeps)
    page = c.fetch_page("KRW-BTC", "day", utc(2026, 10, 2), 1)
    assert page.attempts == 2 and len(session.calls) == 2 and sleeps == [2.0]


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_5xx_retried_with_backoff_then_succeeds(status):
    sleeps = []
    c, session = client(sequence(make_response(status, "x"), make_response(status, "x"), OK_DAY), sleeps=sleeps)
    page = c.fetch_page("KRW-BTC", "day", None, 1)
    assert page.attempts == 3 and sleeps == [0.5, 1.0]


def test_5xx_exhausted_raises_with_diagnostics():
    c, session = client(lambda m, u, p: make_response(503, "unavailable", reason="Service Unavailable"))
    with pytest.raises(ProviderError) as ei:
        c.fetch_page("KRW-BTC", "day")
    assert len(session.calls) == 3 and ei.value.diagnostics.status_code == 503
    assert "after 3 attempts" in str(ei.value)


def test_timeout_is_retried_then_raises():
    c, session = client(lambda m, u, p: requests.Timeout("slow"))
    with pytest.raises(ProviderError, match="Timeout"):
        c.fetch_page("KRW-BTC", "hour")
    assert len(session.calls) == 3
    c, session = client(sequence(requests.ConnectionError("reset"), OK_DAY))
    assert c.fetch_page("KRW-BTC", "day").attempts == 2


@pytest.mark.parametrize("status", [400, 401, 403, 404, 418, 451])
def test_policy_and_client_errors_are_never_retried(status):
    c, session = client(lambda m, u, p: make_response(status, "no"))
    with pytest.raises(ProviderError, match="not retried") as ei:
        c.fetch_page("KRW-BTC", "day")
    assert len(session.calls) == 1 and ei.value.diagnostics.status_code == status


def test_every_attempt_goes_through_the_rate_limiter():
    now = [0.0]
    sleeps = []

    def sleep(s):
        sleeps.append(s)
        now[0] += s
    limiter = SlidingWindowLimiter([(4, 1.0)], clock=lambda: now[0], sleep=sleep)
    c, session = client(sequence(*[make_response(503, "x")] * 2, *[OK_DAY] * 3), limiter=limiter,
                        sleeps=[])
    for _ in range(3):
        c.fetch_page("KRW-BTC", "day")
    assert len(session.calls) == 5 and limiter.waited > 0  # 5th request had to wait for the window


def test_bad_bodies_and_rows_raise_parse_errors():
    with pytest.raises(CandleParseError):
        decode_candles(b"{not json")
    with pytest.raises(CandleParseError):
        decode_candles(b'{"error": {"name": "x"}}')
    good = row(utc(2026, 10, 1))
    bad_rows = [
        {k: v for k, v in good.items() if k != "trade_price"},
        good | {"opening_price": "100"},                          # string, not a number
        good | {"timestamp": 1.5},
        good | {"market": "KRW-ETH"},
        good | {"candle_date_time_kst": good["candle_date_time_utc"]},
        good | {"candle_date_time_utc": "2026-10-01T09:00:00", "candle_date_time_kst": "2026-10-01T18:00:00"},
        good | {"candle_date_time_utc": "2026-10-01T00:00:00Z"},
    ]
    for r in bad_rows:
        with pytest.raises(CandleParseError):
            parse_candle(r, "KRW-BTC", "day")
    with pytest.raises(CandleParseError, match="unit"):
        parse_candle(row(utc(2026, 10, 1, 3), "hour", unit=240), "KRW-BTC", "hour")


def test_input_validation():
    c, _ = client(Server([]))
    for args in [(datetime(2026, 10, 1), utc(2026, 10, 2)), (utc(2026, 10, 1, 3), utc(2026, 10, 2)),
                 (utc(2026, 10, 2), utc(2026, 10, 2))]:
        with pytest.raises(ValueError):
            pull_candles(c, "KRW-BTC", "day", *args)
    with pytest.raises(ValueError):
        pull_candles(c, "KRW-BTC", "week", utc(2026, 10, 1), utc(2026, 10, 2))
    with pytest.raises(ValueError):
        c.fetch_page("krw-btc", "day")
    with pytest.raises(ValueError):
        c.fetch_page("KRW-BTC", "day", count=201)


def test_pagination_that_does_not_move_backwards_stops():
    rows = series(utc(2026, 10, 1), 3)
    c, session = client(lambda m, u, p: make_response(200, dumps(list(reversed(rows))),
                                                      {"Date": format_datetime(NOW, usegmt=True)}))
    with pytest.raises(ProviderError, match="did not move"):
        pull_candles(c, "KRW-BTC", "day", utc(2026, 9, 1), utc(2026, 10, 4))
    assert len(session.calls) == 2


# --- raw evidence store -----------------------------------------------------------------------

def test_pull_to_store_preserves_exact_bytes_hashes_and_report(tmp_path):
    first = utc(2026, 9, 23)
    server = Server(series(first, 450, "hour"))
    bodies = []

    def handler(m, u, p):
        resp = server(m, u, p)
        bodies.append(resp.content)
        return resp
    c, _ = client(handler)
    pull, store = pull_to_store(c, tmp_path, "KRW-BTC", "hour", first, first + 450 * HOUR, provenance="fixture")
    doc = json.loads((store.dir / "pull.json").read_text(encoding="utf-8"))
    assert doc["status"] == "complete" and doc["provenance"] == "fixture" and doc["synthetic"] is True
    assert doc["source"]["endpoint"] == "/v1/candles/minutes/60" and doc["source"]["public_market_data_only"]
    assert doc["report"]["candles"] == 450 and doc["report"]["ok"] is True
    assert len(doc["pages"]) == len(bodies) == 3
    for entry, body in zip(doc["pages"], bodies):
        path = store.dir / entry["file"]
        assert path.read_bytes() == body and sha256_file(path) == entry["sha256"]
        meta = json.loads(path.with_name(path.stem + ".meta.json").read_text(encoding="utf-8"))
        assert meta["sha256"] == entry["sha256"] and meta["params"]["to"].endswith("Z")
        assert meta["status_code"] == 200 and meta["server_date"].startswith("2026-10-12T01:42")
    assert not list(tmp_path.rglob("*.tmp"))


def test_storage_failure_stops_the_pull(tmp_path, monkeypatch):
    def broken(path, data):
        raise OSError("disk full")
    monkeypatch.setattr(candle_store, "atomic_write_bytes", broken)
    c, session = client(Server(series(utc(2026, 9, 1), 300)))
    with pytest.raises(CandleStoreError, match="disk full"):
        pull_to_store(c, tmp_path, "KRW-BTC", "day", utc(2026, 9, 1), utc(2026, 10, 1), provenance="fixture")
    assert len(session.calls) == 1  # no further requests without preserved evidence
    (pull_dir,) = tmp_path.iterdir()
    doc = json.loads((pull_dir / "pull.json").read_text(encoding="utf-8"))
    assert doc["status"] == "failed" and "disk full" in doc["error"] and doc["pages"] == []


def test_malformed_page_is_saved_before_the_parse_error(tmp_path):
    c, _ = client(lambda m, u, p: make_response(200, '[{"market": "KRW-BTC"}]'))
    with pytest.raises(CandleParseError):
        pull_to_store(c, tmp_path, "KRW-BTC", "day", utc(2026, 9, 1), utc(2026, 10, 1), provenance="fixture")
    (pull_dir,) = tmp_path.iterdir()
    assert (pull_dir / "pages" / "0000.json").read_bytes() == b'[{"market": "KRW-BTC"}]'
    assert json.loads((pull_dir / "pull.json").read_text(encoding="utf-8"))["status"] == "failed"


def test_store_never_overwrites(tmp_path):
    fixed = lambda: NOW  # noqa: E731
    args = (tmp_path, "KRW-BTC", "day", utc(2026, 9, 1), utc(2026, 10, 1))
    store = CandleRawStore.create(*args, provenance="fixture", utcnow=fixed)
    with pytest.raises(CandleStoreError, match="already exists"):
        CandleRawStore.create(*args, provenance="fixture", utcnow=fixed)
    c, _ = client(Server(series(utc(2026, 9, 1), 3)))
    page = c.fetch_page("KRW-BTC", "day")
    store.save_page(0, page)
    before = (store.dir / "pages" / "0000.json").read_bytes()
    with pytest.raises(CandleStoreError, match="already exists"):
        store.save_page(0, page)
    assert (store.dir / "pages" / "0000.json").read_bytes() == before
    with pytest.raises(ValueError):
        CandleRawStore.create(tmp_path / "x", "KRW-BTC", "day", utc(2026, 9, 1), utc(2026, 10, 1), provenance="live")


# --- review additions: retry bounds, termination, storage failure paths -----------------------

def test_max_retries_zero_means_a_single_attempt():
    c, session = client(lambda m, u, p: make_response(503, "x"), max_retries=0)
    with pytest.raises(ProviderError, match="after 1 attempts"):
        c.fetch_page("KRW-BTC", "day")
    assert len(session.calls) == 1
    with pytest.raises(ValueError):
        client(Server([]), max_retries=-1)


def test_long_retry_after_ends_the_pull_instead_of_sleeping():
    sleeps = []
    c, session = client(lambda m, u, p: make_response(429, "slow down", {"Retry-After": "600"}), sleeps=sleeps)
    with pytest.raises(ProviderError, match="wait 600 s, not retried"):
        c.fetch_page("KRW-BTC", "day")
    assert len(session.calls) == 1 and sleeps == []


def test_candle_http_client_leaves_retries_to_the_candle_client():
    http = candle_http_client(timeout=3.0)
    try:
        assert http.base_url == REST_BASE_URL and http.timeout == 3.0
        assert http.session.get_adapter(REST_BASE_URL).max_retries.total == 0  # no 3 x 3 retry storm
        assert http.session.trust_env is False  # no proxy pick-up
    finally:
        http.close()


def test_page_limit_stops_pagination():
    first = utc(2026, 9, 23)
    c, session = client(Server(series(first, 450, "hour")))
    with pytest.raises(ProviderError, match="page limit 2"):
        pull_candles(c, "KRW-BTC", "hour", first, first + 450 * HOUR, max_pages=2)
    assert len(session.calls) == 2


def test_metadata_write_failure_stops_and_keeps_the_original_error(tmp_path, monkeypatch):
    real = candle_store.atomic_write_json
    calls = []

    def flaky(path, payload, *a, **kw):
        calls.append(path)
        if len(calls) > 1:  # pull.json at create succeeds, everything after fails
            raise OSError("read-only")
        return real(path, payload, *a, **kw)
    monkeypatch.setattr(candle_store, "atomic_write_json", flaky)
    c, session = client(Server(series(utc(2026, 9, 1), 30)))
    with pytest.raises(CandleStoreError, match="raw page 0"):
        pull_to_store(c, tmp_path, "KRW-BTC", "day", utc(2026, 9, 1), utc(2026, 10, 1), provenance="fixture")
    assert len(session.calls) == 1
    (pull_dir,) = tmp_path.iterdir()
    # pull.json could not be updated either: it still says "running", which marks the pull as unfinished
    assert json.loads((pull_dir / "pull.json").read_text(encoding="utf-8"))["status"] == "running"


def test_page_meta_has_no_row_count_from_before_parsing(tmp_path):
    c, _ = client(Server(series(utc(2026, 9, 1), 3)))
    _, store = pull_to_store(c, tmp_path, "KRW-BTC", "day", utc(2026, 9, 1), utc(2026, 9, 4), provenance="fixture")
    meta = json.loads((store.dir / "pages" / "0000.meta.json").read_text(encoding="utf-8"))
    assert "rows" not in meta and meta["bytes"] == len((store.dir / "pages" / "0000.json").read_bytes())
