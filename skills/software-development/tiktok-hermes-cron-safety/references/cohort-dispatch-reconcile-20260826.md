# Cohort Dispatch & Reconcile Architecture (2026-08-26)

## Invariant Core
1. **Denominator / Expected Machines**:
   - `build_cohort_plan(manifest, as_of)` selects the active `block_index` + `session_index` currently being dispatched.
   - `expected_machine_ids` MUST equal the set of machines launched in that exact session. Do NOT expand the denominator to the entire block/day if only one session is launched, as unlaunched machines will falsely trigger `missing`/`timeout`.
   - Never infer expected count from account entries or output folders.

2. **Launcher / Process Identity Binding**:
   - Launcher (`tiktok_runner.py` / `run-feed-session.ps1` / `run_tiktok.py`) binds:
     - `assignment_id`
     - `cohort_id`
     - `block_index`
     - `session_index`
     - `entry_id`
     - `worker_id`
     - `machine`
   - Child process writes these identity fields directly into `run_manifest.json` on completion.

3. **Watchdog Verification**:
   - `cohort_watchdog.py` strictly matches `run_manifest.json` against the frozen `cohort-v1-*.json` plan.
   - Any manifest from a different session, block, cohort, or assignment is rejected.
   - `load_cohort_plan` verifies `manifest_digest` against the source assignment manifest to detect tampering.

4. **Multi-Child Process Lease**:
   - Live lease (`runner-live-lease/<day>.json`) records all spawned child PIDs (`rows: [{"row": r, "pid": p}]`).
   - `_lease_alive()` keeps the lease active as long as ANY child row PID is alive. It only unlinks the lease when ALL child processes have terminated. This prevents duplicate batch spawns when one row finishes early.

5. **Follow Architecture**:
   - **Organic For You Feed Follow**: Runs randomly inside feed session (20% on Deep Inspect intervals).
   - **Cross-Repo Follow Hook (`tiktok-follow`)**: Spawns `run_follow.py` after a successful feed session (`success`/`degraded`).
     - Gate 0: Video count <= 0 skips follow to prevent account follow-release bans.
     - Sensitive failure skip: Skips follow if feed stopped on login/OTP/2FA/captcha.
     - Daily lock / release cooldown: Skips follow if the account failed follow earlier on the same day.
