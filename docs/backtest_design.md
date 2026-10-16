# MoneyLab 백테스트 시스템 설계 (BT-0)

- 상태: **DRAFT (BT-0 설계 문서). 코드 없음, 미커밋.** 작성 2026-10-15.
- 범위: Upbit KRW 현물, 단일 자산(KRW-BTC), 일 단위 long/cash 전략의 **비용 후 수익성 검증용 백테스트**.
- 표시: BT-1–BT-4의 모든 실행 결과는 합성 데이터에서 나오므로 **SYNTHETIC / NOT_EVIDENCE**다. 실데이터 결과는 BT-5부터이며,
  그때도 증거 수준(L1/L2/L3)은 `docs/research_v06_preregistration_draft.md`(이하 "v0.6 초안") 2절을 따른다.
- 이 문서는 수익률, 성능, 검정력에 대한 주장을 하지 않는다. 수치가 나오면 출처(실측, 초안의 가정, 미검증)를 함께 적는다.
- 각 단계(BT-1–BT-6)는 별도 승인 후 진행한다. 코드 작성, 테스트 실행, 커밋은 서로 다른 승인 대상이다.

## 0. 불변 조건

| 항목 | 상태 |
|---|---|
| F3/F4 결과와 판정 | 변경하지 않는다. H-a0 FAIL, F3 D2 `selected: null`, F4 undetermined 유지 |
| F5 | 보류 |
| `research/v06` 코드 | 수정하지 않는다. `backtest/`는 이 패키지를 **런타임에 import하지 않는다**(13절) |
| Polymarket 전용 모듈 | `paper/`, `pnl/`, `sizing/`, `strategy/`를 직접 확장하지 않는다 |
| v0.6 초안 | 이 문서는 초안을 바꾸지 않는다. 초안과 다른 선택이 필요하면 16절 미확정 사항으로 올린다 |
| 실거래 | 범위 밖(CLAUDE.md 절대 규칙 1). 주문, API key, 계좌 연결 없음 |

## 1. 목적과 비목적

**목적.** 사전에 고정한 규칙의 long/cash 전략이 수수료, spread, slippage, 시장 충격을 뺀 뒤에도 자산을 늘리는지를 **재현 가능하고
미래 정보가 섞이지 않는 방식**으로 계산한다. 계산 결과는 v0.6 초안의 판정표(11.3절)에 들어가는 입력이다.

**비목적.**
- 파라미터 탐색과 최적화 도구를 만들지 않는다. 백테스터는 사전등록된 파라미터만 받는다.
- 통계 검정(H1 bootstrap, H2 무작위화)을 다시 구현하지 않는다(14.2절, 3.4절).
- 호가 수준 체결 시뮬레이션(L2 replay)은 하지 않는다. OHLCV 기반 근사만 한다.
- 실시간 주문, 모의거래 실행 엔진은 BT-6 이후의 별도 설계 대상이다.

## 2. 전체 아키텍처

```
providers/upbit (기존)                 domain (신규 타입)            backtest/ (신규 패키지)
┌──────────────────────────┐        ┌────────────────────┐       ┌─────────────────────────────────────┐
│ candles.py               │        │ bars.py            │       │ data.py      BarSeries, AsOfView     │
│ candle_store.py          │──────▶ │  Bar               │ ────▶ │ strategy.py  LongCashRule (M/R)      │
│ bar_export.py (신규)     │ Bars + │  BarProvenance     │       │ execution.py FillModel (E0–E3, 진단) │
│  - verify_candle_pull    │ 출처   │  (provider-neutral)│       │ costs.py     CostModel               │
│  - Candle → Bar 변환     │        └────────────────────┘       │ portfolio.py ResearchBook, Account   │
│  - 구간 분리·vault 기록   │                                     │ ledger.py    TradeLedger, Equity     │
└──────────────────────────┘                                     │ metrics.py   지표 (analytics 재사용)  │
                                                                 │ benchmarks.py B2, B3, B4 (B1은 BT-2) │
storage/atomic.py (기존) ◀──────────────────────────────────────── │ run.py       실행, manifest, SHA     │
analytics/metrics.py (기존, 순수 함수) ◀────────────────────────── │ vault.py     Holdout/Forward (BT-3)  │
                                                                 └─────────────────────────────────────┘
cli.py: `backtest` 명령 (BT-2, `--source fixture` 우선)
tests: research/v06의 procedures·synthetic는 **테스트에서만** 기준 구현으로 import (교차검증)
```

- 의존 방향은 `providers/upbit → domain ← backtest`이다. `backtest/`는 provider를 모른다.
  기존 `providers/upbit/research_export.py`(raw → domain `MarketEvent`)와 같은 형태다.
- `backtest/`가 쓰는 기존 모듈은 `domain`, `analytics.metrics`, `storage.atomic`, `core`(예외, 로깅)뿐이다.

## 3. 데이터 흐름

```
[수집, 기존·승인 필요] candles-pull (live는 매번 승인, dry-run 먼저)
      │  data/raw/upbit/candles_v06/<pull_id>/  pages/NNNN.json + meta + pull.json (SHA-256)
      ▼
[검증, 기존] candles-verify: 해시, 파일 목록, replay 일치                    → 실패 시 중단
      ▼
[변환, 신규] providers/upbit/bar_export.py
      │  Candle(Decimal) → Bar, 출처(BarProvenance) 부착
      │  중복·결측 보고, 확정 규칙 재확인, 구간 분리(확증 / holdout / 제외 / forward)
      │  holdout·forward 구간은 vault로만 기록 (BT-3)
      ▼
data/processed/backtest_bars/<bars_id>/  bars_<interval>.jsonl + bars_manifest.json + SHA256SUMS.txt
      ▼
[백테스트, 신규] backtest.run
      │  BarSeries 적재 → SHA 재확인 → AsOfView(horizon = 구간 끝)
      │  신호(일봉, 확정분만) → 주문 의도 → 체결 모델(1시간봉) → 비용 → 포트폴리오 → 원장·평가금액
      ▼
data/processed/backtest/<run_id>/  trades.jsonl, equity.jsonl, metrics.json, manifest.json, SHA256SUMS.txt
      ▼
[판정, 별도] v0.6 판정표 입력. 통계 검정은 research 쪽에서 별도 실행(14.2절)
```

## 4. 데이터 계층

### 4.1 `domain.bars.Bar` (신규, provider-neutral)

| 필드 | 타입 | 정의 |
|---|---|---|
| `market` | str | 예: `KRW-BTC` |
| `interval` | str | `day` 또는 `hour` |
| `start_utc`, `end_utc` | datetime (tz=UTC) | 구간 [start, end). Upbit `candle_date_time_utc`는 구간 **시작**이다(2026-10-12 실측) |
| `open`, `high`, `low`, `close` | Decimal | 첫 체결가, 고가, 저가, 마지막 체결가 |
| `value_krw`, `volume` | Decimal | 구간 누적 거래대금, 거래량 |
| `last_tick_ms` | int | 구간 마지막 체결 시각 |

- Bar는 불변(frozen)이고 시간대 없는 datetime을 거부한다.
- 가격은 Decimal로 보존한다. 계산 단계의 float 변환은 5.4절 규칙을 따른다.

### 4.2 `domain.bars.BarProvenance`

| 필드 | 값 |
|---|---|
| `kind` | `real` / `fixture` / `synthetic` |
| `source_pulls` | pull ID 목록과 각 `pull.json`의 페이지 SHA |
| `bars_sha256` | 정규화된 Bar JSONL의 SHA-256 |
| `confirmed_rule` | 확정 규칙(구간 끝 + 120 s ≤ min(로컬 수신 시각, 서버 Date))과 확정 시각 |
| `excluded_incomplete`, `duplicates_identical`, `duplicates_conflicting`, `gaps` | 개수와 목록 |

`kind != real`인 데이터로 만든 모든 결과에는 `SYNTHETIC / NOT_EVIDENCE`가 manifest와 출력 첫 필드에 들어간다. 실데이터와 합성 데이터를
한 run에 섞지 않는다(적재 시 거부).

### 4.3 `backtest.data.BarSeries`

- 한 시장, 한 interval의 Bar 목록. 적재할 때 다음을 검사하고 위반하면 예외를 낸다.
  - 시작 시각 오름차순 정렬(입력 순서에 의존하지 않음), 같은 시작 시각 중복 없음
  - interval 정렬(일봉 00:00 UTC, 1시간봉 정시)
  - `bars_sha256` 재계산 일치
- **결측은 오류가 아니다.** Upbit는 체결이 없는 구간을 생략한다(문서 기준). 결측 구간 목록을 보고하고, 보간하지 않는다.
  처리 규칙은 6.4절에 있다.

### 4.4 `backtest.data.AsOfView` (미래 정보 차단)

- `AsOfView(series, t)`는 **`end_utc ≤ t`이고 확정 시각 ≤ t인 Bar만** 돌려준다(기존 `candles.closed_as_of`와 같은 규칙).
- 전략은 `AsOfView`만 받는다. `BarSeries` 자체나 인덱스에 직접 접근할 수 없다.
- 구간 horizon: 각 평가 구간 G의 실행에서 `AsOfView`의 상한은 `min(t, G_end)`다(v0.6 초안 8.1-1). G_end 이후 Bar는 적재 단계에서
  아예 넘기지 않는다(이중 차단).
- 위반 시도(미래 인덱스, horizon 밖 시각)는 `LookAheadError`를 낸다. 경고로 넘기지 않는다.

## 5. 전략 계층

### 5.1 규칙 (BT 엔진 검증용 규칙과 v0.6 초안 6.1절 정의의 구분)

아래 표는 v0.6 초안 6.1절의 사전등록(research) 정의를 참고용으로 옮긴 것이다. M20/M60/M120은 N일 수익률 부호 momentum
전략이며 BT 엔진에는 구현되어 있지 않다. BT 엔진 검증용으로 구현된 별도 규칙은 아래 U1의 `sma20`, `sma60`, `sma120`과 `r5`다.

D일 종가를 C_D, r(a, b] = ln(C_b / C_a)라 한다.

| 전략 | 보유(1) 조건 | 현금(0) 조건 | 필요한 과거 일봉 |
|---|---|---|---|
| M20 | r(D−20, D] > 0 | 그 외 | 21개 |
| M60 | r(D−60, D] > 0 | 그 외 | 61개 |
| M120 | r(D−120, D] > 0 | 그 외 | 121개 |
| R5 | r(D−5, D] < 0 | 그 외 | 6개 |

- **U1 결정 (2026-10-16, 사용자): BT-1의 M 전략은 단순이동평균(SMA) 규칙이다.** 코드 이름은 `sma20`, `sma60`, `sma120`이다.
  - SMA_N(D)는 일봉 D−N+1 … D의 확정 종가 N개 평균(D 포함). C_D > SMA_N(D)이면 Long(1), C_D ≤ SMA_N(D)이면 Cash(0).
  - 일봉 D 확정 이후 신호를 만들고 D+1의 지정 시각에 주문한다. 데이터가 부족하면 거래하지 않고 사유를 기록한다.
  - R5는 위 표의 5일 수익률 규칙 그대로다(`r5`, C_D < C_{D−5}이면 Long).
  - **v0.6 초안의 M20/M60/M120(N일 수익률 부호)과는 다른 전략이다.** 초안은 바뀌지 않았고, 초안 규칙은 BT-1에 구현하지 않았다.
    초안의 판정에 SMA 규칙을 쓰려면 고정 전 초안 개정 또는 새 study가 필요하다.
- 필요한 일봉이 없거나 해당 일봉이 결측이면 신호는 `None`(현금 유지)이고 사유를 기록한다.
- 0 수익률(= 0)은 초안 M 규칙에서 현금, R5에서 현금이다(부등호가 엄격). BT `sma*` 규칙은 C_D = SMA_N(D)이면 현금이다(위 정의).
- 파라미터(N, 방향)는 config에서 읽고 config SHA를 manifest에 기록한다. 백테스터에는 파라미터를 바꾸는 반복 실행 기능이 없다.

### 5.2 신호와 주문 시점 (E0 기준)

| 시점 (UTC) | 사건 |
|---|---|
| D+1 00:00 | 일봉 D 구간 끝 |
| D+1 00:02 | 일봉 D 확정(+120 s). 신호 s[D] 계산. 이 시각까지 확정된 일봉만 사용 |
| D+1 00:59 | 주문 의도: s[D] ≠ 현재 포지션이면 시장가 진입 또는 청산 |
| D+1 01:00 | 근사 체결가 = 1시간봉 [00:00, 01:00) 종가. 수익률 기준 시각 |
| (D+1 01:00, D+2 01:00] | 포지션 s[D]의 보유 구간. 다음 날 같은 절차 반복 |

- 진입: 0 → 1 전환 시 전액 매수. 청산: 1 → 0 전환 시 전량 매도. 부분 진입, 손절, 피라미딩은 없다.
- 같은 캔들의 종가로 신호를 만들고 같은 종가에 체결하지 않는다(초안 6.3).
- 다른 시나리오(E1, E2, E3, 진단)는 6절 표의 시각을 쓴다. E2는 신호 s[D]가 아니라 s[D−1]이 한 칸 늦게 적용된다(초안과 `synthetic.py` 정의).

## 6. 체결 모델 (`backtest.execution`)

### 6.1 시나리오 (v0.6 초안 6.2절)

| 시나리오 | 주문 시각 | 근사 체결가 | 편도 κ (spread + slippage) | 용도 |
|---|---|---|---|---|
| E0 | D+1 00:59 시장가 | 1시간봉 [00:00, 01:00) 종가 | 5 bp | 기본 |
| E1 | D+1 01:59 | 1시간봉 [01:00, 02:00) 종가 | 10 bp | 스트레스 |
| E2 | D+1 23:59 | 일봉 D+1 종가 | 10 bp | 스트레스 |
| E3 | 없음 | 체결 1시간봉의 최악가(매수 고가, 매도 저가) | 10 bp | 보고 전용 경계값 |
| 진단 | 없음 | D+1 시가 | 5 bp | 낙관적 상한, 판정 미사용 |

**OHLCV 체결은 근사다.** 종가는 매수 체결인지 매도 체결인지 알 수 없는 마지막 체결가이고, 주문 시각과 근사 시각 사이 약 1분의
가격 변동, 과거 호가 깊이를 반영하지 못한다. 근사 체결가는 실제 체결가가 아니며 체결을 보장하지 않는다. 모든 출력의 manifest에
`fill_model: "ohlcv_approximation"`과 시나리오를 기록한다.

### 6.2 체결 가능성

| 상황 | 처리 (연구 모드) | 기록 |
|---|---|---|
| 체결 1시간봉이 없음(무체결 구간 생략) | 다음 1시간봉 종가에 체결. 24시간 안에 없으면 그 시나리오의 다음 기준 시각 종가 (초안 6.3) | `fill_substituted`, 지연 시간 |
| 다음 기준 시각까지도 없음 | 미체결. 포지션 유지, 다음 날 다시 시도 | `unfilled`, 연속 일수 |
| 주문 금액이 체결 구간 거래대금의 비율 p를 넘음 | **연구 모드에서는 체결하고 표시만 한다**(초안에 참여율 규칙이 없으므로 넣으면 study 변경) | `participation_ratio`, 초과 여부 |
| 데이터 결측으로 신호가 `None` | 현금 유지(보유 중이면 청산하지 않고 유지할지는 U4) | `signal_missing` |

- 미체결과 대체 체결 건수는 품질 지표(초안 Q10)로 보고한다.
- 계좌 모드(8.2절)는 참여율 상한을 적용해 부분 체결을 계산할 수 있지만, 판정에는 연구 모드만 쓴다.

### 6.3 시장 충격

ι(C) = ι_ref × √(C / C_ref), ι_ref = 1.0 bp, C_ref = 100만 KRW (**초안의 가정**, 근거는 v0.4 단일 세션 관측의 외삽).
100만 / 500만 / 1,000만 KRW에서 약 1.0 / 2.2 / 3.2 bp. C > 1,000만 KRW는 `CAPACITY_UNVERIFIED`.

### 6.4 결측과 평가 가격

- 보유 중인 날의 평가 가격은 기준 시각의 1시간봉 종가다. 그 1시간봉이 없으면 기준 시각 이전의 가장 최근 1시간봉 종가다(초안 6.3).
- 평가 가격 대체 건수를 보고한다. 미래 Bar로 결측을 채우지 않는다.

## 7. 거래 비용 모델 (`backtest.costs`)

### 7.1 항목 분리

거래 1건(진입 또는 청산)의 비용을 다음 항목으로 나눠 원장에 기록한다.

| 항목 | 기호 | 기준 금액 | 값 |
|---|---|---|---|
| 매수 수수료 | f_buy | 체결 금액(체결가 × 수량) | 편도 bp, 파라미터 |
| 매도 수수료 | f_sell | 체결 금액 | 편도 bp, 파라미터 |
| 반 spread | h | 근사 체결가 | κ의 일부 (보고용 분해) |
| slippage | s | 근사 체결가 | κ의 일부 (보고용 분해) |
| 시장 충격 | ι(C) | 근사 체결가 | 6.3절 |
| 미체결 | – | – | 비용이 아니라 상태로 기록(6.2절). 기회비용은 "체결 지연 없음" 대비 차이로 보고만 함 |

- **판정에 쓰는 합계는 초안 7절의 곱셈 규칙이다:** 거래 1건마다 자산 × (1 − f)(1 − κ − ι). 로그로는
  ln(1 − f) + ln(1 − κ − ι)이며, 기존 `procedures.trade_cost_log`와 같은 정의다(교차검증 대상, 14.2절).
- κ = h + s로 두고 h, s는 보고용 분해일 뿐 합계는 κ 하나로 계산한다. 기본값은 h = s = κ/2이고, 분해 비율은 판정에 영향이 없다.

### 7.2 이중 계산 방지

| 위험 | 규칙 |
|---|---|
| 수수료를 spread 조정 전 가격과 조정 후 가격에 두 번 부과 | 수수료는 **κ와 ι를 반영한 실효 체결 금액**에 한 번만 곱한다(곱셈 규칙의 (1 − f) 항) |
| spread를 κ와 별도로 다시 차감 | 캔들에는 bid/ask가 없으므로 spread는 κ 안에만 있다. 별도 spread 항목을 합계에 더하지 않는다 |
| 왕복 비용을 진입 시 한꺼번에 부과 | 진입과 청산에 각각 부과한다. 구간 끝의 가상 청산도 청산 비용을 낸다(초안 8.1) |
| 벤치마크와 다른 비용 적용 | B1·B2·B4에 같은 비용 규칙과 같은 기준 시각을 쓴다 |

- 단위 테스트에 항등식을 둔다: 원장의 항목별 비용 합 = 곱셈 규칙으로 계산한 자산 감소분(허용 오차 1e-12 상대).

### 7.3 수수료 상태

- 실제 계정 수수료를 확인하기 전까지 모든 결과에 `fee_status = FEE_UNCONFIRMED`를 기록한다.
- 민감도 시나리오: 편도 0(진단) / 5 / 15 / 25 bp. 판정 수수료는 확인 전 25 bp(초안의 보수적 가정).
- 확인 후에는 `account_fee_bps`와 출처(문서명 또는 화면, 확인 날짜, 매수·매도 구분, maker/taker 구분)를 config에 기록하고
  `fee_status = CONFIRMED`로 바꾼다. 확인 방법은 14.3절.
- 손익분기 수수료 f*(m_s = 0이 되는 편도 수수료)를 보고한다.

## 8. 포트폴리오 (`backtest.portfolio`)

두 가지 모드를 둔다. 판정은 연구 모드로만 한다.

### 8.1 연구 모드 `ResearchBook` (판정용)

- 자산 W는 실수 배수로만 추적한다(최소 주문, 수량 단위 없음). 포지션 ∈ {0, 1}, 보유 시 자산 전액이 BTC 노출.
- 일별 순 로그수익률 r_t = p_t × m_t + (거래가 있으면 거래 비용 로그), m_t는 기준 시각 간 시장 로그수익률.
  이 정의는 `procedures.segment_returns`와 같아야 한다(테스트로 강제).
- 현금 수익률 0(이자 없음), 공매도와 레버리지 없음(포지션은 0 또는 1).

### 8.2 계좌 모드 `Account` (보고용)

- KRW 현금(Decimal, 원 단위)과 BTC 수량(Decimal). 초기 자본 C ∈ {100만, 500만, 1,000만} KRW.
- 매수 수량 = floor_to_step((가용 KRW / (1 + f_buy)) / 실효 체결가). 매도는 보유 수량 전부(단위 내림 후 잔량은 기록).
- 최소 주문 금액, 수량 단위, 호가 단위는 config 값이며 **출처가 확인되기 전에는 `UNVERIFIED`**로 표시한다(14.6절).
- 최소 주문 금액 미만이면 주문하지 않고 `below_min_order`로 기록한다.
- 일별 평가금액 = KRW 현금 + 수량 × 평가 가격(6.4절).
- 수렴 검사: 최소 주문 0, 단위 0, 자본이 충분히 크면 계좌 모드 수익률이 연구 모드와 같아야 한다(테스트).

### 8.3 원장 (`backtest.ledger`)

| 기록 | 필드 |
|---|---|
| 거래(leg) | 신호 일자 D, 신호 값, 주문 시각, 체결 시각, 근사 체결가, 실효 체결가, 수량, 수수료, h, s, ι, 대체·미체결 표시, 가상 진입·청산 표시 |
| 왕복(round trip) | 진입 leg, 청산 leg, 보유 일수, 순손익(KRW, 로그), 비용 합계 |
| 일별 | 기준 시각, 포지션, 시장 수익률, 순수익률, 자산(연구 모드), 평가금액(계좌 모드), 노출 |

모든 손익은 거래 비용 차감 후(net) 값이다. 총손익(gross)은 같은 행에 따로 기록하지만 채택 판단에 쓰지 않는다.

## 9. 성과 지표 (`backtest.metrics`)

공통: 일별 순 로그수익률 r_t(연구 모드), 단순수익률 R_t = e^{r_t} − 1, 평가 일수 n, 달력 일수 T_d,
**연율화 기준 365일**(암호화폐 24/7 시장, 초안과 `procedures.ANNUALIZATION_DAYS`와 같음). 무위험 수익률 0.

| 지표 | 정의 | 비고 |
|---|---|---|
| 누적 순수익률 | exp(Σ r_t) − 1 | |
| CAGR | exp(Σ r_t × 365 / T_d) − 1 | T_d < 365이면 보고하되 표시 |
| Sharpe | mean(r_t) / sd(r_t) × √365, sd는 표본(n − 1) | `procedures.annual_sharpe`와 같은 정의(교차검증). sd = 0이면 None |
| Sortino | mean(r_t) / DD × √365, DD = √(mean(min(r_t, 0)²)) (전체 일수 기준) | DD = 0이면 None |
| Maximum Drawdown | 자산 곡선의 최대 고점 대비 하락 비율 (0–1) | 기존 `analytics.metrics.max_drawdown` 재사용. 로그 누적 정의(`procedures.max_drawdown`)와 일치 테스트 |
| Calmar | CAGR / MDD | MDD = 0이면 None |
| Profit Factor | 왕복 순손익 중 이익 합 / 손실 합 | 기존 `analytics.metrics.profit_factor`. 가상 청산 왕복 포함 여부를 함께 보고 |
| 승률 | 순손익 > 0인 왕복 비율 | 기존 `win_rate` |
| 거래 횟수 | 왕복 수, leg 수, 연간 왕복 수 | 가상 진입·청산 수 별도 |
| 회전율 | Σ |거래 금액| / 평균 자산 × 365 / T_d | 연구 모드는 leg마다 1 |
| 노출 비율 | 보유 일수 / n | |
| Buy & Hold 대비 초과 | Σ r_t − Σ r_t^{B2}, CAGR 차이 | B2: 진입·청산 각 1회 비용 |
| 현금 대비 | Σ r_t − 0 (현금 B3 = 0) | 사실상 전략 자체의 순수익 |
| 무작위 노출 대비 | m_s − mean_k(m^{B1}_k) | **초안의 핵심 비교.** BT-2에서 구현 |
| 연도별 순수익 | 달력 연도별 Σ r_t, 양(+)인 연도 비율 | 초안 E-c |
| gross/비용 비율, f* | 비용 전 수익 / 비용, 손익분기 수수료 | 초안 7절 보고 항목 |

- 모든 지표는 순수 함수이고 입력은 원장과 일별 수익률뿐이다. 같은 함수가 이후 paper·live에도 쓰인다(CLAUDE.md 아키텍처 규칙).
- 지표는 기술 통계다. 유의성 판단은 하지 않는다(14.2절).

## 10. 검증 체계

### 10.1 테스트 계획 (BT-1–BT-3, 모두 오프라인, 합성 데이터)

| 종류 | 내용 |
|---|---|
| 수작업 소형 사례 | 10–20일 Bar에서 신호, 체결가, 비용, 자산을 손으로 계산한 값과 일치 |
| 미래 정보 섭동 | 시각 t 이후 Bar를 무작위로 바꿔도 t 이전의 신호·체결·자산이 바이트 단위로 같다. 모든 전략과 시나리오 |
| AsOfView 차단 | 미래 인덱스·horizon 밖 접근이 `LookAheadError`를 낸다. 진행 중 캔들(확정 전)이 보이지 않는다 |
| 비용 항등식 | 항목별 비용 합 = 곱셈 규칙의 자산 감소. 수수료 0·κ 0이면 gross = net |
| 이중 계산 | 수수료만 / κ만 / 둘 다 켠 결과의 곱셈 관계 확인 |
| 교차검증 | `synthetic.make_path` 경로에서 연구 모드 일별 수익률이 `procedures.segment_returns` + `trade_cost_log`와 일치(상대 1e-12). Sharpe, MDD도 일치 |
| 경계 처리 | 구간 시작 가상 진입, 끝 가상 청산, 구간 밖 가격 미사용(초안 8.1) |
| 결측 | 1시간봉 결측 시 대체 체결 규칙, 미체결 기록, 보간 없음 |
| 계좌 모드 수렴 | 제약을 끄면 연구 모드와 일치. 최소 주문 미만은 주문 없음 |
| 재현성 | 같은 입력으로 두 번 실행해 출력 파일 SHA 동일. 실행 순서·프로세스와 무관 |
| 무결성 | Bar SHA 불일치, 출처 혼합(real + fixture), 기존 출력 디렉터리에 대한 쓰기를 거부 |
| 아키텍처 | `backtest/`가 `providers.*`와 `moneylab.research`를 import하지 않음(13절) |
| 알려진 정답 | 참 Sharpe가 알려진 합성 경로에서 결과가 기대 방향과 크기 범위에 있음(분포 확인이며 검정 아님) |

### 10.2 Walk-forward

- 이 전략들은 **추정하는 파라미터가 없다**(N 고정). 그래서 walk-forward는 재최적화가 아니라 **시간 안정성 분석**으로 정의한다.
  - 연도별 지표, 초안의 보조 하위 구간(2022-07-01 – 2024-03-31), 겹치지 않는 2년 창별 지표를 보고한다.
  - 창마다 독립 운용 기간 규칙(가상 진입·청산)을 적용한다.
- 앞으로 추정 파라미터가 있는 전략을 넣을 경우: 학습 창에서만 추정하고 다음 평가 창에 적용하며, 창 사이에 lookback 길이 이상의
  embargo를 둔다. 이것은 새 study의 설계 대상이다.
- walk-forward 결과는 판정에 쓰지 않는다(보고 전용).

### 10.3 Holdout 격리 (BT-3)

- 구간: 확증 평가(warmup 끝 – 2024-03-31), historical holdout(2024-04-01 – H_end), 제외 구간, forward(동결 후). 초안 8절과 같다.
- `bar_export`가 구간을 나눌 때 holdout·forward Bar는 **vault 디렉터리에만** 쓰고, 확증 평가용 Bar 파일에는 넣지 않는다.
- `HoldoutVault.open_once(config_sha, prereg_sha)`: 한 번만 열린다(기존 `research/split.LockedTestVault`와 같은 형태). 개봉 기록을
  남기고 재개봉을 거부한다.
- **raw 페이지에는 전체 기간 가격이 들어 있다.** 에이전트가 raw나 vault 파일을 직접 읽지 않도록 하는 guard 규칙은 초안 19.5절
  사양에 있고, 적용은 사용자 결정이다(16절 U9).

### 10.4 다중 전략 비교와 선택 편향

- 이 절의 primary 4개(M20, M60, M120, R5)는 v0.6 사전등록(research) 전략이다. BT 엔진 검증 전략 `sma20`, `sma60`, `sma120`은
  여기에 포함되지 않고, 그 결과(SYNTHETIC / NOT_EVIDENCE)는 사전등록 판정에 쓰지 않는다.
- primary 4개(M20, M60, M120, R5)는 **모두** 보고한다. 가장 좋은 전략만 고르거나 결과를 보고 전략을 빼지 않는다.
- 판정은 초안의 다중검정 규칙(H1·H2 IUT + Holm)을 따른다. 검정은 백테스터가 아니라 research 쪽에서 실행한다(14.2절).
- 보고: 4개 전략의 지표 표, 최고 Sharpe 전략의 deflated Sharpe(시도 수 9, 초안 6.1), 승자의 저주 경고.
- 효과 크기는 forward(L3) 추정치로만 주장한다(초안 2절).

## 11. 재현성과 무결성

| 항목 | 방법 |
|---|---|
| 결정론 | 백테스트 코어에는 난수가 없다. B1 벤치마크(BT-2)는 `research/stats.derived_seed`와 같은 방식의 자체 seed 함수(라벨 `"BT"`, `research` import 금지 때문에 별도 구현)를 쓰고, seed를 manifest에 기록 |
| 입력 고정 | Bar 파일 SHA, `bars_manifest.json`(pull ID, 페이지 SHA, 확정 규칙, 결측·중복 보고), config SHA, v0.6 사전등록 SHA |
| 코드 고정 | Git 커밋과 `uncommitted_changes`를 manifest에 기록. 실데이터 run(BT-5)은 미커밋 상태에서 거부 |
| 출력 | 새 run 디렉터리만 사용(존재하면 거부), `storage.atomic` 쓰기, `SHA256SUMS.txt`(LF, 상대 경로) |
| 재실행 검증 | `backtest-verify <run>`(BT-2): 입력 SHA 재확인 → 같은 커밋으로 재계산 → 출력 SHA 비교. 파일을 쓰지 않음 |
| 수치 | float64. 결과 JSON은 고정 소수 자릿수가 아니라 `repr` 전체 정밀도. 플랫폼 간 차이는 1e-12 상대 허용 |

## 12. 기존 코드 재활용 범위

| 기존 모듈 | 사용 | 방식 |
|---|---|---|
| `providers/upbit/candles.py` | 사용 | 수집, `Candle`, `closed_as_of` 규칙. 변경 없음 |
| `providers/upbit/candle_store.py` | 사용 | `verify_candle_pull`, `StoredPageClient`로 저장된 pull을 다시 읽음. 변경 없음 |
| `providers/upbit/candle_fixture.py`, `tests/fixtures/upbit_candles_synthetic.json` | 사용 | 오프라인 테스트 입력 |
| `storage/atomic.py` | 사용 | 출력 쓰기와 SHA |
| `analytics/metrics.py` | 사용 | `max_drawdown`, `profit_factor`, `win_rate`, `net_return`. 새 지표(Sharpe, Sortino, CAGR)는 같은 모듈 형식의 순수 함수로 `backtest/metrics.py`에 둔다(기존 함수는 수정하지 않음) |
| `analytics/spot_costs.py` | 참고 | 수수료 파라미터화 원칙. 호가 VWAP 함수는 캔들에 쓰지 않음 |
| `risk/kill_switch.py` | 참고 | 판정용 위험 한도(초안 12행 MDD)는 지표로 보고. 백테스트에서 kill switch를 실행하지 않음 |
| `research/split.py` | 참고 | vault 패턴. v0.4 코드는 수정하지 않음 |
| `research/v06/procedures.py`, `synthetic.py` | **테스트에서만** | 교차검증 기준 구현과 합성 경로. 런타임 import 금지 |
| `paper/`, `pnl/`, `sizing/`, `strategy/` | 사용 안 함 | Polymarket 이진 상품 전제. 확장하지 않음 |

## 13. 의존성 규칙

| 규칙 | 강제 방법 |
|---|---|
| `backtest/`는 `providers.*`를 import하지 않음 | 기존 `tests/test_architecture_and_cli.py`가 이미 `backtest`를 provider-neutral 목록에 넣어 Polymarket·Upbit import를 검사한다 |
| `backtest/`는 `moneylab.research`(v0.4, v0.6 모두)를 import하지 않음 | 새 아키텍처 테스트 추가(BT-1) |
| `research/`는 `backtest/`를 import하지 않음 | 새 아키텍처 테스트. 통계 검정은 백테스트 출력 파일(일별 수익률)을 읽어서만 수행 |
| `domain.bars`는 어떤 provider도 import하지 않음 | 기존 domain 규칙 |
| Candle → Bar 변환은 `providers/upbit/bar_export.py`에만 둠 | 코드 리뷰와 위 테스트 |

## 14. 추가 확인사항 검토

### 14.1 Bar 타입의 위치

**`domain`(신규 `domain/bars.py`)을 권장한다.** `backtest/`는 아키텍처 테스트상 `providers.upbit`를 import할 수 없으므로, provider의
`Candle`을 직접 쓸 수 없다. `domain`에 provider-neutral `Bar`를 두고 변환은 provider 쪽(`bar_export.py`)에서 한다. v0.4의
`research_export.py`(raw → `domain.MarketEvent`)와 같은 구조라 일관성도 맞다. Bar를 provider에 두면 아키텍처 테스트를 바꿔야
하므로 권장하지 않는다.

### 14.2 데이터 수집 계층과 백테스트 계층의 의존성, 통계 엔진과의 관계

- 수집(`providers/upbit`) → 변환(`bar_export`) → 파일(`data/processed/backtest_bars`) → 백테스트(`backtest/`). 백테스트는 파일만
  읽는다. 네트워크 호출이 없다.
- 통계 검정(H1 bootstrap, H2 무작위화, 무익성, Holm/IUT)은 `research/v06/procedures.py`에 있다. 이 엔진은 구현 재현성과 이론 π
  일관성(반증 부재)은 확인됐지만, **엔진 점검 기준의 FAR 통제가 미확정**이다(H-a0 FAIL, F3 `selected: null`, F4 undetermined).
  또한 H1은 짧은 표본에서 공칭 α보다 자주 기각하는 알려진 수준 왜곡이 있다(F2 동기 자료, F3 π에 반영).
- 따라서 백테스트 출력에 붙는 H1/H2 p값은 **"검증되지 않은 공학적 점검 상태"** 라벨과 함께 보고하고, 판정 반영 방식은 사전등록
  결정 D10(16절)으로 정한다. **어떤 통계 출력도 매매 신호나 실거래 승격 근거로 쓰지 않는다.**

### 14.3 Upbit 수수료 확인 방법

| 방법 | 가능 여부 | 비고 |
|---|---|---|
| Upbit 공식 수수료 안내(웹·앱)를 사용자가 직접 확인 | **권장** | 시장별(KRW, BTC, USDT), 매수·매도, 이벤트·할인 여부, 확인 날짜와 화면 위치를 기록. 에이전트는 이 값을 추측하지 않는다 |
| 사용자의 계정 화면(거래 내역의 수수료 항목)에서 사용자가 확인 | 가능 | 실제 적용 요율 확인. 내역 원본은 저장소에 넣지 않고 값과 날짜만 기록 |
| 인증 API(계정·주문 정보 endpoint)로 조회 | **범위 밖** | API key가 필요하다. CLAUDE.md 절대 규칙 1·2에 따라 사용자 승인 전에는 구현하지 않는다. endpoint 이름과 응답 필드도 미검증 |
| 공개 시세 API | 불가 | 수수료 정보가 없다 |

- 과거 기간의 수수료는 현재 요율과 다를 수 있다. 과거 요율 이력은 미검증이므로, 백테스트 전 기간에 확인된 현재 요율과 민감도
  시나리오(5/15/25 bp)를 함께 적용하고 이 한계를 결과에 적는다.

### 14.4 기존 1시간봉 데이터의 사용 가능 범위

- **현재 보유량:** 1시간봉 10개 요청 중 확정 9개(2026-10-12 수집 1회분, `hour_KRW-BTC_20261012T094742435199Z`). 일봉도 같은 규모다.
  이 데이터는 파이프라인 검증용이며 백테스트에 쓸 수 없다.
- 이 데이터의 가격은 2026-10-03 – 10-12 구간에 해당하고 이미 노출되었다(초안 부록 B). 어떤 평가 구간에도 쓰지 않는다.
- **필요량:** 체결 근사(E0, E1)와 평가 가격에 1시간봉이 전 평가 기간에 필요하다. count 200 기준 산술로 1시간봉 1년은 약 44페이지,
  일봉 1년은 2페이지다. 전체 요청 수는 상장일(미확인)과 1시간봉 과거 제공 범위(미확인)에 달려 있다.
- **확인되지 않은 사실:** Upbit가 1시간봉을 상장 초기까지 제공하는지, `to`의 경계 포함 여부, 과거 캔들의 사후 수정. 1시간봉 제공
  범위가 일봉보다 짧으면 그 이전 기간은 E0/E1을 계산할 수 없다. 이 경우 처리(평가 시작일 조정 또는 E2만 사용)는 사전등록 고정 전에
  정해야 한다(16절 U5). 범위 확인은 dry-run과 소량 live 수집(승인)으로 한다.

### 14.5 데이터 확보 기간과 검증 기간의 분리

| 구분 | 내용 |
|---|---|
| 수집 시점 | 과거 데이터는 **사전등록 고정 후** 한 번에 수집하고 첫 수집본을 기준 데이터로 고정한다(초안 4절). 고정 전에는 가격을 분석하지 않는다(CLAUDE.md) |
| 수집 범위 | 한 번의 수집이 확증·holdout·제외 구간 가격을 모두 포함한다. 그래서 수집 직후 `bar_export`가 구간을 나누고 holdout을 vault로 보낸다 |
| 확증 평가 | warmup 끝 – 2024-03-31. 이 구간 Bar 파일만 백테스트에 노출 |
| holdout | 2024-04-01 – H_end(D9). vault, 한 번 개봉 |
| 제외 구간 | 이미 노출된 날짜. 평가에 쓰지 않음(lookback만 허용) |
| forward | 동결일 이후 월 1회 수집(매번 승인). 별도 vault |
| lookback | 앞 구간 Bar는 다음 구간의 신호 계산(과거 방향)에만 쓸 수 있다 |

### 14.6 최소 주문 금액과 거래 단위

- 최소 주문 금액, 수량 소수 자릿수, KRW 호가 단위는 **미검증**이다. 추측해서 코드에 넣지 않는다(CLAUDE.md 절대 규칙 5).
- config에 `min_order_krw`, `qty_step`, `price_tick`과 출처·확인 날짜를 둔다. 확인 전에는 `UNVERIFIED`로 표시한다.
- **연구 모드(판정)는 이 값들을 쓰지 않는다**(실수 배수). 계좌 모드(보고)만 적용한다. 판정 자본 1,000만 KRW에서는 최소 주문의
  영향이 작을 것으로 보이지만, 이것은 확인 전 가정이다.
- 근사 체결가는 호가 단위에 맞지 않을 수 있다. 계좌 모드에서는 매수 올림·매도 내림(보수적)으로 맞추고 차이를 slippage에 포함해 기록한다.

### 14.7 체결 불가능한 구간

6.2절 표를 따른다. 요약: 무체결 구간은 다음 1시간봉, 24시간 안에 없으면 다음 기준 시각, 그래도 없으면 미체결로 포지션 유지.
거래소 점검·중단(시세 결측이 길게 이어지는 경우)은 구분할 정보가 캔들에 없으므로 결측 길이만 보고한다. 미체결과 대체 체결 건수는
품질 지표로 보고하고, 기준을 넘으면 데이터 품질 판정(초안 5절 Q)에 반영한다.

### 14.8 재현성과 무결성 검증 방법

11절과 같다. 핵심: (1) raw pull SHA → (2) Bar 파일 SHA → (3) config·사전등록 SHA → (4) 코드 커밋 → (5) 출력 SHA의 사슬을 manifest에
남기고, `backtest-verify`로 재계산 일치를 확인한다. 실데이터 run은 커밋된 코드와 고정된 사전등록에서만 허용한다.

## 15. 단계별 개발 로드맵

| 단계 | 내용 | 데이터 | 완료 기준 | 예상 규모 (추정) |
|---|---|---|---|---|
| BT-0 | 이 문서, 인터페이스 확정 | 없음 | 사용자 승인 | – |
| BT-1 | `domain.bars`, `backtest.data`(BarSeries, AsOfView), `strategy`(M/R 규칙), `portfolio.ResearchBook`, `ledger`, 단순 비용(f, κ), 지표 일부, 아키텍처 테스트 | 합성·fixture만 | 10.1절의 수작업·섭동·차단·비용 항등식·교차검증·재현성 테스트 통과 | 코드 약 500–800줄 + 테스트, 1–2 세션 |
| BT-2 | 체결 시나리오 E0–E3·진단, 결측·대체·미체결, ι(C), 계좌 모드, 지표 전체, B1–B4, CLI `backtest --source fixture`, `backtest-verify`, `bar_export`(fixture) | 합성·fixture만 | 비용 분해 항등식, 계좌 모드 수렴, 결측 규칙 테스트 | 1–2 세션 |
| BT-3 | 구간 분리, HoldoutVault·ForwardVault, config 로더(사전등록 SHA), walk-forward 보고 | 합성만 | 잠금 우회 불가, 재개봉 거부 테스트 | 1 세션 |
| BT-4 | v0.6 사전등록 고정(D1–D10, U1–U9 결정 반영) | – | 사전등록·config SHA | 사용자 결정 |
| BT-5 | dry-run → 과거 캔들 수집(승인) → `candles-verify` → `bar_export` → 확증 평가 백테스트 1회 → research 쪽 검정 | **실데이터** | 판정표 결과(L1). 수익률은 이 단계에서 처음 생긴다 | 승인별 |
| BT-6 | holdout 개봉(조건 충족 시) → forward 평가(월 1회 수집, 12개월 이상). 실시간 모의거래는 PAPER_CANDIDATE 이후의 별도 설계 | 실데이터 | L2/L3 | 12개월 이상 |

- 세션 수는 지금까지 작업 속도에 기반한 대략적 추정이며 약속이 아니다.
- BT-6의 "실시간 모의거래"는 초안 기준으로 forward L3 평가와 다르다. forward 평가는 캔들 수집으로 하고, 실시간 모의거래(paper)는
  초안 11.3의 PAPER_CANDIDATE 이후에 별도 설계와 승인을 받는다.

## 16. 미확정 사항 (사용자 결정 필요)

| ID | 항목 | 선택지 | 영향 |
|---|---|---|---|
| U1 | M20/M60/M120 정의 | **결정(2026-10-16): BT-1은 SMA 규칙(`sma20/60/120`)** | v0.6 초안의 수익률 부호 규칙과 구분. 초안 판정에 쓰려면 초안 개정 또는 새 study |
| U2 | 계정 수수료 | 사용자 확인(14.3절) | 확인 전 FEE_UNCONFIRMED, 판정 25 bp |
| U3 | 최소 주문·수량·호가 단위 | 공식 자료로 확인 | 계좌 모드만 영향 |
| U4 | 신호 결측 시 보유 중 포지션 | 유지 / 청산 | 결측이 드물면 영향 작음(확인 전 가정) |
| U5 | 1시간봉 제공 범위가 일봉보다 짧을 때 | 평가 시작일을 늦춤 / 그 기간은 E2만 | 확증 기간 길이(검정력)에 영향 |
| U6 | 참여율 상한 | 연구 모드 보고 전용(현재 설계) / 판정 반영(초안 변경) | 판정 자본 1,000만 KRW에서 영향은 미확인 |
| U7 | 가격 수치 표현 | 계산 float64 + 원장 Decimal(현재 설계) / 전부 Decimal | 속도와 정밀도 |
| D10 | H1 수준 왜곡과 엔진 FAR 미확정의 판정 반영 | 보고 전용 / π 기준 보정(시뮬레이션 필요, 별도 승인) / 판정 제외 | v0.6 판정표 S축 |
| U8 | 커밋 위치 | 새 브랜치(예: `feature/backtest-core`)의 기준 커밋 선택 | 현재 이 문서는 `C:\MoneyLab`의 `feature/v06-prereg-audit-fix` 작업 트리에 미추적 파일로 있다 |
| U9 | raw·vault 접근 guard | 초안 19.5 사양 적용 여부 | holdout 격리의 기술적 강제 수준 |
| – | v0.6 초안 D1–D9 | 초안 18.1절 | BT-4 고정의 전제 |

## 17. 개정 이력

| 판 | 날짜 | 변경 |
|---|---|---|
| BT-0 초안 | 2026-10-15 | 최초 작성. 코드·테스트·시뮬레이션·수집 없음 |
| BT-1 | 2026-10-16 | U1 결정 반영(5.1절, 16절). 코어 MVP 구현(합성 데이터 전용, 미커밋): `domain/bars.py`, `backtest/{data,strategy,costs,portfolio,ledger,metrics}.py`. 비용은 매수·매도 수수료와 고정 bp slippage만(ASSUMED, FEE_UNCONFIRMED). 실데이터(`kind = real`)는 거부 |
| 문구 정리 | 2026-10-16 | 사전등록 M20/M60/M120과 BT `sma*`의 구분을 명확화(5.1절, 10.4절). 전략 정의 변경 없음 |
