from __future__ import annotations

import json

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from moneylab.analytics import metrics
from moneylab.core.diagnostics import DiagnosticReport, EndpointCheck
from moneylab.core.http import HttpDiagnostics
from moneylab.domain.orderbook import OrderBook
from moneylab.paper.runner import SimulationResult
from moneylab.scanner.market_scanner import ScanResult

console = Console()
WIDE_LAYOUT_MIN = 130


def fmt_price(p: float | None) -> str:
    return "-" if p is None else f"{p:.3f}"


def fmt_money(v: float | None) -> str:
    if v is None:
        return "-"
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= div:
            return f"${v / div:,.2f}{unit}"
    return f"${v:,.0f}"


def render_scan(result: ScanResult) -> None:
    if result.error is not None:
        render_provider_error(result)
        return
    # Narrow terminals: drop secondary columns instead of squeezing the market name away.
    wide = console.width >= WIDE_LAYOUT_MIN
    table = Table(
        title=f"{result.provider} - {len(result.candidates)} candidates "
        f"(fetched {result.fetched}) @ {result.scanned_at:%Y-%m-%d %H:%M UTC}",
        box=box.SQUARE if wide else box.SIMPLE_HEAD,
        padding=(0, 1) if wide else (0, 0, 0, 1),
    )
    if wide:
        table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Market", overflow="fold", min_width=22, max_width=60)
    table.add_column("YES", justify="right", style="green", no_wrap=True)
    table.add_column("NO", justify="right", style="red", no_wrap=True)
    if wide:
        table.add_column("Spread", justify="right", no_wrap=True)
    table.add_column("Vol 24h", justify="right", no_wrap=True)
    if wide:
        table.add_column("Volume", justify="right", no_wrap=True)
    table.add_column("Liq.", justify="right", no_wrap=True)
    table.add_column("Ends", no_wrap=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    if wide:
        table.add_column("Flags", style="yellow", overflow="fold", min_width=8)
    for i, cand in enumerate(result.candidates, 1):
        m = cand.market
        yes, no = m.yes_price, m.no_price
        if yes is None and m.outcomes:  # non yes/no market: show first two outcomes
            yes = m.outcomes[0].price
            no = m.outcomes[1].price if len(m.outcomes) > 1 else None
        ends = "-" if m.end_date is None else f"{m.end_date:%Y-%m-%d}" if wide else f"{m.end_date:%y-%m-%d}"
        cells = [escape(m.question), fmt_price(yes), fmt_price(no)]
        if wide:
            cells = [str(i), *cells, fmt_price(m.spread)]
        cells.append(fmt_money(m.volume_24h))
        if wide:
            cells.append(fmt_money(m.volume))
        cells += [fmt_money(m.liquidity), ends, m.market_id]
        if wide:
            cells.append(escape(" ".join(cand.flags)))
        table.add_row(*cells)
    console.print(table)
    if not wide:
        console.print("[dim]Narrow terminal: spread/volume/flags hidden (need >= "
                      f"{WIDE_LAYOUT_MIN} columns).[/dim]")


def render_http_diagnostics(diag: HttpDiagnostics) -> None:
    lines = [
        f"[bold]{escape(diag.method)} {escape(diag.url)}[/bold]",
        f"Status : {diag.status_code} {escape(diag.reason or '')}  ({diag.elapsed_ms} ms)",
    ]
    if diag.error:
        lines.append(f"Error  : {escape(diag.error)}")
    lines.append("Headers:")
    lines += [f"  {escape(k)}: {escape(v)}" for k, v in diag.headers.items()]
    lines.append("Body (excerpt):")
    lines.append("  " + escape(diag.body_excerpt.strip() or "<empty>").replace("\n", "\n  "))
    console.print(Panel("\n".join(lines), title="HTTP diagnostics", border_style="red"), markup=True)


def render_provider_error(result: ScanResult) -> None:
    err = result.error
    console.print(
        Panel(
            f"{escape(str(err))}\n\nScan aborted gracefully - no data was fetched.\n"
            "Run [bold]python -m moneylab diagnose[/bold] for a full connectivity report, "
            "or [bold]python -m moneylab scan --source fixture[/bold] to work offline.",
            title=f"Provider '{result.provider}' unavailable",
            border_style="red",
        )
    )
    if err.diagnostics is not None:
        render_http_diagnostics(err.diagnostics)


def _render_check(check: EndpointCheck, title: str) -> None:
    if check.http:
        render_http_diagnostics(check.http)
    else:
        console.print(Panel(escape(f"{check.url}\n{check.network_error}"),title=title, border_style="red"))
    for o in check.observations:
        console.print(f"  - {escape(o)}")


def render_diagnostics(report: DiagnosticReport) -> None:
    console.rule(f"Connectivity diagnostics @ {report.created_at}")
    for check in report.checks:
        _render_check(check, "Target")
    if report.control:
        status = report.control.http.status_code if report.control.http else report.control.network_error
        console.print(f"\n[bold]Control endpoint[/bold] {report.control.url} -> {status}")
    if report.edge_trace:
        console.print("[bold]CDN edge trace (IP omitted):[/bold] " + escape(json.dumps(report.edge_trace)))
    console.print(Panel(escape("\n".join(f"- {o}" for o in report.observations)),title="Observations (facts)"))
    if report.hypotheses:
        console.print(
            Panel(
                escape("\n".join(f"- {h}" for h in report.hypotheses)),
                title="Possible causes (hypotheses - NOT conclusions)",
                border_style="yellow",
            )
        )


def render_book(book: OrderBook, depth_cents: float = 2.0, levels: int = 5) -> None:
    table = Table(title=f"Order book {book.token_id}", box=box.SIMPLE_HEAVY)
    table.add_column("Bid size", justify="right")
    table.add_column("Bid", justify="right", style="green")
    table.add_column("Ask", justify="right", style="red")
    table.add_column("Ask size", justify="right")
    for i in range(min(levels, max(len(book.bids), len(book.asks)))):
        b = book.bids[i] if i < len(book.bids) else None
        a = book.asks[i] if i < len(book.asks) else None
        table.add_row(
            f"{b.size:,.0f}" if b else "", fmt_price(b.price) if b else "",
            fmt_price(a.price) if a else "", f"{a.size:,.0f}" if a else "",
        )
    console.print(table)
    mid = book.mid
    micro = metrics.microprice(book.best_bid, book.best_bid_size, book.best_ask, book.best_ask_size)
    dist = depth_cents / 100
    bid_sh, bid_usd = metrics.depth_within(book.bids, mid, dist) if mid is not None else (0.0, 0.0)
    ask_sh, ask_usd = metrics.depth_within(book.asks, mid, dist) if mid is not None else (0.0, 0.0)
    ticks = metrics.spread_ticks(book.best_bid, book.best_ask, book.tick_size)
    console.print(
        f"mid {fmt_price(mid)}  microprice {fmt_price(micro)}  spread {fmt_price(book.spread)} ({ticks} ticks)  "
        f"tick {book.tick_size}  min size {book.min_order_size}\n"
        f"depth within +/-{depth_cents:g}c: bids {bid_sh:,.0f} sh (${bid_usd:,.2f})  asks {ask_sh:,.0f} sh (${ask_usd:,.2f})  "
        f"imbalance {fmt_price(metrics.book_imbalance(bid_sh, ask_sh))}"
    )


def _num(v: float | None, pct: bool = False) -> str:
    if v is None:
        return "-"
    if v == float("inf"):
        return "inf"
    return f"{v:.2%}" if pct else f"{v:,.4f}"


def render_simulation(result: SimulationResult, description: str = "") -> None:
    title = f"Simulation: {result.strategy}" + ("  [SYNTHETIC DATA]" if result.synthetic else "")
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    table.add_column("Component")
    table.add_column("USDC", justify="right")
    for name, value in result.breakdown.rows():
        style = "bold" if name in ("gross_trading_pnl", "net_trading_pnl_after_cost", "all_in_realized_pnl") else None
        if name.startswith("estimated") or name.startswith("all_in_estimated"):
            style = "dim"
        table.add_row(name, f"{round(value, 9) + 0.0:,.4f}", style=style)
    console.print(table)
    if description:
        console.print(f"[dim]{escape(description)}[/dim]")
    b = result.breakdown
    console.print(
        f"fills: maker {result.maker_fills}, taker {result.taker_fills}  rejected orders {len(result.rejections)}\n"
        f"trades {len(result.trade_pnls)} (open, marked at final mid: {result.open_trades_marked})  "
        f"win rate {_num(result.win_rate, True)}  profit factor {_num(result.profit_factor)}\n"
        f"max drawdown {_num(result.max_drawdown, True)} ({_num(result.max_drawdown_abs)} USDC)  "
        f"costs: fees {_num(b.trading_costs + 0.0)}, slippage {_num(b.slippage + 0.0)}\n"
        f"accounting identity {'OK' if b.identity_holds else 'MISMATCH'}  final positions {result.final_positions}"
    )
    if result.kill_switch_reasons:
        console.print(f"[red]Kill switch tripped at {result.kill_switch_tripped_at}: {escape('; '.join(result.kill_switch_reasons))}[/red]")
    color = {"REJECT": "red", "INSUFFICIENT_EVIDENCE": "yellow", "CANDIDATE": "green"}[result.verdict.status]
    console.print(f"[{color}]Adoption: {result.verdict.status}[/{color}] - {escape('; '.join(result.verdict.reasons))}")
    console.print("[dim]Estimated incentives are model outputs and are excluded from realized PnL and adoption.[/dim]")


def render_recorder_report(report) -> None:
    """RecorderReport (providers.polymarket.recorder) - duck-typed to keep display provider-free."""
    status = str(report.status)
    color = "green" if report.ok else "red"
    table = Table(title=f"Recorder: {report.recorder}", box=box.SIMPLE_HEAVY)
    table.add_column("Item")
    table.add_column("Value", justify="right")
    for name in ("polls", "books_written", "unchanged_written", "duplicates_skipped", "errors", "rate_limited"):
        table.add_row(name, str(getattr(report, name)))
    console.print(table)
    console.print(f"[{color}]status: {escape(status)}[/{color}]")
    for cid, path in report.datasets.items():
        console.print(f"[dim]{escape(cid)} -> {escape(str(path))}[/dim]")
    for w in report.warnings:
        console.print(f"[yellow]warning:[/yellow] {escape(w)}")
    if report.last_error:
        err = report.last_error
        console.print(f"[red]last error ({escape(str(err.get('category')))}):[/red] {escape(str(err.get('message')))}")
        diag = err.get("diagnostics") or {}
        if diag.get("body_excerpt"):
            console.print(Panel(escape(str(diag["body_excerpt"])[:800]), title="response body (redacted excerpt)"))
        if diag.get("note"):
            console.print(f"[yellow]{escape(diag['note'])}[/yellow]")


def render_integrity(report) -> None:
    """IntegrityReport (providers.polymarket.recorder) - duck-typed."""
    color = "green" if report.ok else "red"
    console.print(f"[{color}]Integrity {'OK' if report.ok else 'FAILED'}[/{color}]  {escape(str(report.path))}")
    console.print(f"status {report.status}  synthetic {report.synthetic}  counts {report.counts}")
    if report.first_ts is not None:
        console.print(f"span {report.first_ts:.0f} -> {report.last_ts:.0f} ({report.last_ts - report.first_ts:,.0f}s)")
    for e in report.errors:
        console.print(f"[red]error:[/red] {escape(e)}")
    for w in report.warnings[:30]:
        console.print(f"[yellow]warning:[/yellow] {escape(w)}")
    if len(report.warnings) > 30:
        console.print(f"[dim]... {len(report.warnings) - 30} more warnings[/dim]")


def render_stream_recorder_report(report) -> None:
    """Streaming recorder report (e.g. providers.upbit UpbitRecorderReport) - duck-typed."""
    color = "green" if report.ok else "red"
    table = Table(title=f"Recorder: {report.recorder}", box=box.SIMPLE_HEAVY)
    table.add_column("Item")
    table.add_column("Value", justify="right")
    for name, value in report.counters().items():
        table.add_row(name, str(value))
    console.print(table)
    console.print(f"[{color}]status: {escape(str(report.status))}[/{color}]  termination reason: "
                  f"{escape(str(getattr(report, 'termination_reason', None)))}")
    free0, free1 = getattr(report, "disk_free_start", None), getattr(report, "disk_free_end", None)
    if free0 is not None or free1 is not None:
        console.print(f"disk free start {(free0 or 0) / 1e9:.2f} GB  end {(free1 or 0) / 1e9:.2f} GB")
    clock = getattr(report, "clock", None)
    if clock:
        render_clock_summary(clock)
    for key, path in report.datasets.items():
        console.print(f"[dim]{escape(key)} -> {escape(str(path))}[/dim]")
    for w in report.warnings[:30]:
        console.print(f"[yellow]warning:[/yellow] {escape(w)}")
    if report.last_error:
        err = report.last_error
        console.print(f"[red]last error ({escape(str(err.get('category')))}):[/red] {escape(str(err.get('message')))}")
        diag = err.get("diagnostics") or {}
        if diag.get("body_excerpt"):
            console.print(Panel(escape(str(diag["body_excerpt"])[:800]), title="response body (redacted excerpt)"))
        if diag.get("note"):
            console.print(f"[yellow]{escape(diag['note'])}[/yellow]")


def render_clock_summary(c: dict) -> None:
    def ms(v):
        return "-" if v is None else f"{v:.1f}ms"
    drift = c.get("clock_drift_ppm")
    color = {"OK": "green", "WARNING": "yellow"}.get(c.get("clock_quality_status"), "red")
    console.print(f"clock [{color}]{c.get('clock_quality_status')}[/{color}]  start {ms(c.get('clock_offset_start_ms'))} "
                  f"end {ms(c.get('clock_offset_end_ms'))} min {ms(c.get('clock_offset_min_ms'))} "
                  f"max {ms(c.get('clock_offset_max_ms'))} median {ms(c.get('clock_offset_median_ms'))}  "
                  f"measurements {c.get('clock_measurements_ok')}/{c.get('clock_measurements')}  "
                  f"drift {'-' if drift is None else f'{drift:.1f} ppm'}  [dim]({c.get('clock_sign_convention')})[/dim]")


def _utc(ts: float | None) -> str:
    if ts is None:
        return "-"
    from datetime import UTC, datetime

    return datetime.fromtimestamp(ts, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def render_replay_check(report) -> None:
    """Recorder -> replay comparison (providers.upbit ReplayCheckReport) - duck-typed."""
    color = "green" if report.ok else "red"
    label = "SYNTHETIC/FIXTURE" if report.synthetic else "REAL"
    console.print(f"[{color}]Replay check {'OK' if report.ok else 'FAILED'}[/{color}]  [bold]{label}[/bold] "
                  f"provenance={report.provenance} market={report.market}  {escape(str(report.path))}")
    console.print(f"counts {report.counts}")
    first_ex = None if report.first_exchange_ms is None else report.first_exchange_ms / 1000
    last_ex = None if report.last_exchange_ms is None else report.last_exchange_ms / 1000
    console.print(f"exchange_timestamp {_utc(first_ex)} -> {_utc(last_ex)}")
    console.print(f"received_timestamp {_utc(report.first_received)} -> {_utc(report.last_received)}")
    for kind, st in report.latency_ms.items():
        if st:
            console.print(f"receive latency {kind:9s} n={st['n']} mean={st['mean']:.1f}ms median={st['median']:.1f}ms "
                          f"p95={st['p95']:.1f}ms min={st['min']:.1f}ms max={st['max']:.1f}ms")
    console.print(f"orderbook units per message {report.units_histogram}  stream types {report.stream_types}")
    console.print(f"replay {report.replay_stats}  reader {report.reader_stats}")
    for key, ex in report.examples.items():
        console.print(f"[dim]{key}: {escape(json.dumps(ex, default=str))}[/dim]")
    console.print(f"dataset size {report.size_bytes:,} bytes")
    for m in report.mismatches[:30]:
        console.print(f"[red]mismatch:[/red] {escape(m)}")


# --- v0.4 research --------------------------------------------------------------------------

def _f(v, digits: int = 2) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "-"
    return f"{v:.{digits}f}" if isinstance(v, float) else str(v)


def _evidence_banner(evidence: str, kind: str = "") -> None:
    color = "green" if evidence == "EVIDENCE" else "yellow"
    console.print(Panel(f"[bold {color}]{escape(evidence)}[/bold {color}]  {escape(kind)}\n"
                        "Decisions are capped at RESEARCH_MORE unless evidence is EVIDENCE, at least the "
                        "pre-registered number of sessions exist and the test split passed.",
                        title="Research evidence", box=box.ROUNDED))


def render_research_build(m: dict) -> None:
    _evidence_banner(m["evidence"], m["kind"])
    c, s, x = m["collection"], m["split"], m["exclusions"]
    console.print(f"run [bold]{escape(m['run_id'])}[/bold]  session {escape(m['session_id'])}  market {m['market']}  "
                  f"provenance [bold]{m['provenance']}[/bold]")
    console.print(f"collection {c['start_iso']} -> {c['end_iso']} ({c['duration_seconds']:.0f}s)")
    console.print(f"hashes: prereg {str(m['preregistration_sha256'])[:12]}  config {str(m['config_sha256'])[:12]}  "
                  f"raw manifest {str(m['raw_manifest_sha256'])[:12]}  dataset {str(m['dataset_sha256'])[:12]}  "
                  f"git {str(m['git'].get('commit'))[:12]}{' (dirty)' if m['git'].get('dirty') else ''}")
    if m.get("config_overrides"):
        console.print(f"[yellow]config overrides (dry run only): {m['config_overrides']}[/yellow]")
    console.print(f"grid rows {x['grid_rows']}  clean {x['clean_rows']}  excluded {x['excluded_rows']}  "
                  f"by reason {x['by_reason']}")
    console.print(f"embargo rows {x['embargo_rows']}  purged label values {x['label_values_purged']}  "
                  f"feature values cut at segment start {x['feature_values_cut_at_segment_start']}")
    console.print(f"split rows {s['rows']}  train_end {_utc(s['train_end'])}  validation "
                  f"{_utc(s['validation_start'])} -> {_utc(s['validation_end'])}  test {_utc(s['test_start'])} -> "
                  f"{_utc(s['end'])} [dim](test LOCKED)[/dim]")
    console.print(f"fee scenarios {m['fee_scenarios_bps']} bp (decision {m['decision_fee_bps']} bp, "
                  f"account fee confirmed: {m['account_fee_confirmed']})  delays {m['delay_scenarios_ms']} ms")


def render_leaderboard(rows: list, evidence: str, kind: str = "", top: int = 20) -> None:
    _evidence_banner(evidence, kind)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["decision"]] = counts.get(r["decision"], 0) + 1
    console.print(f"{len(rows)} feature x horizon tests  decisions {counts}")
    ranked = sorted(rows, key=lambda r: -abs(r["Spearman_IC"]) if r["Spearman_IC"] == r["Spearman_IC"] else 0)
    t = Table(box=box.SIMPLE, title=f"Top {min(top, len(rows))} by |validation Spearman IC|")
    for col in ("feature", "h", "N", "miss", "IC", "CI", "BH_q", "TB bp", "acc", "gross", "cost", "net",
                "net@fees", "net@delays", "val", "test", "decision"):
        t.add_column(col)
    for r in ranked[:top]:
        fs = "/".join(_f(v, 1) for v in r["fee_sensitivity"].values())
        ds = "/".join(_f(v, 1) for v in r["delay_sensitivity"].values())
        t.add_row(r["feature"], str(r["horizon"]), str(r["N"]), _f(r["missing_rate"]), _f(r["Spearman_IC"], 3),
                  f"[{_f(r['IC_CI_low'], 3)}, {_f(r['IC_CI_high'], 3)}]", _f(r["BH_q"], 3), _f(r["top_bottom_bps"]),
                  _f(r["directional_accuracy"]), _f(r["gross_edge_bps"]), _f(r["estimated_cost_bps"]),
                  _f(r["net_edge_bps"]), fs, ds, r["validation_result"], r["test_result"], r["decision"])
    console.print(t)
