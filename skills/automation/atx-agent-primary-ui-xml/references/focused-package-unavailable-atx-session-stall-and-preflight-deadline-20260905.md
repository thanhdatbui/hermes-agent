# Case 116: Khắc Phục Lỗi Stall 5 Phút Trong get_focused_activity, Settle Retry Pre-tap Navigation & Quá Deadline Preflight Switch Anchor (Sự Cố Máy 40)

- **Thời gian xử lý:** 05/09/2026
- **Vị trí áp dụng:** 
  - `python_runner/flows/observe.py` (`get_focused_activity`)
  - `python_runner/flows/calibrate_screens.py` (`tap_navigation_target`)
  - `python_runner/flows/feed_swipe_smoke.py` (`verify_and_switch_profile`, `_maybe_recover_navigation_from_add_phone`, `_navigate_profile_for_preflight`)
  - `python_runner/tests/test_navigation_focus_recovery.py`
  - `docs/farm-automation-cases.md`

## 1. Hiện tượng lỗi / Sự cố thực tế
- Farm Alert Máy 40 (`ce0418244d10342502`, Nick `jxlmiaxr6gt`, Row 1) dừng phiên feed session tại bước profile preflight với triệu chứng:
  `run plan max_duration_seconds exceeded before capture profile_preflight_switch_anchor_2_pre_tap_guard attempt 1`.
- Hiện trường máy thật: TikTok vẫn đang mở bình thường ở Trang chủ / Home Feed (`for-you`), màn hình hiển thị video rõ ràng.

## 2. Phân tích nguyên nhân gốc rễ (Anti-Pattern)
1. **Stall 5-6 phút trong `get_focused_activity` do fallthrough `capture_ui_xml`:**
   - Trong `python_runner/flows/observe.py`, `get_focused_activity` gọi `capture_ui_xml(ctx.adb, timeout=15, ...)`.
   - Tuy nhiên lời gọi này không truyền bất kỳ lightweight probe key nào (`lightweight=True`, `readiness_probe`, v.v.). Theo cơ chế của `automation_core.ui:1420`, thiếu lightweight key khiến core bỏ qua tầng ATX session nhẹ và chuyển sang `_dump_current_ui_unlocked`.
   - Khi uiautomator stub bị lag hoặc không phản hồi kịp, `_dump_current_ui_unlocked` kích hoạt toàn bộ chuỗi legacy recovery ladder (shell uiautomator dump với multiple retries, uiautomator process kill, app relaunch x3 với monkey, và adb transport reconnect loops).
   - Mỗi lệnh adb timeout ngốn 60s x 3 retries kèm reconnect wait 20s x 3 -> tổng thời gian thực thi của một lời gọi `get_focused_activity` lên tới 300s-360s (5 đến 6 phút).
2. **Pre-tap navigation thiếu nhịp settle retry khi `package: None`:**
   - Trong `calibrate_screens.py::tap_navigation_target`, bước kiểm tra an toàn pre-tap gọi `focus = get_focused_activity(ctx)` và `safety = safety_check(focus_package=focus.get("package"), ...)`.
   - Sau khi tap account switcher đổi tài khoản, TikTok đang chuyển cảnh hoặc reload dữ liệu khiến `focus.get("package")` tạm thời là `None`.
   - `safety_check` trả về `SAFETY_FAILED` với lý do `"focused package unavailable"`.
   - `tap_navigation_target` lập tức abort và trả về `NavigationResult(False, "fail", "focused package unavailable")` mà không cho phép settle retry (trong khi Case 115 mới chỉ hỗ trợ settle cho post-tap).
3. **Relaunch TikTok với sleep 2.0s quá ngắn trên Samsung S7:**
   - Trong `feed_swipe_smoke.py::_maybe_recover_navigation_from_add_phone`, khi dính `_is_launcher_focus_loss`, code gọi `force_stop_and_relaunch_tiktok` kèm `time.sleep(2.0)` rồi gọi ngay `retry_navigation()`.
   - Trên thiết bị Samsung Galaxy S7 (RAM 2GB, Android 7), app TikTok cần 6-10s để khởi động và hiển thị UI. 2.0s sleep khiến `retry_navigation()` kiểm tra focus khi app chưa kịp lên foreground, dẫn tới thất bại liên hoàn `focused package unavailable`.
4. **Vắt kiệt ngân sách deadline 2100s:**
   - Chuỗi 5 lần gọi ADB bị stall (mỗi lần 5-6 phút): `_dismiss_notification_shade_if_open` (6m) -> `tap_navigation_target` (5m) -> `_maybe_recover_navigation_from_add_phone` (6m) -> `_navigate_profile_for_preflight` (5m) -> loop sang `attempt = 2` (5m).
   - Tổng thời gian tiêu tốn lên tới 28-30 phút, vượt quá trần `DEFAULT_DEVICE_TIMEOUT_SECONDS = 2100.0` (35 phút).
   - Tại đầu vòng lặp `attempt = 2`, lời gọi `_capture_profile_guard_row(ctx, step="profile_preflight_switch_anchor_2_pre_tap_guard")` gọi `ensure_run_plan_deadline(ctx.config, ...)` và ném ngoại lệ `RunPlanDeadlineExceeded: run plan max_duration_seconds exceeded before capture profile_preflight_switch_anchor_2_pre_tap_guard attempt 1`.

## 3. Giải pháp chuẩn (Case Fix)
1. **Loại bỏ hoàn toàn stall 5 phút trong `get_focused_activity`:**
   - Thay thế `capture_ui_xml` bằng `from automation_core.persistent_ui import capture_atx_session_ui`.
   - Đặt timeout chặt chẽ `timeout=min(3.0, float(ctx.timeout("adb_seconds", 15)))` với `restart_attempts=0`.
   - Nếu có XML `<hierarchy`, trích xuất package/activity như bình thường.
   - Nếu ATX session không có XML hoặc ném lỗi, chỉ fallback sang các lệnh dumpsys shell nhanh (`dumpsys window`, `dumpsys activity activities`) với timeout giới hạn `<= 5.0s`. Tuyệt đối không fallthrough vào `_dump_current_ui_unlocked`.
2. **Bổ sung pre-tap settle retry & XML fallback trong `tap_navigation_target`:**
   - Trong `calibrate_screens.py::tap_navigation_target`, nếu `not focus.get("package")`: `time.sleep(1.0)` và gọi lại `get_focused_activity(ctx)` 1 lần nữa để bắt kịp nhịp chuyển cảnh của WindowManager.
   - Nếu `safety_check` vẫn trả về `SAFETY_FAILED` do `"focused package unavailable"`: trước khi abort, thử đọc nhanh UI XML qua ATX session. Nếu XML chứa package TikTok hợp lệ (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`), cập nhật `focus["package"] = expected_package` và cho phép tiến hành tap navigation bình thường.
3. **Sử dụng `_relaunch_and_poll_tiktok_focus` thay cho blind sleep 2.0s:**
   - Trong `_maybe_recover_navigation_from_add_phone` và các nhánh launcher recovery, sử dụng `_relaunch_and_poll_tiktok_focus` có polling loop (tối đa 4 lần x 2s) để đảm bảo TikTok đã thực sự chiếm foreground trước khi gọi `retry_navigation()`.
