"""Market-making strategy interface and a reference implementation.

A market maker returns the full set of quotes it wants resting after each step; the runner
reconciles them with live paper orders (cancel stale, place missing).

Polymarket mechanics used here (docs "Prices & Orderbook"): a YES ask can be expressed as a
NO bid at 1 - price (complementary matching), so a maker without YES inventory quotes the
ask side by bidding NO. Shorting is not possible; selling requires holding shares.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from moneylab.analytics.metrics import microprice
from moneylab.risk.inventory import reservation_price
from moneylab.strategy.context import Quote, StrategyContext, ceil_to_tick, floor_to_tick


class MarketMakingStrategy(ABC):
    name: str = "abstract-mm"

    @abstractmethod
    def quote(self, ctx: StrategyContext) -> list[Quote]:
        """Desired resting quotes. Pure: no I/O, no order placement."""


@dataclass
class SymmetricMarketMaker(MarketMakingStrategy):
    """Quotes around the YES microprice, skewed against inventory.

    reservation = fair - skew_per_share * net_yes_delta
    bid = floor(reservation - half_spread_ticks * tick), ask = ceil(reservation + ...)
    Quotes never cross the book (post-only). When `stay_in_reward_band` is set and the market
    has reward settings, prices are pulled inside the max qualifying spread and sizes raised to
    the reward minimum - but only if that does not cross the book.
    """

    quote_size: float = 50.0
    half_spread_ticks: int = 1
    skew_per_share: float = 0.0001
    max_inventory_shares: float = 300.0
    stay_in_reward_band: bool = True
    name: str = "symmetric-mm"

    def quote(self, ctx: StrategyContext) -> list[Quote]:
        p = ctx.params
        yes, no = p.yes_token, p.no_token
        book = ctx.book(yes)
        if not yes or not no or book is None or book.best_bid is None or book.best_ask is None:
            return []
        tick = book.tick_size or p.tick_size
        fair = microprice(book.best_bid, book.best_bid_size, book.best_ask, book.best_ask_size)
        delta = ctx.net_yes_delta
        r = reservation_price(fair, delta, self.skew_per_share, tick)

        bid = floor_to_tick(r - self.half_spread_ticks * tick, tick)
        ask = ceil_to_tick(r + self.half_spread_ticks * tick, tick)
        bid = min(bid, round(book.best_ask - tick, 6))  # post-only: never cross
        ask = max(ask, round(book.best_bid + tick, 6))
        size = max(self.quote_size, p.min_order_size)

        rewards = p.rewards
        if self.stay_in_reward_band and rewards is not None and book.mid is not None:
            band = rewards.max_spread_cents / 100.0
            bid = max(bid, ceil_to_tick(book.mid - band + tick, tick))
            ask = min(ask, floor_to_tick(book.mid + band - tick, tick))
            bid = min(bid, round(book.best_ask - tick, 6))
            ask = max(ask, round(book.best_bid + tick, 6))
            size = max(size, rewards.min_size)

        quotes: list[Quote] = []
        if delta < self.max_inventory_shares and tick <= bid < 1:
            quotes.append(Quote(yes, "buy", bid, size))
        if delta > -self.max_inventory_shares and 0 < ask <= 1 - tick:
            if ctx.position(yes) >= size:
                quotes.append(Quote(yes, "sell", ask, size))
            else:
                quotes.append(Quote(no, "buy", round(1.0 - ask, 6), size))
        return quotes
