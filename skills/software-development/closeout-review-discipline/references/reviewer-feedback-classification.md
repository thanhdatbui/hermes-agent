# Reviewer feedback classification and remediation ledger

Use this matrix when a closeout reviewer mixes policy disagreement, concrete defects, coverage requests, and transport noise. It is a companion to `closeout-review-discipline/SKILL.md`; it does not override the user's active contract.

## Classification order

1. `TRANSIENT`: timeout, 429, 5xx, connection reset, or empty provider response. Retry the same immutable `(diff_sha256, contract_hash)` with bounded backoff; do not edit the candidate.
2. `STRUCTURAL`: repeated same-class worker failure, malformed patch, wrong files, missing focused verification, schema/route failure, or payload above the configured safety ceiling. Narrow the contract or repair the runner; do not change user invariants.
3. `REVIEW_CONTRACT_CONFLICT`: reviewer asks to violate an explicit invariant. Examples: making `ready_to_close=false` veto a validated rubric score >=85; allowing explicit `NEED_CONTEXT` to pass; changing the exact Terra model; or removing the configured safety ceiling. Record the finding and do not dispatch it to a code worker.
4. `IN_SCOPE_CONCRETE_DEFECT`: an in-scope file/anchor, reproducible wrong behavior or fail-open path, and a focused offline test contract are all present. Examples: missing binding mismatch rejection, TOCTOU gap, root-commit crash, unsafe bypass primitive, or fallback transport failure that accepts truncated review.
5. `OUT_OF_SCOPE_COVERAGE`: generic requests for full-suite/E2E/provider/device testing, refactors, or extra telemetry outside the allowlist without a demonstrated defect in the candidate. Record as a note; do not expand scope merely to improve a score.

A vague claim is not an in-scope defect until the Coordinator verifies it read-only. Preserve the original reviewer text and the classification reason in the ledger.

## Immutable review identity

A review attempt is identified by `(diff_sha256, contract_hash)`, where `contract_hash` covers the fixed reviewer/system-prompt annex and policy version. Do not resubmit unchanged bytes under a changed prompt to hunt for a higher score. A new review requires a newly closed concrete finding or a transient transport retry. Preserve `NEED_CONTEXT` as fail-closed even when the rubric looks high; preserve the user-defined rubric precedence for advisory `ready_to_close`.

## Remediation ledger fields

Each finding should carry:

- stable `finding_id` derived from the file/anchor and claim;
- class and invariant reference, if any;
- exact target files and expected code delta;
- RED evidence and focused GREEN command;
- worker dispatch ID and changed hunk ownership;
- before/after diff SHA and contract hash;
- disposition: `CLOSED`, `REVIEW_CONTRACT_CONFLICT`, `OUT_OF_SCOPE_COVERAGE`, or `NO_VALID_REMEDIATION_PATH`.

Every worker hunk must map to an assigned `finding_id`. Reject edits with no mapping, broad refactors, new dependencies, or files outside the allowlist.

## State transitions

```text
REVIEW -> CLASSIFY
CLASSIFY + IN_SCOPE_CONCRETE_DEFECT -> PATCH -> VERIFY -> REVIEW
CLASSIFY + TRANSIENT -> REVIEW_TRANSIENT -> REVIEW (same bytes)
CLASSIFY + NEED_CONTEXT -> BLOCKED_NEED_CONTEXT
CLASSIFY + only CONTRACT_CONFLICT/OUT_OF_SCOPE -> CONTRACT_RECHECK once -> BLOCKED_AT_REVIEW_CONTRACT
CLASSIFY + no newly closable concrete finding -> NO_VALID_REMEDIATION_PATH
REVIEW + validated score >=85 -> CLOSEOUT_APPROVED
```

A score oscillation on unchanged bytes is not progress. Stop rather than repeatedly dispatching workers or changing prompts. This is distinct from the user's required anti-surrender behavior for genuine, newly evidenced in-scope defects.

## Policy-test checklist

The policy validator should assert the five class labels, `BLOCKED_AT_REVIEW_CONTRACT`, `diff_sha256`, `contract_hash`, immutable-prompt/no-rereview language, stable finding IDs, and the exact validator filename. Runtime tests should separately cover rubric/advisory precedence, explicit `NEED_CONTEXT` fail-closed, exact Terra routing and safety ceiling, and provider-failure fail-closed. Do not add runtime tests for behavior the current candidate does not implement; classify those as a separate candidate task.
