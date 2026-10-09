# Pool Reorder & Hermes Fallback Chain — Session Notes (2026-09-09)

## Root Cause: maxGlobalAttempts=30 Budget Exhaustion

`ag-gemini-pool-3` có 63 acc. `maxGlobalAttempts` mặc định của OmniRoute là **30** (từ `comboConfig.ts`).

Khi phần đầu pool có nhiều acc cạn quota (bị `quota_cutoff` skip — mỗi skip TỐN 1 attempt) cộng với vài acc lỗi 403/502, ngân sách 30 attempts cạn sạch trước khi OmniRoute lướt đến dàn Starter 100% quota ở đuôi. OmniRoute ném `503 Maximum combo retry limit reached` cho Hermes.

**Bẫy nested combo**: Tưởng `omni-worker` (Tier1→Tier2→Tier3) sẽ tự fallback Tier1→Tier2 (`ag-claude`). Nhưng khi `maxGlobalAttempts` cạn, OmniRoute ném 503 ra ngoài toàn bộ `omni-worker` — Tier2 không bao giờ được chạy. Nested combo fallback KHÔNG hoạt động khi attempts thủng.

## Giải Pháp: Hermes Gateway Fallback Chain

Thêm `ag-claude` vào `fallback_providers` Hermes ở **vị trí đầu tiên** trước `omni-free`:

```python
from hermes_cli.config import load_config, save_config
from hermes_cli.fallback_cmd import _write_chain
cfg = load_config()
chain = [
    {'model': 'ag-claude', 'provider': 'omni'},
    {'model': 'omni-free', 'provider': 'omni'},
    {'model': '9r-free', 'provider': 'custom:9router'}
]
_write_chain(cfg, chain)
save_config(cfg)
```

Verify: `hermes fallback list`

Đồng bộ template: `D:\Taadaa\AI-Tools\config\hermes\hermes_config_template.yaml`

## Thứ Tự Reorder ag-gemini-pool-3

4 nhóm ưu tiên (sort: group ASC, remaining_percentage DESC):

| Group | Điều kiện | Lý do |
|-------|-----------|-------|
| GRP0 | `g1-pro-tier` + proxy LIVE | Quota cao ~50x Starter, ưu tiên tuyệt đối |
| GRP1 | `free-tier` + proxy LIVE + quota >= 10% | Starter còn dồi dào |
| GRP2 | `free-tier` + proxy LIVE + quota < 10% | Starter gần cạn |
| GRP3 | `standard-tier` + proxy LIVE | 403 candidate, đang fix |
| GRP4 | proxy DEAD / inactive / expired | Vô dụng, xếp đuôi |

### Script Reorder (Python)

```python
import sqlite3, json, socket, urllib.request

def check_proxy(c, cid, timeout=0.3):
    """Returns (is_live, proxy_tuple). Direct egress (no row) = True."""
    c.execute('''
        SELECT pr.host, pr.port
        FROM proxy_assignments pa
        JOIN proxy_registry pr ON pr.id = pa.proxy_id
        WHERE pa.scope_id = ?
    ''', (cid,))
    pr = c.fetchone()
    if not pr or not pr[0]:
        return True, None
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    res = s.connect_ex((pr[0], pr[1]))
    s.close()
    return (res == 0), pr

def get_quota_rem(c, cid):
    c.execute('''
        SELECT remaining_percentage, is_exhausted
        FROM quota_snapshots
        WHERE connection_id = ? AND (window_key = 'gemini_weekly' OR window_key LIKE 'gemini-3.8%')
        ORDER BY created_at DESC LIMIT 1
    ''', (cid,))
    qs = c.fetchone()
    if not qs:
        return 0, 1
    return qs[0], qs[1]

conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
c = conn.cursor()

req = urllib.request.urlopen('http://localhost:20129/api/combos')
combos = json.loads(req.read().decode()).get('combos', [])
target_combo = next(cb for cb in combos if cb['name'] == 'ag-gemini-pool-3')
models = target_combo['models']

scored = []
for m in models:
    cid = m.get('connectionId')
    c.execute('SELECT email, is_active, test_status, provider_specific_data FROM provider_connections WHERE id = ?', (cid,))
    row = c.fetchone()
    if not row:
        scored.append((9, 0, m)); continue
    email, active, status, psd_str = row
    psd = json.loads(psd_str) if psd_str else {}
    tier = psd.get('tier')
    proxy_live, _ = check_proxy(c, cid, timeout=0.3)
    rem, exh = get_quota_rem(c, cid)

    if not active or status == 'expired':
        g = 4
    elif not proxy_live:
        g = 4
    elif tier == 'g1-pro-tier':
        g = 0
    elif tier == 'free-tier' and exh == 0 and rem >= 10:
        g = 1
    elif tier == 'free-tier':
        g = 2
    elif tier == 'standard-tier':
        g = 3
    else:
        g = 2

    scored.append((g, -rem, m))

scored.sort(key=lambda x: (x[0], x[1]))

reordered = []
for idx, (g, r, m) in enumerate(scored):
    item = dict(m)
    item['label'] = f'pool-{idx+1}'
    reordered.append(item)

payload = {
    'name': target_combo['name'],
    'description': target_combo.get('description', ''),
    'strategy': target_combo.get('strategy', 'priority'),
    'config': target_combo.get('config', {}),
    'models': reordered
}
update_req = urllib.request.Request(
    f'http://localhost:20129/api/combos/{target_combo["id"]}',
    headers={'Content-Type': 'application/json'},
    data=json.dumps(payload).encode(),
    method='PUT'
)
res = urllib.request.urlopen(update_req)
print('Update status:', res.status)
```

## Pitfalls

- **Proxy probe timeout**: Dùng `socket.settimeout(0.3)` minimum, `0.2s` báo DEAD nhầm khi proxy lag. Khi có nghi ngờ verify lại với `0.5s`.
- **DIRECT egress**: Acc không có `proxy_assignments` row → `proxy_live = True` mặc định (không có gì để test).
- **GPM fix standard-tier 403**: TUYỆT ĐỐI dùng đúng proxy đã gán trong OmniRoute (`proxy_assignments` → `proxy_registry` host:port:user:pass). KHÔNG tự chế proxy khác gắn vào GPM start. Sai proxy = IP khác = Google kích hoạt checkpoint bảo mật, hỏng token.
- **Backup trước khi PUT**: Luôn backup combo ra `D:\Taadaa\AI-Tools\tools\omniroute\combos_backup.json` trước khi reorder.

## Chẩn đoán quota exhaustion cutoff

Trong `combo.ts` line ~1303: OmniRoute gọi `resolveQuotaExhaustionCutoffForTarget()` — nếu snapshot ghi `is_exhausted=1` hoặc `remaining_percentage=0`, **target bị skip ngay (không dispatch)** nhưng **vẫn tốn 1 globalAttempt**. 63 acc × skip = 63 attempts cần thiết để lướt hết pool, nhưng default cap chỉ là 30.

## Trạng thái pool ag-gemini-pool-3 (2026-09-09)

- 63 accounts tổng
- 14 acc g1-pro-tier (11 proxy live, 3 proxy dead: `5111`/lelinh, `5103`/marcusephillips, `5117`/bobbyxruizz)
- ~17 acc Starter free-tier quota >= 70-100% với proxy live
- 10 acc standard-tier (6 proxy live cần fix ToS via GPM, 4 proxy dead)
- 4 acc expired/inactive
