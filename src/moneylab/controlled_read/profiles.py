"""D9-D11 and AUTO-12 N2: the fixed ECON-FWD-M20 profiles and the shared normalization.

Only the profiles in PROFILES exist. Another document needs a new Work Order or ERRATA: no profile or marker is added
or guessed at run time. A marker line is a line that equals the marker constant byte for byte; anything
else (indentation, trailing space, quotes, other case) is body text."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from moneylab.controlled_read import ControlledReadError

TEXT_LIMIT = 2 * 1024 * 1024  # D12: UTF-8 bytes of the selected text
BODY_LIMIT = 1 * 1024 * 1024  # D12: bytes of the extracted body


@dataclass(frozen=True)
class Profile:
    id: str
    version: int
    begin: bytes
    end: bytes
    kinds: frozenset[str]  # selector kinds this profile accepts
    trim_empty_edges: bool  # D10 drops the outer zero-length lines; D11 keeps every line
    # AUTO-12 N2: skip a tool_result content item whose type is a string other than "text" when the bounded
    # scan of transcript.NontextPolicy finds no marker in it. False keeps the S4d rule for such an item.
    skip_marker_free_nontext: bool = False


WORK_ORDER = Profile(
    id="ECON-FWD-M20-WO/1", version=1,
    begin=b"-----BEGIN ECON-FWD-M20 WORK ORDER CANDIDATE-----",
    end=b"-----END ECON-FWD-M20 WORK ORDER CANDIDATE-----",
    kinds=frozenset({"assistant", "tool_result"}), trim_empty_edges=True)
PREREGISTRATION = Profile(
    id="ECON-FWD-M20-PREREG/1", version=1,
    begin=b"===== FINAL BODY BEGIN =====",
    end=b"===== FINAL BODY END =====",
    kinds=frozenset({"tool_result"}), trim_empty_edges=False)
# AUTO-12-CONTROLLED-READ-NONTEXT N2: ECON-FWD-M20-WO/2 (version 2). Its begin, end, kinds and
# trim_empty_edges values are those written below; it differs from ECON-FWD-M20-WO/1 in
# skip_marker_free_nontext=True, so its candidates, its uniqueness and its PRECHECK_OK mean less:
# (a) A candidate is only a supported single text string (an assistant text block, a tool_result string
#     content, or a content array item with type == "text") that has a BEGIN or END marker line under the
#     existing rule (marker_line_present: a whole line equal to the marker).
# (b) Items are never joined, attachments are never interpreted and nothing is decoded further.
# (c) Uniqueness under /2 holds only within the scope of (a); it does not mean the marker is unique in the
#     whole non-text content.
# (d) The non-text scan only checks the conditions that refuse a skip (a whole marker in a key or string
#     value: S4e; a scan limit: S4f). It neither supports nor validates non-text content.
WORK_ORDER_V2 = Profile(
    id="ECON-FWD-M20-WO/2", version=2,
    begin=b"-----BEGIN ECON-FWD-M20 WORK ORDER CANDIDATE-----",
    end=b"-----END ECON-FWD-M20 WORK ORDER CANDIDATE-----",
    kinds=frozenset({"assistant", "tool_result"}), trim_empty_edges=True, skip_marker_free_nontext=True)
PROFILES: dict[str, Profile] = {p.id: p for p in (WORK_ORDER, PREREGISTRATION, WORK_ORDER_V2)}


def check_kind(profile: Profile, kind: str) -> None:
    if kind not in profile.kinds:
        raise ControlledReadError("SELECTOR_KIND_MISMATCH")


def encode_text(text: str) -> bytes:
    """D9 (a) and the D12 text limit."""
    try:
        data = text.encode("utf-8")
    except UnicodeEncodeError:
        raise ControlledReadError("ENCODING_INVALID") from None
    if len(data) > TEXT_LIMIT:
        raise ControlledReadError("TEXT_LIMIT_EXCEEDED")
    return data


def _marker_index(lines: list[bytes], marker: bytes) -> int:
    found = [index for index, line in enumerate(lines) if line == marker]
    if not found:
        raise ControlledReadError("MARKER_MISSING")
    if len(found) > 1:
        raise ControlledReadError("MARKER_DUPLICATE")
    return found[0]


def extract(profile: Profile, text: str) -> bytes:
    """The approved body bytes of `text` under `profile` (D9 with D10 or D11)."""
    data = encode_text(text)
    if text.startswith("\N{ZERO WIDTH NO-BREAK SPACE}"):
        raise ControlledReadError("BOM_PRESENT")
    data = data.replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise ControlledReadError("CR_PRESENT")
    lines = data.split(b"\n")
    has_begin = profile.begin in lines
    has_end = profile.end in lines
    if not (has_begin and has_end):
        raise ControlledReadError("MARKER_MISSING")
    begin = _marker_index(lines, profile.begin)
    end = _marker_index(lines, profile.end)
    if end < begin:
        raise ControlledReadError("MARKER_ORDER_INVALID")
    body_lines = lines[begin + 1:end]  # every line here was followed by an LF in the text
    if profile.trim_empty_edges:
        while body_lines and body_lines[0] == b"":
            body_lines.pop(0)
        while body_lines and body_lines[-1] == b"":
            body_lines.pop()
    if not body_lines:
        raise ControlledReadError("BODY_EMPTY")
    body = b"".join(line + b"\n" for line in body_lines)
    if len(body) > BODY_LIMIT:
        raise ControlledReadError("BODY_LIMIT_EXCEEDED")
    return body


def marker_line_present(profile: Profile, text: str) -> bool:
    """AUTO-09 D5: True when a line of `text` (CRLF read as LF) equals the BEGIN or END marker exactly.
    No limit or encoding check: this only marks a precheck candidate, it does not validate the block."""
    begin = profile.begin.decode("ascii")
    end = profile.end.decode("ascii")
    return any(line in (begin, end) for line in text.replace("\r\n", "\n").split("\n"))


def values(body: bytes) -> dict[str, object]:
    """D9 (g)."""
    return {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "lf": body.count(b"\n")}
