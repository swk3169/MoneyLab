# ERRATA: GOV-AUTOMATION-03 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: GOV-AUTOMATION-03-ERRATA-001
TASK_ID: GOV-AUTOMATION-03
TARGET_WORK_ORDER: docs/tasks/GOV-AUTOMATION-03/WORK_ORDER.md @ b0b1855ce5c30a233d836b816cea5a4f62c38f87 (sha256 c0e6d7729430cedb6854e778a5bc65bd29911273114d77b5974049a45600ae72)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자 (최종 발행 승인 시 확정)

## CHANGED_FIELDS

CHANGED_FIELDS:
- DESIGN_CONTRACT.D6 "미종결 단계" 항목 (그 항목만 대체)
- DESIGN_CONTRACT.D6 "거부 조건과 무관하게 허용하는 예외(이 목록이 전부다)" 항목 (그 항목만 대체)
- DESIGN_CONTRACT.D6 phase 전이 중 "TERMINAL이 아닌 모든 phase→TERMINAL(STOPPED, code)" 줄 (그 줄만 대체)
- TEST_GATES "세션" 항목 (그 항목만 대체)
- TEST_GATES "ERRATA-001 회귀 테스트" 항목 (신설)
- TEST_GATES "ERRATA-001 경로 회귀 테스트" 항목 (신설)
- GATE_TRANSITION_RULES (항목 추가)
- PROTECTED_FILES (항목 추가)
- CONTRACT_FILE_EXCEPTION (항목 추가)
- COMMIT_PLAN (전체 대체)

## RATIONALE

RATIONALE:
- PRECOMMIT_AUDIT F-1: D6는 이전 nonce의 미종결 단계를 UNKNOWN_STEP으로 정의하지만, nonce를 바꾸는 RESUME은 미종결 단계가 있으면 거부된다. 그래서 새 세션은 남은 단계를 결과 불명으로 식별할 수 없고, 허용되어야 할 STOPPED 종결도 STEP_OPEN으로 막힌다. 남는 길은 결과 불명 단계를 ok·fail로 닫는 것뿐인데, 그것은 금지되어 있다.
- 결정: RESUME 거부는 유지한다. 미종결 단계가 있어도 TERMINAL(STOPPED) 종결 기록 하나만 허용한다.
- PRECOMMIT_AUDIT F-2: TEST_GATES의 단계 조건과 전이 조건에 대응하는 테스트가 부족했다.
- 정적 대조 F-3: D4는 경로의 모든 구성 요소가 링크·재분석 지점이 아니어야 한다고 정한다. 그런데 LEASE·REVOKED·pr_text.md의 최종 구성 요소는 읽을 때 링크 검사 없이 따라가고, 깨진 링크는 없는 경로로 취급된다. D4 문언은 바꾸지 않고, 구현과 테스트로 보완한다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- D6 "미종결 단계":
  - 미종결 단계는 STEP_START가 있고 대응하는 STEP_END가 없는 단계다.
  - 현재 nonce로 시작한 미종결 단계(진행 중):
    - 그 단계를 실제로 수행하고 결과를 관측한 세션만 같은 nonce로 end(ok|fail)를 기록한다. 같은 nonce라는 사실만으로 결과를 관측하지 않은 단계를 ok·fail로 닫지 않는다.
    - session_nonce는 인증 수단이 아니며 원장에서 읽을 수 있다. taskctl은 명령을 제출한 실제 세션도, 그 세션이 결과를 관측했는지도 인증하지 못한다. 결과를 관측한 세션만 end를 기록한다는 조건은 Agent가 지켜야 하는 협조 규칙이다. 이 ERRATA는 인증 기능이나 실행 권한을 추가하지 않는다.
    - 새 start는 STEP_OPEN으로 거부한다. TERMINAL(STOPPED)이 아닌 phase-set도 STEP_OPEN으로 거부한다.
    - TERMINAL(STOPPED)은 이 상태에서도 허용한다. 이때 그 단계는 결과 불명으로 남는다.
  - 이전 nonce로 시작한 미종결 단계: UNKNOWN_STEP이다. RESUME과 모든 상태 변경을 거부한다. 예외는 아래 예외 목록뿐이다.
  - RESUME은 미종결 단계가 하나라도 있으면 거부한다. nonce 교체, 작업 재개, 재실행 권한은 추가하지 않는다.
  - 결과 불명 단계의 복구와 재실행은 첫 버전 범위 밖이다.
- D6 "거부 조건과 무관하게 허용하는 예외(이 목록이 전부다)":
  - status, verify-ledger, check --read-only, publish-draft: 항상 허용한다.
  - revoke: 항상 허용한다.
  - lease-clear: LEASE가 있고 원장이 유효할 때 허용한다.
  - 현재 nonce로 시작한 진행 중 단계의 step end(ok|fail): REVOKED·만료 상태에서도 허용한다. phase TERMINAL에서는 거부한다.
  - `phase-set --to TERMINAL --terminal-status STOPPED --code <CODE>`:
    - 조건: 원장이 유효하고, phase가 TERMINAL이 아니며, LEASE가 없다.
    - REVOKED·만료·UNKNOWN_STEP·STEP_OPEN 상태에서도 허용한다. 미종결 단계의 nonce와는 관계없다.
    - 기록은 PHASE 이벤트 1개뿐이다. 기존 STEP_START와 nonce는 그대로 둔다. STEP_END(ok·fail)를 합성하지 않고, nonce를 교체하지 않는다.
    - 원장 재생에서 TERMINAL PHASE 이벤트 앞에 STEP_END 없이 남은 STEP_START는 결과 불명이다.
    - 종결 사유는 PHASE 이벤트의 code로 기록한다(예: UNKNOWN_STEP, REVOKED, EXPIRED, OPERATOR_STOP).
    - 이벤트 스키마는 바꾸지 않는다. PHASE payload는 {from, to:"TERMINAL", terminal_status:"STOPPED", code, violations:null}이다.
    - STOPPED 종결은 재개, 재실행, LEASE 제거·복구·정리 권한을 만들지 않는다.
- D6 phase 전이 "TERMINAL(STOPPED)" 줄:
  - TERMINAL이 아닌 모든 phase→TERMINAL(STOPPED, code)는 위 예외 목록의 조건에서 허용한다.
  - TERMINAL 이후에는 조회 명령과 revoke 외의 모든 명령을 TERMINAL로 거부한다. 거부 대상: step start, step end(ok·fail), phase-set, record-message, pr-text, lease-clear.
  - COMPLETE와 CLOSED_WITH_VIOLATION은 미종결 단계가 없을 때만 허용한다(기존과 같다).
- 계속 금지: 결과 불명 단계를 ok·fail로 닫는 것, 결과 불명 단계의 재실행, 미종결 단계가 있는 상태의 RESUME, 종결 뒤의 재개와 성공 종결, STOPPED 기록을 위한 LEASE 제거·복구·정리.
- TEST_GATES "세션":
  - 진행 중 단계의 STEP_END는 같은 nonce에서만 허용한다. 다른 nonce의 end는 SESSION_MISMATCH로 거부한다.
  - 이와 별도로, 위 예외 목록의 조건에 따른 TERMINAL(STOPPED) 종결을 허용한다.
  - 같은 nonce라는 사실이 결과 불명 단계를 ok·fail로 닫을 권한을 만들지는 않는다.
  - 미종결 단계가 있으면 RESUME을 UNKNOWN_STEP(exit 4)으로 거부한다.
  - 미종결 단계가 있어도 TERMINAL(STOPPED)을 기록할 수 있다. 이때 원장에는 해당 STEP_START가 STEP_END 없이 남는다.
  - 종결 후 step end(ok·fail), step start, RESUME, phase-set은 TERMINAL로 거부된다.
- TEST_GATES "ERRATA-001 회귀 테스트":
  - 모든 파일·커밋·ref 생성은 tmp_path의 임시 Git 저장소에서만 한다. 대상 저장소의 파일·커밋·ref는 만들거나 바꾸지 않는다.
  - 각 항목은 아래 입력에 대해 기대 코드와 원장 상태를 검증한다. 테스트 이름만으로 충족을 판정하지 않는다.
  - T1: init 후 SETUP_ENV start → C1 위에 커밋 1개 추가 → end ok. 기대 HEAD_MISMATCH.
  - T2: init 후 SETUP_ENV start → ALLOWED_FILES의 새 파일 작성 → end ok. 기대 NOT_CLEAN.
  - T3: SETUP_DONE에서 IMPLEMENT 완료 → LOCAL_AUDIT start → ALLOWED_FILES 파일 수정 → end ok. 기대 STATE_CHANGED. 같은 단계를 end fail로 기록하면 OK.
  - T4: LOCAL_COMMIT 완료 → CLEAN_E2E start → ALLOWED_FILES 파일 수정 → end ok. 기대 STATE_CHANGED.
  - T5: LOCAL_COMMIT 완료 → CLEAN_E2E start → ALLOWED_FILES 밖 untracked 파일 생성 → end ok. 기대 UNTRACKED.
  - T6: PUBLISHING에서 PUSH start → ALLOWED_FILES 파일 수정 → end ok(remote pushed_head=I). 기대 STATE_CHANGED.
  - T7: PUSH·PR_CREATE·CI_WAIT·PREMERGE_CHECK ok → MERGE start → ALLOWED_FILES 파일 수정 → end ok(올바른 remote). 기대 STATE_CHANGED.
  - T8: MERGED에서 origin/main을 BASE로 둔 채 POST_MERGE_AUDIT start → end ok(merge_sha=M, merge_tree_recomputed=TREE). 기대 PUBLISH_MISMATCH.
  - T9: parents가 [I, BASE]인 merge M2를 만들고, MERGE를 remote merge_sha=M2, merge_parents=BASE,I로 ok 기록 → origin/main=M2 → POST_MERGE_AUDIT end ok. 기대 PUBLISH_MISMATCH.
  - T10: tree가 BASE tree이고 parents가 [BASE, I]인 merge M3으로 T9와 같은 절차 → POST_MERGE_AUDIT end ok. 기대 PUBLISH_MISMATCH.
  - T11: 올바른 merge M에서 merge_tree_recomputed=BASE tree로 POST_MERGE_AUDIT end ok. 기대 PUBLISH_MISMATCH.
  - T12: LOCAL_DONE에서 pr-text 없이 phase-set READY_TO_PUBLISH. 기대 INVALID_TRANSITION.
  - T13: PUBLISHING에서 PUSH·PR_CREATE만 ok → phase-set MERGED. 기대 INVALID_TRANSITION.
  - T14: MERGED에서 POST_MERGE_AUDIT 없이 phase-set AUDITED. 기대 INVALID_TRANSITION.
  - T15: SETUP_DONE에서 IMPLEMENT start(nonce N1) → status의 resume_draft 값과 새 nonce N2로 RESUME. 기대 UNKNOWN_STEP(status UNKNOWN, exit 4). 원장 이벤트 수는 바뀌지 않는다.
  - T16: T15 직후 phase-set TERMINAL --terminal-status STOPPED --code UNKNOWN_STEP. 기대 OK. 원장 마지막 이벤트는 PHASE(to TERMINAL, terminal_status STOPPED, code UNKNOWN_STEP)이고, IMPLEMENT의 STEP_START는 STEP_END 없이 남는다. 원장을 다시 읽었을 때 phase는 TERMINAL이고 미종결 단계 1개가 남는다.
  - T17: T16 뒤 step end IMPLEMENT ok(N1), step end IMPLEMENT fail(N1), step start TEST_TARGETED, RESUME(N2), phase-set TERMINAL STOPPED를 다시 실행. 기대: 모두 TERMINAL이고 원장 이벤트 수는 바뀌지 않는다.
  - T18: 미종결 단계와 잔존 LEASE가 있는 상태에서 STOPPED. 기대 LEASE_PRESENT. LEASE와 원장은 바뀌지 않는다.
  - T19: 미종결 단계와 REVOKED가 있는 상태에서 STOPPED. 기대 OK.
  - T20: 미종결 단계가 있고 만료가 지난 상태에서 STOPPED. 기대 OK.
  - T21: 원장이 유효하지 않은 상태(events/000002.json 삭제)에서 STOPPED. 기대 LEDGER_GAP. 남은 이벤트 파일의 이름·바이트는 바뀌지 않고 새 이벤트도 생기지 않는다.
- TEST_GATES "ERRATA-001 경로 회귀 테스트":
  - D4는 유지하며 완화하지 않는다. LEASE·REVOKED·pr_text.md의 최종 구성 요소에 대해, 이미 존재하는 링크·재분석 지점을 따라 읽거나 정상 경로로 취급하지 않는다. 깨진 링크도 존재하지 않는 정상 경로로 취급하지 않는다. 보완은 기존 경로 검사(check_tree_path)를 재사용해 ALLOWED_FILES 안의 구현·테스트로 한다.
  - 검사와 사용 사이의 경쟁을 완전히 막는다고 주장하지 않는다. 링크 검사를 위해 링크 대상이나 기존 산출물을 수정·삭제하지 않는다.
  - 모든 링크·파일 생성은 tmp_path의 임시 저장소와 그 안의 임시 대상에서만 한다.
  - 링크를 만들 수 없는 플랫폼·권한에서는 해당 항목을 NOT_RUN_PLATFORM으로 skip하고 보고한다. 실행하지 못한 항목은 통과로 표시하지 않는다.
  - 공통 기대: 거부 코드는 PATH_INVALID다. 링크 대상의 바이트, 기존 이벤트 파일의 이름·바이트, 기존 산출물은 바뀌지 않고 새 이벤트도 생기지 않는다.
  - P1: LEASE 자리에 임시 대상 파일을 가리키는 심볼릭 링크를 둔 상태에서 status와 step start. 기대 PATH_INVALID.
  - P2: LEASE 자리에 깨진 심볼릭 링크를 둔 상태에서 status와 step start. 기대 PATH_INVALID. LEASE 없음으로 취급하지 않는다.
  - P3: REVOKED 자리에 임시 대상 파일을 가리키는 심볼릭 링크를 둔 상태에서 status, step start, revoke. 기대 PATH_INVALID.
  - P4: REVOKED 자리에 깨진 심볼릭 링크를 둔 상태에서 status, step start, revoke. 기대 PATH_INVALID. 철회되지 않은 상태로 취급하지 않는다.
  - P5: LOCAL_DONE에서 pr_text.md 자리에 임시 대상 파일을 가리키는 심볼릭 링크를 둔 상태에서 pr-text. 기대 PATH_INVALID. 같은 링크가 있는 READY_TO_PUBLISH 상태의 PUBLISH 기록과 publish-draft도 PATH_INVALID.
  - P6: pr_text.md 자리에 깨진 심볼릭 링크를 둔 상태에서 P5와 같은 명령. 기대 PATH_INVALID.
  - P7: Windows에서 LEASE·REVOKED·pr_text.md 자리에 임시 대상 디렉터리를 가리키는 junction을 둔 상태에서 P1·P3·P5와 같은 명령. 기대 PATH_INVALID. 다른 플랫폼에서는 NOT_RUN_PLATFORM이다.
  - P8: 정상 일반 파일·디렉터리에서는 기존 동작을 유지한다. 잔존 LEASE는 LEASE_PRESENT, revoke는 OK와 newly_revoked, pr-text와 PUBLISH 기록은 OK다.
- GATE_TRANSITION_RULES 추가:
  - IMPLEMENTATION 하위 단계 ERRATA_001_CREATION_ONLY를 둔다. 이 단계에서 docs/tasks/GOV-AUTOMATION-03/ERRATA-001.md를 승인 바이트로 최초 1회 생성하고, 그 경로 하나만 stage해 Ce1 커밋을 만든다.
  - Ce1 이후 승인문은 `GATE_AUTHORIZATION: GOV-AUTOMATION-03 <GATE> WO@b0b1855ce5c30a233d836b816cea5a4f62c38f87`와 `ERRATA: ERRATA-001@<Ce1 SHA>`를 함께 적는다.
  - IMPLEMENTATION으로의 후퇴는 Ce1 이후 별도로 승인한다.
- PROTECTED_FILES 추가: docs/tasks/GOV-AUTOMATION-03/ERRATA-001.md
- CONTRACT_FILE_EXCEPTION 추가: docs/tasks/GOV-AUTOMATION-03/ERRATA-001.md는 ERRATA_001_CREATION_ONLY에서 승인 바이트로 최초 1회만 생성한다. 이 예외는 ALLOWED_FILES에 속하지 않는다.
- COMMIT_PLAN:
  - C1: parent = CANONICAL_BASE_SHA, 변경 = A docs/tasks/GOV-AUTOMATION-03/WORK_ORDER.md (b0b1855ce5c30a233d836b816cea5a4f62c38f87)
  - Ce1: parent = C1, 변경 = A docs/tasks/GOV-AUTOMATION-03/ERRATA-001.md 하나. 작성 시점의 ALLOWED_FILES 미커밋 변경은 stage하지 않고 보존한다.
  - I: parent = Ce1, 변경 = ALLOWED_FILES 전체.
  - base..I = WORK_ORDER.md, ERRATA-001.md, ALLOWED_FILES뿐이다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1–3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다. ALLOWED_FILES와 그 변경 한정은 바꾸지 않는다.
- Work Order 파일은 변경하지 않는다. 이 ERRATA는 CHANGED_FIELDS에 적은 항목만 대체하거나 추가한다.
- D1–D5, D7, D8, BUNDLE_MAX_RANGE, 예산, LEASE 정리 권한은 바꾸지 않는다.
