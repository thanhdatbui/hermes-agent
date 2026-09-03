# Review-rejection repair and concurrent-writer handoff

Use this reference when a prior closeout review returns `REJECT` and remediation is requested before another closeout attempt.

## Required sequence

1. Snapshot `HEAD`, branch/upstream, porcelain status, and changed paths before dispatching any worker.
2. Workers may edit only the explicit allowlist and must not commit, push, reset, stash, or perform live actions.
3. After every worker result, re-check `HEAD` and status before trusting its report. If a writer committed or pushed unexpectedly, stop reconciliation, invalidate all prior review/test evidence, and review the new exact commit/tree; do not continue on stale bytes or force-push.
4. Convert every review finding into one focused regression test. Run the test RED against the rejected candidate before production edits, then implement the smallest fix and run GREEN.
5. For ordering/state-machine fixes, record explicit state-transition markers (for example `focus_restored`/`recovery_complete`) and bind calls to the same video/attempt/state. A list of generic event names or a later call in another iteration is insufficient proof.
6. For terminal/fail-closed errors, test through the outer flow when the finding concerns downstream behavior. A helper-only test does not prove that the caller stops swipe, shell fallback, retry, or cleanup actions.
7. Treat external side-effect results as tri-state when delivery can be ambiguous. A Boolean `False` is not proof that nothing was sent if timeout/transport failure can occur after delivery; retain the claim/pending marker and require explicit reconciliation rather than automatic retry.
8. Re-run focused tests, compile/diff checks, then obtain a fresh parseable review on the exact final candidate. Only after `APPROVED` may the normal commit/rebase/push gates proceed.

## Common false fixes

- Do not guard a behavior with a broad configuration flag when the bug is a narrower runtime fault. Example: skip a sponsored check only when `focus_lost`, not whenever `fast_swipe` is enabled.
- Do not treat a passing canary on a pre-change or different tree as proof for the final candidate.
- Do not let tests assert only that an event occurred somewhere in the session; assert the forbidden interval and the required completion marker.

## Evidence labels

Report `RED`, `GREEN`, `focused PASS`, `full-suite PASS/BLOCKED`, `REVIEW_PENDING`, `REJECT`, and `APPROVED` distinctly. A worker self-report, HTTP 200, process exit 0, or successful canary is not an approval.
