# Test fixtures

| File | Origin | Notes |
|---|---|---|
| `gamma_markets_sample.json` | **Synthetic.** Written from the official Gamma API docs (`GET /markets`) | Live API returned HTTP 451 from the dev environment, so no real capture exists yet. It mixes field encodings (JSON strings and native lists, string and numeric numbers) and edge cases (closed, missing id, malformed values, non-Yes/No outcomes). **Replace or extend it with a real capture from `data/raw/polymarket/` once access works.** |
| `http_451_cloudflare.json` | **Real capture** (2026-10-04, curl, no Accept header) | Plain-text body `error code: 1026`. Contains no client IP. |
| `http_451_cloudflare_json.json` | **Real capture** (2026-10-04, `moneylab diagnose`, `Accept: application/json`) | Structured Cloudflare error JSON (`error_name=legal_block`, `error_category=legal`). Contains no client IP. |

Fixtures must never contain secrets, private keys or personal IP addresses.
