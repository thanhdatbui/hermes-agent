# Continuous Rolling 2FA TikTok & Anti-Legacy-Ca4 Deadlock (2026-10-15)

## 1. Bối cảnh: Lịch Farm 3 Ca x 2 Phiên (Bỏ Ca 4 Đêm)
- Farm vận hành theo chu kỳ 4 ngày, 3 Ca x 2 Phiên:
  * Ca 1: 06:00, 08:00 (kết thúc trước 09:30)
  * Ca 2: 12:00, 14:00 (kết thúc trước 15:30)
  * Ca 3: 18:00, 20:00 (kết thúc trước 21:15)
- Đã bỏ hoàn toàn Ca 4 đêm (00:00 - 05:30).
- Hiện trạng thiếu 2FA:
  * Farm Kibe: thiếu 117 acc (523/640 có 2FA).
  * Farm Admin: thiếu 592 acc (34/626 có 2FA).
- Cửa sổ rảnh rỗi phục vụ cuốn chiếu 2FA:
  * Cửa sổ đêm: 21:30 → 04:00 (6.5 tiếng).
  * Cửa sổ sáng: 09:30 → 11:45 (2 tiếng 15 phút).
  * Cửa sổ chiều: 15:30 → 17:45 (2 tiếng 15 phút).

## 2. Tử Huyệt Deadlock Tàn Dư Ca 4 (`is_ca4_finished`)
- **Triệu chứng:** Watchdog 2FA đêm (`cron_night_tiktok_2fa_watchdog.py`) không bao giờ kích hoạt, state file vắng bóng.
- **Nguyên nhân:** Lệnh kiểm tra `is_ca4_finished(today_str)` kiểm tra session `ca4_phien2` trong `feed_session_reported.json`. Do Ca 4 đã bị xoá, session này không bao giờ tồn tại, dẫn đến watchdog exit 0 âm thầm mọi tick.
- **Khắc phục:** Loại bỏ điều kiện `is_ca4_finished`. Chuyển sang cơ chế Dynamic Guard:
  * Kiểm tra `not is_feed_runner_active()` (không có tiến trình feed).
  * Cách ca nuôi kế tiếp tối thiểu 30 phút.
  * Máy không bị vướng active `device_lock`.

## 3. Kiến Trúc Vận Hành Cuốn Chiếu & Báo Cáo Định Kỳ
- **Worker pool an toàn:** Không spawn 40 workers cùng lúc (gây nghẽn OneDrive workbook lock). Chạy cuốn chiếu 10-15 workers/lượt.
- **Báo cáo định kỳ:** Chuyển sang chu kỳ 6h (00:00, 06:00, 12:00, 18:00) hoặc 12h, báo cáo tổng thể tiến độ toàn farm, số lượng mới làm được, và danh sách máy lỗi thật.
- Khi toàn farm hoàn tất 100% 2FA: Bắn báo cáo nghiệm thu và tự động chuyển sang chế độ im lặng.
