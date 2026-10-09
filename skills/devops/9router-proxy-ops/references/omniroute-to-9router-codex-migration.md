# Di chuyển & Tái sử dụng Tài khoản Codex từ OmniRoute sang 9Router

## 1. Bối cảnh & Chỉ đạo Vận hành (User Directive)
Khi các tài khoản ChatGPT/Codex bị OpenAI quét hủy token hoặc bị khóa (`account_deactivated`), việc tạo mới hoặc OAuth lại tài khoản trắng thường gặp rào cản:
- Dính **Phone Verification Gate** (yêu cầu SMS OTP).
- Số dư dịch vụ thuê sim (5SIM) có thể bị cạn kiệt.

**Nguyên tắc vận hành tối thượng (User Directive)**:
> *"Mày nạp các profile đã oauth codex trên omni thôi chứ, nghĩa là đã từng ver số r. Con nào bị ban xoá đi chỉ giữ profile gpm có hotmail thôi"*

- **CẤM** tự ý chuyển hướng mục tiêu sang dùng pool web (`chatgpt-web` / `cgpt-web`) khi User yêu cầu nạp Codex.
- **Ưu tiên số 1**: Trích xuất kho tài khoản Codex đã từng ver số và lưu trong OmniRoute (`C:\Users\Kibe\.omniroute\storage.sqlite`), kiểm tra live qua proxy và nạp sang 9Router.
- **Bảo toàn Profile GPM**: Chỉ xóa record connection bị ban trong database của proxy (OmniRoute, 9Router). Tuyệt đối không xóa profile GPM vì profile chứa mailbox Hotmail gốc của farm.

---

## 2. Quy trình Trích xuất & Giải mã Token OmniRoute

### Bước 1: Lấy `STORAGE_ENCRYPTION_KEY` từ Tiến trình OmniRoute
OmniRoute lưu key mã hóa trong biến môi trường của tiến trình đang chạy (PID cổng 20129):
```python
import psutil

# Tìm process lắng nghe cổng 20129 hoặc process node run-next.mjs
for p in psutil.process_iter(['pid', 'name']):
    try:
        env = p.environ()
        if 'STORAGE_ENCRYPTION_KEY' in env:
            secret = env['STORAGE_ENCRYPTION_KEY'].encode('utf-8')
            break
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
```

### Bước 2: Dẫn xuất Khóa AES-256-GCM (Scrypt)
OmniRoute sử dụng chuẩn Scrypt với static salt:
```python
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

STATIC_SALT = b"omniroute-field-encryption-v1"
kdf = Scrypt(salt=STATIC_SALT, length=32, n=16384, r=8, p=1)
aes_key = kdf.derive(secret)

def decrypt_omni_field(enc_str: str) -> str:
    """Giải mã chuỗi dạng enc:v1:<iv_hex>:<ciphertext_hex>:<authTag_hex>"""
    if not enc_str or not enc_str.startswith("enc:v1:"):
        return enc_str
    parts = enc_str[7:].split(":")
    iv = bytes.fromhex(parts[0])
    ct = bytes.fromhex(parts[1])
    tag = bytes.fromhex(parts[2])
    aesgcm = AESGCM(aes_key)
    return aesgcm.decrypt(iv, ct + tag, None).decode("utf-8")
```

---

## 3. Kiểm tra Live Stream qua Egress Proxy Riêng

OpenAI Codex API yêu cầu:
1. Phải đi qua đúng proxy tương ứng của profile (ngăn chặn rò rỉ IP nhà làm revoke token).
2. **Bắt buộc `stream: True`**: Nếu gửi `stream: False`, OpenAI sẽ trả về `400 {"detail":"Stream must be set to true"}`.
3. **Phân loại lỗi HTTP**:
   - `200 OK` (có event `response.created`): Tài khoản LIVE và sẵn sàng nhận request.
   - `429 Too Many Requests` (`usage_limit_reached`): Token LIVE hợp lệ nhưng đang chạm hạn mức tạm thời. **VẪN NẠP VÀO 9ROUTER** vì khi chạy round-robin pool lớn, tài khoản sẽ tự phục hồi sau thời gian cooldown.
   - `401 Unauthorized` (`invalidated oauth token` / `token_revoked`): Token đã bị OpenAI hủy, bỏ qua không nạp.

```python
import urllib.request, json

def verify_codex_account(at: str, proxy_url: str):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
    )
    req = urllib.request.Request(
        'https://chatgpt.com/backend-api/codex/responses',
        data=json.dumps({
            'model': 'gpt-5.6-luna',
            'input': [{'role': 'user', 'content': [{'type': 'input_text', 'text': 'hi'}]}],
            'stream': True,
            'store': False
        }).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {at}',
            'Content-Type': 'application/json',
            'originator': 'codex_cli_rs',
            'User-Agent': 'codex_cli_rs/0.136.0'
        }
    )
    try:
        res = opener.open(req, timeout=8).read().decode('utf-8', errors='ignore')
        return ('LIVE', res) if 'response.created' in res else ('UNKNOWN', res)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return ('RATE_LIMITED_429', 'Valid session')
        return ('ERROR', f'HTTP {e.code}')
    except Exception as e:
        return ('ERROR', str(e))
```

---

## 4. Nạp vào 9Router & Gán `proxyPoolId` 1-1

Ghi trực tiếp vào database `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`:
```python
import sqlite3, json, uuid, datetime

db_path = r'C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Ánh xạ proxy port -> proxyPoolId
port_to_pool_id = {}
for pid, data_str in cur.execute('SELECT id, data FROM proxyPools').fetchall():
    for p in range(5101, 5139):
        if f':{p}' in data_str:
            port_to_pool_id[p] = pid
    if ':10001' in data_str:
        port_to_pool_id[10001] = pid

now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

for acc in verified_accounts:
    email = acc['email']
    name = acc['name']
    at = acc['accessToken']
    rt = acc['refreshToken']
    port = acc['proxy_port']
    pool_id = port_to_pool_id.get(port)
    
    existing = cur.execute(
        'SELECT id FROM providerConnections WHERE email = ? AND provider = ?', 
        (email, 'codex')
    ).fetchone()
    conn_id = existing[0] if existing else str(uuid.uuid4())
    
    data_payload = {
        'accessToken': at,
        'refreshToken': rt,
        'expiresAt': acc.get('expiresAt'),
        'testStatus': 'active',
        'expiresIn': 864000,
        'idToken': acc.get('idToken') or '',
        'lastRefreshAt': now_iso,
        'providerSpecificData': {
            'chatgptPlanType': 'free',
            'proxyPoolId': pool_id
        }
    }
    
    if existing:
        cur.execute('''
            UPDATE providerConnections 
            SET authType = 'oauth', name = ?, isActive = 1, priority = 1, data = ?, updatedAt = ?
            WHERE id = ?
        ''', (name, json.dumps(data_payload), now_iso, conn_id))
    else:
        cur.execute('''
            INSERT INTO providerConnections (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt)
            VALUES (?, 'codex', 'oauth', ?, ?, 1, 1, ?, ?, ?)
        ''', (conn_id, name, email, json.dumps(data_payload), now_iso, now_iso))

conn.commit()
conn.close()
```

---

## 5. Dọn dẹp Tài khoản Bị Ban (Deactivated Cleanup)

Khi phát hiện tài khoản bị lỗi `account_deactivated`:
1. Xóa khỏi `provider_connections` và `proxy_assignments` trong OmniRoute SQLite (`C:\Users\Kibe\.omniroute\storage.sqlite`).
2. Xóa khỏi `providerConnections` trong 9Router SQLite (`C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`).
3. **CẤM xóa thư mục/profile GPMLogin** tương ứng. Profile GPM chứa email Hotmail/Outlook gốc để phục vụ các dịch vụ khác của farm.

---

## 6. Chiến Lược Xoay Tải Phù Hợp trong 9Router (`round-robin` vs `fill-first`)

Trong mã nguồn điều phối `2283.js` của 9Router:
- **`fill-first` (Mặc định)**: Dồn toàn bộ request vào connection đầu tiên cho đến khi cạn quota hoặc bị 429 mới nhảy sang connection tiếp theo.
  - *Nhược điểm*: Khiến 1 account và 1 proxy IP bị bắn liên tục, dễ bị OpenAI gắn cờ spam và nghẽn luồng.
- **`round-robin` (Chiến lược khuyến nghị cho pool Codex)**: Xoay vòng tài khoản theo thứ tự thời gian gọi gần nhất (`lastUsedAt`).
  - Đi kèm tham số `stickyRoundRobinLimit`: Số request liên tiếp trên 1 connection trước khi đổi sang connection khác. Đặt `stickyRoundRobinLimit: 1` để san phẳng tải tuyệt đối qua 38 port proxy 4G Mobi.

### Cấu hình `round-robin` trong 9Router Database
Ghi cấu hình vào bảng `settings` trong `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`:
```python
import sqlite3, json

conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite')
cur = conn.cursor()

# Đọc settings hiện tại
row = cur.execute('SELECT data FROM settings WHERE id = 1').fetchone()
data = json.loads(row[0]) if row else {}

# Thiết lập round-robin cho provider codex hoặc toàn cục
data['fallbackStrategy'] = 'round-robin'
data['stickyRoundRobinLimit'] = 1
data.setdefault('providerStrategies', {})
data['providerStrategies']['codex'] = {
    'rotateStrategy': 'round-robin',
    'fallbackStrategy': 'round-robin',
    'stickyRoundRobinLimit': 1
}

cur.execute('UPDATE settings SET data = ? WHERE id = 1', (json.dumps(data),))
conn.commit()
conn.close()
```
Sau khi cập nhật, 9Router sẽ tự động chia đều tải cho toàn bộ pool 80+ acc Codex, mỗi request ra một egress IP 4G Mobi khác nhau.
