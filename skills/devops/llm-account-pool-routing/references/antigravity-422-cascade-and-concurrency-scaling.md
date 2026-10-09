# Antigravity 422 Cascade Diagnosis & Concurrency Scaling Runbook

## 1. Context & Pathology
- **Triệu chứng UI**: Tab Logs của OmniRoute (`:20129/dashboard/logs`) xuất hiện mũi tên cong `↳` màu vàng cam cạnh số `200 OK` ở cột Status hàng loạt.
- **Bản chất**: `↳` là nút "Go to parent", đánh dấu request này là kết quả thành công của một nhánh thử lại/failover (`isRetry: true`) trong cùng chuỗi `correlationId`.
- **Cơ chế nghẽn & sụp đổ theo tầng (Cascade Breakdown)**:
  1. Combo `omni-worker` được cấu hình phân tầng: `Tier 1: ag-gemini-pool-3 (Pro)` -> `Tier 2: ag-gemini-free-pool (Free)`.
  2. Mặc định tài khoản Pro được đặt `max_concurrent: 2`. Khi có đợt tải dồn dập (>80 requests trong 2 phút do subagents/Hermes song song), 20 nick Pro kịch trần 40 luồng (`isAccountSemaphoreFull`).
  3. Cơ chế `runtimeUnitCapacity` và `queueTimeout: 3000ms` phát hiện Pro đầy tải, lập tức xả tràn (overflow) xuống Tier 2 Free Pool.
  4. Trong Free Pool tồn tại **23 tài khoản thiếu `project_id`** (chưa onboard Cloud Code / Gemini Code Assist). Khi OmniRoute dispatch vào các nick này, Google từ chối ngay lập tức bằng mã lỗi `422 Unprocessable Entity` ("Missing Google projectId for Antigravity account").
  5. Dính 422, OmniRoute tiếp tục failover sang các nick Free hợp lệ khác, tạo ra chuỗi retry dài và các request thành công mang icon `↳`.

---

## 2. Bẫy Cronjob Tự Bật Lại (Cron Reactivation Hazard)
Khi cách ly các tài khoản lỗi bằng cách set `is_active = 0`, cần kiểm tra ngay các watchdog/cronjob chạy định kỳ.
Trong hệ thống, job `omni-activate-soaked-codex` (`cron_omni_activate_soaked_codex.py`, chạy mỗi 1h) có câu lệnh:
```sql
UPDATE provider_connections 
SET is_active = 1 
WHERE provider = 'antigravity' 
  AND is_active = 0 
  AND test_status = 'active';
```
Vì các tài khoản thiếu `project_id` có `test_status` vẫn là `active`, cron này sẽ tự động bật `is_active = 1` trở lại sau mỗi 60 phút, phá vỡ hoàn toàn sự cách ly.

### Cách khắc phục:
Siết chặt điều kiện SQL trong cronjob:
```sql
UPDATE provider_connections 
SET is_active = 1 
WHERE provider = 'antigravity' 
  AND is_active = 0 
  AND test_status = 'active'
  AND project_id IS NOT NULL 
  AND project_id != '';
```

---

## 3. Quy tắc Concurrency Scaling An toàn cho Antigravity
- **Tài khoản Thường (Free / Standard Tier)**: BẮT BUỘC giữ nguyên `max_concurrent: 2`. Hạn mức RPM/TPM của tài khoản thường từ Google rất thấp. Nâng lên 3 sẽ gây bóp băng thông, ngâm request >60s hoặc dính `429 Rate Limit`.
- **Tài khoản Pro (`g1-pro-tier` / `Google AI Pro`)**: Có thể nâng an toàn lên **`max_concurrent: 3`**.
  * 20 nick Pro $\times$ 3 = **60 luồng song song** (tăng 50% trần chịu tải).
  * Thuật toán `least-used` của `omni-worker` đảm bảo tải được tản đều vào các account ít việc nhất, hạn chế tối đa việc dồn cục request nặng vào cùng một OAuth connection.
- **Hiệu lực**: SQLite table `provider_connections` có in-memory TTL cache 5 giây (`TTLCache(5000)` trong `readCache.ts`). Mọi thay đổi qua lệnh SQL trực tiếp đều có hiệu lực sau tối đa 5 giây mà không cần restart OmniRoute.

---

## 4. Runbook Điều tra & Cách ly Nhanh (O(1))

```python
import sqlite3

conn = sqlite3.connect(r"C:\Users\Kibe\.omniroute\storage.sqlite")
cur = conn.cursor()

# 1. Cách ly toàn bộ Antigravity thiếu project_id
cur.execute("""
    UPDATE provider_connections
    SET is_active = 0, updated_at = CURRENT_TIMESTAMP
    WHERE provider = 'antigravity' AND (project_id IS NULL OR project_id = '');
""")
print(f"Isolated {cur.rowcount} invalid accounts.")

# 2. Scale concurrency = 3 cho Pro
cur.execute("""
    UPDATE provider_connections 
    SET max_concurrent = 3, updated_at = CURRENT_TIMESTAMP
    WHERE provider = 'antigravity' AND (
        provider_specific_data LIKE '%g1-pro-tier%' OR 
        provider_specific_data LIKE '%Google AI Pro%' OR
        provider_specific_data LIKE '%"plan":"Pro"%'
    );
""")
print(f"Scaled {cur.rowcount} Pro accounts to max_concurrent=3.")

conn.commit()
conn.close()
```
