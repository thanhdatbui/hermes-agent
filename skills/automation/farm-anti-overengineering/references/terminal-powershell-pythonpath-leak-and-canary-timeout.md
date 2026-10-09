# Terminal PowerShell PYTHONPATH Leak & Canary Timeout Handling

## 1. Sự cố rò rỉ `PYTHONPATH` từ Hermes Terminal

### A. Triệu chứng
Khi chạy script launcher PowerShell (như `run-feed-session.ps1`, `run-follow.ps1`) hoặc lệnh Python consumer trực tiếp từ terminal của Hermes:
```text
Traceback (most recent call last):
  File "D:\Taadaa\tiktok-luot nuoi acc\python_runner\run_tiktok.py", line 37, in <module>
    from flows.calibrate_screens import calibrate_screens
  File "D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\calibrate_screens.py", line 10, in <module>
    from PIL import Image, UnidentifiedImageError
  File "C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\Image.py", line 95, in <module>
    from . import _imaging as core
ImportError: cannot import name '_imaging' from 'PIL' (C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\__init__.py)
```

### B. Nguyên nhân gốc rễ
Shell bash của Hermes export biến môi trường `PYTHONPATH` trỏ vào venv của chính Hermes agent (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`).
PowerShell khi khởi chạy từ bash kế thừa toàn bộ biến này trong `$env:PYTHONPATH`. Khi script PowerShell gọi `python`, trình thông dịch Python (ở host `Python312` hoặc venv của consumer) bị ép nạp site-packages của Hermes, dẫn tới xung đột binary C-extension (`_imaging`) của thư viện Pillow (PIL).

### C. Quy tắc khắc phục bắt buộc
1. **Luôn chạy kèm `env -u PYTHONPATH`:**
   Mọi lệnh terminal chạy PowerShell launcher hoặc Python consumer đều BẮT BUỘC bỏ gán `PYTHONPATH`:
   ```bash
   env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> ...
   ```
2. **Hardening trong script PowerShell:**
   Trong các runner PowerShell top-level, chèn `$env:PYTHONPATH = ""` ngay đầu script trước khi gọi `& $Python ...` để tự vệ độc lập với caller environment.

---

## 2. Xử lý Canary Run thời lượng dài bị Timeout Terminal (300s)

### A. Triệu chứng
Chạy canary feed session (`run-feed-session.ps1 -RecoveryTestSwipes 2 ...`) bị ngắt ở terminal sau 300s:
```text
[Command timed out after 300s]
```

### B. Cạm bẫy tâm lý (Anti-Patterns)
- **Vội kết luận Canary fail:** Tưởng lệnh lỗi và hoang mang đi tìm traceback không có thật.
- **Chạy đè lệnh mới:** Chạy lại ngay lệnh PowerShell khác trong khi tiến trình Python cũ vẫn đang chiếm ADB / giữ device lock, gây xung đột `LockTimeoutError` hoặc rối loạn UI điện thoại.
- **Mò tay ADB can thiệp:** Gõ `adb shell input` trong lúc runner đang dở tay thực hiện sequence vuốt.

### C. Cơ chế vận hành thực tế của Feed Session Runner
Tiến trình `run_tiktok.py` cần khoảng 6 – 9 phút để hoàn thành phiên phục hồi và lướt 2 swipe:
1. Đọc và kiểm tra safe workbook, mapping serial và acquire lock.
2. Thiết lập độ xoay màn hình (portrait rotation guard).
3. Mở TikTok, kiểm tra identity và chuyển tài khoản (switcher/anchor/verify guards).
4. Điều hướng về Home Feed, kiểm tra baseline và xử lý popup blind-probe.
5. Thực hiện 2 lần vuốt (swipe 1, swipe 2) kèm khoảng nghỉ ngẫu nhiên (watch delay 3–8s) và jitter cử chỉ.
6. Chụp ảnh màn hình kiểm chứng sau mỗi swipe.
7. Thoát TikTok về Launcher Home, giải phóng toàn bộ device lock (`machine_<N>.lock.json`, `serial_<serial>.lock.json`) và xuất `run_manifest.json`, `summary.txt`.

### D. Quy trình 4 bước kiểm chứng Canary khi dính Terminal Timeout (O(1))
1. **Bước 1: Kiểm tra PID:**
   ```powershell
   powershell.exe -Command "Get-Process -Name python,powershell | Select-Object Id, ProcessName, StartTime"
   ```
   Nếu tiến trình `python` của feed session vẫn tồn tại, đợi thêm 1–3 phút hoặc dùng `Wait-Process -Id <PID> -Timeout 60`.
2. **Bước 2: Theo dõi tiến độ thời gian thực qua log:**
   ```powershell
   powershell.exe -Command "Get-Content 'D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<run_id>\machines\machine_<N>\<run_id>\log.jsonl' -Tail 15"
   ```
3. **Bước 3: Xác thực kết quả dứt điểm từ Artifacts:**
   Khi tiến trình kết thúc, đọc 3 file trong thư mục run của máy:
   - `run_manifest.json`: kiểm tra `"final_status": "success"` và `"total_swipes_completed": 2`.
   - `recovery_lock_handoff.json`: kiểm tra `"final_status": "success"` và `"lock_status": "released"`.
   - `summary.txt`: đọc tóm tắt trạng thái và các step hoàn thành.
4. **Bước 4: Kiểm tra trạng thái máy trên ADB:**
   Dùng serial từ `recovery_lock_handoff.json` để kiểm tra focus:
   ```bash
   adb -s <serial> shell "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"
   ```
   Xác nhận máy đã về `LauncherActivity` (Home) an toàn.
