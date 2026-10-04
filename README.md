# MoneyLab

데이터 기반 투자·예측시장 전략을 분석하고 수익 기회를 탐색하는 Python 프로젝트.

최종 목표는 **검증된 수익성을 가진 자동매매 시스템**이며, 다음 순서로 단계적으로 진행한다.

```
Scanner (v0.1) → 호가창 전략 연구·오프라인 시뮬레이션 (v0.2) → 데이터 축적 → Paper Trading(실데이터) → Live Execution
```

> **현재 버전(v0.2)은 읽기 전용이다.** 실제 주문, 지갑 연결, 개인키 사용, 자동매매, 실거래 자금 사용 기능은 없다.

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
│   └── polymarket/         Gamma client(API/파일), 파서, provider 어댑터
├── scanner/                공급자 독립 스캐너 (필터, 정렬, 플래그)
├── analytics/              metrics(MDD, spread, microprice, depth), costs(fee/rebate), rewards, ev
├── storage/                data/raw JSON, data/processed CSV  (예정: SQLite)
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
| v0.2.x | 실제 호가 기록(합법적 접근 시)으로 fixture 교체, SQLite 스냅샷, queue-position fill 모델 |
| v0.3 | Strategy engine, 비용 모델(수수료, spread, slippage), 백테스트 |
| v0.4 | Paper trading, PnL tracking, 지표 리포트 |
| v0.5 | Risk management, position sizing, kill switch |
| v1.0 | Live execution. 별도 검토, 명시적 opt-in, 소액 한도를 전제로 하며, 합법적으로 접근 가능한 환경에서만 진행 |

## Git / GitHub

- 기본 브랜치는 `main`이다. 기능은 브랜치에서 개발하고 PR로 병합한다.
- 커밋 전에 `python -m pytest`를 통과시키고, `git status`에 `.env`나 데이터 파일이 없는지 확인한다.
