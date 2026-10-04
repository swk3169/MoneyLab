# MoneyLab

데이터 기반 투자·예측시장 전략을 분석하고 수익 기회를 탐색하는 Python 프로젝트.

최종 목표는 **검증된 수익성을 가진 자동매매 시스템**이며, 다음 순서로 단계적으로 진행한다.

```
Scanner (v0.1) → 데이터 축적(SQLite) → Strategy → Backtest → Paper Trading → Risk/Sizing → Live Execution
```

> **현재 버전(v0.1)은 읽기 전용이다.** 실제 주문, 지갑 연결, 개인키 사용, 자동매매, 실거래 자금 사용 기능은 없다.

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
├── analytics/metrics.py    net return, win rate, EV, profit factor, MDD, 비용, spread, slippage, VWAP
├── storage/                data/raw JSON, data/processed CSV  (예정: SQLite)
├── display/                rich 콘솔 출력
├── strategy/   (인터페이스)  Strategy → Signal
├── risk/       (인터페이스)  RiskCheck → RiskDecision
├── execution/  (인터페이스만, 실거래 구현 없음)
├── sizing/ backtest/ paper/ pnl/   (예정)
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
| v0.2 | SQLite 스냅샷 저장(시계열), 실제 응답 기반 fixture 갱신, CLOB 호가(`/book`)로 실제 spread와 VWAP 계산 |
| v0.3 | Strategy engine, 비용 모델(수수료, spread, slippage), 백테스트 |
| v0.4 | Paper trading, PnL tracking, 지표 리포트 |
| v0.5 | Risk management, position sizing, kill switch |
| v1.0 | Live execution. 별도 검토, 명시적 opt-in, 소액 한도를 전제로 하며, 합법적으로 접근 가능한 환경에서만 진행 |

## Git / GitHub

- 기본 브랜치는 `main`이다. 기능은 브랜치에서 개발하고 PR로 병합한다.
- 커밋 전에 `python -m pytest`를 통과시키고, `git status`에 `.env`나 데이터 파일이 없는지 확인한다.
