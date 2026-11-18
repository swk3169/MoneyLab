# Work Order: FUTVAL-V8-01-RUN — RUNWATCH 감시 아래 FUTVAL-V8-01 본 실행 1회와 무결성 확인

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: FUTVAL-V8-01-RUN
TASK_ID: FUTVAL-V8-01-RUN
TITLE: 승인된 자원 예산으로 FUTVAL-V8-01 본 실행을 RUNWATCH 감시 아래 1회 실행하고, 결과 내용을 열지 않고 무결성만 확인
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: a3197059f0c1bc41e41ba0d2c7700836cb795645 (RUNWATCH-01 Ce)
CANONICAL_BASE_TREE: 96625e93d5b9e969b9b79f9e19ae097d52adaee6
CANONICAL_BASE_PARENT: 9790420c14d471420a86aeca301311f2e0ee09e6 (RUNWATCH-01 C2, 감시 도구 구현 식별 커밋)
RESEARCH_IMPLEMENTATION_COMMIT: 155aeef016927615bf8449c9cf1060e497d39f56
BASE_REMOTE_REF: NONE (로컬 커밋. fetch하지 않는다)
TARGET_BRANCH: codex/futval-v8-01-run
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck (재사용. 현재 branch codex/runwatch-01에서 branch만 전환한다)
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
ENV_PYTHON: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe (editable 설치. 재설치하지 않는다)
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE (PUSH·PR_CI·MERGE gate 없음)
REQUIRED_CI_CHECKS: NOT_APPLICABLE
BUNDLE_ELIGIBLE: NO
RELATED_TASKS: FUTVAL-V8-01(사전등록 고정), -IMPL, -PRECHECK, -SMOKE-PERF, RUNWATCH-01(판정·보류·사건·이탈·D3 절차 차이 불변)
PRESERVED_OUTPUT: PRESERVED_OUTPUT 절

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> RESOURCE_BUDGET_APPROVAL -> MAIN_RUN -> POST_RUN_INTEGRITY -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- WORKSPACE_SETUP: GATE_AUTHORIZATION: FUTVAL-V8-01-RUN WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
- RESOURCE_BUDGET_APPROVAL: 사용자의 결정이며 에이전트 행위가 없다. 형식은 RESOURCE_BUDGET_APPROVAL: FUTVAL-V8-01 WO@<C1 SHA> WORKERS=<n> EXPECTED_SECONDS=<n> ABORT_MULTIPLIER=<n> MAX_SECONDS=<n> ABSOLUTE_CAP_SECONDS=<n> START_MIN_AVAILABLE_BYTES=<n> ABORT_BELOW_AVAILABLE_BYTES=<n> POLL_SECONDS=<n> VERIFY_SECONDS=<n>. 이 승인은 본 실행 승인이 아니다. 값은 RESOURCE_BUDGET 절의 고정값과 같아야 한다
- MAIN_RUN: GATE_AUTHORIZATION: FUTVAL-V8-01-RUN MAIN_RUN WO@<C1 SHA> BUDGET@<RESOURCE_BUDGET_APPROVAL 원문과 같은 값>. 본 실행 1회 승인이며, 결과 열람 승인이 아니다
- POST_RUN_INTEGRITY, CLOSEOUT_REPORT: 각각 GATE_AUTHORIZATION: FUTVAL-V8-01-RUN <GATE> WO@<C1 SHA>
- 결과 열람: 이 Work Order 밖이다. 사전등록 §11에 따라 별도 1회 승인을 받는다
- 상태 변경은 각각 별도 도구 호출로 실행하고, 결과를 확인한 뒤 다음으로 간다. 검사·실행 명령 뒤에 파이프·자르기·리디렉션·다른 명령을 붙이지 않는다
- 각 gate 보고 뒤 멈춘다. 이 Work Order는 TASK_COMPLETE를 선언하지 않는다

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)과 고정 사전등록(docs/research_futval_v8_01_preregistration.md, sha256 d77549ed4cc732f0b2fb0151fcf17913d319ce8e0de929827fc3a8c9c7ea9b91)이 우선한다. 복제하지 않고 바꾸지 않는다. 충돌하면 STOP한다. 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: 사전등록 §9의 본 실행(이름공간 FUTVAL-V8-01, 12셀, R 10,000, B 9,999)을 승인된 자원 예산으로 RUNWATCH 감시 아래 1회 실행한다. 결과 파일 내용은 열지 않고, 감시·종료·파일 집합·무결성만 확인한다. 연구 설계·seed·R·B·셀·판정은 바꾸지 않는다.

## BACKGROUND

BACKGROUND:
- 사전등록 §10·§11: 본 실행 worker 수, wall-clock 상한, 중단 배수는 성능 측정 뒤 별도 승인으로 정한다. 예산 부족을 이유로 설계를 바꾸지 않으며, 예산이 부족하면 실행하지 않거나 새 study로 간다
- 예산 후보(사용자 제시, 미승인): worker 4, EXPECTED_SECONDS 49,800, 중단 배수 2, 유효 시간 중단 기준 99,600 s, 절대 상한 100,800 s, 시작 가용 RAM ≥ 12 GiB, 실행 중 가용 RAM < 6 GiB이면 중단, poll 30 s, verify 30 s
- RUNWATCH-01: DRILL_PASS·CLOSEOUT_REPORT_PASS. 단, D3의 15초·30초 조회를 생략한 것은 계약에 명시되지 않은 절차 차이이며 기록으로 유지한다. inline-code 승인 창 횟수는 미확인이다. 실제 세션 단절, 장시간 내구성, PeakJobMemoryUsed 값의 의미는 검증하지 않았다
- 연구 프로세스 최대 메모리는 SMOKE-PERF에서 null(미측정)이었다
- manifest.json의 code.commit은 실행 시점 HEAD(이 Work Order의 C1)로 기록된다. 연구 소스 blob은 RESEARCH_IMPLEMENTATION_COMMIT과 같아야 한다

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 출력(PRESERVATION_CHECK). 기준 확인: HEAD·tree·branch·clean, 계약·소스·PRESERVED_OUTPUT 해시. TARGET_BRANCH와 Work Order 경로가 없는지 확인
  - git -C C:/MoneyLab-futval-v8-01-precheck switch -c codex/futval-v8-01-run 1회
  - docs/tasks/FUTVAL-V8-01-RUN/WORK_ORDER.md Write 1회(승인 바이트)
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/FUTVAL-V8-01-RUN/WORK_ORDER.md 1회
  - C1 커밋 1회(메시지 docs(task): add FUTVAL-V8-01-RUN work order, 본문·trailer 없음)
  - 종료 시 PRESERVATION_CHECK 비교
- MAIN_RUN
  - PRE_RUN_CHECK 절의 읽기 전용 확인
  - RUN_COMMAND 1회. Bash 백그라운드로 실행하고 완료 알림을 기다린다
  - 완료 알림 뒤 watcher 출력 한 줄과 watch_final.json의 운영 필드만 확인한다
- POST_RUN_INTEGRITY: INTEGRITY_CHECK 절의 읽기 전용 확인
- CLOSEOUT_REPORT: PRESERVATION_CHECK 비교와 종결 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위, CONTRACT_FILE_EXCEPTION 밖 tracked 변경, PROTECTED_FILES 변경
- 사전등록·Work Order 수정
- 연구 설계·seed·R·B·셀·α·ε·λ·판정 규칙 변경, TEST 이름공간 외의 범위 변경
- 결과 4개 파일(manifest.json, design.json, cells.json, summary.json) 내용 열람. 결과를 출력·요약·복사하는 행위
- 결과 수치의 PR·커밋·CI·공개 문서 기재
- 자동 재실행, 재시도, 예산 증가 뒤 재실행, worker 수 변경 뒤 재실행, 부분 결과 사용, 다른 출력 디렉터리로 다시 실행
- 실행 중·실행 뒤의 추가 결과 열람, 재실행, 설계 변경
- 실행 중 연구 출력 디렉터리 조회. 진행 확인은 사용자가 요청할 때 watch_state.json 읽기만 허용한다
- 이름·경로·PID 검색에 근거한 프로세스 종료, Job 밖 프로세스 조작, TaskStop(사용자의 명시 지시가 있을 때만 이 실행의 백그라운드 작업 ID에 1회)
- breakaway, 작업 스케줄러·서비스 등록, 전원·절전 설정 변경, 권한 규칙·guard·hook·settings 변경
- 설치, 네트워크, fetch, push, PR, merge
- git add . / -A, --no-verify, amend, reset, restore, stash, clean, rebase, cherry-pick
- 셸 출력 폐기·리디렉션·tee, 임시 스크립트 파일
- 기존 산출물·다른 branch·worktree·untracked·ignored 항목의 변경·정리. 부분 산출물 삭제

## ALLOWED_FILES

ALLOWED_FILES: 없음 (코드·테스트 변경 없음)

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/FUTVAL-V8-01-RUN/WORK_ORDER.md (WORKSPACE_SETUP 전용, 승인 바이트로 최초 1회)

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/FUTVAL-V8-01-RUN/** (CONTRACT_FILE_EXCEPTION 최초 생성 1회 제외), docs/tasks/FUTVAL-V8-01*/**, docs/tasks/RUNWATCH-01/**, docs/research_*_preregistration*.md
- src/**, tests/**, pyproject.toml, requirements*.txt, .gitignore, .gitattributes, CLAUDE.md, .claude/**, .github/**, configs/**, docs/**(위 예외 제외)
- data/** 기존 산출물(PRESERVED_OUTPUT)

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## COMMIT_PLAN

COMMIT_PLAN:
- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/FUTVAL-V8-01-RUN/WORK_ORDER.md 하나. 메시지 docs(task): add FUTVAL-V8-01-RUN work order, 본문·trailer 없음
- 이 Work Order의 커밋은 C1 하나뿐이다. 본 실행 HEAD는 C1이다

## SOURCE_IDENTITY

SOURCE_IDENTITY (MAIN_RUN 진입 시 HEAD = C1 기준):
- 연구 소스: SOURCE_FILES 4개의 HEAD blob이 RESEARCH_IMPLEMENTATION_COMMIT의 blob과 같아야 한다
  - procedures.py = bf6dfddea822f3af0d6e50274c8b3b5b0c767daf
  - stats.py = 01b6472cadb2ce2437a613b09d419a999398c685
  - futval_v8_01.py = 462eb3d3a37c4efa9a5eb64443db9245af8a8115
  - tests/test_futval_v8_01.py = f985319878545ca9d04c7f978162c362270c5564
  - working 바이트를 LF로 정규화한 값이 HEAD blob과 같아야 한다
- 감시 도구: src/moneylab/runwatch/ 4개 파일과 tests/test_runwatch.py의 HEAD blob이 C2와 같아야 한다. commit 내용 S와 working W가 같아야 한다(__init__.py 7c88c91b…, __main__.py a69b77e7…, winjob.py 5c06755c…, watch.py bc9560ac…, test_runwatch.py f996714b…)
- 계약: 사전등록 d77549ed…, RUNWATCH-01 WORK_ORDER.md e0432beb…, ERRATA-001.md 95d5fbbc…, 이 Work Order 승인 SHA-256
- CANONICAL_BASE_SHA..C1 변경은 이 Work Order 파일 하나뿐이다
- 비교 방법: 위 축약 표기는 식별용이며, 비교는 축약값이 아니라 전체 값과 실제 바이트로 한다. C2 전체 blob ID는 src/moneylab/runwatch/__init__.py a42ce7867117a8c76a2ae4f3c175f63c86c7d46d, src/moneylab/runwatch/__main__.py b973f05e12b5e0193da09b1783bbd99354a07276, src/moneylab/runwatch/winjob.py d00a408557b4bfbbd67df337879bce2d8b12dc91, src/moneylab/runwatch/watch.py 316eedaa61868bd52ea7630c33ac8cf164e72b93, tests/test_runwatch.py 78e59a4bd9f32699a30dcfb37ee55f69938e45b8이다. 같은 순서의 전체 SHA-256(S = W)은 7c88c91b58e20e037c51d147cf2dff7ce4fc5a8f03d159071e2f30b4d49a3b91, a69b77e7f83e4dac6ba54736a1f4b226b114d35eee50b63795e6120b9e03aa27, 5c06755c9e67d2299345b5411eb8368f2559340094d14259150b48e8e672bb7d, bc9560ac26f9abe8b3bb243050522a7b95566fde21f7ec359476b50b82d7b26a, f996714bf39838a41e2c1ac5d2c6934edc3e26124beae1da231af793b1b1dbe5이다. 계약의 전체 SHA-256은 사전등록 d77549ed4cc732f0b2fb0151fcf17913d319ce8e0de929827fc3a8c9c7ea9b91, RUNWATCH-01 WORK_ORDER.md e0432beb06e41f424e42f42f0b192f4ee7901c25e58578118587a172a2ed60e1, ERRATA-001.md 95d5fbbcf20bff379d901eca400dca50159788c7c026da78105055134ebf17ed이다

## RESOURCE_BUDGET

RESOURCE_BUDGET (이 Work Order에 고정. RESOURCE_BUDGET_APPROVAL 전에는 효력 없음):
- WORKERS: 4 (--workers 4)
- EXPECTED_SECONDS: 49800, ABORT_MULTIPLIER: 2
- MAX_SECONDS: 99600 (--max-seconds. 유효 시간 중단 기준 = EXPECTED_SECONDS × 2). RUNWATCH가 중단을 판단하는 기준이다. 조회·스케줄링·종료 확인 지연 때문에 실제 중단과 기록은 이 시점보다 늦을 수 있다
- ABSOLUTE_CAP_SECONDS: 100800. 감시 도구 시작부터 watch_final 기록까지의 바깥 상한으로, MAX_SECONDS + 종료 확인 + 기록 여유를 포함한다. 넘으면 결과 불명으로 판정한다. 최종 판정용 바깥 상한이며, 이 값으로 프로세스를 종료하는 독립된 OS 강제 종료 장치는 없다
- START_MIN_AVAILABLE_BYTES: 12884901888 (12 GiB)
- ABORT_BELOW_AVAILABLE_BYTES: 6442450944 (6 GiB)
- POLL_SECONDS: 30, VERIFY_SECONDS: 30
- 위 값은 이 Work Order에 고정한다. RESOURCE_BUDGET_APPROVAL과 MAIN_RUN 승인은 이 값과 같아야 한다. 다른 값이 필요하면 실행 전에 계약 정정(ACCEPTED ERRATA)을 받아야 하며, 명령 인자만 바꾸어 실행하지 않는다

## PATHS

PATHS:
- RESEARCH_OUT: data/processed/futval_v8_01/run-155aeef01692-w4-a1 (연구 모듈이 새로 만든다. 미리 있으면 STOP)
- WATCH_DIR: data/processed/runwatch_futval_v8_01_run-a1 (감시 도구가 os.mkdir로 만든다. 부모 data/processed는 이미 있음. 미리 있으면 STOP)
- 두 경로는 서로 상위·하위 관계가 아니다. --forbid-under로 data/processed/futval_v8_01과 RESEARCH_OUT을 모두 지정해, WATCH_DIR이 연구 출력 트리와 같거나 중첩되면 감시 도구가 START_PATH_REJECTED(31)로 거부하게 한다
- 두 경로 모두 .gitignore data/processed/* 범위의 ignored 항목이다. 상위 경로에 reparse 지점·링크가 없어야 한다

## RUN_COMMAND

RUN_COMMAND (RESOURCE_BUDGET 고정값 기준, Bash 백그라운드 1회):
cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m moneylab.runwatch --watch-dir data/processed/runwatch_futval_v8_01_run-a1 --max-seconds 99600 --start-min-available-bytes 12884901888 --abort-below-available-bytes 6442450944 --poll-seconds 30 --verify-seconds 30 --forbid-under data/processed/futval_v8_01 --forbid-under data/processed/futval_v8_01/run-155aeef01692-w4-a1 -- C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe -B -m moneylab.research.v06.futval_v8_01 run --out data/processed/futval_v8_01/run-155aeef01692-w4-a1 --workers 4

- 실행 형태: 감시 도구가 연구 명령을 Job 안에서 실행한다. 연구 stdout·stderr는 WATCH_DIR의 child_stdout.bin·child_stderr.bin에 기록된다
- 이 명령에 없는 기능(메모리 값 위조, 진행률 출력, 재시작 등)은 가정하지 않는다
- 정적 대조 결과 guard ASK는 예상되지 않는다

## PRE_RUN_CHECK

PRE_RUN_CHECK (MAIN_RUN 진입 직후, 목적별 작은 읽기 전용 호출. 하나라도 실패하면 RUN_COMMAND를 실행하지 않고 STOP):
- Git: HEAD = C1, tree, branch = codex/futval-v8-01-run, staged·unstaged·untracked 없음, ignored 집합이 PRESERVED_OUTPUT 기준과 같음
- SOURCE_IDENTITY 전 항목
- PRESERVED_OUTPUT 해시. RESEARCH_OUT과 WATCH_DIR이 없음. 상위 경로가 reparse 지점·링크가 아님
- src·tests 아래 __pycache__·*.pyc 없음
- ENV_PYTHON 버전이 3.14.8이고, os.cpu_count()가 확인됨
- 시스템 가용 RAM(GlobalMemoryStatusEx.ullAvailPhys, 감시 도구와 같은 기준)이 START_MIN_AVAILABLE_BYTES 이상. 시각과 값을 기록한다. 감시 도구는 시작할 때 같은 기준을 다시 검사한다(START_REFUSED 30)
- F0 기준 보존 비교

## WAIT_AND_SESSION

WAIT_AND_SESSION:
- RUN_COMMAND 실행 뒤 에이전트는 완료 알림을 기다린다. 폴링, 반복 조회, 예약 깨우기를 하지 않는다
- 사용자가 진행 상황을 요청하면 WATCH_DIR/watch_state.json을 1회 읽어 elapsed_seconds, available_bytes, job_active_processes, utc만 보고한다
- 에이전트 세션이 끝나거나 끊겨도 계산이 계속된다고 보장하지 않는다. RUNWATCH D3에서 TaskStop 뒤 감시 도구·실행기·Job 안 프로세스가 모두 종료된 것이 관찰됐다. 세션 단절로 백그라운드 작업이 정리되면 KILL_ON_JOB_CLOSE로 연구 계산도 끝날 것으로 예상한다(원인 미입증)
- 장시간 백그라운드 작업의 유지 여부, 시스템 절전·재부팅의 영향은 검증하지 않았다

## OUTCOME_CLASSIFICATION

OUTCOME_CLASSIFICATION (MAIN_RUN 완료 알림 또는 세션 재개 뒤, 파일 근거로 판정):
- RUN_FINISHED_CANDIDATE: watcher 0 COMPLETED, termination VERIFIED, child_exit_code 0, child_stdout이 status COMPLETE·command run 한 줄. watch_final.elapsed_seconds에는 시작 준비·종료 확인·기록 시간이 포함될 수 있으므로 MAX_SECONDS 이하를 요구하지 않는다. 정상 완료 여부는 reason·자식 종료 코드·termination·연구 execution.json 시간·파일 무결성을 함께 판단한다. POST_RUN_INTEGRITY 통과 전에는 완료로 보지 않는다
- RUN_STOPPED: watcher 10(CHILD_EXIT_NONZERO). child_stdout의 STOP code만 보고한다. traceback이 있으면 예외 형식 이름만 보고한다
- RUN_COMPLETED_WITH_LEFTOVER: watcher 11. 연구 자식은 0으로 끝났지만 Job에 남은 프로세스를 종료했다. 이상으로 보고하고, 결과 사용 여부는 사용자가 결정한다
- RUN_ABORTED_BUDGET: watcher 20(ABORT_TIME) 또는 21(ABORT_MEMORY)
- RUN_ABORTED_MONITOR: watcher 22, 23
- RUN_NOT_STARTED: watcher 29–36. 연구 자식이 시작되지 않았거나 시작 직후 종료됐다. 기존 승인은 소진된 것으로 본다
- RUN_TERMINATION_UNVERIFIED: watcher 50, 또는 40(FINAL_WRITE_FAILURE)
- RUN_INTERRUPTED: 완료 알림 없이 세션이 끝났거나, 감시 도구가 watch_final 없이 사라짐
- RUN_RESULT_UNKNOWN: ABSOLUTE_CAP_SECONDS를 넘도록 완료가 확인되지 않거나, 위 분류에 맞지 않음
- 판정은 watcher 코드, child_exit_code, termination, 파일 집합·무결성을 함께 본다. watcher 코드 0만으로 성공으로 보지 않는다

## INTEGRITY_CHECK

INTEGRITY_CHECK (POST_RUN_INTEGRITY, 결과 파일 내용을 열지 않음):
- RESEARCH_OUT 파일 집합이 정확히 manifest.json, design.json, cells.json, summary.json, execution.json, SHA256SUMS 6개이고, 하위 디렉터리와 .part 파일이 없음
- 각 파일의 이름·크기·SHA-256
- SHA256SUMS가 정확히 4줄이고, 형식이 "<64 hex>  <name>"이며, 이름이 manifest·design·cells·summary 순서이고, 각 해시가 실제 파일 해시와 같음. SHA256SUMS 자체와 execution.json은 목록에 없음
- execution.json에서는 status, code, elapsed_seconds, workers 필드만 읽는다. 값은 COMPLETE, NONE, ≤ MAX_SECONDS, 승인 worker 수여야 한다. host·output_dir·os는 보고에 복사하지 않는다. 파일이 없거나 읽을 수 없거나 필드가 없으면 RUN_INTEGRITY_FAIL이다
- WATCH_DIR 파일 집합이 watch_state.json, watch_final.json, child_stdout.bin, child_stderr.bin이다. watch_final의 reason, watcher_exit_code, child_exit_code, termination, started_utc, finished_utc, elapsed_seconds, min_available_bytes, peak_job_commit_bytes를 확인한다. cwd·argv의 절대 경로는 보고에 복사하지 않는다
- watch_final의 started_utc부터 finished_utc까지가 ABSOLUTE_CAP_SECONDS 이하
- 모두 맞으면 RUN_INTEGRITY_PASS. 하나라도 어긋나면 RUN_INTEGRITY_FAIL이며 결과를 사용하지 않는다
- peak_job_commit_bytes는 기록값으로만 보고한다. 값의 의미는 검증하지 않았다

## FAILURE_AND_PARTIAL_OUTPUT

FAILURE_AND_PARTIAL_OUTPUT:
- execution.json: 연구 모듈은 정상적인 예외 처리 경로에서 작성을 시도하지만, 강제 종료·프로세스 장애·쓰기 실패 때는 없거나 불완전할 수 있다. 파일이 없거나 불완전한 것을 정상 완료로 해석하지 않는다
- RUN_FINISHED_CANDIDATE + RUN_INTEGRITY_PASS가 아닌 모든 경우, RESEARCH_OUT과 WATCH_DIR의 현재 상태를 그대로 보존한다. 삭제·이동·수정하지 않는다
- 파일 목록·크기·해시만 기록한다. SHA256SUMS가 없는 RESEARCH_OUT은 사전등록 §9에 따라 미완료이며 사용하지 않는다
- 자동 재실행, 예산을 늘린 재실행, 부분 결과 사용은 없다. 다음 행동(새 study, 새 계약, 새 예산, 새 출력 이름)은 사용자의 새 결정으로만 정한다
- 남은 프로세스가 의심되면 WATCH_DIR 기록의 child_pid와 생성 시각에 근거한 읽기 전용 조회만 할 수 있다. 조회 결과를 근거로 종료하지 않는다

## PRESERVED_OUTPUT

PRESERVED_OUTPUT (이름·SHA-256 불변):
- data/processed/futval_v8_01/precheck-155aeef01692-a1/precheck.json 852b46b441cd34d62fb71a8ba0ed57675c696bb65a6e4538a44e5c5eb66963c5
- data/processed/futval_v8_01/precheck-155aeef01692-a1/execution.json f90539386604f1a48df67f3efd6e6f27fce7dee07c1c147083f0bf2d5ae739f8
- data/processed/futval_v8_01/precheck-155aeef01692-a1/SHA256SUMS 2f882f4ad8fb323df5ea37b3d223e549407ce70a560b14a67ec97607af78fa53
- data/processed/futval_v8_01/smoke-155aeef01692-a1/smoke.json 85858d562939487bf830567763e364e96cd0de66528bdf30f918a40546652dec
- data/processed/futval_v8_01/smoke-155aeef01692-a1/SHA256SUMS ed0f3bd9a18223d548ae23e1fce84e2a0840b8d08b88aa882622a3c2be31ac65
- data/processed/futval_v8_01/perf-155aeef01692-w4-a1/perf.json 41f446ccf58d47a8099303925e4b1310abaf242f16ac09654cbbceb21d4052e2
- data/processed/runwatch_drill/ 파일 21개 (RUNWATCH-01 CLOSEOUT_REPORT 기록)
  - 빈 파일(e3b0c442…) 8개: D1a-a1, D1b-a1, D2-a1, D3-a1 각각의 child_stderr.bin과 child_stdout.bin
  - D1a-a1/watch_final.json e49c3fffb78f45e8431517a7fd89f016a2c2f421af04e775c61101f9885a3a62
  - D1a-a1/watch_state.json c565cdca77a3e34a305c74f972edb15664f1faf749973a86b228041d751da548
  - D1a-ids.json b064f8f7117602d231d52ab42f9277a780ed6ef301232378c9543977741649e3
  - D1b-a1/watch_final.json b5f8702270c8880921c61b9fa6f52d6906f5ab446d8db28c43db474adb8ec203
  - D1b-a1/watch_state.json cb6f27507d173f8f783058b28b643398643b70f6d98de99e96a0bfb4f470e028
  - D1b-ids.json accef5ca3b0fc9555765e7c055b85a82626888e9ad175991e9a99bf6623416e3
  - D2-a1/watch_final.json 7f8ab54a713d82c2ce45e07a6a00ca8aee7bda65b37bb209e7da3cf07d2c7921
  - D2-a1/watch_state.json 572adddb1e4327093b0b616a3f077957d046ddb5da7215e6cf068ad7bc78ba3d
  - D2-ids.json 0ccfb5a02adce693c6fb27bf9f18a93acea825331881abb0ba2f53a1c8d30788
  - D2-sleeper-ids.json a1b42458a6bca794701a5aa5f2f5cef277e6d8236595f1518437455047e26c76
  - D3-a1/watch_state.json 32f762d52ad336462caadb17d0796dec00d50a8a703a8940c74a6daac66e1286
  - D3-ids.json db13a7d5b91a3489222ccdc8f14e90b1cd51a96402a149af964eb9aba1ff0e25
  - D3-watcher-ids.json fc5513af1f29d0b4256e3adf8cfdb0f570ac2a6eb662b773ad411850a7ee547e

## PRESERVATION_CHECK

PRESERVATION_CHECK:
- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): git -C C:/MoneyLab-gov-automation-03 for-each-ref --sort=refname --format="%(refname) %(objectname)", worktree list --porcelain, host rev-parse HEAD HEAD^{tree}와 status --porcelain=v1 --untracked-files=all --ignored=matching 원문 전체를 도구 출력으로 남긴다
- 분류: TASK = refs/heads/codex/futval-v8-01-run(생성 -> C1), OBSERVED = refs/codex/turn-diffs/checkpoints/**, PRESERVE = 그 밖(codex/runwatch-01 = Ce, codex/futval-v8-01-precheck, codex/futval-v8-01-smoke-perf 포함)
- worktree: TARGET_WORKTREE 항목은 통째로 제외하고 항목 단위로 비교한다. TARGET_WORKTREE 항목의 기대 변화는 branch가 runwatch-01에서 futval-v8-01-run으로, HEAD가 C1로 바뀌는 것뿐이다
- 산출물: PRESERVED_OUTPUT 불변. 새 ignored 항목은 RESEARCH_OUT과 WATCH_DIR뿐이다
- 비교 시점: WORKSPACE_SETUP 종료, MAIN_RUN 진입(PRE_RUN_CHECK), POST_RUN_INTEGRITY 종료, CLOSEOUT_REPORT

## EXPECTED_ASK

EXPECTED_ASK(실제 발생은 보장하지 않음):
- WORKSPACE_SETUP: Work Order 최초 생성(task-contract) 최대 1회, git commit 확인 1회
- MAIN_RUN: 없음(정적 대조). RUN_COMMAND나 확인 명령에서 권한 창이 뜨면 예상 밖 ASK로 보고, 진행하지 않고 STOP한다
- POST_RUN_INTEGRITY, CLOSEOUT_REPORT: 없음
- 그 밖의 ASK·거절·무응답·DENY는 STOP

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: 기준·C1 SHA·tree·parent, 소스 blob, 커밋 파일 집합
- CLAUDE_REPORTED: PRE_RUN_CHECK 값(가용 RAM과 시각 포함), RUN_COMMAND 원문, watcher 출력, watch_final 운영 필드, OUTCOME_CLASSIFICATION, INTEGRITY_CHECK, 보존 비교
- INDEPENDENT: 사용자 확인

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, HEAD·parent·tree, 변경 집합, status(ignored 포함)
- 예산 승인 원문과 RUN_COMMAND 인자 대조, 실제 실행 횟수(1 또는 0)
- OUTCOME_CLASSIFICATION, INTEGRITY_CHECK, PRESERVATION_CHECK 분류별 결과
- GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES, <GATE>_PASS, READY_FOR_<NEXT>
- 결과 수치·판정은 보고하지 않는다(결과 열람은 별도 승인)
- 유지할 한계: RUNWATCH D3의 15초·30초 조회 생략(절차 차이), inline-code 승인 창 횟수 미확인, 실제 세션 단절·장시간 내구성·PeakJobMemoryUsed 의미 미검증, 연구 프로세스 최대 메모리 미측정, poll 사이 메모리 급감 미감지 가능성, 장시간 백그라운드 작업 유지와 절전 영향 미검증
- RUNWATCH 검증과 이 실행의 무결성 확인은 연구 결과나 수익성의 증거가 아니다

## STOP_CONDITIONS

STOP_CONDITIONS:
- 기준·HEAD·tree·Work Order sha256 불일치, TARGET_BRANCH·Work Order 경로·RESEARCH_OUT·WATCH_DIR이 미리 있음
- SOURCE_IDENTITY 불일치, 사전등록 해시 불일치, pyc 존재, Python 버전 불일치
- 가용 RAM이 시작 기준 미만, RESOURCE_BUDGET_APPROVAL 없음, 또는 RESOURCE_BUDGET_APPROVAL·MAIN_RUN 승인·RESOURCE_BUDGET 고정값 사이의 값 불일치
- CONTRACT_FILE_EXCEPTION 밖 tracked 변경, PROTECTED 변경, 예상 밖 untracked·ignored
- PRESERVE ref 변화, worktree 항목 불일치, PRESERVED_OUTPUT 변화
- guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- OUTCOME_CLASSIFICATION이 RUN_FINISHED_CANDIDATE가 아닌 경우: 보고하고 멈추며, 재실행하지 않는다
- 사전등록·상위 규칙과 충돌
