# ERRATA: GUARD-PROTECT-01 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: GUARD-PROTECT-01-ERRATA-001
TASK_ID: GUARD-PROTECT-01
TARGET_WORK_ORDER: docs/tasks/GUARD-PROTECT-01/WORK_ORDER.md @ 3bc7c6f28b417207a15efbc602cd1a9adeed5a0e (sha256 33b9a2b049d2089d4e48be7aad70447eac1a5f8bbf21543b49bf8930781b7f5e)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER, 2026-11-08

## APPLICABILITY

APPLICABILITY: PR #44의 Linux 실험 CI에서 발생한 신규 실패 17건을 수정하기 위한 IMPLEMENTATION rollback 재진입 1회.

이 ERRATA는 rollback 승인이 아니다. 재진입과 이후 gate는 각각 별도의 Gate Authorization이 필요하다.

## CHANGED_FIELDS

CHANGED_FIELDS (위 재진입 1회에만 적용):
- IMPLEMENTATION_SAFETY_CONDITIONS.S0
- IMPLEMENTATION_SAFETY_CONDITIONS.S1
- 재진입 수정 범위와 통과 기준 (REENTRY_SCOPE, REENTRY_PRINCIPLES, REENTRY_PASS_CRITERIA 추가)

## RATIONALE

RATIONALE:
- GATE_TRANSITION_RULES와 ROLLBACK_AND_RECOVERY는 CI 실패 뒤 명시 승인에 따른 IMPLEMENTATION rollback과 새 커밋을 허용한다.
- 그러나 S0는 HEAD = C1을, S1은 네 파일 blob = BASE_FILE_IDENTITY를 요구한다. 구현 커밋 20a39f537c08c12e973a172c5755c699bb113922 뒤에는 둘 다 충족할 수 없다.
- PR #44의 Linux 실험 CI에서 신규 실패 17건이 관측되었다: `test_gp_wrapper` 16건, `test_gp_file_tool[idc01-06]` 1건. 기존 `test_wrapper_*` 2건은 이전부터 실패한다.
- 사용자는 필수 Windows CI 통과만으로 이 Linux 회귀를 수용하지 않기로 결정했다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:

- Ce: 이 ERRATA 문서만 추가한 커밋이다. parent = 20a39f537c08c12e973a172c5755c699bb113922. 구현 파일 변경이 없어야 한다.

- S0 SESSION_START_CHECK: HEAD = Ce, Work Order sha256 일치, clean(ignored `.venv` 제외), ENVIRONMENT_ACCEPTANCE의 S0 항목 전부 충족. 인라인 인터프리터는 sys.prefix와 moneylab.__file__ 출력을 위한 지정 명령 1개만 허용한다.

- S1 원본 정체성: 네 파일의 `git hash-object`와 `git rev-parse HEAD:<path>`가 20a39f537c08c12e973a172c5755c699bb113922 시점의 아래 blob과 같다. 다르면 STOP.
  - .claude/hooks/guard.py: 1ee78a04aabdb01bb1a8cd818d24762ce77fc075
  - .claude/settings.json: a863ba0a680bf961b13f1f099e468721d918d0ac
  - tests/test_agent_guard.py: 660418236248dbba8ce99b4882a5378fc6abb6a2
  - docs/agent_workflow.md: ecac3a4b6f6403d22e1d18336a7235f362fd5752

- REENTRY_SCOPE: 재진입에서 수정할 수 있는 파일은 아래 2개뿐이다. 재진입 커밋의 파일 집합은 이 2개의 부분집합이며, Gate 표 COMMIT 행의 "필수 변경 3개 포함"은 커밋 20a39f537c08c12e973a172c5755c699bb113922로 충족된 것으로 본다.
  - .claude/hooks/guard.py
  - tests/test_agent_guard.py

- REENTRY_PURPOSE:
  1. Linux 신규 wrapper 실패 16건 해결
  2. idc01-06 경로 판정 실패 1건 해결
  3. Windows Guard 보호 기능 유지
  4. 기존 테스트 및 보호 계약 유지

- REENTRY_PRINCIPLES:
  - 최소 변경
  - 테스트 삭제 금지
  - 기존 기대값 완화 금지
  - 신규 skip·xfail로 실패 은폐 금지
  - Guard 비활성화·우회 금지
  - os.path.exists 수정 방식은 후보로 취급하고 실제 검증으로 확정한다

- REENTRY_PASS_CRITERIA:
  - Windows 필수 CI SUCCESS
  - Linux 신규 실패 0건
  - Linux 전체 실패는 기존 wrapper 2건 이내
  - 기존 테스트 삭제·기대값 변경 없음
  - GUARD_PROTECTION_COMPLETE = NO 유지

## UNCHANGED_FIELDS

UNCHANGED_FIELDS: 위에 적지 않은 Work Order의 나머지 요구사항과 STOP 조건은 그대로 유지한다. C1, WORK_ORDER.md blob과 그 sha256, ALLOWED_FILES, PROTECTED_FILES, GATE_SEQUENCE, GATE_TRANSITION_RULES, REQUIRED_CI_CHECKS, MERGE_METHOD를 포함한다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
