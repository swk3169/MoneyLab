# MoneyLab v0.6 사전등록 초안: Upbit KRW-BTC 일 단위 long/cash 추세·반전 전략의 비용 후 경제성

상태: **초안(DRAFT), 아직 고정되지 않음.** 사용자 검토용이다. 고정 절차(17절)를 거치기 전에는 해시를 기록하지 않고,
과거 데이터를 수집하지 않으며, 백테스트 코드를 만들지 않는다. 고정되면 `docs/research_v06_preregistration.md`와
`configs/research_v06.toml`(부록 A)이 되고, 두 파일의 SHA-256이 모든 v0.6 run manifest에 기록된다.

이 연구는 **읽기 전용**이다. 실제 주문, API key, 계좌 연결, 자동매매, Paper Trading 승격은 범위 밖이다(CLAUDE.md 절대 규칙 1).
"가정" 또는 "미검증"으로 표시한 수치는 확인된 사실이 아니다.

개정 이력: 2026-10-12 초판 → 2026-10-12 개정(체결 시점, 확증 기간, 통계 정의, 판정 4축 분리, 품질 기준, 비용·운영비 구조).

## 0. 다른 study와의 관계

- v0.6은 **별도 study**다. v0.4(prereg `f86792c0…`, config `c16b22a3…`)와 v0.5 초안의 문서·설정·결과·test lock은 바꾸지 않는다.
  v0.4의 REJECT 판정은 그대로 유효하다.
- v0.4/v0.5의 L2 microstructure 데이터를 쓰지 않는다. v0.4 기술통계(1절)는 보유기간을 늘리는 **동기**로만 쓰고 신호 선택에는 쓰지 않는다.
- v0.5와 v0.6의 결과를 합쳐 하나로 검정하지 않는다.

## 1. 배경: 왜 보유기간을 늘리는가 (v0.4 validation 기술통계, 동기 전용)

| 항목 | v0.4 관측값 |
|---|---|
| 왕복 spread·체결 비용 (0.001 BTC, 수수료 제외) | 약 3.35 bp |
| 크기 0.001 → 0.01 BTC 추가 비용 | +0.5 bp (최대 0.87) |
| 최대 gross (h = 30 s) | 1.20 bp |
| mid 변동 sd (h = 1 / 30 s) | 0.63 / 2.94 bp |
| 수수료 0bp에서도 최선 net | −2.35 bp (116개 조합 모두 음수) |

거래 1회 비용은 보유기간과 거의 무관하고 가격 변동은 대략 √h로 커진다. 일 단위에서는 net > 0에 필요한 신호 강도가 문헌의
시계열 모멘텀과 같은 자릿수가 된다(√h 외삽, **가정**). 이것은 가능성의 여지일 뿐 양의 기대수익의 증거가 아니다.

## 2. 질문, 가설, 증거 수준

> Upbit KRW-BTC 일봉에서 과거 N일 수익률의 부호로 보유/현금을 정하는 long/cash 전략이 수수료·spread·slippage·시장 충격을 뺀 뒤에도
> 자산을 늘리고(H1), 같은 노출을 무작위 시점에 잡는 경우보다 나은가(H2)?

판정은 서로 독립인 네 축으로 한다(11절).

| 축 | 질문 | 값 |
|---|---|---|
| **Q** 데이터 품질 | 데이터가 판정에 쓸 만한가 (수익률을 보기 전) | VALID / INVALID / SENSITIVE |
| **S** 통계적 유의성 | H1·H2를 다중검정 보정 후 기각하는가 | PASS / FAIL |
| **E** 경제성 | 비용 후 거래 수익성과 그 강건성 (점추정 + 실패 증거) | PASS / FAIL / INCONCLUSIVE / FEE_UNCONFIRMED |
| **L** 증거 수준 | 어떤 성격의 데이터까지 통과했는가 | L1 / L2 / L3 |

운영 가치(운영비·계획 자본 포함)는 E와 분리된 부속 판정 **E_op**로 따로 계산한다(9절).

**증거 수준.** M20/M60/M120/R5는 **BTC 과거 가격을 이미 관찰한 상태에서** 문헌의 관행값으로 선택되었다(사람과 AI 모두, AI 학습
데이터는 2026-06까지 포함). 따라서 결과의 성격을 구분한다.

| 수준 | 데이터 | 결과 경로를 알았는가 | 막아 주는 것 | 막지 못하는 것 | 쓸 수 있는 결론 |
|---|---|---|---|---|---|
| L0 | 합성·fixture | – | – | 전부 | 없음 (NOT_EVIDENCE) |
| L1 | 확증 평가 기간 | 알았음 | 파라미터 탐색 | 이력 기반 선택 편향 | 반증 또는 일관성 확인 |
| L2 | historical holdout | 알았음 (공개 가격) | 분석 과적합 | 선택 편향 | 반증 또는 일관성 확인 |
| L3 | forward (동결 후) | 몰랐음 | 선택 편향 포함 전부 | 짧은 기간의 낮은 검증력 | 양의 기대수익 주장의 유일한 근거 |

PAPER_CANDIDATE는 L3를 요구한다. forward 12개월은 연 Sharpe 약 2.5 이상만 검출하므로 확증 수단이 아니라 붕괴를 보는 반증 검사다.

## 3. 사전 경제성·검정력 (계획용, 데이터를 보기 전 추정)

- 거래비용 부담: 연 20회 왕복, 편도 수수료 5/15/25 bp(가정), 편도 spread·slippage 5 bp이면 연 약 4/8/12 %.
- 검정력: 단측 α = 0.05, 검정력 80 %에서 검출 가능한 연 Sharpe 차이 MDE ≈ 2.49/√T년. 확증 평가 약 6년이면 약 1.0이다.
- 결과가 `UNDERPOWERED` 또는 `ECONOMIC_INCONCLUSIVE`(RESEARCH_MORE)로 끝날 가능성이 높다. 이는 실패가 아니라 정상 결과다.

## 4. 데이터

| 항목 | 값 |
|---|---|
| 시장/소스 | Upbit KRW-BTC 공개 REST 캔들. 일봉(신호), 1시간봉(체결 근사·수익률 기준 시각). `core/http.HttpClient` 경유 |
| provenance | `real`만 증거. fixture/synthetic은 L0 |
| raw 위치 | `data/raw/upbit/candles_v06/<pull_id>/` (`pull.json`, `pages/NNNN.json`, `pages/NNNN.meta.json`) |
| 원문 바이트 | `pages/NNNN.json`은 HTTP 전송 압축(gzip)을 푼 **응답 본문**이다. SHA-256은 이 바이트에 대해 계산한다. 압축된 전송 바이트는 저장하지 않으며, `Content-Encoding`은 메타 헤더에 남는다 |
| 일봉 경계 | **UTC 00:00 = KST 09:00.** 일봉 D는 [D 00:00 UTC, D+1 00:00 UTC) 구간이다 (2026-10-12 실측) |
| 1시간봉 경계 | UTC 정시. 1시간봉 H는 [H, H+1h) 구간이다 |
| 확정 규칙 | 캔들은 구간 끝 + 120 s ≤ (로컬 수신 시각과 서버 `Date` 중 이른 쪽)일 때만 확정. 진행 중 캔들은 제외하고 `excluded_incomplete`에 기록 |
| 기준 데이터 | 모든 판정은 **첫 수집본**(manifest에 pull ID와 SHA 기록)으로 한다. 사후 수정이 발견돼도 기준 데이터는 바꾸지 않는다 |
| 수집 도구 | `moneylab.providers.upbit.candles` + `candle_store`. CLI `candles-pull`(live는 매번 사용자 승인, dry-run 먼저), 검증 `candles-verify` |
| 파싱 | 가격·거래량은 Decimal. 응답 정렬에 의존하지 않고 직접 정렬. 같은 값 중복은 제거하고 개수만, 다른 값 중복은 첫 수신본 유지 + 기록. 보간 없음 |

**2026-10-12 실제 응답으로 확인한 사실** (`/v1/candles/days`, `/v1/candles/minutes/60`, KRW-BTC, count=10, HTTP 200, 각 10개.
01:42 UTC 1차 확인은 화면 출력만, 09:47 UTC 2차 수집은 원본 저장, 부록 B):
- `candle_date_time_utc`·`candle_date_time_kst`는 구간 **시작** 시각이고 시간대 표기가 없다. KST = UTC + 9 h.
- 응답은 최신 순이다(문서에 정렬 규칙 없음).
- `opening_price`는 구간 첫 체결가이고, `trade_price`는 종가(진행 중 구간에서는 현재가)다.
- `timestamp`는 구간 마지막 틱 시각(ms)이다. 경계 7 ms 뒤 체결이 이전 일봉에 귀속된 사례가 있었다(10-05 일봉, 저장 원문으로 재확인).
- 일봉 경계 00:00 UTC를 1시간봉과 교차 확인했다(시가 일치, 고가·저가 일치). `prev_closing_price`는 전날 `trade_price`와 일치했다.
- 문서 기준: count 최대 200, `to` 이전 캔들 반환, 체결이 없는 구간은 생략, 캔들 그룹은 IP당 초당 10회.

**확인되지 않은 사실 (가정하지 않는다, 절대 규칙 5):** `to`의 경계 포함 여부, 상장 이전 `to`에 대한 응답, 과거 캔들의 사후 수정,
KRW-BTC 첫 캔들 날짜(상장일), 계정 수수료, maker/taker 차이, 세금. 앞의 세 가지는 5절과 16절의 수집 과정에서 확인한다.

## 5. 데이터 품질 판정 Q (경제성과 독립, 수익률을 보기 전)

품질 판정은 품질 도구만으로 수행하고 수익률·신호 성과를 보지 않는다(Q13 제외). 결과는 `VALID`, `INVALID`, `SENSITIVE` 중 하나다.
historical holdout 구간의 원본 가격은 품질 도구 외에는 열람하지 않는다(잠금 유지).

| # | 검사 | 기준 | 위반 시 |
|---|---|---|---|
| Q1 | `candles-verify` (해시, 파일 목록, Replay) | 모든 pull ok | INVALID |
| Q2 | 일봉 누락률 (행 수가 아니라 시작 시각 차이로 판정) | ≤ 0.5 % | INVALID |
| Q3 | 1시간봉 누락률 | ≤ 1.0 % | INVALID |
| Q4 | 연속 누락 최댓값 | 일봉 ≤ 2일, 1시간봉 ≤ 6시간. 초과 구간은 `gap_event` | 확증 평가 기간에 `gap_event` ≥ 3건이면 INVALID |
| Q5 | 급변기 누락 | 변동성 상위 10 % 날(앞뒤 확정 종가 사이 절대 로그수익률 ÷ trailing 60일 sd)의 누락률 ≤ max(1 %, 전체 누락률 × 2) | INVALID |
| Q6 | 값이 다른 중복, OHLC·거래량 이상 (low ≤ open, close ≤ high, 가격 > 0, 거래량 ≥ 0) | 각 ≤ 0.1 %. 해당 일은 NaN, 보간 없음 | INVALID |
| Q7 | 일봉 ↔ 그날 1시간봉 24개 교차검증 (시가·고가·저가·종가 일치, 거래량 합 일치) | 불일치 ≤ 비교 가능일의 0.5 % | INVALID |
| Q8 | `prev_closing_price` 연속성 | 불일치 ≤ 0.5 % | INVALID |
| Q9 | 신호 영향 | lookback 종가(D 또는 D−N)가 없는 날은 **포지션 유지(거래 없음)**. 영향 신호 ≤ 신호일의 1 % | INVALID |
| Q10 | 체결 영향 | 체결 1시간봉이 없어 대체 규칙(6.3)을 쓴 거래 ≤ 1 % | INVALID |
| Q11 | 사후 수정 (최근) | 7일 이상 뒤 최근 60일 재수집에서 변경된 확정 캔들 ≤ 0.5 % | INVALID |
| Q12 | 사후 수정 (전 구간) | 일봉 전체 재수집(품질 판정 때와 holdout 개봉 직전 각 1회), 1시간봉 무작위 20페이지에서 변경 ≤ 0.5 % | INVALID |
| Q13 | 결과 민감도 | (a) Q9·Q10 영향 거래 제외, (b) 체결 대체 규칙을 직전 1시간봉 종가로 변경, (c) 사후 수정값으로 재계산. 어느 하나로 11.3의 행이 바뀌면 | SENSITIVE |

- Q1–Q12는 수익률을 보기 전에 판정한다. Q13만 경제성 계산 뒤에 판정하며, 판정 행의 변경 여부만 본다.
- **임계값 민감도 (보고 전용):** Q2–Q12의 임계값을 0.5배·2배로 바꿨을 때 Q 결과가 어떻게 바뀌는지 보고한다. 판정은 위 기준값으로만 한다.
- 관측 기록: `to` 경계 포함 여부(페이지 경계마다 같은 값의 중복이 1건씩이면 포함), 상장 이전 `to` 응답.

## 6. 전략과 체결

### 6.1 전략

r(a, b]는 a일 종가에서 b일 종가까지의 로그수익률이다. 신호는 τ_D = D+1 00:00 UTC에 끝난 일봉 D까지만 쓰고, 확정 규칙에 따라
**00:02 UTC에 확정**된다(`closed_as_of`). 진행 중인 D+1 일봉의 어떤 값도 쓰지 않는다.

| Primary (확증, 4개) | 규칙 | 선정 근거 |
|---|---|---|
| M20 | r(D−20, D] > 0이면 보유, 아니면 현금 | 시계열 모멘텀, 단기 |
| M60 | r(D−60, D] > 0이면 보유 | 중기 |
| M120 | r(D−120, D] > 0이면 보유 | 장기 |
| R5 | r(D−5, D] < 0이면 보유 | 단기 반전 대표 1개 |

- N은 고정이며 탐색하지 않는다.
- **Secondary (탐색 전용, 최대 RESEARCH_MORE, 별도 family):** M24h, M72h, M168h(1시간봉, 4시간마다 재평가), 변동성 목표 M60
  (trailing 30일 실현변동성, 목표 연 40 %, 상한 1배), M20·M60·M120 동일가중. 이 목록 밖의 변형은 새 study(v0.6.1)다.
- deflated Sharpe의 시도 수는 9(primary 4 + secondary 5)로 고정한다.

### 6.2 실행 규칙과 백테스트 근사 체결가

세 층을 구분한다. **결정 입력**은 신호 확정 시각까지 확정된 캔들뿐이다. **실행 규칙**은 실제로 할 수 있는 행동(주문 제출 시각과
유형)이다. **근사 체결가**는 실행 규칙의 체결가를 캔들로 근사한 값이다. **근사 체결가는 실제 체결가가 아니며 체결을 보장하지 않는
백테스트 가정이다.**

| 시나리오 | 실행 규칙 (주문 제출) | 근사 체결가 | 편도 spread·slippage κ | 용도 |
|---|---|---|---|---|
| **E0** | D+1 00:59:00 UTC 시장가 | 1시간봉 [00:00, 01:00) 종가 | 5 bp | S·E 판정 |
| E1 | D+1 01:59:00 UTC 시장가 | 1시간봉 [01:00, 02:00) 종가 | 10 bp | **경제성 스트레스 (E 필수 조건)** |
| E2 | D+1 23:59:00 UTC 시장가 | 일봉 D+1 종가 | 10 bp | **경제성 스트레스 (E 필수 조건)** |
| E3 | 없음 (경계값) | 체결 1시간봉 [00:00, 01:00)의 최악가 (매수 고가, 매도 저가) | 10 bp | 보고 전용 |
| 진단 | 없음 | D+1 시가 | 5 bp | 낙관적 상한, 판정 미사용 |

**E0 근사의 한계 (사전 기록):**
1. 근사값은 01:00:00 직전 마지막 체결가이고, 실행 규칙은 약 1분 전에 주문을 낸다. 그 사이 가격 변동(1σ 약 4.9 bp, v0.4 1초 sd에서
   외삽, **가정**)만큼 차이가 난다. 신호와 무관한 잡음으로 보고 편향으로 다루지 않는다.
2. 종가가 매수·매도 어느 쪽 체결이었는지 모른다. κ = 5 bp는 호가 전체 폭(v0.4 실측 평균 약 2.9–3.4 bp)보다 크게 잡았다.
3. 과거 시점의 호가 깊이는 알 수 없다. 시장 충격은 7절의 ι(C) 가정으로만 반영한다.
4. 매일 같은 시각의 시장가 주문이라는 실행 규칙은 운영 조건(00:59 UTC = 09:59 KST에 실행 환경 가동, 시계 정확도)을 전제한다.
   백테스트는 이 조건이 항상 충족된다고 가정한다.
5. E3의 최악가는 신호 확정 전(00:00–00:02) 가격을 포함하므로 실행 불가능한 경계값이다. 판정에 쓰지 않는다.
6. 진단(D+1 시가)과 E0의 차이는 "신호 후 1시간 대기"의 비용을 보여 준다. 판정에는 쓰지 않는다.

근사 오차 측정(선택, 별도 승인): forward 기간에 읽기 전용 recorder로 00:59 UTC 전후 호가를 기록해 거래 크기별 VWAP과 E0 근사값의
차이를 주문 없이 측정한다.

### 6.3 수익률 기준 시각과 결측 처리

- 각 시나리오의 일별 수익률은 **그 시나리오의 체결 시각**을 기준으로 한다: E0는 01:00 UTC, E1은 02:00 UTC, E2는 00:00 UTC.
  비교하는 benchmark(B1–B4)도 같은 기준 시각을 쓴다.
- 보유 중인 날은 기준 시각의 1시간봉 종가로 평가한다. 그 1시간봉이 없으면 기준 시각 이전의 가장 최근 1시간봉 종가로 평가한다.
- 체결 1시간봉이 없으면 다음 1시간봉 종가에 체결한다. 24시간 안에 없으면 그 시나리오의 다음 기준 시각 종가에 체결한다. 대체 건수는 Q10.
- 같은 캔들의 종가로 신호를 만들고 같은 종가에 체결하는 가정은 쓰지 않는다.

## 7. 거래비용 (세전)

| 구성 | 정의 | 값 |
|---|---|---|
| 수수료 f | 편도, 진입·청산 각각 | 시나리오 0(진단)/5/15/25 bp. 판정 수수료 = `account_fee_bps`(공식 자료, 출처·날짜 기록). **미확인이면 25 bp(보수적 가정)** |
| spread·slippage κ | 편도, 진입·청산 각각 | E0 5 bp, E1·E2·E3 10 bp |
| 시장 충격 ι(C) | 편도, 계획 자본 C에 의존 | ι(C) = ι_ref × √(C / C_ref), ι_ref = 1.0 bp, C_ref = 100만 KRW (**가정**: v0.4의 0.001 → 0.01 BTC 추가 비용 0.5–0.87 bp를 올림). 100만 / 500만 / 1,000만 KRW에서 약 1.0 / 2.2 / 3.2 bp |

- 거래 1건(진입 또는 청산)은 자산에 (1 − f)(1 − κ − ι(C))를 곱한다. 같은 규칙을 B1·B2·B4에 적용한다. 현금 수익률은 0이다(이자 없음).
- **판정 자본:** E와 S는 가장 보수적인 **C = 1,000만 KRW**의 비용으로 판정한다. 100만·500만 KRW는 민감도로 보고한다.
- **규모별 민감도 (보고):** C ∈ {100만, 500만, 1,000만} × ι 배수 {0, 1, 2}에서 E0 m_s, 손익분기 수수료 f*를 보고한다.
- C > 1,000만 KRW는 ι의 근거가 없으므로 `CAPACITY_UNVERIFIED`로 표시하고 판정에 쓰지 않는다.
- 과거 구간의 BTC 가격 변화로 같은 KRW 자본의 BTC 수량은 달라지지만(2017년에는 훨씬 큼), 과거 호가 깊이를 알 수 없으므로 ι는
  KRW 자본만의 함수로 둔다. 이 한계는 결론에 명시한다.
- 보고: 손익분기 수수료 f*, gross/비용 비율, 연간 왕복 횟수, 연간 비용 부담.

## 8. 기간과 benchmark

| 구간 | 기간 | 증거 수준 | 규칙 |
|---|---|---|---|
| warmup | 첫 일봉 ~ +120일 | – | 신호 계산만, 평가 제외 |
| 확증 평가 | warmup 끝 ~ 2024-03-31 (약 6년, 상장일 미검증) | L1 | Q·S·E 판정. 보조로 2022-07-01 ~ 2024-03-31 하위 구간 보고 |
| historical holdout | 2024-04-01 ~ 동결일 전날 | L2 | **잠금.** 한 번만 개봉 |
| forward | 동결일 ~ 최소 12개월, 최대 24개월 | L3 | 동결 후 수집분만. 월 1회 수동 수집(매번 승인) |

- lookback이 앞 구간에 걸치는 것은 허용한다(과거 방향 정보뿐). 경계를 넘는 거래는 진입 구간에 귀속한다.
- 동결 이후 구간 추가나 기간 변경은 새 study(v0.6.1)다.
- **AI 모델 사용 제한:** 언어 모델은 학습 데이터에 과거 가격이 있으므로 신호 생성이나 과거 구간의 매매 판단에 쓰지 않는다(12절).

**Benchmark** (모두 7절 비용과 6.3 기준 시각을 같게 적용):
- **B1 matched random exposure:** 전략의 보유 구간 길이 목록과 내부 현금 구간 길이 목록을 각각 무작위로 섞고, 앞뒤 현금 구간은 총합을
  유지하며 무작위로 나눈 뒤 번갈아 배치한다. 총 노출일, 거래 횟수, 비용이 전략과 같다. 구간마다 따로 생성한다.
- **B2 buy-and-hold:** 진입·청산 각 1회 비용.
- **B3 현금:** 0.
- **B4 노출 비율을 맞춘 B2:** B2 × 전략의 평균 노출 비율, 나머지 현금, 리밸런싱 없음. 보고 전용.

## 9. 운영비, 운영 가치 E_op, 세후 시나리오 (거래 수익성과 분리)

운영비는 거래 수익성(E)에 넣지 않고, 운영 가치 분석에만 쓴다.

```
R_s     : 전략 s의 연 net 로그수익률을 연 단순수익률로 환산한 값 (E0, 7절 거래비용 포함, 세전)
Ops     = AI_runtime + AI_ops + Infra + Data        (KRW/년)
C*_0    = Ops / R_s                                  (R_s > 0일 때, 0 대비 손익분기 자본)
V(C)    = C · (R_s(C) − R_B2(C)) − (Ops − Ops_B2)    (Ops_B2 ≈ 0, B2 대비 운용 가치)
C*_B2   = (Ops − Ops_B2) / (R_s − R_B2)              (R_s > R_B2일 때)
회수 기간 = 개발비(일회성) / V(C)
```

| 항목 | 산식 | 상태 |
|---|---|---|
| AI_runtime | 0. 규칙 기반이고 AI는 결정 경로(데이터 → 신호 → 위험 → 주문)에서 제외 | 확정 |
| AI_ops | 세션/월 × 12 × 세션 단가 | 단가는 공식 가격표·계약서 값만 (출처·날짜) |
| Infra | 소비전력 × 가동시간 × 전기요금. E0 실행 규칙상 매일 00:59 UTC 가동 필요 | 입력 필요 |
| Data | 공개 API 0 (유료 데이터를 쓰면 포함) | 확정 |
| 개발비 | 일회성, 별도 표기 | 기록 |

**E_op 판정 (계획 자본 100만 / 500만 / 1,000만 KRW 각각):**
- `OP_PASS`: V(C) > 0, 또는 ΔSR_{s,B2} > 0 그리고 MDD_s ≤ MDD_B2 (점추정, ΔSR 신뢰구간 함께 보고)
- `OP_FAIL`: 그 밖
- 운영비 입력이 없으면 `OP_UNDETERMINED`

**세후 시나리오 (판정 제외, 별도 보고):**
- 세금은 S·E·E_op 판정에 넣지 않는다. 판정은 모두 세전이다.
- 세후 계산 틀: 연도별 실현 손익 G_y(청산 기준), 손실 통산 범위, 기본공제 D, 세율 τ, 과세 시작 시점 Y0를 입력으로 받아
  세액 = τ × max(0, G_y − D) (y ≥ Y0)를 차감한다. 같은 틀을 B2(청산 시점 실현)에도 적용해 B2 대비 세후 차이를 보고한다.
- τ, D, Y0, 손실 통산 규칙은 적용 법령과 시행 시점이 공식 자료로 확인될 때까지 **미확정**이다. 확인 전에는 τ ∈ {0, 0.10, 0.20, 0.30}의
  **가상 민감도**만 보고하고 법령으로 표기하지 않는다. 확인되면 `tax_rule`을 사실 입력(17절 예외)으로 기록한다.

## 10. 통계 판정 S

### 10.1 공통 정의

```
w_t^s : 전략 s의 자산 (6.3 기준 시각, 7절 비용, 판정 자본 C = 1,000만 KRW)
r_t^s = ln(w_t^s / w_{t−1}^s)        일별 net 로그수익률 (세전, 현금일 0)
T     : 확증 평가 기간의 일 집합, n = |T|
m_s   = (1/n) Σ_{t∈T} r_t^s
S     = {M20, M60, M120, R5}          판정은 E0, 판정 수수료
seed  = 20261012                      derived_seed(seed, *parts)는 research/stats.py와 같은 방식
```

로그수익률을 쓰는 이유: 평균 단순수익률 > 0이어도 변동성 때문에 자산은 줄 수 있다. m_s > 0 ⇔ 기간 중 자산 증가이므로 S와 E가
같은 양을 본다. 연환산은 365일(24시간·연중무휴)이다.

### 10.2 H1 (자산 증가) — 단측

- **귀무가설 H1₀,s: μ_s ≤ 0. 대립가설 H1₁,s: μ_s > 0** (μ_s = E[r_t^s]). 오른쪽 단측 검정.
- **검정통계량:** m_s.
- **귀무가설하 재표본추출 (Politis–Romano stationary bootstrap):**
  1. 평균을 0에 맞춘 c_t^s = r_t^s − m_s. 귀무가설의 경계 μ = 0(가장 불리한 귀무)을 부과한다.
  2. 시작점 ~ 균등(1..n), 블록 길이 ~ 기하분포(평균 L = 20일), 원형으로 이어 붙여 길이 n의 인덱스열을 만든다.
  3. B = 9,999회. 인덱스열은 `derived_seed(seed, "H1")`로 생성하고 4개 전략에 **같은 인덱스열**을 쓴다(전략 간 의존성 보존).
- **p값:** m*_{s,b} = 재표본 b의 c^s 평균,
  **p1_s = (1 + #{b : m*_{s,b} ≥ m_s}) / (B + 1).**
- 보고 전용: L = 5, 60의 p값, Newey-West(lag 20) t값.
- 유효성 전제: r^s가 약한 의존성을 가진 정상 과정이라는 근사. 노출 전환과 변동성 국면 때문에 근사가 완전하지 않으므로 블록 길이
  민감도와 Newey-West를 함께 보고한다.

### 10.3 H2 (시점 선택의 기여) — 단측

- **귀무가설 H2₀,s:** 실현된 가격 경로를 조건으로, 전략의 보유 배치는 같은 보유 구간 길이 목록을 가진 무작위 배치(B1)와 교환 가능하다
  (시점 선택의 가치가 없다). **대립가설:** 전략의 m이 무작위 배치보다 크다. 오른쪽 단측 검정.
- **검정통계량:** m_s (B1 배치에도 같은 비용·기준 시각 적용).
- **귀무가설하 재표본추출:** 8절 절차로 B1 배치를 K = 9,999개 생성한다(seed `derived_seed(seed, "H2", s)`). 각 배치 k의 평균 m^B1_{s,k}.
- **p값 (Monte Carlo 무작위화 검정):**
  **p2_s = (1 + #{k : m^B1_{s,k} ≥ m_s}) / (K + 1).**
- 유효성 전제: 귀무가설 자체가 "관측 배치는 무작위 배치 중 하나"이므로 이 p값은 Monte Carlo 오차 안에서 정확하다. B1은 총 노출과
  거래 횟수를 보존하므로 BTC의 장기 drift는 귀무 분포에도 들어 있다.

### 10.4 다중검정 범위

- S의 주장은 "H1₀,s와 H2₀,s를 **둘 다** 기각"이다. 그 귀무가설은 합집합 H1₀,s ∪ H2₀,s이고, 교집합-합집합(IUT) 원리에 따라
  **pS_s = max(p1_s, p2_s)**는 이 합집합 귀무가설에 대한 유효한 p값이다.
- **Holm 보정은 primary 4개의 pS에만** 적용한다. 오름차순 p(1) ≤ … ≤ p(4)에 대해
  p̃(j) = max_{i ≤ j} min(1, (5 − i)·p(i)). **S = PASS ⇔ p̃_s ≤ 0.05.** 4개 전략의 S 주장 전체에서 거짓 주장 확률이 0.05 이하다.
- secondary 5개는 같은 절차를 별도 family로 적용하고 "탐색"으로 표시한다. primary 판정에 영향을 주지 않는다.
- holdout·forward 검정(10.6)은 S = PASS 전략에만 적용한다. 두 개 이상이면 그 전략들의 해당 검정 p값에 Holm을 적용한다.
- 보고 전용: 보정 전 p1, p2, 각 family의 Holm 값, 낮은 수수료 시나리오의 p값.

### 10.5 Sharpe 차이와 기타 보고

- ΔSR_{s,B} = √365 · (mean(r^s)/sd(r^s) − mean(r^B)/sd(r^B)), B ∈ {B2, B4}. (r^s, r^B)를 같은 인덱스열로 쌍 stationary bootstrap
  (B = 9,999, seed `derived_seed(seed, "SR", s, B)`)하여 95 % 백분위 신뢰구간을 보고한다. E_op에는 점추정만 쓴다.
- deflated Sharpe(Bailey–López de Prado, 시도 수 9, 확증 평가 기간의 왜도·첨도), 연도별 net, MDD와 회복 기간, 국면별 성과(사후 분류).
- MDE_SR ≈ 2.49/√(n/365)와 관측 Sharpe로 계산한 필요 기간 (2.49/SR)².

### 10.6 실패 증거 검정 (E의 REJECT 근거, holdout·forward)

경제성 실패를 REJECT하려면 "수익이 없다"는 **충분한 증거**가 필요하다. 다음 검정을 미리 정한다.

- **무익성(futility) 검정, 확증 기간:** 의미 있는 최소 효과를 연 Sharpe 0.5로 정한다(δ_s = 0.5 · sd(r^s) / √365, 일 단위).
  r^s를 그대로(평균 이동 없이) stationary bootstrap(B = 9,999, seed `derived_seed(seed, "FUT", s, 시나리오)`)한 평균의 95 % 분위수를
  U_s라 하면, **U_s < δ_s이면 "의미 있는 수익 없음"의 충분한 증거**다. 민감도로 최소 효과 0.3·0.7을 보고한다.
- **무작위보다 나쁨, 확증 기간:** p2low_s = (1 + #{k : m^B1_{s,k} ≤ m_s}) / (K + 1) ≤ 0.05이면 "무작위 배치보다 나쁨"의 충분한 증거다.
- **holdout·forward 차이 검정:** H₀: μ_hold ≥ μ_conf. 두 구간을 각각 평균을 0에 맞춰 독립적으로 stationary bootstrap(B = 9,999,
  seed "HOLD"/"FWD")하고, d = m_conf − m_hold에 대해 10.2와 같은 식으로 p값을 계산한다. p < 0.05이면 유의하게 나쁨.
- **holdout·forward 음수 검정:** H₀: μ ≥ 0, 대립가설 μ < 0(왼쪽 단측). 10.2 절차의 부호를 바꿔 p < 0.05이면 유의하게 음수.

## 11. 경제성 판정 E와 종합 판정

### 11.1 표본 충분 조건

확증 평가 기간 ≥ 5년, 왕복 ≥ 20회. 미달이면 `INSUFFICIENT_SAMPLE`.

### 11.2 경제성 판정 E (primary 전략별, 판정 수수료, C = 1,000만 KRW)

| 조건 | 통과 기준 (점추정) | 실패 시 충분한 증거 (10.6) |
|---|---|---|
| E-a 수익성 | E0에서 m_s > 0 그리고 m_s > mean_k(m^B1_{s,k}) | E0 무익성(U_s < δ_s) 또는 p2low_s ≤ 0.05 |
| E-b 스트레스 | E1과 E2에서도 m_s > 0 | E1 또는 E2의 무익성 |
| E-c 연도 일관성 | net > 0인 연도 비율 ≥ 60 % | 없음 (단독으로는 REJECT 근거가 아님) |

- **E = PASS:** E-a, E-b, E-c 모두 통과.
- **E = FAIL:** E-a 또는 E-b가 실패했고, 그 조건의 충분한 증거가 있음.
- **E = INCONCLUSIVE:** PASS도 FAIL도 아님(점추정은 실패했지만 실패 증거가 부족, 또는 E-c만 실패).
- **E = FEE_UNCONFIRMED:** 판정 수수료가 미확인(25 bp 가정)이고 판정 수수료에서는 PASS가 아니지만, 5 bp 또는 15 bp에서는 PASS.
  수수료가 확인되면 이 값은 쓰지 않는다.
- **양(+)의 연도 비율 민감도 (보고):** 50 %·70 %에서의 E 결과. 판정은 60 %로만 한다.

### 11.3 종합 판정 (위에서부터 처음 해당하는 행)

| # | 단계 | 조건 | 결과 코드 | 판정 |
|---|---|---|---|---|
| 1 | Q | Q = INVALID | `INSUFFICIENT_DATA` | RESEARCH_MORE |
| 2 | 표본 | 11.1 미달 | `INSUFFICIENT_SAMPLE` | RESEARCH_MORE |
| 3 | Q | Q = SENSITIVE (Q13 재계산이 4–8행 중 다른 행에 해당) | `DATA_SENSITIVE` | RESEARCH_MORE |
| 4 | E | E = FEE_UNCONFIRMED | `FEE_UNCONFIRMED` (f* 보고) | RESEARCH_MORE |
| 5 | E | E = FAIL, E-a 실패 | `UNPROFITABLE` | **REJECT (수익성 부족의 충분한 증거)** |
| 6 | E | E = FAIL, E-b 실패 | `NOT_ROBUST` | **REJECT (스트레스 실패의 충분한 증거)** |
| 7 | E | E = INCONCLUSIVE | `ECONOMIC_INCONCLUSIVE` (실패 조건과 U_s, p2low 보고) | RESEARCH_MORE |
| 8 | S | E = PASS, S = FAIL | `UNDERPOWERED` (MDE, 필요 기간 보고) | RESEARCH_MORE |
| 9 | L2 | E = PASS, S = PASS, holdout 미개봉 | `PENDING_HOLDOUT` | RESEARCH_MORE |
| 10 | L2 | holdout 차이 검정 또는 음수 검정 p < 0.05 | `HOLDOUT_FAIL` | **REJECT (유의한 실패)** |
| 11 | L2 | holdout net ≤ 0 또는 B1 대비 초과 ≤ 0 (유의하지 않음), **forward 데이터가 아직 없음** | `HOLDOUT_WEAK` | RESEARCH_MORE (forward 진행, 24개월 필요) |
| 12 | L3 | forward 12개월 미만 (holdout이 약했던 전략은 24개월 미만), 13·14행 미해당 | `PENDING_FORWARD` | RESEARCH_MORE |
| 13 | L3 | forward 차이 검정 또는 음수 검정 p < 0.05 | `FORWARD_FAIL` | **REJECT (유의한 실패)** |
| 14 | L3 | forward MDD > 확증 평가 MDD × 1.5 | `RISK_LIMIT` | **REJECT (사전 위험 한도 위반)** |
| 15 | L3 | net ≤ 0 또는 초과 < 0 (유의하지 않음), 24개월 미만 | `FORWARD_WEAK` | RESEARCH_MORE (24개월까지 연장) |
| 16 | L3 | 24개월에도 15행 상태 (holdout이 약했던 전략 포함) | `FORWARD_INCONCLUSIVE` | **study 종료** (REJECT 아님) |
| 17 | E_op | forward 통과, E_op = OP_FAIL 또는 OP_UNDETERMINED (판정 자본) | `CONFIRMED_NO_OPERATING_VALUE` | 가설은 지지, 운용 가치 미달 (PAPER_CANDIDATE 아님) |
| 18 | – | forward 통과(net > 0, 초과 ≥ 0, MDD ≤ 1.5배), E_op = OP_PASS | `CONFIRMED` | PAPER_CANDIDATE |

- **REJECT는 5·6행(확증 기간의 충분한 실패 증거), 10·13행(유의한 실패), 14행(사전 위험 한도)뿐이다.** 증거 부족은 모두 RESEARCH_MORE
  또는 미확정 코드(`ECONOMIC_INCONCLUSIVE`, `UNDERPOWERED`, `HOLDOUT_WEAK`, `FORWARD_WEAK`, `FORWARD_INCONCLUSIVE`)다.
- 우선순위 근거: 데이터·표본 문제(1–3행)는 모든 결과를 무효로 만드므로 먼저 본다. 수수료 미확인(4행)은 판정 수수료 자체가 가정이므로
  REJECT보다 앞선다. 경제성 실패(5–7행)는 통계 유의성과 무관하게 판정하고, S는 E가 통과한 경우에만 결과를 가른다(8행).
- holdout은 10행(유의한 실패)이 아니면 forward로 진행한다. holdout이 약했던 전략(11행 조건)은 forward 데이터가 생긴 뒤에도
  12·16행에서 24개월 기준을 적용받는다.
- forward "통과"는 12개월 이상(holdout이 약했으면 24개월 이상)에서 net > 0, B1 대비 초과 ≥ 0, MDD ≤ 확증 평가 MDD × 1.5다.
- 각 결과에는 네 축(Q, S, E, L)과 E_op 값을 함께 기록한다. 예: `Q=VALID, S=FAIL, E=PASS, L=L1 → UNDERPOWERED`.
- secondary는 최대 RESEARCH_MORE. **PAPER_CANDIDATE도 실거래·Paper 승격이 아니다.** Paper Trading 설계를 검토할 자격만 뜻한다.

## 12. AI Agent 역할 분리

| 단계 | 규칙 기반 Python | AI 모델 호출 | v0.6 결정 |
|---|---|---|---|
| 데이터 수집 | `HttpClient` + 원문 저장 + 해시 | 불필요 (추측 파싱 위험) | Python |
| 신호 계산 | 순수 함수, 테스트 가능 | **금지** (학습 데이터의 미래 가격, 비결정성) | Python |
| 전략 평가 | 순수 함수, bootstrap, Holm | 런타임 불필요. 개발 시 코드 작성·리뷰·보고서 보조(일회성) | Python (+개발 보조) |
| 위험관리 | 고정 한도 | **금지** | Python |
| 거래 실행 | 범위 밖(절대 규칙 1) | 범위 밖 | 해당 없음 |
| 이상 탐지·장애 조사 | 품질 지표 임계값으로 1차 탐지 | 조건부 (임계값 초과 시 incident 분석 보조) | 조건부 호출 |

AI를 결정 경로에 넣는 전략은 별도 study로 다루고, 그 경우 9절 비용과 look-ahead 통제(모델 knowledge cutoff 이후 구간만 평가)를 사전등록한다.

## 13. 알려진 bias와 대응

| bias | 대응 |
|---|---|
| look-ahead | 정착 규칙 + `closed_as_of`, 00:59 제출 실행 규칙, 시나리오별 수익률 기준 시각, "t 이후 데이터 변경 시 신호 불변" 속성 테스트, AI 신호 금지 |
| 이력 기반 선택 편향 | 2절 증거 수준. L1·L2는 반증·일관성 확인만, PAPER_CANDIDATE는 L3 필수 |
| 파라미터 과최적화 | N 고정, secondary 분리, IUT + Holm, deflated Sharpe(시도 수 9), 분석 갈래를 이 문서에 모두 고정 |
| drift를 신호로 착각 | H2 (B1 대비) |
| 변동성 손실 | 로그수익률로 판정 |
| 체결 가능성 | 실행 규칙과 근사 체결가 분리, κ 5/10 bp, E1·E2 필수 스트레스, E3 보고 |
| 비용 과소평가 | 진입·청산 각각 f + κ + ι(C), 판정 수수료 25 bp(미확인 시), 판정 자본 1,000만 KRW, 규모 민감도 |
| 데이터 결측·수정 | 5절 Q2–Q13, 첫 수집본 고정, 임계값 민감도 |
| 생존 편향 | 단일 종목. 거래소(Upbit)·종목(BTC)의 사후 선택 한계를 결론에 명시 |
| 검정력 부족 | 3절 기록, 무익성 검정 없이는 REJECT하지 않음, 미확정 코드 분리 |
| 세금 | 판정 제외, 세후 시나리오 별도 |

## 14. 후속 연구 후보: 복합 Alpha (범위 밖)

외부 자료("A Unified Framework for Alpha Extraction and Signal Combination", 사용자 요약 기준, **원문 미검토·성과 미검증**)의 절차는
다종목 point-in-time universe(상장폐지 포함), t−1까지의 rolling 통계, nested walk-forward, 시도 수 전체 기록이 필요하다.
착수 조건: v0.6 primary 중 하나 이상이 REJECT가 아닐 것, 다종목 캔들 응답 확인, 별도 사전등록(v0.7).

## 15. 2026-10-12 수집 기록 (파이프라인 검증, 수익성 검증 아님)

가격·수익률은 분석하지 않았다. 이 표본(9일·9시간)은 가설 선택에 쓰지 않는다. 상세는 부록 B.

## 16. 수집·검증 실행 순서 (고정 후, 각 단계 사용자 승인)

1. 일봉 전체: `candles-pull --interval day --start 2017-01-01T00:00:00Z --end <당일 00:00Z> --page-count 200 --max-pages 25` (약 18 요청, 약 15초)
2. 1시간봉 전체: 같은 범위, `--max-pages 420` (약 396 요청, 약 2–3분, 약 29 MB)
3. 품질 판정 Q1–Q10 (수익률 미열람)
4. 7일 이상 뒤: 최근 60일 재수집(일봉 1, 1시간봉 8 요청)과 일봉 전체 재수집(약 18 요청) → Q11, Q12
5. 백테스트 구현 (3–4단계 대기 중 합성 데이터로 개발 가능)
6. 확증 평가 → S·E·E_op·종합 판정 → Q13
7. 일봉 전체 재수집(Q12) 후 historical holdout 1회 개봉
8. forward 월 1회 수집 (일봉 `--last 35`, 1시간봉 `--last 840`, 자동 반복 없음)

모든 live 수집은 같은 인자의 dry-run을 먼저 보이고, UTC 00:00–00:05와 정시 직후 3분을 피하며, 직후 `candles-verify`를 실행한다.
상장 이전 `to`가 오류를 반환하면 원본을 보존하고 재수집 승인을 요청한다.

## 17. 고정 절차

1. 사용자가 이 초안과 18절 결정 사항을 확정한다.
2. 확정본을 `docs/research_v06_preregistration.md`, `configs/research_v06.toml`로 만들고 SHA-256을 기록한다(커밋은 사용자 승인 후).
3. 이후 문서·설정 변경은 새 study다. 예외는 사실 입력 `account_fee_bps`, `tax_rule`(세후 보고 전용)뿐이며, holdout 개봉 후에는 바꾸지 않는다.

## 18. 고정 전 결정 사항 (사용자)

| # | 항목 | 현재안 |
|---|---|---|
| 1 | 계정 수수료 | 공식 확인 전 25 bp (보수적 가정) |
| 2 | 계획 자본 / 판정 자본 | 100만 / 500만 / 1,000만 KRW, 판정은 1,000만 |
| 3 | 시장 충격 가정 | ι_ref = 1.0 bp @ 100만 KRW, √ 스케일 |
| 4 | 무익성 최소 효과 | 연 Sharpe 0.5 (민감도 0.3·0.7) |
| 5 | 양(+)의 연도 비율 | 60 % (민감도 50·70 %) |
| 6 | 품질 임계값 | 5절 (민감도 0.5배·2배) |
| 7 | AI_ops 세션 빈도·단가, Infra 입력값 | 미정 |
| 8 | guard 규칙 (`candles-pull` live, holdout 개봉 명령) | 제안만 됨, 사용자 결정 |

## 부록 A. config 초안 (`configs/research_v06.toml` 예정, 아직 파일 생성 안 함)

```toml
[study]
name = "moneylab-v0.6-upbit-krw-btc-daily-trend"
version = 1
market = "KRW-BTC"
preregistration = "docs/research_v06_preregistration.md"
provenance_required = "real"
annualization_days = 365
return_type = "log"

[data]
signal_interval = "day"                 # [D 00:00 UTC, D+1 00:00 UTC), verified 2026-10-12
execution_interval = "hour"
settle_seconds = 120
max_missing_day_share = 0.005
max_missing_hour_share = 0.010
max_consecutive_missing_days = 2
max_consecutive_missing_hours = 6
max_gap_events_confirmatory = 3
turbulent_quantile = 0.90
max_turbulent_missing_share = 0.01      # or 2x overall missing share, whichever is larger
max_conflict_or_invalid_share = 0.001
max_day_hour_mismatch_share = 0.005
max_prev_close_mismatch_share = 0.005
max_signal_affected_share = 0.01
max_fill_fallback_share = 0.01
max_revised_share = 0.005
revision_recheck_days = 60
revision_recheck_min_delay_days = 7
threshold_sensitivity_factors = [0.5, 2.0]   # report only

[split]
warmup_days = 120
confirmatory_end = "2024-03-31"
confirmatory_sub_start = "2022-07-01"   # report only
holdout_start = "2024-04-01"            # locked, opened once
forward_min_months = 12
forward_max_months = 24

[strategy]
primary = ["M20", "M60", "M120", "R5"]
secondary = ["M24h", "M72h", "M168h", "M60_voltarget", "M_combo_equal"]
deflated_sharpe_trials = 9
missing_signal_rule = "hold_previous"

[execution]
# scenario = [order submit (UTC, D+1), approximation price, one-way spread+slippage bps, role]
E0 = ["00:59:00", "hour_close_00", 5.0, "decision"]
E1 = ["01:59:00", "hour_close_01", 10.0, "economic_stress_required"]
E2 = ["23:59:00", "day_close_d1", 10.0, "economic_stress_required"]
E3 = ["none", "hour_00_worst", 10.0, "report_only"]
diagnostic = ["none", "day_open_d1", 5.0, "diagnostic"]
fill_fallback = "next_hour_close_then_next_reference"
mark_missing_hour = "last_available_hour_close"

[costs]
fee_bps_scenarios = [0.0, 5.0, 15.0, 25.0]   # 0 = diagnostic only
decision_fee_bps_if_unconfirmed = 25.0
# account_fee_bps =                     # official source + date only
impact_ref_bps = 1.0                    # assumption, at impact_ref_capital_krw
impact_ref_capital_krw = 1000000
impact_scaling = "sqrt"
impact_multipliers = [0.0, 1.0, 2.0]    # report only
planned_capital_krw = [1000000, 5000000, 10000000]
decision_capital_krw = 10000000
capacity_unverified_above_krw = 10000000

[tax]                                    # report only, never in a decision
# rule =                                 # official source + effective date only
hypothetical_rates = [0.0, 0.10, 0.20, 0.30]

[stats]
bootstrap = "stationary"
bootstrap_mean_block_days = 20
bootstrap_block_robustness = [5, 60]    # report only
bootstrap_resamples = 9999
random_exposure_draws = 9999
seed = 20261012
hac_lag_days = 20
multiple_testing = "holm_on_iut_max_p"  # pS = max(p1, p2), Holm over the 4 primary
alpha_one_sided = 0.05
futility_min_annual_sharpe = 0.5
futility_sensitivity = [0.3, 0.7]       # report only
futility_quantile = 0.95

[decision]
min_confirmatory_years = 5
min_roundtrips = 20
min_positive_year_share = 0.60
positive_year_sensitivity = [0.50, 0.70]   # report only
forward_max_mdd_ratio = 1.5
holdout_fail_alpha = 0.05
forward_fail_alpha = 0.05
```

## 부록 B. 2026-10-12 수집 기록

| pull | 시각 (UTC) | 요청 | 결과 | 원문 SHA-256 | 검증 |
|---|---|---|---|---|---|
| `day_KRW-BTC_20261012T094735818002Z` | 09:47:35 | `count=10, to=2026-10-13T00:00:00Z`, 1회, 재시도 없음 | HTTP 200, 10행, 진행 중 1개 제외, 확정 9개(10-03~10-11), 중복·누락·값 이상 0 | `b00a2fed…f176d` | `candles-verify` ok |
| `hour_KRW-BTC_20261012T094742435199Z` | 09:47:42 | `count=10, to=2026-10-12T10:00:00Z`, 1회, 재시도 없음 | HTTP 200, 10행, 진행 중 1개 제외, 확정 9개(10-12 00:00~08:00), 중복·누락·값 이상 0 | `26f6cdaf…adb62` | `candles-verify` ok |

- 로컬 수신 시각과 서버 `Date`의 차이는 1 s 미만이다(`Date`는 초 단위).
- `to`에 미래 경계를 넣었으므로 `to`의 경계 포함 여부는 이 수집으로 판별되지 않았다.
