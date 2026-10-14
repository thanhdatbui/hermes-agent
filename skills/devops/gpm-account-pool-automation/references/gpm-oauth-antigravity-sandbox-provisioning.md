# GPM OAuth Automation for Antigravity Sandbox Provisioning

## Bối cảnh & Căn nguyên

Khi vận hành pool tài khoản Google One / Antigravity Pro trên dàn máy Taadaa Farm:
- **Tài nguyên có sẵn:** GPM Login v3 (`:19995`) Group 10 (`Google_Live_Ready`) quản lý 77 tài khoản Google đang live, mỗi tài khoản được gán chết một cổng Proxy 4G di động riêng (`test.taadaa.click:PORT:USER:PASS`).
- **Nghẽn xác thực:** Trong cơ sở dữ liệu `storage.sqlite`, phần lớn tài khoản chưa hoàn tất bước cấp quyền OAuth (Authorize) cho Google Cloud Code / Antigravity CLI (`refresh_token` rỗng).
- **Mục tiêu:** Tự động hóa quy trình đăng nhập OAuth qua Playwright CDP để trích xuất `refresh_token` và đóng gói thành các profile sandbox độc lập cho `agy` CLI (`D:/Taadaa/agy_profiles/acc_XX`).

---

## Thông số OAuth Chính thức của Antigravity CLI

Các thông số này được Google nhúng công khai trong client Antigravity:
- **Client ID:** `[REDACTED_GOOGLE_CLIENT_ID].apps.googleusercontent.com`
- **Client Secret:** `GOCSPX-[REDACTED_PUBLIC_DESKTOP_CLIENT_SECRET]`
- **Authorize URL:** `https://accounts.google.com/o/oauth2/v2/auth`
- **Token Endpoint:** `https://oauth2.googleapis.com/token`
- **Scopes Bắt buộc:**
  ```text
  https://www.googleapis.com/auth/cloud-platform
  https://www.googleapis.com/auth/userinfo.email
  https://www.googleapis.com/auth/userinfo.profile
  https://www.googleapis.com/auth/cclog
  https://www.googleapis.com/auth/experimentsandconfigs
  ```

---

## Quy trình Tự động hóa qua Playwright CDP

### 1. Khởi động Profile GPM & Kết nối CDP (Chống ECONNREFUSED)
```python
start_res = gpm_get(f"/profiles/start/{PID}?win_scale=0.8")
cdp = start_res["data"]["remote_debugging_address"]
# Bắt buộc: Chờ Chrome mở hoàn toàn cổng remote debugging trước khi connect CDP
time.sleep(4)
browser = playwright.chromium.connect_over_cdp(f"http://{cdp}")
page = browser.contexts[0].pages[0]
```

### 2. Mở URL Cấp quyền (Kèm login_hint) & Xử lý Thử thách Google
Khi xin quyền các scopes nhạy cảm (`cloud-platform`, `cclog`), Google thường kích hoạt cơ chế tái xác thực (Re-authentication):
1. **Tiêm login_hint vào Auth URL:**
   ```python
   if EMAIL and "login_hint=" not in auth_url:
       auth_url += f"&login_hint={urllib.parse.quote(EMAIL)}"
   ```
   Giúp Google nhận diện thẳng tài khoản cần cấp quyền, giảm tỷ lệ văng về trang chọn tài khoản chung.
2. **Bắt sự kiện chọn tài khoản (Account Chooser):**
   - Click `[data-email*='{EMAIL}']` hoặc `text={EMAIL}`.
3. **Bẫy Mật khẩu Tái xác thực (Password Re-auth Trap) & Chống Hang 90s:**
   - Khi Google hiện màn hình *"Chào mừng <email> - Nhập mật khẩu của bạn"*:
     - **Lỗi phổ biến:** Script chỉ phát hiện `has_pwd` rồi log `BỊ HỎI PASSWORD!` và đứng nhìn hết timeout 90s.
     - **Cách xử lý đúng:** Tự động click vào ô password để kích hoạt autofill của Chrome, sau đó bấm `#passwordNext` hoặc gửi phím `Enter`.
     - Nếu sau 2 lần thử không vượt qua (password chưa lưu hoặc dính 2FA OTP): Chụp ngay ảnh màn hình runtime `gpm_oauth_checkpoint.jpg` và thoát fail-fast ngay lập tức, CẤM ngồi chờ hết timeout 90s.
4. **Bắt sự kiện chấp thuận quyền:**
   - Click `#submit_approve_access`, `#identifierNext`, hoặc button `has-text('Tiếp theo')`, `has-text('Tiếp tục')`, `has-text('Allow')`.
5. Lắng nghe callback URL (`http://127.0.0.1:.../callback?code=...`) để bóc tách tham số `code`.

### 3. Đổi Code Lấy Tokens
Gửi POST request tới `https://oauth2.googleapis.com/token`:
```python
data = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": captured_code,
    "grant_type": "authorization_code",
    "redirect_uri": REDIRECT_URI
}
# Trả về: access_token, refresh_token, id_token, expires_in
```

---

## Tự động Đóng gói Profile Sandbox cho `agy`

Khi nhận được token, tự động khởi tạo thư mục profile:
```text
D:/Taadaa/agy_profiles/acc_XX/
  ├── AppData/Roaming/
  ├── AppData/Local/
  ├── Temp/
  └── .gemini/
        ├── installation_id     # UUID sinh ngẫu nhiên mới
        ├── google_accounts.json # {"active": email, "old": []}
        └── oauth_creds.json    # access_token, refresh_token, scope
```

### Chuẩn hóa Proxy từ GPM sang HTTP Proxy URL:
Chuỗi `raw_proxy` từ GPM: `test.taadaa.click:5136:mobi36:TaadaaMobi#2026!`  
Chuyển đổi sang URL gán cho `agy`:
```python
host, port, user, pwd = raw_proxy.split(":")
encoded_pwd = urllib.parse.quote(pwd, safe="")
proxy_url = f"http://{user}:{encoded_pwd}@{host}:{port}"
```
Ghi nhận profile vào `D:/Taadaa/agy_profiles/profiles_config.json`:
```json
{
  "name": "acc_02",
  "proxy": "http://mobi36:TaadaaMobi%232026%21@test.taadaa.click:5136",
  "path": "D:/Taadaa/agy_profiles/acc_02",
  "enabled": true
}
```

---

## Quy tắc An toàn Bắt buộc (Safety Invariants)

1. **Canary Đơn Nick Đầu Tiên:** Bắt buộc chạy thử nghiệm hoàn chỉnh trên 1 nick trước khi kích hoạt batch cuốn chiếu.
2. **Dọn dẹp Tiến trình Chrome (Zombified Process Prevention):** GPM đóng profile qua API đôi khi để sót tiến trình Chrome ngầm. Bắt buộc kết hợp `psutil` để quét và kill triệt để Chrome instance sau khi lấy token xong.
3. **Không Tái sử dụng `installation_id`:** Mỗi sandbox profile bắt buộc phải sở hữu một mã UUID riêng biệt để tránh kích hoạt cơ chế phát hiện Sybil/Multi-account của Google Cloud Code.
4. **Không Viết Plaintext Client Secret/ID vào Markdown Skill:** Chuỗi Google OAuth Client Secret có tiền tố `GOCSPX-` và Client ID dạng `...apps.googleusercontent.com` bị GitHub Push Protection quét tự động và CHẶN ĐỨNG lệnh push toàn repository (`push declined due to repository rule violations`). Bắt buộc luôn che giấu dạng `[REDACTED_...]` hoặc nạp từ file cấu hình/biến môi trường.

