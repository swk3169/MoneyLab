# ERRATA: QUALITY-GATES-02 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: QUALITY-GATES-02-ERRATA-001
TASK_ID: QUALITY-GATES-02
TARGET_WORK_ORDER: docs/tasks/QUALITY-GATES-02/WORK_ORDER.md @ b6a8028c4b770e7d3d99b0769b2ee0d9c0a3d833 (sha256 87dfdefc67ea60f3e8a608a99e17c545a406d1942510499f9befe20332bbfa95)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER, 2026-11-06

## ISSUE

ISSUE:
- core.autocrlf=true(system)이고 WORK_ORDER.md에 text·eol attribute가 없다(`git check-attr` 모두 unspecified).
- 같은 저장소의 다른 Work Order 21개는 `git ls-files --eol`로 i/lf w/crlf다. WORK_ORDER.md는 직접 쓴 파일이라 현재 i/lf w/lf다.
- 따라서 이 파일이 다시 checkout되면(다른 worktree·clone·merge 후 main checkout 포함) 작업 트리 바이트가 CRLF가 되어 FILE_SHA256이 달라진다. C1 blob은 바뀌지 않는다.
- 현재 STOP_CONDITIONS는 "이후 gate에서 FILE_SHA256이 WORK_ORDER_SHA256과 다름"을 중단 조건으로 두므로, 계약 바이트가 불변인데도 STOP이 날 수 있다.
- Ce가 추가되면 REQUIRED_EVIDENCE의 "HEAD = C1"(IMPLEMENTATION), "Ci parent = C1"(COMMIT), "PR 커밋 {C1, Ci}·파일 4개"(PR_CI)가 실제 이력과 맞지 않는다.
- STOP_CONDITIONS의 PROTECTED_FILES 조건은 C1_CREATION_EXCEPTION만 제외해, ACCEPTED ERRATA의 Ce 최초 생성이 STOP으로 읽힐 수 있다.

## CHANGED_FIELDS

CHANGED_FIELDS:
- REQUIRED_EVIDENCE (HASH_DEFINITIONS 포함, 섹션 전체 대체)
- REQUIRED_REPORT (섹션 전체 대체)
- STOP_CONDITIONS (섹션 전체 대체)

## UNCHANGED_FIELDS

UNCHANGED_FIELDS (명시적으로 바꾸지 않음):
- Metadata 전부(CANONICAL_BASE_SHA·TREE·PARENTS, MERGE_EXPECTED_REMOTE_MAIN 포함), GATE_SEQUENCE, GATE_TRANSITION_RULES.
- USER_DECISIONS D1–D7, SCOPE, OUT_OF_SCOPE, ALLOWED_ACTIONS, FORBIDDEN_ACTIONS.
- ALLOWED_FILES, PROTECTED_FILES, INVARIANT, C1_CREATION_EXCEPTION.
- DESIGN_CONTRACT DC1–DC14(DC3a, DC10a, DC12a 포함), TEST_GATES T01–T29, E2E_GATES.
- COMPLETION_CRITERIA, ROLLBACK_POLICY, PR_POLICY, MERGE_POLICY.
- C1 커밋, C1의 WORK_ORDER.md blob과 그 SHA-256(87dfdefc67ea60f3e8a608a99e17c545a406d1942510499f9befe20332bbfa95).
- REQUIRED_EVIDENCE의 WORKSPACE_SETUP 행(이미 충족된 기록으로 유지).
- CLAUDE.md, docs/tasks/README.md, .gitattributes, git 설정.

## RATIONALE

RATIONALE:
- 계약 바이트는 커밋된 blob이 정의한다. 작업 트리 바이트는 git 설정에 따라 checkout마다 달라질 수 있으므로 무결성 기준을 blob 내용 SHA-256으로 정한다.
- 줄바꿈 변환만 허용하고, 그 밖의 바이트 차이는 STOP으로 남긴다.
- Ce 추가에 따른 증거 표의 부모·범위 값을 실제 이력에 맞춘다.
- PROTECTED 조건의 Ce 처리는 CLAUDE.md(ERRATA 최초 생성은 ACCEPTED ERRATA 커밋에서만)와 C1_CREATION_EXCEPTION의 Ce 문장을 명시적으로 반영한 것이다. 보호 범위를 넓히거나 줄이지 않는다.
- `.gitattributes` 변경은 ALLOWED_FILES 밖이므로 이 task에서 하지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:

- REQUIRED_EVIDENCE:

HASH_DEFINITIONS:
- FILE_SHA256: 작업 트리 파일 바이트의 SHA-256(소문자 hex 64자리). 보조 증거다.
- GIT_BLOB_OID: `git rev-parse <commit>:<path>`가 내는 Git 객체 ID. Git 객체 형식의 해시이며 SHA-256 값과 비교하지 않는다.
- BLOB_CONTENT_SHA256: `git cat-file blob <commit>:<path>`가 내는 바이트의 SHA-256.
- BLOB_CONTENT_MATCH: `git cat-file blob <commit>:<path>` 바이트와 작업 트리 파일 바이트가 바이트 단위로 같으면 YES, 아니면 NO. 서로 다른 해시 알고리즘의 값을 비교해서 판정하지 않는다.
- WORK_ORDER_SHA256: C1의 `docs/tasks/QUALITY-GATES-02/WORK_ORDER.md` BLOB_CONTENT_SHA256 = 87dfdefc67ea60f3e8a608a99e17c545a406d1942510499f9befe20332bbfa95.
- ERRATA_001_SHA256: Ce의 `docs/tasks/QUALITY-GATES-02/ERRATA-001.md` BLOB_CONTENT_SHA256(Ce 보고값).
- LF_NORMALIZED_SHA256: 작업 트리 파일 바이트에서 모든 CRLF(0x0D 0x0A)를 LF(0x0A)로 바꾼 바이트의 SHA-256. 단독 CR은 바꾸지 않는다.
- CONTRACT_FILE_CHECK(<commit>, <path>, <승인 SHA-256>): B = `git cat-file blob <commit>:<path>` 바이트, W = 작업 트리 파일 바이트.
  1. SHA-256(B) ≠ 승인 SHA-256이면 MISMATCH.
  2. W = B이면 EXACT_MATCH.
  3. B에 CR이 없고, W의 모든 CR이 CRLF의 일부이며(단독 CR 없음), W의 CRLF를 LF로 바꾼 바이트가 B와 바이트 단위로 같으면 LINE_ENDING_ONLY. 이때 LF_NORMALIZED_SHA256을 보고한다.
  4. 그 밖은 MISMATCH.
  작업 트리 파일 존재 요구:
  - WORKING_FILE_REQUIRED gate: CE_COMMIT, IMPLEMENTATION, PRECOMMIT_AUDIT, COMMIT, CLEAN_COMMIT_E2E. 이 gate에서 작업 트리 파일이 없으면 결과는 WORKING_FILE_ABSENT이고 PASS가 아니다(STOP).
  - BLOB_ONLY gate: POST_MERGE_AUDIT. 작업 트리 파일 확인을 요구하지 않는다. 1만 판정하고, 1을 통과하면 결과는 BLOB_ONLY_VERIFIED다. 작업 트리 파일이 있으면 2–4도 판정해 함께 보고한다.
  - 허용 결과: WORKING_FILE_REQUIRED gate는 EXACT_MATCH 또는 LINE_ENDING_ONLY만, BLOB_ONLY gate는 BLOB_ONLY_VERIFIED, EXACT_MATCH, LINE_ENDING_ONLY만. 그 밖(MISMATCH, WORKING_FILE_ABSENT)은 STOP.
- C1 이후 Work Order 무결성 판정은 BLOB_CONTENT_SHA256과 CONTRACT_FILE_CHECK로 한다. FILE_SHA256 단독 불일치는 STOP 사유가 아니다.

REQUIRED_EVIDENCE (gate별 통과 증거와 확인 주체. 보고 key 목록은 REQUIRED_REPORT에 따로 있다):

| gate | GIT_VERIFIABLE | CLAUDE_REPORTED | INDEPENDENT | 통과 확인 |
|---|---|---|---|---|
| WORKSPACE_SETUP | `git ls-remote` 원격 main = CANONICAL_BASE_SHA; worktree 생성 직후 HEAD = CANONICAL_BASE_SHA, tree = CANONICAL_BASE_TREE, parents = CANONICAL_BASE_PARENTS; C1 SHA·tree; C1 parent = CANONICAL_BASE_SHA; C1 파일 집합 = {docs/tasks/QUALITY-GATES-02/WORK_ORDER.md}; FILE_SHA256, GIT_BLOB_OID, BLOB_CONTENT_SHA256; BLOB_CONTENT_MATCH = YES | 문구가 승인본과 같음, clean | 사용자가 FILE_SHA256·C1 확인 | 사용자 |
| IMPLEMENTATION | 변경 파일 집합 ⊆ ALLOWED_FILES; PROTECTED diff 0; HEAD = Ce; CONTRACT_FILE_CHECK(HEAD, WORK_ORDER.md, WORK_ORDER_SHA256)·(HEAD, ERRATA-001.md, ERRATA_001_SHA256) ∈ {EXACT_MATCH, LINE_ENDING_ONLY} | T01–T29, 전체 pytest 수(passed/failed/errors/skipped), ruff, mypy exit 0 | 없음 | 사용자(보고 수락) |
| PRECOMMIT_AUDIT | 변경 집합 = ALLOWED_FILES(전부 A); `git diff --check`; PROTECTED diff 0; 세 파일 FILE_SHA256; 두 계약 파일 CONTRACT_FILE_CHECK | DC1–DC14 spot check, 결과값 부재 확인 | 없음 | 사용자 |
| COMMIT | Ci SHA·tree; Ci parent = Ce; Ci 파일 집합 = ALLOWED_FILES; 세 파일 GIT_BLOB_OID; 세 파일 BLOB_CONTENT_MATCH = YES; 세 FILE_SHA256 = PRECOMMIT_AUDIT 값; 두 계약 파일 CONTRACT_FILE_CHECK | clean | 없음 | 사용자 |
| CLEAN_COMMIT_E2E | HEAD = Ci; 실행 전후 `git status --porcelain` 비어 있음; 두 계약 파일 CONTRACT_FILE_CHECK | TEST_GATES 재실행 결과 | 없음 | 사용자 |
| PUSH | 원격 main = MERGE_EXPECTED_REMOTE_MAIN; 원격 branch head = Ci | 없음 | 사용자가 GitHub branch 확인 가능 | 사용자 |
| PR_CI | PR base·head·head SHA; PR 커밋 {C1, Ce, Ci}·파일 5개(WORK_ORDER.md, ERRATA-001.md, ALLOWED_FILES 3개) = PR 범위 | 없음 | REQUIRED_CI_CHECKS가 head SHA에서 SUCCESS(GitHub Actions) | 사용자(CI 화면) |
| MERGE | README §13 사전 검증 1–7(7은 MERGE_EXPECTED_REMOTE_MAIN), merge SHA | 사전 검증 기록 | 사전 검증 5: 사용자가 이 표의 IMPLEMENTATION·PRECOMMIT_AUDIT·CLEAN_COMMIT_E2E CLAUDE_REPORTED 증거와 PR_CI INDEPENDENT 증거를 수락 | 사용자 |
| POST_MERGE_AUDIT | merge parent1 = MERGE_EXPECTED_REMOTE_MAIN, parent2 = PR head; merge tree = merge-tree 재계산; first-parent 범위; ancestry; branch·worktree 보존; merge 커밋의 WORK_ORDER.md BLOB_CONTENT_SHA256 = WORK_ORDER_SHA256, ERRATA-001.md BLOB_CONTENT_SHA256 = ERRATA_001_SHA256; CONTRACT_FILE_CHECK(merge SHA, docs/tasks/QUALITY-GATES-02/WORK_ORDER.md, WORK_ORDER_SHA256) ∈ {BLOB_ONLY_VERIFIED, EXACT_MATCH, LINE_ENDING_ONLY}; CONTRACT_FILE_CHECK(merge SHA, docs/tasks/QUALITY-GATES-02/ERRATA-001.md, ERRATA_001_SHA256) ∈ {BLOB_ONLY_VERIFIED, EXACT_MATCH, LINE_ENDING_ONLY} | 감사 기록 | 사용자 확인 | 사용자 |

CE_COMMIT_EVIDENCE (ERRATA-001 Ce, 별도 Gate Authorization):
- GIT_VERIFIABLE: Ce SHA·tree; Ce parent = C1(b6a8028c4b770e7d3d99b0769b2ee0d9c0a3d833); Ce 파일 집합 = {docs/tasks/QUALITY-GATES-02/ERRATA-001.md}; FILE_SHA256, GIT_BLOB_OID, BLOB_CONTENT_SHA256(= ERRATA_001_SHA256); BLOB_CONTENT_MATCH = YES; CONTRACT_FILE_CHECK(Ce, WORK_ORDER.md, WORK_ORDER_SHA256)
- CLAUDE_REPORTED: 파일 바이트가 수락본과 같음, clean
- INDEPENDENT: 사용자가 ERRATA_001_SHA256·Ce 확인
- 통과 확인: 사용자

- Claude가 실행한 결과는 INDEPENDENT로 쓰지 않는다(CLAUDE.md, docs/tasks/README.md §11).

- REQUIRED_REPORT:

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256(= C1 WORK_ORDER.md의 BLOB_CONTENT_SHA256), ACCEPTED_ERRATA와 각 ERRATA_<NNN>_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- WORKSPACE_SETUP: FILE_SHA256, GIT_BLOB_OID, BLOB_CONTENT_SHA256, BLOB_CONTENT_MATCH
- C1 이후 각 gate: 계약 파일마다 BLOB_CONTENT_SHA256, FILE_SHA256, CONTRACT_FILE_CHECK 결과, LINE_ENDING_ONLY이면 LF_NORMALIZED_SHA256
- 그 gate의 REQUIRED_EVIDENCE 행과 각 값의 증거 등급(GIT_VERIFIABLE / CLAUDE_REPORTED / INDEPENDENT)
- PROPOSED_ERRATA, ISSUES
- GUARD_EVENTS
- DEVIATIONS
- RESULT_REREAD_COUNT, RESULT_CONTEXT_EXPOSURE
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

- STOP_CONDITIONS:

STOP_CONDITIONS:
- base·HEAD·tree·parents가 기대와 다름
- Work Order 불일치: C1 WORK_ORDER.md가 승인 문구와 다르거나 C1의 BLOB_CONTENT_MATCH = NO, 또는 이후 gate에서 CONTRACT_FILE_CHECK(<HEAD>, WORK_ORDER.md, WORK_ORDER_SHA256)가 그 gate의 허용 결과(HASH_DEFINITIONS)가 아님
- ERRATA 불일치: Ce ERRATA-001.md가 수락 문구와 다르거나 Ce의 BLOB_CONTENT_MATCH = NO, 또는 이후 gate에서 CONTRACT_FILE_CHECK(<HEAD>, ERRATA-001.md, ERRATA_001_SHA256)가 그 gate의 허용 결과(HASH_DEFINITIONS)가 아님
- C1 이후 WORK_ORDER.md blob 변경, Ce 이후 ERRATA-001.md blob 변경
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경(C1_CREATION_EXCEPTION과 ACCEPTED ERRATA 파일의 Ce 최초 생성 제외), ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A 표기와 base 상태 불일치(경로가 이미 있음)
- TARGET_BRANCH 또는 TARGET_WORKTREE가 이미 있음
- guard deny, 권한 창 거절
- 테스트 실패·에러, ruff 위반, mypy exit ≠ 0, TEST_GATES 항목 불일치, COMMIT의 BLOB_CONTENT_MATCH = NO
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일
- 원격 main이 기대값과 다름(WORKSPACE_SETUP: CANONICAL_BASE_SHA, PUSH·MERGE: MERGE_EXPECTED_REMOTE_MAIN, D5). 필드를 고치지 않고, 자동 rebase·merge 없이, 별도 ERRATA 승인 대상으로 보고한다
- 구현에 실제 study 값이 필요해지거나 연구 결과 열람이 필요해짐
- ALLOWED_FILES 밖 변경(예: research/__init__.py export, pyproject)이 필요해짐

## ISSUANCE

ISSUANCE:
- 이 ERRATA는 IMPLEMENTATION이 의존하므로 IMPLEMENTATION 전에 Ce로 커밋한다(docs/tasks/README.md §6).
- 순서(각 단계 별도 사용자 승인, 자동 진행 없음):
  1. 최종 문안 수락(STATUS: ACCEPTED, ACCEPTED_BY: USER, <날짜>로 바꾼 문안)
  2. 수락 바이트 고정(저장소 밖 후보 파일 생성과 SHA-256·bytes·lines 보고, D6 예외 승인이 있을 때만)
  3. Ce: 수락 바이트를 docs/tasks/QUALITY-GATES-02/ERRATA-001.md로 생성(UTF-8, BOM 없음, LF, 끝 개행 1개), 그 경로만 `git add --`, 커밋 1개(`docs(task): add QUALITY-GATES-02 ERRATA-001`), REQUIRED_EVIDENCE의 CE_COMMIT_EVIDENCE 보고
  4. IMPLEMENTATION Gate Authorization(WO@b6a8028c4b770e7d3d99b0769b2ee0d9c0a3d833, ACCEPTED_ERRATA: ERRATA-001)
- Ce는 push하지 않는다. PUSH gate에서 Ci와 함께 게시된다.

## BASELINE_IMPACT

BASELINE_IMPACT:
- C1, WORK_ORDER.md blob, WORK_ORDER_SHA256 불변.
- 설계·테스트·파일 범위·PR·merge 정책의 의미 변화 없음. 증거 표의 부모·범위 값만 Ce 이력에 맞춘다.
- feature/quality-gates-02의 HEAD가 Ce로 이동한다. PR 범위는 커밋 3개·파일 5개가 된다.

## SECURITY_IMPACT

SECURITY_IMPACT:
- guard·hook·settings, git 설정, .gitattributes를 바꾸지 않는다.
- 연구 결과값·판정 라벨이 없다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA:
- AC-1: Ce 파일 집합 = {docs/tasks/QUALITY-GATES-02/ERRATA-001.md}, Ce parent = C1.
- AC-2: Ce의 BLOB_CONTENT_MATCH = YES, ERRATA_001_SHA256 = 수락 바이트의 SHA-256.
- AC-3: CONTRACT_FILE_CHECK(Ce, WORK_ORDER.md, WORK_ORDER_SHA256) ∈ {EXACT_MATCH, LINE_ENDING_ONLY}(CE_COMMIT은 WORKING_FILE_REQUIRED gate다).
- AC-4: 이 파일에 결과값·판정 라벨이 없다.

## ROLLBACK_POLICY

ROLLBACK_POLICY:
- ACCEPTED 이후 이 파일은 불변이다. 철회·수정은 ERRATA-002로만 한다.
- Ce를 amend·reset하지 않는다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
