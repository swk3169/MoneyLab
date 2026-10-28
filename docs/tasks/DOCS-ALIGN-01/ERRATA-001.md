# ERRATA: DOCS-ALIGN-01 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: DOCS-ALIGN-01-ERRATA-001
TASK_ID: DOCS-ALIGN-01
TARGET_WORK_ORDER: docs/tasks/DOCS-ALIGN-01/WORK_ORDER.md @ 2ebcbac3850ad414cddbecc0a61d9d0eba3fbcca (sha256 7bed5713ea5a33d5148a46ae2bd60f280a28e542f0ba9386a8ded05d491d5eda)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자, 2026-10-28

## CHANGED_FIELDS

CHANGED_FIELDS:
- TEST_GATES (hygiene 항목 교체)
- ACCEPTANCE_CRITERIA.AC1 (PR 파일 집합에 이 ERRATA 추가, Ce 고정에 따른 정합성)
- E2E_GATES (구현 커밋의 부모를 이 ERRATA의 Ce로, Ce 고정에 따른 정합성)

UNCHANGED_FIELDS (명시적으로 바꾸지 않음): GOAL, NON_GOALS, ALLOWED_ACTIONS, FORBIDDEN_ACTIONS, ALLOWED_FILES, PROTECTED_FILES, INVARIANT, DESIGN_CONTRACT E1–E10, APPROVED_TEXT 전체, ACCEPTANCE_CRITERIA AC2–AC8, REQUIRED_EVIDENCE, REQUIRED_REPORT, STOP_CONDITIONS, GATE_SEQUENCE, GATE_TRANSITION_RULES.

## RATIONALE

RATIONALE: IMPLEMENTATION gate에서 TEST_GATES의 로컬 hygiene grep은 패턴 문자열 `.env` 때문에 guard [env] 규칙에 DENY되었다. guard·hook·settings는 바꾸지 않고 우회하지 않는다. 같은 목적의 기존 검사 tests/test_repo_hygiene.py가 PR CI Windows `pytest` job에서 실행된다. docs/tasks/README.md §6에 따라 이 ERRATA는 Ce 커밋으로 고정되므로, PR 파일 집합(AC1)과 구현 커밋의 부모(E2E_GATES)를 함께 맞춘다. 그 밖의 계약은 바꾸지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- TEST_GATES:
  - 변경 파일 집합 = {ARCHITECTURE.md, README.md}, PROTECTED diff 0, untracked 0
  - `git diff --check` 깨끗함
  - hunk 대조: `git diff -U0 0848cfc6ddf04d7ebdeb5d5e66de47ee1760c9cf -- ARCHITECTURE.md README.md`의 hunk 위치·내용이 E1–E8과 같고 hunk 수가 6 / 4다
  - 기대 결과 일치: 각 파일 blob이 E10 정의와 같고 줄 수가 235 / 537이다
  - claim→evidence 표 작성(AC5)
  - 경로 실재: AC6의 경로가 CANONICAL_BASE tree에 있다(`git cat-file -e` 또는 `git ls-tree`)
  - 표 열 수 확인(AC6)
  - hygiene (로컬): 로컬 hygiene grep은 수행하지 않는다. IMPLEMENTATION 보고에 "로컬 hygiene grep 미실행(guard [env], ERRATA-001)"을 기록한다. 미실행 검사를 PASS로 소급 처리하지 않는다.
  - hygiene (CI, 필수): 대상 테스트는 `tests/test_repo_hygiene.py::test_no_secrets_or_personal_data_in_addable_files`와 `tests/test_repo_hygiene.py::test_no_forbidden_or_large_tracked_files`다. 다음 조건을 모두 만족해야 CI_HYGIENE_VERIFIED = YES다.
    1. PR CI Windows `pytest` job이 성공했다.
    2. 두 대상 테스트가 그 job에서 수집·실행되었다는 증거가 있다.
    3. 두 대상 테스트가 skip 또는 xfail로 처리되지 않았다는 증거가 있다.
    4. 1–3의 증거가 하나라도 부족하면 CI_HYGIENE_VERIFIED = NO다.
    5. CI_HYGIENE_VERIFIED = YES 이전에는 MERGE를 승인하지 않는다.
    CI hygiene 확인 결과는 INDEPENDENT 증거로 PR_CI gate에서 보고한다. IMPLEMENTATION gate에서는 이 항목을 PENDING으로 보고하고 PASS로 표시하지 않는다.
  - guard 설정 변경, 차단 문자열의 제거·변형, 그 밖의 우회로 같은 검사를 대신하지 않는다.
  - 로컬 pytest는 요구하지 않는다: 두 파일은 코드·테스트가 내용을 읽지 않고, TARGET_WORKTREE에 `.venv`가 없으며 이 task는 `.venv`를 만들지 않는다.
- ACCEPTANCE_CRITERIA.AC1: 구현 커밋 파일 집합 = ALLOWED_FILES. PR 전체 파일 집합 = ALLOWED_FILES ∪ {docs/tasks/DOCS-ALIGN-01/WORK_ORDER.md, docs/tasks/DOCS-ALIGN-01/ERRATA-001.md}.
- E2E_GATES:
  - NOT_REQUIRED (문서 전용). 대체 확인: clean 구현 커밋에서 두 파일 blob이 E10과 같고, 커밋 파일 집합 = ALLOWED_FILES이며, 구현 커밋의 부모 = Ce(이 ERRATA의 커밋)이고 Ce의 부모 = C1이다.

## RESIDUAL_RISK

RESIDUAL_RISK:
- 로컬 grep과 tests/test_repo_hygiene.py의 검출 범위는 같지 않다. 테스트는 MSYS 형식 home 경로(`/c/Users/…`), `/home/` 경로, 문서 속 `.env` 문자열 언급, 할당 형태가 아닌 단어 `token`·`secret`·`private key`를 검출하지 않는다.
- 이 차이는 이 task에서 해소하지 않는다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1–3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
- 실행하지 않은 로컬 hygiene grep을 PASS로 소급 처리하지 않는다. guard 설정 변경, 명령 변형, 우회는 허용하지 않는다.
