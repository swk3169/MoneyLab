# Work Order: ECON-SCREEN-V06-02 — 후속 study 사전등록 최초 고정

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 docs/tasks/ECON-SCREEN-V06-02/ERRATA-<NNN>.md(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: ECON-SCREEN-V06-02
TASK_ID: ECON-SCREEN-V06-02
TITLE: ECON-SCREEN-V06-02 사전등록 최초 고정
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: bee1d2e3b3f0863c3a82a6bc2221914cf8a066ab (branch codex/econ-screen-v06-01-run, 01 RUN C1. 01은 COLLECT_LIVE STOP으로 중단 종결)
CANONICAL_BASE_TREE: e72b52c79542bb580587c491b7ef9b6f2ffda9f9
ENTRY_HEAD: bee1d2e3b3f0863c3a82a6bc2221914cf8a066ab (branch codex/econ-screen-v06-01-run)
ENTRY_TREE: e72b52c79542bb580587c491b7ef9b6f2ffda9f9
TARGET_BRANCH: codex/econ-screen-v06-02
TARGET_WORKTREE: C:/MoneyLab-futval-v8-01-precheck (재사용)
WORKSPACE_METHOD_EXCEPTION: 이 task의 WORKSPACE_SETUP에 한해 TARGET_WORKTREE에서 CANONICAL_BASE_SHA를 기준으로 git switch -c codex/econ-screen-v06-02를 1회 실행한다. 다른 task에 적용되지 않는다.
GIT_HOST_WORKTREE: C:/MoneyLab-gov-automation-03
PYTHON: C:/MoneyLab-futval-v8-01-precheck/.venv/Scripts/python.exe (재사용. 설치·갱신 없음)
PREREGISTRATION_PATH: docs/research_econ_screen_v06_02_preregistration.md
PREREGISTRATION_SHA256: c6bd5e7eb0bcd8d44e668a9289ea67dafc97462063003cc1f9d183c18f092f81
PREREGISTRATION_BYTES: 20011
PREREGISTRATION_LF: 194
PREVIOUS_STUDY: ECON-SCREEN-V06-01(사전등록 SHA-256 2ff766fa8e60adbc107b1ffe9ae4df30c455b616cd5345154704ff928b74705d, RUN Work Order C1 bee1d2e3b3f0863c3a82a6bc2221914cf8a066ab, 중단 종결). 그 사전등록·Work Order·STOP·중단 종결 기록은 바꾸지 않는다.
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: NOT_APPLICABLE
REQUIRED_CI_CHECKS: NOT_APPLICABLE
BUNDLE_ELIGIBLE: NO
EVIDENCE: 문서 고정 작업이다. 데이터·계산·결과가 없다.

## GATE_SEQUENCE

GATE_SEQUENCE: CONTRACT_REVIEW -> WORKSPACE_SETUP -> PREREGISTRATION_FREEZE -> CLOSEOUT_REPORT

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- gate마다 별도 승인이 필요하며 묶지 않는다. gate 보고 뒤 멈춘다.
- 승인 형식
  - WORKSPACE_SETUP: GATE_AUTHORIZATION: ECON-SCREEN-V06-02 WORKSPACE_SETUP WO_SHA256=<64 hex> WO_BYTES=<n> WO_LF=<n>
  - PREREGISTRATION_FREEZE: GATE_AUTHORIZATION: ECON-SCREEN-V06-02 PREREGISTRATION_FREEZE WO@<C1> PREREG_SHA256=c6bd5e7eb0bcd8d44e668a9289ea67dafc97462063003cc1f9d183c18f092f81 PREREG_BYTES=20011 PREREG_LF=194
  - 그 밖: GATE_AUTHORIZATION: ECON-SCREEN-V06-02 <GATE> WO@<C1>
- 프로젝트 저장소의 커밋은 C1(WORKSPACE_SETUP)과 C2(PREREGISTRATION_FREEZE) 각 1회만 허용한다.
- 사전등록의 효력은 C2가 완료되는 시점에 생긴다. 이 Work Order는 구현·검증·수집·계산 권한을 만들지 않는다.
- 이 Work Order는 TASK_COMPLETE를 선언하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES:
- 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md)이 우선한다. 충돌하면 STOP한다.
- 01 사전등록은 01의 수행·중단·기록에 적용하며, 이 작업에서 변경하지 않는다.
- 02는 별도 study다. C2 고정 이후에는 수락한 02 사전등록이 02에 적용된다.
- 이 문서 고정 작업은 01의 재시도나 연구 재개를 승인하지 않는다. 01 사전등록의 재시도 금지 등 01의 조항은 02 문서 고정 자체를 막는 근거로 적용하지 않는다.
- 실거래·주문·지갑·키·자금은 범위 밖이다.

## GOAL

GOAL: 사용자가 수락한 ECON-SCREEN-V06-02 사전등록 바이트(PREREGISTRATION_SHA256)를 PREREGISTRATION_PATH에 최초 1회 고정한다. 01의 기록·원본·실패 pull은 보존한다.

## PREREGISTRATION_SOURCE

PREREGISTRATION_SOURCE(승인 바이트 재현 규칙):
- 출처: 이 세션 기록의 도구 결과 중 "=====FINAL_PREREG_BODY_BEGIN====="와 "=====FINAL_PREREG_BODY_END=====" 표식을 가진 출력 1개
- 표식은 줄 단위로 식별한다. 줄 끝 CR 하나를 무시한 내용이 표식 문자열과 정확히 같은 줄만 표식이다.
- 표식 줄을 제외한 사이의 줄만 본문으로 취한다. CRLF만 LF로 정규화한다. 단독 CR이 있으면 STOP한다.
- 본문의 문자·공백은 바꾸지 않고 끝 LF를 정확히 1개로 한다. 이전 후보에 치환을 다시 적용하지 않는다.
- 표식 쌍이 하나가 아니면 STOP한다.
- 재현 결과의 SHA-256·바이트 수·LF 수가 PREREGISTRATION_SHA256·BYTES·LF와 모두 같을 때만 작성한다.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP
  - F0 출력(PRESERVATION_CHECK, 상태 변경 전 첫 호출)
  - 진입 확인
    - HEAD·tree·branch = ENTRY, clean
    - TARGET_BRANCH, docs/tasks/ECON-SCREEN-V06-02, PREREGISTRATION_PATH, data/processed/econ_screen_v06_02 부재
    - 01 사전등록 blob 내용 SHA-256 = 2ff766fa8e60adbc107b1ffe9ae4df30c455b616cd5345154704ff928b74705d
    - data/ 파일의 이름·크기·SHA-256 목록(내용은 열지 않음)
  - git -C C:/MoneyLab-futval-v8-01-precheck switch -c codex/econ-screen-v06-02 bee1d2e3b3f0863c3a82a6bc2221914cf8a066ab 1회
  - Work Order를 승인 바이트로 Write 1회, 작성 파일의 SHA-256·바이트·LF 대조
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/tasks/ECON-SCREEN-V06-02/WORK_ORDER.md 1회
  - 커밋 전 확인: staged 경로 = Work Order 하나, staged 내용 SHA-256 = WO_SHA256, git diff --cached --check exit 0
  - C1 커밋 1회
  - C1 확인: parent = CANONICAL_BASE_SHA 하나, 변경 = A docs/tasks/ECON-SCREEN-V06-02/WORK_ORDER.md 하나, C1 blob = 승인 바이트, clean
  - 종료 시 PRESERVATION_CHECK
- PREREGISTRATION_FREEZE(진입: HEAD = C1, clean, PREREGISTRATION_PATH 부재)
  - PREREGISTRATION_SOURCE 규칙으로 재현하고 해시·바이트·LF 대조(읽기 전용 1회)
  - 일치할 때만 사전등록을 승인 바이트로 Write 1회, 작성 파일의 SHA-256·바이트·LF·CR 0 대조
  - git -C C:/MoneyLab-futval-v8-01-precheck add -- docs/research_econ_screen_v06_02_preregistration.md 1회
  - 커밋 전 확인: staged 경로 = 사전등록 하나, staged 내용 SHA-256 = PREREGISTRATION_SHA256, git diff --cached --check exit 0
  - C2 커밋 1회
  - C2 확인: parent = C1 하나, 변경 = A docs/research_econ_screen_v06_02_preregistration.md 하나, C2 blob SHA-256·바이트 = 승인값, clean
  - 01 사전등록·Work Order 파일이 C2 tree에서 CANONICAL_BASE_SHA와 같음
  - 종료 시 PRESERVATION_CHECK
- CLOSEOUT_REPORT: 읽기 전용 보존 확인과 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 범위 밖 작업: 파서 보완·study 식별 연결 등 코드 변경, incident 작성, 일봉 재사용 검증, candles-verify, 시간봉 수집, prepare·run, 경제성 계산, 테스트·측정
- 데이터: 원본·실패 pull·기존 산출물의 열람·수정·삭제·이름 변경
- 계약: 01 사전등록·01 Work Order·이 Work Order의 수정, 수락 문안의 재작성·치환
- 네트워크: 전부. fetch, push, PR, merge
- Git: git add의 전체 지정, amend, no-verify, reset, restore, stash, rebase, cherry-pick, 지정 외 checkout·switch·커밋
- 셸: 출력 폐기·리디렉션·분기, 임시 스크립트 파일, guard·hook·settings·권한 규칙·메모리 변경과 우회

## ALLOWED_FILES

ALLOWED_FILES: NONE(아래 예외의 최초 생성만)

## CONTRACT_FILE_EXCEPTION

CONTRACT_FILE_EXCEPTION:
- A docs/tasks/ECON-SCREEN-V06-02/WORK_ORDER.md(WORKSPACE_SETUP, 승인 바이트로 최초 1회)
- A docs/research_econ_screen_v06_02_preregistration.md(PREREGISTRATION_FREEZE, 승인 바이트로 최초 1회)

## PROTECTED_FILES

PROTECTED_FILES: 저장소의 tracked 파일 전부(위 예외의 최초 생성 제외), data/** 전부

## COMMIT_PLAN

COMMIT_PLAN:
- C1(WORKSPACE_SETUP): parent = CANONICAL_BASE_SHA, A docs/tasks/ECON-SCREEN-V06-02/WORK_ORDER.md, 메시지 docs(task): add ECON-SCREEN-V06-02 work order
- C2(PREREGISTRATION_FREEZE): parent = C1, A docs/research_econ_screen_v06_02_preregistration.md, 메시지 docs(research): add ECON-SCREEN-V06-02 preregistration
- 본문·trailer 없음. CANONICAL_BASE_SHA..C2 변경 경로는 위 두 파일뿐이다.
- 커밋 이후 수정·실패는 STOP이며 후퇴하지 않는다.

## UNTRACKED_AND_IGNORED

UNTRACKED_AND_IGNORED:
- 예상 untracked: 각 gate에서 Write 뒤 add 전까지의 해당 파일 1개. 그 밖은 STOP이다.
- 저장소 안 새 ignored 항목은 금지한다(.venv 내부 갱신만 허용).

## PRESERVATION_CHECK

PRESERVATION_CHECK:
- F0(WORKSPACE_SETUP 첫 호출, 상태 변경 전): GIT_HOST_WORKTREE의 for-each-ref --sort=refname --format="%(refname) %(objectname)", worktree list --porcelain, rev-parse HEAD HEAD^{tree}, status --porcelain=v1 --untracked-files=all --ignored=matching 원문 전체(표지 F0V0602)
- ref 분류
  - TASK: refs/heads/codex/econ-screen-v06-02(생성 -> C1 -> C2)
  - OBSERVED: refs/codex/turn-diffs/checkpoints/**(기록만)
  - PRESERVE: 그 밖 전부. 하나라도 변하면 STOP한다. 다음을 포함한다.
    - refs/heads/codex/econ-screen-v06-01-run = bee1d2e3b3f0863c3a82a6bc2221914cf8a066ab
    - refs/heads/codex/econ-screen-v06-01-impl-03와 refs/remotes/origin/codex/econ-screen-v06-01-impl-03 = 3b34ece3da58dd0cc4099da92238da9d17e83590
    - refs/heads/codex/econ-screen-v06-01-impl-02 = 281e0948d24db3d264c80807af56b252748b5ae8
    - refs/heads/codex/econ-screen-v06-01-impl = bd6e7400ed79ff426aa19c4b8d45e474ae7e1ee2
    - refs/heads/codex/econ-screen-v06-01 = de22c19d97afa7cb9312e3bf294e7fc29242ad5c
    - refs/heads/codex/runwatch-01 = a3197059f0c1bc41e41ba0d2c7700836cb795645
    - refs/heads/codex/futval-v8-01-run와 그 원격 ref = c3d98eda9b969875f8eb7b05eb24ce3301e2dbd4
- worktree: TARGET_WORKTREE를 제외하고 항목 단위로 비교한다. TARGET_WORKTREE의 기대 변화는 branch 전환과 HEAD가 C1·C2로 가는 것뿐이다.
- host: HEAD·tree·status = F0
- data: 진입 목록(01 pull 2개 포함)의 파일 이름·크기·SHA-256이 같고 새 파일이 없다.
- 비교 시점: WORKSPACE_SETUP 종료, PREREGISTRATION_FREEZE 종료, CLOSEOUT_REPORT

## EXPECTED_ASK

EXPECTED_ASK(guard 규칙 기준. 실제 발생은 보장하지 않음):
- WORKSPACE_SETUP: task-contract(Work Order 최초 Write) 최대 1회, git-commit 1회
- PREREGISTRATION_FREEZE: 사전등록 경로 최초 Write에 대한 guard·settings 확인 최대 1회, git-commit 1회
- CLOSEOUT_REPORT: 0
- 그 밖의 ASK·거절·무응답·DENY는 STOP

## REQUIRED_REPORT

REQUIRED_REPORT:
- gate별 HEAD·parent·tree·branch, 변경 경로, staged·commit blob 대조, status(ignored 포함)
- 재현 출처(도구 결과 위치), 표식 줄 위치, CRLF·단독 CR 수, 해시·바이트·LF 일치 여부
- PRESERVATION_CHECK 분류별 결과
- 증거 등급(GIT_VERIFIABLE, CLAUDE_REPORTED, INDEPENDENT), GUARD_EVENTS, DEVIATIONS, PROPOSED_ERRATA, <GATE>_PASS, READY_FOR_<NEXT>

## STOP_CONDITIONS

STOP_CONDITIONS:
- 진입 상태: ENTRY·base·tree·branch 불일치, clean 아님, 대상이 미리 있음, 01 사전등록 해시 불일치
- 바이트: 재현·작성·staged·commit 중 하나라도 승인값과 불일치, 표식 쌍이 하나가 아님, 단독 CR
- 범위: 예외 밖 변경, 보호 경로 변경, 예상 밖 untracked, 저장소 안 새 ignored 항목
- 보존: PRESERVE ref·worktree·host·data 변화
- 도구: guard deny, 예상 밖 ASK, 권한 거절·무응답, 셸·도구 오류, 결과 불명
- 기타: 상위 규칙과 충돌
- STOP 뒤 변형 재시도는 하지 않는다.

## FOLLOW_UP_PLAN

FOLLOW_UP_PLAN(이 Work Order의 승인 범위가 아니다. 각각 별도 계약·승인):
- 구현 계약(사전등록 13절 2단계)
  - timestamp null 보존: 키가 있고 null일 때만 None, 그 밖의 형식은 거부. warnings 사유 기록, pull 보고 키 불변
  - bar_quality의 보고 전용 last_tick_missing
  - study 식별 연결: STUDY_ID, PREREGISTRATION_PATH, PREREGISTRATION_SHA256 = C2의 사전등록 해시, REAL_ROOT_NAME = econ_screen_v06_02
  - 합성 회귀 시험, incident 기록 1건
- 실행 계약: 일봉 재사용 검증(오프라인), 시간봉 dry-run과 live 1회, 품질 확인, 예산, 선별 1회, 무결성 확인, 별도 결과 열람
- 공개 백업 여부는 따로 결정한다.
