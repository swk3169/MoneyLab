# Work Order: RUNWATCH-01 — 연구 실행 감시 도구(Windows Job Object) 구현과 합성 검증

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/RUNWATCH-01/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: RUNWATCH-01
TASK_ID: RUNWATCH-01
TITLE: 연구 코드와 분리된 실행 감시·중단 도구 구현과 합성 작업 검증
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: dedfafb16c3dd08cad5da3e26530b716c2edc51f
CANONICAL_BASE_TREE: b4ee40be8ea154b6155c554bdf970173ab794927
CANONICAL_BASE_PARENT: 905b2c5a8f9a6e0ed0cd59eef18ea61a3ca6ad83
BASE_REMOTE_REF: NONE (로컬 커밋. fetch하지 않는다)
TARGET_BRANCH: codex/runwatch-01
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck (재사용. 현재 branch codex/futval-v8-01-smoke-perf에서 branch만 전환한다)
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
ENV_PYTHON: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe (editable 설치. 재설치하지 않는다)
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE (PUSH·PR_CI·MERGE gate 없음)
REQUIRED_CI_CHECKS: NOT_APPLICABLE
BUNDLE_ELIGIBLE: YES
BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E
RELATED_TASKS: FUTVAL-V8-01, -IMPL, -PRECHECK, -SMOKE-PERF(판정·보류·사건·ISSUE 불변), FUTVAL-V8-01-RUN 초안(보류, 발행하지 않음)
PRESERVED_OUTPUT: data/processed/futval_v8_01/ 아래 기존 파일 6개(precheck 3, smoke 2, perf 1)의 이름·SHA-256 불변

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> SYNTHETIC_DRILL -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- WORKSPACE_SETUP: GATE_AUTHORIZATION: RUNWATCH-01 WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
- IMPLEMENTATION..CLEAN_COMMIT_E2E: docs/tasks/README.md §14 BUNDLE_AUTHORIZATION(BGA-2 키 전부) 1건 또는 gate별 GATE_AUTHORIZATION
- SYNTHETIC_DRILL, CLOSEOUT_REPORT: 각각 GATE_AUTHORIZATION: RUNWATCH-01 <GATE> WO@<C1 SHA> (묶음 밖)
- 상태 변경은 각각 별도 도구 호출로 실행하고 결과를 확인한 뒤 다음으로 간다. 검사·실행 명령 뒤에 파이프·자르기·리디렉션·다른 명령을 붙이지 않는다
- COMMIT 뒤 수정은 STOP하고 사용자 결정을 받는다. amend 금지
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)과 고정 사전등록이 우선한다. 복제하지 않고 바꾸지 않는다. 충돌하면 STOP한다. 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: 장시간 연구 명령을 Windows Job Object 안에서 실행하고, 시간 상한·가용 RAM 기준·감시 실패 때 Job 전체를 종료하며, 종료와 잔존 여부를 확인하고 운영 정보만 기록하는 moneylab.runwatch를 구현한다. 연구 코드와 분리하며, 연구 실행·자원 예산·본 실행은 범위 밖이다.

## BACKGROUND

BACKGROUND:
- automation/executor.py와 workstate/collect.py는 직계 프로세스만 종료하고 장시간·메모리·트리 종료를 다루지 않는다
- research/v06/futility_diag.py 3030–3140행에 argtypes·restype·구조체 크기 검사를 갖춘 Job Object 패턴이 있다. 보호 대상 연구 모듈이므로 import하지 않고 새 모듈에서 독립 구현한다
- FUTVAL-V8-01-SMOKE-PERF에서 연구 프로세스 최대 메모리가 null(미측정)이었다. 원인은 미확정이다
- 세션 단절 뒤 실행을 계속하는 기능은 범위가 아니다. 세션이 끝나 실행이 함께 끝나더라도 감시되지 않는 자식이 남지 않는 것이 필수다

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 출력(PRESERVATION_CHECK), 기준 확인(HEAD·tree·branch·clean, 계약·소스·PRESERVED_OUTPUT 해시), 새 branch와 Work Order 경로 부재 확인
  - git -C C:/MoneyLab-futval-v8-01-precheck switch -c codex/runwatch-01 1회
  - docs/tasks/RUNWATCH-01/WORK_ORDER.md Write 1회(승인 바이트), git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/RUNWATCH-01/WORK_ORDER.md 1회, C1 커밋 1회(메시지 docs(task): add RUNWATCH-01 work order, 본문·trailer 없음)
  - 종료 시 PRESERVATION_CHECK 비교
  - C1 생성 직후, 구현 파일 생성 전에 COLLECT_COMMAND 1회(BASELINE_COLLECT. 수집 ID 원문을 도구 출력에 남긴다)
- IMPLEMENTATION: ALLOWED_FILES 생성·수정, CHECK_1·CHECK_2·CHECK_3A·CHECK_3B 순차 실행, 모두 통과 뒤 CHECK_4. BGA-4 수정 반복
- PRECOMMIT_AUDIT: 읽기, git diff --check, COLLECT_COMMAND 1회, BGA-8 확인
- COMMIT: ALLOWED_FILES만 경로 지정 stage, git diff --cached --check, C2 커밋 1회(메시지 feat(runwatch): add job-object run watcher, 본문·trailer 없음)
- CLEAN_COMMIT_E2E: HEAD = C2 clean에서 CHECK_1 1회와 상태·바이트 재확인
- SYNTHETIC_DRILL: SYNTHETIC_DRILL 절에 고정한 실행(감시 도구 4회, Job 밖 sleeper 1회)
- CLOSEOUT_REPORT: PRESERVATION_CHECK 비교와 종결 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위, ALLOWED_FILES·CONTRACT_FILE_EXCEPTION 밖 tracked 변경, PROTECTED_FILES 변경
- 사전등록·Work Order·ERRATA 수정
- 운영 smoke·perf·run, FUTVAL-V8-01 이름공간 실행, 연구 결과 열람, 연구 산출물 내용 열람
- 감시 도구 시험에서 연구 모듈 import·실행
- 실제 시스템 메모리 부하·고갈 시험, 실제 가용 RAM 변화를 강제로 만드는 시험
- 운영 CLI에 시험용 메모리 값 위조 옵션 추가
- Job 밖 프로세스 조작, 이름·경로·PID 검색 기반 종료. 단 TEST_GATES의 CLEANUP_EXCEPTION 범위(시험이 직접 생성하고 핸들을 보유한 프로세스)는 예외이며, 기존·무관 프로세스 조작은 계속 금지한다
- breakaway 사용, 작업 스케줄러 등록, 서비스 등록, 권한 규칙·guard·hook·settings 변경
- 설치, 네트워크, fetch, push, PR, merge
- git add . / -A, --no-verify, amend, reset, restore, stash, clean, rebase, cherry-pick
- 셸 출력 폐기·리디렉션·tee, 임시 스크립트 파일(감시 도구가 직접 만드는 CHILD_OUTPUT 예외는 DESIGN_CONTRACT D7)
- 기존 산출물·다른 branch·worktree·untracked·ignored 항목의 변경·정리

## ALLOWED_FILES

ALLOWED_FILES:
- A src/moneylab/runwatch/__init__.py
- A src/moneylab/runwatch/__main__.py
- A src/moneylab/runwatch/winjob.py
- A src/moneylab/runwatch/watch.py
- A tests/test_runwatch.py

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/RUNWATCH-01/WORK_ORDER.md (WORKSPACE_SETUP 전용, 승인 바이트로 최초 1회)

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/RUNWATCH-01/** (CONTRACT_FILE_EXCEPTION 최초 생성 1회 제외), docs/tasks/FUTVAL-V8-01*/**, docs/research_*_preregistration*.md
- src/moneylab/research/**, src/moneylab/storage/**, src/moneylab/core/**, src/moneylab/automation/**, 그 밖의 src/**(ALLOWED_FILES 제외), tests/**(tests/test_runwatch.py 제외)
- pyproject.toml, requirements*.txt, .gitignore, .gitattributes, CLAUDE.md, .claude/**, .github/**, configs/**, docs/**(위 예외 제외)
- data/** 기존 산출물

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## COMMIT_PLAN

COMMIT_PLAN:
- C1: parent = CANONICAL_BASE_SHA, 변경 = CONTRACT_FILE_EXCEPTION의 Work Order 파일 하나(A). 메시지 docs(task): add RUNWATCH-01 work order, 본문·trailer 없음
- C2: parent = C1, 변경 = ALLOWED_FILES 5개(모두 A)뿐. 메시지 feat(runwatch): add job-object run watcher, 본문·trailer 없음
- CANONICAL_BASE_SHA..C2 변경 경로는 위 6개뿐이다. 이 Work Order의 커밋은 C1과 C2 둘뿐이다

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 CLI: python -m moneylab.runwatch --watch-dir <dir> --max-seconds <int> --start-min-available-bytes <int> --abort-below-available-bytes <int> --poll-seconds <int> --verify-seconds <int> [--forbid-under <dir>]... -- <argv...>. shell=False. argv[0]은 절대 경로 또는 작업 디렉터리 기준 상대 경로. 인자 이름에 guard 규칙 단어(record, research-final 등)를 쓰지 않는다. 시험용 메모리 값 위조 옵션을 두지 않는다. 비Windows는 시작 전 UNSUPPORTED_PLATFORM으로 끝낸다. 인자 검증: max-seconds·poll-seconds·verify-seconds는 양의 정수, 두 메모리 기준은 0 이상의 정수, start 기준 ≥ abort 기준. 위반하면 watch-dir과 자식을 만들지 않고 ARGUMENT_REJECTED
- D2 Win32 선언: kernel32·psapi 함수는 모두 argtypes·restype을 지정하고 GetLastError는 use_last_error로 읽는다. 구조체(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, JOBOBJECT_EXTENDED_LIMIT_INFORMATION, MEMORYSTATUSEX, STARTUPINFOEXW, PROCESS_INFORMATION) 크기를 x64 값과 대조해 다르면 시작 전 STOP
- D3 핸들 소유권과 닫는 순서
  - 감시 도구가 소유한다: Job 핸들(J), 자식 프로세스 핸들(P), 자식 주 스레드 핸들(T), NUL 입력(I)·stdout 파일(O)·stderr 파일(E) 핸들, 속성 목록
  - J는 lpJobAttributes = NULL(비상속)로 만들고 복제·전달하지 않는다. JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE를 설정하고 breakaway 플래그는 설정하지 않는다
  - I·O·E만 상속 가능으로 만들고 PROC_THREAD_ATTRIBUTE_HANDLE_LIST로 상속 대상을 이 셋으로 제한한다
  - 닫는 순서: 자식 생성 직후 성공·실패와 무관하게 I·O·E와 속성 목록 정리 → 재개 뒤 T → 종료 확인 뒤 P → 최종 기록 뒤 마지막으로 J. J를 닫으면 OS가 남은 Job 구성원을 종료한다(KILL_ON_JOB_CLOSE)
- D4 시작 순서와 실패 지점별 정리
  - S0 watch-dir 검증·생성(D8), 가용 RAM < start 기준이면 START_REFUSED(자식 생성 없음)
  - S1 J 생성·제한 설정 실패 → JOB_SETUP_FAILED(자식 생성 없음)
  - S2 CreateProcessW(CREATE_SUSPENDED | EXTENDED_STARTUPINFO_PRESENT | CREATE_NO_WINDOW) 실패 → CHILD_START_FAILED
  - S3 AssignProcessToJobObject(J, P) 실패 → P로 TerminateProcess, verify-seconds 안에 P signaled 확인, ASSIGN_FAILED(확인 실패 시 UNVERIFIED 덧붙임)
  - S4 IsProcessInJob(P, J) 거짓·실패 → S3과 같은 정리, ASSIGN_UNCONFIRMED
  - S5 ResumeThread(T) 실패 → TerminateJobObject(J) 뒤 종료 확인(D6), RESUME_FAILED
  - 모든 실패 경로는 재시도하지 않는다
- D5 감시 루프: poll-seconds마다 경과(monotonic), 가용 RAM(GlobalMemoryStatusEx.ullAvailPhys), Job 활성 프로세스 수(BasicAccounting), PeakJobMemoryUsed(ExtendedLimit)를 읽어 watch_state.json을 atomic 갱신. 판정 순서
  - 루트 자식 종료 → D6 정상 종료 경로
  - 경과 ≥ max → ABORT_TIME
  - 가용 RAM < abort 기준 → ABORT_MEMORY
  - 어떤 조회 예외 → ABORT_MONITOR_FAILURE
  - watch_state.json 쓰기 실패 → ABORT_STATE_WRITE_FAILURE(감시 기록 없이 자식이 계속 실행되지 않게 한다)
  - 모든 ABORT는 TerminateJobObject(J) 뒤 D6 종료 확인
  - 감시 루프의 처리되지 않은 예외는 finally에서 TerminateJobObject(J)와 D6를 시도한 뒤 INTERNAL_ERROR로 끝낸다
- D6 종료 확인: verify-seconds 상한 안에서 P signaled와 Job 활성 프로세스 0을 확인하면 TERMINATION_VERIFIED, 아니면 TERMINATION_UNVERIFIED. UNVERIFIED는 어떤 경우에도 정상 완료로 판정하지 않는다
- D7 자식 입출력(CHILD_OUTPUT 예외)
  - stdin은 NUL, stdout·stderr는 watch-dir 안 child_stdout.bin·child_stderr.bin을 배타 생성(CREATE_NEW)해 핸들로 직접 넘긴다. 파이프를 쓰지 않으므로 막힘이 없다
  - 이 두 파일은 감시 도구가 직접 관리하는 운영 기록이며 셸 리디렉션·tee·출력 폐기에 해당하지 않는다. 내용을 자르거나 지우지 않고 보존한다
  - 연구 명령의 stdout·stderr에 연구 결과값이 없다는 것은 감시 도구가 보장하지 않는다. 보고에서는 이 파일 이름·크기·SHA-256만 다루고 내용 열람은 해당 실행 계약이 정한다
- D8 경로 규칙
  - watch-dir은 존재하지 않아야 하며 os.mkdir로 배타 생성한다. 이미 있으면 START_PATH_REJECTED(내용 변경 없음)
  - watch-dir의 부모부터 작업 디렉터리 루트까지 각 경로 요소가 재분석 지점(FILE_ATTRIBUTE_REPARSE_POINT)이나 링크이면 거부한다. 검사와 사용 사이의 경쟁을 완전히 막는다고 주장하지 않는다
  - --forbid-under 경로와 같거나 그 안이거나 그것을 포함하는 watch-dir은 거부한다(연구 출력 디렉터리 중첩 금지). --forbid-under로 전달된 경로만 검사하며, 자식 argv에서 연구 출력 경로를 자동으로 찾아내지 않는다
  - 성공 후 남는 영구 파일은 watch_state.json, watch_final.json, child_stdout.bin, child_stderr.bin 네 개뿐이다. storage.atomic이 같은 디렉터리에 만드는 임시 파일의 생성·교체는 허용된 내부 동작이며, 실패로 남은 임시 파일은 지우지 않고 보존·보고한다. watch_final.json과 두 출력 파일은 배타 생성, watch_state.json은 storage.atomic.atomic_write_bytes로 자기 파일만 교체한다
- D9 최종 기록: 종료 확인 뒤 watch_final.json을 storage.atomic.atomic_create_new_bytes로 1회 쓴다. 쓰기 실패 시 FINAL_WRITE_FAILURE 종료 코드를 우선하고, stderr에 사유 코드 한 줄만 쓴다. 이때 Job은 이미 종료·확인된 상태여야 한다
- D10 종료 사유와 감시 도구 종료 코드(자식 종료 코드와 구분해 기록)
  - 0 COMPLETED(루트 자식 0, 잔존 없음, VERIFIED)
  - 10 CHILD_EXIT_NONZERO(루트 자식 비0. 잔존이 있으면 Job 종료·확인 뒤)
  - 11 COMPLETED_WITH_LEFTOVER(루트 자식 0, 잔존을 Job 종료로 정리)
  - 20 ABORT_TIME, 21 ABORT_MEMORY, 22 ABORT_MONITOR_FAILURE, 23 ABORT_STATE_WRITE_FAILURE
  - 29 ARGUMENT_REJECTED, 30 START_REFUSED, 31 START_PATH_REJECTED, 32 JOB_SETUP_FAILED, 33 CHILD_START_FAILED, 34 ASSIGN_FAILED, 35 ASSIGN_UNCONFIRMED, 36 RESUME_FAILED
  - 40 FINAL_WRITE_FAILURE, 50 TERMINATION_UNVERIFIED(다른 코드보다 우선), 60 UNSUPPORTED_PLATFORM, 70 INTERNAL_ERROR
- D11 기록 범위와 비밀정보: watch 파일에는 UTC 시각, 경과, 가용 RAM, Job 활성 수, PeakJobMemoryUsed, 최소 가용 RAM, 루트 자식 PID·종료 코드, 사유, 종료 확인, core.redaction.redact_text를 거친 argv, 작업 디렉터리만 넣는다. 환경 변수는 기록하지 않는다. 채팅 보고에는 절대 경로·호스트를 넣지 않는다
- D12 종료 대상 식별: 종료는 J(TerminateJobObject)와 감시 도구가 직접 만든 P(TerminateProcess, S3·S4)로만 한다. 프로세스 이름·venv 경로·PID 검색으로 종료하지 않는다
- D13 한계: 감시 주기는 즉시 강제가 아니다. 샘플 사이의 급격한 가용 RAM 감소와 OS 종료 지연을 막지 못한다. ABORT_MEMORY 분기는 조회 함수 주입 단위 시험으로만 검증되며, 실제 가용 RAM 기준 미달 상황에서의 동작은 검증하지 않는다. PeakJobMemoryUsed는 commit 기준이며 working set이 아니고, 실제 의미는 SYNTHETIC_DRILL 범위에서만 확인된다. 세션 단절 뒤 실행 지속은 보장하지 않는다. 장시간 내구성은 짧은 시험으로 입증하지 않는다

## TEST_GATES

TEST_GATES:
- tests/test_runwatch.py는 합성 작업만 쓴다(짧은 합성 Python 코드, 연구 모듈 import 금지). 합성 프로세스는 자기 수명 상한(실행이 시작된 경우 최대 60초 뒤 스스로 종료)을 가진다
- 단위 시험(winjob 조작·시계·메모리·기록을 주입한 가짜로)
  - 판정 순서, ABORT_TIME, ABORT_MONITOR_FAILURE, ABORT_STATE_WRITE_FAILURE, FINAL_WRITE_FAILURE, ASSIGN_FAILED·ASSIGN_UNCONFIRMED·RESUME_FAILED 정리 경로, 종료 확인 시간 초과 → UNVERIFIED와 코드 50, CHILD_EXIT_NONZERO와 잔존 처리, ARGUMENT_REJECTED(인자 검증 각 조건), D8 경로 거부(기존 존재, 링크·재분석 지점 흉내, forbid-under 중첩), redaction 적용, 종료 코드 표
  - ABORT_MEMORY: 가용 RAM 조회 함수를 주입해 시작 시에는 start 기준 이상을, 실행 중에는 abort 기준 미만을 반환하게 하고, ABORT_MEMORY 판정과 Job 종료·종료 확인 경로를 확인한다
  - START_REFUSED: 주입한 조회 함수가 시작 시 start 기준 미만을 반환하면 자식을 만들지 않음을 확인한다
- Windows 통합 시험(실제 Job, sys.platform == "win32"에서만, 핵심 시험)
  - W1a 정상 종료(코드 0): 하위 프로세스가 모두 먼저 끝난 뒤 루트가 0으로 종료 → 코드 0일 때만 통과, VERIFIED, 기록 필드 집합
  - W1b 잔존 정리(코드 11): 루트가 0으로 끝날 때 하위 프로세스가 아직 실행 중 → 코드 11일 때만 통과, 하위 프로세스 종료 확인
  - W2 시간 초과: max-seconds 짧게 → 20, 자식·손자 모두 종료 확인
  - W3 실제 조회 연동: 정상 실행 중 실제 GlobalMemoryStatusEx와 Job 조회가 성공하고 watch_state.json에 가용 RAM·Job 활성 수·PeakJobMemoryUsed 값이 기록됨을 확인한다. 기준 미달을 만들지 않으며 메모리 중단 분기는 단위 시험이 맡는다
  - W4 시작 거부: start·abort 기준을 실제 가용량보다 크게(start ≥ abort 유지) 설정 → 30, 자식 생성 없음
  - W5 감시 도구 강제 종료: 실행 중 시험이 보유 핸들로 감시 도구를 TerminateProcess → 자식·손자가 verify 상한 안에 사라짐(시험이 신원 기록의 PID·생성 시각을 대조해 미리 연 SYNCHRONIZE 핸들의 유한 시간 대기로 확인. 핸들을 열 수 없거나 신원이 다르면 미확인으로 실패)
  - W6 무관 프로세스 보존: 시험이 Job 밖에서 띄운 sleeper가 W2 중단 뒤에도 살아 있음
- CLEANUP_EXCEPTION: 시험이 직접 생성하고 핸들을 보유한 감시 도구·합성 프로세스(Job 밖 sleeper 포함)에 한해, 그 보유 핸들로 종료하고 유한 시간 대기로 종료를 확인할 수 있다. 그 밖의 기존·무관 프로세스 조작은 금지한다
- 정리 책임: 각 통합 시험은 finally에서 CLEANUP_EXCEPTION 범위의 프로세스를 종료·확인한다. Job 구성원은 감시 도구 종료 시 KILL_ON_JOB_CLOSE로 정리된다. CREATE_SUSPENDED 상태의 자식은 자기 60초 타이머가 실행되지 않으므로 자기 수명 상한으로 정리되지 않는다. pytest 프로세스 자체가 강제 종료되면 정리가 보장되지 않는다(한계)
- 정리 실패는 숨기지 않고 잔존 또는 종료 미확인으로 보고하며 테스트 실패로 처리한다
- 예상된 실패 경로는 테스트 단언으로 다룬다. 감시 도구의 실제 예외·크래시는 테스트 실패다
- Windows에서 W1a·W1b·W2–W6 중 하나라도 skip되면 검증 완료로 판정하지 않고 STOP한다
- CHECK_COMMANDS(문자열 그대로)
  - CHECK_1: cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -rs -v tests/test_runwatch.py
  - CHECK_2: cd C:/MoneyLab-futval-v8-01-precheck && ./.venv/Scripts/python.exe -B -m ruff check --no-cache src tests
  - CHECK_3A: cd C:/MoneyLab-futval-v8-01-precheck && ./.venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache
  - CHECK_3B: cd C:/MoneyLab-futval-v8-01-precheck && ./.venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache src/moneylab/runwatch
  - CHECK_4: cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -rs
  - COLLECT_COMMAND: cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q
- CHECK_4는 기존 연구 단위 테스트(tests/test_futval_v8_01.py 등)의 회귀 실행을 포함하며 허용된다. 운영 smoke·perf·run과 FUTVAL-V8-01 이름공간 실행은 아니다
- 시간 한도: CHECK_1·2·3A·3B·COLLECT 각 600초, CHECK_4 3600초(백그라운드, 완료 알림, 폴링 없음). 넘으면 STOP
- CHECK_1–4 failed 0 / errors 0. 각 CHECK 전후 ALLOWED_FILES의 W와 git status --ignored 기록
- BGA-4·BGA-10: IMPLEMENTATION의 신규 테스트·ruff·mypy 실패는 승인 예산 안에서 ALLOWED_FILES만 고쳐 같은 CHECK로 다시 실행한다. 기존 비허용 파일 테스트 회귀, COMMIT 이후 실패, Windows 핵심 시험 skip은 STOP이다
- BGA-8: BASELINE_COLLECT(WORKSPACE_SETUP에서 C1 생성 직후, 구현 파일 생성 전 COLLECT_COMMAND 1회의 수집 ID 원문) 대비 감소 없음, 추가 ID는 모두 tests/test_runwatch.py, 기존 테스트 변경·skip·xfail 추가 없음
- git diff --check 깨끗함, 변경 파일 집합 = ALLOWED_FILES

## E2E_GATES

E2E_GATES:
- CLEAN_COMMIT_E2E: HEAD = C2 clean, CHECK_1 1회, 실행 전후 status(ignored 포함) 동일, ALLOWED_FILES의 commit 내용 S와 작업 파일 W 대조, 보호 소스·사전등록·PRESERVED_OUTPUT 불변

## SYNTHETIC_DRILL

SYNTHETIC_DRILL(별도 승인, 묶음 밖):
- 시작 주체·방식: 에이전트가 Bash 백그라운드 단독 호출로 감시 도구 CLI를 시작하고 완료 알림으로 기다린다. breakaway·스케줄러·사용자 터미널은 쓰지 않는다. 각 명령 문자열은 실행 승인에 명시한다
- 위치: data/processed/runwatch_drill/<항목>-a1 (ignored, 각 watch-dir은 미리 없어야 한다). 합성 프로세스의 신원 기록은 watch-dir 밖 data/processed/runwatch_drill/<항목>-ids.json
- 합성 자식: 짧은 합성 Python 코드다. 실행이 시작되면 자기와 하위 프로세스의 PID와 생성 시각(GetProcessTimes)을 신원 기록에 쓰고, 최대 60초 뒤 스스로 끝난다. 연구 모듈을 import하지 않는다
- 실제 메모리 고갈이나 가용량 변화를 강제로 만들지 않는다. 메모리 중단 분기는 TEST_GATES의 조건 주입 단위 시험으로 검증하며 drill에 포함하지 않는다
- 실행 항목과 횟수(재시도 없음)
  - D1a 정상: 감시 도구 1회, sleeper 0회. 하위 프로세스가 모두 먼저 끝난 뒤 루트가 0으로 종료. 기대 코드 0, VERIFIED. 코드 11이면 실패
  - D1b 잔존 정리: 감시 도구 1회, sleeper 0회. 루트가 0으로 끝날 때 하위 프로세스가 아직 실행 중. 기대 코드 11, VERIFIED
  - D2 시간 초과와 무관 보존: 감시 도구 1회, sleeper 1회. 루트 60초, max-seconds 5. D2 감시 도구 시작 전에 Job 밖 sleeper(90초 뒤 스스로 종료)를 1회 시작하고 같은 실행 동안 관찰. 기대 코드 20, VERIFIED, 중단 직후 sleeper 생존
  - D3 감시 도구 중단: 감시 도구 1회, sleeper 0회. max-seconds 120인 감시 도구 백그라운드 작업을 실행 중 TaskStop. 기대: 잔존 확인에서 모든 대상 종료 확인
- 합계: 감시 도구 실행 4회, Job 밖 sleeper 시작 1회. D2의 무관 보존 관찰은 D2와 같은 실행이며 별도 재실행이 아니다
- 잔존 확인(D2 sleeper 생존, D3 종료 확인)
  - 방식: 읽기 전용 조회로 신원 기록의 각 PID에 대해 현재 프로세스 존재 여부와 생성 시각만 얻는다. 종료·조작 동작은 없다. 조회 명령은 실행 승인에 명시한다
  - 시점·횟수: D3은 TaskStop 직후, 15초 뒤, 30초 뒤 각 1회(최대 3회). D2 sleeper는 D2 감시 도구 종료 직후 1회. 조회 사이 대기는 하네스가 허용하는 방식으로 하며 그 명령도 실행 승인에 명시한다
  - 판정: 프로세스 없음 → 종료 확인. 같은 PID이고 생성 시각이 같음 → 잔존. 같은 PID이고 생성 시각이 다름 → 재사용으로 보고 미확인. 접근 거절·조회 실패·신원 기록 부재 → 미확인
  - D3은 마지막 조회에서 모든 대상이 종료 확인일 때만 통과다. 잔존이나 미확인이 하나라도 있으면 STOP하고 RUN 계약 진행을 막는다
  - PID 조회 결과를 근거로 어떤 프로세스도 종료하지 않는다
- 판정: D1a·D1b·D2·D3이 모두 기대와 같으면 DRILL_PASS
- 한계: 최대 3회 표본이므로 30초 안의 종료를 연속 관찰로 입증하지 않는다. 메모리 중단은 실제 상황에서 검증하지 않는다. 세션 단절 상황 자체와 장시간 내구성은 이 drill로 입증하지 않는다

## PRESERVATION_CHECK

PRESERVATION_CHECK:
- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): git -C C:/MoneyLab-gov-automation-03 for-each-ref --sort=refname --format="%(refname) %(objectname)", worktree list --porcelain, host rev-parse HEAD HEAD^{tree}와 status --porcelain=v1 --untracked-files=all --ignored=matching 원문 전체를 도구 출력으로 남긴다
- 분류: TASK = refs/heads/codex/runwatch-01(생성 -> C1 -> C2), OBSERVED = refs/codex/turn-diffs/checkpoints/**, PRESERVE = 그 밖(codex/futval-v8-01-precheck = Ce, codex/futval-v8-01-smoke-perf = dedfafb1 포함)
- worktree: TARGET_WORKTREE 항목을 통째로 제외하고 항목 단위 비교. TARGET_WORKTREE 항목의 기대 변화는 branch가 smoke-perf에서 runwatch-01로, HEAD가 C1·C2로 바뀌는 것뿐
- 산출물: PRESERVED_OUTPUT 불변, 새 ignored 항목은 data/processed/runwatch_drill/ 와 .venv/.mypy_cache 갱신뿐
- 비교 시점: WORKSPACE_SETUP 종료, CLEAN_COMMIT_E2E 종료, SYNTHETIC_DRILL 종료, CLOSEOUT_REPORT

## EXPECTED_ASK

EXPECTED_ASK(실제 발생은 보장하지 않음):
- WORKSPACE_SETUP: Work Order 최초 생성(task-contract) 1회, git commit 확인 1회
- COMMIT: git commit 확인 1회
- SYNTHETIC_DRILL: 없음. 잔존 확인 조회를 포함한 어떤 명령에서든 권한 창이 뜨면 예상 밖 ASK로 보고 그 명령을 진행하지 않고 STOP하며, 새 승인을 받는다
- 그 밖의 ASK·거절·무응답·DENY는 STOP

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: 기준·C1·C2 SHA·tree·parent, 파일 SHA-256, 커밋 파일 집합
- CLAUDE_REPORTED: CHECK 결과·시간과 전후 W, 수집 ID 비교, BGA-8, drill 종료 코드·watch_final 필드·잔존 확인, 보존 비교
- INDEPENDENT: 사용자 확인(원격 단계 없음)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, HEAD·parent·tree, 변경 집합, PROTECTED diff, status(ignored 포함), W·S
- 테스트와 DESIGN_CONTRACT D1–D13 대응, Windows 통합 시험 skip 여부
- PRESERVATION_CHECK 분류별 결과
- GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES, BUDGET 사용, <GATE>_PASS, READY_FOR_<NEXT>
- 유지할 한계: D13, 바깥 Job과의 상호작용·세션 종료 동작은 drill 범위에서만 확인됨

## STOP_CONDITIONS

STOP_CONDITIONS:
- 기준·HEAD·tree·Work Order sha256 불일치, TARGET_BRANCH·Work Order 경로가 미리 있음
- ALLOWED_FILES 밖 변경, PROTECTED 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅, 예상 밖 untracked·ignored
- 기존 비허용 파일 테스트 회귀, COMMIT 이후 테스트 실패, Windows 핵심 시험 skip, BUDGET(수정 반복·같은 실패 연속 포함) 초과, 시간 한도 초과. IMPLEMENTATION의 신규 테스트·ruff·mypy 실패는 BGA-4 범위 안에서는 STOP이 아니다
- 통합 시험·drill에서 Job 밖 프로세스 영향, 자식·손자 잔존, 감시 도구가 Job 할당 없이 자식을 실행한 정황
- PRESERVE ref 변화, worktree 항목 불일치, PRESERVED_OUTPUT 변화
- guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- 사전등록·상위 규칙과 충돌
