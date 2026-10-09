# Nested Combo Spillover & Fast Request Log Inspection

## 1. Quick Diagnostic Endpoints (O(1) Live API)
- **Combos Configuration:** `GET /api/combos` (Kiểm tra thứ tự các tiers, strategy, fallback config, targetTimeoutMs, failoverBeforeRetry).
- **Live Request Logs:** `GET /api/usage/request-logs?limit=N`
  - Định dạng trả về: `<Timestamp UTC> | <Model> | <Provider> | <Account/Email> | <Prompt Tokens Tx> | <Completion Tokens TO> | <HTTP Status>`
  - Lưu ý quan trọng: Endpoint `/api/logs` không tồn tại trong OmniRoute. Sử dụng `/api/usage/request-logs` để đọc O(1) mà không cần grep qua file log khổng lồ.

## 2. Root Cause: Spillover to Free Tier despite Remaining Quota
Khi thấy model rơi từ primary Gemini pool sang Free model (như `oc/muse-spark-1.3-contributor-free`) dù quota Gemini vẫn còn:
1. **Kiểm tra cấu trúc Combo:** Thường `omni-worker` là **nested combo** (Tier 1: `ag-gemini-pool-3`, Tier 2: `ag-claude`, Tier 3: `omni-free`).
2. **Concurrency / In-flight Saturation:** Khi có các request nặng (Tx > 80k–150k tokens) đang chiếm giữ các connection slot của pool Antigravity Gemini, các connection này chạm ngưỡng giới hạn đồng thời.
3. **Failover Before Retry Trigger:** Nếu cấu hình combo cha có `"failoverBeforeRetry": true`, request mới đến sẽ không chờ đợi trong hàng đợi mà ngay lập tức failover sang Tier tiếp theo.
4. **Cascade Drop:** Nếu Tier 2 (`ag-claude`) đang bị 429 rate limit, request sẽ rơi thẳng xuống Tier 3 (`omni-free`), route vào model đầu tiên của omni-free (`muse-spark-1.3`).
