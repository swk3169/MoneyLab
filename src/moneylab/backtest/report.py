"""Backtest reports from verified run directories (BT-2b-3; docs/backtest_bt2b3_metrics.md).

`build_report(run_dir, out_root, seed=..., draws=..., code_state=..., now=...)`
  1. refuses an output root that does not end with "-fixture" or lies inside the run directory, and an
     existing final directory <out_root>/<run_dir_name>-report-<UTC stamp>
  2. hashes every file of the run directory (it is only read, never opened for writing)
  3. requires backtest.run.verify_run to be OK (files, inputs, settings, code, reproducibility, ...)
  4. recomputes the run and requires result_sha256 and the stored daily / trade rows to match it
  5. computes the metrics (backtest.performance) and, when the ledger returns are aligned with the
     position-series returns, the benchmarks B1-B4 (backtest.benchmarks); otherwise not_aligned + reasons
  6. writes report.json, report.md, report_meta.json and SHA256SUMS.txt into a temporary directory,
     re-checks the written hashes and the run directory hashes, then renames it into place (never over
     an existing directory). On failure only the files written by this call are removed.

report.json is deterministic: json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False,
allow_nan=False), UTF-8, LF, one trailing newline; it holds no time, no code state, no Python version.
report.md is generated from report.json only. report_meta.json holds created_utc, code_state, the Python
version and the SHA-256 of report.json. SHA256SUMS.txt lists the three files by name.

`check_report(report_dir, run_dir, code_state=...)` writes nothing and checks the file hashes, the meta,
the schema / definition / seed versions (unknown ones are refused), the run references, the run itself
(verify_run) and that report.json and report.md are reproduced byte for byte.
All reports are SYNTHETIC / NOT_EVIDENCE and descriptive: no p-values, no verdict.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.backtest import metrics as bt_metrics
from moneylab.backtest.bars_io import load_bars
from moneylab.backtest.benchmarks import (
    B1_QUANTILES,
    BT_SEED_ALGORITHM,
    BenchmarkError,
    alignment,
    bt_seed,
    bt_seed_payload,
    compare,
    leg_cost_logs,
    ledger_positions,
    market_log_returns,
)
from moneylab.backtest.data import DataIntegrityError
from moneylab.backtest.performance import (
    ANNUALIZATION_DAYS,
    METRICS_VERSION,
    RISK_FREE_RATE,
    MetricError,
    check_positive,
    exposure,
    series_metrics,
    turnover,
    value,
)
from moneylab.backtest.portfolio import BacktestResult, simulate
from moneylab.backtest.run import FIXTURE_ROOT_SUFFIX, SUMS_FILE, config_from_dict, utc_stamp, verify_run
from moneylab.domain.bars import NOT_EVIDENCE
from moneylab.storage.atomic import atomic_write_bytes, sha256_file

REPORT_SCHEMA = "moneylab.backtest.report/1"
REPORT_FILES = ("report.json", "report.md", "report_meta.json")
KNOWN_SCHEMAS = (REPORT_SCHEMA,)
KNOWN_METRICS_VERSIONS = (METRICS_VERSION,)
KNOWN_SEED_ALGORITHMS = (BT_SEED_ALGORITHM,)
TOTAL_RETURN_TOLERANCE = 1e-12  # relative: exp(sum r) - 1 against the Decimal ledger
MDD_NOTE = ("mdd (P) samples wealth before each day's trade and after the final exit (research/v06/procedures."
            "max_drawdown); mdd_ledger_after_trade (BT-1 backtest.metrics.max_drawdown) samples equity after each "
            "trade. They coincide on days without trades and generally differ on trade days; comparisons use P.")
FORMULAS = {
    "returns": "r_i = ln(E_before(i+1) / E_before(i)), the last day ends after the virtual exit; net of all costs",
    "total_return": "exp(sum r) - 1 (checked against final / initial equity of the ledger)",
    "cagr": "exp(sum r * 365 / T_d) - 1, T_d = calendar days between the first and last valuation",
    "volatility": "sample sd(r) * sqrt(365)",
    "sharpe_log": "mean(r) / sample sd(r) * sqrt(365), risk-free rate 0 (primary)",
    "sharpe_simple": "the same on R = exp(r) - 1 (secondary)",
    "sortino": "mean(r) / sqrt(sum(min(r, 0)^2) / n) * sqrt(365)",
    "mdd": "1 - exp(-max(peak - level)), level = running sum of r from 0 (P)",
    "mdd_ledger_after_trade": "largest fall of [initial cash, equity after each valuation] (BT-1)",
    "calmar": "cagr / mdd (P)",
    "exposure": "sum(p) / n",
    "turnover": "sum(quantity * ref_price) / mean(daily equity after trades); * 365 / T_d annualized (primary)",
    "turnover_legs": "sum(quantity * ref_price / equity before the leg) * 365 / T_d (secondary)",
}


class ReportError(ValueError):
    """The report cannot be made (run does not verify, bad output path, inconsistent recomputation)."""


@dataclass(frozen=True)
class ReportOutput:
    dir: Path
    report_sha256: str
    body: dict[str, Any]


@dataclass
class ReportVerifyReport:
    report_dir: str
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.checks[name] = {"ok": ok, "detail": detail}

    @property
    def ok(self) -> bool:
        return all(self.checks.get(k, {}).get("ok") is True for k in REPORT_CHECKS)

    def to_dict(self) -> dict[str, Any]:
        return {"evidence": NOT_EVIDENCE, "report_dir": self.report_dir, "ok": self.ok, "checks": self.checks}


REPORT_CHECKS = ("files", "meta", "versions", "run_refs", "run_verify", "content")


def report_bytes(body: dict[str, Any]) -> bytes:
    return (json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            + "\n").encode("utf-8")


def _meta_bytes(meta: dict[str, Any]) -> bytes:
    return (json.dumps(meta, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _tree_hashes(d: Path) -> dict[str, str]:
    return {p.relative_to(d).as_posix(): sha256_file(p) for p in sorted(d.rglob("*")) if p.is_file()}


def _read_manifest(run_dir: Path) -> dict[str, Any]:
    try:
        return json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReportError(f"cannot read {run_dir / 'manifest.json'}: {exc}") from exc


def _jsonl_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def recompute_run(run_dir: Path, manifest: dict[str, Any]) -> BacktestResult:
    """Re-run the recorded config on the recorded inputs; result and stored rows must match."""
    cfg = config_from_dict(manifest["config"])
    day = load_bars(Path(manifest["inputs"]["day"]["path"]))
    hour = load_bars(Path(manifest["inputs"]["hour"]["path"]))
    res = simulate(day, hour, cfg)
    if res.sha256() != manifest["result_sha256"]:
        raise ReportError("recomputed result_sha256 differs from the manifest")
    if sha256_file(run_dir / "result.json") != manifest["result_sha256"]:
        raise ReportError("result.json does not hash to the manifest result_sha256")
    body = res.to_dict()
    if _jsonl_rows(run_dir / "daily.jsonl") != body["daily"]:
        raise ReportError("stored daily.jsonl rows differ from the recomputed ledger")
    if _jsonl_rows(run_dir / "trades.jsonl") != body["trades"]:
        raise ReportError("stored trades.jsonl rows differ from the recomputed ledger")
    return res


def compute_body(run_dir: Path, manifest: dict[str, Any], *, seed: int, draws: int) -> dict[str, Any]:
    run_dir = Path(run_dir)
    res = recompute_run(run_dir, manifest)
    led, cfg = res.ledger, res.config
    assert led is not None
    if len(led.daily) < 2:
        raise ReportError("fewer than 2 daily valuations: no return to describe")
    check_positive([float(led.initial_cash)] + [float(d.equity_before_trade) for d in led.daily] +
                   [float(d.equity) for d in led.daily], "equity")
    r = bt_metrics.daily_log_returns(led)
    first, last = led.daily[0].ref_time, led.daily[-1].ref_time
    t_days = (last - first).total_seconds() / 86400
    total = bt_metrics.cumulative_net_return(led)
    from_log = math.expm1(sum(r))
    if abs(from_log - float(total)) > TOTAL_RETURN_TOLERANCE * max(1.0, abs(float(total))):
        raise ReportError(f"exp(sum r) - 1 = {from_log!r} differs from the ledger total return {total}")
    positions = ledger_positions(led)
    legs = led.trades
    notionals = [float(t.quantity * t.ref_price) for t in legs]
    before_leg = [float(t.cash_before + t.qty_before * t.ref_price) for t in legs]
    perf = series_metrics(r, t_days) | {
        "exposure": exposure(positions),
        "turnover": turnover(notionals, before_leg, [float(d.equity) for d in led.daily], t_days),
        "mdd_ledger_after_trade": value(bt_metrics.max_drawdown(led)),
        "total_return_ledger": str(total),
        "initial_cash": str(led.initial_cash),
        "final_equity": str(led.daily[-1].equity),
        "t_days": t_days,
        "irregular_spacing": len(r) != round(t_days) or any(
            (b.ref_time - a.ref_time).total_seconds() != 86400 for a, b in zip(led.daily, led.daily[1:])),
        "legs": len(legs),
        "no_trades": not legs,
    }
    labels = ["B1", cfg.rule, cfg.scenario]
    align = alignment(led, r, cfg.costs)
    c_b, c_s = leg_cost_logs(cfg.costs)
    if align["aligned"]:
        bench = compare(r, market_log_returns(led), positions, c_b, c_s, t_days, draws=draws, seed=seed,
                        labels=labels)
    else:
        bench = {"status": "not_aligned", "reasons": list(align["reasons"])}
    return {
        "schema": REPORT_SCHEMA,
        "evidence": NOT_EVIDENCE,
        "labels": [*manifest["labels"], "DESCRIPTIVE_ONLY"],
        "run": {"run_dir_name": manifest["run_dir_name"], "manifest_sha256": sha256_file(run_dir / "manifest.json"),
                "result_sha256": manifest["result_sha256"], "inputs": manifest["inputs"],
                "settings": manifest["settings"], "config": manifest["config"]},
        "metrics_definition": {"version": METRICS_VERSION, "annualization_days": ANNUALIZATION_DAYS,
                               "risk_free_rate": RISK_FREE_RATE, "formulas": FORMULAS, "mdd_note": MDD_NOTE},
        "seed": {"algorithm": BT_SEED_ALGORITHM, "seed": str(seed), "labels": labels,
                 "derived_seed": str(bt_seed(seed, *labels)), "b1_draws": draws,
                 "b1_quantiles": list(B1_QUANTILES)},
        "cost_logs": {"buy": c_b, "sell": c_s},
        "metrics": perf,
        "alignment": align,
        "benchmarks": bench,
        "p_values": "not computed",
    }


# --- markdown -------------------------------------------------------------------------------------------

def _fmt(m: Any) -> str:
    if isinstance(m, dict) and "value" in m:
        if m["value"] is None:
            return f"n/a ({m['reason']})"
        return f"{m['value']:.6g}"
    return str(m)


_ROWS = ("total_return", "cagr", "volatility", "sharpe_log", "sharpe_simple", "sortino", "mdd", "calmar")


def report_markdown(body: dict[str, Any]) -> str:
    m, run, seed = body["metrics"], body["run"], body["seed"]
    lines = [
        f"# Backtest report: {run['run_dir_name']}",
        "",
        f"**{body['evidence']}** | labels: {', '.join(body['labels'])}",
        "",
        "Descriptive statistics only. Not a statistical test, no p-values, no verdict.",
        "",
        "## Run",
        "",
        f"- rule {run['config']['rule']}, scenario {run['config']['scenario']}, "
        f"fee {run['config']['costs']['buy_fee_bps']} bp ({run['config']['costs']['fee_basis']}), "
        f"fill substitution {run['config']['fill_substitution']}",
        f"- result_sha256 `{run['result_sha256']}`",
        f"- manifest sha256 `{run['manifest_sha256']}`",
        f"- metrics definition {body['metrics_definition']['version']}, annualization "
        f"{body['metrics_definition']['annualization_days']} days, risk-free rate "
        f"{body['metrics_definition']['risk_free_rate']}",
        f"- B1 seed {seed['algorithm']}: seed {seed['seed']}, labels {seed['labels']}, "
        f"derived {seed['derived_seed']}, draws {seed['b1_draws']}",
        "",
        "## Strategy metrics (net of costs)",
        "",
        "| metric | value |",
        "|---|---|",
    ]
    lines += [f"| {k} | {_fmt(m[k])} |" for k in _ROWS]
    lines += [
        f"| mdd_ledger_after_trade (BT-1) | {_fmt(m['mdd_ledger_after_trade'])} |",
        f"| exposure | {_fmt(m['exposure'])} |",
        f"| turnover (period / annualized) | {_fmt(m['turnover']['period'])} / {_fmt(m['turnover']['annualized'])} |",
        f"| turnover legs (period / annualized) | {_fmt(m['turnover']['legs_period'])} / "
        f"{_fmt(m['turnover']['legs_annualized'])} |",
        f"| legs | {m['legs']} |",
        f"| returns n / T_d days | {m['n_returns']} / {m['t_days']:.6g} |",
        f"| initial cash / final equity (KRW) | {m['initial_cash']} / {m['final_equity']} |",
        "",
        f"Flags: short_period {m['cagr']['short_period']}, irregular_spacing {m['irregular_spacing']}, "
        f"no_trades {m['no_trades']}.",
        "",
        f"MDD: {body['metrics_definition']['mdd_note']}",
        "",
        "## Benchmarks",
        "",
    ]
    b = body["benchmarks"]
    if b["status"] != "compared":
        lines += ["**not_aligned**: no benchmark comparison is made. Reasons:", ""]
        lines += [f"- {x}" for x in b["reasons"]]
    else:
        lines += ["| series | sum log r | CAGR | Sharpe (log) | Sortino | MDD (P) |", "|---|---|---|---|---|---|"]
        for name in ("strategy", "b2", "b3", "b4"):
            s = b[name]
            tag = " (REPORT_ONLY)" if name == "b4" else ""
            lines.append(f"| {name}{tag} | {_fmt(s['sum_log_return'])} | {_fmt(s['cagr'])} | {_fmt(s['sharpe_log'])} | "
                         f"{_fmt(s['sortino'])} | {_fmt(s['mdd'])} |")
        b1 = b["b1"]
        q = b1["mean_log_return"]
        lines += [
            "",
            f"B1 ({b1['draws']} placements, {b1['quantile_method']}): mean daily log return mean {_fmt(q['mean'])}, "
            f"q05 {_fmt(q['q05'])}, q50 {_fmt(q['q50'])}, q95 {_fmt(q['q95'])}; strategy minus mean B1 "
            f"{_fmt(b1['strategy_minus_mean_b1'])}. p-value not computed.",
            "",
            f"Differences: sum log r − B2 {_fmt(b['differences']['sum_log_return_minus_b2'])}, "
            f"CAGR − B2 {_fmt(b['differences']['cagr_minus_b2'])}, MDD − B2 {_fmt(b['differences']['mdd_minus_b2'])}.",
            f"B4 weight {_fmt(b['b4']['weight'])}, no rebalancing.",
        ]
    return "\n".join(lines) + "\n"


# --- build ----------------------------------------------------------------------------------------------

def _check_draws(draws: int) -> None:
    if isinstance(draws, bool) or not isinstance(draws, int) or draws < 1:
        raise ReportError(f"b1 draws must be a positive integer, got {draws!r}")


def build_report(run_dir: Path, out_root: Path, *, seed: int, draws: int, code_state: dict[str, Any],
                 now: datetime) -> ReportOutput:
    run_dir = Path(run_dir).resolve()
    out_root = Path(out_root)
    try:
        bt_seed_payload(seed)
    except BenchmarkError as exc:
        raise ReportError(str(exc)) from exc
    _check_draws(draws)
    if not out_root.name.endswith(FIXTURE_ROOT_SUFFIX):
        raise ReportError(f"reports go under a '*{FIXTURE_ROOT_SUFFIX}' root, not {out_root}")
    out_abs = out_root.resolve()
    if out_abs == run_dir or run_dir in out_abs.parents:
        raise ReportError("the report root must not be inside the run directory")
    manifest = _read_manifest(run_dir)
    final = out_root / f"{manifest['run_dir_name']}-report-{utc_stamp(now)}"
    if final.exists():
        raise ReportError(f"{final} already exists; refusing to overwrite")
    before = _tree_hashes(run_dir)
    rep = verify_run(run_dir, code_state=code_state)
    if not rep.ok:
        failed = [k for k, c in rep.checks.items() if c["ok"] is False]
        raise ReportError(f"the run does not verify (failed: {', '.join(failed)}); no report is made")
    try:
        body = compute_body(run_dir, manifest, seed=seed, draws=draws)
        rj = report_bytes(body)
    except (MetricError, BenchmarkError, DataIntegrityError, KeyError) as exc:
        raise ReportError(f"{type(exc).__name__}: {exc}") from exc
    files = {
        "report.json": rj,
        "report.md": report_markdown(body).encode("utf-8"),
        "report_meta.json": _meta_bytes({
            "schema": REPORT_SCHEMA, "evidence": NOT_EVIDENCE, "created_utc": now.astimezone(UTC).isoformat(),
            "code_state": dict(code_state), "python": platform.python_version(),
            "report_sha256": hashlib.sha256(rj).hexdigest()}),
    }
    out_root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-report-", dir=out_root))
    written: list[Path] = []
    try:
        for name in REPORT_FILES:
            p = tmp / name
            atomic_write_bytes(p, files[name])
            written.append(p)
        for name in REPORT_FILES:
            if sha256_file(tmp / name) != hashlib.sha256(files[name]).hexdigest():
                raise ReportError(f"written {name} does not hash to its content")
        sums = "".join(f"{sha256_file(tmp / n)}  {n}\n" for n in REPORT_FILES)
        atomic_write_bytes(tmp / SUMS_FILE, sums.encode("utf-8"))
        written.append(tmp / SUMS_FILE)
        if _tree_hashes(run_dir) != before:
            raise ReportError("the run directory changed while the report was made")
        os.rename(tmp, final)  # never overwrites
    except BaseException:
        for p in written:
            p.unlink(missing_ok=True)
        try:
            tmp.rmdir()
        except OSError:
            pass
        raise
    return ReportOutput(final, hashlib.sha256(rj).hexdigest(), body)


# --- check ----------------------------------------------------------------------------------------------

def check_report(report_dir: Path, run_dir: Path, *, code_state: dict[str, Any]) -> ReportVerifyReport:
    report_dir, run_dir = Path(report_dir), Path(run_dir)
    rep = ReportVerifyReport(str(report_dir))

    def step(name: str, fn) -> Any:
        try:
            detail, out = fn()
        except Exception as exc:  # noqa: BLE001 - every failure is reported, nothing is written
            rep.add(name, False, f"{type(exc).__name__}: {exc}")
            return None
        rep.add(name, True, detail)
        return out

    def files():
        sums = {}
        for line in (report_dir / SUMS_FILE).read_text(encoding="utf-8").splitlines():
            digest, _, name = line.partition("  ")
            sums[name] = digest
        present = sorted(p.name for p in report_dir.iterdir())
        if list(sums) != list(REPORT_FILES) or present != sorted([*REPORT_FILES, SUMS_FILE]):
            raise ReportError(f"report files {present} / {SUMS_FILE} entries {list(sums)} are not the expected set")
        bad = [n for n in REPORT_FILES if sha256_file(report_dir / n) != sums[n]]
        if bad:
            raise ReportError(f"hash mismatch: {bad}")
        return "report files match SHA256SUMS.txt", None

    def meta():
        m = json.loads((report_dir / "report_meta.json").read_text(encoding="utf-8"))
        if m.get("report_sha256") != sha256_file(report_dir / "report.json"):
            raise ReportError("report_meta.json report_sha256 does not match report.json")
        py = m.get("python")
        note = "same Python version" if py == platform.python_version() else \
            f"report made with Python {py}, now {platform.python_version()} (B1 draws may differ)"
        return f"report_sha256 matches; {note}", m

    def versions():
        body = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
        problems = []
        if body.get("schema") not in KNOWN_SCHEMAS:
            problems.append(f"unknown schema {body.get('schema')!r}")
        if body.get("metrics_definition", {}).get("version") not in KNOWN_METRICS_VERSIONS:
            problems.append(f"unknown metrics definition {body.get('metrics_definition', {}).get('version')!r}")
        if body.get("seed", {}).get("algorithm") not in KNOWN_SEED_ALGORITHMS:
            problems.append(f"unknown seed algorithm {body.get('seed', {}).get('algorithm')!r}")
        if problems:
            raise ReportError("; ".join(problems))
        return f"{body['schema']}, {body['metrics_definition']['version']}, {body['seed']['algorithm']}", body

    def run_refs(body):
        manifest = _read_manifest(run_dir)
        if body["run"]["run_dir_name"] != manifest["run_dir_name"]:
            raise ReportError("report refers to another run directory")
        if body["run"]["manifest_sha256"] != sha256_file(run_dir / "manifest.json"):
            raise ReportError("run manifest.json changed since the report")
        if not (body["run"]["result_sha256"] == manifest["result_sha256"] == sha256_file(run_dir / "result.json")):
            raise ReportError("result_sha256 differs between the report, the manifest and result.json")
        return "run manifest and result hashes match the report", manifest

    def run_verify():
        v = verify_run(run_dir, code_state=code_state)
        if not v.ok:
            failed = [k for k, c in v.checks.items() if c["ok"] is False]
            raise ReportError(f"run does not verify: {', '.join(failed)}")
        return "verify_run OK", None

    def content(body, manifest):
        seed = int(body["seed"]["seed"])
        draws = body["seed"]["b1_draws"]
        again = compute_body(run_dir, manifest, seed=seed, draws=draws)
        if report_bytes(again) != (report_dir / "report.json").read_bytes():
            raise ReportError("report.json is not reproduced byte for byte")
        if report_markdown(again).encode("utf-8") != (report_dir / "report.md").read_bytes():
            raise ReportError("report.md is not reproduced from report.json")
        return "report.json and report.md reproduced byte for byte", None

    step("files", files)
    step("meta", meta)
    body = step("versions", versions)
    manifest = step("run_refs", lambda: run_refs(body)) if body is not None else None
    if body is None:
        rep.add("run_refs", False, "skipped: report.json schema and versions did not check")
    step("run_verify", run_verify)
    if body is not None and manifest is not None:
        step("content", lambda: content(body, manifest))
    else:
        rep.add("content", False, "skipped: versions or run references did not check")
    return rep
