"""Fill scenarios on OHLCV bars (BT-2a; v0.6 draft 6.2 and 6.3, docs/backtest_bt2_review.md C and D).

For signal day D (decision at D+1 00:00 UTC + confirm delay), times are offsets from D+1 00:00:

  scenario  order    fill bar                     fill price             reference  kappa  use
  E0        00:59    hour [00:00, 01:00) of D+1   close                  01:00      5 bp   base case
  E1        01:59    hour [01:00, 02:00) of D+1   close                  02:00      10 bp  stress
  E2        23:59    day D+1                      close                  D+2 00:00  10 bp  stress (one day later)
  E3        (00:59)  hour [00:00, 01:00) of D+1   worst: buy high, sell low  01:00  10 bp  report only, bound
  DIAG      (00:59)  hour [00:00, 01:00) of D+1   open (before the signal)   01:00  5 bp   report only, optimistic

The reference time is when the fill is booked and when holdings are valued (hourly close that ends at
the reference time). E3 and DIAG have no executable order rule (draft 6.2); their order time is
nominal and their results are REPORT_ONLY. OHLCV fills are approximations, not executed prices.

Missing fill bar (`fill_substitution`):
  "none"        the order stays pending and is retried at the next decision (BT-1 behaviour)
  "prereg_6_3"  first hourly bar that starts at or after the scheduled fill bar's end and ends no later
                than the next decision time; its close is the fill (draft 6.3: "next hourly close").
                If there is none the order stays pending and is retried at the next reference time.
A pending order is cancelled when the next decision wants the current holding again.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from moneylab.backtest.costs import CostModel, impact_bps_for_capital
from moneylab.backtest.data import BarSeries
from moneylab.domain.bars import Bar

H = timedelta(hours=1)
M = timedelta(minutes=1)
SUBSTITUTION_RULES = ("none", "prereg_6_3")


@dataclass(frozen=True)
class FillSpec:
    name: str
    order_offset: timedelta
    bar_interval: str  # "hour" or "day"
    bar_offset: timedelta
    price_field: str  # "close", "open" or "worst"
    ref_offset: timedelta
    kappa_bps: Decimal
    report_only: bool

    def order_time(self, day: datetime) -> datetime:
        return day + timedelta(days=1) + self.order_offset

    def bar_start(self, day: datetime) -> datetime:
        return day + timedelta(days=1) + self.bar_offset

    def ref_time(self, day: datetime) -> datetime:
        return day + timedelta(days=1) + self.ref_offset


SCENARIOS: dict[str, FillSpec] = {
    "E0": FillSpec("E0", 59 * M, "hour", timedelta(0), "close", H, Decimal(5), False),
    "E1": FillSpec("E1", H + 59 * M, "hour", H, "close", 2 * H, Decimal(10), False),
    "E2": FillSpec("E2", 23 * H + 59 * M, "day", timedelta(0), "close", 24 * H, Decimal(10), False),
    "E3": FillSpec("E3", 59 * M, "hour", timedelta(0), "worst", H, Decimal(10), True),
    "DIAG": FillSpec("DIAG", 59 * M, "hour", timedelta(0), "open", H, Decimal(5), True),
}


@dataclass(frozen=True)
class FillResult:
    price: Decimal
    fill_time: datetime
    bar_start: datetime
    kind: str  # "primary" or "substituted"


def bar_price(bar: Bar, field: str, side: str) -> Decimal:
    if field == "close":
        return bar.close
    if field == "open":
        return bar.open
    if field == "worst":
        return bar.high if side == "buy" else bar.low
    raise ValueError(f"unknown price field {field!r}")


def find_fill(spec: FillSpec, daily: BarSeries, hourly: BarSeries, day: datetime, side: str,
              not_after: datetime, substitution: str) -> FillResult | None:
    """Fill of an order of signal day `day`, or None (stays pending). Never returns a bar ending after
    `not_after` (the next decision time)."""
    if substitution not in SUBSTITUTION_RULES:
        raise ValueError(f"fill_substitution must be one of {SUBSTITUTION_RULES}")
    series = hourly if spec.bar_interval == "hour" else daily
    start = spec.bar_start(day)
    bar = series.at_start(start)
    if bar is not None and bar.end_utc <= not_after:
        return FillResult(bar_price(bar, spec.price_field, side), bar.end_utc, bar.start_utc, "primary")
    if substitution == "none":
        return None
    scheduled_end = start + (H if spec.bar_interval == "hour" else timedelta(days=1))
    sub = hourly.first_starting_at_or_after(scheduled_end)
    if sub is not None and sub.end_utc <= not_after:
        return FillResult(sub.close, sub.end_utc, sub.start_utc, "substituted")
    return None


def prereg_costs(fee_bps: int, scenario: str, capital: Decimal, *, impact: bool = True,
                 fee_basis: str = "inclusive") -> tuple[CostModel, bool]:
    """Cost model of the v0.6 draft for one scenario and planned capital: fee scenario, the scenario's
    kappa and iota(C). Returns (model, capacity_verified)."""
    spec = SCENARIOS[scenario]
    iota, verified = impact_bps_for_capital(capital) if impact else (Decimal(0), True)
    return CostModel.scenario(fee_bps, spec.kappa_bps, iota, fee_basis), verified
