import json

import pytest
import requests
from conftest import FakeSession, make_response

from moneylab.core.diagnostics import analyze_response, parse_cdn_error_body, parse_trace, run_diagnostics
from moneylab.core.exceptions import ApiError, NetworkError, ProviderError
from moneylab.core.http import HttpClient, HttpDiagnostics
from moneylab.providers.base import MarketQuery
from moneylab.providers.polymarket import GammaApiSource, PolymarketProvider


def client_for(handler):
    return HttpClient("https://gamma-api.polymarket.com", timeout=1, session=FakeSession(handler))


def test_451_raises_api_error_with_full_diagnostics(response_451):
    http = client_for(lambda *a: response_451)
    with pytest.raises(ApiError) as ei:
        http.get_json("/markets", params={"limit": 1})
    d = ei.value.diagnostics
    assert d.status_code == 451
    assert d.reason == "Unavailable For Legal Reasons"
    assert d.headers["Server"] == "cloudflare"
    assert d.headers["CF-RAY"].endswith("-ICN")
    assert d.body_excerpt == "error code: 1026"


def test_timeout_and_connection_errors_become_network_error():
    for exc in (requests.Timeout("t"), requests.ConnectionError("c")):
        http = client_for(lambda *a, e=exc: e)
        with pytest.raises(NetworkError):
            http.get_json("/markets")


def test_invalid_json_is_api_error():
    http = client_for(lambda *a: make_response(200, "<html>oops</html>", {"Content-Type": "text/html"}))
    with pytest.raises(ApiError) as ei:
        http.get_json("/markets")
    assert ei.value.diagnostics.error == "Response body is not valid JSON"


def test_session_ignores_environment_proxies():
    assert client_for(lambda *a: None).session.trust_env is False


def test_sensitive_headers_are_redacted():
    resp = make_response(403, "denied", {"Set-Cookie": "session=abc", "CF-Connecting-IP": "1.2.3.4", "Server": "x"})
    d = HttpDiagnostics.from_response(resp, 1.0)
    assert d.headers["Set-Cookie"] == "***REDACTED***"
    assert d.headers["CF-Connecting-IP"] == "***REDACTED***"
    assert d.headers["Server"] == "x"


def test_provider_wraps_451_and_keeps_diagnostics(response_451):
    provider = PolymarketProvider(GammaApiSource(client_for(lambda *a: response_451)))
    with pytest.raises(ProviderError) as ei:
        provider.get_markets(MarketQuery(max_markets=5))
    assert ei.value.diagnostics.status_code == 451


def test_gamma_pagination_and_raw_sink():
    pages = {0: [{"id": str(i), "question": "q"} for i in range(100)], 100: [{"id": "x", "question": "q"}]}
    saved = []

    def handler(method, url, params):
        return make_response(200, json.dumps(pages[params["offset"]]), {"Content-Type": "application/json"})

    src = GammaApiSource(client_for(handler), raw_sink=lambda name, payload: saved.append(name))
    raw = src.fetch_markets(max_markets=250, active_only=True, order="volume24hr")
    assert len(raw) == 101
    assert saved == ["gamma_markets_offset0", "gamma_markets_offset100"]
    params = src.http.session.calls[0][2]
    assert params["active"] == "true" and params["closed"] == "false" and params["order"] == "volume24hr"


def test_analyze_451_observations(response_451):
    obs = analyze_response(HttpDiagnostics.from_response(response_451, 10))
    text = " ".join(obs)
    assert "Cloudflare edge" in text and "ICN" in text
    assert "CDN error code 1026" in text


def test_analyze_451_structured_json_body(response_451_json):
    obs = analyze_response(HttpDiagnostics.from_response(response_451_json, 10))
    text = " ".join(obs)
    assert "error_code=1026" in text
    assert "error_name=legal_block" in text
    assert "error_category=legal" in text
    assert "retryable=False" in text
    assert "This content is unavailable for legal reasons." in text


def test_parse_cdn_error_body_ignores_non_cloudflare_json():
    assert parse_cdn_error_body('{"error": "x"}') == {}
    assert parse_cdn_error_body("not json") == {}


def test_parse_trace_drops_ip():
    out = parse_trace("fl=1\nip=203.0.113.9\ncolo=ICN\nloc=KR\nwarp=off\n")
    assert out == {"colo": "ICN", "loc": "KR", "warp": "off"}


def test_run_diagnostics_separates_facts_from_hypotheses(response_451_json):
    def handler(method, url, params):
        if "cloudflare.com" in url:
            return make_response(200, "loc=KR\ncolo=ICN\n", url=url)
        if url.endswith("/cdn-cgi/trace"):
            return make_response(200, "ip=203.0.113.9\ncolo=ICN\nloc=KR\nwarp=off\n", url=url)
        return response_451_json

    http = HttpClient("", session=FakeSession(handler))
    report = run_diagnostics(["https://gamma-api.polymarket.com/markets?limit=1"], http)
    assert report.edge_trace == {"colo": "ICN", "loc": "KR", "warp": "off"}
    assert any("Control endpoint reachable" in o for o in report.observations)
    assert any("451" in h for h in report.hypotheses)
    assert any("['legal']" in h for h in report.hypotheses)
    # loc is reported as an observation, never asserted as the cause
    assert not any("loc=KR" in h or "Korea" in h for h in report.hypotheses)
    assert "203.0.113.9" not in json.dumps(report.to_dict(), default=str)
