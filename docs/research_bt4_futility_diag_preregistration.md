# BT4-FUTILITY-01 사전등록: MC-V06 futility 경계 과다기각 원인 진단 MC (DIAG)

상태: PREREGISTERED (C2 커밋 시 고정). 고정 후 변경은 새 study다.
증거 등급: 이 study의 모든 수치 결과는 SYNTHETIC / NOT_EVIDENCE다.

## 0. 식별

- STUDY_ID: BT4-FUTILITY-01-DIAG
- WORK_ORDER: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md @ 7ac09a674e68cbc95dd5c934f2d3580939fd02f0 (sha256 c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b, blob bccc08b79518d2bbd2244d702ee8b2c3fa3831f9)
- CANONICAL_BASE: 15957207a592e062aaa51a6610b7e748ce136ca0 (tree 8dbdb68d1cf2948d3e7b497c17b563eb416fc55d)
- CONFIG: configs/bt4_futility_diag.toml (같은 C2 커밋, sha256은 C2 보고에 기록)
- 우선순위: 이 문서와 Work Order가 다르면 Work Order가 앞선다. 이 문서는 Work Order가 사전등록에 위임한 값만 정한다.

## 1. 이번 사전등록의 결정 (사용자 승인: G2A-1 Gate Authorization)

- A1 BASE_SEED = 20261029 (저장소 관례 YYYYMMDD, Work Order C1 커밋일). MC-V06 seed 20261012, v0.4 seed 20261006과 다르다.
- A1-c: 이름공간 문자열 충돌은 STOP. 32비트 파생 seed 값 충돌은 보고 전용이며, 충돌 건수, 충돌 입력 tuple, 정렬 목록 sha256을 기록한다(§3).
- U6: CORE 부산물은 Work Order대로 포함한다. G5X–G7X EXPLORATORY는 §7에 정의된 항목만 포함한다.
  data-driven 블록과 S1 + data-driven은 Work Order에 정의된 식이 없으므로 EXCLUDED_FROM_THIS_STUDY다.
- U8: 경로 A 추정량 블록은 이번 사전등록에서 제외한다. r̂(V0)(E1-θ0.7 경계 기각률)은 CORE 부산물로 기술 통계로만 보고하며, 경로 A의 채택·검증·허용을 주장하지 않는다.
- N2 허용 범위: §6
- F1 수치 정책: §5
- P2 spell 규칙: §7

## 2. 고정 입력 (MC-V06 canonical run에서 읽음)

출처: C:/MoneyLab-mc-v06-full-run/data/processed/research_v06_sim/mc_v06_full_2d6ed0a/16_normal_M60_+0p7_attempt1/
- manifest.json sha256 = 2025f9aace9960f14efcbef1543d3eb719124b114bef86f4fcff27c1b3b3acb2
- scenarios/normal_M60_+0p7/summary.json sha256 = f5680e8abdbaa06a77c1bd8d01b6060c76865e0261ab264c8739f6ac347fc613
- MC-V06 seed = 20261012. 파생 규칙과 rep·truth seed 규칙은 manifest `seeds` 항목 그대로
- e_cal (edge_annual) = 0.728515625
- SR_ach (achieved_sharpe) = 0.70007463504927, 잔차 SR_ach − θ = 7.463504927e-05 (|잔차| ≤ 10⁻³)
- truth_years = 400, truth_se_sharpe = 0.05
- 이 값들은 summary.json의 `scenario.calibration`에서 읽었다(manifest의 `scenarios[].dgp.edge_annual`은 보정 전 값 0.0이다). 기각률 등 결과 항목은 이 사전등록의 입력으로 쓰지 않는다.
- UNVERIFIED: run 디렉터리의 SHA256SUMS와의 대조는 하지 않았다.
- DC14 재현 검사: 구현 단계에서 MC-V06 seed 규칙으로 `montecarlo.resolve`를 재현해 e_cal과 SR_ach가 위 값과 같은지 확인한다. 다르면 STOP

## 3. Seed

- BASE_SEED = 20261029. 파생은 Work Order DC10 그대로: stats.derived_seed(BASE_SEED, namespace, cell, str(rep), window, rule)
- 이름공간: "FUTDIAG", "FUTDIAG-PILOT", "FUTDIAG-SIGMA", "FUTDIAG-X", "FUTDIAG"+"v4eval", "FUTDIAG-TEST". 이름공간 문자열이 서로 다르고 "FUTVAL"과도 다름을 단언한다(위반하면 STOP).
- 파생 seed 값 충돌(보고 전용, STOP 아님): DIAG가 쓰는 경로·σ·평가 seed의 전체 목록을 config에서 결정적으로 나열해 manifest에 다음을 기록한다.
  (a) MC-V06 normal_M60_+0p7의 rep·truth seed와의 교집합 건수
  (b) DIAG 내부 중복 건수
  (c) 충돌한 각 값의 입력 tuple (namespace, cell, rep, window, rule)
  (d) 정렬 목록의 sha256

## 4. Work Order 계약 (VERBATIM)

다음 블록은 C1 Work Order(blob bccc08b79518d2bbd2244d702ee8b2c3fa3831f9)의 해당 줄을 바이트 그대로 복사한 것이다. 각 블록의 BEGIN·END 표지 사이 내용의 sha256은 표지에 적힌 원본 구간 sha256과 같아야 한다.

### 4.1 POLICY_VALUES

<!-- BEGIN VERBATIM WO@7ac09a6 L30-L47 sha256=fac75a1060fd8bb63d46b4cbdd7217e18966333b5c56a6ec3ef0576e0fa64a24 -->
POLICY_STATUS: APPROVED
POLICY_APPROVAL: 사용자 Gate Authorization 원문 인용(날짜와 승인자 표기는 원문에 없으므로 기록하지 않는다):
  "GATE_AUTHORIZATION: BT4-FUTILITY-01 G1b-1 WO@DRAFT_v0.3.2"
  "POLICY_DECISION: 사용자는 G1B_PREISSUE_LOCK의 B-1~B-8 수정안과 C. POLICY_APPROVAL_TABLE의 정책값을 승인한다."
  "DOCUMENT_STATUS: VERSION = 1.0 / STATUS = ISSUED / POLICY_STATUS = APPROVED"
- PRIMARY_ALPHA = 0.05
- SUPPORTED_FWER = 0.025, SUPPORTED_MULTIPLICITY = HOLM (1차 가설 5개)
- WEAKENED_FWER = 0.025, WEAKENED_MULTIPLICITY = BONFERRONI (가설당 0.005)
- MIN_EFFECT = 0.01, EFF = max(0.01, 0.25·(r_reference − 0.05))
- BOOTSTRAP_B = 1,999, CORE_R_MAX = 40,000
- PILOT_DISCORDANCE_CI = CLOPPER_PEARSON_ONE_SIDED_95
- SIGMA_CALIBRATION_R = 2,000
- V4_GAMMA_DELTA = 0.0025 (단측 하한 L_Δ의 비포함확률), V4_GAMMA_SIGMA = 0.0025 (σ 양측 구간의 비포함확률), V4_SIGMA_INTERVAL = LOG_ASYMPTOTIC_KURTOSIS
- S1_DEGENERACY_POLICY = PD-1..PD-6 (DC4.1)
- PILOT_STOP_THRESHOLDS: p_lo/p_hi 기각 판정 불일치 > 0.02, ND flag > 0.05, SD > 0.05 (G6에서만 평가)
- CORE_MAX_WALLTIME = 96 hours, CORE_MAX_WORKERS = 12, CORE_MAX_WORKER_HOURS = 1,152 (G1b 발행 승인으로 상한 고정)
- N1_TOLERANCE: atol = 10⁻¹²·v₀, rtol = 10⁻¹⁰ (TEST_GATES)
- EXPLORATORY_EXECUTION = SEPARATE_AUTHORIZATION, VALID_STUDY = SEPARATE_WORK_ORDER
<!-- END VERBATIM -->

### 4.2 DESIGN_CONTRACT

<!-- BEGIN VERBATIM WO@7ac09a6 L154-L270 sha256=3454ad68e5c3a97a0373daf1c2b0fcfe2f44fda40252c448bcbd655a06a99d48 -->
DESIGN_CONTRACT:

- DC1 범위
  - 1차 대상은 단일 E0 futility p값(`futility_pvalue` 형식)뿐이다. 초안 OR 규칙과 R1-A가 공통으로 쓰는 양이다.
  - `p_maxt`, R1-A, p2low, H1, H2, B1(K_RAND)은 범위 밖이다.
  - 전략은 M60, 비용 시나리오는 E0, 비용은 `montecarlo.Costs()` 기본값이다.

- DC2 V0 (현행 절차 anchor, procedures.py:163-171와 일치함을 G0에서 확인)
  - p = (1 + #{b : m*_b − m + δ̂ ≤ m})/(B + 1), δ̂ = θ·s/√365 (s는 n−1 분모)
  - 왼쪽 단측이다.
  - 경계는 c_t = r_t − m + δ̂ shift이고, 재표본에서 δ̂는 고정이다. basic 중심화다.
  - stationary bootstrap은 `stats._blocks`이다(DC4의 인덱스 체인 정의 참조).
  - 구현은 `procedures.futility_pvalue`, `futility_delta`, `bootstrap_means`를 import해 그대로 호출한다.

- DC3 변형 (같은 복제, 공통 난수)
  - CORE: V0, V0d(δ_true = θ·σ_pop/√365), S1(블록 20 인덱스 공유), V0b60(mean_block 60, 별도 인덱스)
  - σ_pop은 해석값(P 셀) 또는 4,000년 보정 경로의 E0 segment 수익률 sd(E 셀)다.
  - EXPLORATORY(G7X 전용, seed "FUTDIAG-X"): S2, data-driven 블록, S1 + data-driven, B = 9,999 anchor

- DC4 S1: 부분 studentization 진단 후보. g = μ − cσ(c = θ/√365) 추정량 전체의 변동을 반영하는 검증된 절차가 아니다.
  - S1은 δ̂ = c·s를 상수로 취급한다(ψ_t = r_t − m).
  - p = 1/max(mean_block, 1). _blocks와 같은 정의다.
  - 적용 범위: F1은 다음 인덱스 체인의 분포에서 정확하다.
    I_1 ~ U{1..n}. 서로 독립인 R_t ~ Bernoulli(p)에 대해 R_t = 0이면 I_{t+1} = (I_t mod n) + 1, R_t = 1이면 I_{t+1} ~ U{1..n}.
    m* = n⁻¹ Σ_{t=1}^{n} X_{I_t}.
    stats._blocks(균등 시작, 확률 1−p로 연장, 마지막 블록 절단)가 이 분포와 같다는 것은 INFERENCE이며 N1-c로 검증한다.
  - 순환 자기공분산: Ĉ(k) = n⁻¹ Σ_{j=1}^{n} (X_j − X̄)(X_{(j+k) mod n} − X̄), k = 0, …, n−1.
    분모는 n이고 X̄ = m이다. 순환 대칭 Ĉ(k) = Ĉ(n−k).
  - 원표본 (F1, 정의): ŝe² = Var*(m*) = n⁻¹ [ Ĉ(0) + 2 Σ_{k=1}^{K} (1 − k/n)(1 − p)^k Ĉ(k) ]
    - p < 1이면 K = min(n − 1, ⌈ln(10⁻¹⁵)/ln(1 − p)⌉), 절단 오차 상한은 2·Ĉ(0)·(1 − p)^{K+1}/(n·p).
    - p = 1(mean_block ≤ 1)이면 K = 0이고 ŝe² = Ĉ(0)/n이다. 모든 블록 길이가 1인 iid bootstrap이며 절단 오차는 0.
    - K = n − 1이면 데이터가 주어졌을 때 정확한 유한 표본 항등식이다(CLAUDE_REPORTED 도출, 문헌 표기와의 일치는 UNVERIFIED, N1-a와 N1-c로 검증).
  - (F2, 교차 검증용 동치식): Var*(m*) = n⁻¹ [ Ĉ(0) + Σ_{k=1}^{n−1} b(k) Ĉ(k) ],
    b(k) = (1 − k/n)(1 − p)^k + (k/n)(1 − p)^{n−k}.
    F1의 k항과 n−k항을 순환 대칭으로 합친 것이며 2배 인자가 없다. p = 1이면 모든 k < n에서 b(k) = 0이므로 F1과 같다.
    정의는 F1이고 F2는 N1-a에서만 쓴다. 절단은 F1에서만 허용한다.
  - 재표본: ŝe*_b² = c_L · n⁻² Σ_{j=1}^{J_b} (S*_j − L_j·m*_b)², c_L = (1 − Σ_j L_j²/n²)⁻¹
    - S*_j는 블록 j의 합, L_j는 그 길이(마지막 절단 블록 포함)다. 블록 길이가 가변이어도 c_L을 쓴다.
    - 블록 길이가 모두 같으면 c_L = J/(J−1)이다. p = 1이면 c_L = n/(n−1)이다.
    - V(L) ∝ L 근사에서 E*[ŝe*² | L] = Var*(m* | L)이고, E*[m* | L] = m이므로 기댓값 수준에서 ŝe²와 추정 대상이 같다(INFERENCE). 2차 성질은 UNVERIFIED다.
  - 통계량: T = (m − δ̂)/ŝe, T*_b = (m*_b − m)/ŝe*_b
  - 동등성 조건: 모든 b에서 ŝe*_b를 ŝe로 고정하면 T*_b ≤ T ⇔ m*_b − m ≤ m − δ̂이므로 p_S1 = p_V0(N1-d).
  - 근거 등급: 랜덤 길이 블록 bootstrap-t의 2차 성질과 단일 기준값 futility 검정에 대한 직접 문헌은 UNVERIFIED / HYPOTHESIS다.

- DC4.1 퇴화 정의와 정책 (PD-1..PD-6, POLICY_VALUES)
  - 표본 퇴화 SD: s = 0 또는 ŝe = 0. p_S1 = 1(DEGENERATE_SAMPLE)
  - 재표본 퇴화 RD: J_b < 2 또는 ŝe*_b ≤ 10⁻⁶·ŝe. 복제당 RD 수를 d라 한다.
  - 근접 퇴화 ND: ŝe*_b < 0.25·ŝe. 비율을 기록하고 복제당 1%를 넘으면 flag한다. 하한은 두지 않는다.
  - PD-1: 1차 S1 p는 p_hi = (1 + #{정상 b : T*_b ≤ T} + d)/(B + 1)이다(RD를 T*_b = −∞로 셈, 검정 자체로는 보수적).
  - PD-2: 모든 복제에서 p_lo = p_hi − d/(B + 1)(RD를 +∞로 셈), d, SD 여부, ND 비율을 기록한다. 어떤 퇴화 처리에서도 p_S1 ∈ [p_lo, p_hi]다.
  - PD-3: V-1 판정은 H-V1 정의(D1_lo, D1_hi)를 따른다.
  - PD-4: V-2는 SD 복제를 뺀 대비를 EXPLORATORY 민감도로 보고한다. 1차 판정 규칙은 그대로다(SD일 때 V0d가 p = 1/(B + 1)로 기각하는 것은 규칙상 정상 동작).
  - PD-5: 퇴화 STOP은 G6에서만 평가한다. E1 f12·f36에서 p_lo/p_hi 기각 판정이 갈리는 복제 > 0.02, ND flag 복제 > 0.05, 또는 SD 복제 > 0.05이면 STOP_FOR_USER_DECISION
  - PD-6: 본 실행 중에는 퇴화를 이유로 멈추지 않고 비율만 보고한다.

- DC5 S2 (EXPLORATORY 전용)
  - ψ_t = (r_t − m) − c·((r_t − m)² − s²)/(2s)
  - 4차 적률이 유한해야 하며, t4 innovation에서는 이론 근거가 없다.

- DC6 DGP 셀
  - CORE
    - E1-θ0.7: normal_M60 피드백(`synthetic.DGP(garch_alpha=0, garch_beta=0, t_df=None, edge_kind="momentum", edge_lookback=60)`). edge는 4,000년 보정 경로(FUTDIAG)에 `montecarlo.calibrate_edge`로 맞춘다.
    - P0-θ0.7: iid Normal, 항상 노출, 일 sd = 0.70/√365, 일 평균 = θ·sd/√365
    - V-4 평가: MC-V06 `normal_M60_+0p7`의 e_cal(DC14)
  - EXPLORATORY: P1(iid Bernoulli 0.5 노출), P2(2상태 Markov, spell은 G6에서 CORE pilot E1 M60 포지션 평균으로 고정), E2(garch_t_M60), E1-θ0.3, P0-θ0.3, E1-int(truth SR 0.7, θ 0.5), holdout 914일 창

- DC7 창 (`montecarlo.Layout()`, `SimulationCalendar()` 기본값과 일치)
  - conf = [122, 2349) (2227일)
  - f12 = [3323, 3688) (365일), f24는 731일, f36은 1096일. f0 = 3323에서 시작하는 중첩 창이다.
  - conf와 f12는 겹치지 않는다(사이 974일).
  - P 셀도 같은 경계와 `total_days`를 쓴다.

- DC8 α
  - 1차 α: 모든 1차 대비의 기각 지시변수 I_v는 α = 0.05(PRIMARY_ALPHA)에서 정의한다.
  - EXPLORATORY α: 같은 CORE 기록에서 α = 0.025(D7 α/2)와 α = 0.10(D2)의 기각률과 대비를 추가 비용 없이 계산해 EXPLORATORY로만 보고한다. 1차 라벨, Holm, Bonferroni에 쓰지 않는다.

- DC9 반복 축 (MC-V06 값을 상속하지 않음)
  - CORE: R_c는 DC12, B = 1,999. E1 보정 경로 4,000년. V-4 평가 경로 4,000년 1개. σ 보정 R_σ = 2,000
  - EXPLORATORY: R = 5,000, B = 1,999(anchor만 9,999)
  - K_RAND는 쓰지 않는다.
  - TARGET_MAX_MC_SE: 기각률 ≤ 0.005, 짝지은 차이 ≤ 0.0035
  - ADAPTIVE_STOPPING = PROHIBITED

- DC10 seed
  - base seed는 G2a에서 정한다(A1).
  - 파생은 `stats.derived_seed(base, <namespace>, cell, str(rep), window, rule)` 형식이다.
  - 이름공간: "FUTDIAG"(CORE 본 실행과 보정), "FUTDIAG-PILOT", "FUTDIAG-SIGMA", "FUTDIAG-X", "FUTDIAG"+"v4eval", "FUTDIAG-TEST"(테스트 전용, N1-c 등)
  - "FUTVAL"과 MC-V06 seed 규칙은 쓰지 않으며, manifest에서 겹치지 않음을 단언한다.
  - 예외: e_cal 재현과 T3 parity 테스트는 MC-V06 seed 규칙을 읽기 목적으로만 쓴다.

- DC11 출력
  - `data/processed/research_v06_futility_diag/<run_id>/`에 `storage/atomic`으로만 쓴다.
  - 복제별 record: m, s, δ̂, δ_true, annual Sharpe, 변형별 ŝe와 p, S1의 p_hi·p_lo·d·ND 비율, SD 여부, 블록 규칙별 bootstrap sd, (EXPLORATORY) 선택된 블록 길이
  - 셀 기록: 보정 edge와 achieved SR, σ_pop
  - manifest, SHA256SUMS, execution.json을 쓴다. execution.json을 뺀 파일은 worker 수와 무관하게 바이트가 같아야 한다.
  - pilot summarize는 nuisance 값(불일치 수, 시간, 퇴화 비율, spell, σ)만 출력하고 효과 수치는 출력하지 않는다.

- DC12 R 산정 (G6, 1회)
  - z는 `statistics.NormalDist().inv_cdf`로 정확히 계산한다. z_{1−0.005} = 2.575829, z_{0.80} = 0.841621, (합)² = 11.6790(Holm 최악 단계 0.025/5)
  - π_U = Clopper–Pearson 단측 95% 상한(x_disc, 200). stdlib `math.comb` 이항 누적확률을 bisection으로 푼다. V-1은 x_disc = max(x_disc^lo, x_disc^hi)를 쓴다(nuisance, 보수적).
  - R_c = 1,000 단위 올림(max(10,000, ⌈(z_{0.995} + z_{0.80})²·π_U/0.01²⌉, ⌈π_U/0.0035²⌉))
  - 검정력 80%는 Holm 최악 단계 기준 유의성 부분만이다. 참 효과 = EFF이면 SUPPORTED 전체 확률은 약 50%다.
  - 0.01은 정책값(MIN_EFFECT)이다.
  - R_c > CORE_R_MAX(40,000)이면 STOP한다. R_MAX는 설계 가정 위반과 예산 가드다.
  - 입력은 pilot 불일치 수뿐이다. 계산은 G6에서 1회만 하고, 다시 계산하거나 결과를 보고 바꾸지 않는다.

- DC13 라벨
  - 가설 수준: SUPPORTED / WEAKENED / INCONCLUSIVE(사유 코드 포함: DEGENERACY_AMBIGUOUS, APPROX_OUT_OF_RANGE)
  - 후보 수준에서 DIAG가 줄 수 있는 최고 라벨은 VALIDATION_CANDIDATE다. VALIDATED와 calibrated는 VALID Work Order에서만 판정할 수 있다.

- DC14 V-4 입력 (e_cal, SR_ach, σ_conf 보정)
  - e_cal과 SR_ach: MC-V06 manifest에 있으면 그 값을 쓰고, 없으면 MC-V06 seed 규칙으로 `montecarlo.resolve`를 재현한다(T12). 재현값이 manifest와 다르면 STOP한다.
  - σ_conf 보정
    - e_cal DGP로 R_σ = 2,000 복제(FUTDIAG-SIGMA)를 돌려 conf 창 annual SR_hat의 표본 sd σ̂를 구한다.
    - 구간 [σ_L, σ_U] = exp(log σ̂ ∓ z_{1−0.00125}·√((κ̂ − 1)/(4R_σ))), z_{1−0.00125} = 3.023341, κ̂는 표본 첨도(양측 합 γ_σ = 0.0025)
    - G5에서 실행하고 G6에서 고정한다. 본 결과를 본 뒤 바꾸지 않는다.
    - iid 값 √(365/2227) ≈ 0.405는 민감도로만 보고한다.
<!-- END VERBATIM -->

### 4.3 STATISTICAL_HYPOTHESES (판정 규칙, 다중성, ERROR_CLAIM_SCOPE, EXPLORATORY 포함)

<!-- BEGIN VERBATIM WO@7ac09a6 L274-L342 sha256=1a81f56c7a63829b9db0e44e27b48431f9fc9e4fa2e5f1cf24fcf2cf73b884f4 -->
공통 기호 (McNemar형 대비: V-1, V-2, V-3, V-8)
- I_v = 1{p_v ≤ 0.05}
- D̂ = (n₁₀ − n₀₁)/R
- SE_D = √((n₁₀ + n₀₁) − R·D̂²)/R
- 단측 p = 1 − Φ(D̂/SE_D)
- EFF = max(0.01, 0.25·(r̂_기준 − 0.05)). r̂_기준은 V-1·V-2·V-3에서는 r̂(V0), V-8에서는 r̂(f12)
- WEAKENED 상한: U_D = D̂ + z_{0.995}·SE_D

- H-V1 non-studentization
  - E1-θ0.7, f12. 대비: V0 대 S1. S1 지시변수는 p_lo와 p_hi 두 가지(DC4.1)
  - D1_lo = r(V0) − r(S1_lo), D1_hi = r(V0) − r(S1_hi). 복제마다 p_lo ≤ p_hi이므로 D̂1_lo ≤ D̂1_hi가 항상 성립한다.
  - 유의성·SUPPORTED: H0: D1_lo ≤ 0. 짝지은 McNemar형 SE_lo, 단측 p₁. Holm 가족의 V-1 p는 p₁이다. 효과 게이트는 D̂1_lo ≥ EFF
  - WEAKENED: U_D = D̂1_hi + z_{0.995}·SE_hi < 0.01. Bonferroni 가족의 V-1 구간
  - 두 판정은 하나의 V-1 가설을 방향별로 보수적으로 판정한 것이며 독립 가설이 아니다. 상호 배타적이다.
  - DEGENERACY_AMBIGUOUS는 보고용 사유 코드이며 판정을 바꾸지 않는다.
  - 해석 한계: SUPPORTED는 "평균의 se를 반영하면 과다기각이 줄어든다"는 뜻으로 한정한다(부분 studentization).
- H-V2 plug-in δ̂
  - E1-θ0.7, f12. 대비: V0 대 V0d. H0: D₂ ≤ 0. 부호를 함께 보고한다. SD 제외 민감도는 EXPLORATORY(PD-4)
- H-V3 block length
  - E1-θ0.7, f36. 대비: V0(블록 20) 대 V0b60. H0: D₃ ≤ 0
  - 블록 수를 맞춘 설계다(1096/60 ≈ 18.3, 365/20 ≈ 18.25).
- H-V8 finite sample
  - P0-θ0.7. 대비: V0의 r(f12) − r(conf). 두 창은 겹치지 않는다. H0: D₈ ≤ 0
  - 추가 조건: r̂(f12) − 0.05 ≥ 0.01
  - 해석 한계: iid에서 짧은 창의 초과를 보일 뿐이며 엔진 셀의 유한 표본 효과를 단독으로 증명하지 않는다.
- H-V4 truth calibration (독립 truth calibration 평가이며 McNemar 대비가 아니다)
  - 1차 대상: Δ = SR_eval − θ. SR_eval은 FUTDIAG "v4eval" 4,000년 경로에서 e_cal로 계산하며, 정의는 `_target_sharpe(path,"M60","E0")`, 단위는 연환산 Sharpe다.
  - 보고만: A = SR_eval − SR_ach, 잔차 = SR_ach − θ(|잔차| > 10⁻³이면 표시)
  - 추론은 MC-V06의 실현 보정을 조건으로 한다(SR_ach와 θ는 상수).
  - SE: 100년 batch 40개의 batch-means, t(39). 1차 고정이며 fallback은 없다. K = 20과 batch lag-1 상관은 민감도로만 보고한다.
  - 유의성: H0: Δ ≥ 0, 단측 t p. σ는 쓰지 않는다(σ > 0이면 ΔRej > 0 ⇔ Δ < 0).
  - 효과 함수: ΔRej(Δ, σ) = Φ(−z_{0.95} − Δ/σ) − 0.05. ∂/∂Δ = −φ/σ < 0, ∂/∂σ = φ·Δ/σ²(Δ의 부호를 따름)
  - 효과 게이트: min over σ ∈ [σ_L, σ_U] of ΔRej(Δ̂, σ) ≥ 0.01 (Δ̂ < 0이면 σ_U에서 최소, Δ̂ ≥ 0이면 통과 불가)
  - WEAKENED: L_Δ = Δ̂ − t_{39, 1−0.0025}·SE. ΔRej_max = max over {L_Δ} × {σ_L, σ_U} of ΔRej < 0.01
    - γ_Δ = 0.0025는 단측 하한 L_Δ의 명목 비포함확률이다.
    - γ_σ = 0.0025는 σ 양측 구간 [σ_L, σ_U]의 명목 비포함확률이다.
    - WEAKENED에 필요한 두 구간의 명목 비포함확률 합은 0.005(Bonferroni 가설당 몫)다.
  - 보고(설명용): U_Δ = Δ̂ + t_{39, 1−0.0025}·SE와 사각형 [L_Δ, U_Δ] × [σ_L, σ_U]의 꼭짓점 min·max.
    U_Δ와 ΔRej_min은 설명용이며, 같은 γ_Δ로 양측 동시 포함확률을 주장하지 않는다.
  - 근사 조건: |Δ̂|/σ_L ≤ 0.5. 벗어나면 INCONCLUSIVE(APPROX_OUT_OF_RANGE)까지만
  - EXPLORATORY: 설명 비율 ΔRej / (r_obs,conf − 0.05)(r_obs = MC-V06 기존값 0.116, SYNTHETIC). r_obs 기준식 ΔRej′ = r_obs − Φ(Φ⁻¹(r_obs) + Δ/σ). f12·f24·f36 창 값
  - 해석 제한
    - SUPPORTED는 "이 시나리오의 conf 창에서 모집단 SR이 θ보다 낮아 기각률이 0.01 이상 올랐을 수 있다"는 근거로 한정한다.
    - 과다기각 전체 설명, 다른 시나리오·창에 대한 일반화, calibrated, 인과를 주장하지 않는다.
    - WEAKENED는 이 시나리오의 conf 창에서 기여가 0.01 미만일 가능성이 높다는 뜻이며 다른 시나리오를 배제하지 않는다.

판정 규칙과 다중성 (총 0.05 = SUPPORTED 0.025 + WEAKENED 0.025, POLICY_VALUES)
- 유의성: 5개 1차 p(V-1은 p₁)에 Holm, FWER 0.025
- SUPPORTED: Holm 기각이고 효과 게이트 통과(V-1: D̂1_lo ≥ EFF. V-2·V-3: D̂ ≥ EFF. V-8: D̂ ≥ EFF와 추가 조건. V-4: 위 효과 게이트)
  - 효과 게이트는 α를 쓰지 않는다. 주장을 줄이기만 하며 자체 오류 보장은 없다.
- WEAKENED: Bonferroni, 가설당 0.005. V-1: D1_hi의 U_D < 0.01. V-2·V-3·V-8: U_D < 0.01. V-4: ΔRej_max < 0.01(γ_Δ = 0.0025 단측, γ_σ = 0.0025 양측)
- INCONCLUSIVE: 그 밖의 경우(사유 코드 포함)
- 합집합 한계로 P(거짓 SUPPORTED 또는 거짓 WEAKENED가 하나라도) ≤ 0.05. 표본 판정에서 SUPPORTED와 WEAKENED는 가설마다 상호 배타다.
- 여러 가설이 동시에 SUPPORTED일 수 있다. "원인 확정" 라벨은 없다.

ERROR_CLAIM_SCOPE (판정 규칙은 바꾸지 않고 오류 주장의 범위만 밝힌다):
- 명목 목표: SUPPORTED 가족 FWER 0.025(Holm), WEAKENED 가족 0.025(Bonferroni), 합집합 한계로 거짓 주장 전체 0.05. 모두 목표치다.
- 실제 한계(근사)
  - McNemar p는 정규 근사다.
  - V-4는 t(39) batch-means(batch 간 독립 근사)와 σ 로그 점근 구간(κ̂)을 쓴다.
  - ΔRej는 정규 위치이동 모형이며, 모형 오차는 어떤 구간에도 포함되지 않는다.
  - V-4는 MC-V06 실현 보정을 조건으로 한다.
  - 따라서 실제 오류율은 근사가 성립하는 범위에서만 목표와 같다(UNVERIFIED).
- SUPPORTED의 효과 게이트(D̂ ≥ EFF, ΔRej(Δ̂, σ_U) ≥ 0.01)는 점추정 기준이다. 포함확률이나 오류 보장이 없고 주장을 줄이기만 한다.
- WEAKENED는 해당 구간(McNemar 단측 U_D, V-4는 단측 L_Δ와 σ 양측 구간, 명목 비포함 합 0.005)의 포함확률 가정에 의존한다. V-4의 WEAKENED는 모형이 함축하는 ΔRej에 대한 주장이며, MC 기각률의 실제 변화를 직접 측정한 것이 아니다.

EXPLORATORY (보정 없음, 1차 라벨에 영향 없음)
- CORE 부산물: 1차가 아닌 창, α 0.025와 0.10, oracle 분해(위치 λ, 척도 κ, 결합 잔차, 복제를 반으로 나눈 cross-fitting), V-4 분해와 민감도, PD-4 민감도
- G7X 묶음: DC3·DC6의 EXPLORATORY 변형과 셀. 독립 seed이므로 CORE와 짝지은 비교를 하지 않는다.
<!-- END VERBATIM -->

### 4.4 TEST_GATES

<!-- BEGIN VERBATIM WO@7ac09a6 L357-L392 sha256=3ffe5ffc5c4cbdfc41ce1b060a5159ab2a348f9bc08385f81c6d49bcda34d125 -->
TEST_GATES:
- Python: `C:/MoneyLab-mc-v06/.venv/Scripts/python.exe`, `PYTHONPATH=C:/MoneyLab-bt4-futility-diag/src`(A9). 새 venv나 junction을 만들지 않는다. `moneylab.__file__`이 TARGET_WORKTREE 아래인지 확인한다.
- 허용 오차 함수: close(a, b; atol, rtol) ⇔ |a − b| ≤ atol + rtol·max(|a|, |b|). v₀ = Ĉ(0)/n
- `tests/test_v06_futility_diag.py`(오프라인, 결정적)
  - N1 구현 일치. N1-a·b·d·e가 실패하면 STOP_IMPLEMENTATION하고, 고친 뒤 N1 전체를 다시 실행한다.
    - N1-a 정의식 일치
      (i) 전체 F1과 F2: close(·, ·; atol = 10⁻¹²·v₀, rtol = 10⁻¹⁰). v₀ = 0이면 둘 다 정확히 0
      (ii) 절단 F1과 전체 F1: |F1_K − F1_full| ≤ 2·Ĉ(0)·(1−p)^{K+1}/(n·p) + 10⁻¹²·v₀. p = 1이면 둘 다 Ĉ(0)/n과 정확히 같아야 한다.
      (iii) F1 ≥ −10⁻¹²·v₀
      사례
      - 계열: iid, AR(1) ρ = 0.5, 노출 0.5 zero-inflated, 상수 계열(분산 0), 값 하나만 0이 아닌 계열, iid × 10⁻⁸와 × 10⁻¹⁵⁰
      - n ∈ {2, 365, 2227}, mean_block ∈ {1, 20, 60}
    - N1-b 재표본 se 직접 재계산
      ŝe*²와 c_L이 명시적 재표본 벡터와 블록 경계로 다시 계산한 값과 close(·, ·; atol = 10⁻¹²·v₀*, rtol = 10⁻¹⁰), v₀* = 재표본 Ĉ*(0)/n.
      가변 길이, 마지막 절단 블록, J_b = 1(degenerate 경로), mean_block = 1(c_L = n/(n−1)) 포함
    - N1-c 경험 분산 비교
      |F1 − Var_MC(m*)| ≤ 4·SE_MC. B = 200,000, SE_MC는 m* 4차 적률로 계산한다.
      계열은 iid, AR(1), zero-inflated이고 n = 365, mean_block ∈ {1, 20}.
      seed는 사전등록된 고정값 derived_seed(base, "FUTDIAG-TEST", "N1c", case)다(결정적).
      명목 거짓 실패 확률은 사례당 약 6×10⁻⁵다(정규 근사, 참고).
      실패하면 결과와 seed를 보존하고, 다른 seed로 재시도하지 않으며, 허용 오차를 조정하지 않고, STOP_FOR_USER_DECISION으로 보고한다.
    - N1-d: ŝe*를 ŝe로 고정하는 테스트 훅에서 S1 p와 V0 p가 bit 단위로 같음
    - N1-e: 퇴화 분기(SD, RD: J_b < 2, ŝe* ≤ 10⁻⁶·ŝe, ND 0.25 flag), p_hi·p_lo·d 계산(p_lo = p_hi − d/(B + 1))과 기록
  - N2 통계적 성질. 사전등록 범위 밖이면 STOP_FOR_USER_DECISION이다. 코드 오류로 단정하거나 추정량을 조용히 바꾸지 않는다.
    - N2-a: E*[ŝe*²]/ŝe²
    - N2-b: ŝe*의 변동계수, T*와 T의 분위수
    - N2-c: iid Normal 경계, n ∈ {365, 2227}, R = 2,000, B = 999에서 S1 기각률
  - T3 parity: 같은 경로와 MC-V06 seed 규칙, 작은 Procedure(bootstrap=99, draws=9)에서 `montecarlo._window_stats`의 M60 `p_fut`와 새 모듈 V0가 일치
  - DC7 경계 = `Layout.bounds`. P 셀 해석적 SR = θ
  - V-1: D̂1_lo ≤ D̂1_hi가 항상 성립하는지, 판정 상호 배타성(단위 테스트)
  - V-4: batch-means 함수, ΔRej 꼭짓점 min·max(부호 분기 단위 테스트), σ 구간 함수, Clopper–Pearson 상한(알려진 값)
  - seed 이름공간 분리. worker 1과 2의 출력 바이트가 같음
  - pilot summarize 출력에 효과 수치가 없음
- 전체 pytest, failed 0 / errors 0. stdlib과 architecture 테스트 통과
- `git diff --check`가 깨끗하고, 변경 파일 집합이 해당 gate의 ALLOWED_FILES와 같음
- MC-V06 `_SOURCE_FILES`의 base 대비 diff가 비어 있음
<!-- END VERBATIM -->

### 4.5 RESOURCE_BUDGET

<!-- BEGIN VERBATIM WO@7ac09a6 L411-L421 sha256=905d9ac6af168b0fa17369598f742d5b2b00ad7bea52ba510e06b515fef89207 -->
RESOURCE_BUDGET:
- CORE 상한(POLICY_VALUES, G1b에서 고정): wall-clock 96 hours, 12 worker, 1,152 worker-hour. G6이 예상 비용을 계산해 두 상한의 충족 여부를 판정한다. G7은 G6에서 확정한 조건으로 실행 승인만 받는다. 상한을 바꾸려면 ERRATA가 필요하다.
- EXPLORATORY 상한은 UNRESOLVED(N-6)이고 G7X에서 따로 승인한다.
- 모든 비용은 pilot 실측 전까지 ESTIMATE다(MC-V06 공학 추정에서 유도).
- 지배 요인: 블록 길이를 정하는 난수 호출(B × Σn × 인덱스 집합 수), 블록 합 누적, F1의 O(n·K), 4,000년 보정·평가, 병렬 효율
- G6 판정
  - 예상 worker-hour W = Σ_c R_c × t̂_c(pilot 95% 상한) × 1.3 / 3600 ≤ 1,152
  - 예상 wall-clock = W / (12·η̂) ≤ 96 hours. η̂는 pilot에서 잰 병렬 효율이다.
  - 두 조건을 모두 충족해야 한다. CORE R은 줄이지 않는다. 넘으면 STOP하고 계약 결정을 요청한다.
- EXPLORATORY 축소 순서(사전등록): ① E2와 P1 제외 ② B = 999 ③ R 5,000 → 3,000
- 실행 중 누적 시간이 예상의 1.5배를 넘으면 STOP한다. 이미 쓴 unit은 보존한다.
<!-- END VERBATIM -->

## 5. DC4 수치 처리 정책 (F1)

- v₀ = Ĉ(0)/n
- F1 ≥ 0이면 원래 값을 쓴다.
- −10⁻¹²·v₀ ≤ F1 < 0이면 F1_effective = 0으로 처리한다.
- F1 < −10⁻¹²·v₀이면 STOP_IMPLEMENTATION
- v₀ = 0이면 F1은 정확히 0이어야 한다.
- 허용 오차를 넓히지 않고, 다른 seed로 재시도하지 않는다.
- 정합성(새 규칙 아님): F1_effective = 0이면 ŝe = 0이므로 DC4.1의 SD로 처리한다(p_S1 = 1). N1-a (iii)은 그대로다.

## 6. N2 허용 범위

- N2-a
  - 사례: 계열 {iid, AR(1) ρ = 0.5, zero-inflated 0.5} × n {365, 2227} × mean_block 20
  - 사례마다 고정 표본 1개(seed FUTDIAG-TEST "N2a-data", case)에 B_N2a = 20,000 재표본(seed FUTDIAG-TEST "N2a-boot", case)
  - ρ̂ = mean_b(ŝe*_b²)/ŝe², SE_ρ = sd_b(ŝe*_b², ddof = 1)/(√B_N2a·ŝe²). ŝe²는 F1_effective
  - 판정 순서
    1. ŝe² = 0이면 N2A_UNDEFINED_DENOMINATOR
    2. ρ̂나 SE_ρ가 NaN 또는 Inf이면 N2A_INVALID
    3. 3·SE_ρ > 0.02이면 N2A_IMPRECISE
    4. [ρ̂ − 3SE_ρ, ρ̂ + 3SE_ρ] ∩ [0.95, 1.05] = ∅이면 N2A_FAIL
    5. 그 밖에는 N2A_PASS
  - 1–4는 PASS가 아니며 모두 STOP_FOR_USER_DECISION이다. 구현 오류로 단정하지 않는다.
- N2-b: REPORT_ONLY_DIAGNOSTIC
  - N2-a 사례마다 ŝe*의 변동계수
  - T*의 분위수 {0.01, 0.05, 0.5, 0.95, 0.99}와 N2-c 복제들의 T 분위수
  - 범위 없음. NaN·Inf는 그대로 보고한다.
- N2-c
  - iid Normal(DC6 P0 정의, 해석적 경계 SR = θ = 0.7), α = 0.05, R = 2,000, B = 999, n ∈ {365, 2227}
  - seed FUTDIAG-TEST "N2c"
  - 판정 경계는 반올림하지 않은 α ± 3·√(α(1−α)/R) = [0.035379810…, 0.064620190…]이며 n마다 판정한다.
  - 표시용 범위는 [0.0354, 0.0646]이다. 기각률 격자 k/2000에서 두 범위의 통과 집합은 k ∈ {71, …, 129}로 같다.
  - 범위 밖이면 STOP_FOR_USER_DECISION
- N1-c seed: FUTDIAG-TEST "N1c", case (Work Order TEST_GATES 그대로)

## 7. 실행 명세

- CORE 셀: E1-θ0.7, P0-θ0.7 (DC6). 창은 DC7, 변형은 V0, V0d, S1, V0b60 (DC3). B = 1,999
- E1 edge 보정: 4,000년 보정 경로(seed FUTDIAG "E1-θ0.7", "calib")에 calibrate_edge를 적용한다. G5에서 한 번 계산하고 G7에도 같은 edge를 쓴다. σ_pop은 같은 경로의 E0 segment 수익률 sd다.
- V-4 평가 경로: 4,000년(seed FUTDIAG "v4eval"), e_cal = §2 값. G7에서 계산한다.
- pilot(G5): CORE 셀마다 200 복제(seed FUTDIAG-PILOT), B는 본 실행과 같다. 출력은 nuisance만(DC11).
- σ 보정(G5): e_cal DGP, R_σ = 2,000(seed FUTDIAG-SIGMA), conf 창 annual SR_hat의 표본 sd와 표본 첨도 κ̂. 구간은 DC14
- G6: DC12(R_c), RESOURCE_BUDGET(예산 판정), PD-5. 계산은 1회만 하고 manifest에 고정한다.
- P2 spell 규칙(G6에서 1회 고정)
  - 입력: CORE pilot E1-θ0.7의 M60 포지션, conf 창
  - 잘린 첫·끝 spell을 제외한다.
  - 보유 spell과 현금 spell 각각 모든 pilot 복제를 합친 pooled 산술 평균을 구한다.
  - 양수 일수에 round-half-up(⌊x + 0.5⌋)을 적용한다.
  - 2상태 Markov 전이확률 = 1/rounded_mean ∈ (0, 1]
  - 남은 보유·현금 spell이 없으면 P2_UNDEFINED, 전이확률이 (0, 1] 밖이면 P2_INVALID다. 기본값으로 대체하지 않는다.
  - P2_UNDEFINED와 P2_INVALID는 P2(EXPLORATORY)에만 적용한다. G6 보고에 표시하고 G5X에서 P2를 실행하지 않으며 STOP_FOR_USER_DECISION이다. CORE G7은 막지 않는다.
- EXPLORATORY(G5X–G7X, 실행은 별도 승인, seed FUTDIAG-X, R = 5,000, B = 1,999)
  - 변형: S2(DC5). B = 9,999 anchor(E1-θ0.7의 V0만)
  - 셀: P1(iid Bernoulli 0.5 노출), P2(위 규칙), E2(garch_t_M60, θ0.7, 4,000년 보정), E1-θ0.3, P0-θ0.3, E1-int(truth SR 0.7, θ 0.5), holdout 914일 창(E1-θ0.7)
  - 축소 순서: Work Order RESOURCE_BUDGET
- EXCLUDED_FROM_THIS_STUDY: data-driven 블록, S1 + data-driven

## 8. 보고

- 1차 판정은 Work Order STATISTICAL_HYPOTHESES와 판정 규칙 그대로(§4.3)
- r̂(V0)는 기술 통계로만 보고한다(U8 제외).
- 모든 결과에 SYNTHETIC / NOT_EVIDENCE를 표시한다. VALIDATED / calibrated 표기는 금지한다.

## 9. 고정 조항

- pilot, σ 보정, 본 실행의 결과로 이 문서와 config의 어떤 항목도 바꾸지 않는다. 변경은 새 study다.
