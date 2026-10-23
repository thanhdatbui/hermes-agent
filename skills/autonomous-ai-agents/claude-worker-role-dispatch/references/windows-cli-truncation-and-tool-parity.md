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
- **Thứ tự Fallback Planner Hợp Lệ Cưỡng Chế Bằng Code (Cấm Dùng Prompt Mềm):**
  1. *Tier 1 (Ưu tiên 1):* Gọi **Claude Sonnet CLI** (`claude_worker.py --role planner`, timeout >= 300s).
  2. *Tier 2 (Fallback 1 khi Claude Quota >= 85% hoặc Sonnet lỗi):* Tự động chuyển bước lập Plan sang **Sol Planner** (`D:/Taadaa/tools/sol_planner.py` qua `:20129`, timeout >= 300s).
  3. *Tier 3 (Fallback 2 - Cứu sinh):* **Coordinator trong session hiện tại**. Nếu cả Sonnet lẫn Sol Planner đều fail/timeout, script in cờ `[PLANNER_FALLBACK_COORDINATOR]` và trả mã `exit 100`. Khi đó Coordinator chính thức nhận quyền tự lập Plan / chốt Patch Contract O(1) để đi tiếp, tuyệt đối cấm viện cớ thiếu plan để đóng băng task.

## 6. Thứ Tự Phân Tầng Chuẩn 4-Tier Trong Single Dispatch Gateway (`dispatch_worker.py`)
- **Quy chuẩn bất biến (Cưỡng chế 100% cơ học, dẹp prompt):**
  1. **Tier 1 (Primary - Free 100%):** Sol Web Worker (`sol_worker.py` qua `:20129`, timeout >= 180s) — Không tốn token Anthropic hay Google Pro.
  2. **Tier 2 (Fallback 1 - Native Pool):** Agy CLI (`ag_cli.py fix`, timeout >= 180s) — Chạy native binary `agy.exe` qua 29 tài khoản Google One Pro cục bộ (đồng bộ token qua Windows Keyring `wincred`).
  3. **Tier 3 (Fallback 2 - An Toàn Cuối):** Claude Haiku CLI (`claude_worker.py --role worker`, timeout >= 180s) — Phẫu thuật O(1) tốc độ cao khi cả Sol và Agy đều cạn quota hoặc timeout.
  4. **Tier 4 (Fallback cuối cùng):** Coordinator kích hoạt quyền Emergency Surgery (T1/L2) vá O(1) dứt điểm task khi bắt được cờ `[WORKER_FALLBACK_COORDINATOR]`.

## 7. Thiết Quân Luật Về Timeout Cơ Học (Cấm Tuyệt Đối Set Ngắn)
- **Bản chất kỹ thuật:** Reasoning model (Sonnet, Sol Web High) và multi-turn CLI agents (`agy.exe`) cần từ 20s đến 45s chỉ để suy luận (TTFT), đọc context và lập luận. Đặt timeout ngắn 25s, 45s, 60s sẽ làm chém ngang lưng tiến trình đang xử lý bình thường, gây lỗi 429 giả hoặc timeout giả.
- **Quy chuẩn bắt buộc:**
  * Planner Timeout: Cố định mặc định >= 300s (5 phút).
  * Worker Timeout: Cố định mặc định >= 180s - 300s (3 - 5 phút).
  * Cơ chế Idle Streaming Timeout: Chỉ ngắt khi socket câm lặng hoàn toàn > 20s không nhả token; tuyệt đối cấm dùng trần cứng wall-clock ngắn để kill tiến trình đang stream dữ liệu.

## 8. Nguyên Lý Cưỡng Chế Tầng Cơ Học Thay Cho Prompt (Anti-Overengineering)
- **Dẹp bỏ tầng prompt mềm:** Không dùng prompt để nhắc nhở quy tắc phân tầng, vì context phình to sẽ gây attention drift và ảo giác. Mọi luồng fallback và quota check phải được code hóa cứng trong `dispatch_planner.py`, `claude_worker.py`, và `dispatch_worker.py`.
- **Chống bẫy Over-engineering của Sol:** Không chế thêm các lớp gate rườm rà (assert schema, blocking daemons, approval tokens) gây nguy cơ tê liệt và khóc lóc đóng băng hệ thống. Hệ thống đã có sẵn các gate cơ học, chỉ cần bổ sung đúng 1 lớp fallback an toàn về Coordinator (Hermes session model) khi các lựa chọn primary thất bại.

## 9. Kỹ Thuật Chạy Native Antigravity CLI (`agy.exe`) Trên Windows Sandbox Profiles
- **Cơ chế xác thực Windows Credential Manager (`wincred`):** Binary `agy.exe` trên Windows đọc token từ Windows Keyring qua `TargetName: gemini:antigravity` với `auth_method: consumer`, `token_type: Bearer`, KHÔNG đọc từ `.gemini/oauth_creds.json` trong sandbox profile.
- **Cơ chế nạp token profile động:** Trước khi spawn `agy.exe`, wrapper `ag_cli.py` bắt buộc phải gọi hàm `sync_profile_to_wincred(profile_dir)` sử dụng Win32 API `CredWriteW` để ghi đè token của profile tương ứng vào `gemini:antigravity`.
- **Quy tắc cờ `--project`:** Cờ `--project` của `agy.exe` là local workspace conversation ID (như `default-cli-project`), TUYỆT ĐỐI CẤM truyền GCP Cloud Project ID (`aicode-consumers`) vào tham số dòng lệnh vì sẽ làm hỏng parser và mất context.

## 6. Cơ Chế Hard Guard Của `claude_quota_guard.py` & Kỷ Luật Không Bỏ Cuộc Giữa Chừng
- **Bảo vệ vật lý khi Quota 5h >= 85%:** Lệnh gọi `claude` CLI bị chặn vật lý ở tầng OS (exit 20). `claude_quota_guard.py` tự động phát hiện caller là AI tự động (`is_automated_agent_caller()`) để từ chối các cờ bypass ngầm (`--force-claude`).
- **Kỷ luật Điều tra Đến Cùng (Anti-Deflection):** Khi gặp lỗi hóc búa (như 429 giả mạo do Windows Credential Manager), Coordinator BẮT BUỘC phải dùng read-only tools để đào sâu tới tận binary strings và Win32 API ngay trong phiên hiện tại; CẤM TUYỆT ĐỐI viện cớ bí tắc để thoái thác "xin thêm session mới" khi hệ thống vẫn đang trong tầm kiểm soát.
