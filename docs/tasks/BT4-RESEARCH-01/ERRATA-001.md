# ERRATA: BT4-RESEARCH-01 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-RESEARCH-01-ERRATA-001
TASK_ID: BT4-RESEARCH-01
TARGET_WORK_ORDER: docs/tasks/BT4-RESEARCH-01/WORK_ORDER.md @ f72a477174bae28d0baaa1251e587f9dc73cf6dd (sha256 eaf525e5c4469f0b76cd5ad2344c9267bbb240b689c7b9b5a9e89a9028b78720)
CI_IMPLEMENTATION_COMMIT: 1608e89344b178d69607ff7c6120a49fd47cccd3 (parent f72a477174bae28d0baaa1251e587f9dc73cf6dd, tree 009ab879c92b290bacbdb64c695b5490bb6864aa, report sha256 ad724cb20e4d2a981fe7841641bcc2c7910a052b1b6f07b6248b686a032b891a; 이 ERRATA는 Ci를 대체하지 않는다)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

## CHANGED_FIELDS

CHANGED_FIELDS:
- TEST_GATES (CLEAN_COMMIT_E2E local full pytest 판정에 한정된 예외 추가)
- E2E_GATES (위 예외의 적용 범위와 Ce 이후 재실행 명시)
- ALLOWED_ACTIONS.PR_CI (deferred 조건 확인 추가)
- ALLOWED_ACTIONS.MERGE (deferred 조건 해소 전 merge 금지)
- STOP_CONDITIONS (deferred test의 PR_CI 실패 추가)
- 새 절: DEFERRED_TEST_CONTRACT

UNCHANGED_FIELDS (명시적으로 바꾸지 않음): Work Order 결정 4와 FORBIDDEN_ACTIONS의 "새 worktree에 `.venv`나 junction 생성 금지", TEST_GATES의 Python·PYTHONPATH 지정과 import source 확인, `git diff --check`, 변경 파일 집합 = ALLOWED_FILES, report 구조 점검, E2E_GATES의 MC-V06 RUN_ROOT·worktree 확인, GATE_SEQUENCE, ALLOWED_FILES, PROTECTED_FILES, DESIGN_CONTRACT R1–R7, EVIDENCE_POLICY, DIAGNOSTICS_POLICY, WORKING_MATERIAL_POLICY, `docs/research_bt4_01_evidence_review.md`의 내용, source verification status, D1–D9, BT4 과학 결정, `tests/**`의 내용.

## TRIGGER

TRIGGER: CLEAN_COMMIT_E2E (Ci 1608e89344b178d69607ff7c6120a49fd47cccd3) = BLOCKED, 2026-10-26. 전체 pytest가 실패 2건으로 Work Order TEST_GATES의 "full pytest, failed 0 / errors 0"을 충족하지 못했다.

## OBSERVED_LOCAL_RESULT

OBSERVED_LOCAL_RESULT (CLAUDE_REPORTED):
- 작업 디렉터리: C:/MoneyLab-bt4-research-01
- 명령: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=C:/MoneyLab-bt4-research-01/src C:/MoneyLab-mc-v06/.venv/Scripts/python.exe -B -m pytest -rsx -p no:cacheprovider`
- import source: `C:\MoneyLab-bt4-research-01\src\moneylab\__init__.py`
- 결과: 2 failed, 1634 passed, 6 skipped, 1 deselected, 3 xfailed. pytest exit code 1
- 실패 test:
  - `tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through`
  - `tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0`
- 관찰된 사실 (FACT):
  - test helper `run_wrapped`(`tests/test_agent_guard.py:623-629`)가 `CLAUDE_PROJECT_DIR`를 test 대상 repository root인 C:/MoneyLab-bt4-research-01로 설정한다.
  - guard wrapper 명령이 `${CLAUDE_PROJECT_DIR}/.venv/Scripts/python.exe`를 실행하려 했고 "No such file or directory"로 실패했다(returncode 2, 기대값 0).
  - C:/MoneyLab-bt4-research-01에는 `.venv`가 없다.
  - test 후 worktree는 ignored 항목을 포함해 clean이었다.
- 추론 (INFERENCE, 검증하지 않음):
  - Ci는 markdown report 한 파일만 추가했으므로, 이 실패가 Ci의 product-code regression 때문이라는 증거는 없다.
  - 공식 CI(`.github/workflows/ci-tests.yml`)는 repository root에 `.venv`를 만들므로 local E2E와 environment topology가 다르다.

## ROOT_ENVIRONMENTAL_CONSTRAINT

ROOT_ENVIRONMENTAL_CONSTRAINT: Work Order 결정 4(WORKSPACE_SETUP, FORBIDDEN_ACTIONS, TEST_GATES)는 새 worktree에 `.venv`나 junction을 만드는 것을 금지한다. 위 두 test는 repository-local `.venv`를 전제로 하므로, 이 계약 아래의 local 환경에서는 그 전제를 충족할 수 없다.

## NORMATIVE_DECISION

NORMATIVE_DECISION:
- A. Work Order 결정 4의 "새 worktree에 `.venv`나 junction을 만들지 않는다"는 그대로 유지한다.
- B. BT4-RESEARCH-01의 CLEAN_COMMIT_E2E local TEST_GATES에서만, DEFERRED_TESTS 두 개의 local failure를 `ENVIRONMENT_DEPENDENT_DEFERRED_TO_PR_CI`로 분류할 수 있다.
- C. 이 분류는 해당 test를 PASS로 간주한다는 뜻이 아니다. local 결과는 계속 "2 failed"로 기록한다.
- D. CLEAN_COMMIT_E2E의 나머지 조건은 모두 그대로 적용한다: commit integrity, report integrity, Work Order integrity, static checks, 나머지 test, test 후 cleanliness, protected state.
- E. PUSH 이후 PR_CI에서 공식 CI가 repository-local `.venv`를 만든 환경으로 전체 canonical test suite를 실행해야 한다.
- F. PR_CI에서 DEFERRED_TESTS 중 하나라도 실패하면 PR_CI = FAIL이며 MERGE를 금지한다.
- G. PR_CI에서 전체 suite가 통과해야만 이 deferred 조건이 해소된다.
- H. 이 ERRATA는 BT4 통계·과학 결정, D1–D9, report 내용, source status를 바꾸지 않는다.

## DEFERRED_TEST_CONTRACT

DEFERRED_TEST_CONTRACT:
- DEFERRED_TESTS:
  - `tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through`
  - `tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0`
- 분류: `ENVIRONMENT_DEPENDENT_DEFERRED_TO_PR_CI`
- 적용 범위: BT4-RESEARCH-01의 CLEAN_COMMIT_E2E local TEST_GATES(재실행 포함)에만 적용한다. 다른 task와 다른 gate에는 적용하지 않는다.
- 적용 조건: local 실행에서 failed가 정확히 DEFERRED_TESTS 두 개이고, 두 실패 모두 `${CLAUDE_PROJECT_DIR}/.venv/Scripts/python.exe` 부재가 원인이어야 한다. 그 밖의 failed나 error가 하나라도 있으면 CLEAN_COMMIT_E2E = FAIL이다.
- test 파일은 삭제·수정·skip 처리하지 않는다.
- Ce 이후의 CLEAN_COMMIT_E2E는 Ce를 HEAD로 해서 다시 실행한다. Ce는 이 ERRATA 파일 하나만 추가한다.

## PR_CI_RESOLUTION_CONDITION

PR_CI_RESOLUTION_CONDITION:
- PUSH 이후 PR_CI에서 GitHub Actions `ci-tests` workflow가 repository root에 `.venv`를 만들고 전체 canonical suite(`pytest -rsx`)를 실행한다.
- 해소 조건: workflow 성공, 전체 suite failed 0 / errors 0, 그리고 CI log에서 DEFERRED_TESTS 두 개가 실행되어 passed로 표시될 것.
- DEFERRED_TESTS 중 하나라도 failed면 PR_CI = FAIL이고 MERGE를 금지한다.
- DEFERRED_TESTS가 CI에서 skipped로 표시되면 deferred 조건은 해소되지 않은 것으로 보고, MERGE 전에 멈추고 사용자 결정을 요청한다.
- PR CI 결과의 증거 등급은 INDEPENDENT다.

## NON_EFFECTS

NON_EFFECTS: 이 ERRATA는 BT4 통계·과학 결정, D1–D9, `docs/research_bt4_01_evidence_review.md`의 내용, source verification status, `tests/**`, guard·hook·settings, `.venv` 관련 금지, MC-V06 산출물과 RUN_ROOT를 바꾸지 않는다.

## SCRATCHPAD_NOTE

SCRATCHPAD_NOTE:
- CLEAN_COMMIT_E2E 중 repository 밖 Claude session scratchpad에 `bt4_e2e_pre_ignored_attempt1.txt`가 새로 만들어졌다. Claude가 test 전 `git status --short --ignored --untracked-files=all` 출력을 기록하려고 만든 파일이다.
- 분류: repository artifact가 아니다. evidence source가 아니다. report에 포함되지 않는다. commit 대상이 아니다.
- 이 파일은 삭제하지 않고 그대로 보존한다.
- 이 파일 생성이 CLEAN_COMMIT_E2E 승인 범위 안이었는지는 이 ERRATA에서 판단하지 않는다.
