# Closeout remediation and Sol enforcement

## Trigger

Use when the user says `chốt phiên`, `đóng phiên`, `done`, or asks whether the current deliverable is finished.

## Mandatory lifecycle

A closeout reviewer result is not terminal unless it is `APPROVED` with score >=85 or a genuine non-recoverable `HARD_STOP`.

```text
closeout
  → inspect exact finding
  → bounded remediation worker
  → focused offline verification
  → closeout reviewer again
  → APPROVED >=85 / HARD_STOP
```

Do not stop with `BLOCKED_AT_REVIEW` after the first rejection. `REJECTED`, score <85, ordinary timeout, missing evidence, and missing Sol plan are intermediate remediation states. Preserve the score and finding verbatim, create a narrower contract, run the focused check, and rerun the reviewer. Stop only for:

- `APPROVED >=85`;
- explicit user cancellation; or
- `HARD_STOP` proven by non-recoverable safety, credentials, integrity, business decision, explicit cancellation, or exhausted bounded circuit breaker.

A passing focused test is evidence for the next review, not permission to close the session by itself.

## Machine-readable ledger

Every attempt should persist:

```text
run_id, repo, attempt, max_attempts, state, verdict, overall_score,
blocker, evidence, next_action, sol_plan_id, review_route,
parent_entry_id/prev_chain_hash, terminal
```

Use recoverable states such as `REMEDIATION_REQUIRED` and `SOL_PLAN_REQUIRED`. Reserve `HARD_STOP` for terminal conditions. Keep process exit code protection separate from lifecycle state: a nonzero exit can still represent a recoverable state requiring the next remediation action.

## Sol visible handoff

Missing `SOL_PLAN_ID` must produce a visible, structured next action; it must not silently bypass mutation or become an opaque stop. A planner failure may produce `SOL_FALLBACK_PENDING`, but fallback requires an explicit reason and authorization context and remains visible in JSON/audit output. An unstructured `SOL_FALLBACK` token must never silently grant `ALLOW`.

Sol is the engineering/planning authority. Claude is an independent quality reviewer. Neither silently self-approves a worker mutation.

## Evidence and dirty-worktree discipline

Before retrying closeout, isolate the candidate diff from unrelated dirty files and quarantine artifacts. If an oversized monolithic test file is auto-selected, run only the exact changed-test subset offline and preserve its command/output for the reviewer. Verify:

```text
git ls-files --eol <files>
git diff --numstat -- <files>
git -c core.whitespace=cr-at-eol diff --check -- <files>
```

Worker self-reports are claims, not evidence. Independently inspect status, exact paths, timestamps, and diffs. Move stray artifacts to a recoverable quarantine; do not delete them or use broad cleanup.
