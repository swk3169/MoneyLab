# Work Order: MC-V06 — v0.6 synthetic Monte Carlo decision-characteristic validation

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/MC-V06/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

이 파일이 계약의 유일한 출처다. 대화 기억에 의존하지 않는다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: MC-V06
TASK_ID: MC-V06
TITLE: v0.6 synthetic Monte Carlo decision-characteristic validation
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: a25ff3bb6afd7ef01de028b5d00f7071d31e593c
CANONICAL_BASE_TREE: 4fbfc549be2ca386ceb59c985f3aa1ae365fd8b9
TARGET_BRANCH: feature/v06-mc-v06
TARGET_WORKTREE: C:/MoneyLab-mc-v06
WORKSPACE_SETUP: REQUIRED (완료. branch·worktree·ignored `.venv` junction(→ C:/MoneyLab/.venv)은 C1 전에 생성했고, 이 파일이 C1)
INITIAL_GATE: IMPLEMENTATION
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (squash/rebase merge 금지: 계약 커밋이 구현보다 먼저인 이력을 보존)
DATA_SCOPE: fixture·합성 전용. 모든 Monte Carlo 출력은 SYNTHETIC / NOT_EVIDENCE다. 외부 시장 데이터, 외부 API, 실거래, 주문 실행 없음.

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> MC_PILOT -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> MC_FULL_RUN -> MC_RESULT_AUDIT -> COMPLETE

이전 gate: DESIGN_INVESTIGATION = PASS, CONTRACT_REVIEW = PASS, WORKSPACE_SETUP = PASS (BASE@a25ff3b, 대화로 완료).

- 남은 모든 forward gate는 각각 명시적 Gate Authorization이 필요하다. 어떤 gate도 자동으로 승인되지 않는다.
- MC_PILOT은 CLEAN_COMMIT_E2E 뒤, PUSH 전에 한다. 비과학 점검이다(PILOT_CONTRACT).
- MC_FULL_RUN은 PUSH, PR_CI, MERGE, POST_MERGE_AUDIT가 모두 PASS인 뒤에만, 자체 Gate Authorization으로 한다.
- MERGE는 구현 통합일 뿐 MC-V06 COMPLETE가 아니다.
- BT-4 CONTRACT_REVIEW 2단계는 MC_FULL_RUN = PASS, MC_RESULT_AUDIT = PASS, MC-V06 COMPLETE = PASS 전에는 시작하지 않는다.

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: MC-V06 <GATE> WO@<C1 commit>`)
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다.

## GOAL

GOAL: v0.6 사전등록 초안 18.1의 후보 선택지에 대해 합성 경로에서 판정 특성을 추정하고 보고한다(초안 16절 0단계). 보고 대상: 해당하는 경우 REJECT / RESEARCH_MORE / PAPER 확률, study 단위 FWER, RISK_LIMIT 발동률, Monte Carlo 표준오차(MC SE), 필요한 민감도·비교 결과. MC-V06은 BT-4의 최종 D1–D9 값을 고르지 않는다. 과학적 결과 값 자체는 MC-V06의 PASS/FAIL 기준이 아니다.

## BACKGROUND

BACKGROUND:
- 초안 16절 0단계: 고정 전 판정 확률 합성 시뮬레이션(진짜 Sharpe별 REJECT·RESEARCH_MORE·통과 확률, 10.6·10.7 표의 근사 확인). 결과에 따라 18.1 결정을 확정한 뒤 고정한다.
- `docs/backtest_design.md` BT-3e 절: "MC-V06은 같은 지표·대응·누적 의미를 따라야 한다." BT-3E Work Order DEFERRED: "MC-V06: 같은 대응·지표·누적 의미로 위험 확인 모델링".
- 기존 harness `src/moneylab/research/v06/montecarlo.py`(CLI `research-v06-sim`, 스키마 `moneylab.research_v06_sim/1`)는 위험 한도를 30일 단위 누적 확인으로 근사한다. 이것은 BT-3E의 달력 월 의미와 다르다.
- 아키텍처: `tests/test_backtest_architecture.py`는 backtest → research와 research → backtest의 런타임 import를 모두 금지한다(`docs/backtest_design.md` 536–537행).

## ARCHITECTURE_CONTRACT

ARCHITECTURE_CONTRACT:
- 런타임: research -> backtest = PROHIBITED, backtest -> research = PROHIBITED.
- MC-V06 런타임 구현은 `src/moneylab/research/v06/**` 안에만 둔다.
- MC 위험 모델은 research 계층의 독립 순수 구현으로 만든다. backtest의 공개·비공개 API에 대한 런타임 의존을 만들지 않는다.
- 패키지를 넘는 비교는 테스트(`tests/`)에서만 한다.

## BT3E_SEMANTIC_EQUIVALENCE

BT3E_SEMANTIC_EQUIVALENCE:
- 규범적 동치 범위:
  1. MAX_DRAWDOWN_LOG: 누적 로그수익률에 대한 `1 - exp(-worst)`
  2. 합성 일별 수익률의 달력 월 구분
  3. CUMULATIVE_FROM_L
  4. MONTH_ONLY
  5. gt 비교
  6. ge 비교
- 규범적 동치에 포함하지 않는 것(수익률 생성 의미): backtest 엔진이 만드는 equity, 1시간봉 엔진 경로, 시나리오 기준 시각 처리, ENGINE_WINDOW_BT3B의 F = P − 2 실행 이동, ENGINE_WINDOW_BT3B의 last_day = N − 3 이동.
- 위 제외 항목은 결과와 문서에 한계로 보고한다.
- BT4-Q18은 미해결로 남는다. MC-V06은 엔진 수준 동치나 Q18 해결을 주장하지 않는다.

## PRECISION_REPETITION_CONTRACT

PRECISION_REPETITION_CONTRACT:
- R_OUTER = 10,000 (합성 경로 외부 반복 수)
- B_BOOT = 9,999 (과학 절차: stationary bootstrap 재표본 수)
- K_RAND = 9,999 (과학 절차: B1 무작위 배치·순열 수. 기존 harness의 `draws`에 해당)
- TRUTH_YEARS = 400 (시뮬레이션 정답·보정 경로 길이)
- TARGET_MAX_MC_SE = 0.005
- ADAPTIVE_STOPPING = PROHIBITED
- 네 축은 이름을 따로 두고 manifest에도 따로 기록한다. 서로 같은 것으로 취급하지 않는다.
- 실행 편의를 위해 어떤 값도 몰래 줄이지 않는다. 규범 실행이 불가능하면 멈추고 명시적 계약 결정을 요청한다.

## PILOT_CONTRACT

PILOT_CONTRACT:
- MC_PILOT은 비과학 점검이다. 측정 대상: 실행 시간, 메모리, 산출물·스키마 동작, 결정적 실행, 실패 동작.
- pilot의 통계 결과는 다음에 쓰지 않는다: 기준값 변경, 시나리오 선택 변경, 합격 기준 변경, 최종 D1–D9 선택, R_OUTER·B_BOOT·K_RAND 변경, 전체 실행의 적응적 중단.

## SCENARIO_CONTRACT

SCENARIO_CONTRACT:
- 기존 tier1 합성 시나리오 계열(`tier1_scenarios`)을 DGP·정답 시나리오의 기반으로 쓴다. 구현 중 직접적인 계약 모순이 드러나면 멈춘다.
- 불필요한 Cartesian product를 만들지 않는다. 공통 경로·공통 난수로 평가할 수 있는 후보 차원은 타당한 경우 결정적 후처리로 평가한다(예: 유의수준·Holm·α 배분은 저장한 p값에 기준만 바꿔 적용, θ_min 후보는 같은 bootstrap 표본에서 함께 계산, T_F 후보는 가장 긴 forward 경로의 중간 시점에서 평가).
- D8, D9는 MC-V06의 Monte Carlo 차원이 아니다. BT-4로 미룬다.
- D10(H1 수준 왜곡·엔진 FAR 보정)은 범위 밖이다. 하려면 별도 task가 필요하다.

## SIMULATION_CALENDAR

SIMULATION_CALENDAR:
- MC-V06에는 시뮬레이션 전용 달력 규칙이 필요하다. 이 규칙은 NOT_A_BT4_DECISION이다.
- PRIMARY_SIMULATION_CONVENTION:
  - 합성 forward 시작 L은 UTC 달력 월의 첫날에 고정한다.
  - 합성 일별 관측은 달력 날짜로 하루씩 나아간다.
  - 위험 확인은 달력 월 단위다.
  - forward 평가는 해당하는 경우 12/24/36개월 관측 시점을 포함한다.
- SENSITIVITY_ONLY_CONVENTION: L을 월 중간에 두는 제한된 민감도 규칙을 둘 수 있다. 출력은 따로 표시하며 두 번째 규범 정의가 되지 않는다.
- 비교용으로 기존 30일 위험 동작을 남기면 `LEGACY_30D_COMPARISON`으로 명시하고 규범 결과와 키를 공유하지 않는다.

## ARTIFACT_PROVENANCE_CONTRACT

ARTIFACT_PROVENANCE_CONTRACT:
- 기존 스키마와 다른 새 스키마·버전을 쓴다: `moneylab.research_v06_sim/2`.
- 전체 실행 산출물에 최소한 다음을 기록한다: 기본·난수 seed, 결정적 파생 seed 규칙, R_OUTER, B_BOOT, K_RAND, TRUTH_YEARS, 시나리오 식별, DGP 파라미터, 관련 Procedure·Layout 식별, 시뮬레이션 달력 규칙, 관련 `research/v06` 코드와 `research/stats.py`의 코드 식별, Python·버전 정보, 실행 Git 커밋 식별, 해당하는 경우 UTC 실행 시작·끝, 명시적 SYNTHETIC / NOT_EVIDENCE 표시, 결정적 재현 정보, SHA256SUMS 또는 그에 준하는 무결성 기록.
- 소스 파일 SHA-256을 직접 기록할 수 있으면 그것만을 위해 Git을 subprocess로 부르지 않는다.
- 요약(summary)과 반복별 기록(per-rep records)은 논리적으로 분리한다. 전체 실행의 반복별 기록을 하나의 거대한 in-memory JSON 객체에 모두 두도록 요구하지 않는다.
- 반복별 기록의 정확한 결정적 직렬화는 기존 저장소 설계가 정하지 않았다면 구현에서 정할 수 있다. 어떤 선택이든 결정적 재현성을 지켜야 한다.
- 생성된 시뮬레이션 산출물은 이후 명시적 계약 승인이 없는 한 ignored 합성 출력 저장소에만 둔다.
- 기존 BT-3E 이전 stage1 산출물(예: `v06mc_stage1_6328463`)은 보존하고, 수정·삭제하지 않으며, MC-V06 증거로 쓰지 않는다. 명시적으로 표시한 경우에만 과거 실행 시간 참고로 쓸 수 있다.

## EQUIVALENCE_TEST_CONTRACT

EQUIVALENCE_TEST_CONTRACT:
- 규범적 패키지 간 동치 테스트는 테스트에서만 public ForwardVault / public backtest-facing 동작을 쓴다.
- 규범 계약은 비공개 `backtest/risk_check.py` 함수에 의존하지 않는다.
- 다룰 것: MDD 의미, 달력 월 구분, 두 누적 방식, gt, ge, 기준값 경계 동작.
- 제외된 ENGINE_WINDOW_BT3B −2/−3일 실행 이동에 결과가 좌우되는 사례를 규범 동치로 표시하지 않는다.
- MC-D8/Q18 특성 확인을 위해 gap 없는 합성 신호의 제한된 비교를 넣을 수 있다. 이를 BT4-Q18 해결로 보고하지 않는다.

## IMPORT_SOURCE_REQUIREMENT

IMPORT_SOURCE_REQUIREMENT:
- 공유 ignored `.venv` junction은 C:/MoneyLab/.venv를 가리키며 그 editable 설치는 C:/MoneyLab/src를 가리킬 수 있다.
- 모든 MC-V06 테스트 gate는 테스트 대상 소스가 TARGET_WORKTREE의 `C:/MoneyLab-mc-v06/src`가 되게 한다. 이미 쓰던 명시적 PYTHONPATH 방식이나 그에 준하는 비변경 방식을 쓴다.
- 테스트 증거를 받기 전에 import된 moneylab이 `C:/MoneyLab-mc-v06/src`에서 오는지 명시적으로 확인한다.
- C:/MoneyLab/src를 대상으로 통과한 테스트는 MC-V06 테스트 증거가 아니다.

## NO_RESUME_FEATURE

NO_RESUME_FEATURE:
- MC-V06은 checkpoint/resume 기능을 추가하지 않는다. `src/moneylab/cli.py`는 보호 파일이다(새 CLI 명령·resume 옵션 없음).
- resume/checkpoint 기능 없이는 전체 실행이 불가능하다고 판명되면 멈춘다. 범위를 자동으로 넓히지 않는다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: 완료(이 파일의 C1 커밋 포함)
- IMPLEMENTATION: ALLOWED_FILES만 생성·수정, TEST_GATES 실행(IMPORT_SOURCE_REQUIREMENT 준수)
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, 커밋 하나
- CLEAN_COMMIT_E2E: E2E_GATES의 확인(ignored 출력만)
- MC_PILOT: Gate Authorization이 정한 작은 비과학 실행, 새 ignored 출력 경로에만
- PUSH: TARGET_BRANCH 하나만 `git push -u origin feature/v06-mc-v06`
- PR_CI: Gate Authorization이 명시한 경우 PR 1건 생성, CI 읽기 전용 관찰
- MERGE: Gate Authorization이 명시한 경우 MERGE_METHOD로만
- POST_MERGE_AUDIT: 읽기 전용 구조 감사(fetch는 Gate Authorization이 명시한 경우 `git fetch origin main`만)
- MC_FULL_RUN: Gate Authorization이 정한 규범 전체 실행, 새 ignored 출력 경로에만
- MC_RESULT_AUDIT: 산출물 읽기 전용 감사
- COMPLETE: 최종 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull
- hooks·settings·.claude 변경 또는 guard 우회
- 다른 branch·worktree·untracked·ignored·reference 산출물(기존 MC 산출물 포함) 정리·변경·삭제
- 실데이터·외부 API·수집·주문
- R_OUTER·B_BOOT·K_RAND·TRUTH_YEARS·시나리오 범위·정밀도 요구의 무단 축소, 적응적 중단, 결과를 본 뒤 기준·시나리오·파라미터 변경
- D1–D9 최종 값 선택, BT4-Q18 해결 주장, 엔진 수준 동치 주장
- `.venv` 내용 변경, 패키지 설치·갱신

## ALLOWED_FILES

ALLOWED_FILES:
- M src/moneylab/research/v06/montecarlo.py
- A src/moneylab/research/v06/risk_model.py
- M tests/test_v06_montecarlo.py
- A tests/test_v06_risk_model.py
- M docs/backtest_design.md

`docs/tasks/MC-V06/WORK_ORDER.md`는 C1에서만 만들고 그 직후부터 보호 파일이다. 그 밖의 구현 경로는 허용하지 않는다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/MC-V06/** (예외: C1의 이 파일 최초 생성, 이후 명시적으로 ACCEPTED된 ERRATA-NNN.md의 Ce 최초 생성)
- docs/research_v06_preregistration_draft.md
- configs/**
- src/moneylab/backtest/**
- src/moneylab/research/v06/procedures.py
- src/moneylab/research/v06/synthetic.py
- src/moneylab/research/stats.py
- src/moneylab/cli.py
- tests/test_backtest_* (테스트에서 import·참조는 가능, 수정 불가)
- tests/backtest_helpers.py (테스트에서 import·참조는 가능, 수정 불가)
- .claude/**
- CLAUDE.md
- docs/tasks/** (다른 task 계약)
- ALLOWED_FILES 밖의 모든 경로

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가)

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- E1 목적: GOAL과 같다. 선택지별 판정 특성 표를 만들고 값을 고르지 않는다.
- E2 동치 범위: BT3E_SEMANTIC_EQUIVALENCE와 같다.
- E3 절차와 결과의 분리: PROCEDURE_ACCEPTANCE와 SCIENTIFIC_RESULTS를 섞지 않는다.
- E4 반복 축: PRECISION_REPETITION_CONTRACT와 같다.
- E5 격자와 후처리: SCENARIO_CONTRACT와 같다.
- E6 달력: SIMULATION_CALENDAR와 같다.
- E7 legacy 분리: `LEGACY_30D_COMPARISON`은 규범 결과와 키를 공유하지 않는다.
- E8 provenance: ARTIFACT_PROVENANCE_CONTRACT와 같다.
- E9 아키텍처: ARCHITECTURE_CONTRACT와 같다.
- E10 BT4-Q18: 해결하지 않는다.
- E11 문서: `docs/backtest_design.md`에 MC-V06 절(동치 범위, 제외 항목 한계, 달력 규칙 NOT_A_BT4_DECISION, 반복 축, SYNTHETIC / NOT_EVIDENCE)과 개정 이력 행을 더한다. 사전등록 초안은 바꾸지 않는다.

## PROCEDURE_ACCEPTANCE

PROCEDURE_ACCEPTANCE:
- Stage A / 구현 증거:
  - 규범 동치 테스트 통과
  - 결정적 재현 통과
  - 해당하는 경우 직렬·병렬 결과 일치
  - 아키텍처 테스트 통과
  - 저장소 전체 테스트 suite 통과
  - 금지된 런타임 교차 import 없음
  - 테스트 import 소스가 `C:/MoneyLab-mc-v06/src`임을 확인
- MC_FULL_RUN:
  - 미리 정한 규범 시나리오 격자 완료
  - R_OUTER = 10,000, B_BOOT = 9,999, K_RAND = 9,999
  - 적응적 중단 없음, 실행 중 파라미터 변경 없음
  - 필요한 모든 확률 추정치와 모든 MC SE 보고
  - MC SE ≤ TARGET_MAX_MC_SE(0.005)
  - provenance manifest 존재, 무결성 해시 존재
  - 출력에 SYNTHETIC / NOT_EVIDENCE 표시
- MC_RESULT_AUDIT:
  - 산출물이 승인된 코드·설정 식별과 일치
  - 반복 수가 계약과 일치
  - 시나리오 범위가 계약과 일치
  - 무결성 해시 검증
  - 결과를 본 뒤 파라미터를 조정한 흔적 없음
  - 과학적 결과를 절차 PASS/FAIL 기준으로 바꾸지 않고 보고

## SCIENTIFIC_RESULTS

SCIENTIFIC_RESULTS: REJECT 비율, RESEARCH_MORE 비율, PAPER·통과 비율, study 단위 FWER, RISK_LIMIT 발동률, 근사표와의 차이, 제한된 legacy·민감도 비교. 이것들은 보고하는 결과다. 예상 밖이거나 불리한 값 자체는 MC-V06 실패가 아니다.

## TEST_GATES

TEST_GATES:
- IMPORT_SOURCE_REQUIREMENT에 따른 import 소스 확인을 먼저 한다.
- 새 테스트 `tests/test_v06_risk_model.py`: EQUIVALENCE_TEST_CONTRACT의 범위
- `tests/test_v06_montecarlo.py`: 결정적 재현, 직렬·병렬 일치, 반복 축 이름 분리, 스키마 `moneylab.research_v06_sim/2` manifest 필드, summary·per-rep 분리, legacy 키 분리, NOT_EVIDENCE 표시
- 아키텍처 테스트(`tests/test_backtest_architecture.py`, `tests/test_architecture_and_cli.py`)
- 전체 pytest, failed 0 / errors 0
- `git diff --check` 깨끗함, 변경 파일 집합 ⊆ ALLOWED_FILES

## E2E_GATES

E2E_GATES:
- clean 구현 커밋에서 TEST_GATES 재실행(import 소스 확인 포함)
- 작은 결정적 실행으로 같은 seed의 산출물 바이트가 같은지 확인. 출력은 새 ignored 경로에만 둔다. 과학 결과로 쓰지 않는다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 커밋 SHA·parent·tree, Work Order sha256, 커밋 파일 집합, merge parent·tree
- CLAUDE_REPORTED: 테스트·E2E·pilot·전체 실행 결과, 산출물 해시
- INDEPENDENT: PR CI 결과, GitHub 화면(사용자 확인)
- 모든 MC 결과는 SYNTHETIC / NOT_EVIDENCE로 표시한다. Claude가 실행한 결과를 INDEPENDENT로 표시하지 않는다.

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

## DEFERRED_TO_BT4

DEFERRED_TO_BT4:
- 최종 D1–D9 값
- 최종 위험 정책 값
- 정식 개월 수 → W_end 변환(DP4)
- DP2, DP3
- BT4-Q18
- U4–U6
- D10
- MC-V06 결과를 최종 고정 사전등록 문서에 반영할지와 그 방법
- MC-V06은 이 항목들을 몰래 정하지 않는다.

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, Work Order sha256 불일치
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기와 base 상태 불일치
- guard deny, 권한 창 거절
- 테스트 실패·에러, hard gate 불일치
- 테스트 import 소스가 `C:/MoneyLab-mc-v06/src`가 아님
- 계약 모순, 상위 규칙과 충돌(tier1 시나리오 기반과의 직접 모순 포함)
- 규범 실행이 불가능하거나 resume/checkpoint 없이는 불가능함
- 반복 수·시나리오·정밀도를 줄여야만 진행할 수 있음
- 예상하지 못한 untracked 파일
