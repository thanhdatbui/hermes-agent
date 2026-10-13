# Pitfalls: Fast Fail-Closed, Threadpool Starvation, & Watchdog Timezone Reconciliation

## 1. Watchdog Timezone vs Window Parsing (`_is_session_manifest_completed`)
- **Triệu chứng:** Báo cáo phiên sáng (khung 06:00 - 08:00) không được gửi lúc 08:00 - 09:30, watchdog im lặng dù máy đã chạy xong và phiên 2 đang chạy bình thường.
- **Root Cause:**
  - `run_manifest.json` ghi nhận `end_time` theo chuẩn ISO UTC (`+00:00`, ví dụ: `2026-10-13T01:02:39+00:00`).
  - Watchdog so sánh với mốc kết thúc cửa sổ phiên (`win_end_hm = "08:00"` giờ HCMC).
  - Cắt chuỗi ngây thơ `end_time.replace("T", " ").split(" ", 1)[-1][:5]` ra `"01:02"`. Vì `"01:02" < "08:00"`, watchdog ngộ nhận phiên 1 chưa hoàn tất sau window.
  - Khi phiên 2 kích hoạt, `runner_busy` của cluster trở thành `True`. Watchdog thấy phiên 1 chưa xong VÀ cluster đang busy -> kích hoạt cờ chặn gửi báo cáo.
- **Quy tắc chuẩn hóa:**
  Bắt buộc parse ISO timestamp và convert sang múi giờ `Asia/Ho_Chi_Minh` trước khi so sánh:
  ```python
  try:
      dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
      if dt.tzinfo is not None:
          dt = dt.astimezone(HCMC)
      end_hm = dt.strftime("%H:%M")
  except Exception:
      end_hm = end_time.replace("T", " ").split(" ", 1)[-1][:5]
  if end_hm >= win_end_hm:
      return True
  ```

---

## 2. Ngâm Threadpool do Dismiss Popup Khi TikTok Chưa Lên Foreground
- **Triệu chứng:** Phiên nuôi acc chạy chạm kịch trần 2 giờ (`hard outer watchdog deadline expired`), mỗi máy hỏng ngâm thread từ 30 đến 76 phút.
- **Root Cause:**
  - Trong `prepare_tiktok_app_for_automation`, khi TikTok crash/văng, thiết bị ở màn hình Launcher hoặc đơ ADB (`focused_package` là `None` hoặc `com.sec.android.app.launcher`).
  - Hàm `dismiss_popup()` vẫn mù quáng gọi `capture_required_ui(timeout=60)` qua 10 lần retry để quét popup TikTok.
- **Giải pháp tối ưu O(1) (Zero extra ADB call):**
  - Caching `_last_focus` ngay trong `read_focus()` (không gọi thêm dumpsys làm tốn thời gian và làm hỏng mock test):
  ```python
  _last_focus: dict[str, Any] = {}

  def read_focus() -> tuple[str | None, str | None]:
      nonlocal _last_focus
      focus = get_focused_activity(ctx)
      ...
      _last_focus = focus
      return focus.get("package"), focus.get("activity")

  def dismiss_popup() -> bool:
      pkg = _last_focus.get("package")
      if not pkg or pkg in (
          "com.sec.android.app.launcher",
          "com.google.android.apps.nexuslauncher",
          "com.android.launcher3",
          "com.android.systemui",
      ):
          logger.info("Skipping popup dismissal: foreground package %s is launcher/systemui", pkg)
          return False
  ```

---

## 3. Fast Fail-Closed Khi Prepare Focus Thất Bại
- **Triệu chứng:** Máy không mở được TikTok nhưng runner vẫn tiếp tục cố chạy `upload-hook` (khởi chạy process `scripts.tiktok_workflow` riêng tốn thêm 45-60s/máy).
- **Quy tắc:**
  - Bổ sung `"failed to focus tiktok after launch"` vào `_FATAL_DEVICE_ERROR_PATTERNS`.
  - Trong `_run_child`: Ngay khi `is_fatal` là `True`, lập tức `return child_result` trước khi đến các hook follow/upload/clear cache.
  - Thêm telemetry log rõ ràng: `logger.warning("[FAST-FAIL] Machine %s serial %s fatal stop: %s; skipping hooks immediately", ...)`.

---

## 4. Kiểm Thử Fast Fail-Closed & Mock Teardown
- Khi viết unit test cho `_run_child` fast-fail, BẮT BUỘC mock cả `_force_stop_tiktok_and_home` để tránh teardown thực hiện lệnh ADB ngầm gây timeout test.
- Kiểm tra giải phóng tài nguyên bằng `mock_lease.release.assert_called()` thay vì các trạng thái lease cũ không tồn tại.
