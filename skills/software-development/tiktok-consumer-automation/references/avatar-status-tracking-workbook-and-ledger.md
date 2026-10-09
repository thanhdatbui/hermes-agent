# Avatar Status Tracking, Workbook Update, and Idempotency Ledger

## Architecture & Integration

In `Tiktok-video` consumer workflows:
1. **Workbook Field (`Avatar`)**:
   - Canonical header: `Avatar` (aliases: `Avatar Đã Up`, `Avatar Status`).
   - `account_source.TikTokAccountSource.update_avatar_status(status="OK")`:
     - Uses `automation_core.workbook.atomic_workbook_update` with backup and lock timeout (30s).
     - Dynamically finds or appends the `Avatar` column if not already present in the sheet.
     - Supports `dry_run` mode without file I/O.
2. **State Machine (`ENSURE_AVATAR`)**:
   - Once avatar is uploaded and CDN settle delay elapses, updates workbook via `account_source.update_avatar_status("OK")`.
   - Appends record to ledger: `D:/CodexRuntime/tiktok-video/idempotency/avatar-ledger.jsonl`:
     ```json
     {"timestamp": "...", "machine": "...", "device_id": "...", "account": "...", "folder": "...", "status": "VERIFIED_SUCCESS"}
     ```
3. **Runner Script (`run_tiktok_upload_avatar.ps1`)**:
   - Param `$ForceAvatarMachineList` defaults to `""`.
   - When omitted, invokes `scripts/resolve_avatar_pending_machines.py [string]$Tik` via `python -B` to detect machines whose `Avatar != 'OK'`, skipping accounts with `MISSING_ID` or invalid account IDs.
   - **Workbook Name Discrepancy:** Row 3 uses `tik3.xlsx` (lowercase 't') while others use `Tik{num}.xlsx`. `resolve_avatar_pending_machines.py` handles this casing mapping automatically.
   - **PowerShell Null Path Trap with `$ErrorActionPreference = 'Stop'`:**
     - `$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path` MUST be declared BEFORE `if (-not $ForceAvatarMachineList)`.
     - In PowerShell, `Join-Path $null "..."` triggers `ParameterBindingValidationException` under `$ErrorActionPreference = 'Stop'`. Fallbacks like `if (-not (Test-Path $resolverScript))` can never execute if the initial `Join-Path` binds to `$null`.
   - **User Rule on Machine Scope (Machine 38):** Never blindly exclude Machine 38 across all workbooks! Machine 38's status is slot-dependent (e.g. Tik4 has 2 videos and avatar OK, but Tik5 and Tik6 have separate accounts awaiting avatar upload). Always let the workbook `Avatar` column determine eligibility.

4. **Dedicated Resolver (`scripts/resolve_avatar_pending_machines.py`)**:
   - Standalone CLI replacing legacy inline `$pyScript` in `run_tiktok_upload_avatar.ps1`.
   - Usage: `python scripts/resolve_avatar_pending_machines.py <tik_num>` -> outputs comma-separated machine IDs (e.g. `1,2,3...`).
   - Avoids PowerShell here-string escape issues and quoting/f-string parser bugs completely.

5. **Workbook Migration Across Farm (Tik1..Tik6)**:
   - For historic accounts: accounts with `Video Đã Đăng >= 1` (and Tik4 machine 36) are marked `Avatar = "OK"`.
   - Tik5 and Tik6 remain `None` for machines pending avatar upload.

5. **Pitfall: Inline Python in PowerShell Here-String with F-Strings**:
   - In PowerShell expandable here-strings (`@"..."@`), `{var}` inside Python f-strings (e.g. `f"Error reading Tik{Tik}.xlsx: {e}\n"`) is NOT interpolated by PowerShell, but Python expects `Tik` to be a defined Python variable -> causes runtime `NameError: name 'Tik' is not defined`.
   - **Fix pattern:** Always use single-quoted here-strings (`@'...'@`) so PowerShell leaves all quotes and braces verbatim, and pass arguments via CLI:
     ```powershell
     $pyScript = @'
     import sys, openpyxl
     tik_num = sys.argv[1] if len(sys.argv) > 1 else "1"
     wb_path = rf"D:\OneDrive\TaadaaData\kibe\Tik{tik_num}.xlsx"
     ...
     '@
     $resolvedList = & python -c $pyScript [string]$Tik
     ```

6. **Post-Feed Avatar Watchdog (`scripts/avatar_post_feed_watchdog.py`)**:
   - **Trigger Window:** Runs late night after Ca 3 Phiên 3 finishes (~22:30 to 00:45 Asia/Ho_Chi_Minh). Hard cut-off at 00:45 to avoid conflicting with the nightly registration batch (starts ~01:00). Supports `--force` to bypass time check.
   - **Target Row Mapping:** Odd day of month -> Row 5 (`Tik5.xlsx`), Even day of month -> Row 6 (`Tik6.xlsx`). Supports `--row` to override.
   - **Active Runner Gate:** Checks via psutil for active feed/upload runners: `multi-machine-feed-session`, `multi_machine_feed_session`, `run-feed-session.ps1`, `run_follow`, `hermes_cron_runner.py`, `run_tiktok.py`. Alternatively verifies `f"{today}_ca3_phien3"` in `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json`. If runner is active, exits 0 silently.
   - **Idempotency Rule ("Mỗi row nick 1 lần thôi"):**
     - Ledger path: `D:\Taadaa\runtime\kibe\cron-state\avatar_upload_history.json` (supports `--state-file`).
     - Structure: `{"row5": {"m1": {"status": "success", "timestamp": "..."}}, "row6": ...}`.
     - Reads `D:\OneDrive\TaadaaData\kibe\Tik{row}.xlsx` to find machines with valid accounts whose `Avatar` status is not yet `OK`.
     - Cross-references ledger; selects ONLY machines without `status: "success"`. If empty, exits 0 silently.
   - **Assignment Manifest Generation:**
     - Generates manifest at `D:\CodexRuntime\tiktok-video\assignment-manifest-avatar-row{row}.json`:
       `{"schema_version": 1, "assignment_id": f"avatar-tik{row}-all-{ts}", "owner_id": "hermes-kibe-avatar", "resources": [f"machine:{m}" for m in machines], "reviewed_at": iso_ts}`
   - **Batch Execution (`run_tiktok_upload_avatar.ps1`):**
     - Invocation:
       `powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <row> -AssignmentManifest <manifest_path> -WorkerId hermes-kibe-avatar -ForceAvatarMachineList <m1,m2,...> -MaxParallel 40 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml`
     - Env Var: Must set `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION=0.4.45` before invocation to avoid automation-core version mismatch.
     - Supports `--dry-run` to validate logic without spawning PowerShell.
   - **Ledger Update & Verification:**
     - Reads `summary.csv` from newest batch run in `D:\CodexRuntime\tiktok-video\batch-runs\batch_tik{row}_*`.
     - Machines with `ExitCode == 0` and `Verified == True` are recorded as `status: success`.
   - **Python Environment & Testing:**
     - Automation Python runner: `D:\Taadaa\python-envs\automation\Scripts\python.exe` (not `automation\python.exe`).
     - Unit test suite: `tests/test_avatar_post_feed_watchdog.py`.

     7. **Durable Replacement Queue (`avatar_replace_queue`) vs Web Crawl Pitfall**:
     - **The Dashboard Overwrite Trap**:
       - Daily TikTok tracker (`tiktok_account_tracker.py`) crawls TikTok CDN snapshots at 07:00. It flags `has_avatar = 1` for ANY non-default avatar URL.
       - Merely resetting the Excel `Avatar` column or executing `UPDATE snapshots SET has_avatar = 0` is dangerously fragile: if an evening batch fails (VPN drop, UI stall, network timeout), the account still holds the previous avatar on TikTok CDN. The morning crawl sees a non-default avatar and re-overwrites `has_avatar = 1`. The evening watchdog would then permanently skip the failed machine on subsequent nights!
     - **Durable Architecture**:
       - SQLite table `avatar_replace_queue` in `D:/Taadaa/data/tiktok_tracker.db` with composite primary key `(username, tik, host_id)`:
         ```sql
         CREATE TABLE IF NOT EXISTS avatar_replace_queue (
             username TEXT,
             may INTEGER,
             tik INTEGER,
             host_id TEXT,
             folder_video TEXT,
             video_goc TEXT,
             status TEXT DEFAULT 'PENDING',
             last_error TEXT,
             created_at TEXT DEFAULT (datetime('now', 'localtime')),
             updated_at TEXT DEFAULT (datetime('now', 'localtime')),
             PRIMARY KEY (username, tik, host_id)
         );
         ```
       - **Watchdog Query Integration (`post_evening_avatar_watchdog.py`)**:
         - Binds `LEFT JOIN avatar_replace_queue q ON m.username = q.username AND m.may = q.may AND m.tik = q.tik`.
         - Accounts with `queue_status == 'PENDING'` are unconditionally flagged as `unuploaded`, even if `snapshots.has_avatar == 1`.
         - Transition to `DONE` occurs ONLY when batch verification confirms `SUCCESS` / `Verified == True` on the physical device.
         - Failures transition state to `FAILED` telemetry while preserving `status = 'PENDING'` in the queue, ensuring automatic retries on subsequent nights.
     - **Source Resolution Fix (`resolve_avatar_path`)**:
       - `video gốc` MUST take precedence over `Folder Video` because `avatar_source_root` may contain legacy folders with colliding numbers from different topics.
       - Always sync avatar binaries to both ends: `D:/TIKTOK-videonuoinick/<Folder Video>/avatar.jpg` and `D:/video goc/<video_goc>/avatar.jpg`.



