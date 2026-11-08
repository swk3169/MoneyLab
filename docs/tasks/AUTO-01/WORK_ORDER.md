# Work Order: AUTO-01 — Read-Only Automation MVP

이 파일은 C1 커밋 이후 불변이다. 변경은 ACCEPTED ERRATA로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: AUTO-01
TASK_ID: AUTO-01
TITLE: Deterministic Read-Only Automation MVP
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 849a44efe7a463e833294aa5596ec4f6a91f4b0c
CANONICAL_BASE_TREE: 4e0034a8e78850ba0286b2e64b6a8ebe0f45bea1
TARGET_BRANCH: feature/auto-01-readonly
TARGET_WORKTREE: C:/MoneyLab-auto-01
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests / pytest (Windows)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 전진은 Gate Authorization (`GATE_AUTHORIZATION: AUTO-01 <GATE> WO@<C1 SHA>`) 하나당 한 gate만 허용한다.
- 후퇴는 명시적 승인으로 IMPLEMENTATION에만 허용한다.
- COMMIT 이후 수정은 새 커밋으로 처리하며 amend하지 않는다.
- gate 생략은 허용하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: CLAUDE.md, docs/tasks/README.md, docs/agent_workflow.md, .claude/ guard·hook·settings, 기존 고정·사전등록 계약이 우선한다. 이 Work Order는 이를 변경하거나 우회하지 않는다.

## GOAL

GOAL: 오프라인 Knowledge 검증 작업 하나를 결정적 allowlist로 판정하고, 고정 argv로 한 번 실행한 뒤 표준 증거를 반환하는 최소 읽기 전용 자동화 API를 구현한다. 무인 반복 실행과 자동 Gate 승인은 활성화하지 않는다.

## BACKGROUND

BACKGROUND:
- SUPERVISOR-01의 Proposal은 Work Order나 실행 승인이 아니다. 기존 Proposal 스키마는 변경하지 않는다.
- CE-02와 Supervisor는 읽기 전용 입력 공급원이며 이번 구현 범위 밖이다.
- 기존 Guard는 Claude Code 보호용이며 OS sandbox가 아니다.
- GUARD_PROTECTION_COMPLETE=NO는 그대로 유지한다. 이 사실만으로 이번 task의 별도 승인된 gate가 자동 중단되는 것은 아니나, Guard의 실제 거절·차단은 STOP이다.

## ENVIRONMENT

ENVIRONMENT:
- WORKSPACE_SETUP은 기존 정상 작동하는 세션에서 수행한다. TARGET_WORKTREE를 root로 하는 새 Claude Code 세션은 그곳에 전용 .venv가 준비된 뒤 시작한다.
- 사용자 승인 아래 TARGET_WORKTREE/.venv에 전용 Python 3.14.8 환경을 준비한다. 버전이 다르면 보고 후 STOP한다.
- 의존성 준비는 기존 고정 requirements-dev.txt와 `pip install -e . --no-deps` 기준이다. 실제 설치 명령·네트워크 사용·환경 변경은 별도 사용자 승인 없이는 실행하지 않는다.
- S0: TARGET_WORKTREE root 세션에서 차단 없는 읽기 도구 호출이 가능한지 확인한다. 이는 hook 실행 경로 정상의 필요조건일 뿐 Guard 전체 활성화 검증 PASS를 뜻하지 않는다. 모든 도구 호출이 차단되면 STOP한다.
- S0: sys.version, sys.prefix, sys.executable, moneylab.__file__을 읽기 전용으로 확인한다. sys.executable은 TARGET_WORKTREE/.venv 하위이고 moneylab.__file__은 TARGET_WORKTREE/src/moneylab 하위여야 한다. 불일치 시 STOP한다.
- S0에서 전용 환경·기존 테스트 기준선·Guard의 실제 동작을 확인하되, GUARD-ACTIVATION-01 미완료를 완료로 선언하지 않는다.
- WORKSPACE_SETUP에서 원격 main SHA/tree, branch·worktree 부재, 승인된 원문 파일의 절대 경로·SHA-256·줄 수·바이트 수를 대조한다. 원문은 저장소 밖의 승인된 파일에서 변경 없이 복사한다. C1 전후 SHA-256이 동일해야 한다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: 승인된 새 branch·worktree 생성, 승인된 WORK_ORDER.md 원문을 최초 복사, 해당 파일 하나만 stage하고 C1 커밋.
- IMPLEMENTATION: ALLOWED_FILES만 신규 생성하고 지정된 오프라인 테스트·정적 검사를 실행.
- PRECOMMIT_AUDIT: 읽기 전용으로 파일 집합·계약·보호 경로·테스트 증거 감사.
- COMMIT: ALLOWED_FILES만 경로를 지정해 stage하고 구현 커밋 하나 생성.
- CLEAN_COMMIT_E2E: clean commit 기준 테스트·API E2E 실행, 기존 파일 보존.
- PUSH: TARGET_BRANCH 하나만 `git push -u origin feature/auto-01-readonly`.
- PR_CI: README §13의 조건을 모두 만족하고 별도 승인에 PR_CREATE: YES 및 필요한 PR 정보가 있을 때만 `gh pr create` 1회. 아니면 compare URL과 PR 본문만 제공.
- MERGE: README §13의 조건을 모두 만족하고 별도 승인에 MERGE_EXECUTE: YES 및 PR 번호·head SHA가 있을 때만 merge commit 방식으로 1회. 아니면 사용자 결정 대기.
- POST_MERGE_AUDIT: main ref만 fetch하여 병합 parent·tree·ancestry 감사.
- COMPLETE: 채팅·PR 본문으로 증거 요약. 추가 보고 파일 생성 금지.

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖 작업, ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경.
- Work Order·ERRATA 수정, .claude/ 변경, Guard·Hook·Settings 우회.
- 임의 shell/argv 실행, AI 생성 명령 실행, 외부 API·네트워크 호출을 요구하는 action 추가.
- 실거래·주문·자금 이동·비밀정보 접근·서명·지갑 기능.
- 연구 사전등록·locked·frozen·test split 변경, 기존 데이터·산출물 정리.
- Task Queue, 무인 루프, 자동 Git 작업, PR 자동 병합, 비용 한도 강제 기능 구현.
- 패키지 임의 설치, 승인되지 않은 환경 변경.
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune.
- 다른 branch·worktree·untracked·ignored·reference 산출물 삭제 또는 변경.

## ALLOWED_FILES

ALLOWED_FILES:
- A src/moneylab/automation/__init__.py
- A src/moneylab/automation/policy.py
- A src/moneylab/automation/executor.py
- A src/moneylab/automation/evidence.py
- A tests/test_automation_policy.py
- A tests/test_automation_executor.py
- A tests/test_automation_evidence.py
- A tests/test_automation_isolation.py

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/AUTO-01/** (C1에서 WORK_ORDER.md 최초 생성만 예외; 이후 불변)
- .claude/**
- .github/**
- CLAUDE.md
- docs/agent_workflow.md
- docs/tasks/README.md
- docs/tasks/TEMPLATE.md
- pyproject.toml
- src/moneylab/supervisor/**
- src/moneylab/knowledge/**
- src/moneylab/execution/**
- configs/**
- knowledge/records/**
- data/raw/**
- data/processed/**
- tests/** EXCEPT tests/test_automation_policy.py, tests/test_automation_executor.py, tests/test_automation_evidence.py, tests/test_automation_isolation.py

INVARIANT: IMPLEMENTATION의 ALLOWED_FILES ∩ PROTECTED_FILES = ∅. WORKSPACE_SETUP의 C1 원문 최초 생성은 README v1.2에 따른 별도 예외이며 구현 허용 파일에 포함하지 않는다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 Policy: `src/moneylab/automation/executor.py`의 공개 API는 `run_action(action_id: str) -> str`이다. 반환값은 UTF-8 canonical JSON 문자열이며 stdout에 직접 출력하지 않는다. 유일한 허용 action_id는 `knowledge_validate`; 다른 값은 실행 없이 DENY한다. 인자·명령 문자열·경로를 외부에서 받지 않는다.
- D2 CLI: 실제 argv는 `[sys.executable, '-m', 'moneylab.knowledge', '--root', <검증된 절대 repo root>, 'validate']`로 고정한다. `--full-history`는 사용하지 않는다. repo root는 검증된 실행 환경에서 결정하고 임의 입력을 받지 않는다. 종료 코드 0=SUCCEEDED, 1=VALIDATION_FAILED, 3=SOURCE_UNVERIFIED, 그 외(2 포함)=UNEXPECTED_EXIT, timeout=TIMEOUT이다. 0 이외는 성공이 아니다.
- D3 Executor: `subprocess.Popen`에 고정 argv 리스트, `shell=False`, 고정 cwd, 환경변수 allowlist를 적용한다. stdout·stderr는 별도 표준 라이브러리 thread에서 각각 청크 단위로 동시에 읽고, 공유된 누적 바이트 수 상한(두 스트림 합계 1 MiB = 1,048,576 bytes)을 초과하면 프로세스를 종료한다. 두 reader thread는 누적 길이 검사와 바이트 추가를 동일 lock으로 직렬화하며, 상한 초과 청크는 저장하지 않는다. 제한을 넘는 출력은 상태 OUTPUT_LIMIT_EXCEEDED로 기록한다. timeout은 프로세스 시작부터 종료·회수까지의 단조 시계 기준 60초로 적용한다. timeout 또는 출력 상한 초과 시 프로세스를 kill하고 wait로 회수하며 reader thread를 join한다. 종료·회수에 실패하거나 thread가 남으면 성공으로 보고하지 않고 STOP한다. subprocess 전체 출력을 무제한 메모리에 모으거나 실행 후 잘라내는 방식은 금지한다. 재시도 0회이며 단일 호출 동시 실행 1개만 허용한다. `sys.executable`을 사용하며 Windows 경로를 코드에 하드코딩하지 않는다.
- D4 Environment: 최소 환경변수 allowlist를 사용한다. Windows에서는 SYSTEMROOT 및 검증된 PATH(Git 실행 경로 포함), 필요한 경우 Windows 기본 프로세스 실행 변수만 허용한다. 필수 추가 변수가 발견되면 임의 확대하지 않고 STOP한다. 외부 네트워크 차단용 OS sandbox는 제공하지 않으며, 등록 action의 오프라인 성질만 검증한다.
- D5 Guard: automation 런타임은 `.claude/hooks/guard.py`를 import하지 않는다. 테스트에서 기존 방식(importlib)을 통해 고정 명령의 Guard 호환성을 검증한다. Guard 판정이 PASS가 아니면 STOP하며 Guard를 수정하지 않는다.
- D6 Evidence: `moneylab.automation.evidence/1` canonical JSON 문자열을 반환한다. 필드는 `schema`, `action_id`, `decision`, `status`, `exit_code`, `duration_ms`, `stdout_sha256`, `stderr_sha256`이다. decision enum은 ALLOW|DENY; status enum은 SUCCEEDED|VALIDATION_FAILED|SOURCE_UNVERIFIED|TIMEOUT|OUTPUT_LIMIT_EXCEEDED|UNEXPECTED_EXIT|DENIED. DENIED는 exit_code·duration_ms·두 해시 모두 null. TIMEOUT과 OUTPUT_LIMIT_EXCEEDED는 exit_code=null; 제한 안에서 수집한 출력 바이트의 SHA-256을 사용하고 수집 바이트가 없으면 빈 바이트의 SHA-256을 사용한다. 출력 상한 초과 시 해시는 상한 내에서 보존된 출력에 대해서만 계산하며 전체 프로세스 출력 해시라고 주장하지 않는다. 다른 실행 결과의 exit_code는 정수이며 해시는 원문 바이트 기준이다. duration_ms는 비음수 정수이며 실행별 가변이므로 결정성 비교에서는 제외한다. stdout/stderr 원문을 Evidence에 포함하거나 파일로 저장하지 않는다. Evidence 생성 실패는 성공으로 위장하지 않는다.
- D7 Isolation: 기존 Supervisor·Knowledge·Execution·Provider·Paper 구현과 스키마를 변경하지 않는다. 신규 패키지는 주문·서명·지갑·네트워크 기능을 import하지 않는다. Git 상태 비교는 참고 증거일 뿐 OS 파일 시스템 격리 증명이 아니다.
- D8 Scope: `supervisor_check`, `automation_selftest`, CLI 진입점, queue, scheduler, 무인 루프, 자동 Gate 승인, Git 변경, LLM 비용 측정·강제는 이번 범위에서 제외한다.
- D9 Policy self-protection: action 정의는 코드의 고정 상수로 유지하며 외부 설정·사용자 문자열로 변경하지 않는다. 동일 프로세스 권한에서 정책 파일의 물리적 수정까지 방지하는 보안 경계는 제공하지 않으므로 이를 보장했다고 주장하지 않는다.

## TEST_GATES

TEST_GATES:
- 신규 정책·Executor·Evidence·Isolation 테스트 모두 통과.
- 미등록 action DENY 시 subprocess 호출 0회; 임의 argv/경로/명령 주입 불가.
- 고정 argv·`shell=False`·timeout·최소 환경변수·Git 경로 검증.
- stdout·stderr 동시 출력에서 누적 1 MiB 상한이 실행 중 강제되는지, 초과 시 OUTPUT_LIMIT_EXCEEDED·exit_code=null이 반환되는지, 프로세스 종료·wait·thread join이 완료되는지 검증. 불가능하면 STOP.
- 0, 1, 3, 2/기타, timeout, 출력 상한 초과 매핑은 fake Popen 및 제한된 실제 자식 프로세스 테스트에서 검증.
- DENIED null 필드, TIMEOUT·OUTPUT_LIMIT_EXCEEDED null exit_code, stdout/stderr SHA-256, canonical JSON 직렬화 검증. 결정성 비교에서는 duration_ms 제외.
- Guard의 고정 명령 판정 PASS 확인. ASK/DENY이면 STOP.
- 외부 네트워크 호출·주문 경로·보호 파일 변경이 없음을 정적·동적 테스트로 검증.
- `python -m mypy src/moneylab/automation` 로컬 명시 실행 통과. 기존 CI의 mypy files 설정에는 신규 패키지가 포함되지 않으므로 CI가 이 검사를 보장한다고 주장하지 않는다.
- 기존 ruff 검사 및 전체 pytest 회귀 통과(failed 0, errors 0).
- `git diff --check`, 변경 파일 집합 = ALLOWED_FILES, PROTECTED diff 0.

## E2E_GATES

E2E_GATES:
- clean commit에서 Python API `run_action('knowledge_validate')`를 실제 1회 실행하고 반환 JSON의 action·status·exit_code·해시가 관측 결과와 일치하는지 확인.
- 미등록 action을 실제 subprocess 호출 없이 DENIED로 처리하는지 확인.
- 종료 코드 0/1/3/기타, timeout 및 출력 상한 초과의 상태 매핑은 fake Popen 단위 테스트와 제한된 실제 자식 프로세스 테스트에서 검증하며 실제 Knowledge E2E에서 모든 코드를 재현할 것을 요구하지 않는다.
- 기존 tracked·보호·연구 데이터 변경 0. 기존 ignored·untracked 산출물 보존.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base/C1/구현 commit SHA·tree, Work Order SHA-256, 변경 파일 집합, 보호 파일 diff, 병합 parent·tree.
- CLAUDE_REPORTED: S0, 테스트·ruff·mypy·E2E 결과, 실제 명령·종료 코드.
- INDEPENDENT: GitHub PR CI 결과 및 사용자·독립 확인 결과.

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, HEAD, parent, tree.
- 변경 파일 집합, PROTECTED diff, worktree clean, `git diff --check`.
- 증거 등급, DEVIATIONS, ISSUES, PROPOSED_ERRATA.
- `<GATE>_PASS = YES/NO`, `READY_FOR_<NEXT_GATE> = YES/NO`.
- 보고는 채팅 및 승인된 PR 본문으로만 하고 신규 보고 파일을 만들지 않는다.

## STOP_CONDITIONS

STOP_CONDITIONS:
- 원격 main base SHA/tree 불일치, 대상 branch/worktree 기존 존재, Work Order 원문 해시·크기·줄 수 불일치.
- S0 실패, 모든 도구 호출 차단, guard DENY, 권한 거절, 예상하지 못한 ASK.
- ALLOWED_FILES 밖 tracked 변경, PROTECTED diff, 예기치 않은 untracked 파일, 계약 모순.
- 패키지 임의 설치 필요, 의존성·환경 불일치, Git 경로 확인 실패.
- 명령 주입·임의 argv 실행 가능, 출력 상한 강제 실패, 예상 밖 네트워크 접근 발견.
- Evidence 비밀정보 포함, 테스트 실패·오류, hard gate 불일치.
- 기존 branch·worktree·ignored·untracked·reference 산출물 보존 위반.
