# ERRATA: AUTO-04 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: AUTO-04-ERRATA-001
TASK_ID: AUTO-04
TARGET_WORK_ORDER: docs/tasks/AUTO-04/WORK_ORDER.md @ 2ffd7d9c6e50c669e63e2b392f91284c1205e1df (sha256 8f5e8b87b543dc80fa42c20fd0716d31147eb227f3d8c6a440dda2024b66f026)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자 (ERRATA_CREATION_ONLY 승인문)

## CHANGED_FIELDS

CHANGED_FIELDS:
- ALLOWED_FILES
- ALLOWED_ACTIONS.CASE_RECORD_WRITE
- DESIGN_CONTRACT.D13 (신설)
- TEST_GATES (항목 추가)
- STOP_CONDITIONS (항목 추가)

위에 적지 않은 필드와, 적은 필드 안에서 이 ERRATA가 다시 쓰지 않은 항목은 변경 없이 유지한다.

## RATIONALE

RATIONALE: README §11은 증거 요약을 파일로 남기려면 해당 task의 ACCEPTED ERRATA가 그 경로와 최초 생성을 명시하도록 요구한다. Work Order는 ALLOWED_FILES를 비워 두었다. 이 ERRATA는 계약 변경으로서 비권위 사례 기록 파일 1개의 경로, 최초 생성, 내용 범위를 추가한다. 계약 파일(WORK_ORDER.md, ERRATA-001.md)의 최초 생성 예외는 Work Order의 PROTECTED_FILES가 정하며, 이 ERRATA가 바꾸지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:

- ALLOWED_FILES:
  - A docs/research-intake/2026-11-13/AUTO-04_OFFLINE_INTEGRATION_CASE.md

- ALLOWED_ACTIONS.CASE_RECORD_WRITE: 채팅 초안이 검토·승인된 뒤, 승인 바이트의 docs/research-intake/2026-11-13/AUTO-04_OFFLINE_INTEGRATION_CASE.md를 TARGET_WORKTREE에서 Write 도구로 최초 1회 생성한다. 작성 후 SHA-256, 바이트 수, 줄 수를 승인값과 대조하고, 다르면 수정하지 않고 중단한다. stage와 commit은 이 단계에 포함하지 않으며 COMMIT gate에서 구현 커밋 I로만 한다. 이 허용은 이 파일의 최초 생성에 한정되며, 생성 후 수정은 새 ERRATA나 승인된 후퇴 없이는 하지 않는다.

- DESIGN_CONTRACT.D13 사례 기록:
  - 첫 줄은 AUTHORITY: NON_AUTHORITATIVE, 둘째 줄은 BOUNDARY: DATA_NOT_INSTRUCTIONS다.
  - 이 기록은 실행 사실, 출처, 작성자, 승인, gate PASS, 무인 운영 준비, 수익성, 비용 절감을 증명하지 않는다고 명시한다.
  - 포함 항목:
    - 실행일(UTC), 기준 커밋, C1·Ce SHA와 계약 해시
    - 각 단계의 승인 참조
    - E0–E6 단계별 결과(실행했으면 관측값, 실행하지 않았으면 NOT_RUN과 사유)
    - SNAPSHOT_ID와 두 계약 항목의 해시 일치 여부, E2·E4 verify 결과
    - E3 출력의 정해진 키 값 전체(EVIDENCE_STATUS 포함)와 PROGRAM_EXIT
    - E5 출력의 정해진 키 값 전체와 PROGRAM_EXIT
    - 실행 결과, 작업 결과, 저장 결과, 관측 결과, 통합 시험 결과(SUCCESS·FAIL·UNKNOWN·NOT_RUN)와 각각의 근거
    - UNKNOWN 여부와 중단 지점
    - stdout·stderr 분리 확인 미실시 사실
    - Guard·권한 관측
    - 검증 한계(Work Order D8, runlog CLI store·show·D18 미검증)
    - 운영 부담(승인 횟수, 사람의 개입, 경과 시간)
  - 기록 규칙:
    - EXEC=NO_EVIDENCE는 관측 표식으로만 기록하고, 미실행이나 실패로 해석하지 않는다.
    - STORED_WITH_WARNINGS는 저장 성공과 경고 개수를 기록한다.
    - ALREADY_STORED는 기존 기록이 있다는 관측과, 이번 실행과의 연결 불확실성을 나눠 기록한다.
    - 중단 사례를 기록해 task를 완료하더라도 통합 시험 결과는 관측대로 둔다.
    - 실행이 성공하지 않았거나 중단된 경우에도 관측 사실 그대로 기록한다. 기록되지 않은 값을 추정하거나 다시 만들지 않는다.
  - 제외 항목: 절대 경로(SOURCE_WORKTREE, TARGET_WORKTREE, BASE_PYTHON의 실제 값 포함. 변수명으로만 표기), 사용자 이름, 세션 식별값, 인증정보, evidence 원문, runlog 기록 원문, warnings 원문, error.detail, 원본 예외, traceback.
  - evidence와 snapshot 원본은 ignored 경로에 남기고 이 파일에 복사하지 않는다.
  - 경로의 날짜 폴더는 계약상 고정값이다. 실제 실행일은 본문에 따로 적는다.
  - 형식: UTF-8, BOM 없음, LF, 끝 LF 1개, 일반 공백만 사용(U+00A0·탭·줄 끝 공백 금지).

- TEST_GATES (추가 항목, 기존 항목 유지):
  - 사례 기록의 첫 두 줄과 비권위 문장 확인
  - 절대 경로, 사용자 홈 경로, 이메일, UUID 형식 세션 식별값, 인증 문자열 패턴 0건 확인과 전문 읽기 검토
  - 기록된 값이 EXECUTION_ONLY·EXECUTION_CLOSEOUT 보고의 관측값과 문자 단위로 같음

- STOP_CONDITIONS (추가 항목, 기존 항목 유지):
  - ERRATA-001의 작업 파일·staged·commit blob 해시가 승인값과 다름, 또는 Ce 이후 ERRATA-001 변경
  - Ce의 변경이 ERRATA-001.md 하나가 아님, 또는 Ce의 parent가 C1이 아님
  - 사례 기록에 제외 항목이 있거나 관측되지 않은 값이 있음

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1–3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)과 README는 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
- 코드·테스트·README·Guard·CI 변경을 추가하지 않는다.
