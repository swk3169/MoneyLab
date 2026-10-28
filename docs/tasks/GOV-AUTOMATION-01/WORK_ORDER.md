# Work Order: GOV-AUTOMATION-01 — Work Order contract v1.2: approved PR creation and merge execution

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/GOV-AUTOMATION-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

이 파일이 계약의 유일한 출처다. 대화 기억이나 채팅 보고서에 의존하지 않는다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: GOV-AUTOMATION-01
TASK_ID: GOV-AUTOMATION-01
TITLE: Work Order contract v1.2: approved PR creation and merge execution
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 0848cfc6ddf04d7ebdeb5d5e66de47ee1760c9cf
CANONICAL_BASE_TREE: b364858178d0a1b5e3f861b210866e51abe20aa1
BASE_BLOBS: docs/tasks/README.md 88f2d93ea167c7324c7e5cd81ad40883273f1b3f (153 lines), docs/tasks/TEMPLATE.md 5544a18f05c678da302c338632788c060d5226f0 (183 lines), CLAUDE.md 81bd3926472e6252e4b136a7eb34be2bf5a6e974 (67 lines), docs/agent_workflow.md 6ca61105302ee38503b4e34d0278bb53a56ea040 (138 lines). 모두 LF, final newline. (CANONICAL_BASE 기준, WORKSPACE_SETUP에서 확인)
TARGET_BRANCH: chore/gov-automation-01
TARGET_WORKTREE: C:/MoneyLab-gov-automation-01
SOURCE_WORKTREE: C:/MoneyLab-mc-v06 (WORKSPACE_SETUP 명령을 실행하는 기존 worktree. 파일·index·branch를 바꾸지 않는다.)
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
PRIOR_GATES: DESIGN_INVESTIGATION(설계 검토), CONTRACT_REVIEW, WORK_ORDER_DRAFT(정합성 검토 포함). 모두 채팅, C1 이전.
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (squash/rebase merge 금지)
REQUIRED_CI_CHECKS: ci-tests / pytest (Windows)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: GOV-AUTOMATION-01 <GATE> WO@<C1 commit>`)
- 각 gate의 보고 후 멈춘다. 이전 gate의 승인이나 이 Work Order 자체는 다음 gate의 승인이 아니다.
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping
- 역사적 BLOCKED 결과를 PASS로 바꿔 쓰지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약)을 참조한다. 이 task는 ALLOWED_FILES의 승인 문구만 바꾸며, 그 밖의 상위 규칙은 복제하지 않고 바꾸지 않는다. guard deny는 우회하지 않는다. 이 task 자신은 계약 v1.1로 진행하며, 이 task가 도입하는 v1.2 실행 권한을 자신에게 적용하지 않는다.

## GOAL

GOAL: Work Order 계약을 v1.2로 올려, v1.2 Work Order에서 사용자가 Gate Authorization으로 명시적으로 승인한 경우에만 Claude가 `gh pr create`(PR_CI)와 `gh pr merge --merge --match-head-commit`(MERGE)을 각 1회 실행할 수 있게 한다. v1.1 규칙은 문서에 그대로 보존하고 소급하지 않는다. 사용자의 최종 결정권과 guard ASK는 유지한다.

## BACKGROUND

BACKGROUND:
- 현재 제한의 근거: docs/tasks/README.md:47 (PR_CI "없음 (Claude는 compare URL·PR 본문만 제공)"), :48 (MERGE "없음 (사용자가 GitHub UI에서 merge commit으로)"), :151 (사용 흐름), docs/tasks/TEMPLATE.md:67–68 (ALLOWED_ACTIONS). Gate Authorization은 Work Order 범위를 넘지 못한다(README §4, §8).
- SUPERVISOR-01 D27과 DOCS-ALIGN-01 NON_GOALS(D27)는 이 문구와 실제 관행의 차이를 별도 governance task로 남겼다. 이 task가 그 정리다. 과거 Work Order·ERRATA는 바꾸지 않는다.
- 선례: docs/tasks/DOCS-STATUS-01/WORK_ORDER.md:64는 v1.1 Work Order가 자기 ALLOWED_ACTIONS에 PR 생성을 명시한 사례다.
- guard: `gh pr create`·`gh pr merge`는 `github` ask 규칙 대상이다(docs/agent_workflow.md §4). gh 게시 본문은 따로 검사된다. 이 task는 guard·hook·settings를 바꾸지 않는다. `.claude/settings.json`의 `Bash(gh pr *)` 규칙 내용은 UNVERIFIED이며 이 설계는 그 값에 의존하지 않는다.
- 테스트 제약: tests/test_skills.py는 docs/agent_workflow.md에 모든 guard 규칙 이름(백틱), 모든 tier 태그, 필수 skill·섹션 이름이 있는지 검사한다. tests/test_agent_guard.py:72는 CLAUDE.md 편집이 guard ask임을 정한다.
- 사용자 결정: 계약 v1.2, gate 이름(PR_CI, MERGE)과 GATE_SEQUENCE 유지, PR_CREATE gate 신설 없음, PR 생성·merge는 각각 명시적 Gate Authorization, guard ASK 유지, v1.1 규칙 명시 보존, 소급 금지, 이 task 자체는 v1.1.

## NON_GOALS

NON_GOALS:
- guard·hook·settings(`.claude/**`) 변경, 권한 allow 규칙 추가
- GitHub branch protection·rulesets·required status checks 설정, `.github/**` 변경
- 기존 Work Order·ERRATA 수정, 과거 D27 편차의 소급 정정
- GATE_SEQUENCE 변경, PR_CREATE 등 새 gate 신설
- DOCS-ALIGN-01(PR #33)의 PR_CI·MERGE 진행
- 코드·테스트·설정·의존성 변경
- CLAUDE.md의 54행 외 변경, docs/agent_workflow.md의 항목 8 외 변경

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP:
  A. Gate Authorization이 명시하면 `git fetch origin main`만 실행해 원격 main을 확인하고 CANONICAL_BASE_SHA·TREE와 BASE_BLOBS를 확정·보고한다. 잠정값과 다르면 멈추고 보고한다(사용자가 재기준 결정).
  B. A가 확정되고 TARGET_BRANCH·TARGET_WORKTREE·`docs/tasks/GOV-AUTOMATION-01/`이 없을 때만 다음을 진행한다.
  C. SOURCE_WORKTREE에서 `git worktree add -b chore/gov-automation-01 C:/MoneyLab-gov-automation-01 <CANONICAL_BASE_SHA>`
  D. `docs/tasks/GOV-AUTOMATION-01/WORK_ORDER.md`를 승인 문구 그대로 최초 생성하고, 그 파일만 `git add --`로 stage해 C1 커밋 `docs(task): add GOV-AUTOMATION-01 work order`를 만든다.
  E. WORK_ORDER.md의 sha256을 커밋 전후로 보고한다.
- IMPLEMENTATION: ALLOWED_FILES를 DESIGN_CONTRACT E1–E12대로 수정하고 TEST_GATES를 실행한다. CLAUDE.md 편집의 guard ASK는 사용자 승인 후에만 진행한다.
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: `git add -- docs/tasks/README.md docs/tasks/TEMPLATE.md CLAUDE.md docs/agent_workflow.md`, 커밋 하나
- CLEAN_COMMIT_E2E: E2E_GATES의 읽기 전용 확인
- PUSH: TARGET_BRANCH 하나만 `git push -u origin chore/gov-automation-01`
- PR_CI: (v1.1) compare URL·PR 본문 제공만. PR은 사용자가 만든다. CI 결과는 Gate Authorization이 명시한 범위에서 읽기 전용 관찰
- MERGE: (v1.1) 사용자 결정(GitHub UI, MERGE_METHOD). Claude는 읽기 전용 사전 검증만
- POST_MERGE_AUDIT: Gate Authorization이 명시하면 `git fetch origin main`만, 읽기 전용 구조 감사
- COMPLETE: 최종 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull
- hooks·settings·.claude 변경 또는 guard 우회, git config 변경, guard DENY 명령의 재시도·변형
- 다른 branch·worktree·untracked·ignored·reference 산출물·egg-info·외부 venv·scratchpad 정리·변경
- `.venv` 생성·설치·변경, 패키지 설치
- APPROVED_TEXT 재작성, E1–E12 밖 편집
- Claude의 `gh pr create`·`gh pr merge`·`gh pr edit` 실행 (이 task는 v1.1)
- 위 fetch·push 밖의 네트워크 쓰기, 거래 API, 자동화 실행

## ALLOWED_FILES

ALLOWED_FILES:
- M docs/tasks/README.md
- M docs/tasks/TEMPLATE.md
- M CLAUDE.md
- M docs/agent_workflow.md

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/GOV-AUTOMATION-01/** (C1의 WORK_ORDER.md 최초 생성과 ACCEPTED ERRATA 최초 생성만 예외)
- docs/tasks/*/** (기존 모든 task의 Work Order·ERRATA)
- .claude/**
- .github/**
- AGENTS.md, LICENSE, README.md, ARCHITECTURE.md, .gitattributes, .gitignore, .env.example
- src/**, tests/**, configs/**, examples/**, data/**, knowledge/**
- docs/** 중 docs/tasks/README.md, docs/tasks/TEMPLATE.md, docs/agent_workflow.md 이외 전부
- pyproject.toml, requirements.txt, requirements-dev.txt
- ALLOWED_FILES 이외의 모든 경로

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가). C1 파일 ∩ ALLOWED_FILES = ∅. 의존성 변경 0. C1·ACCEPTED ERRATA 외 새 파일 0.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- 줄 번호는 모두 BASE_BLOBS 기준이며, 같은 파일의 편집은 같은 base에 동시에 적용한다. "N행 뒤"는 base의 N행과 N+1행 사이에 삽입한다는 뜻이다. 승인 문구 블록은 12개(T1–T5, M1–M5, C1, W1)이고, 각 블록의 내용은 아래 APPROVED_TEXT의 해당 fenced block에서 여는 fence 줄과 닫는 fence 줄 사이의 줄이다(fence 줄 제외). 각 줄은 LF로 끝난다.
- E1 docs/tasks/README.md 1행 `# Work Order (docs/tasks) — 계약 v1.1`을 APPROVED_TEXT T1(1줄)로 교체한다.
- E2 docs/tasks/README.md 47행 `| PR_CI | PR과 CI | 없음 (Claude는 compare URL·PR 본문만 제공) | push 완료 | PR 범위(git 기준), CI 결과(사용자 확인) |`을 APPROVED_TEXT T2(1줄)로 교체한다.
- E3 docs/tasks/README.md 48행 `| MERGE | 통합 | 없음 (사용자가 GitHub UI에서 merge commit으로) | CI 성공, 사용자 결정 | merge 방식 = Create a merge commit |`을 APPROVED_TEXT T3(1줄)로 교체한다.
- E4 docs/tasks/README.md 151행 `6. 사용자가 GitHub에서 PR을 만들고 CI를 확인하고 merge commit으로 합친다(PR_CI, MERGE).`를 APPROVED_TEXT T4(1줄)로 교체한다.
- E5 docs/tasks/README.md 153행(`8. 계약 변경이 필요하면 …`) 뒤에 빈 줄 1줄과 APPROVED_TEXT T5(21줄)를 삽입한다.
- E6 docs/tasks/TEMPLATE.md 1행 `# Work Order·ERRATA 템플릿 (계약 v1.1)`을 APPROVED_TEXT M1(1줄)로 교체한다.
- E7 docs/tasks/TEMPLATE.md 19행 `WORK_ORDER_CONTRACT_VERSION: v1.1`을 APPROVED_TEXT M2(1줄)로 교체한다.
- E8 docs/tasks/TEMPLATE.md 32행(`MERGE_METHOD: Create a merge commit`) 뒤에 APPROVED_TEXT M3(1줄)을 삽입한다.
- E9 docs/tasks/TEMPLATE.md 67행 `- PR_CI: compare URL·PR 본문 제공만`을 APPROVED_TEXT M4(1줄)로 교체한다.
- E10 docs/tasks/TEMPLATE.md 68행 `- MERGE: 사용자 결정(GitHub UI, MERGE_METHOD)`을 APPROVED_TEXT M5(1줄)로 교체한다.
- E11 CLAUDE.md 54행 `## Work Order (`docs/tasks/`, 계약 v1.1)`을 APPROVED_TEXT C1(1줄)로 교체한다. CLAUDE.md의 다른 바이트는 바꾸지 않는다.
- E12 docs/agent_workflow.md 43행(`7. 사전등록(…)을 바꾸면 새 study다. Skill은 이를 바꾸지 않는다.`) 뒤에 APPROVED_TEXT W1(4줄)을 삽입한다. 기존 줄은 바꾸거나 지우지 않는다.
- E13 경계: E1–E12 지점 밖의 바이트는 base와 같다. LF와 파일 끝 줄바꿈 형식은 바꾸지 않는다.
- E14 기대 결과: 구현 후 각 파일의 blob = base blob에 해당 E를 적용한 결과(바이트 단위)다. 승인 문구 블록 12개의 줄 수 합계는 35이다. 기대 줄 수: docs/tasks/README.md 153 + 22 = 175, docs/tasks/TEMPLATE.md 183 + 1 = 184, CLAUDE.md 67, docs/agent_workflow.md 138 + 4 = 142. `git diff -U0`의 hunk 수: README.md 4 (E2·E3은 인접해 1 hunk), TEMPLATE.md 4 (E9·E10은 인접해 1 hunk), CLAUDE.md 1, agent_workflow.md 1, 합계 10. 줄 변화: README.md +26/−4, TEMPLATE.md +5/−4, CLAUDE.md +1/−1, agent_workflow.md +4/−0, 합계 +36/−9. APPROVED_TEXT의 실질 변경이 필요하면 구현하지 않고 멈춰서 PROPOSED_ERRATA로 보고한다.

APPROVED_TEXT T1 (docs/tasks/README.md, E1, 1줄):

````text
# Work Order (docs/tasks) — 계약 v1.2
````

APPROVED_TEXT T2 (docs/tasks/README.md, E2, 1줄):

````text
| PR_CI | PR과 CI | v1.1: 없음 (Claude는 compare URL·PR 본문만 제공). v1.2: §13 조건을 모두 만족하면 `gh pr create` 1회 | push 완료 | PR 범위(git 기준), CI 결과(v1.1: 사용자 확인, v1.2: REQUIRED_CI_CHECKS 확인) |
````

APPROVED_TEXT T3 (docs/tasks/README.md, E3, 1줄):

````text
| MERGE | 통합 | v1.1: 없음 (사용자가 GitHub UI에서 merge commit으로). v1.2: §13 사전 검증을 모두 통과하면 `gh pr merge <N> -R <repo> --merge --match-head-commit <SHA>` 1회 | CI 성공, 사용자 결정 | merge 방식 = Create a merge commit |
````

APPROVED_TEXT T4 (docs/tasks/README.md, E4, 1줄):

````text
6. PR_CI, MERGE: v1.1 Work Order는 사용자가 GitHub에서 PR을 만들고 CI를 확인하고 merge commit으로 합친다. v1.2 Work Order는 §13에 따라, 승인된 경우 Claude가 `gh pr create`·`gh pr merge --merge`를 실행할 수 있다.
````

APPROVED_TEXT T5 (docs/tasks/README.md, E5, 21줄):

````text
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
````

APPROVED_TEXT M1 (docs/tasks/TEMPLATE.md, E6, 1줄):

````text
# Work Order·ERRATA 템플릿 (계약 v1.2)
````

APPROVED_TEXT M2 (docs/tasks/TEMPLATE.md, E7, 1줄):

````text
WORK_ORDER_CONTRACT_VERSION: v1.2
````

APPROVED_TEXT M3 (docs/tasks/TEMPLATE.md, E8, 1줄):

````text
REQUIRED_CI_CHECKS: <예: ci-tests / pytest (Windows)>
````

APPROVED_TEXT M4 (docs/tasks/TEMPLATE.md, E9, 1줄):

````text
- PR_CI: v1.2에서 Gate Authorization이 PR_CREATE: YES와 저장소·base·head branch·head SHA·PR 제목·본문을 명시하면 `gh pr create` 1회(README §13). 아니면 compare URL·PR 본문 제공만
````

APPROVED_TEXT M5 (docs/tasks/TEMPLATE.md, E10, 1줄):

````text
- MERGE: v1.2에서 Gate Authorization이 MERGE_EXECUTE: YES와 PR 번호·head SHA를 명시하고 README §13 사전 검증을 모두 통과하면 `gh pr merge <N> -R <repo> --merge --match-head-commit <SHA>` 1회. 아니면 사용자 결정(GitHub UI, MERGE_METHOD)
````

APPROVED_TEXT C1 (CLAUDE.md, E11, 1줄):

````text
## Work Order (`docs/tasks/`, 계약 v1.2)
````

APPROVED_TEXT W1 (docs/agent_workflow.md, E12, 4줄):

````text
8. PR 생성(`gh pr create`)과 merge(`gh pr merge`)는 `github` ask 규칙의 `[B]`다. v1.2 Work Order에서 Gate Authorization이
   `PR_CREATE: YES` 또는 `MERGE_EXECUTE: YES`를 명시한 경우에만 실행하고, 승인 창에서 다시 승인받는다. merge는
   `--merge --match-head-commit <SHA>`로만 하며 `--admin`·`--auto`·`--squash`·`--rebase`·`--delete-branch`·`--force`를 쓰지
   않는다. 조건과 사전 검증은 `docs/tasks/README.md` §13을 따른다.
````

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA:
- AC1 구현 커밋 파일 집합 = ALLOWED_FILES(4개). PR 전체 파일 집합 = ALLOWED_FILES ∪ {docs/tasks/GOV-AUTOMATION-01/WORK_ORDER.md} (ACCEPTED ERRATA가 생기면 그 파일 포함).
- AC2 네 파일의 blob이 E14 정의와 바이트 단위로 같다(줄 수 175 / 184 / 67 / 142).
- AC3 `git diff -U0 CANONICAL_BASE_SHA`의 hunk가 E1–E12와 대응한다(hunk 수 4 / 4 / 1 / 1, 줄 변화 +26/−4, +5/−4, +1/−1, +4/−0). 그 밖의 diff 0.
- AC4 v1.1 규칙 보존: 구현 후 docs/tasks/README.md에 "Claude는 compare URL·PR 본문만 제공"과 "사용자가 GitHub UI에서 merge commit으로"가 각각 §3 표와 §13에 남아 있고, §13에 v1.1 비소급 적용 범위 문장이 있다.
- AC5 v1.2 실행 조건: §13에 `PR_CREATE: YES`, `MERGE_EXECUTE: YES`, head SHA 검증, PR 범위 검증, `REQUIRED_CI_CHECKS` SUCCESS, 추가 증거 수락, MERGEABLE, 원격 main 확인, guard ASK 승인, 금지 옵션 6개, POST_MERGE_AUDIT 필수가 모두 있다. TEMPLATE.md에 `REQUIRED_CI_CHECKS:` 필드가 있다.
- AC6 CLAUDE.md diff는 정확히 1줄 삭제·1줄 추가(54행)다.
- AC7 docs/agent_workflow.md diff에 삭제 줄이 0이다. 기존 guard 규칙 이름·tier 태그·필수 섹션 이름이 모두 그대로 있다.
- AC8 새 문구가 GATE_SEQUENCE를 바꾸거나, 새 gate를 만들거나, 사용자 승인 없는 실행·guard 변경·allow 규칙을 허용하지 않는다.
- AC9 PR CI `ci-tests / pytest (Windows)` 성공(INDEPENDENT). tests/test_skills.py와 tests/test_agent_guard.py가 실패·skip되지 않았다는 증거를 PR_CI에서 보고한다.

## TEST_GATES

TEST_GATES:
- 변경 파일 집합 = ALLOWED_FILES, PROTECTED diff 0, untracked 0
- `git diff --check` 깨끗함
- hunk 대조: `git diff -U0 <CANONICAL_BASE_SHA> -- <ALLOWED_FILES>`의 hunk 위치·내용이 E1–E12와 같고 hunk 수가 4 / 4 / 1 / 1이다
- 기대 결과 일치: 커밋된 WORK_ORDER.md의 APPROVED_TEXT로 base에서 독립 재구성한 blob = 각 파일의 blob(E14), 줄 수 175 / 184 / 67 / 142
- CLAUDE.md 1줄 변경 검증(AC6)
- v1.1 보존 검증(AC4)과 v1.2 조건 검증(AC5): 구현 결과에서 해당 문자열의 존재를 확인
- guard 규칙 이름 보존(AC7): agent_workflow.md 삭제 줄 0, base에 있던 백틱 규칙 이름이 모두 남아 있음
- 로컬 pytest는 요구하지 않는다(TARGET_WORKTREE에 `.venv`가 없고 이 task는 `.venv`를 만들지 않는다). 회귀·hygiene 확인은 PR CI `ci-tests / pytest (Windows)`로 한다(tests/test_skills.py, tests/test_agent_guard.py, tests/test_repo_hygiene.py 포함).
- guard가 거부하는 문자열을 담은 로컬 검사 명령은 실행하지 않는다. 거부되면 재시도·변형하지 않고 멈춘다.

## E2E_GATES

E2E_GATES:
- NOT_REQUIRED (문서 전용). 대체 확인: clean 구현 커밋에서 네 파일 blob이 E14와 같고, 커밋 파일 집합 = ALLOWED_FILES이며, 구현 커밋의 부모 = C1(또는 마지막 ACCEPTED ERRATA 커밋)이다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 커밋 SHA·parent·tree, Work Order sha256, 커밋 파일 집합, 네 파일 blob과 E14 일치, hunk 목록, merge parent·tree
- CLAUDE_REPORTED: Claude가 실행한 확인·계산, 재구성 비교, AC4·AC5·AC7 문자열 확인
- INDEPENDENT: PR CI 결과, GitHub 화면(사용자 확인)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, 원격 main ≠ 확정 CANONICAL_BASE_SHA, Work Order sha256 불일치
- BASE_BLOBS 불일치, 또는 E1–E12가 인용한 base 줄의 내용이 실제와 다름
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기와 base 상태 불일치
- 구현 결과가 E14와 다름, APPROVED_TEXT 변경 필요, NON_GOALS를 건드려야만 일관성이 맞는 경우
- guard deny, 권한 창(ASK) 거절
- CI 실패
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일
