# IP Circuit Breaker Rolling 48H & Watchdog Telegram Auto-Chunking

## 1. Cơ Chế IP Circuit Breaker Rolling 48H
- **Quy tắc cách ly:** Khi 1 máy dính `FOLLOW_FAILED`, IP/proxy của máy đó sẽ bị ngắt **rolling 48 tiếng** kể từ thời điểm dính nhả (`now + timedelta(hours=48)`), thay vì chỉ hết ngày `23:59:59`.
- **Logic kiểm tra (`check_ip_breaker`):**
  - Bỏ lọc cứng `target_date = today`.
  - Kiểm tra `status == 'TRIPPED'` và so sánh thời gian thực `reset_dt > now` theo múi giờ `Asia/Ho_Chi_Minh`.
  - Fail-closed: Nếu `reset_at` bị thiếu hoặc hỏng format -> mặc định chặn an toàn.
  - Trả về `(True, reason)` -> Runner trả về `CIRCUIT_BREAKER_SKIPPED` để cứu nick cùng IP.
- **Phân tách phạm vi bảo vệ:**
  - **CHỈ CẤM FOLLOW:** Cầu dao chỉ nằm trong preflight của `run_follow.py` để chặn hành vi bấm follow.
  - **NUÔI / LƯỚT FEED VẪN CHẠY BÌNH THƯỜNG:** Tiến trình lướt feed, xem video, thả tim nhẹ nhàng (`tiktok-luot nuoi acc`) vẫn chạy bình thường theo lịch để tạo hành vi người dùng thật, giúp "rửa sạch IP" và hạ nhiệt cảnh báo thuật toán TikTok.

## 2. Watchdog Telegram Auto-Chunking (Chống Lỗi HTTP 400 Bad Request)
- **Giới hạn Telegram:** Telegram giới hạn cứng 4.096 ký tự/tin nhắn. Khi farm có nhiều máy bị ngắt hoặc nhả follow, báo cáo tổng hợp Ca có thể vượt quá 4.500 - 5.500 ký tự.
- **Bộ chia nhỏ tin nhắn thông minh (`dispatch_split_reports`):**
  - Tự động tách `full_msg` thành các chunk <= 3.900 ký tự theo ngắt dòng (`splitlines(keepends=True)`).
  - Gửi tuần tự các chunk về Telegram group ID (`-5127276494` cho Follow, `-5435853713` cho Video).
  - Tuyệt đối không để exception nuốt mất báo cáo Follow khi gặp lỗi message too long.
- **Khử trùng lặp:** Khối báo cáo Cầu dao IP chỉ xuất ở cụm liên quan (Kibe/Admin), tránh lặp lại làm phình độ dài tin nhắn gấp đôi.
- **Chống Mù Thông Tin Kênh Feed (Channel Blindness & 1-Line Summary Preservation):**
  - Khi tách báo cáo 3 kênh, báo cáo Nuôi Acc (Feed) gửi về stdout cronjob tuyệt đối không được xóa trắng mục Follow và Upload.
  - Luôn giữ lại 1 dòng tóm tắt trạng thái:
    `if fl_s: f_s.append(fl_s[0])`
    `if up_s: f_s.append(up_s[0])`
    giúp người theo dõi kênh Nuôi Acc thấy ngay dòng:
    `• Follow chéo (0 lượt follow) [Module 2 (Anchor): 0 | Module 1 (Bù): 0]:`
    tránh hiểu nhầm farm bỏ quên hoặc không chạy follow.
- **Vòng Lặp Gửi Tin Cậy & Cô Lập Ngoại Lệ (Isolated Retry Dispatch):**
  - Bọc `try...except` độc lập cho từng kênh (`cid`) để lỗi ở kênh Follow không nuốt mất kênh Video.
  - Thiết lập vòng lặp retry 3 lần, tăng `timeout=15s` kèm backoff `time.sleep(2)`.
  - In cảnh báo ra `sys.stderr.write()` khi gửi thất bại để cron bắt được lỗi, cấm `except Exception: logger.warning()` nuốt mất dấu vết.

## 3. Thẩm Định Độc Lập Sol High & Khóa Cứng Fail-Closed
- Advisor Sol ChatGPT-Web Pool (port 20129, 115 tài khoản):
  - Model ID chuẩn: `gpt-web-sol`.
  - Khóa cứng qua client `D:/Taadaa/tools/consult_advisor.py`, streaming 45s, zero-fallback, fail-closed ném `AdvisorUnavailable`.
  - CẤM TUYỆT ĐỐI fallback sang Gemini/Luna hoặc mạo danh Advisor.
