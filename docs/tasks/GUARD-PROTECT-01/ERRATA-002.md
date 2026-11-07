# ERRATA: GUARD-PROTECT-01 ERRATA-002

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: GUARD-PROTECT-01-ERRATA-002
TASK_ID: GUARD-PROTECT-01
TARGET_WORK_ORDER: docs/tasks/GUARD-PROTECT-01/WORK_ORDER.md @ 3bc7c6f28b417207a15efbc602cd1a9adeed5a0e (sha256 33b9a2b049d2089d4e48be7aad70447eac1a5f8bbf21543b49bf8930781b7f5e)
APPLIES_AFTER: docs/tasks/GUARD-PROTECT-01/ERRATA-001.md @ 1d49e7baee61d85a5c08b1d91932322e2b7a5346 (sha256 26bd5d9e4daa690595bf64952e710cffc5ac87221a696a5d660d16b9edbd1457)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER, 2026-11-08

## APPLICABILITY

APPLICABILITY: ERRATA-001에 따른 IMPLEMENTATION 재진입 결과가 커밋되기 전, PRECOMMIT_AUDIT에서 발견된 POSIX symlink 경로 판정 위험을 보완하기 위한 IMPLEMENTATION rollback 재진입 1회.

이 ERRATA는 rollback 승인이 아니다. 재진입과 이후 gate는 각각 별도의 Gate Authorization이 필요하다.

## CHANGED_FIELDS

CHANGED_FIELDS (위 재진입 1회에만 적용):
- IMPLEMENTATION_SAFETY_CONDITIONS.S0 (ERRATA-001의 대체 내용을 다시 대체)
- IMPLEMENTATION_SAFETY_CONDITIONS.S1 (ERRATA-001의 대체 내용을 다시 대체)
- 보완 범위와 통과 기준 (REMEDIATION_SCOPE, REMEDIATION_PRINCIPLES, REMEDIATION_PASS_CRITERIA 추가)

## RATIONALE

RATIONALE:
- ERRATA-001 재진입의 구현은 `.claude/hooks/guard.py`의 존재 확인 3곳(FROZEN_IF_EXISTS, TASK_CONTRACT, PREREG_ONCE_EXISTS)을 `os.path.exists(path)`에서 `os.path.exists(realpath(abspath(path)))`로 바꾸었다.
- 코드 해석상 POSIX에서 symlink 뒤에 `..`이 오는 경로는 수정 전 물리 경로로, 수정 후 문자열 정리 경로로 존재를 확인한다. 물리 경로에만 파일이 있으면 기존 DENY가 ASK로 바뀔 수 있다. PASS로 바뀌는 경우는 없다. 이 동작은 재현하지 않았으며 NOT_VERIFIED다.
- 이 변화는 INTENDED_DECISION_CHANGES 표 밖의 판정 변경일 수 있다.
- ERRATA-001의 S0(clean)와 S1(20a39f537c08c12e973a172c5755c699bb113922 시점 blob)은 커밋 전 수정 상태를 보존한 채 충족할 수 없고, restore는 금지되어 있다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:

- Ce: 이 ERRATA 문서만 추가한 커밋이다. parent = 1d49e7baee61d85a5c08b1d91932322e2b7a5346. 구현 파일은 stage하거나 커밋하지 않는다. Ce 생성 전후 아래 두 수정 파일의 작업 트리 blob은 같아야 한다.

- S0 SESSION_START_CHECK: HEAD = Ce, Work Order sha256 일치, ERRATA-001 sha256 일치. tracked 변경은 정확히 `.claude/hooks/guard.py`, `tests/test_agent_guard.py` 2개이고 staged 변경과 untracked 파일은 없다(ignored `.venv`와 허용 ignored 캐시 제외). ENVIRONMENT_ACCEPTANCE의 S0 항목 전부 충족. 인라인 인터프리터는 sys.prefix와 moneylab.__file__ 출력을 위한 지정 명령 1개만 허용한다.

- S1 원본 정체성: 아래 값과 다르면 STOP.
  - .claude/hooks/guard.py: 작업 트리 `git hash-object` = bfb0aea0a66ffdd0bfdd00305fb6e0996bfd9c82, `git rev-parse HEAD:<path>` = 1ee78a04aabdb01bb1a8cd818d24762ce77fc075
  - tests/test_agent_guard.py: 작업 트리 `git hash-object` = 64d691cce36b7eda8e4b1b62572e9f9cfed34fc6, `git rev-parse HEAD:<path>` = 660418236248dbba8ce99b4882a5378fc6abb6a2
  - .claude/settings.json: 작업 트리와 HEAD 모두 a863ba0a680bf961b13f1f099e468721d918d0ac
  - docs/agent_workflow.md: 작업 트리와 HEAD 모두 ecac3a4b6f6403d22e1d18336a7235f362fd5752

- REMEDIATION_SCOPE:
  - 이 재진입에서 수정할 수 있는 것은 `.claude/hooks/guard.py`의 `_exists` 함수(본문과 docstring)뿐이다.
  - `tests/test_agent_guard.py`는 수정하지 않고 S1의 작업 트리 blob을 유지한다.
  - 재진입 커밋의 파일 집합은 ERRATA-001 REENTRY_SCOPE의 2개 파일의 부분집합이다. Gate 표 COMMIT 행의 "필수 변경 3개 포함"은 커밋 20a39f537c08c12e973a172c5755c699bb113922로 충족된 것으로 본다.
  - 수정 후보: `return os.path.exists(path) or os.path.exists(_resolved(path))`

- REMEDIATION_PRINCIPLES:
  - 최소 변경
  - ERRATA-001 재진입의 수정 결과를 폐기하지 않는다. restore, reset, stash를 쓰지 않는다.
  - 테스트 삭제 금지, 기존 기대값 완화 금지
  - 신규 skip·xfail로 실패 은폐 금지
  - Guard 비활성화·우회 금지

- REMEDIATION_PASS_CRITERIA:
  - 커밋 20a39f537c08c12e973a172c5755c699bb113922의 guard가 DENY로 판정하는 파일 도구 호출은 수정 후에도 DENY다. 기존 DENY가 ASK 또는 PASS로 바뀌지 않는다.
  - Windows 기존 테스트 통과, 전체 pytest failed 0 / errors 0
  - Windows 필수 CI SUCCESS
  - Linux 신규 실패 0건, Linux 전체 실패는 기존 wrapper 2건 이내 (PR_CI에서 확인)
  - 기존 테스트 삭제·기대값 변경 없음, 신규 skip·xfail 없음
  - GUARD_PROTECTION_COMPLETE = NO 유지
  - POSIX symlink 사례의 실제 판정은 테스트하지 않으며 NOT_VERIFIED로 보고한다.

## UNCHANGED_FIELDS

UNCHANGED_FIELDS: 위에 적지 않은 Work Order와 ERRATA-001의 나머지 요구사항과 STOP 조건은 그대로 유지한다. C1, WORK_ORDER.md blob과 그 sha256, ERRATA-001 blob과 그 sha256, ALLOWED_FILES, PROTECTED_FILES, GATE_SEQUENCE, GATE_TRANSITION_RULES, REQUIRED_CI_CHECKS, MERGE_METHOD, ERRATA-001의 REENTRY_PASS_CRITERIA를 포함한다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
