# GPM Lifecycle Silent Watchdog & DIE Profile Preservation

## 1. Nguyên lý Vòng đời Profile GPM & S7 (`sync_gpm_lifecycle.py`)
- Cronjob: `gpm-lifecycle-sync-watchdog` (lịch: `*/15 7,8 * * *`, chạy chế độ `no_agent: True`).
- Mục đích: Đồng bộ giữa Master Excel (`master_gmail_manager.xlsx`) và GPMLogin Local API (`http://127.0.0.1:19995/api/v3`) + dọn tài khoản DIE trên thiết bị S7 buổi sáng (07:15 - 08:45 HCMC).

## 2. Invariant: Bảo toàn Tuyệt đối Profile GPM khi Gmail DIE
- **BỐI CẢNH**: Profile GPM của các Gmail bị DIE/BAN/SUSPENDED có thể đã được nạp tiền thuê SIM (5sim / SMS OTP) để verify số đăng ký tài khoản OpenAI / Codex, hoặc lưu session extension quan trọng.
- **QUY TẮC BẤT DI BẤT DỊCH**:
  - CẤM TUYỆT ĐỐI gửi lệnh API xóa profile GPM (`/api/v3/profiles/delete/{id}`) đối với các tài khoản Gmail DIE.
  - Vẫn đọc danh sách email trong DB GPM SQLite (`existing_gpm_emails`) để ngăn việc tạo trùng profile.
  - Khi phát hiện Gmail DIE: ghi log an toàn và emit metric telemetry `gpm_lifecycle_sync_die_skipped`.

## 3. Kiến trúc Silent Watchdog cho Cronjob no_agent=True
- Trong Hermes Agent, job có `no_agent: True` tự động gom toàn bộ nội dung `stdout` để gửi tin nhắn Telegram:
  - Nếu `stdout` có bất kỳ ký tự nào $\rightarrow$ Telegram nhận tin nhắn.
  - Nếu `stdout` rỗng $\rightarrow$ Scheduler hoàn toàn im lặng (Watchdog pattern chuẩn).
- **Thiết kế Logging chuẩn**:
  - **Mặc định**: Logger CHỈ add `FileHandler` ghi log chi tiết vào file (`D:\Taadaa\GPM auto\logs\sync_gpm_lifecycle.log`).
  - **TUYỆT ĐỐI KHÔNG** add `StreamHandler(sys.stdout)` vào logger mặc định ở cấp module (sẽ gây spam log mỗi 15 phút).
  - Cung cấp cờ CLI `-v / --verbose`: Chỉ add `StreamHandler(sys.stdout)` khi chạy debug thủ công.
  - **Báo cáo sự kiện**:
    - Khi `created_count == 0` và `cleaned_count == 0`: `stdout` hoàn toàn **RỖNG**.
    - Khi có hành động thực tế (`created_count > 0` hoặc `cleaned_count > 0`): In duy nhất 1 dòng tổng kết sạch:
      `[GPM & S7 LIFECYCLE] Tạo mới {created_count} profile LIVE | Đã dọn {cleaned_count} tài khoản DIE trên S7`

## 4. Structured Telemetry Metrics
- Mỗi sự kiện vòng đời quan trọng cần emit metric dạng JSON có cấu trúc qua hàm `log_telemetry_metric(event_type, data)`:
  - `gpm_lifecycle_sync_die_skipped`: Ghi nhận số lượng DIE được bảo vệ và lý do.
  - `gpm_lifecycle_sync_completed`: Số profile tạo mới, tổng candidates live, tổng profile hiện có.
  - `s7_cleanup_completed`: Số tài khoản DIE đã dọn trên thiết bị S7 qua rolling lock.
- Phục vụ watchdog downstream và audit scoring đạt chuẩn Closeout Gate ($\ge 85$).
