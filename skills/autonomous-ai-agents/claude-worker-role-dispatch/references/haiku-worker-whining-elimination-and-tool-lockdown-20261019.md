# Triệt Tiêu Hoàn Toàn Bệnh "Khóc Lóc" & Sửa Lan Của Claude Haiku Worker (19/10/2026)

## 1. Hiện Tượng & Root Cause Phân Tích Từ Log `dispatch.jsonl`

Khi Claude Haiku (`claude-haiku-5-5`) chạy làm worker sửa code non-interactive qua `claude -p`, thực tế các ca fail 95% không phải do quota mà do 3 cạm bẫy cấu trúc:

1. **Sửa lan sang file khác (`unrelated_files_changed`):**
   - Khi có sẵn tool `Write` và `Bash`, Haiku tiện tay tạo file tạm hoặc sửa luôn file test bên cạnh. Gateway `dispatch_worker.py` phát hiện `files_modified > 1` so với scope lock nên fail-closed hủy kết quả.
2. **Kẹt lượt & Than vãn hết turns (`MAX_TURNS`):**
   - Khi bóp `max-turns` quá chật (6–8 turns), Haiku đọc file, chạy lệnh bash test, loay hoay hết turns trước khi kịp gọi `Edit`. CLI tự động ngắt và nhả văn bản phân trần: *"Reached max turns. I was unable to complete..."* -> Gateway đánh dấu `NO_DIFF`.
3. **Từ chối hội thoại & Xin quyền ngầm (`conversational_refusal` / `permission_denial`):**
   - Trong `-p` không có human bấm Allow, Haiku tự phân trần: *"I need permission to edit file X"*.
   - Hoặc khi prompt mang tính đàm thoại, Haiku trả lời văn xuôi phân tích thay vì xuất lệnh tool call.

---

## 2. Giải Pháp Cơ Học Đã Thống Nhất Cùng Claude Sonnet Architect & Reviewer APPROVED

### 2.1. Khóa Cứng Công Cụ Phân Tầng Theo Trạng Thái File Đích
- **Khi target file đã tồn tại trên đĩa:**
  - Cấp: `--allowedTools Read,Edit`
  - Chặn triệt để: `--disallowedTools Write,Bash,NotebookEdit,WebFetch,WebSearch,Agent,Task`
  - Về mặt vật lý ở tầng runtime CLI, Haiku không có tool `Write` để tạo file rác và không có tool `Bash` để gõ lệnh shell lan man.
- **Khi tạo file mới (chưa có trên đĩa):**
  - Cấp: `--allowedTools Read,Edit,Write`
  - Chặn triệt để: `--disallowedTools Bash,NotebookEdit,WebFetch,WebSearch,Agent,Task`

### 2.2. Phân Nhánh System Directive Chống Nói Nhảm
- **Nhánh sửa file:**
  `WORKER_DIRECTIVE`: *"You are an automated non-interactive patch worker. Do not ask questions, do not explain, do not propose plans. Apply the edit to the target file with the Edit tool now. Touch ONLY the target file named in the task. Never touch or create any other files. If the task cannot be done, print exactly BLOCKED: <reason> and make no edits."*
- **Nhánh tạo file:**
  `WORKER_CREATE_DIRECTIVE`: *"You are an automated non-interactive file creator... Create the target file with the Write tool now. Touch ONLY the target file named in the task."*

### 2.3. Nâng Trần 15 Turns Nhưng Khóa Chân Khóa Tay
- Đặt `default_turns = 15` (khớp trần `hard_cap_turns = 15`).
- Vì đã cắt quyền `Bash`, Haiku không thể chạy lệnh vòng vo đốt turns. Thực tế chỉ mất đúng 2-3 turns (Read -> Edit -> Done). Mức 15 turns là "bình dưỡng khí" để không bao giờ bị cắt ngang giữa chừng rồi sinh ra văn khóc lóc `MAX_TURNS`.

### 2.4. Containment Check & Xác Minh Nội Dung Bằng SHA-256
- `resolve_target_path(file_arg, workdir)`:
  - Bắt buộc kiểm tra `Path.is_relative_to(workdir_resolved)`. Nếu path cố tình nhảy ra ngoài bằng `../` hoặc symlink -> trả về `None` (fail-closed), ngăn chặn path traversal.
- `target_snapshot(file_arg, workdir)`:
  - Đọc trực tiếp và băm `hashlib.sha256(p.read_bytes()).hexdigest()[:16]` thay vì dựa vào `mtime/size`.
  - Phân định rõ trạng thái file: `ok`, `unreadable`, `absent`.
- Telemetry `worker_complete`:
  - Ghi nhận `target_file`, `tool_lock` (`locked` / `create_fallback` / `unscoped`), `target_exists`, `target_readable`, `target_changed` (true/false/null) và `correlation_id` đồng nhất để phục vụ audit khép kín.

---

## 3. Hạch Toán Thinking Token & Quyết Định Chọn Effort Cho Worker

- **Bản chất chi phí:** Ở task ngắn $O(1)$, `--effort high` sinh ra lượng thinking tokens **gấp 3 lần** `--effort medium` (232 vs 77 tokens), và được tính vào chi phí output token.
- **Tại sao vẫn bắt buộc khóa cứng `--effort high` cho Haiku Worker?**
  1. *First-Shot Success:* Haiku Medium dễ bị bẫy hội thoại hoặc nói nhảm xin quyền làm hỏng cú pháp AST (như ở Hiệp 3 benchmark). Khi fail phát đầu, dispatcher phải retry lần 2, nuốt lại toàn bộ 60k–80k token context input. Một lần ăn ngay của High rẻ hơn nhiều so với việc retry của Medium.
  2. *Tốc độ thực tế tương đương:* Haiku High chỉ mất vài giây suy luận để định hình AST rồi xuất code, thời gian hoàn thành module ngang ngửa Medium (~169s vs 170s).
  3. *Ngược lại với AGY CLI (Gemini):* AGY CLI bắt buộc lock cứng **Medium** (`gemini-3.8-flash-medium`) vì Gemini khi lên High sẽ suy nghĩ lan man 5-10 phút gây timeout và đứt đuôi token (`SyntaxError`).
