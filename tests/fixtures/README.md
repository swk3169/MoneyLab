# Test fixtures

| File | Origin | Notes |
|---|---|---|
| `gamma_markets_sample.json` | **Synthetic.** Written from the official Gamma API docs (`GET /markets`) | Live API returned HTTP 451 from the dev environment, so no real capture exists yet. It mixes field encodings (JSON strings and native lists, string and numeric numbers) and edge cases (closed, missing id, malformed values, non-Yes/No outcomes). **Replace or extend it with a real capture from `data/raw/polymarket/` once access works.** |
| `http_451_cloudflare.json` | **Real capture** (2026-10-04, curl, no Accept header) | Plain-text body `error code: 1026`. Contains no client IP. |
| `http_451_cloudflare_json.json` | **Real capture** (2026-10-04, `moneylab diagnose`, `Accept: application/json`) | Structured Cloudflare error JSON (`error_name=legal_block`, `error_category=legal`). Contains no client IP. |

| `clob_books_sample.json` | **Synthetic.** `GET /book` shape from the CLOB OpenAPI spec (2026-10-04) | YES and NO books. Bids are deliberately ascending (as in the WS docs example) to test sorting. |
| `clob_market_info_sample.json` | **Synthetic.** `GET /clob-markets/{condition_id}` shape | Politics-like fee `fd.r=0.04`, tick 0.01, min size 5. |
| `clob_rewards_market_sample.json` | **Synthetic.** `GET /rewards/markets/{condition_id}` shape | Max spread 3c, min size 50, 20/day. |
| `clob_timeline_mm.json` | **Synthetic**, generated | 2h, 60s snapshots: 80 min mean-reverting YES mid, then a 40-minute drift. NO book mirrors YES. No resolution. |
| `clob_timeline_mispricing.json` | **Synthetic**, generated | 1h, 60s snapshots with 4 dislocated NO books (complement gap) and an invented `fair_yes` signal. Resolves YES; the outcome is arbitrary. |

All `clob_*` files are produced by `generate_clob_fixtures.py` (seeded, deterministic). Their prices, sizes, ids and
paths are invented. **No simulation result on them is evidence of profitability.** Replace them with recorded `/books`
responses from `data/raw/polymarket/` once the API can be reached legally, then re-run the simulations and update
the golden values in `tests/test_simulation_e2e.py`.

Fixtures must never contain secrets, private keys or personal IP addresses.
