# Camera-recovery incident and lock-lifecycle closeout

Use this reference when a feed-session incident reports `profile verification camera-recovery-failed`, when a target must be held after a non-success result, or when a closeout is requested for a machine-specific incident.

## Evidence-first diagnosis

1. Treat the user-provided incident machine/account as authoritative input, but resolve the canonical row and serial from the safe workbook/device-map before live action. Never guess a row or serial from historical artifacts.
2. Read the exact target run's `log.jsonl`, summary, manifest, `recovery_lock_handoff.json`, and matching `ui.xml`/`screen.png`. Keep code-level proof and live-runtime proof separate.
3. For Camera recovery, distinguish `camera dismiss failed`, `camera dismiss recapture unavailable`, `capture-artifact-incomplete`, and `camera overlay remained after dismiss recapture`. Retry Profile only after a fresh valid capture proves Camera is absent.
4. A BACK/ADB return code is transport acknowledgement, not UI success. A persistent overlay is a valid fail-closed result.
5. A bounded delayed-overlay retry may re-run dismiss and recapture once; persistent overlay must still stop without Profile navigation.

## Lock lifecycle invariant

A consumer promising blocked-target retention must create a real lease before target work. In the shared core, `acquire_device_lock(user_authorized=False)` intentionally returns an unlocked no-op lease when no prior lock exists; `set_status("blocked")` cannot create a lock retroactively.

For `multi-machine-feed-session`:

1. Reserve a real lock before ADB/device work.
2. Keep takeover authorization separate from lock creation: normal scheduling may create a lock with `user_authorized=True` while passing `allow_takeover=False` and no takeover scope.
3. On verified success, release machine and serial aliases.
4. On failure/manual-needed/blocked/finalization error, set the real lease to `blocked` and retain both aliases.
5. Regression tests should observe lock files during child execution, assert both aliases remain `status=blocked` and `owner_active=false` after failure, and assert both disappear after success.
6. `lock_status=blocked` combined with `present=false` aliases is a lifecycle defect.

## Scope discipline and worker attribution

- Inspect the exact current diff and `git blame` before accepting a worker result. `00000000 (Not Committed Yet)` identifies working-tree edits; a commit hash identifies committed history.
- Workers can include unrelated hunks. Remove only the unrelated hunk, preserve the requested fix, and rerun focused tests after cleanup.
- A worker report is not proof; re-read changed files and run verification in the coordinator checkout.
- Report which changes pre-existed, came from the current worker, and which accidental changes were removed. Do not claim another session broke code without diff/blame evidence.

## Closeout gates

- A machine-specific incident triggers live-canary eligibility, but never duplicate a running batch that already includes the target.
- If the target is in an active batch, stop at Gate 0; do not kill the batch or run a second canary.
- Preflight with the exact production interpreter before live action. Import errors or dependency-path contamination are `BLOCKED_AT_GATE_0_PREFLIGHT`, not UI evidence.
- Only a fresh target-scoped canary with `final_status=success` and empty `stop_reason` opens review/commit/push. If the user explicitly cancels live validation, record `SKIPPED_BY_USER` and use offline closeout.

## Regression matrix

| Case | Expected |
|---|---|
| BACK false | Specific dismiss reason; invalid capture; no Profile retry |
| BACK true, Camera remains | One bounded second dismiss/recapture; no Profile retry if persistent |
| Camera disappears | Retry Profile after valid recapture and continue identity verification |
| Normal reservation, feed failure | Real machine+serial leases remain `blocked` |
| Normal reservation, verified success | Both aliases released |
| Existing retained lock | Normal schedule does not take over |
