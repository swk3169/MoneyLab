# ERRATA: BT4-FUTILITY-01 ERRATA-009

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-FUTILITY-01-ERRATA-009
TASK_ID: BT4-FUTILITY-01
TARGET_WORK_ORDER: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md
TARGET_WORK_ORDER_COMMIT: 7ac09a674e68cbc95dd5c934f2d3580939fd02f0
TARGET_WORK_ORDER_SHA256: c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

## ISSUE

ISSUE:
- README §13 사전 검증 5는 "Work Order·ERRATA가 요구한 추가 증거를 사용자가 수락했다"이다.
  Work Order와 ERRATA-001~008은 "추가 증거"를 정의하지 않는다.
- G8a는 1회 실행됐고 결과가 기록돼 있다.
  - G8A_CORE_EXECUTION_PASS = NO
  - G8A_CORE_ACCEPTANCE = CONDITIONAL_ACCEPTANCE
  - G8A_FULL_PASS = NOT_ASSESSED
  - G8A_PASS = NOT_ASSIGNED
- G8a 보고는 Work Order REQUIRED_REPORT(G8a 항목)를 구조적으로 다 담지 않는다
  (G8A_STRUCTURAL_COMPLETENESS = INCOMPLETE).
- README §2 우선순위는 (1) 안전·도구 제약 (2) CLAUDE.md, .claude/, docs/agent_workflow.md
  (3) 고정·사전등록 계약 (4) Work Order + ACCEPTED ERRATA이다.
- README §3은 전환 규칙을 "GATE_TRANSITION_RULES 기본값"으로 두고 "건너뛰기는 금지다"라고 쓴다.
  TEMPLATE.md는 Work Order에 GATE_TRANSITION_RULES 필드를 둔다.
- "건너뛰기"는 gate를 수행하지 않는 것이다. G8a는 수행됐으므로 건너뛰기가 아니다.
- 결과가 NO인 gate 뒤의 진행(실패 후 진행)은 README §3, Work Order, ERRATA-001~008 어디에도 정해져 있지 않다.
- Work Order BACKGROUND는 "채팅 단계 기록(G0 단계들)은 저장소 증거가 아니다"라고 쓴다.
  G8a 이후의 수용·검토 기록은 채팅에만 있다.
- 따라서 G8d 병합 가능 여부와 사전 검증 5의 수용 대상이 계약상 모호하다.

## SCOPE

SCOPE:
- 이 ERRATA는 다음 두 가지만 정한다.
  - G8d(MERGE) 진입을 위한 실패 후 진행 조건
  - README §13 사전 검증 5의 수용 대상
- 다음으로 해석하지 않는다:
  - G8a 실행 성공, G8a PASS
  - REQUIRED_REPORT 충족 또는 면제
  - 통계적 검증 성공, VALIDATED·calibrated 판정
  - 연구 결과의 독립 검증, 결과 공개, TASK_COMPLETE
- 이 ERRATA는 README, CLAUDE.md, 우선순위 1~3을 바꾸지 않는다.

## CHANGED_FIELDS

CHANGED_FIELDS:
- GATE_TRANSITION_RULES에 G8d 전용 실패 후 진행 규칙 1개를 추가한다(MERGE_EXCEPTION).
- G8d의 README §13 사전 검증 5에서 수락할 증거의 범위를 정한다(PRECHECK_5_EVIDENCE_SCOPE).
- G8d 병합 전 재검증 규칙을 정한다(MERGE_PRECHECK_REVALIDATION).

## UNCHANGED_FIELDS

UNCHANGED_FIELDS (명시적으로 바꾸지 않음):
- 연구 가설, STATISTICAL_HYPOTHESES, 판정·다중성 규칙, ERROR_CLAIM_SCOPE.
- 사전등록 문서(sha256 6da9e20088b1a6ca5c9ce9696c0baadd0850d7aa409f962f2583b188b322189f)와 config.
- G7·G8a 산출물, decision_summary.json, 그 해시와 증거.
- CANONICAL_BASE_SHA 15957207a592e062aaa51a6610b7e748ce136ca0.
- CODE_SHA(G8a 실행 코드) d2fcaf64b5fb87f502afba29572be340f653be24.
- research_identity와 9개 contract sha256.
- Work Order REQUIRED_REPORT(G8a 항목 포함)의 의무. 이 ERRATA는 면제하지 않는다.
- COMPLETION_CRITERIA(WO:465-469) 전부.
- GATE_SEQUENCE, GATE_TABLE(G8d 명령·금지 옵션, G8e 포함), ALLOWED_FILES, PROTECTED_FILES.
- 기존 GATE_TRANSITION_RULES 조항 전부.
- README(§2, §3, §5, §13 포함)와 CLAUDE.md.
- ERRATA-001~008 전부. ERRATA-008의 MERGE_EXPECTED_REMOTE_MAIN과 그 해석 포함.
- G8a 상태값과 EXPLORATORY 상태.
- 사용자 결정 D2, D4(RESULT_PUBLICATION NOT_AUTHORIZED).

## KNOWN_LIMITATIONS

KNOWN_LIMITATIONS (병합 뒤에도 미해결로 남는다. 해결된 것으로 재분류하지 않는다):
- KL-1: V-1 재표본 퇴화 수 분포(WO REQUIRED_REPORT G8a)가 보고되지 않았다.
  - V1_DISTRIBUTION_STATUS = ACCEPTED_AS_KNOWN_LIMITATION
  - 계산·결과 열람은 승인되지 않았다(NOT_AUTHORIZED).
- KL-2: G8a 보고의 REQUIRED_REPORT가 불완전하다(G8A_STRUCTURAL_COMPLETENESS = INCOMPLETE).
  - 일부 항목(ERROR_CLAIM_SCOPE, 증거 등급, PROPOSED_ERRATA, ISSUES, 공통 gate 항목, V-4 해석 제한 문구)은
    E-4가 계약 원문·git 기준으로 보완했다.
  - 원래 보고서에 있었다는 증거는 아니다.
- KL-3: G8A_PASS = NOT_ASSIGNED.
- KL-4: G8A_CORE_EXECUTION_PASS = NO.
- KL-5: G8A_FULL_PASS = NOT_ASSESSED, SEMANTIC_COMPLETENESS = NOT_ASSESSED.
- KL-6: EXPLORATORY_REPORT_STATUS = PARTIAL. A, B, C, C', D, E = RETAINED_UNRESOLVED.
- KL-7: G8a 보고의 사전등록 형식 준수(COMPLETION_CRITERIA:466)가 NOT_VERIFIED다.
- KL-8: 기존 산출물 보존 증거 일부가 NOT_VERIFIED다.
  - 약 5,800개 파일에 실행 전후 내용 비교가 없다.
  - 실행 전 메타데이터 목록이 없다.
  - 기준선 상태 = OBSERVED_NOT_HISTORICALLY_VERIFIED.
- KL-9: G8a 실행 종료 코드가 NOT_CAPTURED다(추정 0).
- KL-10: 증거 등급은 SYNTHETIC / NOT_EVIDENCE다. G8a 판정은 BT4-02로 이미 알려져 있었고 독립 확인이 아니다.

## PRECHECK_5_EVIDENCE_SCOPE

PRECHECK_5_EVIDENCE_SCOPE:
- G8d의 README §13 사전 검증 5에서 "Work Order·ERRATA가 요구한 추가 증거"는
  이 task에서 다음 기록 묶음(EVIDENCE_SET_G8D)이다.
- 식별 기준:
  - 세션 로그: ~/.claude/projects/C--MoneyLab-bt4-futility-diag/4e12076e-eeca-4240-b6bb-d43854faed93.jsonl
  - LINE: 1부터 센 줄 번호
  - UUID: 그 줄의 uuid 필드
  - BODY_SHA256: 그 메시지 text 내용의 UTF-8 바이트 SHA-256
- E-1:
  - 기록: G8a 실행 보고(assistant)
  - UUID: 2b005a75-db8b-414e-8d91-31481274703f
  - LINE: 7449
  - 시각: 2026-11-05T08:57:19.857Z
  - BODY_SHA256: 24a4bf1c37f67f0ba4a8c82313f31926ef7dfeb1f718e80eca69e8fbb3c653cc
- E-2a:
  - 기록: G8a 조건부 수용 결정(user)
  - UUID: 10e0a536-0933-4cf3-927b-eab883ae1f7e
  - LINE: 7485
  - 시각: 2026-11-05T09:02:01.848Z
  - BODY_SHA256: e9daa225471e1327ef090b6344905df0bf4ab1612c15049ca0f1c7e9744e6aec
- E-2b:
  - 기록: G8a 조건부 수용 기록 보고(assistant)
  - UUID: be298661-b830-431c-9556-43dadddee0de
  - LINE: 7495
  - 시각: 2026-11-05T09:03:02.223Z
  - BODY_SHA256: 740a5546794d2b4f40a159321d9a413721ab50943a2f1794ee323a580153114d
- E-3:
  - 기록: G8a REQUIRED_REPORT 구조적 완전성 검토(assistant)
  - UUID: 7fc709d4-23fd-419f-814f-7f0ad441f6b9
  - LINE: 8178
  - 시각: 2026-11-05T14:28:38.675Z
  - BODY_SHA256: dcd57701e6939d103f871b02759bb4111da2e13cd3f7ac0002e858da25a80713
- E-4:
  - 기록: G8a 기존 증거 기반 보완 보고(assistant)
  - UUID: b9d3a93a-8006-48ba-b498-97e3f1730acf
  - LINE: 8261
  - 시각: 2026-11-05T14:34:42.031Z
  - BODY_SHA256: adaf3d6332725b2a8efa8bf5711d10e76a2d7417d2b72e005dcf9ff6ede5f86e
- E-5a:
  - 기록: V-1 분포 OPTION_C 결정(user)
  - UUID: 3017e062-b578-412d-9acf-bf62b3b70977
  - LINE: 8300
  - 시각: 2026-11-05T14:39:46.194Z
  - BODY_SHA256: 37a7afc60f04083a3d1191f9e57e7f454239dea6691b116e16a983cc16192a69
- E-5b:
  - 기록: V-1 분포 OPTION_C 결정 기록(assistant)
  - UUID: 470f0092-fb0f-4145-af97-a1849e2b917b
  - LINE: 8304
  - 시각: 2026-11-05T14:39:56.863Z
  - BODY_SHA256: 0ed7ce0af4b219c1c4a58f7d2e1f59ef4472ff32f220c3344c03dd36dd30b778
- E-6:
  - 기록: G8d 사전 검증 5 계약 예외 검토(assistant)
  - UUID: bdcbfdf4-6e89-4c30-88cf-527b7f8e1c6f
  - LINE: 8324
  - 시각: 2026-11-05T14:42:22.986Z
  - BODY_SHA256: 3f5158850c2c6dd4aac5da1b09ca091200d4b59b7ca9b42b868f25fff6a97b4c
- 증거 지위:
  - 위 식별자는 CLAUDE_REPORTED다(Claude가 세션 로그에서 계산).
  - 세션 로그는 저장소 밖의 로컬 파일이다. 저장소 증거나 INDEPENDENT 증거가 아니다.
  - Work Order BACKGROUND의 "채팅 단계 기록은 저장소 증거가 아니다"는 그대로 유효하다.
  - 저장소에 고정되는 것은 이 파일의 식별자와 KNOWN_LIMITATIONS의 상태값뿐이다.
  - E-1·E-2a 본문에는 결과값 또는 판정 라벨이 있다. 이 파일은 그 본문을 인용하지 않는다(D4).
- 이 ERRATA의 수락은 사전 검증 5의 PASS가 아니다.
- 사전 검증 5는 사용자가 G8d 전에 별도 결정으로 다음을 모두 명시할 때만 PASS다.
  - PRECHECK_5_ACCEPTANCE: ACCEPTED_WITH_KNOWN_LIMITATIONS
  - EVIDENCE_SET_G8D(E-1~E-6)와 KNOWN_LIMITATIONS(KL-1~KL-10)의 수락
  - PR #37의 정확한 head SHA
  - 이 ERRATA의 Ce 커밋 SHA
- 다음이면 사전 검증 5는 BLOCKED이고 merge하지 않는다.
  - 그 결정이 없다.
  - 다른 한계가 새로 발견된다.
  - 식별자 재계산이 위 값과 다르다.

## MERGE_EXCEPTION

MERGE_EXCEPTION (REPLACEMENT_CONTRACT, GATE_TRANSITION_RULES 추가):
- 근거:
  - README §3 전환 규칙은 "기본값"이다.
  - Work Order는 GATE_TRANSITION_RULES를 가진다(TEMPLATE.md).
  - ACCEPTED ERRATA는 우선순위 4에서 Work Order를 바꾼다(README §2, §5).
  - 이 조항은 README를 바꾸지 않는다. 기본값이 정하지 않은 "실패 후 진행"에 Work Order 수준 규칙 1개를 더한다.
  - README 자체의 우선순위 위치는 README §2에 명시되지 않았다(NOT_VERIFIED). 이 조항은 README §3의 '기본값' 문구에 근거하며, README의 우선순위가 확정됐다고 주장하지 않는다.
- 건너뛰기와 구분:
  - 이 조항은 건너뛰기를 허용하지 않는다.
  - G8a는 수행됐고 그 결과(NO / CONDITIONAL_ACCEPTANCE)는 그대로 남는다.
- 규칙: 다음 모두가 충족되면 G8d는 KNOWN_LIMITATIONS가 미해결인 상태로 진입할 수 있다.
  1. README §13 사전 검증 1~4, 6이 승인된 head SHA 기준으로 통과한다.
  2. 사전 검증 5가 PRECHECK_5_EVIDENCE_SCOPE에 따라 통과한다.
  3. 사전 검증 7이 ERRATA-008과 이 파일의 PRECHECK_7에 따라 통과한다.
  4. MERGE_PRECHECK_REVALIDATION을 지켰다.
  5. D2 G8d 예외가 별도로 승인되어 있다.
  6. Gate Authorization에 MERGE_EXECUTE: YES, PR 번호(37), 정확한 head SHA가 있다.
- 적용 범위:
  - G8d 한 번의 진입에만 적용된다.
  - G8b·G8c의 기존 진행을 소급해 정당화하거나 판정하지 않는다.
  - G8a의 상태값, REQUIRED_REPORT 의무, COMPLETION_CRITERIA를 바꾸지 않는다.
  - G8e·COMPLETE 진입 조건을 바꾸지 않는다.
- 병합으로 main에 들어가는 파일은 결과값·판정 라벨을 담지 않는다(D4 유지).

## MERGE_PRECHECK_REVALIDATION

MERGE_PRECHECK_REVALIDATION:
- 사전 검증 5 결정, D2 G8d 예외, merge Gate Authorization은 같은 PR head SHA를 명시해야 한다.
- 그 결정·검증 이후 PR #37 head가 바뀌면 다음을 다시 한다.
  - 새 head에서 REQUIRED_CI_CHECKS(ci-tests / pytest (Windows)) SUCCESS 재확인
  - README §13 사전 검증 1~7 재검증
  - 사전 검증 5 결정과 D2 G8d 예외 재결정(기존 결정은 효력을 잃는다)
- merge 직전 `git ls-remote`로 PR head와 원격 main을 다시 확인한다.
  - PR head ≠ 승인된 head SHA이면 merge하지 않고 STOP한다.
  - 원격 main ≠ MERGE_EXPECTED_REMOTE_MAIN이면 merge하지 않고 STOP한다.
- merge 명령은 `--match-head-commit <승인된 head SHA>`를 쓴다(WO:75).

## COMPLETION_CRITERIA_TREATMENT

COMPLETION_CRITERIA_TREATMENT:
- COMPLETION_CRITERIA는 바뀌지 않는다.
- WO:466(G8a 보고의 사전등록 형식 준수)은 NOT_VERIFIED로 남는다.
  - 병합으로 PASS가 되지 않는다.
  - G8e 또는 COMPLETE 판단 전에 별도로 평가한다.
- KL-1, KL-2가 COMPLETION_CRITERIA 충족에 미치는 영향은 이 ERRATA가 정하지 않는다.
- 완료 기준의 변경·면제가 필요하면 병합 예외와 분리된 별도 ERRATA와 별도 사용자 결정으로만 한다.
- TASK_COMPLETE는 NOT_DECLARED다. 이 ERRATA나 병합만으로 선언하지 않는다.

## G8E

G8E:
- G8e(POST_MERGE_AUDIT)는 GATE_TABLE 그대로 별도 Gate Authorization과 검증이 필요하다.
- 이 ERRATA의 수락이나 G8d 병합은 G8e 승인이 아니다.

## PRECHECK_7

PRECHECK_7:
- ERRATA-008의 MERGE_EXPECTED_REMOTE_MAIN(5dcf70735f51159053b2387412d9a6ab18abfdb6)과 그 해석을 유지한다.
- 해석 위험:
  - README §13 사전 검증 7의 문구는 "원격 main = Work Order가 기대한 base"이다.
  - 문자 그대로 읽으면 Work Order의 base는 CANONICAL_BASE_SHA 15957207뿐이다.
  - 이 task는 ERRATA-008 수락으로 채택한 해석(ACCEPTED_AS_INFERRED)에 의존한다.
  - 이 ERRATA는 그 해석을 확정하거나 넓히지 않는다.
- G8d 진입 직전 원격 main이 MERGE_EXPECTED_REMOTE_MAIN과 다르면 merge하지 않고 STOP한다.
- 15957207이 원격 main의 조상이 아니면 STOP한다.
- 원격 main이 바뀌면 ERRATA-008을 고치지 않는다. 새 ERRATA로만 정한다.

## ISSUANCE

ISSUANCE:
- G8d가 이 ERRATA에 의존하므로 G8d 전에 Ce로 커밋한다(README §6).
- 순서(각 단계 별도 사용자 승인, 자동 진행 없음):
  1. 최종 문안 수락(STATUS: ACCEPTED, ACCEPTED_BY: USER로 바꾼 문안)
  2. 저장소 밖 후보 파일 생성과 sha256·bytes·lines 보고
  3. Ce:
     - docs/tasks/BT4-FUTILITY-01/ERRATA-009.md로 binary 복사
     - 그 경로만 stage
     - 커밋 1회
     - 커밋된 파일 sha256 확인
     - parent = 34723a63fb7d284abc1861138d1cd857afb50797
  4. D2 예외 승인 뒤 push 1회
  5. 새 HEAD에서 ci-tests / pytest (Windows) SUCCESS 확인
  6. G8d 사전 검증 1~7 재검증(새 head SHA 기준)
  7. 사전 검증 5 증거 수용 결정(head SHA와 이 ERRATA의 Ce SHA 명시)
  8. D2 G8d 예외 승인(같은 head SHA)
  9. G8d merge Gate Authorization(MERGE_EXECUTE: YES, PR #37, 같은 head SHA)
- 6~9 사이에 head가 바뀌면 MERGE_PRECHECK_REVALIDATION에 따라 5부터 다시 한다.
- PR 범위는 ALLOWED_FILES ∪ docs/tasks/BT4-FUTILITY-01/**이고 이 파일은 그 안에 있다.

## BASELINE_IMPACT

BASELINE_IMPACT:
- 연구 정체성, G7·G8a 결과·증거, 판정, EXPLORATORY 상태에 영향이 없다.
- research_identity의 9개 contract 키에 이 파일은 없다.
- push 후 PR #37은 변경 파일 15개, 커밋 14개가 된다.
  ERRATA-008 BASELINE_IMPACT의 14개·13개는 ERRATA-008 push 시점 값이며, 그 파일은 고치지 않는다.
- PR #40의 base 브랜치가 앞으로 이동한다. PR #40 자체는 바뀌지 않는다.

## SECURITY_IMPACT

SECURITY_IMPACT:
- guard·hook·settings, 저장소 설정을 바꾸지 않는다.
- 이 파일에는 연구 결과값과 가설별 판정 라벨이 없다. D4는 유지된다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA:
- AC-1: 후보 sha256 = Ce 복사본 sha256 = 커밋된 파일 sha256.
  Ce 파일은 이 파일 하나, parent는 34723a63fb7d284abc1861138d1cd857afb50797.
- AC-2: research_identity에 쓰이는 값(CANONICAL_BASE_SHA, base_sha, BASE_SHA, 9개 contract sha256)과
  G7·G8a 산출물 해시가 바뀌지 않았다.
- AC-3: 이 파일에 결과값·판정 라벨이 없다.
- AC-4: G8d 전에 PRECHECK_5_ACCEPTANCE 사용자 결정이 따로 있다.
  그 결정은 head SHA와 이 ERRATA의 Ce SHA를 명시한다.
- AC-5: G8d 진입 시 원격 main = MERGE_EXPECTED_REMOTE_MAIN.
  PR head = 승인된 head SHA.
- AC-6: 결정 이후 head가 바뀌었다면 CI·사전 검증 1~7·사전 검증 5 결정·D2 G8d 예외를 새 head에서 다시 했다.

## ROLLBACK_POLICY

ROLLBACK_POLICY:
- ACCEPTED 이후 이 파일은 불변이다. 철회·수정은 ERRATA-010으로만 한다.
- Ce 커밋을 amend·reset하지 않는다.

## APPROVAL

APPROVAL:
- 다음은 각각 사용자의 별도 승인으로 한다:
  - 최종 문안 수락
  - 후보 생성
  - Ce 커밋
  - push(D2 예외 포함)
  - CI 확인
  - G8d 사전 검증 재검증
  - 사전 검증 5 증거 수용 결정
  - D2 G8d 예외
- G8d merge는 이 ERRATA로 승인되지 않는다.
  MERGE_EXECUTE: YES, PR #37, 정확한 head SHA를 담은 Gate Authorization이 따로 필요하다.
- 이 ERRATA는 D2·D4, G8a 상태값, REQUIRED_REPORT 의무, COMPLETION_CRITERIA를 바꾸지 않는다.
