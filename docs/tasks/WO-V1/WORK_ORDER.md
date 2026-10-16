# Work Order: WO-V1 — Introduce MoneyLab Work Order v1

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/WO-V1/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: WO-V1
TASK_ID: WO-V1
TITLE: Introduce MoneyLab Work Order v1
VERSION: 1.1
STATUS: ISSUED
CANONICAL_BASE_SHA: af4035ce80be07b6b2e8fb14223cf4750e0c6f2a
CANONICAL_BASE_TREE: dbfe5764c6c75cef7e1f0a7ac0f7aeb9e37a72da
TARGET_BRANCH: docs/work-order-v1
TARGET_WORKTREE: C:/MoneyLab-work-order-v1
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (squash/rebase merge 금지: 계약 커밋이 구현보다 먼저인 이력을 보존)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

DESIGN_INVESTIGATION과 CONTRACT_REVIEW는 이 파일 발행 전에 대화로 완료했다(계약 v1.1).

## GATE_TRANSITION_RULES

- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: WO-V1 <GATE>`)
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping except WORKSPACE_SETUP: NOT_REQUIRED tasks
- Gate Authorization은 파일 수정이 아니다. 이전 gate의 승인이나 이 파일이 다음 gate의 승인을 대신하지 않는다.

## PRIORITY

1. safety / system / tool restrictions
2. repository absolute rules: CLAUDE.md, .claude guard/hook/settings, docs/agent_workflow.md
3. frozen / preregistered contracts
4. 이 Work Order와 ACCEPTED ERRATA
5. implementation judgment

충돌하면 상위 규칙을 따르고 STOP/REPORT 한다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 위 PRIORITY 1-3의 저장소 규칙을 참조한다(복제하지 않는다). 이 Work Order는 그 규칙을 바꾸지 않는다.

## GOAL

GOAL: MoneyLab Work Order v1.1(ChatGPT가 쓰고 Claude Code가 gate 단위로 실행하는 version-controlled 계약)을 저장소의 영구 규칙(CLAUDE.md)과 문서(docs/tasks/README.md, docs/tasks/TEMPLATE.md)로 도입한다.

## BACKGROUND

BACKGROUND: 기존 C:/MoneyLab의 `docs/chatgpt-task-handoff` 미커밋 초안(CLAUDE.md 작업 지시서 절, docs/tasks/README.md, docs/tasks/TEMPLATE.md)은 gate 모델, allowlist/protected, base SHA 강제, 보고 flag, ID/ERRATA, evidence가 없었다. 그 초안은 legacy reference로만 쓰고(문구 일부 재사용 가능) 그 worktree와 파일은 수정하지 않는다.

## ALLOWED_FILES

IMPLEMENTATION에서 변경할 수 있는 tracked 파일은 정확히 다음 3개다(allowlist).

ALLOWED_FILES:
- M CLAUDE.md
- A docs/tasks/README.md
- A docs/tasks/TEMPLATE.md

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/WO-V1/**
- .claude/**
- AGENTS.md
- .agents/**
- docs/backtest_bt2_review.md
- docs/backtest_bt2b_review.md
- docs/research_v06_preregistration_draft.md
- src/**
- tests/**
- configs/**

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 이 Work Order는 INVALID이고 IMPLEMENTATION에 진입할 수 없다)

## ALLOWED_ACTIONS (gate별 최대 범위)

- WORKSPACE_SETUP: base 확인, TARGET_BRANCH/TARGET_WORKTREE 생성, 이 파일 하나 최초 생성, `git add -- docs/tasks/WO-V1/WORK_ORDER.md`, C1 commit 하나, 감사
- IMPLEMENTATION: ALLOWED_FILES 3개만 생성/수정(CLAUDE.md 수정은 guard ask, [B] 승인), TEST_GATES 실행
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, commit 하나
- CLEAN_COMMIT_E2E: E2E_GATES 실행(ignored 출력만)
- PUSH: TARGET_BRANCH 하나만 `git push -u origin docs/work-order-v1`
- PR_CI: compare URL과 PR 본문 제공만(PR 생성과 CI 확인은 사용자)
- MERGE: 사용자 결정, GitHub UI, MERGE_METHOD
- POST_MERGE_AUDIT: main ref만 fetch, 구조 감사
- COMPLETE: 최종 보고. 증거 요약 보관은 별도 승인

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 현재 승인된 gate 밖의 행위
- ALLOWED_FILES 밖의 tracked 변경, PROTECTED_FILES 변경
- 이 Work Order 또는 ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick
- fetch --all, fetch --prune
- hooks / settings / .claude 변경 또는 guard 우회
- 기존 worktree/branch 삭제·수정, 기존 untracked/ignored/reference artifact 정리
- C:/MoneyLab(`docs/chatgpt-task-handoff`)과 그곳 미커밋 파일 변경
- AGENTS.md / .agents/** 도입, BT review 문서 2개 처리, BT-3d 시작
- 인라인 인터프리터 실행, 임시 스크립트

## DESIGN_CONTRACT

DESIGN_CONTRACT: 아래 내용을 IMPLEMENTATION에서 작성한다. Work Order v1.1 계약(대화로 확정)을 따른다.

1. CLAUDE.md (영구 workflow 규칙만, task별 내용 금지; 기존 절은 유지하고 Work Order 절을 추가)
   - Work Order 발견 방식: `docs/tasks/<TASK_ID>/WORK_ORDER.md` + ACCEPTED `ERRATA-<NNN>.md`
   - repository priority (PRIORITY 1-5)
   - Gate Authorization: 대화에서 명시적으로 승인된 gate 하나만 수행
   - immutable Work Order / ERRATA (WORKSPACE_SETUP의 C1과 ERRATA 커밋에서 최초 생성할 때 외에는 쓰지 않음)
   - ALLOWED/PROTECTED invariant (`ALLOWED_FILES ∩ PROTECTED_FILES = ∅`, `docs/tasks/<TASK_ID>/**`는 항상 PROTECTED)
   - mutation approval 세 겹(Work Order 최대 범위, Gate Authorization, tool permission/guard)
   - STOP rules
   - 다른 worktree/artifact 보존
   - guard/hook/settings 우회 금지
   - evidence classification (GIT_VERIFIABLE / CLAUDE_REPORTED / INDEPENDENT)
2. docs/tasks/README.md
   - Work Order v1.1 개념, 역할 분리(ChatGPT, Work Order, Claude Code, User, Git)
   - priority model
   - gate sequence와 각 gate의 목적, 허용 행위, 진입/완료 조건, 필수 증거, STOP 조건
   - Gate Authorization과 권장 문구
   - storage/commit model: task branch에서 C1(Work Order) -> Ce(ACCEPTED ERRATA) -> Ci(구현), merge commit PR 하나
   - immutable Work Order/ERRATA, allowlist/protected invariant, 감사 범위(구현 커밋 vs PR 전체)
   - mutation approval, STOP conditions, evidence model, 보고는 채팅만
3. docs/tasks/TEMPLATE.md
   - `moneylab.work_order/1` 템플릿, Markdown `KEY: value` 형식(YAML front matter 없음)
   - 필수 필드, GATE_SEQUENCE, GATE_TRANSITION_RULES, ALLOWED_FILES, PROTECTED_FILES, DESIGN_CONTRACT,
     TEST_GATES, E2E_GATES, REQUIRED_EVIDENCE, REQUIRED_REPORT, STOP_CONDITIONS
   - ERRATA 템플릿(TARGET_WO, NNN, 변경 필드, 근거, STATUS: PROPOSED | ACCEPTED)

## TEST_GATES

TEST_GATES:
- IMPLEMENTATION 후: `tests/test_repo_hygiene.py`, `tests/test_skills.py`, `tests/test_agent_guard.py` 통과
- IMPLEMENTATION 후: 전체 pytest, failed 0 / errors 0
- `git diff --check` 깨끗함, 변경 파일 집합 = ALLOWED_FILES

## E2E_GATES

E2E_GATES:
- CLEAN_COMMIT_E2E: clean commit에서 전체 pytest, failed 0 / errors 0
- 문서 전용 task이므로 backtest E2E는 요구하지 않는다(코드 변경 0 확인으로 대체: src/**, tests/**, configs/** diff 0)

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base SHA/tree, C1 SHA/parent/tree, Work Order 파일 sha256, 커밋별 파일 집합과 diff stat, merge parent/tree
- CLAUDE_REPORTED: pytest 결과
- INDEPENDENT: PR CI 결과, GitHub 화면(사용자 확인)
- 보고서는 각 값의 evidence 등급을 표시한다. Claude가 실행한 결과를 INDEPENDENT로 표시하지 않는다.

## REQUIRED_REPORT

REQUIRED_REPORT: 각 gate의 보고는 해당 Gate Authorization 메시지가 지정한 key 목록으로 끝내고, 최소 다음을 포함한다.
- WORK_ORDER_CONTRACT_VERSION, TASK_ID, 현재 gate
- HEAD/parent/tree, 변경 파일 집합, protected diff, worktree clean, diff --check
- 증거 등급 표시, DEVIATIONS, ISSUES
- `<GATE>_PASS = YES / NO`, `READY_FOR_<NEXT_GATE> = YES / NO`

## STOP_CONDITIONS

STOP_CONDITIONS:
- base/HEAD/tree가 기대와 다름
- ALLOWED_FILES 밖 tracked 변경 또는 PROTECTED_FILES 변경
- ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기가 실제 base 상태와 다름
- guard deny 또는 permission prompt 거절
- 테스트 실패/에러
- 계약 모순 또는 상위 규칙과 충돌
- 예상하지 못한 untracked 파일
- Work Order 파일 sha256이 C1과 다름

## REPORT_STORAGE

REPORT_STORAGE: gate별 보고는 채팅만. 저장소에 보관하지 않는다. COMPLETE 시 짧은 evidence summary는 별도 승인 후에만 보관한다.
