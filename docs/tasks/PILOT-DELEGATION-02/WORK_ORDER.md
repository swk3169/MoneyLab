# Work Order: PILOT-DELEGATION-02 — v1.4 위임 파일럿 재수행: taskctl init 경로 링크 거부 테스트

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 ACCEPTED ERRATA로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.4
WORK_ORDER_ID: PILOT-DELEGATION-02
TASK_ID: PILOT-DELEGATION-02
TITLE: v1.4 위임 절차로 taskctl init의 경로 링크 거부를 오프라인 테스트로 확인(PILOT-DELEGATION-01 재수행)
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 2f1309879f58307c6208e91cfb2c19c74110aecf
CANONICAL_BASE_TREE: 0906c9707c16843a830e3d4bb74d81ea223db541
TARGET_BRANCH: codex/pilot-delegation-02
TARGET_WORKTREE: C:/MoneyLab-pilot-delegation-02
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
TASKCTL_PYTHON: C:/MoneyLab-gov-automation-03/.venv/Scripts/python.exe
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: DELEGATE
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests의 pytest job(Windows), 정확한 PR head에 연결된 run의 SUCCESS
BUNDLE_ELIGIBLE: NO
BUNDLE_MAX_RANGE: NONE

## GATE_SEQUENCE

GATE_SEQUENCE: DELEGATE(WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> READY_TO_PUBLISH) -> PUBLISH(PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> 최종 보고)

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- README §15를 따른다. 권한은 현재 세션 사용자가 보낸 DELEGATE, PUBLISH, RESUME, REVOKE, CLEAR_LEASE 메시지에서만 나온다(DL-0).
- DELEGATE 1건이 DELEGATED_PROCEDURE 1–14를 승인한다(DL-1). DELEGATE가 허용하는 네트워크는 두 가지뿐이다: DELEGATED_PROCEDURE 1의 지정 origin main ref fetch 1회, SETUP_COMMAND_2·3이 명시한 https://pypi.org/simple 설치. 그 밖의 네트워크 사용, push, PR, merge, ERRATA, Work Order 변경, 만료 연장은 승인하지 않는다.
- PUBLISH 1건이 DELEGATED_PROCEDURE 15–21을 승인한다(DL-2). 다른 head, 재push, PR 수정, CI 수동 실행·재실행은 승인하지 않는다. PUBLISH 구간의 원격 조회, push, PR 생성, merge, POST_MERGE_AUDIT fetch는 PUBLISH 범위에만 속하며 DELEGATE로는 허용되지 않는다.
- 단계는 DELEGATED_PROCEDURE 순서로만 진행한다. 건너뛰거나 순서를 바꾸지 않는다.
- turn 종료와 세션 종료를 구분한다. 같은 세션에서 보고 후 turn이 끝나면, 사용자의 다음 메시지는 대화를 이어 줄 뿐 권한을 추가하지 않는다. 진행은 이미 받은 DELEGATE 또는 PUBLISH의 범위와 만료 안에서만 한다. 새 세션에서는 README §15 DL-3의 RESUME 조건을 모두 만족할 때만 이어 간다.
- STOP 뒤에는 보고하고 대기한다. 재시도, 변형, 우회는 새 승인 없이 하지 않는다.
- COMMIT 후 수정은 새 커밋으로 한다. amend는 금지한다.
- 이 Work Order와 v1.4 규칙은 GOV-AUTOMATION-03과 PILOT-DELEGATION-01에 소급 적용하지 않는다. 두 task의 DEVIATION·이탈은 이 task의 위반으로 합산하지 않고, 이 task가 지우지도 않는다.
- 실행 순서(P11): 상태 변경 명령은 각각 별도 도구 호출로 실행하고, 그 결과를 확인한 뒤 다음 단계로 진행한다. 선행 결과에 의존하는 조회·검사는 병렬로 실행하지 않는다. STOP 조건이 생기면 그 뒤의 단계·명령을 실행하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 이 문서는 그것을 복제하거나 바꾸지 않는다.

## GOAL

GOAL: v1.4 Task Delegation 절차를 실제 task에 적용한다. PILOT-DELEGATION-01에서 STOPPED로 끝난 같은 작업을 새 task로 다시 수행한다. 대상 변경은 taskctl init이 원장 경로의 기존 구성 요소에 있는 링크, 깨진 링크, junction, 재분석 지점을 거부하는지와 정상 경로의 init 동작을 오프라인 테스트로 확인하는 것이다.

## BACKGROUND

BACKGROUND:
- GOV-AUTOMATION-03(PR #54, merge 2f1309879f58307c6208e91cfb2c19c74110aecf)이 README §15와 taskctl을 추가했다. 그 task는 CLOSED_WITH_VIOLATION으로 종결되었다.
- 그 task의 남은 한계 중 하나가 "init 경로 검사의 실행 테스트 없음"이다. 정적으로는 init이 mkdir 전에 기존 구성 요소를 lstat으로 검사한다.
- PILOT-DELEGATION-01(C1 e44906cd651751ac09304eafbbb8813aab2702b1)은 같은 범위로 실행되었다. TEST_FULL은 실패 0으로 끝났지만, 실행 중 src/moneylab 아래 __pycache__ 4개(pyc 10개)가 생겨 taskctl TEST_FULL 종료 기록이 STATE_CHANGED로 거부되었고 STOPPED로 종결되었다. 그 branch·worktree·원장·미커밋 변경·캐시는 증거로 보존하며 재개·수정·정리하지 않는다.
- 원인은 정적 근거에 따른 유력 가설이다: tests/test_v06_randomness.py가 `-B` 없이 부모 환경을 상속해 실행한 하위 인터프리터가 montecarlo·synthetic과 그 import closure의 pyc를 쓴 것으로 보인다. 실행 확인은 하지 않았다.
- 수익성, 실거래, 무인 운영은 이 task의 성공 조건이 아니며, 이 task로 그 달성을 주장하지 않는다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- DELEGATE 구간: DELEGATED_PROCEDURE 1–14.
- PUBLISH 구간: DELEGATED_PROCEDURE 15–21.
- 작업 디렉터리 지정: Git은 `git -C <절대 경로>`, taskctl은 `--repo C:/MoneyLab-pilot-delegation-02`, 파일과 실행 파일은 절대 경로를 쓴다. `cd <경로> && <명령>` 결합은 DELEGATION의 CHECK_COMMAND와 DESIGN_CONTRACT의 COLLECT_COMMAND 문자열과 정확히 같은 명령에만 쓴다.

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 구간 밖의 행위. ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, Work Order 수정.
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, `fetch --all`, `fetch --prune`.
- Guard·hook·settings·.github 변경이나 우회. 경로·명령의 은닉·분할·인코딩.
- 출력 폐기, 출력 리디렉션, tee, 임시 검사 스크립트 파일 작성.
- 대기 루프, 백그라운드 폴링, 자동 재시도. TEST_FULL(CHECK_COMMAND_4)의 백그라운드 실행과 완료 알림 대기는 예외다(DESIGN_CONTRACT P5).
- 다른 branch·worktree·untracked·ignored·기존 산출물의 정리.
- 운영 코드 결함을 테스트 약화(단언 완화, skip·xfail 추가, 검사 생략)로 감추는 것.
- 실주문, 지갑, 개인키, 실거래 자금.
- PILOT-DELEGATION-01의 branch·worktree·원장·미커밋 변경·캐시를 변경·정리·재개하는 것. 그 worktree는 P10의 읽기 전용 복사 원본으로만 쓴다.
- 전역·영구 환경 설정 변경, 바이트코드 캐시의 사전 생성·삭제, 환경 변수 유무 비교 실험.

## ALLOWED_FILES

ALLOWED_FILES:
- M tests/test_taskctl_lease.py (이름이 test_init_으로 시작하는 init 경로 링크 거부 테스트와 그에 필요한 helper 추가만. 기존 테스트·단언·helper 동작은 바꾸지 않는다. DESIGN_CONTRACT P4의 LF 정규화 외의 형식 변경은 하지 않는다)

## PROTECTED_FILES

PROTECTED_FILES:
- ALLOWED_FILES 밖의 모든 저장소 파일. docs/tasks/PILOT-DELEGATION-02/**, 다른 docs/tasks/<TASK>/**, src/**, .claude/**, .github/**, CLAUDE.md, docs/agent_workflow.md, .gitignore, .gitattributes, pyproject.toml, requirements*.txt를 포함한다.
- ALLOWED_FILES 항목이라도 위 변경 한정을 벗어난 변경은 보호 위반으로 본다.

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- docs/tasks/PILOT-DELEGATION-02/WORK_ORDER.md는 DELEGATED_PROCEDURE 3에서 DELEGATE가 고정한 바이트로 최초 1회만 생성한다. 이 예외는 ALLOWED_FILES에 속하지 않는다.

## COMMIT_PLAN

COMMIT_PLAN:
- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/PILOT-DELEGATION-02/WORK_ORDER.md, 메시지 `docs(task): add PILOT-DELEGATION-02 work order`
- I: parent = C1, 변경 = M tests/test_taskctl_lease.py, 메시지 `test: cover taskctl init path links`
- base..I = 위 2개 경로뿐이다. 본문·trailer는 넣지 않는다.
## DESIGN_CONTRACT

DESIGN_CONTRACT:
- P1 taskctl 명세의 적용 관계
  - taskctl의 CLI·원장·lease·단계·전이·실패 코드는 docs/tasks/GOV-AUTOMATION-03/WORK_ORDER.md의 DESIGN_CONTRACT D2–D8을 따른다.
  - 그 위에 GOV-AUTOMATION-03 ERRATA-001의 D6 대체(미종결 단계의 STOPPED 종결)와 D4 보완(LEASE·REVOKED·pr_text 최종 구성 요소 검사)을 적용한다.
  - GOV-AUTOMATION-03 ERRATA-002는 그 task의 COMMIT_PLAN과 테스트 보존 조건만 바꿨으며 taskctl 동작을 바꾸지 않는다. 이 task에는 적용 대상이 없다.
  - 기준 코드는 CANONICAL_BASE_TREE의 src/moneylab/taskctl이다.
- P2 taskctl 실행
  - 형식: `C:/MoneyLab-gov-automation-03/.venv/Scripts/python.exe -I -B -m moneylab.taskctl <command> --task-id PILOT-DELEGATION-02 --repo C:/MoneyLab-pilot-delegation-02 [옵션]`
  - 사전 확인(읽기 전용, init 전 1회와 각 세션 시작 시): GIT_HOST_WORKTREE의 HEAD tree = CANONICAL_BASE_TREE이고 clean이다. TASKCTL_PYTHON을 `-I -B`로 실행해 Python 3.14, `sys.dont_write_bytecode` True, moneylab과 moneylab.taskctl이 C:/MoneyLab-gov-automation-03/src 아래에서 로드됨을 확인한다. 하나라도 다르면 STOP한다.
  - session_nonce는 init과 RESUME마다 새 무작위 hex32를 쓴다. 인증 수단이 아니다.
  - 각 단계는 `step start` 후 실행하고, 결과를 관측한 세션이 같은 nonce로 `step end`를 기록한다. CHECK 단계의 --input-sha256은 실행한 CHECK_COMMAND 문자열의 UTF-8 SHA-256이고, SETUP_ENV는 SETUP_COMMAND_1..5를 LF로 이은 문자열의 SHA-256이다.
  - taskctl이 OK가 아닌 code를 반환하면 그 code로 STOP한다.
  - taskctl은 협조형 검사·기록 도구다. 이미 실행 중인 작업을 강제로 중단하지 않는다. BUDGET_TIME_SECONDS와 만료는 새 step 시작과 phase 전이를 거부할 뿐이다. REVOKE는 이후 상태 변경을 거부하는 기록이며 프로세스를 종료하지 않는다.
  - pr-text 본문 바이트는 stdin 파이프로만 넘긴다. 파일·리디렉션을 쓰지 않는다.
- P3 환경 준비(SETUP_ENV)
  - SETUP_COMMAND_1은 TASKCTL_PYTHON의 venv 모듈로 새 venv를 만든다. CPython 3.14의 venv 구현은 `sys._base_executable`(기반 설치의 python.exe)을 새 venv의 기반으로 쓴다. 이것은 구현 근거이며 이 task 전에 실행 확인하지 않았다(미확인). 실패하면 STOP한다.
  - 설치 출처는 https://pypi.org/simple 하나다. `--isolated`로 사용자·환경 pip 설정을 무시하고, `--no-cache-dir`로 캐시를 쓰지 않는다.
  - requirements-dev.txt(requirements.txt 포함)의 고정 버전만 설치한다. mypy는 `--no-binary=mypy`로 공식 sdist에서 순수 Python으로 빌드한다(AUTO-03에서 Windows 정책이 mypyc 확장 모듈을 막은 이력).
  - 격리 빌드에 필요한 빌드 의존성(mypy sdist의 build-system.requires, 이 저장소의 setuptools>=69)은 같은 출처에서 pip가 내려받는 것만 허용한다. 그 버전은 고정되지 않는다(한계).
  - editable 설치는 `--no-deps`를 유지한다.
  - 준비 완료 조건: SETUP_COMMAND_1–5가 모두 exit 0, `pip check` 문제 없음, `mypy --version` 출력에 `mypy 2.4.0`과 `compiled: no` 포함, SETUP_ENV 종료 시 ignored가 `.venv/`, `src/moneylab.egg-info/`의 부분집합. 하나라도 다르면 STOP한다.
  - SETUP_ENV에서 네트워크는 SETUP_COMMAND_2·3에만 쓴다. DELEGATE 구간의 다른 네트워크 사용은 DELEGATED_PROCEDURE 1의 fetch 1회뿐이다.
- P4 줄바꿈과 해시
  - 시스템 git 설정 core.autocrlf=true 때문에 checkout된 tests/test_taskctl_lease.py는 CRLF일 수 있다.
  - taskctl LOCAL_COMMIT 종료 검사는 commit blob 내용 SHA-256을 LOCAL_AUDIT의 작업 파일 SHA-256(W)과 비교한다. 따라서 IMPLEMENT는 대상 파일 한 개를 LF만으로 기록해 W = S가 되게 한다.
  - 각 IMPLEMENT 단계(최초 1회와 BUDGET_FIX 안의 승인된 수정 반복마다)에서 대상 파일을 편집한 뒤 CR 개수를 읽기 전용으로 센다. CR이 1개 이상일 때만 아래 LF_NORMALIZE_COMMAND를 그 IMPLEMENT 단계에서 최대 1회 실행하고, CR이 0개이면 실행하지 않는다. 이 명령은 그 파일의 CRLF를 LF로 바꾸는 것 외에는 아무것도 바꾸지 않으며 다른 파일을 쓰지 않는다. 실행 전 바이트의 CRLF→LF 변환 결과 SHA-256을 먼저 계산하고, 실행 후 파일 SHA-256이 그 값과 같고 CR이 0개인지 확인한다.
  - LF_NORMALIZE_COMMAND: `C:/MoneyLab-pilot-delegation-02/.venv/Scripts/python.exe -I -B -c "import pathlib; p = pathlib.Path('C:/MoneyLab-pilot-delegation-02/tests/test_taskctl_lease.py'); p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n'))"`
  - 이 명령이 오류로 끝나거나 Guard·권한 검토에서 차단·거절되면 다른 방식으로 바꾸거나 다시 실행하지 않고 STOP한다. 이 조항은 오류·차단 뒤의 재시도 권한이 아니다.
  - 이 비교 방식이 CRLF 작업 파일과 맞지 않는 점은 taskctl의 알려진 한계로 보고한다. 이 task에서 운영 코드를 고치지 않는다.
- P5 시간과 실행
  - 일반 명령은 600초 안에 끝나야 한다. 넘으면 STOP한다.
  - CHECK_COMMAND_4는 명령 단위 `PYTHONDONTWRITEBYTECODE=1`과 `-B`를 함께 쓴다. 이 환경 변수는 그 명령과 그 하위 프로세스에만 적용되며 전역·영구 설정을 바꾸지 않는다. 검사 내용·단언·실행 범위와 ignored 보존 조건은 바꾸지 않는다.
  - 바이트코드 방지 검증 기준: TEST_FULL 전후 ignored 목록이 같고 taskctl TEST_FULL `step end --result ok`가 OK다. 다르면 STOP한다.
  - TEST_FULL(CHECK_COMMAND_4)은 BUDGET_PYTEST 안에서 TEST_FULL step마다 1회 실행한다. 실행 도구의 백그라운드 실행으로 시작하고 완료 알림을 기다린다. 폴링하지 않는다.
  - 3600초는 Agent가 관측하는 TEST_FULL 경과시간 한도다. 운영체제가 보장하는 강제 종료 한도가 아니다. 경과는 TEST_FULL 시작과 함께 시작한 3600초 대기 백그라운드 작업의 완료 알림으로 관측한다.
  - 상태 확인과 중단에는 실행 도구가 제공하는 백그라운드 작업 상태 확인·중단 기능만 쓴다. 그 기능의 동작과 결과를 추정하지 않는다. 새 종료 프로그램, Job Object 하네스, 별도 시험은 추가하지 않는다.
  - TEST_FULL이 끝나기 전에 3600초 경과를 관측하면 그 기능으로 TEST_FULL 작업의 중단을 요청하고, 이후 단계를 시작하지 않으며 STOPPED(BUDGET_TIME)로 보고한다.
  - 중단 요청이 실패하거나 TEST_FULL 작업의 종료를 도구 출력으로 확인할 수 없으면 결과 불명으로 보고하고 멈춘다. 종료되었다고 주장하거나 다시 실행하지 않는다.
  - TEST_FULL이 먼저 끝나면 대기 작업을 같은 기능으로 중단한다. 명령 완료 뒤에야 3600초 초과를 알게 되면 실제 경과시간과 한도 초과를 보고하고 다음 단계로 진행하지 않는다.
  - Guard·권한 검토를 피하기 위한 별칭·인코딩·명령 변형은 쓰지 않는다.
  - 예상 소요(추정, 보장 아님): SETUP 5–15분, TEST_TARGETED 1–4분, LINT 1분 이하, TYPECHECK 2분 이하, TEST_FULL 40–50분, CLEAN_E2E 5분, 전체 1.5–2.5시간.
- P6 PUBLISH 구간의 CI 조회
  - 조회는 `gh run view <RUN_ID> -R swk3169/MoneyLab --json ...`과 필요한 job 로그 구간의 단발 조회만 한다.
  - 진행 중이면 상태만 보고하고 그 turn을 끝낸다. 이후는 GATE_TRANSITION_RULES의 turn·세션 규칙을 따른다.
  - README §13 사전 검증 4는 REQUIRED_CI_CHECKS로 판정한다. 비필수 job 실패는 별도로 기록한다.
- P7 테스트 대상(IL)
  - 새 테스트 함수 이름은 아래 접두로 시작한다. 모든 링크와 대상은 tmp_path의 임시 저장소 안에서만 만들고, 임시 저장소 밖을 가리키지 않는다.
  - 각 IL 테스트는 tests/test_taskctl_cli.py의 make_repo, Taskctl, TASK를 쓴다. TASK는 "PILOT-X"이고, make_repo가 만드는 임시 Work Order는 docs/tasks/PILOT-X/WORK_ORDER.md이며 그 DELEGATION의 LEDGER_TASK_ID도 PILOT-X다. init은 Taskctl.init(base, c1)으로 `--task-id PILOT-X`를 넘긴다. 아래 경로의 PILOT-X는 이 TASK이며, 링크 경로는 ledger.LEDGER_ROOT와 TASK로 만든다.
  - IL1 `test_init_il1_`: data/processed/taskctl 자리에 임시 대상 디렉터리를 가리키는 심볼릭 링크. init 기대 PATH_INVALID.
  - IL2 `test_init_il2_`: data/processed/taskctl 자리에 깨진 심볼릭 링크. init 기대 PATH_INVALID.
  - IL3 `test_init_il3_`: 실제 data/processed/taskctl 아래 data/processed/taskctl/PILOT-X 자리에 심볼릭 링크. init 기대 PATH_INVALID.
  - IL4 `test_init_il4_`: Windows에서 data/processed/taskctl 자리에 junction(대상 존재, 대상 삭제 두 경우). init 기대 PATH_INVALID.
  - IL5 `test_init_il5_`: Windows에서 data/processed/taskctl/PILOT-X 자리에 junction. init 기대 PATH_INVALID.
  - IL1–IL5 공통 기대: 링크 자체와 링크 대상의 내용(파일 이름·바이트)이 바뀌지 않는다. 대상 안에 원장 파일이 생기지 않는다. 저장소 HEAD와 git status 출력이 바뀌지 않는다.
  - IL6 `test_init_il6_`: 정상 경로. data/processed/taskctl이 없을 때 init이 OK이고, 생성된 data/processed/taskctl, data/processed/taskctl/PILOT-X, events가 링크·재분석 지점이 아닌 일반 디렉터리이며, events/000001.json이 일반 파일이다.
  - 링크를 만들 수 없는 플랫폼·권한에서는 해당 항목을 NOT_RUN_PLATFORM으로 skip하고 보고한다. 실행하지 못한 항목은 통과로 표시하지 않는다.
  - 검사와 사용 사이의 경로 변경 경쟁(TOCTOU)은 이 task의 검증 범위 밖이다.
- P8 수집 ID 대조
  - COLLECT_COMMAND: `cd C:/MoneyLab-pilot-delegation-02 && ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q tests/test_taskctl_cli.py tests/test_taskctl_lease.py tests/test_taskctl_ledger.py tests/test_taskctl_check.py`
  - IMPLEMENT의 첫 편집 전에 COLLECT_COMMAND로 기준 ID 목록을 얻는다(기대 127개). LOCAL_AUDIT에서 다시 수집해, 기준 ID가 모두 남고 추가된 ID가 모두 test_init_il로 시작하는지 ID 단위로 대조한다.
  - TEST_TARGETED(-v) 출력의 테스트 ID 목록과 수집 목록 중 -k "test_init"에 해당하는 ID를 ID 단위로 대조해, IL1–IL6의 모든 ID가 선택·실행되었는지 확인한다. 개수만으로 판단하지 않는다.
- P10 구현 재사용
  - 구현 후보는 C:/MoneyLab-pilot-delegation-01/tests/test_taskctl_lease.py에 보존된 바이트(SHA-256 c3aeaf64c75295264424312f1812cb3690a831d39fc6442ba14962f5fa0245e1, LF)다. BASE blob 대비 차이는 `import stat`, `is_link_like` import, IL1–IL6 블록의 삽입뿐이다(삭제·수정 0).
  - 최초 IMPLEMENT에서 복사 전에 원본 SHA-256이 위 값인지 읽기 전용으로 확인하고, REUSE_COMMAND 1회로 복사한 뒤 대상 파일 SHA-256이 같은 값인지 확인한다. 다르면 STOP한다.
  - REUSE_COMMAND: `C:/MoneyLab-pilot-delegation-02/.venv/Scripts/python.exe -I -B -c "import pathlib; pathlib.Path('C:/MoneyLab-pilot-delegation-02/tests/test_taskctl_lease.py').write_bytes(pathlib.Path('C:/MoneyLab-pilot-delegation-01/tests/test_taskctl_lease.py').read_bytes())"`
  - 이 명령이 오류로 끝나거나 차단·거절되면 다른 방식으로 바꾸거나 다시 실행하지 않고 STOP한다. 원본 파일은 읽기만 한다.
  - 수정 반복의 IMPLEMENT에서는 ALLOWED_FILES만 편집하고 P4를 따른다.
- P11 실행 순서
  - 상태 변경 명령(taskctl 기록, git add·commit, 파일 쓰기, 설치)은 각각 별도 도구 호출로 실행하고, exit code와 taskctl code를 확인한 뒤 다음 명령을 실행한다.
  - 선행 결과에 의존하는 조회·검사는 그 결과를 확인하기 전에 병렬로 보내지 않는다. 서로 독립인 읽기 전용 조회만 병렬로 보낼 수 있다.
  - CHECK_COMMAND와 COLLECT_COMMAND의 `cd <경로> &&` 결합은 하나의 검사 명령이며 이 원칙의 "명령 연결"에 해당하지 않는다.
  - STOP 조건이 생기면 그 호출과 이후 호출에서 후속 단계·명령을 실행하지 않는다.
- P9 예상 도구 승인
  - 예상되는 승인 창(통과를 보장하지 않음): git commit(C1, I), git push, gh pr create, gh pr merge.
  - 불확실한 것: worktree add, Work Order Write(docs/tasks 경로), pip 설치(네트워크), REUSE_COMMAND·LF_NORMALIZE_COMMAND(inline python 파일 쓰기), CHECK_COMMAND_4(명령 단위 환경 변수 접두), gh 로그 조회.
  - 예상 밖 ASK, 거절, 무응답, DENY는 STOP이다.

## DELEGATED_PROCEDURE

DELEGATED_PROCEDURE:
- 1. 기준 확인: `git -C C:/MoneyLab-gov-automation-03 fetch origin refs/heads/main:refs/remotes/origin/main` 1회 뒤 origin/main = CANONICAL_BASE_SHA를 확인한다. 다르면 STOP한다. TARGET_WORKTREE 경로와 TARGET_BRANCH가 없는지, P2 사전 확인이 통과하는지 확인한다.
- 2. `git -C C:/MoneyLab-gov-automation-03 worktree add -b codex/pilot-delegation-02 C:/MoneyLab-pilot-delegation-02 2f1309879f58307c6208e91cfb2c19c74110aecf`
- 3. DELEGATE의 WO_SHA256과 같은 바이트로 Work Order를 Write 1회로 만들고, 그 경로만 `git -C C:/MoneyLab-pilot-delegation-02 add --` 후 C1을 커밋한다. 작업 파일과 staged blob의 SHA-256 = WO_SHA256을 확인한다.
- 4. taskctl init(P2). 기대 OK.
- 5. SETUP_ENV: step start → SETUP_COMMAND_1..5 순서 실행 → P3 준비 완료 조건 확인 → step end. 이어서 `phase-set --to SETUP_DONE`.
- 6. IMPLEMENT: step start → (최초 IMPLEMENT에서만) P8 기준 수집과 P10 재사용 복사·해시 확인 → (수정 반복에서는) ALLOWED_FILES 편집 → P4에 따른 CR 확인과 조건부 LF 정규화 → step end.
- 7. TEST_TARGETED(CHECK_COMMAND_1), LINT(CHECK_COMMAND_2), TYPECHECK(CHECK_COMMAND_3), TEST_FULL(CHECK_COMMAND_4, P5)을 각각 step으로 실행한다. 테스트·ruff·mypy가 실패로 끝나면 그 step을 fail로 기록하고, BUDGET 안에서 6으로 돌아가 ALLOWED_FILES만 고친다. 실패 원인이 운영 코드이면 STOP한다. 셸·도구 오류, 결과 불명, P5의 경과 한도 관측은 수정 반복 대상이 아니며 STOP한다.
- 8. LOCAL_AUDIT: TEST_GATES의 감사 항목과 P8 대조를 확인한다.
- 9. LOCAL_COMMIT: `git -C C:/MoneyLab-pilot-delegation-02 add -- tests/test_taskctl_lease.py`, `git -C C:/MoneyLab-pilot-delegation-02 diff --cached --check`, 그리고 COMMIT_PLAN 메시지로 커밋 1회.
- 10. CLEAN_E2E: E2E_GATES.
- 11. `phase-set --to LOCAL_DONE`.
- 12. PR 본문을 확정해 `pr-text --sha256 <hex>`로 기록한다. 본문은 변경 내용, 검사 결과, 로컬 플랫폼 skip, 한계, 위반 여부를 담는다.
- 13. `phase-set --to READY_TO_PUBLISH`.
- 14. `publish-draft`가 만든 PUBLISH 문장을 READY_TO_PUBLISH 보고에 넣고 멈춘다.
- 15. PUBLISH를 받으면 `record-message --kind PUBLISH`로 기록하고 `phase-set --to PUBLISHING`.
- 16. PUSH: `git -C C:/MoneyLab-pilot-delegation-02 push -u origin codex/pilot-delegation-02` 1회.
- 17. PR_CREATE: `gh pr create -R swk3169/MoneyLab --base main --head codex/pilot-delegation-02 --title "test: cover taskctl init path links" --body-file C:/MoneyLab-pilot-delegation-02/data/processed/taskctl/PILOT-DELEGATION-02/pr_text.md` 1회.
- 18. CI_WAIT: P6. PREMERGE_CHECK: README §13 사전 검증 1–7.
- 19. MERGE: `gh pr merge <N> -R swk3169/MoneyLab --merge --match-head-commit <I>` 1회. 이어서 `phase-set --to MERGED`.
- 20. POST_MERGE_AUDIT: 1과 같은 fetch 1회, parent 순서, tree, first-parent, ancestry, merge-tree 재계산, 변경 경로 2개, blob 해시, branch·worktree 보존. 심볼릭 ref(origin/HEAD)의 파생값은 실제 ref 변경과 구분한다. 이어서 `phase-set --to AUDITED`.
- 21. 최종 보고와 `phase-set --to TERMINAL --terminal-status <COMPLETE|CLOSED_WITH_VIOLATION> --violations <n>`.

## TEST_GATES

TEST_GATES:
- P7의 IL1–IL6을 tests/test_taskctl_lease.py에 추가하고 각 기대 코드와 불변 조건을 단언한다.
- P8 대조: 기준 taskctl 테스트 ID가 모두 남고, 추가 ID는 모두 test_init_il로 시작한다. 기존 단언 삭제·완화, skip·xfail 추가는 없다(새 테스트의 NOT_RUN_PLATFORM skip은 P7 규칙에 따른다).
- CHECK_COMMAND_1–4가 실패 0으로 끝난다. 로컬 플랫폼 skip은 항목별로 보고한다.
- 공백·끝 LF 검사: `git -C C:/MoneyLab-pilot-delegation-02 diff --check`와 `git -C C:/MoneyLab-pilot-delegation-02 diff --cached --check`가 exit 0이고, 대상 파일의 CR 0개, 줄 끝 공백 0줄, 끝 LF 1개를 확인한다.
- 변경 집합 = ALLOWED_FILES이고 변경 한정을 지킨다.

## E2E_GATES

E2E_GATES:
- CLEAN_E2E: HEAD = I, parent(I) = C1, 커밋 파일 집합 = ALLOWED_FILES, commit blob SHA-256 = 작업 파일 SHA-256, CHECK_COMMAND_1 재실행 실패 0, 실행 전후 git status(ignored 포함) 동일.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base, C1, I, merge의 SHA·tree·parents, 파일 SHA-256(W·S), 커밋 파일 집합.
- CLAUDE_REPORTED: 각 CHECK 결과와 집계, 소요 시간, taskctl 결과 JSON의 code, 원장 이벤트 수, P3·P8 확인 결과.
- INDEPENDENT: PR CI(필수 Windows job), 사용자의 GitHub 화면 확인.

## REQUIRED_REPORT

REQUIRED_REPORT:
- 위임 경로 검증과 테스트 기능 검증을 나눠 보고한다.
  - 위임 경로: DELEGATE·PUBLISH 각 1건으로 진행했는지, taskctl phase 전이와 step 기록, 예산 사용, 예상·예상 밖 승인 창, 중단과 재개.
  - 테스트 기능: IL1–IL6 결과. 로컬에서 실행한 것, 로컬 플랫폼 skip, CI에서 실제 실행한 것을 분리한다.
- READY_TO_PUBLISH 보고: 단계별 결과, 검사 집계와 skip, W·S, I의 SHA·tree, taskctl status(phase·budget·open_step), publish-draft의 PUBLISH 문장, 위반 여부.
- 최종 보고: CI 증거, merge 구조 감사, 종결 상태(DL-8), 남은 한계. 무인 운영·수익성 달성은 주장하지 않는다.

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, Work Order SHA-256 불일치, origin/main ≠ CANONICAL_BASE_SHA, P2 사전 확인 실패.
- P3 준비 완료 조건 실패.
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, 예상 밖 untracked·ignored 산출물.
- taskctl이 OK가 아닌 code를 반환. 원장 무효, LEASE 잔존, REVOKED, 만료, 예산 초과.
- 테스트 실패 중 원인이 운영 코드인 것. 같은 실패 연속 BUDGET_SAME_FAIL회. 일반 명령 600초 초과. TEST_FULL 경과 3600초 초과 관측(P5).
- Guard DENY, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명. 중단 후 다른 도구로 같은 작업을 계속하지 않는다. STOP 이후에는 후속 단계·명령을 실행하지 않는다(P11).
- P10 원본·복사본 해시 불일치. TEST_FULL 전후 ignored 목록 변화.
- 계약 모순, 상위 규칙과 충돌.

## DELEGATION

DELEGATION_SCHEMA: moneylab.delegation/1
LEDGER_TASK_ID: PILOT-DELEGATION-02
BUDGET_TIME_SECONDS: 10800
BUDGET_FIX: 3
BUDGET_PYTEST: 2
BUDGET_SAME_FAIL: 2
REQUIRED_CI: pytest
PR_TITLE: test: cover taskctl init path links
SETUP_COMMAND_1: C:/MoneyLab-gov-automation-03/.venv/Scripts/python.exe -I -B -m venv C:/MoneyLab-pilot-delegation-02/.venv
SETUP_COMMAND_2: C:/MoneyLab-pilot-delegation-02/.venv/Scripts/python.exe -B -m pip install --isolated --disable-pip-version-check --no-input --no-cache-dir --index-url https://pypi.org/simple --no-binary=mypy -r C:/MoneyLab-pilot-delegation-02/requirements-dev.txt
SETUP_COMMAND_3: C:/MoneyLab-pilot-delegation-02/.venv/Scripts/python.exe -B -m pip install --isolated --disable-pip-version-check --no-input --no-cache-dir --index-url https://pypi.org/simple --no-deps -e C:/MoneyLab-pilot-delegation-02
SETUP_COMMAND_4: C:/MoneyLab-pilot-delegation-02/.venv/Scripts/python.exe -B -m pip check
SETUP_COMMAND_5: C:/MoneyLab-pilot-delegation-02/.venv/Scripts/python.exe -B -m mypy --version
CHECK_COMMAND_1: cd C:/MoneyLab-pilot-delegation-02 && ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -rs -v --durations=30 tests/test_taskctl_lease.py tests/test_taskctl_cli.py -k "test_init"
CHECK_COMMAND_2: cd C:/MoneyLab-pilot-delegation-02 && ./.venv/Scripts/python.exe -B -m ruff check --no-cache src tests
CHECK_COMMAND_3: cd C:/MoneyLab-pilot-delegation-02 && ./.venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache
CHECK_COMMAND_4: cd C:/MoneyLab-pilot-delegation-02 && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -rs
