# OmniRoute Reset-Aware vs Priority Quota Preflight Freeze Pitfall (Case 2026-09-13)

## Triệu chứng
1. Pool Gemini có tới 81 tài khoản Antigravity active, quota dồi dào nhưng toàn bộ traffic bị nghẽn chậm (freeze 10–30s) hoặc rớt đài sang Tier 2 (`ag-claude`), rồi tiếp tục kẹt ở `waiting_account_slot` hoặc rơi xuống Tier 3 (`omni-free` / Muse Spark).
2. Request gọi vào `ag-gemini-pool-3` bị timeout, pending queue dồn ứ hàng loạt request không thoát được.

## Nguyên nhân gốc rễ (Root Cause)
1. **`reset-aware` preflight quota scoring stall:**
   - Khi combo có nhiều accounts (ví dụ 81 accounts Antigravity), chiến lược `reset-aware` kích hoạt hàm `orderTargetsByResetAwareQuota` -> gọi pre-flight fetch snapshot quota cho từng connection (`fetchResetAwareQuotaWithCache`).
   - Khi số lượng accounts lớn, việc query/tính toán quota đồng thời làm request bị stall/freeze trong 10-30s trước khi kịp dispatch request thực tế, dẫn tới client-side hoặc gateway timeout.
2. **`failoverBeforeRetry: true` ở combo cha/con:**
   - Khi Tier 1 (Gemini) bị stall do preflight quota check, router coi như Tier 1 thất bại và ngay lập tức failover sang Tier 2 (`ag-claude`).
   - Lúc này các tài khoản Claude cũng bị dồn tải, chạm giới hạn `maxConcurrent: 2` và rơi vào trạng thái `waiting_account_slot`, làm treo cứng toàn bộ pipeline.
3. **CẤM gỡ 9router / 9r-free khỏi fallback chain của Hermes:**
   - `9r-free` luôn nằm ở tầng cuối cùng (`fallback_providers` trong config Hermes) làm safety net. Tuyệt đối KHÔNG được tự ý gỡ hoặc thay đổi khi gặp sự cố ở các tầng trên.

## Cách xử lý chuẩn (Canonical Fix)
1. **Đổi Strategy của pool lớn sang `priority`:**
   - Đối với pool có số lượng tài khoản lớn (như `ag-gemini-pool-3` với 81 accounts), chuyển `strategy` từ `reset-aware` sang `priority` qua PATCH API:
     ```json
     PATCH /api/combos/:id
     {
       "strategy": "priority",
       "config": {
         "failoverBeforeRetry": false,
         "maxRetries": 3,
         "retryDelayMs": 500
       }
     }
     ```
   - Chiến lược `priority` dispatch O(1) ngay lập tức vào connection sẵn sàng đầu tiên mà không tốn thời gian tính toán quota preflight trên 81 accounts.
2. **Tắt `failoverBeforeRetry` để thử trong nội bộ pool trước:**
   - Đặt `failoverBeforeRetry: false` kèm `maxRetries: 3` để khi 1 account bận slot concurrency (`maxConcurrent: 2`), router sẽ nhảy sang account tiếp theo trong cùng pool Gemini thay vì văng ra khỏi combo.
