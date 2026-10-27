"""examples/synthetic_backtest_demo.py end to end (PORTFOLIO-DEMO-01; SYNTHETIC / NOT_EVIDENCE).

The demo runs as a subprocess with sys.executable (no shell, not imported) and writes only to tmp_path. The goldens
are the cross-run deterministic artifacts of ERRATA-001: the day/hour bar hashes and four run files. result_sha256
carries timestamp-bearing provenance, so it is only checked for internal consistency, never against a fixed value.
The expected branch follows the existing code-state policy: PINNED (clean checkout) -> report, COMPLETE, exit 0;
UNPINNED (e.g. uncommitted changes) -> no report, PARTIAL_CODE_STATE_UNPINNED, exit 4. The subprocess is not
included in coverage."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from moneylab.backtest.code_state import code_state_problems
from moneylab.backtest.run import verify_run
from moneylab.cli import backtest_code_state

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "examples" / "synthetic_backtest_demo.py"
EVIDENCE = "SYNTHETIC / NOT_EVIDENCE"
GOLDEN_BARS = {"day": ("d6a40221a2c3b810d468b0f522cc2a1ef2305315f43864e0b37e7410251ec561", 199),
               "hour": ("39ad26cbb0cedfe3a647f6dc01e31d19f8bec58a9d69f460918516bad972e412", 4809)}
GOLDEN_RUN_FILES = {"daily.jsonl": "77211e81cc44b32605b0d4b1eccf02ac4a8bbb0d06dfcf9f7272ba20521578ac",
                    "metrics.json": "bc26e3f19fd7c48381bff995c74b1ee5a1fe3085bb92e16b40044fd29de971c6",
                    "trades.jsonl": "066b65f86992b11a0538c0c978088b84eae70b406c9351028f987e791c658bbb",
                    "orders.jsonl": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_status() -> bytes | None:
    """Tracked, untracked and ignored entries, so writes into data/ or src/ would show up too."""
    if shutil.which("git") is None:
        return None
    out = subprocess.run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored"], cwd=REPO,
                         capture_output=True)
    return out.stdout if out.returncode == 0 else None


def run_demo(*args: str, env: dict[str, str] | None = None, code: str | None = None) -> subprocess.CompletedProcess[str]:
    """The demo as a reviewer runs it; with `code`, a `python -c` driver instead (failure injection tests)."""
    full_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(env or {})}
    argv = [sys.executable, "-c", code, str(DEMO), *args] if code else [sys.executable, str(DEMO), *args]
    return subprocess.run(argv, cwd=REPO, env=full_env, capture_output=True, text=True, errors="replace", timeout=600)


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    work = tmp_path_factory.mktemp("demo") / "work"
    pinned = not code_state_problems(backtest_code_state())
    before = repo_status()
    proc = run_demo("--workdir", str(work))
    after = repo_status()
    summary = json.loads((work / "demo_summary.json").read_text(encoding="utf-8"))
    return {"proc": proc, "work": work, "pinned": pinned, "before": before, "after": after, "summary": summary}


def test_warning_comes_first_and_summary_is_labelled(demo):
    lines = [line for line in demo["proc"].stdout.splitlines() if line.strip()]
    assert EVIDENCE in lines[0]
    s = demo["summary"]
    assert s["schema"] == "moneylab.demo.synthetic_backtest/1" and s["evidence"] == EVIDENCE
    assert "per_run_integrity" in s and "cross_run_deterministic_artifacts" in s
    assert "result_sha256" in s["per_run_integrity"]
    assert "result_sha256" not in json.dumps(s["cross_run_deterministic_artifacts"])


def test_exit_code_and_status_follow_the_code_state(demo):
    proc, s = demo["proc"], demo["summary"]
    expected = ("COMPLETE", 0) if demo["pinned"] else ("PARTIAL_CODE_STATE_UNPINNED", 4)
    assert (s["demo_status"], proc.returncode) == expected, proc.stdout[-4000:] + proc.stderr[-2000:]
    assert s["exit_code"] == proc.returncode and s["problems"] == []
    assert s["code_state"]["classification"] == ("PINNED" if demo["pinned"] else "UNPINNED")
    assert f"DEMO_STATUS = {expected[0]}" in proc.stdout
    stages = {st["name"]: st["status"] for st in s["stages"]}
    for name in ("candles-pull day", "candles-pull hour", "bars-export day", "bars-export hour", "backtest"):
        assert stages[name] == "OK"


@pytest.mark.parametrize("interval", ["day", "hour"])
def test_bar_goldens(demo, interval):
    bars_dir = next((demo["work"] / f"bars_{interval}-fixture").iterdir())
    manifest = json.loads((bars_dir / "bars_manifest.json").read_text(encoding="utf-8"))
    assert (manifest["bars_sha256"], manifest["bars"]) == GOLDEN_BARS[interval]
    assert demo["summary"]["cross_run_deterministic_artifacts"]["bars"][interval]["match"] is True


def run_dir(demo) -> Path:
    runs = list((demo["work"] / "runs-fixture").iterdir())
    assert len(runs) == 1
    return runs[0]


def sums(run: Path) -> dict[str, str]:
    lines = (run / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    return {name.strip(): digest for digest, name in (line.split(maxsplit=1) for line in lines if line.strip())}


@pytest.mark.parametrize("name", sorted(GOLDEN_RUN_FILES))
def test_run_file_goldens(demo, name):
    run = run_dir(demo)
    assert sha256_file(run / name) == sums(run)[name] == GOLDEN_RUN_FILES[name]
    assert demo["summary"]["cross_run_deterministic_artifacts"]["run_files"][name]["match"] is True


def test_result_sha256_is_a_consistent_per_run_value(demo):
    run = run_dir(demo)
    recorded = json.loads((run / "manifest.json").read_text(encoding="utf-8"))["result_sha256"]
    assert len(recorded) == 64 and recorded == sums(run)["result.json"] == sha256_file(run / "result.json")
    p = demo["summary"]["per_run_integrity"]
    assert p["result_sha256"] == recorded and p["internally_consistent"] is True


def test_verify_checks(demo):
    v = demo["summary"]["verify"]
    assert v["non_code_ok"] is True and v["checks"]["reproducibility"] is True
    assert all(ok is not False for name, ok in v["checks"].items() if name != "code")
    assert v["checks"]["code"] is demo["pinned"]
    # independent re-verification of the produced run with the existing verification path
    rep = verify_run(run_dir(demo), code_state=backtest_code_state())
    assert {name: c["ok"] for name, c in rep.checks.items()} == v["checks"]
    assert (rep.status, rep.ok) == (v["status"], v["ok"]) and rep.ok is demo["pinned"]


def test_report_only_with_pinned_code_state(demo):
    s, reports = demo["summary"], demo["work"] / "reports-fixture"
    if demo["pinned"]:
        assert s["report"] == {"status": "OK", "report_verify": "OK"}
        report = next(reports.iterdir())
        assert {"report.json", "report.md", "report_meta.json"} <= {p.name for p in report.iterdir()}
    else:
        assert s["report"] == {"status": "SKIPPED_CODE_STATE_UNPINNED", "report_verify": "SKIPPED_CODE_STATE_UNPINNED"}
        assert not reports.exists()
        assert "requires a pinned code state" in demo["proc"].stdout


def strings(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)
    elif isinstance(value, str):
        yield value


def test_summary_has_no_machine_paths(demo):
    for text in strings(demo["summary"]):
        assert str(demo["work"]) not in text and str(REPO) not in text and not Path(text).is_absolute(), text
    assert set(demo["summary"]["paths"]) == {"bars_day", "bars_hour", "run"} | ({"report"} if demo["pinned"] else set())


def test_repository_is_unchanged(demo):
    if demo["before"] is None:
        pytest.skip("git status not available")
    assert demo["after"] == demo["before"]


# --- failure paths -----------------------------------------------------------------------------------------

ABSOLUTE = re.compile(r"\b[A-Za-z]:[\\/]|\\\\|(?<![\w.~>-])/[^\s'\"]")  # "<path>/name" is the redacted form


def test_unexpected_error_is_failed_and_its_paths_stay_out_of_the_summary(tmp_path):
    """An invalid MONEYLAB_LOG_LEVEL makes logging raise ValueError inside the first stage; the value carries
    absolute Windows and POSIX paths with spaces, none of whose directories may reach demo_summary.json."""
    work = tmp_path / "work"
    level = ("C:\\work\\First Last\\AppData\\demo.txt C:\\Program Files\\App\\demo.txt "
             "/srv/first last/data/demo.txt")
    proc = run_demo("--workdir", str(work), env={"MONEYLAB_LOG_LEVEL": level})
    assert proc.returncode == 1 and "Traceback" not in proc.stderr, proc.stderr[-2000:]
    assert "DEMO_STATUS = FAILED" in proc.stdout
    s = json.loads((work / "demo_summary.json").read_text(encoding="utf-8"))
    assert (s["demo_status"], s["exit_code"]) == ("FAILED", 1)
    assert s["problems"] == ["ValueError: Unknown level: '<path>/DEMO.TXT'"]  # the setting is upper-cased
    for text in strings(s):
        assert not ABSOLUTE.search(text) and "<path><path>" not in text, text
        for part in ("FIRST", "LAST", "APPDATA", "PROGRAM FILES", "SRV"):
            assert part not in text.upper(), text


def test_unwritable_workdir_fails_closed(tmp_path):
    blocker = tmp_path / "file.txt"
    blocker.write_text("x\n", encoding="utf-8")
    proc = run_demo("--workdir", str(blocker / "work"))
    assert proc.returncode == 1 and "Traceback" not in proc.stderr, proc.stderr[-2000:]
    assert "DEMO_STATUS = FAILED" in proc.stdout and "demo_summary.json could not be written" in proc.stdout
    assert blocker.read_text(encoding="utf-8") == "x\n"


# Test-only fault injection: a child process executes the unmodified demo file and changes one in-memory value
# before calling main(), to reach failure branches that the real pipeline cannot be made to produce from outside.
LOAD_DEMO = """
import json, sys
from pathlib import Path
demo = Path(sys.argv[1])
ns = {"__name__": "demo_under_test", "__file__": str(demo)}
exec(compile(demo.read_text(encoding="utf-8"), str(demo), "exec"), ns)
"""
WRONG_GOLDEN = LOAD_DEMO + """
ns["GOLDEN_RUN_FILES"]["daily.jsonl"] = "0" * 64
sys.exit(ns["main"](sys.argv[2:]))
"""
# After a successful pipeline, a directory takes the place of demo_summary.json, so writing the summary fails.
SUMMARY_BLOCKED = LOAD_DEMO + """
run = ns["Demo"].run
def blocked_run(self):
    status = run(self)
    (self.work / "demo_summary.json").mkdir()
    return status
ns["Demo"].run = blocked_run
sys.exit(ns["main"](sys.argv[2:]))
"""
STRIP_PATHS = LOAD_DEMO + """
cases = json.loads(sys.argv[2])
print(json.dumps({c: [ns["strip_paths"](c), ns["strip_paths"](ns["strip_paths"](c))] for c in cases}))
"""

STRIP_CASES = {
    "x 'C:\\work\\First Last\\AppData\\demo.txt'": "x '<path>/demo.txt'",
    "x 'C:/work/First Last/AppData/demo.txt'": "x '<path>/demo.txt'",
    "x 'C:\\Program Files\\App\\demo.txt'": "x '<path>/demo.txt'",
    "x '/srv/first last/data/demo.txt'": "x '<path>/demo.txt'",
    "x '\\\\host\\share\\first last\\demo.txt'": "x '<path>/demo.txt'",
    "x 'C:\\work\\First Last'": "x '<path>'",                     # a directory name is not kept
    "x C:\\Program Files\\App\\demo.txt": "x <path>",             # unquoted: redacted to the end of the line
    "x /srv/first last/data/demo.txt": "x <path>",
    "FileNotFoundError: No such file or directory (<path>/manifest.json)":
        "FileNotFoundError: No such file or directory (<path>/manifest.json)",
    "x '<path>/demo.txt'": "x '<path>/demo.txt'",
    "HTTP 429/5xx retried; see docs/x.md; a / b": "HTTP 429/5xx retried; see docs/x.md; a / b",
}


def test_strip_paths_redacts_paths_with_spaces_and_is_idempotent():
    proc = run_demo(json.dumps(list(STRIP_CASES)), code=STRIP_PATHS)
    assert proc.returncode == 0, proc.stderr[-2000:]
    got = json.loads(proc.stdout)
    for case, expected in STRIP_CASES.items():
        assert got[case] == [expected, expected], case


def test_summary_write_failure_after_the_pipeline_ends_as_failed(tmp_path):
    work = tmp_path / "work"
    proc = run_demo("--workdir", str(work), code=SUMMARY_BLOCKED)
    assert proc.returncode == 1 and "Traceback" not in proc.stderr, proc.stdout[-4000:] + proc.stderr[-2000:]
    statuses = [line for line in proc.stdout.splitlines() if line.startswith("DEMO_STATUS = ")]
    assert statuses == ["DEMO_STATUS = FAILED"]  # no COMPLETE or PARTIAL_CODE_STATE_UNPINNED terminal status
    assert "FAILED: demo_summary.json could not be written" in proc.stdout
    assert "demo_summary.json was not written" in proc.stdout and "(demo_summary.json)" not in proc.stdout
    assert (work / "demo_summary.json").is_dir() and len(list((work / "runs-fixture").iterdir())) == 1


def test_substantive_failure_is_never_reported_as_code_state(tmp_path):
    work = tmp_path / "work"
    proc = run_demo("--workdir", str(work), code=WRONG_GOLDEN)
    assert proc.returncode == 1, proc.stdout[-4000:] + proc.stderr[-2000:]
    s = json.loads((work / "demo_summary.json").read_text(encoding="utf-8"))
    assert s["demo_status"] == "FAILED"
    assert s["problems"] == ["a deterministic run artifact differs from its golden SHA-256"]
    assert s["cross_run_deterministic_artifacts"]["run_files"]["daily.jsonl"]["match"] is False
    stages = {st["name"]: st["status"] for st in s["stages"]}
    assert "CODE_STATE_UNPINNED" not in json.dumps(s["stages"]) and "SKIPPED_CODE_STATE_UNPINNED" not in json.dumps(s)
    assert stages["backtest-report"] == stages["backtest-report-verify"] == "NOT_RUN"
    assert not (work / "reports-fixture").exists()


def test_non_empty_workdir_is_an_argument_error(tmp_path):
    (tmp_path / "keep.txt").write_text("x\n", encoding="utf-8")
    proc = run_demo("--workdir", str(tmp_path))
    assert proc.returncode == 2 and EVIDENCE in proc.stdout.splitlines()[0]
    assert (tmp_path / "keep.txt").read_text(encoding="utf-8") == "x\n"
