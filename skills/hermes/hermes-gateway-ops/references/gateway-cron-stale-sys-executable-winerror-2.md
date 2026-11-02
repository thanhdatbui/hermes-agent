# Gateway In-Process Cron Scheduler Stale sys.executable & [WinError 2] RCA

## 1. Triệu chứng Hiện trường
- Hàng loạt cronjob / watchdog (cả `no_agent: true` lẫn agent jobs) đồng loạt thất bại trong cùng một khung giờ với thông báo:
  ```text
  ⚠️ Cron '<job_name>' failed: Script execution failed: [WinError 2] The system cannot find the file specified
  ```
- Tuy nhiên, khi kiểm tra trên đĩa thì file script (ví dụ `follow_session_watchdog.py`) vẫn tồn tại nguyên vẹn.
- Khi gọi test độc lập hoặc chạy bằng session CLI mới thì script chạy thành công bình thường.

## 2. Cơ chế Kỹ thuật Gốc rễ (Root Cause)
Trong `cron/scheduler.py` của Hermes:
```python
    suffix = path.suffix.lower()
    if suffix in {".sh", ".bash"}:
        argv = [_bash, str(path)]
    else:
        argv = [sys.executable, str(path)]

    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=script_timeout,
        cwd=str(path.parent),
        env=cron_env,
        **popen_kwargs,
    )
```

1. **Thứ tự kiểm tra an toàn của Scheduler:**
   - Scheduler kiểm tra `if not path.exists(): return False, f"Script not found: {path}"`.
   - Nếu bản thân file script bị thiếu, scheduler sẽ trả về `Script not found: ...`, **tuyệt đối không bao giờ rơi vào khối `except Exception as exc: return False, f"Script execution failed: {exc}"`**.
2. **Nguồn gốc ngoại lệ `[WinError 2]` trong khối try:**
   - Khi ngoại lệ là `Script execution failed: [WinError 2] The system cannot find the file specified`, điều đó chứng minh 100% chính tham số đầu tiên `argv[0]` — tức `sys.executable` — **không tồn tại trên hệ điều hành Windows**.
3. **Bẫy Venv Migration / Dọn đĩa C:**
   - Khi di dời môi trường từ venv cũ ở ổ C sang `D:\Taadaa\Hermes\.venv`, thư mục venv cũ bị xóa trong khi tiến trình Gateway cũ vẫn đang chạy trong RAM (chưa restart).
   - Trong RAM, `sys.executable` của tiến trình Gateway vẫn trỏ vào binary python.exe cũ đã bị xóa. Mỗi tick cron, Gateway cố spawn `python.exe` từ đường dẫn cũ $\rightarrow$ Windows báo `[WinError 2]`.

## 3. Bẫy Forwarding Shims & Stale Scripts Hardcode
Ngoài tiến trình Gateway cha, các forwarding shims hoặc script watchdog con cũng có thể tự chứa hardcode:
- Ví dụ trong `watchdog_kibe_downloader.py`:
  ```python
  python_exe = r"C:/Users/Kibe/.../venv/Scripts/python.exe"
  subprocess.Popen([python_exe, "-u", script_p], ...)
  ```
- Khi venv cũ bị xóa, script này ném `[WinError 2]` khi cố spawn background downloader.
- Cần chuẩn hoá các script con sử dụng:
  `python_exe = r"D:\Taadaa\Hermes\.venv\Scripts\python.exe"` hoặc virtualenv nghiệp vụ thích hợp (`D:\Taadaa\python-envs\automation\Scripts\python.exe`).

## 4. Quy trình Khắc phục và Phòng ngừa Chuẩn
1. **Khởi động lại Gateway ngay sau khi hoán đổi Venv:**
   - Cập nhật `$GatewayPython = 'D:\Taadaa\Hermes\.venv\Scripts\python.exe'` trong `hermes-gateway-watchdog.ps1`.
   - Dừng tiến trình Gateway cũ để Watchdog tự bật Gateway mới với `sys.executable` hợp lệ.
2. **Xác nhận `sys.executable` của Gateway mới:**
   - Kiểm tra `gateway.pid` và verify `gateway.log` / `watchdog.log` ghi nhận PID mới đã chạy với interpreter ổ D.
3. **Rà soát Forwarding Shims:**
   - Quét tìm chuỗi `hermes-agent` hoặc các đường dẫn venv cũ trong scripts để đảm bảo không còn script con nào gọi nhầm binary đã bị xóa.
