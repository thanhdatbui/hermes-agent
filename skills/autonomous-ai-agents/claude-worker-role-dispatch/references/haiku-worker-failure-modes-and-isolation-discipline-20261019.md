# Phân tích nguyên nhân Haiku Worker thất bại trong Single Dispatch Gateway & Kỷ luật cô lập (19/10/2026)

## 1. Bối cảnh & Dữ liệu thực tế từ live dispatch log (`D:/Taadaa/logs/dispatch.jsonl`)

Qua phân tích các ca thất bại của `claude-haiku-5-5` trong `dispatch_worker.py`:
- Thất bại không phải do cạn quota (`QUOTA` chỉ chiếm <5% khi chạm 85%).
- 95% ca thất bại xuất phát từ vi phạm hợp đồng thực thi O(1) giữa Coordinator và Worker.

---

## 2. Ba nguyên nhân thất bại cốt lõi & Cách triệt tiêu

### A. Lỗi sửa lan sang file khác (`unrelated_files_changed`)
- **Cơ chế phát hiện:** `dispatch_worker.py` chụp snapshot git fingerprints trước và sau khi worker chạy. Nếu tập file bị thay đổi chứa bất kỳ file nào ngoài `target_file`, gateway lập tức hủy kết quả (`TASK_FAIL`), kích hoạt Attempt 2 hoặc fallback sang AGY CLI.
- **Root Cause:**
  1. Prompt chứa yêu cầu kép: Vừa yêu cầu sửa file code (`healing_selector.py`), vừa dặn "cập nhật test" $\rightarrow$ Haiku sửa luôn `tests/test_healing_selector.py`.
  2. Haiku chạy lệnh bash/pytest tự tạo file cache hoặc file log tạm trong thư mục làm việc.
  3. Quyền hạn quá rộng: `allowed_tools` cấp cả `Write,Bash` khiến Haiku tự tiện tạo file mới.
- **Kỷ luật cô lập:**
  1. *Quy tắc 1 Target - 1 Dispatch:* Tuyệt đối CẤM gộp task sửa code và sửa test vào cùng một prompt dispatch. Luôn chia làm 2 lượt: Turn 1 sửa file code, Turn 2 sửa file test.
  2. *Khóa quyền tool vật lý:* Khi file mục tiêu đã tồn tại trên đĩa, chỉ cấp quyền `Read,Edit`, tước quyền `Write` để ngăn chặn vật lý việc tạo file rác.
  3. *Chỉ thị cấm chạm file khác:* Prompt worker bắt buộc có tiền tố: `Do not create new files or modify any file other than <target>.`

### B. Lỗi không tạo ra diff (`NO_DIFF / target_file_unchanged`)
- **Cơ chế phát hiện:** Gateway so khớp SHA256 của target file. Nếu hash không đổi sau khi worker exit 0, gateway coi là thất bại.
- **Root Cause:**
  1. Goal quá mở ("tìm và sửa lỗi X"): Haiku là model nhỏ, khi gặp yêu cầu mở trên file >300 dòng, nó sẽ trần thuật lý thuyết thay vì gọi tool `Edit`.
  2. Chạm trần số lượt trao đổi (`MAX_TURNS = 8`): Haiku mất 4-6 turns đọc file và tra cứu liên kết, hết ngân sách turns trước khi kịp gọi lệnh `Edit`.
- **Kỷ luật cô lập:**
  1. *Cung cấp Patch Contract O(1):* Coordinator phải đọc file trước, định vị anchor duy nhất và cấp sẵn `old_string` $\rightarrow$ `new_string`. Haiku chỉ mất đúng 1 turn để áp dụng.
  2. *Nâng ngân sách turns lên kịch trần an toàn (Triệt tiêu bệnh khóc lóc `MAX_TURNS`):* Nâng `default_turns` từ 8 lên **15** (khớp với `hard_cap_turns` = 15). Việc bóp hẹp 6-8 turns khiến Haiku chưa sửa xong đã bị ngắt giữa chừng và nhả ra văn than vãn phân trần "reached max turns". Khi nâng lên 15 và **cắt quyền Bash**, Haiku chỉ mất đúng 2 nhịp (Read -> Edit) là xong việc ở turn 2-3, trần 15 turns là lưới an toàn để không bao giờ bị cắt ngang.

### C. Triệt tiêu 100% bệnh phân trần / khóc lóc của Haiku Worker (Claude Reviewer APPROVED)
Bản review từ Claude Sonnet Principal Architect đã chốt cơ chế 4 tầng bảo vệ:
1. *Khóa cứng quyền Tool phân tầng theo file thực tế:*
   - **Khi sửa file đã có:** Cấp `--allowedTools Read,Edit` và chặn triệt để:
     `--disallowedTools Write,Bash,NotebookEdit,WebFetch,WebSearch,Agent,Task`
     *(Về mặt vật lý không thể tạo file rác, không thể gõ shell, không thể sửa lan sang file khác).*
   - **Khi tạo file mới:** Cấp `--allowedTools Read,Edit,Write` và chặn toàn bộ:
     `--disallowedTools Bash,NotebookEdit,WebFetch,WebSearch,Agent,Task`.
2. *Chỉ thị cưỡng chế không thể chối cãi (WORKER_DIRECTIVE):*
   - Nhánh sửa: *"Apply the edit to the target file with the Edit tool now. Touch ONLY the target file named in the task. Never touch or create any other files."*
   - Nhánh tạo mới: *"Create the target file with the Write tool now."*
3. *Chống lỗi xin quyền ngầm (Silent Permission Denial):*
   - Cấp `--dangerously-skip-permissions` và `--strict-mcp-config` (cắt bỏ MCP rác gây nhiễu tool schema).
4. *Phán quyết bằng code, cấm đọc văn xuôi:*
   - Gateway chỉ phán xét dựa trên `git diff --numstat` và focused test, tuyệt đối không đọc văn xuôi xã giao của Haiku để suy diễn xem nó có đang than vãn hay không.

### D. Cơ chế tiêu hao Quota khi Gate chặn & Kỷ luật Mechanical Gate vs Memory
- **Đặc tính cơ học:** Tất cả các gate/hook (`guard_dispatch_contract.py`, `guard_terminal_policy.py`, `claude_quota_guard.py`) đều là script Python thuần chạy offline cục bộ (<50ms).
- Khi Coordinator gọi sai lệnh và bị Gate chặn (`action: block`): Tool call bị hủy trước khi process con được sinh ra. **Chi phí token và quota Claude là 0%.**
- Quota chỉ bị tiêu hao khi process `claude -p` thực sự vượt qua mọi gate và kết nối tới API server.
- **Kỷ luật cơ học vs Memory (User Correction 19/10/2026):**
  *"Là sao có gate cơ học r cứ dùng memory chi v"*.
  Khi quy chuẩn đã được cơ giới hóa thành code và có test suite bảo vệ (129/129 tests pass), TUYỆT ĐỐI CẤM ghi lại cấu hình vào Persistent Memory hay tiêm prompt mềm thừa thãi. Code và test là chân lý duy nhất.
