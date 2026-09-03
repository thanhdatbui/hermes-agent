# Feed Alert Deduplication & Claim Lifecycle

## Cơ chế Alert Deduplication trong Multi-Machine Feed Session

### 1. Cấu trúc Claim Key
- Hàm `_feed_session_alert_key(ctx)` tạo khóa nhận diện phiên cảnh báo:
  `session_key = f"{day}-row{row_idx}"` (ví dụ `2026-08-28-row4`).
- Thư mục lưu trữ: `D:\Taadaa\runtime\kibe\live\alert-claims\<session_key>\machine_<N>.claimed`.

### 2. Nguyên lý một cảnh báo duy nhất mỗi ca (Single Alert per Shift/Day):
- Khi một máy phát sinh lỗi và được gửi cảnh báo đến Telegram bot/nhóm alert, file `machine_<N>.claimed` được tạo với nội dung `pid=<PID>\nstatus=delivered\n`.
- Nếu batch bị restart, retry hoặc chạy tiếp sang Phiên 2 / Phiên 3 của cùng một Row trong ngày:
  - Hàm `_claim_machine_alert_once` kiểm tra nếu file `machine_<N>.claimed` đã tồn tại thì lập tức trả về `False` (bỏ qua gửi alert).
  - Mục đích: Chống spam tin nhắn trùng lặp vào nhóm Telegram khi cron kích hoạt nhiều lần hoặc khi các máy lỗi tiếp tục được re-run trong ca.

### 3. Quy trình chẩn đoán khi người dùng thắc mắc không nhận được Alert:
1. Kiểm tra thư mục `D:\Taadaa\runtime\kibe\live\alert-claims\<day>-row<row>\`.
2. Xem timestamp và mtime của file `.claimed`:
   - Nếu file `.claimed` được tạo từ đợt chạy trước đó trong ngày (ví dụ đợt chạy fail lúc 14:19), giải thích rõ cho user cơ chế deduplication đã chặn tin nhắn lặp lại ở phiên sau.
3. Nếu cần reset để nhận lại alert trong ca: Chỉ xóa file `.claimed` tương ứng của máy khi có yêu cầu kiểm tra live canary.
