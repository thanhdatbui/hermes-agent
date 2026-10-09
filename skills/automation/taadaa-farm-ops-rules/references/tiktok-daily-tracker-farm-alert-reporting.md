# TikTok Daily Tracker & Farm Alert Reporting Pattern

## Bối cảnh & Mục đích
- Cron job `daily-tiktok-farm-tracker` (`cron_tiktok_daily_tracker.py`, chạy lúc 07:00 sáng hàng ngày) quét trạng thái tất cả tài khoản TikTok trên farm từ `taikhoan_run_safe.xlsx`.
- Kết quả quét được ghi nhận vào SQLite snapshot (`D:/Taadaa/data/tiktok_tracker.db`) và xuất file Excel chi tiết (`D:/Taadaa/reports/tiktok_tracker_report.xlsx`).

## Quy tắc Báo Cáo về Farm Alert (`telegram:-5373649734`)
1. **Target Deliver:**
   - Bắt buộc cấu hình deliver của cronjob là `deliver: "telegram:-5373649734"` (thay vì để mặc định `origin` chỉ gửi về DM cá nhân).

2. **Cấu trúc Báo cáo (Tối đa <= 1024 ký tự):**
   - **Header:** `📊 [FARM ALERT] BÁO CÁO TRẠNG THÁI TIKTOK (DD/MM/YYYY HH:MM)`.
   - **Tổng quan:** Tổng nick quét, số nick LIVE, số nick DIE/NOT FOUND, số nick ERROR, tổng Follower toàn farm.
   - **Danh sách Nick DIE / NOT FOUND:**
     - Không chỉ báo con số tổng, BẮT BUỘC liệt kê cụ thể: `Máy <N> | @<username> (<status>)`.
     - Nếu số nick die vượt quá 15: Liệt kê top 15 và tóm tắt `... và còn N nick khác (xem chi tiết trong file Excel report)`.
   - **Danh sách Nick Cắn Đề Xuất (Trending):**
     - Tiêu chuẩn trending: `follower_delta >= 10` hoặc `heart_delta >= 50` so với snapshot trước.
     - Liệt kê cụ thể: `Máy <N> | @<username>: +<f_delta> fl, +<h_delta> like (Tổng: <total_fl> fl)`.

3. **Cơ chế Wrapper & Silent Cron:**
   - Wrapper trích xuất marker `========================================` để chỉ lấy phần summary cuối cùng in ra stdout.
   - Script chạy dưới dạng `no_agent=True` trong Hermes Cron để stdout tự động được chuyển tiếp tới Telegram Farm Alert.
