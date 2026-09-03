# Subagent Iteration Limits, Coordinator Invariants & E2E Canary Execution (2026-09-03)

## 1. Nguyên nhân cạn kiệt budget Tool Calls / Iterations
- Khi subagent nhận Farm Alert `[MÁY N]`, quy trình thực tế gồm 4 phase:
  1. **Triage (5-10 calls):** Đọc alert, trích xuất hiện trường.
  2. **Investigate & Trace (30-45 calls):** Dump UI XML, inspect hierarchy, trace qua nhiều file registry/flow (`DeviceContext` -> `AdbClient` -> `automation_core`).
  3. **Patch (15-20 calls):** Sửa code, check syntax, chuẩn bị test.
  4. **Validate / Canary Test (20-30 calls):** Chạy PowerShell canary test, đợi máy chạy, đọc summary log.
- **Tổng thực tế:** 70–110 calls cho case cơ bản, 100–150 calls cho case phức tạp.
- Nếu đặt `delegation.max_iterations: 100`, subagent sẽ cạn budget ngay sau bước patch và bị ngắt trước khi kịp chạy canary test.

## 2. Invariant cho Coordinator: CẤM BỎ DỞ & CẤM IN LỆNH BẮT USER CHẠY
- **CẤM:** Khi subagent dừng do `max_iterations` hoặc trả về lệnh PowerShell, Coordinator tuyệt đối KHÔNG in câu lệnh ra ngoài bảo user tự chạy.
- **BẮT BUỘC:** Coordinator phải tự động dispatch tiếp subagent thứ 2 (hoặc tiếp tục delegation) để thực thi lệnh canary test trên máy thật và lấy log artifact xác thực (`SUCCESS`/`FAIL`).

## 3. TikTok Modal Chặn Phím BACK & Dump UI Hierarchy Quirk
- Dialog xin quyền danh bạ/bạn bè của TikTok chặn `KEYCODE_BACK` (bấm BACK modal không tắt).
- `DeviceContext` không có method `.dump_hierarchy()`, cần trích xuất qua `automation_core.ui.dump_current_ui(ctx.adb)` để parse XML node "Không cho phép" / "Don't allow" và tap trực tiếp theo bounds node, hoặc fallback tap theo tỷ lệ `(w * 0.305, h * 0.639)`.
