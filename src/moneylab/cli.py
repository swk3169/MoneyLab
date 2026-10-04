"""MoneyLab command line.

    python -m moneylab scan                         # live Polymarket scan
    python -m moneylab scan --source fixture        # offline, from a saved response
    python -m moneylab diagnose                     # connectivity / HTTP error report

Exit codes: 0 ok, 3 data source unavailable (handled), 1 unexpected error (handled), 2 usage.
"""

from __future__ import annotations

import argparse
import logging
import traceback
from pathlib import Path

from moneylab import __version__
from moneylab.config import Settings, load_settings
from moneylab.core.diagnostics import run_diagnostics
from moneylab.core.http import HttpClient
from moneylab.core.logging_setup import setup_logging
from moneylab.core.redaction import redact_text
from moneylab.display.console import console, render_diagnostics, render_scan
from moneylab.providers.base import MarketDataProvider, MarketQuery
from moneylab.providers.polymarket import GammaApiSource, GammaFileSource, PolymarketProvider
from moneylab.scanner import MarketScanner, ScanCriteria
from moneylab.storage.files import RawStore, save_json, save_markets_csv

log = logging.getLogger("moneylab")

EXIT_OK, EXIT_ERROR, EXIT_UNAVAILABLE = 0, 1, 3
DEFAULT_FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "gamma_markets_sample.json"


def build_provider(args: argparse.Namespace, settings: Settings) -> MarketDataProvider:
    if args.source == "fixture":
        return PolymarketProvider(GammaFileSource(args.fixture))
    http = HttpClient(settings.gamma_url, settings.http_timeout, settings.http_retries, settings.user_agent)
    sink = None if args.no_save else RawStore(settings.raw_dir, "polymarket")
    return PolymarketProvider(GammaApiSource(http, raw_sink=sink))


def cmd_scan(args: argparse.Namespace, settings: Settings) -> int:
    provider = build_provider(args, settings)
    criteria = ScanCriteria(
        min_volume=args.min_volume,
        min_liquidity=args.min_liquidity,
        max_days_to_end=args.max_days,
        binary_only=args.binary_only,
        sort_by=args.sort,
        top_n=args.top,
    )
    query = MarketQuery(max_markets=args.fetch, order_by=args.order or None)
    try:
        result = MarketScanner(provider).scan(criteria, query)
    finally:
        provider.close()

    render_scan(result)
    if not result.ok:
        return EXIT_UNAVAILABLE
    if not args.no_save and args.source != "fixture" and result.candidates:
        path = save_markets_csv([c.market for c in result.candidates], settings.processed_dir)
        console.print(f"[dim]Saved {len(result.candidates)} candidates -> {path}[/dim]")
    return EXIT_OK


def cmd_diagnose(args: argparse.Namespace, settings: Settings) -> int:
    urls = args.url or [
        f"{settings.gamma_url}/markets?limit=1",
        f"{settings.clob_url}/markets",
    ]
    http = HttpClient("", settings.http_timeout, retries=0, user_agent=settings.user_agent)
    try:
        report = run_diagnostics(urls, http, include_control=not args.no_control)
    finally:
        http.close()
    render_diagnostics(report)
    if not args.no_save:
        path = save_json(settings.raw_dir / "diagnostics" / f"{report.created_at.replace(':', '')}.json", report.to_dict())
        console.print(f"[dim]Report saved -> {path}[/dim]")
    return EXIT_OK if all(c.ok for c in report.checks) else EXIT_UNAVAILABLE


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="moneylab", description="MoneyLab - prediction market research (read-only)")
    p.add_argument("--version", action="version", version=f"moneylab {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="scan active markets for candidates")
    s.add_argument("--source", choices=["polymarket", "fixture"], default="polymarket")
    s.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE, help="saved Gamma /markets JSON")
    s.add_argument("--fetch", type=int, default=200, help="max markets to fetch")
    s.add_argument("--order", default="volume24hr", help="server-side Gamma order field ('' to disable)")
    s.add_argument("--min-volume", type=float, default=0.0)
    s.add_argument("--min-liquidity", type=float, default=0.0)
    s.add_argument("--max-days", type=float, default=None, help="only markets ending within N days")
    s.add_argument("--binary-only", action="store_true")
    s.add_argument("--sort", choices=["volume24h", "volume", "liquidity", "end", "spread"], default="volume24h")
    s.add_argument("--top", type=int, default=30)
    s.add_argument("--no-save", action="store_true", help="do not write data/raw or data/processed")
    s.set_defaults(func=cmd_scan)

    d = sub.add_parser("diagnose", help="report HTTP status/headers/body for API endpoints")
    d.add_argument("--url", action="append", help="endpoint to check (repeatable)")
    d.add_argument("--no-control", action="store_true", help="skip control endpoint check")
    d.add_argument("--no-save", action="store_true")
    d.set_defaults(func=cmd_diagnose)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    setup_logging("DEBUG" if args.verbose else settings.log_level)
    try:
        return args.func(args, settings)
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted.[/yellow]")
        return EXIT_ERROR
    except Exception as exc:  # last-resort guard: report, don't crash
        log.error("Unexpected error: %s", redact_text(f"{type(exc).__name__}: {exc}"))
        if args.verbose:
            console.print(redact_text(traceback.format_exc()), markup=False)
        return EXIT_ERROR
