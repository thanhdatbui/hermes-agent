# Case Cron Watchdog Silent-by-Default & Anti-Duplicate-Spam

## Bối cảnh & Hiện tượng
1. **Lỗi báo đúp (Duplicate Farm Alert):**
   - Watchdog `post_evening_avatar_watchdog.py` vừa gọi trực tiếp hàm `send_farm_alert(report_msg)` (qua Telegram Bot API) vừa gọi `print(report_msg)` ra stdout.
   - Do cron job được cấu hình `no_agent: True` và `deliver: telegram:-5373649734`, Hermes scheduler tự động bắt toàn bộ `stdout` để gửi tin nhắn.
   - Hậu quả: Nhóm Farm Alert nhận 2 tin nhắn y hệt nhau liên tiếp trong cùng 1 phút.
2. **Lỗi spam template rỗng (Empty Report Spam):**
   - Watchdog `post_morning_gmail_2fa_watchdog.py` chạy định kỳ mỗi 5 phút (`*/5 8,9,10,11 * * *`).
   - Khi không có máy nào đủ điều kiện hoặc danh sách máy online rỗng, script vẫn `print` template rỗng:
     ```text
     [BÁO CÁO 2FA GMAIL SAU CA SÁNG]
     - Thời gian: 09:20 -> 09:20 (0.1 phút)
     - Tổng máy đủ điều kiện: 0
     - Success (S): []
     - Fail (F): []
     ```
   - Hậu quả: Hermes scheduler coi stdout là có nội dung và gửi tin nhắn vào group liên tục mỗi 5 phút làm ngập nhóm và gây bức xúc cho user.

## Nguyên tắc Thiết kế Bất biến cho Cron Watchdog (no_agent=True)
1. **Stdout là Kênh Gửi Duy Nhất (Single Delivery Channel):**
   - TUYỆT ĐỐI KHÔNG vừa gọi API Telegram thủ công (`send_farm_alert`) vừa `print()` nội dung báo cáo ra stdout trong script no_agent.
   - Chuẩn hóa: Chỉ dùng `print()` ra stdout để Hermes Cron Scheduler tự động deliver vào target Telegram đã cấu hình.
2. **Silent-by-Default khi Không Có Kết Quả (Zero-Item Silent):**
   - Khi `total_eligible == 0` hoặc danh sách xử lý rỗng: script BẮT BUỘC thoát im lặng (exit 0 và KHÔNG in gì ra stdout).
   - Mọi log trung gian kiểm tra điều kiện phải dùng `sys.stderr.write()` hoặc ghi file log, TUYỆT ĐỐI KHÔNG in ra stdout.
   - Chỉ `print()` duy nhất 1 lần khi có kết quả thực tế (`len(success) > 0` hoặc `len(fail) > 0`) hoặc khi chốt giờ kết thúc ca.
3. **Idempotency & Session Locking:**
   - Mỗi ca chỉ được báo cáo 1 lần duy nhất (`last_reported_session = today_str`).
   - Sau khi báo cáo thành công, lưu state ngay lập tức để các lần tick sau (mỗi 5-10 phút) kiểm tra thấy `already_reported` sẽ thoát im lặng ngay từ đầu hàm `main()`.

## Bẫy StreamHandler(sys.stdout) Tuồn Log Thô & Telegram Chunking Spam (Bài Học 02/10/2026)
1. **Hiện tượng:**
   - Script nuôi tài khoản (như `cron_gpm_gmail_nurture.py`) cấu hình `logging.basicConfig` với `logging.StreamHandler(sys.stdout)`.
   - Khi chạy qua Cronjob `no_agent: True` gửi về Telegram, toàn bộ log chi tiết (từng giây xem video YouTube, kết nối Playwright CDP, JSON metric...) hơn 15KB bị tuồn sạch ra `sys.stdout`.
   - Telegram Adapter tự động xé nhỏ tin nhắn vượt ngưỡng 4096 ký tự thành 5 tin nhắn phân trang `(1/5)` đến `(5/5)` bắn tới tấp vào Telegram làm spam nghiêm trọng.
2. **Quy tắc Bất biến:**
   - **CẤM TUYỆT ĐỐI `StreamHandler(sys.stdout)`**: Mọi log vận hành, debug, telemetry BẮT BUỘC ghi vào `RotatingFileHandler(LOG_FILE)` trên đĩa.
   - **Chỉ xuất console qua `sys.stderr`**: Nếu cần hiển thị khi chạy tay, chỉ dùng `logging.StreamHandler(sys.stderr)` vì scheduler cron của Hermes KHÔNG deliver `stderr` vào Telegram khi script exit 0.
   - **Silent on 100% Success**: Khi toàn bộ task/acc hoàn thành thành công, `sys.stdout` BẮT BUỘC rỗng 100% để Hermes im lặng tuyệt đối. Chỉ `print` duy nhất 1 dòng cảnh báo ngắn gọn $\le$ 160 ký tự khi có tài khoản hoặc thiết bị gặp lỗi thực sự.
