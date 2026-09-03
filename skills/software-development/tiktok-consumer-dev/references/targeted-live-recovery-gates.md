# Targeted live recovery gates

Use this runbook for a user-authorized, per-machine recovery of a prior TikTok batch. It is a gate, not a replacement for the consumer workflow.

## Per-target sequence

1. Resolve the latest report from the batch summary; inspect only redacted status fields and artifacts. Require `post_submission_state == None`. `ACCEPTED` or an ambiguous post state is terminal for this retry path: do not retry.
2. Classify the exact current failure signature and verify that the checked-out source revision contains an applicable handler. A missing handler is `NO_HANDLER_IMPLEMENTED`, not permission to improvise.
3. Inspect both lock aliases (machine and serial). Confirm they describe the same lease, project/scope, host, and lock ID. Prove the recorded owner PID is dead and search for a replacement workflow process for the exact machine/config. Keep alive, foreign, mismatched, or unverifiable locks untouched.
4. Validate the exact required config path before launching. Missing config is a hard blocker; never create or infer a production config during recovery.
5. Apply the attempt budget by signature. Repeated `OPEN_TIKTOK_FAILED` remains the same signature even when the timestamps or visual artifacts differ. Once the maximum meaningful attempts is reached, record `BLOCKED` and stop.
6. Only if every gate passes, launch one workflow process for that machine using the prescribed command. Do not use manual ADB tap/back/reboot, coordinate actions, popup clicks, or PackageInstaller interaction outside the workflow handler. If stale matching aliases must be reclaimed, back up both aliases and write redacted evidence before the atomic takeover; never touch live or foreign aliases.
7. Verify the resulting report, not the process exit code. Count success only when the report has `SUCCESS` plus `post_verified=true`, or an explicitly documented equivalent verified-workflow terminal state. Preserve handoff locks for blocked/no-launch targets.

## Evidence to retain

Record target, prior report path, exact signature, post state, config-present/missing result, both lock identities/statuses, recorded PID liveness, replacement-worker search result, launch/log path (or `not launched`), final report path, verifier fields, and retained-lock decision. Do not print credentials, workbook rows, account identifiers, or full raw reports.

## Common no-launch outcomes

- `CONFIG_MISSING`: target cannot run the prescribed command; do not synthesize config.
- `ATTEMPT_CAP_REACHED`: same signature already exhausted; do not blind retry.
- `POST_STATE_NOT_NONE`: prior submission needs existing automatic reconciliation, never a manual workbook edit or repost.
- `LOCKED_OR_UNVERIFIABLE`: keep both aliases and stop; do not delete a lock merely because a PID lookup is inconclusive.
