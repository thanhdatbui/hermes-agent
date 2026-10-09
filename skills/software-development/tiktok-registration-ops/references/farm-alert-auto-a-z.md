# Farm Alert Auto A–Z

## Trigger
When a user sends a TikTok Farm Alert, do not stop at diagnosis.

## Required state machine
`ALERT → EVIDENCE → CLASSIFY → WORKER → VERIFY → CANARY → DONE/BLOCKED`

## Execution
1. Read the current run's exact log/XML/screenshot and resolve cluster/host (Kibe/Admin), machine→serial→workbook before action.
2. Classify each fingerprint as transient, structural, infrastructure, business/ownership, or mixed.
3. Transient: bounded retry with fresh evidence. Structural: dispatch a narrower worker contract with a non-empty contract delta. Known exact diff: use the pre-authorized bounded surgery path. Wrong host/mapping/runner: pivot, then re-prove target identity.
4. Independently verify diff scope and focused offline test. Then run one canonical-target canary and inspect fresh artifacts; exit code alone is not success.
5. Continue routine in-budget recovery without asking. Ask only for credentials, business/ownership decisions, irreversible/paid/live durable actions, or exhausted escalation.

## Farm safety
Never manual ADB tap/clear/logout, broad-scan runtime, or modify workbook/account ownership without evidence. Preserve locks, nick assets, and visual evidence. Keep code patch, batch job, and live canary as separate lanes.

## Incident lessons
- Resolve the correct cluster before declaring a machine mapping blocker; a valid device can be hidden by stale Kibe/Admin environment variables.
- After a detector patch, rerun a single canonical canary; treat new XML fingerprints as new evidence and patch only the narrow classifier gap.
- A runner can report `SUCCESS` while auto-sync is `BLOCKED_DATA_CONFLICT`; verify the created account/email/serial against the correct Admin workbook and backup before claiming complete.
- Worker `completed`/`timeout` is not proof of file changes; parent must independently verify status, diff, markers, and tests.
- Claude CLI is an independent reviewer: keep iterating on concrete findings until `APPROVED`; do not report approval from a worker self-report.
