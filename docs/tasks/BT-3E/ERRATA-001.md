# ERRATA: BT-3E ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT-3E-ERRATA-001
TASK_ID: BT-3E
TARGET_WORK_ORDER: docs/tasks/BT-3E/WORK_ORDER.md @ de69e4f28a7e269e59aaebc1040c9453c8071787 (sha256 3a506f748ea33a28c8a1cf01fffda43a74ff216efa0a4cae9d9ee2eb62a40a20)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자, 2026-10-17 (GATE_AUTHORIZATION: BT-3E CONTRACT_ERRATA WO@de69e4f28a7e269e59aaebc1040c9453c8071787)

## CHANGED_FIELDS

CHANGED_FIELDS:
- DESIGN_CONTRACT.E6 (MONTH_ONLY의 lookback과 "검증" 문장)
- DESIGN_CONTRACT.E10 (MONTH_ONLY 월 자격)
- DESIGN_CONTRACT.E14 (DERIVED_IDENTITY의 전략별 config_sha256 정의)
- DESIGN_CONTRACT.E15 (risk_policy candidates의 config_sha256 정의)
- DESIGN_CONTRACT.E19 (문서 갱신 내용)
- TEST_GATES.T9
- TEST_GATES.T10

## RATIONALE

RATIONALE: BT-3E PRECOMMIT_AUDIT(작업 트리 기준, HEAD de69e4f)이 계약의 차단성 모호 두 가지를 찾았다. (1) MONTH_ONLY에서 대상 월 이전의 보호 forward 행을 lookback으로 쓸 수 있는지, 그리고 없는 달을 어떻게 처리하는지를 E6·E10이 정하지 않았다. E6의 lookback 목록에는 locked holdout과 public만 있다. (2) 후보별 config_sha256이 무엇을 해시하는지 E14·E15가 정하지 않았다. 사용자는 (1)을 해석 B(결정적으로 필요한 최소 lookback만 쓰고, 필요한 봉인이 없거나 무결하지 않으면 소비 전에 거부)로, (2)를 날짜와 무관한 후보 평가 설정의 식별로 확정했다. 이 ERRATA는 위 필드만 명확히 한다. 새 연구 정책 값을 고르지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- DESIGN_CONTRACT.E6: 날짜 대응 (Q6). 이 항목 전체를 다음으로 바꾼다.
  - 지원하는 대응은 이름 붙인 enum 하나 `ENGINE_WINDOW_BT3B`뿐이다. 기본값은 없고 정책에 명시해야 한다.
  - 의미: 보호 구간 시작 날짜를 P라 할 때 engine first_day F = P − 2일. 대상 월 m의 다음 달 시작을 N이라 할 때 engine last_day = N − 3일(엔진 G_end = N).
    - 누적 방식(CUMULATIVE_FROM_L): 과학적 평가 구간은 L부터 대상 월까지 누적이다. P = L(vault spec의 locked_end_utc)이다.
    - 월 단독 방식(MONTH_ONLY): 과학적 평가 구간은 대상 월뿐이다. P = max(m 시작, L)이다. 이전 forward 달을 있다는 이유만으로 누적하거나 읽지 않는다.
    - 확증 계산은 정책의 confirmatory_first_day/confirmatory_last_day를 engine first_day/last_day로 그대로 쓴다.
  - 결과를 문서에 명시한다: 첫 엔진 기준 시각은 P보다 앞설 수 있고 그 값은 허용된 lookback 행에서 온다. 월말 하루의 수익률은 엔진의 다음 날·다음 달 의미로 넘어갈 수 있다.
  - 허용된 lookback 행: public 행과 locked holdout 행(원래 계약과 같음), 그리고 MONTH_ONLY에서 아래의 "결정적 최소 forward lookback" 행. 그 밖의 보호 forward 행은 읽지 않는다.
  - 결정적 최소 forward lookback (MONTH_ONLY에만 적용, 엔진 상수와 고정된 정책에서만 유도):
    - n_max = 바인딩된 F의 전략들이 엔진에서 요구하는 일봉 창 길이(`strategy.RULES[rule].bars_needed`)의 최댓값.
    - 필요한 일봉 시작 하한 T_day = F − (n_max − 1)일. 필요한 1시간봉 시작 하한 T_hour = F. T_req = min(T_day, T_hour).
    - 필요한 forward lookback 달 = month(L) ≤ m′ < m 이고 next(m′) > T_req 인 모든 달 m′ (빈 집합일 수 있다. T_req < L이면 L 이전 부분은 public·locked holdout lookback이다).
    - 필요한 forward lookback 달은 모두 봉인되어 있고 무결해야 한다. 하나라도 없거나, 봉인되지 않았거나, 무결성 검사에 실패하면 월별 접근 기록을 만들기 전에 거부한다(사용 아님, VaultPreconditionError 또는 VaultIntegrityError). 없는 필요 달을 건너뛰지 않고, 엔진의 신호 결측 처리로 대신하지 않는다.
    - 필요하지 않은 이전 forward 달이 없는 것만으로는 거부하지 않는다. 필요하지 않은 이전 forward 달은 있더라도 읽지 않고, 그 파일을 접근 기록의 files에 넣지 않는다.
    - 엔진에 넘기는 forward 행: 대상 월의 행 전부, 그리고 필요한 forward lookback 달의 행 중 일봉은 시작 ≥ T_day, 1시간봉은 시작 ≥ T_hour인 행만. public과 locked holdout 행은 원래 계약대로 넘긴다.
  - 검증: 엔진에 필요한 끝이 허용된 봉인 범위(대상 월까지)를 넘지 않는다. 위의 허용된 행만 쓴다. 대상 월이 check_window_end_utc 정책 안에 있다.
  - 소비 전에는 봉인 메타데이터와 해시만 검사한다(BT-3D 계약과 같음). 보호 forward 행은 월별 접근 기록을 만든 뒤에만 읽는다.
  - BT-3E가 `ENGINE_WINDOW_BT3B`를 지원한다고 해서 BT-4가 그것을 고른 것은 아니다. 다른 대응은 별도 승인 작업이다. MC-V06은 나중에 같은 대응 ID와 같은 lookback 규칙을 따라야 한다.
- DESIGN_CONTRACT.E10: VIOLATION·final 이후 (Q10). 이 항목 전체를 다음으로 바꾼다.
  - 장치는 VIOLATION 이후 study 수준 중단을 하지 않는다. 다른 조건이 맞으면 이후 달도 확인할 수 있다.
  - check_window_end_utc 밖의 달은 거부한다. 규칙: check_window_end_utc가 null이 아니면 대상 월 시작 < check_window_end_utc여야 한다. null은 "경계 없음"을 명시한 값이며 기본값이 아니다(키 누락은 거부).
  - 대상 월은 month(L) 이상이어야 한다.
  - 누적 방식이면 month(L)부터 대상 월까지 모든 달이 봉인되고 무결해야 한다.
  - 월 단독 방식이면 대상 월과 E6의 "필요한 forward lookback 달"이 모두 봉인되고 무결해야 한다. 그 밖의 이전 달은 요구하지 않는다.
  - 위 조건을 어기면 월별 접근 기록을 만들기 전에 거부한다(사용 아님).
- DESIGN_CONTRACT.E14 DERIVED_IDENTITY 줄: "DERIVED_IDENTITY: 전략별 config_sha256(E15의 날짜와 무관한 후보 평가 설정 식별), vault_content_sha256, preregistration_sha256, config_sha256(study config 식별, 최상위), L(vault spec), 레코드 SHA"
- DESIGN_CONTRACT.E15 risk_policy candidates의 config_sha256: risk_policy 항목의 다른 내용은 그대로 두고, candidates의 config_sha256 정의를 다음으로 정한다.
  - candidate.config_sha256 = `storage.atomic.sha256_of(payload)` (프로젝트의 정규 JSON: 키 정렬, 구분자 "," ":", ensure_ascii=False, 그 SHA-256).
  - payload는 정확히 다음 7개 키의 객체이고, 값은 risk_policy 레코드에 기록된 그대로(JSON 형식: scenario 문자열, initial_cash 10진 문자열, fee_bps 정수, kappa_bps 10진 문자열, impact_bps 10진 문자열, fill_substitution 문자열, capacity_verified 불리언)다: scenario, initial_cash, fee_bps, kappa_bps, impact_bps, fill_substitution, capacity_verified.
  - payload에 넣지 않는 것: confirmatory_first_day, confirmatory_last_day, 대상 월, forward 월·창 날짜, caller, 시각, 실제 F, 접근 기록 식별, 전략 ID(전략 ID는 candidates의 키로 따로 바인딩된다).
  - 같은 candidate.config_sha256이 그 후보의 확증 재계산과 forward 위험 평가를 모두 바인딩한다. 두 계산은 모두 이 7개 설정으로 RunConfig를 재구성하고, 날짜만 다르다.
  - 바인딩된 후보 평가 필드 중 하나라도 바뀌면 config_sha256이 바뀐다. 확증·forward 날짜만 바뀌면 config_sha256은 바뀌지 않는다. 레코드를 읽을 때 기록된 7개 값으로 다시 계산한 값과 다르면 정책은 형식 오류다(VaultPreconditionError, 사용 아님).
  - 확증 구간은 risk_policy.confirmatory_first_day·confirmatory_last_day로 따로 고정·바인딩된다.
- DESIGN_CONTRACT.E19: docs/backtest_design.md 갱신. 원래 E19 내용에 다음을 더한다: MONTH_ONLY를 "대상 월의 과학적 평가 + 결정적 최소 엔진 필요 lookback이며, 필요한 보호 lookback 봉인은 소비 전에 fail-closed로 검증한다"로 설명하고, "이전 봉인 월이 있으면 쓰고 없으면 건너뛴다"는 문구나 그런 뜻을 남기지 않는다. 후보 config_sha256을 날짜와 무관한 7개 설정의 식별로 설명한다.
- TEST_GATES.T9: "T9 식별 불일치는 VaultPreconditionError이고 접근 기록이 생기지 않는다. 다음을 각각 별도 테스트로 확인한다: (a) preregistration_sha256 불일치, (b) 최상위 config_sha256 불일치, (c) 정책 레코드의 vault_content_sha256 불일치, (d) F 레코드의 risk_policy_sha256 불일치, (e) 후보 config_sha256 바꿔치기(기록된 7개 설정과 다른 값) 불일치, (f) 후보 설정만 바꾸고 config_sha256을 그대로 둔 경우. 또한 확증 날짜만 다른 두 정책의 같은 후보는 같은 config_sha256을 갖고, 후보 설정 하나만 다르면 다른 config_sha256을 갖는다."
- TEST_GATES.T10: "T10 월 자격(모두 사용 아님): month(L) 이전, check_window_end_utc 밖, 봉인되지 않은 대상 월, 누적 방식에서 중간 달 누락을 거부한다. MONTH_ONLY: (a) 대상 월이 봉인되고 필요한 최소 forward lookback 봉인이 있으면 다른 조건이 맞을 때 확인할 수 있다. (b) 필요한 최소 forward lookback 봉인이 없으면 소비 전에 거부한다(필요 달을 건너뛰지 않음). (c) 필요하지 않은 이전 forward 달이 없는 것만으로는 거부하지 않는다. (d) 필요하지 않은 이전 forward 달의 파일은 읽지 않고 접근 기록의 files에 없다. (e) 필요한 lookback 달이 무결성 검사에 실패하면 소비 전에 거부한다. 기존 누적·경계 테스트는 유지한다."

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다. ALLOWED_FILES와 PROTECTED_FILES는 바뀌지 않는다.
- 바꾸지 않는 것: 공개 API와 `__all__`(28개), 레코드 스키마(키 집합; 후보 config_sha256의 의미와 유도만 위와 같이 명확히 함), 증거 종류, 소비 시점, 정책·F 두 단계 시점, 확증 내부 재계산, 전략별 PASS/VIOLATION 출력, MAX_DRAWDOWN_LOG 지원, ENGINE_WINDOW_BT3B 공식, BT4-Q18 보류, BT-3D 계약, fixture 전용 경계, BT-4/BT-5/BT-6 범위.
- 새 연구 정책 값을 고르지 않는다.
