# Work Order: GUARD-PROTECT-01 — 계약·사전등록 경로와 다른 worktree에 대한 guard 보호 확장

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/GUARD-PROTECT-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

IMPLEMENTATION은 TARGET_WORKTREE를 root로 하는 새 Claude Code session에서 진행한다. 그 session은 이전 대화의 맥락에 의존하지 않는다. 이 파일이 계약의 유일한 출처다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: GUARD-PROTECT-01
TASK_ID: GUARD-PROTECT-01
TITLE: 계약·사전등록 경로와 다른 worktree에 대한 guard 보호 확장
VERSION: 1.0
STATUS: ISSUED
POLICY_STATUS: APPROVED
CANONICAL_BASE_SHA: 8e8d2e54d130b9fe5b3661ee735c0d64cf114238
CANONICAL_BASE_TREE: 94de0bc391903a0d9d8396b03987ab01f95a0c8a
TARGET_BRANCH: chore/guard-protect-01
TARGET_WORKTREE: C:/MoneyLab-guard-protect-01
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: GitHub Actions workflow `ci-tests`, job `pytest`, runner `windows-latest`, 승인된 head SHA에서 SUCCESS. 실제 결과는 PR_CI에서 확인한다.
ENVIRONMENT: ISOLATED_VENV

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> ACTIVATION_CHECK -> COMPLETE

ISSUANCE_RECORD: CONTRACT_REVIEW_PASS = YES, BASE@8e8d2e54d130b9fe5b3661ee735c0d64cf114238

| Gate | 허용 | 금지 | 필수 증거 |
|---|---|---|---|
| WORKSPACE_SETUP | BASE@ 값이 CANONICAL_BASE_SHA와 같고 메시지에 `C1_TEXT_APPROVED: YES`, 저장소 밖 발행본 파일의 절대 경로, 발행본 SHA-256·줄 수·크기가 있을 때만 진행한다. 기존 session에서 `git ls-remote origin refs/heads/main`으로 base 확인, TARGET_BRANCH·TARGET_WORKTREE 부재 확인, `git worktree add -b chore/guard-protect-01 C:/MoneyLab-guard-protect-01 8e8d2e54d130b9fe5b3661ee735c0d64cf114238`, 복사 전 발행본 파일의 SHA-256·줄 수·크기가 메시지 값과 같음을 확인(다르면 즉시 STOP), `mkdir -p C:/MoneyLab-guard-protect-01/docs/tasks/GUARD-PROTECT-01`, 복사 직전 WORK_ORDER.md 대상 파일이 없음을 확인(있으면 즉시 STOP), `cp -n "<메시지의 절대 경로>" C:/MoneyLab-guard-protect-01/docs/tasks/GUARD-PROTECT-01/WORK_ORDER.md`로 WORK_ORDER.md 생성, 생성 직후 SHA-256·줄 수·크기 재확인과 `git hash-object`로 blob 정체성 확인, 그 파일만 stage, C1 커밋, 커밋 후 SHA-256과 `git hash-object`가 커밋 전과 같고 `git rev-parse HEAD:docs/tasks/GUARD-PROTECT-01/WORK_ORDER.md`와 같음을 확인 | 그 밖의 파일, push, `.venv` 생성, 패키지 설치, 지정된 복사 경로·명령 밖의 생성 방법, 기존 파일을 덮어쓰는 복사. Guard DENY 또는 권한 거절 시 STOP하며 다른 도구나 대체 명령을 이용한 우회·재시도를 금지한다 | C1 SHA·parent·tree, sha256과 `git hash-object`(커밋 전후 동일), 검토된 발행 문구와의 동일성 확인, 파일 1개, clean |
| IMPLEMENTATION | 새 session에서 S0·S0a·S1 후 ALLOWED_FILES 수정, TEST_GATES | 커밋, 범위 밖 수정 | S0·S0a·S1, 테스트, PENDING_REGISTER와 BEFORE_DIAGNOSIS, 변경 파일, PROTECTED diff 0 |
| PRECOMMIT_AUDIT | 읽기·감사 | 변경 | diff --check, pending 0건, INTENDED_DECISION_CHANGES 대조 |
| COMMIT | ALLOWED_FILES 경로 명시 stage, 커밋 1개 | amend | SHA·parent·tree, 파일 집합(⊆ ALLOWED_FILES, 필수 변경 3개 포함) |
| CLEAN_COMMIT_E2E | clean 커밋에서 E2E_GATES | 추적 파일 변경 | 테스트 결과 |
| PUSH | `git push -u origin chore/guard-protect-01` | force | 원격 head, main 불변 |
| PR_CI | Gate Authorization의 PR_CREATE: YES일 때 `gh pr create` 1회, CI 확인 | merge, CI 재실행 | REQUIRED_CI_CHECKS 결과 |
| MERGE | MERGE_EXECUTE: YES와 README §13 통과 시 `gh pr merge <N> -R <repo> --merge --match-head-commit <SHA>` 1회 | --admin, --auto, --squash, --rebase, --delete-branch, --force | 사전 검증 1~7 |
| POST_MERGE_AUDIT | main ref만 fetch, 구조 감사 | --all, --prune, 정리 | parent, tree, first-parent, merge-tree, branch·worktree 보존 |
| ACTIVATION_CHECK | D10 절차 | 파일 변경, 보호 파일 쓰기 시도, 재시도 | 세 부문 결과 |
| COMPLETE | 최종 보고 | 재해석 | COMPLETION_CRITERIA |

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization.
  - WORKSPACE_SETUP: `GATE_AUTHORIZATION: GUARD-PROTECT-01 WORKSPACE_SETUP BASE@8e8d2e54d130b9fe5b3661ee735c0d64cf114238`. 이 시점에는 C1이 없으므로 WO@를 쓰지 않는다.
  - 같은 메시지에 `C1_TEXT_APPROVED: YES`, 사용자가 승인한 저장소 밖 발행본 파일의 절대 경로, 발행본 SHA-256·줄 수·크기를 포함한다. 그 경로와 SHA-256으로 고정된 파일 내용을 승인된 C1 문구로 본다.
  - IMPLEMENTATION 이후: `GATE_AUTHORIZATION: GUARD-PROTECT-01 <GATE> WO@<C1 SHA>`.
  - BASE@ 승인은 WORKSPACE_SETUP 한 gate에만 유효하며 다음 gate의 승인이 아니다.
  - BASE@ 형식이 CLAUDE.md의 상위 규칙에 위배되면 STOP하고 사용자에게 보고한다. 상위 규칙을 수정하거나 우회하지 않는다.
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping
- 이전 gate의 승인이나 이 파일은 다음 gate의 승인이 아니다.
- `ACTIVATION_CHECK_RESUME`은 Gate Authorization이 아니다. ACTIVATION_CHECK 안의 지정 단계 하나에만 유효하며 다음 gate의 승인이 아니다.
- 결과가 NO인 gate 뒤의 진행 규칙은 없다.

## PRIORITY

1. safety / system / tool restrictions
2. repository absolute rules: CLAUDE.md, .claude guard/hook/settings, docs/agent_workflow.md
3. frozen / preregistered contracts
4. 이 Work Order와 ACCEPTED ERRATA
5. implementation judgment

충돌하면 상위 규칙을 따르고 STOP한다. 이 task는 guard를 고치지만, 고치는 동안에도 실행 중인 guard의 판정을 따른다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙을 참조한다. 복제하지 않고 바꾸지 않는다.
CHANGE_BASIS: guard·settings 변경의 근거는 docs/agent_workflow.md 6절의 사용자 정책 결정이다. 이 Work Order는 그 실행 범위만 정한다.

## GOAL

GOAL: 계약 파일과 사전등록 문서를 guard로 보호하고, 파일 도구에 한해 같은 저장소의 다른 worktree에 같은 경로 판정을 적용하며, 기존 보호 판정과 규칙명을 약화하거나 바꾸지 않는다. 다른 worktree의 Bash 명령은 문자열 규칙으로만 판정한다. guard가 sandbox가 아니라는 한계는 유지하고 GUARD_PROTECTION_COMPLETE는 NO로 둔다.

## BACKGROUND

BACKGROUND:
- base guard의 경로 판정에 docs/tasks/**가 없고, 일반 파일 쓰기는 세션 루트 안에서 PASS다.
- 세션 루트 밖 쓰기는 settings·hooks, locked, 비밀 파일 외 PASS다.
- 해시 고정 테스트는 configs/research_v04.toml, docs/research_v04_preregistration.md, docs/research_v05_preregistration_draft.md만 다룬다.
- 선례: docs/tasks/GUARD-GH-01/WORK_ORDER.md
- BT4-VALID-01 구현은 이 task와 별도 결정 전까지 차단 상태다.

## PRECONDITIONS

PRECONDITIONS:
- 원격 main = CANONICAL_BASE_SHA, tree 일치
- TARGET_BRANCH(로컬)와 TARGET_WORKTREE 부재
- BASE_FILE_IDENTITY: `git hash-object`와 base blob으로 정체성을 확인한다. checkout 줄바꿈 때문에 sha256 단독 비교를 쓰지 않는다.
  - .claude/hooks/guard.py: aa2f6045ac21464cc0beb86c3c3f20fd4fb37751
  - .claude/settings.json: a863ba0a680bf961b13f1f099e468721d918d0ac
  - tests/test_agent_guard.py: b94fabcda71c0b1c088017e5830b8a49b54f9316
  - docs/agent_workflow.md: dc026dc7521bc6ba95280bfa86e72020ae384aeb

CONTRACT_REVIEW_ACCEPTANCE (BASE 파일 목록 대조 결과):
- configs/research_v04.toml, docs/research_v04_preregistration.md: 파일 도구 DENY frozen 유지. Bash 변경 DENY protected-path 유지.
- docs/research_v05_preregistration_draft.md: 파일 도구 ASK protected-edit 유지. Bash 변경은 DENY protected-path로 변경.
- docs/research_v06_preregistration_draft.md: 파일 도구 ASK prereg-protected로 변경. Bash 변경은 DENY protected-path로 변경.
- docs/research_bt4_futility_diag_preregistration.md, configs/bt4_futility_diag.toml: 파일 도구 DENY prereg-protected로 변경. Bash 변경은 DENY protected-path로 변경.
- configs/backtest_costs.toml: guard 판정 PASS 유지. Work Order와 Gate의 변경 제한은 별도로 적용한다.
- 패턴에 걸리지 않음을 확인: docs/research_bt4_01_evidence_review.md, docs/research-intake/**, docs/bt4_futility_diag_report.md, docs/bt4_design_01.md

ENVIRONMENT_DECISION:
- ISOLATED_VENV: 사용자가 Claude Code 밖에서 TARGET_WORKTREE에 전용 ignored `.venv`를 만든다. Python 3.14.8, 고정 requirements-dev.txt, `pip install -e . --no-deps`.
- 실제 생성·설치는 C1 뒤 사용자의 별도 승인과 조치로 수행한다. 네트워크 사용은 그 조치에 한정되며 에이전트 범위가 아니다.
- 에이전트는 패키지를 설치·업그레이드하지 않고 `.venv`를 만들지 않는다. junction을 만들지 않는다.

ENVIRONMENT_ACCEPTANCE:
- 사용자 조치 후 새 session 전: `.venv/Scripts/python.exe --version` = 3.14.8, `.venv`가 git-ignored이고 `git status`에 나타나지 않음.
- 새 session S0: session root = TARGET_WORKTREE, sys.prefix = TARGET_WORKTREE/.venv, moneylab.__file__이 TARGET_WORKTREE/src 아래.
- 호출이 차단 없이 실행되면 hook 실행 경로 정상의 필요 조건으로만 기록한다. 실제 판정 관측은 ACTIVATION_HOOK_OBSERVATION에서 한다.
- 전 도구가 막히면 STOP하고 사용자가 환경을 확인한다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: Gate 표 범위
- IMPLEMENTATION: IMPLEMENTATION_SAFETY_CONDITIONS를 지키며 ALLOWED_FILES만 수정, TEST_GATES 실행
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, 커밋 하나
- CLEAN_COMMIT_E2E: E2E_GATES, ignored 출력만
- PUSH: TARGET_BRANCH 하나만
- PR_CI: Gate Authorization이 PR_CREATE: YES와 저장소·base·head branch·head SHA·PR 제목·본문을 명시하면 `gh pr create` 1회(README §13). 아니면 compare URL·PR 본문 제공만
- MERGE: Gate Authorization이 MERGE_EXECUTE: YES와 PR 번호·head SHA를 명시하고 README §13 사전 검증을 모두 통과하면 merge 1회
- POST_MERGE_AUDIT: main ref만 fetch, 구조 감사
- ACTIVATION_CHECK: D10 절차
- COMPLETE: 최종 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, Work Order·ERRATA 수정
- `git add .`, `git add -A`, `git add -u`, `git commit -a`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull
- `git stash list` 호출은 D10의 ask 관측을 위해 1회 시도만 허용하며 실행을 허용하지 않는다. 실행되면 STOP이다. 금지 목록의 다른 항목에는 예외가 없다.
- ALLOWED_FILES 밖 `.claude` 변경, guard 우회, Edit·Write 외 방법으로 guard·settings 변경, hook·guard 비활성화, `disableAllHooks` 설정
- 경로 숨기기, patch·스크립트 경유 쓰기, 알리지 않은 write route
- 기존 worktree·branch·untracked·ignored·reference 산출물 정리, 다른 worktree 변경
- 패키지 설치, 인터프리터 설정 변경, 공유 `.venv`나 junction 사용
- S0의 지정 명령 외 인라인 인터프리터, 임시 스크립트
- 비밀 파일 접근, 키·주문 기능
- 실데이터, 외부 시장 API, DIAG 결과 열람, BT4-VALID-01 변경·재개
- 기존 테스트 사례 삭제·기대값 변경
- 실제 보호 파일에 대한 ACTIVATION_CHECK 쓰기 시도
- IMPLEMENTATION_SAFETY_CONDITIONS 밖의 복구 시도

## C1_CREATION_ONLY

C1_CREATION_ONLY:
- A docs/tasks/GUARD-PROTECT-01/WORK_ORDER.md
  - WORKSPACE_SETUP에서 승인된 문구로 1회만 생성하고 C1으로 커밋한다.

CE_CREATION_ONLY:
- A docs/tasks/GUARD-PROTECT-01/ERRATA-<NNN>.md
  - 사용자가 수락한 ERRATA만, 그 ERRATA에 의존하는 gate 전에 1회 생성하고 Ce로 커밋한다.

위 파일은 IMPLEMENTATION과 COMMIT의 변경 대상이 아니다. 생성 커밋 뒤에는 PROTECTED다.

## ALLOWED_FILES

ALLOWED_FILES:
- M .claude/hooks/guard.py
- M .claude/settings.json
- M tests/test_agent_guard.py
- M docs/agent_workflow.md

이 네 파일만 IMPLEMENTATION과 COMMIT의 변경 대상이다. 목록 밖의 파일이 필요하면 STOP하고 사용자가 결정한다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/GUARD-PROTECT-01/**
- docs/tasks/**, docs/tasks/README.md, docs/tasks/TEMPLATE.md
- .claude/** 중 ALLOWED_FILES에 명시된 두 파일을 제외한 전부
- tests/** 중 ALLOWED_FILES에 명시된 한 파일을 제외한 전부, tests/ 아래 새 파일
- docs/** 중 ALLOWED_FILES에 명시된 한 파일을 제외한 전부
- CLAUDE.md, AGENTS.md, .agents/**, README.md, .github/**, .gitignore, .gitattributes
- src/**, configs/**, knowledge/**
- pyproject.toml, requirements*.txt
- data/**, 모든 locked 파일, 비밀 파일

INVARIANT:
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가)
- C1_CREATION_ONLY, CE_CREATION_ONLY는 ALLOWED_FILES에 속하지 않는다.
- 이 두 목록의 생성은 지정 gate의 최초 생성만 허용하며 PROTECTED 지정을 해제하지 않는다. 생성 커밋 뒤의 수정은 어떤 gate에서도 허용하지 않는다.
- PRECOMMIT_AUDIT는 구현 커밋 파일 집합 ⊆ ALLOWED_FILES를 확인한다. PR 전체는 ALLOWED_FILES ∪ docs/tasks/GUARD-PROTECT-01/**이다.

GUARD_NOTE: Guard 판정은 수정 승인이 아니다. PROTECTED_FILES는 Guard가 PASS로 판정해도 수정할 수 없다. PROTECTED diff를 각 gate에서 git으로 확인한다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:

- D1 계약 파일 (파일 도구, 규칙명 task-contract)
  - `docs/tasks/<id>/WORK_ORDER.md`, `docs/tasks/<id>/ERRATA-*.md`: 작업 트리에 있으면 DENY, 없으면 ASK.
  - 그 밖의 `docs/tasks/**`: ASK.
  - guard는 "승인됨"을 판단하지 않는다. 파일 존재를 근사 기준으로 쓰며 판정은 worktree별이다. 승인은 Gate Authorization과 권한 창이 담당한다.
  - 커밋 전 잘못 쓴 초안은 에이전트가 고치지 않는다. 사용자가 처리한다.
  - 번호 순서와 STATUS는 guard 검사 대상이 아니다. README 5절 절차로 유지한다.
  - Ce는 Write 도구로 만들고 후보와 `git hash-object`·sha256을 대조한다. 다르면 STOP.

- D2 Bash 보호 (규칙명 protected-path)
  - 보호 경로 텍스트에 기존 계약 파일 패턴, D3의 모든 파일과 패턴(docs/research_v05_preregistration_draft.md 포함), D6 파일, .claude/skills를 추가한다.
  - 변경 동사 또는 해당 경로로의 redirect가 함께 있으면 DENY.
  - cat, grep, sha256sum, git show, git diff, `git add -- <path>`, pytest 실행은 현재 판정을 유지한다.
  - sed는 읽기 목적이어도 DENY다. 이는 받아들인 기존 동작이다.
  - 이 규칙은 명령 문자열만 판정한다. 세션 루트와 다른 worktree를 구분하지 않으며 D4의 판별을 쓰지 않는다.
  - 다른 worktree를 대상으로 한 Bash 명령도 이 문자열 규칙으로만 판정한다. 다른 worktree에 대한 Bash 동등 보호를 보장한다고 주장하지 않는다.
  - 텍스트 매칭 한계는 유지된다. 범위는 COMPLETION_CRITERIA의 KNOWN_LIMITATION을 따른다.
  - 절대 경로 판정은 기존 명령 정규화와 문자열 검색 방식을 따른다. 새 탐지 알고리즘을 추가하지 않는다.
  - 문자열 규칙은 저장소를 구분하지 않는다. 다른 저장소의 같은 경로 문자열도 같은 판정을 받을 수 있다. 이 동작은 받아들이며 저장소 판별로 주장하지 않는다.
  - guard의 명령 판정 함수는 Bash와 PowerShell 명령을 같은 문자열 규칙으로 처리한다. 다만 gh 게시 본문 분리는 Bash에만 적용한다.
  - 이 task는 PowerShell 도구의 실제 hook 적용을 직접 관측하지 않는다. PowerShell에 대한 실제 보호를 보장한다고 주장하지 않는다.
  - INTENDED_DECISION_CHANGES의 TOOL 표기 Bash는 PowerShell의 실제 보호를 뜻하지 않는다.

- D3 사전등록
  - 패턴의 `*`는 경로 구분자를 넘지 않는다.
  - 기존 파일 도구 판정과 규칙명은 바꾸지 않는다:
    - configs/research_v04.toml, docs/research_v04_preregistration.md: 존재와 무관하게 DENY frozen
    - configs/research_v05.toml, docs/research_v05_preregistration.md: 있으면 DENY frozen, 없으면 ASK protected-edit
    - docs/research_v05_preregistration_draft.md: ASK protected-edit
  - 위 파일을 제외한 새 보호 대상의 규칙명은 prereg-protected다:
    - `docs/research_*_preregistration.md`, `configs/research_*.toml`, `configs/bt4_*.toml`: 있으면 DENY, 없으면 ASK
    - `docs/research_*_preregistration_draft.md`: ASK
  - configs/backtest_costs.toml은 이 규칙의 대상이 아니다.

- D4 다른 worktree (파일 도구 전용, 동작 계약, 판별 오류 규칙명 worktree-detect)
  - 이 조항의 판별과 상대 경로 판정은 파일 도구(Write, Edit, MultiEdit, NotebookEdit)에만 적용한다. Bash 명령에는 적용하지 않는다.
  - 같은 Git 저장소의 다른 worktree로 판별되면 그 worktree 기준 상대 경로에 D1, D3, D6와 기존 경로 판정을 적용한다.
  - 저장소에 속하지 않는 경로와 다른 저장소 경로는 현재 판정을 유지한다.
  - 판별 오류는 PASS가 아니다. 보호 이름 패턴이면 DENY, 그 외 ASK다.
  - 기존 locked, 비밀 파일, settings·hooks DENY가 먼저 적용된다.
  - 단순 접두사 비교만으로 판별하지 않는다. 실제 경로 해석을 쓴다.
  - hook 8초 제한 안에서 끝나야 한다.
  - 알고리즘은 이 파일에서 고정하지 않는다. 충족할 수 없으면 STOP한다.

- D5 Git 명령
  - `git commit --amend`: DENY (규칙명 git).
  - `git checkout <ref> -- <path>`, `git worktree remove|move|prune`, `git branch -f`, `git update-ref`, `git symbolic-ref`: ASK (규칙명 git-history).
  - `git update-ref -d`의 DENY, `git checkout -- <path>`의 ASK, `git worktree add`, `git switch -c`, `git fetch`의 현재 판정을 유지한다.
  - 이 ASK는 Work Order 금지를 해제하지 않는다.

- D6 자기 보호 (규칙명 protected-edit)
  - tests/test_agent_guard.py, tests/test_skills.py, tests/test_repo_hygiene.py, docs/agent_workflow.md: 파일 도구 ASK.
  - .claude/skills/**의 Bash 변경: D2에 따라 DENY.

- D7 Fail-closed
  - 기존 예외 차단을 유지한다. 신규 분기의 예외도 차단으로 끝난다.
  - settings의 hook 연결·래퍼 형식은 바꾸지 않는다.

- D8 권한 규칙
  - `.claude/settings.json`에 `docs/tasks/**`와 사전등록 관련 Edit 규칙을 추가할 수 있다.
  - `Bash(...)` 규칙 추가는 tests/test_skills.py의 tier 판정을 바꾸지 않아야 한다.
  - Edit 규칙의 도구별 적용은 NOT_VERIFIED다. guard 판정을 대체하지 않는다.

- D9 문서와 규칙명
  - 새 규칙명은 task-contract, prereg-protected, worktree-detect다. `Decision(DENY|ASK, "<name>")` 형식으로 쓰고 docs/agent_workflow.md 4절에 추가한다.
  - 기존 판정의 규칙명 변경은 회귀다.
  - 존재하지 않는 Skill 참조 수정은 범위 밖이다.

- D10 ACTIVATION_CHECK
  - 전제: POST_MERGE_AUDIT PASS, 별도 Gate Authorization, session root = merge된 guard를 가진 worktree.
  - 실제 보호 파일에 대한 Edit·Write 시도, 내용을 바꿀 수 있는 호출, 차단 뒤 재시도를 금지한다.
  - 세 부문을 차례로 수행한다. 앞 부문이 실패하면 멈춘다.
  - ACTIVATION_INTEGRITY:
    - session root의 guard.py, settings.json `git hash-object` = merge commit의 blob.
    - session root가 기대 경로임을 확인한다.
    - ACTIVATION_CHECK 시작 시 `git status --porcelain` 출력을 기록한다.
    - HOOK-3 보고 뒤 FINAL_STATUS 단계에서 같은 명령을 1회 실행해 시작 시 출력과 같음을 확인한다.
  - ACTIVATION_UNIT:
    - 같은 worktree에서 tests/test_agent_guard.py, tests/test_skills.py, tests/test_repo_hygiene.py 실행, failed 0 / errors 0.
    - INTENDED_DECISION_CHANGES의 판정은 이 부문으로 검증한다.
  - ACTIVATION_HOOK_OBSERVATION (실제 Claude Code hook, 지정 호출 3개, 아래 순서, 호출당 최대 1회):
    - HOOK-1 deny, Bash: `echo disableAllHooks`. 기대: MoneyLab guard [hooks].
    - HOOK-2 ask, Bash: `git stash list`. 기대: MoneyLab guard [git-history] 승인 요청. 승인 요청 관측만 허용한다. 사용자는 실제 실행을 승인하지 않는다. 실행되면 STOP이고 관측 실패다.
    - HOOK-3 deny, Read: 존재하지 않는 `data/processed/__activation_probe__/locked/none.txt`. 기대: MoneyLab guard [locked].
    - 위 호출은 guard가 없어도 파일을 바꾸지 않는다. 판정은 메시지의 규칙 이름으로 확인한다.
    - HOOK-2의 규칙 이름이 Claude에게 보이지 않으면 사용자가 승인 창 문구 원문을 제공한다. 사용자가 실제 관측한 원문만 증거로 인정하며 Claude는 규칙명이나 메시지를 추정하지 않는다. 둘 다 없으면 미관측이다.
    - 기대한 DENY 또는 ASK 거절을 관측하면 즉시 STOP하고 사용자에게 보고한다. 이 관측은 STOP의 예외가 아니다.
    - 다음 단계(HOOK-2, HOOK-3, FINAL_STATUS)는 같은 session의 같은 ACTIVATION_CHECK Gate 안에서 사용자가 재개를 승인한 경우에만 진행한다.
    - 재개 승인 형식: `ACTIVATION_CHECK_RESUME: GUARD-PROTECT-01 <HOOK-2|HOOK-3|FINAL_STATUS> WO@<C1 SHA>`. 승인 1건은 지정된 단계 하나에만 유효하다.
    - 재개 승인은 이전 DENY나 권한 거절을 무효화하지 않는다. 차단된 명령을 다시 실행하거나 변형해서 시도하지 않는다.
    - 기대한 판정과 규칙명이 관측되지 않거나, `git stash` 명령이 실제로 실행되거나, 보호 파일이 변경되면 STOP하고 HOOK_OBSERVATION_PASS = NO로 보고한다. 재개 승인을 받더라도 다음 단계로 넘어가지 않으며 ROLLBACK_AND_RECOVERY의 조사만 한다.
    - 이 절차는 ACTIVATION_CHECK에만 적용한다. 다른 Gate의 STOP 규칙과 기존 보호 정책을 바꾸지 않는다.
  - HOOK_OBSERVATION_PASS는 HOOK-1, HOOK-2, HOOK-3이 각각 기대한 판정과 규칙명으로 관측된 경우에만 YES다.
  - INTEGRITY_PASS는 FINAL_STATUS까지 일치한 경우에만 YES다.
  - ACTIVATION_CHECK_PASS는 세 부문이 모두 PASS일 때만 YES다. INTEGRITY_PASS, UNIT_PASS, HOOK_OBSERVATION_PASS를 따로 보고한다.
  - 범위: 그 session과 worktree만.
  - KNOWN_LIMITATION: Write·Edit 경로의 실제 hook 동작은 직접 관측하지 않는다. blob 일치, 단위 테스트, matcher 설정에서 INFERRED로 보고한다.

## INTENDED_DECISION_CHANGES

아래 표 밖의 판정 또는 규칙명 변경은 회귀다. BEFORE의 (test)는 기존 테스트로 고정된 값, (code)는 코드 해석이다. 행의 정책은 사용자 승인됨, 구현 결과는 미검증이다.

이 절의 PASS, ASK, DENY는 Guard 도구 판정만 뜻한다. KEEP의 PASS와 ASK의 승인은 Work Order의 파일 수정 승인이 아니다. PROTECTED_FILES는 Guard 판정과 관계없이 이 task에서 수정할 수 없다. 변경 가능 여부는 ALLOWED_FILES와 승인된 Gate로 판단한다.

의도된 변경:

| RULE_ID | TOOL | TARGET | BEFORE | AFTER | REASON | TEST_CASE |
|---|---|---|---|---|---|---|
| IDC-01 | Write·Edit | 기존 WORK_ORDER.md | PASS (code) | DENY task-contract | 불변성 | T1 |
| IDC-02 | Write | 신규 WORK_ORDER.md | PASS (code) | ASK task-contract | C1 생성 | T1 |
| IDC-03 | Write·Edit | 기존 ERRATA-*.md | PASS (code) | DENY task-contract | 불변성 | T1 |
| IDC-04 | Write | 신규 ERRATA-*.md | PASS (code) | ASK task-contract | Ce 생성 | T1 |
| IDC-05 | Write·Edit | docs/tasks/README.md, TEMPLATE.md, 그 밖의 docs/tasks/** | PASS (code) | ASK task-contract | 계약 규칙 파일 | T1 |
| IDC-06 | Bash | 계약 파일 + 변경 동사·redirect | 일반 변경 동사 PASS (code) / 재귀 삭제 ASK recursive-delete (code) / git rm ASK git-history (code) | DENY protected-path | 우회 차단 | T2 |
| IDC-07 | Write·Edit | docs/research_bt4_futility_diag_preregistration.md, configs/bt4_futility_diag.toml | PASS (code) | DENY prereg-protected | 사전등록 보호 | T3 |
| IDC-08 | Write | 신규 사전등록·config (D3 새 보호 대상) | PASS (code) | ASK prereg-protected | 사전등록 생성 | T3 |
| IDC-09 | Write·Edit | docs/research_v06_preregistration_draft.md | PASS (code) | ASK prereg-protected | 초안 변경 통제 | T3 |
| IDC-10 | Bash | D3 패턴과 v05 초안 + 변경 동사. 이미 DENY protected-path인 configs/research_v04.toml, docs/research_v04_preregistration.md, configs/research_v05.toml, docs/research_v05_preregistration.md는 제외한다. | 일반 변경 동사 PASS (code) / 재귀 삭제 ASK recursive-delete (code) / git rm ASK git-history (code) | DENY protected-path | 우회 차단 | T3 |
| IDC-11 | Write·Edit | tests/test_agent_guard.py, test_skills.py, test_repo_hygiene.py | PASS (code) | ASK protected-edit | 자기 보호 | T6 |
| IDC-12 | Write·Edit | docs/agent_workflow.md | PASS (code) | ASK protected-edit | 자기 보호 | T6 |
| IDC-13 | Bash | D6 파일, .claude/skills + 변경 동사 | 일반 변경 동사 PASS (code) / 재귀 삭제 ASK recursive-delete (code) / git rm ASK git-history (code) | DENY protected-path | 자기 보호 | T6 |
| IDC-14 | Bash | git commit --amend | ASK git-commit (code) | DENY git | 금지 명령 | T5 |
| IDC-15 | Bash | git checkout <ref> -- <path> | PASS (code) | ASK git-history | 경로 복원 | T5 |
| IDC-16 | Bash | git worktree remove·move·prune | PASS (code) | ASK git-history | 보존 규칙 | T5 |
| IDC-17 | Bash | git branch -f | PASS (code) | ASK git-history | ref 변경 | T5 |
| IDC-18 | Bash | git update-ref (-d 제외) | PASS (code) | ASK git-history | ref 변경 | T5 |
| IDC-19 | Bash | git symbolic-ref | PASS (code) | ASK git-history | ref 변경 | T5 |
| IDC-20 | Write·Edit | 다른 worktree의 v04 파일, data/raw | PASS (code) | DENY frozen, raw-or-git | 동등 보호 | T4 |
| IDC-21 | Write·Edit | 다른 worktree의 계약 파일, 사전등록 | PASS (code) | D1·D3 판정과 규칙명 | 동등 보호 | T4 |
| IDC-22 | Write·Edit | 다른 worktree의 .claude/skills, CLAUDE.md, D6 파일, 기타 ASK 대상 | PASS (code) | ASK protected-edit | 동등 보호 | T4 |
| IDC-23 | Write·Edit | 판별 오류 + 보호 이름 패턴 | PASS (code) | DENY worktree-detect | 안전 기본값 | T4 |
| IDC-24 | Write·Edit | 판별 오류 + 그 외 | PASS (code) | ASK worktree-detect | 안전 기본값 | T4 |

IDC-06, IDC-10, IDC-13의 사례는 명령 종류별로 따로 등록한다. BEFORE_DIAGNOSIS는 그 사례의 명령 종류에 해당하는 BEFORE와 사례별로 대조한다.
IDC-10에서 제외한 네 파일은 D2의 보호 대상에 남는다. 이 파일들의 Bash 변경 판정 DENY protected-path와 규칙명은 기존 판정이며 변경하지 않는다.
IDC-06, IDC-10, IDC-13의 대상에는 명령 문자열에 다른 worktree 절대 경로가 포함된 사례도 들어간다. 판정은 문자열 규칙으로만 한다. IDC-20~IDC-24는 파일 도구 전용이다.

유지 (판정과 규칙명 모두):

| RULE_ID | TOOL | TARGET | 판정 | 근거 | TEST_CASE |
|---|---|---|---|---|---|
| KEEP-01 | Write·Edit | 루트 안 v04 두 파일 | DENY frozen | test, 규칙명 code | test_file_tools, T8 |
| KEEP-02 | Write | v05 파일 없음 / 있음 | ASK protected-edit / DENY frozen | test, 규칙명 code | test_frozen_v05_files_only_once_they_exist, T8 |
| KEEP-03 | Edit | v05 초안 | ASK protected-edit | test, 규칙명 code | test_file_tools, T8 |
| KEEP-04 | Write·Edit | guard.py, settings.json (루트 안) | ASK protected-edit | test, 규칙명 code | test_file_tools, T8 |
| KEEP-05 | Write·Edit | 루트 밖 settings·hooks | DENY claude-settings | test, 규칙명 code | test_settings_outside_project_are_denied, T8 |
| KEEP-06 | Bash | guard·settings + 변경 동사, sed -n | DENY protected-path | test | test_behaviour_outside_gh_is_unchanged |
| KEEP-07 | Bash | cat, grep guard 파일 | PASS | test | test_behaviour_outside_gh_is_unchanged |
| KEEP-08 | Read·Write | locked / 비밀 파일 | DENY locked / env | test, 규칙명 code | test_file_tools, T8 |
| KEEP-09 | Write·Edit | README.md, src/moneylab/cli.py | PASS | test | test_file_tools |
| KEEP-10 | Bash | git add docs/x.md, git switch -c, git fetch, git status, git diff, git log, git show | PASS | test | PASS_COMMANDS |
| KEEP-11 | Bash | git add -- docs/agent_workflow.md | PASS | test | test_valid_skill_passes |
| KEEP-12 | Bash | sha256sum frozen, cat data/raw, pytest | PASS | test | PASS_COMMANDS |
| KEEP-13 | Bash | git checkout -- <path>, git restore, git reset HEAD~1 / git commit -m | ASK git-history / ASK git-commit | test, 규칙명 code | ASK_COMMANDS, T8 |
| KEEP-14 | Bash | git update-ref -d | DENY git | code | T5 |
| KEEP-15 | Bash | git worktree add | PASS | code | T5 |
| KEEP-16 | Write·Edit | 저장소 밖 파일, 다른 저장소 파일 | PASS | code | T4 |
| KEEP-17 | Bash | incident Skill의 [A] 명령 | PASS | test | test_incident_skill_is_read_only |
| KEEP-18 | 전체 | 입력 오류 / 내부 오류, hook 래퍼 | DENY malformed / exit 2 | test | 기존 fail-closed 테스트 |
| KEEP-19 | Bash | D2·D6 밖의 `.claude` 경로, CLAUDE.md 등 Bash 쓰기 | PASS | code | T2 |
| KEEP-20 | Bash | echo disableAllHooks | DENY hooks | test, 규칙명 code | DENY_COMMANDS, T8 |
| KEEP-21 | Bash | git stash list | ASK git-history | code, 문서 | T5 |
| KEEP-22 | Read | 존재하지 않는 locked 경로 | DENY locked | code | T1 |
| KEEP-23 | Write·Edit | configs/backtest_costs.toml | PASS | code | T3 |

KEEP-03의 유지 범위는 파일 도구 판정이다. v05 초안에 대한 Bash 변경은 IDC-10에 따라 DENY protected-path로 변경된다.

NOT_VERIFIED:
- 파일 도구가 상대 경로를 받을 때 hook 프로세스의 기준 디렉터리
- Edit 권한 규칙의 Write·MultiEdit 적용 범위
- `!` 명령의 hook 적용 여부. 복구는 Claude Code 밖 터미널로 하므로 여기에 의존하지 않는다.
- node ID 문자열로 인한 Guard 오탐 가능성. 코드 해석에 따른 미검증 위험이다.
- PowerShell 도구 호출의 실제 hook 적용
- 권한 규칙 `Bash(...)`의 PowerShell 호출 적용 여부
- D2 신규 패턴의 절대 경로 일치. T2에서 확인한다.

## IMPLEMENTATION_SAFETY_CONDITIONS

IMPLEMENTATION_SAFETY_CONDITIONS:
- S0 SESSION_START_CHECK: HEAD = C1, Work Order sha256 일치, clean(ignored `.venv` 제외), ENVIRONMENT_ACCEPTANCE의 S0 항목 전부 충족. 인라인 인터프리터는 sys.prefix와 moneylab.__file__ 출력을 위한 지정 명령 1개만 허용한다.
- S0a PYTEST_XFAIL_SUPPORT: 수정 전에 `./.venv/Scripts/python.exe -m pytest --version`과 `./.venv/Scripts/python.exe -m pytest --markers`로 고정 버전과 xfail의 `raises` 지원을 확인하고 원문을 보고한다. `--runxfail` 옵션 지원은 `--help`로 확인한다. 확인되지 않으면 STOP하고 사용자가 결정한다.
- S1 원본 정체성: 네 파일의 `git hash-object`와 `git rev-parse HEAD:<path>`가 BASE_FILE_IDENTITY와 같다. 다르면 STOP.
- S2 변경은 ALLOWED_FILES로 한정한다.
- S3 ASK 대상 파일 수정은 사용자 승인이 필요하다. 거절되면 STOP.
- S4 guard crash 또는 fail-closed로 호출이 막히면 다른 경로를 시도하지 않고 STOP한다.
- S5 복구는 사용자의 명시적 조치 후 진행한다.
- S6 SAFE_CHANGE_PRINCIPLES:
  - Edit의 크기를 강제하지 않는다. 각 Edit 뒤 guard.py는 실행 가능한 상태여야 한다.
  - 변경은 검증 가능한 단위로 나눈다. 한 단위마다 관련 테스트를 실행한 뒤 다음 단위로 간다.
  - 기존 DENY·ASK를 임시로도 완화하지 않는다. guard·hook 비활성화로 작업 순서를 맞추지 않는다.
  - settings.json 변경은 guard.py 변경과 분리하고, hook 연결·래퍼는 바꾸지 않는다.
  - 호출이 막히면 S4를 적용한다.

EXPECTED_FAILURE_RULE:
- 예상 실패는 이번 task에서 새로 추가한 테스트 중, 아직 구현하지 않은 판정을 기대하는 사례만 해당한다.
- 표시는 `xfail(strict=True, raises=AssertionError, reason="GUARD-PROTECT-01 pending: <IDC-ID>")`로 한다.
- 파일과 경로 준비는 fixture에서 하고, 테스트 본문은 Guard의 `(action, rule)`이 IDC의 AFTER와 같은지만 assert한다. 실패 메시지에 관측값을 포함한다. 본문에 다른 assert를 두지 않는다.
- fixture 오류는 EXPECTED_FAILURES가 아니라 REGRESSION_FAILURES로 처리한다.
- D4 판별 오류는 내부 함수 치환 없이 임시 파일 구조로 재현한다. 재현할 수 없으면 STOP하고 별도 결정을 요청한다.
- PENDING_REGISTER: 실행 전에 pending node ID, IDC-ID, 그 행의 BEFORE를 보고한다. 등록되지 않은 node는 pending이 아니다.
- 신규 pending node ID는 Guard의 명령 문자열 오탐 가능성을 고려해 중립적으로 작성한다. 기존 테스트 node ID는 변경하지 않는다.
- 실행이 실제로 차단되면 이름 변경이나 다른 실행 경로로 우회하지 않고 STOP한다.

### BEFORE_DIAGNOSIS

- 해당 IDC의 guard 판정을 구현하기 전에 1회 수행한다.
- 사전 등록된 pending node ID를 지정해 그 node에만 `--runxfail`을 적용한다. 등록 밖의 node에 적용하지 않는다.
- assert 메시지의 관측 `(action, rule)`을 해당 IDC의 BEFORE와 대조한다.
- 관측 action 또는 rule이 BEFORE와 다르면 STOP한다.
- AssertionError 이외의 예외는 회귀이며 STOP한다.

### EXPECTED_FAILURE_RULE (BEFORE_DIAGNOSIS 이후)

- 보고는 EXPECTED_FAILURES(등록된 node, 관측값이 BEFORE와 일치)와 REGRESSION_FAILURES(그 외 전부)로 분리한다.
- BEFORE_DIAGNOSIS의 결과는 전체 테스트 PASS의 근거가 아니다. 전체 테스트 판정은 `--runxfail` 없이 실행한 결과로만 한다.
- BEFORE의 규칙명이 표에 없는 PASS는 관측 rule이 빈 값이어야 한다.
- 해당 판정을 구현하면 strict xfail이 XPASS로 실패하므로 표시를 제거한다.
- 다음은 모두 회귀 실패이며 STOP이다:
  - 기존 테스트의 실패, 사례 삭제, 기대값 변경, 결과 변화
  - 기존 판정의 규칙명 변경
  - 기존 strict xfail 3건의 결과 변화
  - 보고 목록 밖의 새 실패
  - 기대와 다른 사유의 실패, 또는 INTENDED_DECISION_CHANGES 밖의 판정 변경
- PRECOMMIT_AUDIT, COMMIT, CI, MERGE 시점에는 `GUARD-PROTECT-01 pending` 표시가 0건이어야 한다.

## TEST_GATES

TEST_GATES (모두 offline. 실행은 `./.venv/Scripts/python.exe -m pytest`):
- T1 D1 판정: 있음·없음, 표기 변형, README·TEMPLATE ASK, 존재하지 않는 locked Read DENY.
- T2 D2 판정: 변경 동사 DENY, 읽기 PASS, redirect DENY, sed DENY, 범위 밖 Bash 쓰기 유지.
  - 절대 경로 사례는 명령을 실행하지 않고 guard 판정만 확인한다. 경로는 슬래시, 백슬래시, 대문자, 따옴표로 묶은 표기를 포함한다.
  - 기대 판정:
    - 계약 파일 + 일반 변경 동사, 재귀 삭제, git rm: DENY protected-path
    - redirect 대상이 계약 파일: DENY protected-path
    - D3 새 보호 대상과 v05 초안 + 변경 동사: DENY protected-path
    - D6 파일, .claude/skills + 변경 동사: DENY protected-path
    - 같은 경로의 cat, grep: PASS
  - 사례 경로는 raw, locked, record 같은 기존 규칙 단어를 포함하지 않는다.
  - PowerShell: `decide`에 tool_name PowerShell로 대표 변경 명령 1건과 읽기 명령 1건을 넘겨 판정 함수의 결과를 확인한다. 이 사례는 실제 hook 적용의 증거가 아니다.
- T3 D3 판정: 기존·신규, BT4 파일, v06 초안 ASK, v04·v05 판정과 규칙명 불변, backtest_costs PASS.
- T4 D4 판정(파일 도구): 임시 worktree 구조, 저장소 밖 PASS, 다른 저장소 PASS, 판별 오류 처리, junction.
- T5 D5 판정: 각 Git 명령, amend DENY, 메시지 텍스트 오탐 없음, 유지 사례, git stash list ASK.
- T6 D6 판정.
- T7 신규 분기 예외 차단.
- T8 INTENDED_DECISION_CHANGES의 각 행을 `(action, rule)` 테스트 사례로 고정.
- T9 tests/test_agent_guard.py 통과. 기존 사례 삭제·기대값 변경 금지, 추가만 허용. 기존 strict xfail 결과 유지. EXPECTED_FAILURE_RULE 적용.
- T10 tests/test_skills.py, tests/test_repo_hygiene.py 수정 없이 통과. 전체 pytest failed 0 / errors 0. pending 표시 0건.
- T11 `-m ruff check --no-cache --select E4,E7,E9,F src tests`, `-m mypy` 통과. 테스트에 사용자 홈 경로·개인 이메일 없음.
- T12 hook 래퍼 판정: 기존 wrapper 테스트 방식에 따라 guard.py 사본을 임시 root의 `.claude/hooks/`에 두고, IDC의 파일 도구 대표 사례를 subprocess로 넘겨 종료 코드와 규칙 이름을 확인한다. 실제 저장소 파일은 수정하지 않는다.
- `git diff --check` 깨끗함, 변경 파일 집합 ⊆ ALLOWED_FILES, PROTECTED diff = 0.
- .claude/hooks/guard.py, tests/test_agent_guard.py, docs/agent_workflow.md는 필수 변경이다. .claude/settings.json은 D8을 적용할 때만 변경한다.

## E2E_GATES

E2E_GATES:
- clean 구현 커밋에서 T1~T12 재실행.
- 커밋된 guard로 INTENDED_DECISION_CHANGES를 테스트로 확인한다. 실제 대상 파일을 변경하지 않는다.
- 실제 Claude Code hook 동작은 ACTIVATION_HOOK_OBSERVATION에서만 관측한다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA:
- AC1 기존 guard 보호 규칙을 약화하지 않는다. 기존 DENY·ASK가 PASS로 바뀌지 않는다.
- AC2 기존 PASS·ASK·DENY와 규칙명 회귀 테스트 통과, 표 밖 판정·규칙명 변경 없음.
- AC3 신규·기존 Work Order와 ERRATA 판정이 D1, D2를 만족.
- AC4 사전등록 판정이 D3를 만족.
- AC5 Worktree 판별 실패 시 D4대로 처리.
- AC6-a ACTIVATION_INTEGRITY PASS
- AC6-b ACTIVATION_UNIT PASS
- AC6-c ACTIVATION_HOOK_OBSERVATION PASS
- AC7 복구 경로가 문서화되고 사용자가 C1 파일로 복원할 수 있음.
- AC8 테스트·필수 CI 통과.
- AC9 승인된 4개 파일 외 구현 변경 없음.
- AC10 비밀 파일 접근 없음, 관련 테스트의 비밀 판정 유지.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base SHA·tree, C1·Ci SHA·parent·tree, Work Order sha256, 파일 blob, 커밋 파일 집합, merge parent·tree
- CLAUDE_REPORTED: 환경 확인, pytest 지원 확인, pytest, 예상 실패 목록과 BEFORE 대조, E2E, ACTIVATION_CHECK 관측
- INDEPENDENT: PR CI, GitHub 화면과 사용자 재확인
- USER_APPLIED: 사용자의 환경 생성, 복구 조치

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- IMPLEMENTATION: pytest·xfail 지원 원문, PENDING_REGISTER, BEFORE_DIAGNOSIS의 관측 `(action, rule)`과 대조 결과, EXPECTED_FAILURES, REGRESSION_FAILURES, `--runxfail` 없는 전체 테스트 결과
- ACTIVATION_CHECK: INTEGRITY_PASS, UNIT_PASS, HOOK_OBSERVATION_PASS, 호출별 관측 원문과 판정, 사용자가 제공한 승인 창 문구, 단계별 재개 승인 문구, FINAL_STATUS 결과, KNOWN_LIMITATION
- ACTIVATION_CHECK의 STOP마다 수행한 단계, 관측 원문, 다음 단계를 보고한다. 이 보고는 gate 완료 보고가 아니다.
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, Work Order sha256 불일치, S1 불일치
- C1 파일이 검토된 발행 문구와 다름, 또는 승인된 세 치환 밖의 변경이 있음
- BASE@ 형식이 CLAUDE.md의 상위 규칙에 위배됨
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, 교집합 발생, A/M 표기 불일치
- guard deny, 권한 창 거절, guard crash 또는 전 도구 차단.
  - 예외는 없다. D10 ACTIVATION_HOOK_OBSERVATION의 지정 호출에서 기대한 DENY와 사용자의 ASK 거절도 즉시 STOP하고 보고한다.
  - 호출당 1회만 정상 관측으로 처리하며, 다음 단계는 D10의 재개 승인이 있을 때만 진행한다.
  - 다음은 관측 실패이며 재개 승인으로도 다음 단계로 넘어가지 않는다: 지정 호출 밖의 DENY·권한 거절, 같은 호출의 재시도, 기대한 Guard 규칙명이 확인되지 않은 경우, `git stash` 명령이 실제로 실행된 경우, 보호 파일이 변경된 경우.
- pytest의 `raises` 또는 `--runxfail` 지원 미확인
- 테스트 실패·에러. 예외는 EXPECTED_FAILURE_RULE의 등록된 strict xfail과 BEFORE_DIAGNOSIS의 EXPECTED_FAILURES뿐이다.
- BEFORE_DIAGNOSIS의 관측 action 또는 rule이 IDC BEFORE와 다름
- T2의 절대 경로 사례가 기대 판정과 다름. 기대값 변경, 사례 삭제, 새 탐지 알고리즘 추가로 해결하지 않는다. EXPECTED_FAILURE_RULE의 등록된 사례 외에는 예외가 없다.
- INTENDED_DECISION_CHANGES 밖 판정·규칙명 변경, 기존 DENY·ASK의 PASS 전환
- D4 충족 불가, 계약을 지키려면 PROTECTED 파일 수정이 필요함
- 계약 모순, 상위 규칙 충돌
- 예상 외 파일 변경:
  - 해당 gate의 허용 집합 밖 tracked 변경
  - 예상 밖 untracked 파일
  - 승인 목록 밖 ignored 산출물 변경
  - 허용 ignored: 승인된 `.venv`, `__pycache__`, `.pytest_cache`, 커밋된 테스트의 임시 출력
- Hook 판정 불일치:
  - 실제 hook 판정 또는 규칙 이름이 기대값과 다름
  - 승인 창이 있어야 할 호출에 없음, 없어야 할 호출에 있음
  - 단위 테스트와 실제 hook의 판정이 다름
  - 권한 규칙이 먼저 작동해 guard 판정을 확인할 수 없음
  - 위 경우 원문 메시지를 보고하고, 재시도나 변형 호출을 하지 않는다.

## ROLLBACK_AND_RECOVERY

ROLLBACK_AND_RECOVERY:
- 수정 중 테스트 실패: STOP. 승인 후 IMPLEMENTATION 안에서 Edit. 임의 restore 금지.
- 전 도구 차단: 사용자가 Claude Code 밖 터미널에서 해당 파일을 C1 상태로 복원하고 보고. 에이전트 조치 없음.
- 표 밖 판정·규칙명 변경: STOP. 코드 수정 또는 ACCEPTED ERRATA.
- CI 실패: STOP. 명시 승인 시 IMPLEMENTATION rollback, 새 커밋. 자동 재실행 금지.
- MERGE 후 오작동: STOP. ACCEPTED ERRATA 또는 새 task와 PR. main 직접 push, 이력 재작성 금지.
- ACTIVATION_CHECK 실패: STOP. 조사만.
- 기존 worktree와 산출물은 어떤 경우에도 정리하지 않는다.

## COMPLETION_CRITERIA

COMPLETION_CRITERIA:
- ACCEPTANCE_CRITERIA 전부 충족
- MERGE, POST_MERGE_AUDIT PASS, ACTIVATION_CHECK PASS
- 잔여 공백 기록: 텍스트 매칭 한계, 스크립트 내부 동작, D4 범위, 해시 미고정 문서, Write·Edit 실제 hook 미관측, configs/backtest_costs.toml guard 미보호
- KNOWN_LIMITATION (다른 worktree의 Bash):
  - D2의 문자열 규칙으로만 판정하며 동등 보호를 보장하지 않는다.
  - 상대 경로, `cd` 이후 실행, 변수·문자열·스크립트 내부에서 조립한 경로는 보호 경로로 인식되지 않을 수 있다.
  - 이 한계를 해소했다고 주장하지 않는다.
- GUARD_PROTECTION_COMPLETE: NO 유지

## BT4_VALID_01_INTERLOCK

BT4_VALID_01_INTERLOCK:
- 이 task의 완료는 BT4-VALID-01 재개가 아니다.
- 차단 해제 판단 증거: 필수 Guard 규칙 병합, 기존·신규 테스트 통과, CI PASS, POST_MERGE_AUDIT PASS, ACTIVATION_CHECK PASS, 새 main SHA·tree 확인, 사용자 별도 승인.
- 이 Work Order는 BT4-VALID-01의 통계 계약, 연구 설계, 구현을 바꾸지 않는다.

## REPORT_STORAGE

REPORT_STORAGE: gate 보고는 채팅으로만 한다.
