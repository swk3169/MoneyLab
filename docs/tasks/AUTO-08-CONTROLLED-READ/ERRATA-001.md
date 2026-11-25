# ERRATA-001: AUTO-08-CONTROLLED-READ

STATUS: ACCEPTED
TASK_ID: AUTO-08-CONTROLLED-READ
APPLIES_TO: docs/tasks/AUTO-08-CONTROLLED-READ/WORK_ORDER.md @ 14eb236b53a65cc7922441133bfbd27f1223cca9 (SHA-256 ffe9b566300fb3d34add648a04ec3dd36d72aff5335256abaad6bba02b3af6eb)
REPLACES: D3의 대조 문구, D5, D12의 prefix 한도, D13의 검사 대상, D14, D15의 저장 실패 처리, D16의 오류 응답과 (c), FILE_FORMAT의 검사 시점, IMPLEMENTATION 예산 계수, COMMIT 이후 감사 기준
UNCHANGED: ALLOWED_FILES 15개, PROTECTED_FILES, GATE_SEQUENCE, D1, D2의 명령 문법과 값 문법, D4, D6-D11, D17, FORBIDDEN_ACTIONS, E2E_GATES
BACKGROUND: IMPLEMENTATION은 guard protected-path DENY로 STOP되었다. 그 STOP·DENY 기록과 STOP 전 targeted 결과(1030 passed, 1 skipped, 3 xfailed)는 보존하되, 이 ERRATA 이후 코드의 검증 근거로 쓰지 않는다. 이 ERRATA는 STOP 이전 구현의 해석을 소급 승인하지 않는다.

## E1 출력 스키마

E1.1 공통
- 모든 출력은 D14 직렬화(json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=True, allow_nan=False) + LF 1개)로 stdout에 1회 쓴다. stderr에는 쓰지 않는다.
- 오류 코드 집합은 D14의 30개에 SESSION_UNREADABLE을 더한 31개다.
- error.detail은 코드마다 구현 안에 상수로 고정된 문구다. 입력값, 토큰, 경로, 예외 원문, 환경값을 포함하지 않는다. 서로 다른 코드는 서로 다른 문구를 갖는다.
- 정의되지 않은 예외는 출력 없이 전파하며 성공으로 바꾸지 않는다(D14 유지).

E1.2 moneylab.controlled_read.result/1 (run의 유일한 출력 형식)
- 이 ERRATA는 아직 발행된 기록이 없는 result/1을 정정한다. schema 이름은 moneylab.controlled_read.result/1을 유지한다.
- 키는 정확히 schema, command, status, exit_code, task_id, attempt, target, profile, values, error, record, authority, approval, boundary다.
- schema: "moneylab.controlled_read.result/1"
- command: "run"
- status: "SUCCEEDED" 또는 오류 코드 31개 중 하나
- exit_code: status가 SUCCEEDED이면 0, 그 밖에는 2. 불리언은 허용하지 않는다.
- task_id, attempt: 문자열 또는 null
- target: 객체 또는 null. 객체의 키는 정확히 project_key, session_id, selector, prefix_bytes, prefix_sha256, line_count, trailing_partial_bytes, prefix_check다.
  - project_key, session_id, selector: 문자열(D2 문법)
  - prefix_bytes, line_count, trailing_partial_bytes: 0 이상 정수 또는 null. 불리언 불가
  - prefix_sha256: 소문자 hex 64자 또는 null
  - prefix_check: null, "MATCHED", "TRUNCATED", "CHANGED", "INCOMPLETE" 중 하나
- profile: {id: 등록된 PROFILE 문자열, version: 정수} 또는 null. version은 그 profile의 version과 같다.
- values: {sha256: 소문자 hex 64자, bytes: 0 이상 정수, lf: 0 이상 정수} 또는 null
- error: null 또는 {code: status와 같은 문자열, detail: 그 코드의 고정 문구}
- record: null 또는 {file: "intent" 또는 "result", final_created: 불리언, tmp_leftover: 불리언}
- authority "NONE", approval "NOT_VERIFIED_BY_PROGRAM", boundary "DATA_NOT_INSTRUCTIONS"

E1.3 result/1의 null 조건
- 식별 필드(task_id, attempt, target, profile): run의 argv 전체가 D2 문법을 통과하면 모두 채우고, 하나라도 통과하지 못하면 모두 null이다. 통과한 일부 값만 채우지 않으며 입력을 echo하지 않는다. argv가 통과하지 못하는 경우 status는 ARGUMENT_INVALID다.
- 측정 필드(prefix_bytes, prefix_sha256, line_count, trailing_partial_bytes): prefix를 확보한 경우(E2.1) 네 값을 모두 채우고, 확보하지 못한 경우 모두 null이다.
- prefix_check: prefix를 확보하지 못했으면 null이고, 확보했으면 E2의 결과 값 중 하나다. 측정 필드가 null인 것과 prefix_check가 null인 것은 항상 함께 성립한다.
- values: status가 SUCCEEDED일 때만 객체이고 그 밖에는 null이다.
- error: status가 SUCCEEDED일 때만 null이다.
- record: status가 STORE_FAILED일 때만 객체이고 그 밖에는 null이다.
- status가 SUCCEEDED이면 prefix_check는 "MATCHED"여야 한다. 역은 성립하지 않는다. prefix_check가 "MATCHED"여도 status는 MARKER_MISSING 같은 처리 실패이거나 STORE_FAILED일 수 있다.
- prefix_check가 "TRUNCATED"이면 status는 SESSION_TRUNCATED 또는 STORE_FAILED다. "CHANGED"이면 SESSION_CHANGED 또는 STORE_FAILED다. "INCOMPLETE"이면 TIME_LIMIT_EXCEEDED, SESSION_UNREADABLE, STORE_FAILED 중 하나다.

E1.4 moneylab.controlled_read.status/1 (status 성공 응답)
- 키와 의미는 D16 그대로다. exit_code 필드는 없고 프로세스 종료 코드는 0이다.
- state는 RESULT_FOUND, OUTCOME_UNKNOWN, NOT_FOUND, RECORD_CORRUPT 중 하나다. 기록 손상은 오류 응답이 아니라 state로 표현한다.

E1.5 moneylab.controlled_read.status_error/1 (status 오류 응답)
- 키는 정확히 schema, command, status, exit_code, task_id, attempt, error, authority, boundary다.
- schema "moneylab.controlled_read.status_error/1", command "status", exit_code 2, 프로세스 종료 코드 2
- status: ARGUMENT_INVALID 또는 ENVIRONMENT_INVALID만
- task_id, attempt: status의 argv 전체가 D2 문법을 통과했으면 그 값, 아니면 둘 다 null
- error: {code: status와 같은 문자열, detail: 고정 문구}
- authority "NONE", boundary "DATA_NOT_INSTRUCTIONS"

E1.6 저장 기록에 쓰지 않는 문서
- result.json에는 status가 ARGUMENT_INVALID, ENVIRONMENT_INVALID, STORE_PATH_INVALID, ATTEMPT_EXISTS, STORE_FAILED가 아닌 result/1 문서만 쓴다. 이 다섯 코드를 저장 불가 코드라고 부른다.
- status/1과 status_error/1 문서는 어떤 기록 파일에도 쓰지 않는다.

## E2 prefix 검증과 한도 (D5와 D12의 prefix 한도를 대체)

E2.1 첫 읽기와 prefix 확보
- 세션 파일을 연 뒤 fstat 크기 S0이 64 MiB(67108864바이트)를 넘으면 SESSION_LIMIT_EXCEEDED다. 한도는 S0에 적용한다. prefix는 S0 이하이므로 prefix도 이 한도를 넘지 않는다.
- 처음 S0바이트를 읽는다. 읽기 중 OSError는 SESSION_UNREADABLE, 읽은 바이트가 S0보다 적으면 SESSION_TRUNCATED, 읽기 중 시간 초과는 TIME_LIMIT_EXCEEDED다. 이 세 경우와 그 이전의 실패(SESSION_NOT_FOUND, SESSION_PATH_INVALID, SESSION_LIMIT_EXCEEDED)에서는 prefix를 확보하지 못한 것이며 측정 필드와 prefix_check는 null이다.
- S0바이트를 모두 읽으면 마지막 LF까지를 prefix(P바이트)로 확정한다. 이 시점을 prefix 확보라고 부른다.

E2.2 처리
- prefix 확보 뒤 D6-D11 처리를 한다. 결과는 처리 성공이거나 정의된 처리 실패다. 정의된 처리 실패는 SESSION_CORRUPT, LINE_LIMIT_EXCEEDED, ENTRY_LIMIT_EXCEEDED, TEXT_LIMIT_EXCEEDED, BODY_LIMIT_EXCEEDED, FORMAT_UNSUPPORTED, ENTRY_NOT_FOUND, ENTRY_DUPLICATE, SELECTOR_KIND_MISMATCH, TOOL_RESULT_ERROR, TEXT_BLOCK_NOT_FOUND, TEXT_BLOCK_AMBIGUOUS, ENCODING_INVALID, BOM_PRESENT, CR_PRESENT, MARKER_MISSING, MARKER_DUPLICATE, MARKER_ORDER_INVALID, BODY_EMPTY다.
- 처리 중 시간 초과는 처리 실패가 아니라 TIME_LIMIT_EXCEEDED로 즉시 끝난다. 이때 재해시를 하지 않으며 prefix_check는 "INCOMPLETE"다.
- profile과 selector 종류가 맞지 않아 세션을 열기 전에 끝나는 SELECTOR_KIND_MISMATCH(D11)는 prefix 확보 전 실패이며 측정 필드와 prefix_check는 null이다.

E2.3 재해시
- 처리 성공과 정의된 처리 실패는 모두 재해시 대상이다. 처리 결과를 R이라 한다.
- 재해시는 아래 순서로 하며 처음 해당하는 단계에서 끝난다.
  1. 시간 확인. 초과면 status TIME_LIMIT_EXCEEDED, prefix_check "INCOMPLETE".
  2. 열린 핸들의 fstat. OSError면 SESSION_UNREADABLE, "INCOMPLETE". 크기가 P보다 작으면 SESSION_TRUNCATED, "TRUNCATED".
  3. [0, P)를 다시 읽는다. OSError면 SESSION_UNREADABLE, "INCOMPLETE". 읽기 중 시간 초과면 TIME_LIMIT_EXCEEDED, "INCOMPLETE". 읽은 바이트가 P보다 적으면 SESSION_TRUNCATED, "TRUNCATED".
  4. SHA-256이 다르면 SESSION_CHANGED, "CHANGED".
  5. 일치하면 prefix_check는 "MATCHED"다.
  6. 시간 확인. 초과면 status TIME_LIMIT_EXCEEDED이고 prefix_check는 "MATCHED"를 유지한다.
  7. 그 밖에는 status는 R이다.
- 잘림과 변경이 함께 있으면 위 순서에 따라 SESSION_TRUNCATED다. 읽기 실패는 그 단계에 도달한 경우에만 보고한다.
- 2-4에서 정한 status는 R을 대체한다. 바뀐 입력에서 얻은 R은 신뢰할 수 없기 때문이다.
- 이 검증은 전체 파일의 원자적 스냅샷이 아니며, 두 읽기 사이에 바뀌었다가 되돌아온 변경은 감지하지 못한다(D5 한계 유지).

E2.4 저장과의 관계
- 재해시가 끝난 뒤 result.json 저장에 실패하면 E3에 따라 status는 STORE_FAILED가 된다. 이미 얻은 측정 필드와 prefix_check는 그대로 유지한다.
- 처리 실패와 저장 실패가 함께 있으면 stdout의 status는 STORE_FAILED다. 처리 실패 코드나 SUCCEEDED로 보고하지 않는다.

## E3 저장 실패 (D15의 해당 부분을 대체)

E3.1 원칙
- atomic_create_new_bytes가 CreateNewError를 던지면 final_created 값과 관계없이 status STORE_FAILED, exit_code 2, values null이다. 어떤 경우에도 SUCCEEDED를 출력하지 않고, 저장된 다른 문서를 stdout 문서 대신 출력하지 않는다.
- record.file은 실패한 생성 시도의 대상("intent" 또는 "result")이다. record.final_created는 CreateNewError.final_created를, record.tmp_leftover는 CreateNewError.tmp_leftover가 None이 아닌지를 그대로 옮긴다.
- final_created는 그 생성 시도가 대상 파일을 완성했는지에 대한 정보일 뿐이다. 다른 파일의 존재나 유효성, status의 판정 결과를 증명하지 않는다.
- 이미 생성된 파일, 남은 임시 파일, 디렉터리는 수정·삭제·재작성하지 않는다. 프로그램은 정리하지 않으며 같은 ATTEMPT로 재실행하지 않는다.
- CreateNewError가 아닌 예외는 D14에 따라 전파한다.

E3.2 intent 저장 실패
- 세션 파일을 열지 않는다.
- stdout은 식별 필드를 채운 result/1이다. status STORE_FAILED, record.file "intent"이고, 측정 필드와 prefix_check는 null이다.

E3.3 result 저장 실패
- stdout은 처리와 재해시로 얻은 문서 P에서 status를 STORE_FAILED로, exit_code를 2로, values를 null로, error를 STORE_FAILED 고정 문구로, record를 {file: "result", ...}로 바꾼 문서다. 식별 필드, 측정 필드, prefix_check는 P의 값을 유지한다.
- 이 경우 stdout 문서는 result.json에 들어 있을 수 있는 P와 다르다. 이것은 정의된 예외이며, D15의 "result는 같은 실행이 stdout에 출력한 문서를 그대로 담는다"는 result.json 저장에 성공한 호출에만 적용된다.

E3.4 status의 한계
- RESULT_FOUND는 두 기록 파일이 형식과 식별값 면에서 유효하다는 뜻일 뿐이다. 그 호출의 stdout 내용, 호출 전체의 성공, 임시 파일 정리, 실행 진위, 승인, 재실행 권한을 증명하지 않는다. 내부 result의 status와 exit_code는 바꾸지 않는다.
- OUTCOME_UNKNOWN을 성공이나 미실행으로, NOT_FOUND를 미실행으로 바꾸지 않는다.

## E4 status 기록 검증 (D16 (c)를 대체)

- 내부 result가 다음을 모두 만족할 때만 (c)를 통과한다.
  - E1.2의 키 집합·타입을 만족한다.
  - schema는 "moneylab.controlled_read.result/1", command는 "run"이다. status/1과 status_error/1 문서는 통과하지 않는다.
  - task_id, attempt, target, profile이 모두 null이 아니고 D2 문법에 맞는다.
  - status는 저장 불가 코드(E1.6)가 아니고 record는 null이다.
  - E1.3의 조건을 모두 만족한다. 특히 status가 SUCCEEDED이면 측정 필드가 모두 채워져 있고 prefix_check가 "MATCHED"다.
- (a), (b), (d), state 정의, 출력 스키마는 D16 그대로다.

## E5 guard 검사 대상 (D13의 검사 대상을 대체)

- 정규화된 명령 c가 다음 중 하나에 맞으면 검사 대상이다.
  - (a) 모듈 실행 표기: 정규식 (?<![\w./-])-[a-z]*m\s*moneylab\.controlled_read(?!\w). 분리형 -m, 붙임형 -mmoneylab.controlled_read, 결합 옵션 -Bm·-Bmm, 하위 모듈 moneylab.controlled_read.__main__을 포함한다.
  - (b) INLINE_CODE 패턴에 맞으면서 moneylab.controlled_read를 포함하는 명령
- 판정
  - ASK(rule controlled-read)는 Bash 도구 호출이고 정규화 전 원문 명령 전체가 D2의 run 또는 status 형태와 fullmatch하는 경우뿐이다. 정확한 두 형태 밖의 실행 형태는 새로 허용하지 않는다.
  - 그 밖의 검사 대상은 모두 DENY(rule controlled-read-form)다. 붙임형 -m, 결합 옵션, 하위 모듈, 다른 인터프리터와 실행 파일 경로, 옵션 추가·누락이 여기에 속한다. PowerShell 도구 호출은 형태와 관계없이 DENY다.
  - 검사 대상이 아닌 명령은 기존 판정 그대로다(예: git diff -- src/moneylab/controlled_read/, git show, cat, 경로나 모듈명을 언급하는 grep, pytest, ruff, mypy).
- 위치는 D13 그대로 DENY_RULES 다음, PROTECTED 검사 앞이다. 다른 규칙, 상수, strict xfail 시험은 바꾸지 않는다.
- 한계: E5는 알려진 실행 표기를 식별하는 문자열 규칙이다. 모든 Python 실행, 동적 import, 간접 호출(변수, 스크립트 파일, 다른 모듈 경유)을 막는 보안 격리를 보장하지 않는다. 이를 보완하려고 범용 Python 허용이나 광범위한 명령 차단을 추가하지 않는다.
- 알려진 오탐(안전 쪽): 실행 프로그램과 관계없이 c에 -<영문자들>m moneylab.controlled_read 토큰 열이 있으면 DENY다.
- docs/agent_workflow.md에 같은 규칙과 한계를 적는다.

## E6 문안 정리

E6.1 D3 승인 대조 (D3의 "CLI 인자 7개" 문구를 대체)
- 승인 메시지는 고정 토큰 AUTO-08-CONTROLLED-READ를 포함해야 한다.
- 승인 필드 6개를 run 인자와 1:1로 문자열 완전 일치로 대조한다: TASK와 --task, PROJECT_KEY와 --project-key, SESSION과 --session, SELECTOR와 --selector, PROFILE과 --profile, ATTEMPT와 --attempt.
- EXPIRES_UTC는 호출 직전의 UTC와 비교한다. 이 대조와 만료 확인은 Claude가 하며 프로그램은 하지 않는다. 원문을 확인할 수 없으면 STOP한다.
- status는 CONTROLLED_READ_AUTHORIZATION을 소비하지 않는다. 사용자의 명시적 요청이 있고 guard ASK 승인 창을 거친 경우에만 실행한다.

E6.2 FILE_FORMAT 검사 시점 (FILE_FORMAT의 검사 방법을 구체화)
- 요구 내용(UTF-8, BOM 없음, LF, 끝 LF 1개, 탭·U+00A0·줄 끝 공백 없음)은 바꾸지 않는다. 판정 대상은 Git에 저장될 바이트다.
- PRECOMMIT_AUDIT: 작업 파일 바이트에서 CRLF만 LF로 바꾼 예상 저장 바이트를 검사한다. 다른 변환은 하지 않으며 BOM·공백 등을 자동으로 고치지 않는다. 작업 파일의 원래 CRLF 수는 별도로 기록한다.
- staging 뒤: 실제 index blob을 검사한다.
- 커밋 뒤: commit blob이 index blob과 같은지 대조한다.
- staging하지 않은 파일에는 index blob 검사를 요구하지 않는다.
- 검사 명령은 해당 gate의 Gate Authorization에서 정한다.
- STOP 전 FILE_FORMAT 검사에서 docs/agent_workflow.md와 tests/test_controlled_read_profiles.py가 출력된 원인은 미확정으로 기록한다. 관측 사실: Claude의 검사 명령이 두 파일을 출력했다(CLAUDE_REPORTED). ChatGPT 확인 시점에 docs/agent_workflow.md 작업 파일은 CRLF 202개였고, 두 파일에서 실제 U+00A0·탭·줄 끝 공백은 발견되지 않았다(INDEPENDENT).

## E7 커밋, 감사 기준, 예산

E7.1 Ce (ERRATA 커밋)
- Ce는 이 파일 docs/tasks/AUTO-08-CONTROLLED-READ/ERRATA-001.md 하나만 담는 커밋이다. 현재 작업 트리의 구현 변경 15개는 포함하지 않는다.
- 절차
  1. 15개 ALLOWED_FILES 작업 파일 각각의 SHA-256과 바이트 수, git status --porcelain --untracked-files=all 출력을 기록한다.
  2. Write 도구로 이 파일을 수락된 정본 그대로 최초 1회 작성하고 SHA-256·바이트·LF를 수락값과 대조한다.
  3. git add -- docs/tasks/AUTO-08-CONTROLLED-READ/ERRATA-001.md 1회. staged 경로가 정확히 이 1개인지와 staged blob의 SHA-256을 대조한다.
  4. git commit -m "docs(task): accept AUTO-08-CONTROLLED-READ ERRATA-001"(본문·trailer 없음, -a 없음). commit blob의 SHA-256과 커밋 파일 집합(이 1개)을 대조한다.
  5. 1의 15개 파일 SHA-256·바이트 수가 Ce 직후와 같고, status 출력이 이 파일의 추가 외에는 같은지 대조한다.
- 어느 대조든 다르면 STOP하고 파일·index·커밋을 보존한다. 삭제·덮어쓰기·자동 재시도·복구는 사전 승인되지 않는다.
- Ce의 parent는 14eb236b53a65cc7922441133bfbd27f1223cca9다. Ce 시점의 활성 guard는 미커밋 수정본임을 보고한다.

E7.2 Ce 이후 감사 기준
- 구현 커밋의 parent는 Ce다. PRECOMMIT_AUDIT와 COMMIT의 diff 기준, "변경 파일 집합 = ALLOWED_FILES 15개" 판정은 Ce 대비로 한다.
- 시험 ID 기준선은 14eb236에서 IMPLEMENTATION 변경 전에 수집한 3267개(1 deselected)를 유지한다. Ce는 시험 수집에 영향을 주지 않는 문서 1개만 추가하므로 기준선을 다시 수집하지 않는다.
- WORK_ORDER.md의 SHA-256은 바뀌지 않는다. ACCEPTED ERRATA는 이 파일 하나다.
- COMMIT gate의 "커밋 1회"는 구현 커밋에만 해당한다. Ce는 C1과 같은 계약 커밋으로 별도로 센다.
- POST_MERGE_AUDIT의 구조 감사 범위는 ALLOWED_FILES ∪ docs/tasks/AUTO-08-CONTROLLED-READ/** 그대로다.

E7.3 IMPLEMENTATION 예산
- 수정 반복 예산은 5회 중 사용 2회, 잔여 3회다. 전체 pytest는 3회 중 사용 0회, 잔여 3회다. 같은 실패 2회 연속 STOP 조건은 그대로다.
- 수정 반복 1회는 CHECK_COMMANDS 중 하나가 실패한 뒤 그 실패에 대응해 코드나 시험을 수정하고 다시 검사하는 것이다.
- 이 ERRATA를 반영하는 최초 변경 묶음(R0)은 실패 대응이 아니므로 수정 반복으로 세지 않는다. R0는 첫 CHECK_COMMANDS 실행 전에 끝내고, R0의 변경 파일 목록을 보고에 따로 적는다. R0 이후 첫 검사부터의 실패 대응 수정은 잔여 3회에서 센다.
- 이전 IMPLEMENTATION의 사용 기록(수정 2회, 전체 pytest 0회, protected-path DENY에 의한 STOP)은 보고에 유지한다.
- IMPLEMENTATION 재진입은 새 Gate Authorization으로만 한다. 이 ERRATA 자체는 재진입 승인이 아니다.
