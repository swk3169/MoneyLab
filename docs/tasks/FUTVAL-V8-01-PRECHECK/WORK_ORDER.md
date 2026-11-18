# Work Order: FUTVAL-V8-01-PRECHECK — FUTVAL-V8-01 운영 설정의 결정적 사전 검사(seed 고유성·임계값)

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/FUTVAL-V8-01-PRECHECK/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: FUTVAL-V8-01-PRECHECK
TASK_ID: FUTVAL-V8-01-PRECHECK
TITLE: precheck 하위명령 추가와 운영 seed 고유성·임계값의 결정적 사전 검사 1회
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: b42fe6fa5fb76a474e59d18c929dd11c6f74bea6
CANONICAL_BASE_TREE: 02735b6725c25cda94044796d118d6f35d2dd498
CANONICAL_BASE_PARENT: 9014a902c9a91f6d103f6bcd30ffee7ce5abb10f
BASE_REMOTE_REF: NONE (로컬 커밋이며 원격 main이 아니다. 기준 확인은 로컬 git 객체로만 한다. fetch하지 않는다)
TARGET_BRANCH: codex/futval-v8-01-precheck
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
ENV_PYTHON: C:/MoneyLab-gov-automation-03/.venv/Scripts/python.exe
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE (PUSH·PR_CI·MERGE gate 없음)
REQUIRED_CI_CHECKS: NOT_APPLICABLE (원격 단계 없음)
BUNDLE_ELIGIBLE: YES
BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E
PREREGISTRATION_PATH: docs/research_futval_v8_01_preregistration.md
PREREGISTRATION_SHA256: d77549ed4cc732f0b2fb0151fcf17913d319ce8e0de929827fc3a8c9c7ea9b91
IMPL_WORK_ORDER_PATH: docs/tasks/FUTVAL-V8-01-IMPL/WORK_ORDER.md
IMPL_WORK_ORDER_SHA256: 6a7c7bac1ce9589d8740af51f32342f32cb247e117c6dc7225c37921ec8e9cbb
SOURCE_BLOB_PROCEDURES: src/moneylab/research/v06/procedures.py = bf6dfddea822f3af0d6e50274c8b3b5b0c767daf
SOURCE_BLOB_STATS: src/moneylab/research/stats.py = 01b6472cadb2ce2437a613b09d419a999398c685
BASE_BLOB_MODULE: src/moneylab/research/v06/futval_v8_01.py = ceefcabd7103940774b69c77bf866a724937f400
BASE_BLOB_TEST: tests/test_futval_v8_01.py = 9835be6184e95486cd4f64b1f16e88a9c0ed7fbe
RELATED_TASKS: FUTVAL-V8-01(PREREGISTRATION_FREEZE_PASS 보류, ref 보존 미확정), FUTVAL-V8-01-IMPL(CLOSEOUT_REPORT_PASS, TASK_COMPLETE NOT_DECLARED). 이 Work Order는 그 판정·보류·사건 기록을 바꾸거나 완료시키지 않는다.

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> ENV_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PRECHECK_EXECUTION -> RESULT_REPORT -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- WORKSPACE_SETUP, ENV_SETUP, PRECHECK_EXECUTION, RESULT_REPORT, CLOSEOUT_REPORT는 각각 GATE_AUTHORIZATION 1건으로만 시작하고 보고 후 멈춘다.
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: FUTVAL-V8-01-PRECHECK WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - 그 밖의 개별 gate: GATE_AUTHORIZATION: FUTVAL-V8-01-PRECHECK <GATE> WO@<C1 SHA>
  - PRECHECK_EXECUTION 승인에는 C2 SHA와 출력 디렉터리 경로를 함께 적는다.
- IMPLEMENTATION..CLEAN_COMMIT_E2E는 README §14의 BUNDLE_AUTHORIZATION(BGA-2 키 전부) 1건으로 진행할 수 있다. 개별 GATE_AUTHORIZATION으로도 진행할 수 있다. PRECHECK_EXECUTION은 묶음에 넣지 않는다.
- BGA-0–BGA-10과 README §14 상태 전이 기준을 그대로 적용한다. 이 Work Order는 그 규칙을 완화하지 않는다.
- 일반 DELEGATE(v1.4)는 어떤 gate도 대신하지 않는다.
- 상태 변경 명령은 각각 별도 도구 호출로 실행하고 결과를 확인한 뒤 다음 명령을 실행한다. 선행 결과에 의존하는 조회는 병렬로 보내지 않는다. 같은 mypy 캐시를 쓰는 검사는 순차로만 실행한다. STOP 뒤에는 후속 명령을 실행하지 않는다.
- COMMIT 뒤 수정은 STOP하고 사용자 결정을 받는다. amend는 금지한다.
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)과 고정 사전등록(PREREGISTRATION_PATH, PREREGISTRATION_SHA256)이 이 Work Order보다 우선한다. 충돌하면 STOP한다. 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: 고정 사전등록 §4·§6·§7의 운영 설정(BASE 20261118, 이름공간 FUTVAL-V8-01, 12셀, R 10,000, α 1/20, ε 1/100, λ 1/40)에 대해, 데이터 생성 없이 seed 240,000개의 고유성과 임계값 a_1..a_12·b, 그리고 그 검증·경계 부등식을 1회 계산해 구현·사전등록 식별값과 연결된 산출물로 남긴다. 이를 위해 기존 모듈에 precheck 하위명령을 추가한다.

## BACKGROUND

BACKGROUND:
- 구현 커밋 b42fe6fa5fb76a474e59d18c929dd11c6f74bea6에는 임계값만 계산하는 진입점이 없다(CLI는 seed-check, smoke, perf, run뿐이며 run은 본 실행이다). seed-check는 소스 검증과 산출물 해시가 없다.
- 기존 테스트(R 50 이하)에서는 축 B 임계값 b가 -1뿐이어서 b 0 이상의 계산 경로가 검증되지 않았다.
- 기존 verify_thresholds는 방법 1·2의 판정 방향 일치만 검사하며, 임계값 양옆의 정확 부등식을 단언하지 않는다.
- 이 사전 검사는 설계 상수와 seed만 다룬다. 연구 결과가 아니다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 사전 목록 출력(PRESERVATION_CHECK)
  - 기준 확인: git -C C:/MoneyLab-gov-automation-03 rev-parse b42fe6fa5fb76a474e59d18c929dd11c6f74bea6^{tree}, 계약·소스 blob 확인
  - git -C C:/MoneyLab-gov-automation-03 worktree add -b codex/futval-v8-01-precheck C:/MoneyLab-futval-v8-01-precheck b42fe6fa5fb76a474e59d18c929dd11c6f74bea6 1회
  - docs/tasks/FUTVAL-V8-01-PRECHECK/WORK_ORDER.md Write 1회, git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/FUTVAL-V8-01-PRECHECK/WORK_ORDER.md, C1 커밋 1회(메시지 docs(task): add FUTVAL-V8-01-PRECHECK work order, 본문·trailer 없음)
- ENV_SETUP(네트워크는 E2·E3의 https://pypi.org/simple에만, 각 1회, 이 순서)
  - E1: C:/MoneyLab-gov-automation-03/.venv/Scripts/python.exe -I -B -m venv C:/MoneyLab-futval-v8-01-precheck/.venv
  - E2: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe -B -m pip install --isolated --disable-pip-version-check --no-input --no-cache-dir --index-url https://pypi.org/simple --no-binary=mypy -r C:/MoneyLab-futval-v8-01-precheck/requirements-dev.txt
  - E3: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe -B -m pip install --isolated --disable-pip-version-check --no-input --no-cache-dir --index-url https://pypi.org/simple --no-deps -e C:/MoneyLab-futval-v8-01-precheck
  - E4: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe -B -m pip check
  - E5: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe -B -m mypy --version
  - 완료 조건: 모두 exit 0, pip check 문제 없음, mypy 출력에 "mypy 2.4.0"과 "compiled: no", 대상 Python의 moneylab 로드 위치가 TARGET_WORKTREE/src, ignored 항목이 .venv/와 src/moneylab.egg-info/의 부분집합
  - 그 뒤 COLLECT_COMMAND 1회로 기준 수집 ID 목록을 도구 출력에 남긴다
- IMPLEMENTATION: ALLOWED_FILES 2개 수정, CHECK_1·CHECK_2·CHECK_3A·CHECK_3B를 순차 실행, 모두 통과 뒤 CHECK_4 실행. BGA-4 수정 반복
- PRECOMMIT_AUDIT: 읽기, git diff --check, COLLECT_COMMAND 1회, BGA-8 확인
- COMMIT: ALLOWED_FILES 2개만 경로 지정 stage, git diff --cached --check, C2 커밋 1회(메시지 feat(research): add FUTVAL-V8-01 precheck command, 본문·trailer 없음)
- CLEAN_COMMIT_E2E: HEAD = C2 clean에서 CHECK_1 1회와 상태·바이트 재확인
- PRECHECK_EXECUTION: PRECHECK_COMMAND 1회
- RESULT_REPORT: precheck.json·execution.json·SHA256SUMS 열람 1회와 채팅 보고
- CLOSEOUT_REPORT: PRESERVATION_CHECK 비교와 종결 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위, ALLOWED_FILES·CONTRACT_FILE_EXCEPTION 밖 tracked 변경, PROTECTED_FILES 변경
- 사전등록·Work Order·ERRATA 수정
- git add ., git add -A, --no-verify, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, 모든 형태의 fetch
- push, PR, merge, CI 실행
- DGP 데이터 생성, bootstrap, 기각률 추정, smoke, 성능 측정, 본 실행, 연구 결과 열람
- PRECHECK_EXECUTION 밖의 운영 seed 240,000개 검사와 운영 R 임계값 계산(IMPLEMENTATION·CLEAN_COMMIT_E2E의 검사 포함)
- seed 값의 출력·기록
- 기존 공개 함수의 동작·판정·상수 변경
- 기존 비공개 결과·V-1 분포·BT4 산출물 열람
- ENV_SETUP E2·E3 밖의 네트워크
- 임시 스크립트 파일 작성, 출력 폐기·리디렉션·tee
- hooks·settings·.claude·.github·pyproject.toml·requirements*.txt·.gitignore 변경, guard 우회
- 다른 branch·worktree·untracked·ignored·기존 산출물의 변경·복구·정리

## ALLOWED_FILES

ALLOWED_FILES:
- M src/moneylab/research/v06/futval_v8_01.py (precheck 하위명령, 사전 검사 내부 함수, 정확 산술 중간값 재사용 추가만. 기존 공개 함수의 동작·판정·상수는 바꾸지 않는다)
- M tests/test_futval_v8_01.py (precheck 관련 테스트 추가만. 기존 테스트 함수와 단언은 바꾸지 않는다)

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/FUTVAL-V8-01-PRECHECK/WORK_ORDER.md (WORKSPACE_SETUP 전용, 승인 바이트로 최초 1회)

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/FUTVAL-V8-01-PRECHECK/** (최초 생성 제외), docs/tasks/FUTVAL-V8-01/**, docs/tasks/FUTVAL-V8-01-IMPL/**, docs/research_futval_v8_01_preregistration.md
- ALLOWED_FILES와 CONTRACT_FILE_EXCEPTION 밖의 모든 저장소 파일. src/moneylab/research/v06/procedures.py, src/moneylab/research/stats.py, src/moneylab/research/v06/__init__.py, montecarlo.py, synthetic.py, risk_model.py, futility_diag.py, src/moneylab/storage/**, 다른 src/**, 다른 tests/**, configs/**, docs/**, .claude/**, .github/**, CLAUDE.md, .gitignore, .gitattributes, pyproject.toml, requirements*.txt를 포함한다

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## COMMIT_PLAN

COMMIT_PLAN:
- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/FUTVAL-V8-01-PRECHECK/WORK_ORDER.md
- C2: parent = C1, 변경 = M src/moneylab/research/v06/futval_v8_01.py, M tests/test_futval_v8_01.py
- CANONICAL_BASE_SHA..C2 변경 경로는 위 세 파일뿐이다. 커밋 본문과 trailer는 넣지 않는다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D0 원칙: 사전등록 문언이 기준이다. 아래는 구현 위치와 검사 조건만 정하며 사전등록의 통계 설계·수치 방법(§6·§7)을 바꾸지 않는다. 다르게 구현해야 할 필요가 생기면 STOP하고 보고한다.
- D1 진입점
  - CLI: python -m moneylab.research.v06.futval_v8_01 precheck --out <dir>. --out 외 인자는 없다.
  - CLI는 운영 설정(NS_MAIN, BASE, CELLS, R, α, ε, λ)만 쓴다. 덮어쓰기 인자는 CLI에 없다.
  - 내부 함수는 TEST 이름공간과 작은 R·소스 덮어쓰기를 받을 수 있다. 운영 이름공간에서 덮어쓰기 인자가 주어지면 ValueError로 거부한다(기존 run과 같은 규칙).
- D2 실행 순서(첫 실패에서 STOP)
  1) 출력 디렉터리 배타 생성. 이미 있으면 실패하며, 그 디렉터리 안에는 실패 기록을 포함해 아무것도 쓰지 않고 기존 내용을 바꾸지 않는다.
  2) 소스 검증: 기존 git_provenance(로드 경로, 보호 파일 기대 blob, HEAD blob과 LF 작업 파일 대조)를 계산 전에 호출한다.
  3) seed 고유성: 기존 seed_uniqueness(NS_MAIN, CELLS, R). 개수·서로 다른 개수·통과 여부만 기록한다. seed 값은 기록·출력하지 않는다.
  4) 임계값(방법 1, 정확 정수): levels = holm_levels(12), a_1..a_12, b.
  5) 방법 2 검증: 각 임계값과 이웃 지점에서 방법 1과 방법 2의 꼬리확률을 비교해, 상대 오차가 10^-9 이하인지와 수준 비교의 판정 방향이 같은지를 각각 따로 검사한다. 기존 verify_thresholds가 두 조건을 모두 검사한다고 가정하지 않는다. 기존 공개 함수는 바꾸지 않고 precheck 내부 함수에서 두 조건을 명시적으로 검사한다. 어느 한 조건이라도 실패하면 COMPUTATION_FAILURE로 STOP한다.
  6) 경계 부등식(방법 1, 정확 유리수 비교)
     - 각 j: P(Bin(R, 1/20) >= a_j) <= t_j, 그리고 a_j > 0이면 P(Bin(R, 1/20) >= a_j - 1) > t_j
     - P(Bin(R, 3/50) <= b) <= λ, 그리고 P(Bin(R, 3/50) <= b + 1) > λ
     - 운영 precheck(R = 10,000, 3/50, λ = 1/40)에서만 b >= 0을 요구한다. b < 0이면 B_NEGATIVE로 STOP한다. 일반 함수 axis_b_threshold가 작은 R에서 -1을 반환하는 동작은 유지한다.
  7) 출력 쓰기
- D3 정확 산술 중간값 재사용: 사전 검사 내부에서만 pmf 분자·접미합·누적합을 1회 계산해 재사용할 수 있다. 결과는 기존 exact_upper_tail, exact_lower_tail, axis_a_thresholds, axis_b_threshold와 같아야 하며, 기존 함수의 정의는 바꾸지 않는다.
- D4 호출 금지: precheck 경로는 generate_p0, v0_statistics, v0_replicate, procedures.bootstrap_means, _execute, _work, evaluate의 기각률 부분, cp_interval을 호출하지 않는다.
- D5 독립성 한계: 방법 1과 방법 2는 같은 모듈 안의 서로 다른 계산이며 독립 검증이 아니다. 보고에서 독립 검증이라고 주장하지 않는다.
- D6 출력(PRECHECK_EXECUTION 출력 디렉터리, ignored)
  - precheck.json(schema moneylab.futval_v8_01.precheck/1): study, preregistration(path, sha256, version), decision_version, code(git_provenance 결과), environment(sys_version, implementation, sys_platform), seed_check(namespace, count, distinct, pass), design(R, alpha, epsilon, lambda, holm_levels, cells), thresholds(a, b), threshold_checks(지점마다 축, 지점, 수준, 방법 1·2 값, 상대 오차, relative_error_ok, same_direction을 구분해 기록), boundary_checks(각 임계값과 이웃의 관계·성립 여부), b_nonnegative, classification "DESIGN_CONSTANTS_NOT_RESEARCH_RESULTS". 시간·경로·호스트는 넣지 않는다.
  - execution.json: 상태(COMPLETE 또는 STOP), 실패 코드, 시작·종료 시각, 경과 시간, 호스트, 출력 경로, OS. 실행 메타데이터이며 SHA256SUMS 대상이 아니다.
  - SHA256SUMS: precheck.json 하나의 sha256만 담는다. 자기 자신과 execution.json은 담지 않는다.
  - 작성 순서: precheck.json -> execution.json -> SHA256SUMS. 모두 storage.atomic으로 쓴다. SHA256SUMS가 없는 디렉터리는 불완료다.
  - 실패 처리
    - 결과 쓰기 전에 계산·검증이 실패하면 precheck.json과 SHA256SUMS를 만들지 않는다.
    - 이미 성공적으로 쓴 파일은 이후 실패가 있어도 삭제하거나 덮어쓰지 않는다.
    - SHA256SUMS는 앞선 모든 쓰기와 검증이 성공한 뒤 마지막에 쓴다. SHA256SUMS가 없으면 미완료다.
    - 디렉터리 생성 뒤 실패하면 execution.json에 STOP 상태와 실패 코드를 기록하려고 시도한다. 이 기록 쓰기 자체도 실패할 수 있으며, 그 경우 완전한 실패 기록을 보장하지 않는다.
    - 출력 경로가 이미 있으면 그 안에 실패 기록도 쓰지 않는다.
    - 쓰기 실패 뒤 재시도·정리·삭제를 하지 않는다.
    - 소스 불일치는 seed·임계값 계산 전에 STOP한다.
- D7 실패 처리: 재시도, seed 변경, 임계값·판정·수치 방법 변경 없이 STOP한다. 재실행은 새 승인과 새 디렉터리(a<N+1>)로만 한다.

## TEST_GATES

TEST_GATES:
- 새 테스트는 TEST 이름공간 또는 작은 R(50 이하)과 tmp_path만 쓴다. 운영 seed 240,000개 검사와 R 10,000 임계값 계산은 테스트에 넣지 않는다.
  - 중간값 재사용 결과가 기존 exact_upper_tail·exact_lower_tail·axis_a_thresholds·axis_b_threshold와 같음(작은 R 여러 값)
  - 경계 부등식 함수의 진리표(성립, 불성립, a_j = 0, b = -1)
  - b >= 0 조건 함수가 b < 0을 STOP으로 처리함(운영 조건 함수 단독 시험)
  - 작은 R의 precheck 내부 실행이 스키마·필드·작성 순서·SHA256SUMS 목록을 지킴, seed 값이 출력에 없음
  - DGP·bootstrap·기각률 경로 미호출(감시 함수로 단언)
  - 소스 불일치 시 계산 전 STOP, precheck.json과 SHA256SUMS 미생성, execution.json STOP 기록
  - precheck.json 작성 이후 실패 주입(execution.json 쓰기 실패, SHA256SUMS 쓰기 실패 각각): precheck.json은 남고 바이트가 바뀌지 않으며 SHA256SUMS는 없음, 재시도 없음
  - 방법 2 상대 오차 위반 주입과 판정 방향 불일치 주입을 각각 따로 시험해 둘 다 COMPUTATION_FAILURE로 STOP하고 precheck.json을 만들지 않음. 성공 기록에서 relative_error_ok와 same_direction이 구분되어 있음
  - 기존 출력 디렉터리가 있으면 실패하고, 그 안의 기존 파일 이름·바이트가 바뀌지 않으며 실패 기록도 생기지 않음
  - 운영 이름공간 덮어쓰기 인자 거부, CLI 인자 구성
- CHECK_COMMANDS(cwd 결합은 이 문자열 그대로만)
  - CHECK_1: cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -rs -v tests/test_futval_v8_01.py
  - CHECK_2: cd C:/MoneyLab-futval-v8-01-precheck && ./.venv/Scripts/python.exe -B -m ruff check --no-cache src tests
  - CHECK_3A: cd C:/MoneyLab-futval-v8-01-precheck && ./.venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache
  - CHECK_3B: cd C:/MoneyLab-futval-v8-01-precheck && ./.venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache src/moneylab/research/v06/futval_v8_01.py
  - CHECK_4: cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -rs
  - COLLECT_COMMAND: cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q
- 시간 한도: ENV_SETUP 명령과 CHECK_1·2·3A·3B·COLLECT_COMMAND는 각 600초. CHECK_4는 3600초이며 백그라운드 실행과 완료 알림으로 기다리고 폴링하지 않는다. 넘으면 STOP한다
- CHECK_1–4 failed 0 / errors 0. CHECK_4는 COMMIT 전에 통과해야 한다. 각 CHECK 전후 두 파일의 W와 git status --ignored를 기록한다
- BGA-8: PRECOMMIT_AUDIT에서 ENV_SETUP 기준 수집 ID 대비 감소 없음, 추가 ID는 모두 tests/test_futval_v8_01.py, 기존 테스트 함수·단언 변경 없음(git diff로 삭제 줄이 없음을 확인), skip·xfail 추가 없음. 단정 완화·우회는 "독립 검토 필요"로 보고한다
- BGA-4·BGA-10: 새 테스트·ruff·mypy 실패는 BUDGET 안에서 ALLOWED_FILES만 고쳐 같은 CHECK로 다시 실행한다. 기존 테스트 실패(회귀)와 COMMIT 이후 실패는 STOP한다

## E2E_GATES

E2E_GATES:
- CLEAN_COMMIT_E2E: HEAD = C2, clean, ignored 집합 = ENV_SETUP 종료 시점. CHECK_1 1회. commit blob 내용 SHA-256 = S, 작업 파일 SHA-256 = W. 실행 전후 status(ignored 포함) 동일. 사전등록 sha256과 보호 소스 blob 불변. CHECK_4는 반복하지 않는다

## PRECHECK_EXECUTION

PRECHECK_EXECUTION(별도 GATE_AUTHORIZATION, 묶음 밖, 1회):
- 진입 조건: HEAD = C2, clean, ignored 집합 = ENV_SETUP 종료 시점, 두 파일 W = C2 commit 내용, 계약·보호 소스 불변, 출력 디렉터리 data/processed/futval_v8_01/precheck-<C2 SHA 앞 12자>-a1이 없고 git check-ignore로 ignored임
- PRECHECK_COMMAND: cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m moneylab.research.v06.futval_v8_01 precheck --out data/processed/futval_v8_01/precheck-<C2 SHA 앞 12자>-a1
- 시간 한도 600초. 이것은 STOP 기준이며 보장값이 아니다. 실제 시간·메모리는 실행 전 미측정이다
- 실행 뒤 종료 코드, stdout 한 줄, 출력 디렉터리 파일 이름·크기·sha256만 확인한다. 내용 열람은 RESULT_REPORT에서 한다
- 실패하면 재시도하지 않고 STOP한다

## RESULT_REPORT

RESULT_REPORT(별도 GATE_AUTHORIZATION):
- precheck.json·execution.json·SHA256SUMS를 1회 열람하고 SHA256SUMS와 대조한다
- 채팅 보고: seed_check(개수, 서로 다른 개수, 통과), a_1..a_12, b, b_nonnegative, threshold_checks와 boundary_checks의 성립 여부, code 식별값(커밋, 네 파일 blob), 사전등록 sha256 연결, precheck.json sha256
- 임계값은 설계 상수이며 연구 결과가 아님을 표시한다. seed 값은 보고하지 않는다
- 결과를 파일·PR·커밋·공개 문서에 옮기지 않는다

## PRESERVATION_CHECK

PRESERVATION_CHECK(이전 task의 기준을 소급 변경하지 않는다. 이 Work Order에만 적용):
- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): 다음 원문 전체를 도구 출력으로 남긴다. 파일로 쓰지 않는다
  - git -C C:/MoneyLab-gov-automation-03 for-each-ref --sort=refname --format="%(refname) %(objectname)"
  - git -C C:/MoneyLab-gov-automation-03 worktree list --porcelain
  - git -C C:/MoneyLab-gov-automation-03 rev-parse HEAD HEAD^{tree}, git -C C:/MoneyLab-gov-automation-03 status --porcelain=v1 --untracked-files=all --ignored=matching
- 분류
  - TASK: refs/heads/codex/futval-v8-01-precheck. 기대 변화는 생성 -> C1 -> C2뿐
  - OBSERVED: refs/codex/turn-diffs/checkpoints/** 만. 변화는 이름·값 차이로 보고하며 변경 주체를 인증하거나 단정하지 않는다. STOP 사유가 아니다
  - PRESERVE: 그 밖의 모든 ref(refs/heads/codex/futval-v8-01, refs/heads/codex/futval-v8-01-impl을 포함한 refs/heads/**, refs/remotes/**, refs/tags/**, 그 밖의 미분류 ref). 하나라도 추가·삭제·값 변화가 있으면 STOP하고 보고한다
- 비교: refname 바이트 순 정렬 뒤 항목 단위로 비교한다. 개수 일치를 근거로 쓰지 않는다
- worktree: porcelain을 빈 줄 단위 항목으로 파싱하고, TARGET_WORKTREE 항목 하나를 통째로 제외한 뒤 worktree 경로 순으로 정렬해 F0과 항목 단위로 비교한다
- 비교 시점: ENV_SETUP 종료, CLEAN_COMMIT_E2E 종료, PRECHECK_EXECUTION 종료, CLOSEOUT_REPORT. 비교 원문은 같은 명령의 현재 세션 도구 출력이다

## EXPECTED_ASK

EXPECTED_ASK(통과를 보장하지 않음):
- WORKSPACE_SETUP: worktree add, Work Order Write(docs/tasks), git commit 1회
- ENV_SETUP: pip install 2회(E2·E3)
- COMMIT: git commit 1회
- 그 밖의 ASK, 거절, 무응답, DENY는 STOP이다

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: 기준·C1·C2 SHA·tree·parent, 파일 내용 SHA-256, 커밋 파일 집합, 보호 소스 blob, 사전등록 blob 내용 SHA-256
- CLAUDE_REPORTED: ENV_SETUP 결과, CHECK 결과·시간과 전후 W, 수집 ID 비교, BGA-8 확인, PRECHECK_EXECUTION 종료 코드·시간·출력 해시, RESULT_REPORT 값, 보존 비교
- INDEPENDENT: 사용자 확인(원격 단계 없음)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, HEAD·parent·tree, 변경 집합, PROTECTED diff, status(ignored 포함), W·S
- 추가 테스트와 DESIGN_CONTRACT 항목의 대응
- PRESERVATION_CHECK 분류별 비교
- GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES, BUDGET 사용, <GATE>_PASS, READY_FOR_<NEXT>
- 유지할 한계: 방법 1·2의 독립성 한계, 디스크 소스 대조와 모듈 위치 기반 root의 인증 한계, 시간·메모리 미측정

## STOP_CONDITIONS

STOP_CONDITIONS:
- 기준 커밋·tree·parent·계약 sha256·소스 blob 불일치, TARGET_WORKTREE·TARGET_BRANCH가 미리 있음
- ALLOWED_FILES 밖 변경, PROTECTED 변경, 예상 밖 untracked·ignored, CHECK 전후 status 변화
- 기존 테스트 실패(회귀), 기존 테스트 함수·단언 변경, COMMIT 이후 실패, BUDGET 초과, 시간 한도 초과
- PRESERVE 분류 ref 변화, worktree 항목 불일치
- PRECHECK_EXECUTION 밖의 운영 seed 검사·운영 임계값 계산, DGP·bootstrap·기각률 경로 실행, seed 값 출력
- 출력 디렉터리가 이미 있음, 소스 검증 실패, COMPUTATION_FAILURE, 경계 부등식 불성립, B_NEGATIVE
- 모듈·테스트 두 파일로 이 계약을 충실히 구현할 수 없는 경우
- guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명, BUNDLE_AUTHORIZATION 원문 확인 불가
- 사전등록과 구현의 모순, 상위 규칙 충돌
