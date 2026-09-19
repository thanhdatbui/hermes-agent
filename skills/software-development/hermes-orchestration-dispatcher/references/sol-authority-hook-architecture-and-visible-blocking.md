# Sol Authority Hook Architecture & Visible Blocking Handoff (2026-09-19)

> **Context**: Sếp Kibe chỉ đạo: "Tại sao tao đã setup hook bắt buộc Sol plan rồi mà Coordinator vẫn để tao phải nhắc mới gọi Sol? Sửa thiết kế hook lại, gọi Claude CLI và Sol khi nào 2 con thống nhất thì làm."

---

## 1. Bản chất lỗ hổng kiến trúc cũ (Enforcement at the wrong abstraction layer)

- **Vị trí cũ**: Hook `guard_dispatch_contract.py` đặt ở `pre_tool_call(delegate_task)`.
- **Lý do thất bại**:
  - Khi Coordinator phát hiện bug, bản năng mặc định của LLM là **"Plan → Present text → Ask approval"** trước khi bấm gọi tool.
  - Coordinator ngồi chat dông dài, giải thích nguyên nhân và xin phép sếp duyệt bằng miệng (`plain text output`).
  - Do chưa gọi `delegate_task`, hook cũ hoàn toàn **vô hình**, dẫn đến việc User phải đóng vai người cầm roi nhắc nhở: *"Gọi Sol lên plan đi!"*.
  - User thẳng thắn từ chối giải pháp ghi rule vào `Memory` vì memory chỉ là soft-constraint, không có tính cưỡng chế vật lý.

---

## 2. Bản đồng thuận tuyệt đối giữa Claude Code CLI & GPT-5.6 Sol (100% Consensus)

### Nguyên tắc cốt lõi: "Sol as Compiler Phase"
- **Không ép Coordinator 'nhớ' gọi Sol**: Lập trình viên không cần "nhớ" type-checking, trình biên dịch (Compiler) ép buộc.
- **Loại bỏ quyền Mutation không có Plan**: Không có `SOL_PLAN_ID` $\rightarrow$ Tuyệt đối không được phép mutate code.

### Phân cấp vai trò & Dòng chảy ý tưởng (Chain of Command)
1. **Sếp (User) — Intent Authority**: Đưa ra ý tưởng, mục tiêu, định hướng xử lý gốc.
2. **Coordinator (Hermes) — Context Authority**: Khảo sát hiện trường O(1), gom ngữ cảnh, đóng gói bài toán.
3. **Sol (:20129) — Engineering Authority**: Tổng công trình sư trực tiếp chỉ đạo kỹ thuật. Sol **KHÔNG tự bịa ra plan**, mà đầu vào bắt buộc lấy từ `--goal` (ý tưởng của Sếp) và `--context` (hiện trường Coordinator). Sol chuyển ngữ thành bản vẽ kỹ thuật chi tiết: Decompose tasks, xác định anchor duy nhất (C Invariant `grep -o ... | wc -l == 1`), lệnh test focused <30s, worker budget.
4. **Worker — Execution Authority**: Thợ thi công, nhận Patch Contract chuẩn để gõ code.

---

## 3. Kiến trúc 3 Lớp Bảo Vệ Chuẩn Production

```text
               YÊU CẦU / BUG HIỆN TRƯỜNG
                         │
                         ▼
                    Coordinator
                         │
           (thực hiện thao tác sửa code)
       ┌─────────────────┴─────────────────┐
       ▼                                   ▼
 [Nói miệng / Chat]                [Gọi Mutation Tool]
 - Không tạo ra thay đổi       {delegate_task, patch, write_file}
 - Không ảnh hưởng hệ thống                │
                                           ▼
                                ╔═════════════════════╗
                                ║    MUTATION GATE    ║
                                ╚══════════┬══════════╝
                                           │
                                 Có SOL_PLAN_ID chưa?
                                 ┌─────────┴─────────┐
                                 │                   │
                                YES                  NO
                                 │                   │
                                 ▼                   ▼
                           [EXECUTE]       1. Tự động gọi Sol Planner (:20129)
                                           2. Sinh file sol_plans/<id>.json
                                           3. BLOCK tool call kèm thông báo:
                                              "Đã tự động sinh Sol Plan <id>.
                                               Hãy retry với SOL_PLAN_ID=<id>"
                                                     │
                                                     ▼
                                           Coordinator thấy Plan ID
                                           ngay trong context ➔ Retry chuẩn chỉ!
```

---

## 4. Cơ chế Visible Blocking Resolution & Fallback Valve

### A. Visible Blocking Handoff (Chống Ghost Plan)
- **Cấm Auto-resolve ngầm (Silent continue)**: Nếu hook tự gọi Sol rồi cho chạy tiếp, Coordinator sẽ không biết plan nào vừa sinh, dễ sinh plan rác hoặc mất quyền kiểm soát.
- **Quy trình chuẩn**:
  1. Hook phát hiện thiếu `SOL_PLAN_ID` $\rightarrow$ Tự động kích hoạt subprocess chạy `python D:/Taadaa/tools/sol_planner.py`.
  2. Khi Sol trả về `sol_plan_id`, hook **BLOCK** tool call và trả thông báo tường minh trên stdout:
     `[SOL_GATE AUTO-RESOLVE] 🟢 ĐÃ TỰ ĐỘNG GỌI SOL PLANNER (:20129) VÀ SINH KẾ HOẠCH THÀNH CÔNG! ... Hãy retry với SOL_PLAN_ID=<id>`.
  3. Coordinator nhìn thấy Plan ID ngay trong context và re-dispatch worker đàng hoàng.

### B. Van xả áp toàn diện (Fallback Valve)
Hệ thống **tuyệt đối không bị treo hay deadlock** khi Sol không khả dụng. Hook tự động trao quyền chỉ đạo trực tiếp cho Coordinator khi:
1. **Sự cố kỹ thuật**: Sol timeout > 25s, sập port 20129, lỗi kết nối HTTP.
2. **Sự cố bộ lọc đạo đức (Safety / Policy Refusal)**: Khi bài toán kỹ thuật của farm (CAPTCHA, login, proxy, mail) bị bộ lọc của OpenAI từ chối vì lý do an toàn/chính sách.
3. **Cú pháp Fallback**:
   Hook nhả thông báo `[SOL_GATE FALLBACK VALVE] ⚠️ SOL PLANNER KHÔNG KHẢ DỤNG HOẶC TỪ CHỐI DO POLICY/OFFLINE!` và cấp quyền cho Coordinator re-dispatch với `SOL_FALLBACK: <lý do>`.

### C. Chống lặp đệ quy (Recursion Breaker)
- Cờ `SOL_AUTOCALL_ATTEMPTED=1` được kiểm tra trong context để ngăn hook gọi Sol Planner lặp vô tận khi gặp lỗi.
