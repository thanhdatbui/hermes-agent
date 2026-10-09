# MobiProxy Web Management, Authentication & Audit Troubleshooting

## 1. MobiProxy Architecture & Management Web UI
- **Bản chất thiết bị:** Router OpenWrt MT7621 (đặt tại Thái Bình) quay số đa phiên PPPoE (`pppoe-proxy01`..`pppoe-proxy38`) trực tiếp trên đường cáp quang Viettel, lấy các dải IP dân cư động Viettel (`117.1.x.x`, `116.107.x.x`, `171.224.x.x`...), **KHÔNG PHẢI SIM/Dcom 4G**.
- **Host / URL:** `http://test.taadaa.click` (hoặc IP local `192.168.1.1` qua mạng LAN).
- **Default Dashboard:** `#dashboard`, `#proxies`, `#security`, `#network`.
- **API Token Header:** `Authorization: Bearer <mpx_token>` hoặc query `?token=<mpx_token>`.
- **Key API endpoints:**
  - `GET /proxy_getlist?token={token}`: Trả về danh sách proxy, IPv4/IPv6, status, uptime.
  - `GET /proxy_check?proxy=host:port&token={token}`: Kiểm tra trạng thái proxy (`proxy_ok` / `proxy_false`).
  - `GET /proxy_getip?proxy=host:port&token={token}`: Lấy IPv4 của proxy.
  - `GET /proxy_recreat?proxy=host:port&token={token}`: Reset/redial phiên PPPoE của cổng chỉ định để đổi IP Viettel mới.
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

---

## 5. Cấu Hình "NAT Cổng Proxy" (Bật/Tắt NAT) Trên Box MobiProxy

### Vị trí trên Web UI
- Tab / Panel **FIREWALL**: `NAT cổng proxy` (Form `id="nat-form"`, API `proxy.nat`, biến cấu hình `legacy.nat_port`).
- Trạng thái: `0` (Đang tắt) hoặc `1` (Đang bật).

### Bản chất kỹ thuật & Bằng chứng thực nghiệm (2026-09-08)
- **KHI TẮT (`nat_port: 0`):**
  - OpenWrt firewall trên box **CHẶN TOÀN BỘ KẾT NỐI TỪ WAN (Internet / Đà Nẵng)** vào các cổng proxy `5101..5138` (`WinError 10061: Connection refused`).
  - Hậu quả trực tiếp: Sing-box tại Đà Nẵng (`192.168.110.2:20001..20080`) không thể kết nối tới upstream `test.taadaa.click:51XX`, trả về thẳng `HTTP/1.1 502 Bad Gateway`.
  - Toàn bộ 80 máy Samsung S7 trên farm bị mất mạng (`dumpsys connectivity` báo `lastValidated: false`), kéo theo lỗi hàng loạt `profile username still mismatched after switch` trong feed runner.
- **KHI BẬT (`nat_port: 1`):**
  - Box kích hoạt rule DNAT / Port Forwarding và `MASQUERADE` trong firewall OpenWrt cho dải cổng proxy `5101..5138`.
  - Các kết nối WAN từ ngoài vào cổng `51xx` được chuyển tiếp thông suốt vào proxy daemon.
  - Ngay khi bật: `curl -x http://192.168.110.2:20001 http://api.ipify.org` lập tức trả về `HTTP 200 OK` kèm đúng IP Public Viettel của từng luồng PPPoE (`117.1.50.206`, `117.5.52.153`...), và điện thoại S7 chuyển sang `lastValidated: true` có mạng ngay lập tức.

### Quy tắc Farm Taadaa
- **BẮT BUỘC PHẢI BẬT (`nat_port: 1`):** Nút này bắt buộc phải bật để mở luồng WAN cho dàn máy Đà Nẵng kết nối vào proxy. Tuyệt đối KHÔNG ĐƯỢC TẮT. Nếu thấy máy farm đồng loạt mất mạng và Sing-box báo `502 Bad Gateway`, kiểm tra ngay API `http://test.taadaa.click/api.php?action=settings.get` xem `legacy.nat_port` có bị tắt về 0 hay không, nếu bị tắt thì gọi ngay API `proxy.nat` với `{"enabled": true}` để bật lại.
- **Xử lý khi Seller tắt NAT do Bot ngoài Internet scan quá tải:** Khi bot bên ngoài dò pass làm quá tải kết nối, seller thường tắt NAT port để hạ nhiệt con box. Việc tắt NAT này làm sập kết nối của cả dàn farm. Cách xử lý chuẩn: BẬT LẠI NAT PORT (`nat_port: 1`) kết hợp Whitelist IP WAN Kibe (mạng FPT, ví dụ `42.119.145.61`) vào tham số `allowed_ips` qua API `proxy.access_bulk`. Khi đó OpenWrt firewall chỉ cho phép IP Kibe kết nối và xác thực proxy, triệt tiêu 100% request rác từ bot quét ngoài Internet mà dàn máy farm vẫn chạy bình thường.
- **Tạm dừng Auto-Healer khi Box sập Cổng 1/DDNS:** Khi cổng 1 (5101) bị sập làm rụng DDNS `test.taadaa.click` hoặc Nginx trả `502 Bad Gateway`, BẮT BUỘC `pause` ngay cron `mobiproxy-auto-healer-watchdog` để tránh việc script tự động gửi API `/proxy_recreat` dồn dập khiến router OpenWrt bị nghẽn CPU.
- **Recipe bật NAT qua API (CSRF 2 bước, đã verify 2026-09-08):** `POST api.php?action=proxy.nat` bắt buộc header `X-CSRF-Token` lấy từ `<meta name="csrf-token">` trong `index.php` (KHÔNG dùng `_csrf` của `login.php`). Flow: (1) GET `login.php` lấy `_csrf` → POST login password; (2) GET `index.php` trích `csrf-token` meta; (3) POST JSON `{"enabled": true}` kèm `Content-Type: application/json` + `X-CSRF-Token` + `X-Requested-With: XMLHttpRequest`. Thiếu header đúng trả về `419 invalid_csrf`. Verify sau bật: `settings.get` → `legacy.nat_port == 1`, rồi `curl -x http://192.168.110.2:20001 http://api.ipify.org` phải trả `200 OK` + IP Viettel.
- **Chẩn đoán 2 tầng (tránh ngộ nhận modem UP = proxy sống):** Tầng box = `GET /proxy_check?proxy=test.taadaa.click:51XX&token=...` (`proxy_ok` chỉ chứng minh daemon/WAN còn đáp); tầng kênh = `curl -x http://192.168.110.2:200xx http://api.ipify.org` từ Đà Nẵng (quyết định S7 có mạng thật không). Box `proxy_ok` nhưng Sing-box `502` = firewall NAT tắt hoặc kênh WAN→51xx bị chặn, không phải modem rớt IP.

---

## 6. Xử Lý Khẩn Cấp Khi Web UI Treo / Chrome Báo ERR_CONNECTION_REFUSED
1. **Lỗi Chrome Auto-Upgrade HTTPS:**
   - Box MobiProxy chỉ chạy web HTTP cổng 80, không có SSL.
   - Luôn gõ rõ tiền tố: `http://test.taadaa.click` (tuyệt đối không để Chrome tự điền `https://`).
2. **Lỗi Quá Tải Do Script Healer Spam API Recreate:**
   - Nếu watchdog chạy cron dày (`*/1 * * * *`) và nhiều tiến trình cùng bắn `/proxy_recreat`, daemon PHP/Nginx trên box sẽ bị treo cứng.
   - Khắc phục: Kill sạch các process `mobiproxy_auto_healer` trên máy tính, pause cron hoặc chỉnh về `*/5 * * * *`, Web UI sẽ phản hồi lại bình thường sau vài giây.

---

## 7. Bão Quét Botnet / Brute-Force Ports 51xx & Hiện Tượng Sập Web (502 / Conntrack Overflow)
- **Cơ chế bão scan & sập chùm:** Khi BẬT NAT (`nat_port: 1`), dải cổng `5101..5138` mở toang ra Internet (`0.0.0.0/0`). Các scanner/botnet trên Internet quét dải IP Viettel kết nối và brute-force mật khẩu liên tục, làm tràn bảng theo dõi kết nối (`conntrack`) và CPU Mediatek MT7621 nhảy lên 100%. Hậu quả: Nginx/PHP cổng 80 bị nghẽn (`502 Bad Gateway` / timeout), người quản trị không thể truy cập web admin.
- **Hạn chế của Cloudflare & `allowed_ips` tầng App:**
  + Cloudflare gói Free/Pro chỉ hỗ trợ các cổng HTTP tiêu chuẩn, không bảo vệ được dải port TCP proxy `5101..5138` (đòi hỏi Cloudflare Spectrum). Hơn nữa scanner quét trực tiếp theo dải IP WAN Viettel chứ không qua hostname DNS.
  + Thiết lập `allowed_ips` trong `proxy.access_bulk` chỉ hoạt động ở tầng Proxy daemon; các gói tin SYN/TCP vẫn đập vào OpenWrt làm kiệt quệ tài nguyên chip MT7621.
- **Quy trình giải cứu khẩn cấp (Emergency Rescue Loop):**
  + Khi box bị nghẽn, việc F5 web thủ công để tắt NAT rất khó bắt kịp nhịp sống ngắn của backend.
  + Giải pháp: Triển khai script watchdog thăm dò `login.php` (interval 2s, timeout 3s). Ngay mili-giây đầu tiên khi backend PHP hồi phục (trả 200 OK), script lập tức bắt CSRF, đăng nhập tự động, và bắn ngay request `POST /api.php?action=proxy.nat` với `{"enabled": false}` để ngắt NAT tức thì.
  + Khi NAT tắt, OpenWrt drop toàn bộ traffic vào 51xx, CPU hạ nhiệt về 0%, web quản trị khôi phục hoàn toàn.
- **Giải pháp bền vững (Whitelisting ở Firewall):**
  + Để dùng được proxy mà không bị botnet quét sập: Trong cấu hình Port Forwarding / NAT của OpenWrt, cấu hình Source IP (Địa chỉ nguồn) giới hạn duy nhất IP WAN của Farm (IP máy Kibe / FPT) thay vì để `Any` (`0.0.0.0/0`).
