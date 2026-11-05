# ERRATA: BT4-FUTILITY-01 ERRATA-008

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-FUTILITY-01-ERRATA-008
TASK_ID: BT4-FUTILITY-01
TARGET_WORK_ORDER: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md
TARGET_WORK_ORDER_COMMIT: 7ac09a674e68cbc95dd5c934f2d3580939fd02f0
TARGET_WORK_ORDER_SHA256: c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

## ISSUE

ISSUE:
- docs/tasks/README.md §13 MERGE 사전 검증 7은
  "원격 main = Work Order가 기대한 base다. 다르면 멈추고 보고한다"이다.
- 이 Work Order가 정한 base는 CANONICAL_BASE_SHA
  15957207a592e062aaa51a6610b7e748ce136ca0(WO:14, G1a 2026-10-29 확인)뿐이다.
- 2026-11-05 G8d 사전 검토에서 `git ls-remote`로 관측한 원격 main은
  5dcf70735f51159053b2387412d9a6ab18abfdb6이었다.
- 15957207은 5dcf7073의 조상이다.
- PR #37(base main, head feature/bt4-futility-diag)의 merge base는 15957207이고 mergeable = MERGEABLE이다.
- 이 Work Order에는 merge 시점의 원격 main 기대값 필드가 없다.
- 따라서 README §13 사전 검증 7이 통과할 수 없다.
- CANONICAL_BASE_SHA는 연구 정체성이기도 하므로 바꿀 수 없다.
  - configs/bt4_futility_diag.toml base_sha
  - 사전등록 CANONICAL_BASE
  - futility_diag.py BASE_SHA, research_identity의 base_sha
- 따라서 merge 사전 검증 전용 필드를 추가한다.

## CHANGED_FIELDS

CHANGED_FIELDS:
- Metadata에 MERGE_EXPECTED_REMOTE_MAIN 1개 필드를 추가한다(REPLACEMENT_CONTRACT).
- G8d(WO:75)의 README §13 사전 검증 7의 기대값을 이 필드로 정한다.

## UNCHANGED_FIELDS

UNCHANGED_FIELDS (명시적으로 바꾸지 않음):
- CANONICAL_BASE_SHA, CANONICAL_BASE_TREE, CANONICAL_BASE_PARENTS, BASE_VERIFICATION(WO:14-17).
- configs/bt4_futility_diag.toml의 base_sha.
- 사전등록 docs/research_bt4_futility_diag_preregistration.md의 CANONICAL_BASE와 문서 전체.
- futility_diag.py의 BASE_SHA, research_identity, IDENTITY_FIELDS,
  CONTRACT_FILES·CONTRACT_SHA256(9개 키).
- CODE_SHA = d2fcaf64b5fb87f502afba29572be340f653be24.
- G1b, WO:133 등 CANONICAL_BASE_SHA를 쓰는 다른 모든 조항.
- 판정 기준, 다중성, 판정 함수, decision_summary.json 스키마.
- G7·G8a 산출물과 그 증거.
- G8a의 기존 기록:
  - G8A_CORE_EXECUTION_PASS = NO
  - G8A_CORE_ACCEPTANCE = CONDITIONAL_ACCEPTANCE
  - G8A_FULL_PASS = NOT_ASSESSED
- EXPLORATORY 의무(RETAINED_UNRESOLVED, EXPLORATORY_REPORT_STATUS PARTIAL).
- TASK_COMPLETE = NOT_DECLARED.
- G8d의 명령·병합 방식(MERGE_METHOD: Create a merge commit, WO:23, :75)과 금지 옵션.
- docs/tasks/README.md(§13의 사전 검증 1~6과 그 밖의 규칙 포함)와 CLAUDE.md.
- COMPLETION_CRITERIA(WO:465-469), GATE_SEQUENCE, ALLOWED_FILES, PROTECTED_FILES.
- ERRATA-001~007 전부.
- 사용자 결정 D2(PR #37 KEEP_OPEN_UNCHANGED), D4(RESULT_PUBLICATION NOT_AUTHORIZED).

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- MERGE_EXPECTED_REMOTE_MAIN: 5dcf70735f51159053b2387412d9a6ab18abfdb6
  - 근거: 2026-11-05 `git ls-remote origin refs/heads/main` 관측값.
  - 적용 범위: G8d의 README §13 사전 검증 7에만 쓴다.
  - 다른 어떤 조항, 연구 실행, research_identity 검사에도 쓰지 않는다.
  - CANONICAL_BASE_SHA를 대체하지 않는다.
- 적용 근거:
  - CLAUDE.md:58: task 계약은 WORK_ORDER.md와 STATUS: ACCEPTED인 ERRATA이며 뒤 번호가 앞선다.
  - docs/tasks/README.md:77-78: ACCEPTED ERRATA만 계약(우선순위 4)을 바꾼다.
  - README §13 사전 검증 3은 "Work Order(와 ACCEPTED ERRATA)"라고 쓰고,
    사전 검증 7은 "Work Order"라고만 쓴다.
  - 이 ERRATA는 사전 검증 7의 "Work Order가 기대한 base"를
    ACCEPTED ERRATA를 포함한 이 task 계약의 기대값으로 읽는다.
  - 이 해석은 문서로 확정된 것이 아니며, 사용자가 이 ERRATA를 수락함으로써 채택한다.
  - README와 CLAUDE.md는 바꾸지 않는다.
- G8d 진입 시 `git ls-remote`로 원격 main을 다시 확인한다.
  MERGE_EXPECTED_REMOTE_MAIN과 다르면 merge하지 않고 STOP한다.
- 원격 main이 다시 바뀌면 이 필드를 고치지 않는다. 새 ERRATA로만 정한다.
- 15957207이 원격 main의 조상이 아니게 된 경우에도 STOP한다.

## ISSUANCE

ISSUANCE:
- 이 ERRATA는 G8d가 의존하므로 G8d 전에 Ce로 커밋한다(README:88, :95).
- 순서(각 단계 별도 사용자 승인, 자동 진행 없음):
  1. 최종 문안 수락(STATUS: ACCEPTED, ACCEPTED_BY: USER로 바꾼 문안).
  2. 저장소 밖 후보 파일 생성과 sha256·bytes·lines 보고.
  3. Ce:
     - 후보 바이트를 docs/tasks/BT4-FUTILITY-01/ERRATA-008.md로 binary 복사
     - 그 경로만 stage
     - 커밋 1회
     - blob sha256 확인
  4. D2 예외 승인 뒤 push 1회(PR #37 head 변경, 파일 1개 추가).
  5. 새 HEAD에서 필수 CI ci-tests / pytest(Windows) job SUCCESS 확인.
  6. G8d 사전 검증(README §13 1~7, 2·4는 새 head SHA 기준).
  7. 별도 G8d merge 승인(MERGE_EXECUTE: YES).
- PR 범위는 ALLOWED_FILES ∪ docs/tasks/BT4-FUTILITY-01/**이다.
  이 ERRATA는 그 안에 있다(README §6).

## RATIONALE

RATIONALE:
- README §13 사전 검증 7은 계약이 예상하지 않은 main 변화를 막는다.
- 연구 기준 SHA를 바꾸면 사전등록·config·코드 정체성(우선순위 3)과 충돌하고
  G7·G8a의 실행 정체성을 흐린다.
- 연구 기준과 merge 기준을 분리하는 최소 변경이다.
- 15957207이 main의 조상이고 PR이 MERGEABLE이므로
  merge 기준만 현재 main으로 정하면 된다.
- 사전 검증 7의 문구에 ERRATA가 명시되지 않은 점은 REPLACEMENT_CONTRACT의 적용 근거에 기록했다.

## BASELINE_IMPACT

BASELINE_IMPACT:
- 연구 정체성, G7·G8a 결과·증거, 판정, EXPLORATORY 상태에 영향이 없다.
- research_identity의 contract_sha256은 9개 고정 키(ERRATA-001~007, 사전등록, config)만 본다.
  이 파일은 그 키에 없다.
- Ce 커밋은 feature/bt4-futility-diag의 HEAD를 바꾼다. 이 브랜치에서 연구 실행은 더 하지 않는다.
- PR #37의 변경 파일은 14개, 커밋은 13개가 된다(push 후).
- PR #40의 base 브랜치가 앞으로 이동한다.
  PR #40 자체(head, draft, 변경 파일)는 바뀌지 않는다.

## SECURITY_IMPACT

SECURITY_IMPACT:
- guard·hook·settings, 저장소 설정을 바꾸지 않는다.
- 이 파일에는 연구 결과값과 가설별 판정 라벨이 없다.
- D4는 유지된다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA:
- AC-1: 후보 sha256 = Ce 복사본 sha256 = Ce blob sha256.
  Ce 파일은 이 파일 하나, parent는 7e3e42ccbd3f5bcae2a90aab8769ffd67332d717.
- AC-2: research_identity에 쓰이는 값(CANONICAL_BASE_SHA, base_sha, BASE_SHA, 9개 contract sha256)이 바뀌지 않았다.
- AC-3: G8d 진입 시 원격 main = MERGE_EXPECTED_REMOTE_MAIN.
- AC-4: 이 파일에 결과값·판정 라벨이 없다.

## ROLLBACK_POLICY

ROLLBACK_POLICY:
- ACCEPTED 이후 이 파일은 불변이다. 철회·수정은 ERRATA-009로만 한다.
- Ce 커밋을 amend·reset하지 않는다. 문제가 있으면 새 커밋이나 새 ERRATA로 한다.

## APPROVAL

APPROVAL:
- 다음은 각각 사용자의 별도 승인으로 한다.
  - 최종 문안 수락
  - 후보 생성
  - Ce 커밋
  - push(D2 예외 포함)
  - CI 확인
  - G8d 사전 검증
- G8d merge는 이 ERRATA로 승인되지 않는다.
  G8d에는 다음이 별도로 필요하다.
  - MERGE_EXECUTE: YES, PR 번호, head SHA를 담은 Gate Authorization
  - D2 G8d 예외
  - README §13 사전 검증 5(G8a 조건부 수용의 수락 여부)에 대한 사용자 결정
- 이 ERRATA는 D2·D4를 바꾸지 않는다.
