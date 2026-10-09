# Watchdog Upload Classification Bug - 2026-09-04

## Issue
`feed_session_watchdog.py` misclassifies `"already_uploaded_in_shift"` upload results as **"Lỗi script/xác minh"** instead of **"Bỏ qua"**.

## Root Cause
Lines 532-539 in `feed_session_watchdog.py` define `skipped_keywords` but miss `"already_uploaded_in_shift"`:

```python
skipped_keywords = (
    "video_not_rendered", "missing_video_folder", "missing_account_id",
    "not-final-session", "sensitive-skip", "cooling_period",
    "account_cooling_period", "age_gate", "under_10_days"
)
# Missing: "already_uploaded_in_shift"
```

## Evidence (2026-09-04 Row 2, Ca 1 Phiên 3)
- **Run 09:16**: 51 uploads success, 20 failed (`upload_subprocess_nonzero`), 1 skipped (`video_not_rendered`)
- **Run 10:30**: 5 success (recovered machines), **70 skipped** (`already_uploaded_in_shift`), 1 failed (`upload_subprocess_nonzero`)
- **Watchdog report** (merged): showed "Bỏ qua (71)" but actually should be "Bỏ qua (1)" + "Lỗi script/xác minh (70)" due to bug

## Fix
Add `"already_uploaded_in_shift"` to `skipped_keywords` tuple at line 534.

## Impact
- False alarm: 70 machines flagged as "Lỗi script" when they correctly skipped due to idempotency
- Operators waste time investigating non-issues
- Actual upload errors (20 machines `upload_subprocess_nonzero`) buried in noise