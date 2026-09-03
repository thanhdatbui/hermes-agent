# Workbook Serial Drift + Lock Timeout (Case 73, 02/09/2026)

## Root Cause

**Workbook Serial Drift (Machine 75..80):**
- `Tik2.xlsx` and `tik3.xlsx` Column B (`device ID`) got swapped during creation — machine 75↔79, 76↔78, 77↔80.
- Feed session uses `taikhoan_run_safe.xlsx` (correct), but upload subprocess opens `Tik2.xlsx` directly and maps by `--single-device <serial>`.
- Result: `ACCOUNT_MISSING: expected account was not found` because serial maps to wrong row/nick.
- 5-min sync cron (`sync-tik-workbooks.py`) only synced Column C (`ID`), never validated Column B (`device ID`).

**Lock Timeout (`_ShiftUploadLedger.claim_reservation`):**
- Previously passed `deadline=hard_dl` (global session deadline) to `_InterProcessFileLock`.
- When 80 machines hit upload hook simultaneously near session end, `hard_dl` was nearly exhausted → 39 machines failed with `shift_upload_lock_timeout_fail_closed`.
- Fix: dedicated `shift_upload_lock_timeout_seconds=180` with jitter backoff, decoupled from global deadline.

## Fixes Applied

1. **`multi_machine_feed_session.py`**: `_ShiftUploadLedger.claim_reservation` uses dedicated `lock_timeout=180s` + jitter instead of `hard_dl`.

2. **`sync-tik-workbooks.py`**: 
   - Added `EXTRA_MACHINES` dict for machines 75..80 with hardcoded serials
   - Built `canonical_serials` from Tik1.xlsx + EXTRA_MACHINES + master DAT
   - Now validates AND enforces Column B (`device ID`) on every sync cycle
   - Added `_is_valid_serial()` filter to reject dates/garbage in serial column

3. **`feed_swipe_smoke.py`**: Added `_maybe_recover_missing_account_via_login` that triggers `reconcile_tiktok_accounts.py` when switcher reports `ACCOUNT_MISSING`.

4. **Tests**: 
   - `test_sync_fixes_swapped_serial` in `test_sync_tik_workbooks.py`
   - `test_auto_login_recovery_on_missing_account_in_switcher` in `test_feed_session_smoke.py`

All 104 tests pass.

## Key Lesson

**Sync cron MUST validate Column B (device ID) every cycle** — not just Column C (ID). The 5-min sync was a false sense of security because it silently preserved a broken serial mapping for months.