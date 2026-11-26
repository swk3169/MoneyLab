# ERRATA-001: AUTO-10-CONTROLLED-READ-DIAGNOSE — 격리 시험 모듈 목록, applicability, S3b 비문자열 type, ERRATA_COMMIT 절차

이 파일은 불변이다. 고정(Ce) 후 수정하지 않는다. 추가 정정은 ERRATA-002 이후 번호로만 한다.

## Metadata

ERRATA_ID: ERRATA-001
TASK_ID: AUTO-10-CONTROLLED-READ-DIAGNOSE
STATUS: ACCEPTED
ACCEPTED_BY: 저장소 관리자(현재 대화 사용자), 2026-11-26
APPLIES_TO: docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/WORK_ORDER.md (sha256 a147275224462d7cd3493cb2231b16468a1a0f0e5a64f215c00838a52d47abaf, C1 740c142b10c5eceeaf91012f6c2e276d7f57100b)
ERRATA_PATH: docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md
ERRATA_SOURCE: C:/Users/USER/.codex/visualizations/2026/11/10/01a1c608-854b-77c3-9025-e5fba3a281a8/MoneyLab-approvals/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.review.md
ERRATA_COMMIT_PARENT: 740c142b10c5eceeaf91012f6c2e276d7f57100b
AUDIT_TOOLS_PATH: C:/Users/USER/.codex/visualizations/2026/11/10/01a1c608-854b-77c3-9025-e5fba3a281a8/MoneyLab-approvals/AUTO-10-CONTROLLED-READ-DIAGNOSE/audit_tools.errata-001.review.py
AUDIT_TOOLS_SHA256: 0c970e1fb3f60bba7c26268031e4f3769844e2b7938b76fa3160387f26af8233

## 사유

- R1 D8·ALLOWED_FILES는 새 모듈 src/moneylab/controlled_read/diagnose.py를 요구하고, D8·T9(a)는 기존 시험 무변경 통과를 요구한다. PROTECTED인 tests/test_controlled_read_isolation.py:31-33은 패키지 *.py 집합이 정확히 6개라고 단정하므로 두 조건은 동시에 만족할 수 없다(IMPLEMENTATION 진입 직후 수정 전 STOP).
- R2 T1은 violation의 applicability를 요구하지만 D5 허용 목록에 그 필드가 없다.
- R3 transcript.py:261의 S3b 조건 `block.get("type") not in ASSISTANT_BLOCK_TYPES`는 type이 list·dict이면 TypeError(unhashable)를 내어 run·precheck·diagnose가 정의되지 않은 예외로 끝나고 위치를 보고하지 못한다.
- R4 기존 M1·M7·M2는 WORK_ORDER.md와 고정 경로만 다루므로 ERRATA 파일 감사 모드가 없다.

## E1 격리 시험 (ALLOWED_FILES, PROTECTED_FILES, D8, T9 정정)

E1.1 ALLOWED_FILES 8번째에 `M tests/test_controlled_read_isolation.py`를 추가한다. 기존 7개 순서는 유지한다. 합계 M 5개, A 3개.
E1.2 이 파일에 허용하는 변경은 다음 둘뿐이다.
  - (a) test_package_has_exactly_the_planned_modules의 기대 집합에 "diagnose.py" 하나 추가
  - (b) OWN_ALLOWED에 "moneylab.controlled_read.diagnose" 하나 추가
  그 밖의 시험 함수, 검사 조건, 허용 목록(STDLIB_ALLOWED·FORBIDDEN_LOADED 포함), 프로세스·API 금지 조건, 직렬화 시험은 바꾸지 않는다.
E1.3 PROTECTED_FILES의 "CANONICAL_BASE_SHA에 이미 있는 tests/** 전체"에서 이 파일은 E1.2의 두 변경에 한해서만 예외다. 그 밖의 줄 변경은 PROTECTED 위반이다.
E1.4 diagnose.py는 기존 _modules() 수집(PACKAGE.glob("*.py"))에 포함되어 모든 격리 검사를 받는다. 하위 패키지로 옮기거나 수집에서 빼는 방법은 금지한다.
E1.5 D8의 "기존 test_controlled_read_isolation.py 통과"와 T9(a)의 "기존 시험 파일 변경 없이 전체 통과"는 "E1.2의 두 변경 외에는 기존 시험 파일 변경 없이 전체 통과"로 읽는다.

## E2 applicability (D4, D5 정정)

E2.1 D5의 violation 객체에 applicability 필드를 둔다. 값은 D4의 고정 등급 GLOBAL, SELECTOR_KIND_DEPENDENT, SELECTED_ENTRY_ONLY 중 하나이고, check_id마다 고정이다.
  - S1·S2: GLOBAL
  - S4a: SELECTOR_KIND_DEPENDENT
  - S3a·S3b·S3c·S4b·S4c·S4d: SELECTED_ENTRY_ONLY
E2.2 출력 전 검증(D5)은 applicability가 check_id의 고정 값과 같은지도 확인한다. 다르면 ValueError(출력 없음).
E2.3 violation 객체의 키는 check_id, applicability, field_path, expected, actual_json_type, block_index, item_index, line이다. 그 밖의 필드, null 조건, 오류 우선순위, D7 상태표는 바꾸지 않는다.

## E3 S3b 비문자열 type (D2, D3, D5, T9 정정)

E3.1 transcript._assistant_texts의 S3b 조건(기준 261행)에 한해 type의 문자열 여부 선행 검사를 허용한다. 판정 순서:
  - (1) block이 dict가 아니면 S3b, field_path assistant.content[], expected object
  - (2) block.get("type")이 str이 아니면 S3b, field_path assistant.content[].type, expected listed_block_type, actual_json_type은 _json_type 결과(missing, null, bool, number, array, object)
  - (3) 문자열이고 ASSISTANT_BLOCK_TYPES에 없으면 S3b, 같은 field_path·expected, actual_json_type string_unlisted
  - (4) 그 밖은 기존 동작
  (2)는 (3)의 포함 검사보다 앞서며, 단락 평가로 비문자열 값이 집합 포함 검사에 들어가지 않는다.
E3.2 사용자 입력을 set·frozenset·dict 키로 바꾸거나 해시하지 않는다. 실제 type 값, 키 이름, 본문은 출력하지 않는다. block_index와 line은 D3 (c)·(d)의 반복 인덱스로 정한다.
E3.3 의도된 동작 변경은 하나뿐이다. 기존에 TypeError가 나던 list·dict type은 FORMAT_UNSUPPORTED(FormatViolation)가 된다. 이 변경은 run(assistant 선택자의 대상 항목), precheck scan, diagnose에 같이 적용된다.
E3.4 기존에 FORMAT_UNSUPPORTED였던 입력(type 없음, null, bool, number, 미등록 문자열, block 비객체)은 run·precheck에서 그 결과를 유지하고, diagnose에서는 E3.1 (1)–(3)의 고정 field_path·expected·actual_json_type으로 보고한다. 정상 입력(등록 문자열)의 선택, 추출, 검사 순서, 출력 바이트는 바뀌지 않는다.
E3.5 D2(불변)·D3(b)("조건식은 글자 그대로")·T9(b)(기존 동작 기준)의 보존 조건은 E3.1의 S3b 조건 한 곳만 예외다. DIFF_SHAPE는 261행 조건 변경을 E3.1 형태에 한해 허용하며, 다른 조건식 변경은 여전히 위반이다.
E3.6 합성 시험(tests/test_controlled_read_diagnose.py). assistant content block의 type이 list인 경우와 dict인 경우를 각각, 앞에 정상 block 2개와 정상 줄을 두고 만든다.
  - (a) diagnose: DIAGNOSE_VIOLATION_FOUND, check_id S3b, applicability SELECTED_ENTRY_ONLY, field_path assistant.content[].type, expected listed_block_type, actual_json_type array·object, block_index·line 실제 위치, item_index null
  - (b) precheck(WO): FORMAT_UNSUPPORTED, checks.scan FAILED, prefix_check MATCHED
  - (c) run: assistant 선택자 대상 항목이면 FORMAT_UNSUPPORTED. 비대상 항목이고 대상이 정상이면 SUCCEEDED(리터럴 기대 values). tool_result 선택자 run은 영향 없음
  - (d) 보존: 등록 문자열 type(text, thinking, redacted_thinking, tool_use)은 기존처럼 통과. 미등록 문자열 type은 FORMAT_UNSUPPORTED이고 diagnose는 string_unlisted
  - (e) TypeError가 나지 않고, list·dict type 안에 넣은 고유 표식 문자열이 stdout·stderr 어디에도 없음
  - (f) PREREG/1 profile에서는 S3 계열이 적용되지 않음(T3과 같음)
  T7의 기록·파일 생성 없음은 diagnose 호출에 적용한다. E3.6(c)의 run 시험은 tmp_path 안의 합성 저장소와 기록 경로만 사용하며, 기존 run의 정상 기록 동작을 검증할 수 있다. 실제 home·세션·연구 데이터와 계약 밖 경로에는 접근하거나 쓰지 않는다.

## E4 AUDIT_TOOLS 교체

E4.1 AUDIT_TOOLS_PATH와 AUDIT_TOOLS_SHA256은 이 ERRATA의 Metadata 값으로 바꾼다. CHECK_PYTHON·실행 형식·실행 직전 sha256sum 확인 규칙은 그대로다.
E4.2 이전 판(50d35e12322953f65639bf59a232679e4f65e4170c9c158a2eb05d5064bef9f3)과의 차이는 ALLOWED_FILES 8번째 항목 추가, M5 docstring, M6 인자 9개(INDEX|HEAD + S 8개)와 docstring뿐이다. 다른 모드·상수·판정·경로 허용 목록은 같다.
E4.3 이전 audit_tools.py는 보존하며 Ce부터 실행하지 않는다.
E4.4 새 모드는 없다. ERRATA-001.md 감사는 E5의 Ce 전용 예외로만 한다.

## E5 ERRATA_COMMIT gate (GATE_SEQUENCE 정정)

E5.1 위치: 현재 IMPLEMENTATION STOP(수정 전) 상태에서 ERRATA_COMMIT으로 진입할 수 있다. ERRATA_COMMIT 완료 후 보고하고 멈추며, IMPLEMENTATION 재개에는 E6.5 형식의 별도 승인이 필요하다. 이는 GATE_TRANSITION_RULES의 후퇴가 아니라 이 ERRATA 한 번에 한정한 삽입 단계다.
E5.2 승인 형식:
  `GATE_AUTHORIZATION: AUTO-10-CONTROLLED-READ-DIAGNOSE ERRATA_COMMIT ERRATA=001 WO@740c142b10c5eceeaf91012f6c2e276d7f57100b ERRATA_SHA256=<64hex> ERRATA_SOURCE=C:/Users/USER/.codex/visualizations/2026/11/10/01a1c608-854b-77c3-9025-e5fba3a281a8/MoneyLab-approvals/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.review.md AUDIT_TOOLS_SHA256=0c970e1fb3f60bba7c26268031e4f3769844e2b7938b76fa3160387f26af8233`
  ERRATA_SOURCE는 위 고정 경로다. 원문 존재, 필드와 실행 인자의 문자열 완전 일치를 대조하고, 어긋나면 STOP한다.
E5.3 진입 조건: `pwd -W` → C:/MoneyLab-auto-10, HEAD = 740c142b10c5eceeaf91012f6c2e276d7f57100b, tree = fc97e260f4afc46d1757e63d72f400c8fd3a4e01, tracked·untracked·staged 0, `sha256sum <AUDIT_TOOLS_PATH>` = AUDIT_TOOLS_SHA256.
E5.4 범위: ERRATA-001.md 최초 생성 1회와 문서 전용 커밋 Ce 1개뿐이다. Ce의 parent는 C1이다. 다른 파일 변경, 설치, 시험, 네트워크는 없다.
E5.5 절차(모두 독립 호출. 이 ERRATA가 명시한 예외 외에는 FORBIDDEN_ACTIONS를 그대로 적용):
  - X1 `sha256sum <ERRATA_SOURCE>` → ERRATA_SHA256
  - X2 대상 부재 확인(이 고정 경로 하나에 대한 os.lstat 예외. 정확히 다음 명령):
    ```
    C:/MoneyLab-auto-10/.venv/Scripts/python.exe -I -B -c 'import os, sys
    try:
        os.lstat(sys.argv[1])
    except FileNotFoundError:
        print("PATH_STATE=ABSENT")
        raise SystemExit(0)
    except OSError as exc:
        print("PATH_STATE=QUERY_ERROR", type(exc).__name__)
        raise SystemExit(2)
    print("PATH_STATE=PRESENT")
    raise SystemExit(3)' C:/MoneyLab-auto-10/docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md
    ```
    판정: 출력이 `PATH_STATE=ABSENT` 한 줄일 때만 통과한다. PRESENT, QUERY_ERROR, 그 밖의 출력이나 도구 오류는 STOP이다. 하위 내용이나 링크 대상을 따라 읽지 않는다.
  - X3 Read로 ERRATA_SOURCE를 읽고 Write 1회로 ERRATA_PATH를 쓴다. 이어서 `git status --porcelain=v1 --untracked-files=all` → `?? docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md` 한 줄
  - X4 `sha256sum docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md` → ERRATA_SHA256(작업 파일 원바이트)
  - X5 `git add -- docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md`(줄바꿈 변환 경고는 보고만 한다)
  - X6 `git diff --cached --name-status` → `A`와 그 경로 한 줄
  - X7 `git diff --cached --check` → 빈 출력, 도구 오류 없음
  - X8 `git hash-object -- docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md` → OID_E(`-w` 금지)
  - X9 `git rev-parse :docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md` = OID_E
  - X10 `git commit -m "docs(task): accept AUTO-10-CONTROLLED-READ-DIAGNOSE ERRATA-001" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. commit 직후 다음 명령 전에 멈추고 승인 창 관측을 묻는다(WS-B4와 같은 규칙).
  - X11 사후 확인: `git rev-list --parents -n 1 HEAD` → `<Ce> 740c142b10c5eceeaf91012f6c2e276d7f57100b`, `git rev-parse "HEAD^{tree}"`, `git show --name-status --format= HEAD` → A 1개, `git rev-parse HEAD:docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md` = OID_E, status 빈 출력
E5.6 증거 해석:
  - X1·X4는 외부 정본과 작업 파일의 원바이트 SHA-256이 같음을 입증한다.
  - 외부 정본의 형식 검사(UTF-8 strict, BOM·TAB·NBSP·줄 끝 공백 0, CR 0, 끝 LF 정확히 1개)는 발행 단계에서 끝내며, Ce에서 다시 하지 않는다. 그 결과의 근거 등급은 발행 단계의 형식 검사 결과(CLAUDE_REPORTED)다. 동일 바이트라는 해시 대조가 그 형식 검사 결과를 작업 파일로 이어받는 근거다. 독립 검증을 수행했다고 쓰지 않는다.
  - X8·X9·X11의 OID는 Git 필터(줄바꿈 정규화 등)를 반영한 blob 객체 ID(SHA-1)이며, 원바이트 SHA-256과 다른 값이다. index·commit blob의 content SHA-256은 계산하지 않으며 계산했다고 보고하지 않는다.
  - 이 예외는 ERRATA-001.md 한 파일의 Ce 감사에만 적용한다. 구현 8개 파일의 M5·M6 감사와 WORK_ORDER.md의 M7은 그대로다.
E5.7 STOP: 위 판정 불일치, DENY, 목록 밖 ASK, 도구 오류, 예상 밖 untracked·staged, 해시 불일치. 재시도·되돌리기·정리 없이 보고한다. X2·X8의 실제 guard 판정은 미확인이다. 실행할 때 DENY·도구 오류면 STOP하고, EXPECTED_ASK 안의 ASK는 정상 권한 절차를 따른다.
E5.8 EXPECTED_ASK 추가: X2 인라인 Python(나타나는 경우), X3 Write(`task-contract`), X10 `git commit`, X8 `git hash-object`(나타나는 경우).

## E6 연쇄 정정

E6.1 M5·M6·AUDIT_S·COMMIT·CLEAN_COMMIT_E2E·사후 blob 대조는 ALLOWED_FILES 8개 기준이다. COMMIT의 `git add --`는 8개 경로를 명시하고, `git diff --cached --name-status`와 `git show --name-status --format= HEAD`는 8개다. STOP_CONDITIONS의 "staged = ALLOWED_FILES 7개"와 IMPLEMENTATION의 "M 4개"·"A 3개"는 각각 8개, M 5개, A 3개로 읽는다.
E6.2 M8 PRECOMMIT 판정은 그대로다. REMOVED = 0, ADDED는 tests/test_controlled_read_diagnose.py와 tests/test_controlled_read_diagnose_guard.py에서만 허용한다. 격리 시험 파일의 node ID가 추가·삭제되면 FAIL이다.
E6.3 PRECOMMIT_AUDIT 추가:
  - ISOLATION_DIFF_SHAPE: Read로 `git diff <base> -- tests/test_controlled_read_isolation.py`를 확인해 변경 줄이 E1.2 (a)·(b)를 위한 줄뿐인지 판정한다. 출력이 잘리면 STOP한다.
  - DIFF_SHAPE(transcript.py)는 E3.1의 261행 조건 변경을 허용 범위에 포함한다.
E6.4 PROTECTED 판정(`git diff --name-status <base>`): A는 ALLOWED_FILES의 A 3개, WORK_ORDER.md, ERRATA-001.md. M은 ALLOWED_FILES의 M 5개. 그 밖의 M·D·R·A는 0.
E6.5 계보: C1 → Ce → I. 구현 커밋 I의 parent는 Ce다. IMPLEMENTATION 이후 gate 승인 형식은
  `GATE_AUTHORIZATION: AUTO-10-CONTROLLED-READ-DIAGNOSE <GATE> WO@740c142b10c5eceeaf91012f6c2e276d7f57100b ERRATA-001@<Ce SHA>`
  이다. PR_CI·MERGE의 추가 줄은 Work Order와 같다.
E6.6 PR 범위: 커밋은 C1, Ce, I 3개. 파일은 ALLOWED_FILES 8개 + WORK_ORDER.md + ERRATA-001.md, 합계 10개.
E6.7 바꾸지 않는 것: WORK_ORDER.md, C1, baseline collect(BASELINE_FILE_SHA256 50c5810960f2e451835b44369e8313f3057eb578e38b9a4e18a0cc2224bcc5c4, selected 3780, total 3781, deselected 1. deselected 원인은 미확인), WS-B2 보존 기준값 16개, M9·M10 판정, PRESERVED_WORKTREES 규칙.
E6.8 예산과 시간:
  - 네트워크: N3·N4 사용 횟수를 유지한다. ERRATA_COMMIT은 네트워크를 쓰지 않는다.
  - 고치는 예산: FIX 0/4, C5 0/3, C4 0/6을 이어서 센다.
  - IMPLEMENTATION 수행 시간: 첫 구간은 2026-11-26T08:28:16Z부터 정정 작업 시작 08:31:15Z까지 179초를 보수적 상한으로 집계한다(정확한 STOP 시각은 기록되지 않음). 남은 예산은 10621초다.
  - 정정 준비, 승인 대기, ERRATA_COMMIT은 구현 수행 시간에서 제외한다.

## E7 그 밖

E7.1 이 ERRATA는 상위 규칙, 사전등록, PRESERVED_WORKTREES 규칙, NETWORK 제한, 실제 세션 열람 금지를 바꾸지 않는다. 이 ERRATA 고정에 필요한 예외는 E5에 명시한 ERRATA-001.md의 부재 확인·최초 생성·원바이트 SHA-256 대조·쓰기 없는 Git OID 대조·staging·문서 전용 커밋과 사후 확인에 한정한다. 다른 파일이나 다른 gate로 확대하지 않는다. 그 밖의 FORBIDDEN_ACTIONS는 유지한다.
E7.2 이 ERRATA가 언급하지 않은 Work Order 조항은 그대로다.
E7.3 기존 기록 유지: H1·H4 미확인, C1 ASK_UNVERIFIED, 설치 출력 관리자 한정 수락, 기존 STOP·이탈 기록, AUTO-08-FIRST-USE의 STOP, 연구 공개 백업 보류.
