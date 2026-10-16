---
name: incident
description: MoneyLab 장애 조사. 수집 중단, 데이터 공백, 연구 run 실패, 무결성 불일치, guard 차단 같은 장애의 증거를 읽기 전용으로 모으고 원인을 분류해 docs/incidents/에 보고서를 쓴다. 복구는 제안만 한다.
allowed-tools:
  - Read
  - Grep
  - Glob
---

# incident: 장애 조사 (읽기 전용)

이 Skill은 증거 수집, 원인 분류, 보고서 작성, 복구 제안만 한다. 복구 명령, 시스템 설정 변경, 데이터 삭제·이동,
Git 변경, 수집·연구 실행, 거래는 하지 않는다. 아래 명령은 모두 `[A]`(자동, 읽기 전용)다.
유일한 쓰기는 `docs/incidents/` 아래 보고서 파일 하나다. 규칙 전체는 `docs/agent_workflow.md`를 따른다.

## 입력

- 증상: 사용자가 본 것 (오류 메시지, 멈춘 시각, 이상한 수치)
- 대상 경로 (해당하는 것만): Upbit 데이터셋 `data/raw/upbit/research/<session>/<market>`,
  연구 run `data/processed/research/<run>`, 로그 파일
- 시간 창: 장애 전후 시각 (KST와 UTC를 함께 적는다)

## 절차

1. 저장소 상태와 보호 파일 무결성부터 확인한다. 무결성 테스트가 실패하면 그 사실을 맨 앞에 보고하고 다른 조사보다 우선한다.

```bash
git status --short  # [A]
git log --oneline -5  # [A]
git diff --stat HEAD -- configs docs src  # [A]
./.venv/Scripts/python.exe -m pytest -q tests/test_repo_hygiene.py  # [A]
```

2. 수집 장애: recorder 상태, 종료 사유, 마지막 오류, 시계 기록, 무결성을 본다.

```bash
cat data/raw/upbit/research/<session>/<market>/state.json  # [A]
cat data/raw/upbit/research/<session>/<market>/dataset.json  # [A]
tail -n 20 data/raw/upbit/research/<session>/<market>/clock_monitor.jsonl  # [A]
./.venv/Scripts/python.exe -m moneylab record-verify data/raw/upbit/research/<session>/<market>  # [A]
./.venv/Scripts/python.exe -m moneylab replay-check data/raw/upbit/research/<session>/<market>  # [A]
```

3. 연구 run 장애: manifest와 test lock 상태를 본다. `locked/` 해시는 다른 명령과 묶지 않은 단독 `sha256sum`으로만
   실행하고, 꺾쇠 자리표시자 대신 `*` glob을 쓴다 (`<`, `>`가 들어가면 guard가 deny한다).
   test 개봉 여부는 manifest의 `test_access_count`로 본다 (0이면 미개봉). 해시는 manifest의 `test_sha256`과 대조한다.

```bash
grep -n "sha256\|status\|test_access_count" data/processed/research/<run>/manifest.json  # [A]
sha256sum data/processed/research/*/locked/test.jsonl.gz  # [A]
```

4. 시스템 원인 후보 (절전, 시계): 조회만 한다. 설정은 바꾸지 않는다.
   `wevtutil` 필터는 UTC로 쓴다. `/f:text` 출력의 `Date`는 끝에 `Z`가 붙어 있어도 로컬 시각(KST)이다 (2026-10-10 관측).
   Windows 명령에는 `MSYS_NO_PATHCONV=1`을 붙인다. 없으면 Git Bash가 `/query` 같은 인자를 경로로 바꿔서
   `w32tm`은 `C:/Program Files/Git/query`를 받고(exit 87), `powercfg /a`는 인자 오류(exit 1)로 끝난다 (2026-10-10 관측).
   이 명령들은 콘솔 코드 페이지로 출력한다. 먼저 `chcp.com`으로 코드 페이지를 확인한다. 숫자는 글자가 깨져도 읽힌다.
   949면 아래처럼 `iconv`로 UTF-8로 바꾸고, 65001이면 `| iconv ...` 없이 실행한다. 다른 값이면 변환하지 않고 원본을 그대로 기록한다.
   (`iconv -f`는 쓰지 않는다. `tests/test_skills.py`의 `-f` 패턴에 걸린다.)

```bash
chcp.com  # [A]
MSYS_NO_PATHCONV=1 wevtutil qe System "/q:*[System[(EventID=506 or EventID=507) and TimeCreated[@SystemTime>='<from-utc>' and @SystemTime<='<to-utc>']]]" /f:text | iconv --from-code=CP949 --to-code=UTF-8  # [A]
MSYS_NO_PATHCONV=1 w32tm /query /status | iconv --from-code=CP949 --to-code=UTF-8  # [A]
MSYS_NO_PATHCONV=1 powercfg /a | iconv --from-code=CP949 --to-code=UTF-8  # [A]
```

5. guard 차단: 차단 메시지의 `[rule]` 이름과 명령을 그대로 기록하고 `docs/agent_workflow.md` 4절의 규칙·알려진 오탐과 대조한다.
   우회 명령을 시도하지 않는다.

6. 분류: 아래 중 하나 이상을 고른다.
   `collection` (수집 중단·공백) · `clock` · `research-run` · `integrity` · `guard` · `network` (HTTP 상태 포함) · `environment` (전원, 디스크, venv) · `unknown`

7. 보고서를 `docs/incidents/YYYYMMDD-<slug>.md`에 쓴다 (날짜는 장애 발생일, KST). 필수 절:
   `## 요약`, `## 분류`, `## 사실`, `## 가설`, `## 증거`, `## 영향`, `## 무결성`, `## 복구 제안`.
   모의(재현) 보고서는 제목 아래에 그렇다고 적는다.

## 검증 기준

- 사실과 가설이 다른 절에 있다. 사실에는 출처(파일 경로, 명령, 로그 이벤트)가 붙어 있다.
- HTTP 451/401/403의 원인을 단정하지 않는다 (CLAUDE.md 절대 규칙 4).
- 시각은 KST와 UTC를 구분해 적는다.
- 무결성 절에 hygiene 테스트 결과와 관련 해시를 적는다.
- 보고서에 비밀정보, 사용자 홈 경로, 개인 이메일이 없다 (`tests/test_repo_hygiene.py`).
- 조사 중 승인 창이 한 번도 뜨지 않았다. 떴다면 그 명령은 이 Skill 범위 밖이므로 거절하고 보고한다.

## 실패 처리

- 명령이 guard에 막히면 우회하지 않고 막힌 사실을 보고서의 증거로 남긴다.
- 파일이 없거나 읽을 수 없으면 "미확인"으로 적고 계속한다. 추측으로 채우지 않는다.
- `iconv`가 `cannot convert`를 내거나 0이 아닌 값으로 끝나면 변환이 실패한 것이다. 그 앞까지만 출력되고 나머지는 버려진다.
  변환된 일부를 결과로 쓰지 않는다. 오류 메시지를 보고서 증거 절에 그대로 적고, 아래처럼 변환 없이 한 번 다시 실행해 원본 출력을 보존한다.
  깨진 글자를 추측으로 해석하지 않는다. 숫자·영문 필드만 사실로 적고 나머지는 "미확인 (인코딩)"으로 적는다.

```bash
MSYS_NO_PATHCONV=1 wevtutil qe System "/q:*[System[(EventID=506 or EventID=507) and TimeCreated[@SystemTime>='<from-utc>' and @SystemTime<='<to-utc>']]]" /f:text  # [A]
MSYS_NO_PATHCONV=1 w32tm /query /status  # [A]
MSYS_NO_PATHCONV=1 powercfg /a  # [A]
```
- 무결성 테스트가 실패하면 조사를 멈추고 사용자에게 먼저 알린다. 파일을 되돌리지 않는다.
- 모든 도구 호출이 막히면 (guard fail-closed) 에이전트는 진단할 수 없다. 사용자에게 아래 명령을 직접 실행하도록 안내한다.

```text
! ./.venv/Scripts/python.exe --version
! which timeout bash
! echo "$CLAUDE_PROJECT_DIR"
```

## 승인 조건

- 이 Skill 안에서는 승인이 필요한 작업을 하지 않는다. 모든 명령이 `[A]`다.
- 보고서의 복구 제안을 실행하려면 해당 Skill(`collect-session`, `research-run`, `git-ship`)의 승인 절차를 따른다.
- 보고서 파일을 커밋하는 것은 `git-ship`의 일이다.

## 복구 절차

이 Skill은 복구를 실행하지 않는다. 보고서의 `## 복구 제안`에 아래 기준으로 제안만 적는다.

| 분류 | 제안 |
|---|---|
| collection | raw 데이터는 보존. 원인 해소 후 같은 `--out`으로 이어서 수집 (`collect-session`, `[B]`). 품질 판정은 사용자 |
| clock | 시계·시간 서비스 설정은 바꾸지 않는다. 사용자가 직접 확인할 항목만 적는다 |
| environment | 절전·전원 설정은 사용자가 직접 바꾼다. 에이전트는 바꾸지 않는다 |
| research-run | 실패한 run 보존, 새 run 생성 (`research-run`, `[B]`). test가 열린 run은 재사용 불가 |
| integrity | 모든 작업 중지, 사용자 판단 |
| guard | 오탐이면 정책 변경 제안 (사용자 결정, `.claude/` 수정은 `[B]`) |
| network | 사실(상태 코드, 헤더, 시각)만 적고 원인 가설은 가설 절에. 우회 기능은 제안하지 않는다 |
