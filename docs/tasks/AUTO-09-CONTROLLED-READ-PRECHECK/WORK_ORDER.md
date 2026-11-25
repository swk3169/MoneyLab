# Work Order: AUTO-09-CONTROLLED-READ-PRECHECK — controlled_read precheck 하위 명령

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 ACCEPTED ERRATA로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: AUTO-09-CONTROLLED-READ-PRECHECK
TASK_ID: AUTO-09-CONTROLLED-READ-PRECHECK
TITLE: 지정 세션 하나의 bounded prefix에서 PROFILE 후보를 찾아 run SELECTOR를 반환하는 precheck
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: d471d644279ed8b2fe861a23dedca7765c5511ac
CANONICAL_BASE_TREE: 31b2a776c5d341dcba311a0c2d1fd318aa7a5928
TARGET_BRANCH: codex/auto-09-controlled-read-precheck
TARGET_WORKTREE: C:/MoneyLab-auto-09
SETUP_SESSION_ROOT: C:/MoneyLab-auto-08 (WORKSPACE_SETUP PART=WORKTREE 전용)
SESSION_ROOT: C:/MoneyLab-auto-09 (WORKSPACE_SETUP PART=C1_ENV부터 COMPLETE까지)
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: pytest
BUNDLE_ELIGIBLE: NO
BUNDLE_MAX_RANGE: NONE

## GATE_SEQUENCE

GATE_SEQUENCE: WORKSPACE_SETUP PART=WORKTREE -> WORKSPACE_SETUP PART=C1_ENV -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_AUTHORIZATION_FORMS

- WORKSPACE_SETUP PART=WORKTREE (SETUP_SESSION_ROOT 세션에서 받는다):
  `GATE_AUTHORIZATION: AUTO-09-CONTROLLED-READ-PRECHECK WORKSPACE_SETUP PART=WORKTREE WO_SHA256=<64hex>`
- WORKSPACE_SETUP PART=C1_ENV (SESSION_ROOT에서 새로 시작한 세션에서 받는다):
  `GATE_AUTHORIZATION: AUTO-09-CONTROLLED-READ-PRECHECK WORKSPACE_SETUP PART=C1_ENV WO_SHA256=<64hex> WO_SOURCE=<C:/MoneyLab-auto-09 밖의 절대 경로> BYTES_SCRIPT_SHA256=<64hex>`
- IMPLEMENTATION, PRECOMMIT_AUDIT, COMMIT, CLEAN_COMMIT_E2E, PUSH, PR_CI, MERGE, POST_MERGE_AUDIT, COMPLETE (SESSION_ROOT 세션에서 받는다):
  `GATE_AUTHORIZATION: AUTO-09-CONTROLLED-READ-PRECHECK <GATE> WO@<C1 SHA>`
  PR_CI와 MERGE는 docs/tasks/README.md §13이 요구하는 추가 필드(PR_CREATE: YES, MERGE_EXECUTE: YES, 저장소, base, head branch, head SHA, PR 번호, PR 제목·본문)를 함께 적는다.

## GATE_TRANSITION_RULES

- 한 번에 한 단계만 전진한다. 각 단계에는 그 단계를 실행하는 세션에서 사용자가 보낸 Gate Authorization 원문이 있어야 한다. 원문을 확인할 수 없으면 STOP한다.
- 세션이 바뀌면 이전 세션의 승인은 이어지지 않는다.
- 후퇴는 IMPLEMENTATION으로만, 명시적 승인으로 한다.
- COMMIT 이후 수정은 새 커밋으로 한다. amend는 쓰지 않는다.

## AUTHORIZATION_MODEL

- 이 Work Order는 각 gate의 최대 범위만 정한다. ALLOWED_FILES와 FILE_CREATION은 변경 허용 범위일 뿐 실행 승인이 아니다.
- 변경에는 다음 세 가지가 모두 있어야 한다: (1) 이 Work Order의 gate 범위 (2) 사용자의 해당 Gate Authorization (3) 도구 권한 창과 guard 승인. 어느 하나가 다른 것을 대신하지 않는다.
- guard.py와 docs/agent_workflow.md 변경은 관리자 결정에 따라 D11·D12 범위에서만 허용된다. 이 결정은 도구 권한 창과 guard 판정을 대신하지 않는다.
- AUTO-08-CONTROLLED-READ의 예산·원장·종결 기록은 읽거나 바꾸지 않으며 이 task 예산과 합산하지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, .claude guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않는다.

## GOAL

GOAL: moneylab.controlled_read에 precheck 하위 명령 하나를 추가한다. precheck는 지정 세션 파일 하나의 bounded prefix에서 D7 호환성과 PROFILE 표식 후보를 확인하고, 전체 스캔 결과 후보가 유일할 때만 그 후보를 기존 run SELECTOR 문법으로 반환한다. 본문·텍스트는 출력하거나 저장하지 않는다.

## BACKGROUND

BACKGROUND: AUTO-08-CONTROLLED-READ(PR #56, merge d471d644279ed8b2fe861a23dedca7765c5511ac)의 run은 SELECTOR를 입력으로 요구하지만, 원문을 열람하지 않고 SELECTOR를 정할 수단이 없다. 이것이 FIRST-USE의 기능 공백이다.

## GUARD_SESSION_NOTICE

- SESSION_ROOT 세션의 PreToolUse hook은 C:/MoneyLab-auto-09/.venv/Scripts/python.exe로 C:/MoneyLab-auto-09/.claude/hooks/guard.py를 실행한다. 따라서 AUTO-09 전용 venv가 있고 버전 확인을 통과한 뒤에만 SESSION_ROOT 세션을 시작한다(WS-A6).
- IMPLEMENTATION에서 guard.py를 고치면 그 세션의 활성 guard가 즉시 바뀐다.
- guard.py 편집은 D11 (a)와 (b) 두 단위로 나눠 Edit 1회씩 한다. 각 Edit 직후 정상 읽기 명령 `git status --porcelain=v1`을 1회 실행한다. hook 오류, 차단, 목록 밖 ASK 가운데 하나라도 나오면 STOP한다.
- guard 오류로 도구가 모두 막히면 세션은 스스로 복구하지 않는다. 보고하고 사용자의 조치를 기다린다.
- 다른 worktree의 guard는 편집하지 않는다. settings 변경, guard 우회, 통과 명령 탐색은 금지한다.

## EXPECTED_ASK

다음 지점에서는 settings 또는 guard의 ASK가 나타날 수 있다. 나타나면 사용자가 그 창에서 판단한다. 목록 밖의 ASK, 거절, 무응답은 STOP이다.
- WS-B4의 WORK_ORDER.md Write, WS-B3의 bytes_check.py Write
- BYTES_SCRIPT 실행
- IMPLEMENTATION의 .claude/hooks/guard.py Edit, docs/agent_workflow.md Edit
- `git commit`, `git push`, `gh pr ...`

## NETWORK

- N1 PART=WORKTREE: `git -C C:/MoneyLab-auto-08 ls-remote origin refs/heads/main`, `git -C C:/MoneyLab-auto-08 ls-remote origin refs/heads/codex/auto-09-controlled-read-precheck` 각 1회.
- N2 PART=C1_ENV: E3, E4의 pip 명령 각 1회(PyPI. E4는 build isolation 때문에 setuptools를 받을 수 있다).
- N3 PUSH: `git push -u origin codex/auto-09-controlled-read-precheck` 1회.
- N4 PR_CI: `gh pr create` 1회(§13 조건 충족 시). CI_CRITERIA의 `gh pr checks`, `gh run list`, `gh run view` 조회.
- N5 MERGE: `gh pr merge` 1회(§13 조건 충족 시).
- N6 POST_MERGE_AUDIT: `git fetch origin main` 1회.
- 위 밖의 네트워크는 금지한다. venv 생성(E1), 시험, 검사, 바이트 계산은 오프라인이다. 네트워크 명령이 실패하면 STOP하고 재시도하지 않는다.

## ENVIRONMENT_RECOVERY_ONCE

- C1 발행 전 E6에서 두 번 실패한 현재 AUTO-09 환경에만 적용한다. 이전 실패·STOP과 로그 조회 권한 거절은 보존하며 원인이 Windows 정책이라고 확정하지 않는다.
- 관리자가 승인한 설치 대안은 공식 mypy 2.4.0 소스 배포의 interpreted 방식이다. 보안 설정·예외·guard·hook·settings·인터프리터는 변경하지 않는다. 거절된 이벤트 조회도 재시도하지 않는다.
- E3·E4를 반복하거나 venv를 재생성하지 않는다. 아래 명령 하나만 별도 gate 승인으로 최초 1회 실행할 수 있다:
  `.venv/Scripts/python.exe -m pip install --force-reinstall --no-deps --no-binary=mypy --no-cache-dir mypy==2.4.0`
- 이 명령에 한해 N2 네트워크 범위를 추가한다. 공식 PyPI의 mypy 소스와 빌드 격리에 필요한 빌드 의존성 다운로드를 허용한다. 빌드 의존성 버전은 이 계약에서 고정하지 않는 한계가 있다. 다른 인덱스·직접 URL·보안 차단 해제는 허용하지 않는다.
- F3의 설치 산출물 예외는 위 mypy 교체에도 적용한다. mypy의 기존 설치 파일 교체만 허용하며 다른 배포판은 재설치하지 않는다. 빌드 임시 파일은 pip가 운영하는 시스템 임시 경로에서 생성·정리될 수 있다.
- 설치 실패·DENY·권한 거절이면 즉시 STOP하고 대체 명령을 실행하지 않는다. 성공한 경우 E5와 E6을 각각 1회 실행하여 pip check 정상 및 mypy 2.4.0 (compiled: no)를 확인한다. 어느 하나라도 실패하면 STOP한다.
- 위 확인 후 명시적으로 승인된 경우에만 WS-B3부터 계속한다. 성공해도 DLL 실패 원인이 밝혀졌다고 주장하지 않는다.

## RECORD_OUTPUTS

기록 파일은 아래 10개뿐이다. 각 파일은 지정된 명령의 stdout을 셸 리디렉션으로 그대로 저장하고, 생성 직후 `sha256sum <파일>` 값을 보고한다. 생성 뒤에는 수정·삭제·덮어쓰기를 하지 않는다. Write 도구로 옮겨 적지 않는다.

- 디렉터리 P = C:/MoneyLab-auto-08/data/processed/auto09_pre (PART=WORKTREE)
  - P1 pre_worktrees.txt: `git -C C:/MoneyLab-auto-08 worktree list --porcelain`. worktree 생성 전.
  - P2 pre_refs.txt: `git -C C:/MoneyLab-auto-08 for-each-ref "--format=%(objectname) %(refname)" refs/heads refs/remotes refs/tags`. worktree 생성 전.
- 디렉터리 B = C:/MoneyLab-auto-09/data/processed/auto09/baseline (PART=C1_ENV부터)
  - B1 post_env_status.txt: `git status --porcelain=v1 --ignored=traditional --untracked-files=normal`. 환경 준비 직후(E7).
  - B2 collect_base.txt: `.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q`. E8.
  - B3 mypy_cr_base.txt: `.venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache src/moneylab/controlled_read`. E9.
  - B4 collect_precommit.txt: B2와 같은 명령. PRECOMMIT_AUDIT.
  - B5 e2e_status_before.txt: B1과 같은 명령. CLEAN_COMMIT_E2E 실행 전.
  - B6 e2e_status_after.txt: B1과 같은 명령. CLEAN_COMMIT_E2E 실행 후.
  - B7 complete_worktrees.txt: `git worktree list --porcelain`. COMPLETE.
  - B8 complete_refs.txt: `git for-each-ref "--format=%(objectname) %(refname)" refs/heads refs/remotes refs/tags`. COMPLETE.

기록 규칙:
- 디렉터리 생성 전: `test -e <디렉터리>` → 종료 코드 1, `git -C <해당 worktree> check-ignore -q <디렉터리>/x` → 종료 코드 0. 그다음 `mkdir -p <디렉터리>`. 조건이 다르면 STOP한다.
- 파일 생성 전: `test -e <파일>` → 종료 코드 1. 생성 명령은 `set -C && <명령> > <파일>` 형태로 한 호출에서 실행한다(noclobber).
- 기록 명령 자체의 종료 코드가 기대와 다르면 STOP한다(B3은 E9 조건을 따른다).

## FILE_CREATION

이 task에서 생길 수 있는 파일은 아래 분류뿐이다. 분류 밖의 파일이 생기면 STOP한다.
- F1 tracked 신규 파일: ALLOWED_FILES의 A 항목(tests/test_controlled_read_precheck.py) 1개.
- F2 C1: docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md 최초 작성 1회(WS-B4).
- F3 venv·설치 산출물: C:/MoneyLab-auto-09/.venv/** (E1, E3, E4), 그리고 E4가 만드는 ignored 메타데이터. E4 뒤 `git status --porcelain=v1`이 빈 출력이어야 한다.
- F4 합성 시험 자료: pytest tmp_path(시스템 임시 디렉터리, 저장소 밖)만.
- F5 검사 캐시: C:/MoneyLab-auto-09/.venv/.mypy_cache/**만. pytest는 `-B -p no:cacheprovider`, ruff는 `--no-cache`, BYTES_SCRIPT는 `-I -B`로 실행해 그 밖의 캐시를 만들지 않는다.
- F6 기록: RECORD_OUTPUTS의 10개와 그 두 디렉터리.
- F7 검사 스크립트: C:/MoneyLab-auto-09/data/processed/auto09/tools/bytes_check.py 1개(WS-B3). 디렉터리 생성은 RECORD_OUTPUTS의 디렉터리 규칙을 따른다.
- F1·F2·F7은 생성 전에 `test -e <파일>` → 종료 코드 1을 확인한다. F6·F7은 덮어쓰지 않는다.

## BYTES_SCRIPT

경로: C:/MoneyLab-auto-09/data/processed/auto09/tools/bytes_check.py
내용: 아래 BEGIN과 END 표식 줄 사이의 줄들(표식 줄 제외)이다. 각 줄은 LF로 끝나고 BOM은 없다. 그 바이트의 sha256이 BYTES_SCRIPT_SHA256이다.
실행: `.venv/Scripts/python.exe -I -B data/processed/auto09/tools/bytes_check.py <경로> [<경로> ...]`
의미: 각 경로의 파일 바이트 W를 읽기 전용으로 읽는다. CRLF만 LF로 바꾼 S를 계산하고, 바꾼 뒤 CR이 남으면 실패한다.
출력: 성공한 경로마다 `<W sha256> <S sha256> <경로>` 한 줄, CR이 남으면 `CR_REMAINS <경로>` 한 줄.
종료 코드: 0 = 모두 성공, 3 = CR_REMAINS 하나 이상, 2 = 인자 없음, 그 밖(예외 1 포함) = 도구 오류(STOP).

----- BEGIN BYTES_SCRIPT -----
import hashlib
import sys


def main(paths):
    if not paths:
        return 2
    status = 0
    for path in paths:
        with open(path, "rb") as handle:
            data = handle.read()
        stored = data.replace(b"\r\n", b"\n")
        if b"\r" in stored:
            sys.stdout.write("CR_REMAINS " + path + "\n")
            status = 3
            continue
        line = hashlib.sha256(data).hexdigest() + " " + hashlib.sha256(stored).hexdigest() + " " + path
        sys.stdout.write(line + "\n")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
----- END BYTES_SCRIPT -----

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경(WS-B4의 WORK_ORDER.md 최초 작성 1회만 예외)
- FILE_CREATION 분류 밖 파일 생성, 기록·검사 스크립트의 수정·삭제·덮어쓰기
- 보호 경로에 cp·셸 리디렉션으로 쓰기
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, `fetch --all`, `fetch --prune`
- settings 변경, guard 우회, 통과 명령 탐색, 범용 Python 실행 허용, guard 문자열 은닉, `python -c` 실행
- 다른 worktree의 guard·파일 편집(WS-A의 P 기록과 C:/MoneyLab-auto-09 생성 제외)
- 인터프리터 교체, Windows 보안 설정 변경
- 실제 사용자 home·`.claude/projects/**`·실제 세션 JSONL·debug 로그·연구 데이터 열람(보존 확인 목적 포함)
- precheck·run CLI를 실제 home 대상으로 실행
- 기존 data 파일 읽기·변경
- 기존 시험 함수의 수정·삭제, skip·skipif·xfail 추가, 단정 완화, 기존 인코딩 검사 시험의 예외 목록 변경
- 다른 branch·worktree·untracked·ignored·reference 산출물 정리
- STOP 뒤 재실행, 변형 재시도, 되돌리기 명령

## ALLOWED_FILES

ALLOWED_FILES:
- M src/moneylab/controlled_read/__main__.py
- M src/moneylab/controlled_read/selector.py
- M src/moneylab/controlled_read/transcript.py
- M src/moneylab/controlled_read/profiles.py
- M src/moneylab/controlled_read/store.py
- M .claude/hooks/guard.py
- M docs/agent_workflow.md
- M tests/test_agent_guard.py
- A tests/test_controlled_read_precheck.py

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/** (WS-B4의 WORK_ORDER.md 최초 작성 1회만 예외)
- docs/tasks/AUTO-08-CONTROLLED-READ/**
- .claude/** 중 .claude/hooks/guard.py를 제외한 모든 경로
- src/moneylab/controlled_read/__init__.py
- tests/test_controlled_read_cli.py
- tests/test_controlled_read_selector.py
- tests/test_controlled_read_transcript.py
- tests/test_controlled_read_profiles.py
- tests/test_controlled_read_store.py
- tests/test_controlled_read_isolation.py
- CLAUDE.md, pyproject.toml, requirements.txt, requirements-dev.txt, .gitattributes, .gitignore, .github/**, configs/**
- data/** (FILE_CREATION의 F6·F7 최초 생성만 예외. 이 파일들은 ignored이며 tracked 변경이 아니다)
- docs/research_*

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

## FILE_FORMAT

- 적용 대상: 신규 파일 전체, 그리고 수정 파일에서 추가·변경한 줄. 수정 파일의 변경하지 않은 기존 줄은 다시 쓰지 않고 검사 대상에서 뺀다.
- 규칙: UTF-8(BOM 없음), 줄 끝 LF, 파일 끝 LF 1개, `git diff --check` 위반 없음.
- 저장소의 기존 인코딩 검사 시험이 허용하는 예외 줄은 그대로 둔다. 그 시험과 예외 목록은 고치지 않는다. 신규·변경 줄이 그 시험을 실패시키면 IMPLEMENTATION 안에서 신규·변경 줄을 고친다.
- 바이트 정의: W는 작업 파일 바이트의 sha256, S는 CRLF만 LF로 바꾼 예상 저장 바이트의 sha256이다. 둘 다 BYTES_SCRIPT로만 계산한다. BYTES_SCRIPT가 종료 코드 3을 내면 FILE_FORMAT 위반이다.
- BYTES_SCRIPT는 W·S 계산과 단독 CR 확인에만 쓴다. BYTES_SCRIPT 통과만으로 FILE_FORMAT 전체 통과를 선언하지 않는다.
- 신규 파일(tests/test_controlled_read_precheck.py)은 UTF-8 strict 디코딩, BOM 없음, 파일 끝 LF 정확히 1개를 따로 확인한다.
- 기존 파일의 추가·변경 줄은 위 형식 규칙과 `git diff --check`로 확인한다.
- 이 확인들의 정확한 검사 방법은 해당 실행 gate의 Gate Authorization에서 고정한다. 위반은 보고만 하고 자동 정정하지 않는다.
- 신규 시험의 합성 비ASCII 입력은 소스에서 명시적 이스케이프(`\uXXXX`, `\xNN`, bytes 이스케이프)로 쓴다. 기존 시험 파일의 UTF-8 줄은 변경하지 않는다.
- 대조: staged 내용은 `git cat-file blob :<path> | sha256sum`, commit 내용은 `git cat-file blob HEAD:<path> | sha256sum`으로 계산해 S와 비교한다. Git blob object ID를 내용 sha256과 혼동하지 않는다.

## DESIGN_CONTRACT

D1 호출 형태(유일):
`.venv/Scripts/python.exe -B -m moneylab.controlled_read precheck --task <TASK_ID> --project-key <PROJECT_KEY> --session <SESSION> --profile <PROFILE>`
값 문법은 run과 같다. 옵션 순서는 고정이고 각 1회이며 추가 토큰은 없다.

D2 run/status 불변. 다음을 바꾸지 않는다.
- run·status의 CLI와 인자 문법
- 스키마 result/1, intent/1, stored_result/1, status/1, status_error/1
- __init__.DETAILS, ERROR_CODES
- store.valid_result, RESULT_KEYS, TARGET_KEYS, BEFORE_PREFIX, AFTER_PREFIX, NON_STORABLE, CHECK_STATUSES
- 기록 경로와 저장 방식
__main__.run()에는 `argv[:1] == ["precheck"]` 분기 하나만 추가한다.

D3 기록 없음: store.prepare_attempt와 store.create_record를 호출하지 않고 파일을 만들지 않는다. 자식 프로세스는 confirmed_root의 git 하나다.

D4 재사용(기존 시그니처와 동작 불변):
- selector: _values, parse_selector, SELECTOR, valid_*
- __main__: confirmed_root, confirmed_home
- transcript: Deadline, open_session, Session.rehash, _lines, parse_line, _user_blocks, _assistant_texts, select_text
- profiles: PROFILES, check_kind, extract, values
- store: canonical_bytes, profile_ref

D5 신규:
- selector: PRECHECK_OPTIONS = ("--task", "--project-key", "--session", "--profile"), PrecheckArgs(task_id, project_key, session_id, profile), parse_precheck(argv) -> PrecheckArgs. 실패하면 ControlledReadError("ARGUMENT_INVALID").
- selector: format_selector(kind, ident, text_index) -> str | None. 출력은 항상 `:text:<k>`를 붙인 run 문법이다. ident가 str이 아니거나 SELECTOR.fullmatch에 실패하면 None.
- profiles: marker_line_present(profile, text: str) -> bool. text의 CRLF를 LF로 바꾸고 LF로 나눈 줄 가운데 profile.begin 또는 profile.end의 ASCII 문자열과 정확히 같은 줄이 있으면 True. 한도·인코딩 검사는 하지 않는다.
- transcript: 기존 _tool_result_texts의 content 해석부를 _tool_result_content_texts(block) -> list[str]로 분리한다. _tool_result_texts는 기존 순서대로 is_error 검사와 TOOL_RESULT_ERROR를 처리한 뒤 이 함수를 호출한다. 기존 입력별 반환과 예외는 같다.
- transcript: Candidate(kind: str, ident: object, text_index: int, is_error: bool)(frozen dataclass), scan_candidates(prefix, kinds, is_candidate, deadline) -> list[Candidate].
- store: PRECHECK_SCHEMA = "moneylab.controlled_read.precheck/1", PRECHECK_OK = "PRECHECK_OK", PRECHECK_DETAILS(D8), PRECHECK_KEYS, precheck_document(...).
- __main__: _precheck(argv, root, home).

D6 후보(scan_candidates는 prefix 전체를 끝까지 스캔한 뒤 반환한다):
- 모든 줄에 parse_line을 적용한다. "uuid"가 있는데 str이 아니면 FORMAT_UNSUPPORTED다. _user_blocks도 모든 줄에 적용한다. 이 둘은 run의 _find와 같다.
- "assistant"가 kinds에 있으면: type == "assistant"인 entry마다, _assistant_texts(entry)의 k번째(1부터) text가 is_candidate이면 Candidate("assistant", entry.get("uuid"), k, False).
- "tool_result"가 kinds에 있으면: _user_blocks의 type == "tool_result" 블록마다 다음을 적용한다. tool_use_id가 str이 아니면 FORMAT_UNSUPPORTED, is_error가 있는데 bool이 아니면 FORMAT_UNSUPPORTED다. _tool_result_content_texts(block)의 k번째 text가 is_candidate이면 Candidate("tool_result", tool_use_id, k, is_error is True).
- 후보는 BEGIN 또는 END 독립 표식 줄을 하나라도 가진 text block이다. 표식이 불완전한 블록도 후보로 센다. 표식이 없는 정상 형식의 오류 결과는 후보가 아니다.
- 반환값은 위치·식별자뿐이고 text는 보관하지 않는다.
- 호환성 구분: 줄 파싱, uuid 타입, _user_blocks, tool_use_id 타입은 run도 요구하는 검사다. _assistant_texts와 content 검사를 profile kinds의 모든 블록에 적용하는 것은 run이 요구하지 않는 추가 탐색 검사다. 둘 다 checks.scan에 포함된다.

D7 종료 경로(_precheck). 각 경로마다 status / checks.scan / checks.selected / candidate_count / prefix_check / selector / values / error / exit_code를 적는다.
- P1 인자 오류: ARGUMENT_INVALID / checks=null / checks=null / null / target=null / null / null / 코드·문구 / 2. task_id와 profile도 null.
- P2 환경 오류: ENVIRONMENT_INVALID / NOT_REACHED / NOT_REACHED / null / null(측정 4개 null) / null / null / 코드·문구 / 2.
- P3 open_session 실패(SESSION_NOT_FOUND, SESSION_PATH_INVALID, SESSION_LIMIT_EXCEEDED, SESSION_UNREADABLE, SESSION_TRUNCATED, TIME_LIMIT_EXCEEDED): 그 코드 / NOT_REACHED / NOT_REACHED / null / null(측정 4개 null) / null / null / 코드·문구 / 2.
- P4 스캔 정의 실패(SESSION_CORRUPT, FORMAT_UNSUPPORTED, LINE_LIMIT_EXCEEDED, ENTRY_LIMIT_EXCEEDED): 그 코드 후 R / FAILED / NOT_REACHED / null / R의 값 / null / null / 코드·문구 / 2.
- P5 스캔 중 시간 초과: TIME_LIMIT_EXCEEDED / FAILED / NOT_REACHED / null / INCOMPLETE(재해시 없음) / null / null / 코드·문구 / 2.
- P6 후보 0개: PRECHECK_NO_CANDIDATE 후 R / PASSED / NOT_REACHED / 0 / R의 값 / null / null / 코드·문구 / 2.
- P7 후보 2개 이상(오류 결과 포함): PRECHECK_MULTIPLE_CANDIDATES 후 R / PASSED / NOT_REACHED / 후보 수 / R의 값 / null / null / 코드·문구 / 2.
- P8 후보 1개, format_selector가 None: PRECHECK_SELECTOR_UNREPRESENTABLE 후 R / PASSED / NOT_REACHED / 1 / R의 값 / null / null / 코드·문구 / 2.
- P9 후보 1개, 선택 경로(parse_selector, check_kind, select_text, extract, values)의 정의 실패(오류 결과면 TOOL_RESULT_ERROR): 그 코드 후 R / PASSED / FAILED / 1 / R의 값 / null / null / 코드·문구 / 2.
- P10 후보 1개, 선택 경로 중 시간 초과: TIME_LIMIT_EXCEEDED / PASSED / FAILED / 1 / INCOMPLETE(재해시 없음) / null / null / 코드·문구 / 2.
- P11 후보 1개, 선택 경로 성공, R이 (None, MATCHED): PRECHECK_OK / PASSED / PASSED / 1 / MATCHED / run 문법 문자열 / {sha256, bytes, lf} / null / 0.

R 재해시(P4, P6–P9, P11):
- Session.rehash(deadline)가 (None, MATCHED)를 반환하면 해당 행을 그대로 유지한다.
- (code, check)를 반환하면 다음으로 바꾼다: status=code, prefix_check=check, error=code의 DETAILS 문구, candidate_count=null, selector=null, values=null, exit_code=2. checks는 유지한다.
- 대체 code와 check 조합: SESSION_TRUNCATED/TRUNCATED, SESSION_CHANGED/CHANGED, SESSION_UNREADABLE/INCOMPLETE, TIME_LIMIT_EXCEEDED/INCOMPLETE, TIME_LIMIT_EXCEEDED/MATCHED.

P3 이후 handle은 finally에서 닫는다. 정의되지 않은 예외는 출력 없이 전파한다. 유일성 판정은 scan_candidates가 prefix 전체를 마친 뒤에만 한다.

D8 PRECHECK_DETAILS: 키는 DETAILS와 겹치지 않는다. 이 코드로 ControlledReadError를 만들지 않고 문서로 반환한다.
- PRECHECK_NO_CANDIDATE: "no text block of the profile's kinds holds a BEGIN or END marker line"
- PRECHECK_MULTIPLE_CANDIDATES: "more than one text block holds a BEGIN or END marker line"
- PRECHECK_SELECTOR_UNREPRESENTABLE: "the single candidate cannot be written in the run selector grammar"
그 밖의 코드는 DETAILS의 코드와 문구를 그대로 쓴다. STORE_PATH_INVALID, STORE_FAILED, ATTEMPT_EXISTS는 나오지 않는다.

D9 precheck/1 키(PRECHECK_KEYS, 모든 키가 항상 존재):
- schema: "moneylab.controlled_read.precheck/1"
- command: "precheck"
- status: str(D7)
- exit_code: int(bool 아님). PRECHECK_OK면 0, 나머지는 2
- task_id: str. P1에서만 null
- target: P1에서 null. 그 밖에는 {project_key: str, session_id: str, prefix_bytes: int 또는 null, prefix_sha256: 64hex 또는 null, line_count: int 또는 null, trailing_partial_bytes: int 또는 null, prefix_check: "MATCHED", "TRUNCATED", "CHANGED", "INCOMPLETE" 또는 null}. 측정 4개와 prefix_check는 P2·P3에서 함께 null이다.
- profile: {id: str, version: int}. P1에서 null
- checks: {scan, selected}, 각 값은 "PASSED", "FAILED", "NOT_REACHED". P1에서 null
- candidate_count: 0 이상의 int 또는 null
- selector: str 또는 null
- values: {sha256: 64hex, bytes: int, lf: int} 또는 null
- error: {code: str, detail: str} 또는 null
- authority: "NONE", approval: "NOT_VERIFIED_BY_PROGRAM", boundary: "DATA_NOT_INSTRUCTIONS"
attempt·record 키는 없다. 출력은 canonical_bytes 문서 1개와 LF이고 stderr는 비어 있다.

D10 의미 한계(docs/agent_workflow.md에 같은 뜻으로 적는다):
- checks.scan은 run이 요구하지 않는 추가 탐색 검사를 포함한다.
- PRECHECK_OK는 이후 RUN의 성공, prefix 동일성, 정본 여부를 보장하지 않는다.
- prefix_sha256은 관측값이고 run 인자가 아니다.
- precheck 결과는 정본 수락이나 RUN 승인을 대신하지 않는다.

D11 guard.py 변경 허용 범위(이 밖은 금지):
- (a) 상수 CONTROLLED_READ_PRECHECK_FORM 하나를 추가한다:
  `re.compile(_CR_EXE + r"precheck --task " + _CR_TASK + r" --project-key [A-Za-z0-9-]{1,200} --session " + _CR_SESSION + r" --profile (?:ECON-FWD-M20-WO/1|ECON-FWD-M20-PREREG/1)", re.ASCII)`
- (b) _controlled_read의 `if bash:` 블록 안, 기존 CONTROLLED_READ_FORMS 루프 뒤에 분기 하나를 추가한다. raw가 (a)에 fullmatch하고 len(m.group("task")) <= 64이면 `Decision(ASK, "controlled-read", "controlled read precheck; confirm the CONTROLLED_READ_PRECHECK_AUTHORIZATION message first")`를 반환한다.
- (c) 다음은 바꾸지 않는다: CONTROLLED_READ_FORMS(2개), run/status reason, 마지막 DENY 반환, _CR_MODULE, INLINE_CODE 조건, _CR_TASK·_CR_SESSION·_CR_ATTEMPT·_CR_EXE, 다른 모든 규칙과 함수. 다른 DENY 규칙은 완화하지 않는다.

D12 docs/agent_workflow.md 변경 허용 범위: 제한 읽기 CLI 절 안에서만 바꾼다.
- "두 형태"를 "세 형태"로 고치고 D1 형태를 추가한다.
- precheck는 기록을 만들지 않으며 status 대상이 아니라는 문장을 넣는다.
- D10 문장을 넣는다.
- 승인 문구를 추가한다(메시지 1건이 호출 1회를 승인한다):
  `CONTROLLED_READ_PRECHECK_AUTHORIZATION: AUTO-09-CONTROLLED-READ-PRECHECK TASK=<TASK_ID> PROJECT_KEY=<PROJECT_KEY> SESSION=<SESSION> PROFILE=<PROFILE> EXPIRES_UTC=<YYYY-MM-DDTHH:MM:SSZ>`
  에이전트는 원문의 존재, 필드 4개와 인자의 문자열 완전 일치, 만료를 확인하고, 하나라도 확인하지 못하면 멈춘다. 이 승인은 CONTROLLED_READ_AUTHORIZATION을 대신하지 않는다.
- 그 밖의 절은 바꾸지 않는다.

## WS_A (WORKSPACE_SETUP PART=WORKTREE, SETUP_SESSION_ROOT 세션, 각 명령은 독립 호출)

WS-A1 사전 조건. 하나라도 기대와 다르면 STOP한다.
- `git -C C:/MoneyLab-auto-08 rev-parse --show-toplevel` → C:/MoneyLab-auto-08
- `git -C C:/MoneyLab-auto-08 status --porcelain=v1` → 빈 출력
- `git -C C:/MoneyLab-auto-08 ls-remote origin refs/heads/main` → d471d644279ed8b2fe861a23dedca7765c5511ac
- `git -C C:/MoneyLab-auto-08 ls-remote origin refs/heads/codex/auto-09-controlled-read-precheck` → 빈 출력
- `git -C C:/MoneyLab-auto-08 rev-parse d471d644279ed8b2fe861a23dedca7765c5511ac^{tree}` → 31b2a776c5d341dcba311a0c2d1fd318aa7a5928
- `git -C C:/MoneyLab-auto-08 show-ref --verify --quiet refs/heads/codex/auto-09-controlled-read-precheck` → 종료 코드 1
- `test -e C:/MoneyLab-auto-09` → 종료 코드 1

WS-A2 디렉터리 P를 만든다. RECORD_OUTPUTS의 디렉터리 규칙을 적용하고, check-ignore 기준 worktree는 C:/MoneyLab-auto-08이다.

WS-A3 기록(각 파일 `test -e` → 1 확인 후):
- `set -C && git -C C:/MoneyLab-auto-08 worktree list --porcelain > C:/MoneyLab-auto-08/data/processed/auto09_pre/pre_worktrees.txt`
- `set -C && git -C C:/MoneyLab-auto-08 for-each-ref "--format=%(objectname) %(refname)" refs/heads refs/remotes refs/tags > C:/MoneyLab-auto-08/data/processed/auto09_pre/pre_refs.txt`
- `sha256sum C:/MoneyLab-auto-08/data/processed/auto09_pre/pre_worktrees.txt C:/MoneyLab-auto-08/data/processed/auto09_pre/pre_refs.txt`

WS-A4 `git -C C:/MoneyLab-auto-08 worktree add -b codex/auto-09-controlled-read-precheck C:/MoneyLab-auto-09 d471d644279ed8b2fe861a23dedca7765c5511ac`

WS-A5 확인:
- `git -C C:/MoneyLab-auto-09 rev-parse HEAD` → d471d644279ed8b2fe861a23dedca7765c5511ac
- `git -C C:/MoneyLab-auto-09 status --porcelain=v1` → 빈 출력
- `git -C C:/MoneyLab-auto-09 check-ignore -q .venv/x` → 종료 코드 0

WS-A6 AUTO-09 전용 venv(오프라인). 실패하면 STOP하고, 인터프리터를 바꾸거나 재시도하지 않는다.
- E1 `C:/MoneyLab/.venv/Scripts/python.exe -m venv C:/MoneyLab-auto-09/.venv`
- E2 `C:/MoneyLab-auto-09/.venv/Scripts/python.exe --version` → "Python 3.14."로 시작해야 한다(진입 조건). 정확한 값은 기록만 한다.
- `git -C C:/MoneyLab-auto-09 status --porcelain=v1` → 빈 출력

WS-A7 보고 후 이 세션은 AUTO-09 작업을 끝낸다. 의존성 설치, C1, 나머지 준비는 하지 않는다. SESSION_ROOT 세션은 WS-A6 통과 뒤에만 시작한다.

## WS_B (WORKSPACE_SETUP PART=C1_ENV, C:/MoneyLab-auto-09에서 새로 시작한 세션, 각 명령은 독립 호출)

WS-B1 진입 확인. 각 명령을 독립 호출로 실행하고, hook 오류나 차단이 있으면 STOP한다.
- `pwd` → /c/MoneyLab-auto-09
- `git status --porcelain=v1` → 빈 출력
- `git rev-parse HEAD` → d471d644279ed8b2fe861a23dedca7765c5511ac
- `git rev-parse --abbrev-ref HEAD` → codex/auto-09-controlled-read-precheck
- `.venv/Scripts/python.exe --version` → WS-A6 E2와 같은 값

WS-B2 의존성 설치(N2). 실패하면 STOP하고, 인터프리터를 바꾸거나 재시도하지 않는다.
- E3 `.venv/Scripts/python.exe -m pip install --no-binary=mypy --no-cache-dir -r requirements-dev.txt`
- E4 `.venv/Scripts/python.exe -m pip install -e . --no-deps`
- E5 `.venv/Scripts/python.exe -m pip check` → 종료 코드 0
- E6 `.venv/Scripts/python.exe -m mypy --version` → 종료 코드 0, `mypy 2.4.0 (compiled: no)`를 확인한다. DLL·import 오류는 STOP하며 보안 설정을 바꾸지 않는다.
- `git status --porcelain=v1` → 빈 출력

WS-B3 검사 스크립트(F7):
- 디렉터리 C:/MoneyLab-auto-09/data/processed/auto09/tools를 RECORD_OUTPUTS의 디렉터리 규칙으로 만든다(check-ignore 기준 worktree는 C:/MoneyLab-auto-09).
- `test -e data/processed/auto09/tools/bytes_check.py` → 종료 코드 1
- Write 도구로 BYTES_SCRIPT 내용을 그대로 작성한다.
- `sha256sum data/processed/auto09/tools/bytes_check.py` → BYTES_SCRIPT_SHA256. 다르면 STOP한다.

WS-B4 C1(보호 경로 최초 작성 예외. cp·셸 리디렉션은 쓰지 않는다):
- `sha256sum <WO_SOURCE>` → WO_SHA256
- `test -e docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md` → 종료 코드 1
- Read 도구로 WO_SOURCE 전체를 읽고, Write 도구로 docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md에 같은 내용을 최초 작성한다.
- `.venv/Scripts/python.exe -I -B data/processed/auto09/tools/bytes_check.py docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md` → 종료 코드 0이고 W = S = WO_SHA256
- `git add -- docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md`
- `git diff --cached --name-only` → 그 경로 1개
- `git cat-file blob :docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md | sha256sum` → WO_SHA256
- `git diff --cached --check` → 빈 출력, 종료 코드 0
- `git commit -m "docs(task): add AUTO-09-CONTROLLED-READ-PRECHECK work order" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`
- `git cat-file blob HEAD:docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md | sha256sum` → WO_SHA256
- `git rev-parse HEAD^` → d471d644279ed8b2fe861a23dedca7765c5511ac
- `git diff-tree --no-commit-id --name-only -r HEAD` → 1개
- `git status --porcelain=v1` → 빈 출력

WS-B5 기준 기록:
- 디렉터리 B를 RECORD_OUTPUTS의 디렉터리 규칙으로 만든다.
- E7 `set -C && git status --porcelain=v1 --ignored=traditional --untracked-files=normal > data/processed/auto09/baseline/post_env_status.txt`
- E8 `set -C && .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q > data/processed/auto09/baseline/collect_base.txt` → 종료 코드 0
- E9 `set -C && .venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache src/moneylab/controlled_read > data/processed/auto09/baseline/mypy_cr_base.txt` → 종료 코드 0이고 "Success:"로 시작하는 줄이 있어야 한다. 아니면 STOP한다.
- `sha256sum data/processed/auto09/baseline/post_env_status.txt data/processed/auto09/baseline/collect_base.txt data/processed/auto09/baseline/mypy_cr_base.txt`

## IMPL_CHECKS

IMPL_CHECKS (IMPLEMENTATION, SESSION_ROOT 세션):
- C1 `.venv/Scripts/python.exe -m ruff check --no-cache --select E4,E7,E9,F src tests` → 종료 코드 0
- C2 `.venv/Scripts/python.exe -m ruff check --no-cache --select E4,E7,E9,F .claude/hooks/guard.py tests/test_agent_guard.py` → 종료 코드 0
- C3 `.venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache` → 종료 코드 0
- C4 `.venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache src/moneylab/controlled_read` → 종료 코드 0
- C5 `.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/test_controlled_read_precheck.py tests/test_agent_guard.py tests/test_controlled_read_cli.py tests/test_controlled_read_selector.py tests/test_controlled_read_transcript.py tests/test_controlled_read_profiles.py tests/test_controlled_read_store.py tests/test_controlled_read_isolation.py` → failed 0 / errors 0
- C6 `.venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q` → failed 0 / errors 0
- C7 `git diff --check` → 빈 출력. `git status --porcelain=v1` → ALLOWED_FILES만
- guard.py 편집은 GUARD_SESSION_NOTICE 절차를 따른다.

## FIX_RULES

- 수정 가능(IMPLEMENTATION 안에서만, BUDGET_FIX와 BUDGET_SAME_FAIL 안에서): ALLOWED_FILES 안에서 생긴 ruff 진단(C1·C2), C4 mypy 오류, 신규 시험 실패, tests/test_agent_guard.py 신규 시험 함수의 실패, FILE_FORMAT 위반. ALLOWED_FILES만 고치고 같은 검사 명령으로 다시 확인한다.
- 즉시 STOP:
  - ALLOWED_FILES 밖 파일의 ruff·mypy 진단, C3 실패
  - 기존 시험(PROTECTED 시험 6개와 tests/test_agent_guard.py의 기존 함수) 실패
  - 진단 없이 끝난 도구 비정상 종료, crash, timeout, DLL·import 오류, 환경 불일치
  - COMMIT 이후의 모든 실패
- 도구 오류 뒤에는 어떤 명령도 다시 실행하지 않는다. STOP하고 보고한 뒤 별도 승인을 기다린다.
- 예산 적용:
  - BUDGET_FIX(수정 반복), BUDGET_PYTEST(C6), BUDGET_TARGETED(C5)는 각 한도 횟수까지 수행할 수 있다. 마지막 허용 시도에서 성공하면 다음 gate로 진행할 수 있다.
  - 한도를 넘는 시도가 필요하거나, 한도를 다 쓴 뒤에도 추가 수정·검사가 필요하면 STOP한다.
  - 같은 실패가 BUDGET_SAME_FAIL(2)회 연속되면 남은 한도와 관계없이 STOP한다.
  - 시간: BUDGET_TIME_SECONDS는 각 gate의 Gate Authorization을 받은 시각부터 그 gate 보고를 마친 시각까지의 경과 시간을 모든 gate에 걸쳐 합한 값이다. gate 사이의 대기와 ASK·권한 창에서 사용자 응답을 기다린 시간은 넣지 않는다.

## TEST_GATES

TEST_GATES (tests/test_controlled_read_precheck.py 신규, 합성 tmp_path만):
- 경로: D7의 P1–P11과 R의 다섯 대체 조합을 각각 1건 이상 다룬다. 각 건에서 D9의 모든 키 값을 단정한다.
- 후보:
  - assistant 단일, tool_result 단일
  - 같은 entry의 두 text block(MULTIPLE), assistant와 tool_result 동시(MULTIPLE)
  - BEGIN만 있는 블록과 완전한 블록(MULTIPLE)
  - 유일 오류 결과(TOOL_RESULT_ERROR, P9), 표식 없는 오류 결과(비후보), 오류 결과를 포함한 복수(MULTIPLE)
  - uuid 없음, tool_use_id 문법 밖, k=100(UNREPRESENTABLE)
  - 다른 type entry의 같은 uuid(ENTRY_DUPLICATE, P9)
- 스캔: 비후보 entry의 미지원 블록(FORMAT_UNSUPPORTED, P4), SESSION_CORRUPT, LINE·ENTRY 한도. 마지막 줄에 두 번째 후보를 두어 전체 스캔 뒤에만 판정하는지 확인한다.
- 재해시와 시간: transcript._before_rehash seam으로 R 대체 조합을, transcript._monotonic seam으로 P5·P10을 재현한다.
- 누출과 쓰기: sentinel 문자열이 stdout·stderr에 없다. 호출 전후 tmp_path 파일 목록이 같다. data/processed/controlled_read가 생기지 않는다.
- run 연결(합성): P11의 selector로 같은 합성 세션에 run을 실행하면 SUCCEEDED이고 values가 같다.
- 분리: set(store.PRECHECK_DETAILS).isdisjoint(DETAILS). 각 PRECHECK 코드로 ControlledReadError를 만들면 ValueError. 모든 경로의 precheck 문서에 store.valid_result가 False. ERROR_CODES == tuple(DETAILS).
- 동치: _tool_result_texts의 분리 전후 동작이 같다. is_error true·false·비bool, content str·list·불량 각 입력의 결과와 예외를 비교한다.
- tests/test_agent_guard.py: 새 시험 함수만 추가하고 기존 함수는 바꾸지 않는다.
  - ASK: precheck 정확 형태 → ("ask", "controlled-read")와 precheck reason
  - DENY: -B 누락, `-mmoneylab`, --selector 추가, --attempt 추가, 옵션 순서 변경, 추가 토큰, 미등록 PROFILE, `;` 결합, PowerShell 도구, task 65자 → ("deny", "controlled-read-form")
  - run_hook 프로세스: ASK 1건, DENY exit 2 1건

## DIFF_RULES

- diff는 독립 호출 `diff <앞> <뒤>`로 실행한다. 리디렉션, 파이프, `;`, `&&`, `||`를 붙이지 않고, 원래 출력과 실제 종료 코드를 그대로 확인한다. 출력을 버리거나 실패를 숨기는 연결은 쓰지 않는다.
- diff 종료 코드: 0 = 같음. 1 = 차이 보고이며 아래 허용 규칙으로 판정한다. 2 이상 = 도구 오류이며 STOP한다.
- 상태 비교(B1 대 B5, B5 대 B6)에서 종료 코드가 1이면 diff 출력 전체를 그대로 보고 변경 줄을 하나씩 판정한다.
  - 감소 금지: `<`로 시작하는 줄(앞에만 있는 줄)이 하나라도 있으면 STOP한다.
  - 허용 추가: `>` 줄은 `> !! .venv/`, `> !! data/`, `> !! data/processed/`로 시작하는 줄과, `> !! src/` 또는 `> !! tests/`로 시작하고 `__pycache__/`로 끝나는 줄만 허용한다. 그 밖의 `>` 줄이 하나라도 있으면 STOP한다.
- 보존 비교(P1 대 B7, P2 대 B8): 같은 방식으로 독립 호출하고, PRESERVATION_CHECK의 허용 차이만 인정한다.
- 수집 ID 비교는 AUDIT_CHECKS의 COLLECT_COMPARE를 따른다.

## AUDIT_CHECKS

AUDIT_CHECKS (PRECOMMIT_AUDIT, 읽기 전용, B4 생성만 예외):
- `git status --porcelain=v1`의 변경 집합 = ALLOWED_FILES
- `git diff --stat d471d644279ed8b2fe861a23dedca7765c5511ac -- src/moneylab/controlled_read/__init__.py tests/test_controlled_read_cli.py tests/test_controlled_read_selector.py tests/test_controlled_read_transcript.py tests/test_controlled_read_profiles.py tests/test_controlled_read_store.py tests/test_controlled_read_isolation.py CLAUDE.md pyproject.toml requirements.txt requirements-dev.txt .gitattributes .gitignore .github configs docs/tasks/AUTO-08-CONTROLLED-READ` → 빈 출력
- `git diff --stat d471d644279ed8b2fe861a23dedca7765c5511ac -- .claude` → .claude/hooks/guard.py만
- `set -C && .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider --collect-only -q > data/processed/auto09/baseline/collect_precommit.txt` → 종료 코드 0
- 수집 ID 비교(COLLECT_COMPARE): B2 collect_base.txt와 B4 collect_precommit.txt 두 파일만 읽어 Python 메모리 안에서 비교한다. 프로그램 원문은 PRECOMMIT_AUDIT Gate Authorization에서 확정한다.
  - 두 파일을 UTF-8 strict로 읽는다. 프로그램은 파일·캐시를 쓰지 않는다. 읽기·디코딩·파싱 오류는 성공으로 바꾸지 않고 STOP한다.
  - 각 파일에서 먼저 세 가지가 일관되는지 검증한다: 수집 성공(오류·중단 표시 없음), 요약 줄의 수집 개수, 추출한 node ID 개수. 파싱이 모호하거나 개수가 맞지 않으면 STOP한다.
  - node ID는 매개변수 부분과 공백을 포함한 전체 문자열 그대로 비교한다.
  - 통과 조건: 기준 ID 가운데 현재 집합에서 사라진 ID가 0개.
  - 보고: 사라진 ID(있으면), 추가된 ID, 파일별 ID 개수.
  - 셸 파이프, process substitution, 출력 폐기로 대체하지 않는다.
- `git diff -- tests/`에 skip, skipif, xfail, `pytest.skip(`, `pytest.xfail(` 추가가 없고, 기존 시험 함수의 변경·삭제가 없다. 단정 의미 완화와 mock 우회 여부는 "독립 검토 필요"로 보고하고 PASS로 단정하지 않는다.
- guard.py diff가 D11 (a)(b) 밖을 건드리지 않고, agent_workflow.md diff가 D12 범위 안이다.
- `.venv/Scripts/python.exe -I -B data/processed/auto09/tools/bytes_check.py src/moneylab/controlled_read/__main__.py src/moneylab/controlled_read/selector.py src/moneylab/controlled_read/transcript.py src/moneylab/controlled_read/profiles.py src/moneylab/controlled_read/store.py .claude/hooks/guard.py docs/agent_workflow.md tests/test_agent_guard.py tests/test_controlled_read_precheck.py` → 종료 코드 0. 출력한 파일별 W와 S를 감사값으로 확정해 보고한다.

## COMMIT_STEPS

COMMIT_STEPS:
- AUDIT_CHECKS의 bytes_check 명령을 다시 실행해 종료 코드 0이고 9개 파일의 W와 S가 감사값과 같은지 확인한다. 다르면 STOP한다.
- `git add -- src/moneylab/controlled_read/__main__.py src/moneylab/controlled_read/selector.py src/moneylab/controlled_read/transcript.py src/moneylab/controlled_read/profiles.py src/moneylab/controlled_read/store.py .claude/hooks/guard.py docs/agent_workflow.md tests/test_agent_guard.py tests/test_controlled_read_precheck.py`
- `git diff --cached --name-only` → 위 9개
- 9개 파일마다 `git cat-file blob :<path> | sha256sum` → 감사 S
- `git diff --cached --check` → 빈 출력, 종료 코드 0
- `git commit -m "feat(automation): add controlled_read precheck" -m "AUTO-09-CONTROLLED-READ-PRECHECK: precheck returns one run selector from a single-candidate prefix scan; exact precheck form is guard ASK." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`
- `git rev-parse HEAD^` → C1
- `git diff-tree --no-commit-id --name-only -r HEAD` → 9개
- 9개 파일마다 `git cat-file blob HEAD:<path> | sha256sum` → 감사 S
- `git status --porcelain=v1` → 빈 출력

## E2E_GATES

E2E_GATES (CLEAN_COMMIT_E2E: 커밋된 코드의 targeted pytest 1회, 전체 pytest 예산과 별도):
- HEAD = 구현 커밋, `git status --porcelain=v1` → 빈 출력
- `set -C && git status --porcelain=v1 --ignored=traditional --untracked-files=normal > data/processed/auto09/baseline/e2e_status_before.txt`
- B1 대 B5를 DIFF_RULES의 상태 비교로 판정한다. 위반이면 STOP한다.
- IMPL_CHECKS C5 명령 1회 → failed 0 / errors 0. 실패하면 STOP한다.
- `set -C && git status --porcelain=v1 --ignored=traditional --untracked-files=normal > data/processed/auto09/baseline/e2e_status_after.txt`
- B5 대 B6을 DIFF_RULES의 상태 비교로 판정하고, HEAD와 tree가 그대로인지 확인한다.
- 실제 home 대상 precheck·run 실행은 하지 않는다.

## CI_CRITERIA

CI_CRITERIA (PR_CI):
- 필수: PR head의 Windows job `pytest`가 success여야 한다.
- Linux job `pytest-linux-experimental`:
  - 기준 증거: base merge commit d471d644279ed8b2fe861a23dedca7765c5511ac에는 CI 실행이 없을 수 있다. 그래서 기존에 확인한 AUTO-08 승인 head 64faf1c55e3e611e860e49fffc7358f59ea40c6c의 CI run 45616533199를 Linux 기준으로 쓴다. 이 Work Order는 그 run을 새로 조회했다고 주장하지 않는다.
  - F_base: PR_CI에서 `gh run view 45616533199 -R swk3169/MoneyLab --log-failed`의 Linux job "FAILED " 시험 ID 집합.
  - F_pr: PR head run에서 같은 방법으로 모은 Linux job 실패 ID 집합.
  - F_base가 기존 wrapper 실패 2건이 아니거나 조회에 실패하면 STOP하고 보고한다.
  - F_pr ⊆ F_base이면 non-blocking이다. F_pr에 F_base 밖의 ID가 있으면 신규 회귀로 보고 STOP한다.
- CI 수동 실행과 재실행은 하지 않는다.

## PRESERVATION_CHECK

PRESERVATION_CHECK (COMPLETE, POST_MERGE_AUDIT 뒤):
- 각 파일 `test -e` → 1 확인 후:
  - `set -C && git worktree list --porcelain > data/processed/auto09/baseline/complete_worktrees.txt`
  - `set -C && git for-each-ref "--format=%(objectname) %(refname)" refs/heads refs/remotes refs/tags > data/processed/auto09/baseline/complete_refs.txt`
- `diff C:/MoneyLab-auto-08/data/processed/auto09_pre/pre_worktrees.txt data/processed/auto09/baseline/complete_worktrees.txt`: 허용 차이는 worktree C:/MoneyLab-auto-09(branch refs/heads/codex/auto-09-controlled-read-precheck) 블록의 추가뿐이다.
- `diff C:/MoneyLab-auto-08/data/processed/auto09_pre/pre_refs.txt data/processed/auto09/baseline/complete_refs.txt`: 허용 차이는 다음뿐이다.
  - refs/heads/codex/auto-09-controlled-read-precheck 추가
  - refs/remotes/origin/codex/auto-09-controlled-read-precheck 추가
  - refs/remotes/origin/main 값이 POST_MERGE_AUDIT에서 검증한 merge commit으로 바뀜
- 다음 파일을 `sha256sum`으로 다시 계산해 생성 때 보고한 값과 같은지 확인한다: P1, P2, B1–B6, bytes_check.py.
- 불일치 처리: 허용 밖의 차이나 해시 불일치가 있으면 COMPLETE_PASS = NO로 STOP한다. 차이 줄(ref 이름, SHA, worktree 경로)만 보고하고, 복원·삭제·되돌리기는 하지 않는다. 처리는 사용자가 결정한다.
- 보존 확인을 위해 다른 worktree의 파일 목록이나 내용, 세션, 연구 데이터를 읽지 않는다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base SHA·tree, C1 SHA·parent·tree, WORK_ORDER.md의 작업·index·commit sha256, 구현 커밋 SHA·parent·tree, 커밋 파일 집합과 S, PR head, merge commit parent1·parent2·tree
- CLAUDE_REPORTED: WS_A·WS_B 결과, 기록 10개와 bytes_check.py의 sha256, ruff·mypy·pytest·E2E 결과, 수집 ID 비교, PRESERVATION_CHECK 결과
- INDEPENDENT: PR CI `pytest`, GitHub 화면(사용자 확인)

## REQUIRED_REPORT

REQUIRED_REPORT (매 단계, 채팅으로):
- 공통: TASK_ID, GATE(PART 포함), 세션 루트, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, HEAD·parent·tree, 변경 파일 집합, PROTECTED diff 결과, worktree clean 여부, diff --check 결과, 생성한 기록·스크립트 파일과 sha256, 사용 예산(시간·FIX·전체 pytest·targeted·SAME_FAIL), 값별 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES, <GATE>_PASS = YES 또는 NO, READY_FOR_<NEXT> = YES 또는 NO
- PART=WORKTREE: WS-A1 결과, P1·P2 sha256, 새 worktree HEAD와 clean 여부, E2 Python 버전
- PART=C1_ENV: WS-B1 결과, E5·E6 결과, bytes_check.py sha256, C1 검증 값, B1–B3 sha256
- IMPLEMENTATION: C1–C7 결과, guard 편집 단위별 읽기 확인 결과, 수정 횟수와 원인
- PRECOMMIT_AUDIT: AUDIT_CHECKS 전 항목, 파일별 W·S, B4 sha256
- COMMIT: 파일별 index·commit sha256과 감사 S의 대조
- CLEAN_COMMIT_E2E: B5·B6 sha256, 두 상태 비교 결과, targeted 결과
- PUSH: 원격 ref SHA
- PR_CI: PR 번호, head SHA, `pytest` 결과, F_base·F_pr
- MERGE: merge commit SHA
- POST_MERGE_AUDIT: docs/tasks/README.md §3 항목
- COMPLETE: PRESERVATION_CHECK 결과, B7·B8 sha256

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree가 기대값과 다름, WORK_ORDER.md의 작업·index·commit sha256이 WO_SHA256과 다름, WS-A1 조건 불일치
- 세션 루트가 해당 단계의 지정 루트와 다름, WS-B1 진입 확인 실패, WS-A6 전에 SESSION_ROOT 세션을 시작함
- ALLOWED_FILES 밖 tracked 변경, PROTECTED 변경(WS-B4 예외 제외), FILE_CREATION 분류 밖 파일 생성, 기록·스크립트 덮어쓰기 시도, A/M 표기와 base 상태 불일치, 예상 밖 untracked 파일
- bytes_check.py sha256 ≠ BYTES_SCRIPT_SHA256, BYTES_SCRIPT 종료 코드가 0이나 3이 아님
- PROTECTED 시험이나 기존 인코딩 검사 시험의 수정이 필요해짐
- DETAILS·ERROR_CODES·valid_result 허용 범위의 변화, D11·D12 밖의 guard·문서 변경 필요
- FIX_RULES의 즉시 STOP 항목, BUDGET_FIX·BUDGET_SAME_FAIL·BUDGET_PYTEST·BUDGET_TARGETED·BUDGET_TIME_SECONDS 도달
- E2가 3.14.x가 아님, E1·E3–E6·E8·E9 실패
- W·S·index·commit 해시 불일치, BYTES_SCRIPT의 CR_REMAINS
- DIFF_RULES 위반, diff·grep 도구 오류(종료 코드 2 이상), COLLECT_COMPARE 실패·STOP 판정, CI_CRITERIA 위반, PRESERVATION_CHECK 불일치
- guard DENY, hook 오류, 권한 창 거절·무응답, EXPECTED_ASK 밖 ASK
- NETWORK 밖 접근 필요, 실제 home·세션 경로 접근 필요
- 새로 발견된 계약 모순, 상위 규칙과 충돌
- 공통 처리: 모든 STOP에서 재실행, 변형 재시도, 되돌리기를 하지 않는다. 분류, 마지막 PASS 단계, 실제 HEAD·tree를 보고하고 별도 승인을 기다린다.

## DELEGATION

DELEGATION_SCHEMA: moneylab.delegation/1
LEDGER_TASK_ID: AUTO-09-CONTROLLED-READ-PRECHECK
BUDGET_TIME_SECONDS: 10800
BUDGET_FIX: 4
BUDGET_PYTEST: 3
BUDGET_TARGETED: 6
BUDGET_SAME_FAIL: 2
BUDGET_NOTE: BUDGET_PYTEST는 IMPL_CHECKS C6(로컬 전체 pytest)의 총 횟수다. E8·B4 수집, C5 targeted(BUDGET_TARGETED로 따로 센다), E2E targeted 1회는 포함하지 않는다. AUTO-08 예산과 합산하지 않는다.
REQUIRED_CI: pytest
PR_TITLE: feat(automation): add controlled_read precheck
SETUP_COMMAND_1: C:/MoneyLab/.venv/Scripts/python.exe -m venv C:/MoneyLab-auto-09/.venv  (WS-A6 E1, SETUP_SESSION_ROOT 세션)
SETUP_COMMAND_2: .venv/Scripts/python.exe -m pip install --no-binary=mypy --no-cache-dir -r requirements-dev.txt  (WS-B2 E3, SESSION_ROOT 세션)
SETUP_COMMAND_3: .venv/Scripts/python.exe -m pip install -e . --no-deps  (WS-B2 E4, SESSION_ROOT 세션)
CHECK_COMMAND_1: .venv/Scripts/python.exe -m ruff check --no-cache --select E4,E7,E9,F src tests
CHECK_COMMAND_2: .venv/Scripts/python.exe -m ruff check --no-cache --select E4,E7,E9,F .claude/hooks/guard.py tests/test_agent_guard.py
CHECK_COMMAND_3: .venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache
CHECK_COMMAND_4: .venv/Scripts/python.exe -m mypy --cache-dir .venv/.mypy_cache src/moneylab/controlled_read
CHECK_COMMAND_5: .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q tests/test_controlled_read_precheck.py tests/test_agent_guard.py tests/test_controlled_read_cli.py tests/test_controlled_read_selector.py tests/test_controlled_read_transcript.py tests/test_controlled_read_profiles.py tests/test_controlled_read_store.py tests/test_controlled_read_isolation.py
CHECK_COMMAND_6: .venv/Scripts/python.exe -B -m pytest -p no:cacheprovider -q
CHECK_NOTE: CHECK_COMMAND_1–6은 IMPL_CHECKS C1–C6과 같은 명령이며 SESSION_ROOT C:/MoneyLab-auto-09를 작업 디렉터리로 실행한다.

## AFTER_COMPLETE

AFTER_COMPLETE (이 task 밖, 참고용): AUTO-09가 COMPLETE된 뒤 FIRST-USE는 다음 순서로 진행한다.
1. FIRST-USE 계약 수락, hook 확인, CONTROLLED_READ_PRECHECK_AUTHORIZATION 1건
2. PRECHECK 1회
3. 형식 결과 수락
4. 별도 CONTROLLED_READ_AUTHORIZATION으로 RUN
PRECHECK 전에 실제 형식 확인 완료를 요구하지 않는다. 실제 세션 식별값은 채팅 승인에만 쓰고 이 문서에는 넣지 않는다.
