# Upload Hook Architecture & Preflight Gates in Feed Session

## 1. Overview
At the final feed session of each shift (session 3), after the feed swipe session finishes (and independent of the follow hook), `multi_machine_feed_session.py` invokes `_run_upload_hook`.

## 2. Five Preflight Gates
Before any subprocess or device interaction is initiated, 5 fail-safe gates are checked:
1. **Session Index Gate**: Only runs when `_session_index == 3` (or final session).
2. **Status Gate**: Requires `child_result.final_status in {"success", "degraded"}`.
3. **Sensitive Stop Gate**: Skips if `stop_reason` contains sensitive terms (login, otp, 2fa, captcha, verify, banned, suspended, locked).
4. **Workbook & Account Gate**:
   - Resolves `Tik{row_index}.xlsx` from `D:\OneDrive\TaadaaData\kibe\` using case-insensitive mapping (`WORKBOOK_FILENAMES`, note `tik3.xlsx` lowercase).
   - Reads machine row matching `account.machine`.
   - Skips if `ID` is missing/empty/`MISSING_ID` (`missing_account_id`).
   - Skips if `Folder Video` is empty (`missing_video_folder`).
5. **Video Render Ready Gate**:
   - Computes `next_video = int(posted_count) + 1`.
   - Checks `D:\TIKTOK-videonuoinick\<Folder Video>\<next_video>.mp4`.
   - Skips if file does not exist or `stat().st_size == 0` (`video_not_rendered`).

## 3. Subprocess Execution
- Invokes `python -m tiktok_workflow --config D:\Taadaa\Tiktok-video\config-machine-<M>.yaml --workflow-workbook D:\OneDrive\TaadaaData\kibe\<TikN>.xlsx --machine <M> --no-dry-run`.
- Timeout: 900s (15 min).
- Subprocess isolation: runs with cwd `D:\Taadaa\Tiktok-video`.
- Result is saved to `upload_result.json` in the child run directory.
