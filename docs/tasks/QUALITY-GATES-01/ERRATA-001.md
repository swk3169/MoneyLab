# ERRATA-001: QUALITY-GATES-01 — ruff 국소 수정 경로와 mypy 범위·호출 확정

이 파일은 불변이다. 발행(Ce1) 후 수정하지 않는다.

## Metadata

ERRATA_ID: QUALITY-GATES-01/ERRATA-001
TASK_ID: QUALITY-GATES-01
STATUS: ACCEPTED
ACCEPTED_IN_GATE: SCOPE_DECISION_V2 (사용자 Gate Authorization)
APPLIES_TO_WORK_ORDER: docs/tasks/QUALITY-GATES-01/WORK_ORDER.md @ C1v2 `5f7bb60bc1d1ac547fc94f25c6c2fcde09d2caa9`
WORK_ORDER_SHA256: 5581c56a91b5fd0e98e8564a7713516906a5916d4da7c35a0d7079273d4a9f5a
LINEAGE: v2 (`chore/quality-gates-01-v2`). SUPERSEDED lineage `chore/quality-gates-01` (`acd2d19f…`)는 그대로 보존하고 쓰지 않는다.

## REASON

REASON:
- Q0_HISTORICAL_EVIDENCE(CLAUDE_REPORTED, SUPERSEDED lineage)의 ruff 기준선 18건은 7개 파일에 있고, 모두 동작을 보존하는 국소 수정으로 해소할 수 있다.
- C1v2는 `src/**`, `tests/**`를 PROTECTED로 두고 정확한 경로의 ERRATA만 예외로 허용한다. 이 ERRATA가 그 7개 경로를 정확히 추가한다.
- SD2의 mypy 호출 설계를 SCOPE_DECISION_V2에서 read-only로 정했으므로 여기에 고정한다.

## ALLOWED_FILES_ADDITIONS

ALLOWED_FILES (IMPLEMENTATION, Ci, 조건부 경로 확정). 이 7개 경로만 추가한다:

| # | path | Q0 위반 | 허용 수정 |
|---|---|---|---|
| 1 | `src/moneylab/providers/polymarket/recorder/store.py` | F401 1건 (`parse_timestamp`, import 목록 안) | 그 미사용 이름 하나만 import 목록에서 삭제 |
| 2 | `tests/test_backtest_segment.py` | F401 2건 (`timedelta`, `bars_sha256`) | 그 두 미사용 이름만 각 import 줄에서 삭제 |
| 3 | `tests/test_backtest_vault.py` | F401 1건 (`inspect`) | 그 미사용 import 하나만 삭제 |
| 4 | `tests/test_research_features_labels.py` | F401 1건 (`trade`) | 그 미사용 이름 하나만 import 줄에서 삭제 |
| 5 | `tests/test_upbit_recorder.py` | F401 1건 (`Path`) | 그 미사용 import 하나만 삭제 |
| 6 | `tests/test_backtest_code_state.py` | F811 6건 (fixture `bars` import 줄) | fixture import 줄의 `# noqa: F401`을 `# noqa: F401, F811`로 바꿈. 기존 설명 주석은 유지 |
| 7 | `tests/test_backtest_report.py` | F811 6건 (fixture `bars` import 줄) | fixture import 줄의 `# noqa: F401`을 `# noqa: F401, F811`로 바꿈. 기존 설명 주석은 유지 |

RUFF_REMEDIATION_RULES:
- `noqa` 추가는 F811이 필요한 fixture import 줄에만 한다. 다른 줄에 `noqa`를 넣지 않는다.
- 전역 F811 억제(`ignore`, `extend-ignore`), F811 per-file ignore, 그 밖의 넓은 per-file ignore를 쓰지 않는다.
- fixture import 방식과 fixture 동작을 바꾸지 않는다. test를 refactor하지 않는다. runtime 동작을 바꾸지 않는다.
- 관련 없는 줄의 서식 변경, 관련 없는 lint 정리, `ruff --fix`, `ruff format`(쓰기)를 하지 않는다.
- 수정 후 그 7개 파일의 diff는 위 표의 변경만 포함해야 한다. Q0_V2_VERIFICATION이 기준선 18건과 다른 위반을 찾으면 IMPLEMENTATION 전에 멈추고 보고한다.

WILDCARD_DENIAL: `src/**`, `tests/**`에 대한 wildcard 변경 권한은 없다. 위 7개 외의 `src/`·`tests/` 파일은 계속 PROTECTED다. mypy를 위한 source 수정 권한도 없다(새 ACCEPTED ERRATA가 정확한 경로를 추가하기 전까지).

## MYPY_SCOPE_AND_INVOCATION

MYPY_REQUIRED_SCOPE (SD2 확정): 정확히 `src/moneylab/execution`, `src/moneylab/pnl`, `src/moneylab/scanner`, `src/moneylab/sizing`. src 전체, Q0 S2·S3, tests는 gate하지 않는다. 넓은 기준선(오류 208개, 파일 40개)은 debt로 기록한다.

MYPY_INVOCATION (확정):
- `pyproject.toml` `[tool.mypy]`:
  - `files = ["src/moneylab/execution", "src/moneylab/pnl", "src/moneylab/scanner", "src/moneylab/sizing"]`
  - `follow_imports = "silent"`
- CI와 local 명령: 인자 없는 `python -m mypy`(위 설정을 읽음). 각 명령은 한 step에 하나.
- 그 밖의 `[tool.mypy]` 키, `[[tool.mypy.overrides]]`는 추가하지 않는다.

MYPY_FORBIDDEN:
- `follow_imports = "skip"`(import한 type을 Any로 바꿔 선택 package 안의 오류를 숨길 수 있다)
- `ignore_missing_imports`(전역·module별), `ignore_errors`, `disable_error_code`, 선택 package를 대상으로 하는 override
- 선택 package 안의 `# type: ignore` 추가
- strict 계열 옵션 추가

ERROR_CLASSES (구분):
- selected-package errors: 위 네 경로의 파일은 mypy source로 완전히 검사되고 오류가 보고된다. gate 실패다.
- imported-module errors: 선택 package가 import해서 따라간 범위 밖 module(`core`, `domain`, `providers.base`, `risk`, 그리고 transitive로 `analytics`, `strategy` 등)은 type 정보를 위해 분석되지만, 그 module 안의 오류는 `silent`로 보고하지 않는다. 넓은 기준선 debt로 남는다.
- missing-import/stub errors: `ignore_missing_imports`를 쓰지 않으므로 선택 package 안의 import-not-found나 누락 stub 오류는 gate 실패로 보고된다. 범위 밖 module 안의 같은 오류는 imported-module errors로 취급한다. Q0 기준 0건.

MYPY_DESIGN_EVIDENCE (CLAUDE_REPORTED, SCOPE_DECISION_V2, C1v2 worktree, mypy 2.4.0, `--cache-dir=nul`, 설정 변경 없음):
- A. 기본(`follow_imports=normal`)으로 네 경로 실행: exit 1, 오류 14개, 파일 6개, 모두 범위 밖(`analytics/metrics.py`, `domain/models.py`, `risk/kill_switch.py`, `strategy/mispricing.py`, `strategy/market_making.py`, `core/http.py`). 기본 호출은 사실상 범위 밖 gate가 된다.
- B. `--follow-imports=silent`로 네 경로 실행: exit 0, `no issues found in 9 source files`. 검사 대상(source)은 네 package의 9개 파일이다. verbose log로 범위 밖 module도 분석됨을 확인했다(Any로 바뀌지 않음).
- C. 대조 실험: `--follow-imports=silent`로 `src/moneylab/risk`를 source로 실행하면 `risk/kill_switch.py:99` 오류가 보고된다(exit 1). `silent`는 source로 넘긴 module의 오류를 숨기지 않는다.
- 선택 package 안의 기존 `type: ignore`·`noqa`·`mypy:` 주석: 0건.
- 영향: `files`·`follow_imports` 설정이 있어도 `mypy src`처럼 모든 파일을 명시적으로 넘기면 전부 source로 검사되므로 넓은 기준선 재측정이 가능하다(INFERENCE, mypy 의미에 근거).

MYPY_VALIDATION:
- Q0_V2_VERIFICATION: 설정 전이므로 같은 의미의 CLI(`--follow-imports=silent` + 네 경로, 저장소 밖 cache 또는 `nul`)로 오류 0, source 9개를 확인한다.
- IMPLEMENTATION·CLEAN_COMMIT_E2E: 인자 없는 `python -m mypy`가 같은 결과(exit 0, 9 source files)를 내는지 확인한다.
- PR_CI: CI log에서 MYPY_GATE step success와 `9 source files`(또는 그 시점 실제 수와 원인)를 확인한다.

## OTHER_SCOPE_CONFIRMATIONS

- SD3 TYPES-REQUESTS: NOT_REQUIRED. 추가하지 않는다. Q0 근거: 누락 stub·import 오류 0, requests 관련 오류 0.
- SD4 COVERAGE: 관찰 전용. fail-under 없음, coverage 비율 gate 없음. 92%가 충분하다·부족하다는 주장을 하지 않는다. 기준선 statements 12,979, missing 829, branches 3,694, partial 466, 합산 92%, line 약 93.6%. subprocess에서 실행된 코드는 반영되지 않는 한계를 유지한다.
- SD5 FORMAT: `ruff format`은 관찰 전용(171 would reformat, 23 already formatted). 서식 변경 없음. 이 task에 format CI 요구 없음.
- SD6 SEQUENCE: `SCOPE_DECISION_V2 -> Q0_V2_VERIFICATION -> IMPLEMENTATION`를 확정한다. Q0_V2_VERIFICATION은 측정 전용이고 IMPLEMENTATION보다 먼저 한다.

## Q0_V2_VERIFICATION_ADDITIONS

C1v2 Q0_V2_VERIFICATION 절에 다음을 더한다(최소 확인 항목):
1. C1v2가 repo hygiene 실패를 더 이상 일으키지 않음.
2. ruff 기준선 18건 유지. 다르면 저장소 상태 차이로 설명한다.
3. SD2 네 package가 위 MYPY_INVOCATION과 같은 의미의 호출에서 오류 0.
4. 전체 pytest가 SUPERSEDED Q0와 Work Order hygiene 회귀 제거만큼만 다름(관련 없는 발견 없음).
5. 두 agent-guard wrapper 실패가 사전등록된 `.venv/Scripts/python.exe` 부재 원인으로 나면 KNOWN_ENVIRONMENT_TOPOLOGY로 분류.
6. coverage 기준선이 관찰 전용이고 과거 측정과 실질적으로 일치.
7. 저장소가 clean하고 변경 없음.
- 이 gate에서는 아무것도 고치지 않는다.

## GUARD_PROVENANCE_ADDITIONS

- LINEAGE_CORRECTION_GUARD_DENY = 0
- LINEAGE_CORRECTION_GUARD_ASK = 1
- LINEAGE_CORRECTION_GUARD_ASK_CONTEXT = C1v2 git commit
- LINEAGE_CORRECTION_GUARD_ASK_USER_APPROVED = YES (Claude는 UI 확인 창을 직접 관찰하지 못했다. 사용자가 관찰하고 승인했다)

## PRESERVED

이 ERRATA가 명시적으로 바꾸지 않은 C1v2의 모든 제약(PROTECTED_FILES, FORBIDDEN_ACTIONS, CI_TOPOLOGY, GATE_STATUSES, TASK_PASS_SEMANTICS, KNOWN_ENVIRONMENT_TOPOLOGY, E2E_GATES, PR_CI_CONDITIONS, SUPERSEDED lineage 보호)은 그대로 유지한다. 이 ERRATA와 이후 ERRATA에는 machine-local 사용자 홈 경로나 Windows 계정명을 쓰지 않는다.
