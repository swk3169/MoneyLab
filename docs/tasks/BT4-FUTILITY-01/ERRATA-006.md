# ERRATA: BT4-FUTILITY-01 ERRATA-006

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-FUTILITY-01-ERRATA-006
TASK_ID: BT4-FUTILITY-01
TARGET_WORK_ORDER: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md @ 7ac09a674e68cbc95dd5c934f2d3580939fd02f0 (sha256 c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b)
PRIOR_ACCEPTED_ERRATA: ERRATA-001 (sha256 9fcac5a97605a85be68612ba4a465c5f24b8c5b5594f3a801ca5e551993d24bf, Ce 616ed51f257a8cfa2d2c080067b09258651930e9), ERRATA-002 (sha256 0ca8ab961af350b10a2660ca8ee7b8c4bfab2757ee2b6b1ae61ffcfeee7308fe, Ce 2eb876e02456405667f466a124f745b3dd4fba3c), ERRATA-003 (sha256 9b8fcf9f30d8b525237a63b00f599add0a2fbcb33cb0f9ce900642a5a349823d, Ce b9932dcaa0c3f11568a65c9a6c19993675581d4c), ERRATA-004 (sha256 4b8de161474139cd24976897804a717ad94c9beaa89a2f74da492e0e845b2061, Ce a1b15ff1eb088860a50ec3dbbc7c98abd985e3c6), ERRATA-005 (sha256 34408e04bf832446d376cc5dd679a4fc4f4afc20b8d1be472c640d75be1d194e, Ce 02aa62b3c678a97026fb2982a9921242d74f68d4)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

ERRATA-006: BT4-FUTILITY-01 R-4 lock token(비난수 최소 token), lock 스키마 g7_lock/2, lock 필드 목록 정정,
            lock 구조적 유효성의 단일 기준
BASE: ERRATA-005 (ACCEPTED, Ce5 02aa62b). ERRATA-001~005를 번호 순으로 적용한 뒤 적용한다.

PURPOSE:
- [A] ERRATA-005 R-4 [B] 획득 4의 "무작위 소유 토큰"은 저장소 재현성 규칙(tests/test_v06_randomness.py:
  research/v06 모듈의 OS 엔트로피 금지)과 충돌한다. CLAUDE.md 우선순위(저장소 규칙이 ERRATA보다 위)에 따라
  계약을 고친다.
- [A] ERRATA-005 R-4 [B] 획득 4의 lock 내용 목록에는 schema_version이 없지만, 같은 절의 "유효한 lock"은
  "필드가 정확히 위와 같다"고 정한다. 구현은 schema_version을 포함한다. 이 누락을 바로잡는다.
- [B] lock 파일의 구조적 유효성을 하나의 기준으로 정하고, lock 읽기, 디렉터리 상태 검증, 소유권 확인이
  모두 그 기준을 쓰게 한다. 유효하지 않은 lock이 정상 lock으로 인정되는 경로를 없앤다.
- 잠금의 배타성, released·abandoned·pool 기록의 lock_sha256 소속 판정, abandon, E-BOOT, 조사 절차는 바꾸지 않는다.

CHANGED_CLAUSES:
1. ERRATA-005 R-4 [B] 획득 4의 lock 내용 목록:
   - 맨 앞에 schema_version을 더한다. 값은 "moneylab.bt4_futility_diag.g7_lock/2"다.
   - "무작위 소유 토큰"을 "token(아래 TOKEN 정의)"으로 바꾼다.
   - 그 밖의 필드(pid, 드라이버 프로세스 시작 시각, 시작 UTC, CODE_SHA, 대상 run_id, 대상 job 사용,
     할당 전 기존 job 소속 여부, 대상 job 정책 readback 성공, 정확한 sys.version 문자열, host_id, boot_identity)와
     "예산 수치는 넣지 않는다", "host_id나 boot_identity를 읽지 못하면 lock을 쓰기 전에 STOP한다"는 그대로다.
2. ERRATA-005 R-4 [B] 유효한 lock: 아래 STRUCTURAL_VALIDITY로 대체한다. 기존 조건(canonical JSON, 필드 집합
   정확히 일치, 비었거나 일부만 쓰였거나 읽을 수 없으면 유효하지 않음)을 모두 포함한다.
3. ERRATA-005 R-4 [B] 해제: "소유 토큰"을 "그 lock의 token 값(같은 객체)"으로 바꾼다.
4. ERRATA-005 R-4 [B] 획득 1의 디렉터리 상태 검증(비정상 상태)과 소유권 확인: 아래 SCAN_RULE을 더한다.

TOKEN:
- token은 JSON 객체이며 키는 정확히 "lock_number" 하나다.
- lock_number의 값은 그 lock 파일 이름 NNNNNN이 나타내는 정수 n(획득 3에서 정한 번호)이다.
  타입은 bool이 아닌 int이고 1 이상이다.
- token을 만들 때 난수, OS 엔트로피, secrets 모듈, 연구 seed, 시드 난수 생성기, 해시를 쓰지 않는다.
- token은 획득 3에서 번호 n이 정해진 뒤 lock 내용에 넣고, 획득 4대로 같은 파일 디스크립터로 쓰고 fsync한 뒤 닫는다.
- 직렬화는 lock 전체와 함께 기존 canonical JSON 규칙(정렬 키, (",", ":") 구분자, ensure_ascii=False,
  NaN 금지, 끝 개행, UTF-8)을 그대로 따른다.
- token은 비밀값이 아니며 인증, 권한 부여, 소유권 판정에 쓰지 않는다.

PROPERTIES:
- 번호가 다른 두 lock은 token 값이 다르므로 canonical lock 바이트가 반드시 다르다. 이 차이는 규칙에서 나오며
  확률에 기대지 않는다. 같은 번호의 lock은 O_CREAT|O_EXCL로 하나만 만들어진다.
- released·abandoned·pool 기록이 어느 lock에 속하는지는 ERRATA-005대로 lock 바이트 sha256으로 판정한다.
  바이트가 다른 두 lock의 sha256이 다르다는 것은 SHA-256의 충돌 저항성 가정에 따른 것이며, 수학적으로 충돌이
  불가능하다는 뜻이 아니다. 이 가정은 ERRATA-005가 이미 쓰고 있으며, 이 ERRATA는 그것을 새로 도입하거나
  강화하지 않는다.
- token은 프로세스, host, 사용자의 고유 식별을 주장하지 않는다. 그 근거는 기존 pid, driver_creation_time, host_id다.

STRUCTURAL_VALIDITY (lock 파일 자체의 유효성, 단일 기준):
- 다음을 모두 만족하는 lock 파일만 유효하다.
  1. 파일 이름이 NNNNNN.lock(6자리, 1 이상) 형식이다.
  2. 내용이 canonical JSON이고 읽을 수 있다(비었거나 일부만 쓰였거나 손상되지 않음).
  3. 키 집합이 CHANGED_CLAUSES 1의 필드 집합과 정확히 같다.
  4. schema_version이 "moneylab.bt4_futility_diag.g7_lock/2"다.
  5. token이 객체이고 키 집합이 정확히 {"lock_number"}이며, 값이 bool이 아닌 int이고, 1 이상이며,
     파일 이름 NNNNNN의 정수와 같다.
- 이 기준은 하나의 공통 검증으로 정의되며, lock 읽기(유효한 lock 내용 또는 유효하지 않음), 디렉터리 상태 검증,
  소유권 확인, abandon 신청 전 검증, 조사 보고가 모두 같은 기준을 쓴다. 각 지점이 따로 다른 기준을 두지 않는다.
- 유효하지 않은 lock은 host_id와 boot_identity를 신뢰할 수 없으므로 E-BOOT가 성립하지 않는다(ERRATA-005 그대로).
- 구조적 유효성은 소속 판정과 별개다. released·abandoned·pool 기록이 어느 lock에 속하는지는 계속 lock_sha256으로만
  판정하며, 이 ERRATA는 그 판정 방식과 순서를 바꾸지 않는다.

SCAN_RULE:
- 디렉터리 상태 검증은 g7-core-lock/의 모든 lock 파일에 STRUCTURAL_VALIDITY를 적용한다. 유효하지 않은 lock이
  하나라도 있으면 짝(released·abandoned) 유무와 관계없이 비정상 상태이며 STOP_FOR_USER_DECISION이다.
- 이 검사는 ERRATA-005의 기존 비정상 상태 검사(허용되지 않은 이름, 번호 공백, lock 없는 기록, released와 abandoned
  동시 존재, 다른 lock의 기록, 짝 없는 lock 둘 이상, pool 번호 공백, start 없는 workers, 필드 불일치)를 대신하지
  않고 그에 더해진다. 기존 검사의 판정 기준은 바꾸지 않는다.
- 적용 시점: 다음 번호 획득 전(획득 1), 소유권 확인 시점마다(run 시작, 각 unit 파일 쓰기 직전, 각 execution.json
  쓰기 직전), abandon 신청 전 상태 검증. 소유권 확인은 기존 세 조건(lock 바이트 sha256이 핸들과 같음,
  released·abandoned 없음, 더 큰 번호 없음)과 execution.json 마지막 세션 일치에 더해 이 검사를 한다.
- 이 규칙은 released·abandoned 기록의 lock 번호를 비교하지 않는다.

LEGACY (/1 및 그 밖의 유효하지 않은 lock):
- schema_version이 g7_lock/1인 lock, 문자열 token을 가진 lock, 그 밖에 STRUCTURAL_VALIDITY를 만족하지 않는 lock은
  자동으로 승계, 변환, 수정, 삭제, abandon하지 않는다(추가 전용 유지). 자동 마이그레이션은 없다.
- 그런 lock이 g7-core-lock/에 하나라도 있으면, 짝이 있든 없든 다음 번호를 획득하지 않고 STOP_FOR_USER_DECISION으로
  보고한다. 처리 방법은 사용자가 정하며, 이 ERRATA는 처리 방법을 정하지 않는다.
- ERRATA-005는 최상위 lock에 짝이 있으면 다음 번호 획득을 허용했다. 이 ERRATA는 그 허용을 유효한 lock에 한정한다.
  삭제·수정 금지와 추가 전용 원칙은 그대로다.

OWNERSHIP (판정 방식 변경 없음):
- 소유권 확인은 ERRATA-005대로 lock 번호와 lock 바이트 sha256(핸들), released·abandoned 부재, 더 큰 번호 부재,
  execution.json 마지막 세션 일치로 한다. token은 비교하지 않는다. SCAN_RULE의 구조적 유효성 검사가 더해질 뿐이다.

RESEARCH_RNG_SEPARATION:
- token은 연구 난수 흐름(stats.derived_seed, explicit_seed, random.Random(seed))과 무관하며 어떤 seed에도 쓰이지 않는다.
- 이 ERRATA 적용 뒤 research/v06 모듈에는 OS 엔트로피 사용이 남지 않는다. tests/test_v06_randomness.py는 수정하지 않는다.

REPRODUCIBILITY:
- [사실] lock 파일은 G7 연구용 CORE 실행에서만 만들어지며, 출력 루트 아래 g7-core-lock/ 디렉터리에 있다.
- [사실] run_units는 lock 핸들을 소유권 확인에만 쓰며, token과 lock 내용을 manifest, SHA256SUMS, execution.json,
  unit 파일에 쓰지 않는다.
- [사실] G4c smoke와 보정 run은 lock을 쓰지 않는다.
- [추론] 따라서 token 변경과 SCAN_RULE은 G4c의 "재실행 바이트 일치"와 연구 결과 파일의 바이트에 영향을 주지 않는다.
- [사실] lock 파일 자체는 pid, 시작 UTC, 드라이버 생성 시각을 담으므로 실행마다 바이트가 다르며, 재현 대상이 아니다.
  이는 ERRATA-005와 같다.

ALLOWED_FILES: 변경 없음. 구현은 src/moneylab/research/v06/futility_diag.py와 tests/test_v06_futility_diag.py(G3)
  안에서 한다.

TEST_ACCEPTANCE (G3 TEST_GATES에 더함):
- 공통 원칙: 기존 assertion은 삭제하거나 완화하지 않는다. 기존 테스트는 fixture(테스트 입력 생성)만 바꿀 수 있으며,
  그 경우에도 기대 결과(match 문구, 예외 종류, 비교식의 엄격성)는 유지한다. tests/test_v06_randomness.py는 수정하지 않는다.
- T-6a (스키마와 구조): 새로 획득한 lock의 schema_version이 g7_lock/2이고, token이 정확히 {"lock_number": n}
  (type이 int이며 bool이 아님)이며, n이 파일 이름 번호와 같고, 키 집합이 CHANGED_CLAUSES 1의 필드 집합과 같으며,
  lock 읽기 결과가 획득 핸들의 내용과 같다.
- T-6b (유효하지 않은 변형): 공통 검증과 lock 읽기가 다음을 모두 유효하지 않음으로 판정한다: /1 스키마,
  문자열 token, token 없음, 추가 키가 있는 token, lock_number가 True·0·-1·1.0, lock_number와 파일 번호 불일치,
  NNNNNN.lock 형식이 아닌 이름, 빈 파일, 일부만 쓰인 파일.
- T-6c (번호별 바이트 차이): 같은 입력 내용으로 두 번 획득하면 두 lock 파일의 바이트와 sha256이 다르고,
  디코딩한 JSON에서 다른 키는 token뿐이다.
- T-6d (released): n.released의 token이 그 lock의 token과 같다. lock 1의 released 바이트를 lock 2의 released
  자리에 두면 STOP_FOR_USER_DECISION("not a record")이다. 기존 0 sha 사례도 그대로 유지한다.
- T-6e (SCAN_RULE과 소유권 확인): T-6b의 각 변형이 g7-core-lock/에 짝 있는 경우와 짝 없는 경우 모두,
  디렉터리 상태 검증과 다음 번호 획득이 STOP_FOR_USER_DECISION이다. 짝 있는 /1 lock은 다음 번호 획득을 막는다.
  소유권 확인(LockHandle.check())은 자기 lock이 유효해도 디렉터리에 유효하지 않은 lock이 있으면
  STOP_FOR_USER_DECISION이다. 기존 비정상 상태 사례는 모두 유지하며, 특히 "more than one unpaired"와 "gap" 사례는
  같은 match 문구로 유지한다. 구조적 유효성 검사가 먼저 걸리는 사례는 fixture만 해당 번호의 유효한 /2 lock으로
  바꾼다.
- T-6f (회귀): tests/test_v06_randomness.py가 수정 없이 통과한다. 기존 lock·scan·abandon·E-BOOT·G7 FAKE 테스트가
  assertion 삭제·완화 없이 통과한다. 전체 pytest(WO:390, 승인된 기본 명령)가 failed 0 / errors 0이다.

UNCHANGED:
- lock 번호 규칙(6자리, 1부터, 공백 없음), 허용 파일명, O_CREAT|O_EXCL·fsync·추가 전용, 획득 2–3,
  released·abandoned 절차와 lock_sha256 소속 판정, NON_BOOT_ABANDON = DISALLOWED, E-BOOT 정의·판독·RB-1 제한,
  E-PID·E-WORKERS·E-TREE, PID·생성 시각 검증, E-POOL-START·E-WORKERS 필드와 스키마, UDR 문법과 user_decision/1,
  R-4c, R-9, G7_POOL_FAILURE_POLICY, Guard 정책, DC10 연구 seed 규칙과 이름공간, 사전등록·config, PROTECTED_FILES.
- released·abandoned 기록의 lock 번호 비교 강화는 이 ERRATA에 넣지 않는다(별도 후보).

SECURITY_IMPACT: 없음. 비밀값을 만들거나 기록하지 않는다. 기록되는 식별 정보는 ERRATA-005의 lock 필드와 같다.
ACCEPTANCE: 이 ERRATA의 수락은 SOURCE·TEST 수정, 테스트 실행, ERRATA 파일 생성, 커밋의 승인을 포함하지 않는다.
            각각 별도로 승인한다.
