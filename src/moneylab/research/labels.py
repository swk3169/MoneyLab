"""Forward-looking labels on the grid (wall-clock horizons, never next-event).

For row k at t and horizon h (h_rows = h / grid):
  future_mid_return_h{h}    ln(mid[k+h] / mid[k])
  future_mid_move_bps_h{h}  1e4 * (mid[k+h] / mid[k] - 1)
  exec_buy_bps_h{h}_q{Q}_d{D}   1e4 * (VWAP_bid(t+h+D, Q) / VWAP_ask(t+D, Q) - 1)   buy, then sell
  exec_sell_bps_h{h}_q{Q}_d{D}  1e4 * (VWAP_bid(t+D, Q) / VWAP_ask(t+h+D, Q) - 1)   sell inventory, buy back
Executable labels are BEFORE fees (spread, depth and delay are in them); fees are applied with
analytics.spot_costs. A label is NaN when row k or k+h is excluded, any row in k..k+h is a
discontinuity, the entry/exit samples are not clean, or the 30 levels cannot fill Q.
These are the only values that look at the future; features never read them.
"""

from __future__ import annotations

import math

from moneylab.research.features import NAN
from moneylab.research.sampling import Grid


def mid_label_names(h: int) -> tuple[str, str]:
    return f"future_mid_return_h{h}", f"future_mid_move_bps_h{h}"


def exec_label_name(side: str, h: int, size: float, delay_ms: int) -> str:
    return f"exec_{side}_bps_h{h}_q{size:g}_d{delay_ms}"


def label_names(horizons, sizes, delays) -> list[str]:
    out = []
    for h in horizons:
        out.extend(mid_label_names(h))
        for q in sizes:
            for d in delays:
                out += [exec_label_name("buy", h, q, d), exec_label_name("sell", h, q, d)]
    return out


def _ratio_bps(num: float, den: float) -> float:
    if not (num > 0 and den > 0):  # also rejects NaN
        return NAN
    return 1e4 * (num / den - 1.0)


def compute_labels(grid: Grid, horizons: tuple[int, ...]) -> dict[str, list[float]]:
    n = len(grid)
    mid = grid.cols["mid_price"]
    out: dict[str, list[float]] = {}
    for h in horizons:
        hr = grid.lookback_rows(h)
        ret, move = [NAN] * n, [NAN] * n
        for k in range(n - hr):
            j = k + hr
            if grid.reasons[k] or grid.reasons[j] or not grid.clean(k, j):
                continue
            if mid[k] > 0 and mid[j] > 0:
                ret[k] = math.log(mid[j] / mid[k])
                move[k] = 1e4 * (mid[j] / mid[k] - 1.0)
        rn, mn = mid_label_names(h)
        out[rn], out[mn] = ret, move
        for d, ex in grid.exec.items():
            for q in grid.params.sizes_btc:
                buy, sell = [NAN] * n, [NAN] * n
                for k in range(n - hr):
                    j = k + hr
                    if (grid.reasons[k] or not grid.clean(k, j) or not ex.ok[k] or not ex.ok[j]
                            or ex.breaks[k] != ex.breaks[j]):
                        continue
                    buy[k] = _ratio_bps(ex.vwap_bid[q][j], ex.vwap_ask[q][k])
                    sell[k] = _ratio_bps(ex.vwap_bid[q][k], ex.vwap_ask[q][j])
                out[exec_label_name("buy", h, q, d)] = buy
                out[exec_label_name("sell", h, q, d)] = sell
    return out
