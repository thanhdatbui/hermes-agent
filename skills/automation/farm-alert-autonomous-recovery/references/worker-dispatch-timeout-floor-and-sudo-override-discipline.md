# Kỷ Luật Điều Phối Worker: Sàn Timeout 360s, Bẫy Investigate và User Sudo Override

## 1. Sàn Timeout 360s & Nguyên Tắc Không Tự Bóp Nghẹt Timeout
- **Mục đích của mốc 60s trong hook `guard_broad_grep.py`:**
  - Chỉ áp dụng làm cầu chì bảo vệ phiên chat cho các lệnh shell/terminal ad-hoc không xác định thời lượng (chống treo session).
  - Hoàn toàn KHÔNG áp dụng cho các công cụ điều phối nằm trong `LONG_RUNNING_ALLOWLIST` (`dispatch_worker.py`, `sol_worker.py`, `ag_cli.py`, `closeout_gate.py`, `pytest`).
- **Sàn cứng `SOL_AGY_TIMEOUT_FLOOR = 360`:**
  - Sol Web Worker (`gpt-web-sol`) cần 30–35s/turn trong vòng lặp ReAct (tối thiểu 3 turns = 105–120s).
  - Agy CLI qua proxy cần thời gian khởi tạo sandbox và xử lý multi-turn.
  - **CẤM TUYỆT ĐỐI:** Coordinator tự ý truyền `--timeout 60` hoặc `--timeout 120` vào `dispatch_worker.py` hay lệnh worker CLI. Việc tự bóp timeout sẽ chém chết tiến trình con ngang lưng (`TimeoutExpired`), sinh lỗi giả và kích hoạt fallback sai lệch.
  - Hãy để `dispatch_worker.py` chạy với timeout mặc định 360s hoặc tự động clamp lên sàn 360s.

## 2. Thang Luân Chuyển Tự Động (Auto-Wiring)
- **Chuỗi bậc thang chuẩn:**
  `Sol Web (Tier 1)` ──(Fail/Timeout)──► `Agy CLI (Tier 2)` ──(Cooldown/Timeout)──► `Claude Haiku (Tier 3)`
- **Kỷ luật leo thang:**
  - Khi Tier 1 và Tier 2 thực sự gặp lỗi (timeout thật sau 360s, cạn quota, hoặc profile cooldown), `dispatch_worker.py` tự động chuyển tiếp sang Claude Haiku để hoàn thành nhiệm vụ khẩn cấp.
  - Đây là cơ chế failover tự động được thiết kế có chủ đích — Coordinator KHÔNG được chặn lại hỏi xin phép User hay tạo thêm rào cản hành chính rườm rà.

## 3. Bẫy Investigate / Read-Only Worker Deadlock
- **Hiện tượng:** Worker subagent chạy qua `delegate_task` bị chặn ghi file với lỗi:
  `⛔ [WORKER GATE - READ-ONLY WORKER]: Worker này không được cấp Scope Lock hợp lệ! BỊ CẤM GHI FILE 100%.`
- **Nguyên nhân gốc rễ:**
  - Khi Coordinator đưa các cụm từ như `BUDGET: <= 8 tool calls`, `investigate`, `khảo sát`, `thám nghiệm` vào context của task sửa code.
  - Dispatch Gate tự động phân loại task thành `TASK_KIND: INVESTIGATE`, gán `target_files = []` và khóa cứng worker thành Read-Only.
- **Quy tắc khắc phục:**
  - Task sửa code BẮT BUỘC dùng nhãn `TASK_KIND: EDIT` hoặc `TASK_KIND: CREATE`.
  - CẤM TUYỆT ĐỐI đưa từ khóa `budget` hay `investigate` vào context của task cần sửa/tạo file.
  - Cung cấp Patch Contract O(1) rõ ràng: `FILE:`, `OLD_STRING:`, `NEW_STRING:`, `FOCUSED_TEST:`.

## 4. Cơ Chế User Sudo Override (`user_sudo.py`)
- **Mục đích:** Xóa bỏ tình trạng "Tam giác quỷ liệt cơ học" khi Coordinator hết quota T1, Worker bị khóa read-only, và Terminal chặn script ghi file.
- **Kích hoạt bằng chỉ thị của User:**
  - Các từ khóa trigger: `BYPASS_ALL_GUARDS_CONFIRMED`, `tao cho phép`, `bypass`, `sửa gấp`, `làm luôn`, `force`, `tao duyệt`.
- **Rào chắn an toàn O(1):**
  - Cấp single-use grant có chữ ký HMAC-SHA256 (`get_secret_key()`), TTL 300s.
  - Sử dụng file lock `sudo_grant.lock` để chống race condition khi tiêu thụ grant đồng thời.
  - Ràng buộc session ID và so khớp canonical path `Path(target).resolve()`.
  - Giới hạn cứng diff: `0 <= diff_lines <= 30`.
  - Cấm tuyệt đối can thiệp vào các đường dẫn nhạy cảm: `hooks/`, `guard_`, `user_sudo.py`, `.env`, `credentials`, `secret`, `accounts.db`.
  - Ghi nhật ký toàn diện ra `D:/Taadaa/runtime/audit_logs/sudo_audit.jsonl`.
