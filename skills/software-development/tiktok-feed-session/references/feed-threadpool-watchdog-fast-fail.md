# TikTok Feed Session: Threadpool Starvation, Watchdog Timezones & Fast Fail-Closed

## 1. Watchdog UTC vs HCMC Timezone Handling
- **Nguyên nhân bug nghẽn báo cáo:** `run_manifest.json` ghi thời gian `end_time` theo chuẩn ISO UTC (`+00:00` hoặc `Z`, ví dụ `2026-10-13T01:02:39+00:00`).
- **Hiện tượng deadlock:** Khi Ca 1 chạy trễ đè sang Ca 2, `is_cluster_session_busy` luôn bằng `True`. Watchdog bắt buộc phải kiểm tra `_is_session_manifest_completed`. Nếu cắt chuỗi thô (`end_time.split(" ")[-1][:5]`) thì lấy giờ UTC `"01:02"` so sánh với mốc ca `"08:00"`. Do `"01:02" < "08:00"`, watchdog ngộ nhận Ca 1 chưa xong và khóa nghẽn gửi báo cáo Telegram.
- **Quy tắc:** Bắt buộc parse datetime và đổi sang múi giờ `Asia/Ho_Chi_Minh` trước khi so sánh với `win_end_hm`:
  ```python
  dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
  if dt.tzinfo is not None:
      dt = dt.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
  end_hm = dt.strftime("%H:%M")
  ```

## 2. Phòng chống ngâm Threadpool trong `prepare_tiktok` (Anti-Starvation)
- **Triệu chứng:** Khi TikTok văng ra Launcher hoặc đơ ADB, hàm `dismiss_popup()` trong `prepare_tiktok_app_for_automation` gọi `capture_required_ui(timeout=60)` tới 10 lần retry. Nếu nhiều máy cùng dính, worker threadpool bị ngâm 30-76 phút, dẫn đến chạm kịch trần watchdog 2 tiếng (`hard outer watchdog deadline expired`).
- **Quy tắc O(1) Cache & Skip:**
  - Lưu `_last_focus` ngay trong closure `read_focus()` để không tốn thêm lệnh dumpsys/ADB nào.
  - Trong `dismiss_popup()`, nếu `_last_focus` là `None` hoặc thuộc launcher (`com.sec.android.app.launcher`, Launcher3) / SystemUI, lập tức `return False` và ghi log skip. Tuyệt đối không dump UI XML khi app chưa ở foreground.
  - Cắt giảm thời gian xử lý máy lỗi từ 76 phút xuống dưới 10 giây.

## 3. Fast Fail-Closed trên lỗi Focus & Skip Downstream Hooks
- Đưa chuỗi `"failed to focus tiktok after launch"` vào `_FATAL_DEVICE_ERROR_PATTERNS`.
- Khi `prepare_tiktok` thất bại, thiết bị được coi là dính lỗi fatal:
  - Bỏ qua toàn bộ follow-hook, upload-hook, clear-cache-hook.
  - Nhả ngay slot lease để worker thread nhận máy tiếp theo.

## 4. Chuẩn hóa Import `_path_setup` trong Unit Tests
- Khi Closeout Gate hoặc các test runner độc lập chạy pytest trực tiếp trên file test mà không có cờ `-o pythonpath`, lệnh `import _path_setup` sẽ ném `ModuleNotFoundError`.
- Mẫu chuẩn bắt buộc cho mọi file test trong `python_runner/tests/`:
  ```python
  try:
      import _path_setup  # noqa: F401
  except ModuleNotFoundError:
      import sys
      from pathlib import Path

      _tests_dir = Path(__file__).resolve().parent
      if str(_tests_dir) not in sys.path:
          sys.path.insert(0, str(_tests_dir))
      import _path_setup  # noqa: F401
  ```
