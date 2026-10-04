"""Strategy evaluation metrics.

Pure functions over plain numbers so backtest, paper trading and live PnL tracking
all compute results the same way. Conventions:
  * `pnls`  - realized net PnL per closed trade, in quote currency (after costs)
  * `equity` - equity curve values in time order
  * prices are probabilities in [0, 1]
"""

from __future__ import annotations

from collections.abc import Sequence


def net_return(start_equity: float, end_equity: float) -> float:
    """Fractional return after all costs: end/start - 1."""
    if start_equity <= 0:
        raise ValueError("start_equity must be positive")
    return end_equity / start_equity - 1.0


def win_rate(pnls: Sequence[float]) -> float | None:
    """Share of trades with strictly positive PnL. None if there are no trades."""
    if not pnls:
        return None
    return sum(1 for p in pnls if p > 0) / len(pnls)


def profit_factor(pnls: Sequence[float]) -> float | None:
    """Gross profit / gross loss. inf if there are no losses, None if no trades."""
    if not pnls:
        return None
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = -sum(p for p in pnls if p < 0)
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else None
    return gross_profit / gross_loss


def max_drawdown(equity: Sequence[float]) -> float:
    """Largest peak-to-trough decline as a fraction of the peak (0.25 = -25%)."""
    peak = float("-inf")
    mdd = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            mdd = max(mdd, (peak - v) / peak)
    return mdd


def expected_value_binary(
    p_true: float, entry_price: float, fee_rate: float = 0.0, slippage: float = 0.0
) -> float:
    """EV per share of buying a binary outcome that pays 1.0 if it resolves true.

    p_true      - your estimated probability the outcome resolves true
    entry_price - quoted price paid per share
    fee_rate    - proportional fee on notional (entry_price)
    slippage    - extra price paid per share beyond the quote
    """
    if not 0 <= p_true <= 1:
        raise ValueError("p_true must be in [0, 1]")
    cost = entry_price + slippage + transaction_cost(entry_price, 1.0, fee_rate)
    return p_true * 1.0 - cost


def expected_value_trades(pnls: Sequence[float]) -> float | None:
    """Empirical EV: mean realized PnL per trade."""
    return sum(pnls) / len(pnls) if pnls else None


def transaction_cost(price: float, size: float, fee_rate: float, fixed_fee: float = 0.0) -> float:
    """Proportional fee on notional (price*size) plus a fixed fee per order."""
    return abs(price * size) * fee_rate + fixed_fee


def spread(best_bid: float | None, best_ask: float | None) -> float | None:
    if best_bid is None or best_ask is None:
        return None
    return best_ask - best_bid


def relative_spread(best_bid: float | None, best_ask: float | None) -> float | None:
    """Spread / mid. Comparable across price levels."""
    s = spread(best_bid, best_ask)
    if s is None:
        return None
    mid = (best_bid + best_ask) / 2
    return s / mid if mid > 0 else None


def slippage(expected_price: float, fill_price: float, side: str) -> float:
    """Adverse price movement per share (positive = worse than expected).

    side: "buy" or "sell"
    """
    side = side.lower()
    if side == "buy":
        return fill_price - expected_price
    if side == "sell":
        return expected_price - fill_price
    raise ValueError("side must be 'buy' or 'sell'")


def vwap_fill(levels: Sequence[tuple[float, float]], size: float) -> float | None:
    """Average fill price for `size` shares walking order-book levels [(price, size), ...]
    sorted best-first. None if the book is too thin."""
    remaining = size
    cost = 0.0
    for price, available in levels:
        take = min(remaining, available)
        cost += take * price
        remaining -= take
        if remaining <= 1e-12:
            return cost / size
    return None
