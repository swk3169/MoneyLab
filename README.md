# MoneyLab

데이터 기반 투자·예측시장 전략을 분석하고 수익 기회를 탐색하는 Python 프로젝트.

최종 목표는 **검증된 수익성을 가진 자동매매 시스템**이며, 다음 순서로 단계적으로 진행한다.

```
Scanner (v0.1) → 호가창 전략 연구·오프라인 시뮬레이션 (v0.2) → 실데이터 Recorder·Replay (v0.3, Upbit v0.3.1) → Paper Trading(실데이터) → Live Execution
```

> **현재 버전(v0.3)은 읽기 전용이다.** 실제 주문, 지갑 연결, 개인키 사용, 자동매매, 실거래 자금 사용 기능은 없다.

---

## v0.1: Polymarket Scanner

- Polymarket Gamma 공개 API에서 활성 시장을 조회한다 (페이지네이션, timeout, 재시도 포함).
- 시장명, YES/NO 가격, bid/ask spread, 24시간 거래량, 누적 거래량, 유동성, 종료일, Market ID를 표로 출력한다.
- 필터(최소 거래량·유동성, N일 이내 종료, binary only)와 정렬을 지원한다.
- 플래그를 표시한다: `WIDE_SPREAD`, `PRICE_SUM≠1`, `NOT_ACCEPTING`, `NON_BINARY`.
- 원본 응답은 `data/raw/`에, 후보 목록 CSV는 `data/processed/`에 저장한다.
- API 접근이 실패하면 status, headers, body를 포함한 진단을 출력하고 정상 종료한다 (traceback 없음).
- `diagnose` 명령으로 연결 상태를 진단한다. 사실(observations)과 가설(hypotheses)을 분리해서 보여준다.

### 알려진 제약

개발 환경(2026-10-04)에서는 Polymarket의 모든 공개 엔드포인트가 **HTTP 451**을 반환한다
(Cloudflare `error_code=1026`, `error_category=legal`). 원인이 되는 클라이언트 속성은 서버가 밝히지 않으므로 단정하지 않는다.
이 프로젝트는 VPN, 프록시 등 **접근 제한 우회 기능을 제공하지 않으며 앞으로도 제공하지 않는다**.
Polymarket 이용약관과 거주 지역 규정을 직접 확인할 것.

그래서 `tests/fixtures/gamma_markets_sample.json`은 공식 문서를 기준으로 만든 **합성 데이터**다.
실제 응답을 받을 수 있게 되면 `data/raw/polymarket/`에 저장된 원본으로 교체해야 한다 ([tests/fixtures/README.md](tests/fixtures/README.md) 참고).

---

## v0.2: 호가창 기반 전략 연구 (오프라인 시뮬레이션)

Polymarket CLOB V2(2026-04-28부터 운영)의 공개 읽기 전용 엔드포인트를 기준으로 만들었다.
HTTP 451 상태에서도 fixture timeline으로 전체 전략을 오프라인에서 시뮬레이션한다.

| 모듈 | 파일 |
|---|---|
| CLOB order-book reader (`/book`, `/books`, `/clob-markets/{id}`, `/rewards/markets/{id}`) | `providers/polymarket/clob_*.py` |
| spread, microprice, depth, imbalance, price impact | `analytics/metrics.py` |
| taker fee `C·rate·p(1−p)` (소수 5자리 반올림), maker fee 0 | `analytics/costs.py` |
| maker rebate **추정치** (`rebate_rate × fee_equivalent`) | `analytics/costs.py` |
| liquidity reward 점수 `S, Q_one, Q_two, Q_min`, 보상 **추정치** | `analytics/rewards.py` |
| taker/maker EV (거래 EV와 인센티브 분리) | `analytics/ev.py` |
| market-making 인터페이스 + `SymmetricMarketMaker` | `strategy/market_making.py` |
| mispricing 인터페이스 + `ComplementArbitrage`, `FairValueDeviation` | `strategy/mispricing.py` |
| inventory risk (net delta, 최악 손실, reservation price) | `risk/inventory.py` |
| fractional Kelly (기본 0.25) + 6가지 cap | `sizing/position.py` |
| paper execution engine (taker VWAP, 보수적 trade-through maker fill) | `paper/engine.py`, `paper/fill_models.py` |
| PnL 분해, equity, drawdown, 채택 규칙 | `pnl/ledger.py`, `pnl/report.py` |
| kill switch (7가지 조건, 발동 시 주문 전량 취소) | `risk/kill_switch.py` |
| 실거래 adapter | **설계 문서만 있음**: [docs/live_execution_design.md](docs/live_execution_design.md) |

### PnL 분해

```
gross_trading_pnl          = spread_captured − slippage + inventory_pnl   (= 현금흐름 + 포지션×평가가, 테스트로 검증)
net_trading_pnl_after_cost = gross_trading_pnl − taker_fees − maker_fees
all_in_realized_pnl        = net_trading_pnl_after_cost + realized_maker_rebate + realized_liquidity_reward
```

`estimated_maker_rebate`와 `estimated_liquidity_reward`는 모델이 계산한 값이다. 실제 지급이 확인되기 전에는
실현 PnL에 넣지 않는다. 경쟁자의 유동성을 알 수 없으므로 reward를 확정값으로 계산하지 않는다.

**채택 규칙**: 인센티브를 뺀 `net_trading_pnl_after_cost`가 0 이하인 전략은 `REJECT`한다.
합성 데이터이거나 거래 수가 부족하면 결과가 양수여도 `INSUFFICIENT_EVIDENCE`로 판정한다.

### 실제 데이터로 교체하기

timeline JSON은 실제 CLOB 응답 형식을 그대로 담는다 (`snapshots[].books[]` = `GET /book` 응답).
API에 합법적으로 접근할 수 있게 되면 `/books` 응답을 같은 형식으로 기록하고 `simulate --timeline <파일>`로 실행한다.
실시간 페이퍼 트레이딩은 `paper/book_stream.PollingBookStream`이 `OrderBookProvider`를 polling하는 방식으로 이어진다.

---

## v0.3: Real Market Data Recorder + Replay

실제 Polymarket CLOB 호가를 오랜 기간 기록하고, 기록한 데이터를 v0.2 paper engine에 그대로 재생한다.

```
Recorder (REST /books, 추후 WebSocket) → data/raw/polymarket/recordings/<condition_id>/
  → RecordingReader → ReplayBookStream → MM / Mispricing → PaperEngine → PnL Report
```

> 개발 환경에서는 API가 **HTTP 451**을 반환하므로 실제 수집에 성공한 적은 없다. 전체 파이프라인은
> fixture로 검증했다 (`record --source fixture`). 접근이 합법적으로 가능해지면 **설정만 바꿔서**
> (`--source polymarket` 또는 `MONEYLAB_RECORDER_SOURCE`) 실제 데이터를 기록할 수 있다.

| 기능 | 구현 |
|---|---|
| `PolymarketRecorder` 인터페이스 (저장, 중복 처리, 상태, 오류 분류, backoff 공통) | `providers/polymarket/recorder/base.py` |
| REST snapshot recorder (`POST /books` 1회로 여러 market 기록, metadata 주기적 갱신) | `recorder/rest.py` |
| 저장 형식, atomic write, 중복 처리, restart/resume | `recorder/store.py`, `storage/atomic.py` |
| 무결성 검사 | `recorder/integrity.py` |
| replay (lazy, error 레코드 → kill switch에 전달) | `recorder/replay.py`, `paper/book_stream.ReplayBookStream` |
| 오프라인 source (fixture timeline을 1 poll = 1 snapshot으로 제공) | `recorder/fixture_source.py` |

### 저장 형식

```
data/raw/polymarket/recordings/<condition_id>/       (git 제외: data/raw/*)
  dataset.json                     condition_id, synthetic, source, interval
  state.json                       상태(running/completed/blocked_http_451/...), 카운터, 마지막 오류, 실행 이력
  metadata/<시각>_<hash12>.json    GET /clob-markets, GET /rewards/markets 원본과 요약
                                   (tokens/outcome, tick_size, min_order_size, fee schedule, reward config).
                                   내용이 바뀔 때만 새 버전 저장
  records/<YYYYMMDD>/<seq>.json    kind=book | unchanged | error, 레코드마다 sha256 checksum
```

- `book` 레코드는 `/books` 응답 항목을 **변형 없이** 저장하고(bid/ask levels, tick_size, min_order_size,
  last_trade_price, 서버 timestamp), 토큰별 요약(outcome, best_bid, best_ask, spread, depth)을 덧붙인다.
  각 레코드는 `metadata_hash`로 fee·reward 설정 버전을 참조한다.
- 중복 처리: 내용과 서버 timestamp가 모두 같으면 저장하지 않고 카운트만 한다(같은 서버 snapshot을 다시 받은 경우).
  내용만 같으면 작은 `unchanged` 레코드(`ref_seq`)를 남겨 시간 축은 유지하면서 디스크를 아낀다.
- 모든 파일은 temp → fsync → `os.replace` 순서로 원자적으로 쓴다. 중단 후 다시 시작하면 남은 `.tmp`를 지우고,
  디스크에 실제로 남은 마지막 seq와 hash에서 이어서 기록한다. 실제 데이터와 synthetic 데이터는 같은 dataset에 섞지 않는다.

### 오류 처리 (우회 기능 없음)

| 상황 | 동작 |
|---|---|
| HTTP 451 | **즉시 중단**하고 재시도하지 않는다. `state.json`에 `blocked_http_451`, 응답 status/headers/body(마스킹)를 기록한다. 원인은 추정하지 않는다 |
| HTTP 401/403 | 즉시 중단 (`access_denied`) |
| HTTP 429 | `Retry-After`(초 또는 HTTP-date)를 따른다. 없으면 backoff |
| 5xx, 네트워크 오류, 잘못된 payload | `error` 레코드를 남기고 지수 backoff + jitter로 계속한다. 연속 `MONEYLAB_RECORDER_MAX_FAILURES`회 실패하면 `failed` |
| 요청 간격 | 요청 사이에 최소 간격(0.5초)을 두고, poll 주기는 `--interval`로 정한다 |

replay에서 `error` 레코드는 error event가 되므로, kill switch가 기록 당시의 장애를 실시간과 똑같이 본다.

### 사용법

```powershell
python -m moneylab record --source fixture                         # 오프라인 (recordings-synthetic/)
python -m moneylab record --condition-id <id> --interval 60        # 실제 기록 (Ctrl+C로 중단하면 상태 저장, 다시 실행하면 이어서 기록)
python -m moneylab record --condition-id <a> --condition-id <b> --rebate-rate 0.25 --duration 86400
python -m moneylab record-verify data\raw\polymarket\recordings\<id>
python -m moneylab simulate --strategy mm --recording data\raw\polymarket\recordings\<id> [--start <unix>] [--end <unix>]
```

`record` 종료 코드: `0` 정상(완료, 중단, fixture 소진), `3` 451/403/연속 실패, `1` 저장소·설정 오류.
`record-verify`: `0` 정상, `1` 무결성 오류.

검증: fixture timeline을 기록한 뒤 replay하면 원본 timeline과 PnL, equity curve, fill이 **완전히 같다**
(`tests/test_replay.py`). 기록 데이터에는 외부 signal(`fair_yes`)이 없으므로 fair-value 전략은 동작하지 않는다.
maker rebate 비율은 CLOB가 제공하지 않는다. `--rebate-rate`로 지정하지 않으면 0으로 두고, metadata의 `rebate_rate_source`에 출처를 남긴다.

### 미검증 사항

`/books`, `/clob-markets`, `/rewards/markets` 응답의 필드 해석은 v0.2와 같은 공식 문서 기준이며, 실제 응답으로는 검증하지 못했다.
특히 다음은 실제 응답을 받은 뒤 확인해야 한다.
- 서버 `timestamp`의 단위(ms로 가정), 호가가 변하지 않았을 때 `timestamp`와 `hash`가 바뀌는지 여부(중복 처리 정책에 영향)
- `/books` 응답 항목의 `market` 필드. 기록할 때 market 구분은 `asset_id`와 metadata의 토큰 목록으로 한다

원본은 그대로 저장되므로, 해석이 틀렸더라도 다시 수집하지 않고 parser만 고쳐서 replay할 수 있다.

---

## v0.3.1: Upbit Public WebSocket Recorder + Replay

Upbit 공개 WebSocket으로 실제 KRW-BTC의 orderbook(30호가)과 trade를 받아 저장하고 replay한다.
**공개 시세만 사용한다.** API Key, Secret, JWT, 계좌, 주문, 입출금 코드는 없다.
기존 전략(MM, mispricing)은 예측시장 전제(가격 0~1, YES/NO 보완, 결산가 1.0)라서 Upbit 데이터에 **연결하지 않는다**
(`simulate --recording <upbit dataset>`은 거부한다).

```
Upbit Public WebSocket → parser → UpbitRecorder → data/raw/upbit/recordings/<market>/ (segments, atomic)
  → UpbitRecordingReader → paper.book_stream.ReplayBookStream
```

### 공식 문서 (2026-10-06 확인)

| 항목 | 내용 | 출처 |
|---|---|---|
| Public endpoint | `wss://api.upbit.com/websocket/v1` | [websocket-guide](https://docs.upbit.com/kr/reference/websocket-guide) |
| 구독 요청 | `[{"ticket"}, {"type","codes","is_only_snapshot"?,"is_only_realtime"?}, {"format"}]`, format `DEFAULT\|SIMPLE\|JSON_LIST\|SIMPLE_LIST` | websocket-guide |
| orderbook | `type, code, total_ask_size, total_bid_size, orderbook_units[{ask_price,bid_price,ask_size,bid_size}], timestamp(ms), level, stream_type`. 호가 수는 code 접미사 `.1/.5/.15/.30`, `level` 기본 0(모아보기 없음) | [websocket-orderbook](https://docs.upbit.com/kr/reference/websocket-orderbook) |
| trade | `type, code, trade_price, trade_volume, ask_bid(ASK=매도/BID=매수), trade_date, trade_time, trade_timestamp, timestamp, sequential_id(체결 번호, unique), prev_closing_price, change, change_price, best_ask/bid_price/size, stream_type` | [websocket-trade](https://docs.upbit.com/kr/reference/websocket-trade) |
| idle / heartbeat | 120초 동안 데이터 교환이 없으면 서버가 연결 종료. PING frame 또는 `"PING"` 메시지로 유지, `{"status":"UP"}` 응답 | websocket-guide |
| rate limit | 연결 초당 5회(IP), 메시지 연결당 초당 5회·분당 100회, 429는 다음 초에 재요청, 418은 반복 위반 시 차단(응답에 차단 시간 포함) | [rate-limits](https://docs.upbit.com/kr/reference/rate-limits) |
| 에러 | `{"error":{"name","message"}}` | websocket-guide |
| market list (REST) | `GET https://api.upbit.com/v1/market/all?is_details=true`, 초당 10회(IP) | [list-trading-pairs](https://docs.upbit.com/kr/reference/list-trading-pairs) |

MoneyLab은 `DEFAULT` format으로 `KRW-BTC.30` orderbook과 `KRW-BTC` trade를 구독하고 `level`은 보내지 않는다.

| 기능 | 구현 |
|---|---|
| 공통 recorder core (상태, 실패 분류, backoff+jitter, checksum) | `recording/core.py` (Polymarket recorder도 사용) |
| endpoint, 제한값, 문서 출처 | `providers/upbit/endpoints.py` |
| parser (orderbook, trade, status, error) → `OrderBook`, `TradeTick` | `providers/upbit/parser.py`, `domain/trades.py` |
| WebSocket transport (`websockets` sync, `proxy=None`, PING frame) | `providers/upbit/ws_client.py` |
| recorder (재연결, PING 텍스트, stale 감지, 429/418/451, 중복, 연속 실패 제한) | `providers/upbit/recorder/recorder.py` |
| 저장 (JSONL segment, atomic, resume) | `providers/upbit/recorder/store.py` |
| replay, 무결성 검사, 원본↔replay 비교 | `recorder/replay.py`, `recorder/integrity.py`, `recorder/verify.py` |
| 오프라인 scripted session (SYNTHETIC) | `recorder/fixture_source.py`, `tests/fixtures/upbit_ws_timeline_synthetic.json` |
| market list provider | `providers/upbit/provider.py` (`UpbitMarketDataProvider`) |

### 저장 형식

```
data/raw/upbit/recordings/<market>/            실제 데이터 (provenance=real, git 제외)
data/raw/upbit/recordings-fixture/<name>/...   fixture 재생 결과 (provenance=fixture)
  dataset.json                                 market, provenance, synthetic, origin, orderbook_units, 문서 출처
  state.json                                   상태, 카운터, 마지막 오류, 실행 이력, 디스크에 확정된 last_seq
  segments/<YYYYMMDD>/<first_seq>.jsonl        수신한 메시지 1개 = 1줄, 불변, atomic write
```

- 각 줄에는 `raw`(서버가 보낸 원문 텍스트 그대로), `event_type`, `market`, `exchange_timestamp`(메시지 `timestamp`, ms),
  `received_timestamp`(수신 직후 로컬 UTC epoch 초), `connection_id`, `local_sequence`, `provenance`, `checksum`이 있다.
  orderbook 줄에는 `best_bid, best_ask, spread, bid_depth, ask_depth`(+ levels, total sizes, level, stream_type),
  trade 줄에는 `sequential_id, trade_price, trade_volume, ask_bid, trade_timestamp`가 추가된다.
  원문을 보존하므로 `116409000.00000000` 같은 표현과 2^53을 넘는 `sequential_id`도 손실 없이 남는다.
- orderbook과 trade 사이에는 거래소 공통 sequence가 없으므로 만들지 않는다. replay 기본 정렬은
  `(exchange_timestamp, received_timestamp, local_sequence)`이고, `order="received"`로 도착 순서 재생도 가능하다.
- 중복 메시지도 저장하되 `duplicate: true`로 표시하고 replay에서 제외한다. trade는 `sequential_id` 기준이다.
  orderbook은 **timestamp와 내용이 모두 같을 때만** 중복으로 본다. 내용이 같고 timestamp가 다른 정상 호가는 지우지 않는다.
- 연결, 끊김, 실패도 줄로 남기므로 replay에서 error event(공백 구간)로 보인다.
- 버퍼는 2초 또는 500줄마다 segment로 flush한다. 크래시가 나면 flush 전 버퍼(최대 약 2초)를 잃지만, 디스크의 파일은 항상 완전하다.
  재시작하면 `.tmp`를 지우고 디스크의 마지막 `local_sequence`부터 이어서 쓰며, 최근 `sequential_id`를 다시 읽어 중복을 막는다.
- real과 fixture, origin, orderbook 단위가 다른 데이터는 같은 dataset에 섞지 않는다(`DatasetMismatch`).

### 연결과 오류 처리

| 상황 | 동작 |
|---|---|
| keep-alive | WebSocket PING frame 30초마다(`websockets`), `"PING"` 텍스트 기본 60초마다(`--ping-interval`, 120초 미만) |
| 시장 데이터 없음 60초 | stale로 보고 재연결 |
| HTTP 451 / 401 / 403 (handshake) | 즉시 중단, 재시도 없음, 원인 추정 없음 |
| HTTP 429 | `Retry-After` 또는 최소 1초 대기 |
| HTTP 418 | `Retry-After`가 있으면 그 시간, 없으면 60초 대기. `max_ban_wait`(600초)보다 길면 `banned_http_418`으로 중단 |
| 끊김, 네트워크 오류, 서버 error 메시지 | 지수 backoff + jitter(1초~60초), 연결 간격 최소 1초. 시장 데이터 없이 연속 10회 실패하면 `failed` |
| 메시지 전송 | 연결당 초당 5회, 분당 100회 이하로 제한 (`core/ratelimit.py`) |

### 사용법

```powershell
python -m moneylab record --provider upbit --duration 60                   # 실제 KRW-BTC (Ctrl+C로 중단, 다시 실행하면 이어서 기록)
python -m moneylab record --provider upbit --market KRW-BTC --market KRW-ETH --duration 3600
python -m moneylab record --provider upbit --source fixture                # 오프라인 SYNTHETIC session
python -m moneylab record-verify data\raw\upbit\recordings\KRW-BTC
python -m moneylab replay-check data\raw\upbit\recordings\KRW-BTC          # 원본 ↔ 저장 요약 ↔ replay 비교, latency
python -m pytest -m network tests/test_upbit_live_smoke.py                 # 실제 연결 smoke test (60초)
```

기본 market은 `MONEYLAB_UPBIT_MARKETS`(기본 `KRW-BTC`), 호가 수는 `MONEYLAB_UPBIT_ORDERBOOK_UNITS`(기본 30)로 바꾼다.

### 실제 데이터로 확인한 것 (2026-10-06, KRW-BTC 90초)

- 메시지는 UTF-8 JSON **binary frame**으로 왔다. 서버가 `permessage-deflate`를 제안했다.
- orderbook 720건 모두 30 units, `level` 0. REALTIME 메시지도 30 units 전체였다(delta가 아님).
- trade의 `sequential_id`는 17자리 정수였다. 같은 스트림 안에서 exchange timestamp 역전은 없었다.
- `"PING"` 텍스트 4회를 보내는 동안 `{"status":"UP"}`를 7번 받았다(첫 수신 후 10초 간격).

### 미검증 사항

- `ask_bid`가 aggressor(taker) 방향인지는 문서에 명시되어 있지 않다. 그래서 `ASK→sell`, `BID→buy`로만 바꾼다.
- `sequential_id`가 단조 증가하는지는 문서에 없다(문서에는 unique라고만 되어 있다). 중복 판정에만 사용한다.
- 418 응답에서 차단 시간이 표시되는 형식(헤더인지 본문인지)은 문서에 없다. 표준 `Retry-After`만 해석하고, 응답은 마스킹해서 기록한다.
- `"PING"` 텍스트가 메시지 rate limit에 포함되는지는 문서에 없다. 포함된다고 가정하고 제한한다.
- `{"status":"UP"}`의 수신 주기가 PING 텍스트와 PING frame 중 어느 쪽과 연결되는지는 확인하지 못했다.
- `received − exchange` 차이에는 로컬 시계와 거래소 시계의 오프셋이 포함된다. 순수 네트워크 지연이 아니다.

---

## v0.4 (Phase 1): Upbit KRW-BTC microstructure research pipeline

질문: t 시점의 orderbook/trade 상태가 t+1s/5s/10s/30s 가격 움직임을 **거래비용을 넘을 만큼** 예측하는가.
사전등록: `docs/research_v04_preregistration.md` + `configs/research_v04.toml` (두 파일의 SHA-256이 모든 run manifest에 기록된다).

```
raw (불변, recorder만 씀)  --record-verify-->  providers/upbit/research_export.py  -->  MarketEvent (+ quality flag)
   --> research/ : 1초 wall-clock as-of grid --> features --> labels --> 시간순 split (embargo, purge, test lock)
   --> research-stats (train/validation) --> leaderboard --> research-final (test, 한 번만)
```

- 시간 축은 로컬 수신 시각이다. 행 t는 `received_timestamp <= t`인 이벤트만 쓴다(도착 순서 누적 최대 시각). `received − exchange` 차이는 품질 지표로만 쓴다.
- 품질 flag(`warmup`, `stale_book`, `crossed_book`, `locked_book`, `timestamp_reverse`, `sequence_gap`, `duplicate`, `reconnect_boundary`)는 삭제하지 않고 기록한다. 제외 여부는 research layer가 정하고 사유별로 집계한다.
- label: 미래 mid 수익률(wall-clock)과 체결 가능 수익률(VWAP, 0.001/0.01 BTC, 지연 0/100/250ms). depth가 부족하면 NaN이고, forward-fill은 하지 않는다.
- 비용: `analytics/spot_costs.py`. 수수료는 설정값이며 기본 시나리오는 5/15/25bp다. 계정 수수료가 확정되기 전에는 가장 비싼 시나리오로 판정한다.
- 통계: Spearman IC, quintile, 방향 적중률, stationary block bootstrap CI, Newey-West HAC, Benjamini-Hochberg FDR. 의존성은 표준 라이브러리뿐이다(processed 파일은 gzip JSONL, Parquet 미사용).
- 판정: `REJECT` / `RESEARCH_MORE` / `PAPER_CANDIDATE`. fixture/synthetic(`NOT_EVIDENCE`), dry-run, 6시간 미만, 단일 세션은 최대 `RESEARCH_MORE`다.
- 판정 근거는 `evidence_class`로 구분한다: `INSUFFICIENT_EVIDENCE`(표본 부족 → RESEARCH_MORE, REJECT 아님), `NEGATIVE_EVIDENCE`(충분한 표본에서 net ≤ 0 또는 gross < cost → REJECT), `POSITIVE_BUT_UNCONFIRMED`(→ RESEARCH_MORE).
- 장시간 수집(Phase 1.1): Ctrl+C·Ctrl+Break(SIGBREAK)·SIGTERM에 graceful stop, 10분마다 디스크 확인(5GB 미만이면 중단), 5분 heartbeat, 종료 시 `capture_manifest.json`(종료 사유, 디스크, raw sha256, clock 요약). `w32tm /stripchart` 기반 read-only clock monitor(`clock_monitor.jsonl`)는 품질 metadata일 뿐 보정에 쓰지 않는다. 단독 실행: `python -m moneylab clock-monitor`.
- test split은 `locked/`에만 있다. `research-stats`는 열 수 없다. `research-final`은 사전등록 해시가 같고 validation이 끝난 경우에만, run마다 **한 번** 연다.

```powershell
python -m moneylab research-build data\raw\upbit\research\<session>\KRW-BTC     # 실데이터만 (fixture: --allow-fixture, NOT_EVIDENCE)
python -m moneylab research-build <dir> --dry-run --embargo-seconds 15          # 짧은 데이터로 파이프라인 점검 (DRY_RUN)
python -m moneylab research-stats data\processed\research\<run>
python -m moneylab research-final data\processed\research\<run>                # test split, run당 1회
```

---

## 설치

Python 3.12 이상이 필요하다 (개발과 검증은 3.14.8에서 진행).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
pip install -e . --no-deps
```

`.env`는 선택 사항이다. 필요하면 `.env.example`을 복사해서 사용한다. v0.1에는 비밀정보가 필요 없다.

## 사용법

```powershell
python -m moneylab scan                                   # 실제 API 스캔
python -m moneylab scan --min-liquidity 10000 --max-days 30 --binary-only --sort volume24h --top 20
python -m moneylab scan --source fixture                  # 오프라인 (샘플 데이터)
python -m moneylab scan --source fixture --fixture data\raw\polymarket\<file>.json
python -m moneylab diagnose                               # 연결/HTTP 오류 진단
python -m moneylab diagnose --url https://gamma-api.polymarket.com/events?limit=1

python -m moneylab book                                   # fixture 호가창: spread, microprice, depth
python -m moneylab book --source polymarket --token <token_id>
python -m moneylab simulate --strategy mm                 # market-making 오프라인 시뮬레이션
python -m moneylab simulate --strategy mispricing         # 차익 + fair-value 오프라인 시뮬레이션
python -m moneylab simulate --strategy fair-value --resolution no   # 결과 민감도 확인
python -m moneylab simulate --timeline data\raw\polymarket\clob\<recorded>.json --kelly 0.1 --save
```

종료 코드는 다음과 같다.

| 코드 | 의미 |
|---|---|
| `0` | 성공 |
| `3` | 데이터 소스 접근 불가 (처리된 오류) |
| `1` | 예상치 못한 오류 (처리된 오류) |
| `2` | 잘못된 인자 |

터미널 폭이 130칸 미만이면 Spread, Volume, Flags 열을 숨긴다.

## 테스트

```powershell
python -m pytest            # 오프라인 테스트 (네트워크 불필요)
python -m pytest -m network # 실제 네트워크 테스트 (Upbit 공개 WebSocket, 약 60초)
```

---

## 구조

```
src/moneylab/
├── config.py               환경변수 설정 (비밀정보 없음)
├── cli.py, __main__.py     CLI 진입점
├── core/                   HTTP(timeout, 재시도, 진단), 예외, 비밀정보 마스킹, 로깅, rate limiter
├── domain/                 공급자 중립 Market/Outcome, OrderBook, TradeTick, MarketEvent(research)
├── recording/              공급자 중립 recorder core (상태, 실패 분류, backoff, checksum)
├── providers/
│   ├── base.py             MarketDataProvider, RecordedBookSource 인터페이스
│   ├── polymarket/         Gamma/CLOB client, 파서, provider 어댑터, recorder/ (기록·무결성·replay)
│   └── upbit/              공개 WebSocket transport, 파서, market list provider, recorder/ (기록·무결성·replay)
├── scanner/                공급자 독립 스캐너 (필터, 정렬, 플래그)
├── analytics/              metrics(MDD, spread, microprice, depth), costs(fee/rebate), spot_costs, rewards, ev
├── research/               v0.4 as-of grid, features, labels, split/test lock, stats, leaderboard, pipeline
├── storage/                data/raw JSON, data/processed CSV, atomic write
├── display/                rich 콘솔 출력
├── strategy/               Strategy→Signal, MarketMakingStrategy→Quote, MispricingStrategy→TradeIntent
├── risk/                   inventory risk, kill switch, RiskCheck
├── sizing/                 capped fractional Kelly
├── paper/                  paper engine, maker fill model, book stream, simulation runner
├── pnl/                    ledger (PnL 분해), report (채택 규칙)
├── execution/  (인터페이스만, 실거래 구현 없음 - docs/live_execution_design.md)
├── backtest/   (예정)
tests/                      오프라인 단위 테스트 + fixtures
data/raw, data/processed    생성 데이터 (git 제외)
```

### 의존성 방향

```
cli → scanner → providers.base (MarketDataProvider) ← providers.polymarket, providers.upbit
         ↘ domain ↙
strategy / risk / backtest / paper / execution / research → domain, analytics   (공급자 import 금지)
providers.* → recording (공통 core). providers.upbit와 providers.polymarket은 서로 import하지 않는다
```

새 데이터 소스를 추가할 때는 `MarketDataProvider`를 구현해서 `Market`을 반환하게 하면 된다.
스캐너와 전략 코드는 수정할 필요가 없다.

## 보안 원칙

- API Key, private key, seed phrase를 코드, 로그, fixture, 커밋에 넣지 않는다.
- `.env`는 `.gitignore`에 등록되어 있다. 예시는 `.env.example`만 커밋한다.
- 로그와 진단 출력은 `core/redaction.py`를 거친다. 64자리 hex 키, `key=value` 형태의 비밀값, seed phrase 형태의 문자열, IP 주소, 인증·쿠키 헤더를 마스킹한다.
- HTTP 세션은 `trust_env=False`로 생성하므로 환경변수 프록시를 자동으로 사용하지 않는다.

## 로드맵

| 단계 | 내용 |
|---|---|
| v0.1 | Scanner, 진단, 오프라인 테스트 ✅ |
| v0.2 | CLOB 호가 reader, 비용·리베이트·리워드 모델, MM/mispricing 전략, paper engine, PnL 분해, kill switch (fixture 기반 오프라인) ✅ |
| v0.3 | Real Market Data Recorder (REST), atomic 저장, resume, 451 중단, 무결성 검사, ReplayBookStream ✅ (실제 수집은 접근 가능해진 뒤) |
| v0.3.1 | Upbit 공개 WebSocket recorder (KRW-BTC orderbook 30호가 + trade), 공통 recording core, replay 검증 ✅ (실제 데이터로 확인) |
| v0.3.x | Polymarket WebSocket recorder, 일 단위 압축, 실제 기록으로 fixture 교체, queue-position fill 모델, 현물 시장용 비용 모델·전략 |
| v0.4 | 실데이터 microstructure 연구 pipeline (Phase 1 구현, 6시간 수집 전) → Paper trading, PnL tracking, 지표 리포트 |
| v0.5 | Risk management, position sizing, kill switch |
| v1.0 | Live execution. 별도 검토, 명시적 opt-in, 소액 한도를 전제로 하며, 합법적으로 접근 가능한 환경에서만 진행 |

## Git / GitHub

- 기본 브랜치는 `main`이다. 기능은 브랜치에서 개발하고 PR로 병합한다.
- 커밋 전에 `python -m pytest`를 통과시키고, `git status`에 `.env`나 데이터 파일이 없는지 확인한다.
