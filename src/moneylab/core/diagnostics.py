"""Connectivity diagnostics for HTTP APIs.

Collects *facts* (status, headers, body, CDN edge info) and lists *hypotheses*
separately. It never concludes the cause of a block on its own: a 451/403 from a
CDN can stem from jurisdiction rules, IP reputation/ASN rules or other policies,
and only the server operator knows which applied.

This module only observes. It does not attempt to bypass anything.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from moneylab.core.exceptions import NetworkError
from moneylab.core.http import HttpClient, HttpDiagnostics
from moneylab.core.redaction import redact_text

CF_ERROR_RE = re.compile(r"error code:\s*(\d{3,5})", re.I)
CF_ERROR_FIELDS = ("error_code", "error_name", "error_category", "retryable", "owner_action_required", "zone", "ray_id")
# Control endpoint unrelated to the target API: tells "network down" apart from "target refuses".
CONTROL_URL = "https://www.cloudflare.com/cdn-cgi/trace"
TRACE_KEYS_KEPT = ("colo", "loc", "http", "tls", "warp", "gateway")

STATUS_HINTS: dict[int, list[str]] = {
    451: [
        "Server/CDN-side legal or policy restriction (HTTP 451 'Unavailable For Legal Reasons').",
        "Possible triggers (unverified): jurisdiction derived from client IP, "
        "IP reputation or ASN-based rules (e.g. hosting/VPN ranges), account- or path-level policy.",
        "The exact rule is not observable from the client; check the provider's official "
        "docs/terms on restricted regions and contact the provider if the access should be allowed.",
    ],
    403: [
        "Forbidden: WAF/bot rule, missing auth, or IP-based policy.",
    ],
    429: [
        "Rate limited: slow down; honour Retry-After.",
    ],
}


@dataclass
class EndpointCheck:
    url: str
    ok: bool
    http: HttpDiagnostics | None = None
    network_error: str | None = None
    observations: list[str] = field(default_factory=list)


@dataclass
class DiagnosticReport:
    created_at: str
    checks: list[EndpointCheck]
    control: EndpointCheck | None
    edge_trace: dict[str, str]
    observations: list[str]
    hypotheses: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_trace(text: str) -> dict[str, str]:
    """Parse Cloudflare /cdn-cgi/trace output, keeping only non-identifying keys (no IP)."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key in TRACE_KEYS_KEPT:
            out[key] = value.strip()
    return out


def parse_cdn_error_body(body: str) -> dict[str, Any]:
    """Cloudflare returns a structured JSON error when the client sends Accept: application/json."""
    try:
        data = json.loads(body)
    except ValueError:
        return {}
    if not isinstance(data, dict) or not data.get("cloudflare_error"):
        return {}
    return {k: data[k] for k in (*CF_ERROR_FIELDS, "detail") if k in data}


def analyze_response(diag: HttpDiagnostics) -> list[str]:
    """Derive factual observations from a single HTTP response."""
    obs: list[str] = []
    headers = {k.lower(): v for k, v in diag.headers.items()}
    server = headers.get("server", "")
    if server:
        obs.append(f"Server header: {server}")
    if "cloudflare" in server.lower() or "cf-ray" in headers:
        ray = headers.get("cf-ray", "")
        colo = ray.rsplit("-", 1)[-1] if "-" in ray else "?"
        obs.append(f"Response served by Cloudflare edge (CF-RAY {ray}, edge colo {colo}).")
        if diag.status_code and diag.status_code >= 400:
            obs.append(
                "No origin-specific headers present; the request was most likely answered "
                "at the CDN edge rather than by the API origin."
            )
    cf = parse_cdn_error_body(diag.body_excerpt or "")
    if cf:
        obs.append(
            "CDN error body: "
            + ", ".join(f"{k}={cf[k]}" for k in CF_ERROR_FIELDS if k in cf)
        )
        if cf.get("detail"):
            obs.append(f"CDN error detail (server's own wording): {cf['detail']}")
    else:
        m = CF_ERROR_RE.search(diag.body_excerpt or "")
        if m:
            obs.append(f"Body contains CDN error code {m.group(1)} (see Cloudflare error docs).")
    ctype = headers.get("content-type", "")
    if diag.status_code and diag.status_code >= 400 and "json" not in ctype:
        obs.append(f"Error body is not JSON (Content-Type: {ctype or 'n/a'}).")
    return obs


def check_endpoint(client: HttpClient, url: str) -> EndpointCheck:
    try:
        resp = client.request("GET", url)
    except NetworkError as exc:
        return EndpointCheck(url=url, ok=False, network_error=str(exc))
    diag = HttpDiagnostics.from_response(resp, getattr(resp, "elapsed_ms", 0.0))
    return EndpointCheck(url=url, ok=resp.ok, http=diag, observations=analyze_response(diag))


def run_diagnostics(urls: list[str], client: HttpClient, include_control: bool = True) -> DiagnosticReport:
    checks = [check_endpoint(client, u) for u in urls]

    control = check_endpoint(client, CONTROL_URL) if include_control else None

    # Edge trace on the first target host: how the CDN in front of the API sees this client.
    edge_trace: dict[str, str] = {}
    if checks and checks[0].http and any("cloudflare" in o.lower() for o in checks[0].observations):
        parts = urlsplit(urls[0])
        try:
            resp = client.request("GET", f"{parts.scheme}://{parts.netloc}/cdn-cgi/trace")
            if resp.ok:
                edge_trace = parse_trace(resp.text)
        except NetworkError:
            pass

    observations: list[str] = []
    statuses = sorted({c.http.status_code for c in checks if c.http and c.http.status_code})
    failed = [c for c in checks if not c.ok]
    observations.append(f"{len(checks) - len(failed)}/{len(checks)} target endpoints succeeded; statuses seen: {statuses}.")
    if control is not None:
        observations.append(
            "Control endpoint reachable (general internet/TLS works)."
            if control.ok
            else f"Control endpoint FAILED ({control.network_error or control.http.status_code}): "
            "general connectivity problem likely."
        )
    if edge_trace:
        observations.append(
            f"CDN in front of the target sees this client at loc={edge_trace.get('loc', '?')}, "
            f"colo={edge_trace.get('colo', '?')}, warp={edge_trace.get('warp', '?')}."
        )
    if len(failed) == len(checks) and len({c.http.status_code for c in failed if c.http}) == 1:
        observations.append("All target endpoints fail identically -> host/client-level policy, not endpoint-specific.")

    hypotheses: list[str] = []
    for status in statuses:
        hypotheses.extend(STATUS_HINTS.get(status, []))
    categories = {
        parse_cdn_error_body(c.http.body_excerpt).get("error_category")
        for c in failed if c.http
    } - {None}
    if categories:
        hypotheses.append(
            f"The CDN itself labels the block as category {sorted(categories)}; it does not state "
            "which client attribute (location, network, other) triggered it."
        )
    if any(c.network_error for c in checks):
        hypotheses.append("Network-level failure (DNS/TLS/firewall/timeout) on at least one endpoint.")

    return DiagnosticReport(
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        checks=checks,
        control=control,
        edge_trace=edge_trace,
        observations=[redact_text(o) for o in observations],
        hypotheses=hypotheses,
    )
