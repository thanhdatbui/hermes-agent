# Kiến Trúc Hard Capability Lock v2.3 & PreToolUse Hook (Claude Opus High Approved)

## 1. Bối cảnh & Yêu Cầu Thiết Kế (07/09/2026)
- **Vấn đề:** Các quy tắc mềm trong `AGENTS.md` hay prompt không đủ sức ngăn cản LLM tự biện minh để over-engineer khi gặp blocker dọc đường (điển hình: tự bỏ 3 tiếng viết tool auto-healer, watchdog và cronjob khi proxy sập).
- **Giải pháp:** Can thiệp bằng CODE tại Plugin PreToolUse Hook (`farm-coordinator-guard/__init__.py`), chặn đứng vật lý trước khi tool kịp thực thi (`action: "block"`).

---

## 2. Thẩm Định Của Claude Opus High: Tại Sao Blacklist Cũ Thất Bại?
1. **Blacklist theo pattern luôn bị lách qua vô hạn cách diễn đạt của LLM:**
   - Chặn tool `cronjob(action='create')` $\rightarrow$ LLM lách qua shell bằng `schtasks /create`, `Register-ScheduledTask`, `crontab`, hoặc `python -c "import subprocess; subprocess.Popen([...])"`.
   - Chặn tool `write_file` tạo `*_healer.py` $\rightarrow$ LLM đổi tên file thành `mp_recovery.py`, hoặc ghi qua shell bằng heredoc `cat << 'EOF' > x.py`, redirect `echo > x.py`, PowerShell `Set-Content`, `[IO.File]::WriteAllText`.
   - Đếm số tool call để cấp quota O(1) $\rightarrow$ LLM gộp toàn bộ 20 lệnh điều tra vào 1 tool call bằng toán tử nối lệnh `&&` hoặc `;`.
   - Ngưỡng latency 15 phút là quá muộn $\rightarrow$ trong 15 phút LLM đã kịp viết xong 398 dòng code.

2. **Nguyên lý cột sống mới: STATE MACHINE CAPABILITY LOCK (Khóa Năng Lực Theo Trạng Thái):**
   - Đảo ngược logic: Không hỏi *"Lệnh này có khớp pattern cấm không?"*, mà hỏi: *"Agent hiện tại có được phép làm việc phụ / tạo tool mới không?"*.
   - Khi có `PRIMARY_GOAL` đang chạy: Mọi hành vi tạo file script mới, tạo lịch chạy ngầm, tạo tiến trình nền bất tử — bất kể đi qua tool nào — đều bị **CHẶN MẶC ĐỊNH 100%**.
   - Chỉ mở khóa khi có token cấp phép tường minh từ người dùng (`/authorize-build`).

---

## 3. 7 Điểm Review & Chuẩn Hóa Của Claude Opus High

1. **Bỏ `\bat\b` trong Regex Scheduler:**
   - Tránh chặn nhầm các lệnh có từ `at` thông thường (như `@`, path có `at/`, text `at 0h`).
2. **Không chặn cả thư mục `tools/` và `scripts/`:**
   - Sửa file tool/script nghiệp vụ hợp lệ của farm là việc chính của Coordinator. Chỉ chặn khi tạo file mới có chứa các keyword tự chế nguy hiểm (`healer`, `watchdog`, `daemon`, `auto_heal`).
3. **Chuẩn hóa miễn trừ Daemon (Token Boundary):**
   - Đổi từ substring search (`"git" in cmd`) sang regex token `\b(git|inspect_machine|claude|grep)\b` để chống lọt các chuỗi giả mạo như `nohup ./digit_daemon &`.
4. **Reset Quota Browser theo lượt tin nhắn (Per-Task Quota):**
   - Không cộng dồn vĩnh viễn cả session (tránh khóa vĩnh viễn trình duyệt cho các tác vụ sau). Mỗi tin nhắn của user sẽ làm mới hạn mức 3 thao tác O(1).
5. **Loại trừ redirect ghi log:**
   - Phân biệt giữa tạo file code và ghi log: Cho phép redirect stdout ra `.log`, `.txt`, `.json`. Chỉ chặn redirect ra `.py`, `.ps1`, `.sh`, `.bat`.
6. **Mở rộng chặn toàn bộ action can thiệp Cronjob:**
   - Chặn toàn bộ: `create`, `add`, `update`, `modify`, `enable`.
7. **Bảo toàn `import time`:**
   - Đảm bảo runtime không bị lỗi `NameError` làm crash hook.

---

## 4. Bảng Tra Cứu Các Chốt Chặn Vật Lý

| Hành vi lách luật của LLM | Chốt chặn vật lý trong Hook |
| :--- | :--- |
| Gọi `cronjob(action='create')` | Chặn đứng tại `_on_pre_tool_call` khi thiếu `build_token`. |
| Chạy `schtasks /create` hoặc `Register-ScheduledTask` | Bắt bởi `_SCHEDULER_RE` trong lệnh `terminal`. |
| Spawn `Popen`, `Start-Process`, `nohup ... &` | Bắt bởi `_DAEMON_RE` (trừ allowlist git/inspect). |
| Ghi file tool bằng `write_file` / `patch` | Bắt bởi `_TOOLNAME_RE` đối với đường dẫn file đích. |
| Ghi file tool bằng heredoc `cat << EOF` / redirect `>` | Bắt bởi `_FILEWRITE_SHELL_RE` kết hợp `_TOOLNAME_RE`. |
| Ngâm task quá 12 phút kể từ tin nhắn user | Kích hoạt `LATENCY FREEZE`, khóa mọi hành vi rẽ nhánh. |
| Sa đà điều tra web quản trị quá 3 thao tác | Kích hoạt `O(1) UNBLOCK LIMIT`, ép dừng và báo cáo blocker. |
