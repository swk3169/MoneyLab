"""KRW cash + long/cash position and the BT-1 daily loop (docs/backtest_design.md sections 5, 6, 8).

Timeline for signal day D (UTC), execution hour h (E0: h = 0):
  D+1 00:00            daily bar D ends
  D+1 00:00 + 120 s    decision: AsOfView(daily) shows bar D and earlier confirmed bars only
  D+1 (h):59           order time (market order, if the signal differs from the position)
  D+1 (h+1):00         fill at the close of hourly bar [h:00, h+1:00) of D+1  = reference time R(D)
The fill bar starts after daily bar D ended, so no trade ever uses the close the signal was built on.
The position chosen at R(D) is held over (R(D), R(D+1)].

Missing data (BT-1 rules; substitute fills are BT-2):
  * signal None (missing bar, short history, gap) -> no trade, reason kept in the signal list
  * fill bar missing                              -> order unfilled, holdings unchanged, row in `unfilled`
  * valuation price at R(D) = fill bar close, else the last hourly close that ended by R(D)
After the last decision day E the run ends at R(E+1): an open position is sold there (virtual exit,
draft 8.1 rule 4) and the final valuation is taken.

Only fixture or synthetic bars are accepted in BT-1. Results are SYNTHETIC / NOT_EVIDENCE.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, localcontext
from typing import Any

from moneylab.backtest.costs import PRECISION, CostModel
from moneylab.backtest.data import CONFIRM_DELAY, AsOfView, BarSeries, DataIntegrityError
from moneylab.backtest.ledger import DailyRow, Ledger, UnfilledRow
from moneylab.backtest.strategy import RULES, Signal, decide
from moneylab.domain.bars import NOT_EVIDENCE, require_utc, utc_iso

ALLOWED_KINDS = ("fixture", "synthetic")  # BT-1: real data is refused


@dataclass(frozen=True)
class RunConfig:
    rule: str
    first_day: datetime  # first signal day D (start of its daily bar)
    last_day: datetime  # last signal day E
    initial_cash: Decimal
    costs: CostModel
    exec_hour: int = 0  # E0
    confirm_delay: timedelta = CONFIRM_DELAY

    def __post_init__(self) -> None:
        if self.rule not in RULES:
            raise ValueError(f"unknown rule {self.rule!r}; registered: {sorted(RULES)}")
        for name in ("first_day", "last_day"):
            t = require_utc(getattr(self, name), name)
            if t.hour or t.minute or t.second or t.microsecond:
                raise ValueError(f"{name} must be 00:00 UTC")
        if self.last_day < self.first_day:
            raise ValueError("last_day is before first_day")
        if not isinstance(self.initial_cash, Decimal) or self.initial_cash <= 0:
            raise ValueError("initial_cash must be a positive Decimal (KRW)")
        if not 0 <= self.exec_hour <= 22:
            raise ValueError("exec_hour must be 0..22 (the fill must come after the decision on D+1)")
        if not timedelta(0) <= self.confirm_delay < timedelta(minutes=59):
            raise ValueError("confirm_delay must leave time before the order")

    def to_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "first_day": utc_iso(self.first_day), "last_day": utc_iso(self.last_day),
                "initial_cash": str(self.initial_cash), "costs": self.costs.to_dict(), "exec_hour": self.exec_hour,
                "confirm_delay_s": self.confirm_delay.total_seconds()}


@dataclass
class BacktestResult:
    config: RunConfig
    provenance: dict[str, dict[str, str]]
    signals: list[Signal] = field(default_factory=list)
    ledger: Ledger | None = None
    evidence: str = NOT_EVIDENCE

    def to_dict(self) -> dict[str, Any]:
        from moneylab.backtest import metrics  # local import: metrics reads the ledger only

        led = self.ledger
        assert led is not None

        def row(obj) -> dict[str, Any]:
            return {k: (utc_iso(v) if isinstance(v, datetime) else str(v) if isinstance(v, Decimal) else v)
                    for k, v in obj.__dict__.items()}

        return {"evidence": self.evidence, "config": self.config.to_dict(), "provenance": self.provenance,
                "signals": [row(s) for s in self.signals], "trades": [row(t) for t in led.trades],
                "unfilled": [row(u) for u in led.unfilled], "daily": [row(d) for d in led.daily],
                "metrics": metrics.summary(led)}

    def canonical_json(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json()).hexdigest()


def _check_inputs(daily: BarSeries, hourly: BarSeries) -> None:
    if daily.interval != "day" or hourly.interval != "hour":
        raise ValueError("need a daily series for signals and an hourly series for fills")
    if daily.market != hourly.market:
        raise ValueError("daily and hourly series are of different markets")
    kinds = {daily.provenance.kind, hourly.provenance.kind}
    if not kinds <= set(ALLOWED_KINDS):
        raise DataIntegrityError(f"BT-1 accepts only {ALLOWED_KINDS} bars, got {sorted(kinds)}")
    if len(kinds) != 1:
        raise DataIntegrityError("daily and hourly bars must have the same provenance kind")
    daily.verify()
    hourly.verify()


def simulate(daily: BarSeries, hourly: BarSeries, config: RunConfig) -> BacktestResult:
    """Run one rule over [first_day, last_day]. All money arithmetic uses PRECISION Decimal digits."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return _simulate(daily, hourly, config)


def _simulate(daily: BarSeries, hourly: BarSeries, config: RunConfig) -> BacktestResult:
    _check_inputs(daily, hourly)
    rule = RULES[config.rule]
    result = BacktestResult(config, {s.interval: {"kind": s.provenance.kind, "description": s.provenance.description,
                                                  "bars_sha256": s.provenance.bars_sha256} for s in (daily, hourly)})
    ledger = Ledger(config.initial_cash)
    cash, qty = config.initial_cash, Decimal(0)
    one_day = timedelta(days=1)
    fill_offset = timedelta(hours=config.exec_hour)
    last_price: Decimal | None = None

    def valuation(ref_time: datetime, fill_bar) -> tuple[Decimal | None, str]:
        if fill_bar is not None:
            return fill_bar.close, "fill_bar"
        prev = hourly.last_ended_by(ref_time)
        if prev is not None:
            return prev.close, "last_close"
        return None, "none"

    day = config.first_day
    final = config.last_day + one_day
    while day <= final:
        decided_at = day + one_day + config.confirm_delay
        fill_start = day + one_day + fill_offset
        fill_time = fill_start + timedelta(hours=1)
        order_time = fill_time - timedelta(minutes=1)
        fill_bar = hourly.at_start(fill_start)
        price, source = valuation(fill_time, fill_bar)
        if price is None:
            price, source = last_price, "carried"
        equity_before = cash + qty * price if price is not None else cash
        position = 1 if qty > 0 else 0

        if day < final:
            sig = decide(rule, AsOfView(daily, decided_at, confirm_delay=config.confirm_delay), day)
            result.signals.append(sig)
            target = sig.value
            virtual = False
        else:
            target = 0  # end of the run: virtual exit of an open position
            virtual = True

        if target is not None and target != position:
            side = "buy" if target == 1 else "sell"
            if fill_bar is None and not virtual:
                ledger.unfilled.append(UnfilledRow(day, order_time, side, "fill_bar_missing"))
            elif price is None:
                ledger.unfilled.append(UnfilledRow(day, order_time, side, "no_price"))
            else:
                leg = config.costs.buy(cash, price) if side == "buy" else config.costs.sell(qty, price)
                row = ledger.add_trade(leg=leg, day=day, signal_time=decided_at, order_time=order_time,
                                       fill_time=fill_time,
                                       fill_bar_start=fill_bar.start_utc if fill_bar else fill_start,
                                       cash_before=cash, qty_before=qty, virtual=virtual)
                cash, qty = row.cash_after, row.qty_after

        if price is not None:
            ledger.add_daily(DailyRow(fill_time, price, source, 1 if qty > 0 else 0, cash, qty, equity_before,
                                      cash + qty * price))
            last_price = price
        day += one_day

    ledger.verify()
    result.ledger = ledger
    return result
