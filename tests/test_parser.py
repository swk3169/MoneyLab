from datetime import UTC, datetime

import pytest

from moneylab.providers.polymarket.parser import json_list, parse_datetime, parse_gamma_market, to_float


def by_id(sample, mid):
    return next(m for m in sample if m.get("id") == mid)


def test_parses_json_encoded_fields(gamma_sample):
    m = parse_gamma_market(by_id(gamma_sample, "500001"))
    assert m.market_id == "500001"
    assert m.yes_price == pytest.approx(0.62)
    assert m.no_price == pytest.approx(0.38)
    assert m.outcomes[0].token_id == "1111"
    assert m.volume == pytest.approx(4123456.78)
    assert m.liquidity == pytest.approx(152340.55)
    assert m.volume_24h == pytest.approx(210345.12)
    assert m.end_date == datetime(2026, 12, 10, tzinfo=UTC)
    assert m.spread == pytest.approx(0.02)
    assert m.is_binary_yes_no
    assert m.url == "https://polymarket.com/event/fed-decision-december-2026"


def test_parses_native_lists_and_string_numbers(gamma_sample):
    m = parse_gamma_market(by_id(gamma_sample, "500002"))
    assert m.yes_price == pytest.approx(0.18)
    assert m.volume == pytest.approx(2_500_000)  # falls back from volumeNum to volume
    assert m.volume_24h == pytest.approx(95000.5)
    assert m.best_bid == pytest.approx(0.17)
    assert m.spread == pytest.approx(0.08)


def test_non_yes_no_outcomes(gamma_sample):
    m = parse_gamma_market(by_id(gamma_sample, "500003"))
    assert not m.is_binary_yes_no
    assert m.yes_price is None
    assert [o.name for o in m.outcomes] == ["Team A", "Team B"]
    assert m.price_sum == pytest.approx(1.02)


def test_malformed_values_do_not_raise(gamma_sample):
    m = parse_gamma_market(by_id(gamma_sample, "500005"))
    assert m is not None
    assert m.end_date is None
    assert m.liquidity is None and m.volume is None
    assert m.yes_price is None and m.no_price is None
    assert m.active is True and m.closed is False  # "true"/"false" strings


def test_missing_id_is_skipped(gamma_sample):
    raw = next(m for m in gamma_sample if "id" not in m)
    assert parse_gamma_market(raw) is None


@pytest.mark.parametrize("value,expected", [("1.5", 1.5), (2, 2.0), ("", None), (None, None), ("x", None), (True, None), ("nan", None)])
def test_to_float(value, expected):
    assert to_float(value) == expected


def test_json_list_variants():
    assert json_list('["a","b"]') == ["a", "b"]
    assert json_list(["a"]) == ["a"]
    assert json_list("a, b") == ["a", "b"]
    assert json_list(None) == []
    assert json_list('{"a":1}') == []


def test_parse_datetime_variants():
    assert parse_datetime("2026-12-10") == datetime(2026, 12, 10, tzinfo=UTC)
    assert parse_datetime("2026-12-10T05:00:00.000Z") == datetime(2026, 12, 10, 5, tzinfo=UTC)
    assert parse_datetime("garbage") is None
