"""KRW cash + long/cash position and the daily loop (BT-1, extended in BT-2a;
docs/backtest_design.md sections 5, 6, 8; docs/backtest_bt2_review.md C, D, E).

For signal day D the decision is taken at D+1 00:00 UTC + confirm delay from an AsOfView of the
daily bars. The scenario (backtest.execution.SCENARIOS) fixes the order time, the fill bar and price
and the reference time R(D) at which fills are booked and holdings are valued; E0 is the default:
order D+1 00:59, fill at the close of hourly bar [00:00, 01:00), R(D) = D+1 01:00. The fill bar
always starts after daily bar D ended, so no trade uses the close the signal was built on. The
position chosen for D is held over (R(D), R(D+1)].

Orders:
  * signal None (missing bar, short history, gap): no new order; an order already pending stands
  * fill bar missing: the order stays pending (row in `unfilled`) and is retried at the next decision;
    with fill_substitution "prereg_6_3" the next hourly close before the next decision is used first
  * a pending order is cancelled (row in `cancelled`) when a later decision wants the current holding
  * pending and unfilled orders never change cash or quantity
Valuation at R(D): close of the hourly bar ending at R(D), else the last hourly close before R(D).
After the last signal day E the run ends at R(E+1): pending orders are cancelled and an open position
is sold (virtual exit, draft 8.1 rule 4; at the valuation price if the fill bar is missing).

Only fixture or synthetic bars are accepted before BT-5. Results are SYNTHETIC / NOT_EVIDENCE;
scenarios E3 and DIAG are additionally REPORT_ONLY (no executable order rule).
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
from moneylab.backtest.execution import SCENARIOS, SUBSTITUTION_RULES, find_fill
from moneylab.backtest.ledger import DailyRow, Ledger, UnfilledRow
from moneylab.backtest.strategy import RULES, Signal, decide
from moneylab.domain.bars import NOT_EVIDENCE, require_utc, utc_iso

ALLOWED_KINDS = ("fixture", "synthetic")  # real data is refused until BT-5


@dataclass(frozen=True)
class RunConfig:
    rule: str
    first_day: datetime  # first signal day D (start of its daily bar)
    last_day: datetime  # last signal day E
    initial_cash: Decimal
    costs: CostModel
    scenario: str = "E0"
    fill_substitution: str = "none"  # "none" (BT-1 behaviour) or "prereg_6_3"
    confirm_delay: timedelta = CONFIRM_DELAY
    capacity_verified: bool = True  # False when the impact assumption is used above its basis

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
        if self.scenario not in SCENARIOS:
            raise ValueError(f"unknown scenario {self.scenario!r}; known: {sorted(SCENARIOS)}")
        if self.fill_substitution not in SUBSTITUTION_RULES:
            raise ValueError(f"fill_substitution must be one of {SUBSTITUTION_RULES}")
        if not timedelta(0) <= self.confirm_delay < timedelta(minutes=59):
            raise ValueError("confirm_delay must leave time before the order")

    def to_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "first_day": utc_iso(self.first_day), "last_day": utc_iso(self.last_day),
                "initial_cash": str(self.initial_cash), "costs": self.costs.to_dict(), "scenario": self.scenario,
                "report_only": SCENARIOS[self.scenario].report_only, "fill_substitution": self.fill_substitution,
                "fill_model": "ohlcv_approximation", "confirm_delay_s": self.confirm_delay.total_seconds(),
                "capacity": "verified_range" if self.capacity_verified else "CAPACITY_UNVERIFIED"}


@dataclass
class BacktestResult:
    config: RunConfig
    provenance: dict[str, dict[str, str]]
    signals: list[Signal] = field(default_factory=list)
    ledger: Ledger | None = None
    evidence: str = NOT_EVIDENCE

    @property
    def labels(self) -> list[str]:
        out = [self.evidence, "FEE_UNCONFIRMED", "COSTS_ASSUMED"]
        if SCENARIOS[self.config.scenario].report_only:
            out.append("REPORT_ONLY")
        if not self.config.capacity_verified:
            out.append("CAPACITY_UNVERIFIED")
        return out

    def to_dict(self) -> dict[str, Any]:
        from moneylab.backtest import metrics  # local import: metrics reads the ledger only

        led = self.ledger
        assert led is not None

        def row(obj) -> dict[str, Any]:
            return {k: (utc_iso(v) if isinstance(v, datetime) else str(v) if isinstance(v, Decimal) else v)
                    for k, v in obj.__dict__.items()}

        return {"evidence": self.evidence, "labels": self.labels, "config": self.config.to_dict(),
                "provenance": self.provenance, "signals": [row(s) for s in self.signals],
                "trades": [row(t) for t in led.trades], "unfilled": [row(u) for u in led.unfilled],
                "cancelled": [row(c) for c in led.cancelled], "daily": [row(d) for d in led.daily],
                "metrics": metrics.summary(led)}

    def canonical_json(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json()).hexdigest()


@dataclass
class _Pending:
    side: str
    since: datetime  # signal day of the first attempt


def _check_inputs(daily: BarSeries, hourly: BarSeries) -> None:
    if daily.interval != "day" or hourly.interval != "hour":
        raise ValueError("need a daily series for signals and an hourly series for fills")
    if daily.market != hourly.market:
        raise ValueError("daily and hourly series are of different markets")
    kinds = {daily.provenance.kind, hourly.provenance.kind}
    if not kinds <= set(ALLOWED_KINDS):
        raise DataIntegrityError(f"BT-1 accepts only {ALLOWED_KINDS} bars (real data is refused until BT-5), "
                                 f"got {sorted(kinds)}")
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
    spec = SCENARIOS[config.scenario]
    result = BacktestResult(config, {s.interval: {"kind": s.provenance.kind, "description": s.provenance.description,
                                                  "bars_sha256": s.provenance.bars_sha256} for s in (daily, hourly)})
    ledger = Ledger(config.initial_cash)
    cash, qty = config.initial_cash, Decimal(0)
    one_day = timedelta(days=1)
    last_price: Decimal | None = None
    pending: _Pending | None = None

    def valuation(ref_time: datetime) -> tuple[Decimal | None, str, datetime | None]:
        bar = hourly.last_ended_by(ref_time)
        if bar is None:
            return None, "none", None
        return bar.close, ("ref_close" if bar.end_utc == ref_time else "last_close"), bar.start_utc

    day = config.first_day
    final = config.last_day + one_day
    while day <= final:
        decided_at = day + one_day + config.confirm_delay
        next_decision = decided_at + one_day
        order_time = spec.order_time(day)
        ref_time = spec.ref_time(day)
        position = 1 if qty > 0 else 0
        last_step = day == final

        if last_step:
            target: int | None = 0  # end of the run: virtual exit of an open position
        else:
            sig = decide(rule, AsOfView(daily, decided_at, confirm_delay=config.confirm_delay), day)
            result.signals.append(sig)
            target = sig.value

        if pending is not None and (last_step or (target is not None and target == position)):
            ledger.cancelled.append(UnfilledRow(pending.since, order_time, pending.side,
                                                "end_of_run" if last_step else "signal_reverted"))
            pending = None

        side: str | None = None
        if target is not None and target != position:
            side = "buy" if target == 1 else "sell"
        elif pending is not None:
            side = pending.side  # no decision today: the pending order stands

        price, source, val_start = valuation(ref_time)
        if price is None:
            price, source = last_price, "carried"

        fill = None
        if side is not None:
            fill = find_fill(spec, daily, hourly, day, side, next_decision,
                             "none" if last_step else config.fill_substitution)
            if fill is not None:
                fill = (fill.price, fill.fill_time, fill.bar_start, fill.kind)
            elif last_step and price is not None:
                fill = (price, ref_time, val_start or ref_time, "virtual_fallback")
            elif not last_step:
                ledger.unfilled.append(UnfilledRow(day, order_time, side, "fill_bar_missing"))
                pending = _Pending(side, pending.since if pending is not None else day)

        def trade() -> None:
            nonlocal cash, qty, pending
            fill_price, fill_time, bar_start, kind = fill
            leg = config.costs.buy(cash, fill_price) if side == "buy" else config.costs.sell(qty, fill_price)
            row = ledger.add_trade(leg=leg, day=day, signal_time=decided_at,
                                   order_time=min(order_time, fill_time - timedelta(minutes=1)),
                                   fill_time=fill_time, fill_bar_start=bar_start, cash_before=cash, qty_before=qty,
                                   virtual=last_step, scenario=spec.name, fill_kind=kind)
            cash, qty = row.cash_after, row.qty_after
            pending = None

        equity_before = cash + qty * price if price is not None else cash
        if fill is not None and fill[1] <= ref_time:
            trade()
        if price is not None:
            ledger.add_daily(DailyRow(ref_time, price, source, 1 if qty > 0 else 0, cash, qty, equity_before,
                                      cash + qty * price))
            last_price = price
        if fill is not None and fill[1] > ref_time:
            trade()  # substituted fill after the reference time: booked at its own time
        day += one_day

    ledger.verify()
    result.ledger = ledger
    return result
