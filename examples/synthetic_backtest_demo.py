"""MoneyLab synthetic backtest pipeline demo (SYNTHETIC / NOT_EVIDENCE).

A pipeline demonstration on synthetic data: one offline command runs the existing MoneyLab CLI stages

    candles-pull (fixture, day and hour) -> bars-export -> backtest -> backtest-verify
    -> backtest-report -> backtest-report-verify

on the synthetic fixture tests/fixtures/upbit_candles_backtest_synthetic.json and checks the outputs against
known hashes. It shows reproducibility and integrity controls; it is not a strategy test and says nothing about
profitability. sma20 is an engine-validation rule, not one of the preregistered v0.6 rules.

Prerequisite (README, Getting Started): `pip install -r requirements-dev.txt` and `pip install -e . --no-deps`
from a repository checkout. Reports are only made for a pinned code state (clean Git checkout); otherwise the
demo stops after verification with PARTIAL_CODE_STATE_UNPINNED.

Usage: python examples/synthetic_backtest_demo.py [--workdir DIR]
Without --workdir the outputs go to a temporary directory that is removed afterwards. With --workdir (a new or
empty directory) they are kept, together with demo_summary.json.

Exit codes: 0 COMPLETE, 1 FAILED, 2 invalid arguments, 4 PARTIAL_CODE_STATE_UNPINNED (3 is not used).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

EVIDENCE = "SYNTHETIC / NOT_EVIDENCE"
SCHEMA = "moneylab.demo.synthetic_backtest/1"
EXIT_COMPLETE, EXIT_FAILED, EXIT_PARTIAL = 0, 1, 4
COMPLETE, FAILED, PARTIAL = "COMPLETE", "FAILED", "PARTIAL_CODE_STATE_UNPINNED"

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "upbit_candles_backtest_synthetic.json"
SETTINGS = REPO / "configs" / "backtest_costs.toml"

# Fixed configuration (Work Order PORTFOLIO-DEMO-01, D3). B1 draws = 20 keeps the demo short; it is not a
# research-grade Monte Carlo sample size.
PULLS = {"day": ("2025-06-01T00:00:00Z", "2025-12-19T00:00:00Z"),
         "hour": ("2025-06-01T00:00:00Z", "2025-12-18T11:00:00Z")}
RULE, FIRST_DAY, LAST_DAY = "sma20", "2025-06-26", "2025-11-28"
SCENARIO, FEE_BPS, FEE_BASIS = "E0", 25, "inclusive"
B1_SEED, B1_DRAWS = 20261027, 20

# Cross-run deterministic goldens (ERRATA-001). result_sha256 is not among them: result.json carries
# timestamp-bearing provenance, so its hash is a per-run integrity value.
GOLDEN_BARS = {"day": ("d6a40221a2c3b810d468b0f522cc2a1ef2305315f43864e0b37e7410251ec561", 199),
               "hour": ("39ad26cbb0cedfe3a647f6dc01e31d19f8bec58a9d69f460918516bad972e412", 4809)}
GOLDEN_RUN_FILES = {"daily.jsonl": "77211e81cc44b32605b0d4b1eccf02ac4a8bbb0d06dfcf9f7272ba20521578ac",
                    "metrics.json": "bc26e3f19fd7c48381bff995c74b1ee5a1fe3085bb92e16b40044fd29de971c6",
                    "trades.jsonl": "066b65f86992b11a0538c0c978088b84eae70b406c9351028f987e791c658bbb",
                    "orders.jsonl": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
STAGES = ("candles-pull day", "candles-pull hour", "bars-export day", "bars-export hour", "backtest",
          "backtest-verify", "backtest-report", "backtest-report-verify")


# Absolute paths in free text: Windows drive (C:\ or C:/), UNC (\\host) or POSIX (/...). Paths may contain spaces,
# so a quoted path (as in exception messages) is redacted up to its closing quote and an unquoted one up to the end of
# the line. A "/" after a word character or after the <path> marker ("429/5xx", "docs/x.md", "<path>/x") or before
# a space ("a / b") does not start a path; this also keeps strip_paths idempotent.
QUOTED_PATH = re.compile(r"(['\"])((?:[A-Za-z]:[\\/]|\\\\|/)(?:(?!\1)[^\n])*)\1")
UNQUOTED_PATH = re.compile(r"(?:\b[A-Za-z]:[\\/]|\\\\|(?<![\w.~>-])/(?!\s))[^\n]*")
FILE_NAME = re.compile(r"[\w.-]+\.\w+")  # a plain file name such as manifest.json; directory names are dropped


def safe_name(path: str) -> str:
    """<path>/<file name>, or <path> when the last component is not a plain file name (it may be a user directory)."""
    name = re.split(r"[\\/]+", path.rstrip("\\/ "))[-1]
    return f"<path>/{name}" if FILE_NAME.fullmatch(name) else "<path>"


def strip_paths(text: str) -> str:
    """Replace absolute paths so demo_summary.json stays machine-independent; already stripped text is unchanged."""
    text = QUOTED_PATH.sub(lambda m: m.group(1) + safe_name(m.group(2)) + m.group(1), text)
    return UNQUOTED_PATH.sub("<path>", text)


def describe_error(exc: Exception) -> str:
    """Exception type and reason (not yet path-stripped; Demo.fail is the single sanitizing step)."""
    if isinstance(exc, OSError) and exc.strerror:
        names = [safe_name(str(f)) for f in (exc.filename, exc.filename2) if f]
        return f"{type(exc).__name__}: {exc.strerror}" + (f" ({', '.join(names)})" if names else "")
    return f"{type(exc).__name__}: {exc}"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_sums(run_dir: Path) -> dict[str, str]:
    """SHA256SUMS.txt of a run directory: `<sha256>  <name>` per line."""
    sums = {}
    for line in (run_dir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            sums[name.strip()] = digest
    return sums


def only_child(root: Path) -> Path:
    """The single output directory a stage created under its fresh output root."""
    children = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    if len(children) != 1:
        raise RuntimeError(f"expected one output directory under {root.name}, found {len(children)}")
    return children[0]


class Demo:
    def __init__(self, work: Path) -> None:
        from moneylab import cli

        self.cli = cli
        self.work = work
        self.stages = [{"name": name, "status": "NOT_RUN", "exit_code": None} for name in STAGES]
        self.summary: dict[str, Any] = {
            "schema": SCHEMA, "evidence": EVIDENCE, "demo_status": None, "exit_code": None,
            "config": {"fixture": FIXTURE.relative_to(REPO).as_posix(), "settings": SETTINGS.relative_to(REPO).as_posix(),
                       "pulls": {k: {"start": s, "end": e} for k, (s, e) in PULLS.items()}, "rule": RULE,
                       "first_day": FIRST_DAY, "last_day": LAST_DAY, "scenario": SCENARIO, "fee_bps": FEE_BPS,
                       "fee_basis": FEE_BASIS, "b1_seed": B1_SEED, "b1_draws": B1_DRAWS},
            "code_state": None, "stages": self.stages,
            "cross_run_deterministic_artifacts": {"bars": {}, "run_files": {}},
            "per_run_integrity": None, "verify": None, "report": {"status": "NOT_RUN", "report_verify": "NOT_RUN"},
            "paths": {}, "problems": [],
        }

    def stage(self, index: int, argv: list[str]) -> bool:
        print(f"\n== [{index + 1}/{len(STAGES)}] {STAGES[index]}", flush=True)
        rc = self.cli.main(argv)
        sys.stdout.flush()
        self.stages[index].update(status="OK" if rc == 0 else "FAILED", exit_code=rc)
        return rc == 0

    def fail(self, problem: str, detail: str | None = None) -> str:
        """Record a failure. This is the one place where summary text is path-stripped; the console may show the
        full detail."""
        self.summary["problems"].append(strip_paths(problem))
        print(f"FAILED: {detail or problem}")
        return FAILED

    def rel(self, path: Path) -> str:
        return path.relative_to(self.work).as_posix()

    def run(self) -> str:
        from moneylab.backtest.code_state import code_state_problems

        state = self.cli.backtest_code_state()
        problems = code_state_problems(state)
        self.summary["code_state"] = {"classification": "UNPINNED" if problems else "PINNED",
                                      "commit": state.get("commit"), "problems": problems}
        print(f"code state: {'UNPINNED (' + '; '.join(problems) + ')' if problems else 'PINNED'}"
              f" (commit {state.get('commit') or 'unknown'})")

        bars = {}
        for i, interval in enumerate(PULLS):
            start, end = PULLS[interval]
            if not self.stage(i, ["candles-pull", "--source", "fixture", "--fixture", str(FIXTURE), "--interval",
                                  interval, "--start", start, "--end", end, "--out", str(self.work / "candles-fixture")]):
                return self.fail(f"candles-pull {interval} failed")
        for i, interval in enumerate(PULLS, start=2):
            pull = only_child_matching(self.work / "candles-fixture", f"{interval}_")
            out = self.work / f"bars_{interval}-fixture"
            if not self.stage(i, ["bars-export", str(pull), "--out", str(out)]):
                return self.fail(f"bars-export {interval} failed")
            bars[interval] = only_child(out)
            manifest = json.loads((bars[interval] / "bars_manifest.json").read_text(encoding="utf-8"))
            observed, count = manifest["bars_sha256"], manifest["bars"]
            expected = GOLDEN_BARS[interval]
            match = (observed, count) == expected
            self.summary["cross_run_deterministic_artifacts"]["bars"][interval] = {
                "bars_sha256": observed, "bars": count, "expected_sha256": expected[0], "expected_bars": expected[1],
                "match": match}
            self.summary["paths"][f"bars_{interval}"] = self.rel(bars[interval])
            if not match:
                return self.fail(f"{interval} bars_sha256 {observed} ({count} bars) != golden {expected[0]}")

        if not self.stage(4, ["backtest", "--daily", str(bars["day"]), "--hourly", str(bars["hour"]), "--rule", RULE,
                              "--first-day", FIRST_DAY, "--last-day", LAST_DAY, "--fee-bps", str(FEE_BPS),
                              "--fee-basis", FEE_BASIS, "--scenario", SCENARIO, "--settings", str(SETTINGS),
                              "--out", str(self.work / "runs-fixture")]):
            return self.fail("backtest failed")
        run_dir = only_child(self.work / "runs-fixture")
        self.summary["paths"]["run"] = self.rel(run_dir)

        sums = read_sums(run_dir)
        files_ok = True
        for name, golden in GOLDEN_RUN_FILES.items():
            listed, actual = sums.get(name), sha256_file(run_dir / name)
            match = listed == actual == golden
            self.summary["cross_run_deterministic_artifacts"]["run_files"][name] = {
                "sha256": actual, "sha256sums_entry": listed, "expected_sha256": golden, "match": match}
            files_ok = files_ok and match
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        recorded, listed, actual = manifest.get("result_sha256"), sums.get("result.json"), sha256_file(run_dir / "result.json")
        consistent = recorded is not None and recorded == listed == actual
        self.summary["per_run_integrity"] = {
            "result_sha256": recorded, "sha256sums_entry": listed, "result_json_sha256": actual,
            "internally_consistent": consistent,
            "note": "per-run integrity value; result.json includes timestamp-bearing provenance, so this hash is "
                    "not a cross-run deterministic identifier"}

        self.stage(5, ["backtest-verify", str(run_dir)])
        from moneylab.backtest.run import VERIFY_CHECKS, verify_run

        rep = verify_run(run_dir, code_state=self.cli.backtest_code_state())
        checks = {name: c["ok"] for name, c in rep.checks.items()}
        non_code_ok = (all(ok is not False for name, ok in checks.items() if name != "code")
                       and all(checks.get(name) is True for name in VERIFY_CHECKS if name != "code"))
        self.summary["verify"] = {"status": rep.status, "ok": rep.ok, "checks": checks, "non_code_ok": non_code_ok,
                                  "code_ok": checks.get("code")}
        # Substantive integrity first; the code state is only looked at once everything else is known to be good.
        if not files_ok:
            return self.fail("a deterministic run artifact differs from its golden SHA-256")
        if not consistent:
            return self.fail("result_sha256 is not consistent with SHA256SUMS.txt and the result.json bytes")
        if not non_code_ok:
            return self.fail("a non-code verification check did not pass")
        if checks.get("code") is not True:
            self.stages[5]["status"] = "CODE_STATE_UNPINNED"  # only the existing code check did not pass
            print("\nThe existing MoneyLab policy requires a pinned code state (clean Git checkout) for report "
                  "generation; the report stages are not run.")
            for i in (6, 7):
                self.stages[i]["status"] = "SKIPPED_CODE_STATE_UNPINNED"
            self.summary["report"] = {"status": "SKIPPED_CODE_STATE_UNPINNED",
                                      "report_verify": "SKIPPED_CODE_STATE_UNPINNED"}
            return PARTIAL

        reports = self.work / "reports-fixture"
        if not self.stage(6, ["backtest-report", str(run_dir), "--seed", str(B1_SEED), "--b1-draws", str(B1_DRAWS),
                              "--out", str(reports)]):
            self.summary["report"]["status"] = "FAILED"
            return self.fail("backtest-report failed")
        report_dir = only_child(reports)
        self.summary["paths"]["report"] = self.rel(report_dir)
        self.summary["report"]["status"] = "OK"
        if not self.stage(7, ["backtest-report-verify", str(report_dir), str(run_dir)]):
            self.summary["report"]["report_verify"] = "FAILED"
            return self.fail("backtest-report-verify failed")
        self.summary["report"]["report_verify"] = "OK"
        return COMPLETE


def only_child_matching(root: Path, prefix: str) -> Path:
    found = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith(prefix))
    if len(found) != 1:
        raise RuntimeError(f"expected one {prefix}* pull under {root.name}, found {len(found)}")
    return found[0]


def print_summary(s: dict[str, Any]) -> None:
    print(f"\n{EVIDENCE} | demo summary (pipeline demonstration on synthetic data)")
    if s["code_state"]:
        print(f"  code state: {s['code_state']['classification']}")
    for st in s["stages"]:
        print(f"  stage {st['name']}: {st['status']}")
    art = s["cross_run_deterministic_artifacts"]
    for interval, b in art["bars"].items():
        print(f"  {interval} bars_sha256 {b['bars_sha256']} ({b['bars']} bars): {'MATCH' if b['match'] else 'MISMATCH'}")
    for name, f in art["run_files"].items():
        print(f"  {name} sha256 {f['sha256']}: {'MATCH' if f['match'] else 'MISMATCH'}")
    if s["per_run_integrity"]:
        p = s["per_run_integrity"]
        print(f"  result_sha256 {p['result_sha256']} (per-run integrity; "
              f"{'consistent' if p['internally_consistent'] else 'INCONSISTENT'} with SHA256SUMS.txt and result.json)")
    if s["verify"]:
        print(f"  backtest-verify: {s['verify']['status']}")
        for name, ok in s["verify"]["checks"].items():
            print(f"    {'PASS' if ok is True else 'FAIL' if ok is False else 'NOTE'} {name}")
    print(f"  report: {s['report']['status']}, report-verify: {s['report']['report_verify']}")
    print(f"DEMO_STATUS = {s['demo_status']}")


def main(argv: list[str] | None = None) -> int:
    print(f"{EVIDENCE} - MoneyLab synthetic backtest pipeline demonstration (offline, synthetic data, "
          "not a strategy test)", flush=True)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workdir", type=Path, default=None,
                        help="keep the outputs and demo_summary.json in this new or empty directory")
    args = parser.parse_args(argv)
    if args.workdir is not None and args.workdir.exists() and (not args.workdir.is_dir() or any(args.workdir.iterdir())):
        parser.error(f"--workdir must be a new or empty directory: {args.workdir}")
    try:
        import moneylab  # noqa: F401
    except ImportError:
        print("FAILED: moneylab is not importable; install it first: pip install -r requirements-dev.txt and "
              "pip install -e . --no-deps (see README, Getting Started)")
        return EXIT_FAILED

    with tempfile.TemporaryDirectory(prefix="moneylab-demo-", ignore_cleanup_errors=True) as tmp:
        work = args.workdir if args.workdir is not None else Path(tmp) / "work"
        demo = Demo(work)
        try:
            work.mkdir(parents=True, exist_ok=True)
            status = demo.run()
        except Exception as exc:  # last-resort guard: any ordinary error ends as FAILED, never as success
            status = demo.fail(describe_error(exc), detail=f"{type(exc).__name__}: {exc}")
        code = {COMPLETE: EXIT_COMPLETE, PARTIAL: EXIT_PARTIAL}.get(status, EXIT_FAILED)
        demo.summary.update(demo_status=status, exit_code=code)
        # The summary is written before the final status is printed, so a failed write can only end as FAILED.
        written = False
        if args.workdir is not None:
            try:
                (work / "demo_summary.json").write_text(json.dumps(demo.summary, indent=2) + "\n", encoding="utf-8")
                written = True
            except OSError as exc:
                status = demo.fail(f"demo_summary.json could not be written: {describe_error(exc)}",
                                   detail=f"demo_summary.json could not be written: {type(exc).__name__}: {exc}")
                code = EXIT_FAILED
                demo.summary.update(demo_status=status, exit_code=code)
        print_summary(demo.summary)
        if written:
            print(f"outputs kept in {work} (demo_summary.json)")
        elif args.workdir is not None:
            print(f"outputs kept in {work}; demo_summary.json was not written")
    return code


if __name__ == "__main__":
    sys.exit(main())
