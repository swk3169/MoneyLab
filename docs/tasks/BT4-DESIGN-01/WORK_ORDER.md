# Work Order: BT4-DESIGN-01 — BT-4 고정 전 결정 구조·검증 경계 설계

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/BT4-DESIGN-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

이 파일이 계약의 유일한 출처다. 대화 기억에 의존하지 않는다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: BT4-DESIGN-01
TASK_ID: BT4-DESIGN-01
TITLE: BT-4 decision inventory, dependency, validation boundary and freeze framework design
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 2a184b2d3f44d868590d65f85f7dfd9d09fe7988
CANONICAL_BASE_TREE: e6ff902c564ef00fb64a5e81c0860457cfbee7e1
TARGET_BRANCH: docs/bt4-design-01
TARGET_WORKTREE: C:/MoneyLab-bt4-design-01
WORKSPACE_SETUP: REQUIRED (이 gate에서 branch·worktree를 base에서 만들고 이 파일을 C1로 발행한다. 새 worktree에 `.venv`나 junction을 만들지 않는다)
INITIAL_GATE: IMPLEMENTATION
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (squash·rebase merge·auto merge 금지. branch 삭제는 별도 승인 없이는 하지 않는다)
DATA_SCOPE: base 시점 repository, BT4-RESEARCH-01 결과물의 기존 증거. 새 외부 증거, 시장 데이터, 새 simulation 없음.
LANGUAGE: 한국어 중심. gate 이름, 필드명, 코드 identifier, 파일 경로, 논문 제목, 통계 방법명, 결정 ID는 필요하면 영어 원문을 유지한다.

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

이전 gate: DESIGN_INVESTIGATION = PASS, CONTRACT_REVIEW = PASS (대화). WORKSPACE_SETUP은 이 C1 커밋으로 수행하고 결과는 채팅으로 보고한다.

- EVIDENCE_COLLECTION gate는 없다. 이 task는 새 외부 증거를 수집하지 않고, BT4-RESEARCH-01의 증거와 repository 사실을 구조화한다.
- 남은 모든 forward gate는 각각 명시적 Gate Authorization이 필요하다. 어떤 gate도 자동으로 승인되지 않는다.
- MERGE는 산출물 통합일 뿐 COMPLETE가 아니다.

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: BT4-DESIGN-01 <GATE> WO@<C1 commit>`)
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다.

## GOAL

GOAL: BT-4(v0.6 사전등록 고정) 전에 다음을 설계 문서 하나(`docs/bt4_design_01.md`)로 정의한다.
1. BT-4에서 최종적으로 결정해야 할 전체 decision inventory의 복원
2. 각 decision의 dependency와 evidence 상태
3. validation이 필요한 decision과 policy-only decision의 분리
4. 이후 statistical validation의 사전등록 입력 구조
5. 이후 freeze task가 쓸 decision framework

## NON_GOALS

NON_GOALS:
- BT-4 freeze 자체. 어떤 decision value도 선택하지 않는다.
- D1–D10, U, G, 위험 정책 값, DP2–DP4, BT4-Q18의 값 선택
- 절차 갈림길 A/B 선택
- 통계 절차 채택(studentized futility, block 길이 방법, Holm/StepM/SPA/RC 중 승자)
- GARCH/Normal 정책 선택, Mode A+B 유지·제거 결정, DSR·PBO의 규범 규칙 채택
- ε, 목표 MC SE, 목표 truth SE, 반복 수 같은 threshold·값 확정
- simulation, calibration, resampling, 후보 절차 구현, BT4 implementation
- validation task의 생성·실행, downstream task ID 고정

## SCOPE_INVENTORY

SCOPE_INVENTORY (출처는 CANONICAL_BASE_SHA 기준. 분류는 CONTRACT_REVIEW의 잠정 분류이며, 산출물에서 근거와 함께 다시 정하되 D1–D7은 READY_TO_FREEZE로 두지 않는다. 초안의 현재안·기본값은 immutable decision이 아니다):

| 항목 | 출처 | 잠정 분류 |
|---|---|---|
| D1 무익성 최소 효과 θ_min | docs/research_v06_preregistration_draft.md §18.1 | NEEDS_VALIDATION |
| D2 α_fut | 같음 | NEEDS_VALIDATION |
| D3 무익성 Holm 적용 | 같음 | NEEDS_VALIDATION |
| D4 forward S_F의 H2 포함 | 같음 | NEEDS_POLICY_DECISION (H1·H2 통계량 불변 조건) |
| D5 α_F | 같음 | NEEDS_POLICY_DECISION (같은 조건) |
| D6 T_F | 같음 | NEEDS_VALIDATION / NEEDS_POLICY_DECISION |
| D7 중간·최종 무익성 α 배분 | 같음 | NEEDS_VALIDATION |
| D8 구간 경계 열린 포지션 | 같음 | NEEDS_POLICY_DECISION |
| D9 historical holdout 끝 H_end | 같음 | NEEDS_POLICY_DECISION |
| D10 H1 수준 왜곡·엔진 FAR 판정 반영 | docs/backtest_design.md 16절 | NEEDS_POLICY_DECISION (π 보정 선택 시 NEEDS_VALIDATION) |
| U1 M 전략 정의 | docs/backtest_design.md 16절 (결정 2026-10-16) | 이미 결정됨 (BT-1 엔진 규칙) |
| U2 계정 수수료 (alias G1) | 16절, draft §18.2 | NEEDS_POLICY_DECISION |
| U3 최소 주문·호가 단위 | 16절 | OUT_OF_SCOPE (계좌 모드 전용) |
| U4 신호 결측 시 보유 포지션 | 16절, BT-3E handoff | NEEDS_POLICY_DECISION |
| U4a | docs/tasks/BT-3E/WORK_ORDER.md DEFERRED_TO_LATER_TASKS에만 이름이 있음 | UNRESOLVED_REFERENCE |
| U5 1시간봉 범위 | 16절, BT-3E handoff | NEEDS_POLICY_DECISION |
| U6 참여율 상한 | 16절, BT-3E handoff | NEEDS_POLICY_DECISION |
| U7 가격 수치 표현 | 16절 | DEFERRED |
| U8 커밋 위치 | 16절 | OUT_OF_SCOPE |
| U9 raw·vault 접근 guard (alias G7) | 16절, draft §18.2 | NEEDS_POLICY_DECISION |
| G1–G6 (자본, 충격, 양의 연도 비율, 품질 임계값, AI_ops 등) | draft §18.2 | 고정 전 draft 현재안. BT-4에서 확정 대상 |
| 위험 정책: ratio | docs/tasks/BT-3E/WORK_ORDER.md DEFERRED_TO_LATER_TASKS | NEEDS_POLICY_DECISION (MC-V06 평가 값 외 선택 시 NEEDS_VALIDATION) |
| 위험 정책: comparison operator | 같음 | NEEDS_POLICY_DECISION |
| 위험 정책: accumulation mode | 같음 | NEEDS_POLICY_DECISION |
| 위험 정책: metric/date mapping | 같음 | NEEDS_POLICY_DECISION |
| 위험 정책: per-strategy cost/capital/scenario | 같음 | NEEDS_POLICY_DECISION |
| 위험 정책: confirmation interval | 같음 | NEEDS_POLICY_DECISION |
| 위험 정책: check_window_end_utc | 같음 | NEEDS_POLICY_DECISION |
| 위험 정책: F selection rule | 같음 | NEEDS_POLICY_DECISION |
| 위험 정책: violation handling | 같음 | NEEDS_POLICY_DECISION |
| DP2 locked 파일 형식 문구 | docs/backtest_design.md 10.3 | NEEDS_POLICY_DECISION |
| DP3 접근 기록 문구 | 같음 | NEEDS_POLICY_DECISION |
| DP4 개월 수 → W_end 해석 | 같음 | NEEDS_POLICY_DECISION |
| BT4-Q18 엔진 gap-free 창 vs 사전등록 D·D−N 종가 | docs/tasks/BT-3E/WORK_ORDER.md | NEEDS_VALIDATION (엔진 수준) |
| DSR 보고 항목, 시도 수 | draft §6.1(시도 수 9), §10.5(보고), config 템플릿 `deflated_sharpe_trials` | DIAGNOSTIC_ONLY. 시도 수 9는 BT-4 freeze 전 draft 값 |

ALIASES_AND_LINKS:
- 중복(alias): G1 = U2, G7 = U9
- 연결: D6 ↔ DP4, D9(H_end) ↔ 위험 정책 confirmation interval

OTHER_ITEMS (BT-4 decision inventory가 아님):
- PBO: PROPOSED_DECISION_ITEM / diagnostic candidate (초안에 없음)
- Mode A+B: DIAGNOSTIC_ONLY (MC 보고)
- GARCH/Normal 정책: PROPOSED_DECISION_ITEM (검증 합격 규칙의 일부)
- Holm: D3 그 자체
- Romano–Wolf StepM, Hansen SPA, White Reality Check, studentized futility, data-driven block length: validation의 후보 절차

UNRESOLVED_REFERENCE_U4A: BT-3E Work Order의 handoff 목록에는 이름이 있으나 canonical repository에서 정의를 찾지 못했다. U4의 하위 항목이라고 추론하지 않는다. 이 task에서 정의하지 않는다. BT-4 freeze 전에 provenance·정의 해결이 필요하다.

TAX_INPUTS: 세율 τ, D, Y0(draft에서 법령 확인 전 미확정)는 현재 확인된 BT-4 handoff 목록에 없으므로 inventory에 넣지 않는다. 산출물의 unresolved 절에 `OUTSIDE_CURRENT_BT4_HANDOFF`, `RELATED_UNRESOLVED_INPUT`으로 기록할 수 있다. 값과 범위는 정하지 않는다.

DI_CORRECTION_DSR: DESIGN_INVESTIGATION에서 DSR을 "새 decision candidate"로 분류한 것은 canonical repository와 맞지 않았다. canonical 분류는 기존 draft 보고 항목(DIAGNOSTIC_ONLY), draft 시도 수 9다.

## CLASSIFICATION_VOCABULARY

CLASSIFICATION_VOCABULARY: NEEDS_VALIDATION | NEEDS_POLICY_DECISION | READY_TO_FREEZE | DEFERRED | OUT_OF_SCOPE | DIAGNOSTIC_ONLY | PROPOSED_DECISION_ITEM | UNRESOLVED_REFERENCE
- 분류는 잠정 설계 분류이며 freeze 결정이 아니다.
- D1–D7은 READY_TO_FREEZE로 분류하지 않는다.
- 새 decision ID를 임의로 만들지 않는다. 필요하면 PROPOSED_DECISION_ITEM으로만 표시한다.

## DELIVERABLE_CONTRACT

DELIVERABLE_CONTRACT: `docs/bt4_design_01.md` 하나. 최소 절(순서대로):
1. Purpose / non-goals
2. Canonical BT-4 decision inventory
3. Decision classification
4. D/R/V dependency map
5. Futility procedure decomposition
6. Multiple-testing decision structure
7. Procedure fork A vs B
8. DGP policy alternatives
9. Mode A+B / DSR / PBO classification
10. Evidence gaps
11. Validation requirements V-1~V-8
12. Freeze prerequisites
13. Proposed downstream task boundaries
14. Unresolved user decisions

- 숫자 decision value나 procedure winner를 기록하지 않는다.
- 원인 귀속은 HYPOTHESIS / unresolved로 유지한다. 새 인과 결론을 만들지 않는다.
- Holm을 타당하지 않은 개별 p값을 고치는 방법으로 쓰지 않는다. DSR·PBO를 개별 test size 보정으로 쓰지 않는다.

## PROCEDURE_FORK_CONTRACT

PROCEDURE_FORK_CONTRACT:
- 경로 A: 현재 통계 절차를 유지하고, 측정된 operating characteristics를 알고 BT-4 decision을 내린다.
- 경로 B: 통계 절차를 바꾸고, 새 사전등록 validation MC 뒤 BT-4 decision을 내린다.
- 이 task는 A/B를 선택하지 않는다. 선택은 downstream 사용자 결정이다.
- 산출물은 각 경로에 대해 required evidence, benefits, risks, 무효·낡게 되는 것, required next task, freeze prerequisites를 정의한다.
- "경로 A를 고르면 validation을 자동으로 생략할 수 있다"는 규칙을 만들지 않는다. 경로 A의 최소 evidence requirement를 정의하고, 그 고려 사항에 truth 정밀도와 DGP 요인 분리를 포함한다.

## VALIDATION_BOUNDARY

VALIDATION_BOUNDARY:
- V-1~V-8은 이 task에서 실행하지 않는다.
- 산출물은 다음만 정의한다: hypothesis 구조, estimand, DGP 요인 구조, 표본 길이 구조, 후보 절차 집합, primary metric, 합격 기준의 형태, 정밀도 요구 범주, multiplicity 정책 요구, 사전등록 요구.
- 정하지 않는 값: ε, 목표 MC SE, 목표 truth SE, 정확한 simulation 수, 정확한 bootstrap 수, DGP 정책, 우승 절차.
- MC-V06의 R_OUTER, B_BOOT, K_RAND, TRUTH_YEARS, TARGET_MAX_MC_SE는 참고 기준일 뿐 새 validation에 자동으로 상속하지 않는다.
- 향후 validation은 최소 두 계층으로 분리하는 방향을 산출물에 기록한다: (A) statistical validation(V-1~V-8: futility, studentization, delta, block 길이, truth 정밀도, 2×2 DGP, 다중검정, 유한 표본), (B) engine / risk-policy validation(BT4-Q18, 위험 비율 대안, D10에서 π 보정을 고르는 경우). 정확한 downstream task ID는 고정하지 않는다.

## EVIDENCE_POLICY

EVIDENCE_POLICY:
- 새 웹 검색과 새 외부 source 조사·다운로드를 금지한다.
- 외부 문헌은 BT4-RESEARCH-01 source register(`docs/research_bt4_01_evidence_review.md` §3)의 Tier와 verification status를 그대로 쓴다. 승격하지 않는다.
- repository·code 사실: GIT_VERIFIABLE. 산출물에 넣기 전에 CANONICAL_BASE_SHA의 실제 경로·내용으로 다시 확인한다. 채팅 보고만을 repository 증거로 쓰지 않는다.
- MC-V06 수치: SYNTHETIC / NOT_EVIDENCE. 필요하면 CLAUDE_REPORTED를 함께 적는다. BT4-RESEARCH-01 report에 이미 있는 수치만 인용한다. 새 진단 계산을 하지 않는다.
- 새 추론: INFERENCE. 확인되지 않은 원인 설명: HYPOTHESIS.
- INDEPENDENT는 CI 결과나 사용자·독립 검증이 있을 때만 쓴다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: 사전조건 확인; `git worktree add -b docs/bt4-design-01 C:/MoneyLab-bt4-design-01 2a184b2d3f44d868590d65f85f7dfd9d09fe7988`; 승인된 문구로 이 파일 생성; 이 파일만 stage; C1 commit; sha256 보고
- IMPLEMENTATION: `docs/bt4_design_01.md`만 생성·수정. base 시점 repository의 읽기 전용 조사
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: `git add -- docs/bt4_design_01.md`; commit 하나
- CLEAN_COMMIT_E2E: TEST_GATES와 E2E_GATES만 (저장소 쓰기 없음)
- PUSH: `git push -u origin docs/bt4-design-01`만 (이후 fast-forward push는 같은 branch에 한함)
- PR_CI: PR 생성은 PR_CI Gate Authorization이 명시적으로 허용할 때만. CI는 읽기 전용으로 관찰
- MERGE: MERGE_METHOD
- POST_MERGE_AUDIT: `git fetch origin main`만; 구조 감사
- COMPLETE: 최종 보고 (채팅·PR 본문)

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 작업
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull
- hooks·settings·`.claude/**` 변경 또는 guard 우회
- 다른 branch·worktree, untracked·ignored·reference 출력 정리·변경 (MC-V06 RUN_ROOT, BT4-RESEARCH-01 worktree 포함)
- 새 worktree에 `.venv`나 junction 생성, dependency 설치
- simulation, calibration, resampling, 새 진단 계산, 후보 절차 구현, BT4 implementation
- 새 웹 검색, 새 source 다운로드
- NON_GOALS의 모든 결정
- Claude memory, MEMORY.md, memory note의 생성·수정
- scratchpad의 생성·수정·삭제 (기존 항목은 관찰만)

## ALLOWED_FILES

ALLOWED_FILES:
- A docs/bt4_design_01.md

`docs/tasks/BT4-DESIGN-01/WORK_ORDER.md`는 C1에서만 만들고 그 직후부터 보호 파일이다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/BT4-DESIGN-01/** (예외: C1의 WORK_ORDER.md 생성, Ce의 ACCEPTED ERRATA 생성)
- docs/tasks/**
- docs/research_v04_preregistration.md, docs/research_v05_preregistration_draft.md, docs/research_v06_preregistration_draft.md
- docs/backtest_design.md
- docs/research_bt4_01_evidence_review.md
- configs/**, src/**, tests/**, data/**
- .claude/**, .github/**, CLAUDE.md, README.md, pyproject.toml, requirements*.txt, .gitignore, .gitattributes
- ALLOWED_FILES 밖의 모든 경로

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가)

## TEST_GATES

TEST_GATES:
- Python: 기존 검증된 venv `C:/MoneyLab-mc-v06/.venv/Scripts/python.exe`. 환경변수 `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=C:/MoneyLab-bt4-design-01/src`. 새 worktree에 `.venv`·junction을 만들지 않는다.
- 실행 전에 `moneylab.__file__`로 import source가 `C:/MoneyLab-bt4-design-01/src` 아래인지 확인한다. 아니면 멈춘다.
- canonical local full suite: 작업 디렉터리 `C:/MoneyLab-bt4-design-01`에서 `python -B -m pytest -rsx -p no:cacheprovider`. 결과를 그대로 기록한다.
- `git diff --check` clean; 변경 파일 집합 = ALLOWED_FILES
- 산출물 구조 점검: DELIVERABLE_CONTRACT의 14절 제목 존재; D1–D7에 READY_TO_FREEZE 없음; 결정값·procedure winner 기록 없음; 외부 문헌 status가 BT4-RESEARCH-01 register와 같음

## KNOWN_ENVIRONMENT_TOPOLOGY

KNOWN_ENVIRONMENT_TOPOLOGY:
- 다음 두 test는 `CLAUDE_PROJECT_DIR=<repository root>`를 설정하고 `<repository root>/.venv/Scripts/python.exe`를 실행한다(`tests/test_agent_guard.py`의 `run_wrapped`):
  - `tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through`
  - `tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0`
- 이 Work Order는 새 worktree에 `.venv` 생성을 금지하므로, local full suite에서 이 두 test의 failure가 예상된다.
- 이 failure를 PASS로 표현하지 않는다. LOCAL_TEST_RESULT는 실제 결과 그대로 기록한다.

## E2E_GATES

E2E_GATES (CLEAN_COMMIT_E2E):
- clean implementation commit에서 TEST_GATES를 실행한다.
- gate-level acceptance는 다음을 모두 만족할 때만 가능하다. 이 조건은 local test를 PASS로 재분류하는 규칙이 아니다:
  - A. local failed test가 정확히 KNOWN_ENVIRONMENT_TOPOLOGY의 두 test뿐이다.
  - B. 두 failure 모두 `C:/MoneyLab-bt4-design-01/.venv/Scripts/python.exe` 부재라는 같은 환경 의존 원인이다.
  - C. 그 외 failed = 0
  - D. errors = 0
  - E. 예상하지 못한 collection failure = 0
  - F. collected, selected, deselected, passed, failed, errors, skipped, xfailed, xpassed 수를 모두 기록한다.
- 하나라도 다르면 CLEAN_COMMIT_E2E = FAIL 또는 BLOCKED.
- 보고에는 `LOCAL_TEST_RESULT: <실제 결과>, not PASS`(failure가 있을 때)와 `DEFERRED_STATUS: ENVIRONMENT_DEPENDENT_DEFERRED_TO_PR_CI`를 함께 쓴다.
- test 후 worktree에 cache·bytecode·artifact가 없어야 한다(ignored 포함). 생겼으면 삭제하지 않고 보고하고 FAIL/BLOCKED.
- MC-V06 RUN_ROOT와 MC-V06 worktree 두 곳에 tracked 변경이 없는지 확인한다.

## PR_CI_CONDITIONS

PR_CI_CONDITIONS:
- 판정 대상: MERGE 시점 PR head commit에 대해 실행된 `ci-tests` run.
- 직접 증거 우선: CI log에 KNOWN_ENVIRONMENT_TOPOLOGY의 두 test가 개별 PASSED로 나오면 그것을 쓴다(`EVIDENCE_TYPE: DIRECT_CI_EVIDENCE`). workflow나 check가 green이라는 사실만으로 개별 test의 PASSED를 추론하지 않는다.
- pytest 출력 형식 때문에 개별 PASSED 줄이 없으면, 각 test마다 아래 E1–E9를 모두 확인할 수 있을 때만 PASSED를 eliminative CI evidence로 인정한다(`EVIDENCE_TYPE: ELIMINATIVE_CI_EVIDENCE`):
  - E1. canonical pytest job이 success이고, pytest 요약에서 failed = 0, errors = 0이다.
  - E2. collected, selected, deselected, passed, skipped, xfailed, xpassed, failed, errors 수가 CI log에서 확인되고 selected = passed + skipped + xfailed + xpassed + failed + errors가 성립한다.
  - E3. 해당 test가 평가 대상 commit의 canonical collection(`testpaths`)에 존재한다. 확인 방법: 그 commit의 소스 확인, 또는 cache·bytecode를 만들지 않는 local `pytest --collect-only -q -p no:cacheprovider`(`PYTHONDONTWRITEBYTECODE=1`, `python -B`).
  - E4. CI log의 SKIPPED 목록에 해당 test가 없다.
  - E5. CI log의 XFAIL·XPASS 목록에 해당 test가 없다.
  - E6. 해당 test에 deselection 대상 marker가 없다(함수 decorator, class, module의 `pytestmark` 모두 확인).
  - E7. 다른 selection exclusion이 없다: `pyproject.toml`의 `addopts`·`testpaths`, CI 명령의 추가 인자(`-k`, `-m`, `--deselect`, `--ignore`), `conftest.py`의 collection hook(`pytest_collection_modifyitems`, `pytest_ignore_collect` 등).
  - E8. CI log의 FAILED·ERROR 목록에 해당 test가 없다.
  - E9 (보조 증거). 같은 commit 내용의 local CLEAN_COMMIT_E2E와 CI의 count가 대조된다: local failed가 정확히 두 test였고, CI passed가 local passed보다 정확히 2 많으며, skipped·deselected·xfailed 수와 목록이 일치한다. E9는 E1–E8을 대신하지 않는다.
- 하나라도 확인할 수 없으면 NOT_RESOLVED, PR_CI = BLOCKED.
- 두 test 중 하나라도 CI에서 failed나 error이면 PR_CI = FAIL. skipped이면 NOT_RESOLVED. 어느 경우든 MERGE 전에 멈춘다.
- 증거 등급: CI log의 수치·목록·conclusion은 INDEPENDENT, 소스·설정 확인은 GIT_VERIFIABLE, E1–E9를 결합한 판정은 CLAUDE_REPORTED.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 커밋의 SHA·parent·tree, Work Order sha256, 커밋 파일 집합, merge parents·tree, 산출물 sha256
- CLAUDE_REPORTED: local pytest 결과, E1–E9 결합 판정
- INDEPENDENT: PR CI 결과, GitHub 화면, 사용자 재확인

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
- ALLOWED_FILES 밖 tracked 변경, PROTECTED 변경, ALLOWED ∩ PROTECTED ≠ ∅, A/M marker 불일치
- guard deny, 권한 거절 (deny된 명령을 변형해 반복하지 않는다)
- E2E_GATES 조건 불충족, PR_CI_CONDITIONS 불충족
- 계약 모순 또는 상위 규칙과의 충돌
- 예상 밖 untracked 파일
- D1–D10 실제 값 선택; U·G·위험 정책·DP·Q18 실제 값 선택
- A/B fork 선택; 통계 절차 채택(studentized futility, block 길이 방법 포함); Holm/StepM/SPA/RC 승자 선택
- GARCH/Normal 정책 선택; Mode A+B 유지·제거 결정; DSR·PBO 규범 규칙 채택
- ε·MC SE·truth SE 확정
- simulation·calibration·resampling 실행; BT4 implementation 시작
- import source가 새 worktree가 아님
