# Work Order: AUTO-15-CONTROLLED-READ-CANDIDATES — controlled_read candidates 하위 명령(고정 prefix 후보 메타데이터 열거)

이 파일은 발행 정본이다. 발행은 실행 승인이 아니며 각 gate에는 별도 승인이 필요하다. 이 정본은 발행 후 수정하지 않고, C1 이후 계약 변경은 docs/tasks/AUTO-15-CONTROLLED-READ-CANDIDATES/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: AUTO-15-CONTROLLED-READ-CANDIDATES
TASK_ID: AUTO-15-CONTROLLED-READ-CANDIDATES
TITLE: 고정 prefix 후보의 위치·selector·선택/추출 판정·해시만 출력하는 candidates 하위 명령
VERSION: 1.0
STATUS: ISSUED
REPOSITORY: swk3169/MoneyLab
CANONICAL_BASE_SHA: 2005e301e1de80150db4c7dcefd4a6e2b5d0b451
CANONICAL_BASE_TREE: b34f8db4eec8bc4633f2b9b50062137617047935
TARGET_BRANCH: codex/auto-15-controlled-read-candidates
TARGET_WORKTREE: C:/MoneyLab-auto-15
SETUP_SESSION_ROOT: C:/MoneyLab-auto-12
SETUP_EXECUTION_HEAD: ad2ab7cbe8c7045f340afd9380c35c852918fe93
SESSION_ROOT: C:/MoneyLab-auto-15
PYTHON_VERSION: 3.14.8
TOOL_VERSIONS: mypy 2.4.0 (compiled: no), ruff 0.17.2, pytest 9.1.1
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: pytest
BUNDLE_ELIGIBLE: NO

- 표기: base = CANONICAL_BASE_SHA 40자, C1 = 이 Work Order 커밋, I = 구현 커밋, M = merge 커밋.
- CANONICAL_BASE_SHA는 WS-A1에서 원격 main과 대조한다. 다르면 STOP하며 임의로 갱신하지 않는다.
- SETUP_SESSION_ROOT는 PART=WORKTREE에만 쓴다. SESSION_ROOT는 PART=C1_ENV부터 COMPLETE까지 같은 세션에서 쓴다. 세션이 바뀌면 ACCEPTED ERRATA가 필요하다.
- PRESERVED_WORKTREES (HEAD, tree, status 빈 출력이 기대값):
  - C:/MoneyLab-auto-12 @ ad2ab7cbe8c7045f340afd9380c35c852918fe93, tree b34f8db4eec8bc4633f2b9b50062137617047935
  - C:/MoneyLab-auto-10 @ b876d7d2d8af953ff805f61070768087b28489c4, tree 191535287b124be9c9c3fc8882f50f028c5057df
  - C:/MoneyLab-auto-09 @ 326fc4985f1118b1a0a1c81d197babff5d2dce72, tree fe3de24c2394a894d16e62070827695a81cfa706
  - C:/MoneyLab-auto-08-first-use @ 2b826d4ed9e278b28456eff9f8c70fa1070895ac, tree 0bc73292da8f1a6ee32cd866bb88e296e93fca2b
- APPROVAL_DIR은 WORKSPACE_SETUP 승인문에서 슬래시 절대 경로로 제공한다. 이 문서에는 사용자 홈 절대 경로를 넣지 않는다.
- WO_SOURCE = APPROVAL_DIR/WORK_ORDER.review.md (발행 정본. 검토본 WORK_ORDER.review-draft*.md는 WO_SOURCE가 아니다). 절대 경로는 채팅 승인문에만 쓴다.
- NONREQUIRED_CI_BASELINE: pytest-linux-experimental의 기존 실패 2건(재조회 없이 재사용)
  - tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through
  - tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0

## GATE_SEQUENCE

WORKSPACE_SETUP PART=WORKTREE -> WORKSPACE_SETUP PART=C1_ENV -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

- 한 번에 한 단계만 전진한다. 각 단계에는 그 단계를 실행하는 세션에서 받은 Gate Authorization 원문이 필요하다. 자동 전진과 단계 묶음은 없다.
- 후퇴는 IMPLEMENTATION으로만, 명시적 승인으로 한다. COMMIT 이후 수정은 새 커밋이며 amend는 없다.
- 이전 gate 승인이나 이 Work Order 자체는 다음 gate의 승인이 아니다.

## AUTHORIZATION_FORMS

- PART=WORKTREE: GATE_AUTHORIZATION: AUTO-15-CONTROLLED-READ-CANDIDATES WORKSPACE_SETUP PART=WORKTREE WO_SHA256=<64hex> APPROVAL_DIR=<슬래시 절대 경로>
- PART=C1_ENV: GATE_AUTHORIZATION: AUTO-15-CONTROLLED-READ-CANDIDATES WORKSPACE_SETUP PART=C1_ENV WO_SHA256=<64hex> WO_SOURCE=<슬래시 절대 경로>
- 그 밖의 gate: GATE_AUTHORIZATION: AUTO-15-CONTROLLED-READ-CANDIDATES <GATE> WO@<C1 SHA>
  - PR_CI 추가 필드: PR_CREATE: YES, REPOSITORY: swk3169/MoneyLab, BASE: main, HEAD_BRANCH: codex/auto-15-controlled-read-candidates, HEAD_SHA: <I>, PR_TITLE, PR_BODY(PR_CI 승인 때 확정)
  - MERGE 추가 필드: MERGE_EXECUTE: YES, PR: <N>, HEAD_SHA: <I>
- 대조: 원문이 있고, 필드와 실행 인자가 문자열로 완전히 같아야 한다. 어긋나면 STOP.

## AUTHORIZATION_MODEL

- 이 Work Order는 각 gate의 최대 범위만 정하며 실행 승인이 아니다.
- 변경·실행에는 (1) 이 Work Order의 gate 범위, (2) 그 gate의 Gate Authorization 원문, (3) 도구 권한 창과 guard 판정이 모두 필요하다. 어느 하나가 다른 것을 대신하지 않는다.
- gate 안에서는 그 gate가 허용하는 읽기·수정·합성 fixture 작성·오프라인 검사·실패 분석과 수정을 사용자 확인 없이 진행한다. 다음 gate 승인 시점, STOP 조건, 실제 사용자 결정이 필요할 때만 보고하고 멈춘다.
- 관측하지 못한 승인 창은 ASK_UNVERIFIED로 기록하며, 사용자에게 다시 떠올려 달라고 하지 않는다. DENY·권한 거절·무응답은 STOP이다.
- hook 운영 위험: settings는 hook을 CLAUDE_PROJECT_DIR 아래 작업 사본의 .claude/hooks/guard.py로 선언한다. IMPLEMENTATION 중 guard.py 편집이 같은 세션의 판정에 영향을 줄 수 있다. 실제 hook 경로(H4)는 관측 전까지 미확인이다. 편집 뒤 예상 밖 DENY나 hook 오류가 나면 STOP한다.

## OBSERVATION_LIMITS (미리 정한 관측 한계)

- 종료 코드: 도구가 숫자로 표시한 종료 코드는 0을 포함해 모두 관측값이다. 숫자가 표시되지 않으면 "미표시"로 기록하며, 미표시만으로 실패하지 않고 0이 입증됐다고 쓰지도 않는다. 프로그램 JSON 안의 exit_code는 OS 종료 코드와 같다고 쓰지 않는다.
- 출력 끝 LF와 stdout·stderr 분리는 도구 표시로 관측할 수 없다. 이 둘은 통과 조건이 아니며 STOP 사유도 아니다. 미확인으로 기록한다.
- 백그라운드 실행 결과는 그 호출이 알려준 결과 파일 하나만 Read로 100줄씩, 최대 30회 연다. Grep으로 대체하지 않는다. 다른 tool-results·세션·debug 파일은 열지 않는다.

## EXIT_CRITERIA

- 일반: 계약에 적힌 기대 출력이 있고 도구 오류 표시가 없으면 통과다. 표시된 0이 아닌 종료 코드는 아래 정상 예외를 빼고 실패다.
- 도구별: pytest 요약 줄에 passed가 있고 failed·error가 없다. ruff는 "All checks passed!". mypy는 "Success: no issues found"로 시작하는 줄. pip install은 표시된 0이 아닌 종료 코드와 ERROR 줄이 없고 "Successfully installed" 또는 "Requirement already satisfied"가 있다([notice] 줄은 판정에 쓰지 않음).
- 정상 예외:
  - git show-ref --verify --quiet <ref>의 표시된 Exit code 1(로컬 ref 부재 기대)
  - git ls-remote의 빈 출력(원격 ref 부재 기대)
  - git diff --no-index의 표시된 Exit code 1(차이 있음). 판정은 출력 내용으로 한다
  - git diff(--stat, --name-status, --name-only 포함)는 출력 내용으로 판정한다. git diff --check와 git diff --cached --check는 빈 출력이어야 한다
  - git check-ignore -v는 한 줄, source .gitignore, pattern이 !로 시작하지 않음, 표시 경로가 요청 경로와 같음
  - Grep 도구의 "No matches found" 또는 개수 0은 기대가 0인 검사에서 통과
  - gh pr checks는 표가 완전히 파싱되면 표시된 종료 코드(대기 8, 비필수 실패 1)를 기록만 하고 CI_STATES로 판정한다
  - PS·FMT는 각 절의 RESULT·종료 코드 규칙으로 판정한다

## GOAL

moneylab.controlled_read에 candidates 하위 명령을 추가한다. 승인된 고정 prefix [0, N)의 SHA·LF를 검증한 뒤, profile의 후보 text 문자열을 최대 8개까지 열거하고, 후보마다 위치·selector 표현 가능 여부·기존 run 선택/추출 경로의 판정·본문 해시와 길이만 출력한다. 본문·주변 문맥·키 이름·type 이름·표식 줄 원문은 출력하지 않는다. 기록을 만들지 않는다. 후보를 자동으로 고르지 않는다. 기존 run·status·precheck·diagnose 동작은 바꾸지 않는다. 실제 세션 조회는 이 계약 범위 밖이다.

## BACKGROUND

- AUTO-14 precheck(/2)는 고정 prefix 44113503바이트(5433d3eb2ce924e22e2cbd6e71d6e4d77f35b2e1e102825b2d4b73cfef2351f2, line_count 14707)에서 PRECHECK_MULTIPLE_CANDIDATES, candidate_count 2를 보고했다. 기존 공개 CLI로는 두 후보를 구분할 수 없다(읽기 전용 설계 검토 결과).
- AUTO-08-FIRST-USE의 STOP, PR #40·ECON-FWD-M20 발행 계산 미완료, 연구 공개 백업 보류를 유지한다.

## DESIGN_CONTRACT

### N1 보존

- run, status, precheck, diagnose의 CLI·문법·스키마·출력 바이트·판정을 바꾸지 않는다.
- 다음 파일은 바꾸지 않는다: src/moneylab/controlled_read/__init__.py, selector.py, store.py, profiles.py.
- 다음 정의는 바꾸지 않는다: transcript.Candidate, select_text, _find, _lines, parse_line, _user_blocks, _assistant_texts, _tool_result_texts, _tool_result_content_texts, NontextPolicy, open_session, Session, Session.rehash, Deadline, FormatViolation, _json_type; diagnose.py의 기존 상수(DIAGNOSE_*, APPLICABILITY, FIELDS, JSON_TYPES, UNLISTED_FIELDS, BLOCK_INDEX_CHECKS, ITEM_INDEX_CHECKS, VIOLATION_KEYS, TARGET_KEYS, DIAGNOSE_KEYS)와 기존 함수·클래스(DiagnoseError, parse_diagnose, open_fixed_prefix, violation_object, check_violation, diagnose_document, _count).
- 새 모듈을 추가하지 않는다. 기존 시험 변경 예외(EX)는 0건이다.
- scan_candidates는 positions·limit를 넘기지 않으면 반환값·예외·순서가 이전과 같다. precheck·diagnose 경로는 positions·limit를 넘기지 않는다.

### N2 scan_candidates 확장 (src/moneylab/controlled_read/transcript.py)

- 서명: 현재 정의의 기존 위치 인자(prefix, kinds, is_candidate, deadline)와 그 타입 표기, 기존 keyword-only 인자 nontext와 그 표기(현재 표기 없음이면 그대로), 반환 타입 표기(list[Candidate])를 보존한다. keyword-only 인자 positions와 limit를 추가하며 둘 다 기본값 None이다.
  - positions·limit에는 타입 표기를 붙일 수 있다. 붙이는 경우 positions: list[tuple[int, int | None, bytes]] | None, limit: int | None를 쓴다. 표기 여부는 C3a·C3b(mypy) 통과를 조건으로 구현에서 정한다.
  - 정의는 한 줄 또는 여러 줄 모두 허용한다.
- 새 클래스: class CandidateLimitReached(Exception). ControlledReadError의 하위 클래스가 아니다. 속성이나 메시지에 세션 값을 담지 않는다.
- is_candidate(text)가 참인 각 후보에 대해, append 직전에 다음을 순서대로 한다.
  1. limit가 정수이고 len(found) == limit이면 CandidateLimitReached를 던진다(Candidate와 positions에 추가하지 않음). 따라서 적재 목록은 최대 limit개다.
  2. found.append(Candidate(...)) (기존과 같음)
  3. positions가 list면 positions.append((line_no, block_index, digest)). block_index는 tool_result 후보의 user content block 위치(1부터), assistant 후보는 None. digest = hashlib.sha256(text.encode("utf-8", "surrogatepass")).digest(). 텍스트 자체는 보관하지 않는다.
- CandidateLimitReached는 scan_candidates 안의 FormatViolation 처리(exc._at)를 거치지 않고 그대로 전파된다. 그 뒤의 줄은 읽지 않는다.
- 그 밖의 줄(검사 순서, 기존 예외, 반환값)은 바꾸지 않는다.
- 시험만을 위한 상태 노출 API(found 반환, 카운터 공개 등)는 추가하지 않는다.

### N3 candidates 처리 (src/moneylab/controlled_read/diagnose.py에 추가, __main__.py에 분기)

새 상수(diagnose.py):
- CANDIDATES_OPTIONS = ("--task", "--project-key", "--session", "--profile", "--expect-prefix-bytes", "--expect-prefix-sha256")
- CANDIDATES_SCHEMA = "moneylab.controlled_read.candidates/1"
- CANDIDATES_LISTED = "CANDIDATES_LISTED", CANDIDATES_LIMIT_EXCEEDED = "CANDIDATES_LIMIT_EXCEEDED"
- CANDIDATES_DETAILS = {CANDIDATES_LISTED: "every candidate of the fixed prefix is listed with its selection result", CANDIDATES_LIMIT_EXCEEDED: "the scan stopped because the fixed prefix holds more candidates than the candidate limit"}
- CANDIDATE_LIMIT = 8
- CANDIDATES_KEYS, CANDIDATE_ITEM_KEYS, CANDIDATE_STATES, CANDIDATE_LOCAL_CODES, CANDIDATES_GLOBAL_CODES (N4·N6에서 정의)

새 함수(diagnose.py): parse_candidates(argv), 처리 도우미, check_candidates_document(doc), candidates_document(...). __main__.py: _candidates(argv, root, home)와 run()의 분기 `if argv[:1] == ["candidates"]: return _candidates(argv, root, home)`.

처리 순서(__main__._candidates):
1. 인자: grammar._values(argv, "candidates", CANDIDATES_OPTIONS). 값은 valid_task_id, valid_project_key, valid_session, valid_profile, N은 diagnose.PREFIX_BYTES fullmatch이고 1 ≤ N ≤ 67108864, SHA는 diagnose.PREFIX_SHA256 fullmatch. 실패는 ARGUMENT_INVALID 문서(N6의 모든 식별 필드 null). ARGUMENT_INVALID 문서가 만들어지는 곳은 이 단계뿐이다.
2. 환경: confirmed_root(root), confirmed_home(home). 실패는 ENVIRONMENT_INVALID.
3. deadline = transcript.Deadline() 1개. 이후 열기·scan·선택·재해시 전체에 쓴다. 한도 60초(transcript.TIME_LIMIT)를 바꾸거나 연장하지 않는다.
4. diagnose.open_fixed_prefix(home, PK, SESSION, N, SHA, target, deadline). 실패 코드는 그대로(SESSION_PATH_INVALID, SESSION_NOT_FOUND, SESSION_TRUNCATED, SESSION_UNREADABLE, TIME_LIMIT_EXCEEDED, DIAGNOSE_PREFIX_MISMATCH, DIAGNOSE_PREFIX_NOT_LINE_ALIGNED). checks.prefix = FAILED.
5. scan: transcript.scan_candidates(prefix, profile.kinds, lambda t: profiles.marker_line_present(profile, t), deadline, **nontext_kwargs(scan용 새 정책 객체, /2일 때만), positions=새 리스트, limit=CANDIDATE_LIMIT)
   - CandidateLimitReached: checks.scan = LIMIT_STOPPED, 후보 처리를 하지 않고 7로 간다(결과 후보 CANDIDATES_LIMIT_EXCEEDED).
   - FormatViolation 또는 ControlledReadError: checks.scan = FAILED. TIME_LIMIT_EXCEEDED면 재해시 없이 prefix_check = INCOMPLETE로 확정. 그 밖은 결과 후보 = 그 코드(FORMAT_UNSUPPORTED 등)로 7로 간다.
   - 정상: checks.scan = PASSED.
6. 후보별 선택(prefix 순서, i = 1..n):
   a. selector = grammar.format_selector(kind, ident, text_index). None이면 state = SELECTOR_UNREPRESENTABLE, selector 출력 null.
   b. 표현 가능한 selector 문자열이 다른 후보의 selector와 같으면, 그 selector를 가진 후보 모두 state = SELECTOR_DUPLICATE. 이 후보들은 select_text를 부르지 않는다.
   c. 그 밖: parsed = grammar.parse_selector(selector)
      - parse_selector가 ARGUMENT_INVALID를 내면 내부 불변식 위반이다(format_selector가 문법을 이미 검증함). ControlledReadError가 아닌 예외(예: RuntimeError, 메시지에 세션 값 없음)를 던져 처리 전체를 끝낸다. 정상 candidates 문서를 만들지 않으며 stdout에 아무것도 쓰지 않는다. 후보·계산값을 출력하지 않는다.
   d. text = transcript.select_text(prefix, parsed, deadline, **nontext_kwargs(새 정책 객체, /2일 때만))
      - ControlledReadError e:
        - e.code ∈ CANDIDATE_LOCAL_CODES이면 state = e.code, 다음 후보로.
        - e.code ∈ CANDIDATES_GLOBAL_CODES 또는 그 밖의 DETAILS 코드(ARGUMENT_INVALID 제외)면 전체 처리 실패: checks.selected = FAILED, 결과 후보 = e.code. TIME_LIMIT_EXCEEDED면 재해시 없이 prefix_check = INCOMPLETE로 확정. 그 밖은 7로 간다. 이미 구한 후보 상태와 values는 모두 버린다.
        - e.code가 ARGUMENT_INVALID면 c와 같은 내부 불변식 위반으로 처리한다.
      - 성공: sha256(text.encode("utf-8", "surrogatepass")).digest()가 positions[i]의 digest와 다르면 state = SELECTION_MISMATCH.
      - 같으면 body = profiles.extract(profile, text). ControlledReadError e는 d와 같은 분류 규칙을 적용한다(로컬이면 state = e.code, 전체 실패 코드면 전체 실패). 성공하면 state = OK, values = profiles.values(body).
   e. 모든 후보 처리 뒤 checks.selected = PASSED. 후보가 0개면 처리 없이 PASSED.
7. 재해시: replaced, check = session.rehash(deadline). prefix_check = check. replaced가 None이 아니면 status = replaced이고 candidates·candidate_count·candidate_count_at_least는 모두 null(폐기). checks는 그때까지의 값을 유지한다.
8. 결과:
   - 재해시 MATCHED + scan PASSED + selected PASSED → CANDIDATES_LISTED, candidate_count = n, candidates = 항목 n개
   - 재해시 MATCHED + scan LIMIT_STOPPED → CANDIDATES_LIMIT_EXCEEDED, candidate_count_at_least = 9
   - 재해시 MATCHED + 그 밖 → 앞선 결과 후보 코드
9. 문서를 만든 뒤 check_candidates_document(doc)를 통과해야 출력한다. 실패하면 ValueError(정의되지 않은 예외)로 끝나며 stdout에 아무것도 쓰지 않는다.
10. 기록 함수(store.prepare_attempt, store.create_record)는 호출하지 않는다. handle은 open_fixed_prefix 이후 finally에서 한 번 닫는다(내부 불변식 위반 예외 경로 포함).

정책 객체: profile.skip_marker_free_nontext가 True일 때만 scan 1회와 select_text 1회마다 새 NontextPolicy(profile.begin, profile.end, deadline)를 만든다. False면 nontext 키워드를 넘기지 않는다(AUTO-12 __main__._nontext와 같은 방식).

### N4 선택 경로 오류 분류(빠짐없이)

parse_selector·select_text·extract가 낼 수 있는 ControlledReadError 코드와 분류:
- CANDIDATE_LOCAL_CODES(후보 단위, 처리 계속): ENTRY_NOT_FOUND, ENTRY_DUPLICATE, TOOL_RESULT_ERROR, TEXT_BLOCK_NOT_FOUND, ENCODING_INVALID, TEXT_LIMIT_EXCEEDED, BOM_PRESENT, CR_PRESENT, MARKER_MISSING, MARKER_DUPLICATE, MARKER_ORDER_INVALID, BODY_EMPTY, BODY_LIMIT_EXCEEDED
- CANDIDATES_GLOBAL_CODES(전체 실패, 정의된 문서로 보고, 목록 폐기): TIME_LIMIT_EXCEEDED, SESSION_CORRUPT, LINE_LIMIT_EXCEEDED, ENTRY_LIMIT_EXCEEDED, FORMAT_UNSUPPORTED(FormatViolation 포함), SELECTOR_KIND_MISMATCH, TEXT_BLOCK_AMBIGUOUS
- 내부 불변식 위반(정의된 문서 없음, 출력 없음): 선택 단계의 ARGUMENT_INVALID
- 그 밖의 DETAILS 코드가 선택 단계에서 나오면 전체 실패로 처리한다(정의된 문서). 후보 단위 상태로 바꾸지 않는다. ARGUMENT_INVALID는 이 규칙에서 제외되며 항상 내부 불변식 위반이다.
- 근거: scan이 같은 prefix의 모든 항목에 구조 검사를 이미 통과시켰으므로 선택 단계의 FORMAT_UNSUPPORTED·SESSION_CORRUPT·한도 초과는 불일치다. format_selector는 항상 :text:<k>를 붙이므로 TEXT_BLOCK_AMBIGUOUS는 도달하지 않으며, 나오면 불일치다. scan은 profile kinds의 항목만 후보로 모으므로 SELECTOR_KIND_MISMATCH도 불일치다. parse_selector의 ARGUMENT_INVALID는 format_selector가 문법을 검증한 뒤이므로 도달할 수 없으며, 나오면 출력 문서의 ARGUMENT_INVALID(인자 해석 실패)와 섞이지 않도록 문서를 만들지 않는다.

### N5 위치·selector·내용의 대응

- 위치(line, block_index, text_index)는 scan이 기록한다. selector는 (kind, ident, text_index)로 만든다.
- 위치 유일성의 근거는 기존 run 경로다: _find는 prefix 전체에서 selector의 ident와 일치하는 entry(assistant) 또는 tool_result block이 정확히 1개일 때만 대상을 돌려주고, 2개 이상이면 ENTRY_DUPLICATE다. 대상 안에서 text_index번째 텍스트를 고른다. 후보끼리 selector가 같으면 run 경로로 구분할 수 없으므로 SELECTOR_DUPLICATE로 고정하고 select_text를 부르지 않는다.
- digest 일치는 run 경로가 고른 텍스트와 후보 텍스트의 내용 일치 증거일 뿐 위치 동일성의 증거가 아니다. 위치 동일성은 위의 selector 비중복과 _find의 유일성 검사로만 뒷받침한다.
- 내용이 같은 서로 다른 위치의 후보(ident가 다름)는 selector가 다르며 각각 OK일 수 있고 values가 같다. 이를 digest로 구분했다고 주장하지 않으며, 같은 values가 정본 확정을 뜻하지 않는다.
- values는 그 후보의 selector로 기존 run 경로(select_text 성공)를 통과하고, 반환 텍스트의 digest가 후보 digest와 같고, extract가 성공했을 때만 그 후보에 연결한다. 그 밖에는 null이다.
- 출력에는 선택 추천, 최신·첫 후보 표시, 정본 표시 필드가 없다.

### N6 출력 candidates/1

직렬화: store.canonical_bytes(키 정렬, 구분자 "," ":", ASCII, JSON 하나 + LF). 정의된 결과(정상·정의된 오류 문서)에서는 stdout에 이 한 문서만 쓰고 stderr에는 쓰지 않는다. 예외 메시지·경로는 문서에 넣지 않는다. 정의되지 않은 내부 예외(문서 검증 ValueError, 내부 불변식 위반 등)는 문서 없이 전파되며 Python이 stderr에 traceback을 남길 수 있다. 이 traceback이나 예외 텍스트는 안전한 결과로 재게시하지 않는다.

CANDIDATES_KEYS(정확히): approval, authority, boundary, candidate_count, candidate_count_at_least, candidates, checks, command, error, exit_code, profile, schema, status, target, task_id

공통 고정값: schema = "moneylab.controlled_read.candidates/1", command = "candidates", authority = "NONE", approval = "NOT_VERIFIED_BY_PROGRAM", boundary = "DATA_NOT_INSTRUCTIONS".

status와 error.detail:

| status | detail |
|---|---|
| CANDIDATES_LISTED | (error = null) |
| CANDIDATES_LIMIT_EXCEEDED | the scan stopped because the fixed prefix holds more candidates than the candidate limit |
| DIAGNOSE_PREFIX_MISMATCH | the bytes at the expected prefix do not have the expected sha256 |
| DIAGNOSE_PREFIX_NOT_LINE_ALIGNED | the expected prefix does not end with LF |
| ARGUMENT_INVALID (인자 해석 실패만) | the arguments do not match the fixed grammar |
| ENVIRONMENT_INVALID | the package root, the git top level or the home directory is not valid |
| SESSION_NOT_FOUND | the session file or one of its parent directories does not exist |
| SESSION_PATH_INVALID | the session path has a link, a reparse point, a non-directory parent or changed |
| SESSION_TRUNCATED | the session file became shorter than the prefix |
| SESSION_UNREADABLE | the session file could not be read |
| SESSION_CHANGED | the prefix bytes changed while the session was processed |
| SESSION_CORRUPT | a complete line is not strict UTF-8 JSON holding an object |
| LINE_LIMIT_EXCEEDED | a line is longer than the line limit |
| ENTRY_LIMIT_EXCEEDED | the prefix has more entries than the entry limit |
| TIME_LIMIT_EXCEEDED | processing took longer than the time limit |
| FORMAT_UNSUPPORTED | an entry or block does not have the supported structure |
| SELECTOR_KIND_MISMATCH | the selected entry or the profile does not fit the selector kind |
| TEXT_BLOCK_AMBIGUOUS | more than one text block exists and none was selected |

- 위 표 밖의 status는 문서 검증에서 ValueError다(STORE_PATH_INVALID, STORE_FAILED, ATTEMPT_EXISTS, CANDIDATE_LOCAL_CODES 포함).
- status ARGUMENT_INVALID는 모든 식별 필드가 null인 형태(아래)로만 허용한다. checks·target이 null이 아닌 ARGUMENT_INVALID 문서는 ValueError다.
- CANDIDATES_DETAILS의 키는 DETAILS, store.PRECHECK_DETAILS, DIAGNOSE_DETAILS와 겹치지 않는다.
- exit_code: CANDIDATES_LISTED만 0, 그 밖은 2. error: CANDIDATES_LISTED만 null, 그 밖은 {"code": status, "detail": 위 문구}.
- CANDIDATES_LISTED는 처리가 완료됐다는 뜻이다. 후보 0개면 candidate_count 0, candidates [], exit_code 0이며 후보 발견이나 추출 성공을 뜻하지 않는다. 후보가 있어도 OK인 후보가 있다는 뜻이 아니다.

null·값 조건:
- ARGUMENT_INVALID: task_id, target, profile, checks, candidate_count, candidate_count_at_least, candidates가 모두 null.
- 그 밖: task_id = 입력값(문법 검증됨), profile = {"id": 입력값, "version": PROFILES[입력값].version}.
- target: ARGUMENT_INVALID에서 null. 그 밖에는 키 정확히 {project_key, session_id, expected_prefix_bytes, expected_prefix_sha256, observed_size_at_open, trailing_bytes_excluded, line_count, prefix_check}이고 규칙은 diagnose D7과 같다.
  - 앞의 네 값은 입력과 같다.
  - observed_size_at_open: null 또는 0 이상 정수(bool 아님). null은 크기를 얻기 전 실패.
  - trailing_bytes_excluded, line_count: prefix 확정 전 null. 확정 뒤 trailing = observed − N(0 이상), line_count = prefix의 LF 수(1 이상 N 이하).
  - prefix_check: null, MATCHED, TRUNCATED, CHANGED, INCOMPLETE. LISTED·LIMIT_EXCEEDED이면 MATCHED.
- checks: ARGUMENT_INVALID에서 null. 그 밖에는 키 정확히 {prefix, scan, selected}.
  - prefix·selected ∈ {NOT_REACHED, PASSED, FAILED}, scan ∈ {NOT_REACHED, PASSED, FAILED, LIMIT_STOPPED}
  - 허용 조합과 status:

| prefix | scan | selected | status |
|---|---|---|---|
| NOT_REACHED | NOT_REACHED | NOT_REACHED | ENVIRONMENT_INVALID |
| FAILED | NOT_REACHED | NOT_REACHED | open_fixed_prefix 실패 코드 7종 |
| PASSED | FAILED | NOT_REACHED | scan 실패 코드, 또는 scan 실패 뒤 재해시가 대체한 코드 |
| PASSED | LIMIT_STOPPED | NOT_REACHED | CANDIDATES_LIMIT_EXCEEDED, 또는 그 뒤 재해시가 대체한 코드 |
| PASSED | PASSED | FAILED | 선택 단계 전체 실패 코드(CANDIDATES_GLOBAL_CODES 등), 또는 그 뒤 재해시가 대체한 코드 |
| PASSED | PASSED | PASSED | CANDIDATES_LISTED, 또는 그 뒤 재해시가 대체한 코드 |

- candidate_count: CANDIDATES_LISTED에서만 0 이상 8 이하 정수(bool 아님), 그 밖은 null.
- candidate_count_at_least: CANDIDATES_LIMIT_EXCEEDED에서만 정수 9, 그 밖은 null. 관측한 하한이며 정확한 전체 수가 아니다.
- candidates: CANDIDATES_LISTED에서만 길이 = candidate_count인 배열, 그 밖은 null. 부분 목록은 출력하지 않는다.

CANDIDATE_ITEM_KEYS(정확히): block_index, index, is_error, kind, line, selected, selector, text_index, values
- index: 1부터 연속하는 정수(prefix 순서).
- line: 1 이상 target.line_count 이하 정수. index가 커질수록 line은 줄지 않는다.
- kind: "assistant" 또는 "tool_result"이며 profile.kinds에 속한다.
- block_index: tool_result는 1 이상 8388608 이하 정수, assistant는 null.
- text_index: 1 이상 8388608 이하 정수.
- is_error: bool. assistant는 false.
- selector: selected가 SELECTOR_UNREPRESENTABLE이면 null, 그 밖은 문자열. 문자열이면 selector.SELECTOR에 fullmatch하고, parse_selector 결과의 kind가 항목 kind와 같고, text_index(k)가 항목 text_index와 같다. assistant이면 ident는 소문자 UUID 문법이다.
- selected ∈ CANDIDATE_STATES = {OK, SELECTOR_UNREPRESENTABLE, SELECTOR_DUPLICATE, SELECTION_MISMATCH} ∪ CANDIDATE_LOCAL_CODES.
- SELECTOR_DUPLICATE인 항목은 같은 selector 문자열을 가진 다른 항목이 적어도 하나 있다. 그 밖의 상태에서 selector 문자열은 문서 안에서 유일하다.
- values: selected = OK일 때만 키 정확히 {bytes, lf, sha256}. bytes 1 이상 1048576 이하 정수, lf 1 이상 bytes 이하 정수, sha256 소문자 hex 64자. 그 밖은 null.
- 정수 검사는 type(x) is int로 하며 bool을 정수로 받지 않는다. bool 검사는 type(x) is bool.

출력하지 않는 것: 본문, 주변 문맥, 표식 줄, 키 이름, type 이름, 표현 불가 ident, digest, 예외 메시지, 경로. 입력 문자열은 task_id·project_key·session_id·profile.id·expected_prefix_sha256의 문법 검증된 반향뿐이다.

### N7 CLI·guard·문서

- 정확한 CLI(Bash 독립 호출, ASCII 공백 1개):
  .venv/Scripts/python.exe -B -m moneylab.controlled_read candidates --task <TASK_ID> --project-key <PROJECT_KEY> --session <SESSION> --profile <PROFILE> --expect-prefix-bytes <N> --expect-prefix-sha256 <SHA>
- .claude/hooks/guard.py:
  - CONTROLLED_READ_DIAGNOSE_FORM 정의 바로 다음 줄에 CONTROLLED_READ_CANDIDATES_FORM 하나를 추가한다. 그 정규식 원문은 CONTROLLED_READ_DIAGNOSE_FORM의 원문에서 문자열 "diagnose --task "를 "candidates --task "로 바꾼 것과 같다(profile 대안 /1, PREREG/1, WO/2 포함, re.ASCII).
  - _controlled_read의 diagnose 분기 바로 뒤, 같은 if bash 블록 안에 분기 하나를 추가한다: m이 있고 len(m.group("task")) ≤ 64이고 int(m.group("bytes")) ≤ 67108864이면 Decision(ASK, "controlled-read", "controlled read candidates; confirm the CONTROLLED_READ_CANDIDATES_AUTHORIZATION message first").
  - 그 밖의 상수·순서·reason·마지막 DENY·_CR_MODULE·INLINE_CODE 조건은 바꾸지 않는다. 기존 DENY를 약화하지 않는다.
- docs/agent_workflow.md 제한 읽기 CLI 절:
  - "아래 네 형태"를 "아래 다섯 형태"로 바꾸고 위 CLI 형태와 (AUTO-15-CONTROLLED-READ-CANDIDATES) 표기를 diagnose 형태 다음에 추가한다.
  - diagnose bullet 뒤, ECON-FWD-M20-WO/2 bullet 앞에 candidates bullet을 추가한다. 내용: 기록 없음, status 대상 아님, 고정 prefix 검증, 상한 8과 하한 표기, 출력 범위(위치·selector·선택 판정·해시·길이), 의미 한계(표식이 있음이나 OK는 유효한 지시문이라는 판단이 아님, 자동 선택 없음, values가 같아도 정본 확정 아님, 유일성은 지원되는 개별 text 문자열 범위로 한정, 후보 0개의 LISTED는 발견·성공이 아님), 승인 문구와 대조 규칙.
  - 승인 문구: CONTROLLED_READ_CANDIDATES_AUTHORIZATION: AUTO-15-CONTROLLED-READ-CANDIDATES TASK=<TASK_ID> PROJECT_KEY=<PROJECT_KEY> SESSION=<SESSION> PROFILE=<PROFILE> EXPECT_PREFIX_BYTES=<N> EXPECT_PREFIX_SHA256=<SHA> EXPIRES_UTC=<YYYY-MM-DDTHH:MM:SSZ> (원문 존재, 필드 6개와 인자의 문자열 완전 일치, 만료 확인. 다른 controlled_read 승인을 대신하지 않음)
  - 다른 절은 바꾸지 않는다.

## ALLOWED_FILES (7개: M 5개, A 2개, 이 순서가 AUDIT_SET 순서)

1. M src/moneylab/controlled_read/transcript.py (N2만)
2. M src/moneylab/controlled_read/diagnose.py (N3–N6 추가만, 기존 정의의 줄 변경 0)
3. M src/moneylab/controlled_read/__main__.py (N3의 _candidates와 run() 분기만)
4. M .claude/hooks/guard.py (N7만)
5. M docs/agent_workflow.md (N7만)
6. A tests/test_controlled_read_candidates.py
7. A tests/test_controlled_read_candidates_guard.py

## PROTECTED_FILES

- CANONICAL_BASE_SHA에 있는 tests/** 전체. 기존 시험 변경 예외 0건(위생 시험 포함, 예외 추가 없음).
- src/** 중 ALLOWED 3개를 뺀 전부, .claude/** 중 hooks/guard.py를 뺀 전부, .github/**, CLAUDE.md, pyproject.toml, requirements*.txt, .gitignore, 사전등록 파일, docs/tasks/**(예외: WS-B3의 WORK_ORDER.md 최초 생성 1회).
- 판정: git diff --name-status <base>에서 PROTECTED 경로의 M·D·R이 0건, A는 ALLOWED의 A 2개와 WORK_ORDER.md뿐.

## TEST_GATES (합성 tmp_path만, 실제 home·세션 접근 없음, skip·xfail 없음)

비ASCII 합성 입력은 Python의 N-이름 이스케이프(역슬래시 + N{문자 이름}) 또는 U-8자리 이스케이프로만 쓴다. 역슬래시 + u4자리 형태는 쓰지 않는다(AUTO-12 교훈: 도구 인자 해석으로 실제 문자가 될 수 있음).

tests/test_controlled_read_candidates.py
- C1 보존: precheck/1·diagnose/1·run의 대표 경로 결과가 기존과 같다. scan_candidates를 새 인자 없이 부르면 반환 리스트가 Candidate 4필드로 같다. precheck·diagnose 경로 호출에 positions·limit 키워드가 넘어가지 않는다(spy, 키워드 부재 확인).
- C2 열거: 후보 0개 → LISTED, count 0, [], exit_code 0, selected PASSED. 후보 1개·2개 → 순서, line, block_index, text_index, kind, is_error가 맞다. assistant와 tool_result 혼합. /2에서 표식 없는 비텍스트 항목을 건너뛴 뒤의 text_index가 run 경로의 :text:<k>와 같다.
- C3 상한(관측 방법을 결합):
  - CLI: 후보 8개 → LISTED, 8항목. 후보 9개 이상 → LIMIT_EXCEEDED, at_least 9, count null, candidates null, scan LIMIT_STOPPED, selected NOT_REACHED. 재해시 seam이 LIMIT 뒤에도 1회 호출된다.
  - 직접 호출(limit=8, 외부 positions 리스트 전달): CandidateLimitReached가 나고, 예외 뒤 외부 positions 길이가 8이다.
  - 스캔 중단: 9번째 후보 줄 뒤에 둔 손상 줄이 SESSION_CORRUPT로 보고되지 않는다(CLI와 직접 호출 모두).
  - found(함수 지역 변수)는 예외 시 반환되지 않으므로 시험에서 관측하지 않는다. 후보 목록이 8개를 넘게 적재되지 않는다는 근거는 positions 길이 8, 9번째 이후 스캔 미진행, PRECOMMIT_AUDIT CODE_READ(limit 검사가 Candidate·positions 적재보다 앞섬)의 결합이다. 시험용 상태 노출 API는 쓰지 않는다.
- C4 위치·selector·내용:
  - 같은 block의 text:1과 text:2 → 서로 다른 selector, 둘 다 OK.
  - 같은 내용의 서로 다른 위치(uuid가 다른 두 assistant entry에 같은 후보 텍스트) → 둘 다 OK, selector·line이 다르고 values가 같다. 문서에 선택·정본 필드가 없다.
  - selector 중복: 같은 uuid U를 가진 두 assistant entry(서로 다른 줄)에 각각 첫 text block으로 후보 텍스트가 있음(둘 다 k = 1) → 두 selector가 assistant:U:text:1로 같으므로 둘 다 SELECTOR_DUPLICATE, select_text 호출 0회(spy).
  - 중복 ident(selector는 다름): 서로 다른 user entry에 tool_use_id가 같은 두 tool_result block을 둔다. block A의 content = [후보 텍스트 X](X는 k = 1), block B의 content = [표식 없는 text 항목, 후보 텍스트 Y](Y는 k = 2). 두 selector는 tool_result:<id>:text:1과 tool_result:<id>:text:2로 다르며 SELECTOR_DUPLICATE가 아니다. select_text의 _find가 같은 tool_use_id block 2개를 찾으므로 두 후보 모두 ENTRY_DUPLICATE, values null.
  - 후보 ident가 후보 아닌 block과 겹침: 후보 block과 tool_use_id가 같은 표식 없는 tool_result block을 다른 줄에 둔다 → 그 후보 ENTRY_DUPLICATE, 같은 문서의 다른 후보는 OK.
  - 서로 다른 내용의 선택 불일치: select_text seam이 다른 텍스트를 돌려주면 SELECTION_MISMATCH, values null.
  - 표현 불가: k ≥ 100, assistant uuid 없음, tool_use_id 문법 밖 → SELECTOR_UNREPRESENTABLE, selector null, 해당 ident 문자열이 stdout에 없다.
- C5 후보 단위 거부: MARKER_MISSING(BEGIN만), MARKER_DUPLICATE, MARKER_ORDER_INVALID, BODY_EMPTY, TOOL_RESULT_ERROR(is_error true)가 각각 그 후보의 selected이고, 같은 문서의 다른 후보 OK와 values가 함께 나온다. extract 단계 로컬 코드(TEXT_LIMIT_EXCEEDED·BODY_LIMIT_EXCEEDED는 monkeypatch로 한도 축소)도 포함한다.
- C6 전체 실패와 폐기: scan 중 TIME_LIMIT_EXCEEDED(INCOMPLETE, 재해시 없음), 선택 중 TIME_LIMIT_EXCEEDED(INCOMPLETE, 재해시 없음, selected FAILED), 재해시 SESSION_CHANGED·SESSION_TRUNCATED·SESSION_UNREADABLE·TIME_LIMIT_EXCEEDED, DIAGNOSE_PREFIX_MISMATCH, DIAGNOSE_PREFIX_NOT_LINE_ALIGNED, scan FORMAT_UNSUPPORTED, 선택 단계 seam의 FORMAT_UNSUPPORTED·SELECTOR_KIND_MISMATCH·TEXT_BLOCK_AMBIGUOUS·SESSION_CORRUPT → 모두 정의된 문서이며 candidates·candidate_count·candidate_count_at_least null, 앞서 구한 OK 후보의 values도 출력에 없다.
- C6b 내부 불변식 위반: 선택 단계 seam(parse_selector 또는 select_text)이 ARGUMENT_INVALID를 내면 cli.main이 ControlledReadError가 아닌 예외로 끝나고(pytest.raises), stdout이 빈 바이트이며, 연 handle이 닫힌다. 인자 해석 단계의 ARGUMENT_INVALID 문서(C7 형태)와 구분된다.
- C7 문서 검증(check_candidates_document): 키 추가·누락, 표 밖 status, detail 불일치, checks 조합 위반, null 조건 위반(식별 필드가 null이 아닌 ARGUMENT_INVALID 포함), bool을 정수 자리에 넣음, 정수를 bool 자리에 넣음, selector 문법 밖, selector kind·k와 항목 불일치, index 불연속, line 감소, OK가 아닌데 values 있음, OK인데 values 없음, SELECTOR_DUPLICATE인데 짝 없음, 비중복 상태의 selector 중복, profile id·version 불일치, task_id 문법 밖 → 각각 ValueError. 인자 해석 실패의 ARGUMENT_INVALID 문서(모든 식별 필드 null)는 통과한다.
- C8 누출·기록: 정의된 결과에서 stdout은 canonical JSON 하나, stderr는 빈 바이트, LEAK 표식(본문, 키 이름, type 이름, 표현 불가 ident, 비ASCII 합성 값)이 stdout에 없다. store.prepare_attempt·create_record를 호출하면 실패하는 seam과 tmp_path·저장소 기록 경로 목록 불변.
- C9 profile·정책: /1, PREREG/1, /2 각각 LISTED 경로. /2에서 실제 CLI 경로의 NontextPolicy 생성이 scan 1개 + select_text 호출 수만큼이며 객체가 모두 다르다. /1·PREREG/1에서는 nontext 키워드가 넘어가지 않는다.
- C10 상수: CANDIDATES_DETAILS 키가 DETAILS·PRECHECK_DETAILS·DIAGNOSE_DETAILS와 서로소, CANDIDATES_SCHEMA, CANDIDATES_OPTIONS, CANDIDATE_LIMIT = 8, CANDIDATE_LOCAL_CODES·CANDIDATES_GLOBAL_CODES가 서로소이고 각각 N4 목록과 같으며 ARGUMENT_INVALID는 어느 쪽에도 없다.
- C11 handle: 모든 경로(내부 불변식 위반 포함)에서 연 handle이 닫힌다.

tests/test_controlled_read_candidates_guard.py
- C12 guard 판정: 정확한 형태(세 profile, N = 1·67108864, task 64자) → ASK, rule controlled-read, reason 고정 문구. DENY(controlled-read-form): 옵션 순서 변경, 누락, 중복, 추가 토큰, 따옴표, 탭, = 형태, N = 0·67108865·012, 대문자 SHA, 63·65자 SHA, 다른 실행 파일 경로, -mmoneylab, -Bm, .__main__, 끝 공백, 대문자 CANDIDATES, PowerShell 도구. 기존 run·status·precheck·diagnose 형태의 판정과 reason은 그대로.
- C13 hook 프로세스: ASK는 exit 0과 JSON(permissionDecision ask, reason 고정 문구), DENY는 exit 2와 stderr의 controlled-read-form, stdout 빈 바이트.

재귀 부재·적재 순서의 근거는 C3과 PRECOMMIT_AUDIT CODE_READ를 함께 쓴다. Grep 0건만으로 입증하지 않는다.

## FILE_FORMAT

- A 2개(파일 전체): UTF-8 strict, BOM 없음, CR 없음, 탭·U+00A0·U+FEFF 없음, 줄 끝 공백 없음, 파일 끝 LF 정확히 1개, 비ASCII 바이트 0개.
- M 5개: 추가·변경 줄은 UTF-8 strict, 탭·U+00A0·U+FEFF·CR 없음, 줄 끝 공백 없음. 파일 전체는 BOM 없음, CRLF를 LF로 바꾼 뒤 남는 CR 0, 끝 LF.
- 비ASCII 바이트 검사는 Grep 도구(내용 모드, 패턴 [^ -~])로 A 2개에 한다. 기대 0건. 이 패턴은 탭도 잡으며 탭도 금지 대상이다.

## INLINE_CHECKS (읽기 전용 확인문, 고정 원문, 파일로 저장하지 않음)

공통:
- Bash 독립 호출 1회. 셸 명령의 <SOURCE> 자리에 아래 Python 소스 블록 내용을 글자 그대로(첫 줄부터 마지막 줄까지, 앞뒤 공백 줄 없이) 넣는다. 소스에는 작은따옴표와 역슬래시가 없다.
- <PY>: WS-A에서는 C:/MoneyLab-auto-12/.venv/Scripts/python.exe, WS-B부터는 C:/MoneyLab-auto-15/.venv/Scripts/python.exe.
- 이 확인문은 읽기 전용이다. 디렉터리 생성은 MKD 절의 mkdir로만 한다.
- 발행 전 검증 범위: 이 소스들은 AUTO-12 계약의 고정 원문과 같으며, 발행 단계에서는 구문 분석까지만 확인한다(실행·import·함수 호출 없음).

### PS (경로 상태)

셸 명령:

<PY> -I -B -c '<SOURCE>' <경로1> [<경로2> …]

Python 소스:

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

- 출력: 인자마다 "<경로> PATH_STATE=<ABSENT|DIRECTORY|FILE|LINK|REPARSE|OTHER>". lstat 오류는 "<경로> PATH_STATE=QUERY_ERROR <예외 이름>"과 종료 코드 2.
- 허용 인자(슬래시 절대 경로, 이 목록만):
  - C:/MoneyLab-auto-15
  - C:/MoneyLab-auto-15/.venv (WS-A3 한정)
  - C:/MoneyLab-auto-15/docs/tasks/AUTO-15-CONTROLLED-READ-CANDIDATES
  - C:/MoneyLab-auto-15/docs/tasks/AUTO-15-CONTROLLED-READ-CANDIDATES/WORK_ORDER.md
  - C:/MoneyLab-auto-15/data, C:/MoneyLab-auto-15/data/processed, C:/MoneyLab-auto-15/data/processed/auto15, C:/MoneyLab-auto-15/data/processed/auto15/preserve
  - RECORDS의 각 기록 파일(C:/MoneyLab-auto-15/ 접두 절대 경로)
- 판정: 기대 ABSENT는 ABSENT, 기대 DIRECTORY는 DIRECTORY. LINK, REPARSE, OTHER, 기대와 다른 FILE·DIRECTORY, QUERY_ERROR, 종료 코드 2, 예외 출력은 STOP. 재시도하거나 다른 방법으로 확인하지 않는다.

### MKD

- 생성 허용 경로(이 순서): C:/MoneyLab-auto-15/data -> C:/MoneyLab-auto-15/data/processed -> C:/MoneyLab-auto-15/data/processed/auto15 -> C:/MoneyLab-auto-15/data/processed/auto15/preserve
- 각 경로: PS가 DIRECTORY면 그대로 쓴다. ABSENT면 독립 호출 mkdir <경로>(-p 없음) 1회 뒤 PS로 DIRECTORY 확인. 그 밖은 STOP.

### FMT (형식, 모드 new, changed, added)

셸 명령:

<PY> -I -B -c '<SOURCE>' <new|changed|added> <파일1> [<파일2> …]

Python 소스:

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

- 판정: RESULT=PASS이고 표시된 종료 코드가 없거나 0이면 통과. RESULT=FAIL·종료 코드 3은 위반 → STOP(자동 수정 없음). 종료 코드 1·2, traceback, RESULT 누락, USAGE_ERROR는 STOP. added에서 HUNKS=0이면 FAIL.
- 허용 인자(SESSION_ROOT 기준 상대 경로): new = A 2개, changed = M 5개, added = data/processed/auto15/added.diff.
- FMT는 ASCII 여부를 검사하지 않는다. ASCII는 FILE_FORMAT의 Grep으로 따로 확인한다.

## AUDIT_METHOD

- W(원바이트): sha256sum <path>. 작업 파일 그대로의 바이트.
- O(Git blob OID): git -C C:/MoneyLab-auto-15 hash-object -- <path>(-w 금지). index는 git -C C:/MoneyLab-auto-15 rev-parse :<path>, 커밋은 git -C C:/MoneyLab-auto-15 rev-parse HEAD:<path>와 대조한다. W와 O는 서로 대조하지 않는다.
- AUDIT_SET: PRECOMMIT_AUDIT에서 확정한 7개의 (경로, W, O). COMMIT·CLEAN_COMMIT_E2E는 O로, 작업 파일 불변은 W로 대조한다.
- 모든 Bash 호출은 독립 명령 하나다. 체인·파이프·리디렉션은 금지이며 예외는 RECORDS 원문뿐이다.
- 큰 출력과 백그라운드 결과는 OBSERVATION_LIMITS의 Read 절차를 따른다.

## RECORDS (TARGET_WORKTREE 아래 ignored, create-new)

- ignore 확인: git -C C:/MoneyLab-auto-15 check-ignore -v -- data/processed/auto15/x -> 한 줄, source .gitignore, pattern이 !로 시작하지 않음. 아니면 STOP.
- 각 파일은 쓰기 직전 PS로 ABSENT를 확인한다. 아래 원문만 허용한다. R1–R5는 작업 위치 C:/MoneyLab-auto-15에서, P1·P2는 WS-A4에서 절대 경로로 실행한다.
  - R1: set -C && .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q > data/processed/auto15/collect_base.txt
  - R2: set -C && .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q > data/processed/auto15/collect_precommit.txt
  - R3: set -C && git diff --no-index -U0 -- data/processed/auto15/collect_base.txt data/processed/auto15/collect_precommit.txt > data/processed/auto15/collect_diff.txt
  - R4: set -C && git diff --stat 2005e301e1de80150db4c7dcefd4a6e2b5d0b451 > data/processed/auto15/diff_stat.txt
  - R5: set -C && git diff -U0 --no-color --no-ext-diff --no-renames 2005e301e1de80150db4c7dcefd4a6e2b5d0b451 -- src/moneylab/controlled_read/transcript.py src/moneylab/controlled_read/diagnose.py src/moneylab/controlled_read/__main__.py .claude/hooks/guard.py docs/agent_workflow.md > data/processed/auto15/added.diff
  - P1: set -C && git -C C:/MoneyLab-auto-15 worktree list --porcelain > C:/MoneyLab-auto-15/data/processed/auto15/preserve/worktrees_s1.txt
  - P2: set -C && git -C C:/MoneyLab-auto-15 for-each-ref "--format=%(objectname) %(refname) %(symref)" refs/heads refs/remotes refs/tags > C:/MoneyLab-auto-15/data/processed/auto15/preserve/refs_s1.txt
  - P3: set -C && git -C C:/MoneyLab-auto-15 worktree list --porcelain > data/processed/auto15/preserve/worktrees_s2.txt
  - P4: set -C && git -C C:/MoneyLab-auto-15 for-each-ref "--format=%(objectname) %(refname) %(symref)" refs/heads refs/remotes refs/tags > data/processed/auto15/preserve/refs_s2.txt
  - P5: set -C && git -C C:/MoneyLab-auto-15 worktree list --porcelain > data/processed/auto15/preserve/worktrees_s3.txt
  - P6: set -C && git -C C:/MoneyLab-auto-15 for-each-ref "--format=%(objectname) %(refname) %(symref)" refs/heads refs/remotes refs/tags > data/processed/auto15/preserve/refs_s3.txt
- 기록 내용 전체는 채팅에 내지 않는다(sha256, 줄 수, 판정만).
- 기존 기록은 덮어쓰기·삭제·재생성하지 않는다. 위 목록 밖의 기록·로그 파일은 만들지 않는다.
- 감사 후 수정에 따른 기록 재사용 규칙(REUSE):
  - IMPLEMENTATION 후퇴로 ALLOWED 파일이 바뀐 뒤 PRECOMMIT_AUDIT를 다시 할 때, 기존 R2–R5는 다시 만들 수 없다(create-new).
  - 재사용 조건: 각 기록의 sha256이 생성 때와 같다; 바뀐 파일·줄이 보고된다; 그 변경이 R2·R3에서는 시험 정의·매개변수·수집 구조를, R4·R5에서는 M 5개를 바꾸지 않는다는 근거(예: M 파일 O 불변, 바뀐 파일이 A뿐이고 ID에 영향 없음)가 보고된다; 관리자의 명시적 수락이 있다.
  - 조건을 하나라도 충족하지 못하면 해당 감사 항목은 STOP하고 ERRATA(새 기록 이름 허용)를 기다린다.

## PRESERVE_RULES

- 직접 확인(WS-A1, WS-A4, PUSH, POST_MERGE_AUDIT): PRESERVED_WORKTREES 네 곳 각각 독립 호출 git -C <wt> rev-parse HEAD HEAD^{tree}와 git -C <wt> status --porcelain=v1 --untracked-files=all. HEAD·tree가 Metadata와 같고 status가 빈 출력.
- 기준 s1: WS-A4에서 새 worktree를 만든 뒤 기록한 P1·P2.
- 비교(독립 호출, 출력 원문 판정):
  - s2: git -C C:/MoneyLab-auto-15 diff --no-index -- data/processed/auto15/preserve/worktrees_s1.txt data/processed/auto15/preserve/worktrees_s2.txt
  - s2: git -C C:/MoneyLab-auto-15 diff --no-index -- data/processed/auto15/preserve/refs_s1.txt data/processed/auto15/preserve/refs_s2.txt
  - s3: 같은 형태로 s1과 s3 비교 2회
- s2(PUSH 뒤) 허용 차이(이것뿐):
  - worktree 목록: worktree C:/MoneyLab-auto-15 블록의 "HEAD <base>"가 "HEAD <I>"로 바뀜
  - refs: refs/heads/codex/auto-15-controlled-read-candidates 줄의 objectname이 base에서 I로 바뀜
  - refs: "<I> refs/remotes/origin/codex/auto-15-controlled-read-candidates " 한 줄 추가
- s3(fetch 뒤) 허용 차이: s2의 차이 전부와 다음뿐
  - refs/remotes/origin/main 줄의 objectname이 base에서 M으로 바뀜
  - refs/remotes/origin/HEAD 줄: s1에 있었다면 symref 열 refs/remotes/origin/main은 그대로이고 objectname만 base에서 M으로 바뀜. s1에 없었다면 s3에도 없어야 함
- 그 밖의 worktree·ref 추가·삭제·변경은 STOP. git diff 출력의 줄바꿈 변환 경고(LF→CRLF)는 판정에 쓰지 않고 보고만 한다.

## COLLECT_RULES

- WS-B7(R1 뒤): Grep 도구(개수 모드)로 R1의 ID 줄 수(:: 포함 줄)를 세고, Grep 도구(내용 모드)로 요약 줄(collected 포함 줄)을 읽어 selected·total·deselected를 기록한다. ID 줄 수 = selected, total = selected + deselected. 어긋나면 STOP.
- PRECOMMIT(R2·R3 뒤), 모두 만족해야 통과:
  - R2에서도 ID 줄 수 = selected, total = selected + deselected
  - R3에서 -로 시작하는 ID 줄(:: 포함)은 0개(기존 ID 제거·변경 없음)
  - R3에서 +로 시작하는 ID 줄은 모두 tests/test_controlled_read_candidates.py:: 또는 tests/test_controlled_read_candidates_guard.py::로 시작한다
  - precommit selected = base selected + |추가 ID|, deselected는 base와 같다. 요약 줄의 실행 시간 변화는 ID 변화로 세지 않는다
  - 추가 ID 안에 중복이 없다
- 위반은 STOP하며 허용 범위를 넓혀 해석하지 않는다.

## WS_A (PART=WORKTREE, SETUP_SESSION_ROOT 세션, 모두 독립 호출)

- WS-A1:
  - pwd -W -> C:/MoneyLab-auto-12
  - git -C C:/MoneyLab-auto-12 rev-parse HEAD -> SETUP_EXECUTION_HEAD
  - git -C C:/MoneyLab-auto-12 status --porcelain=v1 --untracked-files=all -> 빈 출력
  - N1 git -C C:/MoneyLab-auto-12 ls-remote origin refs/heads/main -> 2005e301e1de80150db4c7dcefd4a6e2b5d0b451 와 refs/heads/main
  - N2 git -C C:/MoneyLab-auto-12 ls-remote origin refs/heads/codex/auto-15-controlled-read-candidates -> 빈 출력
  - git -C C:/MoneyLab-auto-12 cat-file -t 2005e301e1de80150db4c7dcefd4a6e2b5d0b451 -> commit
  - git -C C:/MoneyLab-auto-12 rev-parse 2005e301e1de80150db4c7dcefd4a6e2b5d0b451^{tree} -> CANONICAL_BASE_TREE
  - git -C C:/MoneyLab-auto-12 show-ref --verify --quiet refs/heads/codex/auto-15-controlled-read-candidates -> 표시된 Exit code 1
  - PS C:/MoneyLab-auto-15 -> ABSENT
  - PRESERVE 직접 확인(네 곳)
- WS-A2: git -C C:/MoneyLab-auto-12 worktree add -b codex/auto-15-controlled-read-candidates C:/MoneyLab-auto-15 2005e301e1de80150db4c7dcefd4a6e2b5d0b451 (1회)
  - 확인: git -C C:/MoneyLab-auto-15 rev-parse HEAD HEAD^{tree} -> base, CANONICAL_BASE_TREE. status 빈 출력. PS C:/MoneyLab-auto-15/docs/tasks/AUTO-15-CONTROLLED-READ-CANDIDATES -> ABSENT
- WS-A3:
  - git -C C:/MoneyLab-auto-15 check-ignore -v -- .venv/x -> source .gitignore, pattern이 !로 시작하지 않는 한 줄
  - PS C:/MoneyLab-auto-15/.venv -> ABSENT
  - C:/MoneyLab-auto-12/.venv/Scripts/python.exe -m venv C:/MoneyLab-auto-15/.venv (1회)
  - C:/MoneyLab-auto-15/.venv/Scripts/python.exe --version -> Python 3.14.8
- WS-A4:
  - git -C C:/MoneyLab-auto-15 check-ignore -v -- data/processed/auto15/x -> 통과
  - MKD(PS의 <PY>는 WS-A 값)
  - P1, P2 생성(각 쓰기 직전 PS ABSENT) 후 각 sha256sum과 줄 수 보고
  - PRESERVE 직접 확인(네 곳)
- 보고 후 멈춘다. 사용자가 C:/MoneyLab-auto-15에서 새 세션을 시작한다.

## WS_B (PART=C1_ENV, SESSION_ROOT 새 세션, 모두 독립 호출)

- WS-B1: pwd -W -> C:/MoneyLab-auto-15. git -C C:/MoneyLab-auto-15 rev-parse HEAD HEAD^{tree} -> base, CANONICAL_BASE_TREE. branch --show-current -> TARGET_BRANCH. status·cached 빈 출력. .venv/Scripts/python.exe --version -> Python 3.14.8. RECORDS의 ignore 확인.
- WS-B2: 사용자 /status·/hooks 화면 확인(H1)은 실제로 전달받은 범위만 기록하고, 없으면 미확인. settings의 hook 선언(H2)은 Read로 확인. H4는 미확인으로 기록.
- WS-B3 (계약 파일 최초 작성):
  - sha256sum <WO_SOURCE> = WO_SHA256
  - PS C:/MoneyLab-auto-15/docs/tasks/AUTO-15-CONTROLLED-READ-CANDIDATES/WORK_ORDER.md -> ABSENT
  - Read로 WO_SOURCE를 끝까지 읽고(필요하면 offset으로 나눠) Write 1회로 docs/tasks/AUTO-15-CONTROLLED-READ-CANDIDATES/WORK_ORDER.md를 쓴다.
  - sha256sum docs/tasks/AUTO-15-CONTROLLED-READ-CANDIDATES/WORK_ORDER.md = WO_SHA256
  - 최초 작성 실패 처리(WS-B3-FAIL): 해시가 다르면 STOP한다. 작성한 파일을 다시 쓰거나 고치거나 지우지 않는다(Write 재시도 금지). 복구는 사용자가 Claude 밖(일반 셸 등)에서 WO_SOURCE를 저장소 안 대상 경로 C:/MoneyLab-auto-15/docs/tasks/AUTO-15-CONTROLLED-READ-CANDIDATES/WORK_ORDER.md로 복사해 덮어쓰는 절차다. 사용자가 재진입 승인을 주면, 재진입은 HEAD·tree·staged 0·untracked가 그 파일 하나뿐임을 확인하고 WO_SOURCE와 작업 파일의 sha256 일치를 확인한 뒤 WS-B4부터 진행한다. 이 경우 이탈로 기록한다.
- WS-B4 C1:
  - git add -- docs/tasks/AUTO-15-CONTROLLED-READ-CANDIDATES/WORK_ORDER.md
  - git diff --cached --name-status -> A와 그 경로 한 줄
  - git diff --cached --check -> 빈 출력
  - git hash-object -- <그 경로> = git rev-parse :<그 경로>
  - git commit -m "docs(task): add AUTO-15-CONTROLLED-READ-CANDIDATES work order" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" (1회)
  - 확인: git rev-list --parents -n 1 HEAD -> <C1> <base>, git rev-parse HEAD^{tree}, git show --name-status --format= HEAD -> A 1개, git rev-parse HEAD:<그 경로> = 위 OID, status 빈 출력. 승인 창은 ASK_UNVERIFIED 가능.
- WS-B5 설치(N3, N4, 각 1회):
  - .venv/Scripts/python.exe -m pip install --no-binary=mypy --no-cache-dir -r requirements-dev.txt
  - .venv/Scripts/python.exe -m pip install -e . --no-deps
- WS-B6:
  - .venv/Scripts/python.exe -m pip check -> No broken requirements found.
  - .venv/Scripts/python.exe -m mypy --version -> mypy 2.4.0 (compiled: no)
  - .venv/Scripts/python.exe -m ruff --version -> ruff 0.17.2
  - .venv/Scripts/python.exe -m pytest --version -> pytest 9.1.1
  - Read C:/MoneyLab-auto-15/.venv/Lib/site-packages/moneylab-0.3.0.dist-info/direct_url.json -> "editable": true, "url": "file:///C:/MoneyLab-auto-15"
  - 하나라도 다르면 STOP.
- WS-B7:
  - MKD 재확인(네 경로 PS DIRECTORY)
  - PS C:/MoneyLab-auto-15/data/processed/auto15/collect_base.txt -> ABSENT
  - R1 생성, sha256sum과 줄 수 보고
  - COLLECT_RULES WS-B7 항목 수행

## IMPLEMENTATION

- 쓰기: Edit·Write는 ALLOWED_FILES에만 한다. guard.py 편집 뒤 git status --porcelain=v1로 hook 오류가 없는지 확인한다. 예상 밖 DENY·hook 오류는 STOP.
- A 2개 작성 직후 Grep 도구(패턴 [^ -~])로 0건을 확인한다. 0건이 아니면 그 파일만 Edit로 고친다(FIX 1회로 집계).
- CHECK_COMMANDS(SESSION_ROOT, 각 독립 호출):
  - C1 .venv/Scripts/python.exe -m ruff check --no-cache --select E4,E7,E9,F src tests -> All checks passed!
  - C2 .venv/Scripts/python.exe -m ruff check --no-cache --select E4,E7,E9,F .claude/hooks/guard.py -> All checks passed!
  - C3a .venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache -> Success: no issues found로 시작
  - C3b .venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache src/moneylab/controlled_read -> Success: no issues found로 시작
  - C4 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/test_controlled_read_candidates.py tests/test_controlled_read_candidates_guard.py tests/test_controlled_read_nontext.py tests/test_controlled_read_nontext_guard.py tests/test_controlled_read_diagnose.py tests/test_controlled_read_diagnose_guard.py tests/test_controlled_read_precheck.py tests/test_controlled_read_cli.py tests/test_controlled_read_selector.py tests/test_controlled_read_transcript.py tests/test_controlled_read_profiles.py tests/test_controlled_read_store.py tests/test_controlled_read_isolation.py tests/test_agent_guard.py tests/test_skills.py tests/test_repo_hygiene.py
  - C5 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q (백그라운드 실행 허용, 결과는 OBSERVATION_LIMITS의 Read 절차)
- 순서: C1–C3b -> C4 -> C5. C4 통과 전에는 C5를 실행하지 않는다. C5 통과가 IMPLEMENTATION_PASS 조건이다.
- 고치는 규칙: 신규 시험·ALLOWED 안의 실패는 ALLOWED만 고친다. 기존 시험(EX 0건)의 실패는 회귀이며 즉시 STOP한다. 원인 분석은 보고만 하고, 승인 없이 소스를 고쳐 계속하지 않는다. 기대값을 구현 결과에 맞춰 완화하지 않는다.
- 예산: 수행 시간 21600초(시험 시간 포함), FIX 4회, C4 6회, C5 3회, 같은 실패 2회 연속 STOP. 수정 없이 같은 C5 실패를 반복하지 않는다.

## PRECOMMIT_AUDIT (읽기와 감사, 생성 기록은 R2–R5만)

1. 변경 집합: git -C C:/MoneyLab-auto-15 diff --name-status 2005e301e1de80150db4c7dcefd4a6e2b5d0b451와 git -C C:/MoneyLab-auto-15 ls-files --others --exclude-standard로 PROTECTED 판정. tracked는 ALLOWED M 5개와 C1의 WORK_ORDER.md(A)뿐, untracked는 ALLOWED A 2개뿐. git -C C:/MoneyLab-auto-15 diff --cached --name-status -> 빈 출력.
2. git -C C:/MoneyLab-auto-15 diff --check -> 빈 출력. PS로 R4 대상 ABSENT -> R4, sha256·줄 수 보고.
3. DIFF_SHAPE: M 5개마다 git -C C:/MoneyLab-auto-15 diff 2005e301e1de80150db4c7dcefd4a6e2b5d0b451 -- <path>를 단독 호출해 읽는다. transcript.py는 N2 범위만(서명, CandidateLimitReached, positions·limit 처리), diagnose.py는 추가 줄만(- 줄 0개), __main__.py는 _candidates와 run() 분기만, guard는 N7의 상수 1개와 분기 1개만, 문서는 N7만. 위반은 STOP.
4. CODE_READ(Read로 해당 함수 끝까지, 줄 위치와 함께 판정):
   - scan_candidates에서 limit 검사가 Candidate·positions 적재보다 앞서고, 적재 목록이 최대 8개다
   - 선택 단계에서 CANDIDATE_LOCAL_CODES만 후보 상태가 되고, 그 밖의 코드는 전체 실패로 목록·values를 폐기하며, ARGUMENT_INVALID는 문서 없는 내부 불변식 위반이다
   - 재해시 대체 시 candidates·count·at_least가 모두 null이다
   - values 연결 조건이 N5와 같다(select_text 성공, digest 일치, extract 성공)
   - 정책 객체가 scan 1회·select_text 1회마다 새로 만들어진다
   - 기록 함수 호출이 없다
   - check_candidates_document가 N6 전체 규칙을 검사하고, 출력 전에 호출된다
   - 근거는 이 읽기와 C3·C4·C6·C6b·C7·C9 결과를 함께 쓴다
5. SIGNATURE(Grep 도구와 Read로 정의를 읽고 판정):
   - 기존 위치 인자 prefix, kinds, is_candidate, deadline이 같은 순서와 같은 타입 표기로 보존됐다
   - nontext, positions, limit가 * 뒤의 keyword-only 인자다
   - 세 인자의 기본값이 None이다
   - 반환 타입 표기가 보존됐다
   - Grep 도구로 src 아래 scan_candidates 호출 지점을 찾아, __main__._precheck·_diagnose의 호출에 positions·limit가 없음을 확인한다
   - DETAILS 불변은 1번의 PROTECTED 판정(__init__.py 변경 0)으로 확인한다
6. skip·xfail: Grep 도구로 A 2개에서 pytest.mark.skip, skipif, xfail, pytest.skip(, pytest.xfail( -> 0건.
7. collect: PS로 R2 대상 ABSENT -> R2. PS로 R3 대상 ABSENT -> R3. R3를 Read(100줄씩, 최대 30회)로 열고 COLLECT_RULES PRECOMMIT 판정.
8. FMT: PS로 R5 대상 ABSENT -> R5. FMT added data/processed/auto15/added.diff, FMT changed <M 5개>, FMT new <A 2개>를 각각 독립 호출. 셋 다 RESULT=PASS.
9. SYNTHETIC_ESCAPE_AUDIT: Grep 도구(내용 모드, 패턴 [^ -~])로 A 2개 0건을 확인하고, A 2개를 Read로 끝까지 읽어 비ASCII 합성 입력이 N-이름 또는 U-8자리 이스케이프로만 쓰였는지 줄 위치와 함께 판정한다. 위반·누락·모호함은 STOP.
10. AUDIT_SET 확정: 7개 각각 sha256sum <path>와 git -C C:/MoneyLab-auto-15 hash-object -- <path>를 독립 호출하고, 경로와 전체 값으로 보고한다.
11. 감사 끝에 7개의 W를 다시 계산해 10번과 같은지 확인한다.

## COMMIT

- git -C C:/MoneyLab-auto-15 add -- <ALLOWED 7개를 ALLOWED 순서로> (1회, 줄바꿈 변환 경고는 보고만)
- git -C C:/MoneyLab-auto-15 diff --cached --name-status -> M 5, A 2, 경로가 ALLOWED와 같음
- git -C C:/MoneyLab-auto-15 rev-parse :<경로1> … :<경로7>(한 명령, ALLOWED 순서) -> AUDIT_SET의 O와 순서대로 같음
- git -C C:/MoneyLab-auto-15 diff --cached --check -> 빈 출력
- git -C C:/MoneyLab-auto-15 commit -m "feat(automation): add controlled_read candidates subcommand" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" (1회)
- 확인: rev-list --parents -n 1 HEAD -> <I> <C1>, rev-parse HEAD^{tree}, show --name-status --format= HEAD -> 7개, rev-parse HEAD:<경로1> … HEAD:<경로7> -> O, status·cached 빈 출력. 승인 창은 ASK_UNVERIFIED 가능.

## CLEAN_COMMIT_E2E

- git -C C:/MoneyLab-auto-15 rev-parse HEAD -> I, status·cached 빈 출력
- git -C C:/MoneyLab-auto-15 rev-parse HEAD:<경로1> … HEAD:<경로7> -> O
- C4 1회(구현 예산과 따로 기록. 600초 도구 한도를 넘으면 백그라운드로 이어지며, 결과는 그 호출의 결과 파일 하나를 Read로 연다)
- 실행 뒤 rev-parse HEAD HEAD^{tree}, branch --show-current, status가 그대로
- 새 checkout 재현성 검증이 아니다.

## PUSH

- N5 git -C C:/MoneyLab-auto-15 ls-remote origin refs/heads/main -> base
- N6 git -C C:/MoneyLab-auto-15 ls-remote origin refs/heads/codex/auto-15-controlled-read-candidates -> 빈 출력
- N7 git -C C:/MoneyLab-auto-15 push -u origin codex/auto-15-controlled-read-candidates (1회, force 없음. 결과가 불명확하면 재실행하지 않음)
- N8 git -C C:/MoneyLab-auto-15 ls-remote origin refs/heads/codex/auto-15-controlled-read-candidates -> I
- PS로 P3·P4 대상 ABSENT -> P3, P4 -> PRESERVE s2 판정, PRESERVE 직접 확인(네 곳)

## PR_CI

- N9 ls-remote origin refs/heads/main -> base
- N10 ls-remote origin refs/heads/codex/auto-15-controlled-read-candidates -> I
- N11 gh pr list -R swk3169/MoneyLab --head codex/auto-15-controlled-read-candidates --base main --state open --json number,headRefOid -> []
- N12 gh pr create -R swk3169/MoneyLab --base main --head codex/auto-15-controlled-read-candidates --title "<승인 제목>" --body "<승인 본문>" (1회, 임시 파일 없음, 본문 구분자 제외)
- N13 gh pr view <N> -R swk3169/MoneyLab --json number,state,isDraft,baseRefName,headRefName,headRefOid,commits,files,mergeable -> OPEN, 비초안, base main, head 일치, headRefOid I, 커밋 2개(C1, I), 파일 8개(ALLOWED 7개와 WORK_ORDER.md)
- 조회 한도: N14 gh pr checks <N> -R swk3169/MoneyLab 최대 40회, N15 gh run list -R swk3169/MoneyLab --branch codex/auto-15-controlled-read-candidates --json databaseId,headSha,name,status,conclusion 최대 10회, N16 gh run view <run> -R swk3169/MoneyLab --json jobs 최대 2회, N17 gh run view <run> -R swk3169/MoneyLab --job <linux job id> --log-failed 최대 1회(N15에서 run status completed와 headSha = I를 확인한 뒤에만)
- 같은 종류 조회 간격 60초 이상. 조회 없는 대기는 독립 sleep 60(백그라운드)만 허용하며 CI 시간에 포함한다.
- CI_STATES: pytest pass -> REQUIRED_PASS. pytest fail·cancel -> STOP. pending -> 대기. Linux fail -> Linux 판정 대상. 표가 없거나 알 수 없는 응답 -> UNPARSED(최대 5줄 보고, 사용자 재개 대기). 인증·통신·구문 오류 -> STOP.
- Linux 판정: N17 로그의 FAILURES 절 실패 ID 집합이 NONREQUIRED_CI_BASELINE의 부분집합이면 NO_NEW_LINUX_REGRESSION. 그 밖이나 로그 미확보는 STOP. Linux pass면 N17 생략. N17 출력이 큰 경우 그 호출이 알려준 결과 파일 하나만 Read로 연다.
- CI 시간: N12 직후부터 두 job 최종 상태와 Linux 판정 끝까지 3600초 이하.

## MERGE

- N18 gh pr view <N> -R swk3169/MoneyLab --json state,isDraft,baseRefName,headRefName,headRefOid,commits,files,mergeable -> OPEN, 비초안, 일치, I, 커밋 2, 파일 8, MERGEABLE
- N19 gh pr checks <N> -R swk3169/MoneyLab 1회 -> REQUIRED_PASS, PR_CI와 같은 run·job, Linux 판정 유지
- N20 ls-remote origin refs/heads/main -> base
- N21 ls-remote origin refs/heads/codex/auto-15-controlled-read-candidates -> I
- N22 gh pr merge <N> -R swk3169/MoneyLab --merge --match-head-commit <I> (1회, --admin·--auto·--squash·--rebase·--delete-branch 금지). 출력이 없거나 종료 코드가 미표시여도 재실행하지 않는다.
- N23 gh pr view <N> -R swk3169/MoneyLab --json state,mergeCommit,mergedAt -> MERGED, M

## POST_MERGE_AUDIT

- N24 git -C C:/MoneyLab-auto-15 fetch origin main (1회)
- E-1 git -C C:/MoneyLab-auto-15 rev-parse origin/main -> M
- E-2 git -C C:/MoneyLab-auto-15 rev-list --parents -n 1 <M> -> 정확히 "<M> 2005e301e1de80150db4c7dcefd4a6e2b5d0b451 <I>"
- E-3 git -C C:/MoneyLab-auto-15 merge-base 2005e301e1de80150db4c7dcefd4a6e2b5d0b451 <I> -> base
- E-4 git -C C:/MoneyLab-auto-15 rev-parse <M>^{tree} <I>^{tree} -> 두 줄이 같음
- E-5 git -C C:/MoneyLab-auto-15 diff --name-only <I> <M> -> 빈 출력
- E-6 git -C C:/MoneyLab-auto-15 merge-tree --trivial-merge 2005e301e1de80150db4c7dcefd4a6e2b5d0b451 <I> 2005e301e1de80150db4c7dcefd4a6e2b5d0b451 -> 빈 출력이고 표시된 0이 아닌 종료 코드 없음. E-2·E-3 중 하나라도 실패하면 E-6을 실행하지 않고 FAIL. --write-tree 금지.
- PS로 P5·P6 대상 ABSENT -> P5, P6 -> PRESERVE s3 판정, PRESERVE 직접 확인(네 곳), TARGET_WORKTREE clean.
- branch·worktree 보존.

## COMPLETE

- 채팅 보고만: base·C1·I·M의 SHA·parent·tree, E-1–E-6, preserve s2·s3, 시험·CI·Linux 판정, 예산, ASK 상태, 관측 한계, DEVIATIONS·ISSUES·PROPOSED_ERRATA.
- 검증 한계: 실제 세션 후보 조회 미수행, 실제 후보 2개에서 Deadline 60초 안 완료 여부 미검증, 추가 인코딩·분할·외부 참조 표식 미감지, H1·H4.
- 실제 세션 후보 조회는 별도 읽기 전용 계약과 승인으로 한다. AUTO-08-FIRST-USE의 STOP을 유지한다.

## TIME_ACCOUNTING

- 수행 시간 = 측정 구간 합계 − 제외 구간 합계. 시각은 독립 호출 date -u +%Y-%m-%dT%H:%M:%SZ의 출력이다.
- 제외: 보고 직후부터 재개 메시지 뒤 첫 명령 직전까지의 사용자 재개 대기. 권한 창 대기는 실제로 따로 측정할 수 있을 때만 빼며, 못하면 포함하고 "보수적 상한"으로 기록한다.
- IMPLEMENTATION 21600초(후퇴 뒤 재개 시 이어서 집계), CI 3600초(PR_CI).

## NETWORK

- 이 문서의 N1–N24만, 해당 gate 승인으로, 적힌 횟수 안에서 쓴다. N3·N4(WS-B5)는 PyPI와 빌드 의존성 다운로드다. 실패하면 STOP하고 재시도하지 않는다.

## EXPECTED_ASK

- WS-A2 worktree add, WS-A3 venv 생성(나타나는 경우)
- PS·FMT 인라인 실행(나타나는 경우)
- WS-B3 WORK_ORDER.md Write(task-contract)
- .claude/hooks/guard.py·docs/agent_workflow.md Edit
- MKD의 mkdir(나타나는 경우)
- git commit 2회, git push, gh pr create, gh pr merge, pip install
- 목록 밖 ASK, 거절, 무응답은 STOP. DENY는 즉시 STOP이며 재시도·변형하지 않는다.

## FORBIDDEN_ACTIONS

- 실제 세션·debug·메모리·세션 JSONL·tool-results 열람(OBSERVATION_LIMITS의 결과 파일 1개 절차 제외)
- 실제 세션에서 candidates·diagnose·precheck·run·status 실행
- ALLOWED 밖·PROTECTED 변경, 기존 시험 변경, 시험 삭제, skip·xfail 추가
- guard N7 밖 변경, settings·hook 등록 변경, 명령 은닉·문자열 분할·설정 완화, guard가 검사하지 않는 경로로 옮겨 실행
- controlled_read를 import하는 인라인 코드, INLINE_CHECKS 밖의 인라인 코드, 스크립트 파일 작성·실행, 새 검사 프로그램, 시험만을 위한 상태 노출 API
- 명령 체인·파이프·리디렉션(RECORDS 원문 예외만)
- git add .·-A, --no-verify, amend, force push, reset·restore·stash·clean·rebase·cherry-pick·checkout, fetch --all·--prune, branch·worktree 삭제
- PRESERVED_WORKTREES의 변경과 그 파일 내용·기록·data 열람(PRESERVE_RULES의 git 조회와 WS-A3의 venv 생성용 인터프리터 실행만 예외)
- AUTO-08–AUTO-14 기록 변경, 연구 공개 백업 진행

## STOP_CONDITIONS

- base·HEAD·tree·cwd·SETUP_EXECUTION_HEAD 불일치, WO 해시 불일치(WS-B3-FAIL 포함)
- 단계별 허용 상태 밖의 변경: WS 완료부터 IMPLEMENTATION 시작 전까지 0(ignored 기록·venv 제외), IMPLEMENTATION은 staged 0·tracked M 5개 안·untracked A 2개 안, PRECOMMIT_AUDIT는 W 불변, COMMIT add 뒤 commit 전 staged = 7개, commit 뒤 0
- EXIT_CRITERIA 미충족, 결과 불명, 출력 잘림의 허용 절차 밖 우회
- 기존 시험 실패(회귀), DIFF_SHAPE·CODE_READ·SIGNATURE 위반, PROTECTED diff, COLLECT_RULES 위반, FMT FAIL·오류, ASCII 검사 위반, PS 비기대 상태, REUSE 조건 불충족
- 예산 초과(21600초, CI 3600초, 조회 횟수, FIX, 같은 실패 2회 연속)
- guard DENY, hook 오류, 목록 밖 ASK, 거절·무응답
- REQUIRED_FAIL, Linux 신규 실패·판정 불가, merge 사전 검증 실패, preserve 허용 밖 차이
- 계약 모순, 상위 규칙과 충돌
- 관측 한계(OBSERVATION_LIMITS)는 STOP 조건이 아니다.
- 공통: 재시도·되돌리기·정리 없이 분류하고, 마지막 PASS 단계와 실제 HEAD·tree를 보고한 뒤 별도 승인을 기다린다.

## REQUIRED_EVIDENCE

- GIT_VERIFIABLE: SHA·parent·tree, 파일 집합, blob OID, merge parent 순서
- CLAUDE_REPORTED: 검사 판정 줄, W, PS·FMT·Grep 출력, collect·preserve 판정, CODE_READ·SIGNATURE 근거, pwd -W·date -u, 표시된 종료 코드 또는 미표시
- INDEPENDENT: 사용자 /status·/hooks 확인, GitHub CI 결과
- 관측하지 못한 승인 창은 ASK_UNVERIFIED.

## REQUIRED_REPORT

- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- cwd, HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, clean, diff --check
- 판정 줄과 종료 코드 또는 미표시, ASK 상태, 예산, 관측 한계
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES/NO, READY_FOR_<NEXT> = YES/NO

## AFTER_COMPLETE (참고, 이 task 밖)

- 실제 세션 후보 조회(예: AUTO-16-FIRST-USE-CANDIDATES)는 별도 읽기 전용 계약과 승인으로 한다. 고정 입력: project-key C--MoneyLab-auto-01, session 89314c93-2226-473b-8ef0-7ff8c28c57c6, profile ECON-FWD-M20-WO/2, N 44113503, SHA 5433d3eb2ce924e22e2cbd6e71d6e4d77f35b2e1e102825b2d4b73cfef2351f2. 기대(통과 조건 아님): line_count 14707, CANDIDATES_LISTED, candidate_count 2.
- 그 계약은 실행 루트(merge 뒤 커밋), 승인 원문 2건(gate + CONTROLLED_READ_CANDIDATES_AUTHORIZATION), 실행 1회, candidates/1 출력의 허용 목록 검증, 예상 밖 출력·traceback 재게시 금지, 관측 한계를 정한다.
- 어느 후보를 run에 쓸지는 사용자가 결정하고 run 계약도 따로 둔다.
