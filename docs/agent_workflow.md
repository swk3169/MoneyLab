# Agent workflow (Claude Code)

MoneyLab에서 Claude Code 에이전트가 작업하는 규칙이다. `.claude/hooks/guard.py`, `.claude/settings.json`,
`.claude/skills/*/SKILL.md`, `tests/test_skills.py`와 함께 유지한다. guard 규칙을 바꾸면 이 문서도 같이 바꾼다
(`tests/test_skills.py`가 규칙 이름을 대조한다).

## 1. 보호 계층

| 계층 | 위치 | 강제력 | 역할 |
|---|---|---|---|
| 권한 규칙 | `.claude/settings.json` `permissions` | Claude Code가 강제 | 경로·명령 접두어 단위 allow/ask/deny |
| Guard hook | `.claude/hooks/guard.py` (PreToolUse) | Claude Code가 강제, fail-closed | 명령 텍스트·경로를 보고 deny/ask/pass |
| 저장소 테스트 | `tests/test_repo_hygiene.py`, `tests/test_agent_guard.py`, `tests/test_skills.py` | pytest·CI | frozen 해시, 위생, guard 회귀, Skill 일관성 |
| Skill 절차 | `.claude/skills/*/SKILL.md` | 에이전트가 따름 (강제 아님) | 순서, 검증 기준, 실패·복구 절차 |

강제력이 있는 것은 위 두 줄(권한 규칙, guard)뿐이다. Skill 문서는 절차이고 보안 경계가 아니다.
Skill이 "승인 필요"라고 적어도 guard나 권한 규칙이 ask를 내지 않으면 승인 창은 뜨지 않는다.
그래서 Skill 명령에는 아래 등급 태그를 달고, `tests/test_skills.py`가 태그와 실제 guard 판정이 일치하는지 검사한다.

guard는 명령을 텍스트로 매칭하는 한 계층이다. 실행 중에 조립되는 경로와 디스크에 먼저 쓴 스크립트는 보지 못한다
(`tests/test_agent_guard.py`의 strict xfail 2건). 그 공백은 권한 규칙과 해시 고정 테스트가 메운다.

## 2. 권한 등급

| 태그 | 이름 | guard 판정 | 실행 방식 | 예 |
|---|---|---|---|---|
| `[A]` | 자동 | pass, 권한 규칙 ask/deny 없음 | 승인 없이 실행 | `git status`, `git diff`, `pytest`, `record-verify`, `replay-check`, `research-build --dry-run`, `research-stats`, `w32tm /query`, `powercfg /a` |
| `[B]` | 승인 (강제) | ask, 또는 pass지만 권한 규칙 ask | 승인 창에서 사용자가 승인 | live `record`, fixture `record --provider upbit` (권한 규칙 ask), 정식 `research-build`, `research-final`, `git commit`, `git push`, `gh pr create`, `git reset --soft`, `git revert`, `pip install`, `.claude/`·`.github/`·`CLAUDE.md` 수정 |
| `[B-skill]` | 승인 (절차) | pass, 권한 규칙 ask/deny 없음 | 에이전트가 먼저 묻고 사용자가 대화로 승인 | `git add -- <경로>` (index만 바뀌고 되돌릴 수 있음) |
| C | 금지 | deny | 실행하지 않음. Skill에 넣지 않음 | force push, main 직접 push, `git add -A`/`.`, `--no-verify`, `git clean`, `reset --hard`, 시계·레지스트리·전원 변경, raw·locked·frozen 파일 변경, 키·주문 관련 문자열 |

C 등급은 태그가 없다. Skill 코드 블록에 deny 명령이 하나라도 있으면 테스트가 실패한다.

## 3. 승인 절차

1. `[B]`·`[B-skill]` 단계 전에 한 줄로 알린다: 무엇을 실행하는지, 무엇이 바뀌는지, 되돌리는 방법.
2. 승인 창(`[B]`)이나 대화(`[B-skill]`)에서 사용자가 승인한 경우에만 진행한다.
3. 거절되면 멈추고 보고한다. 같은 결과를 내는 다른 명령으로 돌아가지 않는다.
4. 승인은 그 한 번의 실행에만 유효하다. 재시도, 다른 인자, 다음 run은 새로 승인받는다.
5. guard가 deny하면 우회하지 않는다 (변수로 경로 조립, 스크립트 파일 경유, 인코딩 등). 오탐이면 `incident`로 보고하고
   정책 변경은 사용자가 결정한다.
6. `research-final`은 run당 한 번이다. 실행 전에 manifest로 test가 열리지 않았는지 확인하고, 실패해도 자동 재시도하지 않는다.
7. 사전등록(`docs/research_v04_preregistration.md`, `configs/research_v04.toml`)을 바꾸면 새 study다. Skill은 이를 바꾸지 않는다.
8. PR 생성(`gh pr create`)과 merge(`gh pr merge`)는 `github` ask 규칙의 `[B]`다. v1.2 Work Order에서 Gate Authorization이
   `PR_CREATE: YES` 또는 `MERGE_EXECUTE: YES`를 명시한 경우에만 실행하고, 승인 창에서 다시 승인받는다. merge는
   `--merge --match-head-commit <SHA>`로만 하며 `--admin`·`--auto`·`--squash`·`--rebase`·`--delete-branch`·`--force`를 쓰지
   않는다. 조건과 사전 검증은 `docs/tasks/README.md` §13을 따른다.

## 4. Guard 규칙 목록

이름은 guard 거부·승인 메시지의 `[rule]`에 나온다.

- 명령 deny 규칙 (`DENY_RULES`): `clock`, `registry`, `power`, `git`, `trading`, `env`, `exec`, `hooks`
- 명령 ask 규칙 (`ASK_RULES`): `git-commit`, `git-push`, `git-history`, `git-config`, `github`, `deps`, `schedule`,
  `recursive-delete`
- 경로 규칙: `locked`, `protected-path`, `protected-word` (deny), `inline-code`, `untracked-script` (ask)
- MoneyLab CLI (ask): `research-final`, `research-build` (`--dry-run` 제외), `record-live` (`--source fixture` 제외)
- 파일 도구: `locked`, `env`, `frozen`, `raw-or-git`, `claude-settings` (deny), `protected-edit` (ask)
- 입력 오류: `malformed` (deny)

GitHub CLI:

- `gh`, `gh.exe`, 절대 경로 표기(`"/c/Program Files/GitHub CLI/gh.exe"`, `"C:\Program Files\GitHub CLI\gh.exe"`,
  `C:/tools/gh.exe`, PowerShell `& "…\gh.exe"`)는 모두 `gh`로 정규화된다. `github` ask 규칙과 읽기 전용 allowlist
  (`--version`, `auth status`, `pr view/list/status/diff/checks`, `run view/list`)가 모든 표기에 같이 적용된다.
- gh `pr`/`issue` `create`/`edit`/`comment`에 `--body-file -` 또는 `-F -`로 넘기는 인용 heredoc(`<<'WORD'`, `<<"WORD"`,
  `<<-`) 본문은 명령이 아니라 게시 텍스트로 취급한다. 조건: Bash 도구, 명령 전체에 heredoc이 하나, gh 앞에는 `cd DIR &&`만,
  gh부터 `<<`까지 `;` `&` `|` `(` `)` backtick `$(` 줄바꿈 없음, 따옴표·주석·줄 이어짐이 모호하지 않음, `WORD`와 정확히 같은
  닫는 줄(CRLF `\r`이면 닫힘으로 보지 않음)이 있음. 하나라도 어긋나면 분리하지 않고 명령 전체를 검사한다.
- 게시 본문도 `env`와 `trading`으로 검사한다. 본문은 텍스트를 지우는 정규화(`git commit` 메시지 제거, 실행 파일 축약 등)를
  거치지 않는다. 본문 밖의 모든 텍스트(체인, redirect, 닫는 줄 이후)는 명령으로 검사되고, gh mutation은 여전히 `github` ask다.
- 비인용·부분 인용 heredoc(`<<EOF`, `<<\EOF`, `<<E"O"F`), gh 이외 명령(bash, python, cat, 읽기 전용 gh 등)의 heredoc,
  PowerShell here-string(`@'…'@`), `--body-file=-`는 전체를 검사한다.

알려진 오탐 (안전 쪽, 정책 미수정):

- `git stash list` 같은 읽기 전용 stash 명령도 `git-history`로 ask된다. Skill에서는 stash를 쓰지 않는다.
- 한 명령에 `sed` 등 변경 동사와 frozen 파일 경로가 함께 있으면 deny된다. 명령을 나눈다.
- `.env` 문자열이 들어간 명령은 `ls`라도 deny된다.
- `locked/` 경로는 단독 `sha256sum`·`ls`만 허용된다. `&&`로 다른 명령과 묶거나 `<run>` 같은 꺾쇠 자리표시자를 쓰면
  deny된다. Skill에서는 `data/processed/research/*/locked/test.jsonl.gz`처럼 glob을 쓴다.
- 인라인 `--title`/`-t`, `--body`/`-b` 텍스트는 여전히 명령 텍스트로 검사된다. 긴 본문은 인용 heredoc(`--body-file -`)으로 넘긴다.
- 게시 본문의 `place_order`·`/v1/orders`·`.env.local`·`UPBIT_ACCESS_KEY`처럼 `trading`·`env`에 매치되는 표현은 deny된다.

알려진 한계:

- `.claude/settings.json`의 `Bash(gh pr *)` 권한 규칙은 전체 경로 gh 표기와 매치되지 않는다(defense in depth 한계).
  전체 경로 표기는 guard의 `github` 규칙으로만 ask된다.
- `git commit`의 비인용 heredoc 본문은 검사 전에 제거되어, 본문의 `$(…)`가 deny 대신 `git-commit` ask로 내려간다.
  후속 작업으로 미뤘다(`tests/test_agent_guard.py`의 strict xfail).

## 5. Skill 작성 규칙

- 위치: `.claude/skills/<name>/SKILL.md`. 스크립트 파일은 두지 않는다 (미추적 스크립트는 ask, 기존 CLI와 중복).
- frontmatter: `name`(폴더 이름과 같음), `description`. 데이터를 만들거나 외부로 나가는 Skill
  (`collect-session`, `research-run`, `git-ship`)은 `disable-model-invocation: true`로 사용자만 호출한다.
- `allowed-tools`는 읽기 도구(`Read`, `Grep`, `Glob`)만 쓸 수 있다. Bash나 쓰기 도구를 넣어 승인을 미리 주지 않는다.
- 필수 절: `## 입력`, `## 절차`, `## 검증 기준`, `## 실패 처리`, `## 승인 조건`, `## 복구 절차`.
  `git-ship`의 복구 절차는 `### commit 전`, `### commit 후`, `### push 후`로 나눈다.
- 실행 명령은 ` ```bash ` 블록에 한 줄에 하나씩 쓰고 줄 끝에 `# [A]`, `# [B]`, `# [B-skill]` 중 하나를 단다.
  자리표시자는 `<session>`처럼 꺾쇠로 쓴다.
- MoneyLab 명령은 `./.venv/Scripts/python.exe -m moneylab <subcommand>` 형태로 쓰고, 존재하는 하위 명령만 쓴다.
- `/`로 시작하는 인자를 받는 Windows 명령(`w32tm`, `powercfg`, `wevtutil` 등)에는 `MSYS_NO_PATHCONV=1`을 붙인다.
  Git Bash가 `/query`를 `C:/Program Files/Git/query`로 바꿔 넘기기 때문이다. 접두어가 없으면 `w32tm /query /status`는 exit 87,
  `powercfg /a`는 인자 오류(exit 1)로 끝난다 (2026-10-10 관측). guard 판정은 접두어가 있든 없든 pass다.
- 이 명령들은 콘솔 코드 페이지(이 PC는 949, CP949)로 출력해서 한글이 깨진다. `chcp.com`으로 코드 페이지를 확인하고
  `| iconv --from-code=CP949 --to-code=UTF-8`로 바꾼다. `-f`는 `tests/test_skills.py`의 `force` 패턴에 걸리므로 긴 옵션을 쓴다.
  `iconv`가 실패하면(`cannot convert`, 0이 아닌 종료) 변환 없이 다시 실행해 원본을 보존하고 오류를 보고한다.
- 금지: `--no-verify`, `$(...)`·백틱, 변수로 만든 경로, `bash -c`·`python -c`, `eval`, 인코딩된 명령,
  `disableAllHooks`, `--dangerously-skip-permissions`, `core.hooksPath`.
- 비밀정보, 사용자 홈 경로, 개인 이메일을 쓰지 않는다 (`tests/test_repo_hygiene.py`가 검사).

## 6. 장애 대응과 복구

공통: 사실(관측한 출력, 경로, 종료 사유)과 가설을 나눠 적는다. HTTP 451/401/403의 원인을 단정하지 않는다.
보고서는 `incident` Skill이 `docs/incidents/YYYYMMDD-<slug>.md`로 쓴다. 복구 실행은 해당 Skill의 승인 절차를 따른다.

| 상황 | 즉시 조치 | 복구 |
|---|---|---|
| guard deny | 멈추고 규칙 이름과 명령 보고 | 오탐이면 정책 변경 제안 (사용자 결정, `.claude/` 수정은 `[B]`) |
| 모든 도구 호출이 막힘 (guard fail-closed) | 에이전트는 고칠 수 없음 | 사용자가 `!` 명령으로 venv, `CLAUDE_PROJECT_DIR`, `timeout` 확인 |
| 수집 중단 (`disk_low`, `connection_failure`, `clock_unstable`, 451/401/403) | raw 데이터 보존, 종료 사유·로그 수집 | 원인 해소 후 같은 `--out`으로 이어서 수집 (`[B]`), 품질 판정은 사용자 |
| research-build 실패 | 실패한 run 디렉터리 보존 | 새 run 생성 (`[B]`). 삭제는 사용자 결정 |
| research-final 실패 | 재시도하지 않음 | test가 열렸는지 manifest로 확인 후 보고. 열린 run은 재사용 불가 |
| 무결성 불일치 (frozen·manifest·locked 해시) | 모든 작업 중지 | 사용자 보고. 에이전트는 파일을 되돌리지 않음 |
| 잘못된 stage·commit·push | `git-ship` 복구 절차 | commit 전/후/push 후를 구분해 되돌림 |

재시도 정책: `[A]`는 원인을 확인한 뒤 1회까지. `[B]`·`[B-skill]`은 재시도도 새 승인이다.
네트워크 재시도는 `core/http.HttpClient`가 맡고, recorder는 451/401/403을 재시도하지 않는다.

## 7. CI 범위

`data/`는 git에 없으므로 CI에서는 `tests/test_repo_hygiene.py`의 `@needs_runs` 3건이 skip된다
(run manifest 대조, locked split 해시·미개봉, raw manifest 대조). 이 3건은 로컬에서만 검증된다.
frozen blob 해시, CRLF checkout, 위생·비밀정보 검사, guard 테스트, Skill 테스트는 CI에서도 돈다.
Windows나 Git Bash가 필요한 일부 guard 테스트는 러너 환경에 따라 skip될 수 있다.

## 8. 범위 밖 (향후 과제)

이번 단계에서 구현하지 않는다: 무인 실행 루프, 작업 큐, 스케줄러(`schtasks`, 클라우드 routine), headless 실행의 비용 한도,
실행 로그 hook, recorder 중복 실행 lock, 실거래·지갑·주문 기능. 무인화 전에는 headless 모드에서 ask 판정이 어떻게
처리되는지 실측해야 한다. 실거래는 `CLAUDE.md` 절대 규칙 1과 `docs/live_execution_design.md`를 따른다.
