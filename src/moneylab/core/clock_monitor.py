"""Read-only local clock quality monitor (Windows `w32tm /stripchart`).

Measures the offset of the local clock against an NTP server with the operating system's own
tool and records it. It NEVER adjusts the system clock and its numbers are never used to correct
timestamps, features or labels: they are quality metadata only.

Sign convention (same as w32tm): offset_ms = reference - local.
  negative -> the local clock is AHEAD of the reference (receive times are stamped too late).
A measurement runs `w32tm /stripchart /computer:<server> /samples:<n> /dataonly` and takes the
median of the parsed sample lines ("HH:MM:SS, -00.1475167s"); lines with errors are ignored.
w32tm sends NTP (UDP 123) itself; MoneyLab opens no socket for it.

Quality status (pre-registered thresholds, configs/research_v04.toml [clock]):
  OK              every successful |offset| <= warn_ms
  WARNING         some successful |offset| > warn_ms (100 ms)
  CLOCK_UNSTABLE  |offset| > unstable_ms (250 ms) for every successful measurement over at least
                  `unstable_seconds` (600 s) and at least `unstable_min_measurements` (3)
                  consecutive measurements; or a step between two measurements > unstable_ms
  UNKNOWN         no successful measurement, or none for longer than `stale_seconds`
"""

from __future__ import annotations

import json
import logging
import re
import statistics
import subprocess
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from moneylab.storage.atomic import atomic_write_text

log = logging.getLogger(__name__)

OK, WARNING, CLOCK_UNSTABLE, UNKNOWN = "OK", "WARNING", "CLOCK_UNSTABLE", "UNKNOWN"
SIGN_CONVENTION = "offset_ms = reference - local (negative: local clock ahead)"
_LINE = re.compile(r"^\s*\d{1,2}:\d{2}:\d{2},\s*([+-]?\d+(?:\.\d+)?)s\s*$")

Runner = Callable[..., subprocess.CompletedProcess]


@dataclass(frozen=True)
class ClockThresholds:
    warn_ms: float = 100.0
    unstable_ms: float = 250.0
    unstable_seconds: float = 600.0
    unstable_min_measurements: int = 3
    stale_seconds: float = 1800.0


@dataclass(frozen=True)
class ClockSample:
    timestamp: float  # local clock, epoch seconds
    timestamp_iso: str
    source: str
    measurement_status: str  # ok | unparseable | error | timeout | unavailable
    measured_offset_ms: float | None = None
    samples: int = 0
    spread_ms: float | None = None  # max - min of the parsed samples
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_stripchart(text: str) -> list[float]:
    """Offsets in SECONDS from the data lines of `w32tm /stripchart /dataonly` (any locale)."""
    out = []
    for line in text.splitlines():
        m = _LINE.match(line)
        if m:
            out.append(float(m.group(1)))
    return out


def _decode(raw: bytes) -> str:
    for enc in ("utf-8", "cp949", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def measure_offset(server: str = "time.windows.com", samples: int = 3, *, runner: Runner = subprocess.run,
                   clock: Callable[[], float] = time.time, timeout: float = 60.0) -> ClockSample:
    """One read-only measurement. Never raises: failures become a sample with a status."""
    now = clock()
    iso = datetime.fromtimestamp(now, UTC).isoformat()
    source = f"w32tm:{server}"
    args = ["w32tm", "/stripchart", f"/computer:{server}", f"/samples:{int(samples)}", "/dataonly"]
    try:
        r = runner(args, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return ClockSample(now, iso, source, "timeout", detail=f"w32tm did not finish in {timeout:g}s")
    except (OSError, ValueError) as exc:
        return ClockSample(now, iso, source, "unavailable", detail=f"{type(exc).__name__}: {exc}")
    raw = r.stdout if isinstance(r.stdout, bytes) else (r.stdout or "").encode()
    offsets = parse_stripchart(_decode(raw))
    if not offsets:
        status = "error" if r.returncode else "unparseable"
        tail = _decode(raw).strip().splitlines()[-1:] if raw else []
        return ClockSample(now, iso, source, status, detail=f"rc={r.returncode} {' '.join(tail)[:200]}")
    ms = [o * 1000.0 for o in offsets]
    return ClockSample(now, iso, source, "ok", measured_offset_ms=statistics.median(ms), samples=len(ms),
                       spread_ms=max(ms) - min(ms))


def classify(samples: Sequence[ClockSample], thresholds: ClockThresholds = ClockThresholds(),
             now: float | None = None) -> str:
    good = [s for s in samples if s.measurement_status == "ok" and s.measured_offset_ms is not None]
    if not good:
        return UNKNOWN
    t = thresholds
    for a, b in zip(good, good[1:]):
        if abs(b.measured_offset_ms - a.measured_offset_ms) > t.unstable_ms:
            return CLOCK_UNSTABLE  # a clock step larger than the instability threshold
    run: list[ClockSample] = []
    for s in good:
        if abs(s.measured_offset_ms) > t.unstable_ms:
            run.append(s)
            if (len(run) >= t.unstable_min_measurements
                    and run[-1].timestamp - run[0].timestamp >= t.unstable_seconds):
                return CLOCK_UNSTABLE
        else:
            run = []
    if now is not None and now - good[-1].timestamp > t.stale_seconds:
        return UNKNOWN
    if any(abs(s.measured_offset_ms) > t.warn_ms for s in good):
        return WARNING
    return OK


def summarize(samples: Sequence[ClockSample], thresholds: ClockThresholds = ClockThresholds()) -> dict[str, Any]:
    """Manifest fields. drift_ppm = least-squares slope of offset over time (quality metadata)."""
    good = [s for s in samples if s.measurement_status == "ok" and s.measured_offset_ms is not None]
    offs = [s.measured_offset_ms for s in good]
    drift = None
    if len(good) >= 2 and good[-1].timestamp > good[0].timestamp:
        ts = [s.timestamp for s in good]
        mt, mo = statistics.fmean(ts), statistics.fmean(offs)
        sxx = sum((x - mt) ** 2 for x in ts)
        if sxx > 0:
            slope_ms_per_s = sum((x - mt) * (y - mo) for x, y in zip(ts, offs)) / sxx
            drift = slope_ms_per_s * 1000.0  # ms/s -> ppm (1e-6 s/s = 1e-3 ms/s)
    return {
        "clock_offset_start_ms": offs[0] if offs else None,
        "clock_offset_end_ms": offs[-1] if offs else None,
        "clock_offset_min_ms": min(offs) if offs else None,
        "clock_offset_max_ms": max(offs) if offs else None,
        "clock_offset_median_ms": statistics.median(offs) if offs else None,
        "clock_measurements": len(samples),
        "clock_measurements_ok": len(good),
        "clock_drift_ppm": drift,
        "clock_quality_status": classify(samples, thresholds),
        "clock_sign_convention": SIGN_CONVENTION,
        "clock_source": good[0].source if good else (samples[0].source if samples else None),
        "clock_thresholds": asdict(thresholds),
    }


def read_log(path: Path) -> list[ClockSample]:
    out = []
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(ClockSample(**json.loads(line)))
    return out


@dataclass
class ClockMonitor:
    """Measures every `interval` seconds in a daemon thread and rewrites `log_path` atomically
    (JSON lines, one per measurement). `status` is safe to read from other threads."""

    log_path: Path
    server: str = "time.windows.com"
    interval: float = 120.0
    samples_per_measurement: int = 3
    thresholds: ClockThresholds = field(default_factory=ClockThresholds)
    measure: Callable[[], ClockSample] | None = None
    history: list[ClockSample] = field(default_factory=list)

    def __post_init__(self):
        self.log_path = Path(self.log_path)
        self.history = read_log(self.log_path)  # resume: keep earlier measurements of this dataset
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if self.measure is None:
            self.measure = lambda: measure_offset(self.server, self.samples_per_measurement)

    @property
    def status(self) -> str:
        with self._lock:
            return classify(self.history, self.thresholds, now=time.time())

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return summarize(list(self.history), self.thresholds)

    def measure_once(self) -> ClockSample:
        s = self.measure()
        with self._lock:
            self.history.append(s)
            text = "".join(json.dumps(x.to_dict(), separators=(",", ":")) + "\n" for x in self.history)
        atomic_write_text(self.log_path, text)
        if s.measurement_status != "ok":
            log.warning("clock measurement %s: %s", s.measurement_status, s.detail)
        return s

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.measure_once()
            except Exception as exc:  # the monitor must never take the recorder down
                log.warning("clock monitor error: %s", exc)
            self._stop.wait(self.interval)

    def start(self) -> ClockMonitor:
        self._thread = threading.Thread(target=self._loop, name="clock-monitor", daemon=True)
        self._thread.start()
        return self

    def stop(self, final_measurement: bool = True) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=90)
        if final_measurement:
            try:
                self.measure_once()
            except Exception as exc:
                log.warning("final clock measurement failed: %s", exc)
