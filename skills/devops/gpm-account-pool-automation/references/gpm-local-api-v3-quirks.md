# GPM Local API v3 Quirks & Known Blockers

## `/start` — PROFILE_NOT_FOUND fix: dùng `skip_proxy_check=true`

**Root cause**: GPM tiến hành pre-flight test kết nối proxy trước khi mở browser. Khi proxy dạng `mirotik1.taadaa.click:100xx` bị Hairpin NAT router chặn (máy host trong cùng mạng LAN), pre-flight fail → `PROFILE_NOT_FOUND`.

**Fix chuẩn**: Thêm query param `skip_proxy_check=true` vào GET request:

```python
# ĐÚNG — dùng GET + skip_proxy_check=true
import requests
res = requests.get(
    f'http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}',
    params={'skip_proxy_check': 'true'},
    timeout=30
)
data = res.json()
# {'success': True, 'data': {'remote_debugging_address': '127.0.0.1:60737', ...}}
```

Đã verify thực tế: **tất cả 50 profile trong GPM list đều start được ngay khi có `skip_proxy_check=true`**.

### Cách dùng với GPMClient (src/gpm_client.py):
```python
from src.gpm_client import GPMClient
gpm = GPMClient()
start_data = gpm.start_profile(profile_id, skip_proxy_check=True)
cdp_addr = start_data['data']['remote_debugging_address']
# Ví dụ: '127.0.0.1:60737'
```

### Stop profile (GET, không phải POST):
```
GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}
```

---

## Proxy Hairpin NAT loopback — Singbox vs MikroTik

**Bối cảnh**: Máy Kibe PC nằm trong mạng nội bộ `192.168.110.x`.

| Proxy type | Format | Kết quả trên LAN |
|---|---|---|
| Singbox (port 20001..20080) | `http://192.168.110.2:200xx` | **DEAD** — 502/Reset khi truy cập HTTPS |
| MikroTik port forward | `http://192.168.110.2:100xx:admin@1:admin@1` | **LIVE** — thông mạng ổn định |
| Domain ngoài | `mirotik1.taadaa.click:100xx` | Hairpin NAT chặn từ trong LAN |

**Kết luận**: Khi launch browser từ máy host:
- **Dùng**: `http://192.168.110.2:10007:admin@1:admin@1` (MikroTik LAN IP trực tiếp)
- **KHÔNG dùng**: `mirotik1.taadaa.click:10007` (Hairpin NAT fail), `192.168.110.2:20007` (Singbox bị 502)
- Singbox `200xx` chỉ dùng từ các máy ngoài phòng (non-Kibe host), hoặc từ thiết bị S7

**Test nhanh proxy có thông HTTPS không**:
```python
import urllib.request
proxy_url = 'http://admin@1:admin@1@192.168.110.2:10007'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'https': proxy_url}))
res = opener.open('https://api.ipify.org?format=json', timeout=5)
print(res.read().decode())  # {"ip": "116.110.158.143"} nếu thông
```

---

## Playwright qua CDP với proxy có basic auth → ERR_TOO_MANY_RETRIES

Khi dùng `launch_persistent_context(proxy={'server': '...', 'username': '...', 'password': '...'})`, Chromium bị loop authentication challenge trên mỗi 302-redirect của Google (codeassist.google.com → codeassist.google → ...) dẫn đến `net::ERR_TOO_MANY_RETRIES`.

**Giải pháp 1 (KHUYẾN NGHỊ)**: Dùng GPM API + CDP connect — GPM start profile với proxy đã gán sẵn trong profile, Playwright chỉ `connect_over_cdp` không cần truyền proxy:
```python
# Start qua GPM API → nhận CDP address
start_data = gpm.start_profile(pid, skip_proxy_check=True)
cdp_addr = start_data['data']['remote_debugging_address']
browser = playwright.chromium.connect_over_cdp(f'http://{cdp_addr}')
# Không cần truyền proxy — GPM đã inject sẵn
```

**Giải pháp 2**: Dùng local tunnel forwarder (strip basic auth, thêm vào header thay vì pass qua Playwright):
```python
import socket, threading, base64, select

class LocalProxyTunnel:
    def __init__(self, local_port, upstream_host, upstream_port, user, pwd):
        self.auth_header = b'Proxy-Authorization: Basic ' + base64.b64encode(f'{user}:{pwd}'.encode()) + b'\r\n'
        # ... (inject header vào từng CONNECT request)
    # Chromium trỏ vào 127.0.0.1:<local_port> không cần auth
```

---

## Field tạo profile: `profile_name` (không phải `name` hay `Name`)

- `POST /api/v3/profiles` KHÔNG tạo profile — nó trả list hiện tại.
- `POST /api/v3/profiles/create` là endpoint đúng.

| API Create Field | Ghi chú |
|---|---|
| `profile_name` ✅ | Required — SQLite column là `Name` nhưng API field là `profile_name` |
| `name`, `Name`, `ProfileName` | ❌ NOT NULL constraint fail |
| `raw_proxy` | Optional, format: `host:port:user:pass` |
| `profile_path` | Optional — nếu đặt, API **TẠO FOLDER MỚI** tại tên ngẫu nhiên (`Zytr3EkLsk-09092026`) chứ KHÔNG dùng folder bạn đặt |

**BẪY `profile_path`**: Dù truyền `profile_path: '7_tspsb'`, GPM tạo folder mới `Zytr3EkLsk-09092026` trống. Cookies cũ không migrate tự động.

### Cookie migration khi tạo profile mới từ folder cũ:
```python
import shutil, os

# Kill tất cả Chrome processes trước
# Sau đó copy data từ folder cũ sang folder MỚI trả về từ API
OLD = r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\7_tspsb\Default'
NEW = r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\Zytr3EkLsk-09092026\Default'

os.makedirs(NEW, exist_ok=True)
for item in ['Network', 'Login Data', 'Preferences', 'Web Data', 'Local Storage', 'IndexedDB']:
    s = os.path.join(OLD, item)
    d = os.path.join(NEW, item)
    if os.path.exists(s):
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
```

---

## SQLite DB vs Cloud API drift & Bẫy Multi-Account Profile Sharing

- `profile_data.db` chứa 341+ record local; API chỉ trả 50 profile sync cloud.
- Profile SQLite record ID ≠ API ID — **KHÔNG dùng SQLite ID để start**.
- Folder vật lý + Cookies cũ còn sống dù bị xóa khỏi cloud → Chrome launch vẫn OK.
- **BẪY PROFILE NAMING VÀ DÙNG CHUNG PROFILE (MULTI-ACCOUNT REUSE)**:
  - Tất cả tài khoản đã OAuth vào OmniRoute 100% đều đã từng login qua GPM.
  - CẤM TUYỆT ĐỐI vội vã kết luận "thiếu profile" hay "profile bị xóa" chỉ vì grep email không thấy trong cột `Name` của SQLite `Profiles`.
  - Trên thực tế: 1 máy S7 và 1 cổng proxy (ví dụ Máy 61 / Port 5127) thường chỉ có 1 profile GPM đại diện (tên mang email acc đầu tiên reg trên máy, ví dụ `M61 - 5127 - khahoan...`), nhưng folder `ProfilePath` đó (ví dụ `SUNVqFew4a-05092026`) được dùng chung cho các tài khoản tiếp theo (`vukhoa04122002`).
  - Khi re-auth, bắt buộc tra số máy (`mid`) và `port` trong Master Excel + log cũ (`run_batch_*.log`) để bốc đúng folder `ProfilePath`.
- Cách khai thác: tạo profile mới trên API + copy cookie từ folder cũ sang folder mới.

### Kiểm tra session Google còn sống trong folder cũ:
```python
import sqlite3, os
base = r'C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile'
for profile_path in ['7_tspsb', '3_s5w5k']:
    cookie_db = os.path.join(base, profile_path, 'Default', 'Network', 'Cookies')
    db = sqlite3.connect(cookie_db)
    c = db.cursor()
    c.execute("SELECT name, host_key FROM cookies WHERE host_key LIKE '%accounts.google%' AND name IN ('SID','LSID','HSID') LIMIT 3")
    print(profile_path, ':', c.fetchall())
    db.close()
```

---

## OmniRoute: endpoints refresh token và sync models (KHÔNG dùng /test)

```
POST /api/providers/{conn_id}/test     → probe-only, KHÔNG update tier, thường trả 400 inconclusive
POST /api/providers/{conn_id}/refresh  → real refresh_token, cập nhật expiresAt
POST /api/providers/{conn_id}/sync-models → full tier discovery, cập nhật provider_specific_data.tier
```

Để fix standard-tier → free-tier:
1. Mở browser trong đúng profile (với đúng Google account đã accept ToS)
2. Navigate đến `https://codeassist.google.com/?authuser=0`
3. Accept Personal ToS nếu có
4. Gọi `/refresh` → `/sync-models` → verify `tier` trong SQLite OmniRoute

---

## Combo reorder ag-gemini-pool-3

Dùng GRP-sort theo 5 tier:
- GRP0: g1-pro-tier, proxy live
- GRP1: free-tier, proxy live, quota ≥10%
- GRP2: free-tier, proxy live, quota <10%
- GRP3: standard-tier (cần fix ToS)
- GRP4: proxy dead hoặc account expired/inactive

**Update via** `PUT http://localhost:20129/api/combos/{combo_id}` với payload `{..., 'models': reordered_list}`.
`maxGlobalAttempts` mặc định 30 — nếu pool có >30 acc chết/hết quota ở đầu, request không bao giờ reach acc tốt.
