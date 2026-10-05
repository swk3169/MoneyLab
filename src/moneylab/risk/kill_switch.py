"""Kill switch: latched halt of all new risk.

Once tripped it stays tripped until `reset()` is called explicitly (manual action). On trip it
invokes every registered callback - the runner registers the execution client's cancel_all,
so outstanding orders are cancelled immediately.

Conditions:
  daily_loss_limit     today's PnL (mark-to-market, from the day's first equity) <= -limit
  max_drawdown         (peak - equity) / peak >= limit
  inventory_limit      |net YES delta| in any market > limit
  stale_market_data    now - book timestamp > stale_after_seconds (or a book is missing)
  provider_errors      consecutive provider errors >= max_consecutive_errors
  abnormal_spread      spread > max_spread, or a one-sided / crossed book
  manual_kill_flag     the kill-flag file exists
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from moneylab.domain.orderbook import OrderBook

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class KillSwitchConfig:
    daily_loss_limit: float = 50.0
    max_drawdown: float = 0.20
    max_inventory_shares: float = 500.0
    stale_after_seconds: float = 120.0
    max_consecutive_errors: int = 3
    max_spread: float = 0.20
    kill_flag_path: Path | None = None


@dataclass(frozen=True)
class RiskSnapshot:
    now: float
    equity: float
    peak_equity: float
    daily_pnl: float
    net_delta: Mapping[str, float] = field(default_factory=dict)  # market -> YES-equivalent shares
    books: Mapping[str, OrderBook | None] = field(default_factory=dict)  # watched token -> book


class KillSwitch:
    def __init__(self, config: KillSwitchConfig | None = None):
        self.config = config or KillSwitchConfig()
        self.tripped = False
        self.reasons: list[str] = []
        self.tripped_at: float | None = None
        self.consecutive_errors = 0
        self._callbacks: list[Callable[[list[str]], None]] = []

    def on_trip(self, callback: Callable[[list[str]], None]) -> None:
        self._callbacks.append(callback)

    @property
    def allows_new_orders(self) -> bool:
        return not self.tripped

    def record_error(self, now: float | None = None) -> bool:
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.config.max_consecutive_errors:
            self.trip([f"provider_errors: {self.consecutive_errors} consecutive"], now)
        return self.tripped

    def record_success(self) -> None:
        self.consecutive_errors = 0

    def evaluate(self, snap: RiskSnapshot) -> list[str]:
        """Return every violated condition (does not trip by itself)."""
        c = self.config
        reasons: list[str] = []
        if c.kill_flag_path is not None and Path(c.kill_flag_path).exists():
            reasons.append(f"manual_kill_flag: {c.kill_flag_path}")
        if snap.daily_pnl <= -c.daily_loss_limit:
            reasons.append(f"daily_loss_limit: {snap.daily_pnl:.2f} <= -{c.daily_loss_limit}")
        if snap.peak_equity > 0:
            dd = (snap.peak_equity - snap.equity) / snap.peak_equity
            if dd >= c.max_drawdown:
                reasons.append(f"max_drawdown: {dd:.2%} >= {c.max_drawdown:.2%}")
        for market, delta in snap.net_delta.items():
            if abs(delta) > c.max_inventory_shares:
                reasons.append(f"inventory_limit: {market} |delta|={abs(delta):.1f} > {c.max_inventory_shares}")
        for token, book in snap.books.items():
            if book is None:
                reasons.append(f"stale_market_data: no book for {token}")
                continue
            if book.timestamp is None or snap.now - book.timestamp > c.stale_after_seconds:
                age = "unknown" if book.timestamp is None else f"{snap.now - book.timestamp:.0f}s"
                reasons.append(f"stale_market_data: {token} age={age}")
            if book.best_bid is None or book.best_ask is None or book.is_crossed:
                reasons.append(f"abnormal_spread: {token} one-sided or crossed book")
            elif book.spread > c.max_spread + 1e-12:
                reasons.append(f"abnormal_spread: {token} spread={book.spread:.3f} > {c.max_spread}")
        if self.consecutive_errors >= c.max_consecutive_errors:
            reasons.append(f"provider_errors: {self.consecutive_errors} consecutive")
        return reasons

    def check(self, snap: RiskSnapshot) -> bool:
        """Evaluate and trip if anything is violated. Returns True when tripped."""
        if not self.tripped:
            reasons = self.evaluate(snap)
            if reasons:
                self.trip(reasons, snap.now)
        return self.tripped

    def trip(self, reasons: list[str], now: float | None = None) -> None:
        if self.tripped:
            return
        self.tripped, self.reasons, self.tripped_at = True, list(reasons), now
        log.warning("KILL SWITCH TRIPPED: %s", "; ".join(reasons))
        for cb in self._callbacks:
            cb(self.reasons)

    def reset(self, confirm: str) -> None:
        """Manual reset only. `confirm` must be 'RESET' to avoid accidental calls."""
        if confirm != "RESET":
            raise ValueError("pass confirm='RESET' to reset the kill switch")
        self.tripped, self.reasons, self.tripped_at, self.consecutive_errors = False, [], None, 0
