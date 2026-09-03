# OmniRouter Antigravity OAuth + GPM Profile Automation

## 1. Mục đích
Tự động hóa luồng cấp quyền OAuth cho provider `antigravity` trên OmniRouter (`http://127.0.0.1:20129`) bằng các profile trình duyệt GPMLogin (Chrome Core 142) đã được cấu hình proxy và tài khoản Gmail tương ứng.

---

## 2. API Endpoints của OmniRouter (Port 20129)

- **Kiểm tra sức khỏe:** `GET http://127.0.0.1:20129/api/health`
- **Lấy danh sách Connections đã có:** `GET http://127.0.0.1:20129/api/providers`
  - Lọc `connection.provider == "antigravity"` để lấy danh sách Gmail đã kích hoạt.
- **Lấy thông tin Authorize (authUrl, codeVerifier, state):**
  - `GET http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri=http://127.0.0.1:20129/callback`
  - Trả về JSON:
    ```json
    {
      "authUrl": "https://accounts.google.com/o/oauth2/v2/auth?client_id=1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com&response_type=code&redirect_uri=http%3A%2F%2F127.0.0.1%3A20129%2Fcallback&scope=...&state=...&access_type=offline&prompt=consent",
      "state": "...",
      "codeVerifier": "...",
      "redirectUri": "http://127.0.0.1:20129/callback"
    }
    ```
- **Gửi Exchange Authorization Code để lưu Connection:**
  - `POST http://127.0.0.1:20129/api/oauth/antigravity/exchange`
  - Body:
    ```json
    {
      "code": "4/0ATsMZq...",
      "redirectUri": "http://127.0.0.1:20129/callback",
      "codeVerifier": "...",
      "state": "..."
    }
    ```
  - Response:
    ```json
    {
      "success": true,
      "connection": {
        "id": "...",
        "provider": "antigravity",
        "email": "user@gmail.com"
      }
    }
    ```

---

## 3. Luồng Tự Động Hóa Playwright CDP + Chrome Core 142

### A. Khởi chạy Chrome Core 142 với Proxy Chuẩn
```python
context = playwright.chromium.launch_persistent_context(
    user_data_dir=profile_folder_path,
    executable_path=CHROME_EXE,
    proxy={"server": f"http://192.168.110.2:{20000 + port_index}"},
    locale="vi-VN",
    headless=False,
    args=[
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--lang=vi-VN,vi"
    ]
)
```

### B. Bắt Authorization Code Bằng Network Interception (Kỹ Thuật Cốt Lõi)
Google Native App / First-party OAuth sẽ kích hoạt redirect loopback tới `http://127.0.0.1:20129/callback?code=...`.
Do chuyển trang nhanh hoặc không load được local body, **bắt buộc dùng `page.on("request")`** để lấy `code` ngay khi request vừa phát ra:
```python
captured_code = None
def on_request(req):
    nonlocal captured_code
    if "/callback" in req.url and "code=" in req.url:
        parsed = urllib.parse.urlparse(req.url)
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" in qs:
            captured_code = qs["code"][0]

page.on("request", on_request)
```

### C. Xử Lý Các Màn Hình Trên Google OAuth UI
1. **Màn hình Chọn Tài Khoản (`accountchooser`):**
   - Click vào element khớp email: `page.locator(f'div[data-identifier="{email}"], div:has-text("{email}")').first.click()`
2. **Màn hình Native App / First-Party Warning (`firstparty/nativeapp`):**
   - Click nút: `"Sign in"`, `"Đăng nhập"`, `"Tiếp tục"`, `"Continue"`, hoặc `#submit_approve_access`.
3. **Màn hình Cấp Quyền (Scopes Checkbox):**
   - Đánh dấu chọn tất cả scopes (`#select-all-scopes` hoặc các checkbox chưa tick).
4. **Màn hình Đăng Nhập Lại (Khi Session hết hạn):**
   - Tự động điền email (`input#identifierId`), điền mật khẩu (`input[type="password"]:not([aria-hidden="true"])`) từ kho quản lý `master_gmail_manager.xlsx`.
   - Lưu ý: Google có `input[type="password"][aria-hidden="true"]` là field ẩn — phải dùng selector loại trừ `aria-hidden`.
5. **Màn hình Checkpoint / Bị Kẹt:**
   - Nếu gặp xác minh SĐT hoặc 2FA không tự giải quyết được → tự động chụp ảnh màn hình lưu vào `D:\Taadaa\GPM auto\debug_screenshots\` và gửi đường dẫn để người dùng hướng dẫn.

---

## 4. Phát Hiện Profile Đã Logged-in (Cookie Check)

Thay vì mở browser và kiểm tra URL, phát hiện nhanh qua SQLite Cookie DB:

```python
def has_google_cookies(p_path: str) -> bool:
    cookie_files = [
        os.path.join(p_path, "Default", "Network", "Cookies"),
        os.path.join(p_path, "Network", "Cookies"),
        os.path.join(p_path, "Default", "Cookies"),
    ]
    for cf in cookie_files:
        if os.path.exists(cf):
            try:
                import shutil, tempfile
                tmp = tempfile.mktemp(suffix=".db")
                shutil.copy2(cf, tmp)  # copy vì Chrome lock file
                conn = sqlite3.connect(tmp)
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM cookies WHERE host_key LIKE '%.google.com' "
                    "AND name IN ('SID','SAPISID','SSID','HSID','__Secure-1PSID')"
                )
                cnt = cur.fetchone()[0]
                conn.close()
                os.remove(tmp)
                if cnt >= 3:
                    return True
            except:
                pass
    return False
```
- Profile có `≥3 Google auth cookies` → có session sống, dùng `launch_persistent_context` trực tiếp.
- Profile không có cookie hoặc `<3` → cần login lại.

---

## 5. OmniRouter Proxy Assignment (Đúng Scope)

```python
# Gán proxy cho connection Antigravity
resp = requests.put("http://127.0.0.1:20129/api/settings/proxies/assignments", json={
    "scope": "account",       # PHẢI là "account" (không phải "connection")
    "scopeId": conn_id,       # id của connection từ GET /api/providers
    "proxyId": proxy_id       # id từ GET /api/settings/proxies
})
```

### Thêm proxy vào registry nếu chưa có:
```python
resp = requests.post("http://127.0.0.1:20129/api/settings/proxies", json={
    "name": "mirotik_10001",
    "type": "http",
    "host": "mirotik1.taadaa.click",
    "port": 10001
})
# → 201 Created với id
```

### Map Singbox Port → Proxy Registry Name:
| Singbox Port | MikroTik External Port | Registry Name    |
|-------------|----------------------|-----------------|
| 20001       | 10001                | mirotik_10001   |
| 20002       | 10002                | mirotik_10002   |
| ...         | ...                  | ...             |
| 20035       | 10035                | mirotik_10035   |

Công thức: `external_port = singbox_port - 10000`

### Map Email → Singbox Port (Thứ tự ưu tiên):
1. **GPM DB** (`profile_data.db` → `JsonData.raw_proxy`): regex `:(200\d{2})` → port trực tiếp
2. **Master Excel** (`master_gmail_manager.xlsx` → cột `gpm_profile` = `"02 - email@..."`): `port = 20000 + số prefix`
3. **Clean V2** (`gmail_clean_v2.xlsx` → cột `machine` số máy): `port = 20000 + machine`

---

## 6. Google "Trình Duyệt Không An Toàn" khi Login Profile Mới

Khi dùng `subprocess.Popen(chrome.exe)` + `connect_over_cdp` trên profile **hoàn toàn trắng** (chưa có cookie/history), Google chặn đăng nhập với thông báo:
- `"Trình duyệt hoặc ứng dụng này có thể không an toàn"`
- `net::ERR_TOO_MANY_RETRIES` (nếu proxy socks5 format bị parse sai)

**Nguyên nhân:** Profile trắng + automation detection → Google reject toàn bộ login attempts.

**Giải pháp:** Dùng profile GPM cũ có sẵn cookie/history (kho 240 profile ẩn). `launch_persistent_context` vào thư mục profile đó → Google nhận Trust Score cao hơn và cho qua.

---

## 7. Scripts Chính

| Script | Mục đích |
|--------|---------|
| `D:\Taadaa\GPM auto\scripts\batch_add_logged_in_profiles.py` | Batch add OAuth các profile đã có Google cookie |
| `D:\Taadaa\GPM auto\scripts\relogin_and_add_omniroute.py` | Đăng nhập lại profile hết phiên + add OAuth |
| `D:\Taadaa\GPM auto\scripts\cdp_stealth_login_and_oauth.py` | CDP subprocess stealth mode (dùng khi cần bypass GPM API) |
| `D:\Taadaa\GPM auto\scripts\add_oauth_omniroute.py` | Script gốc add OAuth một tài khoản |
| `D:\OneDrive\AI-Tools\tools\omniroute\*` | Bản đồng bộ AI-Tools của các script trên |

---

## 8. Kết Quả Thực Tế (2026-09-03)

- Batch run thành công: **18 tài khoản Antigravity** active trong OmniRouter.
- Proxy gán thành công: **15/18** connection.
- 3 tài khoản không tìm được proxy (`thanhdatbui19951`, `thanhdatbui1995`, `jinrakal`) — không thuộc cụm máy Kibe 1-35, gán proxy thủ công nếu cần.
- Profile dính Google Prompt (challenge/ootp, challenge/dp): chụp ảnh debug → xử lý thủ công → chạy lại script sau.
