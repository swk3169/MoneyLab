# ERRATA: AUTO-06 ERRATA-002

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: AUTO-06-ERRATA-002
TASK_ID: AUTO-06
TARGET_WORK_ORDER: docs/tasks/AUTO-06/WORK_ORDER.md @ 0927350e51e0a1693de0987335df18fda97e0023 (sha256 e2df8b638d71d042e665977273f3a13b05322abc170fa7c51e4d0bb414dee2fc)
PRIOR_ERRATA: docs/tasks/AUTO-06/ERRATA-001.md @ 75f1e1f620832baf7458ee66c57528eddad081bf (sha256 bd6d4eaa59c076d5810b1adf07421f7c52a6475ccafb287343d04b6d74f07fdf)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자 (ERRATA_002_CREATION_ONLY 승인문)

## CHANGED_FIELDS

CHANGED_FIELDS:
- GATE_TRANSITION_RULES (Work Order 필드 전체 대체)
- ALLOWED_ACTIONS.ERRATA_002_CREATION_ONLY (신설)
- ALLOWED_ACTIONS.COMMIT (ERRATA-001의 대체 내용을 다시 전체 대체)
- PROTECTED_FILES (ERRATA-001의 대체 내용을 다시 전체 대체)
- COMMIT_PLAN (ERRATA-001의 대체 내용을 다시 전체 대체)
- DESIGN_CONTRACT.D2 (전체 대체)
- DESIGN_CONTRACT.D3의 "환경 준비 뒤 P 실행 전까지 허용되는 것" 항목 (그 항목만 대체)
- DESIGN_CONTRACT.D4의 "상수" 항목과 "출력과 출력 실패" 항목 (두 항목만 대체)
- DESIGN_CONTRACT.D5의 "S0 진입 확인" 항목 (그 항목만 대체)
- DESIGN_CONTRACT.D7의 "계약 두 파일" 항목 (그 항목만 대체. 항목 이름은 "계약 파일"로 바뀐다)
- DESIGN_CONTRACT.D17의 "기준과 계약" 항목 (ERRATA-001이 신설한 D17 가운데 그 항목만 대체)
- TEST_GATES (ERRATA-001의 대체 내용을 다시 전체 대체)
- ACCEPTANCE_CRITERIA (ERRATA-001의 대체 내용을 다시 전체 대체)
- STOP_CONDITIONS (ERRATA-001의 대체 내용을 다시 전체 대체)

적용 규칙:
- ACCEPTED ERRATA는 번호 순으로 적용하고, 뒤 번호가 앞선다.
- 위에 적지 않은 필드는 Work Order와 ERRATA-001이 정한 내용을 그대로 유지한다.
- 항목만 대체한다고 적은 필드는, 그 항목만 아래 내용으로 바꾸고 같은 필드의 나머지 항목은 유지한다.
- ERRATA-001에서 그대로 유지하는 필드는 다음과 같다.
  - ALLOWED_FILES (사례 기록 경로 docs/research-intake/2026-11-14/AUTO-06_OFFLINE_INTEGRATION_CASE.md)
  - ALLOWED_ACTIONS.CASE_RECORD_WRITE (사례 기록의 작성 시점, 최초 1회 생성 권한, 작성 후 대조)
  - DESIGN_CONTRACT.D17 가운데 "기준과 계약" 밖의 모든 항목
- Work Order, ERRATA-001 파일은 변경하지 않는다. 이 ERRATA는 ERRATA-001 전체를 폐기하지 않는다.

## RATIONALE

RATIONALE:
- Work Order D4는 P가 보고를 표준 출력에 쓰고 쓰기 반환값을 요청 길이와 비교하라고 정했다. 같은 D4와 D7은 보호 경로인 계약 파일 경로를 P 원문에 명시하라고 정했다.
- 활성 Guard는 보호 경로 문자열과 수정 패턴이 한 명령에 함께 있으면 그 명령을 차단한다. 쓰기 반환값을 얻는 write 호출은 수정 패턴에 해당한다. 그래서 계약 문언 그대로의 P는 실행 단계에서 차단된다. 이것은 PROGRAM_REVIEW의 정적 검토에서 확인했다.
- 경로를 숨기거나 쪼개거나 인코딩하는 방법, 다른 이름의 쓰기 API로 판정을 피하는 방법은 쓰지 않는다. 대신 출력 방식을 print 1회와 예외 기반 출력 실패로 바꾼다. 잘린 출력은 D9의 출력 수락 조건이 미수락으로 판정한다.
- 이 ERRATA를 Ce2로 고정하면 docs/tasks/AUTO-06/ 아래 계약 파일이 3개가 된다. workstate가 수집하는 계약 집합도 3개가 된다. 그래서 다음을 함께 바꾼다.
  - 실행 진입 HEAD, S0와 D7의 계약 대조
  - P 상수
  - 커밋 구조와 파일 범위
  - 검사, 완료 조건, 중단 조건
  - 사례 기록의 계약 정보
- 사례 기록 경로와 그 최초 생성 권한은 바꾸지 않는다. 새 실행, 재실행, 재저장, 재조회, 정리 권한은 추가하지 않는다.
- 이 ERRATA는 Guard 통과를 보장하지 않는다. 바뀐 출력 방식으로도 차단되면 중단한다.
- Ce2의 SHA와 tree, 이 ERRATA 파일의 sha256은 이 본문에 넣지 않는다. 이 값들은 생성 후 P 상수와 이후 승인문에서 고정한다. 이 본문에서는 이 값들을 "Ce2", "Ce2 tree", "ERRATA-002의 승인 해시"로 가리킨다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:

- GATE_TRANSITION_RULES:
  - C1 이전의 CONTRACT_REVIEW PASS는 후보 문안에 대한 검토 판정이며 계약 발행이 아니다. Work Order와 각 ERRATA는 해당 커밋(C1, Ce1, Ce2)에 포함된 바이트로만 효력이 있다.
  - 각 gate와 하위 단계는 사용자의 명시적 승인 범위에서만 수행한다. 하나의 승인으로 둘 이상의 하위 단계를 진행하지 않는다.
  - 승인문의 식별값:
    - C1 이전 승인은 TASK_ID, SUBPHASE, EXPECTED_HEAD, EXPECTED_TREE, 후보 해시로 식별한다.
    - C1 이후에는 GATE_AUTHORIZATION: AUTO-06 <GATE> WO@<C1 SHA>를 쓴다.
    - Ce1 이후에는 ERRATA: ERRATA-001@<Ce1 SHA>를 함께 적는다.
    - Ce2 이후에는 ERRATA: ERRATA-001@<Ce1 SHA>, ERRATA-002@<Ce2 SHA>를 함께 적는다.
  - ACCEPTED ERRATA는 번호 순으로 적용하고, 뒤 번호가 앞선다.
  - WORKSPACE_SETUP 하위 단계는 MAIN_REF_FETCH_ONLY, WORKTREE_CREATION_ONLY, C1_CREATION_ONLY, ERRATA_CREATION_ONLY, ENVIRONMENT_PREPARATION_ONLY 순서다.
  - IMPLEMENTATION 하위 단계는 다음 순서다: ERRATA_002_CREATION_ONLY, PROGRAM_REVIEW, EXECUTION_ONLY, EXECUTION_CLOSEOUT(D11의 경우에만), CASE_RECORD_DRAFT, CASE_RECORD_WRITE.
  - PROGRAM_REVIEW는 Ce2 이후에 처음부터 다시 진행한다. Ce2 이전에 채팅으로 제시한 P 조각은 검토 이력으로만 남기며, P 후보로 쓰지 않는다.
  - EXECUTION_CLOSEOUT과 중단 후 문서화 전이는 별도 승인으로만 한다. 전이 승인문에는 EXECUTION_OUTCOME: <P 종료 코드, 출력 수락 여부, 첫 실패 단계>를 적는다.
  - BUNDLE_ELIGIBLE: NO. PUSH, PR_CI, MERGE, POST_MERGE_AUDIT, COMPLETE, 후퇴는 각각 개별 승인이다.
  - Guard DENY, 권한 거절이나 무응답, 실패, 결과 불명이 생기면 그 단계에서 멈춘다. 재시도, 변형, 우회는 하지 않는다. 같은 작업을 다시 하려면 새 승인이 필요하다.
  - 종료된 승인은 자동으로 복원하지 않는다. COMMIT 후 수정은 새 커밋으로 한다. amend는 금지한다.

- ALLOWED_ACTIONS.ERRATA_002_CREATION_ONLY (신설):
  - 위치: IMPLEMENTATION의 첫 하위 단계다. 사용자의 별도 명시적 승인이 있을 때만 수행한다.
  - 사전 확인: 다음을 모두 확인한다. 보호 경로 확인은 다른 확인이나 수정 작업과 별도 호출로 한다.
    - branch가 TARGET_BRANCH다.
    - HEAD가 Ce1 75f1e1f620832baf7458ee66c57528eddad081bf이고, tree가 df25d1b8bf39fe27e09a02752932c151d18d9c8e다.
    - tracked·index·untracked 변경이 0이다.
    - ignored 항목이 .venv/와 src/moneylab.egg-info/뿐이다.
    - docs/tasks/AUTO-06/ERRATA-002.md가 없다.
    - Work Order와 ERRATA-001의 작업 파일과 HEAD blob 내용 SHA-256이 승인값과 같다.
  - 작성:
    - 수락된 승인 바이트를 메모리에서 구성하고, 그 SHA-256, 바이트 수, 줄 수를 승인값과 대조한다.
    - 대조가 맞으면 docs/tasks/AUTO-06/ERRATA-002.md를 TARGET_WORKTREE에서 Write 도구로 최초 1회 생성한다.
    - 분할 작성, Edit 추가, 셸이나 Python으로 직접 기록하는 것은 하지 않는다.
  - 작성 후 대조:
    - 작성한 파일의 SHA-256, 바이트 수, 줄 수, 바이트 형식을 승인값과 대조한다.
    - 다르면 stage와 commit을 하지 않고, 파일을 수정·덮어쓰기·삭제하지 않은 채 상태를 보고하고 중단한다.
  - stage와 커밋:
    - 대조가 맞을 때만 git -C <TARGET_WORKTREE> add -- docs/tasks/AUTO-06/ERRATA-002.md로 그 경로 하나만 stage한다.
    - staged 집합이 그 파일의 A 하나뿐인지 확인한다. staged blob 내용 SHA-256이 승인값과 같은지 확인한다. git diff --cached --check가 통과하는지 확인한다.
    - 확인이 모두 통과하면 Ce2 커밋 1개를 만든다. 메시지는 docs(task): add AUTO-06 ERRATA-002다. 승인문에 없는 trailer는 넣지 않는다.
  - 사후 확인:
    - Ce2의 parent가 Ce1 하나다.
    - Ce2의 변경이 docs/tasks/AUTO-06/ERRATA-002.md의 A 하나다.
    - commit blob 내용 SHA-256이 승인값과 같다.
    - Work Order와 ERRATA-001의 작업 파일과 blob 해시가 바뀌지 않았다.
    - tracked·index·untracked 변경이 0이다. ignored 항목은 .venv/와 src/moneylab.egg-info/뿐이다.
  - 이 단계는 다음을 포함하지 않는다: P 작성·실행, snapshot, verify, run_action, store_evidence, load_evidence, 사례 기록 작성, push, 정리.

- ALLOWED_ACTIONS.COMMIT:
  - docs/research-intake/2026-11-14/AUTO-06_OFFLINE_INTEGRATION_CASE.md 경로만 지정해 stage하고, 구현 커밋 I 1개를 만든다.
  - I의 parent는 Ce2다.
  - 메시지는 docs(research-intake): add AUTO-06 offline integration case다. 승인문에 없는 trailer는 넣지 않는다.
  - staged와 commit blob의 내용 해시를 승인값과 대조한다.

- PROTECTED_FILES:
  - ALLOWED_FILES 밖의 모든 저장소 파일은 보호 대상이다. docs/tasks/AUTO-06/**와 .claude/**를 포함한다.
  - 보호 대상의 예외는 계약 파일 세 개의 최초 생성뿐이다.
    - docs/tasks/AUTO-06/WORK_ORDER.md는 C1_CREATION_ONLY에서 1회 생성한다.
    - docs/tasks/AUTO-06/ERRATA-001.md는 ERRATA_CREATION_ONLY에서 1회 생성한다.
    - docs/tasks/AUTO-06/ERRATA-002.md는 ERRATA_002_CREATION_ONLY에서 1회 생성한다.
    - 세 파일은 생성 후 변경하지 않는다. 이 예외는 ALLOWED_FILES에 속하지 않는다.
  - 사례 기록 파일은 ALLOWED_FILES에 속하며 보호 대상이 아니다. 경로와 권한은 ERRATA-001 그대로다. 허용되는 것은 CASE_RECORD_WRITE의 최초 생성과 COMMIT의 stage뿐이다.
  - INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

- COMMIT_PLAN:
  - C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/AUTO-06/WORK_ORDER.md 하나 (0927350e51e0a1693de0987335df18fda97e0023)
  - Ce1: parent = C1, 변경 = A docs/tasks/AUTO-06/ERRATA-001.md 하나 (75f1e1f620832baf7458ee66c57528eddad081bf)
  - Ce2: parent = Ce1, 변경 = A docs/tasks/AUTO-06/ERRATA-002.md 하나
  - I: parent = Ce2, 변경 = A docs/research-intake/2026-11-14/AUTO-06_OFFLINE_INTEGRATION_CASE.md 하나
  - base..I: 위 4개 파일뿐
  - 실행 진입 HEAD는 Ce2다. P는 Ce2 위에서만 실행하며, Ce2와 I 사이에는 다른 커밋을 두지 않는다.

- DESIGN_CONTRACT.D2 작업공간:
  - 실행과 문서 작성은 TARGET_WORKTREE에서만 한다.
  - 실행 진입 HEAD는 Ce2이고, 실행 진입 tree는 Ce2의 tree다.
  - 저장에 쓰는 task ID는 AUTO-06이다.

- DESIGN_CONTRACT.D3의 "환경 준비 뒤 P 실행 전까지 허용되는 것" 항목:
  - 환경 준비 뒤 P 실행 전까지 TARGET_WORKTREE에 대해 허용되는 것은 다음뿐이다.
    - 읽기 전용 Git 조회
    - BASE_PYTHON을 -I -B로 실행하는 원문 검사. 대상은 채팅으로 받은 P 후보 또는 실행할 원문의 바이트다. sha256, 바이트 수, 줄 수, 문자 형식, 구문 해석을 메모리에서만 계산한다. 파일을 쓰지 않고, moneylab을 import하지 않으며, 원문을 실행하지 않는다.
    - 저장소 파일과 Git 객체의 읽기 전용 검토
    - ALLOWED_ACTIONS.ERRATA_002_CREATION_ONLY가 정한 범위의 docs/tasks/AUTO-06/ERRATA-002.md 최초 생성, 대조, 그 경로 하나의 stage, Ce2 커밋 1개
  - 그 밖의 파일, Git, 환경 변경은 허용하지 않는다. Ce2 작성은 ignored 산출물을 만들거나 바꾸지 않아야 하며, ignored 항목은 .venv/와 src/moneylab.egg-info/로 유지된다.

- DESIGN_CONTRACT.D4의 "상수" 항목:
  - 상수:
    - P의 상수는 다음과 같다.
      - CANONICAL_BASE_SHA, C1 SHA, Ce1 SHA, Ce2 SHA와 Ce2 tree, TARGET_BRANCH
      - 계약 세 파일의 상대 경로: docs/tasks/AUTO-06/WORK_ORDER.md, docs/tasks/AUTO-06/ERRATA-001.md, docs/tasks/AUTO-06/ERRATA-002.md
      - 각 계약 파일의 W·S 내용 sha256
      - D6·D8의 상한
    - Ce2 SHA, Ce2 tree, 세 계약 파일의 W·S는 Ce2 생성 후 실측한 값을 P에 넣는다. 이 값들은 PROGRAM_REVIEW와 EXECUTION_ONLY 승인문에서 고정한다.
    - 상수는 Ce2 이후 PROGRAM_REVIEW에서 수락된 원문에 있는 값이다. 실행 중 외부 입력을 받지 않는다.
    - 비교에 쓰는 경로는 승인된 명시적 입력값으로 취급한다. 보호 경로를 숨기거나 조각내거나 인코딩하지 않는다. 허용된 전달 방식이 Guard나 권한 창에서 차단되면 중단한다.
    - 절대 경로는 P가 실행 시점의 cwd와 sys.prefix에서 얻으며, 출력하지 않는다.

- DESIGN_CONTRACT.D4의 "출력과 출력 실패" 항목:
  - 출력과 출력 실패:
    - P는 보고 전문을 메모리에서 구성한 뒤, 끝에서 print(text, end="", flush=True)를 1회 호출해 표준 출력에 쓴다. 이 밖의 출력 호출은 하지 않는다.
    - 쓰기 반환값의 비교는 하지 않는다.
    - print 또는 flush가 예외를 내면 출력 실패다. 다시 출력하지 않고, 자동 진단이나 재실행도 하지 않는다. P는 가능하면 종료 코드 2로 끝낸다. 그 실행의 결과는 D10에 따라 출력 미수락이다.
    - 잘리거나 일부만 관측된 출력은 D9의 출력 수락 조건에 따라 미수락으로 판정한다. 출력 수락 여부는 P의 자기 판단이 아니라 관측 출력과 도구가 보고한 종료 코드로 정한다.
    - 인터프리터 종료 단계의 오류는 완전히 통제하지 못한다. 버퍼 처리, 종료 처리기, 런타임 경고 등에서 생기는 추가 오류나 출력이 여기에 해당한다. 그런 출력이 관측 출력에 섞이면 D9에 따라 미수락이다.
    - KeyboardInterrupt와 프로세스 소실도 같은 방식으로 처리한다.
    - 이 출력 방식이 Guard 판정을 통과한다고 보장하지 않는다. 차단되면 중단하고, 다른 API, 별칭, 인코딩으로 다시 시도하지 않는다.

- DESIGN_CONTRACT.D5의 "S0 진입 확인" 항목:
  - S0 진입 확인: 다음을 모두 만족하면 PASS다.
    - 직접 Git(D6)으로 HEAD = Ce2 SHA, HEAD tree = Ce2 tree, 현재 branch = TARGET_BRANCH를 확인한다.
    - git status --porcelain=v1 -z --untracked-files=all 출력이 0바이트다.
    - 계약 세 파일 각각의 작업 파일 바이트 sha256이 그 파일의 승인 W와 같다.
    - 계약 세 파일 각각에 대해 git cat-file blob <Ce2 SHA>:<경로> 바이트의 sha256이 그 파일의 승인 S와 같다.
    - data/processed가 링크가 아닌 일반 디렉터리다.
    - data/processed/workstate/AUTO-06과 data/processed/runlog/AUTO-06이 없다.
    - sys.flags.dont_write_bytecode가 참이다.
    - sys.prefix와 moneylab 위치가 D3과 같다.
    - 확인된 불일치는 FAIL이며 FIRST_FAIL_CODE는 PRECONDITION이다. 직접 Git의 실패, 회수 실패, 예외는 UNKNOWN이며, 코드는 D6과 W0의 회수·출력 실패 코드를 따른다.

- DESIGN_CONTRACT.D7의 "계약 파일" 항목 ("계약 두 파일" 항목을 대체):
  - 계약 파일:
    - state.contract는 정확히 3항목의 배열이다. 각 항목은 키가 정확히 path, head_sha256, work_sha256인 객체이며, 값은 모두 문자열이다.
    - path 집합은 승인된 세 상대 경로와 정확히 같아야 한다: docs/tasks/AUTO-06/WORK_ORDER.md, docs/tasks/AUTO-06/ERRATA-001.md, docs/tasks/AUTO-06/ERRATA-002.md. 끝 파일명만 같은 것은 일치로 보지 않는다.
    - 각 항목의 head_sha256은 그 파일의 승인 S와 같아야 한다. work_sha256은 그 파일의 승인 W와 같아야 한다. 두 값은 각각 대조하며, W와 S가 같다고 가정하지 않는다.
    - CONTRACT_ENTRIES의 기대값은 3이다. 항목 수, 경로 집합, 해시 가운데 하나라도 다르면 D5의 E1C 매핑에 따라 FAIL이고, FIRST_FAIL_CODE는 CONTRACT_MISMATCH다.
    - D7의 나머지 항목은 그대로 유지한다: 경로, 원바이트, 엄격한 JSON, state 해시, 판정과 출력, 근거 구분.

- DESIGN_CONTRACT.D17의 "기준과 계약" 항목:
  - 기준과 계약:
    - CANONICAL_BASE_SHA와 tree
    - C1, Ce1, Ce2의 SHA와 tree. 각 parent 관계도 적는다(C1 ← base, Ce1 ← C1, Ce2 ← Ce1, I ← Ce2).
    - Work Order, ERRATA-001, ERRATA-002의 sha256
    - Ce2 SHA와 tree, ERRATA-002의 sha256은 Ce2 생성 뒤 확인한 값을 증거 등급과 함께 적는다.

- TEST_GATES:
  - 코드 변경이 없으므로 로컬 pytest, ruff, mypy는 NOT_REQUIRED다.
  - 로컬 검증은 D15의 문서 검사로 제한한다.
  - 바이트 형식: 계약 파일 세 개와 사례 기록 파일은 UTF-8, BOM 없음, CR 0, U+00A0 0, 탭 0, 줄 끝 공백 0, 끝 LF 1개여야 한다. 계약 파일 세 개는 WORK_ORDER.md, ERRATA-001.md, ERRATA-002.md다.
  - 해시 대조:
    - 계약 파일 세 개는 작업 파일, staged, commit blob의 내용 SHA-256이 각각의 승인값과 같아야 한다.
    - 사례 기록 파일은 작성 직후의 SHA-256, 바이트 수, 줄 수가 승인값과 같아야 한다. 이후 작업 파일, staged, commit blob의 내용 SHA-256도 승인값과 같아야 한다.
  - 사례 기록 내용:
    - D17의 포함 항목이 있는지 확인한다. ERRATA-002가 대체한 "기준과 계약" 항목, 그리고 P가 실행된 경우의 REQUIRED_MISSING도 포함한다.
    - D13의 비식별화를 확인한다.
    - 기록한 값을 P 출력과 Git 값에 대조한다.
  - 변경 집합과 보호 diff를 확인하고, git diff --check를 실행한다.

- ACCEPTANCE_CRITERIA:
  - AC1: C1, Ce1, Ce2, I의 parent와 변경 집합이 COMMIT_PLAN과 같다. Ce1의 parent는 C1, Ce2의 parent는 Ce1, I의 parent는 Ce2다.
  - AC2: base..I는 다음 4개 파일뿐이다. 보호 diff는 0이고, 세 계약 파일의 해시는 변하지 않았다.
    - docs/tasks/AUTO-06/WORK_ORDER.md
    - docs/tasks/AUTO-06/ERRATA-001.md
    - docs/tasks/AUTO-06/ERRATA-002.md
    - docs/research-intake/2026-11-14/AUTO-06_OFFLINE_INTEGRATION_CASE.md
  - AC3: 다음 중 하나가 기록되었다.
    - D3의 환경 확인값, pip check 통과, 환경 준비 직후의 ignored 목록
    - 환경 준비가 중단된 경우: 그 관측값, 실패 지점, 이후 단계의 NOT_RUN 사유
  - AC4: 다음 중 하나가 기록되었다.
    - P가 실행된 경우: P 출력의 수락 여부와 그 근거. 출력이 수락되었으면 STAGE_S0 값(PASS, FAIL, UNKNOWN)과 실행 진입 HEAD·tree(Ce2와 그 tree)의 확인 결과를 기록한다. 미수락이면 S0 결과는 미확인으로 기록한다.
    - P가 실행되지 않은 경우: NOT_RUN과 그 사유
  - AC5: 다음 중 하나가 기록되었다.
    - 출력이 수락된 경우: 실행·작업·저장·조회·상태·산출물 축과 통합 사례 최종 판정을 D10에 따라 각각 기록한다. 확인된 위반과 UNKNOWN이 함께 있으면 둘 다 기록한다.
    - 출력이 수락되지 않은 경우: 최종 판정 UNKNOWN, 그리고 축 값이 미확인인 사유
    - 출력 수락 여부와 P 종료 코드는 ERRATA-002가 대체한 D4의 출력 조항과 D9의 수락 조건·종료 코드 규칙에 따라 판정한다.
  - AC6: 다음 중 하나가 기록되었다.
    - B0와 B1의 영역별 수와 집계 해시, 실제 차이 건수, DIFF_UNEXPECTED, REQUIRED_MISSING
    - NOT_RUN 또는 UNKNOWN과 그 사유
  - AC7: PRECOMMIT_AUDIT 시점에 미커밋 tracked·untracked 변경이 사례 기록 파일 하나뿐이다.
  - AC8: 사례 기록이 D17(ERRATA-002가 대체한 "기준과 계약" 항목 포함)과 D13을 만족한다.
  - AC9: 사례 기록의 W와 승인 S, staged blob, commit blob의 내용 SHA-256이 일치한다. commit 후 작업 트리가 clean이다.
  - AC10: 정확한 PR head의 Windows CI가 SUCCESS이고 D16이 기록되었다. PR_CI 이전 단계에서는 NOT_YET_APPLICABLE이다.
  - 완료 판정:
    - 문서화 task의 COMPLETE는 다음을 모두 요구한다.
      - AC1–AC10 충족
      - 계약 위반, 보호 파일 변경, 설명되지 않은 상태 변경이 없음. D12의 사건 한정 처리를 포함한다.
    - 통합 사례 SUCCESS는 완료 조건이 아니다. 완료는 통합 사례 최종 판정을 바꾸지 않는다.
    - 사례가 FAIL이나 UNKNOWN이면, D11과 D12의 별도 승인과 조건에 따라서만 문서화한다.
    - 아직 실행하지 않은 gate의 조건은 충족으로 표시하지 않는다. NOT_YET_APPLICABLE 또는 NOT_RUN으로 표시한다.

- STOP_CONDITIONS:
  - 기준선 불일치
    - 기준선, HEAD, tree, 계약 해시, 파일 범위가 기대와 다르거나, 예상 밖 untracked가 있다.
    - 생성 전에 대상 branch나 worktree가 이미 있거나, 생성 후 상태가 기대와 다르다.
    - fetch 후 원격 추적 main이나 그 tree가 기대값과 다르거나, SOURCE_WORKTREE HEAD tree가 CANONICAL_BASE_TREE와 다르다.
    - PATH_VARIABLES 값이 승인문에 없거나 기대 상태와 다르다.
  - 환경
    - 환경 확인 항목을 충족하지 못했거나 pip check가 실패했다.
    - ENVIRONMENT_PREPARATION_ONLY 완료 시점의 확인에서 .venv 밖에 __pycache__가 있거나, D3 밖의 ignored 항목이 있다. 실행 뒤의 산출물은 이 조건이 아니라 D8로 판정한다.
  - P 실행
    - 실행 진입 HEAD가 Ce2가 아니거나, 실행 진입 tree가 Ce2의 tree가 아니다.
    - 실행할 P 원문의 sha256이 Ce2 이후 PROGRAM_REVIEW에서 수락된 값과 다르다.
    - P 종료 코드가 0이 아니거나, D4와 D9에 따라 P 출력이 미수락이다.
  - ERRATA-001과 Ce1 커밋
    - ERRATA-001의 작업 파일, staged, commit blob 해시가 승인값과 다르다.
    - Ce1의 변경이 ERRATA-001.md 하나가 아니거나, Ce1의 parent가 C1이 아니다.
  - ERRATA-002와 Ce2 커밋
    - ERRATA-002의 작성 후 SHA-256, 바이트 수, 줄 수가 승인값과 다르다. 또는 작업 파일, staged, commit blob 해시가 승인값과 다르다.
    - Ce2의 변경이 ERRATA-002.md 하나가 아니거나, Ce2의 parent가 Ce1이 아니다.
    - 세 계약 파일 가운데 하나라도 생성 후 변경되었다.
  - 사례 기록과 I 커밋
    - 사례 기록을 CASE_RECORD_WRITE 승인 없이 작성했거나, ALLOWED_ACTIONS.CASE_RECORD_WRITE의 작성 시점 조건이 충족되기 전에 작성했다.
    - 사례 기록의 작성 후 SHA-256, 바이트 수, 줄 수가 승인값과 다르다.
    - 작성 후 승인 없이 사례 기록이 변경되었다.
    - I의 parent가 Ce2가 아니거나, I의 변경이 사례 기록 파일 하나가 아니다.
    - 사례 기록이나 보고에서 통합 사례 최종 판정이 P 출력과 D10이 정하는 값과 다르게 표기되었다.
  - 공통
    - 보호 파일이 변경되었거나, 기존 코드·테스트·설정이 변경되었다.
    - Guard DENY, 권한 거절이나 무응답, 예상 밖 ASK, 오류나 결과 불명이 발생했다.
    - 계약에 모순이 있거나 상위 규칙과 충돌한다.
  - 위 조건에 따른 중단은 보고 후 멈춤을 뜻한다. D11과 D12의 별도 승인에 따른 EXECUTION_CLOSEOUT과 문서화 전이를 막지 않는다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1–3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)과 README는 바꾸지 않는다.
- Guard, hook, settings는 변경하거나 우회하지 않는다. 보호 경로를 숨기거나 조각내거나 인코딩하지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
- Work Order와 ERRATA-001 파일은 변경하지 않는다. 이 ERRATA는 CHANGED_FIELDS에 적은 필드와 항목만 대체한다.
- 코드, 테스트, README, Guard, settings, CI, .gitignore 변경을 추가하지 않는다.
- D4의 출력 방식 변경 외에 P의 동작, 단계, 호출 횟수, 상한, 판정 규칙을 확장하지 않는다.
- 다음 권한은 추가하지 않는다.
  - P와 작업 API(run_action, store_evidence, load_evidence)의 새 실행 권한이나 재실행 권한
  - workstate snapshot·verify의 추가 실행 권한
  - evidence·snapshot·runlog 원본의 재조회 권한
  - 산출물과 캐시의 정리 권한
- ERRATA-002.md의 최초 생성과 사례 기록 파일의 최초 생성 외에는 파일 작성 권한을 추가하지 않는다.
