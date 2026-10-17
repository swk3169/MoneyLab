# Work Order: BT-3D — Backtest vault locking (HistoricalHoldoutVault, ForwardVault, single-open access records)

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/BT-3D/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: BT-3D
TASK_ID: BT-3D
TITLE: Backtest vault locking (HistoricalHoldoutVault, ForwardVault, single-open access records)
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 114c5f03227537620b2c554035376220eda77054
CANONICAL_BASE_TREE: 05f1248f46d6f4fbd487a4b559217941d9b88c37
TARGET_BRANCH: feature/backtest-bt3d-vault
TARGET_WORKTREE: C:/MoneyLab-bt3d-vault
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (squash/rebase merge 금지: 계약 커밋이 구현보다 먼저인 이력을 보존)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

DESIGN_INVESTIGATION과 CONTRACT_REVIEW는 이 파일 발행 전에 대화로 완료했다(BASE@114c5f0).

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: BT-3D <GATE> WO@<commit>`)
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

## GOAL

GOAL: v0.6 사전등록 초안 19.1–19.4와 backtest_design 10.3의 잠금 원칙(한 번만 개봉, 개봉 기록을 먼저 쓰고 읽기, 해시 대조, 잠금 구간 집계 전용 출력)을 synthetic/fixture 데이터에 대해 provider와 무관한 backtest 라이브러리(`backtest/vault.py`)로 구현한다. 모든 산출물은 SYNTHETIC / NOT_EVIDENCE다.

## BACKGROUND

BACKGROUND: 사전등록 16-0은 잠금 구현(19절)을 고정 전에 완료하도록 한다. backtest_design 2절은 `backtest/vault.py Holdout/Forward`를, 4절과 15절은 BT-3d를 "잠금 vault(open_once, seal, 접근 기록, 초안 19.1–19.5)"로 정한다. BT-3c 계약 D11도 같은 범위다. 현재 backtest에는 vault가 없고, 유일한 잠금 구현은 v0.4 `research/split.LockedTestVault`다(동작 참고만, 수정하지 않음).

## SOURCE_OF_TRUTH

SOURCE_OF_TRUTH:
- docs/research_v06_preregistration_draft.md: 8절 구간 표, 8.1, 10.1, 10.7, 11.3(9·12행), 16, 19.1–19.6, 부록 A [split]·[vault]
- docs/backtest_design.md: 2, 3, 4(BT-3b·BT-3c), 10.3, 12, 14.5, 15, 16(U9)
- BT-3c 계약 D11 (채팅 계약, design 4절 172행이 같은 범위를 기록)
- src/moneylab/research/split.py LockedTestVault (동작 참고, 이 계약 자체가 아님)

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: base 확인, TARGET_BRANCH/TARGET_WORKTREE 생성(base 114c5f0), 이 파일 하나 최초 생성, `git add -- docs/tasks/BT-3D/WORK_ORDER.md`, C1 commit 하나, 감사
- IMPLEMENTATION: ALLOWED_FILES 3개만 생성/수정, TEST_GATES 실행
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, commit 하나
- CLEAN_COMMIT_E2E: E2E_GATES 실행(ignored 출력만)
- PUSH: TARGET_BRANCH 하나만 `git push -u origin feature/backtest-bt3d-vault`
- PR_CI: compare URL과 PR 본문 제공. PR 생성은 별도 사용자 승인이 있을 때만
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
- 기존 worktree/branch 삭제·수정, 기존 untracked/ignored/reference artifact 정리
- C:/MoneyLab(`docs/chatgpt-task-handoff`)과 그곳 미커밋 파일 변경
- 인라인 인터프리터 실행(`python -c` 등), 임시 스크립트
- real 데이터, 거래소 API, 수집(candles-pull live), 주문, 페이퍼·실거래
- BT-4(사전등록·config 고정) 또는 BT-5(실데이터·bar_export 연결) 작업
- 사전등록 초안 수정, 18.1 결정(D1–D9) 확정

## ALLOWED_FILES

ALLOWED_FILES:
- A src/moneylab/backtest/vault.py
- A tests/test_backtest_vault.py
- M docs/backtest_design.md

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/BT-3D/**
- docs/tasks/** (README.md, TEMPLATE.md, WO-V1/** 포함)
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
- docs/backtest_bt2_review.md
- docs/backtest_bt2b_review.md
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
- base(114c5f0)에서 tests/ 아래 tracked인 모든 파일 (tests/fixtures/** 포함)

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 이 Work Order는 INVALID이고 IMPLEMENTATION에 진입할 수 없다)

## NON_GOALS

NON_GOALS:
- real 데이터·수집·bar_export 연결(BT-5), 사전등록·study config 고정과 config 로더(BT-4)
- "forward N개월"·"T_F개월"을 날짜로 바꾸는 계산 (DP4)
- CLI 명령 추가
- guard·settings·권한 규칙(19.5, U9)
- 11.3 판정·Q12 재수집 계산, 증거 SHA의 참 여부 검증
- forward 월별 위험 한도 확인 (DP1)
- v0.4 LockedTestVault 수정, 기존 스키마(bars/1, segment/1, run/2, report/2, result, bt-metrics/2, bt-seed/1) 변경
- 전역 vault 등록부, 기존 산출물·worktree 정리
- 통계 판정, 수익률 분석

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 모듈과 공개 API: `src/moneylab/backtest/vault.py` 하나. 공개 이름은 `VaultSpec`, `build_vault`, `vault_status`, `record_evidence`, `HistoricalHoldoutVault(vault_dir).open_once`, `ForwardVault(vault_dir).seal`, `ForwardVault(vault_dir).open_analysis`, 예외 클래스, 상태 상수다. import는 표준 라이브러리, `moneylab.backtest.bars_io`, `moneylab.backtest.data`, `moneylab.domain.bars`, `moneylab.storage.atomic`, `moneylab.core.exceptions`만 허용한다. providers·research·subprocess를 import하지 않는다.
- D2 VaultSpec: 다음 필드는 모두 명시적 입력이고 기본값이 없다.
  - confirmatory_data_end_utc C, holdout_end_utc H (배타적 끝 = H_end + 1일), locked_end_utc L (동결일 00:00)
  - forward_interim_end_utc, forward_final_end_utc (각각 None 가능)
  - preregistration_sha256, config_sha256 (64자리 소문자 hex)
  - 검사: 시각은 모두 timezone-aware UTC 00:00:00이어야 한다. C < H ≤ L이어야 한다. None이 아닌 W_end는 L보다 커야 한다. 둘 다 None이 아니면 interim < final이어야 한다.
  - L이 매월 1일이어야 한다는 제약은 없다.
- D3 구간 분할: 모든 Bar는 interval 단위로 정렬되어 있다고 전제하고, end_utc 기준으로 나눈다.
  - PUBLIC = {end ≤ C}
  - HOLDOUT_EVAL = {C < end ≤ H}
  - EXCLUDED = {H < end ≤ L}, H = L이면 비어 있다
  - LOCKED_HOLDOUT = HOLDOUT_EVAL ⊎ EXCLUDED
  - 구성 입력(day·hour BarSeries) 중 어떤 행이든 end > L이면 구성을 거부한다.
  - 따라서 interval마다 PUBLIC ⊎ LOCKED_HOLDOUT = 입력 전체다(서로 겹치지 않고, 버리는 행이 없다).
  - PUBLIC과 HOLDOUT_EVAL은 interval마다 비어 있으면 안 된다.
  - gap은 행이 없는 것이고 품질 판정은 범위 밖이다.
- D4 물리 배치 `<out_root>/<vault_id>/`:
  - out_root 이름은 fixture·synthetic이면 "-fixture"로 끝나야 한다.
  - 봉인 집합 = `vault_manifest.json`(moneylab.backtest.vault/1), `SHA256SUMS.txt`(봉인 파일, "<sha256>  <상대경로>", 바이트 사전순), `public/<입력 day 디렉터리 이름>/`과 `public/<입력 hour 디렉터리 이름>/`(각각 표준 bars/1: bars_<iv>.jsonl, bars_manifest.json, SHA256SUMS.txt), `locked/holdout_day.jsonl`, `locked/holdout_hour.jsonl`
  - 잠금 파일 바이트는 `canonical_bar_rows`이고, 파일 SHA는 `bars_sha256`과 같다. gzip 없음, interval별(D-L1).
  - 상태 항목 = `build_record.json`, `evidence/`, `access/`, `locked_forward/forward_YYYYMM/`
  - `public/`에 `segment_manifest.json`을 두지 않는다. 그래서 run.py는 전체 입력으로 처리한다.
- D5 seal의 정의: 바뀌지 않는 내용 바이트 생성 + manifest·SHA256SUMS 확정 + 원자적 게시(임시 디렉터리 → 바이트 대조 → rename 1회, 덮어쓰지 않음)를 모두 포함하는 ABSENT→SEALED 상태 전이다. 봉인된 바이트는 이후 어떤 API도 쓰지 않는다. vault 구성은 public과 holdout을 봉인하고, `seal(month)`는 forward 월 단위를 봉인한다.
- D6 내용 식별:
  - `vault_content_sha256` = `storage.atomic.sha256_of(payload)`
  - payload = schema, market, provenance, spec 전체(D2), interval별 public dir_name·bars_sha256·건수, interval별 잠금 파일 SHA·holdout_eval 건수·excluded 건수
  - `vault_id` = `vault_<market>_lock<L의 YYYYMMDDTHHMMZ>_<content sha 앞 12자리>`
  - manifest = payload + 입력 계보(interval별 입력 bars_sha256·건수·입력 bars manifest SHA) + evidence 표시 + content SHA + vault_id
  - `source_locator`·절대 경로·시각은 넣지 않는다. 따라서 content SHA, vault_id, manifest SHA는 경로와 무관하다.
  - forward 월 식별 `forward_seal_content_sha256`의 payload = month, vault_content_sha256, interval별 SHA·건수
- D7 접근 상태 식별과 기록:
  - 접근 상태는 해시 식별이 아니다. `access/`와 `evidence/`의 기록 집합에서 유도하며, content SHA·vault_id·SHA256SUMS에 영향을 주지 않는다.
  - `access/<holdout_open|forward_interim|forward_final>.json`은 같은 디렉터리의 임시 파일에 전체 내용을 쓰고 fsync한 뒤 `os.link(tmp, final)`로 배타적으로 생성한다. 이미 있으면(FileExistsError) VaultLockedError다. 임시 파일은 제거를 시도하고, 남아도 무시한다.
  - 기록 내용: kind, vault_content_sha256, 넘겨받은 prereg·config SHA, 사용한 증거 SHA, 대조한 파일 SHA, opened_at_utc(식별 아님), caller 표시
  - 기록이 생성되는 순간 1회 사용이다. `manifest.json`을 다시 쓰지 않는다(D-L2).
  - os.link가 FileExistsError가 아닌 다른 이유로 실패하면 아무것도 생성하지 않고 거부한다(사용 아님).
- D8 증거: `record_evidence(vault_dir, kind, sha256, *, detail)`
  - kind ∈ {confirmatory_results, row9_strategy, q12_done}
  - row9_strategy의 detail은 비어 있지 않은 전략 ID 목록이다.
  - `evidence/<kind>.json`을 D7과 같은 방식으로 배타적으로 생성한다.
  - 같은 내용이면 ALREADY_RECORDED_IDENTICAL(쓰기 없음), 다르면 거부한다.
  - BT-3D는 존재·형식·vault_content_sha256 결속만 검사하고, 참 여부는 검사하지 않는다.
- D9 `open_once(preregistration_sha256, config_sha256)` 순서:
  - (a) 기록 전 검사(실패하면 VaultPreconditionError 또는 VaultIntegrityError, 사용 아님):
    1. manifest·SHA256SUMS·봉인 파일이 서로 맞는다.
    2. provenance가 real이 아니다.
    3. `access/holdout_open.json`이 없다.
    4. 넘겨받은 prereg·config SHA가 spec과 같다.
    5. 증거 3종이 있고 형식이 맞다.
    6. 잠금 파일 SHA가 기록과 같다(해시만 하고, 파싱·반환하지 않는다).
  - (b) D7 접근 기록을 생성한다.
  - (c) 잠금 파일을 메모리로 한 번만 읽고, 그 버퍼의 SHA를 다시 대조하고, 같은 버퍼를 파싱하고, bars_sha256·건수를 대조한다.
  - (d) day·hour Bar를 반환하고, 각 행에 HOLDOUT_EVAL 또는 EXCLUDED 표시를 붙인다.
  - (b) 이후의 모든 예외(BaseException 포함)는 사용으로 남고, 행을 반환하지 않는다.
- D10 `seal(day_series, hour_series, month)`:
  - 봉인 창 FORWARD(m) = {max(m_start, L) < end ≤ m_next_start}, month ≥ month(L)
  - 조건: vault 봉인 집합이 온전하다. real이 아니다. interval마다 입력에 end ≥ m_next_start인 Bar가 있다(그 달이 끝났다는 뜻). FORWARD(m)이 interval마다 비어 있지 않다.
  - 창 밖 행은 봉인하지 않고 건수만 기록한다.
  - 결과 `locked_forward/forward_YYYYMM/`{forward_day.jsonl, forward_hour.jsonl, seal.json, SHA256SUMS.txt}는 임시 디렉터리를 거쳐 rename으로 게시한다.
  - 반환값은 건수·SHA뿐이다. 순서와 상관없이 봉인할 수 있고, holdout 개봉 여부와도 무관하다.
- D11 `open_analysis(kind, preregistration_sha256, config_sha256)` (RQ3 = E):
  - W_end(kind) = spec.forward_interim_end_utc 또는 spec.forward_final_end_utc
  - 기록 전 검사(사용 아님): W_end가 None이 아니다. `access/holdout_open.json`이 있다. `access/forward_<kind>.json`이 없다. prereg·config SHA가 같다. month(L)부터 month(W_end − 1초)까지 모든 달의 `forward_YYYYMM/`이 빠짐없이 있고 온전하다. 잠금 holdout 파일과 해당 월 파일의 SHA가 기록과 같다.
  - 그다음 D7 기록 → 재해시·파싱 → 반환한다.
  - 반환 범위: forward 행 중 `L < end ≤ W_end`인 것과 LOCKED_HOLDOUT 행(lookback). W_end 뒤 행은 돌려주지 않는다.
  - 봉인 창(D10)과 분석 자격(D11)은 서로 다른 개념이다.
  - 개월 수를 날짜로 바꾸는 계산과 첫 부분 월 규칙은 두지 않는다(DP4).
  - final이 interim을 요구하지 않는다.
- D12 예외: 모두 `VaultError(ValueError)` 아래에 둔다.
  - VaultLockedError: 이미 사용됨, 배타적 생성 경쟁에서 짐
  - VaultPreconditionError: 사용 아님
  - VaultIntegrityError: 기록 전이면 사용 아님, 기록 후면 사용
  - VaultExistsError: 기존 구조나 바이트가 다름
  - 예외 메시지에 잠금 행의 값·시각을 넣지 않는다.
- D13 crash와 재시도:
  - 구성·seal 도중 rename 전 crash: 결과물이 없다. `.tmp-*`는 vault로 읽지 않고 자동 삭제하지도 않는다.
  - rename 후 crash: 재시도하면 ALREADY_SEALED_IDENTICAL이다.
  - 접근 기록 link 전 crash: 사용 아님.
  - link 후 crash: 사용이며, 재시도하면 VaultLockedError다.
  - 읽을 수 없는 접근 기록은 OPENED(RECORD_UNREADABLE)로 보고, 다시 열지 못하게 거부한다.
  - 읽을 수 없는 증거 기록은 개봉을 거부한다(사용 아님).
  - 접근 상태를 초기화하거나 복구하는 API는 없다.
- D14 IDENTICAL_EXISTING (구성 시 `<out_root>/<vault_id>`가 이미 있을 때):
  1. 생성·수정·삭제·rename·권한 변경을 하지 않는다. 임시 디렉터리도 만들지 않는다. `build_record.json`도 다시 쓰지 않는다.
  2. 기존 `SHA256SUMS.txt` 바이트가 계획한 바이트와 같아야 하고, 거기 적힌 모든 파일이 있고 계획한 바이트와 같아야 한다.
  3. 최상위 항목은 봉인 집합의 최상위 항목(`vault_manifest.json`, `SHA256SUMS.txt`, `public/`, `locked/`)과 상태 항목(`access/`, `evidence/`, `locked_forward/`, `build_record.json`)만 허용한다. `public/`과 `locked/` 아래에는 봉인 목록에 있는 파일만 있어야 한다.
  4. 상태 항목은 비교·변경하지 않는다.
  5. ALREADY_SEALED_IDENTICAL과 현재 상태를 반환하고, 잠금 행은 반환하지 않는다.
  6. 하나라도 어긋나면 VaultExistsError이고, 덮어쓰기·수리·부분 복구를 하지 않는다.
  7. forward 월 디렉터리는 안의 목록이 봉인 집합과 정확히 같을 때만 IDENTICAL이다.
  - 구성 API는 어떤 경로로도 `access/`나 `evidence/`에 쓰거나 지우지 않는다.
- D15 provenance:
  - 구성과 seal에서 day·hour provenance가 `bars_io.REFUSED_KINDS`(real)에 속하면 거부한다.
  - day와 hour의 provenance가 다르면 거부한다.
  - BT-5 전까지 synthetic·fixture만 허용하며, 모두 SYNTHETIC / NOT_EVIDENCE다.
- D16 정보 누출:
  - 잠금 행을 반환하는 공개 API는 `open_once`와 `open_analysis`뿐이다.
  - `vault_status`는 id, content SHA, provenance, spec 값, public 건수, interval별 holdout_eval·excluded 건수와 잠금 파일 SHA, 무결성 PASS/FAIL, 접근 상태(UNOPENED/OPENED/RECORD_UNREADABLE), 증거 유무, 봉인된 월 목록과 월별 건수만 반환한다.
  - 잠금 행의 가격·수익률·개별 시각·첫/끝 시각은 반환하지 않는다(19.4).
- D17 하위 호환: bars/1, segment/1, run/2, report/2, result, bt-metrics/2, bt-seed/1의 형식과 코드를 바꾸지 않는다. public bars/1은 load_bars, export_segment, run_backtest, verify가 수정 없이 읽는다. v0.4 vault와 guard는 그대로 둔다.
- D18 보장과 비보장:
  - 보장 G1–G6: 결정적인 물리 분리, 공개 API로는 두 함수로만 잠금 행 접근, 배타적 단일 사용(동시성·crash 포함, 기록을 먼저 쓰고 읽기), 기록 전·후 해시 변조 탐지, real 거부, 상태·예외에서 누출 없음
  - 비보장 N1–N6: 경로 직접 읽기(특히 `locked_forward/`), access 기록 삭제로 초기화, 다른 경로에 재구성해 새 vault 얻기, 원본·전체 기간 source bars 노출, 증거의 참 여부, 같은 프로세스 안의 악의적 코드
- D19 docs/backtest_design.md 갱신:
  - 4절과 10.3에 구현 상태와 D3–D16 요약
  - 2·3절 데이터 흐름 주석: vault는 backtest 라이브러리이고 bar_export 연결은 BT-5
  - DP1–DP4 기록(D-L1·D-L2가 사전등록 문구와 다른 점, W_end 해석은 BT-4)
  - 개정 이력에 BT-3d 행 추가
  - SYNTHETIC / NOT_EVIDENCE 표시

## DEFERRED_PREREQUISITES

DEFERRED_PREREQUISITES:
- DP1: forward 월별 위험 한도 확인(19.3 셋째 항목, 11.3 12행)은 확증 MDD·결과와 forward 평가 엔진을 갖춘 별도 계약 task로 미룬다. BT-3D는 대체 평가 API나 그 목적으로 forward 내용을 반환하는 경로를 두지 않는다(fail-closed). 16-0의 "고정 전 잠금 완료"는 이 항목만큼 충족되지 않는다.
- DP2: 잠금 파일 형식(D-L1: interval별 gzip 없는 canonical JSONL)과 19.1·부록 A `[vault]`의 `*.jsonl.gz` 단일 파일 문구의 차이를 BT-4 고정 때 반영한다.
- DP3: 접근 기록 위치(D-L2: `access/*.json`)와 19.2 "manifest에 먼저 쓴다" 문구의 차이를 BT-4 고정 때 반영한다.
- DP4: "forward 12개월", "T_F개월"을 구체적인 forward_interim_end_utc / forward_final_end_utc로 바꾸는 해석은 BT-4 study·config 고정에서 한다.
- 이 항목들은 BT-4·BT-5 작업을 승인하지 않는다.

## TEST_GATES

TEST_GATES:
- 새 파일 tests/test_backtest_vault.py (합성 BarSeries, tmp_path, 오프라인):
  - T1 결정성: 두 번 구성하면 봉인 바이트와 id가 같다. 경로가 달라도 content SHA·manifest SHA가 같다.
  - T2 경계: end = C·H·L에서 정확히 포함·제외된다. H = L이면 EXCLUDED가 비어 있다.
  - T3 분할: PUBLIC ⊎ LOCKED = 입력. end > L 행이 있으면 거부한다. PUBLIC이나 HOLDOUT_EVAL이 비면 거부한다.
  - T4 public 호환: load_bars·export_segment·run_backtest·verify가 public에서 통과한다. run manifest의 segment는 null이다.
  - T5 열지 않은 상태에서는 구성 결과·상태 조회에 잠금 행이 없다.
  - T6 open_once는 1회 성공하고, 두 번째는 VaultLockedError다.
  - T7 기록 전 실패(증거 누락·형식 오류, prereg/config 불일치, 잠금 파일 변조)는 사용이 아니다. 조건을 갖춘 뒤 정상 개봉된다.
  - T8 기록 후 실패를 주입하면 예외가 나고 재개봉이 거부된다.
  - T9 기록 선점 시 배타적 생성에서 패배하여 VaultLockedError다.
  - T10 빈·깨진 access 기록은 RECORD_UNREADABLE이고 개봉이 거부된다.
  - T11 IDENTICAL_EXISTING:
    - (a) 개봉·증거 기록 뒤 같은 입력으로 다시 구성하면 IDENTICAL이고, 전후 디렉터리 전체의 바이트·목록이 같다.
    - (b) 예상하지 못한 최상위 항목이 있으면 VaultExistsError다.
    - (c) 봉인 바이트가 하나라도 다르면 VaultExistsError다.
    - (d) build_record.json을 다시 쓰지 않는다.
    - (e) forward 월 디렉터리에 같은 규칙이 적용된다.
  - T12 증거는 한 번만 기록된다. 같은 값은 IDENTICAL, 다른 값은 거부한다.
  - T13 real 거부(구성·seal), "-fixture"가 아닌 루트 거부, provenance 불일치 거부
  - T14 seal: 창 선택(L이 월 중간인 경우 포함), 창 밖 행은 건수만, 끝나지 않은 달 거부, 빈 창 거부, 내용이 다른 재봉인 거부
  - T15 open_analysis:
    - holdout 개봉 전이면 거부한다. W_end가 None이면 거부한다. kind별로 1회만 열린다.
    - month(L)부터 month(W_end − 1초)까지 한 달이라도 빠지면 거부한다.
    - 정확히 `L < end ≤ W_end` 행과 holdout lookback만 반환하고, W_end 뒤 행은 반환하지 않는다.
    - L이 월 중간이고 W_end가 월 중간인 경우를 포함한다.
  - T16 상태 조회·예외 문자열에 합성 가격·잠금 행 시각이 들어 있지 않다.
  - T17 개봉·증거 기록·seal 뒤에도 vault_content_sha256과 SHA256SUMS가 바뀌지 않는다.
  - T18 spec 검증: 00:00이 아닌 경계, C<H≤L 위반, W_end ≤ L, interim ≥ final, 잘못된 SHA 형식은 거부한다.
  - T19 구성 API가 `access/`나 `evidence/`에 쓰지 않는다.
  - T20 fixture E2E: 저장소 합성 fixture로 bars를 만든 뒤 vault 구성 → public run·verify OK → 증거 3개 기록 → open_once 1회 → 재개봉 거부 → seal → 봉인이 W_end까지 닿지 않으면 open_analysis 거부, 닿으면 1회 성공
- 전체 pytest, failed 0 / errors 0. 기존 테스트 수정 0. tests/test_architecture_and_cli.py 통과
- `git diff --check` 깨끗함, 변경 파일 집합 = ALLOWED_FILES

## E2E_GATES

E2E_GATES:
- CLEAN_COMMIT_E2E (clean Ci, TARGET_WORKTREE):
  - (1) 전체 pytest, failed 0 / errors 0
  - (2) tests/test_backtest_vault.py 단독 실행 통과 (T20이 vault 흐름의 E2E. CLI가 없고 인라인 실행이 금지되어 있으므로 테스트로 확인한다)
  - (3) 기존 CLI `backtest`로 reference fixture bars(C:/MoneyLab-bt2b3-e2e/data/processed/e2e-v20y, day d6a40221…, hour 39ad26cb…)에서 5개 baseline을 새 ignored 출력 디렉터리에 다시 만든다. result.json SHA가 다음과 바이트 단위로 같아야 한다.
    - sma20 01b86731f866d1e12642d6419f15e52be10e3ff23812ed62c756c5980ebb7b2d
    - M20 d356e54f…2840
    - M60 6a5ec280…6810
    - M120 73293976…ec1b
    - R5 49f1eedc…cb5f
- 기존 출력·reference 산출물은 수정하지 않는다. `locked/` 경로는 단독 `sha256sum`·`ls`로만 다룬다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base SHA/tree, C1 SHA/parent/tree, Work Order sha256, Ci SHA/parent/tree, 커밋별 파일 집합과 diff stat, merge parent/tree
- CLAUDE_REPORTED: targeted·전체 pytest 결과, E2E 결과(baseline SHA 5개)
- INDEPENDENT: PR CI 결과, GitHub 화면(사용자 확인)
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
- 계약을 지키려면 PROTECTED 파일(run.py, bars_io.py, segment.py, storage/atomic.py, cli.py 등) 수정이 필요하다고 판명됨 (PROPOSED_ERRATA로 보고)
- 테스트 환경에서 os.link 배타적 생성이 동작하지 않음
- 예상하지 못한 untracked 파일

## REPORT_STORAGE

REPORT_STORAGE: gate별 보고는 채팅만. 저장소에 보관하지 않는다. COMPLETE 증거 요약을 파일로 남기려면 ACCEPTED ERRATA가 경로와 최초 생성을 명시해야 한다.
