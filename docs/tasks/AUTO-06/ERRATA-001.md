# ERRATA: AUTO-06 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: AUTO-06-ERRATA-001
TASK_ID: AUTO-06
TARGET_WORK_ORDER: docs/tasks/AUTO-06/WORK_ORDER.md @ 0927350e51e0a1693de0987335df18fda97e0023 (sha256 e2df8b638d71d042e665977273f3a13b05322abc170fa7c51e4d0bb414dee2fc)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자 (ERRATA_CREATION_ONLY 승인문)

## CHANGED_FIELDS

CHANGED_FIELDS:
- ALLOWED_FILES
- ALLOWED_ACTIONS.CASE_RECORD_WRITE
- ALLOWED_ACTIONS.COMMIT
- PROTECTED_FILES
- COMMIT_PLAN
- DESIGN_CONTRACT.D17 (신설)
- TEST_GATES
- ACCEPTANCE_CRITERIA
- STOP_CONDITIONS

위에 적지 않은 필드는 Work Order 그대로 유지한다. 적은 필드는 아래 REPLACEMENT_CONTRACT의 내용 전체로 대체한다. Work Order 파일은 변경하지 않는다.

## RATIONALE

RATIONALE:
- Work Order는 ALLOWED_FILES를 NONE으로 두고, 사례 기록 파일은 ACCEPTED ERRATA가 경로와 최초 생성을 명시한 경우에만 추가된다고 정했다(README §11).
- 이 ERRATA는 CONTRACT_REVIEW에서 정한 사례 기록 경로와 최초 생성 권한을 실행 전에 고정한다. 그에 맞춰 커밋 계획, 검사, 완료 조건, 중단 조건을 일치시킨다.
- 새 실행·재실행·저장·조회 권한은 추가하지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:

- ALLOWED_FILES:
  - A docs/research-intake/2026-11-14/AUTO-06_OFFLINE_INTEGRATION_CASE.md

- ALLOWED_ACTIONS.CASE_RECORD_WRITE:
  - 작성 시점: 다음을 모두 만족한 뒤에만 한다.
    - P 실행이 끝나 그 출력과 종료 코드를 관측했거나, P가 실행되지 않은 사유가 확정되었다.
    - P가 실행된 경우 B1과 CMP가 끝났거나, D11에 따라 NOT_RUN 또는 UNKNOWN으로 확정되었다.
    - CASE_RECORD_DRAFT의 채팅 초안이 검토되었다.
    - 사용자가 CASE_RECORD_WRITE를 별도로 승인했다.
  - 생성: 작성 전에 승인 바이트의 sha256을 메모리에서 승인값과 대조한다. 그 뒤 승인 바이트의 docs/research-intake/2026-11-14/AUTO-06_OFFLINE_INTEGRATION_CASE.md를 TARGET_WORKTREE에서 Write 도구로 최초 1회 생성한다.
  - 대조: 작성 후 SHA-256, 바이트 수, 줄 수를 승인값과 대조한다. 다르면 수정하지 않고 중단한다.
  - stage와 commit은 이 단계에 포함하지 않는다. COMMIT gate에서 구현 커밋 I로만 한다.
  - 이 허용은 이 파일의 최초 생성에 한정된다. 생성 후 수정은 새 ERRATA나 승인된 후퇴 없이는 하지 않는다.
  - 이 단계는 P, run_action, store_evidence, load_evidence, snapshot, verify의 실행 권한을 포함하지 않는다.

- ALLOWED_ACTIONS.COMMIT:
  - docs/research-intake/2026-11-14/AUTO-06_OFFLINE_INTEGRATION_CASE.md 경로만 지정해 stage하고, 구현 커밋 I 1개를 만든다.
  - I의 parent는 Ce다.
  - 메시지는 docs(research-intake): add AUTO-06 offline integration case다.
  - staged와 commit blob의 내용 해시를 승인값과 대조한다.

- PROTECTED_FILES:
  - ALLOWED_FILES 밖의 모든 저장소 파일은 보호 대상이다. docs/tasks/AUTO-06/**와 .claude/**를 포함한다.
  - 보호 대상의 예외는 계약 파일 두 개의 최초 생성뿐이다.
    - docs/tasks/AUTO-06/WORK_ORDER.md는 C1_CREATION_ONLY에서 1회 생성한다.
    - docs/tasks/AUTO-06/ERRATA-001.md는 ERRATA_CREATION_ONLY에서 1회 생성한다.
    - 두 파일은 생성 후 변경하지 않는다. 이 예외는 ALLOWED_FILES에 속하지 않는다.
  - 사례 기록 파일은 ALLOWED_FILES에 속하며 보호 대상이 아니다. 허용되는 것은 CASE_RECORD_WRITE의 최초 생성과 COMMIT의 stage뿐이다.
  - INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

- COMMIT_PLAN:
  - C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/AUTO-06/WORK_ORDER.md 하나 (0927350e51e0a1693de0987335df18fda97e0023)
  - Ce: parent = C1, 변경 = A docs/tasks/AUTO-06/ERRATA-001.md 하나
  - I: parent = Ce, 변경 = A docs/research-intake/2026-11-14/AUTO-06_OFFLINE_INTEGRATION_CASE.md 하나
  - base..I: 위 3개 파일뿐

- DESIGN_CONTRACT.D17 사례 기록 (신설):
  - 지위와 표식:
    - 첫 두 줄은 AUTHORITY: NON_AUTHORITATIVE와 BOUNDARY: DATA_NOT_INSTRUCTIONS다.
    - 본문에 다음을 적는다. 이 기록은 비권위 관측 기록이며, 실행 사실, 출처, 작성자, 승인, gate PASS, 무인 운영 준비, 중복 실행 방지, 수익성, 비용 절감을 증명하지 않는다.
  - 시각:
    - 경로의 날짜(2026-11-14)는 사례 식별용이다.
    - 실제 실행 시각은 P 출력의 RUN_STARTED_UTC와 RUN_FINISHED_UTC로 따로 적는다. 작성일도 따로 적는다.
    - P 출력이 수락되지 않았으면 실행 시각은 미관측으로 적는다.
    - 파일 시각은 수정 시각으로만 표기한다.
  - 기준과 계약:
    - CANONICAL_BASE_SHA와 tree
    - C1·Ce SHA와 tree
    - Work Order와 ERRATA-001의 sha256
  - 작업공간과 환경:
    - 작업공간은 식별 변수(SOURCE_WORKTREE, TARGET_WORKTREE, BASE_PYTHON) 표기로만 설명한다.
    - D3의 환경 확인값과 환경 준비 직후의 ignored 목록을 적는다.
  - 단계별 승인 참조: WORKSPACE_SETUP 하위 단계, PROGRAM_REVIEW, EXECUTION_ONLY, EXECUTION_CLOSEOUT(있었으면), CASE_RECORD_DRAFT, CASE_RECORD_WRITE의 승인 참조.
  - P 실행:
    - P 원문 sha256
    - 사전 검토 결과
    - 출력 수락 여부와 그 근거
    - 도구가 보고한 프로세스 종료 코드와 PROGRAM_EXIT
  - P 출력 값: 출력이 수락된 경우 D9의 키 이름으로 다음을 옮긴다.
    - STAGE_로 시작하는 12개 키, FIRST_FAILED_STAGE, FIRST_FAIL_CODE
    - AXIS_EXEC, AXIS_TASK, AXIS_STORE, AXIS_LOOKUP, AXIS_STATE, AXIS_ARTIFACT
    - SNAPSHOT_ID, SNAPSHOT_FILE_SHA256, STATE_SHA256, CONTRACT_ENTRIES, CONTRACT_MATCH, STATE_SHA256_RECOMPUTED_MATCH, E2_STATUS, E4_STATUS
    - EVIDENCE_BYTES, EVIDENCE_SHA256, EVIDENCE_VALID, EVIDENCE_STATUS, EVIDENCE_EXIT_CODE
    - STORE_STATUS, STORE_EXIT_CODE, STORE_FINAL_FILE_CREATED, STORE_WARNING_COUNT, STORE_ERROR_CODE, RECORD_ID, RECORD_FILE_SHA256
    - LOOKUP_STATUS, LOOKUP_EXIT_CODE, LOOKUP_WARNING_COUNT, LOOKUP_ERROR_CODE, LOOKUP_EVIDENCE_CANONICAL_SHA256, MATCH_RECORD_ID, MATCH_EVIDENCE_SHA256, MATCH_FILE_SHA256
    - E6_CHANGED_COUNT, E6_IGNORED_COUNT, E6_IGNORED_LISTED, E6_IGNORED_OMITTED, 출력된 E6_IGNORED_ITEM 항목
    - B0와 B1의 영역별 FILES, DIRS, BYTES, FILES_SHA256, DIRS_SHA256 값
    - DIFF_로 시작하는 영역별 개수 10개, DIFF_TOTAL, DIFF_UNEXPECTED, REQUIRED_MISSING, DIFF_LISTED, DIFF_OMITTED, 출력된 DIFF_ITEM 항목
  - 값의 구분:
    - 원본 API 값과 파생 검사값을 D9의 구분대로 표시한다.
    - NONE과 NULL을 구분해 그대로 적는다.
    - REQUIRED_MISSING은 실제 삭제 건수와 구분해 적는다.
    - DIFF_UNEXPECTED=0과 저장 결과 불명이 함께 있으면 둘을 모두 적는다.
    - DIFF_OMITTED나 E6_IGNORED_OMITTED가 1 이상이면, 생략된 사실과 건수만 기록한다. 생략 항목을 확인했다고 주장하거나 추정해 복원하지 않는다.
  - 출력이 수락되지 않은 경우:
    - 관측된 부분 값은 "참고, 판정 근거 아님"으로 표시해 적거나 적지 않는다.
    - 그 값을 판정 근거로 쓰지 않는다.
    - EXECUTION_CLOSEOUT의 관측이 있으면 따로 적는다.
  - 판정:
    - 통합 사례 최종 판정과 그 근거를 D10의 판정 순서대로 적는다.
    - 확인된 위반과 UNKNOWN 항목이 함께 있으면 FAIL과 UNKNOWN 항목을 모두 적는다.
    - AXIS_TASK가 TIMEOUT이면 작업 완료 여부 불명을 따로 적는다.
    - AXIS_ARTIFACT=MISMATCH이면 D12의 사건 한정 처리 조건 충족 여부를 적는다.
    - 문서화 task의 완료 여부는 이 판정과 별개라고 적는다.
  - 한계: D8과 D12의 관측 한계를 적는다. 최소한 다음을 포함한다.
    - 최종 상태 비교의 한계(실행 중 생성 후 삭제는 부정할 수 없음)
    - TARGET_WORKTREE 밖과 .git 관리 정보는 미관측
    - 실제 자식 argv는 직접 관측하지 않음
    - 직접 자식만 kill됨
    - 중복 실행 통제가 없음
    - 경쟁 상태에 대한 보안 격리가 아님
    - D14의 Guard 확인 범위와 미확인 범위
  - 증거 등급:
    - 모든 값에 GIT_VERIFIABLE, CLAUDE_REPORTED, INDEPENDENT 중 하나를 붙인다.
    - P 출력과 판정은 CLAUDE_REPORTED다.
    - 직접 관측, 보고, 추론을 구분한다. 추론은 추론으로 표시한다.
    - 기록되지 않은 값을 추정하거나 다시 만들지 않는다.
  - 이벤트: Guard·권한 관측, 누적 Guard DENY 수와 DEVIATIONS 수, 이 task에서 새로 생긴 항목.
  - 비식별화: D13을 따른다.
  - 유지 사항: AUTO-04의 통합 시험 FAIL, Linux experimental의 기존 wrapper 실패 2건, Git garbage 경고는 해결된 것으로 표시하지 않는다.

- TEST_GATES:
  - 코드 변경이 없으므로 로컬 pytest, ruff, mypy는 NOT_REQUIRED다.
  - 로컬 검증은 D15의 문서 검사로 제한한다.
  - 계약 파일 두 개와 사례 기록 파일의 바이트 형식: UTF-8, BOM 없음, CR 0, U+00A0 0, 탭 0, 줄 끝 공백 0, 끝 LF 1개.
  - 해시 대조:
    - 계약 파일 두 개는 작업 파일, staged, commit blob의 내용 SHA-256이 승인값과 같아야 한다.
    - 사례 기록 파일은 작성 직후의 SHA-256, 바이트 수, 줄 수가 승인값과 같아야 한다. 이후 작업 파일, staged, commit blob의 내용 SHA-256도 승인값과 같아야 한다.
  - 사례 기록 내용:
    - D17의 포함 항목이 있는지 확인한다. P가 실행된 경우 REQUIRED_MISSING도 포함한다.
    - D13의 비식별화를 확인한다.
    - 기록한 값을 P 출력과 Git 값에 대조한다.
  - 변경 집합과 보호 diff를 확인하고, git diff --check를 실행한다.

- ACCEPTANCE_CRITERIA:
  - AC1: C1, Ce, I의 parent와 변경 집합이 COMMIT_PLAN과 같다. Ce의 parent는 C1, I의 parent는 Ce다.
  - AC2: base..I는 다음 3개 파일뿐이다. 보호 diff는 0이고, 두 계약 파일의 해시는 변하지 않았다.
    - docs/tasks/AUTO-06/WORK_ORDER.md
    - docs/tasks/AUTO-06/ERRATA-001.md
    - docs/research-intake/2026-11-14/AUTO-06_OFFLINE_INTEGRATION_CASE.md
  - AC3: 다음 중 하나가 기록되었다.
    - D3의 환경 확인값, pip check 통과, 환경 준비 직후의 ignored 목록
    - 환경 준비가 중단된 경우 그 관측값, 실패 지점, 이후 단계의 NOT_RUN 사유
  - AC4: 다음 중 하나가 기록되었다.
    - P가 실행된 경우: P 출력의 수락 여부와 그 근거. 출력이 수락되었으면 STAGE_S0 값(PASS, FAIL, UNKNOWN)과 실행 진입 HEAD 확인 결과. 미수락이면 S0 결과는 미확인으로 기록한다.
    - P가 실행되지 않은 경우: NOT_RUN과 그 사유.
  - AC5: 다음 중 하나가 기록되었다.
    - 출력이 수락된 경우: 실행·작업·저장·조회·상태·산출물 축과 통합 사례 최종 판정을 D10에 따라 각각 기록한다. 확인된 위반과 UNKNOWN이 함께 있으면 둘 다 기록한다.
    - 출력이 수락되지 않은 경우: 최종 판정 UNKNOWN, 그리고 축 값 미확인 사유.
  - AC6: 다음 중 하나가 기록되었다.
    - B0와 B1의 영역별 수와 집계 해시, 실제 차이 건수, DIFF_UNEXPECTED, REQUIRED_MISSING
    - NOT_RUN 또는 UNKNOWN과 그 사유
  - AC7: PRECOMMIT_AUDIT 시점에 미커밋 tracked·untracked 변경이 사례 기록 파일 하나뿐이다.
  - AC8: 사례 기록이 D17과 D13을 만족한다.
  - AC9: 사례 기록의 W와 승인 S, staged blob, commit blob의 내용 SHA-256이 일치한다. commit 후 작업 트리가 clean이다.
  - AC10: 정확한 PR head의 Windows CI가 SUCCESS이고 D16이 기록되었다. PR_CI 이전 단계에서는 NOT_YET_APPLICABLE이다.
  - 완료 판정:
    - 문서화 task의 COMPLETE는 다음을 모두 요구한다.
      - AC1–AC10 충족
      - 계약 위반, 보호 파일 변경, 설명되지 않은 상태 변경이 없음(D12의 사건 한정 처리 포함)
    - 통합 사례 SUCCESS는 완료 조건이 아니다. 완료는 통합 사례 최종 판정을 바꾸지 않는다.
    - 사례가 FAIL이나 UNKNOWN이면, D11과 D12의 별도 승인과 조건에 따라서만 문서화한다.
    - 아직 실행하지 않은 gate의 조건은 충족으로 표시하지 않는다. NOT_YET_APPLICABLE 또는 NOT_RUN으로 표시한다.

- STOP_CONDITIONS:
  - 기준선 불일치
    - 기준선, HEAD, tree, 계약 해시, 파일 범위가 기대와 다르거나 예상 밖 untracked가 있다.
    - 생성 전에 대상 branch나 worktree가 이미 있거나, 생성 후 상태가 기대와 다르다.
    - fetch 후 원격 추적 main이나 그 tree가 기대값과 다르거나, SOURCE_WORKTREE HEAD tree가 CANONICAL_BASE_TREE와 다르다.
    - PATH_VARIABLES 값이 승인문에 없거나 기대 상태와 다르다.
  - 환경
    - 환경 확인 항목을 충족하지 못했거나 pip check가 실패했다.
    - ENVIRONMENT_PREPARATION_ONLY 완료 시점의 확인에서, .venv 밖에 __pycache__가 있거나 D3 밖의 ignored 항목이 있다. 실행 뒤의 산출물은 이 조건이 아니라 D8로 판정한다.
  - P 실행
    - 실행 진입 HEAD가 Ce가 아니다.
    - 실행할 P 원문의 sha256이 PROGRAM_REVIEW에서 수락된 값과 다르다.
    - P 종료 코드가 0이 아니거나 P 출력이 미수락이다.
  - ERRATA-001과 Ce 커밋
    - ERRATA-001의 작업 파일, staged, commit blob 해시가 승인값과 다르다.
    - Ce의 변경이 ERRATA-001.md 하나가 아니거나, Ce의 parent가 C1이 아니다.
  - 사례 기록과 I 커밋
    - 사례 기록을 CASE_RECORD_WRITE 승인 없이 작성했거나 ALLOWED_ACTIONS.CASE_RECORD_WRITE의 작성 시점 조건 전에 작성했다.
    - 사례 기록의 작성 후 SHA-256, 바이트 수, 줄 수가 승인값과 다르다.
    - 작성 후 승인 없이 사례 기록이 변경되었다.
    - I의 parent가 Ce가 아니거나, I의 변경이 사례 기록 파일 하나가 아니다.
    - 사례 기록이나 보고에서 통합 사례 최종 판정이 P 출력과 D10이 정하는 값과 다르게 표기되었다.
  - 공통
    - 보호 파일이 변경되었거나, 기존 코드·테스트·설정이 변경되었다.
    - Guard DENY, 권한 거절이나 무응답, 예상 밖 ASK, 오류나 결과 불명이 발생했다.
    - 계약에 모순이 있거나 상위 규칙과 충돌한다.
  - 위 조건에 따른 중단은 보고 후 멈춤을 뜻한다. D11과 D12의 별도 승인에 따른 EXECUTION_CLOSEOUT과 문서화 전이를 막지 않는다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1–3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)과 README는 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
- 코드, 테스트, README, Guard, settings, CI, .gitignore 변경을 추가하지 않는다.
- 다음 권한은 추가하지 않는다.
  - P와 작업 API(run_action, store_evidence, load_evidence)의 새 실행·재실행 권한
  - workstate snapshot·verify의 추가 실행 권한
  - evidence·snapshot·runlog 원본의 재조회 권한
  - 산출물과 캐시의 정리 권한
- 사례 기록 파일의 최초 생성 외에는 파일 작성 권한을 추가하지 않는다.
