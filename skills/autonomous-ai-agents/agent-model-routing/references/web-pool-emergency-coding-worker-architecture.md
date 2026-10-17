# Web-Pool Emergency Coding Worker Architecture: Sol Web (:20129) Quota-Fallback Harness

## 1. Bối cảnh & Mục đích (User Correction 2026-10-16)

Khi các coding CLI trả phí hoặc giới hạn quota nghiêm ngặt (Claude CLI với trần 85% session 5h, Antigravity CLI với burst TPM/503 limits) cạn kiệt hạn mức, hệ thống không được phép đóng băng (zero-downtime).
Kho tài khoản ChatGPT-Web (Sol Web `:20129`) vốn có sẵn cơ chế xoay tua đa tài khoản qua P2C và proxy 4G, hoàn toàn có thể được kích hoạt làm **Tier 4 Emergency Fallback Worker** để duy trì nhịp thi công code tự động.

## 2. So sánh Kỹ thuật: MCP Web Bridge vs Web-Pool Proxy Worker

| Tiêu chí | MCP Web Bridge (Antigravity IDE) | Sol Web Worker Pool (:20129) |
| :--- | :--- | :--- |
| **Bản chất** | Tool-level call từ IDE agent | Upstream Model Provider qua OpenAI API format |
| **Thực thi tool local** | MCP Server parse text/action để ghi file hoặc chạy lệnh | Local Harness (`sol_worker.py`) parse action block để patch & test |
| **Quản lý quota** | 1 tài khoản (dễ chết, dính CAPTCHA là sập toàn bộ) | Multi-account pool (29+ acc) tự động xoay tua qua P2C & 4G proxy |
| **Quyền hạn & An toàn** | Thường thả rông shell/file | Bị khóa trong lồng: Search/Replace O(1) + 1 focused test <30s |

## 3. Ba Trụ Cột Kỹ Thuật Bắt Buộc Khi Dùng Web LLM Làm Coding Worker

Web-based LLM vốn được tối ưu cho giao diện chat người dùng, không có native function calling của API chính ngạch. Để biến nó thành Autonomous Worker chạy vòng lặp ReAct an toàn, harness local bắt buộc phải thực thi 3 cơ chế:

### A. Stateless Web Sessions vs Local Conversation State Engine
- **Vấn đề:** Khi tài khoản Web hiện tại chạm rate-limit (429) hoặc timeout, OmniRoute router sẽ gạt request sang tài khoản tiếp theo trong pool. Tài khoản mới hoàn toàn không có session context của các bước trước.
- **Giải pháp:** 
  - Toàn bộ state và lịch sử hội thoại `[system_prompt, user_goal, assistant_action, tool_result, ...]` được lưu trữ 100% tại bộ nhớ của harness local (`sol_worker.py`).
  - Web session chỉ đóng vai trò compute engine không lưu trạng thái (Stateless). Mỗi turn hoặc mỗi khi đổi tài khoản, local gửi lại context nén đầy đủ.

### B. Cấm Ghi Đè Toàn Phần — Ép Khuôn Search/Replace Patch DSL (Anti-Lazy Code Truncation)
- **Vấn đề:** Khi sinh code diff lớn hoặc sửa file dài (>100 dòng), Web LLM mắc tật "lười code" kinh niên, thường chèn comment tóm tắt như `# ... giữ nguyên logic cũ ...` hoặc `# ... existing code ...`. Nếu cho phép `write_file` toàn phần, file nguồn sẽ bị xóa sạch ruột.
- **Giải pháp:**
  - **TUYỆT ĐỐI CẤM `write_file` toàn phần.**
  - Chỉ hỗ trợ action `PATCH` dạng Search/Replace block:
    ```text
    ACTION: PATCH
    FILE: <relative_path>
    SEARCH:
    <<<<<<<
    <exact_old_code_snippet>
    =======
    <replacement_code_snippet>
    >>>>>>>
    ```
  - Harness local kiểm tra trước khi ghi: đoạn `SEARCH` phải khớp duy nhất 1 vị trí trong file (`matches == 1`), kèm kiểm tra cú pháp AST (`ast.parse`) trên file kết quả. Nếu không khớp hoặc cú pháp lỗi, trả lỗi về context để model tự chỉnh lại.

### C. Tolerant Block Parser (Anti-JSON-Hallucination)
- **Vấn đề:** Giao diện Web không có Grammar Constrained Decoding. Khi context vượt quá 30.000 tokens kèm code có ký tự đặc biệt, nháy kép, xuống dòng, model rất hay sinh JSON vỡ cú pháp khiến `json.loads` bị crash.
- **Giải pháp:**
  - Sử dụng Delimiter Block Regex thay vì JSON.
  - Phân loại rõ các Action hợp lệ:
    - `ACTION: READ` (kèm `FILE: ...`, `OFFSET: ...`, `LIMIT: ...`)
    - `ACTION: PATCH` (kèm block `SEARCH` / `REPLACE`)
    - `ACTION: TEST` (chỉ cho phép chạy đúng lệnh focused test được chỉ định, timeout < 30s)
    - `ACTION: FINISH` (báo cáo hoàn tất kèm diff tóm tắt)

## 4. Thang Điều Phối Mở Rộng (Extended 4-Tier Escalation Ladder)

1. **Tier 1:** Coordinator Tự Vá O(1) (<= 15 dòng, 1 file, verify < 30s).
2. **Tier 2 (Primary Worker):** Agy CLI / Gemini Worker Pool (Nhanh, native tool call).
3. **Tier 2 (Heavyweight Worker):** Claude CLI (Sonnet/Haiku kẹp turns & quota gate).
4. **Tier 4 (Emergency Fallback Worker):** **Sol Web Pool Worker (:20129)**.
   - Kích hoạt khi: Claude CLI chạm trần 85% session HOẶC Agy CLI cạn quota / 503 liên tục.
   - Vận hành: Xoay tua qua kho tài khoản ChatGPT-Web, thực thi patch diff có AST verification và focused test khép kín.

## 5. Các Chốt An Toàn Thực Chiến Khi Triển Khai `sol_worker.py` (2026-10-17)

1. **Phòng vệ Shell Metacharacters:**
   Hàm `is_command_safe` bắt buộc kiểm tra `re.search(r"[;&|`$]", cmd)` để chặn đứng các kỹ thuật ghép lệnh (`pytest && rm ...`, `echo 1 | cat`, subshell `$()`, backticks) khi `execute_command` thực thi lệnh shell.
2. **Atomic Write Khi Áp Dụng Patch:**
   Tuyệt đối không ghi đè trực tiếp lên target file bằng `write_bytes` trần. Bắt buộc ghi ra file tạm `.tmp.<uuid>` rồi thực hiện `os.replace` để nguyên tử hóa thao tác ghi, chống rách/hỏng file nếu tiến trình bị ngắt đột ngột.
3. **Chuẩn Hóa Thông Báo Ngữ Nghĩa AST:**
   Chỉ bổ sung `AST valid.` khi target file là `.py`. Các file định dạng khác (JSON, YAML, text) không được gán nhãn AST bừa bãi.
4. **Validation Hợp Đồng Đầu Vào & Telemetry:**
   Hàm `run_worker_loop` bắt buộc kiểm tra fail-closed `max_turns <= 0` và gắn `correlation_id` ngẫu nhiên cho mỗi phiên làm việc để phục vụ quan sát log có cấu trúc.
5. **Cạm Bẫy `NEED_CONTEXT` Của Closeout Gate Đối Với File Mới Lớn (>20KB):**
   Khi diff của file mới tạo quá lớn, `sol_payload_guard` sẽ kích hoạt truncation digest và chèn chỉ thị an toàn khiến Reviewer trả về `NEED_CONTEXT:<path>`. Để xử lý triệt để, Coordinator cần commit cục bộ sạch và chạy Closeout Gate với `--base HEAD~1 --files <targets>` để thẩm định context toàn vẹn trong cây git.

