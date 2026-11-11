# ERRATA: AUTO-02 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: AUTO-02-ERRATA-001
TASK_ID: AUTO-02
TARGET_WORK_ORDER: docs/tasks/AUTO-02/WORK_ORDER.md @ d198cbbaa3719ffcdece4ed1abc2f410279aeb77 (sha256 10b484c1625f5660a7f04a6ae4d3de3269e500b11e5ef3e2fc0e36eceaa886e5)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자, 2026-11-11

## CHANGED_FIELDS

CHANGED_FIELDS:
- PROTECTED_FILES (첫 항목과 INVARIANT)
- DESIGN_CONTRACT.D14
- FORBIDDEN_ACTIONS
- ACCEPTANCE_CRITERIA.평가 시점, ACCEPTANCE_CRITERIA.AC1, ACCEPTANCE_CRITERIA.AC2, ACCEPTANCE_CRITERIA.AC3
- STOP_CONDITIONS

## RATIONALE

RATIONALE: TEST_GATES·AC19의 명시적 mypy 대상인 src/moneylab/storage/atomic.py는 CANONICAL_BASE의 기존 98행 `removed = []`(cleanup_tmp)에서 mypy var-annotated 오류가 난다. 이 줄은 기존 줄 수정 금지(D14, FORBIDDEN_ACTIONS, AC3, STOP_CONDITIONS)에 묶여 있어 AC19와 동시에 충족할 수 없다. 함수 반환 타입이 `list[Path]`이고 `Path`가 이미 import되어 있으므로, 그 한 줄을 `removed: list[Path] = []`로 바꾸는 타입 주석만 예외로 허용한다. 동작은 바뀌지 않는다. Work Order 파일은 수정하지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- PROTECTED_FILES 첫 항목: docs/tasks/AUTO-02/** (C1의 WORK_ORDER.md와 Ce의 ERRATA-001.md 최초 생성만 예외; 이후 불변)
- PROTECTED_FILES INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅. C1의 docs/tasks/AUTO-02/WORK_ORDER.md와 Ce의 docs/tasks/AUTO-02/ERRATA-001.md 최초 생성은 docs/tasks/README.md 규칙에 따른 별도 예외이며 ALLOWED_FILES 11개에 속하지 않는다.
- DESIGN_CONTRACT.D14: D14 atomic: `atomic_create_new_bytes(path, data) -> Path`와 예외 `CreateNewError(cause, final_created, tmp_leftover)`를 추가한다. 부모 디렉터리를 만들지 않는다. 순서는 같은 디렉터리에 `mkstemp` tmp 작성 → flush·fsync → `os.link(tmp, path)`(대상이 있으면 `FileExistsError`) → tmp unlink. link 전 실패(부모 없음 `FileNotFoundError`, tmp 작성·fsync 오류, link 미지원·권한 오류, `FileExistsError`)는 이 호출이 만든 tmp 하나만 삭제를 시도하고 `CreateNewError(cause=<원래 예외>, final_created=False, tmp_leftover=<삭제 실패 시 경로, 성공 시 None>)`를 올린다. link 성공 후 unlink 실패는 `CreateNewError(cause=<unlink 오류>, final_created=True, tmp_leftover=<경로>)`를 올린다. 최종 파일·기존 파일·다른 실행의 tmp는 삭제하지 않는다. 기존 함수·상수의 동작·시그니처는 바꾸지 않는다. 기존 줄 변경의 유일한 예외는 `cleanup_tmp`의 `    removed = []` 한 줄을 `    removed: list[Path] = []`로 바꾸는 타입 주석이며 동작은 같다. 이 밖의 atomic.py 기존 줄은 삭제·수정하지 않는다.
- FORBIDDEN_ACTIONS:
  - 승인된 gate 밖의 행위, ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
  - Work Order·ERRATA 수정
  - `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
  - hooks·settings·.claude 변경 또는 guard 우회, guard deny된 명령의 변형 재시도
  - 다른 branch·worktree·untracked·ignored·reference 산출물 정리
  - 실제 저장소(TARGET_WORKTREE 포함)에서 snapshot 실행, `data/processed/workstate/` 또는 그 안의 파일 생성(테스트는 tmp 저장소만 사용)
  - `storage/atomic.py` 기존 함수·상수의 동작·시그니처 변경, D14가 허용한 타입 주석 1줄 외의 기존 줄 삭제·수정
  - 기존 테스트의 삭제·수정·skip·xfail 추가·단정 완화
  - symlink·junction 테스트를 위한 권한 상승·OS 설정 변경
- ACCEPTANCE_CRITERIA.평가 시점: 구현 커밋 전 AC1–AC3은 Ce와 현재 작업 파일·index의 후보 변경으로, 구현 커밋 후에는 commit 간 비교로 확정한다. 존재하지 않는 커밋·PR·CI의 검사를 PASS로 보고하지 않는다.
- ACCEPTANCE_CRITERIA.AC1: C1 parent = CANONICAL_BASE_SHA, C1 변경 = docs/tasks/AUTO-02/WORK_ORDER.md(A) 하나. Ce parent = C1, Ce 변경 = docs/tasks/AUTO-02/ERRATA-001.md(A) 하나. 구현 커밋 parent = Ce. `git diff --name-status <Ce> <구현 커밋>` = ALLOWED_FILES 11개와 A/M 표기 일치. base→구현 커밋 전체 변경 = docs/tasks/AUTO-02/WORK_ORDER.md ∪ docs/tasks/AUTO-02/ERRATA-001.md ∪ ALLOWED_FILES
- ACCEPTANCE_CRITERIA.AC2: Ce→구현 커밋 PROTECTED_FILES diff 비어 있음. Work Order blob 내용 SHA-256은 승인값(10b484c1625f5660a7f04a6ae4d3de3269e500b11e5ef3e2fc0e36eceaa886e5)과 같고, ERRATA-001 blob 내용 SHA-256은 수락값과 같으며, 둘 다 이후 불변이고 작업 파일 해시도 같다.
- ACCEPTANCE_CRITERIA.AC3: `git diff --numstat <CANONICAL_BASE_SHA> <구현 커밋>`에서 docs/tasks/README.md의 삭제 수 0. src/moneylab/storage/atomic.py의 삭제 수는 정확히 1이고, 그 삭제 줄은 `    removed = []`, 대응 추가 줄은 `    removed: list[Path] = []`이며, 그 밖의 삭제·수정 줄은 없다.
- STOP_CONDITIONS:
  - base·HEAD·tree·BASE_BLOBS 불일치, Work Order 또는 ERRATA-001 sha256(blob·작업 파일) 불일치, D16 앵커 불일치
  - ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅, A/M 표기 불일치
  - atomic.py·README.md 기존 줄의 삭제·수정(numstat 삭제 수가 README.md에서 0 초과, atomic.py에서 1 초과, 또는 atomic.py의 삭제 줄이 D14의 예외 줄이 아님), 기존 테스트 변경·약화
  - 실제 저장소에서 snapshot 실행 또는 `data/processed/workstate/` 생성
  - guard deny, 예상하지 못한 ASK, 편집·commit·push 승인 창 거절·무응답
  - 테스트·ruff·mypy 실패·에러(BUNDLE 안에서는 README §14 BGA-4·BGA-10), AC 불충족
  - NOT_RUN_PLATFORM으로 PARTIAL AC 발생(BUNDLE 안에서는 그 gate 보고에서 STOP, 개별 진행에서도 gate PASS는 YES가 아님)
  - 대상 파일 시스템에서 os.link를 쓸 수 없음(대체 구현 없이 STOP, PROPOSED_ERRATA로 보고)
  - 계약 모순, 상위 규칙과 충돌, 예상하지 못한 untracked 파일

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
- Work Order 파일은 수정하지 않는다. 위에 적지 않은 Work Order 필드는 그대로다.
- Ce는 HEAD = C1(d198cbbaa3719ffcdece4ed1abc2f410279aeb77)에서 이 파일 하나만 `git add -- docs/tasks/AUTO-02/ERRATA-001.md`로 stage해 `docs(task): add AUTO-02 ERRATA-001` 커밋 1회로 만든다. 기존 미커밋 구현 변경 11개는 stage하지 않고 Ce에 포함하지 않는다.
- Ce 전후로 기존 구현 변경 11개의 작업 파일 SHA-256(W)과 stage될 내용 SHA-256(S)이 같아야 하고, Ce 직전 index에는 이 파일 외 항목이 없어야 한다. 다르면 STOP한다.
