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

4. **CẤM TUYỆT ĐỐI `logging.StreamHandler(sys.stdout)` Trong Cron Script (Bẫy Chunking Spam Telegram `(1/N)`):**
   - **Hiện tượng & Hậu quả:** Khi script dùng `logging.basicConfig(handlers=[StreamHandler(sys.stdout), ...])`, toàn bộ log runtime (từng giây xem video, Playwright kết nối CDP, telemetry JSON) bị tuồn ra `sys.stdout`. Hermes Cron Scheduler (`no_agent=True`) bắt toàn bộ 15.000+ ký tự này làm tin nhắn Telegram. Telegram Adapter tự động xé nhỏ thành các tin nhắn phân trang dạng `...(1/5)`, `...(2/5)`, ..., `(4/5)`, `(5/5)` và bắn liên hoàn vào Telegram của người dùng.
   - **Quy chuẩn bắt buộc:**
     + Trong mọi script cron/watchdog, logging CHỈ ĐƯỢC PHÉP dùng `RotatingFileHandler(LOG_FILE)`. CẤM TUYỆT ĐỐI gắn `logging.StreamHandler(sys.stdout)` vào root logger khi chạy production cron.
     + Nếu cần in console khi dev chạy tay qua terminal, chỉ bật StreamHandler khi có cờ `--verbose` hoặc kiểm tra `sys.stdout.isatty()`.

5. **Định Kỳ Nuôi Background Mặc Định Hoàn Toàn Silent (Quiet-on-Success):**
   - Với các job nuôi định kỳ chạy hàng giờ (như GPM nurture, YouTube xem video): Khi tất cả profile hoàn tất thành công (`success_count == total_count`), script BẮT BUỘC giữ `sys.stdout` rỗng để scheduler im lặng 100%.
   - CHỈ in ra stdout duy nhất 1 thông báo ngắn gọn $\le$ 160 ký tự khi có sự cố thất bại thực sự (`fail_count > 0` hoặc lỗi nền tảng nghiêm trọng).

6. **Anti-Spam Cho Preflight Reg Bù / Runner Tick Loop:**
   - Khi preflight chạy trước ca nuôi (15 phút/lần) phát hiện máy lỗi lặp lại (ví dụ máy offline liên tục, device not found), CẤM bắn summary thất bại lặp đi lặp lại ra nhóm Telegram mỗi tick.
   - Bắt buộc có cơ chế cooldown/dedup: chỉ báo lỗi 1 lần đầu tiên khi phát hiện máy lỗi mới, các tick tiếp theo nếu cùng danh sách máy và lỗi không đổi thì phải SILENT.
