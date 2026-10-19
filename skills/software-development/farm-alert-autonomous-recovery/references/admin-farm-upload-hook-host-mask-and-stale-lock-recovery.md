# Admin Farm UploadHook [HOST] Masking & Orphan Device Lock Recovery

## Incident Signature
- Batch Alert: `UploadScriptError:UploadHook: [HOST] host=admin machines=200-999 workbook_root=D:\OneDrive\TaadaaData\admin runtime=D:\Taadaa\runtime\admin`
- Cluster: Farm Admin (Machines 200-999, e.g. M201-M280)
- Process: Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`)

## Root Cause Dual-Failure
1. **Subprocess Error Masking in `_extract_upload_subprocess_error()`**:
   - `python_runner/flows/multi_machine_feed_session.py` inspected `stderr` before `stdout` and took `lines[-1]` blindly.
   - Entrypoint calls via SSH print host key warnings, and `taadaa_host.py` prints `[HOST] host=admin ...` to `stderr`.
   - Result: Benign configuration output in `stderr` completely masked the real error in `stdout` (e.g. `[NEEDS_USER_DECISION] ACQUIRE_LOCKS`).
2. **Orphan Device Locks on Admin PC (`Admin-PC`)**:
   - Prior crashed/aborted batch jobs (e.g. `tiktok-add-bao-mat-f2a`) left dead lock files in `C:\Users\Admin\.codex\device-locks\`.
   - When upload hook invoked `scripts.tiktok_workflow` with `user_authorized=False`, `automation_core.device_lock` strictly refused to override existing locks belonging to another project.

## Autonomous Triage & Recovery Playbook
1. **T0 Canary Inspection**:
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
2. **Inspect Remote Device Locks via Canonical SSH Tool**:
   ```bash
   python D:/Taadaa/tools/admin_ssh.py --powershell "Get-ChildItem C:\Users\Admin\.codex\device-locks"
   ```
3. **Execute Safe Quarantine Cleanup of Dead-Owner Locks**:
   ```bash
   python D:/Taadaa/tools/admin_ssh.py "python \"D:\Taadaa\tiktok-luot nuoi acc\scripts\reap-dead-owner-locks.py\""
   ```
   - Automatically identifies dead PIDs (`owner_process_alive() == False`) and locks older than 1h TTL.
   - Safely moves files to `C:\Users\Admin\.codex\device-locks-reaped/<timestamp>` (never hard-deletes).
4. **Verify Lock Released**:
   ```bash
   python D:/Taadaa/tools/admin_ssh.py --powershell "Test-Path 'C:\Users\Admin\.codex\device-locks\machine_<N>.lock.json'"
   ```
5. **Masking Prevention Rule in Code**:
   - In `_extract_upload_subprocess_error()`, always filter out non-error prefixes from `stderr`:
     `[HOST]`, `warning:`, `permanently added`, `post-quantum key`.
   - Match real error signatures from `stdout`: `[NEEDS_USER_DECISION]`, `workflow failed:`, `[ERROR]`, `[CRITICAL]`.
