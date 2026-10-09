# Standalone Night Chain Cron vs Feed Runner Hooks & Quy Trình Chẩn Đoán Khi Tắt Reg

## 1. Bản chất kiến trúc: 2 luồng hoàn toàn độc lập
Hệ thống farm có 2 cơ chế chạy đăng ký tài khoản (Reg Gmail / TikTok) có vòng đời hoàn toàn tách biệt:

| Tiêu chí | Feed Runner Preflight / Inline Hook | Hermes Standalone Night Chain Cron |
|---|---|---|
| **Bộ kích hoạt (Trigger)** | `tiktok_runner.py` (ăn theo các khung giờ Ca 1, 2, 3, 4) | Hermes Cron Scheduler (Job ID `38ea60c09825`, lịch `0 1 * * *`) |
| **Mục đích** | Bù tài khoản thiếu trực tiếp vào Row đang nuôi | Chạy chuỗi ban đêm: Reg Gmail -> Reg TikTok -> Bật 2FA |
| **File thực thi** | `D:\Taadaa\tools\ensure_row_accounts.py` | `night_chain_reg_pipeline_launcher.py` -> `run_night_chain_pipeline.py` |
| **Kênh báo cáo** | Báo cáo theo phiên nuôi / Watchdog feed | Tin nhắn Cron Telegram riêng (`telegram:-5139245637` hoặc DM) |

## 2. Điểm mù thực tế (Pitfall)
- Khi người vận hành yêu cầu hoặc đã sửa code "bỏ reg sau ca cuối", họ thường ngầm hiểu là hệ thống sẽ ngừng toàn bộ các hoạt động reg tự động.
- Tuy nhiên, việc sửa/bỏ hook trong `tiktok_runner.py` (hoặc sau ca cuối) **không hề ảnh hưởng** tới `night-chain-reg-pipeline` trong Hermes Scheduler. Cronjob này vẫn đều đặn thức dậy lúc 01:00 AM để chạy chuỗi reg.
- Khi báo cáo chuỗi đêm nổ lên lúc 01:00 -> 02:00, người vận hành sẽ tưởng nhầm code sửa chưa có hiệu lực hoặc feed ca cuối vẫn tự kích hoạt reg.

## 3. Quy trình chẩn đoán O(1) & Xử lý chuẩn
1. **Truy vết nguồn gốc qua `job_id`:**
   - Khi nhận khiếu nại kèm báo cáo cron, ngay lập tức đọc `job_id` trên header tin nhắn (vd `38ea60c09825`).
   - Gọi `cronjob(action='list')` để lấy thông tin chi tiết: `name`, `schedule`, `script`, `last_run_at`.
2. **Giải thích rõ ràng cho user:**
   - Xác nhận code feed runner đã được gỡ bỏ an toàn (không bị chạy đè).
   - Chỉ rõ báo cáo đến từ standalone cronjob độc lập cố định lúc 01:00 AM chứ không phải do ca cuối kích hoạt.
3. **Đề xuất hành động tức thì:**
   - Hỏi xác nhận nếu user muốn **tắt hẳn (pause/remove)** cronjob `night-chain-reg-pipeline` qua `cronjob(action='pause', job_id='...')` hoặc giữ nguyên.
