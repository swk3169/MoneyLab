# Work Order: BT4-FUTILITY-02 — BT4-FUTILITY-01 G7 표본의 사후 진단 분석 (POST_HOC_DIAGNOSTIC)

이 파일은 불변이다. 발행(G1의 C1 커밋) 후 수정하지 않는다. 계약 변경은 `docs/tasks/BT4-FUTILITY-02/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.
CF_CANDIDATE_FREEZE에서 저장소 밖에 만든 이 파일의 후보는 발행 전 후보일 뿐이며, 아래 `STATUS: ISSUED`는 G1의 C1 커밋이 완료된 시점에 효력이 생긴다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: BT4-FUTILITY-02
TASK_ID: BT4-FUTILITY-02
TITLE: BT4-FUTILITY-01 G7 CORE 기록의 읽기 전용 사후 진단(1차 라벨 5개와 EXPLORATORY 진단)
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: d2fcaf64b5fb87f502afba29572be340f653be24
CANONICAL_BASE_TREE: 9bd42f835ef48b44246bde009ce7adb3b751aa1f
CANONICAL_BASE_PARENTS: 6725ff68068c14b5241bde04c39d6a5ffeb50fa7
BASE_REMOTE_REF: origin/feature/bt4-futility-diag (main이 아니다. README:41의 "base SHA가 원격과 일치"는 이 ref로 판정한다)
BASE_VERIFICATION: 2026-11-05 `git ls-remote origin refs/heads/feature/bt4-futility-diag` = d2fcaf64…, 로컬 HEAD·tree 일치
TARGET_BRANCH: feature/bt4-futility-02
TARGET_WORKTREE: C:/MoneyLab-bt4-futility-02
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: C0_CONTRACT_REVIEW
ACCEPTED_ERRATA: NONE
PR_STRATEGY: OPTION_B
PR_BASE: feature/bt4-futility-diag
PR_HEAD: feature/bt4-futility-02
PR_TYPE: DRAFT
PR_POLICY: DO_NOT_MERGE
MERGE_METHOD: NOT_APPLICABLE (MERGE·POST_MERGE_AUDIT gate 없음. README §13 merge 사전 검증 1(base = main, non-draft)이 성립하지 않으므로 merge 경로는 닫혀 있다)
REQUIRED_CI_CHECKS: ci-tests / pytest (job 결론 SUCCESS로 판정. workflow 전체 결론으로 판정하지 않는다)
OPTIONAL_CI_CHECKS: ci-tests / pytest-linux-experimental (continue-on-error, 비차단. 알려진 실패는 기록만)
EXPECTED_REMOTE_MAIN: 5dcf70735f51159053b2387412d9a6ab18abfdb6
PYTHON_VERSION: 3.14.8 (Windows. 실행 파일 경로는 고정하지 않고 D1·D10에서 확인한다)
RESEARCH_CLASSIFICATION: POST_HOC_DIAGNOSTIC
INDEPENDENT_CONFIRMATION: NO
EVIDENCE_CLASS_OF_RESULTS: SYNTHETIC / NOT_EVIDENCE
PUBLIC_RESULT_REPORT: NOT_AUTHORIZED
PUBLIC_REPORT_COMMIT: DEFERRED
RESULT_PERSISTENCE: LOCAL_IGNORED_OUTPUT
TERMINAL_STATE: TASK_COMPLETE = NOT_DECLARED (이 Work Order에서 COMPLETE에 도달하지 않는다)
RELATED_TASKS: BT4-FUTILITY-01 (G7 COMPLETE, G8a SUPERSEDED_NOT_EXECUTED, PR #37 KEEP_OPEN_UNCHANGED), MC-V06 (COMPLETE). VALID(독립 검증, seed 이름공간 "FUTVAL")는 별도 Work Order이며 범위 밖이다.

## GATE_SEQUENCE

GATE_SEQUENCE: C0_CONTRACT_REVIEW -> CF_CANDIDATE_FREEZE -> G1_WORK_ORDER_ISSUE_AND_WORKSPACE_SETUP -> G2_IMPLEMENTATION -> G3a_PRECOMMIT_AUDIT -> G3b_COMMIT -> G3c_CLEAN_COMMIT_E2E -> G4a_PUSH -> G4b_PR_CI_DRAFT_PR -> G4c_PR_CI_REVIEW -> G5_F2_INPUT_INTEGRITY -> G6_F2_DIAGNOSTIC_ANALYSIS -> G7_F2_RESULT_AUDIT -> G8_CLOSEOUT

README 표준 gate 대응: C0 = CONTRACT_REVIEW, G1 = WORKSPACE_SETUP(Work Order 발행 포함), G2 = IMPLEMENTATION, G3a = PRECOMMIT_AUDIT, G3b = COMMIT, G3c = CLEAN_COMMIT_E2E, G4a = PUSH, G4b·G4c = PR_CI(승인 2건으로 분리). CF·G5~G8은 이 Work Order의 task 전용 gate다. MERGE·POST_MERGE_AUDIT·COMPLETE는 실행하지 않는다(건너뛰기가 아니라 이 Work Order의 범위 밖).

커밋 이름: C1 = Work Order 발행 커밋(G1, README §6), C2 = 분석 코드 커밋(G3b). "C1"은 커밋 이름으로만 쓰고 gate 이름으로 쓰지 않는다.

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 각 gate는 사용자의 Gate Authorization 하나로만 시작하고, 보고 후 멈춘다. 이전 gate의 승인이나 PASS는 다음 gate의 승인이 아니다. 어떤 gate도 자동 실행하지 않는다.
- 승인 식별자
  - C0, CF: `GATE_AUTHORIZATION: BT4-FUTILITY-02 <GATE>`(해시 없음)
  - G1: `GATE_AUTHORIZATION: BT4-FUTILITY-02 G1_WORK_ORDER_ISSUE_AND_WORKSPACE_SETUP CANDIDATE_PATH: <경로> WO_SHA256: <64 hex> WO_BYTES: <n> WO_LINES: <n>`(CF가 보고한 값)
  - G2 이후: `GATE_AUTHORIZATION: BT4-FUTILITY-02 <GATE> WO@<C1 커밋 SHA>`
- G2는 사용자가 G1 보고의 Work Order sha256을 채팅에서 확인한 뒤에만 승인할 수 있다(README:93).
- CF 후보 파일은 생성 후 수정하지 않는다. 문구 변경이 필요하면 새 CF 승인으로 새 파일명(`WORK_ORDER.r<N>.md`)에 만들고 세 값을 다시 보고한다. 이전 후보 파일은 보존한다.
- rollback은 명시적 승인으로 G2(IMPLEMENTATION)로만 한다. G5 시작 이후 분석 코드 변경은 새 study다(새 Work Order).
- G7에서 결과를 연 뒤에는 이 Work Order 안에서 G6을 다시 실행하지 않는다. 재실행이 필요하면 STOP하고 사용자가 결정한다.
- COMMIT 이후 수정은 새 커밋으로만 한다. amend는 금지한다. G3b 이후 새 커밋이 생기면 G3c·G4a·G4b(또는 PR 갱신 확인)·G4c를 다시 통과해야 G5에 들어간다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약)이 이 Work Order보다 우선한다. 충돌하면 상위 규칙을 따르고 STOP한다. 실거래·주문·지갑·API 키는 범위 밖이다. API 응답 구조를 추측하지 않는다(CLAUDE.md 절대 규칙 5).

## GOAL

GOAL: BT4-FUTILITY-01이 G7에서 생성한 CORE 기록과 V-4 산출물을 읽기 전용으로 재사용해, (1) BT4-FUTILITY-01 사전등록의 1차 라벨 5개를 기존 판정 함수 그대로 계산하고 (2) 이 Work Order에서 정의를 고정한 EXPLORATORY 진단을 계산한다. 절차를 채택하거나 VALIDATED를 판정하지 않는다. 결과는 공개하지 않고 로컬 ignored 출력과 채팅 감사로만 남긴다.

## BACKGROUND

BACKGROUND:
- BT4-FUTILITY-01은 G7 CORE_MAIN_RUN COMPLETE다(E1 1000 unit, P0 1900 unit, V-4 VERIFIED, 2026-11-04). G8a는 실행되지 않았다(g8a-* 디렉터리 0개, g7-core-lock/000001.released 존재).
- G8a 사전 검토에서, BT4-FUTILITY-01 WO:440·442·341이 요구하는 보고 항목 6개(RD 분포, α 0.025·0.10, oracle 분해, V-4 K=20·lag-1, 설명 비율, PD-4)를 커밋된 코드가 계산하지 않음이 확인됐다. oracle 분해와 f-창 설명 비율은 계약에 식이 없다.
- 사용자는 2026-11-04~05 대화에서 OPTION_C(기존 연구 보존 + 새 Work Order), DESIGN_A(G7 출력 읽기 전용 재사용), CODE_BASELINE d2fcaf6, PR #37 KEEP_OPEN_UNCHANGED, NO_MERGE_WITHOUT_SEPARATE_CONTRACT_DECISION, PR OPTION_B, 결과 비공개를 결정했다.
- 이 Work Order는 BT4-FUTILITY-01의 G8a를 SUPERSEDED_NOT_EXECUTED로 선언한다. 이 선언은 이 Work Order 안의 기록이며 BT4-FUTILITY-01 Work Order·ERRATA를 바꾸지 않는다. BT4-FUTILITY-01의 G8a 보고 의무(oracle 분해, f12·f24·f36 설명 비율 포함)는 완료되지 않은 채 남으며, 이 Work Order는 그것을 완료했다고 주장하지 않는다.

## SCOPE

SCOPE:
모든 항목은 G6에서 계산된다. 계산할 수 없으면 G6 전체가 STOP한다.
부분 결과를 기록하고 진행하는 경로는 없다.

REQUIRED:
- R1 V-1 RD 분포 (D4)
- R2 α=0.025/0.10 대비 (D5)
- R3 PD-4 SD 제외 부분집합 (D6)
- R4 Primary label 5개 (D3)

REQUIRED_AFTER_REGEN_MATCH:
G6 첫 단계 D7-a의 K=40 재생성 MATCH 뒤에만 계산한다.
MISMATCH면 G6 전체 STOP.
- C5 V-4 K=20 민감도 (D7-b)
- C6 V-4 batch lag-1 (D8, K=40과 K=20)
- C7 V-4 conf 설명 비율 (D9)

EXCLUDED:
- oracle 분해(위치 λ, 척도 κ, 결합 잔차, cross-fitting): 정의 없음
- f12·f24·f36 설명 비율: 창별 r_obs·σ 정의 없음
- G7X EXPLORATORY 묶음, 새 MC 표본 생성, VALID
- 공개 결과 보고서와 그 커밋

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- CF: 저장소 밖 `C:/MoneyLab-Context-Intake/contract-review/BT4-FUTILITY-02/WORK_ORDER.md`(재발행은 `WORK_ORDER.r<N>.md`) 하나 생성. LF, UTF-8 BOM 없음, 줄 끝 공백 없음, tab 없음. 같은 경로가 이미 있으면 STOP. 생성 후 수정하지 않는다
- G1: (1) 후보 파일 sha256·bytes·lines가 승인된 세 값과 일치 확인 (2) `git worktree add -b feature/bt4-futility-02 C:/MoneyLab-bt4-futility-02 d2fcaf64b5fb87f502afba29572be340f653be24` 1회 (3) 후보 바이트를 binary로 `docs/tasks/BT4-FUTILITY-02/WORK_ORDER.md`에 복사(줄끝 변환 없음) (4) 복사본 세 값 재확인 (5) 그 파일만 경로 지정 stage, C1 커밋 1회 (6) `git cat-file blob HEAD:docs/tasks/BT4-FUTILITY-02/WORK_ORDER.md`의 sha256 = WO_SHA256 확인
- G2: ALLOWED_FILES의 G2 파일 생성·수정, 테스트 실행(stage·commit 없음)
- G3a: 읽기와 `git diff --check`만
- G3b: G2 파일 두 개만 경로 지정 stage, C2 커밋 1회
- G3c: HEAD = C2 clean에서 전체 pytest(합성 fixture만, ignored tmp 출력만)
- G4a: `git push -u origin feature/bt4-futility-02` 1회
- G4b: `gh pr create --draft --base feature/bt4-futility-diag --head feature/bt4-futility-02 --title <승인 제목> --body <승인 본문>` 1회(Gate Authorization에 PR_CREATE: YES, 저장소, base, head, head SHA, 제목·본문)
- G4c: D13의 읽기 전용 gh 조회(각 1회, polling 없음)
- G5·G6: D10 실행 절차만. (0) D10 단계 0의 Python 실행 환경 확인 1회 (1) D10 단계 1의 NEW_OUTPUT_ROOT 확인·최초 생성 (2) 시도 디렉터리를 `mkdir`(재귀·-p 없음) 1회로 배타적 생성. 이미 있으면 STOP (3) 엔트리포인트 1회 실행, stderr는 그 시도 디렉터리의 stderr.bin으로 리디렉션. SOURCE_OUTPUT_ROOT는 읽기만
- G7: G6 출력 파일 열람과 채팅 보고(1회)
- G8: 읽기 전용 보존 확인

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- C:/MoneyLab-bt4-futility-diag worktree와 feature/bt4-futility-diag branch의 변경·checkout·커밋·push·삭제
- PR #37 변경(edit, close, merge, ready, comment, review 상태 변경)
- 이 Work Order의 PR에 대한 `gh pr merge`, `gh pr ready`, `gh pr edit`, `gh pr close`, auto-merge, CI 재실행
- CF 후보 파일의 수정·덮어쓰기·삭제
- SOURCE_OUTPUT_ROOT 아래 파일의 생성·수정·삭제·이동
- 실패한 G5·G6 출력 디렉터리의 열람·수정·삭제·재사용
- G7 이전 stderr.bin 내용 열람
- 작업 파일의 줄끝 변환·재checkout(D1 정규화는 메모리에서만)
- Python·패키지의 설치·업그레이드·재설치, venv 생성·변경, 환경 변수로 다른 소스 경로 주입(D10 단계 0이 확인한 경로 외)
- BT4-FUTILITY-01 G7·G8a·G5X·G6X·G7X 실행 또는 재실행
- 결과값(효과, 기각률, p, SE, Δ̂, SR_eval, 라벨, ρ̂₁, 비율, batch Sharpe)을 G7 이전에 열람·출력하거나, 어느 때든 PR 본문·commit message·CI 로그·공개 문서·테스트 출력에 쓰기
- 임시 스크립트, scratchpad 분석. 분석은 커밋된 코드로만 한다
- 의존성 추가(stdlib only)
- `git add .`·`-A`, amend, force push, reset·restore·stash·clean·rebase·cherry-pick, `--no-verify`, git config, fetch
- guard·hook·settings 변경·우회, 전체 경로 gh 표기(`agent_workflow.md`:87)

## ALLOWED_FILES

ALLOWED_FILES:
- A docs/tasks/BT4-FUTILITY-02/WORK_ORDER.md (G1 C1 전용)
- A src/moneylab/research/v06/futility_02.py (G2)
- A tests/test_v06_futility_02.py (G2)

PR_SCOPE: `git diff --name-only origin/feature/bt4-futility-diag...HEAD` = 위 세 경로(README §6 "PR 전체 = ALLOWED_FILES ∪ docs/tasks/<TASK_ID>/**"와 일치)

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/BT4-FUTILITY-02/** (G1 C1 최초 생성 제외), docs/tasks/BT4-FUTILITY-01/**, docs/tasks/MC-V06/**, docs/tasks/BT4-RESEARCH-01/**, docs/tasks/BT4-DESIGN-01/**
- .claude/**, .github/**, CLAUDE.md, AGENTS.md, docs/agent_workflow.md, docs/tasks/README.md, docs/tasks/TEMPLATE.md
- src/moneylab/research/v06/futility_diag.py, tests/test_v06_futility_diag.py
- docs/research_bt4_futility_diag_preregistration.md, configs/bt4_futility_diag.toml
- src/moneylab/research/stats.py, src/moneylab/research/v06/__init__.py, procedures.py, montecarlo.py, synthetic.py, risk_model.py
- docs/research_v06_preregistration_draft.md, docs/research_v04_preregistration.md, configs/research_v04.toml, configs/backtest_costs.toml
- src/moneylab/cli.py, src/moneylab/__main__.py, pyproject.toml, requirements*.txt
- docs/research_bt4_01_evidence_review.md, docs/bt4_design_01.md, docs/backtest_design.md, knowledge/**

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (C1 생성 예외는 G1의 그 파일 하나뿐)

## INPUTS

SOURCE_WORKTREE: C:/MoneyLab-bt4-futility-diag (HEAD d2fcaf64…, branch feature/bt4-futility-diag, clean이어야 한다)
SOURCE_OUTPUT_ROOT: C:/MoneyLab-bt4-futility-diag/data/processed/research_v06_futility_diag (읽기 전용)
NEW_OUTPUT_ROOT: C:/MoneyLab-bt4-futility-02/data/processed/research_v06_futility_02 (G5 전에 `git check-ignore`로 ignored 확인)

## INPUT_HASH_MANIFEST

| 대상 | sha256 |
|---|---|
| docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md | c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b |
| docs/tasks/BT4-FUTILITY-01/ERRATA-001.md | 9fcac5a97605a85be68612ba4a465c5f24b8c5b5594f3a801ca5e551993d24bf |
| docs/tasks/BT4-FUTILITY-01/ERRATA-002.md | 0ca8ab961af350b10a2660ca8ee7b8c4bfab2757ee2b6b1ae61ffcfeee7308fe |
| docs/tasks/BT4-FUTILITY-01/ERRATA-003.md | 9b8fcf9f30d8b525237a63b00f599add0a2fbcb33cb0f9ce900642a5a349823d |
| docs/tasks/BT4-FUTILITY-01/ERRATA-004.md | 4b8de161474139cd24976897804a717ad94c9beaa89a2f74da492e0e845b2061 |
| docs/tasks/BT4-FUTILITY-01/ERRATA-005.md | 34408e04bf832446d376cc5dd679a4fc4f4afc20b8d1be472c640d75be1d194e |
| docs/tasks/BT4-FUTILITY-01/ERRATA-006.md | 63c08d10131a71911e849f60b4ff09c542853821c1a3458a68369ffa1bc6fd11 |
| docs/tasks/BT4-FUTILITY-01/ERRATA-007.md | 25841248dae87d0f5568c72e9b35b00ea1a79530f1e546c7d5c312cb67d56cda |
| docs/research_bt4_futility_diag_preregistration.md | 6da9e20088b1a6ca5c9ce9696c0baadd0850d7aa409f962f2583b188b322189f |
| configs/bt4_futility_diag.toml | 3df664508e117ae25b05d7de49b3f62dec1c6ef55eab185ce0cf52f631351723 |
| src/moneylab/research/v06/futility_diag.py (blob 7e2391725f2c85700a37cb228ae336df6ccd0fba) | 2415305b4002661d982ecb9a00843ce9ff882676f91dcf0c78ee03d4d0446e50 |
| src/moneylab/research/v06/synthetic.py (blob 8932b630c321d10fd5ff4f7b0a38cc24bbdad50b) | fc8c944ed3f542079ee5df2b8bf3aa208f8f492dbe726829f9d92c144a03d337 |
| src/moneylab/research/v06/montecarlo.py (blob 0c68be45ed1f42358e9e1b0a3f1086657bc4c968) | b01897591e5c70b0558c558cc7a320d0d73be0ccd2ce2db066aa3763231c5534 |
| src/moneylab/research/v06/procedures.py (blob bf6dfddea822f3af0d6e50274c8b3b5b0c767daf) | bdb261d0328d5bab71ac4b1b2fb082a8a08fd557f3363a21f854eba825f8a351 |
| src/moneylab/research/v06/risk_model.py (blob 7abbda7dd531ad1c669ae7de63c7041f7888aa71) | 296e14789f82301b26fb2659ba33f2bfd2ab368e3d6de61b504cfe6958f28e7a |
| src/moneylab/research/v06/__init__.py (blob 71745fa0622c2b96f9f7036ee551913e073071db) | 40140983b003261e150e529f0a251046629414b68cfe66bd2704be99cd12fbe7 |
| src/moneylab/research/stats.py (blob 01b6472cadb2ce2437a613b09d419a999398c685) | b3d9d05d9d29270cee60ce648aa4a5eb56a4213f7bb855496cc2b3d0fb9ef4e4 |
| g7-E1-theta0.7-d2fcaf64b5fb/manifest.json | ceecf2fa0e7c7666866e2174a2478ab115ddeefde69ca42be5a38bc07b869ea3 |
| g7-E1-theta0.7-d2fcaf64b5fb/SHA256SUMS | bd4bbe60c9cc5de8f3ff36d523a6f47bc38551932a063deb5a4c0d8dcc6474f4 |
| g7-E1-theta0.7-d2fcaf64b5fb/run_spec.json | db26b584d61d0a72c70f7419a1fb8756ce22a60261b47350796bfe185f257f98 |
| g7-E1-theta0.7-d2fcaf64b5fb/run_inputs.json | fa0d4e5d4ede01a18d1d9f8b96e3422df09b15882a6ef1c4eccd94990a48045a |
| g7-P0-theta0.7-d2fcaf64b5fb/manifest.json | d52c355896489739621a4dbec50b84ed86c165dd5a29722f74a9f60b90e8732e |
| g7-P0-theta0.7-d2fcaf64b5fb/SHA256SUMS | 59b34d901d6a25f39c1e156a38351f995521010f6e7130752e2ae9ec85a2d857 |
| g7-P0-theta0.7-d2fcaf64b5fb/run_spec.json | 120c42ff50b2b36648323c6aca27ab0730209051293d760722c0cda9479eb5a5 |
| g7-P0-theta0.7-d2fcaf64b5fb/run_inputs.json | 60e54164393b8b4f7245af1399243429036e33c5aa31463648b0b6185f7425ae |
| g7-v4-d2fcaf64b5fb/v4.json | 517f5ddbbcbee2439e6698e636a11459269d7c2651872251a2c7a078a48137a4 |
| g7-v4-d2fcaf64b5fb/SHA256SUMS | 86c1619a3c0d127d0e5635ff2cd32bba743e0601ac57bfca6e596cb4ea4c155d |
| g5-pilot-d2fcaf64b5fb/manifest.json | fb8a66f54cb0cbe7ab396a8017d70705c6e90c4078dc5c7866c8894de703b7df |
| g5-pilot-d2fcaf64b5fb/SHA256SUMS | f903d3c724ba6546999f7195de52a5a6acf794563af7038aca19073585ef1575 |
| g5-pilot-d2fcaf64b5fb/g6/g6_summary.json | 9bcec3f11fd81f8d59241caa1c1e161baa9065a79cdb3ec727abe49ed0a93cd9 |
| g5-pilot-d2fcaf64b5fb/g6/SHA256SUMS | 92b4f1de63d8729955e5dbde27632d0529ef302457dd427e7d64671b25201682 |
| g5-cal-d2fcaf64b5fb/calibration.json | a1bbada5821f7ae33707a8818927d3929d05a1ac4019946c15a7eac06e73531c |
| user-decisions/000001-PD5_PROCEED.json | b8c8e6a6ae1ecbb8c8fe242d7e211729fee89469de3a6ecbafbeff609ae7df5d |
| g7-core-lock/000001.lock | a896ecdec6eb9f04cbdda410ee6a71f104bdec94ab91e7c2c861fefda256003b |
| g7-core-lock/000001.released | 2b8ae66ba6bb5c6494d30955eaef8c58c94956ca33cadddb8f5b486ec24ae6b9 |

(G7·G5·UDR·lock 행은 SOURCE_OUTPUT_ROOT 기준. 코드 행의 sha256은 LF 바이트 기준이며 비교 규칙은 D1을 따른다)

## PROVENANCE_ACCESS_POLICY

PROVENANCE_ACCESS_POLICY:
- 메타데이터: run_spec.json, run_inputs.json, manifest의 provenance·identity 필드, SHA256SUMS, lock·UDR 파일, 파일 해시와 개수. run_inputs는 run 시작 전에 쓰였으며 CORE 결과를 담지 않는다.
- 결과값: unit jsonl record의 통계 필드, v4.json의 sr_eval·batch_sharpes, G6 출력의 모든 수치.
- 규칙: G5·G6에서는 커밋된 코드만 파일을 읽는다. 결과 파일은 해시 확인, unit 재검증(`verify_run`), 재생성 비교, 분석 계산에만 쓰인다. G5·G6의 출력·보고는 D11 허용 스키마뿐이다. 이 Work Order에서 "결과 열람"은 결과값을 사람이나 Claude에게 표시·보고하는 것이며 G7에서만 허용된다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:

- D0 원칙
  - 아래 정의는 C1 커밋으로 고정되며, G7 이전에 어떤 결과도 열지 않는다. 결과를 본 뒤 정의를 바꾸면 새 study다.
  - SOURCE_CODE_SHA = d2fcaf64b5fb87f502afba29572be340f653be24(데이터 생성 코드). ANALYSIS_CODE_SHA = G3b의 C2 커밋. 두 값을 모든 출력의 provenance에 따로 기록한다.
  - futility_02.py는 futility_diag.py를 import해 그 함수를 바꾸지 않고 쓴다. 기존 `g8a`·`g8a_payload`·`research_identity`는 쓰지 않는다(HEAD = CODE_SHA를 요구하므로).
  - 출력은 `futility_diag.canonical_bytes`로 직렬화한다(D12).

- D1 실행 identity(G5·G6 공통, 엔트리포인트가 다른 작업보다 먼저 확인. 하나라도 실패하면 STOP)
  - Python 실행 환경과 identity 인자
    - `--expected-python`, `--expected-head`가 모두 주어져야 한다. 누락은 IDENTITY_FAILED
    - sys.platform == "win32", platform.python_version() == "3.14.8"
    - os.path.normcase(os.path.realpath(sys.executable)) == os.path.normcase(os.path.realpath(--expected-python))
    - `git rev-parse HEAD`(TARGET_WORKTREE) == --expected-head
    - `moneylab`, `moneylab.research.v06.futility_diag`, `moneylab.research.v06.futility_02`의 `__file__` 실제 경로(realpath·normcase)가 TARGET_WORKTREE/src 아래
    - sys.executable과 sys.version을 provenance에 기록한다
    - 위 어느 것이든 불일치면 IDENTITY_FAILED
  - TARGET_WORKTREE의 `git status --porcelain`이 0줄(clean), branch feature/bt4-futility-02, HEAD = ANALYSIS_CODE_SHA = G4c에서 D13이 확인한 PR head SHA
  - INPUT_HASH_MANIFEST의 코드 7행은 두 가지를 모두 만족해야 한다
    - HEAD Git blob: `git cat-file blob HEAD:<경로>`의 원본 바이트 sha256 = 표의 값
    - 작업 파일: 바이트를 읽어 메모리에서 CRLF(b"\r\n")만 LF(b"\n")로 바꾼 바이트의 sha256 = 표의 값(`futility_diag._lf`와 같은 규칙). 단독 CR, 공백, 인코딩, 그 밖의 내용은 바꾸지 않으므로 그런 차이는 불일치가 된다
    - 정규화는 비교용이며 작업 파일을 수정·재checkout하지 않는다
  - d2fcaf6이 HEAD의 조상이고, d2fcaf6..HEAD 변경 경로가 ALLOWED_FILES의 부분집합
  - NEW_OUTPUT_ROOT가 ignored

- D2 입력 검증(G5, 결과값 없음)
  - SOURCE_WORKTREE: HEAD = d2fcaf6, branch feature/bt4-futility-diag, `git status --porcelain` 0줄(읽기 전용 git)
  - INPUT_HASH_MANIFEST의 G7·G5·UDR·lock 행 바이트 sha256 일치
  - `futility_diag.verify_run`: E1·P0 status COMPLETE, unit_status COMPLETE, time_accounting COMPLETE. pilot status COMPLETE, g6 VERIFIED
  - `futility_diag.verify_v4_run`: VERIFIED
  - `futility_diag.load_calibration(<cal>/calibration.json, a1bbada5821f7ae33707a8818927d3929d05a1ac4019946c15a7eac06e73531c)` 성공, E1·P0 run_inputs의 calibration_provenance.calibration_sha256이 같은 값(코드 비교, 출력은 MATCH만)
  - user-decisions에 000001-PD5_PROCEED.json 하나만, g7-core-lock에 000001.released 있음, SOURCE_OUTPUT_ROOT에 g8a-* 없음
  - 출력: input_verification.json(검사 이름, 기대·실측 sha256, status, 개수만), SHA256SUMS

- D3 R4 1차 라벨(BT4-FUTILITY-01 규칙 그대로)
  - by_cell = `read_records`(E1 run) ∪ `read_records`(P0 run), v4 = `verify_v4_run(...)["v4"]`, sigma = load_calibration 결과의 sigma 절
  - primary = `futility_diag.decision_summary(by_cell, v4, sigma)`를 변경 없이 호출한 결과 전체
  - Holm family는 정확히 5개(V-1 p₁=D1_lo, V-2, V-3, V-8, V-4), FWER 0.025. EXPLORATORY 항목은 family·라벨·EFF에 들어가지 않는다
  - 이 값은 BT4-FUTILITY-01 G8a 결과가 아니라 BT4-FUTILITY-02의 계산이다

- D4 R1 RD 분포
  - 대상: E1-theta0.7 f12 record(rep 0..R−1, 누락·순서 불일치는 STOP)
  - 필드: variants.S1.d(int), sd(bool). d가 int가 아니거나 d < 0 또는 d > 1,999면 STOP
  - SD 복제는 분포에서 빼고 sd_count로 따로 보고한다(SD에서 d = 0은 구성상 값)
  - 출력: {cell, window, reps_R, bootstrap_B, sd_count, n_nonsd, counts: [[d, n_d], …](d 오름차순, n_d > 0만), summary: {share_d0, mean, max, q50, q90, q99}}
  - 분위수: 비SD d를 오름차순 정렬한 x₍₁₎..x₍N₎에서 q_p = x₍⌈p·N⌉₎. N = 0이면 summary = null, status "EMPTY"

- D5 R2 α 대비
  - I_v(α) = 1{p_v ≤ α}, α ∈ (0.025, 0.10). p_v는 V0·V0d·V0b60의 p, S1_lo는 p_lo, S1_hi는 p_hi
  - rates[α][cell][window][indicator] = {rate, mc_se = √(r(1−r)/R), reps}: 두 셀 × 4창 × 5지시변수
  - contrasts[α][name]: `futility_diag.CONTRASTS` 5개(V-1_lo, V-1_hi, V-2, V-3, V-8)에 `futility_diag.mcnemar` 적용. 출력 {d_hat, se, n10, n01, reason, p_one_sided_unadjusted}
  - EFF, U_D, Holm, Bonferroni, V-8 추가 조건, 라벨은 계산하지 않는다
  - 정렬: α 오름차순, CONTRASTS 정의 순서

- D6 R3 PD-4
  - 대상: E1-theta0.7 f12 중 sd = false인 record
  - 출력: {R_total, R_sd, R_subset, rates: {V0, V0d}, contrast: {d_hat, se, n10, n01, reason, p_one_sided_unadjusted, u_d}}, 라벨 없음
  - R_subset = 0이면 contrast = null, status "NOT_COMPUTABLE_EMPTY_SUBSET"

- D7 C5 V-4 K=20
  - D7-a(G6의 첫 단계, 다른 어떤 record 읽기·계산보다 먼저): `futility_diag.v4_evaluation(4000, ("FUTDIAG","v4eval"), E_CAL)`과 같은 단계로 경로·수익률을 재생성한다. 같은 seed의 재현이며 새 표본이 아니다. years, seed_parts, seed, edge_annual, sr_eval, batch_sharpes, batch_lengths 7개 필드를 v4.json과 `canonical_bytes`로 비교한다. 판정은 바이트 완전 일치(허용 오차 없음, -0.0과 0.0도 다름). 실측 n = 1,459,876, n mod 40 = 36, K=40 batch_lengths가 코드 유도값(앞 36개 36,497일, 뒤 4개 36,496일)과 같아야 한다
  - D7-a MISMATCH 또는 n·길이 불일치: G6 전체 STOP. R1~R4·C5~C7 어느 것도 계산하거나 쓰지 않는다. 출력은 D11 실패 JSON뿐이다. 결과 열람·자동 재실행·SOURCE_OUTPUT_ROOT 변경 없음
  - D7-b(MATCH 뒤): 같은 수익률을 `futility_diag.batch_sharpes(rets, 20)`으로 연속 20 배치(n mod 20 = 16: 앞 16개 72,994일, 뒤 4개 72,993일). K=20 배치는 K=40 배치 두 개의 결합이 아니다(경계 17·18·19가 1·2·1일 다름)
  - 추론: `futility_diag.v4_inference(sr_eval, 0.7, batch20)` → t(19). 출력 {k: 20, df: 19, batch_lengths, se, t_quantile, delta_lower, delta_upper, p_one_sided, se_ratio_vs_k40}
  - K=40 label은 바꾸지 않는다. K=20 라벨·대체 판정·"판정이 바뀌었을지" flag를 출력하지 않는다

- D8 C6 lag-1
  - ρ̂₁ = Σⱼ₌₁^{K−1}(xⱼ − x̄)(xⱼ₊₁ − x̄) / Σⱼ₌₁^{K}(xⱼ − x̄)², x̄ = K개 전체 평균
  - K=40: v4.json batch_sharpes. K=20: D7-b 배치
  - 분모 0: rho1 = null, status "UNDEFINED_CONSTANT". 비유한 입력 또는 K < 3: STOP
  - 출력 {k, n_pairs, estimator: "acf_full_mean_full_ss", rho1, status, batch_source}, k 내림차순(40, 20)
  - 검정·임계값·독립성 주장 없음

- D9 C7 conf 설명 비율
  - 분모 0.066 = r_obs,conf − 0.05, r_obs,conf = 0.116(BT4-FUTILITY-01 WO:314, MC-V06, SYNTHETIC)
  - 기본 분자 ΔRej(Δ, σ) = Φ(−z₀.₉₅ − Δ/σ) − 0.05(`futility_diag.delta_rej`). 보조 분자 ΔRej′(Δ, σ) = r_obs − Φ(Φ⁻¹(r_obs) + Δ/σ)
  - Δ̂, L_Δ, U_Δ는 R4의 K=40 V-4 추론값, σ_L·σ_U는 calibration 값
  - 점추정 범위: (Δ̂, σ_L), (Δ̂, σ_U) 두 점의 분자·비율과 min·max
  - 기술적 경계: [L_Δ, U_Δ] × [σ_L, σ_U] 네 꼭짓점 분자의 min·max(ΔRej는 `futility_diag.rect_extrema`), 비율 = 분자 / 0.066
  - flag: RATIO_NEGATIVE(비율 < 0), RATIO_ABOVE_ONE(비율 > 1), APPROX_OUT_OF_RANGE(|Δ̂|/σ_L > 0.5). 값은 자르지 않는다
  - σ ≤ 0 또는 비유한값은 STOP
  - 해석: 모형이 함축하는 기각률 변화를 다른 study(MC-V06)의 관측 초과분에 견준 비다. 인과적 기여율이나 측정된 설명 비율로 쓰지 않는다

- D10 출력·실행
  - 시도 디렉터리: NEW_OUTPUT_ROOT/g5-input-<ANALYSIS_SHA 앞 12자리>-a<N>/, NEW_OUTPUT_ROOT/g6-analysis-<ANALYSIS_SHA 앞 12자리>-a<N>/(N은 1부터, 시도마다 새 디렉터리)
  - 실행 절차(G5·G6 각각 1회)
    0. Python 실행 환경 확인(데이터를 읽지 않는 1회 명령): 사용할 실행 파일 `<PYTHON>`으로 sys.executable의 절대경로, platform.python_version(), sys.platform, `moneylab`·`moneylab.research.v06.futility_diag`·`moneylab.research.v06.futility_02`의 `__file__`을 출력한다. 3.14.8·win32가 아니거나, import가 실패하거나, 모듈 파일이 TARGET_WORKTREE/src 아래가 아니면 STOP. 확인된 절대경로를 gate 보고에 쓰고 단계 3에 같은 실행 파일을 쓴다. Gate Authorization에 실행 파일 경로가 적혀 있으면 그것과도 같아야 한다
    1. NEW_OUTPUT_ROOT 확인
       - `git check-ignore`로 NEW_OUTPUT_ROOT가 ignored인지 확인한다. 아니면 STOP
       - G5 첫 시도(a1): NEW_OUTPUT_ROOT가 없어야 한다. 있으면 자동 재사용하지 않고 STOP. 없으면 `mkdir -p NEW_OUTPUT_ROOT` 1회(부모 포함)
       - 그 밖의 시도(G5 재시도, G6): NEW_OUTPUT_ROOT가 있어야 하고, 그 안의 항목이 이전 gate 보고에 기록된 시도 디렉터리 목록과 정확히 같아야 한다. 다르면(예상 밖 파일·디렉터리 포함) STOP
    2. `mkdir <시도 디렉터리>`(재귀·-p 없음) 1회. 이미 있으면 실패하므로 STOP(재사용 금지)
    3. `<PYTHON> -m moneylab.research.v06.futility_02 <verify-inputs|analyze> --out <시도 디렉터리> --expected-python <단계 0 절대경로> --expected-head <C2 SHA> … 2> <시도 디렉터리>/stderr.bin` 1회. stdout은 리디렉션하지 않는다
    4. 종료 후 종료 코드, stdout(D11 JSON), stderr.bin 크기·sha256만 확인
  - 실행 파일 경로는 이 Work Order에 고정하지 않는다. 설치·업그레이드·venv 생성·환경 변경은 승인하지 않는다
  - 엔트리포인트는 시작 시 시도 디렉터리의 내용이 크기 0인 stderr.bin 하나뿐인지 확인한다. 다르면 OUTPUT_DIR_NOT_FRESH로 STOP
  - G5 파일: input_verification.json, SHA256SUMS, stderr.bin. G6 파일: analysis.json(schema moneylab.bt4_futility_02.analysis/1: provenance, input_verification_sha256, regeneration, primary, rd, alpha, pd4, v4_k20, lag1, conf_ratio, evidence, classification), SHA256SUMS, stderr.bin
  - G6 계산 순서: D1 → D7-a → D3 → D4 → D5 → D6 → D7-b → D8 → D9 → 쓰기(D12)
  - exit code: 0 COMPLETE, 2 STOP. 그 밖의 종료 코드는 UNCONTROLLED_TERMINATION(D11)
  - G6 wall-clock 권고 한도 4시간. 넘으면 Claude는 상태(경과 시간, 프로세스 생존, 시도 디렉터리 파일 이름·크기)만 보고하고 STOP한다. 강제 종료·재실행은 사용자 결정으로만 한다

- D11 OUTPUT_CONTROL (G5·G6 엔트리포인트)
  - 엔트리포인트 전체를 하나의 최상위 `try/except BaseException`이 감싼다.
  - 성공 시 stdout은 JSON 한 줄: {status: "COMPLETE", stage, elapsed_s, warnings_count, python_executable, output_dir, output_sha256s, regeneration(G6: "MATCH")}
  - 실패 시 stdout은 JSON 한 줄: {status: "STOP", stage, failure_code, elapsed_s, warnings_count, python_executable, output_dir, files: [[이름, 크기, sha256], …]}
  - failure_code는 코드에 고정된 목록에서만 고른다: IDENTITY_FAILED, SOURCE_WORKTREE_CHANGED, INPUT_HASH_MISMATCH, VERIFY_RUN_FAILED, VERIFY_V4_FAILED, CALIBRATION_MISMATCH, UDR_OR_LOCK_INVALID, G8A_DIR_PRESENT, OUTPUT_NOT_IGNORED, OUTPUT_DIR_NOT_FRESH, REGEN_MISMATCH, LENGTH_MISMATCH, RECORD_INVALID, NONFINITE, SIGMA_NONPOSITIVE, SE_ZERO, WRITE_FAILED, INTERNAL_ERROR
  - failure_code 배정: failure_code는 실행 단계와 명시적인 예외 유형으로 결정하며, 예외 메시지를 파싱하지 않는다. 단계에 대응하지 않는 예외는 INTERNAL_ERROR로 처리한다. 각 단계는 시작 전에 자기 failure_code를 현재 단계로 등록하고, 그 단계 안에서 난 예외(기존 `futility_diag.StopImplementation`, ValueError 등)는 그 단계의 코드가 된다. D1의 Python 실행 환경 확인 실패는 IDENTITY_FAILED다
  - 인자 해석은 최상위 예외 처리 안에서 하며, 오류를 stderr에 쓰거나 스스로 종료하지 않는다(예: argparse `exit_on_error=False`, usage·help 출력 없음). 인자 누락·형식 오류는 IDENTITY_FAILED
  - 예외 메시지, traceback, repr, 변수값은 어떤 채널(stdout, stderr, 파일)에도 쓰지 않는다(기존 `futility_diag`의 StopImplementation 메시지에는 값이 들어갈 수 있으므로 메시지를 버리고 failure_code로만 바꾼다)
  - stderr는 D10의 stderr.bin으로 리디렉션되며 크기가 0이어야 한다. 엔트리포인트는 stderr에 아무것도 쓰지 않는다. Python warning은 `warnings.catch_warnings(record=True)`로 잡아 개수만 보고한다
  - debug logging, 분석 경로의 print, 임시 분석 파일 금지
  - 통제 한계: 프로세스 강제 종료, 인터프리터 치명 오류, 메모리 고갈처럼 Python이 처리할 수 없는 실패는 최상위 예외 처리로 포착하지 못할 수 있다. 이런 출력은 stderr.bin에 격리된다. 종료 코드가 0·2가 아니거나 stdout이 D11 스키마의 JSON 한 줄이 아니면 Claude는 stdout 내용을 인용하지 않고 "UNCONTROLLED_TERMINATION", 종료 코드, 경과 시간, stderr.bin 크기·sha256만 보고하고 STOP한다

- D12 PARTIAL_OUTPUT
  - 모든 결과는 메모리에서 계산한 뒤, 파일마다 배타적 `*.tmp` 생성 → 원자적 rename으로 쓴다. 순서는 데이터 파일 먼저, SHA256SUMS 마지막
  - SHA256SUMS는 엔트리포인트가 쓴 데이터 파일(input_verification.json 또는 analysis.json)만 담는다. stderr.bin은 담지 않는다(근거: stderr.bin은 셸이 열고 프로세스 종료까지 쓰일 수 있어 SHA256SUMS를 쓰는 시점에 최종 바이트가 아니며, 비정상 종료 시에는 SHA256SUMS 자체가 없다). stderr.bin의 크기·sha256은 프로세스 종료 뒤 Claude가 측정해 gate 보고에 남긴다(CLAUDE_REPORTED)
  - 시도 디렉터리에 허용된 파일: 데이터 파일, SHA256SUMS, stderr.bin, 그리고 실패 시 남은 `*.tmp`. 그 밖의 파일은 STOP
  - NEW_OUTPUT_ROOT 안에는 시도 디렉터리만 허용한다. 그 밖의 항목이 생기면 STOP
  - 각 gate 보고는 실행 뒤 NEW_OUTPUT_ROOT의 항목 목록을 기록한다(다음 시도의 기준)
  - 후속 시도 진입 전 NEW_OUTPUT_ROOT의 기존 시도 디렉터리 목록과 각 파일의 크기·SHA-256이 직전 Gate 보고의 값과 일치해야 한다. 불일치하면 STOP한다. 파일 내용은 열람하거나 출력하지 않는다.
  - SHA256SUMS가 없는 디렉터리는 미완료다. 미완료 또는 STOP 디렉터리는 열람·수정·삭제·덮어쓰기·재사용하지 않는다. 보고는 파일 이름·크기·sha256만
  - stderr.bin은 허용된 실행 증거 파일이다. G7 이전에는 내용을 열람하지 않는다. G6 PASS에는 크기 0이 필요하므로 G7에서 열 내용도 없다. 크기가 0이 아닌 stderr.bin의 열람은 별도 사용자 결정으로만 한다
  - 재실행은 별도 승인과 새 디렉터리(a<N+1>)로만 한다
  - G8 보존 확인은 실패 시도 디렉터리를 포함한 NEW_OUTPUT_ROOT 전체 목록을 대상으로 한다

- D13 CI_TESTED_TREE (G4c PASS 증거, 모두 읽기 전용, 각 1회)
  - 기대 필드 이름은 GitHub REST 문서 기준이며 이 저장소에서 아직 확인하지 않았다. G4c는 실제 응답에서 필드를 읽는다. 필드가 없거나 구조가 다르면 추측하지 않고 STOP한다
  - E1 `gh api repos/swk3169/MoneyLab/pulls/<N>`: head.sha = C2, base.sha = d2fcaf64b5fb87f502afba29572be340f653be24, base.ref = feature/bt4-futility-diag, draft = true, merge_commit_sha 기록
  - E2 `gh api repos/swk3169/MoneyLab/git/commits/<merge_commit_sha>`: tree.sha = C2의 tree
  - E3 CI run: `gh api` 또는 `gh run view`로 event = pull_request, head_sha = C2, 해당 PR 번호와 연결
  - E4 그 run의 `pytest` job: conclusion = success, head_sha = C2
  - E5 그 job의 checkout 단계 로그에서 실제 checkout된 commit SHA = merge_commit_sha
  - E1~E5 중 하나라도 확인할 수 없거나 불일치하면 STOP. CI 재실행·PR 변경으로 해결하지 않는다

## TEST_GATES

TEST_GATES (G2·G3c, 실제 G7 데이터를 쓰지 않음):
- T1 전체 pytest 통과(`-p no:cacheprovider -rfEs -q`), failed 0 / errors 0
- T2 tmp_path에 FUTDIAG-TEST 이름공간의 작은 합성 run을 만들어 D2~D9 계산 경로를 끝까지 검증한다. SOURCE_OUTPUT_ROOT를 테스트에서 읽지 않는다
- T3 D3: fixture에서 futility_02의 primary가 decision_summary 직접 호출 결과와 바이트 일치
- T4 D4~D6: 작은 고정 배열로 기대값 일치, 빈 부분집합·SD·범위 밖 d 처리
- T5 D7: 짧은 years에서 v4_evaluation과 재생성 결과 일치, 필드 하나를 바꾸면 REGEN_MISMATCH이고 그 뒤 계산 함수가 호출되지 않음, batch 길이 규칙
- T6 D8: 상수 시계열 UNDEFINED_CONSTANT, 비유한 STOP, 알려진 수열의 ρ̂₁
- T7 D9: 알려진 Δ·σ에서 ΔRej·ΔRej′·flag
- T8 D1·D2: Python 버전 불일치, 플랫폼 불일치, 모듈 파일이 TARGET_WORKTREE/src 밖, 코드 blob 불일치, 입력 해시 불일치, g8a-* 존재, source worktree dirty에서 STOP(가짜 입력). D1 줄끝 규칙(tmp 파일): LF 파일 PASS, 같은 내용의 CRLF 파일 PASS, 내용 한 바이트 변경 STOP, 단독 CR이 있는 파일은 단독 CR을 지우지 않으므로 STOP, 비교 뒤 작업 파일 바이트 불변, TARGET dirty worktree STOP
  - --expected-python 또는 --expected-head 누락, 다른 실행 파일 경로, 다른 HEAD SHA에서 IDENTITY_FAILED. 인자 오류 시에도 stdout은 D11 JSON 한 줄, stderr는 비어 있음
- T9 D11: 성공·실패 모두 stdout이 허용 스키마의 JSON 한 줄이고 stderr가 비어 있음. 엔트리포인트를 subprocess로 실행해 확인한다. failure_code 목록의 각 코드에 대해 해당 단계에 표식 문자열을 담은 예외를 주입하는 failure-injection 테스트를 두고, 표식 문자열이 stdout·stderr에 나오지 않음과 failure_code가 단계로 정해짐(메시지가 달라도 같은 코드)을 확인한다. 단계 밖 예외는 INTERNAL_ERROR
- T10 D12: 쓰기 중 실패 주입 시 SHA256SUMS가 없음, SHA256SUMS에 stderr.bin이 없음, 시도 디렉터리에 stderr.bin 외 파일이 있거나 stderr.bin 크기가 0이 아니면 OUTPUT_DIR_NOT_FRESH
- T11 `git diff --check` 깨끗, 변경 경로 ⊆ ALLOWED_FILES, PROTECTED diff 0

## E2E_GATES

E2E_GATES (G3c): HEAD = C2 clean에서 T1~T11 재실행. 실제 G7 데이터 E2E는 G5·G6이 대신한다.

## GATE_TABLE

| gate | 진입 조건 | 승인 범위 | 산출물 | PASS | STOP | 다음 승인 |
|---|---|---|---|---|---|---|
| C0 CONTRACT_REVIEW | 최종 후보 초안 | 읽기 | 검토 보고 | 체크리스트 PASS | 계약 모순 | CF |
| CF CANDIDATE_FREEZE | C0 PASS | 저장소 밖 후보 파일 1개 생성 | 경로, sha256·bytes·lines | 인코딩 규칙 충족 | 경로 존재, 규칙 위반 | G1(경로와 세 값) |
| G1 WORK_ORDER_ISSUE_AND_WORKSPACE_SETUP | 원격 base = d2fcaf6, 대상 branch·경로 없음, 후보 세 값 일치 | ALLOWED_ACTIONS G1 (1)~(6) | C1 SHA·parent·tree, WO sha256·bytes·lines, blob sha256 | 복사 전후·blob 모두 일치, clean | 어느 값이든 불일치, 경로 존재 | 사용자 sha256 확인 뒤 G2 WO@C1 |
| G2 IMPLEMENTATION | HEAD = C1 clean, sha256 확인됨 | G2 파일 2개, 테스트 | diff, 테스트 결과 | T1~T11 | 범위 밖 변경, 테스트 실패 | G3a |
| G3a PRECOMMIT_AUDIT | G2 PASS | 읽기 | 감사 보고 | 변경 집합 = 계획, diff --check, PROTECTED 0 | 불일치 | G3b |
| G3b COMMIT | G3a PASS | 2파일 stage, C2 1회 | C2 SHA·tree | clean, 파일 집합 일치 | 추가 경로 | G3c |
| G3c CLEAN_COMMIT_E2E | HEAD = C2 clean | pytest, tmp 출력 | 테스트 결과 | T1~T11 | 실패 | G4a |
| G4a PUSH | G3c PASS, 원격 main = EXPECTED_REMOTE_MAIN, 원격 base = d2fcaf6 | push 1회 | 원격 head | 원격 head = C2 | main·base 변동 | G4b(PR_CREATE: YES, 제목·본문) |
| G4b PR_CI_DRAFT_PR | G4a PASS, 같은 head/base 열린 PR 없음 | draft PR 생성 1회 | PR 번호 | draft, base·head 일치, PR_SCOPE 3경로 | 중복 PR, 범위 불일치 | G4c |
| G4c PR_CI_REVIEW | PR 존재 | D13 조회 | E1~E5 증거 | E1~E5 전부 확인, ci-tests / pytest SUCCESS | check 없음·진행 중·실패, E1~E5 불일치·확인 불가 | G5 |
| G5 F2_INPUT_INTEGRITY | G4c PASS, HEAD = C2 | D10 절차(단계 0 환경 확인, mkdir 1회, verify-inputs 1회, stderr → stderr.bin) | Python 절대경로, D11 JSON, input_verification sha256, stderr.bin 크기·sha256 | 단계 0 PASS, exit 0, D1·D2 전부 PASS, 허용 스키마, stderr.bin 크기 0 | 환경 확인 실패, failure_code, 디렉터리 존재, stderr.bin ≠ 0, UNCONTROLLED_TERMINATION | G6 |
| G6 F2_DIAGNOSTIC_ANALYSIS | G5 PASS, 같은 HEAD | D10 절차(단계 0 환경 확인, mkdir 1회, analyze 1회, stderr → stderr.bin) | Python 절대경로, D11 JSON, analysis.json sha256, stderr.bin 크기·sha256 | 단계 0 PASS, exit 0, MATCH, 허용 스키마, stderr.bin 크기 0 | 환경 확인 실패, REGEN_MISMATCH 등 failure_code, 디렉터리 존재, stderr.bin ≠ 0, UNCONTROLLED_TERMINATION, 4시간 초과 | G7 |
| G7 F2_RESULT_AUDIT | G6 PASS | analysis.json 열람 1회, 채팅 보고 | 채팅 감사 보고 | REQUIRED_REPORT 충족 | 출력 모순·스키마 위반 | G8 |
| G8 CLOSEOUT | G7 보고 | 읽기 | 종료 기록 | 보존 확인 전부 PASS | 보호 영역 변경 흔적 | 없음 |

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·C2 SHA·tree, WO sha256·blob sha256, 커밋 파일 집합, PR_SCOPE diff
- CLAUDE_REPORTED: pytest, Python 실행 환경 확인, G5·G6 실행 결과, 출력 sha256, stderr.bin 크기·sha256
- INDEPENDENT: GitHub PR·CI 응답(D13), 사용자 확인
- Claude가 실행한 결과를 INDEPENDENT로 쓰지 않는다

## REQUIRED_REPORT

REQUIRED_REPORT:
- 모든 gate: TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, HEAD·parent·tree, worktree 상태, 변경 경로, PROTECTED diff, GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, <GATE>_PASS, READY_FOR_<NEXT_GATE>
- CF: 후보 경로, sha256, bytes, lines, 인코딩 검사 결과
- G1: 복사 전·후 세 값, C1 SHA·parent·tree, blob sha256, "사용자 sha256 확인 필요"
- G4b·G4c: PR 번호, base, head SHA, draft 여부, D13 E1~E5 각 값과 판정
- G5: Python 실행 파일 절대경로·버전·플랫폼·모듈 파일 경로, 시도 디렉터리, 종료 코드, D11 JSON 전문, input_verification.json sha256, stderr.bin 크기·sha256(수치 없음)
- G6: Python 실행 파일 절대경로·버전·플랫폼·모듈 파일 경로, 시도 디렉터리, 종료 코드, D11 JSON 전문, analysis.json sha256, regeneration 상태, 실행 시간, stderr.bin 크기·sha256(수치 없음)
- G7(채팅만):
  - R4 라벨 5개와 효과·SE·Holm p·WEAKENED 상한(BT4-FUTILITY-01 WO:439-441 형식)
  - V-1 lo/hi와 DEGENERACY_AMBIGUOUS
  - V-4 L_Δ·σ_L·σ_U·ΔRej_max·근사 조건
  - R1~R3·C5~C7 표
  - 해석 제한, "VALIDATED 판정 없음", "SYNTHETIC / NOT_EVIDENCE", "POST_HOC_DIAGNOSTIC, 독립 확인 아님"
  - G6_KNOWN_INFORMATION
  - ANALYSIS_CODE_SHA, input·analysis sha256
- G8:
  - RESEARCH_AUDIT_COMPLETE: YES/NO
  - PR_STATE: OPEN_DRAFT_DO_NOT_MERGE
  - TASK_COMPLETE: NOT_DECLARED
  - NEXT_DECISION: SEPARATE_CONTRACT_REQUIRED
  - 보존 확인:
    - SOURCE worktree HEAD·clean
    - PR #37 head·updatedAt
    - feature/bt4-futility-diag 원격 head
    - SOURCE_OUTPUT_ROOT 목록·수정 시각
    - NEW_OUTPUT_ROOT 전체 디렉터리(실패 시도 포함) 목록과 파일 sha256
    - CF 후보 파일 sha256
  - 남은 의무:
    - BT4-FUTILITY-01 미완료 의무
    - 결과 공개·merge 결정

## G6_KNOWN_INFORMATION

G6_KNOWN_INFORMATION (분석 정의 고정 전 이미 알려진 정보):
- 알려짐: BT4-FUTILITY-01 G6 nuisance 값(R_c, σ̂, κ̂, σ_L, σ_U), PD-5 STOP과 UDR의 ND flag 비율, P0_CONF_CHECK PASS, pilot 시간·예산, MC-V06 결과(r_obs 등), BT4-FUTILITY-01 보고 누락 6항목 목록, n 등 코드 유도 메타데이터
- 알려지지 않음(G7 전까지): CORE 기각률·대비·p·Δ̂·SR_eval·라벨·batch Sharpe, pilot 효과

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree·branch가 기대와 다름, 원격 feature/bt4-futility-diag ≠ d2fcaf6
- CF 후보 파일의 sha256·bytes·lines가 승인 값과 다름(G1 복사 전·후), 커밋된 blob의 sha256이 WO_SHA256과 다름
- CF 경로 또는 TARGET_BRANCH·TARGET_WORKTREE가 미리 있음
- ALLOWED_FILES 밖 tracked 변경, PROTECTED 변경, 예상 밖 untracked 파일, PR_SCOPE ≠ 3경로
- SOURCE worktree·branch·PR #37·SOURCE_OUTPUT_ROOT의 변경 흔적
- guard ASK 거절·DENY, 권한 거절
- 테스트 실패·에러
- 원격 main ≠ EXPECTED_REMOTE_MAIN(G4a·G4b)
- 같은 head/base의 열린 PR 존재, PR이 draft가 아님, base·head 불일치
- G4c: ci-tests / pytest check 없음·진행 중·실패, D13 E1~E5 중 확인 불가·불일치(CI 테스트 트리 검증 실패)
- G4c 이후 새 커밋 생김(G5 전)
- Python 실행 환경 확인 실패(D10 단계 0 또는 D1: 버전, 플랫폼, 실행 파일 경로 불일치, import 실패, 모듈 파일이 TARGET_WORKTREE/src 밖)
- D1·D2 실패(코드 blob 또는 CRLF 정규화 작업 파일 sha256 불일치, dirty worktree 포함)
- G6 재생성 MISMATCH(D7-a), n·batch 길이 불일치, 비유한값, σ ≤ 0, batch-means SE = 0
- stdout이 D11 허용 스키마를 벗어남, 종료 코드가 0·2가 아님(UNCONTROLLED_TERMINATION)
- stderr.bin 크기가 0이 아님
- 시도 디렉터리 mkdir 실패(이미 있음), OUTPUT_DIR_NOT_FRESH, 시도 디렉터리에 허용 밖 파일
- NEW_OUTPUT_ROOT가 G5 첫 시도 전에 이미 있음, 또는 그 뒤 시도에서 내용이 기록된 시도 디렉터리 목록과 다름
- 부분·실패 출력 디렉터리의 열람·재사용 시도, G7 이전 stderr.bin 내용 열람 필요
- G5·G6 출력·PR·커밋·CI 출력에 결과값 노출
- G7 이전 결과 열람 필요
- G6 4시간 초과
- 결과를 본 뒤 정의·범위·순서 변경 필요(새 study)
- COMPLETE 선언 시도, merge·ready·edit·close 시도
- 계약 모순, 상위 규칙 충돌

## CLOSEOUT_CRITERIA

CLOSEOUT_CRITERIA:
- RESEARCH_AUDIT_COMPLETE = YES: G7에서 R1~R4·C5~C7이 모두 보고됨(SCOPE상 부분 결과는 없다). G6이 STOP으로 끝났으면 NO
- PR_STATE = OPEN_DRAFT_DO_NOT_MERGE, PR #37 불변, feature/bt4-futility-diag 불변, SOURCE 산출물 보존
- TASK_COMPLETE = NOT_DECLARED. 결과 공개, merge, main 통합, PR 종료는 별도 계약 결정으로만 한다
