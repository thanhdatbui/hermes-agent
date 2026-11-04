# ChatGPT Web Pool Auto-Feed Stagnation & Candidate Rolling Cooldown

## 1. Triệu chứng & Bệnh lý (Infinite Stagnation Loop)
Khi cronjob định kỳ cấp cứu / hồi sinh tài khoản Web (`cron_auto_feed_chatgpt_pool.py`) chạy tự động:
- Nếu logic chọn ứng viên (`get_dynamic_candidates()`) là **stateless** (chỉ query `Profiles` từ GPM và lọc `email not in active_emails`):
- Khi top 10 tài khoản đầu tiên bị lỗi cứng (ví dụ: văng session Google Auth, chuyển hướng về `accounts.google.com/v3/signin/identifier`):
- Ở mỗi tick tiếp theo (mỗi 15 phút), vì 10 tài khoản này vẫn chưa active trong OmniRoute, **hàm lại tiếp tục bốc đúng 10 tài khoản lỗi đó ra thử lại**.
- **Hậu quả:** Cron kẹt trong vòng lặp vô tận, đốt CPU/RAM mở profile vô ích, bỏ rơi hàng trăm tài khoản khỏe mạnh phía sau (Hotmail/Gmail khác) không bao giờ được chạm tới, và không có cảnh báo Telegram để người vận hành xử lý tay.

---

## 2. Kiến trúc Khắc phục Chuẩn (Rolling Cooldown & Dead-End Telemetry)

### A. Cơ chế Rolling Cooldown 12h (`failed_candidates_cooldown.json`)
1. **Lưu vết thất bại:** Khi một tài khoản thất bại trong chu kỳ nạp:
   - Ghi nhận vào state file: `{ "email": <timestamp> }`.
2. **Loại trừ động:** Trong `get_dynamic_candidates()`:
   - Tính `now - failed_at`. Nếu còn trong khoảng cooldown (12 giờ), **bỏ qua tài khoản này** trong lượt chọn hiện tại.
   - Nhờ vậy, 5 workers sẽ **cuốn chiếu liên tục qua toàn bộ danh sách tài khoản còn lại trong kho**.
3. **Giải phóng khi thành công:**
   - Ngay khi tài khoản được nạp token và kết nối thành công vào OmniRoute, tự động xóa email đó khỏi danh sách cooldown.

### B. Ưu tiên Nguồn Tài khoản Độc lập (Hotmail vs Gmail)
- Tài khoản Hotmail thường đăng nhập trực tiếp bằng cookie/session độc lập, ít bị dính màn hình Google SSO identifier.
- Luôn xếp thứ tự ưu tiên: `cand_h + cand_g` (Hotmail trước, Gmail sau) để tối đa hóa tỷ lệ nạp tự động thành công.

### C. Báo cáo Tóm tắt & Cảnh báo Kẹt về Telegram
- Sau khi hoàn thành batch xử lý, nếu có tài khoản thất bại:
  - Tự động gom danh sách các tài khoản kẹt kèm thông điệp lỗi ngắn gọn.
  - Gửi thông báo về Telegram channel quản lý (`-5256944036` hoặc kênh tương ứng) thông qua module `telegram_report.send_telegram_msg`.
  - Giúp người vận hành biết chính xác tài khoản nào cần mở GPM đăng nhập tay lại session.
