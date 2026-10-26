# User Supreme Sovereignty & Hook Auto-Rewire Architecture

## 1. Triết Lý Chủ Quyền Tối Thượng Của User (Unix Sudo Philosophy)
### Vấn Đề Gốc Rễ: Phản Mẫu Đảo Ngược Phân Cấp (Hierarchy Inversion Anti-pattern)
- Trong mọi hệ thống: **`Root Owner (User) > Coordinator > Autonomous Subagent`**.
- Rào chắn an toàn (Guard Hooks, Pre-tool Gates) được dựng lên để kiềm tỏa AI chạy ngầm không kiểm soát (Autonomous Runaway), **tuyệt đối không được phép tước quyền của Root Owner**.
- Nếu rào chắn chặn cả chính User khi đã có chỉ đạo tường minh (`"tao cho phép"`, `"làm luôn"`, `"force"`, `"bypass"`), hệ thống rơi vào "Tam giác quỷ bại liệt cơ học" (Deadlock Triangle): chính chủ nhân bị giam giữ bởi quy tắc do mình tạo ra, buộc phải thoát ra terminal ngoài để gõ lệnh thủ công.

### Chuẩn Hóa Cơ Chế User Sudo Cho Phép Sửa Hooks
1. **Gỡ bỏ `hooks/` và `guard_` khỏi `FORBIDDEN_PATTERNS`:**
   - Trong `user_sudo.py`, danh sách cấm tuyệt đối chỉ áp dụng cho mật khẩu/thông tin nhạy cảm:
     `FORBIDDEN_PATTERNS = ('user_sudo.py', '.env', 'credentials', 'secret', 'accounts.db')`.
   - Các file quy tắc hệ thống (`hooks/guard_*.py`) được phép can thiệp KHI VÀ CHỈ KHI có chữ ký HMAC-SHA256 hợp lệ được sinh từ tin nhắn chứa trigger keyword của User.
2. **Kỷ Luật Bọc An Toàn O(1):**
   - Diff trần cứng: $\le 30$ dòng diff tổng cộng.
   - Bắt buộc chạy 1 focused test $< 30$s ngay sau khi sửa.
   - Test fail $\to$ Tự động `git checkout -- <file>` rollback ngay lập tức.
   - Audit trail bất biến: Ghi đầy đủ `session_id`, `grant_nonce`, `user_prompt`, `diff_lines` vào `D:/Taadaa/runtime/audit_logs/sudo_audit.jsonl`.

---

## 2. Kỷ Luật "Cấm Khóc Lóc Block" (Anti-Whining & Zero-Turn Auto-Rewire)

### A. Investigate Missing Budget (Góc Chết #2)
- **Trước đây (Passive Denial):** Agent gọi `delegate_task` cho task khảo sát/đọc log nhưng quên ghi từ khóa "Budget" $\to$ Hook chặn cứng: `Task điều tra/khảo sát bắt buộc phải có BUDGET GIỚI HẠN!` $\to$ Agent mất 1–2 lượt gõ lại.
- **Chuẩn hóa (0-Turn Auto-Rewire):**
  - Nếu thiếu budget: Tự động chèn clause `BUDGET: <= 8 tool calls, thời gian < 3 phút` vào `updated_args` và trả về `action: rewrite` kèm `budget = 8`.
  - Nếu cú pháp budget không đọc được số (unparseable): Tự động fallback về budget mặc định 8 calls (`rule_id: HARD_GATE_3_INVESTIGATE_BUDGET_FALLBACK_CLAMPED`) thay vì fail-closed quăng lỗi.
- **Cảnh báo Auditor Review (Tránh Bẫy Sửa Đệ Quy Toàn Bộ Args):**
  - CẤM viết hàm `_inject_budget` duyệt đệ quy qua toàn bộ dict/list để nối chuỗi vào mọi giá trị (sẽ làm méo mó các trường metadata lồng nhau, bị Closeout Reviewer chấm rớt điểm).
  - BẮT BUỘC tiêm chuỗi có mục tiêu (Targeted Field Injection) theo thứ tự:
    `if "context" in updated_args: ... elif "goal" in updated_args: ... elif "prompt" in updated_args: ...`.

### B. Foreground Timeout Exceeded (Ma Sát #3)
- **Trước đây (Passive Denial):** Lệnh foreground có `timeout > 60s` (hoặc `> 360s` với allowlist) $\to$ Hook chặn đứng `GUARD_FOREGROUND_TIMEOUT_EXCEEDED` $\to$ Agent phải đọc guidance để hạ số giây hoặc chuyển `background=True`.
- **Chuẩn hóa (0-Turn Auto-Clamp):**
  - Hook tự động kẹp `updated_args["timeout"] = max_allowed` (60s cho lệnh thường, 360s cho `LONG_RUNNING_ALLOWLIST`) và trả về `action: rewrite` với `rule_id: GUARD_FOREGROUND_TIMEOUT_AUTO_CLAMPED`.
  - Lệnh được thực thi ngay trong cùng turn, triệt tiêu 100% lượt loay hoay thừa.

---

## 3. Cấu Hình Sàn Thực Thi Cho Sol Worker
- Để Sol Worker không bị cạn lượt khi xử lý các task multi-file hoặc micro-patching:
  - `DEFAULT_MAX_TURNS` trong `sol_worker.py` và `--max-turns` trong `dispatch_worker.py` nâng lên **12 turns**.
  - `SOL_AGY_TIMEOUT_FLOOR` và `--timeout` mặc định nâng lên **480s** (đảm bảo đủ thời gian gọi mô hình qua OmniRoute `:20129`).
