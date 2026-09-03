# Stale device-lock reconciliation (tiktok-upload batch)

When a canonical upload batch dies mid-run it can leave **dead-owner `tiktok-upload`
locks** — `status=running` + `owner_active=True` but the PID is dead. The next batch
then SKIPs those targets (`SKIPPED_LOCKED`) even though nothing is alive. The correct
fix is **exact-attribution guarded reconciliation**, NOT a global unlock and NOT raw
file deletion.

## Trigger
User reports a batch with many `SKIPPED_LOCKED` rows and dead-PID locks, and asks to
release the locks of a failed batch. Scope is the canonical upload repo
(`D:\Taadaa\Tiktok-video`): `run_tiktok_upload_batch.ps1`,
`scripts/tiktok_workflow/state_machine.py`, `tests/test_tiktok_workflow.py`,
`docs/HANDOFF`. Do NOT create a new launcher/runner, do NOT touch automation-core,
workbook, credentials, or devices; do NOT live-upload.

## Hard rules
- **Never raw-delete lock files.** Every release goes through the guarded
  automation-core API (`acquire_device_lock` dead-owner reaping, or
  `open_failed_locked_lock` / `release_with_audit`), which re-checks dead-PID +
  same-host + same-project and writes a `DeviceLockOpenAudit`. Prefer fail-closed
  evidence over deletion.
- **Never globally release all `tiktok-upload` locks** — they may belong to another
  batch. Reconcile ONLY dead-owner locks whose target is in the **current canonical
  batch** machine list.
- **Preserve foreign / other locks:** `tiktok-luot nuoi acc`, `Tiktok_Reg`, and any
  lock whose command carries a different intentional workflow marker:
  `--force-avatar-upload`, `--avatar-smoke`, `--profile-smoke`,
  `--account-switch-smoke`, `--upload-flow-smoke`, `--post-surface-*`,
  `--video-pick-recovery`, `--recovery-mode`, `--preflight`, or `nuoi acc` /
  `force-avatar-machines`. Machine 78 (luot), 57 (Tiktok_Reg), 15 (avatar) must
  survive untouched.
- **Exact attribution WITHOUT a schema change:** stamp the batch id onto every worker
  via env `CODEX_DEVICE_LOCK_RUN_ID` (plus a `TIKTOK_LOCK_OPERATION=upload` marker)
  so the acquire path can carry `run_id=batch_id` and reclamation is provably this
  batch's. If the lock schema later gains an explicit `batch_id` field, prefer it.
- **Implement in two narrow places only:** (1) launcher **preflight** reconcile that
  calls a guarded `reconcile-stale-upload-locks` CLI subcommand with
  `--batch-id --machines --apply` (fail-closed: a reconcile failure only warns and
  continues, never aborts the batch); (2) optional forward `reconcile_stale_lock` in
  the worker acquire path for same-consumer dead owners. Do NOT weaken
  recovery/verifier gates or allow repost.

## Reusable module-level helper shape
```python
def reconcile_stale_upload_locks(targets, *, batch_id, lock_root=None) -> list[dict]:
    for machine in {int(t) for t in targets}:
        owner = inspect_device_lock(machine=machine, lock_root=lock_root)
        if not owner:
            continue
        if str(owner.get("project") or "") != "tiktok-upload":
            continue                                   # foreign consumer
        if lock_is_other_workflow(owner):
            continue                                   # different workflow
        status = str(owner.get("status") or "").strip().lower()
        if status in ("failed_locked", "blocked"):
            continue                                   # terminal retained locks
        if owner_process_alive(owner) is True:
            continue                                   # genuinely live PID
        # DO NOT gate on owner_active (the stale lie from the dead batch)
        serial = str(owner.get("serial") or "").strip() or None
        lease = acquire_device_lock(                   # core auto-reaps dead owner
            machine=machine, serial=serial, project="tiktok-upload",
            status="running", run_id=batch_id,
            bypass_proxy_readiness=True, lock_root=lock_root,
        )
        lease.release_with_audit(reason=f"reconcile cleared stale lock for batch {batch_id}")
        released.append({"machine": machine, "status": "RECLAIMED", ...})
    return released
```
Key: `acquire_device_lock` with a dead owner **reaps** the stale lock and overwrites
both machine + serial aliases with a fresh audited lease; releasing it (owner-matched)
lets the batch re-acquire cleanly. No raw delete at any point.

> **`open_failed_locked_lock` is NOT sufficient here.** It only clears terminal
> `failed_locked` locks. A dead-owner `running` lock is NOT reclaimed by it, so
> calling it alone cannot fix `SKIPPED_LOCKED` from a dead batch. Use dead-owner
> reaping (`acquire_device_lock`) as above.

## CLI subcommand (launcher calls this)
`python -m tiktok_workflow reconcile-stale-upload-locks --batch-id <id> --machines <csv> [--apply] [--lock-root <dir>]`
- Report-only without `--apply` (safe dry run: lists targets, touches nothing).
- Launcher passes `--apply` in the live preflight, guarded by a `Reconcile stalled`
  warning that does NOT abort the batch.

## Regression tests (RED→GREEN, existing `TestStateMachine` style)
1. **Dead-owner `tiktok-upload` lock is reconciled by guarded takeover.**
   Seed `machine_12.lock.json` (`status=running`, `owner_active=True`, `pid=999999`,
   `run_id=""`), `monkeypatch.setattr(state_machine, "owner_process_alive", lambda o: False)`,
   capture `acquire_device_lock` kwargs. Assert `released==1`, `run_id==batch_id`,
   `project=="tiktok-upload"`, machine==12.
2. **Reconcile preserves foreign / active / other-workflow locks.** Seed machine 78
   (luot), 3 (real live PID), 15 (avatar `--force-avatar-upload`). Assert
   `released==[]` and no `acquire_device_lock` attempted.
3. **Child does not leave a dead-owner lock `running` after exit.**
   `machine._release_lease_on_abnormal_exit()` must mark the lease `handoff`
   (retain), never `release()` it.
4. **Launcher invokes guarded reconcile, never raw-deletes.** Assert
   `reconcile-stale-upload-locks` present with `--batch-id`+`$batchId`,
   `--machines`+`($targetMachines -join ',')`, `--apply`; assert `Remove-Item` /
   `del ` / `raw delete` absent and a `Reconcile stalled` fail-closed branch present.

## Verification sequence
1. Run focused new tests (expect all green).
2. PowerShell syntax parse (no execution, no upload):
   `[System.Management.Automation.Language.Parser]::ParseFile("run_tiktok_upload_batch.ps1",[ref]$toks,[ref]$errs)` → no errors.
3. Dry-run the subcommand in report-only mode:
   `python -m tiktok_workflow reconcile-stale-upload-locks --batch-id <id> --machines 1,2,15,57,78`
   (no `--apply`) — confirms it loads and touches nothing; verify no lock files deleted.
4. `git diff --check`, keep EOL (repo is CRLF).
5. Relevant full suite. **Attribute pre-existing failures** (e.g.
   `ImportError: cannot import name 'PopupAction' from 'automation_core'` — an
   environment/contract issue unrelated to locks) separately; they are not regressions
   from the lock fix.

## Pitfalls
- **`owner_active=True` on a dead lock is expected** — do NOT treat it as "live".
  Trust `owner_process_alive` (real PID probe) only.
- **Do NOT reuse `open_failed_locked_lock` for `running` stale locks**; it won't
  reclaim them.
- **Monkeypatch trap:** if the helper does a *local* `from automation_core.device_lock
  import acquire_device_lock`, `monkeypatch.setattr(state_machine, "acquire_device_lock", ...)`
  is bypassed and the test fails (released==0). Import at **module top level** so the
  test can override `state_machine.acquire_device_lock`.
- **`patch` tool can swallow the following class header** when inserting a large test
  block (e.g. it ate `class TestConfig:`). Re-read the patched region immediately and
  restore the class declaration if the diff consumed it.
- **Tests may land under a different `unittest.TestCase` class** than intended and
  still run; verify the method resolves under the intended class when asserting pytest
  node IDs (`file.py::ClassName::method`).
- **Exact attribution when schema lacks `batch_id`:** reconcile by target-membership in
  the current batch list only and stamp `run_id` forward; do NOT broad-unlock.
- Report: exact changed files, focused + full-suite status, dry-run output, root cause,
  and rollback baseline path (e.g. `git stash` of the 4 touched files, or a backup dir
  for non-git trees). No commit/push unless asked.
