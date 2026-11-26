# Work Order: AUTO-10-CONTROLLED-READ-DIAGNOSE — controlled_read diagnose 하위 명령

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: AUTO-10-CONTROLLED-READ-DIAGNOSE
TASK_ID: AUTO-10-CONTROLLED-READ-DIAGNOSE
TITLE: 고정 prefix에서 최초 구조 위반의 위치와 고정 유형만 보고하는 diagnose 하위 명령
VERSION: 1.0
STATUS: ISSUED
REPOSITORY: swk3169/MoneyLab
CANONICAL_BASE_SHA: b88cb267ed993ddf55657518a37b03b924fcce27 (WS-A1에서 원격 main과 대조한다)
CANONICAL_BASE_TREE: fe3de24c2394a894d16e62070827695a81cfa706 (AUTO-09 사후 감사 기록값. WS-A1에서 다시 대조한다)
TARGET_BRANCH: codex/auto-10-controlled-read-diagnose
TARGET_WORKTREE: C:/MoneyLab-auto-10
SETUP_SESSION_ROOT: C:/MoneyLab-auto-09 (WORKSPACE_SETUP PART=WORKTREE 전용)
SESSION_ROOT: C:/MoneyLab-auto-10 (PART=C1_ENV부터 COMPLETE까지)
PRESERVED_WORKTREES: C:/MoneyLab-auto-09 (codex/auto-09-controlled-read-precheck @ 326fc4985f1118b1a0a1c81d197babff5d2dce72), C:/MoneyLab-auto-08-first-use (codex/auto-08-first-use @ 2b826d4ed9e278b28456eff9f8c70fa1070895ac)
AUDIT_TOOLS_PATH: C:/Users/USER/.codex/visualizations/2026/11/10/01a1c608-854b-77c3-9025-e5fba3a281a8/MoneyLab-approvals/AUTO-10-CONTROLLED-READ-DIAGNOSE/audit_tools.py
AUDIT_TOOLS_SHA256: 50d35e12322953f65639bf59a232679e4f65e4170c9c158a2eb05d5064bef9f3
PYTHON_VERSION: 3.14.8
TOOL_VERSIONS: mypy 2.4.0 (compiled: no), ruff 0.17.2, pytest 9.1.1
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: pytest
NONREQUIRED_CI_BASELINE: pytest-linux-experimental, run 45727495839의 기존 실패 2건(AUTO-09 확인 결과 재사용, 이번에 다시 조회하지 않음)
  - tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through
  - tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0
BUNDLE_ELIGIBLE: NO
BUNDLE_MAX_RANGE: NONE

## GATE_SEQUENCE

GATE_SEQUENCE: WORKSPACE_SETUP PART=WORKTREE -> WORKSPACE_SETUP PART=C1_ENV -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

- 한 번에 한 단계씩 전진한다. 각 단계에는 그 단계를 실행하는 세션에서 사용자가 보낸 Gate Authorization 원문이 있어야 한다. 원문을 확인할 수 없으면 STOP한다.
- PART=C1_ENV부터 COMPLETE까지는 같은 SESSION_ROOT 세션에서 한다. 세션이 바뀌면 이전 승인과 보존 기준은 이어지지 않는다. 다시 시작하려면 ACCEPTED ERRATA가 필요하다.
- 후퇴는 IMPLEMENTATION으로만, 명시적 승인으로 한다. COMMIT 이후 수정은 새 커밋이며 amend는 없다.
- 자동 전진은 없다. 각 단계의 PASS 조건 중 하나라도 미확인이면 보고하고 멈춘다.

## AUTHORIZATION_FORMS

- WORKSPACE_SETUP PART=WORKTREE(SETUP_SESSION_ROOT 세션):
  `GATE_AUTHORIZATION: AUTO-10-CONTROLLED-READ-DIAGNOSE WORKSPACE_SETUP PART=WORKTREE WO_SHA256=<64hex> AUDIT_TOOLS_SHA256=<64hex>`
- WORKSPACE_SETUP PART=C1_ENV(SESSION_ROOT에서 새로 시작한 세션):
  `GATE_AUTHORIZATION: AUTO-10-CONTROLLED-READ-DIAGNOSE WORKSPACE_SETUP PART=C1_ENV WO_SHA256=<64hex> WO_SOURCE=<AUDIT 허용 폴더 안의 절대 경로> AUDIT_TOOLS_SHA256=<64hex>`
- IMPLEMENTATION, PRECOMMIT_AUDIT, COMMIT, CLEAN_COMMIT_E2E, PUSH, POST_MERGE_AUDIT, COMPLETE:
  `GATE_AUTHORIZATION: AUTO-10-CONTROLLED-READ-DIAGNOSE <GATE> WO@<C1 SHA>`
- PR_CI: 위 줄 + PR_CREATE: YES, REPOSITORY: swk3169/MoneyLab, BASE: main, HEAD_BRANCH: codex/auto-10-controlled-read-diagnose, HEAD_SHA: <구현 커밋>, PR 제목·본문
- MERGE: 위 줄 + MERGE_EXECUTE: YES, PR: <번호>, HEAD_SHA: <구현 커밋>
- 대조: 원문 존재, 필드와 실행 인자의 문자열 완전 일치, audit_tools.py 파일 sha256 = AUDIT_TOOLS_SHA256(실행 직전마다 확인). 하나라도 어긋나면 STOP한다.

## AUTHORIZATION_MODEL

- 이 Work Order는 각 gate의 최대 범위만 정한다. 실행 승인이 아니다.
- 변경·실행에는 (1) gate 범위 (2) 해당 gate의 사용자 승인 원문 (3) 도구 권한 창과 guard 판정이 모두 있어야 한다. 어느 하나가 다른 것을 대신하지 않는다.
- guard.py와 docs/agent_workflow.md 변경은 D11·D12 범위에서만 허용한다.
- PRESERVED_WORKTREES와 그 venv·설치는 바꾸지 않는다.
  - 읽기는 AUDIT_TOOLS의 preserve 모드가 하는 git 메타데이터 조회(HEAD, tree, status 줄 수, worktree·ref 목록)와 C:/MoneyLab-auto-09 설치 메타데이터 2파일의 해시로만 한정한다.
  - 그 worktree의 파일 내용·기록·data는 열지 않는다.
- AUTO-08-FIRST-USE는 PRECHECK STOP 상태를 유지한다. 이 task는 그 기록을 바꾸거나 재평가하지 않는다.
- EXIT_CRITERIA(판정 기준):
  - 출력 기반 확인: 계약에 적힌 기대 출력이 있고 도구 오류 표시가 없으면 통과다.
  - Git ref 부재: `show-ref --verify --quiet`에 도구가 명시적으로 표시한 `Exit code 1`이 있을 때만 부재로 판정한다.
  - 경로 상태: AUDIT_TOOLS path-state 모드의 `PATH_STATE`로만 판정한다. `test -e`·`test -f`는 쓰지 않는다.
  - 검사 도구:
    - pytest: 마지막 요약 줄에 `passed`가 있고 `failed`·`error`가 없음
    - ruff: `All checks passed!`
    - mypy: `Success: no issues found`로 시작하는 줄
    - AUDIT_TOOLS: `RESULT=` 줄
  - git diff 계열:
    - `git diff`(옵션 없음)·`--stat`·`--name-status`·`--name-only`: 차이가 있어도 정상 종료하므로 출력 내용으로 판정한다.
    - `git diff --check`: 출력이 비고 도구 오류가 없어야 통과다. 출력이 있으면 위반이다.
    - `--quiet`·`--exit-code`: 이 계약에서는 쓰지 않는다. 쓰게 되면 `Exit code 1`은 "차이 있음"이고, 그 밖의 0이 아닌 값은 도구 오류다.
  - gh pr checks: PR_CI의 CI_STATES로 판정한다.
  - 표시된 프로세스 종료 코드는 별도로 기록한다. 위 예외를 빼고 0이 아닌 값이 표시되면 실패다.
  - 미표시만으로 실패나 STOP을 만들지 않으며, 종료 코드 0이 입증됐다고 쓰지도 않는다.
  - JSON exit_code는 프로그램 보고값이며 OS 종료 코드와 같다고 입증된 것이 아니다.

## GOAL

GOAL: moneylab.controlled_read에 diagnose 하위 명령 하나를 추가한다. diagnose는 승인 입력으로 고정한 prefix [0, N)에서 precheck scan과 같은 검사를 같은 순서로 적용하고, 최초 FORMAT_UNSUPPORTED 위반의 줄·검사 ID·적용 등급·고정 필드 경로·기대 타입·실제 JSON 타입·block/item 위치만 보고한다. selector·values를 만들지 않으며, 지원 범위와 기존 판정은 바꾸지 않는다.

## BACKGROUND

BACKGROUND:
- AUTO-08-FIRST-USE의 PRECHECK(C1 2b826d4ed9e278b28456eff9f8c70fa1070895ac)는 FORMAT_UNSUPPORTED, checks.scan=FAILED, prefix_check=MATCHED로 끝났다. 측정값은 prefix_bytes 44113503, line_count 14707, prefix_sha256 5433d3eb2ce924e22e2cbd6e71d6e4d77f35b2e1e102825b2d4b73cfef2351f2다. 실제 원인 줄과 필드는 미확인이다.
- 현재 precheck/1 출력에는 위반 위치가 없다(AUTO-09 D9). guard에는 위치를 보고하는 실행 경로가 없다(guard.py:400-415).
- 이 task는 합성 tmp_path 자료만 쓴다. 실제 세션 열람과 최초 진단 실행은 별도 계약과 승인으로 한다.
- 연구 공개 백업 보류와 모든 과거 기록(ASK_UNVERIFIED, H4 미확인, 각 STOP과 정정 기록)을 유지한다.

## DESIGN_CONTRACT

D1 CLI(유일, Bash 독립 호출, ASCII 공백 1개):
`.venv/Scripts/python.exe -B -m moneylab.controlled_read diagnose --task <TASK_ID> --project-key <PROJECT_KEY> --session <SESSION> --profile <PROFILE> --expect-prefix-bytes <N> --expect-prefix-sha256 <SHA>`
- 값 검사는 selector._values(argv, "diagnose", DIAGNOSE_OPTIONS)와 valid_task_id·valid_project_key·valid_session·valid_profile로 한다(selector.py:64-106의 기존 함수를 그대로 호출).
- N: `[1-9][0-9]{0,7}`에 fullmatch하고 정수로 1 ≤ N ≤ 67108864
- SHA: `[0-9a-f]{64}`

D2 불변:
- run·status·precheck의 CLI, 문법, 스키마, 출력 바이트
- DETAILS, ERROR_CODES, ControlledReadError, store의 모든 상수·함수·valid_result
- selector·profiles·store·__init__ 모듈
- 기록 경로, open_session, Session, Session.rehash, parse_line, _lines, _find, select_text, _tool_result_texts
- 예외: __main__.run()에 `argv[:1] == ["diagnose"]` 분기 하나를 추가한다.
  - 이 분기는 첫 토큰이 정확히 "diagnose"인 입력의 출력을 result/1 ARGUMENT_INVALID에서 diagnose/1로 바꾼다. 그 밖의 입력(예: ["scan"], ["diagnosex"])은 기존과 같다(test_controlled_read_cli.py:333-339).

D3 위반 위치와 진단 전용 상태:
- transcript.py에 클래스 FormatViolation(ControlledReadError)를 추가한다.
  - __init__(check_id, field_path, expected, actual_json_type, block_index=None, item_index=None)은 super().__init__("FORMAT_UNSUPPORTED")만 호출하고, 위치 값은 별도 속성에 둔다.
  - code·detail·args·final_created·tmp_leftover는 ControlledReadError("FORMAT_UNSUPPORTED")와 같다. line·block_index는 None일 때만 채우는 메서드 `_at(line=None, block_index=None)`로 나중에 채운다.
- 같은 파일에 보조 함수 `_json_type(container, key)`를 둔다. 값이 문자열이면 값을 비교·출력하지 않고 "string"만 돌려준다.
- 진단 전용 상태(DIAGNOSE_*)는 ControlledReadError로 만들지 않는다. diagnose.py의 DiagnoseError(Exception)이 DIAGNOSE_DETAILS 등록 코드만 받는다. DiagnoseError는 run·precheck 경로에서 쓰지 않는다.
- transcript.py의 허용 변경(이 밖은 금지, DIFF_SHAPE로 감사):
  - (a) FormatViolation 클래스와 _json_type 추가
  - (b) raise 교체 9곳: 216-218(S2), 256-258(S3a), 261-262(S3b), 264-265(S3c), 284-285(S4c), 288-289(S4d), 332-333(S1), 344-345(S4a), 346-347(S4b)의 `raise ControlledReadError("FORMAT_UNSUPPORTED")`를 `raise FormatViolation(...)`로 바꾼다. 조건식은 글자 그대로 유지하고, FormatViolation 인자 계산은 조건이 참일 때만 한다.
  - (c) 위치를 얻기 위한 반복문 인덱싱:
    - _user_blocks 215-218의 `for block in blocks`를 `for block_index, block in enumerate(blocks, start=1)`로
    - _assistant_texts 260의 `for block in message["content"]`를 enumerate(start=1)로
    - _tool_result_content_texts 287의 `for item in content`를 enumerate(start=1)로
    - scan_candidates 329의 `for line in _lines(...)`를 enumerate(start=1)로
    - scan_candidates 340의 `for block in blocks`를 enumerate(start=1)로
    - 위치는 반복 인덱스에서만 얻는다. list.index는 쓰지 않는다.
  - (d) 위치 전달:
    - scan_candidates의 줄 처리 본문을 `try: … except FormatViolation as exc: exc._at(line=line_no); raise`로 감싼다.
    - tool_result 블록 처리에서 _tool_result_content_texts 호출을 `try: … except FormatViolation as exc: exc._at(block_index=block_index); raise`로 감싼다.
    - 같은 예외 객체를 그대로 다시 던진다.
  - 그 밖의 줄(229-230, 239-240, 252-253, 271-275, 검사 순서, 반환값, 선택·추출 결과)은 바꾸지 않는다.
- 보존 근거:
  - (가) PRECOMMIT_AUDIT에서 __main__의 except 지점이 exc.code와 STORE_FAILED 전용 속성만 쓴다는 점을 Grep으로 다시 확인한다.
  - (나) T9 골든 시험

D4 검사 ID, 적용 등급, 실제 RUN 동작(transcript.py 근거):
- 등급의 뜻:
  - GLOBAL: run이 selector 종류와 관계없이 prefix의 모든 줄에 요구한다.
  - SELECTOR_KIND_DEPENDENT: run이 tool_result 선택자일 때만, 그 종류의 모든 block에 요구한다.
  - SELECTED_ENTRY_ONLY: run이 선택된 대상 항목이나 block 하나에만 요구한다.
  - precheck와 diagnose는 등급과 관계없이 profile kinds의 모든 항목에 적용한다.
- 검사별:
  - S1 entry.uuid 비문자열: GLOBAL(_find 229-230)
  - S2 user content block 비객체 또는 type 비문자열: GLOBAL(_find 231 → _user_blocks)
  - S3a·S3b·S3c(assistant 구조): SELECTED_ENTRY_ONLY. assistant 선택자의 대상 항목만(select_text 297 → _assistant_texts)
  - S4a tool_use_id 비문자열: SELECTOR_KIND_DEPENDENT(_find 239-240, tool_result 선택자)
  - S4b is_error 비bool: SELECTED_ENTRY_ONLY. tool_result 대상 block만(_tool_result_texts 271-273, 원래 위치 그대로)
  - S4c·S4d: SELECTED_ENTRY_ONLY. tool_result 대상 block만(_tool_result_texts → _tool_result_content_texts)
- 이 등급은 보고용 고정 표이며 판정을 바꾸지 않는다. bool 형태의 run_required는 쓰지 않는다.

D5 출력 허용 목록(diagnose.py 상수, 이 밖의 값은 출력하지 않음):
- (check_id, field_path, expected) 쌍:
  - S1: entry.uuid / string
  - S2: user.content[] / object, user.content[].type / string
  - S3a: assistant.message / object, assistant.message.content / array
  - S3b: assistant.content[] / object, assistant.content[].type / listed_block_type
  - S3c: assistant.content[].text / string
  - S4a: tool_result.tool_use_id / string
  - S4b: tool_result.is_error / bool
  - S4c: tool_result.content / string_or_array
  - S4d: tool_result.content[] / object, tool_result.content[].type / text_literal, tool_result.content[].text / string
- actual_json_type: missing, null, bool, number, string, array, object, string_unlisted 중 하나. string_unlisted는 S3b·S4d의 type이 문자열이지만 허용 값이 아닐 때다.
- block_index: S2·S3b·S3c·S4a·S4b·S4c·S4d에서 message.content 배열의 1부터 센 위치. S1·S3a는 null
- item_index: S4d에서 tool_result content 배열의 1부터 센 위치. 그 밖은 null
- line: prefix 안의 1부터 센 줄 번호
- 출력 전 검증: diagnose 문서를 만들 때 각 값이 이 목록과 정수 범위에 맞는지 확인한다. 어긋나면 ValueError를 던진다(정의되지 않은 예외, 출력 없음).
- 문자열 값, 키 이름, uuid·tool_use_id, 본문은 어떤 경로로도 출력하지 않는다.

D6 고정 prefix(diagnose.py의 open_fixed_prefix. transcript의 open_session·Session·rehash는 바꾸지 않는다):
1. rel = transcript.session_rel(project_key, session_id)(기존 함수 그대로).
   before = collect.check_tree_path(home, rel, "SESSION_PATH_INVALID", require_regular=True)로 경로 각 구성요소의 링크·reparse point·비디렉터리 부모와 마지막 구성요소의 정규 파일 여부를 검사한다.
   WorkstateError는 SESSION_PATH_INVALID, None은 SESSION_NOT_FOUND. 이 단계에서는 파일을 열지 않는다.
2. 1을 통과한 뒤에만 handle = open(home / rel, "rb").
   FileNotFoundError는 SESSION_NOT_FOUND, 그 밖의 OSError는 SESSION_PATH_INVALID. 열기에 실패하면 handle이 없으므로 닫을 것도 없다.
3. handle 소유권:
   - 2 이후 open_fixed_prefix가 handle을 소유한다. 4–8 중 어떤 예외(BaseException 포함)가 나도 handle.close()를 호출한 뒤 다시 던진다.
   - 9에서 Session을 반환하면 소유권이 호출자(_diagnose)로 넘어간다. _diagnose는 G4·G5를 감싼 finally에서 session.handle.close()를 한 번 호출한다.
4. opened = transcript._fstat(handle.fileno())(호출 시점에 조회하는 seam).
   (before.st_size, st_dev, st_ino) ≠ (opened.st_size, st_dev, st_ino)면 SESSION_PATH_INVALID. S0 = opened.st_size
5. S0 < N이면 SESSION_TRUNCATED(읽지 않음).
6. data = transcript._read_exactly(handle, N, deadline). 읽는 범위는 [0, N)뿐이다.
   TIME_LIMIT_EXCEEDED는 그대로 전파하고, OSError는 SESSION_UNREADABLE, len(data) < N이면 SESSION_TRUNCATED.
7. sha256(data) ≠ SHA면 DiagnoseError("DIAGNOSE_PREFIX_MISMATCH").
8. 7을 통과했는데 data[-1] ≠ 0x0A면 DiagnoseError("DIAGNOSE_PREFIX_NOT_LINE_ALIGNED"). 7이 8보다 우선한다.
9. 측정값 observed_size_at_open = S0, trailing_bytes_excluded = S0 − N, line_count = data.count(b"\n")를 target에 쓰고 transcript.Session(handle, data, target)을 반환한다.
- 한도: N ≤ 64 MiB일 때만 S0 > 64 MiB를 허용한다. 읽기(6)와 재해시(Session.rehash, len(prefix) = N)는 언제나 [0, N)이다. 줄 8 MiB·항목 200000·시간 60 s는 기존 _lines·Deadline을 그대로 쓴다.
- Deadline은 1 직전에 한 번 만들어 열기·읽기·scan·재해시 전체에 쓴다.
- observed_size_at_open은 4가 끝나 S0를 얻었을 때만 값이고, 그 밖은 null이다. trailing_bytes_excluded·line_count는 9에서만 값이 들어간다.

D7 처리 순서와 상태표(__main__._diagnose):
- 키는 항상 존재한다.
  - target: project_key, session_id, expected_prefix_bytes, expected_prefix_sha256, observed_size_at_open, trailing_bytes_excluded, line_count, prefix_check
  - checks: prefix, scan. 값은 NOT_REACHED, PASSED, FAILED 중 하나
- 경로별 값:
  - G1 인자 오류: status ARGUMENT_INVALID. task_id·profile·target·checks·violation은 null. exit 2
  - G2 환경(confirmed_root, confirmed_home): ENVIRONMENT_INVALID. target은 인자 4개만 값, 측정 4개 null. checks는 NOT_REACHED/NOT_REACHED. violation null. exit 2
  - G3a 1–2 실패: 해당 코드. target 측정 4개 null. checks는 FAILED/NOT_REACHED. exit 2
  - G3b 4–8 실패: 해당 코드(SESSION_PATH_INVALID, SESSION_TRUNCATED, SESSION_UNREADABLE, TIME_LIMIT_EXCEEDED, DIAGNOSE_PREFIX_MISMATCH, DIAGNOSE_PREFIX_NOT_LINE_ALIGNED). observed_size_at_open은 4가 성공했으면 S0, 아니면 null. 나머지 측정 3개 null. checks는 FAILED/NOT_REACHED. exit 2
  - prefix 확정 뒤에는 trailing_bytes_excluded = S0 − N, line_count = prefix의 LF 수이고, checks.prefix는 PASSED다.
  - G4 scan = transcript.scan_candidates(prefix, profile.kinds, 항상 False인 판정 함수, deadline):
    - G4a FormatViolation: 후보 DIAGNOSE_VIOLATION_FOUND, scan FAILED, violation = D5 객체
    - G4b SESSION_CORRUPT, LINE_LIMIT_EXCEEDED, ENTRY_LIMIT_EXCEEDED: 후보 그 코드, scan FAILED, violation null
    - G4c TIME_LIMIT_EXCEEDED: 재해시 없이 확정. prefix_check INCOMPLETE, scan FAILED, violation null, exit 2
    - G4d 예외 없음: 후보 DIAGNOSE_NO_VIOLATION, scan PASSED
  - G5 재해시(G4a·b·d 뒤): Session.rehash(deadline)
    - (None, MATCHED)면 후보를 유지하고 prefix_check = MATCHED
    - (code, check)면 status = code, prefix_check = check, violation = null(폐기), exit 2. scan 값은 유지한다.
  - handle은 G4·G5에서 finally로 닫는다.
- exit_code는 DIAGNOSE_NO_VIOLATION만 0이고 나머지는 2다.
- error는 DIAGNOSE_NO_VIOLATION만 null이다. 그 밖에는 {code, detail}이고, 문구는 DETAILS 또는 DIAGNOSE_DETAILS를 쓴다.
- 정의되지 않은 예외는 출력 없이 전파한다.
- DIAGNOSE_NO_VIOLATION은 PRECHECK_OK, selector 존재, RUN 성공을 뜻하지 않는다.

D8 diagnose.py(새 모듈):
- DIAGNOSE_OPTIONS = ("--task", "--project-key", "--session", "--profile", "--expect-prefix-bytes", "--expect-prefix-sha256")
- DIAGNOSE_SCHEMA = "moneylab.controlled_read.diagnose/1"
- DIAGNOSE_DETAILS(키는 DETAILS와 겹치지 않음):
  - DIAGNOSE_VIOLATION_FOUND: "the first unsupported structure in the fixed prefix is described in violation"
  - DIAGNOSE_NO_VIOLATION: "no unsupported structure was found in the fixed prefix by the scan checks"
  - DIAGNOSE_PREFIX_MISMATCH: "the bytes at the expected prefix do not have the expected sha256"
  - DIAGNOSE_PREFIX_NOT_LINE_ALIGNED: "the expected prefix does not end with LF"
- 그 밖에 DiagnoseError, parse_diagnose, open_fixed_prefix, diagnose_document를 둔다. 직렬화는 store.canonical_bytes를 그대로 쓴다.
- 문서 키: schema, command("diagnose"), status, exit_code, task_id, target, profile, checks, violation, error, authority, approval, boundary. selector·values·record 키는 없다.
- 기록 파일을 만들지 않는다(prepare_attempt·create_record 호출 없음).
- import 허용: moneylab.controlled_read(__init__, selector, store, profiles, transcript), moneylab.workstate.collect, 표준 라이브러리. automation·runlog·providers는 import하지 않는다(기존 test_controlled_read_isolation.py 통과).

D11 guard.py 변경 허용 범위:
- (a) CONTROLLED_READ_PRECHECK_FORM(guard.py:394) 다음 줄에 상수 하나를 추가한다:
  `CONTROLLED_READ_DIAGNOSE_FORM = re.compile(_CR_EXE + r"diagnose --task " + _CR_TASK + r" --project-key [A-Za-z0-9-]{1,200} --session " + _CR_SESSION + r" --profile (?:ECON-FWD-M20-WO/1|ECON-FWD-M20-PREREG/1) --expect-prefix-bytes (?P<bytes>[1-9][0-9]{0,7}) --expect-prefix-sha256 [0-9a-f]{64}", re.ASCII)`
- (b) _controlled_read의 precheck 분기(guard.py:410-413) 뒤, 같은 `if bash:` 블록 안에 분기 하나를 추가한다.
  - m이 있고 len(m.group("task")) ≤ 64이고 int(m.group("bytes")) ≤ 67108864이면
    `Decision(ASK, "controlled-read", "controlled read diagnose; confirm the CONTROLLED_READ_DIAGNOSE_AUTHORIZATION message first")`
  - 그 밖은 기존 마지막 DENY로 간다.
- (c) 기존 상수·루프·precheck 분기·reason·마지막 DENY·_CR_MODULE·INLINE_CODE 조건·check_command 순서는 바꾸지 않는다.

D12 docs/agent_workflow.md 변경 허용 범위(제한 읽기 CLI 절 안):
- "세 형태"를 "네 형태"로 고치고 D1 형태를 추가한다.
- 기록 없음, status 대상 아님, D7 의미 한계 문장을 넣는다.
- 승인 문구를 추가한다:
  `CONTROLLED_READ_DIAGNOSE_AUTHORIZATION: AUTO-10-CONTROLLED-READ-DIAGNOSE TASK=<TASK_ID> PROJECT_KEY=<PROJECT_KEY> SESSION=<SESSION> PROFILE=<PROFILE> EXPECT_PREFIX_BYTES=<N> EXPECT_PREFIX_SHA256=<SHA> EXPIRES_UTC=<YYYY-MM-DDTHH:MM:SSZ>`
  - 원문 존재, 필드 6개와 인자의 문자열 완전 일치, 만료를 확인한다.
  - 이 승인은 다른 controlled_read 승인을 대신하지 않는다.
- 그 밖의 절은 바꾸지 않는다. guard 규칙 이름은 controlled-read 그대로다(test_skills.py 대조 유지).

## ALLOWED_FILES

ALLOWED_FILES(TARGET_WORKTREE):
- M src/moneylab/controlled_read/transcript.py (D3 (a)–(d)만)
- M src/moneylab/controlled_read/__main__.py (diagnose 분기와 _diagnose)
- A src/moneylab/controlled_read/diagnose.py
- M .claude/hooks/guard.py (D11만)
- M docs/agent_workflow.md (D12만)
- A tests/test_controlled_read_diagnose.py
- A tests/test_controlled_read_diagnose_guard.py

## PROTECTED_FILES

PROTECTED_FILES:
- CANONICAL_BASE_SHA에 이미 있는 tests/** 전체. 위 두 A 시험 파일은 base에 없으므로 여기에 포함되지 않는다.
  - 명시 목록: tests/test_agent_guard.py, test_skills.py, test_repo_hygiene.py, test_controlled_read_cli.py, test_controlled_read_isolation.py, test_controlled_read_precheck.py, test_controlled_read_profiles.py, test_controlled_read_selector.py, test_controlled_read_store.py, test_controlled_read_transcript.py, tests/conftest.py, tests/fixtures/**
- src/moneylab/controlled_read/__init__.py, selector.py, store.py, profiles.py, 그리고 src/** 가운데 ALLOWED_FILES의 세 소스 경로(transcript.py, __main__.py, diagnose.py)를 뺀 모든 경로
- .claude/** 중 hooks/guard.py를 뺀 모든 경로, .github/**, CLAUDE.md, pyproject.toml, requirements*.txt, .gitignore, 사전등록 파일
- docs/tasks/** (예외: WS-B의 docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/WORK_ORDER.md 최초 생성 1회. 그 뒤 불변)
- 판정: `git diff --name-status <base>`에서 PROTECTED 경로의 M·D·R이 0이고, A는 ALLOWED_FILES의 A 3개와 C1의 WORK_ORDER.md뿐이어야 한다.

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅.

## FILE_FORMAT

- 신규 파일 전체와 수정 파일의 추가·변경 줄: UTF-8(BOM 없음), LF, 파일 끝 LF 1개, 탭·U+00A0·줄 끝 공백 없음, `git diff --check` 위반 없음.
- 수정(M) 파일:
  - 정규화 바이트가 UTF-8 BOM으로 시작하면 F<n>_BOM=YES로 FAIL.
  - 추가·변경 줄의 U+FEFF는 BOM과 별도 항목인 F<n>_ADDED_FEFF로 개수를 보고하며, 1 이상이면 FAIL.
- 비ASCII 문자(기존 한국어 문서 포함)는 그 이유만으로 거부하지 않는다.
- 신규 시험의 비ASCII 합성 입력은 명시적 이스케이프로 쓴다. 이 이스케이프 요구는 M5가 판정하지 않으며, 별도 수동 감사 항목으로 유지한다.
- W(작업 파일 바이트)와 S(CRLF만 LF로 바꾼 바이트)는 AUDIT_TOOLS가 계산한다. index·commit blob 내용 sha256도 AUDIT_TOOLS가 git cat-file로 메모리에서 계산한다. 셸 파이프는 쓰지 않는다.
- 줄바꿈 변환 경고는 보고만 한다. blob 기준 대조가 우선한다.

## AUDIT_TOOLS (단일 고정 파일, 원문은 별도 승인으로 작성·검토·고정)

- 위치: AUDIT_TOOLS_PATH. C1 전에 사용자 승인으로 create-new 1회 만든다. 수정·교체·삭제·이동은 금지한다.
- 실행: 실행 직전 독립 호출 `sha256sum <AUDIT_TOOLS_PATH>` = AUDIT_TOOLS_SHA256을 확인한 뒤 `<CHECK_PYTHON> -I -B <AUDIT_TOOLS_PATH> <MODE> <인자…>`로 실행한다. 표준 입력 전달은 없다.
  - CHECK_PYTHON = C:/MoneyLab-auto-10/.venv/Scripts/python.exe. WS-A의 venv 생성 전에는 C:/MoneyLab-auto-09/.venv/Scripts/python.exe
- 순환 방지: 프로그램에는 WO_SOURCE·WO_SHA256·구현 뒤 해시·C1·구현 커밋·BEFORE 값·I·M을 넣지 않는다. 모두 승인 인자로 받는다. 프로그램에 고정하는 것은 아래 상수뿐이다.
  - 경로: TARGET_WORKTREE, PRESERVED_WORKTREES, WO_SOURCE 허용 폴더(AUDIT_TOOLS_PATH의 폴더), 계약 저장 경로, ALLOWED_FILES 7개
  - 이름: TARGET_BRANCH, REPOSITORY 관련 ref 이름
  - 값: CANONICAL_BASE_SHA, 기록 경로, PRESERVED_WORKTREES의 고정 기대 HEAD 2개(Work Order 바이트와 무관)
- 모드별 인자 개수·허용 경로·Git 명령은 audit_tools.py 원문의 MODES와 각 함수의 docstring에 있는 그대로다.
- 공통:
  - 표준 라이브러리만 쓴다.
  - 하위 프로세스는 `git -C <고정 경로> <고정 하위 명령>`만 쓴다(shell=False, stdin DEVNULL, capture_output, GIT_OPTIONAL_LOCKS=0, returncode 확인, UTF-8 strict, CR 포함 출력 거부).
  - 파일 쓰기·삭제·이동·네트워크는 없다.
  - 파일 원문·본문을 출력하지 않는다. 출력은 key=value 줄과 마지막 `RESULT=`이다.
  - 인자가 허용 목록 밖이면 사용 오류다.
  - RESULT와 종료 코드:
    - PASS, REPORTED, RECORDED → 0(통과, 보고, 기록)
    - FAIL → 3(위반)
    - USAGE_ERROR, ERROR → 2(사용 오류, 도구 오류)
- 모드:
  - M1 contract `<WO_SOURCE> <WO_SHA256>`
    - WO_SOURCE는 허용 폴더 안의 `WORK_ORDER.review.md` 또는 `WORK_ORDER.review-v<1–3자리 숫자>.md`만, 슬래시(/) 절대 경로로 받는다. 역슬래시나 `..`가 있으면 사용 오류다.
    - 원본과 계약 저장 경로의 W·S, CR_RAW·CR_REMAIN, UTF8_STRICT, BOM, TAB, NBSP, TRAILING_WS_LINES, FINAL_LF
    - 판정: 저장 파일 W = S = WO_SHA256, 원본 S = WO_SHA256, 둘 다 형식 통과이면 RESULT=PASS
  - M2 path-state `<경로>`
    - 허용 경로(이 목록만):
      - C:/MoneyLab-auto-10
      - C:/MoneyLab-auto-10/docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE
      - RECORDS의 디렉터리 5개(data, data/processed, data/processed/auto10, data/processed/auto10/baseline, data/processed/auto10/precommit. 모두 TARGET_WORKTREE 기준)
      - RECORDS의 파일 3개
      - ALLOWED_FILES의 A 3개
    - os.lstat 1회. 대상이나 하위 내용은 따라 읽지 않는다.
    - 출력 PATH_STATE는 ABSENT / DIRECTORY / FILE / LINK / REPARSE / OTHER 중 하나이며, ABSENT가 아니면 REPARSE_POINT=YES|NO를 함께 출력한다.
      - 분류 순서: symlink → LINK, 그 밖에 FILE_ATTRIBUTE_REPARSE_POINT(0x400)가 있으면 → REPARSE(junction 포함), 그다음 DIRECTORY / FILE / OTHER.
      - ABSENT는 FileNotFoundError일 때만이다.
      - 이 상태들의 RESULT는 REPORTED다. 그 밖의 lstat 오류는 PATH_STATE=QUERY_ERROR(ERROR_TYPE 포함), RESULT=ERROR다.
    - STOP 조건:
      - 기대 상태가 ABSENT인 경로에 ABSENT가 아닌 값이 나오면 STOP.
      - 기대 상태가 DIRECTORY인 경로는 PATH_STATE=DIRECTORY이면서 REPARSE_POINT=NO일 때만 통과한다. LINK / REPARSE / OTHER / FILE은 STOP.
      - 기대 상태가 FILE인 경로는 PATH_STATE=FILE이면서 REPARSE_POINT=NO일 때만 통과한다.
      - 어떤 경로든 QUERY_ERROR / ERROR이면 STOP. 재시도하거나 다른 방법으로 확인하지 않는다.
      - junction이나 reparse 경로는 재사용하거나 정리하지 않고 보고한다.
  - M3 ignore `<경로>`
    - 경로는 `.venv/x`, `data/processed/auto10/x`만 받는다.
    - `git -C C:/MoneyLab-auto-10 check-ignore -v -- <경로>` 출력에서 source·pattern을 분석한다. git 종료 코드 0·1만 받고, 그 밖은 ERROR다.
    - 출력: GIT_EXIT, RULE_SOURCE, RULE_PATTERN, IGNORED(YES|NO)
    - 판정: 출력이 한 줄이고, 표시 경로가 인자와 같고, source가 `.gitignore`이고, pattern이 `!`로 시작하지 않으면 IGNORED=YES, RESULT=PASS. 그 밖은 IGNORED=NO, RESULT=FAIL. 행 번호는 판정에 쓰지 않는다.
  - M4 guard-base
    - TARGET_WORKTREE/.claude/hooks/guard.py 작업 파일의 S와 `git cat-file blob <CANONICAL_BASE_SHA>:.claude/hooks/guard.py` 내용 sha256을 비교한다.
    - 출력: GUARD_W, GUARD_S, GUARD_CR_RAW, BASE_BLOB_SHA256, GUARD_CR_REMAIN, GUARD_S_EQ_BASE
    - 판정: S = BASE_BLOB_SHA256이고 CR_REMAIN 0이면 RESULT=PASS
  - M5 worktree-bytes
    - ALLOWED_FILES 7개의 W·S·CR_RAW를 계산한다.
    - A 3개는 FILE_FORMAT 전체를 검사한다.
    - M 4개는 `git diff --no-color --no-ext-diff --no-renames -U0 <CANONICAL_BASE_SHA> -- <경로>`의 추가 줄에서 TAB·NBSP·줄 끝 공백·CR·U+FEFF를 세고, 파일 전체의 BOM·CR_REMAIN·FINAL_LF를 검사한다.
    - 모두 통과하면 RESULT=PASS. 출력 S가 구현 뒤 감사값이 된다(guard 포함).
  - M6 blobs `<INDEX|HEAD>` `<S값 7개를 ALLOWED_FILES 순서로>`
    - `git cat-file blob :<경로>` 또는 `HEAD:<경로>`의 내용 sha256을 인자와 대조한다. 7개 모두 일치하면 RESULT=PASS.
    - 계약 WORK_ORDER.md는 M7로 대조한다.
  - M7 contract-blob `<INDEX|HEAD>` `<WO_SHA256>`: 계약 저장 경로의 blob 내용 sha256을 대조한다. 일치하면 RESULT=PASS.
    - 출력: CONTRACT_BLOB_SHA256, CONTRACT_MATCH. CONTRACT_MATCH=YES이고 RESULT=PASS여야 통과한다.
  - M8 collect `<STAGE>`
    - STAGE: BASELINE, PRECOMMIT. RECORDS의 해당 파일 경로가 고정돼 있다.
    - pytest `--collect-only -q` 출력을 분석한다. node ID 줄은 매개변수·공백을 보존한 원문 그대로이고, 첫 빈 줄 전까지다. 빈 줄 뒤의 비어 있지 않은 줄은 요약 한 줄뿐이어야 한다.
    - 요약 줄 형식: `<selected>[/<total>] test(s) collected[ (<deselected> deselected)] in <초>s`. 형식이 다르면 거부한다.
    - 요약 줄의 관계를 모두 검증한다.
      - 추출 ID 수 = selected
      - total과 deselected가 둘 다 있으면 total = selected + deselected
      - 둘 다 없는 형식은 허용
      - 한쪽만 있는 형식은 모호한 출력으로 거부
      - 중복 ID, 빈 줄 구획 위반, 요약 형식 불일치는 거부
    - 거부는 RESULT=ERROR(종료 코드 2)이며 STOP이다. 모순된 요약은 통과하지 못한다.
    - BASELINE 단독: 형식·개수 확인 뒤 RESULT=REPORTED.
    - PRECOMMIT: BASELINE과 비교한다. REMOVED = 0이고, ADDED의 모든 ID가 두 신규 시험 파일 경로로 시작하면 RESULT=PASS.
    - 출력: 단계별 <STAGE>_FILE_SHA256, <STAGE>_IDS, <STAGE>_SUMMARY_SELECTED, <STAGE>_SUMMARY_TOTAL, <STAGE>_SUMMARY_DESELECTED, 그리고 PRECOMMIT에서 REMOVED, ADDED, ADDED_OUTSIDE_NEW_FILES. ID 원문은 출력하지 않는다.
  - M9 preserve
    - 프로그램에 실제 BEFORE 값을 넣지 않는다. 프로그램을 먼저 고정한 뒤 BEFORE를 실행할 수 있다.
    - 읽는 대상(읽기 전용):
      - `git -C C:/MoneyLab-auto-09 worktree list --porcelain`
      - `git -C C:/MoneyLab-auto-09 for-each-ref "--format=%(objectname) %(refname) %(symref)" refs/heads refs/remotes refs/tags`
      - PRESERVED_WORKTREES 두 곳 각각의 `rev-parse HEAD`, `rev-parse "HEAD^{tree}"`, `status --porcelain=v1 --untracked-files=all` 줄 수
      - C:/MoneyLab-auto-09/.venv/Lib/site-packages/moneylab-0.3.0.dist-info/direct_url.json과 __editable__.moneylab-0.3.0.pth의 원바이트 sha256
    - 해시 대상에서 빼고 따로 다루는 항목(고정):
      - worktree path C:/MoneyLab-auto-10 항목
      - ref: refs/heads/codex/auto-10-controlled-read-diagnose, refs/remotes/origin/codex/auto-10-controlled-read-diagnose, refs/remotes/origin/HEAD, refs/remotes/origin/main
    - 나머지 worktree 항목과 ref 줄은 정렬해 LF로 이어 붙인 sha256과 개수로 쓴다.
    - 기준값 16개(이 순서, 이 형식):
      1. WT_SHA256(64hex) 2. WT_COUNT(정수) 3. REF_SHA256(64hex) 4. REF_COUNT(정수)
      5. AUTO09_HEAD(40hex) 6. AUTO09_TREE(40hex) 7. AUTO09_STATUS_LINES(정수)
      8. FIRSTUSE_HEAD(40hex) 9. FIRSTUSE_TREE(40hex) 10. FIRSTUSE_STATUS_LINES(정수)
      11. DIRECT_URL_SHA256(64hex) 12. PTH_SHA256(64hex)
      13. ORIGIN_HEAD_STATE(ABSENT|PRESENT) 14. ORIGIN_HEAD_SYMREF(ref 이름 문자열 또는 NONE) 15. ORIGIN_HEAD_OBJECT(40hex 또는 NONE)
      16. ORIGIN_MAIN_OBJECT(40hex 또는 NONE)
    - PRESERVED_WORKTREES 고정 기대 HEAD(Work Order 바이트와 무관):
      - C:/MoneyLab-auto-09 = 326fc4985f1118b1a0a1c81d197babff5d2dce72
      - C:/MoneyLab-auto-08-first-use = 2b826d4ed9e278b28456eff9f8c70fa1070895ac
    - 호출 형식(인자 개수 고정):
      - `preserve BEFORE S0_BASELINE`(인자 2개): 기준값 16개를 출력하고, task 항목 4종이 모두 없음을 확인한다.
      - `preserve BEFORE S1_WORKTREE_CREATED`(인자 2개): 기준값 16개와 TASK_WT_HEAD·TASK_BRANCH를 출력한다. task worktree 항목과 local branch는 정확히 1개씩, remote task ref는 없어야 한다.
      - `preserve AFTER S1_WORKTREE_CREATED <기준값 16개> <X>`(인자 19개)
      - `preserve AFTER S2_PUSHED <기준값 16개> <X>`(인자 19개)
      - `preserve AFTER S3_MAIN_FETCHED <기준값 16개> <X> <M>`(인자 20개)
      - 개수나 형식이 다르면 사용 오류(종료 코드 2)다.
    - BEFORE 판정(S0_BASELINE, S1_WORKTREE_CREATED): 다음을 모두 만족할 때만 RESULT=RECORDED이며, 아니면 FAIL → STOP이다.
      - 두 worktree의 status가 0줄(PRESERVED_CLEAN=YES)
      - 두 HEAD가 고정 기대값과 일치(PRESERVED_HEADS_OK=YES)
      - 단계별 task 항목 조건(S0: TASK_ABSENT=YES, S1: TASK_SHAPE_OK=YES)
      - dirty 상태는 기준으로 채택하지 않는다.
    - AFTER의 16개 기준값 인자도 같은 조건(status 0, 고정 HEAD)을 만족하지 않으면 USAGE_ERROR → STOP이다.
    - BEFORE 해시·목록, C1, 구현 해시는 계속 실행 인자로 받는다.
    - AFTER 판정(모두 만족하면 RESULT=PASS):
      - 기준값 1–12가 현재 값과 같아야 한다.
      - task 항목:
        - S1: worktree 항목이 정확히 1개(줄은 정확히 "worktree C:/MoneyLab-auto-10", "HEAD X", "branch refs/heads/codex/auto-10-controlled-read-diagnose"), local branch = X, remote task ref 없음
        - S2·S3: worktree HEAD = local branch = remote task ref = X
      - origin/main:
        - S1·S2: 현재 값(없으면 NONE)이 기준값 16과 같다.
        - S3: 현재 값 = M이어야 한다(기준값 16이 NONE이었어도 S3에서는 M이 있어야 한다).
      - origin/HEAD:
        - S1·S2: STATE·SYMREF·OBJECT가 모두 기준값 13–15와 같다.
        - S3, 기준 STATE = ABSENT: 현재도 없어야 한다.
        - S3, 기준 SYMREF = refs/remotes/origin/main: 현재 SYMREF가 같고 OBJECT = M.
        - S3, 그 밖의 SYMREF 또는 symref 없는 직접 ref: STATE·SYMREF·OBJECT 모두 기준과 같다.
        - 예상 밖의 생성·삭제·대상 변경은 실패다.
    - AFTER 출력: 기준값 1–12의 항목별 <KEY>_MATCH, UNEXPLAINED_DIFF(목록 이름만), TASK_SHAPE_OK, 기준값 13–16의 현재 값 NOW_<KEY>, ORIGIN_MAIN_OK, ORIGIN_HEAD_OK, RESULT.
  - M10 merge-check `<I> <M>`(인자 2개, 각 40hex)
    - TARGET_WORKTREE에서 읽기 전용 git만 쓴다: rev-parse, rev-list --parents, merge-base, diff --name-only, `merge-tree --trivial-merge`(--write-tree 없음, 쓰기 없음).
    - 검사 내용은 POST_MERGE_AUDIT의 E-1–E-6이다.
    - 출력: E1_ORIGIN_MAIN_EQ_M, E2_PARENTS_BASE_HEAD, E3_BASE_IS_MERGE_BASE, E4_TREE_EQUAL, E5_DIFF_EMPTY, 그리고 E-6을 실행한 경우 E6_RETURNCODE, E6_STDOUT_BYTES, E6_STDERR_BYTES, E6_MERGE_TREE. E-6을 실행하지 않으면 E6_MERGE_TREE=NOT_RUN.
    - 판정: E-1–E-6 모두 통과하면 RESULT=PASS, 그 밖은 FAIL.

## RECORDS (TARGET_WORKTREE 아래 ignored 경로, create-new)

- 디렉터리(순서대로 처리): data, data/processed, data/processed/auto10, data/processed/auto10/baseline, data/processed/auto10/precommit
  - M2 결과가 DIRECTORY이고 REPARSE_POINT=NO면 그대로 쓴다.
  - ABSENT면 독립 호출 `mkdir <경로>`(-p 없음) 1회 뒤 M2로 DIRECTORY(REPARSE_POINT=NO)를 확인한다.
  - FILE·LINK·REPARSE·OTHER·QUERY_ERROR면 STOP한다.
- 파일:
  - data/processed/auto10/baseline/collect_base.txt
  - data/processed/auto10/precommit/collect_precommit.txt
  - data/processed/auto10/precommit/diff_stat.txt
- 각 파일은 쓰기 전에 M2로 ABSENT를 확인한다. 아래 정확한 형태만 명령 체인 금지의 예외로 허용한다.
  - `set -C && .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q > data/processed/auto10/baseline/collect_base.txt`
  - `set -C && .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q > data/processed/auto10/precommit/collect_precommit.txt`
  - `set -C && git diff --stat <CANONICAL_BASE_SHA> > data/processed/auto10/precommit/diff_stat.txt`
- ignore 확인: WS-B에서 M3 `data/processed/auto10/x` → IGNORED. 아니면 STOP한다.
- 기록 파일은 비권위 실행 기록이다. 내용 전체는 채팅에 출력하지 않는다(M8 요약과 sha256만).

## WS_A (WORKSPACE_SETUP PART=WORKTREE, SETUP_SESSION_ROOT 세션, 독립 호출)

- WS-A0: audit_tools.py sha256 = AUDIT_TOOLS_SHA256
- WS-A1 사전 조건:
  - `pwd -W` → C:/MoneyLab-auto-09
  - C:/MoneyLab-auto-09 HEAD·tree·status 빈 출력
  - N1 `git -C C:/MoneyLab-auto-09 ls-remote origin refs/heads/main` → b88cb267…
  - N2 `git -C C:/MoneyLab-auto-09 ls-remote origin refs/heads/codex/auto-10-controlled-read-diagnose` → 빈 출력
  - `cat-file -t <base>` → commit, base tree → CANONICAL_BASE_TREE
  - `show-ref --verify --quiet refs/heads/codex/auto-10-controlled-read-diagnose` → 명시적 `Exit code 1`
  - M2 `C:/MoneyLab-auto-10` → ABSENT
  - `C:/MoneyLab-auto-09/.venv/Scripts/python.exe --version` → `Python 3.14.8`
- WS-A2: M9 preserve BEFORE S0_BASELINE
- WS-A3: `git -C C:/MoneyLab-auto-09 worktree add -b codex/auto-10-controlled-read-diagnose C:/MoneyLab-auto-10 b88cb267ed993ddf55657518a37b03b924fcce27`
  - 확인: 새 HEAD = base, 새 worktree status 빈 출력, M2 `C:/MoneyLab-auto-10/docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE` → ABSENT
- WS-A4: M3 `.venv/x` → IGNORED(CHECK_PYTHON은 auto-09 venv. git -C 대상은 C:/MoneyLab-auto-10)
- WS-A5: `C:/MoneyLab-auto-09/.venv/Scripts/python.exe -m venv C:/MoneyLab-auto-10/.venv`, 이어서 `C:/MoneyLab-auto-10/.venv/Scripts/python.exe --version` → `Python 3.14.8`
- WS-A6: M9 preserve AFTER S1_WORKTREE_CREATED X=base
- 보고 후 멈춘다. 사용자가 C:/MoneyLab-auto-10에서 새 세션을 시작한다.

## WS_B (WORKSPACE_SETUP PART=C1_ENV, SESSION_ROOT 새 세션, 독립 호출)

- WS-B0: audit_tools.py sha256 확인. 보고에 사용자 /status·/hooks 화면 확인(H1), settings 선언(H2)을 넣는다. H4는 미확인으로 적는다.
- WS-B1:
  - `pwd -W` → C:/MoneyLab-auto-10, HEAD = base, clean
  - `.venv/Scripts/python.exe --version` → `Python 3.14.8`
  - M4 guard-base → S = BASE_BLOB_SHA256, CR_REMAIN 0
- WS-B2: M9 preserve BEFORE S1_WORKTREE_CREATED(이 세션의 보존 기준. 이후 gate의 AFTER 입력)
- WS-B3 계약:
  - Read로 WO_SOURCE를 읽고, Write 1회로 docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/WORK_ORDER.md를 쓴다.
  - M1 contract → PASS
- WS-B4 C1:
  - `git add -- docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/WORK_ORDER.md`
  - `git diff --cached --name-status` → 출력은 상태 A와 그 경로로 이루어진 한 줄
  - M7 INDEX WO_SHA256 → PASS
  - `git commit -m "docs(task): add AUTO-10-CONTROLLED-READ-DIAGNOSE work order" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`
  - commit 직후 다음 명령 전에 멈추고, 사용자에게 승인 창 관측을 묻는다. ASK_OBSERVED가 아니면 관리자 결정을 기다린다.
  - 확인: C1 전체 SHA·parent(base)·tree, `git show --name-status --format= HEAD` → A 1개, M7 HEAD WO_SHA256 → PASS, clean
- WS-B5 설치(N3, N4):
  - `.venv/Scripts/python.exe -m pip install --no-binary=mypy --no-cache-dir -r requirements-dev.txt`
  - `.venv/Scripts/python.exe -m pip install -e . --no-deps`
  - 판정: 출력에 `ERROR`가 없고 마지막 줄이 `Successfully installed`로 시작한다.
- WS-B6 버전(출력 기반):
  - `pip check` → `No broken requirements found.`
  - `-m mypy --version` → `mypy 2.4.0 (compiled: no)`
  - `-m ruff --version` → `ruff 0.17.2`
  - `-m pytest --version` → `pytest 9.1.1`
- WS-B7 기록: RECORDS의 디렉터리 처리와 M3 `data/processed/auto10/x` → IGNORED, 그다음 BASELINE collect 파일과 M8 BASELINE 단독 확인(형식·개수)

## IMPLEMENTATION

- 시간: TIME_ACCOUNTING의 IMPLEMENTATION 예산을 따른다.
- 쓰기: Edit·Write는 ALLOWED_FILES에만 쓴다.
  - guard.py는 D11 (a)·(b) Edit 각 1회. 각 Edit 직후 `git status --porcelain=v1` 1회를 실행하고, hook 오류·차단·목록 밖 ASK가 나오면 STOP한다.
  - agent_workflow.md는 D12 Edit 1회.
- CHECK_COMMANDS(SESSION_ROOT):
  - C1 `.venv/Scripts/python.exe -m ruff check --no-cache --select E4,E7,E9,F src tests` → `All checks passed!`
  - C2 `.venv/Scripts/python.exe -m ruff check --no-cache --select E4,E7,E9,F .claude/hooks/guard.py` → `All checks passed!`
  - C3a `.venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache` → `Success:`로 시작하는 줄(pyproject 범위, CI와 같은 범위, controlled_read 미포함)
  - C3b `.venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache src/moneylab/controlled_read` → `Success:`로 시작하는 줄
  - C4 targeted: `.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/test_controlled_read_diagnose.py tests/test_controlled_read_diagnose_guard.py tests/test_controlled_read_precheck.py tests/test_controlled_read_cli.py tests/test_controlled_read_selector.py tests/test_controlled_read_transcript.py tests/test_controlled_read_profiles.py tests/test_controlled_read_store.py tests/test_controlled_read_isolation.py tests/test_agent_guard.py tests/test_skills.py`
  - C5 `.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q`
- 고치는 규칙:
  - 신규 시험과 ALLOWED_FILES 안의 실패는 ALLOWED_FILES만 고친다.
  - 기존 시험 실패(회귀)는 고치지 않고 STOP한다.
  - 예산: BUDGET_FIX 4, BUDGET_SAME_FAIL 2, C5 3회, C4 6회.

## TIME_ACCOUNTING

- 수행 시간 = 측정 구간 합계 − 제외 구간 합계. 모든 시각은 독립 호출 `date -u +%Y-%m-%dT%H:%M:%SZ`의 출력이다.
- 제외 구간:
  - (가) 사용자 재개 대기: Claude가 보고나 질문으로 멈춘 직후 찍은 시각부터, 재개 메시지 뒤 첫 명령 직전 시각까지
  - (나) 권한 창 응답 대기:
    - 실제 응답 대기만 따로 측정할 수 있을 때에만 그 대기를 뺀다. 측정 근거는 하네스나 사용자가 알려 준 시작·종료 시각이다.
    - 따로 측정할 수 없으면 그 명령의 앞뒤 `date -u` 사이 전체를 수행 시간에 포함한다. 이 값은 보수적 상한으로 기록하며, 정확한 순수 실행 시간이라고 쓰지 않는다.
  - 보고에는 수행 시간이 "측정값"인지 "보수적 상한 포함"인지 구분해 적는다.
- IMPLEMENTATION 예산: 그 gate 첫 명령 직전부터 보고 직전까지, 수행 시간 10800초 이하
- CI 예산:
  - N12(gh pr create)가 끝난 직후부터, 필수 job pytest와 비필수 job pytest-linux-experimental이 모두 최종 상태(pass, fail, cancel, skipping)가 되고 Linux 판정이 끝난 직후까지, 수행 시간 3600초 이하
  - 필수 job이 먼저 끝나도 Linux 확인 전에는 측정을 끝내지 않는다.
- 대기 방법:
  - 조회 없이 기다리기만 하는 하네스 대기 기능이 실제로 제공되면, 한 번에 최대 60초까지 쓸 수 있다. 그 대기는 CI 수행 시간에 포함된다.
  - 그런 기능이 없으면, 현재 CI 상태와 N14·N15 사용 횟수·CI 수행 시간을 보고하고 사용자 재개를 기다린다(제외 구간 가).
  - 재개해도 조회 횟수와 누적 시간은 초기화하지 않는다.
  - 같은 종류 조회는 앞 조회 시각으로부터 60초 이상 지난 뒤에만 한다.

## TEST_GATES (합성 tmp_path만, 실제 home·세션 경로 접근 없음)

- T1 S1–S4d 각각(D5의 모든 field_path·expected 쌍):
  - status DIAGNOSE_VIOLATION_FOUND이고 check_id·applicability·field_path·expected·actual_json_type·block_index·item_index·line이 기대값과 같다.
  - 위치 정확성:
    - (가) 위반 앞에 정상 block(또는 item)을 2개 이상 두면, 위반의 block_index·item_index가 실제 위치(예: 3)와 같다.
    - (나) 값이 똑같은 위반 block(또는 item)이 여러 개 있으면, 첫 위반의 index가 보고된다.
    - (다) S4c·S4d처럼 helper가 item_index를 정하고 scan이 block_index와 line을 붙이는 경로에서, 전달 단계가 이미 정해진 값(item_index, 그리고 _user_blocks·_assistant_texts가 정한 block_index)을 덮어쓰지 않는다. 채워지는 것은 None인 칸뿐이다. 앞에 정상 줄을 둔 fixture로 line도 정확한지 확인한다.
- T2 같은 fixture에서 precheck가 FORMAT_UNSUPPORTED와 checks.scan=FAILED를 냄. 위반 없는 fixture에서는 precheck scan PASSED, diagnose는 DIAGNOSE_NO_VIOLATION
- T3 첫 위반 선택:
  - 앞 줄이 우선
  - 한 줄 안에서는 scan 순서(S1 → S2 → S3 → S4a → S4b → S4c·S4d)
  - 한 목록 안에서는 앞 block·item
  - PROFILE ECON-FWD-M20-PREREG/1에서는 S3 계열이 적용되지 않음
- T4 누출 방지:
  - 고유 표식 문자열을 알 수 없는 키, 알 수 없는 type 값, uuid, tool_use_id, text 본문, tool_result 본문에 넣는다.
  - diagnose stdout·stderr 어디에도 표식이 없음
  - 모든 출력 값이 D5 목록과 정수 범위 안에 있음
- T5 고정 prefix:
  - 일치, 해시 불일치, S0 < N, 후행 추가(진단 결과 같음, trailing_bytes_excluded 정확), LF 미정렬. 불일치와 LF 미정렬이 함께 있으면 MISMATCH.
  - N 경계 0·67108864·67108865, 대문자 hex
  - S0 > 64 MiB(N ≤ 64 MiB):
    - 실제 파일은 작게 만든다.
    - monkeypatch로 diagnose가 쓰는 collect.check_tree_path 결과와 transcript._fstat 결과를 같은 st_dev·st_ino와 같은 큰 st_size(64 MiB + 1 이상)를 가진 stat 대용 객체로 바꾼다. 경로 검사 단계와 열린 handle의 메타데이터가 일치하도록 한다.
    - transcript._read_exactly를 감싼 spy로 요청 크기가 N이고, 반환 바이트 수가 N 이하임을 단정한다.
    - 결과: diagnose는 진단을 끝내고, observed_size_at_open = 큰 값, trailing_bytes_excluded = 큰 값 − N.
    - 같은 seam에서 precheck(open_session)는 기존대로 SESSION_LIMIT_EXCEEDED여야 한다.
- T6 시간 초과와 재해시:
  - _monotonic seam으로 열기 중(G3b), scan 중(G4c, 재해시 없음), 재해시 전·후(G5) 시간 초과를 만든다.
  - _before_rehash·_fstat seam으로 TRUNCATED·CHANGED·UNREADABLE을 만든다.
  - 위반이 있어도 status는 재해시 코드이고 violation은 null
  - 모든 실패 경로에서 handle이 닫힘
- T7 기록·파일 생성 없음: 실행 전후 tmp_path와 repo `data/processed/controlled_read/`의 파일 목록이 같음
- T8 링크·경로 방어: 세션 경로 구성요소가 링크·비정규 파일이면 SESSION_PATH_INVALID, 없으면 SESSION_NOT_FOUND
- T9 회귀(기준은 기존 계약의 실제 동작. 출처 미확인 코드 사본은 쓰지 않음):
  - (a) 기존 시험 파일 변경 없이 전체 통과
  - (b) 골든 시험(기대 문서는 AUTO-08 D14·ERRATA-001 E1.2, AUTO-09 D7·D9 키 규칙으로 시험에 리터럴로 적음):
    - S1·S2(GLOBAL): run(assistant 선택자)과 run(tool_result 선택자) 모두 FORMAT_UNSUPPORTED, prefix_check MATCHED. precheck도 FORMAT_UNSUPPORTED
    - S3a·S3b·S3c(SELECTED_ENTRY_ONLY):
      - 위반이 대상 assistant 항목에 있으면 run FORMAT_UNSUPPORTED
      - 위반이 비대상 assistant 항목에 있고 대상이 정상이면 run SUCCEEDED(values는 시험에 리터럴로 적은 기대 본문의 sha256·bytes·lf)
      - tool_result 선택자 run은 S3 위반에 영향받지 않음
      - precheck(WO)는 모두 FORMAT_UNSUPPORTED
    - S4a(SELECTOR_KIND_DEPENDENT):
      - tool_result 선택자 run은 FORMAT_UNSUPPORTED
      - assistant 선택자 run은 대상이 정상이면 SUCCEEDED
      - precheck(WO·PREREG)는 FORMAT_UNSUPPORTED
    - S4b·S4c·S4d(SELECTED_ENTRY_ONLY):
      - 대상 tool_result block이면 run FORMAT_UNSUPPORTED
      - 비대상 block이고 대상이 정상이면 run SUCCEEDED
      - assistant 선택자 run은 영향받지 않음
      - precheck는 FORMAT_UNSUPPORTED
  - (c) 각 FormatViolation 경로를 `pytest.raises(ControlledReadError)`로 잡았을 때 code == "FORMAT_UNSUPPORTED", detail == DETAILS 문구, args == ("FORMAT_UNSUPPORTED",)
  - (d) run(["diagnose", …]) → diagnose/1, run(["diagnosex"]) → result/1 ARGUMENT_INVALID, run(["scan"]) → result/1 ARGUMENT_INVALID
- T10 guard(새 시험 파일):
  - D1 정확한 형태는 ASK이고 reason이 D11 문구와 같음(N = 1, 67108864, PREREG 프로필, task 64자)
  - DENY(controlled-read-form): N = 0, 67108865, 99999999, 012, 9자리, 대문자 hex, 63자리 hex, 옵션 순서 변경·누락·중복·추가, `=` 형태, 따옴표, 탭, 체인·redirect, 다른 실행 파일·-m 표기, task 65자, PowerShell 호출
  - 기존 run·status·precheck 형태의 판정과 reason은 바뀌지 않음
  - hook 프로세스 ASK 출력은 JSON이고, DENY는 exit 2

## PRECOMMIT_AUDIT (읽기와 감사만)

- `git diff --name-status <base>`와 PROTECTED 판정
- `git diff --check` → 빈 출력
- RECORDS의 diff_stat 파일 생성, 그 sha256과 줄 수
- DIFF_SHAPE: Read로 `git diff <base> -- src/moneylab/controlled_read/transcript.py` 출력을 확인한다. 삭제·변경 줄이 D3 (b)·(c)·(d)에 열거한 줄뿐이고, 추가 줄은 (a)–(d) 범위뿐이어야 한다. 출력이 잘리면 STOP한다.
- Grep: `src/moneylab/controlled_read/__main__.py`의 `except ControlledReadError`가 exc.code와 STORE_FAILED 전용 속성만 쓰는지 확인
- skip·xfail 추가 0: 신규 시험 두 파일에서 `pytest.mark.skip`, `skipif`, `xfail`, `pytest.skip(`, `pytest.xfail(` Grep 결과 0
- collect: PRECOMMIT collect 파일 생성, M8 PRECOMMIT → PASS
- M5 worktree-bytes → 형식 PASS. 출력 S 7개를 AUDIT_S로 확정해 보고한다(guard 포함).
- SYNTHETIC_ESCAPE_AUDIT:
  - Read로 tests/test_controlled_read_diagnose.py와 tests/test_controlled_read_diagnose_guard.py를 끝까지 읽는다. 필요한 경우 범위를 나눠 읽는다.
  - 비ASCII 합성 입력을 만드는 문자열·fixture 표현이 명시적 이스케이프를 사용하는지 확인한다. 합성 입력을 다른 표현이나 결합으로 생성하면 관련 정의까지 확인한다.
  - 주석·설명문에 비ASCII가 있다는 이유만으로 위반으로 판정하지 않는다.
  - 위반이 0개이고 관련 표현을 모두 확인했을 때만 SYNTHETIC_ESCAPE_AUDIT=PASS다. 누락·모호함·잘린 출력·위반이 있으면 STOP하고, 감사 중 자동 수정하지 않는다.
  - 보고에는 확인한 파일·줄 위치와 판정만 적는다. M5가 이 검사를 대신했다고 쓰지 않는다.

## COMMIT

- `git add -- <ALLOWED_FILES 7개 경로>`
- M6 INDEX <AUDIT_S 7개> → PASS
- `git diff --cached --name-status` → ALLOWED_FILES와 표기 일치
- `git commit -m "feat(automation): add controlled_read diagnose" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. ASK 관측 규칙은 WS-B4와 같다.
- 확인: 구현 커밋 I 전체 SHA·parent(C1)·tree, `git show --name-status --format= HEAD` → ALLOWED_FILES 7개, M6 HEAD <AUDIT_S> → PASS, clean

## CLEAN_COMMIT_E2E

- HEAD = I, clean
- M6 HEAD <AUDIT_S> → PASS
- C4 1회
- 실행 뒤 `git status --porcelain=v1 --untracked-files=all` 빈 출력

## PUSH

- 사전:
  - N5 `git ls-remote origin refs/heads/main` → base
  - N6 `git ls-remote origin refs/heads/codex/auto-10-controlled-read-diagnose` → 빈 출력
- N7 `git push -u origin codex/auto-10-controlled-read-diagnose` 1회
- 사후:
  - N8 `git ls-remote origin refs/heads/codex/auto-10-controlled-read-diagnose` → I
  - M9 preserve AFTER S2_PUSHED X=I(WS-B2 기준)

## PR_CI

- 사전:
  - N9 `git ls-remote origin refs/heads/main` → base. 다르면 STOP한다.
  - N10 `git ls-remote origin refs/heads/codex/auto-10-controlled-read-diagnose` → I
  - N11 `gh pr list -R swk3169/MoneyLab --head codex/auto-10-controlled-read-diagnose --base main --state open --json number,headRefOid` → `[]`(같은 head/base의 열린 PR만 본다)
- N12 `gh pr create -R swk3169/MoneyLab --base main --head codex/auto-10-controlled-read-diagnose --title <승인 제목> --body <승인 본문>` 1회
- 사후 N13 `gh pr view <N> -R swk3169/MoneyLab --json number,state,isDraft,baseRefName,headRefName,headRefOid,commits,files,mergeable` 1회
  - PR 범위: 커밋은 C1과 I, 파일은 ALLOWED_FILES ∪ {계약 WORK_ORDER.md}
- CI 대기: 시간·간격·대기 방법은 TIME_ACCOUNTING의 CI 예산과 대기 방법을 따른다. 조회 횟수:
  - N14 `gh pr checks <N> -R swk3169/MoneyLab` 최대 40회
  - N15 `gh run list -R swk3169/MoneyLab --branch codex/auto-10-controlled-read-diagnose --json databaseId,headSha,name,status,conclusion` 최대 10회
  - N16 `gh run view <run> -R swk3169/MoneyLab --json jobs` 최대 2회
  - N17 `gh run view <run> -R swk3169/MoneyLab --job <linux job id> --log-failed` 최대 1회(Linux 판정 전용)
- CI_STATES(gh pr checks 출력):
  - 판정은 출력을 정상적으로 파싱한 표의 상태 열로 한다. 표시된 0이 아닌 종료 코드는 기록하고, 표가 완전히 파싱되면 도구 오류로 보지 않는다.
  - REQUIRED_PENDING / NONREQUIRED_PENDING: 해당 job이 pending·queued·in_progress로 파싱되면 대기한다(정상 상태 보고).
  - REQUIRED_PASS: pytest가 pass로 파싱됨
  - REQUIRED_FAIL: pytest가 fail·cancel로 파싱됨 → STOP
  - NONREQUIRED_DONE_FAIL: pytest-linux-experimental이 fail로 파싱됨 → Linux 판정 대상(실패가 아님)
  - UNPARSED: 표가 없거나 알려지지 않은 응답 → 원문을 짧게(최대 5줄) 보고하고 보류한다. 대기로 바꾸지 않고, 자동 재조회하지 않는다. 다음 조회는 사용자 재개 뒤에만 한다(조회 횟수와 시간은 초기화하지 않음).
  - 인증 실패, 네트워크·통신 오류, 명령 구문 오류 → STOP. 대기로 바꾸지 않고 재시도하지 않는다.
  - "no checks"류 안내 문구는 확인된 문구가 없으므로 별도 상태로 정의하지 않는다. 그런 출력은 UNPARSED다.
- CI 완료: 두 job(pytest, pytest-linux-experimental)이 모두 최종 상태로 파싱되고 Linux 판정이 끝났을 때만 CI 측정을 끝낸다.
- Linux 판정:
  - N17 출력의 실패 node ID 집합이 NONREQUIRED_CI_BASELINE 2건의 부분집합이면 NO_NEW_LINUX_REGRESSION
  - 다른 실패가 있으면 보고하고 STOP(사용자 결정)
  - Linux job이 pass이면 N17은 생략한다.
- 큰 CI 출력:
  - 하네스가 출력을 파일로 저장했다고 알리면, 그 호출 반환값에 적힌 정확한 파일 하나만 Read로 나눠 연다(offset·limit 최대 100줄, 최대 30회).
  - 실패 node ID와 요약 줄만 보고한다.
  - 다른 tool-results·세션·debug 파일의 검색·열람은 금지한다.
  - 30회 안에 판정하지 못하면 STOP한다.

## MERGE

- 사전(§13 1–7):
  - N18 `gh pr view <N> -R swk3169/MoneyLab --json state,isDraft,baseRefName,headRefName,headRefOid,commits,files,mergeable`
  - N19 `gh pr checks <N> -R swk3169/MoneyLab` 1회 → REQUIRED_PASS와 Linux 판정 유지
  - N20 `git ls-remote origin refs/heads/main` → base
  - N21 `git ls-remote origin refs/heads/codex/auto-10-controlled-read-diagnose` → I
- N22 `gh pr merge <N> -R swk3169/MoneyLab --merge --match-head-commit <I>` 1회
- 사후 N23 `gh pr view <N> -R swk3169/MoneyLab --json state,mergeCommit,mergedAt` 1회 → state MERGED, merge commit M

## POST_MERGE_AUDIT

- N24 `git fetch origin main` 1회(--all·--prune 없음)
- audit_tools.py sha256 = AUDIT_TOOLS_SHA256을 확인한다.
- M10 merge-check `<I> <M>` 1회. 아래 E-1–E-6을 모두 확인한다.
  - E-1 `rev-parse origin/main` = M
  - E-2 `rev-list --parents -n 1 M`의 출력이 정확히 `M CANONICAL_BASE_SHA I`(parent 순서 base·승인 head)
  - E-3 `merge-base CANONICAL_BASE_SHA I` = CANONICAL_BASE_SHA
  - E-4 `rev-parse M^{tree}` = `rev-parse I^{tree}`
  - E-5 `diff --name-only I M`이 빈 출력
  - E-6 merge-tree 재계산(docs/tasks/README.md §3):
    - `git merge-tree --trivial-merge CANONICAL_BASE_SHA I CANONICAL_BASE_SHA`
    - shell=False·capture_output=True로 실행하며, returncode = 0, stdout = 빈 바이트, stderr = 빈 바이트여야 통과다.
    - 전제는 E-2와 E-3이다. base가 I의 조상이고 다른 쪽이 base 그대로일 때, 결과가 첫 branch인 I와 같아서 trivial-merge 출력에서 생략된다는 성질을 쓴다.
    - E-2·E-3 중 하나라도 통과하지 않으면 E-6은 실행하지 않고 FAIL이다.
    - `--write-tree`, index·ref·객체 쓰기는 허용하지 않는다.
- E-6은 §3이 요구하는 재계산이다. E-1–E-5는 함께 확인하는 증거이며, E-6을 대신하지 않는다.
- M9 preserve AFTER S3_MAIN_FETCHED(WS-B2 기준값 16개, X = I, M)
- branch·worktree를 보존하며 삭제는 없다. TARGET_WORKTREE는 clean이어야 한다.
- 근거 등급: ChatGPT가 공식 Git 문서와 AUTO-09 객체로 이 형식을 확인했다(INDEPENDENT). AUTO-10의 E-6 성공은 미리 확인된 것이 아니다.

## COMPLETE

- 최종 보고만 한다(파일 보관 없음).
- 보고 항목:
  - base·C1·I·M의 SHA·parent·tree
  - POST_MERGE_AUDIT E-1–E-6(M10 merge-check)과 M9 S3 결과
  - CI 결과(필수 job, Linux 판정, 기준 2건과의 비교)
  - 모든 단계의 ASK 상태, 예산 사용량, DEVIATIONS·ISSUES·PROPOSED_ERRATA
  - 검증 한계: OS 종료 코드 0 미표시, H4 미관측, Linux 기준은 AUTO-09 결과 재사용, merge-tree 처리 방식
- 실제 세션 진단은 별도 계약으로 남긴다. AUTO-08-FIRST-USE는 STOP 상태를 유지한다.
- COMPLETE_PASS = YES / NO

## NETWORK

- 이 문서에 번호를 붙인 N1–N24만, 해당 gate 승인으로, 적힌 횟수 안에서 쓴다.
- N3·N4는 PyPI와 빌드 의존성 다운로드다.
- 그 밖의 네트워크는 금지한다. 실패하면 STOP하고 재시도하지 않는다.

## EXPECTED_ASK

- audit_tools.py 실행(guard `untracked-script` 등, 또는 작업 디렉터리 밖 경로 권한 창)
- WS-A3 worktree add(나타나는 경우)
- WS-A5 venv 생성(나타나는 경우)
- WS-B3 WORK_ORDER.md Write(`task-contract`)
- guard.py·agent_workflow.md Edit(settings `Edit(/.claude/**)`, `protected-edit`)
- `mkdir`(data/processed 아래, 나타나는 경우)
- `git commit` 2회, `git push`, `gh pr create`·`gh pr merge`(`github`), `pip install`(`deps`)
- 목록 밖 ASK, 거절, 무응답은 STOP이다.

## FORBIDDEN_ACTIONS

- 실제 세션·debug·tool-results 열람(PR_CI 큰 출력 예외 1개 파일 제외), 실제 home 경로를 쓰는 실행
- 실제 세션에서 diagnose·precheck·run·status 실행
- D2 대상 변경, ALLOWED_FILES 밖·PROTECTED 변경, 기존 시험의 수정·삭제·skip·xfail
- guard D11 밖 변경, settings·hook 등록 변경, 인라인 import·명령 은닉·문자열 분할·설정 완화
- AUDIT_TOOLS 밖의 검사 프로그램 실행·생성, audit_tools.py의 수정·교체, 표준 입력 heredoc으로 프로그램 전달
- 명령 체인(`&&`, `;`, `|`). 예외는 RECORDS의 정확한 3형태뿐이다.
- `git add .`·`-A`, `--no-verify`, amend, force push, reset·restore·stash·clean·rebase·cherry-pick, fetch --all·--prune, branch·worktree 삭제
- PRESERVED_WORKTREES의 변경, 그리고 그 파일 내용·기록·data 열람. 예외는 AUDIT_TOOLS M9가 하는 git 메타데이터 조회와 C:/MoneyLab-auto-09 설치 메타데이터 2파일(direct_url.json, __editable__.moneylab-0.3.0.pth)의 원바이트 sha256 계산뿐이다.
- AUTO-08/09·FIRST-USE 기록 변경, 연구 공개 백업 진행

## STOP_CONDITIONS

- base·HEAD·tree·cwd 불일치, WO·AUDIT_TOOLS 해시 불일치
- 변경 판정(단계별 허용 상태가 아니면 STOP):
  - PRESERVED_WORKTREES: 모든 단계에서 status 0줄, HEAD·tree 불변
  - TARGET_WORKTREE:
    - WS-A3 직후·WS-B1·WS-B2: tracked·untracked·staged 0
    - WS-B3 Write 뒤 add 전: untracked는 docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/WORK_ORDER.md 1개뿐, tracked·staged 0
    - WS-B4 add 뒤 commit 전: staged는 그 경로의 A 1개뿐, 그 밖 0
    - C1 뒤(WS-B4 확인부터 IMPLEMENTATION 시작 전까지): 0(ignored 기록·venv는 대상 아님)
    - IMPLEMENTATION 중과 끝: staged 0. tracked 변경은 ALLOWED_FILES의 M 4개 안, untracked는 A 3개 안
    - PRECOMMIT_AUDIT: IMPLEMENTATION 끝 상태와 같고, M5 출력 W·S가 감사 중 바뀌지 않음
    - COMMIT add 뒤 commit 전: staged = ALLOWED_FILES 7개, 그 밖 0
    - 구현 커밋 뒤 모든 단계: 0
- EXIT_CRITERIA 미충족, 결과 불명·출력 잘림·파일 우회(PR_CI 예외 절차 밖)
- 회귀(기존 시험 실패), DIFF_SHAPE 위반, PROTECTED diff, collect REMOVED > 0 또는 신규 파일 밖 추가
- 예산 초과(IMPLEMENTATION 10800초, CI 3600초, 조회 횟수, 고치는 횟수)
- guard DENY, hook 오류, 목록 밖 ASK, 거절·무응답, commit 뒤 ASK 미관측(관리자 결정 대기)
- REQUIRED_FAIL, Linux 신규 실패, §13 사전 검증 실패, merge 결과 불일치, preserve UNEXPLAINED_DIFF
- 계약 모순, 상위 규칙과 충돌
- 공통: 재시도·되돌리기·정리 없이 분류, 마지막 PASS 단계, 실제 HEAD·tree를 보고하고 별도 승인을 기다린다.

## REQUIRED_EVIDENCE

- GIT_VERIFIABLE: base·C1·I·M의 SHA·parent·tree, 파일 집합, blob 내용 sha256, merge parent 순서
- CLAUDE_REPORTED: 검사 판정 줄, AUDIT_TOOLS 출력, collect 비교, preserve 결과, `pwd -W`·`date -u`, 표시된 종료 코드 또는 미표시
- INDEPENDENT: 사용자 /status·/hooks 확인, ASK 창 관측(사용자 진술), GitHub CI 결과, ChatGPT 검토
- 검증 한계: OS 종료 코드 0 미표시, H4 미관측, Linux 기준은 AUTO-09 확인 결과 재사용

## REQUIRED_REPORT

- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- 셸 cwd, HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, clean, diff --check
- 검사 판정 줄과 표시된 종료 코드 또는 "미표시", ASK 상태, 예산 사용량(`date -u` 기준)
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES / NO, READY_FOR_<NEXT_GATE> = YES / NO

## AFTER_COMPLETE (이 task 밖, 참고)

AUTO-08-FIRST-USE 세션의 최초 진단은 별도 계약과 승인으로 한다. 그 계약은 다음을 정해야 한다.
- 실행 루트(diagnose가 설치된 커밋과 venv)
- 대상 PROJECT_KEY·SESSION
- 기대 prefix(44113503바이트, 5433d3eb2ce924e22e2cbd6e71d6e4d77f35b2e1e102825b2d4b73cfef2351f2)
- CONTROLLED_READ_DIAGNOSE_AUTHORIZATION 1건, 대상 세션 비활성 확인, 그 세션의 hook 확인
- 지원 범위 변경은 진단 결과를 수락한 뒤 다시 별도 task로 한다.
