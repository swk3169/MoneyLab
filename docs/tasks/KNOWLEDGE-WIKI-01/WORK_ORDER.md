# Work Order: KNOWLEDGE-WIKI-01 — Context Engine / Memory Layer Phase 1 (불변 JSON knowledge record와 결정적 검증·조회)

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/KNOWLEDGE-WIKI-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: KNOWLEDGE-WIKI-01
TASK_ID: KNOWLEDGE-WIKI-01
TITLE: Git이 추적하는 불변 JSON knowledge record, stdlib 전용 결정적 validator와 query, seed 7개
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 2819e708ff70edfb8380d27ddf7077c9b1e91aff
CANONICAL_BASE_TREE: ed361b0dd3cbb530954653c047ac7099e05dd252
REPOSITORY: swk3169/MoneyLab (PUBLIC)
BRANCH: feature/knowledge-wiki-01
WORKTREE: C:/MoneyLab-knowledge-wiki-01
EXTERNAL_TOOL_VENV: QUALITY-GATES-01에서 만든 외부 venv(사용자 프로필 아래 `.venvs/moneylab-quality-gates-01`). 정확한 machine-local 경로는 Gate Authorization과 채팅 증거에만 둔다. 현재 editable install 대상은 이 worktree가 아니므로 TOOL_ENV_SETUP에서 확인·재지정한다(X6).
WORKSPACE_SETUP: REQUIRED (1차 시도 BLOCKED: B가 로컬 객체 DB에 없음. WORKSPACE_SETUP_RETRY에서 `git fetch origin main` 1회로 B를 받은 뒤 B에서 branch·worktree 생성, 이 파일을 C1으로 발행)
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (MERGE gate에서 따로 승인)

## GATE_SEQUENCE

GATE_SEQUENCE: DISCOVERY_INVENTORY -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> TOOL_ENV_SETUP -> Q0_MEASUREMENT -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

- DISCOVERY_INVENTORY(PASS), CONTRACT_REVIEW(PASS)는 C1 이전에 채팅에서 끝났다.
- WORKSPACE_SETUP 1차 시도 = BLOCKED (역사 기록으로 보존). WORKSPACE_SETUP_RETRY가 WORKSPACE_SETUP을 완료하며 이 파일을 C1으로 발행한다.

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 명시적 Gate Authorization으로 한 gate씩만 앞으로 간다. 각 gate의 보고 후 멈춘다.
- rollback은 명시적 승인으로 IMPLEMENTATION까지만 한다.
- COMMIT 이후 수정은 새 commit으로 한다. amend, force push, squash, rebase 없음.
- 역사적 BLOCKED 결과를 PASS로 바꿔 쓰지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다. guard deny는 우회하지 않는다.

## GOAL

GOAL: 장기 목표(24/7 자율 퀀트 연구·거래 시스템)의 Context Engine / Memory Layer에 필요한 최소 신뢰 기반을 만든다. Git이 추적하는 불변 JSON record를 유일한 권위 원천으로 하고, stdlib만 쓰는 결정적 loader·validator·in-memory index·query와 seed record 7개를 둔다.

NON_GOALS: agent orchestration, Supervisor, Task Generator, MCP server, RAG, embedding, vector DB, SQLite index, MediaWiki, LLM 호출, 자동 수집(PR·채팅·demo 출력), record 쓰기 API, legacy 용어 정규화, paper trading, live trading.

## USER_DECISIONS (WORKSPACE_SETUP에서 고정)

- X1 = APPROVED: TaskRecord는 knowledge record이며 저장된 gate 보고도 COMPLETE 증거 요약도 아니다. `docs/tasks/README.md` §11은 수정하지 않는다. TaskRecord는 Git으로 검증 가능한 신원·출처 사실과 schema가 허용한 commit된 원문 사실만 담는다. PASS·COMPLETE gate 판정, test 수 요약, guard 기록, 채팅 서술, Claude 추론을 담지 않는다.
- X2 = SHALLOW_CI_HEAD_VALIDATION: Phase 1 CI 검증은 HEAD blob 검증이다. CI fetch-depth는 바꾸지 않는다. 전체 이력 출처 검증은 로컬 선택 검증이다. seed record는 HEAD 검증에 적합한 출처만 쓴다.
- X3 = IMMUTABLE_EXISTING_RECORDS: 채택된 `knowledge/records/**` 파일은 보호된다. 정정은 `supersedes`를 가진 새 record로 한다.
- X4 = SEED_VERTICAL_SLICE_7: 아래 SEED_RECORDS 7개만. 과거 task 전체 이관 없음.
- X5 = CONTROLLED_TOPICS_MINIMAL: 아래 TOPIC_ENUM만 쓴다.
- X6 = NEW_TOOL_ENV_SETUP_REQUIRED: 외부 venv의 editable install 대상 재지정은 TOOL_ENV_SETUP에서 따로 승인받는다.
- X7 = GATE_SEQUENCE: 위 GATE_SEQUENCE.

## ALLOWED_FILES

ALLOWED_FILES:
(모두 새 파일, `A`)
- A docs/tasks/KNOWLEDGE-WIKI-01/WORK_ORDER.md (C1 전용, 이후 불변·PROTECTED)
- A knowledge/SCHEMA.md
- A knowledge/records/task/PORTFOLIO-DEMO-01/outcome.json
- A knowledge/records/decision/PORTFOLIO-DEMO-01/result-hash-policy-c1.json
- A knowledge/records/decision/PORTFOLIO-DEMO-01/result-hash-policy-errata-001.json
- A knowledge/records/claim/MC-V06/study-verdict.json
- A knowledge/records/question/BT4-RESEARCH-01/futility-boundary-cause.json
- A knowledge/records/decision/BT4-DESIGN-01/d3.json
- A knowledge/records/claim/BT4-RESEARCH-01/futility-mean-block-hypothesis.json
- A src/moneylab/knowledge/__init__.py
- A src/moneylab/knowledge/model.py
- A src/moneylab/knowledge/load.py
- A src/moneylab/knowledge/validate.py
- A src/moneylab/knowledge/query.py
- A src/moneylab/knowledge/__main__.py
- A tests/test_knowledge_validate.py
- A tests/test_knowledge_query.py
- A tests/test_knowledge_seed.py

위 목록 밖의 경로는 같은 디렉터리 아래라도 허용하지 않는다. 잘못된 record 예시는 test 안에서 `tmp_path`에 만들고 저장소 파일로 두지 않는다.

## PROTECTED_FILES

PROTECTED_FILES:
- canonical base B에 있는 모든 기존 파일. 특히:
  - README.md, ARCHITECTURE.md, CLAUDE.md, LICENSE
  - docs/tasks/README.md (§11 포함), docs/tasks/TEMPLATE.md, 기존 docs/tasks/** 전체
  - docs/** 의 기존 연구·설계·사전등록·incident 문서 전체
  - src/** 의 기존 파일 전체 (`src/moneylab/cli.py` 포함). 새 package `src/moneylab/knowledge/`의 위 6개 파일만 예외
  - tests/** 의 기존 파일 전체, tests/fixtures/**
  - examples/** (synthetic demo 포함)
  - .github/**, .claude/**, configs/**, data/**
  - pyproject.toml, requirements*.txt, .gitignore, .gitattributes, .env.example
- docs/tasks/KNOWLEDGE-WIKI-01/** (C1 이후)
- knowledge/records/** 의 각 파일 (그 파일이 채택된 commit 이후. X3)

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅. 새 task 파일과 위에 명시한 새 knowledge 파일만 생성할 수 있다. 기존 파일 변경 0건.

## DESIGN_CONTRACT

### D1 SOURCE_OF_TRUTH

- 권위 원천은 Git이 추적하는 불변 JSON record(`knowledge/records/**/*.json`)뿐이다.
- 권위가 아닌 것: GitHub PR 본문, Claude·채팅 기록, Claude memory(cache일 뿐), README·ARCHITECTURE(사람용 요약. record가 commit된 바이트를 증거로 인용할 때만 출처가 된다), 외부 로컬 연구 산출물(hash·availability로 가리킬 수 있으나 자동 승격 없음).

### D2 TASK_RECORD_VS_GATE_REPORT

- TaskRecord의 결과 필드는 Git으로 확인 가능한 `MERGED_TO_MAIN`만 쓴다. 채팅 전용 gate 판정(PASS, BLOCKED, COMPLETE)은 담지 않는다.
- gate 보고는 계속 채팅 전용이다(§11 그대로).

### D3 FORMAT

- JSON, UTF-8, ASCII only(`ensure_ascii=True`).
- 정규 형식: `json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True) + "\n"`.
- validator는 파일 텍스트의 CRLF를 LF로 바꾼 뒤 정규 형식과 바이트 비교한다(Windows `core.autocrlf=true` checkout 대응. `.gitattributes`는 바꾸지 않는다).

### D4 LOCATION

- 사람용 명세: `knowledge/SCHEMA.md` (권위 원천 아님).
- record: `knowledge/records/<kind>/<NAMESPACE>/<slug>.json`.
- 생성 index나 binary 파일은 두지 않는다.

### D5 ATOMS

- 공통 envelope 하나와 `kind` 4종: `task`, `claim`, `decision`, `question`.
- EvidenceRef는 record 안의 객체이며 다섯 번째 kind가 아니다.
- Experiment, Run, Strategy, Risk, Limitation은 보류.

### D9 KNOWLEDGE_LAYERS (CONTRACT_REVIEW H의 모호성 해소, 고정)

- SOURCE_FACT
  - 하나 이상의 qualifying EvidenceRef로 직접 뒷받침된다(qualifying = `type: git_blob`, `provenance_class: GIT_VERIFIABLE`, `availability: IN_GIT`).
  - `derived_from`은 비어 있어도 된다.
  - HYPOTHESIS에 의존하지 않는다(`derived_from`에 HYPOTHESIS가 없다).
  - 인용한 증거가 직접 뒷받침하는 사실을 나타낸다.
- DERIVED_SUMMARY
  - `derived_from`에 유효한 record ID가 하나 이상 있어야 한다.
  - 언제나 DERIVED_SUMMARY로 보인다. 스스로 SOURCE_FACT로 승격되지 않는다.
- HYPOTHESIS
  - 미해결 설명 후보나 연구 아이디어를 명시적으로 HYPOTHESIS로 나타낸다.
  - EVIDENCE context에서 제외된다.
  - SOURCE_FACT나 DERIVED_SUMMARY를 뒷받침할 수 없다(그 `derived_from`에 들어갈 수 없다).
  - 과학적 상태를 자율적으로 승격하지 않는다.
- Phase 1에 추가 계층은 없다.

### D10 EVIDENCE_AXES

legacy 상태를 하나의 필드로 평탄화하지 않는다.

| 필드 | 종류 | 값 |
|---|---|---|
| `layer` | 필수, 통제 enum | SOURCE_FACT, DERIVED_SUMMARY, HYPOTHESIS |
| `evidence[].provenance_class` | 필수, 통제 enum | GIT_VERIFIABLE, CLAUDE_REPORTED, INDEPENDENT |
| `evidence[].availability` | 필수, 통제 enum | IN_GIT, GITHUB, EXTERNAL_LOCAL, MISSING |
| claim `payload.axis` | 필수, 통제 enum | SCIENTIFIC, ENGINEERING, WORKFLOW, MATURITY, LITERATURE |
| claim `payload.data_basis` | 필수, 통제 enum | REAL, SYNTHETIC, FIXTURE, NOT_APPLICABLE |
| task `payload.outcome` | 필수, 통제 enum | MERGED_TO_MAIN |
| decision `payload.state` | 필수, 통제 enum | PENDING, DECIDED |
| question `payload.state` | 필수, 통제 enum | OPEN, ANSWERED, WITHDRAWN |
| `labels` | 필수(빈 object 허용), 불투명 문자열 map | 원문 legacy 값을 그대로 둔다. 해석·정규화·승격하지 않는다 |

수익성·alpha·edge·live 준비를 나타내는 통제 값은 어떤 필드에도 두지 않는다.

### D21 SYNTHETIC_DEMO_BOUNDARY

- 기존 demo는 수정하지 않는다. 자동 수집은 범위 밖이다.
- 향후 등록은 `claim`(axis ENGINEERING, data_basis SYNTHETIC)과 증거 포인터로 할 수 있다.
- `SYNTHETIC / NOT_EVIDENCE`는 수익성 증거가 될 수 없다. UNPINNED 실행 출력은 신뢰된 SOURCE_FACT가 될 수 없다. `result_sha256`은 실행별 무결성 값일 뿐이고 실행 간 결정적 산출물 hash와 분리된다. (Phase 1에서는 SCHEMA.md 규칙으로 적는다. 자동 강제는 Phase 2의 run payload 이후.)

### D22 AGENT_AUTHORITY

- 향후 agent는 record를 제안만 한다. 채택은 통제된 Git 절차(Work Order 범위, 사람의 gate 승인, commit, merge commit PR)로만 한다.
- 자율적인 과학적 상태 승격, 위험 한도 승인, 자본 승인, live 거래 승인은 없다.
- Phase 1 코드에는 record 쓰기 API가 없다.

### D18/D19 WIKI_RAG_MCP

- MediaWiki는 범위 밖이다. 나중에 만들면 Git record에서 만든 파생 보기이며, Wiki 편집은 조용히 증거가 될 수 없다.
- RAG, embedding, vector DB, MCP server는 보류. query API는 순수 함수이고 결과를 JSON으로 직렬화할 수 있게 만들어 나중에 MCP로 노출할 수 있게 한다.

## SCHEMA_CONTRACT

- 모든 record: `"schema": "moneylab.knowledge.record/1"`. validator는 다른 값을 거부한다. 해석이 바뀌면 `/2`를 새로 만들고, `/1` record를 조용히 다르게 해석하지 않는다.
- envelope 필수 필드: `schema`, `id`, `kind`, `layer`, `title`, `statement`, `topics`, `supersedes`, `derived_from`, `evidence`, `labels`, `payload`.
  - `title`, `statement`: 비어 있지 않은 ASCII 문자열.
  - `topics`: TOPIC_ENUM 값의 비어 있지 않은 목록, 중복 없음.
  - `supersedes`, `derived_from`: record ID 목록(빈 목록 허용), 중복 없음.
  - `evidence`: EvidenceRef 목록.
  - `labels`: 문자열 → 문자열 object.
  - `payload`: kind별 object.
- kind별 payload:
  - task: `task_id`(문자열, NAMESPACE와 같음), `outcome`, `merge_commit`, `implementation_commit`(40자리 hex), `tree`(40자리 hex).
  - claim: `axis`, `data_basis`.
  - decision: `state`, `local_id`(원문의 ID 문자열 또는 null).
  - question: `state`.
- 알 수 없는 envelope·payload 필드는 거부한다(조용한 확장 금지).
- ID 형식: `<kind>/<NAMESPACE>/<slug>`
  - kind: `task|claim|decision|question`
  - NAMESPACE: `^[A-Z0-9][A-Z0-9-]{0,47}$`
  - slug: `^[a-z0-9][a-z0-9-]{0,63}$`
  - 원문 로컬 ID는 소문자로 바꿔 slug에 쓴다(예: D3 → `d3`).
  - 파일 경로는 `knowledge/records/` + ID + `.json`과 정확히 같아야 한다.

## PROVENANCE_CONTRACT

EvidenceRef 공통 필드: `type`, `provenance_class`, `availability`, `locator`(선택, 문자열 또는 null). type별:
- `git_blob`: `rev`(40자리 commit SHA), `path`(저장소 기준 POSIX 상대 경로), `sha256`(그 rev의 **commit된 blob 바이트** SHA-256, 작업 폴더 바이트 아님), availability = IN_GIT.
- `github`: `locator`만(`github:<owner>/<repo>/<pull|actions/runs>/<number>` 형식), availability = GITHUB. 기계 경로 없음.
- `external`: `locator`(`external:<artifact-class>/<상대 경로>`), `sha256` 필수, availability = EXTERNAL_LOCAL 또는 MISSING.
- `recorded_in_commit`은 두지 않는다. record의 도입 commit은 Git 이력에서 유도한다. record는 자신이 들어갈 commit을 인용하지 않는다(자기 참조 금지). seed record의 `rev`는 canonical base B로 한다.
- 외부 산출물: 논리 locator만. 드라이브 문자, UNC, `/`로 시작하는 절대 경로, `~` 경로, 사용자 이름 없음. Phase 1은 외부 locator를 해석하지 않는다. EXTERNAL_LOCAL 증거만으로 SOURCE_FACT를 만들 수 없다.

## SUPERSESSION_CONTRACT

- record는 채택 후 불변이다. 정정·변경은 새 record로 한다.
- 새 record는 여러 기존 record를 대체할 수 있다(병합).
- 각 기존 record의 직접 대체자는 최대 1개다(분기 금지).
- 대체 순환 금지.
- 같은 kind끼리만 대체한다.
- `superseded_by`는 저장하지 않고 계산한다.
- current = 어떤 유효 record도 그것을 대체하지 않는다.
- 계층 순위 SOURCE_FACT = 3, DERIVED_SUMMARY = 2, HYPOTHESIS = 1. 새 record의 순위 ≥ 대체되는 record의 순위. 따라서 HYPOTHESIS는 DERIVED_SUMMARY·SOURCE_FACT를, DERIVED_SUMMARY는 SOURCE_FACT를 대체할 수 없다.

## VALIDATOR_CONTRACT

validator는 결정적이며 다음을 거부한다(각 위반은 rule 번호와 record ID를 담은 오류로 보고, 오류 목록은 (rule, record_id, 메시지) 순으로 정렬):

1. 지원하지 않는 `schema`
2. 중복 record ID
3. ID 형식 위반
4. ID와 파일 경로 불일치
5. 필수 필드 누락, 알 수 없는 필드, enum 밖 값, 타입 오류, JSON 형식 오류, 정규 형식 위반
6. 존재하지 않는 record 참조(`supersedes`, `derived_from`)
7. 대체 순환
8. 대체 분기(한 record에 직접 대체자가 둘 이상)
9. kind가 다른 대체, 계층을 낮추는 대체
10. `derived_from`이 비어 있는 DERIVED_SUMMARY
11. qualifying EvidenceRef가 없는 SOURCE_FACT
12. HYPOTHESIS가 HYPOTHESIS 아닌 record의 `derived_from`에 쓰임
13. HEAD 모드에서 git_blob `path`가 HEAD에 없거나, `git cat-file blob HEAD:<path>` 바이트의 SHA-256이 기록된 `sha256`과 다름
14. 모든 문자열 값의 machine-specific 절대 경로: Windows 드라이브(`X:\`, `X:/`), UNC(`\\`), `/`로 시작하는 POSIX 절대 경로, `~/` 경로
15. `tests/test_repo_hygiene.py`의 SECRET_PATTERNS와 같은 기준의 secret 형태 문자열(test가 그 목록을 import해서 같은 기준임을 확인한다)

git을 쓸 수 없는 환경:
- 규칙 1–12, 14, 15는 git 없이 검사한다.
- 규칙 13(과 전체 이력 모드 검사)은 git이 없거나 저장소가 아니면 검사하지 못한다. 이때 조용히 통과시키지 않고 결과 상태를 `SOURCE_UNVERIFIED`로 보고한다.
- CLI 종료 코드: 0 = 모든 검사 통과, 1 = 하나 이상의 규칙 위반, 2 = 잘못된 인자, 3 = 위반은 없으나 출처 검사를 할 수 없음(`SOURCE_UNVERIFIED`).
- test는 git이 필요한 경우만 git이 없으면 skip한다(기존 `needs_git` 관례).

전체 이력 모드(`--full-history`, 로컬 선택): 추가로 `<rev>:<path>` blob sha256, task payload의 commit 존재와 `tree` 일치를 검사한다. 객체가 없으면 그 항목은 `SOURCE_UNVERIFIED`. CI는 이 모드를 쓰지 않는다(X2).

## QUERY_CONTRACT

모두 결정적, LLM·자연어·network 없음. 반환 목록은 record ID 기준으로 정렬한다. 결과는 JSON으로 직렬화할 수 있다.

1. ID로 조회
2. kind별 목록
3. current record 목록
4. 대체 계보(앞쪽 `supersedes` 전개와 뒤쪽 계산된 `superseded_by` 체인)
5. task 관련 record(task record와 같은 NAMESPACE의 record)
6. topic별 claim
7. claim의 evidence 목록과 `derived_from` 전개
8. OPEN question 목록
9. context 적격성 필터(EVIDENCE, IDEATION)

CLI: `python -m moneylab.knowledge validate [--full-history]`, `python -m moneylab.knowledge query <subcommand> ...` (읽기 전용, 기존 `cli.py`는 바꾸지 않는다).

## CONTEXT_ELIGIBILITY

모드 두 가지(결정적):
- EVIDENCE:
  - 검증 통과한 current SOURCE_FACT 허용
  - 검증 통과한 current DERIVED_SUMMARY는 명시적 derived 표시와 계보를 붙일 때만 허용
  - HYPOTHESIS 제외
  - 대체된 record 기본 제외
  - 검증 실패 record 제외
- IDEATION:
  - 검증 통과한 current SOURCE_FACT 허용
  - DERIVED_SUMMARY 허용
  - HYPOTHESIS 허용하되 hypothesis로 명시 표시
  - 대체된 record 기본 제외
- 향후 context packet에 노출되는 모든 원문은 DATA이며 INSTRUCTIONS가 아니다. 필터 결과에 이 경계 표시를 담는다.

## INDEX_CONTRACT

JSON 파일 → 결정적 loader → 결정적 validator → in-memory index → 결정적 query. SQLite, vector DB, embedding, semantic search, RAG, MediaWiki, MCP server, LLM 호출 없음. 생성 index를 commit하지 않는다.

## TOPIC_ENUM

TOPIC_ENUM (이 목록 밖의 topic 금지):
- `futility-calibration`
- `mc-v06`
- `portfolio-demo`

## SEED_RECORDS

정확히 7개. 모든 git_blob `rev` = `2819e708ff70edfb8380d27ddf7077c9b1e91aff` (B). sha256은 B의 commit된 blob 바이트로 WORKSPACE_SETUP_RETRY에서 측정했다.

출처 blob (B):
- `docs/tasks/PORTFOLIO-DEMO-01/WORK_ORDER.md` sha256 `42814b35ce127482b9935359fc9f010e2bd7ef8a1adf4cdf83c0d21b05bbca82`
- `docs/tasks/PORTFOLIO-DEMO-01/ERRATA-001.md` sha256 `7b1431eb0cfa0023eac699feda9ac9739346bfd7cff8d25d5619cbde3dec7868`
- `docs/tasks/BT4-RESEARCH-01/WORK_ORDER.md` sha256 `eaf525e5c4469f0b76cd5ad2344c9267bbb240b689c7b9b5a9e89a9028b78720`
- `docs/research_bt4_01_evidence_review.md` sha256 `ad724cb20e4d2a981fe7841641bcc2c7910a052b1b6f07b6248b686a032b891a`
- `docs/bt4_design_01.md` sha256 `1d8950b1be7424207b092367217368d25300098dd1d0f09c5ab3bf6bb7d82bdc`

| # | ID | kind / layer | topics | 출처(locator) | 핵심 payload / labels |
|---|---|---|---|---|---|
| 1 | `task/PORTFOLIO-DEMO-01/outcome` | task / SOURCE_FACT | portfolio-demo | PORTFOLIO-DEMO-01 WORK_ORDER.md(`Metadata`), ERRATA-001.md(`Metadata`), `github:swk3169/MoneyLab/pull/29`(INDEPENDENT, GITHUB) | task_id PORTFOLIO-DEMO-01, outcome MERGED_TO_MAIN, merge_commit `2819e708ff70edfb8380d27ddf7077c9b1e91aff`, implementation_commit `1413298b78c7f17d30b1c16b11692058c14f05e0`, tree `ed361b0dd3cbb530954653c047ac7099e05dd252` |
| 2 | `decision/PORTFOLIO-DEMO-01/result-hash-policy-c1` | decision / SOURCE_FACT | portfolio-demo | PORTFOLIO-DEMO-01 WORK_ORDER.md `L262`, `L265`, `L413` (GOLDEN_HASH_POLICY, STOP_CONDITIONS) | state DECIDED, local_id null. statement: result_sha256 was UNKNOWN_AT_C1 and was to be required equal across two independent equivalent runs and then frozen in tests/test_examples_demo.py; a cross-run mismatch was a STOP condition. |
| 3 | `decision/PORTFOLIO-DEMO-01/result-hash-policy-errata-001` | decision / SOURCE_FACT, supersedes #2 | portfolio-demo | PORTFOLIO-DEMO-01 ERRATA-001.md `L36-L39`, `L61-L66` | state DECIDED, local_id null. statement: result_sha256 is a per-run integrity identifier, is not compared to a fixed cross-run golden and is not described as cross-run deterministic; ERRATA-001 supersedes the three original result_sha256 requirements. |
| 4 | `claim/MC-V06/study-verdict` | claim / SOURCE_FACT | mc-v06 | BT4-RESEARCH-01 WORK_ORDER.md `L58`, evidence review `L91` | axis SCIENTIFIC, data_basis SYNTHETIC. labels: `verdict` = `MIXED / DESIGN-INFORMATIVE`, `bt4_readiness` = `READY_WITH_CAUTION`. statement: The MC-V06 synthetic simulation study's scientific conclusion is MIXED / DESIGN-INFORMATIVE and its BT4 readiness label is READY_WITH_CAUTION. |
| 5 | `question/BT4-RESEARCH-01/futility-boundary-cause` | question / SOURCE_FACT | mc-v06, futility-calibration | evidence review `L580` (§10.2 첫 문장), `L339` (연구 질문 B) | state OPEN. statement: What explains the MC-V06 futility over-rejection (size distortion) at the boundary remains unresolved; the listed candidate causes are not causally confirmed. |
| 6 | `decision/BT4-DESIGN-01/d3` | decision / SOURCE_FACT | futility-calibration | bt4_design_01.md `L61`, `L161` | state PENDING, local_id `D3`. statement: Decision D3, whether to apply Holm to the futility REJECT over the four primaries, is pending; it is classified NEEDS_VALIDATION because the Holm guarantee depends on the validity of the individual p-values. |
| 7 | `claim/BT4-RESEARCH-01/futility-mean-block-hypothesis` | claim / HYPOTHESIS | mc-v06, futility-calibration | evidence review `L580`, `L583` (§10.2 HYPOTHESIS) | axis SCIENTIFIC, data_basis SYNTHETIC. statement(아래 고정 문장) |

record 7의 statement (고정, 원문을 강화하지 않는다):

"Candidate cause, not causally confirmed: the fixed stationary-bootstrap mean_block=20 may be short relative to the regime persistence of the momentum-feedback DGP, as one candidate explanation of the MC-V06 futility over-rejection. This is a hypothesis only; it does not establish profitability, alpha, or live readiness."

원문(B, `docs/research_bt4_01_evidence_review.md`): L580 "다음은 모두 MC-V06 futility 초과기각의 원인 후보이며, 어느 것도 인과적으로 확인되지 않았다.", L583 "고정 `mean_block=20` (모멘텀 피드백 DGP의 국면 지속성에 비해 짧을 가능성)".

seed 문장은 위 표와 고정 문장의 뜻을 바꾸지 않는 범위에서 영어 ASCII로 쓴다. 원문에 없는 주장을 더하지 않는다. README는 seed 출처로 쓰지 않는다.

## Q0_MEASUREMENT

Q0_MEASUREMENT (IMPLEMENTATION 전 측정, 저장소 변경 없음):
- 외부 Python 환경과 `moneylab` import 대상(TOOL_ENV_SETUP 결과 확인)
- B 기준 위 출처 blob 5개의 sha256 재측정과 locator 행 내용 확인
- 관련 기존 test 기준선(hygiene, architecture)
- `git cat-file blob HEAD:<path>` 동작(Windows와 shallow 조건 고려)

## TEST_GATES

TEST_GATES:
- 새 test 파일은 ALLOWED_FILES의 3개뿐. 기존 test 수정 0건.
- validator 거부 규칙 15개 각각을 `tmp_path` fixture로 실제 거부함을 보인다.
- query 9종과 EVIDENCE·IDEATION 적격성을 test한다.
- seed 7개의 HEAD 모드 검증 오류 0.
- 결정성: 같은 입력 → 같은 출력(로드 순서 무관).
- knowledge package는 stdlib과 git subprocess만 쓴다(새 test로 확인. 기존 아키텍처 test는 바꾸지 않는다).
- 전체 pytest(기존 기대 실패 외 실패 0), ruff(`--select E4,E7,E9,F src tests`) 통과. mypy는 기존 설정을 바꾸지 않고, knowledge package는 따로 실행해 결과만 기록한다.
- `git diff --check` 깨끗함, 변경 파일 ⊆ ALLOWED_FILES.

## E2E_GATES

E2E_GATES:
- clean commit에서 `python -m moneylab.knowledge validate` 종료 코드 0, seed 7개.
- query 9종을 CLI로 실행해 결정적 결과(두 번 실행 결과 동일).
- 실행 전후 저장소 status 동일.

## SUCCESS_CRITERIA

SUCCESS_CRITERIA:
- seed record 정확히 7개, 모두 parse, 모두 정규 JSON 형식.
- HEAD 검증 오류 0. 모든 출처 blob hash가 commit된 바이트와 일치.
- ID 유일, 모든 참조 해석, 대체 해석 결정적(#3이 #2를 대체, #2는 current 아님).
- validator 거부 규칙 15개 전부 test됨.
- query 9종 전부 test됨. EVIDENCE·IDEATION 적격성 test됨(#7은 EVIDENCE에서 제외, IDEATION에서 hypothesis 표시).
- record의 절대 local 경로 0, secret 0.
- test 오프라인, network 의존 없음, LLM 의존 없음.
- ruff PASS. mypy는 기존 설정 변경 없이 가능할 때 기록.
- Windows 필수 CI 새 실패 없음. Linux 실험 job은 기존 EXPECTED_FAILURE 2건(`test_agent_guard.py::test_wrapper_passes_real_decisions_through`, `test_agent_guard.py::test_wrapper_cannot_fix_invalid_json_with_exit_0`) 외 새 실패 없음.
- 기존 저장소 파일 변경 0.

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, WORK_ORDER sha256 불일치
- ALLOWED_FILES 밖 변경, PROTECTED_FILES 변경, 기존 파일 변경
- 출처 blob sha256이 이 문서의 값과 다름, locator 행이 seed 문장을 뒷받침하지 않음
- seed가 7개가 아니거나 TOPIC_ENUM 밖 topic 사용
- validator 규칙 중 하나라도 test로 거부를 보일 수 없음
- record에 수익성·alpha·live 준비 주장, gate 판정, test 수, 채팅 서술이 들어감
- 새 의존성 필요, CI·pyproject·cli.py 변경 필요
- guard deny, 권한 거절, test 실패, 계약 모순, 예상하지 못한 untracked 파일

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·구현 commit SHA·tree, 파일 sha256, 출처 blob sha256, 변경 파일 집합, merge parent·tree
- CLAUDE_REPORTED: test, validate·query 실행 결과
- INDEPENDENT: PR CI, GitHub 화면(사용자 확인)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES, guard·권한 이벤트
- <GATE>_PASS = YES / NO, READY_FOR_<NEXT_GATE> = YES / NO
