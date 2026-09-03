# MobiProxy Web Management, Authentication & Audit Troubleshooting

## 1. MobiProxy Architecture & Management Web UI
- **Host / URL:** `http://test.taadaa.click` (hoặc IP local `192.168.1.1` qua mạng LAN).
- **Default Dashboard:** `#dashboard`, `#proxies`, `#security`, `#network`.
- **API Token Header:** `Authorization: Bearer <mpx_token>` hoặc query `?token=<mpx_token>`.
- **Key API endpoints:**
  - `GET /proxy_getlist?token={token}`: Trả về danh sách proxy, IPv4/IPv6, status, uptime.
  - `GET /proxy_check?proxy=host:port&token={token}`: Kiểm tra trạng thái proxy (`proxy_ok` / `proxy_false`).
  - `GET /proxy_getip?proxy=host:port&token={token}`: Lấy IPv4 của proxy.
  - `GET /api.php?action=audit.list`: Lấy danh sách audit log, actor IP, thời gian, hành động đăng nhập/thay đổi proxy.
  - `POST /api.php?action=proxy.access_bulk` (CSRF protected): Cấu hình xác thực hàng loạt cho toàn bộ proxy.

---

## 2. Lỗi 407 Proxy Authentication Required & Chrome Không Vào Được Mạng

### Hiện Tượng
- Box MobiProxy báo trạng thái tất cả proxy đang Xanh (`Hoạt động`).
- Trên điện thoại: Chrome báo lỗi **"Không thể truy cập trang web này" / "Kết nối đã được đặt lại" (`ERR_CONNECTION_RESET`)**.
- Thử mở `http://api.ipify.org` từ Python/curl qua proxy cổng `5101` $\rightarrow$ Nhận mã lỗi **`HTTP Error 407: Proxy Authentication Required`**.

### Nguyên Nhân
- Sau khi reset box hoặc thay đổi cấu hình, MobiProxy kích hoạt chế độ xác thực `strong` (yêu cầu User/Password) hoặc đổi mật khẩu ngẫu nhiên.
- ViChanger trên Android đang giữ cấu hình cũ hoặc gửi định dạng user:pass không khớp $\rightarrow$ Proxy từ chối request $\rightarrow$ VpnService tunnel không chuyển tiếp được gói tin.

---

## 3. Quy Trình Cấu Hình Xác Thực An Toàn (Dedicated Bulk Password)

> **Cảnh báo bảo mật:** Tuyệt đối KHÔNG để proxy ở chế độ `none` (Không xác thực) lâu dài khi mở ra internet qua domain công khai, vì proxy rất dễ bị quét IP và sử dụng trái phép gây nghẽn băng thông.

### Bước 1: Áp dụng mật khẩu riêng biệt hàng loạt (`mode="strong"`)
Đăng nhập vào `http://test.taadaa.click` và gọi API `proxy.access_bulk`:
```python
import urllib.request, urllib.parse, http.cookiejar, re, json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. Login
res = opener.open('http://test.taadaa.click/login.php')
html_login = res.read().decode('utf-8')
csrf = re.search(r'name="_csrf"\s+value="([^"]+)"', html_login).group(1)

login_data = urllib.parse.urlencode({'_csrf': csrf, 'password': '<ADMIN_PASSWORD>'}).encode('utf-8')
opener.open(urllib.request.Request('http://test.taadaa.click/login.php', data=login_data))

# 2. Get CSRF from index.php
req2 = urllib.request.Request('http://test.taadaa.click/index.php')
html_index = opener.open(req2).read().decode('utf-8')
csrf_val = re.search(r'name="_csrf"\s+value="([^"]+)"', html_index).group(1)

# 3. Apply mode="strong" with dedicated password for all proxies
payload = {'mode': 'strong', 'password': '<NEW_DEDICATED_PASSWORD>', 'allowed_ips': ''}
api_req = urllib.request.Request(
    'http://test.taadaa.click/api.php?action=proxy.access_bulk',
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-CSRF-Token': csrf_val,
    }
)
res = opener.open(api_req)
```

### Bước 2: Chuẩn hóa Mapping Workbook sang `host:port:user:pass`
Khi proxy ở chế độ `strong`:
- Từng cổng được gán user mặc định dạng `mobi<idx>`:
  - Port `5101` $\rightarrow$ `mobi1`, `5102` $\rightarrow$ `mobi2`, ..., `5138` $\rightarrow$ `mobi32`.
- Cột proxy trong `PROXYgandienthoai.xlsx` cập nhật đầy đủ: `test.taadaa.click:5101:mobi1:<NEW_DEDICATED_PASSWORD>`.

### Bước 3: Reconnect Broadcast toàn bộ máy
Gửi lệnh ADB broadcast tới toàn bộ thiết bị đang online:
```python
# STOP_VPN -> START_VPN
subprocess.run(['adb', '-s', serial, 'shell', 'am', 'broadcast', '-a', 'vn.vichanger.app.STOP_VPN', '-n', 'vn.vichanger.app/.AdbCaller'])
subprocess.run(['adb', '-s', serial, 'shell', 'am', 'broadcast', '-a', 'vn.vichanger.app.START_VPN', '-n', 'vn.vichanger.app/.AdbCaller', '-e', 'proxy', proxy_str])
```

### Bước 4: Kiểm tra trực tiếp trên thiết bị
Mở Chrome tải `http://api.ipify.org` và chụp màn hình xác thực IP public riêng biệt hiển thị thành công.

---

## 4. Kiểm Tra Lịch Sử IP Truy Cập (Audit Logs & Intrusion Check)
Để rà soát xem có IP lạ nào đăng nhập hoặc điều khiển domain MobiProxy hay không:
```python
api_url = 'http://test.taadaa.click/api.php?action=audit.list'
req_api = urllib.request.Request(api_url, headers={'Accept': 'application/json'})
res_api = opener.open(req_api)
data = json.loads(res_api.read().decode('utf-8'))

for ev in data['data']['events']:
    print(f"Actor: {ev.get('actor')} | Action: {ev.get('action')} | Success: {ev.get('success')}")
```
- Nếu chỉ thấy actor chứa IP mạng nhà (ví dụ `admin:113.23.29.121`), hệ thống hoàn toàn an toàn và không bị truy cập lạ.
