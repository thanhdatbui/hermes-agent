# ChatGPT GPM Audit: Graph API Recursion & Webmail Timeout Pitfall

## Triệu chứng
Trong kịch bản `login_audit_and_purge_deactivated.py` (chạy định kỳ kiểm tra sức khỏe tài khoản ChatGPT trên GPMLogin):
Hàng loạt tài khoản (ví dụ 53/69 tài khoản) trả về kết quả `UNKNOWN`, kèm log:
```text
[WARNING] [OTP-GRAPH] Graph API failed (maximum recursion depth exceeded), falling back to Outlook Webmail...
[INFO] [OTP-WEBMAIL] Opening Outlook webmail on 127.0.0.1:<port> to read OTP for ...
[WARNING] [OTP-WEBMAIL] Error reading Outlook webmail: Connection timed out
```

## Nguyên nhân gốc rễ (Root Cause)
1. **Circular Delegation Recursion trong OTP Helper Injection**:
   Trong `login_audit_and_purge_deactivated.py`:
   ```python
   def get_access_token(refresh_token, client_id=None):
       return coh.get_access_token(refresh_token, client_id=client_id)

   def fetch_otp_with_fallback(account, host_port, cdp_client_cls=None, retries=3, delay=4):
       coh.get_access_token = get_access_token  # <--- BẪY ĐỆ QUY VÔ TẬN!
       ...
       return coh.fetch_otp_with_fallback(...)
   ```
   Khi gán `coh.get_access_token = get_access_token`, hàm trong module `chatgpt_otp_helper` trỏ ngược lại hàm wrapper `get_access_token` trong file gọi. Hàm wrapper lại gọi `coh.get_access_token`, dẫn đến vòng lặp vô hạn và văng exception `RecursionError: maximum recursion depth exceeded`.
2. **Kéo theo Webmail Fallback quá tải qua Proxy GPM**:
   Do Graph API lập tức crash vì đệ quy, toàn bộ 69 profile đều phải mở tab webmail `https://outlook.live.com/mail/0/` qua proxy dân cư / Singbox gán trên GPM. Khi CDP navigate webmail liên tục, network proxy bị nghẽn dẫn đến `Connection timed out` hoặc không kịp render inbox trong khung thời gian chờ.

## Quy tắc xử lý & Phòng ngừa (Invariant / Runbook)
1. **Tuyệt đối cấm monkeypatch circular reference**:
   - Nếu cần inject dependency hoặc wrapper, truyền trực tiếp qua tham số hàm (dependency injection) thay vì mutate attribute của module (`coh.get_access_token = ...`).
   - Giữ nguyên `coh.get_access_token` gốc của module helper.
2. **Fail-Closed khi tài khoản ở trạng thái UNKNOWN**:
   - Khi không đọc được OTP hoặc chưa vào được giao diện chính của ChatGPT, script bắt buộc đánh dấu `UNKNOWN`.
   - CẤM TUYỆT ĐỐI tự ý đánh dấu `DEAD` hay `purge_account()` khi chưa có screenshot xác nhận `account_deactivated` hoặc lỗi vô hiệu hóa chính thức từ OpenAI.

3. **Giao diện tiếng Việt & DOM Marker ChatGPT (`LOGGED_IN_MARKERS`)**:
   - ChatGPT trên GPM profile có IP Việt Nam thường hiển thị sidebar / nút chat bằng tiếng Việt.
   - Bên cạnh `"New chat"` và `"Cuộc trò chuyện mới"`, giao diện web ChatGPT mới nhất hiển thị `"Trò chuyện mới"` ở panel bên trái và nút new chat.
   - Bắt buộc kiểm tra cả `"Trò chuyện mới"` trong `LOGGED_IN_MARKERS`. Nếu thiếu marker này, các tài khoản đã login hợp lệ và hiển thị giao diện sẵn sàng chat sẽ bị đánh nhầm thành `UNKNOWN`.

4. **OmniRoute & 9Router Provider Schema Compatibility (`connections` vs `providers`)**:
   - Khi query REST API `GET /api/providers` trên OmniRoute (:20129) và 9Router (:20128), response JSON chứa key root là `connections` (ví dụ `{"connections": [...], "total": N}`), KHÔNG phải `providers` hay `data`.
   - Hàm `_list_providers` / đồng bộ token bắt buộc trích xuất theo thứ tự ưu tiên: `data.get("connections", data.get("providers", data.get("data", [])))`. Nếu chỉ đọc key `providers`, kết quả trả về rỗng và vô hiệu hóa việc đồng bộ / purge provider tương ứng.

5. **Background Process & Visual Verification Invariant trong Audit Runner**:
   - Khi chạy script kiểm tra sức khỏe `login_audit_and_purge_deactivated.py` (kể cả batch nhỏ `--limit 5` hoặc `--all` 69-70 tài khoản), mỗi tài khoản khởi động GPM + CDP + đọc mail mất từ 15-30 giây (5 tài khoản mất ~80-120 giây).
   - **Bẫy Foreground Timeout Guard**: Trên môi trường Coordinator, lệnh foreground bị guard giới hạn cứng `timeout <= 60s` (nếu đặt `timeout > 60s` sẽ bị chặn `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`; nếu đặt `timeout <= 60s` sẽ bị đứt giữa chừng). Do đó, BẮT BUỘC khởi chạy qua `terminal(background=True)` và kiểm soát tiến trình qua `process(action='wait', timeout=60, session_id=...)` lặp lại cho tới khi hoàn tất.
   - Trước khi đính kèm `MEDIA:<path>` minh chứng tài khoản DEAD, Agent BẮT BUỘC gọi `vision_analyze` để soi mắt kiểm tra ảnh chụp màn hình artifact thực tế (chứng minh thông báo lỗi tài khoản bị xóa / vô hiệu hóa hiển thị rõ, không bị màn hình đen hay che khuất).
   - Báo cáo audit phải phân tách rõ ràng: LIVE, DEAD_DEACTIVATED (kèm ảnh chụp đã soi và xác nhận purge đồng bộ combo SQLite + OmniRoute :20129), SKIPPED_DEAD (tối ưu hóa bỏ qua acc đã purge trước đó), và UNKNOWN (cần xử lý challenge/OTP).
