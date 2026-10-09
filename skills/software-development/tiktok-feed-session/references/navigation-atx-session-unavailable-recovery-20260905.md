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

### Tầng 1: Bẫy Boolean Logic `navigation_error is None` Trong `tap_navigation_target`
- Tại `python_runner/flows/calibrate_screens.py::tap_navigation_target`:
  ```python
  try:
      xml_text = capture_required_ui(ctx.adb, ...)
      ...
  except UIDumpError as exc:
      navigation_error = exc
      navigation_status = exc.code
      navigation_reason = str(exc)
  ```
- Nhánh phục hồi downstream sử dụng điều kiện:
  ```python
  if point is None and navigation_error is None:
      # Thực hiện back recovery, popup dismissal, retry...
  ```
- **Hậu quả:** Khi capture UI ném `UIDumpError` (ví dụ `ATX_SESSION_UNAVAILABLE`), `navigation_error` mang giá trị ngoại lệ khác `None` $\rightarrow$ điều kiện `navigation_error is None` trả về `False`.
- Toàn bộ khối phục hồi bị bỏ qua; hàm không hề thử khôi phục lại ATX agent/stub dù TikTok vẫn đang ở foreground, trả về kết quả thất bại ngay lập tức.

### Tầng 2: Thiếu Phục Hồi ATX Trong `_navigate_profile_for_preflight` & `home_navigation` (Before Swipe)
- Tại `python_runner/flows/feed_swipe_smoke.py::_navigate_profile_for_preflight` (Case 108):
  - Khi `navigation.ok` trả về `False`, flow chỉ kiểm tra cờ `is_launcher` (ứng dụng bị văng ra launcher).
  - Vì TikTok vẫn đang mở ở foreground (`com.ss.android.ugc.trill`), `is_launcher` là `False`.
  - Flow không kiểm tra xem nguyên nhân thất bại có phải do lỗi dump UI (`ATX_SESSION_UNAVAILABLE` / `UIDumpError`), không gọi `reset_atx_agent()`, mà trả về kết quả lỗi ngay lập tức $\rightarrow$ dừng phiên và đánh dấu `manual-needed` oan uổng.
- Tại `python_runner/flows/feed_swipe_smoke.py::_feed_session_flow` bước `home_navigation` trước khi swipe (Case 109, Sự Cố Máy 23 - Nick `nikoadamopou16`):
  - Sau khi preflight profile xong, flow gọi `tap_navigation_target(ctx, _home_target(), ...)` để về Trang chủ trước khi swipe feed.
  - Sau bước này, flow chỉ gọi `_maybe_recover_navigation_from_add_phone`, hoàn toàn không kiểm tra `is_atx_failure` khi TikTok vẫn ở foreground.
  - Khi stub/socket ATX chập chờn, phiên bị dừng oan uổng tại `feed-session-smoke\home\navigation`.
  - **Khắc phục (Case 109):** Bổ sung kiểm tra `is_atx_failure`. Nếu `current_pkg in tiktok_pkgs and is_atx_failure`, tự động ghi action log `home_navigation_atx_recovery`, gọi `reset_atx_agent(ctx.adb, timeout=15)`, sleep 1.0s và retry `tap_navigation_target(_home_target())`. Bổ sung 3 unit tests cho `home_navigation` trong `test_navigation_atx_recovery.py`.

---

## 3. Giải Pháp Chuẩn Hóa (2 Tầng Phục Hồi)

### Tầng 1: Phục hồi ATX Session Trực Tiếp Trong `tap_navigation_target`
1. Khi `capture_required_ui` ném `UIDumpError`:
   - Lấy focus thực tế qua `get_focused_activity(ctx)`.
   - Nếu `focus_pkg` vẫn thuộc các package của TikTok (`tiktok_pkgs`):
     - Ghi nhận action log `navigation_atx_recovery` với result `retry`.
     - Gọi `reset_atx_agent(ctx.adb, timeout=15)` để khởi động lại daemon và background stub.
     - Cho sleep 1.0s để socket JSON-RPC bind hoàn chỉnh.
     - Thực hiện recapture XML bằng `capture_required_ui` với timeout tối thiểu 15s.
     - Nếu recapture thành công: xóa `navigation_error = None` và tìm lại target element. Nếu tìm thấy, lấy tọa độ tâm để tiếp tục click điều hướng.
2. **Bảo tồn Hard Invariant Case 105:** Tuyệt đối không bấm phím BACK (`KEYCODE_BACK`) nếu màn hình đang ở Home/Feed (`for-you`, `following`, `friends`, `home`) để tránh làm văng ứng dụng ra Samsung Launcher.

### Tầng 2: Phục hồi ATX Tại Preflight Trong `_navigate_profile_for_preflight`
- Khi `navigation.ok` là `False`, kiểm tra nếu `actual_pkg in tiktok_pkgs`:
  - Kiểm tra lý do lỗi `nav_reason_lower` chứa `"atx_session_unavailable"` hoặc `"uidumperror"`.
  - Ghi nhận action log `profile_preflight_atx_recovery`.
  - Gọi `reset_atx_agent(ctx.adb, timeout=15)` và sleep 1.0s.
  - Thử gọi lại `tap_navigation_target` lần 2 trước khi chấp nhận kết luận thất bại.

---

## 4. Kiểm Thử & Verification Suite
- Unit test suite: `python_runner/tests/test_navigation_atx_recovery.py` (6/6 tests passed 100%):
  1. `test_tap_navigation_target_recovers_from_atx_session_unavailable`: Mock lần 1 ném `UIDumpError`, lần 2 recapture thành công $\rightarrow$ navigation thành công.
  2. `test_tap_navigation_target_preserves_error_when_atx_recovery_fails`: Khi recapture sau reset vẫn lỗi, bảo toàn nguyên vẹn mã lỗi `ATX_SESSION_UNAVAILABLE`.
  3. `test_tap_navigation_target_skips_atx_recovery_when_not_tiktok_focus`: Khi app đã văng Launcher, bỏ qua recovery ATX và không gọi `reset_atx_agent` mù quáng.
  4. `test_tap_navigation_target_atx_recovery_preserves_case_105_back_guard_at_home_feed`: Xác nhận guard không gửi phím BACK khi ở Home/Feed vẫn hoạt động chuẩn xác.
  5. `test_navigate_profile_for_preflight_recovers_from_atx_session_unavailable`: Tầng 2 preflight tự động reset ATX và retry thành công.
  6. `test_navigate_profile_for_preflight_fails_when_atx_recovery_retry_still_fails`: Preflight fail an toàn khi cả 2 lần tap đều lỗi.
- Lệnh chạy test:
  ```bash
  PYTHONPATH="D:\Taadaa\tiktok-luot nuoi acc\python_runner;D:\Taadaa\automation-core\src" /d/Taadaa/python-envs/automation/Scripts/python.exe -m pytest "D:\Taadaa\tiktok-luot nuoi acc\python_runner\tests\test_navigation_atx_recovery.py" -v
  ```

---

## 5. Pitfalls & Unit Test Mocking Trap

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
