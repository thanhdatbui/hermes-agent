# Windows CLI Truncation, Tool Parity & 3-Tier Worker Hierarchy

## 1. Bẫy Windows CLI Truncation do Ký tự Xuống dòng `\n` trong `claude -p`
- **Hiện tượng:** Khi gọi `claude -p <prompt>` qua `subprocess.run` / `subprocess.Popen` trên Windows, nếu chuỗi `prompt` chứa ký tự xuống dòng `\n` (ví dụ `Target file: foo.py\n\nNhiệm vụ: ...`), cmdline parser của Windows sẽ **cắt cụt toàn bộ nội dung sau `\n`**.
- **Hậu quả:** Claude CLI chỉ nhận được đúng dòng đầu tiên (`Target file: foo.py`), hoàn toàn mất toàn bộ yêu cầu phía sau → Worker đứng im hỏi lại *"Your message only names the file and gives no task"*.
- **Cách khắc phục bắt buộc:** Luôn chuẩn hóa prompt thành 1 dòng trước khi truyền vào `-p`:
  ```python
  prompt_input = " ".join(build_prompt(args.prompt, args.file).splitlines()).strip()
  ```

## 2. Quy tắc Cấp Quyền & Tool Parity khi Dispatch / Benchmark Worker (Chống Đổ Lỗi Mù Cho Model)
- **Quyền hạn tương đương (Tool Parity):** Khi so sánh benchmark hoặc dispatch worker thực hiện phẫu thuật kèm kiểm chứng (verify), nếu yêu cầu chạy test/py_compile thì **bắt buộc phải cấp quyền terminal (`Bash` / `COMMAND`) cho worker** (ví dụ cờ `--allow-bash` trên `haiku_worker.py`).
- **Cấm khóa tool bất cân xứng:** Tuyệt đối không giao task yêu cầu verify cú pháp cho model nhưng lại khóa cứng `--disallowedTools Bash`, khiến model bị trói tay không thể thi công rồi kết luận sai lệch là model yếu kém hoặc từ chối làm việc.

## 3. Cấu trúc Phân tầng 3-Tier trong Single Dispatch Gateway (`dispatch_worker.py`)
- **Tier 1 (Primary - Free 100%):** Sol Web Worker (`sol_worker.py` qua OmniRoute `:20129`) — Không tốn token Anthropic hay quota 5h.
- **Tier 2 (Fallback 1):** Agy CLI (`ag_cli.py fix`) — Multi-account sandbox pool.
- **Tier 3 (Fallback 2):** Claude Haiku (`claude_worker.py --role worker` / `haiku_worker.py`) — Phẫu thuật O(1) tốc độ cao khi các tầng free cạn quota/kẹt lỗi.

## 4. Quota Cache vs Live Quota trong OmniRoute (`:20129`)
- Endpoint `GET /api/usage/provider-limits` là passive cache từ lần sync trước, có thể hiển thị `100%` cho snapshot cũ đã hết hạn.
- Để lấy live quota chính xác theo từng tài khoản, cần gọi endpoint on-demand: `GET /api/usage/[connectionId]`.
- Desktop client `agy.exe` kiểm tra quota cá nhân trực tiếp với Google (`RESOURCE_EXHAUSTED 429: Individual quota reached`).

## 5. Phân Định Ranh Giới: Bắt Buộc Sonnet Plan vs Đi Thẳng Haiku Worker T2 (Chống Nhầm Rule Lên Plan)
- **Căn bệnh "Nhầm rule lên plan":** Khi user hỏi *"mày sửa có gọi claude cli lên plan không?"*, Coordinator không được luống cuống nhận vơ là vi phạm gate nếu task đó vốn dĩ là T2 fix code thông thường.
- **Quy tắc phân định 2 trường hợp:**
  1. **BẮT BUỘC Claude Sonnet Plan (`--role planner`):** CHỈ áp dụng khi có **thay đổi kiến trúc hệ thống / đổi cơ chế auth / refactor đa module** mà chưa có diff rõ ràng (ví dụ: thiết kế cơ chế bypass keyring, đổi giao thức lưu token trên OS, tái cấu trúc pipeline nhiều repo).
  2. **ĐI THẲNG Haiku Worker T2 (`--role worker`):** Khi bài toán đã được xác định nguyên nhân cơ học và Coordinator đã có **exact diff O(1)** (Patch Contract cụ thể, <= 2 files, có lệnh verify focused test < 30s). Ở trường hợp này, việc gọi Sonnet lập plan là **thừa thãi, sai quy trình và đốt sạch quota Sonnet vô ích**.
- **Kỷ luật trả lời:** Hiểu bản chất câu hỏi của user là đang chất vấn logic phân loại task, không tự nhận tội hoang tưởng làm rối loạn quy trình điều phối.

## 6. Cơ Chế Hard Guard Của `claude_quota_guard.py` & Kỷ Luật Không Bỏ Cuộc Giữa Chừng
- **Bảo vệ vật lý khi Quota 5h >= 85%:** Lệnh gọi `claude` CLI bị chặn vật lý ở tầng OS (exit 20). `claude_quota_guard.py` tự động phát hiện caller là AI tự động (`is_automated_agent_caller()`) để từ chối các cờ bypass ngầm (`--force-claude`).
- **Kỷ luật Điều tra Đến Cùng (Anti-Deflection):** Khi gặp lỗi hóc búa (như 429 giả mạo do Windows Credential Manager), Coordinator BẮT BUỘC phải dùng read-only tools để đào sâu tới tận binary strings và Win32 API ngay trong phiên hiện tại; CẤM TUYỆT ĐỐI viện cớ bí tắc để thoái thác "xin thêm session mới" khi hệ thống vẫn đang trong tầm kiểm soát.
