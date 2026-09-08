# Subagent Iteration Limits, Coordinator Invariants & E2E Canary Execution (2026-09-03)

## 1. Nguyên nhân cạn kiệt budget Tool Calls / Iterations
- Khi subagent nhận Farm Alert `[MÁY N]`, quy trình thực tế gồm 4 phase:
  1. **Triage (5-10 calls):** Đọc alert, trích xuất hiện trường.
  2. **Investigate & Trace (30-45 calls):** Dump UI XML, inspect hierarchy, trace qua nhiều file registry/flow (`DeviceContext` -> `AdbClient` -> `automation_core`).
  3. **Patch (15-20 calls):** Sửa code, check syntax, chuẩn bị test.
  4. **Validate / Canary Test (20-30 calls):** Chạy PowerShell canary test, đợi máy chạy, đọc summary log.
- **Tổng thực tế:** 70–110 calls cho case cơ bản, 100–150 calls cho case phức tạp.
- Nếu đặt `delegation.max_iterations` quá cao mà không có hard timeout, subagent sẽ rơi vào Analysis Paralysis, đốt sạch token/thời gian mà không làm gì.
- **BÀI HỌC VỤ NGÂM 3 TIẾNG (Case M41 - 07/09/2026)**:
  + Khi subagent chạm trần `max_iterations`, runtime Hermes (`handle_max_iterations`) ép ngắt tool và yêu cầu tóm tắt. Model reasoning (như `ag-gemini-pool-3`) bị dính **bẫy ảo giác (confabulation)**: tự nhận trong bài tóm tắt là "đã áp patch và test passed" dù thực tế chưa hề gọi tool sửa file.
  + Tháo bỏ phanh timeout (`child_timeout_seconds: None`) khiến 1 worker ngâm tới 75 phút / 54 phút.
  + **CHUẨN HÓA MỚI (User chốt & Claude CLI APPROVED 07/09/2026)**:
    * `delegation.model: ag-claude` (thay vì gemini-pool hay tự bịa hành động).
    * `delegation.max_iterations: 15` (giới hạn chặt, ép decompose hoặc kết thúc nhanh).
    * `delegation.child_timeout_seconds: 600` (hard cap 10 phút, quá giờ runtime tự kill).
    * `delegation.reasoning_effort: medium` (giảm 50% độ trễ turn).
    * **Zero-Trust Verification**: Coordinator tuyệt đối không tin prose báo cáo; sau khi worker xong BẮT BUỘC chạy `git status --porcelain` và `git diff` kiểm tra độc lập.
- **PITFALL TRÔI CẤU HÌNH WORKER SANG `ag-gemini-pool-3` (08/09/2026)**:
  + Nếu `config.yaml` bị trôi hoặc vô tình set `delegation.model: ag-gemini-pool-3` (kèm `reasoning_effort: high`), mỗi lượt API call của Gemini tốn ~65-70 giây do sinh thinking stream quá dài.
  + Hậu quả trực tiếp: Chỉ thực hiện được 9 calls đã cạn sạch 600 giây timeout (`status=timeout, api_calls=9, 600.08s`), worker bị runtime kill trước khi kịp ghi file. Trong khi đó cùng task đó trên `ag-claude` (effort medium) hoàn tất 5 calls và 9 tests chỉ mất 82 giây.
  + **Quy chuẩn sửa ngay**: Khi thấy worker báo timeout >600s với số calls thấp (<10 calls), kiểm tra ngay `hermes config show` hoặc `config.yaml`. Chạy lệnh chuẩn hóa:
    ```bash
    hermes config set delegation.model ag-claude
    hermes config set delegation.reasoning_effort medium
    ```
- Nếu đặt `delegation.max_iterations: 100`, subagent sẽ cạn budget ngay sau bước patch và bị ngắt trước khi kịp chạy canary test.

## 2. Invariant cho Coordinator: CẤM BỎ DỞ & CẤM IN LỆNH BẮT USER CHẠY
- **CẤM:** Khi subagent dừng do `max_iterations` hoặc trả về lệnh PowerShell, Coordinator tuyệt đối KHÔNG in câu lệnh ra ngoài bảo user tự chạy.
- **BẮT BUỘC:** Coordinator phải tự động dispatch tiếp subagent thứ 2 (hoặc tiếp tục delegation) để thực thi lệnh canary test trên máy thật và lấy log artifact xác thực (`SUCCESS`/`FAIL`).

## 3. TikTok Modal Chặn Phím BACK & Dump UI Hierarchy Quirk
- Dialog xin quyền danh bạ/bạn bè của TikTok chặn `KEYCODE_BACK` (bấm BACK modal không tắt).
- `DeviceContext` không có method `.dump_hierarchy()`, cần trích xuất qua `automation_core.ui.dump_current_ui(ctx.adb)` để parse XML node "Không cho phép" / "Don't allow" và tap trực tiếp theo bounds node, hoặc fallback tap theo tỷ lệ `(w * 0.305, h * 0.639)`.

## 4. Phân Biệt Claude CLI Local Binary vs OmniRoute / 9Router
- **Claude Code CLI (`claude -p`):** Chạy trực tiếp bằng binary local (`Anthropic.ClaudeCode`) với cơ chế xác thực riêng của Anthropic (OAuth/Subscription). **Hoàn toàn KHÔNG đi qua OmniRoute hay 9Router**.
- **Cấu hình gọi Claude CLI:** Khi user yêu cầu gọi Claude CLI, luôn thực thi với cờ model Opus cao nhất và effort kịch trần:
  ```bash
  claude -p "<prompt>" --model opus --effort max --output-format text
  ```
- **OmniRoute (`localhost:20129`) vs 9Router (`localhost:20128`):** Là các cổng LLM proxy nội bộ quản lý Antigravity pool, OpenRouter upstream và model fallback cho Hermes Agent.
