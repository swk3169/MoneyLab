# ERRATA: AUTO-02 ERRATA-003

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: AUTO-02-ERRATA-003
TASK_ID: AUTO-02
TARGET_WORK_ORDER: docs/tasks/AUTO-02/WORK_ORDER.md @ d198cbbaa3719ffcdece4ed1abc2f410279aeb77 (sha256 10b484c1625f5660a7f04a6ae4d3de3269e500b11e5ef3e2fc0e36eceaa886e5)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자, 2026-11-12

## CHANGED_FIELDS

CHANGED_FIELDS:
- PROTECTED_FILES (전체, INVARIANT 포함)
- ALLOWED_ACTIONS.COMMIT
- ALLOWED_ACTIONS.PR_CI
- DESIGN_CONTRACT.D10
- FORBIDDEN_ACTIONS
- ACCEPTANCE_CRITERIA.평가 시점, ACCEPTANCE_CRITERIA.AC1, ACCEPTANCE_CRITERIA.AC2, ACCEPTANCE_CRITERIA.AC3, ACCEPTANCE_CRITERIA.AC4, ACCEPTANCE_CRITERIA.AC7, ACCEPTANCE_CRITERIA.AC8, ACCEPTANCE_CRITERIA.AC9, ACCEPTANCE_CRITERIA.AC16, ACCEPTANCE_CRITERIA.AC20, ACCEPTANCE_CRITERIA.AC21 (신설)
- TEST_GATES
- E2E_GATES
- REQUIRED_EVIDENCE
- STOP_CONDITIONS

## RATIONALE

RATIONALE: PR #47(head 387ec92fe5daf584a418a67789a48af9020c7533)의 CI run 43158870163에서 ci-tests / pytest (Windows)는 SUCCESS였고, 로컬에서 NOT_RUN_PLATFORM이던 collect-untracked-symlink와 verify-record-symlink가 PASSED로 실행됐다. pytest-linux-experimental(ubuntu-26.04)에서는 tests/test_workstate_store.py::test_real_junction_as_store_directory_is_refused가 실패했다. Linux에서 저장 경로 구성 요소 data/processed/workstate를 디렉터리 symlink로 만들면, snapshot 결과가 기대값 STORE_PATH_INVALID가 아니라 GIT_FAILED였다(tests/test_workstate_store.py:149). 현재 D10은 (1) git check-ignore를 (2) 기존 구성 요소 D6 검사보다 먼저 수행하도록 순서를 고정한다. 구현도 그 순서를 따르며, check-ignore의 종료 코드가 0·1이 아니면 D4에 따라 GIT_FAILED가 된다. GIT_FAILED를 낸 호출이 check-ignore이고 Linux git이 symlink 너머의 경로를 거부했다는 것은 가설이다. stderr는 설계상 저장하지 않으므로 확정하지 않는다. 이 ERRATA는 오류 코드를 바꿔 실패를 숨기지 않는다. 대신 이미 존재하는 저장 경로 구성 요소의 링크 검사를 Git 호출보다 앞으로 옮긴다. 저장 전 ignore 확인은 유지한다. 기존 구현 커밋 I1은 보존하고 수정은 새 커밋 I2로 한다(amend·force push 금지). ERRATA-001과 ERRATA-002는 바뀌지 않고 유효하다. 같은 필드를 이 ERRATA가 다시 정하면 이 ERRATA의 값이 앞선 ERRATA의 값을 포함해 대체한다(번호 규칙). 로컬의 NOT_RUN_PLATFORM 이력과 I1의 Windows CI 실행 증거는 그대로 유지한다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- PROTECTED_FILES:
  - docs/tasks/AUTO-02/** (C1의 WORK_ORDER.md, Ce1의 ERRATA-001.md, Ce2의 ERRATA-002.md, Ce3의 ERRATA-003.md 최초 생성만 예외; 이후 불변)
  - docs/** 중 docs/tasks/README.md를 제외한 전부
  - src/** 중 src/moneylab/workstate/**와 src/moneylab/storage/atomic.py를 제외한 전부(src/moneylab/automation/** 포함)
  - tests/** 중 ALLOWED_FILES의 테스트 파일 6개를 제외한 전부(tests/test_automation_*.py, tests/test_atomic_storage.py 포함)
  - .claude/**, .github/**, .gitignore, .gitattributes
  - pyproject.toml, requirements.txt, requirements-dev.txt
  - configs/**, knowledge/**, data/**, examples/**
  - README.md, ARCHITECTURE.md, LICENSE, .env.example, CLAUDE.md
  - INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅. C1의 docs/tasks/AUTO-02/WORK_ORDER.md, Ce1의 docs/tasks/AUTO-02/ERRATA-001.md, Ce2의 docs/tasks/AUTO-02/ERRATA-002.md, Ce3의 docs/tasks/AUTO-02/ERRATA-003.md 최초 생성은 docs/tasks/README.md 규칙에 따른 별도 예외이며 ALLOWED_FILES 12개에 속하지 않는다.
- ALLOWED_ACTIONS.COMMIT:
  - I1: 387ec92fe5daf584a418a67789a48af9020c7533 `feat(workstate): add state snapshot and verify`(ERRATA-002의 COMMIT으로 이미 생성됨, 보존)
  - I2: HEAD = Ce3에서 `git add -- src/moneylab/workstate/store.py tests/test_workstate_store.py`, 커밋 하나 `fix(workstate): validate store paths before git ignore check`. 다른 경로는 stage하지 않는다.
- ALLOWED_ACTIONS.PR_CI: docs/tasks/README.md §13. TARGET_BRANCH의 열린 PR #47이 있으면 새 PR을 만들지 않는다. 이 ERRATA가 PR 본문에 대해 허용하는 최대 범위는 `gh pr edit 47 -R swk3169/MoneyLab --body <본문>` 1회이다. 실제 실행에는 별도 PR_CI Gate Authorization이 PR_BODY_EDIT: YES와 정확한 최종 본문을 명시해야 하며, 이 ERRATA 자체는 실행 승인이 아니다. 실행 후 PR 본문 SHA-256을 보고한다. 본문 파일이 필요하면 scratchpad 파일 1개만 만들고 지우지 않으며 경로를 보고한다. 명시가 없으면 본문을 수정하지 않는다. PR이 없으면 기존 PR_CI 규칙(PR_CREATE)을 따른다. CI 재실행은 별도 승인이다.
- DESIGN_CONTRACT.D10: D10 저장(snapshot만): 경로 `<root>/data/processed/workstate/<TASK_ID>/<snapshot_id>.json`. 순서: (1) 경로 검사(이 단계에서는 Git을 호출하지 않는다): 먼저 최종 파일 경로가 root 아래인지 문자열로만 확인한다(파일 시스템 접근 없음, 아니면 `STORE_PATH_INVALID`). 그다음 `data`, `processed`, `workstate`, `<TASK_ID>` 중 이미 존재하는 구성 요소를 위에서 아래로 lstat해 D6으로 검사한다. symlink·junction·reparse point이거나 디렉터리가 아니면 `STORE_PATH_INVALID`이다. (2) 최종 파일 경로에 `git check-ignore -q`로 ignored 확인(아니면 `STORE_PATH_INVALID`). 종료 코드가 0·1이 아니면 D4대로 `GIT_FAILED`이며 다른 코드로 바꾸지 않는다. (1)과 (2) 사이에 생긴 경로 변화로 (2)가 실패해도 같다. (3) `data`, `processed`, `workstate`, `<TASK_ID>` 중 없는 디렉터리를 위에서 아래로 하나씩 `os.mkdir`로 생성(`parents=True` 금지). 생성 직후 그 디렉터리를 D6으로 재검사한다. `FileExistsError`면 그 경로를 lstat으로 재검사해 링크·junction·reparse가 아닌 일반 디렉터리일 때만 계속하고, 아니면 `STORE_PATH_INVALID`. 마지막 구성 요소까지 끝난 뒤 그 디렉터리의 resolve 결과가 root 밖이면 `STORE_PATH_INVALID`. (4) `storage.atomic.atomic_create_new_bytes`로만 쓴다. 결과: (a) 새로 생성: `STORED`. (b) `CreateNewError.cause`가 `FileExistsError`: 기존 파일을 D11의 3·5·6·7·8단계로 검증한다(2단계 root 확인은 이 snapshot 실행에서 이미 통과한 같은 root를 쓰고, 4단계 존재는 확정된 것으로 본다). 오류 코드는 verify와 같다. 검증을 통과하고 schema·task_id·state·reported가 새 객체와 같으면 기존 파일과 meta를 보존하고 `ALREADY_STORED`, 객체가 다르면 `SNAPSHOT_CORRUPT`이며 기존 파일은 바꾸지 않는다. 동시 실행에서 link에 진 쪽도 같은 규칙을 따른다. (c) `final_created=True`(link 후 tmp 정리 실패): `STORED`와 warning `TMP_LEFTOVER:<파일 이름>`. (d) 그 밖의 `CreateNewError`: `STORE_FAILED`이며 `tmp_leftover`가 있으면 warning `TMP_LEFTOVER:<파일 이름>`. (b)에서 `tmp_leftover`가 있으면 결과에 같은 warning을 붙인다. 오류로 끝날 때 이 실행이 만든 디렉터리는 지우지 않고 warning `DIR_LEFT:<root 기준 상대 경로>`로 보고한다. 성공 시 만든 디렉터리는 warning이 아니다. 덮어쓰기·`os.replace` 대체·삭제·정리 경로는 없다. verify는 디렉터리·파일을 만들지 않는다. D13의 "D10 (4)에 도달"은 이 (4)를 뜻한다.
- FORBIDDEN_ACTIONS:
  - 승인된 gate 밖의 행위, ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
  - Work Order·ERRATA 수정
  - `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
  - C1·Ce1·Ce2·I1·Ce3의 이력 변경 또는 대체
  - hooks·settings·.claude·.github 변경 또는 guard 우회, guard deny된 명령의 변형 재시도
  - 다른 branch·worktree·untracked·ignored·reference 산출물 정리
  - 실제 저장소(TARGET_WORKTREE 포함)에서 snapshot 실행, `data/processed/workstate/` 또는 그 안의 파일 생성(테스트는 tmp 저장소만 사용)
  - `storage/atomic.py` 기존 함수·상수의 동작·시그니처 변경, D14가 허용한 타입 주석 1줄 외의 기존 줄 삭제·수정
  - 기존 테스트의 삭제·수정·skip·xfail 추가·단정 완화. 예외는 둘뿐이다: (i) D18이 정한 tests/test_upbit_replay.py 단정 1줄 변경, (ii) I1→I2에서 tests/test_workstate_store.py에 새 테스트를 추가하는 것(기존 줄의 삭제·수정은 예외가 아니며 금지).
  - I1→I2에서 src/moneylab/workstate/store.py의 `save_record` 함수 밖 변경. `save_record` 안에서도 D10 순서를 맞추기 위한 기존 단계의 이동과 그 함수의 docstring·주석 갱신만 허용한다. 판정 조건, 오류 코드, detail 문구, 다른 함수의 변경은 금지한다.
  - I1→I2에서 ALLOWED_FILES의 나머지 10개 파일 변경
  - check-ignore 실패나 Linux 실패를 숨기기 위한 오류 코드 변환, 플랫폼 조건부 skip·xfail 추가, 기존 실제 링크 테스트의 단정·case ID 변경
  - symlink·junction 테스트를 위한 권한 상승·OS 설정 변경
- ACCEPTANCE_CRITERIA.평가 시점: I2 커밋 전에는 AC1–AC3을 Ce3과 현재 작업 파일·index의 후보 변경으로, I2 커밋 후에는 commit 간 비교로 확정한다. 존재하지 않는 커밋·PR·CI의 검사를 PASS로 보고하지 않는다. I1 기준으로 이미 보고한 결과는 이력으로 유지하고 I2 기준 결과와 구분한다. AC20과 AC21은 PR_CI gate에서만 평가한다. 그 전의 gate(IMPLEMENTATION, PRECOMMIT_AUDIT, COMMIT, CLEAN_COMMIT_E2E, PUSH)에서는 NOT_YET_APPLICABLE이다. 이 상태는 PARTIAL이 아니며, 그 gate의 중단 사유도, `<GATE>_PASS`가 YES가 되지 못하는 사유도 아니다.
- ACCEPTANCE_CRITERIA.AC1: 다음 이력이 성립한다. C1 parent = CANONICAL_BASE_SHA, C1 변경 = docs/tasks/AUTO-02/WORK_ORDER.md(A) 하나. Ce1(35411875e24851e60bbc6d8975a0d827d43df35b) parent = C1, 변경 = docs/tasks/AUTO-02/ERRATA-001.md(A) 하나. Ce2(6d83f348623964280d3ef146838a1fa9ba1b973b) parent = Ce1, 변경 = docs/tasks/AUTO-02/ERRATA-002.md(A) 하나. I1(387ec92fe5daf584a418a67789a48af9020c7533) parent = Ce2, `git diff --name-status <Ce2> <I1>` = ALLOWED_FILES 12개와 A/M 표기 일치. Ce3 parent = I1, 변경 = docs/tasks/AUTO-02/ERRATA-003.md(A) 하나. I2 parent = Ce3, `git diff --name-status <Ce3> <I2>` = `M src/moneylab/workstate/store.py`, `M tests/test_workstate_store.py` 정확히 두 개. base→I2 전체 변경 = 계약 4개(WORK_ORDER.md, ERRATA-001.md, ERRATA-002.md, ERRATA-003.md) ∪ ALLOWED_FILES 12개, 합계 16개이고, ALLOWED_FILES의 base 대비 A/M 표기는 ERRATA-002와 같다.
- ACCEPTANCE_CRITERIA.AC2: I1→Ce3의 변경은 docs/tasks/AUTO-02/ERRATA-003.md 하나이고, Ce3→I2의 PROTECTED_FILES diff는 비어 있다. Work Order blob 내용 SHA-256은 승인값(10b484c1625f5660a7f04a6ae4d3de3269e500b11e5ef3e2fc0e36eceaa886e5), ERRATA-001은 수락값(e1f788dba33f807a8284ee6c58735d275cd85bb58879dd7fa9bc4fbc115130c8), ERRATA-002는 수락값(770bae80b286275ea986464cfc45008c5704d4e98653077c37d4aee4e25af71b), ERRATA-003은 Ce3 생성 때 보고한 수락값과 같다. 넷 다 이후 불변이고 작업 파일 해시도 같다.
- ACCEPTANCE_CRITERIA.AC3: (a) base→I2: `git diff --numstat <CANONICAL_BASE_SHA> <I2>`에서 base에 있던 파일은 세 개만 변경된다. docs/tasks/README.md는 삭제 수 0이다. src/moneylab/storage/atomic.py는 삭제 수가 정확히 1이고, 삭제 줄은 `    removed = []`, 대응 추가 줄은 `    removed: list[Path] = []`이다. tests/test_upbit_replay.py는 추가 1·삭제 1이고, 삭제 줄과 추가 줄은 D18의 변경 전·후 줄과 정확히 같다. 이 세 파일에 그 밖의 삭제·수정 줄은 없다. I1에서 새로 추가된 ALLOWED_FILES 9개는 base 대비 추가만 있다(삭제 수 0). (b) I1→I2: `git diff --numstat <I1> <I2>`에서 tests/test_workstate_store.py는 삭제 수 0(추가만)이다. src/moneylab/workstate/store.py의 변경 hunk는 모두 `save_record` 함수 안에 있고, 그 내용은 D10 순서에 맞춘 기존 단계의 이동과 그 함수의 docstring·주석 갱신뿐이다(`git diff -U0` hunk 위치와 수동 대조로 확인). ALLOWED_FILES의 나머지 10개 파일은 I1→I2 diff가 0이다.
- ACCEPTANCE_CRITERIA.AC4: 기준선의 `pytest --collect-only -q` 테스트 ID가 모두 I2에서도 수집되고(감소 0), I1에서 수집된 테스트 ID도 모두 I2에서 수집된다(감소 0). base에 있던 기존 테스트 파일의 base→I2 diff는 D18의 tests/test_upbit_replay.py 1줄 변경을 제외하면 0이다.
- ACCEPTANCE_CRITERIA.AC7: 거부·불안정: unborn, unmerged, 진행 중 merge, skip-worktree, assume-unchanged 각각 UNSUPPORTED_STATE. 변경·untracked·계약 경로 또는 그 상위 디렉터리의 symlink·junction·reparse는 오류 주입 단위 테스트에서 항상 UNSUPPORTED_STATE이고, 실제 링크 통합 케이스는 D17을 따른다. 수집 중 파일 변경 주입은 UNSTABLE_STATE. 각 상한 초과 주입(stdout·stderr·blob·W 파일·경로 수·경로 길이·합계)은 LIMIT_EXCEEDED이고 자식 프로세스가 회수됨. git 비정상 종료·timeout 주입은 GIT_FAILED. 모두 종료 2, MATCH 아님, 저장 없음. 실제 링크 통합 케이스 collect-untracked-symlink는 로컬에서 NOT_RUN_PLATFORM(Windows winerror 1314)으로 미실행됐고, 이 이력은 유지한다. 같은 케이스는 I1(387ec92fe5daf584a418a67789a48af9020c7533)의 CI run 43158870163 Windows job 130985091047에서 PASSED로 나열돼 실행·통과했다(INDEPENDENT). 이 증거도 유지한다. I2 기준 판정은 AC20에서 I2 head의 Windows job이 같은 테스트를 다시 PASSED로 나열할 때 완료된다. 그 전까지 로컬 판정은 PARTIAL (NOT_RUN_PLATFORM: collect-untracked-symlink)로 기록한다.
- ACCEPTANCE_CRITERIA.AC8: 저장: ignored 아닌 경로, 저장 경로 구성 요소의 symlink·junction·reparse(오류 주입 단위 테스트 필수, 실제 링크는 D17), root 밖 경로는 STORE_PATH_INVALID이며 기록 파일 생성 없음. `data`·`processed`·`workstate`·`<TASK_ID>`가 없는 tmp 저장소에서 snapshot은 위에서 아래로 생성 후 STORED. mkdir 중 FileExistsError 주입 시 일반 디렉터리면 계속하고, 링크·비디렉터리면 STORE_PATH_INVALID. 이후 단계 실패 시 만든 디렉터리는 남고 `DIR_LEFT` warning. verify는 디렉터리를 만들지 않음. 같은 ID 재실행(meta 시각만 다름)은 ALREADY_STORED이고 기존 파일 바이트·meta 불변이며 반환 file_sha256 = 기존 파일 바이트 해시. 새로 쓴 STORED의 file_sha256 = 생성된 파일 바이트 해시. 같은 ID의 기존 파일이 D11 검증(3·5·6·7·8단계)에 실패하면 해당 오류(STORE_PATH_INVALID, SNAPSHOT_UNREADABLE, SNAPSHOT_CORRUPT, SNAPSHOT_INCOMPATIBLE)를 반환하고, 검증은 통과했으나 ID 대상 객체(schema·task_id·state·reported)가 새 객체와 다르면 SNAPSHOT_CORRUPT를 반환하며, 두 경우 모두 기존 파일을 보존한다. 유효한 meta 차이만으로는 CORRUPT로 판정하지 않고 ALREADY_STORED이다. 두 스레드·두 프로세스가 같은 ID를 동시에 쓰면 파일 1개, 한쪽 STORED·다른 쪽 ALREADY_STORED, 두 file_sha256 동일. link 후 tmp 정리 실패 주입은 STORED, `TMP_LEFTOVER` warning, exit 1, final_file_created true. link 전 실패와 tmp 삭제 실패 동시 주입은 STORE_FAILED, `TMP_LEFTOVER` warning, final_file_created false, 최종 파일 없음. 1 MiB 초과 기록은 LIMIT_EXCEEDED이며 생성 없음. 추가 조건(D10 순서): 이미 존재하는 저장 경로 구성 요소가 링크·junction·reparse(오류 주입 단위 테스트)일 때, 저장 경로가 git에서 ignored가 아니어도 결과는 STORE_PATH_INVALID이고 detail은 그 구성 요소의 링크 문구이며 그 실행에서 `check-ignore` 호출은 0회다. 링크가 없는 정상 snapshot에서는 `check-ignore`가 기존 구성 요소 검사 뒤, 디렉터리 생성 전에 1회 호출된다. 호출 여부와 순서는 실제 `collect.run_git`에 위임하면서 하위 명령만 기록하는 감시(spy)로 확인하며 git 결과를 대체하지 않는다. 기존 실제 링크 테스트(store-directory-link: test_real_junction_as_store_directory_is_refused)의 단정은 그대로 유지한다. 실제 링크 통합 케이스에 NOT_RUN_PLATFORM이 있으면 이 AC는 PARTIAL이다.
- ACCEPTANCE_CRITERIA.AC9: verify 오류: 없음 SNAPSHOT_NOT_FOUND(file_sha256 null), 읽기 오류 SNAPSHOT_UNREADABLE(null), 기록 파일이 symlink·junction이면 STORE_PATH_INVALID, 링크가 아닌 비정규 파일(디렉터리 등)·1 MiB 초과는 SNAPSHOT_CORRUPT(null), 바이트 1개 변경·비canonical·중복 키·파일 이름 불일치·task_id 불일치는 SNAPSHOT_CORRUPT(file_sha256 = 실제 파일 바이트 해시), 알 수 없는 schema 문자열은 SNAPSHOT_INCOMPATIBLE. 모두 종료 2, 다른 파일로 대체 없음, 파일 삭제 없음, 디렉터리 생성 없음. 실제 링크 통합 케이스 verify-record-symlink는 로컬에서 NOT_RUN_PLATFORM(Windows winerror 1314)으로 미실행됐고, 이 이력은 유지한다. 같은 케이스는 I1(387ec92fe5daf584a418a67789a48af9020c7533)의 CI run 43158870163 Windows job 130985091047에서 PASSED로 나열돼 실행·통과했다(INDEPENDENT). 이 증거도 유지한다. I2 기준 판정은 AC20에서 I2 head의 Windows job이 같은 테스트(test_real_symlinked_record_is_refused)를 다시 PASSED로 나열할 때 완료된다. 그 전까지 로컬 판정은 PARTIAL (NOT_RUN_PLATFORM: verify-record-symlink)로 기록한다.
- ACCEPTANCE_CRITERIA.AC16: I2 코드의 IMPLEMENTATION 전체 pytest와 I2 커밋의 CLEAN_COMMIT_E2E 전체 pytest가 각각 failed 0 / errors 0이다(CLAUDE_REPORTED). NOT_RUN_PLATFORM skip은 별도 목록으로 보고한다. I1 기준 실행 결과는 이력으로 구분한다.
- ACCEPTANCE_CRITERIA.AC20: PR_CI에서 PR #47의 head가 I2와 같고, 그 head의 ci-tests / pytest (Windows)가 SUCCESS이다(INDEPENDENT). 그 job 로그(`-rfEsxXp`)에서 collect-untracked-symlink(test_real_untracked_symlink_is_unsupported), verify-record-symlink(test_real_symlinked_record_is_refused), store-directory-link(test_real_junction_as_store_directory_is_refused), collect-untracked-directory-link(test_real_untracked_directory_link_is_unsupported)가 PASSED로 나열되고, NOT_RUN_PLATFORM skip이 없다. 이것은 테스트 이름별 직접 증거다. PR_CI 이전 gate에서는 NOT_YET_APPLICABLE이다(평가 시점 참조).
- ACCEPTANCE_CRITERIA.AC21: PR_CI에서 같은 I2 head의 pytest-linux-experimental에 대해 다음을 모두 충족해야 한다(INDEPENDENT). (a) 로그 완전성: 그 job의 로그를 생략 없이 조회했고(잘림·"log truncated" 같은 생략 표시 없음), pytest 세션 시작부터 최종 집계 행까지 포함된다. (b) 실패 범위: AUTO-02 테스트 파일 5개(tests/test_workstate_collect.py, tests/test_workstate_store.py, tests/test_workstate_cli.py, tests/test_workstate_isolation.py, tests/test_atomic_create_new.py)와 tests/test_upbit_replay.py의 FAILED·ERROR가 0이다. (c) 링크 대상 검사 4개의 파일 단위 추론 증거: 대상은 store-directory-link(tests/test_workstate_store.py::test_real_junction_as_store_directory_is_refused), verify-record-symlink(tests/test_workstate_store.py::test_real_symlinked_record_is_refused), collect-untracked-symlink(tests/test_workstate_collect.py::test_real_untracked_symlink_is_unsupported), collect-untracked-directory-link(tests/test_workstate_collect.py::test_real_untracked_directory_link_is_unsupported)이다. 대상 파일 tests/test_workstate_store.py와 tests/test_workstate_collect.py 각각에 대해 다음이 모두 성립한다: 진행 표시의 결과 문자(여러 줄로 나뉘면 합산)가 `.`뿐이고 F·E·s·x가 없다. 결과 문자 수가 E2E_GATES에서 기록한 I2의 파일별 수집 수와 같다. 해당 파일의 SKIPPED·XFAIL·FAILED·ERROR 행이 없다. (d) 플랫폼별 수집 조건: I2의 두 대상 파일에 수집 단계에서 플랫폼에 따라 달라지는 조건(모듈·데코레이터 수준 skipif, 플랫폼 조건부 테스트 정의·매개변수, 수집 훅)이 없음을 소스에서 확인한다. 있으면 Linux 기대 수집 수를 계산해 (c)의 대조에 쓰고 근거를 보고한다. 계산할 수 없으면 미확인이다. (e) 판정 표기: (c)는 테스트 이름별 직접 증거가 아니라 파일 단위 추론이며 보고에 그렇게 표기한다. (a)–(d) 중 하나라도 충족하지 못하거나 로그 일부가 생략됐거나 수가 맞지 않으면 AC21은 미확인으로 기록하고 MERGE는 진행하지 않는다. job 전체 SUCCESS는 요구하지 않는다. tests/test_agent_guard.py의 기존 wrapper 실패 2건(.github/workflows/ci-tests.yml에서 Linux 실패가 예상된다고 적힌 항목)은 이름과 함께 별도로 보고하며 AC21 판정에 넣지 않는다. 그 밖의 실패는 AUTO-02 파일이 아니어도 원인이 불명이면 이름과 함께 보고하고 MERGE 전에 사용자 결정을 받는다. PR_CI 이전 gate에서는 NOT_YET_APPLICABLE이다(평가 시점 참조).
- TEST_GATES:
  - 신규 테스트 파일 5개 targeted 실행 통과(D17의 NOT_RUN_PLATFORM은 통과로 세지 않음)
  - ruff(CI와 같은 명령): `.\.venv\Scripts\python.exe -m ruff check --no-cache --select E4,E7,E9,F src tests`
  - mypy(CI와 같은 명령): `.\.venv\Scripts\python.exe -m mypy`
  - mypy(명시적 경로 추가 보장, CLAUDE_REPORTED): `.\.venv\Scripts\python.exe -m mypy src/moneylab/workstate src/moneylab/storage/atomic.py` 오류 0
  - IMPLEMENTATION에서 I2 후보 코드로 전체 pytest 1회 `./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q -rs`, failed 0 / errors 0
  - `git diff --check` 깨끗함, Ce3 대비 변경 파일 집합 = `src/moneylab/workstate/store.py`, `tests/test_workstate_store.py`, PROTECTED diff 0
  - README §14 BGA-8 (A) 수동 확인: 추가한 순서 테스트, spy 사용 범위, skip 추가 여부를 그대로 보고한다. (B)는 "독립 검토 필요"로 보고한다.
- E2E_GATES:
  - clean I2 커밋에서 전체 pytest 1회와 AC1–AC19 확인. AC16의 IMPLEMENTATION 실행과 이 실행을 구분한다. AC20·AC21은 NOT_YET_APPLICABLE로 보고한다.
  - clean I2 커밋에서 `./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q tests/test_workstate_store.py tests/test_workstate_collect.py` 1회로 파일별 수집 수를 기록한다(AC21 대조용). 출력은 파일로 리디렉션하지 않는다.
  - 실제 저장소에서 `./.venv/Scripts/python.exe -B -m moneylab.workstate verify --task-id AUTO-02 --snapshot-id 0000000000000000000000000000000000000000000000000000000000000000` 1회: 종료 2, status SNAPSHOT_NOT_FOUND, file_sha256 null, final_file_created null, 실행 전후 `git status --porcelain=v2 --ignored` 동일, `data/processed/workstate/` 미생성. stdout·stderr를 파일로 리디렉션하지 않는다.
  - 실제 저장소에서 snapshot 실행 금지
  - `git diff --name-only <CANONICAL_BASE_SHA> <I2> -- src tests`가 ALLOWED_FILES의 src·tests 경로 11개와 같음
- REQUIRED_EVIDENCE:
  - GIT_VERIFIABLE: base·C1·Ce1·Ce2·I1·Ce3·I2 SHA·parent·tree, ALLOWED_FILES blob 전후, `git diff --numstat`, 변경 파일 집합, merge parent·tree
  - CLAUDE_REPORTED: pytest·ruff·mypy·E2E 결과, 파일별 수집 수, AC 확인, BGA-8 (A), NOT_RUN_PLATFORM 목록
  - INDEPENDENT: PR CI의 ci-tests / pytest (Windows)와 그 실행에서의 플랫폼 케이스 실행 여부(테스트 이름별 직접 증거), pytest-linux-experimental의 AC21 판정 근거(파일 단위 추론으로 표기), 사용자 검토. BGA-8 (B)는 "독립 검토 필요"로 보고
- STOP_CONDITIONS:
  - base·HEAD·tree·BASE_BLOBS 불일치, Work Order·ERRATA-001·ERRATA-002·ERRATA-003 sha256(blob·작업 파일) 불일치, D16 앵커 불일치
  - C1·Ce1·Ce2·I1·Ce3·I2의 parent 또는 변경 집합이 AC1과 다름
  - ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅, A/M 표기 불일치
  - 기존 줄의 허용되지 않은 삭제·수정: base→I2에서 README.md 삭제 수 > 0, atomic.py 삭제 수 > 1 또는 삭제 줄이 D14 예외 줄이 아님, tests/test_upbit_replay.py에서 삭제 수 > 1 또는 변경 줄이 D18의 줄이 아님. I1→I2에서 tests/test_workstate_store.py 삭제 수 > 0, store.py 변경이 `save_record` 밖이거나 그 안에서 단계 이동·docstring·주석 갱신 외의 변경, 나머지 10개 ALLOWED_FILES의 변경. 그 밖의 기존 테스트 변경·약화
  - 실제 저장소에서 snapshot 실행 또는 `data/processed/workstate/` 생성
  - guard deny, 예상하지 못한 ASK, 편집·commit·push·PR 수정 승인 창 거절·무응답
  - 테스트·ruff·mypy 실패·에러(BUNDLE 안에서는 README §14 BGA-4·BGA-10), AC 불충족
  - NOT_RUN_PLATFORM으로 PARTIAL AC 발생(BUNDLE 안에서는 그 gate 보고에서 STOP, 개별 진행에서도 gate PASS는 YES가 아님)
  - PR_CI 또는 MERGE 단계에서 AC20 또는 AC21이 미확인이거나 불충족(MERGE 진행 금지). PR_CI 이전 gate의 NOT_YET_APPLICABLE은 이 조건에 해당하지 않는다.
  - 대상 파일 시스템에서 os.link를 쓸 수 없음(대체 구현 없이 STOP, PROPOSED_ERRATA로 보고)
  - 계약 모순, 상위 규칙과 충돌, 예상하지 못한 untracked 파일

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다. ALLOWED_FILES는 ERRATA-002의 12개 그대로다.
- Work Order, ERRATA-001, ERRATA-002 파일은 수정하지 않는다. 여기 적지 않은 필드는 Work Order, ERRATA-001, ERRATA-002의 값이 그대로 유효하다.
- I1(387ec92fe5daf584a418a67789a48af9020c7533)은 보존한다. 수정은 I2 새 커밋으로만 하며 amend·force push·rebase로 이력을 바꾸지 않는다. PUSH는 기존 규칙(`git push -u origin feature/auto-02-workstate`, fast-forward)을 따른다.
- Ce3은 HEAD = I1에서 이 파일 하나만 `git add -- docs/tasks/AUTO-02/ERRATA-003.md`로 stage해 `docs(task): add AUTO-02 ERRATA-003` 커밋 1회로 만든다. Ce3 직전 index에는 이 파일 외 항목이 없어야 하고 작업 트리는 clean이어야 한다.
- IMPLEMENTATION으로의 후퇴는 Ce3 이후 별도 Gate Authorization으로만 한다(README §14 BGA-1: ERRATA 고정과 후퇴는 묶을 수 없다).
- D10 변경, 추가한 순서 테스트, spy 사용은 README §14 BGA-8 (B)의 검토 대상이며 "독립 검토 필요"로 보고하고 PASS로 단정하지 않는다.
- PR #47 본문의 "15개 파일"과 로컬 검증 수치는 I2 이후 오래된 값이 된다. 이 ERRATA는 ALLOWED_ACTIONS.PR_CI의 `gh pr edit` 1회를 최대 범위로 허용할 뿐이며, 실제 반영은 별도 PR_CI Gate Authorization(PR_BODY_EDIT: YES와 정확한 최종 본문)으로만 한다.
