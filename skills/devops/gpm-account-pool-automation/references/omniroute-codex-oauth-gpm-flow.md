# OmniRoute Codex OAuth + GPM Profile Automation & 1:1 Proxy Flow

## 1. Tổng Quan Kiến Trúc
Tự động hóa luồng cấp quyền / đăng nhập lại OAuth cho provider `codex` (OpenAI ChatGPT/Codex) trên OmniRoute (`http://localhost:20129`) thông qua các profile trình duyệt GPMLogin (Port 19995) mang IP Proxy 1:1 (cụm Mobi 4G Farm S7 `5101..5138` hoặc MikroTik).

---

## 2. Cơ Chế PKCE Callback Server Của Codex Trên OmniRoute (Port 20129)

Khác với Antigravity (dùng direct exchange code), Codex trên OmniRoute sử dụng cơ chế **PKCE Local Callback Server**:

1. **Khởi động Callback Server:**
   - Endpoint: `GET http://localhost:20129/api/oauth/codex/start-callback-server`
   - OmniRoute khởi tạo một HTTP server lắng nghe trên loopback port cố định `1455` (đường dẫn `/auth/callback`).
   - Sinh PKCE `codeVerifier`, `state` và trả về JSON:
     ```json
     {
       "authUrl": "https://auth.openai.com/oauth/authorize?response_type=code&client_id=app_EMoamEEZ73f0CkXaXp7hrann&redirect_uri=http%3A%2F%2Flocalhost%3A1455%2Fauth%2Fcallback&scope=openid%20profile%20email%20offline_access&code_challenge=...&state=...",
       "codeVerifier": "...",
       "redirectUri": "http://localhost:1455/auth/callback",
       "serverPort": 1455
     }
     ```
2. **Lắng nghe & Trao đổi Token Tự Động:**
   - Server local port 1455 nhận GET request từ trình duyệt: `/auth/callback?code=...&state=...`.
   - Trả về trang HTML thông báo *"Authentication Successful"* và lưu `callbackParams`.
3. **Poll Callback & Upsert Connection:**
   - Endpoint: `POST http://localhost:20129/api/oauth/codex/poll-callback` với body `{}`.
   - Khi `callbackParams` đã nhận: OmniRoute tự động gọi upstream OpenAI exchange code lấy JWT tokens (`id_token`, `access_token`, `refresh_token`), parse `chatgpt_account_id` / `chatgpt_plan_type`, lưu connection vào database và trả về:
     ```json
     {
       "success": true,
       "connection": {
         "id": "uuid-...",
         "provider": "codex",
         "email": "user@icloud.com",
         "displayName": "user@icloud.com"
       }
     }
     ```

---

## 3. Khởi Chạy GPM Profile & Kết Nối Playwright CDP

1. **Start Profile qua Local API v3 (Port 19995):**
   - Gọi: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`
   - Trích xuất: `remote_debugging_address` (VD: `127.0.0.1:56753`).
   - Chờ Chrome bind port: `time.sleep(2.5)` kèm retry loop 5-6 lần khi `connect_over_cdp`.
2. **Lọc Bỏ Extension Offscreen Pages (Bắt Buộc):**
   ```python
   ctx = browser.contexts[0]
   regular_pages = [p for p in ctx.pages if not p.url.startswith("chrome-extension://")]
   page = regular_pages[0] if regular_pages else ctx.new_page()
   ```

---

## 4. Cạm Bẫy Loopback Proxy & Kỹ Thuật Dual-Capture Callback (CRITICAL)

### Vấn Đề (Hairpin / Loopback Proxy Block):
Khi profile GPM chạy với proxy ngoài (như Mobi 4G `test.taadaa.click:5101` hoặc MikroTik), một số phiên bản Chrome/gpmdriver có thể chuyển hướng request `http://localhost:1455/auth/callback` lên proxy thay vì loopback máy host. Proxy ngoài không thể kết nối tới `localhost:1455` của PC host, dẫn tới lỗi `ERR_CONNECTION_REFUSED` hoặc `ERR_PROXY_CONNECTION_FAILED`, làm callback server của OmniRoute không bao giờ nhận được code!

### Giải Pháp Dual-Capture & Host-Side Forwarding:
1. **Bắt URL chứa Code từ Chrome:**
   - Dùng `page.on("request")` và liên tục kiểm tra `page.url`:
     ```python
     captured_callback_url = None
     def on_request(req):
         nonlocal captured_callback_url
         if ("/callback" in req.url or "/auth/callback" in req.url) and "code=" in req.url:
             captured_callback_url = req.url
     page.on("request", on_request)
     ```
2. **Forward Chủ Động Từ Script Host:**
   - Ngay khi phát hiện `code=` trên `page.url` hoặc qua request event, Python script chạy trên host chủ động gửi một HTTP GET nội bộ:
     ```python
     parsed = urllib.parse.urlparse(captured_callback_url)
     local_url = f"http://127.0.0.1:{server_port}{parsed.path}?{parsed.query}"
     requests.get(local_url, timeout=5)
     ```
   - Request này đảm bảo 100% server `1455` nhận được callback params và kích hoạt luồng exchange tokens.

---

## 5. Tự Động Hóa Giao Diện OpenAI OAuth

Khi điều hướng tới `authUrl`:
- Nếu session ChatGPT/OpenAI còn sống: OpenAI tự động hiển thị màn hình cấp quyền hoặc tự động redirect về callback URL.
- Quét và click các nút chấp thuận nếu xuất hiện:
  - `button:has-text("Continue"), button:has-text("Tiếp tục")`
  - `button:has-text("Accept"), button:has-text("Allow"), button:has-text("Cho phép")`
  - `button:has-text("Authorize"), button[type="submit"]`
- Nếu gặp màn hình chọn Workspace / Organization: Click workspace mặc định hoặc nút Submit.
- Nếu gặp Cloudflare Turnstile hoặc Captcha: Cho phép thời gian chờ (timeout 60-75s) để Cloudflare tự giải hoặc user can thiệp.

---

## 6. Gán Proxy 1:1 Cho Connection Trên OmniRoute

Sau khi poll-callback trả về `success: true` và `connection["id"]`:
```python
# Gán đúng Proxy 1:1 theo Proxy Registry của OmniRoute
resp = requests.put("http://localhost:20129/api/settings/proxies/assignments", json={
    "scope": "account",         # BẮT BUỘC là "account" (không dùng "connection")
    "scopeId": connection["id"],
    "proxyId": target_proxy_id
})
```

---

## 7. Bản Đồ Mapping Thực Tế (Tài Khoản Codex ↔ Port ↔ GPM Profile)

| Port | Proxy ID OmniRoute | Profile GPM ID | Thư Mục Profile | Email Codex Đang Lưu Login / Cookie |
|---|---|---|---|---|
| **5101** | `2b59fcae-cba5-45a4-9570-30a930eb163c` | `08a734cd-751f-4462-9c0a-343ada64ab64` | `x_rua_jidbq` | `bevels.vanity8s@icloud.com` |
| **5102** | `e6b75277-c113-4581-9008-f71245e94885` | `ba0dbe74-95e2-4dea-a5dd-59bd31d2ad39` | `2_r7clp` | `dishes.66-panic@icloud.com` |
| **5103** | `ad030a88-e465-48eb-a25f-65571e407d2d` | `96580472-6f9e-4906-8fb7-2f4e4a12f7f6` | `10_p5cej` | `98.duper-comb@icloud.com` |
| **5104** | `26f478c1-2b94-407b-984c-c7f87e1f7a66` | `89f48f5b-759f-4962-8426-b7647eeaa79d` | `4_hmmy5` | `coaster.leafed-5x+5diuz@icloud.com` |
| **5105** | `6765914c-44af-4427-bbf1-f03b6373e616` | `1b487fa5-dea4-40c3-97c9-fc198558efba` | `5_vqxmk` | `bulbous_elector_3m@icloud.com` |
| **5108** | `77c6d61b-d012-4bcc-bd02-72ec4747b84f` | `4bd0ad22-bb07-4c21-b30d-949f4d9eed43` | `8_vuchy` | `bevels.vanity8s@icloud.com` |
| **5111** | `93ffc9bf-6376-47df-ab66-a465afd8136a` | `d1dce8e9-722c-4273-ab43-604b628bfe05` | `9_bk115` | `quocthanhthao.962@outlook.com` |

> *Lưu ý quan trọng (2026-09-05):* Proxy ID cũ của port 5111 (`f70536fe-b289-4d15-a11c-d32f3afa9e15`) không còn tồn tại trên OmniRoute và sẽ gây lỗi `Proxy not found: f70536fe...`. Proxy active hiện tại là `93ffc9bf-6376-47df-ab66-a465afd8136a`. Khi gán proxy 1:1, script runner cần có cơ chế fallback tra cứu động qua `GET /api/settings/proxies` lọc theo `port == target_port` để luôn lấy được Proxy ID mới nhất.

---

## 8. Script Runner Sản Xuất

Được lưu trữ tại: `D:\Taadaa\GPM auto\scripts\run_codex_oauth_flow.py`

### Cách Sử Dụng CLI:
```bash
# Liệt kê tất cả profiles đã cấu hình sẵn mapping
python "D:/Taadaa/GPM auto/scripts/run_codex_oauth_flow.py" --list

# Mở và nạp OAuth cho Profile Máy 01 (Port 5101)
python "D:/Taadaa/GPM auto/scripts/run_codex_oauth_flow.py" --machine 1

# Mở và nạp OAuth theo Port chỉ định (VD Port 5102)
python "D:/Taadaa/GPM auto/scripts/run_codex_oauth_flow.py" --port 5102

# Mở theo Profile ID tùy ý
python "D:/Taadaa/GPM auto/scripts/run_codex_oauth_flow.py" --profile-id ba0dbe74-95e2-4dea-a5dd-59bd31d2ad39 --proxy-id e6b75277-c113-4581-9008-f71245e94885
```

---

## 9. Danh Mục Pitfalls & Lưu Ý Quan Trọng (2026-09-05)

1. **Python Toolchain Mismatch trên Windows:** BẮT BUỘC chạy script bằng lệnh `python` (Python 3.11 hệ thống), TUYỆT ĐỐI KHÔNG dùng `python3` (trỏ vào venv 3.12 của Hermes agent bị lỗi `ModuleNotFoundError: No module named 'greenlet._greenlet'` khi import Playwright).
2. **Xử Lý Tuần Tự (Sequential Only):** OmniRoute callback server chỉ lắng nghe duy nhất 1 luồng trên port `1455` tại một thời điểm (`fixedPort: 1455`). TUYỆT ĐỐI KHÔNG mở song song nhiều profile khi nạp Codex OAuth gây xung đột callback code.
3. **Kỷ Luật Cleanup & Process Guard (Finally Block):** Sau khi xử lý xong từng profile (kể cả thành công, timeout hay gặp checkpoint), khối `finally` bắt buộc gọi `stop/{id}` trên GPM và quét kill tiến trình `chrome.exe` mồ côi theo remote debugging port để giải phóng RAM.
4. **Kỷ Luật Ngân Sách Lượt Gọi Khi Dispatch Worker (3 Bước Tinh Gọn):** Khi Coordinator đã xác nhận môi trường và dữ liệu đối soát, prompt dispatch worker BẮT BUỘC chỉ định làm đúng 3 bước: `write_file -> py_compile -> chạy script / báo cáo`. CẤM TUYỆT ĐỐI giao prompt mở khiến worker tiêu tốn 30-35 tool calls đọc lại hàng loạt file tham chiếu gây cạn kiệt ngân sách `max_iterations = 35`.
5. **Dynamic Proxy Resolution & Proxy ID Drift (2026-09-05):** Proxy ID trong OmniRoute có thể thay đổi/recreate khi reset hoặc import lại registry (ví dụ port 5111 đổi từ `f70536fe...` sang `93ffc9bf...`). Nếu dùng Proxy ID cũ sẽ bị lỗi 404 `Proxy not found`. Script runner bắt buộc có hàm lookup động `GET /api/settings/proxies` lọc `port == target_port` để luôn lấy proxyId hợp lệ trước khi gán.
6. **Lỗi `profile_path` bị None từ GPM API v3 & Autofill Decryption Fallback (2026-09-05):**
   - API GPM v3 (`GET /api/v3/profiles/start/{id}`) trả JSON `data` KHÔNG chứa trường `profile_path`. Nếu script dùng `profile_path = res_data.get("profile_path")` sẽ bị `None`, khiến hàm `get_saved_password` bị bỏ qua và script kẹt ở ô password dẫn đến timeout 120s.
   - **Khắc phục:** Bắt buộc map trực tiếp `profile_path` (`8_vuchy`, `2_r7clp`, `10_p5cej`, `5_vqxmk`, `9_bk115`) trong `PROFILES_CONFIG` hoặc tra cứu từ cột `ProfilePath` trong `profile_data.db`. Trong `run_oauth_flow`, giữ fallback theo `profile_id` và chỉ cập nhật `if res_data.get("profile_path"): profile_path = res_data.get("profile_path")`.
   - **Tự động điền mật khẩu & Submit:** Dùng DPAPI (`win32crypt.CryptUnprotectData`) giải mã master key trong `Local State`, sau đó dùng `AESGCM` giải mã `password_value` trong bản sao `Default/Login Data`. Sau khi `pwd_loc.first.fill(saved_pwd)`, bắt buộc click submit button (`Tiếp tục`, `Continue`, `Log in`) hoặc nhấn `Enter`.
7. **Phát hiện lỗi OpenAI `account_deactivated` để Fail-Fast (2026-09-05):**
   - Khi đăng nhập vào tài khoản OpenAI đã bị xóa hoặc vô hiệu hóa, trang trả về `account_deactivated` ("Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa") và dừng lại, không redirect về `localhost:1455`.
   - Nếu script chỉ poll callback server sẽ bị treo 120s vô ích. Bắt buộc kiểm tra `account_deactivated` hoặc `vô hiệu hóa` trên DOM trong `check_and_handle_login` để ngắt sớm (fail-fast), dọn dẹp browser và báo cáo lỗi ngay lập tức.
