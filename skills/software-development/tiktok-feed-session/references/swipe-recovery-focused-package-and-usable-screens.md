# Swipe Recovery Stuck on 3rd Party App / Focus Loss Contract (2026-08-24)

## Hiện tượng & Sự cố (Máy 46)
- **Script:** `multi-machine-feed-session`
- **Tài khoản:** `trieutruc0505`
- **Lý do dừng:** `swipe recovery passed stuck screen`
- **Ảnh hiện trường:** Ứng dụng Danh bạ / Điện thoại (`com.samsung.android.contacts` / `com.android.dialer`) xuất hiện trên màn hình thay vì TikTok feed.

## Phân tích Call Chain & Root Cause
1. **Lỗi logic trong `_swipe_recovery_on_stuck()`:**
   - Trước khi sửa, hàm `_swipe_recovery_on_stuck()` thực hiện vuốt 2 lần để cứu kẹt. Sau khi vuốt và chụp lại attempt, code kiểm tra điều kiện hồi phục bằng cách loại trừ blacklist:
     ```python
     if detected and detected not in {
         "manual-needed:login",
         "manual-needed:verification",
         "manual-needed:captcha",
         "manual-needed:security",
         "manual-needed:manual_challenge",
         "unknown",
     }:
         row["status"] = ExitStatus.SUCCESS.value
         row["safety_reason"] = "swipe recovery passed stuck screen"
     ```
   - Khi app thứ 3 (như Danh bạ, Dialer, Cài đặt) chiếm màn hình, nếu classifier trả về một mã màn hình không nằm trong blacklist (hoặc `manual-needed:popup`), `_swipe_recovery_on_stuck` nhận nhầm là đã vượt qua kẹt thành công và gán `safety_status = "ok"`, `safety_reason = "swipe recovery passed stuck screen"`.
   - Khi row trả về tiếp tục đi qua các chốt kiểm tra tiếp theo (`ManualReasonGuard` hoặc `safety_check`), việc mất focus TikTok khiến session dừng lại với lý do dừng là `swipe recovery passed stuck screen`.

## Quy tắc bắt buộc (Fail-Closed Contract)
1. **Whitelist thay vì Blacklist:**
   - Chỉ công nhận hồi phục sau swipe recovery khi `detected` thuộc whitelist các màn hình TikTok hợp lệ:
     `usable_screens = {*FEED_TYPES, "home", "profile"}`
2. **Kiểm tra Focused Package:**
   - Bắt buộc kiểm tra `focused_pkg == expected_package` (`com.ss.android.ugc.trill`). Nếu focus đang thuộc app thứ 3 hoặc SystemUI, tuyệt đối không được đánh dấu là `SUCCESS`.
3. **Regression Tests:**
   - Suite `test_feed_swipe_smoke_popups.py::SwipeRecoveryOnStuckTests` phải kiểm thử cả 2 nhánh:
     - Nhánh hợp lệ: `detected in usable_screens` và `focused_package == tiktok_package` -> `status == "success"`.
     - Nhánh app ngoài (Dialer/Contacts): `focused_package != tiktok_package` -> `res is None` (fail-closed).
