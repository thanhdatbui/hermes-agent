# Codex OAuth Proxy Binding & Direct Egress Leak Prevention

## 1. Tử huyệt Direct Egress của Codex Provider trên OmniRoute
- Khi một connection Codex được tạo bằng OAuth hoặc Token Import (`POST /api/oauth/codex/import-token`), connection mang `proxy_enabled = 1`.
- Tuy nhiên, theo Resolution Chain (`src/lib/db/settings.ts`), nếu không có bản ghi trong bảng `proxy_assignments` (`scope = 'account'` hoặc `scope = 'provider', scope_id = 'codex'`), OmniRoute sẽ rơi về **Step 12: `{ proxy: null, level: "direct" }`**.
- Mọi request gửi tới ChatGPT backend qua provider `codex` lúc này sẽ đi thẳng bằng IP mạng nhà của máy chủ host, gây nguy cơ rate-limit IP, checkpoint, hoặc lộ địa chỉ mạng Farm.

## 2. Quy trình gán Proxy 1-1 tự động từ Profile GPM
Mỗi profile GPM chứa thông tin `raw_proxy` (vd `test.taadaa.click:5113:...`).
Sau khi import token vào OmniRoute nhận được `conn_id`, bắt buộc thực hiện gán proxy ngay:

```python
import re, requests

def bind_codex_proxy_from_gpm(conn_id: str, raw_proxy: str, omni_base: str = "http://127.0.0.1:20129"):
    if not conn_id or not raw_proxy:
        return
    m = re.search(r':(\d{4,5})', raw_proxy)
    if not m:
        return
    port = int(m.group(1))
    r_reg = requests.get(f"{omni_base}/api/settings/proxies", timeout=5).json()
    matched = [p for p in r_reg.get("items", []) if p.get("port") == port]
    if matched:
        proxy_id = matched[0]["id"]
        requests.put(f"{omni_base}/api/settings/proxies/assignments", json={
            "proxyId": proxy_id,
            "scope": "account",
            "scopeId": conn_id
        }, timeout=5)
        requests.put(f"{omni_base}/api/providers/{conn_id}", json={"proxyEnabled": True}, timeout=5)
```

## 3. Lệnh Verify O(1) kiểm tra trạng thái gán Proxy
```bash
node -e "
const Database = require('C:/Users/Kibe/OmniRoute/node_modules/better-sqlite3');
const os = require('os');
const path = require('path');
const db = new Database(path.join(os.homedir(), '.omniroute', 'storage.sqlite'));

const codexConns = db.prepare('SELECT id, name FROM provider_connections WHERE provider = \'codex\'').all();
for (const c of codexConns) {
  const a = db.prepare(\`
    SELECT pa.proxy_id, pr.name as proxy_name, pr.host, pr.port
    FROM proxy_assignments pa
    LEFT JOIN proxy_registry pr ON pa.proxy_id = pr.id
    WHERE pa.scope_id = ?
  \`).get(c.id);
  const status = a ? \`PORT \${a.port} @ \${a.host}\` : '❌ DIRECT EGRESS';
  console.log(\`\${a ? '✓' : '•'} \${c.name.padEnd(45)} -> \${status}\`);
}
"
```
