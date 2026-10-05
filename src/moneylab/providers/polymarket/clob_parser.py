"""CLOB raw payloads -> domain objects.

FIELD SOURCE STATUS: names follow the official CLOB OpenAPI spec (docs.polymarket.com,
checked 2026-10-04). NONE were verified against a live response from this environment
(HTTP 451). Parsing is defensive: numbers may be strings, fields may be missing.

  GET  /book?token_id=            OrderBookSummary {market, asset_id, timestamp, hash, bids, asks,
                                   min_order_size, tick_size, neg_risk, last_trade_price}
  POST /books                      [OrderBookSummary, ...]
  GET  /clob-markets/{condition}   {t:[{t,o}], mts, mos, mbf, tbf, fd:{r,e,to}, r, rfqe, itode, oas, ...}
  GET  /rewards/markets/{cond}     {data:[{rewards_max_spread, rewards_min_size,
                                   rewards_config:[{rate_per_day, start_date, end_date}], tokens}], ...}

Unverified interpretations:
  * `timestamp` on /book: unit not documented. Values > 1e11 are treated as milliseconds.
  * `fd.r` is used as the fee rate (same scale as Gamma `feeSchedule.rate`, e.g. 0.04).
    `/fee-rate` (`base_fee` in bps) is NOT used: its relation to `fd.r` is undocumented.
  * neg_risk is not in the /clob-markets spec; it is taken from /book (`neg_risk`).
  * Rebate rate is not part of /clob-markets; it comes from Gamma `feeSchedule.rebateRate`
    or the documented category table (caller supplies it).
"""

from __future__ import annotations

from typing import Any

from moneylab.domain.market_params import FeeSchedule, MarketParams, RewardAllocation, RewardConfig, TokenInfo
from moneylab.domain.orderbook import OrderBook
from moneylab.providers.polymarket.parser import parse_date, to_bool, to_float


def parse_timestamp(value: Any) -> float | None:
    ts = to_float(value)
    if ts is None:
        return None
    return ts / 1000.0 if ts > 1e11 else ts


def _levels(raw: Any) -> list[tuple[float, float]]:
    out = []
    for lvl in raw if isinstance(raw, list) else []:
        if not isinstance(lvl, dict):
            continue
        price, size = to_float(lvl.get("price")), to_float(lvl.get("size"))
        if price is None or size is None or not 0.0 <= price <= 1.0:
            continue
        out.append((price, size))
    return out


def parse_order_book(raw: dict[str, Any]) -> OrderBook:
    if not isinstance(raw, dict):
        raise ValueError(f"order book must be an object, got {type(raw).__name__}")
    token_id = raw.get("asset_id")
    if not token_id:
        raise ValueError("order book without asset_id")
    return OrderBook.build(
        str(token_id),
        _levels(raw.get("bids")),
        _levels(raw.get("asks")),
        tick_size=to_float(raw.get("tick_size")) or 0.01,
        min_order_size=to_float(raw.get("min_order_size")) or 0.0,
        market_id=raw.get("market"),
        timestamp=parse_timestamp(raw.get("timestamp")),
        last_trade_price=to_float(raw.get("last_trade_price")),
        neg_risk=bool(to_bool(raw.get("neg_risk"), False)),
    )


def parse_order_books(payload: Any) -> dict[str, OrderBook]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):  # tolerate an envelope
        payload = payload["data"]
    if not isinstance(payload, list):
        raise ValueError(f"/books payload must be a list, got {type(payload).__name__}")
    books = [parse_order_book(b) for b in payload]
    return {b.token_id: b for b in books}


def parse_rewards(payload: Any) -> RewardConfig | None:
    """/rewards/markets/{condition_id} -> RewardConfig, or None if the market has no rewards."""
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return None
    row = rows[0]
    max_spread = to_float(row.get("rewards_max_spread"))
    min_size = to_float(row.get("rewards_min_size"))
    if max_spread is None or min_size is None:
        return None
    allocations = tuple(
        RewardAllocation(
            daily_rate=to_float(c.get("rate_per_day")) or 0.0,
            start_date=parse_date(c.get("start_date")),
            end_date=parse_date(c.get("end_date")),
        )
        for c in row.get("rewards_config") or []
        if isinstance(c, dict)
    )
    return RewardConfig(max_spread_cents=max_spread, min_size=min_size, allocations=allocations)


def parse_fee_details(fd: Any, rebate_rate: float = 0.0) -> FeeSchedule:
    if not isinstance(fd, dict):
        return FeeSchedule.free()
    rate = to_float(fd.get("r")) or 0.0
    return FeeSchedule(
        rate=rate,
        exponent=to_float(fd.get("e")) or 1.0,
        taker_only=bool(to_bool(fd.get("to"), True)),
        rebate_rate=rebate_rate,
        enabled=rate > 0,
    )


def parse_clob_market_info(
    raw: dict[str, Any], condition_id: str, rewards: RewardConfig | None = None, rebate_rate: float = 0.0
) -> MarketParams:
    if not isinstance(raw, dict):
        raise ValueError(f"/clob-markets payload must be an object, got {type(raw).__name__}")
    tokens = tuple(
        TokenInfo(token_id=str(t.get("t")), outcome=str(t.get("o", "")))
        for t in raw.get("t") or []
        if isinstance(t, dict) and t.get("t")
    )
    if not tokens:
        raise ValueError("/clob-markets payload without tokens")
    return MarketParams(
        condition_id=condition_id,
        tokens=tokens,
        tick_size=to_float(raw.get("mts")) or 0.01,
        min_order_size=to_float(raw.get("mos")) or 0.0,
        fee=parse_fee_details(raw.get("fd"), rebate_rate),
        rewards=rewards,
    )
