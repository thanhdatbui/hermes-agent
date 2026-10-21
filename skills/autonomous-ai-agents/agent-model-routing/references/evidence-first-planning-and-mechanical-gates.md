# Evidence-first planning and mechanical gates

Use this reference when the Coordinator has repeatedly declared work complete but later defects show the architecture or plan was wrong.

## User expectation
The operator does not accept verbal memory, a plan, or a worker self-report as completion. The Coordinator must dispatch the implementation, run the focused tests, obtain independent reviewer evidence, and report the real verdict. Do not wait for a second recurrence before escalating a single non-trivial architecture/state/contract/guard/lock/cron/database/interface issue.

## Recommended pipeline

`Coordinator triage -> EvidencePack Gate -> strong planner -> cheap implementation worker -> diff/test gate -> independent reviewer`

### EvidencePack minimum
- Exact symptom/error and affected component.
- Tight reproduction or failing focused test.
- Exact file/line excerpts and data-flow boundary.
- Recent relevant change/diff.
- Ranked hypotheses with falsifiable predictions.
- Explicit unknowns; do not convert assumptions into facts.

Reject the handoff when claims cannot be traced to a file, log, command result, OCR readback, or other verifiable artifact.

### Planner contract
The planner must return root cause, non-goals, allowlisted files/anchors, bounded steps, executable acceptance commands plus expected exit codes, rollback, risks, and unresolved assumptions. The Coordinator supplies evidence; the planner must not be asked to explore an unbounded repository blindly.

### Mechanical gates
- Gate A: validate EvidencePack schema, source existence, line/hash integrity, command results, and OCR readback.
- Gate B: validate plan schema, evidence references, allowlisted paths, non-empty rollback, executable acceptance checks, and chain-of-custody hashes.
- Gate C: validate base snapshot, committed/staged/untracked/renamed paths, non-empty in-scope diff, plan hash, bounded test timeout/process cleanup, and acceptance results.
- Receipts must be tamper-evident and cannot be forged by the worker. Never allow a later rerun to reset the base snapshot and hide already-committed out-of-scope changes.

## Review discipline
A focused suite passing is necessary but not sufficient. Independent review must probe adversarial cases: receipt tampering, plan/evidence mutation, committed changes after the base snapshot, rename old/new paths, untracked files, empty diff, missing HEAD/base SHA, empty rollback, and Windows process-tree timeout cleanup. A reviewer rejection is evidence; do not report APPROVED until the reviewer actually returns APPROVED.

## Quota strategy
Use the strong planner for non-trivial design decisions, not for transient device/network faults or every trivial fix. Make the EvidencePack compact so planning is one bounded call. Use the low-cost implementation pool as the primary worker only when its scope, snapshot, time, and diff gates are mechanically enforced; retain the Claude worker as fallback rather than removing it without measurements.

Session-specific implementation notes and probe history for `plan_exec_gate.py` are intentionally kept here rather than in the main routing policy.
