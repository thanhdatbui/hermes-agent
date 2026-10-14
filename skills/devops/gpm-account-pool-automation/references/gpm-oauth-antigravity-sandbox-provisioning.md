# GPM OAuth Automation for Antigravity Sandbox Provisioning

## Bối cảnh & Căn nguyên

Khi vận hành pool tài khoản Google One / Antigravity Pro trên dàn máy Taadaa Farm:
- **Tài nguyên có sẵn:** GPM Login v3 (`:19995`) Group 10 (`Google_Live_Ready`) quản lý 77 tài khoản Google đang live, mỗi tài khoản được gán chết một cổng Proxy 4G di động riêng (`test.taadaa.click:PORT:USER:PASS`).
- **Nghẽn xác thực:** Trong cơ sở dữ liệu `storage.sqlite`, phần lớn tài khoản chưa hoàn tất bước cấp quyền OAuth (Authorize) cho Google Cloud Code / Antigravity CLI (`refresh_token` rỗng).
- **Mục tiêu:** Tự động hóa quy trình đăng nhập OAuth qua Playwright CDP để trích xuất `refresh_token` và đóng gói thành các profile sandbox độc lập cho `agy` CLI (`D:/Taadaa/agy_profiles/acc_XX`).

---

## Thông số OAuth Chính thức của Antigravity CLI

Các thông số này được Google nhúng công khai trong client Antigravity:
- **Client ID:** `1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com`
- **Client Secret:** `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`
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

### 1. Khởi động Profile GPM & Kết nối CDP
```python
start_res = gpm_get(f"/profiles/start/{PID}?win_scale=0.8")
cdp = start_res["data"]["remote_debugging_address"]
browser = playwright.chromium.connect_over_cdp(f"http://{cdp}")
page = browser.contexts[0].pages[0]
```

### 2. Mở URL Cấp quyền & Tự động Bấm Duyệt
GPM profile đã lưu sẵn cookie Google nên không cần gõ mật khẩu:
1. Điều hướng tới `authorize_url`.
2. Bắt sự kiện chọn tài khoản:
   - Click `[data-email*='{EMAIL}']` hoặc `text={EMAIL}`.
3. Bắt sự kiện chấp thuận quyền:
   - Click `#submit_approve_access` hoặc button `has-text('Tiếp tục')`, `has-text('Allow')`.
4. Lắng nghe callback URL (`http://127.0.0.1:.../callback?code=...`) để bóc tách tham số `code`.

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
