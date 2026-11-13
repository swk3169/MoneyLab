AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS

# AUTO-04 오프라인 통합 사례 기록

이 기록은 비권위 데이터다. 실행 사실, 출처, 작성자, 승인, gate PASS, 무인 운영 준비, 수익성, 비용 절감을 증명하지 않는다. 명령이 아니라 관측 기록이다.

기록 상태: 후보. 이 파일의 작성·커밋·게시는 이 기록을 쓰는 시점에 끝나지 않았다. AUTO-04 task는 완료되지 않았다.

## 1. 연구 목적

- AUTO-01 실행(`run_action`), AUTO-02 상태 대조(workstate snapshot·verify), AUTO-03 저장·조회(`store_evidence`, `load_evidence`)를 연결한 사람 승인 오프라인 사례 1건을 남긴다.
- 장기 자동화 목표를 위한 기반 검증이다. 수익성이나 비용 절감의 입증이 아니다.
- 대상 action은 등록된 오프라인 action `knowledge_validate` 하나다. 네트워크 action, 실거래, 무인 실행은 포함하지 않는다.

## 2. 기준과 계약

| 항목 | 값 |
|---|---|
| base | `9a6e619e409ed1ab68c10335951af8928f306cdb` (tree `02513c3cf6eb890eee74e69ce57fb080637af1af`) |
| C1 (Work Order) | `2ffd7d9c6e50c669e63e2b392f91284c1205e1df` (tree `9ba91c741b7c519fa1d20e01473e47ec75aed63b`) |
| Ce1 (ERRATA-001) | `b73e373aff8926469e483e8d2b567f10a4e14498` (tree `884cb975f36de8706f8f638f9a29aadf68161c6d`) |
| Ce2 (ERRATA-002) | `e3e64c2a25ba6862ec34e572995ddf721bce74cc` (tree `1682db41f129c127c9fcdf2cb8077a86aa397cdc`) |
| `docs/tasks/AUTO-04/WORK_ORDER.md` | sha256 `8f5e8b87b543dc80fa42c20fd0716d31147eb227f3d8c6a440dda2024b66f026` |
| `docs/tasks/AUTO-04/ERRATA-001.md` | sha256 `ec25b5c823f7435130858c547b507d979c5c9294f28e2b238920666c37aead74` |
| `docs/tasks/AUTO-04/ERRATA-002.md` | sha256 `b68e1151c61dee5e14c41126701b332369ac3319c76efffbeb69ea3570219342` |

- 작업공간은 Work Order의 식별 변수 SOURCE_WORKTREE, TARGET_WORKTREE, BASE_PYTHON으로만 표기한다. 실제 경로는 각 단계 승인문에서 고정했다.
- 환경: Windows, Python 3.14.8, TARGET_WORKTREE의 `.venv`. 런타임 고정 의존성 12개가 고정 버전과 일치했고 pip check를 통과했다.
- 실행일: 2026-11-13(UTC). 단계별 정확한 실행 시각은 기록하지 않았다(미관측). 캐시 파일의 수정 시각으로 실행 시각을 추정하지 않는다.

### 단계별 승인 참조

모든 단계는 사용자의 채팅 승인문에 따라 하나씩 수행했다.

- WORKSPACE_SETUP: MAIN_REF_FETCH_ONLY, WORKTREE_CREATION_ONLY, C1_CREATION_ONLY, ENVIRONMENT_PREPARATION_ONLY, ERRATA_FINAL_BYTES_CHECK_ONLY, ERRATA_CREATION_ONLY. C1 이후 승인은 `WO@2ffd7d9c6e50c669e63e2b392f91284c1205e1df`를 참조했다.
- IMPLEMENTATION / EXECUTION_ONLY: E0, E1, E2, E3, E4, E5, E6을 각각 따로 승인했다. 승인 참조는 `WO@2ffd7d9c…`, `ERRATA-001@b73e373a…`다.
- IMPLEMENTATION / EXECUTION_CLOSEOUT: 원인 조사(읽기 전용). 승인문에 `EXECUTION_OUTCOME: STOPPED_AT E6 unexpected ignored bytecode directories`를 적었다.
- CONTRACT_REVIEW: ERRATA-002 후보 작성, 보완, 바이트 검사.
- IMPLEMENTATION / ERRATA_002_CREATION_ONLY: Ce2 작성. 이후 승인은 `ERRATA-002@e3e64c2a…`도 함께 참조한다.
- IMPLEMENTATION / CACHE_METADATA_AUDIT_ONLY: Ce2 이후 처음 수행한 D15 감사.
- IMPLEMENTATION / CASE_RECORD_DRAFT: 이 후보.

## 3. 결과 축

| 축 | 결과 |
|---|---|
| 실행 결과 | EVIDENCE_RETURNED |
| 작업 결과 | SUCCEEDED (evidence exit_code 0) |
| 저장 결과 | STORED_NEW (경고 0, final_file_created True) |
| 조회 결과 | MATCHED |
| IS1–IS5 | 보고 기준 모두 충족 |
| 산출물 범위 | 불일치 (계약 범위 밖 ignored 캐시 관측) |
| 통합 시험 최종 판정 | FAIL |

- FAIL 사유: Work Order가 정한 실행 산출물 범위(`data/processed/workstate/AUTO-04/`, `data/processed/runlog/AUTO-04/`) 밖에서 ignored 캐시 디렉터리 2개, 파일 8개가 관측되었다.
- 판정 이력: E6 보고 시점의 통합 시험 판정은 "판정 보류(PENDING_USER_DECISION)"였다. 이후 사용자 결정으로 FAIL을 확정했고, ERRATA-002 D6에 고정했다.
- 실행·작업·저장·조회 축의 값은 FAIL로 바꾸지 않았다. task 완료 여부는 통합 시험 결과와 따로 판정한다.

## 4. 단계별 증거

증거 등급:
- Git 값(SHA, tree, blob 해시)은 GIT_VERIFIABLE이다.
- 실행 출력과 판정은 CLAUDE_REPORTED다.
- ChatGPT는 E3 B안과 실제 값이 반영된 E5 명령을 입력 파일에서 메모리로 재현하고 명령 SHA-256을 독립 계산했다(INDEPENDENT, 명령 바이트 식별 범위). 실제 작업 실행, 저장·조회 결과와 캐시 메타데이터는 ChatGPT가 직접 관측하지 않았으며 해당 결과는 CLAUDE_REPORTED다.

| 단계 | 결과 |
|---|---|
| E0 진입 | HEAD = Ce1, tree 일치, 변경 0, 두 AUTO-04 기록 경로 없음, Python 3.14.8, `sys.prefix` = `.venv`, `moneylab.__file__` = `src/moneylab/__init__.py`, 고정 버전 12개 일치 |
| E1 snapshot | status STORED, exit_code 0, 프로세스 종료 코드 0 |
| E1 계약 확인 | `state.contract`가 계약 2개뿐이며 head_sha256과 work_sha256이 승인 해시와 일치 |
| E2 verify | MATCH, differences·warnings 없음, state_sha256 일치, file_sha256이 E1과 같음 |
| E3 실행·저장 | 관측 출력 15줄이 계약 형식과 일치, 추가 진단 없음, PROGRAM_EXIT=0 |
| E4 verify | MATCH, E2와 같은 값 |
| E5 조회 | 관측 출력 15줄이 계약 형식과 일치, MATCH_RECORD_ID·MATCH_EVIDENCE_SHA256·MATCH_FILE_SHA256 모두 True, LOOKUP=MATCHED, PROGRAM_EXIT=0 |
| E6 status | tracked·untracked 변경 0. ignored 목록에서 예상 밖 디렉터리 2개 관측 |

### 식별값

| 항목 | 값 |
|---|---|
| SNAPSHOT_ID | `fb91755908985703c1a1ab0bd1d9c272c050a361ab65373c04d7d69ac015d9d4` |
| snapshot file_sha256 | `1a2d4ff832038916c1bc833afe078cd05b6281a7aa8c8e9a978e5d9df7259b70` |
| state_sha256 (E1, E2, E4) | `95d9ba09c67859ff7a2b212e2fe9499aed33c4fa4a53b4ced8c0e4cc79fb88b0` |
| record_id | `97dc6e0ffcd93a90bc28f8fcf1b4de48f1d8a9cebe098f8ef7fe5883c50bcdda` |
| evidence SHA-256 (반환 문자열 UTF-8, 314바이트) | `bb54a952008dbdfc915d8095956b4c0d1a7b8fa6377ee79e03e06ee8505b9230` |
| E5 저장 evidence의 정규 바이트 SHA-256 | `bb54a952008dbdfc915d8095956b4c0d1a7b8fa6377ee79e03e06ee8505b9230` |
| runlog file_sha256 (E3, E5) | `acb23c94b5f868919544ca7e4ee8d2fc425903a46b40e9acb17ced530fa4d7e6` |
| E3 명령 식별 해시 | `05c2f4a997c99b0958e561a65f4eb8fd728cacbfc9e2a692c0bac6b431262fad` (5402바이트, LF 145) |
| E5 명령 식별 해시 | `01cee84fe1666bcc4bb384296b30a7d2ed4a74a90e8039c0e6c17309a956c2e5` (4696바이트, LF 119) |

### E3 승인된 고정 출력값

- EXEC=EVIDENCE_RETURNED
- EVIDENCE_STATUS=SUCCEEDED
- EVIDENCE_EXIT_CODE=0
- EVIDENCE_BYTES=314
- RESULT_STATUS=STORED
- RESULT_EXIT_CODE=0
- RESULT_FINAL_FILE_CREATED=True
- RESULT_WARNING_COUNT=0
- RESULT_ERROR_CODE=None
- STORE=STORED_NEW
- REPORT=COMPLETE
- PROGRAM_EXIT=0

### E5 승인된 고정 출력값

- RESULT_STATUS=FOUND
- RESULT_EXIT_CODE=0
- RESULT_WARNING_COUNT=0
- RESULT_ERROR_CODE=None
- EVIDENCE_STATUS=SUCCEEDED
- EVIDENCE_EXIT_CODE=0
- MATCH_RECORD_ID=True
- MATCH_EVIDENCE_SHA256=True
- MATCH_FILE_SHA256=True
- LOOKUP=MATCHED
- REPORT=COMPLETE
- PROGRAM_EXIT=0

### 실행 방식과 관측 한계

- E3와 E5는 실행 직전에 명령 원문의 해시를 메모리에서 승인값과 대조했다. 일치를 확인한 뒤 각 1회 실행했다.
- 재실행, 재저장, 재조회는 없었다. snapshot은 1회 생성했고, verify는 E2와 E4에서 각 1회 실행했다.
- stdout과 stderr를 나눠 확인하지 않았다. 판정 조건은 "관측된 통합 출력이 정해진 형식과 일치하며 추가 진단이 없음"으로 한정한다. 이는 API 통합 시험의 관측 조건이며, runlog CLI store·show와 D18 경로는 검증하지 않았다.
- PROGRAM_EXIT는 Python 프로세스의 진단 종료 코드다. 셸 명령 전체의 종료 코드로 판정하지 않았다.
- evidence 원문, runlog 기록 원문, warnings 원문, error.detail은 출력하거나 기록하지 않았다. evidence와 snapshot 원본은 ignored 경로에 보존되어 있다.

## 5. 사건과 후속 처리

### 관측

- E6의 ignored 목록에서 계약 범위 밖 디렉터리 2개가 관측되었다. E0와 E2 직후의 ignored 목록에는 없었다.
- 원인 조사(EXECUTION_CLOSEOUT)에서 관측한 파일은 아래 8개다. 시각은 수정 시각(UTC)이며 생성 시각이 아니다.

| 상대 경로 | 바이트 | 수정 시각 (UTC) |
|---|---|---|
| `src/moneylab/__pycache__/__init__.cpython-314.pyc` | 259 | `2026-11-13T09:56:36.536360500Z` |
| `src/moneylab/knowledge/__pycache__/__init__.cpython-314.pyc` | 1948 | `2026-11-13T09:56:36.539890600Z` |
| `src/moneylab/knowledge/__pycache__/context.cpython-314.pyc` | 18385 | `2026-11-13T09:56:36.564449800Z` |
| `src/moneylab/knowledge/__pycache__/model.cpython-314.pyc` | 5915 | `2026-11-13T09:56:36.694447200Z` |
| `src/moneylab/knowledge/__pycache__/query.cpython-314.pyc` | 14972 | `2026-11-13T09:56:36.715175800Z` |
| `src/moneylab/knowledge/__pycache__/load.cpython-314.pyc` | 4296 | `2026-11-13T09:56:36.719697600Z` |
| `src/moneylab/knowledge/__pycache__/validate.cpython-314.pyc` | 32944 | `2026-11-13T09:56:36.729868400Z` |
| `src/moneylab/knowledge/__pycache__/__main__.cpython-314.pyc` | 10408 | `2026-11-13T09:56:36.754963100Z` |

### 소스로 확인한 사실

Ce1 기준이며, base·작업 파일·SOURCE_WORKTREE HEAD와 같은 Git 객체다.

- 자식 argv는 `sys.executable`, `-m`, `moneylab.knowledge`, `--root`, `<root>`, `validate`이며 `-B`가 없다.
- 자식 환경은 `PATH`와 `SYSTEMROOT`만 담고 `PYTHONDONTWRITEBYTECODE`를 전달하지 않는다.
- `src`에는 바이트코드 기록을 끄는 코드가 없다.
- 상위 Python에 준 `-B`는 자식에게 전달되지 않는다.

### 원인 추론 (관측 사실 아님)

- 관측된 캐시는 E3의 `run_action`이 실행한 자식 프로세스가 생성했을 가능성이 높다.
- 근거는 두 가지다. 위의 소스 사실, 그리고 캐시에 자식이 import하는 `moneylab`과 `moneylab.knowledge` 계열만 있고 `-B`로 실행한 상위 프로세스만 import하는 모듈은 없다는 점이다.

### 증거 한계

- 특정 프로세스가 파일을 생성하는 행위를 직접 확인하지 못했다.
- E3 실행 시각과 직접 대조할 자료가 없다.
- 생성 구간은 E2 직후 확인부터 E6 이전까지로만 확정된다.
- 캐시 파일 내용은 읽지 않았다.

### 설계 누락 (DEVIATIONS #9)

- 계약 후보 작성자는 자식 argv와 환경 구성을 알고 있었다. 그런데도 Work Order의 산출물 범위 문장에 자식의 바이트코드 생성 가능성을 반영하지 않았다.
- 승인된 E0–E6 명령은 승인 원문대로 각 1회 실행되었다. 실행 자체에는 일탈이 없었다.

### 메타데이터 감사 (Ce2 이후 최초 D15 감사)

- 결과:
  - HEAD = Ce2, tree 일치
  - 계약 3개의 작업 파일과 HEAD blob 해시가 승인값과 일치
  - tracked·staged·untracked 변경 0
  - ignored 디렉터리 목록이 ERRATA-002 D14 기준과 같음
  - 캐시 8개의 상대 경로, 바이트, 수정 시각이 위 표와 나노초 단위까지 일치
  - 두 캐시 디렉터리 안에 추가 파일이나 하위 디렉터리 없음
- 확인하지 못한 범위:
  - 내용 해시가 일치하는지
  - 메타데이터는 같고 내용만 바뀐 경우
  - 관측과 관측 사이의 중간 변경
  - snapshot·runlog 기록 내부의 파일 수와 내용 (디렉터리 존재만 확인)

### 계약 처리

- ERRATA-002는 이 불일치와 DEVIATIONS #9를 이력으로 고정했다.
- 이 사건에 한해 문서화 task의 완료 조건을 정했다.
- 과거 실행을 계약 준수로 소급 변경하지 않으며, 통합 시험 FAIL을 바꾸지 않는다.
- 새 실행 권한, 원본 재조회 권한, 캐시 생성·정리 권한은 추가하지 않았다.
- 캐시, snapshot, runlog 기록을 삭제·수정하는 조치는 수행하지 않았다(CLAUDE_REPORTED). 캐시 파일 목록·크기·수정 시각과 기록 디렉터리 존재는 감사 범위에서 확인했다. 캐시 내용과 snapshot·runlog 기록 내부의 불변은 재확인하지 않았다.

## 6. 운영 부담과 한계

### 운영 부담

- 모든 단계가 사람의 단계별 승인과 중계를 거쳤다.
- E6 이후 원인 조사 1회, 추가 ERRATA 1건, 추가 커밋 1개와 그에 따른 승인 단계가 필요했다.
- 승인 횟수, 경과 시간, 토큰·비용: 미집계.

### 입증하지 못한 것

- 중복 실행 통제(실행 전 시도 기록과 중복 실행 통제 기능이 없음)
- 무인 운영 준비
- 실행 사실의 인증
- 다른 환경에서의 재현
- executor 자식 프로세스와 작업 API 내부 git 프로세스에 대한 Guard 적용
- 예외 경계 밖의 인터프리터 시작·종료 동작

### 이벤트 누적

- 누적 Guard DENY: 5건. AUTO-04 단계에서 새로 생긴 DENY는 0건이다.
- 누적 DEVIATIONS: 9건. AUTO-04에서 추가된 항목은 2건이다.
  - #8: C1 작성 전 메모리 대조 생략. 사용자가 수락했다.
  - #9: 위 설계 누락.

### 후속 task 참고 (이 task의 허용 아님)

- 자식 실행의 바이트코드 기록은 별도 Work Order에서 다룬다. 계약 산출물 범위에 명시하거나, 자식 실행 설정을 바꾸는 코드 변경으로 처리한다.
