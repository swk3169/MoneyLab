# Work Order: FUTVAL-V8-01-IMPL — FUTVAL-V8-01 고정 사전등록의 구현과 오프라인 검증

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/FUTVAL-V8-01-IMPL/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: FUTVAL-V8-01-IMPL
TASK_ID: FUTVAL-V8-01-IMPL
TITLE: FUTVAL-V8-01 사전등록 구현(새 모듈 1개, 새 테스트 1개), 연구 실행 제외
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: e82ef7e9bdda5026124bc1da93feb4bf0f08aa22
CANONICAL_BASE_TREE: 5af27b3228c9df17441c4866d35431a162c4d274
BASE_REMOTE_REF: NONE (로컬 커밋이며 원격 main이 아니다. 기준 확인은 로컬 git 객체로만 한다. fetch하지 않는다)
TARGET_BRANCH: codex/futval-v8-01-impl
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-impl
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
SOURCE_BLOB_PROCEDURES: src/moneylab/research/v06/procedures.py = bf6dfddea822f3af0d6e50274c8b3b5b0c767daf
SOURCE_BLOB_STATS: src/moneylab/research/stats.py = 01b6472cadb2ce2437a613b09d419a999398c685
RELATED_TASKS: FUTVAL-V8-01 (PREREGISTRATION_FREEZE_PASS 보류, ref 보존 미확정, TASK_COMPLETE NOT_DECLARED). 이 Work Order는 그 판정을 바꾸거나 완료시키지 않는다.

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> ENV_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- WORKSPACE_SETUP, ENV_SETUP, CLOSEOUT_REPORT는 각각 GATE_AUTHORIZATION 1건으로만 시작하고 보고 후 멈춘다.
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: FUTVAL-V8-01-IMPL WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - ENV_SETUP, CLOSEOUT_REPORT: GATE_AUTHORIZATION: FUTVAL-V8-01-IMPL <GATE> WO@<C1 SHA>
- IMPLEMENTATION..CLEAN_COMMIT_E2E는 README §14의 BUNDLE_AUTHORIZATION(BGA-2 키 전부) 1건으로 진행할 수 있다. 개별 GATE_AUTHORIZATION으로도 진행할 수 있다.
- BGA-0–BGA-10과 README §14 상태 전이 기준을 그대로 적용한다. 이 Work Order는 그 규칙을 완화하지 않는다.
- 일반 DELEGATE(v1.4)는 어떤 gate도 대신하지 않는다.
- 상태 변경 명령은 각각 별도 도구 호출로 실행하고 결과를 확인한 뒤 다음 명령을 실행한다. 선행 결과에 의존하는 조회는 병렬로 보내지 않는다. STOP 뒤에는 후속 명령을 실행하지 않는다.
- COMMIT 뒤 수정은 STOP하고 사용자 결정을 받는다. amend는 금지한다.
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)과 고정 사전등록(PREREGISTRATION_PATH, PREREGISTRATION_SHA256)이 이 Work Order보다 우선한다. 충돌하면 STOP한다. 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: 고정 사전등록 §2–§10의 절차·판정·seed·출력·무결성·실패 규칙을 새 모듈 1개로 구현하고, §9의 T1–T12를 새 테스트 파일 1개로 오프라인 검증한다. smoke, 성능 측정, 본 실행, 운영 seed 검사, 운영 임계값 계산은 하지 않는다.

## BACKGROUND

BACKGROUND:
- 사전등록 고정 커밋: FUTVAL-V8-01 C2 e82ef7e9bdda5026124bc1da93feb4bf0f08aa22(로컬, 원격 미게시).
- 기준이 원격 main이 아니므로 README §15 DELEGATE는 쓸 수 없다(taskctl init이 origin/main = BASE를 요구). README §14 BGA에는 그런 조건이 없다.
- 이 작업은 사전등록을 읽기만 하며 생성·변경·확정하지 않는다(BGA-9와 구분).

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 사전 목록 출력(PRESERVATION_CHECK)
  - 기준 확인: git -C C:/MoneyLab-gov-automation-03 rev-parse e82ef7e9bdda5026124bc1da93feb4bf0f08aa22^{tree}, 사전등록·소스 blob 확인
  - git -C C:/MoneyLab-gov-automation-03 worktree add -b codex/futval-v8-01-impl C:/MoneyLab-futval-v8-01-impl e82ef7e9bdda5026124bc1da93feb4bf0f08aa22 1회
  - docs/tasks/FUTVAL-V8-01-IMPL/WORK_ORDER.md Write 1회, git -C C:/MoneyLab-futval-v8-01-impl add -- docs/tasks/FUTVAL-V8-01-IMPL/WORK_ORDER.md, C1 커밋 1회(메시지 docs(task): add FUTVAL-V8-01-IMPL work order, 본문·trailer 없음)
- ENV_SETUP(네트워크는 E2·E3의 https://pypi.org/simple에만, 각 1회, 이 순서)
  - E1: C:/MoneyLab-gov-automation-03/.venv/Scripts/python.exe -I -B -m venv C:/MoneyLab-futval-v8-01-impl/.venv
  - E2: C:/MoneyLab-futval-v8-01-impl/.venv/Scripts/python.exe -B -m pip install --isolated --disable-pip-version-check --no-input --no-cache-dir --index-url https://pypi.org/simple --no-binary=mypy -r C:/MoneyLab-futval-v8-01-impl/requirements-dev.txt
  - E3: C:/MoneyLab-futval-v8-01-impl/.venv/Scripts/python.exe -B -m pip install --isolated --disable-pip-version-check --no-input --no-cache-dir --index-url https://pypi.org/simple --no-deps -e C:/MoneyLab-futval-v8-01-impl
  - E4: C:/MoneyLab-futval-v8-01-impl/.venv/Scripts/python.exe -B -m pip check
  - E5: C:/MoneyLab-futval-v8-01-impl/.venv/Scripts/python.exe -B -m mypy --version
  - 완료 조건: 모두 exit 0, pip check 문제 없음, mypy 출력에 "mypy 2.4.0"과 "compiled: no", ignored 항목이 .venv/와 src/moneylab.egg-info/의 부분집합
  - 그 뒤 COLLECT_COMMAND 1회로 기준 수집 ID 목록을 도구 출력에 남긴다
- IMPLEMENTATION: ALLOWED_FILES 2개 작성, CHECK_1·CHECK_2·CHECK_3A·CHECK_3B 실행, 모두 통과 뒤 CHECK_4 실행. BGA-4 수정 반복
- PRECOMMIT_AUDIT: 읽기, git diff --check, COLLECT_COMMAND 1회, BGA-8 확인
- COMMIT: ALLOWED_FILES 2개만 경로 지정 stage, git diff --cached --check, C2 커밋 1회(메시지 feat(research): add FUTVAL-V8-01 implementation, 본문·trailer 없음)
- CLEAN_COMMIT_E2E: HEAD = C2 clean에서 CHECK_1 1회와 상태·바이트 재확인
- CLOSEOUT_REPORT: PRESERVATION_CHECK 비교와 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위, ALLOWED_FILES·CONTRACT_FILE_EXCEPTION 밖 tracked 변경, PROTECTED_FILES 변경
- 사전등록·Work Order·ERRATA 수정
- git add ., git add -A, --no-verify, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, 모든 형태의 fetch
- push, PR, merge, CI 실행
- 실제 smoke 실행(FUTVAL-V8-01-TEST 이름공간 §10 smoke 포함), FUTVAL-V8-01-PERF 성능 측정, FUTVAL-V8-01 본 실행
- 운영 이름공간 seed 240,000개 고유성 검사, 운영 R·α·ε·λ의 임계값 a_j·b 계산, CLI 운영 하위명령 실행
- 결과 열람, 기존 비공개 결과·V-1 분포·BT4 산출물 열람
- ENV_SETUP E2·E3 밖의 네트워크
- 임시 스크립트 파일 작성, 출력 폐기·리디렉션·tee
- hooks·settings·.claude·.github·pyproject.toml·requirements*.txt·.gitignore 변경, guard 우회
- 다른 branch·worktree·untracked·ignored·기존 산출물의 변경·복구·정리

## ALLOWED_FILES

ALLOWED_FILES:
- A src/moneylab/research/v06/futval_v8_01.py
- A tests/test_futval_v8_01.py

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/FUTVAL-V8-01-IMPL/WORK_ORDER.md (WORKSPACE_SETUP 전용, 승인 바이트로 최초 1회)

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/FUTVAL-V8-01-IMPL/** (최초 생성 제외), docs/tasks/FUTVAL-V8-01/**, docs/research_futval_v8_01_preregistration.md
- ALLOWED_FILES와 CONTRACT_FILE_EXCEPTION 밖의 모든 저장소 파일. src/moneylab/research/v06/procedures.py, src/moneylab/research/stats.py, src/moneylab/research/v06/__init__.py, montecarlo.py, synthetic.py, risk_model.py, futility_diag.py, src/moneylab/storage/**, 다른 src/**, 다른 tests/**, configs/**, docs/**, .claude/**, .github/**, CLAUDE.md, .gitignore, .gitattributes, pyproject.toml, requirements*.txt를 포함한다

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## COMMIT_PLAN

COMMIT_PLAN:
- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/FUTVAL-V8-01-IMPL/WORK_ORDER.md
- C2: parent = C1, 변경 = A src/moneylab/research/v06/futval_v8_01.py, A tests/test_futval_v8_01.py
- CANONICAL_BASE_SHA..C2 변경 경로는 위 세 파일뿐이다. 커밋 본문과 trailer는 넣지 않는다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D0 원칙: 사전등록 문언이 기준이다. 아래는 구현 위치만 정하며 사전등록의 수치·규칙을 바꾸지 않는다. 사전등록과 다르게 구현하거나 파일을 늘려야 할 필요가 생기면 STOP하고 보고한다.
- D1 모듈(futval_v8_01.py, 표준 라이브러리와 moneylab만 import)
  - 상수: 연구 ID FUTVAL-V8-01, 사전등록 판 v1, 판정 규칙 판 FUTVAL-V8-01-decision/1, 이름공간 3개, BASE = 20261118, §3 셀 순서, R = 10000, B = 9999, mean_block = 20, α = 1/20, ε = 1/100, λ = 1/40(fractions.Fraction)
  - §4: seed 직렬화 함수, seed 고유성 함수(값만 계산)
  - §3·§4: P0 생성 함수
  - §2·§5: V0 복제 함수. procedures 함수만 호출하며 NORMAL(지시변수) 또는 DEGENERATE를 반환한다. 예외는 잡지 않고 전파한다
  - §6·§7: 방법 1 정확 정수 꼬리확률과 임계값, 방법 2 로그 공간 꼬리확률, 경계 검증, K 기반 Holm, 축 B 판정, CP bisection(폭 10^-10 또는 200회)
  - §9: 본 실행 함수. K·D 집계, manifest·design·cells·summary·SHA256SUMS·execution.json, storage.atomic만 사용, 데이터 파일 먼저 SHA256SUMS 마지막, 실패 시 쓴 파일을 지우지 않는다
  - §9 manifest: 실행 커밋 SHA, 네 파일의 Git blob ID와 LF 기준 sha256, §2 대상 8개의 inspect.getsource UTF-8 sha256, 환경, 난수 규칙. 다른 출력 파일 해시는 담지 않는다
  - §10: smoke 함수(별도 스키마, 결과값 없음), 성능 측정 함수(별도 스키마, 시간·자원만. 통계 계산 작업량은 본 실행과 같은 경로로 수행하고 그 값은 버린다)
  - CLI: python -m moneylab.research.v06.futval_v8_01 {seed-check,smoke,perf,run}. 이 Work Order에서는 어느 하위명령도 실행하지 않는다
  - 운영 경로의 R·B·셀·이름공간은 상수로 고정한다. 작은 R·B·셀은 이름공간이 FUTVAL-V8-01-TEST일 때만 받는다
  - 병렬: concurrent.futures ProcessPoolExecutor(spawn). 결과를 셀·rep 순서로 정렬해 집계하므로 worker 수와 무관하다
- D2 출력 위치: 운영은 data/processed/futval_v8_01/<run_id>/(ignored). 테스트는 tmp_path만

## TEST_GATES

TEST_GATES:
- 새 테스트 파일에 사전등록 §9 T1–T12 각각에 대응하는 테스트 함수를 둔다(이름공간 FUTVAL-V8-01-TEST, 작은 고정 입력)
  - T2: 운영 상수(B 9999, mean_block 20, α 1/20)와 운영 이름공간 문자열을 단언한다
  - T3: 고정 사례 seed 값과 중복 주입만 다룬다. 운영 240,000개 검사는 하지 않는다
  - T4·T5: 소규모 R(50 이하)에서만 방법 1·2를 비교한다. 운영 R의 임계값은 계산하지 않는다
  - T8·T12: 예외 주입 시 STOP, 이미 쓴 파일 보존, SHA256SUMS 부재(미완료) 확인
  - T11: 작은 R·B로 worker 1과 2를 실행해 결과 4개 파일과 SHA256SUMS 바이트 동일, execution.json 분리
  - smoke·perf 스키마: 작은 TEST 입력으로 함수를 호출해 허용 필드만 기록됨을 확인한다. 실제 §10 smoke·perf 실행은 아니다
- CHECK_COMMANDS(cwd 결합은 이 문자열 그대로만)
  - CHECK_1: cd C:/MoneyLab-futval-v8-01-impl && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -rs -v tests/test_futval_v8_01.py
  - CHECK_2: cd C:/MoneyLab-futval-v8-01-impl && ./.venv/Scripts/python.exe -B -m ruff check --no-cache src tests
  - CHECK_3A: cd C:/MoneyLab-futval-v8-01-impl && ./.venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache
  - CHECK_3B: cd C:/MoneyLab-futval-v8-01-impl && ./.venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache src/moneylab/research/v06/futval_v8_01.py
  - CHECK_4: cd C:/MoneyLab-futval-v8-01-impl && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -rs
  - COLLECT_COMMAND: cd C:/MoneyLab-futval-v8-01-impl && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q
- 시간 한도: ENV_SETUP 명령과 CHECK_1·2·3A·3B·COLLECT_COMMAND는 각 600초. CHECK_4는 3600초이며 백그라운드 실행과 완료 알림으로 기다리고 폴링하지 않는다. 넘으면 STOP한다
- CHECK_1–4 failed 0 / errors 0. CHECK_4는 COMMIT 전에 통과해야 한다
- 각 CHECK 전후 git status --ignored 출력이 같아야 한다
- BGA-8: PRECOMMIT_AUDIT에서 ENV_SETUP 기준 수집 ID 대비 감소 없음, 추가 ID는 모두 tests/test_futval_v8_01.py, 기존 테스트 파일 변경 없음, skip·xfail 추가는 새 파일 안의 플랫폼 사유뿐임을 확인한다. 단정 완화·우회는 "독립 검토 필요"로 보고한다
- BGA-4·BGA-10: 새 테스트·ruff·mypy 실패는 BUDGET 안에서 ALLOWED_FILES만 고쳐 같은 CHECK로 다시 실행한다. 기존 테스트 실패(회귀)와 COMMIT 이후 실패는 STOP한다

## E2E_GATES

E2E_GATES:
- CLEAN_COMMIT_E2E: HEAD = C2, clean, ignored 집합 = ENV_SETUP 종료 시점. CHECK_1 1회. commit blob 내용 SHA-256 = S, 작업 파일 SHA-256 = W. 실행 전후 status(ignored 포함) 동일. 소스 두 blob과 사전등록 sha256 불변. CHECK_4는 반복하지 않는다

## PRESERVATION_CHECK

PRESERVATION_CHECK(FUTVAL-V8-01의 기준을 소급 변경하지 않는다. 이 Work Order에만 적용):
- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): 다음 원문 전체를 도구 출력으로 남긴다. 파일로 쓰지 않는다
  - git -C C:/MoneyLab-gov-automation-03 for-each-ref --sort=refname --format="%(refname) %(objectname)"
  - git -C C:/MoneyLab-gov-automation-03 worktree list --porcelain
  - git -C C:/MoneyLab-gov-automation-03 rev-parse HEAD HEAD^{tree}, git -C C:/MoneyLab-gov-automation-03 status --porcelain=v1 --untracked-files=all --ignored=matching
- 분류
  - TASK: refs/heads/codex/futval-v8-01-impl. 기대 변화는 생성 → C1 → C2뿐
  - OBSERVED: refs/codex/turn-diffs/checkpoints/** 만. 변화는 이름·값 차이로 보고하며 변경 주체를 인증하거나 단정하지 않는다. STOP 사유가 아니다
  - PRESERVE: 그 밖의 모든 ref(refs/heads/codex/futval-v8-01을 포함한 refs/heads/**, refs/remotes/**, refs/tags/**, 그 밖의 미분류 ref). 하나라도 추가·삭제·값 변화가 있으면 STOP하고 보고한다
- 비교: refname 바이트 순 정렬 뒤 항목 단위로 비교한다. 개수 일치를 근거로 쓰지 않는다
- worktree: porcelain을 빈 줄 단위 항목으로 파싱하고, TARGET_WORKTREE 항목 하나를 통째로 제외한 뒤 worktree 경로 순으로 정렬해 F0과 항목 단위로 비교한다
- 비교 시점: ENV_SETUP 종료, CLEAN_COMMIT_E2E 종료, CLOSEOUT_REPORT. 비교 원문은 같은 명령의 현재 세션 도구 출력이다

## EXPECTED_ASK

EXPECTED_ASK(통과를 보장하지 않음):
- WORKSPACE_SETUP: worktree add, Work Order Write(docs/tasks), git commit 1회
- ENV_SETUP: pip install 2회(E2·E3)
- COMMIT: git commit 1회
- 그 밖의 ASK, 거절, 무응답, DENY는 STOP이다

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: 기준·C1·C2 SHA·tree·parent, 파일 내용 SHA-256, 커밋 파일 집합, 소스 두 blob, 사전등록 blob 내용 SHA-256
- CLAUDE_REPORTED: ENV_SETUP 결과, CHECK 결과·시간, 수집 ID 비교, BGA-8 확인, 보존 비교
- INDEPENDENT: 사용자 확인(원격 단계 없음)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, HEAD·parent·tree, 변경 집합, PROTECTED diff, status(ignored 포함), W·S
- T1–T12 대응표와 각 테스트 결과, skip 항목
- PRESERVATION_CHECK 분류별 비교
- GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES, BUDGET 사용, <GATE>_PASS, READY_FOR_<NEXT>

## STOP_CONDITIONS

STOP_CONDITIONS:
- 기준 커밋·tree·사전등록 sha256·소스 blob 불일치, TARGET_WORKTREE·TARGET_BRANCH가 미리 있음
- ALLOWED_FILES 밖 변경, PROTECTED 변경, 예상 밖 untracked·ignored, CHECK 전후 status 변화
- 기존 테스트 실패(회귀), COMMIT 이후 실패, BUDGET 초과, 시간 한도 초과
- PRESERVE 분류 ref 변화, worktree 항목 불일치
- 운영 이름공간 사용, 운영 seed 검사·임계값 계산·CLI 운영 하위명령 실행, 결과값 출력
- 모듈 1개·테스트 1개로 사전등록을 충실히 구현할 수 없는 경우
- guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명, BUNDLE_AUTHORIZATION 원문 확인 불가
- 사전등록과 구현의 모순, 상위 규칙 충돌
