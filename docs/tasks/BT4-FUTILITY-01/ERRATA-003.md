# ERRATA: BT4-FUTILITY-01 ERRATA-003

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-FUTILITY-01-ERRATA-003
TASK_ID: BT4-FUTILITY-01
TARGET_WORK_ORDER: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md @ 7ac09a674e68cbc95dd5c934f2d3580939fd02f0 (sha256 c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b)
PRIOR_ACCEPTED_ERRATA: ERRATA-001 (sha256 9fcac5a97605a85be68612ba4a465c5f24b8c5b5594f3a801ca5e551993d24bf, Ce 616ed51f257a8cfa2d2c080067b09258651930e9), ERRATA-002 (sha256 0ca8ab961af350b10a2660ca8ee7b8c4bfab2757ee2b6b1ae61ffcfeee7308fe, Ce 2eb876e02456405667f466a124f745b3dd4fba3c)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

규칙 분류: [A] 기존 계약 명시 / [B] 기존 계약에서 직접 도출 / [C] 신규 보충(수락 시 계약)

## ISSUE

ISSUE: WO:417-421은 G6 예산 판정식(W, 예상 wall-clock)과 실행 중 1.5배 STOP을 정하지만, t̂_c("pilot 95% 상한")의 통계량과 측정 범위, η̂의 정의·측정 조건, 보정·평가 시간과 W의 관계, 1.5배 STOP의 "누적 시간"과 "예상", 시간 값의 기록 위치와 수치 처리를 정하지 않는다. G6 공식은 사전등록 대상이다(WO:349). 그래서 G5 실행 전에, 결과와 무관하게 이 빈칸만 보충한다. 이 ERRATA 작성 시점에 pilot·보정은 실행되지 않았다.

## CHANGED_FIELDS

CHANGED_FIELDS (보충, 기존 문장 유지):
- RESOURCE_BUDGET G6 판정: t̂_c, η̂, T_wall의 정의와 측정 조건
- RESOURCE_BUDGET 실행 중 1.5배 STOP: 적용 대상, 누적 wall-clock, 시간 기록 불완전 상태
- DC11 출력: 비결정적 시간 값의 기록 위치
- DC12: 셀별 R_c 결합(직접 도출의 명문화)
- E2E_GATES G4c: smoke seed와 E1 TEST_FIXTURE 값

UNCHANGED_FIELDS (명시적으로 바꾸지 않음):
- [A] W = Σ_c R_c × t̂_c × 1.3 / 3600 ≤ 1,152 (WO:417), 예상 wall-clock = W / (12·η̂) ≤ 96 hours (WO:418). 식, 상수(1.3, 12, 1,152, 96), 비교 방향 "≤".
- [A] 두 조건을 모두 충족해야 한다. CORE R은 줄이지 않는다. 넘으면 STOP한다 (WO:419).
- [A] 실행 중 누적 시간이 예상의 1.5배를 넘으면 STOP하고, 이미 쓴 unit은 보존한다 (WO:421, config runtime_stop_multiple = 1.5).
- [A] DC12 R 산정식, π_U, z값, 1,000 단위 올림, R_c > 40,000이면 STOP.
- [A] pilot은 CORE 셀당 200 복제, B는 본 실행과 같다 (사전등록 §7:368). E1 edge는 G5에서 한 번 계산하고 G7에서도 쓴다 (§7:366). V-4 평가는 G7에서 한다 (§7:367).
- [A] execution.json을 뺀 파일은 worker 수와 무관하게 바이트가 같다 (WO:248, WO:406). 재개는 허용된다 (WO:405).
- POLICY_VALUES, STATISTICAL_HYPOTHESES, 판정·다중성, ERROR_CLAIM_SCOPE, DC1–DC14, ERRATA-001·002, 사전등록·config 파일.
- 이 ERRATA는 통계 판정 기준, 검정력 목표, 예산 상한, 예산식을 추가하거나 바꾸지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- R-1 t̂_c (복제당 계산 시간):
  - [B] 단위: 셀 c의 복제 1개당 초 (W 식에서 직접 나온다).
  - [C] 표본: 그 셀의 G5 CORE pilot 복제 200개 각각의 측정 시간 t_{c,1..200}.
  - [C] 측정 구간: worker 프로세스 안에서 복제 하나(경로 생성, 모든 창, 모든 변형, record 생성)의 시작과 끝을 같은 프로세스의 time.perf_counter()로 잰 차이.
    - 들어가지 않는 것: unit 파일 쓰기·검증, 프로세스 풀 생성·스케줄링·대기. 이 비용은 R-2의 T_wall에만 들어간다.
  - [C] 통계량: 평균의 단측 95% 신뢰상한
    t̂_c = mean(t_c) + t_{0.95, n−1} · sd(t_c, ddof = 1) / √n, n = 200
    - t 분위수는 `t_ppf`(futility_diag.py)로 계산한다. sd = 0이면 t̂_c = mean(t_c).
  - [C] 200개 중 하나라도 결측·비유한·음수이면 STOP_FOR_USER_DECISION. 값을 대체하거나 추정하지 않는다.
- R-2 η̂ (병렬 효율):
  - [C] η̂ = Σ_{c,r} t_{c,r} / (w · T_wall)
    - Σ t는 R-1에서 잰 pilot 두 셀 전체 복제 시간의 합, w는 pilot worker 수다.
  - [C] T_wall은 부모 프로세스 time.perf_counter()로 잰 pilot 복제 단계의 경과 시간이다.
    - 시작: 부모 프로세스가 pilot 복제 작업 실행을 시작하는 시점(init_run과 디렉터리 검사가 끝난 직후, 첫 unit의 프로세스 풀을 만들기 전).
    - 끝: 마지막 unit의 index 기록이 완료된 시점.
    - 포함: 프로세스 풀 생성, 작업 스케줄링, worker 대기, unit I/O, unit 검증, 마지막 index 기록.
    - 제외: init_run(run_spec·run_inputs 작성, 디렉터리 검사)과 마지막 manifest·SHA256SUMS·execution.json 작성. 제외 구간의 경과 시간도 진단값으로 기록한다.
  - [C] 측정 조건: pilot은 w = 12(CORE_MAX_WORKERS), G7과 같은 unit_size로, 한 세션에서 끝까지 실행한다(WO:418 분모 12에 맞는 효율).
  - [C] 0 < η̂ ≤ 1일 때만 G6 예산 판정에 쓴다.
    - η̂ > 1, η̂ ≤ 0, 비유한이면 값을 보정하거나 제한하지 않고 STOP_FOR_USER_DECISION.
    - pilot 세션이 둘 이상이거나 R-4의 TIME_ACCOUNTING_INCOMPLETE이면 T_wall이 정의되지 않으므로 STOP_FOR_USER_DECISION.
- R-3 보정·평가 시간과 W:
  - [B] W와 G6 예상 wall-clock은 G7 CORE 본 실행 복제의 예상 비용이다. G5에서 끝난 E1 edge 보정과 σ 보정의 시간은 넣지 않는다.
  - [C] V-4 평가(G7, 4,000년 경로 1개)는 CORE unit run과 별도 단계로 실행한다.
    - W와 G6 예상 wall-clock에 넣지 않는다(WO:417-418 식은 그대로).
    - R-4의 CORE 누적 wall-clock에도 넣지 않는다.
    - G7 전체 실행 시간에는 포함해 따로 보고한다.
    - G6 보고에는 참고값(ESTIMATE)을 적는다. 참고값은 G5 E1 보정에서 잰 4,000년 경로 1회 평가 시간이다.
  - [B] 중복 계상 방지: pilot t는 복제 계산만 담는다. 보정·σ 보정·V-4 평가 시간은 각자의 실행 기록에만 남는다.
- R-4 실행 중 1.5배 STOP과 시간 기록 상태:
  - [B] 적용 대상: G7 CORE unit run. "예상"은 G6이 고정한 값이므로 G5 pilot, σ 보정, V-4 평가, G4c smoke에는 적용하지 않는다.
  - [C] 기준: CORE 누적 wall-clock > 1.5 × G6이 고정한 예상 wall-clock(W / (12·η̂)) 이면 STOP.
    - 세션 경과 시간: 세션 시작부터 그 세션에서 마지막으로 완료된 unit의 index 기록까지, 부모 프로세스 perf_counter 차이.
    - CORE 누적 wall-clock: 그 run 디렉터리의 모든 세션 경과 시간의 합. 재개해도 0으로 돌아가지 않는다.
  - [B] 평가 시점은 unit 완료 직후다. STOP하면 완료 unit은 보존하고(WO:421), 진행 중이던 unit은 쓰지 않는다.
  - [C] 진행률 기반 초과 예상(누적 wall ÷ 완료 복제 비율)은 진단값으로만 기록한다. 이 값으로 자동 STOP하지 않는다.
  - [C] TIME_ACCOUNTING_INCOMPLETE: 세션 시작 기록은 있는데 끝 기록이 없는 세션(비정상 종료)이 있는 상태.
    - 완료 unit은 보존한다.
    - 기록된 누적 wall-clock을 하한으로 표시한다.
    - 그 세션의 마지막 완료 unit 이후 구간을 미계상 구간으로 따로 보고한다.
    - UTC 시각 차이를 실행 시간으로 간주하지 않는다. 누락 시간을 추정하거나 대체하지 않는다.
    - 하한이 이미 1.5배를 넘으면 위 STOP을 적용한다. 넘지 않아도 시간 기준 PASS로 판정하지 않는다.
    - 재개는 사용자 결정에 따른다.
- R-5 시간 기록 위치와 수치 처리:
  - [B] 모든 비결정적 시간 값은 execution.json에만 쓴다(WO:248과 WO:69를 함께 만족하기 위해서). 대상: 복제 시간, T_wall, 진단 구간, 세션 경과, 누적, t̂_c, η̂, W, 예상 wall-clock, 예산 판정, 진행률 진단값, 미계상 구간.
    - unit, index, manifest, SHA256SUMS, 결정적 G6 요약에는 시간 값을 넣지 않는다.
  - [C] execution.json에는 세션 시작, unit 완료, 세션 끝, G6 시간 판정을 각각 기록한다. 원자적으로 쓰고, 기존 기록을 보존한 채 덧붙인다.
  - [C] 상태 구분:
    - Unit 완료: index 검증 통과(결정적).
    - 시간 기록 완료: 모든 세션에 시작·끝 기록이 있고 완료 unit마다 완료 기록이 있음.
    - 시간 기록 불완전: TIME_ACCOUNTING_INCOMPLETE.
    - 실행 전체 완료: 결정적 산출물이 모두 검증되고 execution.json이 정상. 시간 기록 상태는 별도로 보고한다.
  - [C] 측정은 time.perf_counter(), 초 단위 float를 그대로 기록한다(JSON repr). 같은 프로세스 안에서 잰 차이만 쓴다. UTC 시각은 표시와 미계상 구간 보고에만 쓴다.
  - [C] 계산(t̂_c, η̂, W, wall, 누적)은 반올림하지 않는다. 표시만 소수 3자리로 한다. worker-hour = 초 / 3600.
  - [A] 경계 비교: W ≤ 1,152, wall ≤ 96이면 통과("≤"). 1.5배 STOP은 엄격히 큰 경우("넘으면").
- R-6 셀별 R_c 결합 (명확화):
  - [B] R_c = max_{h ∈ H(c)} R_h. H(E1-θ0.7) = {V-1, V-2, V-3}, H(P0-θ0.7) = {V-8}.
    - R_h = required_reps(π_U(x_disc,h))이고, V-1은 x_disc = max(x_lo, x_hi)다(WO:253).
    - 근거: 한 셀의 가설은 같은 복제를 공통 난수로 쓴다(DC3). 검정력·TARGET_MAX_MC_SE(DC9) 조건이 가설마다 적용되므로, 모두를 만족하는 최소 R이 max다.
    - 새로운 검정력 목표나 판정 기준이 아니다.
- R-7 G4c smoke:
  - [B] E1·P0 경로와 smoke σ 보정(R_σ = 20)은 namespace "FUTDIAG-TEST"에서 ERRATA-002와 같은 cell·window·rule 문자열을 쓴다(DC10 "테스트 전용", ERRATA-002 일반 형식).
    - smoke σ는 ("FUTDIAG-TEST", "E1-ecal", str(rep), "all", "path")다. 새 seed 문자열은 없고, "FUTDIAG-SIGMA"는 쓰지 않는다.
  - [C] smoke E1 TEST_FIXTURE: edge_annual = e_cal(config 0.728515625), sigma_pop = 0.70/√365, calibration_provenance.kind = TEST_FIXTURE. 연구 결과로 쓰지 않는다.
  - [A] 실제 E1 보정은 G5에서 한 번 하고, G7은 그 값을 재사용한다.

## RATIONALE

RATIONALE:
- T1(평균의 상한)은 W가 R_c개 복제의 합을 추정한다는 점과 맞는다. 단측은 예산 초과만 문제라는 점과 π_U의 방향에 맞춘 것이다.
- 복제 계산(t)과 병렬 오버헤드(T_wall → η̂)를 나누면 오버헤드가 wall 판정에 정확히 한 번 들어간다.
- 측정값이 무효이거나 시간 기록이 불완전할 때 값을 보정하거나 추정하지 않고 사용자 결정으로 넘기는 것은 예산 판정이 측정 오류 때문에 낙관적으로 되지 않게 하기 위해서다.
- 모든 시간 값을 execution.json에만 두면 G6 기록 요구(WO:69)와 결정성 요구(WO:248)를 함께 만족한다.

## BASELINE_IMPACT

BASELINE_IMPACT:
- Ce 커밋은 이 파일 하나만 추가한다. Work Order, ERRATA-001·002, 사전등록, config, MC-V06 `_SOURCE_FILES`는 바뀌지 않는다.
- 구현 초안(futility_diag.py, test_v06_futility_diag.py)과의 정합은 G3 Gate Authorization 범위의 구현에서 맞춘다.
- 통계 record, unit·index·manifest·SHA256SUMS 바이트, 통계 판정, 예산식·상한은 바뀌지 않는다.

## SECURITY_IMPACT

SECURITY_IMPACT: 없음. guard·hook·settings·자격증명·네트워크·실데이터와 관계없다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA (G3 TEST_GATES에서 light로 검증):
- AC-1 t̂_c: 알려진 입력으로 식 값 확인, sd = 0, 결측·비유한·음수 → STOP.
- AC-2 η̂: 식 값 확인, T_wall 시작·끝 경계, η̂ > 1 → STOP(제한하지 않음), η̂ ≤ 0·비유한 → STOP, 세션이 둘 이상인 pilot → STOP.
- AC-3 W·wall 경계: 정확히 1,152 / 96이면 통과, 바로 위 float이면 STOP.
- AC-4 1.5배 STOP: 세션 여러 개 누적, 재개 후 누적 유지, 정확히 1.5배면 통과, 초과면 STOP, 완료 unit 보존. 진행률 진단값으로는 STOP하지 않음. V-4 시간은 누적에 들어가지 않음.
- AC-5 TIME_ACCOUNTING_INCOMPLETE: 끝 기록이 없는 세션을 감지, 하한과 미계상 구간 보고, 자동 PASS 없음, 하한이 1.5배를 넘으면 STOP.
- AC-6 시간 값이 결정적 파일에 없음. 시간 기록을 더해도 worker 1·2 바이트 일치와 SHA256SUMS 범위가 유지됨. G3b-3 record 바이트 회귀 없음.
- AC-7 smoke: FUTDIAG-TEST tuple, FUTDIAG-SIGMA 미사용, TEST_FIXTURE 값과 표시.
- AC-8 Ce 커밋 전후 이 파일의 sha256이 같고 커밋 파일이 이 파일 하나다.

## ROLLBACK_POLICY

ROLLBACK_POLICY:
- ACCEPTED 이후 이 파일은 불변이다. 철회·수정은 ERRATA-004로만 한다.
- G5 이후에 이 ERRATA의 내용을 바꾸면 GATE_TRANSITION_RULES(WO:87)에 따라 사용자가 결정하고, G7 이후에는 새 study다.
- 사용자가 이 보충을 사전등록 변경으로 판단하면 이 ERRATA는 쓰지 않고 새 Work Order·사전등록으로 간다(WO:85).

## APPROVAL

APPROVAL:
- 사용자가 이 ERRATA-003의 최종 문구를 수락했다(ACCEPTED). 이 ERRATA는 Ce 커밋으로 고정되며 저장소 규칙에 따라 계약(우선순위 4)을 바꾼다.
- 수락은 [C] 항목 전체와, 이 보충이 사전등록 변경이 아니라 미정 사항 보충(WO:85, WO:349)이라는 사용자 판단을 포함한다.
- ACCEPTED 문구 확정과 Ce 커밋(파일 생성, 경로를 지정한 stage, 커밋, sha256 보고)은 각각 사용자의 별도 승인 사항이다.
- G5 전에 ACCEPTED로 고정한다.
