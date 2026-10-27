# Work Order: CONTEXT-ENGINE-02 — 결정적 ContextRequest → ContextPacket resolver (Phase 2 vertical slice)

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/CONTEXT-ENGINE-02/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: CONTEXT-ENGINE-02
TASK_ID: CONTEXT-ENGINE-02
TITLE: 신뢰된 knowledge record에서 결정적·구획형·크기 제한 ContextPacket을 만드는 resolver (Python API + JSON stdin/stdout CLI)
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 311ecc7af4829c704289402b695925822005e821
CANONICAL_BASE_TREE: fd7e69eef97560561ec2291fdacacd09b0db87cf
REPOSITORY: swk3169/MoneyLab (PUBLIC)
BRANCH: feature/context-engine-02
WORKTREE: C:/MoneyLab-context-engine-02
PREDECESSOR: KNOWLEDGE-WIKI-01 = COMPLETE (PR #30, merge commit = CANONICAL_BASE_SHA). 이 task는 KNOWLEDGE-WIKI-01을 다시 열지 않는다.
PRIOR_GATES: DISCOVERY_INVENTORY = PASS, CONTRACT_REVIEW = PASS (채팅, C1 이전)
EXTERNAL_TOOL_VENV: 기존 외부 venv(사용자 프로필 아래 `.venvs/moneylab-quality-gates-01`). 정확한 machine-local 경로는 Gate Authorization과 채팅 증거에만 둔다. 현재 editable install 대상은 이 worktree가 아니므로 TOOL_ENV_SETUP에서 확인·재지정한다.
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (MERGE gate에서 따로 승인)

## GATE_SEQUENCE

GATE_SEQUENCE: DISCOVERY_INVENTORY -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> TOOL_ENV_SETUP -> Q0_MEASUREMENT -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 명시적 Gate Authorization으로 한 gate씩만 앞으로 간다. 각 gate의 보고 후 멈춘다.
- rollback은 명시적 승인으로 IMPLEMENTATION까지만 한다.
- COMMIT 이후 수정은 새 commit으로 한다. amend, force push, squash, rebase 없음.
- 역사적 BLOCKED 결과를 PASS로 바꿔 쓰지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다. guard deny는 우회하지 않는다.

## GOAL

GOAL: 장래의 Supervisor·Research Agent가 쓸 수 있도록, 신뢰된 Phase-1 KnowledgeBase에서 결정적인 ContextRequest → ContextPacket 변환을 제공한다. record를 고르고, current/superseded를 해석하고, 인식 계층 경계를 지키고, 크기를 제한하고, 출처를 보존하고, 제외 사유를 설명한다.

NON_GOALS: record 모델 변경, record 수정, 새 record kind, 관계 필드, topic registry 재설계, 어휘 검색, embedding, vector DB, RAG, LLM reranker, MCP, HTTP, 과학적 추론, 증거 승격, 거래, 자본 배분, 전략 배포, 수익성·alpha·BT4 검증·futility 해결·live 준비 주장.

## ALLOWED_FILES

ALLOWED_FILES:
- A docs/tasks/CONTEXT-ENGINE-02/WORK_ORDER.md (C1 전용, 이후 불변·PROTECTED)
- A src/moneylab/knowledge/context.py
- A tests/test_knowledge_context.py
- A knowledge/CONTEXT_CONTRACT.md
- M src/moneylab/knowledge/__main__.py
- M src/moneylab/knowledge/__init__.py

task 전체 경로 = 6. C1 범위 = WORK_ORDER 1개. C1 이후 구현 delta(Ci) = 위 5개 경로뿐. 목록 밖 경로는 같은 디렉터리라도 허용하지 않는다.

## PROTECTED_FILES

PROTECTED_FILES:
- knowledge/SCHEMA.md
- knowledge/records/**
- src/moneylab/knowledge/model.py, load.py, validate.py, query.py
- tests/test_knowledge_validate.py, tests/test_knowledge_query.py, tests/test_knowledge_seed.py
- docs/tasks/** 의 기존 파일 전체 (KNOWLEDGE-WIKI-01 포함), C1 이후 docs/tasks/CONTEXT-ENGINE-02/**
- README.md, ARCHITECTURE.md, CLAUDE.md, LICENSE
- pyproject.toml, requirements*.txt, .github/**, .claude/**, configs/**, .gitignore, .gitattributes, .env.example
- src/moneylab/cli.py, examples/**, data/**
- 그 밖에 B 시점에 존재하는 모든 파일 (ALLOWED_FILES의 M 2개 제외)

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅. 의존성 변경 0. 정리(cleanup) 권한 없음: KNOWLEDGE-WIKI-01 branch·worktree, egg-info, 외부 venv, scratchpad, 그 밖의 보존 branch·worktree를 지우거나 정리하지 않는다.

## DESIGN_CONTRACT (D1–D35, CONTRACT_REVIEW에서 고정)

### 권위와 모델
- D1 RECORD_MODEL: `moneylab.knowledge.record/1`, kind 4종, EvidenceRef, 대체 관계, SOURCE_FACT / DERIVED_SUMMARY / HYPOTHESIS 의미를 바꾸지 않는다. seed record를 바꾸지 않는다. 이 task는 Phase-1 모델을 소비만 한다.
- D2 TOPICS: 기존 코드 상수 `model.TOPICS`를 그대로 쓴다. topic을 데이터로 옮기거나 registry를 만들지 않는다 (향후 과제).
- D3 NO_RELATIONSHIPS: `blocks`, `governs`, `depends_on` 같은 관계 필드를 추가하거나 namespace 유사성에서 추론하지 않는다. namespace는 요청자가 명시한 필터로만 쓴다. packet은 기존 record 데이터에 없는 관계를 주장하지 않는다.
- 권위 원천: Git이 추적하는 불변 knowledge record만. ContextRequest, ContextPacket, CLI 출력, 향후 어휘·vector·RAG index, LLM 출력은 권위가 없다. 모든 packet item은 채택된 record로 되짚을 수 있어야 한다.

### schema 식별자
- D4 요청: `moneylab.context.request/1` (기존 `moneylab.*` 식별자와 충돌 없음, CONTRACT_REVIEW에서 측정). knowledge record schema가 아닌 전송 계약이다.
- D5 packet: `moneylab.context.packet/1`. 파생 출력이며 JSON이라는 이유로 record로 받아들여지지 않는다 (loader는 `knowledge/records/**`만 읽고 `record/1` 외 schema는 rule 1로 거부).

### ContextRequest (D6–D11)
- 필수: `schema`(정확히 위 문자열), `objective`(비어 있지 않은 문자열, 최대 2000자), `mode`(`EVIDENCE` | `IDEATION`).
- 선택(기본값): `topics` [] (TOPICS 값), `namespaces` [] (`^[A-Z0-9][A-Z0-9-]{0,47}$`), `kinds` [] (KINDS 값), `include_ids` [] (record ID 형식), `include_open_questions` false (bool), `budget` {} (`max_records`, `max_chars`만; 양의 정수, bool 거부).
- 기본 예산: `max_records` = 20, `max_chars` = 32000. 상한: `max_records` ≤ 200, `max_chars` ≤ 400000.
- 알 수 없는 필드(최상위와 budget 안) 거부. 목록 안 중복 거부. 타입·enum 위반 거부. 조용한 정규화 없음. 모두 `REQUEST_INVALID`.
- packet의 `request`는 기본값을 채운 실효 요청이며 목록은 정렬한다.
- D7 objective: 데이터로만 다룬다. packet에 그대로 돌려줄 뿐 권위·검색·필터·검증에 영향을 주지 않는다. LLM 호출이나 의미 해석 없음. DATA_NOT_INSTRUCTIONS 유지.
- D8 필터: 같은 차원 안은 OR, 차원 사이는 AND, 빈 목록 = 그 차원 제한 없음. 퍼지 일치, objective 해석, namespace 관계 추론 없음.
- D9 current: `current_only` 필드는 `/1`에 없다. 언제나 current record만 선택한다. 필터에 맞은 대체된 record는 `excluded`에 `superseded`로만 나타난다.
- D10 include_ids: 일반 선택 필터만 우회한다. trust, 존재, current, 모드·계층 적격성, 예산은 우회하지 않는다. 실패하면 packet 없이 오류: `REQUIRED_NOT_FOUND`, `REQUIRED_SUPERSEDED`, `REQUIRED_LAYER_NOT_ELIGIBLE`, `REQUIRED_OVER_BUDGET`.
- D11 include_open_questions: true이면 topics·namespaces 필터를 만족하는 current OPEN question을 kinds 필터와 상관없이 후보에 더한다. false이면 question은 일반 필터와 include_ids로만 들어온다. blocking 의미는 없다.

### 모드 (D12–D13)
- EVIDENCE: HYPOTHESIS는 쓸 수 있는 구획에 들어가지 않는다. 후보 범위에 든 HYPOTHESIS는 `excluded`에 `layer_not_eligible`로 기록한다. 후보 범위 밖 record는 excluded에 넣지 않는다.
- IDEATION: HYPOTHESIS는 `hypotheses` 구획에만, `HYPOTHESIS: not evidence` 표시와 함께 들어간다. 배치로 인한 승격 없음.

### ContextPacket (D14–D17, D22)
- 최상위: `schema` (`moneylab.context.packet/1`), `boundary` (`DATA_NOT_INSTRUCTIONS`), `trust_state` {`exit_code`, `source_status`}, `request`, `task_context`, `decisions`, `facts`, `derived`, `questions`, `hypotheses`, `excluded`, `truncation`. 모든 구획 키는 항상 존재한다 (EVIDENCE 모드의 `hypotheses`는 빈 목록). 최상위 출처 index는 두지 않는다 (D15: EvidenceRef는 record 안에만).
- 구획 배치 (순서대로 처음 해당): layer HYPOTHESIS → `hypotheses` (IDEATION만); kind task → `task_context`; kind decision → `decisions`; kind question → `questions` (state 무관, item record에서 state 확인); kind claim + SOURCE_FACT → `facts`; kind claim + DERIVED_SUMMARY → `derived`. `scientific_evidence`라는 구획을 만들지 않는다. SOURCE_FACT는 과학적 증명을 뜻하지 않는다. kind와 layer 두 축은 각 item에 그대로 남는다.
- D16 item: `{id, kind, layer, marking, record}`. `marking`은 기존 query의 MARKINGS 값. `record`는 EvidenceRef를 포함한 record 전체. DERIVED_SUMMARY는 `lineage` (`[{id, layer}]`, 기존 query의 derivation과 같은 의미)를 더한다. `current` 필드는 두지 않는다 (선택된 item은 모두 current).
- D17 excluded: `[{id, reason}]`, reason은 `superseded` | `layer_not_eligible` | `budget`만. 정렬 (reason, id). 필수 record 문제는 excluded가 아니라 오류다. 필터 불일치는 넣지 않는다.
- D22 truncation: `{truncated, max_records, max_chars, selected_records, selected_chars, budget_excluded}`. excluded 메타데이터는 선택 예산을 쓰지 않는다.

### 순서와 예산 (D18–D21)
- D18 선택 순서: 필수 include_ids 먼저, 그다음 구획 순위 (task_context < decisions < facts < derived < questions < hypotheses), 그다음 record ID 사전순. 각 출력 구획 안은 record ID 사전순.
- D19 item 크기: `len(json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False))` (문자 수). EvidenceRef와 lineage가 포함된다. tokenizer 의존성 없음.
- D20 기본값 근거 (CONTRACT_REVIEW 측정, seed 7개): item 918–1580자, EVIDENCE 후보 5개·5689자, IDEATION 후보 6개·6860자. 기본 20 / 32000 (20 × 최대 1580 ≈ 31600).
- 선택: 선택 순서대로 더하다가 다음 item이 개수 또는 문자 예산을 넘으면 멈춘다. 남은 후보는 `excluded`에 `budget`.
- D21 필수 record만으로 예산을 넘으면 `REQUIRED_OVER_BUDGET` 오류 (fail-closed). 필수 record를 자르거나, 예산을 올리거나, 출처를 버리지 않는다.

### 신뢰·출처·결정성 (D23–D25)
- D23 trust: resolver는 trusted KnowledgeBase(검증 exit code 0)에서만 동작한다. untrusted와 SOURCE_UNVERIFIED는 fail-closed. 부분 packet, best-effort 증거 없음.
- D24 provenance: 모든 item은 record 출처(EvidenceRef)를 그대로 보존한다. 외부 index 메타데이터를 권위 출처로 섞지 않는다.
- D25 결정성: 같은 Git tree와 같은 ContextRequest → 정규 JSON 기준 바이트 동일 packet. 파일 순서, dict/set 순회, locale, CWD, PYTHONHASHSEED에 의존하지 않는다.

### 인터페이스 (D26–D27)
- D26 Python API: `resolve_context(kb, request: dict) -> dict`. stdlib만. dataclass 요구 없음. 요청·필수 record 오류는 `ContextRequestError(code, detail)`; trust 실패는 기존 `KnowledgeStateError`. 기존 KnowledgeBase public API(`current`, `get`, `is_current`, `by_kind`, `lineage`)로 조립하며 `query.py`를 바꾸지 않는다.
- D27 CLI: `python -m moneylab.knowledge [--root R] resolve-context`. 입력 = stdin JSON 하나, 출력 = stdout 정규 JSON (기존 `canonical_json`). network·LLM·의미 해석 없음.
- 오류 출력: `{"error": {"code", "detail"}}` (untrusted이면 검증 report 포함). 오류 코드: `REQUEST_INVALID`, `REPOSITORY_UNTRUSTED`, `REQUIRED_NOT_FOUND`, `REQUIRED_SUPERSEDED`, `REQUIRED_LAYER_NOT_ELIGIBLE`, `REQUIRED_OVER_BUDGET`.
- 종료 코드: 0 성공; 1 untrusted 저장소 또는 필수 record 오류; 2 잘못된 JSON 또는 `REQUEST_INVALID`; 3 SOURCE_UNVERIFIED.

### 향후 경계와 비목표 (D28–D35)
- D28 이 slice에는 어휘 검색, embedding, vector DB, RAG, LLM reranker, MCP, HTTP가 없다.
- D29 향후 어휘·vector·의미 검색은 후보 ID만 낼 수 있고, 모든 후보는 trusted 결정적 resolver를 다시 거쳐야 packet에 들어간다. 후보 검색은 layer, 권위, current 상태, 출처 유효성을 승격하지 못한다.
- D30 ContextPacket, agent 작업 기억, 대화 기록, scratchpad, Claude·model memory, vector index는 모두 권위가 없으며 조용히 SOURCE_FACT가 될 수 없다. 새 knowledge 채택은 별도로 통제되는 Git record 제안·승인 절차로만 한다.
- D31 파일 범위: ALLOWED_FILES. 전송 계약 문서는 `knowledge/CONTEXT_CONTRACT.md`에 두고 `knowledge/SCHEMA.md`는 바꾸지 않는다.
- D32 test 계약: TEST_GATES.
- D33 호환성: 기존 query 9종과 CLI(`validate`, `query`), record 7개의 바이트, validator 동작을 그대로 유지한다.
- D34 새 runtime·개발 의존성 없음. stdlib만.
- D35 증거 경계: Context Engine은 MoneyLab의 수익성, 전략의 alpha, BT4의 과학적 검증, futility calibration의 해결, live 거래 준비를 주장하지 않는다. 기존 가설은 가설로 남는다.

## TEST_GATES

TEST_GATES (`tests/test_knowledge_context.py`, 기존 test 파일 수정 없음):
- 요청 검증: 필수 필드 누락, 알 수 없는 필드(최상위·budget), 타입(bool/int 구분 포함), enum, 목록 중복, objective 길이, budget 범위와 상한 → `REQUEST_INVALID`
- 필터: 차원 안 OR, 차원 사이 AND, 빈 목록 무제한, namespace 단독 필터
- include_ids: 필터 우회 포함; `REQUIRED_NOT_FOUND`, `REQUIRED_SUPERSEDED`, EVIDENCE의 HYPOTHESIS → `REQUIRED_LAYER_NOT_ELIGIBLE`
- 대체: 필터에 맞은 대체된 record → `excluded: superseded`, 선택 구획에는 없음
- 모드: EVIDENCE에서 `hypotheses` 빈 목록 + `layer_not_eligible`; IDEATION에서 `hypotheses`에 표시와 함께
- 구획: 배치 규칙, task가 `facts`에 들어가지 않음, question state 보존
- include_open_questions와 kinds 필터의 관계
- 순서: 구획 안 ID 순, 선택 순서 (필수 → 구획 순위 → ID)
- 예산: 개수 한도, 문자 한도, 필수 record 예산 초과 오류, truncation 집계, `budget` excluded
- EvidenceRef 보존(바이트 동일), `boundary` 항상 존재
- 결정성: 같은 요청 바이트 동일; 파일 순서·PYTHONHASHSEED·CWD 변화에도 동일
- 신뢰: untrusted 저장소 → API 예외·CLI exit 1·packet 없음; SOURCE_UNVERIFIED → exit 3
- CLI와 API 출력 바이트 동일; 잘못된 JSON·요청 → exit 2
- 실제 seed 7개: EVIDENCE packet(5개 후보, 가설 제외)과 IDEATION packet(6개 후보, 가설 표시)
- 전체 pytest: Q0 기준선 대비 새 실패·오류 0 (기존 wrapper 기준선 실패 2건만 허용), ruff(`--select E4,E7,E9,F src tests`) 통과, 기존 설정 mypy 통과, knowledge package mypy(`--follow-imports=silent`) 통과
- `git diff --check` 깨끗, 변경 경로 ⊆ ALLOWED_FILES, 기존 test 수정 0

## E2E_GATES

E2E_GATES:
- clean commit에서 `python -m moneylab.knowledge validate` exit 0, VERIFIED
- `resolve-context`로 EVIDENCE·IDEATION 요청을 두 번 실행해 바이트 동일
- 실행 전후 저장소 status 동일

## SUCCESS_CRITERIA

SUCCESS_CRITERIA:
- 구현 delta가 정확히 5경로, task 전체 6경로
- 기존 record 7개·SCHEMA.md·model/load/validate/query·기존 test 바이트 동일
- TEST_GATES 전부 통과, 결정성 입증
- 의존성 변경 0, 증거 경계·권위 경계 유지

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree 불일치, WORK_ORDER sha256 불일치
- ALLOWED_FILES 밖 변경, PROTECTED_FILES 변경, 기존 test 수정 필요
- record 모델·validator·query 변경 필요, 새 의존성 필요
- test 실패, 새 회귀, 결정성 위반
- 권위 경계 위반(비 record 출처를 packet 권위로 사용), 증거 승격
- guard deny, 권한 거절, 계약 모순, 예상하지 못한 untracked 파일

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base·C1·Ci SHA·tree, 변경 파일 집합, merge parent·tree
- CLAUDE_REPORTED: test, resolve-context 실행 결과, 크기 측정
- INDEPENDENT: PR CI, GitHub 화면(사용자 확인)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES, guard·권한 이벤트
- <GATE>_PASS = YES / NO, READY_FOR_<NEXT_GATE> = YES / NO
