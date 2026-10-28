# Remote Host UltraViewer Service Troubleshooting & Recovery

## Context & Symptoms
Khi máy trạm/host điều khiển farm (ví dụ `admin-farm` / `ADMIN-PC` tại `192.168.110.119`) bị mất kết nối UltraViewer hoặc người dùng báo "ultra view sập", màn hình desktop xuất hiện lỗi:
```text
Cannot Start Service: Cannot start service on computer '.'
```

## Root Cause
1. Ứng dụng GUI `UltraViewer_Desktop.exe` khi khởi động yêu cầu Windows Service `UltraViewService` chạy ở nền (`LocalSystem`, session 0).
2. Nếu `UltraViewService` bị `Disabled` hoặc `Stopped` (do tối ưu hóa nhầm service khi chống nháy màn hình, hoặc xung đột sau reboot/crash):
   - `UltraViewer_Desktop.exe` sẽ ném dialog lỗi modal và từ chối kết nối tới server UltraViewer.
   - Quá trình authen thất bại, log báo:
     `Cannot init Ultraviewerservice; error: ; InitServiceTriedAgain=False`
     `Restart service return false`

## Remote Recovery Protocol (via SSH)

### 1. Kiểm tra trạng thái Service & Process
Qua SSH kết nối tới host (`ssh -o ConnectTimeout=5 -o BatchMode=yes <host>`):
```cmd
sc query UltraViewService
powershell -Command "Get-Service *ultra* | Format-List Name, Status, StartType"
tasklist | findstr /i "ultra"
```

### 2. Khôi phục Service & Kích hoạt lại
```cmd
:: Cấu hình service tự khởi động cùng Windows
sc config UltraViewService start= auto

:: Khởi động service
sc start UltraViewService
:: Hoặc: net start UltraViewService
```

### 3. Giải phóng GUI Process bị kẹt dialog
Khi service đã khởi động, tiến trình `UltraViewer_Desktop.exe` cũ vẫn có thể đang kẹt hiển thị modal dialog "Cannot Start Service":
```cmd
taskkill /F /IM UltraViewer_Desktop.exe
```
Ngay sau khi GUI cũ bị kill, `UltraViewer_Service.exe` ở Session 0 sẽ tự động phát hiện và khởi chạy một tiến trình `UltraViewer_Desktop.exe` mới trên active console session (Session 1). Nếu không tự khởi chạy, restart lại service:
```cmd
net stop UltraViewService && net start UltraViewService
```

### 4. Đối soát & Kiểm chứng phục hồi qua Log & Registry
- **Log xác thực server (`%APPDATA%\UltraViewer\UV_Desktop_log.txt`):**
  Kiểm tra các dòng cuối cùng có:
  ```text
  TCPClient: BeforeAuthen
  TCPClient: AfterAuthen
  ```
- **Log mạng (`%APPDATA%\UltraViewer\Error_Log.txt`):**
  Xác nhận đã kết nối thành công:
  ```text
  FormLoad:FinishAllTasks
  VTCPNL: Connected
  ```
- **Tra cứu UltraViewer ID:**
  ```powershell
  (Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\UltraViewer').PreferID
  ```
