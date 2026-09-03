# OmniRoute — Proxy Auth & Account Diagnostics

## Session: 2026-09-03 — Proxy Missing Auth, Account Health, Lỗi Đỏ

### 1. DB thực của OmniRoute vs 9Router
- **OmniRoute** chạy port `20129`, DB tại `~/.omniroute/storage.sqlite` (legacy path `.omniroute` có priority cao hơn `AppData/Roaming/omniroute`).
- DB thứ hai tại `AppData/Roaming/omniroute/storage.sqlite` là fallback — OmniRoute **đọc file nào tìm thấy trước**.
- Khi sửa SQLite: query `~/.omniroute/storage.sqlite`, không phải `AppData/Roaming`.

### 2. Phân biệt "nãy xanh, giờ đỏ" — proxy auth thiếu
- **Triệu chứng:** Account hiện xanh lúc token còn hạn trong cache. Sau ~1 tiếng, token hết hạn, OmniRoute gọi Google OAuth refresh qua proxy → proxy từ chối → UI chuyển đỏ (`Token expired and refresh failed` / `fetch failed` / `network/timeout`).
- **Root cause pattern:** Proxy được thêm vào `proxy_registry` nhưng để **trống username/password** → MikroTik từ chối auth khi refresh OAuth.
- **Diagnosis query:**
```sql
SELECT id, name, host, port, username, password FROM proxy_registry
WHERE username = '' OR username IS NULL;
```
- **Fix:** `UPDATE proxy_registry SET username = 'admin@1', password = 'admin@1' WHERE host = 'mirotik1.taadaa.click' AND (username = '' OR username IS NULL);`

### 3. Circuit breaker / refreshCircuit cần reset sau khi fix proxy
Sau khi fix proxy auth, account vẫn có thể stuck trong `refreshCircuit` (cooldown `until`). Reset:
```sql
-- Xóa refreshCircuit trong provider_specific_data
UPDATE provider_connections
SET error_code = NULL, last_error = NULL, rate_limited_until = NULL,
    provider_specific_data = json_remove(provider_specific_data, '$.refreshCircuit'),
    test_status = 'active', updated_at = datetime('now')
WHERE id = '<connection_id>';
```
Sau đó gọi `POST /api/providers/<id>/test` để force probe.

### 4. Bật lại account bị toggle off
```sql
UPDATE provider_connections SET is_active = 1, updated_at = datetime('now')
WHERE provider = 'antigravity' AND is_active = 0;
```

### 5. Kiểm tra account có thực sự chạy hay chỉ health-check
Dấu hiệu account **không thực sự xử lý request**:
- `tokens_input = 0` trong `usage_history`
- `last_used_at = NULL` và `consecutive_use_count = 0` trong `provider_connections`
- Toàn bộ `call_logs` là `model = 'connection-test'`
```sql
SELECT pc.name, pc.priority,
    count(uh.id) as req_count, sum(uh.tokens_input) as tokens_in,
    pc.last_used_at
FROM provider_connections pc
LEFT JOIN usage_history uh ON pc.id = uh.connection_id
WHERE pc.provider = 'antigravity'
GROUP BY pc.id ORDER BY pc.priority ASC;
```

### 6. Phân loại lỗi trong call_logs
```sql
SELECT status, count(*), error_type, error_summary
FROM call_logs WHERE connection_id = '<id>'
GROUP BY status, error_type;
```
- **403 `project_route_error`**: projectId không hợp lệ với account, cần reconnect OAuth / Google chưa hoàn thành Code Assist onboarding.
- **429 semaphore timeout**: Account đang bị rate-limit hoặc semaphore contention.
- **409 Hard connection binding mismatch**: Combo routing conflict.
- **422 `missing_project_id`**: Account có `projectId = ''` → chưa hoàn thành Gemini Code Assist onboarding → reconnect.

### 7. Sync quota cho tất cả accounts
```bash
curl -s -X POST http://localhost:20129/api/usage/provider-limits
# returns {"total": N, "succeeded": N, "failed": 0}
```

### 8. Proxy assignment: scope 'account' vs 'provider'
- `scope = 'provider'` → áp proxy cho toàn bộ provider antigravity (round-robin tất cả proxy trong list).
- `scope = 'account'` → áp proxy riêng cho từng connection_id (priority cao hơn).
```sql
SELECT pa.scope, pa.scope_id, pr.name, pr.host, pr.port
FROM proxy_assignments pa
JOIN proxy_registry pr ON pa.proxy_id = pr.id
WHERE pa.scope = 'account';
```

### 9. Test proxy thực qua Python
```python
import urllib.request
proxy_url = 'http://admin@1:admin@1@mirotik1.taadaa.click:10003'
proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
opener = urllib.request.build_opener(proxy_handler)
req = urllib.request.Request('https://oauth2.googleapis.com/token', headers={'User-Agent': 'curl/7.88.1'})
try:
    with opener.open(req, timeout=5) as resp:
        print('Connected, HTTP:', resp.status)
except urllib.error.HTTPError as e:
    print('Proxy OK, Google returned:', e.code)  # 404 là OK, proxy thông
except Exception as e:
    print('Proxy DEAD:', e)
```

### 10. 9Router — reset priority bị demote về 9999
Khi accounts antigravity (trong 9Router) bị hạ priority xuống 9999 do 429:
```sql
UPDATE providerConnections
SET priority = json_extract(data, '$.priorityBase'), updatedAt = datetime('now')
WHERE provider = 'antigravity' AND priority = 9999;
```
Sau đó restart 9Router (kill node PID trên port 20128, khởi lại `server.js`).
