"""Masking of secrets and personal data before anything is printed, logged or saved.

Applied to log records, HTTP diagnostics and diagnostic reports. It is a safety net:
the primary rule is that secrets are never passed to these code paths at all.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping

MASK = "***REDACTED***"

SENSITIVE_HEADERS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "poly-api-key",
    "poly_api_key",
    "poly-signature",
    "poly_signature",
    "poly-passphrase",
    "poly_passphrase",
    "cf-connecting-ip",
    "x-forwarded-for",
    "x-real-ip",
    "true-client-ip",
}

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # 32-byte hex keys (EVM private keys). Shorter 0x values (addresses, tx hashes
    # are 20/32 bytes too) - we accept masking 32-byte hashes as a false positive.
    (re.compile(r"\b(0x)?[0-9a-fA-F]{64}\b"), MASK),
    # key=value / "key": "value" pairs with sensitive names
    (
        re.compile(
            r"(?i)\b(private[_-]?key|secret|passphrase|api[_-]?key|seed|mnemonic|password|(?:access|refresh|auth)[_-]?token)"
            r"(\"?\s*[:=]\s*\"?)([^\s\"',&]+)"
        ),
        r"\1\2" + MASK,
    ),
    # IPv4 addresses (public IP is personal data)
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "x.x.x.x"),
    # IPv6 (loose)
    (re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}\b"), "x:x:x:x"),
]

# 12/24-word seed phrases: long runs of lowercase words only
_SEED_RE = re.compile(r"\b(?:[a-z]{3,8}\s+){11,23}[a-z]{3,8}\b")


def redact_text(text: str) -> str:
    if not text:
        return text
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return _SEED_RE.sub(MASK, text)


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        k: (MASK if k.lower() in SENSITIVE_HEADERS else redact_text(str(v)))
        for k, v in headers.items()
    }


class RedactingFilter(logging.Filter):
    """Logging filter that masks secrets in the final formatted message."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redact_text(record.getMessage())
            record.args = None
        except Exception:  # never let logging break the program
            pass
        return True
