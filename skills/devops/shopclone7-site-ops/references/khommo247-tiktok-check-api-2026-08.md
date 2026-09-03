# khommo247 TikTok check-live API — reverse-engineered (2026-08-20)

Sau chuỗi test dài (Camoufox headless/headful, CDP vào Chrome Hermes, cron VPS full, sweep 32 proxy farm) để qua Cloudflare + login gate khommo247, phát hiện cuối: **tool web chỉ là UI bọc một API HTTP đơn giản có thể gọi thẳng** — không cần mở browser cho từng acc.

## API

- `POST https://khommo247.com/api/tiktok_check.php`
- Body: `{"username": "<username>"}` (JSON, 1 username / request). KHÔNG có token, KHÔNG danh sách, KHÔNG CSRF header riêng.
- Headers tối thiểu đã verify hoạt động:
  ```
  Content-Type: application/json
  X-Requested-With: XMLHttpRequest
  Referer: https://khommo247.com/cong-cu/check-tiktok
  Cookie: KHOMMO247SESSID_V2=<session>; cf_clearance=<cf_clearance>
  User-Agent: chuẩn Chrome (tùy chọn nhưng nên có)
  ```
- Response live:
  ```json
  {"success":true,"status":"live","method":"oembed","user":{"username":"khaby.lame","nickname":"Khabane lame","bio":"","avatar":"","verified":false,"region":"","created":"","followers":0,"following":0,"likes":0,"videos":0}}
  ```
- Response die:
  ```json
  {"success":true,"status":"die","method":"scrape_html_detect","user":{"username":"tiktok","error_msg":"Tài khoản không tồn tại"}}
  ```
- Response lỗi tạm thời (cần retry):
  ```json
  {"success":false,"error":"Không thể kiểm tra @sonaairhrk395682. Vui lòng thử lại sau.","username":"sonaairhrk395682"}
  ```

## Chi tiết quan trọng

- **Cookies ràng buộc IP.** `cf_clearance` của Cloudflare gắn với IP lúc cấp. Nếu camoufox mở trang qua proxy `test.taadaa.click:5105` → lấy cookies → gọi API KHÔNG proxy / proxy khác sẽ dính 403 của CF. Phải gọi API qua CÙNG proxy đã lấy cookies. Verify: `curl -x "http://mobi5:TaadaaMobi%232026%21@test.taadaa.click:5105" -H "Cookie: ..." ... https://khommo247.com/api/tiktok_check.php` trả 200 (curl từ VPS qua farm proxy đã OK → **danh sách hàng loạt có thể chạy ngay trên VPS**, chỉ bước refresh cookies cần máy nhà).
- **Cách lấy cookies:** Camoufox (venv-core024, ≥0.5.5) `persistent_context=True, user_data_dir=%LOCALAPPDATA%\hermes\scripts\khommo_profile`, proxy dict `{"server":"http://test.taadaa.click:51xx","username":"mobiN","password":"TaadaaMobi#2026!"}` (KHÔNG geoip), `page.context.cookies()` sau khi vào tool → in ra `KHOMMO247SESSID_V2` + `cf_clearance`.
- **Quirk chính xác của tool:** acc nổi tiếng (`@tiktok`) bị trả `die`/“Tài khoản không tồn tại” SAI (oembed không handle creator-profile lớn). Ngược lại `success:false` là lỗi check tạm thời (có thể là rate-limit từ phía TikTok qua proxy đó). Quy tắc xử lý cho kho farm:
  - `status: "live"` → giữ.
  - `status: "die"` → chỉ tin nếu acc là dạng farm (`user...`, prefix lạ); với acc nổi tiếng nghi ngờ → re-check bằng VPS direct check (file khác).
  - `success: false` → retry 2-3 lần (đổi proxy nếu cần) rồi mới kết luận.
- **Call gốc từ web:** tool gửi 1 POST `tiktok_check.php` cho MỖI username (bắt được bằng `page.on("request")`). UI render kết quả vào body dạng bảng (`# USERNAME TÊN FOLLOWERS FOLLOWING LIKES VIDEOS VERIFIED STATUS` + dòng kết quả), KHÔNG ghi ngược vào `#ttList` — đừng đọc `#ttList.value` để lấy kết quả.
- **Login gate vẫn bắt buộc 1 lần:** tài khoản đã đăng nhập trong profile persistent (`thanhdatbui19951@gmail.com` / `kudat195@@`). Nếu session chết → mở `/dang-nhap` form `#loginEmail`/`#loginPass` rồi quay lại tool. Pass proxy farm `TaadaaMobi#2026!` ≠ pass panel MobiProxy `n0spam@@` (không nhầm).

## Script mẫu (đã chạy OK từ máy nhà, venv-core024)

```python
import os, json, requests

PROFILE_DIR = os.path.expandvars(r"%LOCALAPPDATA%\hermes\scripts\khommo_profile")
PROXY = {"server": "http://test.taadaa.click:5105", "username": "mobi5", "password": "TaadaaMobi#2026!"}
# ... mở Camoufox persistent_context, page.goto tool, chờ CF clear, đọc cookies ...
cookies_jar = {"KHOMMO247SESSID_V2": sess, "cf_clearance": cf}
proxies = {"http": "http://mobi5:TaadaaMobi%232026%21@test.taadaa.click:5105",
           "https": "http://mobi5:TaadaaMobi%232026%21@test.taadaa.click:5105"}
headers = {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest",
           "Referer": "https://khommo247.com/cong-cu/check-tiktok",
           "Cookie": "; ".join(f"{k}={v}" for k, v in cookies_jar.items())}
for u in ["khaby.lame", "sonaairhrk395682"]:
    r = requests.post("https://khommo247.com/api/tiktok_check.php",
                      json={"username": u}, headers=headers, proxies=proxies, timeout=25)
    print(u, r.text[:200])
```

## Tham chiếu chéo

- Recon UI khommo247 (37 textarea ẩn, `#ttList`/`#ttBtnStart`, login gate): `khommo247-check-tiktok-recon-2026-08.md`.
- Recipe máy nhà + proxy farm qua CF: `khommo247-home-machine-proxy-recipe-2026-08.md`.
- Thử cron VPS bất khả thi: `khommo247-vps-cron-attempt-2026-08.md`.
- VPS direct check TikTok (kênh chính, không phụ thuộc khommo247): `tiktok-direct-vps-checklive-2026-08.md`.