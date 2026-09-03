# P2+ Recovery-Adapter Consumer Pattern

Use this reference after the shared `automation-core` control plane is shipped and a consumer needs runtime integration. It records the proven login/reconcile shape, but the acceptance rules apply equally to mail, proxy, registration, and UI consumers.

## Proven seam matrix

| Runtime seam | Consumer evidence | Adapter action |
|---|---|---|
| Single-job executor result choke point (`_save_result` or equivalent) | Every outcome passes through one save boundary | Map intentional terminal outcomes (`FAILED_SAFE`, invalid/credential/identity failures, terminal account states) to core `NON_RETRYABLE`; do not invoke AI escalation for these. Map retryable outcomes to the shared recovery path. |
| Inventory/reconcile bounded recovery (`_collect_with_recovery`) | App restart/reboot allowance is exhausted and the same failure signature recurs | Classify the repeated terminal as budget-exhausted and finalize the durable queue as `FAILED_LOCKED`; retain the device lock. |
| Existing per-account retry loop | Existing local attempts/re-capture/restart are already real runtime behavior | Call the shared registry/hook from the proven boundary; do not add a second retry loop or reset the core cap. |
| Proposed feature with no runtime reference | Discovery finds no call-site or executable path | Mark `DISPROVED`/`NEEDS_PROOF` and do not invent a new guided-recovery feature merely to satisfy a plan. |

## Required RED/GREEN evidence

1. Snapshot worktree identity, exact base SHA, dirty source checkout status, scoped mtimes, and the combined baseline suite before writing.
2. Write the smallest focused adapter test in the phase allowlist. Guard optional imports if necessary so collection yields per-test `FEATURE_MISSING` failures rather than hiding all contract tests behind one import error.
3. Run RED against unmodified production files and preserve the real failure output. A test that passes before the implementation, or fails due to a typo/import environment, is not valid RED evidence.
4. Implement only in the proven seam files plus the requirements pin and focused test file. Do not create an unplanned adapter module.
5. Run GREEN in the target core environment. Verify the distribution metadata and imported module path; requirements text and worker reports are not enough.
6. Assert durable state (`queue.get(target).state == FAILED_LOCKED`) and restart behavior, not only a returned status. Assert the lock was retained and no second detection/retry occurred.
7. Run the exact combined focused suite again. Preserve and classify any baseline sibling/environment failure; do not edit an out-of-scope repository to make the suite green.

## Core contract checks

- Normal meaningful recovery budget is separate from AI escalation budget: the default policy is normally 8 meaningful attempts, while escalation is normally capped at 3. Consumer policy may tighten but never silently replace one with the other.
- `NON_RETRYABLE` fails closed without AI hook consultation.
- Missing handler, absent hook, hook exception, timeout, invalid proof, or proof-free success must end in durable `FAILED_LOCKED` with the device lock retained.
- Hook evidence must be redacted by the core before it reaches the consumer hook. Never include credentials, raw account identifiers, serials, tokens, or connection strings in fixtures or reports.
- Hook success is not completion proof. Release is allowed only after valid artifact recapture and passed verifier proof through the normal completion gate.
- A `FAILED_LOCKED` record is terminal across restart; scheduler/watchdog must not re-fire it. User-explicit inspection/open is a separate action.

## Verification commands

Use Windows-visible paths and clear inherited Python path state:

```bash
env -u PYTHONPATH <target-python> -m pytest -q -p no:cacheprovider <exact combined files>
env -u PYTHONPATH <target-python> -m py_compile <scoped production files> <focused test>
git diff --check
git diff --name-status
```

Also verify:

```python
import importlib.metadata as metadata
import automation_core
print(metadata.version("automation-core"))
print(automation_core.__file__)
```

The printed version must be the target wheel and the module path must belong to the target environment, not a stale Hermes environment.

## Async delegation evidence rule

`ASYNC DELEGATION BATCH COMPLETE` is lifecycle metadata, not a code-delivery proof. Before audit, commit, or replacement worker:

- inspect branch/HEAD/status and the exact allowlist diff;
- check whether the focused test file and production seams actually exist;
- verify mtimes and any checkpoint/report artifact;
- rerun the deterministic tests independently.

If the worktree is still at its base SHA with only a discovery report, keep implementation `PENDING` and re-dispatch only after the current worker has shut down and exact-scope reconciliation proves no overlap.

## Login/reconcile example acceptance matrix

| Case | Required result |
|---|---|
| `FAILED_SAFE` / terminal account state | `NON_RETRYABLE`; no escalation hook |
| Retryable executor or inventory signature | shared registry/hook called once at the proven seam |
| Repeated `FINAL_BLOCKED` after bounded restart/reboot | durable `FAILED_LOCKED`; lock retained |
| No handler or hook raises | durable `FAILED_LOCKED`; no retry/release |
| Hook returns success without recapture/verifier proof | durable `FAILED_LOCKED` |
| Valid recapture + passed verifier | only then may the normal completion gate proceed |
| Restart after `FAILED_LOCKED` | no re-detect, re-fire, or scheduler/watchdog retry |
