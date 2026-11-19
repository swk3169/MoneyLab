# Work Order: ECON-SCREEN-V06-01-IMPL-03 — 실제 선별 전 관문 보완(품질 관문 결속, 출력 root·잠금 고정, 시도 표시 시점, 코드 일치)

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/ECON-SCREEN-V06-01-IMPL-03/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: ECON-SCREEN-V06-01-IMPL-03
TASK_ID: ECON-SCREEN-V06-01-IMPL-03
TITLE: ECON-SCREEN-V06-01 실제 선별 전 관문 보완
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 281e0948d24db3d264c80807af56b252748b5ae8 (branch codex/econ-screen-v06-01-impl-02, Ce of IMPL-02, 로컬, 원격 미게시)
CANONICAL_BASE_TREE: a5c1979483516e5fccb732fa3bd1e205e0fb0ce2
ENTRY_HEAD: 281e0948d24db3d264c80807af56b252748b5ae8 (branch codex/econ-screen-v06-01-impl-02)
ENTRY_TREE: a5c1979483516e5fccb732fa3bd1e205e0fb0ce2
TARGET_BRANCH: codex/econ-screen-v06-01-impl-03
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck (재사용. .venv의 editable 설치가 이 worktree의 src를 가리킨다)
WORKSPACE_METHOD_EXCEPTION: 이 task의 WORKSPACE_SETUP에 한해 docs/tasks/README.md 표의 git worktree add -b(새 경로) 대신, TARGET_WORKTREE에서 CANONICAL_BASE_SHA를 기준으로 git switch -c codex/econ-screen-v06-01-impl-03를 1회 실행한다. 기존 branch·ref·산출물은 보존한다. 다른 task에 적용되지 않는다.
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
PYTHON: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe (재사용. 설치·갱신 없음)
PREREGISTRATION_PATH: docs/research_econ_screen_v06_01_preregistration.md
PREREGISTRATION_SHA256: 2ff766fa8e60adbc107b1ffe9ae4df30c455b616cd5345154704ff928b74705d
PREVIOUS_TASKS: ECON-SCREEN-V06-01-IMPL(C2 bd6e7400ed79ff426aa19c4b8d45e474ae7e1ee2), ECON-SCREEN-V06-01-IMPL-02(C2 eedf28df8d10a7ef7c0e894399f8a62d6fa096c1, Ce 281e0948d24db3d264c80807af56b252748b5ae8, CLOSEOUT_REPORT_PASS 범위 한정). 그 Work Order·ERRATA·DEVIATION·STOP 기록은 바꾸지 않는다.
REVIEW_BASIS: 별도 검토 에이전트의 읽기 전용 검토(2026-11-19) 결과 A1, A2, B2-a, B2-d. 증거 등급 CLAUDE_REPORTED(별도 에이전트)이며 INDEPENDENT(CI·사람)가 아니다.
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE
REQUIRED_CI_CHECKS: NOT_APPLICABLE
BUNDLE_ELIGIBLE: YES
BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E
EVIDENCE: 이 task의 모든 실행 출력은 SYNTHETIC / NOT_EVIDENCE다. real 분기 시험의 입력은 provenance만 real로 기록한 합성 pull이며 연구 증거가 아니다.

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> CHANGE_REVIEW -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 단일 gate 승인 형식
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-IMPL-03 WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - 그 밖: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-IMPL-03 <GATE> WO@<C1 SHA>
- 묶음은 docs/tasks/README.md §14 BGA-0–BGA-10과 상태 전이 기준을 그대로 따른다. 구간은 BUNDLE_MAX_RANGE 안이다. gate마다 보고하고, 전진 조건을 다시 확인해 통과하면 추가 채팅 승인 없이 다음 gate로 간다.
- CONTRACT_REVIEW, WORKSPACE_SETUP, CHANGE_REVIEW, CLOSEOUT_REPORT는 묶지 않는다.
- 프로젝트 저장소의 git commit은 C1(WORKSPACE_SETUP)과 C2(COMMIT gate) 각 1회만 허용한다. 시험이 tmp_path 안의 독립 저장소에 만드는 임시 커밋은 프로젝트 커밋이 아니다.
- settings·guard 승인 창은 사용자가 그 창에서 따로 승인한다. BGA는 그것을 대신하지 않는다.
- 상태 변경은 각각 별도 호출로 한다. 조회·해시·보존 비교는 목적별 작은 호출로 나누고, 검사 명령 뒤에 파이프·자르기·리디렉션·다른 명령을 붙이지 않는다.
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)과 고정 사전등록이 우선한다. 충돌하면 STOP한다. 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: 실제 선별 실행 전에, 검토에서 실행을 막는 결함으로 분류된 A1·A2와 운영 위험 B2-a·B2-d를 최소 수정과 오프라인 회귀 시험으로 보완한다.
- A1: run의 품질 관문을 승인 manifest와 다시 계산한 품질 결과에 결속한다.
- A2: real 출력 root를 정규화된 절대 경로로 고정하고, prepare 입력을 그 root 아래로 제한하며, 실행 잠금을 원자적으로 만든다.
- B2-a: 읽기 전용 사전 검증을 모두 마친 뒤에 실행 잠금과 시도 표시를 만든다.
- B2-d: prepare와 run의 코드 커밋이 같아야 한다.
고정 사전등록, 전략·비용·B1·SCREEN_FLAG·품질 임계값은 바꾸지 않는다. 실제 데이터의 수집·열람·계산, 합성 측정 반복, 새 감시 도구는 범위 밖이다.

## BACKGROUND

BACKGROUND:
- A1(cli.py 997–1010, 1025–1028): run은 quality.json의 summary.required_all_pass만 확인한다. quality.json은 같은 디렉터리의 SHA256SUMS로만 보호되므로 둘을 함께 바꿀 수 있다. 승인 manifest의 quality_sha256은 대조되지 않고, 다시 계산한 Q 값이 모두 PASS인지도 판정하지 않는다.
- A2(cli.py 900–904, 989–991, 1016–1018): real root는 --out의 디렉터리 이름만 검사된다. 잠금은 그 root 안에서만 확인한다. prepare 위치는 root와 무관하다. check_run_lock(검사) 뒤 begin_output(고유 이름 생성)이라 동시에 시작한 두 실행이 모두 통과할 수 있다(원자성 없음).
- B2-a(cli.py 989–1000): 시도 표시(.tmp-run-*)가 인자·해시·경로 검증 전에 생겨, 입력 오류 하나로 1회 실행 기회가 소진된다.
- B2-d(cli.py 958 vs 1016–1018): prepare와 run이 각각 clean인지만 검사하고 같은 커밋인지는 확인하지 않는다.
- 잠금 전 검증 실패의 취급
  - 잠금 전 사전 검증에서 거부되면 수익성 계산이 시작되지 않았다는 운영 사실을 기록한다.
  - 그 경우에도 해당 승인 실행은 STOP한다. 잠금이 없다는 이유로 자동 재시도하거나 다른 인자로 다시 실행하지 않는다.
  - 이후 재개 가능 여부는 고정 사전등록과 별도 승인으로 판단한다. 이 Work Order는 재시도·재실행 권한을 만들지 않는다.
  - 잠금을 얻은 뒤의 실패는 기존대로 잠금·시도 표시·부분 산출물을 보존한다.
- B2-b(마지막 1시간 bucket 2024-03-31T23:00Z)는 코드를 바꾸지 않고 실행 계약의 사전 입력 확인 항목으로 둔다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 출력(PRESERVATION_CHECK, 상태 변경 전 첫 호출)
  - 진입 확인
    - HEAD·tree·branch가 ENTRY와 같고 clean이다.
    - TARGET_BRANCH와 docs/tasks/ECON-SCREEN-V06-01-IMPL-03이 없다.
    - 사전등록 blob 내용 sha256이 PREREGISTRATION_SHA256과 같다.
    - data/ 아래 파일의 이름·크기·SHA-256 목록을 남긴다(내용은 열지 않음).
  - git -C C:/MoneyLab-futval-v8-01-precheck switch -c codex/econ-screen-v06-01-impl-03 281e0948d24db3d264c80807af56b252748b5ae8 1회
  - Work Order를 승인 바이트로 Write 1회
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/ECON-SCREEN-V06-01-IMPL-03/WORK_ORDER.md 1회
  - C1 커밋 1회
  - 종료 시 PRESERVATION_CHECK
- IMPLEMENTATION(진입: HEAD = C1, clean)
  1. 수집 baseline: 새로 수집하지 않는다. IMPL-02 PRECOMMIT_AUDIT의 COLLECT_COMMAND 출력(세션 tool-results/b1nbqh2jj.txt, 3,332개 ID)을 baseline으로 쓴다. 근거: 그 수집 뒤 IMPL-02 C2 commit blob이 S와 같았고, C2 이후 tests·src 변경이 없다(Ce는 ERRATA 문서만 추가). 파일을 확인할 수 없으면 변경 전에 COLLECT_COMMAND를 1회 실행해 baseline으로 쓴다.
  2. ALLOWED_FILES만 Edit로 수정한다.
  3. PYTEST_TARGET, RUFF, MYPY가 통과할 때까지 FAILURE_RULES 안에서 수정·재실행한다.
  4. 3이 통과한 뒤 PYTEST_FULL을 백그라운드로 1회 실행하고 완료 알림을 기다린다.
  5. 종료 기준: 변경 ⊆ ALLOWED_FILES. 작업 파일 해시 집합 W와 stage될 내용 해시 집합 S를 기록한다.
- PRECOMMIT_AUDIT(읽기와 감사만. staging·커밋 없음)
  - 변경 집합 = ALLOWED_FILES 계획, git diff --check exit 0, PROTECTED diff 0, 예상 밖 untracked 0
  - BGA-8 (A): COLLECT_COMMAND 1회 실행 후 baseline과 비교해 감소한 ID 0, ALLOWED_FILES 밖 테스트 파일 변경 0, skip·skipif·xfail 추가 0
  - BGA-8 (B): "독립 검토 필요"로 보고하며 CHANGE_REVIEW에서 다룬다
  - 계약 spot check D1–D8, W·S 불변
- COMMIT(독립 gate)
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- <ALLOWED_FILES 4개 경로 명시> 1회
  - 커밋 전 필수 확인. 하나라도 다르면 커밋하지 않고 STOP한다.
    - staged 경로 집합 = ALLOWED_FILES 4개
    - staged blob 내용 SHA-256 집합 = S
    - git -C C:/MoneyLab-futval-v8-01-precheck diff --cached --check exit 0
  - C2 커밋 1회
  - 커밋 후 확인: parent(C2) = C1, 변경 집합 = ALLOWED_FILES 4개, commit blob 내용 = S, clean
- CLEAN_COMMIT_E2E(진입: HEAD = C2, clean)
  - PYTEST_TARGET 1회(백그라운드 가능), CLI_HELP 1회. 전체 pytest는 반복하지 않는다.
  - 커밋과 작업 파일의 연결: ALLOWED_FILES의 작업 파일 내용(LF 정규화)과 C2 blob 내용 SHA-256이 같다.
  - 실행 전후 git status(ignored 포함)가 같아야 한다.
  - 종료 시 PRESERVATION_CHECK
- CHANGE_REVIEW(별도 승인. 진입: HEAD = C2, clean)
  - 구현 작성에 참여하지 않은 별도 에이전트에게 읽기 전용 도구(Read·Grep·Glob)만 주어, C1..C2 변경분과 고정 사전등록·관련 코드·시험을 검토하게 한다.
  - 검토 질문: A1·A2·B2-a·B2-d가 실제로 막히는지, 새 우회 경로나 단정 완화가 생겼는지, 시험이 같은 구현으로 기대값을 만들거나 spy로 검증 대상을 대체하는지.
  - 결과는 발견 사항(파일·행·실패 조건·영향)과 실행 차단 여부로 보고한다. 증거 등급은 CLAUDE_REPORTED(별도 에이전트)이며 INDEPENDENT(CI·사람)로 쓰지 않는다.
  - 이 gate는 파일·Git을 바꾸지 않는다. 차단 결함이 나오면 CLOSEOUT_REPORT 전에 보고하고 멈춘다.
- CLOSEOUT_REPORT: 읽기 전용 보존 확인과 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 실데이터
  - 수집·열람·변환·계산, candles-pull(dry-run 포함), 네트워크
  - econ-screen-prepare·econ-screen-run의 실제 데이터 실행
- 측정과 감시
  - 합성 자원 측정의 반복, RUNWATCH로 실제 명령을 감시하는 실행
- 계약 문서: 사전등록·이전 Work Order·ERRATA·이 Work Order 수정
- 범위 확장
  - 사전등록·전략·비용·B1·SCREEN_FLAG·품질 임계값 변경
  - 범용 리팩터링, 사용하지 않는 클래스 정리, 새 도구
  - RUNWATCH 코드 수정, B2-b를 위한 계산 코드 변경
  - 자동 재실행, 기존 시도 표시·잠금의 삭제 기능
- 시험 약화
  - permit·품질·경로·해시·clean·커밋 검사를 mock으로 바꾸거나 조건을 완화
  - 운영 CLI에 시험용 옵션 추가
- Git
  - fetch, push, PR, merge
  - git add의 전체 지정, amend, no-verify, reset, restore, stash, rebase, cherry-pick
  - 지정 외 checkout·switch, 프로젝트 저장소의 지정 외 커밋
- 실행과 정리
  - 셸 출력 폐기·리디렉션·출력 분기, 임시 스크립트 파일
  - guard·hook·settings·권한 규칙·메모리 변경
  - 기존 산출물·다른 branch·worktree·untracked·ignored 항목의 변경·정리

## ALLOWED_FILES

ALLOWED_FILES(모두 C2):
- M src/moneylab/cli.py
- M src/moneylab/backtest/econ_screen.py
- M tests/test_econ_screen.py
- M docs/backtest_design.md (15.1절 문구와 17절 개정 이력 행만)

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/ECON-SCREEN-V06-01-IMPL-03/WORK_ORDER.md (WORKSPACE_SETUP 전용, 승인 바이트로 최초 1회). ALLOWED_FILES에 속하지 않는다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/** (위 예외의 최초 생성 1회 제외)
- docs/research_*_preregistration*.md, configs/**
- docs/** 중 docs/backtest_design.md를 뺀 전부
- src/moneylab/** 중 ALLOWED_FILES의 src 경로를 뺀 전부. backtest/bars_io.py, backtest/portfolio.py, providers/upbit/**, runwatch/**, config.py, backtest/run.py, backtest/vault.py, research/**, domain/**를 포함한다
- tests/** 중 tests/test_econ_screen.py를 뺀 전부(tests/test_runwatch.py, tests/fixtures/** 포함)
- .claude/**, .github/**, CLAUDE.md, README.md, .gitignore, .gitattributes, pyproject.toml, requirements*.txt
- data/** 기존 산출물

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## UNTRACKED_AND_IGNORED

UNTRACKED_AND_IGNORED:
- 예상 untracked: WORKSPACE_SETUP에서 Write 뒤 add 전까지의 Work Order. 그 밖의 untracked는 F3이다.
- 허용된 ignored 내부 변화: .venv/.mypy_cache 내용 갱신. 저장소 안 새 ignored 항목(__pycache__, .pytest_cache, .ruff_cache, .mypy_cache(.venv 밖), data/ 아래 새 파일)은 금지한다.
- 시험 임시 자원: pytest tmp_path(OS 임시 영역)만 허용한다.
  - 독립 git 저장소, 그 안의 임시 커밋, 합성 pull, MONEYLAB_DATA_DIR로 지정한 tmp 데이터 루트와 그 아래 출력이 여기에 포함된다.
  - 임시 커밋은 시험 코드가 subprocess로 만들며 다음 옵션을 쓴다: git -c user.name=econ-screen-test -c user.email=test@example.invalid -c commit.gpgsign=false -c core.hooksPath=<tmp_path 안의 빈 디렉터리>. 프로젝트 저장소에는 아무것도 쓰지 않는다.
  - 이 임시 git 호출은 도구 호출이 아니므로 guard·settings 창이 생기지 않을 것으로 예상한다. 창이 생기면 예상 밖 ASK로 STOP한다.

## COMMIT_PLAN

COMMIT_PLAN:
- C1(WORKSPACE_SETUP): parent = CANONICAL_BASE_SHA, A docs/tasks/ECON-SCREEN-V06-01-IMPL-03/WORK_ORDER.md, 메시지 docs(task): add ECON-SCREEN-V06-01-IMPL-03 work order
- C2(COMMIT gate 1회): parent = C1, ALLOWED_FILES 4개, 메시지 fix(backtest): bind ECON-SCREEN-V06-01 run gates
- 본문·trailer 없음. CANONICAL_BASE_SHA..C2 변경 경로는 WORK_ORDER.md와 ALLOWED_FILES뿐이다. 프로젝트 커밋은 위 2회뿐이며 시험의 임시 커밋은 포함되지 않는다.
- COMMIT 이후 수정·실패는 STOP이며 후퇴하지 않는다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 real root 고정(A2)
  - real 모드의 출력 root는 실행 시점의 settings가 정하는 정규 경로 settings.processed_dir / "econ_screen_v06_01"을 resolve()한 절대 경로 하나다.
  - prepare·run 모두 --out이 주어지면, 그 resolve() 값이 이 경로와 같을 때만 받는다. 이름만 같은 다른 위치는 거부한다.
  - 거부는 출력 디렉터리나 시도 표시를 만들기 전에 한다.
  - fixture 모드의 root 규칙(이름이 -fixture로 끝남)은 바꾸지 않는다.
  - 한계: settings.processed_dir는 환경변수 MONEYLAB_DATA_DIR로 바뀔 수 있다. 이 고정은 환경 변경까지 전역적으로 막는 보안 장치가 아니며, 한 실행 환경 안에서 prepare·run·잠금의 위치를 하나로 맞추는 장치다. 실제 실행 계약에서 환경(MONEYLAB_DATA_DIR 포함)·root·커밋을 고정한다.
- D2 prepare 입력 위치(A2): real run의 --prepare는 resolve()한 부모가 D1의 root이고, 이름이 prepare-로 시작하며, 디렉터리여야 한다. 아니면 계산 전에 거부한다.
- D3 원자적 실행 잠금(A2)
  - econ_screen에 acquire_run_lock(root)를 둔다.
  - 기존 check_run_lock 검사를 먼저 하고, 이어서 os.mkdir(root / "run-lock")을 exist_ok 없이 한 번 호출해 잠금을 얻는다.
  - mkdir이 FileExistsError면 거부한다. 동시에 시작한 두 실행 중 하나만 성공한다.
  - run-lock 디렉터리는 지우지 않는다. 이름이 run-으로 시작하므로 이후 check_run_lock 검사에서도 시도 기록으로 잡힌다.
  - 잠금 해제나 기존 표시 삭제 기능은 만들지 않는다.
- D4 품질 관문 결속(A1). 두 가지를 구분한다.
  - 저장 기록의 결속(해시 대조, 재계산 없음)
    - 승인된 manifest.json의 SHA-256이 --expect-prepare-manifest-sha256과 같아야 한다. 이 값은 64자리 소문자 hex여야 한다.
    - sha256(quality.json 바이트) == manifest["quality_sha256"]이어야 한다.
  - 실제 품질의 판정(재계산)
    - pull 검사와 bars를 이용해 품질을 D5의 해당 단계에서 한 번 다시 계산한다.
    - 그 결과가 저장된 pull_stage·bar_quality와 같은지 확인한다.
    - 같은 재계산 결과로 econ_screen.quality_summary(stage, quality)["required_all_pass"]가 True인지 직접 판정한다. True가 아니면 잠금·계산 전에 거부한다.
  - 저장된 summary.required_all_pass는 판정에 쓰지 않는다. 기록 대조에만 쓴다.
  - D4는 D5와 별도로 품질을 한 번 더 계산하라는 뜻이 아니다.
- D5 사전 검증 후 잠금(B2-a). 잠금 전에 모든 검증을 한다는 원칙을 유지한다. cmd_econ_screen_run의 순서:
  1. mode·spec·인자 형식(승인 manifest 해시가 64자리 소문자 hex인지 포함)
  2. D1 root와 D2 prepare 위치
  3. prepare SHA256SUMS(verify_output)
  4. 승인 manifest 해시 대조
  5. study·mode·kind·spec 일치
  6. D4 저장 기록 결속: quality.json 해시 == manifest quality_sha256(재계산 없음)
  7. pull 재검사(pull_stage 재계산)
  8. D6 코드 일치
  9. permit 발급(real: 사전등록 해시·clean)
  10. bars 해시 확인과 로드
  11. D4 실제 품질 판정: bar_quality를 1회 재계산하고, 7과 함께 저장값과 대조한 뒤, 재계산 결과로 required_all_pass를 판정
  12. (real) D3 잠금 획득
  13. 시도 표시 .tmp-run-<stamp> 생성
  14. 계산과 출력
  - 1–11의 실패: 잠금·시도 표시·출력을 만들지 않는다. 계산이 시작되지 않았다는 사실을 보고하고, 그 승인 실행은 STOP한다(BACKGROUND의 잠금 전 검증 실패 취급).
  - 12 이후의 실패: 잠금·시도 표시·이미 쓴 파일을 보존하며 자동 재실행하지 않는다.
  - fixture 모드는 잠금 없이 13부터 같다.
- D6 코드 일치(B2-d)
  - real run은 현재 backtest_code_state(REPO_ROOT)["commit"]이 prepare manifest의 code_state["commit"]과 같아야 한다. 다르면 계산 전에 거부한다.
  - clean 여부는 기존 permit 검사가 판정한다.
  - 실제 실행 계약에서 prepare와 run은 같은 승인 커밋으로 고정한다.
- D7 시험(tests/test_econ_screen.py, 오프라인, tmp_path만)
  - 공통 준비
    - real 경로 시험은 monkeypatch.setenv("MONEYLAB_DATA_DIR", <tmp>)로 settings.processed_dir를 tmp 아래로 둔다. 운영 경로 고정 논리 자체는 바꾸지 않는다.
    - clean·사전등록 해시 검사는 IMPL-02 R1과 같은 독립 tmp 저장소와 REPO_ROOT 전환으로 실제 git에 대해 수행한다.
    - 비용을 줄이기 위해 real 합성 pull과 real prepare 하나를 module 범위에서 만들고, 각 시험은 자기 tmp 데이터 루트로 그 prepare 디렉터리를 바이트 그대로 복사해 쓸 수 있다. 복사로 manifest 해시는 바뀌지 않는다.
  - S1 A1
    - (a) quality.json을 바꾸고 SHA256SUMS를 다시 만들어도, 승인 manifest의 quality_sha256 불일치로 거부된다.
    - (b) quality.json·SHA256SUMS·manifest를 모두 바꾸면, 승인된 manifest 해시 불일치로 거부된다.
    - (c) 실제 Q가 실패한 prepare에서 summary만 PASS로 조작하고 quality_sha256·SHA256SUMS·manifest를 맞춘 뒤, 그 새 manifest 해시를 승인값으로 넘겨도 재계산 판정으로 거부된다.
    - 세 경우 모두 run_matrix가 호출되지 않고(호출되면 실패하는 spy), 잠금·시도 표시가 생기지 않는다.
  - S2 A2
    - 다른 위치의 econ_screen_v06_01을 --out으로 주면 prepare·run 모두 거부되고, 어느 위치에도 출력·잠금·시도 표시가 생기지 않는다.
    - 다른 root에 있는 prepare를 넘기면 거부된다.
    - acquire_run_lock을 같은 root에 두 번 호출하면 두 번째가 거부된다.
    - 여러 스레드가 동시에 호출하면 정확히 하나만 성공한다.
  - S3 B2-a
    - 잘못된 manifest 해시(대문자 hex, 다른 값, 길이 오류)와 존재하지 않는 prepare 경로는 거부되고, run-lock·.tmp-run-*가 생기지 않는다.
    - 잠금을 얻은 뒤 실패(run_matrix가 오류를 내도록 한 경우)에는 run-lock과 .tmp-run-*가 보존되고, 이후 real run이 거부된다.
  - S4 B2-d: prepare 뒤 독립 tmp 저장소에 새 커밋을 만들어 clean이지만 다른 커밋이 되게 하면, run이 계산 전에 거부되고 잠금·시도 표시가 생기지 않는다.
  - 기존 R1·R5(real 잠금)는 D1–D5에 맞게 경로를 바꿀 수 있다. 다른 기존 단정은 약화하지 않는다.
- D8 측정: 계산 경로(simulate, B1)를 바꾸지 않으므로 합성 측정을 반복하지 않는다. 기존 값의 한계(prepare·재검증·출력 미포함, Python heap만 측정)를 유지한다.

## CHECK_COMMANDS

CHECK_COMMANDS(아래 문자열 그대로 단독 호출. 출력 자르기·리디렉션·파이프 없음):
- COLLECT_COMMAND (상한 600 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 600 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q
- PYTEST_TARGET (상한 1800 s, 백그라운드 가능. -rs로 skip 사유 출력)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 1800 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q -rs tests/test_econ_screen.py tests/test_bar_export.py tests/test_backtest_core.py tests/test_backtest_run.py tests/test_backtest_cli.py tests/test_backtest_architecture.py tests/test_architecture_and_cli.py
- RUFF (상한 120 s)
  cd C:/MoneyLab-futval-v8-01-precheck && timeout 120 .venv/Scripts/ruff.exe check --no-cache src/moneylab/backtest/econ_screen.py src/moneylab/cli.py tests/test_econ_screen.py
- MYPY (상한 300 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 300 .venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache src/moneylab/backtest/econ_screen.py
- PYTEST_FULL (상한 5400 s, 백그라운드, 완료 알림 대기)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 5400 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q -rs
- CLI_HELP (상한 60 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 60 .venv/Scripts/python.exe -B -m moneylab econ-screen-run --help
- 상한 도달은 F2로 STOP한다. 검사 대상에서 파일을 빼서 실패를 피하지 않는다.

## FAILURE_RULES

FAILURE_RULES(BGA-4, BGA-10):
- IMPLEMENTATION에서 tests/test_econ_screen.py의 실패와, ALLOWED_FILES의 src 경로에서 생긴 RUFF·MYPY 실패만 BUDGET 안에서 ALLOWED_FILES를 고쳐 같은 명령으로 다시 실행한다.
- 그 밖의 기존 테스트 파일에서 난 실패는 원인과 baseline에 관계없이 수정하지 않고 STOP한다.
- PYTEST_FULL에서 기존 테스트가 실패하면 STOP한다. 신규·수정 시험만 실패하면 예산 안에서 고치고 PYTEST_FULL을 1회 더 실행할 수 있다(최대 2회).
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
  - TASK: refs/heads/codex/econ-screen-v06-01-impl-03(생성 -> C1 -> C2)
  - OBSERVED: refs/codex/turn-diffs/checkpoints/**(기록만)
  - PRESERVE: 그 밖 전부. 하나라도 변하면 STOP한다. 다음을 포함한다.
    - refs/heads/codex/econ-screen-v06-01-impl-02 = 281e0948d24db3d264c80807af56b252748b5ae8
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
- IMPLEMENTATION: settings 편집 승인 창은 ALLOWED_FILES 경로당 최대 1회(최대 4회). guard ASK 0
- PRECOMMIT_AUDIT: 0
- COMMIT: git-commit 1회
- CLEAN_COMMIT_E2E: 0
- CHANGE_REVIEW: 0(별도 에이전트는 읽기 전용 도구만 쓴다)
- 시험 내부의 임시 git 호출: 0(창이 생기면 STOP)
- 그 밖의 ASK·거절·무응답·DENY는 STOP

## REQUIRED_REPORT

REQUIRED_REPORT:
- gate별 HEAD·parent·tree, 변경 집합, W·S, PROTECTED diff, status(ignored 포함)
- 검사 결과·소요 시간·skip 사유, 수정 횟수, baseline 비교, BGA-8 (A) 결과
- D1–D8 대응 위치와 S1–S4 결과, 잠금 원자성 시험 결과
- CHANGE_REVIEW 발견 사항과 실행 차단 여부(증거 등급 CLAUDE_REPORTED 별도 에이전트)
- PRESERVATION_CHECK 분류별 결과
- 증거 등급(GIT_VERIFIABLE, CLAUDE_REPORTED, INDEPENDENT), GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES, <GATE>_PASS, READY_FOR_<NEXT>

## STOP_CONDITIONS

STOP_CONDITIONS:
- 진입 상태: ENTRY·base·tree·branch 불일치, clean 아님, 대상이 미리 있음, 사전등록·Work Order 해시 불일치
- 범위: ALLOWED_FILES 밖 변경, PROTECTED 변경, 예상 밖 untracked, 저장소 안 새 ignored 항목
- 검사: 기존 테스트 실패, 예산 초과, COMMIT 이후 수정·실패, 수집 ID 감소, 시간 상한 도달
- 계약: 사전등록과 구현의 충돌(PROPOSED_ERRATA 보고)
- 보존: PRESERVE ref·worktree·host·data 변화
- 리뷰: CHANGE_REVIEW에서 실행 차단 결함 발견
- 도구: guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- 기타: BUNDLE_AUTHORIZATION 원문 확인 불가, 상위 규칙과 충돌

## FOLLOW_UP_PLAN

FOLLOW_UP_PLAN(이 Work Order의 승인 범위가 아니다. 이후 별도 계약·승인으로 한다):
- 공개 백업: 최종 보완 branch(codex/econ-screen-v06-01-impl-03) 하나를 push해 ECON 계보 전체를 보존한다. push 전에 범위(main 기준 계보, FUTVAL 파일·data 미포함)를 다시 확인하고 따로 승인한다.
- 연구 결과는 우선 비공개 보고로 둔다. 공개는 따로 결정한다.
- 실행 계약의 예산 후보
  - prepare RUNWATCH 3600초, run RUNWATCH 7200초
  - 가용 RAM 하한: 시작 12 GiB, 중단 6 GiB(총 RAM 약 31.2 GiB 기록 재사용). 실행 직전에 가용량을 확인한다.
  - 이 값들은 확정이 아니다.
- 실행 계약은 환경(MONEYLAB_DATA_DIR 포함)·root·커밋을 고정한다(D1 한계).
- B2-b: pull 식별값 승인 단계에서 hour pull의 last_start = 2024-03-31T23:00:00Z인지 사전 입력 확인 항목으로 본다.
