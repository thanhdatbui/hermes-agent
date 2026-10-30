# Night 2FA Watchdog Trace Observability & Anti-Hallucination Discipline (30/10/2026)

## 1. Nguyên Tắc Cốt Lõi: Cấm Đoán Mò Khi Triệu Chứng Thiếu Trace
- **Sự cố thực tế (30/10/2026):** Khi bot watchdog báo cáo `Hoàn tất 22 | Bỏ qua 12 | Lỗi 36` (Kibe) và `Hoàn tất 37 | Bỏ qua 16 | Lỗi 35` (Admin), Coordinator đã tự ý suy diễn là do "kẹt lock với tiến trình khác" và "lỗi app Outlook trên máy S7".
- **Bị người dùng chấn chỉnh gay gắt:**
  1. **Thứ tự thực thi:** Phase 1 (Reg Gmail) kết thúc lúc 00:16 rồi mới kích hoạt Phase 2 (2FA TikTok). Hai phase chạy tuần tự, hoàn toàn không có chuyện đè lock lẫn nhau.
  2. **Hạ tầng mạng & Proxy:** Farm đã **bỏ hoàn toàn ViChanger từ tháng 9/2026** (toàn bộ chạy Wi-Fi Singbox qua MikroTik tĩnh). CẤM TUYỆT ĐỐI nhắc lại ViChanger.
  3. **Cơ chế đọc OTP Hotmail:** Đọc 100% trên PC qua **Microsoft Graph API Token** (từ `gmail_clean_v2.xlsx`) và **GPM Profile**, tuyệt đối không mở app Outlook trên thiết bị Android S7.
  4. **Không suy diễn khi thiếu log:** Nguyên nhân trước đó không điều tra được là do watchdog cũ nuốt sạch stdout và không lưu log trace ra đĩa. Mọi kết luận kỹ thuật bắt buộc phải trích xuất từ file log trace thật.

---

## 2. Kiến Trúc Observability Mới Của Watchdog (`cron_night_tiktok_2fa_watchdog.py`)
Mọi phiên chạy 2FA ban đêm bắt buộc phải tuân thủ 3 trụ cột giám sát:
1. **Lưu vết thô đầy đủ ra đĩa (Raw Runner Trace):**
   - File trace: `D:/Taadaa/reports/night_2fa_trace_{YYYY-MM-DD}.log`.
   - Ghi lại toàn bộ bảng máy và stdout/stderr của cả cụm Kibe lẫn cụm Admin (qua SSH).
2. **Bóc tách nhóm lỗi tự động (`parse_2fa_breakdown_from_text`):**
   - Trích xuất bảng kết quả: `machine | row | user | status | reason`.
   - Gom nhóm đếm số lượng từng mã lỗi thật (ví dụ: `POST_SUCCESS_VERIFICATION_FAILED`, `DEVICE_NOT_CONNECTED`, `PASSWORD_FORM_NOT_REACHED_AFTER_OTP`).
3. **Báo cáo minh bạch trên Telegram & State JSON:**
   - Tin nhắn Telegram bắt buộc đính kèm:
     * Dòng `• Lỗi chi tiết: <tổng số> (<mã_lỗi_1: N>, <mã_lỗi_2: N>...)`
     * Dòng `• Trace: D:/Taadaa/reports/night_2fa_trace_{YYYY-MM-DD}.log`
   - State JSON (`night_tiktok_2fa_state.json`) lưu đầy đủ `failure_breakdown` và `trace_path`.

---

## 3. Quy Trình Điều Tra Sự Cố 2FA Khi Nhận Báo Cáo
Khi nhận forward báo cáo 2FA ban đêm có máy lỗi (`failed > 0`):
1. **Bước 1 (Đọc Trace O(1)):** Mở file `D:/Taadaa/reports/night_2fa_trace_{YYYY-MM-DD}.log` đọc trực tiếp danh sách máy lỗi và reason code cụ thể.
2. **Bước 2 (Kiểm tra Graph API Token):** Đối với các mã lỗi liên quan đến OTP/Password (`PASSWORD_FORM_NOT_REACHED_AFTER_OTP`, `POST_SUCCESS_VERIFICATION_FAILED`), kiểm tra xem tài khoản đó trong `gmail_clean_v2.xlsx` đã có token và client_id còn hạn hay chưa.
3. **Bước 3 (Kiểm tra Device Lock/Khung giờ):** Nếu ban ngày đang trong khung giờ nuôi feed (`ROLLING_BLOCK_WINDOWS`), tuyệt đối không được kích hoạt live canary đè lock thiết bị, bảo toàn ca nuôi của farm.
