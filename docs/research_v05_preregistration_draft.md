# MoneyLab v0.5 사전등록 초안: Upbit KRW-BTC 장기 horizon(60–300s) microstructure 예측력과 현물 경제성

상태: **초안(DRAFT), 아직 고정되지 않음.** 이 문서는 사용자 검토용이다. 고정 절차(15절)를 거치기 전까지는 해시를 기록하지
않고, 데이터를 수집하지 않으며, 코드를 바꾸지 않는다. 고정되면 `docs/research_v05_preregistration.md`와
`configs/research_v05.toml`(부록 A)이 되고, 두 파일의 SHA-256이 모든 v0.5 run manifest에 기록된다.

이 연구는 **읽기 전용**이다. 실제 주문, API key, 계좌 연결, 자동매매, Paper Trading 승격은 범위 밖이다.

## 0. v0.4와의 관계 (새 study)

- v0.5는 v0.4(`moneylab-v0.4-upbit-krw-btc-microstructure`, prereg `f86792c0…`, config `c16b22a3…`)의 수정본이 아니라
  **별도 study**다. v0.4의 문서·설정·결과·test lock은 바꾸지 않는다.
- v0.4 세션 `session_20261009T2206KST`는 v0.5에서 **어떤 용도로도 쓰지 않는다**(dry-run 포함). 원본 raw에는 v0.4의 잠긴
  test 구간이 들어 있으므로, 다시 처리하면 사실상 test를 여는 것이 된다. v0.4 run의 `locked/test.jsonl.gz`는 열지 않는다.
- v0.4의 train/validation 결과는 **가설을 만드는 데에만**(feature 선정, 표본 크기 계획) 쓴다. v0.5의 증거는 v0.5용으로
  새로 수집한 세션에서만 나온다.

## 1. 배경: v0.4 결과 요약

| 항목 | v0.4 결과 (세션 1개, 6h, 2026-10-09 22:06–04:06 KST) |
|---|---|
| 데이터 | real, integrity OK, 유효 grid 97.9%, 대기 모드로 인한 326 s gap 1건, clock WARNING |
| 검정 | 29 feature × h{1,5,10,30}s = 116 조합 |
| 판정 | REJECT 112 (NEGATIVE_EVIDENCE), RESEARCH_MORE 4 (trade_flow_imbalance_1s, 결측 84%), PAPER_CANDIDATE 0 |
| 예측력 | 호가 불균형 계열의 validation IC가 유의함. depth_imbalance_5bp h30 IC 0.38 [0.28, 0.47], BH q<0.001, 단조성 1.0. 116개 중 23개 조합이 BH q<0.05, CI가 0을 포함하지 않음, train/validation 부호 일치를 모두 충족 |
| 경제성 | 최대 gross 1.2 bp. 비용 52–55 bp(수수료 25bp×2 + spread 약 3 bp). 수수료 0bp로 외삽해도 최선 net −2.4 bp, 양수 조합 0개 |
| 지연·크기 | 0→250 ms 지연 영향 ≤ 0.1 bp. 0.01 BTC는 0.001 BTC보다 0.5–0.9 bp 불리 |

v0.4에서 얻은 결론: **예측력은 있지만 1–30 s의 가격 움직임이 왕복 spread보다 작다.** v0.5는 horizon을 늘려 gross가
비용을 넘는지를 검증한다.

## 2. 질문과 가설

> Upbit KRW-BTC에서 t 시점의 호가 불균형·유동성 상태가 t+60/120/300 s의 가격 움직임을 예측하는가?
> 그 예측으로 **long-only(매수 후 매도, 평소 현금 보유)** 현물 전략을 운용하면, 실제 체결 가능 가격과 수수료를 반영한 뒤에도
> net edge가 양수이고, 같은 노출을 무작위로 잡는 경우보다 나은가?

- **H1 (예측력, primary):** primary signal(5절)의 validation Spearman IC 부호가 train과 같고 0과 다르다.
- **H2 (경제성, primary):** primary signal의 long-only/cash 전략(7절) net edge > 0 (판정 수수료 기준).
- **H3 (signal 기여, primary):** 같은 전략의 net이 거래 수와 보유 시간을 맞춘 무작위 진입 benchmark보다 크다(excess > 0).
  이 검정은 상승장 drift를 signal로 착각하는 것을 막기 위한 것이다.
- **귀무가설:** 위 세 가지가 모두 0 이하다. 판정은 H1–H3을 모두 통과해야 한다(10절).

## 3. 사전 경제성 점검 (v0.4 train/validation 기술통계, 계획용 추정)

| horizon | mid 변동 sd | 왕복 crossing 비용 (0.001 BTC, 수수료 제외) | net > 0에 필요한 gross (fee 0 / 5 / 15 / 25 bp) | 1.5× 비용 기준을 넘는 데 필요한 gross (fee 5 / 25 bp) |
|---|---|---|---|---|
| 60 s | 3.8 bp | 약 3.2 bp | 3.2 / 13.2 / 33.2 / 53.2 | 19.8 / 79.8 |
| 120 s | 5.6 bp | 약 3.2 bp | 같음 | 같음 |
| 300 s | 9.3 bp | 약 3.2 bp | 같음 | 같음 |

- v0.4 하나의 야간 세션(약 4.8 h)에서 얻은 추정치다. 주간의 변동성은 더 클 수 있다.
- IC가 0.3이라고 낙관해도 top quintile의 기대 gross는 0.3 × sd × 약 1.4이다. 300 s에서 **약 4 bp**로, 수수료 5bp 시나리오의 손익분기(약 13 bp)에도 못 미친다.
- **따라서 사전 기대는 "판정 수수료 25bp에서 REJECT, 손익분기 수수료는 0–2bp 수준"이다.** v0.5의 주된 가치는 이 기대를
  새 데이터로 확인하고, horizon별 손익분기 수수료와 gross/spread 비를 정량화하는 데 있다. 이 점을 알고 수집 비용을
  승인할지는 사용자가 결정한다(16절, 약 86 h).

## 4. 데이터

| 항목 | 값 |
|---|---|
| 시장/소스 | Upbit KRW-BTC, 공개 WebSocket orderbook(30 units) + trade. 기존 recorder 재사용 |
| provenance | `real`만 증거. fixture/synthetic은 `NOT_EVIDENCE` |
| 세션 길이 | 명목 **12 h** (`nominal_session_seconds = 43200`). 실제 길이가 90% 미만이면 무효 |
| 세션 구성 | pilot 1 + development 4 + test 2. 모두 **서로 다른 날짜**(8절) |
| raw 위치 | `data/raw/upbit/research_v05/<session_id>/KRW-BTC/` (v0.4 경로와 분리) |
| 시계 | recorder 내장 clock monitor, 60 s 간격, `--stop-on-clock-unstable` |
| 수집 환경 | 수집 전에 사용자가 절전과 최신 대기 모드를 끈다. 시스템 설정은 코드가 바꾸지 않는다 |

**세션 유효성** (label·통계를 보기 전, 품질 보고서만으로 판정):
1. integrity OK, replay-check OK
2. 길이 ≥ 90% × 12 h
3. clock 상태가 `CLOCK_UNSTABLE`이 아님
4. 유효 grid 비율 ≥ 0.90
5. gap 행 비율 ≤ 5%

무효 세션은 결과를 보지 않고 버리며, **다른 날짜의 새 세션으로 교체**한다. 교체 사실과 사유는 study 기록에 남긴다.

확인되지 않은 사실 (v0.4와 같음, 가정하지 않는다):
- 메시지 timestamp의 의미
- `ask_bid`의 taker 방향 여부
- 호가 단위
- 계정 수수료
- 최소 주문 금액(공식 문서 미확인, 0.001 BTC ≈ 11만 KRW라 일반적인 하한보다 큰 것으로 추정)

## 5. Feature

시간 축, sampling, 품질 flag, 행 제외 규칙은 v0.4 3–4절과 같다(수신 시각 as-of, 1 s grid, warmup 5 s, stale 1 s, gap 10 s).
최대 lookback은 **300 s**다.

**Primary family (확증 검정, 5 signal × 3 horizon = 15 검정):**

| signal | 정의 | 선정 근거 |
|---|---|---|
| depth_imbalance_5bp | v0.4 5절과 같음 | v0.4 validation IC 최대 |
| depth_imbalance_10bp | v0.4와 같음 | 같음 |
| obi_1 | v0.4와 같음 | train/validation 부호 일치, 단조성 높음 |
| book_slope | v0.4와 같음 | 같음 |
| imbalance_composite | 위 4개를 train 평균·표준편차로 z-score화하고 train IC 부호를 곱한 뒤 단순 평균. 가중치 추정 없음 | 4개 신호를 하나로 묶어 검정 수를 늘리지 않고 잡음을 줄인다 |

**Secondary family (탐색, 17 signal × 3 horizon = 51 검정):**
- 호가: obi_5, obi_10, obi_30, microprice_dev_bps
- 평활 불균형(신규): depth_imbalance_5bp_avg60, obi_1_avg60. (t−60, t]의 1 s grid 값 평균이며 결측 행은 제외하고, 유효값이 50% 미만이면 NaN
- 유동성: spread_bps, liquidity_concentration, bid_depth_30, ask_depth_30, realized_vol_300s
- 체결 흐름(신규 창): signed_volume_60s, signed_volume_300s, trade_flow_imbalance_60s, trade_flow_imbalance_300s
- 모멘텀: return_60s, return_300s

**규칙:**
- secondary 결과로는 PAPER_CANDIDATE가 나올 수 없다. 양성 결과는 다음 study의 가설로만 쓴다.
- 가격 수준(mid, microprice, spread KRW)은 v0.4처럼 state로만 저장하고 검정하지 않는다.

## 6. Label

- horizon h ∈ {60, 120, 300} s, wall-clock. 미래 가격은 t+h 시점의 as-of book이다.
- `future_mid_move_bps_h = 1e4 · (m_{t+h}/m_t − 1)`
- 실행 가능 수익률 (수수료 전, 크기 Q ∈ {0.001, 0.01} BTC, 지연 Δ ∈ {0, 250, 1000} ms):
  - `exec_long_bps = 1e4 · (VWAP_bid(t+h+Δ, Q) / VWAP_ask(t+Δ, Q) − 1)`: 매수 후 매도 (v0.4 exec_buy와 같음)
  - `exec_overlay_bps = 1e4 · (VWAP_bid(t+Δ, Q) / VWAP_ask(t+h+Δ, Q) − 1)`: 보유 재고를 매도한 뒤 재매수 (v0.4 exec_sell과 같음)
  - 30 units 안에서 Q를 채울 수 없으면 NaN이다. NaN 비율은 보고하고, 1%를 넘으면 해당 조합은 INSUFFICIENT_EVIDENCE다.
- 수수료 적용 공식은 v0.4와 같다: `net = 1e4 · ((1 + exec/1e4) · (1−f)/(1+f) − 1)`.
- label 창에 불연속 행(gap/warmup/no_book)이 있으면 label은 NaN이다.

## 7. 전략 (현물 long-only, 공매도 없음)

**S1 long/cash (primary 경제성).** 평소에는 현금을 보유한다.
1. 포지션이 없고 행이 정상일 때, d·x_t ≥ q80_train(d = sign(IC_train))이면 t+Δ에 ask VWAP으로 Q를 매수한다.
2. 정확히 h를 보유한 뒤 bid VWAP으로 매도한다. 수수료는 양쪽에 적용한다.
3. 포지션은 한 번에 하나뿐이다(중첩 없음). 청산 직후 다음 진입이 가능하다.
4. 청산 시점의 행이 불연속이면 **첫 유효 book에서 강제 청산**하고 그 결과를 포함한다. 버리지 않는다.
   강제 청산 건수는 보고한다.
5. 세션 끝까지 보유 중인 포지션은 마지막 유효 book에서 청산해 포함한다.

**B1 matched random entry (H3의 benchmark).**
- S1과 거래 수와 보유 시간이 같다.
- 진입 시각은 "포지션 없음 & 정상 행" 시각 중에서 무작위로 고른다. seed를 고정하고 1000회 뽑는다.
- excess = mean(S1 net) − mean(B1 net). p값은 B1 분포에서의 순위로 정한다.

**B2 buy-and-hold:** 같은 구간에서 0.001 BTC를 계속 보유한 수익률이다. 보고만 한다.

**S2 inventory overlay (secondary).**
- 평소에 Q BTC를 보유한다.
- d·x_t ≤ q20_train이면 매도하고, h 뒤에 재매수한다.
- 성과는 계속 보유한 경우 대비로 측정한다(`exec_overlay_bps`의 net).
- 이 결과만으로는 PAPER_CANDIDATE가 될 수 없다.

추가 규칙:
- maker 주문, 지정가 대기, rebate는 범위 밖이다. L2 스냅샷으로는 대기열과 체결을 검증할 수 없다.
- 체결 가정은 보수적으로 둔다. 같은 시점 book의 VWAP을 쓰고, 자기 주문이 이후 book에 주는 영향은 무시한다. 소량 주문이라 영향이 작다는 가정이며 이를 명시한다.

## 8. 세션 계획과 split

| 단계 | 세션 | 용도 | 비고 |
|---|---|---|---|
| P0 | pilot 1개 (≥ 2 h) | 파이프라인·품질 dry-run | **증거에서 영구 제외**. label 통계를 보지 않는다 |
| D1–D4 | development 4개 × 12 h | train/validation | 시작 시각을 바꿔 가며 수집: 21:00, 09:00, 21:00, 09:00 KST |
| freeze | — | 개발 동결 | 아래 참조 |
| T1–T2 | test 2개 × 12 h | test (한 번만) | **동결 이후에 수집한다.** 시작 시각 21:00, 09:00 |

- 날짜: 7개 세션 모두 서로 다른 날짜다. 요일과 시간대는 기록만 하고 통제하지 않는다.
- 최소 조건: PAPER_CANDIDATE를 판정하려면 유효한 dev 세션 ≥ 2, test 세션 ≥ 1, 서로 다른 날짜 ≥ 3이 필요하다.
  계획(4 + 2)보다 적으면 검정력이 부족하다(11절). 이 경우 결과는 INSUFFICIENT_EVIDENCE 쪽으로 판정된다.
- **dev 세션 내부 split:**
  - 시간순으로 train 75% | embargo 600 s | validation 25%로 나눈다.
  - embargo 600 s는 최대 lookback 300 s와 최대 horizon 300 s를 합한 값이다.
  - purge: label 창의 끝(t+h+Δmax)이 자기 구간 끝을 넘으면 그 horizon에서 제외한다.
  - lookback 창이 구간 시작보다 앞으로 넘어가면 NaN이다.
- **pooling:**
  - train은 D1–D4의 train 구간을 합친 것이다.
  - quintile 경계, 방향 d, z-score 모수, median은 **pooled train에서만** 정한다.
  - validation은 D1–D4의 validation 구간을 합친 것이다.
- **test lock:**
  - T1–T2는 build 시점에 전부 `locked/`에 들어간다. `research-stats`는 읽지 못한다.
  - `research-final`만, 동결 해시가 일치할 때 **정확히 한 번** 연다. 접근 횟수는 manifest에 기록된다.
- **개발 동결 (freeze):**
  - validation leaderboard가 완료되면 동결 manifest를 만든다. 여기에는 train fit(경계, 방향, z 모수), 전략 규칙, 판정 수수료, prereg/config 해시를 담고 그 해시를 기록한다.
  - test 세션은 동결 manifest의 시각 **이후에** 수집을 시작한다. test 데이터는 개발 중에 존재하지 않았다.
- **세션 추가 금지:** validation을 본 뒤 dev 세션을 추가하면 optional stopping이 된다. 표본이 부족하면 이 study는
  INSUFFICIENT_EVIDENCE로 끝나고, 추가 수집은 새 study(v0.5.1, 새 해시)로 한다.

## 9. 통계

모든 통계는 signal × horizon마다 train과 validation 각각에서 계산한다.

- **IC:** Spearman IC를 **세션 내부에서** 계산하고 유효 N으로 가중 평균한다. 날짜마다 수준이 다른 feature가 pooled 순위를
  왜곡하지 않게 하기 위해서다. Pearson, quintile 조건부 평균, top-bottom, 방향 적중률, 유효 N(≈ N/h)도 보고한다.
- **신뢰구간:** 세션별로 층화한 stationary block bootstrap을 쓴다. 평균 블록 길이는 max(120 s, 5h)이므로 h300에서는 1500 s다.
  1000회, seed는 고정한다.
- **HAC:** Newey-West, lag = h + 60 s.
- **최소 표본:** bootstrap은 n ≥ 5 × 블록 길이, HAC는 n ≥ 2 × (lag+1)일 때만 계산한다. 아니면 NaN이고 INCONCLUSIVE다.
- **다중 검정:**
  - primary 15개에 BH-FDR(q < 0.05)을 적용한다.
  - secondary 51개에는 **별도로** BH를 적용하고 탐색 결과로 표시한다.
  - 경제성 검정(H2 net > 0, H3 excess > 0)은 primary 15개에 각각 **Holm** 보정(단측 α = 0.05)을 적용한다.
- **경제성 CI:** S1 거래별 net을 단위로 한다. 세션 층화 stationary block bootstrap(평균 블록 10거래)을 쓴다.
  거래는 중첩되지 않지만 시장 국면에 따른 상관이 남기 때문이다.
- **손익분기 수수료:** net = 0이 되는 편도 수수료 f*를 보고한다. 수수료와 무관하게 gross/spread 비도 보고한다.
- **세션 안정성:** S1 net 점추정치의 부호를 세션별(validation 구간)로 보고한다.

## 10. 비용 시나리오와 판정

- 수수료 편도: **0(진단 전용), 5, 10, 15, 25 bp.** 판정 수수료 = `account_fee_bps`이고, 미확인이면 **25 bp**(가장 비싼 시나리오)다.
- `account_fee_bps`는 공식 문서나 계정 화면에서 확인한 값만 설정할 수 있다. 출처와 날짜를 기록한다.
  이것은 사실을 입력하는 것이지 선택이 아니며, 모든 시나리오 결과가 항상 함께 보고되므로 새 study를 만들지 않는 유일한 설정 변경이다.
  단, test를 연 뒤에는 바꾸지 않는다.
- 지연 0/250/1000 ms, 크기 0.001/0.01 BTC 결과를 모두 보고한다. 강건성 시나리오는 1000 ms, 0.01 BTC, 판정 수수료 + 2 bp다.

**PAPER_CANDIDATE 기준** (primary만 해당, 모두 충족해야 함):
1. provenance=real, 모든 사용 세션이 유효(4절). dev ≥ 2, test ≥ 1, 서로 다른 날짜 ≥ 3. 유효 label 비율 ≥ 0.90
2. validation IC 부호 = train IC 부호, IC 95% CI가 0 미포함, primary BH q < 0.05
3. quintile 단조성(방향 보정) ≥ 0.9, train과 validation 모두
4. S1 net(판정 수수료)의 Holm 보정 하한 > 0, gross ≥ 1.5 × estimated cost
5. H3: excess over B1 > 0 (Holm 보정)
6. 강건성 시나리오에서 net > 0
7. validation 비중첩 S1 거래 ≥ 100, 세션별 S1 net 점추정치 > 0인 dev 세션 ≥ 75%
8. test(한 번만): S1 net > 0, excess > 0, IC 부호 동일

**Evidence class:**

| class | 조건 | 판정 |
|---|---|---|
| `INSUFFICIENT_EVIDENCE` | train 방향 없음, CI·q 계산 불가, 비중첩 거래 < 30, 결측 > 0.5, 유효 label < 0.90, label NaN(체결 불가) > 1%, 세션 수 미달 | RESEARCH_MORE. REJECT하지 않는다 |
| `NEGATIVE_EVIDENCE` | 표본 충분 **그리고** (net ≤ 0 **또는** gross < cost **또는** excess ≤ 0) | REJECT |
| `POSITIVE_AT_LOWER_FEE` | 표본 충분, 판정 수수료에서는 음수지만 5/10/15 bp 중 어느 시나리오에서 net > 0 및 excess > 0 | RESEARCH_MORE (`reason=FEE_UNCONFIRMED: break-even f*`). PAPER_CANDIDATE 불가 |
| `POSITIVE_BUT_UNCONFIRMED` | 표본 충분, 판정 수수료에서 net > 0, excess > 0, 1–8 중 일부 미충족 또는 test 미개봉 | RESEARCH_MORE |
| `CONFIRMED` | 1–8 전부, test PASS | PAPER_CANDIDATE |

**상한:**
- secondary family는 최대 RESEARCH_MORE다.
- pilot, dry-run, fixture는 `NOT_EVIDENCE`다.
- test를 열기 전에는 최대 RESEARCH_MORE다.
- **PAPER_CANDIDATE도 실거래나 Paper Trading 승격이 아니다.** 사용자 승인을 받아 Paper Trading 설계를 검토할 자격만 뜻한다.

## 11. 검정력 (계획용 추정, primary 최악 α ≈ 0.05/15, 검정력 80%)

MDE(Minimum Detectable Effect, 검출 가능한 최소 IC) ≈ 3.78 / sqrt(N_eff), N_eff ≈ 유효 초 / h.

| horizon | validation (D1–D4의 25% ≈ 11.4 h) N_eff → MDE | test (T1–T2 ≈ 23 h) N_eff → MDE | validation S1 거래 상한 (≈ T/h) |
|---|---|---|---|
| 60 s | 684 → **0.14** | 1380 → 0.10 | 약 680 |
| 120 s | 342 → **0.20** | 690 → 0.14 | 약 340 |
| 300 s | 137 → **0.32** | 276 → 0.23 | 약 137 (실제 trigger 대기로 더 적음) |

- h300은 validation에서 IC 0.32 미만이면 검출하기 어렵다. 비중첩 거래도 100건 기준에 가깝다.
  h300 결과가 INSUFFICIENT_EVIDENCE일 가능성이 높다는 것을 미리 기록한다.
- 이를 줄이려면 dev 세션을 6개로 늘리거나 세션을 24 h로 늘려야 한다. **고정 전에 결정한다(16절).**

## 12. 알려진 bias와 대응

| bias | 대응 |
|---|---|
| look-ahead | 수신 시각 as-of, 도착 순서 누적 최대 시각, 평활 feature는 (t−60, t]만 사용. "t 이후 이벤트가 바뀌어도 feature(t)는 불변" 테스트 |
| 중첩 label | horizon이 길수록 중첩이 커진다. 블록 길이 max(120 s, 5h) 층화 bootstrap, HAC lag h+60, 유효 N 보고. 경제성은 비중첩 S1 거래로 평가 |
| split 간 leakage | 세션 내 시간순 split + 600 s embargo + purge + 구간 내 lookback. 통계는 pooled train에서만 추정. test 세션은 동결 이후에 수집 |
| v0.4와의 오염 | v0.4 세션 사용 금지, v0.4 test 미개봉. v0.4 결과는 가설 선정에만 쓰고, 선정 근거를 이 문서에 공개 |
| 다중 검정 | primary 15개로 제한하고 BH 적용, 경제성은 Holm, secondary는 별도 family이며 탐색 전용 |
| optional stopping | 세션 수를 사전에 고정, validation을 본 뒤 추가 금지, 무효 세션 교체는 품질 보고서만으로 결정 |
| 거래비용 과소평가 | 체결 가능 VWAP, 수수료 양쪽 적용, 판정은 가장 비싼 수수료, 지연 1000 ms·0.01 BTC·+2 bp 강건성, 체결 불가와 강제 청산을 포함, maker/rebate 가정 없음 |
| drift를 signal로 착각 | long-only는 상승장에서 이익이 난다. matched random entry 대비 excess(H3)를 필수 기준으로 둔다 |
| 시간대·국면 | 시작 시각 교대(주간/야간), 세션별 결과 보고, 결론 범위를 KRW-BTC와 수집 기간으로 한정 |
| 시계·대기 모드 | clock monitor, stop-on-clock-unstable, 수집 전 절전 해제 체크, 무효 세션 교체 |

## 13. v0.4와의 비교 (기술적 비교만)

| 항목 | v0.4 | v0.5 |
|---|---|---|
| horizon | 1, 5, 10, 30 s | 60, 120, 300 s |
| 검정 수 | 116 (단일 family) | primary 15 + secondary 51 (분리) |
| 전략 | top/bottom quintile trigger, buy/sell round trip | long/cash 순차 전략 S1 + random-entry benchmark, overlay S2 (secondary) |
| 세션 | 1 × 6 h, 세션 내부 60/20/20 | dev 4 × 12 h (75/25) + 동결 후 test 2 × 12 h |
| embargo | 300 s | 600 s |
| 지연 | 0/100/250 ms | 0/250/1000 ms |
| 수수료 | 5/15/25 bp | 0(진단)/5/10/15/25 bp, 손익분기 수수료 보고 |
| 다중 검정 | BH 116 | BH(primary), BH(secondary), Holm(경제성) |
| 증거 상한 | 세션 1개로 최대 RESEARCH_MORE | dev ≥ 2 + test ≥ 1, 서로 다른 날짜 ≥ 3 |

두 study의 결과를 합쳐 하나로 검정하지 않는다. 비교는 표와 서술로만 한다. 예: horizon별 gross/spread 비의 변화.

## 14. 범위 밖

실제 주문, 계좌 연결, private API, 자동매매, Paper Trading, maker 전략, 다른 종목, 레버리지, 공매도.

## 15. 고정 절차

1. 사용자가 이 초안을 검토하고 16절의 결정 사항을 확정한다.
2. 확정본을 `docs/research_v05_preregistration.md`와 `configs/research_v05.toml`로 만들고 SHA-256을 기록한다(commit은 사용자 승인 후).
3. 이후 문서나 설정을 바꾸면 새 study다. 예외는 10절의 `account_fee_bps` 입력뿐이다.

## 16. 고정 전 결정 사항 (사용자)

1. **수집 비용 승인:** 3절의 사전 기대(판정 수수료에서 REJECT 가능성 높음)를 알고도 약 86 h(pilot 2 h + 6 × 12 h)를 수집할지.
2. **h300 검정력:** dev 세션 4 × 12 h(현재안)로 할지, 6개 또는 24 h 세션으로 늘릴지.
3. **primary family 구성:** 현재 5 signal로 둘지. 평활 feature를 primary로 올리면 검정 수가 늘어난다.
4. **long/cash 진입 문턱:** train q80(현재안)로 둘지 q90으로 할지. 하나만 선택한다. 둘 다 쓰면 검정 수가 2배가 된다.

---

## 부록 A. config 초안 (`configs/research_v05.toml` 예정, 아직 파일 생성 안 함)

```toml
[study]
name = "moneylab-v0.5-upbit-krw-btc-long-horizon"
version = 1
market = "KRW-BTC"
preregistration = "docs/research_v05_preregistration.md"
provenance_required = "real"
nominal_session_seconds = 43200        # 12 h
min_session_share = 0.90
dev_sessions = 4
test_sessions = 2
min_dev_sessions = 2
min_test_sessions = 1
min_distinct_dates = 3
excluded_sessions = ["session_20261009T2206KST"]   # v0.4: never read

[sampling]
grid_seconds = 1.0
time_axis = "received"
warmup_seconds = 5.0
stale_book_seconds = 1.0
gap_seconds = 10.0
max_lookback_seconds = 300

[labels]
horizons_seconds = [60, 120, 300]
sizes_btc = [0.001, 0.01]
delays_ms = [0, 250, 1000]
max_unfillable_share = 0.01

[split]
dev_train = 0.75
dev_validation = 0.25
embargo_seconds = 600
test_after_freeze = true

[strategy]
long_cash_entry_quantile = 0.80       # d*x >= train q80
overlay_exit_quantile = 0.20          # secondary S2
random_entry_draws = 1000
random_entry_seed = 20261010

[costs]
fee_bps_scenarios = [0.0, 5.0, 10.0, 15.0, 25.0]   # 0 = diagnostic only
# account_fee_bps =                   # set only from an official source (source + date recorded)
decision_size_btc = 0.001
decision_delay_ms = 0

[stats]
quantiles = 5
ci_level = 0.95
bootstrap = "stationary_session_stratified"
bootstrap_resamples = 1000
bootstrap_seed = 20261010
block_seconds_min = 120
block_horizon_multiple = 5
trade_block_mean = 10
hac_extra_lag_seconds = 60
fdr_alpha = 0.05                       # BH within primary; BH within secondary separately
economic_correction = "holm"
economic_alpha_one_sided = 0.05
ic_within_session = true

[decision]
min_valid_share = 0.90
min_quantile_monotonicity = 0.9
min_gross_to_cost = 1.5
robust_delay_ms = 1000
robust_size_btc = 0.01
robust_fee_buffer_bps = 2.0
min_nonoverlapping_trades = 100
min_session_positive_share = 0.75
min_evidence_trades = 30
max_missing_rate = 0.5

[clock]
warn_ms = 100.0
unstable_ms = 250.0
unstable_seconds = 600.0
unstable_min_measurements = 3
stale_seconds = 1800.0

[features]
primary = ["depth_imbalance_5bp", "depth_imbalance_10bp", "obi_1", "book_slope", "imbalance_composite"]
secondary = [
  "obi_5", "obi_10", "obi_30", "microprice_dev_bps",
  "depth_imbalance_5bp_avg60", "obi_1_avg60",
  "spread_bps", "liquidity_concentration", "bid_depth_30", "ask_depth_30", "realized_vol_300s",
  "signed_volume_60s", "signed_volume_300s", "trade_flow_imbalance_60s", "trade_flow_imbalance_300s",
  "return_60s", "return_300s",
]
state = ["mid_price", "spread", "microprice"]
```

## 부록 B. 구현 순서 (고정 후, 각 단계는 사용자 승인 후 진행)

1. **config/study 일반화:** study 버전별 config 로더, v0.4 경로·동작 불변(회귀 테스트).
2. **feature:** 60/300 s 체결 창, avg60 평활, composite. lookback ≤ 300 s, look-ahead 불변 테스트.
3. **label:** horizon 60/120/300, 지연 1000 ms, 체결 불가 비율 집계.
4. **multi-session build:** 세션 유효성 검사, dev 세션 내부 75/25 split, embargo 600 s, pooled train fit, test 세션 전체 잠금, `excluded_sessions` 강제.
5. **전략 시뮬레이터:** S1 순차 long/cash(강제 청산 포함), B1 matched random entry, B2, S2. 순수 함수는 `analytics/`에 둔다.
6. **통계:** 세션 내 IC 가중 평균, 세션 층화 bootstrap, 거래 단위 bootstrap, Holm, 손익분기 수수료.
7. **동결 manifest와 research-final:** 동결 시각 이후 수집된 test 세션만 허용, 1회 개봉.
8. **leakage/선택 편향 테스트:** synthetic fixture로 오프라인 검증 후 pilot P0 dry-run.
9. **수집과 분석:** D1–D4 수집 → build/stats → 동결 → T1–T2 수집 → research-final.
