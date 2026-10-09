# Nested Combo Failover Before Retry & Pool Sizing Pitfall

## Bối cảnh & Hiện tượng
Khi một request đến combo cha (ví dụ `omni-worker`) có kiến trúc đa tầng lồng nhau:
- **Tier 1:** `ag-gemini-pool-3` (81 accounts, reset-aware/priority)
- **Tier 2:** `ag-claude`
- **Tier 3:** `omni-free` (chứa `muse-spark`)

Mặc dù Tier 1 còn quota dồi dào trên hàng chục tài khoản, request vẫn có thể bất ngờ nhảy thẳng xuống Tier 3 (Muse Spark) khi tài khoản đầu tiên bận context lớn (~90k-140k tokens) hoặc chạm `maxConcurrent: 2`.

## Nguyên nhân cốt lõi (Root Cause)
1. **`failoverBeforeRetry: true` ở Combo Cha:** Khi `failoverBeforeRetry = true` kết hợp `maxRetries = 0` hoặc `retryDelayMs = 0`, router coi việc tài khoản đầu tiên trả về 429/bận là toàn bộ Tier 1 bị lỗi -> router không thực hiện quay vòng sang các account tiếp theo trong pool con mà lập tức trượt xuống Tier 2 / Tier 3.
2. **Ảo giác số lượng tài khoản (Danh nghĩa vs Thực tế):**
   - Không được nhầm lẫn giữa 9Router (:20128) và OmniRoute (:20129). OmniRoute quản lý 81 connections trong khi 9Router local sqlite có thể chỉ lưu subset kết nối. Phải query đúng API `/api/combos` và `/api/providers` của instance đang phục vụ.
   - Khi pool con có nhiều tài khoản, mỗi tài khoản có `maxConcurrent = 2` và `priority` dạng thác đổ (ordered spillover), tải sẽ dồn vào top tài khoản đầu tiên.

## Cách xử lý chuẩn (Canonical Fix)
Để combo con tự động luân chuyển sang các account còn quota/slot mà không nhảy xuống tier free:
1. **Cấu hình lại Combo Cha qua API PATCH `/api/combos/<id>`:**
   - `failoverBeforeRetry: false` (bắt buộc router thử hết cơ chế của pool con trước khi nhảy tầng).
   - `maxRetries: 3` (hoặc 5).
   - `retryDelayMs: 1000` (giãn cách 1s để pool kịp chọn connection kế tiếp).
2. **Kiểm tra sau khi PATCH:**
   Query `GET /api/combos` để xác nhận `config` của combo cha đã merge đầy đủ các flags, không làm mất các options tối ưu hoá khác (`disableSessionStickiness`, `trackMetrics`,...).
