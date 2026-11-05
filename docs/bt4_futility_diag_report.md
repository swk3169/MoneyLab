# BT4-FUTILITY-01 — Research Procedure and Execution Report

## 1. Purpose and Scope

This report documents the research procedure, execution status, artifact integrity checks, and interpretation limits of BT4-FUTILITY-01.

The task operates under a fixed Work Order and accepted ERRATA-001 through ERRATA-007.

This document is a procedure and execution record. It does not publish research result values or per-hypothesis decision labels.

The underlying research uses synthetic evidence classified as `SYNTHETIC / NOT_EVIDENCE`. It does not constitute independent confirmation or validation of a trading strategy.

## 2. Research Identity

- Task: `BT4-FUTILITY-01`
- Research code SHA: `d2fcaf64b5fb87f502afba29572be340f653be24`
- Governing documents: Work Order and accepted ERRATA-001 through ERRATA-007
- Research procedure: Contract-governed and deterministic
- G8a execution attempts: One

The research identity, clean worktree requirement, and pinned contract hashes were checked before G8a execution.

The C4 report is a subsequent documentation artifact. Its commit does not change the research code identity used by the completed G8a run.

## 3. Execution Record

G8a was executed exactly once.

The CLI reported `COMPLETE`, and the expected two output files were generated and verified.

The process exit code was not captured directly because an intervening shell command overwrote the exit-status variable.

An exit code of zero is inferred from the reported completion status and the existing CLI implementation. It is not treated as an observed exit code.

The original execution-gate result remains:

`G8A_CORE_EXECUTION_PASS: NO`

The completed core execution was subsequently granted:

`G8A_CORE_ACCEPTANCE: CONDITIONAL_ACCEPTANCE`

This conditional acceptance permits consideration of the next gate under separate authorization. It does not retroactively convert the original gate result into PASS.

The full G8a assessment remains:

`G8A_FULL_PASS: NOT_ASSESSED`

## 4. Artifact Integrity and Preservation

The two newly generated G8a artifacts passed their integrity checks.

For pre-existing research artifacts, the available preservation evidence is partial:

- All 18 artifact entries in the BT4-FUTILITY-02 Work Order input-hash manifest, which was fixed before the G8a execution, matched their recorded hashes.
- Seven SHA256SUMS lists were checked, covering 5,913 files, with no reported failures.
- Approximately 5,800 additional files, primarily in the G7 core-lock directory, lack a complete pre-execution content-hash comparison.
- The original per-entry filesystem metadata listing was not retained.
- The output-root directory's modification time changed when the G8a output directory was created.

The recorded SHA256SUMS checks establish consistency with their corresponding hash lists. They do not, by themselves, prove that every covered file was unchanged relative to the pre-G8a state unless the corresponding hash reference was independently fixed before execution. Five of the seven SHA256SUMS files are themselves among the 18 pre-fixed manifest entries; for the 5,891 files they list, content preservation relative to the pre-G8a state is established through that hash chain. The remaining two lists, covering the G4c smoke runs, lack such a pre-fixed reference.

The complete pre-execution metadata baseline cannot be reconstructed.

The post-G8a metadata digest is retained as:

`OBSERVED_NOT_HISTORICALLY_VERIFIED`

Accordingly, full before-and-after preservation equivalence is not claimed.

## 5. Exploratory Obligations

The exploratory reporting status remains:

`EXPLORATORY_REPORT_STATUS: PARTIAL`

The following items remain unresolved:

- A: Alternative significance thresholds
- B: PD-4
- C: V-4 sensitivity
- C': V-4 decomposition
- D: Oracle decomposition
- E: f12/f24/f36 explanation ratios

Their status remains:

`RETAINED_UNRESOLVED`

Item F, covering non-primary windows, is implemented in the existing decision summary.

No unresolved exploratory item has been waived, declared complete, or populated using results from another study.

No exploratory result values are published in this report.

## 6. Interpretation Limits

The evidence classification remains:

`SYNTHETIC / NOT_EVIDENCE`

The G8a procedure does not provide independent confirmation or new validation.

The corresponding decision outputs were already known through BT4-02, which used the same decision function and inputs.

Consequently, the G8a execution must not be presented as an independent replication or a new discovery.

No conclusion about live-trading profitability, production readiness, or validated trading performance is established.

## 7. Publication and Completion Status

Research result publication remains:

`RESULT_PUBLICATION: NOT_AUTHORIZED`

This document intentionally excludes numerical research results and per-hypothesis decision labels.

The original G8a execution-gate outcome and its conditional acceptance remain separately recorded.

The exploratory obligations described above remain open.

The task completion status remains:

`TASK_COMPLETE: NOT_DECLARED`

The completion requirement for C4 to be merged and pass the post-merge audit has not been met.

PR #37 remains open and unchanged.

PR #40 remains open, draft, and unchanged.

G8c, G8d, and G8e have not been authorized.

Any subsequent push, pull-request change, merge, post-merge audit, or publication requires separate authorization.
