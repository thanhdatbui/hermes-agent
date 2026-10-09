# Cluster-first canary & persistent A–Z supervisor

## Operating rule

For multi-machine incidents, classify alerts by failure signature and root-cause hypothesis before live action. Select one representative canary per cluster; add another only for material runner/OS/device variance or explicit coverage. Run independent clusters in parallel when locks/resources permit. A failed representative blocks only its cluster. Fleet reopen requires one passing representative per identified cluster, focused evidence, and an exception ledger for uncovered variants—not every machine in the cluster.

## Root-task lifecycle

Do not use one LLM child as an A–Z supervisor. Persist an incident ledger/state machine outside the chat loop:

```text
CODE_VERIFY → cluster canaries → FLEET_REOPEN → CLOSEOUT
```

Each worker returns one structured status: `DONE`, `CHECKPOINT`, `FAILED_RETRYABLE`, `FAILED_FINAL`, or `NEEDS_DECISION`, plus `resume_token`, evidence references, and a concrete `next_action`. `DONE` advances the next phase idempotently. `LOCK_HELD` is a monitor checkpoint, never an excuse to stop or ask the user.

## Live execution separation

- Code-surgery worker: offline patch + focused test; never waits on device locks.
- Monitor/preemption worker: finite read-only lock/heartbeat check; returns `LOCK_HELD` quickly.
- Live runner/job: deterministic detached process owns polling, lease acquisition, canary execution, artifacts, and resume. Do not make an LLM child wait on a lock.
- Independent cluster workers may run concurrently; same-cluster representatives remain isolated unless coverage is explicitly requested.

## Anti-excuse gate

After inspect, the coordinator must either dispatch the exact next phase or emit a structured checkpoint with `next_action`. It may not stop because of a stale fixture, ordinary dirty files outside scope, child completion, or a transient timeout. Retry/resume from the ledger rather than rediscovering completed work. Ask the user only for missing credentials, unresolvable identity mismatch, destructive action, or a genuine business decision.

## Evidence minimum

For each representative: machine, slot/row, account, serial, failure cluster, command, exit code, final status, screenshot/UI XML/OCR or explicit unavailable marker, artifact/log path, and post-lock state. Never report fleet reopen until every identified cluster has a passing representative and the reopen/smoke evidence is present.
