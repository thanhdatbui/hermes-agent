# OmniRoute Proxy Egress & Fallback Mechanics

## 1. Ý nghĩa màn hình Proxy Logs (`/dashboard/logs/proxy`)
Màn hình **Proxy Logger** trên Dashboard OmniRoute (`http://<ip>:20129/dashboard/logs/proxy`, backend `/api/usage/proxy-logs`) dùng để giám sát và đối soát toàn bộ lưu lượng gửi ra ngoài (egress outbound traffic) từ OmniRoute tới các nhà cung cấp AI upstream (Google Antigravity, Anthropic Claude, OpenAI Codex...):
- **Status & Latency**: `success`, `timeout` (408/504), `error` kèm thời gian phản hồi (ms) qua proxy.
- **Proxy**: Host, Port, loại proxy (HTTP/SOCKS5), tên định danh (ví dụ `mirotik_10001`, `71`, `54`).
- **Level**: Cấp độ phân giải proxy:
  - `account`: Proxy gán riêng 1:1 cho connection/tài khoản.
  - `provider`: Proxy thuộc pool chung của provider (được chọn qua rotation hoặc fallback).
  - `apiKey`: Proxy gán theo API Key của client.
  - `global`: Proxy dùng chung toàn hệ thống.
  - `direct`: Không qua proxy, đi trực tiếp từ host IP.
- **Client IP vs Egress IP**:
  - `clientIp`: IP inbound của máy gọi request vào OmniRoute (`127.0.0.1` nếu local, `192.168.110.x` nếu từ máy farm).
  - `egressIp`: IP public outbound thực tế mà Google/OpenAI nhìn thấy (được probe ngầm qua `src/lib/proxyEgress.ts`), ví dụ dải Viettel `171.231.179.44`.
- **Lưu trữ**: Hybrid gồm in-memory ring buffer (`MAX_IN_MEMORY_ENTRIES = 200`) phục vụ live polling 3s trên dashboard, kết hợp ghi batch bất đồng bộ vào bảng `proxy_logs` trong SQLite.

---

## 2. Chuỗi phân giải Proxy (Resolution Chain) trong Codebase
Trong `src/lib/db/settings.ts` (hàm `resolveProxyForConnection(connectionId, apiKeyId, providerId)`):
1. **Global Toggle**: Kiểm tra `proxyEnabled` trong `key_value` table. Nếu tắt -> trả về `direct`.
2. **API Key Level**: Kiểm tra `perKeyProxyEnabled` và `apiKey.proxy_id`.
3. **Account Level (1:1)**:
   - Tra cứu `proxy_assignments` với `scope = 'account'` và `scope_id = connectionId`.
   - **Health Gate**: Gọi `isProxyReachable(proxyHealthUrl)`.
   - **Automatic Fallback Trigger**: Nếu proxy account không thể kết nối được (`isUnreachable == true`), OmniRoute KHÔNG để request chết hoặc rớt về direct IP, mà kích hoạt:
     ```typescript
     const providerFallback = await resolveProviderPoolFallbackProxy(connectionProvider, connectionId);
     if (providerFallback) {
       console.warn(`[ProxyFallback] Account proxy unreachable; using provider pool for ${connectionProvider}`);
       return providerFallback;
     }
     ```
4. **Provider Level (Pool)**:
   - Tra cứu `proxy_assignments` với `scope = 'provider'` và `scope_id = providerId`.
   - Xoay vòng theo chiến lược (`strategy`: `round-robin`, `sticky`, `random`, hoặc `latency`) trong bảng `proxy_scope_rotation`.
5. **Legacy Config & Global Fallback**: Đọc từ `key_value` namespace `proxyConfig` hoặc fallback auto-selection.

---

## 3. Hiện tượng dồn toàn bộ traffic về MikroTik Port `10001`
Khi dashboard log ghi nhận hàng loạt request của các account khác nhau đều xuất phát từ `mirotik1.taadaa.click:10001` với `Level: provider`:
1. **Dải Proxy 1:1 của Account bị chết**:
   - Bình thường các tài khoản Antigravity được gán proxy 1:1 trên dải mobile farm `test.taadaa.click:5101..5138`.
   - Khi dải port 51xx bị mất mạng, lỗi modem 4G, hoặc service proxy phía farm tắt, hàm `isProxyReachable()` đánh giá `false`.
2. **Thứ tự duyệt trong legacy `firstReachableProviderPoolProxy` (Thundering Herd Root Cause)**:
   - Hàm cũ duyệt tuần tự qua toàn bộ proxy của pool provider `antigravity` theo thứ tự:
     `ORDER BY a.position ASC, a.id ASC`
   - Các vị trí từ 0 đến 31 là các proxy `test.taadaa.click:5101..5138` (đều unreachable).
   - Vị trí sống đầu tiên trong bảng là **vị trí 32: `mirotik1.taadaa.click:10001` (proxy ID 71)**.
   - Do đó, OmniRoute tự động chuyển tiếp toàn bộ request của mọi tài khoản qua duy nhất port 10001 để cứu request — vi phạm nguyên tắc 1 tài khoản : 1 proxy.
   - **ĐÃ VÁ (2026-09-09)**: `firstReachableProviderPoolProxy` đã được thay bằng `resolveProviderPoolFallbackProxy(connectionProvider, connectionId)` — xem Mục 5 bên dưới. Nếu thấy lại hiện tượng `Level: provider` dồn 1 port → kiểm tra build đang chạy có phải production build mới nhất không (`git log --oneline -3`). Sau khi sửa, bắt buộc `npm run build && watchdog restart`.

---

## 4. Vị trí Database SQLite chuẩn xác của OmniRoute
- **Database chạy thật**: `C:\Users\Kibe\.omniroute\storage.sqlite` (`~/.omniroute/storage.sqlite`, dung lượng > 1 GB).
- **Thư mục phụ / Watchdog**: `C:\Users\Kibe\AppData\Roaming\omniroute\` chỉ chứa watchdog script và log, file `storage.sqlite` tại đây là file cũ/tách biệt.
- **Lệnh query kiểm tra nhanh bằng Python**:
  ```python
  import sqlite3
  conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
  cur = conn.cursor()
  cur.execute("SELECT a.position, p.name, p.host, p.port, p.status FROM proxy_assignments a JOIN proxy_registry p ON p.id = a.proxy_id WHERE a.scope = 'provider' ORDER BY a.position ASC LIMIT 10")
  for row in cur.fetchall():
      print(row)
  ```

---

## 5. Cơ chế Fallback Phân tán theo Tài khoản (Distributed Account-Aware Proxy Fallback)
Đã triển khai trong `src/lib/db/settings.ts` (commit 2026-09-09). Hàm `resolveProviderPoolFallbackProxy(provider, connectionId?)` thay thế hoàn toàn `firstReachableProviderPoolProxy`:

```typescript
function hashConnectionId(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export async function resolveProviderPoolFallbackProxy(
  provider: string | null,
  connectionId?: string
) {
  if (!provider) return null;
  const pool = await getAliveProxyPoolForScope("provider", provider);
  if (pool.length === 0) return null;

  const candidateChecks = await Promise.all(
    pool.map(async (candidate) => {
      const url = proxyHealthUrl(candidate.proxy);
      if (!url) return null;
      const alive = await isProxyReachable(url);
      return alive ? candidate : null;
    })
  );
  const reachable = candidateChecks.filter((c): c is NonNullable<typeof c> => c !== null);
  if (reachable.length === 0) return null;

  if (connectionId) {
    const index = hashConnectionId(connectionId) % reachable.length;
    return reachable[index];
  }
  return reachable[0];
}
```

**3 thuộc tính vận hành:**
1. **Concurrent Probe**: Quét song song toàn bộ `pool` thay vì tuần tự → không bị chặn lại ở proxy chết đầu đường.
2. **Reachable Filtering**: Chỉ những proxy thực sự kết nối được TCP mới vào tập phân bổ.
3. **Deterministic Connection Hashing**:
   - Hàm `hashConnectionId(connectionId) % reachable.length` → cùng một `connectionId` luôn map về cùng proxy (sticky), nhưng các `connectionId` khác nhau trải đều sang các proxy khác nhau.
   - Nếu không có `connectionId`, fallback về `reachable[0]` an toàn.

**Lợi ích vận hành:**
- **Account Isolation**: 48+ tài khoản cùng gặp proxy 1:1 chết KHÔNG còn dồn hết vào 1 port (10001). Thay vào đó trải đều trên toàn dải MikroTik 10001..10035 còn sống.
- **Connection Stickiness**: Bảo vệ trust score và nhất quán session OAuth của từng tài khoản.
- **Test coverage**: `tests/unit/proxy-fallback-distribution.test.ts` kiểm chứng 10 connection/acc đều phân tán sang ≥ 2 port khác nhau.

**Sau khi apply fix phải rebuild:**
```bash
cd C:/Users/Kibe/OmniRoute
npm run build   # ~5-6 phút
# Watchdog tự restart server sau khi build hoàn tất
```

---

## 6. Chẩn đoán nhanh khi thấy dồn cổng bất thường
```python
import sqlite3, socket

def tcp_probe(host, port, timeout=1.5):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close(); return True
    except: return False

conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
cur = conn.cursor()
cur.execute("""
SELECT a.position, p.name, p.host, p.port
FROM proxy_assignments a
JOIN proxy_registry p ON p.id = a.proxy_id
WHERE a.scope = 'provider' AND a.scope_id = 'antigravity'
ORDER BY a.position ASC
""")
for r in cur.fetchall():
    alive = tcp_probe(r[2], r[3])
    if alive:
        print(f"FIRST ALIVE: pos={r[0]} name={r[1]} {r[2]}:{r[3]}")
        break
    print(f"DEAD: pos={r[0]} {r[1]} {r[2]}:{r[3]}")
```
Nếu output cho thấy toàn bộ `test.taadaa.click:51xx` là DEAD → nguyên nhân rõ ràng là farm proxy tier bị outage, không phải lỗi OmniRoute. Khắc phục: phục hồi kết nối farm hoặc tạm thời đặt MikroTik lên đầu `position` trong pool.

---

## 7. Sự khác biệt cốt lõi: Account-level Fallback vs Provider-level Rotation Pool
Cần phân biệt rõ hai cơ chế kiểm tra proxy hoàn toàn khác nhau trong OmniRoute:

### A. Tầng Account (như Antigravity - Gemini / Claude):
- **Cơ chế**: Hàm `resolveProxyForConnection` (`settings.ts`) gọi `isProxyReachable(accountHealthUrl)` thực hiện kiểm tra TCP socket thực tế (timeout 2s, unhealthy cache 2s).
- **Khi Proxy gốc (MobiProxy) chết**: `isProxyReachable` trả về `false` → OmniRoute tự động kích hoạt `resolveProviderPoolFallbackProxy` để băm đều tài khoản sang các cổng MikroTik sống (`hashConnectionId(connectionId) % reachable.length`).
- **Khi Proxy gốc (MobiProxy) sống lại**: Lần gọi tiếp theo, `isProxyReachable` ping TCP socket thành công → **TỰ ĐỘNG QUAY VỀ DÙNG MOBIPROXY GỐC**, không còn fallback sang MikroTik và không cần bất kỳ thao tác cấu hình lại nào.

### B. Tầng Provider Rotation Pool (như OpenCode / `omni-free`):
- **Cơ chế**: Trong `src/lib/db/proxies/rotation.ts`, hàm `fetchAlivePoolRows` + `pickFromCandidates` chỉ truy vấn SQL:
  ```sql
  WHERE (p.status IS NULL OR LOWER(p.status) NOT IN ('inactive','error','disabled','dead','down'))
  ```
- **Hạn chế**: **HOÀN TOÀN KHÔNG KIỂM TRA TCP SOCKET RUNTIME**. Nó chỉ đọc trạng thái lưu trong bảng `proxy_registry`.
- **Hậu quả nếu gán proxy chết**: Nếu gán dải proxy đang chết (nhưng cờ `status` trong DB vẫn là `'active'`) vào pool của `opencode`, con trỏ Round-Robin sẽ bốc trúng cổng chết và ném cho HTTP client → **Request tèo ngay lập tức (HTTP 502 / Socket Hang Up / Timeout)** chứ KHÔNG tự động nhảy sang cổng sống tiếp theo trong cùng request.
- **Quy tắc an toàn**: **TUYỆT ĐỐI KHÔNG gán proxy đang chết vào provider-level pool của `opencode`**. Luôn đảm bảo toàn bộ proxy trong pool `opencode` đang mở socket và hoạt động tốt (ví dụ dải MikroTik 35 cổng FPT).

---

## 8. Ứng phó bão lỗi 403 Google Antigravity & Kỷ luật CẤM sửa code core
1. **Bản chất lỗi 403 Antigravity**: Thống kê `call_logs` chứng minh lỗi 403 trên dàn Google Antigravity diễn ra theo **SÓNG (waves)** chứ không phải tài khoản bị khóa vĩnh viễn (có khung giờ 100% 200 OK, có khung giờ dính sóng 403 rồi tự động phục hồi >70% OK).
2. **Cấu hình Cooldown tối ưu**:
   - Giữ nguyên `initial: 30000` (30 giây) với Exponential Backoff (`max: 1800000` - 30 phút).
   - KHÔNG tăng `initial` lên quá cao (như 5-10 phút) vì sẽ khóa oan tài khoản khi sóng 403 đã qua.
3. **Kỷ luật CẤM can thiệp code lõi OmniRoute (User Rule 2026-09-10)**:
   - CẤM sửa đổi mã nguồn engine của OmniRoute (`combo.ts`, `providerCooldownTracker.ts`...) để gượng ép logic cooldown hay fallback. OmniRoute là core proxy, chỉ dùng các tính năng có sẵn và cấu hình qua database/settings.
   - Khi Tier 1 (Antigravity) gặp bão lỗi 403 khiến việc duyệt 63 accounts bị chậm/timeout: **Người dùng / Agent chủ động swap thẳng sang model/combo `combo/omni-free`** (chạy trực tiếp qua pool 35 cổng MikroTik của OpenCode) để hoàn thành tác vụ ngay tức thì, không ngồi chờ combo tự fallback. Khi bão 403 qua thì swap lại `combo/omni-worker`.

