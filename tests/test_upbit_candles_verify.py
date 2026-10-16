"""v0.6 candle pulls: page_count, verify_candle_pull (hashes, file set, replay) and the
candles-pull / candles-verify CLI. Everything is SYNTHETIC and offline: FakeSession servers from
test_upbit_candles, or the scripted fixture tests/fixtures/upbit_candles_synthetic.json.
"""

import gzip
import hashlib
import io
import json
from email.utils import format_datetime
from pathlib import Path

import pytest
import requests
import urllib3
from conftest import FakeSession, make_response
from test_upbit_candles import DAY, HOUR, NOW, Server, client, dumps, series, utc

from moneylab import cli
from moneylab.cli import main
from moneylab.core.http import HttpClient
from moneylab.core.ratelimit import SlidingWindowLimiter
from moneylab.providers.upbit.candle_fixture import CandleFixture
from moneylab.providers.upbit.candle_store import pull_to_store, verify_candle_pull
from moneylab.providers.upbit.candles import UpbitCandleClient, pull_candles
from moneylab.providers.upbit.endpoints import REST_BASE_URL

FIXTURE = Path(__file__).parent / "fixtures" / "upbit_candles_synthetic.json"


def stored_pull(tmp_path, n=25, page_count=10, inclusive=False, interval="hour"):
    first = utc(2026, 10, 10) if interval == "hour" else utc(2026, 9, 1)
    step = HOUR if interval == "hour" else DAY
    c, session = client(Server(series(first, n, interval), inclusive_to=inclusive))
    pull, store = pull_to_store(c, tmp_path, "KRW-BTC", interval, first, first + n * step, provenance="fixture",
                                page_count=page_count)
    return pull, store, session


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, doc) -> None:
    path.write_text(json.dumps(doc), encoding="utf-8")


def snapshot(d: Path) -> dict:
    return {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in sorted(d.rglob("*")) if p.is_file()}


# --- page_count -------------------------------------------------------------------------------

@pytest.mark.parametrize("inclusive", [False, True])
def test_page_count_limits_every_request_and_paginates_without_duplicates(inclusive):
    first = utc(2026, 10, 10)
    c, session = client(Server(series(first, 25, "hour"), inclusive_to=inclusive))
    pull = pull_candles(c, "KRW-BTC", "hour", first, first + 25 * HOUR, page_count=10)
    assert [p["count"] for _, _, p in session.calls] == [10] * len(session.calls)
    assert len(session.calls) == 3
    assert [x.start_utc for x in pull.candles] == [first + i * HOUR for i in range(25)]
    assert pull.report.duplicates_conflicting == [] and pull.report.gaps == []
    assert pull.report.duplicates_identical == (2 if inclusive else 0)  # inclusive `to` repeats one row per boundary


@pytest.mark.parametrize("kwargs", [{"page_count": 0}, {"page_count": 201}, {"max_pages": 0}])
def test_bad_page_settings_are_refused_before_any_request(kwargs):
    c, session = client(Server(series(utc(2026, 9, 1), 5)))
    with pytest.raises(ValueError):
        pull_candles(c, "KRW-BTC", "day", utc(2026, 9, 1), utc(2026, 9, 6), **kwargs)
    assert session.calls == []


def test_pull_json_records_settings_and_origin(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    doc = load(store.dir / "pull.json")
    assert doc["settings"] == {"settle_seconds": 120.0, "page_count": 10, "max_pages": 10_000}
    assert doc["status"] == "complete" and doc["synthetic"] is True and doc["origin"] is None


# --- verify: happy path -----------------------------------------------------------------------

@pytest.mark.parametrize("inclusive", [False, True])
def test_verify_passes_and_replay_reproduces_the_stored_report(tmp_path, inclusive):
    pull, store, session = stored_pull(tmp_path, inclusive=inclusive)
    before = snapshot(store.dir)
    rep = verify_candle_pull(store.dir)
    assert rep.ok, rep.problems
    assert rep.pages_checked == len(session.calls) and rep.candles == 25 == pull.report.candles
    assert rep.replay == load(store.dir / "pull.json")["report"]
    assert snapshot(store.dir) == before  # verify writes nothing


def test_verify_replays_the_in_progress_exclusion_from_stored_times(tmp_path):
    rows = series(utc(2026, 10, 3), 10)  # 10-12 is still open at NOW (the stored receive time)
    c, _ = client(Server(rows))
    pull, store = pull_to_store(c, tmp_path, "KRW-BTC", "day", utc(2026, 10, 3), utc(2026, 10, 13),
                                provenance="fixture", page_count=10)
    assert pull.report.excluded_incomplete == 1
    rep = verify_candle_pull(store.dir)
    assert rep.ok and rep.replay["excluded_incomplete"] == 1 and rep.candles == 9


def test_stored_bytes_are_the_gzip_decoded_body_and_the_hash_covers_them(tmp_path):
    """Upbit answers with Content-Encoding: gzip. Built through the real requests/urllib3 response
    path (no network): the page file holds the decoded body, and its SHA-256 is of those bytes."""
    body = dumps(series(utc(2026, 9, 1), 3)).encode()
    wire = gzip.compress(body)
    assert wire != body

    class GzipSession(requests.Session):
        def request(self, method, url, params=None, **kwargs):  # type: ignore[override]
            req = requests.Request(method, url, params=params).prepare()
            raw = urllib3.HTTPResponse(
                body=io.BytesIO(wire), status=200, preload_content=False, decode_content=True,
                headers={"Content-Encoding": "gzip", "Content-Type": "application/json;charset=UTF-8",
                         "Date": format_datetime(NOW, usegmt=True)})
            return requests.adapters.HTTPAdapter().build_response(req, raw)

    c = UpbitCandleClient(HttpClient(REST_BASE_URL, session=GzipSession()), utcnow=lambda: NOW,
                          limiter=SlidingWindowLimiter([(1000, 1.0)], clock=lambda: 0.0, sleep=lambda s: None))
    pull, store = pull_to_store(c, tmp_path, "KRW-BTC", "day", utc(2026, 9, 1), utc(2026, 9, 4), provenance="fixture")
    assert pull.report.candles == 3
    page = store.dir / "pages" / "0000.json"
    assert page.read_bytes() == body
    meta = load(store.dir / "pages" / "0000.meta.json")
    assert meta["sha256"] == hashlib.sha256(body).hexdigest() != hashlib.sha256(wire).hexdigest()
    assert meta["bytes"] == len(body) and meta["headers"]["Content-Encoding"] == "gzip"
    assert verify_candle_pull(store.dir).ok


# --- verify: damage is detected ---------------------------------------------------------------

def test_tampered_page_byte_fails_sha_check_and_skips_replay(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    page = store.dir / "pages" / "0001.json"
    data = bytearray(page.read_bytes())
    data[10] ^= 0x01
    page.write_bytes(bytes(data))
    rep = verify_candle_pull(store.dir)
    assert not rep.ok and rep.replay is None
    assert any("page 1: SHA-256 mismatch" in p for p in rep.problems)


def test_recorded_hash_edited_in_pull_json_is_detected(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    doc = load(store.dir / "pull.json")
    doc["pages"][0]["sha256"] = "0" * 64
    save(store.dir / "pull.json", doc)
    assert any("page 0: SHA-256 mismatch" in p for p in verify_candle_pull(store.dir).problems)


def test_missing_page_file_is_reported(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    (store.dir / "pages" / "0002.json").unlink()
    rep = verify_candle_pull(store.dir)
    assert any("page 2: cannot read" in p for p in rep.problems)
    assert any("missing files in pages/" in p and "0002.json" in p for p in rep.problems)


def test_missing_meta_file_is_reported(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    (store.dir / "pages" / "0000.meta.json").unlink()
    assert any("page 0: cannot read" in p for p in verify_candle_pull(store.dir).problems)


def test_unlisted_file_in_pages_is_reported(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    (store.dir / "pages" / "0099.json").write_bytes(b"[]")
    rep = verify_candle_pull(store.dir)
    assert any("unlisted files in pages/" in p and "0099.json" in p for p in rep.problems)


def test_meta_params_that_disagree_with_pull_json_are_reported(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    meta_path = store.dir / "pages" / "0000.meta.json"
    meta = load(meta_path)
    meta["params"]["count"] = 11
    save(meta_path, meta)
    assert any("page 0: meta does not match pull.json" in p for p in verify_candle_pull(store.dir).problems)


def test_stored_request_params_must_match_the_replayed_request(tmp_path):
    """Consistent but wrong params (meta and pull.json agree, the bytes are intact): the replay
    asks for a different request than the one stored, so the stored path is not reproducible."""
    _, store, _ = stored_pull(tmp_path)
    doc = load(store.dir / "pull.json")
    meta_path = store.dir / "pages" / "0001.meta.json"
    meta = load(meta_path)
    for params in (doc["pages"][1]["params"], meta["params"]):
        params["to"] = "2026-10-10T07:00:00Z"
    save(store.dir / "pull.json", doc)
    save(meta_path, meta)
    rep = verify_candle_pull(store.dir)
    assert any(p.startswith("replay failed") and "page 1: replay requested" in p for p in rep.problems)


def test_stored_report_that_differs_from_replay_is_reported(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    doc = load(store.dir / "pull.json")
    doc["report"]["candles"] += 1
    doc["report"]["excluded_incomplete"] = 3
    save(store.dir / "pull.json", doc)
    rep = verify_candle_pull(store.dir)
    assert any("stored report differs from replay in ['candles', 'excluded_incomplete']" in p for p in rep.problems)
    assert rep.replay["candles"] == 25  # the replay itself is reported, not the edited numbers


def test_replay_that_stops_before_using_every_stored_page_is_reported(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    doc = load(store.dir / "pull.json")
    doc["requested_start"] = "2026-10-10T20:00:00Z"  # replay reaches this start on the first page
    save(store.dir / "pull.json", doc)
    rep = verify_candle_pull(store.dir)
    assert any("replay used 1 of 3 stored pages" in p for p in rep.problems)


def test_replay_page_limit_in_settings_is_enforced(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    doc = load(store.dir / "pull.json")
    doc["settings"]["max_pages"] = 1
    save(store.dir / "pull.json", doc)
    assert any("page limit 1 reached" in p for p in verify_candle_pull(store.dir).problems)


def test_pull_without_settings_cannot_be_replayed(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    doc = load(store.dir / "pull.json")
    del doc["settings"]
    save(store.dir / "pull.json", doc)
    assert verify_candle_pull(store.dir).problems == ["pull.json has no pull settings; cannot replay"]


def test_failed_pull_is_not_ok(tmp_path):
    def handler(method, url, params):
        if "to" in params and params["to"] != "2026-10-11T01:00:00Z":
            return make_response(503, "{}", url=url)
        return Server(series(utc(2026, 10, 10), 25, "hour"))(method, url, params)
    c, _ = client(handler, max_retries=0)
    with pytest.raises(Exception):
        pull_to_store(c, tmp_path, "KRW-BTC", "hour", utc(2026, 10, 10), utc(2026, 10, 11, 1), provenance="fixture",
                      page_count=10)
    (pull_dir,) = tmp_path.iterdir()
    rep = verify_candle_pull(pull_dir)
    assert rep.status == "failed" and not rep.ok and rep.replay is None
    assert any("status is 'failed'" in p and "HTTP 503" in p for p in rep.problems)
    assert rep.pages_checked == 1  # the page saved before the failure still checks out


def test_running_pull_is_not_ok(tmp_path):
    _, store, _ = stored_pull(tmp_path)
    doc = load(store.dir / "pull.json")
    doc["status"], doc["report"] = "running", None
    save(store.dir / "pull.json", doc)
    assert any("status is 'running'" in p for p in verify_candle_pull(store.dir).problems)


@pytest.mark.parametrize("content", [b"{not json", b'{"schema": "other/1"}', b"[]"])
def test_unreadable_or_foreign_pull_json(tmp_path, content):
    (tmp_path / "pull.json").write_bytes(content)
    rep = verify_candle_pull(tmp_path)
    assert not rep.ok and len(rep.problems) == 1


def test_missing_pull_dir(tmp_path):
    rep = verify_candle_pull(tmp_path / "nope")
    assert not rep.ok and rep.problems[0].startswith("cannot read pull.json")


# --- synthetic fixture source ------------------------------------------------------------------

def test_fixture_series_shape():
    fx = CandleFixture.load(FIXTURE)
    day = fx.rows["day"]
    assert day[0]["candle_date_time_utc"] == "2026-01-15T00:00:00"  # newest first, in progress at now_utc
    assert day[0]["timestamp"] == int(fx.now.timestamp() * 1000)
    assert "2026-01-08T00:00:00" not in {r["candle_date_time_utc"] for r in day}
    assert all(r["candle_date_time_kst"][11:13] == "09" for r in day)
    assert {r["unit"] for r in fx.rows["hour"]} == {60}


def test_fixture_must_be_marked_synthetic(tmp_path):
    doc = load(FIXTURE)
    doc["meta"]["synthetic"] = False
    save(tmp_path / "f.json", doc)
    with pytest.raises(ValueError, match="not marked synthetic"):
        CandleFixture.load(tmp_path / "f.json")


# --- CLI: collect -> store -> verify -> replay ----------------------------------------------------

@pytest.fixture
def no_network(monkeypatch):
    """Any real HTTP request fails the test (the scripted fixture session overrides request())."""
    def refuse(self, *a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(requests.Session, "request", refuse)


def only_pull(out: Path) -> Path:
    (d,) = [p for p in out.iterdir() if p.is_dir()]
    return d


@pytest.mark.parametrize("interval, first, last", [
    ("day", "2026-01-06T00:00:00Z", "2026-01-14T00:00:00Z"),
    ("hour", "2026-01-15T01:00:00Z", "2026-01-15T09:00:00Z"),
])
def test_cli_fixture_pull_stores_verifies_and_replays(tmp_path, no_network, interval, first, last):
    out = tmp_path / "pulls"
    assert main(["candles-pull", "--interval", interval, "--last", "10", "--source", "fixture",
                 "--out", str(out)]) == 0
    d = only_pull(out)
    doc = load(d / "pull.json")
    assert doc["provenance"] == "fixture" and doc["synthetic"] and doc["origin"] == "fixture:upbit_candles_synthetic.json"
    assert len(doc["pages"]) == 1 and doc["pages"][0]["params"]["count"] == 10  # one request, at most 10 rows
    assert sorted(f.name for f in (d / "pages").iterdir()) == ["0000.json", "0000.meta.json"]
    r = doc["report"]
    assert r["rows_received"] == 10 and r["excluded_incomplete"] == 1 and r["excluded_out_of_range"] == 1
    assert r["candles"] == 8 and r["missing_buckets"] == 1 and r["duplicates_conflicting"] == [] and r["ok"]
    assert (r["first_start"], r["last_start"]) == (first, last)
    assert main(["candles-verify", str(d)]) == 0
    assert main(["candles-verify", str(d), "--json"]) == 0
    assert verify_candle_pull(d).replay == r


def test_cli_fixture_with_inclusive_to_and_small_pages(tmp_path, no_network):
    doc = load(FIXTURE)
    doc["meta"]["inclusive_to"] = True
    save(tmp_path / "fx.json", doc)
    out = tmp_path / "pulls"
    assert main(["candles-pull", "--interval", "day", "--last", "10", "--page-count", "4", "--source", "fixture",
                 "--fixture", str(tmp_path / "fx.json"), "--out", str(out)]) == 0
    r = load(only_pull(out) / "pull.json")["report"]
    assert r["pages"] == 3 and r["duplicates_identical"] == 2 and r["candles"] == 8
    assert main(["candles-verify", str(only_pull(out))]) == 0


def test_cli_verify_fails_on_tampered_fixture_pull(tmp_path, no_network):
    out = tmp_path / "pulls"
    assert main(["candles-pull", "--interval", "day", "--last", "3", "--source", "fixture", "--out", str(out)]) == 0
    page = only_pull(out) / "pages" / "0000.json"
    page.write_bytes(page.read_bytes().replace(b"KRW-BTC", b"KRW-BTX", 1))
    assert main(["candles-verify", str(only_pull(out))]) == 1


def test_cli_fixture_runs_never_share_a_directory(tmp_path, no_network):
    out = tmp_path / "pulls"
    for _ in range(2):
        assert main(["candles-pull", "--interval", "hour", "--last", "2", "--source", "fixture", "--out", str(out)]) == 0
    assert len([p for p in out.iterdir() if p.is_dir()]) == 2


@pytest.mark.parametrize("source", ["live", "fixture"])
def test_cli_dry_run_sends_nothing_and_writes_nothing(tmp_path, no_network, monkeypatch, source, capsys):
    monkeypatch.setattr(cli, "candle_http_client", lambda *a, **k: pytest.fail("client built in a dry run"))
    out = tmp_path / "pulls"
    assert main(["candles-pull", "--interval", "day", "--last", "10", "--source", source, "--out", str(out),
                 "--dry-run"]) == 0
    assert not out.exists()
    text = capsys.readouterr().out
    assert "page_count 10, at most 2 page request(s)" in text and "dry run" in text


@pytest.mark.parametrize("argv", [
    ["--last", "10", "--start", "2026-01-01T00:00:00Z"],
    ["--start", "2026-01-01T00:00:00Z"],
    ["--start", "2026-01-01T00:00:00", "--end", "2026-01-05T00:00:00Z"],   # no timezone
    ["--start", "2026-01-01T05:00:00Z", "--end", "2026-01-05T00:00:00Z"],  # not a day boundary
    ["--start", "2026-01-05T00:00:00Z", "--end", "2026-01-01T00:00:00Z"],
    ["--last", "0"],
    ["--last", "10", "--page-count", "0"],
    ["--last", "10", "--page-count", "201"],
    ["--last", "10", "--max-pages", "0"],
    ["--last", "10", "--market", "BTC"],
])
def test_cli_refuses_bad_arguments_without_creating_anything(tmp_path, no_network, argv):
    out = tmp_path / "pulls"
    assert main(["candles-pull", "--interval", "day", "--source", "fixture", "--out", str(out), *argv]) == 1
    assert not out.exists()


def test_cli_refuses_unmarked_fixture(tmp_path, no_network):
    doc = load(FIXTURE)
    del doc["meta"]["synthetic"]
    save(tmp_path / "fx.json", doc)
    out = tmp_path / "pulls"
    assert main(["candles-pull", "--interval", "day", "--last", "3", "--source", "fixture",
                 "--fixture", str(tmp_path / "fx.json"), "--out", str(out)]) == 1
    assert not out.exists()


def test_cli_live_path_stops_on_451_without_retry_and_keeps_failed_evidence(tmp_path, monkeypatch):
    """The live branch with its HTTP layer replaced by a FakeSession: no real request is made."""
    session = FakeSession(lambda m, url, p: make_response(451, "blocked", url=url, reason="Unavailable"))
    monkeypatch.setattr(cli, "candle_http_client", lambda *a, **k: HttpClient(REST_BASE_URL, session=session))
    out = tmp_path / "pulls"
    assert main(["candles-pull", "--interval", "day", "--last", "3", "--out", str(out)]) == 3
    assert len(session.calls) == 1
    doc = load(only_pull(out) / "pull.json")
    assert doc["provenance"] == "real" and doc["origin"] == "live" and doc["status"] == "failed"
    assert "HTTP 451" in doc["error"] and doc["pages"] == []
    assert main(["candles-verify", str(only_pull(out))]) == 1


def test_cli_live_path_uses_now_for_last_and_a_single_small_request(tmp_path, monkeypatch):
    rows = series(utc(2026, 10, 3), 10)  # newest (10-12) still open at NOW
    session = FakeSession(Server(rows))
    monkeypatch.setattr(cli, "candle_http_client", lambda *a, **k: HttpClient(REST_BASE_URL, session=session))

    class FrozenDatetime(cli.datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW
    monkeypatch.setattr(cli, "datetime", FrozenDatetime)
    monkeypatch.setattr("moneylab.providers.upbit.candles.datetime", FrozenDatetime)
    out = tmp_path / "pulls"
    assert main(["candles-pull", "--interval", "day", "--last", "10", "--out", str(out)]) == 0
    assert [p for _, _, p in session.calls] == [{"market": "KRW-BTC", "count": 10, "to": "2026-10-13T00:00:00Z"}]
    r = load(only_pull(out) / "pull.json")["report"]
    assert r["candles"] == 9 and r["excluded_incomplete"] == 1 and r["missing_buckets"] == 0
