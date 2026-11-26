# ERRATA-002: AUTO-10-CONTROLLED-READ-DIAGNOSE — 위생 검사 한정 수락, D12 보완, dirty 상태 ERRATA_COMMIT, 운영 전환

이 파일은 불변이다. 고정(Ce2) 후 수정하지 않는다. 추가 정정은 ERRATA-003 이후 번호로만 한다.

## Metadata

ERRATA_ID: ERRATA-002
TASK_ID: AUTO-10-CONTROLLED-READ-DIAGNOSE
STATUS: ACCEPTED
ACCEPTED_BY: 저장소 관리자(현재 대화 사용자), 2026-11-26
APPLIES_TO: docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/WORK_ORDER.md (sha256 a147275224462d7cd3493cb2231b16468a1a0f0e5a64f215c00838a52d47abaf, C1 740c142b10c5eceeaf91012f6c2e276d7f57100b), docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md (sha256 1e9f312749807a370077d11ad9e7b64cb4e820a1335c2283af77a5a25996e4b2, blob 7312eba5ca0c1a62e2133d6cb6f2520312c5de2e, Ce 85fe16840b999946557925a51bc0c27f6304620c)
ERRATA_PATH: docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-002.md
APPROVAL_DIR: 원계약 Metadata의 AUDIT_TOOLS_PATH가 있는 폴더(이 문서는 그 절대 경로를 직접 적지 않는다)
ERRATA_SOURCE: APPROVAL_DIR/ERRATA-002.review-v2.md
SUPERSEDED_DRAFT: APPROVAL_DIR/ERRATA-002.review.md (sha256 56f4affbf6865dbbf74f92d9bc71ddfe7b79d0f56dfeaa8e8537bc049d244ff8, 형식·패턴 미확인, 커밋하지 않고 보존)
ERRATA_COMMIT_PARENT: 85fe16840b999946557925a51bc0c27f6304620c
CE2_AUDIT_TOOLS: APPROVAL_DIR/audit_tools.errata-001.review.py (sha256 0c970e1fb3f60bba7c26268031e4f3769844e2b7938b76fa3160387f26af8233)
IMPLEMENTATION_AUDIT_TOOLS: APPROVAL_DIR/audit_tools.errata-002.review.py (sha256 325f3ef928111588cd091a341792c19e0cee312732273a26199e72a8cb29485e)

## 사유

- R1 IMPLEMENTATION C5 1회차에서 기존 시험 tests/test_repo_hygiene.py::test_no_secrets_or_personal_data_in_addable_files가 실패했다. WORK_ORDER.md와 ERRATA-001.md가 승인 폴더의 사용자 홈 경로를 담고 있어 "user home path" 패턴에 걸렸다. 두 문서는 불변이고 시험은 PROTECTED라 계약 안에서 해결할 수 없다(회귀 STOP). 구현 8개 파일은 실패 목록에 없다.
- R2 docs/agent_workflow.md의 D12 Edit 1회가 형태 목록과 값 문법에만 쓰였고, diagnose 설명 bullet과 CONTROLLED_READ_DIAGNOSE_AUTHORIZATION 문구·대조 규칙이 빠졌다.
- R3 ERRATA_COMMIT(ERRATA-001 E5)은 clean 작업 트리를 전제하지만, 현재 작업 트리에는 구현 8개 파일 변경이 있고 이를 정리하는 조작(stash, reset, checkout, 임시 커밋)은 금지다.
- R4 첫 ERRATA-002 발행본(SUPERSEDED_DRAFT)의 형식 확인 명령이 guard DENY(trading 규칙, 명령 안의 출력 라벨에 대한 정적 매칭으로 판단)로 차단됐다. 그 검사는 재실행하거나 다른 도구·스크립트로 옮기지 않는다.
- R5 관리자 운영 전환 결정(2026-11-26): 일반 문서 편집 횟수 제한, 확인할 수 없는 승인 창 관측과 기술 검증의 혼합, 시간 상한을 정정한다. 단계 묶음 승인은 채택하지 않는다.

## F1 위생 검사의 한정 수락 (ALLOWED_FILES, PROTECTED_FILES 정정)

F1.1 ALLOWED_FILES 9번째에 `M tests/test_repo_hygiene.py`를 추가한다. 기존 8개 순서는 유지한다. 합계 M 6개, A 3개, 9개.
F1.2 이 파일에 허용하는 변경은 다음 셋뿐이다.
  - (a) 상수 HOME_PATH_ACCEPTED 하나 추가: 두 경로를 키로, CRLF만 LF로 바꾼 전체 파일 SHA-256을 값으로 한다.
    - docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/WORK_ORDER.md → a147275224462d7cd3493cb2231b16468a1a0f0e5a64f215c00838a52d47abaf
    - docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-001.md → 1e9f312749807a370077d11ad9e7b64cb4e820a1335c2283af77a5a25996e4b2
  - (b) 보조 함수 accepted_hits(path, data, found) 하나 추가: 경로가 (a)의 키이고 data를 CRLF→LF로 바꾼 SHA-256이 그 값과 같을 때만 found에서 "user home path" 항목 하나를 뺀다. 그 밖에는 found를 그대로 돌려준다.
  - (c) test_no_secrets_or_personal_data_in_addable_files의 `found = secret_hits(...)` 한 줄만, 같은 결과를 accepted_hits에 넘긴 값으로 바꾼다.
F1.3 SECRET_PATTERNS, SCAN_EXCLUDE, PINNED_BLOB, PINNED_WORKTREE, FORBIDDEN_TRACKED, ALLOWED_TRACKED, MAX_TRACKED_BYTES, secret_hits(text)의 동작과 반환값, 그 밖의 시험 함수와 기대 결과는 바꾸지 않는다. 시험 함수를 새로 만들지 않는다. 검사 결과 전체를 무조건 비우는 구조, 경로만 또는 해시만 보는 수락은 금지한다.
F1.4 수락 범위는 위 두 경로·두 해시 조합의 "user home path" 한 항목뿐이다. 같은 파일에 다른 패턴(이메일, 키, 토큰 등)이 있으면 그대로 실패한다. 해시가 다르거나 다른 경로이면 기존 검사를 그대로 적용한다. ERRATA-002.md 자신에는 이 수락을 적용하지 않으므로, 이 문서에는 사용자 홈 절대 경로를 쓰지 않는다.
F1.5 회귀 시험은 tests/test_controlled_read_diagnose.py(기존 A 파일)에 둔다. 위생 시험 모듈은 importlib.util.spec_from_file_location으로 별도 이름으로 불러온다. 검증 항목:
  - (a) 합성 바이트와 monkeypatch한 합성 경로·해시 표에서 일치하면 "user home path"만 빠짐(CRLF판도 수락)
  - (b) 한 바이트를 바꾼 문서나 다른 경로이면 수락하지 않음
  - (c) 같은 합성 문서의 이메일 패턴은 수락 대상이어도 남음
  - (d) secret_hits의 일반 사용자 홈 경로 탐지 유지
  - (e) 다른 비밀정보 탐지(예: aws access key, personal email) 유지
  - (f) 실제 상수 표가 F1.2 (a)의 두 경로·두 해시와 리터럴로 같음
  - (g) 실제 두 계약 파일을 읽기만 하여 수락됨을 확인(파일 수정 없음)
  합성 문자열 가운데 비밀정보 패턴에 해당하는 것(홈 경로의 `:`·`/`·`\`, 이메일의 `@`, 키 접두어 등)은 시험 파일 원문이 위생 검사에 걸리지 않도록 `\x` 이스케이프로 쓰며, SYNTHETIC_ESCAPE_AUDIT 대상이다. 이 이스케이프는 탐지기를 시험하기 위한 합성 입력 표현에 한정한다. 실행 명령·실제 경로·비밀값을 숨기거나 guard를 우회하는 문자열 분할은 허용하지 않는다.
F1.6 PROTECTED 예외는 F1.2의 세 변경뿐이다. 그 밖의 줄 변경은 PROTECTED 위반이다.

## F2 D12 보완 (편집 횟수 제한 정정, K1)

F2.1 docs/agent_workflow.md의 Edit 횟수 제한(원계약 IMPLEMENTATION "D12 Edit 1회")을 없앤다. 판정은 최종 diff로 한다. 이 보완 작업은 FIX 1회로 센다.
F2.2 허용 범위는 원 D12 범위와, 제한 읽기 CLI 절의 precheck bullet 뒤에 diagnose bullet을 추가하는 것뿐이다. bullet 내용은 기록 없음, status 대상 아님, D7 의미 한계(DIAGNOSE_NO_VIOLATION은 PRECHECK_OK·selector 존재·RUN 성공을 뜻하지 않음), D12의 CONTROLLED_READ_DIAGNOSE_AUTHORIZATION 문구, 대조 규칙(원문 존재, 필드 6개와 인자의 완전 일치, 만료 확인, 다른 controlled_read 승인을 대신하지 않음)이다. 다른 절은 바꾸지 않는다.
F2.3 guard.py는 원계약 D11의 범위와 제한(Edit 각 1회 포함)을 그대로 유지하며 확대하지 않는다. guard 추가 변경은 허용하지 않는다.

## F3 ERRATA_COMMIT(ERRATA-002) — dirty 작업 트리 보존 절차

F3.1 위치: 현재 IMPLEMENTATION STOP 상태에서 진입한다. Ce2 사후 확인 뒤 보고하고 멈춘다. IMPLEMENTATION 재개에는 F5.1 형식의 별도 승인이 필요하다.
F3.2 승인 형식:
  `GATE_AUTHORIZATION: AUTO-10-CONTROLLED-READ-DIAGNOSE ERRATA_COMMIT ERRATA=002 WO@740c142b10c5eceeaf91012f6c2e276d7f57100b ERRATA-001@85fe16840b999946557925a51bc0c27f6304620c ERRATA_SHA256=<64hex> ERRATA_SOURCE=<APPROVAL_DIR/ERRATA-002.review-v2.md의 슬래시 절대 경로> AUDIT_TOOLS_SHA256=0c970e1fb3f60bba7c26268031e4f3769844e2b7938b76fa3160387f26af8233`
  원문 존재와 필드·인자의 문자열 완전 일치를 대조하고, 어긋나면 STOP한다. ERRATA_SHA256은 사용자가 발행본의 실제 내용과 해시를 확인한 뒤 승인문에 적는 값이며, 에이전트가 미리 채우지 않는다.
F3.3 진입 조건:
  - `pwd -W` → C:/MoneyLab-auto-10
  - HEAD = 85fe16840b999946557925a51bc0c27f6304620c, tree = 6242e4707e2a6a9627bd4059bae91bbf03a65764
  - `git diff --cached --name-status` 빈 출력(staged 0)
  - `git status --porcelain=v1 --untracked-files=all`이 정확히 다음 8줄(순서 무관)이며, 이 상태를 명시적으로 허용한다:
    ` M .claude/hooks/guard.py`, ` M docs/agent_workflow.md`, ` M src/moneylab/controlled_read/__main__.py`, ` M src/moneylab/controlled_read/transcript.py`, ` M tests/test_controlled_read_isolation.py`, `?? src/moneylab/controlled_read/diagnose.py`, `?? tests/test_controlled_read_diagnose.py`, `?? tests/test_controlled_read_diagnose_guard.py`
  - `sha256sum <CE2_AUDIT_TOOLS>` = 0c970e1fb3f60bba7c26268031e4f3769844e2b7938b76fa3160387f26af8233
F3.4 범위: ERRATA-002.md 최초 생성 1회와 그 파일 하나만 stage·commit하는 문서 전용 커밋 Ce2 1개뿐이다. Ce2의 parent는 Ce다. 구현 8개 변경은 unstaged·untracked 상태 그대로 둔다. stash, reset, restore, checkout, clean, 임시 커밋, `git add .`·`-A`, 다른 경로 add는 금지한다.
F3.5 절차(모두 독립 호출):
  - Y0 CE2_AUDIT_TOOLS M5 worktree-bytes 실행 → F1–F8의 W·S를 BEFORE로 기록
  - X1 `sha256sum <ERRATA_SOURCE>` → ERRATA_SHA256
  - X2 대상 부재 확인: ERRATA-001 E5.5 X2와 같은 명령이며 마지막 인자만 `C:/MoneyLab-auto-10/docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-002.md`로 한다. 판정과 예외 범위는 같다.
  - X3 Read로 ERRATA_SOURCE를 읽고 Write 1회로 ERRATA_PATH를 쓴다. 이어서 status = F3.3의 8줄 + `?? docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-002.md` 1줄
  - X4 `sha256sum docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-002.md` → ERRATA_SHA256
  - X5 `git add -- docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-002.md`
  - X6 `git diff --cached --name-status` → `A`와 그 경로 한 줄
  - X7 `git diff --cached --check` → 빈 출력
  - X8 `git hash-object -- docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-002.md` → OID_E2(`-w` 금지)
  - X9 `git rev-parse :docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-002.md` = OID_E2
  - X10 `git commit -m "docs(task): accept AUTO-10-CONTROLLED-READ-DIAGNOSE ERRATA-002" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. 승인 창 관측은 F7.2에 따라 기록하며 사용자에게 묻지 않는다.
  - X11 사후 확인: `git rev-list --parents -n 1 HEAD` → `<Ce2> 85fe16840b999946557925a51bc0c27f6304620c`, `git rev-parse "HEAD^{tree}"`, `git show --name-status --format= HEAD` → A 1개, `git rev-parse HEAD:docs/tasks/AUTO-10-CONTROLLED-READ-DIAGNOSE/ERRATA-002.md` = OID_E2, `git diff --cached --name-status` 빈 출력, status = F3.3의 8줄
  - Y1 CE2_AUDIT_TOOLS M5 재실행 → F1–F8의 W·S가 Y0과 모두 같음
  Y0·Y1 판정: Y0·Y1은 이번 Ce2에서 8개 파일의 바이트 보존만 확인하는 예외다. F1–F8의 W·S 16개 값이 모두 확보되어야 한다. RESULT=PASS 또는 RESULT=FAIL(형식 위반에 따른 종료 코드 3)은 기록하되 Ce2의 형식 통과 조건으로 사용하지 않는다. RESULT=ERROR·USAGE_ERROR, 출력 누락·잘림, 다른 도구 오류는 STOP이다. Y0·Y1의 W·S는 전부 같아야 한다. 이는 이후 IMPLEMENTATION·PRECOMMIT_AUDIT의 형식 PASS 의무를 면제하지 않는다.
F3.6 증거 해석과 ERRATA-002.md 형식의 한정 수락(K6):
  - X1·X4는 외부 정본과 작업 파일의 원바이트 SHA-256 대조, X8·X9·X11은 Git 필터를 반영한 blob OID 대조다. index·commit content SHA-256은 계산하지 않는다.
  - 이 문서(ERRATA-002.md)에 한해 UTF-8 strict, BOM 없음, 탭 0, NBSP 0, 줄 끝 공백 0, CR 0, 끝 LF 정확히 1개의 기계 확인을 생략하고 미확인 한계로 수락한다. 이 항목들을 검사 완료 또는 PASS로 기록하지 않는다.
  - 유지하는 확인은 X1·X4 SHA-256 대조, X7 `git diff --cached --check`, X8·X9·X11 OID 대조, 그리고 IMPLEMENTATION C5(위생 시험이 이 파일도 검사)다. 이들이 위 미확인 항목 전체를 입증한다고 표현하지 않는다.
  - SUPERSEDED_DRAFT의 차단된 형식·패턴 검사는 재실행하거나 다른 도구·스크립트로 옮기지 않는다.
  - 이 한정 수락은 ERRATA-002.md의 Ce2 진입만을 위한 것이며, 구현 파일의 형식 검사 의무(M5 등)는 그대로다.
F3.7 STOP: 판정 불일치, DENY, 도구 권한 거절, 승인 대기·무응답, 목록 밖 ASK, 도구 오류, 예상 밖 status·staged, Y0·Y1 불일치, 해시 불일치. X2·X8의 실제 guard 판정은 미확인이다.
F3.8 이 절차의 예외(dirty 상태 허용, X2 lstat 확인, F3.6 한정 수락)는 ERRATA-002.md의 Ce2 고정에만 적용한다.

## F4 AUDIT_TOOLS 교체 (IMPLEMENTATION 재개부터)

F4.1 IMPLEMENTATION 재개부터 AUDIT_TOOLS는 IMPLEMENTATION_AUDIT_TOOLS(325f3ef928111588cd091a341792c19e0cee312732273a26199e72a8cb29485e)다. Ce2 절차(F3)는 CE2_AUDIT_TOOLS를 쓴다.
F4.2 errata-001 판과의 차이는 ALLOWED_FILES 9번째 항목 추가, M5 docstring, M6 인자 10개(INDEX|HEAD + S 9개)와 docstring뿐이다. M8 NEW_TEST_PREFIXES를 포함한 다른 판정은 같다.
F4.3 이전 판 두 개는 보존한다.

## F5 연쇄 정정

F5.1 IMPLEMENTATION 이후 gate 승인 형식:
  `GATE_AUTHORIZATION: AUTO-10-CONTROLLED-READ-DIAGNOSE <GATE> WO@740c142b10c5eceeaf91012f6c2e276d7f57100b ERRATA-001@85fe16840b999946557925a51bc0c27f6304620c ERRATA-002@<Ce2 SHA>`
F5.2 M5·M6·AUDIT_S·COMMIT staging·`git diff --cached --name-status`·`git show --name-status`·사후 blob 대조는 9개 기준이다. IMPLEMENTATION 중 tracked 변경은 M 6개 안, untracked는 A 3개 안이다.
F5.3 계보: C1 → Ce → Ce2 → I. 구현 커밋 I의 parent는 Ce2다.
F5.4 PR 범위: 커밋 C1, Ce, Ce2, I 합계 4개. 파일 ALLOWED_FILES 9개 + WORK_ORDER.md + ERRATA-001.md + ERRATA-002.md 합계 12개.
F5.5 PROTECTED 판정: A는 ALLOWED_FILES의 A 3개, WORK_ORDER.md, ERRATA-001.md, ERRATA-002.md. M은 ALLOWED_FILES의 M 6개. 그 밖은 0.
F5.6 PRECOMMIT_AUDIT 추가:
  - HYGIENE_DIFF_SHAPE: Read로 `git diff <base> -- tests/test_repo_hygiene.py`를 확인해 변경 줄이 F1.2 (a)–(c)뿐인지 판정
  - D12 판정: agent_workflow.md 최종 diff가 원 D12 범위와 F2.2 범위뿐인지 판정
  - M8 PRECOMMIT은 그대로(ADDED는 두 신규 시험 파일만, test_repo_hygiene.py의 node ID 추가·삭제 없음)
F5.7 Ce2 절차 동안 기존 구현 8개 파일의 변경 집합과 W·S는 F3에 따라 보존한다. IMPLEMENTATION 재개 후에는 F1·F2의 보완과 기존 계약의 수정 규칙·남은 예산 안에서 ALLOWED_FILES를 변경할 수 있다. 기존 구현을 되돌리거나 검사·보존 조건을 약화해서는 안 된다. WORK_ORDER.md, ERRATA-001.md, C1, Ce, baseline collect, WS-B2 보존 기준값 16개, M9·M10 판정은 바꾸지 않는다.

## F6 재개 시 검사와 예산

F6.1 재개 순서:
  - (1) F2 보완(FIX 1)
  - (2) F1.2 위생 시험 변경과 F1.5 회귀 시험 추가(합쳐 FIX 1)
  - (3) C6 위생 단독 확인 `.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/test_repo_hygiene.py`(최대 2회, 판정: 마지막 요약 줄에 `passed`가 있고 `failed`·`error`가 없음)
  - (4) C1, C2, C3a, C3b
  - (5) C4(목록에 tests/test_repo_hygiene.py 추가)
  - (6) C5
  C6 통과 전에는 C4·C5를 실행하지 않는다. 수정 없이 같은 C5 실패를 반복하지 않는다.
F6.2 시간 상한(관리자 결정): IMPLEMENTATION 총 수행 시간 상한을 10800초에서 18000초로 바꾼다. 이미 사용한 4623초(보수적 상한)를 포함한다. 시험 실행 시간도 계속 포함하며 별도로 보고한다. 넘으면 STOP한다. 정정 준비·승인 대기·ERRATA_COMMIT은 원계약 TIME_ACCOUNTING의 제외 규칙을 따른다.
F6.3 횟수 예산은 초기화하거나 자동 증가시키지 않는다. FIX 0/4에서 F6.1 (1)·(2) 뒤 2/4, C4 1/6, C5 1/3, C6 0/2.
F6.4 기존 실패를 통과로 바꾸거나 필수 CI 실패를 받아들이는 판정은 없다. 정정 후 C5 전체 통과가 IMPLEMENTATION_PASS 조건이다.

## F7 운영 전환 (관리자 결정, 2026-11-26)

F7.1 gate 안의 자율 수행: 승인된 gate 안에서는 그 gate가 허용하는 읽기·수정·합성 fixture 작성·오프라인 시험·실패 분석과 수정을 사용자 확인 없이 수행한다. 다음 gate의 별도 승인이 필요한 시점, STOP 조건, 실제로 필요한 사용자 결정이 있을 때만 보고하고 멈춘다.
F7.2 승인 창 관측(K3): 원계약 WS-B4·COMMIT과 ERRATA-001 E5.5 X10의 "commit 직후 멈추고 사용자에게 승인 창 관측을 묻는다"는 절차를 없앤다. 에이전트가 관측할 수 없는 승인 창은 ASK_UNVERIFIED로 기록하고, 기술 결과는 SHA·parent·tree·변경 집합·blob 대조로 판정한다. 이는 실제 권한 승인을 생략하는 조항이 아니다. 도구의 DENY·권한 거절·승인 대기·무응답은 계속 STOP이다. 관측하지 못한 창을 승인됐다고 기록하지 않는다. 이 조항은 Ce2(X10)와 이후 COMMIT gate에 적용한다.
F7.3 단계 묶음(K4)은 채택하지 않는다. GATE_SEQUENCE와 GATE_TRANSITION_RULES의 단계별 승인은 그대로다. 이 ERRATA는 상위 규칙과 충돌하는 묶음 권한을 만들지 않는다.
F7.4 출력 조건(K2): 설치 출력의 pip `[notice]` 안내는 WS-B5 N3·N4의 관리자 한정 수락으로만 다룬다. 이를 "ERROR가 없으면 모든 도구가 성공"이라는 일반 규칙으로 확대하지 않는다. 검사 도구의 판정은 원계약 EXIT_CRITERIA를 그대로 따른다.
F7.5 정정 절차(K7): 이번 운영 전환과 보완은 이 통합 ERRATA 1건으로 고정한다. 발행 후 사용자가 실제 내용과 해시를 확인해 F3.2 승인을 보낸다. 사용자의 침묵이나 무응답을 승인으로 보지 않는다.

## F8 그 밖

F8.1 이 ERRATA는 상위 규칙, 사전등록, PRESERVED_WORKTREES 규칙, NETWORK 제한, 실제 세션 열람 금지, 연구 공개 백업 보류, guard DENY 비우회 원칙을 바꾸지 않는다. 예외는 F1·F2·F3·F6·F7에 명시한 범위로 한정하며 다른 파일이나 다른 gate로 확대하지 않는다.
F8.2 이 ERRATA가 언급하지 않은 Work Order·ERRATA-001 조항은 그대로다.
F8.3 기존 기록 유지: H1·H4 미확인, C1·Ce ASK_UNVERIFIED와 한정 수락, 설치 출력 한정 수락, IMPLEMENTATION C5 회귀 STOP, D12 미완 이탈, SUPERSEDED_DRAFT 형식 확인 명령의 guard DENY, AUTO-08-FIRST-USE의 STOP.
