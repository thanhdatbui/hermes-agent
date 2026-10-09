# Admin ADB Server — Ẩn Cửa Sổ Console Triệt Để

## Vấn đề
Task Scheduler `Taadaa_ADB_User_Remote` trên máy Admin (192.168.110.119) khởi động `C:\Taadaa_Service\start_admin_adb.bat`:
```bat
@echo off
netstat -ano | findstr "0.0.0.0:5037" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 exit /b 0
"C:\Program Files (x86)\xiaowei\tools\adb.exe" kill-server >nul 2>&1
start "" /b "C:\Program Files (x86)\xiaowei\tools\adb.exe" -a nodaemon server
```

`adb.exe -a nodaemon server` chạy ở foreground, giữ `cmd.exe` sống mãi và print liên tục toàn bộ USB transport trace log cho ~80 Galaxy S7:
- `read/write thread spawning`
- `fetching keys ... Calling send_auth_response`
- `offline` → `device` (cho mỗi máy)

User thấy cửa sổ đen nhảy chữ liên tục và hỏi _"nhảy lung tung gì thế"_. Bấm X = kill ADB = rớt toàn bộ farm.

## Giải pháp: VBScript SW_HIDE Wrapper

### Bước 1 — Tạo file `C:\Taadaa_Service\start_admin_adb.vbs`
```vbscript
Option Explicit
Dim objShell, adbPath
Set objShell = CreateObject("WScript.Shell")
adbPath = "C:\Program Files (x86)\xiaowei\tools\adb.exe"

' Kiểm tra cổng 5037 đã lắng nghe chưa (lệnh netstat chạy ẩn)
Dim checkResult
checkResult = objShell.Run("cmd.exe /c netstat -ano | findstr ""0.0.0.0:5037"" | findstr ""LISTENING""", 0, True)
If checkResult = 0 Then
    WScript.Quit 0  ' ADB đang chạy, không làm gì
End If

' Kill server cũ (ẩn hoàn toàn)
objShell.Run """" & adbPath & """ kill-server", 0, True

' Khởi động ADB server mới — SW_HIDE (0), không chờ (False)
objShell.Run """" & adbPath & """ -a nodaemon server", 0, False

Set objShell = Nothing
```

### Bước 2 — Cập nhật Task Scheduler (chạy từ máy Admin hoặc qua SSH)
```powershell
# Cập nhật action của task hiện tại
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument """C:\Taadaa_Service\start_admin_adb.vbs"""
Set-ScheduledTask -TaskName "Taadaa_ADB_User_Remote" -Action $action
```

Hoặc qua SSH từ Kibe:
```bash
ssh admin-farm 'powershell -Command "
$action = New-ScheduledTaskAction -Execute \"wscript.exe\" -Argument \"\\\"\C:\Taadaa_Service\start_admin_adb.vbs\\\"\"
Set-ScheduledTask -TaskName Taadaa_ADB_User_Remote -Action \$action
"'
```

### Bước 3 — Kill ADB hiện tại và restart ẩn (< 3 giây mất kết nối)
Từ Kibe qua SSH:
```bash
ssh admin-farm 'powershell -Command "
Stop-Process -Id 15868 -Force -ErrorAction SilentlyContinue
Start-Sleep 1
wscript.exe \"C:\Taadaa_Service\start_admin_adb.vbs\"
"'
```

## Kết quả sau khi áp dụng
- ✅ Không có cửa sổ cmd/conhost nào hiện trên màn hình Admin
- ✅ ADB server vẫn lắng nghe `0.0.0.0:5037` cho Hermes (từ Kibe) và Cửu Vệ (local)
- ✅ ~80 máy S7 reconnect tự động trong ~3-5 giây
- ✅ Task Scheduler vẫn chạy đúng khi reboot (trigger OnLogon)

## Lưu ý quan trọng
- `wscript.exe` là GUI subsystem binary → **không bao giờ cấp phát console window**
- Ngược lại `powershell.exe -WindowStyle Hidden`: vẫn tạo console window 50-200ms → conhost flash
- `adb.exe -a nodaemon server` phải chạy **không có window**, không có `wait=True`, vì nó không bao giờ thoát (infinite loop listen)
- Đừng nhầm với `adb start-server` (ADB tự fork daemon, gọi xong là xong)

## Kiểm tra sức khỏe sau khi áp dụng
```bash
# Từ Kibe - kiểm tra port 5037 vẫn được lắng nghe
ssh admin-farm 'netstat -ano | findstr "0.0.0.0:5037"'

# Kiểm tra thiết bị vẫn online
python D:/Taadaa/tools/remote_admin_adb.py devices
```
