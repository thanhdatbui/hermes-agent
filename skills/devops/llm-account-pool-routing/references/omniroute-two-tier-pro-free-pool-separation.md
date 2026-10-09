# OmniRoute Two-Tier Pro/Free Pool Separation & Test Suite Invariants

## 1. Bối cảnh & Mục tiêu
Khi vận hành số lượng lớn tài khoản Antigravity (100+ accounts), việc gộp chung cả tài khoản Pro (`g1-pro-tier`) và tài khoản Free (`standard-tier`) vào một combo Round-Robin duy nhất (`ag-gemini-pool-3`) gây ra:
- **Bẫy pha loãng chất lượng / quota:** Request bị chia đều ngẫu nhiên vào các tài khoản Free có quota rất thấp (50-60 requests/ngày), dẫn đến rate-limit 429 sớm và làm chậm quá trình xử lý.
- **Giải pháp 2 tầng sạch:**
  1. Combo Primary: `ag-gemini-pool-3` chỉ chứa các tài khoản Pro (15 accounts).
  2. Combo Fallback: `ag-gemini-free-pool` chứa toàn bộ tài khoản Free/Standard active (87-89 accounts).
  3. Combo Điều phối `omni-worker` (Priority):
     - Tier 1: `ag-gemini-pool-3` (Pro)
     - Tier 2: `ag-gemini-free-pool` (Free Fallback)
     - Tier 3: `chatgpt-web-pool`
     - Tier 4: `omni-free`
     - Tier 5: `ag-claude`

---

## 2. Xác định tài khoản từ SQLite DB (`~/.omniroute/storage.sqlite`)

### Query lọc tài khoản Pro:
```sql
SELECT id, email 
FROM provider_connections 
WHERE provider = 'antigravity' 
  AND is_active = 1 
  AND (
    json_extract(provider_specific_data, '$.tier') = 'g1-pro-tier' 
    OR json_extract(provider_specific_data, '$.plan') = 'Pro'
  );
```

### Query lọc tài khoản Free/Standard:
```sql
SELECT id, email 
FROM provider_connections 
WHERE provider = 'antigravity' 
  AND is_active = 1 
  AND NOT (
    json_extract(provider_specific_data, '$.tier') = 'g1-pro-tier' 
    OR json_extract(provider_specific_data, '$.plan') = 'Pro'
  );
```

### Pitfall kiểm tra số lượng tài khoản (Account Drift / Discrepancy):
1. **Trạng thái `is_active`:** Luôn kiểm tra `is_active = 1`. Một số tài khoản có thể bị OmniRoute vô hiệu hóa (`is_active = 0`) do lỗi OAuth hoặc quá trình rà soát token. Không add các tài khoản inactive vào pool.
2. **Đối chiếu Whitelist vs Query:** Nếu user chỉ định danh sách 15 tài khoản cụ thể, cần so sánh danh sách đó với kết quả query. Một số tài khoản mới nâng cấp gói (hoặc background sync cập nhật `plan = Pro`) có thể làm số lượng trả về lệch (ví dụ 16 thay vì 15). Cần ưu tiên giữ đúng danh sách chỉ định và xếp các tài khoản còn lại vào đúng nhóm.

---

## 3. Cấu hình Model Item & Invariants của Test Suite

### Cấu hình Combo Primary (`ag-gemini-pool-3`):
- `id`: `22975610-b162-41b9-b6b3-30be076265bd`
- `strategy`: `round-robin`
- `config`:
  ```json
  {
    "maxRetries": 3,
    "retryDelayMs": 500,
    "targetTimeoutMs": 120000,
    "stickyRoundRobinLimit": 1,
    "disableSessionStickiness": false,
    "disablePromptCacheAffinity": false,
    "failoverBeforeRetry": false,
    "maxSetRetries": 3
  }
  ```
- Mỗi entry trong `models`:
  ```json
  {
    "id": "ag-gemini-pro-{idx}",
    "kind": "model",
    "model": "antigravity/gemini-3.8-flash-tiered",
    "providerId": "antigravity",
    "connectionId": "<cid>",
    "weight": 0,
    "label": "pro-{email}"
  }
  ```

### Cấu hình Combo Fallback (`ag-gemini-free-pool`):
- `name`: `ag-gemini-free-pool`
- `strategy`: `round-robin`
- `config`: Tương tự như `ag-gemini-pool-3` (bắt buộc `stickyRoundRobinLimit: 1`, `disableSessionStickiness: false`).
- Mỗi entry trong `models`:
  ```json
  {
    "id": "ag-gemini-free-{idx}",
    "kind": "model",
    "model": "antigravity/gemini-3.8-flash-tiered",
    "providerId": "antigravity",
    "connectionId": "<cid>",
    "weight": 0,
    "label": "free-{email}"
  }
  ```

### Test Suite Invariants (`test_omniroute_combos.py`):
Khi cập nhật combos qua API hoặc cập nhật file `combos_backup.json`, phải bảo đảm:
1. **Stickiness Guard:** Mọi active combo đều PHẢI có:
   - `stickyRoundRobinLimit == 1`
   - `disableSessionStickiness == False`
2. **Chatgpt Description Guard:** Mô tả của combo `chatgpt-web-pool` phải chứa chuỗi `"16 live accounts"`. Không được vô tình ghi đè hoặc làm mất description này khi serialize JSON.
3. **Backup File Structure:** File `combos_backup.json` phải ở định dạng `{"combos": [...], "total": N}` và đồng bộ khớp với endpoint `GET /api/combos`.
