# Work Order: GOV-AUTOMATION-02 — Work Order contract v1.3: Bundled Gate Authorization

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/GOV-AUTOMATION-02/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: GOV-AUTOMATION-02
TASK_ID: GOV-AUTOMATION-02
TITLE: Work Order contract v1.3: Bundled Gate Authorization
VERSION: 1.1
STATUS: ISSUED
CANONICAL_BASE_SHA: 04733d12e0bf0ae780853dc6e4cdcb71dd804344 (C1 직전 원격 main과 재대조)
CANONICAL_BASE_TREE: 8b123f9a96337701b494b46b4ff3852f628950bd (확인된 base Git 객체와 재대조)
BASE_BLOBS: CLAUDE.md 6efd3050098ac9f4c25d8018733855e7b2e93a3c (67 lines, 8839 bytes), docs/agent_workflow.md ecac3a4b6f6403d22e1d18336a7235f362fd5752 (175 lines, 16708 bytes), docs/tasks/README.md 6edbdcc120a4ada11d22c956d02968232140de2f (175 lines, 13658 bytes), docs/tasks/TEMPLATE.md 1d608d83ab6cb6072eff4716191fcbbd7180f943 (184 lines, 6631 bytes) (C1 직전 재검증, 다르면 STOP)
SOURCE_WORKTREE: C:/MoneyLab-auto-01
TARGET_BRANCH: docs/gov-automation-02
TARGET_WORKTREE: C:/MoneyLab-gov-automation-02
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests / pytest (Windows)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: GOV-AUTOMATION-02 <GATE> WO@<C1 commit>`)
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping
- 이 task는 계약 v1.2로 진행한다. 이 task가 도입하는 v1.3 BUNDLE_AUTHORIZATION을 이 task 자신에게 적용하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약을 따른다. 이 task는 ALLOWED_FILES에 DESIGN_CONTRACT의 승인 문구를 추가할 뿐 기존 줄을 삭제·수정하지 않는다. guard deny는 우회하지 않는다.

## GOAL

GOAL: 이 Work Order가 merge된 뒤 새로 발행되는 v1.3 Work Order에 한해, 사용자가 BUNDLE_AUTHORIZATION 하나로 IMPLEMENTATION → PRECOMMIT_AUDIT → COMMIT → CLEAN_COMMIT_E2E의 연속 부분 구간 또는 POST_MERGE_AUDIT → COMPLETE 구간을 진행할 수 있도록 계약 문서에 BGA-0~BGA-10을 추가한다. PUSH·PR_CI·MERGE·후퇴는 개별 승인을 유지한다. 효과는 채팅 Gate 승인 감소에 한정되며 settings·guard 승인 창은 바뀌지 않는다.

## BACKGROUND

BACKGROUND:
- 현재 gate당 승인 근거: CLAUDE.md:60, docs/tasks/README.md:54(§3), :63-70(§4), :112(§8), :120·124(§9), docs/tasks/TEMPLATE.md:42.
- commit·push·PR의 승인 창: .claude/settings.json ask `Bash(git commit *)`·`Bash(git push *)`·`Bash(gh pr *)`, guard ASK_RULES `git-commit`·`git-push`·`github`. 이 task는 이를 바꾸지 않는다.
- AUTO-01(main merge commit 04733d1)은 구현 8개 파일에 사용자 메시지 약 24건이 필요했다(CLAUDE_REPORTED, git으로 재현 불가).
- 선례: GOV-AUTOMATION-01은 계약을 v1.1→v1.2로 올리면서 자기 적용을 금지했다.

## ENVIRONMENT

ENVIRONMENT:
- C1 도구 실행 세션은 SOURCE_WORKTREE의 기존 Guard·Python 환경을 사용한다. TARGET_WORKTREE의 .venv는 C1 조건이 아니다.
- IMPLEMENTATION 진입 전 TARGET_WORKTREE 전용 .venv, Python 3.14, 고정 requirements-dev.txt와 editable moneylab 설치를 확인한다. sys.prefix와 moneylab.__file__이 대상 worktree를 가리켜야 한다. 기존 확인 버전은 3.14.8이다.
- 환경 준비는 별도 명시 승인 대상이다. .venv 생성, 패키지 설치, 빌드 의존성 다운로드를 포함할 수 있는 네트워크 범위를 승인문에 지정한다. C1 승인에 포함하지 않는다.
- 테스트는 대상 .venv/Scripts/python.exe를 사용한다. 도구 호출 실패를 피하려고 hook·settings를 변경하지 않는다.

## NON_GOALS

NON_GOALS:
- `.claude/**`, `.github/**`, `.gitignore`, `.gitattributes` 변경, 권한 규칙 변경
- 코드·테스트·설정·의존성 변경
- Evidence 저장·ledger·자동 재개, 전진 조건 평가기·테스트 약화 검사기·예산 카운터 구현, executor action 추가(AUTO-02 이후)
- PUSH·PR_CI·MERGE의 묶음 포함, 자동 후퇴
- 기존 Work Order·ERRATA 수정, ALLOWED_FILES 기존 줄의 삭제·수정, 소급 적용, 자기 적용
- GATE_SEQUENCE 변경, 새 gate 신설, Linux 지원

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: 두 하위 단계로 수행한다. (1) WORKTREE_CREATION_ONLY는 2026-11-08 사용자 승인에 따라 완료됐다. 당시 대상 branch·경로 없음과 기준선을 확인했다. (2) C1_CREATION_ONLY는 별도 사용자 승인 후 기존 TARGET_WORKTREE에서 수행한다. SOURCE_WORKTREE는 도구 실행 위치이며 모든 Git 쓰기는 TARGET_WORKTREE를 명시한다. 대상 branch가 TARGET_BRANCH이고 HEAD·tree가 CANONICAL_BASE_SHA·TREE와 같으며 tracked·index diff 0, untracked 0, docs/tasks/GOV-AUTOMATION-02/ 부재일 때만 진행한다. 사용자 승인에 포함된 git ls-remote --heads origin refs/heads/main 1회로 원격 main SHA를 확인하고 base 객체의 tree·BASE_BLOBS를 대조한다. 조회 실패나 불일치이면 STOP한다. worktree 생성과 fetch는 반복하지 않는다. 승인된 Work Order 문안의 UTF-8, BOM 없음, LF, 끝 줄바꿈 1개인 바이트를 메모리에서 확정하고 승인 SHA-256과 대조한다. Write 도구로 WORK_ORDER.md를 최초 1회 작성하고 해시·바이트를 확인한다. 해당 경로만 stage하고 staged blob 바이트가 승인 바이트와 같은지 확인한 뒤 C1 커밋 docs(task): add GOV-AUTOMATION-02 work order를 1회 만든다. C1 parent = CANONICAL_BASE_SHA, 변경 파일 = WORK_ORDER.md 한 개, commit blob 바이트 = 승인 바이트, clean을 확인하고 보고 후 STOP한다. 불일치 파일을 덮어쓰거나 자동 복구하지 않는다. C1 전 승인에는 WO@<C1> 대신 승인 문안 SHA-256과 기준선을 명시하고, 이후 gate는 실제 C1 SHA를 사용한다.
- IMPLEMENTATION: ALLOWED_FILES에 DESIGN_CONTRACT의 승인 문구를 지정 위치에 추가하고 TEST_GATES를 실행한다. 각 파일 편집의 승인 창(guard ASK·settings ask)은 사용자가 승인한 경우에만 진행한다.
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: `git add -- CLAUDE.md docs/agent_workflow.md docs/tasks/README.md docs/tasks/TEMPLATE.md`, 커밋 하나
- CLEAN_COMMIT_E2E: 전체 pytest, ACCEPTANCE_CRITERIA 확인(ignored 출력만)
- PUSH: TARGET_BRANCH 하나만 `git push -u origin docs/gov-automation-02`
- PR_CI: docs/tasks/README.md §13(v1.2). Gate Authorization이 PR_CREATE: YES와 저장소·base·head branch·head SHA·PR 제목·본문을 명시하면 `gh pr create` 1회. 아니면 compare URL·PR 본문 제공만
- MERGE: docs/tasks/README.md §13(v1.2). Gate Authorization이 MERGE_EXECUTE: YES와 PR 번호·head SHA를 명시하고 사전 검증을 모두 통과하면 `gh pr merge <N> -R <repo> --merge --match-head-commit <SHA>` 1회. 아니면 사용자 결정(GitHub UI, MERGE_METHOD)
- POST_MERGE_AUDIT: main ref만 fetch, 구조 감사
- COMPLETE: 최종 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위, ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- ALLOWED_FILES 기존 줄의 삭제·수정
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
- hooks·settings·.claude 변경 또는 guard 우회, guard deny된 명령의 변형 재시도
- 다른 branch·worktree·untracked·ignored·reference 산출물 정리

## ALLOWED_FILES

ALLOWED_FILES:
- M CLAUDE.md
- M docs/agent_workflow.md
- M docs/tasks/README.md
- M docs/tasks/TEMPLATE.md

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/GOV-AUTOMATION-02/** (C1에서 WORK_ORDER.md 최초 생성만 예외; 이후 불변)
- docs/tasks/** 중 docs/tasks/README.md와 docs/tasks/TEMPLATE.md를 제외한 전부
- docs/** 중 docs/agent_workflow.md, docs/tasks/README.md, docs/tasks/TEMPLATE.md를 제외한 전부
- .claude/**, .github/**, .gitignore, .gitattributes
- pyproject.toml, requirements.txt, requirements-dev.txt
- src/**, tests/**, configs/**, knowledge/**, data/**, examples/**
- README.md, ARCHITECTURE.md, LICENSE, .env.example

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅. C1의 WORK_ORDER.md 최초 생성은 README v1.2에 따른 별도 예외이며 ALLOWED_FILES에 속하지 않는다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 추가 전용: 네 파일 모두 기존 줄을 삭제·수정하지 않고 아래 승인 문구만 지정 위치에 추가한다(`git diff --numstat`의 삭제 수 0). 각 TEXT 블록은 코드 펜스 안의 내용만 그대로 넣는다.
- D2 docs/tasks/README.md: 파일 끝(§13 마지막 줄 다음)에 빈 줄 하나, `## 14. 계약 v1.3: Bundled Gate Authorization (BGA)`, 빈 줄 하나, TEXT-README 전문을 순서대로 추가한다.
- D3 docs/tasks/TEMPLATE.md: Work Order 템플릿 Metadata의 `REQUIRED_CI_CHECKS:` 줄(BASE 기준 33행) 다음에 TEXT-TEMPLATE-META를, Work Order 템플릿 GATE_TRANSITION_RULES 목록의 마지막 항목(BASE 기준 45행 `- no skipping except WORKSPACE_SETUP: NOT_REQUIRED tasks`) 다음에 TEXT-TEMPLATE-GTR을 추가한다.
- D4 CLAUDE.md: (a) 절대 규칙 7 줄(BASE 기준 26행) 다음에 TEXT-CLAUDE-R7을 추가한다. (b) "## Work Order" 절의 "- Gate Authorization:" 항목(BASE 기준 60행) 다음에 TEXT-CLAUDE-GA를 추가한다.
- D5 docs/agent_workflow.md: §3 항목 8의 마지막 줄(BASE 기준 47행) 다음에 TEXT-WORKFLOW를 항목 9로 추가한다. guard 규칙 이름·tier 태그·기존 항목은 바꾸지 않는다.
- D6 위 행 번호는 BASE_BLOBS 기준이며, WORKSPACE_SETUP에서 BASE_BLOBS가 확정된 경우에만 유효하다. 행 번호와 앵커 문자열이 다르면 STOP한다.

TEXT-README:
```
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
```

TEXT-TEMPLATE-META:
```
BUNDLE_ELIGIBLE: <NO | YES (v1.3만, docs/tasks/README.md §14)>
BUNDLE_MAX_RANGE: <NONE | IMPLEMENTATION..CLEAN_COMMIT_E2E의 연속 부분 구간 | POST_MERGE_AUDIT..COMPLETE>
```

TEXT-TEMPLATE-GTR:
```
- v1.3이고 BUNDLE_ELIGIBLE: YES이면 docs/tasks/README.md §14의 BUNDLE_AUTHORIZATION으로 BUNDLE_MAX_RANGE 안의 연속 구간을 진행할 수 있다. PUSH·PR_CI·MERGE·후퇴는 개별 승인이다.
```

TEXT-CLAUDE-R7:
```
   - v1.3 Work Order에서 사용자가 COMMIT을 범위에 명시한 `BUNDLE_AUTHORIZATION`(docs/tasks/README.md §14)은 그 묶음 안의 git commit 1회에 대한 "사용자 요청"이다. push는 포함하지 않는다. BGA는 settings·guard 승인 창을 대신하지 않는다.
```

TEXT-CLAUDE-GA:
```
- 예외: v1.3 Work Order에서는 `BUNDLE_AUTHORIZATION` 하나로 docs/tasks/README.md §14가 정한 연속 gate 구간을 진행할 수 있다. PUSH·PR_CI·MERGE·후퇴는 개별 승인이다. BGA는 settings·guard 승인 창을 대신하지 않는다.
```

TEXT-WORKFLOW:
```
9. v1.3 `BUNDLE_AUTHORIZATION`(docs/tasks/README.md §14) 안에서도 `[B]` 명령은 gate당 1회이고 승인 창에서 다시 승인받는다. BGA는 settings·guard 승인 창을 대신하지 않는다. 묶음 안에서 재실행할 수 있는 것은 `[A]` 명령뿐이다.
```

## TEST_GATES

TEST_GATES:
- IMPLEMENTATION에서 전체 pytest 1회, failed 0 / errors 0 (tests/test_skills.py, tests/test_agent_guard.py, tests/test_repo_hygiene.py 포함). 동일 gate에서 변경·실패·미해결 근거 없이 반복하지 않는다.
- ACCEPTANCE_CRITERIA AC1–AC13
- `git diff --check` 깨끗함, 변경 파일 집합 = ALLOWED_FILES, PROTECTED diff 0

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA (git·grep·pytest 및 읽기 전용 바이트·해시 확인):
- 평가 시점: 구현 커밋 전 AC1–AC3은 C1과 현재 작업 파일·index의 후보 변경을 비교한다. 구현 커밋이 생긴 뒤에는 명시된 commit 간 비교로 확정한다. 아직 존재하지 않는 커밋·PR·CI의 검사를 PASS로 보고하지 않는다.
- AC1 C1의 parent = CANONICAL_BASE_SHA, 변경 파일 = docs/tasks/GOV-AUTOMATION-02/WORK_ORDER.md 한 개다. `git diff --name-only <C1> <구현 커밋>` = {CLAUDE.md, docs/agent_workflow.md, docs/tasks/README.md, docs/tasks/TEMPLATE.md}. base→구현 커밋 전체 변경은 계약 파일과 위 네 파일의 합집합이다. Ce가 필요해지면 이 검사 범위도 ACCEPTED ERRATA로 명시한다.
- AC2 C1→구현 커밋의 PROTECTED_FILES diff가 비어 있다. C1 Work Order blob의 내용 SHA-256은 승인값과 같고 이후 불변이다. base→구현 커밋에서 C1의 계약 파일 최초 생성은 별도로 검사한다.
- AC3 `git diff --numstat <CANONICAL_BASE_SHA> <구현 커밋>`의 삭제 수가 네 파일 모두 0이다
- AC4 docs/tasks/README.md에서 n = 0..10 각각 `grep -c "^- BGA-<n> "` = 1
- AC5 docs/tasks/README.md의 `- BGA-1 ` 줄에 DESIGN_INVESTIGATION, CONTRACT_REVIEW, WORKSPACE_SETUP, ERRATA 고정(Ce), PUSH, PR_CI, MERGE, 후퇴가 모두 있다
- AC6 docs/tasks/README.md의 `- BGA-2 ` 줄에 BUNDLE_AUTHORIZATION, ERRATA, ENTRY_HEAD, ENTRY_TREE, BUDGET, EXPIRES_UTC, EXPECTED_ASK, CONTRACT_HASHES, ENTRY_CHANGES, IMPLEMENTATION_COMMIT이 모두 있고, docs/tasks/TEMPLATE.md에 `BUNDLE_ELIGIBLE:`와 `BUNDLE_MAX_RANGE:`가 있다
- AC7 고정 문자열 "BGA는 settings·guard 승인 창을 대신하지 않는다"가 docs/tasks/README.md, CLAUDE.md, docs/agent_workflow.md에 각각 1회 이상 있다
- AC8 고정 문자열 "BGA는 채팅으로 보내는 Gate 승인의 수만 줄인다"가 docs/tasks/README.md에 있다
- AC9 고정 문자열 "초기 실험값이며 검증된 안전 기준이 아니다"가 docs/tasks/README.md에 있다
- AC10 고정 문자열 "소급하지 않는다"와 "GOV-AUTOMATION-02 자신에는 적용하지 않는다"가 docs/tasks/README.md에 있다
- AC11 IMPLEMENTATION과 CLEAN_COMMIT_E2E 각각에서 전체 pytest failed 0 / errors 0 (CLAUDE_REPORTED). PR CI는 AC14에 따라 PR_CI에서만 판정한다.
- AC12 `git diff --check` 통과, 네 파일 모두 LF이고 파일 끝 줄바꿈이 있다
- AC13 이 Work Order의 `## Metadata` 절(다음 `## ` 제목 전까지)에 `WORK_ORDER_CONTRACT_VERSION: v1.2`가 있고 `BUNDLE_ELIGIBLE:`로 시작하는 줄이 없다
- AC14 PR_CI에서 승인된 정확한 PR head의 ci-tests / pytest (Windows) SUCCESS를 확인한다(INDEPENDENT). 이전 gate에서는 NOT_YET_APPLICABLE로 기록하며 성공으로 표시하지 않는다.

## E2E_GATES

E2E_GATES:
- clean 구현 커밋에서 전체 pytest 1회와 AC1–AC13을 확인한다. AC11의 IMPLEMENTATION 실행과 이 clean commit 실행은 구분한다. AC14는 PR_CI 전까지 NOT_YET_APPLICABLE이다.
- `git diff --name-only <CANONICAL_BASE_SHA> <구현 커밋> -- src tests`가 비어 있다(코드 동작 변경 없음)

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 커밋 SHA·tree, 네 파일의 blob 전후, `git diff --numstat`, 변경 파일 집합, merge parent·tree
- CLAUDE_REPORTED: pytest 결과, AC 확인 결과
- INDEPENDENT: PR CI(ci-tests / pytest (Windows)), 사용자 검토

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree·BASE_BLOBS 불일치, Work Order sha256 불일치, DESIGN_CONTRACT 앵커 문자열 불일치
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅, A/M 표기 불일치
- 기존 줄의 삭제·수정(numstat 삭제 수 > 0)
- guard deny, 편집·commit·push 승인 창 거절, 예상하지 못한 ASK
- 테스트 실패·에러, AC 불충족
- 계약 모순, 상위 규칙과 충돌, 예상하지 못한 untracked 파일
