# BT4-RESEARCH-01 Evidence Review — BT4 D1–D7 고정 전 통계·구현 근거 검토

- 작업: BT4-RESEARCH-01 (Work Order `docs/tasks/BT4-RESEARCH-01/WORK_ORDER.md`, C1 `f72a477174bae28d0baaa1251e587f9dc73cf6dd`)
- 기준 commit: CANONICAL_BASE_SHA `2d6ed0a0878fac5553d5ac173f3d658d7ac78cc8`
- 근거 수집: EVIDENCE_COLLECTION gate, 2026-10-26 (모든 외부 source의 access date)
- 성격: **비구속 연구 검토 보고서.** 이 문서는 BT-4를 시작하지 않고, D1–D9 값을 정하지 않으며, BT4-Q18 해결을 주장하지 않는다. 절차를 바꾸거나 채택하지 않는다.

### 절 대응표

이 보고서는 Work Order DESIGN_CONTRACT R1의 12절 순서를 따른다. IMPLEMENTATION Gate Authorization이 요구한 항목은 아래처럼 각 절 안에 둔다.

| R1 절 | 포함 내용 (Gate Authorization 항목) |
|---|---|
| 1 Executive summary | Executive Summary, Scope and Non-Goals, Evidence Classification |
| 2 MoneyLab problem mapping | MC-V06 Problem Statement, MoneyLab Current Implementation Facts |
| 3 Source register | Literature Evidence Review |
| 4 Research-question matrix A–I | Research Questions A–I, GARCH-t vs Normal Policy Options, Mode A+B |
| 5 MC-V06 findings trace | MC-V06 descriptive diagnostics (window별 관찰) |
| 6 Candidate-method comparison | Candidate Method Comparison |
| 7 External implementation-reference review | External Implementation References |
| 8 Supported conclusions | Findings: SUPPORTED |
| 9 Challenged assumptions | Findings: CHALLENGED |
| 10 Unresolved evidence gaps | Findings: UNRESOLVED / HYPOTHESIS / CANDIDATE — INSUFFICIENT_EVIDENCE, Evidence Gaps and Limitations |
| 11 Recommendations for BT4 | Non-Binding Recommendations for BT4 |
| 12 Items requiring a separate validation/MC task | Validation Required Before BT4 Freeze |

---

## 1. Executive summary

### 1.1 요약

1. **MC-V06의 현재 futility procedure는 반보수적이다.** theta_min 경계(진짜 Sharpe = θ)에서 α=0.05 검정의 기각률은 창과 DGP에 따라 0.069–0.158이고, 일부 귀무 내부에서도 명목 수준보다 높다(예: truth SR 0.5, θ=0.3, f12 창에서 0.0934. §5.2 항목 5). (SUPPORTED, SYNTHETIC / NOT_EVIDENCE)
2. **현재 근거로는 원인을 특정할 수 없다.** non-studentization, 고정 `mean_block=20`, plug-in delta, 유한 표본, truth calibration 불확실성, heavy tails / volatility clustering은 모두 HYPOTHESIS다.
3. **Holm과 Bonferroni는 타당하지 않은 개별 p값을 복구하지 못한다.** 두 방법의 FWER 보장은 개별 p값이 귀무에서 타당하다는 전제 위에 있다. 따라서 지금 우선할 문제는 다중검정 절차가 아니라 **개별 futility 추론의 calibration**이다. (SUPPORTED)
4. **studentized block bootstrap은 중요한 후보다.** 다만 확인한 근거(Ledoit & Wolf 2008)는 두 Sharpe ratio 차이 검정에 대한 것이다. MoneyLab의 단일 기준값 futility 검정에 대해 직접 검증된 것은 아니다. (CANDIDATE)
5. **data-driven block length도 후보다.** 다만 확인한 근거(Patton, Politis & White 2009)의 최적성 기준은 test size가 아니라 분산 추정 MSE다. (CANDIDATE)
6. **Romano–Wolf StepM**은 joint dependence를 활용해 Holm보다 검정력을 높일 수 있는 후보다. 하지만 잘못 calibration된 개별 futility 검정의 해결책은 아니다. (CANDIDATE)
7. **White Reality Check와 Hansen SPA**는 data snooping과 최선 모형 선택이라는 별도 축의 방법이다. 현재 futility size 문제와 섞지 않는다.
8. **DSR과 PBO / CSCV**는 selection bias와 backtest overfitting의 진단 후보다. 개별 futility p값의 size를 보정하는 방법이 아니다.
9. **GARCH-t vs Normal 차이는 한 요인에 귀속할 수 없다.** 현재 DGP 설계에서는 volatility clustering, tail thickness, edge calibration 값이 함께 바뀐다.
10. **Mode A+B는 계속 non-normative diagnostic이다.**

### 1.2 Scope and Non-Goals

범위:

- 외부 통계·계량경제·구현 근거의 확인과 MoneyLab 문제와의 대응
- base `2d6ed0a`의 MoneyLab 코드 사실 확인
- MC-V06 canonical 출력에 대한 기술(descriptive) 진단의 재사용

하지 않는 것 (Non-Goals):

- BT-4 시작, BT4 코드 구현, D1–D9 값 결정, BT4-Q18 해결 주장
- 새 Monte Carlo, MC-V06 재실행, resampling, 새 calibration, 새 통계 절차 구현
- 외부 코드의 clone·설치·실행·복사, 의존성 추가
- 외부 구현체의 수익성을 근거로 쓰는 것

### 1.3 Evidence Classification

| 표시 | 의미 |
|---|---|
| GIT_VERIFIABLE | commit SHA·tree·경로·행 번호처럼 누구나 재현할 수 있는 MoneyLab 저장소 사실. 이 보고서의 코드 사실은 base `2d6ed0a` 기준이다 |
| CLAUDE_REPORTED | Claude가 읽고 정리한 외부 source의 주장과 Claude가 실행한 계산. **모든 외부 source 주장은 CLAUDE_REPORTED**다 |
| INDEPENDENT | 사용자나 별도 검증자의 재확인, CI 결과. **이 보고서 작성 시점에는 INDEPENDENT 등급의 주장이 없다** |
| SYNTHETIC / NOT_EVIDENCE | MC-V06 합성 시뮬레이션에서 나온 수치. 실제 시장에 대한 증거가 아니다 |

source는 Tier와 verification status를 서로 독립된 두 필드로 기록한다.

- **Tier 1**: peer-reviewed full text, full scholarly book
- **Tier 2**: original-author full working paper / preprint
- **Tier 3**: authoritative documentation 또는 mature implementation (implementation claim에만 쓴다)
- **Verification status**:
  - `VERIFIED_FROM_FULL_TEXT`: 실제로 full text를 읽은 경우에만
  - `ABSTRACT_ONLY`
  - `IMPLEMENTATION_REFERENCE`: Tier 3 전용
  - `UNVERIFIED_CANDIDATE`

결론에는 다음 분류를 붙인다: SUPPORTED, CHALLENGED, UNRESOLVED, HYPOTHESIS, CANDIDATE — INSUFFICIENT_EVIDENCE.

Recommendation 규칙: Tier 1 또는 Tier 2의 `VERIFIED_FROM_FULL_TEXT` 근거가 하나 이상 없으면 recommendation으로 확정하지 않고 `CANDIDATE — INSUFFICIENT_EVIDENCE`로 둔다.

근거 수집 중의 PDF와 텍스트 추출본은 repository 밖 Claude session scratchpad에만 있다. 이것들은 evidence 자체가 아니며, 이 보고서는 검증한 source claim만 반영한다.

---

## 2. MoneyLab problem mapping

### 2.1 MC-V06 Problem Statement

MC-V06 (COMPLETE = PASS, 실행 commit `2d6ed0a`)은 v0.6 사전등록 초안의 후보 선택지에 대해 합성 경로로 판정 특성을 추정했다. 이전 결과 감사(MC_RESULT_AUDIT)의 과학적 결론은 MIXED / DESIGN-INFORMATIVE였고, BT4 준비도는 READY_WITH_CAUTION이었다.

현재 futility procedure:

- 귀무는 H0: μ ≥ δ, 대립은 μ < δ다. 기각하면 "의미 있는 수익 없음(futility)"으로 판정한다.
- δ는 연 Sharpe θ_min을 그 창의 표본 변동성으로 일별 평균으로 바꾼 값이다.
- p값은 stationary bootstrap 평균 분포를 귀무 경계로 옮겨 계산한다.

boundary over-rejection:

- truth Sharpe가 정확히 θ인 경계 시나리오에서 α=0.05 기각률이 0.069–0.158이었다. 상세는 §5에 있다.
- 기각률은 가장 짧은 forward 12개월 창에서 가장 컸고, confirmatory 창에서 대체로 가장 작았다.

적용 범위 제한:

- 수치는 모두 SYNTHETIC / NOT_EVIDENCE다.
- 대상은 MoneyLab 합성 DGP(모멘텀 피드백 edge, GARCH-t 또는 i.i.d. Normal)와 M60 전략이다.
- 실제 시장 수익률에서의 size는 이 수치로 추론하지 않는다.

### 2.2 MoneyLab Current Implementation Facts (GIT_VERIFIABLE, base `2d6ed0a`)

| 항목 | 사실 | 위치 |
|---|---|---|
| `futility_pvalue` | p = (1 + #{boot_b − m + δ ≤ m}) / (B + 1). 기본형(basic, 비studentized) bootstrap이고 resample마다 표준화하지 않는다 | `src/moneylab/research/v06/procedures.py:163-166` |
| `futility_delta` | δ̂ = θ_min · sd(series) / √365. 같은 창의 표본 sd(n−1)를 쓰는 plug-in이고, 포지션이 없는 날(수익 0)도 포함한다 | `procedures.py:169-171` |
| `bootstrap_means` | 모든 series가 stationary-bootstrap index block 한 벌을 공유한다(series 사이 의존 보존) | `procedures.py:131-151` |
| block 생성 `_blocks` | 기하분포 p = 1/mean_block, 순환(circular), 마지막 block은 n에 맞춰 자른다 | `src/moneylab/research/stats.py:187-199` |
| `mean_block` | `Procedure.mean_block = 20.0` 고정. confirmatory 2227일, holdout 914일, forward 365/731/1096일에 모두 같다 | `src/moneylab/research/v06/montecarlo.py:137` (mean_block), `:161-162` (confirmatory·holdout 길이). forward 길이는 `SimulationCalendar`의 달력 개월 수에서 정해진다(`montecarlo.py:185-208`) |
| `derived_seed` | crc32 기반의 결정적 per-test seed | `stats.py:182-184` |
| `maxt_futility_pvalue` | 통계량 min_j (m_j − δ_j)/se_j. se_j는 bootstrap 표본 sd 하나로 고정되며 resample마다 다시 계산하지 않는다. 정규화이지 resample별 studentization은 아니다 | `procedures.py:174-193` |
| `holm` | 표준 Holm step-down 조정 p값 | `procedures.py:254-263` |
| `iut_holm` | 전략별 max(p1, p2)에 Holm 적용 (S = H1과 H2 모두 기각) | `procedures.py:266-269` |
| `r1a_reject_pvalue` | min(1, 2·min(p_maxt, p2low)). 서로 다른 재표본 방식을 Bonferroni로 결합 | `procedures.py:272-276` |
| holdout / forward futility | E0 단일 p_fut. Holm 적용 여부는 D3 후보에 따른다 | `montecarlo.py:340-358, 554, 577` |
| truth calibration | 시나리오의 진짜 Sharpe는 400년 표본 경로 하나에서 calibration한다. summary의 `truth_se_sharpe` = 0.05 | `montecarlo.py:279-325` |
| DGP "normal" | i.i.d. 정규 innovation, `garch_alpha = garch_beta = 0`, `t_df = None` | `montecarlo.py` tier1 시나리오, MC-V06 summary `resolved_dgp` |
| DGP "garch_t" | GARCH(1,1) α=0.08, β=0.90, t4 innovation | 위와 같음 |
| edge | 지난 60일 수익 부호에 따라 ±edge_annual/365 drift(모멘텀 피드백). SR 0.5 시나리오의 edge_annual은 garch_t 0.512, normal 0.584로 서로 다르다 | `src/moneylab/research/v06/synthetic.py:83-104`, summary |
| MC-V06 record | per-rep record에는 p값, 판정 boolean, roundtrips, 위험 지표만 있고 표본 평균·sd는 없다 | MC-V06 `records.jsonl` 구조 |
| R5 truth | R5 전략의 truth E0 Sharpe는 약 −0.18(null_drift) ~ −0.81이다. null_drift를 제외하면 약 −0.44 ~ −0.81 | MC-V06 summary `truth` |

---

## 3. Source register

### 3.1 공통 사항

- 외부 source의 주장은 모두 CLAUDE_REPORTED다.
- access date는 모두 2026-10-26이다.
- 근거 수집 환경에는 PDF page 렌더러가 없었다. 그래서 full text는 표준 라이브러리 텍스트 추출로 읽었다. **수식과 정리의 세부는 검증하지 못했고**, `VERIFIED_FROM_FULL_TEXT`는 본문 문장 수준의 확인을 뜻한다.
- stance는 "현재 MoneyLab futility procedure와 그 보정 방향"에 대한 관계로 정의한다:
  - SUPPORTS: 현재 방식이 타당하다는 쪽
  - CHALLENGES: 현재 방식에 문제를 제기하는 쪽
  - NEUTRAL: 별도 축이거나 직접 관련이 없음

### 3.2 요약표

| ID | Source | 읽은 version | Tier | Verification status | Stance | Evidence grade |
|---|---|---|---|---|---|---|
| S01 | Patton, Politis & White (2009) | 출판본 | 1 | VERIFIED_FROM_FULL_TEXT | NEUTRAL | CLAUDE_REPORTED |
| S02 | Ledoit & Wolf (2008) | 출판본 판형 | 1 | VERIFIED_FROM_FULL_TEXT | CHALLENGES | CLAUDE_REPORTED |
| S03 | Bailey & López de Prado, Deflated Sharpe Ratio | author manuscript (2014-07-31) | 2 | VERIFIED_FROM_FULL_TEXT (출판본 미확인) | NEUTRAL | CLAUDE_REPORTED |
| S04 | Bailey, Borwein, López de Prado & Zhu, PBO | author revised version (2014-11) | 2 | VERIFIED_FROM_FULL_TEXT (출판본 미확인) | NEUTRAL | CLAUDE_REPORTED |
| S05 | Romano & Wolf, StepM | working paper (2003-10) | 2 | VERIFIED_FROM_FULL_TEXT (Econometrica 2005 출판본 미확인) | CHALLENGES | CLAUDE_REPORTED |
| S06 | Hansen, SPA | working paper (Brown WP 01-06, 2001-11) | 2 | VERIFIED_FROM_FULL_TEXT (JBES 2005 출판본 미확인) | NEUTRAL | CLAUDE_REPORTED |
| S07 | Harvey, Liu & Zhu | NBER working paper w20592 (2014-10) | 2 | VERIFIED_FROM_FULL_TEXT (RFS 2016 출판본 미확인) | NEUTRAL | CLAUDE_REPORTED |
| S08 | White (2000), Reality Check | 텍스트 추출 불가(이미지 스캔) | 해당 없음 | UNVERIFIED_CANDIDATE | 해당 없음 | 해당 없음 |
| S09 | Holm (1979) | 원문 미확보 | 해당 없음 | ABSTRACT_ONLY | 해당 없음 | 해당 없음 |
| S10 | Politis & Romano (1994), Stationary Bootstrap | 원문 미확보 | 해당 없음 | ABSTRACT_ONLY | 해당 없음 | 해당 없음 |
| S11 | Politis & White (2004) | 원문 미확보 | 해당 없음 | ABSTRACT_ONLY | 해당 없음 | 해당 없음 |
| S12 | Lo (2002) | 원문 미확보 | 해당 없음 | ABSTRACT_ONLY (원문 미확보) | 해당 없음 | 해당 없음 |
| S13 | Hall, Horowitz & Jing (1995) | 원문 미확보 | 해당 없음 | UNVERIFIED_CANDIDATE | 해당 없음 | 해당 없음 |

### 3.3 Source별 검토

#### S01 — Patton, Politis & White (2009)

- **Citation:** Patton, A., Politis, D. N., & White, H. (2009). Correction to "Automatic Block-Length Selection for the Dependent Bootstrap" by D. Politis and H. White. *Econometric Reviews*, 28(4), 372–375.
- **DOI / URL:** 10.1080/07474930802459016 / https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf
- **Version / Tier / status:** 출판본(저자 Duke 페이지 호스팅) / Tier 1 / VERIFIED_FROM_FULL_TEXT
- **확인 위치:** §1 Introduction, 정정 항목 1–5, §2와 Table 1–4
- **Supported claims:**
  - Politis & White (2004) Theorem 3.1의 stationary-bootstrap 분산 상수 D_SB를 2g²(0)로 정정한다.
  - 2004년 논문의 시뮬레이션 결과는 잘못된 상수에 기반해 "inaccurate"하므로 Table 1–4를 새 표로 대체한다.
  - 정정 후 AR(1), N=200/800 시뮬레이션에서 추정 block 크기는 평균적으로 진짜 최적값의 90–110%다.
- **Assumptions:** 최적화 대상은 bootstrap 분산 추정량의 MSE다. 시뮬레이션 DGP는 Gaussian AR(1)이다.
- **Limitations:** 검정 size나 신뢰구간 coverage에 대한 최적성을 주장하지 않는다.
- **MoneyLab applicability:** 창 길이별 data-driven block 규칙의 후보 근거가 된다. 단, MoneyLab futility 검정의 size calibration 근거는 아니다. Politis & White (2004)를 인용한다면 반드시 이 정정본과 함께 인용해야 한다.

#### S02 — Ledoit & Wolf (2008)

- **Citation:** Ledoit, O., & Wolf, M. (2008). Robust performance hypothesis testing with the Sharpe ratio. *Journal of Empirical Finance*, 15(5), 850–859.
- **URL:** https://uzh.ch/cmsssl/econ/dam/jcr:ffffffff-935a-b0d6-0000-00007214c2bc/jef_2008pdf.pdf
- **Version / Tier / status:** 출판본 판형(University of Zurich 호스팅) / Tier 1 / VERIFIED_FROM_FULL_TEXT
- **확인 위치:** Abstract, §3.1 (HAC inference), §3.2 (bootstrap inference, Remark 3.3), §4–5, Table 1
- **Supported claims:**
  - Jobson–Korkie/Memmel 검정은 heavy tails나 시계열 의존이 있으면 타당하지 않다.
  - HAC 추론은 점근적으로 타당하지만 소·중표본에서 자주 liberal하다.
  - 비studentized bootstrap은 정규근사 기반 추론보다 정확도를 개선하지 못한다(Remark 3.3, Hall 1992와 Lahiri 2003 인용).
  - 제안 방법은 studentized circular block bootstrap이다. 표준오차는 prewhitened QS kernel(원표본)과 Götze–Künsch 방식(bootstrap 표본)으로 구하고, block 크기는 calibration(Loh 1987)으로 고른다.
  - 시뮬레이션(Table 1)에서 Boot-TS는 i.i.d., GARCH, VAR DGP 모두에서 명목 수준에 가깝다.
- **Assumptions:** 정상(stationary) 시계열. 이론적 우월성 증명에는 강한 moment 조건이 필요하다고 저자들이 밝힌다.
- **Limitations:**
  - **연구 대상은 두 Sharpe ratio의 차이 검정이다.** 단일 Sharpe ratio로의 확장은 독자에게 맡긴다고 쓴다.
  - MoneyLab의 단일 기준값(δ) futility 검정, 그리고 δ 자체가 표본 sd로 추정되는 구조는 다루지 않는다.
- **MoneyLab applicability:** studentization이 왜 중요한지에 대한 일반 근거다. MoneyLab futility 검정의 직접 검증은 아니다.

#### S03 — Bailey & López de Prado, Deflated Sharpe Ratio

- **Citation:** Bailey, D. H., & López de Prado, M. The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality. *Journal of Portfolio Management*, 40(5), 94–107 (2014).
- **DOI / URL:** 10.3905/jpm.2014.40.5.094 / https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
- **Version / Tier / status:** author manuscript, "This version: July 31, 2014" / Tier 2 / VERIFIED_FROM_FULL_TEXT. JPM 출판본은 읽지 않았다.
- **확인 위치:** 본문 BACKTEST OVERFITTING 절, THE DEFLATED SHARPE RATIO 절, Appendix A.1, Appendix 3 언급
- **Supported claims:**
  - DSR은 다중검정 아래의 selection bias와 비정규 수익률이라는 두 가지 성과 부풀림을 보정한다.
  - DSR은 PSR의 기준값을 N개 독립 시행의 기대 최대 Sharpe로 올린 것이다.
  - 입력은 시행 수 N, 시행 간 SR 분산, 표본 길이, 왜도, 첨도다.
  - holdout은 단일 시행처럼 평가하므로 반복하면 false positive가 생긴다.
- **Assumptions:** 독립 시행과 시행 SR의 정규성. 시행이 독립이 아닐 때 N을 정하는 방법은 Appendix 3에 있다고 쓴다.
- **Limitations:** 개별 검정의 size 보정 방법이 아니다. 확인한 대목에서 serial dependence 처리는 확인하지 못했다.
- **MoneyLab applicability:** PAPER 판정 전의 selection-bias 진단 후보다.

#### S04 — Bailey, Borwein, López de Prado & Zhu, Probability of Backtest Overfitting

- **Citation:** Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. The Probability of Backtest Overfitting. *Journal of Computational Finance* (2017).
- **DOI / URL:** 10.21314/JCF.2016.322 / https://carmamaths.org/jon/backtest2.pdf
- **Version / Tier / status:** author revised version, 2014-11 / Tier 2 / VERIFIED_FROM_FULL_TEXT. 출판본은 읽지 않았다(eScholarship 사본 접근 실패).
- **확인 위치:** Definition 2.1–2.2, CSCV 절차(§2.2), §5 Limitations and misuse, §6–7
- **Supported claims:**
  - PBO는 IS에서 최적인 전략이 OOS에서 중앙값 아래에 놓일 확률이다.
  - CSCV는 성과 행렬을 짝수 S개의 부분행렬로 나눠 대칭 조합으로 추정한다.
  - 연구자는 실제로 시험한 모든 시행을 제공해야 하며, 시행을 숨기면 overfitting이 과소추정된다.
  - 이 절차는 백테스트 자체의 정확성(비용 가정, look-ahead 등)을 평가하지 않는다.
  - 성과 시계열의 자기상관이 강하면 대칭 분할이 특성을 흐릴 수 있다.
- **Assumptions:** 동기화된 T×N 성과 행렬과 부분표본에서 추정 가능한 성과 지표.
- **Limitations:** 개별 전략 가설검정이 아니라 선택 "과정"을 진단한다. N이 작을 때의 해상도는 확인하지 않았다.
- **MoneyLab applicability:** selection-process 진단 후보다. MoneyLab family는 전략 4개(M20, M60, M120, R5)라서 해상도가 낮을 수 있다. 이 점은 Claude의 추론이며 source가 직접 말하지 않는다.

#### S05 — Romano & Wolf, Stepwise Multiple Testing as Formalized Data Snooping

- **Citation:** Romano, J. P., & Wolf, M. Stepwise Multiple Testing as Formalized Data Snooping. Working paper, Universitat Pompeu Fabra, October 2003. 출판본은 *Econometrica*, 73(4), 1237–1282 (2005).
- **DOI / URL:** 10.1111/j.1468-0262.2005.00615.x (출판본) / https://econ-papers.upf.edu/papers/712.pdf (WP)
- **Version / Tier / status:** **working paper (2003-10)**, 원 UPF URL의 web archive 사본 / Tier 2 / VERIFIED_FROM_FULL_TEXT. **Econometrica 출판본은 읽지 않았다.**
- **확인 위치:** Abstract, §1, §2.3 Existing Methods(각주 6 포함), Algorithm 3.1, Assumption 3.1, Theorem 3.1, Scenario 3.1–3.3, §4, §6–7
- **Supported claims:**
  - StepM은 FWE를 점근적으로 강하게(strong) 통제한다.
  - 검정통계량의 joint dependence를 암묵적으로 포착하므로, single-step 방법보다 더 많은 거짓 귀무를 기각한다.
  - Bonferroni와 Holm은 개별 p값이 귀무에서 (점근) Uniform(0,1)이라는 가정 아래 FWE를 통제한다. 각주 6에 따르면 Prob(p ≤ x) ≤ x면 충분하다.
  - 두 방법은 의존 구조를 고려하지 않고 최악의 의존을 가정하므로 보수적일 수 있다.
  - White의 RC는 "표본에서 최선인 전략이 benchmark를 이기는가"만 판단하며, White는 약한 FWE 통제만 증명했다.
  - studentization은 가능하면 쓸 것을 권고한다.
  - 시계열(Scenario 3.2)에서는 moment와 mixing 조건이 필요하다.
  - 데이터 기반 block 선택(Algorithm 6.1)은 계산 비용 때문에 다중검정 시뮬레이션에서 검증하지 못했다고 밝힌다.
- **Assumptions:** Assumption 3.1(점근 분포의 존재와 bootstrap의 일치성), 정상 시계열의 moment·mixing 조건.
- **Limitations:** WP와 출판본 사이에 차이가 있을 수 있다. 시뮬레이션은 주로 정규 DGP다.
- **MoneyLab applicability:**
  - Holm의 대안으로 검정력을 개선하는 후보다.
  - 동시에, Holm이 개별 p값의 size 문제를 고칠 수 없다는 근거를 제공한다(§2.3의 가정).

#### S06 — Hansen, Superior Predictive Ability

- **Citation:** Hansen, P. R. An Unbiased and Powerful Test for Superior Predictive Ability. Brown University Department of Economics Working Paper No. 01-06, November 2001. 출판본 계열은 *Journal of Business & Economic Statistics*, 23, 365–380 (2005), "A Test for Superior Predictive Ability".
- **URL:** https://ideas.repec.org/p/bro/econwp/2001-06.html (WP 서지). 본문은 원 저자 URL의 web archive 사본으로 읽었다.
- **Version / Tier / status:** **working paper (2001-11)** / Tier 2 / VERIFIED_FROM_FULL_TEXT. **JBES 2005 출판본은 읽지 않았다.**
- **확인 위치:** Abstract, §1, §4 (Example 3–4), §5, §5.1.3, §5.2
- **Supported claims:**
  - RC는 similarity 조건을 만족하지 않는다. 그래서 점근적으로 편향되고 p값이 비일치적이다.
  - RC는 나쁘거나 무관한 모형을 포함하면 보수적이 되어 검정력을 잃는다. 극단적으로는 검정력이 0에 가까워질 수 있다.
  - 개선책은 두 가지다. 하나는 나쁜 모형의 영향을 점근적으로 없애는 consistent p값이고, 다른 하나는 standardized maximum(최대 t통계량, T_SM)이다.
  - 재표본에는 stationary bootstrap을 쓴다.
- **Assumptions:** 상대 성과 변수의 정상성과 mixing 조건.
- **Limitations:**
  - WP의 Monte Carlo는 시간에 독립인 데이터(block 길이 1)로만 했다.
  - 출판본과 다를 수 있다.
  - 대상은 "최선 모형이 benchmark보다 나은가"이며 futility 검정이 아니다.
- **MoneyLab applicability:**
  - "family 중 최선 전략이 benchmark를 이기는가"라는 별도 축의 후보다.
  - R5는 대부분의 시나리오에서 크게 음수인 truth SR을 가지지만, null_drift에서는 약 −0.18이다(§2.2). 크게 음수인 시나리오에서는 RC를 쓰면 보수화될 위험이 있다. 이 연결은 MoneyLab 적용에 대한 Claude의 추론이다.

#### S07 — Harvey, Liu & Zhu

- **Citation:** Harvey, C. R., Liu, Y., & Zhu, H. ". . . and the Cross-Section of Expected Returns". NBER Working Paper No. 20592, October 2014. 출판본은 *Review of Financial Studies* (2016).
- **URL:** https://www.nber.org/system/files/working_papers/w20592/w20592.pdf
- **Version / Tier / status:** **NBER working paper (2014-10)** / Tier 2 / VERIFIED_FROM_FULL_TEXT. **RFS 출판본은 읽지 않았다.**
- **확인 위치:** Abstract, §4.2–4.4, Table 3–4
- **Supported claims:**
  - 광범위한 data mining 때문에 새 factor에 t > 2.0 기준을 쓰는 것은 타당하지 않다. 추정 결과는 t > 3.0 수준의 기준이다.
  - 검정 간 상관과 미출판(숨겨진) 시행을 허용하는 다중검정 틀을 쓴다.
  - Bonferroni와 Holm은 FWER를, BHY는 FDR을 통제한다.
  - Bonferroni는 p값 의존 구조에 대한 가정 없이 FWER를 통제한다고 서술한다(§4.4.1).
- **Assumptions:** 학계 전체의 factor 발견 과정과 출판편향 모형.
- **Limitations:** 사전등록된 소수 전략 family가 아니라 학계 전체의 factor 발견에 대한 기준이다.
- **MoneyLab applicability:**
  - 직접 연결되는 부분: "실제 시험한 모든 시행을 세야 한다"는 원칙.
  - 직접 연결되지 않는 부분: t > 3.0이라는 수치 기준. MoneyLab family로 옮길 근거가 없다.

#### S08 — White (2000)

- **Citation:** White, H. (2000). A Reality Check for Data Snooping. *Econometrica*, 68(5), 1097–1126.
- **DOI:** 10.1111/1468-0262.00152
- **Status:** **UNVERIFIED_CANDIDATE.** 확보한 사본은 제3자 강의 페이지의 이미지 스캔 PDF였고 텍스트 추출이 불가능했다.
- RC에 대한 이 보고서의 서술은 모두 S05와 S06이 전하는 2차 서술이다. White 원문을 직접 확인한 주장은 없다.

#### S09 — Holm (1979)

- **Citation:** Holm, S. (1979). A Simple Sequentially Rejective Multiple Test Procedure. *Scandinavian Journal of Statistics*, 6(2), 65–70.
- **Status:** **ABSTRACT_ONLY.** 공식 무료 원문을 확보하지 못했다.
- Holm 절차의 성질은 S05와 S07의 2차 서술로만 확인했다.

#### S10 — Politis & Romano (1994)

- **Citation:** Politis, D. N., & Romano, J. P. (1994). The Stationary Bootstrap. *Journal of the American Statistical Association*, 89(428), 1303–1313.
- **Status:** **ABSTRACT_ONLY.** 원문을 확보하지 못했다.
- 같은 저자의 *Statistica Sinica* 4, 461–476 (1994)도 abstract만 확인했다. 그 abstract는 stationary bootstrap이 넓은 추정량 class에서 점근적으로 타당하다는 결과를 제시한다고 쓴다.

#### S11 — Politis & White (2004)

- **Citation:** Politis, D. N., & White, H. (2004). Automatic Block-Length Selection for the Dependent Bootstrap. *Econometric Reviews*, 23(1), 53–70.
- **Status:** **ABSTRACT_ONLY.** 원문을 확보하지 못했다.
- 정정 관계는 S01에서 확인했으며, 이 보고서는 S11에 대한 독립 주장을 만들지 않는다.

#### S12 — Lo (2002)

- **Citation:** Lo, A. W. (2002). The Statistics of Sharpe Ratios. *Financial Analysts Journal*, 58(4), 36–52.
- **DOI:** 10.2469/faj.v58.n4.2453
- **Status:** **원문 미확보.** 공식 출처에서 abstract 수준만 확인했다(ABSTRACT_ONLY).
- 이 보고서는 Lo (2002)를 recommendation의 근거로 쓰지 않는다.

#### S13 — Hall, Horowitz & Jing (1995)

- **Citation:** Hall, P., Horowitz, J. L., & Jing, B.-Y. (1995). On blocking rules for the bootstrap with dependent data. *Biometrika*, 82(3), 561–574.
- **DOI:** 10.1093/biomet/82.3.561
- **Status:** **UNVERIFIED_CANDIDATE.** 원문을 확보하지 못했다.
- 2차 서술에 따르면 최적 block 차수가 분산·편의 추정 n^(1/3), 단측 분포 n^(1/4), 양측 분포 n^(1/5)로 다르다. 이 보고서는 **이 source를 근거로 현재 block=20이 잘못되었다고 판단하지 않는다.**

---

## 4. Research-question matrix A–I

### A. 현재 stationary-bootstrap futility test는 theta_min 경계에서 적절히 calibration되어 있는가?

- **Answer:** 아니다. MoneyLab 합성 설정에서는 반보수적이다.
- **Evidence:** §5의 경계 기각률(α=0.05에서 0.069–0.158, MC SE 약 0.004 이하)과 귀무 내부 기각률(§5.2 항목 5).
- **Classification:** SUPPORTED (SYNTHETIC / NOT_EVIDENCE)
- **Remaining uncertainty:**
  - truth Sharpe 자체가 400년 경로 하나에서 calibration되어 ±0.05 정도 불확실하다.
  - 결과가 실제 시장 수익률에 그대로 옮겨진다는 근거는 없다.

### B. 무엇이 관찰된 size distortion을 설명할 수 있는가?

- **Answer:** 이번 task에서는 인과적 분리가 불가능하다.
  - 후보: non-studentization, 고정 `mean_block=20`, plug-in delta, 유한 표본, truth calibration 불확실성, heavy tails / volatility clustering, bootstrap 구성 방식.
  - MC-V06 record에 표본 평균과 sd가 없으므로 기술 진단만으로는 분리할 수 없다.
- **Evidence:**
  - S02: 비studentized bootstrap은 정규근사보다 정확도를 개선하지 못한다는 Remark 3.3의 이론적 언급, 그리고 두 Sharpe 차이 검정 simulation에서 Boot-TS가 명목 size에 더 가까웠다는 결과(§8-3).
  - S05: studentization을 권고한다.
  - S01: data-driven block은 분산 MSE 기준이다.
  - §5 패턴: 짧은 창에서 초과기각이 가장 크고, Normal DGP에서도 나타난다.
- **Classification:** HYPOTHESIS (모든 원인 후보)
- **Remaining uncertainty:** 원인별 기여도. 분리하려면 별도 사전등록 MC가 필요하다(§12).

### C. dependent returns 환경에서 inference와 FWER를 다루는 확립된 방법은 무엇인가?

- **Answer:**
  - 개별 추론: block / stationary bootstrap, 그리고 가능하면 studentized 통계량.
  - FWER: 개별 p값이 타당하다는 전제 아래 임의 의존에서 통제하는 Holm(보수적), 또는 joint dependence를 활용하는 Romano–Wolf StepM.
- **Evidence:** S02 (Tier 1), S05 (Tier 2), S06 (Tier 2). S10은 ABSTRACT_ONLY.
- **Classification:** SUPPORTED (일반론)
- **Remaining uncertainty:** MoneyLab의 단일 기준값 futility 검정에 대한 직접 검증은 없다.

### D. Holm을 계속 normative candidate로 둘 근거가 있는가? Romano–Wolf는 무엇을 더 해결하는가?

- **Answer:**
  - Holm은 개별 p값이 타당하다는 전제 아래 임의 의존에서 FWER를 통제한다. 하지만 **타당하지 않은 개별 p값을 복구하지 못한다.** 현재 개별 futility p값은 그 타당성 전제가 깨져 있으므로(§5) Holm의 FWER 통제 **보장**을 적용할 수 없다. 이는 실제 FWER가 반드시 α를 넘는다는 뜻이 아니며, 실제 FWER는 별도로 평가해야 한다.
  - Romano–Wolf StepM이 더하는 것은 **검정력**(의존 구조 활용)이지, 개별 검정의 타당성이 아니다.
- **Evidence:** S05 §2.3과 각주 6, S07 §4.4. Holm 원문(S09)은 ABSTRACT_ONLY.
- **Classification:**
  - Holm의 복구 불가: SUPPORTED
  - Holm 유지 여부: UNRESOLVED. 개별 검정을 보정한 뒤에 판단할 문제다.
  - StepM 도입: CANDIDATE — INSUFFICIENT_EVIDENCE. MoneyLab에서의 이득 크기가 검증되지 않았다.
- **Remaining uncertainty:** 4전략 family에서 StepM과 Holm의 실제 검정력 차이.

### E. PAPER 판정 전에 strategy-selection bias와 backtest overfitting을 어떻게 측정해야 하는가?

- **Answer:** 실제 시험한 모든 시행을 기록하고, DSR(선택된 전략 SR의 다중 시행·비정규 보정)과 PBO / CSCV(선택 과정의 overfitting 확률)를 진단으로 쓰는 방법이 문헌에 있다.
- **Evidence:** S03, S04, S07 (모두 Tier 2 VERIFIED_FROM_FULL_TEXT)
- **Classification:**
  - 진단 역할: SUPPORTED
  - 규범 PASS 규칙으로 쓰는 것: CANDIDATE — INSUFFICIENT_EVIDENCE
- **Remaining uncertainty:** 4전략 family에서의 해상도, 그리고 MoneyLab 수익률의 serial dependence가 DSR 입력에 주는 영향.

### F. DSR과 PBO / CSCV는 각각 어떤 역할을 할 수 있으며 어떤 역할을 할 수 없는가?

- **Answer:**
  - 할 수 있는 것: DSR은 선택된 전략의 SR이 다중 시행과 비정규성을 감안해도 기준을 넘는지 진단한다. PBO / CSCV는 선택 과정이 OOS에서 중앙값 이상을 고르는지 진단한다.
  - 할 수 없는 것: 개별 futility p값의 size 보정. 백테스트 자체의 정확성 평가(S04 §5). 시행을 숨긴 경우의 정확한 추정(S04 §5).
- **Evidence:** S03, S04
- **Classification:** SUPPORTED (역할 구분)
- **Remaining uncertainty:** MoneyLab 설정(N=4, 의존 수익률)에서의 실용성.

### G. GARCH-t와 Normal DGP 사이의 robustness를 어떻게 표현할 것인가?

- **Answer:** 현재 DGP 설계에서는 volatility clustering(GARCH 유무), tail thickness(t4 vs Normal), edge calibration 값이 함께 바뀐다. 그래서 차이를 한 요인에 귀속할 수 없다. 세 정책은 비교만 한다.
- **Evidence:** §2.2의 DGP 사실 (GIT_VERIFIABLE)
- **Classification:** UNRESOLVED
- **Remaining uncertainty:** 요인별 효과. 2×2 factorial DGP가 별도 MC 후보다(§12).

#### GARCH-t vs Normal Policy Options (비교만 하며 선택하지 않는다)

| 정책 | 의미 | 장점 | 단점 |
|---|---|---|---|
| worst-case-over-DGP | 오류율 등의 기준을 고려한 DGP 중 가장 나쁜 값으로 평가 | 오류율에 보수적 상한을 줌. 단일 수치로 보고 가능 | DGP 목록 선택에 결과가 의존함. 검정력이 손실됨. 목록 밖 DGP는 보장하지 않음 |
| criterion-must-hold-under-both-DGPs | 같은 기준이 두 DGP 모두에서 성립해야 PASS | 해석이 단순함. 두 모형 모두에 대한 강건성을 요구함 | DGP가 두 개이면 사실상 worst-case와 비슷하게 동작할 수 있음. 비단조성이 있으면 기준이 불안정함 |
| model-specific reporting without aggregate pass rule | DGP별 결과를 따로 보고하고 종합 PASS 규칙은 두지 않음 | 정보 손실이 없음. 요인 혼재를 감추지 않음 | 사전등록된 판정 규칙이 없으므로 결정을 미루는 결과가 됨. 사후 선택 위험이 있음 |

### H. Mode A+B를 향후 MC에서 non-normative diagnostic으로 유지할 것인가, 제거할 것인가?

- **Answer:** 근거는 양쪽에 있고, 이 task는 선택하지 않는다. 어떤 경우에도 normative procedure로 올리지 않는다.
- **Evidence:** 이전 MC-V06 결과 감사(MC_RESULT_AUDIT)에서 Mode A+B는 D3/D7 경계를 넘었다(SYNTHETIC / NOT_EVIDENCE). Mode A+B는 초안 §11.3 판정표에 없는 harness의 탐색 트랙이다(GIT_VERIFIABLE).
- **Classification:** UNRESOLVED

#### Mode A+B

- **유지 근거:**
  - 탐색 트랙(E = PASS, S = FAIL 전략의 forward 진행)의 운영 특성을 계속 관찰할 수 있다.
  - D3/D7 경계 위반 같은 위험 신호를 조기에 볼 수 있다.
- **제거 근거:**
  - 사전등록 초안 §11.3에 없는 트랙이다.
  - 비규범 수치가 규범 판정과 혼동될 위험이 있다.
  - MC 보고의 복잡도가 늘어난다.
- **제한:**
  - Mode A+B는 non-normative diagnostic이다.
  - 그 결과는 D1–D9 결정이나 PASS/FAIL 규칙의 근거가 아니다.

### I. 외부 구현체 중 MoneyLab의 독립 implementation reference로 유용한 것은 무엇인가?

- **Answer:**
  - 통계 방법의 독립 교차검증 참조로는 `bashtage/arch`가 가장 직접적이다.
  - QuantConnect/Lean, vectorbt, bt는 architecture / implementation pattern 참조로만 쓴다.
- **Evidence:** §7 (Tier 3, IMPLEMENTATION_REFERENCE)
- **Classification:** IMPLEMENTATION_REFERENCE. scientific evidence가 아니다.
- **Remaining uncertainty:** 구현체의 정확성은 이 task에서 검증하지 않았다. 실행하지 않았다.

---

## 5. MC-V06 findings trace

**표시:** SYNTHETIC / NOT_EVIDENCE, CLAUDE_REPORTED. 이 수치들은 EVIDENCE_COLLECTION gate에서 계산한 기술 진단을 그대로 옮긴 것이며, 이 gate에서 새로 계산하지 않았다.

**재현 질의:**

- 대상: RUN_ROOT `C:/MoneyLab-mc-v06-full-run/data/processed/research_v06_sim/mc_v06_full_2d6ed0a`의 canonical unit `11_garch_t_M60_+0p3`, `12_normal_M60_+0p3`, `13_garch_t_M60_+0p5`, `14_normal_M60_+0p5`, `15_garch_t_M60_+0p7`, `16_normal_M60_+0p7` (attempt1), 각 `records.jsonl`의 10,000 replication.
- 필드: `strategies.M60.p_fut_E0[θ]`(conf), `holdout_p_fut[θ]`(hold), `forward.{12,24,36}.p_fut[θ]`(f12, f24, f36). θ는 시나리오 truth Sharpe와 같은 후보값이다.
- 계산: p ≤ α인 replication 비율.
- 실행 조건: 표준 라이브러리만, stdin, `python -B`, `PYTHONDONTWRITEBYTECODE=1`, 쓰기 없음.

### 5.1 정확한 경계(M60 E0 truth SR = θ)에서 α=0.05 futility 기각률

| 시나리오 (θ) | conf (2227일) | hold (914일) | f12 (365일) | f24 (731일) | f36 (1096일) |
|---|---|---|---|---|---|
| garch_t +0.3 (0.3) | 0.072 | 0.089 | 0.111 | 0.090 | 0.088 |
| normal +0.3 (0.3) | 0.082 | 0.104 | 0.128 | 0.108 | 0.103 |
| garch_t +0.5 (0.5) | 0.107 | 0.116 | 0.132 | 0.122 | 0.111 |
| normal +0.5 (0.5) | 0.096 | 0.106 | 0.144 | 0.119 | 0.105 |
| garch_t +0.7 (0.7) | 0.069 | 0.092 | 0.125 | 0.100 | 0.092 |
| normal +0.7 (0.7) | 0.116 | 0.117 | 0.158 | 0.132 | 0.118 |

비율 하나의 MC SE는 √(p(1−p)/10000)이다. 관찰된 범위에서 MC SE는 약 0.004 이하이고(p=0.158일 때 약 0.0036), p ≤ 0.10이면 약 0.003 이하다.

### 5.2 window별 관찰 (원인 판단 아님)

1. 경계 초과기각은 모든 창, 모든 θ, 두 DGP에서 나타난다.
2. 가장 짧은 forward 12개월 창이 가장 크고, confirmatory 창이 대체로 가장 작다.
3. α=0.01에서의 경계 기각률은 약 0.02–0.05다.
4. 경계의 p_fut 누적분포는 q=0.2에서 0.21–0.33이다. 꼬리만이 아니라 분포 전체가 작은 p 쪽으로 치우쳐 있다.
5. 귀무 내부(truth SR > θ)에서도 기각률이 높다. 아래 값은 EVIDENCE_COLLECTION의 기존 원 출력에서 옮긴 것이다(SYNTHETIC / NOT_EVIDENCE, CLAUDE_REPORTED). 필드는 모두 `strategies.M60.forward.12.p_fut[θ]`이고 계산은 p ≤ 0.05인 replication 비율이다.
   - 명목 수준(α=0.05)보다 높은 예: unit `13_garch_t_M60_+0p5`(truth SR 0.5)에서 θ=0.3이면 f12 기각률 0.0934, unit `16_normal_M60_+0p7`(truth SR 0.7)에서 θ=0.5이면 f12 기각률 0.1185. 두 unit은 위 재현 질의 대상(unit 11–16) 안에 있으며, θ만 truth SR보다 작은 후보값으로 바꾼 것이다.
   - 정규근사보다 높은 예: unit 11–16 밖의 unit `17_garch_t_M60_+1p0`와 `18_normal_M60_+1p0`(truth SR 1.0, attempt1)에서 같은 필드 `forward.12.p_fut["0.3"]`의 기각률은 0.0510(garch_t)과 0.0504(normal)로 명목 수준과 비슷하지만, Claude가 계산한 i.i.d. 정규근사(약 0.01)보다 높다. 이 근사 비교는 CLAUDE_REPORTED이다.
   - 이 수치들은 원인의 증거가 아니다.
6. 같은 θ에서도 DGP에 따라 confirmatory 기각률 차이가 관찰된다: θ=0.3에서 0.072(garch_t)/0.082(normal), θ=0.5에서 0.107/0.096, θ=0.7에서 0.069/0.116. 이 차이를 GARCH나 heavy tail의 단독 효과로 귀속하지 않는다(§2.2의 요인 혼재). truth calibration 불확실성과도 맞는 모습이지만 확인된 것은 아니다.

### 5.3 적용 범위 제한

- 이 수치들은 어떤 원인도 증명하지 않는다.
- "짧은 창에서 가장 크다"는 패턴이 truth calibration 오차만으로는 잘 설명되지 않는다는 해석도 기술적 추론일 뿐이다.

---

## 6. Candidate-method comparison

방법들이 같은 문제를 푼다고 가정하지 않는다.

- "MC-V06 무효화"는 그 변경이 BT4 절차에 들어가면 MC-V06의 operating characteristics가 더 이상 BT4 절차를 기술하지 못한다는 뜻이다.
- "별도 MC"는 D1–D7 고정 전에 별도의 사전등록 validation/MC task가 필요하다는 뜻이다.

| 방법 | 해결하려는 문제 | null / alternative 또는 목표 | 핵심 assumptions | dependence 처리 | multiple testing | selection bias | MoneyLab fit / 현재 절차와의 관계 | cost | MC-V06 무효화 | 별도 MC | 근거 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| current stationary-bootstrap futility | 단일 전략의 "μ < δ" 판정 | H0: μ ≥ δ̂ / H1: μ < δ̂ | 정상성, SB 일치성, δ̂ plug-in | SB, mean block 20 고정 | 없음 (Holm은 별도 단계) | 없음 | 현행 절차. §5에서 반보수적 | 중간 | 해당 없음 | 해당 없음 | §2.2 (GIT_VERIFIABLE), S10 ABSTRACT_ONLY |
| studentized block bootstrap | 의존 데이터에서의 size·coverage 정확도 | 같은 귀무, studentized 통계량 | 정상성, moment·mixing, 블록별 SE | block bootstrap, Götze–Künsch형 SE | 없음 | 없음 | futility·H1 통계량의 대체 후보. 단일 기준값 futility에 대한 직접 검증은 없음 | 높음 | YES | YES | S02 (두 Sharpe 차이), S05 |
| data-driven block length | 분산 추정 MSE 최적 block | 목표는 σ² 추정의 MSE 최소화 | 정상성, spectral 추정 | 자료로 block 추정 | 없음 | 없음 | 창 길이별 block 규칙 후보. size 최적화 근거가 아님 | 낮음 | YES | YES | S01 (Tier 1). S11 ABSTRACT_ONLY, S13 UNVERIFIED_CANDIDATE |
| Holm | 임의 의존에서의 FWER | 교집합 귀무, strong FWER | 개별 p값이 타당함 (Prob(p ≤ x) ≤ x) | 무시 (최악 의존 가정) | FWER | 없음 | 현행 D3 후보. 개별 p값의 타당성 전제가 깨지면 FWER 통제 보장을 적용할 수 없음 (실제 FWER는 별도 평가) | 매우 낮음 | NO (이미 MC 대상) | 해당 없음 | S05, S07. S09 ABSTRACT_ONLY |
| Romano–Wolf StepM | joint dependence를 활용한 FWER 검정력 개선 | 전략별 θ_k ≤ 0, strong FWER (점근) | Assumption 3.1, moment·mixing | joint bootstrap | FWER | data snooping 일부 | Holm 대체 후보(S·H1 family). 개별 futility size 문제의 해결책이 아님 | 높음 | YES | YES | S05 (WP) |
| White Reality Check | 최선 모형이 benchmark를 이기는가 (data snooping) | H0: max_k θ_k ≤ 0 | 정상성, SB | SB | 최선 1개만 판정 (약한 FWE) | data snooping | 별도 축. 크게 나쁜 모형(대부분 시나리오의 R5)이 있으면 보수화 위험 (S06 기반 Claude 추론) | 중간 | YES | YES | S08 UNVERIFIED_CANDIDATE. S05·S06의 2차 서술 |
| Hansen SPA | RC의 편향과 나쁜 모형 민감도 개선 | H0: max_k θ_k ≤ 0, consistent p, standardized max | 정상성, mixing | SB | 최선 1개만 판정 | data snooping | RC보다 MoneyLab family(R5 포함)에 적합할 수 있음 (Claude 추론) | 중간 | YES | YES | S06 (WP) |
| Deflated Sharpe Ratio | 선택된 전략 SR의 다중 시행·비정규 보정 | 진짜 SR이 기대 최대 SR 이하인가 | 독립 시행(App. 3 보정), 시행 SR 정규 | 확인 못함 | 기준값 상향으로 반영 | YES | PAPER 전 진단 후보. size 보정 방법이 아님 | 낮음 | 진단만이면 NO | 규범이면 YES | S03 (author manuscript) |
| PBO / CSCV | 선택 과정의 overfitting 확률 | 비모수 (logit 분포) | 동기화된 T×N 행렬, 모든 시행 공개 | 대칭 분할 (강한 자기상관에서 한계) | 아님 | YES | 진단 후보. N=4라 해상도가 낮을 수 있음 (Claude 추론) | 중간 | 진단만이면 NO | 규범이면 YES | S04 (author revised) |

---

## 7. External implementation-reference review

**구분:**

- 이 절의 내용은 Tier 3 IMPLEMENTATION_REFERENCE이며 scientific evidence가 아니다.
- GitHub stars, 수익률, screenshot, README의 profitability claim은 근거로 쓰지 않았다.
- 조사는 읽기 전용 GitHub REST API와 web 열람으로만 했다. clone, 설치, 실행, 의존성 추가, 코드 복사는 하지 않았다.
- 기록한 SHA는 2026-10-26 조사 시점 기본 branch의 HEAD다.

| Repository | 공식 여부 | 확인 commit SHA | Licence | 유지보수 (조사 시점 pushed_at) |
|---|---|---|---|---|
| bashtage/arch | 저자(Kevin Sheppard) 개인 repo, fork 아님 | `d0c59ddb023ca6703fbfaa87ef305d0157e11a67` (main) | `LICENSE.md`: 저작권 표시와 허용형 이용 허락. GitHub API의 SPDX 판정은 NOASSERTION | 2026-10-25 |
| QuantConnect/Lean | QuantConnect 조직 공식 repo | `f3d841e60dfd010ee5fc293ea893e56952484108` (master) | Apache-2.0 | 2026-10-23 |
| polakowo/vectorbt | 저자 repo, fork 아님 | `8e30b8ce102f302bec0c0226e05b59714453bebd` (master) | `LICENSE.md`: Commons Clause 조건이 붙은 license (판매 제한). GitHub API는 NOASSERTION | 2026-10-23 |
| pmorissette/bt | 저자 repo, fork 아님 | `5dbfbedb24ec83d7a43c8d55741b72b1642a62a6` (master) | MIT | 2026-10-25 |

**bashtage/arch:**
- 확인한 구조:
  - `arch/bootstrap/base.py`
    - `optimal_block_length`: docstring이 Politis & White (2004)와 Patton, Politis & White (2009)를 인용하고, Patton의 MATLAB 조정값을 쓴다고 밝힌다.
    - `IIDBootstrap`, `StationaryBootstrap`, `CircularBlockBootstrap`, `MovingBlockBootstrap` 클래스가 있다.
    - 재현 가능한 bootstrap에는 `seed`를 명시하라고 안내한다.
  - `arch/bootstrap/multiple_comparison.py`
    - `SPA`: p값 종류 `lower`, `consistent`, `upper`, bootstrap 종류 stationary / circular / moving block.
    - `StepM` (Romano–Wolf): `studentize`(kernel 장기분산), `nested` bootstrap 옵션.
    - `MCS` (Hansen, Lunde & Nason)도 있다.
- MoneyLab 참고 패턴:
  - 통계 절차(SB, block 길이, SPA, StepM)를 독립적으로 교차검증할 때 가장 직접적인 참조 후보다.
  - 정정본(PPW 2009)을 반영한다고 명시한 점도 참고할 만하다.
- **의존성으로 채택하지 않는다.** 코드를 복사하지 않고, 설치·실행하지 않는다.

**QuantConnect/Lean:**
- 확인한 구조:
  - 최상위가 `Engine`, `Algorithm`, `Algorithm.Framework`, `Research`, `Optimizer`, `Report`, `Tests` 등으로 나뉘어 있다.
  - `Common/Statistics/Statistics.cs`에 `SharpeRatio`, `ProbabilisticSharpeRatio`, `ObservedSharpeRatio` 등이 있고, DSR은 함수 목록에서 찾지 못했다.
- MoneyLab 참고 패턴:
  - 실행 엔진, 연구, 최적화, 보고의 분리. MoneyLab의 research / backtest 분리와 비교할 만한 architecture 참조다.

**polakowo/vectorbt:**
- 확인한 구조:
  - `vectorbt/generic/splitters.py`에 `RangeSplitter`와 `RollingSplitter`가 있다. purging/embargo CV는 유료판(vectorbt.pro) 문서를 가리킨다.
  - `vectorbt/returns/accessors.py`는 `sharpe_ratio`와 `rolling_sharpe_ratio`를 제공한다. 이 파일 안에서는 deflated·probabilistic Sharpe를 찾지 못했다. 검색 범위는 이 파일 하나였으며, repository 전체에 없다는 뜻은 아니다.
- MoneyLab 참고 패턴: 시계열 분할 API 설계.
- Commons Clause license 때문에 코드 참조와 재사용에 제약이 있다.

**pmorissette/bt:**
- 확인한 구조: `bt/backtest.py`의 `benchmark_random`은 백테스트를 구조가 같은 무작위 전략들(nsim개)과 비교한다.
- MoneyLab 참고 패턴: MoneyLab의 B1 matched random exposure 비교와 개념이 비슷한 benchmark 패턴이다.

---

## 8. Supported conclusions

모든 외부 근거는 CLAUDE_REPORTED이고, MC 수치는 SYNTHETIC / NOT_EVIDENCE다.

1. **[SUPPORTED]** MC-V06의 현재 futility procedure는 theta_min 경계와 일부 귀무 내부에서 반보수적이다. (§5.1 경계표, §5.2 항목 5의 귀무 내부 값. SYNTHETIC / NOT_EVIDENCE)
2. **[SUPPORTED]** Holm과 Bonferroni의 FWER 보장은 개별 p값이 타당하다는 전제 위에 있다. 따라서 이 절차들은 타당하지 않은 개별 p값을 복구하지 못하며, 지금 우선할 문제는 개별 futility 추론의 calibration이다. (S05 §2.3과 각주 6, S07 §4.4, §5)
3. **[SUPPORTED, 적용 범위 제한]** Ledoit & Wolf의 두 Sharpe ratio 차이 검정 simulation(Table 1)에서 studentized time-series bootstrap(Boot-TS)은 JKM, HAC 계열(HAC, HAC_PW), i.i.d. bootstrap(Boot-IID)보다 명목 size에 더 가까웠다. 비studentized bootstrap이 정규근사보다 정확도를 개선하지 못한다는 내용은 이 simulation 결과가 아니라 Remark 3.3의 별도 이론적 언급이다(Hall 1992, Lahiri 2003 인용). 두 근거 모두 MoneyLab의 단일 기준값 futility 검정에 대해 직접 검증된 결과가 아니다. (S02 Tier 1. studentization 권고는 S05 Tier 2)
4. **[SUPPORTED]** Politis & White (2004)의 block 길이 방법은 정정본(S01)으로만 써야 하며, 그 최적성 기준은 분산 추정 MSE다.
5. **[SUPPORTED]** White RC와 Hansen SPA는 "family의 최선 모형이 benchmark를 이기는가"라는 data snooping 축의 방법이다. RC는 나쁜 모형을 포함하면 보수적이 된다. (S06. RC 원문 S08은 UNVERIFIED_CANDIDATE이므로 RC 서술은 S05·S06의 2차 서술)
6. **[SUPPORTED]** DSR과 PBO / CSCV는 selection bias와 backtest overfitting의 진단이다. 개별 검정의 size 보정 방법이 아니다. PBO는 모든 시행을 공개해야 하고 백테스트의 정확성은 평가하지 않는다. (S03, S04)
7. **[SUPPORTED]** Harvey, Liu & Zhu의 t > 3.0은 학계 전체 factor 발견의 다중성과 출판편향을 반영한 기준이다. "모든 시행을 센다"는 원칙은 MoneyLab에 연결되지만, 수치 기준을 그대로 옮길 근거는 없다. (S07)

## 9. Challenged assumptions

1. **[CHALLENGED]** 초안의 정규근사 operating characteristics(초안 §10.6·§10.7 표)가 MC 결과를 대신할 수 있다는 가정. MC-V06 결과와 맞지 않았다. (이전 MC_RESULT_AUDIT, §5)
2. **[CHALLENGED]** "futility family에 Holm을 적용하면 오류율이 통제된다"는 암묵적 가정. 개별 p값의 타당성 전제가 깨져 있으면 Holm의 FWER 통제 보장을 적용할 수 없다. 실제 FWER가 반드시 α를 넘는다는 뜻은 아니며, 실제 FWER는 별도로 평가해야 한다. (§8-2)
3. **[CHALLENGED]** GARCH-t vs Normal의 차이를 tail thickness 또는 GARCH 중 한 요인의 효과로 해석하는 것. 현재 DGP에서는 두 요인과 edge 값이 함께 바뀐다. (§2.2)
4. **[CHALLENGED]** DSR, PBO, CSCV를 개별 futility 검정의 size 보정 수단으로 보는 해석. (§8-6)

## 10. Unresolved evidence gaps

### 10.1 UNRESOLVED

- Holm을 규범 후보로 유지할지 여부. 개별 검정 calibration 이후에 판단할 문제다.
- GARCH-t vs Normal 비단조성의 원인과 세 정책 중 어느 것을 쓸지. 이 task는 선택하지 않는다.
- Mode A+B를 유지할지 제거할지. 이 task는 선택하지 않는다.

### 10.2 HYPOTHESIS

다음은 모두 MC-V06 futility 초과기각의 원인 후보이며, 어느 것도 인과적으로 확인되지 않았다.

- non-studentization (S02의 일반론이 개연성을 지지하지만 적용 범위가 다르다)
- 고정 `mean_block=20` (모멘텀 피드백 DGP의 국면 지속성에 비해 짧을 가능성)
- plug-in delta (δ̂의 표본 변동)
- finite sample (짧은 창에서 초과기각이 가장 크다는 패턴과 맞는 모습이지만 인과는 미확인)
- truth calibration uncertainty (±0.05. 짧은 창에서 가장 크다는 패턴과는 잘 맞지 않는다는 기술적 추론이 있음)
- heavy tails / volatility clustering (Normal DGP에서도 초과기각이 나타남)
- bootstrap 구성 방식 (basic(hybrid) bootstrap 방식의 p값, 순환 block, 마지막 block 절단)

### 10.3 CANDIDATE — INSUFFICIENT_EVIDENCE

- 단일 기준값 futility 검정을 studentized block bootstrap으로 바꾸면 경계 size가 개선된다.
- 창 길이별 data-driven block이 futility size를 개선한다.
- Holm을 Romano–Wolf StepM으로 바꾼다.
- RC나 SPA를 S family 또는 PAPER 판정에 도입한다.
- DSR이나 PBO / CSCV를 규범 PASS 규칙으로 쓴다.
- Harvey–Liu–Zhu식 t-hurdle을 적용한다.
- Lo (2002)의 serial-correlation 보정을 적용한다 (원문 미확보).

### 10.4 Evidence Gaps and Limitations

1. **원문 검증 한계:**
   - White (2000): UNVERIFIED_CANDIDATE, 이미지 스캔이라 텍스트 추출 불가
   - Holm (1979): ABSTRACT_ONLY
   - Politis & Romano (1994): ABSTRACT_ONLY
   - Politis & White (2004): ABSTRACT_ONLY
   - Lo (2002): 원문 미확보
   - Hall, Horowitz & Jing (1995): UNVERIFIED_CANDIDATE
2. **출판본 미확인:** Romano & Wolf(2003 WP), Hansen(2001 WP), Harvey, Liu & Zhu(NBER WP), DSR(author manuscript), PBO(author revised version)는 출판본이 아니라 WP나 저자 원고를 읽었다. 출판본과 내용이 다를 수 있다.
3. **수식 미검증:** PDF page 렌더러가 없어서 텍스트 추출로 읽었다. 수식과 정리의 세부는 검증하지 못했고, 검증은 본문 문장 수준이다.
4. **Ledoit & Wolf의 적용 범위:** 연구 대상은 두 Sharpe ratio의 차이 검정이다. MoneyLab의 단일 기준값 futility 검정, δ가 표본 sd로 추정되는 구조, 귀무 경계로 옮기는 방식은 다루지 않는다.
5. **MoneyLab 고유의 인과 분석 부재:** MC-V06 record에 표본 평균과 sd가 없고, 이 task는 새 simulation을 금지한다. 그래서 초과기각의 원인별 기여를 분리하지 못했다.
6. **block 길이 문헌의 공백:** MoneyLab DGP(지난 60일 부호 기반 모멘텀 피드백)에서 block 길이의 효과를 직접 다룬 source는 확인하지 못했다.
7. **외부 구현체:** 구현의 정확성을 이 task에서 검증하지 않았다(실행 금지).
8. **INDEPENDENT 등급 없음:** 이 보고서의 모든 외부 주장은 CLAUDE_REPORTED다. 사용자나 독립 검증자의 재확인은 아직 없다.

---

## 11. Recommendations for BT4

**이 절의 권고는 모두 비구속(non-binding)이다.** D1–D9 값을 정하지 않고, 절차 변경을 채택하지 않는다. MC-V06 operating characteristics를 무효화하는 변경은 §12의 별도 사전등록 validation/MC task를 거쳐야 하며, 그 task는 D1–D7 고정 전에 와야 한다.

| # | 권고 | 상태 | 근거 |
|---|---|---|---|
| R-1 | BT4 설계 문서에 "현재 futility procedure는 MC-V06 합성 설정에서 반보수적"이라는 사실을 명시하고, MC-V06 수치를 인용할 때 이를 전제로 둔다 | SUPPORTED | §5, §8-1 |
| R-2 | futility family의 오류율 문제를 다중검정 절차(Holm, StepM)만으로 해결하려 하지 않는다. 개별 futility 추론의 calibration을 먼저 다룬다 | SUPPORTED | S05 §2.3, §8-2 |
| R-3 | studentized block bootstrap 기반 futility 통계량을 §12의 별도 MC에서 평가할 후보로 둔다. 직접 검증 전에는 채택 근거로 쓰지 않는다 | CANDIDATE | S02 (적용 범위 제한), S05 |
| R-4 | 창 길이별 data-driven block 규칙을 별도 MC 후보로 둔다. 인용할 때는 S01 정정본과 MSE 기준이라는 한계를 함께 쓴다 | CANDIDATE | S01 |
| R-5 | Holm 유지 여부는 개별 검정 calibration 이후로 미룬다. StepM과 SPA는 검정력·data snooping 축의 별도 비교 후보로 둔다 | UNRESOLVED (Holm) / CANDIDATE (StepM, SPA) | S05, S06 |
| R-6 | DSR과 PBO / CSCV는 PAPER 전 진단 후보로만 두고, 규범 PASS 규칙으로 쓰지 않는다. 실제 시험한 모든 시행을 기록하는 원칙은 유지한다 | SUPPORTED (진단 역할) / CANDIDATE (규범 사용) | S03, S04, S07 |
| R-7 | GARCH-t vs Normal은 §4 G의 세 정책을 비교한 상태로 BT4에 넘긴다. 요인 분리는 2×2 factorial DGP로 별도 검증한다 | UNRESOLVED | §2.2 |
| R-8 | Mode A+B는 non-normative diagnostic으로만 취급한다. 향후 MC에서 유지할지 제거할지는 BT4 또는 후속 MC 계약에서 정한다 | UNRESOLVED | §4 H |
| R-9 | 통계 절차를 독립 교차검증할 때 `bashtage/arch`(SHA 고정)를 implementation reference 후보로 둔다. 의존성 채택과 코드 복사는 하지 않는다 | IMPLEMENTATION_REFERENCE | §7 |
| R-10 | 원인 귀속(§10.2)을 BT4 문서에서 사실처럼 쓰지 않는다 | SUPPORTED | §10.2, §10.4-5 |

---

## 12. Items requiring a separate validation/MC task

다음은 **실행하지 않은** 별도 사전등록 validation/MC task 후보다. 모두 BT4 절차에 들어가면 MC-V06 operating characteristics를 무효화하는 변경이거나 그 원인을 분리하기 위한 것이다. 따라서 채택하려면 D1–D7 고정 전에 별도 Work Order로 사전등록해야 한다.

| # | 후보 | 목적 | 관련 HYPOTHESIS / CANDIDATE |
|---|---|---|---|
| V-1 | studentized futility | 단일 기준값 futility 검정에서 studentized block bootstrap의 경계 size 평가 | non-studentization, R-3 |
| V-2 | delta definition | plug-in δ̂ 대신 다른 δ 정의(예: 고정 변동성 기준 등 후보)의 size 영향 평가 | plug-in delta |
| V-3 | block rule | 고정 `mean_block=20`과 창 길이별 data-driven block의 비교 | fixed mean_block=20, R-4 |
| V-4 | truth precision | truth calibration 정밀도를 높여(예: 더 긴 truth 경로) 경계 불확실성을 분리 | truth calibration uncertainty |
| V-5 | 2×2 DGP | Normal / t innovations × homoskedastic / GARCH 요인 분리 | heavy tails / volatility clustering, R-7 |
| V-6 | Holm vs StepM / SPA | 개별 검정 보정 이후의 FWER 절차 비교 (검정력·오류율) | R-5 |
| V-7 | Mode A+B reporting | Mode A+B를 비규범 진단으로 유지할 때의 보고 방식, 또는 제거 시의 영향 | R-8 |
| V-8 | finite-sample 분리 | 창 길이별 size 변화를 원인 후보와 분리해 측정 | finite sample |

각 후보의 구체적 설계(반복 수, 시나리오, 판정 기준)는 해당 task의 Work Order에서 정한다. 이 보고서는 설계 값을 제시하지 않는다.
