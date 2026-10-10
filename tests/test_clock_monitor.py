"""Read-only clock monitor: w32tm parsing (any locale), malformed/failed responses, quality
classification, summary fields and the JSONL log. No real w32tm call (runner is faked)."""

import json
import subprocess

import pytest

from moneylab.core.clock_monitor import (
    CLOCK_UNSTABLE,
    OK,
    UNKNOWN,
    WARNING,
    ClockMonitor,
    ClockSample,
    ClockThresholds,
    classify,
    measure_offset,
    parse_stripchart,
    read_log,
    summarize,
)
from moneylab.research.config import load_config

KOREAN = ("time.windows.com[192.0.2.1:123] 추적 중\n5개 샘플 수집 중\n현재 시간은 2026-10-06 오후 9:11:05입니다.\n"
          "21:11:05, -00.1475167s\n21:11:07, -00.1476631s\n21:11:09, 오류: 0x800705B4\n21:11:11, +00.0012000s\n")


def fake_runner(stdout: bytes = b"", rc: int = 0, exc: Exception | None = None):
    calls = []

    def run(args, **kw):
        calls.append(args)
        if exc is not None:
            raise exc
        return subprocess.CompletedProcess(args, rc, stdout=stdout, stderr=b"")
    run.calls = calls
    return run


def sample(t, off, status="ok"):
    return ClockSample(t, "x", "w32tm:test", status, off, 3 if off is not None else 0)


def test_parse_stripchart_any_locale_and_skips_error_lines():
    assert parse_stripchart(KOREAN) == pytest.approx([-0.1475167, -0.1476631, 0.0012])
    assert parse_stripchart("garbage\nno data here") == []


def test_measure_offset_uses_w32tm_read_only_and_median():
    run = fake_runner(KOREAN.encode("cp949"))
    s = measure_offset("time.windows.com", 3, runner=run, clock=lambda: 1000.0)
    assert run.calls == [["w32tm", "/stripchart", "/computer:time.windows.com", "/samples:3", "/dataonly"]]
    assert not any(a in ("/resync", "/config", "/register") for a in run.calls[0])  # never changes the clock
    assert s.measurement_status == "ok" and s.samples == 3
    assert s.measured_offset_ms == pytest.approx(-147.5167) and s.spread_ms == pytest.approx(1.2 + 147.6631)


@pytest.mark.parametrize("runner, status", [
    (fake_runner(b"\xc1\xa2\xb1\xd9 \xbf\xc0\xb7\xf9", rc=0), "unparseable"),
    (fake_runner(b"error: 0x800705B4", rc=1), "error"),
    (fake_runner(exc=subprocess.TimeoutExpired(["w32tm"], 60)), "timeout"),
    (fake_runner(exc=FileNotFoundError("w32tm")), "unavailable"),
])
def test_malformed_or_failed_responses_become_samples_not_exceptions(runner, status):
    s = measure_offset(runner=runner, clock=lambda: 5.0)
    assert s.measurement_status == status and s.measured_offset_ms is None and s.detail


def test_classification_thresholds():
    th = ClockThresholds()
    assert classify([], th) == UNKNOWN
    assert classify([sample(0, -50), sample(120, -90)], th) == OK
    assert classify([sample(0, -50), sample(120, -101)], th) == WARNING
    # > 250 ms but not yet sustained for 10 minutes / 3 measurements
    assert classify([sample(0, -260), sample(240, -270), sample(480, -280)], th) == WARNING
    assert classify([sample(0, -260), sample(300, -270), sample(600, -280)], th) == CLOCK_UNSTABLE
    # interrupted by a good measurement: the run restarts
    assert classify([sample(0, -260), sample(300, -100), sample(600, -280), sample(700, -290)], th) == WARNING
    # a step bigger than 250 ms between two measurements
    assert classify([sample(0, -200), sample(120, 100)], th) == CLOCK_UNSTABLE
    # failed measurements are ignored; only failures -> UNKNOWN; stale -> UNKNOWN
    assert classify([sample(0, None, "timeout")], th) == UNKNOWN
    assert classify([sample(0, -10)], th, now=10_000) == UNKNOWN


def test_thresholds_match_the_preregistered_config():
    cfg = load_config()
    th = ClockThresholds()
    assert (th.warn_ms, th.unstable_ms, th.unstable_seconds, th.unstable_min_measurements, th.stale_seconds) == (
        cfg.clock_warn_ms, cfg.clock_unstable_ms, cfg.clock_unstable_seconds, cfg.clock_unstable_min_measurements,
        cfg.clock_stale_seconds)


def test_summary_fields_and_drift():
    s = summarize([sample(0, -6.0), sample(1000, -44.0), sample(2000, -82.0), sample(2100, None, "error")])
    assert s["clock_offset_start_ms"] == -6.0 and s["clock_offset_end_ms"] == -82.0
    assert s["clock_offset_min_ms"] == -82.0 and s["clock_offset_max_ms"] == -6.0
    assert s["clock_offset_median_ms"] == -44.0
    assert s["clock_measurements"] == 4 and s["clock_measurements_ok"] == 3
    assert s["clock_drift_ppm"] == pytest.approx(-38.0)  # -38 ms per 1000 s
    assert s["clock_quality_status"] == OK and "negative: local clock ahead" in s["clock_sign_convention"]


def test_monitor_log_is_jsonl_and_resumes(tmp_path):
    offsets = iter([-10.0, -120.0])
    log_path = tmp_path / "ds" / "clock_monitor.jsonl"
    m = ClockMonitor(log_path, measure=lambda: sample(1.0, next(offsets)))
    m.measure_once()
    m.measure_once()
    lines = [json.loads(x) for x in log_path.read_text(encoding="utf-8").splitlines()]
    assert [x["measured_offset_ms"] for x in lines] == [-10.0, -120.0]
    assert set(lines[0]) >= {"timestamp", "measured_offset_ms", "source", "measurement_status"}
    again = ClockMonitor(log_path, measure=lambda: sample(2.0, -5.0))
    assert len(again.history) == 2 and len(read_log(log_path)) == 2
    assert m.summary()["clock_quality_status"] == WARNING


def test_monitor_thread_start_stop_and_never_raises(tmp_path):
    def boom():
        raise RuntimeError("w32tm exploded")
    m = ClockMonitor(tmp_path / "c.jsonl", interval=0.01, measure=boom).start()
    m.stop(final_measurement=True)  # errors are logged, not raised
    assert m.history == []
