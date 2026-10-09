# Case 109: ATX Session Unavailable Trong Home Navigation (Before Swipe) & Cơ Chế Phục Hồi Toàn Diện (05/09/2026, Sự Cố Máy 23)

## 1. Hiện Tượng & Triệu Chứng Lỗi
- **Thiết bị:** Máy 23 | Serial: `ce0117113acfd47e0c` | Nick: `nikoadamopou16` (Row 5, Ca chiều 05/09/2026).
- **Quy trình:** Feed Session Smoke (`multi-machine-feed-session` / `feed-session-smoke` trong repo `tiktok-luot nuoi acc`).
- **Triệu chứng báo cáo:** Dừng phiên tại `feed-session-smoke/home/navigation` với error:
  `ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset artifact=.../feed-session-smoke/home/navigation`.
- **Hiện trường thực tế khi inspect:** TikTok đang mở bình thường ở màn hình Hồ sơ (Profile root của nikoadamopou16) sau khi hoàn tất preflight. Thanh điều hướng đáy hiển thị rõ: "Trang chủ", "Cửa hàng", "+", "Hộp thư" (badge 16), "Hồ sơ" (đang active). Quá trình đọc UI XML để điều hướng về Trang chủ trước khi lướt feed bị đứt quãng do socket ATX tạm thời mất kết nối hoặc stub bị crash ngầm.

---

## 2. Nguyên Nhân Cốt Lõi
- Trong `python_runner/flows/feed_swipe_smoke.py`, sau khi hoàn tất kiểm tra hồ sơ (`profile_preflight`), flow thực hiện điều hướng về Trang chủ trước khi bắt đầu lướt feed:
  ```python
  home_navigation = tap_navigation_target(
      ctx,
      _home_target(),
      current_top_tab=current_top_tab,
      artifact_prefix=artifact_prefix,
      log_prefix=artifact_prefix,
  )
  home_navigation = _maybe_recover_navigation_from_add_phone(...)
  ```
- **Lỗ hổng phân mảnh sau Case 108**:
  - Case 108 (commit `33f5091`) đã bổ sung cơ chế phục hồi 2 tầng cho `_navigate_profile_for_preflight` (gọi `reset_atx_agent` và retry `tap_navigation_target` khi TikTok foreground).
  - Tuy nhiên, bước điều hướng về Trang chủ (`home_navigation`) ngay sau đó lại CHƯA ĐƯỢC áp dụng cơ chế phục hồi này.
  - Hàm `_maybe_recover_navigation_from_add_phone` chỉ xử lý các popup như Add Phone, Quick Security, Verify Email, hoặc launcher focus loss, hoàn toàn bỏ qua lỗi `ATX_SESSION_UNAVAILABLE` / `UIDumpError`.
  - Hệ quả: Khi ATX session bị lỗi tạm thời tại bước `home_navigation`, flow lập tức ghi nhận thất bại và kết thúc phiên (`finalize_feed_session_cleanup`) dẫn đến dừng phiên oan uổng dù TikTok vẫn đang ở foreground.

---

## 3. Quy Tắc Khắc Phục Chuẩn (Standard Fix Pattern)

1. **Phục Hồi ATX 2 Tầng Tại Bước `home_navigation` Trong `feed_swipe_smoke.py`:**
   - Sau khi gọi `tap_navigation_target` và `_maybe_recover_navigation_from_add_phone`, nếu `home_navigation.ok` vẫn là `False`:
     * Kiểm tra foreground focus qua `get_focused_activity(ctx)`.
     * Nếu package vẫn thuộc TikTok (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`) và mã lỗi/lý do là ATX failure (`ATX_SESSION_UNAVAILABLE`, `UI_DUMP_FAILED`, `uidumperror`, `ui capture failed`):
       - Log action: `home_navigation_atx_recovery` với result `retry`.
       - Kích hoạt `reset_atx_agent(ctx.adb, timeout=15)` và sleep 1.0s để socket bind lại.
       - Thử lại `tap_navigation_target(ctx, _home_target(), ...)` một lần nữa trước khi kết luận thất bại.

2. **Nguyên Tắc Bất Biến (Invariant)**:
   - MỌI điểm chuyển tiếp điều hướng chính giữa các tab (Home -> Profile, Profile -> Home, Home -> Friends/Following/For You) đều phải có cơ chế bọc phục hồi ATX session 2 tầng nếu TikTok vẫn giữ foreground.
   - Không được để lỗi socket tạm thời của daemon ATX làm sập toàn bộ flow feed session của máy farm.

---

## 4. Kiểm Thử Độc Lập & Pitfall Mocking Module Attribute Trong Unit Test
- **Lệnh chạy unit test:**
  ```bash
  PYTHONPATH="D:\Taadaa\automation-core\src;D:\Taadaa\tiktok-luot nuoi acc\python_runner" python -m unittest python_runner/tests/test_navigation_atx_recovery.py
  ```
- **Pitfall Mocking Module-Level Import**:
  - Khi viết test khôi phục ATX cho `home_navigation`, nếu hàm gọi `get_focused_activity` và `tap_navigation_target` được import trực tiếp dạng `from flows.calibrate_screens import get_focused_activity, tap_navigation_target`, việc dùng `patch("flows.calibrate_screens.tap_navigation_target", return_value=...)` sẽ không đè lên tham chiếu đã bind tại namespace của file test.
  - Giải pháp chuẩn: Import module `import flows.calibrate_screens as cs` và gọi `cs.get_focused_activity(ctx)`, `cs.tap_navigation_target(...)`. Nhờ đó `patch("flows.calibrate_screens...")` sẽ mock chính xác các method tại runtime.
- **Xử lý Exception khi Reset**:
  - `reset_atx_agent` phải được bọc trong `try...except Exception as reset_err:` ghi log `action="home_navigation_atx_reset_failed"`, `result="warning"` và vẫn tiếp tục retry tap navigation để không bị gián đoạn flow khi reset tạm thời lỗi.

