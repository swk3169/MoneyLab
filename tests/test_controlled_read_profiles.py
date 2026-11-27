"""AUTO-08 D9-D11 and TEST_GATES P1-P10, W1-W8: the two fixed ECON-FWD-M20 profiles.

Every text goes through a synthetic session prefix (tool_result content string for PREREG, assistant text
block for WO) and then the profile. Expected bytes are fixed here as str literals; sha256, bytes and lf are
computed separately with hashlib, len and count."""

from __future__ import annotations

import hashlib
import json

import pytest

from moneylab.controlled_read import ControlledReadError, profiles, transcript
from moneylab.controlled_read.selector import parse_selector

WB = "-----BEGIN ECON-FWD-M20 WORK ORDER CANDIDATE-----"
WE = "-----END ECON-FWD-M20 WORK ORDER CANDIDATE-----"
PB = "===== FINAL BODY BEGIN ====="
PE = "===== FINAL BODY END ====="
UUID = "11111111-2222-4333-8444-555555555555"
TOOL_ID = "toolu_01"


def _prefix(entries: list[dict]) -> bytes:
    return b"".join(json.dumps(e).encode("utf-8") + b"\n" for e in entries)


def _tool_result_prefix(content: object) -> bytes:
    return _prefix([
        {"type": "assistant", "uuid": "aaaaaaaa-0000-4000-8000-000000000001",
         "message": {"content": [{"type": "tool_use", "id": TOOL_ID, "name": "Bash", "input": {}}]}},
        {"type": "user", "uuid": "aaaaaaaa-0000-4000-8000-000000000002",
         "message": {"content": [{"type": "tool_result", "tool_use_id": TOOL_ID, "content": content}]}},
    ])


def _assistant_prefix(text: str) -> bytes:
    return _prefix([
        {"type": "user", "uuid": "aaaaaaaa-0000-4000-8000-000000000003", "message": {"content": "hello"}},
        {"type": "assistant", "uuid": UUID, "message": {"content": [{"type": "text", "text": text}]}},
    ])


def prereg(text: str) -> bytes:
    sel = parse_selector(f"tool_result:{TOOL_ID}")
    profiles.check_kind(profiles.PREREGISTRATION, sel.kind)
    selected = transcript.select_text(_tool_result_prefix(text), sel, transcript.Deadline())
    return profiles.extract(profiles.PREREGISTRATION, selected)


def work_order(text: str) -> bytes:
    sel = parse_selector(f"assistant:{UUID}")
    profiles.check_kind(profiles.WORK_ORDER, sel.kind)
    selected = transcript.select_text(_assistant_prefix(text), sel, transcript.Deadline())
    return profiles.extract(profiles.WORK_ORDER, selected)


def code_of(fn, text: str) -> str:
    with pytest.raises(ControlledReadError) as info:
        fn(text)
    return info.value.code


def assert_values(body: bytes, expected: bytes) -> None:
    assert body == expected
    assert profiles.values(body) == {"sha256": hashlib.sha256(expected).hexdigest(), "bytes": len(expected),
                                     "lf": expected.count(b"\n")}


# --------------------------------------------------------------------------------- PREREG (D11)


def test_p1_crlf_body_between_markers_keeps_inner_and_final_empty_lines():
    text = "intro\r\n" + PB + "\r\n# T\r\n\r\nline  x\r\n\r\n" + PE + "\r\ntail"
    assert_values(prereg(text), "# T\n\nline  x\n\n".encode("utf-8"))


def test_p2_lone_cr_is_rejected():
    assert code_of(prereg, PB + "\na\rb\n" + PE + "\n") == "CR_PRESENT"


def test_p3_quoted_marker_inside_a_line_is_body_text():
    text = PB + "\nsee \"" + PB + "\" here\n" + PE + "\n"
    assert_values(prereg(text), ("see \"" + PB + "\" here\n").encode("utf-8"))


def test_p4_marker_with_trailing_space_is_not_a_marker():
    assert code_of(prereg, PB + " \nx\n" + PE + "\n") == "MARKER_MISSING"


def test_p5_duplicate_begin_marker():
    assert code_of(prereg, PB + "\nx\n" + PB + "\ny\n" + PE + "\n") == "MARKER_DUPLICATE"


def test_p6_end_before_begin():
    assert code_of(prereg, PE + "\nx\n" + PB + "\n") == "MARKER_ORDER_INVALID"


def test_p7_non_ascii_body_without_final_newline_after_end():
    body = prereg(PB + "\n\N{HANGUL SYLLABLE GA}\N{HANGUL SYLLABLE NA}\r\n" + PE)
    assert_values(body, "\N{HANGUL SYLLABLE GA}\N{HANGUL SYLLABLE NA}\n".encode("utf-8"))
    assert len(body) == 7 and body.count(b"\n") == 1


def test_p8_no_line_between_markers_is_empty():
    assert code_of(prereg, PB + "\n" + PE + "\n") == "BODY_EMPTY"


def test_p9_bom_is_rejected():
    assert code_of(prereg, "\N{ZERO WIDTH NO-BREAK SPACE}" + PB + "\nx\n" + PE + "\n") == "BOM_PRESENT"


def test_p10_assistant_selector_does_not_fit_prereg():
    with pytest.raises(ControlledReadError) as info:
        profiles.check_kind(profiles.PREREGISTRATION, parse_selector(f"assistant:{UUID}").kind)
    assert info.value.code == "SELECTOR_KIND_MISMATCH"


def test_prereg_empty_lines_only_are_kept():
    assert_values(prereg(PB + "\n\n\n" + PE + "\n"), "\n\n".encode("utf-8"))


# ------------------------------------------------------------------------------------- WO (D10)


def test_w1_outer_empty_lines_dropped_indent_tab_and_trailing_spaces_kept():
    text = "\n\n" + WB + "\n\n  # \N{HANGUL SYLLABLE JE}\N{HANGUL SYLLABLE MOG}\n\tx  \n\n" + WE + "\n\n"
    assert_values(work_order(text), "  # \N{HANGUL SYLLABLE JE}\N{HANGUL SYLLABLE MOG}\n\tx  \n".encode("utf-8"))


def test_w2_crlf_text():
    text = "\r\n" + WB + "\r\nA\r\n\r\nC\r\n" + WE + "\r\n"
    assert_values(work_order(text), "A\n\nC\n".encode("utf-8"))


def test_w3_only_empty_lines_is_empty():
    assert code_of(work_order, WB + "\n\n\n" + WE + "\n") == "BODY_EMPTY"


def test_w4_whitespace_only_lines_are_not_zero_length_and_stay():
    assert_values(work_order(WB + "\n \nA\n \n" + WE + "\n"), " \nA\n \n".encode("utf-8"))


def test_w5_lone_cr_is_rejected():
    assert code_of(work_order, WB + "\nA\r\rC\n" + WE + "\n") == "CR_PRESENT"


def test_w6_indented_quoted_end_marker_is_body_text():
    text = WB + "\n  " + WE + "\nA\n" + WE + "\n"
    assert_values(work_order(text), ("  " + WE + "\nA\n").encode("utf-8"))


def test_w7_quoted_begin_marker_is_body_text():
    text = WB + "\nquote \"" + WB + "\"\nA\n" + WE + "\n"
    assert_values(work_order(text), ("quote \"" + WB + "\"\nA\n").encode("utf-8"))


def test_w8_other_profile_markers_are_not_accepted():
    assert code_of(work_order, PB + "\nA\n" + PE + "\n") == "MARKER_MISSING"


def test_wo_profile_also_accepts_a_tool_result_selector():
    profiles.check_kind(profiles.WORK_ORDER, "tool_result")


def test_marker_case_and_indent_variants_are_body_text():
    for variant in (WB.lower(), " " + WB, WB + "\t", "\"" + WB + "\""):
        assert code_of(work_order, variant + "\nA\n" + WE + "\n") == "MARKER_MISSING"


# --------------------------------------------------------------------------- D9 (a), D12 limits


def test_unpaired_surrogate_is_an_encoding_error():
    assert code_of(prereg, PB + "\n\ud800\n" + PE + "\n") == "ENCODING_INVALID"


def test_text_limit(monkeypatch):
    monkeypatch.setattr(profiles, "TEXT_LIMIT", 40)
    text = PB + "\nx\n" + PE + "\n"
    assert len(text.encode("utf-8")) > 40
    assert code_of(prereg, text) == "TEXT_LIMIT_EXCEEDED"


def test_body_limit(monkeypatch):
    monkeypatch.setattr(profiles, "BODY_LIMIT", 3)
    assert prereg(PB + "\nab\n" + PE + "\n") == b"ab\n"
    assert code_of(prereg, PB + "\nabc\n" + PE + "\n") == "BODY_LIMIT_EXCEEDED"


def test_only_two_profiles_exist():
    assert {p.id: p.version for p in profiles.PROFILES.values()} == {"ECON-FWD-M20-WO/1": 1, "ECON-FWD-M20-PREREG/1": 1, "ECON-FWD-M20-WO/2": 2}
