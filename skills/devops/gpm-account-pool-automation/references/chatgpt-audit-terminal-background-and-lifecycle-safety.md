# ChatGPT GPM Audit: Terminal Background Execution & Verification Lifecycle

## Context & Quirks
Khi vận hành script `login_audit_and_purge_deactivated.py` qua cron job hoặc CLI agent:
1. **Terminal Foreground Guard & Coordinator Allowlist**:
   - Môi trường Hermes agent trên máy host enforce `[GUARD_FOREGROUND_TIMEOUT_MISSING]`.
   - Các lệnh terminal foreground bắt buộc phải có tham số `timeout <= 60s`.
   - **Coordinator Guard Default-Deny**: Tuyệt đối không tự ý chạy các lệnh probe ad-hoc như `curl http://127.0.0.1:19995/...` hay `curl ...:20129` để preflight ở session chính vì sẽ bị Coordinator Guard chặn (DEFAULT-DENY). Script `login_audit_and_purge_deactivated.py` đã tự tích hợp sẵn preflight, timeout handling và fallback nội bộ; Coordinator chỉ cần gọi trực tiếp script.
   - Với quy trình audit nhiều tài khoản GPM (mỗi tài khoản mở profile, kết nối CDP, giải/lấy OTP qua Graph API hoặc Outlook webmail, kiểm tra DOM mất từ 20s - 45s mỗi tài khoản): tổng thời gian audit 5 tài khoản có thể vượt quá 60s (thường từ 120s - 180s).
   - **Quy tắc thực thi**: Bắt buộc khởi chạy script ở chế độ background `terminal(command="python D:/Taadaa/tools/login_audit_and_purge_deactivated.py --limit 5", background=True)` và điều phối bằng `process(action='wait', session_id=..., timeout=60)` theo từng cửa sổ thời gian (polling/wait loop) cho đến khi `process_running: false`.
   - **Cảnh báo Python -c inline command guard**: Tránh chạy các đoạn script inline phức tạp dạng `python -c "..."` có chứa multiline string hoặc ký tự đặc biệt vì dễ kích hoạt guard kiểm tra lifecycle script hoặc gặp lỗi `open: embedded null character in path`. Để kiểm tra DB hoặc API nội bộ, nên gọi script có sẵn hoặc truy vấn an toàn bằng urllib một dòng đơn giản.

2. **Cron Environment & Notifications**:
   - Phiên cron job / one-shot runner không hỗ trợ nhận async notification (`notify_on_complete / watch_patterns are not available in this session`).
   - Agent cần chủ động dùng `process(action='wait')` hoặc `process(action='poll')` với timeout xác định để chờ script hoàn tất thay vì dựa vào notification.

3. **UNKNOWN Status vs DEAD_DEACTIVATED**:
   - Nếu account sau khi điền OTP chưa kịp render xong marker giao diện (`New chat`, `Cuộc trò chuyện mới`) hoặc timeout khi tải webmail, kết quả trả về là `UNKNOWN`.
   - **Quy tắc an toàn**: Tuyệt đối không quy chụp `UNKNOWN` thành `DEAD_DEACTIVATED`. Chỉ thực hiện purge khi có marker xác thực cụ thể (`account_deactivated` hoặc `đã bị xóa hoặc vô hiệu hóa`) kèm ảnh chụp bằng chứng màn hình lưu vào `artifacts/`.

4. **Dọn dẹp Zombie Process**:
   - Mỗi chu kỳ audit tài khoản GPM, hàm `_kill_gpm_chrome(host_port)` sử dụng psutil để quét và kill triệt để Chrome headless theo debug port. Đảm bảo không tồn đọng orphan processes làm chiếm dụng port hoặc RAM.

5. **Cơ chế Fallback OTP (Graph API -> Webmail) & Xử lý HTTP 400**:
   - Khi tài khoản gặp lỗi `HTTP Error 400: Bad Request` từ Graph API (refresh token hết hạn hoặc không khớp client_id), script tự động fallback sang mở Outlook webmail trực tiếp trong browser profile GPM (`[OTP-WEBMAIL] Opening Outlook webmail on ...`).
   - Nếu proxy/mạng của profile bị nghẽn làm timeout webmail, kết quả trả về là `UNKNOWN`. Đây là lỗi môi trường/mạng, script giữ nguyên tài khoản trong kho và không purge.
