# Work Order (docs/tasks) — 계약 v1.2

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
| PR_CI | PR과 CI | v1.1: 없음 (Claude는 compare URL·PR 본문만 제공). v1.2: §13 조건을 모두 만족하면 `gh pr create` 1회 | push 완료 | PR 범위(git 기준), CI 결과(v1.1: 사용자 확인, v1.2: REQUIRED_CI_CHECKS 확인) |
| MERGE | 통합 | v1.1: 없음 (사용자가 GitHub UI에서 merge commit으로). v1.2: §13 사전 검증을 모두 통과하면 `gh pr merge <N> -R <repo> --merge --match-head-commit <SHA>` 1회 | CI 성공, 사용자 결정 | merge 방식 = Create a merge commit |
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

작업 상태 스냅샷(`python -m moneylab.workstate`, AUTO-02)은 gate 보고가 아니다. ignored 경로 `data/processed/workstate/`에만 쓰는 비권위 로컬 기록이며 Git에 넣지 않는다. 승인·권한·gate PASS를 만들지 않고 종료된 BUNDLE_AUTHORIZATION을 되살리지 않는다. 일치 판정은 새 승인의 ENTRY 값을 대조하는 데에만 쓴다. 이 기록에는 위의 파일 보관 제한이 적용되지 않는다.

실행 증거 기록(python -m moneylab.runlog, AUTO-03)은 gate 보고가 아니다. ignored 경로 data/processed/runlog/에 보관하는 외부 제공 evidence의 비권위 로컬 기록이다. 형식·내부 일관성·파일 해시 검사는 실제 실행, 작성자 진위, 승인, gate PASS, 자동 재개 권한을 증명하지 않는다. NOT_FOUND는 기록 부재이며 미실행을 뜻하지 않는다. 이 기록에는 위의 gate 보고 파일 보관 제한이 적용되지 않는다.

## 12. 사용 흐름 (예: BT-3d)

1. ChatGPT와 DESIGN_INVESTIGATION, CONTRACT_REVIEW를 진행한다(Claude는 읽기만, 보고는 채팅).
2. ChatGPT가 `TEMPLATE.md` 형식으로 `docs/tasks/BT-3d/WORK_ORDER.md` 문구를 확정한다.
3. 사용자: `GATE_AUTHORIZATION: BT-3d WORKSPACE_SETUP` (+ Work Order 문구). Claude는 branch·worktree를 만들고 C1을 커밋하고
   sha256과 C1 SHA를 보고한다.
4. 사용자: `GATE_AUTHORIZATION: BT-3d IMPLEMENTATION WO@<C1>`. Claude는 ALLOWED_FILES만 바꾸고 TEST_GATES를 돌리고 보고한다.
5. PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH 를 각각 승인받아 진행한다.
6. PR_CI, MERGE: v1.1 Work Order는 사용자가 GitHub에서 PR을 만들고 CI를 확인하고 merge commit으로 합친다. v1.2 Work Order는 §13에 따라, 승인된 경우 Claude가 `gh pr create`·`gh pr merge --merge`를 실행할 수 있다.
7. POST_MERGE_AUDIT -> COMPLETE.
8. 계약 변경이 필요하면 언제든 ChatGPT가 `ERRATA-<NNN>.md`를 쓰고, 사용자가 ACCEPTED로 승인한다.

## 13. PR·merge 실행 규칙 (v1.2)

적용 범위: `WORK_ORDER_CONTRACT_VERSION: v1.2` 이상인 Work Order에만 적용한다. v1.1 Work Order의 PR_CI·MERGE는 v1.1 규칙을 따르며, 이 절의 실행 권한은 소급되지 않는다. v1.1 Work Order가 자기 ALLOWED_ACTIONS에 명시한 권한은 그 Work Order 안에서만 유효하다.

v1.1 규칙(유지): PR_CI에서 Claude는 compare URL·PR 본문만 제공한다. MERGE는 사용자가 GitHub UI에서 merge commit으로 합친다.

v1.2 규칙:

- 결정은 사용자, 실행은 Claude다. 실행 권한은 Gate Authorization 1건당 명령 1회이고, guard ASK 승인 창에서 사용자가 다시 승인해야 한다(§8 세 겹 승인).
- PR 생성(PR_CI): Gate Authorization에 `PR_CREATE: YES`, 저장소, base, head branch, head SHA, 확정된 PR 제목·본문이 있고, 원격 head = 로컬 HEAD = 승인된 SHA이며, 같은 head/base의 열린 PR이 없을 때만 `gh pr create`를 1회 실행한다.
- merge(MERGE): Gate Authorization에 `MERGE_EXECUTE: YES`, PR 번호, head SHA가 있고 다음 사전 검증(읽기 전용)을 모두 통과할 때만 `gh pr merge <N> -R <repo> --merge --match-head-commit <SHA>`를 1회 실행한다.
  1. PR이 OPEN이고 draft가 아니며, base = main, head branch가 일치한다.
  2. PR head SHA = 승인된 SHA = 원격 branch head다.
  3. PR 커밋·파일 집합 = Work Order(와 ACCEPTED ERRATA)의 PR 범위다.
  4. Work Order `REQUIRED_CI_CHECKS`의 모든 job이 그 head SHA에서 SUCCESS다.
  5. Work Order·ERRATA가 요구한 추가 증거를 사용자가 수락했다.
  6. mergeable = MERGEABLE이다(merge conflict 없음).
  7. 원격 main = Work Order가 기대한 base다. 다르면 멈추고 보고한다.
- merge 방식은 Create a merge commit(`--merge`)만 허용한다. `--admin`, `--auto`, `--squash`, `--rebase`, `--delete-branch`, `--force`는 쓰지 않는다. `gh pr edit`·`gh pr close`, CI 재실행, 자동 재시도는 이 절로 허용되지 않는다.
- 멈춤: 사전 검증 실패 또는 확인 불가, head SHA 변경, 필수 CI 미성공·진행 중, 중복 PR, 승인문 필수 값 누락, guard deny·ASK 거절, gh 명령 실패. 실패한 gh 명령은 재시도하지 않고 읽기로 상태만 확인해 보고한다.
- merge 뒤에는 보고하고 멈춘다. POST_MERGE_AUDIT는 별도 Gate Authorization으로 반드시 수행하고, 통과해야 COMPLETE로 간다. 사용자 승인 없는 merge(`--auto`, 예약·반복 실행)는 없다.

## 14. 계약 v1.3: Bundled Gate Authorization (BGA)

적용 범위: 이 절은 GOV-AUTOMATION-02 merge 뒤 새로 발행되고 Metadata에 `WORK_ORDER_CONTRACT_VERSION: v1.3`과 `BUNDLE_ELIGIBLE: YES`를 선언한 Work Order에만 적용한다. v1.2 이하 Work Order에는 소급하지 않는다. 이 절을 도입한 GOV-AUTOMATION-02 자신에는 적용하지 않는다. v1.3 Work Order에서 이 절은 §3 전환 규칙의 "한 gate씩", §4의 "gate 하나", §8의 "재시도도 새 승인", §9의 "테스트 실패 시 멈춤"에 대한 예외로, 아래 조항이 정한 범위에서만 적용된다. 우선순위(§2)는 바꾸지 않는다.

- BGA-0 지위: BGA는 우선순위 4(Work Order·Gate Authorization) 층의 승인 형식이다. 우선순위 1–3(안전·도구 제약, guard deny·ask, settings 승인 창, CLAUDE.md·.claude·docs/agent_workflow.md, 고정·사전등록 계약)은 묶음 안에서도 그대로 적용된다. BGA는 settings·guard 승인 창을 대신하지 않는다.
- BGA-1 구간: 묶을 수 있는 구간은 (a) IMPLEMENTATION → PRECOMMIT_AUDIT → COMMIT → CLEAN_COMMIT_E2E의 연속 부분 구간, (b) POST_MERGE_AUDIT → COMPLETE뿐이다. DESIGN_INVESTIGATION, CONTRACT_REVIEW, WORKSPACE_SETUP, ERRATA 고정(Ce), PUSH, PR_CI, MERGE, IMPLEMENTATION으로의 후퇴는 묶을 수 없고 개별 Gate Authorization이 필요하다. 구간은 Work Order의 `BUNDLE_MAX_RANGE` 안이어야 한다.
- BGA-2 형식: 사용자가 현재 세션의 대화 메시지로 다음 키를 모두 적는다. `BUNDLE_AUTHORIZATION: <TASK_ID> <FROM>..<TO> WO@<C1 SHA>`, `ERRATA: <NONE | ERRATA-NNN@<Ce SHA>, ...>`, `ENTRY_HEAD: <SHA>`, `ENTRY_TREE: <SHA>`, `BUDGET: <항목=값, ...>`, `EXPIRES_UTC: <ISO-8601>`, `EXPECTED_ASK: <gate:rule:횟수, ...>`, `CONTRACT_HASHES: <Work Order 및 각 ACCEPTED ERRATA의 Git blob 내용 SHA-256>`, `ENTRY_CHANGES: <NONE | 경로·A/M/D·작업 파일 SHA-256·index blob 내용 SHA-256 또는 ABSENT의 전체 목록>`, `IMPLEMENTATION_COMMIT: <NONE | SHA>`. PRECOMMIT_AUDIT 또는 COMMIT부터 시작하면 ENTRY_CHANGES와 선행 gate 완료 조건의 재검증이 필수다. CLEAN_COMMIT_E2E부터 시작하면 IMPLEMENTATION_COMMIT이 필수이며 ENTRY_HEAD와 같아야 한다. 키가 빠지거나 BGA-1을 어기면 승인 전체가 INVALID이고 어떤 gate도 시작하지 않는다. 요약문, 모델 메모리, 이전 gate 보고만으로 BUNDLE_AUTHORIZATION을 새로 구성하거나 복원하지 않는다.
- BGA-3 진행: 각 gate를 시작하기 전에, 현재 세션에서 사용자가 보낸 원본 BUNDLE_AUTHORIZATION 메시지의 원문을 확인할 수 있어야 한다. 원문을 신뢰할 수 있는 형태로 확인할 수 없으면 즉시 STOP한다. 각 gate는 아래 상태 전이 기준과 Work Order의 완료 조건을 모두 만족할 때만 다음 gate로 넘어간다. 전진 조건은 git·테스트를 다시 실행해 확인하며 이전 보고를 근거로 삼지 않는다. gate마다 채팅으로 보고하되 보고는 승인 요청이 아니다. git commit은 COMMIT gate에서 1회만 허용한다. git commit을 포함한 모든 settings·guard ASK 승인 창은 사용자가 그 창에서 별도로 승인해야 한다. EXPECTED_ASK에 없는 ASK가 나타나면 STOP한다. ASK가 거절되거나 응답이 없으면 STOP한다. BGA는 도구 권한 승인이나 guard 판정을 대체하지 않는다.
- BGA-4 수정 반복: IMPLEMENTATION 안에서 신규 테스트 또는 ALLOWED_FILES 테스트의 실패와 ruff·mypy 실패는 BUDGET 안에서 ALLOWED_FILES만 고쳐 `[A]` 명령으로 다시 실행할 수 있다. ALLOWED_FILES 밖 기존 테스트의 실패(회귀)는 고치지 않고 STOP한다. COMMIT 이후의 실패는 STOP이며 자동 후퇴는 없다.
- BGA-5 종료: <TO> gate 보고 완료, STOP, 예산 초과, EXPIRES_UTC 경과, 세션 종료 또는 새 세션 시작 중 하나가 일어나면 묶음은 끝나고 다시 쓰지 않는다. 같은 세션 안의 컨텍스트 요약만으로는 묶음이 끝나지 않지만, 요약 뒤에도 BGA-3의 원문 확인을 통과해야 한다. 끝난 묶음을 이어서 하려면 새 BUNDLE_AUTHORIZATION 또는 단일 Gate Authorization이 필요하며, 그 ENTRY_HEAD·ENTRY_TREE는 그 시점의 실제 git 상태여야 한다. 자동 재개는 없다.
- BGA-6 예산: BUDGET 값은 소유자가 승인문마다 정하는 초기 실험값이며 검증된 안전 기준이 아니다. 이 계약은 값이 아니라 "상한에 닿으면 STOP"만 정한다. 항목은 묶음 전체 시간, 명령당 timeout, 전체 pytest 실행 횟수, IMPLEMENTATION 수정 반복 횟수, 같은 실패의 연속 횟수, 도구 호출 수다. 도구 호출 수와 시간은 Claude가 스스로 세는 절차 상한이며 코드로 강제되지 않는다. LLM 비용은 측정 수단이 없어 항목에 넣지 않는다.
- BGA-7 Evidence: gate 보고와 그 값은 비권위 실행 기록이며 승인·권한·전진 조건 PASS를 만들지 않는다. 보고는 §11대로 채팅에만 둔다. 이 계약은 Evidence 저장 기능을 전제하지 않는다.
- BGA-8 테스트 약화: 자동 검사기는 없다. PRECOMMIT_AUDIT에서 다음을 기존 도구로 수동 확인하고 보고한다. (A) 기준선 대비 수집 테스트 ID 감소(`pytest --collect-only`), 테스트 함수·파일 삭제, `skip`·`skipif`·`xfail`·`pytest.skip(`·`pytest.xfail(` 추가, ALLOWED_FILES 밖 테스트 파일 변경(git diff). (B) 단정의 의미 완화, 허용 목록·tolerance 확대, mock·fixture를 통한 검증 경로 우회는 이 확인으로 판정할 수 없으며 "독립 검토 필요"로 보고하고 PASS로 단정하지 않는다.
- BGA-9 금지: 묶음은 다음을 허용하지 않는다. 사전등록 생성·변경·확정, research-final, test split 열람, 실데이터 수집(live record, live candles-pull), 네트워크 접근(단 구간 (b)의 POST_MERGE_AUDIT가 §3에 따라 이미 갖는 main ref fetch 1회는 예외), 주문·지갑·키·자금, guard·hook·settings·.github·.gitignore 변경, Work Order·ERRATA 생성·수정, push, PR 생성, merge, branch 삭제, ALLOWED_FILES 밖 변경, PROTECTED_FILES 변경, guard deny 뒤 같은 목적의 변형 재시도.
- BGA-10 실패: F1 신규·ALLOWED_FILES 테스트 실패(IMPLEMENTATION)는 BGA-4에 따르고, 같은 실패가 연속 상한에 닿으면 STOP한다. F1' 회귀 또는 COMMIT 이후 실패는 STOP한다. F2 환경 문제(venv·Python·git 경로 불일치, 도구 crash, timeout)는 STOP하며 읽기 전용 관찰 명령만 1회 재실행할 수 있다. F3 계약 위반(범위 밖·보호 diff, 해시·SHA·tree 불일치, 예상 밖 untracked)은 즉시 STOP하며 되돌리기 명령을 쓰지 않는다. F4 guard deny는 즉시 STOP하며 재시도·변형하지 않는다. F5 예상 밖·거절·무응답 ASK는 STOP한다. F6 예산 초과는 STOP한다. F7 원본 BUNDLE_AUTHORIZATION 원문 확인 불가는 STOP한다. 모든 STOP은 BGA-5에 따라 묶음을 끝내고 분류, 마지막 PASS gate, 실제 HEAD·tree를 보고한다.

상태 전이 기준(H_e·T_e = ENTRY_HEAD·ENTRY_TREE, C = COMMIT gate가 만든 커밋):

| gate | 진입 기준 | 종료 기준 |
|---|---|---|
| 묶음 시작 | HEAD = H_e, tree = T_e, H_e는 C1(또는 Ce) 자신 또는 후손, Work Order·ERRATA blob sha256 = CONTRACT_HASHES. FROM이 IMPLEMENTATION 또는 CLEAN_COMMIT_E2E이면 tracked·index diff 0, untracked 0. FROM이 PRECOMMIT_AUDIT 또는 COMMIT이면 현재 변경 전체가 ENTRY_CHANGES와 같고 ALLOWED_FILES 안이며, 선행 gate의 완료 조건을 현재 증거로 검증. FROM이 POST_MERGE_AUDIT이면 merge commit과 승인 PR head를 검증하고 clean. | — |
| IMPLEMENTATION | HEAD = H_e | HEAD = H_e, 변경 ⊆ ALLOWED_FILES, 작업 파일 바이트 SHA-256 집합 W와 Git에 stage될 내용 SHA-256 집합 S |
| PRECOMMIT_AUDIT | HEAD = H_e, 작업 파일 해시 = W, stage될 내용 해시 = S. 이 gate부터 시작하면 ENTRY_CHANGES로 W·S를 확정 | HEAD = H_e, W·S 불변 |
| COMMIT | HEAD = H_e, 작업 파일 해시 = W, staged blob 내용 해시 = S. 이 gate부터 시작하면 ENTRY_CHANGES와 선행 감사 조건을 재검증 | HEAD = C, parent(C) = H_e, 커밋 파일 집합 = 변경 집합, commit blob 내용 해시 = S, clean. 이후 기준은 C와 tree(C) |
| CLEAN_COMMIT_E2E | HEAD = C, tree = tree(C), clean. 이 gate부터 시작하면 C = 승인된 IMPLEMENTATION_COMMIT = ENTRY_HEAD | HEAD·tree 불변, 실행 전후 git status(ignored 포함) 동일 |
| POST_MERGE_AUDIT | ENTRY_HEAD = merge commit M, parent2(M) = 승인된 PR head | 변경 없음 |
| COMPLETE | 감사 PASS | 보고 |

해시 기준: W는 작업 파일의 실제 바이트, S는 저장소 속성에 따라 Git에 저장될 내용의 바이트를 각각 SHA-256으로 계산한다. Git blob object ID와 내용 SHA-256을 혼동하지 않는다. 삭제 경로는 ABSENT로 표시한다. 줄바꿈 변환이 있으면 W와 S가 달라질 수 있으므로 두 값을 직접 같다고 가정하지 않는다. staged·commit 내용은 S와 비교하고 작업 파일 변경은 W로 확인한다. 승인되지 않은 파일·속성·필터 변화는 STOP한다.

효과 범위: BGA는 채팅으로 보내는 Gate 승인의 수만 줄인다. settings·guard 승인 창(git commit 등)과 그 횟수는 바뀌지 않는다.
