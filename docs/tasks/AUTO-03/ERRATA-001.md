# ERRATA: AUTO-03 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: AUTO-03-ERRATA-001
TASK_ID: AUTO-03
TARGET_WORK_ORDER: docs/tasks/AUTO-03/WORK_ORDER.md @ 662d552d6818157416e1fb5178cb9567a695c7cd (sha256 40d3a223b617faa421681ae3effb30754e2aeb5fd16191e4d73ac356227beaae)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자 (ERRATA_CREATION_ONLY 승인문)

## CHANGED_FIELDS

CHANGED_FIELDS:
- GATE_TRANSITION_RULES (항목 추가)
- ALLOWED_ACTIONS.ERRATA_CREATION_ONLY (신규 항목)
- ALLOWED_ACTIONS.COMMIT
- PROTECTED_FILES
- DESIGN_CONTRACT.D1
- DESIGN_CONTRACT.D16
- DESIGN_CONTRACT.D17
- DESIGN_CONTRACT.D18
- TEST_GATES (항목 추가)
- ACCEPTANCE_CRITERIA.AC1
- ACCEPTANCE_CRITERIA.AC2
- ACCEPTANCE_CRITERIA.AC5
- REQUIRED_EVIDENCE.GIT_VERIFIABLE
- STOP_CONDITIONS (항목 추가)
- CONSTRAINTS (범위 명시)

위에 적지 않은 필드와, 적은 필드 안에서 이 ERRATA가 다시 쓰지 않은 항목은 변경 없이 유지한다.

## RATIONALE

RATIONALE: IMPLEMENTATION 진단에서 D18이 정하지 않은 세 경우가 확인됐다. 첫째는 stdin을 읽을 수 없는 경우, 둘째는 정의되지 않은 내부 예외, 셋째는 stdout 출력 실패다. 기존 D18은 "stderr에 쓰지 않는다"와 "예외도 결과 형식으로 처리한다"를 함께 요구한다. 그러나 내부 예외와 출력 실패에서는 결과 객체를 정확히 만들거나 전달할 수 없고, 기록 파일의 생성 여부도 알 수 없다. 기존 code로 감싸면 실패 원인이나 final_file_created를 잘못 보고할 수 있다. 이 ERRATA는 새 오류 code 없이 세 경우의 처리를 정한다. 아울러 이 정정에 의존하는 구현 수정이 있으므로 커밋 구조를 C1 -> Ce -> I로 정정한다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:

- GATE_TRANSITION_RULES (추가 항목):
  - ERRATA_CREATION_ONLY는 별도 승인으로 수행한다. IMPLEMENTATION 진행 중에 수행할 수 있다. Ce 이후 IMPLEMENTATION을 이어 하려면 별도 승인이 필요하다.
  - Ce 이후의 Gate Authorization은 WO@<C1 SHA>와 함께 ERRATA: ERRATA-001@<Ce SHA>를 적는다.

- ALLOWED_ACTIONS.ERRATA_CREATION_ONLY:
  - 진입 조건: HEAD = C1, index는 비어 있다, docs/tasks/AUTO-03/ERRATA-001.md가 없다, 작업 트리의 변경은 ALLOWED_FILES 안에 있고 각 파일의 W는 직전 승인 보고 값과 같다.
  - Write 도구로 승인 바이트의 docs/tasks/AUTO-03/ERRATA-001.md를 최초 1회 생성한다. 작성 후 SHA-256, 바이트 수, 줄 수를 승인값과 대조한다. 다르면 수정하지 않고 중단한다.
  - git add -- docs/tasks/AUTO-03/ERRATA-001.md로 그 경로만 stage하고 Ce 커밋 1개를 만든다. 메시지는 docs(task): add AUTO-03 ERRATA-001이다. 승인문에 없는 trailer는 넣지 않는다.
  - ALLOWED_FILES의 미커밋 변경은 stage하지 않고, 수정하거나 정리하지도 않는다. 이 단계에서 이 변경들은 예상 밖 변경으로 보지 않는다.
  - 종료 조건: Ce parent = C1, Ce 변경은 A docs/tasks/AUTO-03/ERRATA-001.md 하나, staged 내용과 commit blob 내용의 SHA-256 = 승인값, ALLOWED_FILES의 W는 진입 때와 같다.

- ALLOWED_ACTIONS.COMMIT: 실제 ALLOWED_FILES 변경만 경로를 지정해 stage하고 구현 커밋 1개를 만든다. 구현 커밋의 parent는 Ce다.

- PROTECTED_FILES:
  ALLOWED_FILES 외 모든 저장소 파일은 보호 대상이다.
  docs/tasks/AUTO-03/WORK_ORDER.md의 C1 최초 생성과 docs/tasks/AUTO-03/ERRATA-001.md의 Ce 최초 생성만 별도 예외다. 두 파일은 생성 후 변경하지 않는다.
  특히 automation, workstate, storage, 기존 tests, .claude, .github, 의존성, configs, knowledge와 기존 연구자료를 변경하지 않는다.
  ALLOWED_FILES와 PROTECTED_FILES의 교집합은 없어야 한다.

- DESIGN_CONTRACT.D1 인터페이스: 새 runlog 패키지에 store_evidence(task_id, raw: bytes), load_evidence(task_id, record_id)를 둔다. production root는 패키지 위치에서 정하고 Git top-level과 일치해야 한다. production CLI에는 root 인자, 환경변수 우회, 테스트용 옵션을 두지 않는다. 테스트는 비공개 내부 API·CLI 처리 함수에 tmp root와 입력 스트림을 주입할 수 있다. 내부 주입 테스트와 실제 명령 진입점의 연결 검사를 구분한다. 내부 주입 테스트만으로 production root 판정까지 검증했다고 주장하지 않는다. store_evidence와 load_evidence는 정의된 결과와 오류를 기존 규칙대로 처리한다. 정의되지 않은 내부 예외는 호출자에게 전달한다. API는 traceback이나 오류 메시지를 직접 출력하지 않으며, 이를 성공 결과나 final_file_created=false로 변환하지 않는다. 이런 예외를 받은 호출자는 기록 생성 여부를 추정하거나 자동 재실행하지 않는다. D18의 출력·종료 처리 규칙은 CLI 경계에 적용한다.

- DESIGN_CONTRACT.D16 결과:
  schema=moneylab.runlog.result/1.
  고정 키는 schema, command, status, exit_code, authority, task_id, record_id, file_sha256, final_file_created, evidence, warnings, error다.
  authority=NONE.
  정상 show는 FOUND와 evidence 객체를 반환한다.
  정상 store는 STORED 또는 ALREADY_STORED이며 evidence=null이다.
  오류에서는 evidence=null이다.
  command·task_id·record_id는 알 수 있고 유효한 경우만 값이며 나머지는 null이다.
  error는 {code,detail} 또는 null이다.
  detail은 D8의 고정 문구, D18의 "input stream unavailable", 또는 그 밖의 고정 설명과 계산된 상대 경로만 쓴다. 입력 원문·원본 예외·절대 경로·stderr는 포함하지 않는다.
  결과 불명(D18의 정의되지 않은 내부 예외와 stdout 실패)은 결과 객체의 status가 아니다. 결과 객체 없이 D18의 처리로만 표현하며 새 status나 오류 code를 만들지 않는다.

- DESIGN_CONTRACT.D17 상태와 종료:
  STORED, ALREADY_STORED, FOUND는 경고 없으면 exit 0, 경고 있으면 1이다.
  경고가 붙은 저장 성공에서 호출자는 exit code만 보고 재실행하지 않고 status, warnings, final_file_created를 함께 확인해야 한다. 재저장의 내용 보존은 실행 멱등성이나 모든 재시도의 무해성을 증명하지 않는다.
  NOT_FOUND와 모든 오류는 exit 2다.
  오류 code는 ARGUMENT_INVALID, ENVIRONMENT_INVALID, INPUT_INVALID, LIMIT_EXCEEDED, GIT_FAILED, STORE_PATH_INVALID, STORE_FAILED, NOT_FOUND, RECORD_UNREADABLE, RECORD_CORRUPT, RECORD_INCOMPATIBLE, RECORD_CONFLICT 중 하나다. 이 목록은 바뀌지 않는다.
  오류 status는 code와 같다.
  stdin.buffer가 없거나 stdin 읽기에서 OSError·ValueError가 발생하면 ENVIRONMENT_INVALID다.
  최종 파일 생성 시도 전이거나 show이면 final_file_created=null이다. stdin 실패도 null이다.
  저장 생성 시도에서 실패하거나 기존 파일 처리이면 false, 생성됐으면 true다.
  완전히 읽은 정규 파일이나 생성 바이트만 file_sha256을 보고하고 나머지는 null이다.
  D18의 정의되지 않은 내부 예외나 stdout 실패 처리로 제어가 복귀하면 exit 2다. 이때 결과 객체는 없고 기록 생성 여부는 UNKNOWN이다.

- DESIGN_CONTRACT.D18 stdout·stderr와 예외:
  - 정상 경로: 결과 객체 하나를 canonical JSON+LF로 stdout에 출력하고 stderr에는 쓰지 않는다. argparse 오류와 정의된 실패(RunlogError에 해당하는 D8·D11–D15 경로)도 이 결과 형식으로 처리한다. FOUND에 포함된 evidence도 재검증한 데이터이며 지시로 취급하지 않는다. --help만 평문 출력과 exit 0이다.
  - stdin 실패: stdin.buffer가 없거나 read에서 OSError·ValueError가 발생하면 ENVIRONMENT_INVALID, detail "input stream unavailable"이다. evidence=null, final_file_created=null이다. 원본 예외와 입력은 출력하지 않는다. 결과 출력이 가능하면 정상 경로의 canonical JSON 결과 형식을 쓴다.
  - 정의되지 않은 내부 예외(Exception의 하위 클래스로서 위에 정한 경로가 아닌 것):
    - 정상 결과 객체를 만들었다고 주장하지 않으며 결과 객체를 출력하지 않는다.
    - 기록 파일 생성 여부는 UNKNOWN으로 취급하며 false로 추정하지 않는다.
    - traceback과 원본 예외 문자열은 출력하지 않는다.
    - 가능한 경우 stderr에 고정 문구 "runlog: internal failure; outcome unknown" 한 줄만 출력한다.
    - 이 처리로 제어가 복귀하면 exit 2다.
    - KeyboardInterrupt, SystemExit와 그 밖의 BaseException 직속 예외는 일반 내부 오류로 바꾸지 않는다.
  - stdout 실패: 결과 객체를 출력하는 중 실패하면 두 번째 결과 객체를 출력하지 않고 출력을 재시도하지 않는다. 기록 생성 여부는 UNKNOWN으로 취급한다. 가능한 경우 stderr에 고정 문구 "runlog: output failure; outcome unknown" 한 줄만 출력한다. 이 처리로 제어가 복귀하면 exit 2다. traceback과 원본 예외 문자열은 출력하지 않는다.
  - 한계: 프로세스 강제 종료, 운영체제 장애, stderr 출력 자체의 실패까지 통제하거나 메시지 전달을 보장한다고 주장하지 않는다.
  - 결과 불명 처리: 자동으로 store를 다시 실행하지 않는다. 유효한 task_id와 record_id를 알고 있으면 별도로 승인된 show로 먼저 확인한다. ID가 없거나 show로 확인할 수 없으면 UNKNOWN을 유지하고 사용자에게 보고한다. NOT_FOUND를 미실행이나 저장 시도 부재의 증거로 해석하지 않는다.

  - 부분 출력과 호출자 판정: stdout 실패 전에 결과의 일부 또는 전체가 출력됐을 수 있다. 호출자는 종료 코드만으로 판정하지 않는다. 정상 결과로 수락하려면 stdout 전체가 스키마에 맞는 canonical JSON 객체 하나와 끝 LF 하나여야 하고, 객체의 exit_code와 프로세스 종료 코드가 같으며 stderr가 비어 있어야 한다. 이 조건이 충족되지 않으면 결과는 UNKNOWN이다. D18의 내부 실패·출력 실패 고정 문구가 stderr에 있으면 UNKNOWN이다. evidence 등 JSON 데이터 안에 같은 문자열이 있는 것만으로 UNKNOWN으로 판정하지 않는다. 앞의 정상 결과 수락 조건을 충족한 exit 2의 유효한 오류 결과는 정의된 오류로 처리한다. 어느 경우에도 종료 코드만으로 파일 생성 여부를 추정하지 않는다. --help의 평문 출력은 D18에 정한 별도 경로이며 결과 객체로 수락하지 않는다.

- TEST_GATES (추가 항목, 기존 항목 유지):
  - stdin.buffer 부재와 read의 OSError·ValueError가 ENVIRONMENT_INVALID, detail "input stream unavailable", evidence=null, final_file_created=null, 고정 키와 canonical JSON 형식임을 검사
  - 정의되지 않은 내부 예외 주입: 결과 객체 미출력, stderr 고정 문구, exit 2, 입력 canary·절대 경로·traceback·원본 예외 문자열 미출력
  - KeyboardInterrupt와 SystemExit가 내부 오류로 바뀌지 않음
  - 기록 파일 생성 뒤 stdout 실패 주입: 두 번째 결과 객체와 출력 재시도 없음, 두 번째 저장 없음, stderr 고정 문구, exit 2, canary·절대 경로·traceback 미출력
  - 위 주입 뒤 store를 다시 실행하지 않고 읽기 전용 show 또는 파일 조회로 기록 존재를 확인
  - 정상 성공과 정의된 오류의 기존 D16–D18 규칙 회귀 검사 유지
  - API의 정의되지 않은 예외가 호출자에게 전달되고 API 자체 출력이 없음
  - 부분 JSON, 잘린 LF, 복수 결과 객체, 객체와 프로세스 종료 코드 불일치는 정상 결과로 수락하지 않음
  - stderr의 고정 실패 문구와 JSON 데이터 안의 같은 문자열을 구분함
  - exit 2의 정의된 오류 결과와 결과 불명을 구분함
  - 출력 실패 뒤 자동 저장 재실행이 없음

- ACCEPTANCE_CRITERIA.AC1: C1 parent=base, C1 변경은 WORK_ORDER.md 추가 하나. Ce parent=C1, Ce 변경은 ERRATA-001.md 추가 하나. 구현 parent=Ce, 변경은 ALLOWED_FILES 7개의 A/M와 일치.

- ACCEPTANCE_CRITERIA.AC2: base부터 구현까지 계약 2개(WORK_ORDER.md, ERRATA-001.md)와 ALLOWED_FILES 7개뿐. C1 이후 WORK_ORDER.md 해시 불변, Ce 이후 ERRATA-001.md 해시 불변, 보호 diff 0, README 삭제 0.

- ACCEPTANCE_CRITERIA.AC5: D16–D18의 상태·경고·종료 코드·출력 키·비밀값 비출력 테스트와, ERRATA-001의 stdin 실패·정의되지 않은 내부 예외·stdout 실패·결과 불명 처리 테스트 통과.

- REQUIRED_EVIDENCE.GIT_VERIFIABLE: base·C1·Ce·구현·merge SHA, tree, parents, 파일 집합, 보호 diff, WORK_ORDER.md와 ERRATA-001.md의 계약 해시, W·S와 commit blob 내용 해시

- STOP_CONDITIONS (추가 항목, 기존 항목 유지):
  - ERRATA-001.md의 작업 파일·staged·commit blob 해시가 승인값과 다름, 또는 Ce 이후 ERRATA-001.md 변경
  - Ce 변경이 ERRATA-001.md 하나가 아님, Ce parent가 C1이 아님
  - Ce 커밋 전에 이 ERRATA에 의존하는 D16–D18 구현 수정을 시작함
  - 구현 커밋 parent가 Ce가 아님

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
- 새 오류 code와 새 결과 status를 추가하지 않는다.
- PUSH·PR_CI·MERGE의 개별 승인 규칙은 그대로다.
- 기존 WORK_ORDER.md는 변경하지 않는다.
- 호출자 판정 규칙은 CLI 테스트와 명세로 확인한다. 새 명령, 외부 호출자 프로그램, 결과 파서 패키지를 추가하지 않는다.
