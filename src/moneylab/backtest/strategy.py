"""Long/cash rules on confirmed daily closes (BT-1, docs/backtest_design.md section 5).

Rules (fixed parameters; nothing here searches or tunes them):
  sma20 / sma60 / sma120   C_D > SMA_N(D) -> 1 (long), C_D <= SMA_N(D) -> 0 (cash);
                           SMA_N(D) = mean of the N closes of days D-N+1 .. D (day D included)
  r5                       C_D < C_{D-5} -> 1 (5-day return negative: short-term reversal), else 0

These SMA rules are NOT the M20/M60/M120 of docs/research_v06_preregistration_draft.md 6.1, which
hold when the N-day return r(D-N, D] is positive. The user fixed the SMA definition for BT-1
(decision U1, 2026-10-16); the draft's rules are unchanged and are not implemented here.

A decision for day D is taken from an AsOfView at D+1 00:00 UTC + confirm delay, so only bars that
ended and were confirmed are visible. The newest visible daily bar must be day D itself and the
window must be gap-free; otherwise the signal is None with a reason and no trade is made.
Comparisons use Decimal arithmetic on the stored closes (no float rounding at the threshold).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from moneylab.backtest.data import AsOfView
from moneylab.domain.bars import Bar


@dataclass(frozen=True)
class Rule:
    name: str
    kind: str  # "sma" or "reversal"
    length: int

    @property
    def bars_needed(self) -> int:
        return self.length if self.kind == "sma" else self.length + 1


RULES: dict[str, Rule] = {
    "sma20": Rule("sma20", "sma", 20),
    "sma60": Rule("sma60", "sma", 60),
    "sma120": Rule("sma120", "sma", 120),
    "r5": Rule("r5", "reversal", 5),
}


@dataclass(frozen=True)
class Signal:
    rule: str
    day: datetime  # start of daily bar D (the last bar the decision used)
    decided_at: datetime
    value: int | None  # 1 long, 0 cash, None no decision (see reason)
    reason: str | None = None
    detail: str | None = None  # e.g. "close=... sma=..."


def sma(closes: Sequence[Decimal]) -> Decimal:
    if not closes:
        raise ValueError("no closes")
    return sum(closes, Decimal(0)) / Decimal(len(closes))


def _contiguous(bars: Sequence[Bar]) -> bool:
    return all(b.start_utc - a.start_utc == timedelta(days=1) for a, b in zip(bars, bars[1:]))


def decide(rule: Rule, view: AsOfView, day: datetime) -> Signal:
    """Signal for daily bar `day` (D), from what `view` shows."""
    if rule.name not in RULES or RULES[rule.name] != rule:
        raise ValueError(f"unregistered rule {rule!r}")
    if view.interval != "day":
        raise ValueError("signals are computed on daily bars")
    if day + timedelta(days=1) > view.as_of:
        raise ValueError(f"day {day} has not ended at {view.as_of}")
    latest = view.latest()
    if latest is None or latest.start_utc != day:
        return Signal(rule.name, day, view.as_of, None, "missing_bar",
                      f"latest visible daily bar: {latest.start_utc if latest else None}")
    window = view.last(rule.bars_needed)
    if len(window) < rule.bars_needed:
        return Signal(rule.name, day, view.as_of, None, "insufficient_history",
                      f"{len(window)} of {rule.bars_needed} daily bars")
    if not _contiguous(window):
        return Signal(rule.name, day, view.as_of, None, "gap_in_window", None)
    close = window[-1].close
    if rule.kind == "sma":
        level = sma([b.close for b in window])
        value = 1 if close > level else 0
        return Signal(rule.name, day, view.as_of, value, None, f"close={close} sma{rule.length}={level}")
    base = window[0].close
    value = 1 if close < base else 0
    return Signal(rule.name, day, view.as_of, value, None, f"close={close} close_{rule.length}d_ago={base}")
