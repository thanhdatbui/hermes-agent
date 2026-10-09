# ADB Settings Timeout & Portrait Rotation Guard (Case 113)

## 1. Hiện tượng & Triệu chứng
Farm Alert `[MÁY N] DỪNG PHIÊN` với lỗi:
```text
adb command timed out: ('C:\Program Files (x86)\xiaowei\tools\adb.exe', '-s', '<serial>', 'shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0')
```
Hiện trường máy thật: TikTok đang mở bình thường ở foreground (`SplashActivity`), đang phát video trên feed, không hề bị kẹt UI.

## 2. Nguyên nhân cốt lõi (Anti-Pattern)
- Trong các bước preflight và dọn dẹp (`before_swipe_loop`, `after_swipe_loop`, `prepare_tiktok`), runner gọi `ensure_portrait_rotation` (trong `device_prepare.py`) hoặc `lock_portrait_rotation` (trong `automation-core/src/automation_core/startup.py`).
- Cả hai hàm này thực thi các lệnh `adb shell settings put system accelerometer_rotation 0` và `settings get ...` với timeout mặc định 15s nhưng **không bọc trong khối `try...except`**.
- Khi ADB daemon bị trễ, cáp micro-USB của dòng S7 tiếp xúc kém chập chờn, hoặc transport bị lag, `AdbClient` quăng ngoại lệ `ADBError` (hoặc `subprocess.TimeoutExpired`).
- Do thiếu exception guard, ngoại lệ văng thẳng lên top-level runner, làm sập toàn bộ session feed đang chạy mượt mà và kích hoạt Farm Alert dừng máy oan uổng.

## 3. Giải pháp chuẩn (Pattern Case 113)
Áp dụng tại `flows/device_prepare.py` và `automation_core/startup.py`:

### a. Giới hạn Timeout (Timeout Capping)
Không để lệnh xoay màn hình chờ tới 15s-30s. Giới hạn trần:
```python
timeout = min(ctx.timeout("adb_seconds", 15), 8.0)
```

### b. Bọc Exception Guard độc lập cho từng lệnh
Bọc `try...except Exception as exc:` độc lập cho cả vòng lặp `settings put` và `settings get` của cả 2 thuộc tính `accelerometer_rotation` và `user_rotation`:
```python
for setting in ("accelerometer_rotation", "user_rotation"):
    try:
        result = ctx.adb.shell(["settings", "put", "system", setting, "0"], timeout=timeout)
        observed[f"{setting}_put"] = ExitStatus.SUCCESS.value if result.ok else "failed"
        if not result.ok:
            errors.append(f"{setting} put: {result.stderr.strip() or result.stdout.strip() or 'adb command failed'}")
    except Exception as exc:
        observed[f"{setting}_put"] = "failed"
        errors.append(f"{setting} put timeout/error: {exc}")
```
Làm tương tự cho bước `settings get`.

### c. Nguyên tắc Degraded thay vì Abort
- Lệnh khóa xoay màn hình chỉ là bước chuẩn bị phụ trợ (auxiliary device readiness), không mang tính sinh tử như kiểm tra app foreground hay tài khoản đăng nhập.
- Khi lệnh này thất bại hoặc timeout, runner chỉ ghi nhận step row có `result="failed"` kèm text lỗi vào summary, **tuyệt đối không để exception văng ra ngoài** làm dừng phiên lướt feed.

## 4. Test Verification chuẩn
Viết test case trong `tests/test_device_prepare.py` giả lập `ctx.adb.shell.side_effect = ADBError("timed out")` để đảm bảo:
1. Hàm không văng ngoại lệ (`Exception` không thoát ra ngoài).
2. Trả về row có `result="failed"`, chứa text `"timeout/error"` và các trường `*_put = "failed"`.
3. Test cap timeout xác minh mọi call shell đều có `timeout <= 8.0`.
