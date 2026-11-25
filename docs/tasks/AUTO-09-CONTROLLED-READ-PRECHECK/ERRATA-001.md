# ERRATA: AUTO-09-CONTROLLED-READ-PRECHECK ERRATA-001

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: AUTO-09-CONTROLLED-READ-PRECHECK-ERRATA-001
TASK_ID: AUTO-09-CONTROLLED-READ-PRECHECK
TARGET_WORK_ORDER: docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md @ C1 ae9995b72ae94423571ad923dd04b5750d89119f, SHA-256 16ea11a4ed684d401b76fc3d6929a90b5ae629950c9d81d9d2537102d3099d40
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 저장소 관리자(현재 대화 사용자), 2026-11-26

이 파일은 발행 후 수정하지 않는다. 이 ERRATA는 아래 CHANGED_FIELDS에 적은 항목만 보완한다. 적지 않은 WORK_ORDER의 절과 조항은 그대로 유지한다.

## CHANGED_FIELDS

- GATE_SEQUENCE: PUSH와 PR_CI 사이에 ERRATA_COMMIT, PUSH_ERRATA를 넣는다.
- GATE_AUTHORIZATION_FORMS: ERRATA_COMMIT, PUSH_ERRATA 형식을 추가하고 PR_CI·MERGE의 head SHA를 E로 정한다.
- EXPECTED_ASK: ERRATA_COMMIT의 ERRATA-001.md Write와 `git commit`, PUSH_ERRATA의 `git push`를 추가한다.
- NETWORK: N3a(PUSH_ERRATA)를 추가하고, N4(PR_CI)·N5(MERGE)·N6(POST_MERGE_AUDIT)에 읽기 조회를 추가한다.
- FILE_CREATION: F8(ERRATA-001.md)을 추가한다.
- PROTECTED_FILES: docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/**의 예외에 ERRATA_COMMIT의 ERRATA-001.md 최초 작성 1회를 추가한다.
- FILE_FORMAT: ERRATA-001.md를 신규 문서로 검사한다.
- CI_CRITERIA: 대기 상태 처리, 조회 한도, F_pr 판정을 보완한다.
- 시간 예산: 누적 10800초 예산 준수 여부는 미입증으로 유지하고, 이 ERRATA 수락 메시지 이후 COMPLETE 보고까지의 gate 수행 시간에 추가 상한 6400초를 둔다(R10). FIX·전체 pytest·targeted의 기존 횟수 예산은 바꾸지 않는다.
- 승인 head와 범위: PUSH_ERRATA 이후 승인 head를 E로 하고 기대 범위를 3커밋·11파일로 한다.
- 기존 감사·E2E 재사용 조항을 추가한다.
- REQUIRED_EVIDENCE, REQUIRED_REPORT, STOP_CONDITIONS에 새 단계의 항목을 추가한다.

## RATIONALE

- WORK_ORDER의 N4·N5는 PR 생성·CI 조회·merge 명령만 허용한다. 그래서 PR 생성과 merge 전후에 원격 main·head·열린 PR·PR 범위를 실시간으로 확인할 수 없다. 이 확인들은 docs/tasks/README.md §13의 PR 생성과 merge 조건을 판정하는 데 필요하다.
- Gate Authorization은 Work Order가 정한 gate 최대 범위를 넓히지 못한다. 그래서 계약 정정이 필요하다.
- N3 push 1회는 이미 사용했다. ERRATA 커밋을 원격에 올리려면 추가 push 1회가 필요하다.

## REPLACEMENT_CONTRACT

### R1. 적용 기준과 용어

- C1: ae9995b72ae94423571ad923dd04b5750d89119f
- IMPL(구현 커밋): c207fb1b466cfbfd20f4b27b696f584e4f3b50a7
- EXPECTED_BASE_SHA: d471d644279ed8b2fe861a23dedca7765c5511ac
- 저장소: swk3169/MoneyLab (origin https://github.com/swk3169/MoneyLab.git)
- base branch: main
- head branch: codex/auto-09-controlled-read-precheck
- E: ERRATA_COMMIT에서 실제로 만들어진 문서 전용 커밋. parent는 IMPL이고, 이 ERRATA-001.md 한 파일만 추가한다. E의 SHA는 이 문서에 적지 않는다. 생성 후 보고된 값을 이후 gate의 승인 head로 쓴다.
- N: PR_CI에서 생성된 task PR의 번호.
- M: MERGE로 생긴 merge commit의 SHA.
- 감사 S: PRECOMMIT_AUDIT에서 확정한 구현 9개 파일의 S 값.

### R2. GATE_SEQUENCE

GATE_SEQUENCE: WORKSPACE_SETUP PART=WORKTREE -> WORKSPACE_SETUP PART=C1_ENV -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> ERRATA_COMMIT -> PUSH_ERRATA -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

ERRATA_COMMIT과 PUSH_ERRATA는 이 ERRATA가 추가하는 독립 단계다. 각 단계에는 그 단계의 Gate Authorization이 따로 있어야 한다.

### R3. GATE_AUTHORIZATION_FORMS 추가·보완

- ERRATA_COMMIT:
  `GATE_AUTHORIZATION: AUTO-09-CONTROLLED-READ-PRECHECK ERRATA_COMMIT ERRATA=001 ERRATA_SHA256=<64hex> ERRATA_SOURCE=<C:/MoneyLab-auto-09 밖의 절대 경로> WO@ae9995b72ae94423571ad923dd04b5750d89119f`
- PUSH_ERRATA:
  `GATE_AUTHORIZATION: AUTO-09-CONTROLLED-READ-PRECHECK PUSH_ERRATA WO@ae9995b72ae94423571ad923dd04b5750d89119f HEAD=<E>`
- PR_CI와 MERGE의 형식은 WORK_ORDER의 형식을 따르고, §13 추가 필드의 head SHA는 E로 적는다.

### R4. ERRATA_COMMIT

ERRATA_COMMIT만 ERRATA-001.md의 최초 생성, staging, 문서 전용 커밋 1회를 허용한다. 각 명령은 독립 호출로 실행한다. 보호 경로에는 cp나 셸 리디렉션으로 쓰지 않는다.

1. 오프라인 전제를 확인한다:
   - HEAD = IMPL, branch = head branch
   - tracked·untracked·staged 변경 0개
   - `sha256sum docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md` → TARGET_WORK_ORDER의 SHA-256
2. `sha256sum data/processed/auto09/tools/bytes_check.py` → ebc57d35e7ba9d0fdcdab6342ff59ef726161e668a7d6e72b3c6fbf31a6004b6
3. 직전 W·S: `.venv/Scripts/python.exe -I -B data/processed/auto09/tools/bytes_check.py src/moneylab/controlled_read/__main__.py src/moneylab/controlled_read/selector.py src/moneylab/controlled_read/transcript.py src/moneylab/controlled_read/profiles.py src/moneylab/controlled_read/store.py .claude/hooks/guard.py docs/agent_workflow.md tests/test_agent_guard.py tests/test_controlled_read_precheck.py docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md` → 종료 코드 0, 구현 9개 파일의 S = 감사 S, WORK_ORDER.md의 W = S = TARGET_WORK_ORDER의 SHA-256
4. `sha256sum <ERRATA_SOURCE>` → ERRATA_SHA256
5. `test -e docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/ERRATA-001.md` → 종료 코드 1
6. Read 도구로 ERRATA_SOURCE 전체를 읽고, Write 도구로 docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/ERRATA-001.md에 같은 내용을 최초 작성한다.
7. `.venv/Scripts/python.exe -I -B data/processed/auto09/tools/bytes_check.py docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/ERRATA-001.md` → 종료 코드 0, W = S = ERRATA_SHA256
8. R7의 신규 문서 FILE_FORMAT 확인
9. `git add -- docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/ERRATA-001.md`
10. `git diff --cached --name-status` → `A` 그 경로 1개
11. `git cat-file blob :docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/ERRATA-001.md | sha256sum` → ERRATA_SHA256
12. `git diff --cached --check` → 빈 출력, 종료 코드 0
13. 1회 실행: `git commit -m "docs(task): accept AUTO-09-CONTROLLED-READ-PRECHECK ERRATA-001" -m "AUTO-09-CONTROLLED-READ-PRECHECK ERRATA-001: read-only PR_CI and MERGE checks, one fast-forward push of the errata commit." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`
14. 커밋 후 확인:
    - `git rev-parse HEAD HEAD^ HEAD^{tree}` → HEAD^ = IMPL. HEAD를 E로 보고한다.
    - `git diff-tree --no-commit-id --name-status -r HEAD` → `A` ERRATA-001.md 1개
    - `git cat-file blob HEAD:docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/ERRATA-001.md | sha256sum` → ERRATA_SHA256
    - 3번과 같은 bytes_check 명령 → 구현 9개 파일의 W와 S가 3번 결과와 같고, S = 감사 S. WORK_ORDER.md의 W = S = TARGET_WORK_ORDER의 SHA-256
    - `git status --porcelain=v1` → 빈 출력

### R5. PUSH_ERRATA (NETWORK N3a)

오프라인 전제:
- HEAD = E, 작업 트리 변경 0개
- `git log --format=%H d471d644279ed8b2fe861a23dedca7765c5511ac..HEAD` → E, IMPL, C1의 3개
- `git diff --name-status d471d644279ed8b2fe861a23dedca7765c5511ac HEAD` → R8의 F 11개

네트워크(이 gate에서만, 각 1회):
- 사전 1: `git ls-remote origin refs/heads/main` → EXPECTED_BASE_SHA
- 사전 2: `git ls-remote origin refs/heads/codex/auto-09-controlled-read-precheck` → IMPL
- push: `git push origin codex/auto-09-controlled-read-precheck` (IMPL → E 일반 fast-forward)
- 사후 1: `git ls-remote origin refs/heads/codex/auto-09-controlled-read-precheck` → E
- 사후 2: `git ls-remote origin refs/heads/main` → EXPECTED_BASE_SHA

force, `--force-with-lease`, tag, 다른 branch, 재시도는 금지한다. push가 거절되거나 결과가 불명이면 STOP한다.

### R6. FILE_CREATION·PROTECTED_FILES 보완

- F8: docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/ERRATA-001.md를 ERRATA_COMMIT에서 1회 최초 작성한다. 생성 전에 `test -e` → 종료 코드 1을 확인한다.
- PROTECTED_FILES의 docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/** 예외는 WS-B4의 WORK_ORDER.md 최초 작성 1회와 ERRATA_COMMIT의 ERRATA-001.md 최초 작성 1회다.
- PR 본문 전달용 임시 파일은 허용하지 않는다. 확정된 본문은 `gh pr create`의 `--body` 인자로 직접 전달한다.

### R7. FILE_FORMAT 보완

ERRATA-001.md는 신규 문서로 검사한다. 규칙은 UTF-8 strict 디코딩, BOM 없음, 줄 끝 LF, 파일 끝 LF 정확히 1개, `git diff --cached --check` 위반 없음이다. 정확한 검사 방법은 ERRATA_COMMIT Gate Authorization에서 고정한다. 위반은 보고만 하고 자동으로 정정하지 않는다.

### R8. 승인 head와 범위

- PUSH_ERRATA 이후 PR_CI, MERGE, POST_MERGE_AUDIT, COMPLETE의 승인 head는 E다.
- 구현 기준 커밋은 IMPL로 유지한다. COMMIT_STEPS의 "9개" 판정은 IMPL에 대한 것이다.
- `WO@` 기준은 C1 ae9995b72ae94423571ad923dd04b5750d89119f로 유지한다.
- 기대 커밋(base 이후): C1, IMPL, E의 3개.
- 기대 파일 집합 F(11개):
  - M .claude/hooks/guard.py
  - M docs/agent_workflow.md
  - M src/moneylab/controlled_read/__main__.py
  - M src/moneylab/controlled_read/profiles.py
  - M src/moneylab/controlled_read/selector.py
  - M src/moneylab/controlled_read/store.py
  - M src/moneylab/controlled_read/transcript.py
  - M tests/test_agent_guard.py
  - A tests/test_controlled_read_precheck.py
  - A docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/WORK_ORDER.md
  - A docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/ERRATA-001.md

### R9. 기존 감사·E2E 재사용

다음이 모두 성립하면 PRECOMMIT_AUDIT와 CLEAN_COMMIT_E2E(IMPL 대상)의 기존 결과를 E에 재사용한다. 이 경우 시험, 수집, 별도 검토를 반복하지 않는다.
- `git diff --name-status c207fb1b466cfbfd20f4b27b696f584e4f3b50a7 E` → `A docs/tasks/AUTO-09-CONTROLLED-READ-PRECHECK/ERRATA-001.md` 1개
- R4 14번의 W·S 조건

재사용은 기존 기록의 효력을 넓히지 않는다. CLEAN_COMMIT_E2E의 종료 코드 3건(B1 대 B5 diff, targeted pytest, B5 대 B6 diff)은 미입증 상태와 관리자 한정 수락을 그대로 유지한다. 이 ERRATA로 계약 준수가 소급 입증되지 않는다. PR CI는 E를 대상으로 판정한다.

### R10. PR_CI (NETWORK N4 보완)

조회 대상은 저장소 swk3169/MoneyLab의 main, head branch, 같은 head/base의 열린 PR, task PR N, PR head E의 CI run, CI_CRITERIA의 기준 run 45616533199로 제한한다.

PR 생성 전(각 1회):
- G1 `git ls-remote origin refs/heads/main` → EXPECTED_BASE_SHA
- G2 `git ls-remote origin refs/heads/codex/auto-09-controlled-read-precheck` → E. 오프라인 `git rev-parse HEAD`도 E여야 한다.
- G3 `gh pr list -R swk3169/MoneyLab --head codex/auto-09-controlled-read-precheck --base main --state open --json number,url` → `[]`

PR 생성: WORK_ORDER N4의 `gh pr create` 1회. `-R swk3169/MoneyLab --base main --head codex/auto-09-controlled-read-precheck --title <확정 제목> --body <확정 본문>`이고, 제목과 본문은 PR_CI Gate Authorization의 문구 그대로 쓴다.

PR 생성 후:
- G4 `gh pr view N -R swk3169/MoneyLab --json number,url,state,isDraft,baseRefName,headRefName,headRefOid,commits,files` 1회 → state OPEN, isDraft false, baseRefName main, headRefName = head branch, headRefOid = E, commits = C1·IMPL·E, files = F
- G5 `gh pr checks N -R swk3169/MoneyLab` 최대 40회
- G6 `gh run list -R swk3169/MoneyLab --branch codex/auto-09-controlled-read-precheck --commit E --json databaseId,name,status,conclusion,headSha` 최대 10회
- G7 F_base: `gh run view 45616533199 -R swk3169/MoneyLab --log-failed` 1회. PR CI 성공 여부와 관계없이 수행한다.
- G8 F_pr:
  - PR head run의 Linux job이 success로 완료되면 F_pr = 빈 집합으로 판정한다.
  - Linux job이 실패로 완료되면 그 완료 run에 대해 `gh run view <run id> -R swk3169/MoneyLab --log-failed` 1회로 F_pr을 얻는다.
- G9 판정 직전 `gh pr view N -R swk3169/MoneyLab --json state,isDraft,headRefOid,mergeable,mergeStateStatus,statusCheckRollup` 1회

대기와 한도:
- 같은 종류의 반복 조회는 최소 60초 간격으로 한다.
- 과거 환경 준비 시간을 포함한 누적 10800초 예산 준수 여부는 미입증으로 유지한다. 이 ERRATA 수락 메시지 이후 COMPLETE 보고까지의 모든 gate 수행 시간에는 별도 추가 상한 6400초를 적용한다. gate 사이 대기와 사용자 승인·권한 창 응답 대기는 제외하고, gate 수행 중 CI 대기는 포함한다. 각 gate의 시작·종료와 누적 사용량을 기록한다. 추가 상한에 도달하면 STOP한다. 이는 과거 예산 준수를 소급 입증하거나 이전 사용량을 지우는 결정이 아니다. FIX·전체 pytest·targeted의 기존 횟수 예산은 변경하지 않는다.
- CI의 pending, queued, in_progress 상태와 `gh pr checks`가 대기 중을 나타내는 정상 응답은 조회 실패로 취급하지 않는다.
- 한도에 도달했는데 필수 check가 완료되지 않았으면 판정을 보류하고 멈춘다.
- CI 수동 실행과 재실행은 금지한다.

### R11. MERGE (NETWORK N5 보완)

merge 전(각 1회):
- H1 `git ls-remote origin refs/heads/main` → EXPECTED_BASE_SHA
- H2 `git ls-remote origin refs/heads/codex/auto-09-controlled-read-precheck` → E
- H3 `gh pr view N -R swk3169/MoneyLab --json state,isDraft,baseRefName,headRefName,headRefOid,commits,files,mergeable,mergeStateStatus,statusCheckRollup` → 다음을 모두 만족해야 한다:
  - state OPEN, isDraft false, baseRefName main, headRefName = head branch
  - headRefOid = E = H2 값
  - commits = C1·IMPL·E, files = F
  - E에 대한 필수 CI `pytest`가 success
  - mergeable MERGEABLE
  - 계약이 요구한 추가 증거를 사용자가 수락함
  - reviewDecision은 §13의 별도 필수 조건이 아니다. 저장소의 다른 강제 요건이 실제로 확인되면 그 근거와 함께 적용한다.

merge 명령(WORK_ORDER N5의 1회): `gh pr merge N -R swk3169/MoneyLab --merge --match-head-commit E`. WORK_ORDER의 금지 옵션과 별도 MERGE 승인 조건을 유지한다.

merge 후(각 1회):
- H4 `gh pr view N -R swk3169/MoneyLab --json state,mergedAt,mergeCommit` → state MERGED, mergeCommit의 SHA를 M으로 기록
- H5 `gh api --method GET repos/swk3169/MoneyLab/commits/M --jq "{sha: .sha, parents: [.parents[].sha], tree: .commit.tree.sha}"` → parents = [EXPECTED_BASE_SHA, E], tree = E의 tree. E가 base의 후손이므로 merge 결과 tree는 E의 tree와 같아야 한다.
- H6 `git ls-remote origin refs/heads/main` → M

### R12. POST_MERGE_AUDIT (NETWORK N6 보완)

기존 `git fetch origin main` 1회를 유지하고, `gh pr view N -R swk3169/MoneyLab --json state,mergeCommit` 1회를 추가로 허용한다. state MERGED와 mergeCommit SHA = M을 다시 확인한다.

### R13. 공통 STOP

다음 가운데 하나라도 나오면 즉시 STOP하고 재시도, 명령 변형, 자동 복구를 하지 않는다:
- 인증·통신·명령 구문 오류
- 응답 불명, 확인할 수 없는 상태
- 기대값과 불일치
- 허용 횟수 초과
- G3에서 열린 PR이 있음
- 완료된 필수 check의 실패
- F_pr에 F_base 밖의 ID가 있음(새 Linux 회귀)
- DENY, 예상 밖 ASK

읽기 조회 권한에는 CI 수동 실행·재실행, PR 수정·종료·재오픈, push, merge가 포함되지 않는다.

### R14. EXPECTED_ASK, REQUIRED_EVIDENCE, REQUIRED_REPORT 보완

- EXPECTED_ASK 추가: ERRATA_COMMIT의 ERRATA-001.md Write와 `git commit`, PUSH_ERRATA의 `git push`.
- REQUIRED_EVIDENCE 추가:
  - GIT_VERIFIABLE: E의 SHA·parent·tree, ERRATA-001.md의 작업·index·commit SHA-256, M의 parent1·parent2·tree
  - CLAUDE_REPORTED: R4의 직전·직후 W·S 대조, N3a 사전·사후 조회 결과
- REQUIRED_REPORT 추가:
  - ERRATA_COMMIT: R4 각 항목, E의 SHA·parent·tree
  - PUSH_ERRATA: 사전·사후 원격 SHA와 push 출력·종료 상태
  - PR_CI·MERGE·POST_MERGE_AUDIT: R10–R12의 조회 결과

## CONSTRAINTS

- 바꾸지 않는 것: ALLOWED_FILES, DESIGN_CONTRACT D1–D12, TEST_GATES, FIX_RULES의 수정·STOP 규칙, BUDGET_FIX·BUDGET_PYTEST·BUDGET_TARGETED·BUDGET_SAME_FAIL 횟수 예산, CI_CRITERIA의 판정 기준(R10에 적은 보완 외), 구현 9개 파일, WORK_ORDER.md, PRESERVATION_CHECK의 허용 차이.
- 시간 예산은 R10의 시간 조항을 따른다. 누적 10800초 예산 준수 여부는 미입증으로 유지하며, 이 ERRATA의 추가 상한은 과거 사용량을 지우거나 과거 준수를 소급 입증하지 않는다.
- 이 ERRATA는 CI 수동 실행·재실행, PR 수정·종료·재오픈, E 이외의 추가 커밋, force push, 이력 재작성을 허용하지 않는다.
- ERRATA_COMMIT, PUSH_ERRATA, PR_CI, MERGE, POST_MERGE_AUDIT는 각각 별도의 Gate Authorization이 필요하다. 이 문서의 수락만으로는 어떤 실행도 승인되지 않는다.
- 기존 기록을 유지한다:
  - CLEAN_COMMIT_E2E 종료 코드 3건 미입증과 관리자 한정 수락
  - 비차단 한계 1–7
  - 과거 STOP·DENY·지시 위반·DEVIATION
  - DLL 실패 원인 미확정과 CodeIntegrity 조회 권한 거절
  - 누적 10800초 시간 예산 준수 미입증
  - 연구 공개 백업 보류
