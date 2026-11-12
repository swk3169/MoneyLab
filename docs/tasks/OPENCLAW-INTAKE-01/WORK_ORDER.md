# Work Order: OPENCLAW-INTAKE-01 — OpenClaw 자동화 연구자료 비권위 보존

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/OPENCLAW-INTAKE-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: OPENCLAW-INTAKE-01
TASK_ID: OPENCLAW-INTAKE-01
TITLE: OpenClaw 자동화 연구자료, 출처 대장, 자동화 사례의 비권위 보존
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 8eed531cd09ff2748bf91165abd0e1a69b8148c8
CANONICAL_BASE_TREE: 8d515890e0767b9b70d809325c69ec4ea492b442
SOURCE_WORKTREE: C:/MoneyLab-auto-02 (worktree 생성 명령 실행 위치. 기존 파일과 브랜치 내용은 변경하지 않는다. 승인된 worktree 생성에 필요한 Git 관리정보 변경만 예외다)
TARGET_BRANCH: docs/openclaw-intake-2026-11-12
TARGET_WORKTREE: C:/MoneyLab-openclaw-intake
WORKSPACE_SETUP: REQUIRED (SUBPHASE: WORKTREE_CREATION_ONLY -> C1_CREATION_ONLY)
INITIAL_GATE: WORKSPACE_SETUP / WORKTREE_CREATION_ONLY
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests / pytest (Windows), 정확한 PR head SHA에서 SUCCESS
NON_BLOCKING_CI: ci-tests / pytest-linux-experimental. 기존 wrapper 실패 2건은 해결된 것으로 표시하지 않는다.
BUNDLE_ELIGIBLE: YES
BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E
BUNDLE_GRANTED: NONE (실제 묶음 실행은 README §14 형식의 별도 BUNDLE_AUTHORIZATION이 필요하다)
RESEARCH_DOCUMENT_STATUS: NON_AUTHORITATIVE_REFERENCE
CASE_STUDY_STATUS: PARTIAL

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP(WORKTREE_CREATION_ONLY -> C1_CREATION_ONLY) -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- C1 이전 승인 형식: `GATE_AUTHORIZATION: OPENCLAW-INTAKE-01 WORKSPACE_SETUP SUBPHASE=<WORKTREE_CREATION_ONLY | C1_CREATION_ONLY> EXPECTED_HEAD=<40자리 SHA> EXPECTED_TREE=<40자리 SHA>`. WO@ 표기는 쓰지 않는다.
- WORKTREE_CREATION_ONLY와 C1_CREATION_ONLY는 각각 별도 승인이 필요하다. 한 승인으로 두 subphase를 진행하지 않는다.
- C1 이후 승인 형식: `GATE_AUTHORIZATION: OPENCLAW-INTAKE-01 <GATE> WO@<C1 SHA>`
- forward only one gate (또는 subphase) with explicit authorization
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping
- BUNDLE_ELIGIBLE: YES이지만 BUNDLE_GRANTED: NONE이다. 별도 BUNDLE_AUTHORIZATION 없이는 묶어서 진행하지 않는다. 묶음은 BUNDLE_MAX_RANGE 안의 연속 구간만 허용한다. PUSH, PR_CI, MERGE, 후퇴는 개별 승인이다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다.

## GOAL

GOAL: OpenClaw 자동화 연구보고서, 출처 대장, 이번 자동화 시험 사례를 `docs/research-intake/2026-11-12/`에 비권위 연구 참고자료로 보존한다. 이 자료는 승인, 실행 권한, 도구 채택 결정, 비용 절감이나 전체 자동화 성공의 증거가 아니다.

## BACKGROUND

BACKGROUND:
- AUTO-02는 main 8eed531에서 COMPLETE다. 이 task는 그 결과를 바꾸지 않는다.
- INPUT-R 연구보고서(저장소 밖, 경로는 승인 메시지로 전달): sha256 cf8412e5d1257d904588211efe4816618e4b3bd65182347f519ceb5a6bd5bdea, 46279 bytes, 266 lines.
- INPUT-C 사례 기록(저장소 밖, 경로는 승인 메시지로 전달): sha256 a979d5061dd01095f61be619193de7bbaa55a240758807176af13fc928d2adf2, 7011 bytes, 65 lines.
- INPUT-U 사용자가 전달한 ChatGPT 보고: D7 추가 보고의 6개 항목 줄(각 줄은 `- `로 시작)을 UTF-8, BOM 없음, LF, 끝 LF 1개로 정규화한 텍스트. sha256 73fc60c627747b2b9f7a0560638f1824391e5b4eb22944674c5af6a02fd6e654, 462 bytes, 6 lines. Claude가 재확인하지 않은 보고다.
- OpenClaw 추가 시험과 모델 호출은 사용자가 시간과 토큰 소모 때문에 중단했다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP / WORKTREE_CREATION_ONLY: 읽기 전용 사전 확인 뒤 SOURCE_WORKTREE에서 `git worktree add -b docs/openclaw-intake-2026-11-12 C:/MoneyLab-openclaw-intake 8eed531cd09ff2748bf91165abd0e1a69b8148c8` 1회. 이 명령에 따른 Git 관리정보 변경(새 branch ref, worktree 등록 정보)만 허용한다. SOURCE_WORKTREE의 기존 파일, 기존 브랜치 내용, index는 변경하지 않는다. 파일 생성, stage, commit은 없다.
- WORKSPACE_SETUP / C1_CREATION_ONLY: TARGET_WORKTREE에 `docs/tasks/OPENCLAW-INTAKE-01/WORK_ORDER.md` 최초 생성(승인 문구 바이트 그대로), 그 경로만 명시해 stage, C1 커밋 1개. 이 작업은 PROTECTED_FILES에 대한 유일한 예외다.
- IMPLEMENTATION: INPUT-R·INPUT-C 전문 읽기, ALLOWED_FILES 3개 생성, TEST_GATES 실행. stage는 없다.
- PRECOMMIT_AUDIT: 읽기와 감사만. stage하지 않고 승인 S를 계산해 보고한다(D4).
- COMMIT: ALLOWED_FILES 3개만 경로를 명시해 stage, 커밋 하나
- CLEAN_COMMIT_E2E: E2E_GATES 실행, 파일 쓰기 없음
- PUSH: `git push -u origin docs/openclaw-intake-2026-11-12` 1회
- PR_CI: Gate Authorization이 PR_CREATE: YES와 저장소·base·head branch·head SHA·PR 제목·본문을 명시하면 `gh pr create` 1회(README §13)
- MERGE: Gate Authorization이 MERGE_EXECUTE: YES와 PR 번호·head SHA를 명시하고 README §13 사전 검증을 모두 통과하면 `gh pr merge <N> -R <repo> --merge --match-head-commit <SHA>` 1회
- POST_MERGE_AUDIT: main ref만 fetch, 구조 감사
- COMPLETE: 최종 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate·subphase 밖의 행위
- SOURCE_WORKTREE의 기존 파일·브랜치 내용·index 변경(승인된 worktree 생성에 필요한 Git 관리정보 변경만 예외)
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경(C1_CREATION_ONLY의 WORK_ORDER.md 최초 생성 1회만 예외)
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
- hooks·settings·.claude 변경 또는 guard 우회. guard deny 뒤 같은 목적의 재시도·변형·다른 도구를 통한 같은 조사
- 다른 branch·worktree·untracked·ignored·reference 산출물 정리
- OpenClaw, Gateway, ACP, acpx, MCP relay의 호출·설치·설정 변경과 추가 연결 시험, executor 세션 밖의 모델 호출
- INPUT-R·INPUT-C 원본의 수정·이동·삭제
- 원본 JSONL, 인증 URL, 토큰, 내부 세션 ID, 사용자 홈 경로, 이메일 주소를 저장소 파일에 복사
- 출처 없는 내용 정정, 결론 강화, 새 주장 추가
- 비용 절감, 전체 자동화 성공, 수익성, 실거래 준비 주장의 추가
- docs/research-intake/2026-11-06/** 와 기존 색인 변경
- TARGET_WORKTREE에 .venv 생성, 패키지 설치, 환경 변경
- 보호 경로 이름과 sed 등 수정 명령을 한 Bash 명령에 섞기, 출력 리디렉션으로 파일 생성, scratchpad·임시 스크립트 생성
- 한국어와 영어 외 언어 사용

## ALLOWED_FILES

ALLOWED_FILES:
- A docs/research-intake/2026-11-12/OPENCLAW_AUTOMATION_RESEARCH.md
- A docs/research-intake/2026-11-12/SOURCE_REGISTER.md
- A docs/research-intake/2026-11-12/AUTOMATION_CASE_STUDY.md

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/OPENCLAW-INTAKE-01/** (예외: C1_CREATION_ONLY에서 WORK_ORDER.md 최초 생성 1회. C1 이후에는 예외 없음)
- docs/tasks/** (위 예외 외)
- docs/research-intake/2026-11-06/**
- .claude/**
- .github/**
- .gitattributes
- .gitignore
- CLAUDE.md
- src/**
- tests/**
- configs/**
- pyproject.toml
- requirements*.txt

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가). C1 최초 생성 예외는 ALLOWED_FILES에 넣지 않고 C1_CREATION_ONLY 행위로만 둔다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 커밋 구조: C1의 parent는 CANONICAL_BASE_SHA이고 C1의 변경은 `A docs/tasks/OPENCLAW-INTAKE-01/WORK_ORDER.md` 하나다. 구현 커밋 I의 parent는 C1이고 I의 변경은 ALLOWED_FILES 3개의 A뿐이다.
- D2 보호 diff: 비교 범위는 C1부터 I까지(`git diff --name-status C1 I`)다. 결과는 ALLOWED_FILES 3개의 A와 정확히 같고 PROTECTED_FILES 변경은 0이다. PR 전체 범위(base..I)는 WORK_ORDER.md와 ALLOWED_FILES 3개, 합계 4개 파일의 A다.
- D3 인코딩: WORK_ORDER.md와 ALLOWED_FILES 3개는 UTF-8, BOM 없음, LF만 사용(CR 0), 끝 LF 정확히 1개(마지막 바이트 0x0A, 그 앞 바이트는 0x0A가 아님)다.
- D4 해시:
  - C1: 작업 파일 바이트는 승인 문구 바이트와 같고, staged 내용 SHA-256과 C1 커밋 blob 내용 SHA-256은 승인 문구 SHA-256과 같다.
  - PRECOMMIT_AUDIT: stage하지 않는다. 파일마다 작업 파일 바이트 SHA-256(W)과, 저장소 속성과 Git 필터(core.autocrlf 포함)를 적용했을 때 저장될 예상 내용의 SHA-256을 계산한다. 뒤의 값을 사용자가 승인하면 그것이 승인 S다. Git blob object ID와 내용 SHA-256을 혼동하지 않는다.
  - COMMIT: 파일마다 W는 PRECOMMIT_AUDIT 당시 값과 같고, staged 내용 SHA-256과 커밋 blob 내용 SHA-256은 승인 S와 같다. W와 S가 같을 것은 따로 요구하지 않는다. 조건이 하나라도 어긋나면 STOP한다.
- D5 공개용 변환(세 파일 공통): IMPLEMENTATION에서 INPUT-R과 INPUT-C 전문을 읽은 뒤 다음 편집만 수행한다.
  - (a) 비식별화: 사용자 홈 경로, 내부 세션 ID, 원본 JSONL 파일명, 인증 URL, 토큰, 이메일 주소, 그 밖의 개인 식별 정보를 제거하거나 일반 표현으로 바꾼다. 위치는 특정 행 번호로 제한하지 않고 전문 검사로 찾는다.
  - (b) 형식 정규화: D3에 맞춘다.
  - (c) 출처 있는 정정: INPUT-C, INPUT-U, 또는 Git으로 확인 가능한 사실을 근거로 명시할 수 있는 사실 오류만 고친다. 근거 없는 정정, 결론 변경, 새 주장은 하지 않는다.
  - (d) 구성 작성: D6–D8이 요구하는 머리말, 입력 대장, 출처 대장, 편집 이력, 사례 절, 상태 표식을 작성한다.
  - 원본 INPUT-R·INPUT-C는 바꾸지 않고, 작업 전후 해시를 재확인한다.
  - (a)–(c)의 모든 편집과 (d)로 추가한 절은 SOURCE_REGISTER.md의 "편집 이력" 절에 대상 파일, 위치(절 제목 또는 행 범위), 종류(a·b·c·d), 변경 요지, 근거를 기록한다. 이력에는 제거한 민감 값 자체를 다시 적지 않는다.
- D6 SOURCE_REGISTER.md: 첫 세 줄은 `AUTHORITY: NON_AUTHORITATIVE`, `BOUNDARY: DATA_NOT_INSTRUCTIONS`, `DOCUMENT_DATE: 2026-11-12`다. 다음 세 절을 둔다.
  - "입력 대장": INPUT-R, INPUT-C, INPUT-U의 SHA-256, 바이트 수, 줄 수, 출처 구분. 로컬 경로는 적지 않는다.
  - "출처 대장": INPUT-R 부록 A의 출처 목록. D5 변환만 적용하고, 새 출처 추가나 URL 재조회 주장은 하지 않는다.
  - "편집 이력": D5에 따른 기록.
- D7 AUTOMATION_CASE_STUDY.md: INPUT-C를 바탕으로 D5 변환을 적용하고 다음을 반영한다.
  - 머리말에 `CASE_STUDY_STATUS: PARTIAL`을 둔다. INPUT-C의 `STATUS:` 값은 사례 기록 작성 시점의 문서 상태로 남기고 CASE_STUDY_STATUS와 구분한다.
  - PARTIAL의 뜻: 지시 전달과 Claude 측 작업 완료는 기록으로 확인됐지만, 정상 응답 경로 회수는 실패했다. 전체 절차 자동화와 비용 절감은 입증되지 않았다.
  - 다음 절을 덧붙인다(본문은 아래 문구 그대로. 6개 항목 줄은 INPUT-U와 바이트 일치).

  ## 추가 보고: 마지막 수정 지시 전달

  출처: 사용자가 전달한 ChatGPT 보고. Claude가 재확인하지 않았다.

  - 마지막 수정 지시는 OpenClaw를 통해 1회 전달됐다.
  - 호출은 60초 timeout으로 끝났다.
  - 이후 ChatGPT가 Claude 세션 기록에서 지시 수신과 수정안 생성 완료를 확인했다.
  - 정상 응답 경로의 회수는 실패했고, 기록에서 결과를 복구했다.
  - 전체 절차 자동화와 비용 절감은 입증되지 않았다.
  - 사용자는 시간과 토큰 소모 때문에 추가 시험을 중단하기로 했다.

  ## timeout 사건의 동일성

  - 사례 기록 13항의 60초 timeout과 위 추가 보고의 60초 timeout이 같은 사건인지는 미확인이다.
  - 두 보고는 출처별로 따로 적는다. 별개 사건으로 세지 않고, timeout 건수를 합산하지 않는다.

  ## 보존 시점 상태

  - 사례 기록의 "현재 판정"과 "다음 경계"는 그 기록을 작성한 시점의 상태다.
  - 이 문서는 비권위 연구 참고자료다. 승인, 실행 권한, 채택 결정이 아니다.
  - 이번 보존 작업에서는 OpenClaw 추가 시험과 모델 호출을 하지 않았다.

  (덧붙이는 본문은 위의 들여쓰기 2칸을 뺀 바이트로 쓴다.)
- D8 상태 구분: OPENCLAW_AUTOMATION_RESEARCH.md의 상태 표기는 RESEARCH_DOCUMENT_STATUS(NON_AUTHORITATIVE_REFERENCE)를 따르고, 사례 상태(CASE_STUDY_STATUS)와 섞지 않는다. 세 파일의 첫 줄은 `AUTHORITY: NON_AUTHORITATIVE`다.
- D9 executor 정적 확인: WORKTREE_CREATION_ONLY, C1_CREATION_ONLY, IMPLEMENTATION 진입 전에 다음을 정적으로 확인해 보고한다.
  - executor 세션 root worktree의 `.claude/settings.json`·`.claude/hooks/guard.py` blob이 base와 같은지
  - `settings.local.json`이 있는지
  - `.venv/Scripts/python.exe`가 있는지
  - 사용자 전역 settings에 hook이 있는지
  - TARGET_WORKTREE는 세션 root로 쓰지 않는다.
  - 동적 강제 검증은 진입 조건이 아니다.
  - 다음 미확인 사항을 확인된 것으로 표시하지 않는다: guard의 docs/research-intake/** 처리 방식, hook 실제 실행 여부, matcher 밖 도구(mcp__* 등) 적용 여부, 세션 root 밖 worktree 경로에 대한 경로 규칙 적용 여부.

## TEST_GATES

TEST_GATES:
- INPUT-R·INPUT-C 해시를 작업 전후에 재확인한다(원본 불변). INPUT-U 해시를 D7 6개 항목 줄과 대조한다.
- D3 바이트 검사(3개 파일)
- D5 비식별화 검사: 세 파일 전문 읽기와 패턴 검색을 함께 수행한다. 사용자 홈 경로, 내부 세션 ID, 원본 JSONL 파일명, 이메일 주소, 인증 URL, 실제 토큰과 비밀값이 남아 있으면 STOP한다. 공개 논문 식별자와 Git SHA는 보존한다. 검색 결과 0건만으로 비식별화 완료를 판정하지 않는다.
- D5 편집 이력: 모든 편집과 구성 절이 SOURCE_REGISTER.md에 기록되고 근거가 붙어 있다. 원본과의 차이와 편집 이력이 서로 맞는다.
- D7: CASE_STUDY_STATUS: PARTIAL 존재, 추가 보고 본문 일치, timeout 동일성 미확인 표시, timeout 건수 합산 없음
- 한자·가나·키릴 문자 0건
- `git diff --check` 깨끗함, 변경 집합 = ALLOWED_FILES, PROTECTED diff 0
- 로컬 전체 pytest: NOT_REQUIRED(문서 전용 작업의 제안 기준). REQUIRED_CI_CHECKS는 정확한 PR head에서 필수다.

## E2E_GATES

E2E_GATES:
- clean 상태의 I에서 TEST_GATES의 파일 검사를 다시 실행한다.
- `git diff --name-status C1 I`와 `git diff --name-status <base> I`가 D2와 같다.
- 파일 쓰기가 없고, 실행 전후 git status(ignored 포함)가 같다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·I SHA와 tree, parent, 커밋 파일 집합, blob 내용 SHA-256, merge parent·tree
- CLAUDE_REPORTED: W·승인 S 계산, staged 내용 대조, TEST_GATES·E2E_GATES 결과, D9 정적 확인과 미확인 사항
- INDEPENDENT: 정확한 PR head의 Windows CI, GitHub 화면, ChatGPT·사용자 재검토

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, SUBPHASE(C1 이전), EXPECTED_HEAD·EXPECTED_TREE(C1 이전) 또는 WORK_ORDER_COMMIT·WORK_ORDER_SHA256(C1 이후)
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 파일별 W, 승인 S, staged 내용 SHA-256, 커밋 blob 내용 SHA-256
- 편집 이력 요약, 미확인 사항
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE 또는 SUBPHASE> = YES / NO

## STOP_CONDITIONS

STOP_CONDITIONS:
- WORKTREE_CREATION_ONLY 생성 전:
  - 원격 main ≠ CANONICAL_BASE_SHA, base tree 불일치
  - EXPECTED_HEAD·EXPECTED_TREE가 base와 다름
  - TARGET_BRANCH 또는 TARGET_WORKTREE가 이미 존재
- WORKTREE_CREATION_ONLY 생성 후:
  - TARGET_WORKTREE의 branch ≠ TARGET_BRANCH, HEAD ≠ base, tree ≠ base tree, clean 아님
  - SOURCE_WORKTREE의 HEAD·branch·index·작업 파일 변경
- C1_CREATION_ONLY 진입: HEAD·tree ≠ 승인의 EXPECTED_HEAD·EXPECTED_TREE, clean 아님. 부재 조건은 다시 적용하지 않는다.
- C1_CREATION_ONLY 종료:
  - C1 parent ≠ base
  - C1 변경이 WORK_ORDER.md 하나가 아님
  - 작업 파일 바이트 ≠ 승인 문구 바이트
  - staged 내용 또는 C1 커밋 blob 내용의 SHA-256 ≠ 승인 문구 SHA-256
  - clean 아님
- C1 이후: Work Order sha256 불일치, docs/tasks/OPENCLAW-INTAKE-01/** 변경
- INPUT-R·INPUT-C·INPUT-U 해시 불일치, 읽기 실패, 원본 변경
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경(C1 최초 생성 예외 외), ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A 표기와 base 상태 불일치
- D3–D8 위반, 민감 패턴 발견, 근거 없는 정정, 편집 이력 누락
- COMMIT에서 W가 PRECOMMIT_AUDIT 값과 다름, staged 내용 또는 커밋 blob 내용이 승인 S와 다름
- guard deny, 권한 창 거절, BUNDLE 실행 중 EXPECTED_ASK에 없는 ASK
- 테스트 실패·에러, hard gate 불일치
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일
