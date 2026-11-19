# Work Order: ECON-SCREEN-V06-01-IMPL-02 — 실제 선별 전 최소 보완(real 연결 시험, 계약 정합, 출력 검증, RUNWATCH 반입)

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/ECON-SCREEN-V06-01-IMPL-02/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: ECON-SCREEN-V06-01-IMPL-02
TASK_ID: ECON-SCREEN-V06-01-IMPL-02
TITLE: ECON-SCREEN-V06-01 실제 선별 전 최소 보완
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: bd6e7400ed79ff426aa19c4b8d45e474ae7e1ee2 (branch codex/econ-screen-v06-01-impl, 로컬, 원격 미게시)
CANONICAL_BASE_TREE: 1a34da9200c84a1b1c1576b455eb7978d2ca8850
ENTRY_HEAD: bd6e7400ed79ff426aa19c4b8d45e474ae7e1ee2 (branch codex/econ-screen-v06-01-impl)
ENTRY_TREE: 1a34da9200c84a1b1c1576b455eb7978d2ca8850
TARGET_BRANCH: codex/econ-screen-v06-01-impl-02
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck (재사용. .venv의 editable 설치가 이 worktree의 src를 가리킨다)
WORKSPACE_METHOD_EXCEPTION: 이 task의 WORKSPACE_SETUP에 한해 docs/tasks/README.md 표의 git worktree add -b(새 경로) 대신, TARGET_WORKTREE에서 CANONICAL_BASE_SHA를 기준으로 git switch -c codex/econ-screen-v06-01-impl-02를 1회 실행한다. 기존 branch·ref·산출물은 보존한다. 다른 task에 적용되지 않는다.
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
PYTHON: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe (재사용. 설치·갱신 없음)
PREREGISTRATION_PATH: docs/research_econ_screen_v06_01_preregistration.md
PREREGISTRATION_SHA256: 2ff766fa8e60adbc107b1ffe9ae4df30c455b616cd5345154704ff928b74705d
PREVIOUS_TASK: ECON-SCREEN-V06-01-IMPL (C1 f784c54530becae12fe70170c49f395b6e7844d7, C2 bd6e7400ed79ff426aa19c4b8d45e474ae7e1ee2, CLOSEOUT_REPORT_PASS 범위 한정). 그 Work Order·DEVIATION·이탈 기록은 바꾸지 않는다.
RUNWATCH_SOURCE: a3197059f0c1bc41e41ba0d2c7700836cb795645 (refs/heads/codex/runwatch-01)
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE
REQUIRED_CI_CHECKS: NOT_APPLICABLE
BUNDLE_ELIGIBLE: YES
BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E
EVIDENCE: 이 task의 모든 실행 출력은 SYNTHETIC / NOT_EVIDENCE다. real 분기 시험의 입력은 provenance만 real로 기록한 합성 pull이며 연구 증거가 아니다.

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 단일 gate 승인 형식
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-IMPL-02 WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - 그 밖: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-IMPL-02 <GATE> WO@<C1 SHA>
- 묶음은 docs/tasks/README.md §14 BGA-0–BGA-10과 상태 전이 기준을 그대로 따른다. 구간은 BUNDLE_MAX_RANGE 안이다. gate마다 보고하고, 전진 조건을 다시 확인해 통과하면 추가 채팅 승인 없이 다음 gate로 간다.
- CONTRACT_REVIEW, WORKSPACE_SETUP, CLOSEOUT_REPORT는 묶지 않는다.
- 프로젝트 저장소의 git commit은 C1(WORKSPACE_SETUP)과 C2(COMMIT gate) 각 1회만 허용한다. 시험이 tmp_path 안의 독립 저장소에 만드는 임시 커밋은 프로젝트 커밋이 아니다(UNTRACKED_AND_IGNORED, D7).
- settings·guard 승인 창은 사용자가 그 창에서 따로 승인한다. BGA는 그것을 대신하지 않는다.
- 상태 변경은 각각 별도 호출로 한다. 조회·해시·보존 비교는 목적별 작은 호출로 나누고, 검사 명령 뒤에 파이프·자르기·리디렉션·다른 명령을 붙이지 않는다.
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)과 고정 사전등록이 우선한다. 충돌하면 STOP한다. 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: 실제 선별 실행 전에 필요한 최소 보완을 구현하고 오프라인으로 검증한다.
- real 성공 경로 전체 연결 시험
- 실행 잠금 범위를 real로 맞춤
- 평가 기간 미달 시 144조합 보고와 SCREEN_NOT_EVALUABLE
- 연간 왕복 분모 일치
- 경계 시각의 고정 UTC 문자열 시험
- B1 배치 공유와 SCREEN_FLAG 연결의 직접 검증
- 비유한 값의 조기 중단
- RUNWATCH의 원본 blob 반입
실제 데이터의 수집·열람·계산, 합성 자원 측정, RUNWATCH로 실제 명령을 감시하는 실행은 하지 않는다.

## BACKGROUND

BACKGROUND:
- 사전등록 9절은 "4개 전략의 표시와 144개 조합 전체를 함께 보고한다"고 요구한다. 6절은 평가 기간 미달 시 "모든 전략이 SCREEN_NOT_EVALUABLE"이라고 하고, 8절은 "계산 불가 값은 사유와 함께 보고하며, 0이나 다른 값으로 바꾸지 않는다"고 한다. 계산 전 STOP은 5절(필수 Q 검사가 INVALID 또는 NOT_EVALUATED)과 11절 목록에만 있으며 평가 기간을 포함하지 않는다. 따라서 기간 미달은 다음과 같이 처리한다. 이 처리는 6·8·9절과 양립하므로 사전등록을 바꾸지 않는다.
  - 계산 가능하면 144조합을 계산·보고하고 표시만 SCREEN_NOT_EVALUABLE로 둔다.
  - 계산 불가하면 144개 조합 식별자마다 계산 불가 상태와 사유를 보고한다.
- 이전 IMPL Work Order D4의 "평가 기간 조건이 PASS가 아니면 계산하지 않는다"는 이 task에서 사전등록 9절에 맞게 바꾼다. 이전 Work Order 파일과 DEVIATION e 기록은 그대로 둔다.
- 평가 일수는 사전등록 3·6절의 G 길이(일)다. 같은지 여부는 D3의 정의로 출력에서 검사하고, 다르면 계산 오류로 처리한다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 출력(PRESERVATION_CHECK, 상태 변경 전 첫 호출)
  - 진입 확인
    - HEAD·tree·branch가 ENTRY와 같고 clean이다.
    - TARGET_BRANCH와 docs/tasks/ECON-SCREEN-V06-01-IMPL-02가 없다.
    - 사전등록 blob 내용 sha256이 PREREGISTRATION_SHA256과 같다.
    - data/ 아래 파일의 이름·크기·SHA-256 목록을 남긴다(내용은 열지 않음).
  - git -C C:/MoneyLab-futval-v8-01-precheck switch -c codex/econ-screen-v06-01-impl-02 bd6e7400ed79ff426aa19c4b8d45e474ae7e1ee2 1회
  - Work Order를 승인 바이트로 Write 1회
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/ECON-SCREEN-V06-01-IMPL-02/WORK_ORDER.md 1회
  - C1 커밋 1회
  - 종료 시 PRESERVATION_CHECK
- IMPLEMENTATION(진입: HEAD = C1, clean)
  1. 수집 baseline: 새로 수집하지 않는다. 직전 task PRECOMMIT_AUDIT의 COLLECT_COMMAND 출력(세션 tool-results/b5qimmodc.txt, 3,286개 ID)을 baseline으로 쓴다. 근거: 그 수집 뒤 작업 파일 W와 C2 commit blob이 S로 일치했고, C2 이후 tracked 변경이 없다. 파일을 확인할 수 없으면 변경 전에 COLLECT_COMMAND를 1회 실행해 baseline으로 쓴다.
  2. RUNWATCH 반입: git -C C:/MoneyLab-futval-v8-01-precheck restore --source=a3197059f0c1bc41e41ba0d2c7700836cb795645 --worktree -- src/moneylab/runwatch/__init__.py src/moneylab/runwatch/__main__.py src/moneylab/runwatch/watch.py src/moneylab/runwatch/winjob.py tests/test_runwatch.py 1회
  3. 반입 직후 각 파일의 git hash-object 값이 RUNWATCH_BLOBS와 같은지 확인한다. 다르면 STOP한다. 이후 이 5개 파일은 수정하지 않는다.
  4. ALLOWED_FILES의 M 경로만 Edit로 수정한다.
  5. PYTEST_TARGET, RUFF, MYPY가 통과할 때까지 FAILURE_RULES 안에서 수정·재실행한다.
  6. 5가 통과한 뒤 PYTEST_FULL을 백그라운드로 1회 실행하고 완료 알림을 기다린다.
  7. 종료 기준: 변경 ⊆ ALLOWED_FILES. 작업 파일 해시 집합 W와 stage될 내용 해시 집합 S를 기록한다.
- PRECOMMIT_AUDIT(읽기와 감사만. staging·커밋 없음)
  - 변경 집합 = ALLOWED_FILES 계획, git diff --check exit 0, PROTECTED diff 0, 예상 밖 untracked 0
  - RUNWATCH 5개 작업 파일의 git hash-object 값이 RUNWATCH_BLOBS와 같다
  - BGA-8 (A)
    - COLLECT_COMMAND 1회 실행 후 baseline과 비교해 감소한 ID가 없어야 한다.
    - ALLOWED_FILES 밖 테스트 파일 변경이 없어야 한다.
    - skip·skipif·xfail 추가가 없어야 한다. 단 tests/test_runwatch.py에 원래 있는 win_only skipif는 RUNWATCH_BLOBS로 원본 그대로임을 확인하고 "반입분"으로 따로 보고한다.
  - BGA-8 (B): "독립 검토 필요"로 보고한다
  - 계약 spot check D1–D9, W·S 불변
- COMMIT(독립 gate)
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- <ALLOWED_FILES 10개 경로 명시> 1회
  - 커밋 전 필수 확인. 하나라도 다르면 커밋하지 않고 STOP한다.
    - staged 경로 집합 = ALLOWED_FILES 10개
    - staged blob 내용 SHA-256 집합 = S
    - RUNWATCH 5개의 staged blob ID(git ls-files -s) = RUNWATCH_BLOBS
    - git -C C:/MoneyLab-futval-v8-01-precheck diff --cached --check exit 0
  - C2 커밋 1회
  - 커밋 후 확인: parent(C2) = C1, 변경 집합 = ALLOWED_FILES 10개, commit blob 내용 = S, RUNWATCH 5개의 commit blob ID = RUNWATCH_BLOBS, clean
- CLEAN_COMMIT_E2E(진입: HEAD = C2, clean)
  - PYTEST_TARGET 1회(백그라운드 가능), CLI_HELP 1회, RUNWATCH_HELP 1회. 전체 pytest는 반복하지 않는다.
  - 실제 구현이 커밋돼 있는지: HEAD = C2, clean, commit blob과 작업 파일의 대응을 확인한다(R1의 임시 저장소 시험은 이것을 증명하지 않는다).
  - 실행 전후 git status(ignored 포함)가 같아야 한다.
  - 종료 시 PRESERVATION_CHECK
- CLOSEOUT_REPORT: 읽기 전용 보존 확인과 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 실데이터
  - 수집·열람·변환·계산, candles-pull(dry-run 포함), 네트워크
  - econ-screen-prepare·econ-screen-run의 실제 데이터 실행
- 측정과 감시
  - 합성 자원 측정의 반복
  - RUNWATCH로 실제 명령을 감시하는 실행. 예외: tests/test_runwatch.py 실행과 RUNWATCH_HELP
- 계약 문서: 사전등록·이전 Work Order·이 Work Order·ERRATA 수정
- 시험 약화
  - permit·품질·경로·해시·clean 코드 검사를 mock으로 바꾸거나 조건을 완화
  - 운영 CLI에 시험용 축소 옵션 추가
  - D7 R1 밖의 REPO_ROOT 전환
- 값과 실행 처리
  - 계산 불가 값의 0 치환, 결과 숨기기, 자동 재실행
  - 실패를 숨기려는 검사 대상 제외
- 범위 확장: 사용하지 않는 클래스 정리, 범용 리팩터링, RUNWATCH 코드 수정, 새 감시 도구
- Git
  - fetch, push, PR, merge
  - git add의 전체 지정, amend, no-verify, reset, stash, rebase, cherry-pick
  - 지정 외 restore·checkout·switch, 프로젝트 저장소의 지정 외 커밋
- 실행과 정리
  - 셸 출력 폐기·리디렉션·출력 분기, 임시 스크립트 파일
  - guard·hook·settings·권한 규칙·메모리 변경
  - 기존 산출물·다른 branch·worktree·untracked·ignored 항목의 변경·정리

## ALLOWED_FILES

ALLOWED_FILES(모두 C2):
- M src/moneylab/backtest/econ_screen.py
- M src/moneylab/cli.py
- M tests/test_econ_screen.py
- M tests/fixtures/README.md
- M docs/backtest_design.md (15.1절 문구와 17절 개정 이력 행만)
- A src/moneylab/runwatch/__init__.py (blob a42ce7867117a8c76a2ae4f3c175f63c86c7d46d)
- A src/moneylab/runwatch/__main__.py (blob b973f05e12b5e0193da09b1783bbd99354a07276)
- A src/moneylab/runwatch/watch.py (blob 316eedaa61868bd52ea7630c33ac8cf164e72b93)
- A src/moneylab/runwatch/winjob.py (blob d00a408557b4bfbbd67df337879bce2d8b12dc91)
- A tests/test_runwatch.py (blob 78e59a4bd9f32699a30dcfb37ee55f69938e45b8)

RUNWATCH_BLOBS: 위 5개 A 경로의 blob ID. 반입 직후 작업 파일, staging, 커밋의 세 시점에서 각각 같아야 한다.

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/ECON-SCREEN-V06-01-IMPL-02/WORK_ORDER.md (WORKSPACE_SETUP 전용, 승인 바이트로 최초 1회). ALLOWED_FILES에 속하지 않는다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/** (위 예외의 최초 생성 1회 제외)
- docs/research_*_preregistration*.md, configs/**
- docs/** 중 docs/backtest_design.md를 뺀 전부
- src/moneylab/** 중 ALLOWED_FILES의 src 경로를 뺀 전부. backtest/bars_io.py, backtest/portfolio.py, providers/upbit/**, backtest/run.py, backtest/vault.py, research/**, domain/**를 포함한다
- tests/** 중 ALLOWED_FILES의 tests 경로를 뺀 전부(tests/fixtures의 기존 파일 포함)
- .claude/**, .github/**, CLAUDE.md, README.md, .gitignore, .gitattributes, pyproject.toml, requirements*.txt
- data/** 기존 산출물

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## UNTRACKED_AND_IGNORED

UNTRACKED_AND_IGNORED:
- 예상 untracked
  - WORKSPACE_SETUP: Write 뒤 add 전까지의 Work Order
  - IMPLEMENTATION·PRECOMMIT_AUDIT: RUNWATCH 5개 A 경로
  - 그 밖의 untracked는 F3이다.
- 허용된 ignored 내부 변화: .venv/.mypy_cache 내용 갱신. 저장소 안 새 ignored 항목(__pycache__, .pytest_cache, .ruff_cache, .mypy_cache(.venv 밖), data/ 아래 새 파일)은 금지한다.
- 시험 임시 자원: pytest tmp_path(OS 임시 영역)만 허용한다.
  - R1의 독립 git 저장소, 그 안의 임시 커밋, 합성 pull, 출력 root가 여기에 포함된다.
  - 임시 커밋은 시험 코드가 subprocess로 만들며 다음 옵션을 쓴다: git -c user.name=econ-screen-test -c user.email=test@example.invalid -c commit.gpgsign=false -c core.hooksPath=<tmp_path 안의 빈 디렉터리>. 프로젝트 저장소에는 아무것도 쓰지 않는다.
  - 이 임시 git 호출은 도구 호출이 아니므로 guard·settings 창이 생기지 않을 것으로 예상한다. 창이 생기면 예상 밖 ASK로 STOP한다.

## COMMIT_PLAN

COMMIT_PLAN:
- C1(WORKSPACE_SETUP): parent = CANONICAL_BASE_SHA, A docs/tasks/ECON-SCREEN-V06-01-IMPL-02/WORK_ORDER.md, 메시지 docs(task): add ECON-SCREEN-V06-01-IMPL-02 work order
- C2(COMMIT gate 1회): parent = C1, ALLOWED_FILES 10개, 메시지 fix(backtest): close ECON-SCREEN-V06-01 pre-run gaps
- 본문·trailer 없음. CANONICAL_BASE_SHA..C2 변경 경로는 WORK_ORDER.md와 ALLOWED_FILES뿐이다.
- 프로젝트 커밋은 위 2회뿐이며, R1의 임시 커밋은 이 수에 포함되지 않는다.
- COMMIT 이후 수정·실패는 STOP이며 후퇴하지 않는다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 실행 잠금: cmd_econ_screen_run은 real 모드에서만 check_run_lock을 호출한다. fixture 모드는 잠그지 않는다. 시도 표시 디렉터리와 실패 시 보존 규칙은 그대로다.
- D2 평가 기간 미달(필수 Q가 모두 PASS인 경우만. Q가 PASS가 아니면 계산 전에 거부하는 동작은 바꾸지 않는다)
  - 계산 가능(F ≤ E)
    - run_matrix로 144조합을 계산·보고한다.
    - screen_flags는 4개 전략 모두 SCREEN_NOT_EVALUABLE, 사유 evaluation_period_below_minimum이다.
    - 사유에 eval_days와 min_eval_days를 함께 기록하고 데이터 부족을 명시한다.
  - 계산 불가(F > E)
    - simulate를 호출하지 않는다.
    - combinations에 144개 조합 식별자(rule, scenario, fee_bps, capital_krw)마다 status NOT_COMPUTABLE을 기록한다. 사유 insufficient_data_first_signal_after_last_signal와 F·E·d0 값을 함께 둔다.
    - 수치 필드는 None과 사유로 두며 0을 넣지 않는다.
    - 4개 전략은 모두 SCREEN_NOT_EVALUABLE이고 같은 데이터 부족 사유를 갖는다.
    - 실행은 정상 완료하고 combinations_count = 144다. 빈 목록으로 처리하지 않는다.
  - F ≤ E인데 엔진이 거부하는 경우(예: 1시간봉이 평가 끝 전에 끝남)는 계산 오류(사전등록 11절)로 STOP한다.
- D3 평가 일수
  - 정의
    - n = 평가 행 수 − 1
    - T_d = (마지막 평가 기준 시각 − 첫 평가 기준 시각) / 1일. 첫 기준 시각 = R(F), 마지막 = R(E+1)
    - G_days = (requested_end − g_start) / 1일, g_start = F + 2일
  - 엔진이 F부터 E+1까지 하루에 한 행을 만들면 세 값은 모두 E − F + 1이다. 이것을 가정하지 않고 조합마다 검사한다. 하나라도 다르면 ScreenComputationError로 중단한다.
  - 연간 왕복 = 가상 청산을 포함한 왕복 수 / (G_days / 365). cost_analysis의 annual_round_trips(분모 T_d)와 같은 값이어야 한다.
- D4 비유한 값
  - describe 결과의 모든 float이 유한한지 조합마다 검사한다. 아니면 그 조합에서 즉시 ScreenComputationError로 중단한다.
  - cmd_econ_screen_run의 except에 ArithmeticError(OverflowError 포함)를 추가한다.
  - 정의되지 않는 지표는 기존대로 None과 사유이며, 0 치환은 하지 않는다.
  - 실패 시 임시 디렉터리와 이미 쓴 파일을 보존하고 자동 재실행하지 않는다.
- D5 REPO_ROOT: cli는 _econ_prereg_hashes와 backtest_code_state에 호출 시점의 모듈 변수 REPO_ROOT를 인자로 넘긴다. 검사 논리는 바꾸지 않는다.
- D6 RUNWATCH: 5개 파일은 RUNWATCH_SOURCE의 blob 그대로이며 수정하지 않는다. backtest_design.md 15.1절에 다음을 적는다.
  - real 실행은 RUNWATCH 아래에서 별도 승인한 시간·가용 메모리 하한·감시 디렉터리로 한다.
  - RUNWATCH의 메모리 기준은 시스템 가용 메모리(GlobalMemoryStatusEx)이며 프로세스 메모리가 아니다.
  - 17절에 개정 이력 행을 추가한다.
- D7 시험(tests/test_econ_screen.py, 오프라인, tmp_path만)
  - R1 real 전체 연결
    - 입력: provenance real로 기록한 합성 pull. 요청 범위는 [2017-01-01T00:00:00Z, 2024-04-01T00:00:00Z), 데이터 시작은 2017-06-01T00:00:00Z다(빈 페이지로 수집 종료). 출처는 시험 docstring과 README에 적는다.
    - tmp_path 안에 독립 git 저장소를 만들고, 사전등록 원본 바이트를 같은 경로에 커밋한다. monkeypatch로 cli.REPO_ROOT를 이 저장소로 바꾸며, monkeypatch가 시험 종료 시 자동 복원한다.
    - 실제 clean 검사(backtest_code_state, code_state_problems)와 사전등록 해시 검사(작업 파일 LF 정규화, HEAD blob)를 그대로 수행한다.
    - 이 시험은 검사 연결을 검증할 뿐, 실행 중인 구현 코드가 그 임시 저장소에 커밋돼 있음을 증명하지 않는다. 실제 구현의 커밋 연결은 CLEAN_COMMIT_E2E에서 따로 확인한다.
    - 흐름: real prepare → issue_permit 실제 발급 → bars 디렉터리로 Bar 변환·로드 → 품질 PASS → real run → 144조합과 4개 플래그 → 같은 root의 두 번째 real run 거부
    - econ_screen.run_matrix는 원본을 호출하는 spy로 감싼다.
      - spy는 진입 시 spec이 LOCKED_SPEC이고 b1_draws = 9,999이며, real_permit이 mode real이고 day·hour bars 해시를 가짐을 단정한다.
      - 그 뒤 원본 run_matrix를 b1_draws만 3으로 바꾼 spec으로 호출한다.
      - permit·품질·해시·경로 검사는 축소하지 않는다.
      - 이 시험은 9,999회 전체 계산과 그 실행 시간을 검증하지 않는다. 이 사실을 시험 이름과 docstring에 명시한다.
  - R2 경계 시각(R1 출력, 모든 규칙)
    - 첫 기준 시각: E0 2017-09-30T01:00:00Z, E1 2017-09-30T02:00:00Z, E2 2017-10-01T00:00:00Z
    - 마지막 기준 시각: E0 2024-03-31T01:00:00Z, E1 2024-03-31T02:00:00Z, E2 2024-04-01T00:00:00Z
    - d0 = 2017-06-01T00:00:00Z, F = 2017-09-29T00:00:00Z, E = 2024-03-29T00:00:00Z, g_start = 2017-10-01T00:00:00Z
    - n = T_d = G_days = 2374
    - 모든 기대값은 엔진 함수로 다시 계산하지 않고 위 문자열·정수로 고정한다.
  - R3 B1 배치 공유: R1 실행 중 benchmarks.b1_positions를 원본을 호출하는 기록용 spy로 감싸, 같은 규칙·시나리오 12조합의 배치 순열이 같은지 직접 비교한다.
  - R4 SCREEN_FLAG 연결: R1의 screen.json 조합 값으로 사전등록 9절 조건(기준 조합 순 평균 > 0, 순 평균 > B1 평균, E1·E2(25 bp, 10,000,000 KRW) 순 평균 > 0, 완전 연도 양(+) 비율 ≥ 3/5, 6절 표본 조건)을 시험 안에서 독립 계산해 출력 플래그와 비교한다.
  - R5 D1·D2: fixture 무잠금, real 잠금, 계산 가능한 기간 미달(144 계산, 표시 NOT_EVALUABLE), F > E(144개 NOT_COMPUTABLE과 사유, 0 없음, 빈 목록 아님, simulate 미호출)
  - R6 D3: R1의 모든 조합에서 n = T_d = G_days, 연간 왕복 두 출력이 같음, 하나를 다르게 만든 입력에서 ScreenComputationError
  - R7 D4: inf·NaN이 섞인 조합에서 즉시 중단, .tmp-run-* 보존, run-* 없음. OverflowError 경로가 cmd에서 같은 방식으로 보고됨
  - 기존 T10 E2E의 두 번째 fixture 실행 단정은 D1에 맞게 바꾼다. 다른 기존 단정은 약화하지 않는다.
- D8 측정: 계산 경로(simulate, B1)가 바뀌지 않고, 추가 검사는 조합 dict를 한 번 훑는 수준이다. 합성 측정은 반복하지 않는다. 기존 값의 한계(prepare·재검증·출력 미포함, 대입값은 관측값 아님, Python heap은 전체 메모리 아님)를 유지한다.
- D9 README: 시험 입력 출처를 적는다. provenance real로 기록한 합성 pull, tmp git 저장소의 사전등록 사본, 연구 증거 아님.

## CHECK_COMMANDS

CHECK_COMMANDS(아래 문자열 그대로 단독 호출. 출력 자르기·리디렉션·파이프 없음):
- COLLECT_COMMAND (상한 600 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 600 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q
- PYTEST_TARGET (상한 1800 s, 백그라운드 가능. -rs로 skip 사유를 출력)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 1800 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q -rs tests/test_econ_screen.py tests/test_runwatch.py tests/test_bar_export.py tests/test_backtest_core.py tests/test_backtest_run.py tests/test_backtest_cli.py tests/test_backtest_architecture.py tests/test_architecture_and_cli.py
- RUFF (상한 120 s. RUNWATCH-01 CHECK_2와 같은 규칙. pyproject는 a3197059와 같다)
  cd C:/MoneyLab-futval-v8-01-precheck && timeout 120 .venv/Scripts/ruff.exe check --no-cache src/moneylab/backtest/econ_screen.py src/moneylab/cli.py src/moneylab/runwatch tests/test_econ_screen.py tests/test_runwatch.py
- MYPY (상한 300 s. RUNWATCH-01 CHECK_3B의 대상 포함)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 300 .venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache src/moneylab/backtest/econ_screen.py src/moneylab/runwatch
- PYTEST_FULL (상한 5400 s, 백그라운드, 완료 알림 대기)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 5400 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q -rs
- CLI_HELP (상한 60 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 60 .venv/Scripts/python.exe -B -m moneylab econ-screen-run --help
- RUNWATCH_HELP (상한 60 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 60 .venv/Scripts/python.exe -B -m moneylab.runwatch --help
- 상한 도달은 F2로 STOP한다. 검사 대상에서 파일을 빼서 실패를 피하지 않는다.

## FAILURE_RULES

FAILURE_RULES(BGA-4, BGA-10):
- IMPLEMENTATION에서 tests/test_econ_screen.py의 실패와, ALLOWED_FILES의 M 경로에서 생긴 RUFF·MYPY 실패만 BUDGET 안에서 그 M 경로를 고쳐 같은 명령으로 다시 실행한다.
- 다음은 수정하지 않고 STOP한다.
  - tests/test_runwatch.py의 실패, Windows에서의 win_only 시험 skip, RUNWATCH 파일의 RUFF·MYPY 실패. RUNWATCH 코드는 고치지 않는다.
  - 그 밖의 기존 테스트 실패
- PYTEST_FULL에서 기존 테스트가 실패하면 STOP한다. 신규 시험만 실패하면 예산 안에서 고치고 PYTEST_FULL을 1회 더 실행할 수 있다(최대 2회).
- COMMIT 이후의 수정·실패는 STOP한다.
- 같은 실패가 연속 상한에 닿거나 예산을 넘으면 STOP한다.

## BUDGET

BUDGET(BGA-6 초기값. 실제 묶음 승인은 C1 생성 뒤 BUNDLE_AUTHORIZATION으로 따로 한다):
- 묶음 전체 21600초, 명령별 상한은 CHECK_COMMANDS를 따른다
- 전체 pytest 최대 2회(기본 1회), IMPLEMENTATION 수정 반복 최대 4회, 같은 실패 연속 최대 2회, 도구 호출 최대 200회

## PRESERVATION_CHECK

PRESERVATION_CHECK:
- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): GIT_HOST_WORKTREE의 for-each-ref --sort=refname --format="%(refname) %(objectname)", worktree list --porcelain, rev-parse HEAD HEAD^{tree}, status --porcelain=v1 --untracked-files=all --ignored=matching 원문 전체
- ref 분류
  - TASK: refs/heads/codex/econ-screen-v06-01-impl-02(생성 -> C1 -> C2)
  - OBSERVED: refs/codex/turn-diffs/checkpoints/**(기록만)
  - PRESERVE: 그 밖 전부. 하나라도 변하면 STOP한다. 다음을 포함한다.
    - refs/heads/codex/econ-screen-v06-01-impl = bd6e7400ed79ff426aa19c4b8d45e474ae7e1ee2
    - refs/heads/codex/econ-screen-v06-01 = de22c19d97afa7cb9312e3bf294e7fc29242ad5c
    - refs/heads/codex/runwatch-01 = a3197059f0c1bc41e41ba0d2c7700836cb795645
    - refs/heads/codex/futval-v8-01-run와 refs/remotes/origin/codex/futval-v8-01-run = c3d98eda9b969875f8eb7b05eb24ce3301e2dbd4
- worktree: TARGET_WORKTREE를 제외하고 항목 단위로 비교한다. TARGET_WORKTREE의 기대 변화는 branch 전환과 HEAD가 C1·C2로 가는 것뿐이다.
- host: GIT_HOST_WORKTREE의 HEAD·tree·status가 F0와 같아야 한다.
- 산출물: data/ 파일의 이름·크기·SHA-256이 진입 목록과 같고, ignored 항목 집합이 같아야 한다(.venv 내부 갱신 허용).
- 비교 시점: WORKSPACE_SETUP 종료, CLEAN_COMMIT_E2E 종료, CLOSEOUT_REPORT

## EXPECTED_ASK

EXPECTED_ASK(guard 규칙 기준. 실제 발생은 보장하지 않음):
- WORKSPACE_SETUP: task-contract(Work Order 최초 Write) 최대 1회, git-commit 1회
- IMPLEMENTATION: git-history(git restore 반입) 1회. 권한 모드에 따른 settings 편집 승인 창은 M 경로당 최대 1회(최대 5회)
- PRECOMMIT_AUDIT: 0
- COMMIT: git-commit 1회
- CLEAN_COMMIT_E2E: 0
- 시험 내부의 임시 git 호출: 0(창이 생기면 STOP)
- 그 밖의 ASK·거절·무응답·DENY는 STOP

## REQUIRED_REPORT

REQUIRED_REPORT:
- gate별 HEAD·parent·tree, 변경 집합, W·S, RUNWATCH blob 대조(반입·staging·커밋), PROTECTED diff, status(ignored 포함)
- 검사 결과·소요 시간·skip 사유, 수정 횟수, baseline 비교, BGA-8 (A) 결과(반입분 skipif 구분), BGA-8 (B) 독립 검토 필요 항목
- D1–D9 대응 위치. R1의 B1 축소(9,999 → 3)와 임시 저장소 시험의 증명 한계 명시
- PRESERVATION_CHECK 분류별 결과
- 증거 등급(GIT_VERIFIABLE, CLAUDE_REPORTED, INDEPENDENT), GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES, <GATE>_PASS, READY_FOR_<NEXT>

## STOP_CONDITIONS

STOP_CONDITIONS:
- 진입 상태: ENTRY·base·tree·branch 불일치, clean 아님, 대상이 미리 있음, 사전등록·Work Order 해시 불일치
- RUNWATCH: 반입·staging·커밋 중 어느 시점이든 blob 불일치
- 범위: ALLOWED_FILES 밖 변경, PROTECTED 변경, 예상 밖 untracked, 저장소 안 새 ignored 항목
- 검사: 기존 테스트 실패, RUNWATCH 시험 실패나 win_only skip, 예산 초과, COMMIT 이후 수정·실패, 수집 ID 감소, 시간 상한 도달
- 계약: 사전등록과 구현의 충돌(PROPOSED_ERRATA 보고)
- 보존: PRESERVE ref·worktree·host·data 변화
- 도구: guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- 기타: BUNDLE_AUTHORIZATION 원문 확인 불가, 상위 규칙과 충돌
