# Quy tắc phân luồng và định dạng Báo cáo Nuôi acc TikTok (Cron Watchdog)

## 1. Phân luồng kênh Telegram theo đúng nghiệp vụ (User directive 2026-10-09)
Báo cáo tổng kết ca nuôi TikTok (khi hoàn tất phiên) trong `feed_session_watchdog.py` không được gộp chung một tin, mà bắt buộc bóc tách thành 3 luồng độc lập gửi về 3 nhóm riêng biệt:

1. **Lướt Feed:**
   - **Kênh:** `tiktok luot nuoi acc` (`chat_id = -5377611430`).
   - **Cơ chế giao:** In ra `stdout` qua `print(feed_msg)` để cron runtime Hermes (`deliver: telegram:-5377611430`) tự động giao.
   - **Nội dung:** Thông tin cụm máy, tổng máy xử lý, số máy thành công, máy lỗi mạng/app, tỷ lệ thả tim, đọc comment, chế độ dưỡng sinh (Organic Rest).

2. **Follow chéo:**
   - **Kênh:** `tiktok follow` (`chat_id = -5127276494`).
   - **Cơ chế giao:** Bắn trực tiếp qua Telegram Bot API (`https://api.telegram.org/bot<TOKEN>/sendMessage`).
   - **Nội dung:** Số lượt follow hoàn thành, nhóm máy Khỏe / Hồi phục, đối soát TikTok Web, danh sách nhả follow, lỗi script/xác minh, bỏ qua.

3. **Đăng Video (Upload clip):**
   - **Kênh:** `tiktok video` (`chat_id = -5435853713`).
   - **Cơ chế giao:** Bắn trực tiếp qua Telegram Bot API (`https://api.telegram.org/bot<TOKEN>/sendMessage`).
   - **Nội dung:** Số lượng video đã đăng, danh sách máy thành công, timeout/quá giờ, lỗi script upload, máy hết video cần cào thêm, bỏ qua.

---

## 2. Quy tắc Farm Alert độc lập & Metadata Ca / Row (BẮT BUỘC)

### Ngưỡng kích hoạt Farm Alert
- Ngưỡng mặc định: `DEFAULT_FARM_ALERT_THRESHOLD = 8` (khi $\ge 8$ máy ~ 10% quy mô cụm bị lỗi script của nghiệp vụ đó).

### Bóc tách Alert độc lập (Không lây nhiễm chéo)
- **Quy tắc:** Lỗi nghiệp vụ nào thì **chỉ kênh đó kích hoạt FARM ALERT**, các kênh khác giữ báo cáo trạng thái hoàn tất bình thường.
- **Ví dụ:** Khi có 14 máy dính lỗi script Upload:
  - Kênh **Upload** (`-5435853713`): Bật header `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT UPLOAD HÀNG LOẠT (14 máy lỗi script Upload) - {win_name} (Row {active_row})`.
  - Kênh **Lướt Feed** (`-5377611430`): Giữ nguyên `📊 [TIKTOK NUÔI ACC] {win_name} hoàn tất (Row {active_row})`.
  - Kênh **Follow** (`-5127276494`): Giữ nguyên `📊 [TIKTOK FOLLOW] {win_name} hoàn tất (Row {active_row})`.

### Bắt buộc đầy đủ Metadata Ca & Row
Mọi tiêu đề báo cáo và Farm Alert bắt buộc phải đính kèm đầy đủ tên Ca và số thứ tự Row đang chạy:
- `{win_name} (Row {active_row})`
- *Ví dụ chuẩn:* `Ca 1 - Phiên 1/2 (Sáng) (Row 1)` hoặc `Ca 2 - Phiên 2/2 (Trưa) (Row 4)`.

---

## 3. Telemetry & Xử lý ngoại lệ khi Dispatch
- **Telemetry logging:** Bắt buộc ghi log có cấu trúc khi dispatch thành công hoặc thất bại:
  - Thành công: `logger.info("[WATCHDOG_TELEGRAM_DISPATCH_SUCCESS] chat_id=%s hdr=%s", cid, hdr)`
  - Thất bại: `logger.warning("[WATCHDOG_TELEGRAM_DISPATCH_FAIL] err=%s", exc)`
- **Graceful degradation:** Lỗi mạng khi gửi tin nhánh phụ (Follow / Upload) không được làm crash toàn bộ tiến trình ghi nhận trạng thái của Watchdog (vẫn bảo toàn state và trả về Feed message để stdout cron giao).
