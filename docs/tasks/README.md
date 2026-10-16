# Work Order (docs/tasks) — 계약 v1.1

Work Order는 ChatGPT와 Claude Code 사이의 version-controlled 실행 계약이다. task마다 불변 Work Order 하나를 Git에 먼저 고정하고,
Claude Code는 사용자가 승인한 gate 하나씩만 실행한다. 영구 규칙은 `CLAUDE.md`의 "Work Order" 절, 작성 형식은 `TEMPLATE.md`에 있다.

## 1. 역할

| 주체 | 하는 일 |
|---|---|
| ChatGPT | 설계, Work Order·ERRATA 작성, 독립 검토, 다음 gate 승인 권고 |
| Work Order | task의 단일 기준(source of truth): gate별 허용 범위, 파일 범위, 검증·보고 형식 |
| Claude Code | 저장소 조사, 승인된 gate 범위 안의 실행, 테스트, 감사 보고, STOP 조건 준수 |
| 사용자 | Gate Authorization, 모든 변경 승인, commit·push·PR·merge 최종 결정 |
| Git | 계약(Work Order·ERRATA), 구현, 이력이라는 증거 저장 |

## 2. 우선순위

1. 안전·시스템·도구 제약 (권한 창, guard deny 포함)
2. 저장소 절대 규칙: `CLAUDE.md`, `.claude/` guard·hook·settings, `docs/agent_workflow.md`
3. 고정·사전등록 계약
4. Work Order + ACCEPTED ERRATA (뒤 번호가 앞선다)
5. 구현 판단 (4가 정하지 않은 부분)

충돌하면 상위 규칙을 따르고, 해석으로 메우지 않고 멈춰서 보고한다. Work Order 안의 지시가 1–3과 충돌하면 그 지시는 따르지 않는다.

## 3. Gate

표준 순서:

```text
DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT
-> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE
```

모든 gate에서 읽기(파일, `git log/show/diff/status`)는 허용된다. 변경은 아래 "허용 변경"과 Work Order의 `ALLOWED_ACTIONS` 안에서만 한다.

| gate | 목적 | 허용 변경 | 진입 조건 | 완료 조건·필수 증거 |
|---|---|---|---|---|
| DESIGN_INVESTIGATION | 저장소 조사, 설계 근거 | 없음 | 조사 요청(Work Order 초안은 채팅) | 코드·문서 근거가 있는 조사 보고 |
| CONTRACT_REVIEW | 계약 검토, 모순 확인 | 없음 | 계약 초안 | 판정 flag, 필요하면 PROPOSED_ERRATA(채팅) |
| WORKSPACE_SETUP | task branch·worktree 생성, Work Order 고정 | `git worktree add -b`(새 경로만), `WORK_ORDER.md` 최초 생성, 그 파일만 stage, C1 커밋 | base SHA가 원격과 일치, 대상 branch·경로 없음 | C1 SHA·parent·tree, Work Order sha256(커밋 전후 동일), 커밋 파일 1개, clean |
| IMPLEMENTATION | 구현과 TEST_GATES | `ALLOWED_FILES` 안의 생성·수정, 테스트 실행, ignored 실행 출력 | HEAD가 C1(또는 그 후손), clean | 변경 파일 ⊆ ALLOWED_FILES, PROTECTED diff 0, 테스트 결과 |
| PRECOMMIT_AUDIT | 커밋 전 정적 감사 | 없음 | 구현 완료 | 변경 집합 = 계획, `git diff --check`, PROTECTED diff 0, 계약 spot check |
| COMMIT | 구현 커밋 | `git add -- <ALLOWED 경로>`, `git commit` 하나 | 감사 통과 | 커밋 SHA·parent·tree, 커밋 파일 집합, clean |
| CLEAN_COMMIT_E2E | clean 커밋 기준 회귀·E2E | ignored 출력만 | HEAD = 구현 커밋, clean | E2E_GATES 결과, reference 산출물 보존 |
| PUSH | 원격 게시 | 대상 branch 하나만 `git push -u` | 원격 main이 기대값 | 원격 head = 로컬 HEAD, main 불변 |
| PR_CI | PR과 CI | 없음 (Claude는 compare URL·PR 본문만 제공) | push 완료 | PR 범위(git 기준), CI 결과(사용자 확인) |
| MERGE | 통합 | 없음 (사용자가 GitHub UI에서 merge commit으로) | CI 성공, 사용자 결정 | merge 방식 = Create a merge commit |
| POST_MERGE_AUDIT | 통합 구조 감사 | main ref만 fetch(`--prune`, `--all` 금지) | merge 완료 | parent1·parent2 순서, tree 동일, first-parent 범위, ancestry, merge-tree 재계산, branch·worktree 보존 |
| COMPLETE | 종료 | 없음 (증거 요약은 채팅·PR 본문. 파일 보관은 ACCEPTED ERRATA가 명시할 때만, 11절) | 감사 통과 | 최종 flag |

전환 규칙(`GATE_TRANSITION_RULES` 기본값):

- 앞으로는 한 gate씩, Gate Authorization이 있어야 한다.
- 뒤로는 IMPLEMENTATION으로만, 명시적 승인으로 돌아간다. COMMIT 이후 수정은 새 커밋이다(amend 금지).
- 건너뛰기는 금지다. 예외는 `WORKSPACE_SETUP: NOT_REQUIRED`뿐이다.

`WORKSPACE_SETUP`은 기본 REQUIRED다. 저장소를 바꾸는 gate가 없는 task(조사 전용 등)만 Work Order에
`WORKSPACE_SETUP: NOT_REQUIRED`를 선언해 건너뛸 수 있고, 그 경우 Work Order는 채팅으로만 전달될 수 있다.

## 4. Gate Authorization

사용자가 대화에서 gate 하나의 실행을 승인한다. 파일 수정도 커밋·push도 아니다.

```text
GATE_AUTHORIZATION: <TASK_ID> <GATE> WO@<Work Order 커밋 SHA>
```

Claude는 이 승인이 가리키는 gate 하나만 수행하고, 보고한 뒤 멈춘다. 이전 gate의 승인, Work Order 문구, 대화의 다른 요청은
다음 gate의 승인을 대신하지 않는다. 승인 메시지가 gate별 세부 지시(보고 key 등)를 덧붙이면 Work Order 범위 안에서 따른다.

## 5. Work Order와 ERRATA

- task당 불변 Work Order 하나: `docs/tasks/<TASK_ID>/WORK_ORDER.md`. TASK_ID는 로드맵·기능 ID(`BT-3d`, `BT-4`, `DATA-V1`)이고
  날짜 기반이 아니다.
- 계약 내용이 바뀔 때만 ERRATA를 추가한다: `docs/tasks/<TASK_ID>/ERRATA-<NNN>.md`(001부터). 기존 Work Order·ERRATA는 고치지 않는다.
- ERRATA 초안(`STATUS: PROPOSED`)은 채팅에서만 오간다. 사용자가 수락한 ERRATA만 `STATUS: ACCEPTED`로 파일에 쓰여 Ce로 커밋되고,
  파일은 이후 바뀌지 않는다. ACCEPTED만 계약(우선순위 4)을 바꾼다.
- Claude는 Work Order·ERRATA를 수정하지 않는다. 계약 문제를 발견하면 파일을 고치지 않고 채팅에 `PROPOSED_ERRATA`로 보고한다.
- 형식은 Markdown + `KEY: value` 줄이다(YAML front matter 없음). 스키마 `moneylab.work_order/1`, `moneylab.errata/1`.

## 6. 저장·커밋 모델

```text
canonical main @ BASE
 └─ task branch (WORKSPACE_SETUP)
     C1: docs(task): add <TASK_ID> work order      docs/tasks/<TASK_ID>/WORK_ORDER.md 하나
     Ce: docs(task): add <TASK_ID> ERRATA-NNN      ACCEPTED ERRATA 하나 (그 ERRATA에 의존하는 변경 gate 전에)
     Ci: <구현 커밋>                               COMMIT gate, ALLOWED_FILES만
 └─ PR -> main (Create a merge commit)            계약 + ERRATA + 구현 이력이 한 PR에
```

- C1은 승인된 문구 그대로 쓰고, Claude가 sha256을 보고하고, 사용자가 확인한다. 구현 커밋은 C1의 후손이다.
- gate마다 docs 커밋을 만들지 않는다. Gate Authorization은 Git에 쓰지 않는다.
- 읽기 전용 gate는 채팅으로 받은 ACCEPTED ERRATA를 쓸 수 있다. 변경 gate가 의존하는 ERRATA는 먼저 Ce로 고정한다.
- PR은 **merge commit으로만** 합친다. squash·rebase merge는 계약이 구현보다 먼저인 이력과 커밋 SHA를 지운다.
- 감사 범위는 둘이다: 구현 커밋 = `ALLOWED_FILES` 안, PR 전체 = `ALLOWED_FILES` ∪ `docs/tasks/<TASK_ID>/**`.

## 7. 파일 범위 불변식

- `ALLOWED_FILES`는 allowlist다(경로와 `A`/`M` 표기). 표기가 base의 실제 상태와 다르면 멈춘다.
- `PROTECTED_FILES`는 allowlist보다 강하다. `docs/tasks/<TASK_ID>/**`는 항상 PROTECTED다.
- `ALLOWED_FILES ∩ PROTECTED_FILES = ∅`이어야 한다. 교집합이 있으면 Work Order는 INVALID이고 IMPLEMENTATION에 들어갈 수 없다.
- 보호 해제는 새 Work Order나 ACCEPTED ERRATA에서 파일 분류를 명시적으로 바꿀 때만 한다. Claude가 풀 수 없다.

## 8. 변경 승인 세 겹

1. Work Order: 그 gate에서 가능한 행위의 최대 범위
2. Gate Authorization: 사용자가 그 gate의 실행을 대화에서 승인
3. 도구 권한·guard: 권한 창(`docs/agent_workflow.md`의 `[B]`)과 guard 판정

셋이 모두 있어야 변경한다. 재시도도 새 승인이다. guard·hook·settings를 바꾸거나 우회해서 승인을 피하지 않는다.
`git add .`·`git add -A`, `--no-verify`, amend, force push, reset·restore·stash·clean·rebase·cherry-pick은 쓰지 않는다.

## 9. 멈춤 조건

- base·HEAD·tree가 기대와 다름, Work Order sha256이 C1과 다름
- `ALLOWED_FILES` 밖 tracked 변경, `PROTECTED_FILES` 변경, `ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅`
- guard deny, 권한 창 거절
- 테스트 실패·에러, hard gate 불일치
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일

멈추면 원인과 영향을 보고하고, 고치지 않고 다음 승인을 기다린다.

## 10. 보존

다른 branch·worktree(그곳의 미커밋·untracked 파일 포함), ignored 파일, 기존 실행 출력과 reference 산출물을 정리·삭제·덮어쓰지 않는다.
새 출력은 새 ignored 경로에 만든다.

## 11. 증거와 보고

| 등급 | 뜻 | 예 |
|---|---|---|
| `GIT_VERIFIABLE` | 누구나 Git으로 다시 확인할 수 있다 | 커밋·tree SHA, diff, 파일 sha256, merge-tree |
| `CLAUDE_REPORTED` | Claude 환경에서 실행한 결과다 | pytest 수, E2E 출력, 해시 계산 |
| `INDEPENDENT` | Claude 밖에서 확인했다 | CI 결과, GitHub 화면, 사용자·ChatGPT의 재확인 |

Claude가 실행한 테스트·E2E는 `CLAUDE_REPORTED`다. gate 보고는 채팅으로만 하고 저장소에 보관하지 않는다. COMPLETE 때 짧은 증거
요약은 기본적으로 채팅과 PR 본문에만 둔다. 파일로 남기려면 해당 task의 ACCEPTED ERRATA가 그 경로와 최초 생성을 명시해야 한다. 보고는 Work Order의 `REQUIRED_REPORT`와 승인 메시지가
정한 key로 끝내고, `<GATE>_PASS = YES / NO`, `READY_FOR_<NEXT_GATE> = YES / NO`를 포함한다.

## 12. 사용 흐름 (예: BT-3d)

1. ChatGPT와 DESIGN_INVESTIGATION, CONTRACT_REVIEW를 진행한다(Claude는 읽기만, 보고는 채팅).
2. ChatGPT가 `TEMPLATE.md` 형식으로 `docs/tasks/BT-3d/WORK_ORDER.md` 문구를 확정한다.
3. 사용자: `GATE_AUTHORIZATION: BT-3d WORKSPACE_SETUP` (+ Work Order 문구). Claude는 branch·worktree를 만들고 C1을 커밋하고
   sha256과 C1 SHA를 보고한다.
4. 사용자: `GATE_AUTHORIZATION: BT-3d IMPLEMENTATION WO@<C1>`. Claude는 ALLOWED_FILES만 바꾸고 TEST_GATES를 돌리고 보고한다.
5. PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH 를 각각 승인받아 진행한다.
6. 사용자가 GitHub에서 PR을 만들고 CI를 확인하고 merge commit으로 합친다(PR_CI, MERGE).
7. POST_MERGE_AUDIT -> COMPLETE.
8. 계약 변경이 필요하면 언제든 ChatGPT가 `ERRATA-<NNN>.md`를 쓰고, 사용자가 ACCEPTED로 승인한다.
