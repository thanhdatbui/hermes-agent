# Dispatch Worker Timeout Floor, Deadlock Traps & User Sudo Architecture (2026-10-25)

## 1. Cơ Chế Timeout & Cấm Agent Tự Bóp Nghẹt (Anti-Timeout Clamping)
- **Kiến trúc Timeout của Terminal Pre-Tool Hook:**
  - Mốc **60s** chỉ là trần an toàn cho lệnh ad-hoc thông thường để chống treo session của Coordinator.
  - Các công cụ điều phối nặng nằm trong LONG_RUNNING_ALLOWLIST (dispatch_worker.py, sol_worker.py, ag_cli.py, sol_repair.py, closeout_gate.py, pytest) được phép chạy foreground tối đa **360s**.
  - **Auto-Set Rewrite:** Nếu Agent không truyền tham số timeout, Hook tự động điền timeout = 360s.
- **Cạm bẫy tâm lý & Tự hủy (Self-Sabotage):**
  - **CẤM TUYỆT ĐỐI** Coordinator tự tay truyền `--timeout 60` hoặc gán timeout: 60 cho các tool trong allowlist vì sợ lỗi 60s của lệnh phụ.
  - Sol Web Worker (gpt-web-sol qua cổng 20129) có latency ~35s/turn, một task 3 turns cần 105–120s. Nếu ép 60s, tiến trình bị chém chết ngang lưng (TimeoutExpired), gây lỗi giả TIMEOUT và ép hệ thống fallback sai lệch sang Claude.
  - dispatch_worker.py có giá trị mặc định là `--timeout 300` (sàn 180s–300s), phải để nguyên mặc định.

## 2. Kỷ Luật Dispatch Worker — Tránh Bẫy Investigate & Multi-File
- **Bẫy INVESTIGATE (Read-Only Worker Trap):**
  - Đưa các từ khóa budget, investigate, chỉ đọc, khảo sát vào context/goal của task sửa/tạo code sẽ kích hoạt nhánh điều tra trong cơ chế phân vai, gán target_files rỗng và khóa cứng quyền ghi của Worker thành READ-ONLY WORKER 100%.
  - Khi cần tạo hoặc sửa code, bắt buộc dùng TASK_KIND: CREATE hoặc TASK_KIND: EDIT với FILE: đường dẫn tuyệt đối và FILE_CONTENT: hoặc OLD_STRING:.
- **Bẫy MULTI_FILE_VIOLATION (Regex False-Positive):**
  - Tránh đặt tên tham số hoặc chuỗi trong prompt có dạng target_file kèm dấu hai chấm hoặc f-string, vì regex của gate sẽ nhận diện nhầm thành file thứ 2, thứ 3 dẫn đến block MULTI_FILE_VIOLATION.

## 3. Kỷ Luật Claude Worker 100% On-Demand
- Cấm Coordinator tự ý thêm cờ on-demand hoặc tự động nhảy cóc sang claude_worker.py khi chưa có lệnh tường minh từ User chứa từ khóa claude.
- Bậc thang điều phối chuẩn: Sol Web Worker (Tier 1) -> Agy CLI Pool (Tier 2, 29 profiles qua ag_cli.py) -> Báo cáo trung thực hiện trường.

## 4. Cơ Chế User Sudo Override (user_sudo.py)
- Khi User trực tiếp ra lệnh cấp quyền can thiệp nóng (BYPASS_ALL_GUARDS_CONFIRMED, tao cho phép, bypass, sửa gấp, làm luôn, force, tao duyệt):
  - Kích hoạt qua module user_sudo.py.
  - Cấp single-use grant có chữ ký HMAC-SHA256, TTL 300s, lưu tại sudo_grant.json.
  - Ràng buộc an toàn O(1): tối đa 30 dòng diff, cấm đụng vùng cấm (file hệ thống bảo vệ, .env, credentials).
  - Kill-switch khẩn cấp: TAADAA_SUDO=0.
