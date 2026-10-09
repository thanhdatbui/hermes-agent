# ADB Launch App Timeout Recovery & Monkey Pitfalls

## 1. Triệu chứng & Nhận diện lỗi
Khi điều tra lỗi khởi động app (TikTok/Facebook/...) trên thiết bị farm:
- Log lỗi: `adb command timed out: ('...adb.exe', '-s', '<serial>', 'shell', '<redacted>', '-p', 'com.ss.android.ugc.trill', '-c', 'android.intent.category.LAUNCHER', '1')`
- **Tại sao có `<redacted>`:** Trong `automation_core/adb.py`, `SENSITIVE_WORDS = ("TOKEN", "SECRET", "PASSWORD", "PASS", "COOKIE", "KEY")`. Từ khóa `"monkey"` chứa `"key"` nên hàm `_redact_arg("monkey")` tự động che thành `<redacted>`.
- **Thực tế trên máy:** TikTok hoặc ứng dụng mục tiêu đã ở foreground, video đang phát bình thường, nhưng flow script bị crash và báo fail.

## 2. Nguyên nhân gốc rễ
1. **Timeout mặc định 15s:** Subprocess ADB gọi qua `ctx.timeout("adb_seconds", 15)` hoặc `AdbClient.default_timeout = 15`. Lệnh `monkey` khởi động runtime Android và dispatch event, khi máy đang chạy nặng hoặc app đã ở foreground, daemon `monkey` có thể bị nghẽn I/O dẫn tới quá 15s.
2. **`check=False` không chặn `ADBError` do timeout:** Trong `automation_core/adb.py`, cờ `check=False` chỉ ngăn exception khi command trả về `exit_code != 0`. Nếu lệnh quá timeout, `_execute` luôn raise `ADBError("adb command timed out: ...")`.
3. **Thiếu pre-check foreground & ngoại lệ quanh launch:** `prepare_app_for_automation` và `Actions.start_app` nếu gọi trực tiếp `adb.shell(["monkey", ...])` mà không bọc `try...except ADBError` sẽ làm sập toàn bộ luồng, dù app đã mở thành công.

## 3. Quy chuẩn vá code (Code Pattern chuẩn)
Mọi hàm launch app (trong `automation-core/startup.py`, `actions.py`, `device_prepare.py`) phải tuân thủ:

1. **Pre-check Foreground:** Kiểm tra trước xem target package đã ở foreground chưa (`focus_reader()` hoặc `get_focused_activity()`). Nếu đã ở foreground, ghi nhận `already_foreground` và bỏ qua gọi lại `monkey`.
2. **Bọc `try...except Exception` quanh `adb.shell(["monkey", ...])`:**
   ```python
   cur_pkg, _ = focus_reader()
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
   ```
3. **Tăng timeout cho `monkey` lên tối thiểu 30s:** Không dùng timeout quá hẹp (15s) cho thao tác launch app.

## 4. Cảnh báo quét đĩa `.ai-runs`
Thư mục `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs` chứa hàng trăm nghìn file runs lịch sử. Tuyệt đối **CẤM** dùng `os.walk` không giới hạn độ sâu hoặc grep toàn bộ repo; lệnh sẽ bị timeout 900s. Chỉ dùng `inspect_machine.py <N>` hoặc `os.listdir()` ở tầng gốc.
