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
    python -m moneylab record --provider upbit --duration 60          # real Upbit KRW-BTC WebSocket (public)
    python -m moneylab record --provider upbit --source fixture       # offline, scripted synthetic session
    python -m moneylab replay-check <upbit dataset dir>               # recorder -> replay consistency
    python -m moneylab clock-monitor --duration 1800                  # read-only local clock offset log (w32tm)
    python -m moneylab research-build <upbit dataset dir> [--dry-run]  # raw -> events -> grid -> labels -> split
    python -m moneylab research-stats <run dir>                       # train/validation leaderboard (test locked)
    python -m moneylab research-final <run dir>                       # test split, exactly once

Exit codes: 0 ok, 3 data source unavailable (handled), 1 unexpected error (handled), 2 usage.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import subprocess
import time
import traceback
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab import __version__
from moneylab.config import Settings, load_settings
from moneylab.core.clock_monitor import ClockMonitor, ClockThresholds
from moneylab.core.diagnostics import run_diagnostics
from moneylab.core.http import HttpClient
from moneylab.core.logging_setup import setup_logging
from moneylab.core.ratelimit import SlidingWindowLimiter
from moneylab.core.redaction import redact_text
from moneylab.core.exceptions import ProviderError
from moneylab.display.console import (
    console,
    render_book,
    render_clock_summary,
    render_diagnostics,
    render_http_diagnostics,
    render_integrity,
    render_leaderboard,
    render_recorder_report,
    render_replay_check,
    render_research_build,
    render_scan,
    render_simulation,
    render_stream_recorder_report,
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
from moneylab.providers.upbit import WS_PUBLIC_URL, websockets_connector
from moneylab.providers.upbit.recorder import (
    ScriptedWsSource,
    UpbitRecorder,
    UpbitRecorderConfig,
    is_upbit_recording,
    replay_check,
    verify_upbit_recording,
)
from moneylab.providers.upbit.candle_fixture import CandleFixture
from moneylab.providers.upbit.candle_store import (
    DEFAULT_SUBDIR as CANDLES_SUBDIR,
    CandleStoreError,
    pull_to_store,
    verify_candle_pull,
)
from moneylab.providers.upbit.candles import (
    DEFAULT_LIMITS as CANDLE_LIMITS,
    INTERVALS as CANDLE_INTERVALS,
    KST,
    MAX_COUNT as CANDLE_MAX_COUNT,
    CandleParseError,
    UpbitCandleClient,
    candle_http_client,
    is_aligned,
    utc_iso,
)
from moneylab.providers.upbit.endpoints import REST_BASE_URL as UPBIT_REST_URL
from moneylab.providers.upbit.recorder.quality import quality_report
from moneylab.providers.upbit.recorder.store import CAPTURE_MANIFEST, CLOCK_LOG, dataset_dirname, read_json
from moneylab.recording.shutdown import install_stop_signals
from moneylab.providers.upbit.research_export import ExportParams, export_events, raw_manifest, write_raw_manifest
from moneylab.research import pipeline as research
from moneylab.research.config import DEFAULT_CONFIG, load_config
from moneylab.core.clock_monitor import read_log as read_clock_log
from moneylab.core.clock_monitor import summarize as summarize_clock
from moneylab.research.split import InsufficientDataError, SplitLockedError
from moneylab.research.v06 import montecarlo as v06mc
from moneylab.scanner import MarketScanner, ScanCriteria
from moneylab.sizing.position import SizingLimits
from moneylab.strategy.market_making import SymmetricMarketMaker
from moneylab.strategy.mispricing import CombinedMispricing, ComplementArbitrage, FairValueDeviation
from moneylab.storage.atomic import atomic_write_json
from moneylab.storage.files import RawStore, save_json, save_markets_csv
from moneylab.backtest.data import DataIntegrityError
from moneylab.backtest.execution import SCENARIOS as BACKTEST_SCENARIOS
from moneylab.backtest.execution import SUBSTITUTION_RULES as BACKTEST_SUBSTITUTION
from moneylab.backtest.ledger import AccountingError
from moneylab.backtest.portfolio import RunConfig as BacktestRunConfig
from moneylab.backtest.run import INITIAL_CASH_KRW, RunError, run_backtest, verify_run
from moneylab.backtest.report import ReportError, build_report, check_report
from moneylab.backtest.segment import SegmentError, export_segment
from moneylab.backtest.settings import DEFAULT_SETTINGS_FILE as BACKTEST_SETTINGS, SettingsError, cost_model
from moneylab.backtest.settings import load_cost_settings
from moneylab.backtest.strategy import RULES as BACKTEST_RULES
from moneylab.domain.bars import NOT_EVIDENCE
from moneylab.providers.upbit.bar_export import BarExportError, export_bars
from moneylab.backtest.code_state import classify_worktree, parse_porcelain_z
from moneylab.research.config import ROOT as REPO_ROOT

log = logging.getLogger("moneylab")

EXIT_OK, EXIT_ERROR, EXIT_UNAVAILABLE = 0, 1, 3
FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
DEFAULT_FIXTURE = FIXTURES / "gamma_markets_sample.json"
DEFAULT_BOOKS = FIXTURES / "clob_books_sample.json"
DEFAULT_UPBIT_FIXTURE = FIXTURES / "upbit_ws_timeline_synthetic.json"
DEFAULT_CANDLE_FIXTURE = FIXTURES / "upbit_candles_synthetic.json"
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
    if args.recording and is_upbit_recording(args.recording):
        console.print("[red]Upbit recordings are spot order books, not prediction markets; the simulation "
                      "strategies assume binary outcome prices and are not connected to Upbit data. "
                      "Use `moneylab replay-check` to replay it.[/red]")
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


def cmd_record_upbit(args: argparse.Namespace, settings: Settings) -> int:
    """Public Upbit WebSocket (live) or a scripted synthetic session (fixture). Read-only."""
    source = args.source or "live"
    if source not in ("live", "fixture"):
        console.print(f"[red]--provider upbit supports --source live | fixture, not {source!r}[/red]")
        return EXIT_ERROR
    try:
        config = UpbitRecorderConfig(
            markets=tuple(m.upper() for m in (args.market or settings.upbit_markets)),
            orderbook_units=args.orderbook_units or settings.upbit_orderbook_units,
            duration=args.duration, max_market_events=args.max_events,
            ping_text_interval=args.ping_interval, max_consecutive_failures=settings.upbit_max_failures,
            status_interval=args.status_interval, disk_check_interval=args.disk_check_interval,
            min_free_bytes=int(args.min_free_gb * 1e9), stop_on_clock_unstable=args.stop_on_clock_unstable,
        )
        if source == "fixture":
            src = ScriptedWsSource(args.fixture or DEFAULT_UPBIT_FIXTURE)
            if not src.synthetic:
                raise ValueError(f"{src.path} is not marked synthetic; fixtures must never pose as real data")
            out = args.out or settings.upbit_fixture_recordings_dir / src.path.stem
            recorder = UpbitRecorder(src, WS_PUBLIC_URL, out, config, provenance="fixture",
                                     origin=f"fixture:{src.path.name}", clock=src.clock, sleep=src.sleep)
        else:
            out = args.out or settings.upbit_recordings_dir
            monitor = None
            if not args.no_clock_monitor:  # read-only; logs next to the (first) market's raw data
                monitor = ClockMonitor(Path(out) / dataset_dirname(config.markets[0]) / CLOCK_LOG,
                                       server=args.clock_server, interval=args.clock_interval)
            recorder = UpbitRecorder(websockets_connector(), WS_PUBLIC_URL, out, config, provenance="real",
                                     clock_monitor=monitor)
    except (OSError, KeyError, ValueError) as exc:
        console.print(f"[red]Cannot start recorder:[/red] {exc}")
        return EXIT_ERROR
    label = "SYNTHETIC fixture session" if source == "fixture" else WS_PUBLIC_URL
    console.print(f"[dim]Recording Upbit {', '.join(config.markets)} orderbook({config.orderbook_units}) + trade "
                  f"from {label} (public, read-only). Ctrl+C / Ctrl+Break stops and saves.[/dim]")
    if recorder.clock_monitor is not None:
        recorder.clock_monitor.start()
    restore = install_stop_signals(recorder.stop)
    try:
        report = recorder.run()
    finally:
        restore()
    render_stream_recorder_report(report)
    if report.status in (RecorderStatus.BLOCKED_HTTP_451, RecorderStatus.ACCESS_DENIED,
                         RecorderStatus.BANNED_HTTP_418):
        return EXIT_UNAVAILABLE
    if report.status == RecorderStatus.FAILED:
        storage = (report.last_error or {}).get("category") == "storage"
        return EXIT_ERROR if storage else EXIT_UNAVAILABLE
    return EXIT_OK


def cmd_record(args: argparse.Namespace, settings: Settings) -> int:
    if args.provider == "upbit":
        return cmd_record_upbit(args, settings)
    if args.market or args.max_events is not None or args.orderbook_units:
        console.print("[red]--market/--max-events/--orderbook-units are Upbit options (--provider upbit)[/red]")
        return EXIT_ERROR
    args.source = args.source or settings.recorder_source
    if args.source == "live":
        args.source = "polymarket"
    args.fixture = args.fixture or DEFAULT_TIMELINES["mm"]
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
    upbit = is_upbit_recording(args.dataset)
    report = verify_upbit_recording(args.dataset) if upbit else verify_recording(args.dataset)
    if args.json:
        console.print_json(json.dumps(report.to_dict()))
    else:
        render_integrity(report)
    return EXIT_OK if report.ok else EXIT_ERROR


def cmd_replay_check(args: argparse.Namespace, settings: Settings) -> int:
    if not is_upbit_recording(args.dataset):
        console.print(f"[red]{args.dataset} is not an Upbit recording[/red]")
        return EXIT_ERROR
    try:
        report = replay_check(args.dataset)
    except ProviderError as exc:
        console.print(f"[red]Replay failed:[/red] {exc}")
        return EXIT_UNAVAILABLE
    if args.json:
        console.print_json(json.dumps(report.to_dict(), default=str))
    else:
        render_replay_check(report)
    return EXIT_OK if report.ok else EXIT_ERROR


def cmd_clock_monitor(args: argparse.Namespace, settings: Settings) -> int:
    """Standalone read-only clock log (never changes the system clock)."""
    mon = ClockMonitor(args.out, server=args.server, interval=args.interval, samples_per_measurement=args.samples)
    console.print(f"[dim]Clock monitor -> {args.out} every {args.interval:g}s for {args.duration:g}s "
                  f"(w32tm /stripchart, read-only). Ctrl+C stops.[/dim]")
    end = time.time() + args.duration
    try:
        while True:
            s = mon.measure_once()
            console.print(f"{s.timestamp_iso} {s.measurement_status} offset="
                          f"{'-' if s.measured_offset_ms is None else f'{s.measured_offset_ms:.1f}ms'}  "
                          f"status={mon.status}")
            if time.time() + args.interval > end:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        console.print("[yellow]stopped[/yellow]")
    render_clock_summary(mon.summary())
    return EXIT_OK


def _clock_metadata(dataset: Path, cfg) -> dict | None:
    """Clock log next to the raw data, re-classified with the pre-registered thresholds."""
    samples = read_clock_log(dataset / CLOCK_LOG)
    if not samples:
        return None
    return summarize_clock(samples, ClockThresholds(cfg.clock_warn_ms, cfg.clock_unstable_ms,
                                                    cfg.clock_unstable_seconds, cfg.clock_unstable_min_measurements,
                                                    cfg.clock_stale_seconds))


def cmd_research_build(args: argparse.Namespace, settings: Settings) -> int:
    """Upbit raw dataset (read-only) -> processed events -> research run (grid, features, labels, split)."""
    dataset = Path(args.dataset)
    if not is_upbit_recording(dataset):
        console.print(f"[red]{dataset} is not an Upbit recording[/red]")
        return EXIT_ERROR
    overrides = {}
    if args.embargo_seconds is not None:
        if not args.dry_run:
            console.print("[red]--embargo-seconds changes the pre-registered split; only allowed with --dry-run[/red]")
            return EXIT_ERROR
        overrides["embargo_seconds"] = args.embargo_seconds
    try:
        cfg = load_config(args.config, **overrides)
    except (OSError, KeyError, ValueError) as exc:
        console.print(f"[red]Bad research config:[/red] {exc}")
        return EXIT_ERROR
    integrity = verify_upbit_recording(dataset)
    if not integrity.ok:
        render_integrity(integrity)
        console.print("[red]Integrity check failed; refusing to build research data from this dataset[/red]")
        return EXIT_ERROR
    ds = read_json(dataset / "dataset.json")
    if ds.get("provenance") != "real" and not args.allow_fixture:
        console.print(f"[red]provenance={ds.get('provenance')!r}: research needs real data "
                      "(--allow-fixture for pipeline tests; results are NOT_EVIDENCE)[/red]")
        return EXIT_ERROR
    session_id = args.session_id or dataset.resolve().parent.name
    root = args.out or settings.processed_dir
    proc = root / "upbit" / session_id / ds["market"]
    before = raw_manifest(dataset)
    write_raw_manifest(dataset, proc / "raw_manifest.json")
    params = ExportParams(cfg.warmup_seconds, cfg.stale_book_seconds)
    quality = quality_report(dataset, params, cfg.gap_seconds).to_dict()
    atomic_write_json(proc / "quality.json", quality)
    events_path = proc / "events.jsonl.gz"
    export_events(dataset, events_path, params)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = root / "research" / f"{session_id}__{'DRYRUN__' if args.dry_run else ''}{stamp}"
    source = {"provenance": ds.get("provenance"), "market": ds.get("market"), "raw_dataset": str(dataset),
              "raw_manifest_sha256": before["manifest_sha256"], "integrity_ok": integrity.ok,
              "integrity_warnings": integrity.counts.get("warnings_total", 0), "processed_dir": str(proc),
              "quality": quality, "clock": _clock_metadata(dataset, cfg),
              "capture": _capture_summary(dataset)}
    try:
        manifest = research.build(events_path, run_dir, cfg, session_id=session_id, source=source,
                                  dry_run=args.dry_run, allow_fixture=args.allow_fixture)
    except (research.ProvenanceError, InsufficientDataError, ValueError) as exc:
        console.print(f"[red]research-build refused:[/red] {exc}")
        return EXIT_ERROR
    if raw_manifest(dataset)["manifest_sha256"] != before["manifest_sha256"]:
        console.print("[red]raw dataset changed during research-build (it must be immutable)[/red]")
        return EXIT_ERROR
    render_research_build(manifest)
    console.print(f"run dir: {run_dir}")
    return EXIT_OK


def _capture_summary(dataset: Path) -> dict | None:
    path = dataset / CAPTURE_MANIFEST
    if not path.exists():
        return None
    doc = read_json(path)
    runs = doc.get("runs") or []
    return {"runs": len(runs), "termination_reasons": [r.get("termination_reason") for r in runs],
            "all_final": all(r.get("final") for r in runs), "raw_manifest_sha256": doc.get("raw_manifest_sha256"),
            "disk_free_start_bytes": runs[0].get("disk_free_start_bytes") if runs else None,
            "disk_free_end_bytes": runs[-1].get("disk_free_end_bytes") if runs else None}


def cmd_research_stats(args: argparse.Namespace, settings: Settings) -> int:
    try:
        cfg = research.config_for_run(args.run_dir, args.config)
        result = research.stats(args.run_dir, cfg)
    except (OSError, KeyError, ValueError, SplitLockedError) as exc:
        console.print(f"[red]research-stats refused:[/red] {exc}")
        return EXIT_ERROR
    m = result["manifest"]
    render_leaderboard(result["leaderboard"], m["evidence"], f"{m['kind']} validation (test LOCKED)", args.top)
    console.print(f"leaderboard: {Path(args.run_dir) / research.STATS_DIR / 'leaderboard.csv'}")
    return EXIT_OK


def cmd_research_final(args: argparse.Namespace, settings: Settings) -> int:
    try:
        cfg = research.config_for_run(args.run_dir, args.config)
        result = research.final(args.run_dir, cfg)
    except (OSError, KeyError, ValueError, SplitLockedError) as exc:
        console.print(f"[red]research-final refused:[/red] {exc}")
        return EXIT_ERROR
    m = result["manifest"]
    render_leaderboard(result["leaderboard"], m["evidence"], f"{m['kind']} FINAL (test opened once)", args.top)
    return EXIT_OK


def _parse_utc(text: str, name: str) -> datetime:
    t = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError(f"{name} needs an explicit timezone, e.g. 2026-10-01T00:00:00Z")
    return t.astimezone(UTC)


def candle_window(interval: str, now: datetime, last: int | None, start: str | None,
                  end: str | None) -> tuple[datetime, datetime]:
    """[start, end) in UTC. --last N = the N most recent buckets, the one still in progress included
    (the pull drops it as incomplete), so N buckets cost one page of N rows."""
    step = CANDLE_INTERVALS[interval][1]
    if last is not None:
        if start or end:
            raise ValueError("--last cannot be combined with --start/--end")
        if last < 1:
            raise ValueError("--last must be >= 1")
        floor = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        if interval == "day":
            floor = floor.replace(hour=0)
        return floor + step - last * step, floor + step
    if not (start and end):
        raise ValueError("give --last N, or both --start and --end")
    s, e = _parse_utc(start, "--start"), _parse_utc(end, "--end")
    if not (is_aligned(s, interval) and is_aligned(e, interval)):
        raise ValueError(f"--start/--end must be on {interval} bucket boundaries (UTC)")
    if s >= e:
        raise ValueError("--start must be before --end")
    return s, e


def _kst(iso: str | None) -> str:
    if not iso:
        return "-"
    return (_parse_utc(iso, "time") + KST).strftime("%Y-%m-%d %H:%M KST")


def render_candle_report(r: dict[str, Any]) -> None:
    console.print(f"pages {r['pages']}, rows received {r['rows_received']}, candles kept {r['candles']}: "
                  f"{r['first_start']} .. {r['last_start']} UTC ({_kst(r['first_start'])} .. {_kst(r['last_start'])})",
                  markup=False)
    console.print(f"excluded: in progress {r['excluded_incomplete']}, outside range {r['excluded_out_of_range']}; "
                  f"duplicates: identical {r['duplicates_identical']}, conflicting {len(r['duplicates_conflicting'])}; "
                  f"missing buckets {r['missing_buckets']}; invalid values {len(r['invalid'])}", markup=False)
    for g in r["gaps"]:
        console.print(f"  gap: {g['missing']} bucket(s) after {g['after']} before {g['before']} (not filled)", markup=False)
    for c in r["duplicates_conflicting"]:
        console.print(f"  conflicting duplicate at {c} (first received kept)", markup=False)
    for bad in r["invalid"]:
        console.print(f"  invalid {bad['start_utc']}: {', '.join(bad['problems'])}", markup=False)
    for w in r["warnings"]:
        console.print(f"  warning: {w}", markup=False)
    console.print("[green]quality ok[/green]" if r["ok"] else "[red]quality NOT ok[/red]")


def render_candle_verify(rep: Any) -> None:
    console.print(f"verify {rep.pull_dir}: provenance {rep.provenance}, status {rep.status}, "
                  f"pages checked {rep.pages_checked}, candles on replay {rep.candles}", markup=False)
    for p in rep.problems:
        console.print(f"  problem: {p}", markup=False)
    console.print("[green]verify ok: hashes, file set and replay match[/green]" if rep.ok else "[red]verify FAILED[/red]")


def cmd_candles_pull(args: argparse.Namespace, settings: Settings) -> int:
    """v0.6: public Upbit candles -> raw pages + pull.json, then an offline verify. Read-only."""
    fixture = args.source == "fixture"
    try:
        if fixture:
            fx = CandleFixture.load(args.fixture or DEFAULT_CANDLE_FIXTURE)
            now, origin, provenance = fx.now, f"fixture:{fx.path.name}", "fixture"
            out = args.out or settings.raw_dir / "upbit" / "candles_v06-fixture"
        else:
            now, origin, provenance = datetime.now(UTC), "live", "real"
            out = args.out or settings.raw_dir / CANDLES_SUBDIR
        start, end = candle_window(args.interval, now, args.last, args.start, args.end)
        buckets = int((end - start) / CANDLE_INTERVALS[args.interval][1])
        page_count = min(CANDLE_MAX_COUNT, buckets) if args.page_count is None else args.page_count
        if not 1 <= page_count <= CANDLE_MAX_COUNT:
            raise ValueError(f"--page-count must be 1..{CANDLE_MAX_COUNT}")
        max_pages = math.ceil(buckets / page_count) + 1 if args.max_pages is None else args.max_pages
        if max_pages < 1:
            raise ValueError("--max-pages must be >= 1")
        market = args.market.upper()
    except (OSError, KeyError, ValueError) as exc:
        console.print(f"[red]candles-pull refused:[/red] {exc}", markup=True)
        return EXIT_ERROR
    label = "SYNTHETIC fixture " + origin if fixture else f"LIVE {UPBIT_REST_URL}{CANDLE_INTERVALS[args.interval][0]}"
    console.print(f"candles-pull {market} {args.interval} from {label} (public market data only)", markup=False)
    console.print(f"  range [{utc_iso(start)}, {utc_iso(end)}) = {buckets} bucket(s); "
                  f"{_kst(utc_iso(start))} .. {_kst(utc_iso(end))}", markup=False)
    console.print(f"  page_count {page_count}, at most {max_pages} page request(s) (each retried at most twice "
                  f"on 429/5xx/timeout)", markup=False)
    console.print(f"  output: {out}/{args.interval}_{market}_<UTC stamp>/ (new directory, never overwrites)",
                  markup=False)
    if args.dry_run:
        console.print("dry run: no request sent, nothing written", markup=False)
        return EXIT_OK

    if fixture:
        sleep = lambda s: None  # noqa: E731 - scripted session, no real clock to wait for
        client = UpbitCandleClient(HttpClient(UPBIT_REST_URL, session=fx.session()), sleep=sleep, utcnow=lambda: now,
                                   limiter=SlidingWindowLimiter(CANDLE_LIMITS, clock=lambda: 0.0, sleep=sleep))
    else:
        client = UpbitCandleClient(candle_http_client(settings.http_timeout, settings.user_agent))
    created: list[Any] = []
    try:
        pull, store = pull_to_store(client, out, market, args.interval, start, end, provenance=provenance,
                                    origin=origin, page_count=page_count, max_pages=max_pages,
                                    on_created=created.append)
    except (ProviderError, CandleStoreError, CandleParseError, ValueError) as exc:
        where = f" (evidence: {created[0].dir})" if created else ""
        console.print(f"candles-pull failed{where}: {redact_text(f'{type(exc).__name__}: {exc}')}", markup=False)
        return EXIT_UNAVAILABLE if isinstance(exc, ProviderError) else EXIT_ERROR
    console.print(f"saved {store.dir}", markup=False)
    render_candle_report(store.doc["report"])
    verify = verify_candle_pull(store.dir)
    render_candle_verify(verify)
    return EXIT_OK if verify.ok and pull.report.ok else EXIT_ERROR


def cmd_candles_verify(args: argparse.Namespace, settings: Settings) -> int:
    rep = verify_candle_pull(args.pull_dir)
    if args.json:
        console.print_json(json.dumps(rep.to_dict()))
    else:
        render_candle_verify(rep)
        if rep.replay:
            render_candle_report(rep.replay)
    return EXIT_OK if rep.ok else EXIT_ERROR


def cmd_research_v06_sim(args: argparse.Namespace, settings: Settings) -> int:
    """v0.6 DRAFT decision rules on SYNTHETIC paths (Monte Carlo). No market data, no API."""
    scenarios = {s.name: s for s in v06mc.tier1_scenarios()}
    if args.list:
        for s in scenarios.values():
            console.print(f"{s.name}: {s.description}", markup=False)
        return EXIT_OK
    names = list(scenarios) if args.scenario == ["all"] else args.scenario or []
    unknown = [n for n in names if n not in scenarios]
    if not names or unknown:
        console.print(f"[red]give --scenario NAME (or all); unknown: {unknown}[/red]")
        return EXIT_ERROR
    if args.reps < 1 or args.bootstrap < 1 or args.draws < 1 or args.workers < 1:
        console.print("[red]--reps, --bootstrap, --draws and --workers must be >= 1[/red]")
        return EXIT_ERROR
    proc = replace(v06mc.Procedure(), bootstrap=args.bootstrap, draws=args.draws)
    cfg = v06mc.RunConfig(reps=args.reps, seed=args.seed, workers=args.workers, truth_years=args.truth_years,
                          procedure=proc)
    out = args.out or settings.processed_dir / "research_v06_sim" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    try:
        out.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        console.print(f"[red]cannot create {out}: {exc}[/red]")
        return EXIT_ERROR
    chosen = [scenarios[n] for n in names]
    atomic_write_json(out / "manifest.json", v06mc.manifest(cfg, chosen))
    console.print(f"SYNTHETIC Monte Carlo (NOT_EVIDENCE): {len(chosen)} scenario(s), reps {cfg.reps}, "
                  f"bootstrap {proc.bootstrap}, B1 draws {proc.draws}, workers {cfg.workers} -> {out}", markup=False)
    for s in chosen:
        t0 = time.monotonic()
        result = v06mc.run_scenario(s, cfg)
        atomic_write_json(out / f"{s.name}.json", result)
        study = result["metrics"]["study"]
        console.print(f"  {s.name}: {time.monotonic() - t0:.1f}s, study PAPER(A) "
                      f"{study['A']['study_paper']['estimate']:.4f}, REJECT(A) {study['A']['study_reject']['estimate']:.4f}",
                      markup=False)
    return EXIT_OK


# --- backtest (BT-2b-2): offline, synthetic / fixture bars only until BT-5 --------------------------------

def backtest_code_state(root: Path = REPO_ROOT) -> dict[str, Any]:
    """Commit and classified working tree for backtest manifests (local, read-only git; backtest.code_state)."""
    def git(*args: str) -> bytes | None:
        try:
            out = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout if out.returncode == 0 else None

    head = git("rev-parse", "HEAD")
    status = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries = None
    if status is not None:
        try:
            entries = parse_porcelain_z(status.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            entries = None
    commit = head.decode("ascii", "replace").strip() if head else ""
    return classify_worktree(commit or None, entries)


def _utc_day(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=UTC)


def cmd_bars_export(args: argparse.Namespace, settings: Settings) -> int:
    """Stored fixture candle pull -> verified Bar files (no request, the pull is only read)."""
    out = args.out or settings.processed_dir / "backtest_bars-fixture"
    console.print(f"{NOT_EVIDENCE} | bars-export {args.pull_dir} -> {out}", markup=False)
    try:
        exp = export_bars(args.pull_dir, out)
    except (BarExportError, OSError, ValueError) as exc:
        console.print(f"bars-export refused: {type(exc).__name__}: {exc}", markup=False)
        return EXIT_ERROR
    console.print(f"saved {exp.dir} ({exp.bars} {exp.interval} bars, bars_sha256 {exp.bars_sha256})", markup=False)
    return EXIT_OK


def cmd_backtest(args: argparse.Namespace, settings: Settings) -> int:
    """One rule over exported bars; writes a new run directory. Initial cash is fixed (1,000,000 KRW)."""
    out = args.out or settings.processed_dir / "backtest-fixture"
    try:
        cost_settings, _ = load_cost_settings(args.settings)
        costs, verified = cost_model(cost_settings, args.fee_bps, args.scenario, INITIAL_CASH_KRW,
                                     impact=not args.no_impact, fee_basis=args.fee_basis)
        cfg = BacktestRunConfig(args.rule, _utc_day(args.first_day), _utc_day(args.last_day), INITIAL_CASH_KRW, costs,
                                scenario=args.scenario, fill_substitution=args.fill_substitution,
                                capacity_verified=verified)
        output = run_backtest(args.daily, args.hourly, cfg, out, code_state=backtest_code_state(), settings_file=args.settings,
                              now=datetime.now(UTC))
    except (RunError, SettingsError, DataIntegrityError, AccountingError, OSError, ValueError) as exc:
        console.print(f"{NOT_EVIDENCE} | backtest refused: {type(exc).__name__}: {exc}", markup=False)
        return EXIT_ERROR
    m = output.result.to_dict()["metrics"]
    console.print(" | ".join(output.manifest["labels"]), markup=False)
    console.print(f"saved {output.dir}", markup=False)
    console.print(f"  result_sha256 {output.result_sha256}", markup=False)
    console.print(f"  cumulative net return {m['cumulative_net_return']}, max drawdown {m['max_drawdown']:.6f}, "
                  f"legs {m['trade_counts']['legs']} (descriptive only)", markup=False)
    return EXIT_OK


def cmd_backtest_verify(args: argparse.Namespace, settings: Settings) -> int:
    rep = verify_run(args.run_dir, code_state=backtest_code_state())
    if args.json:
        console.print_json(json.dumps(rep.to_dict()))
    else:
        console.print(f"{NOT_EVIDENCE} | backtest-verify {args.run_dir}: {rep.status}", markup=False)
        for name, c in rep.checks.items():
            state = "PASS" if c["ok"] is True else "FAIL" if c["ok"] is False else "NOTE"
            console.print(f"  {state} {name}: {c['detail']}", markup=False)
    return EXIT_OK if rep.ok else EXIT_ERROR


def cmd_backtest_segment(args: argparse.Namespace, settings: Settings) -> int:
    """Upper-bound segment (bar.end_utc <= last_day + 3 days) of two verified bar directories (BT-3c)."""
    out = args.out or settings.processed_dir / "backtest_segments-fixture"
    try:
        exp = export_segment(args.daily, args.hourly, _utc_day(args.last_day), out)
    except (SegmentError, DataIntegrityError, OSError, ValueError) as exc:
        console.print(f"{NOT_EVIDENCE} | backtest-segment refused: {type(exc).__name__}: {exc}", markup=False)
        return EXIT_ERROR
    console.print(f"{NOT_EVIDENCE} | backtest-segment {exp.status}: {exp.dir}", markup=False)
    console.print(f"  segment_content_sha256 {exp.plan.content_sha256}", markup=False)
    console.print(f"  segment_manifest_sha256 {exp.plan.manifest_sha256}", markup=False)
    return EXIT_OK


def cmd_backtest_report(args: argparse.Namespace, settings: Settings) -> int:
    """Metrics and benchmarks B1-B4 of a verified run, into a new report directory (BT-2b-3)."""
    out = args.out or settings.processed_dir / "backtest_reports-fixture"
    console.print(f"{NOT_EVIDENCE} | backtest-report {args.run_dir} -> {out} (descriptive only, no p-values)",
                  markup=False)
    try:
        rep = build_report(args.run_dir, out, seed=args.seed, draws=args.b1_draws, code_state=backtest_code_state(),
                           now=datetime.now(UTC))
    except (ReportError, RunError, DataIntegrityError, AccountingError, OSError, ValueError) as exc:
        console.print(f"backtest-report refused: {type(exc).__name__}: {exc}", markup=False)
        return EXIT_ERROR
    b = rep.body["benchmarks"]
    console.print(f"saved {rep.dir}", markup=False)
    console.print(f"  report_sha256 {rep.report_sha256}", markup=False)
    console.print(f"  benchmarks: {b['status']}" + ("" if b["status"] == "compared" else f" ({'; '.join(b['reasons'])})"),
                  markup=False)
    return EXIT_OK


def cmd_backtest_report_verify(args: argparse.Namespace, settings: Settings) -> int:
    rep = check_report(args.report_dir, args.run_dir, code_state=backtest_code_state())
    if args.json:
        console.print_json(json.dumps(rep.to_dict()))
    else:
        console.print(f"{NOT_EVIDENCE} | backtest-report-verify {args.report_dir}: {'OK' if rep.ok else 'FAILED'}",
                      markup=False)
        for name, c in rep.checks.items():
            console.print(f"  {'PASS' if c['ok'] else 'FAIL'} {name}: {c['detail']}", markup=False)
    return EXIT_OK if rep.ok else EXIT_ERROR


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

    r = sub.add_parser("record", help="record public market data to data/raw (read-only)")
    r.add_argument("--provider", choices=["polymarket", "upbit"], default="polymarket")
    r.add_argument("--source", choices=["polymarket", "live", "fixture"], default=None,
                   help="polymarket: default MONEYLAB_RECORDER_SOURCE or polymarket; upbit: live (default) | fixture")
    r.add_argument("--condition-id", action="append", help="Polymarket market condition id (repeatable)")
    r.add_argument("--market", action="append", help="Upbit pair code, e.g. KRW-BTC (repeatable)")
    r.add_argument("--orderbook-units", type=int, default=None, help="Upbit orderbook units: 1, 5, 15 or 30")
    r.add_argument("--max-events", type=int, default=None, help="Upbit: stop after N orderbook+trade messages")
    r.add_argument("--ping-interval", type=float, default=60.0, help="Upbit: seconds between PING text keep-alives")
    r.add_argument("--fixture", type=Path, default=None,
                   help="fixture for --source fixture (Polymarket timeline JSON / Upbit scripted session JSON)")
    r.add_argument("--out", type=Path, default=None, help="dataset root directory")
    r.add_argument("--interval", type=float, default=None, help="seconds between polls")
    r.add_argument("--max-polls", type=int, default=None)
    r.add_argument("--duration", type=float, default=None, help="stop after N seconds")
    r.add_argument("--rebate-rate", type=float, default=None,
                   help="maker rebate share for this market (not served by the CLOB)")
    r.add_argument("--status-interval", type=float, default=300.0, help="Upbit: heartbeat seconds")
    r.add_argument("--disk-check-interval", type=float, default=600.0, help="Upbit: free-space check seconds")
    r.add_argument("--min-free-gb", type=float, default=5.0, help="Upbit: stop gracefully below this free space")
    r.add_argument("--no-clock-monitor", action="store_true", help="Upbit live: do not log the clock offset")
    r.add_argument("--clock-interval", type=float, default=120.0, help="Upbit live: seconds between clock checks")
    r.add_argument("--clock-server", default="time.windows.com", help="Upbit live: NTP server for w32tm")
    r.add_argument("--stop-on-clock-unstable", action="store_true",
                   help="Upbit live: stop gracefully when clock quality becomes CLOCK_UNSTABLE")
    r.set_defaults(func=cmd_record)

    cm = sub.add_parser("clock-monitor", help="read-only local clock offset log (w32tm /stripchart)")
    cm.add_argument("--out", type=Path, default=Path("data/raw/clock/clock_monitor.jsonl"))
    cm.add_argument("--duration", type=float, default=1800.0)
    cm.add_argument("--interval", type=float, default=120.0)
    cm.add_argument("--samples", type=int, default=3)
    cm.add_argument("--server", default="time.windows.com")
    cm.set_defaults(func=cmd_clock_monitor)

    v = sub.add_parser("record-verify", help="integrity check of a recorded dataset (offline)")
    v.add_argument("dataset", type=Path, help="dataset directory (.../recordings/<condition_id>)")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=cmd_record_verify)

    c = sub.add_parser("replay-check", help="Upbit recording: compare raw messages with their replay (offline)")
    c.add_argument("dataset", type=Path, help="dataset directory (.../upbit/recordings/<market>)")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_replay_check)

    cp = sub.add_parser("candles-pull", help="v0.6: public Upbit day/60-minute candles to data/raw (read-only)")
    cp.add_argument("--interval", choices=sorted(CANDLE_INTERVALS), required=True)
    cp.add_argument("--market", default="KRW-BTC", help="Upbit pair code (default KRW-BTC)")
    cp.add_argument("--last", type=int, default=None,
                    help="the N most recent buckets, the in-progress one included (it is dropped as incomplete)")
    cp.add_argument("--start", default=None, help="UTC bucket boundary, e.g. 2026-10-01T00:00:00Z (with --end)")
    cp.add_argument("--end", default=None, help="exclusive UTC bucket boundary (with --start)")
    cp.add_argument("--page-count", type=int, default=None,
                    help=f"rows per request, 1..{CANDLE_MAX_COUNT} (default: buckets in range, capped)")
    cp.add_argument("--max-pages", type=int, default=None, help="hard cap on page requests (default: pages needed + 1)")
    cp.add_argument("--source", choices=["live", "fixture"], default="live")
    cp.add_argument("--fixture", type=Path, default=None, help="synthetic candle fixture for --source fixture")
    cp.add_argument("--out", type=Path, default=None,
                    help="pull root (default data/raw/upbit/candles_v06, fixture: .../candles_v06-fixture)")
    cp.add_argument("--dry-run", action="store_true", help="print the request plan; no request, no files")
    cp.set_defaults(func=cmd_candles_pull)

    cv = sub.add_parser("candles-verify", help="v0.6: re-hash and replay a stored candle pull (offline)")
    cv.add_argument("pull_dir", type=Path, help="pull directory (.../candles_v06/<interval>_<market>_<stamp>)")
    cv.add_argument("--json", action="store_true")
    cv.set_defaults(func=cmd_candles_verify)

    vs = sub.add_parser("research-v06-sim", help="v0.6 DRAFT rules on SYNTHETIC paths (Monte Carlo, offline)")
    vs.add_argument("--scenario", action="append", help="scenario name (repeatable) or 'all'")
    vs.add_argument("--list", action="store_true", help="list scenarios")
    vs.add_argument("--reps", type=int, default=20)
    vs.add_argument("--bootstrap", type=int, default=199)
    vs.add_argument("--draws", type=int, default=99, help="B1 placements per test")
    vs.add_argument("--workers", type=int, default=1)
    vs.add_argument("--seed", type=int, default=20261012)
    vs.add_argument("--truth-years", type=int, default=400, help="length of the long path for the scenario truth")
    vs.add_argument("--out", type=Path, default=None, help="default data/processed/research_v06_sim/<stamp>")
    vs.set_defaults(func=cmd_research_v06_sim)

    be = sub.add_parser("bars-export", help="backtest: stored FIXTURE candle pull -> verified bar files (offline)")
    be.add_argument("pull_dir", type=Path, help="candle pull directory (fixture provenance only)")
    be.add_argument("--out", type=Path, default=None, help="default data/processed/backtest_bars-fixture")
    be.set_defaults(func=cmd_bars_export)

    bt = sub.add_parser("backtest", help="backtest: one long/cash rule on exported SYNTHETIC/fixture bars (offline)")
    bt.add_argument("--daily", type=Path, required=True, help="exported daily bar directory")
    bt.add_argument("--hourly", type=Path, required=True, help="exported hourly bar directory")
    bt.add_argument("--rule", choices=sorted(BACKTEST_RULES), required=True)
    bt.add_argument("--first-day", required=True, help="first signal day, YYYY-MM-DD (UTC)")
    bt.add_argument("--last-day", required=True, help="last signal day, YYYY-MM-DD (UTC)")
    bt.add_argument("--fee-bps", type=int, choices=[0, 5, 15, 25], default=25, help="per side, ASSUMED (default 25)")
    bt.add_argument("--fee-basis", choices=["inclusive", "on_top"], default="inclusive")
    bt.add_argument("--scenario", choices=sorted(BACKTEST_SCENARIOS), default="E0")
    bt.add_argument("--no-impact", action="store_true", help="drop the market impact assumption")
    bt.add_argument("--fill-substitution", choices=list(BACKTEST_SUBSTITUTION), default="none")
    bt.add_argument("--settings", type=Path, default=BACKTEST_SETTINGS, help="cost settings (configs/backtest_costs.toml)")
    bt.add_argument("--out", type=Path, default=None, help="default data/processed/backtest-fixture")
    bt.set_defaults(func=cmd_backtest)

    bs = sub.add_parser("backtest-segment", help="backtest: upper-bound input segment (end <= last day + 3 days) of "
                                                 "exported SYNTHETIC/fixture bars (offline)")
    bs.add_argument("--daily", type=Path, required=True, help="exported daily bar directory")
    bs.add_argument("--hourly", type=Path, required=True, help="exported hourly bar directory")
    bs.add_argument("--last-day", required=True, help="last signal day of the runs, YYYY-MM-DD (UTC)")
    bs.add_argument("--out", type=Path, default=None, help="default data/processed/backtest_segments-fixture")
    bs.set_defaults(func=cmd_backtest_segment)

    bv = sub.add_parser("backtest-verify", help="backtest: re-check and recompute a run directory (writes nothing)")
    bv.add_argument("run_dir", type=Path)
    bv.add_argument("--json", action="store_true")
    bv.set_defaults(func=cmd_backtest_verify)

    br = sub.add_parser("backtest-report", help="backtest: metrics and benchmarks B1-B4 of a verified run (offline)")
    br.add_argument("run_dir", type=Path)
    br.add_argument("--seed", type=int, required=True, help="B1 seed, 0 <= seed < 2**64 (rule bt-seed/1; no default)")
    br.add_argument("--b1-draws", type=int, default=999, help="B1 placements (default 999)")
    br.add_argument("--out", type=Path, default=None, help="default data/processed/backtest_reports-fixture")
    br.set_defaults(func=cmd_backtest_report)

    bq = sub.add_parser("backtest-report-verify", help="backtest: re-check a report against its run (writes nothing)")
    bq.add_argument("report_dir", type=Path)
    bq.add_argument("run_dir", type=Path)
    bq.add_argument("--json", action="store_true")
    bq.set_defaults(func=cmd_backtest_report_verify)

    rb = sub.add_parser("research-build", help="v0.4: raw Upbit dataset -> grid/features/labels/split (offline)")
    rb.add_argument("dataset", type=Path, help="Upbit dataset directory (.../<session>/KRW-BTC)")
    rb.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="pre-registered study config")
    rb.add_argument("--session-id", default=None, help="default: name of the dataset's parent directory")
    rb.add_argument("--out", type=Path, default=None, help="processed root (default data/processed)")
    rb.add_argument("--dry-run", action="store_true", help="pipeline check; results are DRY_RUN/INSUFFICIENT_EVIDENCE")
    rb.add_argument("--embargo-seconds", type=float, default=None, help="dry run only: shorter embargo")
    rb.add_argument("--allow-fixture", action="store_true", help="accept fixture data (results are NOT_EVIDENCE)")
    rb.set_defaults(func=cmd_research_build)

    rs = sub.add_parser("research-stats", help="v0.4: train/validation statistics and leaderboard (test locked)")
    rs.add_argument("run_dir", type=Path)
    rs.add_argument("--config", type=Path, default=None, help="default: the config the run was built with")
    rs.add_argument("--top", type=int, default=20)
    rs.set_defaults(func=cmd_research_stats)

    rf = sub.add_parser("research-final", help="v0.4: evaluate the locked test split exactly once")
    rf.add_argument("run_dir", type=Path)
    rf.add_argument("--config", type=Path, default=None)
    rf.add_argument("--top", type=int, default=20)
    rf.set_defaults(func=cmd_research_final)
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
