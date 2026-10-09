# OmniRoute Combo Membership Sync & Provider Quota Discrepancy Runbook

## Root Cause & Symptom
**Symptom:** Quota page shows multiple Pro accounts with 100% quota active/alive, but all traffic / requests pile into a single account (or pool runs out of quota unexpectedly).

**Underlying Causes:**
1. **Unsynced Combo Membership (Most Common):** Upgrading or importing accounts to `g1-pro-tier` in `/api/providers` does **NOT** automatically add them to existing combos (`/api/combos`). Combos maintain an explicit array of `models` with pinned `connectionId`s.
2. **Expired / Stale Auth Token:** Account shows 100% quota in UI but has `testStatus: "unavailable"` or `Token expired`, causing OmniRoute scheduler to silently skip it.
3. **Sticky Session / Cache Affinity:** Combos with `disableSessionStickiness: false` or `disablePromptCacheAffinity: false` keep routing consecutive turns of a conversation (`conv_...`) to the same account for prompt cache hits.

---

## Diagnostic & Audit Steps (O(1) API)

### 1. Audit Pro Connections vs Combo Members
Run a fast probe against OmniRoute (`http://192.168.110.123:20129`):

```python
import urllib.request, json

base_url = 'http://192.168.110.123:20129'

# Get all pro connections
conns = json.loads(urllib.request.urlopen(f'{base_url}/api/providers').read().decode())['connections']
pro_conns = [c for c in conns if c.get('provider') == 'antigravity' and c.get('providerSpecificData', {}).get('tier') == 'g1-pro-tier' and c.get('isActive')]

# Get combo models
combos = json.loads(urllib.request.urlopen(f'{base_url}/api/combos').read().decode())['combos']
pool = next(c for c in combos if c.get('name') == 'ag-gemini-pool-3')
pool_conn_ids = set(m.get('connectionId') for m in pool.get('models', []))

missing = [c for c in pro_conns if c.get('id') not in pool_conn_ids]
print(f"Total Active Pro: {len(pro_conns)} | In Combo: {len(pool_conn_ids)} | Missing: {len(missing)}")
for m in missing:
    print(f"  Missing: {m.get('name')} ({m.get('id')})")
```

---

## Remediation / Sync via API

### 2. Add Missing Connections into Primary & Fallback Combos

```python
import urllib.request, json

base_url = 'http://192.168.110.123:20129'
target_combos = ['ag-gemini-pool-3', 'ag-gemini-pool-3-37']
target_models = {
    'ag-gemini-pool-3': 'antigravity/gemini-3.8-flash-tiered',
    'ag-gemini-pool-3-37': 'antigravity/gemini-3.7-flash-tiered'
}

combos_data = json.loads(urllib.request.urlopen(f'{base_url}/api/combos').read().decode())['combos']

for cname in target_combos:
    combo = next((c for c in combos_data if c.get('name') == cname), None)
    if not combo:
        continue
    
    existing_cids = set(m.get('connectionId') for m in combo.get('models', []))
    models = list(combo.get('models', []))
    changed = False

    for conn in pro_conns:
        cid = conn.get('id')
        if cid not in existing_cids:
            models.append({
                'id': f"{cname}-{conn.get('name').split('@')[0]}-{cid[:8]}",
                'kind': 'model',
                'model': target_models[cname],
                'providerId': 'antigravity',
                'connectionId': cid,
                'weight': 0,
                'label': f"pro-{conn.get('name').split('@')[0]}"
            })
            changed = True

    if changed:
        combo['models'] = models
        req = urllib.request.Request(
            f"{base_url}/api/combos/{combo['id']}",
            data=json.dumps(combo).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='PUT'
        )
        res = urllib.request.urlopen(req)
        print(f"Updated combo {cname}: Status {res.status}")
```

### 3. Refresh Stale / Expired Tokens
For accounts showing expired tokens or inconclusive health status:
```bash
curl -X POST http://192.168.110.123:20129/api/providers/<CONNECTION_ID>/test
```

---

## 4. Ghost Stub Trap on Provider Deletion (`connectionId: null`)
- **Cơ chế:** Khi gọi `DELETE /api/providers/<id>` trên OmniRoute, tầng lưu trữ tự động unlink kết nối khỏi các combo đang dùng nó. Tuy nhiên, thay vì xóa bỏ hoàn toàn model entry khỏi mảng `models`, backend có thể giữ lại một model stub với `connectionId: null` hoặc không có `connectionId`.
- **Hậu quả:** 
  - Số lượng model hiển thị trong combo bị đội lên (ví dụ thực tế: có 22 tài khoản Pro thực sự hoạt động nhưng combo báo 23 models).
  - Khi một tài khoản bị xóa nhầm rồi được nạp/thêm lại vào combo, nếu không dọn stub cũ thì combo sẽ chứa 1 entry rác (`connectionId: null`) + 1 entry mới, gây lệch số liệu kiểm toán.
- **Quy tắc dọn dẹp O(1):**
  Trước và sau khi cập nhật combo models, **BẮT BUỘC** lọc bỏ toàn bộ entry không có `connectionId` hoặc có `connectionId` không còn tồn tại trong `provider_connections`:
  ```python
  cleaned_models = [m for m in combo.get('models', []) if m.get('connectionId') and m.get('connectionId') in live_provider_ids]
  ```

---

## 5. Emergency Account Restoration từ SQLite Backup & Cạm bẫy Từ khóa `"group"`
- **Vị trí backup tự động:** OmniRoute lưu các snapshot DB hoàn chỉnh (bao gồm cả encrypted access/refresh token và metadata) tại `C:\Users\Kibe\.omniroute\db_backups\db_*.sqlite`.
- **Phục hồi tài khoản bị xóa nhầm:**
  1. Đọc dòng tài khoản tương ứng từ file backup gần nhất:
     ```python
     row = cur_bak.execute("SELECT * FROM provider_connections WHERE email=?", (email,)).fetchone()
     ```
  2. **CẠM BẪY SQLITE CRITICAL:** Bảng `provider_connections` chứa cột tên là `group`. Trong SQLite, `group` là từ khóa cú pháp dành riêng (`GROUP BY`). Nếu viết `INSERT INTO provider_connections (id, ..., group, ...)`, SQLite sẽ văng lỗi `sqlite3.OperationalError: near "group": syntax error`.
  3. **Khắc phục:** Bắt buộc bọc kép (quote) tên toàn bộ các cột:
     ```python
     cols = [r[1] for r in cur_live.execute("PRAGMA table_info(provider_connections)").fetchall()]
     quoted_cols = ','.join([f'"{c}"' for c in cols])
     placeholders = ','.join(['?'] * len(cols))
     cur_live.execute(f'INSERT OR REPLACE INTO provider_connections ({quoted_cols}) VALUES ({placeholders})', row)
     ```
  4. Đồng thời phục hồi bản ghi trong bảng `proxy_assignments` (`scope_id = <conn_id>`) để đảm bảo tài khoản giữ đúng IP/cổng proxy MikroTik chỉ định.

---

## 6. Kỷ luật Bắt Ngữ cảnh & Trích dẫn (Anti-Misattribution Invariant)
- **Tuyệt đối không xóa nhầm theo đại từ mơ hồ:** Khi người dùng phản hồi với đại từ chỉ định ("acc này", "xóa acc này") trong ngữ cảnh đang thảo luận đối chiếu giữa nhiều tài khoản (như Pro vs Free), **BẮT BUỘC** đối soát chính xác email và tin nhắn gốc được quote trước khi thực thi lệnh hủy diệt (`DELETE`).
- **Nghiêm cấm tự ý đổi hướng nhiệm vụ:** Khi người dùng chỉ đạo "acc A và acc B tao up lên pro rồi đưa vào pool pro cho tao", phải tập trung xử lý dứt điểm yêu cầu đó ngay lập tức (loại khỏi Free pool, nạp vào Pro pool). Tuyệt đối không được bỏ qua chỉ thị mà tự ý đi làm việc khác.
