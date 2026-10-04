import logging

from conftest import FIXTURES

from moneylab import cli
from moneylab.core.redaction import MASK, RedactingFilter, redact_text

FAKE_KEY = "0x" + "ab" * 32


def test_redacts_private_key_and_pairs():
    text = f"key {FAKE_KEY} private_key=deadbeef api_key: \"zzz\" ip 203.0.113.9"
    out = redact_text(text)
    assert FAKE_KEY not in out and "deadbeef" not in out and "zzz" not in out
    assert "203.0.113.9" not in out
    assert MASK in out


def test_redacts_seed_phrase():
    seed = " ".join(["abandon"] * 11 + ["about"])
    assert seed not in redact_text(f"seed words: {seed}")


def test_logging_filter_masks(caplog):
    logger = logging.getLogger("moneylab.test")
    logger.addFilter(RedactingFilter())
    with caplog.at_level(logging.INFO, logger="moneylab.test"):
        logger.info("loaded %s", FAKE_KEY)
    assert FAKE_KEY not in caplog.text


def test_cli_scan_fixture_offline(capsys):
    code = cli.main(["scan", "--source", "fixture", "--fixture", str(FIXTURES / "gamma_markets_sample.json"), "--no-save"])
    assert code == cli.EXIT_OK
    out = capsys.readouterr().out
    assert "500001" in out and "0.620" in out and "$210.35K" in out
    assert "500004" not in out  # closed market filtered


def test_cli_scan_unavailable_exits_gracefully(monkeypatch, response_451):
    from conftest import FakeSession

    import moneylab.core.http as http_mod

    real_init = http_mod.HttpClient.__init__

    def fake_init(self, base_url, timeout=10.0, retries=2, user_agent="x", session=None):
        real_init(self, base_url, timeout, retries, user_agent, session=FakeSession(lambda *a: response_451))

    monkeypatch.setattr(http_mod.HttpClient, "__init__", fake_init)
    code = cli.main(["scan", "--no-save"])
    assert code == cli.EXIT_UNAVAILABLE
