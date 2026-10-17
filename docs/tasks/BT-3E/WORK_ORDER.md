# Work Order: BT-3E — Fixture-only forward monthly risk-check mechanism

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/BT-3E/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: BT-3E
TASK_ID: BT-3E
TITLE: Fixture-only forward monthly risk-check mechanism
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 3f0880b943122a2fd51b84566e9bbddd23057322
CANONICAL_BASE_TREE: 45e434ec4c048a04ed7b3c60ff0733a6061baf5e
TARGET_BRANCH: feature/backtest-bt3e-risk-check
TARGET_WORKTREE: C:/MoneyLab-bt3e-risk-check
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (CREATE_MERGE_COMMIT; squash/rebase merge 금지: 계약 커밋이 구현보다 먼저인 이력을 보존)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

DESIGN_INVESTIGATION과 CONTRACT_REVIEW는 이 파일 발행 전에 대화로 완료했다(BASE@3f0880b). 상위 맥락: BT-4 CONTRACT_REVIEW 1단계의 결정 BT4-Q3 = B(DP1을 BT-4 동결 전 별도 선행 task로 구현).

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: BT-3E <GATE> WO@<commit>`)
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping except WORKSPACE_SETUP: NOT_REQUIRED tasks
- Gate Authorization은 파일 수정이 아니다. 이전 gate의 승인이나 이 파일이 다음 gate의 승인을 대신하지 않는다.

## PRIORITY

1. safety / system / tool restrictions
2. repository absolute rules: CLAUDE.md, .claude guard/hook/settings, docs/agent_workflow.md
3. frozen / preregistered contracts
4. 이 Work Order와 ACCEPTED ERRATA
5. implementation judgment

충돌하면 상위 규칙을 따르고 STOP/REPORT 한다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 위 PRIORITY 1-3의 저장소 규칙을 참조한다(복제하지 않는다). 이 Work Order는 그 규칙을 바꾸지 않는다.

## SCOPE_STATEMENT

SCOPE_STATEMENT:
- fixture/synthetic 데이터만 다룬다. 모든 산출물은 SYNTHETIC / NOT_EVIDENCE다.
- 실데이터를 쓰지 않는다. 외부 시장 API를 호출하지 않는다.
- 주문, 페이퍼·실거래, 자동매매를 하지 않는다.
- BT-4 동결을 하지 않는다. 사전등록 초안과 config를 바꾸지 않는다.
- BT-5/BT-6를 실행하지 않는다. Monte Carlo를 실행하지 않는다.

## GOAL

GOAL: 실제로 바인딩된 전략 집합 F의 각 전략을, 보호된 forward 행·가격·수익률·MDD 값·낙폭 크기·보호 시각을 내보내지 않고 월별 forward 위험 조건으로 평가하는 일반 장치를 BT-3D vault에 추가한다(fixture 전용). 장치는 (1) 위험 정책을 holdout 개봉 전에 바인딩하고, (2) 실제 F를 holdout 개봉 후·첫 forward 접근 전에 바인딩하고, (3) 확증 기준값을 vault의 public 데이터로 내부 재계산하고, (4) 보호 행을 읽기 전에 월별 확인을 소비하고, (5) 적격 봉인 월마다 F 전체에 대해 소비 확인을 정확히 1회만 허용하고, (6) 사전등록 절차에 필요한 최소량인 전략별 PASS/VIOLATION만 반환하고, (7) fail-closed로 동작하며, (8) 여기서 명시적으로 확장하지 않은 BT-3D 동작과 계약을 보존한다. BT-3E는 장치만 제공한다. 연구 정책 값은 BT-4가 고정하고, 실제 F와 실제 월별 확인은 BT-6이 수행한다.

## BACKGROUND

BACKGROUND: 사전등록 초안 11.3 12행(forward 중 MDD > 확증 MDD × 비율이면 RISK_LIMIT, 매월 확인), 19.3(월별 위험 확인은 통과/위반만 반환), 16-0(잠금 구현은 동결 전 완료). BT-3D(Work Order `docs/tasks/BT-3D/WORK_ORDER.md`, merge 3f0880b)는 이 확인을 DP1로 미뤘다. 기존 MDD 함수(`backtest/performance.max_drawdown_log`, `research/v06/procedures.max_drawdown`)와 MC의 RISK_LIMIT 모의는 있지만 vault 안전 경로는 없다.

## SOURCE_OF_TRUTH

SOURCE_OF_TRUTH:
- docs/research_v06_preregistration_draft.md: 8.1, 10.7, 11.3(12행과 끝 문단), 16-0, 19.1–19.4 (읽기만, 수정 금지)
- docs/tasks/BT-3D/WORK_ORDER.md (D1–D19, 특히 D1, D7, D9, D11, D12, D14, D16)
- docs/backtest_design.md 4, 10.3
- src/moneylab/backtest/vault.py, portfolio.py, costs.py, performance.py, data.py (canonical 3f0880b)

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: base 확인(필요하면 origin main ref 하나만 fetch), TARGET_BRANCH/TARGET_WORKTREE 생성(base 3f0880b), 이 파일 하나 최초 생성, `git add -- docs/tasks/BT-3E/WORK_ORDER.md`, C1 commit 하나, 감사
- IMPLEMENTATION: ALLOWED_FILES 5개만 생성/수정, TEST_GATES 실행. 테스트 실행을 위해 TARGET_WORKTREE에 ignored `.venv` junction(→ C:/MoneyLab/.venv) 하나를 만드는 것을 허용한다(tracked 아님, stage·커밋 금지)
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, commit 하나
- CLEAN_COMMIT_E2E: E2E_GATES 실행(ignored 출력만)
- PUSH: TARGET_BRANCH 하나만 `git push -u origin feature/backtest-bt3e-risk-check`
- PR_CI: PR 하나 생성(별도 승인 시), CI 확인
- MERGE: 사용자 결정, MERGE_METHOD
- POST_MERGE_AUDIT: main ref만 fetch, 구조 감사
- COMPLETE: 최종 보고(채팅)

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 현재 승인된 gate 밖의 행위
- ALLOWED_FILES 밖의 tracked 변경, PROTECTED_FILES 변경
- 이 Work Order 또는 ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
- hooks / settings / .claude 변경 또는 guard 우회
- 기존 worktree/branch 삭제·수정·정리, 기존 untracked/ignored/E2E/reference/scratchpad 산출물 정리
- C:/MoneyLab(`docs/chatgpt-task-handoff`) 변경, C:/MoneyLab-bt3d-vault 변경
- 사전등록·config·research·CLI 변경
- 실데이터, 외부 시장 API, live/paper/주문 실행
- Monte Carlo 실행, BT-4 구현, BT-5/BT-6 실행
- 인라인 인터프리터 실행(`python -c` 등), 임시 스크립트

## ALLOWED_FILES

ALLOWED_FILES:
- M src/moneylab/backtest/vault.py
- A src/moneylab/backtest/risk_check.py
- M tests/test_backtest_vault.py
- A tests/test_backtest_risk_check.py
- M docs/backtest_design.md

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/BT-3E/** (WORKSPACE_SETUP의 이 파일 최초 생성과 ACCEPTED ERRATA 생성만 예외)
- docs/tasks/** (README.md, TEMPLATE.md, WO-V1/**, BT-3D/** 포함)
- .claude/**
- .github/**
- CLAUDE.md
- README.md
- AGENTS.md
- .agents/**
- .gitignore
- .gitattributes
- pyproject.toml
- requirements*.txt
- configs/**
- docs/agent_workflow.md
- docs/backtest_bt2b3_metrics.md
- docs/backtest_bt2b4_metrics.md
- docs/incidents/**
- docs/live_execution_design.md
- docs/research_v04_preregistration.md
- docs/research_v05_preregistration_draft.md
- docs/research_v06_preregistration_draft.md
- src/moneylab/__init__.py
- src/moneylab/__main__.py
- src/moneylab/cli.py
- src/moneylab/config.py
- src/moneylab/backtest/__init__.py
- src/moneylab/backtest/bars_io.py
- src/moneylab/backtest/benchmarks.py
- src/moneylab/backtest/code_state.py
- src/moneylab/backtest/cost_analysis.py
- src/moneylab/backtest/costs.py
- src/moneylab/backtest/data.py
- src/moneylab/backtest/execution.py
- src/moneylab/backtest/ledger.py
- src/moneylab/backtest/metrics.py
- src/moneylab/backtest/performance.py
- src/moneylab/backtest/portfolio.py
- src/moneylab/backtest/report.py
- src/moneylab/backtest/round_trips.py
- src/moneylab/backtest/run.py
- src/moneylab/backtest/segment.py
- src/moneylab/backtest/settings.py
- src/moneylab/backtest/strategy.py
- src/moneylab/backtest/yearly.py
- src/moneylab/analytics/**
- src/moneylab/core/**
- src/moneylab/display/**
- src/moneylab/domain/**
- src/moneylab/execution/**
- src/moneylab/paper/**
- src/moneylab/pnl/**
- src/moneylab/providers/**
- src/moneylab/recording/**
- src/moneylab/research/**
- src/moneylab/risk/**
- src/moneylab/scanner/**
- src/moneylab/sizing/**
- src/moneylab/storage/**
- src/moneylab/strategy/**
- base(3f0880b)에서 tests/ 아래 tracked인 모든 파일 중 tests/test_backtest_vault.py를 제외한 전부 (tests/fixtures/** 포함)

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 이 Work Order는 INVALID이고 IMPLEMENTATION에 진입할 수 없다)

## NON_GOALS

NON_GOALS:
- 연구 정책 값 선택(비율, 지표·대응 선택, 비용, 자본, 구간, F 규칙 등은 BT-4)
- BT4-Q18(엔진의 gap-free 창 vs 사전등록 D·D−N 종가) 해결, 신호 로직 변경
- 위반 후 study 수준의 중단·REJECT 절차
- 실제 F 결정과 실제 월별 확인(BT-6)
- `vault_status` 변경, D14 IDENTICAL 규칙 변경, 기존 증거 3종·접근 기록(D7) 스키마 변경, `open_once`·`seal`·`open_analysis` 동작 변경
- CLI, guard, Monte Carlo, 실데이터

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- E1 공개 API (Q1):
  - 새 모듈 함수 `record_risk_policy`, `record_risk_strategies`, `risk_status`와 `ForwardVault.check_risk` 메서드를 추가한다. 그 밖의 공개 표면은 바뀌지 않는다.
  - BT-3E 이후 `vault.py`의 `__all__`은 정확히 다음 28개다.
    - 기존 21개: VaultSpec, build_vault, vault_status, record_evidence, HistoricalHoldoutVault, ForwardVault, VaultError, VaultLockedError, VaultPreconditionError, VaultIntegrityError, VaultExistsError, CREATED, ALREADY_SEALED_IDENTICAL, RECORDED, ALREADY_RECORDED_IDENTICAL, UNOPENED, OPENED, RECORD_UNREADABLE, ABSENT, PASS, FAIL
    - 새 7개: record_risk_policy, record_risk_strategies, risk_status, UNCHECKED, CONSUMED_NO_RESULT, COMPLETED, VIOLATION
  - `ForwardVault.check_risk`는 메서드이므로 `__all__` 이름을 추가하지 않는다. 밑줄 없는 모듈 속성은 이 28개(와 `from __future__ import annotations`의 기능 플래그)뿐이어야 한다.
  - `risk_check.py`는 `__all__ = []`이고 밑줄 없는 모듈 속성을 두지 않는다(같은 기능 플래그 예외). 공개 helper·dataclass·import 별칭을 두지 않는다.
- E2 확증 MDD 바인딩 (Q2):
  - 확증 기준 MDD는 내부에서 재계산한다. 호출자가 확증 MDD 값을 넘기는 경로는 없다.
  - 재계산은 vault의 public bars/1 데이터를 쓰고 다음에 바인딩된다: vault_content_sha256, 전략별 평가 설정과 config_sha256, confirmatory_first_day·confirmatory_last_day, window_mapping_id, metric_id, engine_semantics_id, preregistration_sha256·config_sha256.
  - 확증 엔진 구간의 G_end(= confirmatory_last_day + 3일)는 public 경계 C 이하여야 하고, 확증 계산에 쓰는 행은 모두 public 행이어야 한다. 위반이면 정책 기록을 거부한다.
  - 확증과 forward는 같은 전략 설정, 같은 지표, 같은 엔진으로 계산한다.
  - 기존 vault 보장 이상의 암호학적 보장은 없다. BT-3D N2(기록 삭제로 초기화)는 그대로 적용된다.
- E3 접근 단위와 출력 (Q3):
  - 적격 봉인 월마다, 바인딩된 F 전체에 대해 소비 확인을 1회만 허용한다.
  - 성공 시 공개 결과는 전략 ID → PASS | VIOLATION 맵뿐이다(전략당 1비트).
  - 내보내지 않는 것: MDD 값(확증·forward), 비율 계산 결과, 가격, 수익률, 행, 보호 시각, 행 수, 낙폭 크기.
- E4 위험 명세 저장 (Q4):
  - `record_evidence`에 네 번째 종류를 추가하지 않는다.
  - 기존 evidence state 디렉터리 안의 한 번만 기록하는 별도 레코드 `evidence/risk_policy.json`, `evidence/risk_strategies.json`을 쓴다. 생성 방식은 BT-3D D7과 같다(같은 디렉터리의 임시 파일, fsync, `os.link`로 배타적 생성).
  - 기존 증거 3종의 의미, `open_once`의 요구 조건, `vault_status`의 증거 표시는 바뀌지 않는다.
  - 새 최상위 vault 디렉터리를 만들지 않는다. BT-3D D14 IDENTICAL 동작을 보존한다.
- E5 두 단계 바인딩 (Q5):
  - 1단계 `record_risk_policy`: holdout 개봉 전에만 기록할 수 있다. `access/holdout_open.json`이 이미 있으면 거부한다. 장치가 쓰는 모든 연구 정책·평가 값(후보 전략 설정 포함)을 담는다.
  - 2단계 `record_risk_strategies`: holdout 개봉 후, 그리고 어떤 forward 접근(위험 확인 접근 기록이나 forward 분석 접근 기록)보다도 전에만 기록할 수 있다. holdout이 열리지 않았으면 거부, forward 접근 기록이 하나라도 있으면 거부한다. 실제 F를 고정된 후보 집합의 부분집합으로 바인딩한다.
  - holdout 결과가 나온 뒤에는 위험 정책을 바꿀 수 없다.
  - holdout 개봉 전에 위험 정책을 기록하지 않았다면 위험 확인은 계속 사용할 수 없다(fail-closed).
  - 이를 보완하려고 `HistoricalHoldoutVault.open_once`를 바꾸지 않는다.
  - 같은 내용으로 다시 기록하면 ALREADY_RECORDED_IDENTICAL(쓰기 없음), 다른 내용이면 VaultExistsError다.
- E6 날짜 대응 (Q6):
  - 지원하는 대응은 이름 붙인 enum 하나 `ENGINE_WINDOW_BT3B`뿐이다. 기본값은 없고 정책에 명시해야 한다.
  - 의미: 보호 구간 시작 날짜를 P라 할 때 engine first_day = P − 2일. 대상 월 m의 다음 달 시작을 N이라 할 때 engine last_day = N − 3일(엔진 G_end = N).
    - 누적 방식(CUMULATIVE_FROM_L)에서 P = L(vault spec의 locked_end_utc)이다. 월 단독 방식(MONTH_ONLY)에서 P = max(m 시작, L)이다.
    - 확증 계산은 정책의 confirmatory_first_day/confirmatory_last_day를 engine first_day/last_day로 그대로 쓴다.
  - 결과를 문서에 명시한다: 첫 엔진 기준 시각은 L(또는 P)보다 앞설 수 있고 그 값은 허용된 lookback 행에서 온다. 월말 하루의 수익률은 엔진의 다음 날·다음 달 의미로 넘어갈 수 있다.
  - 검증: 엔진에 필요한 끝이 허용된 봉인 범위(대상 월까지)를 넘지 않는다. 허용된 봉인 행과 lookback 행(locked holdout, 그리고 필요하면 public)만 쓴다. 대상 월이 check_window_end_utc 정책 안에 있다.
  - BT-3E가 `ENGINE_WINDOW_BT3B`를 지원한다고 해서 BT-4가 그것을 고른 것은 아니다. 다른 대응은 별도 승인 작업이다. MC-V06은 나중에 같은 대응 ID를 따라야 한다.
- E7 월별 상태와 결과 기록 (Q7):
  - 상태: UNCHECKED(접근 기록 없음), CONSUMED_NO_RESULT(접근 기록은 있으나 유효한 결과가 없음: 결과 없음, 형식 오류, 결속 불일치 포함), COMPLETED(두 기록 모두 유효하고 서로 결속됨).
  - 접근 기록은 보호 행을 읽기 전에 만든다. 접근 기록 생성 뒤의 모든 실패는 그 달을 소비한다.
  - CONSUMED_NO_RESULT 이후 재시도나 재개봉은 없다(VaultLockedError).
  - 결과 기록은 평가가 성공한 뒤에만 게시한다(배타적 원자 생성, BT-3D D7 방식).
  - 접근 기록 없이 결과만 있으면 무결성 실패다.
  - 결과 게시 충돌: 같은 바이트면 기존 결과를 받아들이고, 다르면 VaultIntegrityError이며 그 달은 소비된 상태로 남는다.
  - 같은 달에 대한 두 번째 `check_risk`는 상태와 무관하게 VaultLockedError이며 보호 행을 다시 읽지 않는다. 결과는 `risk_status`로 읽는다.
- E8 status (Q8):
  - `vault_status`를 바꾸지 않는다. BT-3D D16의 10개 키 계약을 그대로 유지한다.
  - 별도 `risk_status(vault_dir)`를 둔다. 반환은 다음 최소 비민감 정보뿐이다: policy(RECORDED/ABSENT), strategies(RECORDED/ABSENT), integrity(PASS/FAIL), months{YYYYMM: {state: UNCHECKED|CONSUMED_NO_RESULT|COMPLETED, decisions: 전략→PASS|VIOLATION 또는 null}}(기록이 있는 달만). MDD·행·가격·시각·경로·오류 문자열은 반환하지 않는다.
- E9 지표 (Q9):
  - 지원 지표는 `MAX_DRAWDOWN_LOG` 하나다. 의미: `simulate`의 일별 원장 equity(시나리오 기준 시각)로 만든 로그수익률 경로의 최대 낙폭 비율(`backtest/performance.max_drawdown_log`와 같은 공식).
  - 기본값은 없다. 정책이 명시해야 한다. 지원한다고 해서 BT-4가 고른 것은 아니다.
- E10 VIOLATION·final 이후 (Q10):
  - 장치는 VIOLATION 이후 study 수준 중단을 하지 않는다. 다른 조건이 맞으면 이후 달도 확인할 수 있다.
  - check_window_end_utc 밖의 달은 거부한다. 규칙: check_window_end_utc가 null이 아니면 대상 월 시작 < check_window_end_utc여야 한다. null은 "경계 없음"을 명시한 값이며 기본값이 아니다(키 누락은 거부).
  - 대상 월은 month(L) 이상이어야 한다. 누적 방식이면 month(L)부터 대상 월까지 모든 달이 봉인되고 무결해야 한다. 월 단독 방식이면 대상 월이 봉인되고 무결해야 한다.
- E11 모듈 경계 (Q11):
  - 비공개 순수 계산 모듈 `src/moneylab/backtest/risk_check.py`를 추가한다.
  - 의존 방향: vault → risk_check → 기존 backtest portfolio/costs/performance/data와 domain. risk_check는 vault를 import하지 않는다. research를 import하지 않는다. 순환 import가 없다.
  - vault.py는 접근 상태, 증거·명세 바인딩, 무결성, 소비, 비공개를 맡는다. risk_check.py는 바인딩된 명세에서 RunConfig 재구성(`CostModel.scenario`와 `RunConfig` 생성자 사용, 기존 모듈 수정 없음), 순수 평가, 확증 기준 재계산, forward 위험 계산, 비교를 맡는다.
- E12 E2E (Q12): E2E_GATES 참조. CLI를 추가하지 않는다.
- E13 BT4-Q18 (Q13):
  - BT4-Q18을 해결하지 않는다. 신호 로직을 바꾸지 않는다.
  - 위험 정책은 `engine_semantics_id`를 식별·바인딩용으로만 기록한다. 현재 값은 장치 상수(현재 엔진의 gap-free 창 신호, BT-3b 경계, 시나리오 기준 시각 의미를 나타내는 고정 문자열)다.
  - 다른 신호 의미를 고르는 런타임 스위치나 기본값을 두지 않는다. 정책에 기록된 값이 장치 상수와 다르면 거부한다.
- E14 정책과 장치 분리:
  - BT4_FROZEN_VALUE(정책이 명시, 기본값 없음): metric_id, threshold_ratio, comparison_operator, accumulation_mode, window_mapping_id, 전략별 scenario·initial_cash·fee_bps·kappa_bps·impact_bps·fill_substitution·capacity_verified, 후보 전략 집합과 설정, f_rule_sha256(F 선택 규칙 식별), confirmatory_first_day, confirmatory_last_day, check_window_end_utc
  - SUPPORTED_ENUM(구현된 값만 허용): metric_id ∈ {MAX_DRAWDOWN_LOG}, window_mapping_id ∈ {ENGINE_WINDOW_BT3B}, comparison_operator ∈ {gt, ge}, accumulation_mode ∈ {CUMULATIVE_FROM_L, MONTH_ONLY}, scenario ∈ 엔진 SCENARIOS, fill_substitution ∈ 엔진 규칙, 전략 ID ∈ 엔진 RULES
  - DERIVED_IDENTITY: 전략별 config_sha256, vault_content_sha256, preregistration_sha256, config_sha256, L(vault spec), 레코드 SHA
  - MECHANISM_CONSTANT: engine_semantics_id
  - BT6_REALIZED_VALUE: 실제 F, basis_sha256(F 근거)
  - RUNTIME_NONPOLICY: caller, 대상 월
  - BT4_FROZEN_VALUE 필드가 하나라도 없거나 형식이 틀리면 VaultPreconditionError다(사용 아님).
- E15 닫힌 레코드 스키마 (모든 값은 JSON, 키 집합이 정확히 일치해야 유효):
  - risk_policy (`evidence/risk_policy.json`, 결정적, 시각·caller 없음): kind="risk_policy", vault_content_sha256, preregistration_sha256, config_sha256, metric_id, threshold_ratio(10진 문자열, > 0), comparison_operator, accumulation_mode, window_mapping_id, engine_semantics_id, confirmatory_first_day, confirmatory_last_day, check_window_end_utc(UTC 00:00 문자열 또는 null), candidates{rule: {scenario, initial_cash, fee_bps, kappa_bps, impact_bps, fill_substitution, capacity_verified, config_sha256}}, f_rule_sha256. risk_policy_sha256 = 이 레코드의 canonical JSON SHA-256.
  - risk_strategies (`evidence/risk_strategies.json`, 결정적, 시각·caller 없음): kind="risk_strategies", vault_content_sha256, risk_policy_sha256, strategies(정렬된 고유 rule ID 목록, 비어 있지 않음, candidates의 부분집합), basis_sha256(64자리 hex). risk_strategies_sha256 = canonical JSON SHA-256.
  - 월별 접근 기록 (`access/risk_YYYYMM.json`, 소비 시점): kind="risk_check", month, vault_content_sha256, risk_policy_sha256, risk_strategies_sha256, preregistration_sha256, config_sha256, files{사용한 봉인·public 파일 상대경로: SHA}, checked_at_utc(시각), caller.
  - 월별 결과 기록 (`access/risk_YYYYMM.result.json`, 결정적, 시각 없음): kind="risk_result", month, access_record_sha256(접근 기록 파일 바이트의 SHA), risk_policy_sha256, risk_strategies_sha256, decisions{정렬된 rule: PASS|VIOLATION}.
  - 어떤 레코드에도 행, 가격, 수익률, MDD 값, 확증 MDD 값, 낙폭, 행 시각, 행 수를 넣지 않는다.
  - 기존 접근 기록(holdout_open, forward_interim, forward_final)의 D7 8개 키 스키마와 `_record_state` 판단은 바뀌지 않는다.
- E16 실패 처리 (기존 VaultError 하위 클래스만 사용, 메시지에는 타입·이름만):
  - 접근 기록 생성 전(사용 아님): 명세 형식 오류·누락 → VaultPreconditionError. 식별 불일치(vault, prereg, config, policy, F) → VaultPreconditionError. F 없음·잘못됨 → VaultPreconditionError. 봉인되지 않은·부적격 월 → VaultPreconditionError. 무결성·해시 실패 → VaultIntegrityError. 정책·F를 다른 내용으로 다시 기록 → VaultExistsError. 이미 있는 월별 접근 기록·생성 경쟁 패배 → VaultLockedError.
  - 접근 기록 생성 후(사용): 파싱·평가·무결성 실패 → VaultIntegrityError. BaseException → 그대로 전파(사용). CONSUMED_NO_RESULT 재시도 → VaultLockedError. 유효한 접근 기록 없는 결과 → 무결성 실패.
  - 예외 메시지에 보호 값(가격, 수익률, MDD, 시각, 행)을 넣지 않는다. 의존 모듈 예외는 타입 이름만 남겨 감싼다.
- E17 보장과 비보장:
  - 보장: 정책은 holdout 개봉 전, F는 개봉 후·첫 forward 접근 전에만 기록된다. 달마다 소비 위험 접근은 1회다. 기록을 먼저 쓰고 읽는다. 기록 후 실패는 사용으로 센다. 확증 기준은 내부에서 재계산한다. 식별 바인딩. 보호 지표·데이터를 내보내지 않는다. fixture 전용. 지정된 레코드는 결정적이다. BT-3D `vault_status`·D14 의미를 보존한다.
  - 비보장: state 삭제를 암호학적으로 막지 못한다(N2). 실데이터 보안을 주장하지 않는다. 기존 vault 모델 이상의 OS 수준 공격자 방어는 없다. BT-4 연구 정책 값을 고르지 않는다. BT4-Q18을 해결하지 않는다. study 수준 중단·REJECT 절차를 구현하지 않는다. Monte Carlo를 실행하지 않는다. 실제 BT-6 월별 확인을 실행하지 않는다. `ENGINE_WINDOW_BT3B`·`MAX_DRAWDOWN_LOG` 지원은 BT-4가 그것들을 골랐다는 뜻이 아니다.
- E18 하위 호환: bars/1, segment/1, run/2, report/2, result, vault/1 형식과 BT-3D 공개 동작(open_once, seal, open_analysis, record_evidence, vault_status, build_vault, D14)을 바꾸지 않는다. 기존 BT-3D 테스트의 의도는 그대로 통과해야 한다(공개 표면 테스트만 28개 이름으로 갱신).
- E19 docs/backtest_design.md 갱신: 10.3에 BT-3E 절(E1–E17 요약, 날짜 대응 결과, 비보장, BT-4·BT-6 의존성), 개정 이력에 BT-3e 행. SYNTHETIC / NOT_EVIDENCE 표시. DP1을 "장치 구현됨, 정책 값은 BT-4"로 갱신하되 DP2–DP4는 미해결로 둔다.

## DEFERRED_TO_LATER_TASKS

DEFERRED_TO_LATER_TASKS:
- BT-4: 비율, 비교 연산, 누적 방식, 지표·날짜 대응 선택, 전략별 비용·자본·시나리오, 확증 구간, check_window_end_utc, F 선택 규칙, 위반 시 처리, BT4-Q18, D1–D10, U4/U4a/U5/U6, DP2–DP4
- BT-6: 실제 F와 근거 SHA, 실제 월별 확인 실행
- MC-V06: 같은 대응·지표·누적 의미로 위험 확인 모델링
- 이 항목들은 해당 task를 승인하지 않는다.

## TEST_GATES

TEST_GATES:
- 새 파일 tests/test_backtest_risk_check.py와 갱신된 tests/test_backtest_vault.py (합성·fixture, tmp_path, 오프라인):
  - T1 `vault.py`의 `__all__`이 정확히 E1의 28개이고, 밑줄 없는 모듈 속성이 그 28개와 `annotations`뿐이다. 기대 집합은 테스트에 직접 적는다(구현에서 가져오지 않음).
  - T2 `risk_check.py`는 `__all__ == []`이고 밑줄 없는 모듈 속성이 `annotations`뿐이다.
  - T3 정책 기본값 없음: E14의 BT4_FROZEN_VALUE 필드를 하나씩 빼거나 형식을 틀리게 하면 VaultPreconditionError이고 어떤 레코드도 생기지 않는다.
  - T4 지원하지 않는 enum 값(metric_id, window_mapping_id, comparison_operator, accumulation_mode, scenario, fill_substitution, 전략 ID)과 다른 engine_semantics_id를 거부한다.
  - T5 정책 기록 시점: holdout 개봉 뒤 `record_risk_policy`는 거부되고 이후 위험 확인은 계속 불가능하다.
  - T6 F 기록 시점: holdout 개봉 전, 또는 위험 접근·forward 분석 접근 기록이 있은 뒤의 `record_risk_strategies`는 거부된다.
  - T7 canonical F: 후보 밖, 정렬되지 않음, 중복, 빈 목록, 잘못된 basis_sha256을 거부한다.
  - T8 정책·F 불변: 같은 내용 재기록은 ALREADY_RECORDED_IDENTICAL이고 바이트가 바뀌지 않는다. 다른 내용은 VaultExistsError다.
  - T9 식별 불일치(prereg, config, vault, policy SHA, F SHA)는 VaultPreconditionError이고 접근 기록이 생기지 않는다.
  - T10 월 자격: month(L) 이전, check_window_end_utc 밖, 봉인되지 않은 달, 누적 방식에서 중간 달 누락을 거부한다(사용 아님).
  - T11 확증 기준 내부 재계산: 호출자가 MDD 값을 넣는 인자가 없고, public 데이터를 변조하면 무결성 실패, 같은 입력이면 같은 결정이 나온다.
  - T12 확증 구간 제약: confirmatory_last_day + 3일 > C이면 정책 기록을 거부한다.
  - T13 기록 후 읽기: 접근 기록 생성 직후 읽기·평가 단계에 실패를 주입하면 VaultIntegrityError이고 그 달은 CONSUMED_NO_RESULT로 남는다.
  - T14 접근 기록 생성 뒤 BaseException도 그대로 전파되고 그 달을 소비한다.
  - T15 배타적 접근: 기록 존재 확인을 우회해도 배타적 생성에서 패배하면 VaultLockedError다.
  - T16 CONSUMED_NO_RESULT 재시도는 VaultLockedError이고 보호 행을 다시 읽지 않는다.
  - T17 접근 기록 없는 결과 기록은 `risk_status`의 integrity FAIL이고 해당 달 `check_risk`를 거부한다.
  - T18 이상한 state(빈·깨진·키 불일치 정책, F, 접근, 결과 기록)는 fail-closed다.
  - T19 COMPLETED 달의 두 번째 `check_risk`는 VaultLockedError다.
  - T20 결정적 fixture PASS: 합성 데이터로 모든 F 전략이 PASS인 경우를 만들고, 같은 입력이면 결과 기록 바이트가 같다.
  - T21 결정적 fixture VIOLATION: 적어도 한 전략이 VIOLATION, 다른 전략이 PASS인 혼합 맵을 만든다.
  - T22 비공개: 반환값, 모든 위험 레코드, `risk_status`, 예외 메시지에 합성 가격, 보호 행 시각, MDD 값, 비율 계산 결과가 들어 있지 않다.
  - T23 real provenance를 거부하고, `vault_status`가 BT-3D D16의 10개 키 그대로이며, 위험 레코드가 있어도 D14 IDENTICAL 재구성이 그대로 동작한다.
  - T24 BT-3D 회귀: 기존 tests/test_backtest_vault.py의 BT-3D 테스트가 공개 표면 갱신 외에는 그대로 통과한다.
- 전체 pytest, failed 0 / errors 0. tests/test_architecture_and_cli.py, tests/test_backtest_architecture.py, tests/test_repo_hygiene.py 통과. ALLOWED 밖 기존 테스트 수정 0.
- `git diff --check` 깨끗함, 변경 파일 집합 = ALLOWED_FILES

## E2E_GATES

E2E_GATES:
- CLEAN_COMMIT_E2E (clean Ci, TARGET_WORKTREE; `PYTHONPATH=C:/MoneyLab-bt3e-risk-check/src`로 worktree 소스를 쓰는지 확인):
  - (1) 전체 pytest, failed 0 / errors 0
  - (2) tests/test_backtest_vault.py, tests/test_backtest_risk_check.py 단독 실행 통과 (T20·T21의 fixture PASS/VIOLATION 포함)
  - (3) 기존 CLI `python -m moneylab backtest --daily <D> --hourly <H> --rule <r> --first-day 2025-06-26 --last-day 2025-11-28 --out <새 ignored 루트>/runs-<r>-fixture` (기본값 fee 25, inclusive, E0, impact 사용, substitution none, settings 기본값)로 5개 baseline을 다시 만들고 result.json SHA-256이 다음과 정확히 같아야 한다.
    - D = C:/MoneyLab-bt2b3-e2e/data/processed/e2e-v20y/bars-fixture/day_KRW-BTC_20261016T042949164072Z (bars_sha256 d6a40221a2c3b810d468b0f522cc2a1ef2305315f43864e0b37e7410251ec561)
    - H = C:/MoneyLab-bt2b3-e2e/data/processed/e2e-v20y/bars-fixture/hour_KRW-BTC_20261016T042950020977Z (bars_sha256 39ad26cbb0cedfe3a647f6dc01e31d19f8bec58a9d69f460918516bad972e412)
    - sma20 01b86731f866d1e12642d6419f15e52be10e3ff23812ed62c756c5980ebb7b2d
    - M20 d356e54fc854591b7d5c02c3141fe96c2f6e286338cc0f492a47440717262840
    - M60 6a5ec2801f546b45f4f9f7a1cee07d3d9f574e6b03f631e5c7883639340b6810
    - M120 732939763638bf78d99cf0ccb12cb1aff7159288aac413536f2eb9c5429aec1b
    - R5 49f1eedca1b8d4db5431391e8552895b6d139d4d37a46b2c6569b419349dcb5f
    - 출처: BT-3D CLEAN_COMMIT_E2E의 참조 복원(이전 BT-3a/BT-3b E2E 산출물, HISTORICAL_ARTIFACT_VERIFIABLE)과 BT-3D Ci에서의 5/5 재현.
  - (4) CLI 위험 확인 명령은 없다. 위험 확인 E2E는 커밋된 테스트(2)로 확인한다.
- 기존 출력·reference fixture·이전 산출물은 수정하지 않는다. `locked/` 경로는 단독 `sha256sum`·`ls`로만 다룬다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base SHA/tree, C1 SHA/parent/tree, Work Order sha256, Ci SHA/parent/tree, 커밋별 파일 집합과 diff stat, merge parent/tree
- CLAUDE_REPORTED: targeted·전체 pytest 결과, E2E 결과(baseline SHA 5개, 위험 확인 테스트)
- INDEPENDENT/GITHUB_VERIFIABLE: PR CI 결과, GitHub 화면(사용자 확인)
- 보고서는 각 값의 evidence 등급을 표시한다. Claude가 실행한 결과를 INDEPENDENT로 표시하지 않는다.

## REQUIRED_REPORT

REQUIRED_REPORT: 각 gate의 보고는 해당 Gate Authorization 메시지가 지정한 key 목록으로 끝내고, 최소 다음을 포함한다.
- WORK_ORDER_CONTRACT_VERSION, TASK_ID, 현재 gate, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD/parent/tree, 변경 파일 집합, protected diff, worktree clean, diff --check
- 증거 등급 표시, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- `<GATE>_PASS = YES / NO`, `READY_FOR_<NEXT_GATE> = YES / NO`

## STOP_CONDITIONS

STOP_CONDITIONS:
- base/HEAD/tree가 기대와 다름, Work Order sha256이 C1과 다름
- ALLOWED_FILES 밖 tracked 변경 또는 PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기가 실제 base 상태와 다름
- guard deny 또는 permission prompt 거절
- 테스트 실패/에러, baseline result 바이트 불일치
- 계약 모순 또는 상위 규칙과 충돌
- 계약을 지키려면 PROTECTED 파일(portfolio.py, costs.py, performance.py, run.py, bars_io.py, storage/atomic.py, cli.py 등) 수정이 필요하다고 판명됨 (PROPOSED_ERRATA로 보고)
- 연구 정책 값을 기본값으로 정해야만 구현이 가능하다고 판명됨 (PROPOSED_ERRATA로 보고)
- 예상하지 못한 untracked 파일

## REPORT_STORAGE

REPORT_STORAGE: gate별 보고는 채팅만. 저장소에 보관하지 않는다. COMPLETE 증거 요약을 파일로 남기려면 ACCEPTED ERRATA가 경로와 최초 생성을 명시해야 한다.
