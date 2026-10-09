# Phục Hồi ATX_SESSION_UNAVAILABLE Trong Profile Navigation & Retry Khi TikTok Foreground (Case 108, 2026-09-05, Máy 76)

## 1. Hiện Tượng & Ngữ Cảnh Sự Cố (Máy 76 - Serial `9885b64d56305a3731`)
- Phiên chạy `feed-session-smoke` bị dừng ở bước `profile_preflight` với lỗi:
  `ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset artifact=.../feed-session-smoke/profile/navigation`
- **Hiện trường thực tế trên thiết bị**:
  - TikTok vẫn đang mở ở foreground Home Feed (`com.ss.android.ugc.trill` / `.SplashActivity`).
  - Cả tiến trình `atx-agent` và `com.github.uiautomator` (stub) vẫn đang chạy nền (`ps -A` thấy PID 321 / 32289).
  - Không có hiện tượng văng Launcher hay crash app.

## 2. Root Cause
1. **Thiếu cơ chế phục hồi khi dính UIDumpError trong `tap_navigation_target` (`calibrate_screens.py`)**:
   - `capture_required_ui` ném `UIDumpError("ATX_SESSION_UNAVAILABLE", ...)` do nghẽn socket JSON-RPC tạm thời trên máy Android 7 yếu.
   - Hàm bắt được exception và gán `navigation_error = exc`.
   - Vòng lặp recovery phía dưới có guard `if point is None and navigation_error is None:` (từ Case 105 để tránh mask lỗi). Vì `navigation_error is not None`, flow bỏ qua mọi cơ chế phục hồi và trả về `NavigationResult(False, "ATX_SESSION_UNAVAILABLE", ...)` ngay lập tức.
2. **Thiếu nhánh phục hồi khi TikTok vẫn ở Foreground trong `_navigate_profile_for_preflight` (`feed_swipe_smoke.py`)**:
   - Khối xử lý lỗi sau khi `navigation.ok == False` chỉ kiểm tra `if is_launcher:` (để tự động relaunch TikTok khi app bị văng ra launcher).
   - Nếu TikTok vẫn ở foreground (Home Feed / splash) và lỗi là `ATX_SESSION_UNAVAILABLE`, flow không có cơ chế `reset_atx_agent` và không retry tap navigation, dẫn đến fail-closed `manual-needed` oan uổng.

## 3. Quy Tắc & Invariant Bắt Buộc
- **Tuân thủ Case 105**: Tuyệt đối CẤM gửi `input keyevent 4` (KEYCODE_BACK) khi đang ở Home/Feed vì phím BACK tại Home Feed sẽ làm TikTok đóng và văng ra Samsung Launcher.
- **2 Tầng Phòng Thủ (Defense in Depth)**:
  1. **Tầng Low-level (`tap_navigation_target`)**: Khi `capture_required_ui` ném `UIDumpError`, kiểm tra `get_focused_activity(ctx)`. Nếu thuộc `tiktok_pkgs`:
     - Ghi log `action="navigation_atx_recovery"`, `result="retry"`.
     - Gọi `automation_core.persistent_ui.reset_atx_agent(ctx.adb, timeout=15)` (dùng control endpoint `POST /uiautomator`, CẤM `monkey`).
     - Sleep 1.0s chờ JSON-RPC bind.
     - Capture lại XML qua `capture_required_ui(timeout=60)`. Nếu thành công, tìm node Profile và hoàn tất tap.
     - Nếu retry vẫn lỗi, bảo toàn nguyên vẹn exception `UIDumpError` gốc.
  2. **Tầng Flow-level (`_navigate_profile_for_preflight`)**: Khi `navigation.ok == False`:
     - Nếu `is_launcher`: relaunch TikTok + retry.
     - Nếu `current_pkg in tiktok_pkgs` và lỗi là ATX failure (`ATX_SESSION_UNAVAILABLE`, `UI_DUMP_FAILED`, v.v.):
       - Gọi `reset_atx_agent(ctx.adb, timeout=15)`.
       - Sleep 1.0s.
       - Retry `tap_navigation_target` 1 lần an toàn.
- **Bounded Timeout**: Tất cả thao tác reset và retry capture đều giới hạn deadline chặt chẽ, không bao giờ retry vô hạn.
