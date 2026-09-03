# Manual-only device-lock consumer verification

Use this checklist when a shared device-lock API changes from automation-owned
locks to manual/operator authorization.

## Contract matrix

| Path | Required behavior |
|---|---|
| Normal automation, no existing lock | Call `acquire_device_lock(..., user_authorized=False)`; core returns a no-op/unlocked lease and does not create a lock. |
| Normal automation, existing lock | Catch `DeviceLockNeedsUserDecision` before `DeviceLockUnavailable`; preserve owner/project/PID/path evidence; do not release, reclaim, or silently skip. |
| Explicit operator/full-scope path | Pass `user_authorized=True` only when the user explicitly authorized the takeover; retain guarded takeover scope/reason/proof. |
| Generic unavailable/readiness failure | Keep the ordinary locked/readiness status distinct from manual decision. |
| Batch row | Preserve `final_status: needs-user-decision` (or an equivalent explicit manual-decision status). |
| Aggregate | Map any manual-decision row to a non-success aggregate such as `manual-needed`; never let it fall through to `success`. |
| Process result | Verify runner/CLI returns a non-zero code for manual decision. |

## Safe dirty-worktree sequence

1. Read repository rules and handoff only for the exact scope.
2. Record baseline status/diff and identify files being concurrently edited.
3. Patch only a narrow anchor in the owned/approved file; never reset or overwrite
   a concurrent refactor.
4. Compile the changed module immediately.
5. Run focused tests for lock acquisition, exception mapping, and CLI/aggregate
   status. Use the canonical interpreter and clear inherited `PYTHONPATH` when
   the repository requires an isolated import path.
6. Re-read the final diff, run `git diff --check`, and inspect status before any
   commit. Stage explicit paths only.

## Failure patterns worth checking

- A broad `except Exception` before the manual-lock exception silently converts
  the decision gate into a generic failure.
- A `return 0` or a success allowlist that includes `needs-user-decision` makes
  the process look healthy even though the target is blocked.
- An aggregate that checks only `failed`, `manual-needed`, or
  `skipped-device-locked` can fall through to success when a new status string
  is introduced.
- A worker re-acquiring a queued reservation with `user_authorized=True` can
  accidentally turn a normal automation path into an implicit takeover. Thread
  the authorization decision explicitly from the top-level user-authorized flag.
- Absolute imports in an isolated provider namespace may fail even when direct
  execution works. Use package-relative imports with a deliberate direct-run
  fallback, then verify that `sys.path` remains unchanged if isolation requires
  that invariant.

## Evidence report

Report per repository: changed files, dirty/concurrent-file caveat, compile result,
focused test count, full relevant-suite count, aggregate/exit-code assertion, and
any pre-existing or unrelated failures. Do not claim a clean commit when the
worktree still contains another agent's changes.
