# Work Order·ERRATA 템플릿 (계약 v1.1)

사용법: 아래 "Work Order 템플릿" 블록을 `docs/tasks/<TASK_ID>/WORK_ORDER.md`로 복사해 `<...>`를 채운다. 계약이 바뀌면
"ERRATA 템플릿" 블록을 `docs/tasks/<TASK_ID>/ERRATA-<NNN>.md`로 복사한다. 형식은 Markdown + `KEY: value` 줄이다(YAML front matter
없음). 목록 값은 `KEY:` 다음 줄부터 `- ` 항목으로 쓴다. 규칙은 `README.md`와 `CLAUDE.md`의 "Work Order" 절을 따른다.

---

## Work Order 템플릿

````markdown
# Work Order: <TASK_ID> — <TITLE>

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/<TASK_ID>/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: <TASK_ID>
TASK_ID: <로드맵·기능 ID, 예: BT-3d>
TITLE: <한 줄 제목>
VERSION: <예: 1.0>
STATUS: ISSUED
CANONICAL_BASE_SHA: <40자리 hex, 원격 main에서 확인한 값>
CANONICAL_BASE_TREE: <40자리 hex>
TARGET_BRANCH: <예: feature/backtest-bt3d-vault>
TARGET_WORKTREE: <예: C:/MoneyLab-bt3d-vault>
WORKSPACE_SETUP: <REQUIRED | NOT_REQUIRED (저장소를 바꾸는 gate가 없을 때만)>
INITIAL_GATE: <보통 WORKSPACE_SETUP>
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: <TASK_ID> <GATE> WO@<commit>`)
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping except WORKSPACE_SETUP: NOT_REQUIRED tasks

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다.

## GOAL

GOAL: <무엇을 왜 하는가, 한두 문장>

## BACKGROUND

BACKGROUND: <근거 문서, 이전 결과, 관련 커밋>

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: <예: branch·worktree 생성, WORK_ORDER.md 최초 생성과 C1 커밋>
- IMPLEMENTATION: <예: ALLOWED_FILES 생성·수정, TEST_GATES 실행>
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, 커밋 하나
- CLEAN_COMMIT_E2E: <E2E_GATES 실행, ignored 출력만>
- PUSH: TARGET_BRANCH 하나만 `git push -u origin <TARGET_BRANCH>`
- PR_CI: compare URL·PR 본문 제공만
- MERGE: 사용자 결정(GitHub UI, MERGE_METHOD)
- POST_MERGE_AUDIT: main ref만 fetch, 구조 감사
- COMPLETE: 최종 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
- hooks·settings·.claude 변경 또는 guard 우회
- 다른 branch·worktree·untracked·ignored·reference 산출물 정리
- <task별 추가 금지 항목>

## ALLOWED_FILES

ALLOWED_FILES:
- <A|M> <경로>
- <A|M> <경로>

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/<TASK_ID>/**
- .claude/**
- <task별 보호 경로>

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가)

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- <확정된 결정 D1...Dn: 정의, 식, 스키마·버전 영향, 하위 호환, 실패 처리>

## TEST_GATES

TEST_GATES:
- <예: 새 테스트 파일, targeted 테스트 목록>
- 전체 pytest, failed 0 / errors 0
- `git diff --check` 깨끗함, 변경 파일 집합 = ALLOWED_FILES

## E2E_GATES

E2E_GATES:
- <예: clean 커밋에서 baseline result.json 바이트 일치, verify·report 통과>
- <해당 없으면 NOT_REQUIRED와 대체 확인 방법>

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: <base·C1·구현 커밋 SHA·tree, 파일 sha256, 커밋 파일 집합, merge parent·tree>
- CLAUDE_REPORTED: <pytest·E2E 결과>
- INDEPENDENT: <PR CI, GitHub 화면(사용자 확인)>

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, Work Order sha256 불일치
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기와 base 상태 불일치
- guard deny, 권한 창 거절
- 테스트 실패·에러, hard gate 불일치
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일
- <task별 추가 조건>
````

---

## ERRATA 템플릿

초안(`STATUS: PROPOSED`)은 채팅에서만 다룬다. 파일은 사용자가 수락한 뒤 `STATUS: ACCEPTED`로 한 번만 쓰고 Ce 커밋으로 고정한다.

````markdown
# ERRATA: <TASK_ID> ERRATA-<NNN>

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: <TASK_ID>-ERRATA-<NNN>
TASK_ID: <TASK_ID>
TARGET_WORK_ORDER: docs/tasks/<TASK_ID>/WORK_ORDER.md @ <C1 커밋 SHA> (sha256 <Work Order sha256>)
SUPERSEDES_ERRATA: <NONE | 이전 ERRATA_ID>
STATUS: ACCEPTED
ACCEPTED_BY: <사용자, 날짜>

## CHANGED_FIELDS

CHANGED_FIELDS:
- <필드 이름, 예: DESIGN_CONTRACT.D4, ALLOWED_FILES, TEST_GATES>

## RATIONALE

RATIONALE: <왜 바꾸는가: 발견된 모순, 새 사실, 결정>

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- <필드>: <바뀐 뒤의 전체 값. 일부가 아니라 그 필드의 새 내용 전체>

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
````
