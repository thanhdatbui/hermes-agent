# Chi Tiết Vận Hành Quét Windows Defender & Lên Lịch Task Scheduler 2 Máy

## 1. Bản Đồ Máy Mục Tiêu
- **Máy Local (Kibe):** Windows 10, đường dẫn `C:\Program Files\Windows Defender\MpCmdRun.exe`.
- **Máy Remote (Admin-farm):** Windows 10/11, IP `192.168.110.119`, kết nối qua SSH OpenSSH key `admin-farm`.

## 2. Script Tự Động Hóa Chuẩn (`D:/Taadaa/tools/cron_windows_defender_scan.py`)
Script chạy song song 2 luồng qua `ThreadPoolExecutor`:
- Cập nhật mẫu nhận diện mới nhất (`-SignatureUpdate`) trên cả 2 máy.
- Chạy quét nhanh (`-Scan -ScanType 1`) trên cả 2 máy.
- Bắt kết quả:
  - Exit code `0`: Hoàn tất, 0 threat.
  - Exit code `2`: Có threat phát hiện, raise alert.

## 3. Quản Lý Tiến Trình Tránh Kẹt Mutex
- Windows Defender chỉ cho phép 1 scan engine chạy cùng lúc.
- Lệnh kiểm tra và diệt tiến trình quét mồ côi trên Admin:
  ```cmd
  ssh -o ConnectTimeout=5 admin-farm "tasklist | findstr MpCmdRun"
  ssh -o ConnectTimeout=5 admin-farm "taskkill /F /PID <pid>"
  ```

## 4. Đăng Ký Windows Task Scheduler Hệ Thống
```cmd
schtasks /Create /TN "WeeklyWindowsDefenderScan" /TR "python D:\Taadaa\tools\cron_windows_defender_scan.py" /SC WEEKLY /D SUN /ST 03:30 /F
```
Kiểm tra trạng thái:
```cmd
schtasks /Query /TN "WeeklyWindowsDefenderScan" /FO LIST /V
```
