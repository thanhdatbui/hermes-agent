# Swipe Recovery on Stuck Screens — Third-Party App & Whitelist Guard (2026-08-24)

## Hiện tượng & Sự cố thực tế (Máy 46 - Ca ngày 24/08)
- **Script:** `multi-machine-feed-session` / `feed-session-smoke`.
- **Thông báo Farm Alert:** `🚨 [MÁY 46] DỪNG PHIÊN - Lý do: swipe recovery passed stuck screen` kèm ảnh chụp màn hình ứng dụng Danh bạ / Điện thoại (`com.samsung.android.contacts` / `GẦN ĐÂY` & `DANH BẠ`).
- **Trạng thái:** Phiên dừng khẩn cấp giữ hiện trường dù reason ghi "passed stuck screen".

## Root Cause Analysis
1. **Lỏng lẻo trong điều kiện thoát kẹt của `_swipe_recovery_on_stuck()`:**
   - Cơ chế `_swipe_recovery_on_stuck()` thực hiện vuốt thử 1-2 lần khi gặp popup/màn hình lạ không vượt qua được.
   - Sau khi vuốt và chụp lại attempt, code cũ kiểm tra điều kiện hồi phục bằng blacklist lỏng:
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
2. **Không kiểm tra `focused_package`:**
   - Khi TikTok bị văng hoặc bị đè bởi ứng dụng thứ 3 (như Danh bạ, Tin nhắn, Cài đặt), `detected_screen` có thể trả về chuỗi lạ không nằm trong blacklist trên (hoặc không được phân loại là unknown/login/captcha).
   - `_swipe_recovery_on_stuck()` vội vàng gán `status = "success"` và `safety_reason = "swipe recovery passed stuck screen"`.
   - Tuy nhiên khi row này chuyển tiếp qua `ManualReasonGuard` hoặc bước kiểm tra an toàn `_safety_from_row()`, hệ thống phát hiện `TikTok focus lost` hoặc mismatch package và dừng phiên, tạo ra alert mâu thuẫn: Dừng phiên nhưng lý do là "swipe recovery passed".

## Quy tắc bắt buộc (Enforced Contract)
1. **Dùng Whitelist thay vì Blacklist:**
   - Chỉ chấp nhận hồi phục thành công nếu `detected` thuộc tập các màn hình hữu ích và hợp lệ của TikTok: `{*FEED_TYPES, "home", "profile"}`.
2. **Bắt buộc kiểm tra `focused_package`:**
   - `focused_pkg = str(attempt.get("focus_package") or attempt.get("focused_package") or expected)`
   - Bắt buộc `focused_pkg == expected` (`com.ss.android.ugc.trill`). Nếu đang ở app ngoài hoặc system overlay, cấm đánh dấu `success` mà phải fail-closed để giữ hiện trường hoặc kích hoạt recovery focus phù hợp.
