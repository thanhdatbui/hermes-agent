# MobiProxy Control panel (test.taadaa.click) — truy cập & API

## Hai lớp mật khẩu (ĐỪNG NHẦM)
- **Pass login panel** (admin, trang login.php): `n0spam@@` (2026-08-20) — chỉ để đăng nhập web.
- **Pass proxy client** (mỗi user mobiN dùng khi kết nối proxy): `TaadaaMobi#2026!` — nằm trong `PROXYgandienthoai.xlsx` cột C (`host:port:user:pass`).

## Đăng nhập web (CSRF token)
```
GET  http://test.taadaa.click/login.php            # lấy _csrf hidden
POST http://test.taadaa.click/login.php            # _csrf=<token>&password=<pass panel>
Set-Cookie: MOBIPROXY_V2=... (HttpOnly, SameSite=Strict)  # giữ cookie cho các request sau
```

## API trạng thái proxy (cần token API từ trang Bảo mật & API)
```
GET /proxy_getlist?token={api_token}          # toàn bộ proxy + ip_public + status
GET /proxy_check?proxy=test.taadaa.click:5101&token={api_token}   # {"result":"ok","content":"proxy_ok"}
GET /proxy_getip?proxy=test.taadaa.click:5101&token={api_token}   # {"result":"ok","content":"ipv4","ip":...}
GET /proxy_recreat?proxy=...&token={api_token} # reset 1 proxy
GET /proxy_rs_all_1?token={api_token}          # reset tất cả
```
Trả lỗi `{"content":"matkhau_khong_dung","message":"API token is invalid"}` khi thiếu/sai token. Token xem trong trang Bảo mật & API (JS render, action `security` → API `settings.get` trả `api_token`).

## API nội bộ (web app, dùng cookie session)
```
GET  /api.php?action=settings.get     # config: base_port, api_token, api_security, cloudflare...
GET  /api.php?action=dashboard        # proxies[]: index,name,installed,up,ipv4,ipv6,uptime,config{user,password,auth,allowed_ips}
GET  /api.php?action=client_policy.get
POST /api.php?action=proxy.access     # cấu hình auth 1 proxy (X-CSRF-Token header + JSON body)
POST /api.php?action=proxy.access_bulk# auth hàng loạt
POST /api.php?action=api.token.rotate
POST /api.php?action=settings.password# đổi pass panel {current_password,new_password,confirm_password}
```
CSRF cho POST: `meta[name="csrf-token"]` trong trang; header `X-CSRF-Token`.
API actions (2026-08-20): dashboard, settings.get, client_policy.*, network.credentials/plan/delete_lan, proxy.access/access_bulk/change_mac/reset/start/stop, notifications.*, update.check/status/start, audit.list, api.token.rotate, system.reboot/time_sync, automation.schedules.

## Cấu hình proxy thực tế (2026-08-20)
- 40 proxy, **32 UP** (uptime ~3.5h), auth `strong`, user `mobiN` (N = index), pass `TaadaaMobi#2026!`, `allowed_ips: []` (không whitelist IP — VPS kết nối được).
- Port base 5101 (IPv4) / 5201 (IPv6); egress IP mobile VN 27.69.x.x (Lan1).
- File Excel: `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx` — 185 dòng, device ID + proxy; OneDrive sync (mtime 12:36 khi đổi).
- Farm gán qua file này: máy Android VPN chạy bình thường khi proxy panel UP.

## Kiểm tra nhanh proxy từ bất kỳ đâu
```python
import urllib.request, urllib.parse
enc = urllib.parse.quote("TaadaaMobi#2026!", safe="")
ph = urllib.request.ProxyHandler({"http": f"http://mobi1:{enc}@test.taadaa.click:5101", "https": f"http://mobi1:{enc}@test.taadaa.click:5101"})
op = urllib.request.build_opener(ph)
with op.open("https://api.ipify.org?format=json", timeout=15) as r:
    print(r.read().decode())
```
Lưu ý: test song song nhiều proxy cùng lúc dễ gặp 407 dù proxy sống (MobiProxy giới hạn kết nối đồng thời) — test đơn lẻ để chẩn đoán.