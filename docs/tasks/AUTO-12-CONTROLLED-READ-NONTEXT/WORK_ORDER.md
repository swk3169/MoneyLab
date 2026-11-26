# Work Order: AUTO-12-CONTROLLED-READ-NONTEXT — controlled_read profile ECON-FWD-M20-WO/2(마커 없는 비텍스트 tool_result 항목 건너뛰기)

이 파일은 발행 정본이다. 발행은 실행 승인이 아니며 각 gate에는 별도 승인이 필요하다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: AUTO-12-CONTROLLED-READ-NONTEXT
TASK_ID: AUTO-12-CONTROLLED-READ-NONTEXT
TITLE: 새 profile ECON-FWD-M20-WO/2에서 마커 없는 비텍스트 tool_result 항목 건너뛰기(S4e·S4f)
VERSION: 1.0
STATUS: ISSUED
REPOSITORY: swk3169/MoneyLab
CANONICAL_BASE_SHA: 6bd11b0cfbaadef4a12289d56beed243890d70e8
CANONICAL_BASE_TREE: 191535287b124be9c9c3fc8882f50f028c5057df
TARGET_BRANCH: codex/auto-12-controlled-read-nontext
TARGET_WORKTREE: C:/MoneyLab-auto-12
SETUP_SESSION_ROOT: C:/MoneyLab-auto-10
SETUP_EXECUTION_HEAD: b876d7d2d8af953ff805f61070768087b28489c4
SESSION_ROOT: C:/MoneyLab-auto-12
PYTHON_VERSION: 3.14.8
TOOL_VERSIONS: mypy 2.4.0 (compiled: no), ruff 0.17.2, pytest 9.1.1
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: pytest
BUNDLE_ELIGIBLE: NO

- CANONICAL_BASE_SHA는 WS-A1에서 원격 main과 대조한다. 다르면 STOP하며 임의로 갱신하지 않는다.
- SETUP_SESSION_ROOT는 WORKSPACE_SETUP PART=WORKTREE에만 쓴다. SETUP_EXECUTION_HEAD는 그 worktree의 기대 HEAD이며, 이 문서의 I(새 구현 커밋)와 다른 값이다.
- SESSION_ROOT는 PART=C1_ENV부터 COMPLETE까지 쓴다.
- PRESERVED_WORKTREES:
  - C:/MoneyLab-auto-10 @ b876d7d2d8af953ff805f61070768087b28489c4
  - C:/MoneyLab-auto-09 @ 326fc4985f1118b1a0a1c81d197babff5d2dce72
  - C:/MoneyLab-auto-08-first-use @ 2b826d4ed9e278b28456eff9f8c70fa1070895ac
- APPROVAL_DIR: 사용자가 승인문에 슬래시 절대 경로로 준다. 이 문서는 그 경로를 적지 않는다. WO_SOURCE = APPROVAL_DIR/WORK_ORDER.review.md
- NONREQUIRED_CI_BASELINE: pytest-linux-experimental, run 45841073441의 실패 2건(재조회 없이 재사용)
  - tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through
  - tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0
- 표기: I = 이 task의 구현 커밋, M = 이 task의 merge 커밋, C1 = 이 Work Order 커밋. <base>는 CANONICAL_BASE_SHA 40자 값 그대로 쓴다.

## GATE_SEQUENCE

WORKSPACE_SETUP PART=WORKTREE -> WORKSPACE_SETUP PART=C1_ENV -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

- 한 번에 한 단계만 전진한다. 각 단계에는 그 단계를 실행하는 세션의 Gate Authorization 원문이 필요하다. 자동 전진과 단계 묶음은 없다.
- PART=C1_ENV부터 COMPLETE까지는 SESSION_ROOT의 같은 세션에서 한다. 세션이 바뀌면 ACCEPTED ERRATA가 필요하다.
- 후퇴는 IMPLEMENTATION으로만, 명시적 승인으로 한다. COMMIT 이후 수정은 새 커밋이며 amend는 없다.

## AUTHORIZATION_FORMS

- PART=WORKTREE: `GATE_AUTHORIZATION: AUTO-12-CONTROLLED-READ-NONTEXT WORKSPACE_SETUP PART=WORKTREE WO_SHA256=<64hex> APPROVAL_DIR=<슬래시 절대 경로>`
- PART=C1_ENV: `GATE_AUTHORIZATION: AUTO-12-CONTROLLED-READ-NONTEXT WORKSPACE_SETUP PART=C1_ENV WO_SHA256=<64hex> WO_SOURCE=<슬래시 절대 경로>`
- 그 밖의 gate: `GATE_AUTHORIZATION: AUTO-12-CONTROLLED-READ-NONTEXT <GATE> WO@<C1 SHA>`
  - PR_CI에는 다음 필드를 더한다: `PR_CREATE: YES`, `REPOSITORY: swk3169/MoneyLab`, `BASE: main`, `HEAD_BRANCH: codex/auto-12-controlled-read-nontext`, `HEAD_SHA: <I>`, PR 제목·본문(PR_CI 승인 때 확정)
  - MERGE에는 `MERGE_EXECUTE: YES`, `PR: <N>`, `HEAD_SHA: <I>`를 더한다.
- 대조: 원문이 있고, 필드와 실행 인자가 문자열로 완전히 같아야 한다. 어긋나면 STOP한다.

## AUTHORIZATION_MODEL

- 이 Work Order는 각 gate의 최대 범위만 정한다. 실행 승인이 아니다.
- 변경·실행에는 다음 세 가지가 모두 있어야 하며, 어느 하나가 다른 것을 대신하지 않는다.
  - (1) 이 Work Order가 정한 gate의 범위
  - (2) 그 gate에 대한 사용자의 Gate Authorization 원문
  - (3) 도구 권한 창과 guard 판정
- gate 안의 자율 진행: 승인된 gate 안에서는 그 gate가 허용하는 읽기, 수정, 합성 fixture 작성, 오프라인 검사, 실패 분석과 수정을 사용자 확인 없이 진행한다. 다음 gate 승인이 필요한 시점, STOP 조건, 실제로 필요한 사용자 결정이 있을 때만 보고하고 멈춘다.
- 승인 창 기록: 관측하지 못한 창은 ASK_UNVERIFIED로 기록하고 사용자에게 다시 떠올려 달라고 하지 않는다. 이는 실제 권한 승인을 생략하는 조항이 아니다. DENY, 권한 거절, 승인 대기, 무응답은 STOP이다.
- 일반 문서의 Edit 횟수 제한과 성공 출력의 "마지막 줄" 조건은 두지 않는다. 판정은 최종 diff, hook 오류 여부, EXIT_CRITERIA로 한다.
- hook 운영 위험: settings는 hook 명령을 `${CLAUDE_PROJECT_DIR}` 아래 작업 사본의 `.claude/hooks/guard.py`로 선언한다. 그래서 IMPLEMENTATION 중 guard.py 편집이 같은 세션의 판정에 영향을 줄 수 있다. 실제 hook 경로는 관측 전까지 미확인(H4)이다. 편집 뒤 예상 밖 DENY나 hook 오류가 나면 STOP한다.

## EXIT_CRITERIA

- 일반 규칙: 계약에 적힌 기대 출력이 있고 도구 오류 표시가 없으면 통과다. 표시된 0이 아닌 종료 코드는 아래 정상 예외를 빼고 실패다. 종료 코드가 표시되지 않으면 "미표시"로 기록하며, 미표시만으로 실패하지 않고 0이 입증됐다고 쓰지도 않는다.
- 도구별 판정:
  - pytest: 요약 줄에 `passed`가 있고 `failed`·`error`가 없다.
  - ruff: `All checks passed!`
  - mypy: `Success: no issues found`로 시작하는 줄
  - pip install: 표시된 0이 아닌 종료 코드와 `ERROR` 줄이 없고 `Successfully installed` 또는 `Requirement already satisfied` 안내가 있다. `[notice]` 줄은 판정에 쓰지 않는다. 표시된 오류나 비정상 종료를 성공 안내로 덮지 않는다.
- 정상 예외(실패 아님):
  - `git show-ref --verify --quiet <ref>`에 표시된 `Exit code 1`: 로컬 ref 부재라는 기대 결과. 0이나 미표시이면 STOP한다.
  - `git ls-remote …`의 빈 출력: 원격 ref 부재라는 기대 결과(N2, N6).
  - `git diff --no-index …`에 표시된 `Exit code 1`: 차이 있음 보고. 판정은 출력 내용으로 한다.
  - `git diff`(`--stat`·`--name-status`·`--name-only` 포함): 출력 내용으로 판정한다. `git diff --check`·`git diff --cached --check`는 빈 출력이어야 하며 출력이 있으면 위반이다.
  - git check-ignore -v는 출력이 한 줄이고, source가 .gitignore이며, pattern이 !로 시작하지 않고, 표시 경로가 요청 경로와 같고 도구 오류가 없으면 통과한다. 종료 코드 미표시만으로 실패하지 않는다. 표시된 종료 코드 1 이상은 STOP이다.
  - Grep 도구의 "No matches found" 또는 개수 0: 기대가 0인 검사에서는 통과.
  - `gh pr checks`: 표가 완전히 파싱되면 표시된 종료 코드(대기 중 8, 비필수 실패 1 등)는 기록만 하고 CI_STATES로 판정한다.
  - INLINE_CHECKS의 PS·FMT: 각 절의 RESULT·종료 코드 규칙으로 판정한다.
- JSON 내부 exit_code는 프로그램 보고값이며 OS 종료 코드와 같다고 쓰지 않는다.

## GOAL

moneylab.controlled_read에 profile `ECON-FWD-M20-WO/2`를 추가한다. /2는 tool_result content 배열의 비텍스트 항목을 정해진 조건에서만 텍스트 목록에서 뺀다. 그 밖의 profile 동작은 바꾸지 않는다. 실제 세션 진단·precheck·run은 이 계약 범위 밖이다.

## BACKGROUND

- AUTO-11-FIRST-USE-DIAGNOSE(외부 계약 sha256 73752dfe0a694f74d410b4c582024aa23423c6e45dc967541a381a197e13a1bb)는 고정 prefix(44113503바이트, 5433d3eb2ce924e22e2cbd6e71d6e4d77f35b2e1e102825b2d4b73cfef2351f2)에서 최초 위반 S4d를 찾았다: line 227, block_index 1, item_index 1, field_path tool_result.content[].type, expected text_literal, actual_json_type string_unlisted.
- 실제 type 이름과 본문은 미확인이다. 합성 설계에는 실제 type 이름이 필요하지 않다. 실제 세션 호환성은 미확인이며 이 task가 입증하지 않는다.
- AUTO-08-FIRST-USE의 STOP, PR #40·ECON-FWD-M20 발행 계산 미완료, 연구 공개 백업 보류를 유지한다.

## DESIGN_CONTRACT

### N1 보존

- `ECON-FWD-M20-WO/1`과 `ECON-FWD-M20-PREREG/1`의 판정, 오류 코드, 출력 바이트, 텍스트 목록, text_index를 바꾸지 않는다.
- result/1, status, precheck/1, diagnose/1 문서의 스키마와 키를 바꾸지 않는다. 건너뛴 항목 수는 출력하지 않는다.
- `src/moneylab/controlled_read/__init__.py`(DETAILS·ERROR_CODES·ControlledReadError), `store.py`, `selector.py`는 바꾸지 않는다. DETAILS는 변경하지 않는 상수다. selector.valid_profile과 store.profile_ref·_valid_profile은 PROFILES를 따라 /2를 받는다.
- assistant 경로(S1·S2·S3 계열)와 transcript._find는 바꾸지 않는다.

### N2 /2 정의 (`src/moneylab/controlled_read/profiles.py`)

- `Profile`에 기본값 있는 필드 `skip_marker_free_nontext: bool = False`를 추가한다. 기존 두 정의는 기본값을 쓴다.
- `WORK_ORDER_V2 = Profile(id="ECON-FWD-M20-WO/2", version=2, …)`: begin·end·kinds·trim_empty_edges는 /1과 같고 `skip_marker_free_nontext=True`. PROFILES에 추가한다.
- /2 정의의 주석·docstring에 다음을 적는다. "/1과 같다"고 쓰지 않는다.
  - (가) 후보는 지원되는 개별 text 문자열(assistant text block, tool_result 문자열 content, content 배열의 `type == "text"` 항목)에 기존 규칙(marker_line_present, 줄 단위 완전 일치)으로 BEGIN 또는 END 마커 줄이 있는 것뿐이다.
  - (나) 항목 결합, 첨부 해석, 추가 디코딩은 없다.
  - (다) /2의 유일성은 (가)의 범위 안에서만 의미가 있으며 비텍스트 내용 전체의 유일성을 뜻하지 않는다.
  - (라) 비텍스트 검사는 건너뛰기를 거부할 조건의 확인이며, 비텍스트의 지원이나 검증이 아니다.

### N3 항목 판정 순서 (`src/moneylab/controlled_read/transcript.py`, tool_result content 배열의 항목마다)

1. 항목이 dict(객체)가 아니면 S4d(기존): field_path tool_result.content[], expected object.
2. `type == "text"`이면 text가 문자열이 아니면 S4d(기존, tool_result.content[].text / string), 문자열이면 텍스트 목록에 넣는다. text 항목의 다른 키는 검사하지 않는다(기존).
3. type이 문자열이 아니면 S4d(기존, tool_result.content[].type / text_literal, actual_json_type은 기존 _json_type 결과).
4. type이 "text"가 아닌 문자열이면 비텍스트 항목이다.
   - 정책 없음(/1·PREREG/1): S4d(tool_result.content[].type / text_literal / string_unlisted, 기존).
   - /2: N4로 탐색한다. 완전한 마커 발견이면 S4e, 한도 초과면 S4f, Deadline 만료면 TIME_LIMIT_EXCEEDED, 그 밖에는 건너뛴다(텍스트 목록에 넣지 않음).
- 항목은 배열 순서로 보고, 최초 실패에서 멈춘다. type 이름은 비교·출력·추측하지 않는다.

### N4 비텍스트 탐색 (비재귀)

- 검사 대상: 비텍스트 루트 객체 아래의 모든 객체 키와 문자열 값. 어느 하나에 profile의 BEGIN 또는 END 마커 문자열 전체가 부분 문자열로 들어 있으면 S4e다. 숫자·bool·null은 노드로만 센다.
- 일반 JSON 이스케이프는 json.loads 파싱 뒤의 문자열로 검사한다. 추가 인코딩(base64, 퍼센트 인코딩, 이중 이스케이프 등), 외부 참조, 여러 문자열로 나뉜 마커, 비문자열 표현은 해석하지 않으며 감지하지 못하는 한계다.
- 노드 집계: 루트 객체 1, 객체의 각 키 1, 각 값 1, 배열의 각 원소 1. 같은 노드를 중복 집계하지 않는다.
- 깊이: 루트 객체가 깊이 1이다. 깊이 d인 컨테이너 안의 컨테이너 값·원소는 깊이 d+1이다. 키와 스칼라는 깊이를 늘리지 않는다. 깊이가 64를 넘는 컨테이너를 만나면 S4f다.
- 작업량 한도: 항목당 방문 노드 100000 이하, 정책 객체 하나(호출 1회)의 비텍스트 방문 노드 합 2000000 이하. 넘는 노드를 세는 순간 S4f다.
- Deadline: 호출자의 Deadline을 공유한다. 루트 방문 직전과 방문 노드 1024개를 넘기기 전마다(최대 1024 노드 간격) deadline.check()를 한다.
- 구현: 명시적 스택에 (컨테이너 반복자, 깊이)를 둔다. 자식을 하나 꺼낼 때마다 집계·한도·마커·Deadline을 검사한다. 자식 전체를 복제·미리 적재한 뒤 한도를 확인하는 방식과 Python 재귀 호출은 금지한다.
- 결정성: 키 삽입 순서와 배열 순서를 따르는 깊이 우선이다. 처음 만난 실패를 보고한다.
- 상태: 정책·카운터 객체는 scan_candidates 호출 1회, select_text 호출 1회마다 새로 만든다. 호출·실행 사이에 공유하지 않는다.

### N5 공통 텍스트 목록과 시그니처

- 키워드 전용 인자를 추가한다:
  - `_tool_result_content_texts(block, *, nontext=None)`
  - `_tool_result_texts(block, *, nontext=None)`
  - `select_text(prefix, selector, deadline, *, nontext=None)`
  - `scan_candidates(prefix, kinds, is_candidate, deadline, *, nontext=None)`
- `nontext=None`이면 /1 동작과 같다. 기존 직접 호출 시험은 바꾸지 않고 통과해야 한다.
- scan(precheck·diagnose)과 run이 같은 `_tool_result_content_texts`로 텍스트 목록을 만든다. `:text:<k>`는 그 block 텍스트 항목의 k번째다.
- 적용 범위 차이(기존과 같음): precheck와 diagnose는 profile kinds의 모든 tool_result block에, run은 선택된 block에만 적용한다.
- `src/moneylab/controlled_read/__main__.py`는 run, precheck(scan과 선택 확인 각각), diagnose 각 호출 직전에, profile.skip_marker_free_nontext가 True일 때만 새 정책 객체를 만들어 넘긴다.

### N6 진단 고정 값 (`src/moneylab/controlled_read/diagnose.py`)

- S4e: field_path tool_result.content[], expected marker_free_nontext, actual_json_type object, applicability SELECTED_ENTRY_ONLY, block_index 보고(1 이상), item_index 보고(1 이상).
- S4f: field_path tool_result.content[], expected within_nontext_scan_limits, actual_json_type object, applicability SELECTED_ENTRY_ONLY, block_index 보고(1 이상), item_index 보고(1 이상).
- 허용 목록 변경: FIELDS에 위 두 (check_id, field_path, expected) 쌍, APPLICABILITY에 S4e·S4f = SELECTED_ENTRY_ONLY, BLOCK_INDEX_CHECKS와 ITEM_INDEX_CHECKS에 S4e·S4f를 추가한다. 그 밖의 값과 검증 규칙은 바꾸지 않는다.
- run·precheck에서 S4e·S4f의 코드는 FORMAT_UNSUPPORTED(FormatViolation)다. 새 오류 코드는 없다.
- 문자열 값, 키 이름, type 이름, 본문은 어떤 경로로도 출력하지 않는다.

### N7 guard와 문서

- `.claude/hooks/guard.py`: run, precheck, diagnose 세 CLI 형태의 profile 대안 `(?:ECON-FWD-M20-WO/1|ECON-FWD-M20-PREREG/1)`에 `ECON-FWD-M20-WO/2`만 추가한다. 그 밖의 상수, 판정 순서, reason, 마지막 DENY는 바꾸지 않는다. Edit 횟수 제한은 두지 않고 최종 diff와 hook 오류 여부로 감사한다. 실제 권한 승인과 DENY는 그대로 적용한다.
- `docs/agent_workflow.md`의 제한 읽기 CLI 절: PROFILE 값 문법에 `ECON-FWD-M20-WO/2`를 추가하고, N2 (가)–(라), N4의 한계(추가 인코딩·외부 참조·분할 마커 미감지), "/2의 PRECHECK_OK는 /1과 의미가 다르다"는 문장을 넣는다. 다른 절은 바꾸지 않는다.

## ALLOWED_FILES (12개: M 10개, A 2개)

1. M `src/moneylab/controlled_read/profiles.py` (N2)
2. M `src/moneylab/controlled_read/transcript.py` (N3–N5)
3. M `src/moneylab/controlled_read/__main__.py` (N5 정책 전달만)
4. M `src/moneylab/controlled_read/diagnose.py` (N6)
5. M `.claude/hooks/guard.py` (N7)
6. M `docs/agent_workflow.md` (N7)
7. M `tests/test_controlled_read_profiles.py` (EX-1)
8. M `tests/test_controlled_read_selector.py` (EX-2)
9. M `tests/test_agent_guard.py` (EX-3)
10. M `tests/test_controlled_read_diagnose.py` (EX-4, EX-5)
11. A `tests/test_controlled_read_nontext.py`
12. A `tests/test_controlled_read_nontext_guard.py`

새 소스 모듈은 없다. 이 순서가 AUDIT_SET 순서다.

## PROTECTED_FILES와 기존 시험 예외

- CANONICAL_BASE_SHA에 있는 tests/** 전체는 PROTECTED다. 예외는 아래 다섯 곳의 정확한 변경뿐이다. 함수 삭제·이름 변경, 다른 줄 변경, skip·xfail 추가는 위반이다.
- EX-1 `tests/test_controlled_read_profiles.py::test_only_two_profiles_exist`: 함수 이름 유지. 본문의 두 assert를 다음 한 줄로 바꾼다.
  `assert {p.id: p.version for p in profiles.PROFILES.values()} == {"ECON-FWD-M20-WO/1": 1, "ECON-FWD-M20-PREREG/1": 1, "ECON-FWD-M20-WO/2": 2}`
- EX-2 `tests/test_controlled_read_selector.py::test_value_grammar_violations`: 파라미터 `(10, "ECON-FWD-M20-WO/2")`를 `(10, "ECON-FWD-M20-WO/3")`로 바꾼다.
- EX-3 `tests/test_agent_guard.py::test_cr_other_forms_deny`: 원소 `CR_RUN.replace("ECON-FWD-M20-WO/1", "ECON-FWD-M20-WO/2")`를 `CR_RUN.replace("ECON-FWD-M20-WO/1", "ECON-FWD-M20-WO/3")`로 바꾼다.
- EX-4 `tests/test_controlled_read_diagnose.py::test_t1_every_d5_pair_is_covered`:
  - 첫 assert의 왼쪽 집합에 리터럴 집합 `{("S4e", "tool_result.content[]", "marker_free_nontext"), ("S4f", "tool_result.content[]", "within_nontext_scan_limits")}`를 합집합 연산자로 더한다.
  - 둘째 assert의 왼쪽 dict 식에 `"S4e": E, "S4f": E` 두 항목을 더한다(dict 펼침 결합 형태).
- EX-5 `tests/test_controlled_read_diagnose.py::test_diagnose_codes_and_constants`: APPLICABILITY 리터럴 dict에 `"S4e": E, "S4f": E`를 더한다.
- 수집 ID: EX-2와 EX-3의 /2 -> /3 교체에서 생기는 old -> new 쌍만 허용한다(COLLECT_RULES). 기준 ID는 WS-B7에서 baseline으로 식별하며, 실제 ID가 같으면 그 사례의 교체 건수는 0이다.
- 그 밖의 PROTECTED: src/** 중 ALLOWED 4개를 뺀 전부, .claude/** 중 hooks/guard.py를 뺀 전부, .github/**, CLAUDE.md, pyproject.toml, requirements*.txt, .gitignore, 사전등록 파일, docs/tasks/**(예외: WS-B3의 이 WORK_ORDER.md 최초 생성 1회).
- 판정: `git diff --name-status <base>`에서 PROTECTED 경로의 M·D·R이 0이고, A는 ALLOWED의 A 2개와 이 WORK_ORDER.md뿐이다.

## TEST_GATES (합성 tmp_path만, 실제 home·세션 접근 없음, skip·xfail 없음)

tests/test_controlled_read_nontext.py
- T1 /1 보존: /1·PREREG/1에서 비텍스트가 섞인 block의 결과(S4d, FORMAT_UNSUPPORTED, 위치)와 run·precheck·diagnose 문서가 nontext=None 경로와 같다. 기존 직접 호출 형태가 그대로 동작한다.
- T2 순서: /2에서 [비텍스트, 텍스트A, 비텍스트, 텍스트B]의 scan 후보 text_index와 run :text:1·:text:2가 일치하고, 텍스트를 결합하지 않는다.
- T3 S4e: 완전한 마커가 중첩 문자열 값, 객체 키, 배열 원소, 깊이 64의 문자열에 있을 때 S4e와 line·block·item 위치. JSON 이스케이프로 쓴 마커는 파싱 후 감지. 마커 일부, 두 문자열로 나뉜 마커, base64 인코딩 마커는 감지하지 않고 통과(한계 고정).
- T4 S4f와 탐색 방식: 깊이 64 통과·65 S4f, 항목 노드 100000 통과·100001 S4f, 호출당 합 2000000 통과·2000001 S4f(한도는 monkeypatch seam으로 축소해 확인), 키·스칼라는 깊이를 늘리지 않음, 계측 컨테이너 seam으로 한도 초과 시점 이후의 자식을 꺼내지 않음(미리 복제·적재 없음), 깊이 64 입력에서 RecursionError 없음.
- T5 Deadline: 탐색 중 만료되면 TIME_LIMIT_EXCEEDED. precheck·diagnose는 INCOMPLETE·재해시 없음, run은 기존 처리.
- T6 상태 비공유: 연속 호출 사이 카운터 누적 없음, precheck의 scan과 선택 확인이 따로 집계됨.
- T7 S4d 유지: 비객체 항목, 비문자열 type, text 항목의 비문자열 text.
- T8 유일성 범위: 텍스트 후보 1개와 마커 있는 비텍스트 -> FORMAT_UNSUPPORTED. 텍스트 후보 2개 -> PRECHECK_MULTIPLE_CANDIDATES. 후보 1개와 마커 없는 비텍스트 -> PRECHECK_OK.
- T9 누출 방지: stdout·stderr에 LEAK 표식(type 이름, 키 이름, 값, 본문) 없음. 비ASCII 합성 입력은 명시적 이스케이프.
- T10 diagnose /2: S4e·S4f의 D5 객체가 N6 값과 같고, 다른 값은 ValueError.

tests/test_controlled_read_nontext_guard.py
- T11 guard 판정: run·precheck·diagnose의 /2 정확 형태는 ASK(reason 기존 문구 그대로). `ECON-FWD-M20-WO/3`, `econ-fwd-m20-wo/2`, `ECON-FWD-M20-WO/02`, 끝 공백 변형은 controlled-read-form DENY. /1·PREREG/1 판정·reason 불변.
- T12 hook 프로세스: /2 ASK는 JSON 출력, DENY는 exit 2.

재귀 부재·미리 복제하지 않음의 근거는 T4와 PRECOMMIT_AUDIT의 CODE_READ를 함께 쓴다. Grep 0건만으로 입증하지 않는다.

## FILE_FORMAT

- A 2개(파일 전체): UTF-8 strict, BOM 없음, CR 없음, 탭·U+00A0·U+FEFF 없음, 줄 끝 공백 없음, 파일 끝 LF 정확히 1개.
- M 10개: 추가·변경 줄은 UTF-8 strict, 탭·U+00A0·U+FEFF·CR 없음, 줄 끝 공백 없음. 파일 전체는 BOM 없음, CRLF를 LF로 바꾼 뒤 남는 CR 0, 끝 LF.
- 비ASCII 합성 입력은 명시적 이스케이프로 쓴다. 확인하지 못한 조건은 통과로 쓰지 않는다.

## INLINE_CHECKS (읽기 전용 확인문, 고정 원문, 파일로 저장하지 않음)

공통:
- Bash 독립 호출 1회로 실행한다. 셸 명령 전체의 형태는 각 절의 "셸 명령"이고, 그 안의 `<SOURCE>` 자리에 바로 아래 "Python 소스" 코드 블록의 내용을 글자 그대로(첫 줄부터 마지막 줄까지, 앞뒤 공백 줄 없이) 넣는다. 소스는 작은따옴표를 포함하지 않으며 역슬래시를 포함하지 않는다(바이트는 bytes([...])로만 만든다).
- `<PY>`: WS-A에서는 `C:/MoneyLab-auto-10/.venv/Scripts/python.exe`, WS-B부터는 `C:/MoneyLab-auto-12/.venv/Scripts/python.exe`.
- 인자는 각 절의 허용 인자만 받는다. 출력은 경로와 정해진 라벨뿐이며 파일 내용을 출력하지 않는다.
- 이 확인문은 읽기 전용이다. 디렉터리 생성은 MKD 절의 별도 `mkdir` 명령으로만 한다.

### PS (경로 상태)

셸 명령:

```
<PY> -I -B -c '<SOURCE>' <경로1> [<경로2> …]
```

Python 소스:

<!-- PS_SOURCE -->
```python
import os, stat, sys
for p in sys.argv[1:]:
    try:
        st = os.lstat(p)
    except FileNotFoundError:
        print(p, "PATH_STATE=ABSENT")
        continue
    except OSError as exc:
        print(p, "PATH_STATE=QUERY_ERROR", type(exc).__name__)
        raise SystemExit(2)
    attrs = getattr(st, "st_file_attributes", 0)
    if stat.S_ISLNK(st.st_mode):
        kind = "LINK"
    elif attrs & 1024:
        kind = "REPARSE"
    elif stat.S_ISDIR(st.st_mode):
        kind = "DIRECTORY"
    elif stat.S_ISREG(st.st_mode):
        kind = "FILE"
    else:
        kind = "OTHER"
    print(p, "PATH_STATE=" + kind)
```

- 동작: 각 인자에 os.lstat 1회. 링크 대상이나 하위 내용을 따라 읽지 않는다. 1024는 FILE_ATTRIBUTE_REPARSE_POINT(0x400)이며 junction을 포함한다. 분류 순서는 LINK -> REPARSE -> DIRECTORY -> FILE -> OTHER.
- 출력: 인자마다 `<경로> PATH_STATE=<ABSENT|DIRECTORY|FILE|LINK|REPARSE|OTHER>` 한 줄. lstat 오류는 `<경로> PATH_STATE=QUERY_ERROR <예외 이름>`을 출력하고 종료 코드 2로 즉시 끝난다(남은 인자는 처리하지 않는다).
- 종결: 모든 인자를 처리하면 종료 코드 0(미표시 가능).
- 허용 인자(이 목록만, 슬래시 절대 경로):
  - C:/MoneyLab-auto-12
  - C:/MoneyLab-auto-12/.venv (WS-A3 한정)
  - C:/MoneyLab-auto-12/docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT
  - C:/MoneyLab-auto-12/docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT/WORK_ORDER.md
  - C:/MoneyLab-auto-12/data, C:/MoneyLab-auto-12/data/processed, C:/MoneyLab-auto-12/data/processed/auto12, C:/MoneyLab-auto-12/data/processed/auto12/preserve
  - RECORDS 표의 각 기록 파일(C:/MoneyLab-auto-12/ 접두를 붙인 절대 경로)
- 판정: 기대 ABSENT인 경로는 ABSENT, 기대 DIRECTORY인 경로는 DIRECTORY여야 한다. LINK, REPARSE, OTHER, 기대와 다른 FILE·DIRECTORY, QUERY_ERROR, 종료 코드 2, 예외 출력은 STOP이다. 재시도하거나 다른 방법으로 확인하지 않는다. junction·reparse 경로는 재사용·정리하지 않고 보고한다.

### MKD (기록 디렉터리 생성, 읽기 전용 검사와 별도)

- 생성 허용 경로(이 넷만, 이 순서): C:/MoneyLab-auto-12/data -> C:/MoneyLab-auto-12/data/processed -> C:/MoneyLab-auto-12/data/processed/auto12 -> C:/MoneyLab-auto-12/data/processed/auto12/preserve
- 각 경로에 대해 부모부터 순서대로:
  - PS 결과가 DIRECTORY이면 생성하지 않고 그대로 쓴다.
  - ABSENT이면 독립 호출 `mkdir <경로>`(-p 없음) 1회, 이어서 PS로 DIRECTORY를 확인한다.
  - 그 밖은 STOP.
- 기록 파일은 RECORDS의 원문(noclobber)으로만 만들며, 쓰기 직전 PS로 ABSENT를 확인한다.

### FMT (형식, 모드 3개: new, changed, added)

셸 명령:

```
<PY> -I -B -c '<SOURCE>' <new|changed|added> <파일1> [<파일2> …]
```

Python 소스:

<!-- FMT_SOURCE -->
```python
import sys
LF, CR, TAB, SP = bytes([10]), bytes([13]), bytes([9]), bytes([32])
NBSP, FEFF = bytes([194, 160]), bytes([239, 187, 191])
NOEOL = bytes([92]) + b" No newline at end of file"
def bad_utf8(data):
    try:
        data.decode("utf-8", "strict")
        return 0
    except UnicodeDecodeError:
        return 1
def line_report(lines):
    return (sum(bad_utf8(x) for x in lines), sum(x.count(TAB) for x in lines), sum(x.count(NBSP) for x in lines),
            sum(x.count(FEFF) for x in lines), sum(x.count(CR) for x in lines),
            sum(1 for x in lines if x.endswith(SP) or x.endswith(TAB)))
def hunk_count(token):
    return int(token.split(b",")[1]) if b"," in token else 1
if len(sys.argv) < 3 or sys.argv[1] not in ("new", "changed", "added"):
    print("USAGE_ERROR")
    raise SystemExit(2)
mode, names = sys.argv[1], sys.argv[2:]
failed = 0
for name in names:
    with open(name, "rb") as handle:
        raw = handle.read()
    if mode == "new":
        body = raw[:-1] if raw.endswith(LF) else raw
        values = line_report(body.split(LF))
        final_ok = raw.endswith(LF) and not raw.endswith(LF + LF)
        ok = values == (0, 0, 0, 0, 0, 0) and final_ok
        print(name, "UTF8_BAD_LINES=%d TAB=%d NBSP=%d FEFF=%d CR=%d TRAILING=%d" % values,
              "FINAL_LF=" + ("YES" if final_ok else "NO"))
    elif mode == "changed":
        norm = raw.replace(CR + LF, LF)
        bom = raw.startswith(FEFF)
        lone_cr = norm.count(CR)
        final_ok = norm.endswith(LF)
        ok = not bom and lone_cr == 0 and final_ok
        print(name, "BOM=" + ("YES" if bom else "NO"), "LONE_CR=%d" % lone_cr,
              "FINAL_LF=" + ("YES" if final_ok else "NO"))
    else:
        lines = raw.split(LF)
        added = []
        hunks = 0
        noeol = 0
        malformed = 0
        i = 0
        while i < len(lines):
            line = lines[i]
            i += 1
            if not line.startswith(b"@@ -"):
                continue
            parts = line.split(SP)
            if len(parts) < 4 or not parts[1].startswith(b"-") or not parts[2].startswith(b"+") or parts[3] != b"@@":
                malformed += 1
                break
            hunks += 1
            old_left, new_left = hunk_count(parts[1]), hunk_count(parts[2])
            while old_left or new_left:
                if i >= len(lines):
                    malformed += 1
                    break
                body = lines[i]
                i += 1
                if body == NOEOL:
                    noeol += 1
                elif body.startswith(b"-") and old_left:
                    old_left -= 1
                elif body.startswith(b"+") and new_left:
                    new_left -= 1
                    added.append(body[1:])
                else:
                    malformed += 1
                    break
            while i < len(lines) and lines[i] == NOEOL:
                noeol += 1
                i += 1
        values = line_report(added)
        ok = values == (0, 0, 0, 0, 0, 0) and noeol == 0 and malformed == 0 and hunks > 0
        print(name, "HUNKS=%d ADDED_LINES=%d" % (hunks, len(added)),
              "UTF8_BAD_LINES=%d TAB=%d NBSP=%d FEFF=%d CR=%d TRAILING=%d" % values,
              "NO_EOL_MARKERS=%d MALFORMED=%d" % (noeol, malformed))
    failed += not ok
print("RESULT=" + ("PASS" if failed == 0 else "FAIL"))
raise SystemExit(3 if failed else 0)
```

- 변수: LF·CR·TAB·SP·NBSP(U+00A0의 UTF-8)·FEFF(U+FEFF의 UTF-8)·NOEOL(Git의 "No newline at end of file" 표시 줄, 첫 바이트 92)은 소스 첫머리에서 정의한다. bad_utf8·line_report·hunk_count는 소스 안에서 정의한다.
- new 모드: 파일 전체의 줄(마지막 LF 뒤의 빈 조각 제외)에 대해 UTF-8 strict 실패 줄 수, TAB·NBSP·FEFF·CR 개수, 줄 끝 공백·탭 줄 수를 세고, 파일 끝 LF가 정확히 1개인지 본다.
- changed 모드: 파일 전체의 BOM(첫 3바이트 FEFF), CRLF를 LF로 바꾼 뒤 남는 CR 수, 끝 LF를 본다. 추가 줄의 문자 검사는 added 모드가 맡는다. 파일 전체 문자 개수가 같다는 이유로 추가 줄을 적합하다고 판정하지 않는다.
- added 모드: Git diff(-U0) 기록을 hunk 단위로 해석한다. `@@ -a[,b] +c[,d] @@` 머리글의 b·d(쉼표가 없으면 1)만큼 `-` 줄과 `+` 줄을 hunk 안에서 소비하며, 소비한 `+` 줄에서 첫 바이트를 뗀 내용을 추가 줄로 검사한다. 따라서 내용이 `++`로 시작하는 실제 추가 줄도 검사한다. hunk 밖의 `diff --git`, `index`, `--- a/…`, `+++ b/…` 등 파일 머리글 줄은 hunk 머리글이 아니므로 건너뛴다. 머리글 형식이 다르거나, 기대한 개수만큼 줄이 없거나, hunk 안에서 예상 밖 줄이 나오면 MALFORMED로 센다. NOEOL 표시 줄은 센다.
- 출력: 파일마다 한 줄(경로와 라벨), 마지막 줄 `RESULT=PASS` 또는 `RESULT=FAIL`.
- 종결: PASS는 종료 코드 0(미표시 가능), FAIL은 종료 코드 3, 사용법 오류는 `USAGE_ERROR`와 종료 코드 2. 파일을 열 수 없는 등 예외가 나면 traceback과 종료 코드 1이 나온다.
- 허용 인자:
  - new: tests/test_controlled_read_nontext.py, tests/test_controlled_read_nontext_guard.py
  - changed: ALLOWED_FILES의 M 10개
  - added: data/processed/auto12/added.diff 1개
  - 경로는 SESSION_ROOT 기준 상대 경로로 준다.
  - 발행 단계의 별도 사용자 승인으로 FMT new를 외부 WO_SOURCE 한 파일에 적용할 수 있다. 이 예외는 계약 발행본의 형식 확인에만 적용하며, 다른 외부 파일이나 실행 gate로 확대하지 않는다.
- 판정: RESULT=PASS이고 표시된 종료 코드가 없거나 0이면 통과. RESULT=FAIL·종료 코드 3은 위반 -> STOP(자동 수정 없이 보고). 종료 코드 1·2, traceback, RESULT 누락, USAGE_ERROR는 STOP. added 모드에서 HUNKS=0이면 FAIL이다.
- 검증 한계: 이 소스는 발행 전 ast.parse로 구문만 확인한다. 구문 통과는 변수 정의나 판정의 정확성을 보장하지 않는다. 처음 실행할 때의 guard 판정(ASK·DENY·통과)은 미확인이다.

## AUDIT_METHOD

- W(원바이트): `sha256sum <path>`. 작업 파일 그대로의 바이트(CRLF 포함 가능).
- O(Git blob OID): `git -C C:/MoneyLab-auto-12 hash-object -- <path>`(-w 금지). Git 필터(줄바꿈 정규화)를 적용한 blob의 SHA-1. index는 `git -C C:/MoneyLab-auto-12 rev-parse :<path>`, 커밋은 `git -C C:/MoneyLab-auto-12 rev-parse HEAD:<path>`와 대조한다. W와 O는 서로 대조하지 않는다.
- AUDIT_SET: PRECOMMIT_AUDIT에서 확정한 12개의 (경로, W, O). COMMIT·CLEAN_COMMIT_E2E는 O로, 작업 파일 불변은 W로 대조한다.
- 모든 Bash 호출은 독립 명령 하나다. 체인·파이프·리디렉션은 금지이며 예외는 RECORDS 원문뿐이다.
- 큰 출력: 하네스가 그 호출 반환값에 적은 결과 파일 하나만 Read로 나눠 연다(100줄씩, 최대 30회). 다른 tool-results·세션·debug 파일은 열지 않는다.

## RECORDS (TARGET_WORKTREE 아래 ignored, create-new)

- ignore 확인: `git -C C:/MoneyLab-auto-12 check-ignore -v -- data/processed/auto12/x` -> 한 줄, source `.gitignore`, pattern이 `!`로 시작하지 않음. 아니면 STOP.
- 각 파일은 쓰기 직전 PS로 ABSENT를 확인한다. 아래 원문만 허용한다. R1–R5는 작업 위치 C:/MoneyLab-auto-12에서, P1·P2는 WS-A4에서 절대 경로로 실행한다.
  - R1: `set -C && .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q > data/processed/auto12/collect_base.txt`
  - R2: `set -C && .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q > data/processed/auto12/collect_precommit.txt`
  - R3: `set -C && git diff --no-index -U0 -- data/processed/auto12/collect_base.txt data/processed/auto12/collect_precommit.txt > data/processed/auto12/collect_diff.txt`
  - R4: `set -C && git diff --stat 6bd11b0cfbaadef4a12289d56beed243890d70e8 > data/processed/auto12/diff_stat.txt`
  - R5: `set -C && git diff -U0 --no-color --no-ext-diff --no-renames 6bd11b0cfbaadef4a12289d56beed243890d70e8 -- src/moneylab/controlled_read/profiles.py src/moneylab/controlled_read/transcript.py src/moneylab/controlled_read/__main__.py src/moneylab/controlled_read/diagnose.py .claude/hooks/guard.py docs/agent_workflow.md tests/test_controlled_read_profiles.py tests/test_controlled_read_selector.py tests/test_agent_guard.py tests/test_controlled_read_diagnose.py > data/processed/auto12/added.diff`
  - P1: `set -C && git -C C:/MoneyLab-auto-12 worktree list --porcelain > C:/MoneyLab-auto-12/data/processed/auto12/preserve/worktrees_s1.txt`
  - P2: `set -C && git -C C:/MoneyLab-auto-12 for-each-ref "--format=%(objectname) %(refname) %(symref)" refs/heads refs/remotes refs/tags > C:/MoneyLab-auto-12/data/processed/auto12/preserve/refs_s1.txt`
  - P3: `set -C && git -C C:/MoneyLab-auto-12 worktree list --porcelain > data/processed/auto12/preserve/worktrees_s2.txt`
  - P4: `set -C && git -C C:/MoneyLab-auto-12 for-each-ref "--format=%(objectname) %(refname) %(symref)" refs/heads refs/remotes refs/tags > data/processed/auto12/preserve/refs_s2.txt`
  - P5: `set -C && git -C C:/MoneyLab-auto-12 worktree list --porcelain > data/processed/auto12/preserve/worktrees_s3.txt`
  - P6: `set -C && git -C C:/MoneyLab-auto-12 for-each-ref "--format=%(objectname) %(refname) %(symref)" refs/heads refs/remotes refs/tags > data/processed/auto12/preserve/refs_s3.txt`
- 기록 내용 전체는 채팅에 내지 않는다(sha256, 줄 수, 판정만).
- 기존 기록은 덮어쓰기·삭제·재생성하지 않는다.
- 재감사 재사용 조건: 기록의 sha256 동일, 기록 생성 뒤 바뀐 파일·줄, 그 변경이 시험 정의·매개변수·수집 조건을 바꾸지 않는다는 근거를 보고하고, 관리자의 명시적 수락이 있어야 한다.
- 위 목록 밖의 기록·로그 파일은 만들지 않는다.

## PRESERVE_RULES

- 직접 확인(WS-A1, WS-A4, PUSH, POST_MERGE_AUDIT): 세 곳 각각 독립 호출 `git -C <wt> rev-parse HEAD HEAD^{tree}`와 `git -C <wt> status --porcelain=v1 --untracked-files=all`. HEAD가 Metadata 값과 같고 status가 빈 출력.
- 기준 s1: WS-A4에서 새 worktree를 만든 뒤 기록한 P1·P2.
- 비교(독립 호출, 출력 원문 판정):
  - s2: `git -C C:/MoneyLab-auto-12 diff --no-index -- data/processed/auto12/preserve/worktrees_s1.txt data/processed/auto12/preserve/worktrees_s2.txt`
  - s2: `git -C C:/MoneyLab-auto-12 diff --no-index -- data/processed/auto12/preserve/refs_s1.txt data/processed/auto12/preserve/refs_s2.txt`
  - s3: `git -C C:/MoneyLab-auto-12 diff --no-index -- data/processed/auto12/preserve/worktrees_s1.txt data/processed/auto12/preserve/worktrees_s3.txt`
  - s3: `git -C C:/MoneyLab-auto-12 diff --no-index -- data/processed/auto12/preserve/refs_s1.txt data/processed/auto12/preserve/refs_s3.txt`
- s2(PUSH 뒤) 허용 차이(이것뿐):
  - worktree 목록: `worktree C:/MoneyLab-auto-12` 블록의 `HEAD <base>` 줄이 `HEAD <I>`로 바뀜
  - refs: `refs/heads/codex/auto-12-controlled-read-nontext` 줄의 objectname이 base에서 I로 바뀜
  - refs: `<I> refs/remotes/origin/codex/auto-12-controlled-read-nontext ` 한 줄 추가
- s3(fetch 뒤) 허용 차이: s2의 차이 전부와 다음뿐
  - `refs/remotes/origin/main` 줄의 objectname이 base에서 M으로 바뀜
  - `refs/remotes/origin/HEAD` 줄: s1에 있었다면 symref 열 `refs/remotes/origin/main`은 그대로이고 objectname만 base에서 M으로 바뀜. s1에 없었다면 s3에도 없어야 함
- 그 밖의 worktree·ref 추가·삭제·변경은 STOP.

## COLLECT_RULES

- WS-B7(R1 뒤):
  - Grep 도구(개수 모드)로 R1의 ID 줄 수(`::`를 포함한 줄)를 세고, Grep 도구(내용 모드)로 요약 줄(`collected`를 포함한 줄)을 읽어 selected·total·deselected를 기록한다. ID 줄 수 = selected, total과 deselected가 함께 있으면 total = selected + deselected여야 한다. 어긋나면 STOP.
  - EX-2·EX-3 기준 ID: Grep 도구(내용 모드)로 R1에서 패턴 `test_value_grammar_violations.*ECON-FWD-M20-WO/2`와 `test_cr_other_forms_deny.*ECON-FWD-M20-WO/2`의 일치 줄을 찾아 각각 OLD 집합으로 기록한다(일치 없음이면 그 사례의 OLD는 공집합).
  - NEW 집합: 각 OLD 줄에서 `ECON-FWD-M20-WO/2`를 `ECON-FWD-M20-WO/3`로 바꾼 문자열.
- PRECOMMIT(R2·R3 뒤), 모두 만족해야 통과:
  - R2에서도 ID 줄 수 = selected, total = selected + deselected(위와 같은 방법).
  - R3의 `-`로 시작하는 ID 줄(`::` 포함)의 집합 = OLD 집합(0–2개)과 정확히 같다.
  - R3의 `+`로 시작하는 ID 줄의 집합 = NEW 집합 ∪ {`tests/test_controlled_read_nontext.py::` 또는 `tests/test_controlled_read_nontext_guard.py::`로 시작하는 ID}와 정확히 같다.
  - 요약 줄의 실행 시간(`in <초>s`) 변화는 ID 변화로 세지 않는다. 수치 변화는 다음 관계로 검증한다: precommit selected = base selected + |추가 ID| − |제거 ID|, deselected는 base와 같다.
  - 중복 ID가 없다.
- 위반은 STOP이며, ID 개수나 허용 접두를 넓혀 해석하지 않는다.

## WS_A (PART=WORKTREE, SETUP_SESSION_ROOT 세션, 모두 독립 호출)

- WS-A1:
  - `pwd -W` -> C:/MoneyLab-auto-10
  - `git -C C:/MoneyLab-auto-10 rev-parse HEAD` -> SETUP_EXECUTION_HEAD
  - `git -C C:/MoneyLab-auto-10 status --porcelain=v1 --untracked-files=all` -> 빈 출력
  - N1 `git -C C:/MoneyLab-auto-10 ls-remote origin refs/heads/main` -> `6bd11b0cfbaadef4a12289d56beed243890d70e8` 와 `refs/heads/main`
  - N2 `git -C C:/MoneyLab-auto-10 ls-remote origin refs/heads/codex/auto-12-controlled-read-nontext` -> 빈 출력
  - `git -C C:/MoneyLab-auto-10 cat-file -t 6bd11b0cfbaadef4a12289d56beed243890d70e8` -> commit
  - `git -C C:/MoneyLab-auto-10 rev-parse 6bd11b0cfbaadef4a12289d56beed243890d70e8^{tree}` -> CANONICAL_BASE_TREE
  - `git -C C:/MoneyLab-auto-10 show-ref --verify --quiet refs/heads/codex/auto-12-controlled-read-nontext` -> 표시된 `Exit code 1`
  - PS `C:/MoneyLab-auto-12` -> ABSENT
  - PRESERVE 직접 확인(세 곳)
- WS-A2: `git -C C:/MoneyLab-auto-10 worktree add -b codex/auto-12-controlled-read-nontext C:/MoneyLab-auto-12 6bd11b0cfbaadef4a12289d56beed243890d70e8`
  - 확인: `git -C C:/MoneyLab-auto-12 rev-parse HEAD HEAD^{tree}` -> base, CANONICAL_BASE_TREE. `git -C C:/MoneyLab-auto-12 status --porcelain=v1 --untracked-files=all` -> 빈 출력. PS `C:/MoneyLab-auto-12/docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT` -> ABSENT
- WS-A3(venv 생성 전에 ignore 확인):
  - `git -C C:/MoneyLab-auto-12 check-ignore -v -- .venv/x` -> source `.gitignore`, pattern이 `!`로 시작하지 않는 한 줄
  - PS `C:/MoneyLab-auto-12/.venv` -> ABSENT
  - `C:/MoneyLab-auto-10/.venv/Scripts/python.exe -m venv C:/MoneyLab-auto-12/.venv`
  - `C:/MoneyLab-auto-12/.venv/Scripts/python.exe --version` -> `Python 3.14.8`
- WS-A4:
  - `git -C C:/MoneyLab-auto-12 check-ignore -v -- data/processed/auto12/x` -> 통과
  - MKD(PS의 `<PY>`는 WS-A 값)
  - P1, P2 생성 후 각 `sha256sum`과 줄 수 보고
  - PRESERVE 직접 확인
- 보고 후 멈춘다. 사용자가 C:/MoneyLab-auto-12에서 새 세션을 시작한다.

## WS_B (PART=C1_ENV, SESSION_ROOT 새 세션, 모두 독립 호출)

- WS-B1: `pwd -W` -> C:/MoneyLab-auto-12. `git -C C:/MoneyLab-auto-12 rev-parse HEAD` -> base, status·cached 빈 출력. `.venv/Scripts/python.exe --version` -> `Python 3.14.8`. RECORDS의 ignore 확인.
- WS-B2: 사용자 /status·/hooks 화면 확인(H1)을 보고에 넣는다. settings의 hook 선언(H2)은 Read로 확인한다. H4는 미확인으로 적는다.
- WS-B3:
  - `sha256sum <WO_SOURCE>` = WO_SHA256
  - PS `C:/MoneyLab-auto-12/docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT/WORK_ORDER.md` -> ABSENT
  - Read로 WO_SOURCE를 읽고 Write 1회로 `docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT/WORK_ORDER.md`를 쓴다.
  - `sha256sum docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT/WORK_ORDER.md` = WO_SHA256
  - 발행본의 형식은 발행 단계 확인값을 해시 동일성으로 이어받는다. 발행 단계에서 확인하지 않은 항목은 미확인으로 남긴다.
- WS-B4 C1:
  - `git add -- docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT/WORK_ORDER.md`
  - `git diff --cached --name-status` -> A와 그 경로 한 줄
  - `git diff --cached --check` -> 빈 출력
  - `git hash-object -- docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT/WORK_ORDER.md` = `git rev-parse :docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT/WORK_ORDER.md`
  - `git commit -m "docs(task): add AUTO-12-CONTROLLED-READ-NONTEXT work order" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`
  - 확인: `git rev-list --parents -n 1 HEAD` -> `<C1> <base>`, `git rev-parse HEAD^{tree}`, `git show --name-status --format= HEAD` -> A 1개, `git rev-parse HEAD:docs/tasks/AUTO-12-CONTROLLED-READ-NONTEXT/WORK_ORDER.md` = 위 OID, status 빈 출력. 승인 창은 ASK_UNVERIFIED로 기록.
- WS-B5 설치(N3, N4):
  - `.venv/Scripts/python.exe -m pip install --no-binary=mypy --no-cache-dir -r requirements-dev.txt`
  - `.venv/Scripts/python.exe -m pip install -e . --no-deps`
- WS-B6 버전·editable 확인:
  - `.venv/Scripts/python.exe -m pip check` -> `No broken requirements found.`
  - `.venv/Scripts/python.exe -m mypy --version` -> `mypy 2.4.0 (compiled: no)`
  - `.venv/Scripts/python.exe -m ruff --version` -> `ruff 0.17.2`
  - `.venv/Scripts/python.exe -m pytest --version` -> `pytest 9.1.1`
  - Read `C:/MoneyLab-auto-12/.venv/Lib/site-packages/moneylab-0.3.0.dist-info/direct_url.json` -> `"editable": true`이고 `"url": "file:///C:/MoneyLab-auto-12"`
  - 하나라도 다르면 STOP.
- WS-B7 baseline 수집:
  - MKD 재확인(네 경로 모두 PS DIRECTORY)
  - PS `C:/MoneyLab-auto-12/data/processed/auto12/collect_base.txt` -> ABSENT
  - R1 생성, `sha256sum data/processed/auto12/collect_base.txt`와 줄 수 보고
  - COLLECT_RULES WS-B7 항목(개수 검증, EX-2·EX-3 OLD·NEW 식별)을 수행하고 OLD·NEW 원문을 보고한다.

## IMPLEMENTATION

- 쓰기: Edit·Write는 ALLOWED_FILES에만 한다. guard.py 편집 뒤 `git status --porcelain=v1`로 hook 오류가 없는지 확인한다. 예상 밖 DENY·hook 오류는 STOP.
- CHECK_COMMANDS(SESSION_ROOT):
  - C1 `.venv/Scripts/python.exe -m ruff check --no-cache --select E4,E7,E9,F src tests` -> `All checks passed!`
  - C2 `.venv/Scripts/python.exe -m ruff check --no-cache --select E4,E7,E9,F .claude/hooks/guard.py` -> `All checks passed!`
  - C3a `.venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache` -> `Success: no issues found`로 시작하는 줄
  - C3b `.venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache src/moneylab/controlled_read` -> `Success: no issues found`로 시작하는 줄
  - C4 `.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/test_controlled_read_nontext.py tests/test_controlled_read_nontext_guard.py tests/test_controlled_read_diagnose.py tests/test_controlled_read_diagnose_guard.py tests/test_controlled_read_precheck.py tests/test_controlled_read_cli.py tests/test_controlled_read_selector.py tests/test_controlled_read_transcript.py tests/test_controlled_read_profiles.py tests/test_controlled_read_store.py tests/test_controlled_read_isolation.py tests/test_agent_guard.py tests/test_skills.py tests/test_repo_hygiene.py`
  - C5 `.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q`
- 순서: C1–C3b -> C4 -> C5. C4 통과 전에는 C5를 실행하지 않는다. C5 통과가 IMPLEMENTATION_PASS 조건이다.
- 고치는 규칙: 신규 시험·ALLOWED 안의 실패는 ALLOWED만 고친다. EX-1–EX-5 밖의 기존 시험 실패는 회귀 -> STOP. 기대값을 구현 결과에 맞춰 완화하는 것은 금지한다.
- 예산: 수행 시간 총 21600초(시험 시간 포함, 따로 보고, TIME_ACCOUNTING), FIX 4회, C4 6회, C5 3회, 같은 실패 2회 연속 STOP. 수정 없이 같은 C5 실패를 반복하지 않는다.

## PRECOMMIT_AUDIT (읽기와 감사, 생성 기록은 R2–R5만)

1. 변경 집합: `git -C C:/MoneyLab-auto-12 diff --name-status 6bd11b0cfbaadef4a12289d56beed243890d70e8`와 `git -C C:/MoneyLab-auto-12 ls-files --others --exclude-standard`로 PROTECTED 판정. tracked 변경은 ALLOWED의 M 10개와 C1의 WORK_ORDER.md(A)뿐, untracked는 ALLOWED의 A 2개뿐이어야 한다. `git -C C:/MoneyLab-auto-12 diff --cached --name-status` -> 빈 출력.
2. `git -C C:/MoneyLab-auto-12 diff --check` -> 빈 출력. PS로 R4 대상 ABSENT -> R4 생성, sha256·줄 수 보고.
3. DIFF_SHAPE: M 10개마다 `git -C C:/MoneyLab-auto-12 diff 6bd11b0cfbaadef4a12289d56beed243890d70e8 -- <path>`를 단독 호출해 원래 출력을 읽는다(잘리면 AUDIT_METHOD의 큰 출력 절차). 소스 4개는 N2–N6 범위, guard는 세 정규식의 profile 대안만, 문서는 N7만, 시험 4개는 EX-1–EX-5의 정확한 변경만이어야 한다. 위반은 STOP.
4. CODE_READ: Read로 transcript.py의 비텍스트 탐색 함수와 공통 텍스트 목록 함수, __main__.py의 정책 생성 지점을 끝까지 읽고 다음을 줄 위치와 함께 판정한다.
   - 재귀 호출이 없다.
   - 자식 전체를 복제·미리 적재하지 않는다.
   - 자식을 꺼낼 때마다 집계·한도·마커·Deadline을 검사한다.
   - 정책 객체를 호출마다 새로 만든다.
   - 근거는 이 읽기와 T4·T6 결과를 함께 쓴다.
5. SIGNATURE: Grep 도구로 네 함수(_tool_result_content_texts, _tool_result_texts, select_text, scan_candidates)의 정의 줄에 `*, nontext=None`이 있는지 확인한다. DETAILS 불변은 1번의 PROTECTED 판정(`src/moneylab/controlled_read/__init__.py` 변경 0)으로 확인하며 이 항목과 분리한다.
6. skip·xfail: Grep 도구로 신규 시험 2개에서 `pytest.mark.skip`, `skipif`, `xfail`, `pytest.skip(`, `pytest.xfail(` -> 0. M 시험 4개의 추가 줄은 3번에서 확인한다.
7. collect: PS로 R2 대상 ABSENT -> R2. PS로 R3 대상 ABSENT -> R3. R3를 Read(100줄씩, 최대 30회)로 열고 COLLECT_RULES PRECOMMIT 판정.
8. FMT: PS로 R5 대상 ABSENT -> R5. 이어서 FMT `added data/processed/auto12/added.diff`, FMT `changed <M 10개>`, FMT `new <A 2개>`를 각각 독립 호출. 셋 다 RESULT=PASS여야 한다. 판정하지 못한 항목은 통과로 쓰지 않는다.
9. SYNTHETIC_ESCAPE_AUDIT: 신규 시험 2개를 Read로 끝까지 읽어 비ASCII 합성 입력이 명시적 이스케이프인지 확인하고 줄 위치·판정을 보고한다. 위반·누락·모호함은 STOP.
10. AUDIT_SET 확정: 12개 각각 `sha256sum <path>`와 `git -C C:/MoneyLab-auto-12 hash-object -- <path>`를 실행해 경로와 전체 값으로 보고한다.
11. 감사 끝에 12개의 W를 다시 계산해 10번과 같은지 확인한다(감사 중 불변).

## COMMIT

- `git -C C:/MoneyLab-auto-12 add -- <ALLOWED 12개 경로를 ALLOWED 순서로>`(줄바꿈 변환 경고는 보고만)
- `git -C C:/MoneyLab-auto-12 diff --cached --name-status` -> M 10, A 2, 경로가 ALLOWED와 같음
- `git -C C:/MoneyLab-auto-12 rev-parse :<경로1> :<경로2> … :<경로12>`(한 명령, ALLOWED 순서) -> AUDIT_SET의 O와 순서대로 같음
- `git -C C:/MoneyLab-auto-12 diff --cached --check` -> 빈 출력
- `git -C C:/MoneyLab-auto-12 commit -m "feat(automation): add controlled_read profile ECON-FWD-M20-WO/2" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"` 1회
- 확인: `git -C C:/MoneyLab-auto-12 rev-list --parents -n 1 HEAD` -> `<I> <C1>`, `git -C C:/MoneyLab-auto-12 rev-parse HEAD^{tree}`, `git -C C:/MoneyLab-auto-12 show --name-status --format= HEAD` -> 12개, `git -C C:/MoneyLab-auto-12 rev-parse HEAD:<경로1> … HEAD:<경로12>` -> O, status·cached 빈 출력. 승인 창은 ASK_UNVERIFIED로 기록.

## CLEAN_COMMIT_E2E

- `git -C C:/MoneyLab-auto-12 rev-parse HEAD` -> I, status·cached 빈 출력
- `git -C C:/MoneyLab-auto-12 rev-parse HEAD:<경로1> … HEAD:<경로12>` -> O
- C4 1회(구현 예산과 따로 기록)
- 실행 뒤 `git -C C:/MoneyLab-auto-12 rev-parse HEAD HEAD^{tree}`, `git -C C:/MoneyLab-auto-12 branch --show-current`, status가 그대로
- 새 checkout 재현성 검증이 아니다.

## PUSH

- N5 `git -C C:/MoneyLab-auto-12 ls-remote origin refs/heads/main` -> base
- N6 `git -C C:/MoneyLab-auto-12 ls-remote origin refs/heads/codex/auto-12-controlled-read-nontext` -> 빈 출력
- N7 `git -C C:/MoneyLab-auto-12 push -u origin codex/auto-12-controlled-read-nontext` 1회
- N8 `git -C C:/MoneyLab-auto-12 ls-remote origin refs/heads/codex/auto-12-controlled-read-nontext` -> I
- PS로 P3·P4 대상 ABSENT -> P3, P4 -> PRESERVE s2 판정, PRESERVE 직접 확인

## PR_CI

- N9 `git -C C:/MoneyLab-auto-12 ls-remote origin refs/heads/main` -> base
- N10 `git -C C:/MoneyLab-auto-12 ls-remote origin refs/heads/codex/auto-12-controlled-read-nontext` -> I
- N11 `gh pr list -R swk3169/MoneyLab --head codex/auto-12-controlled-read-nontext --base main --state open --json number,headRefOid` -> `[]`
- N12 `gh pr create -R swk3169/MoneyLab --base main --head codex/auto-12-controlled-read-nontext --title "<승인 제목>" --body "<승인 본문>"` 1회(임시 파일 없음)
- N13 `gh pr view <N> -R swk3169/MoneyLab --json number,state,isDraft,baseRefName,headRefName,headRefOid,commits,files,mergeable` -> OPEN, 비초안, base main, head 일치, headRefOid I, 커밋 2개(C1, I), 파일 13개
- 조회 한도:
  - N14 `gh pr checks <N> -R swk3169/MoneyLab` 최대 40회
  - N15 `gh run list -R swk3169/MoneyLab --branch codex/auto-12-controlled-read-nontext --json databaseId,headSha,name,status,conclusion` 최대 10회
  - N16 `gh run view <run> -R swk3169/MoneyLab --json jobs` 최대 2회
  - N17 `gh run view <run> -R swk3169/MoneyLab --job <linux job id> --log-failed` 최대 1회. N15에서 run status completed와 headSha = I를 확인한 뒤에만 실행한다.
- 같은 종류 조회 간격 60초 이상. 조회 없는 대기 `sleep 60`(백그라운드 실행)은 허용하며 CI 시간에 포함한다.
- CI_STATES: pytest pass -> REQUIRED_PASS. pytest fail·cancel -> STOP. pending -> 대기. Linux fail -> Linux 판정 대상(실패 아님). 표가 없거나 알 수 없는 응답 -> UNPARSED(최대 5줄 보고, 사용자 재개 대기). 인증·통신·구문 오류 -> STOP.
- Linux 판정: 실패 ID 집합이 NONREQUIRED_CI_BASELINE 2건의 부분집합이면 NO_NEW_LINUX_REGRESSION. 그 밖이나 로그 미확보는 STOP. Linux pass면 N17 생략.
- CI 시간: N12 직후부터 두 job 최종 상태와 Linux 판정 끝까지 3600초 이하.

## MERGE

- N18 `gh pr view <N> -R swk3169/MoneyLab --json state,isDraft,baseRefName,headRefName,headRefOid,commits,files,mergeable` -> OPEN, 비초안, 일치, I, 커밋 2, 파일 13, MERGEABLE
- N19 `gh pr checks <N> -R swk3169/MoneyLab` 1회 -> REQUIRED_PASS, Linux 판정 유지
- N20 `git -C C:/MoneyLab-auto-12 ls-remote origin refs/heads/main` -> base
- N21 `git -C C:/MoneyLab-auto-12 ls-remote origin refs/heads/codex/auto-12-controlled-read-nontext` -> I
- N22 `gh pr merge <N> -R swk3169/MoneyLab --merge --match-head-commit <I>` 1회(`--admin`·`--auto`·`--squash`·`--rebase`·`--delete-branch` 금지)
- N23 `gh pr view <N> -R swk3169/MoneyLab --json state,mergeCommit,mergedAt` -> MERGED, M

## POST_MERGE_AUDIT

- N24 `git -C C:/MoneyLab-auto-12 fetch origin main` 1회
- E-1 `git -C C:/MoneyLab-auto-12 rev-parse origin/main` -> M
- E-2 `git -C C:/MoneyLab-auto-12 rev-list --parents -n 1 <M>` -> 정확히 `<M> 6bd11b0cfbaadef4a12289d56beed243890d70e8 <I>`
- E-3 `git -C C:/MoneyLab-auto-12 merge-base 6bd11b0cfbaadef4a12289d56beed243890d70e8 <I>` -> base
- E-4 `git -C C:/MoneyLab-auto-12 rev-parse <M>^{tree} <I>^{tree}` -> 두 줄이 같음
- E-5 `git -C C:/MoneyLab-auto-12 diff --name-only <I> <M>` -> 빈 출력
- E-6 `git -C C:/MoneyLab-auto-12 merge-tree --trivial-merge 6bd11b0cfbaadef4a12289d56beed243890d70e8 <I> 6bd11b0cfbaadef4a12289d56beed243890d70e8` -> 빈 출력이고 표시된 0이 아닌 종료 코드 없음(미표시는 기록). E-2·E-3 중 하나라도 실패하면 E-6을 실행하지 않고 FAIL. `--write-tree` 금지.
- PS로 P5·P6 대상 ABSENT -> P5, P6 -> PRESERVE s3 판정. PRESERVE 직접 확인. TARGET_WORKTREE clean.
- branch·worktree 보존.

## COMPLETE

- 채팅 보고만 한다: base·C1·I·M의 SHA·parent·tree, E-1–E-6, preserve s2·s3, 시험·CI·Linux 판정, 예산, ASK 상태, DEVIATIONS·ISSUES·PROPOSED_ERRATA.
- 검증 한계: 실제 세션 호환성 미확인, 추가 인코딩·분할·외부 참조 마커 미감지, 종료 코드 미표시 항목, H4.
- 실제 diagnose /2·precheck·run은 별도 계약이다. AUTO-08-FIRST-USE의 STOP을 유지한다.

## TIME_ACCOUNTING

- 수행 시간 = 측정 구간 합계 − 제외 구간 합계. 시각은 독립 호출 `date -u +%Y-%m-%dT%H:%M:%SZ`의 출력이다.
- 제외 구간: (가) 보고 직후부터 재개 메시지 뒤 첫 명령 직전까지의 사용자 재개 대기. (나) 권한 창 대기는 실제 대기를 따로 측정할 수 있을 때만 빼며, 측정할 수 없으면 포함하고 "보수적 상한"으로 기록한다.
- IMPLEMENTATION 21600초, CI 3600초(PR_CI 정의).

## NETWORK

- 이 문서의 N1–N24만, 해당 gate 승인으로, 적힌 횟수 안에서 쓴다. N3·N4는 PyPI와 빌드 의존성 다운로드다. 실패하면 STOP하고 재시도하지 않는다.

## EXPECTED_ASK

- WS-A2 worktree add, WS-A3 venv 생성(나타나는 경우)
- INLINE_CHECKS PS·FMT 실행(인라인 코드나 작업 디렉터리 밖 경로 창, 나타나는 경우)
- WS-B3 WORK_ORDER.md Write(task-contract)
- `.claude/hooks/guard.py`·`docs/agent_workflow.md` Edit
- 보호 경로인 기존 시험 4개(`tests/test_controlled_read_profiles.py`, `tests/test_controlled_read_selector.py`, `tests/test_agent_guard.py`, `tests/test_controlled_read_diagnose.py`)의 Edit(protected-edit 등, 나타나는 경우)
- MKD의 `mkdir`(나타나는 경우)
- `git commit` 2회, `git push`, `gh pr create`, `gh pr merge`, `pip install`
- 목록 밖 ASK, 거절, 무응답은 STOP. DENY는 즉시 STOP이며 재시도·변형하지 않는다.

## FORBIDDEN_ACTIONS

- 실제 세션·debug·메모리·세션 JSONL·tool-results 열람(AUDIT_METHOD의 큰 출력 1개 파일 절차 제외)
- 실제 세션에서 diagnose·precheck·run·status 실행, 실제 지시문 수정
- ALLOWED 밖·PROTECTED 변경, EX 밖 기존 시험 변경, 시험 삭제, skip·xfail 추가
- guard N7 밖 변경, settings·hook 등록 변경, 명령 은닉·문자열 분할·설정 완화
- controlled_read를 import하는 인라인 코드, INLINE_CHECKS 밖의 인라인 코드, 스크립트 파일 작성·실행, 새 검사 프로그램
- 명령 체인·파이프·리디렉션(RECORDS 원문 예외만)
- `git add .`·`-A`, `--no-verify`, amend, force push, reset·restore·stash·clean·rebase·cherry-pick·checkout, fetch --all·--prune, branch·worktree 삭제
- PRESERVED_WORKTREES의 변경과 그 파일 내용·기록·data 열람(PRESERVE_RULES의 git 조회와 WS-A3의 venv 생성용 인터프리터 실행만 예외)
- AUTO-08/09/10/11·FIRST-USE 기록 변경, 연구 공개 백업 진행

## STOP_CONDITIONS

- base·HEAD·tree·cwd·SETUP_EXECUTION_HEAD 불일치, WO 해시 불일치
- 단계별 허용 상태 밖의 변경:
  - WS 완료부터 IMPLEMENTATION 시작 전까지: 0(ignored 기록·venv 제외)
  - IMPLEMENTATION: staged 0, tracked는 M 10개 안, untracked는 A 2개 안
  - PRECOMMIT_AUDIT: W 불변
  - COMMIT add 뒤 commit 전: staged = 12개
  - commit 뒤: 0
- EXIT_CRITERIA 미충족, 결과 불명, 출력 잘림의 허용 절차 밖 우회
- 회귀, DIFF_SHAPE·CODE_READ 위반, PROTECTED diff, COLLECT_RULES 위반, FMT FAIL·오류, PS 비기대 상태
- 예산 초과(21600초, CI 3600초, 조회 횟수, FIX, 같은 실패 2회 연속)
- guard DENY, hook 오류, 목록 밖 ASK, 거절·무응답
- REQUIRED_FAIL, Linux 신규 실패·판정 불가, merge 사전 검증 실패, preserve 허용 밖 차이
- 계약 모순, 상위 규칙과 충돌
- 공통: 재시도·되돌리기·정리 없이 분류, 마지막 PASS 단계, 실제 HEAD·tree를 보고하고 별도 승인을 기다린다.

## REQUIRED_EVIDENCE

- GIT_VERIFIABLE: SHA·parent·tree, 파일 집합, blob OID, merge parent 순서
- CLAUDE_REPORTED: 검사 판정 줄, W, PS·FMT 출력, collect·preserve 판정, CODE_READ 근거, `pwd -W`·`date -u`, 표시된 종료 코드 또는 미표시
- INDEPENDENT: 사용자 /status·/hooks 확인, GitHub CI 결과
- 관측하지 못한 승인 창은 ASK_UNVERIFIED.

## REQUIRED_REPORT

- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- cwd, HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, clean, diff --check
- 판정 줄과 종료 코드 또는 미표시, ASK 상태, 예산
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES/NO, READY_FOR_<NEXT> = YES/NO

## AFTER_COMPLETE (참고, 이 task 밖)

diagnose /2(같은 고정 prefix) -> precheck /2 -> 별도 승인 run -> ECON-FWD-M20 발행 계산. 각 단계에 별도 계약과 승인이 필요하다.
