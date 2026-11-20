# Work Order: ECON-SCREEN-V06-02-IMPL — timestamp null 보존, 결측 보고, 02 식별 연결

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/ECON-SCREEN-V06-02-IMPL/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: ECON-SCREEN-V06-02-IMPL
TASK_ID: ECON-SCREEN-V06-02-IMPL
TITLE: ECON-SCREEN-V06-02 제한 구현(사전등록 13절 2단계)
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 01262a7570379c9845358ea0e0c1be6723dd33a1 (branch codex/econ-screen-v06-02, 02 사전등록 고정 C2)
CANONICAL_BASE_TREE: 2f3c5cd9d36f4cb73bbc2fe4187238ec4cbdf1e8
ENTRY_HEAD: 01262a7570379c9845358ea0e0c1be6723dd33a1 (branch codex/econ-screen-v06-02)
ENTRY_TREE: 2f3c5cd9d36f4cb73bbc2fe4187238ec4cbdf1e8
TARGET_BRANCH: codex/econ-screen-v06-02-impl
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck (재사용. .venv의 editable 설치가 이 worktree의 src를 가리킨다)
WORKSPACE_METHOD_EXCEPTION: 이 task의 WORKSPACE_SETUP에 한해 TARGET_WORKTREE에서 CANONICAL_BASE_SHA를 기준으로 git switch -c codex/econ-screen-v06-02-impl을 1회 실행한다. 다른 task에 적용되지 않는다.
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
PYTHON: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe (재사용. 설치·갱신 없음)
PREREGISTRATION_PATH: docs/research_econ_screen_v06_02_preregistration.md
PREREGISTRATION_SHA256: c6bd5e7eb0bcd8d44e668a9289ea67dafc97462063003cc1f9d183c18f092f81
PREVIOUS_TASKS: ECON-SCREEN-V06-01 계열(IMPL, IMPL-02, IMPL-03, RUN 중단 종결), ECON-SCREEN-V06-02(사전등록 고정, CLOSEOUT_REPORT_PASS). 그 기록은 바꾸지 않는다.
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE
REQUIRED_CI_CHECKS: NOT_APPLICABLE
BUNDLE_ELIGIBLE: YES
BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E
EVIDENCE: 이 task의 모든 실행 출력은 SYNTHETIC / NOT_EVIDENCE다. 실제 pull·원본·산출물은 열지 않는다.

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> CHANGE_REVIEW -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 단일 gate 승인 형식
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: ECON-SCREEN-V06-02-IMPL WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - 그 밖: GATE_AUTHORIZATION: ECON-SCREEN-V06-02-IMPL <GATE> WO@<C1 SHA>
- 묶음은 docs/tasks/README.md §14 BGA-0–BGA-10을 따른다. 구간은 BUNDLE_MAX_RANGE 안이다. gate마다 보고하고 전진 조건을 다시 확인해 통과하면 다음 gate로 간다.
- CONTRACT_REVIEW, WORKSPACE_SETUP, CHANGE_REVIEW, CLOSEOUT_REPORT는 묶지 않는다.
- 프로젝트 저장소의 git commit은 C1(WORKSPACE_SETUP)과 C2(COMMIT gate) 각 1회만 허용한다. 시험이 tmp_path 안에 만드는 임시 저장소의 커밋은 프로젝트 커밋이 아니다.
- settings·guard 승인 창은 사용자가 그 창에서 따로 승인한다. BGA는 그것을 대신하지 않는다.
- 상태 변경은 각각 별도 호출로 한다. 검사 명령 뒤에 파이프·자르기·리디렉션·다른 명령을 붙이지 않는다.
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES:
- 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)과 고정된 02 사전등록이 우선한다. 충돌하면 STOP한다.
- 01 사전등록·계약·중단 기록은 바꾸지 않는다. 이 작업은 01을 재개하지 않는다.
- 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: 02 사전등록 13절 2단계의 제한 구현만 한다.
- G1 수집기: timestamp 키가 있고 값이 null인 행의 마지막 틱 시각을 None으로 보존하고, 마지막 틱 검사를 계산하지 못한 사유를 기존 warnings에 남긴다.
- G2 품질 기록: bar_quality에 보고 전용 last_tick_missing을 더한다.
- G3 식별: 연구 식별값을 고정된 02 값으로 연결한다.
- G4 합성 회귀 시험과 incident 기록 1건.
전략·평가 구간·비용·B1·SCREEN_FLAG·품질 임계값·RUNWATCH·계산 경로는 바꾸지 않는다.

## BACKGROUND

BACKGROUND:
- 01 RUN COLLECT_LIVE에서 1시간봉 pull(hour_KRW-BTC_20261119T190858838984Z)이 pages/0221.json 행 179–182의 timestamp null로 CandleParseError 중단했다. HTTP 200, 시도 1회, 키는 있고 값만 null, 다른 필드는 형식상 정상(구조 조사 결과).
- Upbit 공식 문서는 timestamp를 required integer int64로 정의하고 nullable·null 의미를 명시하지 않는다.
- 01은 중단 종결됐고, 02 사전등록(5절)이 결측을 보고 전용으로 분류했다.
- 이 작업은 가격·성과 결과를 보고 한 변경이 아니다. 실제 pull의 재사용 검증과 시간봉 재수집은 후속 실행 계약 범위다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 출력(PRESERVATION_CHECK, 상태 변경 전 첫 호출)
  - 진입 확인: HEAD·tree·branch = ENTRY, clean, TARGET_BRANCH와 docs/tasks/ECON-SCREEN-V06-02-IMPL 부재, 02 사전등록 blob 내용 SHA-256 = PREREGISTRATION_SHA256, data/ 파일의 이름·크기·SHA-256 목록(내용은 열지 않음)
  - git -C C:/MoneyLab-futval-v8-01-precheck switch -c codex/econ-screen-v06-02-impl 01262a7570379c9845358ea0e0c1be6723dd33a1 1회
  - Work Order를 승인 바이트로 Write 1회, 작성 파일 대조
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/ECON-SCREEN-V06-02-IMPL/WORK_ORDER.md 1회
  - 커밋 전 확인(staged 경로·내용 SHA-256·diff --cached --check) 후 C1 커밋 1회
  - 종료 시 PRESERVATION_CHECK
- IMPLEMENTATION(진입: HEAD = C1, clean)
  1. 수집 baseline: IMPL-03 PRECOMMIT_AUDIT의 COLLECT_COMMAND 출력(세션 tool-results/bcsbsao4z.txt, 3,339개 ID)을 baseline으로 쓴다. 근거: 그 수집 대상 tree(3b34ece3)부터 CANONICAL_BASE_SHA까지 src·tests 변경이 없다(문서 커밋만). 파일을 읽을 수 없으면 변경 전에 COLLECT_COMMAND를 1회 실행해 baseline으로 쓴다.
  2. ALLOWED_FILES만 Edit·Write로 수정한다.
  3. PYTEST_TARGET, RUFF, MYPY가 통과할 때까지 FAILURE_RULES 안에서 수정·재실행한다.
  4. 3이 통과한 뒤 PYTEST_FULL을 백그라운드로 1회 실행하고 완료 알림을 기다린다.
  5. 종료 기준: 변경 ⊆ ALLOWED_FILES. 작업 파일 해시 집합 W와 stage될 내용 해시 집합 S를 기록한다.
- PRECOMMIT_AUDIT(읽기와 감사만)
  - 실제 변경 경로 집합을 확정하고(⊆ ALLOWED_FILES) 그 집합으로 W·S를 기록한다. git diff --check exit 0, PROTECTED diff 0, 예상 밖 untracked 0
  - BGA-8 (A): COLLECT_COMMAND 1회, baseline 대비 감소한 ID 0, ALLOWED_FILES 밖 시험 파일 변경 0, skip·skipif·xfail 추가 0
  - BGA-8 (B): "독립 검토 필요"로 보고하고 CHANGE_REVIEW에서 다룬다
  - 기존 단정 변경 목록(파일·행·이유)과 TEST_RULES 부합 여부, D1–D7 spot check, W·S 불변
- COMMIT(독립 gate)
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- <PRECOMMIT_AUDIT에서 확정한 실제 변경 경로 명시> 1회
  - 커밋 전 필수 확인: staged 경로 집합 = PRECOMMIT_AUDIT에서 확정한 실제 변경 집합, staged blob 내용 SHA-256 집합 = S, git diff --cached --check exit 0. 하나라도 다르면 커밋하지 않고 STOP한다
  - C2 커밋 1회
  - 커밋 후 확인: parent(C2) = C1, C2 변경 집합 = PRECOMMIT_AUDIT에서 확정한 실제 변경 집합, commit blob 내용 = S, clean
- CLEAN_COMMIT_E2E(진입: HEAD = C2, clean)
  - PYTEST_TARGET 1회(백그라운드 가능), CLI_HELP 1회. 전체 pytest는 반복하지 않는다
  - 실제 변경 집합의 작업 파일 내용(LF 정규화)과 C2 blob 내용 SHA-256이 같다
  - 실행 전후 git status(ignored 포함)가 같다
  - 종료 시 PRESERVATION_CHECK
- CHANGE_REVIEW(별도 승인. 진입: HEAD = C2, clean)
  - 구현 작성에 참여하지 않은 별도 에이전트에게 읽기 전용 도구(Read·Grep·Glob)만 주어 C1..C2 변경분, 02 사전등록, 관련 코드·시험을 검토하게 한다
  - 질문: D1–D7 충족, null 이외 형식의 거부 유지, 보고 키 불변, 결측 건수의 범위와 판정 배제, 기존 permit·품질 결속·원자적 잠금·root 고정·커밋 일치 검사의 비약화, 시험이 거부 사유까지 검증하는지, incident의 사실·가설 구분과 미수행 사항 표기
  - 결과는 발견 사항(파일·행·조건·영향·계약 근거·최소 수정)과 실행 차단 여부로 보고한다. 증거 등급은 CLAUDE_REPORTED(별도 에이전트)다
  - 이 gate는 파일·Git을 바꾸지 않는다
- CLOSEOUT_REPORT: 읽기 전용 보존 확인과 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 실데이터: 원본·실패 pull·기존 산출물의 열람·수정·삭제, candles-pull(dry-run 포함), candles-verify, econ-screen-prepare·run의 실제 데이터 실행, 네트워크
- 측정·감시: 합성 자원 측정, RUNWATCH 실행
- 계약: 01·02 사전등록, 이전 Work Order·ERRATA, 이 Work Order의 수정
- 범위 확장
  - 전략·평가 구간·비용·B1·SCREEN_FLAG·품질 임계값·수집 진행 조건 변경
  - CandleQualityReport 필드·to_dict 키 추가, value_problems·ok 정의 변경, 다른 필드 검사 완화
  - 범용 다중 study 프레임워크, 범용 리팩터링, 새 도구, RUNWATCH 코드 수정
  - ALLOWED_FILES 밖 docstring 정리
- 시험 약화: permit·품질 결속·경로·해시·clean·커밋·잠금 검사를 mock으로 바꾸거나 조건 완화, 기존 단정 삭제·완화(TEST_RULES 예외 제외), 운영 CLI에 시험용 옵션 추가
- Git: fetch, push, PR, merge, git add의 전체 지정, amend, no-verify, reset, restore, stash, rebase, cherry-pick, 지정 외 checkout·switch·커밋
- 실행과 정리: 셸 출력 폐기·리디렉션·분기, 임시 스크립트 파일, guard·hook·settings·권한 규칙·메모리 변경, 기존 산출물·다른 branch·worktree·untracked·ignored 항목의 변경·정리

## ALLOWED_FILES

ALLOWED_FILES(C2에서 변경할 수 있는 최대 범위. 실제 변경 경로는 PRECOMMIT_AUDIT에서 확정하며, 필요 없는 파일은 변경하지 않는다):
- M src/moneylab/providers/upbit/candles.py (D1, D2, 모듈 docstring의 관측·미검증 기록)
- M src/moneylab/backtest/econ_screen.py (D3, D4)
- M src/moneylab/cli.py (D5: econ-screen 도움말·기본 경로 표시 문자열과 관련 주석만)
- M tests/test_upbit_candles.py
- M tests/test_upbit_candles_verify.py
- M tests/test_bar_export.py
- M tests/test_econ_screen.py
- M tests/fixtures/README.md (합성 시험 입력 출처 기록)
- M docs/backtest_design.md (15.1절 문구와 17절 개정 이력 행만)
- A docs/incidents/20261119-econ-screen-v06-01-hour-timestamp-null.md (D7)

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/ECON-SCREEN-V06-02-IMPL/WORK_ORDER.md (WORKSPACE_SETUP 전용, 승인 바이트로 최초 1회). ALLOWED_FILES에 속하지 않는다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/** (위 예외의 최초 생성 1회 제외)
- docs/research_*_preregistration*.md, configs/**
- docs/** 중 docs/backtest_design.md와 위 incident 파일을 뺀 전부(docs/incidents의 기존 파일 포함)
- src/moneylab/** 중 ALLOWED_FILES의 src 경로를 뺀 전부(providers/upbit/bar_export.py, candle_store.py, backtest/bars_io.py, portfolio.py, domain/**, runwatch/**, config.py, research/** 포함)
- tests/** 중 ALLOWED_FILES의 tests 경로를 뺀 전부(tests/test_skills.py, tests/test_runwatch.py, tests/fixtures/*.json 포함)
- .claude/**, .github/**, CLAUDE.md, README.md, .gitignore, .gitattributes, pyproject.toml, requirements*.txt
- data/** 전부

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 timestamp 파싱(candles.parse_candle)
  - "timestamp" in row이고 row["timestamp"] is None이면 last_tick_ms = None이다.
  - 키 누락, bool, int가 아닌 수(실수·Decimal), 문자열, 그 밖의 형식은 기존처럼 CandleParseError다.
  - 정수는 기존과 같다. 다른 필드 검사의 순서·조건·메시지는 바꾸지 않는다.
  - Candle.last_tick_ms의 형식은 int | None이다. values()·to_record는 그대로이며, None은 그 값으로 비교·기록된다(None과 정수의 중복은 값이 다른 중복, None과 None은 같은 값 중복).
- D2 마지막 틱 검사(candles.pull_candles)
  - last_tick_ms가 None이면 구간 검사를 계산하지 않고 warnings에 "<start_utc>: timestamp null, last-tick check not evaluated"를 추가한다. 대상은 수집 보고에 남은 캔들(요청 범위 안, 확정, 같은 bucket은 처음 받은 행)뿐이다.
  - 정수이면 기존 검사와 경고 문구가 같다.
  - CandleQualityReport의 필드와 to_dict 키는 늘리지 않는다. value_problems, invalid, ok, duplicates 집계는 바꾸지 않는다.
  - 값 보충, 행 삭제·건너뛰기는 하지 않는다.
- D3 보고 전용 결측 건수(econ_screen.bar_quality)
  - 반환 dict에 "last_tick_missing" = {"day": <int>, "hour": <int>, "scope": "[d0, requested_end) quality bars", "report_only": true}를 더한다.
  - 건수는 각 BarSeries에서 d0 <= start_utc < requested_end이고 last_tick_ms가 None인 Bar 수다. 그 구간 밖 Bar나 원본 행은 세지 않는다.
  - "required", quality_summary, Q2·Q3·Q4·Q7, evaluation_period, 계산 경로에는 넣지 않는다.
- D4 02 식별(econ_screen 상수)
  - STUDY_ID = "ECON-SCREEN-V06-02"
  - PREREGISTRATION_PATH = "docs/research_econ_screen_v06_02_preregistration.md"
  - PREREGISTRATION_SHA256 = "c6bd5e7eb0bcd8d44e668a9289ea67dafc97462063003cc1f9d183c18f092f81"
  - REAL_ROOT_NAME = "econ_screen_v06_02"
  - SCHEMA, LOCKED_SPEC(seed 20261119 포함), EVIDENCE_REAL, 계산 함수는 바꾸지 않는다.
  - permit·품질 결속·원자적 잠금·root 고정·사전 검증 순서·커밋 일치 검사는 그대로이며 상수만 02를 가리킨다.
- D5 CLI 표시: econ-screen-prepare·run·measure의 도움말과 --out 기본 경로 표시를 02 값으로 맞춘다. 인자·동작은 바꾸지 않는다.
- D6 문서
  - candles.py 모듈 docstring: 2026-11-19 관측(1시간봉 2019-03 구간, 키 있음·값 null), 공식 문서 정의(required int64, nullable 미명시), 의미·다른 값 정확성 미검증을 적는다.
  - tests/fixtures/README.md: 새 시험의 null 행이 합성(실제 응답 행 복사 아님)이라고 적는다.
  - docs/backtest_design.md: 15.1절에 02 연결과 결측 보고 전용 분류를, 17절에 이력 행을 더한다.
- D7 incident 문서(docs/incidents/20261119-econ-screen-v06-01-hour-timestamp-null.md)
  - 형식: tests/test_skills.py가 요구하는 이름 형식과 절(## 요약, ## 분류, ## 사실, ## 가설, ## 증거, ## 영향, ## 무결성, ## 복구 제안)
  - 사실: 01 시간봉 수집 실패(오류 문구, 페이지 0221, 행 179–182, HTTP 200, 시도 1회, 저장 페이지 222개, HTTP 요청 222회), 일봉 완료(verify ok), 파서가 정수만 받음
  - 공식 문서 정의와 실제 관측의 차이. 가설은 사실과 구분하고 null의 원인은 미검증으로 적는다
  - 조사 범위: 가격·거래량·성과 미열람, 구조 정보만 확인
  - 보존 대상: 일봉 pull(27개 파일, 다이제스트 93771f84d66b375e7e779124c46b4e62a7932d976fbfcc67b67551db5893dae8), 실패 시간봉 pull(445개 파일, 다이제스트 da643a341087b6e9de0bfe959988117714a492a97b1dde3ff2d6d7d8f5187e51)
  - 영향: 01 중단 종결, 02 별도 설계(사전등록 SHA-256 c6bd5e7e…)
  - 복구 제안: 02 사전등록 13절 순서를 참조만 한다. 재수집·재사용 검증을 수행했다고 쓰지 않는다
  - 증거: 기존 조사 출력을 재사용하며 원본을 다시 열지 않는다

## TEST_RULES

TEST_RULES:
- 모든 새 시험은 오프라인이며 합성 입력만 쓴다(실제 응답 행 복사 금지). tmp_path 밖에 쓰지 않는다.
- 필수 시험
  - T1 parse_candle: timestamp null → last_tick_ms None. 키 누락·True·1.5·"1"은 CandleParseError("timestamp"). 정수 불변
  - T2 pull_candles(합성 클라이언트): null 행이 캔들로 남고 warnings에 사유 항목이 생기며 ok·duplicates·invalid 불변
  - T3 중복: 같은 bucket의 None과 정수는 duplicates_conflicting, None과 None은 duplicates_identical
  - T4 null 행을 담은 합성 pull의 verify_candle_pull ok와 재생 보고 = 저장 보고
  - T5 그 pull의 export_bars(fixture) 성공, Bar 파일과 load_bars 재로드에서 last_tick_ms None 보존
  - T6 null 없는 합성 pull에서 report.to_dict()의 키 집합(키 목록 명시), 보고 값, warnings가 변경 전 동작과 같음(기대값을 시험에 명시해 단정). 실제 일봉 pull의 재사용 검증은 이 범위가 아니다
  - T7 bar_quality: 필수 Q·required·quality_summary는 None 유무와 무관하고 last_tick_missing만 달라짐. 범위 밖 None Bar는 세지 않음
  - T8 02 식별: permit은 02 사전등록 해시·root 이름만 받고 01 해시·econ_screen_v06_01 root는 거부(거부 사유 문구까지 단정)
  - T9 기존 T·R·S 시험과 아키텍처 시험이 02 식별값으로 통과
- 기존 단정 변경은 다음만 허용한다. PRECOMMIT_AUDIT에 파일·행·이유를 보고한다.
  - 01 식별 문자열을 02로 바꾸는 것
  - bar_quality 결과 dict 전체나 키 집합을 비교하는 단정에 last_tick_missing 키를 반영하는 것
  - 그 밖의 삭제·완화는 금지한다

## CHECK_COMMANDS

CHECK_COMMANDS(아래 문자열 그대로 단독 호출. 출력 자르기·리디렉션·파이프 없음):
- COLLECT_COMMAND (상한 600 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 600 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q
- PYTEST_TARGET (상한 2400 s, 백그라운드 가능. -rs로 skip 사유 출력)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 2400 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q -rs tests/test_upbit_candles.py tests/test_upbit_candles_verify.py tests/test_bar_export.py tests/test_econ_screen.py tests/test_backtest_core.py tests/test_backtest_run.py tests/test_backtest_cli.py tests/test_backtest_architecture.py tests/test_architecture_and_cli.py tests/test_skills.py
- RUFF (상한 120 s)
  cd C:/MoneyLab-futval-v8-01-precheck && timeout 120 .venv/Scripts/ruff.exe check --no-cache src/moneylab/providers/upbit/candles.py src/moneylab/backtest/econ_screen.py src/moneylab/cli.py tests/test_upbit_candles.py tests/test_upbit_candles_verify.py tests/test_bar_export.py tests/test_econ_screen.py
- MYPY (상한 300 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 300 .venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache src/moneylab/providers/upbit/candles.py src/moneylab/backtest/econ_screen.py
- PYTEST_FULL (상한 5400 s, 백그라운드, 완료 알림 대기)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 5400 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q -rs
- CLI_HELP (상한 60 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 60 .venv/Scripts/python.exe -B -m moneylab econ-screen-run --help
- 상한 도달은 STOP한다. 검사 대상에서 파일을 빼서 실패를 피하지 않는다.

## FAILURE_RULES

FAILURE_RULES(BGA-4, BGA-10):
- ALLOWED_FILES 밖 시험의 실패는 원인과 관계없이 수정하지 않고 STOP한다.
- ALLOWED_FILES 안의 시험 파일에서 이 작업이 추가·수정한 시험의 실패와, ALLOWED_FILES의 src 경로에서 생긴 RUFF·MYPY 실패만 BUDGET 안에서 ALLOWED_FILES를 고쳐 같은 명령으로 다시 실행한다.
- ALLOWED_FILES 안의 시험 파일이라도 이 작업이 바꾸지 않은 기존 시험이 실패하면 STOP한다.
- 기존 단정의 변경은 TEST_RULES의 허용 범위 안에서만 하며, 실패를 피하려는 변경은 하지 않는다.
- PYTEST_FULL에서 위 STOP 대상이 실패하면 STOP한다. 신규·수정 시험만 실패하면 예산 안에서 고치고 PYTEST_FULL을 1회 더 실행할 수 있다(최대 2회).
- COMMIT 이후 수정·실패는 STOP한다.
- 같은 실패가 연속 상한에 닿거나 예산을 넘으면 STOP한다.

## BUDGET

BUDGET(BGA-6 초기값. 실제 묶음 승인은 C1 생성 뒤 BUNDLE_AUTHORIZATION으로 한다):
- 묶음 전체 21600 s, 명령별 상한은 CHECK_COMMANDS를 따른다
- 전체 pytest 최대 2회(기본 1회), IMPLEMENTATION 수정 반복 최대 4회, 같은 실패 연속 최대 2회, 도구 호출 최대 200회
- 자원 측정: 계산 경로(simulate, B1)를 바꾸지 않으므로 합성 측정을 반복하지 않는다. 01 구현 단계 측정값과 그 한계(prepare·재검증·출력 미포함, Python heap만)를 그대로 쓴다

## PRESERVATION_CHECK

PRESERVATION_CHECK:
- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): GIT_HOST_WORKTREE의 for-each-ref --sort=refname --format="%(refname) %(objectname)", worktree list --porcelain, rev-parse HEAD HEAD^{tree}, status --porcelain=v1 --untracked-files=all --ignored=matching 원문 전체(표지 F0V0602IMPL)
- ref 분류
  - TASK: refs/heads/codex/econ-screen-v06-02-impl(생성 -> C1 -> C2)
  - OBSERVED: refs/codex/turn-diffs/checkpoints/**(기록만)
  - PRESERVE: 그 밖 전부. 하나라도 변하면 STOP한다. 다음을 포함한다.
    - refs/heads/codex/econ-screen-v06-02 = 01262a7570379c9845358ea0e0c1be6723dd33a1
    - refs/heads/codex/econ-screen-v06-01-run = bee1d2e3b3f0863c3a82a6bc2221914cf8a066ab
    - refs/heads/codex/econ-screen-v06-01-impl-03와 refs/remotes/origin/codex/econ-screen-v06-01-impl-03 = 3b34ece3da58dd0cc4099da92238da9d17e83590
    - refs/heads/codex/econ-screen-v06-01-impl-02 = 281e0948d24db3d264c80807af56b252748b5ae8
    - refs/heads/codex/econ-screen-v06-01-impl = bd6e7400ed79ff426aa19c4b8d45e474ae7e1ee2
    - refs/heads/codex/econ-screen-v06-01 = de22c19d97afa7cb9312e3bf294e7fc29242ad5c
    - refs/heads/codex/runwatch-01 = a3197059f0c1bc41e41ba0d2c7700836cb795645
    - refs/heads/codex/futval-v8-01-run와 그 원격 ref = c3d98eda9b969875f8eb7b05eb24ce3301e2dbd4
- worktree: TARGET_WORKTREE를 제외하고 항목 단위로 비교한다. TARGET_WORKTREE의 기대 변화는 branch 전환과 HEAD가 C1·C2로 가는 것뿐이다.
- host: HEAD·tree·status가 F0와 같다.
- data: 진입 목록(파일 511개, 01 pull 2개 포함)의 이름·크기·SHA-256이 같고 새 파일이 없다. 저장소 안 새 ignored 항목이 없다(.venv/.mypy_cache 내부 갱신만 허용).
- 비교 시점: WORKSPACE_SETUP 종료, CLEAN_COMMIT_E2E 종료, CLOSEOUT_REPORT

## UNTRACKED_AND_IGNORED

UNTRACKED_AND_IGNORED:
- 예상 untracked: WORKSPACE_SETUP의 Work Order(Write 뒤 add 전), IMPLEMENTATION의 incident 파일(COMMIT까지). 그 밖은 STOP이다.
- 시험 임시 자원은 pytest tmp_path(OS 임시 영역)만 허용한다. 임시 git 저장소의 커밋은 git -c user.name=econ-screen-test -c user.email=test@example.invalid -c commit.gpgsign=false -c core.hooksPath=<tmp_path 안의 빈 디렉터리>로 만든다. 그 호출로 승인 창이 생기면 STOP한다.

## COMMIT_PLAN

COMMIT_PLAN:
- C1(WORKSPACE_SETUP): parent = CANONICAL_BASE_SHA, A docs/tasks/ECON-SCREEN-V06-02-IMPL/WORK_ORDER.md, 메시지 docs(task): add ECON-SCREEN-V06-02-IMPL work order
- C2(COMMIT gate 1회): parent = C1, PRECOMMIT_AUDIT에서 확정한 실제 변경 집합(⊆ ALLOWED_FILES), 메시지 fix(upbit): keep null candle timestamps and link ECON-SCREEN-V06-02
- 본문·trailer 없음. CANONICAL_BASE_SHA..C2 변경 경로는 Work Order와 그 실제 변경 집합뿐이다. ALLOWED_FILES 수를 맞추려고 필요 없는 파일을 바꾸지 않는다.
- COMMIT 이후 수정·실패는 STOP이며 후퇴하지 않는다.

## EXPECTED_ASK

EXPECTED_ASK(guard 규칙 기준. 실제 발생은 보장하지 않음):
- WORKSPACE_SETUP: task-contract(Work Order 최초 Write) 최대 1회, git-commit 1회
- IMPLEMENTATION: settings 편집 승인 창은 ALLOWED_FILES 경로당 최대 1회(최대 10회). guard ASK 0
- PRECOMMIT_AUDIT: 0
- COMMIT: git-commit 1회
- CLEAN_COMMIT_E2E: 0
- CHANGE_REVIEW: 0(별도 에이전트는 읽기 전용 도구만 쓴다)
- 그 밖의 ASK·거절·무응답·DENY는 STOP

## REQUIRED_REPORT

REQUIRED_REPORT:
- gate별 HEAD·parent·tree, 변경 집합, W·S, PROTECTED diff, status(ignored 포함)
- 검사 결과·소요 시간·skip 사유, 수정 횟수, baseline 비교, BGA-8 (A) 결과, 기존 단정 변경 목록
- D1–D7 대응 위치와 T1–T9 결과
- CHANGE_REVIEW 발견 사항과 실행 차단 여부(CLAUDE_REPORTED 별도 에이전트)
- PRESERVATION_CHECK 분류별 결과
- 증거 등급(GIT_VERIFIABLE, CLAUDE_REPORTED, INDEPENDENT), GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES, <GATE>_PASS, READY_FOR_<NEXT>

## STOP_CONDITIONS

STOP_CONDITIONS:
- 진입 상태: ENTRY·base·tree·branch 불일치, clean 아님, 대상이 미리 있음, 사전등록·Work Order 해시 불일치
- 범위: ALLOWED_FILES 밖 변경, PROTECTED 변경, 예상 밖 untracked, 저장소 안 새 ignored 항목
- 검사: 기존 시험 실패, 예산 초과, COMMIT 이후 수정·실패, 수집 ID 감소, 시간 상한 도달, 허용 외 단정 변경
- 계약: 02 사전등록과 구현의 충돌(PROPOSED_ERRATA 보고)
- 보존: PRESERVE ref·worktree·host·data 변화
- 리뷰: CHANGE_REVIEW에서 실행 차단 결함 발견
- 도구: guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- STOP 뒤 변형 재시도는 하지 않는다.

## FOLLOW_UP_PLAN

FOLLOW_UP_PLAN(이 Work Order의 승인 범위가 아니다. 각각 별도 계약·승인):
- 실행 계약(02 사전등록 13절 3–9단계): 일봉 pull 재사용 검증(오프라인), 1시간봉 dry-run과 live 1회, 품질 확인, 예산 승인, 선별 1회, 무결성 확인, 별도 결과 열람. EXEC_COMMIT은 이 작업의 C2 위의 실행 Work Order 커밋으로 정한다.
- 공개 백업 여부는 따로 결정한다.
