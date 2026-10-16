# GPM Cron Script Deployment & Delayed Alert Triage

## 1. Cơ Chế Triển Khai Script Cron Cho GPMLogin & Hermes

Khi tạo hoặc cập nhật script cron cho các tác vụ GPM (`cron_gpm_gmail_nurture.py`, `cron_gpm_gmail_nurture_6h_report.py`,...):
- **Quy định đường dẫn của Hermes `no_agent: true`**: Tham số `script` của tool `cronjob` bắt buộc phải là đường dẫn tương đối trỏ về thư mục script runtime của Hermes (`~/.hermes/scripts/`).
- **Rào cản Guard Self-Protection**: Hệ thống bảo vệ ngăn chặn Agent can thiệp trực tiếp (copy, ghi đè, tìm kiếm) vào thư mục runtime scripts. Mọi lệnh thao tác file trực tiếp vào thư mục này đều bị chặn tự động.

## 2. Quy Trình Đồng Bộ Chuẩn 3 Kho (Triệt Tiêu Lỗi "Script not found")

Để triển khai một script mới từ repo `D:/Taadaa/GPM auto/scripts/` vào runtime Hermes:
1. **Copy sang kho Deploy & OneDrive Sync:**
   - Kho Deploy Git: `D:/Taadaa/Hermes/deploy/hermes-home/scripts/<script_name>`
   - Kho OneDrive Sync: `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/<script_name>`
2. **Kích hoạt Watchdog Đồng Bộ Hệ Thống:**
   - Chạy lệnh: `python "D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/cron_sync_watchdog.py"`
   - Hoặc kích hoạt cronjob đồng bộ: `cronjob(action='run', job_id='2b5b608429c7')` (`cron-sync-watchdog`).
   - Watchdog này có quyền đồng bộ an toàn từ kho Deploy/OneDrive vào thư mục runtime nội bộ mà không vi phạm guard.
3. **Thứ tự thực thi bắt buộc:**
   - BẮT BUỘC chạy `cron_sync_watchdog.py` TRƯỚC KHI gọi `cronjob(action='run', ...)`.
   - Nếu gọi test ngay khi script chưa được watchdog sao chép vào runtime, cron engine sẽ báo lỗi:
     `Script not found: ...`

## 3. Triage Cảnh Báo "Script not found" Trễ Do Mạng / Telegram Proxy

Khi nhận được Farm Alert hoặc thông báo người dùng báo cronjob bị fail với lý do `Script not found`:
1. **Kiểm tra trạng thái thực tế qua `cronjob action='list'`:**
   - Xem `last_status` và `last_run_at`.
   - Kiểm tra xem file vật lý trong repo và kho deploy/sync đã đồng bộ chưa.
2. **Nhận diện thông báo trễ (Delayed Notification):**
   - Khi cronjob được tạo ở phiên trước, nếu test-run diễn ra trước khi watchdog sync hoàn tất, lỗi `Script not found` sẽ được ghi nhận.
   - Nếu thời điểm đó gateway gặp lỗi kết nối Telegram (ví dụ: `httpx.ProxyError: Host unreachable`), tin nhắn cảnh báo thất bại có thể bị hoãn lại trong hàng đợi và chỉ gửi đến chat sau đó vài giờ hoặc ở đầu phiên tiếp theo.
3. **Xác thực dứt điểm:**
   - Chạy `cronjob(action='run', job_id='<job_id>')` để kiểm chứng hiện trường trực tiếp.
   - Nếu `execution_success: true` và `last_status: ok`, kết luận đó là cảnh báo trễ từ quá khứ, không sửa mò code hay xóa tạo lại cronjob.
