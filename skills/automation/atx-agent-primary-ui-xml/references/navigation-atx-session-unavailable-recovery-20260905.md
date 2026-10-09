# Case 108: ATX Session Unavailable Trong Navigation Recovery & Bẫy Logic `navigation_error is None` (05/09/2026, Sự Cố Máy 76 & Máy 80)

## 1. Hiện Tượng & Triệu Chứng Lỗi
- **Thiết bị:** 
  - Máy 80 | Serial: `ce061606cd45950405` | Nick: `chrysiigvz6` (Row 3, Ca chiều 05/09/2026).
  - Máy 76 | Serial: `9885b64d56305a3731` | Nick: `ucloan7790` (Row 3, Ca trưa 05/09/2026).
- **Quy trình:** Feed Session Smoke (`multi-machine-feed-session` / `feed-session-smoke` trong repo `tiktok-luot nuoi acc`).
- **Triệu chứng báo cáo:** Dừng phiên tại `feed-session-smoke/profile/navigation` với error:
  `ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset artifact=.../feed-session-smoke/profile/navigation`.
- **Hiện trường thực tế khi inspect:** TikTok đang mở bình thường ở màn hình For You (Home Feed), `SplashActivity` / Feed đang ở foreground (`com.ss.android.ugc.trill`). Quá trình đọc UI XML bị đứt quãng do socket ATX tạm thời mất kết nối hoặc stub bị crash ngầm.

---

## 2. Nguyên Nhân Cốt Lõi (2 Tầng Lỗi)

### Tầng 1: Bẫy Logic `navigation_error is None` Chặn Hoàn Toàn Nhánh Recovery Trong `tap_navigation_target`
- Trong `tap_navigation_target` (`python_runner/flows/calibrate_screens.py`):
  ```python
  try:
      xml_text = capture_required_ui(ctx.adb, ...)
      ...
  except UIDumpError as exc:
      navigation_error = exc
      navigation_status = exc.code
      navigation_reason = str(exc)
  ```
- Đến nhánh phục hồi phía dưới:
  ```python
  if point is None and navigation_error is None:
      ...
  ```
- Vì `navigation_error` mang giá trị ngoại lệ `UIDumpError`, điều kiện `navigation_error is None` bị **False**.
- Hệ quả: Toàn bộ khối xử lý sau đó (kiểm tra focus, retry, recovery) bị bỏ qua hoàn toàn. Hàm trả về `NavigationResult(False, "ATX_SESSION_UNAVAILABLE", ...)` ngay lập tức mà không hề có cơ hội khắc phục sự cố kết nối ATX tạm thời.

### Tầng 2: Thiếu Cơ Chế Reset ATX & Retry Trong `_navigate_profile_for_preflight` Khi TikTok Vẫn Ở Foreground
- Tại `flows/feed_swipe_smoke.py::_navigate_profile_for_preflight`:
  - Khi `navigation.ok` là `False`, flow chỉ kiểm tra cờ `is_launcher`. Nếu văng Launcher thì relaunch TikTok.
  - Tuy nhiên, trong trường hợp Máy 76 và Máy 80, TikTok vẫn ở foreground Trang chủ (`SplashActivity` / Feed) nên `is_launcher` là `False`.
  - Flow không kiểm tra xem thất bại là do lỗi dump UI (`UIDumpError` / `ATX_SESSION_UNAVAILABLE`), không gọi `reset_atx_agent()`, mà lập tức return `navigation` thất bại -> kích hoạt stop flow `manual-needed` một cách oan uổng.

---

## 3. Quy Tắc Khắc Phục Chuẩn (Standard Fix Pattern)

1. **Tách Biệt Lỗi Dump UI Với Logic Target Not-Found Trong `tap_navigation_target`:**
   - Khi `capture_required_ui` ném `UIDumpError`, không nên để nó short-circuit toàn bộ luồng recovery.
   - Nếu lỗi xảy ra và `point is None`, kiểm tra focus thiết bị: nếu TikTok vẫn đang ở foreground, thực hiện gọi `reset_atx_agent(ctx.adb, timeout=15)` một lần để khôi phục stub và thử lại `capture_required_ui` với bounded timeout.
   - Bảo đảm tuân thủ Case 105: CẤM gửi `KEYCODE_BACK` khi màn hình đang ở Home/Feed để tránh làm app văng ra Launcher.

2. **Cơ Chế Phục Hồi ATX Trong `_navigate_profile_for_preflight`:**
   - Khi `navigation.ok` thất bại nhưng focus thực tế vẫn là TikTok (`actual_pkg in tiktok_pkgs`), kiểm tra nếu `nav_reason_lower` chứa `"atx_session_unavailable"` hoặc `"uidumperror"`:
     * Kích hoạt `reset_atx_agent(ctx.adb, timeout=15)`.
     * Cho sleep ngắn 1.0s để bind socket JSON-RPC.
     * Thử lại `tap_navigation_target` một lần nữa trước khi kết luận thất bại.

---

## 4. Pitfalls & Unit Test Mocking Trap

### Bẫy Mocking `get_focused_activity` Khi Test Bỏ Qua ATX Recovery (`test_tap_navigation_target_skips_atx_recovery_when_not_tiktok_focus`)
- Trong `tap_navigation_target`, hàm gọi `get_focused_activity` tại nhiều thời điểm:
  1. **Entry Safety Check (đầu hàm)**: Kiểm tra nếu app không thuộc `tiktok_pkgs` (ví dụ Launcher) thì abort ngay lập tức với `status = "fail"` (reason: `dismiss_overlay_aborted_due_to_non_tiktok_focus`), không bao giờ chạy đến `capture_required_ui`.
  2. **UIDumpError Recovery Check (trong khối `except UIDumpError`)**: Khi `capture_required_ui` ném `UIDumpError("ATX_SESSION_UNAVAILABLE")`, hàm kiểm tra focus lần 2. Nếu là TikTok thì gọi `reset_atx_agent`, còn nếu là Launcher/non-TikTok thì bỏ qua reset và bảo toàn `status = "ATX_SESSION_UNAVAILABLE"`.
- **Bẫy**: Nếu mock `get_focused_activity` bằng một giá trị tĩnh:
  ```python
  # ❌ SAI LẦM: Làm abort ngay tại Entry check
  return_value={"package": "com.sec.android.app.launcher", "activity": ".Launcher"}
  ```
  Test sẽ fail với lỗi: `AssertionError: 'fail' != 'ATX_SESSION_UNAVAILABLE'`.
- **Cách viết chuẩn**: Bắt buộc dùng `side_effect` 2 lần gọi:
  ```python
  # ✅ CHUẨN: Lần 1 pass entry check, lần 2 kiểm tra skip recovery trong except UIDumpError
  patch(
      "flows.calibrate_screens.get_focused_activity",
      side_effect=[
          {"package": "com.ss.android.ugc.trill", "activity": ".MainActivity"},
          {"package": "com.sec.android.app.launcher", "activity": ".Launcher"},
      ],
  )
  ```
