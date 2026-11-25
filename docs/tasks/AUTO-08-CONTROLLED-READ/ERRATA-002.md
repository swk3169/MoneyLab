# ERRATA-002: AUTO-08-CONTROLLED-READ

STATUS: ACCEPTED
TASK_ID: AUTO-08-CONTROLLED-READ
APPLIES_TO: docs/tasks/AUTO-08-CONTROLLED-READ/WORK_ORDER.md (C1 14eb236b53a65cc7922441133bfbd27f1223cca9, C1 시점 SHA-256 ffe9b566300fb3d34add648a04ec3dd36d72aff5335256abaad6bba02b3af6eb), docs/tasks/AUTO-08-CONTROLLED-READ/ERRATA-001.md (Ce fb079ea08f0d4a6cd90d4bdbb3902025ff3eff1d, SHA-256 1c4009cc4a31bb303d4e738b1aed92900c766845c0fe1d4ac85ce937ef9a7473)
PRECEDENCE: ERRATA-001 다음에 적용한다. 충돌하면 이 ERRATA가 앞선다.
DECISION_REF: 이 대화에서 저장소 관리자인 사용자가 보낸 제한된 계약 정정 승인 메시지. 그 메시지는 WORK_ORDER.md의 ENVIRONMENT_SETUP에 있는 Python 실행 파일 사용자 홈 절대 경로 두 곳을 <PYTHON314_EXE>로 바꾸는 것만, 그 두 곳에 한정된 Work Order 불변 규칙의 예외로 허용했다. 다른 계약, ERRATA, guard, settings를 바꿀 권한은 주지 않았다. 이 기록은 승인의 존재를 적은 것이며, 프로그램이나 에이전트가 승인의 진위를 검증했다는 뜻이 아니다.
BACKGROUND: ERRATA-001에 따른 IMPLEMENTATION 재진입에서 R0 뒤 전체 pytest 1회차가 실패했다(1 failed, 3536 passed, 49 skipped, 1 deselected, 3 xfailed; CLAUDE_REPORTED). 실패한 시험은 tests/test_repo_hygiene.py::test_no_secrets_or_personal_data_in_addable_files다. 이 시험은 WORK_ORDER.md를 "user home path"로, tests/test_controlled_read_cli.py를 "assigned secret"으로 걸러냈다. 이 실패, 그로 인한 IMPLEMENTATION STOP, 이전 STOP·DENY·mypy 기록은 보존한다. 기존 실패를 PASS로 바꾸지 않는다.

## F1 합성 표식

- tests/test_controlled_read_cli.py의 BODY_TOKEN과 OTHER_TOKEN 값은 유출 검사용 합성 표식이며 실제 비밀값이 아니다.
- 구현 수정은 두 이름을 BODY_SENTINEL과 OTHER_SENTINEL로 바꾸는 것으로 한정한다. 값, 두 값이 서로 구별된다는 성질, 본문과 다른 항목이 stdout·stderr·intent.json·result.json에 나타나지 않는다는 단정, 기존 시험 함수 이름과 ID는 바꾸지 않는다.
- 문자열을 쪼개거나 인코딩해 검사를 피하는 방식, tests/test_repo_hygiene.py의 패턴·제외 목록·대상 변경, skip·xfail 추가, 실패 무시, 전체 pytest의 선택 제외는 하지 않는다.

## F2 WORK_ORDER.md의 사용자 홈 경로 정정 (완료된 사실의 기록)

- 대상: ALLOWED_ACTIONS > WORKSPACE_SETUP > (3) ENVIRONMENT_SETUP의 첫 두 항목(77·78번째 줄). 두 줄의 첫 백틱 구간은 사용자 홈 아래 Python 3.14 설치 위치의 실행 파일 절대 경로(64바이트)로 시작했다.
- 정정: 두 곳의 그 경로 문자열을 <PYTHON314_EXE>(15바이트)로 바꾸었다. 그 밖의 바이트는 바꾸지 않았다.
  - 정정 후 77번째 줄: - TARGET_WORKTREE에서 `<PYTHON314_EXE> --version`. 3.14.x가 아니면 설치·경로 변경 없이 STOP.
  - 정정 후 78번째 줄: - `<PYTHON314_EXE> -m venv .venv`
  - 두 줄의 앞 들여쓰기(공백 4칸)는 바꾸지 않았다.
- <PYTHON314_EXE>는 ENVIRONMENT_SETUP 당시 사용자가 지정한 Python 3.14 실행 파일이다. 뜻은 정정 전과 같고, 환경에 중립적인 표기로 바꾼 것일 뿐이다. ENVIRONMENT_SETUP은 이미 끝났으므로 다시 실행하지 않는다. Python 설치 위치와 .venv도 바꾸지 않는다.
- 수행과 확인은 끝났다.
  1. 사용자가 Claude Code 밖의 편집기로 두 곳을 바꾸었다. 에이전트는 guard task-contract 규칙 때문에 이 파일을 쓰지 않았고, 그 규칙을 우회하지 않았다.
  2. 에이전트가 읽기 전용으로 Ce의 blob과 작업 파일을 대조했다(CLAUDE_REPORTED). 다른 줄은 77·78번째뿐이었다. 두 줄은 각각 원본 줄의 경로 문자열 1개를 <PYTHON314_EXE>로 바꾼 결과와 바이트 단위로 같았다. 경로 문자열은 2회에서 0회로, <PYTHON314_EXE>는 0회에서 2회로 바뀌었다. 줄 수는 460으로 같았다. UTF-8 strict를 통과했고 BOM·CR·탭·U+00A0·줄 끝 공백이 없었으며 끝 LF는 1개였다. 그 전의 두 차례 대조에서는 작업 파일이 원본과 같아 계산하지 않았고, 그 기록도 보존한다.
  3. 사용자가 다음 값을 수락했다.
- 정정된 WORK_ORDER.md의 수락값: SHA-256 887f04db75147cec7148620c665adf65c989578c55a7dde5a9d6875e8b67c8b6, 바이트 39586, LF 459. 원본보다 98바이트 적다(49바이트씩 두 곳).
- 보존: C1과 Ce의 Git 객체, 기존 승인값(ffe9b566…, 1c4009cc…), C1·Ce 보고, 중단과 실패 기록은 그대로 둔다. amend, 이력 재작성, force push는 하지 않는다.
- ERRATA-001은 정정된 WORK_ORDER.md에도 그대로 적용된다. F2가 바꾼 두 줄은 ERRATA-001이 대체하거나 참조하는 절과 겹치지 않는다. ERRATA-001 APPLIES_TO의 SHA-256은 C1 시점의 기록 값으로 남는다.
- Cd 이후 Work Order SHA-256 대조의 기준은 887f04db75147cec7148620c665adf65c989578c55a7dde5a9d6875e8b67c8b6이다. 이 예외는 위 두 곳에 한정되며 WORK_ORDER.md의 다른 바이트에는 다시 쓰지 않는다.

## F3 기록 디렉터리 준비 실패

- 이 규칙은 이 ERRATA에서 새로 정하는 것이다. 기존 계약은 이 경우의 분류를 명시하지 않았다.
- 기록 파일 생성 시도 전의 디렉터리 준비·검증 실패는 STORE_PATH_INVALID다. 다음이 해당한다.
  - check-ignore 실행 실패 또는 ignored 아님
  - 경로 구성요소의 링크·junction·reparse point·비디렉터리
  - 디렉터리 생성 중 FileExistsError가 아닌 OSError
  - 생성 직후 재검증 실패
- <NNN> 디렉터리가 이미 있으면 ATTEMPT_EXISTS를 유지한다. 처음 검사에서 발견했든 생성 중 FileExistsError로 알았든 같다.
- 두 경우 모두 intent.json을 만들지 않고 세션 파일을 열지 않는다. result.json에도 기록하지 않는다(ERRATA-001 E1.6의 저장 불가 코드).
- 생성되어 남은 디렉터리는 삭제·재사용하지 않고, 자동으로 재시도하지 않는다. status는 기록 파일을 기준으로 판정하므로 기록 파일이 없는 디렉터리는 NOT_FOUND다.
- atomic_create_new_bytes의 CreateNewError는 ERRATA-001 E3대로 STORE_FAILED와 record로 보고한다.
- TEST_GATES 추가: 합성 tmp_path 저장소에서 다음 각 경우를 만든다. 각 경우에 대해 stdout status가 STORE_PATH_INVALID 또는 ATTEMPT_EXISTS인지, exit_code 2인지, values·record가 null인지 확인한다. 또 intent.json 생성 시도(atomic_create_new_bytes 호출)와 세션 open이 0건인지, 남은 디렉터리가 삭제되지 않았는지 감시한다.
  - 중간 디렉터리 생성 OSError
  - 생성 직후 재검증 실패
  - 링크로 판정된 구성요소
  - ignored가 아닌 경로
  - 이미 있는 <NNN>
- 기존 시험은 삭제하거나 완화하지 않는다.

## F4 Cd (문서 커밋)와 감사 기준

- 순서
  1. 사용자의 두 곳 수정(완료)
  2. 에이전트의 원본 대비 변경 범위 대조와 새 발행값 계산(완료)
  3. 사용자 수락(완료)
  4. 이 ERRATA-002의 정본과 발행값 확정
  5. 문서 두 개만 담는 Cd 커밋
  6. 별도 Gate Authorization에 의한 구현 재진입
- 이 ERRATA의 정본 출처와 SHA-256·바이트·LF 수락값은 4에서 정하고 Cd 승인 메시지에 적는다. 자기 참조가 되므로 이 본문에는 넣지 않는다. 4의 수락 전에는 이 ERRATA를 작성하거나 커밋하지 않는다.
- Cd는 정정된 docs/tasks/AUTO-08-CONTROLLED-READ/WORK_ORDER.md(M)와 docs/tasks/AUTO-08-CONTROLLED-READ/ERRATA-002.md(A) 두 개만 담는다. 구현 변경 15개는 포함하지 않는다.
- 절차
  1. 15개 ALLOWED_FILES 작업 파일의 SHA-256·바이트 수와 git status --porcelain --untracked-files=all 출력을 기록한다.
  2. WORK_ORDER.md 작업 파일이 F2의 수락값과 같은지 확인한다.
  3. 에이전트가 Write로 ERRATA-002.md를 수락된 정본 그대로 최초 1회 작성하고 SHA-256·바이트·LF를 수락값과 대조한다.
  4. git add -- docs/tasks/AUTO-08-CONTROLLED-READ/WORK_ORDER.md docs/tasks/AUTO-08-CONTROLLED-READ/ERRATA-002.md 1회. staged 집합이 정확히 이 두 경로인지, 두 staged blob의 SHA-256이 각 수락값과 같은지, git diff --cached --check 결과를 확인한다.
  5. git commit -m "docs(task): accept AUTO-08-CONTROLLED-READ ERRATA-002" 1회(본문·trailer 없음, -a 없음). Cd의 parent, tree, 커밋 파일 집합(정확히 두 개), 두 commit blob의 SHA-256을 확인한다.
  6. 1의 15개 파일 SHA-256·바이트 수가 Cd 직후와 같은지, staged가 비어 있는지, 미커밋 변경이 기존 15개뿐인지 대조한다.
- 어느 대조든 다르면 STOP하고 파일·index·커밋을 보존한다. 삭제·덮어쓰기·자동 재시도·복구는 사전 승인되지 않는다.
- Cd의 parent는 Ce fb079ea08f0d4a6cd90d4bdbb3902025ff3eff1d다. Cd 시점의 활성 guard는 미커밋 수정본임을 보고한다.
- 구현 커밋의 parent는 Cd다. PRECOMMIT_AUDIT와 COMMIT의 diff 기준, "변경 파일 집합 = ALLOWED_FILES 15개" 판정은 Cd 대비로 한다.
- 시험 ID 기준선은 14eb236에서 IMPLEMENTATION 변경 전에 수집한 3267개(1 deselected)를 유지한다.
- ACCEPTED ERRATA는 ERRATA-001과 ERRATA-002다. 번호 순으로 적용하며 뒤 번호가 앞선다. COMMIT gate의 "커밋 1회"는 구현 커밋에만 해당하고, Cd는 C1·Ce와 같은 계약 커밋으로 별도로 센다. POST_MERGE_AUDIT의 구조 감사 범위는 ALLOWED_FILES ∪ docs/tasks/AUTO-08-CONTROLLED-READ/** 그대로다.

## F5 예산과 재검사

- 이미 사용한 예산은 초기화하지 않는다. 실패 대응 수정 반복은 5회 중 2회, 전체 pytest는 3회 중 1회(실패)를 사용했다.
- F1의 이름 변경과 F3의 합성 시험 추가는 하나의 실패 대응 수정 묶음으로 수행하고 1회로 센다. 그 뒤 누적 사용은 3회, 잔여는 2회다. 전체 pytest는 잔여 2회다.
- 그 수정 묶음 뒤의 검사 순서
  1. tests/test_controlled_read_cli.py와 tests/test_repo_hygiene.py::test_no_secrets_or_personal_data_in_addable_files를 좁게 실행한다.
  2. 1이 통과하면 CHECK_COMMANDS 순서대로 ruff 2종, mypy, targeted pytest, 전체 pytest, git diff --check를 실행한다.
- 정확한 명령은 재진입 Gate Authorization에서 정한다. 같은 실패 2회 연속, ALLOWED_FILES 밖 기존 시험의 회귀, guard DENY, 예상 밖 ASK, 도구 오류는 계약대로 STOP한다.
- 재진입은 새 Gate Authorization으로만 한다. 이 ERRATA 자체는 재진입 승인이 아니다.
