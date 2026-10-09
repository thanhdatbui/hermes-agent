# Case 166: Phiên 1 Tự Động Kích Hoạt Upload Do Hardcode `-AllowUploadHook`

## Hiện tượng
Tại Ca 3 - Phiên 1 (18:00), `feed_session_watchdog` báo cáo có 45 video đã được đăng thành công, dù quy tắc vận hành bất biến của farm là: **Chỉ đăng video ở Phiên 2 mỗi ca (Phiên 1 chỉ lướt Feed thuần)**.

## Nguyên nhân cốt lõi (Root Cause)
Trong cron runner wrapper `tiktok_runner.py` (tại `~/AppData/Local/hermes/scripts/tiktok_runner.py`):
- `_determine_row()` phân loại đúng `session_index = 1` cho mốc 18:00 (Phiên 1) và `session_index = 2` cho mốc 20:00 (Phiên 2).
- Tuy nhiên, trong hàm `_spawn_feed_session()`, tham số `"-AllowUploadHook"` bị **hardcode cứng** trong mảng `argv` gọi `run-feed-session.ps1` ở mọi session:
  ```python
  argv = [
      ...
      "-Row", str(row),
      "-SessionIndex", str(session_index),
      "-AllowUploadHook",  # <-- HARDCODE LỖI: luôn kích hoạt upload bất kể session_index
      "-Preset", "full",
      ...
  ]
  ```
- File `run-feed-session.ps1` kiểm tra:
  ```powershell
  if ($AllowUploadHook -or $SessionIndex -eq 2) {
      $arguments += "--allow-upload-hook"
  }
  ```
  Do cờ `-AllowUploadHook` luôn được truyền, runner kích hoạt upload hook ngay cả khi `session_index == 1`.

## Giải pháp chuẩn (Fix Contract)
Chỉ truyền flag `-AllowUploadHook` khi `session_index == 2`:
```python
argv = [
    ...
    "-Row", str(row),
    "-SessionIndex", str(session_index),
    *(["-AllowUploadHook"] if session_index == 2 else []),
    "-Preset", "full",
    ...
]
```

## Quy trình kiểm chứng & Đồng bộ
1. Kiểm tra syntax: `python -m py_compile "C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_runner.py"`
2. Verify logic argv: Với `session_index=1` mảng không chứa `-AllowUploadHook`, với `session_index=2` mảng có `-AllowUploadHook`.
3. Đồng bộ đa tầng (Deploy & OneDrive):
   `python "C:/Users/Kibe/AppData/Local/hermes/scripts/cron_sync_watchdog.py" --force`
