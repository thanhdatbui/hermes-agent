# Watchdog Classification Fix (2026-09-13)

**Problem:** The `feed_session_watchdog.py` script was incorrectly classifying MANUAL_REVIEW outcomes with reason "không có video" (anchor lacking video) as `fl_error` (script errors). These should be `fl_skipped` (safe-skip) per farm rules: when an anchor has no video, the Mode 2 follow runner safely skips to the next anchor.

**Root Cause:** The classification logic at lines 837-842 only checked for `status == "SKIPPED"` or success/failure patterns, but never checked for the `MANUAL_REVIEW` status with the "no video" reason substring.

**Fix Applied:** Added two lines (838-839) in `feed_session_watchdog.py`:

```python
elif status == "MANUAL_REVIEW" and "không có video" in (fd.get("reason", "") or "").lower():
    fl_skipped.append(m)  # anchor thiếu video = safe-skip, KHÔNG phai loi
```

**Before Fix:**
- 20 machines with anchor missing video → classified as "Lỗi script/xác minh" (34 total follow errors)
- Follow error count: 34
- Follow skip count: 40

**After Fix:**
- 20 machines with anchor missing video → correctly classified as "Bỏ qua" (safe-skip)
- 11 machines with real errors (Account Switcher failed, UI crash) → remain as "Lỗi script/xác minh"
- Follow error count: 14 (down from 34)
- Follow skip count: 60 (up from 40)

**Affected Machines (20 machines with anchor missing video):**
M6, M7, M9, M12, M15, M16, M17, M18, M19, M25, M29, M31, M36, M37, M42, M44, M47, M51, M54, M55

**Verification:**
- Unit tests `test_feed_session_watchdog.py`: 4/4 pass
- Data replay Ca 4: 20 Success, 15 Fail, 45 Trống slot; 57 tim / 391 video (14.6%)
- Focused pytest pass 100%
- Reviewer 9Router :20129 model review: VERDICT: APPROVED