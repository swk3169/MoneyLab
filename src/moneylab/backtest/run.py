"""Backtest run directories and their verification (BT-2b-2; docs/backtest_bt2b_review.md 4.3).

`run_backtest` loads two exported bar directories (backtest.bars_io), runs one RunConfig and writes
  result.json     canonical JSON of the result (no timestamps; its SHA-256 is result_sha256)
  trades.jsonl, daily.jsonl, orders.jsonl (unfilled and cancelled), metrics.json
  manifest.json   evidence and labels, config, inputs (paths, bars_sha256, bar manifest hashes),
                  settings file (raw and LF-normalized SHA-256 and the normalization rule), code state
                  (commit and classified working tree, backtest.code_state; supplied by the caller: no
                  subprocess here), Python version, result_sha256
  SHA256SUMS.txt
into <out_root>/<rule>-<scenario>-<fee>bp-<UTC stamp>/ through a temporary directory that is renamed
only after every file is written and hashed. An existing directory is never overwritten. Initial cash
is fixed at 1,000,000 KRW. Fixture runs must go under a root whose name ends with "-fixture".

`verify_run` writes nothing and reports each check separately:
  files              SHA256SUMS.txt lists exactly the run files and every hash matches
  inputs             bar directories reload (their own SHA checks) with the recorded hashes
  settings           LF-normalized settings hash matches (a raw-byte difference is reported, not failed)
  code               current commit == recorded commit; neither side has tracked changes or untracked files
                     that can affect execution (allowed untracked documents are listed, not failed)
  reproducibility    the same config on the same inputs gives the same result_sha256
  accounting         ledger invariants on the recomputed run and on the stored daily / trade rows
  boundary           the stored signals, daily rows and trades lie inside the evaluation boundary derived
                     from the config (BT-3b, `boundary_problems`); checked on the files, not by re-running
  engine_self_check  a hand-calculated reference case still gives its exact expected equity
The full pytest suite is not run here (no subprocess in backtest/); run it separately.
All outputs are SYNTHETIC / NOT_EVIDENCE before BT-5.
"""

from __future__ import annotations

import json
import os
import platform
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from moneylab.backtest.bars_io import MANIFEST_FILE as BARS_MANIFEST_FILE
from moneylab.backtest.bars_io import load_bars
from moneylab.backtest.code_state import CODE_STATE_POLICY, code_state_problems
from moneylab.backtest.costs import PRECISION, CostModel
from moneylab.backtest.data import BarSeries, DataIntegrityError, LookAheadError, provenance_for
from moneylab.backtest.execution import SCENARIOS
from moneylab.backtest.ledger import AccountingError
from moneylab.backtest.portfolio import BacktestResult, RunConfig, evaluation_boundary, simulate
from moneylab.backtest.settings import cost_model, load_cost_settings, settings_hashes
from moneylab.domain.bars import NOT_EVIDENCE, Bar
from moneylab.storage.atomic import atomic_write_bytes, sha256_file

SCHEMA = "moneylab.backtest.run/1"
INITIAL_CASH_KRW = Decimal(1_000_000)
RUN_FILES = ("daily.jsonl", "manifest.json", "metrics.json", "orders.jsonl", "result.json", "trades.jsonl")
SUMS_FILE = "SHA256SUMS.txt"
FIXTURE_ROOT_SUFFIX = "-fixture"
TOLERANCE = Decimal("1e-30")


class RunError(ValueError):
    """The run cannot be made (inputs, settings, config or output path)."""


@dataclass(frozen=True)
class RunOutput:
    dir: Path
    result_sha256: str
    manifest: dict[str, Any]
    result: BacktestResult


@dataclass
class RunVerifyReport:
    run_dir: str
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add(self, name: str, ok: bool | None, detail: str) -> None:
        self.checks[name] = {"ok": ok, "detail": detail}

    @property
    def ok(self) -> bool:
        return bool(self.checks) and all(c["ok"] is not False for c in self.checks.values()) and all(
            self.checks.get(k, {}).get("ok") is True for k in VERIFY_CHECKS)

    def to_dict(self) -> dict[str, Any]:
        return {"evidence": NOT_EVIDENCE, "run_dir": self.run_dir, "ok": self.ok, "checks": self.checks}


VERIFY_CHECKS = ("files", "inputs", "settings", "code", "reproducibility", "accounting", "boundary",
                 "engine_self_check")
FILL_KINDS = ("primary", "substituted", "virtual_fallback")


def utc_stamp(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def run_dir_name(config: RunConfig, now: datetime) -> str:
    c = config.costs
    fee = f"{c.buy_fee_bps.normalize():f}" if c.buy_fee_bps == c.sell_fee_bps else \
        f"{c.buy_fee_bps.normalize():f}-{c.sell_fee_bps.normalize():f}"
    return f"{config.rule}-{config.scenario}-{fee}bp-{utc_stamp(now)}"


def config_from_dict(d: dict[str, Any]) -> RunConfig:
    c = d["costs"]
    costs = CostModel(Decimal(c["buy_fee_bps"]), Decimal(c["sell_fee_bps"]), Decimal(c["slippage_bps"]),
                      c["fee_status"], c["label"], Decimal(c["impact_bps"]), c["fee_basis"])

    def day(s: str) -> datetime:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))

    return RunConfig(d["rule"], day(d["first_day"]), day(d["last_day"]), Decimal(d["initial_cash"]), costs,
                     scenario=d["scenario"], fill_substitution=d["fill_substitution"],
                     confirm_delay=timedelta(seconds=d["confirm_delay_s"]),
                     capacity_verified=d["capacity"] == "verified_range")


def _expected_costs(config: RunConfig, settings_file: Path) -> CostModel:
    settings, _ = load_cost_settings(settings_file)
    fee = int(config.costs.buy_fee_bps)
    model, verified = cost_model(settings, fee, config.scenario, config.initial_cash,
                                 impact=config.costs.impact_bps > 0, fee_basis=config.costs.fee_basis)
    if model != config.costs or Decimal(fee) != config.costs.buy_fee_bps:
        raise RunError("the run's cost model does not follow the settings file")
    if verified != config.capacity_verified:
        raise RunError("capacity flag does not match the settings file")
    return model


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows).encode("utf-8")


def _input_record(path: Path, series: BarSeries) -> dict[str, Any]:
    return {"path": str(Path(path).resolve()), "dir_name": Path(path).name, "kind": series.provenance.kind,
            "bars_sha256": series.provenance.bars_sha256,
            "bars_manifest_sha256": sha256_file(Path(path) / BARS_MANIFEST_FILE)}


def run_backtest(daily_dir: Path, hourly_dir: Path, config: RunConfig, out_root: Path, *, code_state: dict[str, Any],
                 settings_file: Path, now: datetime) -> RunOutput:
    out_root = Path(out_root)
    if config.initial_cash != INITIAL_CASH_KRW:
        raise RunError(f"initial cash is fixed at {INITIAL_CASH_KRW} KRW")
    if code_state.get("policy") != CODE_STATE_POLICY:
        raise RunError(f"code_state must come from backtest.code_state.classify_worktree ({CODE_STATE_POLICY})")
    _expected_costs(config, settings_file)
    daily, hourly = load_bars(daily_dir), load_bars(hourly_dir)
    kinds = {daily.provenance.kind, hourly.provenance.kind}
    if kinds & {"fixture", "synthetic"} and not out_root.name.endswith(FIXTURE_ROOT_SUFFIX):
        raise RunError(f"fixture/synthetic runs must go under a '*{FIXTURE_ROOT_SUFFIX}' root, not {out_root}")
    final = out_root / run_dir_name(config, now)
    if final.exists():
        raise RunError(f"{final} already exists; refusing to overwrite")
    result = simulate(daily, hourly, config)
    body = result.to_dict()
    result_bytes = result.canonical_json()
    manifest = {
        "schema": SCHEMA, "evidence": NOT_EVIDENCE, "labels": result.labels, "run_dir_name": final.name,
        "created_utc": now.astimezone(UTC).isoformat(), "config": config.to_dict(),
        "inputs": {"day": _input_record(daily_dir, daily), "hour": _input_record(hourly_dir, hourly)},
        "settings": settings_hashes(settings_file), "code_state": dict(code_state),
        "python": platform.python_version(), "result_sha256": result.sha256(), "files": list(RUN_FILES),
        "regression_tests": "not run by the backtest; run the pytest suite separately",
    }
    files = {
        "result.json": result_bytes,
        "trades.jsonl": _jsonl(body["trades"]),
        "daily.jsonl": _jsonl(body["daily"]),
        "orders.jsonl": _jsonl([{"status": "unfilled"} | r for r in body["unfilled"]] +
                               [{"status": "cancelled"} | r for r in body["cancelled"]]),
        "metrics.json": (json.dumps(body["metrics"], sort_keys=True, indent=1) + "\n").encode("utf-8"),
        "manifest.json": (json.dumps(manifest, sort_keys=True, indent=1) + "\n").encode("utf-8"),
    }
    out_root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".tmp-run-", dir=out_root))
    written: list[Path] = []
    try:
        for name in RUN_FILES:
            p = tmp / name
            atomic_write_bytes(p, files[name])
            written.append(p)
        if sha256_file(tmp / "result.json") != manifest["result_sha256"]:
            raise RunError("written result.json does not hash to result_sha256")
        sums = "".join(f"{sha256_file(tmp / n)}  {n}\n" for n in RUN_FILES)
        atomic_write_bytes(tmp / SUMS_FILE, sums.encode("utf-8"))
        written.append(tmp / SUMS_FILE)
        os.rename(tmp, final)  # never overwrites
    except BaseException:
        for p in written:
            p.unlink(missing_ok=True)
        try:
            tmp.rmdir()
        except OSError:
            pass
        raise
    return RunOutput(final, manifest["result_sha256"], manifest, result)


# --- verification ---------------------------------------------------------------------------------------

def _close(a: Decimal, b: Decimal) -> bool:
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return abs(a - b) <= TOLERANCE * max(abs(a), abs(b), Decimal(1))


def _stored_accounting(run_dir: Path) -> str:
    """Invariants on the stored rows themselves (independent of the recomputation)."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        for line in (run_dir / "daily.jsonl").read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            cash, qty, price, eq = (Decimal(d[k]) for k in ("cash", "quantity", "price", "equity"))
            if cash < 0 or qty < 0 or not _close(eq, cash + qty * price):
                raise AccountingError(f"stored daily row {d['ref_time']} breaks equity = cash + quantity * price")
        for line in (run_dir / "trades.jsonl").read_text(encoding="utf-8").splitlines():
            t = json.loads(line)
            v = {k: Decimal(t[k]) for k in ("cash_before", "cash_after", "qty_before", "qty_after", "ref_price",
                                            "fee", "slippage_cost", "impact_cost")}
            before = v["cash_before"] + v["qty_before"] * v["ref_price"]
            after = v["cash_after"] + v["qty_after"] * v["ref_price"]
            if min(v["cash_after"], v["qty_after"]) < 0 or not _close(
                    after, before - v["fee"] - v["slippage_cost"] - v["impact_cost"]):
                raise AccountingError(f"stored trade leg {t['leg']} breaks the cost identity")
    return "stored rows hold the invariants"


def _utc(text: Any) -> datetime:
    t = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if t.utcoffset() != timedelta(0):
        raise ValueError(f"not a UTC time: {text!r}")
    return t


def boundary_problems(config: dict[str, Any], signals: list[dict[str, Any]], daily: list[dict[str, Any]],
                      trades: list[dict[str, Any]]) -> list[str]:
    """Temporal membership of the stored rows in the run's evaluation boundary (BT-3b). Pure: reads only the
    given config and rows (it does not run the backtest). Terminal holdings are the accounting check's job."""
    try:
        cfg = config_from_dict(config)  # V1: first_day / last_day at 00:00 UTC and last_day >= first_day
        b = evaluation_boundary(cfg)  # V6: valuation end <= G_end
    except (KeyError, TypeError, ValueError) as exc:
        return [f"config: {type(exc).__name__}: {exc}"]
    problems: list[str] = []
    if b.valuation_end > b.g_end:
        problems.append(f"valuation end {b.valuation_end} is after G_end {b.g_end}")
    one_day = timedelta(days=1)
    spec = SCENARIOS[cfg.scenario]
    n = (cfg.last_day - cfg.first_day).days + 1

    try:  # V2
        days = [_utc(s["day"]) for s in signals]
        if days != [cfg.first_day + k * one_day for k in range(n)]:
            problems.append(f"signal days are not exactly first_day .. last_day ({len(days)} rows, expected {n})")
        for s, d in zip(signals, days):
            decided = _utc(s["decided_at"])
            if decided != d + one_day + cfg.confirm_delay:
                problems.append(f"signal {s['day']}: decided_at {s['decided_at']} does not follow the confirm delay")
            if decided > b.g_end:
                problems.append(f"signal {s['day']}: decided_at {s['decided_at']} is after G_end")
    except (KeyError, TypeError, ValueError) as exc:
        problems.append(f"signals: {type(exc).__name__}: {exc}")

    try:  # V3
        allowed = {spec.ref_time(cfg.first_day + k * one_day) for k in range(n + 1)}
        refs = [_utc(r["ref_time"]) for r in daily]
        for r, t in zip(daily, refs):
            if t not in allowed:
                problems.append(f"daily row {r['ref_time']} is not a reference time R(D), "
                                f"first_day <= D <= last_day + 1")
            if t > b.valuation_end:
                problems.append(f"daily row {r['ref_time']} is after the valuation end")
        if any(a >= c for a, c in zip(refs, refs[1:])):
            problems.append("daily reference times are not strictly increasing")
    except (KeyError, TypeError, ValueError) as exc:
        problems.append(f"daily: {type(exc).__name__}: {exc}")

    try:  # V4, V5
        virtual = 0
        for t in trades:
            leg = t.get("leg")
            day, fill, start, signal = (_utc(t[k]) for k in ("day", "fill_time", "fill_bar_start", "signal_time"))
            kind, is_virtual = t["fill_kind"], t["virtual"]
            if kind not in FILL_KINDS:
                problems.append(f"trade {leg}: unknown fill_kind {kind!r}")
            if not start <= fill <= b.valuation_end:
                problems.append(f"trade {leg}: fill_bar_start {t['fill_bar_start']} <= fill_time {t['fill_time']} "
                                f"<= valuation end does not hold")
            if fill > b.g_end:
                problems.append(f"trade {leg}: fill_time {t['fill_time']} is after G_end")
            if signal > b.g_end:
                problems.append(f"trade {leg}: signal_time {t['signal_time']} is after G_end")
            if kind in ("primary", "substituted") and not start < fill:
                problems.append(f"trade {leg}: {kind} fill bar must start before it ends")
            if kind == "virtual_fallback" and not is_virtual:
                problems.append(f"trade {leg}: virtual_fallback on a non-virtual trade")
            if is_virtual:
                virtual += 1
                if fill != b.valuation_end:
                    problems.append(f"trade {leg}: virtual exit fill_time {t['fill_time']} is not the valuation end")
                if day != cfg.last_day + one_day:
                    problems.append(f"trade {leg}: virtual exit on day {t['day']}, expected last_day + 1")
            elif not cfg.first_day <= day <= cfg.last_day:
                problems.append(f"trade {leg}: day {t['day']} is outside first_day .. last_day")
        if virtual > 1:
            problems.append(f"{virtual} virtual exits (at most one)")
    except (KeyError, TypeError, ValueError) as exc:
        problems.append(f"trades: {type(exc).__name__}: {exc}")
    return problems


def engine_self_check() -> str:
    """Hand-calculated reference (sma20, E0, 25 bp fee, 5 bp slippage): buy at 121, sell at 91.
    Expected final equity = 1,000,000 * 0.9975^2 * 0.9995^2 * 91 / 121, exactly up to 50 digits."""
    t0 = datetime(2020, 1, 1, tzinfo=UTC)
    fills = {20: 100, 21: 121, 22: 129, 23: 91, 24: 90, 25: 89, 26: 88}
    closes = [100] * 20 + [120, 130, 90, 90, 90, 90, 90]

    def bar(interval: str, start: datetime, p: int) -> Bar:
        d = Decimal(p)
        return Bar("KRW-BTC", interval, start, d, d, d, d, Decimal(1), Decimal(1))

    day = [bar("day", t0 + timedelta(days=i), c) for i, c in enumerate(closes)]
    hour = [bar("hour", t0 + timedelta(days=d, hours=h), fills.get(d, 100)) for d in range(27) for h in range(24)]
    ds = BarSeries.build(day, provenance_for(day, "synthetic", "engine_self_check"))
    hs = BarSeries.build(hour, provenance_for(hour, "synthetic", "engine_self_check"))
    cfg = RunConfig("sma20", t0 + timedelta(days=19), t0 + timedelta(days=23), INITIAL_CASH_KRW,
                    CostModel.scenario(25, 5))
    led = simulate(ds, hs, cfg).ledger
    led.verify()
    with localcontext() as ctx:
        ctx.prec = PRECISION
        want = INITIAL_CASH_KRW * Decimal("0.9975") ** 2 * Decimal("0.9995") ** 2 * Decimal(91) / Decimal(121)
        if len(led.trades) != 2 or not _close(led.daily[-1].equity, want):
            raise AccountingError(f"engine self-check: final equity {led.daily[-1].equity} != {want}")
    return "hand case reproduced (2 legs, exact final equity)"


def _check(rep: RunVerifyReport, name: str, fn) -> Any:
    try:
        out = fn()
    except (OSError, ValueError, KeyError, TypeError, AccountingError, DataIntegrityError) as exc:
        rep.add(name, False, f"{type(exc).__name__}: {exc}")
        return None
    detail, value = out if isinstance(out, tuple) else (out, None)
    rep.add(name, True, detail)
    return value


def verify_run(run_dir: Path, *, code_state: dict[str, Any]) -> RunVerifyReport:
    run_dir = Path(run_dir)
    rep = RunVerifyReport(str(run_dir))
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        rep.add("files", False, f"cannot read manifest.json: {exc}")
        return rep

    def files() -> str:
        sums = {}
        for line in (run_dir / SUMS_FILE).read_text(encoding="utf-8").splitlines():
            digest, _, name = line.partition("  ")
            sums[name] = digest
        if set(sums) != set(RUN_FILES):
            raise DataIntegrityError(f"{SUMS_FILE} lists {sorted(sums)}, expected {list(RUN_FILES)}")
        bad = [n for n in RUN_FILES if sha256_file(run_dir / n) != sums[n]]
        if bad:
            raise DataIntegrityError(f"hash mismatch: {bad}")
        if sha256_file(run_dir / "result.json") != manifest["result_sha256"]:
            raise DataIntegrityError("result.json does not hash to the manifest result_sha256")
        return "all run files match SHA256SUMS.txt and result_sha256"

    def inputs():
        series = {}
        for iv, rec in manifest["inputs"].items():
            s = load_bars(Path(rec["path"]))
            if s.provenance.bars_sha256 != rec["bars_sha256"]:
                raise DataIntegrityError(f"{iv} bars changed since the run")
            if sha256_file(Path(rec["path"]) / BARS_MANIFEST_FILE) != rec["bars_manifest_sha256"]:
                raise DataIntegrityError(f"{iv} bar manifest changed since the run")
            series[iv] = s
        return "input bars reload with the recorded hashes", series

    def settings() -> str:
        rec = manifest["settings"]
        now_h = settings_hashes(Path(rec["path"]))
        if now_h["sha256_lf_normalized"] != rec["sha256_lf_normalized"]:
            raise DataIntegrityError("settings file content changed since the run")
        raw = "raw bytes identical" if now_h["sha256_raw_bytes"] == rec["sha256_raw_bytes"] else \
            "raw bytes differ (line endings only: the LF-normalized hash matches)"
        return f"settings LF-normalized hash matches; {raw}"

    def code() -> str:
        rec = manifest.get("code_state") or {}
        if not rec.get("commit") or not code_state.get("commit"):
            raise DataIntegrityError("commit unknown")
        if rec["commit"] != code_state["commit"]:
            raise DataIntegrityError(f"code commit {code_state['commit'][:12]} != run commit {rec['commit'][:12]}")
        bad = [f"run time: {p}" for p in code_state_problems(rec)] + \
              [f"now: {p}" for p in code_state_problems(code_state)]
        if bad:
            raise DataIntegrityError("; ".join(bad) + "; the code cannot be pinned")
        run_docs, now_docs = rec["untracked_allowed"], code_state["untracked_allowed"]
        docs = f"allowed untracked documents: run time {len(run_docs)}, now {len(now_docs)}"
        if run_docs != now_docs:
            docs += " (the lists differ; documents do not affect execution)"
        return f"commit {rec['commit'][:12]} matches; no tracked changes or execution-relevant untracked files " \
               f"at run time or now; {docs}"

    _check(rep, "files", files)
    series = _check(rep, "inputs", inputs)
    _check(rep, "settings", settings)
    _check(rep, "code", code)
    recomputed: list[BacktestResult] = []

    def reproducibility() -> str:
        if series is None:
            raise DataIntegrityError("inputs did not verify")
        cfg = config_from_dict(manifest["config"])
        _expected_costs(cfg, Path(manifest["settings"]["path"]))
        res = simulate(series["day"], series["hour"], cfg)
        recomputed.append(res)
        if res.sha256() != manifest["result_sha256"]:
            raise DataIntegrityError("recomputed result differs from the stored result")
        return "same config and inputs reproduce result_sha256"

    def accounting() -> str:
        if not recomputed:
            raise AccountingError("no recomputed run to check")
        recomputed[0].ledger.verify()
        return "recomputed ledger verifies; " + _stored_accounting(run_dir)

    def boundary() -> str:
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))

        def rows(name: str) -> list[dict[str, Any]]:
            return [json.loads(line) for line in (run_dir / name).read_text(encoding="utf-8").splitlines() if line]

        problems = boundary_problems(manifest["config"], result["signals"], rows("daily.jsonl"), rows("trades.jsonl"))
        if problems:
            more = f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""
            raise LookAheadError("; ".join(problems[:5]) + more)
        b = evaluation_boundary(config_from_dict(manifest["config"]))
        return f"stored rows lie within G_end {b.g_end.isoformat()}; valuation end {b.valuation_end.isoformat()}"

    _check(rep, "reproducibility", reproducibility)
    _check(rep, "accounting", accounting)
    _check(rep, "boundary", boundary)
    _check(rep, "engine_self_check", engine_self_check)
    rep.add("regression_tests", None, "not run by verify_run; run the pytest suite separately")
    return rep
