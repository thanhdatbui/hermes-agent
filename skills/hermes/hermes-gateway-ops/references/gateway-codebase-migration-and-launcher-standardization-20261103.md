# Hermes Codebase Migration to D:\Taadaa\Hermes & Desktop/Startup Launcher Standardization (2026-11-03)

## Bối cảnh & Nguyên nhân
Khi gom codebase Hermes về một mối duy nhất tại `D:\Taadaa\Hermes` và loại bỏ/backup thư mục cũ `%LOCALAPPDATA%\hermes\hermes-agent` (`hermes-agent.retired_backup`), phát sinh 2 rủi ro hệ thống:
1. **SSL / CA Bundle Mismatch (`SSLConfigurationError`)**: Process gateway cũ giữ biến môi trường `SSL_CERT_FILE` trỏ tới `...\hermes-agent\venv\Lib\site-packages\certifi\cacert.pem`. Khi thư mục cũ biến mất, `ssl_guard.py` chặn mọi cuộc gọi tới OpenAI client khiến toàn bộ bot Telegram văng lỗi `"Sorry, I encountered an unexpected error"`.
2. **Orphan Launchers & Watchdogs Trap**: Dù Gateway service chính đã được cập nhật sang `D:\Taadaa\Hermes\.venv`, hàng loạt shortcut, VBS script và batch script trên Desktop, Startup hoặc tools vẫn còn giữ đường dẫn cũ trỏ vào `hermes-agent\venv`:
   - `C:\Users\<user>\Desktop\BAT_Hermes_Gateway.vbs`
   - `C:\Users\<user>\Desktop\Bat Gan Proxy Watcher.cmd`
   - `Startup\start_tiktok_dashboard.vbs`
   - `D:\Taadaa\tools\start_tiktok_dashboard_hidden.vbs`

Nếu người dùng hoặc automation double-click vào các shortcut này, hệ thống sẽ cố gọi executable không tồn tại hoặc spawn lại process với môi trường hỏng.

## Quy chuẩn rà soát và chuẩn hoá sau migration

### 1. Checklist các vị trí launcher bắt buộc kiểm tra
- **Desktop**: `C:\Users\<user>\Desktop\*.vbs`, `*.cmd`, `*.bat`
- **Windows Startup**: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*.vbs`
- **Gateway Service VBS**: `%LOCALAPPDATA%\hermes\gateway-service\Hermes_Gateway.vbs`
- **Tools / Schedulers**: `D:\Taadaa\tools\start_*_hidden.vbs`

### 2. Mẫu chuẩn hoá chuẩn cho Launcher Desktop (`BAT_Hermes_Gateway.vbs`)
Không bao giờ gọi trực tiếp `hermes.exe` từ venv cũ. Luôn ủy quyền qua Service VBS hoặc gọi venv tại `D:\Taadaa\Hermes`:
```vbs
Option Explicit
Dim sh, fso, target
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
target = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\hermes\gateway-service\Hermes_Gateway.vbs"
If fso.FileExists(target) Then
    sh.Run "wscript.exe """ & target & """", 0, False
Else
    sh.Run """D:\Taadaa\Hermes\.venv\Scripts\pythonw.exe"" -m hermes_cli.main gateway run", 0, False
End If
WScript.Sleep 3000
MsgBox "Hermes Gateway da bat lai. Cho 15 giay roi thu nhan tin Telegram.", vbInformation, "BAT Hermes Gateway"
```

### 3. Đồng bộ cả 2 đầu (Tools và Startup)
Đối với các tiến trình chạy ngầm khi boot Windows (như dashboard, watchdog):
- File tại `D:\Taadaa\tools\start_<service>_hidden.vbs`
- File tại `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\start_<service>.vbs`
BẮT BUỘC phải đồng bộ nội dung giống nhau, cùng trỏ về `D:\Taadaa\Hermes\.venv\Scripts\pythonw.exe` (hoặc `python.exe`).
