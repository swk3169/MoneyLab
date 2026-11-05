# ERRATA: BT4-FUTILITY-01 ERRATA-007

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-FUTILITY-01-ERRATA-007
TASK_ID: BT4-FUTILITY-01
TARGET_WORK_ORDER: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md @ 7ac09a674e68cbc95dd5c934f2d3580939fd02f0 (sha256 c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b)
PRIOR_ACCEPTED_ERRATA: ERRATA-001 (sha256 9fcac5a97605a85be68612ba4a465c5f24b8c5b5594f3a801ca5e551993d24bf, Ce 616ed51f257a8cfa2d2c080067b09258651930e9), ERRATA-002 (sha256 0ca8ab961af350b10a2660ca8ee7b8c4bfab2757ee2b6b1ae61ffcfeee7308fe, Ce 2eb876e02456405667f466a124f745b3dd4fba3c), ERRATA-003 (sha256 9b8fcf9f30d8b525237a63b00f599add0a2fbcb33cb0f9ce900642a5a349823d, Ce b9932dcaa0c3f11568a65c9a6c19993675581d4c), ERRATA-004 (sha256 4b8de161474139cd24976897804a717ad94c9beaa89a2f74da492e0e845b2061, Ce a1b15ff1eb088860a50ec3dbbc7c98abd985e3c6), ERRATA-005 (sha256 34408e04bf832446d376cc5dd679a4fc4f4afc20b8d1be472c640d75be1d194e, Ce 02aa62b3c678a97026fb2982a9921242d74f68d4), ERRATA-006 (sha256 63c08d10131a71911e849f60b4ff09c542853821c1a3458a68369ffa1bc6fd11, Ce 31d15edf41530c2b834016bc20827e5819070286)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

ERRATA-007: BT4-FUTILITY-01 research identity의 계약 해시 범위(ERRATA-001~007과 일반 원칙)와 G5 pilot·G6·G7
            진입의 단계 간 실행 신원 검증
BASE: ERRATA-006 (ACCEPTED, Ce6 31d15ed). ERRATA-001~006을 번호 순으로 적용한 뒤 적용한다.

PURPOSE:
- [A] ERRATA-005 R-1 [B] G7 진입 검사의 "CODE_SHA·사전등록·config·ERRATA sha256 불일치(research_identity)"는
  ERRATA의 범위를 정하지 않는다. 구현(futility_diag.py CONTRACT_FILES / CONTRACT_SHA256)은 ERRATA-001~005만
  명시적으로 검증하며 ACCEPTED ERRATA-006이 빠져 있다.
- [B] 구현은 각 실행 안에서만 run_spec과 현재 실행 신원을 비교한다(check_run_identity). G5에서 기록된
  calibration identity와 pilot run_spec을 G6·G7의 현재 실행 신원과 비교하는 검사가 없어, 서로 다른 커밋에서
  G5·G6·G7이 실행되어도 STOP하지 않는다(정적 분석, CLAUDE_REPORTED).
- [C] WO:70(G7 "CODE_SHA·사전등록 sha256·G6 고정값 확인")과 WO:403(CODE_SHA clean worktree)을 단계 간에도
  강제한다. 채팅 결정은 저장소 증거가 아니므로(WO:105) 이 ERRATA로 고정한다.

CHANGED_CLAUSES:
1. 계약 해시 범위 (ERRATA-005 R-1 [B]의 해석 확정)
   - 일반 원칙: C3(CODE_SHA) 생성 전에 Ce 커밋으로 고정된 모든 ACCEPTED ERRATA를 research_identity의 명시적
     계약 해시 검증 대상으로 한다.
   - 이 원칙에 따라 research_identity의 contract_sha256은 정확히 다음 9개 키를 가진다: config, prereg,
     ERRATA-001, ERRATA-002, ERRATA-003, ERRATA-004, ERRATA-005, ERRATA-006, ERRATA-007.
   - 각 값은 해당 파일 LF 바이트의 sha256이다. ERRATA-NNN의 값은 그 ERRATA를 고정한 Ce 커밋의 blob에서 계산한다.
     blob에 CR이 있으면 계산하지 않고 STOP한다.
   - ERRATA-007의 sha256은 이 본문에 기록하지 않는다. Ce7 커밋 뒤 Ce7 blob에서 계산해 코드 상수에만 기록한다.
   - 하나라도 다르면 StopImplementation이다(기존 규칙 그대로).
   - C3 뒤에 수락되는 ERRATA는 이 목록에 자동으로 들어가지 않는다. 그 ERRATA가 G5 이후의 실행에 영향을 주면
     WO:84(G3 rollback, 명시적 승인)와 WO:87(G7 이후는 새 study)을 따른다.
2. 단계 간 실행 신원 (새 STOP 지점)
   - 기호: CAL = G5 calibration.json의 identity. PILOT = G5 pilot run 디렉터리의 run_spec. NOW = 진입 시점에
     research_identity(…, calibration_sha256 = 사용하는 calibration 파일의 sha256)로 계산한 실행 신원.
   - 단계 불변 필드(7개): git_head, git_tree, worktree_clean, base_sha, futility_diag_source,
     mcv06_source_identity, contract_sha256.
   - 단계별 가변 필드(1개): calibration_sha256. CAL에서는 null이어야 하고(기존 validate_calibration 그대로),
     NOW에서는 사용하는 calibration 파일의 sha256과 같아야 한다. CAL과 NOW 사이에서 이 필드를 동일 비교하지 않는다.
   - G5 pilot 진입: CAL과 NOW의 단계 불변 필드 7개가 모두 같아야 한다.
   - G6 진입: CAL과 NOW의 단계 불변 필드 7개가 모두 같고, 다음이 모두 성립해야 한다.
       PILOT["code_sha"] = NOW["git_head"]
       PILOT["code_tree"] = NOW["git_tree"]
       PILOT["config_sha256"] = NOW["contract_sha256"]["config"]
       PILOT["prereg_sha256"] = NOW["contract_sha256"]["prereg"]
   - G7 진입: G6 진입과 같은 조건이다. 검사는 대상 job 할당 전에 하며(ERRATA-005 R-4a의 git 호출 순서 유지),
     새 검사는 git을 다시 호출하지 않고 이미 계산한 NOW를 쓴다.
   - CODE_SHA(git_head·code_sha)와 git_tree(code_tree)를 둘 다 비교한다. 커밋이 같으면 tree가 결정되지만,
     기록 값의 변조·불일치를 잡기 위해 tree도 독립적으로 비교한다.
3. 실패 처리 (fail-closed)
   - 다음은 모두 StopImplementation이다: 단계 불변 필드의 불일치; PILOT의 code_sha·code_tree·config_sha256·
     prereg_sha256 불일치; CAL에 IDENTITY_FIELDS 중 하나가 없거나 남는 필드가 있음; CAL.git_tree가 40자리 소문자
     hex가 아님; PILOT run_spec 파일이 없거나 canonical이 아니거나 validate_run_spec을 통과하지 못함;
     NOW.calibration_sha256이 사용하는 calibration 파일의 sha256과 다름.
   - 검증은 그 단계의 연구 산출물을 쓰기 전에 한다. 검증이 실패하면 그 단계는 연구 산출물을 만들거나 바꾸지 않는다
     (G5 pilot: run 디렉터리의 어떤 파일도, G6: g6/와 execution.json의 g6_timing, G7: lock·run 디렉터리·v4 출력).
   - 메시지는 다른 필드 이름을 나열한다. 값을 추정·대체하거나 재시도하지 않는다.

PRESERVED:
- calibration provenance 검증(pilot run_inputs와 calibration의 sha256·E1 값), validate_research_block,
  verify_g6의 pilot 파일 참조 검증, check_run_identity, validate_calibration, validate_run_spec,
  write_calibration의 verify_research_identity는 그대로 두고, 위 2는 이들에 더한다.
- G6 요약 스키마(g6_summary/1, G6_FIELDS)와 G7 manifest의 G6 섹션(ERRATA-004 R-5)은 바꾸지 않는다.
  G7은 VERIFIED g6/가 sha256로 참조하는 pilot run_spec에서 PILOT 값을 읽는다.
- TEST_FIXTURE 경로(ERRATA-003 R-7, G4c smoke, fixture_identity)는 바꾸지 않는다. 위 2는 연구 진입 함수
  (G5 pilot, G6 summarize, G7 core)에만 적용한다. 공용 함수(g6_summary, write_g6, verify_g6, run_units)에는
  넣지 않는다.

EVIDENCE_LIMITATION:
- [사실] G6을 실행한 시점의 HEAD는 g6/에 기록되지 않는다(스키마 불변). G6이 같은 CODE_SHA에서 실행되었다는 것은
  G6 진입 검사(위 2)가 쓰기 전에 STOP한다는 구현에 의존하며, 사후에 g6/ 파일만으로 증명되지는 않는다.
- [사실] G7에서 G6 요약을 다시 계산해 바이트를 비교하는 검사는 이 ERRATA에 넣지 않는다(별도 후보).

ALLOWED_FILES: 변경 없음. 구현은 src/moneylab/research/v06/futility_diag.py와 tests/test_v06_futility_diag.py(G3)
  안에서 한다.

REQUIRED_G3_PATCH (최소 범위):
- CONTRACT_FILES와 CONTRACT_SHA256에 ERRATA-006(sha256 63c08d10131a71911e849f60b4ff09c542853821c1a3458a68369ffa1bc6fd11)과
  ERRATA-007(Ce7 blob에서 계산한 값) 항목을 추가한다. 주석의 Ce 목록과 모듈 docstring의 Contract 목록에
  ERRATA-006(31d15ed)과 ERRATA-007(Ce7)을 추가한다.
- 단계 간 검증 함수 하나를 추가한다(위 2·3). git을 호출하지 않고, 호출자가 이미 계산한 NOW를 받는다.
- 호출 위치: G5 pilot(NOW 계산 직후, run 디렉터리 쓰기 전), G6 summarize(NOW 계산 뒤, g6/ 쓰기 전),
  G7 core(NOW 계산 뒤, 대상 job 할당과 lock 획득 전). G6과 G7은 pilot run_spec을 읽어 넘긴다.
- validate_calibration의 RESEARCH 분기에 identity.git_tree 40자리 소문자 hex 검사를 추가한다.

TEST_ACCEPTANCE (G3 TEST_GATES에 더함):
- 공통 원칙: 기존 assertion은 삭제하거나 완화하지 않는다. 기존 테스트는 fixture만 바꿀 수 있으며 기대 결과는
  유지한다(ERRATA-006 원칙 그대로).
- T-7a (계약 범위): CONTRACT_FILES의 키가 정확히 config, prereg, ERRATA-001~007이고, 각 실제 파일의 LF sha256이
  CONTRACT_SHA256과 같다. ERRATA-006 또는 ERRATA-007의 바이트를 바꾸면 research_identity가 StopImplementation이다.
- T-7b (정상): CAL·PILOT·NOW가 일치하면 G5 pilot·G6·G7 진입 검사를 통과한다.
- T-7c (불일치): 단계 불변 필드 7개 각각, PILOT의 code_sha·code_tree·config_sha256·prereg_sha256 각각이 하나씩
  다를 때 해당 단계가 StopImplementation이다.
- T-7d (누락·형식): CAL 필드 누락·추가, CAL.git_tree 형식 오류(대문자, 짧은 값, 숫자 타입), PILOT run_spec 없음·
  비canonical·필드 누락·형식 오류, NOW.calibration_sha256 불일치가 모두 StopImplementation이다.
- T-7e (가변 필드): CAL.calibration_sha256 = null이고 NOW.calibration_sha256 = 파일 sha256이면 통과하며,
  둘 사이를 동일 비교하지 않는다.
- T-7f (쓰기 전 차단): T-7c·T-7d의 각 사례에서 그 단계의 연구 산출물이 생성되거나 바뀌지 않는다. G7은 단계 간
  검사가 대상 job 할당과 lock 획득보다 먼저 실행된다(FAKE api 호출 순서와 lock 디렉터리 부재).
- T-7g (회귀): TEST_FIXTURE smoke와 기존 identity·calibration·G6·G7 FAKE 테스트가 assertion 삭제·완화 없이
  통과한다. 전체 pytest(WO:390)가 failed 0 / errors 0이다. WO:391·392가 충족된다.

UNCHANGED:
- 사전등록·config, 가설·지표·판정 규칙, seed 규칙, lock(g7_lock/2)·SCAN_RULE·E-BOOT, run_spec·run_inputs·
  manifest·calibration·g6_summary 스키마, PROTECTED_FILES, Guard 정책, G7_POOL_FAILURE_POLICY.

SECURITY_IMPACT: 없음. 새로 기록하는 값이 없고, 기존 identity 값만 비교한다.
ACCEPTANCE: 이 ERRATA의 수락은 ERRATA 파일 생성, Ce7 커밋, ERRATA-007 sha256 계산, SOURCE·TEST 수정, 테스트 실행의
            승인을 포함하지 않는다. 각각 별도로 승인한다.
