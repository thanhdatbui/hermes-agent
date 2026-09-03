# khommo247 check-tiktok — recipe qua CF từ MÁY NHÀ + proxy farm (verified 2026-08-20)

Mục tiêu: cron tự check live TikTok qua `khommo247.com/cong-cu/check-tiktok` mà không cần user thao tác.
Kết luận khả thi hiện tại: **chạy trên máy nhà (Windows Task Scheduler)**, KHÔNG chạy được trên VPS.
Tài khoản khommo247 (đăng ký free) là điều kiện bắt buộc cuối cùng — login gate không bypass được.

## Chuỗi bằng chứng host × IP (vì sao VPS bế tắc)

| Cấu hình | Egress IP | Kết quả CF khommo247 |
|---|---|---|
| Camoufox headful, chạy trên máy nhà, không proxy | IP nhà dân cư | ✅ PASS |
| Camoufox headful, chạy trên VPS (xvfb), không proxy | IP DO datacenter | ❌ "Just a moment" |
| Camoufox headful, chạy trên VPS + proxy farm (32 port sweep) | IP mobile PPPoE dân cư | ❌ toàn bộ CF_BLOCK |
| Camoufox headful, chạy trên MÁY NHÀ + proxy farm 5101 | IP mobile PPPoE dân cư | ✅ PASS (title "Check TikTok Hàng Loạt", `#ttList` có) |

⇒ **Host/fingerprint + IP kết hợp**: browser phải chạy trên máy có fingerprint trình duyệt thật (Windows máy nhà).
Browser chạy trên VPS dù egress qua cùng IP mobile vẫn bị Cloudflare nhận diện bot.
Bài học trước ("IP reputation quyết định CF") là kết luận SAI — chỉ đúng khi host cố định. VPS không thể thay máy nhà.

## Recipe ĐÃ VERIFY (máy nhà, venv `D:\CodexRuntime\tiktok-video\venv-core024`)

```python
import urllib.parse
from camoufox.sync_api import Camoufox

# 1) Upgrade camoufox lên >=0.5.5 (0.5.4 parse fail với proxy dict):
#    venv-core024\Scripts\pip.exe install --upgrade camoufox

proxy = {
    "server": "http://test.taadaa.click:5101",
    "username": "mobi1",
    "password": "TaadaaMobi#2026!",   # pass proxy — KHÔNG phải pass panel
}

with Camoufox(headless=False, proxy=proxy) as browser:   # KHÔNG geoip=True (rebuild URL pass raw -> parse fail)
    page = browser.new_page()
    page.goto("https://khommo247.com/cong-cu/check-tiktok", wait_until="domcontentloaded", timeout=60000)
    # chờ CF: title rời "Just a moment" / "Chờ một chút" / "Loading ..."
    for _ in range(30):
        low = page.title().lower()
        if "just a moment" not in low and "chờ một chút" not in low and not low.startswith("loading"):
            break
        page.wait_for_timeout(2000)
    # => title "Check TikTok Hàng Loạt - Kiểm Tra Tài Khoản Live/Die"
    page.fill("#ttList", "tiktok\nkhaby.lame")     # đúng id, KHÔNG textarea đầu tiên (37 textarea ẩn multi-tool)
    page.click("#ttBtnStart")                      # "Check tất cả"
    # -> modal .tool-login-gate "Yêu cầu đăng nhập" (nút Để sau / Đăng nhập)
    # -> "Để sau" chỉ đóng UI, backend KHÔNG chạy => cần login thật (xem mục dưới)
```

Pitfalls:
- **`geoip=True` làm hỏng proxy có pass đặc biệt** (`TaadaaMobi#2026!` chứa `#`): camoufox tự rebuild URL pass raw → `Failed to parse: http://mobi1:TaadaaMobi#2026!@...`. Để mặc định False. (VPS còn báo thêm LeakWarning — chỉ là warning.)
- Nhét user:pass vào `server` URL string dù đã URL-encode `%23` → `NS_ERROR_PROXY_CONNECTION_REFUSED` trong Camoufox, NHƯNG curl cùng URL thì OK → lỗi là cú pháp Camoufox, không phải firewall farm. Luôn dùng dict tách.
- Camoufox 0.5.4 (venv-core024 cũ) parse fail với dict → upgrade.
- Headless Camoufox bị CF chặn ngay cả IP nhà → bắt buộc headful (`headless=False`).
- Thời điểm chờ: sau CF trang title hiện `Loading https://...` rồi render UI ~3-8s; chờ tối đa 90s cho `#ttList`.

## Bước còn lại: login khommo247 (chặn cứng)

- Modal `.tool-login-gate`: "Yêu cầu đăng nhập — Bạn cần đăng nhập để sử dụng công cụ này." Nút "Để sau" chỉ đóng modal; bấm Check lại vẫn không trả kết quả (test nhiều lần, cả CDP profile thật).
- "Đăng nhập" → `/dang-nhap?return=%2Fcong-cu%2Fcheck-tiktok`, form `loginEmail` / `loginPass` (+ CSRF `_csrf` nếu POST thủ công). Đăng ký free ở trang ("Đăng ký bán" / "Đăng ký tài khoản").
- Sau khi có tk/mk: login qua Camoufox headful + proxy farm → cookie lưu context → vào tool → `#ttList` + `#ttBtnStart` → đọc kết quả từ `#ttList` (thay đổi sau check) hoặc section "Check Thông Tin TikTok".

## Recon panel proxy `test.taadaa.click` (MobiProxy) — các pass KHÔNG được nhầm

- Panel: `http://test.taadaa.click/` → redirect `login.php` (PHP, cookie `MOBIPROXY_V2`, CSRF `_csrf`). **Login panel pass: `n0spam@@`** (user cung cấp 2026-08-20).
- **Proxy pass (client dùng để connect): vẫn `TaadaaMobi#2026!`** trong `PROXYgandienthoai.xlsx` (185 dòng, format `host:port:user:pass`).
- API nội bộ (đã đăng nhập cookie): `api.php?action=dashboard` → `{ok, data:{proxies:[{index,name,installed,up,up_v6,uptime,ipv4,ipv6,config:{auth,user,password,allowed_ips,...}}]}}` — 32/40 proxy UP, auth `strong`, user `mobiN`. `api.php?action=settings.get` → `legacy.pass_proxy=1`, `api_security=true`.
- API công khai (`api_document.php`): `proxy_check?proxy=ip:port`, `proxy_getlist`, `proxy_getip`, `proxy_recreat` — đều yêu cầu `&token={api_token}` (khi `api_security=true`).
- Farm có ~8 port down lúc sweep (5109/5110/5119/5120 REFUSED) — sweep lại để chọn port sống.