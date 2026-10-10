# MoneyLab v0.4 사전등록: Upbit KRW-BTC 단기 microstructure predictive edge

상태: **사전등록(pre-registration).** 이 문서와 `configs/research_v04.toml`은 연구 데이터의 label·통계를
보기 전에 고정한다. 두 파일의 SHA-256은 모든 run manifest에 기록되고, `research-final`은 해시가 다르면
test split을 열지 않는다. 내용을 바꾸면 새 study(새 해시)이며, 기존 결과와 섞지 않는다.

이 연구는 **읽기 전용**이다. 실제 주문, API key, JWT, private endpoint, 계좌 연결, 자동매매는 없다.

## 1. 질문

> t 시점의 orderbook/trade 상태가 t+1s, 5s, 10s, 30s의 가격 움직임을 **거래비용을 초과할 만큼** 예측하는가?

gross 예측력만으로는 채택하지 않는다. 판단은 executable label(체결 가능한 가격, 수수료 포함) 기준 net edge로 한다.

## 2. 데이터

| 항목 | 값 |
|---|---|
| 시장 | Upbit KRW-BTC (현물, 공매도 불가) |
| 소스 | 공개 WebSocket `wss://api.upbit.com/websocket/v1`, orderbook(30 units) + trade |
| provenance | `real`만 증거. `fixture`/synthetic 결과는 `NOT_EVIDENCE`이며 PAPER_CANDIDATE가 될 수 없다 |
| 세션 | 첫 연구 세션은 6시간. 6시간 미만(`nominal_session_seconds`의 90% 미만)은 `INSUFFICIENT_EVIDENCE` |
| raw | `data/raw/upbit/research/<session_id>/KRW-BTC/` (recorder만 씀, 불변). 연구 코드는 읽기만 한다 |
| 제외 데이터 | `data/raw/upbit/recordings/KRW-BTC` (시계 offset 약 1.2s가 섞인 smoke 데이터) |

확인되지 않은 사실(문서 미기재, 가정하지 않는다):
- 메시지 `timestamp`가 서버 송신 시각인지 이벤트 시각인지. → 시간 축으로 쓰지 않는다(3절).
- trade `ask_bid`가 공격자(taker) 방향인지. → feature 이름은 "Upbit ask_bid 부호"를 뜻한다.
- REALTIME orderbook이 항상 전체 30 units인지(delta가 아닌지). → 품질 보고서에서 units 수를 센다.
- KRW-BTC 호가 단위(WS에 없음, 관측 1,000 KRW). 계정 수수료(공식 페이지 미확인).

## 3. 시간 축과 sampling

- 시간 축: **로컬 수신 시각**(`received_timestamp`, NTP 동기화된 시계). 행 t는 `received_timestamp <= t`인 이벤트만 쓴다.
  도착 순서상 앞선 이벤트보다 수신 시각이 작게 찍힌 이벤트(시계 역행)는 앞선 이벤트의 시각까지 사용 불가로 본다
  (유효 시각 = 도착 순서 누적 최대 수신 시각).
- `received_timestamp - exchange_timestamp`는 **품질 지표**로만 기록하고 feature로 쓰지 않는다.
- sampling: **1초 wall-clock grid**. t_k = ceil(첫 이벤트 수신 시각) + k초.
  event-time sampling은 바쁜 구간을 과대대표하고 100ms 주기의 거의 같은 상태를 반복하므로 쓰지 않는다.

## 4. 품질 flag와 제외 규칙

이벤트 flag (adapter가 붙이고, 삭제하지 않는다):

| flag | 의미 |
|---|---|
| `warmup` | SNAPSHOT 메시지, 또는 연결의 첫 REALTIME book 이후 `warmup_seconds`(5s) 이내 |
| `stale_book` | 같은 연결의 직전 book보다 `stale_book_seconds`(1s) 넘게 늦게 도착한 book |
| `crossed_book` / `locked_book` | best_bid > best_ask / best_bid == best_ask |
| `timestamp_reverse` | 같은 stream의 거래소 timestamp 또는 수신 시각이 직전보다 작음 |
| `sequence_gap` | `local_sequence`가 연속이 아님 |
| `duplicate` | recorder가 표시한 중복 (상태에 반영하지 않음) |
| `reconnect_boundary` | 연결/끊김/실패 이벤트와 연결 후 첫 시장 이벤트 |

행(row) 제외 사유 (여러 개 가능, 사유별로 집계):

| 사유 | 조건 | 성격 |
|---|---|---|
| `no_book` | 아직 book 없음 | 불연속 |
| `gap` | 끊김/실패 이후 다음 연결 전, 또는 book_age > `gap_seconds`(10s), 또는 `sequence_gap` | 불연속 |
| `warmup` | 연결 후 첫 REALTIME book + 5s 이전, 또는 as-of book이 SNAPSHOT | 불연속 |
| `stale_book` | book_age > 1s | 행만 제외 |
| `crossed_book` / `locked_book` | as-of book이 crossed/locked | 행만 제외 |
| `timestamp_reverse` | as-of book에 timestamp_reverse flag | 행만 제외 |

- 불연속 행이 lookback 창에 있으면 그 feature는 NaN, label 창에 있으면 label은 NaN.
- 빈 값은 채우지 않는다(forward-fill 없음). missing은 집계·보고한다.

## 5. Feature (t 시점, 단위)

기호: book bid (p^b_i, q^b_i), ask (p^a_i, q^a_i), i=1..30 best-first, 가격 KRW, 수량 BTC.
m = mid. trade j: 부호 s_j = +1(ask_bid=BID), -1(ASK), 수량 v_j. trade 창 (t-w, t]는 수신 시각 기준, REALTIME·비중복만.

| feature | 공식 | 단위 | lookback |
|---|---|---|---|
| mid_price (state) | (p^b_1 + p^a_1)/2 | KRW | 0 |
| spread (state) | p^a_1 - p^b_1 | KRW | 0 |
| microprice (state) | (p^b_1 q^a_1 + p^a_1 q^b_1)/(q^b_1 + q^a_1) | KRW | 0 |
| spread_bps | 1e4 · spread / m | bp | 0 |
| microprice_dev_bps | 1e4 · (microprice - m) / m | bp | 0 |
| obi_k (k=1,5,10,30) | (Σ_{i≤k} q^b_i - Σ_{i≤k} q^a_i)/(Σ q^b + Σ q^a) | [-1,1] | 0 |
| bid_depth_k, ask_depth_k (k=10,30) | Σ_{i≤k} q_i | BTC | 0 |
| depth_imbalance_δbp (δ=5,10) | D^b=Σ{q^b_i : p^b_i ≥ m(1-δ/1e4)}, D^a=Σ{q^a_i : p^a_i ≤ m(1+δ/1e4)}, (D^b-D^a)/(D^b+D^a) | [-1,1] | 0 |
| signed_volume_ws (w=1,5,30) | Σ_{j∈(t-w,t]} s_j v_j (trade 없으면 0) | BTC | w |
| trade_flow_imbalance_ws (w=1,5,30) | Σ s_j v_j / Σ v_j (trade 없으면 **NaN**) | [-1,1] | w |
| buy_intensity / sell_intensity | (t-5s,t]의 BID / ASK trade 건수 / 5 | 건/s | 5 |
| return_ws (w=1,5,30,60) | 1e4 · ln(m_t / m_{t-w}) | bp | w |
| realized_vol_ws (w=30,60,300) | sqrt(Σ_{k=t-w+1..t} (1e4 · ln(m_k/m_{k-1}))²), 1초 grid | bp | w |
| liquidity_concentration | (Σ_{i≤5} q^b_i + Σ_{i≤5} q^a_i)/(Σ_{i≤30} q^b_i + Σ_{i≤30} q^a_i) | [0,1] | 0 |
| book_slope | ln(slope^b / slope^a), slope^x = Σ_{i≤10} q^x_i / (1e4·|m - p^x_10|/m) | ln-ratio | 0 |

검정 대상은 config의 `signals` 29개, horizon 4개 = 116개 조합. 가격 수준(state)은 검정하지 않는다.
level 수가 k보다 적으면 해당 feature는 NaN.

## 6. Label

horizon h ∈ {1,5,10,30}s, wall-clock(next-event 아님). 미래 가격 = t+h 시점의 as-of book(수신 시각 ≤ t+h).

- `future_mid_return_h = ln(m_{t+h}/m_t)`
- `future_mid_move_bps_h = 1e4 · (m_{t+h}/m_t - 1)`
- 실행 가능 수익률 (크기 Q ∈ {0.001, 0.01} BTC, 지연 Δ ∈ {0,100,250}ms, **수수료 전**):
  - `exec_buy_bps = 1e4 · (VWAP_bid(t+h+Δ, Q) / VWAP_ask(t+Δ, Q) - 1)`  (매수 후 매도)
  - `exec_sell_bps = 1e4 · (VWAP_bid(t+Δ, Q) / VWAP_ask(t+h+Δ, Q) - 1)` (보유 재고 매도 후 재매수; 현물이라 공매도 아님)
  - 30 units 안에서 Q를 채울 수 없으면 NaN.
- 수수료 f(편도) 적용: `net = 1e4 · ((1 + exec/1e4) · (1-f)/(1+f) - 1)` (`analytics/spot_costs.py`).

## 7. Split

시간순, 무작위 분할 없음. 세션 길이 D, 시작 T0:

| 구간 | 범위 |
|---|---|
| train | [T0, T0+0.6D] |
| embargo | 300s |
| validation | [T0+0.6D+300, T0+0.8D] |
| embargo | 300s |
| test | [T0+0.8D+300, T0+D] |

- **purge**: 행 t의 label 창 끝(t+h+Δmax)이 자기 구간 끝을 넘으면 그 horizon에서 제외.
- feature lookback 창은 이전 구간의 끝을 넘어가지 않는다(넘어가면 NaN). embargo 300s ≥ 최대 lookback 300s.
- quintile 경계, 방향(IC 부호), median은 **train에서만** 정하고 validation/test에 그대로 쓴다.
- **test lock**: test 행은 별도 파일(`locked/test.jsonl.gz`, 해시 기록)에만 있다. `research-stats`/leaderboard는
  읽을 수 없다. `research-final`만, 사전등록·config 해시가 같고 validation leaderboard가 완료된 경우에, **정확히 한 번** 연다.
  접근 횟수는 manifest에 기록되고 두 번째 실행은 거부된다.
- 여러 날짜가 쌓이면 날짜 단위 walk-forward로 확장한다.

## 8. 통계 (feature × horizon마다, train과 validation 각각)

N, missing rate, mean/std, Pearson, Spearman IC, quintile 조건부 미래 수익률, top-bottom 차이,
방향 적중률(움직임 0과 feature=median 제외), stationary block bootstrap CI(평균 블록 길이 max(60s, 5h),
1000회, seed 고정, 순위는 전체 표본에서 고정), Newey-West HAC(lag = h + 60s), 116개 조합 전체에 Benjamini-Hochberg FDR.
중첩 label 때문에 유효 N(≈N/h)도 보고한다. random shuffle은 쓰지 않는다.
표본이 너무 작으면 추정치를 내지 않는다(NaN, INCONCLUSIVE): bootstrap은 n ≥ 5 × 평균 블록 길이, HAC는 n ≥ 2 × (lag + 1)일 때만 계산한다.

## 9. 비용과 edge

- trigger: train에서 정한 방향 d = sign(IC_train). d·feature가 train 최상위 quintile이면 진입
  (d·x가 위쪽 → 매수 round trip, 아래쪽 quintile → 매도 round trip).
- gross edge = trigger 행의 방향 부호 × `future_mid_move_bps` 평균.
- net edge = trigger 행의 executable label에 수수료를 적용한 평균 (**직접 계산**).
- estimated cost = gross - net (spread + depth slippage + 지연 중 움직임 + 수수료).
- 수수료: config `fee_bps_scenarios` = 5/15/25bp. `account_fee_bps`가 확정되기 전에는 **가장 비싼 시나리오**로 판정.
- 지연 민감도 0/100/250ms, 크기 0.001/0.01 BTC.
- maker 전략은 범위 밖(L2 스냅샷으로 대기열·체결 검증 불가).

## 10. 판정 규칙 (사전 고정)

**PAPER_CANDIDATE** (모두 충족):
1. provenance=real, 무결성 OK, 유효 label 비율 ≥ 0.90
2. validation IC 부호 = train IC 부호, IC bootstrap 95% CI가 0 미포함, BH q < 0.05
3. quintile 단조성(구간 순서와 평균의 Spearman, 방향 보정) ≥ 0.9 (train, validation 모두)
4. 판정 수수료 기준 net edge 95% CI 하한 > 0, gross ≥ 1.5 × estimated cost
5. Δ=250ms와 수수료+2bp에서도 net > 0
6. validation 비중첩 trigger ≥ 200
7. test(한 번만): net > 0, IC 부호 동일
8. 서로 다른 날짜의 세션 ≥ 3 (walk-forward)

**evidence class** (Phase 1.1에서 보완, 연구 데이터를 보기 전):

| class | 조건 | 판정 |
|---|---|---|
| `INSUFFICIENT_EVIDENCE` | 다음 중 하나: train 방향 없음, IC bootstrap CI 계산 불가, BH q 계산 불가, net/gross edge CI 계산 불가, 비중첩 trigger < `min_evidence_triggers`(30), missing rate > `max_missing_rate`(0.5), 유효 label 비율 < 0.90 | RESEARCH_MORE (`reason=INSUFFICIENT_EVIDENCE`). **REJECT하지 않는다** |
| `NEGATIVE_EVIDENCE` | 표본 충분 **그리고** (validation net edge ≤ 0 **또는** gross < estimated cost) | **REJECT** |
| `POSITIVE_BUT_UNCONFIRMED` | 표본 충분, net > 0, gross ≥ cost. 위 1–8 기준 일부/전부 충족이지만 test 미개봉·실패, 세션 부족, evidence 부족 | RESEARCH_MORE (`reason=POSITIVE_BUT_UNCONFIRMED: ...`) |
| `CONFIRMED` | 1–8 전부, test PASS, provenance=real, 세션 ≥ 3 | PAPER_CANDIDATE |

상한:
- 단일 6시간 세션(세션 수 < 3): 최대 RESEARCH_MORE.
- provenance ≠ real: 최대 RESEARCH_MORE, evidence = `NOT_EVIDENCE`.
- dry-run/짧은 세션: 최대 RESEARCH_MORE, evidence = `DRY_RUN/INSUFFICIENT_EVIDENCE`.
- test 이전(LOCKED): 최대 RESEARCH_MORE.

## 11. 알려진 bias와 대응

| bias | 대응 |
|---|---|
| look-ahead | 수신 시각 as-of, 도착 순서 누적 최대 시각, "t 이후 이벤트 변경 시 feature(t) 불변" 테스트 |
| selection (시간대, 단일 종목) | 수집 시각 기록, 제외 행을 사유별로 집계·보고, 결론 범위를 KRW-BTC·해당 시간대로 한정 |
| data snooping / multiple testing | 이 문서와 config 해시, 116개 조합 고정, BH-FDR |
| overlapping labels | stationary block bootstrap, HAC, 유효 N |
| split 간 leakage | 시간순 + embargo + purge + 구간 내 lookback, train에서만 경계 추정 |
| test 최적화 | test lock, 단 한 번, 접근 기록 |
| synthetic을 real처럼 사용 | provenance 강제, NOT_EVIDENCE, PAPER_CANDIDATE 차단 |
| timestamp 의미 불확실 | 수신 시각 축, recv-ts 차이는 품질 지표만 |
| 품질 임계값 | warmup/stale/gap 임계값은 label·통계를 보기 전에 고정. 6시간 데이터의 book_age 분포는 품질 보고서로만 확인 |
| 로컬 시계 drift | 12절 clock monitor. offset은 품질 metadata로만 기록하고 보정에 쓰지 않는다 |

## 12. 로컬 시계 품질 (Phase 1.1)

- `core/clock_monitor.py`가 `w32tm /stripchart`(읽기 전용, 시스템 시계를 바꾸지 않음)로 offset을 주기적으로 기록한다
  (`clock_monitor.jsonl`, raw 데이터 옆). offset = reference − local (음수: 로컬 시계가 앞섬).
- offset은 **feature·label·timestamp 보정에 쓰지 않는다.** `exchange_timestamp`/`received_timestamp` 원본은 그대로다.
- 분류(config `[clock]`): |offset| > 100ms가 한 번이라도 → `WARNING`. |offset| > 250ms가 **10분 이상, 연속 3회 이상**
  측정에서 지속되거나, 측정 간 250ms 넘는 step → `CLOCK_UNSTABLE`. 성공 측정이 없거나 30분 넘게 없으면 `UNKNOWN`.
- run manifest: `clock_offset_start/end/min/max/median_ms`, `clock_measurements`, `clock_quality_status` (+ drift ppm).
- `CLOCK_UNSTABLE` 세션은 6시간 수집 준비 판정(canary)에서 불합격이다.
