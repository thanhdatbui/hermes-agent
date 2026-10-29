# Windows HTTP Server Multi-Process Socket Collision & Cache Tuning

## 1. Tranh Chấp Socket Multi-Process Trên Windows (`SO_REUSEADDR`)
- **Triệu chứng:**
  - Người dùng truy cập dashboard (ví dụ port 1905, `tiktok_dashboard.py`) bị xoay đơ liên tục, báo `ERR_CONNECTION_TIMED_OUT` hoặc lúc vào được lúc không.
  - Phía server, lệnh curl hoặc probe cục bộ có thể trả về 200, nhưng trình duyệt người dùng bên ngoài mạng LAN hoặc trên máy vẫn báo sập.
- **Nguyên nhân gốc rễ:**
  1. **Nhiều tiến trình cùng bind vào 1 port:**
     - Trên Windows, cờ `SO_REUSEADDR` cho phép nhiều tiến trình Python (`python.exe` / `pythonw.exe`) cùng bind thành công vào cùng một port TCP (1905).
     - Khi một watchdog supervisor (ví dụ PowerShell script `tiktok_dashboard_watchdog.ps1`) thực hiện restart bằng cách kill PID sở hữu cổng (thường chỉ kill tiến trình con mà bỏ sót tiến trình cha `pythonw.exe`), hoặc khi thư mục Windows Startup có các file shortcut trùng lặp (ví dụ cả `start_tiktok_dashboard.vbs` lẫn `tiktok_dashboard_1905.vbs` cùng chạy lúc boot), hệ thống sẽ đẻ ra 2–3 tiến trình cùng lắng nghe trên port 1905.
     - Windows phân phối gói tin TCP SYN ngẫu nhiên cho một trong các tiến trình. Nếu request rơi vào tiến trình đang bị kẹt socket / treo luồng, kết nối sẽ bị treo vô hạn cho đến khi timeout.
  2. **Watchdog Restart Death Loop:**
     - Khi database SQLite (`tiktok_tracker.db`) có kích thước lớn (>130.000 dòng snapshots), một query cold aggregation mất 4–5 giây.
     - Nếu watchdog giám sát đặt timeout quá ngắn (ví dụ 8s) và thực hiện probe bằng `.NET WebRequest` bị leak connection, watchdog tưởng nhầm server chết và ra lệnh restart liên tục mỗi 60–70 giây, khiến các tiến trình mồ côi nhân bản liên tục.
- **Quy trình xử lý dứt điểm:**
  1. **Kill toàn bộ cây tiến trình:**
     - Không chỉ kill PID lắng nghe cổng. Quét toàn bộ tiến trình có commandline chứa tên script (`CommandLine -like "*tiktok_dashboard.py*"`) và kill sạch sẽ bằng `psutil` hoặc taskkill.
     - Dừng cả tiến trình watchdog bị treo: `Stop-Process -Name powershell` hoặc tìm đúng script watchdog.
  2. **Dọn dẹp Windows Startup:**
     - Kiểm tra `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\` và xóa bỏ các file `.vbs` trùng lặp khởi động cùng một dịch vụ.
  3. **Tăng Cache TTL & Nhẹ Hóa Query:**
     - Không đặt `_CACHE_TTL` quá ngắn (15s) trên các bảng dữ liệu lớn. Tăng `_CACHE_TTL >= 180s` (3 phút) để giảm thiểu số lần query nặng quét 130k snapshots trên SQLite.
  4. **Kiểm chứng đa giao diện:**
     - Kiểm tra kết nối độc lập trên cả 3 giao diện: Localhost (`127.0.0.1:1905`), LAN (`192.168.110.x:1905`) và Tailscale (`100.88.x.x:1905`).
