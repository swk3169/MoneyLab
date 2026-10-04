from pathlib import Path

from conftest import FIXTURES, NOW

from moneylab.core.exceptions import ProviderError
from moneylab.domain.models import Market, Outcome
from moneylab.providers.base import MarketDataProvider, MarketQuery
from moneylab.providers.polymarket import GammaFileSource, PolymarketProvider
from moneylab.scanner import MarketScanner, ScanCriteria


class StaticProvider(MarketDataProvider):
    """Non-Polymarket provider: proves the scanner is provider-agnostic."""

    name = "static"

    def __init__(self, markets):
        self.markets = markets

    def get_markets(self, query):
        return self.markets


class FailingProvider(MarketDataProvider):
    name = "broken"

    def get_markets(self, query):
        raise ProviderError(self.name, "HTTP 451")


def fixture_markets():
    return PolymarketProvider(GammaFileSource(FIXTURES / "gamma_markets_sample.json")).get_markets(MarketQuery())


def test_file_provider_drops_closed_and_unparseable():
    ids = {m.market_id for m in fixture_markets()}
    assert "500004" not in ids  # closed
    assert ids == {"500001", "500002", "500003", "500005", "500007"}


def test_select_sorts_and_filters():
    cands = MarketScanner.select(fixture_markets(), ScanCriteria(min_volume=1000, sort_by="volume24h"), now=NOW)
    assert [c.market.market_id for c in cands] == ["500001", "500003", "500002"]


def test_flags():
    cands = {c.market.market_id: c for c in MarketScanner.select(fixture_markets(), ScanCriteria(), now=NOW)}
    assert "WIDE_SPREAD" in cands["500002"].flags
    assert "NON_BINARY" in cands["500003"].flags
    assert any(f.startswith("PRICE_SUM") for f in cands["500003"].flags)
    assert "NOT_ACCEPTING" in cands["500007"].flags
    assert cands["500001"].flags == []


def test_max_days_and_binary_only():
    cands = MarketScanner.select(fixture_markets(), ScanCriteria(max_days_to_end=60, binary_only=True), now=NOW)
    assert [c.market.market_id for c in cands] == []  # 500003 ends in 32d but is non-binary
    cands = MarketScanner.select(fixture_markets(), ScanCriteria(max_days_to_end=90, binary_only=True), now=NOW)
    assert {c.market.market_id for c in cands} == {"500001", "500002"}


def test_scanner_works_with_any_provider():
    m = Market(source="static", market_id="s1", question="Q?", outcomes=(Outcome("Yes", 0.4), Outcome("No", 0.6)), volume=10)
    result = MarketScanner(StaticProvider([m])).scan(ScanCriteria(min_days_to_end=None))
    assert result.ok and result.provider == "static"
    assert result.candidates[0].market.yes_price == 0.4


def test_provider_failure_is_returned_not_raised():
    result = MarketScanner(FailingProvider()).scan(ScanCriteria())
    assert not result.ok
    assert result.candidates == []
    assert "451" in str(result.error)


def test_missing_fixture_file_becomes_provider_error(tmp_path: Path):
    provider = PolymarketProvider(GammaFileSource(tmp_path / "nope.json"))
    result = MarketScanner(provider).scan(ScanCriteria())
    assert not result.ok and isinstance(result.error, ProviderError)
