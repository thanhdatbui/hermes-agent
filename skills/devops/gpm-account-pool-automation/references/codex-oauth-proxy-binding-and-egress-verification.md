# Codex OAuth Proxy Binding Invariant (OmniRoute :20129)

## 1. Tử huyệt rò rỉ IP nhà khi OAuth Codex vào OmniRoute
- **Hiện tượng:** Cờ `proxy_enabled = 1` trên bảng `provider_connections` của OmniRoute là cờ bật cho phép dùng proxy, **KHÔNG đồng nghĩa với việc kết nối đã có proxy**.
- **Cơ chế Resolution Chain (`src/lib/db/settings.ts`):**
  1. Kiểm tra `proxy_assignments` với `scope = 'account'` và `scope_id = connectionId`.
  2. Nếu không có `account` proxy $\rightarrow$ kiểm tra `provider` proxy pool (`scope = 'provider', scope_id = 'codex'`).
  3. Nếu không có `provider` proxy pool $\rightarrow$ kiểm tra global proxy.
  4. Nếu không có $\rightarrow$ **Fall-through về Step 12: `{ proxy: null, level: "direct" }` (Direct Egress đi thẳng IP mạng nhà)**.
- **Hậu quả:** Mọi request gọi model `gpt-5.5` / `codex` / `codex-terra` / `codex-luna` từ OmniRoute sẽ gửi trực tiếp từ IP máy chủ local, gây rủi ro nổ 403 / IP rate limit / lộ IP Farm.

---

## 2. Quy tắc bắt buộc khi sync Codex / ChatGPT-Web vào OmniRoute
Mọi script tạo hoặc cập nhật connection Codex / ChatGPT-Web (`POST /api/oauth/codex/import-token`, `POST /api/providers`) **BẮT BUỘC** phải có bước gán proxy 1-1 từ GPM `raw_proxy` ngay sau khi nhận `conn_id`:

```python
def bind_account_proxy_1to1(conn_id: str, raw_proxy: str, omni_base: str = "http://127.0.0.1:20129"):
    if not conn_id or not raw_proxy:
        return
    import re, requests
    m_port = re.search(r':(\d{4,5})', raw_proxy)
    if not m_port:
        return
    port = int(m_port.group(1))
    try:
        r_reg = requests.get(f"{omni_base}/api/settings/proxies", timeout=5).json()
        matched = [p for p in r_reg.get("items", []) if p.get("port") == port]
        if matched:
            proxy_id = matched[0]["id"]
            requests.put(f"{omni_base}/api/settings/proxies/assignments", json={
                "proxyId": proxy_id,
                "scope": "account",
                "scopeId": conn_id
            }, timeout=5)
            # Đảm bảo proxy_enabled bật
            requests.put(f"{omni_base}/api/providers/{conn_id}", json={"proxyEnabled": True}, timeout=5)
    except Exception as e:
        logger.warning(f"Lỗi bind proxy {port} cho connection {conn_id}: {e}")
```

---

## 3. Lệnh Verify O(1) trạng thái Proxy của Provider Codex trên SQLite
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
  const status = a ? \`PORT \${a.port} @ \${a.host}\` : '❌ NO PROXY (Direct Egress)';
  console.log(\`\${a ? '✓' : '✗'} \${c.name.padEnd(45)} -> \${status}\`);
}
"
```
