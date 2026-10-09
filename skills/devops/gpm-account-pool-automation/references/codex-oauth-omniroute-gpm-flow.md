# Codex OAuth Migration to OmniRoute (:20129) via GPM Profiles

## 1. Bối Cảnh & Kiến Trúc
- **9Router (:20128) -> OmniRoute (:20129):** Toàn bộ các kết nối Codex (ChatGPT Plus OAuth) được di chuyển sang quản lý tập trung trên OmniRoute, gán proxy 1:1 theo port Mobi tương ứng.
- **Cơ chế OAuth Codex của OmniRoute:**
  1. Gọi `GET http://localhost:20129/api/oauth/codex/start-callback-server`:
     - OmniRoute mở HTTP server lắng nghe callback tại cổng `1455` (`/auth/callback`).
     - Sinh `authUrl` chuẩn PKCE: `https://auth.openai.com/oauth/authorize?response_type=code&client_id=app_EMoamEEZ73f0CkXaXp7hrann&redirect_uri=http://localhost:1455/auth/callback&scope=...&prompt=login`.
     - Cờ `prompt=login` là bắt buộc để ngăn Auth0/OpenAI gộp session và tráo token giữa các tài khoản khác nhau trên cùng thiết bị.
  2. Polling kết quả qua `POST http://localhost:20129/api/oauth/codex/poll-callback`:
     - Trả về `{ success: true, connection: { id: "...", provider: "codex", email: "..." } }`.
  3. Gán proxy 1:1 bảo toàn trust:
     - Gọi `PUT http://localhost:20129/api/settings/proxies/assignments` với body:
       `{ "scope": "account", "scopeId": connection.id, "proxyId": proxy_registry_id }`.

---

## 2. Mapping Chuẩn Giữa 9Router Accounts & Profile GPM

| STT | Tài Khoản Codex (9Router) | Profile GPM (Group 1) | Thư Mục Profile (`ProfilePath`) | Proxy Port | OmniRoute Proxy ID |
|:---:|---|---|---|:---:|---|
| 1 | `bevels.vanity8s@icloud.com` | **Profile 08** (`08 - minhan2745`) | `8_vuchy` | 5108 | `77c6d61b-d012-4bcc-bd02-72ec4747b84f` |
| 2 | `dishes.66-panic@icloud.com` *(DEACTIVATED)* | **Profile 02** (`02 - luuhuong28022000`) | `2_r7clp` | 5102 | `e6b75277-c113-4581-9008-f71245e94885` |
| 3 | `98.duper-comb@icloud.com` | **Profile 41** (`41 - marcusephillips52sns`) | `10_p5cej` | 5103 | `ad030a88-e465-48eb-a25f-65571e407d2d` |
| 4 | `bulbous_elector_3m@icloud.com` | **Profile 05** (`05 - toloan12091999`) | `5_vqxmk` | 5105 | `6765914c-44af-4427-bbf1-f03b6373e616` |
| 5 | `quocthanhthao.962@outlook.com` | **Profile 09** (`09 - lelinh09111997`) | `9_bk115` | 5111 | `93ffc9bf-6376-47df-ab66-a465afd8136a` |
| 6 | `coaster.leafed-5x+5diuz@icloud.com` | **Profile 04** (`04 - dinhlan24072000`) | `4_hmmy5` | 5104 | `26f478c1-2b94-407b-984c-c7f87e1f7a66` |

*Ghi chú:* Toàn bộ các profile trên đều đã được lưu tài khoản và mật khẩu trực tiếp trong SQLite `Default/Login Data` của Chromium profile.

---

## 3. Pitfalls & Giải Pháp Đột Phá

### A. GPM API v3 Thiếu `profile_path` Trong Response `start` (Root Cause Timeout)
- **Hiện tượng:** Khi gọi `GET /api/v3/profiles/start/{id}`, API trả về `{"success": true, "data": {"remote_debugging_address": "...", "process_id": ...}}` nhưng **HOÀN TOÀN KHÔNG CÓ** trường `profile_path`.
- **Hậu quả:** Nếu script dựa vào `res_data.get("profile_path")` để đọc file `Login Data`, biến sẽ nhận giá trị `None` $\rightarrow$ bỏ qua bước giải mã mật khẩu $\rightarrow$ browser treo lại ở ô password và timeout.
- **Giải pháp:** Bắt buộc gán trước mapping `profile_path` trong cấu hình hoặc truy vấn từ SQLite `profile_data.db` (`SELECT ProfilePath FROM Profiles WHERE Id=?`) trước khi gọi hàm start.

### B. Dual-Capture & Forward Callback Loopback Qua Proxy 4G Farm
- **Vấn đề:** GPM profile chạy với proxy 4G ngoài (`test.taadaa.click:51XX`). Khi OpenAI redirect về `http://localhost:1455/auth/callback?code=...`, proxy server ở xa không thể định tuyến loopback về máy host cục bộ (gây lỗi `ERR_CONNECTION_REFUSED` trên browser).
- **Giải pháp Dual-Capture:**
  1. Hook `page.on("request", on_req)` trong Playwright:
     ```python
     def on_req(req):
         if "1455" in req.url or "code=" in req.url:
             try:
                 local_url = req.url.replace("localhost", "127.0.0.1")
                 requests.get(local_url, timeout=5)
             except Exception:
                 pass
     page.on("request", on_req)
     ```
  2. Đồng thời kiểm tra `page.url`: nếu trang đổi URL chứa `1455` và `code=`, script Python tại host trực tiếp gọi HTTP GET tới `127.0.0.1:1455` để kích hoạt callback trao đổi token tức thì.

### C. Tự Động Trích Xuất & Giải Mã Mật Khẩu Chrome DPAPI + AES-GCM
- **Cơ chế:**
  1. Đọc master key từ `Local State`:
     `enc_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]`
     `master_key = win32crypt.CryptUnprotectData(enc_key, None, None, None, 0)[1]`
  2. Đọc payload từ bản copy của `Default/Login Data`:
     `SELECT password_value FROM logins WHERE username_value LIKE ?`
  3. Giải mã AES-GCM 12-byte IV (`enc_pass[3:15]`) và ciphertext (`enc_pass[15:]`) bằng `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.
  4. Điền password vào `input[type="password"]` và bấm Enter/Submit.

### D. Phát Hiện Sớm Lỗi OpenAI `account_deactivated` Để Fail-Fast
- **Hiện tượng:** Sau khi submit email/password, nếu tài khoản OpenAI bị xóa hoặc vô hiệu hóa, trang web OpenAI hiển thị:
  `Lỗi xác thực: Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa. account_deactivated`
- **Hậu quả:** Trang dừng lại không chuyển tiếp về `localhost:1455`. Script nếu chỉ poll callback endpoint sẽ bị treo vô ích hết 120s timeout.
- **Giải pháp:** Trong hàm `check_and_handle_login`, quét `page.inner_text("body")` tìm các từ khóa `"account_deactivated"`, `"vô hiệu hóa"`, `"deleted or deactivated"`. Nếu phát hiện, in thông báo lỗi và return early để runner hủy phiên, đóng profile GPM và giải phóng tài nguyên tức thì.

### E. Python Toolchain Mismatch Trên Windows Host Khi Chạy Playwright
- **Vấn đề:** Trên host Windows này, lệnh `python3` (Python 3.12 trong Hermes venv) bị lỗi runtime `ModuleNotFoundError: No module named 'greenlet._greenlet'` khi import `playwright.sync_api`.
- **Giải pháp:** Luôn dùng lệnh `python` (Python 3.11 hệ thống) khi chạy các script tự động hóa Playwright CDP (`run_codex_oauth_flow.py`, `run_batch_*.py`) vì Python 3.11 đã cài sẵn và tương thích 100% `playwright`, `pywin32`, `cryptography`.
