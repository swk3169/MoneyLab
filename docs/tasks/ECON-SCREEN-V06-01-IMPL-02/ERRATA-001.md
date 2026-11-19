# ERRATA-001: ECON-SCREEN-V06-01-IMPL-02 — 지원하지 않는 RUNWATCH_HELP 검사 제거와 CLEAN_COMMIT_E2E 재개 절차

STATUS: ACCEPTED
TASK_ID: ECON-SCREEN-V06-01-IMPL-02
ERRATA_ID: ERRATA-001
APPLIES_TO: docs/tasks/ECON-SCREEN-V06-01-IMPL-02/WORK_ORDER.md (C1 3e5dd495fe1f1e49d8f7694b9ff77620f38b5357, sha256 f74737e66b108cbc2c550acf978ca5bde9b8c8517b740d962f16bf7b416cc26b)
IMPLEMENTATION_COMMIT: eedf28df8d10a7ef7c0e894399f8a62d6fa096c1 (C2, tree fabb223fda83f143464e3fa52a658a4c87c65ae1)

이 파일은 불변이다. 발행(Ce) 후 수정하지 않는다. Work Order와 이 ERRATA가 충돌하면 이 ERRATA가 앞선다. 이 ERRATA가 바꾸지 않은 Work Order 조항은 그대로 유효하다.

## 사건 기록(보존)

- 2026-11-19 CLEAN_COMMIT_E2E에서 Work Order CHECK_COMMANDS의 RUNWATCH_HELP(python -m moneylab.runwatch --help)가 exit 29, 출력 "RUNWATCH ARGUMENT_REJECTED 29"로 실패했다.
- FAILURE_RULES와 BGA-10(F1': COMMIT 이후 실패)에 따라 수정·재실행 없이 STOP했고, 묶음은 BGA-5에 따라 종료됐다.
- 그 시점까지 결과: IMPLEMENTATION_PASS, PRECOMMIT_AUDIT_PASS, COMMIT_PASS. CLEAN_COMMIT_E2E는 미완료다. 이 ERRATA는 그 CLEAN_COMMIT_E2E를 소급해 PASS로 바꾸지 않는다. 실패 기록과 STOP은 그대로 남긴다.

## 원인

- RUNWATCH_SOURCE(a3197059f0c1bc41e41ba0d2c7700836cb795645)의 src/moneylab/runwatch/__main__.py는 도움말을 지원하지 않는다.
  - parse()는 인자에 "--"가 없으면 _ArgumentError를 낸다.
  - 파서는 add_help=False이고, error()는 _ArgumentError를 던진다.
  - main()은 _ArgumentError를 받으면 EXIT_CODES["ARGUMENT_REJECTED"](= 29)를 반환한다.
- 따라서 실패 원인은 RUNWATCH 코드가 아니라, 지원하지 않는 호출을 필수 검사로 정한 Work Order 문안이다.

## 정정

- E1 Work Order CHECK_COMMANDS의 RUNWATCH_HELP 항목을 삭제한다. CLEAN_COMMIT_E2E의 "RUNWATCH_HELP 1회"도 삭제한다.
- E2 대체 명령(import 확인 등)이나 새 검사 명령은 추가하지 않는다.
- E3 RUNWATCH 반입 검증의 근거는 다음 두 가지로 한다.
  - RUNWATCH 5개 파일의 blob ID가 RUNWATCH_BLOBS와 같음. 반입 직후, staging, C2 커밋의 세 시점에서 이미 확인됐다.
  - tests/test_runwatch.py가 C2 기준 PYTEST_TARGET에서 통과했고 skip이 없었음.
- E4 RUNWATCH 코드와 경제성 선별 구현·시험 코드는 바꾸지 않는다. 이 ERRATA의 커밋은 이 파일 하나만 추가한다.

## 정정 커밋(Ce) gate: ERRATA_FREEZE

- 승인 형식: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-IMPL-02 ERRATA_FREEZE WO@3e5dd495fe1f1e49d8f7694b9ff77620f38b5357 ERRATA_SHA256=<64 hex> ERRATA_BYTES=<n> ERRATA_LF=<n>
- 이 gate는 묶을 수 없다(BGA-1).
- 진입 확인: HEAD = IMPLEMENTATION_COMMIT, tree = fabb223fda83f143464e3fa52a658a4c87c65ae1, clean. Work Order·사전등록 blob 해시가 승인값과 같고, docs/tasks/ECON-SCREEN-V06-01-IMPL-02/ERRATA-001.md가 없다.
- ERRATA 원문을 승인된 세션 원문에서 재현해 승인 해시·바이트·LF와 대조한 뒤, Write 1회로 docs/tasks/ECON-SCREEN-V06-01-IMPL-02/ERRATA-001.md를 만든다.
- git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/ECON-SCREEN-V06-01-IMPL-02/ERRATA-001.md 1회
- staged 확인: staged 집합이 A 해당 파일 하나, staged blob 내용이 승인값, git diff --cached --check exit 0.
- Ce 커밋 1회. 메시지 docs(task): add ECON-SCREEN-V06-01-IMPL-02 ERRATA-001, 본문·trailer 없음.
- Ce 확인
  - parent(Ce) = IMPLEMENTATION_COMMIT
  - C2..Ce 변경 = A docs/tasks/ECON-SCREEN-V06-01-IMPL-02/ERRATA-001.md 하나
  - git diff --name-only IMPLEMENTATION_COMMIT Ce -- src tests docs/backtest_design.md 결과가 비어 있음. 구현·시험·설계 문서 blob이 C2와 같다
  - clean
- 종료 시 PRESERVATION_CHECK. TASK ref의 기대 변화는 C2 -> Ce다.
- 예상 ASK: task-contract(ERRATA 최초 Write) 최대 1회, git-commit 1회. 그 밖의 ASK·거절·DENY는 STOP한다.

## CLEAN_COMMIT_E2E 재개

- 승인 형식: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-IMPL-02 CLEAN_COMMIT_E2E WO@3e5dd495fe1f1e49d8f7694b9ff77620f38b5357 ERRATA: ERRATA-001@<Ce SHA>
- 단일 gate이며 묶음이 아니다.
- 구현 식별 커밋은 IMPLEMENTATION_COMMIT(eedf28df8d10a7ef7c0e894399f8a62d6fa096c1)로 고정한다.
- 진입 확인
  - HEAD = Ce, clean, parent(Ce) = IMPLEMENTATION_COMMIT
  - C2..Ce 변경이 ERRATA 파일 하나뿐이다
  - Work Order·ERRATA·사전등록 blob 해시가 승인값과 같다
- 재사용(재실행하지 않음)
  - C2에서 실행해 통과한 PYTEST_TARGET(215 passed, skip 0, 486.67 s)과 CLI_HELP(정상 출력)를 재사용한다.
  - 재사용 조건 R-a: 그 실행 당시 HEAD = IMPLEMENTATION_COMMIT이고 clean이었다(실행 전후 status 기록).
  - 재사용 조건 R-b: IMPLEMENTATION_COMMIT과 Ce 사이에 src, tests, docs/backtest_design.md 경로의 blob 변경이 없다(git diff 결과 비어 있음).
  - 재사용 조건 R-c: 진입 시 작업 트리가 clean이다.
  - 근거는 세션의 해당 실행 출력과 git 조회로 보고한다. 하나라도 확인할 수 없거나 바이트가 다르면 재사용하지 않고 STOP해 보고한다. 이때 다른 검사로 바꾸지 않는다.
  - 전체 pytest와 대상 pytest는 다시 실행하지 않는다.
- 이번 gate에서 수행하는 남은 확인
  - 커밋과 작업 파일의 연결: ALLOWED_FILES 10개의 작업 파일 내용(LF 정규화)과 Ce의 blob 내용 SHA-256이 같고, RUNWATCH 5개의 blob ID가 RUNWATCH_BLOBS와 같다.
  - 검사 전후 git status(ignored 포함) 비교
  - F0IMPL02 대비 PRESERVATION_CHECK. TASK ref는 생성 -> C1 -> C2 -> Ce를 기대 변화로 한다. 나머지 분류는 Work Order와 같다.
- 보고: CLEAN_COMMIT_E2E_PASS 여부. 재사용한 검사와 그 근거, R1의 임시 저장소 시험의 증명 한계, R1의 B1 축소(9,999 -> 3), BGA-8(B) 독립 검토 미완료를 밝힌다.

## 유지 사항

- 사전등록, Work Order 본문, 이전 task의 기록, DEVIATION·사건·이탈·보류 기록, DATAQ 후보는 바꾸지 않는다.
- 실데이터 수집·열람·변환·선별 실행, 합성 자원 측정, RUNWATCH로 실제 명령을 감시하는 실행, 네트워크, 설치, push·PR은 이 ERRATA로 허용되지 않는다.
