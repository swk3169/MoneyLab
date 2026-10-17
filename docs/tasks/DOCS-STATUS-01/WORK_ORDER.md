# Work Order: DOCS-STATUS-01 — README development-status dashboard

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/DOCS-STATUS-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

이 파일이 계약의 유일한 출처다. 대화 기억에 의존하지 않는다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: DOCS-STATUS-01
TASK_ID: DOCS-STATUS-01
TITLE: README development-status dashboard
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 8a6b75ea78a24ea475df1ad351620ee1449e4aaf
CANONICAL_BASE_TREE: 1d15b590d7337aa77fd7a06c37931301ac311d8a
TARGET_BRANCH: docs/status-dashboard
TARGET_WORKTREE: C:/MoneyLab-docs-status
WORKSPACE_SETUP: REQUIRED (branch·worktree는 C1 전에 생성 완료, 이 파일이 C1)
INITIAL_GATE: IMPLEMENTATION
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (squash/rebase merge 금지: 계약 커밋이 구현보다 먼저인 이력을 보존)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

DESIGN_INVESTIGATION, CONTRACT_REVIEW, WORKSPACE_SETUP(branch `docs/status-dashboard`, worktree `C:/MoneyLab-docs-status`, HEAD = CANONICAL_BASE_SHA)은 이 파일 발행 전에 완료했다. 이 파일의 C1 커밋은 별도 Gate Authorization으로 만들었다.

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: DOCS-STATUS-01 <GATE> WO@<C1 commit>`)
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다.

## GOAL

GOAL: README.md 상단에 외부 방문자가 MoneyLab의 최종 목표, 현재 개발 단계, 완료된 검증 인프라, 바로 다음 개발 순서를 한눈에 볼 수 있는 간결한 "개발 현황" 섹션을 추가한다. 기존 상세 기능 설명과 하단 장기 로드맵은 그대로 둔다.

## BACKGROUND

BACKGROUND:
- README.md는 2026-10-10(`937a5e9`) 이후 바뀌지 않았다. 상단 11행 "현재 버전(v0.3)은 읽기 전용이다."는 README 본문의 `## v0.3.1`, `## v0.4 (Phase 1)` 절과 맞지 않는다.
- 현황 근거(CANONICAL_BASE 기준): BT-1–BT-2b(PR #15, #11), BT-3a(PR #16), BT-3b(PR #17), BT-3c(PR #18), BT-3d(PR #20), Work Order v1.1(PR #19), GitHub CLI guard 개선(PR #21) merge 완료. BT-3e는 원격 branch `feature/backtest-bt3e-risk-check`에 있고 PR이 없다. v0.6 Monte Carlo harness는 main에 있다(PR #10). v0.6 사전등록은 초안(DRAFT), 미고정이다. BT-4는 사전등록·config 고정, BT-5는 실데이터 첫 단계다(`docs/backtest_design.md`).
- 증거 범위: `docs/backtest_design.md`는 BT-1–BT-4의 실행 결과를 SYNTHETIC / NOT_EVIDENCE로 정한다. v0.4 연구 pipeline은 실데이터를 쓰므로 프로젝트 전체를 합성으로 일반화하지 않는다.
- 사용자 결정: 최종 목표 문장 유지, stale v0.3 안내 교체, 상단 현황판 추가, v0.6 캔들 수집 별도 행 없음, 내부 task ID(GUARD-ACT-01, MC-V06) 비노출, 하단 `## 로드맵` 수정 없음, README 문구는 이 파일에 고정.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: 완료(이 파일의 C1 커밋 포함)
- IMPLEMENTATION: README.md를 DESIGN_CONTRACT D1–D3대로 수정, TEST_GATES 실행
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: `git add -- README.md`, 커밋 하나
- CLEAN_COMMIT_E2E: E2E_GATES의 읽기 전용 확인
- PUSH: TARGET_BRANCH 하나만 `git push -u origin docs/status-dashboard`
- PR_CI: Gate Authorization이 명시한 경우 base `main`, head TARGET_BRANCH의 PR 1건 생성, CI 읽기 전용 관찰
- MERGE: Gate Authorization이 명시한 경우 MERGE_METHOD로만 merge
- POST_MERGE_AUDIT: 읽기 전용 구조 감사(fetch는 Gate Authorization이 명시한 경우 `git fetch origin main`만)
- COMPLETE: 최종 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull
- hooks·settings·.claude 변경 또는 guard 우회
- 다른 branch·worktree(C:/MoneyLab, C:/MoneyLab-guard-gh-cli, BT-3E worktree 포함)·untracked·ignored·reference 산출물 정리·변경
- `.venv` 생성·설치·변경
- README.md의 승인 문구 재작성(D1–D2 문구는 바이트 그대로 쓴다)
- README.md 하단 `## 로드맵` 절 수정, README 재설계
- 애플리케이션 코드·테스트·설정 변경, guard 활성화, BT-3E 재개, Monte Carlo 실행, BT-4·BT-5 착수
- README에 C1/Ce/Ci SHA, Work Order SHA256, 내부 task ID(GUARD-ACT-01, MC-V06), 권한 창·guard 구현 세부를 쓰는 것

## ALLOWED_FILES

ALLOWED_FILES:
- M README.md

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/DOCS-STATUS-01/** (ACCEPTED ERRATA 최초 생성만 예외)
- docs/tasks/** (다른 task 계약)
- .claude/**
- CLAUDE.md
- AGENTS.md
- .github/**
- src/**
- tests/**
- configs/**
- docs/backtest_design.md
- docs/agent_workflow.md
- docs/research_v04_preregistration.md
- docs/research_v05_preregistration_draft.md
- docs/research_v06_preregistration_draft.md
- README.md 이외의 모든 경로

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가)

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 현재 상태 안내 교체: CANONICAL_BASE의 README.md 11행 한 줄(`> **현재 버전(v0.3)은 읽기 전용이다.** 실제 주문, 지갑 연결, 개인키 사용, 자동매매, 실거래 자금 사용 기능은 없다.`)을 아래 APPROVED_NOTICE 블록의 내용 한 줄로 바꾼다.
- D2 개발 현황 섹션 삽입: D1의 줄 바로 뒤에 빈 줄 하나와 아래 APPROVED_SECTION 블록의 내용을 넣는다. 그 뒤에는 CANONICAL_BASE의 12행(빈 줄), 13행(`---`), 15행 `## v0.1: Polymarket Scanner` 이하가 그대로 이어진다.
- D3 경계: CANONICAL_BASE README.md의 1–10행과 12행 이후 전체는 바이트 단위로 바뀌지 않는다. 최종 목표 문장(5행), 단계 흐름(7–9행), 하단 `## 로드맵` 절은 수정하지 않는다. README 줄바꿈은 blob 기준 LF이고 파일 끝 형식은 바꾸지 않는다.
- D4 기대 결과(정확한 정의): 구현 후 README.md의 blob 내용 = (CANONICAL_BASE README.md 1–10행) + (APPROVED_NOTICE 1줄) + (빈 줄 1줄) + (APPROVED_SECTION 전체 줄) + (CANONICAL_BASE README.md 12행부터 끝까지). APPROVED 블록의 내용은 아래 fenced block의 여는 줄과 닫는 줄 사이의 줄이다(여는·닫는 fence 줄은 포함하지 않는다).
- D5 문구 고정: 구현은 APPROVED 블록을 재작성하지 않는다. 실질적인 문구 변경이 필요하면 구현하지 않고 멈춰서 PROPOSED_ERRATA로 보고한다.

APPROVED_NOTICE:

````markdown
> **현재 MoneyLab은 연구·검증 단계다.** 실제 주문, 지갑 연결, 개인키 사용, 자동매매, 실거래 자금 운용 기능은 구현·활성화되어 있지 않다.
````

APPROVED_SECTION:

````markdown
## 🚧 개발 현황

기준: 2026-10-18

MoneyLab은 현재 **백테스트와 위험검증 인프라를 구축하는 단계**다. 백테스트 단계(BT-1–BT-4)의 실행 결과는 모두 합성 데이터 기반(`SYNTHETIC / NOT_EVIDENCE`)이며 수익성의 근거가 아니다. 실데이터 백테스트는 BT-5부터다.

| 개발 영역 | 상태 |
|---|---|
| 백테스트 엔진·비용·지표 (BT-1–BT-2b) | ✅ 완료 |
| 사전등록 규칙·평가 경계·입력 재현성 (BT-3a–BT-3c) | ✅ 완료 |
| Holdout / Forward Vault 잠금 (BT-3d) | ✅ 완료 |
| Work Order 기반 개발 통제 체계 | ✅ 완료 |
| 월별 Forward 위험 확인 장치 (BT-3e) | 🟡 구현 완료, 리뷰·CI 대기 |
| 개발 에이전트 안전장치 적용 확인 | 🔵 다음 단계 |
| v0.6 Monte Carlo 검증 | ⏳ 예정 |
| v0.6 사전등록·설정 고정 (BT-4) | ⏳ 예정 (사전등록 초안 작성, 미고정) |
| 실데이터 검증 (BT-5) | 🔒 대기 |

바로 다음 단계 (계획):

안전장치 적용 확인 → BT-3e PR·CI → v0.6 Monte Carlo 검증 → BT-4 사전등록·설정 고정 → BT-5 실데이터 검증

단계 정의는 [docs/backtest_design.md](docs/backtest_design.md)에, 장기 버전 방향은 아래 [로드맵](#로드맵) 절에 있다.
````

## TEST_GATES

TEST_GATES:
- 변경 파일 집합 = {README.md}, PROTECTED diff 0, untracked 0
- `git diff --check` 깨끗함
- README.md 변경 hunk는 CANONICAL_BASE 11행 위치 하나뿐이다(D3)
- 구현 후 README.md 내용이 D4 기대 결과와 바이트 단위로 같다(blob id 비교)
- 로컬 pytest는 요구하지 않는다: README.md는 코드·테스트가 읽지 않고, TARGET_WORKTREE에 `.venv`가 없으며 이 task는 `.venv`를 만들지 않는다. 회귀 확인은 PR CI(`pytest`)로 한다.

## E2E_GATES

E2E_GATES:
- NOT_REQUIRED (문서 전용). 대체 확인: clean 구현 커밋에서 README.md blob이 D4 기대 결과와 같고, 커밋 파일 집합이 {README.md}이며, 구현 커밋의 부모가 C1이다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 커밋 SHA·parent·tree, Work Order sha256, 커밋 파일 집합, README.md blob id와 D4 기대 결과 일치, merge parent·tree
- CLAUDE_REPORTED: Claude가 실행한 확인과 계산
- INDEPENDENT: PR CI 결과, GitHub 화면(사용자 확인)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, Work Order sha256 불일치
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기와 base 상태 불일치
- CANONICAL_BASE README.md 11행이 D1의 기존 문장과 다름
- 구현 결과가 D4 기대 결과와 다름, 또는 승인 문구의 변경이 필요함
- guard deny, 권한 창 거절
- CI 실패
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일
