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
