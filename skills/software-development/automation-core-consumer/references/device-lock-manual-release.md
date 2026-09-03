# Device Lock Manual Release Procedure (User-Triggered)

This guide documents the exact workflow when the user requests manual release of device locks (e.g., `Gỡ lock 34 54 75 ra`).

## Key Invariants

1. **Only on Explicit Request**: Never auto-unlock or batch-delete retained locks on farm devices unless explicitly ordered by user.
2. **Dual Alias Matching**: Every locked machine has two lock files in `C:\Users\Kibe\.codex\device-locks\`:
   - `machine_<ID>.lock.json`
   - `serial_<SERIAL>.lock.json`
   Both files must be matched and cleaned.
3. **Backup Directory**: Always create a timestamped backup folder under `C:\Users\Kibe\.codex\device-locks\backup_user_unlock_<YYYYMMDD_HHMMSS>` and move/copy files there before unlinking.
4. **Safety Verification**:
   - Inspect lock metadata (PID, machine, serial, status) to check if the owner process is still running via `wmic`/process inspection.
   - Verify remaining locks in `C:\Users\Kibe\.codex\device-locks\` after release to ensure untouched devices remain protected.
