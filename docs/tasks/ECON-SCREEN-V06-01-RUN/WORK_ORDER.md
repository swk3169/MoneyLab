# Work Order: ECON-SCREEN-V06-01-RUN — 실데이터 수집·prepare·선별 1회 실행

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/ECON-SCREEN-V06-01-RUN/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: ECON-SCREEN-V06-01-RUN
TASK_ID: ECON-SCREEN-V06-01-RUN
TITLE: ECON-SCREEN-V06-01 실데이터 수집·prepare·선별 1회 실행
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 3b34ece3da58dd0cc4099da92238da9d17e83590 (branch codex/econ-screen-v06-01-impl-03, IMPL-03 C2)
CANONICAL_BASE_TREE: ffe2a2adb13da016a5d958935b9b0c81ff610a2e
ENTRY_HEAD: 3b34ece3da58dd0cc4099da92238da9d17e83590 (branch codex/econ-screen-v06-01-impl-03)
ENTRY_TREE: ffe2a2adb13da016a5d958935b9b0c81ff610a2e
ENTRY_PRECONDITION: 공개 백업이 이 Work Order의 WORKSPACE_SETUP 전에 별도 승인으로 끝나 있다. refs/remotes/origin/codex/econ-screen-v06-01-impl-03 = CANONICAL_BASE_SHA
TARGET_BRANCH: codex/econ-screen-v06-01-run
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck (재사용)
WORKSPACE_METHOD_EXCEPTION: 이 task의 WORKSPACE_SETUP에 한해 TARGET_WORKTREE에서 CANONICAL_BASE_SHA를 기준으로 git switch -c codex/econ-screen-v06-01-run을 1회 실행한다. 다른 task에 적용되지 않는다.
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
PYTHON: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe (재사용. 설치·갱신 없음)
RUN_CWD: C:/MoneyLab-futval-v8-01-precheck
RUN_ENV: MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data. 실행·조회 명령마다 명령 앞에 명시한다. .env에만 두는 것은 명시로 인정하지 않는다.
CANONICAL_ROOT: C:/MoneyLab-futval-v8-01-precheck/data/processed/econ_screen_v06_01
PULL_ROOT: C:/MoneyLab-futval-v8-01-precheck/data/raw/upbit/candles_v06
WATCH_DIR_PREPARE: C:/MoneyLab-futval-v8-01-precheck/data/processed/runwatch_econ_screen_v06_01_prepare-a1
WATCH_DIR_RUN: C:/MoneyLab-futval-v8-01-precheck/data/processed/runwatch_econ_screen_v06_01_run-a1
PREREGISTRATION_PATH: docs/research_econ_screen_v06_01_preregistration.md
PREREGISTRATION_SHA256: 2ff766fa8e60adbc107b1ffe9ae4df30c455b616cd5345154704ff928b74705d
PREVIOUS_TASKS: ECON-SCREEN-V06-01, -IMPL, -IMPL-02(ERRATA-001 포함), -IMPL-03(CLOSEOUT_REPORT_PASS. CHANGE_REVIEW CONFORMS, CLAUDE_REPORTED 별도 에이전트). 그 기록은 바꾸지 않는다.
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE
REQUIRED_CI_CHECKS: NOT_APPLICABLE
BUNDLE_ELIGIBLE: NO
EVIDENCE: real 데이터. 증거 등급 L1_SCREENING / NOT_CONFIRMATORY(사전등록 4행). 결과는 수익성 입증·통계적 결론·실거래 적합성 판단이 아니다.
RESULT_DISCLOSURE: PRIVATE. 결과 내용은 승인된 RESULT_VIEW에서 비공개 채팅으로만 보고한다. 결과·산출물은 커밋·push·공개 문서화하지 않는다. 공개는 따로 결정한다.

## EXECUTION_COMMIT

EXECUTION_COMMIT:
- C1은 이 Work Order의 최초 커밋이며 parent = CANONICAL_BASE_SHA다. CANONICAL_BASE_SHA..C1 변경은 이 Work Order 파일 하나뿐이므로 실행 코드는 IMPL-03 C2와 같다. WORKSPACE_SETUP에서 diff로 확인한다.
- EXEC_COMMIT은 PREPARE 시작 시점의 HEAD다.
  - 기본값은 C1이다.
  - PREPARE 전에 ACCEPTED ERRATA 커밋(Ce)이 생기면 마지막 Ce가 EXEC_COMMIT이다. Ce는 docs/tasks/ECON-SCREEN-V06-01-RUN/ERRATA-<NNN>.md 하나만 추가해야 한다.
- PREPARE와 RUN의 승인문에 같은 EXEC_COMMIT=<40 hex>를 적는다.
- PREPARE 시작부터 INTEGRITY_CHECK 종료까지 TARGET_WORKTREE에서 커밋·switch·checkout·tracked 파일 변경을 하지 않는다.
  - 이 구간에 계약 변경이 필요하면 커밋하지 않고 STOP한다. PROPOSED_ERRATA는 채팅으로만 보고한다.
  - 이 구간의 새 커밋은 D6 코드 일치 검사로 run을 막으므로, 이 Work Order로는 실행하지 않는다.
- 실행 중 작업 트리는 clean이어야 한다. 새 산출물은 모두 ignored인 data/ 아래에만 생긴다.

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> COLLECT_DRY_RUN -> COLLECT_LIVE -> PULL_REVIEW -> PREPARE -> RUN_BUDGET -> RUN -> INTEGRITY_CHECK -> RESULT_VIEW -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- gate마다 별도 승인이 필요하며 묶지 않는다. gate 보고 뒤 멈춘다.
- 승인 형식
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-RUN WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - COLLECT_LIVE: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-RUN COLLECT_LIVE WO@<C1> MAX_PAGES_DAY=<n> MAX_PAGES_HOUR=<n>
    - 각 값은 COLLECT_DRY_RUN이 보고한 "at most N page request(s)" 이하다.
    - 이 값은 페이지 상한이다. 페이지마다 최대 2회 재시도하므로 HTTP 요청은 최대 3 × MAX_PAGES다.
  - PREPARE: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-RUN PREPARE WO@<C1> EXEC_COMMIT=<40 hex> DAY_PULL=<pull 디렉터리 이름> DAY_PULL_SHA256=<64 hex> HOUR_PULL=<pull 디렉터리 이름> HOUR_PULL_SHA256=<64 hex> MAX_SECONDS=3600 START_MIN_AVAILABLE_BYTES=12884901888 ABORT_BELOW_AVAILABLE_BYTES=6442450944
  - RUN: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-RUN RUN WO@<C1> EXEC_COMMIT=<40 hex> PREPARE_DIR=<prepare-*> MANIFEST_SHA256=<64 hex> MAX_SECONDS=7200 START_MIN_AVAILABLE_BYTES=12884901888 ABORT_BELOW_AVAILABLE_BYTES=6442450944
  - RESULT_VIEW: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-RUN RESULT_VIEW WO@<C1> RUN_DIR=<run-*> SCREEN_SHA256=<64 hex>
  - 그 밖: GATE_AUTHORIZATION: ECON-SCREEN-V06-01-RUN <GATE> WO@<C1>
- 실행 승인(RUN)과 결과 열람 승인(RESULT_VIEW)은 별개다(사전등록 12절). 한 메시지로 둘을 승인하려면 두 범위를 각각 적어야 한다.
- 프로젝트 저장소의 커밋은 C1과, PREPARE 전의 ACCEPTED ERRATA 커밋만 허용한다.
- 이 Work Order는 TASK_COMPLETE와 수익성을 선언하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES:
- 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)과 고정 사전등록이 우선한다. 충돌하면 STOP한다.
- 실거래·주문·지갑·키·자금은 범위 밖이다.
- 네트워크는 COLLECT_LIVE의 Upbit 공개 REST만 허용한다. 수집기의 core/http.HttpClient를 거친다.

## GOAL

GOAL:
- 고정 사전등록 13절 3–9단계를 순서대로 한 번 수행한다: 수집 dry-run → 별도 승인 live 수집·verify → pull 식별값 승인 → prepare와 품질 확인 → run 예산 승인 → run 1회 → 무결성 확인 → 별도 결과 열람.
- 코드·사전등록·전략·비용·B1·SCREEN_FLAG·품질 기준은 바꾸지 않는다.

## OPERATING_CONTROL

OPERATING_CONTROL(IMPL-03 D1 한계와 B1의 운영 통제):
- 모든 실행·조회 명령은 cd RUN_CWD로 시작하고 RUN_ENV를 명시한다.
- prepare와 run은 같은 EXEC_COMMIT, RUN_ENV, CANONICAL_ROOT, 승인 pull 2개, 승인 prepare manifest를 쓴다.
- real prepare는 승인된 1개만 만들고 쓴다.
  - 승인 prepare를 다른 root로 복사하지 않는다.
  - 실행을 시도한 뒤나 결과를 본 뒤에는 어느 root에서도 새 prepare를 만들지 않는다(재선별 금지, 사전등록 10·11절).
- 이 통제는 환경 변경까지 막는 전역 잠금이 아니며, 완전한 1회 실행 보장이 아니다.
- PRE_EXEC_CHECK: PREPARE와 RUN 직전에 PRE_EXEC_COMMAND를 1회 실행한다. 다음 중 하나라도 다르면 실행하지 않고 STOP한다.
  - HEAD = EXEC_COMMIT, branch = TARGET_BRANCH, 작업 트리 clean(ignored 제외 status 출력 없음)
  - 사전등록 blob과 작업 파일의 내용 sha256 = PREREGISTRATION_SHA256
  - DATA_DIR, RAW_DIR, ROOT 해석값 = RUN_ENV, PULL_ROOT의 상위, CANONICAL_ROOT
  - 승인 pull 2개의 pull.json SHA-256 = 승인값
  - PREPARE 직전: ROOT_ENTRIES = None. root가 없어야 한다.
  - RUN 직전: ROOT_ENTRIES = [PREPARE_DIR] 하나, PREPARE_PARENT_IS_ROOT True, PREPARE_MANIFEST = MANIFEST_SHA256
  - AVAILABLE_BYTES ≥ 승인 START_MIN_AVAILABLE_BYTES
  - 해당 WATCH_DIR가 없음
- 잠금 전 거부("refused before computation (no lock, no attempt marker)")도 STOP이다.
  - 수익성 계산이 시작되지 않았다는 사실만 기록한다.
  - 자동 재시도, 인자를 바꾼 재시도, 새 prepare 생성을 하지 않는다.
  - 재개 여부는 고정 사전등록과 새 승인으로 판단한다.
- 잠금 후 실패: run-lock, .tmp-run-*, run-*, 부분 산출물, RUNWATCH 기록을 지우거나 이름을 바꾸지 않는다. 자동 재실행하지 않는다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 출력(PRESERVATION_CHECK, 상태 변경 전 첫 호출)
  - 진입 확인
    - HEAD·tree·branch = ENTRY, clean, ENTRY_PRECONDITION 충족
    - TARGET_BRANCH와 docs/tasks/ECON-SCREEN-V06-01-RUN이 없음
    - 사전등록 해시 일치
    - CANONICAL_ROOT, WATCH_DIR_PREPARE, WATCH_DIR_RUN이 없음(이름만 확인)
    - data/ 파일의 이름·크기·SHA-256 목록(내용은 열지 않음)
  - git -C C:/MoneyLab-futval-v8-01-precheck switch -c codex/econ-screen-v06-01-run 3b34ece3da58dd0cc4099da92238da9d17e83590 1회
  - Work Order를 승인 바이트로 Write 1회
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/ECON-SCREEN-V06-01-RUN/WORK_ORDER.md 1회
  - C1 커밋 1회. 메시지 docs(task): add ECON-SCREEN-V06-01-RUN work order. 본문·trailer 없음
  - C1 확인: parent = CANONICAL_BASE_SHA, CANONICAL_BASE_SHA..C1 변경 = Work Order 하나, clean
  - 종료 시 PRESERVATION_CHECK
- COLLECT_DRY_RUN(네트워크·파일 쓰기 없음)
  - RESOLVE_COMMAND 1회, DRY_RUN_DAY 1회, DRY_RUN_HOUR 1회
  - 보고: 엔드포인트, 범위(UTC·KST), bucket 수, page_count, 최대 페이지 요청 수, 저장 위치(= PULL_ROOT)
  - 숫자는 출력값을 그대로 보고하며 추정으로 바꾸지 않는다.
  - 최대 페이지 수는 전체 요청 범위 기준의 계획값(ceil(bucket 수 / page_count) + 1)이다. 빈 페이지 종료에 필요한 요청 수를 그 안에 포함하려고 만든 값이며, 상장일과 API 경계 의미는 미검증이다.
  - 실행 전후 git status(ignored 포함)와 data/ 파일 목록이 같아야 한다.
- COLLECT_LIVE(Upbit 공개 REST. 사용자의 명시 승인 필수)
  - guard·settings에 candles-pull 확인 창이 없으므로 채팅 승인이 통제다.
  - 실행 시각: UTC 00:00–00:05와 매 정시 직후 3분을 피한다(CLAUDE.md 규칙을 보수적으로 적용).
  - 순서: LIVE_DAY 1회 → VERIFY_DAY 1회 → LIVE_HOUR 1회(백그라운드, 완료 알림 대기) → VERIFY_HOUR 1회
  - 수집은 새 디렉터리만 만들고 기존 파일을 덮어쓰거나 지우지 않는다.
- PULL_REVIEW(읽기 전용. 가격·수익률 값은 출력하지 않는다)
  - PULL_CHECK_COMMAND 1회. econ_screen_pull_checks는 원본 페이지의 시각 필드만 해석해 범위 밖 개수를 센다.
  - 판정
    - 사전등록 3절 수집 진행 조건: 두 pull status complete, verify_ok, reached_earliest True, 두 first_start의 날짜(UTC)가 같음
    - Q6: duplicates_conflicting = 0, invalid = 0
    - day last_start = 2024-03-31T00:00:00Z, hour last_start = 2024-03-31T23:00:00Z(마지막 hour bucket)
  - 범위 밖 bucket
    - 원본 페이지에 남는 것은 정상이며, Bar 변환·품질·평가에는 쓰지 않는다.
    - excluded_out_of_range와 at_or_after_requested_end를 보고한다.
    - at_or_after_requested_end ≥ 1이면 사전등록 3절에 따라 노출 기록 후보로 보고하고, 그 내용은 열지 않는다. 이 사실만으로 STOP하지 않는다.
  - 보고: 디렉터리 이름, pull_id, pull.json SHA-256, 위 키 값. 사용자가 PREPARE 승인문에 식별값을 적는다.
- PREPARE(RUNWATCH 감시)
  - PRE_EXEC_COMMAND(prepare) 1회 → RUNWATCH_PREPARE 1회(백그라운드, 완료 알림 대기) → PREPARE_REPORT_COMMAND 1회
  - 완료 판단: 다음이 모두 성립해야 한다.
    - watcher exit 0, reason COMPLETED, child_exit_code 0, termination VERIFIED
    - watch_final.json의 limits = 승인값, cwd = RUN_CWD
    - PREPARE_DIRS = [prepare-*] 하나, SUMS_OK True
    - manifest code_commit = EXEC_COMMIT, dirty False
    - QUALITY.summary.required_all_pass True
  - 하나라도 아니면 STOP한다(사전등록 5·11절). 부분 산출물은 보존한다.
  - 보고: watch_final 운영 값, 자식 stdout·stderr, prepare 디렉터리 이름, MANIFEST_SHA256, SUMS_SHA256, 품질 상태
  - 사용자가 RUN 승인문에 PREPARE_DIR와 MANIFEST_SHA256을 적는다.
- RUN_BUDGET(읽기 전용)
  - MEMORY_COMMAND 1회
  - 보고: 가용 RAM, 고정 예산(RUN 7200 s, 시작 12 GiB, 중단 6 GiB), PREPARE의 운영 측정(elapsed_seconds, peak_job_commit_bytes, min_available_bytes)
  - 운영 측정은 참고 근거일 뿐이다. 예산은 가격·수익률·선별 결과를 보고 조정하지 않는다(사전등록 12절).
- RUN(RUNWATCH 감시, 1회)
  - PRE_EXEC_COMMAND(run) 1회 → RUNWATCH_RUN 1회(백그라운드, 완료 알림 대기) → RUN_REPORT_COMMAND 1회
  - 완료 판단: 다음이 모두 성립해야 한다. 아니면 STOP한다.
    - watcher exit 0, reason COMPLETED, child_exit_code 0, termination VERIFIED
    - limits = 승인값, cwd = RUN_CWD
    - ROOT_ENTRIES = [PREPARE_DIR, run-lock, run-*] 각 하나이고 .tmp-run-* 없음
  - 보고: watch_final 운영 값, 자식 stdout·stderr(상태·경로·해시만 출력됨), run 디렉터리 이름
- INTEGRITY_CHECK(읽기 전용)
  - INTEGRITY_COMMAND 1회
  - 허용: run 디렉터리의 SHA256SUMS.txt 검증, 파일 이름·크기·SHA-256, screen.json 바이트의 SHA-256(해시만 계산하고 내용은 파싱·출력하지 않음), 운영 manifest 필드(study_id, mode, kind, spec_sha256, prereg_sha256, screen_sha256, code_state.commit·dirty, permit.pulls·bars·out_root·requested 범위)
  - 금지: screen.json의 내용(조합·지표·표시·품질 값) 열람
  - run과 prepare의 결속: run manifest에는 prepare manifest 해시가 없다. 이 gate에서는 permit.bars = prepare manifest bars 해시, permit.pulls = 승인 pull, spec_sha256 일치, out_root = CANONICAL_ROOT, code_state.commit = EXEC_COMMIT으로 간접 확인한다. screen.json의 prepare 필드 직접 대조는 RESULT_VIEW 첫 단계에서 한다.
  - 보고: 항목별 True/False, 파일 목록, SCREEN_SHA256. 사용자가 RESULT_VIEW 승인문에 RUN_DIR와 SCREEN_SHA256을 적는다.
- RESULT_VIEW(별도 승인)
  - RESULT_VIEW_COMMAND 1회
  - 값 출력 전 확인: SHA256SUMS 검증, screen.json SHA-256 = SCREEN_SHA256, screen.prepare = {dir_name: PREPARE_DIR, manifest_sha256: MANIFEST_SHA256}. 하나라도 다르면 값을 출력하지 않고 STOP한다.
  - 기본 범위(사전등록 9절 "4개 전략의 표시와 144개 조합 전체를 함께 보고")
    - 144개 조합 전체
    - 4개 전략의 SCREEN_FLAG
    - SCREEN_NOT_EVALUABLE·not_aligned·계산 불가의 사유
    - 품질·표본 조건(evaluation_period, 왕복 수 조건)
  - 채팅 보고는 기준 조합과 4개 전략 표시의 핵심 요약을 앞에 두고, 이어서 144개 조합 전체를 표로 둘 수 있다.
  - 라벨 DESCRIPTIVE_ONLY, FEE_UNCONFIRMED, COSTS_ASSUMED, L1_SCREENING을 함께 적는다. 표시는 판정이 아니며, 수익성 입증·채택·실거래 적합성으로 표현하지 않는다.
  - 결과는 비공개 채팅으로만 보고한다. 파일 쓰기, 커밋, 공개 문서화를 하지 않는다.
- CLOSEOUT_REPORT: 읽기 전용 보존 확인과 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 코드·계약
  - src·tests·configs·docs 변경(ERRATA의 최초 생성 예외 제외), 사전등록·전략·비용·B1·SCREEN_FLAG·품질 기준 변경
  - 새 기능, 추가 전략, DATAQ 구현, 합성 자원 재측정, 비차단 정리(B2–B8)
- 실행
  - 승인 범위 밖 수집, 같은 interval의 두 번째 live 수집
  - 두 번째 real prepare, 다른 root로 prepare 복사
  - run 재실행, 잠금 전 거부 뒤 재시도
  - real 실행에서 --out, --spec-json, --b1-draws, --source fixture 사용
  - RUNWATCH 명령에 외부 timeout 추가(감시 상한은 RUNWATCH의 --max-seconds다)
- 결과
  - RESULT_VIEW 승인 전 screen.json 내용 열람
  - 결과를 본 뒤의 재계산·재선별
  - 결과의 커밋·push·공개
- 데이터: 완료된 pull·prepare·run·RUNWATCH 산출물과 기존 data/ 파일의 수정·삭제·이름 변경
- 네트워크: COLLECT_LIVE 외 전부. fetch, push, PR, merge
- Git: git add의 전체 지정, amend, no-verify, reset, restore, stash, rebase, cherry-pick, 지정 외 checkout·switch·커밋
- 셸: 출력 폐기·리디렉션·분기, 임시 스크립트 파일, guard·hook·settings·권한 규칙·메모리 변경과 우회

## ALLOWED_FILES

ALLOWED_FILES: NONE(tracked 코드·문서 변경 없음)

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/ECON-SCREEN-V06-01-RUN/WORK_ORDER.md(WORKSPACE_SETUP, 승인 바이트로 최초 1회)
- A docs/tasks/ECON-SCREEN-V06-01-RUN/ERRATA-<NNN>.md(PREPARE 전, 승인 바이트로 최초 1회, ACCEPTED만)

## PROTECTED_FILES

PROTECTED_FILES: 저장소의 tracked 파일 전부(위 예외의 최초 생성 제외), data/** 기존 파일

## OUTPUTS

OUTPUTS(모두 ignored인 data/ 아래 새 경로):
- 목록
  - PULL_ROOT/day_KRW-BTC_<UTC stamp>/, PULL_ROOT/hour_KRW-BTC_<UTC stamp>/
  - CANONICAL_ROOT/prepare-<stamp>/(실패 시 .tmp-prepare-<stamp>/)
  - CANONICAL_ROOT/run-lock/, CANONICAL_ROOT/run-<stamp>/(실패 시 .tmp-run-<stamp>/)
  - WATCH_DIR_PREPARE/, WATCH_DIR_RUN/
- 보존 원칙
  - 실행 중 프로그램의 정상 기록은 허용한다: 페이지·상태 파일 기록, watch_state.json 갱신, child_stdout.bin·child_stderr.bin 기록, .tmp-*에서 최종 이름으로의 확정.
  - 각 명령이 끝난 뒤에는 산출물을 수정·삭제·이름 변경하지 않는다.
- 그 밖의 새 파일·untracked·저장소 안 새 ignored 항목은 STOP이다.

## CHECK_COMMANDS

CHECK_COMMANDS(문자열 그대로 단독 호출. 출력 자르기·리디렉션·파이프 없음. <...>만 승인값으로 치환한다):

- RESOLVE_COMMAND (상한 60 s)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data timeout 60 .venv/Scripts/python.exe -I -B -X utf8 - <<'PYEOF'
from moneylab.config import load_settings
s = load_settings()
print("DATA_DIR", s.data_dir.resolve())
print("RAW_DIR", s.raw_dir.resolve())
print("PULL_ROOT", (s.raw_dir / "upbit" / "candles_v06").resolve())
print("ROOT", (s.processed_dir / "econ_screen_v06_01").resolve())
PYEOF

- DRY_RUN_DAY (상한 60 s)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data PYTHONDONTWRITEBYTECODE=1 timeout 60 .venv/Scripts/python.exe -B -m moneylab candles-pull --interval day --market KRW-BTC --start 2017-01-01T00:00:00Z --end 2024-04-01T00:00:00Z --dry-run

- DRY_RUN_HOUR (상한 60 s)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data PYTHONDONTWRITEBYTECODE=1 timeout 60 .venv/Scripts/python.exe -B -m moneylab candles-pull --interval hour --market KRW-BTC --start 2017-01-01T00:00:00Z --end 2024-04-01T00:00:00Z --dry-run

- LIVE_DAY (상한 600 s)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data PYTHONDONTWRITEBYTECODE=1 timeout 600 .venv/Scripts/python.exe -B -m moneylab candles-pull --interval day --market KRW-BTC --start 2017-01-01T00:00:00Z --end 2024-04-01T00:00:00Z --max-pages <MAX_PAGES_DAY>

- LIVE_HOUR (상한 1800 s, 백그라운드)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data PYTHONDONTWRITEBYTECODE=1 timeout 1800 .venv/Scripts/python.exe -B -m moneylab candles-pull --interval hour --market KRW-BTC --start 2017-01-01T00:00:00Z --end 2024-04-01T00:00:00Z --max-pages <MAX_PAGES_HOUR>

- VERIFY_DAY (상한 300 s)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data PYTHONDONTWRITEBYTECODE=1 timeout 300 .venv/Scripts/python.exe -B -m moneylab candles-verify C:/MoneyLab-futval-v8-01-precheck/data/raw/upbit/candles_v06/<DAY_PULL>

- VERIFY_HOUR (상한 300 s)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data PYTHONDONTWRITEBYTECODE=1 timeout 300 .venv/Scripts/python.exe -B -m moneylab candles-verify C:/MoneyLab-futval-v8-01-precheck/data/raw/upbit/candles_v06/<HOUR_PULL>

- PULL_CHECK_COMMAND (상한 600 s)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data timeout 600 .venv/Scripts/python.exe -I -B -X utf8 - C:/MoneyLab-futval-v8-01-precheck/data/raw/upbit/candles_v06/<DAY_PULL> C:/MoneyLab-futval-v8-01-precheck/data/raw/upbit/candles_v06/<HOUR_PULL> <<'PYEOF'
import sys
from datetime import UTC, datetime
from pathlib import Path
from moneylab.providers.upbit.bar_export import econ_screen_pull_checks
KEYS = ("pull_dir_name", "pull_id", "pull_json_sha256", "provenance", "market", "interval", "requested_start",
        "requested_end", "status", "verify_ok", "verify_problems", "reached_earliest", "first_start", "last_start",
        "duplicates_conflicting", "invalid", "duplicates_identical", "excluded_out_of_range",
        "at_or_after_requested_end", "warnings", "read_error")
end = datetime(2024, 4, 1, tzinfo=UTC)
for arg in sys.argv[1:]:
    c = econ_screen_pull_checks(Path(arg), end)
    print({k: c.get(k) for k in KEYS})
PYEOF

- MEMORY_COMMAND (상한 60 s)
cd C:/MoneyLab-futval-v8-01-precheck && timeout 60 .venv/Scripts/python.exe -I -B -X utf8 - <<'PYEOF'
from moneylab.runwatch.winjob import WinPlatform
print("AVAILABLE_BYTES", WinPlatform().available_memory())
PYEOF

- PRE_EXEC_COMMAND (상한 120 s. 첫 인자는 prepare 또는 run. run에서만 네 번째 인자 PREPARE_DIR 경로)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data timeout 120 .venv/Scripts/python.exe -I -B -X utf8 - <prepare|run> C:/MoneyLab-futval-v8-01-precheck/data/raw/upbit/candles_v06/<DAY_PULL> C:/MoneyLab-futval-v8-01-precheck/data/raw/upbit/candles_v06/<HOUR_PULL> [C:/MoneyLab-futval-v8-01-precheck/data/processed/econ_screen_v06_01/<PREPARE_DIR>] <<'PYEOF'
import hashlib
import subprocess
import sys
from pathlib import Path
from moneylab.config import load_settings
from moneylab.runwatch.winjob import WinPlatform
REPO = "C:/MoneyLab-futval-v8-01-precheck"
PREREG = "docs/research_econ_screen_v06_01_preregistration.md"
def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, check=True).stdout
print("HEAD", git("rev-parse", "HEAD").decode().strip())
print("BRANCH", git("branch", "--show-current").decode().strip())
print("STATUS", git("status", "--porcelain=v1", "--untracked-files=all").decode())
print("PREREG_BLOB", hashlib.sha256(git("cat-file", "blob", "HEAD:" + PREREG)).hexdigest())
print("PREREG_FILE", hashlib.sha256((Path(REPO) / PREREG).read_bytes().replace(b"\r\n", b"\n")).hexdigest())
s = load_settings()
root = (s.processed_dir / "econ_screen_v06_01").resolve()
print("DATA_DIR", s.data_dir.resolve())
print("RAW_DIR", s.raw_dir.resolve())
print("ROOT", root)
print("ROOT_ENTRIES", sorted(p.name for p in root.iterdir()) if root.exists() else None)
for arg in sys.argv[2:4]:
    print("PULL", Path(arg).name, hashlib.sha256((Path(arg) / "pull.json").read_bytes()).hexdigest())
if sys.argv[1] == "run":
    prep = Path(sys.argv[4]).resolve()
    print("PREPARE_PARENT_IS_ROOT", prep.parent == root, "NAME", prep.name)
    print("PREPARE_MANIFEST", hashlib.sha256((prep / "manifest.json").read_bytes()).hexdigest())
for name in ("runwatch_econ_screen_v06_01_prepare-a1", "runwatch_econ_screen_v06_01_run-a1"):
    print("WATCH_DIR_EXISTS", name, (s.processed_dir / name).exists())
print("AVAILABLE_BYTES", WinPlatform().available_memory())
PYEOF

- RUNWATCH_PREPARE (백그라운드. 외부 timeout 없음. 감시 상한은 --max-seconds)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -B -m moneylab.runwatch --watch-dir C:/MoneyLab-futval-v8-01-precheck/data/processed/runwatch_econ_screen_v06_01_prepare-a1 --max-seconds 3600 --start-min-available-bytes 12884901888 --abort-below-available-bytes 6442450944 --poll-seconds 10 --verify-seconds 30 --forbid-under C:/MoneyLab-futval-v8-01-precheck/data/processed/econ_screen_v06_01 --forbid-under C:/MoneyLab-futval-v8-01-precheck/data/raw --forbid-under C:/MoneyLab-futval-v8-01-precheck/data/processed/futval_v8_01 -- C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe -B -m moneylab econ-screen-prepare --day-pull C:/MoneyLab-futval-v8-01-precheck/data/raw/upbit/candles_v06/<DAY_PULL> --hour-pull C:/MoneyLab-futval-v8-01-precheck/data/raw/upbit/candles_v06/<HOUR_PULL> --expect-day-pull-sha256 <DAY_PULL_SHA256> --expect-hour-pull-sha256 <HOUR_PULL_SHA256>

- PREPARE_REPORT_COMMAND (상한 300 s. 품질 상태만 출력하고 가격·수익률은 출력하지 않는다)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data timeout 300 .venv/Scripts/python.exe -I -B -X utf8 - C:/MoneyLab-futval-v8-01-precheck/data/processed/econ_screen_v06_01 C:/MoneyLab-futval-v8-01-precheck/data/processed/runwatch_econ_screen_v06_01_prepare-a1 <<'PYEOF'
import hashlib
import json
import sys
from pathlib import Path
from moneylab.backtest import econ_screen as es
root, watch = Path(sys.argv[1]), Path(sys.argv[2])
final = json.loads((watch / "watch_final.json").read_text(encoding="utf-8"))
print("WATCH_FINAL", {k: final.get(k) for k in ("reason", "watcher_exit_code", "child_exit_code", "termination",
      "started_utc", "finished_utc", "elapsed_seconds", "min_available_bytes", "peak_job_commit_bytes", "cwd", "limits")})
for name in ("child_stdout.bin", "child_stderr.bin"):
    print("==", name)
    print((watch / name).read_bytes().decode("utf-8", "replace"))
preps = sorted(p.name for p in root.iterdir() if p.name.startswith(("prepare-", ".tmp-prepare-")))
print("PREPARE_DIRS", preps)
if len(preps) == 1 and preps[0].startswith("prepare-"):
    d = root / preps[0]
    sums = es.verify_output(d)
    print("SUMS_OK", True, "FILES", len(sums))
    print("MANIFEST_SHA256", hashlib.sha256((d / "manifest.json").read_bytes()).hexdigest())
    print("SUMS_SHA256", hashlib.sha256((d / es.SUMS_FILE).read_bytes()).hexdigest())
    man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    cs = man.get("code_state") or {}
    print("MANIFEST", {k: man.get(k) for k in ("study_id", "mode", "kind", "spec_sha256", "prereg_sha256",
          "expected_pull_sha256", "quality_sha256", "created_utc", "python")},
          "code_commit", cs.get("commit"), "dirty", cs.get("dirty"))
    print("BARS", {iv: {k: v.get(k) for k in ("bars", "bars_sha256")} for iv, v in (man.get("bars") or {}).items()})
    q = json.loads((d / "quality.json").read_text(encoding="utf-8"))
    st, bq = q.get("pull_stage") or {}, q.get("bar_quality") or {}
    print("QUALITY", {"summary": q.get("summary"), "Q1": st.get("Q1"),
          "Q6": {iv: (st.get("Q6") or {}).get(iv, {}).get("status") for iv in ("day", "hour")},
          "collection": (st.get("collection") or {}).get("status"), "required": bq.get("required"),
          "evaluation_period": (bq.get("evaluation_period") or {}).get("status")})
PYEOF

- RUNWATCH_RUN (백그라운드. 외부 timeout 없음. 감시 상한은 --max-seconds)
cd C:/MoneyLab-futval-v8-01-precheck && MONEYLAB_DATA_DIR=C:/MoneyLab-futval-v8-01-precheck/data PYTHONDONTWRITEBYTECODE=1 .venv/Scripts/python.exe -B -m moneylab.runwatch --watch-dir C:/MoneyLab-futval-v8-01-precheck/data/processed/runwatch_econ_screen_v06_01_run-a1 --max-seconds 7200 --start-min-available-bytes 12884901888 --abort-below-available-bytes 6442450944 --poll-seconds 10 --verify-seconds 30 --forbid-under C:/MoneyLab-futval-v8-01-precheck/data/processed/econ_screen_v06_01 --forbid-under C:/MoneyLab-futval-v8-01-precheck/data/raw --forbid-under C:/MoneyLab-futval-v8-01-precheck/data/processed/futval_v8_01 -- C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe -B -m moneylab econ-screen-run --prepare C:/MoneyLab-futval-v8-01-precheck/data/processed/econ_screen_v06_01/<PREPARE_DIR> --expect-prepare-manifest-sha256 <MANIFEST_SHA256>

- RUN_REPORT_COMMAND (상한 120 s. 운영 기록만)
cd C:/MoneyLab-futval-v8-01-precheck && timeout 120 .venv/Scripts/python.exe -I -B -X utf8 - C:/MoneyLab-futval-v8-01-precheck/data/processed/econ_screen_v06_01 C:/MoneyLab-futval-v8-01-precheck/data/processed/runwatch_econ_screen_v06_01_run-a1 <<'PYEOF'
import json
import sys
from pathlib import Path
root, watch = Path(sys.argv[1]), Path(sys.argv[2])
final = json.loads((watch / "watch_final.json").read_text(encoding="utf-8"))
print("WATCH_FINAL", {k: final.get(k) for k in ("reason", "watcher_exit_code", "child_exit_code", "termination",
      "started_utc", "finished_utc", "elapsed_seconds", "min_available_bytes", "peak_job_commit_bytes", "cwd", "limits")})
for name in ("child_stdout.bin", "child_stderr.bin"):
    print("==", name)
    print((watch / name).read_bytes().decode("utf-8", "replace"))
print("ROOT_ENTRIES", sorted(p.name for p in root.iterdir()))
PYEOF

- INTEGRITY_COMMAND (상한 300 s. screen.json은 해시만 계산하고 파싱·출력하지 않는다)
cd C:/MoneyLab-futval-v8-01-precheck && timeout 300 .venv/Scripts/python.exe -I -B -X utf8 - C:/MoneyLab-futval-v8-01-precheck/data/processed/econ_screen_v06_01 <RUN_DIR> <PREPARE_DIR> <EXEC_COMMIT> <DAY_PULL_SHA256> <HOUR_PULL_SHA256> <<'PYEOF'
import hashlib
import json
import sys
from pathlib import Path
from moneylab.backtest import econ_screen as es
root = Path(sys.argv[1])
run_dir, prep_dir, commit, day_sha, hour_sha = sys.argv[2:7]
d, p = root / run_dir, root / prep_dir
sums = es.verify_output(d)
print("SUMS_OK", True)
for name, sha in sorted(sums.items()):
    print("FILE", name, (d / name).stat().st_size, sha)
screen_sha = hashlib.sha256((d / "screen.json").read_bytes()).hexdigest()
print("SCREEN_SHA256", screen_sha)
man = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
pman = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
permit = man.get("permit") or {}
cs = man.get("code_state") or {}
checks = {
    "study_mode_kind": (man.get("study_id"), man.get("mode"), man.get("kind")) == (es.STUDY_ID, "real", "run"),
    "screen_sha256": man.get("screen_sha256") == screen_sha,
    "code_commit": cs.get("commit") == commit and cs.get("dirty") is False,
    "prereg_sha256": man.get("prereg_sha256") == es.PREREGISTRATION_SHA256,
    "spec_sha256": man.get("spec_sha256") == pman.get("spec_sha256"),
    "out_root": permit.get("out_root") == str(root.resolve()),
    "pulls": sorted((iv, sha) for iv, _pid, sha in permit.get("pulls") or []) == [("day", day_sha), ("hour", hour_sha)],
    "bars": sorted(tuple(b) for b in permit.get("bars") or []) == sorted((iv, v["bars_sha256"]) for iv, v in pman["bars"].items()),
    "range": (permit.get("requested_start"), permit.get("requested_end")) == ("2017-01-01T00:00:00Z", "2024-04-01T00:00:00Z"),
    "root_entries": sorted(x.name for x in root.iterdir()) == sorted([prep_dir, "run-lock", run_dir]),
}
for k, v in checks.items():
    print("CHECK", k, v)
PYEOF

- RESULT_VIEW_COMMAND (상한 300 s. 선행 대조가 모두 통과한 뒤에만 값을 출력한다)
cd C:/MoneyLab-futval-v8-01-precheck && timeout 300 .venv/Scripts/python.exe -I -B -X utf8 - C:/MoneyLab-futval-v8-01-precheck/data/processed/econ_screen_v06_01 <RUN_DIR> <SCREEN_SHA256> <PREPARE_DIR> <MANIFEST_SHA256> <<'PYEOF'
import hashlib
import json
import sys
from pathlib import Path
from moneylab.backtest import econ_screen as es
root = Path(sys.argv[1])
run_dir, screen_sha, prep_dir, man_sha = sys.argv[2:6]
d = root / run_dir
es.verify_output(d)
raw = (d / "screen.json").read_bytes()
if hashlib.sha256(raw).hexdigest() != screen_sha:
    raise SystemExit("STOP: screen.json SHA-256 differs from the approved value; nothing printed")
screen = json.loads(raw.decode("utf-8"))
if screen.get("prepare") != {"dir_name": prep_dir, "manifest_sha256": man_sha}:
    raise SystemExit("STOP: screen.json prepare binding differs; nothing printed")
print("LABELS", screen.get("labels"), "EVIDENCE", screen.get("evidence"))
print("COMBINATIONS_COUNT", screen.get("combinations_count"), "P_VALUES", screen.get("p_values"), "VERDICT", screen.get("verdict"))
print("FLAGS", json.dumps(screen.get("flags"), ensure_ascii=False, sort_keys=True))
print("QUALITY", json.dumps(screen.get("quality"), ensure_ascii=False, sort_keys=True))
for c in screen.get("combinations") or []:
    print("COMBO", json.dumps(c, ensure_ascii=False, sort_keys=True))
PYEOF

- 공통
  - real 실행에 --out, --source, --spec-json, --b1-draws를 지정하지 않는다. 기본값은 real 모드와 정규 root다.
  - 자식 프로세스는 RUNWATCH의 환경(MONEYLAB_DATA_DIR 포함)과 cwd(RUN_CWD)를 상속한다.
  - 명령 상한 도달은 STOP이다.

## BUDGET

BUDGET(고정값. 승인문에 같은 값을 적는다):
- PREPARE: --max-seconds 3600, --start-min-available-bytes 12884901888(12 GiB), --abort-below-available-bytes 6442450944(6 GiB)
- RUN: --max-seconds 7200, RAM 하한은 PREPARE와 같음
- RUNWATCH --poll-seconds 10, --verify-seconds 30
- 근거와 한계
  - 근거: 총 RAM 약 31.2 GiB 기록, 합성 측정(Python heap만, prepare·재검증·출력 미포함)
  - PREPARE의 운영 측정은 RUN 예산 승인의 참고 근거일 뿐이다.
  - 예산은 가격·수익률·선별 결과를 보고 조정하지 않는다(사전등록 12절).
- RUNWATCH 상한의 의미
  - 상한은 중단 판단 기준이다. poll 10 s는 명목 조회 간격이며, OS 스케줄링·조회·종료 지연 때문에 실제 중단은 상한보다 더 늦어질 수 있다.
  - verify 30 s는 종료 확인을 기다리는 시간이며, 전체 종료 시간의 독립된 강제 상한이 아니다.
  - poll 사이의 순간 메모리 저점은 관측되지 않을 수 있다.
- 수집: 페이지 상한 = 승인 MAX_PAGES, HTTP 요청 ≤ 3 × MAX_PAGES. 429에서 긴 대기를 요구받으면 재시도하지 않는다.
- 시간 상한, 메모리 중단, 감시 실패, 페이지 상한 도달은 STOP이며 자동 재실행하지 않는다.
- 도구 호출: gate당 최대 30회

## PRESERVATION_CHECK

PRESERVATION_CHECK:
- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): GIT_HOST_WORKTREE의 다음 원문 전체(표지 F0RUN)
  - for-each-ref --sort=refname --format="%(refname) %(objectname)"
  - worktree list --porcelain
  - rev-parse HEAD HEAD^{tree}
  - status --porcelain=v1 --untracked-files=all --ignored=matching
- ref 분류
  - TASK: refs/heads/codex/econ-screen-v06-01-run(생성 -> C1 -> Ce)
  - OBSERVED: refs/codex/turn-diffs/checkpoints/**
  - PRESERVE: 그 밖 전부. 다음을 포함한다.
    - refs/heads/codex/econ-screen-v06-01-impl-03와 refs/remotes/origin/codex/econ-screen-v06-01-impl-03 = 3b34ece3da58dd0cc4099da92238da9d17e83590
    - refs/heads/codex/econ-screen-v06-01-impl-02 = 281e0948d24db3d264c80807af56b252748b5ae8
    - refs/heads/codex/econ-screen-v06-01-impl = bd6e7400ed79ff426aa19c4b8d45e474ae7e1ee2
    - refs/heads/codex/econ-screen-v06-01 = de22c19d97afa7cb9312e3bf294e7fc29242ad5c
    - refs/heads/codex/runwatch-01 = a3197059f0c1bc41e41ba0d2c7700836cb795645
    - refs/heads/codex/futval-v8-01-run와 그 원격 ref = c3d98eda9b969875f8eb7b05eb24ce3301e2dbd4
- worktree: TARGET_WORKTREE를 제외하고 항목 단위로 비교한다.
- host: HEAD·tree·status = F0
- data: 진입 목록의 파일 이름·크기·SHA-256이 변하지 않는다. 새 파일은 OUTPUTS 경로 아래에만 생긴다.
- 비교 시점: WORKSPACE_SETUP·PREPARE·RUN·INTEGRITY_CHECK 종료, CLOSEOUT_REPORT

## EXPECTED_ASK

EXPECTED_ASK(guard 규칙 기준. 실제 발생은 보장하지 않음):
- WORKSPACE_SETUP: task-contract(Work Order 최초 Write) 최대 1회, git-commit 1회
- ERRATA(PREPARE 전, 있을 때만): task-contract 1회, git-commit 1회
- COLLECT_LIVE: 0(guard 규칙 없음. 채팅 승인이 통제다)
- 나머지 gate: 0
- 그 밖의 ASK·거절·무응답·DENY는 STOP

## REQUIRED_REPORT

REQUIRED_REPORT:
- gate별 HEAD·tree·branch·status(ignored 포함), PRE_EXEC_CHECK 항목별 결과
- 수집: 명령 인자, 페이지 수, HTTP 상태 요약, 디렉터리 이름, pull_id, pull.json SHA-256, verify 결과
- PREPARE·RUN: watch_final 운영 값(reason, exit, termination, elapsed, peak, min available, limits), 자식 stdout·stderr, 산출 디렉터리 이름, 해시
- PREPARE 품질 상태, INTEGRITY 항목별 결과(결과 내용 없음)
- RESULT_VIEW: 기본 범위 전체, 핵심 요약, 라벨과 한계. 비공개 채팅만
- PRESERVATION_CHECK 분류별 결과
- 증거 등급(GIT_VERIFIABLE, CLAUDE_REPORTED, INDEPENDENT), GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, <GATE>_PASS, READY_FOR_<NEXT>

## STOP_CONDITIONS

STOP_CONDITIONS:
- 진입·실행 상태: HEAD·tree·branch·EXEC_COMMIT 불일치, clean 아님, 사전등록·Work Order 해시 불일치, 해석 경로 불일치, 대상 경로가 이미 있음, ENTRY_PRECONDITION 미충족
- 수집: HTTP 451·403·401, 페이지 상한 오류, 비정상 exit, status ≠ complete, candles-verify 실패, 수집 범위 미확정(사전등록 3절), 실행 금지 시간대
- 품질: 필수 Q INVALID·NOT_EVALUATED, Bar 변환 거부, prepare 완료 판단 미충족
- run: 잠금 전 거부, 잠금 후 실패, run 완료 판단 미충족(시간·메모리·감시 실패, termination ≠ VERIFIED 포함)
- 무결성: SHA256SUMS 불일치, CHECK 항목 False, 기대 외 파일
- 결과 열람: screen.json 해시 또는 prepare 결속 불일치
- 계약: 구현과 사전등록의 불일치, 계산 오류, 미커밋 코드(사전등록 11절)
- 보존: PRESERVE ref·worktree·host·data 변화, OUTPUTS 밖 새 파일
- 도구: guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- 모든 STOP 뒤 재시도·기준 변경은 하지 않는다. 새 결정은 새 승인으로 한다.

## FOLLOW_UP_PLAN

FOLLOW_UP_PLAN(이 Work Order의 승인 범위가 아니다):
- 결과 공개 여부와 범위, 결과 기록 문서화 여부
- 후속 확증 연구는 이 study가 평가에 쓰지 않은 구간으로만 하며, 시도 수 4와 선택 사실을 남긴다(사전등록 10절).
- 비차단 사항 B2–B8 정리는 별도 계약으로 한다.
