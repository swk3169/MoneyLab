# ERRATA-001: FUTVAL-V8-01-PRECHECK — PRECHECK_EXECUTION 진입 조건의 작업 파일 바이트 기준 정정

이 파일은 불변이다. 수락(Ce) 후 수정하지 않는다.

## Metadata

ERRATA_ID: ERRATA-001
TASK_ID: FUTVAL-V8-01-PRECHECK
STATUS: ACCEPTED
WORK_ORDER_PATH: docs/tasks/FUTVAL-V8-01-PRECHECK/WORK_ORDER.md
WORK_ORDER_SHA256: fe58eac5b71c6fc6a3d11d72887f3f5298b28084aca6996f604d8dd70884b1e7
WORK_ORDER_COMMIT: fdc82e5ef58d2f9e172e9af47569c680649eecfc
IMPLEMENTATION_COMMIT (C2): 155aeef016927615bf8449c9cf1060e497d39f56
IMPLEMENTATION_TREE: 475e50230758004a491f1fec48ee4d155e9ba74f
PRIOR_ERRATA: NONE

## 변경 항목

- PRECHECK_EXECUTION 진입 조건: "HEAD = C2"와 "두 파일 W = C2 commit 내용"
- ALLOWED_ACTIONS·CONTRACT_FILE_EXCEPTION·PROTECTED_FILES: docs/tasks/FUTVAL-V8-01-PRECHECK/ERRATA-001.md 최초 생성 예외
- COMMIT_PLAN: Ce 추가
- PRESERVATION_CHECK: TASK ref 기대 변화
- REQUIRED_REPORT: 구현 식별 커밋(C2)과 실행 기준 HEAD(Ce)의 구분

## 사유

core.autocrlf=true인 작업 트리에서 두 파일의 작업 파일 바이트(W)는 CRLF이고 C2 commit 내용(S)은 LF다. 원문 조건을 글자 그대로 적용하면 내용이 같아도 W ≠ S가 되어 충족할 수 없다. 이 정정은 작업 파일의 실제 바이트 보존과 LF 커밋 내용의 일치를 구분해 적는 것이며, 소스 변경이나 보존 기준 완화를 허용하지 않는다.

## PRECHECK_EXECUTION 진입 조건 (원 조건 "HEAD = C2"와 "두 파일 W = C2 commit 내용"만 아래로 대체한다)

- HEAD는 실행 기준 HEAD Ce이고, parent(Ce) = C2이며 C2..Ce 변경은 A docs/tasks/FUTVAL-V8-01-PRECHECK/ERRATA-001.md 하나다. 작업 트리는 clean(tracked·index 변경 없음, untracked 없음)이며 ignored 집합은 ENV_SETUP 종료 시점과 같다.
- 두 파일의 raw W SHA-256은 CLEAN_COMMIT_E2E에서 확정한 다음 값과 같다.
  - src/moneylab/research/v06/futval_v8_01.py: 059bc558e54c77a29d1bf00b0d7c9eb711cf8201ec4fc1f66da47cc5989d1106
  - tests/test_futval_v8_01.py: 9e9fc92b6711a9edfa868eb4c42e7eab769b27f0f3a21aaebaa04cb408558ca8
- 작업 파일의 줄바꿈은 CRLF 또는 LF만 허용하며 단독 CR은 없다.
- CRLF만 LF로 바꾼 작업 파일 바이트(메모리 계산)가 C2의 해당 commit blob 내용과 정확히 같다. 그 내용의 SHA-256은 다음 값이다.
  - src/moneylab/research/v06/futval_v8_01.py: 113bd27b1a5df307e5007db56740c6ad95da70070407efb6adc91344ff1bb79c
  - tests/test_futval_v8_01.py: 5ba57dd0c715967bfa3fe936be53b1b5fb803e440d7746f19e23e399d96b727f
- 실행 기준 HEAD에서 두 파일의 blob은 C2의 blob과 같다.
- 실제 작업 파일을 정규화하거나 다시 쓰지 않는다. 비교는 메모리에서만 한다.
- .gitattributes, core.autocrlf 등 속성·필터 설정과 파일의 다른 바이트는 변경하지 않는다.

## ERRATA-001 최초 생성 예외 (ALLOWED_ACTIONS·CONTRACT_FILE_EXCEPTION·PROTECTED_FILES)

- 이 예외는 사용자의 이 ERRATA 수락과 별도 승인 GATE_AUTHORIZATION: FUTVAL-V8-01-PRECHECK ERRATA_001_CREATION_ONLY가 모두 있을 때에만 적용한다. ERRATA 문안 자체는 권한을 만들지 않는다.
- ALLOWED_ACTIONS 추가(ERRATA_001_CREATION_ONLY): docs/tasks/FUTVAL-V8-01-PRECHECK/ERRATA-001.md를 승인된 바이트로 Write 1회, git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/FUTVAL-V8-01-PRECHECK/ERRATA-001.md 1회, Ce 커밋 1회.
- CONTRACT_FILE_EXCEPTION 추가: A docs/tasks/FUTVAL-V8-01-PRECHECK/ERRATA-001.md (ERRATA_001_CREATION_ONLY 전용, 승인 바이트로 최초 1회).
- PROTECTED_FILES의 docs/tasks/FUTVAL-V8-01-PRECHECK/** 보호는 이 최초 생성 외에는 그대로다. WORK_ORDER.md와 기존 파일의 수정, 생성 뒤 ERRATA-001.md의 수정, 다른 보호 경로의 변경은 허용하지 않는다.
- Ce 조건: parent(Ce) = C2 (155aeef016927615bf8449c9cf1060e497d39f56), C2..Ce 변경 = A docs/tasks/FUTVAL-V8-01-PRECHECK/ERRATA-001.md 하나, 메시지 docs(task): add FUTVAL-V8-01-PRECHECK ERRATA-001, 본문·trailer 없음.
- Ce 생성은 묶음 대상이 아니다.

## COMMIT_PLAN 추가

- Ce: parent = C2, 변경 = A docs/tasks/FUTVAL-V8-01-PRECHECK/ERRATA-001.md
- CANONICAL_BASE_SHA..Ce의 변경 경로는 WORK_ORDER.md, ERRATA-001.md, ALLOWED_FILES 두 개, 모두 네 개뿐이다. 커밋 본문과 trailer는 넣지 않는다.

## PRESERVATION_CHECK의 TASK 기대 변화

- 이 task에 한해 TASK(refs/heads/codex/futval-v8-01-precheck)의 기대 변화는 생성 -> C1 -> C2 -> Ce다.
- C2 -> Ce 이동은 위 ERRATA-001 생성 커밋 1회뿐이다. 그 밖의 TASK 변화는 허용하지 않으며 STOP한다.
- OBSERVED·PRESERVE 분류, 비교 방법, STOP 조건, 기존 F0은 바꾸지 않는다.

## 구현 식별과 실행 식별 (REQUIRED_REPORT)

- 구현 식별 커밋은 C2다. 두 파일의 blob과 commit 내용 S는 C2 기준이며, 출력 디렉터리 data/processed/futval_v8_01/precheck-<C2 SHA 앞 12자>-a1은 C2로 정한다(precheck-155aeef01692-a1).
- 실행 기준 HEAD는 Ce다. precheck.json의 code.commit에는 git_provenance가 읽는 실행 시점 HEAD(Ce)가 기록된다.
- REQUIRED_REPORT와 RESULT_REPORT는 C1(Work Order), C2(구현), Ce(ERRATA-001, 실행 기준 HEAD)를 구분해 보고한다.
- Ce 생성 뒤 PRECHECK_EXECUTION 진입 전에 계약 해시(Work Order, ERRATA-001)와 보호 소스 blob을 다시 확인한다.

## 범위와 불변

- 이 정정은 위 변경 항목(PRECHECK_EXECUTION 진입 조건, ERRATA-001 최초 생성 예외, COMMIT_PLAN, PRESERVATION_CHECK의 TASK 기대 변화, REQUIRED_REPORT의 커밋 식별 구분)에만 적용한다. 그 밖의 계약 조건과 이미 끝난 gate의 판정은 바꾸지 않는다.
- 사전등록(docs/research_futval_v8_01_preregistration.md, d77549ed4cc732f0b2fb0151fcf17913d319ce8e0de929827fc3a8c9c7ea9b91), 통계 설계, 구현·테스트(C2의 두 파일), PRECHECK_COMMAND, 실행 횟수(1회), 시간 제한(600초), PRESERVATION_CHECK의 분류·비교·STOP 조건, 그 밖의 진입 조건(출력 디렉터리 부재와 ignored 확인 포함)은 바꾸지 않는다.
- 기존 기록을 소급해 없애지 않는다: WORKSPACE_SETUP의 LF 보고 오류(274로 보고, 실제 275), IMPLEMENTATION 묶음에서 승인된 CHECK_1 문자열 변형(출력 자르기 추가)과 그에 따른 권한 거절, 그 묶음의 STOP.
- Work Order의 유지할 한계(방법 1·2의 독립성 한계, 디스크 소스 대조와 모듈 위치 기반 root의 인증 한계, 시간·메모리 미측정)와 BGA-8(B) 독립 검토 필요 표시는 그대로 유지한다.
- 이 ERRATA는 ERRATA-001 생성과 PRECHECK_EXECUTION의 실행 권한을 만들지 않는다. 각각 별도 GATE_AUTHORIZATION이 필요하다.
