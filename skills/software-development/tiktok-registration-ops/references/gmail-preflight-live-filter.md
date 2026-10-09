# Gmail Preflight Live Filter in Tiktok_Reg

## Purpose & Overview
Before launching multi-worker TikTok registration batches in `_run_all_targets.py`, targets containing Gmail addresses (`@gmail.com`) undergo an automated live verification check via `scripts/gmail_preflight_filter.py`.

This prevents workers from wasting time and device slots attempting to register accounts whose underlying Google accounts are already disabled/banned.

## Architecture
- **Filter Module:** `scripts/gmail_preflight_filter.py` (`filter_live_gmail_targets(targets, project_root)`)
- **Caller:** `_run_all_targets.py` (right after target capping / CLI filtering)
- **Bypass Flag:** `--skip-live-check` CLI argument skips this check if external API is unreachable or manual run requires it.
- **Underlying Live Checker:** `check_gmail_live_batch` (from `tools/check_gmail_live_fast.py`) calling `checkmail.live`.
- **Fail-Open Policy:** Only accounts explicitly confirmed as `DIE` (`result is False`) are removed. Missing, ambiguous, or error responses default to keeping the target (`fail-open`).

## Cleanup Actions on Confirmed DIE:
When a Gmail is confirmed `DIE`:
1. Excluded from the dispatch target list (`targets = [t for t in targets if ...]`).
2. Removed from the credential/target source file via `social_reg_v1.remove_captcha_dead_email_from_source(email)`.
3. Account cleared off the target Android device via `remove_device_google_account.remove_device_account_fast(serial, email)` so the phone is clean for subsequent runs.

## Unit Testing & Verification
- Unit test: `tests/test_gmail_preflight_check.py`
- Test command: `pytest D:/Taadaa/Tiktok_Reg/tests/test_gmail_preflight_check.py -v`
