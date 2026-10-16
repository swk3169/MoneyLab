# BT-2b-4 보고 지표 정의 (bt-metrics/2, moneylab.backtest.report/2, bt-seed/1)

모든 결과는 **SYNTHETIC / NOT_EVIDENCE**이고 기술 통계다. p값과 판정(verdict)은 계산하지 않는다.
bt-metrics/1의 정의(`docs/backtest_bt2b3_metrics.md`)는 그대로이고, /2는 그 위에 아래 세 절을 더한다.
구현: `src/moneylab/backtest/cost_analysis.py`, `round_trips.py`, `yearly.py`, 조립은 `report.py`.
기존 run(`result.json`, `result_sha256`)과 BT-1~BT-2b-3 모듈은 바꾸지 않는다. 보고서 계층에서 원장만 읽는다.

## 1. 기호

| 기호 | 정의 |
|---|---|
| r_i, n, T_d | bt-metrics/1과 같다 (일별 순 로그수익률, 개수, 첫·마지막 기준 시각 사이 달력 일수) |
| R | 왕복 수 (아래 4절) |
| P_entry, P_exit | 왕복의 매수·매도 leg 기준가 (`TradeRow.ref_price`) |
| κ, ι | run의 `slippage_bps`, `impact_bps` (편도) |
| c_b, c_s | 매수·매도 1건의 로그 자산 배수 (`benchmarks.leg_cost_logs`). inclusive c_b = ln((1−f)(1−κ−ι)), on_top c_b = ln((1−κ−ι)/(1+f)), c_s = ln((1−κ−ι)(1−f)) |
| K | ln(1 − κ − ι) |

## 2. 비용 분석 (`cost_analysis`, 기준: 로그)

연구 모드에서는 현금으로 시작해 가상 청산으로 현금으로 끝나고, 자산은 보유 중 가격 변화와 leg 비용으로만 바뀐다. 그래서

```text
Σr = G + R (c_b + c_s),     G = Σ_왕복 ln(P_exit / P_entry)
```

이 정확히 성립한다. 각 leg를 기준가로 평가하므로 체결 시각(대체 체결, virtual_fallback, E3, DIAG)과 무관하다.
보고서는 |Σr − (G − cost_log)| ≤ 1e-9 · max(1, |Σr|)를 확인한 뒤에만 아래 값을 낸다. 어긋나면 모든 값이
`decomposition_mismatch`, 마지막에 포지션이 열려 있으면 `open_position_at_end`인 null이다.

| 항목 | 식 | 단위·의미 | null 사유 |
|---|---|---|---|
| gross_log_return | G | 비용 전 로그수익 (수수료·κ·ι가 0이면 net과 같다) | – |
| cost_log | −R (c_b + c_s) ≥ 0 | 비용으로 잃은 로그수익 | – |
| net_log_return | Σr | 원장 값 | – |
| gross_to_cost_ratio | G / cost_log | 비용 대비 비용 전 수익 (로그 기준) | cost_log = 0: `zero_cost`, G ≤ 0: `non_positive_gross` |
| annual_cost_log (주) | cost_log · 365 / T_d | 연간 로그 비용 (log/년) | T_d ≤ 0: `non_positive_period` |
| annual_cost_fraction (보조) | 1 − exp(−annual_cost_log) | 비용 때문에 1년에 잃는 자산 비율 (0–1) | 같음 |
| annual_round_trips | R · 365 / T_d | 연간 왕복 횟수 | 같음 |
| costs_krw (보조) | `metrics.cost_totals` (fee, slippage, impact, total) | KRW 합계 | – |

### 2.1 손익분기 편도 수수료 f*

정의: 매수·매도에 같은 편도 수수료 f를 둘 때 m_s = Σr / n = 0이 되는 f. κ, ι, fee_basis, 신호, 체결 시각과 가격은
run의 값으로 고정한다(신호는 비용에 의존하지 않는다). 자본은 run의 C = 1,000,000 KRW(ι(C) 포함)뿐이고, 규모별 민감도는 범위 밖이다.

수수료 0일 때 왕복당 순 로그수익 A = (G + 2RK) / R로 두면

```text
inclusive: Σr = G + 2RK + 2R ln(1 − f) = 0          ⇒  f* = 1 − exp(−A / 2)
on_top:    Σr = G + 2RK + R ln(1 − f) − R ln(1 + f) = 0
           ⇒ ln((1 − f)/(1 + f)) = −A                 ⇒  f* = tanh(A / 2)
```

A ≥ 0이면 f* ∈ [0, 1). null 사유: R = 0 `no_round_trips`, A < 0 `net_negative_at_zero_fee`(수수료 0이어도 손실),
분해 불일치 `decomposition_mismatch`, 열린 포지션 `open_position_at_end`. 보고값: `value`(비율), `value_bps`,
`zero_fee_round_trip_log_return`(A), 고정 조건(fee_basis, κ, ι, 자본, 왕복 수). 테스트는 수수료를 f*로 두고 같은 bar로
다시 시뮬레이션해 |Σr| < 1e-9를 확인한다(inclusive, on_top).

## 3. 연도별 순수익 (`yearly`)

- r_i는 (ref_i, ref_{i+1}] 구간의 변화이고 **구간 끝 ref_{i+1}의 UTC 달력 연도**에 배정한다(초안 8.1 규칙 2).
- **예외 없음:** 기준 시각이 정확히 00:00 UTC인 E2에서는 Y-01-01 00:00에 끝나는 구간(전부 Y−1년 12월 31일)이 Y년으로
  간다. 연도 경계가 직관과 다르게 보일 수 있으며, 보고서는 이런 기준 시각이 있으면 `midnight_reference_times = true`와
  `note`로 표시한다.
- 행: year, n_returns, days_in_year(365/366), sum_log_return, net_return = exp(sum) − 1,
  partial_year = (n_returns < days_in_year), irregular(그 해 안에 간격이 1일이 아닌 구간이 있음).
  예: E0(01:00)의 완전한 해는 Y-01-01 01:00부터 Y-12-31 01:00까지 끝나는 365/366개 수익률이다.
- 양(+) 연도 비율: 전체 연도 기준과 완전한 연도만 기준을 **둘 다** 보고하고 어느 것도 주 지표가 아니다. 합이 0인 해는 양이
  아니다. 연도가 없으면 `no_years`, 완전한 해가 없으면 `no_full_years`. 초안 E-c 기준과 비교하지 않는다(`verdict: not computed`).

## 4. 왕복, Profit Factor, 승률 (`round_trips`)

현재 엔진의 성질(`portfolio.simulate`, `costs`, `ledger.verify`): 매수는 현금 전액, 매도는 수량 전부라 부분 체결이 없고,
leg는 매수·매도가 번갈아 나오며, 한 포지션은 매수 1개와 매도 1개다. 마지막 단계는 열린 포지션을 판다
(`TradeRow.virtual = True`, `fill_kind`는 primary 또는 virtual_fallback).

| 항목 | 정의 |
|---|---|
| 왕복 | 매수 leg와 바로 다음 매도 leg. 구조가 다르면 `RoundTripError`(보고서 거부) |
| 가상 청산 | 매도 leg의 `virtual == True`. 행마다 `virtual_close`, `exit_fill_kind` 표시 |
| 순손익 (KRW, 주) | 매도 `cash_after` − 매수 `cash_before`. 두 leg의 수수료·슬리피지·충격이 모두 들어 있다 |
| 결과 | win > 0, loss < 0, zero = 0 (Decimal 정확 비교) |
| 승률 | wins / 그 view의 왕복 수 (zero 포함) |
| Profit Factor | Σ wins / \|Σ losses\| (Decimal로 계산, float로 보고) |
| null | 왕복 없음 `no_round_trips`, 손실 없음 `no_losing_round_trips`, 이익·손실 모두 없음 `no_profit_and_no_loss`. Infinity는 쓰지 않는다 |
| view | `completed_only`(가상 청산 왕복 제외), `including_virtual_close` |

불변식(정확, Decimal 100자리 문맥): 각 매수는 직전 매도의 현금에서 시작하고(`ledger.verify`) 그 사이 현금 변화가 없으므로

```text
Σ net_pnl (including_virtual_close) = 최종 자산 − 초기 현금
Σ net_pnl (completed_only)          = 최종 자산 − 초기 현금 − Σ net_pnl (가상 청산 왕복)
```

마지막에 포지션이 열려 있으면(현재 엔진에서는 평가 가격이 전혀 없을 때만) 불변식을 적용하지 않고 `open_position_at_end`.

## 5. 보고서 /2와 버전 정책

- /2 = /1 내용 + `cost_analysis`, `yearly`, `round_trips`, `"verdict": "not computed"`. `schema`는
  `moneylab.backtest.report/2`, `metrics_definition.version`은 `bt-metrics/2`, seed는 `bt-seed/1` 그대로. 직렬화 규칙은 /1과 같다.
- **legacy /1 (V2′):** /1 계산 코드는 유지하지 않고 /1을 /2 계산기로 재계산하지 않는다. `verify_run`은 run을 그 커밋에
  고정하므로 새 코드로는 어차피 완전 검증이 불가능하다. `check_report`는 /1에 대해 재계산 없는 files, meta, versions,
  run_refs만 검사하고, run_verify와 content는 `LEGACY_REQUIRES_COMMIT_09504cd`(ok = None)로 표시한다. 전체 결과는
  ok = false, `status = LEGACY_REQUIRES_COMMIT_09504cd`, CLI 종료 코드 1. 완전 검증은 커밋
  `09504cd9dacd37cc18ac5a65ecf69fb5f5661286`에서 한다. 무결성 검사가 실패한 /1 보고서는 `FAILED`(손상)로 구분된다.
- 모르는 스키마·정의·seed 알고리즘은 거부한다. /1 스키마에 /2 정의가 붙은 것처럼 맞지 않는 조합도 거부한다.

## 6. 범위 밖

계좌 모드, walk-forward·구간 분할·Vault, Deflated Sharpe, bootstrap·ΔSR 신뢰구간, p값·H1·H2·Holm, 실데이터,
주문 연동, B1 변경, 규모별 f* 민감도.
