# Work Order: FUTVAL-V8-01-SMOKE-PERF — 고정 사전등록 §10 smoke와 성능 측정

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/FUTVAL-V8-01-SMOKE-PERF/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: FUTVAL-V8-01-SMOKE-PERF
TASK_ID: FUTVAL-V8-01-SMOKE-PERF
TITLE: 고정 사전등록 §10의 smoke 1회와 성능 측정 1회
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 905b2c5a8f9a6e0ed0cd59eef18ea61a3ca6ad83
CANONICAL_BASE_TREE: 1d13f8acf4f6ce38ef1b039b5858b99191247a73
CANONICAL_BASE_PARENT: 155aeef016927615bf8449c9cf1060e497d39f56
BASE_REMOTE_REF: NONE (로컬 커밋. fetch하지 않는다)
IMPLEMENTATION_COMMIT: 155aeef016927615bf8449c9cf1060e497d39f56
TARGET_BRANCH: codex/futval-v8-01-smoke-perf
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck (재사용. branch만 전환한다)
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
ENV_PYTHON: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe (기존 환경. 재설치하지 않는다)
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
BUNDLE_ELIGIBLE: NO
PERF_W: 4 (PERF 승인에 W=4를 명시한다. 승인 확인 때와 실행 직전에 os.cpu_count()로 허용 범위 2 이상 os.cpu_count() − 1 이하를 다시 확인한다)
MERGE_METHOD: NOT_APPLICABLE
REQUIRED_CI_CHECKS: NOT_APPLICABLE
PREREGISTRATION_PATH: docs/research_futval_v8_01_preregistration.md
PREREGISTRATION_SHA256: d77549ed4cc732f0b2fb0151fcf17913d319ce8e0de929827fc3a8c9c7ea9b91
PREREGISTRATION_FREEZE_COMMIT: e82ef7e9bdda5026124bc1da93feb4bf0f08aa22
SOURCE_BLOBS: procedures.py = bf6dfddea822f3af0d6e50274c8b3b5b0c767daf, stats.py = 01b6472cadb2ce2437a613b09d419a999398c685, futval_v8_01.py = 462eb3d3a37c4efa9a5eb64443db9245af8a8115, tests/test_futval_v8_01.py = f985319878545ca9d04c7f978162c362270c5564
SOURCE_RAW_W: futval_v8_01.py = 059bc558e54c77a29d1bf00b0d7c9eb711cf8201ec4fc1f66da47cc5989d1106, tests/test_futval_v8_01.py = 9e9fc92b6711a9edfa868eb4c42e7eab769b27f0f3a21aaebaa04cb408558ca8
SOURCE_LF_S: futval_v8_01.py = 113bd27b1a5df307e5007db56740c6ad95da70070407efb6adc91344ff1bb79c, tests/test_futval_v8_01.py = 5ba57dd0c715967bfa3fe936be53b1b5fb803e440d7746f19e23e399d96b727f
PRESERVED_OUTPUT: data/processed/futval_v8_01/precheck-155aeef01692-a1/ (precheck.json 852b46b441cd34d62fb71a8ba0ed57675c696bb65a6e4538a44e5c5eb66963c5, execution.json f90539386604f1a48df67f3efd6e6f27fce7dee07c1c147083f0bf2d5ae739f8, SHA256SUMS 2f882f4ad8fb323df5ea37b3d223e549407ce70a560b14a67ec97607af78fa53)
RELATED_TASKS: FUTVAL-V8-01(PREREGISTRATION_FREEZE_PASS 보류, ref 보존 미확정), FUTVAL-V8-01-IMPL(TASK_COMPLETE NOT_DECLARED), FUTVAL-V8-01-PRECHECK(CLOSEOUT_REPORT_PASS, TASK_COMPLETE NOT_DECLARED). 이 Work Order는 그 판정·보류·사건 기록을 바꾸지 않는다. FREEZE_PASS 보류는 사전등록 효력 조건(고정 커밋 완료)과 별개이며 이 Work Order의 진입 조건이 아니다.

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> SMOKE -> PERF -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

- 각 gate는 GATE_AUTHORIZATION 1건으로만 시작하고 보고 후 멈춘다. 묶음과 DELEGATE는 쓰지 않는다.
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: FUTVAL-V8-01-SMOKE-PERF WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - SMOKE: GATE_AUTHORIZATION: FUTVAL-V8-01-SMOKE-PERF SMOKE WO@<C1 SHA> OUT=<smoke 디렉터리>
  - PERF: GATE_AUTHORIZATION: FUTVAL-V8-01-SMOKE-PERF PERF WO@<C1 SHA> W=4 OUT=<perf 디렉터리>
  - CLOSEOUT_REPORT: GATE_AUTHORIZATION: FUTVAL-V8-01-SMOKE-PERF CLOSEOUT_REPORT WO@<C1 SHA>
- 상태 변경 명령은 각각 별도 도구 호출로 실행하고 결과를 확인한 뒤 다음으로 간다. 실행 명령 뒤에 파이프·자르기·리디렉션·다른 명령을 붙이지 않는다.
- STOP 뒤에는 후속 명령을 실행하지 않는다. 재실행은 새 승인과 새 디렉터리(a<N+1>)로만 한다.
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다.

## ABSOLUTE_RULES

저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)과 고정 사전등록이 이 Work Order보다 우선한다. 충돌하면 STOP한다. 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

고정 사전등록 §10의 smoke(FUTVAL-V8-01-TEST, B 9999, 12셀 × rep 0..1)를 1회, 성능 측정(FUTVAL-V8-01-PERF, B 9999, θ 0.5, n 4개 × rep 0..19, M1 worker 1과 M2 worker W)을 1회 기존 C2 구현으로 실행하고, 결과값이 없는 산출물의 구조·시간·자원만 보고한다.

## ALLOWED_ACTIONS

- WORKSPACE_SETUP
  - F0 출력(PRESERVATION_CHECK)
  - 기준 확인(HEAD = CANONICAL_BASE_SHA, clean, 계약·소스·PRESERVED_OUTPUT 해시)
  - git -C C:/MoneyLab-futval-v8-01-precheck switch -c codex/futval-v8-01-smoke-perf 1회(작업 파일 불변. 대상 worktree의 branch만 바뀌고 HEAD는 Ce 그대로다)
  - docs/tasks/FUTVAL-V8-01-SMOKE-PERF/WORK_ORDER.md Write 1회, git -C C:/MoneyLab-futval-v8-01-precheck add -- <그 경로> 1회, C1 커밋 1회(메시지 docs(task): add FUTVAL-V8-01-SMOKE-PERF work order, 본문·trailer 없음)
  - 종료 시 PRESERVATION_CHECK 비교(F0 대비)
- SMOKE
  - ENTRY_CHECK, SMOKE_COMMAND 1회(백그라운드 실행, 완료 알림 대기, 폴링 없음)
  - 산출 파일 이름·크기·SHA-256 확인, SHA256SUMS 대조, smoke.json 1회 열람과 스키마·허용 필드·구조 검사 확인
- PERF
  - ENTRY_CHECK, os.cpu_count() 확인, PERF_COMMAND 1회(백그라운드 실행, 완료 알림 대기, 폴링 없음)
  - perf.json 1회 열람과 허용 필드 확인, 시간·자원 보고
- CLOSEOUT_REPORT: PRESERVATION_CHECK 비교와 종결 보고

## FORBIDDEN_ACTIONS

- 소스·테스트·계약·사전등록 변경, 구현 변경. 단 이 Work Order 파일의 WORKSPACE_SETUP 최초 생성(CONTRACT_FILE_EXCEPTION) 1회만 예외이며, 기존 계약 파일은 변경하지 않는다
- 본 실행(run), 운영 이름공간 FUTVAL-V8-01의 데이터 생성, 연구 결과 열람, 자원 예산 승인
- smoke·성능 측정의 규모·반복·W를 바꾼 재실행, 성능 측정 반복
- smoke·perf 산출물에 결과값(p, 기각 지시변수, 기각률, K, D, 판정, 이를 복원할 집계)이 있을 때 그 값의 출력·전달
- 설치, 네트워크, fetch, push, PR, merge, 테스트 재실행
- git add . / -A, --no-verify, amend, reset, restore, stash, clean, rebase, branch 삭제
- 출력 폐기·리디렉션·tee, 임시 스크립트 파일
- 기존 산출물(PRESERVED_OUTPUT 포함), 다른 branch·worktree, untracked·ignored 항목의 변경·정리
- hooks·settings·.claude·.github·pyproject.toml·requirements*.txt·.gitignore 변경, guard 우회

## ALLOWED_FILES

ALLOWED_FILES: NONE (구현 변경 없음)

## CONTRACT_FILE_EXCEPTION

- A docs/tasks/FUTVAL-V8-01-SMOKE-PERF/WORK_ORDER.md (WORKSPACE_SETUP 전용, 승인 바이트로 최초 1회)

## PROTECTED_FILES

- docs/tasks/FUTVAL-V8-01-SMOKE-PERF/** (WORKSPACE_SETUP의 이 Work Order 파일 최초 생성 1회만 제외), docs/tasks/FUTVAL-V8-01/**, docs/tasks/FUTVAL-V8-01-IMPL/**, docs/tasks/FUTVAL-V8-01-PRECHECK/**, docs/research_futval_v8_01_preregistration.md
- CONTRACT_FILE_EXCEPTION 밖의 모든 저장소 파일

## COMMIT_PLAN

- C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/FUTVAL-V8-01-SMOKE-PERF/WORK_ORDER.md. 이 Work Order의 커밋은 C1 하나뿐이다.
- 구현 식별 커밋은 IMPLEMENTATION_COMMIT(C2)이고, 실행 기준 HEAD는 C1이다. 보고에서 둘을 구분한다.

## ENTRY_CHECK (SMOKE·PERF 각각 실행 직전)

- branch = TARGET_BRANCH, HEAD = C1, parent(C1) = CANONICAL_BASE_SHA, CANONICAL_BASE_SHA..C1 변경은 A WORK_ORDER.md 하나
- tracked·index 변경 없음, untracked 없음. ignored는 .venv/, src/moneylab.egg-info/, data/processed/futval_v8_01/ 와 이전 gate 승인 산출물뿐
- 계약 blob 내용: 이 Work Order(C1 승인값), PREREGISTRATION_SHA256
- SOURCE_BLOBS가 HEAD에서 같다. 두 파일의 raw W가 SOURCE_RAW_W와 같고, 단독 CR이 없으며, CRLF만 LF로 바꾼 바이트(메모리 계산)가 SOURCE_LF_S와 같다. 작업 파일을 다시 쓰지 않는다
- procedures.py·stats.py의 LF 정규화 작업본 blob ID가 SOURCE_BLOBS와 같다
- PRESERVED_OUTPUT 세 파일의 SHA-256 불변, 이전 gate 산출물 불변
- 출력 디렉터리가 없고 git check-ignore로 ignored다
- 하나라도 다르면 실행하지 않고 STOP한다

## SMOKE

- OUT: data/processed/futval_v8_01/smoke-155aeef01692-a1
- SMOKE_COMMAND: cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m moneylab.research.v06.futval_v8_01 smoke --out data/processed/futval_v8_01/smoke-155aeef01692-a1
- 시간 상한: 1800초. 계약의 STOP 기준이며 완료 시간의 보장이 아니다. 백그라운드 실행과 완료 알림으로 기다리며 폴링·출력 자르기를 하지 않는다. 상한을 넘으면 STOP하고, 종료를 확인하지 못하면 결과 불명으로 보고한다
- 완료 조건: exit 0, stdout 한 줄 {"command": "smoke", "status": "COMPLETE"}, 디렉터리에 smoke.json과 SHA256SUMS 두 파일뿐, SHA256SUMS가 smoke.json 하나의 해시만 담고 실제와 같음
- smoke.json 확인: schema moneylab.futval_v8_01.smoke/1, study FUTVAL-V8-01, namespace FUTVAL-V8-01-TEST, 키 집합이 {schema, study, namespace, cells, all_structure_ok}, 12셀이 고정 순서이고 각 행 키가 {n, theta, completed, structure_ok}, completed = 2, structure_ok·all_structure_ok가 true
- 허용 필드 밖 키나 결과값이 있으면 그 값을 출력하지 않고 STOP한다. 산출물은 수정·삭제하지 않는다
- 실패 시 산출물을 삭제·덮어쓰기·복구하지 않고 보고한다

## PERF

- 진입: SMOKE 완료 조건 충족, ENTRY_CHECK, os.cpu_count()가 정수이고 3 이상, 승인된 W가 PERF_W(4)와 같고 2 이상 os.cpu_count() − 1 이하. 아니면 실행하지 않고 STOP한다
- OUT: data/processed/futval_v8_01/perf-155aeef01692-w4-a1
- PERF_COMMAND: cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m moneylab.research.v06.futval_v8_01 perf --out data/processed/futval_v8_01/perf-155aeef01692-w4-a1 --workers 4
- 시간 상한: 3600초. 계약의 STOP 기준이며 완료 시간의 보장이 아니다. 백그라운드 실행과 완료 알림으로 기다리며 폴링·출력 자르기를 하지 않는다. 상한을 넘으면 STOP하고, 종료를 확인하지 못하면 결과 불명으로 보고한다
- 완료 조건: exit 0, stdout 한 줄 {"command": "perf", "status": "COMPLETE"}, 디렉터리에 perf.json 하나뿐
- perf.json 확인: schema moneylab.futval_v8_01.perf/1, namespace FUTVAL-V8-01-PERF, 키 집합이 {schema, study, namespace, measures, per_rep_wall_seconds_mean_by_n, W, parallel_efficiency}, measures가 M1(worker 1)과 M2(worker W), n 키가 4개, W가 승인값과 같음
- 허용 필드 밖 키나 결과값(p, 기각 지시변수, 기각률, K, D, 판정)이 있으면 그 값을 출력하지 않고 STOP한다. 산출물은 수정·삭제하지 않는다
- 보고: M1·M2의 wall_seconds, cpu_seconds_sum, max_memory_bytes, M1의 n별 복제당 평균 wall, η. 이 값은 자원 예산 판단 자료이며 자원 예산 승인이 아니다
- 측정 의미(C2 구현 기준)
  - wall_seconds: 측정별 작업 실행 호출 전후의 perf_counter 차이다. M2는 worker 프로세스 생성·종료와 작업 전달 비용을 포함한다
  - cpu_seconds_sum: 작업 단위마다 그 작업을 수행한 프로세스 안에서 잰 process_time 차이의 합이다. 프로세스 생성, 모듈 import, 작업 전달, 상위 프로세스의 대기·집계 비용은 포함하지 않는다
  - max_memory_bytes: 작업 단위를 끝낸 시점의 수행 프로세스 최대 메모리(Windows는 PeakWorkingSetSize, 그 밖의 OS는 ru_maxrss)와 측정 직후 상위 프로세스의 같은 값 가운데 최대값이다. 여러 프로세스의 동시 총 메모리가 아니다. M1은 상위 프로세스 안에서 실행되며, 상위 프로세스 값은 시작 이후 누적 최대이므로 M2 값에 M1 동안의 최대가 반영될 수 있다. 측정할 수 없는 값은 빼고, 모두 측정할 수 없으면 null이다
  - per_rep_wall_seconds_mean_by_n: M1에서만 수집한 복제별 wall(데이터 생성과 V0 통계 계산)의 n별 평균이다
  - η = T_M1/(W·T_M2)
  - 작업 분할: 작업 단위 크기는 250복제이고 n마다 rep 0..19가 한 단위이므로 성능 측정 작업 단위는 4개다. M2에서 동시에 작업하는 worker는 최대 4개이며 W = 4와 같다. η는 측정된 T_M1/(4·T_M2)이며 n별 작업 크기 불균형과 프로세스 생성·작업 전달 비용의 영향을 받는다. 이 η를 본 실행(셀마다 작업 단위 40개)의 병렬 효율로 그대로 일반화하지 않는다
  - 이 값들만으로 본 실행의 총 메모리나 완료 시간을 보장하지 않는다
- 실행 뒤 src·tests 아래 __pycache__·.pyc가 없음을 확인한다
- 실패 시 산출물을 삭제·덮어쓰기·복구하지 않고, 재시도·W 변경 없이 STOP한다

## PRESERVATION_CHECK

- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): git -C C:/MoneyLab-gov-automation-03 for-each-ref --sort=refname --format="%(refname) %(objectname)", worktree list --porcelain, host rev-parse HEAD HEAD^{tree}와 status --porcelain=v1 --untracked-files=all --ignored=matching의 원문 전체를 도구 출력으로 남긴다
- 분류
  - TASK: refs/heads/codex/futval-v8-01-smoke-perf. 기대 변화는 생성(Ce) -> C1뿐
  - OBSERVED: refs/codex/turn-diffs/checkpoints/** 만. 이름·값 차이를 기록하고 변경 주체를 단정하지 않는다. STOP 사유가 아니다
  - PRESERVE: 그 밖의 모든 ref. refs/heads/codex/futval-v8-01-precheck(= Ce)를 포함한다. 하나라도 변하면 STOP한다
- worktree: TARGET_WORKTREE 항목 하나를 통째로 제외하고 경로 순으로 항목 단위 비교한다. TARGET_WORKTREE 항목의 기대 변화는 branch가 refs/heads/codex/futval-v8-01-precheck에서 refs/heads/codex/futval-v8-01-smoke-perf로, HEAD가 Ce에서 C1로 바뀌는 것뿐이며 따로 확인한다. refs/heads/codex/futval-v8-01-precheck는 Ce에 보존한다
- 산출물: 승인된 smoke·perf 디렉터리 생성만 기대 변화이고, PRESERVED_OUTPUT과 이전 gate 산출물은 해시가 같아야 한다
- 비교 시점: WORKSPACE_SETUP 종료, SMOKE 종료, PERF 종료, CLOSEOUT_REPORT

## EXPECTED_ASK

- WORKSPACE_SETUP: Work Order 최초 생성(Write)에 대한 task-contract 확인 1회, 커밋 확인(git-commit 규칙) 1회
- SMOKE, PERF, CLOSEOUT_REPORT: 없음
- 위 확인 창이 실제로 뜨는지는 보장하지 않는다. 그 밖의 ASK, 거절, 무응답, DENY는 STOP이다

## REQUIRED_EVIDENCE

- GIT_VERIFIABLE: 기준·C1 SHA·tree·parent, 계약·소스 blob, 커밋 파일 집합
- CLAUDE_REPORTED: ENTRY_CHECK, 실행 종료 코드·stdout·경과 시간, 산출물 이름·크기·SHA-256, smoke 구조 확인, perf 시간·자원 값, 보존 비교
- INDEPENDENT: 사용자 확인

## REQUIRED_REPORT

- TASK_ID, GATE, WORK_ORDER_COMMIT(C1), IMPLEMENTATION_COMMIT(C2), HEAD·tree, status(ignored 포함), 소스 raw W·LF S
- 산출물 경로·파일·SHA-256
- PRESERVATION_CHECK 분류별 결과
- GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES, <GATE>_PASS, READY_FOR_<NEXT>
- 유지할 한계: smoke·perf 산출물에는 코드 식별값이 없고 진입 시 git 확인으로만 연결된다. perf 값은 한 번의 측정이며 일반화된 성능 보장이 아니다. 물리 코어 수는 확인하지 않았다

## STOP_CONDITIONS

- 기준·C1·계약·소스·raw W·LF S·PRESERVED_OUTPUT 불일치, TARGET_BRANCH가 미리 있음, 출력 디렉터리가 미리 있음
- 예상 밖 tracked·untracked·ignored 변화, PRESERVE ref 변화, worktree 항목 불일치
- W 누락·범위 밖, os.cpu_count()가 None이거나 3 미만
- 실행 실패, 시간 상한 초과, 산출물 파일 집합·스키마·허용 필드 불일치, 결과값 발견
- guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- 사전등록과 구현의 모순, 상위 규칙 충돌
