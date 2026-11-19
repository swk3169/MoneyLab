# Work Order: ECON-SCREEN-V06-01 — 경제성 선별 사전등록의 최초 생성과 고정 커밋

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/ECON-SCREEN-V06-01/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: ECON-SCREEN-V06-01
TASK_ID: ECON-SCREEN-V06-01
TITLE: ECON-SCREEN-V06-01 사전등록 문서의 최초 생성과 고정 커밋
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: b13b3a24fce7c5ad634208bd7ed6660cdce2882d (origin/main, PR #55 merge)
CANONICAL_BASE_TREE: c960df50eef37419968ca34d690c3a0413c89cf8
BASE_REMOTE_REF: refs/remotes/origin/main (로컬 값. fetch하지 않는다)
ENTRY_HEAD: c3d98eda9b969875f8eb7b05eb24ce3301e2dbd4 (branch codex/futval-v8-01-run)
ENTRY_TREE: fb4e51c59c5a633809a806c94a2c2727c99d20ef
TARGET_BRANCH: codex/econ-screen-v06-01
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck (재사용. 새 branch를 CANONICAL_BASE_SHA에서 만들어 전환한다)
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE (원격 게시·PR_CI·MERGE gate 없음)
REQUIRED_CI_CHECKS: NOT_APPLICABLE
BUNDLE_ELIGIBLE: NO
PREREGISTRATION_PATH: docs/research_econ_screen_v06_01_preregistration.md
PREREGISTRATION_SHA256: 2ff766fa8e60adbc107b1ffe9ae4df30c455b616cd5345154704ff928b74705d
PREREGISTRATION_BYTES: 13396
PREREGISTRATION_LF: 170
RELATED_TASKS: v0.6 사전등록 초안(DRAFT, 변경 없음), FUTVAL-V8-01 계열, RUNWATCH-01, DATAQ-V06-01 후보(미발행). 이 Work Order는 그 판정·보류·사건 기록을 바꾸지 않는다.

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> PREREGISTRATION_FREEZE -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 각 gate는 사용자의 명시적 GATE_AUTHORIZATION 1건으로만 시작하고, 보고 후 멈춘다. 이전 gate의 승인이나 PASS는 다음 gate의 승인이 아니다.
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: ECON-SCREEN-V06-01 WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - PREREGISTRATION_FREEZE: GATE_AUTHORIZATION: ECON-SCREEN-V06-01 PREREGISTRATION_FREEZE WO@<C1 SHA> PREREG_SHA256=<64 hex> PREREG_BYTES=<n> PREREG_LF=<n>
  - CLOSEOUT_REPORT: GATE_AUTHORIZATION: ECON-SCREEN-V06-01 CLOSEOUT_REPORT WO@<C1 SHA>
- PREREGISTRATION_FREEZE 승인의 세 값은 Metadata의 PREREGISTRATION_SHA256·BYTES·LF와 같아야 한다. 다르면 STOP한다.
- BUNDLE_AUTHORIZATION과 일반 DELEGATE는 이 Work Order의 어떤 gate도 대신하지 않는다.
- 상태 변경은 각각 별도 도구 호출로 실행하고 결과를 확인한 뒤 다음으로 간다. Git 조회, 원문 재현, 해시 확인, 보존 비교는 목적별 작은 호출로 나눈다. 검사 명령 뒤에 파이프·자르기·리디렉션·다른 명령을 붙이지 않는다.
- 오류·차단·불일치가 생기면 그 자리에서 STOP하고, 다른 방식으로 재시도하거나 복구하지 않는다.
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)이 우선한다. 복제하지 않고 바꾸지 않는다. 충돌하면 STOP한다. 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: 사용자가 수락한 ECON-SCREEN-V06-01 사전등록 문서를 승인 바이트 그대로 최초 생성하고 고정 커밋으로 확정한다. 사전등록의 통계·품질·비용·구간·seed·반복 수는 바꾸지 않는다. 구현, 설계 문서 변경, 데이터 수집, 자원 측정, 선별 실행은 하지 않는다.

## BACKGROUND

BACKGROUND:
- 이 study는 v0.6 사전등록 초안과 별개의 탐색적 경제성 선별이다. 증거 등급은 L1_SCREENING / NOT_CONFIRMATORY다.
- 기존 "BT-5 이전 real 금지"(bar_export, bars_io, portfolio, vault, run)는 이 고정으로 해제되지 않는다. backtest_design.md의 BT-5S 추가와 study 전용 real 경로 구현은 후속 구현 계약에서 다룬다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 출력(PRESERVATION_CHECK, 상태 변경 전 첫 호출)
  - 진입 확인: HEAD = ENTRY_HEAD, tree = ENTRY_TREE, branch codex/futval-v8-01-run, staged·unstaged·untracked 없음, refs/remotes/origin/main = CANONICAL_BASE_SHA와 그 tree = CANONICAL_BASE_TREE, TARGET_BRANCH·docs/tasks/ECON-SCREEN-V06-01·PREREGISTRATION_PATH 부재, data/ 아래 파일 이름·SHA-256 목록
  - git -C C:/MoneyLab-futval-v8-01-precheck switch -c codex/econ-screen-v06-01 b13b3a24fce7c5ad634208bd7ed6660cdce2882d 1회
  - 전환 확인: HEAD = CANONICAL_BASE_SHA, tree = CANONICAL_BASE_TREE, clean, ignored 산출물 유지
  - docs/tasks/ECON-SCREEN-V06-01/WORK_ORDER.md를 승인 바이트로 Write 1회
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/ECON-SCREEN-V06-01/WORK_ORDER.md 1회
  - C1 커밋 1회
  - 종료 시 PRESERVATION_CHECK 비교
- PREREGISTRATION_FREEZE
  - 진입 확인: HEAD = C1, clean, C1의 Work Order blob 내용 sha256이 승인값과 같음, PREREGISTRATION_PATH 부재
  - 사전등록 원문을 수락된 최종 계산 출력(세션 도구 결과)에서 메모리로 재현하고 PREREGISTRATION_SHA256·BYTES·LF와 대조한다. 문안은 바꾸지 않는다
  - PREREGISTRATION_PATH를 승인 바이트로 Write 1회
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/research_econ_screen_v06_01_preregistration.md 1회
  - C2 커밋 1회
  - 종료 시 PRESERVATION_CHECK 비교
- CLOSEOUT_REPORT: 읽기 전용 보존 확인과 보고
- 모든 gate: 읽기 전용 git 조회와 파일 해시·형식 검사

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위, ALLOWED_FILES·CONTRACT_FILE_EXCEPTION 밖 tracked 변경, PROTECTED_FILES 변경
- 사전등록·Work Order·ERRATA 수정, 사전등록 문안의 재작성·치환
- 코드·시험·설계 문서 변경, real 금지 해제, 데이터 수집·열람, 자원 측정, 선별 실행
- 설치, 네트워크, fetch, 원격 게시, PR, merge
- git add의 전체 지정, amend, no-verify, reset, restore, stash, rebase, cherry-pick, 지정한 1회 외의 checkout·switch
- 셸 출력 폐기·리디렉션·출력 분기, 임시 스크립트 파일, guard·hook·settings·권한 규칙 변경
- 기존 산출물·다른 branch·worktree·untracked·ignored 항목의 변경·정리

## ALLOWED_FILES

ALLOWED_FILES:
- A docs/research_econ_screen_v06_01_preregistration.md (PREREGISTRATION_FREEZE 전용, 승인 바이트로 최초 1회)

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/ECON-SCREEN-V06-01/WORK_ORDER.md (WORKSPACE_SETUP 전용, 승인 바이트로 최초 1회). ALLOWED_FILES에 속하지 않는다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/ECON-SCREEN-V06-01/** (CONTRACT_FILE_EXCEPTION의 최초 생성 1회 제외. 생성 뒤 수정 포함)
- docs/research_*_preregistration*.md (ALLOWED_FILES의 최초 생성 1회 제외. 생성 뒤 수정 포함)
- 그 밖의 모든 저장소 파일. src/**, tests/**, configs/**, 다른 docs/**, .claude/**, .github/**, CLAUDE.md, .gitignore, .gitattributes, pyproject.toml, requirements*.txt를 포함한다
- data/** 기존 산출물

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (보호 경로의 최초 생성은 위 예외 문구로만 허용한다)

## COMMIT_PLAN

COMMIT_PLAN:
- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/ECON-SCREEN-V06-01/WORK_ORDER.md 하나, 메시지 docs(task): add ECON-SCREEN-V06-01 work order
- C2: parent = C1, 변경 = A docs/research_econ_screen_v06_01_preregistration.md 하나, 메시지 docs(research): add ECON-SCREEN-V06-01 preregistration
- 커밋 본문과 trailer는 넣지 않는다. CANONICAL_BASE_SHA..C2 변경 경로는 위 두 파일뿐이다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- F1 작성 대조: 작업 파일의 sha256·bytes·LF가 승인값과 같고, CR 0, BOM 없음, 탭 0, 줄 끝 공백 0, 끝 LF 1개다. 불일치면 STOP하며 파일을 고치거나 지우거나 다시 쓰지 않는다.
- F2 staged 검사: staged 경로 집합이 해당 파일 하나이고, staged blob 내용 sha256이 승인값이며, git diff --cached --check가 exit 0이다.
- F3 커밋 후 대조: parent, 변경 집합, 커밋된 blob 내용 sha256, worktree clean을 확인한다.
- F4 사전등록 효력은 C2 커밋 완료로 생긴다. 이 고정은 구현·수집·실행·결과 열람·공개 권한을 만들지 않으며, 기존 real 금지를 해제하지 않는다.

## PRESERVATION_CHECK

PRESERVATION_CHECK:
- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): git -C C:/MoneyLab-gov-automation-03 for-each-ref --sort=refname --format="%(refname) %(objectname)", worktree list --porcelain, rev-parse HEAD HEAD^{tree}, status --porcelain=v1 --untracked-files=all --ignored=matching의 원문 전체를 도구 출력으로 남긴다.
- 분류
  - TASK: refs/heads/codex/econ-screen-v06-01. 기대 변화는 생성 -> C1 -> C2뿐이다.
  - OBSERVED: refs/codex/turn-diffs/checkpoints/**. 변화는 기록만 하며 STOP 사유가 아니다.
  - PRESERVE: 그 밖의 모든 ref. refs/heads/codex/futval-v8-01-run = c3d98eda9b969875f8eb7b05eb24ce3301e2dbd4, refs/remotes/origin/codex/futval-v8-01-run, refs/heads/codex/runwatch-01 = a3197059f0c1bc41e41ba0d2c7700836cb795645를 포함한다. 하나라도 변하면 STOP한다.
- worktree: TARGET_WORKTREE 항목을 통째로 제외하고 항목 단위로 비교한다. TARGET_WORKTREE의 기대 변화는 branch가 codex/futval-v8-01-run에서 codex/econ-screen-v06-01로, HEAD가 ENTRY_HEAD에서 CANONICAL_BASE_SHA, C1, C2로 바뀌는 것뿐이다.
- host: GIT_HOST_WORKTREE의 HEAD·tree·status가 F0와 같아야 한다.
- checkout 변화: 전환으로 ENTRY_HEAD에만 있는 16개 tracked 경로가 작업 트리에서 사라진다. 대상은 docs/research_futval_v8_01_preregistration.md, docs/tasks/FUTVAL-V8-01/WORK_ORDER.md, docs/tasks/FUTVAL-V8-01-IMPL/WORK_ORDER.md, docs/tasks/FUTVAL-V8-01-PRECHECK/WORK_ORDER.md, docs/tasks/FUTVAL-V8-01-PRECHECK/ERRATA-001.md, docs/tasks/FUTVAL-V8-01-SMOKE-PERF/WORK_ORDER.md, docs/tasks/FUTVAL-V8-01-RUN/WORK_ORDER.md, docs/tasks/RUNWATCH-01/WORK_ORDER.md, docs/tasks/RUNWATCH-01/ERRATA-001.md, src/moneylab/research/v06/futval_v8_01.py, src/moneylab/runwatch/__init__.py, src/moneylab/runwatch/__main__.py, src/moneylab/runwatch/watch.py, src/moneylab/runwatch/winjob.py, tests/test_futval_v8_01.py, tests/test_runwatch.py다. 이것은 작업 파일 불변이 아니다. 그 파일들은 PRESERVE ref의 커밋과 원격 branch에 그대로 있다. 원래 branch로 되돌리지 않는다.
- 산출물: data/ 아래 ignored 산출물의 이름·SHA-256이 WORKSPACE_SETUP 진입 목록과 같아야 한다. 새 ignored 항목은 없어야 한다. 확인은 이름·크기·SHA-256만 하며 내용은 열지 않는다.
- 비교 시점: WORKSPACE_SETUP 종료, PREREGISTRATION_FREEZE 종료, CLOSEOUT_REPORT.

## EXPECTED_ASK

EXPECTED_ASK(실제 발생은 보장하지 않음):
- WORKSPACE_SETUP: Work Order 최초 생성 확인 최대 1회, 커밋 확인 1회
- PREREGISTRATION_FREEZE: 사전등록 최초 생성 확인 최대 1회, 커밋 확인 1회
- 그 밖의 ASK·거절·무응답·DENY는 STOP

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT·SHA256, HEAD·parent·tree, 변경 집합, PROTECTED diff, status(ignored 포함), F1–F4 결과, PRESERVATION_CHECK 분류별 결과와 checkout 변화
- 증거 등급(GIT_VERIFIABLE, CLAUDE_REPORTED, INDEPENDENT) 구분
- GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES, <GATE>_PASS, READY_FOR_<NEXT>

## STOP_CONDITIONS

STOP_CONDITIONS:
- ENTRY_HEAD·ENTRY_TREE·branch 불일치, origin/main ≠ CANONICAL_BASE_SHA, CANONICAL_BASE_TREE 불일치, 진입 시 clean 아님
- TARGET_BRANCH·docs/tasks/ECON-SCREEN-V06-01·PREREGISTRATION_PATH가 미리 있음
- Work Order 또는 사전등록의 sha256·bytes·LF·형식 불일치, 사전등록 원문 재현 실패
- 전환 뒤 기대 밖 tracked·ignored 변화, ALLOWED_FILES·CONTRACT_FILE_EXCEPTION 밖 변경, PROTECTED 변경
- PRESERVE ref 변화, worktree 항목 불일치, host 변화, data 산출물 변화
- guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- 상위 규칙과 충돌
