# Cluster-first canary and persistent A–Z supervisor

## Trigger
Use for multi-machine Farm Alerts, canary/recovery, rollout gates, or any task that spans code → tests → live devices → fleet reopen.

## Canary policy
1. Classify alerts by failure signature and root-cause hypothesis before live action.
2. Select one representative canary per cluster; record why it represents the cluster.
3. Run independent clusters in parallel when locks/resources permit. Never serialize unrelated machines.
4. A failed representative blocks only its cluster. Other clusters continue.
5. Reopen the fleet only after every identified cluster has a passing representative, focused verification, and evidence. Canary every machine only for explicit coverage or material device/OS/runner variance.
6. Cluster-first controls scope only. Official runner, lock, screenshot/UI XML/OCR, and no-manual-tap gates still apply to each selected representative.

## Persistent A–Z workflow
A multi-phase task is one root task, not disconnected worker prompts. Maintain an atomic ledger containing `incident_id`, `phase`, `status`, `target`, `resume_token`, `last_evidence`, and `next_action`. Consume idempotent statuses: `DONE`, `CHECKPOINT`, `FAILED_RETRYABLE`, `FAILED_FINAL`, and `NEEDS_DECISION`.

- `DONE`: advance the next phase automatically.
- `CHECKPOINT/LOCK_HELD`: emit monitor/resume action; do not let an LLM child wait on a lock.
- `FAILED_RETRYABLE`: retry within a bounded signature budget.
- timeout: resume from the ledger; do not restart discovery from scratch.
- long waits: detached deterministic job runner/poller, not an LLM loop.

The worker report must include the next executable action whenever it is not `DONE`. `PARTIAL` is not completion while an executable phase remains. User intent to complete A–Z overrides ordinary scope, fixture, or unrelated-dirty-tree objections; ask only for credentials, unresolved identity conflicts, destructive actions, or genuine business decisions.

## Evidence ledger per cluster
Record alert signatures, representative selection, machine/slot/account/serial, exact runner command, exit code/final status, screenshot/UI XML/OCR/log/artifact paths, post-run lock state, and rollout decision. Preserve passed clusters when another cluster fails.

## Failure patterns from this incident
- Do not run one canary per machine when several alerts share a root cause.
- Do not assign M11→M40→M66 to one child and wait for all phases; split independent clusters or use the persistent supervisor.
- Do not treat a worker timeout as a completed phase or ask the user to re-trigger the next phase.
- `ACCOUNT_STATE_LOGIN` with explicit login/GMS UI markers is a genuine cluster gate, not automatically a code defect; fail closed and route to credential/manual-review handling without destructive cleanup.
