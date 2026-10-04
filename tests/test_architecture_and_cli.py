import ast
from pathlib import Path

import pytest

from moneylab.cli import main

SRC = Path(__file__).resolve().parents[1] / "src" / "moneylab"
PROVIDER_NEUTRAL = ["scanner", "strategy", "risk", "backtest", "paper", "analytics", "pnl", "sizing", "domain"]


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


@pytest.mark.parametrize("package", PROVIDER_NEUTRAL)
def test_layers_do_not_import_polymarket(package):
    for f in (SRC / package).rglob("*.py"):
        bad = {m for m in imported_modules(f) if m.startswith("moneylab.providers.polymarket")}
        assert not bad, f"{f.relative_to(SRC)} imports {bad}"


def test_no_order_signing_or_wallet_code():
    forbidden = ("py_clob_client", "eth_account", "web3", "private_key", "seed_phrase", "mnemonic")
    for f in SRC.rglob("*.py"):
        mods = imported_modules(f)
        assert not any(m.split(".")[0] in forbidden for m in mods), f
        assert "private_key" not in f.read_text(encoding="utf-8").lower(), f


def test_cli_book_fixture(capsys):
    assert main(["book"]) == 0
    out = capsys.readouterr().out
    assert "microprice" in out and "0.450" in out


def test_cli_book_unknown_token():
    assert main(["book", "--token", "missing"]) == 3


@pytest.mark.parametrize("strategy", ["mm", "mispricing", "arb", "fair-value"])
def test_cli_simulate_offline(strategy, capsys):
    assert main(["simulate", "--strategy", strategy]) == 0
    out = capsys.readouterr().out
    assert "net_trading_pnl_after_cost" in out and "realized_maker_rebate" in out
    assert "Adoption:" in out and "SYNTHETIC" in out


def test_cli_simulate_resolution_override_and_bad_timeline(tmp_path, capsys):
    assert main(["simulate", "--strategy", "fair-value", "--resolution", "no"]) == 0
    assert "REJECT" in capsys.readouterr().out
    assert main(["simulate", "--timeline", str(tmp_path / "nope.json")]) == 3
