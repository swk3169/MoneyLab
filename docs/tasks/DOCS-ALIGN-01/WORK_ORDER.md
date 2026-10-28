# Work Order: DOCS-ALIGN-01 — ARCHITECTURE/README alignment with knowledge, context and supervisor

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/DOCS-ALIGN-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

이 파일이 계약의 유일한 출처다. 대화 기억이나 채팅 보고서에 의존하지 않는다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: DOCS-ALIGN-01
TASK_ID: DOCS-ALIGN-01
TITLE: ARCHITECTURE/README alignment with knowledge, context and supervisor
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 0848cfc6ddf04d7ebdeb5d5e66de47ee1760c9cf
CANONICAL_BASE_TREE: b364858178d0a1b5e3f861b210866e51abe20aa1
BASE_BLOBS: ARCHITECTURE.md be56b5b0449e617eb32a71aef2a03b04aaf6c661 (229 lines, LF, final newline), README.md c2c268d6caa63720e839e2f3fa548a7f375df482 (529 lines, LF, final newline)
TARGET_BRANCH: docs/docs-align-01
TARGET_WORKTREE: C:/MoneyLab-docs-align-01
SOURCE_WORKTREE: C:/MoneyLab-mc-v06 (WORKSPACE_SETUP 명령을 실행하는 기존 worktree. 파일·index·branch를 바꾸지 않는다.)
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
PRIOR_GATES: DESIGN_INVESTIGATION = DISCOVERY_COMPLETED, CONTRACT_REVIEW = 완료(보완 포함). 모두 채팅, C1 이전.
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (squash/rebase merge 금지: 계약 커밋이 구현보다 먼저인 이력을 보존)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- forward only one gate with explicit Gate Authorization (`GATE_AUTHORIZATION: DOCS-ALIGN-01 <GATE> WO@<C1 commit>`)
- 각 gate의 보고 후 멈춘다. 이전 gate의 승인이나 이 Work Order 자체는 다음 gate의 승인이 아니다.
- rollback only to IMPLEMENTATION with explicit authorization
- after COMMIT, fixes use a new commit; never amend
- no skipping
- 역사적 BLOCKED 결과를 PASS로 바꿔 쓰지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다. guard deny는 우회하지 않는다. 이 Work Order는 새 governance 권한을 만들지 않는다.

## GOAL

GOAL: ARCHITECTURE.md와 README.md를 main에 merge된 KNOWLEDGE-WIKI-01, CONTEXT-ENGINE-02, SUPERVISOR-01 구현 사실에 맞춘다. 직접 충돌(ARCHITECTURE.md §8)을 고치고, 누락(ARCHITECTURE.md §3 구성요소 표·의존 관계, §7 저장소 구조, README.md 상태 표·Architecture·저장소 구조)을 최소한으로 보완한다.

## BACKGROUND

BACKGROUND:
- KNOWLEDGE-WIKI-01은 PR #30(merge 311ecc7af4829c704289402b695925822005e821), CONTEXT-ENGINE-02는 PR #31(merge 56743bfb6c5544ef1298b3912d3e46693c60be41), SUPERVISOR-01은 PR #32(merge 0848cfc6ddf04d7ebdeb5d5e66de47ee1760c9cf)로 main에 들어갔다.
- 세 Work Order는 모두 README.md·ARCHITECTURE.md를 PROTECTED로 두었다. 그 결과 ARCHITECTURE.md §8은 구현된 knowledge/context 계층과 supervisor를 `NOT_IMPLEMENTED`로 적고 있고, ARCHITECTURE.md §3·§7과 README.md는 두 계층을 언급하지 않는다.
- 근거 파일 (CANONICAL_BASE tree에 존재):
  - src/moneylab/knowledge/__init__.py
  - src/moneylab/knowledge/__main__.py
  - src/moneylab/knowledge/context.py
  - src/moneylab/knowledge/load.py
  - src/moneylab/knowledge/model.py
  - src/moneylab/knowledge/query.py
  - src/moneylab/knowledge/validate.py
  - src/moneylab/supervisor/__init__.py
  - src/moneylab/supervisor/__main__.py
  - src/moneylab/supervisor/proposal.py
  - knowledge/SCHEMA.md
  - knowledge/CONTEXT_CONTRACT.md
  - knowledge/records/ (record 7개)
  - docs/supervisor_proposal_contract.md
  - tests/test_knowledge_validate.py
  - tests/test_knowledge_query.py
  - tests/test_knowledge_seed.py
  - tests/test_knowledge_context.py
  - tests/test_supervisor_proposal.py
  - tests/test_supervisor_isolation.py
  - docs/tasks/KNOWLEDGE-WIKI-01/WORK_ORDER.md
  - docs/tasks/CONTEXT-ENGINE-02/WORK_ORDER.md
  - docs/tasks/SUPERVISOR-01/WORK_ORDER.md
- 형식 선례: docs/tasks/DOCS-STATUS-01/WORK_ORDER.md (문구 고정, 기대 결과 정의, 로컬 pytest 대신 PR CI).
- README.md·ARCHITECTURE.md는 사람용 요약이며 권위가 없다(docs/tasks/KNOWLEDGE-WIKI-01/WORK_ORDER.md). 이 task는 권위·권한을 만들지 않는다.
- 사용자 결정: IN_SCOPE = A1, A2, A3, A4, R1, R2, R3. A1 문구 유지, R2 부정문 유지, PR_CI·MERGE는 기존 governance와 개별 Gate Authorization에 따름, 로컬 전체 pytest 비필수(문서 검증 + PR CI Windows 테스트), TARGET_BRANCH와 TARGET_WORKTREE 유지.

## NON_GOALS

NON_GOALS:
- ARCHITECTURE.md §1 Current scope 변경(A5)
- D27: docs/tasks/README.md §3·docs/tasks/TEMPLATE.md의 PR_CI·MERGE 문구 정리
- ARCHITECTURE.md §9 기존 불일치 1–4 해소
- ARCHITECTURE.md §3 그림, README.md Architecture 그림 재작성
- CE-02 LOW #1–#5 수정
- knowledge record 추가, TOPICS 확장
- SUPERVISOR-02, Policy Engine, Research Worker, LLM Wiki 자동 작성·갱신에 관한 서술
- Project Memory 생성
- CLAUDE.md 수정
- 소스코드·테스트·설정·의존성 변경
- README.md 하단 Appendix(개발 이력) 수정, README.md·ARCHITECTURE.md 재설계

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP:
  A. Gate Authorization이 명시하면 `git fetch origin main`만 실행해 원격 main = CANONICAL_BASE_SHA를 확인한다.
  B. A가 일치하고 TARGET_BRANCH·TARGET_WORKTREE·`docs/tasks/DOCS-ALIGN-01/`이 없을 때만 다음을 진행한다.
  C. SOURCE_WORKTREE에서 `git worktree add -b docs/docs-align-01 C:/MoneyLab-docs-align-01 0848cfc6ddf04d7ebdeb5d5e66de47ee1760c9cf`
  D. `docs/tasks/DOCS-ALIGN-01/WORK_ORDER.md`를 승인 문구 그대로 최초 생성하고, 그 파일만 `git add --`로 stage해 C1 커밋 `docs(task): add DOCS-ALIGN-01 work order`를 만든다.
  E. WORK_ORDER.md의 sha256을 커밋 전후로 보고한다.
- IMPLEMENTATION: ALLOWED_FILES를 DESIGN_CONTRACT E1–E10대로 수정하고 TEST_GATES를 실행한다.
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: `git add -- ARCHITECTURE.md README.md`, 커밋 하나
- CLEAN_COMMIT_E2E: E2E_GATES의 읽기 전용 확인
- PUSH: TARGET_BRANCH 하나만 `git push -u origin docs/docs-align-01`
- PR_CI, MERGE: docs/tasks/README.md §3과 해당 gate의 Gate Authorization이 명시한 범위만. 이 Work Order는 그 권한을 넓히거나 줄이지 않는다.
- POST_MERGE_AUDIT: Gate Authorization이 명시하면 `git fetch origin main`만 실행하고 읽기 전용 구조 감사를 한다.
- COMPLETE: 최종 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune, pull
- hooks·settings·.claude 변경 또는 guard 우회, git config 변경
- 다른 branch·worktree·untracked·ignored·reference 산출물·egg-info·외부 venv·scratchpad 정리·변경
- `.venv` 생성·설치·변경, 패키지 설치
- APPROVED_TEXT 재작성, E1–E8 밖 편집
- 미구현 기능을 계획되었거나 구현된 것으로 쓰는 것, supervisor·knowledge에 승인·실행·dispatch 권한이 있는 것처럼 쓰는 것, 수익성·live readiness 시사
- README.md·ARCHITECTURE.md에 C1/Ci SHA, Work Order sha256, gate 내부 세부를 쓰는 것
- 위 fetch·push와 Gate Authorization이 명시한 PR 작업 밖의 네트워크, 거래 API, 자동화 실행

## ALLOWED_FILES

ALLOWED_FILES:
- M ARCHITECTURE.md
- M README.md

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/DOCS-ALIGN-01/** (C1의 WORK_ORDER.md 최초 생성과 ACCEPTED ERRATA 최초 생성만 예외)
- docs/tasks/** (docs/tasks/README.md, docs/tasks/TEMPLATE.md, 다른 task 계약 포함)
- .claude/**
- .github/**
- CLAUDE.md, AGENTS.md, LICENSE, .gitattributes, .gitignore, .env.example
- src/**, tests/**, configs/**, examples/**, data/**, knowledge/**
- docs/** (docs/tasks/** 포함 전체)
- pyproject.toml, requirements.txt, requirements-dev.txt
- ALLOWED_FILES 이외의 모든 경로

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅ (교집합이 있으면 INVALID, IMPLEMENTATION 진입 불가). C1 파일 ∩ ALLOWED_FILES = ∅. 의존성 변경 0. C1·ACCEPTED ERRATA 외 새 파일 0.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- 줄 번호는 모두 BASE_BLOBS 기준이며, E1–E8은 같은 base에 동시에 적용한다(앞선 편집으로 줄 번호를 다시 세지 않는다). "N행 뒤"는 base의 N행과 N+1행 사이에 삽입한다는 뜻이다. 각 블록의 내용은 아래 APPROVED_TEXT의 해당 fenced block에서 여는 fence 줄과 닫는 fence 줄 사이의 줄이다(fence 줄 제외). 각 줄은 LF로 끝난다.
- E1 (A1) ARCHITECTURE.md 208행 `- a knowledge / context layer;`를 삭제한다.
- E2 (A1) ARCHITECTURE.md 211행 `- a supervisor and task generation;`을 APPROVED_TEXT A1(1줄)로 교체한다.
- E3 (A2) ARCHITECTURE.md 87행(`| MC-V06 Monte Carlo study | …`) 뒤에 APPROVED_TEXT A2(2줄)를 삽입한다.
- E4 (A3) ARCHITECTURE.md 72행(`Arrows point from importer to imported package. …`) 뒤에 APPROVED_TEXT A3(2줄)을 삽입한다. 72행 자체는 바꾸지 않는다.
- E5 (A4) ARCHITECTURE.md 187행(`  strategy/, risk/, sizing/, paper/, pnl/, scanner/, display/`) 뒤에 APPROVED_TEXT A4-src(2줄)를, 192행(`docs/                   design, preregistration, evidence review, Work Orders`) 뒤에 APPROVED_TEXT A4-top(1줄)을 삽입한다.
- E6 (R2) README.md 42행(`  statistics, and the v0.6 Monte Carlo study (`research/v06/`).`) 뒤에 APPROVED_TEXT R2(4줄)를 삽입한다.
- E7 (R1) README.md 105행(`| Real-data backtest (BT-5), forward evaluation (BT-6) | …`) 뒤에 APPROVED_TEXT R1(1줄)을 삽입한다.
- E8 (R3) README.md 133행(`├── strategy/, risk/, sizing/, paper/, pnl/, scanner/, display/`) 뒤에 APPROVED_TEXT R3-src(2줄)를, 137행(`configs/                  preregistered study configuration`) 뒤에 APPROVED_TEXT R3-top(1줄)을 삽입한다.
- E9 경계: E1–E8 지점 밖의 바이트는 base와 같다. 상태 라벨은 ARCHITECTURE.md의 기존 정의만 쓴다. LF와 파일 끝 줄바꿈 형식은 바꾸지 않는다.
- E10 기대 결과: 구현 후 각 파일의 blob = base blob에 E1–E8을 적용한 결과(바이트 단위)이다. 기대 줄 수는 ARCHITECTURE.md 229 − 1 + 2 + 2 + 3 = 235, README.md 529 + 4 + 1 + 3 = 537이다. `git diff -U0`의 hunk 수는 ARCHITECTURE.md 6, README.md 4다. APPROVED_TEXT의 실질 변경이 필요하면 구현하지 않고 멈춰서 PROPOSED_ERRATA로 보고한다.

APPROVED_TEXT A1 (ARCHITECTURE.md, E2, 1줄):

````text
- supervisor functions beyond read-only, non-authoritative research task proposals;
````

APPROVED_TEXT A2 (ARCHITECTURE.md, E3, 2줄):

````text
| Knowledge records and context | `knowledge/` | `IMPLEMENTED` | Git-tracked immutable JSON records in `knowledge/records/` (format: `knowledge/SCHEMA.md`): validation, deterministic queries and context packets marked `DATA_NOT_INSTRUCTIONS` (`knowledge/CONTEXT_CONTRACT.md`). Read-only; no write API. |
| Supervisor proposals | `supervisor/` | `IMPLEMENTED` | Deterministic research task proposals built from a context packet, marked `NON_AUTHORITATIVE_PROPOSAL` (`docs/supervisor_proposal_contract.md`). A proposal is not a Work Order or an authorization; the package has no execution, dispatch, trading, file-write or network capability. |
````

APPROVED_TEXT A3 (ARCHITECTURE.md, E4, 2줄):

````text
`knowledge` and `supervisor` are not shown in the diagram: `knowledge` imports no other MoneyLab package and calls
`git` read-only (`rev-parse`, `cat-file`) for source checks; `supervisor` imports only `knowledge`.
````

APPROVED_TEXT A4-src (ARCHITECTURE.md, E5 첫 번째, 2줄):

````text
  knowledge/            knowledge records: load, validate, query, context packets
  supervisor/           read-only, non-authoritative research task proposals
````

APPROVED_TEXT A4-top (ARCHITECTURE.md, E5 두 번째, 1줄):

````text
knowledge/              Git-tracked knowledge records (records/), SCHEMA.md, CONTEXT_CONTRACT.md
````

APPROVED_TEXT R1 (README.md, E7, 1줄):

````text
| Knowledge records, context resolution and supervisor proposals | Implemented; read-only and deterministic. A supervisor proposal is a non-authoritative research suggestion, not a Work Order, an approval or an execution instruction | [SCHEMA.md](knowledge/SCHEMA.md), [proposal contract](docs/supervisor_proposal_contract.md) |
````

APPROVED_TEXT R2 (README.md, E6, 4줄):

````text
- **Knowledge and supervisor** (`src/moneylab/knowledge/`, `src/moneylab/supervisor/`): Git-tracked immutable
  knowledge records with validation, deterministic queries and context packets; the supervisor derives read-only
  research task proposals from that context, marked `NON_AUTHORITATIVE_PROPOSAL`. Nothing in these packages
  executes, approves or dispatches work.
````

APPROVED_TEXT R3-src (README.md, E8 첫 번째, 2줄):

````text
├── knowledge/            knowledge records: load, validate, query, context packets
├── supervisor/           read-only, non-authoritative research task proposals
````

APPROVED_TEXT R3-top (README.md, E8 두 번째, 1줄):

````text
knowledge/                Git-tracked knowledge records (records/), SCHEMA.md, CONTEXT_CONTRACT.md
````

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA:
- AC1 구현 커밋 파일 집합 = ALLOWED_FILES. PR 전체 파일 집합 = ALLOWED_FILES ∪ {docs/tasks/DOCS-ALIGN-01/WORK_ORDER.md}.
- AC2 두 파일 blob이 E10 정의와 바이트 단위로 같다(줄 수 235 / 537).
- AC3 `git diff -U0 CANONICAL_BASE_SHA`의 hunk가 E1–E8과 1:1로 대응한다(ARCHITECTURE.md 6, README.md 4). 그 밖의 diff 0.
- AC4 ARCHITECTURE.md §8에 구현된 knowledge/context 계층과 현재 supervisor proposal 기능이 `NOT_IMPLEMENTED`로 남지 않는다.
- AC5 APPROVED_TEXT의 서술마다 코드·계약·테스트 근거(경로와 행)가 PRECOMMIT_AUDIT 보고의 claim→evidence 표에 있다.
- AC6 새 문구가 가리키는 경로(knowledge/SCHEMA.md, knowledge/CONTEXT_CONTRACT.md, knowledge/records/, docs/supervisor_proposal_contract.md, src/moneylab/knowledge/, src/moneylab/supervisor/)가 CANONICAL_BASE tree에 있다. 새 표 행의 열 수가 표 머리와 같다(ARCHITECTURE.md §3 4열, README.md 상태 표 3열). LF·파일 끝 형식 불변.
- AC7 새 문구가 승인·실행·dispatch 권한, 미구현·미승인 기능, 수익성·live readiness를 긍정하지 않는다. "approval"·"authorization"·"approves"는 부정문에서만 쓴다.
- AC8 PR CI의 Windows `pytest` job 성공(INDEPENDENT).

## TEST_GATES

TEST_GATES:
- 변경 파일 집합 = {ARCHITECTURE.md, README.md}, PROTECTED diff 0, untracked 0
- `git diff --check` 깨끗함
- hunk 대조: `git diff -U0 0848cfc6ddf04d7ebdeb5d5e66de47ee1760c9cf -- ARCHITECTURE.md README.md`의 hunk 위치·내용이 E1–E8과 같고 hunk 수가 6 / 4다
- 기대 결과 일치: 각 파일 blob이 E10 정의와 같고 줄 수가 235 / 537이다
- claim→evidence 표 작성(AC5)
- 경로 실재: AC6의 경로마다 `git cat-file -e 0848cfc6ddf04d7ebdeb5d5e66de47ee1760c9cf:<path>` 성공
- 표 열 수 확인(AC6)
- hygiene 대체 확인: 추가된 줄에 `C:/Users`, `C:\Users`, `/c/Users`, `/home/`, `.env`, `token`, `secret`, `private key`가 없다(git diff 출력 검사)
- 로컬 pytest는 요구하지 않는다: 두 파일은 코드·테스트가 내용을 읽지 않고, TARGET_WORKTREE에 `.venv`가 없으며 이 task는 `.venv`를 만들지 않는다. `tests/test_repo_hygiene.py`를 포함한 회귀 확인은 PR CI의 Windows `pytest` job으로 한다.

## E2E_GATES

E2E_GATES:
- NOT_REQUIRED (문서 전용). 대체 확인: clean 구현 커밋에서 두 파일 blob이 E10과 같고, 커밋 파일 집합 = ALLOWED_FILES이며, 구현 커밋의 부모 = C1이다.

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 커밋 SHA·parent·tree, Work Order sha256, 커밋 파일 집합, 두 파일 blob id와 E10 일치, hunk 목록, merge parent·tree
- CLAUDE_REPORTED: Claude가 실행한 확인·계산, claim→evidence 표
- INDEPENDENT: PR CI 결과, GitHub 화면·문구 확인(사용자)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, 원격 main ≠ CANONICAL_BASE_SHA, Work Order sha256 불일치
- BASE_BLOBS 불일치, 또는 E1–E8이 인용한 base 줄의 내용이 실제와 다름
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경, ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A/M 표기와 base 상태 불일치
- 구현 결과가 E10과 다름, APPROVED_TEXT 변경 필요, 근거 없는 서술 필요
- NON_GOALS 항목을 건드려야만 일관성이 맞는 경우
- guard deny, 권한 창 거절
- CI 실패
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일
