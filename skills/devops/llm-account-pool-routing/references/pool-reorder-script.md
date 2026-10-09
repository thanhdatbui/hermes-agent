# Pool Reorder Script — ag-gemini-pool-3

## Mục đích
Sắp xếp lại thứ tự acc trong combo `ag-gemini-pool-3` theo 4 nhóm ưu tiên,
đảm bảo acc Pro proxy live lên đầu để OmniRoute không bị cạn `maxGlobalAttempts`
trước khi chạm vào acc Starter 100% quota ở cuối.

## Thứ tự ưu tiên (sort key: `(group, -remaining_percentage)`)

| Group | Điều kiện | Mô tả |
|---|---|---|
| GRP0 | g1-pro-tier + proxy live + active | Pro lên đầu tuyệt đối |
| GRP1 | free-tier + proxy live + quota ≥ 10% | Starter quota cao |
| GRP2 | free-tier + proxy live + quota < 10% | Starter quota thấp |
| GRP3 | standard-tier + proxy live + active | 403 candidate, chờ fix ToS |
| GRP4 | proxy dead / inactive / expired | Đuôi pool |

Acc `DIRECT` (không có proxy assignment) = `proxy_live = True`.

## Script Python chuẩn

```python
import sqlite3, json, socket, urllib.request

def check_proxy(c, cid):
    c.execute('''
        SELECT pr.host, pr.port
        FROM proxy_assignments pa
        JOIN proxy_registry pr ON pr.id = pa.proxy_id
        WHERE pa.scope_id = ?
    ''', (cid,))
    pr = c.fetchone()
    if not pr or not pr[0]:
        return True  # DIRECT = live
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    res = s.connect_ex((pr[0], pr[1]))
    s.close()
    return (res == 0)

conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
c = conn.cursor()

# Backup trước
import urllib.request, json
req = urllib.request.urlopen('http://localhost:20129/api/combos')
backup = req.read()
with open(r'D:\Taadaa\AI-Tools\tools\omniroute\combos_backup.json', 'wb') as f:
    f.write(backup)

combos = json.loads(backup).get('combos', [])
target_combo = next(cb for cb in combos if cb['name'] == 'ag-gemini-pool-3')
models = target_combo['models']

scored = []
for m in models:
    cid = m.get('connectionId')
    c.execute('SELECT email, is_active, test_status, provider_specific_data FROM provider_connections WHERE id = ?', (cid,))
    row = c.fetchone()
    if not row:
        scored.append((9, 0, m))
        continue
    email, active, status, psd_str = row
    psd = json.loads(psd_str) if psd_str else {}
    tier = psd.get('tier')
    proxy_live = check_proxy(c, cid)

    c.execute('''
        SELECT remaining_percentage, is_exhausted
        FROM quota_snapshots
        WHERE connection_id = ? AND (window_key = 'gemini_weekly' OR window_key LIKE 'gemini-3.8%')
        ORDER BY created_at DESC LIMIT 1
    ''', (cid,))
    qs = c.fetchone()
    rem = qs[0] if qs else 0
    exh = qs[1] if qs else 1

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
print('Top 5 sau reorder:')
for i, (g, r, m) in enumerate(scored[:5]):
    cid = m.get('connectionId')
    c.execute('SELECT email, provider_specific_data FROM provider_connections WHERE id = ?', (cid,))
    row = c.fetchone()
    psd = json.loads(row[1]) if row and row[1] else {}
    print(f'  [{i+1}] GRP{g} | {row[0]} | {psd.get("tier")} | rem={-r:.1f}%')
```

## Lưu ý
- `socket.connect_ex` timeout 0.3s — dùng 0.5s nếu farm flappy
- Chạy lại sau mỗi lần reset quota tuần hoặc sau khi re-OAuth acc mới
- Sau khi reorder xong, commit backup `combos_backup.json` vào AI-Tools git
