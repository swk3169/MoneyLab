"""REAL Upbit public WebSocket smoke test (network). Skipped by default; run with:

    .\\.venv\\Scripts\\python.exe -m pytest -m network tests/test_upbit_live_smoke.py -s

Connects to the documented public endpoint for KRW-BTC orderbook(30) + trade, records for
UPBIT_SMOKE_SECONDS (default 60) into a temporary directory, then replays and compares.
Public market data only: no key, no account, no order.
"""

import os

import pytest

from moneylab.paper.book_stream import ReplayBookStream
from moneylab.providers.upbit import WS_PUBLIC_URL, websockets_connector
from moneylab.providers.upbit.recorder import (
    UpbitRecorder,
    UpbitRecorderConfig,
    UpbitRecordingReader,
    replay_check,
    verify_upbit_recording,
)
from moneylab.recording.core import RecorderStatus

pytestmark = pytest.mark.network


def test_live_krw_btc_record_and_replay(tmp_path):
    seconds = float(os.getenv("UPBIT_SMOKE_SECONDS", "60"))
    cfg = UpbitRecorderConfig(markets=("KRW-BTC",), orderbook_units=30, duration=seconds, ping_text_interval=20.0)
    rep = UpbitRecorder(websockets_connector(), WS_PUBLIC_URL, tmp_path, cfg, provenance="real").run()
    assert rep.status == RecorderStatus.COMPLETED, rep.last_error
    assert rep.orderbook_events > 0 and rep.trade_events > 0
    assert rep.pings_sent >= 1 and rep.status_replies >= 1  # documented keep-alive answered
    ds = tmp_path / "KRW-BTC"
    assert verify_upbit_recording(ds).ok
    reader = UpbitRecordingReader(ds)
    assert reader.provenance == "real" and reader.synthetic is False
    books = trades = 0
    for ev in ReplayBookStream(reader):
        if ev.snapshot:
            b = ev.snapshot.books["KRW-BTC"]
            assert b.best_bid < b.best_ask and b.spread > 0
            books += 1
        for t in ev.trades:
            assert t.price > 0 and t.volume > 0 and t.side in ("buy", "sell")
            trades += 1
    assert books > 0 and trades > 0
    check = replay_check(ds)
    assert check.ok, check.mismatches
