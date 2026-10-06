"""Provider-neutral recording core (status, failure classification, backoff, checksums).

Must not import any `moneylab.providers.<exchange>` package (tests/test_architecture_and_cli.py).
"""

from moneylab.recording.core import (
    FATAL_STATUSES,
    Failure,
    RecorderStatus,
    SourceExhausted,
    backoff_delay,
    checksum_ok,
    classify,
    iso,
    parse_retry_after,
    with_checksum,
)

__all__ = [
    "FATAL_STATUSES", "Failure", "RecorderStatus", "SourceExhausted", "backoff_delay", "checksum_ok",
    "classify", "iso", "parse_retry_after", "with_checksum",
]
