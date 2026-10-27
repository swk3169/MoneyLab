# Work Order: SUPERVISOR-01 — 결정적·읽기 전용·비권위 ResearchTaskProposal 생성기 (Supervisor 첫 vertical slice)

이 파일은 불변이다. 발행(C1) 후 수정하지 않는다. 계약 변경은 `docs/tasks/SUPERVISOR-01/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## ISSUANCE

ISSUANCE:
- 이 문서의 효력은 C1 commit에 있다. WORKSPACE_SETUP Gate Authorization에 따라 `docs/tasks/SUPERVISOR-01/WORK_ORDER.md`로 승인 문구 그대로 생성되고, 그 파일만 담은 C1 commit이 BRANCH에 존재하고, 그 blob의 sha256이 WORKSPACE_SETUP 보고와 일치할 때만 `STATUS: ISSUED`가 유효하다.
- C1 이전의 모든 사본(채팅 문안, 검토본, 미커밋 파일)은 DRAFT이며 어떤 gate의 권한도 주지 않는다.
- C1 이후 이 파일은 불변이다. 변경은 ACCEPTED ERRATA로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.1
WORK_ORDER_ID: SUPERVISOR-01
TASK_ID: SUPERVISOR-01
TITLE: 신뢰된 ContextPacket에서 결정적으로 연구 후보를 찾아 비권위 ResearchTaskProposal을 만들고 검증·stale 확인하는 Supervisor (Python API + JSON stdin/stdout CLI)
VERSION: 1.0
STATUS: ISSUED (ISSUANCE 절의 조건을 충족한 C1 commit에서만 유효)
CANONICAL_BASE_SHA: 56743bfb6c5544ef1298b3912d3e46693c60be41
CANONICAL_BASE_TREE: deb19d8f6db4cabb8d111ef715e462cb40d736b8
REPOSITORY: swk3169/MoneyLab (PUBLIC)
BRANCH: feature/supervisor-01
WORKTREE: C:/MoneyLab-supervisor-01
SOURCE_WORKTREE: C:/MoneyLab-context-engine-02 (WORKSPACE_SETUP 명령을 실행하는 기존 worktree. 파일·index·branch를 바꾸지 않는다. HEAD와 status는 WORKSPACE_SETUP D 단계에서 확인한다.)
PREDECESSOR: CONTEXT-ENGINE-02 = COMPLETE (PR #31, merge commit = CANONICAL_BASE_SHA). 이 task는 CONTEXT-ENGINE-02를 다시 열지 않는다.
PRIOR_GATES: DISCOVERY_INVENTORY = PASS, CONTRACT_REVIEW = PASS (D1–D31), WORK_ORDER_DRAFT = PASS, WORK_ORDER_REVIEW = PASS (수정 반영 통합본 = 이 문서). 모두 채팅, C1 이전.
EXTERNAL_TOOL_VENV: 기존 외부 venv(사용자 프로필 아래 `.venvs/moneylab-quality-gates-01`). 정확한 machine-local 경로는 Gate Authorization과 채팅 증거에만 둔다. 현재 editable install 대상은 이 worktree가 아니므로 TOOL_ENV_SETUP에서 확인·재지정한다.
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit (MERGE gate에서 따로 승인)

## GATE_SEQUENCE

GATE_SEQUENCE: DISCOVERY_INVENTORY -> CONTRACT_REVIEW -> WORK_ORDER_DRAFT -> WORK_ORDER_REVIEW -> WORKSPACE_SETUP -> TOOL_ENV_SETUP -> Q0_MEASUREMENT -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 명시적 Gate Authorization(`GATE_AUTHORIZATION: SUPERVISOR-01 <GATE> WO@<commit>`)으로 한 gate씩만 앞으로 간다. 각 gate의 보고 후 멈춘다. 이전 gate의 승인이나 이 Work Order 자체는 다음 gate의 승인이 아니다.
- rollback은 명시적 승인으로 IMPLEMENTATION까지만 한다.
- COMMIT 이후 수정은 새 commit으로 한다. amend, force push, squash, rebase 없음.
- 역사적 BLOCKED 결과를 PASS로 바꿔 쓰지 않는다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, docs/tasks/README.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다. guard deny는 우회하지 않는다. 이 Work Order는 새 governance 권한을 만들지 않는다.

## GOAL

GOAL: 신뢰된 KnowledgeBase와 CE-02 ContextPacket만을 입력으로, 결정적으로 연구 후보(OPEN question, PENDING decision, IDEATION 모드의 HYPOTHESIS)를 찾아 비권위·비실행 ResearchTaskProposal을 만들고, 그 구조를 검증하고, 입력이 바뀌었는지(stale) 확인한다. Proposal ≠ Work Order ≠ Authorization.

NON_GOALS: 연구 실행, worker·agent·scheduler·queue, LLM·MCP·HTTP·network, shell·subprocess, 저장소·파일 쓰기, knowledge record 생성·수정·채택, Work Order 생성·승인, 과학적 결론·증거 승격, 순위·점수·우선순위, 의존·차단 관계 추론, 실행 사이 상태 저장, paper·live 거래, 자본 배분, Policy Engine, CE-02·knowledge schema 변경, CE-02 LOW 소견 수정, 수익성·alpha·BT4 검증·futility 해결·live 준비 주장.

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP, 순서대로 (한 단계라도 실패하면 그 자리에서 STOP):
  A. Gate Authorization 후 SOURCE_WORKTREE에서 `git fetch origin main`을 한 번만 실행한다 (다른 ref, `--all`, `--prune` 없음).
  B. fetch한 `origin/main`의 commit SHA가 CANONICAL_BASE_SHA와 같은지 확인한다.
  C. 그 commit의 tree SHA가 CANONICAL_BASE_TREE와 같은지 확인한다.
  D. SOURCE_WORKTREE의 HEAD와 `git status --porcelain --untracked-files=all`이 fetch 전에 기록한 값과 같은지 확인한다. SOURCE_WORKTREE의 파일·index·branch는 바꾸지 않는다.
  E. B–D가 모두 통과한 뒤에만 CANONICAL_BASE_SHA에서 BRANCH와 WORKTREE를 만든다. 그 전에 base에 `src/moneylab/supervisor/`와 ALLOWED_FILES·C1_FILES 경로가 없음을 확인한다 (A 표기 확인).
  F. WORKTREE에 C1_FILES 문서 하나를 승인된 최종 문구 그대로 만든다.
  G. 문서 sha256이 승인 문구의 sha256과 같은지, WORKTREE의 변경이 그 한 경로뿐인지 확인한다.
  H. 그 경로만 명시해 stage하고 C1 commit을 만든다 (WORK_ORDER.md 하나만).
  I. C1 SHA·parent·tree, 문서 sha256·blob, guard·권한 이벤트, 변경 범위를 보고한다.
  J. 멈춘다.
  B·C 불일치는 branch·worktree 생성 전에 STOP한다. C:/MoneyLab과 그 밖의 worktree의 파일·index·branch는 바꾸지 않는다 (fetch와 worktree 생성이 공유 git 디렉터리에 쓰는 ref·object·worktree 메타데이터는 이 단계의 승인 범위).
- TOOL_ENV_SETUP: 외부 venv의 editable install 대상 확인·재지정 (의존성 추가 없음)
- Q0_MEASUREMENT: clean C1에서 기준선 측정 (전체 pytest, ruff, mypy, knowledge validate)
- IMPLEMENTATION: ALLOWED_FILES 생성, TEST_GATES 실행
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES만 경로를 명시해 stage, 커밋 하나
- CLEAN_COMMIT_E2E: E2E_GATES와 전체 pytest 실행, 저장소 밖 출력만
- PUSH: `git push -u origin feature/supervisor-01` 하나만
- PR_CI, MERGE: docs/tasks/README.md §3과 해당 gate의 Gate Authorization이 명시한 범위만. 이 Work Order는 그 권한을 넓히거나 줄이지 않는다.
- POST_MERGE_AUDIT: main ref만 fetch, 구조 감사
- COMPLETE: 최종 보고

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- 그 gate의 생성·변경 허용 집합(GATE_FILE_SCOPE) 밖 tracked 변경, PROTECTED_FILES 변경, 기존 test 수정
- Work Order·ERRATA 수정
- `git add .`, `git add -A`, `--no-verify`, amend, force push, reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
- hooks·settings·.claude 변경 또는 guard 우회
- 다른 branch·worktree·untracked·ignored·reference 산출물, egg-info, 외부 venv, scratchpad 정리
- 저장소 안 임시·보고·cache 파일, 파일 redirect·tee·rm workflow
- 의존성 추가·변경, pip install (TOOL_ENV_SETUP의 editable 재지정 제외)
- LLM·외부 AI API 호출, network 호출 (git fetch·push 제외), 거래·paper·live 연결
- 저장소 내용에 사용자 홈 절대 경로 기록, 비밀값 출력

## C1_FILES

C1_FILES (WORKSPACE_SETUP의 C1 commit 전용):
- A docs/tasks/SUPERVISOR-01/WORK_ORDER.md

## ALLOWED_FILES

ALLOWED_FILES (IMPLEMENTATION·COMMIT의 Ci 전용):
- A src/moneylab/supervisor/__init__.py
- A src/moneylab/supervisor/proposal.py
- A src/moneylab/supervisor/__main__.py
- A tests/test_supervisor_proposal.py
- A tests/test_supervisor_isolation.py
- A docs/supervisor_proposal_contract.md

task 전체 경로 = 7 (C1 1 + Ci 6). 목록 밖 경로는 같은 디렉터리라도 허용하지 않는다.

## GATE_FILE_SCOPE

GATE_FILE_SCOPE:

| gate | 생성·변경 허용 | 보호 |
|---|---|---|
| DISCOVERY_INVENTORY ~ WORK_ORDER_REVIEW | 없음 (채팅만) | 저장소 전체 |
| WORKSPACE_SETUP | C1_FILES 1개 (C1 commit에서만) | 그 밖 전체 |
| TOOL_ENV_SETUP, Q0_MEASUREMENT | tracked 없음 (외부 venv만) | 저장소 전체 |
| IMPLEMENTATION, COMMIT | ALLOWED_FILES 6개 | C1_FILES 포함 그 밖 전체 |
| PRECOMMIT_AUDIT, CLEAN_COMMIT_E2E 이후 | 없음 | 저장소 전체 |
| ACCEPTED ERRATA | `docs/tasks/SUPERVISOR-01/ERRATA-<NNN>.md` 1개 (사용자 수락 후 자체 commit, docs/tasks/README.md 절차) | 그 밖 전체 |

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/SUPERVISOR-01/** (C1 이후 전부; C1 commit에서는 C1_FILES 외 전부)
- docs/tasks/** 의 기존 파일 전체
- src/moneylab/knowledge/** (__init__.py, __main__.py, context.py, load.py, model.py, query.py, validate.py)
- knowledge/** (SCHEMA.md, CONTEXT_CONTRACT.md, records/**)
- tests/** 의 기존 파일 전체 (test_knowledge_*.py, test_architecture_and_cli.py, conftest.py, fixtures/** 포함)
- src/moneylab/cli.py
- src/moneylab/analytics/**, backtest/**, core/**, display/**, domain/**, execution/**, paper/**, pnl/**, providers/**, recording/**, research/**, risk/**, scanner/**, sizing/**, storage/**, strategy/**
- README.md, ARCHITECTURE.md, CLAUDE.md, LICENSE, docs/agent_workflow.md
- pyproject.toml, requirements*.txt, .github/**, .claude/**, configs/**, .gitignore, .gitattributes, .env.example
- examples/**, data/**
- 그 밖에 CANONICAL_BASE_SHA 시점에 존재하는 모든 파일

INVARIANT: 각 gate에서 (그 gate의 생성·변경 허용 집합) ∩ PROTECTED_FILES = ∅. C1_FILES ∩ ALLOWED_FILES = ∅. 의존성 변경 0. 기존 test helper(`tests/test_knowledge_validate.py`의 `git_repo`, `needs_git`, `record`, `write`)는 import로만 재사용하고 수정하지 않는다.

## DESIGN_CONTRACT (D1–D31, CONTRACT_REVIEW에서 고정, WORK_ORDER_REVIEW에서 보완)

### 권위 경계
- 권위 원천: Git이 추적하는 knowledge record만. ContextRequest, ContextPacket, proposal, check 결과, CLI 출력, Claude·model memory, 대화, scratchpad는 권위가 없다.
- D31 NO_AUTHORITY: proposal, `validate_proposal`, `check_proposal`, 결과 문서 어느 것도 승인·실행 권한·실행 준비·과학적 타당성을 주거나 뜻하지 않는다. 구조 유효(`validate_proposal` 통과)와 입력 불변(`CURRENT`)은 그 이상의 의미가 없다. 채택 권한은 사람의 gate를 거친 Git record와 Work Order에만 있다.
- D23 POLICY_BOUNDARY: Claude Code guard(`.claude/hooks/guard.py`)는 개발 도구 guard이며 MoneyLab runtime sandbox·Policy Engine이 아니다. 이 slice의 안전은 능력 부재(D22)로 보장한다. Policy Engine은 별도 task다.

### schema (D1–D2)
- D1 문서 schema 3종. 세 문서 모두 `boundary` = `NON_AUTHORITATIVE_PROPOSAL` (상수).
  - `moneylab.supervisor.result/1`: `{schema, boundary, outcome, proposal_count, proposals}`. `outcome` ∈ `PROPOSALS_CREATED` | `NO_CANDIDATES`. `proposals`는 D7 순서.
  - `moneylab.supervisor.proposal/1`: 최상위·중첩 키 집합이 아래와 정확히 같다.
    - `schema`, `boundary`, `proposal_id`, `candidate_key`, `candidate_type`, `epistemic_classification`
    - `source`: `{record_ids: [id] (정확히 1개), record_sha256: {id: "sha256:<hex>"}, quoted_text: {id: {title, statement}}, text_role: "QUOTED_RECORD_DATA"}`
    - `objective`: `{form: "DETERMINISTIC_TEMPLATE", text}`
    - `expected_evidence`, `failure_criteria`: 각각 `{specification: "UNSPECIFIED_REQUIRES_HUMAN", reviewer_questions: [D18 고정 목록]}`
    - `scope_limitations`, `prohibited_actions`, `limitations`, `unresolved_assumptions`: 문자열 목록 (D19)
    - `provenance`: `{mode, request, packet_sha256, trust_state: {exit_code, source_status}, generator: {name: "moneylab.supervisor", rules_version: 1}}`
  - `moneylab.supervisor.check/1`: `{schema, boundary, proposal_id, staleness, source_status, context_status, knowledge_tree, reasons}` (D16).
- D2 금지 키: proposal 어디에서든 키로 `approved`, `approval`, `authorization`, `authorized`, `status`, `work_order`, `work_order_id`, `gate`, `allowed_files`, `branch`, `commit`, `command`, `commands`, `script`, `shell`, `execute`, `run`, `worker`, `dispatch`, `order`, `orders`, `capital`, `allocation`, `priority`, `score`, `rank`가 나오면 거부한다. 인용 텍스트 값은 검사 대상이 아니다. 엄격 schema 위의 이중 방어다.

### 입력과 후보 (D3–D9)
- D3 입력은 CE-02 ContextRequest(`moneylab.context.request/1`) 하나. 외부 packet은 받지 않는다. packet은 언제나 in-process `resolve_context(kb, request)`로 만든다. Supervisor 전용 요청 필드·옵션은 없다. 구현은 `resolve_context`를 `moneylab.supervisor.proposal` 모듈 namespace로 import한다 (test 주입 지점).
- D4 후보 (packet 구획 기준, kind가 아닌 구획이 분류를 정한다):
  - `questions` 구획 item 중 `record.payload.state == "OPEN"` → `OPEN_QUESTION`
  - `decisions` 구획 item 중 `record.payload.state == "PENDING"` → `PENDING_DECISION`
  - `hypotheses` 구획(IDEATION만) item 중 kind `claim`, 또는 state OPEN인 question, 또는 state PENDING인 decision → `HYPOTHESIS` (layer가 우선, 원래 kind·state는 인용으로 보존)
  - 그 밖의 구획·state(task_context, facts, derived, ANSWERED·WITHDRAWN question, DECIDED decision, HYPOTHESIS layer의 task·ANSWERED·WITHDRAWN·DECIDED)는 후보가 아니다.
- D5 record 하나 → proposal 하나. 묶음, 관계, 의존·차단 추론 없음.
- D6 검사 경계:
  - `PACKET_INVALID`는 packet 구조 불변식만 검사한다: `schema`·`boundary` 상수, `trust_state.exit_code == 0`, `request == normalize_request(request)`, 구획 키 6개 존재, EVIDENCE 모드의 `hypotheses` 빈 목록, `truncation` 키 집합.
  - record 단위 검사는 후보 item에만 trusted KB 공개 API로 한다: `kb.get(id)`가 존재 (아니면 `SOURCE_RECORD_MISSING`), `kb.is_current(id)` (아니면 `SOURCE_RECORD_SUPERSEDED`), kind·layer·state가 item과 일치하고 `kb.get(id) == item["record"]` (아니면 `SOURCE_RECORD_MISMATCH`). 후보가 아닌 context item은 record 단위로 다시 검사하지 않는다 (CE-02가 보장).
  - source digest는 packet item의 canonical hash다 (CE-02 비공개 이름 미사용).
- D7 순서: (`OPEN_QUESTION`=1, `PENDING_DECISION`=2, `HYPOTHESIS`=3), 그다음 record ID 사전순. 나열 순서일 뿐 우선순위·순위가 아니다.
- D8 `packet.truncation.truncated == true`이면 proposal 없이 `PACKET_TRUNCATED`. 예산 조정은 요청자의 몫이다.
- D9 후보 0개이고 truncation이 없으면 `outcome = NO_CANDIDATES`, `proposals = []`. 대체 목표를 만들지 않는다.

### 식별자·hash·출처 (D10–D15)
- D10 canonical bytes: `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")`. hash = `"sha256:" + sha256(bytes).hexdigest()`. CLI 표시 형식(`model.canonical_json`)과 다르며 hash는 언제나 in-memory 객체로 계산한다. `packet_sha256` = packet dict의 hash. `record_sha256[id]` = 해당 packet item의 hash.
- D11 `proposal_id` = `proposal_id` 키를 뺀 proposal 전체의 hash. 일부 필드만 hash하지 않는다 (모드·요청·packet·규칙 버전이 다른 proposal의 충돌 방지).
- D12 `candidate_key` = `"<candidate_type>:<record_id>"`. snapshot이 바뀌어도 유지되는 비교용 키. 한 실행 안에서 중복이면 `CANDIDATE_DUPLICATE`. 실행 사이 중복 판단은 Supervisor가 하지 않는다 (상태 저장 없음).
- D13 provenance: `mode`(= `request.mode`), 정규화된 `request`, `packet_sha256`, `trust_state` (`exit_code` = 0, `source_status` ∈ `VERIFIED` | `NO_SOURCES`), `generator`. `limitations`에 `KNOWLEDGE_TREE_NOT_VERIFIED`, `scope_limitations`에 `CONTEXT_SCOPED_TO_REQUEST`를 둔다 (D19). packet hash는 요청 범위만 묶는다.
- D14 git tree SHA·commit SHA는 기록하지 않는다. tree SHA를 얻으려고 git subprocess를 추가하지 않는다 (FUTURE).
- D15 결정적이지 않은 필드(시각, host, 사용자, 경로, 난수) 없음. 같은 trusted 입력 → 같은 bytes.

### 최신 여부 (D16)
- D16 세 차원:
  - `CURRENT_CONTEXT`: `provenance.request`로 지금 KB에서 다시 만든 packet의 hash가 같다.
  - `CURRENT_SOURCE`: source가 존재·current·후보 자격 유지, 다시 만든 packet의 해당 item digest와 인용문이 같다.
  - `CURRENT_KNOWLEDGE_TREE`: 확인하지 않는다. `knowledge_tree` = `"NOT_VERIFIED"` (상수). 저장소·Knowledge 전체 동일성을 주장하지 않는다.
- 판정 단계 (D24 check 오류 우선순위를 통과한 뒤, 끝까지 평가해 이유를 모은다):
  - S1 source (KB 공개 API): 없음 → `SOURCE_MISSING`; current 아님 → `SOURCE_SUPERSEDED`; kind·layer·state가 `candidate_type` 자격을 잃음 → `SOURCE_INELIGIBLE` (앞의 것이 있으면 뒤의 것은 평가하지 않는다)
  - S2 다시 resolve: CE-02 `REQUIRED_NOT_FOUND` / `REQUIRED_SUPERSEDED` / `REQUIRED_LAYER_NOT_ELIGIBLE` / `REQUIRED_OVER_BUDGET` → `CONTEXT_UNRESOLVABLE:<code>` (packet 없음, S3·S4 생략)
  - S3 다시 만든 packet: truncated → `CONTEXT_TRUNCATED`; hash 다름 → `PACKET_HASH_CHANGED`
  - S4 source item: packet에 있고 digest 다름 → `SOURCE_MODIFIED`; packet에 없거나 S2로 packet이 없고 S1 이유도 없음 → `SOURCE_NOT_IN_CONTEXT`
- reason 코드는 check 결과 `reasons` 전용이며 오류 코드와 별개의 이름 공간이다. `reasons`는 사전순.
- `source_status`: `SOURCE_MISSING|SOURCE_SUPERSEDED|SOURCE_INELIGIBLE|SOURCE_MODIFIED` 중 하나라도 있으면 `STALE_SOURCE`; 없고 `SOURCE_NOT_IN_CONTEXT`이면 `NOT_VERIFIED`; 둘 다 없으면 `CURRENT`.
- `context_status`: `CONTEXT_*` 또는 `PACKET_HASH_CHANGED`가 하나라도 있으면 `STALE_CONTEXT`, 아니면 `CURRENT`.
- `staleness`: `STALE_SOURCE` > `STALE_CONTEXT` (`context_status = STALE_CONTEXT` 또는 `source_status = NOT_VERIFIED`) > `CURRENT`.
- 사례: 관련 없는 record 변경으로 packet이 같으면 `CURRENT`. packet이 바뀌고 source가 같으면 `STALE_CONTEXT`. source가 대체·수정·삭제되거나 자격을 잃으면 `STALE_SOURCE`.

### 인식론·과학 경계 (D17–D19)
- D17 `epistemic_classification`: `OPEN_QUESTION` ↔ `QUESTION_NOT_EVIDENCE`, `PENDING_DECISION` ↔ `PENDING_NOT_APPROVED`, `HYPOTHESIS` ↔ `HYPOTHESIS_NOT_EVIDENCE`. HYPOTHESIS는 IDEATION에서만 생기고 limitation `HYPOTHESIS_ONLY_BASIS`가 필수이며 증거 필드가 없다. EVIDENCE 모드 packet의 `hypotheses`가 비어 있지 않으면 `PACKET_INVALID`.
- D18 `objective.text`는 record ID만 쓰는 고정 template:
  - OPEN_QUESTION: `Investigate open question <id>. The question is not evidence.`
  - PENDING_DECISION: `Gather information a human reviewer may use for pending decision <id>. The decision is not approved.`
  - HYPOTHESIS: `Design a test of hypothesis <id>. The hypothesis is not evidence.`
  - record의 `title`·`statement`는 `source.quoted_text`에 그대로 복사만 하고 해석하지 않는다 (DATA_NOT_INSTRUCTIONS).
  - `expected_evidence.reviewer_questions` (순서 고정):
    1. `What observation would answer or advance the source record?`
    2. `What data, with what provenance, would be required?`
    3. `Which frozen or preregistered contract constrains this work?`
  - `failure_criteria.reviewer_questions` (순서 고정):
    1. `What result would count as failure or falsification?`
    2. `What result would make further work on this candidate not worthwhile?`
    3. `What is explicitly out of scope?`
  - 과학적 기준을 만들어 내지 않는다 (`specification` = `UNSPECIFIED_REQUIRES_HUMAN`).
- D19 상수 목록 (순서 고정; `docs/supervisor_proposal_contract.md`와 코드 상수가 같아야 한다):
  - `scope_limitations`: `SINGLE_SOURCE_RECORD`, `CONTEXT_SCOPED_TO_REQUEST`, `NO_DEPENDENCY_OR_BLOCKING_INFERENCE`, `NO_PRIORITY_OR_RANKING`
  - `prohibited_actions`: `EXECUTE_RESEARCH`, `DISPATCH_WORKER`, `MODIFY_REPOSITORY`, `MODIFY_KNOWLEDGE_RECORDS`, `CREATE_OR_APPROVE_WORK_ORDER`, `PROMOTE_EPISTEMIC_STATUS`, `ALLOCATE_CAPITAL`, `PLACE_ORDERS`, `CONNECT_PAPER_OR_LIVE`, `CLAIM_PROFITABILITY_OR_ALPHA`
  - `limitations`: 고정 `NOT_VALIDATED`, `NOT_READY_TO_RUN`, `NOT_A_WORK_ORDER`, `DETERMINISTIC_TEMPLATE_ONLY`, `KNOWLEDGE_TREE_NOT_VERIFIED` 다음에 파생 항목 사전순: `EXCLUDED_COUNT:<reason>:<n>` (packet `excluded`의 reason ∈ `layer_not_eligible` | `superseded`, n ≥ 1), `HYPOTHESIS_ONLY_BASIS`
  - `unresolved_assumptions`: 고정 `EXPECTED_EVIDENCE_NOT_DEFINED`, `FAILURE_CRITERIA_NOT_DEFINED` 다음에 파생 항목 사전순: `SOURCE_EVIDENCE_MISSING:evidence[<i>]` (source EvidenceRef `availability == "MISSING"`)
- 과학적 결론, 순위, 점수, 실행 준비, 수익성·alpha 주장 없음.

### 패키지·API·CLI (D20–D21)
- D20 새 패키지 `moneylab.supervisor`. 의존 방향은 supervisor → knowledge 한 방향 (knowledge는 supervisor를 import하지 않는다).
  - 허용 import: `__future__`, `json`, `hashlib`, `re`, `typing`; `__main__.py`에만 `argparse`, `sys`, `pathlib`(`Path` 인자 타입 전용)
  - 허용 moneylab 이름 (공개 이름만): `moneylab.knowledge`의 `REPO_ROOT`, `KnowledgeBase`, `ContextRequestError`, `open_knowledge_base`(`__main__.py`만), `resolve_context`; `moneylab.knowledge.context`의 `normalize_request`, `REQUEST_INVALID`, `REPOSITORY_UNTRUSTED`, `PACKET_SCHEMA`; `moneylab.knowledge.query`의 `KnowledgeStateError`; `moneylab.knowledge.model`의 `CONTEXT_BOUNDARY`, `canonical_json`
  - 밑줄로 시작하는 knowledge 이름은 쓰지 않는다.
  - 공개 API (`moneylab.supervisor`): `propose(kb, request) -> dict` (result/1), `validate_proposal(obj) -> None`, `check_proposal(kb, proposal) -> dict` (check/1), `SupervisorError(code, detail)`. CE-02 오류(`ContextRequestError`, `KnowledgeStateError`)는 그대로 전파한다.
  - KB 열기(`open_knowledge_base`, 경계 B의 read-only git)는 `__main__.py`와 호출자에서만 한다. API 함수는 열린 `kb`를 받는다.
- D21 CLI: `python -m moneylab.supervisor [--root R] propose` (stdin: ContextRequest JSON 하나), `python -m moneylab.supervisor [--root R] check` (stdin: proposal JSON 하나). stdout에 `model.canonical_json` 출력. stdin은 UTF-8, 중복 키·NaN 거부. 파일 인자·출력 옵션 없음. `cli.py`는 바꾸지 않는다.

### 실행 격리 (D22)
- D22 경계 A (Supervisor 자신, `src/moneylab/supervisor/**`): shell·subprocess, network, 파일 쓰기, worker·thread·process 생성, 거래 기능이 하나도 없다.
- 경계 B (기존 knowledge validator의 read-only git, `open_knowledge_base` 경유): 이미 검토된 별도 경계다. Supervisor 능력으로 세지 않고, 바꾸거나 막지 않으며, 간접 의존으로 인정한다. `resolve_context`는 git을 호출하지 않는다.
- 증명: T17–T20 (회귀 방지이지 sandbox가 아니다).

### 실패·종료 코드 (D24)
- D24 오류 출력: `{"error": {"code", "detail"}}` (untrusted이면 `validation` 포함, CE-02 관례). 모든 오류는 all-or-nothing: 일부 proposal을 출력하지 않는다. 처음 해당하는 오류 하나만 보고한다.
- propose 우선순위: (1) stdin JSON 오류 → `REQUEST_INVALID` (2) KB untrusted → `REPOSITORY_UNTRUSTED` (3) CE-02 `REQUEST_INVALID` (4) CE-02 `REQUIRED_NOT_FOUND` / `REQUIRED_SUPERSEDED` / `REQUIRED_LAYER_NOT_ELIGIBLE` / `REQUIRED_OVER_BUDGET` (5) `PACKET_INVALID` (6) `PACKET_TRUNCATED` (7) 후보별(D7 순서) `SOURCE_RECORD_MISSING` > `SOURCE_RECORD_SUPERSEDED` > `SOURCE_RECORD_MISMATCH` (8) `CANDIDATE_DUPLICATE`.
- check 우선순위: (1) stdin JSON 오류 또는 `validate_proposal` 실패 → `PROPOSAL_INVALID` (KB 접근 없음) (2) KB untrusted → `REPOSITORY_UNTRUSTED` (3) 재resolve의 `REQUEST_INVALID` → `CHECK_REQUEST_REJECTED` (4) source item digest가 같은데 인용문이 다름 → `PROPOSAL_INVALID` (5) 그 밖은 D16 판정.
- propose 중 source 문제는 오류이고, check 중에는 D16 판정(`STALE_SOURCE`)이다.
- 종료 코드:

| 명령 | 0 | 1 | 2 | REPOSITORY_UNTRUSTED |
|---|---|---|---|---|
| propose | `PROPOSALS_CREATED`, `NO_CANDIDATES` | `REQUIRED_*`, `PACKET_INVALID`, `PACKET_TRUNCATED`, `SOURCE_RECORD_MISSING`, `SOURCE_RECORD_SUPERSEDED`, `SOURCE_RECORD_MISMATCH`, `CANDIDATE_DUPLICATE` | `REQUEST_INVALID` | report.exit_code (1, SOURCE_UNVERIFIED는 3) |
| check | `CURRENT` | `STALE_SOURCE`, `STALE_CONTEXT` | `PROPOSAL_INVALID`, `CHECK_REQUEST_REJECTED` | report.exit_code (1, SOURCE_UNVERIFIED는 3) |

### 검증 책임 (D29–D30)
- D29 `validate_proposal(obj) -> None` (실패 시 `SupervisorError("PROPOSAL_INVALID", detail)`): 구조·결정성 검증만 한다. KnowledgeBase·파일·git에 접근하지 않는다. `record_sha256`·`quoted_text`는 형식과 내부 일관성만 확인하며, 통과는 source 진위·최신성·승인을 뜻하지 않는다. 순서대로:
  1. JSON 호환성 (재귀: 키 str, 값 str·int·bool·None·list·dict; float 거부)
  2. 엄격 schema: 모든 층의 키 집합 정확히 일치 (D1), 필드 타입
  3. 상수: `schema`, `boundary`, `generator` (`name`, `rules_version` = 1만), `source.text_role`, `objective.form`, `specification`
  4. 금지 키 (D2)
  5. 일관성: `candidate_type` ↔ `epistemic_classification` (D17), `record_ids` 1개와 `record_sha256`·`quoted_text` 키 일치, `candidate_key` (D12), `provenance.mode == provenance.request.mode`, HYPOTHESIS ⇒ IDEATION·`HYPOTHESIS_ONLY_BASIS`
  6. `provenance.request == normalize_request(provenance.request)`
  7. template: `objective.text` 재렌더링 바이트 일치, `reviewer_questions` 고정 목록 일치 (D18)
  8. 목록: `scope_limitations`·`prohibited_actions` 고정 목록과 순서까지 일치; `limitations`·`unresolved_assumptions`는 고정 항목 전부 + 허용 패턴만, 사전순 (D19)
  9. hash 형식 `^sha256:[0-9a-f]{64}$`, `trust_state` 허용 값 (D13)
  10. `proposal_id` 재계산 일치 (D11)
- D30 `check_proposal(kb, proposal) -> dict` (check/1): D29 전체 다음에 trusted KB, source 존재·current·자격, 다시 만든 packet의 source item digest·인용문, 요청 재resolve와 packet hash, D16 판정. 아무것도 쓰거나 기록하지 않는다. `CURRENT`는 요청 범위 입력 불변만 뜻한다.

### 범위·호환 (D25–D28)
- D25 LLM, worker, scheduler, 순위, 상태 저장, paper·live, 자본은 범위 밖.
- D26 CE-02 LOW 소견 #1–#5는 고치지 않고 이월한다. Supervisor 자체 JSON 호환성 검사(D29-1)는 CE-02 수정이 아니다.
- D27 docs/tasks/README.md §3의 PR_CI·MERGE 문구와 최근 관행의 차이는 별도 governance task 대상이다. 이 Work Order는 gate 권한을 재정의하지 않는다.
- D28 CE-02 구현, knowledge schema·record·validator·query, 기존 CLI(`validate`, `query`, `resolve-context`)의 동작과 바이트를 바꾸지 않는다. 새 의존성 없음, stdlib만.

## TEST_ISOLATION

TEST_ISOLATION:
- 합성 record는 pytest `tmp_path` 아래 임시 git 저장소(기존 helper)에만 쓴다. 저장소 worktree 안에 파일을 만들지 않는다.
- 저장소 자신의 seed record는 읽기만 한다 (`open_knowledge_base(REPO)`, REPO는 `__file__` 기준). seed·PROTECTED_FILES를 쓰거나 바꾸지 않는다.
- 절대 경로(C:/MoneyLab과 사용자 홈 포함)를 test에 쓰지 않는다. C:/MoneyLab과 다른 worktree를 읽거나 쓰지 않는다.
- 실행은 `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`. 실행 후 `git status --porcelain --untracked-files=all`이 비어 있어야 한다 (AU10).

## TEST_GATES

TEST_GATES (새 test 파일 2개; 기존 test 파일 수정 없음):
- 파일 배정: `tests/test_supervisor_proposal.py` = T1–T16, T21–T23, T25; `tests/test_supervisor_isolation.py` = T17–T20; T24 = 기존 test suite (새 파일 없음, 기존 파일 수정 없음).
- T1 결정성: 같은 trusted KnowledgeBase와 ContextRequest → API 결과 바이트 동일; CLI 반복 실행 출력 동일; API와 CLI 출력은 CRLF 정규화 후 일치; PYTHONHASHSEED·작업 디렉터리 변화에도 결정적
- T2 hash 안정성: `proposal_id`·`packet_sha256`·`record_sha256`을 D10·D11로 재계산해 일치; 합성 고정 입력의 golden 값(test 파일 안 상수) 일치
- T3 identity 구분 (유효한 v1만): 모드, 요청 필드, 예산, source record 중 하나만 다른 유효 v1 proposal끼리 `proposal_id`가 다르고 모두 `validate_proposal` 통과
- T4 candidate_key 유지: 관련 없는 record 추가 후 다시 만든 proposal은 `proposal_id`가 다를 수 있으나 `candidate_key`는 같음
- T5 미래 rules_version: 유효 proposal 사본의 `generator.rules_version`을 2로 바꾸고 D10·D11로 계산한 hash는 원래와 다름; 같은 사본에 `validate_proposal` → `PROPOSAL_INVALID` (v1 엄격 검증 유지)
- T6 schema 엄격성: 모든 층의 키 누락·추가, 타입 오류, float, 비문자열 키, 상수 위반, template·reviewer_questions·고정 목록 변조, 패턴 밖 limitation·assumption → `PROPOSAL_INVALID`
- T7 자기 승인 없음: 모든 출력에 `boundary` 상수; D2 금지 키 각각을 넣은 proposal → `PROPOSAL_INVALID`; 생성 출력에 금지 키 없음
- T8 인식론: EVIDENCE에서 HYPOTHESIS 후보 0; IDEATION에서 `HYPOTHESIS_NOT_EVIDENCE` + `HYPOTHESIS_ONLY_BASIS`, 증거 필드 없음; HYPOTHESIS layer의 OPEN question·PENDING decision은 `HYPOTHESIS`로 분류; PENDING은 `PENDING_NOT_APPROVED`
- T9 current-only 선택: 대체된 record는 후보 아님; ANSWERED·WITHDRAWN question과 DECIDED decision은 후보 아님; `include_ids`의 대체 record → `REQUIRED_SUPERSEDED` 전파
- T10 propose 방어 경로 (test가 `moneylab.supervisor.proposal.resolve_context`를 실제 packet의 변조 사본을 돌려주는 함수로 교체): KB에 없는 후보 id → `SOURCE_RECORD_MISSING`; 대체된 record를 후보 구획에 넣음 → `SOURCE_RECORD_SUPERSEDED`; 후보 item의 record 내용 변조 → `SOURCE_RECORD_MISMATCH`; `boundary` 변조 → `PACKET_INVALID`; 같은 후보 중복 → `CANDIDATE_DUPLICATE`; 모든 경우 출력 proposal 없음
- T11 truncation: `truncated == true` → `PACKET_TRUNCATED`, 출력 없음; 예산이 정확히 맞는 경계에서는 정상
- T12 stale 우선순위: source 대체 → `STALE_SOURCE` (`SOURCE_SUPERSEDED`); source 수정 → `STALE_SOURCE` (`SOURCE_MODIFIED` 또는 `SOURCE_INELIGIBLE`); source 삭제 → `STALE_SOURCE` (`SOURCE_MISSING`); 관련 record가 packet에 새로 들어옴 → `STALE_CONTEXT`·source `CURRENT`; source와 context 동시 → `STALE_SOURCE`; source가 packet에서 잘림 → `NOT_VERIFIED`·`STALE_CONTEXT`
- T13 관련 없는 변경: 요청 범위 밖 record 추가·변경, packet 동일 → `CURRENT`, `knowledge_tree == "NOT_VERIFIED"`
- T14 check 오류 경로: 무효 proposal → `PROPOSAL_INVALID`이고 KB 메서드 호출 없음; digest 같고 인용문 다름 → `PROPOSAL_INVALID`; 재resolve가 `REQUEST_INVALID`를 던지도록 교체 → `CHECK_REQUEST_REJECTED`
- T15 잘못된 입력·신뢰: CE-02 `REQUEST_INVALID` 대표 사례 → propose exit 2; untrusted KB → API `KnowledgeStateError`, CLI exit 1; SOURCE_UNVERIFIED → CLI exit 3; 모두 출력 proposal 없음
- T16 후보 없음: `NO_CANDIDATES`, `proposals == []`, 대체 목표 없음
- T17 능력 부재 (AST): import가 D20 허용 목록 밖이면 실패; `open`, `eval`, `exec`, `compile`, `__import__`, `breakpoint`, `input` 호출 금지; `write_text`, `write_bytes`, `mkdir`, `unlink`, `touch`, `rename`, `replace`, `rmdir` 속성 호출 금지; `sys`는 `stdin`, `stdout`, `stderr`, `exit`, `argv`만; 밑줄 knowledge 이름 금지; knowledge가 supervisor를 import하지 않음
- T18 runtime tripwire: KB를 연 뒤 `propose`·`validate_proposal`·`check_proposal` 실행 동안 `subprocess.Popen`, `os.system`, `os.popen`, `socket.socket`, `socket.create_connection`, `builtins.open`, `threading.Thread.start`, `multiprocessing.Process.start`를 예외를 던지게 바꿔도 결과 정상. `open_knowledge_base`(경계 B)는 대상 밖
- T19 모듈 미로딩: 새 interpreter(`sys.executable`)에서 `moneylab.supervisor`를 import하고 propose·check를 실행한 뒤 `sys.modules`에 `moneylab.execution`, `moneylab.paper`, `moneylab.providers`, `moneylab.recording`, `moneylab.core.http`, `moneylab.sizing`, `moneylab.risk`, `moneylab.research`, `moneylab.backtest`, `moneylab.scanner`, `moneylab.strategy`가 없음
- T20 파일 변경 없음: tmp KB에서 API·CLI 실행 전후 파일 목록·바이트 동일; CLI를 cwd=tmp로 실행해도 새 파일 없음; CLI parser에 파일 출력 옵션 없음
- T21 CLI: D24 종료 코드·오류 우선순위 전부, 오류 출력 `{"error": {"code", "detail"}}`, 정상 출력 `canonical_json`
- T22 결과 격리: 반환된 result·proposal·check를 수정해도 다음 호출과 KB에 영향 없음; 같은 프로세스 연속 호출 바이트 동일
- T23 seed 7개: EVIDENCE 무필터 요청 → 2개 (`question/BT4-RESEARCH-01/futility-boundary-cause`, `decision/BT4-DESIGN-01/d3`); IDEATION 무필터 요청 → 3개 (+ `claim/BT4-RESEARCH-01/futility-mean-block-hypothesis`); 모두 `validate_proposal` 통과, `check_proposal` = `CURRENT`
- T24 CE-02 회귀 보존: 새 test를 작성하지 않는다. 기존 test suite(`tests/test_knowledge_*.py` 포함 전체)를 수정 없이 전체 pytest로 실행해, Q0 기준선 대비 새 실패·오류 0이고 기존 knowledge test가 전부 통과하는 것으로 판정한다.
- T25 검증 책임 분리: 형식은 맞지만 지어낸 `record_sha256`·`quoted_text`를 가진 proposal(올바른 `proposal_id` 재계산 포함)은 `validate_proposal`을 통과하고 `check_proposal`에서 `STALE_SOURCE` 또는 `PROPOSAL_INVALID`
- 전체 pytest: Q0 기준선 대비 새 실패·오류 0 (Q0에서 측정된 기준선 실패만 허용)

## E2E_GATES

E2E_GATES (CLEAN_COMMIT_E2E에서 clean Ci commit으로 실행; stdin → stdout 파이프만, 파일 redirect·임시 파일 없음):
- E1 `python -m moneylab.knowledge validate` exit 0, VERIFIED
- E2 `python -m moneylab.supervisor propose`에 seed EVIDENCE 무필터 요청을 두 번 → 바이트 동일, 2개
- E3 IDEATION 무필터 요청을 두 번 → 바이트 동일, 3개
- E4 E3 출력의 각 proposal을 읽기 전용 stdout parser로 뽑아 `python -m moneylab.supervisor check`에 파이프 → `CURRENT`, exit 0 (parser가 guard ASK를 일으키면 멈추고 1회 승인을 받는다)
- E5 실행 전후 `git status --porcelain --untracked-files=all` 동일

## AUDIT_CHECKS

AUDIT_CHECKS:
- AU1 Ci 변경 경로 집합 = ALLOWED_FILES 6개, task 전체 7개
- AU2 PROTECTED_FILES 바이트 동일 (base 대비 diff 0)
- AU3 pyproject.toml·requirements*.txt 불변 (의존성 변경 0)
- AU4 `git diff --check` 깨끗
- AU5 ruff `--select E4,E7,E9,F src tests` 통과
- AU6 기존 설정 mypy 통과, `src/moneylab/supervisor` mypy(`--follow-imports=silent`) 통과
- AU7 `python -m moneylab.knowledge validate` exit 0
- AU8 C1 blob sha256 = WORKSPACE_SETUP 보고 값, C1 이후 불변
- AU9 WORKSPACE_SETUP의 fetched main commit·tree = CANONICAL_BASE_SHA·CANONICAL_BASE_TREE
- AU10 test 실행 후 저장소에 untracked·ignored 신규 파일 없음

## EXECUTION_RESPONSIBILITY

EXECUTION_RESPONSIBILITY:

| ID | 실행 gate | 실행 수단 |
|---|---|---|
| AU9 | WORKSPACE_SETUP (B·C 단계) | git 읽기 |
| AU8 | WORKSPACE_SETUP (기록), PRECOMMIT_AUDIT·POST_MERGE_AUDIT (재확인) | git 읽기·sha256 |
| T1–T23, T25 | IMPLEMENTATION (targeted + 전체 pytest), CLEAN_COMMIT_E2E (전체 pytest 재실행) | 새 test 파일 2개 |
| T24 | IMPLEMENTATION, CLEAN_COMMIT_E2E | 기존 test suite, 전체 pytest |
| AU10 | IMPLEMENTATION·CLEAN_COMMIT_E2E의 test 실행 직후 | git status |
| AU1–AU7 | PRECOMMIT_AUDIT (AU1·AU2는 POST_MERGE_AUDIT에서 merge 기준 재확인) | git 읽기, ruff, mypy, knowledge validate |
| E1–E5 | CLEAN_COMMIT_E2E | CLI 파이프 |
| Q0 기준선 | Q0_MEASUREMENT | 전체 pytest, ruff, mypy, knowledge validate |
| CI | PR_CI | GitHub Actions (INDEPENDENT) |

## SUCCESS_CRITERIA

SUCCESS_CRITERIA:
- SC1 범위: AU1, AU8, AU9
- SC2 보호·회귀: AU2, T24
- SC3 정적 품질: AU4, AU5, AU6, AU7
- SC4 기능: T1–T16, T21–T23, T25 통과
- SC5 결정성: T1, T2, E2, E3
- SC6 의존성 0: AU3
- SC7 권위·인식론 경계: T5, T7, T8, T25
- SC8 실행 능력 0·격리: T17, T18, T19, T20, AU10, E5
- SC9 E2E: E1–E5

## STOP_CONDITIONS

STOP_CONDITIONS:
- AU9 불일치 (WORKSPACE_SETUP B·C 단계에서, branch·worktree·C1 생성 전)
- SOURCE_WORKTREE의 HEAD·status 변화 (WORKSPACE_SETUP D 단계)
- base·HEAD·tree 불일치, WORK_ORDER sha256 불일치
- C1_FILES 외 경로가 C1에 포함, C1 이후 docs/tasks/SUPERVISOR-01/** 변경
- 그 gate의 허용 집합 밖 변경, PROTECTED_FILES 변경, 기존 test 수정 필요
- CE-02·knowledge 변경, 비공개 API 사용, 새 의존성, pyproject 변경이 필요해짐
- test 실패, 새 회귀, 결정성 위반
- test가 저장소 worktree 안에 파일을 만들거나 seed·PROTECTED를 변경 (AU10, AU2)
- 권위 경계 위반, 증거 승격, 승인·실행 필드 출현, 실행 능력 출현
- guard deny, 권한 거절, 계약 모순, 예상하지 못한 untracked 파일

## REQUIRED_EVIDENCE

REQUIRED_EVIDENCE:
- GIT_VERIFIABLE: base(CANONICAL_BASE_SHA)·C1·Ci SHA·tree, 파일 sha256, 변경 파일 집합, merge parent·tree
- CLAUDE_REPORTED: test, ruff, mypy, propose·check 실행 결과, golden hash
- INDEPENDENT: PR CI, GitHub 화면(사용자 확인)

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- 실행한 T·E·AU ID와 결과
- 증거 등급, PROPOSED_ERRATA, DEVIATIONS, ISSUES, guard·권한 이벤트 (Claude가 보지 못한 ASK는 사용자 보고로 표시)
- <GATE>_PASS = YES / NO, READY_FOR_<NEXT_GATE> = YES / NO

## ROLLBACK_AND_FAILURE

ROLLBACK_AND_FAILURE:
- 실패하면 멈추고 보고한다. 자동 수정·재시도로 범위를 넓히지 않는다.
- COMMIT 전 실패: 명시적 승인으로 IMPLEMENTATION에서 다시 한다.
- COMMIT 이후: 새 commit으로만 고친다. 이력을 다시 쓰지 않는다.
- 계약 문제: 파일을 고치지 않고 `PROPOSED_ERRATA`로 채팅에 보고한다.

## SCIENTIFIC_AND_SECURITY_LIMITS

SCIENTIFIC_AND_SECURITY_LIMITS:
- proposal은 연구 후보의 목록일 뿐이며 검증·실행 준비·과학적 결론이 아니다. question·hypothesis는 증거가 아니고 PENDING decision은 승인이 아니다.
- record 텍스트는 데이터로만 다룬다 (prompt injection 방지). 인용만 하고 해석·실행하지 않는다.
- 비밀값·사용자 홈 경로를 코드·test·문서·출력에 넣지 않는다.
- Claude guard는 runtime 보호 장치로 간주하지 않는다.

## COMPLETION

COMPLETION: POST_MERGE_AUDIT = PASS 후 사용자가 COMPLETE를 선언한다. 완료는 Supervisor가 연구를 실행·승인할 수 있다는 뜻이 아니다.
