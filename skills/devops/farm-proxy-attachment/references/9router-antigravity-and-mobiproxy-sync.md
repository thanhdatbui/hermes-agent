# 9Router Antigravity & MobiProxy Dynamic Recovery (2026-08-20)

## 1. Triệu chứng sự cố
- Khi mạng Internet phía đầu cắm Box MobiProxy (`test.taadaa.click`) bị reset/mất điện:
  - DDNS `test.taadaa.click` mất kết nối hoặc chuyển sang IP WAN mới (ví dụ `27.69.64.218`).
  - 9Router báo lỗi hàng loạt trong **Providers > Antigravity**:
    - `failed: Proxy test timed out`
    - `[ProjectId] onboardUser failed after 5 attempts: onboardUser done but no project_id in response`
    - Toàn bộ Proxy Pools chuyển sang `testStatus = "error"`.

## 2. Quy trình kiểm tra & khôi phục tự động
1. **Kiểm tra liveness của Box:**
   - Query DNS `test.taadaa.click` -> kiểm tra IP WAN mới.
   - Quét port proxy `5101..5138` và web panel port 80.
2. **Kiểm tra định dạng Auth & Egress:**
   - Dàn port `5101..5138` tương ứng `mobi1..mobi38`.
   - Pass: `TaadaaMobi#2026!` (URL-encode `%23` và `%21`).
3. **Phục hồi 9Router DB (`%APPDATA%\9router\db\data.sqlite`):**
   ```python
   import sqlite3, json, os, datetime
   db_path = os.path.expandvars(r'%APPDATA%\9router\db\data.sqlite')
   conn = sqlite3.connect(db_path)
   cur = conn.cursor()
   now = datetime.datetime.now(datetime.timezone.utc).isoformat()
   
   # Reset proxyPools
   cur.execute('SELECT id, data FROM proxyPools WHERE data LIKE "%test.taadaa.click%"')
   for pid, d_str in cur.fetchall():
       d = json.loads(d_str)
       d['lastTestedAt'] = now
       d['lastError'] = None
       cur.execute('UPDATE proxyPools SET isActive = 1, testStatus = "active", data = ?, updatedAt = ? WHERE id = ?', (json.dumps(d), now, pid))
   
   # Clear lastError trên providerConnections (antigravity)
   cur.execute('SELECT id, data FROM providerConnections WHERE provider = "antigravity"')
   for cid, d_str in cur.fetchall():
       d = json.loads(d_str)
       d['testStatus'] = 'active'
       d['lastError'] = None
       d['errorCode'] = None
       cur.execute('UPDATE providerConnections SET data = ?, updatedAt = ? WHERE id = ?', (json.dumps(d), now, cid))
   
   conn.commit()
   conn.close()
   ```
