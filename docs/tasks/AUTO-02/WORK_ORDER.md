# Work Order: AUTO-02 — 작업 상태 스냅샷과 재개 전 대조

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/AUTO-02/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.3
WORK_ORDER_ID: AUTO-02
TASK_ID: AUTO-02
TITLE: 작업 상태 스냅샷 저장과 재개 전 대조 (비권위)
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 6f7ee117ce13c8e497407275b53bee6f66cc83ef
CANONICAL_BASE_TREE: 885d99e742760251b4d792b3936dec808a28f220
BASE_BLOBS: src/moneylab/storage/atomic.py 0cbbe855bcb672d7c82e16aa21c9e6adb60e7b4a (108 lines, 3428 bytes), docs/tasks/README.md 1eb52e5f0979ceee756fbfaac8c123db9f94775f (207 lines, 23093 bytes) (C1 직전 재검증, 다르면 STOP)
TARGET_BRANCH: feature/auto-02-workstate
TARGET_WORKTREE: C:/MoneyLab-auto-02
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests / pytest (Windows)
BUNDLE_ELIGIBLE: YES
BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: AUTO-02 <GATE> WO@<commit>`)
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping except WORKSPACE_SETUP: NOT_REQUIRED tasks
- v1.3이고 BUNDLE_ELIGIBLE: YES이면 docs/tasks/README.md §14의 BUNDLE_AUTHORIZATION으로 BUNDLE_MAX_RANGE 안의 연속 구간을 진행할 수 있다. PUSH·PR_CI·MERGE·후퇴는 개별 승인이다.
- BUNDLE_AUTHORIZATION은 C1 커밋과 환경 준비 승인·완료 이후에만 받을 수 있다. POST_MERGE_AUDIT와 COMPLETE는 BUNDLE_MAX_RANGE 밖이며 개별 Gate Authorization으로 진행한다.
- EXPECTED_ASK는 이 Work Order에서 확정하지 않고 각 BUNDLE_AUTHORIZATION에서 확정한다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다.

## GOAL

GOAL: PC·세션 재시작 때 저장소를 다시 조사하는 비용과 수동 인계 부담을 줄이기 위해, 한 worktree의 Git·계약 상태를 비권위 스냅샷으로 저장하고 지정한 스냅샷과 현재 상태를 대조하는 오프라인 CLI `python -m moneylab.workstate`를 추가한다. 상태 일치는 실행 권한, gate PASS, 종료된 BUNDLE_AUTHORIZATION의 복원을 만들지 않는다.

## BACKGROUND

BACKGROUND: AUTO-01(PR #45, merge 04733d12)은 읽기 전용 action 1개 실행과 evidence 반환만 제공하며 저장·상태 수집·재개가 없다. GOV-AUTOMATION-02(PR #46, merge 6f7ee117)가 README §14 BGA를 도입했고 Evidence 저장·자동 재개를 AUTO-02 이후로 미뤘다. README §11은 gate 보고를 채팅에만 두고 파일 보관에 ERRATA를 요구하므로 스냅샷의 지위를 §11에 명시한다. pyproject.toml `[tool.mypy]`의 `files`에는 새 패키지 경로가 없고 `follow_imports = "silent"`이므로, CI의 `python -m mypy`가 workstate의 오류를 보고하는지는 확정되지 않았다. pyproject는 바꾸지 않는다.

## NON_GOALS

NON_GOALS:
- AUTO-01(`src/moneylab/automation/**`, `tests/test_automation_*.py`) 변경
- 전진 조건 평가기, gate PASS 판정, 새 executor action, 연속·무인 실행, scheduler, queue
- 승인·BUNDLE_AUTHORIZATION 생성·복원, 자동 재개
- "가장 최근" 스냅샷 자동 선택, 목록·삭제·정리·보존 기간 기능
- worktree 밖·다른 PC 간 스냅샷 공유, 원격 저장
- EGM 도입, LLM 비용 측정, 거래·네트워크 기능
- 별도 GOV 변경, `.gitignore`·`.claude/**`·`.github/**`·`pyproject.toml`·`docs/agent_workflow.md`·CLAUDE.md 변경

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: 두 하위 단계로 수행한다. (1) WORKTREE_CREATION_ONLY: 승인된 main ref fetch 1회, 원격 main = CANONICAL_BASE_SHA와 BASE_BLOBS 확인, TARGET_BRANCH·TARGET_WORKTREE 생성. 불일치면 STOP한다. (2) C1_CREATION_ONLY: 승인된 문안 바이트(UTF-8, BOM 없음, LF, 끝 줄바꿈 1개)의 SHA-256을 대조하고 Write 도구로 docs/tasks/AUTO-02/WORK_ORDER.md를 최초 1회 작성, 해당 경로만 stage, C1 커밋 `docs(task): add AUTO-02 work order` 1회, 보고 후 STOP. 환경 준비(.venv 생성·설치)는 별도 승인이다.
- IMPLEMENTATION: ALLOWED_FILES 생성·수정, TEST_GATES 실행. 각 편집의 승인 창(guard ASK·settings ask)은 사용자가 승인한 경우에만 진행한다.
- PRECOMMIT_AUDIT: 읽기와 감사만. README §14 BGA-8 (A) 수동 확인 포함
- COMMIT: `git add -- src/moneylab/workstate/__init__.py src/moneylab/workstate/collect.py src/moneylab/workstate/store.py src/moneylab/workstate/__main__.py src/moneylab/storage/atomic.py tests/test_workstate_collect.py tests/test_workstate_store.py tests/test_workstate_cli.py tests/test_workstate_isolation.py tests/test_atomic_create_new.py docs/tasks/README.md`, 커밋 하나 `feat(workstate): add state snapshot and verify`
- CLEAN_COMMIT_E2E: 전체 pytest 1회, E2E_GATES, ACCEPTANCE_CRITERIA 확인(ignored 출력만, 실제 저장소에서 snapshot 실행 금지)
- PUSH: TARGET_BRANCH 하나만 `git push -u origin feature/auto-02-workstate`
- PR_CI: docs/tasks/README.md §13. Gate Authorization이 PR_CREATE: YES와 저장소·base·head branch·head SHA·PR 제목·본문을 명시하면 `gh pr create` 1회. 아니면 compare URL·PR 본문 제공만. CI 재실행은 별도 승인
- MERGE: docs/tasks/README.md §13. Gate Authorization이 MERGE_EXECUTE: YES와 PR 번호·head SHA를 명시하고 사전 검증을 모두 통과하면 `gh pr merge <N> -R swk3169/MoneyLab --merge --match-head-commit <SHA>` 1회
- POST_MERGE_AUDIT: main ref만 fetch, 구조 감사(개별 승인)
- COMPLETE: 최종 보고(개별 승인)

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위, ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
- hooks·settings·.claude 변경 또는 guard 우회, guard deny된 명령의 변형 재시도
- 다른 branch·worktree·untracked·ignored·reference 산출물 정리
- 실제 저장소(TARGET_WORKTREE 포함)에서 snapshot 실행, `data/processed/workstate/` 또는 그 안의 파일 생성(테스트는 tmp 저장소만 사용)
- `storage/atomic.py` 기존 함수·상수의 동작·시그니처 변경
- 기존 테스트의 삭제·수정·skip·xfail 추가·단정 완화
- symlink·junction 테스트를 위한 권한 상승·OS 설정 변경

## ALLOWED_FILES

ALLOWED_FILES:
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
- M docs/tasks/README.md

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/AUTO-02/** (C1에서 WORK_ORDER.md 최초 생성만 예외; 이후 불변)
- docs/** 중 docs/tasks/README.md를 제외한 전부
- src/** 중 src/moneylab/workstate/**와 src/moneylab/storage/atomic.py를 제외한 전부(src/moneylab/automation/** 포함)
- tests/** 중 ALLOWED_FILES의 테스트 파일 5개를 제외한 전부(tests/test_automation_*.py, tests/test_atomic_storage.py 포함)
- .claude/**, .github/**, .gitignore, .gitattributes
- pyproject.toml, requirements.txt, requirements-dev.txt
- configs/**, knowledge/**, data/**, examples/**
- README.md, ARCHITECTURE.md, LICENSE, .env.example, CLAUDE.md

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅. C1의 docs/tasks/AUTO-02/WORK_ORDER.md 최초 생성은 docs/tasks/README.md 규칙에 따른 별도 예외이며 ALLOWED_FILES 11개에 속하지 않는다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 위치·CLI: 새 패키지 `src/moneylab/workstate/`. 명령은 `python -m moneylab.workstate snapshot --task-id <TASK_ID> [--reported-gate <GATE> --reported-result <PASS|NO>]`와 `python -m moneylab.workstate verify --task-id <TASK_ID> --snapshot-id <ID>` 두 개뿐이다. `--reported-gate`와 `--reported-result`는 둘 다 주거나 둘 다 생략한다. `--root`, 파일 경로 인자, latest 선택, 목록 명령은 없다. 출력은 D13의 결과 객체 하나를 canonical JSON(정렬 키, 구분자 `,` `:`, ensure_ascii=False, UTF-8) + LF로 stdout에 쓰고 stderr에는 쓰지 않는다. 예외는 `--help`(argparse 평문, 종료 0)뿐이다.
- D2 root: root는 패키지 위치(`<root>/src/moneylab/workstate`)로 정하고 `git rev-parse --show-toplevel`의 정규화 경로와 같아야 한다. 다르거나 확인할 수 없으면 `ENVIRONMENT_INVALID`. 테스트만 내부 함수 인자로 tmp 저장소 root를 넘긴다.
- D3 형식: TASK_ID `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`이고 64자 이하. GATE는 GATE_SEQUENCE의 이름 중 하나. RESULT는 `PASS` 또는 `NO`. snapshot ID `^[0-9a-f]{64}$`. 인자 누락·형식 위반·알 수 없는 인자·`--reported-*` 한쪽만 지정은 `ARGUMENT_INVALID`.
- D4 git 호출: git만 shell 없이 고정 argv로 호출하고 하위 명령은 `rev-parse`, `status`, `ls-files`, `ls-tree`, `cat-file`, `check-ignore`로 한정한다. 모든 호출에 `-c core.fsmonitor=false -c core.untrackedCache=false`를 붙이고 환경에 `GIT_OPTIONAL_LOCKS=0`을 둔다. 호출마다 timeout 30초, stdout 16 MiB, stderr 64 KiB 상한이며, 상한은 읽기 완료 후가 아니라 자식 프로세스의 stdout·stderr를 청크 단위로 읽는 도중 누적 바이트로 적용한다. `git cat-file blob <oid>`로 S를 계산할 때도 같은 stdout 상한을 적용하고 내용은 메모리에 누적하지 않고 해시에 바로 넣는다. stderr 내용은 저장·출력하지 않는다. 상한 초과나 timeout이면 즉시 자식 프로세스를 kill하고 wait·파이프 close·reader 종료를 최대 10초 기다려 회수한다. 상한 초과는 `LIMIT_EXCEEDED`, timeout과 0이 아닌 종료(`check-ignore`의 정의된 1 제외)는 `GIT_FAILED`, 10초 안에 회수하지 못하면 detail "child not reaped"의 `GIT_FAILED`이다. 명령 출력 원문은 저장하거나 출력하지 않는다. automation 패키지는 import하지 않는다.
- D5 state: `git status --porcelain=v2 -z --untracked-files=all --no-renames --ignored=no`와 rev-parse·ls-tree·ls-files·cat-file로 다음을 만든다. `branch`(이름 또는 null=detached), `head`, `tree`, `entries`(변경 경로별 path·xy·head_mode·head_blob·index_mode·index_blob·w_sha256(작업 파일 바이트, 없으면 ABSENT)·s_sha256(index blob 내용, 없으면 ABSENT), path 정렬), `untracked`(경로 목록, 정렬, 내용 미수집), `contract`(`docs/tasks/<TASK_ID>/` 아래에서 HEAD tree에 있거나 `git ls-files -co --exclude-standard`로 나오는 파일마다 path·head_sha256·work_sha256, 없으면 ABSENT, 경로 정렬). ignored 파일은 계약 폴더 안이라도 수집하지 않는다. ERRATA의 ACCEPTED 여부는 해석하지 않는다.
- D6 경로 안전: 수집 대상은 entries의 작업 파일, untracked 경로, contract 작업 파일과 각각의 root부터의 모든 상위 디렉터리다. 이 중 symlink(`os.path.islink`), junction(`Path.is_junction`), Windows reparse point(`st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT`)가 있거나, W를 계산할 대상이 정규 파일(`S_ISREG`)이 아니면 `UNSUPPORTED_STATE`이다. 저장 경로는 root부터 `<TASK_ID>` 디렉터리까지의 구성 요소와 기록 파일 자신(lstat)이 symlink·junction·reparse point이거나 resolve 결과가 root 밖이면 `STORE_PATH_INVALID`이다. 링크가 아닌 비정규 기록 파일(디렉터리·장치 등)은 D11 5단계의 `SNAPSHOT_CORRUPT`이다.
- D7 거부 상태: unborn HEAD, unmerged 항목, `git rev-parse --git-path`로 확인한 진행 중인 merge·rebase·cherry-pick·revert·bisect, `ls-files -v`의 skip-worktree·assume-unchanged 항목, submodule·gitlink 변경은 `UNSUPPORTED_STATE`이며 저장하지 않고 MATCH를 내지 않는다. 일반 수정·stage·삭제·rename(삭제+추가)·detached HEAD는 지원한다.
- D8 상한·안정성: 변경 경로 2,000개, untracked 경로 2,000개, contract 파일 100개, 경로 길이 1,024 UTF-8 바이트, W·S 해시 대상 1개당 16 MiB(W는 파일을 읽는 도중 누적 바이트로, S는 D4의 stdout 상한으로 적용), 해시 대상 합계 512 MiB. 초과는 `LIMIT_EXCEEDED`. 수집은 두 번 하고 W 대상의 해시 전후 stat(size, mtime_ns)을 비교하며 하나라도 다르면 `UNSTABLE_STATE`. 이것은 일관성 점검이며 원자적 스냅샷을 보장하지 않는다. D4·D6·D7·D8의 오류가 하나라도 있으면 일부 결과로 저장하거나 MATCH를 내지 않는다.
- D9 스키마 `moneylab.workstate.snapshot/1`: 파일 키는 `schema`, `task_id`, `snapshot_id`, `state_sha256`, `state`, `reported`, `meta`뿐이다. `reported`는 `{gate, result}` 또는 null이며 외부 제공 값(UNVERIFIED)이다. `meta`는 `created_at_utc`(RFC 3339 UTC, 초 단위), `tool_version`이며 worktree 경로·호스트·사용자·환경변수는 넣지 않는다. `state_sha256 = sha256(canonical(state))`, `snapshot_id = sha256(canonical({schema, task_id, state, reported}))`. 파일 바이트 = canonical(전체 객체) + LF이며 1 MiB를 넘으면 저장하지 않고 `LIMIT_EXCEEDED`.
- D10 저장(snapshot만): 경로 `<root>/data/processed/workstate/<TASK_ID>/<snapshot_id>.json`. 순서: (1) 최종 파일 경로에 `git check-ignore -q`로 ignored 확인(아니면 `STORE_PATH_INVALID`). (2) 이미 존재하는 저장 경로 구성 요소를 D6으로 검사. (3) `data`, `processed`, `workstate`, `<TASK_ID>` 중 없는 디렉터리를 위에서 아래로 하나씩 `os.mkdir`로 생성(`parents=True` 금지). 생성 직후 그 디렉터리를 D6으로 재검사한다. `FileExistsError`면 그 경로를 lstat으로 재검사해 링크·junction·reparse가 아닌 일반 디렉터리일 때만 계속하고, 아니면 `STORE_PATH_INVALID`. (4) `storage.atomic.atomic_create_new_bytes`로만 쓴다. 결과: (a) 새로 생성: `STORED`. (b) `CreateNewError.cause`가 `FileExistsError`: 기존 파일을 D11의 3·5·6·7·8단계로 검증한다(2단계 root 확인은 이 snapshot 실행에서 이미 통과한 같은 root를 쓰고, 4단계 존재는 확정된 것으로 본다). 오류 코드는 verify와 같다. 검증을 통과하고 schema·task_id·state·reported가 새 객체와 같으면 기존 파일과 meta를 보존하고 `ALREADY_STORED`, 객체가 다르면 `SNAPSHOT_CORRUPT`이며 기존 파일은 바꾸지 않는다. 동시 실행에서 link에 진 쪽도 같은 규칙을 따른다. (c) `final_created=True`(link 후 tmp 정리 실패): `STORED`와 warning `TMP_LEFTOVER:<파일 이름>`. (d) 그 밖의 `CreateNewError`: `STORE_FAILED`이며 `tmp_leftover`가 있으면 warning `TMP_LEFTOVER:<파일 이름>`. (b)에서 `tmp_leftover`가 있으면 결과에 같은 warning을 붙인다. 오류로 끝날 때 이 실행이 만든 디렉터리는 지우지 않고 warning `DIR_LEFT:<root 기준 상대 경로>`로 보고한다. 성공 시 만든 디렉터리는 warning이 아니다. 덮어쓰기·`os.replace` 대체·삭제·정리 경로는 없다. verify는 디렉터리·파일을 만들지 않는다.
- D11 verify 판정 순서: 1 인자(`ARGUMENT_INVALID`) → 2 root(`ENVIRONMENT_INVALID`) → 3 경로 안전: 구성 요소와 기록 파일(lstat)이 symlink·junction·reparse point이거나 root 밖이면 `STORE_PATH_INVALID` → 4 존재(`SNAPSHOT_NOT_FOUND`) → 5 링크가 아닌 비정규 파일이거나 1 MiB 초과면 `SNAPSHOT_CORRUPT`, 읽기 오류면 `SNAPSHOT_UNREADABLE` → 6 UTF-8 strict JSON 객체, 중복 키·NaN·Infinity 거부(`SNAPSHOT_CORRUPT`) → 7 `schema`가 문자열이고 알려진 값이 아니면 `SNAPSHOT_INCOMPATIBLE`, 없거나 문자열이 아니면 `SNAPSHOT_CORRUPT` → 8 키 allowlist·타입·형식, canonical 재직렬화 바이트 = 파일 바이트, 재계산 snapshot_id = 파일 이름 = 필드, 재계산 state_sha256 = 필드, task_id = 인자(`SNAPSHOT_CORRUPT`) → 9 현재 상태 수집(D4–D8 오류 코드) → 10 `state` 전체 비교: 같으면 `MATCH`, 다르면 `MISMATCH`. `meta`와 `reported`는 비교하지 않는다. 어떤 오류도 다른 기록으로 대체하지 않으며 파일을 지우지 않는다.
- D12 무결성 범위: D11 8단계의 canonical 검사는 파일이 스키마에 맞는 객체의 결정적 직렬화와 바이트 단위로 같음을 확인하여 잘림·부분 수정·형식 파손 같은 우발적 손상을 탐지한다. snapshot_id·state_sha256 검사는 schema·task_id·state·reported가 파일 이름·저장된 해시와 일관됨을 확인한다. `meta`의 형식이 유효한 값 변경(예: 다른 유효 시각)과 모든 필드·해시·파일 이름을 일관되게 다시 쓴 변경은 외부에 보관한 기대 file_sha256 없이는 탐지할 수 없다. 로컬 해시는 진위성·작성자·권한을 보장하지 않는다.
- D13 결과 스키마 `moneylab.workstate.result/1`: 모든 출력은 다음 키를 정확히 가진다. `schema`, `command`(snapshot|verify|null), `status`, `exit_code`, `task_id`(유효하면 값, 아니면 null), `snapshot_id`(snapshot은 계산값, verify는 유효한 인자, 그 외 null), `file_sha256`, `final_file_created`(snapshot이 D10 (4)에 도달하면 true/false, 그 외 null), `state_sha256_stored`(verify 8단계 또는 D10 (b) 검증 통과 시, 아니면 null), `state_sha256_current`(수집 성공 시, 아니면 null), `reported`(값 또는 null), `reported_status`(reported가 있으면 "REPORTED_UNVERIFIED", 아니면 null), `differences`(MISMATCH 시 `{field, stored, current}` 목록, 값은 해시·경로·상태 코드만, 그 외 빈 목록), `warnings`(목록, verify는 항상 빈 목록), `error`(오류 시 `{code, detail}`, detail은 고정 문구와 root 기준 상대 경로만, 아니면 null), `authority`("NONE" 고정), `compared`(고정 목록: branch, head, tree, entries, untracked paths, contract), `not_compared`(고정 목록: untracked file bytes, ignored files, git config, hooks, history between snapshots). `file_sha256`: `STORED`는 실제로 생성한 파일의 전체 바이트 해시이며 링크된 tmp에 쓴 메모리의 작성 바이트로 계산할 수 있다. `ALREADY_STORED`와 verify 결과는 읽고 검증한 기존 파일 바이트의 해시다. 그 밖에는 정규 파일을 1 MiB 이하로 전부 읽은 경우에만 그 바이트의 해시이고 아니면 null이다. status·exit_code: snapshot `STORED`·`ALREADY_STORED`는 warnings가 비어 있으면 0, 아니면 1. verify `MATCH` 0, `MISMATCH` 1. 오류(`ARGUMENT_INVALID`, `ENVIRONMENT_INVALID`, `GIT_FAILED`, `LIMIT_EXCEEDED`, `UNSUPPORTED_STATE`, `UNSTABLE_STATE`, `STORE_PATH_INVALID`, `STORE_FAILED`, `SNAPSHOT_NOT_FOUND`, `SNAPSHOT_UNREADABLE`, `SNAPSHOT_CORRUPT`, `SNAPSHOT_INCOMPATIBLE`) 2. MATCH는 실행 권한, gate PASS, BUNDLE_AUTHORIZATION 복원, 스냅샷 사이 변경 이력의 부재를 뜻하지 않는다.
- D14 atomic: `atomic_create_new_bytes(path, data) -> Path`와 예외 `CreateNewError(cause, final_created, tmp_leftover)`를 추가한다. 부모 디렉터리를 만들지 않는다. 순서는 같은 디렉터리에 `mkstemp` tmp 작성 → flush·fsync → `os.link(tmp, path)`(대상이 있으면 `FileExistsError`) → tmp unlink. link 전 실패(부모 없음 `FileNotFoundError`, tmp 작성·fsync 오류, link 미지원·권한 오류, `FileExistsError`)는 이 호출이 만든 tmp 하나만 삭제를 시도하고 `CreateNewError(cause=<원래 예외>, final_created=False, tmp_leftover=<삭제 실패 시 경로, 성공 시 None>)`를 올린다. link 성공 후 unlink 실패는 `CreateNewError(cause=<unlink 오류>, final_created=True, tmp_leftover=<경로>)`를 올린다. 최종 파일·기존 파일·다른 실행의 tmp는 삭제하지 않는다. 기존 함수·상수는 바꾸지 않는다(numstat 삭제 0).
- D15 격리: workstate 패키지는 표준 라이브러리, `moneylab.storage.atomic`, 자기 패키지만 import한다. subprocess 호출은 1곳·git만·shell 없음이다. 네트워크·provider·trading·automation 모듈을 import하지 않는다.
- D16 README §11: docs/tasks/README.md §11의 마지막 문단(BASE 기준 141행, "…포함한다."로 끝남) 다음에 빈 줄 하나와 TEXT-README-11을 추가한다. 기존 줄은 삭제·수정하지 않는다. 행 번호·앵커가 다르면 STOP한다.
- D17 플랫폼 의존 테스트: `os.path.islink`·`Path.is_junction`·`st_file_attributes`·`S_ISREG` 판정은 monkeypatch 오류 주입 단위 테스트로 항상 실행한다. 실제 symlink·junction을 만드는 통합 케이스는 OS가 생성을 거부할 때(Windows `winerror 1314`, POSIX `EPERM`·`ENOTSUP`)만 `pytest.skip("NOT_RUN_PLATFORM: <case-id>")`로 미실행 처리하며 그 밖의 오류는 실패다. 권한 상승·설정 변경은 하지 않는다. NOT_RUN_PLATFORM이 하나라도 있으면 해당 AC는 `PARTIAL (NOT_RUN_PLATFORM: <case-id 목록>)`이며 PASS가 아니고, 그 gate의 `<GATE>_PASS`는 YES가 아니다. BUNDLE 안에서는 그 gate 보고에서 STOP한다. 이 skip 추가와 이유는 README §14 BGA-8 (A)의 검토 대상으로 그대로 보고한다. 후속 처리는 미실행 case ID와 위험을 명시한 사용자의 별도 결정에 따른다. PR_CI Windows runner에서 해당 케이스가 실행됐으면 INDEPENDENT 증거로 따로 보고하고, 실행되지 않았으면 COMPLETE 보고에 미해결로 남긴다.

TEXT-README-11:
```
작업 상태 스냅샷(`python -m moneylab.workstate`, AUTO-02)은 gate 보고가 아니다. ignored 경로 `data/processed/workstate/`에만 쓰는 비권위 로컬 기록이며 Git에 넣지 않는다. 승인·권한·gate PASS를 만들지 않고 종료된 BUNDLE_AUTHORIZATION을 되살리지 않는다. 일치 판정은 새 승인의 ENTRY 값을 대조하는 데에만 쓴다. 이 기록에는 위의 파일 보관 제한이 적용되지 않는다.
```

## TEST_GATES

TEST_GATES:
- 신규 테스트 파일 5개 targeted 실행 통과(D17의 NOT_RUN_PLATFORM은 통과로 세지 않음)
- ruff(CI와 같은 명령): `.\.venv\Scripts\python.exe -m ruff check --no-cache --select E4,E7,E9,F src tests`
- mypy(CI와 같은 명령): `.\.venv\Scripts\python.exe -m mypy`
- mypy(명시적 경로 추가 보장, CLAUDE_REPORTED): `.\.venv\Scripts\python.exe -m mypy src/moneylab/workstate src/moneylab/storage/atomic.py` 오류 0. CI mypy의 workstate 검사 여부와 무관하게 유지한다.
- IMPLEMENTATION에서 전체 pytest 1회 `./.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q -rs`, failed 0 / errors 0
- `git diff --check` 깨끗함, 변경 파일 집합 = ALLOWED_FILES, PROTECTED diff 0
- README §14 BGA-8 (A) 수동 확인: 신규 테스트의 skip 추가와 그 이유를 포함해 그대로 보고한다. (B)는 "독립 검토 필요"로 보고한다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA (git·grep·pytest 및 읽기 전용 바이트·해시 확인):
- 평가 시점: 구현 커밋 전 AC1–AC3은 C1과 현재 작업 파일·index의 후보 변경으로, 구현 커밋 후에는 commit 간 비교로 확정한다. 존재하지 않는 커밋·PR·CI의 검사를 PASS로 보고하지 않는다.
- AC1 C1 parent = CANONICAL_BASE_SHA, C1 변경 = docs/tasks/AUTO-02/WORK_ORDER.md 하나. `git diff --name-status <C1> <구현 커밋>` = ALLOWED_FILES 11개와 A/M 표기 일치. base→구현 커밋 전체 변경 = 계약 파일 ∪ ALLOWED_FILES
- AC2 C1→구현 커밋 PROTECTED_FILES diff 비어 있음. Work Order blob 내용 SHA-256은 승인값과 같고 불변
- AC3 `git diff --numstat <CANONICAL_BASE_SHA> <구현 커밋>`에서 src/moneylab/storage/atomic.py와 docs/tasks/README.md의 삭제 수 0
- AC4 기준선의 `pytest --collect-only -q` 테스트 ID가 모두 구현 커밋에서도 수집됨(감소 0). 기존 테스트 파일 diff 0
- AC5 CLI: verify에 `--snapshot-id` 또는 `--task-id`가 없거나 형식이 틀린 경우, 알 수 없는 인자가 있는 경우, `--reported-*`를 한쪽만 준 경우 각각 `ARGUMENT_INVALID`, 종료 2, stdout은 D13 결과 객체 하나의 canonical JSON + LF, stderr 비어 있음. latest·목록 경로가 없음
- AC6 대조(tmp 저장소): clean 상태에서 snapshot을 만들고 곧바로 verify하면 MATCH다. 그 스냅샷을 기준으로 다음 변경을 각각 따로 가한 뒤 verify하면 모두 MISMATCH이고 `differences`에 해당 field가 보고된다: tracked 파일 수정(`entries`), stage(`entries`), 삭제(`entries`), rename(삭제와 추가 두 항목, `entries`), untracked 파일 추가(`untracked`), 파일 내용을 실제로 바꾼 새 commit(`head`와 `tree`; 빈 commit은 `head`만 바뀔 수 있으므로 tree 검증에 쓰지 않는다), branch 전환(`branch`, 필요 시 `head`), detached HEAD 전환(`branch`), 계약 파일 변경(`contract`). 같은 상태에서 `meta`나 `reported`만 다르게 snapshot을 만든 뒤 verify하면 MATCH다. 상태 A→B→A를 거치면 A의 snapshot_id가 처음과 같고 그 ID로 verify하면 MATCH다.
- AC7 거부·불안정: unborn, unmerged, 진행 중 merge, skip-worktree, assume-unchanged 각각 UNSUPPORTED_STATE. 변경·untracked·계약 경로 또는 그 상위 디렉터리의 symlink·junction·reparse는 오류 주입 단위 테스트에서 항상 UNSUPPORTED_STATE이고, 실제 링크 통합 케이스는 D17을 따른다. 수집 중 파일 변경 주입은 UNSTABLE_STATE. 각 상한 초과 주입(stdout·stderr·blob·W 파일·경로 수·경로 길이·합계)은 LIMIT_EXCEEDED이고 자식 프로세스가 회수됨. git 비정상 종료·timeout 주입은 GIT_FAILED. 모두 종료 2, MATCH 아님, 저장 없음. 실제 링크 통합 케이스에 NOT_RUN_PLATFORM이 있으면 이 AC는 PARTIAL이다.
- AC8 저장: ignored 아닌 경로, 저장 경로 구성 요소의 symlink·junction·reparse(오류 주입 단위 테스트 필수, 실제 링크는 D17), root 밖 경로는 STORE_PATH_INVALID이며 기록 파일 생성 없음. `data`·`processed`·`workstate`·`<TASK_ID>`가 없는 tmp 저장소에서 snapshot은 위에서 아래로 생성 후 STORED. mkdir 중 FileExistsError 주입 시 일반 디렉터리면 계속하고, 링크·비디렉터리면 STORE_PATH_INVALID. 이후 단계 실패 시 만든 디렉터리는 남고 `DIR_LEFT` warning. verify는 디렉터리를 만들지 않음. 같은 ID 재실행(meta 시각만 다름)은 ALREADY_STORED이고 기존 파일 바이트·meta 불변이며 반환 file_sha256 = 기존 파일 바이트 해시. 새로 쓴 STORED의 file_sha256 = 생성된 파일 바이트 해시. 같은 ID의 기존 파일이 D11 검증(3·5·6·7·8단계)에 실패하면 해당 오류(STORE_PATH_INVALID, SNAPSHOT_UNREADABLE, SNAPSHOT_CORRUPT, SNAPSHOT_INCOMPATIBLE)를 반환하고, 검증은 통과했으나 ID 대상 객체(schema·task_id·state·reported)가 새 객체와 다르면 SNAPSHOT_CORRUPT를 반환하며, 두 경우 모두 기존 파일을 보존한다. 유효한 meta 차이만으로는 CORRUPT로 판정하지 않고 ALREADY_STORED이다. 두 스레드·두 프로세스가 같은 ID를 동시에 쓰면 파일 1개, 한쪽 STORED·다른 쪽 ALREADY_STORED, 두 file_sha256 동일. link 후 tmp 정리 실패 주입은 STORED, `TMP_LEFTOVER` warning, exit 1, final_file_created true. link 전 실패와 tmp 삭제 실패 동시 주입은 STORE_FAILED, `TMP_LEFTOVER` warning, final_file_created false, 최종 파일 없음. 1 MiB 초과 기록은 LIMIT_EXCEEDED이며 생성 없음. 실제 링크 통합 케이스에 NOT_RUN_PLATFORM이 있으면 이 AC는 PARTIAL이다.
- AC9 verify 오류: 없음 SNAPSHOT_NOT_FOUND(file_sha256 null), 읽기 오류 SNAPSHOT_UNREADABLE(null), 기록 파일이 symlink·junction이면 STORE_PATH_INVALID, 링크가 아닌 비정규 파일(디렉터리 등)·1 MiB 초과는 SNAPSHOT_CORRUPT(null), 바이트 1개 변경·비canonical·중복 키·파일 이름 불일치·task_id 불일치는 SNAPSHOT_CORRUPT(file_sha256 = 실제 파일 바이트 해시), 알 수 없는 schema 문자열은 SNAPSHOT_INCOMPATIBLE. 모두 종료 2, 다른 파일로 대체 없음, 파일 삭제 없음, 디렉터리 생성 없음
- AC10 snapshot 실행 전후 tmp 저장소의 `git status --porcelain=v2 --ignored=no` 출력, `.git/index` 바이트 SHA-256, HEAD가 같음
- AC11 기록 파일 키 집합 = D9 allowlist. tracked·untracked 파일에 넣은 표식 문자열, 환경변수 값, worktree 절대 경로가 기록 바이트에 없음
- AC12 모든 결과 객체(성공·경고·오류)가 D13 키 집합을 정확히 가지며 `authority` = "NONE", `compared`·`not_compared`가 고정 목록과 같고, status·exit_code 대응이 D13과 같음
- AC13 격리: import allowlist, subprocess 호출 1곳·git만·shell 없음, git 하위 명령 allowlist, `GIT_OPTIONAL_LOCKS=0`, timeout·stdout·stderr 상한과 자식 회수 적용
- AC14 `atomic_create_new_bytes` 단위 테스트: 신규 생성; 대상 존재 시 `cause`=FileExistsError·`final_created`=False·대상 바이트 불변; 부모 없음 시 `cause`=FileNotFoundError·디렉터리 미생성; fsync·link 오류 주입 시 최종 파일 없음·tmp 없음; 같은 오류와 tmp 삭제 오류 동시 주입 시 `cause`=원래 오류·`final_created`=False·`tmp_leftover`=그 경로·최종 파일 없음; link 성공 후 unlink 오류 주입 시 `final_created`=True·`tmp_leftover` 설정·최종 파일 유효; link 미지원 주입 시 덮어쓰기 없음; 같은 디렉터리의 다른 실행 tmp와 기존 파일은 호출 후에도 그대로. 기존 tests/test_atomic_storage.py 무변경 통과
- AC15 docs/tasks/README.md에 TEXT-README-11이 정확히 1회 §11 안에 있고, 삭제 0
- AC16 IMPLEMENTATION과 CLEAN_COMMIT_E2E 각각 전체 pytest failed 0 / errors 0 (CLAUDE_REPORTED). NOT_RUN_PLATFORM skip은 별도 목록으로 보고한다.
- AC17 `git diff --check` 통과, ALLOWED_FILES 전부 LF·끝 줄바꿈
- AC18 이 Work Order의 `## Metadata` 절에 `WORK_ORDER_CONTRACT_VERSION: v1.3`, `BUNDLE_ELIGIBLE: YES`, `BUNDLE_MAX_RANGE: IMPLEMENTATION..CLEAN_COMMIT_E2E`가 있음
- AC19 ruff·mypy(CI 명령)와 명시적 경로 mypy 오류 0 (CLAUDE_REPORTED)
- AC20 PR_CI에서 승인된 정확한 PR head의 ci-tests / pytest (Windows) SUCCESS (INDEPENDENT). 이전 gate에서는 NOT_YET_APPLICABLE

## E2E_GATES

E2E_GATES:
- clean 구현 커밋에서 전체 pytest 1회와 AC1–AC19 확인. AC16의 IMPLEMENTATION 실행과 이 실행을 구분한다.
- 실제 저장소에서 `./.venv/Scripts/python.exe -B -m moneylab.workstate verify --task-id AUTO-02 --snapshot-id 0000000000000000000000000000000000000000000000000000000000000000` 1회: 종료 2, status SNAPSHOT_NOT_FOUND, file_sha256 null, final_file_created null, 실행 전후 `git status --porcelain=v2 --ignored` 동일, `data/processed/workstate/` 미생성
- 실제 저장소에서 snapshot 실행 금지
- `git diff --name-only <CANONICAL_BASE_SHA> <구현 커밋> -- src tests`가 ALLOWED_FILES의 src·tests 경로 10개와 같음

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 커밋 SHA·tree, ALLOWED_FILES blob 전후, `git diff --numstat`, 변경 파일 집합, merge parent·tree
- CLAUDE_REPORTED: pytest·ruff·mypy·E2E 결과, AC 확인, BGA-8 (A), NOT_RUN_PLATFORM 목록
- INDEPENDENT: PR CI(ci-tests / pytest (Windows))와 그 실행에서의 플랫폼 케이스 실행 여부, 사용자 검토. BGA-8 (B)는 "독립 검토 필요"로 보고

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- AC별 PASS / PARTIAL / FAIL / NOT_YET_APPLICABLE, NOT_RUN_PLATFORM case ID와 위험
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES, GUARD_EVENTS(관찰 가능한 범위만)
- <GATE>_PASS = YES / NO (PARTIAL AC가 있으면 YES가 아니다)
- READY_FOR_<NEXT_GATE> = YES / NO

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree·BASE_BLOBS 불일치, Work Order sha256 불일치, D16 앵커 불일치
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅, A/M 표기 불일치
- atomic.py·README.md 기존 줄의 삭제·수정(numstat 삭제 수 > 0), 기존 테스트 변경·약화
- 실제 저장소에서 snapshot 실행 또는 `data/processed/workstate/` 생성
- guard deny, 예상하지 못한 ASK, 편집·commit·push 승인 창 거절·무응답
- 테스트·ruff·mypy 실패·에러(BUNDLE 안에서는 README §14 BGA-4·BGA-10), AC 불충족
- NOT_RUN_PLATFORM으로 PARTIAL AC 발생(BUNDLE 안에서는 그 gate 보고에서 STOP, 개별 진행에서도 gate PASS는 YES가 아님)
- 대상 파일 시스템에서 os.link를 쓸 수 없음(대체 구현 없이 STOP, PROPOSED_ERRATA로 보고)
- 계약 모순, 상위 규칙과 충돌, 예상하지 못한 untracked 파일
