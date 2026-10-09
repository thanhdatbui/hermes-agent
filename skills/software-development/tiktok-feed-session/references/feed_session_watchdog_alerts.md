# Feed Session Watchdog & Farm Alert Gate

File script watchdog: `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py`

## 1. Mục đích & Chu kỳ vận hành
- Chạy theo định kỳ giám sát các ca nuôi TikTok trên Farm (4 Ca / ngày: Ca 1 06:00, Ca 2 12:00, Ca 3 18:00, Ca 4 00:00).
- Chốt báo cáo ca nuôi tổng hợp cả 3 khâu: Lướt Feed, Follow hook, Upload hook.

## 2. Farm Alert Gate (>10 máy lỗi)
- **Mục tiêu**: Kịp thời cảnh báo khẩn cấp lên kênh Telegram Farm Alert khi phát hiện sự cố diện rộng.
- **Ngưỡng kích hoạt**:
  - `feed_fail_cnt > 10` (Lỗi lướt Feed trên 10 máy)
  - HOẶC `follow_err_cnt > 10` (Follow hook lỗi UI/xác minh trên 10 máy)
  - HOẶC `up_err_cnt > 10` (Upload hook lỗi script/xác minh trên 10 máy)
- **Target Chat**: Telegram Farm Alert Group (`chat_id = "-5373649734"`).
- **Cấu hình Token**: Tự động lấy từ `os.environ["TELEGRAM_BOT_TOKEN"]` hoặc fallback đọc từ file `~AppData/Local/hermes/.env`.
- **Định dạng thông báo**: HTML tiêu chuẩn, liệt kê rõ tên ca, Row, tổng số máy và danh sách máy gặp lỗi ở từng khâu để Coordinator xử lý hiện trường.
