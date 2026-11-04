# Tách Biệt Tuyệt Đối Giữa Cron Xử Lý Liên Tục (Silent Cron) Và Watchdog Báo Cáo Định Kỳ (Periodic Watchdog)

## 1. Bối Cảnh Sự Cố & Triệu Chứng
- **Sự cố:** Kênh Telegram (Farm Alerts / GPM Auto) bị spam tin nhắn dồn dập mỗi 15 phút (vào 6:06, 6:19, 6:23, 6:34 PM...) với các sớ báo cáo xử lý từng batch 10 tài khoản.
- **Phản ứng của User:** *"Ủa chứ t đã yêu cầu watchdog 6h 1 lần mà! Còn cron thì cứ chạy xử lý liên tục cz đc"*.
- **Nguyên nhân cốt lõi:**
  1. Worker hoặc Coordinator khi vá logic xử lý theo lô (batch rescue / auto-feed) đã tiện tay thêm lệnh dispatch Telegram (`send_telegram_report(...)`) vào cuối hàm `main()` của cron script (`cron_auto_feed_chatgpt_pool.py`).
  2. Sự nhầm lẫn giữa hai vai trò: **Tiến trình xử lý liên tục (Worker Cron)** và **Tiến trình giám sát báo cáo (Reporter/Watchdog)**.

## 2. Quy Chuẩn Phân Vai Bắt Buộc

### A. Cron Xử Lý Liên Tục (High-Frequency Silent Cron - chu kỳ 5m, 15m, 30m):
- **Nhiệm vụ:** Quét database, bóc session/token, gọi API, cập nhật proxy, đưa acc fail vào cooldown, ghi state JSON / SQLite.
- **Kỷ luật im lặng (Silent Invariant):**
  - **CẤM TUYỆT ĐỐI** gọi hàm gửi tin nhắn Telegram (`send_telegram_report`, `requests.post(telegram_api)`, `send_telegram_msg`) bên trong script cron xử lý tần suất cao.
  - Toàn bộ kết quả, metrics, lỗi từng tài khoản BẮT BUỘC chỉ ghi vào:
    - Log console / stdout.
    - File state JSON (ví dụ: `logs/batch_rescue_report.json`, `logs/failed_candidates_cooldown.json`).
    - SQLite database nội bộ.
  - Deliver của cron job này trong scheduler luôn là `local` hoặc script `no_agent=True` với stdout rỗng khi bình thường.

### B. Watchdog Giám Sát & Báo Cáo Định Kỳ (Low-Frequency Periodic Watchdog - chu kỳ 6h, 12h, 24h):
- **Nhiệm vụ:** Đọc tổng hợp dữ liệu từ file state JSON / SQLite của cả chu kỳ 6h qua, tính toán tỷ lệ tổng thể (tổng acc sống, acc chết, acc active trong pool).
- **Trách nhiệm phát tín hiệu:**
  - Chỉ có Watchdog này mới ĐƯỢC PHÉP tổng hợp và phát 1 tin nhắn duy nhất về Telegram chuyên trách theo đúng lịch hẹn (ví dụ: 0h, 6h, 12h, 18h).
  - Không gửi danh sách vụn vặt từng đợt 10 tài khoản; chỉ gửi tỷ lệ tổng thể và cảnh báo nếu toàn bộ pool cạn kiệt.

## 3. Checklist Kiểm Tra & Anti-Regression Khi Review/Patch Script Cron
1. Script này chạy ở tần suất nào? (Nếu <= 60 phút $\rightarrow$ Mặc định thuộc nhóm **Silent Cron**).
2. Cuối hàm `main()` hoặc sau vòng lặp batch có chứa bất kỳ lệnh gọi gửi Telegram nào không? (Nếu có $\rightarrow$ Xóa hoặc comment ngay).
3. Đã có file test kiểm chứng tính im lặng chưa? Bổ sung test assertion đảm bảo `send_telegram_report` hoặc `requests.post` KHÔNG được gọi khi `main()` hoàn tất.
