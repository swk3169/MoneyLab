# ERRATA: BT4-FUTILITY-01 ERRATA-004

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-FUTILITY-01-ERRATA-004
TASK_ID: BT4-FUTILITY-01
TARGET_WORK_ORDER: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md @ 7ac09a674e68cbc95dd5c934f2d3580939fd02f0 (sha256 c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b)
PRIOR_ACCEPTED_ERRATA: ERRATA-001 (sha256 9fcac5a97605a85be68612ba4a465c5f24b8c5b5594f3a801ca5e551993d24bf, Ce 616ed51f257a8cfa2d2c080067b09258651930e9), ERRATA-002 (sha256 0ca8ab961af350b10a2660ca8ee7b8c4bfab2757ee2b6b1ae61ffcfeee7308fe, Ce 2eb876e02456405667f466a124f745b3dd4fba3c), ERRATA-003 (sha256 9b8fcf9f30d8b525237a63b00f599add0a2fbcb33cb0f9ce900642a5a349823d, Ce b9932dcaa0c3f11568a65c9a6c19993675581d4c)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

규칙 분류(이 문서의 정의이며 ERRATA-003의 [A]/[B]/[C]와 뜻이 다르다): [A] 기존 계약에서 직접 도출되는 명확화 / [B] 기존 계약에 없는 신규 결정(수락 시 계약) / [C] 구현 단계에서 수행할 후속 조치

## ISSUE

ISSUE: G3b-5-2 계약 정합성 점검(G3b-5-2_CONTRACT_CLOSURE)에서 다음 사항을 확인했다.
- ERRATA-003 R-2는 제외 구간의 경과 시간을 진단값으로 기록하라고 정하지만, 세션 시작 기록과 마지막 unit 완료 기록의 쓰기 시간은 어떤 진단값에도 들어가지 않는다.
- ERRATA-003 R-3은 G5 보정 시간과 V-4 평가 시간을 "각자의 실행 기록"에 남기라고 하고, G6 참고값을 "G5 E1 보정에서 잰 4,000년 경로 1회 평가 시간"으로 정한다. 그러나 보정 실행 기록의 위치와 "1회 평가"의 측정 범위·방법은 정하지 않는다.
- ERRATA-003 R-2의 "G7과 같은 unit_size"는 G6 시점에 G7 값이 없으므로 확인 시점과 방법이 정해져 있지 않다.
- 사전등록 §7:370의 "manifest에 고정"이 어느 manifest를 가리키는지, 그리고 비결정적 시간 값과의 관계가 정해져 있지 않다.
- run_spec.reps는 셀 공통인데 R_c는 셀마다 다를 수 있다. 그 결과 G7이 셀별 run이 되면 ERRATA-003 R-4의 "그 run 디렉터리의 누적"을 CORE 전체 예상 wall-clock과 어떻게 비교할지 정해져 있지 않다.
이 ERRATA 작성 시점에 G4c, G5, G6, G7은 실행되지 않았다.

## CHANGED_FIELDS

CHANGED_FIELDS (보충, 기존 문장 유지):
- ERRATA-003 R-2: 제외 구간 진단값의 정의
- ERRATA-003 R-3: G5 보정 실행 기록의 위치, V-4 평가 시간 참고값의 출처·측정 범위·측정 방법
- ERRATA-003 R-2 측정 조건: unit_size 동일성의 기록과 확인 시점
- 사전등록 §7:370 "manifest에 고정"의 해석과 manifest·execution.json의 경계
- ERRATA-003 R-4: 셀별 run일 때 CORE 누적 wall-clock의 합산과 worker 상한

UNCHANGED_FIELDS (명시적으로 바꾸지 않음):
- ERRATA-003 R-1~R-7의 정의: t̂_c, η̂, T_wall 측정 구간, W와 예상 wall-clock 식, 1.5배 STOP 기준, TIME_ACCOUNTING_INCOMPLETE, 시간 기록 위치 원칙
- WO:417-421의 식·상수·비교 방향, CORE_MAX_WORKERS = 12 (WO:45)
- calibration.json 스키마(G3b-5-1), g6/ 구조(G1), 최상위 SHA256SUMS 범위, G5 pilot 산출물
- MC-V06 `_SOURCE_FILES`(montecarlo.calibrate_edge, _target_sharpe 포함)와 그 함수 객체
- POLICY_VALUES, STATISTICAL_HYPOTHESES, 판정·다중성, DC1–DC14, ERRATA-001·002·003, 사전등록·config 파일
- 이 ERRATA는 통계 판정 기준, 검정력 목표, 예산 상한, 예산식을 추가하거나 바꾸지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- R-1 T_wall 제외 구간 진단값:
  - [A] ERRATA-003 R-2(:54-60)의 T_wall 시작·끝·포함·제외 구간은 바꾸지 않는다. 제외 구간의 경과 시간은 진단값으로 기록한다(ERRATA-003 R-2 "제외 구간의 경과 시간도 진단값으로 기록한다").
  - [A] 세션 끝 기록에 두 진단값을 둔다.
    - pre_wall_s: 부모 프로세스 time.perf_counter() 기준, 세션 초기화 시작(init_run 호출 직전)부터 T_wall 시작까지. init_run, 디렉터리 검사, execution.json 검증, 세션 시작 기록 쓰기를 포함한다.
    - post_wall_s: 마지막 unit index 완료(T_wall 끝)부터 최종 SHA256SUMS 쓰기 완료까지. 마지막 unit 완료 기록 쓰기, unit 재검증, manifest, SHA256SUMS를 포함한다.
  - [A] 두 값은 W, t̂_c, η̂, 예산 판정, 1.5배 STOP 계산에 넣지 않는다(ERRATA-003 R-3 :70, R-5).
  - [A] 세션 끝 기록 자체의 쓰기 시간은 그 기록에 담을 수 없으므로 어떤 진단값에도 포함되지 않는다.
  - [C] 기존 init_s, finalize_s는 유지한다. 예산 STOP으로 끝난 세션에서는 manifest·SHA256SUMS를 쓰지 않으므로 post_wall_s는 마지막 unit 완료 기록 쓰기까지로 하고 그 사실을 표시한다.
- R-2 G5 보정 실행 기록:
  - [B] G5 보정의 비결정적 실행 기록(시작·끝 UTC, 경과 시간, worker 수, 구간별 시간, R-3의 V4_EVAL_TIME_ESTIMATE)은 보정 산출물 디렉터리의 execution.json에 둔다. 디렉터리에는 calibration.json과 execution.json 두 파일만 둔다.
  - [A] calibration.json은 결정적 산출물로 유지하고 스키마를 바꾸지 않는다(G3b-5-1). execution.json은 calibration.json의 sha256 provenance와 그 밖의 결정적 검증 대상에서 제외한다(WO:248과 같은 원칙, ERRATA-003 R-5).
  - [A] G5 보정과 σ 보정의 실제 소요 시간은 CORE W와 G6 예상 wall-clock에 넣지 않는다(ERRATA-003 R-3 :64).
  - [C] 보정 execution.json은 run의 execution.json과 같은 원칙(원자적 쓰기, 기존 기록 보존, 손상·스키마 오류 STOP)을 따른다. 스키마 이름은 run의 것과 구분한다.
- R-3 V-4 평가 시간 참고값(V4_EVAL_TIME_ESTIMATE):
  - [A] 출처는 G5 E1 보정, 즉 `montecarlo.calibrate_edge`가 수행하는 4,000년 경로 평가 1회다(ERRATA-003 R-3 :69). 평가 1회는 calibrate_edge의 f(x) 한 번이다(montecarlo.py:286-287).
  - [B] 측정 방법: SAME_EVALUATION_REPLAY.
    - G5 E1 보정(calibrate_edge)이 끝난 뒤, 같은 4,000년 noise와 calibrate_edge가 반환한 보정 edge로 f(x)의 평가 연산을 별도로 정확히 1회 재현한다.
    - 재현 호출은 `_target_sharpe(Path(*add_drift(replace(E1_DGP, edge_annual=edge), noise)), "M60", "E0", costs)`다. costs는 보정에 쓴 `Costs().log_costs()`다.
    - calibrate_edge 안의 호출을 직접 재지 않는다. MC-V06 `_SOURCE_FILES`와 그 모듈의 런타임 함수 객체를 바꾸거나 바꿔치지 않는다.
  - [B] 측정 범위(부모 프로세스 time.perf_counter() 차이 1회):
    - edge 적용(replace)
    - add_drift
    - Path 구성
    - _target_sharpe 호출
    - _target_sharpe 안의 strategy_signals 전체 STRATEGIES 계산
    - M60 선택
    - E0 segment 수익률
    - annual Sharpe
  - [B] 측정 제외:
    - draw_noise
    - calibrate_edge의 탐색 반복
    - 보정 후 achieved SR 검증
    - sigma_pop 계산
    - calibration.json 작성
    - execution.json 작성
  - [B] 재현 결과의 Sharpe s_replay는 MC-V06 산술 순서로 achieved와 비교한다: (s_replay − θ) + θ == achieved(허용오차 없음, G3b-5-1 achieved_reproduced와 같은 식). 다르면 STOP한다. s_replay는 이 확인에만 쓰고 기록하는 achieved를 대신하지 않는다.
  - [B] 측정값 이름은 V4_EVAL_TIME_ESTIMATE, 측정 방법 메타데이터는 method = SAME_EVALUATION_REPLAY다. R-2의 보정 execution.json에 기록하고, G6 보고와 g6_timing에 참고값(ESTIMATE)으로 옮긴다.
  - [A] V4_EVAL_TIME_ESTIMATE는 calibrate_edge 내부 호출을 직접 잰 시간이 아니라, 같은 연산을 따로 실행한 참고 추정치다. 실제 V-4 평가 시간을 대체하지 않는다. 실제 V-4 평가 시간은 G7 V-4 단계의 실행 기록에 따로 남긴다(ERRATA-003 R-3 :65-68). 기록 위치는 OPEN_ITEMS O-4다.
  - [A] 참고값과 실제 V-4 평가 시간은 모두 CORE W, G6 예상 wall-clock, R-6 CORE 누적에서 제외한다(ERRATA-003 R-3 :66-67).
- R-4 unit_size 동일성:
  - [A] ERRATA-003 R-2(:59) "pilot은 … G7과 같은 unit_size로"에 따라 G7 CORE의 unit_size는 G5 pilot의 run_spec.unit_size와 같아야 한다. 이 ERRATA는 새 unit_size 값을 정하지 않는다.
  - [C] G6은 pilot run_spec.unit_size를 g6/g6_summary.json의 pilot 항목에 기록한다.
  - [A] G7 CORE 진입 시 G6에 기록된 unit_size와 CORE run_spec.unit_size를 비교하고, 다르면 STOP한다(WO:87 G5 이후 조건 변경 금지). G6은 아직 만들어지지 않은 G7 run_spec을 요구하지 않는다.
- R-5 "manifest에 고정"의 해석과 manifest·execution.json의 경계:
  - [A] 사전등록 §7:370 "G6 … 계산은 1회만 하고 manifest에 고정한다"의 manifest는 G7 연구 manifest다. 근거는 다음과 같다.
    - G5 pilot의 manifest.json은 G5 끝에 쓰이고 최상위 SHA256SUMS로 봉인되어 바뀌지 않는다(WO:248, WO:405-406).
    - WO:404의 manifest 필수 항목 "σ̂·κ̂·σ_L·σ_U, R_c 계산 입력"은 G6 이후에만 존재한다.
  - [A] G5 pilot의 manifest.json은 수정하지 않는다. G6의 결정적 nuisance 값은 g6/g6_summary.json에 기록하고 g6/SHA256SUMS로 독립 검증한다(WO:69 "run 디렉터리에 기록", 승인된 G1 구조).
  - [A] G7 연구 manifest에는 결정적인 값과 결정적 출처 sha256만 고정한다.
    - G6 요약(g6/g6_summary.json) sha256
    - G6 nuisance 값(R_c, σ̂·κ̂·σ_L·σ_U, PD-5, P2 상태)
    - R_c 계산 입력(불일치 수와 n)
    - G6 요약이 참조한 G5 pilot의 sha256(run_spec, run_inputs, manifest, SHA256SUMS)
    - G6에 기록된 unit_size(R-4)
  - [A] 다음은 G7 manifest에 기록하지 않고 execution.json에만 둔다(ERRATA-003 R-5, WO:248): G6 예상 wall-clock, 실제 wall-clock, t̂_c, η̂, W, 그 밖의 시간 계측값, 예산 판정 결과.
  - [A] G7 manifest는 G6 시간 기록의 위치를 가리키는 결정적 참조(G5 pilot run을 식별하는 위 sha256과 그 run의 execution.json 안 `g6_timing` 항목 이름)만 둘 수 있다. 비결정적 시간 기록 파일(execution.json)의 내용 해시는 manifest에 고정하지 않는다.
  - [A] manifest에 해시가 없으므로 G7 진입 시 pilot execution.json의 세션 기록에서 g6_timing을 다시 계산해 기록된 g6_timing과 같아야 하고, 다르면 STOP한다(ERRATA-003 R-5의 1회 기록 원칙).
- R-6 G7 CORE 전체 예산:
  - [A] 비교식은 ERRATA-003 R-4와 WO:421을 유지한다.
    T_CORE_CUMULATIVE > 1.5 × (W_G6 / (12 · η̂))  이면 STOP
    W_G6는 G6이 고정한 worker-hour이고, 비교 대상은 worker-hour가 아니라 그로부터 계산한 예상 wall-clock이다. 정확히 1.5배면 통과한다.
  - [B] 1.5배 STOP은 셀별 run이 아니라 CORE 작업 전체에 적용한다. E1과 P0를 별도 run으로 실행하면 각 run의 누적을 더한다.
    T_CORE_CUMULATIVE = T_E1_CUMULATIVE + T_P0_CUMULATIVE
    T_X_CUMULATIVE는 셀 X run의 모든 세션 경과 시간의 합이다(ERRATA-003 R-4 정의).
  - [A] 동시에 사용하는 CORE worker 수는 모든 CORE run을 합쳐 12를 넘지 않는다(CORE_MAX_WORKERS, WO:45). 시간이 겹치는 run들의 wall-clock을 더하면 실제 경과보다 커지므로 STOP이 늦어지지 않는다(보수적).
  - [A] 같은 세션 시간을 두 번 더하지 않는다. 재개한 세션의 시간은 누적한다. 어느 셀 run이든 시간 기록이 불완전하면 그 run의 기록값을 하한으로 쓰고 예산 PASS를 선언하지 않는다(ERRATA-003 R-4).
  - [A] V-4 평가 시간은 T_CORE_CUMULATIVE에 넣지 않는다(ERRATA-003 R-3).
  - [B] CORE 전체 누적 검증이 실제 G7 실행 경로에 연결되지 않았다면 G7 시작을 금지한다.
  - 이 조항만으로 G7 실행 구조(단일 run 또는 셀별 run)를 바꾸지 않는다. 구조는 OPEN_ITEMS O-1이다.

## OPEN_ITEMS

OPEN_ITEMS (해결 전에는 실제 G7과 G8a를 실행하지 않고 STOP한다):
- O-1 G7 CORE 구조: 단일 run 또는 셀별 run
- O-2 셀별 R_c가 다를 때 run_spec.reps 처리(현재 run_spec.reps는 셀 공통 정수 하나)
- O-3 G7 전체 예산 감시(R-6)의 실제 저장·검증 경로(셀 run들의 누적을 어디서 합산하고 기록·검증하는지)
- O-4 V-4 실제 평가 단계 산출물(SR_eval, batch 값, 실행 기록)의 최종 디렉터리 구조
- O-5 G8a 판정 결과(decision summary) 저장 위치

## RATIONALE

RATIONALE:
- R-1: ERRATA-003이 이미 요구하는 진단값의 빈칸을 채운다. 측정 구간과 예산식은 그대로 둔다.
- R-2·R-3: ERRATA-003 R-3이 정한 출처에 측정 가능한 위치·범위·방법을 준다.
  - SAME_EVALUATION_REPLAY는 같은 noise와 보정 edge로 calibrate_edge의 평가 연산을 그대로 다시 실행하므로, 보호 모듈을 바꾸거나 바꿔치지 않고 실제 V-4 평가(`_target_sharpe` 1회)와 같은 단위의 연산을 잰다.
  - noise 생성, 탐색 반복, 후처리, 파일 쓰기는 뺀다.
  - 직접 측정이 아님을 메타데이터로 남겨 실제 시간과 혼동하지 않게 한다.
- R-4: ERRATA-003 R-2의 조건을 G6 기록과 G7 진입 검사로 바꾼다. 새 값을 만들지 않는다.
- R-5: 봉인된 pilot manifest, WO:404의 manifest 항목, WO:248의 결정성 요구를 함께 만족한다. 시간 값을 manifest 밖에 두어 manifest의 바이트 결정성을 지킨다.
- R-6: 셀별 run에서도 WO:421의 "누적 시간이 예상의 1.5배"가 CORE 전체 기준으로 유지되게 하고, worker 상한(WO:45)을 run 전체에 적용한다.

## BASELINE_IMPACT

BASELINE_IMPACT:
- Ce 커밋은 이 파일 하나만 추가한다. Work Order, ERRATA-001·002·003, 사전등록, config, MC-V06 `_SOURCE_FILES`는 바뀌지 않는다.
- 구현 초안(futility_diag.py, test_v06_futility_diag.py)과의 정합은 G3 Gate Authorization 범위의 구현에서 맞춘다.
  - R-1 진단값
  - R-2·R-3 보정 실행 기록과 SAME_EVALUATION_REPLAY 측정
  - R-4 unit_size 기록과 진입 검사
  - R-5 연구 manifest와 g6_timing 재검증
  - R-6 전체 예산 감시
- 통계 record, unit·index·manifest·SHA256SUMS 바이트, calibration.json 스키마, 통계 판정, 예산식과 상한은 바뀌지 않는다. 단, R-4에 따라 g6_summary.json의 pilot 항목에 unit_size가 추가된다.

## SECURITY_IMPACT

SECURITY_IMPACT: 없음. guard·hook·settings·자격증명·네트워크·실데이터와 관계없다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA (G3 TEST_GATES에서 light로 검증):
- AC-1 pre_wall_s와 post_wall_s가 fake clock 값과 정확히 맞는다. W·η̂·1.5배 STOP 계산에는 쓰이지 않는다. 예산 STOP으로 끝난 세션의 post_wall_s 범위를 확인한다.
- AC-2 보정 디렉터리에 calibration.json과 execution.json만 있다. execution.json을 바꿔도 calibration sha256과 provenance가 그대로다. execution.json 손상·스키마 오류는 STOP이다.
- AC-3 V4_EVAL_TIME_ESTIMATE (SAME_EVALUATION_REPLAY):
  - fake clock으로 측정 구간이 재현 호출 1회(edge 적용부터 annual Sharpe까지)와 정확히 맞는다. 코드 위치로도 확인한다.
  - 재현 호출이 calibrate_edge에 넘긴 것과 같은 noise 객체와 반환된 보정 edge를 쓴다.
  - (s_replay − θ) + θ == achieved이고, 일부러 다르게 만들면 STOP이다.
  - montecarlo.calibrate_edge, montecarlo._target_sharpe, synthetic.add_drift, synthetic.strategy_signals 등 보호 모듈의 함수 객체가 측정 전후에 같은 객체(is)다. MC-V06 `_SOURCE_FILES` diff가 비어 있다.
  - draw_noise, 탐색 반복, achieved SR 검증, sigma_pop 계산, calibration.json·execution.json 작성이 측정 구간 밖이다.
  - 보정 execution.json에 V4_EVAL_TIME_ESTIMATE와 method = SAME_EVALUATION_REPLAY가 ESTIMATE로 기록되고, g6_timing에 ESTIMATE로 옮겨진다.
  - W, G6 예상 wall-clock, CORE 누적 예산에 들어가지 않는다.
- AC-4 g6_summary.json의 pilot.unit_size가 pilot run_spec과 같다. G7 진입 검사에서 다른 unit_size는 STOP, 같으면 통과다.
- AC-5 G7 연구 manifest:
  - R-5의 결정적 항목이 있다.
  - 시간·η̂·예상·실제 wall-clock·예산 판정 필드가 없고, execution.json 내용 해시가 없다.
  - worker 1·2 실행에서 manifest 바이트가 같다.
  - G5 pilot manifest 바이트는 그대로다.
  - G7 진입 시 g6_timing 재계산이 다르면 STOP이다.
- AC-6 CORE 전체 예산:
  - 셀 run 두 개의 누적 합이 정확히 1.5 × (W_G6 / (12·η̂))이면 통과, 넘으면 STOP이다. W_G6를 직접 비교하지 않는다.
  - 동시 CORE worker 합이 12를 넘는 구성은 시작 전에 STOP이다.
  - 불완전한 시간 기록이 있으면 PASS가 없다.
  - V-4 시간은 합에 들어가지 않는다.
  - 전역 누적 검증이 연결되지 않은 경로로는 G7이 시작되지 않는다.
- AC-7 Ce 커밋 전후 이 파일의 sha256이 같고 커밋 파일이 이 파일 하나다.

## ROLLBACK_POLICY

ROLLBACK_POLICY:
- ACCEPTED 이후 이 파일은 불변이다. 철회·수정은 ERRATA-005로만 한다.
- G5 이후에 이 ERRATA의 내용을 바꾸면 GATE_TRANSITION_RULES(WO:87)에 따라 사용자가 결정하고, G7 이후에는 새 study다.
- 사용자가 이 보충을 사전등록 변경으로 판단하면 이 ERRATA는 쓰지 않고 새 Work Order·사전등록으로 간다(WO:85).

## APPROVAL

APPROVAL:
- 이 문서는 사용자가 수락한 ACCEPTED ERRATA이며, 명시된 보충 계약을 적용한다.
- 수락은 [B] 항목 전체와, 이 보충이 사전등록 변경이 아니라 미정 사항 보충(WO:85, WO:349)이라는 사용자 판단을 포함한다. [B] 항목은 다음과 같다.
  - R-2: 보정 execution.json 위치
  - R-3: 측정 방법 SAME_EVALUATION_REPLAY(사용자 결정), 측정 범위와 제외 항목, 재현 일치 확인, 이름과 메타데이터
  - R-6: CORE 전체 합산, 전역 검증 미연결 시 G7 시작 금지
- OPEN_ITEMS O-1~O-5는 이 ERRATA로 정하지 않는다. 해결 전에는 실제 G7과 G8a를 실행하지 않는다.
- ACCEPTED 문구 확정과 Ce4 커밋(파일 생성, 경로를 지정한 stage, 커밋, sha256 보고)은 각각 사용자의 별도 승인 사항이다.
