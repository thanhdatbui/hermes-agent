# Watchdog Duplicate Reporting & Retention Window Pitfall

## Triệu chứng
Cron watchdog (`feed_session_watchdog.py`) gửi báo cáo lặp lại hoặc gom báo cáo của cả 2 phiên (ví dụ: Phiên 1/2 và Phiên 2/2) vào một tin nhắn gửi Telegram dù Phiên 1 trước đó đã được gửi một lần.

## Cơ chế hoạt động & Nguyên nhân gốc rễ
1. **Retention Scan Window:** Watchdog kiểm tra tất cả các thư mục ngày trong vòng 7 ngày qua (`LIVE_ROOT`) và toàn bộ các cửa sổ phiên (`SESSION_WINDOWS`) của ngày đó.
2. **State Deduplication:** Cơ chế chống gửi lặp dựa hoàn toàn vào file JSON lưu vết: `feed_session_reported.json` (key dạng `<YYYY-MM-DD>_ca<N>_phien<M>`).
3. **Nguyên nhân gửi lặp (Duplicate / Aggregated Report):**
   - **Chưa claim kịp thời (Race / Persistence Miss):** Khi Phiên 1 hoàn tất, watchdog chạy và in báo cáo Phiên 1 ra stdout để cron gateway chuyển tới Telegram. Nhưng nếu state file không được ghi/persist hoặc bị rollback/ghi đè bởi tiến trình khác, key của Phiên 1 không nằm trong `reported_sessions`.
   - **Quét gộp phiên cũ:** Đến chu kỳ kế tiếp khi Phiên 2 hoàn tất, watchdog lại duyệt qua toàn bộ `SESSION_WINDOWS`. Thấy Phiên 1 chưa có trong `feed_session_reported.json`, script tính toán lại cả Phiên 1 lẫn Phiên 2, gom cả 2 thông điệp vào mảng `messages`, dẫn đến Telegram nhận được 1 bản tin gộp chứa lại kết quả của Phiên 1.

## Quy tắc kiểm tra & xử lý (O(1) Checklist)
1. **Kiểm tra file state trực tiếp:**
   - Đường dẫn state: `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json`.
   - Đọc danh sách session của ngày hiện tại để xác nhận key đã tồn tại chưa:
     ```python
     import json
     data = json.load(open(r"D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json", encoding="utf-8"))
     today_keys = [s for s in data.get("reported_sessions", []) if "YYYY-MM-DD" in s]
     ```
2. **Kiểm tra lịch sử output của cronjob:**
   - Lịch sử file output lưu tại: `C:\Users\Kibe\AppData\Local\hermes\cron\output\<job_id>\`.
   - So khớp kích thước và các tiêu đề `📊` giữa các file `.md` đã sinh ra trong ngày.
3. **CẤM quét đĩa diện rộng để tìm nguyên nhân:**
   - Luôn nhắm thẳng vào `feed_session_reported.json` và file output trong thư mục cron của Hermes.
