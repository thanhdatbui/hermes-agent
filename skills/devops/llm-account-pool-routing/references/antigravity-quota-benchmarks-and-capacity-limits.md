# Antigravity Quota Benchmarks & Capacity Limits (Free vs Pro)

Dữ liệu định lượng thực tế đối soát từ hơn 120.000 request và 220.000 quota snapshots trong `C:\Users\Kibe\.omniroute\storage.sqlite` (2026-09-07).

---

## 1. Bảng So Sánh Năng Lực Thực Tế (Empirical Capacity Matrix)

| Chỉ số | Tài khoản Free (Starter Quota) | Tài khoản Trả Phí (Google AI Pro) | Tỷ lệ Pro / Free |
| :--- | :--- | :--- | :--- |
| **Hạn mức tổng / Chu kỳ tuần** | **~190 – 250 request** | **~8.000 – 13.000 request** | **Pro gấp ~45 – 50 lần** |
| **Tổng Token (In + Out + Cache)** | **~22M – 33M tokens / tuần** | **~1,1 Tỷ – 1,8 Tỷ tokens / tuần** | **Pro gấp ~50 – 60 lần** |
| **Sức chịu dồn tải liên tục (Burst)** | **~70 – 90 request trong 10–15 phút** (Sau đó Google trả HTTP 429 và cạn quota) | **3.000 – 5.000 request / ngày** (Chạy liên tục không bị nghẽn) | Pro không bị tụt ngắt giữa chừng |
| **Cơ chế Reset Quota** | Rolling window 7 ngày kể từ lúc kích hoạt tải | Rolling window 7 ngày kể từ lúc kích hoạt tải | Cả hai dùng chu kỳ 7 ngày |
| **Vai trò tối ưu trong Routing** | **Phao cứu sinh ở đuôi combo** (Natural Spillover khi dàn Pro bận) | **Worker chính ở đầu combo** (`pool-1` đến `pool-12`) | Không đảo lộn vị trí |

---

## 2. Bằng Chứng Thực Nghiệm Từ Dữ Liệu Production

### A. Tài khoản Free (Antigravity Starter Quota)
- **`thanhdatbui1995@gmail.com`**: 
  - Ngày 07/09/2026: gánh 93 request liên tục từ `01:04` đến `01:14` UTC (91 req 200 OK), dính 429 lúc `01:14:23` UTC.
  - Tổng chu kỳ tuần: 193 requests, 22.52M tokens in, 70.9k tokens out, 17.6M cache read.
  - Snapshot quota: `remaining_percentage: 0.0%`, `is_exhausted: 1`, reset vào `2026-09-14T01:04:02Z` (sau đúng 7 ngày).
- **`brittanysbarneskn2xa@gmail.com`**:
  - Chạy rải rác 3 ngày: 113 req (03/09) + 75 req (04/09) + 16 req (07/09).
  - Tổng chu kỳ: 208 requests, 32.76M tokens in, 48.2k tokens out, 29.27M cache read.
  - Snapshot quota: `remaining_percentage: 0.0%`, `is_exhausted: 1`, reset vào `2026-09-11T03:23:47Z`.
- **`alicelmoralesjvcrj@gmail.com`**:
  - Ngày 07/09/2026: gánh 74 request liên tục trong 3 phút (`03:20` - `03:23` UTC).
  - Tổng chu kỳ: 250 requests, 24.40M tokens in, 126.6k tokens out.
  - Snapshot quota: `remaining_percentage: 0.95%` (đã tiêu hao 99% hạn mức), reset vào `2026-09-12T23:34:16Z`.

### B. Tài khoản Trả Phí (Google AI Pro)
- **`dokieu04092004@gmail.com`**: 13.393 requests, 1,83 Tỷ tokens in, 5,87M tokens out, 1,63 Tỷ cache read trước khi cạn 0.0%.
- **`marcusephillips52sns@gmail.com`**: 12.260 requests, 1,79 Tỷ tokens in, 6,35M tokens out.
- **`bobbyxruizz0s0o@gmail.com`**: Riêng ngày 07/09/2026 xử lý **3.216 requests / 396M tokens in** mà vẫn còn **30.27% quota**.

---

## 3. Bộ Truy Vấn Chẩn Đoán Quota O(1) Chuẩn Xác

### A. Tra cứu tình trạng Quota Snapshots mới nhất của toàn Pool
```sql
WITH latest AS (
    SELECT connection_id, window_key, remaining_percentage, is_exhausted, next_reset_at, created_at,
           ROW_NUMBER() OVER (PARTITION BY connection_id, window_key ORDER BY created_at DESC) as rn
    FROM quota_snapshots
    WHERE provider = 'antigravity'
)
SELECT l.connection_id, p.name, p.email, 
       json_extract(p.provider_specific_data, '$.subscriptionTier') as sub_tier, 
       l.window_key, l.remaining_percentage, l.is_exhausted, l.next_reset_at
FROM latest l
LEFT JOIN provider_connections p ON p.id = l.connection_id
WHERE l.rn = 1 AND l.window_key IN ('gemini-3.8-flash-tiered', 'gemini_weekly')
ORDER BY l.is_exhausted DESC, l.remaining_percentage ASC;
```

### B. Lọc Request Thật Trong Ngày (Loại trừ nhiễu `connection-test`)
Scheduler OmniRoute quét kiểm tra kết nối định kỳ 5 phút/lần ghi log `model: connection-test` (0 token). Khi đếm tải thực tế bắt buộc lọc:
```sql
SELECT 
    account,
    COUNT(*) as total_calls,
    SUM(CASE WHEN status = 200 THEN 1 ELSE 0 END) as ok_200,
    SUM(CASE WHEN status != 200 THEN 1 ELSE 0 END) as fail_cnt,
    GROUP_CONCAT(DISTINCT status) as statuses,
    GROUP_CONCAT(DISTINCT error_summary) as errors
FROM call_logs 
WHERE timestamp >= 'YYYY-MM-DD' 
  AND model NOT IN ('connection-test', 'model-sync')
GROUP BY account
ORDER BY total_calls DESC;
```

### C. Bóc Tách Lượng Token Đã Tiêu Thụ Theo Tài Khoản (`usage_history`)
```sql
SELECT 
    account_label,
    COUNT(*) as total_reqs,
    ROUND(SUM(tokens_input) / 1000000.0, 2) as in_m_tokens,
    ROUND(SUM(tokens_output) / 1000.0, 1) as out_k_tokens,
    ROUND(SUM(tokens_cache_read) / 1000000.0, 2) as cache_m_tokens,
    MIN(timestamp) as first_seen,
    MAX(timestamp) as last_seen
FROM usage_history
WHERE provider = 'antigravity'
GROUP BY account_label
ORDER BY total_reqs DESC;
```

---

## 4. Cơ Chế Quota Claude (Opus & Sonnet Chung Pool Tuyệt Đối) (2026-09-08)

### A. Đối Soát Thực Tế Dữ Liệu SQLite & Upstream Google
- **Chung 1 Bucket Quota Tuyệt Đối (100%)**:
  - Đối soát **18.490 cặp snapshot đồng thời** giữa `claude-sonnet-4-6` và `claude-opus-4-6-thinking` trong bảng `quota_snapshots`: **18.490/18.490 cặp (100%) trùng khớp tuyệt đối** về `remaining_percentage` và `next_reset_at` (0 sai lệch).
  - Khi gọi Sonnet làm tụt quota, Opus tụt chính xác từng % tương ứng và ngược lại.
- **Bản Chất Upstream Google Cloud Code (`v1internal:retrieveUserQuotaSummary`)**:
  - Google gom toàn bộ các model Claude & third-party vào duy nhất 1 Family Group: `displayName: "Claude and GPT models"`, bucketId: `claude-gpt-weekly`.
  - Google **không cấp bucket riêng** cho từng model Opus hay Sonnet.
- **Router Lockout Scope (`family:claude`)**:
  - Trong `open-sse/services/antigravityQuotaFamily.ts`, mọi model mang tiền tố `claude-`, `cloud-`, hoặc `anthropic/` đều map về `family:claude`.
  - Khi một tài khoản bị lỗi Rate Limit (HTTP 429) hoặc Quota Exceeded trên Sonnet, OmniRoute kích hoạt cooldown theo family `family:claude`, lập tức khóa cả Opus trên cùng connection đó.
- **Định Tuyến & Sử Dụng An Toàn**:
  - Tài khoản Free Starter Quota cũng được cấp quota Claude nhưng dung lượng rất mỏng (~190-250 req/tuần, dồn tải 70-90 req là cạn 0%). Tuyệt đối không dùng Starter làm worker chính cho Claude; chỉ dùng dàn Pro cho các combo `ag-claude`, `ag-opus`.

