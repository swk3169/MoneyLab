# Work Order: AUTO-04 — 오프라인 통합 사례: 실행 증거의 연결·저장·조회

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/AUTO-04/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: AUTO-04
TASK_ID: AUTO-04
TITLE: AUTO-01 실행, AUTO-02 상태 대조, AUTO-03 증거 저장의 사람 승인 오프라인 통합 사례 1건
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 9a6e619e409ed1ab68c10335951af8928f306cdb
CANONICAL_BASE_TREE: 02513c3cf6eb890eee74e69ce57fb080637af1af
SOURCE_WORKTREE: <SOURCE_WORKTREE> (기존 AUTO-03 worktree, 기대 HEAD 351ababbe2e74b80cd2025c4a2342385abe92c66. fetch와 worktree 생성 명령의 실행 위치이며 기존 파일·브랜치 내용·index는 변경하지 않는다)
TARGET_BRANCH: codex/auto-04-offline-integration
TARGET_WORKTREE: <TARGET_WORKTREE> (생성 전 부재해야 하는 새 worktree 경로)
BASE_PYTHON: <BASE_PYTHON> (Python 3.14.8 실행 파일)
VENV_PYTHON: TARGET_WORKTREE 기준 ./.venv/Scripts/python.exe
WORKSPACE_SETUP: REQUIRED (SUBPHASE: MAIN_REF_FETCH_ONLY -> WORKTREE_CREATION_ONLY -> C1_CREATION_ONLY -> ENVIRONMENT_PREPARATION_ONLY -> ERRATA_CREATION_ONLY)
INITIAL_GATE: WORKSPACE_SETUP / MAIN_REF_FETCH_ONLY
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests job pytest, Windows runner, exact PR head SUCCESS
BUNDLE_ELIGIBLE: NO
BUNDLE_MAX_RANGE: NONE
FILE_FORMAT: UTF-8, BOM 없음, LF, 끝 LF 1개, 일반 공백만 사용(U+00A0·탭·줄 끝 공백 금지)

## PATH_VARIABLES

- SOURCE_WORKTREE, TARGET_WORKTREE, BASE_PYTHON은 이 계약의 식별 변수다. 실제 절대 경로와 그 값을 끼운 명령 원문은 각 변수를 처음 쓰는 단계의 사용자 승인문에서 고정한다. SOURCE_WORKTREE는 MAIN_REF_FETCH_ONLY, TARGET_WORKTREE는 WORKTREE_CREATION_ONLY, BASE_PYTHON은 ENVIRONMENT_PREPARATION_ONLY에서 고정한다. 이후 단계는 같은 값을 쓴다.
- 승인문에 값이 없거나 값이 기대 상태(HEAD, 부재, 버전)와 다르면 중단한다. 다른 실행 파일이나 작업공간을 임의로 고르거나 대체하지 않는다.
- 로컬 도구 입력과 채팅 보고에는 실행에 필요한 절대 경로를 쓸 수 있다. 공개 기록(Work Order, ERRATA, 사례 기록, 커밋 메시지, PR 본문)과 E3·E5 프로그램 출력에는 절대 경로, 사용자 이름, 세션 식별값을 넣지 않는다.

## GATE_SEQUENCE

DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

- C1 이전의 CONTRACT_REVIEW PASS는 후보 문안에 대한 검토 판정이며 계약 발행이 아니다. 이 Work Order는 C1 커밋에 포함된 바이트로만 발행되고, STATUS: ISSUED는 그 바이트에 대해서만 효력이 있다.
- 각 gate와 하위 단계는 사용자의 명시적 승인 범위에서만 수행한다. 하나의 승인으로 둘 이상의 하위 단계를 진행하지 않는다.
- C1 이전 승인은 TASK_ID, SUBPHASE, EXPECTED_HEAD, EXPECTED_TREE, 후보 해시로 식별한다.
- C1 이후에는 GATE_AUTHORIZATION: AUTO-04 <GATE> WO@<C1 SHA>를 사용한다. Ce 이후에는 ERRATA: ERRATA-001@<Ce SHA>를 함께 적는다.
- WORKSPACE_SETUP 하위 단계는 MAIN_REF_FETCH_ONLY, WORKTREE_CREATION_ONLY, C1_CREATION_ONLY, ENVIRONMENT_PREPARATION_ONLY, ERRATA_CREATION_ONLY 순서다.
- IMPLEMENTATION 하위 단계는 EXECUTION_ONLY, EXECUTION_CLOSEOUT(중단 시에만), CASE_RECORD_DRAFT, CASE_RECORD_WRITE다. EXECUTION_ONLY는 E0부터 E6까지 단계별로 승인한다.
- 중단 후 문서화 전이와 EXECUTION_CLOSEOUT은 D9에 따른 별도 승인으로만 한다. 전이 승인문에는 EXECUTION_OUTCOME: STOPPED_AT <중단 단계> <사유>를 적는다.
- PUSH, PR_CI, MERGE, POST_MERGE_AUDIT, COMPLETE, 후퇴는 각각 개별 승인이다.
- 종료된 승인은 자동으로 복원하지 않는다. COMMIT 후 수정은 새 커밋으로 한다. amend는 금지한다.

## ABSOLUTE_RULES

CLAUDE.md, .claude의 guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약을 따른다. 이 Work Order는 이들을 변경하거나 덮어쓰지 않는다.

## GOAL

사람의 단계별 승인 아래, 등록된 오프라인 action knowledge_validate를 1회 실행한다. 반환 evidence는 변경 없이 runlog 공개 API에 저장하고, 실행 전후의 workstate 대조와 별도의 읽기 전용 조회로 연결을 확인한다. 그 과정을 사례 1건으로 남긴다. 결과는 비권위 기록이며 실행 사실, 출처, 승인, gate PASS, 무인 운영 준비, 수익성, 비용 절감을 증명하지 않는다.

## NON_GOALS

- 코드 변경, 새 명령, 새 실행기, 새 파서, 시도 기록·중복 실행 통제 기능
- 자동 재실행·재저장·재개, scheduler, queue, 무인 실행
- 네트워크 action, 실거래, 주문, 지갑, 자금
- README, Guard, settings, CI 변경
- runlog CLI store·show와 D18 경로의 검증
- OpenClaw 호출

## ALLOWED_ACTIONS

- MAIN_REF_FETCH_ONLY: git -C <SOURCE_WORKTREE> fetch origin refs/heads/main:refs/remotes/origin/main 1회. 원격 추적 ref 갱신 외의 변경은 없다. 이어서 git -C <SOURCE_WORKTREE> rev-parse refs/remotes/origin/main 결과가 CANONICAL_BASE_SHA이고 그 tree가 CANONICAL_BASE_TREE인지 확인한다. 다르면 중단한다.
- WORKTREE_CREATION_ONLY: TARGET_BRANCH와 TARGET_WORKTREE가 없는지 확인한 뒤 git -C <SOURCE_WORKTREE> worktree add -b codex/auto-04-offline-integration <TARGET_WORKTREE> 9a6e619e409ed1ab68c10335951af8928f306cdb 1회. 생성에 필요한 Git 관리정보 변경만 허용한다.
- C1_CREATION_ONLY: 승인된 바이트의 docs/tasks/AUTO-04/WORK_ORDER.md를 Write 도구로 최초 1회 생성하고, 그 경로만 stage해 C1 커밋 1개를 만든다. 메시지는 docs(task): add AUTO-04 work order다.
- ENVIRONMENT_PREPARATION_ONLY: TARGET_WORKTREE에서 다음을 각각 1회 실행한다.
  - <BASE_PYTHON> -B -m venv .venv
  - ./.venv/Scripts/python.exe -B -m pip install -r requirements.txt
  - ./.venv/Scripts/python.exe -B -m pip install -e . --no-deps
  - 기존 패키지 출처에서 고정 의존성과 선언된 빌드 의존성을 내려받는 것만 허용한다. pip 업그레이드, 별도 출처, requirements-dev.txt 설치는 허용하지 않는다.
  - 확인 항목: Python 3.14.8, sys.prefix가 TARGET_WORKTREE의 .venv, moneylab.__file__이 TARGET_WORKTREE의 src 아래, requirements.txt의 고정 버전 일치, pip check 통과. pip check가 실패하면 원인을 보고하고 중단한다.
  - 생성된 ignored 산출물은 디렉터리 단위로 보고하고 정리하지 않는다.
- ERRATA_CREATION_ONLY: 수락된 승인 바이트의 docs/tasks/AUTO-04/ERRATA-001.md를 Write 도구로 최초 1회 생성하고, 그 경로만 stage해 Ce 커밋 1개를 만든다. 메시지는 docs(task): add AUTO-04 ERRATA-001이다.
- IMPLEMENTATION / EXECUTION_ONLY: D4의 E0–E6만 수행한다. 산출물은 TARGET_WORKTREE의 ignored 경로 data/processed/workstate/AUTO-04/와 data/processed/runlog/AUTO-04/에만 생긴다. 이것은 README §3 IMPLEMENTATION의 ignored 실행 출력이다. runlog 기록 파일의 Read와 runlog CLI show 실행은 하지 않는다.
- IMPLEMENTATION / EXECUTION_CLOSEOUT: 중단 후 D9가 허용한 읽기 전용 확인만, 명령 원문을 개별 승인받아 수행한다.
- IMPLEMENTATION / CASE_RECORD_DRAFT: 사례 기록 후보를 채팅으로만 작성한다.
- IMPLEMENTATION / CASE_RECORD_WRITE: ACCEPTED ERRATA가 허용한 파일만 작성한다. ERRATA-001이 ACCEPTED되기 전에는 할 수 없다.
- PRECOMMIT_AUDIT: 읽기 전용 감사와 W·S 확정만 한다.
- COMMIT: ALLOWED_FILES만 경로를 지정해 stage하고 구현 커밋 1개를 만든다. 구현 커밋의 parent는 Ce다.
- CLEAN_COMMIT_E2E: D12의 문서 검사만 한다. 파일을 쓰지 않는다.
- PUSH: git push -u origin codex/auto-04-offline-integration 1회.
- PR_CI: README §13의 PR_CREATE: YES와 필수 값이 있을 때 PR 생성 1회, 이후 해당 head의 CI 조회.
- MERGE: README §13의 사전 조건과 MERGE_EXECUTE: YES 승인 뒤, 정확한 head로 merge commit 방식 1회.
- POST_MERGE_AUDIT: 읽기 전용 감사. fetch는 별도 승인이 있을 때만 한다.
- COMPLETE: 채팅 최종 보고만 한다.
- 승인문에 없는 trailer는 넣지 않는다.

## ALLOWED_FILES

ALLOWED_FILES: NONE. 사례 기록 파일은 ACCEPTED ERRATA가 경로와 최초 생성을 명시한 경우에만 추가된다(README §11).

## PROTECTED_FILES

ALLOWED_FILES 밖의 모든 저장소 파일은 보호 대상이다.
보호 대상의 예외는 계약 파일 두 개의 최초 생성뿐이다. docs/tasks/AUTO-04/WORK_ORDER.md는 C1_CREATION_ONLY에서, docs/tasks/AUTO-04/ERRATA-001.md는 ERRATA_CREATION_ONLY에서 각각 1회 생성한다. 두 파일은 생성 후 변경하지 않는다. 이 예외는 ALLOWED_FILES에 속하지 않는다.
사례 기록 파일의 최초 생성은 보호 예외가 아니다. ACCEPTED ERRATA가 ALLOWED_FILES에 추가한 경우에만 CASE_RECORD_WRITE에서 허용되며, 구현 커밋 I에만 포함된다.
ALLOWED_FILES와 PROTECTED_FILES의 교집합은 없어야 한다.

## COMMIT_PLAN

- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/AUTO-04/WORK_ORDER.md 하나
- Ce: parent = C1, 변경 = A docs/tasks/AUTO-04/ERRATA-001.md 하나
- I: parent = Ce, 변경 = ACCEPTED ERRATA가 허용한 사례 기록 파일 1개
- base..I: 위 3개 파일뿐

## FORBIDDEN_ACTIONS

- 승인 범위 밖 작업, 보호 파일 변경, 기존 테스트·코드·README·Guard·settings·CI 변경
- git add . 또는 git add -A, amend, --no-verify, force push, reset, restore, stash, clean, rebase, cherry-pick
- 다른 branch·worktree, 기존 untracked·ignored·reference 파일의 변경이나 정리, SOURCE_WORKTREE의 파일·브랜치·환경 변경
- run_action, store_evidence, load_evidence를 D4가 정한 1회를 넘어 호출하는 것, 자동 재실행·재저장
- evidence 원문, runlog 기록 원문, warnings 원문, error.detail, 원본 예외, traceback을 프로그램 출력·채팅 보고·공개 기록에 포함하는 것, runlog 기록 파일의 Read, runlog CLI show 실행
- 공개 기록과 프로그램 출력에 절대 경로, 사용자 이름, 세션 식별값, 인증정보를 넣는 것
- 모델이 다시 작성하거나 복원한 evidence를 원본으로 쓰는 것
- 파일로 된 임시 스크립트, scratchpad, 출력 리디렉션으로 파일 생성
- 보호 경로 이름과 수정 명령 단어를 한 셸 명령에 결합
- Guard DENY나 권한 거절 뒤 재시도, 변형, 우회
- 네트워크 사용(ENVIRONMENT_PREPARATION_ONLY의 승인된 설치, MAIN_REF_FETCH_ONLY, PUSH·PR_CI·MERGE의 정해진 명령은 제외), OpenClaw 호출
- 한국어와 필요한 영어 외 언어 사용

## DESIGN_CONTRACT

- D1 지위: 모든 workstate·runlog 기록과 사례 기록은 비권위 데이터다. snapshot MATCH는 현재 상태의 일치만 뜻한다. 기록이 없다는 이유로 미실행이라고 판단하지 않는다.
- D2 작업공간: 실행과 문서 작성은 TARGET_WORKTREE에서만 한다. Guard 코드의 정적 판정, 실제 도구 호출 차단, 사용자 승인 창은 서로 다른 증거이며, 관측한 것만 보고한다.
- D3 환경: ALLOWED_ACTIONS.ENVIRONMENT_PREPARATION_ONLY를 따른다. 통합 경로의 import는 표준 라이브러리와 moneylab뿐이다. requirements.txt 설치는 pip check 정합성을 위한 것이다.
- D4 실행 단계. 작업 디렉터리는 TARGET_WORKTREE이고 각 단계를 개별 승인한다.
  - E0 진입: HEAD = Ce, tree = tree(Ce), tracked·index·untracked 변경 0, data/processed/workstate/AUTO-04와 data/processed/runlog/AUTO-04가 없음, D3 확인값 재확인.
  - E1 snapshot: ./.venv/Scripts/python.exe -B -m moneylab.workstate snapshot --task-id AUTO-04 1회. 결과 객체가 status = STORED, exit_code = 0, snapshot_id = 소문자 hex 64자여야 한다. 이 값을 SNAPSHOT_ID로 쓴다. E1은 verify가 아니며 MATCH를 요구하지 않는다.
  - E1 계약 확인(로컬 조회): data/processed/workstate/AUTO-04/<SNAPSHOT_ID>.json을 Read로 읽는다. 이 파일은 E3보다 먼저 생성되므로 evidence가 없고, 상대 경로·해시·시각만 담는다(코드 읽기 기준). state.contract에 docs/tasks/AUTO-04/ERRATA-001.md와 docs/tasks/AUTO-04/WORK_ORDER.md 두 항목만 있고, 각 head_sha256과 work_sha256이 승인된 계약 해시와 같아야 한다. 보고와 공개 기록에는 SNAPSHOT_ID, 두 계약 항목의 경로와 해시, 일치 여부만 옮긴다.
  - E2 기준 verify: ./.venv/Scripts/python.exe -B -m moneylab.workstate verify --task-id AUTO-04 --snapshot-id <SNAPSHOT_ID> 1회. MATCH여야 한다.
  - E3 실행·저장: CONTRACT_REVIEW에서 검토한 E3 프로그램 후보와 같은 원문을 승인문에 전문으로 포함해 1회 실행한다.
  - E4 사후 verify: E2와 같은 명령 1회. MATCH여야 한다.
  - E5 조회: E3 출력의 RESULT_RECORD_ID, EVIDENCE_SHA256, RESULT_FILE_SHA256(각 소문자 hex 64자)을 CONTRACT_REVIEW에서 검토한 E5 프로그램 후보의 상수에 넣는다. 그 명령 원문을 승인받아 1회 실행한다.
  - E6 상태: git -C <TARGET_WORKTREE> status --porcelain=v1 --untracked-files=all과 git -C <TARGET_WORKTREE> status --porcelain=v1 --untracked-files=normal --ignored=matching 각 1회.
  - 실행 후에 생기는 SNAPSHOT_ID, RECORD_ID와 해시 값은 출처(E1 결과 객체, E3 출력)와 형식(소문자 hex 64자)을 확인한 뒤 명령에 넣고, 그 명령 원문을 실행 전에 승인받는다.
- D5 프로그램 요구:
  - 호출 횟수 제한은 실행·저장·조회 작업 API에 적용한다. E3는 run_action과 store_evidence를 각각 최대 1회, E5는 load_evidence를 최대 1회 직접 호출한다. 후보에 적힌 검증·해시 보조 함수(evidence.check, canonical_bytes, record_id_for, valid_record_id)는 이 제한 대상이 아니다.
  - 작업 API가 내부에서 하는 동작은 그 호출의 일부로 허용된다. run_action은 등록 action의 자식 프로세스를 실행한다. store_evidence는 읽기 전용 git rev-parse·check-ignore를 조회하고, ignored 저장 경로에 디렉터리와 기록을 생성한다(저장 동작). load_evidence는 읽기 전용 git rev-parse를 조회하고 lstat과 파일 읽기만 하며 파일을 생성하거나 변경하지 않는다(코드 읽기 기준). 프로그램 자신은 git이나 다른 프로세스를 직접 실행하지 않는다.
  - E3는 run_action의 반환 문자열을 UTF-8 바이트로 바꿔 변경 없이 store_evidence에 전달한다.
  - 출력은 정해진 키의 검증된 값만 쓴다. evidence 원문, 기록 원문, warnings 원문, error.detail, 원본 예외, 절대 경로는 출력하지 않는다.
  - 쓰기 반환값이 요청 길이와 다르거나 쓰기·flush가 실패하면 관측 실패로 끝내고 다시 출력하지 않는다.
  - import 실패, 단계별 예외, 해석 실패, KeyboardInterrupt를 구분한다. SystemExit는 바꾸지 않는다.
  - 이 시험은 API 경로만 다루며 runlog CLI store·show와 D18 경로를 검증하지 않는다.
- D6 판정 축. 다음 다섯 가지를 서로 별도로 기록한다.
  - 실행 결과: EVIDENCE_RETURNED, UNKNOWN, NOT_RUN 중 하나. EXEC=NO_EVIDENCE는 AutomationError로 evidence를 받지 못했다는 관측 표식이다. action의 미실행이나 확정된 실패의 증거가 아니며, 실행 결과는 UNKNOWN이다. EXEC=UNKNOWN과 실행 단계 인터럽트도 UNKNOWN이다.
  - 작업 결과: evidence status(SUCCEEDED, VALIDATION_FAILED, SOURCE_UNVERIFIED, TIMEOUT, OUTPUT_LIMIT_EXCEEDED, UNEXPECTED_EXIT, DENIED) 또는 NOT_AVAILABLE. SUCCEEDED는 작업 성공, VALIDATION_FAILED는 작업 검증 실패, SOURCE_UNVERIFIED는 출처 미검증, TIMEOUT 계열은 작업 실패, DENIED는 실행 거부다. 어느 경우에도 재실행하지 않는다.
  - 저장 결과: STORED_NEW(유효한 저장 성공), STORED_WITH_WARNINGS(유효한 저장 성공과 경고), ALREADY_STORED_UNEXPECTED, DEFINED_ERROR, NOT_ATTEMPTED(DENIED 또는 evidence 해석 실패), UNKNOWN, NOT_RUN 중 하나. STORED_WITH_WARNINGS는 저장 성공과 경고를 그대로 유지하며 UNKNOWN으로 바꾸지 않는다. ALREADY_STORED_UNEXPECTED는 결과 형식이 유효한 경우에만 쓴다. 이때 같은 identity의 기록이 이미 있다는 관측과, 그 기록이 이번 실행과 연결되는지에 대한 불확실성(UNKNOWN)을 나눠 기록한다. 형식이 유효하지 않은 결과는 UNKNOWN이다.
  - 관측 결과: E3·E5 출력이 정해진 형식과 일치하는지, 추가 진단이 없는지, E5 대조값. Bash 도구는 stdout과 stderr를 합쳐 보여준다. 그래서 확인 가능한 조건은 "관측된 통합 출력이 정해진 형식과 일치하며 추가 진단이 없음"으로 한정하고, stdout·stderr 분리 확인은 미실시로 기록한다. 이것은 API 통합 시험의 관측 조건이며 CLI D18 수락 검증이 아니다. PROGRAM_EXIT는 Python 프로세스의 진단 종료 코드다. 그 뒤의 echo 때문에 셸 명령 전체의 종료 코드는 다를 수 있으며 판정에 쓰지 않는다. PROGRAM_EXIT나 REPORT=COMPLETE 하나만으로 성공을 판정하지 않는다.
  - 통합 시험 결과: SUCCESS, FAIL, UNKNOWN, NOT_RUN 중 하나.
    - SUCCESS는 다음을 모두 만족할 때다.
      - IS1 E1 STORED, exit_code 0, 계약 항목 일치
      - IS2 E2와 E4 MATCH
      - IS3 E3 관측 출력이 정확히 다음 15줄이고 추가 진단이 없음: EXEC=EVIDENCE_RETURNED, EVIDENCE_STATUS=<값>, EVIDENCE_EXIT_CODE=<값>, EVIDENCE_BYTES=<값>, EVIDENCE_SHA256=<값>, RESULT_STATUS=STORED, RESULT_EXIT_CODE=0, RESULT_RECORD_ID=<값>, RESULT_FILE_SHA256=<값>, RESULT_FINAL_FILE_CREATED=True, RESULT_WARNING_COUNT=0, RESULT_ERROR_CODE=None, STORE=STORED_NEW, REPORT=COMPLETE, PROGRAM_EXIT=0
      - IS4 E5 관측 출력이 정확히 다음 15줄이고 추가 진단이 없음: RESULT_STATUS=FOUND, RESULT_EXIT_CODE=0, RESULT_RECORD_ID=<E3 값>, RESULT_FILE_SHA256=<E3 값>, RESULT_WARNING_COUNT=0, RESULT_ERROR_CODE=None, EVIDENCE_STATUS=<E3 값>, EVIDENCE_EXIT_CODE=<E3 값>, EVIDENCE_CANONICAL_SHA256=<E3 EVIDENCE_SHA256>, MATCH_RECORD_ID=True, MATCH_EVIDENCE_SHA256=True, MATCH_FILE_SHA256=True, LOOKUP=MATCHED, REPORT=COMPLETE, PROGRAM_EXIT=0
      - IS5 E6의 tracked·untracked 변경 0
    - FAIL은 정의된 결과가 관측됐지만 SUCCESS 조건을 충족하지 못한 경우다. 해당하는 경우: 작업 결과 DENIED(저장 안 함), STORED_WITH_WARNINGS, DEFINED_ERROR, E5 LOOKUP=MISMATCH 또는 LOOKUP=DEFINED_ERROR, E3 이후 E4·E6의 정의된 불일치.
    - UNKNOWN은 실행 결과 UNKNOWN, EVIDENCE=UNRECOGNIZED, 저장 결과 UNKNOWN, ALREADY_STORED_UNEXPECTED, E5 LOOKUP=UNKNOWN, INTERRUPTED_STAGE, 관측 실패(진단 코드 8), 정해진 형식과 다른 출력이다.
    - NOT_RUN은 E3가 실행되지 않은 경우이며 사유를 기록한다.
  - 해시 대상: EVIDENCE_SHA256은 run_action 반환 문자열의 UTF-8 바이트(끝 LF 없음)의 SHA-256이다. STORED 또는 ALREADY_STORED이면 runlog 입력 규칙에 따라 저장된 evidence의 정규 바이트 SHA-256(E5의 EVIDENCE_CANONICAL_SHA256)과 같아야 한다.
- D7 UNKNOWN과 중단:
  - 진단 종료 코드는 evidence의 exit_code와 별개이며, 종료 코드만으로 실행이나 저장 여부를 추정하지 않는다.
  - D6의 FAIL·UNKNOWN에 해당하는 모든 상태, 형식 불일치, Guard DENY, 권한 거절·무응답이 생기면 즉시 중단한다. 이후 확인은 D9의 EXECUTION_CLOSEOUT으로만 한다.
  - 자동 재실행·재저장은 없다. 새 승인이나 새 snapshot은 이전 UNKNOWN을 해소하지 않는다. 같은 작업을 다시 실행하려면 별도 Work Order 또는 ERRATA와 중복 실행 위험 평가가 필요하다.
- D8 한계: 실행 전 시도 기록이 없고 중복 실행 통제도 없다. executor 자식 프로세스와 작업 API 내부 git 프로세스에는 Guard가 적용되지 않는다. 예외 경계 밖의 인터프리터 시작·종료(종료 시 flush 실패 포함), import 부수 출력, 강제 종료는 통제하지 못한다. 이것들은 이 사례의 명시적 한계다. 허용 범위는 사람 승인 아래 사례 1건이며, 무인 운영 준비로 판정하지 않는다.
- D9 중단 사례와 task 완료:
  - task 완료(COMPLETE)는 AC1–AC10 충족과 다음이 없음으로 판정한다: 계약 위반, 보호 파일 변경, 설명되지 않은 상태 변경. 이 중 하나라도 있으면 문서화만으로 완료 조건을 충족하지 않는다.
  - 통합 시험 SUCCESS는 task 완료 조건이 아니다. 중단 사례를 문서화해 완료하더라도 통합 시험 결과를 바꾸지 않는다.
  - 수행하지 못한 단계는 NOT_RUN과 사유(중단 지점, 차단 주체 또는 UNKNOWN 상태)를 기록한다.
  - 중단 지점별 전이. 각 전이는 별도 승인이다.
    - C1 이전(MAIN_REF_FETCH_ONLY, WORKTREE_CREATION_ONLY, C1_CREATION_ONLY)에서 중단: 이 Work Order로는 사례 기록을 만들 수 없다. 채팅으로 보고하고 멈춘다. 이후 처리는 사용자가 새로 결정한다.
    - ENVIRONMENT_PREPARATION_ONLY에서 중단: 별도 승인으로 ERRATA_CREATION_ONLY와 CASE_RECORD_DRAFT로 진행할 수 있다. 환경 관측값을 기록하고 E0–E6은 NOT_RUN으로 기록한다.
    - ERRATA_CREATION_ONLY에서 중단: 사례 기록 파일을 만들 수 없다. 채팅으로 보고하고 멈춘다.
    - EXECUTION_ONLY에서 중단: 별도 승인으로 EXECUTION_CLOSEOUT 또는 CASE_RECORD_DRAFT로 전이한다.
  - EXECUTION_CLOSEOUT의 허용 범위:
    - E3가 실행되지 않았으면 E6만 허용한다.
    - E3가 실행된 뒤라면 E4와 E6을 허용한다.
    - E5는 다음을 모두 만족할 때만 허용한다: E3 출력의 RESULT_STATUS가 STORED 또는 ALREADY_STORED이고, 형식이 유효한 RESULT_RECORD_ID와 RESULT_FILE_SHA256, EVIDENCE_SHA256이 관측됨.
  - 차단·거절·UNKNOWN이 된 명령과 E3는 어떤 경우에도 다시 실행하지 않는다.
- D10 비식별화: PATH_VARIABLES를 따른다. 공개 기록과 프로그램 출력에는 절대 경로, 사용자 이름, 세션 식별값, 인증정보, evidence 원문, 기록 원문, warnings 원문, error.detail, 원본 예외를 넣지 않는다. 로컬 도구 입력에서 경로를 쓰는 것은 이 금지와 별개다. evidence와 snapshot 원본은 ignored 경로에 두고, 커밋하거나 정리하지 않는다.
- D11 Guard: Guard 함수를 직접 호출하는 시험은 하지 않는다. 각 명령의 Guard 결과와 승인 창은 관측한 대로만 보고한다.
- D12 문서 검증: PRECOMMIT_AUDIT와 CLEAN_COMMIT_E2E의 로컬 검증은 문서 내용, 비식별화, 바이트 형식, 변경 범위, 증거 값 대조로 제한한다. 전체 pytest는 NOT_REQUIRED다. 기존 PR CI는 변경하지 않는다.

## TEST_GATES

- 코드 변경이 없으므로 로컬 pytest, ruff, mypy는 NOT_REQUIRED다.
- 계약 파일과 사례 파일 확인: UTF-8, BOM 없음, CR 0, U+00A0 0, 탭 0, 줄 끝 공백 0, 끝 LF 1개.
- 변경 집합과 보호 diff 확인, git diff --check.

## E2E_GATES

- clean 상태의 구현 커밋에서 D12 검사를 다시 하고, 검사 전후 git status(ignored 포함)가 같은지 확인한다.
- PR_CI에서 정확한 head의 필수 Windows CI SUCCESS를 확인한다.

## ACCEPTANCE_CRITERIA

- AC1: C1·Ce·I의 parent와 변경 집합이 COMMIT_PLAN과 같다.
- AC2: base..I는 3개 파일뿐이고, 보호 diff 0, 계약 해시 불변.
- AC3: 환경 확인값과 pip check 통과가 관측됨. 또는 ENVIRONMENT_PREPARATION_ONLY가 중단된 경우, 그 관측값, 실패 지점, 이후 단계의 NOT_RUN 사유가 기록됨.
- AC4: E1이 실행됐으면 계약 항목 확인 결과(일치 또는 불일치)가 기록됨. 실행되지 않았으면 NOT_RUN과 사유가 기록됨.
- AC5: 통합 시험 결과가 D6에 따라 SUCCESS, FAIL, UNKNOWN, NOT_RUN 중 하나로, 근거 관측값과 함께 기록됨.
- AC6: 실행 결과, 작업 결과, 저장 결과, 관측 결과가 통합 시험 결과와 별도로 기록됨.
- AC7: PRECOMMIT_AUDIT 시점에 실행 산출물이 ignored 경로에만 있고, base..HEAD 외 tracked·untracked 변경이 없음.
- AC8: 사례 기록이 ACCEPTED ERRATA 요건과 D10을 만족함.
- AC9: W와 승인 S, staged blob, commit blob의 내용 SHA-256이 일치하고, commit 후 clean.
- AC10: 정확한 PR head의 Windows CI SUCCESS. 이전 단계에서는 NOT_YET_APPLICABLE.
- 완료 판정: AC1–AC10 충족과 D9의 부재 조건을 함께 요구한다. 중단 경로의 문서화 전이는 별도 승인으로만 한다.

## REQUIRED_EVIDENCE

- GIT_VERIFIABLE: base·C1·Ce·I·merge SHA, tree, parents, 파일 집합, 계약 해시, W·S·commit blob 내용 해시
- CLAUDE_REPORTED: 환경 확인값, E0–E6 출력, 판정, Guard·권한 관측
- INDEPENDENT: ChatGPT·사용자 검토, 정확한 head의 GitHub CI
- 직접 관측, 보고, 추론을 구분한다.

## REQUIRED_REPORT

TASK_ID, GATE, SUBPHASE, HEAD, parent, tree, 계약 해시, 변경 집합, 보호 diff, 전후 상태, ignored 산출물, 단계별 출력과 판정, 실행·작업·저장·관측·통합 시험 결과, UNKNOWN 여부, NOT_RUN 사유, GUARD_EVENTS, DEVIATIONS, ISSUES, PROPOSED_ERRATA, 해당 gate 판정과 다음 승인 경계를 보고하고 멈춘다.

## STOP_CONDITIONS

- 기준선·HEAD·tree·계약 해시·파일 범위 불일치, 예상 밖 untracked
- 생성 전 대상 branch·worktree 존재, 생성 후 기대 상태 불일치
- fetch 후 원격 추적 main이 CANONICAL_BASE_SHA가 아님
- PATH_VARIABLES 값이 승인문에 없거나 기대 상태와 다름
- 환경 확인 불충족, pip check 실패
- E1이 STORED·exit_code 0이 아님, 계약 항목 불일치·누락, E2·E4가 MATCH가 아님
- E5의 LOOKUP이 MATCHED가 아님
- D7의 모든 중단 상태
- 보호 파일 변경, 기존 코드·테스트·설정 변경
- Guard DENY, 권한 거절·무응답, 예상 밖 ASK, 오류·결과 불명
- 계약 모순, 상위 규칙과의 충돌
