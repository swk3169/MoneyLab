"""Read-only Polymarket market-data recorder and replay (v0.3).

    Recorder (REST now, WebSocket later) -> dataset on disk -> RecordingReader -> ReplayBookStream

No orders, signing, wallets or credentials anywhere in this package.
"""

from moneylab.providers.polymarket.recorder.base import (
    PolymarketRecorder,
    RecorderConfig,
    RecorderReport,
    RecorderStatus,
    SourceExhausted,
)
from moneylab.providers.polymarket.recorder.fixture_source import TimelineFixtureSource
from moneylab.providers.polymarket.recorder.integrity import IntegrityReport, verify_recording
from moneylab.providers.polymarket.recorder.replay import RecordingReader, open_recording
from moneylab.providers.polymarket.recorder.rest import RestBookRecorder
from moneylab.providers.polymarket.recorder.store import DatasetMismatch, RecordingStore

__all__ = [
    "DatasetMismatch", "IntegrityReport", "PolymarketRecorder", "RecorderConfig", "RecorderReport",
    "RecorderStatus", "RecordingReader", "RecordingStore", "RestBookRecorder", "SourceExhausted",
    "TimelineFixtureSource", "open_recording", "verify_recording",
]
