# GPM Profile Lifecycle & Watchdog Unblocking Guide

## 1. Hiện tượng nghẽn Watchdog GPM khi Farm có nhiều IP
- **Triệu chứng**: Watchdog ca tối (`post_evening_gpm_login_watchdog.py`) báo cáo hoàn tất ca chỉ với vài máy (ví dụ: `✓ 0 | ✗ 3 | proxy_limit 2/port/ngày`), trong khi farm có hàng chục port proxy 4G.
- **Nguyên nhân cốt lõi**:
  1. **Thiếu Profile GPM**: Watchdog chỉ duyệt các tài khoản đã có sẵn trong `profile_data.db` (để tránh lỗi `PROFILE_NOT_FOUND`). Trên Master Excel có 227 acc nhưng trong GPM chỉ có ~90 profile. Hơn 130 máy bị bỏ qua ngay lập tức.
  2. **Trần Proxy Rate-Limit**: Mỗi proxy port bị giới hạn `MAX_LOGINS_PER_PROXY = 2/ngày`. Nếu các port của vài profile có sẵn đã chạm mốc 2 lần, watchdog sẽ không còn candidate nào để chạy tiếp.

## 2. Giải pháp Đồng bộ Vòng đời Profile GPM 2 Chiều (Lifecycle Sync)

### A. Tự động tạo Profile cho Gmail LIVE mới (Auto Create LIVE)
- **Nguồn dữ liệu**:
  - Trạng thái `LIVE` từ `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`).
  - Proxy chuẩn từ `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (sheet `Proxy`).
  - Trạng thái thiết bị S7 thật: Phải đang online ADB (`adb devices`).
- **Quy tắc an toàn Farm**:
  - Loại trừ 100% tài khoản có recovery hoặc email dính chuỗi `khoale`.
  - Loại trừ tài khoản trong `omniroute_success`, `excluded_khoalee`, `wrong_password_or_checkpoint` tại `oauth_pipeline_status.json`.
- **Gọi API v3 GPMLogin**:
  - Endpoint: `POST http://127.0.0.1:19995/api/v3/profiles/create`
  - Payload:
    ```json
    {
      "profile_name": "{mid:02d} - {email} - {port}",
      "raw_proxy": "test.taadaa.click:{port}:user:pass",
      "group_id": 1,
      "browser_type": "Chrome"
    }
    ```
  - Rate limit: Sleep 1.5s giữa các lần tạo profile để chống nghẽn API.

### B. Tự động dọn dẹp Profile khi Gmail DIE (Auto Clean DIE)
- **Nguồn dữ liệu**: Các tài khoản có trạng thái `DIE`, `BAN`, `SUSPENDED` trên `master_gmail_manager.xlsx`.
- **Hành động**:
  - Tra cứu ID profile trong SQLite `profile_data.db`.
  - Gọi API xóa triệt để:
    `GET http://127.0.0.1:19995/api/v3/profiles/delete/{profile_id}?mode=2`
  - `mode=2`: Xóa profile trong DB và xóa toàn bộ thư mục dữ liệu trình duyệt trên ổ cứng, giải phóng dung lượng đĩa và chống phình database.

## 3. Tự động hóa qua Watchdog Cron
- Script thực thi: `D:\Taadaa\GPM auto\scripts\sync_gpm_lifecycle.py`
- Lịch Cron: Chạy mỗi 4 tiếng (`0 */4 * * *`) ở chế độ `no_agent=True` để tự động dọn DIE và tạo LIVE liên tục, đảm bảo kho profile GPM luôn sạch và sẵn sàng cho các ca chạy login.
