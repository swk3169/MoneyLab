# Work Order: GUARD-GH-01 — GitHub CLI guard normalization and published-body payload separation

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/GUARD-GH-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

IMPLEMENTATION은 TARGET_WORKTREE를 root로 하는 새 Claude Code session에서 진행한다. 그 session은 이전 대화의 맥락과 auto-memory를 받지 못한다. 이 파일이 계약의 유일한 출처다. 대화 기억에 의존하지 않는다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: GUARD-GH-01
TASK_ID: GUARD-GH-01
TITLE: GitHub CLI guard normalization and published-body payload separation
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 3f0880b943122a2fd51b84566e9bbddd23057322
CANONICAL_BASE_TREE: 45e434ec4c048a04ed7b3c60ff0733a6061baf5e
TARGET_BRANCH: chore/guard-gh-cli
TARGET_WORKTREE: C:/MoneyLab-guard-gh-cli
WORKSPACE_SETUP: REQUIRED (완료 시 이 파일이 C1)
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (CREATE_MERGE_COMMIT; squash/rebase merge 금지: 계약 커밋이 구현보다 먼저인 이력을 보존)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

DESIGN_INVESTIGATION과 CONTRACT_REVIEW(사용자 결정 1~4 포함)는 이 파일 발행 전에 대화로 완료했다(BASE@3f0880b, CONTRACT_REVIEW_PASS = YES, BLOCKING_UNRESOLVED = NONE).

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: GUARD-GH-01 <GATE> WO@<commit>`)
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping
- Gate Authorization은 파일 수정이 아니다. 이전 gate의 승인이나 이 파일이 다음 gate의 승인을 대신하지 않는다.

## PRIORITY

1. safety / system / tool restrictions
2. repository absolute rules: CLAUDE.md, .claude guard/hook/settings, docs/agent_workflow.md
3. frozen / preregistered contracts
4. 이 Work Order와 ACCEPTED ERRATA
5. implementation judgment

충돌하면 상위 규칙을 따르고 STOP/REPORT 한다. 이 task는 guard 자체를 고치지만, 고치는 동안에도 실행 중인 guard의 판정(deny/ask)을 따른다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 위 PRIORITY 1-3의 저장소 규칙을 참조한다(복제하지 않는다). 이 Work Order는 그 규칙을 바꾸지 않는다.

## SCOPE_STATEMENT

SCOPE_STATEMENT:
- `.claude/hooks/guard.py`의 명령 분류만 고친다. 대상은 (1) GitHub CLI 실행 파일 표기 정규화, (2) gh 게시 본문 stdin payload의 좁은 분리다.
- 테스트는 in-process 분류 테스트만 쓴다. 실제 `gh` 실행, 네트워크, GitHub mutation이 필요 없다.
- 실데이터, 외부 시장 API, 주문, Monte Carlo와 무관하다. 사전등록·config·research·src를 바꾸지 않는다.

## GOAL

GOAL: (1) `gh`, `gh.exe`, 절대 경로 `gh.exe`가 모두 같은 GitHub CLI 정책(`github` rule)으로 분류되게 하고, (2) gh `pr`/`issue` `create`/`edit`/`comment`의 인용 heredoc 본문(`--body-file -` 또는 `-F -`)을 실행 의도가 아닌 게시 텍스트로 분리해 `record-live` 같은 무관한 규칙의 오탐을 없애되, 게시 본문에는 기존 `env`/`trading` secret 정책을 계속 적용한다. 그 밖의 guard 동작은 바꾸지 않는다.

## BACKGROUND

BACKGROUND:
- 결함 1 (오탐): `gh pr create ... --body-file - <<'EOF'` 본문이 명령 텍스트로 검사되어, 본문 산문의 "record"와 경로의 "MoneyLab" 때문에 `_moneylab`이 ASK `record-live`를 반환했다. `normalize()`는 heredoc을 `git commit`으로 시작하는 명령에서만 제거한다(`guard.py:111-112`).
- 결함 2 (coverage gap): `normalize()`의 실행 파일 축약(`guard.py:118-119`)에 `gh`가 없어 `"/c/Program Files/GitHub CLI/gh.exe" pr create`가 `github` rule(`\bgh\s+…`, `guard.py:186`)에 매치되지 않았다. 본문에 "record"가 없었다면 guard 확인 없이 실행될 수 있었다.
- `.claude/settings.json`의 `Bash(gh pr *)` 권한 규칙도 전체 경로 표기와 매치되지 않는다(D9, 범위 밖).
- 현재 검사 순서(`guard.py:230-254`): branch -D(원본) → `normalize` → DENY_RULES → PROTECTED/MUTATE → DELETE_MOVE+raw/locked → ASK_RULES → INLINE_CODE → untracked script → `_moneylab`.

## SOURCE_OF_TRUTH

SOURCE_OF_TRUTH (canonical 3f0880b):
- .claude/hooks/guard.py
- tests/test_agent_guard.py
- tests/test_skills.py (`guard_rule_names`, `test_workflow_doc_lists_every_guard_rule`; 수정 금지, 실행만)
- docs/agent_workflow.md 4절
- .claude/settings.json (읽기만, 수정 금지)

BASE_FILE_IDENTITY (ALLOWED_FILES의 base 상태; 이 저장소는 core.autocrlf=true라 checkout된 파일의 sha256은 blob 바이트의 sha256과 다를 수 있다. 정체성 확인은 `git hash-object <path>` = blob id로 한다):
- .claude/hooks/guard.py: blob 9a72e36d8d27f6654d053e852dc5f92ba1a02847, blob-bytes sha256 ad7edb2b43db30fc04da51de0cda29d069fcd7878ecdaf65462537a991da4b9c, WORKSPACE_SETUP checkout sha256 d1e2d95847664ff6459ae28fbaf54a1f265dcc1c33b741de78ef7e988bebef01
- tests/test_agent_guard.py: blob b6ffe0005efcdd7a9b12a20e3b9f7710c3e97933, blob-bytes sha256 1155ac4f27e1f79a2d7e235a898a3061b3eccd8f7699691faaf386473c1c4d9f, WORKSPACE_SETUP checkout sha256 44d5d851fbc635f8bb37fe6ad8f42182a83cdb339516e6f603ea437f0f1b4580
- docs/agent_workflow.md: blob 256a96d0db01367f2809be5819979fc4c5b92849, blob-bytes sha256 2a974ee83b16b51364b3da9f90d6584a0167985ccbcbf07613996fd9097fd96a, WORKSPACE_SETUP checkout sha256 cb813eba51dbfb9af2347f8fde4da90d7261bf4f369faa3b8c6b44cab2eca432

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP (기존 session, root C:/MoneyLab): origin/main = base 확인(`git ls-remote`, fetch 없음), TARGET_BRANCH/TARGET_WORKTREE 생성(base 3f0880b), TARGET_WORKTREE에 ignored `.venv` junction(→ C:/MoneyLab/.venv) 하나 생성(tracked 아님, stage·커밋 금지), 이 파일 하나 최초 생성, `git add -- docs/tasks/GUARD-GH-01/WORK_ORDER.md`, C1 commit 하나, 감사
- IMPLEMENTATION (새 session, root C:/MoneyLab-guard-gh-cli): IMPLEMENTATION_SAFETY_CONDITIONS를 지키며 ALLOWED_FILES 3개만 수정, TEST_GATES 실행
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, commit 하나(Ci)
- CLEAN_COMMIT_E2E: E2E_GATES 실행
- PUSH: TARGET_BRANCH 하나만 `git push -u origin chore/guard-gh-cli`
- PR_CI: PR 하나 생성(별도 승인 시), CI 확인
- MERGE: 사용자 결정, MERGE_METHOD
- POST_MERGE_AUDIT: `git fetch origin main`만, 구조 감사
- COMPLETE: 최종 보고(채팅)

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 현재 승인된 gate 밖의 행위
- ALLOWED_FILES 밖의 tracked 변경, PROTECTED_FILES 변경
- 이 Work Order 또는 ERRATA 수정
- `git add .`, `git add -A`, `git add -u`, `git commit -a`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull
- `.claude/settings.json` 변경, hook/guard 비활성화, `disableAllHooks` 등 hook 끄기
- 경로 숨기기(변수·문자열 조립·인코딩), `git apply`/patch 파일/스크립트 파일 경유 등으로 guard 판정을 피하는 쓰기, 사용자에게 알리지 않은 다른 write route
- C:/MoneyLab(`docs/chatgpt-task-handoff`, 기존 dirty/untracked 상태) 변경. 특히 `C:/MoneyLab/.claude/hooks/guard.py` 수정 금지
- 기존 worktree/branch 삭제·수정·정리, 기존 untracked/ignored/E2E/reference/scratchpad 산출물 정리
- 패키지 설치·업그레이드, interpreter 설정 변경, `.venv` 대상 환경 변경
- 인라인 인터프리터 실행(`python -c`, `python - <<EOF` 등), 임시 스크립트
- 실제 `gh` mutation을 테스트 수단으로 쓰기, 네트워크 호출을 테스트에 넣기
- 실데이터, 외부 시장 API, 주문, Monte Carlo
- BT-3E branch/worktree/PR 관련 행위

## ALLOWED_FILES

ALLOWED_FILES:
- M .claude/hooks/guard.py
- M tests/test_agent_guard.py
- M docs/agent_workflow.md

## PROTECTED_FILES

PROTECTED_FILES:
- .claude/settings.json
- .claude/skills/**
- .claude/** 중 .claude/hooks/guard.py를 제외한 전부 (.claude/hooks/의 다른 파일 포함)
- CLAUDE.md
- AGENTS.md
- .agents/**
- README.md
- .github/**
- .gitignore
- .gitattributes
- src/**
- base(3f0880b)에서 tests/ 아래 tracked인 모든 파일 중 tests/test_agent_guard.py를 제외한 전부 (tests/test_skills.py, tests/test_repo_hygiene.py, tests/fixtures/** 포함), 그리고 tests/ 아래 새 파일 생성
- docs/tasks/** (WORKSPACE_SETUP의 docs/tasks/GUARD-GH-01/WORK_ORDER.md 최초 생성과 ACCEPTED ERRATA `docs/tasks/GUARD-GH-01/ERRATA-<NNN>.md` 생성만 예외)
- docs/** 중 docs/agent_workflow.md와 위 docs/tasks 예외를 제외한 전부
- 모든 BT-3E 파일: docs/tasks/BT-3E/**, src/moneylab/backtest/risk_check.py, src/moneylab/backtest/vault.py, tests/test_backtest_risk_check.py, tests/test_backtest_vault.py, docs/backtest_design.md
- configs/**
- research/** (존재하는 경우), src/moneylab/research/**
- 사전등록 파일: docs/research_v04_preregistration.md, docs/research_v05_preregistration_draft.md, docs/research_v06_preregistration_draft.md
- pyproject.toml
- requirements*.txt

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 이 Work Order는 INVALID이고 IMPLEMENTATION에 진입할 수 없다)

## NON_GOALS

NON_GOALS:
- 인라인 `--title`/`-t`, `--body`/`-b` 값의 특수 처리 (D7)
- `git commit` heredoc 처리 변경, 비인용 heredoc 등급 하향 수정 (D8, 후속 GUARD-HEREDOC-01)
- `.claude/settings.json` 권한 규칙 수정 (D9)
- protected-path `sed` 동작 변경 (D10)
- `_moneylab`의 `moneylab` 부분 문자열 판정 방식 변경
- `trading`/`env` 정규식 분해·완화, 새 secret 탐지기, 새 rule 이름
- 활성 guard(`C:/MoneyLab/.claude/hooks/guard.py`) 전환 (별도 activation gate)
- BT-3E 재개

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- D1 실행 파일 정규화:
  - `normalize()`의 기존 실행 파일 축약 모델(`guard.py:118-119`, git/python/py/powershell/pwsh/bash/sh/cmd/node)에 `gh`를 추가한다. 전체 경로 형태(`[^\s;&|()]*/gh(\.exe)?` 뒤에 공백·`;`·`&`·`|`·`)`·끝)와 bare `gh.exe`가 모두 canonical `gh`가 된다.
  - 지원 표기: `gh`, `gh.exe`, `GH.EXE`(소문자화 후), `"/c/Program Files/GitHub CLI/gh.exe"`, `"C:\Program Files\GitHub CLI\gh.exe"`, `C:/tools/gh.exe`, PowerShell `& "C:\Program Files\GitHub CLI\gh.exe"`. 예: `"C:\Program Files\GitHub CLI\gh.exe"` → `c:/program files/github gh`.
  - `/github cli` 같은 디렉터리 이름은 축약되지 않아야 한다(뒤가 공백이 아니므로).
  - 기존 `github` rule과 그 읽기 전용 allowlist가 canonical 명령에 그대로 적용된다.
  - D2의 gh 세그먼트 탐지도 같은 canonicalization helper(같은 표기 집합)를 쓴다.
  - 기존 실행 파일(git/python/bash/sh/powershell 등)의 정규화는 바뀌지 않는다.
  - 알려진 부작용(허용): 인자 경로가 `/gh` + 공백으로 끝나면 `gh`로 바뀌어 ASK `github`가 될 수 있다(안전 쪽, git과 같은 성질).
- D2 좁은 gh stdin payload 분리:
  - 원본 명령(정규화 전, 따옴표 제거 전)에서 다음 조건을 모두 만족할 때만 heredoc 본문을 분리한다.
    - (a) D1 helper로 식별되는 gh 실행 파일 토큰이 있다.
    - (b) gh 토큰부터 heredoc 연산자 `<<`까지(gh 세그먼트)에 `;`, `&`, `|`, `(`, `)`, backtick, `$(`, 줄바꿈이 없다.
    - (c) gh 세그먼트의 resource가 `pr` 또는 `issue`, action이 `create`, `edit`, `comment` 중 하나다.
    - (d) gh 세그먼트에 정확히 `--body-file -` 또는 `-F -` 토큰 쌍이 있다(`--body-file=-`는 해당하지 않는다).
    - (e) 연산자가 `<<` 또는 `<<-`이고 delimiter 단어 전체가 작은따옴표(`'WORD'`) 또는 큰따옴표(`"WORD"`)로 감싸여 있다. `WORD`는 `\w+`.
    - (f) 연산자 줄 다음 줄부터, `WORD`와 정확히 같은 줄(`<<-`이면 앞의 tab만 허용)이 닫는 delimiter로 존재한다. 줄 끝 `\r`(CRLF)이 있으면 닫는 줄로 인정하지 않는다.
    - (g) gh 세그먼트가 있는 줄에 heredoc 연산자(`<<`, `<<-`)가 정확히 하나다. `<<<`(here-string)는 heredoc이 아니다.
  - 조건 중 하나라도 불확실하거나 만족하지 않으면 분리하지 않는다(fail closed). 이때 전체 명령이 현재와 같이 검사된다.
  - 분리 결과는 두 부분이다. GH_PUBLISHED_BODY_PAYLOAD = 연산자 줄 다음 줄부터 닫는 delimiter 줄 직전까지. OPERATIONAL_COMMAND_TEXT = 나머지 전부(payload 앞 텍스트, 연산자 줄의 연산자 뒤 텍스트, 닫는 delimiter 줄 이후의 모든 줄).
  - payload를 버리지 않는다. D3에 따라 별도로 검사한다.
  - 분리하지 않는 대상: 비인용·부분 인용 heredoc(`<<EOF`, `<<\EOF`, `<<E"O"F`), bash/sh/python/pwsh/cat/tee 등 다른 명령의 heredoc, 읽기 전용 gh 명령의 heredoc, `--body-file=-`, PowerShell here-string(`@'…'@`, `@"…"@`).
  - 분리가 일어나지 않은 명령은 OPERATIONAL_COMMAND_TEXT가 원본 명령과 바이트 단위로 같아야 하고, 판정도 base와 같아야 한다.
- D3 게시 본문의 secret 보호:
  - 기존 DENY_RULES 중 `env`(`(^|[\s/=<>])\.env(?!\.example)\b`)와 `trading`(정규식 전체, 분해하지 않음)을 `normalize()`를 거친 GH_PUBLISHED_BODY_PAYLOAD에 그대로 적용한다.
  - 결과로 게시 본문 산문의 `place_order`, `/v1/orders`, `.env.local`, `UPBIT_ACCESS_KEY`, `seed phrase`, `private_key`, `mnemonic` 등은 DENY된다(사용자 승인된 보수적 동작).
  - 검사 순서: OPERATIONAL_COMMAND_TEXT의 DENY_RULES → payload의 `env`/`trading` → OPERATIONAL_COMMAND_TEXT의 나머지 검사(PROTECTED/MUTATE, DELETE_MOVE, ASK_RULES, INLINE_CODE, untracked script, `_moneylab`). payload DENY는 이후 operational 판정보다 우선한다. 보고 rule 이름은 기존 `env` 또는 `trading`이다.
  - 그 밖의 규칙(git/clock/registry/power/exec/hooks DENY, `protected-path`, `protected-word`, `locked`, `inline-code`, `untracked-script`, `_moneylab`, `check_command` 첫 줄의 `git branch -D` 검사)은 payload를 검사하지 않고 OPERATIONAL_COMMAND_TEXT에만 적용한다.
  - 새 탐지기, 새 rule 이름, 새 `Decision` rule 문자열을 추가하지 않는다(`tests/test_skills.py`의 문서·rule 이름 일관성 유지).
- D4 GitHub mutation은 계속 ASK:
  - OPERATIONAL_COMMAND_TEXT에 gh 동사가 남으므로 기존 `github` ASK rule이 매치된다. 기대 판정은 ASK, rule = `github`이다. 단, 우선순위가 더 높은 기존 DENY(operational DENY 또는 D3 payload DENY)가 적용되면 DENY다.
  - payload 분리 때문에 `gh pr create/edit/comment`, `gh issue create/edit/comment`가 PASS가 되어서는 안 된다.
  - 읽기 전용 gh 명령(`--version`, `auth status`, `pr view/list/status/diff/checks`, `run view/list`)은 기존 분류(PASS)를 유지한다.
- D5 비인용 heredoc fail closed: 비인용·부분 인용·모호한 heredoc은 분리하지 않고 전체를 검사한다. 예: `gh pr create --body-file - <<EOF\n$(rm -rf data/raw)\nEOF`는 DENY다.
- D6 명령 체인은 계속 보인다: 검증된 payload 밖의 모든 바이트(체인 `&&`/`;`/`|`, redirect, 닫는 delimiter 이후 줄)는 OPERATIONAL_COMMAND_TEXT로 남아 기존 규칙으로 검사된다.
- D7 인라인 `--title`/`-t`, `--body`/`-b` 값의 특수 처리는 범위 밖이다. 현재 동작을 유지한다.
- D8 `git commit` heredoc 처리(`_HEREDOC`, `_COMMIT_MSG`, `normalize()`의 `git commit` 분기)는 범위 밖이며 바이트 단위로 바꾸지 않는다. 비인용 heredoc 등급 하향 문제는 후속 후보 GUARD-HEREDOC-01이다. GUARD-GH-01은 이를 고치지도 악화시키지도 않는다. 테스트로만 고정한다(T11).
- D9 `.claude/settings.json`은 범위 밖이며 바꾸지 않는다. canonical gh 명령은 settings 권한 matcher가 전체 경로 표기를 인식하지 못해도 guard의 `github` rule로 강제된다. settings 권한 full-path gap이 고쳐졌다고 주장하지 않는다.
- D10 protected-path `sed` 동작(`sed`가 MUTATE로 분류되어 PROTECTED 경로와 함께 쓰이면 `-n`이어도 DENY)은 받아들인 현재 동작이며 바꾸지 않는다. 읽기 전용 확인은 Read 도구, `cat`, `grep`으로 가능하다.

## SECURITY_INVARIANTS

SECURITY_INVARIANTS:
- G1: `gh`, `gh.exe`, `GH.EXE`, 따옴표 유무와 상관없는 Git-Bash·Windows 절대 경로, PowerShell `& "…\gh.exe"` 형태가 모두 bare `gh`와 같은 분류를 받는다. 하나의 공유 canonicalization helper를 쓴다.
- G2: 기존 읽기 전용 allowlist에 없는 gh 명령은 payload 분리 여부와 상관없이 PASS가 되지 않는다.
- G3: D2의 모든 조건을 만족할 때만 payload 처리를 한다. 모호하면 분리하지 않는다.
- G4: 비인용·부분 인용 heredoc, 닫는 delimiter 없음, CRLF, heredoc 여러 개인 경우는 전체를 검사한다.
- G5: gh `pr`/`issue` `create`/`edit`/`comment` 이외의 명령에 붙은 heredoc(bash, sh, python, pwsh, cat, tee, 읽기 전용 gh 포함)은 전체를 검사한다.
- G6: 검증된 payload 밖의 모든 바이트는 OPERATIONAL_COMMAND_TEXT로 남는다.
- G7: `env`와 `trading` DENY 규칙은 payload도 검사하고, 매치되면 operational 판정보다 우선해 DENY한다.
- G8: `_moneylab`(`record-live`, `research-final`, `research-build`)은 검증된 payload를 검사하지 않는다. 게시 산문을 live 명령 의도로 분류하지 않는다.
- G9: `settings.json`, hook 연결, fail-closed wrapper는 바뀌지 않는다. 어떤 규칙도 제거하지 않고, 검증된 payload 밖에서 기존 DENY나 ASK가 PASS로 바뀌지 않는다.
- G10: base의 `tests/test_agent_guard.py`와 `tests/test_skills.py` 사례가 strict xfail을 포함해 정확히 같은 결과를 유지한다.
- G11: `git commit` heredoc 동작(`_HEREDOC`, `_COMMIT_MSG`, `normalize()`의 `git commit` 분기)은 바이트 단위로 바뀌지 않는다.
- G12: 테스트는 프로세스 안에서 `guard.check_command`/`guard.decide`만 호출한다. subprocess `gh`, 네트워크, git remote를 쓰지 않는다.

## CLASSIFICATION_MATRIX

CLASSIFICATION_MATRIX (수정 후 기대 `(action, rule)`; 문자열은 Python 리터럴 표기, `\n`은 줄바꿈; "인용 본문 X" = `gh pr create --body-file - <<'EOF'\nX\nEOF`):
- A. GitHub mutation → (ask, github):
  - `gh pr create --title x`
  - `gh.exe pr create --title x`
  - `GH.EXE pr create --title x`
  - `"/c/Program Files/GitHub CLI/gh.exe" pr create --title x`
  - `"C:\Program Files\GitHub CLI\gh.exe" pr create --title x`
  - 따옴표 없는 백슬래시 경로: `C:\tools\gh.exe pr create --title x`
  - `C:/tools/gh.exe pr create --title x`
  - `cd C:/MoneyLab-x && "/c/Program Files/GitHub CLI/gh.exe" pr create --title x`
  - `gh pr edit 3 --title x`
  - `gh pr comment 3 --body-file - <<'EOF'\nok\nEOF`
  - `gh issue create --title x`
  - `gh issue edit 3 --title x`
  - `gh issue comment 3 --body-file - <<'EOF'\nok\nEOF`
  - `gh pr merge 3` (기존)
  - PowerShell 도구(`decide()`, tool_name PowerShell): `& "C:\Program Files\GitHub CLI\gh.exe" pr create --title x`
- B. GitHub 읽기 전용 → (pass, ""):
  - `gh --version`, `gh auth status`
  - `gh pr view 3`, `gh pr list --state all`, `gh pr status`, `gh pr diff 3`, `gh pr checks 3`
  - `gh run view 1`, `gh run list`
  - `gh.exe pr view 3`, `gh.exe pr list`, `gh.exe pr checks 3`, `gh.exe --version`
  - `"/c/Program Files/GitHub CLI/gh.exe" pr view 3`, `… pr list`, `… pr checks 3`, `… --version`
  - `"C:\Program Files\GitHub CLI\gh.exe" pr view 3`, `… pr list`, `… pr checks 3`, `… --version`
- C. 산문 오탐 회귀 → (ask, github), rule != `record-live`:
  - `cd C:/MoneyLab-x && gh pr create --base main --head f --body-file - <<'EOF'\nMoneyLab access record\nrecord and recorded\nno real data\nEOF`
  - 같은 명령의 `"/c/Program Files/GitHub CLI/gh.exe"` 변형
  - 같은 명령의 `-F -` 변형
  - 같은 명령의 큰따옴표 delimiter `<<"EOF"` 변형
- C2. D2 판별 (base에서는 DENY, 수정 후 (ask, github)):
  - 인용 본문 `never git push origin main` (base: deny `git`)
  - 인용 본문 `we did not move raw files` (base: deny `protected-word`)
  - 인용 본문 `do not run w32tm /resync` (base: deny `clock`)
- D. 게시 본문 secret → DENY (합성 placeholder만 사용):
  - 인용 본문 `see .env.local` → (deny, env)
  - 인용 본문 `UPBIT_ACCESS_KEY placeholder` → (deny, trading)
  - 인용 본문 `seed phrase placeholder` → (deny, trading)
  - 인용 본문 `call place_order here` → (deny, trading)
- E. 비인용·모호 heredoc → (deny, protected-path):
  - `gh pr create --body-file - <<EOF\n$(rm -rf data/raw)\nEOF`
  - `gh pr create --body-file - <<\EOF\n$(rm -rf data/raw)\nEOF`
  - `gh pr create --body-file - <<E"O"F\n$(rm -rf data/raw)\nEOF`
  - `gh pr create --body-file - <<'EOF'\r\nrm -rf data/raw\r\nEOF\r\n` (CRLF, fail closed)
  - `gh pr create --body-file - <<'EOF'\nrm -rf data/raw\n` (닫는 delimiter 없음, fail closed)
- F. 체인과 redirect → (deny, protected-path):
  - `gh pr create --body-file - <<'EOF' && rm -rf data/raw\nprose\nEOF`
  - `gh pr create --body-file - <<'EOF'\nprose\nEOF\n&& rm -rf data/raw`
  - `gh pr create --body-file - <<'EOF'\nprose\nEOF\nrm -rf data/raw`
  - `gh pr create --body-file - <<'EOF' > data/raw/x.json\nprose\nEOF`
- G. gh mutation에 붙지 않은 heredoc → deny:
  - 기존 `python - <<'EOF'\nimport shutil; shutil.rmtree('data/raw')\nEOF`
  - `bash <<'EOF'\nrm -rf data/raw\nEOF`
  - `gh pr create --body-file - && bash <<'EOF'\nrm -rf data/raw\nEOF`
  - `gh pr view 1 <<'EOF'\nrm -rf data/raw\nEOF`
  - `cat <<'EOF' > .claude/hooks/guard.py\nx\nEOF`
- H. MoneyLab CLI (기존 유지):
  - `python -m moneylab record`, `python -m moneylab record --provider upbit --duration 21600`, `python -m moneylab record --provider upbit --source live` → (ask, record-live)
  - `python -m moneylab record --provider upbit --source fixture` → pass
- I. protected `sed` (기존 유지):
  - `sed -n 1,5p .claude/hooks/guard.py` → (deny, protected-path)
  - 기존 `sed -i s/x/y/ .claude/settings.json` → deny
  - `cat .claude/hooks/guard.py` → pass, `grep -n x .claude/hooks/guard.py` → pass
- J. `git commit` heredoc (기존 유지):
  - 기존 `test_commit_message_text_is_not_a_command` 사례 결과 그대로
  - 고정: `git commit -F - <<EOF\n$(rm -rf data/raw)\nEOF`는 현재 (ask, git-commit)이다. strict xfail로 deny를 기대하고(GUARD-HEREDOC-01), 일반 assert로 action == "ask"를 확인한다.

## IMPLEMENTATION_SAFETY_CONDITIONS

IMPLEMENTATION_SAFETY_CONDITIONS (IMPLEMENTATION은 C:/MoneyLab-guard-gh-cli를 root로 하는 새 Claude Code session에서 수행한다):
- S0 session 시작 확인: HEAD = C1, 이 파일의 sha256이 C1 보고 값과 같음, `git status` clean(ignored `.venv` 제외), `.venv` junction이 C:/MoneyLab/.venv를 가리키고 `./.venv/Scripts/python.exe --version`이 동작함.
- S1 `.claude/hooks/guard.py`를 수정하기 전에 원본 정체성을 확인한다: `git hash-object .claude/hooks/guard.py` = 9a72e36d8d27f6654d053e852dc5f92ba1a02847 이고 `git rev-parse HEAD:.claude/hooks/guard.py`도 같은 값. checkout 파일 sha256(BASE_FILE_IDENTITY)도 기록한다. 다르면 STOP.
- S2 구현 변경은 ALLOWED_FILES 3개로 한정한다.
- S3 `.claude/hooks/guard.py` 수정은 의도된 ASK `protected-edit` 경로를 거치며 사용자의 명시적 승인이 필요하다. 거절되면 STOP.
- S4 수정한 guard가 crash하거나 fail-closed가 되어 도구 호출이 막히면 다른 우회나 숨은 write route를 시도하지 않고 STOP한다.
- S5 복구는 사용자의 명시적 조치 후에만 진행한다(예: 사용자가 `!` 명령으로 확인·복원).
- USER_APPLIED(사용자가 guard.py diff를 직접 적용)는 fallback으로만 남긴다. 사용자가 별도로 지시할 때만 쓴다.
- 경로 숨기기, `git apply`/patch 경유 guard 우회, `.claude/settings.json` 수정, hook/guard 비활성화, C:/MoneyLab 수정은 금지다.

## TEST_GATES

TEST_GATES (모두 offline·in-process; 실행은 `./.venv/Scripts/python.exe -m pytest`):
- T1 실행 파일 정규화 변형: 매트릭스 A의 표기들, `GH.EXE`, `C:/tools/gh.exe`, 따옴표 없는 백슬래시 경로, tool_name PowerShell로 `decide()`를 거치는 `&` 호출 연산자 형태가 bare `gh`와 같은 결과.
- T2 GitHub mutation: 매트릭스 A → (ask, github).
- T3 GitHub 읽기 전용: 매트릭스 B → pass.
- T4 산문 오탐 회귀: 매트릭스 C → (ask, github), `rule != "record-live"` 명시 assert.
- T4b D2 판별: 매트릭스 C2 → (ask, github).
- T5 게시 payload secret: 매트릭스 D → `env` 또는 `trading`으로 deny.
- T6 비인용·부분 인용·CRLF·닫는 delimiter 없음 heredoc: 매트릭스 E → deny. PowerShell here-string(`@'…'@`) 본문이 분리되지 않음을 확인하는 사례 포함.
- T7 체인·redirect: 매트릭스 F → deny.
- T8 gh 이외 heredoc 회귀: 매트릭스 G → deny.
- T9 MoneyLab record-live 회귀: 매트릭스 H.
- T10 protected-path sed 회귀: 매트릭스 I.
- T11 git commit heredoc: 매트릭스 J 그대로 + strict xfail 고정.
- T12 `tests/test_agent_guard.py` 전체 통과. base의 기존 테스트는 수정하지 않는다(새 테스트 추가만; 기존 parametrize 목록에 사례를 추가하는 것은 허용하되 기존 사례 삭제·기대값 변경 금지). 기존 strict xfail은 계속 xfailed.
- T13 `tests/test_skills.py`, `tests/test_repo_hygiene.py` 통과, 전체 suite failed 0 / errors 0.
- T14 테스트에 subprocess `gh`, 네트워크, git remote 사용 없음.
- 테스트 문자열에 사용자 홈 경로·개인 이메일을 넣지 않는다(`tests/test_repo_hygiene.py`).
- `git diff --check` 깨끗함, 변경 파일 집합 = ALLOWED_FILES.

## DOCUMENTATION_REQUIREMENTS

DOCUMENTATION_REQUIREMENTS (`docs/agent_workflow.md` 4절; 영구 동작만, BT-3E 등 task 경위 서술 금지):
- `gh`, `gh.exe`, 절대 경로 표기는 모두 `gh`로 정규화되며 `github` ASK 규칙과 읽기 전용 allowlist가 모든 표기에 적용된다.
- gh `pr`/`issue` `create`/`edit`/`comment`에 `--body-file -` 또는 `-F -`로 넘기는 인용 heredoc payload는 명령이 아니라 게시 텍스트로 취급한다(D2 조건 요약).
- 이 payload도 `env`와 `trading`으로 검사하며, gh mutation은 여전히 ASK다.
- 비인용·부분 인용 heredoc, gh 이외 명령의 heredoc, PowerShell here-string, `--body-file=-`는 전체를 검사한다.
- 알려진 오탐: 기존 `sed`+보호 경로 항목 유지, "인라인 `--title`/`--body` 텍스트는 여전히 명령 텍스트로 검사된다" 추가, "게시 본문의 `place_order`·`/v1/orders` 등 `trading` 매치 표현은 deny된다" 추가.
- 알려진 한계: `.claude/settings.json`의 `Bash(gh pr *)`는 전체 경로 표기와 매치되지 않는다(defense in depth 한계); `git commit`의 비인용 heredoc 등급 하향 문제는 후속 작업으로 미뤘다.
- 새 rule 이름이 없으므로 4절 rule 목록은 바뀌지 않는다.

## E2E_GATES

E2E_GATES:
- CLEAN_COMMIT_E2E (clean Ci, TARGET_WORKTREE):
  - (1) `tests/test_agent_guard.py` 단독 실행 통과(T1~T11 포함)
  - (2) `tests/test_skills.py`, `tests/test_repo_hygiene.py` 통과
  - (3) 전체 pytest failed 0 / errors 0
  - (4) Ci의 `.claude/hooks/guard.py`가 매트릭스 A~J를 만족함을 커밋된 테스트로 확인한다. 실제 `gh` mutation으로 확인하지 않는다.
- 기존 출력·이전 산출물은 수정하지 않는다.

## BT3E_INTERLOCK

BT3E_INTERLOCK:
- BT-3E 현재 상태: PUSH = PASS, PR_CI = PAUSED BEFORE PR CREATION (remote branch feature/backtest-bt3e-risk-check = 679d473986d19b217398ce9448bbabdbdbd0cda9).
- BT-3E 재개 조건(둘 다 필요): (1) GUARD-GH-01 MERGE 및 POST_MERGE_AUDIT PASS, (2) 실제 실행되는 guard가 merge된 GUARD-GH-01 guard와 동일함이 검증됨(줄바꿈 변환 때문에 단순 sha256 비교가 아니라 `git hash-object` = merge된 blob id 비교 또는 정규화 명시 비교; 방법은 activation gate에서 정한다).
- 활성 guard 전환(activation)은 GUARD-GH-01 범위 밖이며 별도 명시적 activation decision/gate가 필요하다. GUARD-GH-01은 C:/MoneyLab을 수정하지 않는다.
- BT-3E 재개 gate는 정확히 `git fetch origin main`만 허용할 수 있다(M_g 검증, Ci와 M_g의 read-only mergeability 계산). `git fetch --all`, `--prune`, pull, rebase, BT-3E branch로의 merge, amend, cherry-pick, reset, force push는 금지다. fetch로 remote-tracking ref `origin/main`이 움직일 수 있음을 재개 보고서에 적는다.
- BT-3E의 C1 → Ce → Ci history는 바꾸지 않는다. HISTORY_REWRITE_REQUIRED = NO.

## NONBLOCKING_FOLLOW_UPS

NONBLOCKING_FOLLOW_UPS (기록만, 이 task에서 구현하지 않음):
- GUARD-HEREDOC-01: 기존 `git commit` 비인용 heredoc 등급 하향(`$(…)`이 든 비인용 heredoc 본문이 제거되어 DENY가 ASK로 내려감)
- `.claude/settings.json` 전체 경로 gh 권한 matcher: 알려진 defense-in-depth 한계
- 활성 guard activation: 별도 명시적 gate

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base SHA/tree, C1 SHA/parent/tree, Work Order sha256, Ci SHA/parent/tree, 커밋별 파일 집합과 diff stat, ALLOWED_FILES base blob id, merge parent/tree
- CLAUDE_REPORTED: targeted·전체 pytest 결과, 분류 매트릭스 테스트 결과
- INDEPENDENT/GITHUB_VERIFIABLE: PR CI 결과, GitHub 화면(사용자 확인)
- USER_APPLIED: fallback을 쓴 경우 사용자가 적용한 변경
- 보고서는 각 값의 evidence 등급을 표시한다. Claude가 실행한 결과를 INDEPENDENT로 표시하지 않는다.

## REQUIRED_REPORT

REQUIRED_REPORT: 각 gate의 보고는 한국어로 쓰고(계약 식별자·SHA·경로·상태값은 원문 유지), 해당 Gate Authorization 메시지가 지정한 key 목록으로 끝내며, 최소 다음을 포함한다.
- WORK_ORDER_CONTRACT_VERSION, TASK_ID, 현재 gate, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD/parent/tree, 변경 파일 집합, protected diff, worktree clean, diff --check
- 증거 등급 표시, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- `<GATE>_PASS = YES / NO`, `READY_FOR_<NEXT_GATE> = YES / NO`

## STOP_CONDITIONS

STOP_CONDITIONS:
- base/HEAD/tree가 기대와 다름, Work Order sha256이 C1과 다름
- S1의 guard.py 원본 정체성 불일치
- ALLOWED_FILES 밖 tracked 변경 또는 PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- guard deny, permission prompt 거절, protected-edit ASK 거절
- guard crash 또는 fail-closed로 도구 호출이 막힘 (S4)
- 테스트 실패/에러, base 기존 테스트 결과 변화
- 계약 모순 또는 상위 규칙과 충돌
- 계약을 지키려면 PROTECTED 파일(`.claude/settings.json`, `tests/test_skills.py` 등) 수정이나 새 rule 이름이 필요하다고 판명됨 (PROPOSED_ERRATA로 보고)
- 예상하지 못한 untracked 파일

## REPORT_STORAGE

REPORT_STORAGE: gate별 보고는 채팅만. 저장소에 보관하지 않는다.
