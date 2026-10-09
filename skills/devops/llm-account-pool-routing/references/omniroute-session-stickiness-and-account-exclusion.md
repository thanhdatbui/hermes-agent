# Bẫy Session Stickiness & 403 Exclusion trong OmniRoute Multi-Account Pool

## 1. Hiện tượng thực tế (Symptom)
- Combo cha (ví dụ `omni-worker`) có Tier 1 là pool `ag-gemini-pool-3` (hơn 70 tài khoản Gemini Flash active và còn đầy quota).
- Tuy nhiên khi chạy tải (subagent, tool gọi LLM liên tục), request chỉ dồn vào 1–2 tài khoản hoặc lập tức tràn xuống Tier 2 Claude (`ag-claude`), bỏ rơi hàng chục account Gemini phía sau không hề được đụng tới.
- Hậu quả: Khi rơi xuống Claude (nơi đa số acc Antigravity không có quota Claude Sonnet 4.6), request dính Semaphore timeout 30s hoặc 403, gây treo nghẽn hàng loạt.

## 2. Nguyên nhân gốc rễ trong Source Code OmniRoute

### A. Session Stickiness ngầm (`sessionStickiness.ts`)
- Mặc định ở strategy `priority`, hàm `applySessionStickiness()` tính hash các tin nhắn (`deriveMessageHash`) và ghim request vào đúng `connectionId` của account đã từng phục vụ thành công trong vòng 15 phút (`TTL_MS = 15 * 60 * 1000`).
- Khi hash khớp, router nhấc target đó lên vị trí index 0 (`reordered = [orderedTargets[stickyIdx], ...]`).
- Router KHÔNG xoay tua qua các account còn lại mà dồn toàn bộ lượt gọi tiếp theo vào account bị ghim này.
- Khi account này chạm trần concurrency (`maxConcurrency = 2`), router kích hoạt spillover hoặc timeout, thay vì chia đều tải.

### B. Account lỗi 403 kích hoạt loại trừ hàng loạt (`targetExhaustion.ts`)
- Trong pool nếu tồn tại dù chỉ 1–2 account bị lỗi authentication/upstream 403 (ví dụ account bị revoke hoặc mất quyền):
  ```typescript
  if (AUTH_LEVEL_ERROR_STATUSES.includes(result.status)) {
    markAuthLevelExhaustion(target, { result, sets, log, tag });
  }
  ```
- Kết hợp với cấu hình `nestedComboMode: "flatten"` mặc định, router làm phẳng cả sub-combo Gemini và Claude thành 1 danh sách. Khi gặp 403 hoặc lỗi upstream, router đánh dấu target lỗi và nhanh chóng trượt xuống các target phía sau (Claude), bỏ qua các nhánh Gemini khác.

## 3. Quy trình khắc phục chuẩn (Resolution Pattern)

1. **Thanh lọc triệt để account lỗi 403/expired khỏi pool**:
   - Truy vấn `/api/usage/call-logs` lọc status 403 / 401 để tìm đích danh `connectionId` chết.
   - Gọi API cập nhật combo (`PUT /api/combos/:id`) loại bỏ các connectionId này ra khỏi danh sách `models`.

2. **Tắt Session Stickiness trên các combo pool**:
   - Set `"disableSessionStickiness": true` trong `config` của cả combo cha (`omni-worker`) và combo pool con (`ag-gemini-pool-3`).
   - Đảm bảo pool xoay vòng tự do qua toàn bộ danh sách account thay vì bị khóa chặt vào 1 account duy nhất.

3. **Thiết lập cơ chế thực thi đóng (`nestedComboMode: "execute"`)**:
   - Cấu hình combo cha:
     ```json
     {
       "config": {
         "nestedComboMode": "execute",
         "disableSessionStickiness": true
       }
     }
     ```
   - Chế độ `execute` bắt buộc OmniRoute phải coi `ag-gemini-pool-3` là một runtime unit độc lập, xử lý và thử hết các account trong pool Gemini theo chiến lược round-robin nội bộ trước khi được phép fallback sang Tier tiếp theo.

4. **Reset Resilience State**:
   - Gửi POST tới `/api/resilience/reset` để xóa sạch các circuit breaker và lockout map tạm thời trong bộ nhớ đệm của OmniRoute.
