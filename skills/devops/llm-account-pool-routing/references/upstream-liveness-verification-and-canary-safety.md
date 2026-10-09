# Upstream Liveness Verification, Canary Safety, and Recovery Pitfalls

## 1. CẤM TIN NHÃN STALE TRONG DATABASE — BẮT BUỘC TEST LIVE UPSTREAM TRƯỚC KHI KẾT LUẬN

### Vấn đề thực tế
Trong OmniRoute (`:20129`), trường `testStatus` (ví dụ `banned`, `expired`) và `isActive=false` có thể được ghi nhận từ nhiều ngày trước do sự cố mạng, proxy lỗi thời điểm đó, hoặc lỗi Cloudflare tạm thời.
Nếu chỉ đọc DB/cache mà vội vàng tuyên bố:
- "Tài khoản đã bị OpenAI khóa/ban"
- Hoặc tự ý gỡ bỏ kết nối khỏi combo/pool
đó là **kết luận sai lầm nghiêm trọng (false dead declaration)** và làm lãng phí tài sản tài khoản của farm.

### Quy tắc đối soát bắt buộc (Live Upstream Probe)
Trước khi kết luận bất kỳ tài khoản nào bị ban, chết hoặc không thể cứu:
1. **BẮT BUỘC test live trực tiếp lên upstream:**
   Gửi request kiểm tra thực tế qua OmniRoute endpoint:
   ```bash
   POST http://127.0.0.1:20129/api/providers/<connection_id>/test
   Body: {}
   ```
2. **Kiểm tra phản hồi thực tế:**
   - Nếu upstream trả về `valid: true` (ví dụ `diagnosis.type: "ok"`):
     Token và tài khoản **vẫn còn sống nguyên vẹn 100%**.
     -> Bật lại `isActive: true`, cập nhật `testStatus: "active"`, và bổ sung lại vào combo tương ứng (ví dụ `chatgpt-web-pool`).
   - CHỈ KHI upstream trả về `valid: false` kèm mã lỗi rõ ràng từ upstream (như `account_deactivated`, `token_revoked`, `401 Unauthorized` kéo dài):
     Mới được phép đánh dấu tài khoản chết hoặc yêu cầu re-login.

---

## 2. QUY TẮC CANARY VÀ VƯỢT RÀO CẢN WORKER GUARD TRONG PHÂN VAI DISPATCHER

### Rào cản thường gặp
Khi Coordinator cần chạy một tác vụ kiểm chứng (Canary verification):
- Dispatch subagent với `TASK_KIND: INVESTIGATE` rồi yêu cầu Worker tạo file script tạm (ví dụ `run_canary_*.py`) và chạy terminal:
  - **Lỗi 1:** `TASK_KIND: INVESTIGATE` bị Worker Gate cưỡng chế là **READ-ONLY WORKER** (cấm gọi `write_file` hoặc `patch`, cấm tạo file script tạm).
  - **Lỗi 2:** Terminal của Worker bị áp dụng **DEFAULT-DENY TERMINAL**, chặn mọi lệnh gọi python lạ ngoài allowlist (`inspect_machine.py`, `pytest`, `adb`, `git`).
  - **Hậu quả:** Worker bị kẹt, không tạo được script, không chạy được canary và báo lỗi tắc nghẽn.

### Giải pháp kiến trúc chuẩn (Anti-Insanity Canary)
1. **Tuyệt đối không vẽ việc tạo script tạm chạy lậu qua terminal.**
2. **Tích hợp lệnh quan sát trực tiếp vào pipeline/watchdog chính thống:**
   - Thay vì tạo file script ngoài luồng, dispatch worker với `TASK_KIND: EDIT` kèm `Scope Lock` để gắn lệnh chụp ảnh (`page.screenshot(path=...)`) trực tiếp vào hàm recovery của script watchdog (`cron_chatgpt_web_pool_watchdog.py`).
   - Chạy watchdog qua cơ chế cron runner độc lập (`cronjob action='run'`). Cron runner chạy ở background process có đầy đủ quyền tương tác Playwright và GPM API mà không bị hạn chế bởi sandbox terminal của agent.
   - Coordinator kiểm tra ảnh xuất ra tại thư mục chuẩn `D:\Taadaa\GPM auto\debug_screenshots\` và gửi `MEDIA:<path>` cho user.
3. **Nếu bắt buộc Worker phải tạo/sửa file:**
   - Luôn dùng `TASK_KIND: EDIT` kèm `Scope Lock: <đường dẫn file>` và tuân thủ ngân sách O(1) (<= 30 dòng, 1 focused test).

---

## 3. CÁC CẠM BẪY KỸ THUẬT KHI HỒI SINH CHATGPT-WEB VÀ PIPELINE S7

### A. Cạm bẫy Cookie Refresh ChatGPT-Web
1. **Reload sau khi clear cookies:**
   Khi gọi `context.clear_cookies()`, trình duyệt không tự động tải lại trang mà vẫn giữ nguyên DOM cũ của phiên lỗi. Bắt buộc phải gọi lại:
   ```python
   page.goto("https://chatgpt.com/auth/login", timeout=35000, wait_until="domcontentloaded")
   page.wait_for_timeout(2000)
   ```
   để form đăng nhập được nạp lại hoàn toàn sạch sẽ trước khi điền email/password.
2. **Guard empty session token:**
   Trước khi gửi token đi validate, bắt buộc có guard kiểm tra rỗng:
   ```python
   if not cookie_str or not isinstance(cookie_str, str):
       return False, "EMPTY_SESSION_TOKEN"
   ```
   Nếu gửi `None` sang OmniRoute validate API, upstream sẽ ném lỗi `HTTP Error 400: Bad Request` làm ô nhiễm log giám sát.

### B. Tra cứu thông tin máy Farm S7 (Antigravity OAuth)
1. **Không giới hạn trong một sheet:**
   Tài khoản farm có thể nằm ở `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7` hoặc `Master_All`) hoặc trong file `taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`).
2. **Thứ tự ưu tiên tra cứu:**
   - Ưu tiên đọc `taikhoan_dat_v2_updated .xlsx` (cột 1: Máy, cột 6: GMAIL, cột 10: Serial thiết bị, port = `20000 + mid`).
   - Fallback an toàn về `master_gmail_manager.xlsx`.
   - Đảm bảo pipeline S7 luôn tìm thấy `machine_id` và `serial` để tự động duyệt Google Prompt hoặc bốc mã 10 số OOTP từ Google Play Services qua port 7912.
