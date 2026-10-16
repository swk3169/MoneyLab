# BT-2b-3 성과지표·벤치마크·보고서 정의 (bt-metrics/1, bt-seed/1)

모든 결과는 **SYNTHETIC / NOT_EVIDENCE**이고 기술 통계다. 유의성 검정, p값, 판정은 계산하지 않는다
(통계 검정은 research 쪽, `docs/backtest_design.md` 14.2절). 구현: `src/moneylab/backtest/performance.py`,
`benchmarks.py`, `report.py`. 기존 BT 모듈(`metrics.py` 포함)은 바꾸지 않았으므로 run의 `result_sha256`은 그대로다.

## 1. 입력

| 기호 | 정의 | 출처 |
|---|---|---|
| E^before_i, E_i | 기준 시각 i의 거래 전·후 자산 (N개 일별 행) | `ledger.DailyRow.equity_before_trade`, `equity` |
| r_i | ln(E^before_{i+1} / E^before_i), i = 0…n−1, n = N − 1. 마지막 날은 가상 청산 뒤 자산 E_{N−1}로 끝난다. 모든 비용 차감 후(net) | `metrics.daily_log_returns` |
| p_i | i일 동안 보유한 포지션 (`daily[i].position`, 거래 후) | `benchmarks.ledger_positions` |
| m_i | ln(P_{i+1} / P_i), P = 기준 시각 평가 가격 | `benchmarks.market_log_returns` |
| T_d | 첫·마지막 기준 시각 사이 달력 일수 (초 / 86,400) | `report.compute_body` |
| c_b, c_s | 거래 1건의 로그 자산 배수. 매수 inclusive ln((1−f_b)(1−κ−ι)), 매수 on_top ln((1−κ−ι)/(1+f_b)), 매도 ln((1−κ−ι)(1−f_s)) | `benchmarks.leg_cost_logs` (`costs.CostModel.buy/sell`에서 유도, 테스트로 일치 확인) |

연율화 365일(`research/v06/procedures.ANNUALIZATION_DAYS`와 같은 값), 무위험수익률 0(초안 7절: 현금 수익률 0).

## 2. 지표 (bt-metrics/1)

| 지표 | 식 | 값이 없을 때 (`{"value": null, "reason": …}`, 0으로 쓰지 않음) |
|---|---|---|
| total_return | exp(Σr) − 1. 원장의 최종/초기 자산 − 1(`total_return_ledger`, Decimal)과 상대 1e-12 이내가 아니면 보고서를 만들지 않음 | – |
| cagr | exp(Σr · 365 / T_d) − 1. `short_period` = T_d < 365 | T_d ≤ 0 또는 비유한: `non_positive_period` |
| volatility | 표본 sd(r) · √365, sd = √(Σ(r − r̄)² / (n − 1)) | n < 2: `fewer_than_2_returns` |
| sharpe_log (주) | r̄ / sd(r) · √365 | n < 2, 또는 sd = 0 (sd ≤ 1e-12 · max\|r\| 포함, 상수 수열의 반올림 잡음): `zero_sample_sd` |
| sharpe_simple (보조) | R = e^r − 1에 같은 식 | 같음 |
| sortino | r̄ / DD · √365, DD = √(Σ min(r, 0)² / n), **분모는 전체 관측 수 n** | n = 0: `no_returns`, DD = 0: `no_downside` |
| mdd (P, 비교용 주 지표) | 1 − exp(−max(peak − level)), level = r의 누적합(0에서 시작) | – |
| mdd_ledger_after_trade (BT-1) | [초기 자산, 각 기준 시각의 거래 후 자산]의 최대 낙폭 비율 (`metrics.max_drawdown` → `analytics.metrics.max_drawdown`) | – |
| calmar | cagr / mdd(P) | cagr 없음: `cagr_unavailable`, mdd = 0: `zero_drawdown` |
| exposure | Σp / n | n = 0: `no_returns` |
| turnover (주) | Σ_leg (q · P_ref) / mean(일별 거래 후 자산 E_i). `period`와 `annualized` (× 365 / T_d) | T_d ≤ 0이면 연율화 값 없음 |
| turnover legs (보조) | Σ_leg (q · P_ref / 그 leg 직전 자산) × 365 / T_d. 연구 모드에서는 leg당 1에 가깝다(정확히 1은 아님) | 같음 |

- 회전율의 leg에는 매수·매도, 가상 청산, 대체 체결이 모두 포함된다. q · P_ref는 체결 수량의 비용 전 평가액이다.
- 비유한 입력(NaN, ±Inf), 0 이하 자산은 `MetricError`로 거부한다. 보고서 JSON은 `allow_nan=False`로 쓴다.
- 표시: `irregular_spacing`(기준 시각 간격이 1일이 아닌 곳이 있거나 n ≠ T_d), `no_trades`, `short_period`.

### 2.1 MDD 두 정의의 차이

| 정의 | 곡선의 점 | 위치 |
|---|---|---|
| P | 초기 자산(= E^before_0), E^before_1, …, E^before_{N−1}, E_{N−1} (거래 **전** 자산, 마지막은 청산 후) | `performance.max_drawdown_log` = `research/v06/procedures.max_drawdown` |
| L | 초기 자산, E_0, E_1, …, E_{N−1} (거래 **후** 자산) | BT-1 `backtest.metrics.max_drawdown` |

거래가 없는 날은 E^before_i = E_i라 두 곡선이 같고, **거래일에만 다르다**. L은 비용을 낸 직후의 낮은 점을, P는 거래 직전의
높은 점을 포함하므로 어느 쪽이 항상 크지 않다. 벤치마크는 수익률 시계열로만 존재해 P로만 계산할 수 있으므로, 전략과 모든
벤치마크의 비교는 P로 한다. L은 연속성을 위해 `mdd_ledger_after_trade`로 따로 보고한다. 거래가 없거나 비용이 0이면 같다.

## 3. 벤치마크 (초안 8절)

포지션 수열 p의 수익률: r_i = p_i m_i + (포지션이 열린 날 c_b) + (닫힌 날 c_s) + (마지막 날 보유 중이면 c_s, 가상 청산).
`procedures.segment_returns`와 같은 규약이다(`benchmarks.position_returns`).

| 벤치마크 | 정의 |
|---|---|
| B1 matched random exposure | 전략 p의 보유 구간 길이 목록과 내부 현금 구간 목록을 각각 섞고, 앞뒤 현금 합을 무작위로 나눠 번갈아 배치. K개. 난수 소비 순서는 `procedures.b1_positions`와 같다: shuffle(보유 구간) → shuffle(내부 현금) → randint(0, 앞 + 뒤). research는 런타임에 import하지 않고 테스트에서만 대조 |
| B2 buy-and-hold | 모든 날 p = 1. 진입 c_b, 청산 c_s 각 1회 |
| B3 현금 | r = 0 |
| B4 (REPORT_ONLY) | w = 전략 exposure. W2(k) = exp(Σ_{i<k} r2_i), **W4(k) = (1 − w) + w · W2(k)**, r4_k = ln(W4(k+1) / W4(k)). 시점 0에 한 번 배분하고 리밸런싱하지 않음. 현금 수익률 0, 비용은 B2 부분에만, 마지막 기준 시각에 B2 부분만 청산 |

보고: 각 벤치마크의 2절 지표(MDD는 P), Σr·CAGR·MDD의 B2 대비 차이, B1의 일평균 로그수익률 m^k의 평균과
5/50/95 % 분위수, m_s − mean(m^B1). 분위수는 선형 보간: 정렬 x, h = (K − 1)q, x_(⌊h⌋) + (h − ⌊h⌋)(x_(⌊h⌋+1) − x_(⌊h⌋))
(`statistics.quantiles(method="inclusive")`와 같은 규칙). **p값은 계산하지 않는다.**

### 3.1 정렬 (alignment)

원장 무결성(`verify_run`, 재계산 일치)과 별도로, 벤치마크 비교는 원장 수익률이 위 포지션 수열 수익률과 같을 때만 만든다
(`benchmarks.alignment`). 검사: 기준 시각 간격 1일, 모든 체결 시각이 기준 시각과 같음, 체결 기준가 = 그 시각 평가 가격,
항등식 |r_i − (p_i m_i + c_i)| ≤ 1e-9. 하나라도 깨지면(예: 기준 시각 뒤에 체결된 대체 체결, 빠진 날, 시가 체결인 DIAG)
`benchmarks = {"status": "not_aligned", "reasons": [...]}`이고 비교 수치를 만들지 않는다(0이나 빈 값으로 쓰지 않음). 전략 지표는 유지한다.

## 4. Seed (bt-seed/1)

```text
payload = json.dumps(["moneylab.bt_seed", 1, str(seed), *labels], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
derived = int.from_bytes(sha256(payload).digest()[:8], "big")      # 64-bit unsigned
rng     = random.Random(derived)
```

- seed: 정수, 0 ≤ seed < 2**64. CLI `--seed`는 필수이고 기본값이 없다.
- labels: `["B1", rule, scenario]`. `result_sha256`은 넣지 않는다.
- `research/stats.derived_seed`(crc32 of `"|".join(parts)`)와 다른 규칙이다. JSON 배열 인코딩이라 라벨 구분자 충돌이 없다.
- 고정 테스트 벡터(외부 `sha256sum`으로 계산): seed 7, labels B1/sma20/E0 → digest `c9080007df1d7dea…`, derived = 0xc9080007df1d7dea.
- 규칙을 바꾸면 `bt-seed/2`로 올리고, 기존 보고서는 기록된 알고리즘으로만 재검증한다. 모르는 알고리즘은 거부한다.
- Python은 `random()` 결과열만 버전 간 재현을 보장한다. `shuffle`·`randint`는 보장되지 않으므로 B1 배치는 같은 Python 버전에서만
  재현이 보장된다. `report_meta.json`에 Python 버전을 기록한다.

## 5. 보고서

`moneylab backtest-report <run_dir> --seed S [--b1-draws 999] [--out <root>-fixture]` →
`<root>/<run_dir_name>-report-<UTC>/` (기본 루트 `data/processed/backtest_reports-fixture`).

| 파일 | 내용 |
|---|---|
| report.json | 스키마 `moneylab.backtest.report/1`, 라벨, run 참조(run 이름, manifest SHA-256, result_sha256, inputs, settings, config), 지표 정의(버전, 365, rf 0, 식, MDD 설명), seed 설정, 비용 로그, 지표, 정렬, 벤치마크, `"p_values": "not computed"`. `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` + LF 1개, UTF-8. 시각·code_state·Python 버전 없음 → 같은 run·정의·seed면 바이트가 같다 |
| report.md | report.json에서만 생성(결정적) |
| report_meta.json | created_utc, code_state, Python 버전, report.json의 SHA-256 |
| SHA256SUMS.txt | `<sha256>  <name>` LF, report.json, report.md, report_meta.json 이름순 |

생성 절차(`report.build_report`): 출력 루트가 `-fixture`로 끝나야 하고 run 디렉터리 안이면 거부, 최종 디렉터리가 있으면 거부 →
run 디렉터리 파일 해시 기록 → `verify_run` OK 필수 → 재계산해 result_sha256과 저장된 daily·trades 행 일치 확인 → 계산 →
임시 디렉터리(`.tmp-report-*`)에 쓰고 해시 재확인, run 디렉터리 해시 재확인 → `os.rename`(덮어쓰지 않음). 실패하면 이번에 쓴
파일만 지운다. run 디렉터리는 읽기만 한다.

검증(`moneylab backtest-report-verify <report_dir> <run_dir>`, `report.check_report`, 파일 쓰기 없음): files(파일 집합과 해시),
meta(report_sha256, Python 버전 표시), versions(스키마·정의·seed 알고리즘, 모르면 거부), run_refs(run 이름, manifest SHA,
result_sha256 = manifest = result.json), run_verify(`verify_run`), content(기록된 seed·draws로 report.json과 report.md를 바이트 단위 재현).

## 6. 이번 버전에 없는 것

Profit factor, 승률, 연도별 순수익, f*, gross/비용 비율, deflated Sharpe, ΔSR 신뢰구간, p값과 다중검정, 구간 분할(초안의 구간별 B1),
계좌 모드, 세후 시나리오, 실데이터(BT-5).
