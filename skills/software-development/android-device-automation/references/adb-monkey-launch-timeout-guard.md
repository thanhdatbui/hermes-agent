# ADB Monkey Launch Timeout Guard & Sensitive Word Redaction

## 1. Hiện tượng & Log lỗi
Khi khởi chạy ứng dụng (TikTok/Facebook/Gmail) trên điện thoại Android thuộc farm:
- Log lỗi trả về:
  `adb command timed out: ('...adb.exe', '-s', '<serial>', 'shell', '<redacted>', '-p', 'com.ss.android.ugc.trill', '-c', 'android.intent.category.LAUNCHER', '1')`
- Quan sát thực tế: App mục tiêu đã mở sẵn ở foreground, video/giao diện đang chạy bình thường, nhưng worker crash với ngoại lệ `ADBError`.

## 2. Phân tích nguyên nhân kỹ thuật
1. **Mặt nạ nhạy cảm `<redacted>`:**
   Trong `automation_core/adb.py`, danh sách `SENSITIVE_WORDS = ("TOKEN", "SECRET", "PASSWORD", "PASS", "COOKIE", "KEY")`. Do từ khóa `"monkey"` chứa chuỗi `"key"`, hàm `_redact_arg("monkey")` tự động che giấu thành `<redacted>`. Đây thực chất là lệnh `adb shell monkey -p <pkg> -c android.intent.category.LAUNCHER 1`.
2. **Cơ chế timeout của `AdbClient`:**
   - Khi chạy lệnh ADB qua `adb.shell(...)`, timeout mặc định kế thừa từ `ctx.timeout("adb_seconds", 15)` hoặc `AdbClient.default_timeout = 15s`.
   - Nếu daemon `monkey` của Android bị nghẽn I/O (do thiết bị đang chạy nặng, load video, hoặc app đã ở foreground), lệnh có thể mất >15 giây.
   - Khi hết timeout, `AdbClient._execute()` ném ra `ADBError("adb command timed out: ...")`. Cờ `check=False` **chỉ áp dụng cho returncode != 0**, hoàn toàn KHÔNG chặn exception do timeout.
3. **Thiếu pre-check foreground & try-except:**
   Hàm `prepare_app_for_automation` (trong `automation_core/startup.py`) và `Actions.start_app` (trong `actions.py`) nếu gọi trực tiếp `adb.shell(["monkey", ...])` mà không bọc `try...except ADBError` sẽ làm sập quy trình khởi động dù ứng dụng đã sẵn sàng.

## 3. Quy chuẩn vá code (Mandatory Pattern)
Mọi điểm gọi lệnh launch app bằng `monkey` bắt buộc:
1. **Pre-check Foreground**: Trước khi bắn lệnh monkey, đọc `focus_reader()` / `get_focused_activity()`. Nếu target package đã ở foreground, bỏ qua lệnh monkey và ghi nhận step `launch_app` thành công (`already_foreground`).
2. **Bọc `try...except` và fallback kiểm tra focus**:
   ```python
   cur_pkg, cur_act = focus_reader()
   if cur_pkg == target:
       steps.append(StartupStep("launch_app", "success", "", {"package": target, "note": "already_foreground"}))
       launched_ok = True
   else:
       launch_error = ""
       try:
           launched = adb.shell(
               ["monkey", "-p", target, "-c", "android.intent.category.LAUNCHER", "1"],
               timeout=max(timeout, 30.0),
               check=False,
           )
           launched_ok = launched.ok
           if not launched.ok:
               launch_error = _text(launched.stderr).strip() or _text(launched.stdout).strip() or "adb command failed"
       except Exception as exc:
           cur_pkg, _ = focus_reader()
           launched_ok = (cur_pkg == target)
           launch_error = str(exc) if not launched_ok else ""
       steps.append(StartupStep("launch_app", "success" if launched_ok else "failed", launch_error, {"package": target}))
   ```
3. **Tăng timeout lên tối thiểu 30s**: Không dùng timeout hẹp 15s cho các lệnh gọi `monkey` trên thiết bị thật.

## 4. Kỷ luật điều tra log & Quét đĩa `.ai-runs`
- Thư mục `.ai-runs` trong `tiktok-luot nuoi acc` chứa hàng trăm nghìn thư mục run lịch sử.
- **CẤM TUYỆT ĐỐI** dùng `os.walk` không giới hạn độ sâu hoặc grep đĩa diện rộng (`grep -rn`), lệnh sẽ bị timeout 900s.
- Chỉ trích xuất log bằng:
  - `python D:/Taadaa/tools/inspect_machine.py <N>`
  - Hoặc `os.listdir('D:/Taadaa/tiktok-luot nuoi acc/.ai-runs')` ở cấp thư mục gốc.
