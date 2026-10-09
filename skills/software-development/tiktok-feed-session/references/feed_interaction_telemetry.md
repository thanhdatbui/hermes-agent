# Telemetry & Interaction Gates in Feed Session

## Watch Dwell Gate for Follow Interactions
- **Mục tiêu:** Chống nhả follow và tránh server TikTok revert do bấm tap quá sớm sau khi xuất hiện video.
- **Quy tắc thời gian:** Ngâm video tối thiểu 8.0 - 12.0s trước khi tap follow (`round(random.uniform(8.0, 12.0), 2)`).
- **Telemetry Requirement:** 
  - Toàn bộ các log sự kiện sau khi qua dwell gate (cho dù `skipped`, `fail`, hay `success`) BẮT BUỘC phải đính kèm telemetry `watch_dwell_seconds` trong dictionary `extra`.
  - Log events:
    - Button not found: `extra={"follow_rate_percent": ..., "watch_dwell_seconds": watch_dwell_s}`
    - Tap failed: `extra={"watch_dwell_seconds": watch_dwell_s}`
    - Follow success: `extra={"swipe_count": ..., "follow_rate_percent": ..., "watch_dwell_seconds": watch_dwell_s}`

## Feed Rates & Distribution Baseline
- **Distribution:** FYP 70%, Following 15%, Friends 15%.
- **Like Rates:** FYP 15% (soft 12-16%), Following 35% (soft 25-40%), Friends 45% (soft 35-50%).
- **Deep Like Rate:** 48%.
- **Test Suite Verification:** `tests/test_feed_like_rates.py` kiểm định các hằng số này và các luồng telemetry tương ứng.
