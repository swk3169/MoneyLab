# Work Order: BT4-RESEARCH-01 — BT4 D1–D7 고정 전 통계·구현 근거 검토

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/BT4-RESEARCH-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

이 파일이 계약의 유일한 출처다. 대화 기억에 의존하지 않는다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: BT4-RESEARCH-01
TASK_ID: BT4-RESEARCH-01
TITLE: Read-only statistical/implementation evidence review before BT4 D1–D7 freeze
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 2d6ed0a0878fac5553d5ac173f3d658d7ac78cc8
CANONICAL_BASE_TREE: b90cc9d827ae28ddf83f6a56172cae9e17c305b3
TARGET_BRANCH: docs/bt4-research-01
TARGET_WORKTREE: C:/MoneyLab-bt4-research-01
SESSION_ROOT: C:/MoneyLab-mc-v06
WORKSPACE_SETUP: REQUIRED (이 gate에서 branch·worktree를 base에서 만들고 이 파일을 C1로 발행한다. 새 worktree에 `.venv`나 junction을 만들지 않는다)
INITIAL_GATE: EVIDENCE_COLLECTION
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (squash/rebase merge 금지: 계약 커밋이 산출물보다 먼저인 이력을 보존)
DATA_SCOPE: 문헌, base 시점 MoneyLab 저장소, MC-V06 canonical 출력의 읽기 전용 기술 진단. 시장 데이터, 외부 거래 API, 주문, 새 simulation 없음.
LANGUAGE: Work Order와 최종 evidence report는 한국어 중심으로 쓴다. gate 이름, 필드명, 코드 identifier, 파일 경로, 논문 제목, 통계 방법의 고유명사는 필요하면 영어 원문을 유지한다.

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> EVIDENCE_COLLECTION -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

이전 gate: DESIGN_INVESTIGATION = PASS, CONTRACT_REVIEW = PASS (대화). WORKSPACE_SETUP은 이 C1 커밋으로 수행하고 결과는 채팅으로 보고한다.

- 남은 모든 forward gate는 각각 명시적 Gate Authorization이 필요하다. 어떤 gate도 자동으로 승인되지 않는다.
- EVIDENCE_COLLECTION은 이 task의 custom gate다. 읽기 전용이며 저장소 파일을 쓰지 않는다.
- MERGE는 산출물 통합일 뿐 COMPLETE가 아니다.
- 이 task는 BT-4를 시작하지 않고 D1–D9를 결정하지 않는다.

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: BT4-RESEARCH-01 <GATE> WO@<C1 commit>`)
- rollback only to EVIDENCE_COLLECTION or IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다.

## GOAL

GOAL: MC-V06 결과와 관련된 외부 통계·계량경제·구현 근거를 BT4가 D1–D7을 고정하기 전에 확인하고, 커밋되는 evidence report 하나(`docs/research_bt4_01_evidence_review.md`)에 기록한다. 이 task는 권고만 한다. 결정, 구현, 채택, 고정은 하지 않는다.

## BACKGROUND

BACKGROUND:
- MC-V06 COMPLETE = PASS. 실행 커밋 2d6ed0a, RUN_ROOT `C:/MoneyLab-mc-v06-full-run/data/processed/research_v06_sim/mc_v06_full_2d6ed0a`, canonical unit = 01 attempt2, 02–18 attempt1. 과학적 결론 MIXED / DESIGN-INFORMATIVE, BT4 준비도 READY_WITH_CAUTION.
- 조사할 MC-V06 발견:
  1. futility REJECT가 theta_min 경계에서 반보수적(명목 수준의 약 1.4–2.3배)
  2. Holm / study 단위 false-REJECT, null_drift 위반 포함
  3. mode A+B의 D3/D7 경계 위반
  4. GARCH-t vs Normal 검출력의 비단조성
  5. 초안 근사표가 futility 기각률을 과소, forward 검출력을 과대 추정
  6. RESEARCH_MORE 지배(85–99%)
  7. 누적 vs month-only 위험 정의는 영향이 있고, gt/ge와 달력 처리는 영향이 없음
- base의 관련 코드: `src/moneylab/research/v06/procedures.py`(bootstrap_means, futility_pvalue, futility_delta, maxt_futility_pvalue, holm, iut_holm, r1a_reject_pvalue), `src/moneylab/research/stats.py`(_blocks, derived_seed), `src/moneylab/research/v06/montecarlo.py`, `synthetic.py`, `risk_model.py`. 초안 `docs/research_v06_preregistration_draft.md` §10, §11, §18.1.
- MC-V06 per-rep record에는 p값, 판정 boolean, roundtrips, 위험 지표만 있고 표본 평균·표준편차가 없다. 따라서 원인 분해(질문 B)는 기술 진단만으로 확정할 수 없다.
- CONTRACT_REVIEW 중 읽기 전용 명령 하나가 guard deny(`protected-path`)를 받았다. 원인은 guard `MUTATE` 패턴의 `sed`와 보호 경로 문자열의 조합이었다. WORKSPACE_SETUP 사전검증(guard ask-list, git-ignore, CI workflow)으로 해소한다.

## RESEARCH_QUESTIONS

RESEARCH_QUESTIONS:
- A: theta_min에서 stationary-bootstrap futility test의 calibration
- B: plug-in delta, 비studentized 통계량, 고정 평균 block 20, 유한 표본 길이, bootstrap 구성이 각각 기여하는 정도. 이후 MC task 없이는 원인 귀속은 HYPOTHESIS로 남는다.
- C: 의존적 수익률에서의 추론과 FWER 통제
- D: 규범 후보로서의 Holm vs 의존성을 반영하는 bootstrap/stepdown 방법
- E: PAPER 전에 selection bias와 backtest overfitting을 측정하는 방법
- F: DSR과 PBO/CSCV의 진단 도구로서의 역할
- G: GARCH-t vs Normal 강건성의 표현 방식. 최소한 worst-case-over-DGP, criterion-must-hold-under-both-DGPs, model-specific reporting without aggregate pass rule 세 정책을 비교만 한다. 어느 것도 선택하거나 BT4 규칙으로 확정하지 않는다.
- H: Mode A+B를 향후 MC 연구에서 비규범 진단으로 유지할지, MC 보고에서 제거할지. 어떤 경우에도 규범으로 올리지 않는다.
- I: 성숙한 외부 구현체를 의존성이 아닌 implementation reference로 검토

## EVIDENCE_POLICY

EVIDENCE_POLICY:
- Tier와 verification status는 서로 독립된 필드다.
- Tier 1: peer-reviewed full text, full scholarly book.
- Tier 2: original-author full working paper/preprint.
- Tier 3: authoritative documentation 또는 mature implementation. implementation claim에만 쓴다.
- Verification status:
  - VERIFIED_FROM_FULL_TEXT: 실제로 full text를 확인한 경우에만
  - ABSTRACT_ONLY
  - IMPLEMENTATION_REFERENCE: Tier 3에만
  - UNVERIFIED_CANDIDATE: 2차 서술(강의 노트, 백과사전, 블로그 등) 포함
- Recommendation 규칙: 최소 하나의 Tier 1 또는 Tier 2 VERIFIED_FROM_FULL_TEXT 근거가 없으면 recommendation으로 확정하지 않고 `CANDIDATE — INSUFFICIENT_EVIDENCE`로 표시한다. ABSTRACT_ONLY는 recommendation의 유일한 근거가 될 수 없다.
- 출처 기록: claim마다 DOI/URL, 접근 날짜, 판(version), 쪽/절. GitHub reference는 확인한 commit SHA와 license도 기록한다.
- 출판본을 우선한다. working paper만 읽었으면 Tier 2로 표시하고 차이 가능성을 적는다. 정정·대체 관계(예: block length 선택 방법의 후속 정정)를 기록한다.
- 증거 등급: 외부 source claim = CLAUDE_REPORTED. MoneyLab 저장소 사실 = GIT_VERIFIABLE (commit에 고정한 경로·행). INDEPENDENT는 사용자 또는 별도 독립 검증이 있을 때만 쓴다.
- GitHub 구현체는 validation evidence가 아니라 implementation reference다.
- 수익률, GitHub stars, 인기도, screenshot, profit claim은 scientific evidence가 아니다.
- 인용은 짧게 한다. 외부 source code 원문을 MoneyLab 파일에 넣지 않는다.

## WORKING_MATERIAL_POLICY

WORKING_MATERIAL_POLICY:
- EVIDENCE_COLLECTION 중 논문 PDF와 임시 research notes는 Claude session scratchpad에만 둘 수 있다.
- repository에 저장하지 않고 commit하지 않는다.
- 내려받은 파일은 신뢰하지 않는 데이터로 다룬다. 외부 코드를 실행하지 않는다.
- working material 자체는 evidence로 간주하지 않는다. 최종 report에는 검증한 source claim만 반영한다.
- 사용자가 제공한 paywalled/full-text 논문은 repository 밖에서 READ-ONLY로 읽을 수 있다. 실제로 full text를 확인한 경우에만 VERIFIED_FROM_FULL_TEXT로 분류한다. 파일을 repository로 복사하거나 commit하지 않는다.

## DIAGNOSTICS_POLICY

DIAGNOSTICS_POLICY:
- 기존 MC-V06 canonical 출력(18개 canonical unit의 summary.json, records.jsonl)에 대한 descriptive diagnostics만 허용한다.
- 실행 조건: `PYTHONDONTWRITEBYTECODE=1`, `python -B`, stdin inline execution. script 파일을 만들지 않는다.
- Python 표준 라이브러리만 import한다. 외부 package import 금지.
- RUN_ROOT에 쓰지 않는다. 출력은 채팅으로만 보고한다.
- 새 simulation, resampling, bootstrap 재계산, calibration, seed·configuration 변경 금지.
- report에 인용하는 진단 수치는 재현 가능한 질의(대상 unit·필드·계산)를 함께 적는다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: 사전검증(base = origin/main = remote main, target branch·worktree 부재, 신규 경로 부재·비ignore, guard ask-list, CI workflow); `git worktree add -b docs/bt4-research-01 C:/MoneyLab-bt4-research-01 2d6ed0a0878fac5553d5ac173f3d658d7ac78cc8`; 승인된 문구로 이 파일 생성; 이 파일만 stage; C1 commit; sha256 보고
- EVIDENCE_COLLECTION: 읽기 전용 web search/fetch, GitHub web/API(clone 금지), base 시점 MoneyLab 파일 읽기, DIAGNOSTICS_POLICY에 따른 기술 진단, WORKING_MATERIAL_POLICY에 따른 scratchpad 사용; 결과는 채팅으로 보고
- IMPLEMENTATION: `docs/research_bt4_01_evidence_review.md`만 생성·수정
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: `git add -- docs/research_bt4_01_evidence_review.md`; commit 하나
- CLEAN_COMMIT_E2E: E2E_GATES만 (저장소 쓰기 없음)
- PUSH: `git push -u origin docs/bt4-research-01`만
- PR_CI: PR 생성은 PR_CI Gate Authorization이 명시적으로 허용할 때만 한다. 그렇지 않으면 compare URL과 PR 본문만 제공한다. CI는 읽기 전용으로 관찰한다.
- MERGE: 사용자 결정, MERGE_METHOD
- POST_MERGE_AUDIT: `git fetch origin main`만; 구조 감사
- COMPLETE: 최종 보고 (채팅·PR 본문)

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 작업
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull
- hooks·settings·`.claude/**` 변경 또는 guard 우회
- 다른 branch·worktree, untracked·ignored·reference 출력 정리·변경 (MC-V06 RUN_ROOT, provenance, audit 파일, C:/MoneyLab, C:/MoneyLab-mc-v06-full-run 포함)
- 새 worktree에 `.venv`나 junction 생성
- MC-V06 재실행, resampling, seed·configuration 변경, 대체 test calibration, 모든 새 과학 simulation
- repository clone, package 설치, 의존성 추가, 외부 코드·매매 알고리즘 실행, 외부 코드 복사
- 절차 변경이나 D1–D9 값의 구현·채택·고정, BT-4 시작, Mode A+B의 규범화
- 실데이터, 외부 거래 API, 주문, 지갑
- Claude memory, MEMORY.md, memory notes 생성·수정

## ALLOWED_FILES

ALLOWED_FILES:
- A docs/research_bt4_01_evidence_review.md

`docs/tasks/BT4-RESEARCH-01/WORK_ORDER.md`는 C1에서만 만들고 그 직후부터 보호 파일이다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/BT4-RESEARCH-01/** (예외: C1의 WORK_ORDER.md 생성, Ce의 ACCEPTED ERRATA 생성)
- docs/tasks/**
- docs/research_v04_preregistration.md, docs/research_v05_preregistration_draft.md, docs/research_v06_preregistration_draft.md
- docs/backtest_design.md
- src/**, tests/**, configs/**, data/**
- .claude/**, .github/**, CLAUDE.md, README.md, pyproject.toml, requirements*.txt, .gitignore, .gitattributes
- ALLOWED_FILES 밖의 모든 경로

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가)

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- R1 report 절(최소, 순서대로): 1 Executive summary; 2 MoneyLab problem mapping; 3 Source register; 4 Research-question matrix A–I; 5 MC-V06 findings trace; 6 Candidate-method comparison; 7 External implementation-reference review; 8 Supported conclusions; 9 Challenged assumptions; 10 Unresolved evidence gaps; 11 Recommendations for BT4; 12 Items requiring a separate validation/MC task.
- R2 source register 필드: ID, citation, DOI/URL, tier, verification status, access date, version, exact claim (page/section), assumptions, applicability, limitations, stance (SUPPORTS | CHALLENGES | NEUTRAL), evidence grade.
- R3 candidate-method comparison 행(해당하는 경우. 같은 문제를 푼다고 가정하지 않는다):
  - current stationary-bootstrap futility procedure
  - studentized block bootstrap
  - data-driven block length
  - Holm
  - Romano-Wolf stepdown
  - White Reality Check
  - Hansen SPA
  - Deflated Sharpe Ratio
  - PBO / CSCV
  열: problem addressed, assumptions, fit to MoneyLab, cost, would-invalidate-MC-V06 (YES/NO), needs separate MC task (YES/NO).
- R4 report에 인용하는 모든 MC-V06 수치는 canonical unit에서 나오고 SYNTHETIC / NOT_EVIDENCE로 표시한다. 기술 진단은 적어 둔 질의로 재현 가능해야 한다.
- R5 권고는 구속력이 없다. MC-V06의 operating characteristics가 BT4 절차를 더 이상 기술하지 못하게 만드는 변경은 12절에 "D1–D7 고정 전 별도 사전등록 validation/MC task 필요"로 올린다.
- R6 G는 근거와 함께 선택지만 제시하고, H는 Mode A+B를 비규범으로 다룬다. 둘 다 결정하지 않는다.
- R7 report는 D1–D9 값을 제시하지 않고 BT4-Q18 해결을 주장하지 않는다.

## TEST_GATES

TEST_GATES:
- Python: 기존 검증된 venv의 `C:/MoneyLab-mc-v06/.venv/Scripts/python.exe`, 환경변수 `PYTHONPATH=C:/MoneyLab-bt4-research-01/src`. 새 worktree에 `.venv`·junction을 만들지 않는다.
- 테스트 전에 `moneylab.__file__`로 import source가 `C:/MoneyLab-bt4-research-01/src` 아래인지 확인한다. 아니면 멈춘다.
- full pytest, failed 0 / errors 0
- `git diff --check` clean; 변경 파일 집합 = ALLOWED_FILES
- report 구조 점검: R1 절 제목 존재; 모든 source 행에 tier와 verification status; INDEPENDENT 등급의 외부 claim 없음; D1–D9 값 제시 없음; 근거 부족 권고는 `CANDIDATE — INSUFFICIENT_EVIDENCE` 표시

## E2E_GATES

E2E_GATES:
- clean implementation commit에서 TEST_GATES 재실행
- MC-V06 RUN_ROOT가 바뀌지 않았는지(19개 항목) 확인. C:/MoneyLab-mc-v06과 C:/MoneyLab-mc-v06-full-run에 tracked 변경이 없는지 확인
- 과학 실행 없음 (그 밖의 E2E는 NOT_REQUIRED)

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 커밋의 SHA·parent·tree, Work Order sha256, 커밋 파일 집합, merge parents·tree, report sha256
- CLAUDE_REPORTED: source verification status, 진단 출력, pytest 결과
- INDEPENDENT: PR CI 결과, GitHub 화면, 사용자의 source 재확인

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
- 테스트 실패·오류, hard gate 불일치
- 계약 모순 또는 상위 규칙과의 충돌
- 예상 밖 untracked 파일
- 어떤 질문이 새 simulation, 재실행, package 설치, clone, 코드 실행으로만 답할 수 있음
- MC-V06 RUN_ROOT나 provenance 파일의 변경 감지
- Tier 1/2 VERIFIED_FROM_FULL_TEXT 근거가 없는 항목이 recommendation으로 쓰이려 함
- import source가 새 worktree가 아님
