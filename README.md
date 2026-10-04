# MoneyLab

데이터 기반 투자·예측시장 전략을 분석하고 수익 기회를 탐색하는 Python 프로젝트.

최종 목표는 **검증된 수익성을 가진 자동매매 시스템**이며, 다음 순서로 단계적으로 진행한다.

```
Scanner (v0.1) → 호가창 전략 연구·오프라인 시뮬레이션 (v0.2) → 실데이터 Recorder·Replay (v0.3) → Paper Trading(실데이터) → Live Execution
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
```

---

## 구조

```
src/moneylab/
├── config.py               환경변수 설정 (비밀정보 없음)
├── cli.py, __main__.py     CLI 진입점
├── core/                   HTTP(timeout, 재시도, 진단), 예외, 비밀정보 마스킹, 로깅
├── domain/models.py        공급자 중립 Market/Outcome 모델
├── providers/
│   ├── base.py             MarketDataProvider 인터페이스
│   └── polymarket/         Gamma/CLOB client, 파서, provider 어댑터, recorder/ (기록·무결성·replay)
├── scanner/                공급자 독립 스캐너 (필터, 정렬, 플래그)
├── analytics/              metrics(MDD, spread, microprice, depth), costs(fee/rebate), rewards, ev
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
cli → scanner → providers.base (MarketDataProvider) ← providers.polymarket
         ↘ domain.models ↙
strategy / risk / backtest / paper / execution → domain, analytics   (공급자 import 금지)
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
| v0.3.x | WebSocket recorder, 일 단위 압축, 실제 기록으로 fixture 교체, queue-position fill 모델 |
| v0.4 | Paper trading, PnL tracking, 지표 리포트 |
| v0.5 | Risk management, position sizing, kill switch |
| v1.0 | Live execution. 별도 검토, 명시적 opt-in, 소액 한도를 전제로 하며, 합법적으로 접근 가능한 환경에서만 진행 |

## Git / GitHub

- 기본 브랜치는 `main`이다. 기능은 브랜치에서 개발하고 PR로 병합한다.
- 커밋 전에 `python -m pytest`를 통과시키고, `git status`에 `.env`나 데이터 파일이 없는지 확인한다.
