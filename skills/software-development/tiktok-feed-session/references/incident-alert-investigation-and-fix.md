# Incident Alert Investigation & Fix

## Trigger

A batch alert names specific machines and reports a systemic feed/account-switcher failure. The user expects investigation and a global script fix, not only a live-device status report.

## Required sequence

1. Run the mandatory machine-scoped inspection for every named machine:
   `python D:/Taadaa/tools/inspect_machine.py <N>`.
2. Read the newest relevant run log/artifact and the farm case documentation before assigning a cause.
3. Classify each finding as `confirmed`, `unproven`, or `live-session/login state`. A current Launcher/Sleep result proves only the current device state; it does not prove logout, login, or the absence of a code defect.
4. Resolve the execution path and canonical implementation. Dispatch a Worker for code investigation/fix and a focused mocked regression test when the alert indicates a reusable flow defect.
5. Keep the batch locked. Do not rerun the whole fleet, use ad-hoc taps, logout accounts, or clear app data to hide symptoms.
6. Verify the Worker’s actual diff, modified-file scope, and focused test output. Then run the official canary only on the resolved target machine(s). Reopen the fleet only after fresh canary evidence passes.

### Bẫy Schema DB `tiktok_tracker.db` & Vị Trí Device Locks
- **Table `farm_account_info` trong `D:/Taadaa/data/tiktok_tracker.db` KHÔNG CÓ cột `status`:**
  - Các cột thực tế: `(username, may, tik, updated_at, host_id)`.
  - Truy vấn chuẩn: `SELECT may, tik, username FROM farm_account_info WHERE may = ? AND tik = ?`. CẤM select cột `status` kẻo văng `sqlite3.OperationalError: no such column: status`.
- **Vị trí chuẩn của Device Locks (Kibe host):**
  - Lock files KHÔNG nằm ở `D:/Taadaa/locks/` mà nằm tại:
    - `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`
    - `C:\Users\Kibe\.codex\device-locks\serial_<SERIAL>.lock.json`
  - Đối chiếu giải phóng lock qua `recovery_lock_handoff.json` trong thư mục run artifact.

### Official Canary CLI Pattern (Single Machine / Scoped Recovery)
- Lệnh chạy canary chính thức qua PowerShell:
  `powershell.exe -ExecutionPolicy Bypass -File "D:/Taadaa/tiktok-luot nuoi acc/scripts/run-feed-session.ps1" -Machines <N> -Row <R> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`
- Đảm bảo trích xuất đầy đủ:
  - Exit code, `final_status` trong `run_manifest.json` và `m<N>_manifest.json`.
  - Artifact UI XML/screenshot tại `profile_identity`, `verify_profile`, `swipe_2_after`.
  - Trạng thái giải phóng lock tại `recovery_lock_handoff.json`.

## Incident example: account switcher

Observed alert signatures included `ATX_SESSION_UNAVAILABLE`, `ACCOUNT_MISSING`, and `login/account screen detected` on M7, M11, M40, and M66. Live inspection showed LauncherActivity (three devices asleep; one awake) rather than TikTok. The correct conclusion is: live TikTok/account state was unproven, while the account-switcher path still required code-level investigation. Do not stop the task at “device is Home/Sleep.”

## Reporting template

- `Mục đích`: investigate and globally fix the reusable flow failure.
- `Đã inspect`: list exact machine IDs and command evidence.
- `Code path`: consumer entrypoint and canonical implementation.
- `Confirmed`: facts from fresh logs/artifacts/tests.
- `Unproven`: live state or root cause lacking matching XML/screenshot.
- `Fix`: exact files and focused test result.
- `Canary`: target-scoped result with fresh evidence.
- `Fleet`: remain locked until canary passes.
