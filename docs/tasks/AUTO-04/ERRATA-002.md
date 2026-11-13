# ERRATA: AUTO-04 ERRATA-002

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: AUTO-04-ERRATA-002
TASK_ID: AUTO-04
TARGET_WORK_ORDER: docs/tasks/AUTO-04/WORK_ORDER.md @ 2ffd7d9c6e50c669e63e2b392f91284c1205e1df (sha256 8f5e8b87b543dc80fa42c20fd0716d31147eb227f3d8c6a440dda2024b66f026)
PRIOR_ERRATA: docs/tasks/AUTO-04/ERRATA-001.md @ b73e373aff8926469e483e8d2b567f10a4e14498 (sha256 ec25b5c823f7435130858c547b507d979c5c9294f28e2b238920666c37aead74)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자 (ERRATA_002_CREATION_ONLY 승인문)

## CHANGED_FIELDS

CHANGED_FIELDS:
- ALLOWED_ACTIONS.ERRATA_002_CREATION_ONLY (신설)
- ALLOWED_ACTIONS.COMMIT
- PROTECTED_FILES (최초 생성 예외 1건 추가)
- COMMIT_PLAN
- GATE_TRANSITION_RULES (승인문 형식 항목 추가)
- DESIGN_CONTRACT.D6 (이번 사례 한정 판정 추가, 일반 판정 규칙 유지)
- DESIGN_CONTRACT.D9 (완료 판정 문장의 AC 범위 교체, 이번 사건 한정 처리 추가)
- DESIGN_CONTRACT.D13 (ERRATA-001 신설 필드, 포함 항목과 기록 규칙 추가)
- DESIGN_CONTRACT.D14 (신설)
- DESIGN_CONTRACT.D15 (신설)
- TEST_GATES (항목 추가)
- ACCEPTANCE_CRITERIA.AC1, AC2 (교체), AC11 (신설), 완료 판정 문장 (교체)
- REQUIRED_EVIDENCE (항목 추가)
- STOP_CONDITIONS (항목 추가)

위에 적지 않은 필드와, 적은 필드 안에서 이 ERRATA가 다시 쓰지 않은 항목은 Work Order와 ERRATA-001 그대로 유지한다. Work Order와 ERRATA-001 파일은 변경하지 않는다.

## RATIONALE

RATIONALE: Work Order ALLOWED_ACTIONS.EXECUTION_ONLY는 실행 산출물이 data/processed/workstate/AUTO-04/와 data/processed/runlog/AUTO-04/에만 생긴다고 정했다. 그러나 E6에서 그 밖의 ignored 디렉터리 src/moneylab/__pycache__/와 src/moneylab/knowledge/__pycache__/(파일 8개)가 관측되었다. 계약 후보 작성·검토 단계에서 executor 자식 Python의 바이트코드 생성 가능성을 검토하지 않은 설계 누락이다(DEVIATIONS #9). 승인된 E0–E6 명령은 승인 원문대로 각 1회 실행되었다. 이 ERRATA는 그 불일치를 이력으로 고정하고, 추가 실행 없이 사례 문서화와 감사를 진행하기 위한 최소 정정이다.

## AUTHORITY

AUTHORITY: 이 ERRATA는 자기 자신의 생성 권한을 부여하지 않는다. docs/tasks/AUTO-04/ERRATA-002.md의 최초 생성과 Ce2 커밋은 사용자의 별도 명시적 승인(ERRATA_002_CREATION_ONLY)에 근거한다. 이는 저장소 절대 규칙(CLAUDE.md Work Order 절)이 허용하는 ACCEPTED ERRATA 커밋 절차를 이용하는 것이다. Guard·hook·settings·도구 권한의 판정은 그대로 따르며, 차단되면 우회하거나 재시도하지 않는다. 아래 PROTECTED_FILES 예외 조항은 그 승인된 최초 생성을 계약에 기록할 뿐이다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:

- ALLOWED_ACTIONS.ERRATA_002_CREATION_ONLY: IMPLEMENTATION 안의 하위 단계이며, 사용자의 별도 명시적 승인이 있을 때만 수행한다. 수락된 승인 바이트의 docs/tasks/AUTO-04/ERRATA-002.md를 TARGET_WORKTREE에서 Write 도구로 최초 1회 생성하고, 그 경로만 stage해 Ce2 커밋 1개를 만든다. 메시지는 docs(task): add AUTO-04 ERRATA-002다. 작성 전 메모리 대조와 작성 후·staged·commit blob 해시 대조를 한다.

- ALLOWED_ACTIONS.COMMIT: ALLOWED_FILES만 경로를 지정해 stage하고 구현 커밋 I 1개를 만든다. I의 parent는 Ce2다.

- PROTECTED_FILES (예외 추가): docs/tasks/AUTO-04/ERRATA-002.md의 ERRATA_002_CREATION_ONLY 최초 1회 생성을, 사용자 승인에 따른 보호 대상의 예외로 기록한다. 생성 후 변경하지 않는다. 이 예외는 ALLOWED_FILES에 속하지 않는다.

- COMMIT_PLAN:
  - C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/AUTO-04/WORK_ORDER.md 하나 (2ffd7d9c6e50c669e63e2b392f91284c1205e1df)
  - Ce1: parent = C1, 변경 = A docs/tasks/AUTO-04/ERRATA-001.md 하나 (b73e373aff8926469e483e8d2b567f10a4e14498. Work Order와 ERRATA-001의 "Ce"는 Ce1을 뜻한다)
  - Ce2: parent = Ce1, 변경 = A docs/tasks/AUTO-04/ERRATA-002.md 하나
  - I: parent = Ce2, 변경 = A docs/research-intake/2026-11-13/AUTO-04_OFFLINE_INTEGRATION_CASE.md 하나
  - base..I: 위 4개 파일뿐

- GATE_TRANSITION_RULES (추가 항목): Ce2 이후의 승인문에는 ERRATA: ERRATA-001@b73e373aff8926469e483e8d2b567f10a4e14498와 ERRATA: ERRATA-002@<Ce2 SHA>를 함께 적는다. ACCEPTED ERRATA는 번호 순으로 적용하고 뒤 번호가 앞선다.

- DESIGN_CONTRACT.D6 (이번 사례 한정 판정 추가): D6의 일반 판정 규칙은 그대로 유지한다. 이번 사례에 한해 다음을 추가한다.
  - IS1–IS5는 E1–E6 보고 기준으로 모두 충족되었다. 이 사실은 유지한다.
  - 산출물 범위: 불일치. Work Order ALLOWED_ACTIONS.EXECUTION_ONLY의 산출물 범위 밖에 ignored 디렉터리 2개, 파일 8개가 관측되었다.
  - 이번 사례의 통합 시험 최종 판정은 FAIL이다. 사유는 계약 산출물 범위 불일치다.
  - 이력: E6 보고 시점의 통합 시험 판정은 "판정 보류(PENDING_USER_DECISION)"였고, 이후 사용자 결정으로 FAIL로 확정되었다. 이 이력은 삭제하지 않는다.
  - 실행 결과 EVIDENCE_RETURNED, 작업 결과 SUCCEEDED, 저장 결과 STORED_NEW, 조회 결과 MATCHED는 각각 유지하며 FAIL로 바꾸지 않는다.
  - 과거 실행을 계약 준수 SUCCESS로 소급 변경하지 않는다. 이후 어떤 단계도 이번 사례의 통합 시험 최종 판정을 바꾸지 않는다.

- DESIGN_CONTRACT.D9:
  - (교체) Work Order D9 첫 항목의 "AC1–AC10 충족"을 "AC1–AC11 충족"으로 바꾼다.
  - (추가) 이번 사건 한정 처리:
    - 대상 사건은 하나다: E6에서 관측된 src/moneylab/__pycache__/와 src/moneylab/knowledge/__pycache__/(파일 8개)의 산출물 범위 불일치와 DEVIATIONS #9.
    - 이 사건에 한해, D9의 "계약 위반이 있으면 문서화만으로 완료 조건을 충족하지 않는다" 규정은 아래 완료 조건을 모두 충족할 때 적용하지 않는다.
      - ERRATA-002가 ACCEPTED되고 Ce2로 고정됨
      - 사례 기록이 D14의 항목을 모두 공개함
      - 이번 사례의 통합 시험 최종 판정 FAIL과 그 사유가 사례 기록과 최종 보고에 유지됨
      - D15의 캐시 메타데이터 대조에서 변화가 관측되지 않음
      - D15의 단계별 기대 변경 집합을 벗어난 tracked·untracked 변경, D14 기준 ignored 목록 외 새 ignored 항목, 보호 파일 변경, 다른 계약 위반이 없음
      - Work Order, ERRATA-001, ERRATA-002의 해시가 불변
    - 이 예외는 위 사건 하나에만 적용한다. 설명되지 않은 추가 변경, 다른 산출물, 다른 계약 위반에는 기존 D9를 그대로 적용한다.
    - task 완료(COMPLETE)는 통합 시험 결과와 별개로 판정한다. 완료는 통합 시험 FAIL을 바꾸지 않는다.
    - 새 실행 권한을 추가하지 않는다. E0–E6, run_action, store_evidence, load_evidence, snapshot·verify의 재실행, 재저장·재조회, snapshot·runlog 원본 조회, 캐시 정리는 허용하지 않는다. 이후 단계의 캐시 생성도 허용하지 않는다.

- DESIGN_CONTRACT.D13 (ERRATA-001 신설 필드, 추가 항목):
  - 포함 항목에 추가: D14의 사건 기록 전체와 D15의 확인 범위·미확인 범위.
  - 기록 규칙에 추가: 원인 추론은 "추론"으로 표시해 관측 사실과 구분해 기록할 수 있다. 이는 ERRATA-001 D13의 "기록되지 않은 값을 추정하거나 다시 만들지 않는다"에 대한 예외가 아니다. 관측값을 추정으로 대체하지 않으며, 추론을 관측값으로 기록하지 않는다.
  - 기록 규칙에 추가: 파일 시각은 "수정 시각"으로만 표기하고 생성 시각으로 표현하지 않는다. 파일 소유자 이름 등 사용자 식별 정보는 메타데이터에서도 제외한다.

- DESIGN_CONTRACT.D14 사건 기록 (신설):
  - 관측: E6 두 번째 status에서 범위 밖 ignored 디렉터리 2개가 관측되었다. E0와 E2 직후의 ignored 목록에는 없었다. EXECUTION_CLOSEOUT 조사에서 관측한 파일 목록(상대 경로, 바이트, 수정 시각 UTC)은 다음과 같다.
    - src/moneylab/__pycache__/__init__.cpython-314.pyc, 259, 2026-11-13T09:56:36.536360500Z
    - src/moneylab/knowledge/__pycache__/__init__.cpython-314.pyc, 1948, 2026-11-13T09:56:36.539890600Z
    - src/moneylab/knowledge/__pycache__/context.cpython-314.pyc, 18385, 2026-11-13T09:56:36.564449800Z
    - src/moneylab/knowledge/__pycache__/model.cpython-314.pyc, 5915, 2026-11-13T09:56:36.694447200Z
    - src/moneylab/knowledge/__pycache__/query.cpython-314.pyc, 14972, 2026-11-13T09:56:36.715175800Z
    - src/moneylab/knowledge/__pycache__/load.cpython-314.pyc, 4296, 2026-11-13T09:56:36.719697600Z
    - src/moneylab/knowledge/__pycache__/validate.cpython-314.pyc, 32944, 2026-11-13T09:56:36.729868400Z
    - src/moneylab/knowledge/__pycache__/__main__.cpython-314.pyc, 10408, 2026-11-13T09:56:36.754963100Z
  - 소스로 확인한 사실(Ce1 기준. base·작업 파일·SOURCE_WORKTREE HEAD와 같은 Git 객체): 자식 argv는 sys.executable, -m, moneylab.knowledge, --root, <root>, validate이고 -B가 없다. 자식 환경은 PATH와 SYSTEMROOT만 담고 PYTHONDONTWRITEBYTECODE를 전달하지 않는다. src에 바이트코드 기록을 끄는 코드가 없다. 상위 Python의 -B는 자식에게 전달되지 않는다.
  - 원인 추론: 관측된 캐시는 E3의 run_action이 실행한 자식 프로세스가 생성했을 가능성이 높다. 근거는 위 소스 사실과 캐시 구성이다. 캐시에는 자식이 import하는 moneylab과 moneylab.knowledge 계열만 있고, -B로 실행한 상위 프로세스만 import하는 모듈은 없다.
  - 증거 한계: 특정 프로세스의 생성 행위를 직접 확인하지 못했다. E3 실행 시각과의 직접 대조 자료가 없다. 생성 구간은 E2 직후 확인부터 E6 이전까지로만 확정된다. 수정 시각은 생성 시각이 아니다. 파일 내용은 읽지 않았다.
  - 설계 누락: 계약 후보 작성자는 자식 argv와 환경 구성을 알고 있었으나 산출물 범위 문장에 반영하지 않았다(DEVIATIONS #9). 승인된 명령의 실행 자체에는 일탈이 없었다.
  - 운영 부담: 원인 조사 1회(EXECUTION_CLOSEOUT), 추가 ERRATA 1건, 추가 커밋 1개, 관련 승인 단계.
  - 기준 ignored 목록: .venv/, data/processed/runlog/, data/processed/workstate/, src/moneylab.egg-info/, src/moneylab/__pycache__/, src/moneylab/knowledge/__pycache__/
  - 향후 task 참고(이 task의 허용이 아님): 자식 실행의 바이트코드 기록은 별도 Work Order에서 계약 범위 명시 또는 코드 변경으로 다룬다.

- DESIGN_CONTRACT.D15 확인 방법 (신설):
  - 단계별 기대 변경 집합. 아래 집합 밖의 tracked·untracked 변경이 없어야 한다. 모든 단계에서 변경이 0이어야 한다는 뜻은 아니다.
    - ERRATA_002_CREATION_ONLY: 작성 후 stage 전에는 untracked ERRATA-002.md 하나, stage 후에는 staged ERRATA-002.md 하나, Ce2 커밋 후에는 0
    - CASE_RECORD_WRITE부터 COMMIT 전까지(PRECOMMIT_AUDIT 포함): untracked 사례 기록 파일 하나
    - COMMIT: stage 후에는 staged 사례 기록 파일 하나, I 커밋 후에는 0
    - CLEAN_COMMIT_E2E 이후: 0
  - 계약 파일 불변: WORK_ORDER.md, ERRATA-001.md, ERRATA-002.md(Ce2 이후)의 작업 파일과 HEAD blob 해시가 승인값과 같아야 한다.
  - 캐시 메타데이터 대조:
    - Ce2 이후 최초로 승인된 읽기 전용 감사에서 D14의 파일 8개의 상대 경로, 바이트, 수정 시각을 D14 값과 대조한다. 두 캐시 디렉터리 안에 다른 파일이 없는지도 확인한다.
    - 이후 감사에서는 같은 파일 목록과 메타데이터의 변화를 확인한다.
    - 확인은 디렉터리 목록과 파일 메타데이터 조회로만 하며, 캐시 내용은 읽거나 실행하지 않는다.
  - 확인 범위와 한계:
    - 확인되는 것: 파일 목록, 바이트, 수정 시각의 일치. snapshot·runlog 기록은 git status의 디렉터리 존재로만 확인된다.
    - 확인되지 않는 것: 내용 해시 일치, 메타데이터가 같은 내용 변경, 관측 사이의 중간 변경, snapshot·runlog 기록 내부의 파일 수와 내용.
    - 완료 조건은 위 확인 범위에서 변화가 관측되지 않는 것이다. 검증할 수 없는 완전 불변은 요구하지 않는다.
  - 문서 바이트 검사 방법:
    - 시스템 Python(BASE_PYTHON)을 -I -B로 실행하고 moneylab을 import하지 않는다. 검사 코드는 파일 읽기와 메모리 계산만 한다.
    - 파일 작성, 설치, 캐시 정리는 검사에 포함하지 않는다.
  - 새 캐시나 기준 목록 외 ignored 항목이 관측되면 원인을 단정하지 않고 중단한다.

- TEST_GATES (추가 항목, 기존 항목 유지):
  - D15의 단계별 기대 변경 집합 대조, 계약 파일 불변 확인, 캐시 메타데이터 대조

- ACCEPTANCE_CRITERIA:
  - AC1 (교체): C1·Ce1·Ce2·I의 parent와 변경 집합이 COMMIT_PLAN과 같다.
  - AC2 (교체): base..I는 4개 파일뿐이고, 보호 diff 0, 세 계약 파일의 해시 불변.
  - AC11 (신설): D9의 이번 사건 한정 완료 조건을 모두 충족하고, 사례 기록과 최종 보고에 이번 사례의 통합 시험 최종 판정 FAIL, 산출물 범위 불일치, DEVIATIONS #9가 기록됨.
  - 완료 판정 (교체): AC1–AC11 충족과 D9의 부재 조건(이번 사건 한정 처리 포함)을 함께 요구한다. 중단 경로의 문서화 전이는 별도 승인으로만 한다.

- REQUIRED_EVIDENCE (추가 항목):
  - GIT_VERIFIABLE: Ce2 SHA·tree·parent, ERRATA-002 작업 파일·staged·commit blob 내용 해시
  - CLAUDE_REPORTED: D15 단계별 변경 집합 대조, ignored 목록 비교, 캐시 메타데이터 대조 결과와 미확인 범위

- STOP_CONDITIONS (추가 항목):
  - ERRATA-002의 작업 파일·staged·commit blob 해시가 승인값과 다름, 또는 Ce2 이후 ERRATA-002 변경
  - Ce2의 변경이 ERRATA-002.md 하나가 아님, 또는 Ce2의 parent가 Ce1이 아님
  - I의 parent가 Ce2가 아님
  - D15의 단계별 기대 변경 집합 밖의 tracked·untracked 변경
  - D14 기준 목록 외 새 ignored 항목, 또는 캐시 메타데이터 대조에서 변화가 관측됨
  - 사례 기록이나 보고에서 이번 사례의 통합 시험 최종 판정이 FAIL 외 값으로 표기됨(다른 결과 축과 과거 E6 시점의 판정 보류 이력에는 적용하지 않음)

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1–3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)과 README는 바꾸지 않는다.
- ALLOWED_FILES는 ERRATA-001의 사례 기록 파일 1개 그대로이며, ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
- 코드·테스트·README·Guard·CI 변경을 추가하지 않는다.
- 새 실행 권한, 원본 재조회 권한, 캐시 생성 허용, 정리 권한을 추가하지 않는다.
