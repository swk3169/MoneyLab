# ERRATA: BT4-FUTILITY-01 ERRATA-002

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-FUTILITY-01-ERRATA-002
TASK_ID: BT4-FUTILITY-01
TARGET_WORK_ORDER: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md @ 7ac09a674e68cbc95dd5c934f2d3580939fd02f0 (sha256 c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b)
PRIOR_ACCEPTED_ERRATA: ERRATA-001 (sha256 9fcac5a97605a85be68612ba4a465c5f24b8c5b5594f3a801ca5e551993d24bf, Ce 616ed51f257a8cfa2d2c080067b09258651930e9)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

## ISSUE

ISSUE: G3b-3H 읽기 전용 감사에서 Work Order와 사전등록이 하나로 정하지 않은 구현 입력 세 가지를 확인했다.
(1) U-P0COST: DC1(WO:159)은 "비용은 `montecarlo.Costs()` 기본값"이라고 하고, DC6(WO:216)은 P0-θ0.7을 "iid Normal, 항상 노출"로 정의하며 비용을 언급하지 않는다. P0에 비용을 적용하는지가 명시되어 있지 않다.
(2) U-SE: DC11(WO:246)은 "변형별 ŝe"를 요구하지만 V0·V0d·V0b60의 정의(DC2)에는 ŝe가 없다. "블록 규칙별 bootstrap sd"의 정의식과 분모가 없다.
(3) U-SEEDSTR: DC10(WO:239) 여섯 부분 형식의 window·rule 자리에 넣을 문자열(특히 창과 무관해야 하는 경로 seed), 셀 이름 표기, pilot·σ 보정 seed 부분이 명시되어 있지 않다.
이 ERRATA는 기존 문구와 모순되지 않게 이 빈칸만 채운다. 이 ERRATA 작성 시점에 G5(pilot·σ 보정)와 그 이후 gate는 실행되지 않았다.

## CHANGED_FIELDS

CHANGED_FIELDS (보충, 기존 문장 유지):
- DC6 P0 정의: 수익률 생성과 비용 처리 명시
- DC11 복제별 record: 변형별 ŝe의 적용 범위, bootstrap sd의 정의, record 단위와 구조 식별자, annual Sharpe의 대상 계열 명시
- DC10 seed: 일반 형식의 window·rule·cell 문자열, pilot·σ 보정 부분(신규 고정 문자열 "E1-ecal" 포함), 명시 예외 목록, 경로 재사용 규칙 명시

UNCHANGED_FIELDS (명시적으로 바꾸지 않음): DC1 E1 셀의 비용(M60, E0, `montecarlo.Costs()` 기본값), DC2–DC4.1의 모든 식·상수·퇴화 정의와 정책(SD, RD, ND, PD-1..PD-6), DC3 변형과 인덱스 공유 관계, DC6의 셀 정의(P0의 일 sd·일 평균 식 포함), DC7 창 경계, DC8–DC9, DC10 일반 형식과 이름공간, BASE_SEED = 20261029, 사전등록에 명시된 seed tuple(E1 보정 `("FUTDIAG", "E1-θ0.7", "calib")`, V-4 평가 `("FUTDIAG", "v4eval")`, N1-c, N2-a, N2-c의 명시 접두), A1-c 충돌 정책, DC11의 통계 필드 목록과 출력 규칙(pilot summarize의 nuisance 전용 출력 포함), DC12–DC14, STATISTICAL_HYPOTHESES, 판정·다중성, ERROR_CLAIM_SCOPE, POLICY_VALUES, TEST_GATES(N1-c B = 200,000, N2-a B_N2a = 20,000, N2-c B = 999 포함), E2E_GATES, GATE_SEQUENCE, ALLOWED_FILES, PROTECTED_FILES, ERRATA-001, 사전등록·config 파일.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- P0_COST (DC6 보충):
  - P0 셀(CORE P0-θ0.7, EXPLORATORY P0-θ0.3)의 일 수익률 r_t는 DC6 식(일 sd = 0.70/√365, 일 평균 = θ·sd/√365)으로 생성한 iid Normal 값 그대로다.
  - DC6의 "항상 노출"은 노출 1의 상수이며 포지션 변화가 없다는 뜻이다.
  - P0에는 거래비용을 차감하지 않고, strategy 신호·`segment_market_positions`·`segment_returns`를 쓰지 않는다.
  - 따라서 P0의 모집단 연율 Sharpe는 정확히 θ이고 σ_pop은 해석값 0.70/√365다(DC3 WO:170 "해석값(P 셀)", TEST_GATES "P 셀 해석적 SR = θ", 사전등록 §6 N2-c와 일치).
  - E1 셀(E1-θ0.7 등)은 DC1을 그대로 따른다: M60, E0, `montecarlo.Costs()` 기본값, `segment_returns` 경유.
  - 이 항목은 P1·P2(EXPLORATORY)의 비용 처리를 정하지 않는다.
- SE_FIELDS (DC11 보충):
  - S1: ŝe는 DC4 F1(F1_effective, 사전등록 §5)의 제곱근, ŝe*_b는 DC4 재표본 식이다. DC4 그대로다. SD 복제에서도 S1의 ŝe 값과 p_S1 = 1은 DC4.1 그대로 기록한다.
  - V0, V0d, V0b60: studentized ŝe는 정의되지 않는다(DC2).
    - record의 해당 ŝe 필드는 null이고, 의미는 NOT_APPLICABLE("이 변형에 정의되지 않음")이다.
    - NOT_APPLICABLE은 퇴화 상태(SD, RD)나 근접 퇴화 비율(ND)이 아니며, 이들과 구분해 기록한다.
    - 이 null은 퇴화 판정, p 계산, 1차 판정에 쓰이지 않는다.
  - DC4.1의 퇴화 정의와 정책은 바뀌지 않는다. 새 통계 판정 기준을 추가하지 않는다.
- BOOTSTRAP_SD (DC11 "블록 규칙별 bootstrap sd" 보충):
  - 정의: 해당 (cell, rep, window)에서 그 블록 규칙의 재표본 평균 m*_b, b = 1..B의 표본표준편차. 분모 B − 1(`procedures.sd`).
  - B는 그 실행 계약의 B다: CORE 본 실행과 pilot은 B = 1,999(DC9, 사전등록 §7). EXPLORATORY는 그 실행 계약의 B(별도 승인)다.
  - TEST_GATES 진단 테스트(N1-c, N2-a, N2-c)의 B는 각 테스트 계약을 따르며 이 항목으로 바뀌지 않는다.
  - b20 값은 V0·V0d·S1이 쓰는 m*_b와 같은 재표본에서, b60 값은 V0b60이 쓰는 m*_b에서 계산한다.
  - bootstrap sd는 S1의 F1 ŝe나 ŝe*_b를 대체하지 않으며, 1차 판정·Holm·Bonferroni·R_c 계산에 쓰지 않는다.
  - 필드 이름은 DC4.1의 표본 퇴화 "SD"와 혼동되지 않게 `boot_sd_b20`, `boot_sd_b60`처럼 블록 규칙을 붙인다.
- RECORD_STRUCTURE (DC11 보충):
  - record 단위는 (cell, rep, window)이다. cell, rep, window는 구조 식별자이며 통계 필드가 아니다.
  - 통계 필드는 DC11 목록 그대로이며 새 통계 필드를 필수로 만들지 않는다.
  - annual Sharpe는 그 record의 m·s를 계산한 같은 r_t 계열의 `procedures.annual_sharpe`다.
- SEED_STRINGS (DC10 보충):
  - 일반 형식은 DC10 그대로: `stats.derived_seed(BASE_SEED, namespace, cell, str(rep), window, rule)`
  - cell 문자열: config `[core].cells`·`[exploratory].cells`의 ASCII 문자열(예: "E1-theta0.7", "P0-theta0.7").
  - 경로(DGP 잡음):
    - window = "all", rule = "path".
    - (namespace, cell, rep)마다 경로를 한 번만 생성하고 모든 창(conf, f12, f24, f36)은 그 경로를 자른다.
    - 창별로 경로를 다시 생성하지 않는다.
  - 블록 20 bootstrap:
    - window = 창 이름("conf" | "f12" | "f24" | "f36"), rule = "b20".
    - 이 seed가 만든 블록 열((시작, 길이) 순서) 하나를 V0, V0d, S1이 공유한다.
    - m*_b, S*_j, L_j는 같은 블록 열에서 계산한다.
  - 블록 60 bootstrap: 같은 window, rule = "b60". V0b60 전용 별도 인덱스다.
  - CORE 본 실행: namespace = "FUTDIAG", rep = 0 .. R_c − 1.
  - pilot: namespace = "FUTDIAG-PILOT", 위와 같은 cell·window·rule 문자열, rep = 0 .. 199.
  - σ 보정:
    - namespace = "FUTDIAG-SIGMA", cell = "E1-ecal", rep = 0 .. 1,999, window = "all", rule = "path". bootstrap은 쓰지 않는다.
    - "E1-ecal"은 e_cal DGP(사전등록 §7:369)의 경로를 가리키는 신규 고정 문자열이다. 이 ERRATA 전에는 Work Order·사전등록·config 어디에도 없었다.
  - EXPLORATORY: namespace = "FUTDIAG-X", 같은 규칙. 실행은 별도 승인이다.
  - 명시 예외(문구 그대로, 일반 형식에 끼워 맞추지 않음):
    - E1 보정: ("FUTDIAG", "E1-θ0.7", "calib"). 사전등록 §7의 Greek literal을 UTF-8 그대로 쓴다.
    - V-4 평가: ("FUTDIAG", "v4eval")
    - N1-c: ("FUTDIAG-TEST", "N1c", case)
    - N2-a: ("FUTDIAG-TEST", "N2a-data", case), ("FUTDIAG-TEST", "N2a-boot", case)
    - case = f"{series}-n{n}-b{int(mean_block)}", series ∈ {"iid", "ar1", "zero_inflated"}
    - N2-c: ("FUTDIAG-TEST", "N2c", f"n{n}", str(rep), role), role ∈ {"data", "boot"}. 사전등록의 접두 "N2c"에 n·rep·역할만 덧붙인다.
    - e_cal 재현과 T3 parity: MC-V06 seed 규칙(DC10 예외, 읽기 목적)
  - 모든 seed 부분은 str이고 "|"를 포함하지 않는다. 첫 부분은 DC10 이름공간이다.
  - A1-c 충돌 기록은 위의 모든 tuple을 config에서 결정적으로 나열해 계산한다. 값이 충돌해도 seed를 다시 뽑지 않는다.

## RATIONALE

RATIONALE: 세 항목 모두 현재 문서로는 구현이 하나로 정해지지 않고, 각 선택이 수치 결과를 결정적으로 바꾼다. 그래서 구현 판단(우선순위 5)으로 두지 않고 G3 전에 계약으로 고정한다.
- P0 무비용:
  - DC1의 비용 문장은 같은 줄의 전략(M60)·비용 시나리오(E0)와 함께 전략·포지션이 있는 셀에 대한 규정이다.
  - Work Order는 DC3(WO:170)에서 P 셀(해석값)과 E 셀(E0 segment 수익률)을 이미 구분한다.
  - 무비용은 사전등록에 이미 있는 "P 셀 해석적 SR = θ"·N2-c 조건과 정확히 일치하는 해석이다.
- V0 계열 ŝe null은 DC2 정의에 ŝe가 없다는 사실을 기록할 뿐이며 판정에 영향이 없다.
- bootstrap sd의 분모 B − 1은 DC2의 s(n−1 분모)와 같은 `procedures.sd` 규약이다.
- 경로 seed를 창과 무관하게 두는 것은 DC7(한 경로 위의 중첩 창)과 H-V8(같은 P0 경로의 f12·conf 짝 비교)이 요구하는 구조다. 블록 seed의 공유·분리는 DC3 그대로다.
- 사전등록의 통계 가설, 식, 상수, 판정 규칙은 바꾸지 않는다. G5 이후 결과는 아직 없으며 이 보충은 결과와 무관하게 정한다.

## BASELINE_IMPACT

BASELINE_IMPACT:
- Ce 커밋은 이 파일 하나만 추가한다. Work Order, ERRATA-001, 사전등록, config, MC-V06 `_SOURCE_FILES`는 바뀌지 않는다.
- untracked 구현 초안(src/moneylab/research/v06/futility_diag.py, tests/test_v06_futility_diag.py)은 이 ERRATA로 바뀌지 않는다. 계약과 맞추는 수정은 G3 Gate Authorization 범위에서 한다.
  - 예: V0 계열 ŝe의 NOT_APPLICABLE null 직렬화, 경로 seed ("all", "path"), σ 보정 cell "E1-ecal".
- 이미 수행된 G3 단계 결과가 이 ERRATA 이전에 유효했는지는 정하지 않는다. docs/tasks/README.md §6에 따라 사용자가 판단한다.

## SECURITY_IMPACT

SECURITY_IMPACT: 없음. guard·hook·settings·자격증명·네트워크·실데이터와 관계없다. ERRATA-001의 guard 실행 예외는 그대로다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA (G3 TEST_GATES에서 검증):
- AC-1: P0 셀 r_t 생성에 비용·strategy 신호·`segment_market_positions`·`segment_returns`가 쓰이지 않는다. E1 셀은 `segment_returns(…, Costs() E0)`를 쓴다(단위 테스트).
- AC-2: V0·V0d·V0b60 record의 ŝe 필드는 NOT_APPLICABLE null이며 SD·RD 표시와 구분된다. S1의 ŝe는 F1_effective와 일치한다(N1-a·b와 함께).
- AC-3: `boot_sd_b20`·`boot_sd_b60`은 해당 m*_b 목록(그 실행의 B개)의 `procedures.sd`와 bit 단위로 같다.
- AC-4: 같은 (namespace, cell, rep)에서 모든 창이 같은 경로 객체를 자른다. 경로 seed는 window = "all", rule = "path" 하나다.
- AC-5: 같은 (cell, rep, window)에서 V0·V0d·S1이 같은 블록 열을 쓴다(N1-d bit 일치). V0b60의 seed는 rule = "b60"으로 다르다.
- AC-6: 명시 예외 tuple과 신규 문자열 "E1-ecal"이 이 문서의 문자열과 바이트 단위로 같다(E1 보정 "θ" 포함). seed_policy가 manifest에 이 규칙을 기록한다.
- AC-7: A1-c 충돌 보고가 위 tuple 전체에서 결정적으로 계산된다(worker 1·2 출력 바이트 같음).
- AC-8: Ce 커밋 전후 이 파일의 sha256이 같고 커밋 파일이 이 파일 하나다.

## ROLLBACK_POLICY

ROLLBACK_POLICY:
- ACCEPTED 이후 이 파일은 불변이다. 철회·수정은 ERRATA-003으로만 한다.
- G5 이후에는 이 ERRATA의 내용을 바꾸면 GATE_TRANSITION_RULES(WO:87)에 따라 사용자가 결정하고, G7 이후에는 새 study다.
- 사용자가 이 보충을 사전등록 변경으로 판단하면 이 ERRATA는 쓰지 않고 새 Work Order·사전등록으로 간다(WO:85).

## APPROVAL

APPROVAL:
- 사용자가 이 ERRATA-002의 최종 문구를 수락했다(ACCEPTED). 이 ERRATA는 Ce 커밋으로 고정되며 저장소 규칙에 따라 계약(우선순위 4)을 바꾼다.
- 수락은 P0 무비용 처리, 신규 seed 문자열 "E1-ecal"의 고정, 그리고 이 문서의 보충들이 사전등록 변경이 아닌 미정 사항 보충(WO:85, WO:348)이라는 사용자 판단을 포함한다.
- ACCEPTED 문구 확정과 Ce 커밋(파일 생성, 경로를 지정한 stage, 커밋, sha256 보고)은 각각 사용자의 별도 승인으로 수행한다.
- Ce 전에는 G3b-3 구현을 시작하지 않는다. G3b-3 구현과 push는 이 승인에 포함되지 않는다.
