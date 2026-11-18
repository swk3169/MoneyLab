# ERRATA-001: RUNWATCH-01 — D5 판정 순서 정합, SYNTHETIC_DRILL 예상 ASK와 drill 판정 보완

이 파일은 불변이다. 발행(Ce) 후 수정하지 않는다.

## Metadata

ERRATA_ID: ERRATA-001
TASK_ID: RUNWATCH-01
STATUS: ACCEPTED
WORK_ORDER_PATH: docs/tasks/RUNWATCH-01/WORK_ORDER.md
WORK_ORDER_SHA256: e0432beb06e41f424e42f42f0b192f4ee7901c25e58578118587a172a2ed60e1
WORK_ORDER_COMMIT: e3b709129c7e78c8cf3223265269c4d7a8307739
IMPLEMENTATION_COMMIT (C2): 9790420c14d471420a86aeca301311f2e0ee09e6
IMPLEMENTATION_TREE: 1f90a652191d1440ff3f67d84136d96c320cbfd7
PRIOR_ERRATA: NONE

## 변경 항목

- DESIGN_CONTRACT D5: 판정 순서를 C2 구현과 일치시킨다
- EXPECTED_ASK: SYNTHETIC_DRILL의 inline-code ASK 상한
- SYNTHETIC_DRILL: D3 준비 확인, 감시 프로세스 신원, 시간 관계, 조회 분류, 신원 취득 실패, 대기·조회 횟수 상한, 명령 조립 규칙
- ALLOWED_ACTIONS·CONTRACT_FILE_EXCEPTION·PROTECTED_FILES: 이 ERRATA 파일의 최초 생성 예외
- COMMIT_PLAN: Ce 추가
- PRESERVATION_CHECK: TASK ref 기대 변화
- REQUIRED_REPORT: 구현 식별 커밋(C2)과 실행 기준 HEAD(Ce)의 구분

## 사유

- C2 구현의 감시 루프는 가용 RAM, Job 활성 수, PeakJobMemoryUsed를 한 번에 조회한다. 그중 하나라도 실패하면 ABORT_MONITOR_FAILURE로 끝내고, 모두 성공한 경우에만 메모리 기준을 판정한다. Work Order D5 문구는 메모리 미달을 조회 예외보다 앞에 두어, 가용 RAM 미달과 다른 조회 실패가 함께 일어난 경우의 사유 코드가 구현(22)과 문구(21)에서 달랐다. 구현은 바꾸지 않고 계약을 구현에 맞춘다
- SYNTHETIC_DRILL의 합성 자식은 임시 스크립트 파일 금지에 따라 python -c 코드로 실행되며, guard inline-code 규칙의 ASK 대상이다. Work Order는 drill의 예상 ASK를 없음으로 정했다
- D3의 통과 판정은 합성 프로세스의 60초 자체 종료와 구별되어야 하고, 감시 프로세스 자체의 종료도 확인해야 한다

## DESIGN_CONTRACT D5 대체 문구

- D5 감시 루프: poll-seconds마다 다음 순서로 판정한다
  - 루트 자식 종료 → D6 정상 종료 경로
  - 경과 ≥ max → ABORT_TIME
  - 가용 RAM(GlobalMemoryStatusEx.ullAvailPhys), Job 활성 프로세스 수(BasicAccounting), PeakJobMemoryUsed(ExtendedLimit)를 조회한다. 하나라도 예외면 ABORT_MONITOR_FAILURE
  - 조회가 모두 성공한 경우에만 가용 RAM < abort 기준 → ABORT_MEMORY. 가용 RAM 미달과 다른 조회 실패가 같은 주기에 함께 일어나면 코드 22(ABORT_MONITOR_FAILURE)가 우선한다
  - watch_state.json 쓰기 실패 → ABORT_STATE_WRITE_FAILURE
  - 모든 ABORT는 TerminateJobObject(J) 뒤 D6 종료 확인
  - 감시 루프의 처리되지 않은 예외는 TerminateJobObject(J)와 D6를 시도한 뒤 INTERNAL_ERROR로 끝낸다
- 이 대체는 C2 구현을 바꾸지 않는다. 과거 D5 차이 보고와 IMPLEMENTATION..CLEAN_COMMIT_E2E PASS 보고는 소급해 지우지 않고 기록으로 유지한다

## EXPECTED_ASK 보완

- SYNTHETIC_DRILL: inline-code 최대 5회(감시 도구 실행 4회와 Job 밖 sleeper 시작 1회의 합성 python -c 명령). 각 창에서 실제 합성 명령을 확인하고 사용자가 그 창에서 별도로 승인해야 한다
- 그 밖의 ASK·거절·무응답·DENY는 STOP이다
- D3 준비 확인(신원 파일 작성 포함)과 신원 조회는 실제 쓰기 동작을 포함해 정적으로 대조한 결과 추가 예상 ASK가 없다. 이 명령들에서 권한 창이 뜨면 예상 밖 ASK로 보고 진행하지 않고 STOP한다
- 이 조항은 연구 실행, 권한 규칙·guard·hook 변경을 허용하지 않는다. guard 판정을 무효화하지 않는다

## SYNTHETIC_DRILL 보완

- 실행 횟수는 바꾸지 않는다: 감시 도구 4회(D1a, D1b, D2, D3), Job 밖 sleeper 1회
- 신원 취득: 합성 프로세스는 GetProcessTimes 성공을 확인한다. 실패하면 신원을 기록하지 않고 비0으로 끝난다. 0값이나 불완전한 신원으로 진행하지 않으며, 신원 기록이 완결되지 않으면 준비 실패로 STOP한다
- 신원 조회 분류
  - OpenProcess 실패 오류 87 → GONE(종료 확인)
  - 같은 생성 시각이고 WaitForSingleObject(…, 0)가 WAIT_OBJECT_0 → EXITED(종료 확인)
  - 같은 생성 시각이고 WAIT_TIMEOUT → ALIVE(잔존)
  - 생성 시각이 다름 → UNCONFIRMED_REUSED
  - 그 밖의 OpenProcess 오류, GetProcessTimes 실패, WaitForSingleObject의 그 밖의 반환값 → UNCONFIRMED
  - 조회 실패를 ALIVE로 분류하지 않는다. 조회 결과를 근거로 어떤 프로세스도 종료하지 않는다
- D3 준비 확인(TaskStop 전 1회)
  - 신원 기록 D3-ids.json의 항목이 정확히 3개이고 PID가 서로 다르며 셋 모두 ALIVE
  - watch_state.json이 있고 child_pid가 정수, elapsed_seconds > 0, job_active_processes ≥ 3
  - 이 준비 확인은 프로세스 읽기 전용 조회와 새 신원 파일 작성이다. 쓰기는 data/processed/runwatch_drill/D3-watcher-ids.json의 최초 작성과 같은 위치의 .part 파일 생성·교체만 허용한다. 파일이 이미 있으면 덮어쓰지 않고 준비 실패로 STOP한다. 실패로 남은 파일은 지우지 않고 보고한다
  - 감시 프로세스 후보는 프로세스 목록 조회로 얻은 child_pid의 부모와 그 부모다. 부모 관계만으로 확정하지 않고 다음이 모두 맞을 때만 각각 감시 도구와 실행기로 인정한다: 실행기의 실행 파일 경로가 대상 venv의 Scripts/python.exe이고 감시 도구의 실행 파일 경로가 그 venv pyvenv.cfg의 home 아래 python.exe다, 생성 시각 순서가 실행기 ≤ 감시 도구 ≤ D3-a1 watch-dir 생성 ≤ 루트 자식 생성이다, 감시 도구 생성 시각이 준비 확인 시점 전 120초 이내다. 확인할 수 없거나 구조가 다르면 준비 실패이며 다른 조상 프로세스를 대상에 넣지 않는다
  - D3 백그라운드 작업 ID와 이 프로세스들의 연결은 같은 D3 명령이 만든 D3-a1 watch-dir과 위 시간 관계로만 확인한다. 그 이상의 연결은 주장하지 않는다
  - 조회한 실행 정보는 판정에 필요한 항목(PID, 생성 시각, 실행 파일 경로의 일치 여부)만 다루며, 경로 등 실행 정보 전체를 출력하거나 기록하지 않는다. 신원 취득은 관찰용이며 PID 조회를 근거로 어떤 프로세스도 종료하지 않는다
  - Snapshot 생성, 프로세스 열거, 신원 조회(OpenProcess·GetProcessTimes·실행 파일 경로 조회) 실패를 명시적으로 검사한다. 준비 조건은 출력이 아니라 검증으로 판정하며, 하나라도 충족하지 않으면 준비 명령이 비0으로 끝나고 TaskStop을 호출하지 않는다
  - 감시 도구와 실행기는 둘 다 ALIVE여야 한다
  - 하나라도 충족하지 않으면 TaskStop을 호출하지 않고 STOP한다
- D3 판정
  - TaskStop 대상은 이번 D3에서 시작한 감시 도구 백그라운드 작업 ID 하나뿐이다
  - TaskStop 직후, 15초 뒤, 30초 뒤 각 1회(최대 3회) D3-ids.json과 D3-watcher-ids.json을 조회한다
  - 시간 관계: 각 조회는 조회 시각(GetSystemTimeAsFileTime)을 함께 기록한다. 합성 프로세스는 생성 시각 + 55초 이전, 감시 프로세스는 생성 시각 + 115초 이전에 이루어진 조회에서만 종료 확인을 인정한다. 그 이후의 조회 결과는 자체 종료나 감시 도구의 시간 상한과 구별할 수 없으므로 UNCONFIRMED_TIME이다
  - 통과: 마지막 조회에서 합성 3개와 감시 2개가 모두 GONE 또는 EXITED이고, 모두 시간 관계를 만족한다. 그 밖의 결과는 실패이며 STOP하고 RUN 계약 진행을 막는다
- 대기·조회 상한(계약상 폴링 금지와 구분되는 유한 확인)
  - 신원 파일 대기: D2 sleeper 1회, D3 1회. 각각 백그라운드 단일 명령, 0.5초 간격, 최대 60초
  - 고정 간격 대기: D3의 15초 대기 2회. 각각 백그라운드 단일 명령
  - 신원 조회: D2 종료 직후 1회, D3 준비 확인 1회, D3 TaskStop 뒤 최대 3회
  - 이 범위를 넘는 반복·대기는 하지 않는다. 연구 산출물은 조회하지 않는다
- 명령 조립: 각 감시 명령은 실행 승인에 고정된 접두부 + 작은따옴표 + 승인된 합성 코드 원문(작은따옴표 없음) + 작은따옴표 + 공백 + 고정 인자로 만든다. 문자를 바꾸거나 인코딩하지 않는다. 실행 때 권한 창과 도구 출력에 표시되는 명령이 이 조립과 같아야 한다
- 승인된 출력: data/processed/runwatch_drill/ 아래 watch-dir 4개(D1a-a1, D1b-a1, D2-a1, D3-a1)와 그 감시 파일, 신원 파일 6개(D1a-ids.json, D1b-ids.json, D2-ids.json, D3-ids.json, D2-sleeper-ids.json, D3-watcher-ids.json). 실패로 남은 .part 파일은 지우지 않고 보고한다

## ERRATA-001 최초 생성 예외 (ALLOWED_ACTIONS·CONTRACT_FILE_EXCEPTION·PROTECTED_FILES)

- 이 예외는 사용자의 이 ERRATA 수락과 별도 승인 GATE_AUTHORIZATION: RUNWATCH-01 ERRATA_001_CREATION_ONLY가 모두 있을 때에만 적용한다. ERRATA 문안 자체는 권한을 만들지 않는다
- ALLOWED_ACTIONS 추가: docs/tasks/RUNWATCH-01/ERRATA-001.md를 승인된 바이트로 Write 1회, git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/RUNWATCH-01/ERRATA-001.md 1회, Ce 커밋 1회
- CONTRACT_FILE_EXCEPTION 추가: A docs/tasks/RUNWATCH-01/ERRATA-001.md (ERRATA_001_CREATION_ONLY 전용, 승인 바이트로 최초 1회)
- PROTECTED_FILES의 docs/tasks/RUNWATCH-01/** 보호는 이 최초 생성 외에는 그대로다. WORK_ORDER.md와 기존 파일 수정, 생성 뒤 ERRATA-001.md 수정, 다른 보호 경로 변경은 허용하지 않는다
- Ce 조건: parent(Ce) = C2(9790420c14d471420a86aeca301311f2e0ee09e6), C2..Ce 변경 = A docs/tasks/RUNWATCH-01/ERRATA-001.md 하나, 메시지 docs(task): add RUNWATCH-01 ERRATA-001, 본문·trailer 없음. Ce 생성은 묶음 대상이 아니다

## COMMIT_PLAN 추가

- Ce: parent = C2, 변경 = A docs/tasks/RUNWATCH-01/ERRATA-001.md
- CANONICAL_BASE_SHA..Ce의 변경 경로는 WORK_ORDER.md, ERRATA-001.md, ALLOWED_FILES 5개, 모두 7개뿐이다

## PRESERVATION_CHECK의 TASK 기대 변화

- TASK(refs/heads/codex/runwatch-01)의 기대 변화는 생성 -> C1 -> C2 -> Ce다. C2 -> Ce 이동은 ERRATA-001 생성 커밋 1회뿐이다
- 대상 worktree 항목의 HEAD 기대 변화에 Ce를 추가한다. OBSERVED·PRESERVE 분류, 비교 방법, STOP 조건, 기존 F0은 바꾸지 않는다

## 구현 식별과 실행 식별 (REQUIRED_REPORT)

- 구현 식별 커밋은 C2다. ALLOWED_FILES 5개의 blob과 commit 내용 S는 C2 기준이다
- SYNTHETIC_DRILL과 CLOSEOUT_REPORT의 실행 기준 HEAD는 Ce다. 진입 시 Ce의 ALLOWED_FILES blob이 C2와 같고, 작업 파일 W가 C2 commit 내용 S와 같음을 확인한다
- 보고는 C1(Work Order), C2(구현), Ce(ERRATA-001, 실행 기준 HEAD)를 구분한다

## 범위와 불변

- 이 정정은 위 변경 항목에만 적용한다. 구현·테스트(C2의 5개 파일), 기존 계약, 사전등록, 연구 산출물, 그 밖의 계약 조건과 이미 끝난 gate의 판정은 바꾸지 않는다
- 기존 기록을 소급해 없애지 않는다: D5 차이 보고, IMPLEMENTATION..CLEAN_COMMIT_E2E PASS, 셸 오류 3건, 예상 밖 ASK를 거친 실행, 건수 오기
- Work Order의 유지할 한계(D13, 세션 단절·장시간 내구성 미입증, PeakJobMemoryUsed 의미 미검증)는 그대로 유지한다
- 이 ERRATA는 ERRATA-001 생성과 SYNTHETIC_DRILL의 실행 권한을 만들지 않는다. 각각 별도 GATE_AUTHORIZATION이 필요하다
