# Case 108: Tự Phục Hồi ATX Session Trong Navigation & Preflight Khi TikTok Ở Foreground (05/09/2026, Sự Cố Máy 76)

## 1. Hiện Tượng & Triệu Chứng Lỗi
- **Máy gặp lỗi:** Máy 76 | Serial: `9885b64d56305a3731` | Account: `ucloan7790` (Row 3).
- **Quy trình:** Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc` - `multi-machine-feed-session`).
- **Triệu chứng báo cáo:** Dừng phiên tại bước `profile/navigation` với lỗi:
  `ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset artifact=...profile\navigation` -> `manual-needed`.
- **Hiện trường thực tế khi inspect:**
  - TikTok vẫn đang mở ở foreground Home Feed (`com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`).
  - Daemon `atx-agent` và tiến trình stub `com.github.uiautomator` vẫn còn process (`ps -A` PID 321 / 32289).

---

## 2. Nguyên Nhân Cốt Lõi (2 Tầng Bẫy Logic)

### Tầng 1: Bẫy Bỏ Qua Recovery Khi Bắt UIDumpError Trong `tap_navigation_target`
- Tại `python_runner/flows/calibrate_screens.py::tap_navigation_target`:
  ```python
  try:
      xml_text = capture_required_ui(ctx.adb, ...)
  except UIDumpError as exc:
      navigation_error = exc
      ...
  ```
- Nhánh recovery phía dưới để xử lý popup hoặc thử lại navigation có điều kiện:
  ```python
  if point is None and navigation_error is None:
  ```
- Khi `capture_required_ui` ném `UIDumpError("ATX_SESSION_UNAVAILABLE")` do kết nối socket JSON-RPC bị nghẽn tạm thời, biến `navigation_error` mang giá trị ngoại lệ (khác `None`).
- Hệ quả: Toàn bộ khối recovery phía dưới bị bỏ qua hoàn toàn. Hàm kết luận thất bại ngay lập tức mà không cho phép reset ATX session stub hay thử lại capture.

### Tầng 2: Preflight Thiếu Tầng Khôi Phục Khi TikTok Vẫn Ở Foreground
- Tại `python_runner/flows/feed_swipe_smoke.py::_navigate_profile_for_preflight`:
  - Khi `navigation.ok` trả về `False`, hàm chỉ kiểm tra nhánh `if is_launcher:` (được bổ sung từ Case 105 để relaunch khi văng ra ngoài Launcher).
  - Khi TikTok vẫn đang ở foreground Home Feed và lỗi xảy ra là `ATX_SESSION_UNAVAILABLE` / `UIDumpError`, hàm không kích hoạt reset hay retry mà fail thẳng, dẫn đến kết luận `manual-needed` và dừng phiên máy.

---

## 3. Quy Tắc Khắc Phục Chuẩn (Standard 2-Layer Recovery Pattern)

### Tầng 1: In-flight Recovery Trong `tap_navigation_target`
Ngay trong khối `except UIDumpError as exc:`, nếu `get_focused_activity(ctx)` xác nhận app vẫn thuộc `tiktok_pkgs`:
1. Ghi log audit `action="navigation_atx_recovery"`, `result="retry"`.
2. Gọi `automation_core.persistent_ui.reset_atx_agent(ctx.adb, timeout=15)` để khởi động lại background stub qua control endpoint `POST /uiautomator` (tuyệt đối CẤM dùng `monkey -p com.github.uiautomator 1` vì sẽ làm xoay ngang màn hình và cướp foreground của TikTok).
3. `time.sleep(1.0)` để socket JSON-RPC bind ổn định.
4. Bounded recapture: Gọi lại `capture_required_ui` 1 lần với deadline cho phép.
5. Nếu thành công: phân tích XML, tìm node Profile và cập nhật `point`, `navigation_error = None`, `navigation_status = "pass"` để tiến hành tap mục tiêu.
6. Nếu recapture vẫn ném `UIDumpError`: bảo toàn nguyên vẹn exception gốc và tuân thủ Case 105 (TUYỆT ĐỐI KHÔNG gửi `KEYCODE_BACK` khi đang ở Home/Feed).

### Tầng 2: Flow Guard Trong `_navigate_profile_for_preflight`
Khi `not navigation.ok`, kiểm tra bổ sung:
```python
is_atx_failure = (
    nav_status_upper in {"ATX_SESSION_UNAVAILABLE", "UI_DUMP_FAILED"}
    or "atx_session_unavailable" in nav_reason_lower
    or "atx session" in nav_reason_lower
    or "uidumperror" in nav_reason_lower
    or "ui capture failed" in nav_reason_lower
)
if current_pkg in tiktok_pkgs and is_atx_failure:
    reset_atx_agent(ctx.adb, timeout=15)
    time.sleep(1.0)
    navigation = tap_navigation_target(ctx, _profile_target(), ...)
```
Đảm bảo nếu sự cố ATX xảy ra ở tầng sâu, tầng điều phối preflight vẫn có cơ hội giải phóng socket kẹt và hoàn tất điều hướng profile trước khi kết luận `manual-needed`.

---

## 4. Verification Evidence
- Unit tests: `python_runner/tests/test_navigation_atx_recovery.py` (6/6 passed trong 2.00s), `test_calibrate_screens.py` (40/40 passed trong 2.88s).
- Live Canary Máy 76: `multi-machine-feed-session` chạy qua 100% (5/5 swipes, exit code 0).
