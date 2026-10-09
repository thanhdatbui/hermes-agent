# Quy tắc đồng bộ 3 chiều Cron Scripts & Tránh xung đột Git ↔ OneDrive Shared

## 1. Cấu trúc đồng bộ Cron Farm (3 Điểm cốt lõi)
Hệ thống cron watchdog trên Farm phân tán giữa hai host (`kibe` và `admin`) và đồng bộ qua 3 vị trí:
1. **Git Deploy Repo:** `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`
2. **Hermes Runtime Cục bộ:** `C:\Users\Kibe\AppData\Local\hermes\scripts\` (hoặc profile tương ứng)
3. **OneDrive Sync Shared (Cơ chế đồng bộ thời gian thực cho Farm):** `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`

## 2. Bài học xung đột khi sửa Watchdog/Cron Scripts
- **Nguy cơ desync giữa Git và OneDrive:**
  - Nếu một bên (ví dụ: `admin`) sửa script trên nhánh Git nhưng **chưa chạy sync** lên OneDrive Sync Shared, trong khi bên kia (`kibe`) sửa trực tiếp hoặc chạy sync cục bộ, bản trên OneDrive có thể ghi đè làm mất commit mới từ Git, hoặc Git push bị reject.
- **Quy tắc xử lý bắt buộc (Integration Checklist):**
  1. **Kiểm tra Git commit mới nhất trên remote trước khi chốt:**
     - Dùng API / git log kiểm tra commit mới nhất trên nhánh deploy của repo (`thanhdatbui/hermes-agent`).
     - Đọc kỹ diff/patch của commit vừa push xem có chạm vào cùng file script hay logic liên quan không.
  2. **Hợp nhất tính năng (Merge Invariants, Không làm mất cải tiến của nhau):**
     - Giữ nguyên cả logic cải tiến của bên đối tác (ví dụ: Admin chặn báo cáo 100% ảo khi chưa gán nick: `total == 0` -> `chưa gán nick (0/80 acc)`).
     - Kết hợp cùng tính năng mới của mình (ví dụ: hiển thị chi tiết `Đã có / Tổng (%)` và danh sách thiếu).
     - Giữ alias hàm cũ để bảo toàn tương thích ngược cho cả hai bên caller (`get_unuploaded_machines` và `get_tik_avatar_status`).
  3. **Đồng bộ ép buộc (Force Sync) lên OneDrive Sync Shared:**
     - Ngay sau khi verify test, BẮT BUỘC copy file sang `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\` hoặc chạy trigger `cron_sync_watchdog.py`.
     - Tuyệt đối không để xảy ra tình trạng code đã sửa trên máy nhưng OneDrive Shared vẫn lưu bản cũ hoặc ngược lại.
