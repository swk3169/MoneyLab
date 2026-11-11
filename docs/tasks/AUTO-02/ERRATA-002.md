# ERRATA: AUTO-02 ERRATA-002

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: AUTO-02-ERRATA-002
TASK_ID: AUTO-02
TARGET_WORK_ORDER: docs/tasks/AUTO-02/WORK_ORDER.md @ d198cbbaa3719ffcdece4ed1abc2f410279aeb77 (sha256 10b484c1625f5660a7f04a6ae4d3de3269e500b11e5ef3e2fc0e36eceaa886e5)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자, 2026-11-11

## CHANGED_FIELDS

CHANGED_FIELDS:
- ALLOWED_FILES
- PROTECTED_FILES (전체, INVARIANT 포함)
- ALLOWED_ACTIONS.COMMIT
- DESIGN_CONTRACT.D18 (신설)
- FORBIDDEN_ACTIONS
- ACCEPTANCE_CRITERIA.평가 시점, ACCEPTANCE_CRITERIA.AC1, ACCEPTANCE_CRITERIA.AC2, ACCEPTANCE_CRITERIA.AC3, ACCEPTANCE_CRITERIA.AC4
- E2E_GATES
- STOP_CONDITIONS

## RATIONALE

RATIONALE: tests/test_upbit_replay.py::test_cli_rejects_bad_upbit_options는 AUTO-02 변경이 없는 worktree(HEAD 841b00264cea1423a41def86634d6af1e58908a3, 테스트·cli.py·display/console.py가 CANONICAL_BASE와 동일)에서도 같은 출력("…must never pose as\nreal data")으로 실패했다. 기대 문구는 출력에 있지만 단어 사이에 줄바꿈이 들어가 원문 그대로의 부분 문자열 검사에 실패한다. 원인(콘솔 폭, 경로 길이 등)은 확정하지 않았다. AC16(전체 pytest failed 0 / errors 0)을 유지한 채 진행하기 위해, 그 단정 한 줄만 공백·줄바꿈을 정규화한 출력과 비교하도록 바꾸는 것을 허용한다. ERRATA-001은 바뀌지 않고 유효하다. 같은 필드를 이 ERRATA가 다시 정하는 경우, 이 ERRATA의 값이 ERRATA-001의 내용을 포함해 대체한다(번호 규칙). symlink 2건의 PARTIAL(D17, AC7, AC9)은 이 ERRATA로 바뀌지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- ALLOWED_FILES:
  - A src/moneylab/workstate/__init__.py
  - A src/moneylab/workstate/collect.py
  - A src/moneylab/workstate/store.py
  - A src/moneylab/workstate/__main__.py
  - M src/moneylab/storage/atomic.py
  - A tests/test_workstate_collect.py
  - A tests/test_workstate_store.py
  - A tests/test_workstate_cli.py
  - A tests/test_workstate_isolation.py
  - A tests/test_atomic_create_new.py
  - M tests/test_upbit_replay.py
  - M docs/tasks/README.md
- PROTECTED_FILES:
  - docs/tasks/AUTO-02/** (C1의 WORK_ORDER.md, Ce1의 ERRATA-001.md, Ce2의 ERRATA-002.md 최초 생성만 예외; 이후 불변)
  - docs/** 중 docs/tasks/README.md를 제외한 전부
  - src/** 중 src/moneylab/workstate/**와 src/moneylab/storage/atomic.py를 제외한 전부(src/moneylab/automation/** 포함)
  - tests/** 중 ALLOWED_FILES의 테스트 파일 6개를 제외한 전부(tests/test_automation_*.py, tests/test_atomic_storage.py 포함)
  - .claude/**, .github/**, .gitignore, .gitattributes
  - pyproject.toml, requirements.txt, requirements-dev.txt
  - configs/**, knowledge/**, data/**, examples/**
  - README.md, ARCHITECTURE.md, LICENSE, .env.example, CLAUDE.md
  - INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅. C1의 docs/tasks/AUTO-02/WORK_ORDER.md, Ce1의 docs/tasks/AUTO-02/ERRATA-001.md, Ce2의 docs/tasks/AUTO-02/ERRATA-002.md 최초 생성은 docs/tasks/README.md 규칙에 따른 별도 예외이며 ALLOWED_FILES 12개에 속하지 않는다.
- ALLOWED_ACTIONS.COMMIT: `git add -- src/moneylab/workstate/__init__.py src/moneylab/workstate/collect.py src/moneylab/workstate/store.py src/moneylab/workstate/__main__.py src/moneylab/storage/atomic.py tests/test_workstate_collect.py tests/test_workstate_store.py tests/test_workstate_cli.py tests/test_workstate_isolation.py tests/test_atomic_create_new.py tests/test_upbit_replay.py docs/tasks/README.md`, 커밋 하나 `feat(workstate): add state snapshot and verify`
- DESIGN_CONTRACT.D18: D18 기존 CLI 테스트 단정 정규화: tests/test_upbit_replay.py의 test_cli_rejects_bad_upbit_options 마지막 단정 한 줄 `    assert "never pose as real" in capsys.readouterr().out`을 `    assert "never pose as real" in " ".join(capsys.readouterr().out.split())`로 바꾼다. 이 파일의 다른 줄, 테스트 이름·ID, 기대 문구, 앞선 `main(...) == 1` 거부 단정, fixture, CLI·Rich 설정·환경은 바꾸지 않는다. 파일은 UTF-8, LF, 끝 줄바꿈 1개로 둔다.
- FORBIDDEN_ACTIONS:
  - 승인된 gate 밖의 행위, ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
  - Work Order·ERRATA 수정
  - `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
  - hooks·settings·.claude 변경 또는 guard 우회, guard deny된 명령의 변형 재시도
  - 다른 branch·worktree·untracked·ignored·reference 산출물 정리
  - 실제 저장소(TARGET_WORKTREE 포함)에서 snapshot 실행, `data/processed/workstate/` 또는 그 안의 파일 생성(테스트는 tmp 저장소만 사용)
  - `storage/atomic.py` 기존 함수·상수의 동작·시그니처 변경, D14가 허용한 타입 주석 1줄 외의 기존 줄 삭제·수정
  - 기존 테스트의 삭제·수정·skip·xfail 추가·단정 완화. 유일한 예외는 D18이 정한 tests/test_upbit_replay.py 단정 1줄 변경이다.
  - symlink·junction 테스트를 위한 권한 상승·OS 설정 변경
- ACCEPTANCE_CRITERIA.평가 시점: 구현 커밋 전 AC1–AC3은 Ce2와 현재 작업 파일·index의 후보 변경으로, 구현 커밋 후에는 commit 간 비교로 확정한다. 존재하지 않는 커밋·PR·CI의 검사를 PASS로 보고하지 않는다.
- ACCEPTANCE_CRITERIA.AC1: C1 parent = CANONICAL_BASE_SHA, C1 변경 = docs/tasks/AUTO-02/WORK_ORDER.md(A) 하나. Ce1(35411875e24851e60bbc6d8975a0d827d43df35b) parent = C1, Ce1 변경 = docs/tasks/AUTO-02/ERRATA-001.md(A) 하나. Ce2 parent = Ce1, Ce2 변경 = docs/tasks/AUTO-02/ERRATA-002.md(A) 하나. 구현 커밋 parent = Ce2. `git diff --name-status <Ce2> <구현 커밋>` = ALLOWED_FILES 12개와 A/M 표기 일치. base→구현 커밋 전체 변경 = docs/tasks/AUTO-02/WORK_ORDER.md ∪ docs/tasks/AUTO-02/ERRATA-001.md ∪ docs/tasks/AUTO-02/ERRATA-002.md ∪ ALLOWED_FILES
- ACCEPTANCE_CRITERIA.AC2: Ce2→구현 커밋 PROTECTED_FILES diff 비어 있음. Work Order blob 내용 SHA-256은 승인값(10b484c1625f5660a7f04a6ae4d3de3269e500b11e5ef3e2fc0e36eceaa886e5), ERRATA-001은 수락값(e1f788dba33f807a8284ee6c58735d275cd85bb58879dd7fa9bc4fbc115130c8), ERRATA-002는 수락값과 같으며, 셋 다 이후 불변이고 작업 파일 해시도 같다.
- ACCEPTANCE_CRITERIA.AC3: `git diff --numstat <CANONICAL_BASE_SHA> <구현 커밋>`에서 docs/tasks/README.md의 삭제 수 0. src/moneylab/storage/atomic.py의 삭제 수는 정확히 1이고, 그 삭제 줄은 `    removed = []`, 대응 추가 줄은 `    removed: list[Path] = []`이다. tests/test_upbit_replay.py는 추가 1·삭제 1이고, 삭제 줄과 추가 줄은 D18의 변경 전·후 줄과 정확히 같다. 그 밖의 삭제·수정 줄은 없다.
- ACCEPTANCE_CRITERIA.AC4: 기준선의 `pytest --collect-only -q` 테스트 ID가 모두 구현 커밋에서도 수집됨(감소 0). D18의 tests/test_upbit_replay.py 1줄 변경을 제외한 기존 테스트 파일 diff 0
- E2E_GATES:
  - clean 구현 커밋에서 전체 pytest 1회와 AC1–AC19 확인. AC16의 IMPLEMENTATION 실행과 이 실행을 구분한다.
  - 실제 저장소에서 `./.venv/Scripts/python.exe -B -m moneylab.workstate verify --task-id AUTO-02 --snapshot-id 0000000000000000000000000000000000000000000000000000000000000000` 1회: 종료 2, status SNAPSHOT_NOT_FOUND, file_sha256 null, final_file_created null, 실행 전후 `git status --porcelain=v2 --ignored` 동일, `data/processed/workstate/` 미생성
  - 실제 저장소에서 snapshot 실행 금지
  - `git diff --name-only <CANONICAL_BASE_SHA> <구현 커밋> -- src tests`가 ALLOWED_FILES의 src·tests 경로 11개와 같음
- STOP_CONDITIONS:
  - base·HEAD·tree·BASE_BLOBS 불일치, Work Order·ERRATA-001·ERRATA-002 sha256(blob·작업 파일) 불일치, D16 앵커 불일치
  - ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅, A/M 표기 불일치
  - 기존 줄의 허용되지 않은 삭제·수정: numstat 삭제 수가 README.md에서 0 초과, atomic.py에서 1 초과 또는 삭제 줄이 D14 예외 줄이 아님, tests/test_upbit_replay.py에서 1 초과 또는 변경 줄이 D18의 줄이 아님. 그 밖의 기존 테스트 변경·약화
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
- Work Order와 ERRATA-001 파일은 수정하지 않는다. 여기 적지 않은 필드는 Work Order와 ERRATA-001의 값이 그대로 유효하다.
- AC16(IMPLEMENTATION과 CLEAN_COMMIT_E2E 각각 전체 pytest failed 0 / errors 0)은 바뀌지 않는다. D17·AC7·AC9의 NOT_RUN_PLATFORM PARTIAL도 바뀌지 않는다.
- D18 변경은 README §14 BGA-8 (B)의 단정 의미 완화 검토 대상이며 "독립 검토 필요"로 보고하고 PASS로 단정하지 않는다.
- Ce2는 HEAD = Ce1(35411875e24851e60bbc6d8975a0d827d43df35b)에서 이 파일 하나만 `git add -- docs/tasks/AUTO-02/ERRATA-002.md`로 stage해 `docs(task): add AUTO-02 ERRATA-002` 커밋 1회로 만든다. 기존 미커밋 구현 변경 11개는 stage하지 않고 Ce2에 포함하지 않는다.
- Ce2 전후로 기존 구현 변경 11개의 작업 파일 SHA-256(W)과 stage될 내용 SHA-256(S)이 같아야 하고, Ce2 직전 index에는 이 파일 외 항목이 없어야 한다. 다르면 STOP한다.
