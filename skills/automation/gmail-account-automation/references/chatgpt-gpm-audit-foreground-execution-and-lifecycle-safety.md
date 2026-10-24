# ChatGPT GPM Audit: Foreground Timeout Discipline & Account Lifecycle Safety

## 1. Bối Cảnh & Rào Cản Môi Trường (Guard Concurrency Traps)
Khi vận hành script `python D:/Taadaa/tools/login_audit_and_purge_deactivated.py` qua cron job hoặc phiên Coordinator:
1. **Foreground Timeout Guard (60s ceiling)**:
   - Các lệnh terminal foreground bắt buộc `timeout <= 60s`.
   - Mỗi tài khoản ChatGPT audit qua GPM + CDP mất trung bình 20–25s (mở profile GPM, kết nối CDP, mở `chatgpt.com/auth/login`, điền email, chờ OTP qua Graph API hoặc Outlook webmail, kiểm tra DOM marker, và kill tiến trình Chrome).
   - Lệnh batch `--limit 5` cần 100–125s nên sẽ **bị ngắt ở giây 60 (Exit code 124: timeout)** nếu chạy trong 1 lệnh foreground duy nhất.

2. **Background Terminal Guard Intersection Trap**:
   - `guard_cronjob_safety.py` chặn các lệnh background gọi trực tiếp `python` (`[CONSOLE_WINDOW_BLOCKED]`) để tránh bật cửa sổ console trên Windows làm cướp focus/giật lag.
   - Đồng thời, Coordinator Terminal Guard chặn `pythonw` và `powershell.exe` ngoài allowlist.
   - Do đó, Coordinator không thể khởi chạy background script Python tùy ý nếu chưa được whitelist cụ thể.

## 2. Chiến Lược Thực Thi Chuẩn: Phân Rã Theo Email Đơn Lẻ (O(1) Per-Account)
Để hoàn tất kiểm tra an toàn giới hạn 5 tài khoản mà không vi phạm bất kỳ guard nào:
- **Quy trình tuần tự O(1)**:
  1. Đọc danh sách tài khoản từ `D:/Taadaa/Hotmail/latest_bought_70.txt` và đối soát với `D:/Taadaa/runtime/chatgpt_account_lifecycle.json`.
  2. Bỏ qua các tài khoản đã có trạng thái `DEAD_DEACTIVATED` (script hỗ trợ `SKIPPED_DEAD` trong < 0.1s).
  3. Với các tài khoản cần audit (lên đến limit 5), chạy từng tài khoản bằng cờ `--email`:
     ```bash
     python D:/Taadaa/tools/login_audit_and_purge_deactivated.py --email <email>
     ```
     kèm tham số `timeout: 60`.
  4. Mỗi lệnh chỉ mất 20–25s, hoàn toàn nằm trong ngưỡng cho phép `< 60s`, không bao giờ bị timeout ngắt giữa chừng.

## 3. Quy Tắc Lifecycle: Phân Biệt Tuyệt Đối UNKNOWN vs DEAD_DEACTIVATED
- **UNKNOWN Status**:
  - Khi tài khoản chưa kịp render xong marker đăng nhập (`New chat`, `Cuộc trò chuyện mới`) hoặc timeout khi lấy OTP/webmail, script trả về `UNKNOWN`.
  - **INVARIANT AN TOÀN**: Tuyệt đối **KHÔNG** quy chụp `UNKNOWN` thành `DEAD_DEACTIVATED`. Không purge khỏi SQLite/proxy pool khi chưa có bằng chứng xác đáng.
- **DEAD_DEACTIVATED Status**:
  - CHỈ đánh dấu và purge khi xuất hiện marker rõ ràng (`account_deactivated` hoặc `đã bị xóa hoặc vô hiệu hóa`).
  - Bắt buộc chụp ảnh màn hình lưu vào `D:/Taadaa/runtime/artifacts/deactivated_<safe_email>.png` làm bằng chứng (Visual Evidence Gate).

## 4. Dọn Dẹp Tiến Trình Chrome (Process Hygiene)
- Sau mỗi lần kiểm tra profile, `_kill_gpm_chrome(host_port)` quét và kill triệt để toàn bộ tiến trình Chromium con theo port debug, đảm bảo không để lại tiến trình mồ côi chiếm RAM hoặc port.
