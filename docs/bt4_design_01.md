# BT4-DESIGN-01 — BT-4 고정 전 결정 구조와 검증 경계 설계

- 작업: BT4-DESIGN-01 (Work Order `docs/tasks/BT4-DESIGN-01/WORK_ORDER.md`, C1 `55a834947c4145e80dacc39659bdc4b47588bbe4`)
- 기준 commit: CANONICAL_BASE_SHA `2a184b2d3f44d868590d65f85f7dfd9d09fe7988`. 이 문서의 repository 인용(경로:행)은 모두 이 commit 기준이다.
- 성격: **비구속 설계 문서.** 어떤 결정값도 선택하지 않는다. 초안의 현재안·기본값은 모두 "draft(미고정)"이며 최종값이 아니다.

### 증거 표시

| 표시 | 의미 |
|---|---|
| GIT_VERIFIABLE | 위 기준 commit의 경로·행으로 재현 가능한 repository 사실 |
| SYNTHETIC / NOT_EVIDENCE | MC-V06 합성 결과. 수치는 `docs/research_bt4_01_evidence_review.md`(이하 "RESEARCH-01 report")에 고정된 것만 인용한다 (CLAUDE_REPORTED) |
| CLAUDE_REPORTED | Claude가 정리·계산한 내용. 외부 문헌 주장은 모두 이 등급이다 |
| INFERENCE | 이 문서에서 새로 한 추론 |
| HYPOTHESIS | 원인이 확인되지 않은 설명 |

외부 문헌의 Tier와 verification status는 RESEARCH-01 report §3(source register)을 그대로 쓴다. 이 문서는 어떤 status도 올리지 않는다. 새 웹 조사와 새 계산은 하지 않았다.

---

## 1. Purpose / non-goals

목적:

1. BT-4(v0.6 사전등록 고정)에서 결정해야 할 전체 decision inventory를 repository에서 복원한다.
2. 각 decision의 dependency와 evidence 상태를 적는다.
3. validation이 필요한 decision과 policy-only decision을 나눈다.
4. 이후 statistical validation의 사전등록 입력 구조를 정의한다.
5. 이후 freeze task가 쓸 decision framework를 정의한다.

하지 않는 것:

- BT-4 freeze. D1–D10, U, G, 위험 정책, DP2–DP4, BT4-Q18의 어떤 값도 고르지 않는다.
- 절차 갈림길 A/B 선택, 통계 절차 채택(studentized futility, block 길이 방법, Holm/StepM/SPA/RC 중 승자)
- GARCH/Normal 정책 선택, Mode A+B 유지·제거, DSR·PBO의 규범 규칙 채택
- ε, 목표 MC SE, 목표 truth SE, 반복 수 같은 값 확정
- simulation, calibration, resampling, 후보 절차 구현, BT4 implementation, downstream task ID 고정

BT-4의 정의: "v0.6 사전등록 고정(D1–D10, U1–U9 결정 반영)" — `docs/backtest_design.md:663` (GIT_VERIFIABLE).

## 2. Canonical BT-4 decision inventory

### 2.1 출처

| 출처 | 내용 |
|---|---|
| `docs/research_v06_preregistration_draft.md:513-527` (§18.1) | D1–D9 (선택지와 근거, "결정 전에는 고정 불가") |
| `docs/research_v06_preregistration_draft.md:529-539` (§18.2) | G1–G7 ("기존 결정 사항"의 현재안) |
| `docs/research_v06_preregistration_draft.md:634-691` | config 템플릿의 `# Dn PENDING` 표시 |
| `docs/backtest_design.md:673-685` (16절) | U1–U9, D10 |
| `docs/backtest_design.md:441-447` | DP1–DP4 |
| `docs/tasks/BT-3E/WORK_ORDER.md:286` | BT-4로 넘긴 항목 목록 (DEFERRED_TO_LATER_TASKS) |
| `docs/tasks/BT-3E/WORK_ORDER.md:259` | 위험 정책의 BT4_FROZEN_VALUE 필드 (기본값 없음) |

### 2.2 D1–D10 (GIT_VERIFIABLE)

| ID | 의미 | 선택지 (draft) | draft 표시 | 출처 |
|---|---|---|---|---|
| D1 | 무익성 최소 효과 θ_min (연 Sharpe). δ_s = θ_min·sd/√365 (원문 표기 `δ_s = θ_min · sd_G(r^s) / √365`) | 0.3 / 0.5 / 0.7 | config `# D1 PENDING` (주석 처리된 0.5) | draft:519, :682, 공식은 draft:345 |
| D2 | 무익성·무작위보다 나쁨 유의수준 α_fut | 0.05 / 0.10 | `# D2 PENDING` | draft:520, :684 |
| D3 | 무익성 REJECT에 Holm 적용 (primary 4개) | 적용 / 미적용 | `# D3 PENDING` | draft:521, :685 |
| D4 | forward S_F에 H2 포함 | 포함(IUT) / H1만 | `# D4 PENDING` | draft:522, :689 |
| D5 | forward 유의수준 α_F | 0.05 / 0.10 / 0.20 | `# D5 PENDING` | draft:523, :690 |
| D6 | forward 최종 분석 시점 T_F | 12 / 24 / 36개월 | `# D6 PENDING` | draft:524, :636 |
| D7 | 중간·최종 무익성 α 배분 | 각 α_fut/2 / 각 α_fut / 중간 분석 없음 | `# D7 PENDING` | draft:525, :691 |
| D8 | 구간 경계의 열린 포지션 | 가상 진입·청산 + 비용 / 비용 없이 시가 평가 | config 637행에 `boundary_rule = "virtual_entry_exit_with_costs"`가 주석 없이 있으나 같은 행에 `# D8 PENDING` 표시 | draft:526, :637 |
| D9 | historical holdout 끝 H_end | 2026-10-02 / 동결일 전날 | `# D9 PENDING` | draft:527, :634 |
| D10 | H1 수준 왜곡과 엔진 FAR 미확정의 판정 반영 | 보고 전용 / π 기준 보정(시뮬레이션 필요, 별도 승인) / 판정 제외 | – | `docs/backtest_design.md:682`, 배경 :594-599 |

### 2.3 U1–U9 (GIT_VERIFIABLE, `docs/backtest_design.md:675-684`)

| ID | 의미 | 상태 (canonical 표기) | BT-3E handoff 포함 |
|---|---|---|---|
| U1 | M20/M60/M120 정의 | **결정(2026-10-16): BT-1은 SMA 규칙** (:675) | 아니오 |
| U2 | 계정 수수료 | 사용자 확인. 확인 전 FEE_UNCONFIRMED, 판정 25 bp (:676) | 아니오 |
| U3 | 최소 주문·수량·호가 단위 | 공식 자료로 확인. 계좌 모드만 영향 (:677) | 아니오 |
| U4 | 신호 결측 시 보유 중 포지션 | 유지 / 청산 (:678) | 예 |
| U5 | 1시간봉 제공 범위가 일봉보다 짧을 때 | 평가 시작일을 늦춤 / 그 기간은 E2만 (:679) | 예 |
| U6 | 참여율 상한 | 연구 모드 보고 전용(현재 설계) / 판정 반영 (:680) | 예 |
| U7 | 가격 수치 표현 | float64 + Decimal(현재 설계) / 전부 Decimal (:681) | 아니오 |
| U8 | 커밋 위치 | 새 브랜치 기준 커밋 선택 (:683). 행의 설명은 문서가 미추적 파일이던 시점 기준이다 (INFERENCE) | 아니오 |
| U9 | raw·vault 접근 guard | 초안 19.5 사양 적용 여부 (:684) | 아니오 |

### 2.4 G1–G7 (GIT_VERIFIABLE, `docs/research_v06_preregistration_draft.md:533-539`)

모두 §18.2 "기존 결정 사항"의 **현재안**이며, 사전등록이 고정되기 전이므로 immutable decision이 아니다.

| ID | 항목 | draft 현재안 |
|---|---|---|
| G1 | 계정 수수료 | 공식 확인 전 25 bp |
| G2 | 계획 자본 / 판정 자본 | 100만 / 500만 / 1,000만 KRW, 판정은 1,000만 |
| G3 | 시장 충격 가정 | ι_ref = 1.0 bp @ 100만 KRW, √ 스케일 |
| G4 | 양(+)의 연도 비율 | 60 % (민감도 50·70 %) |
| G5 | 품질 임계값 | 5절 (민감도 0.5배·2배) |
| G6 | AI_ops 세션 빈도·단가, Infra 입력값 | 미정 |
| G7 | guard 규칙 (19.5) | 사양만 있음, 구현과 적용은 사용자 결정 |

### 2.5 위험 정책 handoff 항목 (GIT_VERIFIABLE)

`docs/tasks/BT-3E/WORK_ORDER.md:286`의 BT-4 목록과, 같은 문서 :259의 BT4_FROZEN_VALUE 필드("정책이 명시, 기본값 없음")를 대응시킨다.

| handoff 항목 (:286) | 대응 필드 (:259) |
|---|---|
| ratio | `threshold_ratio` |
| comparison operator | `comparison_operator` |
| accumulation mode | `accumulation_mode` |
| metric / date mapping | `metric_id`, `window_mapping_id` |
| per-strategy cost / capital / scenario | 전략별 `scenario`, `initial_cash`, `fee_bps`, `kappa_bps`, `impact_bps`, `fill_substitution`, `capacity_verified`, 후보 전략 집합과 설정 |
| confirmation interval | `confirmatory_first_day`, `confirmatory_last_day` |
| check_window_end_utc | `check_window_end_utc` |
| F selection rule | `f_rule_sha256` (F 선택 규칙 식별) |
| violation handling | :259에 대응 필드 없음. :286 목록에만 있음 |

참고 (GIT_VERIFIABLE): MC-V06 격자는 위험 정책을 "누적 2 × 비교 2, 비율 1.5"로만 평가했다 — `docs/backtest_design.md:533`.

### 2.6 DP2–DP4 (GIT_VERIFIABLE, `docs/backtest_design.md:443-447`)

| ID | 내용 |
|---|---|
| DP2 | locked 파일은 interval별 gzip 없는 canonical JSONL. 초안 19.1·부록 A의 `*.jsonl.gz` 문구와 다르며 BT-4 고정 때 정리 |
| DP3 | 접근 기록은 manifest를 다시 쓰지 않고 `access/*.json`. 초안 19.2 문구와 다르며 BT-4 고정 때 정리 |
| DP4 | "forward 12개월", "T_F개월"을 W_end 값으로 바꾸는 해석은 BT-4 study·config 고정에서 한다 |

DP1(forward 월별 위험 한도 확인)은 장치가 BT-3e에서 구현되었고 정책 값만 BT-4로 넘어왔다(:441). 그 정책 값이 §2.5의 항목이다.

### 2.7 BT4-Q18 (GIT_VERIFIABLE)

"엔진의 gap-free 창 vs 사전등록 D·D−N 종가" — `docs/tasks/BT-3E/WORK_ORDER.md:185`. MC-V06도 엔진 수준 동치를 주장하지 않으며 미해결로 남았다(`docs/backtest_design.md:519`).

### 2.8 DSR 보고 항목과 시도 수 (GIT_VERIFIABLE)

- draft §6.1: "deflated Sharpe의 시도 수는 9(primary 4 + secondary 5)로 고정한다" (draft:149)
- draft §10.5 "Sharpe 차이와 기타 보고": deflated Sharpe(시도 수 9, 확증 평가 기간의 왜도·첨도) (draft:336)
- 과최적화 대응 표: "deflated Sharpe(시도 수 9)" (draft:470)
- config 템플릿: `deflated_sharpe_trials = 9` (draft:642)

draft 안의 "고정한다"는 문구는 사전등록 초안의 문장이며, 사전등록 자체가 아직 고정되지 않았으므로 시도 수 9는 BT-4 freeze 전 draft 값이다.

### 2.9 U4a

`docs/tasks/BT-3E/WORK_ORDER.md:286`의 handoff 목록에 "U4/U4a/U5/U6"로 이름만 나온다. canonical repository에서 정의를 찾지 못했다. 분류: **UNRESOLVED_REFERENCE.** U4의 하위 항목이라고 추론하지 않으며, 이 문서에서 정의하지 않는다.

### 2.10 alias와 연결 관계

| 관계 | canonical 근거 | 판정 |
|---|---|---|
| G1 = U2 (계정 수수료) | G1 "계정 수수료, 공식 확인 전 25 bp"(draft:533), U2 "계정 수수료, 확인 전 판정 25 bp"(`docs/backtest_design.md:676`) | 지지됨 |
| G7 = U9 (guard, 초안 19.5) | G7 "guard 규칙 (19.5)"(draft:539), U9 "초안 19.5 사양 적용 여부"(:684) | 지지됨 |
| D6 ↔ DP4 | DP4가 "T_F개월"의 W_end 변환을 다룸(:447). T_F는 D6(draft:524) | 지지됨 (연결) |
| D9(H_end) ↔ confirmation interval | 근거를 찾지 못했다. confirmation interval(`confirmatory_first_day`/`confirmatory_last_day`)의 제약 대상은 public 경계 C다: "G_end(= confirmatory_last_day + 3일)는 public 경계 C 이하"(`docs/tasks/BT-3E/WORK_ORDER.md:204`), T12(:306). 확증 평가 구간은 "warmup 끝 ~ 2024-03-31"이고 H_end는 그 뒤 holdout의 끝이다(draft:207-208) | **canonical source가 지지하지 않음.** 연결로 표시하지 않는다 |
| D9 ↔ holdout 길이 | draft:208 (holdout 2024-04-01 ~ H_end), MC-V06 `holdout: int = 914  # 2024-04-01 .. 2026-10-02 (D9)` (`src/moneylab/research/v06/montecarlo.py:162`) | 지지됨 (연결) |
| confirmation interval ↔ public 경계 C | `docs/tasks/BT-3E/WORK_ORDER.md:204`, :306 | 지지됨 (연결) |

## 3. Decision classification

분류는 Work Order의 어휘만 쓰며 **잠정 설계 분류**다. freeze 결정이 아니다. D1–D7은 READY_TO_FREEZE로 두지 않는다. 이 문서에서 READY_TO_FREEZE로 분류한 항목은 없다.

| 항목 | 분류 | 근거 |
|---|---|---|
| D1, D2, D7 | NEEDS_VALIDATION | 현재 futility 절차의 운영 특성(§5)에 직접 걸린다 |
| D3 | NEEDS_VALIDATION | Holm 보장은 개별 p값의 타당성에 의존한다(§6). 개별 calibration 결과가 먼저 필요하다 |
| D4, D5 | NEEDS_POLICY_DECISION | H1·H2 통계량을 바꾸지 않는다는 조건에서. 바꾸면 NEEDS_VALIDATION으로 바뀐다 (INFERENCE) |
| D6 | NEEDS_VALIDATION | forward 12개월 창에서 경계 왜곡이 가장 컸다(SYNTHETIC). 정책 판단도 함께 필요하다 |
| D8, D9 | NEEDS_POLICY_DECISION | MC 차원이 아니다(`docs/backtest_design.md:534`). validation과의 약한 의존은 §11.5 |
| D10 | NEEDS_POLICY_DECISION | π 기준 보정을 고르면 시뮬레이션이 필요하므로 NEEDS_VALIDATION |
| U1 | OUT_OF_SCOPE | 이미 결정됨(2026-10-16). BT-3E handoff에 없음 |
| U2 (= G1) | NEEDS_POLICY_DECISION | 사용자 확인 |
| U3 | OUT_OF_SCOPE | 계좌 모드만 영향. handoff에 없음 |
| U4, U5, U6 | NEEDS_POLICY_DECISION | BT-3E handoff 항목 |
| U4a | UNRESOLVED_REFERENCE | §2.9 |
| U7 | DEFERRED | 현재 설계가 적혀 있고 handoff에 없음 |
| U8 | OUT_OF_SCOPE | 행의 설명이 문서 위치에 관한 것으로, 판정 규칙이 아님 (INFERENCE) |
| U9 (= G7) | NEEDS_POLICY_DECISION | 사용자 결정 |
| G2–G5 | NEEDS_POLICY_DECISION | draft 현재안의 확정 |
| G6 | NEEDS_POLICY_DECISION | 미정 |
| 위험 정책 항목 (§2.5) | NEEDS_POLICY_DECISION | MC-V06 평가 범위(누적 2 × 비교 2, 비율 1.5) 밖의 값을 고르면 NEEDS_VALIDATION |
| DP2, DP3, DP4 | NEEDS_POLICY_DECISION | 문서 정합과 해석 |
| BT4-Q18 | NEEDS_VALIDATION | 엔진 수준 문제 (§11.1, §11.4) |
| DSR 보고·시도 수 | DIAGNOSTIC_ONLY | draft의 기존 보고 항목 (§2.8, §9) |
| PBO | PROPOSED_DECISION_ITEM | draft에 없음 (§9) |
| Mode A+B | DIAGNOSTIC_ONLY | §9 |
| GARCH/Normal 정책 | PROPOSED_DECISION_ITEM | §8 |

## 4. D/R/V dependency map

### 4.1 R-1~R-10 (RESEARCH-01 report §11, `docs/research_bt4_01_evidence_review.md:625-634`)

| # | 요약 | 상태 |
|---|---|---|
| R-1 | futility 반보수성을 BT4 문서에 명시 | SUPPORTED |
| R-2 | 다중검정보다 개별 futility calibration을 먼저 | SUPPORTED |
| R-3 | studentized block bootstrap futility를 별도 MC 후보로 | CANDIDATE |
| R-4 | 창 길이별 data-driven block을 별도 MC 후보로 | CANDIDATE |
| R-5 | Holm 유지 여부는 calibration 이후. StepM·SPA는 별도 비교 후보 | UNRESOLVED / CANDIDATE |
| R-6 | DSR·PBO는 진단 후보로만 | SUPPORTED / CANDIDATE |
| R-7 | GARCH/Normal 세 정책 비교 상태로, 2×2 DGP 별도 검증 | UNRESOLVED |
| R-8 | Mode A+B는 비규범 진단 | UNRESOLVED |
| R-9 | `bashtage/arch`를 교차검증 참조 후보로 | IMPLEMENTATION_REFERENCE |
| R-10 | 원인 귀속을 사실처럼 쓰지 않음 | SUPPORTED |

### 4.2 V-1~V-8 (RESEARCH-01 report §12, `docs/research_bt4_01_evidence_review.md:644-651`)

| # | 후보 | 목적 |
|---|---|---|
| V-1 | studentized futility | 단일 기준값 futility에서 경계 size 평가 |
| V-2 | delta definition | plug-in δ̂ 대안의 size 영향 |
| V-3 | block rule | 고정 `mean_block=20` vs 창 길이별 data-driven |
| V-4 | truth precision | 경계 불확실성 분리 |
| V-5 | 2×2 DGP | Normal/t × homoskedastic/GARCH |
| V-6 | Holm vs StepM / SPA | 개별 검정 보정 이후의 FWER 절차 비교 |
| V-7 | Mode A+B reporting | 유지 시 보고 방식, 제거 시 영향 |
| V-8 | finite-sample 분리 | 창 길이별 size 변화 |

### 4.3 의존 관계 (INFERENCE, 코드 사용처 기반)

●는 직접, ○는 간접, –는 무관이다.

| | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| R-1 / R-10 (문서화) | ● | ● | ○ | – | – | ● | ● | – | – | – |
| R-2 / V-6 | – | ○ | ● | ○ | ● | – | ● | – | – | – |
| R-3 / V-1 | ● | ● | ○ | – | – | ● | ● | – | – | – |
| R-4 / V-3 (H1 p값도 같은 bootstrap) | ● | ● | ○ | ● | ● | ● | ● | – | – | ○ |
| V-2 (δ 정의) | ● | ● | – | – | – | ○ | ○ | – | – | – |
| V-4 (truth 정밀도) | ● | ● | ● | ○ | ○ | ● | ● | – | – | – |
| R-7 / V-5 (DGP 요인·정책) | ● | ● | ● | ● | ● | ● | ● | – | – | ○ |
| V-8 (유한 표본) | ○ | ● | – | – | ○ | ● | ● | – | ○ | – |
| R-5 SPA/RC (S family 대안) | – | – | – | ● | ● | – | – | – | – | – |
| R-6 DSR/PBO | – | – | – | – | – | – | – | – | – | – |
| R-8 / V-7 (Mode A+B) | – | – | ○ | – | – | – | ○ | – | – | – |
| R-9 (도구) | – | – | – | – | – | – | – | – | – | – |

R-6(DSR·PBO)은 D1–D10에 직접 연결되지 않고 DSR 보고 항목(§2.8)과 PBO 후보(§9)에 연결된다. V-8의 D9 연결은 D9가 holdout 길이를 정하기 때문이다(§2.10).

## 5. Futility procedure decomposition

원인 귀속은 모두 **HYPOTHESIS / unresolved**다. 이 문서는 새 인과 결론을 만들지 않는다.

MC-V06 관찰의 요약(SYNTHETIC / NOT_EVIDENCE, CLAUDE_REPORTED, RESEARCH-01 report §5): truth Sharpe가 θ와 같은 경계에서 α=0.05 futility 기각률은 0.069–0.158이고(`docs/research_bt4_01_evidence_review.md:451-456`), 가장 짧은 forward 12개월 창에서 가장 컸다. 일부 귀무 내부에서도 명목 수준보다 높았다(report §5.2 항목 5).

| 요소 | 현재 구현 (GIT_VERIFIABLE) | MC-V06 관찰 (SYNTHETIC) | 문헌이 직접 지지하는 범위 | 귀속 | 필요한 검증 |
|---|---|---|---|---|---|
| plug-in delta | δ̂ = θ·sd(창)/√365 (`src/moneylab/research/v06/procedures.py:169`), 수익 0인 날 포함 (`segment_returns`, `procedures.py:54-70`) | 경계 초과기각. 기여도 분리 불가 | 직접 근거 없음 | HYPOTHESIS | V-2 |
| studentization 여부 | 비studentized (`procedures.py:163`) | 같음 | S02(Tier 1, VERIFIED_FROM_FULL_TEXT): 두 Sharpe 차이 검정 simulation에서 Boot-TS가 명목 size에 더 가까움. Remark 3.3의 비studentized 관련 내용은 이론적 언급. S05(Tier 2 WP): studentization 권고. MoneyLab 단일 기준값 futility에 대한 직접 검증은 없음 | HYPOTHESIS | V-1 |
| bootstrap statistic | basic(hybrid): p = (1 + #{boot_b − m + δ ≤ m})/(B + 1) (`procedures.py:163`) | 같음 | 직접 근거 없음 | HYPOTHESIS | V-1 |
| stationary bootstrap | 기하 block, 순환, 마지막 block 절단 (`src/moneylab/research/stats.py:187`) | 같음 | S10 ABSTRACT_ONLY | HYPOTHESIS | V-3 |
| block length | `mean_block: float = 20.0` 고정 (`src/moneylab/research/v06/montecarlo.py:137`), 창 365–2227일 | 짧은 창에서 초과기각이 가장 큼 | S01(Tier 1): 분산 추정 MSE 기준이며 test size 기준이 아님. S13 UNVERIFIED_CANDIDATE | HYPOTHESIS | V-3 |
| truth precision | 400년 표본 경로 하나로 calibration (`montecarlo.py:279`, :312; 400은 `montecarlo.py:95` `TRUTH_YEARS = 400`) | 같은 θ에서도 DGP별 confirmatory 기각률 차이(예: θ=0.7에서 0.069/0.116) | 해당 없음 | HYPOTHESIS | V-4 |
| finite sample | confirmatory 2227일, holdout 914일 (`montecarlo.py:161-162`), forward는 `SimulationCalendar`(`montecarlo.py:183`) | 가장 짧은 forward 12개월 창에서 초과기각이 가장 컸다 (RESEARCH-01 report §5.2) | 일반론만 있음 | HYPOTHESIS | V-8 |
| dependence / volatility clustering | 지난 60일 부호에 따른 모멘텀 피드백 drift (`src/moneylab/research/v06/synthetic.py:83`). garch_t는 GARCH(1,1) (이 부분은 GIT_VERIFIABLE이 아니라 SYNTHETIC / CLAUDE_REPORTED, RESEARCH-01 report §2.2) | Normal DGP에서도 초과기각 | S02 Table 1(GARCH DGP, 두 Sharpe 차이) | HYPOTHESIS | V-5 |
| heavy tails | garch_t는 t4 innovation (이 부분은 GIT_VERIFIABLE이 아니라 SYNTHETIC / CLAUDE_REPORTED, RESEARCH-01 report §2.2) | Normal DGP에서도 초과기각 | S02 Table 1(두 Sharpe 차이) | HYPOTHESIS | V-5 |

## 6. Multiple-testing decision structure

네 가지 문제를 나눈다.

| 문제 | 현재 상태 | 근거 |
|---|---|---|
| 개별 p값의 타당성 | 현재 futility p값은 반보수적(SYNTHETIC) | RESEARCH-01 report §5 |
| FWER 통제 | Holm·Bonferroni는 개별 p값이 귀무에서 타당하다는 전제 아래 FWER를 통제한다. 전제가 깨져 있으면 FWER 통제 보장을 적용할 수 없다. 실제 FWER가 반드시 α를 넘는다는 뜻은 아니며 따로 평가해야 한다 | S05(Tier 2 WP) §2.3, S07(Tier 2 NBER WP). S09 Holm 원문은 ABSTRACT_ONLY |
| 검정력 | StepM은 joint dependence를 활용해 Holm보다 검정력을 높일 수 있는 후보 | S05 |
| data snooping / 최선 모형 선택 | RC·SPA는 "family의 최선이 benchmark를 이기는가"라는 별도 질문 | S06(Tier 2 WP). S08 White 원문은 UNVERIFIED_CANDIDATE이며, RC 서술은 S05·S06의 2차 서술 |

| 방법 | 다루는 문제 | MoneyLab에서의 위치 | 상태 |
|---|---|---|---|
| Holm (현재) | FWER (개별 p값 타당 전제) | D3(futility), S·S_F family(`procedures.py:254`, :266) | 현행. 개별 p값의 타당성을 복구하지 않는다 |
| Romano–Wolf StepM | FWER + 검정력 | Holm 대체 후보 | 후보. 채택하지 않음 |
| Hansen SPA | data snooping | S family 대안 후보 | 후보. 채택하지 않음 |
| White Reality Check | data snooping | 같음 | 후보. 원문 미검증. 채택하지 않음 |

MoneyLab과의 연결 (INFERENCE):
- D3의 Holm 적용 여부는 개별 futility calibration 이후의 문제다.
- D4·D5의 S_F Holm은 futility가 아니라 efficacy 쪽이다. 이 축의 MC-V06 오류율 특성은 이 문서가 인용하는 범위(RESEARCH-01 report)에 정리되어 있지 않으므로, 여기서 그 특성을 주장하지 않는다. StepM·SPA는 이 축의 비교 후보일 뿐 채택하지 않는다.

## 7. Procedure fork A vs B

이 문서는 A/B를 선택하지 않는다. 선택은 downstream 사용자 결정이다.

| 항목 | 경로 A: 현재 통계 절차 유지 | 경로 B: 절차 변경 + 사전등록 validation |
|---|---|---|
| required evidence | 아래 "A의 최소 evidence requirement" | 후보 절차의 운영 특성(V-1~V-8 중 해당 항목), 사전등록된 합격 기준 아래의 결과, 수식 수준 검증 또는 참조 구현 교차검증(§10) |
| benefits | MC-V06 특성을 그대로 활용할 수 있다. 코드 변경이 없다 | size 왜곡을 줄일 가능성이 있다(CANDIDATE) |
| risks | 이 경로를 고르면 알려진 반보수성을 안은 채 고정하게 된다. 경계 판정이 truth 정밀도와 DGP 요인 혼재에 제한된다 | 계산 비용, 후보 절차 구현 위험, 새 MC의 사전등록 부담. 후보가 개선을 보이지 않을 수 있다 |
| stale / insufficient가 되는 것 | MC-V06의 truth SE(약 0.05)와 DGP 요인 혼재 때문에 경계 수치의 정밀도가 부족할 수 있다 (INFERENCE) | 절차를 바꾸면 MC-V06 operating characteristics가 BT4 절차를 더 이상 기술하지 못한다 (BT4-RESEARCH-01 Work Order DESIGN_CONTRACT R5, `docs/tasks/BT4-RESEARCH-01/WORK_ORDER.md:190`) |
| required downstream work | A의 최소 evidence를 채우는 작업(재측정을 포함할 수 있음), 그다음 freeze | statistical validation(§11), 필요하면 engine/risk-policy validation, 그다음 freeze |
| freeze prerequisites | 반보수성을 허용할 합격 규칙의 사전 정의와 그 규칙 아래의 판정, §12의 공통 전제 | 사전등록된 validation의 완료와 보고, 채택 절차의 구현 검증, §12의 공통 전제 |

**A의 최소 evidence requirement** (정의만 하며 threshold는 정하지 않는다):
1. **truth 정밀도:** 경계 판정에 쓰는 truth Sharpe의 불확실성이 판정 기준에 비해 무시할 수 있는 수준임을 보여야 한다. MC-V06의 `truth_se_sharpe`는 0.05였다(RESEARCH-01 report §2.2). 필요한 수준은 사용자가 정한다.
2. **DGP 요인 분리:** GARCH 효과와 꼬리 효과가 섞인 현재 비교로는 요인별 특성을 말할 수 없다. 2×2 요인 구조(V-5) 또는 그에 준하는 근거가 필요한지 결정해야 한다.
3. **반보수성 허용 규칙:** 관찰된 futility 반보수성을 어떤 합격 규칙 아래에서 허용할지(예: "모든 경계 시나리오에서 기각률 ≤ 명목 + ε" 형태)를 결과를 보기 전에 정해야 한다. ε 값은 이 문서에서 정하지 않는다.

"경로 A를 고르면 validation을 생략할 수 있다"는 규칙은 두지 않는다. A도 위 최소 evidence를 채워야 하며, 그 과정에서 재측정이 필요할 수 있다 (INFERENCE).

## 8. DGP policy alternatives

현재 DGP 비교에는 volatility clustering(GARCH 유무), tail thickness(t4 vs Normal), edge calibration 값이 함께 바뀐다. 근거는 증거 등급별로 나뉜다: GIT_VERIFIABLE — `synthetic.py:83`은 모멘텀 edge 구조를 보여 준다. SYNTHETIC / CLAUDE_REPORTED — MC-V06에서 쓰인 구체 DGP 설정(GARCH 유무, t4 vs Normal)과 edge 값은 RESEARCH-01 report §2.2에 정리되어 있다. 이 문서는 정책을 선택하지 않는다.

| 정책 | 해석 | 장점 | 위험 | 검증 함의 | freeze 전제 |
|---|---|---|---|---|---|
| worst-case-over-DGP | 고려한 DGP 중 가장 나쁜 값으로 판정 | 오류율에 보수적 상한 | DGP 목록 선택에 좌우됨. 검정력 손실. 목록 밖 DGP는 보장 안 됨 | DGP 목록과 요인 구조(V-5)를 사전등록해야 함 | DGP 목록 고정 |
| both-must-pass | 같은 기준이 두 DGP 모두에서 성립해야 PASS | 해석이 단순함 | DGP가 둘이면 worst-case와 비슷하게 동작할 수 있음. 비단조성이 있으면 불안정 | V-5와 V-4(경계 정밀도)가 필요 | 두 DGP의 정의 고정 |
| model-specific | DGP별로 따로 보고하고 종합 PASS 규칙을 두지 않음 | 정보 손실이 없음. 요인 혼재를 감추지 않음 | 사전등록된 판정 규칙이 없어 결정을 미룸. 사후 선택 위험 | 보고 형식만 필요하지만, 결국 D 선택 규칙이 따로 필요함 | 판정에 쓸 별도 규칙의 정의 |

## 9. Mode A+B / DSR / PBO classification

| 항목 | 분류 | 설명 |
|---|---|---|
| Mode A+B | DIAGNOSTIC_ONLY | MC harness의 탐색 트랙이며 초안 §11.3 판정표에 없다(RESEARCH-01 report §4 H). MC-V06에서 D3/D7 경계를 넘었다(SYNTHETIC / NOT_EVIDENCE, RESEARCH-01 report `docs/research_bt4_01_evidence_review.md:409`). 이 문서는 유지·제거를 결정하지 않는다. 유지 근거: 탐색 트랙 특성의 지속 관찰. 제거 근거: 비규범 수치와 규범 판정의 혼동 위험, 보고 복잡도 |
| DSR | DIAGNOSTIC_ONLY | **draft의 기존 보고 항목**이다(§2.8: draft:149, :336, :470, :642). draft 시도 수 9는 BT-4 freeze 전 값이며 이 문서에서 확정하지 않는다. selection bias 진단이며 개별 test size 보정이 아니다(S03, Tier 2 author manuscript) |
| PBO | PROPOSED_DECISION_ITEM | draft에 없다. 선택 과정의 overfitting 진단 후보이며 규범 규칙으로 채택하지 않는다(S04, Tier 2 author revised). 전략 4개라 해상도가 낮을 수 있다 (INFERENCE) |

**DESIGN_INVESTIGATION 정정:** DESIGN_INVESTIGATION 보고는 DSR을 "새 decision candidate"로 분류했으나, 이는 canonical repository와 맞지 않았다. canonical 분류는 위와 같이 기존 draft 보고 항목(DIAGNOSTIC_ONLY), draft 시도 수 9다.

## 10. Evidence gaps

RESEARCH-01 report §10.4의 gap을 설계 결정에 연결한다. 각 source의 status는 그대로다.

| gap | status (RESEARCH-01) | 영향받는 결정 | freeze를 막는가 (INFERENCE) |
|---|---|---|---|
| White (2000) | UNVERIFIED_CANDIDATE | RC 채택 여부(R-5, V-6) | RC를 채택하지 않으면 막지 않음 |
| Holm (1979) | ABSTRACT_ONLY | D3 | 막지 않음. 성질은 S05·S07(Tier 2)로 확인되고 D3의 특성은 MC로 측정 |
| Politis & Romano (1994) | ABSTRACT_ONLY | stationary bootstrap 기초(D1–D7) | 막지 않음. 경험적 타당성은 V-3·V-1로 대체 가능 |
| Politis & White (2004) | ABSTRACT_ONLY | V-3 | 막지 않음. 정정 관계는 S01로 확인 |
| Lo (2002) | 원문 미확보 | 없음 (권고 근거로 쓰지 않음) | 막지 않음 |
| Hall, Horowitz & Jing (1995) | UNVERIFIED_CANDIDATE | V-3 설계 입력 | 막지 않음. 설계 참고로만 쓰고 검증으로 대체 |
| 출판본 미확인 (S03–S07) | WP·저자 원고 | 해당 source에 기대는 권고 | 채택한 절차가 없으므로 지금은 막지 않음. 채택 시 확인 필요 |
| 수식 수준 미검증 | 텍스트 추출로 읽음 | 후보 절차 구현(studentized SE, SPA consistent p, StepM) | **후보 절차를 구현할 때는 막음.** 수식 검증 또는 `bashtage/arch` 참조 교차검증 필요. 설계 단계는 막지 않음 |

## 11. Validation requirements V-1~V-8

이 문서는 validation을 실행하지 않고 구조만 정의한다.

### 11.1 계층 구분

- **(A) statistical validation:** V-1~V-8과 관련 통계 절차 문제(futility, studentization, delta, block 길이, truth 정밀도, 2×2 DGP, 다중검정, 유한 표본). research 계층(`src/moneylab/research/v06/`)의 문제다.
- **(B) engine / risk-policy validation:** BT4-Q18, 위험 비율 대안(MC-V06은 비율 1.5만 평가, `docs/backtest_design.md:533`), D10에서 π 보정을 고르는 경우의 검증을 추적한다. Q18과 위험 비율은 engine/backtest 또는 risk-policy 문제인 반면, D10의 π 보정은 `research/v06/procedures.py`의 통계 검정 엔진의 FAR·수준 왜곡과 그 판정 반영 방식의 문제와 연결된다(`docs/backtest_design.md:594-599`).

두 validation group을 나누는 이유는 모든 항목의 code layer가 같아서가 아니라 검증 대상과 필요한 증거가 다르기 때문이다. (B) 안에서도 Q18·위험 정책과 D10의 π 보정은 실제 code layer가 서로 다를 수 있다(research ↔ backtest 런타임 import는 양방향 금지, `docs/backtest_design.md:510`) (INFERENCE). downstream task ID는 고정하지 않는다.

### 11.2 공통 요구

- **사전등록:** 후보 절차와 합격 기준은 결과를 보기 전에 사전등록한다. 절차 변경은 MC-V06 특성을 무효화하기 때문이다.
- **multiplicity 정책:** 여러 후보·시나리오·창 길이의 size를 함께 판정하는 규칙(예: 모든 경계 시나리오에서 동시 성립)을 사전에 정한다.
- **정밀도 범주:** MC SE(시나리오별 비율의 표준오차)와 truth SE(경계 정의의 정밀도)를 따로 정한다. MC-V06의 `truth_se_sharpe`는 0.05였다(RESEARCH-01 report §2.2). 경계 판정에는 MC SE뿐 아니라 truth SE가 함께 영향을 준다 (INFERENCE).
- **MC-V06 고정값은 참고만 한다:** R_OUTER = 10,000, B_BOOT = 9,999, K_RAND = 9,999, TRUTH_YEARS = 400, TARGET_MAX_MC_SE = 0.005, ADAPTIVE_STOPPING = PROHIBITED (`docs/tasks/MC-V06/WORK_ORDER.md:87-92`)는 MC-V06 계약의 값이며 새 validation에 자동으로 상속하지 않는다.
- **이 문서에서 정하지 않는 값:** ε, 목표 MC SE, 목표 truth SE, 정확한 R_OUTER·B_BOOT·K_RAND·TRUTH_YEARS, DGP 정책, 우승 절차.

### 11.3 항목별 구조

| V | hypothesis / H0 vs H1 | estimand | DGP 요인 | 표본 길이 | 후보 절차 | primary metric | 합격 기준의 형태 |
|---|---|---|---|---|---|---|---|
| V-1 | H0: 경계 size ≤ 명목 + ε / H1: 초과 | 경계에서 P(p ≤ α) | V-5 요인, edge 크기 | confirmatory·holdout·forward 창 길이 | 현행 basic, studentized(block SE) | 경계·귀무 내부 기각률, 대립 검정력 | 모든 경계 시나리오에서 기각률 ≤ α + ε |
| V-2 | δ 정의에 따른 size 차이 | 같음 | 같음 | 같음 | plug-in δ̂, 대안 정의 | 같음 | 같음 |
| V-3 | block 규칙에 따른 size·검정력 | size, 검정력 | 같음 | 같음 | 고정 20, 창별 data-driven | size, 검정력 | size 조건 아래 검정력 비교 |
| V-4 | truth 정밀도가 경계 판정에 주는 영향 | truth 오차의 기여 | 같음 | 같음 | truth 경로 길이 증가 또는 다른 truth 정의 | truth SE, 기각률 변화 | truth SE ≤ 목표 |
| V-5 | GARCH·꼬리 요인 효과 | 요인별 지표 | 2×2 + 모멘텀 edge | 같음 | 현행(필요하면 후보) | 요인별 기각률 | §8에서 고른 정책의 규칙 |
| V-6 | 개별 보정 후 FWER 절차 비교 | FWER, 검정력 | 같음 | 확증·forward | Holm, StepM, SPA | FWER, 평균 검정력 | FWER ≤ α 아래 검정력 비교 |
| V-7 | A+B 보고의 정보 가치 | A+B 트랙 특성 | 같음 | forward | A, A+B | 경계 위반률 | 보고 형식 결정 (판정 아님) |
| V-8 | 창 길이별 size | 길이별 기각률 | 같음 | 창 길이 전부 | 현행, 후보 | 기울기 | 길이별 기준 적용 |

### 11.4 계층 (B) 항목의 구조

| 항목 | 질문 | 필요 시점 |
|---|---|---|
| BT4-Q18 | 엔진의 gap-free 창과 사전등록 종가 정의의 차이가 판정에 주는 영향 | freeze 전 처리 방식 결정 필요 |
| 위험 비율 대안 | 비율 1.5 외 값의 위반률 | 1.5 외 값을 고려하는 경우에만. MC-V06 격자는 위험 비율 1.5만 평가했다(`docs/backtest_design.md:533`) |
| D10 π 보정 | π 기준 보정의 특성 | D10에서 π 보정을 고르는 경우에만 (`docs/backtest_design.md:682`: "시뮬레이션 필요, 별도 승인") |

### 11.5 D8 / D9의 약한 의존

- D8은 segment 수익과 구간 경계 비용 처리에 영향을 준다(draft:526).
- D9는 holdout 길이와 H_end에 영향을 준다(draft:208, `montecarlo.py:162`).
- 따라서 downstream 사전등록에서 이 둘을 **고정 가정**으로 둘지 **요인**으로 둘지 정해야 한다. 이 문서는 D8·D9를 결정하지 않는다.

## 12. Freeze prerequisites

BT-4 freeze 전에 필요한 것 (INFERENCE, 결정값은 정하지 않음):

1. **inventory 정리:** §2의 모든 항목에 상태가 있어야 한다. alias(G1=U2, G7=U9)는 하나의 이름으로 정리한다.
2. **U4a 해결:** provenance와 정의를 확인한다(§2.9).
3. **경로 선택:** A/B 중 하나를 사용자가 고른다(§7). 각 경로의 freeze 전제를 채운다.
4. **NEEDS_VALIDATION 항목:** 해당 validation(또는 경로 A의 최소 evidence)이 완료·보고되어야 한다. 합격 기준은 결과보다 먼저 사전등록되어야 한다.
5. **DGP 정책:** validation 합격 규칙에 쓰려면 validation 전에, 쓰지 않으면 freeze 전에 정한다(§8).
6. **NEEDS_POLICY_DECISION 항목:** D4·D5(통계량 불변 조건 확인), D8, D9, D10, U2/G1, U4–U6, U9/G7, G2–G6, 위험 정책 항목(§2.5), DP2–DP4를 사용자가 정한다.
7. **BT4-Q18:** 처리 방식(해결, 한계로 명시 등)을 정한다.
8. **DSR 시도 수:** draft 값 9를 그대로 고정할지 확인한다.
9. **고정 산출물:** 사전등록·config SHA (`docs/backtest_design.md:663`의 BT-4 행 산출물).

## 13. Proposed downstream task boundaries

task ID는 고정하지 않는다. 각 단계의 경계만 적는다 (INFERENCE).

| 단계 | 결정할 수 있는 것 | 결정하면 안 되는 것 |
|---|---|---|
| 설계 (이 task) | inventory, 분류, 의존 관계, 경로 비교, 검증 구조 | 모든 결정값, 채택, threshold |
| statistical validation (계층 A) | 사전등록된 후보 절차의 운영 특성 측정 | 결정값과 채택. 후보 절차 구현이 필요하면 그 범위를 해당 task의 Work Order로 정해야 함 |
| engine / risk-policy validation (계층 B) | BT4-Q18, 위험 비율 대안, D10 π 보정의 특성 측정 | 결정값과 채택 |
| freeze (= BT-4) | D1–D10, U, G, 위험 정책, DP2–DP4, Q18 처리, 사전등록·config SHA 고정 (사용자 결정) | 실데이터 개봉 |
| freeze 이후 구현 | 고정된 절차를 판정 코드에 반영 | 사전등록 변경 |

경로 A를 고르더라도 §7의 최소 evidence 작업이 별도로 필요할 수 있다.

## 14. Unresolved user decisions

| # | 결정 | 관련 절 |
|---|---|---|
| 1 | 절차 경로 A/B, 그리고 validation을 두 경로 비교로 설계할지 | §7 |
| 2 | statistical validation의 범위와 후보 절차 집합 | §11 |
| 3 | DGP 정책과 그 결정 시점 | §8 |
| 4 | 합격 기준의 값(ε, 목표 MC SE, 목표 truth SE)과 계산 예산 | §11.2 |
| 5 | 후보 절차를 research 계층에 구현할 범위와 task | §13 |
| 6 | D8·D9를 validation에서 고정 가정으로 둘지 요인으로 둘지 | §11.5 |
| 7 | engine / risk-policy validation이 필요한지 (Q18 처리, 비율 대안, D10 선택에 따라) | §11.4 |
| 8 | U4a의 provenance와 정의 | §2.9 |
| 9 | PBO를 진단 항목으로 추가할지 | §9 |
| 10 | Mode A+B를 향후 MC 보고에 남길지 | §9 |
| 11 | DSR 시도 수 9의 확인 | §2.8 |
| 12 | D10의 선택지 | §2.2 |
| 13 | 세율 τ, D, Y0: 현재 BT-4 handoff 목록에 없다 (`docs/tasks/BT-3E/WORK_ORDER.md:286`). 분류 `OUTSIDE_CURRENT_BT4_HANDOFF`, `RELATED_UNRESOLVED_INPUT`. 이 task에서 값이나 범위를 정하지 않는다 | – |
| 14 | U8 행의 설명이 현재 상태와 맞지 않는 문제의 정리 방식 | §2.3 |
