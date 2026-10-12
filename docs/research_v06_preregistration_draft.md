# MoneyLab v0.6 사전등록 초안: Upbit KRW-BTC 일 단위 보유 추세·반전 전략(long/cash)의 비용 후 경제성

상태: **초안(DRAFT), 아직 고정되지 않음.** 사용자 검토용이다. 고정 절차(15절)를 거치기 전에는 해시를 기록하지 않고,
데이터를 수집하지 않으며, 코드를 바꾸지 않는다. 고정되면 `docs/research_v06_preregistration.md`와
`configs/research_v06.toml`(부록 A)이 되고, 두 파일의 SHA-256이 모든 v0.6 run manifest에 기록된다.

이 연구는 **읽기 전용**이다. 실제 주문, API key, 계좌 연결, 자동매매, Paper Trading 승격은 범위 밖이다.
아래 수치 중 "가정" 또는 "미검증"으로 표시한 것은 확인된 사실이 아니다.

## 0. 다른 study와의 관계

- v0.6은 **별도 study**다. v0.4(prereg `f86792c0…`, config `c16b22a3…`)와 v0.5 초안의 문서·설정·결과·test lock은 바꾸지 않는다.
  v0.4의 REJECT 판정은 그대로 유효하다.
- v0.6은 v0.4/v0.5의 L2 microstructure 데이터를 쓰지 않는다. 데이터 원천(일·시간봉 캔들)이 다르고 기간이 겹쳐도 같은 값을 재사용하지 않는다.
- v0.4의 train/validation 결과는 **보유기간을 늘려야 한다는 동기**로만 쓴다(1절). v0.6의 신호·파라미터 선택에는 쓰지 않는다.
- v0.5와 v0.6은 독립이다. 둘 다 진행하더라도 결과를 합쳐 하나로 검정하지 않는다.

## 1. 배경: 왜 보유기간을 늘리는가 (v0.4 validation 기술통계)

| 항목 | v0.4 관측값 |
|---|---|
| 왕복 spread·체결 비용 (0.001 BTC, 수수료 제외) | 약 3.35 bp |
| 크기 0.001 → 0.01 BTC 추가 비용 | +0.5 bp (최대 0.87) |
| 지연 0 → 250 ms 추가 비용 | 약 0.01 bp |
| 최대 gross (h = 30 s) | 1.20 bp |
| mid 변동 sd (h = 1 / 5 / 10 / 30 s) | 0.63 / 1.29 / 1.70 / 2.94 bp |
| 수수료 0bp에서도 최선 net | −2.35 bp (116개 조합 모두 음수) |

거래 1회 비용(spread + 왕복 수수료 2f)은 보유기간과 거의 무관하고, 가격 변동은 대략 √h로 커진다.
상위 quintile 기대 gross ≈ IC × sd × 1.4로 근사하면, net > 0에 필요한 IC는 다음과 같다 (편도 수수료는 **가정**).

| 보유기간 | sd | 필요 IC (f = 5 bp) | 필요 IC (f = 25 bp) | 비고 |
|---|---|---|---|---|
| 30 s | 2.94 bp | 약 3.3 (불가능) | 약 13 (불가능) | v0.4 관측 |
| 300 s | 9.3 bp | 약 1.0 (불가능) | 약 4.1 (불가능) | v0.5 초안 |
| 1 h | 약 32 bp | 약 0.30 | 약 1.2 | √h 외삽 |
| 1 일 | 약 160–250 bp | 약 0.04–0.06 | 약 0.15–0.24 | √h 외삽, 실제 일간 sd는 데이터로 확인 |

시간~일 단위에서만 필요 신호 강도가 문헌상 보고되는 시계열 모멘텀 수준과 같은 자릿수가 된다. 이것은 **가능성의 여지**일 뿐
양의 기대수익의 증거가 아니다.

## 2. 질문과 가설

> Upbit KRW-BTC 일봉에서, 과거 N일 수익률의 부호로 보유/현금을 정하는 long/cash 전략이 수수료·spread·slippage를 뺀 뒤에도
> 양의 수익을 내고, **같은 시장 노출을 무작위로 잡는 경우보다** 나은가?

- **H1 (경제성, primary):** primary 전략(5절)의 일별 net 수익률 평균 > 0 (판정 수수료 기준).
- **H2 (신호 기여, primary):** 같은 전략의 net이 노출 일수·진입 횟수를 맞춘 무작위 노출 benchmark B1보다 크다.
  BTC의 장기 상승 drift를 신호로 착각하지 않기 위한 핵심 검정이다.
- **H3 (위험 조정, 보고·조건부):** buy-and-hold B2 대비 Sharpe와 최대 낙폭(MDD). 판정 기준 10.4에 포함하지만 단독으로는 채택 근거가 아니다.
- **귀무가설:** H1, H2가 0 이하다. 판정은 H1과 H2를 모두 통과해야 한다.

## 3. 사전 경제성·검정력 점검 (계획용, 데이터를 보기 전 추정)

**거래비용 drag.** 일봉 추세 전략의 왕복 횟수를 연 10–30회로 가정하면(실제 값은 train에서 측정해 보고):

| 편도 수수료 (가정) | 왕복 비용 (2f + spread·slippage 10 bp) | 연 20회 왕복 시 연간 drag |
|---|---|---|
| 5 bp | 20 bp | 약 4 %/년 |
| 15 bp | 40 bp | 약 8 %/년 |
| 25 bp | 60 bp | 약 12 %/년 |

일봉에서는 비용이 신호를 원천적으로 압도하지는 않지만, 판정 수수료 25 bp에서는 무시할 수 없는 크기다.

**검정력 (정직한 한계).** 연환산 Sharpe 차이 ΔSR을 일별 데이터로 검출하는 데 필요한 기간은 대략
`T_years ≈ ((z_α + z_β) / ΔSR)²`이다. 단측 α = 0.05, 검정력 80%(z 합 ≈ 2.49)에서:

| 검출하려는 ΔSR (연) | 필요 기간 |
|---|---|
| 1.0 | 약 6.2 년 |
| 0.7 | 약 12.7 년 |
| 0.5 | 약 24.8 년 |

KRW-BTC 일봉은 약 9년(상장일 **미검증**)이고, validation·holdout 구간은 각각 2년 안팎이다.
**따라서 이 study는 "양의 기대수익 확정"보다 "반증(REJECT)" 또는 "추가 연구 필요(RESEARCH_MORE)"로 끝날 가능성이 높다.**
이 한계를 알고 진행할지는 사용자가 결정한다(16절). 결론의 강도는 forward holdout(8절)이 쌓일수록 커진다.

## 4. 데이터

| 항목 | 값 |
|---|---|
| 시장/소스 | Upbit KRW-BTC, 공개 REST 캔들 (일봉 primary, 1시간봉 secondary). `core/http.HttpClient` 경유 |
| provenance | `real`만 증거. fixture/synthetic은 `NOT_EVIDENCE` |
| raw 위치 | `data/raw/upbit/candles_v06/<pull_id>/` (요청 파라미터, 응답 원문, 수신 시각, SHA-256 기록) |
| 기간 | 상장일(미검증) ~ 동결일. 이후 forward holdout은 동결 이후 수집분만 |
| 일봉 경계 | **UTC 00:00 = KST 09:00.** 일봉 D는 [D 00:00 UTC, D+1 00:00 UTC) 구간이다 |
| 1시간봉 경계 | UTC 정시. 1시간봉 H는 [H, H+1h) 구간이다 |
| 수집 모듈 | `moneylab.providers.upbit.candles` + `candle_store` (페이지 원문·요청 파라미터·수신 시각·SHA-256·출처를 `pull.json`과 `pages/`에 기록) |

**2026-10-12 실제 응답으로 확인한 사실** (`/v1/candles/days`, `/v1/candles/minutes/60`, KRW-BTC, count=10, HTTP 200, 각 10개. 화면 출력으로 확인했고 `data/raw/`에는 저장하지 않았다):
- `candle_date_time_utc`·`candle_date_time_kst`는 구간 **시작** 시각이고 시간대 표기가 없다. KST = UTC + 9 h.
- 응답은 최신 순이다(문서에는 정렬 규칙이 없으므로 수집 코드가 직접 정렬한다).
- `opening_price`는 구간 첫 체결가이고 직전 종가와 다를 수 있다. `trade_price`는 종가이며, 진행 중인 구간에서는 현재가다.
- `timestamp`는 구간 마지막 틱 시각(ms)이다. 경계 7 ms 뒤 체결이 이전 일봉에 귀속된 사례가 1건 있었다.
- 문서 기준: count 최대 200, `to` 이전 캔들을 반환, 체결이 없는 구간은 캔들이 생략, 캔들 그룹은 IP당 초당 10회.

**확인되지 않은 사실 (가정하지 않는다, 절대 규칙 5):**
- `to`가 경계를 포함하는지(수집 코드는 두 경우 모두 중복을 제거한다), `to`에 시간대를 빼면 어떻게 해석되는지(항상 `Z`를 붙여 보낸다)
- 과거 캔들의 사후 수정 여부, KRW-BTC 첫 캔들 날짜(상장일). 수집 코드는 빈 페이지를 과거의 끝으로 간주하고 그 사실을 품질 보고서 경고로 남긴다
- 계정 수수료, maker/taker 수수료 차이, 최소 주문 금액

**진행 중 캔들 제외 규칙:**
- 캔들은 구간 끝 시각 + 정착 시간(120 s)이 기준 시각 이전일 때만 확정으로 본다. 늦게 귀속되는 체결(7 ms 사례)을 고려한 값이다.
- 기준 시각은 로컬 수신 시각과 응답 `Date` 헤더 중 **이른 쪽**이다. 로컬 시계가 빨라도 열린 구간을 닫힌 것으로 보지 않는다.
- 제외된 캔들 수는 품질 보고서(`excluded_incomplete`)에 기록한다. 제외된 캔들은 다음 수집에서 확정된 뒤에만 들어온다.

**데이터 유효성** (수익률 통계를 보기 전, 품질 보고서만으로 판정):
1. 날짜 연속성: 누락 일 ≤ 0.5 %. 연속성은 행 개수가 아니라 구간 시작 시각의 차이로 판정한다(체결 없는 구간은 생략되기 때문).
   누락 일은 보간하지 않고 해당 일의 신호·수익률을 NaN으로 둔다.
2. OHLC 일관성(low ≤ open, close ≤ high), 가격 > 0, 거래량 ≥ 0. 위반 행은 고치지 않고 품질 보고서에 기록한다.
3. 같은 구간이 서로 다른 값으로 두 번 오면(사후 수정 또는 페이지 경계) 기록하고 첫 수신본을 고정한다. 같은 값의 중복은 제거하고 개수만 기록한다.
4. 가격·거래량은 Decimal로 파싱한다(부동소수 반올림 없음).

## 5. 전략 (현물 long/cash, 공매도·레버리지 없음)

신호 시각 t는 일봉 종가 시각이다. r(t−N, t]는 종가 기준 N일 로그수익률이다.

**Primary family (확증 검정, 4개):**

| 전략 | 규칙 | 선정 근거 |
|---|---|---|
| M20 | r(t−20, t] > 0이면 보유, 아니면 현금 | 시계열 모멘텀, 단기 |
| M60 | r(t−60, t] > 0이면 보유 | 중기 |
| M120 | r(t−120, t] > 0이면 보유 | 장기 |
| R5 | r(t−5, t] < 0이면 보유 (단기 반전) | 반전 가설 대표 1개 |

- 파라미터 N은 위 값으로 **고정**한다. train에서 N을 고르지 않는다(탐색 금지). 문헌·관행에서 흔한 값을 데이터를 보기 전에 정했다.
- 포지션 크기는 고정 명목(가정: 100만 KRW 상당)이며 수익률 단위로 평가한다. 변동성 조절 sizing은 secondary.

**Secondary family (탐색, PAPER_CANDIDATE 불가):**
- 1시간봉 M24h, M72h, M168h (4시간마다 재평가)
- 변동성 목표 sizing을 적용한 M60 (trailing 30일 실현변동성, 목표 연 40 %, 상한 1배)
- M20·M60·M120 동일가중 합성 (가중치 추정 없음. 복합 Alpha 후속 연구의 기준선, 9절)

## 6. 체결과 비용 모델

- **신호 생성 시점과 체결 시점을 구분한다.**
  - **신호 시점 τ_D = D+1 00:00 UTC (KST 09:00)**: 일봉 D가 끝난 시각이다. 신호는 τ_D에 **확정된** 캔들(구간 끝 ≤ τ_D, 즉 D 이하)만 쓴다
    (`closed_as_of`). 진행 중인 D+1 일봉의 어떤 값도 쓰지 않는다.
  - **체결 가정 (primary)**: 다음 캔들 D+1의 시가 `opening_price`에 체결한다. 시가는 D+1 구간의 첫 체결가로, τ_D 이후에 발생한 가격이다.
    신호 계산 시간을 무시하는 가정이므로 아래 강건성 시나리오를 함께 보고한다.
  - **체결 가정 (강건성)**: D+1 일봉의 종가(하루 지연). 1시간봉을 쓰는 secondary 전략은 신호 시점 다음 1시간봉의 시가(primary)와 종가(강건성)를 쓴다.
  - 같은 캔들의 종가로 신호를 만들고 같은 종가에 체결하는 가정은 쓰지 않는다(look-ahead).
- 캔들은 체결가이지 호가가 아니므로 spread를 별도로 더한다.
- **왕복 비용 = 2f + c_spread_slip.**
  - f(편도 수수료): 시나리오 0(진단 전용) / 5 / 15 / 25 bp. 판정 수수료 = `account_fee_bps`, 미확인이면 25 bp.
  - c_spread_slip: 판정 10 bp (v0.4 관측 3.35–4.2 bp의 2배 이상, 주간·급변 구간 미관측을 반영), 강건성 20 bp.
- 수수료 공식은 v0.4와 같다: `net = 1e4 · ((1 + exec/1e4) · (1−f)/(1+f) − 1)`.
- 현금 보유 구간 수익률은 0이다(이자 없음).

## 7. Benchmark

- **B1 matched random exposure (H2):** 전략과 같은 보유 구간 길이 목록을 무작위 순서·무작위 시작일로 재배치한다(겹침 없음).
  seed 고정, 1000회. excess = mean(전략 net) − mean(B1 net), p값은 B1 분포에서의 순위.
- **B2 buy-and-hold:** 같은 구간 계속 보유(진입·청산 비용 1회씩).
- **B3 cash:** 0.

## 8. Split과 holdout

| 구간 | 기간 (상장일 확인 후 확정) | 용도 |
|---|---|---|
| warmup | 시작 ~ +120일 | 신호 계산용, 평가 제외 |
| train | warmup 끝 ~ 2022-06-30 | 기술통계, 회전율·보유기간 측정. 파라미터 선택 없음 |
| validation | 2022-07-01 ~ 2024-03-31 | H1–H3 1차 판정 |
| historical holdout | 2024-04-01 ~ 동결일 | **잠금.** `research-final`로 한 번만 연다 |
| forward holdout | 동결일 이후 ≥ 12개월 | 동결 이후 수집한 데이터로만 평가 |

- 구간 경계에서 lookback이 앞 구간에 걸치는 것은 허용한다(가격 정보는 과거 방향뿐이다). 체결이 경계를 넘는 거래는 시작 구간에 귀속한다.
- **historical holdout의 한계:** 2024–2026년 BTC 가격 흐름은 공개된 정보라 연구자(사람과 AI 모두)가 대략 알고 있다.
  파라미터를 고정해 두었으므로 직접 오염은 작지만, 완전한 맹검이 아니다. 따라서 **PAPER_CANDIDATE에는 forward holdout 통과가 필요하다.**
- **AI 모델 사용 제한:** 언어 모델은 학습 데이터에 과거 가격이 들어 있으므로 신호 생성이나 과거 구간의 매매 판단에 쓰지 않는다(look-ahead). 12절 참조.
- 동결 이후 데이터 구간 추가나 기간 변경은 새 study(v0.6.1)다.

## 9. 통계

- 단위: 일별 net 수익률(현금일 포함). 연환산은 **365일**(암호화폐 24시간·연중무휴, 252 거래일 미사용), 1시간봉은 8760.
- 평균 net의 신뢰구간: stationary block bootstrap, 평균 블록 20일, 1000회, seed 고정. 보조로 Newey-West (lag 20).
- 다중 검정: primary 4개의 H1·H2 각각 **Holm** 보정(단측 α = 0.05). secondary는 별도 family, 탐색 표시.
- 과최적화 지표: deflated Sharpe ratio(전체 시도 수 = primary 4 + secondary 5를 명시) 보고.
- 보고 항목: 연환산 수익률·변동성·Sharpe, MDD와 회복 기간, 연간 왕복 횟수, 평균 보유일, 노출 비율, 손익분기 편도 수수료 f*,
  연도별 net 부호, 상승·하락 국면별 성과(국면 정의: B2의 trailing 200일 수익률 부호, 사후 분류이며 보고 전용).

## 10. 판정

**10.1 PAPER_CANDIDATE 기준** (primary만, 모두 충족):
1. provenance=real, 데이터 유효성(4절) 통과
2. validation: H1 Holm 하한 > 0 (판정 수수료, c = 10 bp)
3. validation: H2 excess > 0 (Holm)
4. 강건성(t+1 종가 체결, c = 20 bp, 판정 수수료)에서 net > 0
5. validation 왕복 거래 ≥ 20, 연도별 net 점추정치 > 0인 해 ≥ 60 %
6. historical holdout(한 번만): net > 0, excess > 0
7. forward holdout ≥ 12개월: net > 0, excess ≥ 0, MDD ≤ validation MDD × 1.5
8. 운영비용 포함 순수익(11절) > 0 — 실제 운용 규모를 가정해 계산

**10.2 Evidence class:**

| class | 조건 | 판정 |
|---|---|---|
| `INSUFFICIENT_EVIDENCE` | 데이터 무효, 왕복 < 20, CI 계산 불가 | RESEARCH_MORE |
| `NEGATIVE_EVIDENCE` | 표본 충분 **그리고** (net ≤ 0 **또는** excess ≤ 0) | REJECT |
| `POSITIVE_AT_LOWER_FEE` | 판정 수수료에서는 음수, 5/15 bp에서 net > 0 및 excess > 0 | RESEARCH_MORE (`FEE_UNCONFIRMED`, f* 보고) |
| `POSITIVE_BUT_UNCONFIRMED` | 판정 수수료에서 net > 0, excess > 0, 1–8 중 일부 미충족(특히 forward 미완료) | RESEARCH_MORE |
| `CONFIRMED` | 1–8 전부 | PAPER_CANDIDATE |

- 상한: secondary는 최대 RESEARCH_MORE. forward holdout 전에는 최대 RESEARCH_MORE.
- **PAPER_CANDIDATE도 실거래나 Paper Trading 승격이 아니다.** 사용자 승인 하에 Paper Trading 설계를 검토할 자격만 뜻한다.

## 11. 최종 순수익 평가 체계 (거래비용과 운영비용 분리)

```
순수익 = 총수익(gross)
       − 거래비용   [수수료 2f × 왕복 수 + spread + slippage]          ← 거래마다 발생, 자본에 비례
       − 운영비용   [AI API + 데이터 + 인프라]                           ← 기간마다 발생, 자본과 무관
```

- 거래비용은 전략 수익률(bp) 안에서 차감한다(6절). 운영비용은 KRW/년으로 별도 계산한 뒤 운용 자본으로 나눠 %/년으로 비교한다.
- **손익분기 자본** C* = 연간 운영비용 / (연간 거래비용 후 net 수익률). 자본이 C*보다 작으면 전략이 맞아도 손실이다.
- **연간 AI API 비용** = Σ_모델 [호출/일 × 운영일/년 × (입력 토큰 × 입력 단가 × (1 − 캐시 할인율) + 출력 토큰 × 출력 단가) / 1e6]
  - 운영일/년 = **365** (24시간 시장). 호출이 시간·분 단위면 8760 시간, 525,600 분을 그대로 쓴다.
  - 단가는 계약·공식 가격표에서 확인한 값만 쓰고 출처와 날짜를 기록한다(이 초안에는 확정 단가 없음).
- 데이터 비용: 공개 API는 0이지만 유료 데이터·해외 거래소 데이터를 쓰면 포함.
- 인프라 비용: 상시 실행 PC·서버의 전기·호스팅, 모니터링. 24시간 운영이면 절전 해제 비용 포함.
- 개발 비용(Claude Code 세션 등)은 일회성으로 별도 표기하고, 회수 기간을 보고한다.

**규모 감각 (가상의 단가 예시, 확인된 가격 아님):** 호출당 입력 5,000 토큰, 출력 1,000 토큰, 입력 $3/M, 출력 $15/M라고 가정하면 호출당 $0.03.

| 호출 빈도 | 호출/년 (365일) | 연간 비용 | 연 net 5 %일 때 손익분기 자본 |
|---|---|---|---|
| 하루 1회 | 365 | 약 $11 | 약 $220 |
| 1시간 1회 | 8,760 | 약 $263 | 약 $5,300 |
| 1분 1회 | 525,600 | 약 $15,800 | 약 $315,000 |

v0.6 전략은 하루 1회 규칙 계산이며 런타임 AI 호출이 필요 없다(12절). 따라서 v0.6의 운영비용은 사실상 인프라뿐이다.

## 12. AI Agent 역할 분리

| 단계 | 규칙 기반 Python | AI 모델 호출 | v0.6 결정 |
|---|---|---|---|
| 데이터 수집 | `HttpClient` + 원문 저장 + 해시. 결정적, 재현 가능 | 불필요. 응답 해석을 AI에 맡기면 추측 파싱(절대 규칙 5 위반) 위험 | Python |
| 신호 계산 | 순수 함수, 테스트 가능 | **금지.** 학습 데이터에 미래 가격이 있어 과거 구간에서 look-ahead가 생기고, 비결정적이라 재현 불가 | Python |
| 전략 평가 | `analytics/metrics.py` 순수 함수, bootstrap, Holm | 런타임 불필요. 개발 시 코드 작성·리뷰·보고서 작성 보조(일회성) | Python (+개발 보조) |
| 위험관리 | 고정 한도(최대 포지션, 일 손실 한도, kill switch) | **금지.** 한도 판단에 비결정적 요소를 넣지 않는다 | Python |
| 거래 실행 | 범위 밖(절대 규칙 1) | 범위 밖 | 해당 없음 |
| 이상 탐지·장애 조사 | 품질 지표 임계값으로 1차 탐지 | 조건부: 임계값 초과 시에만 incident 분석 보조 | 조건부 호출 |

원칙: AI는 **개발 도구와 조건부 조사 보조**로 쓰고, 매매 결정 경로(데이터 → 신호 → 위험 → 주문)에는 넣지 않는다.
AI를 결정 경로에 넣는 전략은 별도 study로 다루고, 그 경우 11절 비용과 look-ahead 통제(모델 knowledge cutoff 이후 구간만 평가)를 사전등록한다.

## 13. 알려진 bias와 대응

| bias | 대응 |
|---|---|
| look-ahead | t 종가 신호 → t+1 체결, 신호 함수에 "t 이후 데이터 변경 시 신호 불변" 테스트, AI 모델 신호 금지 |
| 파라미터 과최적화 | N 고정(탐색 없음), primary 4개, Holm, deflated Sharpe, secondary 분리 |
| drift를 신호로 착각 | B1 matched random exposure 대비 excess(H2)를 필수 기준으로 둔다 |
| holdout 오염 | historical holdout 잠금 + forward holdout 필수 |
| 체결 가능성 | 캔들 체결가 + 보수적 spread·slippage 10/20 bp, 하루 지연 강건성. 소량 주문 가정 명시 |
| 생존 편향 | 단일 종목(KRW-BTC)이라 해당 없음. 다종목 확장(복합 Alpha) 시 상장폐지 종목 포함 필요 |
| 국면 의존 | 연도별·국면별 성과 보고, 결론 범위를 KRW-BTC와 기간으로 한정 |
| 검정력 부족 | 3절에 사전 기록, INSUFFICIENT/RESEARCH_MORE를 실패가 아닌 정상 결과로 취급 |

## 14. 후속 연구 후보: 복합 Alpha (이 study의 범위 밖)

외부 자료("A Unified Framework for Alpha Extraction and Signal Combination", X 게시물, 사용자 요약 기준, **원문 미검토·성과 미검증**)의
절차(평균 제거·변동성 정규화 → 공통 시장 요인 제거 → 잔차 기반 가중치 → 신호 결합)는 다음 조건에서만 의미가 있다.

- **다종목 universe가 필요하다.** KRW-BTC 단일 종목에서는 BTC 자체가 시장 요인이라 "공통 요인 제거" 후 잔차가 거의 남지 않는다.
  KRW 마켓 다종목으로 확장하면 상장폐지 종목을 포함한 시점별(point-in-time) universe가 필요하다.
- **누수 지점과 대응:**

| 단계 | 누수·과최적화 위험 | 대응 |
|---|---|---|
| 평균 제거·변동성 정규화 | 전체 표본 평균·sd 사용 | t−1까지의 trailing/expanding 통계만 |
| 시장 요인 제거 | 전체 표본 beta, 사후 universe로 만든 시장 지수 | rolling beta (t−1까지), 시점별 universe로 지수 구성 |
| 잔차 기반 가중치 | in-sample IC·회귀로 가중치 추정 후 같은 구간 평가 | nested walk-forward, 가중치 추정 창과 평가 창 분리, 동일가중 기준선과 비교 |
| 신호 결합 | 신호 수 × 창 길이 × 가중 방식 조합 탐색 | 시도 수 전부 기록, deflated Sharpe, 결합 방식 사전 고정 |
| universe 선택 | 현재 상장 종목만 사용(생존 편향) | 상장폐지 포함, 유동성 기준도 시점별 |

- 착수 조건: v0.6에서 단일 신호 중 하나 이상이 NEGATIVE_EVIDENCE가 아닐 것, 다종목 캔들 응답 확인, 별도 사전등록(v0.7).

## 15. 고정 절차

1. 사용자가 이 초안과 16절 결정 사항을 확정한다.
2. 캔들 API 소량 응답을 확인해 4·6절의 미검증 항목을 채운다. **2026-10-12 완료**(일봉 경계, 필드, 정렬). 남은 미검증 항목은 4절 참조.
3. 확정본을 `docs/research_v06_preregistration.md`, `configs/research_v06.toml`로 만들고 SHA-256을 기록한다(commit은 사용자 승인 후).
4. 이후 문서·설정 변경은 새 study다. 예외는 `account_fee_bps` 사실 입력뿐이며, holdout 개봉 후에는 바꾸지 않는다.

## 16. 고정 전 결정 사항 (사용자)

1. **검정력 한계 수용:** 3절대로 확정적 양성 판정이 어렵다는 것을 알고 진행할지.
2. **primary family:** M20/M60/M120/R5 4개로 둘지(현재안). 늘리면 Holm 보정이 엄격해진다.
3. **구간 경계:** validation 끝 2024-03-31, historical holdout 시작 2024-04-01(현재안).
4. **판정 spread·slippage:** 10 bp(현재안) / 강건성 20 bp.
5. **소량 응답 확인 승인:** 캔들 API 일봉·1시간봉 각 10개 수준 1회 요청.
6. **계정 수수료:** 공식 자료로 확인된 편도 수수료와 maker/taker 차이(확인 전에는 25 bp로 판정).

## 부록 A. config 초안 (`configs/research_v06.toml` 예정, 아직 파일 생성 안 함)

```toml
[study]
name = "moneylab-v0.6-upbit-krw-btc-daily-trend"
version = 1
market = "KRW-BTC"
preregistration = "docs/research_v06_preregistration.md"
provenance_required = "real"
annualization_days = 365

[data]
primary_interval = "day"               # bucket [D 00:00 UTC, D+1 00:00 UTC), verified 2026-10-12
settle_seconds = 120                   # a candle is closed only after end + settle (in-progress excluded)
secondary_interval = "hour"
max_missing_day_share = 0.005

[split]
warmup_days = 120
train_end = "2022-06-30"
validation_start = "2022-07-01"
validation_end = "2024-03-31"
holdout_start = "2024-04-01"           # locked, opened once by research-final
forward_holdout_min_months = 12

[strategy]
primary = ["M20", "M60", "M120", "R5"]
secondary = ["M24h", "M72h", "M168h", "M60_voltarget", "M_combo_equal"]
execution = "next_open"                # robustness: "next_close"
random_exposure_draws = 1000
random_exposure_seed = 20261012

[costs]
fee_bps_scenarios = [0.0, 5.0, 15.0, 25.0]   # 0 = diagnostic only; all assumed
# account_fee_bps =                    # official source + date only
spread_slippage_roundtrip_bps = 10.0
robust_spread_slippage_roundtrip_bps = 20.0

[stats]
bootstrap = "stationary"
bootstrap_block_days = 20
bootstrap_resamples = 1000
bootstrap_seed = 20261012
hac_lag_days = 20
economic_correction = "holm"
economic_alpha_one_sided = 0.05
report_deflated_sharpe = true

[decision]
min_roundtrips = 20
min_positive_year_share = 0.60
forward_max_mdd_ratio = 1.5
```
