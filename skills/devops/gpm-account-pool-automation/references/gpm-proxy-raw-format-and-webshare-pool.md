# GPM Proxy Format & Webshare Free Proxy Integration Reference

## 1. GPM Profile Proxy Format Contract (`raw_proxy`)

Khi cập nhật proxy cho profile GPMLogin qua Local API v3 (`http://127.0.0.1:19995/api/v3/profiles/update/<profile_id>`):

### ❌ Sai (Lỗi `ERR_NO_SUPPORTED_PROXIES` hoặc `Không thể kết nối tới proxy`):
```json
// Không truyền dạng URL scheme có auth lồng vào raw_proxy
{"raw_proxy": "http://user:pass@ip:port"}
{"raw_proxy": "socks5://user:pass@ip:port"}
```
*Hậu quả:* GPM parse sai format, truyền sai cờ command-line proxy vào Chromium khiến Playwright mở trang bị văng lỗi `Page.goto: net::ERR_NO_SUPPORTED_PROXIES`.

### ✅ Đúng (Chuẩn Canonical GPM API):
```json
// 1. Proxy có xác thực (4 trường phân cách bằng dấu 2 chấm):
{"raw_proxy": "ip:port:username:password"}
// Ví dụ:
{"raw_proxy": "198.46.161.42:5092:opmighkf:htikm8njcmjb"}

// 2. Proxy KHÔNG CẦN xác thực (2 trường host:port - như MikroTik 3proxy LAN sau khi bỏ auth):
{"raw_proxy": "host:port"}
// Ví dụ:
{"raw_proxy": "mirotik1.taadaa.click:10007"}
```

### 🚨 Cập Nhật Proxy Hàng Loạt Qua API Khi Hạ Tầng Bỏ Mật Khẩu (2026-10-08):
Khi hạ tầng proxy bỏ user/pass (ví dụ MikroTik 3proxy `admin@1:admin@1` được gỡ bỏ):
```python
import urllib.request, json

# 1. Lấy toàn bộ danh sách profile
req = urllib.request.urlopen("http://127.0.0.1:19995/api/v3/profiles?limit=500")
profiles = json.loads(req.read().decode()).get("data", [])

# 2. Quét và cập nhật các profile có proxy dính pass cũ
for p in profiles:
    raw = p.get("raw_proxy") or ""
    if ":admin@1:admin@1" in raw:
        new_raw = raw.replace(":admin@1:admin@1", "")
        prof_id = p["id"]
        url = f"http://127.0.0.1:19995/api/v3/profiles/update/{prof_id}"
        payload = json.dumps({"raw_proxy": new_raw}).encode("utf-8")
        req_up = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_up) as resp:
            print(f"Updated {p.get('name')}: {new_raw}")
```

Sau khi update `raw_proxy`, thực hiện chuỗi đóng/mở profile:
1. `POST /api/v3/profiles/close/<profile_id>` kèm body `{}`
2. Chờ 1-2 giây để process Chromium cũ giải phóng port CDP.
3. `POST /api/v3/profiles/start/<profile_id>` với body `{"win_scale": "0.8"}` để lấy `remote_debugging_address` mới.

---

## 2. Webshare Free Account Proxy Pool (`thanhdatbui1995@gmail.com`)

Tài khoản Webshare cá nhân có sẵn 10 proxy miễn phí (1 GB bandwidth/tháng) với chứng thực cố định:
* **Username:** `opmighkf`
* **Password:** `htikm8njcmjb`

### Danh sách Proxy US khả dụng (Live & Fast):
1. `198.46.161.42:5092` — US (Los Angeles, California)
2. `198.23.243.226:6361` — US (Los Angeles, California)
3. `38.154.185.97:6370` — US (Piscataway, New Jersey)
4. `191.96.254.138:6185` — US (Los Angeles, California)

### Global Proxies:
* **GB (London):** `31.59.20.176:6754`, `45.38.107.97:6014`
* **ES (Madrid):** `64.137.96.74:6641`
* **PL (Warsaw):** `84.247.60.125:6095`
* **JP (Tokyo):** `142.111.67.146:5611`
* **DE (Frankfurt):** `31.58.9.4:6077`

---

## 3. Meta / Facebook & Instagram OAuth Automation & DOM Traps

### A. Dynamic Locale & Button Selector Pitfall (QUAN TRỌNG)
* **Bẫy ngôn ngữ theo IP Proxy:** Nút đăng nhập của Facebook/Instagram OAuth (`/login/?app_id=...`) tự động thay đổi ngôn ngữ theo IP của proxy hoặc header trình duyệt (ví dụ IP US/Châu Âu có thể render tiếng Pháp `"Se connecter"`, tiếng Anh `"Log In"`, hoặc tiếng Việt `"Đăng nhập"`).
* **Bẫy thẻ Button vs Div Role:** Facebook dùng `<div role="button">` hoặc `<input type="submit">`, KHÔNG dùng `<button type="submit">`. Locator `button[type="submit"]` sẽ bị timeout 30s.
* **Quy tắc selector chuẩn:**
  ```python
  # Locator bắt đa ngôn ngữ và mọi biến thể thẻ submit:
  login_btn = page.locator('div[role="button"]:is(:has-text("Đăng nhập"), :has-text("Log In"), :has-text("Se connecter"), :has-text("Iniciar sesión")), input[type="submit"]')
  login_btn.first.click()
  ```

### B. CẤM gọi `form.submit()` trực tiếp qua JavaScript
* Gọi `document.getElementById("login_form").submit()` sẽ **bỏ qua cơ chế mã hóa mật khẩu phía client (`enc_password`)** và các token CSRF của React, khiến Facebook trả về màn hình lỗi: *"Không thể xử lý yêu cầu của bạn - Đã xảy ra lỗi với yêu cầu này"*.
* **Cách làm đúng:** Luôn dùng `page.bring_to_front()`, điền thông tin qua `locator.fill()` (hoặc `keyboard.type`), sau đó click vào nút `[role="button"]` hoặc `input[type="submit"]` để kích hoạt đầy đủ event handler của Meta.

### C. Các bẫy Checkpoint sau Login của Acc Clone:
1. **WhatsApp 2FA:** Facebook chuyển hướng tới `/auth_platform/codesubmit/` đòi mã gửi về số điện thoại WhatsApp của chủ cũ (ví dụ đầu số `+216` Tunisia). Khi gặp bẫy này, acc kẹt 100% nếu không có quyền truy cập WhatsApp.
2. **Google reCAPTCHA Enterprise (`referer_frame.php`):** Facebook nhúng iframe kiểm tra captcha ẩn khi phát hiện đăng nhập từ IP lạ.
3. **Instagram Meta Accounts Center Collision:** Màn hình `/add_accounts/` báo lỗi *"Đã thuộc Tài khoản Meta này rồi"*: Do acc Instagram đã liên kết với 1 tài khoản Meta khác trước đó, Meta chặn không cho liên kết với tài khoản Meta thứ hai để xác thực tuổi.
4. **Mobile App Cookie vs Web Cookie:** Cookie trích xuất từ Android App (mbasic / katana) mang định dạng session riêng, khi nạp vào Chrome Web dễ bị Meta trả HTTP 400 Bad Request hoặc xóa `c_user`.

---

## 4. Bẫy Acc Clone "Android Registration" khi mang lên Desktop Web (Meta Anti-Fraud)

* **Bản chất tài khoản Clone trên shop:** Phần lớn acc clone giá rẻ trên các shop (Doravo, CloneFBIG, SHOPCLONE7) có mô tả `Android Registration` (được tạo và reg tự động hàng loạt trên Facebook/Instagram Mobile App Android, đi kèm `UA APP`).
* **Cơ chế phát hiện bất thường môi trường của Meta (Environment Jumping):**
  * Thiết bị tin cậy duy nhất của acc là Android App.
  * Khi mang tài khoản này đăng nhập trực tiếp trên trình duyệt máy tính (Chrome PC, GPM Desktop Browser) trên một IP proxy mới:
    * Thuật toán Risk Engine của Meta đánh giá rủi ro cực cao (từ Mobile App chuyển sang Desktop Browser trên IP mới).
    * **Hệ quả tức thì:** Kích hoạt ngay một trong các cơ chế xác minh mà người mua không vượt qua được:
      1. Đòi mã OTP gửi về WhatsApp cài trên SIM điện thoại ảo gốc của người bán (ví dụ đầu số `+216...`).
      2. Kích hoạt Google reCAPTCHA Enterprise (`referer_frame.php`).
      3. Báo lỗi form không hợp lệ hoặc checkpoint khóa acc.
* **Quy tắc vận hành chuẩn:**
  * **Để xác thực tuổi (Age Verification) trên các nền tảng AI như Muse AI:** Ưu tiên số 1 là dùng thẻ Visa/Mastercard (ảo hoặc thật chỉ cần có $1 để authorize $0 rồi nhả ngay), KHÔNG phụ thuộc vào acc clone mạng xã hội.
  * **Nếu bắt buộc dùng acc clone Meta:** Phải đăng nhập acc vào App Facebook/Instagram trên thiết bị Android thật (ví dụ dàn máy Farm Taadaa) trước để nuôi trust và xác thực trên thiết bị quen thuộc, không đăng nhập trực tiếp lần đầu trên Desktop Web.

---

## 5. Playwright CDP Popup Unfocused Input Trap & `bring_to_front()`

* **Bẫy cửa sổ Popup không nhận phím:** Khi tương tác với OAuth popup qua Chrome CDP, lệnh `page.mouse.click(x, y)` và `page.keyboard.type(text)` sẽ bị nuốt chửng nếu popup chưa có focus hệ thống (`email=''`, `pass_len=0`).
* **Bắt buộc:**
  ```python
  popup_page.bring_to_front()
  popup_page.locator('input[name="email"]').fill(user)
  popup_page.locator('input[name="pass"]').fill(password)
  # Luôn verify read-back giá trị thực tế trên DOM trước khi submit:
  assert popup_page.evaluate('() => document.querySelector("input[name=\'pass\']").value.length') > 0
  ```

---

## 6. Captcha Solver Integration & reCAPTCHA Enterprise
* Xem chi tiết kiến trúc giải captcha, rào cản AI tổng quát vs chuyên dụng và phương án tích hợp REST API / Extension tại:
  `references/captcha-solving-architecture-and-services.md`.


