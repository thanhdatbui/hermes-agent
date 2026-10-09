# Anti-Unprompted External CLI Invocation & Dispatch Budget Invariants

## 1. Cấm Tự Tiện Gọi Claude CLI / External Agents Khi Chỉ Nhận Lệnh "Kiểm Tra Lại"
- **Hiện tượng vi phạm (Severe User Frustration)**:
  - Khi user phát lệnh "kiểm tra lại", "check lại", "coi lại": Coordinator tự tiện gọi `claude -p "..."` hoặc spawn external agent liên tục ở background.
  - Hậu quả: Đốt sạch quota 5h của User (`You've hit your session limit · resets 1:10am`), gây trễ nải và làm sai lệch ý định của người dùng.
- **Kỷ luật bất biến**:
  - Lệnh "kiểm tra", "coi lại" $\rightarrow$ Coordinator BẮT BUỘC dùng lệnh O(1) kiểm tra trực tiếp (read_file, git status, inspect_machine, hoặc 1 delegate_task INVESTIGATE nhẹ).
  - CHỈ ĐƯỢC GỌI Claude Code CLI khi:
    1. User ra lệnh tường minh: "gọi claude", "dùng claude sửa", "cho claude làm".
    2. Đã cạn các tầng L0-L1 theo đúng quy trình và cần coding agent bên thứ ba thực thi patch contract rõ ràng.

## 2. Kiến Trúc Chuẩn Cho Dispatch Budget & Circuit Breaker (Tư Vấn Sol Web)
Để tránh tình trạng "tự trói tay chân" khiến Coordinator bị liệt trần cứng:
- **Tách bạch 2 tầng đếm (Dual-Counter Architecture)**:
  1. `total_dispatches` (Monotonic Session Cap):
     - Giới hạn tổng số lượt dispatch trong một phiên làm việc (ví dụ trần 20 hoặc 40).
     - **Tính đơn điệu (Monotonic)**: KHÔNG HOÀN LẠI quota khi thành công để ngăn chặn việc Coordinator chạy vòng lặp vô hạn trong bóng tối.
  2. `consecutive_failures` (Strategy Health / Circuit Breaker):
     - Chỉ đếm số lần thất bại liên tiếp trên **cùng một file đích (normalized target)**.
     - **Miễn trừ Inspect**: Mọi task đọc log, điều tra, chụp OCR (`TASK_KIND: INVESTIGATE`) hoàn toàn KHÔNG tính vào failure streak.
     - **Phân loại lỗi**:
       - `TRANSIENT` (Timeout mạng, API 429/5xx, mất kết nối ADB): Retry có backoff, KHÔNG tính vào failure streak.
       - `STRUCTURAL` (Worker sửa sai logic, assertion fail, ABORT_SCOPE): Tính vào failure streak. Đạt $\ge 3$ lần trên cùng target $\rightarrow$ ngắt mạch chuyển L2 hoặc L3.
  3. **Explicit Success Invariant**:
     - Chỉ công nhận thành công khi có tín hiệu tường minh (`STATUS: SUCCESS` hoặc `STATUS: COMPLETED` kèm diff/test evidence).
     - CẤM suy diễn thành công chỉ vì output không chứa regex lỗi (vì output rỗng, timeout, hoặc dở dang cũng không dính regex lỗi).
  4. **Reset Khi Có Tiến Triển Thật**:
     - Khi Worker thành công đúng target, hoặc `pytest` pass, hoặc `closeout_gate` pass $\rightarrow$ reset `consecutive_failures = 0` ngay lập tức, không để án tích của task cũ ảnh hưởng task mới.

## 3. Rào Chắn Tự Bảo Vệ Guard Source (Self-Protection Fail-Closed)
- Thư mục plugin `farm-coordinator-guard` và `farm_policy.py` là vùng cấm bảo vệ hệ thống tuyệt đối:
  - Worker subagent bị chặn bởi `Worker Gate`: `SELF-MODIFICATION BLOCKED`.
  - Coordinator tools bị chặn bởi `Coordinator Guard`: `GUARD SOURCE BLACKLISTED`.
- Khi cần điều chỉnh guard, tuyệt đối không lãng phí dispatch budget để worker sửa guard. Phải thực hiện qua quy trình cấu hình của host hoặc can thiệp trực tiếp từ ngoài sandbox hook.
