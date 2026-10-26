# ERRATA: BT4-RESEARCH-01 ERRATA-002

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-RESEARCH-01-ERRATA-002
TASK_ID: BT4-RESEARCH-01
TARGET_WORK_ORDER: docs/tasks/BT4-RESEARCH-01/WORK_ORDER.md @ f72a477174bae28d0baaa1251e587f9dc73cf6dd (sha256 eaf525e5c4469f0b76cd5ad2344c9267bbb240b689c7b9b5a9e89a9028b78720)
AMENDS_ERRATA: docs/tasks/BT4-RESEARCH-01/ERRATA-001.md @ d0e3f05b49d813d161e88db8806d07a1a4c8cd3f (sha256 de208730b2cad44ab266cc906c0e41306b86653980a8a59da4a07807758b3718)
SUPERSEDES_ERRATA: NONE (ERRATA-001은 유효하며, 이 ERRATA는 ERRATA-001의 PR_CI_RESOLUTION_CONDITION에 대체 증거 경로 하나만 추가한다)
STATUS: ACCEPTED
ACCEPTED_BY: USER

## CHANGED_FIELDS

CHANGED_FIELDS:
- ERRATA-001 PR_CI_RESOLUTION_CONDITION의 "CI log에서 DEFERRED_TESTS 두 개가 실행되어 passed로 표시될 것" (대체 증거 경로 추가)
- 새 절: ELIMINATIVE_CI_EVIDENCE_RULE

UNCHANGED_FIELDS (명시적으로 바꾸지 않음): ERRATA-001의 NORMATIVE_DECISION A–H, DEFERRED_TESTS 목록, DEFERRED_TEST_CONTRACT, "failed면 PR_CI = FAIL이고 MERGE 금지", "skipped면 해소되지 않음, MERGE 전에 멈추고 사용자 결정 요청", Work Order 결정 4, TEST_GATES, E2E_GATES, GATE_SEQUENCE, ALLOWED_FILES, PROTECTED_FILES, DESIGN_CONTRACT R1–R7, EVIDENCE_POLICY, `docs/research_bt4_01_evidence_review.md`의 내용, source verification status, D1–D9, BT4 과학 결정, `tests/**`, `.github/**`.

## TRIGGER

TRIGGER: PR_CI = BLOCKED, 2026-10-26. PR #25, GitHub Actions run 40264041765(workflow `ci-tests`, event `pull_request`, head d0e3f05b49d813d161e88db8806d07a1a4c8cd3f)는 success였고 결과는 `collected 1646 items / 1 deselected / 1645 selected`, `1636 passed, 6 skipped, 1 deselected, 3 xfailed`, failed 0, errors 0이었다. CI 명령이 `pytest -rsx`이므로 passed test는 개별 줄로 표시되지 않았고, ERRATA-001이 요구한 "DEFERRED_TESTS가 passed로 표시"를 log에서 직접 확인할 수 없었다.

## RATIONALE

RATIONALE: `-rsx` 출력은 skipped와 xfailed test를 모두 위치와 함께 나열하고, failed와 error는 별도 목록과 요약 수치로 보인다. 따라서 어떤 test가 수집·선택되었고 skipped, xfailed, deselected, failed, error 목록 어디에도 없다면, pytest 결과 범주상 passed 외의 가능성은 남지 않는다. 이 ERRATA는 workflow나 test를 바꾸지 않고, 이 추론을 엄격한 조건 아래에서만 증거로 인정하는 좁은 규칙을 정한다.

## ELIMINATIVE_CI_EVIDENCE_RULE

ELIMINATIVE_CI_EVIDENCE_RULE:
- 원칙 유지: ERRATA-001의 원칙은 그대로다. 직접 증거(CI log의 개별 PASSED 줄)가 있으면 그것을 쓴다. workflow나 check가 green이라는 사실만으로 개별 test의 PASSED를 추론하는 것은 계속 금지한다.
- 적용 대상: ERRATA-001이 지정한 DEFERRED_TESTS 두 개에만 적용한다.
  - `tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through`
  - `tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0`
- 적용 시점: PR_CI에서, 평가 대상 CI run의 log에 해당 test의 개별 PASSED 줄이 pytest 출력 형식 때문에 없는 경우에만 적용한다.
- 인정 조건: 각 test마다 아래 E1–E9를 모두 확인할 수 있을 때만 그 test의 PASSED를 eliminative CI evidence로 인정한다.
  - E1. canonical pytest step이 정상 종료했고(job conclusion success), pytest 요약에서 failed = 0, errors = 0이다.
  - E2. collected, deselected, selected 수와 passed, skipped, xfailed(xpassed가 있으면 그 수도) 수가 CI log에서 확인되고, selected = passed + skipped + xfailed + xpassed + failed + errors가 성립한다.
  - E3. 해당 test가 평가 대상 commit의 repository에 존재하고 canonical collection(`testpaths`)에 포함된다. 확인 방법: 평가 대상 commit의 소스 확인, 또는 cache와 bytecode를 만들지 않는 local `pytest --collect-only -q -p no:cacheprovider`(PYTHONDONTWRITEBYTECODE=1, `python -B`)에서 해당 node ID가 나오는 것.
  - E4. CI log의 SKIPPED 목록 어디에도 해당 test(파일:행 또는 node ID)가 없다.
  - E5. CI log의 XFAIL·XPASS 목록 어디에도 해당 test가 없다.
  - E6. 해당 test에 deselection 대상 marker(현재 `addopts = "-m 'not network'"`의 `network`)가 없다. 함수 decorator, class, module의 `pytestmark`를 모두 확인한다.
  - E7. selection configuration상 해당 test가 다른 방식으로 제외되지 않는다: `pyproject.toml`의 `addopts`·`testpaths`, CI 명령의 추가 인자(`-k`, `-m`, `--deselect`, `--ignore` 없음), `conftest.py`의 collection 변경 hook(`pytest_collection_modifyitems`, `pytest_ignore_collect` 등)을 확인한다.
  - E8. CI log의 FAILED·ERROR 목록 어디에도 해당 test가 없다.
  - E9 (보조 증거, count reconciliation). 같은 commit 내용에 대한 local CLEAN_COMMIT_E2E에서 failed가 정확히 DEFERRED_TESTS 두 개였고, CI의 passed 수가 local passed 수보다 정확히 2 많으며, skipped·deselected·xfailed 수와 목록이 local과 일치한다. E9는 E1–E8을 대신하지 않는다.
- 하나라도 확인할 수 없으면: 해당 test의 deferred condition은 NOT_RESOLVED이고 PR_CI = BLOCKED이다. 해당 test가 FAILED나 ERROR 목록에 있으면 PR_CI = FAIL이다. SKIPPED 목록에 있으면 ERRATA-001에 따라 해소되지 않으며 MERGE 전에 멈춘다.
- 기록 방식: 이 규칙으로 해소한 경우 PR_CI 보고에 `EVIDENCE_TYPE: ELIMINATIVE_CI_EVIDENCE`라고 쓰고, 직접 PASSED 줄이 있는 경우의 `EVIDENCE_TYPE: DIRECT_CI_EVIDENCE`와 구분한다. CI log에서 읽은 사실(수치, 목록)은 INDEPENDENT이고, E1–E9를 조합한 판정은 CLAUDE_REPORTED이다.
- 평가 대상 run: PR_CI 판정은 MERGE 시점 PR head commit에 대해 실행된 `ci-tests` run으로 한다. 이 ERRATA를 commit해 PR head가 바뀌면, 이전 head에 대한 run(예: 40264041765, head d0e3f05b49d813d161e88db8806d07a1a4c8cd3f)은 보조 기록으로만 남기고 판정에는 새 head의 run을 쓴다.

## NON_EFFECTS

NON_EFFECTS: 이 ERRATA는 일반적인 MoneyLab test 정책, 다른 task와 향후 task의 CI 증거 기준, workflow(`.github/**`), `tests/**`, BT4 통계·과학 결론, `docs/research_bt4_01_evidence_review.md`의 내용, source verification status, D1–D9, BT4 implementation을 바꾸지 않는다.
