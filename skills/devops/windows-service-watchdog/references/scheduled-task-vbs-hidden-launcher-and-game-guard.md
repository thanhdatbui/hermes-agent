# Windows Task Scheduler Headless Execution (VBScript SW_HIDE) & Game-Guard Pattern

## 1. Hiện tượng & Sự cố thực tế (Incident Context)
- **Triệu chứng:** Khi người dùng đang chơi game (Teamfight Tactics / ĐTCL qua MetaTFT, Liên Minh Huyền Thoại, Warcraft 3) trên máy phụ (`admin-farm` / Admin-PC), màn hình đột ngột bị cướp focus bởi một cửa sổ Command Prompt (`cmd.exe`) in log dọn đĩa / backup Google Drive (`f_src-248 -> GDrive & Freed 55 files...`).
- **Tác hại:** Làm gián đoạn trận đấu, văng chuột, tụt FPS do tranh chấp I/O đĩa và CPU trong pha combat.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Task Scheduler chạy trực tiếp qua Console Subsystem:**
   - Khi đăng ký Scheduled Task với lệnh `cmd /c python ...` hoặc `python.exe script.py`, Windows Task Scheduler khởi tạo tiến trình con thuộc Console Subsystem. Hệ điều hành tự động cấp phát `conhost.exe` và hiển thị cửa sổ cmd lên màn hình tương tác của User (`Session# 1 / Console`).
   - Cờ `Hidden` trong cài đặt XML của Task Scheduler thường không thể giấu triệt để cửa sổ console nếu action gọi thẳng `cmd.exe`.
2. **Thiếu cơ chế Game-Guard kiểm tra trạng thái chơi game:**
   - Các task định kỳ nặng (backup, render, đồng bộ Google Drive/OneDrive, robocopy) kích hoạt định kỳ 2 giờ/lần mà không kiểm tra xem người dùng có đang trong trận game hay không.

## 3. Quy chuẩn giải pháp triệt để (Canonical Fix)

### Bước 1: Bọc hoàn toàn lệnh qua VBScript ẩn (WindowStyle = 0)
Tạo file launcher VBScript trung gian (ví dụ `D:\Taadaa\tools\start_sync_gdrive_hidden.vbs`):
```vbscript
Set WshShell = CreateObject("WScript.Shell")
' Tham số thứ 2 là 0 = SW_HIDE (ẩn hoàn toàn cửa sổ), tham số thứ 3 là True (đợi lệnh chạy xong)
WshShell.Run "python D:\Taadaa\tools\sync_and_clean_gdrive.py 20", 0, True
```

### Bước 2: Cập nhật Scheduled Task trỏ sang `wscript.exe`
Cập nhật Action của Task Scheduler:
- **Program/script:** `wscript.exe`
- **Arguments:** `//B //Nologo "D:\Taadaa\tools\start_sync_gdrive_hidden.vbs"`
- Lệnh CLI qua `schtasks`:
  ```cmd
  schtasks /create /tn "Taadaa_Sync_GDrive_Backup" /tr "wscript.exe //B //Nologo D:\Taadaa\tools\start_sync_gdrive_hidden.vbs" /sc hourly /mo 2 /ru Admin /f
  ```

### Bước 3: Tích hợp Game-Guard kiểm tra trận đấu vào Script Python
Mọi tác vụ nền nặng tài nguyên bắt buộc phải có hàm kiểm tra:
```python
import sys
import subprocess

def is_game_running() -> bool:
    """Kiểm tra xem máy có đang chạy game TFT, LMHT hoặc War3 hay không."""
    try:
        flags = 0x08000000 if sys.platform == "win32" else 0
        out = subprocess.check_output(
            ["tasklist", "/fi", "STATUS eq RUNNING", "/fo", "csv"],
            text=True,
            creationflags=flags
        )
        game_procs = [
            "league of legends.exe",
            "tftclient.exe",
            "tftclient-win64-shipping.exe",
            "war3.exe",
            "w3l.exe",
            "warcraft iii.exe",
            "frozen throne.exe",
        ]
        out_lower = out.lower()
        return any(g in out_lower for g in game_procs)
    except Exception:
        return False

def main_job():
    if is_game_running():
        print("[SKIP] Game is active (TFT/War3), skipping execution to avoid disturbance.")
        return
    # Thực hiện công việc bình thường...
```

### Bước 4: Ép cờ `CREATE_NO_WINDOW` cho mọi subprocess con
Mọi lệnh con bên trong script (ví dụ gọi `robocopy`, `ffmpeg`, `git`, `adb`) bắt buộc truyền cờ:
```python
flags = 0x08000000 if sys.platform == "win32" else 0
subprocess.run(["robocopy", src, dst, "/E", "/NP"], capture_output=True, creationflags=flags)
```

### Bước 5: Rà soát các Task phụ trợ khác
- Với các task "đánh thức" (wake up) hoặc heartbeat chỉ chạy lệnh thoát (như `WakeUpForCron` trước đó chạy `cmd.exe /c exit`):
- Sửa action thành:
  ```cmd
  schtasks /change /tn "WakeUpForCron" /tr "powershell.exe -NoProfile -WindowStyle Hidden -Command exit"
  ```
