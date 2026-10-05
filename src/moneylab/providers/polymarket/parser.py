"""Gamma market dict -> domain Market.

FIELD SOURCE STATUS: field names follow Polymarket's official Gamma API docs.
They have NOT yet been verified against a live response from this environment
(all endpoints returned HTTP 451). Parsing is therefore defensive: every field is
optional, numbers may arrive as strings, and list fields may arrive JSON-encoded.
Once a live response is captured (data/raw/polymarket/...), re-check this file and
refresh tests/fixtures/gamma_markets_sample.json from it.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime
from typing import Any

from moneylab.domain.market_params import FeeSchedule, RewardAllocation, RewardConfig
from moneylab.domain.models import Market, Outcome

log = logging.getLogger(__name__)

SOURCE = "polymarket"
EVENT_URL = "https://polymarket.com/event/{slug}"


def to_float(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # drop NaN


def to_bool(value: Any, default: bool | None = None) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    return default


def json_list(value: Any) -> list[Any]:
    """Gamma encodes outcomes/outcomePrices/clobTokenIds as JSON strings, e.g. '["Yes","No"]'."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return [s.strip() for s in value.split(",") if s.strip()]
        return parsed if isinstance(parsed, list) else []
    return []


def parse_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_gamma_fee_schedule(raw: dict[str, Any]) -> FeeSchedule | None:
    """Gamma `feesEnabled` + `feeSchedule` -> FeeSchedule. None when absent (= unknown)."""
    sched = raw.get("feeSchedule")
    enabled = to_bool(raw.get("feesEnabled"))
    if not isinstance(sched, dict):
        return FeeSchedule.free() if enabled is False else None
    rate = to_float(sched.get("rate")) or 0.0
    return FeeSchedule(
        rate=rate,
        exponent=to_float(sched.get("exponent")) or 1.0,
        taker_only=bool(to_bool(sched.get("takerOnly"), True)),
        rebate_rate=to_float(sched.get("rebateRate")) or 0.0,
        enabled=bool(enabled if enabled is not None else rate > 0) and rate > 0,
    )


def parse_gamma_reward_config(raw: dict[str, Any]) -> RewardConfig | None:
    """Gamma `rewardsMaxSpread`, `rewardsMinSize`, `clobRewards[]` -> RewardConfig."""
    max_spread = to_float(raw.get("rewardsMaxSpread"))
    min_size = to_float(raw.get("rewardsMinSize"))
    if max_spread is None or min_size is None:
        return None
    allocations = tuple(
        RewardAllocation(
            daily_rate=to_float(c.get("rewardsDailyRate")) or 0.0,
            start_date=parse_date(c.get("startDate")),
            end_date=parse_date(c.get("endDate")),
        )
        for c in raw.get("clobRewards") or []
        if isinstance(c, dict)
    )
    return RewardConfig(max_spread_cents=max_spread, min_size=min_size, allocations=allocations)


def parse_gamma_market(raw: dict[str, Any]) -> Market | None:
    market_id = raw.get("id") or raw.get("conditionId")
    question = raw.get("question") or raw.get("title")
    if not market_id or not question:
        log.debug("Skipping market without id/question: keys=%s", sorted(raw)[:10])
        return None

    names = json_list(raw.get("outcomes"))
    prices = json_list(raw.get("outcomePrices"))
    tokens = json_list(raw.get("clobTokenIds"))
    outcomes = tuple(
        Outcome(
            name=str(name),
            price=to_float(prices[i]) if i < len(prices) else None,
            token_id=str(tokens[i]) if i < len(tokens) else None,
        )
        for i, name in enumerate(names)
    )

    events = raw.get("events") if isinstance(raw.get("events"), list) else []
    event_slug = events[0].get("slug") if events and isinstance(events[0], dict) else None

    return Market(
        source=SOURCE,
        market_id=str(market_id),
        question=str(question).strip(),
        outcomes=outcomes,
        volume=to_float(raw.get("volumeNum", raw.get("volume"))),
        volume_24h=to_float(raw.get("volume24hr")),
        liquidity=to_float(raw.get("liquidityNum", raw.get("liquidity"))),
        end_date=parse_datetime(raw.get("endDate")) or parse_datetime(raw.get("endDateIso")),
        best_bid=to_float(raw.get("bestBid")),
        best_ask=to_float(raw.get("bestAsk")),
        last_trade_price=to_float(raw.get("lastTradePrice")),
        active=bool(to_bool(raw.get("active"), True)),
        closed=bool(to_bool(raw.get("closed"), False)),
        accepting_orders=to_bool(raw.get("acceptingOrders")),
        slug=raw.get("slug"),
        condition_id=raw.get("conditionId"),
        url=EVENT_URL.format(slug=event_slug) if event_slug else None,
        fee_schedule=parse_gamma_fee_schedule(raw),
        reward_config=parse_gamma_reward_config(raw),
        extra={"spread_reported": to_float(raw.get("spread"))},
    )
