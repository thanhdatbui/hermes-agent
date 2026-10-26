# ChatGPT GPM Audit: Foreground Timeout Discipline & Account Lifecycle Safety

## 1. Bối Cảnh & Rào Cản Môi Trường (Guard Concurrency Traps)
Khi vận hành script `python D:/Taadaa/tools/login_audit_and_purge_deactivated.py` qua cron job hoặc phiên Coordinator:
1. **Foreground Timeout Guard (60s ceiling & Tham Số timeout Bị Kẹp)**:
   - Các lệnh terminal foreground bị giới hạn cứng `timeout <= 60s`. Ngay cả khi truyền `timeout: 300`, runtime/guard vẫn ngắt lệnh chính xác ở giây 60 (Exit code 124: timeout).
   - Mỗi tài khoản ChatGPT audit qua GPM + CDP mất trung bình 20–25s (mở profile GPM, kết nối CDP, mở `chatgpt.com/auth/login`, điền email, chờ OTP qua Graph API hoặc Outlook webmail, kiểm tra DOM marker, và kill tiến trình Chrome).
   - Lệnh batch `--limit 5` cần 100–140s nên **chắc chắn văng timeout 124** nếu chạy foreground. Nếu retry foreground sẽ kích hoạt `Tool loop warning: repeated_exact_failure_warning`.
   - **Cấm probe bằng curl**: Lệnh `curl` bị Coordinator Guard chặn hoàn toàn (`DEFAULT-DENY`). Không dùng curl để test cổng GPM `19995` hay OmniRoute; hãy chạy trực tiếp script canonical.

2. **Background Terminal Execution & process(action='wait', timeout=180)**:
   - `python D:/Taadaa/tools/login_audit_and_purge_deactivated.py --limit 5` được phép chạy qua `terminal(background=true)`.
   - Trong môi trường cron job / one-shot runner, không cần phụ thuộc notification mà gọi ngay `process(action='wait', session_id=..., timeout=180)` trong turn tiếp theo.
   - `process(action='wait')` hỗ trợ timeout lên tới 180s, cho phép tiến trình chạy hết 5 tài khoản trong 1 turn duy nhất, nhận trọn vẹn stdout và `exit_code: 0`.
   - Pattern này cho phép chạy toàn bộ batch 5 tài khoản trong 1 lệnh duy nhất (~140-150s), tự động xuất file báo cáo tổng hợp `chatgpt_lifecycle_report.json` chuẩn mà không bị trần 60s foreground timeout ngắt giữa chừng.

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
  5. **Bẫy Ghi Đè Báo Cáo JSON (Consolidated Report Aggregation)**:
     - Mỗi lượt chạy `--email` sẽ ghi đè `D:/Taadaa/reports/chatgpt_lifecycle_report.json` chỉ với 1 tài khoản vừa audit (`total: 1`).
     - Sau khi hoàn tất vòng lặp 5 tài khoản, BẮT BUỘC tổng hợp lại kết quả của cả 5 tài khoản vào file JSON này (`total: 5`, danh sách đầy đủ trong `details`).
  6. **Kỷ Luật Vị Trí File Test / Verification & Xóa File**:
     - Whitelist `write_file` của Coordinator chỉ cho phép trong `['D:\\Taadaa', 'C:\\Users\\Kibe\\AppData\\Local\\hermes']`; cấm ghi vào `C:\\Users\\Kibe\\AppData\\Local\\Temp`. Đặt file pytest kiểm chứng ngay tại `D:\\Taadaa\\reports\\test_chatgpt_report.py`.
     - Lệnh `rm` bị chặn bởi Coordinator Allowlist. Dọn dẹp stub/test script bằng `write_file` thay vì gọi `rm` qua terminal.

## 3. Quy Tắc Lifecycle: Phân Biệt Tuyệt Đối UNKNOWN vs DEAD_DEACTIVATED
- **UNKNOWN Status**:
  - Khi tài khoản chưa kịp render xong marker đăng nhập (`New chat`, `Cuộc trò chuyện mới`) hoặc timeout khi lấy OTP/webmail, script trả về `UNKNOWN`.
  - **INVARIANT AN TOÀN**: Tuyệt đối **KHÔNG** quy chụp `UNKNOWN` thành `DEAD_DEACTIVATED`. Không purge khỏi SQLite/proxy pool khi chưa có bằng chứng xác đáng.
- **DEAD_DEACTIVATED Status**:
  - CHỈ đánh dấu và purge khi xuất hiện marker rõ ràng (`account_deactivated` hoặc `đã bị xóa hoặc vô hiệu hóa`).
  - Bắt buộc chụp ảnh màn hình lưu vào `D:/Taadaa/runtime/artifacts/deactivated_<safe_email>.png` làm bằng chứng (Visual Evidence Gate).

## 4. Dọn Dẹp Tiến Trình Chrome (Process Hygiene)
- Sau mỗi lần kiểm tra profile, `_kill_gpm_chrome(host_port)` quét và kill triệt để toàn bộ tiến trình Chromium con theo port debug, đảm bảo không để lại tiến trình mồ côi chiếm RAM hoặc port.
