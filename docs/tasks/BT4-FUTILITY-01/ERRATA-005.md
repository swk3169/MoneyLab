# ERRATA: BT4-FUTILITY-01 ERRATA-005

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-FUTILITY-01-ERRATA-005
TASK_ID: BT4-FUTILITY-01
TARGET_WORK_ORDER: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md @ 7ac09a674e68cbc95dd5c934f2d3580939fd02f0 (sha256 c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b)
PRIOR_ACCEPTED_ERRATA: ERRATA-001 (sha256 9fcac5a97605a85be68612ba4a465c5f24b8c5b5594f3a801ca5e551993d24bf, Ce 616ed51f257a8cfa2d2c080067b09258651930e9), ERRATA-002 (sha256 0ca8ab961af350b10a2660ca8ee7b8c4bfab2757ee2b6b1ae61ffcfeee7308fe, Ce 2eb876e02456405667f466a124f745b3dd4fba3c), ERRATA-003 (sha256 9b8fcf9f30d8b525237a63b00f599add0a2fbcb33cb0f9ce900642a5a349823d, Ce b9932dcaa0c3f11568a65c9a6c19993675581d4c), ERRATA-004 (sha256 4b8de161474139cd24976897804a717ad94c9beaa89a2f74da492e0e845b2061, Ce a1b15ff1eb088860a50ec3dbbc7c98abd985e3c6)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

규칙 분류(ERRATA-004와 같은 정의): [A] 기존 계약에서 직접 도출되는 명확화 / [B] 기존 계약에 없는 신규 결정(수락 시 계약) / [B-STAT] 기존 계약에서 추론되지 않는 신규 통계 계약(수락 시 계약) / [C] 구현 단계에서 수행할 후속 조치

## ISSUE

ISSUE: ERRATA-004 OPEN_ITEMS O-1~O-5(G7 구조, 셀별 reps, 전체 예산의 저장·검증 경로, V-4 산출물, G8a 결과 위치)가 정해지지 않았다. WO:87(G5 이후 코드 변경은 STOP·사용자 결정), WO:71(G7 코드 변경 금지), WO:73(G8a는 커밋된 판정 함수)에 따라 G5~G8a의 진입 코드는 C3(CODE_SHA)에 있어야 하므로 G3 완료 전에 정한다. 또 WO:455의 pilot P0 conf 검사는 SE 정의와 기록 방식이 없고, 사전등록의 STOP_FOR_USER_DECISION(PD-5 등)과 ERRATA-003 R-4의 "재개는 사용자 결정"은 결정을 어떻게 기록·검증하는지 정하지 않는다. 이 ERRATA 작성 시점에 G4c 이후 gate는 실행되지 않았다.

## CHANGED_FIELDS

CHANGED_FIELDS (보충, 기존 문장 유지):
- ERRATA-004 O-1~O-5의 결정
- WO:73 "run 디렉터리"의 해석(셀별 run일 때)
- WO:245 출력 위치 아래의 run_id 규칙, G7 실행 잠금 디렉터리, 사용자 결정 기록 디렉터리
- STOP_FOR_USER_DECISION·재개·잠금 abandon·재시도 결정의 기록·검증 방식
- WO:421(사전등록 §4.5에 원문 수록) "누적 시간"의 재시도 포함 범위 명확화
- WO:455 P0 conf 검사의 SE 정의와 기록 방식(R-8, [B-STAT])
- G7 실행 잠금 abandon의 E-BOOT 판정 방법(R-4), 프로세스 종료의 금지·별도 승인 구분(R-4c), 통합 테스트 구성과 실행 승인 단위(R-9)

UNCHANGED_FIELDS:
- POLICY_VALUES, STATISTICAL_HYPOTHESES, 판정·다중성, DC1–DC14(DC12 R_c 식 포함), PD-1~PD-6과 사전등록의 모든 STOP 조건, 사전등록 §4.5 RESOURCE_BUDGET 원문(식·상수·1.5배 기준), 사전등록·config 파일
- run_spec 스키마(RUN_SPEC_FIELDS), run_inputs 필드, execution.json 스키마 /2, 최상위 SHA256SUMS 범위, storage/atomic
- ERRATA-001~004 전부(ERRATA-003 R-4의 TIME_ACCOUNTING_INCOMPLETE 정의, ERRATA-004 R-6의 비교식과 STOP 기준 포함)
- seed 이름공간과 문자열(ERRATA-002), CORE_MAX_WORKERS = 12, 예산 상한과 식
- 이 ERRATA는 R-8 외의 통계 판정 기준, 검정력 목표, 예산 상한, 예산식을 추가하거나 바꾸지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- R-0 사용자 결정 기록(UDR):
  - [B] STOP_FOR_USER_DECISION 이후의 진행(PD5_PROCEED), 비정상 종료 뒤 재개(RESUME_AFTER_INCOMPLETE), 잠금 abandon(LOCK_ABANDON), 재시도(ATTEMPT)는 UDR 없이 하지 않는다. CLI 인자는 UDR 파일을 가리키기만 하며 승인을 대신하지 않는다.
  - [B] 승인 줄: 사용자 메시지 안의 정확히 한 줄
    `USER_DECISION: BT4-FUTILITY-01 UDR#<NNNNNN> <kind> <full_target> <decision>`
    - 토큰은 공백 하나로 구분하고 토큰 안에는 공백이 없다.
    - kind별 full_target과 decision(모든 sha256은 64자리 전체, 요약 금지):
      - PD5_PROCEED: `g6=<G6 요약 sha256>`, decision = PROCEED
      - RESUME_AFTER_INCOMPLETE: `run=<run_id>,run_spec=<run_spec sha256>`, decision = RESUME
      - LOCK_ABANDON: `lock=<NNNNNN>,lock_sha256=<lock 파일 바이트 sha256>`, decision = ABANDON
      - ATTEMPT: `prev=<이전 run_id>,new=<새 run_id>,reason=<ABNORMAL_TERMINATION|INTEGRITY_FAILURE>`, decision = NEW_ATTEMPT
  - [B] 생성 조건:
    - 실제 사용자 메시지에 위 승인 줄이 있어야 한다. Claude는 승인 줄을 대신 만들거나 제안된 줄을 승인으로 간주하지 않는다. 승인 줄이 없으면 UDR을 만들지 않는다.
    - 승인 줄 하나는 그 번호의 UDR 파일 하나를 쓰는 권한만 준다. 다른 파일 변경, gate 진행, 실행 권한을 주지 않는다.
    - UDR#번호는 쓰는 시점의 `user-decisions/` 다음 번호(가장 큰 번호 + 1)와 같아야 한다. 다르면 쓰지 않고 STOP한다.
  - [B] 위치·형식: 출력 루트(WO:245)의 `user-decisions/NNNNNN-<kind>.json`을 O_CREAT|O_EXCL로 만든다. 추가 전용이며 어떤 파일도 고치거나 지우지 않는다. 내용(canonical JSON, 쓰인 뒤 불변):
    - schema_version = "moneylab.bt4_futility_diag.user_decision/1", study_id, evidence, number, kind, target(승인 줄의 full_target을 구조화한 값), decision
    - reason: 사용자가 준 근거 문장(그대로)
    - approval_text: 승인 줄 원문, approval_text_sha256: 그 UTF-8 바이트의 sha256
    - approved_by = "USER", recorded_by = "CLAUDE", code_sha
    - approved_utc: 참고값. Claude가 기록하므로 검증 근거가 아니다.
  - [B] 증거 등급: UDR은 CLAUDE_REPORTED다. 승인의 검증 근거는 채팅 기록의 승인 줄 원문이며, 사용자·감사자는 approval_text와 approval_text_sha256으로 대조한다.
  - [B] 검증(UDR을 쓰는 모든 단계: G7 진입, V-4, G8a, 잠금 abandon, 재개, 재시도):
    - 파일이 있고 canonical이며 스키마가 맞다.
    - approval_text를 파싱한 번호·kind·target·decision이 파일 이름 번호와 기록 필드에 정확히 같다.
    - approval_text_sha256이 원문과 맞고, `user-decisions/` 안에서 유일하다(재사용 금지).
    - target이 그 단계의 실제 대상과 정확히 같다(다른 대상 전용 금지).
    - 하나라도 어긋나면 STOP한다. 사용한 UDR의 sha256은 그 단계의 결정적 산출물(manifest, v4.json, decision_summary.json)에 기록하고, 하위 단계는 기록된 sha256의 UDR 파일이 그대로 있는지 다시 확인한다.
  - [B] UDR로 할 수 없는 것: 예산 PASS 선언, TIME_ACCOUNTING_INCOMPLETE를 COMPLETE로 바꾸기, 누락 시간 추정·대체, 프로세스 종료 확인의 대체(R-4), 사전등록·ERRATA의 STOP 기준이나 상한 변경, R-6의 G8a 진입 조건 우회, 예산 STOP 뒤 재시도(R-7).
- R-1 G7 run 구조 (O-1, O-2):
  - [A] 한 복제의 record는 (namespace, cell, rep, window, rule) seed로만 정해지므로(ERRATA-002) run 구조와 무관하게 같은 (cell, rep) record의 바이트가 같다. R_c는 셀마다 정해진다(DC12, ERRATA-003 R-6).
  - [B] G7 CORE는 셀별 독립 run 두 개다. 각 run의 run_spec은 mode = core, cells = [그 셀 하나], reps = G6 요약의 r_c.r_c[그 셀], unit_size = G6 요약의 pilot.unit_size(ERRATA-004 R-4), windows = WINDOWS 전체, rules = RULES 전체, bootstrap = 1,999다. run_inputs의 namespace는 FUTDIAG이고 calibration_provenance는 G5 RESEARCH 보정이다.
  - [A] 두 run의 manifest는 같은 G6 요약을 참조하는 같은 G6 section을 담는다(ERRATA-004 R-5).
  - [B] G7 진입 검사(하나라도 어긋나면 STOP): cells가 한 셀, reps ≠ G6 R_c[셀], unit_size ≠ G6 pilot.unit_size, pilot g6가 VERIFIED가 아님, g6_timing 재계산 불일치(ERRATA-004 R-5), g6_timing.budget_pass가 false(WO:419), G6 R_c > 40,000(WO:457), CODE_SHA·사전등록·config·ERRATA sha256 불일치(research_identity), G6 P0_CONF_CHECK = STOP(R-8).
  - [B] PD-5: G6 요약의 pd5.stop이 true이면 G7은 target = 그 G6 요약 sha256인 PD5_PROCEED UDR이 있을 때만 시작한다. 없거나 target이 다르면 STOP_FOR_USER_DECISION이다. 사용한 UDR sha256은 두 CORE run의 manifest에 기록한다. 이는 사전등록 PD-5의 STOP_FOR_USER_DECISION을 기록하는 방식이며 임계값과 STOP 조건을 완화하지 않는다.
  - [A] P2 상태는 CORE G7을 막지 않는다(사전등록 §7).
- R-2 CORE 실행 순서와 호스트:
  - [B] G7 드라이버 하나가 한 프로세스에서 E1 run → P0 run → V-4(R-5) 순서로 실행한다. CORE worker pool은 한 번에 하나만 존재한다.
  - [A] 동시에 쓰는 CORE worker 수는 12 이하다(WO:45, ERRATA-004 R-6). 드라이버의 workers는 1..12만 받는다.
  - [B] G7은 단일 Windows 호스트에서만 실행한다(sys.platform == "win32"). 다른 OS에서는 STOP한다. 출력 루트는 그 호스트의 로컬 디스크여야 한다. 첫 lock에 기록된 host_id(R-4)와 현재 host_id가 다르면 STOP한다.
  - [B] G7 드라이버는 CORE pool을 만들기 전에 R-4a의 대상 job에 들어가야 하고, 모든 계산 worker가 그 대상 job에 속함이 R-4a의 방법으로 확인되기 전에는 연구 계산을 시작하지 않는다. 그 조건을 충족하지 못하면 CORE 실행을 시작하지 않는다.
- R-4a Windows Job Object(G7 CORE worker 생명주기, 대상 job 신원):
  - [A] Windows는 부모 프로세스가 강제 종료돼도 자식 프로세스를 함께 종료하지 않는다. 따라서 드라이버 종료만으로 worker 종료가 보장되지 않는다.
  - [A] 실측 환경 사실(G3b-6I, CLAUDE_REPORTED, Claude Code Bash 도구 아래 조사 프로세스): Windows 10.0.26200, Python 3.14.8, start method spawn. 조사 프로세스는 이미 job에 속했고, 그 가장 안쪽 job의 LimitFlags = 0x3000(KILL_ON_JOB_CLOSE 켜짐, SILENT_BREAKAWAY_OK 켜짐, BREAKAWAY_OK 꺼짐)이었다. venv의 python.exe가 실제 인터프리터를 자식으로 띄우는 중간 실행기로 관찰됐다. 이는 실제 G7 드라이버 환경의 검증이 아니며, 이 플래그만으로 새 job의 worker 보호 실패를 확정하지 않는다. 중첩 할당, 실제 worker 소속, worker 안의 QueryInformationJobObject(NULL) 대상은 UNVERIFIED다.
  - [A] Windows spawn 구현 관찰(G3b-6K, CLAUDE_REPORTED, 설치된 Python 3.14.8 표준 라이브러리 소스를 읽어 확인. 모든 Python 버전에 대한 API 보장이 아니다):
    - multiprocessing/popen_spawn_win32.py:62-67: venv 안에서 실행되면 venv 실행기를 거치지 않고 sys._base_executable(base 인터프리터)을 직접 실행한다(bpo-35797). 따라서 계산 worker는 드라이버의 직계 자식이다. 실행기 → 인터프리터 단계는 드라이버 자신의 실행 경로에만 있다.
    - popen_spawn_win32.py:76-79: _winapi.CreateProcess(…, bInheritHandles = False, 생성 플래그 0, …). 핸들을 상속하지 않고 CREATE_BREAKAWAY_FROM_JOB을 쓰지 않는다.
    - concurrent/futures/process.py:895-916, 856-879: submit마다 _adjust_process_count가 불리며, 쉬는 worker가 없고(쉼 신호는 작업 완료 때만 생김, :391) 현재 수가 max_workers보다 작으면 worker 하나를 그 자리에서(드라이버 스레드에서 동기적으로) 만든다.
    - process.py:232-239: initializer가 예외를 내면 그 worker는 종료되고 부모는 pool을 broken으로 표시한다(BrokenProcessPool).
    - max_tasks_per_child를 쓰지 않으면 worker를 교체하지 않는다.
  - [B] G7 실행 환경은 Python 3.14.8로 고정한다. 다른 버전에서는 STOP하며, 다른 버전을 쓰려면 통합 테스트(IT)를 다시 통과하고 새 ERRATA로 계약을 갱신해야 한다. lock에는 정확한 sys.version 문자열을 기록한다. E-TREE의 재귀 규칙은 이 관찰과 무관하게 유지한다.
  - [A] Python 버전 일치는 위 spawn 경로 관찰의 전제일 뿐이며, Windows job 동작의 검증이 아니다. 중첩 job 할당, worker의 대상 job 소속, 시작 barrier, KILL_ON_JOB_CLOSE의 실제 동작은 그 host와 버전에서 통합 테스트를 통과해야만 인정한다.
  - [B] 대상 job: G7 드라이버가 CreateJobObjectW(보안 속성 없음 = 상속 불가, 이름 없음)로 만든 job 하나다. NULL이 아닌 핸들이어야 한다.
  - [B] 정책과 readback: SetInformationJobObject(JobObjectExtendedLimitInformation)로 LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE를 설정해 성공해야 한다. 대상 job 핸들로 QueryInformationJobObject를 다시 읽어 KILL_ON_JOB_CLOSE가 있고 JOB_OBJECT_LIMIT_BREAKAWAY_OK와 JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK가 없어야 한다.
  - [B] 드라이버 할당: AssignProcessToJobObject(대상 job, 현재 프로세스)가 성공하고, IsProcessInJob(현재 프로세스, 대상 job 핸들)이 TRUE여야 한다. 할당 전에 IsProcessInJob(현재 프로세스, NULL)로 기존 job 소속을 확인해 lock에 기록한다. 기존 job(실측상 SILENT_BREAKAWAY_OK 가능) 안에서의 중첩 할당은 허용하되, 실패하면 STOP한다.
  - [B] breakaway 금지: 대상 job에 두 breakaway 플래그를 두지 않는다. 드라이버는 CREATE_BREAKAWAY_FROM_JOB로 프로세스를 만들지 않는다. 외부 job의 SILENT_BREAKAWAY_OK가 자식의 대상 job 소속에 미치는 영향은 아래 소속 검증의 결과로만 판단한다.
  - [B] 대상 job 소속(드라이버와 실제 계산 worker 전원이 필수 대상이다. 판정은 드라이버 쪽에서 대상 job 핸들로만 한다):
    - 기본 검증(A) IsProcessInJob(worker 핸들, 대상 job 핸들): worker를 (pid, 생성 시각)으로 식별한다. PROCESS_QUERY_LIMITED_INFORMATION으로 열어 핸들을 쥔 채, GetProcessTimes의 생성 시각이 알려 온 값·스냅샷의 값과 같고 드라이버 시작 시각 이후인지, 스냅샷상 부모 pid가 드라이버인지 확인한 뒤 IsProcessInJob이 TRUE여야 한다. 대상 job 자체 또는 그 하위 중첩 job이면 TRUE이며 둘 다 대상 job의 KILL_ON_JOB_CLOSE 적용 범위다. 핸들을 쥔 동안 그 pid는 재사용되지 않는다. 열기 실패, 생성 시각 불일치·조회 실패, FALSE는 STOP이다. 드라이버 자신도 IsProcessInJob(현재 프로세스, 대상 job)으로 확인한다.
    - 보조 통제·무결성 검증(B) QueryInformationJobObject(대상 job, JobObjectBasicProcessIdList)와 프로세스 트리 비교: 대상 job의 pid 목록을 드라이버와 그 살아 있는 자손(스냅샷) 집합과 비교한다. 이는 보조 증거이며 신원 판정은 (A)가 한다. 목록에 드라이버의 자손이 아닌 pid가 있거나(예상 밖 PID), 검증된 worker가 목록이나 스냅샷에 없거나(누락 worker), 목록의 어떤 pid를 열어 생성 시각을 확인할 수 없으면(확인 불가 프로세스) STOP이다. 버퍼가 부족하면 다시 읽는다.
    - 목록과 스냅샷은 서로 다른 시점의 읽기이며 반복해서 일치해도 원자적 증거가 아니다. 이를 보완하기 위해 pool이 열려 있는 동안 드라이버는 계산 worker 외의 자식 프로세스를 만들지 않는다(예: research_identity의 git 호출은 대상 job 할당 전이나 pool을 닫은 뒤에만 한다).
    - (C) worker initializer의 QueryInformationJobObject(NULL)은 가장 안쪽 job의 정책 플래그만 알려 주므로 대상 job 신원의 근거로 쓰지 않는다(진단값만).
  - [B] 시작 barrier(위 Python 3.14.8 관찰에 근거한 구현 경로. 통합 테스트 전까지 구현 동작은 CONDITIONAL):
    1. 대상 job 생성·정책 readback·드라이버 할당·드라이버 소속 확인이 끝난 뒤, R-4의 pool 의도 기록(E-POOL-START)을 쓰고 fsync까지 끝낸 다음에만 CORE pool을 만든다. 의도 기록을 쓰지 못하면 pool을 만들지 않고 STOP한다. `max_tasks_per_child`는 쓰지 않는다.
    2. pool은 `ProcessPoolExecutor(max_workers = w, initializer = barrier, initargs = (ready_queue, release_event, timeout))`로 만든다. ready_queue와 release_event는 spawn 컨텍스트의 Queue와 Event다.
    3. unit의 모든 작업을 먼저 제출한다. barrier가 풀리기 전에는 어떤 작업도 끝나지 않으므로 제출마다 worker가 하나씩 동기적으로 생겨 min(w, 작업 수)개가 된다(위 관찰). release 뒤에는 그 pool에 작업을 제출하지 않는다.
    4. 각 worker의 initializer는 (pid, 생성 시각)을 ready_queue에 넣고 release_event.wait(timeout)으로 기다린다. 시간이 다 되면 예외를 내며, 이는 BrokenProcessPool이 된다. 연구 계산 함수는 initializer가 끝난 뒤에만 실행된다.
    5. 드라이버는 ready_queue에서 알려 온 worker 전원과, 스냅샷에서 pool 생성 뒤 생긴 드라이버의 자식 전원이 정확히 같은 (pid, 생성 시각) 집합인지 확인하고, 그 수가 1 이상 w 이하이며 제출한 작업 수 기준 기대값 min(w, 작업 수)와 같은지 확인한다.
    6. 순서를 고정한다: (i) 그 전원에 대해 기본 검증(A)과 보조 검증(B)을 마친다, (ii) R-4의 worker 기록(E-WORKERS) 파일을 O_EXCL로 만든다, (iii) 내용을 쓴다, (iv) fsync한다, (v) 그 뒤에만 release_event를 set해 계산을 허용한다. (ii)~(iv) 중 하나라도 실패하면 release하지 않고 STOP한다.
    - STOP(그 unit의 결과는 쓰지 않음): worker 수 불일치, ready_queue timeout, BrokenProcessPool, (A)·(B) 실패, 알려 온 worker와 스냅샷 자식의 불일치, E-POOL-START·E-WORKERS 기록 실패.
    - 새 worker나 교체: release 뒤에 검증된 집합 밖의 자식이나 대상 job pid가 나타나면 기존 검증을 재사용하지 않고 STOP한다. 드라이버는 매 unit의 파일을 쓰기 직전에 검증된 집합이 그대로인지(B)와 각 worker가 여전히 같은 (pid, 생성 시각)인지 다시 확인한다. pool은 unit마다 새로 만들고 매번 처음부터 검증한다.
    - deadlock 없음: worker가 준비 신호 전에 죽으면 드라이버의 ready_queue 대기가 timeout으로 STOP하고, 드라이버가 죽으면 worker는 release_event.wait의 timeout 뒤 스스로 끝난다.
  - [B] 핸들 소유권과 수명:
    - 대상 job 핸들은 드라이버 프로세스만 가진다. 상속 불가로 만들고, 자식에 복제(DuplicateHandle)하지 않으며, 파일·로그에 쓰지 않는다.
    - 드라이버는 실행 중에 대상 job 핸들을 닫지 않는다(조기 CloseHandle 금지).
    - 드라이버가 정상 종료, 예외, 강제 종료 중 어떤 이유로든 끝나면 OS가 마지막 핸들을 닫고, KILL_ON_JOB_CLOSE에 따라 대상 job(하위 중첩 job 포함)에 남은 모든 프로세스가 종료된다. 정상 경로에서는 그 전에 `with` 블록이 pool을 닫아 worker가 이미 끝나 있다.
    - 외부 job(예: 실측된 실행기 job)의 정책은 드라이버 자신의 수명에만 관계한다. worker 보호의 근거는 대상 job뿐이다.
  - [B] 기록: lock 내용에 대상 job 사용, 할당 전 기존 job 소속 여부, 대상 job 정책 readback 성공, 드라이버 프로세스 시작 시각을 기록한다(작성 순서: 대상 job 생성·정책·할당·readback → lock 획득).
  - [B] STOP 조건: Windows가 아님, Python 버전이 3.14.8이 아님(위 [B]), 대상 job 생성·정책 설정·readback·할당·IsProcessInJob 중 하나라도 실패, readback 플래그가 위와 다름, 시작 barrier의 STOP 조건, 쓰기 직전 재확인 실패, E-POOL-START 또는 E-WORKERS 기록 실패.
  - [B] 이 장치는 OS의 job 정리 정책이며, MoneyLab 코드가 다른 프로세스에 신호를 보내지 않는다는 R-4 원칙과 충돌하지 않는다. KILL_ON_JOB_CLOSE의 실제 작동과 그 승인은 R-4c를 따른다.
- R-4c 프로세스 종료의 구분:
  - [A] 근거(증거 등급 CLAUDE_REPORTED / PREVIOUSLY_OBSERVED: G3b-6O에서 Python 3.14.8 stdlib을 읽고 관찰한 내용이며, 이 ERRATA를 작성할 때 다시 확인하지 않았다):
    - concurrent/futures/process.py:591-594: pool이 깨지면(broken) 남은 worker 각각에 terminate()를 부른다.
    - process.py:660-663: 깨진 상태의 내부 정리(join 단계)에서 worker에 terminate()를 부른다.
    - process.py:1005-1025: 실행기가 worker를 강제로 끝내는 메서드의 본문이다. 메서드 이름은 확인하지 않았으며, 이 ERRATA는 이름을 추측하거나 정하지 않는다.
    - multiprocessing/popen_spawn_win32.py:126-131: Windows에서 terminate()는 TerminateProcess로 수행된다.
    - 따라서 ProcessPoolExecutor는 오류 처리 과정(BrokenProcessPool 포함)에서 자기 worker를 종료할 수 있다. 시작 barrier의 ready timeout과 initializer 예외(R-4a 시작 barrier 4단계, process.py:232-239)는 이 경로로 이어진다.
  - [B] A. 금지(이 ERRATA의 수락이나 어떤 gate 승인으로도 허용되지 않음):
    - 임의 worker 종료: MoneyLab 코드(운영 코드와 테스트 코드)가 아래 B에 명시된 경우 밖에서 worker를 종료하는 것. 종료 API의 직접 호출, Process 객체의 종료 메서드, 실행기의 worker 강제 종료 메서드(위 :1005-1025 경로), 신호·콘솔 제어 이벤트를 모두 포함한다.
    - 기존 프로세스 종료: 이 실행 이전부터 있던 프로세스(Claude Code, 셸, 다른 MoneyLab 프로세스 포함)의 종료·중단.
    - 승인되지 않은 프로세스 조작: 테스트·드라이버 자신이 만든 것이 아닌 프로세스의 job 할당, 우선순위·affinity 변경, 핸들 복제.
    - guard·hook·settings의 변경이나 우회.
    - timeout을 이유로 한 직접 종료: MoneyLab 코드는 timeout만을 이유로 어떤 프로세스도 직접 종료하지 않으며, 승인되지 않은 종료 API를 호출하지 않는다.
  - [A] timeout과 종료 가능성(사실 기록): 시작 barrier의 ready timeout이나 worker 쪽 release_event.wait timeout은 initializer 예외 → BrokenProcessPool로 이어지고, 이때 stdlib이 그 pool의 남은 worker를 종료할 수 있다(위 [A] 근거). 드라이버가 살아 있는 worker를 남긴 채 끝나면 KILL_ON_JOB_CLOSE가 대상 job의 남은 프로세스를 종료할 수 있다. 이 두 종료는 MoneyLab 코드가 호출하는 것이 아니며, 아래 B(테스트)와 G7_POOL_FAILURE_POLICY(G7)의 별도 승인 대상이다.
  - [B] B. 별도 승인 대상(이 ERRATA의 ACCEPTED는 B의 승인이 아니다):
    - B1 테스트 전용 worker 종료: IT-3b·IT-3c에서 stdlib 오류 처리(위 [A] 근거)로 일어나는 테스트 전용 pool worker의 종료.
    - B2 KILL_ON_JOB_CLOSE 작동 검증: 테스트 전용 대상 job의 마지막 핸들이 닫힐 때 남은 테스트 전용 프로세스의 종료(IT-5).
    - B3 IT-5의 테스트 드라이버 강제 종료.
    - B4 그룹 A 실패 경로의 종료 가능성: 그룹 A(IT-1, IT-2, IT-3a, IT-4)는 정상 경로에서 의도적인 worker 종료를 일으키지 않는다. 그러나 실패 경로(소속 검증 실패, worker 수 불일치, 기록 실패 등으로 release하지 않고 STOP)에서는 worker의 release_event.wait timeout → BrokenProcessPool로 stdlib 내부 worker 종료가 일어날 수 있고, 테스트 드라이버가 끝날 때 KILL_ON_JOB_CLOSE가 작동할 수 있다.
    - 승인 단위는 R-9의 그룹(그룹 A: B4, 그룹 B: B1, 그룹 C: B2·B3)이며, 승인된 그룹의 테스트 전용 프로세스와 테스트 전용 job 밖에는 적용되지 않는다. 이 ERRATA의 초안 작성·수락 승인은 어떤 프로세스 종료도 승인하지 않는다.
  - [B] G7 오류 처리 정책(G7_POOL_FAILURE_POLICY):
    - 후보 값: `G7_POOL_FAILURE_POLICY = ALLOW_STDLIB_OWN_WORKER_TERMINATION`. 이 값은 현재 승인되지 않았으며, 이 ERRATA가 ACCEPTED돼도 승인되지 않는다.
    - 의미(후보 값의 범위): G7에서 BrokenProcessPool이나 시작 barrier 실패가 나면 stdlib이 그 드라이버가 만든 pool의 worker를 종료할 수 있고, 드라이버가 끝나면 KILL_ON_JOB_CLOSE가 대상 job에 남은 프로세스를 종료할 수 있음을 받아들인다. 이 종료는 MoneyLab 코드가 호출하는 것이 아니며, 대상은 그 드라이버의 pool worker와 대상 job 안의 프로세스뿐이다. 발생하면 그 unit 결과를 쓰지 않고 STOP한다.
    - 이 정책은 MoneyLab 코드에 기존 프로세스나 다른 프로세스를 종료할 권한을 주지 않으며, R-4c A의 금지를 바꾸지 않는다.
    - 확정 방법: 사용자는 G7의 GATE_AUTHORIZATION 메시지(`GATE_AUTHORIZATION: BT4-FUTILITY-01 G7 WO@<commit>`)에 위 정책 줄을 정확히 함께 적는다. 새 UDR kind는 만들지 않는다. 그 메시지에 정확한 정책값이 없거나 값이 다르면 G7을 실행하지 않고 STOP한다.
    - 이 확인은 Claude가 G7 진입 전에 채팅의 승인 메시지로 하며(CLAUDE_REPORTED), 산출물 스키마(run_spec, manifest, execution.json)에는 기록하지 않는다.
    - 종료가 위 범위에 한정되는지와 G7의 실제 오류 처리 동작은 그룹 A 실패 경로·그룹 B·그룹 C 통합 테스트 전까지 CONDITIONAL이다.
  - [B] OPEN O-6: 같은 stdlib 동작이 G4c·G5·light 테스트의 다른 pool 사용에도 적용되는 범위와 그 승인 방식은 이 ERRATA에서 정하지 않으며 사용자 결정 대상으로 남긴다.
- R-4b worker 파일 정책:
  - [B] CORE worker(_rep_task)와 보정 worker(_sigma_task)는 계산 결과(와 시작 barrier의 pid 신호)만 부모에게 돌려준다. run 디렉터리, `g7-core-lock/`, `user-decisions/`, execution.json, manifest.json, SHA256SUMS를 포함해 어떤 파일도 쓰지 않는다. 모든 파일 쓰기는 드라이버가 한다.
- R-3 전체 예산 (O-3):
  - [B] 전체 예산 상태는 따로 저장하지 않는다. 매번 CORE run들의 execution.json에서 core_global_budget(ERRATA-004 R-6)으로 다시 계산한다. 비교는 T_CORE > 1.5 × (W_G6 / (12·η̂))이고 정확히 1.5배는 통과다. V-4 시간은 넣지 않는다.
  - [A] T_CORE는 같은 CODE_SHA의 모든 CORE run, 즉 E1·P0의 모든 시도(R-7 ATTEMPT 포함)의 세션 경과 합이다. WO:421(사전등록 §4.5 원문)의 "실행 중 누적 시간"은 재시도로 0으로 돌아가지 않는다(ERRATA-003 R-4 "재개해도 0으로 돌아가지 않는다"). 불완전한 시도는 기록된 하한으로 들어간다.
  - [B] 검사 시점: 드라이버 시작 시, 각 CORE run의 unit이 끝날 때마다, E1 완료 뒤 P0 시작 전. unit 단위 검사의 누적에는 다른 모든 CORE run(이전 시도 포함)의 기록된 누적을 더한다.
  - [A] 초과하면 그 unit까지 보존하고 STOP한다(WO:421). 예산 STOP 뒤에는 같은 CODE_SHA의 G7을 다시 시작하지 않는다. 진행은 WO:419의 계약 결정(새 ERRATA 또는 새 study)으로만 한다.
  - [A] TIME_ACCOUNTING_INCOMPLETE는 예산 PASS가 아니며, UDR을 포함한 어떤 결정으로도 PASS로 바뀌지 않는다(ERRATA-003 R-4).
  - [B] 비정상 종료 세션이 있는 CORE run의 재개는 target이 그 run인 RESUME_AFTER_INCOMPLETE UDR이 있을 때만 한다(ERRATA-003 R-4 "재개는 사용자 결정"). 재개는 계산을 이어가는 것만 허용하며 G8a 진입을 허용하지 않는다(R-6). 재개 중에도 하한 누적으로 1.5배 STOP을 적용한다.
- R-4 G7 실행 잠금(추가 전용):
  - [A] CLAUDE.md "보존"(우선순위 2)과 WO:115에 따라 ignored 산출물을 지우지 않는다. 잠금은 지우지 않는 추가 전용이다.
  - [B] 위치: 출력 루트의 디렉터리 `g7-core-lock/`. 허용 파일은 `NNNNNN.lock`, `NNNNNN.released`, `NNNNNN.abandoned`(6자리, 1부터), `NNNNNN.pool-PPPPPP.start`, `NNNNNN.workers-PPPPPP`(PPPPPP는 그 lock의 pool 일련번호, 6자리, 1부터 공백 없이)뿐이다. 모두 O_CREAT|O_EXCL로 만들고 fsync하며, 쓰인 뒤 고치거나 지우지 않는다(추가 전용).
  - [B] pool 의도 기록(E-POOL-START, `n.pool-p.start`): pool을 만들기 전에 쓰고 fsync까지 끝낸다. 쓰지 못하면 pool을 만들지 않고 STOP한다. 필드(canonical JSON): schema_version, run_id, unit_id(cell, unit 번호), pool_id(파일명의 p와 같음), driver_pid, driver_creation_time, lock_sha256, planned_max_workers, written_utc(참고값).
  - [B] worker 기록(E-WORKERS, `n.workers-p`): 시작 barrier 6단계의 고정 순서((A)·(B) 검증 → O_EXCL 생성 → 내용 → fsync → release)로 쓴다. 쓰지 못하면 release하지 않고 STOP한다. 필드(canonical JSON): schema_version, run_id, unit_id, pool_id(파일명의 p와 같음), driver_pid, driver_creation_time, lock_sha256, python_version(sys.version), expected_worker_count(min(w, 작업 수)), verified_worker_count(expected와 같아야 하며, 다르면 기록하지 않고 STOP), workers(각 worker의 pid와 creation_time 목록), target_job_membership_verified(검증 뒤에만 쓰므로 항상 true, 감사용), written_utc(참고값). 예산 수치는 넣지 않는다. release 여부는 기록하지 않으며 판정에서도 release됐다고 가정한다.
  - [A] 기록이 없다는 사실은 worker가 생성되지 않았다는 증거가 아니다. E-POOL-START가 없거나, E-POOL-START만 있고 E-WORKERS가 없거나, 기록이 손상·일부·불일치이면 그 pool의 worker 존재·종료를 알 수 없는 것으로 본다.
  - [B] 획득:
    1. 디렉터리 상태를 검증한다(아래 "비정상 상태").
    2. 가장 큰 번호 n의 `.lock`에 짝인 `.released`나 `.abandoned`가 없으면 STOP_FOR_USER_DECISION이다.
    3. 그렇지 않으면 `n+1.lock`을 O_CREAT|O_EXCL로 만든다. 실패하면 재시도 없이 STOP이다.
    4. 같은 파일 디스크립터로 내용(canonical JSON: 무작위 소유 토큰, pid, 드라이버 프로세스 시작 시각, 시작 UTC, CODE_SHA, 대상 run_id, 대상 job 사용, 할당 전 기존 job 소속 여부, 대상 job 정책 readback 성공, 정확한 sys.version 문자열, host_id(computer_name, machine_guid), boot_identity(획득 시점의 부팅 시각 판독 S1·S2, 아래 E-BOOT 판정))을 쓰고 fsync한 뒤 닫는다. 예산 수치는 넣지 않는다. host_id나 boot_identity를 읽지 못하면 lock을 쓰기 전에 STOP한다.
  - [B] 유효한 lock: 내용이 canonical JSON이고 필드가 정확히 위와 같다. 비었거나 일부만 쓰였거나 읽을 수 없는 lock은 유효하지 않다.
  - [B] 소유권 확인(연구용 CORE 경로에서 코드로 강제): 드라이버와 연구용 core 모드의 run_units는 잠금 핸들(번호와 lock 바이트 sha256)을 필수 인자로 받는다. 다음 시점마다 아래 세 조건과 "execution.json의 마지막 세션이 이 프로세스가 연 세션과 같음"을 확인하고, 어긋나면 쓰기 전에 STOP_FOR_USER_DECISION이다.
    - 시점: run 시작, 각 unit 파일 쓰기 직전, 각 execution.json 쓰기 직전
    - `n.lock`의 바이트 sha256이 핸들과 같다.
    - `n.released`와 `n.abandoned`가 없다.
    - n보다 큰 번호의 파일이 없다.
  - [B] 해제: 정상 종료, 예산 STOP, 처리된 예외 때 소유 토큰과 lock sha256을 담은 `n.released`를 O_EXCL로 만들고 fsync한다. `n.lock`은 지우지 않는다.
  - [B] abandon(NON_BOOT_ABANDON = DISALLOWED): 자동으로 하지 않는다. 비정상 종료된 lock(짝 없는 `n.lock`)의 `n.abandoned`(UDR sha256, E-BOOT 근거, UTC)는 다음 둘이 모두 있을 때만 O_EXCL로 만든다.
    1. target이 그 lock 번호와 현재 lock 바이트 sha256인 LOCK_ABANDON UDR
    2. (E-BOOT) 아래 "E-BOOT 판정"이 성립한다: host_id가 같고, lock 획득 뒤 부팅 세션이 바뀌었으며, 현재 부팅 시각이 lock 파일과 그 lock의 모든 `pool-p.start`·`workers-p` 파일의 수정 시각보다 뒤다(그 이전 프로세스는 드라이버·worker·자손을 포함해 모두 종료됨).
    - E-BOOT는 abandon을 허용하는 유일한 종료 근거다. 사용자 결정, UDR, 아래 조사 증거는 E-BOOT를 대신하지 못한다. 이 ERRATA는 E-BOOT의 정의와 UDR 조건을 완화하지 않는다. 재부팅은 자동으로 실행하지 않으며 사용자가 한다.
    - 다음 경우 모두 E-BOOT 없이는 abandon할 수 없다: E-POOL-START 누락, E-WORKERS 누락, 기록 손상·일부·불일치, worker 종료 확인 불가, 프로세스 트리 단절 가능성, 이전 worker의 생존 여부 불명, 드라이버 비정상 종료.
  - [B] 상태 조사 증거(감사·진단 전용, abandon 근거 아님): abandon을 신청하기 전과 재부팅 전후의 상태를 판단하고 기록하는 데만 쓴다.
    - 증거의 구분(서로 대신하지 않는다):
      - 준비 증거(lock에 기록): 대상 job 생성, 정책 readback, 드라이버의 대상 job 소속, sys.version.
      - pool 증거: E-POOL-START(pool 의도), E-WORKERS(검증된 worker와 barrier 통과).
      - 현재 상태 조사: E-PID, E-WORKERS 종료 조회, E-TREE.
      - 준비·pool 증거와 "barrier 없이는 계산 없음"이라는 코드 불변식은 그 worker들이 대상 job 정책 아래 있었다는 사실일 뿐이며, 비정상 종료 뒤 worker가 실제로 종료됐다는 증명이 아니다.
    - (E-PID 조사) lock이 유효하고 host_id가 같을 때, 그 pid의 프로세스가 없거나 같은 pid라도 시작 시각이 lock 기록과 다른지.
    - (E-WORKERS 조사) 모든 `pool-p.start`에 짝인 유효한 `workers-p`가 있는지, 기록된 각 worker의 pid가 없거나 같은 pid라도 생성 시각이 기록과 다른지.
    - (E-TREE 조사) 시작점은 드라이버 pid와 기록된 모든 worker pid(이미 죽은 것 포함)이며, 각 시작점의 (pid, 생성 시각)을 함께 쓴다. 프로세스 스냅샷(CreateToolhelp32Snapshot)에서 시작점을 부모로 하고 생성 시각이 그 시작점의 생성 시각 이후인 프로세스를 출발점으로, 같은 규칙으로 재귀적으로 찾은 자손 중 살아 있는 것이 있는지. pid가 재사용된 다른 프로세스의 자식이 섞이면 남은 것으로 본다. 생성 시각을 읽을 수 없으면 확인 불가다. 스냅샷은 두 번 뜨며, 두 번 일치해도 원자적 증거가 아니다.
    - E-TREE의 한계(명시): Windows는 고아 프로세스의 부모 pid를 바꾸지 않으므로, 기록되지 않은 중간 프로세스가 먼저 끝나면 그 아래로는 재귀가 닿지 않는다(트리 단절). 스냅샷은 순간 일관성이 없다. E-TREE는 단독으로 abandon을 허용하지 않는다.
    - 조사에서 살아 있는 드라이버(시작 시각 일치), 기록된 worker, 자손이 보이면 abandon을 신청하지 않는다(STOP). 그 경우에도 프로세스에 신호를 보내지 않는다([C]: Windows에서 os.kill은 프로세스를 종료하므로 쓰지 않는다).
  - [B] E-BOOT 판정(계약 후보: 아래 판독 방법의 실제 Windows 동작은 UNVERIFIED다). 다음이 모두 성립할 때만 E-BOOT가 성립한다. 하나라도 읽기 실패, 불성립, 확인 불가이면 E-BOOT는 불성립이며 STOP이다(짝 없는 lock은 그대로 STOP_FOR_USER_DECISION).
    1. host 식별: host_id는 computer_name(GetComputerNameExW, ComputerNamePhysicalNetBIOS)과 machine_guid(레지스트리 HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid, winreg 읽기 전용, 64비트 view)의 쌍이며, 이 ERRATA의 모든 host 비교(R-2, E-PID 조사, E-BOOT)는 이 host_id로만 한다. 현재 host_id의 두 값이 lock의 host_id와 모두 같아야 한다. 유효하지 않은 lock(빈·부분·손상)은 host_id와 boot_identity를 읽을 수 없으므로 E-BOOT가 성립하지 않는다.
    2. 부팅 시각 판독(두 가지):
       - S1: NtQuerySystemInformation(SystemTimeOfDayInformation)의 BootTime(UTC, 100 ns 단위).
       - S2: GetSystemTimePreciseAsFileTime() − GetTickCount64() × 10⁴(부팅 뒤 경과, 절전 시간 포함).
       - 둘 중 하나라도 실패하면 STOP이다. |S1 − S2| > 120 s이면 시계 변경 의심으로 STOP이다.
       - [A] S1과 S2는 모두 같은 OS의 시계와 부팅 뒤 경과에 기대므로 서로 독립 증거가 아니다. 두 값의 일치는 판독 일관성 검사일 뿐이며, 그것만으로 E-BOOT 증거가 확보된 것으로 판정하지 않는다.
    3. 부팅 세션 변경: 현재 S1 − lock boot_identity의 S1 > 120 s이고, 현재 S2 − lock boot_identity의 S2 > 120 s다.
    4. 파일 수정 시각 비교: 대상은 그 lock 번호 n의 `n.lock`, 모든 `n.pool-p.start`, 모든 `n.workers-p`다. 각 파일의 mtime(os.stat st_mtime_ns, UTC)을 모두 읽을 수 있어야 하고, 현재 S1과 S2가 모두 max(mtime)보다 엄격하게 크다(같으면 불성립). 어떤 mtime이든 현재 시각보다 뒤이면(미래 mtime) STOP이다. 여기서 현재 시각은 위 2의 S2 계산에 쓴 같은 GetSystemTimePreciseAsFileTime() 판독값이다.
    5. 기록: `n.abandoned`에 LOCK_ABANDON UDR sha256, host_id 비교 결과, lock의 boot_identity, 현재 S1·S2, 대상 파일별 mtime_ns, 판정 UTC를 canonical JSON으로 쓴다.
    - [B] 판독 경로 검증 전 제한: AC-J13의 FAKE_TEST와 이 host에서의 부팅 시각 읽기 전용 확인(R-9 RB-1, 별도 승인)을 통과하기 전에는 E-BOOT를 성립으로 판정하지 않는다. 그 전에 생긴 짝 없는 lock은 STOP_FOR_USER_DECISION으로 남는다.
    - [A] 한계(명시):
      - 관리자 권한으로 시계, 파일 mtime, 레지스트리, 컴퓨터 이름을 바꿀 수 있다. E-BOOT는 실수와 비정상 종료를 다루는 장치이며 의도적 조작을 막지 못한다.
      - 시계를 바꿨을 때 S1(BootTime)이 어떻게 조정되는지는 UNVERIFIED다. 시계 변경이 의심되면(위 2의 불일치) STOP한다.
      - NtQuerySystemInformation의 이 정보 클래스가 공개 문서상 안정 인터페이스로 보장되는지는 UNVERIFIED다.
      - 절전·최대 절전에서 돌아와도 부팅 세션은 바뀌지 않으므로 E-BOOT가 불성립한다(프로세스가 살아 있을 수 있으므로 안전한 방향).
      - 빠른 시작(Fast Startup)으로 끄고 켠 경우 부팅 시각이 갱신되는지는 UNVERIFIED다. 갱신되지 않으면 불성립이며, 사용자는 "다시 시작"으로 재부팅해야 한다.
    - [A] E-BOOT 성립은 abandon의 필요조건 하나일 뿐이며, LOCK_ABANDON UDR(위 1)이 함께 있어야 한다. NON_BOOT_ABANDON = DISALLOWED는 그대로이고, 재부팅은 자동으로 하지 않는다.
  - [B] E-BOOT를 쓸 수 없는 경우는 STOP이다.
    - 다른 host의 lock(host_id 불일치): STOP이며 이 host에서 abandon할 수 없다. 그 host에서만 처리할 수 있다.
    - 부팅 세션이 바뀌지 않았거나 부팅 시각이 lock·pool 기록의 수정 시각보다 뒤가 아님: 재부팅 전까지 STOP이다.
    - 부팅 시각, host 식별 정보, 파일 수정 시각 중 어느 것이라도 읽을 수 없음: 확인 불가로 STOP이다.
    - 유효하지 않은 lock: 이 ERRATA 안에서는 풀 수 없다(STOP_FOR_USER_DECISION). 처리는 새 ERRATA로만 한다.
  - [B] 비정상 상태(모두 STOP_FOR_USER_DECISION): 허용 이름이 아닌 파일, 번호 공백(1..max 중 빠진 lock), 짝 lock이 없는 released·abandoned·workers 기록, 같은 번호의 released와 abandoned 동시 존재, released의 lock sha256이 그 lock과 다름, abandoned의 UDR이 없거나 target이 다름, 짝 없는 lock이 둘 이상, pool 일련번호 공백, `pool-p.start` 없는 `workers-p`, `pool-p.start`와 `workers-p`의 run_id·unit_id·pool_id·driver_pid·driver_creation_time·lock_sha256 불일치, 파일명과 pool_id 불일치, 기록의 lock sha256이 그 lock과 다름.
  - [B] 계약 수준 경쟁·crash 검토:
    - 같은 n+1을 노리는 두 프로세스는 O_EXCL로 하나만 통과한다. 다른 번호를 동시에 얻을 수 없다(n+2는 n+1의 짝이 있어야 함).
    - 생성 직후나 내용 쓰기 중 crash는 유효하지 않은 짝 없는 lock을 남긴다. 그 lock은 host_id와 boot_identity가 없어 E-BOOT가 성립하지 않으므로 이 ERRATA 안에서는 풀리지 않는다(STOP_FOR_USER_DECISION, 새 ERRATA로만 처리).
    - released 기록 전 crash는 짝 없는 lock을 남긴다. 그 run은 TIME_ACCOUNTING_INCOMPLETE일 수 있다(ERRATA-003 R-4).
    - 짝 없는 lock은 어떤 경우에도 E-BOOT 없이 abandon되지 않으므로, 이전 시도의 드라이버·worker가 남은 채 새 시도가 시작되는 상황은 계약상 생기지 않는다(WO:45).
    - 상황별(모두 abandon은 E-BOOT만): lock 획득 전 종료(lock 없음, pool 없음), job 준비 뒤 lock 획득 실패(O_EXCL STOP, 짝 없는 lock 없음), E-POOL-START 전 종료(pool 기록 없음, 기록 없음을 pool 없음의 증거로 쓰지 않음), E-POOL-START 뒤·E-WORKERS 전 종료(기록되지 않은 worker가 있을 수 있음), E-WORKERS 뒤 계산 중·execution.json 기록 전 종료(시간 기록은 TIME_ACCOUNTING_INCOMPLETE), 이전 worker가 남은 채 재시작 시도(조사에서 생존이 보이면 STOP, 남은 길은 재부팅 뒤 E-BOOT).
    - 남는 위험: 로컬 파일 시스템의 O_EXCL 원자성, OS가 보고하는 프로세스 시작 시각·부팅 시각(S1·S2, UNVERIFIED)·파일 mtime·부모 pid의 정확성, Windows job 정책의 동작을 전제로 한다.
- R-5 V-4 산출물 (O-4):
  - [B] V-4는 별도 run 디렉터리에 둔다: `v4.json`(결정적), `execution.json`(비결정적, V-4 실제 시간), `SHA256SUMS`(`v4.json`만).
  - [B] `v4.json`: 스키마, study, evidence, years = 4,000, seed parts ("FUTDIAG", "v4eval")와 seed, edge = e_cal과 출처(config [mcv06_inputs]), SR_eval, K = 40 batch Sharpe와 길이, 코드 신원(research_identity), 사용한 UDR sha256 목록. canonical JSON이며 worker 수와 무관하다.
  - [A] V-4 시간은 CORE W, G6 예상 wall-clock, R-3 CORE 누적에서 제외한다(ERRATA-003 R-3, ERRATA-004 R-3·R-6).
  - [B] 재실행: `v4.json`과 SHA256SUMS가 있고 검증되면 다시 계산하지 않는다. `v4.json`만 있으면 다시 계산해 바이트가 같아야 SHA256SUMS를 쓴다. 다르면 STOP한다. 손상은 STOP이고 고치지 않는다.
  - [A] K = 40 batch 계산 불가는 STOP이다(WO:454).
- R-6 G8a 산출물 (O-5):
  - [A] WO:73의 "run 디렉터리"는 셀별 run(R-1)에서 G8a 전용 판정 run 디렉터리를 뜻한다.
  - [B] 판정 run 디렉터리: `decision_summary.json`(결정적, canonical)과 `SHA256SUMS`(그 파일만).
  - [B] 판정 대상 집합: E1·P0·V-4 각각에 대해 같은 stage·part의 시도 중 가장 큰 attempt 번호의 run 하나다(접미사 없음 = 1). 그보다 작은 모든 시도는 run_id, 상태(COMPLETE/INCOMPLETE/손상), 사용 UDR sha256과 함께 `decision_summary.json`의 provenance에 기록한다. 대상 run을 다른 규칙으로 고르지 않는다.
  - [B] `decision_summary.json`은 기존 판정 함수(decision_summary, label_v1, label_mcnemar, label_v4, Holm)의 결과와 입력 provenance를 담는다: 대상 E1·P0 run의 run_spec·run_inputs·manifest·SHA256SUMS sha256, `v4.json` sha256, G6 요약 sha256, calibration sha256, CODE_SHA, 모든 시도 목록, 사용된 모든 UDR sha256.
  - [B] G8a 진입 조건(모두 충족해야 함, 아니면 G8a를 실행하지 않고 STOP):
    - 대상 E1·P0 run verify_run COMPLETE, pilot g6 VERIFIED, V-4 SHA256SUMS 검증, 기록된 UDR 파일 재검증(R-0)
    - 두 run manifest의 G6 section이 서로 같고 pilot에서 다시 만든 section과 같음, calibration sha256이 각 run_inputs provenance와 같음
    - 이전 시도의 완료 unit이 대상 run의 같은 unit과 바이트가 같음(결정적 재현)
    - 같은 CODE_SHA의 모든 CORE run(모든 시도)의 time_accounting이 COMPLETE
    - core_global_budget(모든 시도 포함)이 초과가 아님(budget_pass_allowed = true)
  - [B] TIME_ACCOUNTING_INCOMPLETE가 어느 시도에든 남아 있으면 G8a 최종 판정을 실행하지 않는다. UDR로 이 조건을 바꾸거나 우회할 수 없다(R-0). RESUME_AFTER_INCOMPLETE UDR은 CORE 재개만 허용하며 G8a 진입과 구분된다.
  - [A] 사전등록 판정 기준과 다중성은 바꾸지 않는다. 재실행하면 다시 계산하고 바이트가 다르면 STOP한다.
- R-7 run_id와 재시도(ATTEMPT):
  - [B] 출력 루트(WO:245)의 바로 아래 디렉터리 이름은 `<stage>-<part>-<CODE_SHA 앞 12자리>[-attempt<k>]`다.
    - G4c: `g4c-smoke-<sha12>`, `g4c-cal-<sha12>`
    - G5: `g5-cal-<sha12>`, `g5-pilot-<sha12>`
    - G7: `g7-E1-theta0.7-<sha12>`, `g7-P0-theta0.7-<sha12>`, `g7-v4-<sha12>`
    - G8a: `g8a-<sha12>`
    - 고정 디렉터리: `g7-core-lock`(R-4), `user-decisions`(R-0)
  - [B] 접미사가 없으면 첫 시도다. `-attempt<k>`(k ≥ 2)는 ATTEMPT UDR(target의 new가 그 run_id)이 있을 때만 쓴다. k는 직전 시도 번호 + 1이어야 하며 사용자가 승인 줄에 적는다. 자동으로 만들거나 늘리지 않는다.
  - [B] 재시도 허용 사유는 둘뿐이다: ABNORMAL_TERMINATION(비정상 종료), INTEGRITY_FAILURE(verify STOP을 일으킨 손상). 다음 경우에는 재시도할 수 없다: 예산 STOP 뒤(R-3), G8a 실행 뒤, 결과·판정·효과 수치를 이유로 한 경우.
  - [A] 같은 seed와 코드에서 record는 결정적이므로 재시도로 결과가 달라지지 않는다. 이전 시도의 완료 unit은 새 시도의 같은 unit과 바이트가 같아야 하며 다르면 STOP한다(R-6).
  - [A] 이전 시도의 산출물은 그대로 보존하며 덮어쓰거나 지우지 않는다. 같은 이름의 디렉터리에 다른 입력이 오면 STOP한다(write-or-compare).
  - [A] 재시도의 시간은 전체 예산에서 빠지지 않는다(R-3). 따라서 이전 시도가 TIME_ACCOUNTING_INCOMPLETE이면 재시도로 G8a 조건이 충족되지 않는다. 재시도는 시간 기록이 완전한 손상 복구(INTEGRITY_FAILURE)에서만 G8a로 이어질 수 있다.
  - [B] 진입점은 이름이 단계·part·CODE_SHA·ATTEMPT UDR과 맞는지 확인하고, 아니면 STOP한다([C]). 전체 CODE_SHA는 run_spec·v4.json·decision_summary.json에 기록되며 검증은 내용으로 한다.
- R-8 P0 conf 검사 (WO:455):
  - [A] WO:455 "pilot P0 conf의 V0 기각률이 α ± 3 SE를 벗어남(구현 결함 의심)"은 STOP 조건이다. 대상은 G5 pilot의 P0-θ0.7 conf 창 V0 지시변수 I = 1{p_V0 ≤ α}(DC8)이다.
  - [B-STAT] 다음은 기존 계약에서 추론한 것이 아니라 이 ERRATA가 새로 정하는 통계 계약이다.
    - α = config [policy] primary_alpha(0.05)
    - R = G5 pilot run_spec.reps(연구 pilot은 200)
    - p̂_conf = (P0 conf에서 I = 1인 pilot 복제 수) / R
    - SE = √(α(1−α)/R) (귀무 기준)
    - PASS 조건: |p̂_conf − α| ≤ 3·SE. 경계값은 PASS다. 반올림하지 않는다. 그 밖에는 STOP이다.
  - [A] p̂_conf는 pilot unit record의 V0 p값만으로 누구나 다시 계산할 수 있다.
  - [B] 기록: P0 conf 기각률은 V-8 효과 D8 = r(f12) − r(conf)의 구성 요소이므로 G6 요약, 채팅 보고, 어떤 산출물에도 수치를 쓰지 않는다(DC11, WO:69). G6 요약에는 `P0_CONF_CHECK`: "PASS" 또는 "STOP"만 기록한다.
- R-9 통합 테스트(IT) 구성과 실행 승인:
  - [B] 대응표:

    | IT | 내용 | 대응 AC |
    |---|---|---|
    | IT-1 | 중첩 job 할당과 정책 readback | AC-J4, AC-J1 |
    | IT-2 | worker 부모-자식 관계와 대상 job 소속 | AC-J1, AC-J2 |
    | IT-3 | 시작 barrier(3a 정상, 3b ready timeout, 3c initializer 예외 → BrokenProcessPool) | AC-J3 |
    | IT-4 | job 핸들 비상속 | AC-J5 |
    | IT-5 | 드라이버 강제 종료 뒤 KILL_ON_JOB_CLOSE와 조사 증거 실측 | AC-J7 |
    | IT-6 | 예상 밖 subprocess STOP [FAKE_TEST]: pool이 열린 동안 대상 job pid 목록이나 스냅샷에 검증된 worker가 아닌 프로세스가 나타나면, release 전이면 release 없이, release 뒤면 다음 쓰기 전에 STOP하고 unit을 쓰지 않음 | (AC-J2의 예상 밖 PID 조항, AC-J6) |
    | IT-7 | E-POOL-START 기록 순서·실패 주입 [FAKE_TEST] | AC-J9, AC-J11 |
    | IT-8 | E-WORKERS 기록 순서·실패 주입 [FAKE_TEST] | AC-J10 |

  - [B] AC-J9·AC-J10의 FAKE와 통합 부분 분리:
    - FAKE_TEST(IT-7·IT-8): 실패 주입 검증. O_EXCL 충돌, 생성 실패, write 실패·부분 쓰기, fsync 실패 각각에서 STOP하고 pool을 만들지 않거나 release하지 않는지, 호출 순서, 필드, 비정상 상태. 실패는 FAKE로만 주입한다.
    - INTEGRATION_TEST(IT-2·IT-3a의 부수 확인, 위 대응표의 주 AC에 더해 확인): 아래 "테스트 전용 실제 파일 기록"으로 실제 E-POOL-START·E-WORKERS 파일을 쓰는 성공 경로 검증. 실패 주입은 하지 않으며, 실제 기록 중 실패가 나면 그 자체가 테스트 실패(STOP)다.
      - A. E-POOL-START: pool 생성 전에 O_CREAT|O_EXCL 생성, write 완료, fsync 완료.
      - B. E-WORKERS: worker 생성과 (A)·(B) 소속 검증 완료, verified_worker_count = expected_worker_count 확인, O_CREAT|O_EXCL 생성, write 완료, fsync 완료, 그 뒤에만 barrier release.
      - C. 일관성: 기록된 pid와 실제 worker pid 일치, 기록된 생성 시각과 실제 worker 생성 시각 일치, 기록된 worker 수와 실제 수 일치, 예상 밖 worker가 보이면 STOP.
    - 판정 근거(서로 다른 출처를 함께 쓴다):
      - 드라이버 이벤트 순서: 테스트 드라이버가 stdout으로 내는 단계 표지(E-POOL-START fsync 완료 → pool 생성 → 소속 검증 완료 → E-WORKERS fsync 완료 → release)와 각 단계의 perf_counter 값.
      - 파일 쪽 근거: pytest(부모)가 실행 뒤 두 파일을 읽기 전용으로 읽어 canonical JSON·필드·파일명과 pool_id 일치를 확인하고, E-POOL-START의 mtime ≤ 모든 worker 생성 시각, E-WORKERS의 mtime ≤ 각 worker가 barrier를 통과한 시각(worker가 계산 결과와 함께 돌려주는 GetSystemTimePreciseAsFileTime 값)임을 확인한다. mtime 해상도 때문에 비교는 ≤로 한다.
      - worker 쪽 근거: 각 worker가 돌려주는 자기 pid와 생성 시각(GetProcessTimes)이 E-WORKERS 기록과 같다.
    - [A] 실제 파일 기록 검증은 OS가 생성·write·fsync 성공을 보고했고 그 순서가 지켜졌다는 사실까지만 보인다. 전원 장애 뒤의 영속성(디스크 캐시, 디렉터리 항목 영속성 포함)은 증명하지 않는다.
  - [B] 테스트 전용 실제 파일 기록(IT-2·IT-3a에만 적용, 아래 조건을 모두 만족할 때만 허용):
    - 디렉터리: 테스트마다 pytest가 만드는 독립 임시 디렉터리(tmp_path, 시스템 임시 폴더의 pytest 기본 위치) 하나다. `--basetemp`는 쓰지 않는다(그 옵션은 시작 시 기존 내용을 지운다).
    - 분리 확인(드라이버 시작 전, 하나라도 어긋나면 STOP): 그 디렉터리의 실제 경로(realpath)가 저장소 worktree, `data/`, 연구 출력 루트(WO:245), 어떤 `g7-core-lock/`, `user-decisions/`, scratchpad 디렉터리의 안이나 위가 아니고, 시작 시 비어 있다.
    - 쓰기 범위: 테스트 드라이버만 쓰며 worker는 쓰지 않는다(R-4b). 허용 파일은 그 디렉터리 바로 아래의 `000001.pool-PPPPPP.start`와 `000001.workers-PPPPPP`뿐이다. lock 파일은 만들지 않으며 lock_sha256 필드는 테스트 전용 고정값을 쓴다. 각 쓰기 직전에 대상 경로의 realpath가 그 디렉터리 바로 아래인지 확인하고, 아니면 STOP한다. 디렉터리 밖 쓰기는 금지다.
    - 기록 방법: 운영 G7과 같은 기록 함수를 디렉터리 인자만 바꿔 호출한다(테스트 전용 분기나 mock 없음). 실제 os.open(O_CREAT|O_EXCL|O_WRONLY|O_BINARY), 실제 write, 실제 os.fsync를 쓴다.
    - 실패 처리: 생성 실패(기존 파일 포함), write 실패·부분 쓰기, fsync 실패는 모두 STOP이다. 실패하면 E-POOL-START는 pool을 만들지 않고, E-WORKERS는 release하지 않는다. 기존 파일은 덮어쓰지 않는다(O_EXCL).
    - barrier 순서: worker 소속 검증이 끝나기 전과 E-WORKERS의 fsync가 끝나기 전에는 barrier를 해제하지 않는다(R-4a 시작 barrier 6단계와 같다).
    - 정리와 증거 보존: MoneyLab 테스트 코드는 어떤 파일도 지우지 않는다(테스트 디렉터리 안과 밖 모두). 테스트가 끝나면 pytest(부모)가 두 파일의 경로와 sha256을 출력에 남긴다. 실패하면 전체 테스트를 STOP하고 그 디렉터리 경로를 보고하며, 다음 pytest 실행 전에 사용자가 보존 방법을 정한다. pytest가 자기 기본 위치의 오래된 임시 디렉터리를 정리하는 동작(설치된 pytest 버전의 보존 정책, UNVERIFIED)은 MoneyLab 코드의 삭제가 아니며, 실패 증거는 그 정리 전에 보고로 남긴다.
    - 프로세스 종료 가능성과 승인은 그룹 A 정책(R-4c B4)을 그대로 따른다. 기존 프로세스에는 종료·신호를 보내지 않는다. 테스트 실패는 전체 STOP이다.

  - [B] 실행 승인 그룹(그룹마다 별도 실행 승인이 필요하다. 한 그룹의 승인이나 결과는 다른 그룹의 승인이 아니다):
    - 그룹 A: IT-1, IT-2, IT-3a, IT-4. 테스트 전용 job과 프로세스를 만든다. 정상 경로에서는 의도적인 worker 종료를 일으키지 않는다. 실패 경로에서는 R-4c B4의 종료(stdlib 내부 worker 종료, KILL_ON_JOB_CLOSE)가 일어날 수 있다. 그룹 A 실행을 요청할 때 이 가능성을 따로 고지하며, 이 가능성을 포함한 명시적 실행 승인 전에는 그룹 A를 실행하지 않는다.
    - 그룹 B: IT-3b, IT-3c. R-4c B1(stdlib 오류 처리에 따른 테스트 전용 worker 종료)을 포함한다.
    - 그룹 C: IT-5. R-4c B2·B3(테스트 드라이버 강제 종료와 KILL_ON_JOB_CLOSE 작동)을 포함한다.
    - 그룹 D: IT-6, IT-7, IT-8. FAKE_TEST이며 프로세스·job·ctypes를 쓰지 않는다.
    - 읽기 전용 확인 RB-1(그룹 밖, 별도 승인): 이 host에서 E-BOOT의 S1·S2와 host_id 판독만 하고 결과를 채팅으로 보고한다. 프로세스·job·파일을 만들지 않는다.
  - [B] 공통 실행 규칙:
    - IT 코드는 ALLOWED_FILES(G3)의 커밋 대상 파일에만 둔다(WO:118, 임시 스크립트 금지). 실패 주입은 테스트 파일에만 두고 운영 코드에는 hook을 넣지 않는다.
    - pytest 프로세스는 대상 job에 넣지 않는다. 테스트 드라이버를 별도 하위 프로세스로 띄우고, 그 드라이버가 자기 자신을 테스트 전용 대상 job에 넣는다.
    - worker는 파일을 쓰지 않는다. 테스트 드라이버는 위 "테스트 전용 실제 파일 기록"(IT-2·IT-3a)의 경우를 빼고 파일을 쓰지 않는다. 결과는 stdout으로 전달한다. lock 디렉터리, `data/`, 연구 run, 네트워크에 접근하지 않는다. G7, MC, 공식 G4c smoke를 실행하지 않는다.
    - 그룹 실패는 그 자리에서 STOP이며 다음 그룹으로 진행하지 않는다.
  - [B] timeout: MoneyLab 테스트 코드는 timeout만을 이유로 어떤 프로세스도 직접 종료하지 않고(기존 프로세스와 테스트 프로세스 모두), 승인되지 않은 종료 API를 호출하지 않는다. 시간이 초과되면 전체 테스트를 STOP하고, 남은 테스트 관련 프로세스의 pid·생성 시각·부모 pid·실행 파일 이름을 읽기 전용으로 보고하며, 처리는 사용자가 결정한다. 기존 프로세스는 종료하지 않는다.
  - [A] 그 timeout 이전이나 이후에 stdlib 내부 worker 종료나 KILL_ON_JOB_CLOSE에 의한 종료가 일어났다면(R-4c [A]), 그 사실을 보고에 그대로 적는다.

## ATTEMPT_BUDGET_OPTIONS (검토 기록, 계약 아님)

- OPTION I(이 ERRATA가 채택): 모든 시도의 누적을 전체 CORE 예산에 포함한다. WO:421과 사전등록 §4.5 원문("실행 중 누적 시간이 예상의 1.5배를 넘으면 STOP")과 ERRATA-003 R-4("재개해도 0으로 돌아가지 않는다")에 직접 부합한다. 결과: G7 중 비정상 종료가 한 번이라도 나면 그 CODE_SHA로는 G8a를 실행할 수 없다.
- OPTION II(채택하지 않음): 시도별로 예산을 평가하고 이전 시도의 계산량은 따로 보고한다. 재시도로 누적이 0으로 돌아가므로 WO:421·사전등록 §4.5의 STOP 기준을 실질적으로 완화한다. 사전등록 변경에 해당할 수 있으며(WO:85), 그렇다면 이 ERRATA가 아니라 새 Work Order·사전등록으로만 가능하다.

## RATIONALE

RATIONALE:
- R-0: 사용자 결정을 원문 승인 줄에 결속해 재사용·전용을 막고, 기록이 PASS나 기준 완화를 만들 수 없게 한다.
- R-1: 셀별 run은 run_spec 스키마를 바꾸지 않고 DC12의 셀별 R_c를 정확히 지킨다.
- R-2·R-3: 단일 호스트·단일 프로세스 순차 실행은 WO:418의 12 worker 예상과 맞고, 전체 누적(모든 시도 포함)을 기존 함수로 다시 계산해 별도 상태 없이 WO:421을 그대로 적용한다.
- R-4: 파일만으로는 실행 중과 비정상 종료를 구분할 수 없으므로 O_EXCL 잠금을 쓰고, 프로세스 조사로는 드라이버와 모든 자손의 종료를 증명할 수 없으므로 abandon에는 LOCK_ABANDON UDR과 재부팅 근거(E-BOOT)를 요구한다(NON_BOOT_ABANDON = DISALLOWED). 보존 규칙 때문에 지우지 않는다.
- R-4a·R-4b: Windows는 부모가 죽어도 자식을 끝내지 않고, 실측 환경에서 이미 SILENT_BREAKAWAY_OK가 켜진 외부 job이 관찰됐다. 그래서 worker가 "어떤 job"이 아니라 드라이버가 만든 대상 job에 속하는지를 대상 job 핸들로 드라이버가 직접 확인하고(정책 플래그만으로는 신원을 확정하지 않음), 확인 전에는 계산을 시작하지 않는다. worker는 파일을 쓰지 않으므로 검증되지 않은 계산 결과도 산출물이 되지 않는다. 비정상 종료 뒤의 worker 종료는 소속 사실, 코드 불변식, 기록의 유무, 프로세스 조사로 증명할 수 없으므로(트리 단절, 기록되지 않은 worker 가능성), 비정상 종료된 lock의 abandon은 재부팅(E-BOOT)으로만 허용한다. pool 의도 기록과 worker 기록은 조사·감사 증거로 남긴다. E-BOOT 판독은 같은 OS 시계에 기대는 두 값을 쓰므로 일치를 독립 증거로 보지 않고, lock에 기록한 부팅 식별 정보와의 비교와 판독 경로 검증(RB-1, AC-J13) 뒤에만 쓴다.
- R-4c: stdlib은 오류 처리 중 자기 worker를 종료할 수 있으므로(PREVIOUSLY_OBSERVED), MoneyLab 코드의 종료 행위 금지와 stdlib·OS가 일으키는 종료(별도 승인 대상)를 분리해 승인 범위를 명확히 한다. G7에서는 그 종료 가능성의 수용을 G7_POOL_FAILURE_POLICY로 G7 Gate Authorization에서 명시적으로 확정하게 하여, UDR 계약을 바꾸지 않고 승인 근거를 남긴다.
- R-9: 통합 테스트를 위험 수준별 그룹으로 나눠 프로세스 종료를 포함하는 테스트가 다른 테스트의 승인에 묻혀 실행되지 않게 하고, timeout이 종료 사유가 되지 않게 한다.
- R-5·R-6: G1(g6/)과 같은 원칙을 V-4와 판정에 적용하고, 모든 시도의 시간 기록이 완전하고 예산 이내일 때만 판정한다.
- R-7: 재시도를 사용자 결정과 제한된 사유로만 허용하고, 결정성으로 결과 선택을 원천적으로 막는다.
- R-8: WO:455의 빈칸을 [B-STAT]로 명시적으로 정하고 효과 수치를 남기지 않는다.

## BASELINE_IMPACT

BASELINE_IMPACT:
- Ce 커밋은 이 파일 하나만 추가한다. Work Order, ERRATA-001~004, 사전등록, config, MC-V06 `_SOURCE_FILES`는 바뀌지 않는다.
- [C] 구현 대상(G3 범위): UDR 쓰기·파싱·검증, 연구용 run_inputs와 manifest(UDR sha256 포함), G5 calibrate·pilot 진입점, G6 summarize·timing 진입점(R-8 포함), G7 드라이버(R-1~R-5, 잠금 핸들 강제, 단일 Windows 호스트, R-4a 대상 job 생성·정책 readback·할당·시작 barrier·드라이버 쪽 소속 검증(IsProcessInJob + JobObjectBasicProcessIdList)·쓰기 직전 재확인, E-POOL-START·E-WORKERS 기록, abandon 근거 E-BOOT, 조사 전용 E-PID·E-WORKERS·E-TREE, Python 3.14.8 검사), E-BOOT 판독(host_id, S1·S2, boot_identity, mtime 비교), stdlib ctypes kernel32·ntdll 래퍼(종료·신호 API 없음), R-9 IT 테스트(그룹 표시와 기본 실행 제외, E-POOL-START·E-WORKERS 기록 함수의 디렉터리 인자, 테스트 전용 임시 디렉터리 분리 확인), G8a 진입점(R-6, 시도 집합), R-7 이름·재시도 검사, 각 디렉터리 verify.
- run_spec·execution.json 스키마와 기존 결정적 바이트는 바뀌지 않는다. g6_summary.json에 `P0_CONF_CHECK` 필드가 추가된다(아직 생성된 G6 요약은 없다).

## SECURITY_IMPACT

SECURITY_IMPACT: 없음. guard·hook·settings·자격증명·네트워크·실데이터와 관계없다. 잠금과 UDR에는 pid·host 식별 정보(computer_name, machine_guid)·프로세스 시작 시각·부팅 시각 판독값·토큰·사용자 승인 문구만 기록한다. MoneyLab 코드는 프로세스에 신호를 보내거나 프로세스를 종료하지 않는다(R-4c A). stdlib·OS가 일으키는 종료는 R-4c B의 별도 승인 대상이다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA (G3 TEST_GATES에서 light로 검증):
- AC-0 UDR: 승인 줄 파싱, 번호·kind·target·decision 불일치 STOP, 요약 target STOP, approval_text_sha256 중복 STOP, 번호가 다음 번호가 아니면 STOP, 하위 단계 재검증, UDR로 PASS·완화·종료 확인 대체가 불가능함.
- AC-1 R-1 G7 진입 검사 STOP 9가지 각각, PD-5 STOP일 때 PD5_PROCEED UDR 없이는 STOP_FOR_USER_DECISION.
- AC-2 드라이버가 E1 → P0 → V-4 순서이고 pool이 하나다. workers 13은 STOP, host_id 불일치·Windows가 아닌 OS는 STOP이다.
- AC-2b worker는 어떤 파일도 쓰지 않는다(쓰기 위치 감시 fake로 확인).
- AC-J1 대상 job 신원 [FAKE_TEST + INTEGRATION_TEST_REQUIRED]: 기본 검증(A) IsProcessInJob(worker 핸들, 대상 job)과 (pid, 생성 시각) 일치로 판정, (B)는 보조 통제, (C)만으로는 확인되지 않음, readback 플래그 불일치 STOP.
- AC-J2 드라이버와 모든 계산 worker의 소속 [FAKE_TEST + INTEGRATION_TEST_REQUIRED]: worker가 드라이버의 직계 자식임(3.14.8 관찰)을 실측, 전원 (A) TRUE, (B)에서 예상 밖 PID·누락 worker·확인 불가 프로세스 각각 STOP, pool이 열린 동안 다른 자식 프로세스 생성 시 STOP.
- AC-J3 시작 barrier [FAKE_TEST + INTEGRATION_TEST_REQUIRED]: 모든 작업을 먼저 제출하면 min(w, 작업 수)개 worker가 동기 생성됨을 실측, release 전에는 연구 계산 함수 미호출, 알려 온 worker와 스냅샷 자식 불일치·수 불일치·ready_queue timeout·BrokenProcessPool STOP, release 뒤 새 worker 출현 시 재사용 없이 STOP, max_tasks_per_child 미사용, Python 3.14.8이 아니면 G7 STOP, worker 기록이 계산 허용 직전에 O_EXCL로 쓰임.
- AC-J4 중첩 job·SILENT_BREAKAWAY_OK 환경 [READ_ONLY_AUDIT(완료: 외부 job 0x3000 관찰) + INTEGRATION_TEST_REQUIRED]: 외부 job 안에서 대상 job 할당 성공·readback 성공 기록, 실패 시 STOP, 외부 job 플래그만으로 판정하지 않음.
- AC-J5 핸들 소유권·비상속 [FAKE_TEST + INTEGRATION_TEST_REQUIRED]: 상속 불가 생성, 복제 없음, 실행 중 CloseHandle 없음, 기록 없음, worker 쪽에서 대상 job 핸들이 보이지 않음.
- AC-J6 worker 검증 실패 시 STOP [FAKE_TEST]: 열기 실패, IsProcessInJob FALSE, 목록 불일치, 생성 시각 조회 실패 각각 STOP이고 unit 미기록.
- AC-J7 abandon과 조사 증거 [FAKE_TEST + INTEGRATION_TEST_REQUIRED]: 짝 없는 lock의 abandon은 LOCK_ABANDON UDR과 E-BOOT(부팅 시각이 lock·pool 기록 수정 시각보다 뒤, 같은 host_id)가 모두 있을 때만 허용되고, E-PID·E-WORKERS·E-TREE가 모두 "종료"를 보여도 E-BOOT 없이는 거부됨. E-TREE 조사의 시작점 확장(드라이버 + 기록된 worker pid, 생성 시각 기준)·재귀·PID 재사용·끊긴 사슬·조회 실패·두 스냅샷 불일치, E-WORKERS 조사의 기록 공백·손상·불일치 처리. 강제 종료 뒤 조사 결과를 실측(IT-5, R-9 그룹 C 승인 필요).
- AC-J9 pool 의도 기록 [FAKE_TEST + INTEGRATION_TEST_REQUIRED]: E-POOL-START가 pool 생성 전에 O_EXCL·fsync로 쓰이고 실패 시 pool 미생성 STOP, 파일명과 pool_id 일치, 필드 완비, start 없는 workers 기록은 비정상 상태(FAKE: IT-7). 통합 부분(IT-2·IT-3a, R-9 테스트 전용 실제 파일 기록): 실제 pool 생성 전에 실제 파일의 O_CREAT|O_EXCL 생성·write·fsync가 완료됨(드라이버 이벤트 순서와 mtime ≤ worker 생성 시각). 실패 주입은 FAKE(IT-7)로만 한다. 전원 장애 뒤의 영속성은 증명하지 않는다.
- AC-J10 worker 기록 순서 [FAKE_TEST + INTEGRATION_TEST_REQUIRED]: (A)·(B) 검증 → O_EXCL 생성 → 내용 → fsync → release 순서, 각 단계 실패 시 release 없이 STOP, verified ≠ expected면 기록 없이 STOP, 필드 완비(barrier_release_pending 없음)(FAKE: IT-8). 통합 부분(IT-2·IT-3a, R-9 테스트 전용 실제 파일 기록): 실제 worker 소속 검증 뒤에만 실제 파일의 O_CREAT|O_EXCL 생성·write·fsync 완료, 그 뒤에만 barrier 해제(드라이버 이벤트 순서와 mtime ≤ worker의 barrier 통과 시각), 기록의 pid·생성 시각·verified_worker_count가 실제 worker와 일치, 예상 밖 worker는 STOP. 실패 주입은 FAKE(IT-8)로만 한다. 전원 장애 뒤의 영속성은 증명하지 않는다.
- AC-J11 기록 부재의 해석 [FAKE_TEST]: E-POOL-START 없음, start만 있음, 일부·손상 기록 각각에서 판정이 "worker 없음"이 되지 않고 abandon에 E-BOOT를 요구함.
- AC-J12 Python 버전 [FAKE_TEST]: sys.version이 3.14.8이 아니면 G7 STOP, lock에 정확한 sys.version 기록, 버전 일치만으로 job 동작 검증으로 표시되지 않음.
- AC-J13 E-BOOT 판정 [FAKE_TEST + READ_ONLY_HOST_CHECK_REQUIRED(RB-1)]: host_id 불일치·판독 실패, S1·S2 판독 실패, |S1 − S2| > 120 s, 부팅 세션 미변경, mtime이 부팅 시각과 같거나 뒤, 미래 mtime, 대상 파일 stat 실패, 유효하지 않은 lock 각각에서 불성립(STOP). 모두 성립해도 LOCK_ABANDON UDR이 없으면 abandon 거부. S1·S2 일치만으로 성립하지 않음. RB-1 통과 전에는 성립으로 판정하지 않음. `n.abandoned` 기록 필드 완비.
- AC-J14 프로세스 종료 구분 [FAKE_TEST + 정적 검사]: MoneyLab 운영 코드와 ctypes 래퍼에 종료·신호 API 호출과 실행기의 worker 강제 종료 메서드 호출이 없음. 테스트 코드의 직접 종료 경로는 그룹 C(IT-5) 표시가 붙은 테스트에만 있음(그룹 A·B의 종료는 stdlib·OS가 일으키는 것뿐). 테스트 대기 timeout 경로에 종료 호출이 없고 전체 STOP과 잔존 pid 보고를 함. G7 진입 점검이 GATE_AUTHORIZATION의 정확한 G7_POOL_FAILURE_POLICY 값 없이는 STOP함.
- AC-J8 전체 누적 예산 불변 [FAKE_TEST]: OPTION I(모든 시도 합산), 1.5배 경계, 예산 STOP 뒤 재시도 금지, INCOMPLETE PASS 금지가 rev3와 같은 결과.
- AC-3 모든 시도를 포함한 누적 재계산, 정확히 1.5배 통과·초과 STOP, 예산 STOP 뒤 재시작 STOP, INCOMPLETE는 PASS가 아님, V-4 시간 제외, RESUME UDR 없이는 재개 STOP(fake clock).
- AC-4 잠금: O_EXCL 경쟁에서 하나만 획득, 빈·부분 lock, 쓰기 직전 소유권 확인과 마지막 세션 확인, abandon 근거는 E-BOOT뿐(E-PID·E-WORKERS·E-TREE는 단독이든 조합이든 거부), 부팅 전·host_id 불일치·부팅 시각 조회 실패는 abandon 거부, 비정상 상태(pool 기록 관련 포함), 어떤 파일도 지우지 않음, 잠금 핸들 없는 연구용 core run_units는 STOP, 신호를 보내지 않음.
- AC-5 V-4: v4.json 결정성(worker 1·2), SHA256SUMS 범위, 재사용·재계산 비교, 손상 STOP, K = 40 불가 STOP(작은 경로).
- AC-6 G8a: 진입 조건 각각의 STOP, 대상 시도 선택 규칙, 이전 시도 unit 바이트 비교, 어느 시도든 INCOMPLETE면 STOP, 재실행 바이트 같음, 판정 결과가 기존 decision_summary와 같음.
- AC-7 run_id: 이름 검사, ATTEMPT UDR 없는 `-attempt<k>` STOP, k 건너뛰기 STOP, 허용 사유 외 STOP, 예산 STOP·G8a 뒤 재시도 STOP, 자동 증가 없음.
- AC-8 R-8: 경계값 PASS, 바깥 STOP, 원자료 재계산 일치, g6_summary.json에 수치 없이 PASS/STOP만.
- AC-9 Ce 커밋 전후 이 파일의 sha256이 같고 커밋 파일이 이 파일 하나다.

## ROLLBACK_POLICY

ROLLBACK_POLICY:
- ACCEPTED 이후 이 파일은 불변이다. 철회·수정은 ERRATA-006으로만 한다.
- G5 이후에 이 ERRATA의 내용을 바꾸면 WO:87에 따라 사용자가 결정하고, G7 이후에는 새 study다.
- 사용자가 이 보충을 사전등록 변경으로 판단하면 이 ERRATA는 쓰지 않고 새 Work Order·사전등록으로 간다(WO:85).

## APPROVAL

APPROVAL:
- 이 문서는 사용자가 수락한 ACCEPTED ERRATA이며, 명시된 보충 계약을 적용한다.
- 수락은 [B] 항목 전체, R-8 [B-STAT] 통계 계약, ATTEMPT_BUDGET_OPTIONS의 OPTION I 채택, 그리고 이 보충이 사전등록 변경이 아니라 미정 사항 보충(WO:85, WO:349)이라는 사용자 판단을 포함한다.
- ERRATA-004 O-1~O-5는 이 ERRATA가 ACCEPTED로 Ce 커밋되면 닫힌다.
- 수락은 R-4c B(테스트 전용 종료, 그룹 A 실패 경로 포함)의 실행 승인, G7_POOL_FAILURE_POLICY의 확정(G7 GATE_AUTHORIZATION에서만), R-9 각 그룹과 RB-1의 실행 승인을 포함하지 않는다. 이들은 각각 별도로 승인한다. O-6은 열린 채로 남는다.
- ACCEPTED 문구 확정과 Ce5 커밋(파일 생성, 경로를 지정한 stage, 커밋, sha256 보고)은 각각 사용자의 별도 승인 사항이다.
