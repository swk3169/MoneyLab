# ERRATA: DOCS-ALIGN-01 ERRATA-002

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: DOCS-ALIGN-01-ERRATA-002
TASK_ID: DOCS-ALIGN-01
TARGET_WORK_ORDER: docs/tasks/DOCS-ALIGN-01/WORK_ORDER.md @ 2ebcbac3850ad414cddbecc0a61d9d0eba3fbcca (sha256 7bed5713ea5a33d5148a46ae2bd60f280a28e542f0ba9386a8ded05d491d5eda)
PRIOR_ACCEPTED_ERRATA: docs/tasks/DOCS-ALIGN-01/ERRATA-001.md @ 0375dc6044a890c5883e307ef87d6b50e1e3a692 (sha256 ebc0c605ec1a918300013cba36345b24aa0816236074b1e2fc74ccb996f6d5e8). 효력 유지.
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자, 2026-10-28

## CHANGED_FIELDS

CHANGED_FIELDS:
- Metadata.MERGE_BASE_SHA (새 필드: 원격 main 기대값을 설계 기준선과 분리)
- STOP_CONDITIONS (두 항목만 변경: 첫 항목의 원격 main 비교 대상 CANONICAL_BASE_SHA → MERGE_BASE_SHA, "CI 실패"의 뜻을 필수 Windows job과 workflow run 결론으로 정의. 그 밖의 항목은 원문 그대로)
- ACCEPTANCE_CRITERIA.AC1 (PR 파일 집합에 이 ERRATA 추가. ERRATA-001이 바꾼 필드를 전체로 다시 정의)
- E2E_GATES (Ce2 관계 추가. ERRATA-001이 바꾼 필드를 전체로 다시 정의)
- 새 절: BASELINE_REVALIDATION (새 기준선에서의 PUSH·PR_CI·MERGE 사전 검증·POST_MERGE_AUDIT 조건)

UNCHANGED_FIELDS (명시적으로 바꾸지 않음): WORK_ORDER_CONTRACT_VERSION(v1.1), CANONICAL_BASE_SHA, CANONICAL_BASE_TREE, BASE_BLOBS, DESIGN_CONTRACT E1–E10, APPROVED_TEXT 전체, ACCEPTANCE_CRITERIA AC2–AC8, TEST_GATES(ERRATA-001이 정한 내용 그대로), ALLOWED_FILES, PROTECTED_FILES, INVARIANT, ALLOWED_ACTIONS, FORBIDDEN_ACTIONS, REQUIRED_EVIDENCE, REQUIRED_REPORT, GATE_SEQUENCE, GATE_TRANSITION_RULES.

## RATIONALE

RATIONALE:
- PR #34(GOV-AUTOMATION-01)가 merge되어 원격 main이 CANONICAL_BASE_SHA `0848cfc6ddf04d7ebdeb5d5e66de47ee1760c9cf`에서 `3674c1e1111b235eb1961d6b9997f6276a7cbcee`로 바뀌었고, STOP_CONDITIONS의 "원격 main ≠ CANONICAL_BASE_SHA"에 해당하게 되었다.
- 다음 Git 사실(GIT_VERIFIABLE)에 따라 구현과 설계 기준은 새 main에서도 그대로 유효하다.
  - ARCHITECTURE.md blob은 두 main에서 모두 `be56b5b0449e617eb32a71aef2a03b04aaf6c661`, README.md blob은 모두 `c2c268d6caa63720e839e2f3fa548a7f375df482`로 BASE_BLOBS와 같다.
  - 두 main 사이에 ARCHITECTURE.md, README.md, docs/tasks/DOCS-ALIGN-01/의 변경은 0이다. 변경 파일은 PR #34의 CLAUDE.md, docs/agent_workflow.md, docs/tasks/GOV-AUTOMATION-01/WORK_ORDER.md, docs/tasks/README.md, docs/tasks/TEMPLATE.md뿐이다.
  - `0848cfc6…`는 `3674c1e1…`의 조상이다(`3674c1e1…`의 parent1).
  - PR #33 head `966be9ec04edf20681cf4cb6d122024fd3d43d44`와 새 main의 merge-base는 `0848cfc6…`다.
- 따라서 CANONICAL_BASE_SHA와 E1–E10은 설계 기준으로 유지하고, 원격 main의 기대값만 새 필드 MERGE_BASE_SHA로 분리한다.
- 이전 CI run `40656822812`는 이전 기준선의 merge ref를 시험했으므로 새 기준선의 증거로 쓰지 않는다.
- STOP_CONDITIONS의 "CI 실패"는 정의가 없어, 필수가 아닌 Linux experimental job(`continue-on-error: true`)의 실패까지 포함하는지 모호했다. AC8과 ERRATA-001 TEST_GATES는 Windows `pytest` job의 성공만 요구하므로, 이 ERRATA는 "CI 실패"를 "PR CI의 필수 Windows `pytest` job 실패 또는 `ci-tests` workflow run의 최종 결론 실패"로 정의한다(사용자 결정 OPTION_A). Linux experimental job의 실패는 자동으로 PASS 처리하지 않고 원인과 필수 CI에 미치는 영향을 보고한다.
- rebase·amend·force push 없이 이 ERRATA의 커밋(Ce2)을 Ci 뒤에 추가하고, 새 head에서 CI를 다시 검증한다. 이 task는 계약 v1.1이며 v1.2 실행 권한은 적용하지 않는다.
## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- Metadata.MERGE_BASE_SHA: 3674c1e1111b235eb1961d6b9997f6276a7cbcee (이 ERRATA의 커밋 Ce2 이후의 PUSH, PR_CI, MERGE, POST_MERGE_AUDIT에서 원격 main의 기대값. CANONICAL_BASE_SHA는 C1의 부모, BASE_BLOBS, E1–E10 줄 번호, AC3 hunk의 기준으로 계속 쓴다)
- STOP_CONDITIONS:
  - base·HEAD·tree 불일치, 원격 main ≠ MERGE_BASE_SHA, Work Order sha256 불일치
  - BASE_BLOBS 불일치, 또는 E1–E8이 인용한 base 줄의 내용이 실제와 다름
  - ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
  - ALLOWED_FILES의 A/M 표기와 base 상태 불일치
  - 구현 결과가 E10과 다름, APPROVED_TEXT 변경 필요, 근거 없는 서술 필요
  - NON_GOALS 항목을 건드려야만 일관성이 맞는 경우
  - guard deny, 권한 창 거절
  - CI 실패 (PR CI의 필수 Windows `pytest` job 실패 또는 `ci-tests` workflow run의 최종 결론 실패)
  - 계약 모순, 상위 규칙과 충돌
  - 예상하지 못한 untracked 파일
- ACCEPTANCE_CRITERIA.AC1: 구현 커밋 파일 집합 = ALLOWED_FILES. PR 전체 파일 집합 = ALLOWED_FILES ∪ {docs/tasks/DOCS-ALIGN-01/WORK_ORDER.md, docs/tasks/DOCS-ALIGN-01/ERRATA-001.md, docs/tasks/DOCS-ALIGN-01/ERRATA-002.md}.
- E2E_GATES:
  - NOT_REQUIRED (문서 전용). 대체 확인:
    - C1의 부모 = CANONICAL_BASE_SHA.
    - Ce(ERRATA-001 커밋)의 부모 = C1.
    - 구현 커밋 Ci의 부모 = Ce.
    - Ce2(이 ERRATA의 커밋)의 부모 = Ci.
    - Ci의 커밋 파일 집합 = ALLOWED_FILES.
    - Ce2의 커밋 파일 집합 = {A docs/tasks/DOCS-ALIGN-01/ERRATA-002.md} 하나.
    - Ce2 tree의 ARCHITECTURE.md blob = c57bf469b857913e6002b124d35c81faf5908e54 (E10 기대 결과).
    - Ce2 tree의 README.md blob = 8656b4b981d8723979249459cb97879515526707 (E10 기대 결과).
    - rebase, amend, force push는 하지 않는다.
- BASELINE_REVALIDATION:
  - 적용 범위:
    - Ce2(이 ERRATA의 커밋) 이후의 PUSH, PR_CI, MERGE, POST_MERGE_AUDIT에 적용한다.
    - IMPLEMENTATION, PRECOMMIT_AUDIT, COMMIT, CLEAN_COMMIT_E2E의 증거는 유지한다(Ci와 BASE_BLOBS 불변).
  - PUSH:
    - 원격 main = MERGE_BASE_SHA일 때만 TARGET_BRANCH를 fast-forward로 1회 push한다.
    - push 후 원격 feature branch SHA = Ce2.
  - PR_CI:
    - PR #33 head SHA = Ce2.
    - 원격 feature branch SHA = Ce2.
    - Ce2에 연결된 새 pull_request run이 있고, 그 run의 head SHA = Ce2.
    - 그 run이 시험한 merge ref의 base = MERGE_BASE_SHA. 로그 또는 GitHub API로 확인하고, 확인할 수 없으면 미충족이다.
    - Windows 필수 job `pytest` = SUCCESS.
    - `ci-tests` workflow run의 최종 결론 = SUCCESS.
    - ERRATA-001 TEST_GATES의 CI hygiene 조건 1–5를 그 새 run에서 충족한다.
    - CI_HYGIENE_VERIFIED = YES는 사용자가 수락한 뒤에만 선언한다.
    - 필수가 아닌 Linux experimental job이 실패하면 자동으로 PASS 처리하지 않고, 실패 원인과 필수 CI에 미치는 영향을 보고한다.
    - 이전 run `40656822812`의 증거는 쓰지 않는다.
    - CI 자동 실행을 가정하지 않는다. 새 run이 없으면 멈추고 보고한다.
  - MERGE 사전 검증(읽기 전용, 하나라도 충족되지 않으면 STOP):
    - PR #33 = OPEN.
    - draft = false.
    - base branch = main.
    - head branch = docs/docs-align-01.
    - PR head SHA = Ce2.
    - 원격 feature branch SHA = Ce2.
    - PR 커밋 = 4개(C1, Ce, Ci, Ce2).
    - PR 변경 파일 = AC1의 5개.
    - Windows 필수 CI = SUCCESS(위 PR_CI 조건).
    - ERRATA-001 CI hygiene 조건 1–5 충족.
    - CI_HYGIENE_VERIFIED = YES(사용자 수락).
    - GitHub mergeable = MERGEABLE.
    - 원격 main = MERGE_BASE_SHA.
    - merge는 사용자가 GitHub UI에서 Create a merge commit으로 실행한다. Claude의 merge 실행은 승인되지 않는다(v1.1).
  - POST_MERGE_AUDIT(읽기 전용, `git merge-tree --write-tree` 등 객체를 만드는 명령은 쓰지 않는다):
    - merge commit 부모 수 = 2.
    - parent1 = MERGE_BASE_SHA.
    - parent2 = Ce2.
    - MERGE_BASE_SHA..main의 first-parent 범위의 새 merge commit = 1개.
    - `git diff MERGE_BASE_SHA <merge>`의 경로 = PR #33의 5개 경로이고, 각 blob = Ce2 tree의 같은 경로 blob.
    - `git diff Ce2 <merge>`의 경로 = PR #34가 바꾼 5개 경로이고, 각 blob = MERGE_BASE_SHA tree의 같은 경로 blob.
    - Work Order SHA-256 = 7bed5713ea5a33d5148a46ae2bd60f280a28e542f0ba9386a8ded05d491d5eda.
    - ERRATA-001 SHA-256 = ebc0c605ec1a918300013cba36345b24aa0816236074b1e2fc74ccb996f6d5e8.
    - ERRATA-002 SHA-256 = Ce2에서 확정한 값과 같음.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1–3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
- ERRATA-001의 효력(TEST_GATES, CI hygiene 조건 1–5, RESIDUAL_RISK)을 유지한다. 이 ERRATA가 다시 정의한 AC1과 E2E_GATES는 ERRATA-001의 내용을 포함한다.
- 기존 C1, Ce, Ci는 바꾸지 않는다. 이 task에는 계약 v1.2의 실행 권한을 적용하지 않는다.
