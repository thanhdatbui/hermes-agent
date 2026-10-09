# OmniRouter Antigravity OAuth + GPM Profile Automation

## 1. Mục đích
Tự động hóa luồng cấp quyền OAuth cho provider `antigravity` trên OmniRouter (`http://127.0.0.1:20129`) bằng các profile trình duyệt GPMLogin (Chrome Core 142) đã được cấu hình proxy và tài khoản Gmail tương ứng.

---

## 2. API Endpoints của OmniRouter (Port 20129)

- **Kiểm tra sức khỏe:** `GET http://127.0.0.1:20129/api/health`
- **Lấy danh sách Connections đã có:** `GET http://127.0.0.1:20129/api/providers`
  - *Lưu ý Endpoint:* Endpoint `GET /api/connections` KHÔNG TỒN TẠI (trả về HTTP 404). Danh sách connections nằm trong response `res.json().get("connections", [])` của `GET /api/providers`.
  - *Bẫy đếm tài khoản (Inventory Count Pitfall):* Danh sách connections của provider `antigravity` có thể chứa entry mặc định hệ thống / IDE profile không có `email` và `name` (`projectId: aicode-consumers`, `clientProfile: ide`). Khi đếm hoặc đối soát pool tài khoản Gmail LIVE, BẮT BUỘC lọc:
    ```python
    unique_accounts = set(
        (c.get("email") or c.get("name") or "").strip().lower()
        for c in res.get("connections", [])
        if c.get("provider") == "antigravity" and (c.get("email") or c.get("name"))
    )
    ```
    Nếu chỉ đếm `len([c for c in connections if c.get("provider") == "antigravity"])`, kết quả sẽ bị thừa +1 connection hệ thống, gây lệch dữ liệu đối soát.
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
- **Đồng Bộ Models & Quotas Sau Exchange (BẮT BUỘC):**
  - `POST http://127.0.0.1:20129/api/providers/<connection_id>/sync-models`
  - Giúp làm mới danh mục 11 models và quota snapshots cho connection vừa cấp quyền, tránh bị bộ lọc pre-dispatch loại bỏ (`ALL_TARGETS_SKIPPED`).

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
   - **Bẫy Header Email Collision (2026-09-05):** TUYỆT ĐỐI CẤM dùng `div:has-text("{email}")` không giới hạn URL, vì trên màn hình Consent (cấp quyền), Google render email của user tại chip ở header. Nếu quét `div:has-text("{email}")`, Playwright liên tục click vào header rồi `continue`, rơi vào vòng lặp vô tận và không bao giờ click được nút Consent / "Tiếp tục".
   - **Bộ chọn chuẩn:** Chỉ chạy khi URL chứa `chooser`, `selectaccount`, `accountchooser`, hoặc `identifier`. Dùng selector chính xác: `page.locator(f'div[data-identifier="{email}"], li:has-text("{email}")').first.click()`.
2. **Xử Lý Re-Auth Google Prompt (`challenge/dp`) & Thử Thách Thiết Bị Vật Lý Khi Cấp Quyền OAuth (2026-09-05):**
   - Khi cấp quyền nhạy cảm (Google Cloud / Developer OAuth Antigravity), Google kích hoạt màn hình xác minh danh tính thiết bị S7 (`challenge/dp` hoặc `challenge/ootp`).
   - **Bẫy đổi nhãn nút "Cách xác minh khác" (2026-09-05):** Google đã đổi nhãn nút chuyển phương thức từ *"Thử cách khác"* (`Try another way`) sang *"Cách xác minh khác"* (`More ways to verify`). Bắt buộc dùng selector mở rộng: `button:has-text("Cách xác minh khác"), button:has-text("Thử cách khác"), button:has-text("More ways to verify"), button:has-text("Try another way"), div[role="button"]:has-text("Cách xác minh khác"), div[role="button"]:has-text("Thử cách khác"), span:has-text("Cách xác minh khác")`.
   - **Ưu tiên thiết bị Android vật lý (Galaxy S7) trên luồng OAuth:**
     * Khác với đăng nhập web thông thường có thể chọn ngay Authenticator TOTP 6 số, trên luồng cấp quyền OAuth Antigravity, Google thường khóa chặt vào thiết bị phần cứng chính (Galaxy S7). Khi bấm *"Cách xác minh khác"*, màn hình `challenge/selection` có thể CHỈ hiển thị: (1) *Nhấn vào Có trên điện thoại hoặc máy tính bảng* (Prompt tap số); (2) *Sử dụng điện thoại để nhận mã bảo mật offline* (10 số).
     * **Bẫy nhầm lẫn input `name="Pin"` trên `challenge/ootp`:** Ô nhập mã 10 số ngoại tuyến có thuộc tính `name="Pin" type="tel"`. Script tuyệt đối KHÔNG được bắt `name="Pin"` hay `type="tel"` để điền mã TOTP 6 số (sẽ bị Google từ chối và rơi vào vòng lặp timeout). Chỉ điền mã TOTP khi URL chứa `challenge/totp` hoặc selector đặc hiệu `input#totpPin`.
     * **Xử lý duyệt thiết bị S7 & KỶ LUẬT DEVICE LOCK (User Rule 2026-09-05 - "Nhớ là lock device khi dùng"):** 
       Nếu Google không hiển thị tùy chọn Authenticator `type="6"`: Cần điều khiển ADB máy S7 tương ứng để tap đúng số hiển thị trên PC (Google Prompt) hoặc lấy mã bảo mật 10 số từ intent `GoogleSettingsLink`.
       **QUY TẮC AN TOÀN SỐ 1:** BẮT BUỘC bọc 100% lệnh can thiệp ADB vào:
       ```python
       with acquire_device_lock(
           machine=str(machine_id),
           serial=serial,
           project="gpm-login",
           bypass_proxy_readiness=True,
           force_preempt=True
       ) as lease:
           # Thao tác ADB trên S7...
       ```
       từ `automation_core.device_lock` (đường dẫn `D:\Taadaa\automation-core\src`) để tạm dừng cron nuôi TikTok.
       *LƯU Ý THUỘC TÍNH LEASE:* Đối tượng `DeviceLockLease` có thuộc tính `lease.lock_paths` (dạng list các Path), KHÔNG có thuộc tính `lease.lock_path` (gọi sẽ ném AttributeError).
       *Tra cứu Serial và Proxy tự động:* Đọc từ `PROXYgandienthoai.xlsx` thông qua hàm `automation_core.preflight.resolve_proxy_mapping_path()`.
       *Kết nối ATX Agent S7:* Dùng cổng per-device chuẩn `tcp:{17000 + mid}` trỏ về `tcp:7912`. Đọc hierarchy bằng `http://127.0.0.1:{17000 + mid}/dump/hierarchy`. Luôn bọc lệnh kiểm tra `adb -s <serial> shell echo ok` với timeout 5s để phát hiện sớm các máy dính ADB transport hang (như M68) tránh treo vòng lặp 900s. Trong khối `finally`, BẮT BUỘC gửi `keyevent 3` (HOME) để đưa thiết bị về màn hình chính trước khi nhả lock.
   - Nếu màn hình `challenge/selection` có xuất hiện *"Ứng dụng Authenticator"* (`div[data-challengetype="6"], li:has-text("Authenticator"), li:has-text("xác thực")`): Click chọn và tra cứu Secret Key 32 ký tự từ Excel (`master_gmail_manager.xlsx` cột 5 / `gmail_clean_v2.xlsx` cột 4) -> dùng `pyotp.TOTP(secret).now()` sinh mã 6 số điền vào ô `input#totpPin` và nhấn Enter để bypass 100% qua web.
3. **Màn hình Native App / First-Party Warning (`firstparty/nativeapp`):**
   - Tiêu đề: *"Make sure that you downloaded this app from Google"*
   - Click nút: `button:has-text("Sign in")`, `button:has-text("Đăng nhập")`, `button:has-text("Continue")`, `button:has-text("Tiếp tục")`, hoặc `#submit_approve_access`. Lưu ý kiểm tra `btn.is_visible()` trước khi click.
4. **Màn hình Cấp Quyền (Scopes Checkbox):**
   - Đánh dấu chọn tất cả scopes (`#select-all-scopes` hoặc các checkbox chưa tick).
5. **Màn hình Đăng Nhập Lại (Khi Session hết hạn):**
   - Tự động điền email (`input#identifierId`), điền mật khẩu (`input[type="password"]:not([aria-hidden="true"])`) từ kho quản lý `master_gmail_manager.xlsx`.
   - Lưu ý: Google có `input[type="password"][aria-hidden="true"]` là field ẩn — phải dùng selector loại trừ `aria-hidden`.
6. **Màn hình Checkpoint / Bị Kẹt:**
   - Nếu gặp xác minh SĐT hoặc 2FA không tự giải quyết được → tự động chụp ảnh màn hình lưu vào `D:\Taadaa\GPM auto\debug_screenshots\` và gửi đường dẫn để người dùng hướng dẫn.

### D. Đồng Bộ Hạn Token & Dọn Dẹp Sau Khi Xong (Kỷ Luật Bắt Buộc)
1. **Đồng bộ DB:** Sau khi exchange thành công, cập nhật `token_expires_at = expires_at` trong bảng `provider_connections` của `storage.sqlite` để tránh pre-dispatch skip do lệch timestamp cache.
2. **Đóng Profile GPM:** Gọi API `GET http://127.0.0.1:19995/api/v3/profiles/stop/<id>` để giải phóng profile.
3. **Kill Orphaned Processes:** Quét và kill sạch các tiến trình `chrome.exe` còn sót lại của profile directory đó để tránh kẹt lock file `Cookies` / `Preferences`.

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
1. **GPM DB** (`profile_data.db` → `JsonData.raw_proxy`): regex `:(200\d{2})` hoặc `:(51\d{2})` → port trực tiếp
2. **Master Excel** (`master_gmail_manager.xlsx` → cột `gpm_profile` = `"02 - email@..."`): `port = 20000 + số prefix`
3. **Clean V2** (`gmail_clean_v2.xlsx` → cột `machine` số máy): `port = 20000 + machine`

### Gán Proxy 1:1 Farm Port (`test.taadaa.click:5101..5138`):
Khi nạp các tài khoản cụm Kibe Farm S7 (ports `5101..5138`):
1. Query `GET http://127.0.0.1:20129/api/settings/proxies` → duyệt danh sách `items`, map item theo `item["port"] == target_port`.
2. Gọi `PUT http://127.0.0.1:20129/api/settings/proxies/assignments` với body `{"scope": "account", "scopeId": connection_id, "proxyId": proxy_id}`.
3. Gọi `POST http://127.0.0.1:20129/api/providers/<connection_id>/sync-models` để đồng bộ model.
4. **Loại trừ 100% tài khoản dính `khoaleemagic@gmail.com` (M34, M37, M71):** Tuyệt đối không mở profile, không cấp quyền OAuth và không nạp vào OmniRoute.
5. **Kỷ luật ngân sách Tool Calls (Budget Discipline):** Khi nhận chỉ đạo batch nạp OAuth đã có sẵn script mẫu và danh sách tài khoản/port, agent BẮT BUỘC tạo file runner (`run_add_oauth_batch*.py`) và chạy ngay qua `terminal` trong 2-3 turn đầu tiên. CẤM dùng 10-15 tool calls để đọc/kiểm tra rà soát lặp đi lặp lại các API/DB gây cạn kiệt ngân sách lượt gọi (`max_iterations = 15`) trước khi sinh ra kết quả thực tế.

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

## 8. Kết Quả Thực Tế (2026-09-04)

- Batch run thành công: **18 tài khoản Antigravity** active trong OmniRouter.
- Proxy gán thành công: **15/18** connection.
- 3 tài khoản không tìm được proxy (`thanhdatbui19951`, `thanhdatbui1995`, `jinrakal`) — không thuộc cụm máy Kibe 1-35, gán proxy thủ công nếu cần.
- Profile Google AI Pro (`bobbyxruizz0s0o@gmail.com` - GPM 15): Re-login và hoàn tất exchange code thành công, sync 11 models, khôi phục vị trí P11 trong pool `ag-gemini-pool-3`.
