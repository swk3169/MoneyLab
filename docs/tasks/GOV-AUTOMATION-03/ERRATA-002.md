# ERRATA: GOV-AUTOMATION-03 ERRATA-002

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: GOV-AUTOMATION-03-ERRATA-002
TASK_ID: GOV-AUTOMATION-03
TARGET_WORK_ORDER: docs/tasks/GOV-AUTOMATION-03/WORK_ORDER.md @ b0b1855ce5c30a233d836b816cea5a4f62c38f87 (sha256 c0e6d7729430cedb6854e778a5bc65bd29911273114d77b5974049a45600ae72)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자 (최종 발행 승인 시 확정)

## CHANGED_FIELDS

CHANGED_FIELDS:
- COMMIT_PLAN (전체 대체. ERRATA-001이 대체한 COMMIT_PLAN을 다시 대체한다)
- ACCEPTANCE_CRITERIA의 AC1 (그 항목만 대체)
- PROTECTED_FILES (항목 추가)
- CONTRACT_FILE_EXCEPTION (항목 추가)
- GATE_TRANSITION_RULES (항목 추가)
- TEST_GATES "ERRATA-002 테스트 보존" 항목 (신설)
- TEST_GATES "ERRATA-002 측정과 판정" 항목 (신설)

## RATIONALE

RATIONALE:
- PR_CI에서 필수 Windows job이 job 실행 시간 제한 20분에 도달해 취소되었다. 테스트 단계가 완료되지 않았으므로 AC4의 필수 Windows CI SUCCESS를 충족하지 못했다.
- 같은 run의 Windows 로그 진행 표시 타임스탬프로 계산하면 taskctl 테스트 4개 파일은 약 505초를 사용했다. 이 값은 파일 경계 타임스탬프 기반의 근사값이다.
- 소스 정적 분석에 근거한 가설: 각 테스트가 같은 사전 상태(init부터 merge까지의 단계)를 실제 CLI와 Git으로 매번 처음부터 만들면서 반복하는 Git 프로세스 생성이 주된 비용이다. 이 원인은 측정으로 확정하지 않았다.
- 결정: 실제 CLI와 Git으로 만든 사전 상태를 재사용하되, 각 테스트는 독립된 임시 저장소 사본에서 수행한다. 운영 코드와 CI workflow는 변경하지 않는다.
- WORK_ORDER의 "COMMIT 후 수정은 새 커밋으로 한다. amend는 금지한다."에 따라 기존 I 위에 새 커밋을 추가한다. 현재 COMMIT_PLAN과 AC1은 C1·Ce1·I만 정의하므로 이를 정정한다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- COMMIT_PLAN:
  - C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/GOV-AUTOMATION-03/WORK_ORDER.md (b0b1855ce5c30a233d836b816cea5a4f62c38f87)
  - Ce1: parent = C1, 변경 = A docs/tasks/GOV-AUTOMATION-03/ERRATA-001.md (9104587a8c7fbf3a8106e0580403544a36fcb566)
  - I: parent = Ce1, 변경 = ALLOWED_FILES 전체 (1255161cd1812a77fb6aa1714d92be08b8cb15d7)
  - Ce2: parent = I, 변경 = A docs/tasks/GOV-AUTOMATION-03/ERRATA-002.md 하나. 작성 시점의 미커밋 변경은 없어야 한다.
  - I2: parent = Ce2, 변경 = 다음 4개 파일 중 필요한 파일만: tests/test_taskctl_cli.py, tests/test_taskctl_lease.py, tests/test_taskctl_ledger.py, tests/test_taskctl_check.py. 그 밖의 ALLOWED_FILES(운영 코드, docs/tasks/README.md, docs/tasks/TEMPLATE.md, pyproject.toml)와 CI workflow는 변경하지 않는다.
  - 기존 C1·Ce1·I와 계약 파일은 변경하지 않는다. amend, rebase, force push는 하지 않는다.
  - base..I2 = WORK_ORDER.md, ERRATA-001.md, ERRATA-002.md, ALLOWED_FILES 12개, 총 15개 경로뿐이다. 승인되지 않은 trailer는 넣지 않는다.
- ACCEPTANCE_CRITERIA의 AC1: C1·Ce1·I·Ce2·I2 각각의 parent와 변경 집합이 위 COMMIT_PLAN과 같다.
- PROTECTED_FILES 추가: docs/tasks/GOV-AUTOMATION-03/ERRATA-002.md
- CONTRACT_FILE_EXCEPTION 추가: docs/tasks/GOV-AUTOMATION-03/ERRATA-002.md는 ERRATA_002_CREATION_ONLY에서 승인 바이트로 최초 1회만 생성한다. 이 예외는 ALLOWED_FILES에 속하지 않는다.
- GATE_TRANSITION_RULES 추가:
  - IMPLEMENTATION 하위 단계 ERRATA_002_CREATION_ONLY를 둔다. 이 단계에서 docs/tasks/GOV-AUTOMATION-03/ERRATA-002.md를 승인 바이트로 최초 1회 생성하고, 그 경로 하나만 stage해 Ce2 커밋을 만든다.
  - Ce2 이후 승인문은 `GATE_AUTHORIZATION: GOV-AUTOMATION-03 <GATE> WO@b0b1855ce5c30a233d836b816cea5a4f62c38f87`와 `ERRATA: ERRATA-001@9104587a8c7fbf3a8106e0580403544a36fcb566 ERRATA-002@<Ce2 SHA>`를 함께 적는다.
  - Ce2 이후 IMPLEMENTATION, PRECOMMIT_AUDIT, COMMIT(I2), CLEAN_COMMIT_E2E, PUSH, PR_CI는 각각 다시 승인한다.
  - PUSH는 TARGET_BRANCH에 I2까지의 커밋을 일반 push 1회로 게시한다. force push는 하지 않는다.
  - PR_CI는 기존 PR #54를 사용한다. 새 PR을 만들지 않는다. push로 자동 시작된 CI만 조회하며, CI 수동 실행과 재실행은 별도 명시적 승인 없이 하지 않는다.
  - PR #54의 제목·본문 갱신은 별도 명시적 승인 없이 하지 않는다.
  - 이 ERRATA는 push, CI 재실행, PR 수정, merge 권한을 만들지 않는다.
- TEST_GATES "ERRATA-002 테스트 보존":
  - I2 전후 taskctl 테스트 4개 파일의 수집 테스트 ID 집합은 같은 127개다. ID의 추가·삭제·이름 변경을 하지 않는다.
  - 기존 단언을 삭제하거나 완화하지 않는다. skip·xfail을 추가하지 않는다.
  - 각 테스트가 검증하는 단계와 전이, 정상·거부 사례, ERRATA-001의 T1–T21과 P1–P8의 입력과 기대 결과를 유지한다.
  - 검증 대상 단계와 명령은 실제 taskctl CLI 진입점과 실제 Git으로 수행한다. Git 동작을 mock으로 대체하지 않는다.
  - 재사용하는 사전 상태(템플릿)는 실제 taskctl CLI와 실제 Git으로 만든다. 템플릿은 tmp_path_factory 아래에 두고, 테스트는 템플릿을 직접 변경하지 않는다.
  - 각 테스트는 자신의 tmp_path에 템플릿을 복사한 독립 사본에서 수행한다. 사본마다 별도 디렉터리, 별도 .git, 별도 원장을 가진다.
  - 복사는 링크를 따라가지 않으며, 링크·재분석 지점이 있는 템플릿은 복사하지 않고 실패로 처리한다. 사본은 임시 저장소 밖을 참조하지 않고, 사본에 대한 쓰기는 원본 템플릿에 전달되지 않는다.
  - 복사 직후 사본에서 다음을 확인한다: HEAD·tree가 템플릿과 같음, status 출력이 템플릿과 같음, verify-ledger가 OK이고 이벤트 바이트가 템플릿과 같음, .git과 원장에 템플릿 경로(절대 경로)가 남지 않음.
  - 테스트 종료 후 템플릿의 HEAD·status·이벤트 바이트가 생성 직후와 같은지 확인한다.
  - 사전 상태의 생성 과정 자체를 검증하는 테스트(init, SETUP_ENV, LOCAL_COMMIT, PUBLISH, 전이 조건 등)는 템플릿을 쓰지 않거나 검증 대상 단계 이전까지만 템플릿을 사용하고, 검증 대상 단계는 생략하지 않는다.
  - 시간 고정은 테스트 범위 안의 _now seam에 한정한다. 운영 코드의 만료·예산 검사는 변경하거나 약화하지 않는다.
  - 모든 파일·커밋·ref·링크 생성은 tmp_path 또는 tmp_path_factory의 임시 저장소에서만 한다.
- TEST_GATES "ERRATA-002 측정과 판정":
  - I2의 대상 테스트는 --durations를 사용해 실행하고, 파일별 시간과 가장 느린 테스트 목록을 기록한다.
  - 기존 CI의 taskctl 약 505초는 파일 경계 타임스탬프 기반 근사값이다. 로컬 시간과 CI 시간은 같은 조건의 비교로 주장하지 않는다.
  - Windows CI의 taskctl 100–150초 수준과 job 15분 이하는 추정·목표이며 합격 조건이나 합격 보장으로 쓰지 않는다.
  - 합격 조건은 변경하지 않는다: 필수 Windows CI job이 전체 테스트를 완료하고 SUCCESS여야 한다(AC4). 실패·취소·시간 초과는 불합격이다.
  - PR_CI에서 Windows CI의 taskctl 파일별 시간(진행 표시 타임스탬프 기준), test 단계 시간, job 총시간을 기록한다.
  - Linux experimental 결과와 플랫폼별 skip(P1–P8 포함)은 필수 판정과 분리해 기록한다. 실행하지 못한 테스트를 통과로 표시하지 않는다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1–3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다. ALLOWED_FILES와 그 변경 한정은 바꾸지 않는다. I2는 tests/test_taskctl_cli.py, tests/test_taskctl_lease.py, tests/test_taskctl_ledger.py, tests/test_taskctl_check.py 중 필요한 파일만 수정한다.
- Work Order와 ERRATA-001 파일은 변경하지 않는다.
- SUPERSEDES_ERRATA: NONE은 ERRATA-001 전체를 폐기하지 않는다는 뜻이다. ERRATA-001은 계속 유효하다.
- 조항별 우선순위: 이 ERRATA의 CHANGED_FIELDS에 적은 항목은 이 ERRATA를 따른다. 그 밖의 항목은 ERRATA-001이 대체하거나 추가한 항목이면 ERRATA-001을, 나머지는 Work Order를 따른다.
- D1–D8, ACCEPTANCE_CRITERIA의 AC2–AC5, BUNDLE_MAX_RANGE, 예산, LEASE 정리 권한은 바꾸지 않는다.
- 운영 코드, CI workflow(.github/**), CI job 시간 제한은 변경하지 않는다.
- DEVIATION #1·#2·#3과 그에 따른 CLOSED_WITH_VIOLATION 판정은 이 ERRATA로 소급해 없애지 않는다.
