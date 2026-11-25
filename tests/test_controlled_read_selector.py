"""AUTO-08 D2 grammar and D7-D8 selection on synthetic session prefixes (TEST_GATES: selector)."""

from __future__ import annotations

import json

import pytest

from moneylab.controlled_read import ControlledReadError, transcript
from moneylab.controlled_read.selector import (
    ASSISTANT,
    TOOL_RESULT,
    Selector,
    parse_run,
    parse_selector,
    parse_status,
)

UUID = "11111111-2222-4333-8444-555555555555"
OTHER = "99999999-2222-4333-8444-555555555555"
RUN = ["run", "--task", "ECON-FWD-M20", "--project-key", "C--MoneyLab-auto-08", "--session", UUID,
       "--selector", f"assistant:{UUID}", "--profile", "ECON-FWD-M20-WO/1", "--attempt", "001"]


def _with(index: int, value: str) -> list[str]:
    argv = list(RUN)
    argv[index] = value
    return argv


def _code(fn, *args) -> str:
    with pytest.raises(ControlledReadError) as info:
        fn(*args)
    return info.value.code


# ------------------------------------------------------------------------------------- grammar


def test_valid_run_and_status_parse():
    args = parse_run(RUN)
    assert (args.task_id, args.attempt, args.profile) == ("ECON-FWD-M20", "001", "ECON-FWD-M20-WO/1")
    assert parse_run(_with(10, "ECON-FWD-M20-PREREG/1")).profile == "ECON-FWD-M20-PREREG/1"
    assert parse_status(["status", "--task", "ECON-FWD-M20", "--attempt", "999"]).attempt == "999"


@pytest.mark.parametrize("index, value", [
    (2, "econ-fwd"), (2, "ECON--FWD"), (2, "ECON-"), (2, "1ECON"), (2, "A" * 65), (2, "ECON_FWD"),
    (4, ""), (4, "a" * 201), (4, "C:/x"), (4, "a/b"), (4, "a\\b"), (4, ".."), (4, "a.b"), (4, "a:b"),
    (6, "ABCDEF01-2222-4333-8444-555555555555"),(6, UUID[:-1]), (6, "../" + UUID), (6, UUID + "\\x"), (6, "x" + UUID),
    (8, f"assistant:{UUID}:text:0"), (8, f"assistant:{UUID}:text:100"), (8, f"assistant:{UUID}:text:01"),
    (8, "tool_result:a/b"), (8, "tool_result:" + "a" * 129), (8, "tool_result:"), (8, f"user:{UUID}"),
    (8, f"assistant:{UUID}:text:"), (8, "tool_result:a-b"),
    (10, "ECON-FWD-M20-WO/2"), (10, "econ-fwd-m20-wo/1"), (10, "ECON-FWD-M20-WO"), (10, "OTHER/1"),
    (12, "000"), (12, "1"), (12, "01"), (12, "1000"), (12, "00a"),
])
def test_value_grammar_violations(index, value):
    assert _code(parse_run, _with(index, value)) == "ARGUMENT_INVALID"


@pytest.mark.parametrize("argv", [
    RUN[:1] + RUN[3:5] + RUN[1:3] + RUN[5:],  # order changed
    RUN + ["--attempt", "002"],  # duplicate option
    RUN + ["extra"],  # extra token
    RUN[:-2],  # missing option
    ["run", "--task=ECON-FWD-M20"] + RUN[3:],  # = form
    _with(1, "--tas"),  # abbreviation
    _with(2, "\"ECON-FWD-M20\""),  # quotes left in the token
    _with(2, "ECON-FWD-M20\t"),  # tab
    _with(0, "Run"),
    [],
])
def test_structure_violations(argv):
    assert _code(parse_run, argv) == "ARGUMENT_INVALID"


@pytest.mark.parametrize("argv", [
    ["status", "--attempt", "001", "--task", "T"], ["status", "--task", "T"], ["status", "--task", "T",
                                                                                "--attempt", "001", "x"],
])
def test_status_structure_violations(argv):
    assert _code(parse_status, argv) == "ARGUMENT_INVALID"


def test_selector_forms():
    assert parse_selector(f"assistant:{UUID}") == Selector(ASSISTANT, UUID, None)
    assert parse_selector(f"assistant:{UUID}:text:99") == Selector(ASSISTANT, UUID, 99)
    assert parse_selector("tool_result:toolu_01:text:2") == Selector(TOOL_RESULT, "toolu_01", 2)


# ----------------------------------------------------------------------------------- selection


def line(obj: object) -> bytes:
    return json.dumps(obj).encode("utf-8") + b"\n"


def assistant(uuid: str, blocks: list) -> dict:
    return {"type": "assistant", "uuid": uuid, "message": {"content": blocks}}


def user_result(tool_id: str, content: object, **extra: object) -> dict:
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tool_id,
                                                      "content": content, **extra}]}}


def select(entries: list, selector: str) -> str:
    return transcript.select_text(b"".join(line(e) for e in entries), parse_selector(selector),
                                  transcript.Deadline())


def select_code(entries: list, selector: str) -> str:
    return _code(select, entries, selector)


TEXT = {"type": "text", "text": "A"}


def test_k_selects_one_block_and_out_of_range_is_not_found():
    entries = [assistant(UUID, [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}])]
    assert select(entries, f"assistant:{UUID}:text:2") == "two"
    assert select(entries, f"assistant:{UUID}:text:1") == "one"
    assert select_code(entries, f"assistant:{UUID}:text:3") == "TEXT_BLOCK_NOT_FOUND"


def test_zero_and_two_candidates_without_k():
    assert select_code([assistant(UUID, [])], f"assistant:{UUID}") == "TEXT_BLOCK_NOT_FOUND"
    assert select_code([assistant(UUID, [TEXT, TEXT])], f"assistant:{UUID}") == "TEXT_BLOCK_AMBIGUOUS"


def test_thinking_and_tool_use_blocks_are_not_candidates():
    blocks = [{"type": "thinking", "thinking": "t"}, {"type": "redacted_thinking", "data": "r"},
              {"type": "tool_use", "id": "x", "name": "Bash", "input": {}}, {"type": "text", "text": "only"}]
    assert select([assistant(UUID, blocks)], f"assistant:{UUID}") == "only"


def test_text_is_returned_as_stored_without_stripping():
    text = "     1\u2192  line\r\n"
    assert select([assistant(UUID, [{"type": "text", "text": text}])], f"assistant:{UUID}") == text


def test_tool_result_string_and_list_content():
    assert select([user_result("t1", "body")], "tool_result:t1") == "body"
    listed = [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]
    assert select([user_result("t1", listed)], "tool_result:t1:text:2") == "b"
    assert select_code([user_result("t1", listed)], "tool_result:t1") == "TEXT_BLOCK_AMBIGUOUS"
    assert select_code([user_result("t1", [])], "tool_result:t1") == "TEXT_BLOCK_NOT_FOUND"


def test_user_string_content_has_no_tool_result():
    entries = [{"type": "user", "message": {"content": "tool_result t1"}}]
    assert select_code(entries, "tool_result:t1") == "ENTRY_NOT_FOUND"


def test_duplicate_uuid():
    entries = [assistant(UUID, [TEXT]), {"type": "user", "uuid": UUID, "message": {"content": "x"}}]
    assert select_code(entries, f"assistant:{UUID}") == "ENTRY_DUPLICATE"


def test_duplicate_tool_use_id():
    assert select_code([user_result("t1", "a"), user_result("t1", "b")], "tool_result:t1") == "ENTRY_DUPLICATE"


def test_uuid_entry_that_is_not_assistant_is_a_kind_mismatch():
    entries = [{"type": "user", "uuid": UUID, "message": {"content": "x"}}]
    assert select_code(entries, f"assistant:{UUID}") == "SELECTOR_KIND_MISMATCH"


def test_is_error_true_and_non_bool():
    assert select_code([user_result("t1", "x", is_error=True)], "tool_result:t1") == "TOOL_RESULT_ERROR"
    assert select([user_result("t1", "x", is_error=False)], "tool_result:t1") == "x"
    assert select_code([user_result("t1", "x", is_error="yes")], "tool_result:t1") == "FORMAT_UNSUPPORTED"


@pytest.mark.parametrize("entries, selector", [
    ([assistant(UUID, [{"type": "image", "source": {}}])], f"assistant:{UUID}"),  # unlisted block type
    ([assistant(UUID, [{"type": "text", "text": 3}])], f"assistant:{UUID}"),
    ([assistant(UUID, [{"type": "text"}])], f"assistant:{UUID}"),
    ([assistant(UUID, ["text"])], f"assistant:{UUID}"),
    ([{"type": "assistant", "uuid": UUID, "message": {"content": "text"}}], f"assistant:{UUID}"),
    ([{"type": "assistant", "uuid": UUID}], f"assistant:{UUID}"),
    ([{"uuid": UUID, "message": {"content": []}}], f"assistant:{UUID}"),  # type missing
    ([{"type": 1, "uuid": UUID, "message": {"content": []}}], f"assistant:{UUID}"),
    ([user_result("t1", 5)], "tool_result:t1"),  # content type mismatch
    ([user_result("t1", None)], "tool_result:t1"),
    ([user_result("t1", [{"type": "image", "source": {}}])], "tool_result:t1"),
    ([user_result("t1", [{"type": "text", "text": None}])], "tool_result:t1"),
    ([user_result("t1", ["a"])], "tool_result:t1"),
    ([{"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}}], "tool_result:t1"),
    ([{"type": "user", "message": {"content": [3]}}, assistant(UUID, [TEXT])], f"assistant:{UUID}"),
    ([{"type": "user", "message": {"content": [{"type": None}]}}, user_result("t1", "x")], "tool_result:t1"),
    ([{"type": "user", "uuid": 7}, assistant(UUID, [TEXT])], f"assistant:{UUID}"),
])
def test_unsupported_structure(entries, selector):
    assert select_code(entries, selector) == "FORMAT_UNSUPPORTED"


def test_not_found_and_other_uuid():
    assert select_code([assistant(OTHER, [TEXT])], f"assistant:{UUID}") == "ENTRY_NOT_FOUND"
    assert select_code([], f"assistant:{UUID}") == "ENTRY_NOT_FOUND"
