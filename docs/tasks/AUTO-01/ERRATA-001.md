# ERRATA: AUTO-01 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: AUTO-01-ERRATA-001
TASK_ID: AUTO-01
TARGET_WORK_ORDER: docs/tasks/AUTO-01/WORK_ORDER.md @ 6f5c95d50ae693edb81689138d85c35e28450c07 (sha256 66d3aba3576c56a088541a4cb005761c072a4c21c2385b68b61566fbec7cd355)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER, 2026-11-08

## CHANGED_FIELDS

CHANGED_FIELDS:
- DESIGN_CONTRACT.D3
- DESIGN_CONTRACT.D6
- TEST_GATES
- PROTECTED_FILES (docs/tasks/AUTO-01/** 예외 및 INVARIANT)
- Ce 및 IMPLEMENTATION 재진입 S0 기준선 추가 (CE_COMMIT, REENTRY_S0)

## RATIONALE

RATIONALE: PRECOMMIT_AUDIT에서 (A) D6가 DENIED의 action_id 값을 규정하지 않아 호출자 임의 문자열이 Evidence에 복사되는 점, (B) D3의 "종료·회수까지 60초"가 kill 이후 회수 시간 상한을 규정하지 않는 점이 확인되었다. 소유자는 (A) DENIED action_id를 항상 null로, (B) 60초 실행 제한과 종료·회수 시간 예산을 분리하고 회수 실패 시 AutomationError로 실패하도록 결정했다. 이 ERRATA를 Ce로 고정하려면 PROTECTED 예외가, Ce 뒤 IMPLEMENTATION 재진입에는 HEAD 기준선이 필요하다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- DESIGN_CONTRACT.D3: D3 Executor: `subprocess.Popen`에 고정 argv 리스트, `shell=False`, 고정 cwd, 환경변수 allowlist를 적용한다. stdout·stderr는 별도 표준 라이브러리 thread에서 각각 청크 단위로 동시에 읽고, 공유된 누적 바이트 수 상한(두 스트림 합계 1 MiB = 1,048,576 bytes)을 초과하면 프로세스를 종료한다. 두 reader thread는 누적 길이 검사와 바이트 추가를 동일 lock으로 직렬화하며, 상한 초과 청크는 저장하지 않는다. 제한을 넘는 출력은 상태 OUTPUT_LIMIT_EXCEEDED로 기록한다. 실행 제한(timeout)은 프로세스 시작부터 단조 시계 기준 60초이며, 60초 안에 자식 프로세스가 종료하지 않으면 TIMEOUT이다. 자식이 60초 안에 종료한 경우 남은 출력 수집(reader thread join)도 같은 60초 deadline 안에서만 하며, 끝나지 않으면 TIMEOUT이 아니라 AutomationError로 실패한다. timeout 또는 출력 상한 초과 시 직접 자식 프로세스를 kill하고 wait로 회수(최대 10초)한 뒤 reader thread를 join(두 thread 합계 최대 10초)한다. 회수 대기가 실패하면 정리를 위한 kill·wait를 한 번 더(최대 10초) 시도한 뒤 AutomationError로 실패한다. 이 종료·회수 시간 예산은 60초 실행 제한에 포함하지 않으며, run_action 반환까지 최악 약 80초가 걸릴 수 있다. kill은 직접 자식만 대상으로 하며 프로세스 트리 종료를 보장하지 않는다. 종료·회수에 실패하거나 thread가 남으면 Evidence를 만들지 않고 AutomationError로 실패하며 호출자는 STOP한다. subprocess 전체 출력을 무제한 메모리에 모으거나 실행 후 잘라내는 방식은 금지한다. 재시도 0회이며 단일 호출 동시 실행 1개만 허용한다. `sys.executable`을 사용하며 Windows 경로를 코드에 하드코딩하지 않는다.
- DESIGN_CONTRACT.D6: D6 Evidence: `moneylab.automation.evidence/1` canonical JSON 문자열을 반환한다. 필드는 `schema`, `action_id`, `decision`, `status`, `exit_code`, `duration_ms`, `stdout_sha256`, `stderr_sha256`이다. decision enum은 ALLOW|DENY; status enum은 SUCCEEDED|VALIDATION_FAILED|SOURCE_UNVERIFIED|TIMEOUT|OUTPUT_LIMIT_EXCEEDED|UNEXPECTED_EXIT|DENIED. ALLOW의 action_id는 등록된 고정 action ID 문자열이다. DENIED는 action_id·exit_code·duration_ms·두 해시 모두 null이며, 호출자 입력(원문·해시·길이 등 파생값 포함)을 Evidence에 넣지 않는다. TIMEOUT과 OUTPUT_LIMIT_EXCEEDED는 exit_code=null; 제한 안에서 수집한 출력 바이트의 SHA-256을 사용하고 수집 바이트가 없으면 빈 바이트의 SHA-256을 사용한다. 출력 상한 초과 시 해시는 상한 내에서 보존된 출력에 대해서만 계산하며 전체 프로세스 출력 해시라고 주장하지 않는다. 다른 실행 결과의 exit_code는 정수이며 해시는 원문 바이트 기준이다. duration_ms는 비음수 정수이며 실행별 가변이므로 결정성 비교에서는 제외한다. stdout/stderr 원문을 Evidence에 포함하거나 파일로 저장하지 않는다. Evidence 생성 실패는 성공으로 위장하지 않는다.
- TEST_GATES:
  - 신규 정책·Executor·Evidence·Isolation 테스트 모두 통과.
  - 미등록 action DENY 시 subprocess 호출 0회; 임의 argv/경로/명령 주입 불가.
  - DENIED Evidence의 action_id=null이며 호출자 입력 문자열(canary)이 반환 문자열에 나타나지 않음.
  - 고정 argv·`shell=False`·timeout·최소 환경변수·Git 경로 검증.
  - stdout·stderr 동시 출력에서 누적 1 MiB 상한이 실행 중 강제되는지, 초과 시 OUTPUT_LIMIT_EXCEEDED·exit_code=null이 반환되는지, 프로세스 종료·wait·thread join이 완료되는지 검증. 불가능하면 STOP.
  - 회수(wait) 실패, kill 후 reader thread join 실패, 정상 종료 후 deadline 내 출력 수집 미완료가 각각 AutomationError로 끝나고 Evidence를 만들지 않음을 검증.
  - 0, 1, 3, 2/기타, timeout, 출력 상한 초과 매핑은 fake Popen 및 제한된 실제 자식 프로세스 테스트에서 검증.
  - DENIED null 필드, TIMEOUT·OUTPUT_LIMIT_EXCEEDED null exit_code, stdout/stderr SHA-256, canonical JSON 직렬화 검증. 결정성 비교에서는 duration_ms 제외.
  - Guard의 고정 명령 판정 PASS 확인. ASK/DENY이면 STOP.
  - 외부 네트워크 호출·주문 경로·보호 파일 변경이 없음을 정적·동적 테스트로 검증.
  - `python -m mypy src/moneylab/automation` 로컬 명시 실행 통과. 기존 CI의 mypy files 설정에는 신규 패키지가 포함되지 않으므로 CI가 이 검사를 보장한다고 주장하지 않는다.
  - 기존 ruff 검사 및 전체 pytest 회귀 통과(failed 0, errors 0).
  - `git diff --check`, 변경 파일 집합 = ALLOWED_FILES, PROTECTED diff 0.
- PROTECTED_FILES:
  - docs/tasks/AUTO-01/** (C1에서 WORK_ORDER.md 최초 생성, Ce에서 ERRATA-001.md 최초 생성만 예외; 이후 불변)
  - .claude/**
  - .github/**
  - CLAUDE.md
  - docs/agent_workflow.md
  - docs/tasks/README.md
  - docs/tasks/TEMPLATE.md
  - pyproject.toml
  - src/moneylab/supervisor/**
  - src/moneylab/knowledge/**
  - src/moneylab/execution/**
  - configs/**
  - knowledge/records/**
  - data/raw/**
  - data/processed/**
  - tests/** EXCEPT tests/test_automation_policy.py, tests/test_automation_executor.py, tests/test_automation_evidence.py, tests/test_automation_isolation.py
  - INVARIANT: IMPLEMENTATION의 ALLOWED_FILES ∩ PROTECTED_FILES = ∅. C1의 WORK_ORDER.md 최초 생성과 Ce의 ERRATA-001.md 최초 생성은 README v1.2에 따른 별도 예외이며 구현 허용 파일에 포함하지 않는다.
- CE_COMMIT: docs/tasks/AUTO-01/ERRATA-001.md 하나만 이 ERRATA의 승인된 문구 그대로 최초 생성하고 경로를 지정해 stage한 커밋(`docs(task): add AUTO-01 ERRATA-001`). parent = 6f5c95d50ae693edb81689138d85c35e28450c07. 기존 untracked 구현 파일 8개(ALLOWED_FILES)는 stage하지 않고 보존한다. Ce에는 별도의 명시적 승인이 필요하다.
- REENTRY_S0: Ce 뒤 IMPLEMENTATION 재진입의 S0는 HEAD = Ce, Ce parent = C1, Work Order sha256 일치, ERRATA-001 sha256 = Ce 보고값, tracked diff 0, untracked 파일 = ALLOWED_FILES 8개뿐, 그리고 ENVIRONMENT의 S0 항목 전부를 요구한다. 재진입은 GATE_TRANSITION_RULES에 따른 별도 명시 승인이 필요하다.

## UNCHANGED_FIELDS

UNCHANGED_FIELDS: 위에 적지 않은 Work Order의 나머지 요구사항과 STOP 조건은 그대로 유지한다. C1, WORK_ORDER.md blob과 그 sha256, ALLOWED_FILES, GATE_SEQUENCE, GATE_TRANSITION_RULES, D1·D2·D4·D5·D7·D8·D9, E2E_GATES, REQUIRED_CI_CHECKS, MERGE_METHOD를 포함한다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
