# Work Order: CI-EVIDENCE-01 — Record every test outcome in the required Windows pytest summary

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/CI-EVIDENCE-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

이 파일이 계약의 유일한 출처다. 대화 기억이나 채팅 보고서에 의존하지 않는다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: CI-EVIDENCE-01
TASK_ID: CI-EVIDENCE-01
TITLE: Record every test outcome in the required Windows pytest summary
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: f2b5d91d59fedbc87e916ed3086fe710b5fc7d9a
CANONICAL_BASE_TREE: 271a72993c5526fd6990e2d751ae4cfb92dfc4a8
BASE_BLOBS: .github/workflows/ci-tests.yml fa99d8f746ea190552245386da4ef19e34a2d818 (86 lines, LF, final newline)
TARGET_BRANCH: ci/ci-evidence-01
TARGET_WORKTREE: C:/MoneyLab-ci-evidence-01
SOURCE_WORKTREE: C:/MoneyLab-mc-v06 (WORKSPACE_SETUP 명령을 실행하는 기존 worktree. 파일·index·branch를 바꾸지 않는다.)
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
PRIOR_GATES: DESIGN_INVESTIGATION, CONTRACT_REVIEW, WORK_ORDER_DRAFT. 모두 채팅, C1 이전.
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests / pytest (Windows)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

(WORK_ORDER_DRAFT는 C1 이전 채팅 단계이며 GATE_SEQUENCE를 바꾸지 않는다.)

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: CI-EVIDENCE-01 <GATE> WO@<C1 commit>`)
- 각 gate의 보고 후 멈춘다. 이전 gate의 승인이나 이 Work Order 자체는 다음 gate의 승인이 아니다.
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping
- 역사적 BLOCKED 결과를 PASS로 바꿔 쓰지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다. guard deny는 우회하지 않는다. 이 Work Order는 새 governance 권한을 만들지 않는다.

## GOAL

GOAL: 필수 Windows CI job `pytest`의 pytest 요약에 모든 테스트의 node ID와 결과(passed, failed, error, skipped, xfailed, xpassed)를 남겨, 개별 테스트 실행을 CI 로그에서 직접 검증할 수 있게 한다. 이 task는 계약 v1.2 §13의 PR_CREATE와 MERGE_EXECUTE 절차를 처음 실제로 적용한다.

## BACKGROUND

BACKGROUND:
- 현재 `.github/workflows/ci-tests.yml` 53행은 `coverage run -m pytest -rsx`다. `-rsx`는 skip·xfail만 node ID와 함께 요약하고, 통과한 테스트의 node ID는 남기지 않는다.
- DOCS-ALIGN-01(PR #33)에서 ERRATA-001의 CI hygiene 조건 2·3(두 hygiene 테스트의 수집·실행, skip·xfail 아님)을 직접 증거로 확인하지 못했고, 진행 기호 위치 대조라는 간접 증거를 사용자가 그 task에 한해 수락했다.
- `-rA`는 `P`(passed with output)를 포함해 통과 테스트의 캡처 출력까지 로그에 남기므로 쓰지 않는다. `-rfEsxXp`는 출력 캡처 없이 결과 줄만 남긴다.
- QUALITY-GATES-01(완료)은 "`-rsx` 유지", "job `pytest` 이름 유지"를 정했다. 이 task는 `-rsx`를 `-rfEsxXp`로 바꾸고 job 이름은 유지한다. 완료된 Work Order는 바꾸지 않는다.
- 기준선: run 40673673329(head 9196517c, 시험한 merge ref 5fada94c, tree 271a72993c5526fd6990e2d751ae4cfb92dfc4a8 = CANONICAL_BASE_TREE)의 Windows `pytest` 결과 1966 passed, 6 skipped, 1 deselected, 3 xfailed, 0 failed.
- GOV-AGENT-MERGE-01(설계 결정 OPTION_A, ACCEPTED)이 v1.2 MERGE 승인문에 넣을 추가 조건을 정했다. 이 task의 MERGE gate는 그 조건을 쓴다.
- 사용자 결정: A′ 채택. Windows 필수 job에만 적용. Linux experimental job 변경 없음. JUnit XML·artifact는 범위 밖. 커밋 trailer 없음.

## SCOPE

SCOPE:
- `.github/workflows/ci-tests.yml`의 50행 주석과 53행 pytest 인자, 두 줄만 바꾼다.
- PR_CI gate에서 별도 승인이 있으면 `gh pr create`를 1회 실행한다(v1.2 §13).
- MERGE gate에서 별도 승인이 있으면 `gh pr merge --merge --match-head-commit`을 1회 실행한다(v1.2 §13 + GOV-AGENT-MERGE-01 추가 조건).

## NON_GOALS

NON_GOALS:
- Linux experimental job 변경, `continue-on-error` 변경
- JUnit XML, artifact 업로드, 새 action 추가
- workflow 이름, trigger, permissions, job id, runs-on, timeout, action SHA, ruff, mypy, coverage report 단계 변경
- guard·hook·settings 변경, allow 규칙 추가
- branch protection, rulesets, required status checks 설정
- 테스트·소스·설정·의존성 변경
- Linux guard wrapper 실패 수정(별도 기술 부채)

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP (각 단계는 Gate Authorization이 명시한 경우에만, guard ASK는 사용자 승인 후 진행):
  1. `git fetch origin main`만 실행해 원격 main = CANONICAL_BASE_SHA와 BASE_BLOBS를 확인한다. 다르면 멈추고 보고한다.
  2. 1이 일치하고 TARGET_BRANCH·TARGET_WORKTREE·`docs/tasks/CI-EVIDENCE-01/`이 없을 때만, SOURCE_WORKTREE에서 `git worktree add -b ci/ci-evidence-01 C:/MoneyLab-ci-evidence-01 f2b5d91d59fedbc87e916ed3086fe710b5fc7d9a`로 TARGET_WORKTREE를 만든다.
  3. 같은 명령으로 TARGET_BRANCH `ci/ci-evidence-01`을 CANONICAL_BASE_SHA에서 만든다(2와 한 명령).
  4. `docs/tasks/CI-EVIDENCE-01/WORK_ORDER.md`를 승인 문구 그대로 최초 생성한다.
  5. WORK_ORDER.md만 `git add -- docs/tasks/CI-EVIDENCE-01/WORK_ORDER.md`로 stage한다.
  6. C1 커밋 `docs(task): add CI-EVIDENCE-01 work order`를 만든다(Co-Authored-By trailer 없음). WORK_ORDER.md의 sha256을 커밋 전후로 보고한다.
- IMPLEMENTATION: ALLOWED_FILES를 DESIGN_CONTRACT E1–E2대로 수정하고 TEST_GATES를 실행한다. `.github/` 편집의 guard ASK는 사용자 승인 후에만 진행한다.
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: `git add -- .github/workflows/ci-tests.yml`, 커밋 하나. 메시지 `ci: list every test outcome in the required Windows pytest summary`(Co-Authored-By trailer 없음)
- CLEAN_COMMIT_E2E: E2E_GATES의 읽기 전용 확인
- PUSH: TARGET_BRANCH 하나만 `git push -u origin ci/ci-evidence-01`
- PR_CI: (v1.2 §13) Gate Authorization에 `PR_CREATE: YES`, 저장소, base, head branch, head SHA, PR 제목 전문, PR 본문 전문이 있고 사전 조건을 충족할 때만 `gh pr create` 1회. 그 밖에는 compare URL·PR 본문 제공만. CI는 읽기 전용으로 관찰한다.
- MERGE: (v1.2 §13 + 아래 MERGE_EXECUTE_CONTRACT) Gate Authorization의 필수 값이 모두 있고 사전 검증을 모두 통과할 때만 `gh pr merge <N> -R swk3169/MoneyLab --merge --match-head-commit <HEAD_SHA>` 1회. 그 밖에는 사용자 결정(GitHub UI, MERGE_METHOD).
- POST_MERGE_AUDIT: Gate Authorization이 명시하면 `git fetch origin main`만, 읽기 전용 구조 감사
- COMPLETE: 최종 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, E1–E2 밖 바이트 변경
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull
- hooks·settings·.claude 변경 또는 guard 우회, git config 변경, guard DENY 명령의 재시도·변형
- 다른 branch·worktree·untracked·ignored·reference 산출물·egg-info·외부 venv·scratchpad 정리·변경
- `.venv` 생성·설치·변경, 패키지 설치
- `gh pr merge`의 `--admin`, `--auto`, `--squash`, `--rebase`, `--delete-branch`, `--force`, `gh pr edit`, `gh pr close`, CI 재실행, 자동 재시도
- 승인 1건당 2회 이상의 `gh pr create`·`gh pr merge` 실행
- 위 fetch·push·승인된 gh 명령 밖의 네트워크 쓰기, 거래 API, 자동화 실행

## ALLOWED_FILES

ALLOWED_FILES:
- M .github/workflows/ci-tests.yml

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/CI-EVIDENCE-01/** (명시적 예외: WORKSPACE_SETUP 4–6단계에서 승인된 `docs/tasks/CI-EVIDENCE-01/WORK_ORDER.md`의 최초 생성과 C1 커밋. C1 이후 WORK_ORDER.md는 불변이다. ACCEPTED ERRATA는 v1.2 계약의 별도 승인 절차에 따라서만 `docs/tasks/CI-EVIDENCE-01/ERRATA-<NNN>.md`로 최초 생성할 수 있다.)
- docs/tasks/*/** (기존 모든 task의 Work Order·ERRATA. 변경하지 않는다)
- .github/** 중 .github/workflows/ci-tests.yml 이외 전부
- .claude/**
- src/**, tests/**, configs/**, examples/**, data/**, knowledge/**
- pyproject.toml, requirements.txt, requirements-dev.txt
- CLAUDE.md, AGENTS.md, README.md, ARCHITECTURE.md, LICENSE, .gitattributes, .gitignore, .env.example
- docs/**
- ALLOWED_FILES 이외의 모든 경로

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가). C1 파일 ∩ ALLOWED_FILES = ∅. 의존성 변경 0. C1·ACCEPTED ERRATA 외 새 파일 0. 파일 내부 보호: ci-tests.yml의 E1–E2 밖 바이트는 불변. PROTECTED_FILES의 포괄 규칙은 승인된 C1 및 ACCEPTED ERRATA의 최초 생성 예외보다 우선하지 않는다. 예외는 지정된 Gate에서만 적용한다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- 줄 번호는 BASE_BLOBS 기준이다. 각 블록의 내용은 아래 APPROVED_TEXT의 해당 fenced block에서 여는 fence 줄과 닫는 fence 줄 사이의 줄이다(fence 줄 제외). 각 줄은 LF로 끝난다.
- E1 `.github/workflows/ci-tests.yml` 50행 `      # -rsx prints skip and xfail reasons, so silently skipped tests show up in the log.`을 APPROVED_TEXT W1(1줄)로 교체한다.
- E2 `.github/workflows/ci-tests.yml` 53행 `        run: '& .\.venv\Scripts\python.exe -m coverage run -m pytest -rsx'`을 APPROVED_TEXT W2(1줄)로 교체한다.
- E3 경계: E1–E2 밖의 바이트는 base와 같다. 특히 51행 주석, 52행 단계 이름, 1–49행, 54–86행(coverage report 단계, Linux experimental job 전체)은 바꾸지 않는다. LF와 파일 끝 줄바꿈 형식은 바꾸지 않는다.
- E4 기대 결과: 구현 후 blob = 786bc94f591f7b12f719f033ae162be5575fa942, 86줄, `git diff -U0`의 hunk 2개(-50 +50, -53 +53), +2/−2. 승인 문구 블록은 2개, 2줄. APPROVED_TEXT의 실질 변경이 필요하면 구현하지 않고 멈춰서 PROPOSED_ERRATA로 보고한다.

APPROVED_TEXT W1 (.github/workflows/ci-tests.yml, E1, 1줄):

````text
      # -rfEsxXp lists every test's node ID and outcome, with skip and xfail reasons, but no captured output.
````

APPROVED_TEXT W2 (.github/workflows/ci-tests.yml, E2, 1줄):

````text
        run: '& .\.venv\Scripts\python.exe -m coverage run -m pytest -rfEsxXp'
````

## MERGE_EXECUTE_CONTRACT

MERGE_EXECUTE_CONTRACT (GOV-AGENT-MERGE-01 OPTION_A, v1.2 §13에 더하는 승인 조건):
- MERGE Gate Authorization 필수 값: TASK_ID, PR_NUMBER, HEAD_SHA, BASE_SHA, REQUIRED_CI_RUN_ID, `MERGE_EXECUTE: YES`, `MERGE_METHOD: CREATE_MERGE_COMMIT`, `MAX_ATTEMPTS: 1`, `POST_MERGE_AUDIT: REQUIRED`.
- 사전 검증(읽기 전용, 하나라도 실패·확인 불가면 MERGE_EXECUTE = NO, STOP):
  1. PR 번호 = 승인 PR_NUMBER.
  2. PR head SHA = HEAD_SHA = 원격 branch head.
  3. 원격 main = BASE_SHA.
  4. BASE_SHA = 이 Work Order(와 ACCEPTED ERRATA)의 유효한 기대 base.
  5. REQUIRED_CI_RUN_ID run의 head = HEAD_SHA이고 REQUIRED_CI_CHECKS job = SUCCESS.
  6. 그 run이 checkout한 merge ref의 parent1 = BASE_SHA(checkout 로그와 GitHub API로 확인).
  7. 그 merge ref의 parent2 = HEAD_SHA.
  8. v1.2 §13 사전 검증 1–7 충족.
  9. 이 Work Order의 AC1, AC2, AC4, AC8을 그 run에서 충족.
- 실행 직전 PR head SHA와 원격 main SHA를 다시 확인한다. 다르면 STOP.
- `gh pr merge <PR_NUMBER> -R swk3169/MoneyLab --merge --match-head-commit <HEAD_SHA>` 1회. guard `github` ASK는 사용자가 따로 승인한다. 자동 재시도 금지.
- 채팅 실행 기록: 명령 원문, UTC 시각, exit code, 출력 요약, 사전 검증 결과, merge commit SHA, parent1·parent2, parent1 = BASE_SHA 여부. 저장소에 기록하지 않는다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA:
- AC1 Windows 필수 job의 성공 조건 유지: job id `pytest`, 단계 구성, pytest·coverage 명령의 다른 부분이 base와 같고, 차이는 53행의 `-rsx` → `-rfEsxXp`뿐이다.
- AC2 PR CI의 Windows `pytest` job 로그에 `PASSED tests/test_repo_hygiene.py::test_no_secrets_or_personal_data_in_addable_files`와 `PASSED tests/test_repo_hygiene.py::test_no_forbidden_or_large_tracked_files` 줄이 있다. 줄 형식이 다르면 실제 형식을 보고하고 사용자 판단을 받는다.
- AC3 그 결과를 `gh run view --log --job <id>`로 조회할 수 있다.
- AC4 pytest 실패를 성공으로 바꾸지 않는다: `-r` 옵션만 바뀌고 exit code 처리와 단계 구성은 그대로다.
- AC5 Linux experimental job(58–86행)은 diff 0이다.
- AC6 구현 커밋 파일 집합 = ALLOWED_FILES. PR 전체 파일 집합 = ALLOWED_FILES ∪ {docs/tasks/CI-EVIDENCE-01/WORK_ORDER.md} (ACCEPTED ERRATA가 생기면 그 파일 포함).
- AC7 추가된 로그 줄은 결과·node ID 요약뿐이고 출력 캡처(`P`·`A`)는 없다. PR CI의 `tests/test_repo_hygiene.py`가 통과하고, 추가된 PASSED 줄 표본에 비밀값·개인정보가 없음을 검토한다.
- AC8 PR CI의 Windows `pytest` 결과가 기준선(run 40673673329)과 같다: 1966 passed, 6 skipped, 3 xfailed, 1 deselected, 0 failed. 로그의 `PASSED ` 요약 줄 수 = 1966. 수치가 다르면 원인을 분석하고 근거 없이 PASS로 판정하지 않는다.

## TEST_GATES

TEST_GATES:
- 변경 파일 집합 = ALLOWED_FILES, PROTECTED diff 0, untracked 0
- `git diff --check` 깨끗함
- hunk 대조: `git diff -U0 f2b5d91d59fedbc87e916ed3086fe710b5fc7d9a -- .github/workflows/ci-tests.yml`의 hunk가 E1·E2와 같고 수가 2이다
- 기대 결과 일치: 커밋된 WORK_ORDER.md의 APPROVED_TEXT로 base에서 독립 재구성한 blob = 786bc94f591f7b12f719f033ae162be5575fa942, 86줄
- Linux job 블록 diff 0(AC5)
- 로컬 pytest는 요구하지 않는다(TARGET_WORKTREE에 `.venv`가 없고 이 task는 `.venv`를 만들지 않는다). 회귀·증거 확인은 PR CI `ci-tests / pytest (Windows)`로 한다(AC2, AC7, AC8).
- guard가 거부하는 문자열을 담은 로컬 검사 명령은 실행하지 않는다. 거부되면 재시도·변형하지 않고 멈춘다.

## E2E_GATES

E2E_GATES:
- NOT_REQUIRED (설정 한 줄과 주석 한 줄). 대체 확인: clean 구현 커밋에서 ci-tests.yml blob이 E4와 같고, 커밋 파일 집합 = ALLOWED_FILES이며, 구현 커밋의 부모 = C1(또는 마지막 ACCEPTED ERRATA 커밋)이다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 커밋 SHA·parent·tree, Work Order sha256, 커밋 파일 집합, ci-tests.yml blob과 E4 일치, hunk 목록, merge parent·tree
- CLAUDE_REPORTED: Claude가 실행한 확인·계산, 재구성 비교, 로그 집계
- INDEPENDENT: PR CI 결과와 로그, GitHub API, GitHub 화면(사용자 확인)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- PR_CI·MERGE에서 gh 명령을 실행하면 MERGE_EXECUTE_CONTRACT의 채팅 실행 기록
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

## ROLLBACK_RECOVERY

ROLLBACK_RECOVERY:
- merge 전: PR을 사용자가 닫거나 ERRATA로 계약을 고친다. 커밋 rewrite 없음.
- PR_CREATE 실패·불확실: 재실행하지 않고 `gh pr list`·`gh pr view`로 상태만 확인해 보고한다.
- MERGE 실패: 재시도하지 않고 PR 상태와 원격 main을 읽기로 확인해 보고한다. 다음 시도는 새 Gate Authorization이다.
- merge 후 parent1 ≠ BASE_SHA 또는 감사 실패: 즉시 보고한다. 되돌리기는 새 Work Order의 revert PR(merge commit)로만 한다. force push·reset 없음.
- merge 후 CI 출력 문제(예: 로그 과대): 새 Work Order로 옵션을 조정한다.

## RISKS_EXCEPTIONS

RISKS_EXCEPTIONS:
- R1 자기 검증: 이 PR의 `pull_request` run은 바뀐 workflow로 필수 check를 실행한다. AC1·AC4(diff는 53행 인자뿐)와 AC8(수치 동일)로 완화한다.
- R2 AC2 줄 형식 미관측: 처음 관측은 PR_CI에서 한다. 다르면 보고하고 사용자 판단을 받는다.
- R3 v1.2 §13 첫 실제 적용: 해석 문제가 드러나면 멈추고 ERRATA로 다룬다.
- R4 TOCTOU: `gh pr merge`는 base를 고정할 수 없다. 실행 직전 재확인과 POST_MERGE_AUDIT parent1 확인으로 완화한다.
- R5 서버 측 강제 없음(branch protection 없음): 규칙 준수는 사전 검증과 사용자 판단에 의존한다.
- R6 로그 보관 기간: 저장소 설정을 확인하지 않았다(UNVERIFIED). 증거는 로그 보관 기간 동안만 남는다.
- R7 로그 증가: PASSED 요약 줄 약 1966줄이 추가된다.
- R8 ASK 피로: 승인 창의 명령 원문(PR 번호·SHA)을 승인문과 대조하는 것을 사용자 절차로 권고한다.

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, 원격 main ≠ CANONICAL_BASE_SHA(MERGE에서는 ≠ 승인 BASE_SHA), Work Order sha256 불일치
- BASE_BLOBS 불일치, 또는 E1–E2가 인용한 base 줄의 내용이 실제와 다름
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, E1–E2 밖 바이트 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기와 base 상태 불일치
- 구현 결과가 E4와 다름, APPROVED_TEXT 변경 필요
- NON_GOALS 항목을 건드려야만 일관성이 맞는 경우
- guard deny, 권한 창(ASK) 거절
- CI 실패(PR CI의 필수 Windows `pytest` job 실패 또는 `ci-tests` workflow run의 최종 결론 실패)
- MERGE_EXECUTE_CONTRACT 사전 검증 실패·확인 불가, gh 명령 실패
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일
