# Dispatch Worker Timeout Floor, Deadlock Traps & User Sudo Architecture (2026-10-25)

## 1. Cơ Chế Timeout & Cấm Agent Tự Bóp Nghẹt (Anti-Timeout Clamping)
- **Kiến trúc Timeout của Terminal Pre-Tool Hook:**
  - Mốc **60s** chỉ là trần an toàn cho lệnh ad-hoc thông thường để chống treo session của Coordinator.
  - Các công cụ điều phối nặng nằm trong LONG_RUNNING_ALLOWLIST (dispatch_worker.py, sol_worker.py, ag_cli.py, sol_repair.py, closeout_gate.py, pytest) được phép chạy foreground tối đa **360s**.
  - **Auto-Set Rewrite:** Nếu Agent không truyền tham số timeout, Hook tự động điền timeout = 360s.
- **Cạm bẫy tâm lý & Tự hủy (Self-Sabotage):**
  - **CẤM TUYỆT ĐỐI** Coordinator tự tay truyền `--timeout 60` hoặc gán timeout: 60 cho các tool trong allowlist vì sợ lỗi 60s của lệnh phụ.
  - Sol Web Worker (gpt-web-sol qua cổng 20129) có latency ~35s/turn, một task 3 turns cần 105–120s. Nếu ép 60s, tiến trình bị chém chết ngang lưng (TimeoutExpired), gây lỗi giả TIMEOUT và ép hệ thống fallback sai lệch sang Claude.
  - **Sàn Timeout Cứng 480s & Max Turns 12 (Enforced Floor & Micro-Patch Budget):**
    - Trong `dispatch_worker.py` và `sol_worker.py`, mặc định `--max-turns` nâng lên **12 turns** và `SOL_AGY_TIMEOUT_FLOOR = 480`.
    - Sol Worker khi thực hiện các task sửa code phức tạp thường chia nhỏ thành nhiều thao tác `PATCH` nối tiếp nhau (micro-patching). Nếu chỉ cấp 8 turns, Sol bị ngắt do `MAX_TURNS_REACHED` trước khi kịp verify, ép fallback sang Agy khi tổng thời gian 360s đã cạn.
    - Sàn 480s và trần 12 turns đảm bảo Sol có đủ 250–320s thi công trọn vẹn, đồng thời để lại đủ 120–160s cho Tier 2 Agy CLI nếu cần fallback mà không bị lệnh shell ngoài chém đứt ngang lưng.

## 2. Kỷ Luật Dispatch Worker — Tránh Bẫy Investigate & Multi-File
- **Bẫy INVESTIGATE (Read-Only Worker Trap):**
  - Đưa các từ khóa budget, investigate, chỉ đọc, khảo sát vào context/goal của task sửa/tạo code sẽ kích hoạt nhánh điều tra trong cơ chế phân vai, gán target_files rỗng và khóa cứng quyền ghi của Worker thành READ-ONLY WORKER 100%.
  - Khi cần tạo hoặc sửa code, bắt buộc dùng TASK_KIND: CREATE hoặc TASK_KIND: EDIT với FILE: đường dẫn tuyệt đối và FILE_CONTENT: hoặc OLD_STRING:.
- **Bẫy MULTI_FILE_VIOLATION (Regex False-Positive):**
  - Tránh đặt tên tham số hoặc chuỗi trong prompt có dạng target_file kèm dấu hai chấm hoặc f-string, vì regex của gate sẽ nhận diện nhầm thành file thứ 2, thứ 3 dẫn đến block MULTI_FILE_VIOLATION.

## 3. Thang Luân Chuyển Tự Động (Auto-Fallback Chain: Sol -> Agy -> Claude)
- **Chu trình fallback tự động 100%:** Sol Web Worker (Tier 1) -> Agy CLI (Tier 2) -> Claude Haiku (Tier 3).
- **Hành vi chuẩn:** Khi Tier 1 (Sol) và Tier 2 (Agy) thất bại thật sự (sau khi đã chạy hết timeout floor 360s), `dispatch_worker.py` **tự động chuyển tiếp sang Claude Haiku** để giải quyết dứt điểm công việc.
- **Không thêm rào cản:** TUYỆT ĐỐI KHÔNG dựng thêm tầng xác nhận hỏi User khi chuyển sang Claude Haiku trong chuỗi fallback tự động của dispatch_worker; việc tự động fallback là hoàn toàn đúng để tránh làm phiền User và tránh gây tắc nghẽn hệ thống.

## 4. Cơ Chế User Sudo Override (user_sudo.py)
- Khi User trực tiếp ra lệnh cấp quyền can thiệp nóng (BYPASS_ALL_GUARDS_CONFIRMED, tao cho phép, bypass, sửa gấp, làm luôn, force, tao duyệt):
  - Kích hoạt qua module user_sudo.py.
  - Cấp single-use grant có chữ ký HMAC-SHA256, TTL 300s, lưu tại sudo_grant.json.
  - Ràng buộc an toàn O(1): tối đa 30 dòng diff, cấm đụng vùng cấm (file hệ thống bảo vệ, .env, credentials).
  - Kill-switch khẩn cấp: TAADAA_SUDO=0.

## 5. Ranh Giới Bảo Vệ Cổng Tự Thân (Engine Root of Trust)
- **Vùng bảo vệ bất biến:** Các tiền xử lý pre-tool chặn quét đĩa và dispatch contract được bảo vệ ở cấp động cơ (Engine Self-Protection).
- **Nguyên tắc an ninh:** AI Agent tuyệt đối không tự sửa đổi các tệp kiểm soát cổng bảo vệ an ninh của chính mình.
- **Quy trình khi cần nâng cấp cổng:**
  - Coordinator xuất artifact ra tệp `.patch` độc lập (tránh đặt tên chứa tiền tố nhạy cảm, ví dụ dùng `auto_rewire_upgrade.patch`).
  - Cung cấp cú pháp `git apply` để Operator thi công trực tiếp từ môi trường dòng lệnh bên ngoài session của Agent.
