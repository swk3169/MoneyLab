# ERRATA-003: AUTO-08-CONTROLLED-READ

STATUS: ACCEPTED
TASK_ID: AUTO-08-CONTROLLED-READ
APPLIES_TO: WORK_ORDER.md (SHA-256 887f04db75147cec7148620c665adf65c989578c55a7dde5a9d6875e8b67c8b6), ERRATA-001.md (SHA-256 1c4009cc4a31bb303d4e738b1aed92900c766845c0fe1d4ac85ce937ef9a7473), ERRATA-002.md (SHA-256 d5722f33973feacf9ade918ce2a9b800947d1ab939cddab310dd71af04611391)
PRECEDENCE: ERRATA-001, ERRATA-002 다음에 적용한다. 충돌하면 이 ERRATA가 앞선다.
DECISION_REF: 이 대화에서 저장소 관리자인 사용자가 보낸 FILE_FORMAT 예외 결정 메시지. 이 기록은 결정이 있었다는 사실을 적은 것이며, 프로그램이나 에이전트가 결정의 진위를 검증했다는 뜻이 아니다.

## G1 FILE_FORMAT 이스케이프 요구의 한 줄 예외

- 대상: tests/test_agent_guard.py의 test_process_handles_non_ascii_utf8 함수 안에서 hook 입력 payload의 명령 문자열을 정의하는 기존 한 줄. 이 줄은 비ASCII 합성 입력(한글 2자)을 담는다.
- 식별: 대상은 함수 이름과 그 기존 입력으로 식별한다. 행 번호(Cd와 현재 작업 파일 모두 696번째 줄)는 참고용이다.
- 근거: 이 줄은 Cd bbd019983e63e00a2c3aad514445d9ca6f291dc8의 tests/test_agent_guard.py에 이미 있었다. AUTO-08이 만든 줄이 아니다. UTF-8 비ASCII 입력을 guard가 처리하는지 확인하는 기존 시험의 입력이다.
- 예외: FILE_FORMAT의 "시험 코드 안의 합성 입력 문자열 리터럴은 이스케이프로 표현한다"는 요구를 이 한 줄에만 적용하지 않는다. 이 줄의 바이트는 Cd의 해당 줄 그대로 유지해야 하며 바꾸지 않는다.
- 범위 제한: 이 예외를 다른 줄, 다른 파일, AUTO-08이 추가하거나 바꾼 문자열, FILE_FORMAT의 다른 요구(UTF-8, BOM, LF, 끝 LF 1개, 탭·U+00A0·줄 끝 공백 없음)로 넓히지 않는다.
- 소급 금지: A1(이스케이프되지 않은 합성 리터럴), 이전 PRECOMMIT_AUDIT의 FILE_FORMAT 누락, STOP·DENY·DEVIATION 기록, 이전 실패 기록은 그대로 보존한다. 이 예외는 그 어느 것도 정상으로 바꾸지 않는다.

## G2 Ce3와 감사 기준

- Ce3는 docs/tasks/AUTO-08-CONTROLLED-READ/ERRATA-003.md 하나만 담는 문서 커밋이다. parent는 57de2eac231e44ffe2ff3d3373cc8214cc06faf0이다.
- 미커밋 수정 5개(src/moneylab/controlled_read/profiles.py, src/moneylab/controlled_read/store.py, tests/test_controlled_read_profiles.py, tests/test_controlled_read_isolation.py, tests/test_controlled_read_store.py)는 Ce3에 넣지 않는다. 이 5개 파일의 바이트가 Ce3 직전과 직후에 같아야 한다.
- Ce3 절차는 ERRATA-002 F4와 같다: 수락값 대조, 단일 경로 git add --, staged와 commit blob 대조, 보존 대조. 메시지는 "docs(task): accept AUTO-08-CONTROLLED-READ ERRATA-003"(본문·trailer 없음, -a 없음)이다.
- 이후 수정 커밋의 parent는 Ce3다. 수정 diff는 Ce3 대비 위 5개 파일이다.
- 전체 구현 범위는 Cd 대비 ALLOWED_FILES 15개로 확인한다. 계약 문서 추가(ERRATA-003)는 그와 구분해 따로 보고한다.
- 감사 재사용: Ce3의 커밋 변경이 ERRATA-003.md 추가 하나뿐이고, 미커밋 수정 5개 파일의 W·S 해시가 수정본 PRECOMMIT_AUDIT 기록과 같으며, 그 밖의 작업 트리 변경이 없음을 확인하면 기존 감사 결과를 재사용한다. 수집, 전체 시험, 독립 검토는 반복하지 않는다.
- 시험 ID 기록(기준선 3267개, 현재 수집 3611개, 감소 0개)을 유지한다.
- 예산은 초기화하지 않는다. 실패 대응 수정은 누적 4회, 잔여 1회다. 전체 pytest는 누적 3회, 잔여 0회다.
- 이 ERRATA는 수정 커밋, CLEAN_COMMIT_E2E, 공개, push 승인이 아니다.
