"""Official Upbit public endpoints and limits (Upbit Developer Center, checked 2026-10-06).

Sources (Korean docs):
  WebSocket guide      https://docs.upbit.com/kr/reference/websocket-guide
  Orderbook (WS)       https://docs.upbit.com/kr/reference/websocket-orderbook
  Trade (WS)           https://docs.upbit.com/kr/reference/websocket-trade
  Rate limits          https://docs.upbit.com/kr/reference/rate-limits
  Market list (REST)   https://docs.upbit.com/kr/reference/list-trading-pairs

Only public market data is used. No API key, secret, JWT, account, order, deposit or
withdrawal endpoint is referenced anywhere in this package.
"""

from __future__ import annotations

import re

DOC_WEBSOCKET_GUIDE = "https://docs.upbit.com/kr/reference/websocket-guide"
DOC_WEBSOCKET_ORDERBOOK = "https://docs.upbit.com/kr/reference/websocket-orderbook"
DOC_WEBSOCKET_TRADE = "https://docs.upbit.com/kr/reference/websocket-trade"
DOC_RATE_LIMITS = "https://docs.upbit.com/kr/reference/rate-limits"
DOC_MARKET_LIST = "https://docs.upbit.com/kr/reference/list-trading-pairs"
DOC_REFS = (DOC_WEBSOCKET_GUIDE, DOC_WEBSOCKET_ORDERBOOK, DOC_WEBSOCKET_TRADE, DOC_RATE_LIMITS)

# Public (unauthenticated) WebSocket endpoint. The private endpoint (/websocket/v1/private,
# myOrder/myAsset) is deliberately not referenced.
WS_PUBLIC_URL = "wss://api.upbit.com/websocket/v1"

REST_BASE_URL = "https://api.upbit.com"
REST_MARKET_ALL = "/v1/market/all"  # GET, `is_details` optional

# Subscription request (websocket-guide): JSON array of
#   {"ticket": <unique id>}, one or more {"type", "codes", "is_only_snapshot"?, "is_only_realtime"?},
#   and an optional {"format": DEFAULT | SIMPLE | JSON_LIST | SIMPLE_LIST}.
# MoneyLab requests DEFAULT (full field names) and only parses DEFAULT.
WS_FORMAT = "DEFAULT"
# Orderbook unit count is a code suffix: "KRW-BTC.15" (allowed: 1, 5, 15, 30).
ORDERBOOK_UNITS_ALLOWED = (1, 5, 15, 30)
DEFAULT_ORDERBOOK_UNITS = 30
# `level` (price grouping, KRW markets only) defaults to 0 = native tick size. MoneyLab never
# sends `level`, so no aggregation is requested; the recorder checks the `level` it receives.
NO_AGGREGATION_LEVEL = 0

# Connection management (websocket-guide): the server closes a connection after 120 s without
# data exchange. Clients keep it alive with WebSocket PING frames or a "PING" text message;
# the text message is answered with {"status":"UP"}.
IDLE_TIMEOUT_SECONDS = 120.0
PING_TEXT = "PING"

# Rate limits (rate-limits):
#   websocket-connect  : 5 per second   (per IP when unauthenticated)
#   websocket-message  : 5 per second and 100 per minute, per connection
#   REST quotation     : 10 per second  (per IP, shared within a group)
#   429 -> exceeded; retry from the next second.  418 -> temporary ban after repeated
#   violations; the response states the ban duration, which grows with repeat violations.
WS_CONNECT_LIMITS = ((5, 1.0),)
WS_MESSAGE_LIMITS = ((5, 1.0), (100, 60.0))
REST_QUOTATION_LIMITS = ((10, 1.0),)

DEFAULT_MARKET = "KRW-BTC"
# Docs: pair codes are upper case, e.g. KRW-BTC.
_MARKET_RE = re.compile(r"^[A-Z]{2,10}-[A-Z0-9]{1,20}$")


def validate_market(code: str) -> str:
    code = code.strip()
    if not _MARKET_RE.match(code):
        raise ValueError(f"invalid Upbit market code {code!r} (expected upper case like KRW-BTC)")
    return code


def orderbook_code(market: str, units: int) -> str:
    if units not in ORDERBOOK_UNITS_ALLOWED:
        raise ValueError(f"orderbook units must be one of {ORDERBOOK_UNITS_ALLOWED}, got {units}")
    return f"{validate_market(market)}.{units}"
