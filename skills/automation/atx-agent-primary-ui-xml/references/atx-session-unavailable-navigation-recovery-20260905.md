# Case 108: Phục Hồi ATX_SESSION_UNAVAILABLE Trong Profile Navigation Khi TikTok Ở Foreground (05/09/2026, Sự Cố Máy 76)

## 1. Hiện Tượng & Triệu Chứng Lỗi
- **Thiết bị gặp lỗi:** Máy 76 | Serial: `9885b64d56305a3731` | Nick: `ucloan7790` (Row 3).
- **Quy trình:** Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`).
- **Triệu chứng báo cáo:** Dừng phiên tại `feed-session-smoke/profile/navigation` với lỗi:
  `ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset artifact=...profile\navigation` -> `manual-needed`.
- **Hiện trường thực tế khi inspect:** TikTok vẫn đang mở ở foreground Home Feed (`com.ss.android.ugc.trill` / `.SplashActivity`). Daemon `atx-agent` (PID 32289) và stub `com.github.uiautomator` (PID 321) vẫn tồn tại trên thiết bị nhưng kết nối socket JSON-RPC bị treo hoặc nghẽn tạm thời.

---

## 2. Nguyên Nhân Cốt Lõi (2 Tầng Lỗi)

### Tầng 1: Bẫy Logic Recovery Trong `tap_navigation_target` Bỏ Qua UIDumpError
- Trong `python_runner/flows/calibrate_screens.py` hàm `tap_navigation_target`:
  - Khi `capture_required_ui` ném `UIDumpError("ATX_SESSION_UNAVAILABLE")`, exception được gán vào `navigation_error`.
  - Nhánh recovery phía sau được bảo vệ bởi:
    ```python
    if point is None and navigation_error is None:
    ```
  - Do `navigation_error` không phải là `None`, toàn bộ logic recovery (popup dismiss, back-key recovery) bị bỏ qua hoàn toàn. Hàm kết luận lỗi ngay lập tức mà không có cơ hội thử reset ATX agent hoặc recapture XML.

### Tầng 2: Preflight `_navigate_profile_for_preflight` Thiếu Nhánh Xử Lý Khi TikTok Vẫn Ở Foreground
- Trong `python_runner/flows/feed_swipe_smoke.py` hàm `_navigate_profile_for_preflight`:
  - Khi `not navigation.ok`, code cũ chỉ kiểm tra `if is_launcher:` (phục hồi khi TikTok văng về Launcher).
  - Khi TikTok vẫn ở foreground Home/Feed và lỗi là do sự cố tạm thời của ATX session dump (`UIDumpError`), hàm không kích hoạt cơ chế reset ATX và không thử lại navigation, dẫn đến fail thẳng và kết luận `manual-needed` dừng phiên máy.

---

## 3. Quy Tắc Khắc Phục Chuẩn 2 Tầng (Standard 2-Layer Recovery Pattern)

### Tầng 1: Tự Động Phục Hồi ATX Ngay Trong `tap_navigation_target`
1. **Kiểm tra Focus thực tế:** Khi bắt được `UIDumpError`, gọi `get_focused_activity(ctx)`. Nếu package thực tế vẫn thuộc `tiktok_pkgs`:
2. **Reset ATX stub an toàn:** Gọi `automation_core.persistent_ui.reset_atx_agent(ctx.adb, timeout=15)` (CẤM dùng monkey để không làm bung màn hình ngang tiếng Trung).
3. **Sleep bind socket:** Chờ `time.sleep(1.0)` để socket JSON-RPC bind hoàn tất.
4. **Recapture bounded:** Thử lại `capture_required_ui` 1 lần trong ngân sách deadline. Nếu thành công: phân tích XML, tìm node Profile và hoàn tất tap mục tiêu.
5. **Bảo toàn Case 105:** Nếu retry dump vẫn ném `UIDumpError`, cập nhật `navigation_error` sang lỗi mới, trả về đúng mã lỗi gốc (`ATX_SESSION_UNAVAILABLE`) và TUYỆT ĐỐI KHÔNG gửi `KEYCODE_BACK` khi đang ở Home/Feed.

### Tầng 2: Tầng Phòng Thủ Dự Phòng Tại `_navigate_profile_for_preflight`
- Khi `not navigation.ok`, bổ sung kiểm tra:
  ```python
  if current_pkg in tiktok_pkgs and is_atx_failure:
      reset_atx_agent(ctx.adb, timeout=15)
      time.sleep(1.0)
      navigation = tap_navigation_target(ctx, _profile_target(), ...)
  ```
- Nhận diện linh hoạt các biến thể lỗi: `ATX_SESSION_UNAVAILABLE`, `UI_DUMP_FAILED`, `"atx session"`, `"uidumperror"`, `"ui capture failed"`.

---

## 4. Verification Suite & Evidence
- Unit tests: `python_runner/tests/test_navigation_atx_recovery.py` (6/6 passed in 2.00s):
  - `test_tap_navigation_target_recovers_from_atx_session_unavailable`: kiểm chứng reset_atx_agent được gọi đúng 1 lần và tap trúng tọa độ Profile.
  - `test_tap_navigation_target_preserves_error_when_atx_recovery_fails`: kiểm chứng không gửi KEYCODE_BACK và bảo toàn lỗi gốc.
  - `test_tap_navigation_target_skips_atx_recovery_when_not_tiktok_focus`: không reset nếu mất focus ra Launcher.
  - `test_navigate_profile_for_preflight_recovers_from_atx_session_unavailable`: kiểm chứng tầng recovery thứ hai tại preflight.
- Live Canary: Máy 76 (serial `9885b64d56305a3731`) chạy `multi-machine-feed-session` thành công 100% (5/5 swipes, exit code 0).
