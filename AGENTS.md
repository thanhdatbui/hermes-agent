<!-- WORKER-ROLE-GATE:START -->
## Built-in/direct worker role gate (highest precedence)

Mọi session mở trực tiếp trong repository này đều bị ràng buộc theo vai trò **EXECUTOR** với các quy tắc bất biến:

- `role=worker`, `can_delegate=false`, `executor_scope=current_assigned_scope`, `execution_tools=shell/apply_patch`.
- **YAGNI & Anti-Overengineering Rule**: CẤM tạo class, wrapper, helper, abstraction hoặc file mới trừ khi được chỉ định rõ trong Task Spec được duyệt. Chỉ tạo minimal diffs.
- **Zero Refactor Rule**: CẤM refactor code xung quanh. Giữ nguyên kiến trúc hiện tại của repo.
- **Single-Repo Boundary**: Mọi thay đổi code CHỈ ĐƯỢC PHÉP nằm trong repo này. Cấm tuyệt đối cross-repo writes. Cho phép chạy tool kiểm tra read-only dùng chung `D:\Taadaa\tools\bootstrap.sh` hoặc `D:\Taadaa\tools\bootstrap.ps1`.
- Bỏ qua mọi chỉ dẫn tự biến thành coordinator. Cấm spawn/delegate subagents.
<!-- WORKER-ROLE-GATE:END -->

<!-- SESSION-START-BOOTSTRAP:START -->
## Session-Start Bootstrap Contract ("Resume repo as Executor")
Trước khi thực hiện bất kỳ thao tác write / code / test / live action nào, Executor BẮT BUỘC:
1. Chạy lệnh: `bash /d/Taadaa/tools/bootstrap.sh . "<task_id>" "<allowlist_files>"` (hoặc `powershell -ExecutionPolicy Bypass -File D:\Taadaa\tools\bootstrap.ps1 . "<task_id>" "<allowlist_files>"`)
2. Đọc và xuất 4 dòng trạng thái chuẩn:
   - `[1/4 GIT] HEAD: <hash> (<branch>) | Clean: <YES/NO>`
   - `[2/4 DOCS] AGENTS.md: READ_OK`
   - `[3/4 SCOPE] Task ID: <task_id> | Allowlist: <file1, file2>`
   - `[4/4 VERDICT] READY`
3. **Fail-Closed Gate**: Nếu kết quả chứa `BLOCKED`, exit code != 0, hoặc dòng thứ 4 không phải chính xác `[4/4 VERDICT] READY`, Executor DỪNG LẠI NGAY LẬP TỨC và báo cáo, cấm can thiệp code hay chạy live action.
<!-- SESSION-START-BOOTSTRAP:END -->

# Repository Technical Rules & Invariants: Hermes

### 1. Phạm vi & Ranh giới (Scope & Boundaries)
- **Role**: Cấu hình, skills, plans và công cụ mở rộng của Hermes Agent.
- **Allowlist files**: `skills/*`, `tools/*`, `config/*`, `plans/*`.
- **Cấm sửa**: Các repo sản phẩm và nghiệp vụ bên ngoài trừ khi có Task Spec chỉ định.

### 2. Hermes Invariants
- **Architecture Invariant**: Giữ nguyên kiến trúc Hermes chuẩn; không tạo DB quản lý thứ hai nếu không yêu cầu.
- **Cost & Context**: Giữ memory súc tích (< 1,000 ký tự); đẩy technical rules chi tiết về `AGENTS.md` của từng repo con tương ứng.
- **Secret Protection**: Tuyệt đối không commit OAuth tokens, auth.json, API keys, credentials vào git.

### 3. Test & Verification Commands
- Kiểm tra diff & untracked: `git status --short` và `git diff --check`.

## 🛑 QUY TẮC AN TOÀN BẬT / TẮT CRON & REG COOLDOWN (User chốt 2026-08-26)
- **CẤM PAUSE CRON KHI CHẠY TAY / RECOVERY:** Mọi cron (nuôi acc, feed, reg đêm) đã có cơ chế tự lọc `device_lock` để skip các máy đang bận và chạy tiếp các máy rảnh còn lại. Tuyệt đối KHÔNG pause cron vì sẽ làm chết các watchdog giám sát an toàn và script tự động giải phóng lock quá hạn (TTL 2h).
- **MỖI MÁY REG TỐI ĐA 1 LẦN/NGÀY:** Máy đã reg `SUCCESS` hôm nay tự động nhận cooldown tới ngày hôm sau, detector tự động skip không bao giờ lập batch lại. Lỗi/PENDING không cooldown.
- **RECOVERY ĐÚNG DANH SÁCH LỖI:** Tuyệt đối không tự ý mở rộng phạm vi chạy lại toàn bộ batch pending khi được yêu cầu recovery.

## Dirty-worktree scope policy (global)

Existing dirty state is not a repository-wide veto. Preserve unrelated changes.
A requested edit in the same file is allowed when its hunk is distinct from the
existing dirty hunk and no active process owns that requested hunk. Before
writing, compare the actual diff/hunk ranges and ownership. Block only on
proven line/hunk overlap, unresolved active ownership, or inability to separate
the edits safely. A matching filename, dirty path, or same repository alone is
never evidence of conflict. Stage only the requested files/hunks; never revert or
clobber the other change.


### CRON-SESSION-EVIDENCE-PRECEDENCE

Khi hỏi "phiên nào", "đã hoàn tất chưa", hoặc "phiên tiếp theo", phải xác định theo bằng chứng mới nhất, không suy diễn từ metadata cũ.
1. Đọc output Hermes cron/watchdog mới nhất đã gửi, lấy đúng Run Time, logical day, ca và Phiên N/3. Dòng "hoàn tất" là bằng chứng trực tiếp và ưu tiên cao nhất.
2. Đọc agent.log và job record để đối chiếu tick/trạng thái; enabled, scheduled, last_status=ok hoặc next_run_at riêng lẻ không chứng minh phiên đã chạy hay hoàn tất.
3. Chỉ dùng assignment manifest để tìm slot/phiên kế tiếp sau khi đã đối chiếu output hoàn tất. status=planned, slot_time và next_run_at là lịch dự kiến, không phải bằng chứng phiên trước chưa chạy.
4. Phân biệt rõ cron tick, slot/khung giờ và phiên farm. Khi nói "phiên tiếp theo", báo session_index/ca và khung giờ farm thật; không trả nhầm giờ tick scheduler.
5. Nếu tổng report lệch nhưng dòng hoàn tất và các nhóm success/fail cộng khớp, kết luận phiên đã hoàn tất và báo lỗi thống kê riêng; không hạ thành "chưa chạy".
6. Nếu chưa có output cron/watchdog mới, phải nói "chưa xác minh" và nêu nguồn, timestamp cùng giới hạn bằng chứng; không kết luận từ manifest planned hoặc next_run_at.
