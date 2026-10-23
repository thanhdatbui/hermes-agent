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

## 5. Kỷ Luật Gate Lập Kế Hoạch (Plan Gate) & Giải Quyết Xung Đột Quota Guard

### 1. Quy Tắc Bất Biến Về Gate Lập Plan:
- **Người Dùng Đã Chốt:** Trước khi thi công các ca can thiệp thay đổi cơ chế xác thực (auth), sửa kiến trúc core, hoặc refactor đa module, **COORDINATOR BẮT BUỘC PHẢI GỌI CLAUDE SONNET LÊN PLAN TRƯỚC** (`claude_worker.py --role planner`).
- **CẤM NHẢY CÓC LÀM TẮT:** Coordinator TUYỆT ĐỐI CẤM tự ý phân tích rồi vội vã cấp Patch Contract gọi thẳng Haiku Worker thi công mà bỏ qua bước lập plan của Sonnet. Việc tự làm tắt bị coi là vi phạm nghiêm trọng Gate điều phối.

### 2. Tháo Gỡ Điểm Nghẽn (Deadlock) Khi Claude Quota 5h >= 85%:
- **Tình huống xung đột:** `claude_quota_guard.py` chặn cứng lệnh gọi Claude CLI khi Quota 5h >= 85% (kể cả role `planner`).
- **Thứ tự Fallback Planner Hợp Lệ (Cấm Tự Phẫu Thuật Mò):**
  1. *Ưu tiên 1:* Gọi **Claude Sonnet CLI** (`claude_worker.py --role planner`).
  2. *Fallback khi Claude Quota >= 85%:* Chuyển bước lập Plan sang **Sol Planner** (`:20129` qua `sol_consult` / `gpt-web-sol`). Sol Planner hoàn toàn miễn phí và không tốn quota Anthropic.
  3. Chỉ sau khi đã có Plan được duyệt từ Sonnet hoặc Sol Planner, Coordinator mới trích xuất Patch Contract O(1) để bàn giao cho Worker thi công.

## 6. Thứ Tự Phân Tầng Chuẩn 3-Tier Trong Single Dispatch Gateway (`dispatch_worker.py`)
- **Quy chuẩn bất biến:**
  1. **Tier 1 (Primary - Free 100%):** Sol Web Worker (`sol_worker.py` qua `:20129`) — Không tốn token Anthropic hay Google Pro.
  2. **Tier 2 (Fallback 1 - Native Pool):** Agy CLI (`ag_cli.py fix`) — Chạy native binary `agy.exe` qua 29 tài khoản Google One Pro cục bộ (đồng bộ token qua Windows Keyring `wincred`).
  3. **Tier 3 (Fallback 2 - An Toàn Cuối):** Claude Haiku CLI (`claude_worker.py --role worker` / `haiku_worker.py`) — Phẫu thuật O(1) tốc độ cao khi cả Sol và Agy đều cạn quota hoặc timeout.
- **Khắc phục mâu thuẫn tài liệu:** Bất kỳ docstring, prompt template hay file markdown nào ghi `Tier 1: Haiku` hoặc `Tier 1: Agy` (bỏ sót Sol) đều là tài liệu cũ lạc hậu và phải được chuẩn hóa về đúng thứ tự 3-Tier trên.

## 6. Cơ Chế Hard Guard Của `claude_quota_guard.py` & Kỷ Luật Không Bỏ Cuộc Giữa Chừng
- **Bảo vệ vật lý khi Quota 5h >= 85%:** Lệnh gọi `claude` CLI bị chặn vật lý ở tầng OS (exit 20). `claude_quota_guard.py` tự động phát hiện caller là AI tự động (`is_automated_agent_caller()`) để từ chối các cờ bypass ngầm (`--force-claude`).
- **Kỷ luật Điều tra Đến Cùng (Anti-Deflection):** Khi gặp lỗi hóc búa (như 429 giả mạo do Windows Credential Manager), Coordinator BẮT BUỘC phải dùng read-only tools để đào sâu tới tận binary strings và Win32 API ngay trong phiên hiện tại; CẤM TUYỆT ĐỐI viện cớ bí tắc để thoái thác "xin thêm session mới" khi hệ thống vẫn đang trong tầm kiểm soát.
