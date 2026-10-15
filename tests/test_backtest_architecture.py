"""BT-1 dependency rules (docs/backtest_design.md section 13).

backtest/ and domain/bars.py read no provider, no research code and nothing that can reach the
network; research/ does not read backtest/. The backtest only consumes provider-neutral Bars."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "moneylab"
BACKTEST_FILES = sorted((SRC / "backtest").rglob("*.py")) + [SRC / "domain" / "bars.py"]
NETWORK_MODULES = ("socket", "http", "urllib", "requests", "websocket", "websockets", "ssl", "asyncio",
                   "subprocess", "moneylab.core.http")


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def _bad(mods: set[str], prefixes: tuple[str, ...]) -> set[str]:
    return {m for m in mods if any(m == p or m.startswith(p + ".") for p in prefixes)}


@pytest.mark.parametrize("path", BACKTEST_FILES, ids=lambda p: p.relative_to(SRC).as_posix())
def test_backtest_imports_no_provider_research_or_network(path):
    mods = imported_modules(path)
    assert not _bad(mods, ("moneylab.providers", "moneylab.research", "moneylab.paper", "moneylab.pnl",
                           "moneylab.sizing", "moneylab.strategy", "moneylab.execution")), path
    assert not _bad(mods, NETWORK_MODULES), path


def test_research_does_not_import_backtest():
    for f in (SRC / "research").rglob("*.py"):
        assert not _bad(imported_modules(f), ("moneylab.backtest",)), f
