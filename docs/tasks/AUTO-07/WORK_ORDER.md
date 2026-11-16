# Work Order: AUTO-07 — 고정 파일 전달 검증(무해 probe)

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 ACCEPTED ERRATA로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: AUTO-07
TASK_ID: AUTO-07
TITLE: 사전 고정 파일 실행으로 승인 바이트와 실행 바이트를 연결하는 전달 절차 검증
STATUS: ISSUED
CANONICAL_BASE_SHA: 2a05e0bbdc7a050514860128007ca48b8427121e
CANONICAL_BASE_TREE: ab52b586b69e474242dd5a8db585a2bf94afcd96
TARGET_BRANCH: codex/auto-07-delivery-probe
PATH_VARIABLES: SOURCE_WORKTREE, TARGET_WORKTREE, BASE_PYTHON. 값은 각 승인문에 적고 이 문서와 공개 기록에는 넣지 않는다.
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests job pytest, Windows runner, 정확한 PR head에 연결된 run의 SUCCESS
BUNDLE_ELIGIBLE: NO

## ABSOLUTE_RULES

저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 이 문서는 그 규칙을 복제하거나 바꾸지 않는다.

## GOAL

승인한 프로그램 바이트와 실제 실행된 바이트를, 사전 고정 파일과 해시 대조로 연결하는 전달 절차를 무해한 probe 1회 실행으로 검증한다.

## BACKGROUND

AUTO-06은 실행 전에 동일성을 확보하지 못해 통합 사례를 NOT_RUN으로 기록했다(merge 2a05e0bb…). AUTO-07 DESIGN_INVESTIGATION에서 고정 파일 실행 방식을 후보로 채택했다.

## GATE_SEQUENCE

DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT(I1) -> CLEAN_COMMIT_E2E -> IMPLEMENTATION(후퇴: 실행·사례) -> PRECOMMIT_AUDIT -> COMMIT(I2) -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

- 각 gate와 하위 단계는 사용자의 명시적 승인 범위에서만 수행한다. 승인문은 `GATE_AUTHORIZATION: AUTO-07 <GATE> WO@<C1 SHA>`를 쓰고, 하위 단계가 있으면 SUBPHASE를 함께 적는다. 승인 하나로 둘 이상의 하위 단계를 진행하지 않는다.
- WORKSPACE_SETUP 하위 단계: MAIN_REF_FETCH_ONLY → WORKTREE_CREATION_ONLY → C1_CREATION_ONLY → ENVIRONMENT_PREPARATION_ONLY.
- IMPLEMENTATION(1차) 하위 단계: PROGRAM_REVIEW → FILE_WRITE.
- IMPLEMENTATION(후퇴) 하위 단계: EXECUTION_ONLY → CASE_RECORD_DRAFT → CASE_RECORD_WRITE. 후퇴는 CLEAN_COMMIT_E2E(I1) 통과 뒤 별도 명시 승인으로만 한다.
- 후퇴나 재진입은 끝난 승인을 복원하지 않고 실행 횟수를 늘리지 않는다. EXECUTION_ONLY는 task 전체에서 1회다.
- PUSH, PR_CI, MERGE, POST_MERGE_AUDIT, COMPLETE는 각각 개별 승인이다. COMMIT 후 수정은 새 커밋으로 하고 amend는 금지한다.
- 멈춤 사유(STOP_CONDITIONS)가 생기면 보고하고 멈춘다. 재시도, 변형, 다른 경로로의 우회는 하지 않는다. 같은 작업을 다시 하려면 새 승인이 필요하다.

## ALLOWED_ACTIONS

- WORKSPACE_SETUP: main ref만 fetch, branch·worktree 생성, CONTRACT_FILE_EXCEPTION에 따른 C1, D1 환경 준비.
- IMPLEMENTATION(1차): PROGRAM_REVIEW(채팅 원문과 해시), FILE_WRITE(probe와 테스트 각각 Write 최초 1회, 작성 후 대조).
- PRECOMMIT_AUDIT: 읽기·감사와 D5 검사.
- COMMIT: 해당 커밋의 ALLOWED_FILES만 경로를 지정해 stage하고 커밋 1개.
- CLEAN_COMMIT_E2E: E2E_GATES.
- IMPLEMENTATION(후퇴): EXECUTION_ONLY(D6 1회), CASE_RECORD_DRAFT·WRITE(D8). 승인된 정정 후퇴 포함.
- PUSH, PR_CI, MERGE, POST_MERGE_AUDIT, COMPLETE: README §13과 템플릿 규정대로, 각 1회.

## FORBIDDEN_ACTIONS

- 승인된 gate 밖의 행위. SCOPE_EXCLUSIONS의 실행.
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, Work Order 수정.
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, `fetch --all`, `fetch --prune`.
- Guard·hook·settings·Git 설정·.gitattributes 변경이나 우회. 경로·명령의 은닉·분할·인코딩.
- probe의 재실행·추가 실행. 테스트에서 probe 실행·import.
- 다른 branch·worktree·untracked·ignored·기존 산출물의 정리.

## ALLOWED_FILES

- A tools/auto07_delivery_probe.py
- A tests/test_auto07_delivery_probe.py
- A docs/research-intake/2026-11-16/AUTO-07_DELIVERY_PROBE_CASE.md

## PROTECTED_FILES

- ALLOWED_FILES 밖의 모든 저장소 파일. docs/tasks/AUTO-07/**, .claude/**, .github/**, .gitattributes, .gitignore, CLAUDE.md를 포함한다.
- Git 설정, Guard, hook, settings는 변경하지 않는다.

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## CONTRACT_FILE_EXCEPTION

- docs/tasks/AUTO-07/WORK_ORDER.md는 PROTECTED다. 예외는 C1_CREATION_ONLY에서 승인된 바이트로 최초 1회 생성하고 C1으로 커밋하는 것뿐이다. 이 예외는 ALLOWED_FILES에 속하지 않으며, 생성 후에는 변경하지 않는다.

## COMMIT_PLAN

- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/AUTO-07/WORK_ORDER.md
- I1: parent = C1, 변경 = A tools/auto07_delivery_probe.py, A tests/test_auto07_delivery_probe.py
- I2: parent = I1, 변경 = A docs/research-intake/2026-11-16/AUTO-07_DELIVERY_PROBE_CASE.md
- base..I2 = C1의 WORK_ORDER.md와 ALLOWED_FILES 3개, 합쳐서 추가 4개뿐이다. 경로를 지정해 stage하고, `git add .`·`-A`, 승인되지 않은 trailer는 쓰지 않는다.

## SCOPE_EXCLUSIONS

- knowledge_validate, run_action, store_evidence, load_evidence, workstate, runlog의 실행
- AUTO-06의 재실행, AUTO-06 계약·사례·산출물의 변경
- 차단된 적이 있는 명령이나 다른 프로그램을 파일로 옮겨 실행하는 것. 이 task의 파일 실행 권한은 아래 probe에만 적용된다.

## DESIGN_CONTRACT

- D1 환경 (ENVIRONMENT_PREPARATION_ONLY):
  - BASE_PYTHON 3.14.8로 TARGET_WORKTREE에 .venv를 만든다. requirements-dev.txt는 `-r requirements.txt`를 포함하므로, 대상 venv에 허용되는 것은 두 파일의 고정 이름·버전, moneylab(editable), pip뿐이다.
  - mypy는 requirements-dev.txt의 고정 버전을 유지하고, 과거 Windows 환경과 같이 공식 소스 배포판으로 설치한다.
  - editable 설치와 소스 빌드에 필요한 격리 빌드 의존성은 pip 격리 빌드 환경 안에서만 쓴다. 대상 venv에 추가로 설치할 권한이 아니다.
  - 설치 명령, 출처, 격리 빌드 의존성의 허용 범위는 이 단계 승인문에서 정확히 고정한다. 설치 전에 PIP_ 환경변수와 pip 설정 파일이 없음을 확인한다.
  - 허용하지 않는 것: pip 업그레이드, 고정 목록 밖 패키지의 대상 venv 설치, 별도 출처, 보안 정책 변경, 정책 차단 뒤 임의 재설치. 차단되면 원인을 단정하지 않고 보고한 뒤 멈춘다.
  - 확인 항목(-B로 실행): Python 버전, sys.prefix, moneylab.__file__ 위치, 실행·개발 고정 의존성 전체의 이름·버전 일치, 대상 venv 배포판 목록에 허용 집합 밖 항목이 없음, pip check 통과, mypy 버전과 compiled 여부(소스 배포판이므로 compiled: no 기대).
  - 준비 직후 ignored 항목은 .venv/와 src/moneylab.egg-info/뿐이어야 한다.
- D2 probe 사양 (tools/auto07_delivery_probe.py):
  - 모듈 구성: `import sys`, 상수 문자열 `AUTO07_DELIVERY_PROBE_OK`를 인자로 받는 print 호출 1개, 상수 7을 인자로 받는 sys.exit 호출 1개.
  - 파일 쓰기·삭제, subprocess, 네트워크, moneylab import, 다른 import는 없다.
  - 수십 줄 이내다. UTF-8, BOM 없음, CR 0, U+00A0 0, 탭 0, 줄 끝 공백 0, 끝 LF 1개.

- D3 테스트 (tests/test_auto07_delivery_probe.py):
  - probe를 실행하거나 import하지 않는다. 파일을 바이트로 읽고 ast.parse만 한다.
  - 파일이 없으면 실패한다. 이 검사들에 skip 조건을 두지 않는다.
  - 내용 해시: 작업 파일 바이트에서 CRLF를 LF로 정규화한 뒤의 SHA-256이 PROGRAM_REVIEW 승인값과 같다.
  - 구조 검사: AST가 D2의 구성과 정확히 일치한다.
  - 역할 구분: 해시는 승인 바이트와의 동일성만 확인한다. 구조 검사는 검토된 구성을 기록한다. 둘 다 실행 시 안전을 보장하지 않는다.

- D4 해시의 종류와 확인 시점:
  - 원바이트 해시 W: 대상 worktree 작업 파일의 정규화하지 않은 바이트. BASE_PYTHON -I -B로 메모리에서 계산한다.
  - blob 해시 S: `git show <commit>:<path>` 바이트.
  - 내용 해시: D3의 정규화 해시. 다른 checkout에서는 이 값만 의미가 있다. 다른 checkout의 원바이트 동일성은 보장하지 않는다.
  - 커밋 전(FILE_WRITE, PRECOMMIT_AUDIT): W와 형식만 확인한다.
  - 커밋 후(COMMIT, CLEAN_COMMIT_E2E, EXECUTION_ONLY 전후): W = staged/commit S = 승인값을 확인한다.
  - 각 일치는 그 관측 시점의 사실이다. 실행 전후 일치는 실행 중 불변을 증명하지 않는다.

- D5 로컬 검사:
  - 명령: `./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider tests/test_auto07_delivery_probe.py tests/test_repo_hygiene.py`, 그리고 `./.venv/Scripts/python.exe -B -m ruff check --no-cache tests/test_auto07_delivery_probe.py`. 각 gate에서 1회씩 실행한다.
  - 기존 hygiene 테스트가 pytest tmp_path 아래에 만드는 임시 파일과 임시 Git 저장소는 승인된 테스트 실행 범위에 포함된다. 대상 저장소나 다른 작업공간을 변경할 권한으로 확대하지 않는다.
  - skip 구분: 로컬 연구 데이터(run manifest 등)가 없어서 생기는 기존 hygiene 테스트의 skip은 이름과 사유를 그대로 기록하고 실패로 보지 않는다. 새 probe 테스트는 skip이 1건이라도 있으면 실패로 본다. 기존 skip을 없애거나 테스트를 약화하지 않는다.
  - 검사 전후 git status(untracked 포함, ignored 포함)가 같아야 한다.
  - 전체 pytest, 전체 ruff, mypy는 AC7의 CI에서 확인한다.
- D6 실행 (EXECUTION_ONLY):
  - 승인문에 probe의 W·S 승인 해시와 실행 1회를 적는다. 도구가 승인 창을 띄우지 않을 수 있으므로 이 대화 승인이 필수다. 도구 권한 요청이 있으면 따로 따른다.
  - 진입 조건: HEAD = I1, HEAD tree = I1 tree, clean, ignored 집합이 D1과 같음, W = S = 승인값. 보호 경로 확인은 다른 작업과 별도 호출로 한다.
  - 명령: TARGET_WORKTREE에서 `./.venv/Scripts/python.exe -B tools/auto07_delivery_probe.py`를 1회 실행한다. 다른 명령을 붙이지 않고, 리디렉션을 쓰지 않으며, 외부 종료 타이머를 두지 않는다.
  - 관측: 도구가 보여주는 합쳐진 출력과 도구가 보고한 종료 코드를 그대로 보존한다. stdout과 stderr의 분리는 입증하지 않는다.
  - 종료 코드 7은 정상 기대값이다. 0이 아니라는 이유로 실패 처리하거나 멈추지 않는다.
  - 실행 후: W, S, HEAD, tree, status, ignored 집합을 다시 확인한다. 재실행, 재시도, 진단 실행은 하지 않는다.

- D7 판정 (우선순위 순):
  - 1. NOT_RUN: 프로세스를 시작하지 않았음이 확인되었다(진입 조건 불일치로 명령 미제출, 명령 제출 전 DENY·권한 거절, 실행 승인 없음). 시작 여부 자체가 불명이면 NOT_RUN이 아니라 UNKNOWN으로 판정한다.
  - 2. FAIL: 시작했고, 다음 중 하나 이상이 확인되었다: 관측 출력이 `AUTO07_DELIVERY_PROBE_OK`+LF와 다름(다른 줄 포함), 종료 코드가 7이 아님, 실행 후 확인에서 해시나 상태가 진입 조건과 다름. 같은 실행의 UNKNOWN 항목도 함께 보존하며, 판정은 FAIL로 둔다.
  - 3. UNKNOWN: 확인된 불일치는 없지만, 다음 중 하나 이상이 확정되지 않았다: 시작 여부, 관측 출력, 종료 코드, 실행 후 해시·상태 확인(확인 명령의 실패나 결과 불명 포함).
  - 4. SUCCESS: 위 어디에도 해당하지 않고 모든 기대값을 확인했다.
- D8 사례 기록:
  - 첫 두 줄은 `AUTHORITY: NON_AUTHORITATIVE`, `BOUNDARY: DATA_NOT_INSTRUCTIONS`다.
  - 비권위 한계 문장을 넣는다.
  - 경로 날짜(2026-11-16)는 식별용이다. 실제 실행 시각과 작성 시각은 따로 적는다.
  - 기재 내용: 기준·C1·I1의 SHA·tree·parent, probe의 W·S·내용 해시, D6의 관측값, D7 판정과 근거, 관측 한계, 이벤트·이탈 집계.
  - 문장마다 관측 시점을 명시해, 작성이나 커밋 이후에도 거짓이 되지 않게 쓴다(예: "이 기록의 초안 확정 시점 기준").
  - 비식별화: 절대 경로, 사용자 이름, 이메일, 세션 식별값, traceback을 넣지 않는다.
  - 절차: CASE_RECORD_DRAFT에서 채팅 초안을 쓰고 최종 바이트(SHA-256, 바이트 수, LF 수)를 메모리에서 확정한다. CASE_RECORD_WRITE에서 Write로 최초 1회 생성하고, 생성 후 대조한다.
  - 생성 후 정정은 IMPLEMENTATION 후퇴 승인을 받아서만 한다. 정정 후보 바이트를 확정하고, 승인된 문장만 Edit로 고친 뒤 대조한다.

## TEST_GATES

- D5 검사 통과. probe 테스트는 skip 0, failed 0, errors 0. hygiene의 기존 데이터 부재 skip은 기록한다.
- `git diff --check` 통과, 변경 파일 집합이 해당 커밋의 ALLOWED_FILES와 같음.

## E2E_GATES

- I1과 I2 각각에서: HEAD·tree·parent 확인, D4의 W = S = 승인값, D5 재실행, 검사 전후 status(ignored 포함) 동일.

## EVENTS_AND_VIOLATIONS

- 이벤트와 이탈은 AUTO-07 안에서 0부터 센다.
- 예상된 중단: DENY·ASK 거절, 권한 거절, 사전 대조 불일치로 멈춘 경우. 이벤트로 기록하며 위반이 아니다.
- 검사 오류: 승인 범위 안의 읽기 전용 검사 명령이 실패한 경우(문법, 출력 과다 등). 검사 이슈로 기록하고, 재수행은 새 승인으로 한다.
- 계약·지시 위반: 승인 범위 밖의 행동, 명시된 금지·분리 지침을 어긴 명령 구성, 차단된 동작을 다른 경로로 다시 시도한 경우. 차단 여부와 관계없이 그 구성 자체가 위반이다.
- 예상 밖 상태 변경과 보호 파일 변경은 자동으로 면제되지 않는다. 정리하지 않고 보존해 보고한다.

## ACCEPTANCE_CRITERIA

- AC1: C1·I1·I2의 parent와 변경 집합이 COMMIT_PLAN과 같다.
- AC2: base..I2는 WORK_ORDER.md와 ALLOWED_FILES 3개의 추가뿐이고, 보호 diff가 0이다.
- AC3: D1의 확인값과 준비 직후 ignored 목록이 기록되었다. 준비가 중단되었으면 그 관측값과 이후 단계의 NOT_RUN 사유를 기록한다.
- AC4: probe와 테스트가 D2·D3을 만족하고, D5 검사가 통과했으며, D4의 커밋 전후 해시 대조가 기록되었다.
- AC5: D7 판정 하나가 우선순위에 따른 근거와 함께 기록되었다. SUCCESS, FAIL, UNKNOWN, NOT_RUN 모두 이 조건을 만족할 수 있다. FAIL 판정에 UNKNOWN 항목이 함께 있으면 둘 다 기록한다.
- AC6: 사례 기록이 D8을 만족하고, W·승인값·staged·commit blob이 일치하며, 커밋 후 clean이다.
- AC7: 정확한 PR head에 연결된 Windows CI가 SUCCESS다. PR head SHA, run headSha, checkout 대상(시험용 merge commit이면 parents와 tree 관계 포함)을 기록한다. Linux experimental의 기존 실패와 신규 실패를 구분하고, 이름이 같다는 이유만으로 원인이 같다고 단정하지 않는다.
- AC8: POST_MERGE_AUDIT에서 parent 순서, tree 일치, first-parent 범위, ancestry, merge-tree 재계산, branch·worktree 보존을 확인했다.

## COMPLETION

- task COMPLETE는 다음을 모두 요구한다.
  - AC1–AC8 충족
  - 계약·지시 위반 0건
  - 설명되지 않은 상태 변경과 보호 파일 변경이 없음
- D7 판정과 관계없이 AC1–AC4, AC6–AC8의 커밋·문서·CI·감사 요건은 그대로 충족해야 한다. FAIL·UNKNOWN·NOT_RUN을 문서화할 수 있다는 것이 예상 밖 상태 변경, 보호 파일 변경, 계약·지시 위반을 면제하지 않는다.
- D7 판정이 FAIL, UNKNOWN, NOT_RUN이어도 그것을 기록할 수 있고, 위 조건을 만족하면 COMPLETE할 수 있다. 사례 판정과 task 완료는 별개이며, 완료가 사례 판정을 바꾸지 않는다.
- 계약·지시 위반이 1건 이상 기록되면 COMPLETE를 낼 수 없다. task는 CLOSED_WITH_VIOLATION으로 종결한다. 이후 승인, ERRATA, 정정으로 기록된 위반을 없애지 않는다.
- 아직 수행하지 않은 gate의 조건은 충족으로 표시하지 않는다. NOT_YET_APPLICABLE 또는 NOT_RUN으로 표시한다.

## REQUIRED_EVIDENCE

- GIT_VERIFIABLE: base·C1·I1·I2의 SHA·tree·parent, 커밋 파일 집합, blob 해시, merge parent·tree·merge-tree.
- CLAUDE_REPORTED: 원바이트 W·내용 해시, D1 확인값, D5 결과와 skip 목록, D6 관측값과 Guard·권한 관측, D7 판정.
- INDEPENDENT: PR CI(run headSha, checkout 대상), GitHub의 PR·merge 상태.

## REQUIRED_REPORT

- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, clean 여부, diff --check
- 증거 등급, PROPOSED_ERRATA, 이벤트(예상된 중단·검사 오류)와 DEVIATIONS(AUTO-07 기준 누계)
- <GATE>_PASS = YES / NO, READY_FOR_<NEXT_GATE> = YES / NO

## STOP_CONDITIONS

- 기준 불일치: fetch 후 원격 main이나 그 tree가 CANONICAL_BASE와 다르다. 이때 새 기준을 임의로 채택하지 않는다. 그 밖에 HEAD, tree, 승인 해시, 파일 범위가 다르거나 예상 밖 untracked·ignored가 있다.
- 환경: D1 확인 실패, pip check 실패, 설치 출처 설정이 존재한다.
- 파일: 작성 후 W나 형식이 승인값과 다르다. 생성 후 승인 없이 변경되었다.
- 검사: D5 테스트가 실패하거나 검사 전후 status가 다르다.
- 실행: D6 진입 조건 불일치. 이때는 실행하지 않고 NOT_RUN으로 한다.
- 공통: Guard DENY, 권한 거절이나 무응답, 예상 밖 ASK, 오류나 결과 불명, 계약 모순, 상위 규칙과의 충돌.
- 멈춤은 보고 후 대기를 뜻한다. 문서화 전이는 별도 승인으로 할 수 있다.

## CONSTRAINTS

- 우선순위 1–3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)과 README는 이 Work Order가 바꾸지 못한다.
- 경로·명령을 숨기거나, 쪼개거나, 인코딩하지 않는다. Guard·hook·settings·Git 설정을 변경하거나 우회하지 않는다.
- 보호 경로 확인과 수정 동작 단어를 한 셸 호출에 섞지 않는다. 출력 리디렉션과 임시 파일을 쓰지 않는다. 도구가 자동으로 저장한 결과 파일은 이벤트로 보고한다.
