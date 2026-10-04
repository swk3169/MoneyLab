from __future__ import annotations

import json

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from moneylab.core.diagnostics import DiagnosticReport, EndpointCheck
from moneylab.core.http import HttpDiagnostics
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
