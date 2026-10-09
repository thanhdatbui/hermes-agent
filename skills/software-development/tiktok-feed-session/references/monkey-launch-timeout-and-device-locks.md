# Monkey Launch ADB Timeout & Device Lock Handling

## 1. Monkey Launch ADB Timeout & Foreground Fallback Pattern

### Vấn đề
Lệnh `adb shell monkey -p <pkg> -c android.intent.category.LAUNCHER 1` thường xuyên bị ADB timeout khi chạy đồng thời nhiều thiết bị (batch 40-80 máy) hoặc máy tải cao. Khi đó, tiến trình monkey có thể đã kích hoạt app thành công trên thiết bị, nhưng pipe trả về từ ADB daemon bị nghẽn dẫn tới `TimeoutError` / `ADBError`.

### Quy tắc xử lý chuẩn (Patch Contract trong `device_prepare.py`)
Không để ngoại lệ timeout làm sập flow. Luôn bọc monkey trong `try / except Exception as exc:` và fallback kiểm tra focus:

```python
try:
    launch_result = ctx.adb.shell(
        ["monkey", "-p", target_package, "-c", "android.intent.category.LAUNCHER", "1"],
        timeout=timeout,
    )
except Exception as exc:
    logger.warning("Monkey launch failed or timed out for %s: %s", target_package, exc)
    focus = get_focused_activity(ctx)
    if focus.get("package") == target_package:
        launch_result = AdbResult(
            args=("monkey", "-p", target_package, "-c", "android.intent.category.LAUNCHER", "1"),
            stdout="App in foreground",
            stderr=str(exc),
            exit_code=0,
        )
    else:
        if raise_on_result_failure:
            raise ForceStopRelaunchCommandFailed("launch_tiktok", ...) from exc
        launch_result = AdbResult(...)

if not launch_result.ok:
    focus = get_focused_activity(ctx)
    if focus.get("package") == target_package:
        launch_result = AdbResult(
            args=launch_result.args,
            stdout=launch_result.stdout or "App in foreground",
            stderr=launch_result.stderr,
            exit_code=0,
        )
    elif raise_on_result_failure:
        raise ForceStopRelaunchCommandFailed("launch_tiktok", launch_result)
```

Áp dụng tương tự cho hàm con `_relaunch()` trong `dismiss_popup()` (`prepare_tiktok_app_for_automation`).

---

## 2. Device Lock: Kiểm Tra Stale vs Active Lock

File lock thiết bị lưu tại: `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`

### Quy trình kiểm tra an toàn trước khi chạy Canary:
1. Đọc file lock, trích xuất `pid`.
2. Kiểm tra tiến trình sở hữu (`psutil.pid_exists(pid)`).
3. **Nếu PID đã chết:** Lock là stale -> xóa lock an toàn.
4. **Nếu PID còn sống:** Kiểm tra `cmdline` của process.
   - Nếu là batch cron `multi-machine-feed-session` đang giữ lock, **CẤM** tự tiện xóa lock hoặc can thiệp máy khi chưa được lệnh.
   - Chờ hoặc kiểm tra log của máy trong thư mục runtime xem batch đã hoàn thành phân đoạn của máy đó chưa.

---

## 3. Kỷ Luật Tool-Call & Tối Ưu Tốc Độ Cho Worker

- **Giới hạn:** Tối đa <= 10 tool calls, hoàn tất trong <= 10 phút.
- **Cấm:** Không dùng `os.walk`, `glob(recursive=True)`, `grep -rn` quét ổ đĩa tìm log/chuỗi.
- **Trình tự chuẩn:**
  1. Đọc đúng vị trí code cần sửa (`read_file` theo offset hẹp).
  2. Áp dụng patch (`patch`).
  3. Kiểm tra cú pháp nhanh: `python -m py_compile <file.py>`.
  4. Kiểm tra lock máy: xóa stale lock nếu PID chết.
  5. Chạy Canary Test duy nhất: `run-feed-session.ps1 -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`.
  6. Báo cáo ngắn gọn: Git diff + Canary output.
