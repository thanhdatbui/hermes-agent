# Pitfalls & Operational Invariants: Device-Lock Watchdog False Alarm & Follow Skip Breakdown

## 1. Watchdog False Alarm on Staged Device Locks (2026-09-06)
- **Symptom:** Watchdog (`feed_session_watchdog.py`) reported 80/80 machine failures ("Fail (80): M1..M80") at 06:15:44 for Morning Shift 1, causing false alarms on Telegram.
- **Root Cause:**
  - An earlier batch (`row-2-060253`) ran while overnight jobs (e.g. `gmail_reg_v10.py`, `gpm-login`) still held `device_lock`.
  - All 80 machines exited early with status `skipped-device-locked`.
  - Watchdog woke up, found 80 `summary.txt` files, observed `is_feed_runner_active() == False` in the brief gap between cron ticks, and falsely concluded that all 80 machines had completed their run and failed.
  - The watchdog atomically claimed the session key in `feed_session_reported.json`, which suppressed any subsequent reporting when the real run (`row-2-061651`) executed successfully (64 Success, 16 Fail).
- **Rule & Guard:**
  1. `is_device_locked_skip(data)`: Identify machines whose status is `skipped-device-locked` or whose stop reason contains `device lock active` / `[device-lock]`.
  2. `can_report_session`: When `now_hm < window_end_hm`, if any expected machine has ONLY a `skipped-device-locked` result and has not yet had a real live run, watchdog MUST NOT report early. It must wait until either:
     - All expected machines have executed a real run (not skipped by lock), OR
     - The window deadline (`window_end_hm`, e.g. 07:30) has passed.
  3. `merge_machine_result`: When merging multiple run folders within the same shift, a real run result (even a runtime failure) MUST take precedence over a placeholder `skipped-device-locked` record.

## 2. Follow Hook Skip Explanations (Breakdown for Operator)
When the operator asks why many machines skipped follow (`Bỏ qua nhiều v à`), do not guess. Parse `follow_result.json` and categorize into 3 distinct policy groups:
1. `under-5-videos-follow-disabled`: New accounts with fewer than 5 published videos have cross-following disabled to prevent TikTok shadowbans or instant follow drops.
2. `follow-released-daily-cooldown`: Accounts that encountered `FOLLOW_FAILED` (TikTok automatically unfollowed immediately after click) enter a 24h cooldown to protect account health.
3. `sensitive-skip-manual_needed`: Feed sessions that terminated in a manual-needed or UI-blocked state skip follow hooks fail-closed to avoid interacting with unexpected dialogs.
