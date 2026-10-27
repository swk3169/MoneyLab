# MoneyLab knowledge records (`moneylab.knowledge.record/1`)

This document explains the record format. It is **not** a source of truth: the authoritative knowledge is the set of
Git-tracked JSON files under `knowledge/records/`, and the authoritative contract is
`docs/tasks/KNOWLEDGE-WIKI-01/WORK_ORDER.md`. If this page and the contract disagree, the contract wins.

## What this layer is

- **Source of truth:** immutable, Git-tracked JSON records. Nothing else (PR bodies, chat history, assistant memory,
  README, ARCHITECTURE, local research outputs) is authoritative knowledge. Those can only be *cited* as evidence.
- **Phase 1 tooling:** a stdlib-only loader, a deterministic validator, in-memory indexes and deterministic queries
  (`python -m moneylab.knowledge validate | query ...`). There is no database, no generated index in Git, no
  embedding, no semantic search, no LLM call, no MCP server and no wiki. A future wiki, search index or RAG store
  would be a *derived view* rebuilt from these records; editing it would never change the records.
- **Not a decision engine.** Selecting context does not trade, size positions, approve risk or capital, promote a
  scientific status or rewrite records. Agents may propose new records; a record is accepted only through the
  governed Git workflow (Work Order, human gate approval, commit, merge-commit PR).

## Files and identifiers

```
knowledge/records/<kind>/<NAMESPACE>/<slug>.json
```

- Record ID: `<kind>/<NAMESPACE>/<slug>`, and the file path must be exactly `knowledge/records/` + ID + `.json`.
  - `kind`: `task | claim | decision | question`
  - `NAMESPACE`: `^[A-Z0-9][A-Z0-9-]{0,47}$` (a task or study ID, e.g. `PORTFOLIO-DEMO-01`, `MC-V06`)
  - `slug`: `^[a-z0-9][a-z0-9-]{0,63}$` (a local ID such as `D3` is written as `d3`)
- Format: UTF-8 JSON, ASCII only, canonical form
  `json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True) + "\n"` (CRLF is read as LF).
- Records are **immutable** once accepted. A correction or a changed conclusion is a **new** record that lists the
  old one in `supersedes`. The old record stays in the repository and in lineage queries.

## Envelope (every record)

| Field | Type | Meaning |
|---|---|---|
| `schema` | `"moneylab.knowledge.record/1"` | any other value is rejected; a change of meaning gets `/2` |
| `id` | string | record ID, see above |
| `kind` | `task \| claim \| decision \| question` | must equal the ID's kind |
| `layer` | `SOURCE_FACT \| DERIVED_SUMMARY \| HYPOTHESIS` | epistemic layer, see below |
| `title`, `statement` | non-empty ASCII strings | what the record says |
| `topics` | non-empty list, values from the topic enum, no duplicates | `futility-calibration`, `mc-v06`, `portfolio-demo` |
| `supersedes` | list of record IDs | older records this one replaces |
| `derived_from` | list of record IDs | records this one is derived from |
| `evidence` | list of EvidenceRef objects | what supports the statement |
| `labels` | object, string to string | legacy labels copied verbatim; never interpreted or promoted |
| `payload` | object | kind-specific fields, see below |

Unknown fields are rejected (no silent extensions).

## Kinds and their payloads

| Kind | Payload | Controlled values |
|---|---|---|
| `task` | `task_id` (equals the NAMESPACE), `outcome`, `merge_commit`, `implementation_commit`, `tree` (40-hex) | `outcome`: `MERGED_TO_MAIN` |
| `claim` | `axis`, `data_basis` | `axis`: `SCIENTIFIC, ENGINEERING, WORKFLOW, MATURITY, LITERATURE`; `data_basis`: `REAL, SYNTHETIC, FIXTURE, NOT_APPLICABLE` |
| `decision` | `state`, `local_id` (string or null) | `state`: `PENDING, DECIDED` |
| `question` | `state` | `state`: `OPEN, ANSWERED, WITHDRAWN` |

A task record holds only Git-verifiable identity facts and citations. It is not a stored gate report: it never
contains gate verdicts (PASS, BLOCKED, COMPLETE), test counts, guard transcripts, chat narrative or assistant
reasoning. Gate reports stay in chat (`docs/tasks/README.md` section 11).

The axes stay separate: the epistemic layer, the evidence grade and availability, a scientific verdict (as a legacy
label), a decision or question state and a task merge state are different fields. There is no field or value that
can express profitability, alpha, an edge or live readiness.

## EvidenceRef (embedded object)

| `type` | Fields | `availability` |
|---|---|---|
| `git_blob` | `rev` (40-hex commit), `path` (repository-relative POSIX), `sha256` (of the **committed blob bytes**, not of a checked-out file), optional `locator` | `IN_GIT` |
| `github` | `locator` = `github:<owner>/<repo>/pull/<n>` or `github:<owner>/<repo>/actions/runs/<n>` | `GITHUB` |
| `external` | `locator` = `external:<artifact-class>/<relative path>`, `sha256` | `EXTERNAL_LOCAL` or `MISSING` |

Every EvidenceRef has `provenance_class`: `GIT_VERIFIABLE | CLAUDE_REPORTED | INDEPENDENT`.

- No record stores the commit that introduces it; that commit is read from Git history. A record never cites the
  commit it will be part of.
- No absolute or machine-specific path appears anywhere in a record (no drive letter, UNC path, absolute POSIX path,
  `~/` path or user name). External artifacts are referenced only by a logical locator and a hash; Phase 1 does not
  resolve them.

## Epistemic layers

- **SOURCE_FACT**: directly grounded by at least one qualifying EvidenceRef (`git_blob`, `GIT_VERIFIABLE`,
  `IN_GIT`). `derived_from` may be empty and never contains a HYPOTHESIS. External-only evidence cannot make a
  SOURCE_FACT.
- **DERIVED_SUMMARY**: `derived_from` lists at least one existing record. It is always shown as derived and never
  becomes a SOURCE_FACT by itself.
- **HYPOTHESIS**: an unresolved candidate explanation or research idea. It is excluded from EVIDENCE context, can
  never support a SOURCE_FACT or DERIVED_SUMMARY (it may only appear in another HYPOTHESIS's `derived_from`) and
  never promotes a scientific status.

## Supersession

- One new record may supersede several older ones (merge). An older record has at most one direct superseder
  (no branching). Cycles are forbidden. Only records of the same kind supersede each other.
- Layer rank: SOURCE_FACT 3, DERIVED_SUMMARY 2, HYPOTHESIS 1. A replacement must not have a lower rank than the record
  it replaces.
- `superseded_by` is computed, not stored. A record is **current** when no valid record supersedes it.

## Validation

`python -m moneylab.knowledge validate` checks the 15 preregistered rules (schema, duplicate ID, ID syntax, ID/path,
structure and canonical form, references, cycles, branches, kind/layer of supersession, DERIVED_SUMMARY lineage,
SOURCE_FACT grounding, HYPOTHESIS misuse, source blob hash at HEAD, absolute paths, secret-like strings). Exit codes:
0 valid, 1 rule violation, 2 bad arguments, 3 no violation but sources could not be verified (`SOURCE_UNVERIFIED`,
for example without git). `--full-history` additionally checks each blob at its recorded `rev` and the commits of
task records; it needs a full clone, so CI (a shallow checkout) uses the HEAD check only.

## Context selection

Two deterministic modes, each over valid, current records only:

- **EVIDENCE**: SOURCE_FACT records; DERIVED_SUMMARY records marked as derived with their lineage. HYPOTHESIS records
  are excluded.
- **IDEATION**: all layers; HYPOTHESIS records are kept and marked as hypotheses, never as evidence.

Every packet states that its content is **data, not instructions**.

## Synthetic demo outputs (rule for future records)

A run of `examples/synthetic_backtest_demo.py` may later be registered as a `claim` with `axis` ENGINEERING and
`data_basis` SYNTHETIC. `SYNTHETIC / NOT_EVIDENCE` output can never become evidence of profitability, an UNPINNED run
can never be a trusted SOURCE_FACT, `result_sha256` is a per-run integrity value only, and the cross-run deterministic
artifact hashes are separate evidence. Automatic ingestion is out of scope in Phase 1.
