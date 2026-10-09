# GPM Profile ID Cloud-Sync Trap (2026-09-09)

## Vấn đề

GPM hoạt động theo mô hình **cloud-sync**: profile sống trên GPM cloud server, sync về máy.
Khi ai đó xóa profile trên GPM UI (hoặc từ máy khác qua cloud), profile biến mất khỏi
`/api/v3/profiles` dù:
- Folder vật lý vẫn còn: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\<path>\`
- Record local vẫn còn: `profile_data.db` table `Profiles`

## Bẫy cụ thể

| Nguồn | Trường | Vấn đề |
|---|---|---|
| `profile_data.db`.`Id` | UUID kiểu `d8b05afb-...` | Là LOCAL DB ID — KHÔNG khớp cloud ID |
| `/api/v3/profiles`[n].`id` | UUID | Là CLOUD ID — phải dùng cái này để start/stop |

Khi gọi `/api/v3/profiles/start` với UUID lấy từ SQLite → `PROFILE_NOT_FOUND`.

## Chuẩn xác định Profile ID

**LUÔN lấy `id` từ API `/api/v3/profiles`**, không từ SQLite:

```python
import urllib.request, json

req = urllib.request.urlopen('http://localhost:19995/api/v3/profiles', timeout=10)
profiles = json.loads(req.read().decode())
data = profiles if isinstance(profiles, list) else profiles.get('data', profiles.get('profiles', []))

# Map theo email trong tên profile
target_email = 'chungan2612199833@gmail.com'
email_user = target_email.split('@')[0][:20]
found = [p for p in data if email_user in str(p.get('name', ''))]
for p in found:
    print(f'id={p["id"]} | name={p["name"]} | path={p["profile_path"]} | proxy={p["raw_proxy"]}')
```

## Dấu hiệu profile đã bị xóa

- `email_user` không xuất hiện trong kết quả API list
- Nhưng folder `7_tspsb/` hoặc `3_s5w5k/` vẫn tồn tại trên đĩa
- `profile_data.db` vẫn có record với tên profile

## Xử lý khi profile bị xóa

Không thể tự động fix qua worker — cần Tad tạo lại profile GPM thủ công:
1. Mở GPM UI → New Profile
2. Đặt tên chuẩn: `M<máy> - <port> - <email>`
3. Gán đúng proxy 1:1 theo port farm (`test.taadaa.click:<port>` hoặc MikroTik)
4. Đăng nhập Google lại từ đầu trong profile mới
5. Sau khi có profile mới trên API → mới chạy fix ToS / OAuth

## Proxy đúng khi start GPM

Không tự chế proxy — lấy từ OmniRoute `proxy_assignments`:

```python
import sqlite3

db = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
c = db.cursor()
c.execute('''
    SELECT pr.host, pr.port, pr.username, pr.password
    FROM proxy_assignments pa
    JOIN proxy_registry pr ON pr.id = pa.proxy_id
    WHERE pa.scope_id = ?
''', (conn_id,))
row = c.fetchone()
if row:
    host, port, user, pwd = row
    proxy_str = f'http://{user}:{pwd}@{host}:{port}'
    # Truyền vào GPM start nếu cần override
    # additionalArguments = f'--proxy-server={proxy_str}'
```

Dùng proxy khác = IP khác = Google kích hoạt checkpoint → hỏng token, dính SMS checkpoint.
