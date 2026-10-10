"""Long-run safety of the Upbit recorder over SYNTHETIC scripted sessions: termination reasons,
final buffer flush, state + capture manifest finalization (raw hashes), disk-low stop, clock
monitor hook, heartbeat counters and the SIGBREAK/SIGTERM handler. No network."""

import random
import signal
import sys

import pytest

from moneylab.providers.upbit.endpoints import WS_PUBLIC_URL
from moneylab.providers.upbit.recorder import UpbitRecorder, UpbitRecorderConfig
from moneylab.providers.upbit.recorder.store import CAPTURE_MANIFEST, raw_file_manifest, read_json
from moneylab.recording import shutdown as term
from moneylab.recording.core import RecorderStatus
from upbit_helpers import T0, book, frames, lines, scripted, trade

GB = 10**9


def session(n=60, step=0.1):
    items = []
    for i in range(n):
        items.append(book(1_800_000_000_000 + 100 * i, bid=100.0, ask=101.0))
        if i % 5 == 0:
            items.append(trade(i + 1, 1_800_000_000_000 + 100 * i))
    return scripted([{"frames": frames(*items, step=step), "ping_reply": True}])


class Hooked(UpbitRecorder):
    """Calls `action(self)` when the n-th frame arrives (simulates a signal / crash mid-run)."""

    def __init__(self, *a, at=10, action=None, **kw):
        super().__init__(*a, **kw)
        self._at, self._action, self._n = at, action, 0

    def _handle_frame(self, frame, received, conn_id):
        self._n += 1
        if self._n == self._at and self._action:
            self._action(self)
        return super()._handle_frame(frame, received, conn_id)


def make(src, out, cls=UpbitRecorder, disk_free=lambda p: 500 * GB, **kw):
    cfg = {k: kw.pop(k) for k in list(kw) if k in UpbitRecorderConfig.__dataclass_fields__}
    cfg.setdefault("orderbook_units", 1)
    cfg.setdefault("flush_interval", 1000.0)  # keep everything buffered: the final flush must save it
    return cls(src, WS_PUBLIC_URL, out, UpbitRecorderConfig(**cfg), provenance="fixture", origin="fixture:t",
               clock=src.clock, sleep=src.sleep, rng=random.Random(1), ticket_factory=lambda: "t",
               disk_free=disk_free, **kw)


def capture(out):
    return read_json(out / "KRW-BTC" / CAPTURE_MANIFEST)


def test_sigbreak_style_stop_flushes_buffer_and_finalizes_state_and_manifest(tmp_path):
    src = session()
    rec = make(src, tmp_path, cls=Hooked, at=20, action=lambda r: r.stop(term.SIGBREAK))
    rep = rec.run()
    assert rep.status == RecorderStatus.STOPPED and rep.termination_reason == term.SIGBREAK
    on_disk = lines(tmp_path)
    assert sum(1 for ln in on_disk if ln["event_type"] in ("orderbook", "trade")) == 20  # nothing lost
    state = read_json(tmp_path / "KRW-BTC" / "state.json")
    assert state["termination_reason"] == term.SIGBREAK and state["runs"][-1]["termination_reason"] == term.SIGBREAK
    assert state["last_seq"] == len(on_disk)
    cm = capture(tmp_path)
    run = cm["runs"][-1]
    assert run["final"] is True and run["termination_reason"] == term.SIGBREAK
    assert cm["raw_manifest_sha256"] == raw_file_manifest(tmp_path / "KRW-BTC")["manifest_sha256"]
    assert run["disk_free_start_bytes"] == 500 * GB and run["disk_free_end_bytes"] == 500 * GB


def test_keyboard_interrupt_is_graceful(tmp_path):
    def interrupt(r):
        raise KeyboardInterrupt
    rep = make(session(), tmp_path, cls=Hooked, at=15, action=interrupt).run()
    assert rep.termination_reason == term.KEYBOARD_INTERRUPT and rep.status == RecorderStatus.STOPPED
    assert sum(1 for ln in lines(tmp_path) if ln["event_type"] in ("orderbook", "trade")) == 14
    assert capture(tmp_path)["runs"][-1]["final"] is True


def test_unexpected_error_still_flushes_and_records_reason(tmp_path):
    def crash(r):
        raise RuntimeError("boom")
    rep = make(session(), tmp_path, cls=Hooked, at=12, action=crash).run()
    assert rep.status == RecorderStatus.FAILED and rep.termination_reason == term.UNEXPECTED_ERROR
    assert "boom" in rep.last_error["message"]
    assert sum(1 for ln in lines(tmp_path) if ln["event_type"] in ("orderbook", "trade")) == 11
    assert capture(tmp_path)["runs"][-1]["termination_reason"] == term.UNEXPECTED_ERROR


def test_disk_low_stops_gracefully(tmp_path):
    free = iter([500 * GB, 500 * GB] + [1 * GB] * 1000)
    rep = make(session(200), tmp_path, disk_free=lambda p: next(free), disk_check_interval=2.0).run()
    assert rep.termination_reason == term.DISK_LOW and rep.status == RecorderStatus.STOPPED
    assert rep.disk_free_start == 500 * GB and rep.disk_free_end == 1 * GB
    assert any("below" in w for w in rep.warnings)
    assert capture(tmp_path)["runs"][-1]["min_free_bytes"] == 5 * 1024**3


def test_completed_and_connection_failure_reasons(tmp_path):
    rep = make(session(30), tmp_path / "a", duration=1.5).run()
    assert rep.status == RecorderStatus.COMPLETED and rep.termination_reason == term.COMPLETED
    src = scripted([{"handshake": {"status": 451, "reason": "x", "headers": {}, "body": "blocked"}}])
    rep2 = make(src, tmp_path / "b").run()
    assert rep2.termination_reason == term.CONNECTION_FAILURE


class FakeMonitor:
    def __init__(self, status="CLOCK_UNSTABLE"):
        self._status, self.stopped = status, False

    @property
    def status(self):
        return self._status

    def summary(self):
        return {"clock_quality_status": self._status, "clock_offset_end_ms": -300.0, "clock_measurements": 3}

    def stop(self, final_measurement=True):
        self.stopped = True


def test_clock_unstable_stops_only_when_enabled_and_is_reported(tmp_path):
    mon = FakeMonitor()
    rep = make(session(), tmp_path / "a", clock_monitor=mon, stop_on_clock_unstable=True).run()
    assert rep.termination_reason == term.CLOCK_UNSTABLE and mon.stopped
    assert rep.clock["clock_quality_status"] == "CLOCK_UNSTABLE"
    mon2 = FakeMonitor()
    rep2 = make(session(), tmp_path / "b", clock_monitor=mon2).run()  # default: report, keep recording
    assert rep2.termination_reason == term.SOURCE_EXHAUSTED and mon2.stopped
    assert capture(tmp_path / "b")["runs"][-1]["clock"]["clock_quality_status"] == "CLOCK_UNSTABLE"


def test_heartbeat_and_quality_counters(tmp_path):
    items = [book(1_800_000_000_000, 100.0, 101.0), book(1_800_000_000_100, 101.0, 101.0),  # locked
             book(1_800_000_000_200, 102.0, 101.0)]  # crossed
    fr = frames(*items, step=0.1)
    fr.append({"t": T0 + 2.5, "raw": book(1_800_000_002_500)})  # 2.2 s after the last book: stale
    fr.append({"t": T0 + 14.0, "raw": book(1_800_000_014_000)})  # 11.5 s silence: gap (+ stale)
    fr += [{"t": T0 + 14.0 + 0.1 * i, "raw": book(1_800_000_014_000 + 100 * i)} for i in range(1, 80)]
    rep = make(scripted([{"frames": fr, "ping_reply": True}]), tmp_path, status_interval=3.0).run()
    assert rep.locked_books == 1 and rep.crossed_books == 1
    assert rep.stale_books == 2 and rep.gaps == 1
    assert rep.heartbeats >= 2 and rep.last_heartbeat["books"] > 0
    hb = capture(tmp_path)["runs"][-1]["last_heartbeat"]
    assert set(hb) >= {"runtime_seconds", "books", "trades", "reconnects", "gaps", "stale_books", "crossed_books",
                       "locked_books", "disk_free_bytes", "clock_quality_status"}


def test_raw_line_format_is_unchanged_by_the_new_counters(tmp_path):
    make(session(10), tmp_path).run()
    ob = next(ln for ln in lines(tmp_path) if ln["event_type"] == "orderbook")
    assert not {"crossed", "stale", "gap", "termination_reason"} & set(ob)


@pytest.mark.skipif(not hasattr(signal, "SIGBREAK"), reason="SIGBREAK exists only on Windows")
def test_sigbreak_handler_routes_to_stop_on_windows():
    seen = []
    restore = term.install_stop_signals(seen.append)
    try:
        handler = signal.getsignal(signal.SIGBREAK)
        assert callable(handler) and handler not in (signal.SIG_DFL, signal.SIG_IGN)
        signal.raise_signal(signal.SIGBREAK)
    finally:
        restore()
    assert seen == [term.SIGBREAK]
    assert signal.getsignal(signal.SIGBREAK) is not handler  # previous handler restored


def test_stop_signals_degrade_gracefully_off_main_thread():
    import threading

    out = []
    t = threading.Thread(target=lambda: out.append(term.install_stop_signals(lambda r: None)))
    t.start()
    t.join()
    out[0]()  # restore is a no-op, nothing raised
    assert ("SIGBREAK" in term.available_stop_signals()) == (sys.platform == "win32")
