# Work Order: ECON-SCREEN-V06-01-IMPL — 경제성 선별 전용 경로의 제한된 구현, fixture 검증, 합성 자원 측정

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/ECON-SCREEN-V06-01-IMPL/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: ECON-SCREEN-V06-01-IMPL
TASK_ID: ECON-SCREEN-V06-01-IMPL
TITLE: ECON-SCREEN-V06-01 전용 real 경로·품질·선별 조립의 구현과 fixture 검증, 합성 자원 측정
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: de22c19d97afa7cb9312e3bf294e7fc29242ad5c (branch codex/econ-screen-v06-01, 로컬, 원격 미게시)
CANONICAL_BASE_TREE: 23ab7c415ffa3a4a00ab07cdfe84dc21c06266ce
ENTRY_HEAD: de22c19d97afa7cb9312e3bf294e7fc29242ad5c (branch codex/econ-screen-v06-01)
ENTRY_TREE: 23ab7c415ffa3a4a00ab07cdfe84dc21c06266ce
TARGET_BRANCH: codex/econ-screen-v06-01-impl
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck (재사용. .venv의 editable 설치가 이 worktree의 src를 가리키므로 새 worktree를 만들지 않는다)
WORKSPACE_METHOD_EXCEPTION: 이 task의 WORKSPACE_SETUP에 한해 docs/tasks/README.md 표의 git worktree add -b(새 경로) 대신, TARGET_WORKTREE에서 CANONICAL_BASE_SHA를 기준으로 git switch -c codex/econ-screen-v06-01-impl을 1회 실행한다. 기존 branch·ref·산출물은 보존한다. 이 예외는 다른 task에 적용되지 않는다.
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
PYTHON: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe (기존 venv 재사용. 설치·갱신 없음)
PREREGISTRATION_PATH: docs/research_econ_screen_v06_01_preregistration.md
PREREGISTRATION_SHA256: 2ff766fa8e60adbc107b1ffe9ae4df30c455b616cd5345154704ff928b74705d
PREREGISTRATION_COMMIT: de22c19d97afa7cb9312e3bf294e7fc29242ad5c
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE (원격 게시·PR·MERGE gate 없음)
REQUIRED_CI_CHECKS: NOT_APPLICABLE
BUNDLE_ELIGIBLE: YES
BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E
EVIDENCE: 이 task의 모든 실행 출력은 SYNTHETIC / NOT_EVIDENCE다
RELATED_TASKS: ECON-SCREEN-V06-01(사전등록 고정 완료), DATAQ-V06-01 후보(미발행, 발행하지 않음), FUTVAL-V8-01 계열, RUNWATCH-01. 그 판정·보류·사건 기록과 비공개 조건을 바꾸지 않는다.

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> RESOURCE_MEASUREMENT -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 단일 gate 승인 형식
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-IMPL WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - 그 밖: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-IMPL <GATE> WO@<C1 SHA>
- 묶음: docs/tasks/README.md §14 BGA-0–BGA-10과 상태 전이 기준을 그대로 따른다. BUNDLE_AUTHORIZATION은 BGA-2의 키를 모두 포함해야 하며, 구간은 BUNDLE_MAX_RANGE 안이다. 묶음 안에서는 gate마다 채팅으로 보고하고, 전진 조건을 git·검사로 다시 확인해 통과하면 추가 채팅 승인 없이 다음 gate로 간다. 보고는 승인 요청이 아니다.
- CONTRACT_REVIEW, WORKSPACE_SETUP, RESOURCE_MEASUREMENT, CLOSEOUT_REPORT는 묶지 않으며, 각각 단일 Gate Authorization이 필요하다. RESOURCE_MEASUREMENT는 CLEAN_COMMIT_E2E_PASS 뒤에만 승인할 수 있다.
- git commit은 WORKSPACE_SETUP의 C1과 COMMIT gate의 C2 각 1회만 허용한다. 모든 settings·guard 승인 창은 사용자가 그 창에서 별도로 승인한다. BGA는 그것을 대신하지 않는다.
- 상태 변경은 각각 별도 도구 호출로 하고 결과를 확인한 뒤 다음으로 간다. 조회·해시·보존 비교는 목적별 작은 호출로 나눈다. 검사 명령 뒤에 파이프·자르기·리디렉션·다른 명령을 붙이지 않는다.
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)과 고정 사전등록이 우선한다. 충돌하면 STOP한다. 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: 고정 사전등록(2ff766fa…) 13절 2단계를 구현한다. 범위는 다음 일곱 가지다.
- 설계 문서의 BT-5S 제한 허용 범위
- 이 study 전용 real 입력 경로
- 5절 필수 품질 검사
- 회복 기간과 기존 지표의 보고 조립
- 4전략·144조합과 SCREEN_FLAG 출력
- fixture 검증
- 실제 데이터 없는 제한된 합성 자원 측정
실제 데이터의 수집·열람·계산은 하지 않는다.

## BACKGROUND

BACKGROUND:
- 기존 "BT-5 이전 real 금지"(bar_export, bars_io, portfolio, vault, run)는 일반 경로에서 그대로 유지한다. 이 task는 permit을 거친 이 study 전용 경로만 추가한다. vault·run은 바꾸지 않는다.
- 사전등록 문구는 구현 편의로 바꾸지 않는다. 구현할 수 없는 조건이 나오면 PROPOSED_ERRATA로 보고하고 STOP한다.
- 근거(읽기 전용 확인): backtest/cost_analysis.py에서 1,000,000 KRW(INITIAL_CASH_KRW)는 break_even_fee의 capital_krw 표시 문자열에만 쓰인다. k_log·c_b·c_s·f*는 전달된 CostModel(ι(C) 포함)로, gross는 왕복 가격으로, net은 수익률로 계산한다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 출력(PRESERVATION_CHECK, 상태 변경 전 첫 호출)
  - 진입 확인
    - HEAD·tree·branch가 ENTRY와 같다.
    - staged·unstaged·untracked가 없다.
    - TARGET_BRANCH와 docs/tasks/ECON-SCREEN-V06-01-IMPL이 없다.
    - HEAD의 사전등록 blob 내용 sha256이 PREREGISTRATION_SHA256과 같다.
    - data/ 아래 파일의 이름·크기·SHA-256 목록을 남긴다(DATA_RULES의 보존 예외).
  - 환경 확인(읽기 전용): PYTHON 버전, moneylab import 경로가 TARGET_WORKTREE/src 아래인지
  - git -C C:/MoneyLab-futval-v8-01-precheck switch -c codex/econ-screen-v06-01-impl de22c19d97afa7cb9312e3bf294e7fc29242ad5c 1회
  - Work Order를 승인 바이트로 Write 1회
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/ECON-SCREEN-V06-01-IMPL/WORK_ORDER.md 1회
  - C1 커밋 1회
  - 종료 시 PRESERVATION_CHECK
- IMPLEMENTATION(진입: HEAD = C1, clean)
  1. COLLECT_COMMAND 1회. 변경 전 수집 ID를 baseline으로 보존한다. baseline 전체 pytest는 실행하지 않는다
  2. ALLOWED_FILES만 Edit/Write로 생성·수정
  3. PYTEST_TARGET, RUFF, MYPY가 모두 통과할 때까지 BGA-4와 BUDGET 안에서 ALLOWED_FILES만 수정하고 다시 실행한다
  4. 3이 통과한 뒤 PYTEST_FULL을 백그라운드로 실행하고 완료 알림을 기다린다(폴링하지 않음)
  5. 종료 기준: 변경 ⊆ ALLOWED_FILES, W·S 집합을 기록
- PRECOMMIT_AUDIT(읽기와 감사만)
  - 변경 집합 = ALLOWED_FILES 계획
  - git diff --check exit 0, PROTECTED diff 0, 예상 밖 untracked 0
  - BGA-8 (A): COLLECT_COMMAND를 다시 실행해 baseline ID와 비교하고, 감소한 ID가 없어야 한다. 테스트 삭제, skip·xfail 추가, ALLOWED_FILES 밖 테스트 변경이 없어야 한다
  - BGA-8 (B): 단정 완화·우회는 "독립 검토 필요"로 보고한다
  - 계약 spot check: D1–D11
  - W·S 불변
- COMMIT
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- <ALLOWED_FILES 8개 경로 명시> 1회
  - 커밋 전 필수 확인: staged 경로 집합 = ALLOWED_FILES 8개, staged blob 내용 SHA-256 집합 = S, git -C C:/MoneyLab-futval-v8-01-precheck diff --cached --check exit 0. 하나라도 다르면 커밋하지 않고 STOP한다
  - C2 커밋 1회
- CLEAN_COMMIT_E2E(진입: HEAD = C2, clean)
  - PYTEST_TARGET, CLI_HELP 각 1회. 전체 pytest는 반복하지 않는다
  - 실행 전후 git status(ignored 포함)가 같아야 한다
  - 종료 시 PRESERVATION_CHECK
- RESOURCE_MEASUREMENT(별도 승인, 진입: HEAD = C2, clean)
  - MEASURE 1회. 파일을 쓰지 않는다
  - 실행 전후 git status가 같아야 한다
  - 종료 시 PRESERVATION_CHECK
- CLOSEOUT_REPORT: 읽기 전용 보존 확인과 보고
- 모든 gate: 읽기 전용 git 조회와 파일 해시·형식 검사

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 실데이터
  - live 수집, candles-pull(dry-run 포함), 네트워크
  - real pull·Bar의 생성·열람·계산
  - econ-screen-prepare·econ-screen-run의 real 모드 실행, 결과 열람
- 계약 문서
  - 사전등록·Work Order·ERRATA 수정, 사전등록 문안의 재해석·치환
- 범위
  - ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, 새 의존성, 설치, configs 변경
  - permit 없는 real 허용, vault·run의 real 허용
  - p값·V0·검정·판정 연결, 범용 자동화, 새 통계 검증·측정 연구, 감시 도구 구현, DATAQ 작업
- Git
  - fetch, push, PR, merge
  - git add의 전체 지정, amend, no-verify, reset, restore, stash, rebase, cherry-pick
  - 지정 외 checkout·switch, 지정 외 커밋
  - COMMIT 이후의 파일 수정
- 실행과 정리
  - 셸 출력 폐기·리디렉션·출력 분기, 임시 스크립트 파일
  - guard·hook·settings·권한 규칙·메모리 변경
  - 기존 산출물·다른 branch·worktree·untracked·ignored 항목의 변경·정리·삭제·복구

## DATA_RULES

DATA_RULES:
- 금지: 실데이터의 수집·생성·내용 열람·계산. data/raw와 data/processed의 기존 파일 내용을 열지 않는다.
- 예외(보존 확인 전용): data/ 아래 파일의 이름·크기·SHA-256 읽기. 이 읽기는 내용 해석·출력을 하지 않는다.
- 테스트와 측정은 테스트·코드 안에서 만든 합성 입력만 쓴다. 저장소 안 data/에는 아무것도 쓰지 않는다.

## ALLOWED_FILES

ALLOWED_FILES(모두 C2):
- M docs/backtest_design.md
- A src/moneylab/backtest/econ_screen.py
- M src/moneylab/backtest/bars_io.py (real_permit 키워드만)
- M src/moneylab/backtest/portfolio.py (real_permit 키워드만)
- M src/moneylab/providers/upbit/bar_export.py (real_permit 키워드와 study 전용 pull 검사 함수)
- M src/moneylab/cli.py (econ-screen-prepare, econ-screen-run, econ-screen-measure)
- A tests/test_econ_screen.py
- M tests/fixtures/README.md (테스트 안 합성 생성의 출처 기록. 새 fixture 파일 없음)

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/ECON-SCREEN-V06-01-IMPL/WORK_ORDER.md (WORKSPACE_SETUP 전용, 승인 바이트로 최초 1회). ALLOWED_FILES에 속하지 않는다.

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/** (위 예외의 최초 생성 1회 제외. 생성 뒤 수정 포함)
- docs/research_*_preregistration*.md, configs/**
- docs/** 중 docs/backtest_design.md를 뺀 전부
- src/moneylab/** 중 ALLOWED_FILES의 5개 경로를 뺀 전부. backtest의 run, vault, segment, settings, costs, execution, strategy, benchmarks, cost_analysis, performance, yearly, round_trips, ledger, metrics, report, data, code_state, risk_check, providers/upbit의 candles·candle_store, research/**, domain/**를 포함한다
- tests/** 중 tests/test_econ_screen.py와 tests/fixtures/README.md를 뺀 전부(tests/fixtures의 기존 파일 포함)
- .claude/**, .github/**, CLAUDE.md, README.md, .gitignore, .gitattributes, pyproject.toml, requirements*.txt
- data/** 기존 산출물

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (위 "뺀 전부" 표기로 8개 경로는 PROTECTED에 속하지 않는다)

## UNTRACKED_AND_IGNORED

UNTRACKED_AND_IGNORED:
- 예상 untracked
  - WORKSPACE_SETUP: Write 뒤 add 전까지의 docs/tasks/ECON-SCREEN-V06-01-IMPL/WORK_ORDER.md
  - IMPLEMENTATION·PRECOMMIT_AUDIT: ALLOWED_FILES의 A 경로 2개
  - 그 밖의 untracked는 예상 밖(F3)이다.
- 허용된 ignored 내부 변화: .venv/.mypy_cache 내용 갱신(MYPY). status의 ignored 항목 집합은 변하지 않아야 한다.
- 금지: 저장소 안 새 ignored 항목. __pycache__, .pytest_cache, .ruff_cache, .mypy_cache(.venv 밖), data/ 아래 새 파일을 포함한다.
- 허용 임시 파일: pytest 기본 tmp_path(OS 임시 영역)뿐이다. 테스트와 CLI 테스트는 --out을 tmp_path로 명시한다.

## COMMIT_PLAN

COMMIT_PLAN:
- C1(WORKSPACE_SETUP): parent = CANONICAL_BASE_SHA, A docs/tasks/ECON-SCREEN-V06-01-IMPL/WORK_ORDER.md, 메시지 docs(task): add ECON-SCREEN-V06-01-IMPL work order
- C2(COMMIT gate 1회): parent = C1, ALLOWED_FILES 8개, 메시지 feat(backtest): add ECON-SCREEN-V06-01 screening path
- 본문·trailer 없음. CANONICAL_BASE_SHA..C2 변경 경로는 WORK_ORDER.md와 ALLOWED_FILES뿐이다.
- COMMIT 이후의 수정·실패는 STOP이며 후퇴하지 않는다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 고정 spec
  - econ_screen.LOCKED_SPEC에 사전등록 값을 상수로 둔다.
    - study_id, market KRW-BTC
    - requested_start 2017-01-01T00:00Z, requested_end 2024-04-01T00:00Z(배타)
    - warmup 120일, E = requested_end − 3일
    - 규칙 M20·M60·M120·R5, 시나리오 E0·E1·E2
    - 수수료 {0,5,15,25} bp inclusive, 자본 {1,000,000, 5,000,000, 10,000,000} KRW
    - 기준 조합 (E0, 25, 10M)
    - B1: 9,999회, seed 20261119, bt-seed/1, label ["B1", 규칙, 시나리오]
    - 품질 임계: Q2 1/200, Q3 1/100, Q4(일 3, 시 7, 합계 3), Q7 1/200. 0.5배·2배 결과는 보고만
    - 표본 조건: G ≥ 5×365일, 기준 조합 왕복 ≥ 20
    - 플래그 조건(사전등록 9절), PREREGISTRATION_SHA256
  - real 모드는 LOCKED_SPEC 외의 spec와 9,999 외의 B1 횟수를 거부한다.
  - 다른 spec·draws는 fixture·synthetic 모드에서만 받는다.
- D2 일반 차단 유지
  - bars_io.load_bars, portfolio.simulate, bar_export.export_bars는 real_permit이 None이면 현재 동작과 바이트 단위로 같다.
  - bar_export의 allowed_provenance에 "real"을 넣는 경로는 계속 거부한다.
- D3 permit
  - EconScreenPermit은 mode(real | fixture)를 가진다. 아래 값이 모두 일치할 때만 만든다.
    - study_id, spec 해시
    - 사전등록 해시: 작업 파일 LF 정규화 해시와 HEAD blob 내용 해시. blob은 cli가 git으로 읽어 넘긴다
    - day·hour pull_id와 pull.json SHA-256: 사용자가 승인한 값을 CLI 인자로 받아 실제 값과 대조
    - requested 범위·시장·interval·provenance
    - code_state: real 모드에서는 code_state_problems가 빈 목록이어야 한다
    - 출력 root
  - Bar 변환 뒤에는 bars_sha256을 더한 permit만 load_bars·simulate에 쓸 수 있다.
  - real bar는 mode = real이고 bars_sha256이 일치하는 permit에서만 받는다.
  - 코드는 값의 일치만 검사하며 승인 메시지를 인증하지 않는다. 오용 방지 장치이고 보안 경계가 아니다.
- D4 순서(사전등록 5절)
  - Q1(verify_candle_pull)
  - Q6(duplicates_conflicting 0, invalid 0. 1건 이상이면 INVALID)
  - 수집 진행 조건: 두 pull complete, candles-verify ok, reached_earliest true, 1시간봉 첫 bucket 날짜 = 일봉 첫 bucket 날짜. 아니면 "수집 범위 미확정"
  - permit → Bar 변환 → Q2·Q3·Q4·Q7 → G 길이 조건 → 계산
  - 앞 단계가 PASS가 아니면 뒤 단계 함수를 부르지 않는다.
  - excluded_out_of_range 개수와 requested_end 이후 bucket 개수를 보고한다. 후자는 페이지의 시작 시각 필드만 파싱하고 값 필드는 Bar로 만들지 않는다.
- D5 품질 계산
  - 사전등록 5절 정의 그대로다.
  - 비율은 fractions.Fraction, Q7은 Decimal 정확 일치로 비교한다.
  - 상태는 PASS·INVALID·NOT_EVALUATED이고, 묶음 상태는 INVALID 또는 INCOMPLETE다(VALID 없음).
  - Q5·Q8·Q11·Q12·Q13은 NOT_EVALUATED로 표시한다.
- D6 계산
  - 조합마다 settings.cost_model(settings, fee, scenario, C, fee_basis="inclusive")와 RunConfig(rule, F, E, initial_cash = C, fill_substitution = "prereg_6_3", capacity_verified = cost_model 결과)로 simulate를 부른다. run_backtest는 쓰지 않는다.
  - 지표는 기존 함수를 그대로 쓴다: metrics.daily_log_returns, performance.series_metrics·max_drawdown_log, benchmarks.alignment·compare, cost_analysis, yearly_report, round_trip_report.
  - 자본 표시: capital_krw는 표시 상수에만 쓰이므로, 보고 계층에서 C로 표시하고 원래 값을 함께 남긴다. 계산값은 바꾸지 않는다.
  - Q9(신호 None 일수)·Q10(substituted·virtual_fallback 체결 수)은 보고만 한다.
  - p값·V0·verdict는 계산하지 않는다.
- D7 새 계산과 표시
  - 회복 기간
    - 수준은 P 기준 누적 로그 수준(max_drawdown_log와 같은 정의)이다.
    - 구현 규칙: 최대 낙폭에 처음 도달한 날(최초 저점)부터, 수준이 그 직전 고점 이상이 되는 첫 평가일까지의 일수다.
    - 끝까지 회복하지 못하면 value None·사유 "not_recovered", 낙폭이 0이면 value None·사유 "no_drawdown"이다.
  - 계산 불가 값은 사유와 함께 두고 0이나 다른 값으로 바꾸지 않는다(사전등록 8절).
  - 연도 비율
    - positive_year_ratio_full_years는 yearly_report의 value·사유를 그대로 보고한다.
    - 표본 조건(G ≥ 1,825일)을 통과하면 매일 평가 행이 있으므로 완전 연도가 3개 이상이고 계산 불가가 생기지 않는다. 계산 불가는 SCREEN_NOT_EVALUABLE 경우의 보고 행에서만 나온다.
    - 평가 가능한 전략에서 이 값이 계산 불가이면 사전등록 11절의 "계산 오류"로 STOP하고 플래그를 만들지 않는다.
  - SCREEN_FLAG는 사전등록 9절 그대로다.
- D8 출력·잠금·실패
  - prepare
    - <root>/.tmp-prepare-<stamp>/에 쓴 뒤 <root>/prepare-<stamp>/로 rename한다.
    - 내용: quality.json, bars 디렉터리, manifest.json, SHA256SUMS.txt
  - run
    - 계산 시작 전에 <root>/.tmp-run-<stamp>/를 만든다. 이것이 시도 표시다.
    - 완료 뒤 <root>/run-<stamp>/로 rename한다. 내용: screen.json, manifest.json, SHA256SUMS.txt
  - 잠금: real run은 root에 run-* 또는 .tmp-run-*가 하나라도 있으면 거부한다. prepare-*·.tmp-prepare-*는 run 잠금 대상이 아니다. 파일시스템 검사이며 삭제를 막지 못한다.
  - run 입력: run은 지정한 prepare 디렉터리의 SHA256SUMS·품질 상태를 다시 확인하고, Q2·Q3·Q4·Q7을 재계산해 같은지 본다.
  - 실패: 쓰기·계산이 실패하면 이미 쓴 파일과 임시 디렉터리를 그대로 보존하고, 경로를 보고한 뒤 종료한다. 삭제·복구·재시도를 구현하지 않는다. 덮어쓰지 않는다.
  - 출력 위치: real root는 data/processed/econ_screen_v06_01/이다. fixture·synthetic root는 이름이 -fixture로 끝나야 한다.
  - CLI 출력은 상태·경로·파일 해시만이다. 지표 값은 출력하지 않는다.
  - 증거 표시: real이면 L1_SCREENING / NOT_CONFIRMATORY, 그 밖이면 SYNTHETIC / NOT_EVIDENCE
- D9 BT-5S 문서: backtest_design.md에 BT-5S 절, 15절 로드맵 행, 17절 개정 이력 행을 추가한다. 내용은 다음과 같다.
  - 일반 BT-5 금지는 유지된다.
  - 허용은 ECON-SCREEN-V06-01 permit 경로뿐이다.
  - 허용 범위는 KRW-BTC 일·1시간봉, [2017-01-01, 2024-04-01), 사전등록 SHA 고정이다.
  - 순서는 사전등록 5절을 따르고, vault·run·segment는 제외한다.
  - 확증으로 승격하지 않는다.
  - prepare·run 각각 별도 승인이 필요하다.
- D10 테스트(tests/test_econ_screen.py, 오프라인, 테스트 안 합성 생성, tmp_path만 사용)
  - T1 LOCKED_SPEC 값과 사전등록 값 대조
  - T2 permit 없는 real 거부(load_bars, simulate, export_bars). allowed_provenance real 거부 유지
  - T3 permit 거부: 사전등록 해시, dirty code_state(real 모드), pull SHA 불일치, 범위·시장·interval·provenance 불일치, 잠금(run-*, .tmp-run-*), real 모드의 비고정 spec·draws·spec 인자
  - T3b 우회 차단
    - fixture·synthetic 모드 permit으로 real bar를 받을 수 없다.
    - spec·draws override는 real 모드에서 거부된다.
    - 다른 pull·bars 해시의 permit은 거부된다.
    - synthetic 측정 경로는 파일 입력을 받지 않는다.
    - 기존 일반 경로의 real 거부 메시지와 동작이 바뀌지 않는다.
  - T4 순서와 중단
    - 중단 사례: Q1 실패, Q6 1건, reached_earliest false, 첫 날짜 불일치, Bar 변환 거부
    - Q2·Q3: 임계와 같으면 PASS, 초과하면 INVALID
    - Q4: G 겹침과 3건
    - Q7: 불일치, 비교 가능일 0이면 NOT_EVALUATED
    - 위 경우 simulate가 호출되지 않음
  - T5 경계: d0, warmup 중 신호 없음, F, G 시작·끝, 시나리오별 가상 청산 시각, E, G_end 뒤 bar 사용 시 실패, 범위 밖·종료 이후 bucket 집계
  - T6 자본 일관성(세 C 각각)
    - ι(C) = 1 bp × √(C/1M)
    - 첫 매수의 수수료·κ·ι KRW 비용이 식과 같음
    - 일별 net 로그수익률이 같은 CostModel의 1M 실행과 1e-12 이내로 같음
    - 표시 자본 = C, f*에 ι(C)가 들어감
  - T7 144조합, 같은 규칙·시나리오의 12개 비용 조합이 같은 B1 배치, not_aligned 처리
  - T8 플래그와 표본 조건(1,825일·20회 경계, NOT_EVALUABLE 사유), 연도 비율 계산 불가는 NOT_EVALUABLE 행에서만 생기고 평가 가능 전략에서 생기면 STOP
  - T9 회복 기간: 손계산 기대값, 미회복, 낙폭 0, 동률이면 최초 저점
  - T10 출력
    - 원자적 rename, SHA256SUMS, 덮어쓰기 거부
    - 실패 시 임시 디렉터리와 이미 쓴 파일이 보존됨
    - prepare 산출물이 run 잠금을 일으키지 않음
    - CLI 출력에 지표 값 없음
  - T11 측정 함수가 작은 spec에서 동작하고 파일을 쓰지 않음
- D11 측정(econ-screen-measure, 합성 전용, 새 측정 연구·감시 도구 아님)
  - 입력: econ_screen.synthetic_bars(seed 20261119, label "MEASURE")
    - kind synthetic, 메모리 안에서만 만든다.
    - 일·1시간봉 모두 requested_start부터 requested_end까지다. 최장 길이로 상한을 가정할 뿐 상장일 주장이 아니다.
  - M1: simulate 6회(4규칙 × E0, M20 × E1·E2), 25 bp, 10M. 각 시간
  - M2: compare(draws 99와 999 각 1회), M20 E0
  - 반복: M1·M2를 2회
  - M3: tracemalloc을 켠 별도 1회. simulate(M120 E0)와 compare(draws 99)의 Python heap 최고치
  - 출력: stdout에 시간·heap·입력 길이만. 파일 쓰기 없음
  - 외삽: T_est = 12 × Σ_{규칙,시나리오} t_sim(미측정 조합은 같은 시나리오의 측정 최대값) + 144 × t_B1(999) × 9,999 / 999
  - T_est × 2는 예산 제안이며 실행 예산을 확정하지 않는다.
  - 540 s는 완료를 보장하는 값이 아니라 중단 기준이다.
  - 한계: 실제 공백·대체 체결에 따른 거래 수 차이, 기계 부하, tracemalloc은 RSS가 아님, prepare(재생·변환)는 측정하지 않음

## CHECK_COMMANDS

CHECK_COMMANDS(아래 문자열 그대로 단독 호출. 출력 자르기·리디렉션·파이프 없음):
- COLLECT_COMMAND (상한 600 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 600 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q
  - 출력 전체(도구가 파일로 보존한 경우 그 파일)를 baseline 증거로 둔다.
  - PRECOMMIT_AUDIT의 비교는 두 출력의 ID 집합을 읽기 전용으로 대조한다.
  - 출력 전체를 확인할 수 없으면 F2로 STOP한다.
- PYTEST_TARGET (상한 900 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 900 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/test_econ_screen.py tests/test_bar_export.py tests/test_backtest_core.py tests/test_backtest_run.py tests/test_backtest_cli.py tests/test_backtest_architecture.py tests/test_architecture_and_cli.py
- RUFF (상한 120 s)
  cd C:/MoneyLab-futval-v8-01-precheck && timeout 120 .venv/Scripts/ruff.exe check --no-cache src/moneylab/backtest/econ_screen.py src/moneylab/backtest/bars_io.py src/moneylab/backtest/portfolio.py src/moneylab/providers/upbit/bar_export.py src/moneylab/cli.py tests/test_econ_screen.py
- MYPY (상한 300 s. 대상은 신규 모듈 하나. 수정한 기존 파일은 저장소 mypy 필수 범위 밖이고 baseline 상태가 확인되지 않아 대상에 넣지 않는다)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 300 .venv/Scripts/python.exe -B -m mypy --cache-dir .venv/.mypy_cache src/moneylab/backtest/econ_screen.py
- PYTEST_FULL (상한 3600 s, Bash run_in_background로 실행하고 완료 알림을 기다린다)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 3600 .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q
- CLI_HELP (상한 60 s)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 60 .venv/Scripts/python.exe -B -m moneylab econ-screen-run --help
- MEASURE (상한 540 s, RESOURCE_MEASUREMENT 전용)
  cd C:/MoneyLab-futval-v8-01-precheck && PYTHONDONTWRITEBYTECODE=1 timeout 540 .venv/Scripts/python.exe -B -m moneylab econ-screen-measure
- 상한에 걸리면 결과 불명(F2)으로 STOP한다.

## FAILURE_RULES

FAILURE_RULES(BGA-4, BGA-10):
- IMPLEMENTATION에서 다음 실패만 BUDGET 안에서 ALLOWED_FILES를 고쳐 같은 명령으로 다시 실행할 수 있다.
  - tests/test_econ_screen.py의 신규 시험 실패
  - RUFF·MYPY 실패(CHECK_COMMANDS의 대상 파일)
- 기존 테스트 파일(tests/test_econ_screen.py 밖)에서 발생한 실패는 원인과 baseline에 관계없이 수정하지 않고 STOP한다. baseline 실패 허용 방식은 쓰지 않는다.
- PYTEST_FULL에서 기존 테스트가 실패하면 STOP한다. 신규 테스트만 실패하면 BGA-4 예산 안에서 고치고, PYTEST_TARGET·RUFF·MYPY를 거쳐 PYTEST_FULL을 다시 실행한다. 횟수는 BUDGET의 전체 pytest 횟수를 넘지 않는다.
- COMMIT 이후의 수정·실패는 STOP이다.
- 같은 실패가 연속 상한에 닿거나 예산을 넘으면 STOP한다.

## BUDGET

BUDGET(BGA-6 초기 실험값. 사용자가 선택한 값이다. 실제 묶음 승인은 C1 생성 뒤 BUNDLE_AUTHORIZATION으로 따로 한다):
- 묶음 전체 21600초, 명령별 시간 상한은 CHECK_COMMANDS를 따른다
- 전체 pytest 최대 2회, IMPLEMENTATION 수정 반복 최대 4회, 같은 실패 연속 최대 2회, 도구 호출 최대 200회

## PRESERVATION_CHECK

PRESERVATION_CHECK:
- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): GIT_HOST_WORKTREE의 다음 원문 전체
  - for-each-ref --sort=refname --format="%(refname) %(objectname)"
  - worktree list --porcelain
  - rev-parse HEAD HEAD^{tree}
  - status --porcelain=v1 --untracked-files=all --ignored=matching
- ref 분류
  - TASK: refs/heads/codex/econ-screen-v06-01-impl(생성 -> C1 -> C2)
  - OBSERVED: refs/codex/turn-diffs/checkpoints/**(기록만)
  - PRESERVE: 그 밖 전부. 다음을 포함하며 하나라도 변하면 STOP한다.
    - refs/heads/codex/econ-screen-v06-01 = de22c19d97afa7cb9312e3bf294e7fc29242ad5c
    - refs/heads/codex/futval-v8-01-run = c3d98eda9b969875f8eb7b05eb24ce3301e2dbd4와 그 원격 ref
    - refs/heads/codex/runwatch-01 = a3197059f0c1bc41e41ba0d2c7700836cb795645
- worktree: TARGET_WORKTREE를 제외하고 항목 단위로 비교한다. TARGET_WORKTREE의 기대 변화는 branch 전환과 HEAD가 C1·C2로 가는 것뿐이다. 같은 tree에서 전환하므로 checkout에 따른 파일 변화는 없다.
- host: HEAD·tree·status가 F0와 같아야 한다.
- 산출물: data/ 파일의 이름·크기·SHA-256이 WORKSPACE_SETUP 진입 목록과 같아야 한다. ignored 항목 집합이 같아야 한다(.venv 내부 mypy cache 갱신은 허용).
- 비교 시점: WORKSPACE_SETUP·CLEAN_COMMIT_E2E·RESOURCE_MEASUREMENT 종료, CLOSEOUT_REPORT

## EXPECTED_ASK

EXPECTED_ASK(guard 규칙 기준. 실제 발생은 보장하지 않음):
- WORKSPACE_SETUP: task-contract(Work Order 최초 Write) 최대 1회, git-commit 1회
- IMPLEMENTATION: guard ASK 0. 권한 모드에 따른 settings 편집 승인 창은 ALLOWED_FILES 경로당 최대 1회(최대 8회)
- PRECOMMIT_AUDIT: 0
- COMMIT: git-commit 1회
- CLEAN_COMMIT_E2E: 0
- RESOURCE_MEASUREMENT: 0
- docs/backtest_design.md는 guard 보호 경로가 아니다(guard ASK 0). 이 Work Order에서 ALLOWED_FILES로만 허용한다.
- 그 밖의 ASK·거절·무응답·DENY는 STOP

## REQUIRED_REPORT

REQUIRED_REPORT:
- gate별 HEAD·parent·tree, 변경 집합, W·S, PROTECTED diff, status(ignored 포함)
- baseline 수집 ID 수와 PRECOMMIT_AUDIT 비교 결과, 각 검사 명령의 결과·소요 시간, 수정 반복 횟수
- BGA-8 (A) 결과와 (B) "독립 검토 필요" 항목
- D1–D11과 대응하는 구현 위치, BT-5S 문서 diff 요약
- 측정: M1–M3 원시 값, 외삽식과 결과, 예산 제안(확정 아님), 한계
- PRESERVATION_CHECK 분류별 결과
- 증거 등급(GIT_VERIFIABLE, CLAUDE_REPORTED, INDEPENDENT), GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, ISSUES, <GATE>_PASS, READY_FOR_<NEXT>

## STOP_CONDITIONS

STOP_CONDITIONS:
- 진입 상태
  - ENTRY·base·tree·branch 불일치, 진입 시 clean 아님
  - TARGET_BRANCH·작업 경로가 미리 있음
  - 사전등록 해시 불일치, Work Order sha256·bytes·LF 불일치
- 범위
  - ALLOWED_FILES 밖 변경, PROTECTED 변경
  - 예상 밖 untracked, 저장소 안 새 ignored 항목
- 검사
  - 기존 테스트 실패, BGA-4 예산 초과, COMMIT 이후 수정·실패
  - 수집 ID 감소, 시간 상한 도달
- 계약: 사전등록 문구와 구현의 충돌(PROPOSED_ERRATA 보고), 평가 가능 전략의 연도 비율 계산 불가
- 보존: PRESERVE ref·worktree·host·data 산출물 변화
- 도구: guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- BUNDLE_AUTHORIZATION 원문 확인 불가, 상위 규칙과 충돌
