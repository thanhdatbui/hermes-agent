# Closeout remediation and artifact lineage (2026-09-26)

## Closeout is a loop, not a one-shot gate

When the user says `chốt phiên`, `xong chưa`, or `đóng phiên`, treat it as an execution directive. Run the closeout reviewer. If the reviewer returns `REJECTED`, `MINOR_FIXES`, or score `<85`:

1. Extract concrete findings.
2. Classify each as recoverable remediation, safety/integrity HARD_STOP, or business/credential decision.
3. Dispatch a bounded worker with an exact allowlist/anchor.
4. Run focused offline verification.
5. Re-review the new evidence.
6. Repeat while remediation remains possible; do not end with `BLOCKED_AT_REVIEW` merely because one review failed.

Terminal success requires `APPROVED` and score `>=85`. Terminal failure requires a proven HARD_STOP or an exhausted structural circuit breaker—not an ordinary reviewer rejection.

## State semantics

Use structured lifecycle states:

- `REMEDIATION_REQUIRED`: recoverable finding with `blocker`, `evidence`, and `next_action`.
- `REVIEW_REMEDIATION_EXHAUSTED`: recoverable/nonterminal score-cap state; preserve the ledger for a later bounded cycle.
- `SOL_PLAN_REQUIRED`: missing/expired/unreadable plan or missing plan metadata.
- `SOL_FALLBACK_PENDING`: Sol unavailable, with explicit reason and authorization still required.
- `ALLOW` / `APPROVED`: permitted/accepted.
- `HARD_STOP`: only irreversible safety, integrity, credential, unauthorized fallback, explicit cancel, or a proven structural breaker.

Missing FILE/OLD_STRING/FOCUSED_TEST, duplicate anchors, unreadable target, and focused-test failure are normally remediation states, not terminal HARD_STOPs.

## Runtime integration requirement

A helper and its unit tests do not prove enforcement. Inspect and test the real production entrypoint (`closeout_gate.py::main`, dispatch hook, or named runner). An integration test must demonstrate that the entrypoint actually invokes the remediation state machine, performs focused verification, and re-reviews before returning success.

## Reviewer evidence handoff

Reviewers may not access local filesystem paths. Supply the exact source/diff or a self-contained evidence bundle. A reviewer saying “I cannot access D:/...” is an evidence-access limitation, not a code verdict. Re-run with the source pasted or bundled. Preserve the distinction between:

- `focused tests passed` (local evidence),
- `runtime integration proven` (entrypoint evidence), and
- `reviewer APPROVED >=85` (closeout authorization).

## Artifact lineage for farm alerts

Every feed session normally emits `summary.txt`, `run_manifest.json`, `log.jsonl`, plus attempt-level `screen.png` and `ui.xml`. Resolve the full known lineage by serial/machine/account and separate current batch from historical and unrelated device runs. A generic alert string is not proof for a particular machine: confirm the same serial, same run, same attempt, and matching screenshot/XML/log event. Failure to find a target in a small recent-run subset means only “not found in that subset,” never “no artifact exists.”

## Practical evidence checklist

- Exact repo and run root
- Machine → row → serial mapping
- Current-batch versus historical run label
- `summary.txt`, `run_manifest.json`, `log.jsonl`
- Matching `screen.png` and `ui.xml`
- Verbatim failure reason and timestamp
- Confirmed / excluded / unproven labels
- Next action or proven terminal blocker
