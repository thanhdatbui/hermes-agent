# Locked Device Triage & Shift Startup Diagnostics

Use this reference when an operator inquires why a scheduled shift (e.g. morning ca 1 at 06:00) appears not to have run or when reporting an active device lock alert from Telegram.

## Core Invariant: Device Lock Isolation
- A single machine retaining a lock (status `blocked`, `running`, `recovery`, `handoff` with TTL 2h) **ONLY isolates that specific machine**.
- It does **NOT** block the farm scheduler (`tiktok_picker`, `tiktok_runner`, or multi-machine batches) from executing the remaining available machines.
- The dispatch cohort automatically excludes locked machines during candidate resolution (`_due_entries` / lock probe) and launches the batch for all healthy machines.

## Proxy Outage & Fail-Closed Safety Gate (2026-08-28)
- When a proxy server (e.g., `test.taadaa.click`) is down/unreachable (ports closed / connection refused):
  - Every feed runner preflight checks `require_vichanger_connected` / `require_android_vpn`.
  - When proxy readiness times out, the runner halts immediately with `blocked-vichanger-vpn` and `swipes_completed=0`.
  - **Fail-Closed Protection**: The app NEVER executes feed swipes on direct host/cellular IP without working proxy/VPN protection.

## Cascade Device-Locks & Recurring Cron Alert Storms (2026-08-30)
- **Cascade Lock Pattern**: When a proxy box or network glitch causes VPN preflight timeout across many devices, each device enters `status: blocked` with a 2h TTL lock in `~/.codex/device-locks/`.
- **Recurring Cron Loop**: Because `reap-dead-owner-locks.py` intentionally preserves `status: blocked` locks for 2 hours (to hold the scene for operator triage), recurring 15-minute cron runners (`phase9-runner-tiktok-feed`) repeatedly attempt to run, skip locked machines with `skipped-device-locked`, and trigger repeated watchdog alert reports.
- **Triage & Recovery Procedure**:
  1. **Identify Root Cause**: Check whether failures are VPN preflight timeouts (`MissingVpnRecoveryError / TimeoutError`) vs app/UI popups.
  2. **Pause Cron if Requested/Needed**: If operator requests to halt farm automation or investigate network, pause `phase9-runner-tiktok-feed`, `phase9-watcher-tiktok-feed`, and `tiktok-feed-session-watchdog`.
  3. **Restore Proxy/VPN**: Verify box proxy ports, usernames (`mobi{port_suffix}`), and credentials in `PROXYgandienthoai.xlsx`.
  4. **Clear Stale Blocked Locks**: Once proxy is restored, quarantine or reap stale `blocked` device locks from `~/.codex/device-locks/`.
  5. **Resume Schedule**: Unpause cron jobs to allow next scheduled shift to run cleanly.

## Differentiating Active Device Locks vs Backup History
- When user or log presents a lock file (e.g., `machine_73.lock.json`):
  - Always verify whether it resides directly at root `~/.codex/device-locks/machine_<ID>.lock.json` vs inside historical backup folders (`backup_*`, `quarantine/*`).
  - Files under subdirectories are historical snapshots, not active locks.

## Alert Screenshot Triage vs Live Machine State (Temporal Verification)
- When operator sends an alert screenshot or requests "fix máy X" based on Telegram alert logs (e.g. from Farm Alerts):
  1. **Timestamp & Shift Gate**: Check the timestamp, shift/row, and account in the alert against the current time. Do not assume the device is currently stuck in the state depicted in the screenshot.
  2. **Check Active Lock & Live Session Artifacts**:
     - Check `~/.codex/device-locks/machine_<ID>.lock.json` and `serial_<SERIAL>.lock.json` to see if the lock is currently `blocked`, `running`, or already reaped/released.
     - Inspect the latest run directory under `D:\Taadaa\runtime\kibe\live\<YYYY-MM-DD>\...` for `machine_<ID>`. Check `summary.txt` and `run_manifest.json` to determine if a subsequent session was already scheduled and succeeded (`final_status: success`, swipes completed).
  3. **Live Device State Confirmation**:
     - Check current ADB focus (`dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'`) and capture fresh screenshot.
     - If the machine has already executed a subsequent shift successfully and returned to Launcher/Home, **DO NOT run ad-hoc recovery or kill active processes**.
  4. **Report Format**:
     - `Mục đích`: Xác minh và xử lý Máy X theo yêu cầu.
     - `Hiện trường cũ trong ảnh`: Timestamp, account, lý do dừng phiên cũ.
     - `Trạng thái live thực tế`: Run ID, account hiện tại, kết quả feed (swipes/status), follow hook status, và foreground app hiện tại.
     - `Blocker`: Nêu rõ nếu máy đã hoàn tất phiên và sẵn sàng cho ca tiếp theo mà không cần can thiệp thêm.

## Multi-Workbook Cross-Check for Account Existence (2026-08-28)
- When evaluating whether a machine has an account registered for a given row/slot (e.g., Row 2 / Tik2):
  1. **Check Master Registry**: `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (column C `ID`).
  2. **Check Safe Feed Workbook**: `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (column C `ID`).
  3. **Check Upload Sub-Workbook**: `D:\OneDrive\Tiktok\TikN.xlsx` (e.g., `Tik2.xlsx`).
  4. **Check Cron Source Config**: `D:\Taadaa\runtime\kibe\cron-source\hermes_cron_source_config.json`.
- **Pitfall - Premature "No Account" Diagnosis**: If Master & Safe workbooks contain a registered ID (e.g. `yeisiearet4` for machine 73 Row 2), but `Tik2.xlsx` is blank or `hermes_cron_source_config.json` was not reloaded, the picker excludes the machine from the cohort. **Do NOT report that the machine has no account / needs registration**. Report that the account exists in master but needs synchronization to sub-workbooks/config.
- **Source of Truth Rule**: Always take `taikhoan_run_safe.xlsx` and `taikhoan_dat_v2` as authoritative data sources. Never fabricate or assume missing data.

## Reasons a Machine is Excluded from a Daily Manifest / Shift Cohort
1. **Invalid Hardware Serial (Device ID)**: The cell in `taikhoan_run_safe.xlsx` contains a placeholder or registration date (e.g. `23/08/2026`) instead of a real ADB serial.
2. **Missing Account for Active Row in Source Config**: The row corresponding to the current shift (Row 2, 4, or 6) is blank/None or not yet synced into `hermes_cron_source_config.json`.
3. **Active Device Lock**: The machine is currently locked under `~/.codex/device-locks/`.

## Investigation Checklist for "Ca sáng không chạy"
1. **Check Manifest & Active Cohort**:
   - Inspect `D:/Taadaa/runtime/kibe/cron-state/manifests/<YYYY-MM-DD>/ACTIVE.json` and associated `assignment-v1-*.json`.
   - Verify if `tiktok_picker` successfully ran at 06:00 and created the cohort plan under `cohorts/<YYYY-MM-DD>/`.
2. **Check Live Lease & Runner Dispatch**:
   - Check `D:/Taadaa/runtime/kibe/cron-state/runner-live-lease/<YYYY-MM-DD>.json`.
   - Inspect `started_at`, `expected_machine_ids`, `expected_count`, and active process PID.
   - Confirm if `run-feed-session.ps1` was spawned in the background with detached process groups.
3. **Execution Cadence vs Reporting**:
   - Understand that feed sessions run with stagger delays and concurrency limits (e.g. max 40 workers across 72+ machines).
   - `feed_session_watchdog` only delivers the unified completion report once the entire cohort completes its session cycle (or reaches terminal state).
   - The absence of a Telegram report at 06:20 does not mean the batch failed; it means workers are actively swiping/processing.

## Operator Communication Format
- State clearly whether locked machines impacted the wider batch (No).
- Report exact timestamp and numbers: Manifest generation time, Cohort machine count, and Runner dispatch timestamp.
- Explain watchdog timing: Report will post automatically once the cohort cycle finishes.
- Provide clear unlock instruction for the isolated machine if operator intervention is needed (`Mở khóa máy XX`).
