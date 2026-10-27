# Context resolution contract (`moneylab.context.request/1` → `moneylab.context.packet/1`)

This page explains how a ContextRequest is resolved into a ContextPacket. It is **not** a source of truth for
knowledge and not a second record schema: the authoritative knowledge is the set of Git-tracked, immutable records
under `knowledge/records/` (format in `SCHEMA.md`), and the authoritative contract for this page is
`docs/tasks/CONTEXT-ENGINE-02/WORK_ORDER.md`. If this page and the contract disagree, the contract wins.

## Authority

- **Authoritative:** Git-tracked immutable knowledge records (`moneylab.knowledge.record/1`) only.
- **Non-authoritative input:** a ContextRequest. Its `objective` is data: it is echoed back and never interpreted,
  tokenized, searched, executed or used for selection.
- **Derived, ephemeral output:** a ContextPacket. It is never a record, is never stored as knowledge and cannot become
  a SOURCE_FACT. Every item carries the complete record it was selected from.
- **DATA_NOT_INSTRUCTIONS:** every packet states `"boundary": "DATA_NOT_INSTRUCTIONS"`. Its content is data to
  reason about, not instructions to follow.
- Agent memory, conversation history, scratchpads, vector indexes and LLM output are non-authoritative and never
  become knowledge silently. New knowledge is adopted only through a governed Git record proposal and approval.
- A future lexical, vector or RAG retriever may return **candidate IDs only**. Every candidate must be re-resolved
  through a trusted KnowledgeBase by this resolver; retrieval never promotes a layer, authority, current status or
  provenance.

## Interfaces

- Python: `moneylab.knowledge.resolve_context(kb, request) -> dict`. Raises `KnowledgeStateError` for an untrusted
  repository (checked first) and `ContextRequestError(code, detail)` for an invalid request or a required-record error.
- CLI: `python -m moneylab.knowledge [--root R] resolve-context`, one JSON request on stdin (UTF-8; duplicate keys,
  `NaN` and `Infinity` are invalid JSON). Success prints the packet with the existing `canonical_json`.
  Errors print `{"error": {"code", "detail"}}`; an untrusted repository also prints the validation report.

| Exit | Meaning | Error code |
|---|---|---|
| 0 | packet printed | — |
| 1 | repository did not validate, or a required record failed | `REPOSITORY_UNTRUSTED`, `REQUIRED_NOT_FOUND`, `REQUIRED_SUPERSEDED`, `REQUIRED_LAYER_NOT_ELIGIBLE`, `REQUIRED_OVER_BUDGET` |
| 2 | invalid JSON or invalid request | `REQUEST_INVALID` |
| 3 | no rule violation, but sources could not be verified (`SOURCE_UNVERIFIED`) | `REPOSITORY_UNTRUSTED` |

Invalid JSON is reported before the trust check; a well-formed request on an untrusted repository gets no packet.

## ContextRequest

| Field | Required | Value | Default |
|---|---|---|---|
| `schema` | yes | exactly `moneylab.context.request/1` | — |
| `objective` | yes | non-empty string, at most 2000 characters | — |
| `mode` | yes | `EVIDENCE` or `IDEATION` | — |
| `topics` | no | list of topic enum values (`model.TOPICS`) | `[]` |
| `namespaces` | no | list of `^[A-Z0-9][A-Z0-9-]{0,47}$` | `[]` |
| `kinds` | no | list of `task`, `claim`, `decision`, `question` | `[]` |
| `include_ids` | no | list of record IDs | `[]` |
| `include_open_questions` | no | boolean | `false` |
| `budget` | no | object with only `max_records` (1–200) and `max_chars` (1–400000), integers | `20`, `32000` |

Unknown fields (top level or in `budget`), duplicates in a list, wrong types (a boolean is not an integer) and values
outside an enum, pattern or range are `REQUEST_INVALID`. Nothing is repaired silently. The packet's `request` is the
effective request: defaults filled and list fields sorted.

## Resolution

1. **Trust.** Only a KnowledgeBase whose validation exit code is 0 is used. Otherwise there is no packet, partial or
   best-effort.
2. **Required records** (`include_ids`) bypass the topic, namespace and kind filters only. Each must exist
   (`REQUIRED_NOT_FOUND`), be current (`REQUIRED_SUPERSEDED`) and be eligible in the mode
   (`REQUIRED_LAYER_NOT_ELIGIBLE`: a HYPOTHESIS in EVIDENCE). Together they must fit both budgets
   (`REQUIRED_OVER_BUDGET`). They are never truncated, the budget is never raised and no provenance is dropped. Any
   failure means no packet.
3. **Ordinary candidates** match every non-empty filter: a topic overlap, a namespace in the list and a kind in the
   list (OR within a dimension, AND across dimensions, empty = unrestricted). There is no fuzzy matching and no
   relationship inference. With `include_open_questions`, current OPEN questions that match the topic and namespace
   filters are added whatever `kinds` says.
4. **Current only.** A superseded candidate is listed in `excluded` as `superseded`. In EVIDENCE mode a HYPOTHESIS
   candidate is listed as `layer_not_eligible`. Records outside the candidate set are never listed.
5. **Selection order:** required records first, then section rank (`task_context`, `decisions`, `facts`, `derived`,
   `questions`, `hypotheses`), then record ID. Ordinary candidates are added in that order until the next one would
   exceed `max_records` or `max_chars`. It and every later candidate are listed as `budget`.
6. **Item size** is `len(json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False))`, including the
   record, its EvidenceRefs and lineage. No tokenizer is used. Excluded entries do not use the budget.

## ContextPacket

Top-level keys, all always present: `schema` (`moneylab.context.packet/1`), `boundary`, `trust_state`
(`exit_code`, `source_status`), `request`, `task_context`, `decisions`, `facts`, `derived`, `questions`, `hypotheses`,
`excluded`, `truncation`.

Each record goes into the first section that matches:

| Rule | Section |
|---|---|
| layer HYPOTHESIS (IDEATION only) | `hypotheses` |
| kind `task` | `task_context` |
| kind `decision` | `decisions` |
| kind `question` (any state; read it from the record) | `questions` |
| kind `claim`, layer SOURCE_FACT | `facts` |
| kind `claim`, layer DERIVED_SUMMARY | `derived` |

There is no "scientific evidence" section. SOURCE_FACT means grounded in a cited source, not scientifically proven.

- **Item:** `{id, kind, layer, marking, record}`. `record` is the complete record, so EvidenceRefs travel unchanged.
  `marking` is `SOURCE_FACT`, `DERIVED_SUMMARY: derived, see lineage` or `HYPOTHESIS: not evidence`. A
  DERIVED_SUMMARY also has `lineage`: `[{id, layer}]` for every record it is derived from, transitively, by ID.
  Selected items are current by construction; no `current` field is added. Within a section items are sorted by ID.
- **Excluded:** `[{id, reason}]`, `reason` one of `superseded`, `layer_not_eligible`, `budget`, sorted by
  `(reason, id)`. Required-record problems are errors, never exclusions.
- **Truncation:** `{truncated, max_records, max_chars, selected_records, selected_chars, budget_excluded}`.
- **Determinism:** the same Git tree and request give the same canonical bytes, independent of file order, hash seed,
  locale and working directory.

## Not in scope

No lexical search, embeddings, vector database, RAG, LLM reranking, MCP or HTTP. Selecting context does not trade,
size positions, approve risk or capital or promote a scientific status. A packet does not claim profitability, alpha,
strategy validity or live readiness, and hypotheses stay hypotheses.
