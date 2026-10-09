# Audit & Reconcile: Antigravity Pro Plan Quota vs Combo Models (The 15 vs 16 Discrepancy)

## 1. Bản Chất Hiện Tượng Lệch Số Lượng (15 vs 16 Accounts)
- **Giao diện Provider Limits (`/api/usage/provider-limits`)**: Lọc theo gói bản quyền thật sự của Google được phản ánh trong cache (`plan: 'Pro'`, `tier: 'g1-pro-tier'`). Nếu tài khoản không có gói trả phí thật, Provider Limits sẽ không tính vào bộ lọc Pro.
- **Giao diện Combos (`ag-gemini-pool-3`)**: Danh sách tĩnh các model được gán vào combo qua mảng `models`. Nếu một agent trước đó gán nhầm một tài khoản Free (như `nguyenkhoi14031998`) vào combo Pro, danh sách này sẽ hiển thị thừa 1 account.
- **Hậu quả**:
  - Người dùng nhìn tab Provider Limits thấy **15 Pro**, nhưng nhìn tab Combos thấy **16 Models**.
  - Khi người dùng nâng cấp thêm 1 tài khoản mới thành Pro (`ninhvan04061999`):
    - Provider Limits tăng từ 15 lên **16**.
    - Combo Pro bị đội từ 16 lên **17**.

## 2. Quy Trình Rà Soát & Đối Soát O(1)
Khi phát hiện số lượng Pro giữa 2 nơi không khớp, chạy script kiểm tra chéo ngay:

```python
import urllib.request, json, sqlite3

# 1. Lấy danh sách Pro thật từ ProviderLimits API
req = urllib.request.urlopen("http://127.0.0.1:20129/api/usage/provider-limits")
caches = json.loads(req.read().decode()).get("caches", {})
pro_conn_ids = set()
for cid, c in caches.items():
    if "pro" in (c.get("plan") or "").lower():
        pro_conn_ids.add(cid)

# 2. Lấy danh sách model trong combo Pro
req = urllib.request.urlopen("http://127.0.0.1:20129/api/combos/22975610-b162-41b9-b6b3-30be076265bd")
combo = json.loads(req.read().decode())
combo_conn_ids = {m.get("connectionId") for m in combo.get("models", [])}

# 3. Tìm tài khoản bị gán nhầm (Free đội lốt Pro trong combo)
fake_pro_in_combo = combo_conn_ids - pro_conn_ids
if fake_pro_in_combo:
    conn = sqlite3.connect("C:/Users/Kibe/.omniroute/storage.sqlite")
    cur = conn.cursor()
    for cid in fake_pro_in_combo:
        cur.execute("SELECT email, json_extract(provider_specific_data, '$.tier') FROM provider_connections WHERE id = ?", (cid,))
        print("Tài khoản Free bị lẫn vào Pro combo:", cur.fetchall())
```

## 3. Quy Tắc Xử Lý Chuẩn Xác (Reconciliation)
1. **Loại bỏ tài khoản Free ra khỏi Combo Pro (`ag-gemini-pool-3`)**:
   - Lọc bỏ `connectionId` không có gói Pro thật ra khỏi mảng `models`.
   - Cập nhật lại description và gửi `PUT /api/combos/<pro_pool_id>`.
2. **Đưa tài khoản Free về đúng Combo Free (`ag-gemini-free-pool`)**:
   - Bổ sung `connectionId` vừa gỡ vào mảng `models` của `ag-gemini-free-pool` để không bỏ phí quota tài khoản.
   - Gửi `PUT /api/combos/<free_pool_id>`.
3. **Cập nhật Test Suite & Backup Snapshot**:
   - Chỉnh sửa assertion trong `tests/test_omniroute_combos.py` khớp chính xác số lượng Pro thật (16) và Free thật (88).
   - Dump cấu hình mới nhất ra `tools/omniroute/combos_backup.json`.
   - Reset circuit breaker/lockouts qua `POST /api/resilience/reset` để kích hoạt trạng thái mới ngay lập tức.
