Work Order: AUTO-03 — 비권위 실행 증거 저장과 ID 조회

현재 후보는 PROPOSED_NOT_ISSUED 상태다.
Metadata의 STATUS는 C1 발행 후 사용할 값이다.
C1 발행 후 계약은 불변이며 변경은 ACCEPTED ERRATA로만 한다.

Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: AUTO-03
TASK_ID: AUTO-03
TITLE: 기존 evidence의 비권위 로컬 저장과 명시적 ID 조회
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 99f6bd509d208344321dd375f7d1d3622cfb6f22
CANONICAL_BASE_TREE: 24b1a8286f0a4262b511d51f51bfc92d8f06b4b4
SOURCE_WORKTREE: C:/MoneyLab-auto-02
SOURCE_EXPECTED_HEAD: 4d206e011e89bca6ad031ff7f35562011066dc20
TARGET_BRANCH: codex/auto-03-runlog
TARGET_WORKTREE: C:/MoneyLab-auto-03
WORKSPACE_SETUP: REQUIRED (SUBPHASE: WORKTREE_CREATION_ONLY -> C1_CREATION_ONLY -> ENVIRONMENT_PREPARATION_ONLY)
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests job pytest, Windows runner, exact PR head SUCCESS
BUNDLE_ELIGIBLE: YES
BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E
BUNDLE_GRANTED: NONE

GATE_SEQUENCE

DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

GATE_TRANSITION_RULES

- 각 gate는 사용자의 명시적 승인 범위에서만 수행한다.
- WORKSPACE_SETUP은 WORKTREE_CREATION_ONLY, C1_CREATION_ONLY, ENVIRONMENT_PREPARATION_ONLY를 각각 별도로 승인한다. ENVIRONMENT_PREPARATION_ONLY는 C1_CREATION_ONLY 완료 후, IMPLEMENTATION 전에 수행한다. 표준 GATE_SEQUENCE는 변경하지 않는다.
- C1 이전 승인은 TASK_ID, SUBPHASE, EXPECTED_HEAD, EXPECTED_TREE, 후보 해시로 식별한다.
- C1 이후에는 GATE_AUTHORIZATION: AUTO-03 <GATE> WO@<C1 SHA>를 사용한다. ENVIRONMENT_PREPARATION_ONLY 승인에는 SUBPHASE를 함께 적는다.
- 묶음 실행은 README §14에 맞는 별도 승인으로만 가능하다.
- PUSH, PR_CI, MERGE, 후퇴는 개별 승인이다.
- 종료된 승인은 자동 복원하지 않는다.
- COMMIT 후 수정은 새 커밋으로 한다. amend는 금지한다.

ABSOLUTE_RULES

CLAUDE.md, .claude의 guard·hook·settings, docs/agent_workflow.md와 고정·사전등록 계약을 따른다.
이 작업은 기존 개발 도구 승인과 거래 관련 절대 규칙을 변경하지 않는다.

GOAL

이미 만들어진 evidence를 검증해 ignored 로컬 경로에 저장하고 지정한 ID로 조회한다.
기록 재조사 부담을 줄이는 기반 기능이며 실행·승인·재개·수익성을 증명하지 않는다.

NON_GOALS

- action 실행, executor wrapper, 새 action, 시도 기록, 중복 실행 방지
- 자동 재시도·재개, scheduler, queue
- latest 선택, 목록·삭제·정리, 원격 저장
- Git 실행 시점 증명, 계약 해시 연결, AUTO-02 snapshot 연결
- 네트워크, OpenClaw, 새 모델 호출, 거래·지갑·자본 기능
- automation·workstate·atomic 기존 코드 변경과 기존 테스트 약화

ALLOWED_ACTIONS

- WORKTREE_CREATION_ONLY: source와 원격 main, base tree, 대상 branch·경로 부재를 확인하고 base에서 새 worktree와 branch를 1회 생성한다. source 기존 파일·branch 내용·index는 보존한다. 생성에 필요한 Git 관리정보 변경만 예외다.
- C1_CREATION_ONLY: 승인 바이트의 docs/tasks/AUTO-03/WORK_ORDER.md 하나를 최초 생성하고 그 파일만 stage·C1 commit한다.
- ENVIRONMENT_PREPARATION_ONLY: 별도 승인으로 다음만 수행한다.
  - 대상 worktree 전용 .venv 생성
  - 대상 커밋의 requirements-dev.txt에 따른 의존성 설치
  - 대상 worktree의 editable 설치: pip install -e . --no-deps
  - Python 버전, sys.prefix, moneylab.__file__, 고정 의존성 버전, pip check 확인
  - Python 실행 파일과 설치 명령은 환경 준비 승인문에서 확정한다. 임의 업그레이드나 네트워크 설치는 이 계약만으로 승인되지 않는다.
  - executor 세션 root는 기존 MoneyLab 실행 환경으로 유지하고 대상 worktree를 세션 root로 사용하지 않는다. 세션 root의 프로젝트 settings·guard 경로, settings.local.json 존재 여부, 전용 Python, 사용자 전역 hook을 정적으로 확인한다. 이 확인은 동적 강제나 다른 worktree에 대한 적용을 입증하지 않는다. 거절된 조사는 반복하지 않는다.
  - 승인된 환경 준비의 ignored 산출물은 tracked·untracked 변경과 구분해 보고한다. .venv, editable 설치 산출물, 검사 캐시는 자동 정리하지 않는다. 예상 밖 ignored 산출물도 숨기지 않고 보고한다.
- IMPLEMENTATION: 진입 전에 대상 .venv의 Python과 moneylab 설치 위치가 대상 worktree를 가리키고 필요한 검사 도구의 버전과 의존성이 확인돼야 한다. 확인되지 않으면 구현하지 않고 중단한다. ALLOWED_FILES 구현과 TEST_GATES 실행만 한다.
- PRECOMMIT_AUDIT: 읽기 전용 감사와 W·S 확정만 한다.
- COMMIT: 실제 ALLOWED_FILES 변경만 경로를 지정해 stage하고 구현 커밋 1개를 만든다.
- CLEAN_COMMIT_E2E: clean 구현 커밋에서 지정 검사를 수행한다.
- PUSH: 별도 승인으로 대상 branch push 1회만 한다.
- PR_CI: README §13의 PR_CREATE: YES와 모든 필수 값이 있을 때만 PR 생성 1회, 이후 해당 head CI를 조회한다.
- MERGE: README §13의 사전 조건과 MERGE_EXECUTE: YES 승인 뒤 정확한 head를 지정해 merge commit 방식으로 1회 병합한다.
- POST_MERGE_AUDIT: main 추적 ref fetch 1회와 구조·내용 감사를 한다.
- COMPLETE: 채팅 최종 보고만 한다.
- C1 메시지: docs(task): add AUTO-03 work order
- 구현 메시지: feat(runlog): store and show non-authoritative evidence
- 승인문에 없는 trailer는 넣지 않는다.

ALLOWED_FILES

- A src/moneylab/runlog/__init__.py
- A src/moneylab/runlog/store.py
- A src/moneylab/runlog/__main__.py
- A tests/test_runlog_store.py
- A tests/test_runlog_cli.py
- A tests/test_runlog_isolation.py
- M docs/tasks/README.md

PROTECTED_FILES

ALLOWED_FILES 외 모든 저장소 파일은 보호 대상이다.
docs/tasks/AUTO-03/WORK_ORDER.md의 C1 최초 생성만 별도 예외다.
특히 automation, workstate, storage, 기존 tests, .claude, .github, 의존성, configs, knowledge와 기존 연구자료를 변경하지 않는다.
ALLOWED_FILES와 PROTECTED_FILES의 교집합은 없어야 한다.

FORBIDDEN_ACTIONS

- 승인 범위 밖 작업과 보호 파일 변경
- 기존 테스트 수정·삭제·skip·xfail·단정 완화
- guard·settings 변경이나 우회, Guard DENY 뒤 자동 재시도·변형 실행
- git add . 또는 -A, amend, --no-verify, force push, reset, restore, stash, clean, rebase, cherry-pick
- 다른 branch·worktree·기존 untracked·ignored·reference 파일의 변경·정리
- 대상 worktree를 executor 세션 root로 사용
- 실제 MoneyLab 저장소에서 개발 검증용 runlog store 또는 action 실행
- 개발 검증은 tmp 테스트 저장소만 사용한다. 전체 pytest의 기존 테스트 동작은 유지한다.
- 별도 검사 스크립트, scratchpad, 출력 리디렉션으로 파일 생성
- 보호 경로와 sed 등 수정 명령을 한 셸 명령에 결합
- 실제 stdout·stderr 원문, 사용자 경로, 환경변수, 인증정보 저장
- 코드나 문서에 한국어와 영어 외 언어 사용

DESIGN_CONTRACT

- D1 인터페이스: 새 runlog 패키지에 store_evidence(task_id, raw: bytes), load_evidence(task_id, record_id)를 둔다. production root는 패키지 위치에서 정하고 Git top-level과 일치해야 한다. production CLI에는 root 인자, 환경변수 우회, 테스트용 옵션을 두지 않는다. 테스트는 비공개 내부 API·CLI 처리 함수에 tmp root와 입력 스트림을 주입할 수 있다. 내부 주입 테스트와 실제 명령 진입점의 연결 검사를 구분한다. 내부 주입 테스트만으로 production root 판정까지 검증했다고 주장하지 않는다.
- D2 CLI:
  python -m moneylab.runlog store --task-id <ID>
  python -m moneylab.runlog show --task-id <ID> --record-id <ID>
  두 명령만 제공한다. store만 stdin.buffer를 읽고 show는 stdin을 읽지 않는다. unknown 인자·누락·형식 오류는 ARGUMENT_INVALID다. --help만 평문 출력과 exit 0을 허용한다. 실제 명령 진입점은 --help, 잘못된 인자, 잘못된 evidence처럼 실제 저장소에 기록하지 않는 경우로 확인한다.
- D3 ID: task_id는 AUTO-02와 같은 형식, 최대 64자다. record_id는 소문자 hex 64자다. 입력으로 임의 경로·명령·action을 받지 않는다.
- D4 stdin과 evidence: 최대 65536 bytes이며 선택적 끝 LF 하나도 상한에 포함한다. limit+1까지만 읽어 초과를 LIMIT_EXCEEDED로 거부한다. UTF-8 strict, BOM 없음, JSON 객체 하나, 중복 키·NaN·Infinity·비유한 숫자 거부다. parsing·직렬화의 깊이 또는 숫자 처리 실패도 INPUT_INVALID로 처리한다. EOF까지 block될 수 있으므로 stdin 전체 시간 제한은 이번 범위에 없다고 명시한다.
- D5 입력 canonical: evidence.canonical_json(obj)의 UTF-8 바이트 또는 그 뒤 LF 하나만 허용한다. 앞뒤 공백·CRLF·추가 LF·여러 객체는 INPUT_INVALID다. evidence.check(obj)를 그대로 호출한다. 기존 validator는 변경하지 않는다. 입력 타입 때문에 발생하는 검증 예외도 원문을 출력하지 않고 INPUT_INVALID로 처리한다.
- D6 추가 일관성 검증:
  SUCCEEDED, VALIDATION_FAILED, SOURCE_UNVERIFIED는 각각 automation.policy.EXIT_STATUS에서 그 상태에 대응하는 int exit_code(현재 0, 1, 3)여야 한다.
  UNEXPECTED_EXIT는 int이며 EXIT_STATUS의 키가 아니다.
  TIMEOUT과 OUTPUT_LIMIT_EXCEEDED는 exit_code null이다.
  DENIED는 기존 check의 null 조건을 따른다.
  bool은 int로 허용하지 않는다.
  위반은 INPUT_INVALID다. 이 검사는 실제 실행 여부를 검증하지 않는다.
- D7 재사용과 격리: automation.evidence와 storage.atomic의 공개 함수, automation.policy.EXIT_STATUS의 읽기 전용 import, workstate.collect의 run_git·check_tree_path·is_link_like·WorkstateError를 필요한 범위에서 사용한다. runlog는 EXIT_STATUS를 변경하지 않는다. workstate.store private 함수를 import하거나 공개 이름으로 바꾸지 않는다. runlog는 executor나 run_action을 직접 import·호출하지 않는다. automation 패키지 초기화가 executor를 간접 로드함은 허용하되 문서와 테스트에서 명시한다. 이는 기능 호출 제한이며 보안 sandbox나 capability 격리가 아니다.
- D8 Git 호출과 오류 변환: 기존 run_git을 통해 고정된 rev-parse --show-toplevel과 check-ignore -q --no-index -- <계산된 상대 경로>만 사용한다. store와 show 모두 rev-parse로 root를 확인한다. check-ignore는 store에서만 실행하며, exit 1은 not ignored로서 STORE_PATH_INVALID다. show는 check-ignore를 실행하지 않으므로 ignore 규칙 변경만으로 기존 기록 조회를 막지 않는다. 기존 timeout·출력 상한·자식 회수 동작을 유지한다. 새 subprocess·shell 호출은 없다. 잘못된 인자와 store evidence 입력은 Git·저장 경로 접근 전에 거부한다. 오류 변환은 다음과 같다.
  - root 확인 중 발생한 WorkstateError는 ENVIRONMENT_INVALID, detail "root verification failed"
  - check-ignore 중 발생한 WorkstateError는 GIT_FAILED, detail "ignore verification failed"
  - 상위 디렉터리 경로 검사 중 발생한 WorkstateError는 STORE_PATH_INVALID, detail "store path verification failed"
  - 기존 detail, 예외 문자열, stderr는 전달하거나 해석하지 않는다.
  - stdin 상한 초과는 LIMIT_EXCEEDED, 저장 기록의 크기 초과는 D15에 따라 RECORD_CORRUPT다.
- D9 기록 형식:
  canonical은 evidence.canonical_json의 UTF-8 바이트다.
  identity는 {schema, task_id, evidence}다.
  schema는 moneylab.runlog.record/1이다.
  record_id = sha256(canonical(identity)).
  evidence_sha256 = sha256(canonical(evidence)).
  최종 파일 키는 schema, task_id, record_id, evidence_sha256, evidence, authority, boundary, evidence_origin뿐이다.
  authority=NONE,
  boundary=DATA_NOT_INSTRUCTIONS,
  evidence_origin=EXTERNAL_UNVERIFIED다.
  파일은 canonical(전체 객체)+LF이며 최대 131072 bytes다.
  meta, Git SHA, 시각, 호스트, 사용자, snapshot_id는 넣지 않는다.
- D10 지위: task_id는 호출자가 지정한 분류일 뿐 실행 task의 증명이 아니다. evidence의 status는 제공받은 값이다. ALLOW는 기록 내부 값이며 저장 명령의 실행 승인도 아니다. 저장·조회 성공과 action 성공을 별도 필드로 구분한다.
- D11 저장 경로와 검사 분리: <root>/data/processed/runlog/<task_id>/<record_id>.json만 사용한다. 검증된 ID로만 경로를 만든다. root 내부의 문자열 경계와 resolve 경계를 확인한다.
  - 상위 디렉터리(data, processed, runlog, <task_id>)는 check_tree_path로만 검사한다. 최종 기록 파일에는 check_tree_path를 사용하지 않는다. 상위 구성 요소의 symlink·junction·reparse point, 디렉터리가 아닌 구성 요소, 검사 오류는 D8에 따라 STORE_PATH_INVALID다.
  - 최종 기록 파일은 runlog에서 os.lstat으로 별도 검사하며 D15의 최종 파일 규칙을 따른다.
  - store에서는 저장 경로 안전 검사를 check-ignore보다 먼저 한다. ignored가 아니면 STORE_PATH_INVALID다.
  - 판정은 WorkstateError.detail 문자열에 의존하지 않는다. 원본 예외 문자열과 절대 경로는 출력하지 않는다.
- D12 디렉터리(store 신규 저장): 상위 경로가 없으면 기존 plain directory 여부를 확인하고 없는 디렉터리만 위에서 아래로 mkdir 하나씩 만든다. FileExistsError면 재검사한다. 생성 직후와 파일 작성 직전에 경로를 재검사한다. 오류 시 만든 디렉터리는 남기고 DIR_LEFT:<상대 경로> 경고를 준다. 동시 악성 경로 교체를 완전히 막거나 파일시스템을 원자적으로 snapshot한다고 주장하지 않는다.
- D13 신규 저장: atomic_create_new_bytes만 사용한다. 성공은 STORED, final_file_created=true다. final_created=true인 CreateNewError도 STORED이며 TMP_LEFTOVER:<이름> 경고다. 이 경우 file_sha256은 원자 생성 함수에 넘긴 최종 바이트의 해시다. 기존 파일은 덮어쓰지 않는다. link 전 다른 실패는 STORE_FAILED다. 자체 tmp 정리는 기존 atomic 함수의 동작만 허용한다.
- D14 기존 ID: FileExistsError이면 기존 기록을 D15의 조회 규칙으로 검증한다. 검증 후 identity가 같으면 기존 바이트를 보존하고 ALREADY_STORED, final_file_created=false다. identity가 다르면 RECORD_CONFLICT다. 손상 기록은 RECORD_CORRUPT로 보존한다. hash나 이름 일치만으로 동일 내용을 가정하지 않는다. 기존 ID 처리 중 atomic 함수가 남긴 tmp 경고도 보존한다.
- D15 조회(show와 D14): 계산된 파일 하나만 읽는다.
  - 상위 경로 부재는 NOT_FOUND다. 이 규칙은 show와 D15 조회에만 적용한다. store 신규 저장에서는 D12에 따라 생성한다.
  - 상위 디렉터리 검사 오류는 D8·D11에 따라 STORE_PATH_INVALID다.
  - 최종 파일 os.lstat의 FileNotFoundError는 NOT_FOUND, 그 밖의 OSError는 RECORD_UNREADABLE다.
  - 최종 파일이 링크·junction·reparse point이거나 root 경계를 벗어나면 STORE_PATH_INVALID다.
  - 링크가 아닌 비정규 파일과 크기 초과는 RECORD_CORRUPT다.
  - 내용 읽기의 OSError는 RECORD_UNREADABLE다. 파일 읽기는 limit+1로 제한한다.
  - strict JSON 위반, 중복 키, canonical 불일치, 키·고정 필드·task·ID·해시·evidence 검증 실패는 RECORD_CORRUPT다.
  - schema가 문자열이며 알려진 값이 아니면 RECORD_INCOMPATIBLE다.
  - 최종 파일 오류에는 위 규칙을 우선 적용한다.
  - 파일을 바꾸거나 다른 ID로 대체하지 않는다. show는 파일·디렉터리를 생성하거나 변경하지 않는다.
- D16 결과:
  schema=moneylab.runlog.result/1.
  고정 키는 schema, command, status, exit_code, authority, task_id, record_id, file_sha256, final_file_created, evidence, warnings, error다.
  authority=NONE.
  정상 show는 FOUND와 evidence 객체를 반환한다.
  정상 store는 STORED 또는 ALREADY_STORED이며 evidence=null이다.
  오류에서는 evidence=null이다.
  command·task_id·record_id는 알 수 있고 유효한 경우만 값이며 나머지는 null이다.
  error는 {code,detail} 또는 null이다.
  detail은 D8의 고정 문구 또는 그 밖의 고정 설명과 계산된 상대 경로만 쓰고 입력 원문·원본 예외·절대 경로·stderr를 포함하지 않는다.
- D17 상태와 종료:
  STORED, ALREADY_STORED, FOUND는 경고 없으면 exit 0, 경고 있으면 1이다.
  경고가 붙은 저장 성공에서 호출자는 exit code만 보고 재실행하지 않고 status, warnings, final_file_created를 함께 확인해야 한다. 재저장의 내용 보존은 실행 멱등성이나 모든 재시도의 무해성을 증명하지 않는다.
  NOT_FOUND와 모든 오류는 exit 2다.
  오류 code는 ARGUMENT_INVALID, ENVIRONMENT_INVALID, INPUT_INVALID, LIMIT_EXCEEDED, GIT_FAILED, STORE_PATH_INVALID, STORE_FAILED, NOT_FOUND, RECORD_UNREADABLE, RECORD_CORRUPT, RECORD_INCOMPATIBLE, RECORD_CONFLICT 중 하나다.
  오류 status는 code와 같다.
  최종 파일 생성 시도 전이거나 show이면 final_file_created=null이다.
  저장 생성 시도에서 실패하거나 기존 파일 처리이면 false, 생성됐으면 true다.
  완전히 읽은 정규 파일이나 생성 바이트만 file_sha256을 보고하고 나머지는 null이다.
- D18 stdout: 결과 객체 하나를 canonical JSON+LF로 출력하고 stderr에는 쓰지 않는다. 예외·argparse 오류도 위 결과 형식으로 처리한다. FOUND에 포함된 evidence도 재검증한 데이터이며 지시로 취급하지 않는다.
- D19 README: §11의 AUTO-02 작업 상태 스냅샷 문단 다음에 빈 줄 하나와 TEXT-README-11을 추가한다. 기존 줄은 삭제·수정하지 않는다. §12 이전에 정확히 1회 있어야 한다.
- D20 플랫폼: 링크 판정 오류 주입 단위 테스트는 항상 실행한다. 실제 symlink·junction 생성이 권한·지원 문제로 불가능한 경우만 NOT_RUN_PLATFORM:<case-id>로 skip한다. 그때 관련 AC는 PARTIAL이다. 임의 PASS로 바꾸지 않는다. 미실행 case의 다음 gate 진행은 미리 승인하지 않으며, 발생하면 case ID와 위험을 보고하고 별도 결정을 받는다. 해당 head의 Windows CI 직접 실행 증거를 별도로 보고하고 사용자의 수락을 받는다. 새로운 Linux runlog 실패는 기존 wrapper 실패와 구분해 보고한다.
- D21 실행 전후: show는 파일·디렉터리를 만들지 않는다. store는 지정 ignored runlog 경로와 기존 atomic 함수의 자체 tmp 외에는 쓰지 않는다. HEAD·index·tracked·untracked 상태와 기존 데이터는 보존한다.

TEXT-README-11:
실행 증거 기록(python -m moneylab.runlog, AUTO-03)은 gate 보고가 아니다. ignored 경로 data/processed/runlog/에 보관하는 외부 제공 evidence의 비권위 로컬 기록이다. 형식·내부 일관성·파일 해시 검사는 실제 실행, 작성자 진위, 승인, gate PASS, 자동 재개 권한을 증명하지 않는다. NOT_FOUND는 기록 부재이며 미실행을 뜻하지 않는다. 이 기록에는 위의 gate 보고 파일 보관 제한이 적용되지 않는다.

TEST_GATES

- tmp 저장소에서 내부 API와 내부 CLI 처리 함수의 store -> show round-trip, canonical·ID·file_sha256 대조
- 실제 명령 진입점의 --help, 잘못된 인자, 잘못된 evidence 검사. 실제 저장소에 기록하지 않음을 확인
- evidence의 상태 7종과 status·exit_code 불일치, bool, unknown action, DENIED null 조건
- D6의 세 정상 종료 상태 대응이 automation.policy.EXIT_STATUS와 같음을 대조
- UTF-8·BOM·중복 키·비유한 숫자·깊이 오류·상한 경계·canonical·끝 LF·여러 객체 거부
- 손상·잘림·재계산 ID가 있는 부적합 기록, 파일명·task 불일치, unknown schema, 비정규 파일
- ignored 아님, root 불일치, 문자열·resolve 경계, 링크·junction·reparse 거부
- 상위 디렉터리 오류와 부재, 최종 파일 lstat의 FileNotFoundError와 다른 OSError, 최종 파일의 링크와 비정규 파일, 이 경우들의 서로 다른 오류 code
- 오류 code 판정이 WorkstateError.detail 문자열에 의존하지 않음과 D8 고정 detail 문구
- show가 check-ignore를 실행하지 않고 파일·디렉터리를 만들지 않음
- 두 thread와 두 process의 동일 기록 저장: 한 STORED와 한 ALREADY_STORED, 최종 내용 동일
- fsync·link·tmp 정리·mkdir 실패 주입, 기존 파일 보존, DIR_LEFT와 TMP_LEFTOVER 결과와 exit code
- show 전후 파일·디렉터리·Git index·HEAD 불변, store 전후 tracked·untracked 불변
- 직접 executor 호출과 새 subprocess가 없음을 정적 검사
- round-trip 중 실행 함수가 호출되면 실패하도록 tripwire 검사
- 기존 automation·workstate·atomic 코드와 기존 테스트 diff 0
- targeted: 새 테스트 파일 3개
- 대상 worktree Python으로 ruff, 기본 mypy, 명시적 경로 mypy src/moneylab/runlog 실행
- ruff 인자: -B -m ruff check --no-cache --select E4,E7,E9,F src tests
- IMPLEMENTATION 전체 pytest 1회: -B -m pytest -p no:cacheprovider -q -rs, failed 0 / errors 0
- UTF-8, BOM 없음, LF, 끝 LF 1개, git diff --check, 변경 집합과 보호 diff 확인
- 새 skip·xfail·mock·fixture의 검증 경로를 README §14 BGA-8에 따라 보고

E2E_GATES

- clean 구현 커밋에서 전체 pytest 1회와 AC1–AC9 재검증
- 실제 MoneyLab 저장소에서 runlog store를 실행하지 않는다.
- PR_CI에서 정확한 head의 필수 Windows CI SUCCESS 확인
- 실제 링크 case의 실행 여부를 이름별로 보고한다.
- Linux experimental은 별도 보고하며 새 runlog 실패를 기존 실패로 분류하지 않는다.

ACCEPTANCE_CRITERIA

- AC1: C1 parent=base, C1 변경은 WORK_ORDER.md 추가 하나. 구현 parent=C1, 변경은 ALLOWED_FILES 7개의 A/M와 일치.
- AC2: base부터 구현까지 계약 1개와 ALLOWED_FILES뿐. C1 이후 계약 해시 불변, 보호 diff 0, README 삭제 0.
- AC3: D1–D6, D9–D10의 인자·입력·스키마·권위 경계가 API와 CLI에서 일치.
- AC4: D11–D15의 경로·저장·조회·동시성·손상·실패 보존 테스트 통과.
- AC5: D16–D18의 상태·경고·종료 코드·출력 키·비밀값 비출력 테스트 통과.
- AC6: D7–D8, D21의 실행 비호출·Git과 기존 파일 보존 검사 통과.
- AC7: TEXT-README-11이 지정 절에 정확히 1회 존재하고 기존 문구 불변.
- AC8: targeted, ruff, 기본·명시적 mypy, IMPLEMENTATION과 CLEAN_COMMIT_E2E 전체 pytest failed 0 / errors 0.
- AC9: W와 승인 S를 각각 확정하고 staged·commit blob 내용 SHA-256=승인 S, commit 후 clean.
- AC10: 정확한 PR head의 Windows CI SUCCESS. 이전 단계에서는 NOT_YET_APPLICABLE.
- 플랫폼 case가 미실행이면 관련 AC는 PARTIAL이며 다음 단계 진행은 별도 사용자 결정에 따른다.

REQUIRED_EVIDENCE

- GIT_VERIFIABLE: base·C1·구현·merge SHA, tree, parents, 파일 집합, 보호 diff, 계약 해시, W·S와 commit blob 내용 해시
- CLAUDE_REPORTED: 환경 준비 확인값과 세션 root 정적 확인, API·CLI·pytest·ruff·mypy 검사와 플랫폼 case 결과
- INDEPENDENT: 대상 diff의 ChatGPT 검토와 정확한 head의 GitHub CI
- 직접 관측, 보고, 추론을 구분한다. 사용자 승인 창 클릭을 추정하지 않는다.

REQUIRED_REPORT

TASK_ID, GATE, SUBPHASE, HEAD, parent, tree, WORK_ORDER_COMMIT, WORK_ORDER_SHA256,
변경 집합, 보호 diff, 전후 상태, ignored 산출물, 파일별 W·S,
AC별 PASS/PARTIAL/FAIL/NOT_YET_APPLICABLE,
플랫폼 미실행 case, GUARD_EVENTS, DEVIATIONS, ISSUES, PROPOSED_ERRATA,
해당 gate 판정과 다음 승인 경계를 보고하고 멈춘다.

STOP_CONDITIONS

- 기준선·HEAD·tree·계약 해시·파일 범위 불일치, 예상 밖 untracked
- 생성 전 대상 branch·worktree 존재. 생성 후에는 해당 단계의 기대 상태 불일치
- source가 SOURCE_EXPECTED_HEAD가 아니거나 clean이 아님
- IMPLEMENTATION 진입 전 대상 .venv의 Python·설치 위치·검사 도구 버전·의존성 확인 불충족
- 보호 변경, 기존 테스트 약화, 기존 데이터 변경, 실제 action 호출
- Guard DENY, 권한 거절·무응답, 예상 밖 ASK, 오류·결과 불명
- 검사 실패·미충족·플랫폼 PARTIAL, 상위 규칙 충돌, 실행 환경 불일치
- 묶음 종료·만료·예산 초과. 종료된 승인은 재사용하지 않는다.
- 결과 불명 쓰기는 자동 재전송하지 않는다. 읽기 전용으로 결과만 확인한다.
