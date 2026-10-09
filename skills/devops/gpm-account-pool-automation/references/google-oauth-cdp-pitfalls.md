# Google OAuth via CDP in GPMLogin Profiles - Automation & Pitfalls

## 1. WebSocket / CDP Connection Origin Check (403 Forbidden)
Khi kết nối trực tiếp websocket vào Google Chrome / Chromium từ CDP (`remote_debugging_address`), Chromium có thể từ chối kết nối bắt tay với lỗi:
`WebSocketBadStatusException: Handshake status 403 Forbidden ... Rejected an incoming WebSocket connection from origin`
- **Khắc phục:** Sử dụng flag `suppress_origin=True` trong thư viện `websocket-client`:
  ```python
  ws = websocket.create_connection(ws_url, suppress_origin=True)
  ```

## 2. Trang Google Account Chooser (`accounts.google.com/v3/signin/accountchooser`)
Khi OpenAI / ChatGPT kích hoạt flow Google OAuth, trình duyệt chuyển hướng đến Account Chooser:
- **Hiện tượng treo ở vòng lặp kiểm tra:**
  - Trang Account Chooser trong một số phiên bản Chrome/GPM có thể không populate `document.body.innerText` đầy đủ ngay khi query qua `Runtime.evaluate`, hoặc các thẻ DOM tài khoản bị đóng kín trong custom elements/shadow DOM/rendered dynamic views.
  - Thao tác click DOM selector thông thường:
    ```javascript
    const el = Array.from(document.querySelectorAll('div, li, [role="link"], span')).find(x => x.innerText && x.innerText.includes(email));
    if (el) el.click();
    ```
    có thể không trigger event navigation thực sự nếu Google chặn synthetic click hoặc yêu cầu dispatch `MouseEvent` hoàn chỉnh (mousedown, mouseup, click) hoặc tọa độ thật.
- **Giải pháp tối ưu:**
  1. **Fallback Event Dispatching:** Sử dụng chuỗi sự kiện đầy đủ:
     ```javascript
     function simulateClick(elem) {
         ['mousedown', 'mouseup', 'click'].forEach(eventType => {
             elem.dispatchEvent(new MouseEvent(eventType, { bubbles: true, cancelable: true, view: window }));
         });
     }
     ```
  2. **Kiểm tra URL Redirect & Tab Popup:** Google OAuth có thể mở consent dưới dạng popup hoặc redirect tab hiện tại. Cần kiểm tra liên tục cả `tabs = requests.get(f"http://{remote_addr}/json").json()` để bắt kịp tab mới nảy sinh (OAuth popup window) hoặc redirect callback `auth.openai.com/api/accounts/callback/google`.
  3. **Tự động timeout chuyển profile & Cạm bẫy Timeout 35s trên Proxy 4G Farm:**
     - **Cạm bẫy timeout 35s:** Tuyệt đối không đặt timeout quá ngắn (ví dụ hardcode 35s) cho luồng chờ bắt OAuth Code / Consent redirect trên các profile GPM gắn proxy 4G Farm (Mobi/Viettel xoay vòng hoặc MikroTik).
     - **Nguyên nhân:** Chuỗi redirect OAuth của Google (`accounts.google.com/o/oauth2/auth` -> `CheckCookie` -> `signin/oauth/consent` -> callback OmniRoute) qua proxy di động có độ trễ network từ 40s - 60s. Timeout 35s sẽ ngắt phiên sớm trước khi nhận `code=...`, gây lỗi giả `TIMEOUT_NO_CODE` / `Timeout bắt OAuth code`.
     - **Quy chuẩn:** Bắt buộc đặt timeout OAuth flow tối thiểu từ **120s đến 180s** khi chạy qua proxy farm.
     - **Fallback:** Nếu sau 120s-180s không redirect, ghi log, chụp screenshot debug vào `D:\Taadaa\GPM auto\debug_screenshots\` và chuyển tiếp tài khoản tiếp theo thay vì làm nghẽn toàn bộ batch.

## 3. Lưu Mật Khẩu / Credential Manager trong GPM Profile (Playwright CDP Pitfall)
Khi đăng nhập tài khoản Google/Gmail trên profile GPM tự động, nếu muốn trình duyệt lưu lại mật khẩu vào Trình quản lý mật khẩu của Chrome:
1. **Gỡ cờ chặn của Playwright:**
   - Mặc định Playwright truyền cờ `--disable-save-password-bubble` trong default arguments của Chromium, làm tắt hoàn toàn bong bóng hỏi lưu mật khẩu.
   - Khi khởi chạy context, BẮT BUỘC thêm:
     ```python
     context = p.chromium.launch_persistent_context(
         ...,
         ignore_default_args=["--disable-save-password-bubble"]
     )
     ```
2. **Kích hoạt Password Manager trong Preferences của Profile:**
   - Trước khi launch trình duyệt, cần đảm bảo file `Default/Preferences` trong thư mục profile có:
     ```json
     {
       "credentials_enable_service": true,
       "profile": {
         "password_manager_enabled": true
       }
     }
     ```
3. **Ưu tiên click "Lưu" (Save) trước khi Dismiss:**
   - Trong vòng lặp xử lý các màn hình hậu đăng nhập của Google, nếu xuất hiện prompt web hỏi "Lưu mật khẩu", "Save password", "Duy trì đăng nhập", cần ưu tiên bắt selector nút "Lưu" / "Save" và click trước, tránh click nhầm vào các nút "Để sau", "Hủy", "Not now".
   - **Bẫy cú pháp Playwright Locator:** Không gọi `.count()` trên `.first` (`page.locator(...).first.count()`). Cần kiểm tra `.count()` trên collection locator gốc rồi mới gọi `.first.is_visible()`:
     ```python
     save_btns = page.locator('button:has-text("Lưu"), button:has-text("Save"), button:has-text("Lưu mật khẩu"), button:has-text("Save password")')
     if save_btns.count() > 0 and save_btns.first.is_visible():
         save_btns.first.click()
     ```

## 4. Singbox Port Mapping Pitfall (Dải cổng 20000..21000)
Khi tính toán cổng proxy Singbox từ cấu hình `port` của account:
- **Hiện tượng lỗi:** Cổng Singbox của máy (ví dụ `20005`) bị logic cũ cộng dồn: `20000 + (port - 10000)` $\rightarrow$ biến thành `30005`, gây lỗi `net::ERR_PROXY_CONNECTION_FAILED` hoặc timeout 300s khi tải trang Google.
- **Quy tắc phân giải chuẩn:**
  ```python
  if acc.get("singbox_port"):
      singbox_port = acc["singbox_port"]
  elif port and 20000 <= port < 21000:
      singbox_port = port  # Giữ nguyên cổng nếu đã là dải Singbox 20000+
  elif port == 16002:
      singbox_port = 20000 + mid
  elif port and 5000 < port < 6000:
      singbox_port = 20000 + (port - 5100)
  elif port and 10000 <= port < 11000:
      singbox_port = 20000 + (port - 10000)
  else:
      singbox_port = 20000 + mid
  ```

## 5. Pipeline Runner Script Template & Append OmniRoute Combo
Khi viết hoặc sửa script tự động chạy nạp OAuth đơn lẻ hoặc theo lô cho các máy Farm (như `run_m28_doanthu_auto.py`, `run_m74_phannhu_auto.py`):
- **Import chuẩn từ `run_oauth_s7_pipeline`:**
  - Không import `run_pipeline` từ `run_oauth_s7_pipeline` (hàm này không tồn tại và sẽ gây `ImportError`).
  - Hàm entrypoint chuẩn xử lý từng profile là `process_account(acc)` từ `run_oauth_s7_pipeline.py`.
  - Hàm nạp vào combo OmniRoute pool 3 là `append_connections` từ `append_to_combo_pool3.py`.
- **Cấu trúc runner chuẩn:**
  ```python
  import sys, logging
  sys.path.insert(0, r"D:\Taadaa\GPM auto\scripts")
  from run_oauth_s7_pipeline import process_account
  from append_to_combo_pool3 import append_connections

  acc = {
      "mid": 28,
      "email": "doanthu10051999@gmail.com",
      "password": "...",
      "totp_secret": "...",
      "recovery": "...",
      "serial": "...",
      "port": 19995,
      "singbox_port": 20028,
      "profile": "28 - doanthu10051999@gmail.com - 5134"
  }

  res = process_account(acc)
  conn_id = res.get("conn_id") or res.get("connection_id")
  if res.get("status") in ["SUCCESS", "ALREADY_SUCCESS"] and conn_id:
      append_connections([{"cid": conn_id, "email": acc["email"], "port": acc.get("singbox_port", 20028)}])
  ```
- **Kiểm tra sau khi append combo:**
  - Endpoint kiểm tra combo: `http://127.0.0.1:20129/api/combos`
  - Trường chứa danh sách targets trong response combo JSON là `models` (không phải `targets`), mỗi model item có dạng:
    `{"id": "...", "kind": "model", "model": "antigravity/gemini-3.8-flash-tiered", "providerId": "antigravity", "connectionId": "<cid>", "weight": 0, "label": "pool-X"}`

## 6. Evidence Gate & Screenshot Nghiệm Thu Job GPM (User Correction 2026-09-14)
- **Đúng môi trường:** Khi báo cáo kết quả kiểm tra hoặc sửa lỗi cho các watchdog/job của GPMLogin (ví dụ: `post-evening-gpm-login-watchdog`, `batch_dual_oauth`, `run_oauth_s7_pipeline`):
  - BẰNG CHỨNG ẢNH BẮT BUỘC phải là ảnh màn hình Chromium/GPM profile (lỗi timeout, reCAPTCHA, Google checkpoint...) được chụp vào thư mục `D:\Taadaa\GPM auto\debug_screenshots\`.
  - CẤM TUYỆT ĐỐI gửi ảnh chụp màn hình máy Samsung S7 qua ADB để "trả bài" cho job GPM.
- **Tên file screenshot debug chuẩn:** `D:\Taadaa\GPM auto\debug_screenshots\oauth_<email>_timeout_<timestamp>.png` hoặc `oauth_<email>_challenge_checkpoint_*.png`.

## 7. Subprocess Output Stream & Concurrency Guard trong Watchdog GPM
- **Subprocess capture `stderr`:** Script lõi `run_oauth_s7_pipeline.py` dùng `logging.getLogger()` (`logger.info`) ghi toàn bộ ra `sys.stderr`. Luồng `sys.stdout` hoàn toàn rỗng `""`.
  - Nếu script watchdog kiểm tra `"SUCCESS" in proc.stdout` sẽ 100% đánh giá sai thành `FAIL`.
  - BẮT BUỘC gộp: `combined = (proc.stdout or "") + "\n" + (proc.stderr or "")` và kiểm tra đồng thời cả `SUCCESS` và `ALREADY_SUCCESS`.
- **Giới hạn Concurrency:** GPM + OAuth bắt buộc tối đa `MAX_WORKERS = 2`, stagger delay >= 5s. Tuyệt đối không nâng lên 5-10 workers vì sẽ gây nghẽn proxy Sing-box/MobiProxy, giật lag taskbar Windows và làm timeout đồng loạt toàn bộ profile.

## 8. SỰ CỐ & CẤM TUYỆT ĐỐI: Bypass GPM API Mở Profile Bằng Playwright launch_persistent_context
- **SỰ CỐ NGHIÊM TRỌNG (Case GPM-OAUTH-DIRECT-PLAYWRIGHT-BREAKER-01 - 16/09/2026):**
  - Trước đây từng có suy nghĩ "chữa cháy" khi GPM API lỗi bằng cách bypass GPM Local API, dùng `pw.chromium.launch_persistent_context` mở trực tiếp thư mục `user_data_dir` của profile.
  - **HẬU QUẢ TAI HẠI:** Playwright thô không kích hoạt được gpmdriver và engine anti-detect (WebGL, Canvas, Audio, Navigator spoofing, native DLL hooks của GPMLogin). Khi click Google OAuth ("Continue with Google" vào OpenAI/ChatGPT), Google lập tức phát hiện Automation và kích hoạt rào chắn `accounts.google.com/v3/signin/rejected` ("Trình duyệt hoặc ứng dụng này có thể không an toàn"), đe dọa trực tiếp dàn tài khoản Gmail!
- **LỆNH CẤM BẤT BIẾN (STRICT INVARIANT):**
  - **CẤM TUYỆT ĐỐI** tự ý dùng `pw.chromium.launch_persistent_context` hoặc `webdriver.Chrome` mở trực tiếp thư mục `user_data_dir` của profile GPM khi chạy OAuth Google.
  - Mọi thao tác OAuth Google / ChatGPT **BẮT BUỘC** phải đi qua GPM Local API: `start_gpm_profile` -> lấy port CDP -> `connect_over_cdp`. Nếu API GPM lỗi: DỪNG LẠI VÀ BÁO CÁO NGƯỜI DÙNG, CẤM TỰ CHẾ.

## 9. Nguyên Nhân Thật Sự Của Lỗi GPM API `Yêu cầu cập trình duyệt [Chromium] [142]`
- **Nguyên nhân gốc rễ:** Khi mở ứng dụng GPMLogin, app thường hiển thị modal popup **"Big Update"** (thông báo cập nhật version, database fingerprint 411, v.v.). Khi modal này đang hiển thị, GPMLogin khóa toàn bộ backend API v3 và trả về mã lỗi giả: `Yêu cầu cập trình duyệt [Chromium] [142]` để ép người dùng tương tác trên UI.
- **Cách xử lý chuẩn xác:**
  1. **Tương tác UI:** Bấm nút đỏ **"Đóng thông báo"** trên cửa sổ GPMLogin (hoặc gửi Win32 click vào tọa độ nút).
  2. **Chặn vĩnh viễn không cho popup hiện lại:** Cập nhật file `do_not_show_what_news` trong thư mục GPMLogin lên phiên bản hiện tại (ví dụ: `4.3.6-stable`):
     ```python
     with open(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\do_not_show_what_news", "w") as f:
         f.write("4.3.6-stable")
     ```
  Ngay khi đóng modal, endpoint `/api/v3/profiles/start/{id}` sẽ trả về `success: True`, `remote_debugging_address` và `gpmdriver.exe` hoạt động 100% bình thường.

## 10. Circuit Breaker Bắt Buộc Trong Các Batch Runner GPM
- **Nguyên tắc phân tầng lỗi:**
  - **Lỗi cấu trúc / Hạ tầng (`fatal_structural = True`):** GPM API sập, yêu cầu cập nhật trình duyệt, CDP `ECONNREFUSED` / port closed.
    - Duy trì bộ đếm `consecutive_structural_fails`. Nếu liên tiếp **>= 3 lần**, kích hoạt Circuit Breaker: set `SHUTDOWN_EVENT`, hủy toàn bộ queued futures, gọi hàm dọn dẹp khẩn cấp `force_emergency_cleanup()` để đóng/kill toàn bộ profile đang chạy, và thoát ngay lập tức (`os._exit(1)`).
  - **Lỗi nghiệp vụ tài khoản (`fatal_structural = False`):** Captcha, Cloudflare, timeout chọn tài khoản, yêu cầu password.
    - Bỏ qua tài khoản đó, **reset bộ đếm lỗi cấu trúc về 0** (`consecutive_structural_fails = 0`) và tiếp tục xử lý profile kế tiếp.

## 11. Proxy Format: Lỗi Thiếu Auth Khiến GPM Báo "Không thể kết nối tới proxy"
- Khi thêm hoặc đồng bộ proxy MikroTik (dải cổng `10001` - `10032`) vào GPM:
  - Nếu trường `Proxy` trong `JsonData` chỉ ghi `mirotik1.taadaa.click:10006` (thiếu username/password), GPM sẽ thử kết nối và báo lỗi `Không thể kết nối tới proxy` ngay khi gọi start profile.
  - BẮT BUỘC chuỗi proxy phải có đầy đủ thông tin xác thực: `mirotik1.taadaa.click:10006:admin@1:admin@1`.

## 12. Chunked Cookie Session-Token (`__Secure-next-auth.session-token`)
- Đối với tài khoản ChatGPT Web có payload session lớn, NextAuth chia cookie thành các chunk `.0`, `.1`:
  - Khi trích xuất cookie từ CDP context, thu thập tất cả cookie có tên chứa `session-token`.
  - Sắp xếp theo thứ tự key (`.0`, `.1`) và ghép thành chuỗi định dạng: `k1=v1; k2=v2` để nạp vào OmniRoute:
    ```python
    chunks = {ck['name']: ck['value'] for ck in context.cookies() if 'session-token' in (ck.get('name') or '') and ck.get('value')}
    if chunks:
        sorted_chunks = sorted(chunks.items(), key=lambda x: x[0])
        session_token = "; ".join(f"{k}={v}" for k, v in sorted_chunks) if len(sorted_chunks) > 1 else sorted_chunks[0][1]
    ```

## 13. Tự Động Hồi Sinh Session ChatGPT Web Với 2FA TOTP & Polling CDP (2026-09-18)
- **Tự động hóa toàn diện với 2FA TOTP:**
  - Khi tài khoản ChatGPT Web hết hạn session (`session expired`), click "Tiếp tục với Google" trên profile GPM thường kích hoạt challenge Google OAuth (`/signin/challenge/totp` hoặc yêu cầu password).
  - Tra cứu Password + 2FA Secret Key từ nguồn `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (sheet `Gmail Accounts`).
  - Dùng `pyotp.TOTP(totp_secret).now()` để sinh mã 6 số tự động điền vào `#totpPin` hoặc `input[type="tel"]`, sau đó click `#totpNext` thay vì dừng lại chờ thao tác tay.
- **Quy tắc Polling CDP khi Start Profile:**
  - Sau khi gọi API `/api/v3/profiles/start/{id}`, CDP port cần 1–3s để mở socket.
  - CẤM gọi `connect_over_cdp` ngay lập tức kẻo dính `ECONNREFUSED`. BẮT BUỘC có hàm `wait_for_cdp_ready` ping `http://{cdp_addr}/json` trước khi kết nối Playwright.
- **Kỷ luật giao tiếp Coordinator:**
  - Khi người dùng yêu cầu thực thi hoặc sửa lỗi liên quan đến batch/tài khoản, tuân thủ nguyên tắc **Silent Execution & Final Report Only**: không gửi tin nhắn giải thích dở dang giữa các bước, chỉ báo cáo duy nhất 1 lần khi toàn bộ quy trình hoàn tất.

## 14. Quy Trình Tự Động Hồi Sinh Antigravity OAuth Qua OmniRoute & GPM (2026-09-19)
- **Cơ chế OAuth Antigravity trên OmniRoute (:20129):**
  - **Authorize Flow:** Gửi GET tới `http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri={encoded_callback}`. Response trả về JSON chứa đầy đủ: `{authUrl, state, codeVerifier, codeChallenge, redirectUri, flowType, callbackPath, callbackHost}`.
  - **Playwright CDP Navigation:** Mở GPM profile qua Local API (`/api/v3/profiles/start/{pid}`), kết nối Playwright CDP, điều hướng tới `authUrl`. Đóng profile sau khi hoàn tất qua `GET /api/v3/profiles/close/{pid}`.
  - **Tự động xử lý Account Chooser & Consent:**
    - Click chọn email: `div[data-email="{email.lower()}"]`.
    - Click đồng ý quyền: `button:has-text("Cho phép")`, `button:has-text("Tiếp tục")`, `button:has-text("Allow")`, `button:has-text("Continue")`, `#submit_approve_access`.
  - **Intercept callback code & Exchange:**
    - Lắng nghe event request/response và URL query chứa `/callback` và `code=`.
    - Trích xuất `code` từ query params và gửi POST tới `http://127.0.0.1:20129/api/oauth/antigravity/exchange`.
    - **Schema Payload Exchange chuẩn (Bắt buộc đủ 4 trường):**
      ```json
      {
        "code": "<captured_code>",
        "redirectUri": "http://127.0.0.1:20129/callback",
        "codeVerifier": "<codeVerifier từ authorize response>",
        "state": "<state từ authorize response>"
      }
      ```
    - *Lưu ý ngân sách tool call:* Khi điều phối task này trong session giới hạn turns (<= 8 calls), không probe thăm dò tản mát. Chạy trực tiếp 1 runner script Python hoàn chỉnh gồm đầy đủ start profile -> cdp connect -> check session -> authorize -> listen callback -> exchange -> close profile trong khối `finally` để tiết kiệm tối đa turns.
- **OmniRoute Storage Schema & Đồng bộ Database:**
  - Database: `C:\Users\Kibe\.omniroute\storage.sqlite`.
  - Bảng lưu trữ kết nối là `provider_connections` (LƯU Ý: Không phải bảng `connections`).
  - Sau khi exchange thành công, cập nhật trạng thái kết nối:
    `UPDATE provider_connections SET is_active = 1, test_status = 'active', last_error = NULL WHERE id = ?`.
- **Tái sử dụng module sẵn có:**
  - Logic chuẩn được đóng gói sẵn tại `C:\Users\Kibe\AppData\Local\hermes\scripts\cron_chatgpt_web_pool_watchdog.py` với các hàm `perform_antigravity_oauth(cdp_addr, email)` và `refresh_antigravity_account_via_gpm(pid, email)`.

## 15. Cạm Bẫy Đăng Nhập ChatGPT Web Qua Google OAuth (2026-09-19)
- **Bẫy Vòng Lặp Google Sign-in Identifier:**
  - Khi Google mở trang `accounts.google.com/v3/signin/identifier`, nếu script chỉ tìm và click các nút chung chung ("Tiếp theo", "Tiếp tục", "Next") mà không kiểm tra điền `#identifierId`, Google sẽ không chuyển trang và script bị kẹt trong vòng lặp click nút rỗng.
  - **Quy tắc bắt buộc:** Luôn kiểm tra selector `input[type="email"], #identifierId, input[name="identifier"]`. Nếu selector hiển thị, phải thực hiện `fill(email)` và chờ 1s trước khi click `#identifierNext` hoặc nhấn `Enter`.
- **Cấu Trúc Bảng Excel Credentials `gmail_clean_v2.xlsx`:**
  - Đường dẫn nguồn: `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (sheet `Gmail Accounts`).
  - Thứ tự cột chuẩn: `Col 0: ID/STT`, `Col 1: Email`, `Col 2: Password`, `Col 3: 2FA TOTP Secret (32 ký tự uppercase)`, `Col 4: Recovery Email`, `Col 5: Ngày sinh (DOB)`.
  - Không dò password bằng chuỗi con cố định (ví dụ `@ks`) vì có thể bị sai do chữ hoa/thường (`@Ks`).
- **Tránh Lỗi "Target page, context or browser has been closed" khi OpenAI Redirect:**
  - Khi luồng OAuth hoàn tất từ Google sang OpenAI (`auth.openai.com/about-you` hoặc `chatgpt.com`), trình duyệt thường kích hoạt redirect nhiều chặng hoặc mở/đóng tab con.
  - Gọi `page.wait_for_timeout()` trực tiếp trên đối tượng `page` cũ rất dễ văng ngoại lệ `Target page, context or browser has been closed`.
  - **Cách xử lý:** Luôn lấy page mới nhất qua `page = context.pages[-1] if context.pages else context.new_page()` ở mỗi đầu bước lặp, và bọc các thao tác kiểm tra locator trong khối `try/except Exception: pass`.

## 16. Phân Biệt "Độ Trust Tài Khoản" vs "2FA Secret" Khi Login Google Trên PC & Cơ Chế Điều Tra Chromium History (User Correction 2026-09-20)
- **Sai lầm nhận định:** Tuyệt đối không quy kết máy móc "tài khoản bắt buộc phải có 2FA mới đăng nhập được trên GPM".
  - Thực tế: Nhiều tài khoản Google hoàn toàn KHÔNG CÓ 2FA (cột 2FA trên Excel để trống) nhưng có **Độ Trust (Account Trust Score)** cao, IP sạch/ổn định $\rightarrow$ Google cho đăng nhập thẳng 100% chỉ với Email + Password mà không hề bật bất kỳ thử thách nào (không đòi 2FA, không hỏi SMS, không đòi xác nhận S7).
  - Ngược lại, các tài khoản bị Google đánh giá rủi ro (độ trust thấp, IP proxy bị cờ, hoặc đăng nhập bất thường trên thiết bị lạ) $\rightarrow$ Google kích hoạt Risk Engine chặn ngay bằng Hard Phone Checkpoint (`challenge/iap` đòi số điện thoại mới).
- **Kỹ thuật điều tra O(1) qua Chromium `Default/History`:**
  - Để biết chính xác từng giây một profile Chromium đã điều hướng qua những URL nào, đã đăng nhập thành công hay kẹt ở bước nào mà không cần đoán mò:
    Truy vấn trực tiếp file SQLite `Default/History` trong thư mục profile:
    ```python
    import sqlite3, datetime
    conn = sqlite3.connect(rf"{prof_dir}\Default\History")
    cur = conn.cursor()
    cur.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time ASC")
    for r in cur.fetchall():
        dt = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=r[2])
        print(dt, r[0], r[1])
    ```
  - Nếu thấy URL `CheckCookie` -> `SetSID` -> `signin/oauth/consent`: Tài khoản ĐÃ đăng nhập Google thành công, session cookie đã lưu trên đĩa.
  - Nếu thấy kẹt ở `firstparty/nativeapp`: Đã đăng nhập nhưng kẹt ở bước cấp quyền OAuth (Consent screen) do timeout hoặc không click kịp nút "Cho phép" / "Tiếp tục".
- **Hậu quả của `MAX_WORKERS` cao (ví dụ = 5):**
  - Bung 5 Playwright context chạy song song qua proxy nội bộ gây nghẽn băng thông, giật lag tiến trình, khiến các tài khoản dù đăng nhập thành công cũng bị timeout 180s ở bước bắt redirect OAuth.
  - Giữ vững quy tắc: Tối đa `MAX_WORKERS = 1` hoặc `2`, stagger delay >= 5s.

## 17. Chẩn Đoán Google Session Trong GPM Profile & Playwright Async Bypass Greenlet (2026-09-20)
- **Bẫy Playwright `sync_api` văng `ModuleNotFoundError: No module named 'greenlet._greenlet'` trên Windows:**
  - Trên Windows virtualenv, gói `greenlet` đôi khi bị lỗi C-extension (`_greenlet.pyd`), khiến `from playwright.sync_api import sync_playwright` bị crash ngay từ lúc import.
  - **Khắc phục:** Luôn ưu tiên dùng `playwright.async_api` (`from playwright.async_api import async_playwright` kết hợp `asyncio.run()`). Playwright Async chạy trên loop native của Python/asyncio và hoàn toàn không phụ thuộc vào `greenlet`.
- **Dấu hiệu nhận biết Session Google Đã Chết (Dead / Logged Out) trên GPM Profile:**
  - Tuyệt đối không chỉ kiểm tra HTTP status code 200 (vì các trang landing page của Google đều trả về 200):
    1. **Khi vào `https://myaccount.google.com/`:**
       - **Session Sống:** URL giữ nguyên domain `myaccount.google.com` (ví dụ `https://myaccount.google.com/?pli=1`), title chứa tên chủ tài khoản hoặc mục cài đặt, body hiển thị avatar/email.
       - **Session Chết:** Google redirect về `https://www.google.com/account/about/?hl=vi` (Landing page "Google Tài khoản - Đăng nhập vào Tài khoản Google của bạn và khai thác tối đa...").
    2. **Khi vào `https://mail.google.com/`:**
       - **Session Sống:** URL chuyển vào inbox `https://mail.google.com/mail/u/0/#inbox`.
       - **Session Chết:** Google redirect về `https://workspace.google.com/intl/vi/gmail/` (Landing page tiếp thị có nút *"Đăng nhập"* và *"Tạo tài khoản"*).
    3. **Khi vào Antigravity OAuth URL (`https://accounts.google.com/o/oauth2/v2/auth?...`):**
       - **Session Sống:** Chuyển vào Account Chooser (`accounts.google.com/v3/signin/accountchooser`) hoặc thẳng trang Consent (`signin/oauth/consent`).
       - **Session Chết (Rỗng cookie hoàn toàn):** Chuyển hướng ngay sang `https://accounts.google.com/v3/signin/identifier` yêu cầu nhập lại Email từ đầu (`Email hoặc số điện thoại`, nút `Tiếp theo`). Trường hợp này không thể tự động lấy token OAuth nếu không có luồng đăng nhập lại Email + Mật khẩu + 2FA.

## 18. Cạm Bẫy Lọc `sys.path` Loại Trừ Thư Mục `hermes-agent` Vô Tình Xóa Venv Site-Packages (2026-09-20)
- **Hiện tượng lỗi:** Script chạy độc lập văng ngoại lệ `ModuleNotFoundError: No module named 'requests'` hoặc `playwright` dù đã cài đầy đủ package trong venv hiện hành.
- **Nguyên nhân gốc rễ:** Script chứa dòng code:
  ```python
  sys.path = [p for p in sys.path if "hermes-agent" not in p]
  ```
  Nhằm mục đích tránh import xung đột các module trong repo `hermes-agent`. Tuy nhiên, nếu virtual environment nằm trong thư mục có chứa chuỗi `hermes-agent` (ví dụ `C:\...\hermes-agent\.venv\lib\site-packages`), phép kiểm tra chuỗi con `"hermes-agent" in p` sẽ lọc bỏ luôn cả thư mục `site-packages` của venv.
- **Quy tắc khắc phục:**
  1. Chỉ lọc đường dẫn kết thúc bằng đúng thư mục gốc của agent:
     ```python
     sys.path = [p for p in sys.path if not p.rstrip("/\\").endswith("hermes-agent")]
     ```
  2. Hoặc xóa bỏ hoàn toàn dòng lọc `sys.path` này khi chạy bằng Python interpreter trực tiếp của venv.

## 19. Kỷ Luật Ngân Sách Tool Call & Tránh Treo MSYS `ls -la` Trên Ổ Đĩa Windows (2026-09-21)
- **Cạm bẫy cạn kiệt ngân sách Tool Call do thăm dò tản mát:**
  - Khi người dùng giao task tạo profile GPM và test đăng nhập với ngân sách tool call nghiêm ngặt (ví dụ: `Budget <= 15 tool calls`):
  - Tuyệt đối KHÔNG chia nhỏ thành các turn tương tác tuần tự (turn 1: search files, turn 2: curl GPM, turn 3: create profile, turn 4: start, turn 5: chạy playwright...). Cách làm này tiêu tốn 8-12 lượt gọi trước khi kịp thực thi login thực tế và dễ bị chạm trần tool iteration limit.
  - **Quy chuẩn thực thi một phát ăn ngay (One-shot Runner Script):**
    - Viết một script Python hoàn chỉnh (hoặc gọi module có sẵn như `D:\Taadaa\GPM auto\scripts\test_clean_login_m1_m2.py`) tích hợp trọn gói:
      1. Kiểm tra profile tồn tại qua `GET /api/v3/profiles`.
      2. Tạo profile mới nếu chưa có (`POST /api/v3/profiles/create`).
      3. Start profile (`GET /api/v3/profiles/start/{id}`) và kết nối Playwright CDP.
      4. Xử lý flow đăng nhập Google (Email -> Captcha -> Password -> 2FA / Challenge).
      5. Chụp ảnh màn hình nghiệm thu lưu vào `D:\Taadaa\runtime\kibe\*.png`.
      6. Đóng profile trong khối `finally` (`GET /api/v3/profiles/close/{id}`).
    - Chạy script duy nhất qua `terminal` trong 1 turn, sau đó trả báo cáo kết quả kèm bằng chứng ảnh.
- **Cạm bẫy MSYS shell treo khi duyệt thư mục ổ đĩa Windows:**
  - Lệnh `ls -la /d/Taadaa` hoặc `ls -la D:/` trong Git-Bash/MSYS thường xuyên bị treo và timeout 180s do cơ chế mapping quyền NTFS/ACL của MSYS trên ổ đĩa có nhiều file/folder.
  - **Khắc phục:** Luôn sử dụng Python một dòng `python -c "import os; print(os.listdir('D:/Taadaa'))"` hoặc `search_files(target='files')` có filter cụ thể, hoàn thành chỉ trong < 1 giây mà không gây lag/hang terminal.

## 20. Cạm Bẫy `wait_until="networkidle"` Treo Khi Vào Google Login & Phân Biệt "Không Tìm Thấy Tài Khoản" vs "Phone Checkpoint" (2026-09-21)
- **Bẫy `wait_until="networkidle"` trên Google ServiceLogin:**
  - Khi dùng Playwright điều hướng `https://accounts.google.com/ServiceLogin` hoặc OAuth URL với `wait_until="networkidle"`, Google liên tục duy trì các kết nối telemetry nền (gRPC / batchexecute / background beacons / client logs), khiến networkidle không bao giờ đạt được và gây `TimeoutError: Timeout 60000ms exceeded`.
  - **Quy tắc bắt buộc:** Luôn đặt `wait_until="domcontentloaded"` kèm `timeout=25000` ms khi `page.goto()`. DOM sẵn sàng ngay chỉ trong ~1s, sau đó dùng `locator.wait_for(state="visible")` cho selector ô nhập email (`input[type="email"], #identifierId`).
- **Tránh Nhầm Lẫn Bằng Đoạn Text Phone Trên Trang Google Login:**
  - Trang đăng nhập của Google hiển thị nhãn `Email hoặc số điện thoại` ("Email or phone") ngay tại ô nhập tài khoản.
  - Nếu kiểm tra `is_phone_screen` chỉ bằng chuỗi con `"phone"` hoặc `"số điện thoại"` trong `body.inner_text()`, script sẽ nhận diện sai thành bị dính Phone Challenge ngay cả khi tài khoản bị chết hoặc không tồn tại.
  - **Cách nhận diện chuẩn xác theo thứ tự ưu tiên:**
    1. `ACCOUNT_NOT_FOUND`: Kiểm tra `body_text` chứa `"không tìm thấy tài khoản này"` hoặc `"couldn't find your google account"`.
    2. `ACCOUNT_DISABLED`: Chứa `"account disabled"` hoặc `"tài khoản bị vô hiệu hóa"`.
    3. `WRONG_PASSWORD`: Chứa `"wrong password"` hoặc `"sai mật khẩu"`.
    4. `PHONE_CHALLENGE`: BẮT BUỘC kiểm tra có input số điện thoại thực sự trên DOM (`input[type="tel"]:visible`, `input#phoneNumber:visible`) HOẶC có thông báo thử thách xác minh danh tính (`"xác minh danh tính"`, `"verify it's you"` sau khi đã qua bước nhập password).

## 21. Cạm Bẫy Vòng Lặp Điền Mật Khẩu Vô Tận Khi Sai Password (Infinite Password Re-entry Loop) (2026-09-21)
- **Hiện tượng lỗi:**
  - Khi chạy pipeline login GPM (`run_oauth_s7_pipeline.py`), script liên tục lặp lại log `[Mxx] Điền mật khẩu cho <email>...` mỗi 4-5 giây đến khi hết 180s-300s timeout và trả về kết quả giả `FAILED (TIMEOUT)`.
- **Nguyên nhân gốc rễ:**
  - Khi mật khẩu trong database/sheet không đúng, Google hiển thị thông báo lỗi ngay dưới ô nhập:
    `"Mật khẩu không chính xác. Hãy thử lại hoặc nhấp vào \"Thử cách khác\" để xem các lựa chọn khác."` (hoặc `"Wrong password. Try again or click Forgot password to reset it."`).
  - Tuy nhiên, ô input `input[type="password"]` hoặc `input[name="Passwd"]` **vẫn tiếp tục hiển thị trên DOM** (`is_visible() == True`).
  - Logic đăng nhập chỉ kiểm tra `if pw_inp.count() > 0 and pw_inp.is_visible() and password:` mà không kiểm tra thông báo lỗi sai mật khẩu hoặc không giới hạn số lần nhập (`pw_attempts >= 1` hoặc `2`).
  - Hậu quả: Script gửi đi gửi lại cùng 1 mật khẩu sai hàng chục lần, vừa lãng phí thời gian timeout vừa làm Google đánh dấu hành vi brute-force có thể dẫn đến khóa tài khoản tạm thời!
- **Quy tắc khắc phục chuẩn xác:**
  1. **Bắt sớm lỗi Sai Mật Khẩu (Fast-fail on Wrong Password):**
     Trước khi re-enter password, kiểm tra thông báo lỗi từ Google:
     ```python
     # Kiểm tra container lỗi của Google Sign-in
     err_el = page.locator('div[aria-live="assertive"], span:has-text("không chính xác"), span:has-text("Wrong password"), div:has-text("Mật khẩu không chính xác")')
     if err_el.count() > 0 and any(err_el.nth(i).is_visible() for i in range(err_el.count())):
         logger.error(f"[M{mid:02d}] ❌ Mật khẩu không chính xác cho {email}! Dừng pipeline tránh brute-force.")
         # Chụp ảnh bằng chứng và return ngay lập tức với mã WRONG_PASSWORD
         return {"status": "FAILED", "reason": "WRONG_PASSWORD"}
     ```
  2. **Bộ đếm giới hạn thử mật khẩu (`max_pw_attempts = 1`):**
     Nếu cùng 1 mật khẩu đã được điền và nhấn Tiếp theo nhưng trang vẫn giữ nguyên ở ô password sau 5s, không điền lại mà kiểm tra ngay thông báo lỗi hoặc thoát với `WRONG_PASSWORD`.
  3. **Chẩn đoán nhanh qua WinRT OCR:**
     Khi gặp file debug screenshot timeout (`oauth_<email>_timeout_<timestamp>.png`), chạy ngay script WinRT OCR để đọc text trên ảnh mà không cần mở GUI:
     ```bash
     python C:\Users\Kibe\AppData\Local\hermes\skills\productivity\windows-native-ocr\scripts\winrt_ocr.py "D:\Taadaa\GPM auto\debug_screenshots\<screenshot>.png"
     ```
     Nếu OCR ra cụm `"khong Chinh xac"` hoặc `"Wrong password"`, xác định ngay 100% nguyên nhân do sai mật khẩu trong DB.

## 22. Vượt reCAPTCHA Enterprise Bằng Audio Solver Tự Động Trong GPM Profile (User Correction 2026-09-24)
- **Sai lầm nhận định:** Khi luồng Google OAuth hoặc đăng nhập trên GPM bị bật màn hình `Verify it's you: Confirm you're not a robot` (Google reCAPTCHA Enterprise / v2 challenge), tuyệt đối **CẤM** vội vã kết luận là bế tắc, timeout hoặc abort bỏ cuộc!
- **Hệ thống ĐÃ CÓ SẴN module Audio Solver hoàn chỉnh:**
  - Codebase đã có sẵn hàm `solve_recaptcha_audio(page)` được kiểm chứng thực tế trong `D:\Taadaa\GPM auto\scripts\test_m20_recaptcha.py` và `run_add_2fa_remaining.py`.
  - Môi trường Windows host đã cấu hình đầy đủ:
    + Binary FFmpeg: `C:\Users\Kibe\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe`.
    + Thư viện Python: `pydub` và `speech_recognition` (SpeechRecognition) sử dụng Google Speech API miễn phí (`r.recognize_google(audio_data)`).
- **Quy trình giải reCAPTCHA Audio 7 bước chuẩn:**
  1. **Tìm iframe reCAPTCHA:** Quét `page.frames` tìm `anchor_frame` (chứa `enterprise/anchor` hoặc `api2/anchor`) và `bframe` (chứa `enterprise/bframe` hoặc `api2/bframe`).
  2. **Click checkbox anchor:** Click `#recaptcha-anchor` hoặc `.recaptcha-checkbox`. Nếu `get_attribute("aria-checked") == "true"` (dấu tích xanh tự động), trả về `True` ngay mà không cần giải.
  3. **Mở Audio Challenge:** Trong `bframe`, click nút `#recaptcha-audio-button` (hoặc `button[title*='audio']`, `button[title*='âm thanh']`).
  4. **Tải file âm thanh:** Lấy thuộc tính `href` hoặc `src` từ `#audio-source` hoặc `.rc-audiochallenge-tdownload-link`. Tải file MP3 về thư mục tạm `C:\Users\Kibe\AppData\Local\hermes\cache\recaptcha_<ts>.mp3`.
  5. **Chuyển đổi MP3 sang WAV:** Dùng `sound = pydub.AudioSegment.from_mp3(mp3_path); sound.export(wav_path, format="wav")`.
  6. **Nhận diện giọng nói:** Dùng `r = sr.Recognizer(); with sr.AudioFile(wav_path) as source: text = r.recognize_google(r.record(source))`. Xóa ngay 2 file tạm sau khi nhận diện.
  7. **Submit đáp án:** Điền `text` vào `bframe.locator("#audio-response, input[name='audio-response']")`, sau đó click `#recaptcha-verify-button` (hoặc nút `Verify` / `Xác minh`). Chờ 3-4s để hoàn tất xác thực.

## 23. Bulletproof Cleanup Tránh Rò Rỉ Tiến Trình Chromium GPM (Process Leak Guard)
- **Hiện tượng lỗi:** Gọi API GPM `/profiles/close/{pid}` hoặc `/profiles/stop/{pid}` đôi khi chỉ ngắt kết nối API nhưng để lại hàng chục tiến trình `chrome.exe` con (renderer, gpu-process, crashpad) chạy ngầm bám Taskbar (từng ghi nhận rò rỉ hơn 40 tiến trình chiếm RAM/CPU).
- **Cơ chế đóng 3 lớp dứt điểm:**
  1. Ngắt kết nối Playwright: `context.close()`, `browser.close()`.
  2. Gọi đồng thời cả 2 endpoint GPM API: `GET /api/v3/profiles/close/{pid}` và `GET /api/v3/profiles/stop/{pid}` trong khối `finally`.
  3. Quét dọn tiến trình mồ côi qua `psutil`:
     ```python
     import psutil
     for p in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
         if "chrome" in (p.info["name"] or "").lower():
             exe = (p.info["exe"] or "").lower()
             cmd = " ".join(p.info["cmdline"] or []).lower()
             # CHỈ kill tiến trình thuộc GPMLogin
             if "gpmlogin" in exe or "gpm_browser" in exe or "gpmlogin" in cmd or "gpm_browser" in cmd:
                 try:
                     p.kill()
                 except Exception: pass
     ```
  - **CẢNH BÁO SỐNG CÒN:** Tuyệt đối KHÔNG kill các tiến trình Chrome không chứa từ khóa `gpmlogin` / `gpm_browser` vì đó là trình duyệt làm việc cá nhân của người dùng (`C:\Program Files\Google\Chrome\Application\chrome.exe`).

## 24. Đa Hình Account Chooser & Tự Động Tích Consent Checkbox (2026-09-24)
- **Bẫy URL Guard trên Account Chooser (Nuốt màn hình reCAPTCHA/Challenge):**
  - Khi bắt selector email trên màn hình chọn tài khoản: Nếu không kiểm tra URL hiện tại mà dùng `page.get_by_text(email.lower()).first`, locator này sẽ match nhầm vào email badge hiển thị ở tiêu đề trang của màn hình `Verify it's you` / `Confirm you're not a robot` (reCAPTCHA) hoặc `Enter your password`.
  - Hậu quả: Script click nhầm vào badge tiêu đề rồi gọi `continue`, khiến vòng lặp không bao giờ chạm tới bước giải reCAPTCHA hoặc điền password.
  - **Quy tắc bắt buộc:** Luôn bọc điều kiện kiểm tra URL Account Chooser và LOẠI TRỪ các URL challenge / selectchallenge (vì trang Security Method Selection cũng có URL chứa `selectchallenge` và hiển thị huy hiệu email trên đầu trang; nếu không loại trừ sẽ click nhầm huy hiệu và nuốt mất trang chọn hình thức xác minh):
    ```python
    u_lower = page.url.lower()
    if ("accountchooser" in u_lower or "chooseaccount" in u_lower) and "selectchallenge" not in u_lower and "challenge" not in u_lower:
        acc_div = page.locator(f'div[data-email="{email.lower()}"], div[data-identifier="{email.lower()}"], [role="link"]:has-text("{email.lower()}"), [role="button"]:has-text("{email.lower()}")').first
        if acc_div.count() == 0:
            acc_div = page.get_by_text(email.lower()).first
        if acc_div.count() > 0 and acc_div.is_visible():
            acc_div.click(timeout=5000)
    ```
- **Tự động tích Checkbox ủy quyền:** Màn hình Google Consent hiện tại thường để các checkbox quyền ở trạng thái chưa chọn (`:not(:checked)`). BẮT BUỘC duyệt và tick toàn bộ trước khi click "Tiếp tục" / "Cho phép":
  ```python
  for cb in page.locator('input[type="checkbox"]:not(:checked)').all():
      try:
          if cb.is_visible(): cb.check(timeout=2000)
      except Exception: pass
  ```

## 25. Cạm Bẫy Đọc Credentials Từ Excel `gmail_clean_v2.xlsx` Bị Ghi Đè Bởi Recovery Email
- **Hiện tượng lỗi:** Khi duyệt các dòng trong file `gmail_clean_v2.xlsx`:
  - Cột 1 là Email tài khoản chính (ví dụ: `thoan190945@gmail.com`).
  - Cột 4 là Email khôi phục (ví dụ: `thanhdatbui1995@gmail.com`).
  - Nếu duyệt lặp `for cell in row: if "@gmail.com" in s: email = s`, ô Email khôi phục ở cột 4 sẽ ghi đè lên biến `email` của tài khoản chính.
  - Hậu quả: Toàn bộ mật khẩu và TOTP của tài khoản chính bị gán nhầm cho Email khôi phục, khiến map credentials tra cứu `creds.get(email_chính)` trả về `None` (mất mật khẩu và 2FA của 150+ tài khoản chính).
- **Quy tắc trích xuất chuẩn theo chỉ số cột:**
  ```python
  for row in list(ws.iter_rows(values_only=True))[1:]:
      if not row or len(row) < 3:
          continue
      # Cố định Cột 1 là tài khoản chính, tuyệt đối không duyệt lặp cell để tránh bị Cột 4 ghi đè
      em = str(row[1] or "").strip().lower()
      if "@gmail.com" in em:
          pwd = str(row[2] or "").strip()
          totp = str(row[3] or "").strip() if len(row) > 3 else ""
          recovery_email = str(row[4] or "").strip().lower() if len(row) > 4 else ""
          dob = str(row[5] or "").strip() if len(row) > 5 else ""
          creds[em] = {
              "password": pwd,
              "totp": totp,
              "recovery_email": recovery_email,
              "dob": dob
          }
  ```

## 26. Xử Lý Thử Thách Cấp 2 "Confirm your recovery email" / "Choose how you want to sign in" (2026-09-24)
- **Bối cảnh:** Khi tài khoản vượt qua reCAPTCHA (bằng Audio Solver) và điền đúng Password, Google có thể tiếp tục hiển thị màn hình Security Checkpoint:
  `Choose how you want to sign in:`
  - *Get a verification code at tha.... .......@gmail.com* (gửi mã 6 số về recovery email)
  - *Confirm your recovery email* (gõ lại chính xác địa chỉ email khôi phục đã liên kết)
  - *Use another phone or computer to finish signing in*
- **Kỹ thuật xử lý chuẩn xác bằng `page.evaluate`:**
  - Thay vì dùng locator Playwright dễ bị lỗi DOM shadow hoặc trượt text tiếng Việt/Anh:
    1. Dùng `page.evaluate()` duyệt toàn bộ DOM click chọn phương thức `"Confirm your recovery email"` / `"Xác nhận email khôi phục"`:
       ```javascript
       for (const el of document.querySelectorAll('div, li, span, a, [role="link"], [data-challengeindex]')) {
           const txt = (el.innerText || el.textContent || '').trim();
           if (txt === 'Confirm your recovery email' || txt === 'Xác nhận email khôi phục' || txt.includes('Confirm your recovery email')) {
               el.click(); return true;
           }
       }
       ```
    2. Khi ô nhập email khôi phục xuất hiện (`input[name="knowledgePreregisteredEmailResponse"]` hoặc `input[type="email"]`), inject `recovery_email` (trích xuất từ Cột 4 Excel `gmail_clean_v2.xlsx`), dispatch event `input` & `change`, rồi click nút "Tiếp theo" / "Next".

## 27. Tự Động Đọc OTP Gửi Về Mail Khôi Phục Qua IMAP (User Correction 2026-09-24)
- **Bối cảnh:** Khi Google yêu cầu gửi mã xác nhận về Email Khôi Phục (*"Get a verification code at <recovery_email>"*):
  - Tuyệt đối KHÔNG dừng lại hay fail-fast bỏ cuộc! Codebase và hệ thống farm ĐÃ TÍCH HỢP SẴN cơ chế đọc IMAP hoàn chỉnh từ repo `D:/Taadaa/add mail khoi phuc/read_otp_mail.py` và `automation_core/mailbox.py` (`fetch_latest_otp`).
  - Môi trường đã cấu hình sẵn biến môi trường:
    + `OTP_MAIL_USER`: Hòm mail nhận mã khôi phục (ví dụ `thanhdatbui1995@gmail.com`).
    + `OTP_MAIL_APP_PASSWORD`: Google App Password để login IMAP SSL (`imap.gmail.com:993`).
- **Quy trình 3 bước xử lý tự động:**
  1. **Click chọn phương thức nhận mã:**
     Dùng `page.evaluate()` click vào item chứa text `Get a verification code at` / `Nhận mã xác minh tại`:
     ```javascript
     for (const el of document.querySelectorAll('li, [role="link"], [role="button"], [data-challengeindex]')) {
         const txt = (el.innerText || el.textContent || '').trim();
         if (txt.includes('Get a verification code at') || txt.includes('Nhận mã xác minh tại') || (txt.includes('Get a verification code') && txt.includes('@gmail.com'))) {
             el.click(); return true;
         }
     }
     ```
  2. **Lắng nghe và bóc tách OTP từ IMAP siêu tốc (< 3s):**
     - Hòm thư chứa hàng chục nghìn email (37,000+ emails): Tuyệt đối CẤM dùng `imap.search(None, "ALL")` rồi lặp fetch full body.
     - BẮT BUỘC lọc nhanh theo người gửi: `imap.search(None, "FROM", "\"google.com\"")`.
     - Chỉ fetch header `(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])` của 6-8 email mới nhất để kiểm tra mốc thời gian `not_before_ts = time.time() - lookback_seconds`. Bỏ qua mail có subject chứa `cảnh báo` / `security alert`.
     - Khi tìm thấy mail gửi mã xác nhận, mới tải RFC822 body để trích xuất.
  3. **Cạm bẫy bóc tách OTP trùng 6 số trong Username Gmail:**
     - Trong nội dung email Google gửi về có đoạn: `We received a request to access your Google Account thoan190945@gmail.com through your email address. Your Google verification code is: 984229`.
     - Username `thoan190945` có đúng 6 chữ số `190945`! Nếu dùng regex ngây thơ `(?<!\d)(\d{6})(?!\d)` trên toàn văn, regex sẽ bắt nhầm `190945` thay vì mã thực tế `984229` $\rightarrow$ Google báo lỗi sai mã ("Wrong code. Try again.").
     - **Giải pháp bắt buộc:**
       + BƯỚC 1: Xóa sạch toàn bộ địa chỉ email ra khỏi text trước khi regex:
         `clean_body = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", " ", body)`
       + BƯỚC 2: Ưu tiên bắt theo anchor xác thực:
         `m = re.search(r"(?i)(?:verification code is|ma xac minh la|code is|is:)\D{0,40}(\d{6})(?!\d)", clean_body)`
  4. **Điền mã vào ô xác minh:**
     Điền OTP vào locator `input[name="code"], #idvPin, input[id*="idvPin"], input[id*="Pin"]:not([id*="phone"]):not([id*="Phone"])` và click nút "Tiếp theo" / "Next" để hoàn tất OAuth flow.

## 28. Phân Tách Tuyệt Đối Selector TOTP 2FA vs Email OTP vs Phone Checkpoint (2026-09-24)
- **Hiện tượng lỗi:**
  - Selector TOTP 2FA cũ thường dùng: `#totpPin, input[type="tel"]:visible`.
  - Khi Google chuyển sang màn hình Phone Checkpoint: *"There is something unusual about your activity... Enter a phone number to get a text message with a verification code"*, form này cũng có ô nhập `input[type="tel"]` hoặc nhãn `Phone number`.
  - Hậu quả: Script nhầm ô nhập số điện thoại là ô nhập mã TOTP hoặc Email OTP, tự động điền chuỗi 6 chữ số vào ô số điện thoại, làm Google báo lỗi *"Sorry, didn't recognize this phone number"* và dẫn tới nguy cơ khóa checkpoint nặng hơn.
- **Quy tắc phân tách 3 lớp chuẩn xác:**
  1. **Nhận diện sớm Phone Checkpoint (Fail-Fast Guard):**
     Kiểm tra bằng evaluate trước khi chạm vào bất kỳ input nào:
     ```python
     is_phone_cp = page.evaluate('''() => {
         const txt = (document.body.innerText || '').toLowerCase();
         return (txt.includes('phone number') || txt.includes('số điện thoại')) && (txt.includes('enter a phone') || txt.includes('nhập số'));
     }''')
     if is_phone_cp:
         log(f"[{email}] Google yêu cầu PHONE CHECKPOINT. Dừng ngay để bảo vệ tài khoản!")
         break  # Dừng xử lý tài khoản này, tuyệt đối không nhập OTP bừa bãi
     ```
  2. **Selector TOTP Google Authenticator độc quyền:**
     Chỉ bắt đúng ID của TOTP, CẤM đưa `input[type="tel"]` vào:
     `totp_inp = page.locator('#totpPin, input[name="totpPin"], input[id*="totpPin"]').first`
  3. **Selector Email OTP độc quyền:**
     Loại trừ rõ ràng các ID liên quan đến phone:
     `otp_inp = page.locator('input[name="code"], #idvPin, input[id*="idvPin"], input[id*="Pin"]:not([id*="phone"]):not([id*="Phone"]), input[name="pin"]').first`










