# Work Order: QUALITY-GATES-01 — 자동 품질 gate 도입 (ruff, mypy, coverage, Linux 실험 CI)

이 파일은 불변이다. 발행(C1v2) 후 수정하지 않는다. 계약 변경은 `docs/tasks/QUALITY-GATES-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: QUALITY-GATES-01
TASK_ID: QUALITY-GATES-01
TITLE: 공개 저장소에 lint, type check, coverage 측정, Linux 실험 CI를 점진적으로 도입
VERSION: 2.0
STATUS: ISSUED
LINEAGE: v2 (LINEAGE_CORRECTION으로 재발행. 아래 LINEAGE 절)
CANONICAL_BASE_SHA: aeefcfceb0b80f18c9e136f0a20c8d8060e4e575
CANONICAL_BASE_TREE: c9e99516a4e3b625eada53962b3bff29319aecd9
REPOSITORY: swk3169/MoneyLab (PUBLIC)
TARGET_BRANCH: chore/quality-gates-01-v2
TARGET_WORKTREE: C:/MoneyLab-quality-gates-01-v2
EXTERNAL_TOOL_VENV: 모든 MoneyLab 저장소·worktree 밖, 사용자 프로필 디렉터리 아래의 전용 venv(`.venvs/moneylab-quality-gates-01`). TOOL_ENV_SETUP에서 이미 생성됨. 정확한 machine-local 경로는 Gate Authorization과 채팅 증거에만 둔다.
BASE_PYTHON_314: venv 생성에 쓴 CPython 3.14.8 interpreter (CONTRACT_REVIEW에서 확인). 정확한 machine-local 경로는 채팅 증거에만 둔다.
EXTERNAL_Q0_DIR: EXTERNAL_TOOL_VENV 아래 `q0/` (coverage data, mypy cache, pytest log 등 측정 산출물). 저장소 밖.
WORKSPACE_SETUP: LINEAGE_CORRECTION으로 대체(fetch 없음, 이미 local에서 확인한 canonical base에서 branch·worktree 생성, 이 파일을 C1v2로 발행. 저장소 안에 `.venv`나 junction을 만들지 않는다)
INITIAL_GATE: LINEAGE_CORRECTION
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit

## LINEAGE

LINEAGE:
- SUPERSEDED lineage: branch `chore/quality-gates-01`, worktree `C:/MoneyLab-quality-gates-01`, C1 `acd2d19ffc84eaaf2b7be01ae88c81f6020e7e10` (parent = canonical base).
- 대체 사유: 그 C1의 Work Order가 machine-local 사용자 홈 절대 경로를 포함해 `tests/test_repo_hygiene.py::test_no_secrets_or_personal_data_in_addable_files`가 실패했다('user home path'). Work Order는 불변이므로 수정하지 않고 새 lineage로 재발행한다.
- SUPERSEDED lineage 상태: SUPERSEDED_PRE_PUSH. push하지 않는다. 삭제하지 않는다. 다시 쓰지 않는다(amend, reset, rebase 등). merge하지 않는다. 구현에 쓰지 않는다. 증거로 보존한다.
- 이 lineage(v2)는 canonical base에서 직접 시작한다. C1v2는 이 파일 하나만 추가한다.
- 이 파일은 machine-local 사용자 홈 경로와 Windows 계정명을 포함하지 않는다. 외부 경로는 EXTERNAL_TOOL_VENV, BASE_PYTHON_314, EXTERNAL_Q0_DIR 같은 기호 이름으로만 쓴다.

## GATE_SEQUENCE

GATE_SEQUENCE: DISCOVERY_INVENTORY -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> TOOL_ENV_SETUP -> Q0_MEASUREMENT -> LINEAGE_CORRECTION -> SCOPE_DECISION_V2 -> Q0_V2_VERIFICATION -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

DISCOVERY_INVENTORY(PASS), CONTRACT_REVIEW(PASS), WORKSPACE_SETUP, TOOL_ENV_SETUP, Q0_MEASUREMENT(PASS)는 SUPERSEDED lineage에서 끝났다. LINEAGE_CORRECTION이 이 파일을 발행한다.

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 명시적 Gate Authorization으로 한 gate씩만 앞으로 간다. 각 gate의 보고 후 멈춘다.
- rollback은 명시적 승인으로 IMPLEMENTATION까지만 한다.
- COMMIT 이후 수정은 새 commit으로 한다. amend하지 않는다.
- SCOPE_DECISION_V2는 사용자 결정 gate다. 아래 SCOPE_DECISIONS(SD1–SD6)는 이미 확정이다. 조건부 src·tests 수정 경로와 그 밖의 계약 변경은 ACCEPTED ERRATA로 고정한 뒤 IMPLEMENTATION에 들어간다.
- Q0_V2_VERIFICATION이 PASS하기 전에는 IMPLEMENTATION에 들어가지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다. guard deny는 우회하지 않는다.

## GOAL

GOAL: PORTFOLIO-REVIEW-01이 가장 큰 엔지니어링 약점으로 꼽은 자동 품질 gate 부재를 해소한다. 기존 기술 부채를 대량 정리하지 않고, 측정한 기준선 위에서 회귀를 막는 gate를 점진적으로 도입한다.

## BACKGROUND

BACKGROUND:
- DISCOVERY_INVENTORY (GIT_VERIFIABLE, tree c9e99516…): ruff·black·flake8·pylint·mypy·pyright·coverage·pytest-cov·tox·nox·pre-commit 설정과 언급 0. CI는 `ci-tests.yml` 단일 job(`pytest`, windows-latest, Python 3.14.8, root `.venv`, pwsh, `pytest -rsx`).
- 측정 지표 (CLAUDE_REPORTED): src `.py` 128개 약 20.5k줄, tests 약 14.5k줄, `# noqa` 19개(BLE001 6, F401 5, E731 4, B027 3, ARG002 1), `type: ignore` 12개, src 반환 annotation 약 86%(1,002/1,161), `Any` 403회.
- Linux (INFERENCE, 근거 있음): `tests/test_agent_guard.py`의 `test_wrapper_passes_real_decisions_through`와 `test_wrapper_cannot_fix_invalid_json_with_exit_0`는 `.claude/settings.json` hook 명령에 고정된 `${CLAUDE_PROJECT_DIR}/.venv/Scripts/python.exe`를 실행하므로 Linux에서 실패가 예상된다.
- PUBLIC-RELEASE-01의 기록 `LOCAL_TEST_RESULT = NOT PASS`는 그대로 두고 다시 해석하지 않는다.

## USER_DECISIONS

USER_DECISIONS (사용자 확정):
- D1 QUALITY TOOLS: ruff, mypy, coverage.py만 쓴다. black, flake8, pylint, pyright, pytest-cov, tox, nox, pre-commit은 ERRATA 없이 추가하지 않는다.
- D2 LOCAL MEASUREMENT ENVIRONMENT: 모든 MoneyLab 저장소·worktree 밖의 전용 venv(EXTERNAL_TOOL_VENV)를 쓴다. 기존 worktree의 `.venv`를 쓰지 않는다.
- D3 FORMATTING: `ruff format`은 측정만 한다(`--check`). 저장소 전체 서식 변경 금지. formatting은 이 task의 필수 gate가 아니다.
- D4 LINT: 필수 규칙 `E4, E7, E9, F`. 대상 `src`, `tests`. `select = ALL` 금지. I, B, BLE, ARG 등 추가 규칙 계열을 자동으로 켜지 않는다. 기존 위반은 먼저 측정한다. 대량 정리 금지.
- D5 TYPE CHECKING: mypy. 초기 대상 `src`만, tests 제외. strict 금지. 대량 annotation 변경 금지. 측정 후 src 전체 또는 근거 있는 package 부분집합을 gate로 정한다(SD2로 확정). 넓은 오류 범주를 조용히 억제하지 않는다.
- D6 COVERAGE: coverage.py 직접 사용. `python -m coverage run -m pytest -rsx`, `python -m coverage report -m`. 대상 package `moneylab`. branch coverage 켬. 측정만 하고 fail-under 기준값은 두지 않는다. 측정한 기준선을 기록한다.
- D7 LINUX CI: ubuntu-latest에서 실험적 non-blocking 전체 pytest job. 두 wrapper test를 deselect하지 않는다. `.claude/settings.json`을 바꾸지 않는다. wrapper·Linux 구성 문제를 이 task에서 고치지 않는다. required Linux CI는 별도 task로 미룬다.
- D8 WORKFLOW STRUCTURE: 기존 `.github/workflows/ci-tests.yml`을 확장한다. 두 번째 workflow를 만들지 않는다(기술적 blocker가 있으면 사용자 결정). Windows 전체 pytest를 여러 번 돌리지 않는다.
- D9 BASELINE VIOLATION POLICY: 국소 수정은 원칙적으로 허용하되, 선택한 도구가 객관적으로 식별한 위반이고, 동작을 보존하며, 작고 국소적이고, 정확한 파일 경로가 ACCEPTED ERRATA로 ALLOWED_FILES에 추가되고, 기존 test의 의미가 바뀌지 않을 때만 한다. 넓은 정리, 아키텍처 변경, 대량 서식, 상당한 annotation 작업이 필요하면 고치지 않고 좁은 설정·기준선 전략이나 gate 범위 축소를 쓰고 debt를 명시한다.
- D10 PR STRUCTURE: Q1–Q5를 PR 하나로 한다. commit은 단계별로 나눌 수 있다. 관련 없는 작업을 섞지 않는다.
- O1 EXTERNAL VENV PATH: EXTERNAL_TOOL_VENV. TOOL_ENV_SETUP(SUPERSEDED lineage)에서 이미 만들었다. 다시 만들지 않는다. 다른 venv를 만들지 않는다. MoneyLab worktree 안에 `.venv`를 만들지 않는다.
- O2 TYPES-REQUESTS: SD3으로 확정(추가하지 않음).
- O3 LINUX EXPERIMENTAL JOB: job 이름 `pytest-linux-experimental`, job 단위 `continue-on-error: true`. non-blocking 여부는 YAML 의미만으로 주장하지 않고 PR_CI에서 실제 check·merge 동작으로 확인한다.
- O4 BRANCH/WORKTREE: `chore/quality-gates-01-v2`, `C:/MoneyLab-quality-gates-01-v2`. 저장소 안 `.venv` 없음.
- O5 BASE SYNCHRONIZATION: 이 lineage는 fetch하지 않는다(canonical base는 local에서 이미 확인됨). POST_MERGE_AUDIT의 `git fetch origin main` 1회만 예외. pull, `--prune`, `--all`, `remote update` 금지.

## SCOPE_DECISIONS

SCOPE_DECISIONS (사용자 확정, LINEAGE_CORRECTION 승인에 포함):
- SD1 RUFF: 저장소 전체 필수 gate. 규칙 `E4, E7, E9, F`. 대상 `src`, `tests`. Q0 기준선 위반 18건.
  - 진짜 미사용 import 6건(F401): 최소 국소 삭제.
  - F811 fixture-import 12건: fixture import 동작을 보존하고, 필요한 곳에 좁은 inline `noqa`를 쓴다.
  - 전역 F811 억제 금지. green CI만을 위한 넓은 per-file ignore 금지.
  - 조건부 src·tests 경로는 C1v2 이후 ERRATA로 정확한 경로를 승인받아야 한다.
- SD2 MYPY: 초기 필수 gate 범위는 `src/moneylab/execution`, `src/moneylab/pnl`, `src/moneylab/scanner`, `src/moneylab/sizing` (Q0에서 mypy 오류 0인 package).
  - src 전체를 이 task에서 gate로 하지 않는다. Q0의 S2·S3 범위를 초기 필수 gate에 넣지 않는다.
  - 넓은 기준선 기록: 오류 208개, 영향 파일 40개. 넓은 mypy 정리는 미룬다(debt).
  - mypy 호출은 필수 범위 밖에서 import된 module의 오류가 초기 gate를 암묵적인 src 전체 gate로 바꾸지 않도록 설계한다. 이를 넓은 무음 억제로 해결하지 않는다(예: 필수 범위 안의 오류를 숨기는 전역 `ignore_errors`, 전역 `disable_error_code`, 필수 범위 module에 대한 override 금지).
  - 정확한 호출과 설정은 IMPLEMENTATION에서 정하고 보고한다. IMPLEMENTATION과 CI에서 (a) 필수 범위 안의 오류가 실제로 보고되고, (b) 범위 밖 오류가 gate 실패로 나오지 않음을 검증한다.
- SD3 TYPES-REQUESTS: 추가하지 않는다. Q0 근거: 누락 stub·import 오류 0, requests 관련 mypy 오류 0.
- SD4 COVERAGE: 측정 전용. fail-under 기준값 없음. Q0 기준선: statements 12,979, missing 829, branches 3,694, partial branches 466, coverage.py 합산 보고 92%, 계산한 line coverage 약 93.6%. 한계: subprocess에서 실행된 코드는 이 기준선에 충분히 반영되지 않는다.
- SD5 FORMAT: 관찰 전용. Q0: 다시 서식될 파일 171개, 이미 맞는 파일 23개. 저장소 전체 서식을 적용하지 않는다. formatting을 필수 gate로 하지 않는다.
- SD6 PYTEST: 사전등록된 local topology 실패 두 개(`tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through`, `tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0`)를 보존한다. 이 task에서 고치거나 deselect하지 않는다. Q0의 세 번째 실패 `tests/test_repo_hygiene.py::test_no_secrets_or_personal_data_in_addable_files`는 SUPERSEDED C1 Work Order의 사용자 홈 경로만이 원인이었다. C1v2는 그 원인을 없앤다. hygiene test를 약하게 만들지 않는다.

## Q0_HISTORICAL_EVIDENCE

Q0_HISTORICAL_EVIDENCE (CLAUDE_REPORTED, SUPERSEDED pre-push lineage C1 `acd2d19f…`에서 측정. C1v2에서 실행한 것이 아니다):
- 환경: EXTERNAL_TOOL_VENV, Python 3.14.8, ruff 0.17.2, mypy 2.4.0, coverage 7.17.0, pytest 9.1.1. editable install 없음, cache·coverage data는 EXTERNAL_Q0_DIR.
- M1 `ruff check --no-cache --select E4,E7,E9,F src tests`: exit 1, 18건(F811 12, F401 6).
  - F811: `tests/test_backtest_code_state.py` 6, `tests/test_backtest_report.py` 6 (fixture import 줄의 `noqa`가 F401만 지정).
  - F401: `src/moneylab/providers/polymarket/recorder/store.py` 1, `tests/test_backtest_segment.py` 2, `tests/test_backtest_vault.py` 1, `tests/test_research_features_labels.py` 1, `tests/test_upbit_recorder.py` 1.
- M2 `ruff format --no-cache --check src tests`: exit 1, 171 would reformat, 23 already formatted.
- M3 `mypy src`(기본 설정, types-requests 없음): exit 1, 오류 208개, 파일 40개(검사 128개). execution, pnl, scanner, sizing 오류 0. 누락 stub·import 오류 0.
- M4 coverage 아래 pytest: collected 1646, deselected 1, selected 1645, passed 1633, failed 3, skipped 6, xfailed 3, errors 0. failed = KNOWN_ENVIRONMENT_TOPOLOGY 두 test + hygiene test 1(SUPERSEDED C1 원인).
- M5 worktree 불변, cache·산출물 0.

## Q0_V2_VERIFICATION

Q0_V2_VERIFICATION (C1v2 lineage의 좁은 재확인, 측정 전용, 저장소 mutation 0):
- 실행 환경과 cache 위치 규칙은 Q0와 같다(EXTERNAL_TOOL_VENV, EXTERNAL_Q0_DIR 아래 새 하위 경로, `PYTHONPATH=C:/MoneyLab-quality-gates-01-v2/src`).
- 최소 확인 항목:
  - repo hygiene 회귀가 사라짐(`tests/test_repo_hygiene.py::test_no_secrets_or_personal_data_in_addable_files` 통과).
  - ruff 기준선이 Q0와 같음(SD1 규칙, 같은 18건).
  - mypy 필수 범위(SD2 네 package) 기준선이 유효함.
  - pytest가 Q0와 hygiene 회귀 제거만큼만 다름(관련 없는 변경이 없을 때 failed 2, passed 1634, 나머지 수치 동일).
- 금지: 수정, `--fix`, `ruff format`(쓰기), 설치, 새 venv.

## DEPENDENCY_CONTRACT

DEPENDENCY_CONTRACT:
- CLAUDE.md 규칙: dependency를 추가하면 `pyproject.toml`(범위)과 `requirements*.txt`(고정 버전)를 함께 갱신하고 Python 3.14 호환성을 확인한다.
- `pyproject.toml` `[project.optional-dependencies].dev`: ruff, mypy, coverage의 호환 범위를 추가한다. types-requests는 추가하지 않는다(SD3).
- `requirements-dev.txt`: 정확한 고정 버전. 기존 관례대로 필요한 전이 dependency를 `# transitive` 형식으로 포함한다.
- `requirements.txt`(runtime)는 바꾸지 않는다.
- CI 설치 명령은 기존 `pip install -r requirements-dev.txt`를 그대로 쓴다.
- 버전은 추측하지 않는다. TOOL_ENV_SETUP에서 BASE_PYTHON_314(3.14.8) 기반 EXTERNAL_TOOL_VENV에 실제로 설치·실행해 확인한 버전만 고정 후보로 쓴다(`pip freeze` 증거는 채팅 보고에 있다).

## TOOL_ENV_SETUP

TOOL_ENV_SETUP (SUPERSEDED lineage에서 완료, 이 lineage에서는 다시 하지 않음):
- EXTERNAL_TOOL_VENV는 이미 있다. 이 lineage에서 추가 설치, 다른 venv 생성·변경, types-requests 설치를 하지 않는다.
- 추가 설치가 필요해지면 멈추고 사용자 결정과 ERRATA를 받는다.

## SCOPE_DECISION_V2

SCOPE_DECISION_V2 (사용자 결정):
- SD1–SD6은 확정이다. 이 gate는 조건부 src·tests 수정의 정확한 경로·위반 code·수정 방식과, 그 밖의 계약 변경을 ERRATA로 제안하고 사용자가 ACCEPT한 경우에만 Ce로 commit한다.
- 조건부 경로 후보(Q0 근거, 아직 승인 아님): `src/moneylab/providers/polymarket/recorder/store.py`, `tests/test_backtest_segment.py`, `tests/test_backtest_vault.py`, `tests/test_research_features_labels.py`, `tests/test_upbit_recorder.py`, `tests/test_backtest_code_state.py`, `tests/test_backtest_report.py`.

## ALLOWED_FILES

ALLOWED_FILES (LINEAGE_CORRECTION, C1v2 전용):
- A docs/tasks/QUALITY-GATES-01/WORK_ORDER.md

ALLOWED_FILES (ERRATA, Ce 전용):
- A docs/tasks/QUALITY-GATES-01/ERRATA-<NNN>.md (사용자가 ACCEPT한 경우만)

ALLOWED_FILES (IMPLEMENTATION, Ci):
- M pyproject.toml (`[project.optional-dependencies].dev`, `[tool.ruff]`, `[tool.mypy]`, `[tool.coverage.*]`만. `[build-system]`, runtime dependencies, `[project]`의 다른 필드, `[tool.pytest.ini_options]`는 바꾸지 않는다)
- M requirements-dev.txt
- M .github/workflows/ci-tests.yml
- 조건부: ACCEPTED ERRATA가 정확한 경로로 지정한 `src/`·`tests/` 파일만. wildcard 권한 없음(`src/**`, `tests/**` 변경 권한을 주지 않는다).

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/QUALITY-GATES-01/** (C1v2·Ce 최초 생성만 예외)
- 기존 docs/tasks/** (다른 task, PUBLIC-RELEASE-01 증거 포함)
- CLAUDE.md
- .claude/**
- README.md, LICENSE
- requirements.txt
- src/**, tests/** (ACCEPTED ERRATA가 정확한 경로로 지정한 파일 제외)
- configs/**, data/**
- docs/의 설계·사전등록·evidence 문서
- .gitignore, .gitattributes
- env 계열 파일 전부
- 이 task 이외의 .github/** (ci-tests.yml만 예외)

PROTECTED_REFS (SUPERSEDED lineage, 읽기 전용 증거):
- branch `chore/quality-gates-01` (`acd2d19ffc84eaaf2b7be01ae88c81f6020e7e10`), worktree `C:/MoneyLab-quality-gates-01`

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가)

## CI_TOPOLOGY

CI_TOPOLOGY (`ci-tests.yml` 확장):
- job `pytest` (windows-latest, required, 이름 유지): checkout, setup-python 3.14.8, root `.venv`, `pip install -r requirements-dev.txt`, `pip install -e . --no-deps`, `ruff check src tests`, `mypy <SD2 범위, IMPLEMENTATION에서 확정한 호출>`, `python -m coverage run -m pytest -rsx`, `python -m coverage report -m`. 각 명령은 한 step에 하나(pwsh 종료 코드 규칙).
- ruff와 mypy는 OS 독립이므로 Windows job에서 한 번만 실행한다.
- coverage 설정(`source = ["moneylab"]`, `branch = true`)은 `pyproject.toml` `[tool.coverage.run]`에 둔다. fail-under 없음.
- pytest 선택은 `pyproject` `addopts = "-m 'not network'"`로 유지하고 `-rsx`를 유지한다.
- job `pytest-linux-experimental` (ubuntu-latest, `continue-on-error: true`): bash, `.venv/bin/python`, 같은 설치 단계 후 `python -m pytest -rsx`만 실행. coverage·lint·type 없음. deselect 없음.
- 기존 trigger와 `permissions: contents: read`, action SHA 고정을 유지한다.

## GATE_STATUSES

GATE_STATUSES:
- 필수: RUFF_GATE (CI exit 0), MYPY_GATE (SD2 범위 exit 0), WINDOWS_PYTEST (coverage 아래 실행, failed 0, errors 0, 수치 유지), PACKAGING_INSTALLABILITY (CI editable install 성공)
- 관찰: COVERAGE_MEASUREMENT (보고됨. 값만 기록하고 좋다·나쁘다 평가하지 않는다), LINUX_EXPERIMENTAL, ruff format 측정(Q0)
- LINUX_EXPERIMENTAL 값:
  - PASS
  - EXPECTED_FAILURE: failed가 정확히 `tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through`와 `tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0`뿐이고, 두 실패 모두 `.venv/Scripts/python.exe` 경로 부재가 원인이며, errors 0, collection 오류 0일 때만
  - UNEXPECTED_FAILURE: 그 밖의 모든 failure·error. 별도 분류하고 사용자가 판단한다
- Linux에서 Windows 전용 skip(junction, 8.3 이름, SIGBREAK) 수가 달라지는 것은 예상된 차이로 기록한다.

## TASK_PASS_SEMANTICS

TASK_PASS_SEMANTICS:
- task PASS: RUFF_GATE, MYPY_GATE, WINDOWS_PYTEST, PACKAGING_INSTALLABILITY가 모두 통과하고, COVERAGE_MEASUREMENT가 보고되고, LINUX_EXPERIMENTAL이 PASS 또는 EXPECTED_FAILURE이고, PR_CI에서 Linux job 실패가 실제로 merge를 막지 않음이 확인되고, 범위 위반이 없을 때.
- WINDOWS_PYTEST 기준 수치(base PR #27 CI): collected 1646, deselected 1, selected 1645, passed 1636, skipped 6, xfailed 3, failed 0, errors 0. 이 task는 test 의미를 바꾸지 않으므로 같은 수치를 기대한다. 다르면 원인을 보고한다.
- Linux job이 실제로 merge를 막는 것으로 관찰되면 PR_CI = BLOCKED이고 사용자 결정을 받는다.

## TEST_GATES

TEST_GATES:
- local 실행 환경: EXTERNAL_TOOL_VENV. `PYTHONPATH=C:/MoneyLab-quality-gates-01-v2/src`, `PYTHONDONTWRITEBYTECODE=1`, `-B`, `-p no:cacheprovider`. 실행 전 `moneylab.__file__`이 이 worktree src 아래인지 확인.
- canonical local full suite: 작업 디렉터리 `C:/MoneyLab-quality-gates-01-v2`에서 `python -B -m coverage run -m pytest -rsx -p no:cacheprovider` (COVERAGE_FILE은 EXTERNAL_Q0_DIR 등 저장소 밖), `python -m coverage report -m`. collected·selected 줄과 요약을 모두 캡처한다.
- `ruff check src tests`, `mypy <SD2 범위 호출>`이 local에서 exit 0.
- `git diff --check` clean; 변경 파일 집합 = ALLOWED_FILES.
- worktree에 cache·coverage data·build 산출물이 남지 않을 것.

## KNOWN_ENVIRONMENT_TOPOLOGY

KNOWN_ENVIRONMENT_TOPOLOGY:
- `tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through`, `tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0`는 `CLAUDE_PROJECT_DIR=<repository root>`의 `.venv/Scripts/python.exe`를 실행한다. 이 Work Order는 worktree 안 `.venv`를 금지하므로 local에서 실패가 예상된다. Linux CI에서도 같은 경로 고정 때문에 실패가 예상된다.
- 이 failure를 PASS로 표현하지 않는다. LOCAL_TEST_RESULT는 실제 결과 그대로 기록한다.

## E2E_GATES

E2E_GATES (CLEAN_COMMIT_E2E):
- clean implementation commit에서 TEST_GATES를 실행한다.
- gate-level acceptance는 다음을 모두 만족할 때만 가능하다(local test를 PASS로 재분류하는 규칙이 아니다): local failed가 정확히 KNOWN_ENVIRONMENT_TOPOLOGY의 두 test, 두 failure 모두 `C:/MoneyLab-quality-gates-01-v2/.venv/Scripts/python.exe` 부재가 원인, 그 외 failed 0, errors 0, collection 오류 0, 모든 수치 기록, ruff·mypy local exit 0.
- 보고에 `LOCAL_TEST_RESULT: <실제 결과>, not PASS`와 `DEFERRED_STATUS: ENVIRONMENT_DEPENDENT_DEFERRED_TO_PR_CI`를 쓴다.

## PR_CI_CONDITIONS

PR_CI_CONDITIONS:
- 판정 대상: MERGE 시점 PR head commit에 대한 `pull_request` event의 `ci-tests` run. job `pytest`가 필수, job `pytest-linux-experimental`은 관찰.
- canonical CI test 명령은 `python -m coverage run -m pytest -rsx`이다. pytest 요약 줄은 coverage 아래에서도 log에 나온다.
- 두 wrapper test의 Windows 해소: 직접 PASSED 줄이 있으면 DIRECT_CI_EVIDENCE, 없으면 아래 E1–E9를 모두 확인할 때만 ELIMINATIVE_CI_EVIDENCE:
  - E1. job `pytest` success, pytest 요약 failed 0, errors 0.
  - E2. collected, selected, deselected, passed, skipped, xfailed, xpassed, failed, errors가 log에서 확인되고 selected = passed + skipped + xfailed + xpassed + failed + errors.
  - E3. 해당 test가 평가 대상 commit의 `testpaths`에 존재(소스 확인).
  - E4. SKIPPED 목록에 없음.
  - E5. XFAIL·XPASS 목록에 없음.
  - E6. deselection 대상 marker 없음(decorator, class, module `pytestmark`).
  - E7. 다른 selection exclusion 없음: `addopts`·`testpaths`, CI 명령 추가 인자, conftest collection hook. `[tool.pytest.ini_options]`가 base와 같음.
  - E8. FAILED·ERROR 목록에 없음.
  - E9 (보조). local CLEAN_COMMIT_E2E 대비 CI passed가 정확히 2 많고 skipped·deselected·xfailed가 같음.
- 추가 확인: RUFF_GATE·MYPY_GATE step success, coverage report 출력, PACKAGING_INSTALLABILITY, LINUX_EXPERIMENTAL 분류, Linux job 실패 시 PR mergeStateStatus와 check 상태로 non-blocking 여부를 실제 확인.
- 하나라도 확인할 수 없으면 PR_CI = BLOCKED. 필수 gate 실패는 PR_CI = FAIL.

## ROLLBACK_BOUNDARIES

ROLLBACK_BOUNDARIES (commit 단계, revert 단위):
- Q1 설정·dependency (`pyproject.toml`, `requirements-dev.txt`)
- Q2 ruff 단계 (`ci-tests.yml`)
- Q3 mypy 단계 (`ci-tests.yml`)
- Q4 coverage 실행 (`ci-tests.yml`)
- Q5 Linux 실험 job (`ci-tests.yml`)
- 조건부 src·tests 국소 수정은 별도 commit
- commit 구성은 IMPLEMENTATION 보고에서 확정한다. 하나의 PR. amend·force push 금지.

## GUARD_PROVENANCE

GUARD_PROVENANCE:
- PREVIOUS_GUARD_DENY = clock (DISCOVERY_INVENTORY, Windows 전용 패턴 검색)
- RETRY_OF_DENIED_COMMAND = NO
- BYPASS_ATTEMPT = NO
- NEW_METHOD = LINUX_COMPATIBILITY_AUDIT_V2
- NEW_METHOD_AUTHORIZED_BY_USER = YES
- SUPERSEDED lineage의 이후 gate: WORKSPACE_SETUP에서 C1 commit 확인 요구 1회(사용자 승인), TOOL_ENV_SETUP·Q0_MEASUREMENT에서 deny 0.
- 이후 gate에서 guard deny가 나면 즉시 멈춘다. 재작성·분할·인코딩·다른 도구 경유 금지. ask면 정확한 명령과 확인 요청을 사용자에게 보인다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- LINEAGE_CORRECTION: read-only 사전 확인, canonical base에서 `chore/quality-gates-01-v2` branch·worktree 생성, 이 파일 최초 생성과 C1v2 commit, SUPERSEDED lineage read-only 확인
- SCOPE_DECISION_V2: 보고, 사용자 결정, ACCEPTED ERRATA 생성과 Ce commit
- Q0_V2_VERIFICATION: 위 Q0_V2_VERIFICATION 절의 read-only 측정과 보고만
- IMPLEMENTATION: ALLOWED_FILES(IMPLEMENTATION) 수정, TEST_GATES 실행
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, 승인된 commit 구성
- CLEAN_COMMIT_E2E: TEST_GATES와 E2E_GATES만
- PUSH: `git push -u origin chore/quality-gates-01-v2` 1회
- PR_CI: PR 하나 생성(base main), CI 결과 read-only 확인
- MERGE: `gh pr merge <n> --merge` 1회(squash·rebase·branch 삭제 없음)
- POST_MERGE_AUDIT: read-only 확인(필요 시 `git fetch origin main` 1회)
- COMPLETE: 최종 보고만

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA 수정
- SUPERSEDED lineage(`chore/quality-gates-01`, `C:/MoneyLab-quality-gates-01`)의 push, 삭제, 수정, merge, 구현 사용
- 이 Work Order와 ERRATA에 machine-local 사용자 홈 경로나 Windows 계정명을 쓰는 것
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull, POST_MERGE_AUDIT 밖의 fetch
- hooks·settings·`.claude` 변경, guard 우회, 이전에 차단된 명령의 재시도나 재구성
- MoneyLab worktree 안 `.venv`·junction 생성, 새 venv 생성, 다른 venv 변경
- ruff `--fix`, `ruff format`(쓰기), 저장소 전체 서식, 자동 annotation
- coverage fail-under 기준값
- 두 wrapper test의 deselect, Linux 문제를 감추는 설정, hygiene test 약화
- GitHub 설정·visibility·metadata·branch protection 변경
- memory·scratchpad 변경
- 다른 branch·worktree·untracked·ignored·reference 산출물 정리

## OUT_OF_SCOPE

OUT_OF_SCOPE:
- 큰 module 분할, 아키텍처 변경
- 통계 방법 변경, BT4, 연구 재실행
- README 재설계, demo 구현
- live execution, Polymarket
- 저장소 전체 서식, strict typing, tests typing
- src 전체 mypy gate, Q0 S2·S3 범위, 넓은 mypy 정리
- coverage 기준값
- required Linux CI, Linux wrapper test 대응
- branch·worktree 정리(SUPERSEDED lineage 포함), history rewrite
- governance 확장

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1v2·Ce·Ci·merge SHA·tree·parent, 파일 sha256, commit 파일 집합, SUPERSEDED branch가 `acd2d19f…`를 가리킴
- CLAUDE_REPORTED: 도구 버전과 `pip freeze`, Q0 측정값(SUPERSEDED lineage), Q0_V2_VERIFICATION 측정값, local pytest·coverage 결과, E1–E9 결합 판정
- INDEPENDENT: GitHub CI run conclusion과 log 수치·목록, check·merge 상태, 사용자 확인

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, ACCEPTED_ERRATA
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- gate 상태(RUFF_GATE, MYPY_GATE, COVERAGE_MEASUREMENT, WINDOWS_PYTEST, LINUX_EXPERIMENTAL, PACKAGING_INSTALLABILITY)
- 증거 등급, guard 결과, mutation 수, PROPOSED_ERRATA, DEVIATIONS
- <GATE> 판정과 다음 gate

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, Work Order sha256 불일치
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- SUPERSEDED lineage의 branch가 `acd2d19f…`가 아니거나 worktree가 clean이 아님
- guard deny, 권한 창 거절
- 도구 실행 실패, Python 3.14.8 비호환
- 테스트 실패·에러(KNOWN_ENVIRONMENT_TOPOLOGY 두 test 제외, E2E_GATES 규칙 적용)
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일, worktree에 남은 cache·build 산출물
- Linux job이 실제로 merge를 막음
