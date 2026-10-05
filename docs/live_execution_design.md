# Live execution adapter: design (NOT implemented)

Status: **design only.** No code in this repository places orders, signs messages, loads private
keys or connects a wallet. Building any of this requires explicit approval from the project owner
(CLAUDE.md, absolute rule 1). It can only run where using Polymarket is legal for the operator.
Accessing it from a blocked region, including through a VPN or proxy, is out of scope and will
never be supported.

Endpoints and SDK facts below come from docs.polymarket.com (checked 2026-10-04). Re-verify them
before implementing.

## 1. Goal and non-goals

- Goal: an `ExecutionClient` implementation (`execution/base.py`) that takes the same
  `OrderRequest`s the paper engine accepts and returns `Fill`s in the same shape, so the
  `Ledger`, metrics and kill switch run unchanged in paper and live mode.
- Non-goals: discretionary trading UI, custody, funds transfer, bridging, and any automated
  wallet funding.

## 2. Components

```
strategy -> sizing caps -> KillSwitch.allows_new_orders -> LiveGuard (pre-trade) -> LiveExecutionClient
                                                                                      |  py-clob-client-v2
                                                       HeartbeatThread --------------+  POST /heartbeats
                                                       UserChannel (WS) -> Fill events -> Ledger
```

| Component | Responsibility |
|---|---|
| `execution/live_polymarket.py` (future) | Implements `ExecutionClient.submit/cancel/cancel_all` on **py-clob-client-v2** (`pip install py-clob-client-v2`; the legacy `py-clob-client` does not work on CLOB V2 since 2026-04-28). Converts `OrderRequest` to V2 orders: GTC/GTD, tick and min-size from `/clob-markets/{condition_id}` (`mts`, `mos`). No `feeRateBps`, because fees are set at match time. |
| `LiveGuard` | Runs the pre-trade checks listed in section 4. It refuses orders and does not try to repair them. |
| `HeartbeatThread` | Sends `POST /heartbeats` on a fixed interval. If heartbeats stop, the venue cancels all open orders, which acts as the dead-man switch. If our own heartbeat fails, it trips the kill switch. |
| `UserChannel` | Authenticated WS user channel for order and trade updates. Maps trades to `Fill(liquidity=maker/taker)`. Never infers fills from the book. |
| Reconciler | On start and every N minutes it compares venue open orders and positions with local state. Any mismatch trips the kill switch. |

## 3. Explicit opt-in (all required, checked at process start)

1. Environment variable `MONEYLAB_LIVE_TRADING=I_UNDERSTAND_REAL_MONEY`. Any other value means live mode is off.
2. CLI flag `--live` on a dedicated `moneylab live` command. `simulate` and `scan` can never reach live code.
3. A config file with hard limits: max order notional, max position per market, max portfolio
   exposure, daily loss limit and max drawdown. The process refuses to start without it.
   The limits can only be tightened at runtime.
4. An interactive confirmation that prints the wallet address (public), limits and markets,
   and requires typing the market count. It is skipped only in a supervised service with a
   signed-off config hash.
5. A small-capital phase first: per-order notional cap of a few USDC for the first N days,
   with paper and live results compared daily.

## 4. Pre-trade checks (LiveGuard)

- **Geoblock**: `GET https://polymarket.com/api/geoblock` must return `blocked: false`. It is
  checked at start and every 10 minutes. `blocked: true`, an error or a timeout aborts. The
  system never retries through another network path. If the result is blocked, live mode stays
  off. This is a compliance stop, not an obstacle to route around.
- Kill switch not tripped (section 6).
- The order passes sizing caps: per-market, portfolio, depth, inventory, daily loss and drawdown
  (`sizing/position.py`).
- Price is on tick, size is at or above the minimum, and the market is open (`accepting_orders`).
- Order rate is below the documented CLOB trading limits, with our own token bucket set well
  under them.
- A duplicate of the same intent within T seconds is rejected (idempotency key = intent hash).

## 5. Cancel-all paths

- `ExecutionClient.cancel_all()` calls `DELETE /cancel-all`. The docs say it works in cancel-only mode.
- It is called on: a kill switch trip, SIGINT/SIGTERM, an unhandled exception in the loop,
  heartbeat failure, reconciliation mismatch, geoblock `blocked: true`, and process shutdown
  (`atexit`).
- Venue backstop: missing heartbeats lead the venue to cancel all orders even if our process is dead.
- Per-market cancel uses `DELETE /cancel-market-orders` when a single market misbehaves.

## 6. Kill switch (shared with paper)

`risk/kill_switch.py` is used as-is: daily loss, max drawdown, inventory limit, stale market data,
consecutive provider errors, abnormal spread, and the manual kill flag file. Live mode adds:
heartbeat failure, reconciliation mismatch, geoblock change, and fill-price deviation (a fill
far from the expected price). A trip calls `cancel_all()` and blocks new orders until a
human resets it with `reset("RESET")`.

## 7. Credential isolation

- The private key never lives in this repo, `.env`, logs, fixtures or the process command line.
  It is loaded at start from the OS keystore (Windows Credential Manager or DPAPI) or a hardware
  signer, then held only in the signer object's memory.
- Signing runs in a separate minimal process (`signer`) that exposes "sign this order struct"
  over a local pipe. The trading process never sees the key. The signer enforces its own
  per-order notional cap.
- CLOB L2 API credentials (key, secret, passphrase) are derived at start and kept in memory only.
  They are never written to disk.
- All logging goes through `core/redaction.py`. Tests assert that no 64-hex key, seed phrase or
  auth header appears in logs.
- `.gitignore` already excludes `.env*`, `*.key`, `*.pem`, `*wallet*.json` and `secrets/`.

## 8. Separate trading wallet

- A dedicated wallet is used only for MoneyLab. It holds only the risk capital for the current
  phase, as pUSD (CLOB V2 collateral). The main holdings wallet is never connected.
- Funding is manual and done by a human. The code never moves funds, bridges, wraps or
  withdraws. Wrapping USDC into pUSD is a manual step.
- Token approvals are limited to the CTF Exchange V2 and Neg Risk contracts listed in the docs.
  They are reviewed before use and revoked when live trading stops.

## 9. Accounting

- Fees come from actual trade records. They are not recomputed.
- Maker rebates: `realized_maker_rebate` is booked only from `GET /rebates/current` (by date and
  maker address). The estimate stays in `estimated_maker_rebate` for comparison.
- Liquidity rewards: `realized_liquidity_reward` is booked only from the rewards earnings
  endpoints. The estimate stays separate.
- The adoption rule is unchanged: `net_trading_pnl_after_cost` must be positive without incentives.

## 10. Rollout gates

1. Recorded live order books replace the synthetic fixtures, and the paper results are re-run.
2. Paper trading on live data (`PollingBookStream`) runs for at least several weeks, with the
   adoption rule met on a sufficient number of trades.
3. The project owner approves live execution explicitly and in writing.
4. Small-capital live phase with daily paper-vs-live reconciliation.
5. Limits are raised only after a review.
