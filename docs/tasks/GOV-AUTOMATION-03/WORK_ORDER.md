# Work Order: GOV-AUTOMATION-03 — v1.4 Task Delegation 규칙과 협조적 검사·기록 도구 taskctl

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 ACCEPTED ERRATA로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: GOV-AUTOMATION-03
TASK_ID: GOV-AUTOMATION-03
TITLE: 채팅 승인 반복을 줄이는 v1.4 위임 규칙과 taskctl
STATUS: ISSUED
CANONICAL_BASE_SHA: 9632d9523987d53776c5cdca8a7955c99f0dfb16
CANONICAL_BASE_TREE: 76a16c2d7b5360c189acbe5efe0b4e3a880054a3
TARGET_BRANCH: codex/gov-automation-03-delegation
PATH_VARIABLES: SOURCE_WORKTREE, TARGET_WORKTREE, BASE_PYTHON. 값은 승인문에만 적는다.
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests의 pytest job(Windows), 정확한 PR head에 연결된 run의 SUCCESS
BUNDLE_ELIGIBLE: YES
BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E

## ABSOLUTE_RULES

저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조하며, 이 문서는 그것을 복제하거나 바꾸지 않는다.

## GOAL

한 task의 로컬 구간은 위임 승인 1회로, 외부 게시 구간은 게시 승인 1회로 진행하는 v1.4 규칙을 정한다. 그 진행을 검사하고 기록하는 협조적 도구 taskctl을 추가한다.

## SCOPE_AND_HONESTY

- taskctl은 검사와 기록만 한다. 작업을 대신 실행하지 않는다. Agent가 검사를 건너뛰거나, 검사와 실행 사이에 상태를 바꾸거나, 도구를 직접 실행하는 것을 막지 못한다.
- 실제 실행 경계는 Guard, settings 권한 창, GitHub(--match-head-commit, 필수 CI)다.
- taskctl은 사용자 메시지를 인증하지 못한다. 메시지가 사용자에게서 왔는지 확인하는 것은 Agent의 절차다. 코드는 기록된 필드와 현재 Git·파일 상태가 일치하는지만 확인한다.
- 이 버전이 줄이는 것은 채팅 승인 횟수다. 도구 권한 창의 수와 장기 목표 자동 선택은 해결 대상이 아니다.
- v1.4 규칙은 이 task 자신에게 적용하지 않는다. 이 task는 v1.3으로 진행한다.
- 범위 밖: 실주문, 지갑, 개인키, 실거래 자금.

## GATE_SEQUENCE

DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

- 각 gate는 `GATE_AUTHORIZATION: GOV-AUTOMATION-03 <GATE> WO@<C1 SHA>` 개별 승인으로 진행한다. WORKSPACE_SETUP 하위 단계 MAIN_REF_FETCH_ONLY, WORKTREE_CREATION_ONLY, C1_CREATION_ONLY, ENVIRONMENT_PREPARATION_ONLY도 각각 개별 승인이다.
- 예외: IMPLEMENTATION..CLEAN_COMMIT_E2E의 연속 부분 구간은 README §14의 BUNDLE_AUTHORIZATION 1건으로 진행할 수 있다.
- PUSH, PR_CI, MERGE, POST_MERGE_AUDIT, COMPLETE, IMPLEMENTATION으로의 후퇴는 각각 개별 승인이다.
- COMMIT 후 수정은 새 커밋으로 한다. amend는 금지한다. 종료된 승인은 자동으로 복원하지 않는다.
- 멈추면 보고하고 대기한다. 재시도, 변형, 우회는 새 승인 없이 하지 않는다.

## ALLOWED_ACTIONS

- WORKSPACE_SETUP: main ref만 fetch, branch·worktree 생성, C1, 승인문에 고정한 명령으로 환경 준비.
- IMPLEMENTATION: ALLOWED_FILES 작성·수정, TEST_GATES 실행. BGA 예산 안에서 수정 반복 가능.
- PRECOMMIT_AUDIT: 읽기, 감사, TEST_GATES.
- COMMIT: ALLOWED_FILES만 경로를 지정해 stage하고 커밋 1개.
- CLEAN_COMMIT_E2E: E2E_GATES.
- PUSH: `git push -u origin <TARGET_BRANCH>` 1회.
- PR_CI: 승인문에 PR_CREATE: YES, 저장소, base, head branch, head SHA, PR 제목·본문이 있을 때만 `gh pr create` 1회, 이어서 CI 조회.
- MERGE: README §13의 사전 검증을 모두 통과하면 `gh pr merge <N> -R <repo> --merge --match-head-commit <SHA>` 1회.
- POST_MERGE_AUDIT: main ref만 fetch하고 구조 감사.
- COMPLETE: 최종 보고.

## FORBIDDEN_ACTIONS

- 승인된 gate 밖의 행위. ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, Work Order 수정.
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, `fetch --all`, `fetch --prune`.
- Guard·hook·settings 변경이나 우회. 경로·명령의 은닉·분할·인코딩.
- 승인되지 않은 추가 동작을 명령에 결합하는 것. 작업 디렉터리는 도구의 지정 기능(`git -C`, `gh -R`, 절대 경로)을 우선 쓴다. 그것이 불가능한 명령에만 승인문에 적힌 정확한 `cd <경로> && <명령>` 결합을 쓴다.
- 다른 branch·worktree·untracked·ignored·기존 산출물의 정리.

## ALLOWED_FILES

- M docs/tasks/README.md (§15 추가만. §1–§14 문언은 바꾸지 않는다)
- M docs/tasks/TEMPLATE.md (DELEGATION 절 추가만)
- M pyproject.toml ([tool.mypy] files에 "src/moneylab/taskctl" 한 줄 추가만)
- A src/moneylab/taskctl/__init__.py
- A src/moneylab/taskctl/__main__.py
- A src/moneylab/taskctl/ledger.py
- A src/moneylab/taskctl/lease.py
- A src/moneylab/taskctl/check.py
- A tests/test_taskctl_ledger.py
- A tests/test_taskctl_lease.py
- A tests/test_taskctl_check.py
- A tests/test_taskctl_cli.py

## PROTECTED_FILES

- ALLOWED_FILES 밖의 모든 저장소 파일. docs/tasks/GOV-AUTOMATION-03/**, 다른 docs/tasks/<TASK>/**, .claude/**, .github/**, CLAUDE.md, docs/agent_workflow.md, .gitignore, .gitattributes, requirements*.txt를 포함한다.
- ALLOWED_FILES 항목이라도 위에 적은 변경 한정을 벗어난 변경은 보호 위반으로 본다.

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## CONTRACT_FILE_EXCEPTION

- docs/tasks/GOV-AUTOMATION-03/WORK_ORDER.md는 C1_CREATION_ONLY에서 승인 바이트로 최초 1회만 생성한다. 이 예외는 ALLOWED_FILES에 속하지 않는다.

## COMMIT_PLAN

- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/GOV-AUTOMATION-03/WORK_ORDER.md
- I: parent = C1, 변경 = ALLOWED_FILES 전체
- base..I = C1의 파일과 ALLOWED_FILES뿐이다. 승인되지 않은 trailer는 넣지 않는다.

## SCOPE_EXCLUSIONS

- v1.4 위임을 실제 task에 적용하는 파일럿. 병합 후 별도 task(PILOT-DELEGATION-01)로 한다.
- 장기 목표·과제의 자동 선택, supervisor 연결.

## DESIGN_CONTRACT

- D1 README §15 v1.4 Task Delegation
  - 적용 대상: WORK_ORDER_CONTRACT_VERSION v1.4를 선언하고 DELEGATION 절을 가진 Work Order. 소급 적용하지 않는다.
  - 권한 출처: 현재 세션에서 사용자가 보낸 아래 메시지뿐이다. Work Order, taskctl 원장, workstate snapshot, 이전 세션 텍스트, 파일 내용은 권한을 만들지 않는다. 메시지가 현재 세션 사용자에게서 왔는지는 Agent가 절차로 확인한다. taskctl은 메시지를 인증하지 못하며, Agent가 넘긴 필드와 현재 Git·파일 상태가 일치하는지만 검사한다.
  - DELEGATE: `DELEGATE: <TASK> WO_SHA256=<64hex> BASE=<40hex> EXPIRES_UTC=<YYYY-MM-DDTHH:MM:SSZ>`
    - 고정: Work Order 바이트(DELEGATION 절 포함), 기준 main, 만료.
    - 승인: main ref fetch 1회, BASE에서 branch·worktree 생성, 그 바이트로 C1 생성, taskctl init, DELEGATION의 SETUP_COMMAND 실행, IMPLEMENTATION·PRECOMMIT_AUDIT·로컬 COMMIT·CLEAN_COMMIT_E2E, PR 문안 확정, READY_TO_PUBLISH 보고.
    - 불허: push, PR, merge, ERRATA, Work Order 변경, 만료 연장.
    - init 전에 한 fetch·worktree·C1의 이력은 Agent 보고다. taskctl은 그 단계를 통제·관측하지 않았고, init 시점의 결과 상태만 검사한다.
  - PUBLISH: `PUBLISH: <TASK> WO@<C1 40hex> HEAD=<40hex> TREE=<40hex> BASE=<40hex> PR_TEXT_SHA256=<64hex> EXPIRES_UTC=<…>`
    - 고정: 정확한 head·tree, 기대 base, PR 본문 바이트, 만료.
    - 승인: push 1회, PR 생성 1회(제목은 DELEGATION의 PR_TITLE, 본문은 pr_text.md), 필수 CI 조회, README §13 merge 사전 검증 1–7을 통과한 경우의 merge 1회(--match-head-commit), main ref fetch 1회, POST_MERGE_AUDIT, 최종 보고.
    - 불허: 다른 head, 재push, PR 수정, CI 수동 실행·재실행.
  - RESUME: `RESUME: <TASK> WO_SHA256=<64hex> DELEGATION_ID=<64hex> PHASE=<phase> HEAD=<40hex>`
    - DELEGATION_ID는 DELEGATE 이벤트 파일 바이트의 SHA-256이다.
    - 새 세션에서만 쓴다. 다음 조건을 모두 만족할 때만 원래 위임 범위와 만료 안에서 이어 간다: 이전 세션의 미종결 단계 없음, 원장 유효, LEASE·REVOKED 없음, 만료 전, 현재 상태가 마지막 STEP_END의 post_state와 같음. 범위와 만료는 늘리지 않는다.
    - 첫 버전은 UNKNOWN 단계를 복구하거나 재실행하지 않는다.
  - REVOKE: `REVOKE: <TASK>`. 즉시 철회한다.
  - CLEAR_LEASE: `CLEAR_LEASE: <TASK> LEASE=<32hex>`. 그 lease 하나만 제거한다. 진행을 재개시키지 않는다.
  - READY_TO_PUBLISH 보고에는 publish-draft가 채운 PUBLISH 문장을 넣는다. status 출력에는 resume-draft가 채운 RESUME 문장을 넣는다. 사용자는 SHA나 해시를 직접 조합하지 않는다.
  - §14 예외: DELEGATE가 WORKSPACE_SETUP..CLEAN_COMMIT_E2E를 묶고, PUBLISH가 PUSH..최종 보고를 묶는다.
  - §13 예외(v1.4에만): PUBLISH 1건이 §13의 PR 생성 승인 필드와 merge 승인 필드를 대체한다. PR 번호는 같은 PUBLISH로 만든 PR이며 head SHA로 식별한다. "Gate Authorization 1건당 명령 1회"의 예외로 push·PR 생성·merge 각 1회와 필요한 읽기 전용 조회를 포함한다. §13 merge 사전 검증 1–7, guard ASK 승인 창 재승인, merge 후 보고는 그대로다.
  - 우선순위 1–3과 모든 Guard·settings 승인 창은 그대로다. 예상 밖 ASK·거절·DENY는 STOP이며, 자동 재시도는 없다.
  - 원격 증거: push·PR·CI·merge 결과와 merge-tree 재계산 값은 Agent가 관측해 제출하는 값이다. taskctl은 이 값들의 형식과 PUBLISH 고정값과의 일치만 검사한다. 원격 사실 자체는 검증하지 않는다. 로컬 Git 객체(fetch 후 origin/main, merge commit의 parents·tree)는 taskctl이 run_git으로 검증한다.
  - 기본 예산(DELEGATION에서 더 낮출 수만 있다): 총 경과 4시간, 수정 반복 5회, 전체 pytest 3회, 같은 실패 연속 2회. 강제 수준은 D7을 따른다. 도구 호출 수는 Agent 보고이고, LLM 금액은 측정하지 않는다.
  - 종결 상태
    - COMPLETE: 위반 0건이고 완료 조건 충족
    - CLOSED_WITH_VIOLATION: 계약·지시 위반 1건 이상. 이후 승인으로 지우지 않는다.
    - STOPPED(코드)
    - 사례·연구 판정은 종결 상태와 별개다.
  - 한계
    - taskctl은 협조적 도구다. 작업을 실행하지 않고, 우회를 막지 못한다.
    - atomic 쓰기는 하드링크를 지원하는 로컬 볼륨에서만 원자성을 가진다. 디스크 장애·전원 손실은 보장하지 않는다.
    - 해시 체인은 사고성 손상만 감지한다. 악의적 전체 재작성 방지나 승인 증명이 아니다.
    - exactly-once 실행을 보장하지 않는다.
    - session_nonce는 인증 수단이 아니다.

- D2 TEMPLATE.md DELEGATION 절과 파싱
  - 형식: `## DELEGATION` 절 안의 `KEY: VALUE` 줄만 읽는다. 빈 줄은 무시한다. 그 밖의 줄은 DELEGATION_INVALID이다.
  - 필수 키
    - DELEGATION_SCHEMA = moneylab.delegation/1
    - LEDGER_TASK_ID = TASK_ID
    - BUDGET_TIME_SECONDS, BUDGET_FIX, BUDGET_PYTEST, BUDGET_SAME_FAIL: 0 이상 정수, D1 기본값 이하
    - REQUIRED_CI: `[A-Za-z0-9_.-]{1,40}`
    - PR_TITLE: 200자 이하, 개행 없음
    - SETUP_COMMAND_1..9, CHECK_COMMAND_1..9: 각각 1개 이상, 500자 이하. 정확한 cd 결합을 포함할 수 있다.
  - 키 중복, 알 수 없는 키, 필수 키 누락, 형식 오류는 DELEGATION_INVALID로 STOP한다. 기본값으로 메우지 않는다.
  - taskctl은 명령을 실행하지 않는다. 명령 문자열은 해시로만 기록한다.

- D3 taskctl CLI
  - 형식: `python -m moneylab.taskctl <command> --task-id <TASK> [옵션]`. TASK는 workstate의 task_id 형식을 따른다.
  - 출력: 표준출력에 `moneylab.taskctl.result/1` canonical JSON 1줄과 LF. 필드는 command, status, code, phase, open_step, budget, authority:"NONE"(표시일 뿐 권한 분리의 근거가 아니다), 필요 시 publish_draft·resume_draft.
  - 종료 코드: 0 = OK/PASS, 3 = STOP, 4 = UNKNOWN, 2 = INVALID.
  - 명령
    - `init --wo-sha256 --base --expires-utc --session-nonce`
      - 전제: `data/processed/taskctl/<TASK>`가 없다. 있으면 LEDGER_EXISTS.
      - 검사: HEAD의 parent = BASE, HEAD와 BASE의 차이는 `docs/tasks/<TASK>/WORK_ORDER.md` 추가 1개, 그 blob의 SHA-256 = WO_SHA256, clean, refs/remotes/origin/main = BASE, D2 파싱 성공.
      - 기록: DELEGATE 이벤트.
    - `record-message --kind PUBLISH --wo-c1 --head --tree --base --pr-text-sha256 --expires-utc`
    - `record-message --kind RESUME --wo-sha256 --delegation-id --phase --head --session-nonce`
    - `step start --step <STEP> --session-nonce --input-sha256`
    - `step end --step <STEP> --session-nonce --result ok|fail [--failure-sig <64hex>] [--remote <KEY>=<VALUE> ...]`
    - `phase-set --to <PHASE> [--terminal-status COMPLETE|CLOSED_WITH_VIOLATION|STOPPED --code <CODE> --violations <int>]`
    - `pr-text --sha256 <64hex>`: stdin 바이트로 pr_text.md를 만든다.
    - `lease-clear --lease-id <32hex>`
    - `revoke`
    - 조회: `status`, `verify-ledger`, `check --read-only --phase <PHASE>`, `publish-draft`
  - 이벤트 kind별 payload(키: 유형)
    - DELEGATE: c1(hex40), wo_sha256(hex64), base(hex40), expires_utc(UTC), session_nonce(hex32), delegation_sha256(hex64), state(STATE)
    - PUBLISH: wo_c1, head, tree, base(hex40), pr_text_sha256(hex64), expires_utc(UTC)
    - RESUME: wo_sha256, delegation_id(hex64), phase(PHASE), head(hex40), session_nonce(hex32), state(STATE)
    - STEP_START: step(STEP), session_nonce, input_sha256(hex64), pre_state(STATE)
    - STEP_END: step, start_seq(int), session_nonce, result(ok|fail), failure_sig(hex64|null), post_state(STATE), remote(D4 허용 키만, agent_reported 표시)
    - PHASE: from, to(PHASE), terminal_status(null|COMPLETE|CLOSED_WITH_VIOLATION|STOPPED), code(CODE|null), violations(int|null)
    - PR_TEXT: sha256(hex64), bytes(int)
    - LEASE_CLEARED: lease_id(hex32)
  - STATE와 post_state는 taskctl이 run_git과 파일 해시로 직접 수집한다. Agent는 제출하지 않는다.

- D4 원장·산출물
  - 디렉터리: `<repo>/data/processed/taskctl/<TASK>/`. repo는 git 최상위로 확인한다. 경로의 모든 구성 요소는 링크·재분석 지점이 아니어야 한다(workstate.collect 검사 재사용).
  - events/NNNNNN.json
    - 형식: `{schema:"moneylab.taskctl.event/1", task_id, seq, prev_sha256, kind, utc, payload}`
    - seq는 1부터, seq 1의 prev_sha256은 64개의 "0"이다.
    - canonical 바이트가 8 KiB를 넘으면 쓰지 않고 STOP(EVENT_TOO_LARGE)한다. 자르거나 일부만 기록하지 않는다.
    - 10,000개를 넘으면 STOP(LEDGER_FULL)한다.
  - LEASE: `{schema, lease_id(hex32), utc, command}`, 256 B 이하.
  - REVOKED: `{schema, utc}`, 256 B 이하. taskctl은 삭제하지 않는다.
  - pr_text.md: UTF-8, LF만, 64 KiB 이하. phase LOCAL_DONE에서만 만들며 덮어쓰지 않는다.
  - 모든 파일은 atomic_create_new_bytes로만 만든다. 이벤트는 lease를 가진 상태 변경 명령만 쓴다. LEASE는 소유자 또는 lease-clear만 삭제한다.
  - STATE
    - 필드: head(hex40|null), tree(hex40|null), index_empty(bool), status_sha256(porcelain v2 출력의 hex64), changed, outside_changes(int), untracked_unexpected(int), ignored_top_sha256(hex64)
    - changed: `[[relpath, "A"|"M"|"D", w_sha256(hex64)|null]]`, relpath 순 정렬, 200개 이하(넘으면 STATE_TOO_LARGE)
    - relpath는 ALLOWED_FILES 또는 Work Order의 저장소 상대 POSIX 경로만 쓴다(240자 이하). 그 밖의 변경은 개수로만 센다.
  - remote 허용 키: pushed_head, merge_sha, run_head_sha, checkout_sha, merge_tree_recomputed(hex40), merge_parents(hex40 두 개), pr_number, run_id(int), required_conclusion(`[a-z_]{1,20}`)
  - 값 제한: hex, UTC, `[A-Z0-9_]{1,40}` 코드, 정수, bool, 200자 이하 ASCII 출력 가능 문자열, 위 relpath만 허용한다. 절대 경로, 홈·사용자 이름을 포함한 경로, URL, 환경변수 값, 명령 출력, 예외 원문은 저장하지 않는다. 형식을 벗어난 입력은 INVALID로 처리한다.
  - CreateNewError
    - final_created=True: 대상이 이미 생성된 것으로 관측을 보존하고 STOP(CREATED_CLEANUP_FAILED)한다. 성공으로 보지 않는다. 생성된 파일의 상대 경로·해시와 "임시 파일 잔존 가능"을 보고한다. 같은 이벤트를 다시 쓰거나 명령을 다시 실행하지 않는다.
      - lease 생성 중: lease는 생성된 것으로 보고 해제하지 않는다.
      - 이벤트 생성 중: 이벤트는 기록된 것으로 보고 lease를 해제하지 않는다.
    - final_created=False: 대상이 없다는 관측과 tmp_leftover 여부를 보고하고 STOP(IO_ERROR)한다. 파일시스템 전체에 부분 효과가 없었다고 주장하지 않는다.
    - FileExistsError: CONCURRENT로 처리한다.

- D5 lease
  - 원장을 바꾸는 명령 하나가 실행되는 동안만 잡는다.
  - 순서
    1. LEASE를 create-new로 만든다. 이미 있으면 LEASE_PRESENT로 STOP하고 "잔존 여부와 소유 상태 미확인"으로 보고한다.
    2. 원장을 검증한다.
    3. 이벤트 1개를 create-new로 쓴다.
    4. LEASE 내용이 자신의 lease_id와 같을 때만 삭제한다.
  - 1과 3 사이에서 중단되면 LEASE(와 임시 파일)가 남고 이벤트는 기록되지 않는다. 원장은 바뀌지 않았지만 파일시스템의 부분 효과는 남는다.
  - 3과 4 사이에서 중단되면 이벤트와 LEASE가 남는다.
  - TTL·갱신·자동 회수는 없다.
  - lease-clear(CLEAR_LEASE 메시지 뒤에만)
    - 순서: 원장 검증, LEASE 내용이 지정 id와 같은지 확인, LEASE_CLEARED 이벤트를 create-new로 기록, LEASE 삭제.
    - 기록 뒤 삭제 전에 중단되면 LEASE_PRESENT가 남는다. CLEAR_LEASE를 다시 받아야 한다.

- D6 세션·단계·phase
  - session_nonce: init과 RESUME이 각각 새 무작위 hex32를 기록한다. step start·end는 현재 nonce를 써야 한다.
  - 미종결 단계
    - 현재 nonce로 시작한 단계(진행 중): 같은 nonce의 end(ok|fail)만 허용한다. 새 start와 phase-set은 STEP_OPEN으로 거부한다.
    - 이전 nonce로 시작한 단계(결과 불명): UNKNOWN_STEP. RESUME과 모든 상태 변경을 거부한다. 예외는 아래 목록의 종결 기록뿐이다. 복구와 재실행은 첫 버전 범위 밖이다.
  - 상태 변경 거부 조건: REVOKED 존재, 만료 경과, phase TERMINAL, LEASE 존재, 원장 무효, UNKNOWN_STEP, STEP_OPEN(start·phase-set에만).
  - 거부 조건과 무관하게 허용하는 예외(이 목록이 전부다)
    - status, verify-ledger, check --read-only, publish-draft: 항상 허용
    - revoke: 항상 허용
    - lease-clear: LEASE가 있고 원장이 유효할 때
    - 진행 중 단계의 step end: REVOKED·만료 상태에서도 허용
    - `phase-set --to TERMINAL --terminal-status STOPPED`: REVOKED·만료·UNKNOWN_STEP 상태에서도 허용(LEASE가 없고 원장이 유효할 때)
  - 단계 이름(고정 집합): SETUP_ENV, IMPLEMENT, TEST_TARGETED, TEST_FULL, LINT, TYPECHECK, LOCAL_AUDIT, LOCAL_COMMIT, CLEAN_E2E, PUSH, PR_CREATE, CI_WAIT, PREMERGE_CHECK, MERGE, POST_MERGE_AUDIT
  - 단계별 진입·종료 조건. C1은 DELEGATE의 c1, I는 LOCAL_COMMIT의 post head이다.
    - SETUP_ENV: 진입 HEAD=C1·clean. 종료 HEAD=C1·clean, ignored_top이 {.venv/, src/moneylab.egg-info/}의 부분집합.
    - IMPLEMENT: 진입·종료 모두 HEAD=C1, index 비어 있음, outside_changes=0, untracked는 ALLOWED_FILES 안. W 변화는 허용한다.
    - TEST_TARGETED·TEST_FULL·LINT·TYPECHECK: 진입 HEAD=C1·outside_changes=0. 종료 changed가 진입과 같음(검사가 파일을 바꾸지 않음), ignored 유지.
    - LOCAL_AUDIT: 위와 같다. 종료 changed를 W_audit로 기록한다.
    - LOCAL_COMMIT: 진입 HEAD=C1, changed=W_audit. 종료 HEAD=I, parent(I)=C1, 커밋 파일 집합=W_audit의 경로, 각 blob 내용 해시=W_audit의 w_sha256(다르면 HASH_MISMATCH), clean.
    - CLEAN_E2E: 진입 HEAD=I·clean. 종료 status_sha256과 ignored가 진입과 같음.
    - PUSH·PR_CREATE·CI_WAIT·PREMERGE_CHECK·MERGE: 진입 HEAD=I·clean·phase PUBLISHING. 종료 로컬 상태가 진입과 같음. remote는 형식과 PUBLISH 고정값(head·base·tree)으로 검사한다.
    - POST_MERGE_AUDIT: 진입 HEAD=I·clean. 종료 origin/main=remote.merge_sha이고, cat-file로 parents=[BASE, I], tree=TREE를 확인한다. merge_tree_recomputed=TREE(제출값).
  - 비교 규칙
    - 새 start의 pre_state는 직전 STEP_END의 post_state와 같아야 한다. 예외는 위 진입 조건이 허용하는 W 변화뿐이다.
    - end는 그 단계의 종료 조건으로만 판정한다.
    - 허용되는 HEAD 전환은 init 전 BASE→C1(Agent 보고)과 LOCAL_COMMIT의 C1→I뿐이다. 그 밖은 HEAD_MISMATCH다.
  - phase 전이
    - NONE→DELEGATED: init
    - DELEGATED→SETUP_DONE: SETUP_ENV ok, 현재 상태가 그 post와 같음
    - SETUP_DONE→LOCAL_DONE: 마지막 IMPLEMENT 이후 TEST_TARGETED·LINT·TYPECHECK·TEST_FULL 각 ok, LOCAL_AUDIT ok, LOCAL_COMMIT ok, 그 뒤 CLEAN_E2E ok, 예산 이내
    - LOCAL_DONE→READY_TO_PUBLISH: PR_TEXT, HEAD=I·clean
    - READY_TO_PUBLISH→PUBLISHING: PUBLISH 이벤트의 wo_c1=C1, head=HEAD=I, tree=tree(I), base=DELEGATE.base, pr_text_sha256=파일 해시, 만료 전
    - PUBLISHING→MERGED: PUSH, PR_CREATE, CI_WAIT, PREMERGE_CHECK, MERGE가 이 순서로 각각 ok
    - MERGED→AUDITED: POST_MERGE_AUDIT ok
    - AUDITED→TERMINAL: COMPLETE는 violations=0이고 미종결 단계가 없을 때, CLOSED_WITH_VIOLATION은 violations≥1일 때
    - TERMINAL이 아닌 모든 phase→TERMINAL(STOPPED, code): 위 예외 목록 조건에서 허용
    - 그 밖의 전이는 INVALID_TRANSITION이다.

- D7 예산(원장 기준. Agent의 기록 누락은 막지 못한다)
  - 경과: 현재 UTC − DELEGATE 이벤트 utc. 4시간 이상이면 BUDGET_TIME이다. init 전 setup 시간은 포함하지 않는다. 로컬 시계를 신뢰한다.
  - 수정 반복: 결과 fail인 TEST_*·LINT·TYPECHECK 뒤의 IMPLEMENT start 수. 상한을 넘는 start는 BUDGET_FIX다.
  - 전체 pytest: TEST_FULL start 수. 상한을 넘는 start는 BUDGET_PYTEST다.
  - 같은 실패 연속: 최근 검사 end 2개가 모두 fail이고 failure_sig가 같으면, 다음 IMPLEMENT·검사 start는 BUDGET_SAME_FAIL이다.
  - 경계: 상한과 같은 횟수까지 허용한다.

- D8 check
  - git은 workstate.collect.run_git(rev-parse, status, ls-files, ls-tree, cat-file, check-ignore)으로만 호출한다. 네트워크를 쓰지 않고, 다른 프로세스를 실행하지 않으며, moneylab.providers를 import하지 않는다.
  - 판정 코드: OUT_OF_SCOPE, PROTECTED_CHANGED, HEAD_MISMATCH, UNTRACKED, HASH_MISMATCH, CONTRACT_MISMATCH, STATE_CHANGED

## TEST_GATES

- 신규 테스트는 오프라인으로 실행한다. Git 상태·보호 diff·HEAD 변화가 필요한 테스트는 tmp_path에 임시 Git 저장소를 만든다.
  - init: LEDGER_EXISTS, parent≠BASE, Work Order 해시 불일치, 추가 파일 존재, not clean, origin/main≠BASE, DELEGATION_INVALID의 유형별 실패, 정상 생성.
  - 원장: 정상 체인, LEDGER_GAP, LEDGER_CHAIN, LEDGER_FORMAT, LEDGER_TASK, EVENT_TOO_LARGE(쓰지 않음), STATE_TOO_LARGE, 허용 밖 키·값 거부, 절대 경로·URL형 값 거부, 기존 seq 덮어쓰기 불가.
  - lease: 두 스레드의 동시 생성 중 하나만 성공, LEASE_PRESENT, 비소유자 해제 불가, D5의 두 중단 시점, lease-clear 중단 재현.
  - CreateNewError: lease 생성과 이벤트 생성 각각에 final_created=True와 False를 주입해 CREATED_CLEANUP_FAILED·IO_ERROR, 재기록 없음, lease 미해제를 확인.
  - 세션: 진행 중 단계는 같은 nonce의 end만 허용. 이전 nonce의 미종결은 UNKNOWN_STEP이고 RESUME 거부. UNKNOWN 단계를 ok·fail로 닫는 시도 거부. 종결 STOPPED 기록은 허용.
  - 단계 조건: D6의 각 단계에 성공 1건·실패 1건. IMPLEMENT 중 W 변화 허용, 검사 단계 중 W 변화 거부, LOCAL_COMMIT의 C1→I 허용, 예상 밖 HEAD 전환 거부.
  - phase: D6의 각 전이에서 필수 이벤트가 빠지면 INVALID_TRANSITION.
  - 예산: 네 항목 각각 경계값까지 허용하고 다음을 STOP.
  - 철회·만료: 상태 변경 거부. D6 예외 목록의 명령만 동작.
  - check: D8의 판정 코드를 각각 재현.
  - 권한 분리: DELEGATE 없이 phase-set 거부, 다른 task 디렉터리로 복사한 원장은 LEDGER_TASK, PUBLISH 필드가 현재 상태와 다르면 거부.
  - 경계: providers import 없음, 네트워크 없음, subprocess는 run_git 경로로만.
- 정적 검사: `ruff check --no-cache src tests`와 `mypy`(pyproject 설정, taskctl 포함). CI와 같은 범위다.
- 전체 pytest: 로컬 1회(BGA 예산 안), CI 1회.
- `git diff --check` 통과. 변경 집합 = ALLOWED_FILES이고 각 항목의 변경 한정을 지킨다.

## E2E_GATES

- CLEAN_COMMIT_E2E: HEAD·tree·parent 확인, W·S 대조, 신규 테스트 재실행, 검사 전후 status(untracked·ignored 포함)가 같아야 한다.

## CI_RECORD

- PR_CI에서 다음을 기록한다.
  - PR head SHA, run의 headSha와 event
  - job 로그 checkout 단계에서 확인한 실제 checkout SHA. 시험용 merge commit이면 그 parents와 tree, 그리고 PR head tree와의 관계
  - 필수 Windows job의 결과와 집계
  - Linux experimental에서 기존 실패와 같은 이름의 실패, 그리고 신규 실패를 구분. 이름이 같다는 이유로 원인이 같다고 단정하지 않는다.
  - 로그는 조회한 구간을 명시한다. CI 수동 실행이나 재실행은 하지 않는다.

## ACCEPTANCE_CRITERIA

- AC1 C1·I의 parent와 변경 집합이 COMMIT_PLAN과 같다.
- AC2 README §1–§14와 TEMPLATE 기존 문언이 바뀌지 않았다(diff 확인). §15와 DELEGATION 절이 D1·D2를 담는다. pyproject 변경은 한 줄이다.
- AC3 taskctl이 D3–D8을 만족하고, TEST_GATES가 모두 통과한다.
- AC4 필수 Windows CI가 SUCCESS이고 CI_RECORD가 기록되었다.
- AC5 POST_MERGE_AUDIT에서 parent 순서, tree, first-parent 범위, ancestry, merge-tree 재계산, branch·worktree 보존을 확인했다.
- 파일럿 결과는 이 task의 조건이 아니다.

## COMPLETION

- COMPLETE: AC1–AC5 충족, 계약·지시 위반 0건, 설명되지 않은 상태 변경이나 보호 파일 변경 없음.
- 위반이 1건 이상이면 CLOSED_WITH_VIOLATION이다. 이후 승인, ERRATA, 정정으로 위반을 없애지 않는다.
- 수행하지 않은 gate의 조건은 충족으로 표시하지 않는다.

## REQUIRED_EVIDENCE

- GIT_VERIFIABLE: base, C1, I, merge의 SHA·tree·parent, 커밋 파일 집합, blob 해시, merge-tree 결과.
- CLAUDE_REPORTED: W 해시, TEST_GATES 결과, Guard·권한 관측.
- INDEPENDENT: PR CI(CI_RECORD), GitHub의 PR·merge 상태.

## REQUIRED_REPORT

- 매 gate 보고에 다음을 포함한다: TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, HEAD·parent·tree, 변경 집합, PROTECTED diff, clean 여부, diff --check, 증거 등급, PROPOSED_ERRATA, 이벤트와 DEVIATIONS(이 task 기준 누계), <GATE>_PASS, READY_FOR_<NEXT_GATE>.

## STOP_CONDITIONS

- base·HEAD·tree 불일치(fetch 후 원격 main이 CANONICAL_BASE와 다른 경우 포함. 새 기준을 임의로 채택하지 않는다), Work Order sha256 불일치.
- ALLOWED_FILES 밖 변경, PROTECTED 변경, 변경 한정 위반, 예상 밖 untracked·ignored.
- 테스트·ruff·mypy 실패 중 BGA-4 범위 밖의 것, 회귀, COMMIT 이후 실패.
- Guard DENY, 권한 거절·무응답, 예상 밖 ASK, 오류나 결과 불명, 계약 모순, 상위 규칙과의 충돌, 예산 초과.

## CONSTRAINTS

- 보호 경로 확인과 수정 동작 단어를 한 셸 호출에 섞지 않는다. 출력 리디렉션과 임시 파일을 쓰지 않는다. 도구가 자동 저장한 결과 파일은 이벤트로 보고한다.
