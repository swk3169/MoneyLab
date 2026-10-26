# Work Order: PUBLIC-RELEASE-01 — 포트폴리오 공개 준비와 PRIVATE → PUBLIC 전환

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/PUBLIC-RELEASE-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: PUBLIC-RELEASE-01
TASK_ID: PUBLIC-RELEASE-01
TITLE: MoneyLab을 SAP Korea Labs 지원용 포트폴리오로 공개하기 위한 준비와 별도 승인된 visibility 전환
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 7d335973971059ea3d6f44dfd4cb3be8ad407d17
CANONICAL_BASE_TREE: 52521a9bdfb105469dc501ae90e1911b47323d08
CANONICAL_BASE_PARENTS: 2a184b2d3f44d868590d65f85f7dfd9d09fe7988 9c8518b398ee066aae8afed4df1defe4625ad7df
REPOSITORY: swk3169/MoneyLab
TARGET_BRANCH: chore/public-release-01
TARGET_WORKTREE: C:/MoneyLab-public-release-01
WORKSPACE_SETUP: REQUIRED (`git fetch origin main` 1회로 base를 local에 받고, base에서 branch·worktree를 만들고 이 파일을 C1로 발행한다. 새 worktree에 `.venv`나 junction을 만들지 않는다)
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit

## GATE_SEQUENCE

GATE_SEQUENCE: DISCOVERY_INVENTORY -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> HISTORY_SECURITY_AUDIT -> GITHUB_SURFACE_AUDIT -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> GITHUB_METADATA_UPDATE (OPTIONAL, 별도 승인) -> PREPUBLIC_AUDIT -> VISIBILITY_CHANGE -> POST_PUBLIC_AUDIT -> COMPLETE

DISCOVERY_INVENTORY(PASS_WITH_BLOCKER)와 CONTRACT_REVIEW(PASS)는 이 파일 발행 전에 끝났다.

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 명시적 Gate Authorization(`GATE_AUTHORIZATION: PUBLIC-RELEASE-01 <GATE> WO@<C1>` 또는 ERRATA 포함 형식)으로 한 gate씩만 앞으로 간다. 각 gate의 보고 후 멈춘다.
- rollback은 명시적 승인으로 IMPLEMENTATION까지만 한다.
- COMMIT 이후 수정은 새 commit으로 한다. amend하지 않는다.
- GITHUB_METADATA_UPDATE는 선택 gate다. 별도 승인이 없으면 SKIPPED로 기록하고 PREPUBLIC_AUDIT로 갈 수 있다. SKIPPED는 publication blocker가 아니다.
- VISIBILITY_CHANGE는 항상 별도 승인이 필요하다. 다른 gate의 승인, 이 Work Order, ERRATA는 VISIBILITY_CHANGE 승인이 아니다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다. guard deny는 우회하지 않는다.

## GOAL

GOAL: MoneyLab을 SAP Korea Labs 지원용 software engineering / quantitative research 포트폴리오로 안전하게 공개할 수 있는 상태로 준비한다. 모든 publication blocker가 해소되고 PREPUBLIC_AUDIT가 PASS한 뒤, 별도 명시적 승인이 있을 때만 GitHub visibility를 PRIVATE에서 PUBLIC으로 바꾼다.

## TASK_EXCLUSIONS

TASK_EXCLUSIONS (이 task의 범위가 아님):
- BT4 implementation, BT4 freeze, BT4 validation 실행, BT4 문서 변경 (BT4-DESIGN-01은 COMPLETE이며 수정하지 않는다)
- trading strategy 변경, 새 scientific simulation·calibration, profitability validation, live trading
- credential 우회, guard·settings·hook 약화나 변경
- history rewrite (D3, 그리고 아래 SECRET_CANDIDATE_HANDLING의 별도 remediation 승인 경우 외)
- stale remote branch 정리 (D6)
- memory·scratchpad 변경

## BACKGROUND

BACKGROUND:
- DISCOVERY_INVENTORY (2026-10-26, mutation 0): CURRENT_TREE_SECRET_CANDIDATE = 0 (CLAUDE_REPORTED). HISTORY_SECRET_AUDIT = INCOMPLETE_GUARD_BLOCKED (`env` guard rule이 이력 파일 이름 검사 명령을 deny). visibility PRIVATE, license 없음(`licenseInfo: null`), LICENSE·COPYING·NOTICE 없음. binary·raw market data·연구 산출물 없음. JSON fixture 11개(합성 9개, Cloudflare HTTP 451 실제 캡처 2개). remote branch 24개와 `refs/pull/*` 26개는 모두 main의 조상이다. 그 이력에서 삭제·이름 변경 경로 0개.
- CONTRACT_REVIEW (2026-10-26): PASS. 사전 확인으로 merge commit 포함(`-m`) 삭제 경로 0개를 관찰했다(GIT_VERIFIABLE, 감사로 인정하지 않음). `env` 규칙은 ask가 아니라 deny다.
- README는 2026-10-18 기준 상태표·구조 설명이 오래되었다(MC-V06, BT-3e 미반영, `backtest/ (예정)`). `pyproject.toml`의 version 0.3.0과 description이 오래되었다.

## USER_DECISIONS

USER_DECISIONS (2026-10-26, 사용자 확정):
- D1 LICENSE = MIT
- D2 HISTORY_PATH_COVERAGE_METHOD = APPROVED_AS_PREREGISTERED_AUDIT. 단, 실제 실행은 guard 허용 범위 안에서만 가능하며 guard deny가 발생하면 우회하지 않는다.
- D3 HISTORICAL_PERSONAL_EMAIL = ACCEPT_EXISTING_HISTORY, NO_HISTORY_REWRITE
- D4 README_PRIMARY_TITLE = "MoneyLab — Quantitative Research & Backtesting Platform"
- D5 GITHUB_SURFACE_AUDIT = REQUIRED_PREPUBLIC_GATE
- D6 STALE_REMOTE_BRANCH_CLEANUP = OUT_OF_SCOPE_FOR_THIS_TASK
- D7 GITHUB_PORTFOLIO_METADATA = IN_SCOPE_BUT_REQUIRES_SEPARATE_AUTHORIZATION

## UNRESOLVED_PRE_IMPLEMENTATION_DECISIONS

UNRESOLVED_PRE_IMPLEMENTATION_DECISIONS (상태: USER_DECISION_REQUIRED_BEFORE_IMPLEMENTATION):
- U-A MIT copyright holder/year: MIT 원문의 `Copyright (c) <year> <holder>` 줄. Claude가 임의로 정하지 않는다.
- U-B `pyproject.toml` license metadata 표현: 현재 `[build-system] requires = ["setuptools>=69"]`이다. SPDX 문자열(`license = "MIT"`), 표 형식(`license = {text = "MIT"}`), license 필드 무변경(LICENSE 파일만 추가) 중 선택. 어떤 표현의 setuptools 요구 버전도 이 Work Order에서 검증된 사실로 쓰지 않는다(CLAUDE_REPORTED 수준).
- 두 항목은 C1 생성을 막지 않는다. IMPLEMENTATION 전에 사용자 결정을 받고, Work Order 계약을 바꾸는 경우 ERRATA를 쓴다. 결정 없이 IMPLEMENTATION에 들어가지 않는다.

## GUARD_PREFLIGHT_LIMITATION

GUARD_PREFLIGHT_LIMITATION:
- WORKSPACE_SETUP에서 guard implementation의 추가 사전 확인을 위한 read-only shell command가 `protected-path` rule에 의해 DENY되었다.
- 해당 command는 재시도하지 않았으며, 다른 tool·path를 이용한 동일 목적의 우회도 수행하지 않았다.
- 따라서 HISTORY_SECURITY_AUDIT·GITHUB_SURFACE_AUDIT에 사전등록된 명령이 실제 guard policy와 충돌하지 않는다는 것을 WORKSPACE_SETUP 단계에서 완전히 증명하지 않는다.
- 향후 감사 gate에서:
  - command가 허용되면 계약대로 진행한다.
  - ask이면 그 command에 대해서만 user one-time authorization 후 진행할 수 있다.
  - deny이면 우회하지 않고 즉시 해당 gate = BLOCKED로 멈춘다.
  - deny 발생 후 검사 방법을 즉석에서 바꾸지 않는다.
  - 필요한 계약 변경은 별도 ERRATA + user authorization으로 한다.

## PUBLICATION_BLOCKERS

PUBLICATION_BLOCKERS:
- B1 HISTORY_SECRET_AUDIT = INCOMPLETE_GUARD_BLOCKED. 해소: HISTORY_SECURITY_AUDIT = PASS.
- B2 repository license = UNDECIDED → D1로 MIT 결정됨. 해소: MIT LICENSE가 merge된 main에 있고 U-A가 결정되어 반영됨.
- B3 GitHub-hosted surface 미감사. 해소: GITHUB_SURFACE_AUDIT = PASS.
- B4 SECRET_CANDIDATE가 하나라도 미해결(어느 감사에서든). 해소: 0건.
- VISIBILITY_CHANGE 전제(전부 충족해야 함): current-tree security audit PASS(PREPUBLIC_AUDIT 안에서), HISTORY_SECURITY_AUDIT PASS, GITHUB_SURFACE_AUDIT PASS, 미해결 SECRET_CANDIDATE 0, license 결정 완료와 merge 확인, PREPUBLIC_AUDIT PASS, merge된 canonical main 확인, 명시적 VISIBILITY_CHANGE authorization. 하나라도 없으면 VISIBILITY_CHANGE = BLOCKED.
- 개인 email의 commit metadata 노출(D3), Claude co-author trailer, stale branch(D6), GITHUB_METADATA_UPDATE SKIPPED는 publication blocker가 아니다.

## SECRET_CANDIDATE_HANDLING

SECRET_CANDIDATE_HANDLING (모든 감사 gate 공통):
- 값을 출력·복사·기록하지 않는다. 위치(commit, path, line 또는 PR·run 번호)와 유형만 기록한다. 분류를 위해 값을 볼 때는 앞 4자 이하로 자른 형태만 출력한다.
- 분류: SECRET_CANDIDATE / FIXTURE_OR_EXAMPLE / FALSE_POSITIVE. 실제 secret 여부가 불명확하면 CONFIRMATION_REQUIRED(= SECRET_CANDIDATE로 취급).
- SECRET_CANDIDATE가 하나라도 있으면 해당 gate = FAIL, VISIBILITY_CHANGE 중단, rotation 필요 여부를 판단해 보고하고 멈춘다.
- history rewrite, PR·comment 삭제, log 삭제는 자동으로 하지 않는다. 별도 remediation authorization(새 Work Order 또는 ACCEPTED ERRATA) 없이는 history·GitHub 기록 mutation을 하지 않는다.

## HISTORY_SECURITY_AUDIT

HISTORY_SECURITY_AUDIT (read-only, D2 사전등록 감사):
- 대상: `BASE = 7d335973971059ea3d6f44dfd4cb3be8ad407d17`에서 닿는 전체 이력. gate 시작 시 `git ls-remote origin refs/heads/main`이 BASE와 다르면 STOP하고 보고한다.
- 출력은 pipe로만 처리한다. 임시 파일·scratchpad를 만들지 않는다. 값은 출력하지 않는다(cut으로 `rev:path:line`만).
- H1 reachability: `git ls-remote origin`의 모든 `refs/heads/*`, `refs/pull/*/head` SHA에 대해 `git merge-base --is-ancestor <sha> BASE`. 모두 성립해야 공개 이력 = BASE 이력이다. 성립하지 않는 ref가 있으면 그 ref의 이력도 H2–H5 대상에 넣는다(대상 확장은 ERRATA 없이 허용, 명령 형식은 동일).
- H2 path-set coverage: `git log -m --format= --name-only BASE | sort -u`와 `git ls-tree -r --name-only BASE | sort`를 `comm -23`로 비교한다. 이력에만 있는 경로 수 = 0이어야 한다. 0이 아니면 그 경로 목록(경로 이름만)을 보고하고 각 경로의 이력 내용을 H4로 검사한다.
- H3 delete/rename: `git log -m --diff-filter=D --format= --name-only BASE`와 `git log -m -M --diff-filter=R --format= --name-status BASE`의 줄 수를 기록한다.
- H4 content scan: `git rev-list BASE`의 모든 commit에 대해 `git grep -I -n -E '<P>' <commits> | cut -d: -f1-3`. 패턴 P(사전등록):
  - P1 private key block: `BEGIN [A-Z ]*PRIVATE KEY`
  - P2 AWS access key id: `AKIA[0-9A-Z]{16}`
  - P3 GitHub token: `gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}`
  - P4 Slack token: `xox[baprs]-[A-Za-z0-9-]{10,}`
  - P5 Google API key: `AIza[0-9A-Za-z_-]{35}`
  - P6 sk-style key: `sk-(ant-)?[A-Za-z0-9_-]{20,}`
  - P7 JWT: `eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}`
  - P8 bearer: `Bearer [A-Za-z0-9._-]{20,}`
  - P9 URL credential: `[a-z]+://[^/ :@]+:[^/ @]+@`
  - P10 64-hex: `0x[0-9a-fA-F]{64}`
  - P11 assignment: `(api[_-]?key|secret[_-]?key|access[_-]?key|private[_-]?key|token|password|passwd|secret)[A-Za-z_]*["']?[[:space:]]*[:=][[:space:]]*["'][^"' ]{8,}["']`
  - P12 Windows user profile path: `[Cc]:[\\/]+[Uu]sers[\\/]+`
- H5 commit message scan: `git log --format=%H -E --grep='<P>' BASE` (P1–P11), commit SHA만 출력.
- 분류: SECRET_CANDIDATE_HANDLING. DISCOVERY에서 확인된 test 입력(`tests/test_repo_hygiene.py` 탐지기 test)과 합성 fixture ID는 FIXTURE_OR_EXAMPLE 후보이며, 같은 path·line이 이력에서도 같은 성격인지 확인한다.
- PASS 조건: H1 확인, H2 이력 전용 경로 0(또는 그 경로가 모두 H4에서 SECRET_CANDIDATE 0), H4·H5 SECRET_CANDIDATE 0, 모든 사전등록 명령 실행 완료.
- guard: GUARD_PREFLIGHT_LIMITATION을 따른다. 사전등록 명령 중 하나라도 deny되면 HISTORY_SECURITY_AUDIT = BLOCKED.

## GITHUB_SURFACE_AUDIT

GITHUB_SURFACE_AUDIT (read-only, D5 필수 gate):
- 대상: Public 전환 시 노출되는 GitHub-hosted surface.
  - S1 PR #1 이후 전체: title, body (`gh pr list --state all --limit 200 --json number,title,body`), issue comments (`gh api repos/swk3169/MoneyLab/issues/comments --paginate`), review comments (`gh api repos/swk3169/MoneyLab/pulls/comments --paginate`), reviews (`gh api repos/swk3169/MoneyLab/pulls/<n>/reviews`)
  - S2 issues: `gh issue list --state all --limit 200 --json number,title,body`
  - S3 Actions: `gh run list --limit 1000 --json databaseId,event,headBranch,conclusion`, 각 run의 `gh run view <id> --log`, artifacts (`gh api repos/swk3169/MoneyLab/actions/artifacts`)
  - S4 releases·tags (`gh api repos/swk3169/MoneyLab/releases`, `git ls-remote --tags origin`), wiki 활성 여부 (`gh repo view swk3169/MoneyLab --json hasWikiEnabled`), deployments (`gh api repos/swk3169/MoneyLab/deployments`), environments (`gh api repos/swk3169/MoneyLab/environments`), pages (`gh api repos/swk3169/MoneyLab/pages`, 404 허용)
- 검사: HISTORY_SECURITY_AUDIT의 P1–P12를 각 출력에 pipe로 적용한다. 위치(PR·comment·run 번호)와 유형만 기록한다. 추가로 개인 email·전화번호·비문서용 IP를 REVIEW 항목으로 센다.
- 분류: SECRET_CANDIDATE는 SECRET_CANDIDATE_HANDLING. local 개발 경로(`C:/MoneyLab…`)는 LOCAL_ENVIRONMENT_INFORMATION(허용). commit metadata 밖의 개인 정보는 REVIEW_REQUIRED(사용자 결정).
- mutation 0: PR·comment·issue·log·artifact를 수정·삭제하지 않는다.
- guard: `gh api` 등 ask 명령은 그 명령에 대해서만 one-time authorization 후 실행한다. deny면 BLOCKED.
- PASS 조건: S1–S4 실행 완료, SECRET_CANDIDATE 0, REVIEW_REQUIRED 항목에 대한 사용자 결정 기록.
- MERGE 이후 새로 생긴 PR(이 task의 PR)과 그 CI log는 PREPUBLIC_AUDIT에서 같은 방법으로 다시 검사한다.

## LICENSE_DECISION

LICENSE_DECISION:
- MIT (D1). LICENSE 파일은 IMPLEMENTATION에서만 만든다(`A LICENSE`). 본문은 표준 MIT 원문이며, copyright 줄은 U-A 결정을 따른다.
- `pyproject.toml`의 license 표현은 U-B 결정을 따른다.
- 범위: MoneyLab 자체 source code. dependency는 설치형이며 저장소에 포함되지 않는다. 저장소에 포함된 third-party 자료는 Cloudflare 451 응답 캡처 2개뿐이다.

## README_CONTRACT

README_CONTRACT (IMPLEMENTATION, `M README.md`):
- H1: D4 문구 그대로 "MoneyLab — Quantitative Research & Backtesting Platform".
- 첫 화면: Python, Statistical Testing, Monte Carlo Simulation, CI, AI-assisted Engineering 성격을 빠르게 보여준다.
- 절 구성(순서 권장): 한 줄 정의; Problem / Motivation; Architecture; Engineering Highlights; Research & Validation Methodology; AI-assisted Engineering Workflow; Current Project Status; Limitations / What this project is NOT; Repository Structure; Tests / CI; Getting Started; License.
- 금지: live trading system이라고 주장, profitability 주장, production-ready 주장, BT4 implementation 완료 주장, "Trading System" 같은 실거래 시스템 인상을 주는 부제.
- 실거래 기능(실제 주문, 지갑, 개인키, 자동매매)은 구현·활성화되어 있지 않다고 명시한다.
- 기존 README의 버전별 기록(v0.1–v0.4)은 정보를 삭제하지 않고 README 하위 절 또는 `docs/portfolio_overview.md`로 옮겨 보존한다.
- Polymarket 절 framing: 개발 환경에서 공개 API가 HTTP 451을 반환해 공식 문서 기반 합성 fixture만 썼고, 접근 제한 우회 기능은 의도적으로 구현하지 않았다. 원인을 단정하지 않는다.
- 근거 표시: 상태·수치는 저장소 문서에 있는 것만 쓰고 출처 문서를 링크한다.

## AI_DISCLOSURE_CONTRACT

AI_DISCLOSURE_CONTRACT:
- Co-Authored-By: Claude trailer를 제거하기 위한 history rewrite는 하지 않는다.
- README의 AI-assisted Engineering Workflow 절은 "사람이 설계·승인·최종 판단을 맡고, AI-assisted engineering을 fail-closed guard, CI, 불변 Work Order, gate별 human authorization으로 통제했다"는 사실을 투명하게 설명한다. AI 사용을 숨기거나 축소하지 않고, AI가 프로젝트를 대신 만들었다는 인상도 주지 않는다.
- `CLAUDE.md`, `.claude/**`, `docs/agent_workflow.md`는 수정하지 않고 README에서 링크·설명한다.

## PII_DECISION

PII_DECISION:
- 작성자 이름(commit metadata의 두 표기)은 portfolio identity로 공개를 허용한다.
- 개인 email의 기존 commit metadata 노출은 D3로 수용한다. history rewrite 없음. 이는 publication blocker가 아니다.
- 새 문서(README, LICENSE, portfolio_overview)에는 개인 email·전화번호·주소를 쓰지 않는다. LICENSE의 holder 표기는 U-A를 따른다.

## THIRD_PARTY_DATA_DECISION

THIRD_PARTY_DATA_DECISION:
- Cloudflare HTTP 451 캡처 2개(`tests/fixtures/http_451_cloudflare*.json`)는 유지한다. PUBLIC_SOURCE_LICENSE_UNCLEAR이지만 REVIEW item이며 publication blocker가 아니다. PREPUBLIC_AUDIT에서 client IP 등 개인 정보가 없음을 다시 확인한다.
- 합성 fixture는 출처가 `tests/fixtures/README.md`에 기록되어 있다. 외부 시장 데이터는 저장소에 포함하지 않는다.

## SCIENTIFIC_DISCLOSURE_REQUIREMENTS

SCIENTIFIC_DISCLOSURE_REQUIREMENTS (README와 portfolio_overview에서 정확히 표현):
- MC-V06: MIXED / DESIGN-INFORMATIVE
- BT4 readiness: READY_WITH_CAUTION
- futility boundary: anti-conservative behavior observed (SYNTHETIC, 원인 미확정)
- BT4-DESIGN-01: COMPLETE as design task only
- BT4 freeze: NOT PERFORMED; validation execution: NOT STARTED; BT4 implementation: NOT STARTED
- 백테스트 결과는 합성 데이터 기반이며 수익성의 근거가 아니다(SYNTHETIC / NOT_EVIDENCE)
- v0.4 실데이터 microstructure 결과는 비용 반영 후 REJECT였다는 점을 저장소 문서 근거가 있는 범위에서만 쓴다
- live trading readiness, profitability, production readiness는 주장하지 않는다

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP: `git fetch origin main` 1회(`--prune` 없음, 다른 branch 없음), base 확인, `chore/public-release-01` branch와 `C:/MoneyLab-public-release-01` worktree 생성, 이 파일 최초 생성과 C1 commit
- HISTORY_SECURITY_AUDIT: 위 사전등록 명령의 read-only 실행과 보고만
- GITHUB_SURFACE_AUDIT: 위 사전등록 명령의 read-only 실행과 보고만
- IMPLEMENTATION: U-A·U-B 결정 후 ALLOWED_FILES(IMPLEMENTATION) 생성·수정, TEST_GATES 실행
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, commit 하나(Ci)
- CLEAN_COMMIT_E2E: TEST_GATES와 E2E_GATES만(저장소 쓰기 없음)
- PUSH: `git push -u origin chore/public-release-01` 1회
- PR_CI: PR 하나 생성(base main, head TARGET_BRANCH), CI 결과 read-only 확인
- MERGE: `gh pr merge <n> --merge` 1회(squash·rebase·branch 삭제 없음)
- POST_MERGE_AUDIT: `git ls-remote`와 GitHub API GET으로 merge 구조·내용 확인. fetch는 `git fetch origin main`만, 필요할 때 1회
- GITHUB_METADATA_UPDATE (OPTIONAL, 별도 승인): `gh repo edit swk3169/MoneyLab --description "<승인 문구>"`와 `--add-topic <승인 topic>`만. 승인 문구·topic은 그 gate 승인에 명시되어야 한다. visibility와 섞지 않는다. 승인이 없으면 SKIPPED
- PREPUBLIC_AUDIT: read-only 감사만
- VISIBILITY_CHANGE: 아래 VISIBILITY_CHANGE_CONTRACT의 명령 1회만
- POST_PUBLIC_AUDIT: read-only 확인만
- COMPLETE: 최종 보고만(marker 파일·tag·comment 없음)

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull
- hooks·settings·`.claude` 변경, guard 우회, guard deny 후 같은 목적의 다른 명령·도구·경로 사용, 차단된 명령을 사용자 shell에서 실행하도록 요청
- 외부 scanner·dependency 설치, 새 worktree의 `.venv`·junction 생성
- history rewrite, PR·comment·issue·log·artifact 수정이나 삭제 (SECRET_CANDIDATE_HANDLING의 별도 remediation 승인 경우 외)
- remote branch 삭제(D6), `refs/pull/*` mutation
- VISIBILITY_CHANGE 외의 visibility 변경, GITHUB_METADATA_UPDATE 외의 GitHub settings 변경
- BT4 문서·코드 변경, simulation, calibration, MC 재실행
- memory·scratchpad 변경, 감사용 임시 파일 생성
- 다른 branch·worktree·untracked·ignored·reference 산출물 정리

## ALLOWED_FILES

ALLOWED_FILES (WORKSPACE_SETUP, C1 전용):
- A docs/tasks/PUBLIC-RELEASE-01/WORK_ORDER.md

ALLOWED_FILES (ERRATA, Ce 전용):
- A docs/tasks/PUBLIC-RELEASE-01/ERRATA-<NNN>.md (사용자가 ACCEPT한 경우만)

ALLOWED_FILES (IMPLEMENTATION, Ci):
- M README.md
- M pyproject.toml (`[project]`의 version, description, license 표현만. `[build-system]`, dependencies, scripts, tool 설정은 바꾸지 않는다)
- A LICENSE
- A docs/portfolio_overview.md (선택)

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/PUBLIC-RELEASE-01/** (C1·Ce의 최초 생성만 예외)
- 기존 docs/tasks/** (다른 task)
- CLAUDE.md
- .claude/**
- .github/**
- src/**
- tests/**
- configs/**
- docs/agent_workflow.md
- 기존 scientific evidence 문서와 설계·사전등록 문서: docs/backtest_design.md, docs/backtest_bt2b3_metrics.md, docs/backtest_bt2b4_metrics.md, docs/research_v04_preregistration.md, docs/research_v05_preregistration_draft.md, docs/research_v06_preregistration_draft.md, docs/research_bt4_01_evidence_review.md, docs/live_execution_design.md, docs/incidents/**
- BT4 문서: docs/bt4_design_01.md, docs/tasks/BT4-DESIGN-01/**, docs/tasks/BT4-RESEARCH-01/**
- .gitignore
- .gitattributes
- env 계열 파일 전부(이름이 `.env`로 시작하는 파일, 예시 파일 포함)
- requirements.txt, requirements-dev.txt
- data/**

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가)

## TEST_GATES

TEST_GATES:
- Python: 기존 검증된 venv `C:/MoneyLab-mc-v06/.venv/Scripts/python.exe`. 환경변수 `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=C:/MoneyLab-public-release-01/src`. 새 worktree에 `.venv`·junction을 만들지 않는다.
- 실행 전에 `moneylab.__file__`로 import source가 `C:/MoneyLab-public-release-01/src` 아래인지 확인한다. 아니면 멈춘다.
- canonical local full suite: 작업 디렉터리 `C:/MoneyLab-public-release-01`에서 `python -B -m pytest -rsx -p no:cacheprovider`. 결과를 그대로 기록한다. collected·selected 줄을 포함해 출력 머리와 요약을 모두 캡처한다.
- `git diff --check` clean; 변경 파일 집합 = ALLOWED_FILES(IMPLEMENTATION)
- 산출물 점검: README H1 = D4 문구, README_CONTRACT 금지 표현 없음, SCIENTIFIC_DISCLOSURE_REQUIREMENTS 반영, LICENSE가 MIT 원문이고 U-A 반영, `pyproject.toml` 변경이 허용 필드뿐, 새 문서에 secret·개인 email 없음(P1–P12)

## KNOWN_ENVIRONMENT_TOPOLOGY

KNOWN_ENVIRONMENT_TOPOLOGY:
- 다음 두 test는 `CLAUDE_PROJECT_DIR=<repository root>`를 설정하고 `<repository root>/.venv/Scripts/python.exe`를 실행한다(`tests/test_agent_guard.py`의 `run_wrapped`):
  - `tests/test_agent_guard.py::test_wrapper_passes_real_decisions_through`
  - `tests/test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0`
- 이 Work Order는 새 worktree에 `.venv` 생성을 금지하므로, local full suite에서 이 두 test의 failure가 예상된다.
- 이 failure를 PASS로 표현하지 않는다. LOCAL_TEST_RESULT는 실제 결과 그대로 기록한다.

## E2E_GATES

E2E_GATES (CLEAN_COMMIT_E2E):
- clean implementation commit에서 TEST_GATES를 실행한다.
- gate-level acceptance는 다음을 모두 만족할 때만 가능하다. 이 조건은 local test를 PASS로 재분류하는 규칙이 아니다:
  - A. local failed test가 정확히 KNOWN_ENVIRONMENT_TOPOLOGY의 두 test뿐이다.
  - B. 두 failure 모두 `C:/MoneyLab-public-release-01/.venv/Scripts/python.exe` 부재라는 같은 환경 의존 원인이다.
  - C. 그 외 failed = 0
  - D. errors = 0
  - E. 예상하지 못한 collection failure = 0
  - F. collected, selected, deselected, passed, failed, errors, skipped, xfailed, xpassed 수를 모두 기록한다.
- 하나라도 다르면 CLEAN_COMMIT_E2E = FAIL 또는 BLOCKED.
- 보고에는 `LOCAL_TEST_RESULT: <실제 결과>, not PASS`(failure가 있을 때)와 `DEFERRED_STATUS: ENVIRONMENT_DEPENDENT_DEFERRED_TO_PR_CI`를 함께 쓴다.

## PR_CI_CONDITIONS

PR_CI_CONDITIONS:
- 판정 대상: MERGE 시점 PR head commit에 대해 `pull_request` event로 실행된 `ci-tests` run.
- 직접 증거 우선: CI log에 KNOWN_ENVIRONMENT_TOPOLOGY의 두 test가 개별 PASSED로 나오면 그것을 쓴다(`EVIDENCE_TYPE: DIRECT_CI_EVIDENCE`). workflow나 check가 green이라는 사실만으로 개별 test의 PASSED를 추론하지 않는다.
- pytest 출력 형식 때문에 개별 PASSED 줄이 없으면, 각 test마다 아래 E1–E9를 모두 확인할 수 있을 때만 PASSED를 eliminative CI evidence로 인정한다(`EVIDENCE_TYPE: ELIMINATIVE_CI_EVIDENCE`):
  - E1. canonical pytest job이 success이고, pytest 요약에서 failed = 0, errors = 0이다.
  - E2. collected, selected, deselected, passed, skipped, xfailed, xpassed, failed, errors 수가 CI log에서 확인되고 selected = passed + skipped + xfailed + xpassed + failed + errors가 성립한다.
  - E3. 해당 test가 평가 대상 commit의 canonical collection(`testpaths`)에 존재한다. 확인 방법: 그 commit의 소스 확인, 또는 cache·bytecode를 만들지 않는 local `pytest --collect-only -q -p no:cacheprovider`(`PYTHONDONTWRITEBYTECODE=1`, `python -B`).
  - E4. CI log의 SKIPPED 목록에 해당 test가 없다.
  - E5. CI log의 XFAIL·XPASS 목록에 해당 test가 없다.
  - E6. 해당 test에 deselection 대상 marker가 없다(함수 decorator, class, module의 `pytestmark` 모두 확인).
  - E7. 다른 selection exclusion이 없다: `pyproject.toml`의 `addopts`·`testpaths`, CI 명령의 추가 인자(`-k`, `-m`, `--deselect`, `--ignore`), `conftest.py`의 collection hook(`pytest_collection_modifyitems`, `pytest_ignore_collect` 등). 이 task는 `pyproject.toml`을 바꾸므로 `[tool.pytest.ini_options]`가 base와 같은지 확인한다.
  - E8. CI log의 FAILED·ERROR 목록에 해당 test가 없다.
  - E9 (보조 증거). 같은 commit 내용의 local CLEAN_COMMIT_E2E와 CI의 count가 대조된다: local failed가 정확히 두 test였고, CI passed가 local passed보다 정확히 2 많으며, skipped·deselected·xfailed 수와 목록이 일치한다. E9는 E1–E8을 대신하지 않는다.
- 하나라도 확인할 수 없으면 NOT_RESOLVED, PR_CI = BLOCKED.
- 두 test 중 하나라도 CI에서 failed나 error이면 PR_CI = FAIL. skipped이면 NOT_RESOLVED. 어느 경우든 MERGE 전에 멈춘다.
- PR 본문에 local test를 PASS로 쓰지 않는다. merge가 이 gate에서 승인되지 않았음을 쓴다.

## POST_MERGE_AUDIT

POST_MERGE_AUDIT:
- remote main = 새 merge commit, parent = (BASE, Ci) 순서, base 대비 변경 파일 = Ci의 파일 집합과 이 task의 C1(·Ce) 파일, 각 blob이 Ci와 같음.
- remote task branch 유지, PR state MERGED, local task worktree는 Ci 유지(main으로 전환하지 않음).

## GITHUB_METADATA_UPDATE

GITHUB_METADATA_UPDATE (OPTIONAL, D7):
- 별도 사용자 승인이 있을 때만 실행한다. 승인에는 정확한 description 문구와 topic 목록이 있어야 한다.
- 허용: repository description, topics. homepage, visibility, 기본 branch, feature 설정(wiki·issues 등), branch protection은 바꾸지 않는다.
- 문구는 README_CONTRACT의 금지 표현을 따른다.
- 실행 후 `gh repo view swk3169/MoneyLab --json description,repositoryTopics,visibility`로 확인하고 visibility가 PRIVATE 그대로임을 보고한다.
- 승인이 없으면 SKIPPED. SKIPPED는 publication blocker가 아니다.

## PREPUBLIC_AUDIT

PREPUBLIC_AUDIT (read-only, VISIBILITY_CHANGE 직전):
- remote main SHA를 `git ls-remote`로 확인하고 그것이 POST_MERGE_AUDIT의 merge commit과 같음을 확인한다.
- current-tree security audit: remote main tree에 P1–P12를 적용, SECRET_CANDIDATE 0.
- 새 이력 범위: BASE 이후 추가된 commit(C1, Ce, Ci, merge commit)에 H4·H5를 적용, SECRET_CANDIDATE 0.
- 이 task의 PR과 그 CI log에 GITHUB_SURFACE_AUDIT 방법을 적용, SECRET_CANDIDATE 0.
- HISTORY_SECURITY_AUDIT = PASS, GITHUB_SURFACE_AUDIT = PASS 기록 확인.
- license: remote main에 LICENSE(MIT, U-A 반영) 존재, `gh repo view --json licenseInfo` 관찰값 기록.
- README: H1 = D4, 금지 표현 없음, SCIENTIFIC_DISCLOSURE_REQUIREMENTS 반영.
- Cloudflare 451 캡처 2개에 client IP·개인 정보 없음.
- 미해결 SECRET_CANDIDATE 0, PUBLICATION_BLOCKERS B1–B4 모두 해소.
- visibility가 아직 PRIVATE임을 확인한다.
- 하나라도 충족하지 않으면 PREPUBLIC_AUDIT = FAIL/BLOCKED이고 VISIBILITY_CHANGE = BLOCKED.

## VISIBILITY_CHANGE_CONTRACT

VISIBILITY_CHANGE_CONTRACT:
- 전제: PREPUBLIC_AUDIT = PASS, PUBLICATION_BLOCKERS 모두 해소, remote main이 PREPUBLIC_AUDIT에서 확인한 SHA와 같음(실행 직전 `git ls-remote`로 재확인), 별도 명시적 Gate Authorization.
- 최대 범위: 명령 1회 `gh repo edit swk3169/MoneyLab --visibility public --accept-visibility-change-consequences`. 다른 flag나 설정 변경을 함께 하지 않는다.
- 실패하면 재시도하거나 다른 방법을 쓰지 않고 원인을 보고하고 멈춘다.
- 보고에는 Public 전환 후 노출된 내용은 다시 PRIVATE로 바꿔도 회수되지 않는다는 점(cache, fork, clone 가능성)을 적는다.
- 자동 실행하지 않는다.

## POST_PUBLIC_AUDIT

POST_PUBLIC_AUDIT (read-only):
- `gh repo view swk3169/MoneyLab --json visibility,defaultBranchRef,licenseInfo,description,repositoryTopics`: visibility = PUBLIC, 기본 branch main.
- `git ls-remote origin refs/heads/main` = PREPUBLIC_AUDIT에서 확인한 SHA.
- 인증 없는 접근 확인: `curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/swk3169/MoneyLab` = 200 (GET 1회).
- 다른 repository 설정, branch, PR이 바뀌지 않았음을 확인한다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·Ce·Ci·merge commit SHA·tree·parent, 파일 sha256, commit 파일 집합, 이력 감사의 path·count
- GITHUB_VERIFIABLE: PR metadata, visibility, licenseInfo, description·topics, run metadata
- CLAUDE_REPORTED: local pytest 결과, 감사 분류, E1–E9 결합 판정
- INDEPENDENT: GitHub CI run conclusion과 CI log의 수치·목록, 사용자 확인
- 실제 secret 값은 어떤 증거에도 복사하지 않는다.

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256, ACCEPTED_ERRATA
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 감사 gate: 실행한 사전등록 명령 목록, 결과 count, SECRET_CANDIDATE 수, REVIEW 항목, guard 결과(allow/ask/deny)
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES, mutation 수
- <GATE> 판정과 다음 gate

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, Work Order sha256 불일치, remote main이 기대값과 다름
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기와 base 상태 불일치
- guard deny, 권한 창 거절
- 테스트 실패·에러(KNOWN_ENVIRONMENT_TOPOLOGY의 두 test 제외, E2E_GATES 규칙 적용), hard gate 불일치
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일
- SECRET_CANDIDATE 발견
- U-A·U-B 미결정 상태에서 IMPLEMENTATION 진입 요구
- VISIBILITY_CHANGE 전제 중 하나라도 불충족
