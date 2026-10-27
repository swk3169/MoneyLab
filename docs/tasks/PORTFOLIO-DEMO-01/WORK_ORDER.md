# Work Order: PORTFOLIO-DEMO-01 — 합성 데이터 backtest pipeline demo와 영어 ARCHITECTURE.md

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/PORTFOLIO-DEMO-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: PORTFOLIO-DEMO-01
TASK_ID: PORTFOLIO-DEMO-01
TITLE: 기존 합성 데이터 backtest pipeline을 한 명령으로 보여주는 offline demo와 구현된 아키텍처의 영어 문서
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 128bbad9a349deeda131b46b95cb7487ab084ef5
CANONICAL_BASE_TREE: 0a4dd7cbc48716e88da23fe55b6a3ee109907e1b
REPOSITORY: swk3169/MoneyLab (PUBLIC)
TARGET_BRANCH: feature/portfolio-demo-01
TARGET_WORKTREE: C:/MoneyLab-portfolio-demo-01
EXTERNAL_TOOL_VENV: QUALITY-GATES-01에서 만든 외부 venv. 모든 MoneyLab 저장소·worktree 밖, 사용자 프로필 디렉터리 아래 `.venvs/moneylab-quality-gates-01`. 정확한 machine-local 경로는 Gate Authorization과 채팅 증거에만 둔다.
WORKSPACE_SETUP: REQUIRED (fetch 없음, canonical base commit 자체에서 branch·worktree 생성, 이 파일을 C1으로 발행)
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (MERGE gate에서 따로 승인)

## GATE_SEQUENCE

GATE_SEQUENCE: DISCOVERY_INVENTORY -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> Q0_MEASUREMENT -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

DISCOVERY_INVENTORY(PASS), CONTRACT_REVIEW(PASS)는 C1 이전에 채팅에서 끝났다(historical). WORKSPACE_SETUP이 이 파일을 C1으로 발행한다.

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 명시적 Gate Authorization으로 한 gate씩만 앞으로 간다. 각 gate의 보고 후 멈춘다. 다음 gate를 자동으로 시작하지 않는다.
- rollback은 명시적 승인으로 IMPLEMENTATION까지만 한다.
- COMMIT 이후 수정은 새 commit으로 한다. amend, force push, squash, rebase를 하지 않는다(따로 승인된 경우 제외).
- Q0_MEASUREMENT가 PASS하기 전에는 IMPLEMENTATION에 들어가지 않는다.
- task branch·worktree 정리는 이 task에 포함되지 않는다. 따로 승인될 때만 한다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다. guard deny는 우회하지 않는다.

## GOAL

GOAL: 기존 MoneyLab 합성 데이터 backtest pipeline을 보여주는 작은 공개 portfolio 표면을 만들고, 구현된 아키텍처를 영어로 문서화한다. 외부 reviewer가 구현된 아키텍처를 이해하고, 저장소에서 의미 있는 offline·결정적 합성 pipeline demo 하나를 실행할 수 있게 한다.

NON_GOALS (이 task가 아닌 것):
- strategy research
- profitability validation
- live-trading validation
- agent implementation
- MCP implementation
- autonomous trading implementation
- statistical-method redesign
- backtest-engine refactoring

## BACKGROUND

BACKGROUND:
- QUALITY-GATES-01 COMPLETE. 이 task의 base는 그 merge commit(`128bbad9…`, PR #28)이다.
- 기존 offline pipeline: `candles-pull --source fixture` -> `bars-export` -> `backtest` -> `backtest-verify` -> `backtest-report --seed` -> `backtest-report-verify` (`src/moneylab/cli.py`).
- 사용할 fixture `tests/fixtures/upbit_candles_backtest_synthetic.json`은 합성 선형 가격이고, pipeline 확인용이며 strategy test용이 아니다.
- CONTRACT_REVIEW 정정 사항: `tests/test_bar_export.py`의 `GOLDEN_FINAL_EQUITY`는 `random_market(60, seed=4)` 기반 test의 값이며 이 선형 fixture와 무관하다. 이 fixture에 대해 고정된 golden은 아래 GOLDEN_HASH_POLICY의 bar hash뿐이다.

## SCIENTIFIC_BOUNDARY

SCIENTIFIC_BOUNDARY:
- demo의 성격: "pipeline demonstration on synthetic data"
- evidence label: `SYNTHETIC / NOT_EVIDENCE`
- demo는 다음을 주장하거나 암시하지 않는다: profitable strategy, validated strategy, proven alpha, production readiness, live readiness, real-market validation, autonomous trading implementation, v0.6 strategy validation.
- descriptive 지표는 보여줄 수 있다. 수익성·PnL은 성공 기준이 아니다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: canonical base commit에서 TARGET_BRANCH·TARGET_WORKTREE 생성, 이 파일 하나의 최초 생성과 C1 커밋(subject `docs: preregister portfolio demo task`). push 없음. EXTERNAL_TOOL_VENV 읽기 전용 확인만.
- Q0_MEASUREMENT: 측정만(아래 Q0_MEASUREMENT 절). 저장소 파일 변경 없음.
- IMPLEMENTATION: ALLOWED_FILES 생성·수정, demo·test 실행, GOLDEN_HASH_POLICY에 따른 측정과 result hash 고정, TEST_GATES 실행. commit 없음.
- PRECOMMIT_AUDIT: 읽기와 감사만(PUBLIC_LANGUAGE_CONTRACT 검사 포함).
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, 승인된 commit만.
- CLEAN_COMMIT_E2E: clean commit에서 E2E_GATES 실행. 산출물은 저장소 밖.
- PUSH: `git push -u origin feature/portfolio-demo-01`만. force 없음.
- PR_CI: PR 하나, CI 관찰. merge 없음.
- MERGE: 따로 승인된 방법(merge commit)으로만.
- POST_MERGE_AUDIT: 승인된 main ref fetch, 구조 감사.
- COMPLETE: 최종 보고.

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
- hooks·settings·`.claude` 변경 또는 guard 우회
- 다른 branch·worktree·untracked·ignored·reference 산출물 정리. 특히 `C:/MoneyLab`, `C:/MoneyLab-quality-gates-01-v2`, `C:/MoneyLab-mc-v06`과 그 밖의 기존 worktree를 수정·정리·전환·reset·stash·삭제·재사용하지 않는다.
- 저장소 안 `.venv` 생성
- 새 dependency 추가, 기존 pipeline refactor, CI workflow 수정
- src CLI subcommand 추가
- demo·test에서 monkeypatch, 가짜 commit, code-state check 억제·우회
- 기존 golden 값 변경, 측정 전 result hash 추측
- demo 산출물을 저장소 `data/`에 쓰거나 commit하기
- 네트워크·credential 사용

## ALLOWED_FILES

ALLOWED_FILES:
- A ARCHITECTURE.md
- A examples/synthetic_backtest_demo.py
- A tests/test_examples_demo.py
- M README.md

C1 전용: `A docs/tasks/PORTFOLIO-DEMO-01/WORK_ORDER.md` (WORKSPACE_SETUP에서만. C1 이후 불변이며 PROTECTED).

EXCLUDED: `examples/README.md`는 만들지 않는다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/PORTFOLIO-DEMO-01/** (C1 이후)
- 기존 docs/tasks/**
- src/**
- tests/** (새 파일 `tests/test_examples_demo.py` 생성만 예외)
- tests/fixtures/**
- configs/**
- .github/**
- .claude/**
- CLAUDE.md
- pyproject.toml
- requirements*.txt
- .gitignore
- .gitattributes
- 환경·설정 파일 전체(환경 변수 파일과 그 예시 포함)
- 기존 research·evidence·사전등록·설계 문서 (README.md, ARCHITECTURE.md 외의 docs/** 와 저장소 문서)
- data/**
- LICENSE

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가). README.md는 README_CONTRACT의 추가 전용 patch에 한해 ALLOWED이고, 그 외 변경은 금지다.

## DESIGN_CONTRACT

### D1 DEMO_INTERFACE

- 파일: `examples/synthetic_backtest_demo.py`
- 호출: `python examples/synthetic_backtest_demo.py [--workdir DIR]`. 그 밖의 공개 인자는 없다. 설정은 모두 코드 안의 상수다.
- src CLI subcommand를 추가하지 않는다.
- demo는 기존 공개 MoneyLab 동작을 조율만 한다. 주 실행 경로는 `moneylab.cli.main([...])`이다.
- `tests/` 내부 helper를 import하지 않는다.
- 구조화된 확인에 쓸 수 있는 기존 공개 함수(사전등록 목록, 이 밖은 쓰지 않는다):
  - `moneylab.backtest.run.verify_run`
  - `moneylab.cli.backtest_code_state`
  - 기존 code-state 분류 장치 `moneylab.backtest.code_state.code_state_problems` (와 `classify_worktree`)
- demo 안에서 monkeypatch나 code-state 우회를 하지 않는다.
- backtest 로직을 `examples/`에 복제하지 않는다.

### D2 FIXED_DATA

- fixture: `tests/fixtures/upbit_candles_backtest_synthetic.json`
- 네트워크 없음, credential 없음, 새 synthetic generator 없음.
- 이 fixture는 pipeline-check fixture로 남는다. strategy-test dataset이 아니다.
- fixture 경로와 settings 경로는 예제 파일 위치에서 계산해 CLI에 명시적으로 넘긴다. `MONEYLAB_*` 환경 변수가 다른 데이터 소스를 조용히 고르지 못하게 한다.

### D3 FIXED_PIPELINE_CONFIGURATION

- rule = sma20 (engine-validation rule. 사전등록 v0.6 rule M20/M60/M120/R5가 아니다)
- first_day = 2025-06-26
- last_day = 2025-11-28
- execution scenario = E0
- fee = 25 bp
- fee_basis = inclusive
- candle pull 범위:
  - day: 2025-06-01T00:00:00Z through 2025-12-19T00:00:00Z
  - hour: 2025-06-01T00:00:00Z through 2025-12-18T11:00:00Z
- settings file: `configs/backtest_costs.toml`
- B1 seed: 20261027
- B1 draws: 20
- B1 draws=20은 demo 실행 시간을 위한 선택일 뿐이다. 충분한 통계적 증거나 연구 수준의 Monte Carlo 표본 크기로 설명하지 않는다.

### D4 PIPELINE

demo가 조율하는 단계:
1. candles-pull day fixture
2. candles-pull hour fixture
3. bars-export day
4. bars-export hour
5. backtest
6. backtest-verify
7. backtest-report (code state가 허용할 때)
8. backtest-report-verify (code state가 허용할 때)

기존 pipeline 동작을 그대로 쓴다.

### D5 OUTPUT_POLICY

- `--workdir`가 없으면: OS 임시 작업 디렉터리를 만들고 실행 후 정리한다.
- `--workdir DIR`가 있으면: 생성 산출물을 보존하고 보존 위치를 출력한다.
- fixture provenance 이름이 필요한 모든 출력 root는 기존 `*-fixture` 이름 규칙을 따른다.
- demo 산출물을 저장소 `data/`에 쓰지 않는다. demo 산출물을 commit하지 않는다(run manifest에는 입력의 절대 경로가 기록된다).

### D6 DEMO_SUMMARY

- `--workdir`가 있을 때 `<workdir>/demo_summary.json`을 보존한다.
- schema 식별자: `moneylab.demo.synthetic_backtest/1`
- demo에 필요한 이식 가능한 정보만 담는다: schema, evidence label, code-state 분류, pipeline 단계별 상태, day bars_sha256, hour bars_sha256, result_sha256, verify check 결과, 해당할 때 report·report-verify 상태, DEMO_STATUS.
- machine-local 절대 경로를 넣지 않는다. 경로가 필요하면 workdir 기준 상대 경로로 쓴다.
- 가상의 미래 요구사항을 위해 summary를 과설계하지 않는다.

### D7 CODE_STATE_POLICY

- 기존 MoneyLab code-state 검증을 약화하지 않는다. 기존 동작으로 환경을 분류한다.
- 상위 상태: PINNED, UNPINNED.
- PINNED:
  - 전체 pipeline 실행, report 생성 허용, report verification 필수.
  - 성공 상태 `DEMO_STATUS = COMPLETE`, exit code 0.
- UNPINNED:
  - pull, bars, backtest, verify는 실행한다.
  - report·report-verify를 우회하지 않는다.
  - 실패한 verification 조건이 기존 code-state check 하나뿐이면 report를 만들지 않는다.
  - 성공한 부분 상태 `DEMO_STATUS = PARTIAL_CODE_STATE_UNPINNED`, exit code 4.
  - 기존 MoneyLab 정책상 report 생성에는 pinned code state가 필요하다는 것을 출력한다.
- code가 아닌 verification check가 하나라도 실패하면 `DEMO_STATUS = FAILED`, exit code 1.
- 잘못된 인자: exit code 2.
- exit code 3(moneylab CLI의 "데이터 소스 사용 불가")은 부분 상태에 쓰지 않는다.
- 공식 COMPLETE 환경: clean Git checkout + editable install.
- Git 없음, `.git` 없음, blocking dirty 상태는 기존 정책에 따라 UNPINNED가 될 수 있다.
- monkeypatch 없음, 가짜 commit 없음, code-state check 억제 없음.

EXIT_CODES:
- 0: COMPLETE
- 1: FAILED
- 2: invalid arguments
- 3: 사용하지 않음
- 4: PARTIAL_CODE_STATE_UNPINNED

### D8 EVIDENCE_OUTPUT

- 사람이 읽는 출력에 반드시 포함: `SYNTHETIC / NOT_EVIDENCE`, 단계 상태, day bars_sha256, hour bars_sha256, result_sha256, verify checks, 가능할 때 report verification, DEMO_STATUS.
- descriptive 지표는 보여줄 수 있다. PnL이나 수익률을 대표 성공 기준으로 쓰지 않는다.
- machine evidence를 얻으려고 Rich 터미널 텍스트를 파싱하지 않는다. 구조화된 pipeline 산출물을 읽는다.

### D9 FUTURE_AGENT_COMPATIBILITY

- demo summary 경계는 나중에 Agent Tool 인터페이스로 재사용될 수 있다. 현재 schema는 `moneylab.demo.synthetic_backtest/1`이다.
- 이 task는 Agent framework, Supervisor, MCP, Memory, Knowledge Wiki, autonomous research, autonomous trading을 구현하지 않는다.

## GOLDEN_HASH_POLICY

기존 bar golden (GIT_VERIFIABLE, canonical base의 `tests/test_bar_export.py` `GOLDEN_FIXTURE`에서 그대로 옮김):

- day bars_sha256: `d6a40221a2c3b810d468b0f522cc2a1ef2305315f43864e0b37e7410251ec561` (199 bars)
- hour bars_sha256: `39ad26cbb0cedfe3a647f6dc01e31d19f8bec58a9d69f460918516bad972e412` (4,809 bars)
- 참고(비교 의무 없음): 같은 golden의 page 0 sha256은 day `fe3f3601214a6facee35a581489054661a5c6e97537acf93a0b8af9e8ae76925`, hour `bcd5f91fd1adadc98de51e34d39f8d3426eaaacf1d8d75ff8fb6c869166efc5f`이다. 이 값은 test helper `fixture_pull`(`pull_to_store` 직접 호출) 경로의 것이며 CLI 경로의 page 구성과 같다는 보장은 없다.

대체 값을 계산하지 않는다.

IMPLEMENTATION에서:
- CLI demo 경로를 실행한다.
- CLI가 만든 day·hour bar hash를 위 golden 값과 비교한다.
- 하나라도 다르면 IMPLEMENTATION을 멈춘다. golden을 갱신하지 않는다. 불일치를 재해석하지 않는다. result hash 고정으로 넘어가지 않는다.

result_sha256: UNKNOWN_AT_C1

- Work Order에서 추측하지 않는다.
- IMPLEMENTATION에서 bar hash가 일치한 뒤에만: result_sha256을 측정하고, 독립된 두 번째 동등 실행을 하고, 같은 result_sha256을 요구한 뒤, 관측한 값을 `tests/test_examples_demo.py`에 고정한다.
- 측정값과 출처(commit, 환경, 실행 방식)는 IMPLEMENTATION 보고에 기록한다.
- 측정값을 넣으려고 WORK_ORDER.md를 수정하지 않는다. 계약 정정이 필요하면 따로 승인된 ERRATA gate를 쓴다.

## TEST_GATES

TEST_GATES:
- 새 test 파일은 `tests/test_examples_demo.py` 하나뿐이다. 기존 test는 수정하지 않는다.
- demo 실행: `sys.executable`, examples 스크립트, `--workdir`, pytest `tmp_path` 위치. 셸 없음. examples를 package로 import하지 않는다.
- 최소 확인 항목:
  - `SYNTHETIC / NOT_EVIDENCE`
  - 기대한 pipeline 단계
  - day·hour bar golden hash
  - 승인된 측정 후 고정한 result_sha256
  - code가 아닌 verify check가 모두 true
  - 올바른 code-state 분기
  - PINNED: report 생성, report verification 성공, exit 0, COMPLETE
  - UNPINNED: report 우회 없음, PARTIAL_CODE_STATE_UNPINNED, exit 4
  - Git이 있으면 실행 전후 저장소 status가 같다
- 네트워크가 필요 없어야 한다. 생성 산출물은 저장소 밖에 남는다.
- 알려진 한계: demo subprocess는 부모 프로세스 coverage에 포함되지 않는다.
- 전체 pytest failed 0 / errors 0 (QUALITY-GATES-01의 Linux 실험 job EXPECTED_FAILURE 2건은 CI_CONTRACT에 따로 집계).
- ruff(`--select E4,E7,E9,F src tests`)와 mypy(pyproject 설정) 기존 gate 통과.
- `git diff --check` 깨끗함, 변경 파일 집합 ⊆ ALLOWED_FILES, README diff는 추가 줄만.

## ARCHITECTURE_CONTRACT

- 저장소 root의 영어 `ARCHITECTURE.md`. ASCII 그림만 쓴다(Mermaid 없음).
- 절:
  1. System Overview
  2. Design Principles
  3. Component Architecture
  4. Backtest Data Flow
  5. Research / Evidence Flow
  6. Quality & Reproducibility Controls
  7. Repository Structure
  8. Current Boundaries / Non-Goals
  9. Known Documentation Discrepancies
- 실제 code·import·test를 근거로 쓴다.
- 구성요소마다 다음 중 하나로 분류한다: IMPLEMENTED, PARTIAL / SYNTHETIC-ONLY, DESIGN_ONLY / INTERFACE_ONLY, NOT_IMPLEMENTED.
- 반드시 명시할 내용:
  - execution은 interface-only다
  - live trading은 구현되지 않았다
  - backtest 증거는 synthetic-only다
  - v0.4 결과는 REJECT다
  - MC-V06은 MIXED / DESIGN-INFORMATIVE다
  - READY_WITH_CAUTION은 해당 설계 준비도 맥락에 적용되며 live-trading 준비도가 아니다
  - futility 절차는 경계에서 anti-conservative였고 원인은 아직 밝혀지지 않았다
  - BT4는 design-only다
  - BT-5 / BT-6은 시작하지 않았다
  - Polymarket 실데이터 접근은 HTTP 451로 막혔고, fixture 기반 동작은 real-market validation이 아니다
- Known documentation discrepancies (고치지 않고 기록만):
  1. README 아키텍처 그룹핑은 강제된 backtest 의존성 경계를 정확히 반영하지 않는다.
  2. CLAUDE.md는 `analytics/metrics.py`를 backtest, paper, live가 공유한다고 하지만 backtest에는 자체 `metrics.py`가 있다. 정확한 공유 범위를 과장하지 않는다.
  3. risk와 strategy는 현재 서로 import한다.
  4. providers는 replay 동작을 위해 paper를 import할 수 있다.
- 이를 해결하려고 CLAUDE.md를 수정하지 않는다. 이 task에서 기존 README 아키텍처 그림을 수정하지 않는다.
- 미래의 Agent/Supervisor/MCP/Memory 아키텍처를 구현된 것으로 설명하지 않는다.

## README_CONTRACT

- README.md는 ALLOWED다. 최소한의 추가 전용 discoverability patch만 승인된다.
- 위치: 기존 Getting Started 코드 블록 바로 뒤.
- 추가 내용만:
  - demo 명령 `python examples/synthetic_backtest_demo.py`
  - 이것이 합성 데이터에 대한 pipeline demonstration이고 출력이 `SYNTHETIC / NOT_EVIDENCE`라는 간결한 문장 하나
  - `ARCHITECTURE.md` 링크
- 기존 README 줄을 삭제하거나 고쳐 쓰지 않는다. README diff는 추가 전용이다.
- README 재설계, 부록 번역, 아키텍처 그림 재작성 없음.

## PUBLIC_LANGUAGE_CONTRACT

- 허용·권장 개념: synthetic, synthetic data, pipeline demonstration, reproducibility, reproducible, deterministic hash, verification, verified run, SYNTHETIC / NOT_EVIDENCE, descriptive metrics, engine-validation rule, cost-aware, offline.
- 금지되는 긍정 주장: profitable, validated strategy, proven alpha, edge found, production-ready, live-ready, real-market validation, implemented autonomous trading system.
- "profitability"는 명시적 부정·면책 문맥에서만 쓸 수 있다.
- demo는 사전등록 v0.6 rule의 평가를 암시하지 않는다.
- PRECOMMIT_AUDIT는 새로 만들거나 바꾼 공개 텍스트에서 이 주장들을 검사한다.

## CI_CONTRACT

- CI workflow를 수정하지 않는다.
- 기존 pytest discovery가 `tests/test_examples_demo.py`를 수집해야 한다.
- Windows required CI: 새 demo test가 PASS해야 한다.
- Linux experimental CI: 새 demo test가 PASS해야 한다.
- QUALITY-GATES-01에서 사전등록한 Linux wrapper 실패 2건은 별도 EXPECTED_FAILURE로 남는다.
- Linux에서 `tests/test_examples_demo.py`가 하나라도 실패하면 이 task의 UNEXPECTED_FAILURE다.

## PYTHON_ENVIRONMENT

- 저장소 안 `.venv`를 만들지 않는다.
- EXTERNAL_TOOL_VENV가 여전히 있고 interpreter·toolchain이 쓸 수 있을 때만 재사용한다.
- WORKSPACE_SETUP은 읽기 전용 확인만 한다. 패키지 설치·업그레이드·제거·변경을 하지 않는다.
- 쓸 수 없으면 멈추고 보고한다. 다른 환경을 조용히 만들지 않는다.
- WORKSPACE_SETUP 관측(CLAUDE_REPORTED, 읽기 전용): interpreter CPython 3.14.8, ruff 0.17.2, mypy 2.4.0, coverage 7.17.0, pytest 9.1.1을 실행할 수 있다. 이 환경에는 `moneylab` 배포 metadata가 없다(설치되지 않음). pytest는 pyproject `pythonpath = ["src"]`로 `moneylab`을 찾지만, demo subprocess가 `moneylab`을 import하는 방법은 Q0_MEASUREMENT에서 측정하고, 환경 변경(예: editable install)이 필요하면 따로 승인을 받는다.

## Q0_MEASUREMENT

Q0_MEASUREMENT (IMPLEMENTATION 전 측정. WORKSPACE_SETUP에서 실행하지 않는다):
- 외부 Python 환경 정체(interpreter, toolchain 버전, `moneylab` import 가능 여부와 경로)
- demo와 관련된 baseline test 상태
- 현재 정확한 bar golden hash
- 현재 code-state 동작
- baseline 저장소 깨끗함
- 안전한 측정으로 드러나는 후보 demo 경로의 숨은 runtime 의존성

## E2E_GATES

E2E_GATES:
- clean commit checkout에서 demo가 PINNED 분기로 COMPLETE, exit 0
- day·hour bar hash = golden, result_sha256 = IMPLEMENTATION에서 고정한 값
- report 생성과 report-verify 성공
- 실행 전후 저장소 status 동일, 산출물은 저장소 밖

## MUTATION_RULES

MUTATION_RULES:
- C1은 Work Order만 담는다.
- C1 이후 WORK_ORDER.md는 불변이다.
- 구현 commit은 ALLOWED_FILES만 건드린다.
- amend 없음. force push 없음. 따로 승인되지 않은 squash·rebase 없음.
- merge 방법은 나중에 따로 승인된다.
- 이 task의 일부로 task branch·worktree를 정리하지 않는다(따로 승인된 경우 제외).

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 commit SHA·tree, 파일 sha256, commit 파일 집합, merge parent·tree
- CLAUDE_REPORTED: Q0 측정, pytest, demo 실행, bar·result hash 측정, E2E 결과
- INDEPENDENT: PR CI(Windows required, Linux experimental), GitHub 화면(사용자 확인)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES, guard·권한 이벤트
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, Work Order sha256 불일치
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기와 base 상태 불일치
- guard deny, 권한 창 거절, guard ASK(정확한 명령과 prompt를 보고하고 멈춤)
- 테스트 실패·에러, hard gate 불일치
- CLI 경로의 day 또는 hour bar hash가 golden과 다름
- 두 번의 동등 실행에서 result_sha256이 다름
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일, 저장소 안에 demo 산출물 생성
- EXTERNAL_TOOL_VENV를 쓸 수 없음
