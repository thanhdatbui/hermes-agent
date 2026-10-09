# Case 109: ATX Session Unavailable Recovery in Home Navigation (Before Swipe)

## Hiện tượng & Bối cảnh
- **Lỗi:** `ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset artifact=...home\navigation`
- **Hiện trường:** TikTok vẫn đang mở ở Profile root (`nikoadamopou16`) sau khi hoàn thành profile preflight, thanh điều hướng đáy hiển thị rõ: "Trang chủ", "Cửa hàng", "+", "Hộp thư", "Hồ sơ" (đang active).
- **Mẫu máy gặp lỗi:** Máy 23 (serial `ce0117113acfd47e0c`, nick `nikoadamopou16`).

## Anti-Pattern Cần Tránh
1. **Bỏ sót cơ chế phục hồi ATX tại bước `home_navigation`:**
   Sau khi hoàn tất profile preflight, `_feed_session_flow` thực hiện điều hướng về Trang chủ trước khi lướt feed (`home_navigation = tap_navigation_target(ctx, _home_target(), ...)`). Case 108 chỉ mới áp dụng cơ chế phục hồi 2 tầng cho `_navigate_profile_for_preflight`, trong khi `home_navigation` hoàn toàn thiếu cơ chế này.
2. **`_maybe_recover_navigation_from_add_phone` không xử lý ATX failure:**
   Hàm recovery trung gian chỉ xử lý các popup thông thường (Add Phone, Quick Security, Verify Email) hoặc launcher focus loss, nuốt/trả về nguyên trạng `home_navigation` khi gặp `UIDumpError` / `ATX_SESSION_UNAVAILABLE`. Flow sau đó ghi nhận thất bại và cleanup kết thúc phiên oan uổng.

## Quy Trình Phục Hồi Chuẩn (Case 109 Fix)
1. **Tự động phục hồi ATX 2 tầng tại bước `home_navigation`:**
   - Ngay sau lời gọi `home_navigation` và `_maybe_recover_navigation_from_add_phone`:
   - Nếu `not home_navigation.ok`:
     - Kiểm tra `get_focused_activity(ctx)`.
     - Nếu package vẫn thuộc TikTok (`tiktok_pkgs`) và lỗi là `is_atx_failure` (`ATX_SESSION_UNAVAILABLE`, `UI_DUMP_FAILED`, `uidumperror`, `ui capture failed`):
       - Log action: `home_navigation_atx_recovery` với result `retry`.
       - Bọc `reset_atx_agent(ctx.adb, timeout=15)` trong `try...except` (ghi log warning `home_navigation_atx_reset_failed` nếu reset gặp lỗi).
       - `time.sleep(1.0)` cho socket bind lại.
       - Thử lại `home_navigation = tap_navigation_target(ctx, _home_target(), ...)` một lần nữa trước khi kết luận thất bại.
2. **Bảo toàn luồng error handling tiếp theo:**
   - Nếu sau retry `home_navigation` vẫn thất bại: append failure row và finalize cleanup bình thường, bảo toàn tính fail-closed.

## Pitfall Unit Test Mocking
- Khi viết unit test cho helper khôi phục `home_navigation`, nếu import hàm trực tiếp (`from flows.calibrate_screens import tap_navigation_target`), `patch("flows.calibrate_screens.tap_navigation_target")` sẽ không đè lên tham chiếu cục bộ đã bind. Bắt buộc gọi qua module attribute (`import flows.calibrate_screens as cs; cs.tap_navigation_target(...)`).
- Chạy unit test kiểm chứng:
  ```bash
  PYTHONPATH="D:\Taadaa\automation-core\src;D:\Taadaa\tiktok-luot nuoi acc\python_runner;D:\Taadaa\tiktok-luot nuoi acc\python_runner\tests" python -m unittest python_runner/tests/test_navigation_atx_recovery.py python_runner/tests/test_calibrate_screens.py
  ```
