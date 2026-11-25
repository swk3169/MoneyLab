# Work Order: AUTO-08-CONTROLLED-READ — ECON-FWD-M20 승인 본문 식별값 계산 제한 CLI

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/AUTO-08-CONTROLLED-READ/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: AUTO-08-CONTROLLED-READ
TASK_ID: AUTO-08-CONTROLLED-READ
TITLE: 지정 세션 항목의 ECON-FWD-M20 승인 본문을 고정 프로필로 추출해 SHA-256·바이트·LF를 계산하는 제한 CLI
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: b13b3a24fce7c5ad634208bd7ed6660cdce2882d
CANONICAL_BASE_TREE: c960df50eef37419968ca34d690c3a0413c89cf8
BASE_EVIDENCE: ChatGPT가 로컬 Git 객체와 그 커밋의 CI 설정을 읽어 확인한 값이다(INDEPENDENT). 현재 원격 상태를 새로 확인한 값이 아니다. WORKSPACE_SETUP의 승인된 원격 확인에서 다르면 STOP한다.
TARGET_BRANCH: codex/auto-08-controlled-read
TARGET_WORKTREE: C:/MoneyLab-auto-08
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: pytest
BUNDLE_ELIGIBLE: NO
BUNDLE_MAX_RANGE: NONE
FILE_FORMAT: ALLOWED_FILES는 UTF-8, BOM 없음, LF, 끝 LF 1개, 탭·U+00A0·줄 끝 공백 없음. 시험 코드 안의 합성 입력 문자열 리터럴은 이스케이프로 표현한다.

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: AUTO-08-CONTROLLED-READ <GATE> WO@<commit>`)
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend. COMMIT 이후의 수정은 자동으로 하지 않는다.
- no skipping
- 이 task는 guard 변경을 포함하므로 BUNDLE_AUTHORIZATION을 어느 구간에도 쓰지 않는다. 모든 gate는 개별 Gate Authorization이 필요하다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다.

## GOAL

GOAL: 사용자가 채팅으로 승인한 세션 항목 1건에서, ECON-FWD-M20 전용 고정 프로필로 승인 본문을 추출하고 SHA-256·바이트 수·LF 수를 계산하는 제한 CLI와 비권위 감사 기록을 구현한다. 범위는 구현과 합성 시험 검증까지다. 실제 세션 처리, 현재 승인 원문의 발행 계산, 실사용 준비 완료 선언은 범위 밖이다.

## BACKGROUND

BACKGROUND:
- protected 경로를 언급한 Bash 텍스트가 guard의 PROTECTED+MUTATE 규칙에 걸려 승인 본문 식별값 계산이 DENY로 중단되었다(기록 보존).
- moneylab.automation(AUTO-01)은 호출자 인자를 받지 않는 고정 동작이고, moneylab.runlog(AUTO-03)는 automation.evidence/1만 받는다. 이 task는 두 API를 바꾸지 않고 automation 실행기와 연동하지 않는다.
- 재사용하는 공통 함수: moneylab.workstate.collect.check_tree_path, is_link_like, run_git, moneylab.storage.atomic.atomic_create_new_bytes. 재사용은 함수 호출이며 실행기 연동이 아니다.
- 정규화 규칙의 근거: 기존 대화에서 승인된 규칙. Work Order 문안은 CRLF만 LF로 바꾸고 길이 0인 바깥 빈 줄만 제외하며 끝 LF는 정확히 1개다. 사전등록 문안은 수락된 최종 도구 출력의 FINAL BODY BEGIN/END 사이를 쓰고, CRLF만 LF로 바꾸며, 마지막 본문 줄바꿈을 포함한다.
- 표식 문자열은 사용자가 대화에서 제시한 값이다.
- 확인된 base 환경(GIT_VERIFIABLE): requirements-dev.txt에 ruff==0.17.2, mypy==2.4.0. pyproject.toml에 [tool.ruff.lint], [tool.mypy], requires-python ">=3.12".

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: 하위 단계 셋을 순서대로 하고, 단계마다 보고 후 멈춘다.
  - (1) WORKTREE_CREATION
    - 승인된 `git fetch origin main` 1회.
    - `git rev-parse origin/main` = CANONICAL_BASE_SHA이고 `git rev-parse origin/main^{tree}` = CANONICAL_BASE_TREE인지 확인한다.
    - base에서 다음을 확인한다: ALLOWED_FILES의 A 경로는 모두 없고 M 경로는 모두 있다; src/moneylab/workstate/collect.py에 check_tree_path·is_link_like·run_git가 정의되어 있고 GIT_SUBCOMMANDS에 rev-parse·check-ignore가 있다; src/moneylab/storage/atomic.py에 atomic_create_new_bytes가 있다.
    - `git worktree add -b codex/auto-08-controlled-read C:/MoneyLab-auto-08 b13b3a24fce7c5ad634208bd7ed6660cdce2882d`. 경로나 branch가 이미 있으면 STOP.
  - (2) C1_CREATION
    - 전제: C1 작성 전에 정확한 최종 정본과 그 SHA-256·바이트 수·LF 수가 사용자에게 제시되고 수락되어 있어야 한다. 수락된 값은 Gate Authorization에 적는다. 이 전제가 없으면 작성하지 않는다.
    - Write 도구로 docs/tasks/AUTO-08-CONTROLLED-READ/WORK_ORDER.md를 수락된 정본 그대로 최초 1회 작성한다.
    - 작성 파일의 SHA-256·바이트·LF를 수락값과 대조한다.
    - `git add -- docs/tasks/AUTO-08-CONTROLLED-READ/WORK_ORDER.md`, staged blob 내용의 SHA-256 대조.
    - `git commit -m "docs(task): add AUTO-08-CONTROLLED-READ work order"`(본문·trailer 없음), commit blob 내용의 SHA-256 대조.
    - C1 SHA·parent·tree와 세 대조 결과를 보고한다.
    - 어느 대조든 다르면 STOP하고, 남은 파일·index·커밋을 보존한다. 삭제·덮어쓰기·자동 재시도·복구는 사전 승인되지 않으며, 실제 불일치가 생긴 뒤 별도로 결정한다.
  - (3) ENVIRONMENT_SETUP(별도 승인)
    - TARGET_WORKTREE에서 `C:/Users/USER/AppData/Local/Programs/Python/Python314/python.exe --version`. 3.14.x가 아니면 설치·경로 변경 없이 STOP.
    - `C:/Users/USER/AppData/Local/Programs/Python/Python314/python.exe -m venv .venv`
    - `.venv/Scripts/python.exe -m pip install -r requirements-dev.txt`
    - `.venv/Scripts/python.exe -m pip install -e . --no-deps`
    - `.venv/Scripts/python.exe --version`(3.14.x)
    - `.venv/Scripts/python.exe -m ruff --version`(0.17.2)
    - `.venv/Scripts/python.exe -m mypy --version`(2.4.0)
    - 다르면 STOP. 다른 worktree의 .venv는 바꾸지 않는다.
- IMPLEMENTATION: ALLOWED_FILES 생성·수정, CHECK_COMMANDS 실행.
  - 예산 안에서 계속하는 경우: 승인 범위 안의 일반적인 코드·시험 수정과 재검사. 예산은 수정 반복 5회, 전체 pytest 3회, 같은 실패 2회 연속까지.
  - 즉시 STOP하는 경우: guard DENY, 권한 거절, 권한 충족 여부 불명, ALLOWED_FILES 밖 변경, PROTECTED 위반, ALLOWED_FILES 밖 기존 시험의 회귀, 계약 모순.
- PRECOMMIT_AUDIT: 읽기와 감사만.
  - 기준선 대비 다음을 `.venv/Scripts/python.exe -m pytest --collect-only -q`와 `git diff`로 확인한다: 수집 테스트 ID 감소, 테스트 삭제, skip·skipif·xfail·pytest.skip(·pytest.xfail( 추가, ALLOWED_FILES 밖 테스트 변경.
  - 단정 완화·허용 목록 확대·mock 우회는 판정할 수 없으므로 "독립 검토 필요"로 보고한다.
- COMMIT
  - stage: 아래 15개 경로를 명시한 `git add --` 한 번.
    - src/moneylab/controlled_read/__init__.py
    - src/moneylab/controlled_read/__main__.py
    - src/moneylab/controlled_read/profiles.py
    - src/moneylab/controlled_read/selector.py
    - src/moneylab/controlled_read/transcript.py
    - src/moneylab/controlled_read/store.py
    - tests/test_controlled_read_profiles.py
    - tests/test_controlled_read_selector.py
    - tests/test_controlled_read_transcript.py
    - tests/test_controlled_read_store.py
    - tests/test_controlled_read_cli.py
    - tests/test_controlled_read_isolation.py
    - .claude/hooks/guard.py
    - tests/test_agent_guard.py
    - docs/agent_workflow.md
  - `git commit -m "feat(automation): add AUTO-08 controlled read CLI"`(본문·trailer 없음). 커밋 1회.
- CLEAN_COMMIT_E2E: E2E_GATES 실행, ignored 출력만
- PUSH: `git push -u origin codex/auto-08-controlled-read` 1회
- PR_CI: README §13에 따른다. 필수 check는 pytest다.
- MERGE: README §13에 따른다. merge commit만 쓴다.
- POST_MERGE_AUDIT: `git fetch origin main` 1회. merge commit의 parent·tree와 ALLOWED_FILES ∪ docs/tasks/AUTO-08-CONTROLLED-READ/** 구조를 감사한다.
- COMPLETE: 최종 보고. "도구 구현과 합성 시험 검증 완료"로만 적는다. 실사용 준비 완료나 현재 승인 원문의 발행 계산 완료를 선언하지 않는다.

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
- .claude/settings.json·hook 등록 변경, guard 우회. .claude/hooks/guard.py는 DESIGN_CONTRACT D13 내용으로만 바꾼다
- 다른 branch·worktree·untracked·ignored·reference 산출물 정리·삭제·덮어쓰기
- C1 불일치 뒤의 파일·index·커밋 삭제·덮어쓰기·재시도
- 실제 세션 기록(사용자 home 아래 .claude/projects/**)의 열람·처리. 구현, 시험, E2E 모두 해당
- data/** 읽기·변경·삭제(OUTPUTS 예외는 이 task의 실행에서 쓰지 않는다)
- 연구 branch·worktree(codex/econ-screen-v06-03-run, C:/MoneyLab-futval-v8-01-precheck 등)의 변경·병합·정리·공개 백업
- 발행 바이트 계산, 실제 승인 원문의 식별값 계산, 최초 실제 사용
- 임의 Python·셸을 허용하는 guard 예외, protected-text ASK 예외
- 다른 문서용 프로필·표식의 추가나 자동 추정
- moneylab.automation·moneylab.runlog·moneylab.providers import, automation 실행기와의 연동
- pyproject.toml의 mypy·ruff 설정 변경
- Python 설치·경로 변경
- 네트워크 사용. 단 WORKSPACE_SETUP(1)·POST_MERGE_AUDIT의 main fetch, PUSH, §13 gh 호출, ENVIRONMENT_SETUP의 pip 설치는 예외

## ALLOWED_FILES

ALLOWED_FILES:
- A src/moneylab/controlled_read/__init__.py
- A src/moneylab/controlled_read/__main__.py
- A src/moneylab/controlled_read/profiles.py
- A src/moneylab/controlled_read/selector.py
- A src/moneylab/controlled_read/transcript.py
- A src/moneylab/controlled_read/store.py
- A tests/test_controlled_read_profiles.py
- A tests/test_controlled_read_selector.py
- A tests/test_controlled_read_transcript.py
- A tests/test_controlled_read_store.py
- A tests/test_controlled_read_cli.py
- A tests/test_controlled_read_isolation.py
- M .claude/hooks/guard.py
- M tests/test_agent_guard.py
- M docs/agent_workflow.md

ALLOWED_FILES_COUNT: 15 (A 12, M 3). COMMIT의 stage 대상과 같다. C1은 docs/tasks/AUTO-08-CONTROLLED-READ/WORK_ORDER.md 1개만 담는 별도 커밋이다.

## OUTPUTS

OUTPUTS:
- 운영 출력(이 task의 시험·E2E에서는 생성하지 않음): data/processed/controlled_read/<TASK_ID>/<NNN>/intent.json, data/processed/controlled_read/<TASK_ID>/<NNN>/result.json. ignored 경로에 create-new로 최초 생성만 허용하고 교체·삭제는 금지한다.
- 시험·E2E의 출력은 pytest tmp_path 안에서만 만든다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/AUTO-08-CONTROLLED-READ/**
- docs/tasks/**/WORK_ORDER.md
- docs/tasks/**/ERRATA-*.md
- .claude/settings.json
- .claude/skills/**
- .github/**
- CLAUDE.md
- pyproject.toml
- requirements.txt
- requirements-dev.txt
- .gitignore
- .gitattributes
- configs/**
- docs/research_*_preregistration*.md
- knowledge/**
- src/moneylab/automation/**
- src/moneylab/runlog/**
- src/moneylab/workstate/**
- src/moneylab/taskctl/**
- src/moneylab/knowledge/**
- src/moneylab/storage/**
- src/moneylab/providers/**
- tests/test_repo_hygiene.py
- tests/test_skills.py
- tests/test_automation_evidence.py
- tests/test_automation_executor.py
- tests/test_automation_isolation.py
- tests/test_automation_policy.py
- tests/test_runlog_cli.py
- tests/test_runlog_isolation.py
- tests/test_runlog_store.py
- tests/test_workstate_cli.py
- tests/test_workstate_collect.py
- tests/test_workstate_isolation.py
- tests/test_workstate_store.py
- tests/test_taskctl_check.py
- tests/test_taskctl_cli.py
- tests/test_taskctl_lease.py
- tests/test_taskctl_ledger.py
- tests/test_knowledge_context.py
- tests/test_knowledge_query.py
- tests/test_knowledge_seed.py
- tests/test_knowledge_validate.py
- data/** (OUTPUTS의 최초 생성 예외 제외)

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가). 템플릿 기본값 `.claude/**`는 ALLOWED_FILES의 .claude/hooks/guard.py 때문에 .claude/settings.json과 .claude/skills/**로 좁힌다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 범위: 패키지 moneylab.controlled_read. 하위 명령은 run, status 둘이다. 하나의 프로세스 안에서 처리한다. 외부 프로세스는 collect.run_git의 rev-parse(--show-toplevel)와 check-ignore만 쓴다. automation·runlog·providers는 import하지 않고 automation 실행기와 연동하지 않는다. 범용 실행기와 기억 DB는 만들지 않는다.
- D2 CLI 문법: Bash 도구 호출만 지원한다. 토큰 구분자는 ASCII 공백 1개다. 따옴표, 탭, `=` 형태, 축약, 순서 변경, 중복, 추가 토큰은 ARGUMENT_INVALID다.
  - run: `.venv/Scripts/python.exe -B -m moneylab.controlled_read run --task <TASK_ID> --project-key <PROJECT_KEY> --session <SESSION> --selector <SELECTOR> --profile <PROFILE> --attempt <ATTEMPT>`
  - status: `.venv/Scripts/python.exe -B -m moneylab.controlled_read status --task <TASK_ID> --attempt <ATTEMPT>`
  - 값별 허용 문법(Python re.fullmatch, ASCII):
    - 실행 파일 토큰: 리터럴 `.venv/Scripts/python.exe`. `/`와 `.`을 포함한다.
    - 모듈 토큰: 리터럴 `moneylab.controlled_read`
    - TASK_ID: `[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*`, 64자 이하
    - PROJECT_KEY: `[A-Za-z0-9-]{1,200}`. `/`, `\`, `.`, `:`는 없다.
    - SESSION: `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`
    - SELECTOR: `assistant:<SESSION 문법>(?::text:[1-9][0-9]?)?` 또는 `tool_result:[A-Za-z0-9_]{1,128}(?::text:[1-9][0-9]?)?`. `/`는 없다.
    - PROFILE: 리터럴 `ECON-FWD-M20-WO/1` 또는 `ECON-FWD-M20-PREREG/1`. `/`를 포함한다.
    - ATTEMPT: `00[1-9]|0[1-9][0-9]|[1-9][0-9]{2}`
  - cwd: 패키지가 설치된 checkout의 루트. 패키지 위치에서 계산한 `<root>/src/moneylab/controlled_read`가 실제 위치와 같고, root가 `git rev-parse --show-toplevel`과 같아야 한다. 아니면 ENVIRONMENT_INVALID.
  - `-B`는 자동 bytecode 쓰기만 끈다. 쓰기 격리가 아니다.
- D3 승인 형식과 연결: 승인은 채팅 메시지 한 줄이다.
  - 형식: `CONTROLLED_READ_AUTHORIZATION: AUTO-08-CONTROLLED-READ TASK=<TASK_ID> PROJECT_KEY=<PROJECT_KEY> SESSION=<SESSION> SELECTOR=<SELECTOR> PROFILE=<PROFILE> ATTEMPT=<ATTEMPT> EXPIRES_UTC=<YYYY-MM-DDTHH:MM:SSZ>`
  - 메시지 1건이 시도 1회를 승인한다. 호출 전에 Claude는 현재 세션에 사용자가 보낸 원문이 있는지 확인하고, CLI 인자 7개가 각 값과 같은지, 만료 전인지 대조한다. 원문을 확인할 수 없으면 STOP한다.
  - 프로그램은 이 승인을 보지 못하고 인증하지도 못한다. 정규식에 맞는 입력은 승인 증거가 아니다. 이는 절차상 한계다.
  - 기록에는 `approval: "NOT_VERIFIED_BY_PROGRAM"`을 고정 값으로 넣는다.
  - 실패하거나 결과 불명이면 다음 ATTEMPT 번호로 새 승인을 받는다.
  - docs/agent_workflow.md에 이 형식과 한계를 적는다.
- D4 세션 경로: home = Path.home()이고 절대 경로가 아니면 ENVIRONMENT_INVALID. rel = `.claude/projects/<PROJECT_KEY>/<SESSION>.jsonl`.
  - collect.check_tree_path(home, rel, SESSION_PATH_INVALID, require_regular=True)로 각 구성요소의 symlink·junction·reparse point와 일반 파일 여부를 검사한다. 없는 구성요소가 있으면 SESSION_NOT_FOUND.
  - 열기 전 lstat과 연 핸들의 fstat에서 st_size·st_dev·st_ino가 같아야 하며 아니면 SESSION_PATH_INVALID.
  - 디렉터리 목록은 보지 않는다.
  - 한계: home과 그 상위는 검사하지 않는다. Path.home()은 환경변수를 따른다.
- D5 prefix:
  - 열 때 fstat 크기 S0를 얻고 처음 S0바이트까지만 읽는다. 그 안의 마지막 LF까지를 prefix(P바이트)로 삼는다. 그 뒤의 미완성 줄은 바이트 수만 기록한다.
  - 처리 후 [0, P)를 다시 읽어 SHA-256이 같아야 하며 아니면 SESSION_CHANGED. 그 시점 fstat 크기가 P보다 작으면 SESSION_TRUNCATED.
  - prefix 뒤에 줄이 추가된 것은 실패가 아니다.
  - 전체 파일의 원자적 스냅샷이 아니다. 두 읽기 사이에 바뀌었다 되돌아온 변경은 감지하지 못한다.
- D6 JSONL 해석:
  - prefix의 각 줄(LF 제외)은 UTF-8 엄격 디코딩과 엄격 JSON(중복 키·NaN·Infinity·overflow 거부) 파싱을 통과한 JSON 객체여야 하며, 아니면 SESSION_CORRUPT.
  - 대상이 아닌 줄에서는 D7의 식별 필드만 확인하고 내용을 보관하거나 출력하지 않는다. 출력 제한이며 메모리 격리는 아니다.
- D7 지원 구조: 합성 자료로 검증하는 구조이며, 실제 세션 형식과 같은지는 미검증이다. 코드 주석에도 미검증이라고 적는다.
  - 항목 객체: 선택 필드 `uuid`(문자열), `type`(문자열), `message`(객체).
  - 모든 줄에서 `uuid`가 있으면 문자열이어야 하며, 대상 UUID와 같은 `uuid`가 2회 이상이면 ENTRY_DUPLICATE.
  - assistant 대상: `type == "assistant"`, `message.content`는 block 객체의 목록. 각 block은 문자열 `type`을 가지며 값은 {"text","thinking","redacted_thinking","tool_use"} 중 하나다. text block은 문자열 `text`를 가진다.
  - tool_result 탐색: `type == "user"`이고 `message.content`가 목록인 항목의 block 중 `type == "tool_result"`인 것. 이 block은 문자열 `tool_use_id`를 가지며, `content`는 문자열이거나 {"type":"text","text":<문자열>} 객체의 목록이다. 선택 필드 `is_error`는 불리언이다. `message.content`가 문자열인 user 항목에는 tool_result가 없는 것으로 본다.
  - 대상 tool_use_id와 같은 tool_result block이 2개 이상이면 ENTRY_DUPLICATE.
  - 대상 항목이나 block에서 이 구조를 벗어나는 경우는 모두 FORMAT_UNSUPPORTED다: 필드 누락, 타입 불일치, 목록에 없는 block type, tool_result content 목록에 text가 아닌 항목. 추정하거나 변환하지 않는다.
  - 대상이 아닌 user 항목의 content 목록에서 객체가 아니거나 `type`이 문자열이 아닌 항목도 FORMAT_UNSUPPORTED다.
  - UUID로 찾은 항목의 `type`이 assistant가 아니면 SELECTOR_KIND_MISMATCH. `is_error`가 true면 TOOL_RESULT_ERROR.
  - 대상을 찾지 못하면 ENTRY_NOT_FOUND이며 미완성 줄의 바이트 수를 함께 보고한다.
- D8 text block 선택:
  - 후보는 assistant이면 type "text" block들이고, tool_result이면 content가 문자열일 때 그 하나, 목록일 때 그 text 항목들이다.
  - `:text:<k>`가 없으면 후보가 정확히 1개여야 하며, 0개는 TEXT_BLOCK_NOT_FOUND, 2개 이상은 TEXT_BLOCK_AMBIGUOUS.
  - `:text:<k>`가 있으면 k번째(1부터)를 쓰고, 범위 밖이면 TEXT_BLOCK_NOT_FOUND.
  - block은 합치지 않는다. 선택된 text는 표시된 형태 그대로이며, 줄 번호 접두 같은 도구 표시 형식을 제거하지 않는다.
- D9 공통 정규화(두 프로필):
  - (a) 선택된 text를 UTF-8로 인코딩한다. 짝 없는 서로게이트는 ENCODING_INVALID.
  - (b) 첫 문자가 U+FEFF이면 BOM_PRESENT.
  - (c) CRLF(0x0D 0x0A)만 LF로 바꾼다. 그 뒤에 남는 CR은 CR_PRESENT.
  - (d) LF로 줄을 나눈다.
  - (e) 표식: 줄 하나가 프로필의 표식 상수와 바이트 단위로 완전히 같을 때만 표식 줄이다. 앞뒤 공백, 들여쓰기, 대소문자, 따옴표, 다른 문자가 붙은 줄은 표식이 아니며 본문 내용으로 남는다. BEGIN 표식 줄과 END 표식 줄은 각각 정확히 1개이고 BEGIN이 앞이어야 한다. 위반은 MARKER_MISSING, MARKER_DUPLICATE, MARKER_ORDER_INVALID.
  - (f) 본문 내부의 문자·들여쓰기·공백·탭은 바꾸지 않는다. strip하지 않는다.
  - (g) 계산값: sha256 = SHA-256(출력 바이트) 소문자 hex, bytes = 출력 바이트 길이, lf = 출력 바이트의 0x0A 개수.
- D10 프로필 ECON-FWD-M20-WO/1 (version 1). ECON-FWD-M20 고정용 Work Order 원문 전용이다.
  - selector 종류: assistant 또는 tool_result.
  - BEGIN 표식 줄: `-----BEGIN ECON-FWD-M20 WORK ORDER CANDIDATE-----`
  - END 표식 줄: `-----END ECON-FWD-M20 WORK ORDER CANDIDATE-----`
  - 본문 줄 = 두 표식 줄 사이의 줄들. 앞쪽의 연속된 길이 0인 줄과 뒤쪽의 연속된 길이 0인 줄만 제외한다. 공백만 있는 줄과 내부 빈 줄은 유지한다.
  - 출력 = 남은 각 줄 + LF. 끝 LF는 정확히 1개다. 남은 줄이 0개면 BODY_EMPTY.
- D11 프로필 ECON-FWD-M20-PREREG/1 (version 1). ECON-FWD-M20 사전등록의 수락된 최종 도구 출력 전용이다.
  - selector 종류: tool_result만. assistant 선택자면 SELECTOR_KIND_MISMATCH.
  - BEGIN 표식 줄: `===== FINAL BODY BEGIN =====`
  - END 표식 줄: `===== FINAL BODY END =====`
  - 출력 = BEGIN 표식 줄 다음 바이트부터 END 표식 줄 바로 앞까지. 마지막 본문 줄의 LF를 포함하고 빈 줄도 제외하지 않는다. 본문이 0줄이면 BODY_EMPTY.
  - CRLF만 LF로 바꾼 결과가 승인 형식이다.
- D12 한도(초과 시 코드): prefix 64 MiB(SESSION_LIMIT_EXCEEDED), 한 줄 8 MiB(LINE_LIMIT_EXCEEDED), 항목 200000(ENTRY_LIMIT_EXCEEDED), 선택된 text의 UTF-8 2 MiB(TEXT_LIMIT_EXCEEDED), 출력 1 MiB(BODY_LIMIT_EXCEEDED), monotonic 60 s(TIME_LIMIT_EXCEEDED, 줄마다와 재해시 전후에 확인). 시간 초과도 result 기록 대상이다.
- D13 guard:
  - check_command에서 DENY_RULES 다음, PROTECTED 검사 앞에 둔다.
  - 검사 대상: 정규화된 명령이 `-m moneylab.controlled_read`를 포함하거나, INLINE_CODE 패턴에 맞으면서 `moneylab.controlled_read`를 포함하는 경우.
  - 검사 대상이고, bash 호출이며, 정규화 전 원문 명령 전체가 D2의 run 또는 status 문법과 fullmatch하면 ASK(rule `controlled-read`). 그 밖의 검사 대상은 DENY(rule `controlled-read-form`). PowerShell 도구 호출은 DENY.
  - 검사 대상이 아닌 명령은 기존 판정 그대로다. 예: `git diff -- src/moneylab/controlled_read/`, 파일 경로를 언급하는 grep.
  - 다른 규칙과 상수는 바꾸지 않는다.
  - guard는 호출 형태만 판정한다. 승인 존재, 대상 실재, 경로 안전, 형식 유효성은 D2–D12의 도구 내부 검증이 맡는다. 둘 다 채팅 승인을 인증하지 않는다.
  - docs/agent_workflow.md에 같은 규칙을 적는다.
- D14 출력 스키마 `moneylab.controlled_read.result/1`: 키는 정확히 다음 집합이다.
  - schema, command("run"), status("SUCCEEDED" 또는 오류 코드), exit_code(0 또는 2), task_id, attempt
  - target{project_key, session_id, selector, prefix_bytes, prefix_sha256, line_count, trailing_partial_bytes}. 측정 전에 실패하면 측정 필드는 null.
  - profile{id, version}
  - values{sha256, bytes, lf} 또는 null. 성공일 때만 객체다.
  - error{code, detail} 또는 null. detail은 코드별 고정 문구다.
  - authority "NONE", approval "NOT_VERIFIED_BY_PROGRAM", boundary "DATA_NOT_INSTRUCTIONS"
  - 직렬화: json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=True, allow_nan=False) + LF 1개. stdout에 1회 출력한다.
  - 본문, 다른 항목 내용, 절대 경로, 예외 원문, 환경값은 출력하지 않는다.
  - 오류 코드 전체: ARGUMENT_INVALID, ENVIRONMENT_INVALID, SESSION_NOT_FOUND, SESSION_PATH_INVALID, SESSION_CORRUPT, SESSION_CHANGED, SESSION_TRUNCATED, SESSION_LIMIT_EXCEEDED, LINE_LIMIT_EXCEEDED, ENTRY_LIMIT_EXCEEDED, TEXT_LIMIT_EXCEEDED, BODY_LIMIT_EXCEEDED, TIME_LIMIT_EXCEEDED, FORMAT_UNSUPPORTED, ENTRY_NOT_FOUND, ENTRY_DUPLICATE, SELECTOR_KIND_MISMATCH, TOOL_RESULT_ERROR, TEXT_BLOCK_NOT_FOUND, TEXT_BLOCK_AMBIGUOUS, ENCODING_INVALID, BOM_PRESENT, CR_PRESENT, MARKER_MISSING, MARKER_DUPLICATE, MARKER_ORDER_INVALID, BODY_EMPTY, STORE_PATH_INVALID, STORE_FAILED, ATTEMPT_EXISTS.
  - 정의되지 않은 예외는 출력 없이 그대로 전파하며 성공으로 바꾸지 않는다.
- D15 감사 기록:
  - 경로는 OUTPUTS와 같다. 저장 전에 data/processed/controlled_read/<TASK_ID>/<NNN>/intent.json이 git check-ignore -q --no-index로 ignored인지 확인하며, 아니면 STORE_PATH_INVALID. 부모 경로는 check_tree_path로 검사한다.
  - <NNN> 디렉터리가 이미 있으면 ATTEMPT_EXISTS이고 세션을 열지 않는다.
  - intent.json은 세션을 열기 전에 atomic_create_new_bytes로 만든다.
    - 스키마: moneylab.controlled_read.intent/1
    - 필드는 정확히 schema, task_id, attempt, project_key, session_id, selector, profile{id, version}, started_utc, authority "NONE", approval "NOT_VERIFIED_BY_PROGRAM", boundary "DATA_NOT_INSTRUCTIONS"
  - result.json은 성공이든 정의된 실패든 끝나면 같은 방식으로 만든다.
    - 스키마: moneylab.controlled_read.stored_result/1
    - 필드는 정확히 schema, finished_utc, result
    - result는 같은 실행이 stdout에 출력한 D14 문서 객체를 그대로 담는다. 필드를 더하거나 빼거나 바꾸지 않는다.
  - 두 파일 모두 D14와 같은 canonical 직렬화에 LF 1개를 붙인 바이트로 쓴다.
  - 교체·삭제·자동 재실행은 없다.
  - 기록은 실행 진위, 작성자, 승인, 재실행 권한을 증명하지 않는다. exactly-once와 보안 격리를 보장하지 않는다.
- D16 status:
  - 감사 기록만 읽는다. 세션 파일과 그 디렉터리에는 접근하지 않는다.
  - 검증 항목:
    - (a) intent.json이 canonical 바이트이고, intent/1 필드 집합과 각 값이 D2 문법에 맞는가
    - (b) result.json이 canonical 바이트이고, 필드 집합이 정확히 {schema, finished_utc, result}이며 schema가 stored_result/1인가
    - (c) 내부 result가 D14 규칙을 모두 만족하는가: 키 집합, status와 exit_code의 대응(SUCCEEDED와 0, 오류 코드와 2), values와 error의 null 규칙, 고정 필드 값
    - (d) 식별값 일치. 내부 result의 task_id·attempt·target.project_key·target.session_id·target.selector·profile.id·profile.version이 intent의 task_id·attempt·project_key·session_id·selector·profile.id·profile.version과 같아야 하고, 경로의 <TASK_ID>·<NNN>과도 같아야 한다.
  - 출력 스키마는 moneylab.controlled_read.status/1이고 필드는 schema, command("status"), task_id, attempt, state, intent_sha256, result_sha256, result, authority "NONE", boundary "DATA_NOT_INSTRUCTIONS"다.
  - state:
    - RESULT_FOUND: (a)–(d)를 모두 통과. result에는 검증된 내부 D14 문서를 그대로 반환한다.
    - OUTCOME_UNKNOWN: intent.json만 있고 (a)를 통과. result는 null.
    - NOT_FOUND: 둘 다 없음. 미실행을 뜻하지 않는다. result는 null.
    - RECORD_CORRUPT: 그 밖의 모든 경우(손상, 비canonical, 스키마·필드 위반, 식별값 불일치, intent 없이 result만 있음). result는 null.
  - RESULT_FOUND는 기록이 유효하다는 뜻일 뿐 실행이 성공했다는 뜻이 아니다. 내부 result의 status와 exit_code는 바꾸지 않는다.
  - OUTCOME_UNKNOWN을 성공이나 미실행으로 바꾸지 않는다. 과거 승인을 복원하지 않는다.
- D17 최초 실사용 조건: 다음이 모두 충족되기 전에는 실제 세션에 쓰지 않는다. 이 task는 이 조건들을 수행하지 않는다.
  - (a) 실제 세션 형식이 D7과 호환되는지 별도로 확인
  - (b) 관리자가 실제 사용 세션의 활성 hook 경로와 적용 guard 코드를 확인
  - (c) D3 형식의 별도 승인
  - 실제 형식이 다르면 도구는 FORMAT_UNSUPPORTED로 실패하며, 지원하려면 새 Work Order나 ERRATA가 필요하다.

## CHECK_COMMANDS

CHECK_COMMANDS (TARGET_WORKTREE에서, ENVIRONMENT_SETUP 뒤에 실행):
- `.venv/Scripts/python.exe -m ruff check src/moneylab/controlled_read tests/test_controlled_read_profiles.py tests/test_controlled_read_selector.py tests/test_controlled_read_transcript.py tests/test_controlled_read_store.py tests/test_controlled_read_cli.py tests/test_controlled_read_isolation.py`: 위반 0
- `.venv/Scripts/python.exe -m ruff check .claude/hooks/guard.py tests/test_agent_guard.py`: base 대비 새 위반 0. base 결과는 IMPLEMENTATION에서 파일을 바꾸기 전에 같은 명령으로 기록한다.
- `.venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache src/moneylab/controlled_read`: 오류 0. 이것은 경로를 명시한 로컬 검사다. CI의 기존 mypy 검사 범위와는 별개이며, pyproject의 mypy 대상은 바꾸지 않는다.
- `.venv/Scripts/python.exe -m pytest tests/test_controlled_read_profiles.py tests/test_controlled_read_selector.py tests/test_controlled_read_transcript.py tests/test_controlled_read_store.py tests/test_controlled_read_cli.py tests/test_controlled_read_isolation.py tests/test_agent_guard.py -q`
- `.venv/Scripts/python.exe -m pytest -q`: 전체, 최대 3회
- `git diff --check`

## TEST_GATES

TEST_GATES:
- 입력은 모두 시험 코드가 tmp_path에 만드는 합성 JSONL이다. home은 seam으로 주입한다. 실제 home·세션·data/ 접근은 0건이며 open 감시로 확인한다.
- 기대 바이트는 시험 코드에 str 리터럴 + `.encode("utf-8")`로 미리 고정한다. sha256은 hashlib로, bytes·lf는 len·count로 별도 계산해 대조한다.
- 아래에서 WB = `-----BEGIN ECON-FWD-M20 WORK ORDER CANDIDATE-----`, WE = `-----END ECON-FWD-M20 WORK ORDER CANDIDATE-----`, PB = `===== FINAL BODY BEGIN =====`, PE = `===== FINAL BODY END =====`. `+`는 문자열 연결이다.
  - ECON-FWD-M20-PREREG/1 (tool_result의 content 문자열)
    - P1: `"intro\r\n" + PB + "\r\n# T\r\n\r\nline  x\r\n\r\n" + PE + "\r\ntail"` → `"# T\n\nline  x\n\n"`
    - P2: `PB + "\na\rb\n" + PE + "\n"` → CR_PRESENT
    - P3: `PB + "\nsee \"" + PB + "\" here\n" + PE + "\n"` → `"see \"" + PB + "\" here\n"`
    - P4: `PB + " \nx\n" + PE + "\n"` → MARKER_MISSING
    - P5: `PB + "\nx\n" + PB + "\ny\n" + PE + "\n"` → MARKER_DUPLICATE
    - P6: `PE + "\nx\n" + PB + "\n"` → MARKER_ORDER_INVALID
    - P7: `PB + "\n가나\r\n" + PE` → `"가나\n"` (bytes 7, lf 1)
    - P8: `PB + "\n" + PE + "\n"` → BODY_EMPTY
    - P9: `"\ufeff" + PB + "\nx\n" + PE + "\n"` → BOM_PRESENT
    - P10: assistant 선택자 → SELECTOR_KIND_MISMATCH
  - ECON-FWD-M20-WO/1 (assistant text block)
    - W1: `"\n\n" + WB + "\n\n  # 제목\n\tx  \n\n" + WE + "\n\n"` → `"  # 제목\n\tx  \n"`
    - W2: `"\r\n" + WB + "\r\nA\r\n\r\nC\r\n" + WE + "\r\n"` → `"A\n\nC\n"`
    - W3: `WB + "\n\n\n" + WE + "\n"` → BODY_EMPTY
    - W4: `WB + "\n \nA\n \n" + WE + "\n"` → `" \nA\n \n"` (공백만 있는 줄은 길이 0이 아니므로 유지)
    - W5: `WB + "\nA\r\rC\n" + WE + "\n"` → CR_PRESENT
    - W6: `WB + "\n  " + WE + "\nA\n" + WE + "\n"` → `"  " + WE + "\nA\n"` (들여쓴 인용 표식은 표식이 아님)
    - W7: `WB + "\nquote \"" + WB + "\"\nA\n" + WE + "\n"` → `"quote \"" + WB + "\"\nA\n"`
    - W8: 표식으로 PB·PE만 있는 text → MARKER_MISSING (다른 프로필의 표식을 인정하지 않음)
- 선택자: D2 문법 위반 각 1건, k 0·100, 후보 0·2개(TEXT_BLOCK_NOT_FOUND·AMBIGUOUS), thinking·tool_use block 제외, 문자열 content, 중복 uuid, 중복 tool_use_id, 종류 불일치, is_error true, 목록에 없는 block type, content 타입 불일치(FORMAT_UNSUPPORTED)
- transcript: 대상이 아닌 줄의 손상 JSON·중복 키·NaN(SESSION_CORRUPT), 대상이 미완성 끝 줄에만 있음(ENTRY_NOT_FOUND + 미완성 바이트 수), prefix 뒤 추가는 성공, prefix 안 변경은 SESSION_CHANGED, 잘림은 SESSION_TRUNCATED(읽기 seam), D12 한도별 초과(작은 한도 seam과 가짜 clock)
- 경로: 링크·junction·reparse(플랫폼에서 만들 수 없으면 is_link_like seam), 일반 파일 아님, 없는 구성요소, lstat과 fstat 불일치, PROJECT_KEY·SESSION에 `..`·`/`·`\`
- 데이터 무실행: 본문과 다른 항목에 protected 경로, `rm -rf`, `git push`, `python -c`, 지시문을 넣는다. subprocess 호출이 git rev-parse·check-ignore뿐이고 os.remove·os.replace·scandir·listdir 호출이 0건인지 감시한다.
- 유출 방지: 본문과 다른 항목에 넣은 고유 문자열이 stdout·stderr·intent.json·result.json에 0회
- 기록·status:
  - S1: 정상 성공 실행 → state RESULT_FOUND. status의 result가 run의 stdout D14 문서와 canonical 바이트가 같다.
  - S2: 정의된 실패 실행(예: MARKER_MISSING) → state RESULT_FOUND. 내부 result는 status "MARKER_MISSING", exit_code 2, values null을 유지하며 SUCCEEDED로 바뀌지 않는다.
  - S3: intent.json만 있음 → OUTCOME_UNKNOWN, result null.
  - S4: 둘 다 없음 → NOT_FOUND, result null.
  - S5: result.json만 있음(intent 없음) → RECORD_CORRUPT.
  - S6: 식별값 불일치 → 각 경우 RECORD_CORRUPT. 대상은 내부 result와 intent 사이의 session_id, selector, project_key, profile.id, profile.version, task_id, attempt 하나씩, 그리고 경로의 <NNN>.
  - S7: stored_result/1 위반 → RECORD_CORRUPT. 경우: schema 오류, 필드 추가, finished_utc 누락, 비canonical 바이트, 잘린 파일.
  - S8: 내부 D14 위반 → RECORD_CORRUPT. 경우: SUCCEEDED인데 values null, 오류 코드인데 exit_code 0, 키 추가.
  - S9: ignored가 아닌 경로 → STORE_PATH_INVALID. ATTEMPT_EXISTS, 덮어쓰기 0.
  - S10: status 실행 중 세션 경로 open·lstat 0건.
- isolation: moneylab.automation·runlog·providers가 sys.modules에 로드되지 않음, 직렬화가 같은 인자의 json.dumps와 바이트 동일
- guard: run·status 정확 형태(두 PROFILE 리터럴 각각)는 ASK. 옵션 순서 변경, `--task=X`, 따옴표, 탭, `;`·`&&`·`|`·`>`, 추가 토큰, 다른 실행 파일 경로, 등록되지 않은 PROFILE, `python -c "import moneylab.controlled_read"`, PowerShell 호출은 DENY. `git diff -- src/moneylab/controlled_read/`와 grep은 controlled-read 규칙에 걸리지 않음. 기존 tests/test_agent_guard.py 사례(strict xfail 포함)는 삭제·완화 없이 유지
- 기존 automation·runlog·workstate·taskctl·knowledge 시험이 변경 없이 통과
- 전체 pytest, failed 0 / errors 0
- `git diff --check` 깨끗함, 변경 파일 집합 = ALLOWED_FILES 15개, FILE_FORMAT 충족

## E2E_GATES

E2E_GATES:
- COMMIT 커밋을 새로 checkout한 clean 상태(TARGET_WORKTREE, `git status --porcelain --untracked-files=all` 출력 0줄)에서 CHECK_COMMANDS의 targeted pytest를 다시 실행해 통과를 확인한다.
- 실제 home·세션·data/processed를 대상으로 CLI를 실행하지 않는다.
- 합성 시험 통과는 도구 구현 검증이다. 현재 승인 원문의 발행 계산 완료나 실사용 준비 완료가 아니다.

## PRESERVATION_CHECKS

PRESERVATION_CHECKS:
- WORKSPACE_SETUP 전과 COMPLETE 전에 `git worktree list --porcelain`을 기록하고 비교한다. TARGET_WORKTREE 추가 외의 차이가 없어야 한다.
- C:/MoneyLab-futval-v8-01-precheck의 HEAD = bc1d102d0e5b5d038cbb4199603c6a1c047349e5, branch codex/econ-screen-v06-03-run, `git status --porcelain` 0줄이 처음과 끝에 같아야 한다. 이 확인은 읽기만 한다.
- TARGET_WORKTREE의 `git status --porcelain --ignored`에서 ENVIRONMENT_SETUP 뒤의 ignored 항목 집합(.venv 등)이 COMPLETE 전까지 줄지 않아야 한다.
- C1 불일치로 STOP한 경우 남은 파일·index·커밋을 그대로 둔다.
- 다른 worktree·branch·data/·기존 실행 출력에는 쓰기 명령을 실행하지 않는다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base SHA·tree, C1·구현 커밋 SHA·parent·tree, Work Order 파일·staged blob·commit blob의 SHA-256(Git 객체에서 누구나 다시 계산할 수 있음), 커밋 파일 집합, PROTECTED diff 0, merge parent·tree, base requirements-dev.txt의 ruff·mypy 버전
- CLAUDE_REPORTED: Claude가 계산한 파일·blob 해시와 대조 결과, Python·ruff·mypy 버전 출력, ruff·mypy·pytest 결과와 수, guard 판정표, E2E 결과, 승인 창 관찰
- USER_APPROVAL(사용자 승인): C1 최종 정본과 그 SHA-256·바이트·LF 발행값의 수락. 이것은 승인 기록이다. 바이트 계산이나 내용의 독립 검증이 끝났다는 증거로 분류하지 않는다.
- INDEPENDENT: ChatGPT가 로컬 Git 객체와 CI 설정으로 확인한 BASE 값(현재 원격 상태가 아님), PR CI pytest 결과, 사용자가 확인한 GitHub 화면

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 관찰된 승인 창과 EXPECTED_ASK의 대조, 권한 충족 확인 여부
- PRESERVATION_CHECKS 결과
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

EXPECTED_ASK (관측 기대이며 실제로 뜬다는 보장은 없다):
- Write docs/tasks/AUTO-08-CONTROLLED-READ/WORK_ORDER.md (guard task-contract)
- Edit .claude/hooks/guard.py (settings `Edit(/.claude/**)`, guard protected-edit)
- Edit tests/test_agent_guard.py (guard protected-edit)
- Edit docs/agent_workflow.md (guard protected-edit)
- pip install (guard deps)
- git commit 2회(C1, 구현), git push 1회, §13 gh 호출

EXPECTED_ASK 규칙:
- 목록에 없는 ASK가 나타나면 STOP한다.
- 기대한 창이 뜨지 않았다는 사실만으로 DEVIATION을 확정하지 않는다.
- 그 호출에 필요한 권한이 충족되었는지 확인할 수 없으면 결과 불명으로 STOP하고, 관찰 사실과 미확인 사항을 나눠 보고한다.

## STOP_CONDITIONS

STOP_CONDITIONS:
- 원격 main·tree ≠ CANONICAL_BASE_SHA·CANONICAL_BASE_TREE, base·HEAD·tree 불일치, Work Order sha256 불일치
- C1 정본·SHA-256·바이트·LF의 사용자 수락 없음, 작성 파일·staged blob·commit blob이 수락값과 다름(보존하고 별도 결정을 기다림)
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기와 base 불일치, base에 D1·D4·D15가 쓰는 공통 함수가 없음
- Python 3.14.x·ruff 0.17.2·mypy 2.4.0 확인 실패(설치·경로 변경 없이 STOP)
- guard deny, 권한 창 거절, 예상 밖 ASK, 권한 충족 여부 불명
- ALLOWED_FILES 밖 기존 시험의 회귀, 예산 초과(수정 반복 5회, 전체 pytest 3회, 같은 실패 2회 연속), COMMIT 이후의 모든 실패
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일, PRESERVATION_CHECKS 불일치
- 실제 세션 기록·data/** 접근이 필요해짐, D17 충족 전 실사용 요청
