# Fast Auto-Login Recovery & Parent Device Lock Inheritance

## Context & Root Cause
In multi-machine batch sessions (`multi-machine-feed-session` via `run_tiktok.py`), the parent orchestrator process acquires exclusive device locks (`machine_<N>.lock.json`) for each machine running in the batch.

When a device encounters a missing expected account during `profile_preflight` (e.g. account switcher missing expected account row):
1. `feed_swipe_smoke.py` triggers `auto_login_recovery`.
2. First, it attempts Fast Targeted Auto-Login:
   `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID> --ss`
3. Previously, `tiktok_login_v1.py` unconditionally called `acquire_device_lock(user_authorized=False)`.
4. When `user_authorized=False`, if an active lock file already exists on disk, `acquire_device_lock` raises `DeviceLockNeedsUserDecision`.
5. `tiktok_login_v1.py` logged `[device-lock] NEEDS_USER_DECISION: ...` and exited with returncode 2.
6. `feed_swipe_smoke.py` logged `fast_login_failed_fallback_reconcile` and fell back to `reconcile_tiktok_accounts.py`.
7. `reconcile_tiktok_accounts.py` was too heavy, scanning full account inventories, and often timed out after 300 seconds, ending in `manual-needed`.

## Architecture of Inherited Parent Device Lock
To allow Fast Auto-Login to run seamlessly under an already locked parent batch:
1. **Parent Project Allowlist in `tiktok_login_v1.py`**:
   ```python
   PARENT_LOCK_PROJECTS = (
       "tiktok-luot nuoi acc",
       "tiktok-feed",
       "multi-machine-feed-session",
   )
   ```
2. **`--allow-parent-lock` CLI Flag in `tiktok_login_v1.py`**:
   - `parser.add_argument("--allow-parent-lock", action="store_true", ...)`
   - Helper `_is_parent_lock_owner(exc)` inspects `exc.owner` (dictionary or object with `project` and `pid`).
   - If `getattr(args, "allow_parent_lock", False)` and the owner project is in `PARENT_LOCK_PROJECTS`:
     Script creates `InheritedDeviceLock(machine=args.stt, serial=device_id)` and proceeds with login instead of exiting with code 2.
3. **Parent Invocation Contract in `feed_swipe_smoke.py`**:
   `_run_fast_targeted_login` must append `"--allow-parent-lock"` to `fast_cmd`:
   ```python
   fast_cmd = [
       str(python_exe),
       str(fast_login_script),
       str(machine_id),
       "--email", str(expected),
       "--ss",
       "--allow-parent-lock",
   ]
   ```
