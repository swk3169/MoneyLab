# Work Order: FUTVAL-V8-01 — V0 futility 검정 iid 유한 표본 기각률 검증의 사전등록 고정

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/FUTVAL-V8-01/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: FUTVAL-V8-01
TASK_ID: FUTVAL-V8-01
TITLE: FUTVAL-V8-01 사전등록 문서의 최초 생성과 고정 커밋
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: b13b3a24fce7c5ad634208bd7ed6660cdce2882d
CANONICAL_BASE_TREE: c960df50eef37419968ca34d690c3a0413c89cf8
TARGET_BRANCH: codex/futval-v8-01
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE (이 Work Order에는 PUSH·PR_CI·MERGE gate가 없다)
REQUIRED_CI_CHECKS: NOT_APPLICABLE (원격 단계 없음)
BUNDLE_ELIGIBLE: NO
BUNDLE_MAX_RANGE: NONE
PREREGISTRATION_PATH: docs/research_futval_v8_01_preregistration.md
PREREGISTRATION_SHA256: d77549ed4cc732f0b2fb0151fcf17913d319ce8e0de929827fc3a8c9c7ea9b91
PREREGISTRATION_BYTES: 17124
PREREGISTRATION_LF: 171
SOURCE_BLOB_PROCEDURES: src/moneylab/research/v06/procedures.py = bf6dfddea822f3af0d6e50274c8b3b5b0c767daf
SOURCE_BLOB_STATS: src/moneylab/research/stats.py = 01b6472cadb2ce2437a613b09d419a999398c685

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> PREREGISTRATION_FREEZE -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 각 gate는 사용자의 명시적 Gate Authorization 1건으로만 시작하고, 보고 후 멈춘다. 이전 gate의 승인이나 PASS는 다음 gate의 승인이 아니다.
- 승인 형식
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: FUTVAL-V8-01 WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - PREREGISTRATION_FREEZE: GATE_AUTHORIZATION: FUTVAL-V8-01 PREREGISTRATION_FREEZE WO@<C1 SHA> PREREG_SHA256=<64 hex> PREREG_BYTES=<n> PREREG_LF=<n>
  - CLOSEOUT_REPORT: GATE_AUTHORIZATION: FUTVAL-V8-01 CLOSEOUT_REPORT WO@<C1 SHA>
- PREREGISTRATION_FREEZE 승인의 세 값은 Metadata의 PREREGISTRATION_SHA256·BYTES·LF와 같아야 한다. 다르면 STOP한다.
- 일반 DELEGATE(v1.4), BUNDLE_AUTHORIZATION(v1.3)은 이 Work Order의 어떤 gate도 대신하지 않는다.
- 상태 변경 명령은 각각 별도 도구 호출로 실행하고 결과를 확인한 뒤 다음 명령을 실행한다. 선행 결과에 의존하는 조회는 병렬로 보내지 않는다. STOP 뒤에는 후속 명령을 실행하지 않는다.
- amend는 금지한다. 커밋 뒤 수정이 필요하면 STOP하고 사용자 결정을 받는다.
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다. 구현과 그 밖의 단계는 별도 Work Order로 한다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다. 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: FUTVAL-V8-01 사전등록 문서를 사용자가 승인한 바이트 그대로 저장소에 최초 생성하고 고정 커밋으로 확정한다. 연구 구현·실행은 하지 않는다.

## BACKGROUND

BACKGROUND:
- 사전등록 내용은 BT4-FUTILITY-01 DIAG와 BT4-FUTILITY-02 사후 진단의 결과를 본 뒤 선정한 V-8 질문의 독립 검증 설계다. 기존 결과 수치와 판정 라벨은 문서에 없다.
- 선례: BT4-FUTILITY-01 G2a PREREGISTRATION(커밋 321b54b1aac5e090d8efec93322dbec1901c2b6f).
- 기존 사전등록, 결과 제한(D4, V-1 분포 미승인), PR #40의 DO_NOT_MERGE, 기존 미완료 의무는 바꾸지 않는다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - git -C C:/MoneyLab-gov-automation-03 fetch origin refs/heads/main:refs/remotes/origin/main 1회
  - git -C C:/MoneyLab-gov-automation-03 worktree add -b codex/futval-v8-01 C:/MoneyLab-futval-v8-01 b13b3a24fce7c5ad634208bd7ed6660cdce2882d 1회
  - 승인된 바이트로 docs/tasks/FUTVAL-V8-01/WORK_ORDER.md를 Write 1회로 생성
  - git -C C:/MoneyLab-futval-v8-01 add -- docs/tasks/FUTVAL-V8-01/WORK_ORDER.md
  - C1 커밋 1회
- PREREGISTRATION_FREEZE
  - 승인된 바이트로 docs/research_futval_v8_01_preregistration.md를 Write 1회로 생성
  - git -C C:/MoneyLab-futval-v8-01 add -- docs/research_futval_v8_01_preregistration.md
  - C2 커밋 1회
- CLOSEOUT_REPORT: 읽기 전용 보존 확인과 보고
- 모든 gate: 읽기 전용 git 조회와 파일 해시·형식 검사

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES와 CONTRACT_FILE_EXCEPTION 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA·사전등록 문서 수정
- git add ., git add -A, --no-verify, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
- push, PR 생성·수정, merge, CI 실행
- 연구 코드 구현, seed 고유성 검사, smoke, 성능 측정, 본 실행, 결과 열람, 설치, venv 생성, 테스트 실행
- 저장소 밖 후보 파일 생성, 임시 스크립트 파일 작성, 출력 폐기·리디렉션·tee
- hooks·settings·.claude·.github 변경 또는 guard 우회
- 다른 branch·worktree·untracked·ignored·기존 산출물 정리
- 기존 비공개 결과 수치나 V-1 분포의 열람·기록

## ALLOWED_FILES

ALLOWED_FILES:
- A docs/research_futval_v8_01_preregistration.md (PREREGISTRATION_FREEZE 전용)

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/FUTVAL-V8-01/WORK_ORDER.md는 WORKSPACE_SETUP에서 승인된 바이트로 최초 1회만 생성한다. ALLOWED_FILES에 속하지 않는다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/FUTVAL-V8-01/** (CONTRACT_FILE_EXCEPTION의 최초 생성 제외)
- ALLOWED_FILES와 CONTRACT_FILE_EXCEPTION 밖의 모든 저장소 파일. src/**, tests/**, configs/**, 기존 docs/research_*, 다른 docs/tasks/<TASK>/**, .claude/**, .github/**, CLAUDE.md, docs/agent_workflow.md, .gitignore, .gitattributes, pyproject.toml, requirements*.txt를 포함한다

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## COMMIT_PLAN

COMMIT_PLAN:
- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/FUTVAL-V8-01/WORK_ORDER.md, 메시지 docs(task): add FUTVAL-V8-01 work order
- C2: parent = C1, 변경 = A docs/research_futval_v8_01_preregistration.md, 메시지 docs(research): add FUTVAL-V8-01 preregistration
- 커밋 본문과 trailer는 넣지 않는다.
- CANONICAL_BASE_SHA..C2의 변경 경로는 위 두 파일뿐이다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- F1 WORKSPACE_SETUP 사전 확인
  - GIT_HOST_WORKTREE의 git status가 clean이다.
  - fetch 1회 뒤 refs/remotes/origin/main = CANONICAL_BASE_SHA이고 그 tree = CANONICAL_BASE_TREE다. 다르면 STOP한다.
  - TARGET_WORKTREE 경로와 TARGET_BRANCH가 없다.
- F2 WORKSPACE_SETUP 작성·커밋
  - worktree 생성 뒤 HEAD = CANONICAL_BASE_SHA, clean이다.
  - Work Order 작업 파일의 sha256·bytes·LF가 승인값과 같고 CR 0, BOM 없음, 탭 0, 줄 끝 공백 0, 끝 LF 1개다.
  - staged blob(git cat-file blob :docs/tasks/FUTVAL-V8-01/WORK_ORDER.md)의 sha256이 승인값과 같고 staged 경로가 그 하나뿐이다.
  - 커밋 뒤 parent(C1) = CANONICAL_BASE_SHA, C1 변경 집합이 그 한 파일, 커밋된 blob sha256이 승인값과 같고, worktree가 clean(ignored 없음)이다.
- F3 PREREGISTRATION_FREEZE 사전 확인
  - HEAD = C1, clean, ignored 없음.
  - C1:docs/tasks/FUTVAL-V8-01/WORK_ORDER.md의 sha256이 C1 보고값과 같다.
  - PREREGISTRATION_PATH가 없다.
  - git rev-parse C1:src/moneylab/research/v06/procedures.py = SOURCE_BLOB_PROCEDURES, git rev-parse C1:src/moneylab/research/stats.py = SOURCE_BLOB_STATS.
- F4 PREREGISTRATION_FREEZE 작성 후 대조
  - 작업 파일의 sha256·bytes·LF = PREREGISTRATION_SHA256·BYTES·LF, CR 0, BOM 없음, 탭 0, 줄 끝 공백 0, 끝 LF 1개.
  - 불일치면 STOP한다. 파일을 고치거나 지우거나 다시 쓰지 않고 상태만 보고한다.
- F5 staged 검사
  - staged 경로 집합 = {PREREGISTRATION_PATH}.
  - git cat-file blob :docs/research_futval_v8_01_preregistration.md의 sha256 = PREREGISTRATION_SHA256.
  - git diff --cached --check가 exit 0이다.
- F6 커밋 후 대조
  - parent(C2) = C1, C2 변경 집합 = {A PREREGISTRATION_PATH}, CANONICAL_BASE_SHA..C2 변경 경로 = 두 계약 파일.
  - git cat-file blob C2:docs/research_futval_v8_01_preregistration.md의 sha256 = PREREGISTRATION_SHA256.
  - git rev-parse C2:src/moneylab/research/v06/procedures.py = SOURCE_BLOB_PROCEDURES, git rev-parse C2:src/moneylab/research/stats.py = SOURCE_BLOB_STATS.
  - worktree clean, ignored 없음.
- F7 보존(CLOSEOUT_REPORT)
  - GIT_HOST_WORKTREE의 HEAD·clean 상태가 WORKSPACE_SETUP 전과 같다.
  - 다른 worktree 목록과 branch head가 WORKSPACE_SETUP 전과 같다(새 worktree·branch 1개 추가만).
  - origin 원격 ref는 WORKSPACE_SETUP의 fetch 1회 외에 바뀌지 않았다(심볼릭 ref origin/HEAD의 파생값은 실제 ref 변경과 구분한다).

## TEST_GATES

TEST_GATES:
- 실행 테스트: NOT_REQUIRED. 이 Work Order는 문서 2개만 추가하며 테스트 실행을 승인하지 않는다.
- 대체 확인: F2·F4·F5·F6의 바이트·형식 검사, 그리고 두 문서에 사용자 홈 경로 문자열이 없음을 텍스트 검사로 확인한다.
- 한계: 저장소 hygiene 테스트와 CI 결과는 확인하지 않는다. 원격 단계는 별도 Work Order에서 다룬다.

## E2E_GATES

E2E_GATES:
- NOT_REQUIRED. 대체 확인은 F6과 F7이다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: CANONICAL_BASE·C1·C2의 SHA·tree·parent, 두 파일의 blob sha256, 커밋 파일 집합, 소스 두 파일의 blob ID
- CLAUDE_REPORTED: 작업 파일 sha256·bytes·LF·형식 검사 결과, fetch 결과, 보존 확인
- INDEPENDENT: 사용자의 확인

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree 상태, diff --cached --check
- 해당 gate의 F 항목별 결과와 증거 등급
- GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO
- PREREGISTRATION_FREEZE 보고: C2 SHA·tree, PREREGISTRATION_SHA256 일치, 소스 blob 불변. 사전등록 효력은 이 C2 커밋의 완료로 생긴다는 사실(문서 상태 줄)과, 구현·실행·공개 승인은 없다는 사실

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree·parent 불일치, origin/main ≠ CANONICAL_BASE_SHA, Work Order 또는 사전등록 sha256·bytes·LF 불일치, 형식 위반
- TARGET_WORKTREE·TARGET_BRANCH·PREREGISTRATION_PATH가 미리 있음
- ALLOWED_FILES·CONTRACT_FILE_EXCEPTION 밖 변경, PROTECTED_FILES 변경, 예상 밖 untracked·ignored 파일
- 소스 두 파일의 blob ID 불일치
- guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- 계약 모순, 상위 규칙과 충돌
