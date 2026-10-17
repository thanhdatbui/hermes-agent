# Closeout incident reference: evidence-first review and anti-paralysis

## Lessons captured

- A closeout score of 82 was reported as if it satisfied a mandatory >=85 gate. The safe rule is to read the live policy and the current audit artifact; do not infer a Grace Band from chat history.
- A successful process exit is not proof of a successful push or sync. Verify the commit/ref and the destination separately.
- A screenshot must be opened and visually inspected before it is attached or used as success evidence. A popup such as “Ghim/Riêng tư” is not publish proof.
- A stale idempotency receipt can make an upload runner skip the real upload. Receipts need a current run identity/nonce/timestamp and a regression test proving stale receipts cannot skip the action.
- A remediation loop must not end with an unexplained “kept local” outcome when mechanical checks are green. It must either complete the commit/push path or return a concrete reproduced failure with evidence; retry/remediation counts remain bounded.
- Claude CLI review is useful as an independent reviewer, but the wrapper’s exit code and self-report are not enough: require a final verdict tied to the current diff and verify the scope independently.

## Reproduction checklist

1. Capture repository status, staged paths, current HEAD, and the exact target allowlist.
2. Run the narrow focused test and record its real output.
3. Run the closeout/review wrapper against the current diff, not a prior commit or stale audit.
4. Verify the audit binding (repo, HEAD, scope, timestamp, verdict, score/policy) before push.
5. After push/sync, verify the remote/ref or transfer receipt independently.
6. For UI evidence, inspect the image with vision/OCR before sending it; reject popup-covered or stale images.

## Anti-paralysis state machine

Use finite outcomes only:

- `PUSHED`: mechanical checks and required evidence pass.
- `BLOCKED_BY_REPRODUCED_BUG`: a concrete failing test, crash, or physical blocker is recorded.
- `OWNER_OVERRIDE`: only when the user explicitly issues the push/close command and the override is permitted by current policy.

Do not use “deferred/kept local” as a silent terminal state. If a review remains negative without a reproducible finding, preserve the exact finding, apply the bounded escalation policy, and do not claim approval. Never bypass a higher-priority mandatory closeout gate by inventing a score band.
