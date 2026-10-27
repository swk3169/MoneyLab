# ERRATA: PORTFOLIO-DEMO-01 ERRATA-001 — demo 결정성 계약 정정

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: PORTFOLIO-DEMO-01-ERRATA-001
TASK_ID: PORTFOLIO-DEMO-01
TARGET_WORK_ORDER: docs/tasks/PORTFOLIO-DEMO-01/WORK_ORDER.md @ C1 `638b90399e9156ecd43272b23ae718913bec1c50` (sha256 42814b35ce127482b9935359fc9f010e2bd7ef8a1adf4cdf83c0d21b05bbca82)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자, ERRATA-001_SCOPE_DECISION gate (2026-10-27)
ACCEPTED_IN_GATE: ERRATA-001_SCOPE_DECISION
DECISION: PROPOSED_ERRATA E-A 채택. E-B(정규화 result hash) 이 task에서 기각. E-C(CLI fixture 경로의 시각 고정을 위한 src 변경) 보류, 별도 task는 지금 만들지 않음.

## FINDING

FINDING (Q0_MEASUREMENT, verdict BLOCKED):
- 기존 공개 CLI 경로로 같은 고정 설정을 두 번 독립 실행했을 때 `result_sha256`이 달랐다(MEASURED):
  - run A: `69e46159d96d79f62a0576becef2f7870de5e2797524a7ffd1665887dd931c91`
  - run B: `bb705110db7577bb4bfec499ba8f599a0be441e4f29fa7430f3472d28cfa44d8`
- 두 `result.json`의 차이는 `/provenance/day/description`과 `/provenance/hour/description` 두 곳뿐이었다(MEASURED). 이 값은 `"<pull_id> via <bars dir name> (SYNTHETIC / NOT_EVIDENCE)"` 형태이고(`src/moneylab/backtest/bars_io.py`), pull·bars 디렉터리 이름은 실행 시각 UTC stamp를 포함한다(`src/moneylab/providers/upbit/candle_store.py`의 `pull_id`, CLI `candles-pull` fixture 경로는 `pull_to_store`에 `utcnow`를 넘기지 않는다) (CODE_INSPECTED).
- 즉 시각을 담은 provenance가 기존 설계상 구조적으로 `result.json`에 포함된다. 기존 result integrity hash는 시각을 담은 provenance를 포함하므로 cross-run 결정적 식별자가 아니다. 이것은 결함이 아니라 현재 CLI 의미다.
- 같은 두 실행에서 실질 산출물은 결정적이었다(MEASURED): signals, trades, metrics, daily, config가 같았고, run `SHA256SUMS.txt`의 `daily.jsonl`, `metrics.json`, `trades.jsonl`, `orders.jsonl` hash가 같았다. day·hour bar hash는 기존 golden과 정확히 같았다. verify 9개 check(files, inputs, identity, settings, code, reproducibility, accounting, boundary, engine_self_check) 모두 True, report-verify OK.
- 따라서 Work Order의 "result_sha256 자체가 독립 동등 실행 사이에 같아야 한다"는 요구는 현재 CLI 의미에 대해 성립하지 않는다(INVALID).

## CHANGED_FIELDS

CHANGED_FIELDS:
- GOLDEN_HASH_POLICY (result_sha256 부분만)
- DESIGN_CONTRACT.D6 DEMO_SUMMARY (summary 내용 항목 추가·구분만)
- TEST_GATES (result_sha256 확인 방식만)
- STOP_CONDITIONS (result_sha256 cross-run 불일치 조항만)
- PYTHON_ENVIRONMENT (결정 기록 추가)
- GATE_SEQUENCE (TOOL_ENV_SETUP 삽입, 아래 NEXT_GATES)

SUPERSEDED (이 세 요구만 대체한다. 그 밖의 Work Order 요구는 모두 유지한다):
1. result_sha256이 두 번의 독립 동등 실행에서 같아야 한다 (GOLDEN_HASH_POLICY: "독립된 두 번째 동등 실행을 하고, 같은 result_sha256을 요구한 뒤").
2. result_sha256을 cross-run golden으로 `tests/test_examples_demo.py`에 고정한다 (GOLDEN_HASH_POLICY: "관측한 값을 `tests/test_examples_demo.py`에 고정한다", TEST_GATES: "승인된 측정 후 고정한 result_sha256", E2E_GATES: "result_sha256 = IMPLEMENTATION에서 고정한 값").
3. cross-run result_sha256 불일치 자체가 STOP 조건이다 (STOP_CONDITIONS: "두 번의 동등 실행에서 result_sha256이 다름").

## RATIONALE

RATIONALE: Q0가 cross-run result_sha256 동일성 가정이 기존 공개 CLI 경로에서 거짓임을 측정으로 보였다. 차이는 시각을 담은 provenance 설명에서만 나왔고, 실질 run 산출물과 bar hash는 결정적이었다. 기존 산출물(`SHA256SUMS.txt`)의 hash를 그대로 golden으로 쓰면 새 hash 알고리즘, 정규화 계층, provenance 제거 없이 결정성을 확인할 수 있다(E-A). src는 PROTECTED이므로 E-C는 이 task 범위 밖이다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:

A. BAR GOLDENS (변경 없음, 재확인):
- day bars_sha256: `d6a40221a2c3b810d468b0f522cc2a1ef2305315f43864e0b37e7410251ec561` (199 bars)
- hour bars_sha256: `39ad26cbb0cedfe3a647f6dc01e31d19f8bec58a9d69f460918516bad972e412` (4,809 bars)

B. DETERMINISTIC RUN ARTIFACT GOLDENS (이 demo 설정의 cross-run 결정적 산출물 golden. run 디렉터리 `SHA256SUMS.txt`의 값):
- `daily.jsonl`: `77211e81cc44b32605b0d4b1eccf02ac4a8bbb0d06dfcf9f7272ba20521578ac`
- `metrics.json`: `bc26e3f19fd7c48381bff995c74b1ee5a1fe3085bb92e16b40044fd29de971c6`
- `trades.jsonl`: `066b65f86992b11a0538c0c978088b84eae70b406c9351028f987e791c658bbb`
- `orders.jsonl`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- 출처: Q0_MEASUREMENT, C1 clean checkout(PINNED), 독립 실행 2회(run A, run B)에서 같음.
- IMPLEMENTATION의 CLI demo 경로에서 이 네 값 중 하나라도 다르면 멈춘다. golden을 갱신하거나 재해석하지 않는다.

C. RESULT_SHA256:
- result_sha256은 per-run integrity 식별자로 남는다.
- demo는 이 값을 반드시 표시한다.
- demo·test는 기존 pipeline이 기록한 값이 생성된 `result.json`과 기존 `SHA256SUMS.txt` 의미와 내부적으로 일치하는지 확인한다(run manifest의 `result_sha256` = `SHA256SUMS.txt`의 `result.json` 항목 = `result.json` 바이트의 SHA-256).
- result_sha256을 고정된 cross-run golden과 비교하지 않는다.
- result_sha256을 cross-run 결정적이라고 설명하지 않는다.

D. EXISTING VERIFY CONTRACT:
- 기존 backtest verification이 기준이다.
- demo·test는 해당하는 code 외 check가 모두 통과할 것을 요구한다.
- PINNED이면 code check도 통과해야 한다.
- 기존 reproducibility check는 True여야 한다.
- `verify_run` 의미를 우회하거나 재정의하지 않는다.

E. REPORT:
- 기존 report·report-verify 정책은 바뀌지 않는다.
- PINNED: report 실행, report-verify 통과 필수.
- UNPINNED: report 우회 없음, `PARTIAL_CODE_STATE_UNPINNED` 동작(exit 4) 그대로.

F. GOLDEN_HASH_POLICY의 IMPLEMENTATION 절차 (대체 후 전체):
- CLI demo 경로를 실행한다.
- day·hour bar hash를 A와 비교한다. 다르면 멈춘다.
- 일치하면 네 run 산출물 hash를 B와 비교한다. 다르면 멈춘다.
- result_sha256은 C의 내부 일치만 확인하고, 측정값은 IMPLEMENTATION 보고에 per-run 값으로 기록한다.
- WORK_ORDER.md와 이 ERRATA는 수정하지 않는다.

G. DESIGN_CONTRACT.D6 DEMO_SUMMARY (추가·구분):
- `demo_summary.json`은 다음을 담을 수 있다:
  - `per_run_integrity`: result_sha256 (per-run integrity 값)
  - `cross_run_deterministic_artifacts`: 네 산출물 이름과 관측 SHA-256 값 (그리고 day·hour bars_sha256)
- summary는 `per_run_integrity`와 `cross_run_deterministic_artifacts`를 분명히 구분한다.
- 새 정규화 result hash를 만들지 않는다.
- schema 식별자는 `moneylab.demo.synthetic_backtest/1` 그대로다. schema가 아직 구현·공개되지 않았으므로 version을 올리지 않는다.
- 그 밖의 D6 조항(절대 경로 금지, workdir 기준 상대 경로, 과설계 금지)은 유지한다.

H. TEST_GATES (result_sha256 관련 대체 후):
- `tests/test_examples_demo.py`는 고정된 result_sha256을 assert하지 않는다.
- 대신 다음을 assert한다:
  - day bar golden 정확히 일치
  - hour bar golden 정확히 일치
  - `daily.jsonl` golden 정확히 일치
  - `metrics.json` golden 정확히 일치
  - `trades.jsonl` golden 정확히 일치
  - `orders.jsonl` golden 정확히 일치
  - result_sha256이 있음
  - result_sha256이 기존 pipeline integrity 증거와 내부적으로 일치함(C)
  - 기존 verify reproducibility check가 True
  - 나머지 verify·code-state·report 동작은 Work Order 그대로
- 새 hash 알고리즘 없음. 정규화 계층 없음. provenance 제거 없음.

I. E2E_GATES (result_sha256 항목 대체):
- "result_sha256 = IMPLEMENTATION에서 고정한 값"을 "네 run 산출물 hash = B, result_sha256은 C의 내부 일치"로 대체한다.

J. STOP_CONDITIONS (대체 후 해당 조항):
- "두 번의 동등 실행에서 result_sha256이 다름"을 삭제하고 "CLI demo 경로의 네 run 산출물 hash 중 하나라도 B와 다름" 및 "result_sha256이 C의 내부 일치를 만족하지 않음"으로 대체한다.

## SCIENTIFIC_AND_PUBLIC_LANGUAGE

- 이것을 backtest 재현성의 실패라고 부르지 않는다. 측정된 실질 산출물은 결정적이었다.
- 정확한 표현을 쓴다. 예: "The existing result integrity hash includes timestamp-bearing provenance and is therefore not a cross-run deterministic identifier."
- 시각을 담은 provenance를 결함이라고 주장하지 않는다.
- 수익성이나 전략 검증을 주장하지 않는다.
- `SYNTHETIC / NOT_EVIDENCE`는 바뀌지 않는다.

## ENVIRONMENT_DECISION

- 공개 reviewer 전제 조건은 그대로다: `pip install -r requirements-dev.txt`, `pip install -e . --no-deps`. 이는 기존 README·CI 절차와 Work Order의 COMPLETE 환경(clean Git checkout + editable install)과 일치한다.
- task 실행용으로 EXTERNAL_TOOL_VENV(기존 QUALITY-GATES 외부 환경)에 editable install하는 것은 원칙적으로 승인되었다(APPROVED IN PRINCIPLE). 그러나 이 ERRATA gate는 그것을 실행 승인하지 않는다.
- 외부 Python 환경을 바꾸기 전에 별도의 TOOL_ENV_SETUP gate 승인이 필요하다.
- 이 gate에서 pip install을 하지 않았다. 저장소 안 `.venv`를 만들지 않는다.
- 정확한 machine-local 경로는 Gate Authorization과 채팅 증거에만 둔다.

## NEXT_GATES

GATE_SEQUENCE (이 ERRATA 이후 유효):
DISCOVERY_INVENTORY -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> Q0_MEASUREMENT (BLOCKED) -> ERRATA-001_SCOPE_DECISION -> TOOL_ENV_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

- 이후 gate의 유효 변경 승인은 `WO@638b90399e9156ecd43272b23ae718913bec1c50`과 `ERRATA@<Ce SHA>`를 함께 참조한다.
- Work Order의 "Q0_MEASUREMENT가 PASS하기 전에는 IMPLEMENTATION에 들어가지 않는다"는 이 ERRATA의 수락과 TOOL_ENV_SETUP PASS로 충족된 것으로 본다. Q0의 그 밖의 측정 항목은 모두 기준에 맞았다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다. ALLOWED_FILES와 PROTECTED_FILES는 바뀌지 않는다.
- src 변경을 승인하지 않는다. 새 정규화 hash를 도입하지 않는다. result_sha256을 고정하지 않는다.
- 이 ERRATA에는 machine-local 사용자 홈 경로나 Windows 계정명을 쓰지 않는다.
