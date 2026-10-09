# Farm Alert autonomy and scoped push

## A→Z loop
When a Farm Alert arrives: resolve canonical host/machine/serial; read the exact current log/XML/screenshot; classify TRANSIENT, STRUCTURAL, INFRA, or BUSINESS; dispatch an exact worker contract for code fixes; independently verify diff/test; run one bounded canonical canary; re-classify any new fingerprint; finish DONE or BLOCKED with evidence. Diagnosis is never terminal.

Retry transient errors with a bounded retry. Structural failures require a materially different, narrower contract. Use bounded exact-diff surgery only when its predicate and budget are satisfied. Pivot only to a canonical host/mapping/runner and re-prove identity. Ask only for credentials, business/ownership decisions, irreversible/paid/destructive/deploy actions, or exhausted escalation. Unrelated dirty code/test files are not a refusal reason.

## Scoped commit/push
After an explicit user request, commit and push only the task-contract allowlist. Preserve unrelated dirty/staged/untracked paths; never use `git add -A` or `git commit -a`. Verify staged scope, focused checks, independent review, upstream sync/overlap, and remote SHA. Refuse only for missing credentials/permission, force required, paid/destructive deploy, reviewer or verification failure, true scope conflict, unprovable allowlist, invalid repo state, or absent explicit request.

## Safety
Preserve FARM-ASSET-001 and locks/assets. No manual ADB taps or broad scans. Capture visual evidence before teardown. The canonical repo policies are `docs/ai/workflows/farm-alert-coordinator-loop.md` and `docs/ai/workflows/guarded-task-loop.md#scoped-commit-push-001`.