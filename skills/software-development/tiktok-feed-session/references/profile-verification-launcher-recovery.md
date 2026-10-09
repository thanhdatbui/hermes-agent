# Profile Verification & Launcher Recovery Pitfall

## Triệu chứng & Chữ ký lỗi
- `profile verification navigation-failed: navigation target profile not found in XML`
- Báo cáo Batch Aggregator cảnh báo `[P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]`.

## Nguyên nhân gốc (Root Cause)
1. Trong quá trình nuôi feed hoặc sau chuỗi tương tác, ứng dụng TikTok có thể bị OS kill ngầm hoặc crash văng về màn hình Home/Launcher (`com.sec.android.app.launcher`).
2. Khi quy trình chuyển sang bước `_verify_profile`, lệnh `tap_navigation_target(ctx, CalibrationTarget("profile", ...))` cố dump UI XML nhưng không tìm thấy tab `Hồ sơ` / `Profile` (vì màn hình hiện tại là Launcher, không phải TikTok).
3. `tap_navigation_target` trả về `status="not-found"` với `reason="navigation target profile not found in XML"`.
4. Nếu logic xử lý tại `_verify_profile` chỉ kiểm tra cờ launcher qua thuộc tính focus đã lưu hoặc thiếu nhánh bẫy `is_target_not_found` / kiểm tra actual focus trực tiếp từ thiết bị, quy trình sẽ không kích hoạt relaunch TikTok recovery mà trả về ngay `profile_verify_status = "navigation-failed"`, dẫn đến flow bị kết luận `MANUAL_NEEDED` và kích hoạt báo động văng nick giả tạo.

## Cách xử lý chuẩn (Patch Contract Pattern)
- Kiểm tra actual focus trên thiết bị bằng `get_focused_activity(ctx)`.
- Nhận diện cả 2 trường hợp:
  1. `is_launcher`: Gói đang active thuộc launcher hoặc không thuộc TikTok packages (`actual_pkg not in tiktok_pkgs`).
  2. `is_target_not_found`: `not found in xml` hoặc `target not found` hoặc `status == "not-found"`.
- Mở rộng điều kiện bẫy trong `_verify_profile_after_session`:
  ```python
  if is_launcher or is_target_not_found:
      relaunch_ok, focus, relaunch_err = _relaunch_and_poll_tiktok_focus(
          ctx,
          after_launch_delay_seconds=POST_SWIPE_LAUNCHER_RECOVERY_WAIT_SECONDS,
      )
  ```
- Kích hoạt `_relaunch_and_poll_tiktok_focus` để đưa TikTok trở lại foreground, kiểm tra màn hình nhạy cảm/checkpoint, sau đó retry tap tab profile.
- Tên hàm chuẩn xác khi viết unit test: `_verify_profile_after_session(ctx, artifact_prefix=...)` (không phải `_verify_profile`).

