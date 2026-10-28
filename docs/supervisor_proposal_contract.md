# Supervisor proposal 계약 (SUPERVISOR-01)

이 문서는 `moneylab.supervisor` 첫 vertical slice가 만드는 문서의 형식과 의미를 설명한다. 권위 있는 계약은
`docs/tasks/SUPERVISOR-01/WORK_ORDER.md`(C1)이며, 이 문서와 다르면 Work Order가 우선한다. 아래 상수 목록은 코드
(`src/moneylab/supervisor/proposal.py`)와 같아야 하며 test가 이를 확인한다.

## 권위 경계

- 권위 원천은 Git이 추적하는 knowledge record뿐이다. ContextRequest, ContextPacket, proposal, check 결과, CLI 출력은
  권위가 없다.
- Proposal ≠ Work Order ≠ Authorization. proposal은 사람이 Work Order를 만들지 판단할 때 참고하는 연구 후보 목록일
  뿐이다. 검증·실행 준비·과학적 결론·승인을 뜻하지 않는다.
- Supervisor는 연구를 실행하지 않고, worker를 호출하지 않고, 파일·저장소·knowledge record를 쓰지 않고, network에
  접근하지 않고, 거래·자본 기능을 갖지 않는다.
- record 텍스트(`title`, `statement`)는 데이터로 인용만 한다(DATA_NOT_INSTRUCTIONS). 해석하거나 지시로 따르지 않는다.
- Claude Code guard는 개발 도구 guard이며 runtime sandbox나 Policy Engine이 아니다.

## 문서 schema

모든 문서의 `boundary`는 `NON_AUTHORITATIVE_PROPOSAL`이다.

- `moneylab.supervisor.result/1`: `{schema, boundary, outcome, proposal_count, proposals}`. `outcome`은
  `PROPOSALS_CREATED` 또는 `NO_CANDIDATES`.
- `moneylab.supervisor.proposal/1`: `schema`, `boundary`, `proposal_id`, `candidate_key`, `candidate_type`,
  `epistemic_classification`, `source`, `objective`, `expected_evidence`, `failure_criteria`, `scope_limitations`,
  `prohibited_actions`, `limitations`, `unresolved_assumptions`, `provenance`. 키 집합은 모든 층에서 정확히 일치해야 한다.
- `moneylab.supervisor.check/1`: `{schema, boundary, proposal_id, staleness, source_status, context_status,
  knowledge_tree, reasons}`. `knowledge_tree`는 언제나 `NOT_VERIFIED`다.

proposal 어디에서든 다음 키는 거부된다: `allocation`, `allowed_files`, `approval`, `approved`, `authorization`,
`authorized`, `branch`, `capital`, `command`, `commands`, `commit`, `dispatch`, `execute`, `gate`, `order`, `orders`,
`priority`, `rank`, `run`, `score`, `script`, `shell`, `status`, `work_order`, `work_order_id`, `worker`.

## 후보

입력은 CE-02 ContextRequest 하나이고, packet은 신뢰된 KnowledgeBase에서 in-process로 만든다. 외부 packet은 받지 않는다.

| packet 구획 | 조건 | candidate_type | epistemic_classification |
|---|---|---|---|
| `questions` | state `OPEN` | `OPEN_QUESTION` | `QUESTION_NOT_EVIDENCE` |
| `decisions` | state `PENDING` | `PENDING_DECISION` | `PENDING_NOT_APPROVED` |
| `hypotheses` (IDEATION만) | kind `claim`, OPEN question, PENDING decision | `HYPOTHESIS` | `HYPOTHESIS_NOT_EVIDENCE` |

record 하나가 proposal 하나다. 관계·의존·순위를 추론하지 않는다. 순서는 (`OPEN_QUESTION`, `PENDING_DECISION`,
`HYPOTHESIS`) 다음 record ID이며 우선순위가 아니다. truncation이 있는 packet은 proposal을 만들지 않는다
(`PACKET_TRUNCATED`). 후보가 없으면 `NO_CANDIDATES`이고 대체 목표를 만들지 않는다.

## 고정 내용

- `objective.text` (record ID만 쓰는 template):
  - `Investigate open question <id>. The question is not evidence.`
  - `Gather information a human reviewer may use for pending decision <id>. The decision is not approved.`
  - `Design a test of hypothesis <id>. The hypothesis is not evidence.`
- `expected_evidence`와 `failure_criteria`의 `specification`은 `UNSPECIFIED_REQUIRES_HUMAN`이다.
- `expected_evidence.reviewer_questions`:
  1. What observation would answer or advance the source record?
  2. What data, with what provenance, would be required?
  3. Which frozen or preregistered contract constrains this work?
- `failure_criteria.reviewer_questions`:
  1. What result would count as failure or falsification?
  2. What result would make further work on this candidate not worthwhile?
  3. What is explicitly out of scope?
- `scope_limitations`: `SINGLE_SOURCE_RECORD`, `CONTEXT_SCOPED_TO_REQUEST`, `NO_DEPENDENCY_OR_BLOCKING_INFERENCE`,
  `NO_PRIORITY_OR_RANKING`
- `prohibited_actions`: `EXECUTE_RESEARCH`, `DISPATCH_WORKER`, `MODIFY_REPOSITORY`, `MODIFY_KNOWLEDGE_RECORDS`,
  `CREATE_OR_APPROVE_WORK_ORDER`, `PROMOTE_EPISTEMIC_STATUS`, `ALLOCATE_CAPITAL`, `PLACE_ORDERS`,
  `CONNECT_PAPER_OR_LIVE`, `CLAIM_PROFITABILITY_OR_ALPHA`
- `limitations`: 고정 `NOT_VALIDATED`, `NOT_READY_TO_RUN`, `NOT_A_WORK_ORDER`, `DETERMINISTIC_TEMPLATE_ONLY`,
  `KNOWLEDGE_TREE_NOT_VERIFIED` 다음에 파생 항목 사전순: `EXCLUDED_COUNT:<reason>:<n>`, `HYPOTHESIS_ONLY_BASIS`
- `unresolved_assumptions`: 고정 `EXPECTED_EVIDENCE_NOT_DEFINED`, `FAILURE_CRITERIA_NOT_DEFINED` 다음에 파생 항목
  사전순: `SOURCE_EVIDENCE_MISSING:evidence[<i>]`

## 식별자와 출처

- canonical bytes: `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`의
  UTF-8. hash는 `"sha256:" + sha256(bytes).hexdigest()`. CLI 표시 형식과 다르다.
- `packet_sha256`: packet 전체의 hash. `record_sha256`: source packet item의 hash.
- `proposal_id`: `proposal_id` 키를 뺀 proposal 전체의 hash. `candidate_key`: `<candidate_type>:<record_id>`.
- `provenance`: `mode`, 정규화된 `request`, `packet_sha256`, `trust_state`(`exit_code` 0, `source_status` `VERIFIED`
  또는 `NO_SOURCES`), `generator`(`moneylab.supervisor`, `rules_version` 1).
- git tree·commit SHA, 시각, host, 경로는 기록하지 않는다. 같은 trusted 입력이면 같은 bytes가 나온다.

## 검증과 최신 여부

- `validate_proposal(obj)`: 구조·결정성 검증만 한다. KnowledgeBase·파일·git에 접근하지 않는다. 통과는 source
  진위·최신성·승인을 뜻하지 않는다.
- `check_proposal(kb, proposal)`: 위 검증 후 신뢰된 KB에서 source를 확인하고 기록된 요청으로 packet을 다시 만든다.
  - reason: `SOURCE_MISSING`, `SOURCE_SUPERSEDED`, `SOURCE_INELIGIBLE`, `SOURCE_MODIFIED`, `SOURCE_NOT_IN_CONTEXT`,
    `CONTEXT_UNRESOLVABLE:<code>`, `CONTEXT_TRUNCATED`, `PACKET_HASH_CHANGED`
  - `staleness`: `STALE_SOURCE` > `STALE_CONTEXT` > `CURRENT`. `CURRENT`는 요청 범위의 입력이 바뀌지 않았다는 뜻뿐이다.

## CLI

`python -m moneylab.supervisor [--root R] propose` (stdin: ContextRequest JSON),
`python -m moneylab.supervisor [--root R] check` (stdin: proposal JSON). 출력은 stdout의 canonical JSON이고 파일 옵션은
없다. 오류는 `{"error": {"code", "detail"}}`.

| 명령 | 0 | 1 | 2 |
|---|---|---|---|
| propose | `PROPOSALS_CREATED`, `NO_CANDIDATES` | `REQUIRED_*`, `PACKET_INVALID`, `PACKET_TRUNCATED`, `SOURCE_RECORD_MISSING`, `SOURCE_RECORD_SUPERSEDED`, `SOURCE_RECORD_MISMATCH`, `CANDIDATE_DUPLICATE` | `REQUEST_INVALID` |
| check | `CURRENT` | `STALE_SOURCE`, `STALE_CONTEXT` | `PROPOSAL_INVALID`, `CHECK_REQUEST_REJECTED` |

신뢰되지 않은 저장소는 `REPOSITORY_UNTRUSTED`와 검증 report를 출력하고 검증 exit code(1, SOURCE_UNVERIFIED는 3)로
끝난다.
