# ERRATA: CONTEXT-PACK-03 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: CONTEXT-PACK-03-ERRATA-001
TASK_ID: CONTEXT-PACK-03
TARGET_WORK_ORDER: docs/tasks/CONTEXT-PACK-03/WORK_ORDER.md @ 2f1f37300133fbef426326bfb74dccb13b81d5aa (sha256 30228fc77f77174a46d112ce9b3362ded6cba17793167d3b03fad05b93e64af0)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자, 2026-11-05
FOUND_IN_GATE: COMMIT (post-commit verification of implementation commit d4781288dadafa8656c5521c41f1cc9b3f56af6c, CLAUDE_REPORTED)
APPLIES_FROM: user acceptance in chat; binding for CLEAN_COMMIT_E2E (read-only gate, docs/tasks/README.md §5) and fixed in Git as Ce1 before PUSH

## CHANGED_FIELDS

CHANGED_FIELDS:
- TEST_GATES.T4 (pathspec of the protected ML-CTX files; exception list for paths outside docs/context/)
- ALLOWED_FILES (adds this ERRATA file, Ce1 only)
- PROTECTED_FILES (one-time Ce1 creation of this ERRATA file is exempted, as the C1 creation already is; nothing else changes)
- ALLOWED_ACTIONS (adds ERRATA_COMMIT between CLEAN_COMMIT_E2E and PUSH)
- STOP_CONDITIONS (adds the Ce1 conditions below; existing conditions unchanged)
- New section: CE1_VERIFICATION (checks before ERRATA_COMMIT, after it, and at every later gate where HEAD = Ce1)

UNCHANGED_FIELDS (명시적으로 바꾸지 않음): CONTRACT_VERSION, CANONICAL_BASE_SHA, CANONICAL_BASE_TREE, TARGET_BRANCH, TARGET_WORKTREE, REQUIRED_CI_CHECKS, GOAL, BACKGROUND, NON_GOALS, GATE_SEQUENCE, GATE_TRANSITION_RULES, ABSOLUTE_RULES, FORBIDDEN_ACTIONS, the 16 IMPLEMENTATION paths of ALLOWED_FILES, INVARIANT, BASE_FILE_MANIFEST, SOURCE_SHA256_MANIFEST, DESIGN_CONTRACT D1-D8, GENERATION_RULES, TEST_GATES T1-T3 and T5-T8, E2E_GATES, REQUIRED_EVIDENCE, REQUIRED_REPORT, APPROVED_TEXT_MANIFEST, APPROVED_TEXT.

## RATIONALE

RATIONALE:
- T4 used the pathspec `docs/context/ML-CTX-00?.md` to mean ML-CTX-001 to ML-CTX-008. The `?` also matches `docs/context/ML-CTX-009.md`, an ALLOWED_FILES path created by this task.
- At IMPLEMENTATION and PRECOMMIT_AUDIT the file was untracked, so the working-tree diff did not include it and T4 passed with its intended meaning. After the implementation commit `d4781288dadafa8656c5521c41f1cc9b3f56af6c`, a commit-to-commit diff with the same pathspec reports `A docs/context/ML-CTX-009.md` (GIT_VERIFIABLE).
- With the eight paths written explicitly, the protected-set diff from `64431a03d59aa526965943c9cf06898003fd7875` to `d4781288dadafa8656c5521c41f1cc9b3f56af6c` is empty, and the blob ids of ML-CTX-001 to ML-CTX-008 equal BASE_FILE_MANIFEST (GIT_VERIFIABLE).
- The defect is in the verification command only. The protection scope, the 16 implementation files, the Work Order and the commits C1 `2f1f37300133fbef426326bfb74dccb13b81d5aa` and Ci `d4781288dadafa8656c5521c41f1cc9b3f56af6c` are unchanged.
- E2E_GATES do not use T4 and are evaluated with HEAD = Ci, so CLEAN_COMMIT_E2E is unaffected. Ce1 follows CLEAN_COMMIT_E2E so that its entry condition (HEAD = implementation commit) and the E2E check "parent is C1" hold literally; Ce1 precedes PUSH, the next change gate (docs/tasks/README.md §5). A Ce after the implementation commit has precedent in DOCS-ALIGN-01 ERRATA-002.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- TEST_GATES.T4 (replaces the Work Order text in full):
  - T4 Protected: `git diff --exit-code 64431a03d59aa526965943c9cf06898003fd7875 -- docs/context/MASTER_CONTEXT_2026-10-30.md docs/context/ML-CTX-001.md docs/context/ML-CTX-002.md docs/context/ML-CTX-003.md docs/context/ML-CTX-004.md docs/context/ML-CTX-005.md docs/context/ML-CTX-006.md docs/context/ML-CTX-007.md docs/context/ML-CTX-008.md README.md ARCHITECTURE.md CLAUDE.md`, and no path outside `docs/context/` differs from the base except `docs/tasks/CONTEXT-PACK-03/WORK_ORDER.md` and, after Ce1, `docs/tasks/CONTEXT-PACK-03/ERRATA-001.md`.
- ALLOWED_FILES (addition):
  - Ce1 only: A docs/tasks/CONTEXT-PACK-03/ERRATA-001.md
- PROTECTED_FILES (exemption only): `docs/tasks/**` remains protected except the one-time C1 creation of `docs/tasks/CONTEXT-PACK-03/WORK_ORDER.md` and the one-time Ce1 creation of `docs/tasks/CONTEXT-PACK-03/ERRATA-001.md`. After Ce1 both files are immutable.
- ALLOWED_ACTIONS (addition):
  - ERRATA_COMMIT (after CLEAN_COMMIT_E2E passes, before PUSH; requires its own user authorization): create `docs/tasks/CONTEXT-PACK-03/ERRATA-001.md` with the approved bytes of this file; `git add -- docs/tasks/CONTEXT-PACK-03/ERRATA-001.md`; one commit `docs(task): add CONTEXT-PACK-03 ERRATA-001`; no other path, no amend.
- CE1_VERIFICATION:
  - Before ERRATA_COMMIT: HEAD = `d4781288dadafa8656c5521c41f1cc9b3f56af6c`; worktree clean; CLEAN_COMMIT_E2E passed; the ERRATA file bytes have the approved SHA-256 and byte length.
  - After ERRATA_COMMIT: the parent of HEAD is `d4781288dadafa8656c5521c41f1cc9b3f56af6c`; the commit changes exactly one path, `A docs/tasks/CONTEXT-PACK-03/ERRATA-001.md`; its committed blob has the approved SHA-256; worktree clean.
  - At PUSH, PR_CI, MERGE and POST_MERGE_AUDIT (HEAD = Ce1): ancestry Ce1 -> `d4781288dadafa8656c5521c41f1cc9b3f56af6c` -> `2f1f37300133fbef426326bfb74dccb13b81d5aa` -> `64431a03d59aa526965943c9cf06898003fd7875`; the diff from the base to Ce1 contains exactly 18 paths (the Work Order, the 16 IMPLEMENTATION paths and this ERRATA file); the 16 IMPLEMENTATION blobs at Ce1 equal APPROVED_TEXT_MANIFEST; the Work Order blob at Ce1 has SHA-256 `30228fc77f77174a46d112ce9b3362ded6cba17793167d3b03fad05b93e64af0`; T4 as replaced above passes between the base and Ce1.
  - PR scope (docs/tasks/README.md §13): commits C1, Ci, Ce1; files as in the previous item; the PR head SHA and the approved head SHA are Ce1.
- STOP_CONDITIONS (additions):
  - HEAD differs from Ci before ERRATA_COMMIT, or CLEAN_COMMIT_E2E did not pass
  - the ERRATA file bytes or its committed blob differ from the approved SHA-256
  - Ce1 changes any path other than `docs/tasks/CONTEXT-PACK-03/ERRATA-001.md`, or its parent is not Ci
  - any CE1_VERIFICATION check fails
