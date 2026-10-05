"""MoneyLab command line.

    python -m moneylab scan                         # live Polymarket scan
    python -m moneylab scan --source fixture        # offline, from a saved response
    python -m moneylab diagnose                     # connectivity / HTTP error report
    python -m moneylab book --source fixture        # order book, spread, depth (offline)
    python -m moneylab simulate --strategy mm       # offline paper simulation from a fixture timeline
    python -m moneylab record --condition-id <id>   # record live CLOB order books (read-only)
    python -m moneylab record --source fixture      # offline recorder run over a fixture timeline
    python -m moneylab record-verify <dataset dir>  # integrity check of a recording
    python -m moneylab simulate --recording <dir>   # paper simulation on recorded data

Exit codes: 0 ok, 3 data source unavailable (handled), 1 unexpected error (handled), 2 usage.
"""

from __future__ import annotations

import argparse
import json
import logging
import traceback
from dataclasses import replace
from pathlib import Path

from moneylab import __version__
from moneylab.config import Settings, load_settings
from moneylab.core.diagnostics import run_diagnostics
from moneylab.core.http import HttpClient
from moneylab.core.logging_setup import setup_logging
from moneylab.core.redaction import redact_text
from moneylab.core.exceptions import ProviderError
from moneylab.display.console import (
    console,
    render_book,
    render_diagnostics,
    render_http_diagnostics,
    render_integrity,
    render_recorder_report,
    render_scan,
    render_simulation,
)
from moneylab.paper.book_stream import ReplayBookStream, TimelineBookStream
from moneylab.paper.runner import SimulationConfig, SimulationRunner
from moneylab.providers.base import MarketDataProvider, MarketQuery
from moneylab.providers.polymarket import (
    ClobApiSource,
    ClobFileSource,
    GammaApiSource,
    GammaFileSource,
    PolymarketClobProvider,
    PolymarketProvider,
    load_timeline,
)
from moneylab.providers.polymarket.recorder import (
    RecorderConfig,
    RecorderStatus,
    RestBookRecorder,
    TimelineFixtureSource,
    open_recording,
    verify_recording,
)
from moneylab.scanner import MarketScanner, ScanCriteria
from moneylab.sizing.position import SizingLimits
from moneylab.strategy.market_making import SymmetricMarketMaker
from moneylab.strategy.mispricing import CombinedMispricing, ComplementArbitrage, FairValueDeviation
from moneylab.storage.files import RawStore, save_json, save_markets_csv

log = logging.getLogger("moneylab")

EXIT_OK, EXIT_ERROR, EXIT_UNAVAILABLE = 0, 1, 3
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
DEFAULT_FIXTURE = FIXTURES / "gamma_markets_sample.json"
DEFAULT_BOOKS = FIXTURES / "clob_books_sample.json"
DEFAULT_TIMELINES = {
    "mm": FIXTURES / "clob_timeline_mm.json",
    "mispricing": FIXTURES / "clob_timeline_mispricing.json",
    "arb": FIXTURES / "clob_timeline_mispricing.json",
    "fair-value": FIXTURES / "clob_timeline_mispricing.json",
}


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


def _first_fixture_token(path: Path) -> str | None:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    first = payload[0] if isinstance(payload, list) and payload else payload
    return str(first["asset_id"]) if isinstance(first, dict) and first.get("asset_id") else None


def cmd_book(args: argparse.Namespace, settings: Settings) -> int:
    token = args.token
    if args.source == "fixture":
        provider = PolymarketClobProvider(ClobFileSource(args.fixture))
        token = token or _first_fixture_token(args.fixture)
    else:
        http = HttpClient(settings.clob_url, settings.http_timeout, settings.http_retries, settings.user_agent)
        sink = None if args.no_save else RawStore(settings.raw_dir, "polymarket")
        provider = PolymarketClobProvider(ClobApiSource(http, raw_sink=sink))
    if not token:
        console.print("[red]--token is required (no token found in the fixture)[/red]")
        return EXIT_ERROR
    try:
        book = provider.get_order_book(token)
    except ProviderError as exc:
        console.print(f"[red]Order book unavailable:[/red] {exc}")
        if exc.diagnostics is not None:
            render_http_diagnostics(exc.diagnostics)
        return EXIT_UNAVAILABLE
    finally:
        provider.close()
    render_book(book, depth_cents=args.depth_cents)
    return EXIT_OK


def build_strategy(name: str):
    if name == "mm":
        return SymmetricMarketMaker()
    if name == "arb":
        return ComplementArbitrage()
    if name == "fair-value":
        return FairValueDeviation()
    return CombinedMispricing((ComplementArbitrage(), FairValueDeviation()))


def cmd_simulate(args: argparse.Namespace, settings: Settings) -> int:
    if args.recording and args.timeline:
        console.print("[red]--recording and --timeline are mutually exclusive[/red]")
        return EXIT_ERROR
    path = args.recording or args.timeline or DEFAULT_TIMELINES[args.strategy]
    try:
        if args.recording:
            source = open_recording(args.recording)
            params, synthetic, description, base_resolution = source.params, source.synthetic, source.description, None
            stream = ReplayBookStream(source, start=args.start, end=args.end)
            for w in source.warnings:
                console.print(f"[yellow]warning:[/yellow] {w}")
        else:
            timeline = load_timeline(path)
            params, synthetic, description = timeline.params, timeline.synthetic, timeline.description
            base_resolution, stream = timeline.resolution, TimelineBookStream(timeline)
    except ProviderError as exc:
        console.print(f"[red]Cannot load {'recording' if args.recording else 'timeline'}:[/red] {exc}")
        return EXIT_UNAVAILABLE
    resolution = base_resolution
    if args.resolution in ("yes", "no"):
        yes, no = params.yes_token, params.no_token
        resolution = {yes: 1.0, no: 0.0} if args.resolution == "yes" else {yes: 0.0, no: 1.0}
    elif args.resolution == "none":
        resolution = None
    config = SimulationConfig(
        starting_cash=args.starting_cash,
        sizing=replace(SizingLimits(), kelly_fraction=args.kelly),
        estimate_rewards=not args.no_reward_estimate,
    )
    runner = SimulationRunner(params, build_strategy(args.strategy), config, synthetic=synthetic)
    try:
        result = runner.run(stream, resolution)
    except ProviderError as exc:  # a corrupt record surfaced mid-replay
        console.print(f"[red]Replay aborted:[/red] {exc}")
        return EXIT_UNAVAILABLE
    render_simulation(result, description)
    if isinstance(stream, ReplayBookStream):
        st = stream.stats
        console.print(f"[dim]replay: {st.snapshots} snapshots, {st.errors} recorded errors, "
                      f"{st.skipped_out_of_order} out-of-order skipped, {st.skipped_outside_window} outside window[/dim]")
    if args.save:
        out = save_json(settings.processed_dir / "simulations" / f"{args.strategy}.json", {
            "strategy": result.strategy, "timeline": str(path), "recording": bool(args.recording),
            "resolution": resolution,
            "breakdown": result.breakdown.to_dict(), "trade_pnls": result.trade_pnls,
            "max_drawdown": result.max_drawdown, "win_rate": result.win_rate,
            "profit_factor": result.profit_factor, "verdict": result.verdict.status,
            "equity_curve": result.equity_curve,
        })
        console.print(f"[dim]Saved -> {out}[/dim]")
    return EXIT_OK


def build_recorder(args: argparse.Namespace, settings: Settings) -> tuple[RestBookRecorder, object]:
    """Offline and live recording differ only in the ClobSource (and the fixture's clock)."""
    if args.source == "fixture":
        src = TimelineFixtureSource(args.fixture)
        cids = tuple(args.condition_id or (src.condition_id,))
        out = args.out or settings.raw_dir / "polymarket" / "recordings-synthetic" / Path(args.fixture).stem
        rebate, rebate_src = (src.rebate_rate, "fixture meta") if args.rebate_rate is None \
            else (args.rebate_rate, "cli --rebate-rate")
        kwargs = {"synthetic": src.synthetic, "origin": f"fixture:{Path(args.fixture).name}",
                  "clock": src.clock, "sleep": src.no_sleep}
    else:
        # retries=0: the recorder owns retry/backoff, so every 429/5xx is seen and recorded.
        http = HttpClient(settings.clob_url, settings.http_timeout, 0, settings.user_agent)
        src = ClobApiSource(http)
        cids = tuple(args.condition_id or settings.recorder_condition_ids)
        out = args.out or settings.recordings_dir
        rebate, rebate_src = (0.0, "unknown: not served by the CLOB, 0 assumed") if args.rebate_rate is None \
            else (args.rebate_rate, "cli --rebate-rate")
        kwargs = {"synthetic": False, "origin": settings.clob_url}
    config = RecorderConfig(
        condition_ids=cids, interval=args.interval or settings.recorder_interval,
        max_polls=args.max_polls, duration=args.duration,
        metadata_refresh=settings.recorder_metadata_refresh,
        max_consecutive_failures=settings.recorder_max_failures,
        rebate_rate=rebate, rebate_rate_source=rebate_src,
    )
    return RestBookRecorder(src, out, config, **kwargs), src


def cmd_record(args: argparse.Namespace, settings: Settings) -> int:
    args.source = args.source or settings.recorder_source
    if args.source not in ("polymarket", "fixture"):
        console.print(f"[red]unknown recorder source {args.source!r} (polymarket | fixture)[/red]")
        return EXIT_ERROR
    if args.source == "polymarket" and not (args.condition_id or settings.recorder_condition_ids):
        console.print("[red]--condition-id (or MONEYLAB_RECORDER_CONDITION_IDS) is required for live recording[/red]")
        return EXIT_ERROR
    try:
        recorder, src = build_recorder(args, settings)
    except (OSError, KeyError, ValueError) as exc:
        console.print(f"[red]Cannot start recorder:[/red] {exc}")
        return EXIT_ERROR
    console.print(f"[dim]Recording {', '.join(recorder.config.condition_ids)} from {args.source} "
                  f"every {recorder.config.interval:g}s (read-only). Ctrl+C stops and saves state.[/dim]")
    try:
        report = recorder.run()
    finally:
        src.close()
    render_recorder_report(report)
    if report.status in (RecorderStatus.BLOCKED_HTTP_451, RecorderStatus.ACCESS_DENIED):
        return EXIT_UNAVAILABLE
    if report.status == RecorderStatus.FAILED:
        storage = (report.last_error or {}).get("category") == "storage"
        return EXIT_ERROR if storage else EXIT_UNAVAILABLE
    return EXIT_OK


def cmd_record_verify(args: argparse.Namespace, settings: Settings) -> int:
    report = verify_recording(args.dataset)
    if args.json:
        console.print_json(json.dumps(report.to_dict()))
    else:
        render_integrity(report)
    return EXIT_OK if report.ok else EXIT_ERROR


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

    b = sub.add_parser("book", help="show a CLOB order book with spread/microprice/depth (read-only)")
    b.add_argument("--source", choices=["polymarket", "fixture"], default="fixture")
    b.add_argument("--fixture", type=Path, default=DEFAULT_BOOKS, help="saved /book or /books JSON")
    b.add_argument("--token", help="token (asset) id; default: first book in the fixture")
    b.add_argument("--depth-cents", type=float, default=2.0)
    b.add_argument("--no-save", action="store_true")
    b.set_defaults(func=cmd_book)

    m = sub.add_parser("simulate", help="offline paper simulation on a replay timeline (no orders, no funds)")
    m.add_argument("--strategy", choices=["mm", "mispricing", "arb", "fair-value"], default="mm")
    m.add_argument("--timeline", type=Path, default=None, help="timeline JSON (fixture or recorded data)")
    m.add_argument("--recording", type=Path, default=None, help="recorded dataset directory (moneylab record)")
    m.add_argument("--start", type=float, default=None, help="replay window start, unix seconds (--recording)")
    m.add_argument("--end", type=float, default=None, help="replay window end, unix seconds (--recording)")
    m.add_argument("--starting-cash", type=float, default=1000.0)
    m.add_argument("--kelly", type=float, default=0.25, help="Kelly fraction (default 0.25)")
    m.add_argument("--resolution", choices=["fixture", "yes", "no", "none"], default="fixture",
                   help="override the timeline's resolution (sensitivity check)")
    m.add_argument("--no-reward-estimate", action="store_true")
    m.add_argument("--save", action="store_true", help="write result JSON to data/processed/simulations/")
    m.set_defaults(func=cmd_simulate)

    r = sub.add_parser("record", help="record CLOB order books + market metadata to data/raw (read-only)")
    r.add_argument("--source", choices=["polymarket", "fixture"], default=None,
                   help="default: MONEYLAB_RECORDER_SOURCE or polymarket")
    r.add_argument("--condition-id", action="append", help="market condition id (repeatable)")
    r.add_argument("--fixture", type=Path, default=DEFAULT_TIMELINES["mm"], help="timeline JSON for --source fixture")
    r.add_argument("--out", type=Path, default=None, help="dataset root directory")
    r.add_argument("--interval", type=float, default=None, help="seconds between polls")
    r.add_argument("--max-polls", type=int, default=None)
    r.add_argument("--duration", type=float, default=None, help="stop after N seconds")
    r.add_argument("--rebate-rate", type=float, default=None,
                   help="maker rebate share for this market (not served by the CLOB)")
    r.set_defaults(func=cmd_record)

    v = sub.add_parser("record-verify", help="integrity check of a recorded dataset (offline)")
    v.add_argument("dataset", type=Path, help="dataset directory (.../recordings/<condition_id>)")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=cmd_record_verify)
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
