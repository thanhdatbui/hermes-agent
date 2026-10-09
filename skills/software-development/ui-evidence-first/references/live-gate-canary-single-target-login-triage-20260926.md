# Live Gate Canary Protocol: Single-Target Profile Preflight & Login Blocker Triage (M40 / 2026-09-26)

## Context & Invariant
When executing a live root gate canary on an isolated device (e.g. M40 only, avoiding other fleet machines like M66):
1. **Mandatory Diagnostic Entrypoint:** Always run `python D:/Taadaa/tools/inspect_machine.py <M>` first to capture live screen/power/focus state and verify device responsiveness without perturbing app state.
2. **Three-Way Source of Truth Resolution:**
   - **SQLite (`D:/Taadaa/data/tiktok_tracker.db`):** `SELECT username, may, tik FROM farm_account_info WHERE may = <M>` provides the exact account-to-slot mapping.
   - **Safe Workbook (`taikhoan_run_safe.xlsx` sheet `Accounts`):** Identifies the target row index and account ID expected for the active day's shift.
   - **Live Cron Manifest (`assignment-v1-*.json`):** Determines the scheduled slot time and row (even day vs odd day schedule, e.g. Day 26 even -> Row 2/4/6/8).
3. **Double-Lock Verification:** Check both `machine_<M>.lock.json` and `serial_<SERIAL>.lock.json` across both candidate lock directories (`~/.codex/device-locks` and `~/AppData/Local/automation-core/device-locks`) to ensure 0 active/stale locks before spawning the runner.

## Official Runner Invocation Pattern
Invoke the official PowerShell runner with bounded test parameters to isolate behavior and prevent side effects:
```powershell
powershell -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" `
  -Machines <M> `
  -Row <ProvenRow> `
  -RecoveryTestSwipes 2 `
  -SkipAccountWorkbookSync `
  -Run
```
*Note:* Do not run full sessions or trigger account workbook synchronization during single-target canary triage.

## Triage Pattern: `login/account screen detected` (`manual-needed:login`)
When the runner fails at `profile_preflight_identity_guard` with:
- `detected_screen: manual-needed:login`
- `stop_reason: login/account screen detected`
- `blocker_type: login-gms-verification`

### Evidence Signatures
- **Baseline step:** For You feed is displayed properly (`for-you` screen detected).
- **Navigation action:** Tap coordinate on Profile tab (`[864, 1794][1080, 1920]`, center `[972, 1857]`).
- **Failure state:** App transitions into `SignUpOrLoginActivity` / Phone entry form (`Số điện thoại`, `Đăng nhập`, `Tạo tài khoản`) rather than opening personal profile or account switcher.
- **Root cause distinction:**
  - This indicates the session was logged out or expired on the device for the target slot/account.
  - Tapping Profile directly bounces to the TikTok auth landing screen.
  - Fail-closed contract: Runner cleanly executes teardown (`cleanup_close_all`) and releases device locks (`recovery_lock_handoff.json` -> `final_status: released`).

### Evidence & Artifact Contract
Always collect and report:
- Exit code & `final_status` from `run_manifest.json`
- Step history & exact reason from `machines/machine_<M>/<RUN_ID>/summary.txt`
- Specific UI XML nodes from `profile_preflight_identity_guard/attempt_1/ui.xml`
- Screenshot verification (file existence, byte count, PNG signature)
- Post-run lock absence verification
