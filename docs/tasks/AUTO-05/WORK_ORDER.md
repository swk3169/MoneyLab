Work Order: AUTO-05 — executor 자식 Python의 바이트코드 자동 기록 통제

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/AUTO-05/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: AUTO-05
TASK_ID: AUTO-05
TITLE: knowledge_validate 자식 Python argv에 -B를 추가해 자식 인터프리터의 자동 바이트코드 기록을 끈다
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: d1b26d3b8e38db43e575ac8a7316cb53b02c2371
CANONICAL_BASE_TREE: e362a6cca2eeaf6cd36aa851e2342c1b1265e902
SOURCE_WORKTREE: <SOURCE_WORKTREE> (fetch와 worktree 생성 명령의 실행 위치. 기존 파일·브랜치·index·ignored 산출물은 변경하지 않는다)
TARGET_BRANCH: codex/auto-05-child-bytecode
TARGET_WORKTREE: <TARGET_WORKTREE> (생성 전 부재해야 하는 새 worktree 경로)
BASE_PYTHON: <BASE_PYTHON> (Python 3.14.8 실행 파일)
VENV_PYTHON: TARGET_WORKTREE 기준 ./.venv/Scripts/python.exe
WORKSPACE_SETUP: REQUIRED (SUBPHASE: MAIN_REF_FETCH_ONLY -> WORKTREE_CREATION_ONLY -> C1_CREATION_ONLY -> ENVIRONMENT_PREPARATION_ONLY)
INITIAL_GATE: WORKSPACE_SETUP / MAIN_REF_FETCH_ONLY
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests job pytest, Windows runner, exact PR head SUCCESS
BUNDLE_ELIGIBLE: NO
BUNDLE_MAX_RANGE: NONE
FILE_FORMAT: UTF-8, BOM 없음, LF, 끝 LF 1개, 일반 공백만 사용(U+00A0·탭·줄 끝 공백 금지)

PATH_VARIABLES

- SOURCE_WORKTREE, TARGET_WORKTREE, BASE_PYTHON은 이 계약의 식별 변수다. 실제 절대 경로와 그 값을 넣은 명령 원문은 각 변수를 처음 쓰는 단계의 사용자 승인문에서 고정한다. SOURCE_WORKTREE는 MAIN_REF_FETCH_ONLY에서, TARGET_WORKTREE는 WORKTREE_CREATION_ONLY에서, BASE_PYTHON은 ENVIRONMENT_PREPARATION_ONLY에서 고정한다.
- 승인문에 값이 없거나 값이 기대 상태와 다르면 중단한다. 다른 실행 파일이나 작업공간을 임의로 고르지 않는다.
- 공개 기록(Work Order, 커밋 메시지, PR 본문)과 테스트 출력에는 절대 경로, 사용자 이름, 세션 식별값을 넣지 않는다. 로컬 도구 입력과 채팅 보고에서 경로를 쓰는 것은 별개다.

CROSS_TASK_SUPERSESSION

- 대상: docs/tasks/AUTO-01/WORK_ORDER.md의 DESIGN_CONTRACT.D2 고정 argv 정의.
- 근거: 저장소 규칙(docs/tasks/README.md)에는 다른 task의 설계 조항을 대체하는 일반 절차가 없다. 이 대체는 AUTO-05 CONTRACT_REVIEW에서 사용자가 명시적으로 수락한 결정에 근거하며, 이 Work Order가 자동으로 우선한다는 뜻이 아니다.
- 범위: AUTO-05 구현이 main에 병합된 이후의 코드 동작에 한해, argv의 인터프리터 뒤·-m 앞에 -B 한 원소를 추가하는 것만 대체한다. 그 밖의 원소와 순서, AUTO-01 D1·D3–D9와 AUTO-01 ERRATA-001은 그대로 유지한다.
- 보존: AUTO-01 계약 파일과 AUTO-01 당시의 계약 준수·완료 이력은 바꾸지 않는다. 다른 task 조항을 일반적으로 대체할 권한은 부여하지 않는다.
- 저장소 절대 규칙, 고정·사전등록 계약, Guard·hook·settings, 도구 권한은 바꾸지 않는다.
- 기록: PR_CI에서 만드는 PR 본문에 이 대체의 대상(AUTO-01 D2 고정 argv), 범위(인터프리터 뒤·-m 앞 -B 한 원소, 병합 이후 코드 동작에 한함), 근거(AUTO-05 CONTRACT_REVIEW에서의 사용자 명시 수락), 보존 사항(AUTO-01 계약 파일과 당시 이력 불변)을 적는다. PR 본문 문구는 PR_CI 승인문에서 확정한다.

GATE_SEQUENCE

DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

GATE_TRANSITION_RULES

- C1 이전의 CONTRACT_REVIEW PASS는 후보 문안에 대한 검토 판정이며 계약 발행이 아니다. 이 Work Order는 C1 커밋에 포함된 바이트로만 발행된다.
- 각 gate와 하위 단계는 사용자의 명시적 승인 범위에서만 수행한다. 하나의 승인으로 둘 이상의 하위 단계를 진행하지 않는다.
- C1 이후에는 GATE_AUTHORIZATION: AUTO-05 <GATE> WO@<C1 SHA>를 사용한다.
- IMPLEMENTATION 하위 단계는 CODE_CHANGE, TARGETED_CHECKS, STATIC_CHECKS, FULL_PYTEST 순서다. 각각 따로 승인한다.
- 검사가 실패하면 보고하고 멈춘다. 수정은 IMPLEMENTATION CODE_CHANGE의 새 승인으로만 하고, 그 뒤의 재검사도 각각 새 승인으로 한다. 자동 재실행·재시도는 없다.
- PUSH, PR_CI, MERGE, POST_MERGE_AUDIT, COMPLETE, 후퇴는 각각 개별 승인이다. COMMIT 이후 수정은 새 커밋으로 한다. amend는 금지한다.

ABSOLUTE_RULES

CLAUDE.md, .claude의 guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약을 따른다. 이 Work Order는 이들을 변경하거나 덮어쓰지 않는다.

GOAL

moneylab.automation.policy.build_argv가 만드는 knowledge_validate 자식 명령에 -B를 추가해, 그 자식 인터프리터가 자동으로 바이트코드 캐시를 기록하지 않게 한다. 실험군·대조군 실제 자식 검사로 효과를 오프라인에서 확인한다. AUTO-04에서 관측된 문제의 원인 후보를 통제하는 최소 변경이며, AUTO-04 사례의 판정은 바꾸지 않는다.

NON_GOALS

- 작업자가 테스트 밖에서 별도로 수행하는 실제 action 실행과 새 통합 사례. AUTO-04 E0–E6 재실행을 포함한다. D7이 승인한 기존 오프라인 테스트 안의 run_action 호출, 모의 실행, 테스트가 정한 임시 작업공간 안의 실제 자식 실행은 이 항목에 해당하지 않는다.
- 환경 allowlist, timeout, 출력 상한, 회수, 1회 실행 lock의 변경
- 실행 전 시도 기록, 중복 실행 방지, scheduler, 무인 운영
- 파일 쓰기 격리, sandbox, 보안 경계
- Guard, settings, CI, README 변경
- AUTO-04 worktree·계약·사례·캐시와 AUTO-01 계약 파일의 변경
- Linux wrapper 실패 2건, AUTO-04 통합 시험 FAIL, 기존 Git garbage 경고의 해결
- OpenClaw 호출

ALLOWED_ACTIONS

- MAIN_REF_FETCH_ONLY: git -C <SOURCE_WORKTREE> fetch origin refs/heads/main:refs/remotes/origin/main 1회. 이어서 refs/remotes/origin/main이 CANONICAL_BASE_SHA이고 그 tree가 CANONICAL_BASE_TREE인지 확인한다. 다르면 중단한다.
- WORKTREE_CREATION_ONLY: TARGET_BRANCH와 TARGET_WORKTREE가 없는지 확인한 뒤 git -C <SOURCE_WORKTREE> worktree add -b codex/auto-05-child-bytecode <TARGET_WORKTREE> d1b26d3b8e38db43e575ac8a7316cb53b02c2371 1회.
- C1_CREATION_ONLY: 승인 바이트의 docs/tasks/AUTO-05/WORK_ORDER.md를 Write 도구로 최초 1회 생성한다. 작성 전 메모리 대조와 작성 후·staged·commit blob 해시 대조를 하고, 그 경로만 stage해 C1 커밋 1개를 만든다. 메시지는 docs(task): add AUTO-05 work order다.
- ENVIRONMENT_PREPARATION_ONLY: TARGET_WORKTREE에 .venv를 만들고 requirements.txt와 requirements-dev.txt의 고정 버전을 설치한 뒤 pip install -e . --no-deps를 실행한다. 대상 venv의 실행·개발 의존성은 고정 목록의 이름과 버전만 허용한다. mypy는 requirements-dev.txt의 고정 버전을 유지하고 공식 소스 배포판으로 설치한다. editable 설치와 mypy 소스 빌드에 필요한 격리 빌드 의존성은 pip의 격리 빌드 환경 안에서만 쓰며, 그 설치 출처와 허용 범위는 이 단계 승인문에서 고정한다. 이를 대상 venv에 빌드 의존성을 추가 설치할 권한으로 해석하지 않는다. 정확한 명령은 승인문에서 고정한다. pip 업그레이드, 고정 목록 밖 패키지의 대상 venv 설치, 별도 출처, Windows 보안 정책 변경, 정책 차단 뒤 임의 재설치는 허용하지 않는다. 확인 항목은 D6을 따른다.
- IMPLEMENTATION / CODE_CHANGE: ALLOWED_FILES만 수정한다.
- IMPLEMENTATION / TARGETED_CHECKS, STATIC_CHECKS, FULL_PYTEST: D7의 명령만 정해진 횟수로 실행한다.
- PRECOMMIT_AUDIT: 읽기 전용 감사와 W·S 확정만 한다.
- COMMIT: ALLOWED_FILES만 경로를 지정해 stage하고 구현 커밋 I 1개를 만든다. I의 parent는 C1이다. 메시지는 COMMIT 승인문에서 고정한다.
- CLEAN_COMMIT_E2E: D7의 clean commit 검사만 한다.
- PUSH: git push -u origin codex/auto-05-child-bytecode 1회.
- PR_CI: README §13의 PR_CREATE: YES와 필수 값이 있을 때 PR 생성 1회, 이후 해당 head의 CI 조회와 D10의 기록.
- MERGE: README §13의 사전 조건과 MERGE_EXECUTE: YES 승인 뒤, 정확한 head로 merge commit 방식 1회.
- POST_MERGE_AUDIT: 읽기 전용 감사. fetch는 승인문이 정한 main ref 1회만 한다.
- COMPLETE: 채팅 최종 보고만 한다.
- 승인문에 없는 trailer는 넣지 않는다.

ALLOWED_FILES

ALLOWED_FILES:
- src/moneylab/automation/policy.py
- tests/test_automation_policy.py
- tests/test_automation_executor.py

PROTECTED_FILES

ALLOWED_FILES 밖의 모든 저장소 파일은 보호 대상이다. .claude 아래 전체, .github 아래 전체, docs/tasks 아래 전체, docs/research-intake 아래 전체, src/moneylab/automation/executor.py, pyproject.toml, requirements.txt, requirements-dev.txt를 포함한다.
보호 대상의 예외는 docs/tasks/AUTO-05/WORK_ORDER.md의 C1 최초 생성 하나다. 이 예외는 ALLOWED_FILES에 속하지 않는다.
ALLOWED_FILES와 PROTECTED_FILES의 교집합은 없어야 한다.

COMMIT_PLAN

- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/AUTO-05/WORK_ORDER.md 하나
- I: parent = C1, 변경 = ALLOWED_FILES 중 실제로 바뀐 파일(M), 3개 이하
- base..I: C1 파일과 I 파일뿐

FORBIDDEN_ACTIONS

- 승인 범위 밖 작업, 보호 파일 변경, ALLOWED_FILES 밖 파일 생성·수정
- git add . 또는 git add -A, amend, --no-verify, force push, reset, restore, stash, clean, rebase, cherry-pick
- 다른 branch·worktree, 기존 untracked·ignored·reference 산출물의 변경이나 정리. AUTO-04 worktree와 그 캐시·snapshot·runlog의 조회·변경·삭제
- 작업자가 테스트 밖에서 run_action을 호출하거나 knowledge_validate를 실제로 실행하는 것, 새 통합 사례 실행, AUTO-04 E0–E6 재실행. D7이 승인한 테스트 명령이 그 테스트 코드 안에서 수행하는 run_action 호출, 모의 실행, 실제 자식 실행은 그 테스트가 정한 임시 작업공간과 기존 검사 범위 안에서만 허용한다.
- 파일로 된 임시 스크립트, scratchpad, 출력 리디렉션
- 보호 경로 이름과 수정 명령 단어를 한 셸 명령에 결합
- Guard DENY나 권한 거절 뒤 재시도, 변형, 우회
- Windows 보안 설정 변경, 정책 차단 뒤 임의 재설치
- 확인을 위한 CI 설정 변경
- 네트워크 사용(ENVIRONMENT_PREPARATION_ONLY의 승인된 설치, MAIN_REF_FETCH_ONLY, PUSH·PR_CI·MERGE·POST_MERGE_AUDIT의 정해진 명령은 제외), OpenClaw 호출
- 한국어와 필요한 영어 외 언어 사용

DESIGN_CONTRACT

- D1 argv: policy.build_argv(root)는 [interpreter(), "-B", "-m", "moneylab.knowledge", "--root", str(root), "validate"]를 반환한다. interpreter()는 기존과 같이 sys.executable을 검증해 쓴다. 다른 원소와 순서는 바꾸지 않는다. policy.py의 docstring에 이 변경과 CROSS_TASK_SUPERSESSION 근거를 적을 수 있다.
- D2 불변: build_env의 allowlist(PATH = git 디렉터리 하나, Windows에서 SYSTEMROOT), repo_root, decide, status_for_exit_code, TIMEOUT_SECONDS, OUTPUT_LIMIT_BYTES, executor의 Popen 인자(shell=False, cwd, env, stdin=DEVNULL, stdout·stderr PIPE), 회수, 출력 상한, 1회 실행 lock은 바꾸지 않는다. executor.py는 수정하지 않는다.
- D3 효과와 한계:
  - -B는 executor가 띄운 자식 인터프리터의 자동 바이트코드 기록을 끈다(sys.flags.dont_write_bytecode).
  - sys.pycache_prefix는 자동 캐시의 위치를 바꾸는 설정이다. -B가 켜진 상태에서 자동 기록을 허용하는 예외가 아니다. build_env는 PYTHONPYCACHEPREFIX와 PYTHONDONTWRITEBYTECODE를 전달하지 않는다.
  - -B는 기존 유효 캐시의 읽기·사용, 임의 코드의 명시적 파일 쓰기, 호출자(상위) 프로세스의 캐시 기록을 금지하지 않는다.
  - -B는 손자 Python에 자동으로 전달되지 않는다.
  - 이 변경은 파일 쓰기 격리나 보안 경계가 아니다.
- D4 Guard: 테스트의 기존 Guard 호환 검사(test_guard_passes_the_fixed_command, test_guard_still_stops_the_forbidden_variant)가 새 argv로 그대로 통과해야 한다. Guard 판정이 PASS가 아니면 중단하며 Guard를 수정하지 않는다.
- D5 테스트 변경:
  - tests/test_automation_policy.py: test_argv_is_fixed의 기대값을 D1로 바꾸고, argv[1] == "-B"이며 "-B"가 "-m"보다 앞인지 확인한다. env allowlist와 Guard 호환 검사는 바꾸지 않는다.
  - tests/test_automation_executor.py: test_fixed_popen_call의 기대 argv를 D1로 바꾼다. env == policy.build_env()와 shell=False 확인은 유지한다.
  - tests/test_automation_executor.py에 실제 자식 비교 검사를 추가한다.
    - pytest tmp_path 아래에 서로 분리된 experiment와 control 디렉터리를 만든다. 각 디렉터리에 probe_pkg/__init__.py, probe_pkg/mod.py, probe_pkg/__main__.py를 쓴다.
    - probe_pkg/__main__.py는 probe_pkg.mod를 import한 뒤 sys.stdout.buffer.write(("dont_write_bytecode=" + str(bool(sys.flags.dont_write_bytecode)) + "\n").encode("ascii"))로 정확히 한 줄을 쓴다. 바이너리 버퍼에 직접 써서 Windows의 텍스트 모드 줄바꿈 변환을 피하고, 두 운영체제에서 같은 바이트를 비교한다.
    - 실험군 argv는 policy.build_argv(policy.repo_root())[:2] + ["-m", "probe_pkg"]이다. 운영 argv의 앞 두 원소(인터프리터, -B)만 재사용하고, 모듈과 인자는 탐침으로 바꾼다.
    - 대조군 argv는 [policy.build_argv(policy.repo_root())[0], "-m", "probe_pkg"]로, -B만 뺀 것이다.
    - 두 군은 executor._execute(argv, <각 디렉터리>, policy.build_env(), timeout=30.0)으로 실제 실행한다. Popen spy는 실제 subprocess.Popen을 그대로 호출하고 반환된 프로세스 객체를 수집하는 관측용으로만 쓰며, 실행을 대체하지 않는다.
    - 회수 확인: 이 검사에서 시작된 프로세스가 정확히 2개(실험군 1, 대조군 1)이고, 두 프로세스 모두 poll()이 None이 아닌 종료 상태다. reader thread 확인은 해당 _execute 호출이 생성한 stdout·stderr reader thread 객체에 한정한다. 관측용 spy는 실제 Thread 생성과 실행을 그대로 유지하며 해당 객체를 수집한다. 호출 완료 뒤 수집한 reader thread가 모두 종료됐는지 확인한다. 전체 threading.enumerate()의 전후 차이만으로 해당 호출의 소유 스레드를 판단하지 않는다.
    - 실험군 합격: status SUCCEEDED, exit_code 0, stdout == b"dont_write_bytecode=True\n", stderr == b"", 실험군 디렉터리 아래 __pycache__ 디렉터리 0개와 *.pyc 파일 0개, 위 회수 확인 통과.
    - 대조군 합격: status SUCCEEDED, exit_code 0, stdout == b"dont_write_bytecode=False\n", stderr == b"", 대조군 디렉터리 아래 *.pyc 파일 1개 이상, 위 회수 확인 통과.
    - 대조군에서 *.pyc 파일이 0개이면 검사 전제 불충족이다. skip·xfail·통과로 바꾸지 않고, "control produced no bytecode: precondition not met" 메시지로 실패시킨다.
    - 이 검사는 저장소 안의 기존 캐시를 읽거나 지우거나 재사용하지 않는다. 대상은 각 tmp 디렉터리뿐이다.
    - 이 검사는 knowledge_validate 전체 경로의 E2E가 아니다. 운영 argv 옵션이 자식 인터프리터에 미치는 효과만 확인한다.
- D6 환경 확인(ENVIRONMENT_PREPARATION_ONLY):
  - Python 3.14.8, sys.prefix가 TARGET_WORKTREE의 .venv, moneylab.__file__이 TARGET_WORKTREE의 src 아래.
  - requirements.txt와 requirements-dev.txt의 고정 이름·버전 일치, pip check 통과.
  - 설치 후 대상 venv의 배포판 목록이 고정 목록, moneylab, pip 외의 항목을 담지 않는지 확인한다. 추가 항목이 있으면 보고하고 멈춘다.
  - ./.venv/Scripts/python.exe -B -m mypy --version 출력이 mypy 2.4.0인지 확인하고 compiled 여부를 기록한다. 소스 배포판 설치이므로 compiled: no를 기대한다.
  - 정책 차단이 생기면 원인을 단정하지 않고 보고하고 멈춘다. Windows 보안 설정을 바꾸거나 다른 방식으로 임의 재설치하지 않는다.
  - 환경 확인용 Python 명령은 -B로 실행한다.
- D7 검사 순서와 횟수(작업 디렉터리 TARGET_WORKTREE, 부모 Python은 모두 -B):
  - IMPLEMENTATION / TARGETED_CHECKS 1회: ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -rfEsxXp tests/test_automation_policy.py tests/test_automation_executor.py
  - IMPLEMENTATION / STATIC_CHECKS 1회: ruff check(명시 경로 3개), ruff check(기본 전체), mypy(기본 설정), mypy src/moneylab/automation(명시 경로). 결과는 각각 따로 보고한다.
  - IMPLEMENTATION / FULL_PYTEST 1회: ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -rfEsxXp
  - CLEAN_COMMIT_E2E 1회씩: 전체 pytest(같은 명령), ruff check(기본 전체), mypy(기본 설정), mypy src/moneylab/automation.
  - 출력은 잘라내거나 필터하지 않는다. 같은 gate에서 전체 pytest를 다시 실행하지 않는다.
- D8 프로세스 구분과 산출물:
  - 테스트 부모(pytest)는 -B로 실행한다. 부모의 -B만으로 모든 자식의 캐시가 억제된다고 가정하지 않는다.
  - 실제 자식 비교 검사의 자식은 tmp_path 안에서만 캐시를 쓰거나 쓰지 않는다.
  - 그 밖의 테스트 자식(예: knowledge·guard 관련 테스트가 띄우는 Python)은 -B 없이 저장소 안에 캐시를 쓸 수 있다. 이는 이번 변경의 효과 범위가 아니며 허용 산출물로 기록한다.
  - TARGET_WORKTREE의 허용 ignored 산출물: .venv 디렉터리, src/moneylab.egg-info 디렉터리, src 아래와 tests 아래의 __pycache__ 디렉터리, .mypy_cache 디렉터리, .ruff_cache 디렉터리. -p no:cacheprovider를 쓰므로 .pytest_cache 디렉터리는 기대하지 않는다.
  - pytest tmp_path는 저장소 밖의 사용자 임시 디렉터리에 생긴다. 그 안의 탐침 파일과 캐시는 허용 산출물이며 정리하지 않는다. 저장소 안에 tmp 산출물이 생기면 중단한다.
  - 허용 목록 밖의 새 ignored 항목, ALLOWED_FILES 밖의 tracked·untracked 변경이 관측되면 원인을 단정하지 않고 중단한다.
- D9 기존 이력: AUTO-04 통합 시험 최종 판정 FAIL, AUTO-04 ERRATA-002, Linux wrapper 실패 2건, git count-objects garbage 경고는 바꾸지 않으며 해결된 것으로 표시하지 않는다.
- D10 CI 검사 대상 기록: PR_CI에서 PR head SHA, CI run의 headSha, job이 실제로 checkout한 커밋의 SHA와 tree를 각각 기록한다. 실제 checkout 커밋이 GitHub의 PR 시험용 merge commit이면 그 사실과 parent 관계(base와 PR head), tree를 GitHub API로 확인해 기록한다. 이 결과를 PR head 커밋 자체에서 테스트한 것으로 표현하지 않는다. 확인을 위해 CI 설정을 바꾸지 않는다.

TEST_GATES

- D7의 TARGETED_CHECKS: 실패 0, 새 실제 자식 비교 검사 통과.
- D7의 STATIC_CHECKS: ruff 위반 0. mypy 기본·명시 경로는 오류 0을 기대하며, 오류가 있으면 기존 오류인지 변경 때문인지 구분해 보고하고 멈춘다.
- D7의 FULL_PYTEST: 실패 0. skip과 xfail 목록을 기준 커밋의 기존 목록과 대조해 보고한다.
- 변경 파일의 형식: UTF-8, BOM 없음, CR 0, U+00A0 0, 탭 0, 줄 끝 공백 0, 끝 LF 1개. git diff --check 통과.

E2E_GATES

- clean 구현 커밋에서 D7의 CLEAN_COMMIT_E2E 검사를 수행한다. 검사 전후 tracked·index·untracked 상태가 같고, ignored 목록이 D8 허용 범위 안이어야 한다.
- PR_CI에서 정확한 head의 필수 Windows CI SUCCESS를 확인하고 D10에 따라 검사 대상을 기록한다. Linux experimental 결과는 별도로 보고한다. 기존 wrapper 실패 2건(test_wrapper_passes_real_decisions_through, test_wrapper_cannot_fix_invalid_json_with_exit_0)은 이름으로 구분해 기록하되 해결된 것으로 표시하지 않고, 원인이 같다고 단정하지 않는다. 그 밖의 새 실패가 있거나 기존 실패와 구분할 수 없는 결과는 보고하고 중단한다.

ACCEPTANCE_CRITERIA

- AC1: C1과 I의 parent, 변경 집합이 COMMIT_PLAN과 같다.
- AC2: base..I의 파일이 C1 파일과 ALLOWED_FILES 안의 파일뿐이며, 보호 diff 0, Work Order 해시 불변.
- AC3: D6 환경 확인값, pip check 통과, 대상 venv 배포판 목록 확인, mypy 버전과 compiled 여부 기록.
- AC4: build_argv가 D1과 정확히 같고, D2 불변 항목이 바뀌지 않았다(executor.py diff 0, build_env 테스트 통과).
- AC5: Guard 호환 검사 2개가 새 argv로 통과한다.
- AC6: 실제 자식 비교 검사가 D5 합격 기준을 모두 만족한다. 대조군 전제 불충족은 실패다.
- AC7: 필수 로컬 검사(D7의 TARGETED_CHECKS, STATIC_CHECKS, FULL_PYTEST, CLEAN_COMMIT_E2E)와 필수 Windows CI의 실패가 0이다. Linux experimental은 AC7의 실패 0 대상이 아니며, E2E_GATES에 따라 기존 실패 2건만 있고 새 실패가 없음을 따로 기록한다.
- AC8: 산출물이 D8 허용 범위 안이며 AUTO-04 자료와 다른 worktree가 변경되지 않았다.
- AC9: W와 승인 S, staged blob, commit blob의 내용 SHA-256이 일치하고, commit 후 clean.
- AC10: 정확한 PR head의 Windows CI SUCCESS와 D10 기록. 이전 단계에서는 NOT_YET_APPLICABLE.
- 완료 판정: AC1–AC10 충족과 계약 위반, 보호 파일 변경, 설명되지 않은 상태 변경의 부재를 함께 요구한다. Linux experimental의 기존 실패 2건은 미해결로 남기며 완료를 막지 않는다. 새 Linux 실패나 구분 불가 결과가 있으면 완료하지 않는다. 완료는 D3의 한계 밖 효과를 입증하지 않는다.

REQUIRED_EVIDENCE

- GIT_VERIFIABLE: base·C1·I·merge SHA, tree, parents, 파일 집합, Work Order 해시, W·S·commit blob 내용 해시
- CLAUDE_REPORTED: 환경 확인값, 대상 venv 배포판 목록, mypy 버전과 compiled 여부, D7 검사 출력과 집계, 실제 자식 비교 검사 결과, ignored 산출물 목록, Guard·권한 관측, PR head·run headSha·checkout SHA·시험용 merge의 parents·tree
- INDEPENDENT: ChatGPT·사용자 검토, 정확한 head의 GitHub CI
- 직접 관측, 보고, 추론을 구분한다.

REQUIRED_REPORT

TASK_ID, GATE, SUBPHASE, HEAD, parent, tree, Work Order 해시, 변경 집합, 보호 diff, 전후 상태, ignored 산출물, 검사 명령과 출력 집계, 실패·skip·xfail 목록, GUARD_EVENTS, DEVIATIONS, ISSUES, PROPOSED_ERRATA, 해당 gate 판정과 다음 승인 경계를 보고하고 멈춘다.

STOP_CONDITIONS

- 기준선·HEAD·tree·Work Order 해시·파일 범위 불일치, 예상 밖 untracked
- 생성 전 대상 branch·worktree 존재, 생성 후 기대 상태 불일치
- fetch 후 원격 추적 main이 CANONICAL_BASE_SHA가 아님
- PATH_VARIABLES 값이 승인문에 없거나 기대 상태와 다름
- 환경 확인 불충족, pip check 실패, 대상 venv의 고정 목록 밖 배포판, mypy 버전 불일치, 설치 정책 차단
- 테스트·ruff·mypy 실패, 대조군 전제 불충족, Guard 호환 검사 실패
- Linux experimental에서 기존 실패 2건 외의 새 실패, 또는 기존 실패와 구분할 수 없는 결과
- D8 허용 범위 밖 산출물, 저장소 안 tmp 산출물
- 보호 파일 변경, executor.py 변경, ALLOWED_FILES 밖 변경
- Guard DENY, 권한 거절·무응답, 예상 밖 ASK, 오류·결과 불명
- 계약 모순, 상위 규칙과의 충돌
