# Case 190: Tiến Trình Runner Zombie Kẹt Luồng Chặn Watchdog Báo Cáo Ca Nuôi (`runner_busy` Deadlock) (24/09/2026)

## 1. Hiện Tượng & Thắc Mắc Người Vận Hành
- Quá giờ ca nuôi (ví dụ: đã xong cả Ca 1 và Ca 2 lúc 16:00+) nhưng người vận hành không nhận được bất kỳ tin nhắn tổng kết phiên nào trên Telegram: *"sao t k thấy báo cáo ca nuôi acc nữa nhỉ hay là do chưa hết ca?"*.
- Kiểm tra file state `feed_session_reported.json` thấy các session key của Ca 1, Ca 2 trong ngày chưa hề được ghi nhận.

## 2. Root Cause: `runner_busy` Deadlock Do Tiến Trình Zombie
1. **Lượt chạy đã hoàn thành nhưng process không thoát:**
   - Tiến trình PowerShell (`run-feed-session.ps1`) và Python (`run_tiktok.py --mode multi-machine-feed-session`) của phiên sáng sớm (06:10, 06:29) đã chạy xong toàn bộ 80 máy lúc 08:15–08:35, artifact `run_manifest.json` và `summary.txt` đã ghi nhận trạng thái `failed`/`completed`.
   - Tuy nhiên, tiến trình chính Python giữ lại 27 worker threads hoặc kẹt ở bước dọn dẹp cuối, khiến process Python/PowerShell tồn tại vĩnh viễn ở trạng thái zombie (0% CPU, không network connection, không giữ device lock).
2. **Cơ chế phòng vệ của Watchdog bị phản tác dụng:**
   - Trong `feed_session_watchdog.py`:
     ```python
     runner_busy = is_feed_runner_active()
     ```
     Hàm `is_feed_runner_active()` quét mọi tiến trình hệ điều hành có cmdline chứa `run_tiktok.py`, `multi_machine_feed_session`, `run-feed-session.ps1`...
   - Trong `can_report_session()`:
     ```python
     if is_today and runner_busy:
         return False
     ```
   - Watchdog nhận diện `runner_busy == True`, lầm tưởng farm vẫn đang chạy dở một mẻ nuôi, nên kích hoạt cơ chế silent hold — hoãn xuất toàn bộ báo cáo trong ngày để tránh chốt phiên non.
   - Hậu quả: Dù Ca 2 (12:00–15:27) cũng đã chạy xong hoàn tất, cả 4 phiên của Ca 1 và Ca 2 đều bị phong tỏa, không thể gửi ra Telegram.

## 3. Quy Trình Chẩn Đoán O(1) & Khắc Phục Chuẩn

### Bước 1: Kiểm tra tiến trình runner đang chạy
```powershell
powershell.exe -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*run_tiktok*' -or \$_.CommandLine -like '*run-feed-session*' } | Select-Object ProcessId, CreationDate, CommandLine | Format-List"
```

### Bước 2: Đối chiếu với artifact `run_manifest.json`
Đọc `run_manifest.json` trong các thư mục `row-X-HHMMSS` tương ứng:
- Nếu `end_time` đã tồn tại từ nhiều giờ trước (ví dụ process tạo lúc 06:13, end_time là 08:15 mà hiện tại là 16:00).
- Kiểm tra tài nguyên:
```powershell
powershell.exe -Command "Get-Process -Id <PIDs> | Select-Object Id, ProcessName, CPU, TotalProcessorTime"
```
Nếu CPU không tăng (0% CPU), không kết nối mạng (`Get-NetTCPConnection`), và không có device lock active trong `~/.codex/device-locks/` -> Xác nhận 100% là zombie process.

### Bước 3: Dọn dẹp tiến trình zombie
```powershell
powershell.exe -Command "Stop-Process -Id <PIDs> -Force -ErrorAction SilentlyContinue"
```

### Bước 4: Kích hoạt Watchdog xả báo cáo
- Gọi trực tiếp hoặc chờ chu kỳ cron tiếp theo (mỗi 5 phút):
```bash
python C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py
```
- Watchdog nhận thấy `runner_busy == False`, kiểm tra `completed_expected_count`, lập tức tạo báo cáo tổng hợp và gửi toàn bộ các phiên hoàn tất vào nhóm Telegram Farm.
