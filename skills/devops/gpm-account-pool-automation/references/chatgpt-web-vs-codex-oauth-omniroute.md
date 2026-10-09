# ChatGPT-Web vs Codex OAuth via GPMLogin & OmniRoute (Port 20129)

## 1. Bản chất 2 phương thức trích xuất tài khoản vào OmniRoute

### A. Phương thức 1: `chatgpt-web` (Khuyên dùng cho Farm/Batch)
- **Cơ chế**: Mở profile GPM -> Duyệt `https://chatgpt.com/api/auth/session` -> Lấy `__Secure-next-auth.session-token` hoặc `accessToken` từ session JSON -> Nạp vào OmniRoute qua `POST /api/providers` (provider: `chatgpt-web`, authType: `apikey`).
- **Ưu điểm vượt trội**:
  - **Gọi được cả model Codex**: `chatgpt-web/gpt-5.6-terra-high`, `chatgpt-web/gpt-5.6-sol-high`, `chatgpt-web/gpt-5.6-sol-xhigh`, `chatgpt-web/gpt-5.6-luna-free-thinking`.
  - **Không dính Phone Verification**: Hoàn toàn né được checkpoint yêu cầu số điện thoại của OpenAI.
  - **Không bị lỗi 503 Quota 30 ngày**: Không bị áp đặt hạn ngạch tháng cứng như tài khoản developer của Codex CLI.
  - **Tuổi thọ token thực tế**: Session token sống bền nhiều ngày (không phải 1-2 tiếng như suy đoán lý thuyết). Đã kiểm chứng các session tạo từ sáng đến tối vẫn trả về `status: 200 OK` 100%.

### B. Phương thức 2: `codex` (OAuth Developer Flow)
- **Cơ chế**: Gọi OmniRoute `GET /api/oauth/codex/start-callback-server` -> Mở `authUrl` trên GPM -> Click Google SSO -> Bấm `Authorize/Allow` -> OmniRoute bắt callback cổng 1455 -> Lấy `refresh_token` (`rt.1...`).
- **Nhược điểm nghiêm trọng**:
  - OpenAI bắt verify số điện thoại (Phone Checkpoint) với các tài khoản chưa gắn SMS.
  - Hết hạn ngạch trả về `503 Unavailable (reset after 702h)` (~29 ngày không gọi được).

### C. Nguy cơ nghẽn Combo Review khi dùng Codex đơn lẻ & Phân tách Quota Pool
- **Hiện tượng**: Combo `review` (Tier 1: `codex/gpt-5.6-terra-high`) dính `503 Unavailable (reset after 700h+)`.
- **Nguyên nhân cốt lõi**: Toàn bộ pool Codex chỉ có 1 connection active (`~/.codex/auth.json`), trong khi 81 account Google trong OmniRoute thuộc pool `antigravity` (Gemini/Opus), không thuộc Codex. Khi gọi review dồn dập, 1 account Codex duy nhất bị vắt kiệt hạn ngạch tháng.
- **Chứng minh Quota độc lập**: Cùng một tài khoản khi gọi `codex` báo 503 (`reset after 699h`), nhưng gọi qua `chatgpt-web` (`gpt-5.6-luna-free` hoặc `gpt-5.6-sol-high`) thì trả về **`200 OK` 100%**. OpenAI tách biệt hoàn toàn 2 hạn ngạch này.
- **Giải pháp cho Review/Plan**: Cấu hình thêm model `chatgpt-web/gpt-5.6-sol-high` hoặc `chatgpt-web/gpt-5.6-sol-xhigh` vào combo `review` làm fallback để san tải giữa web pool và codex pool.

---

## 2. Pitfalls & Workarounds khi thao tác GPM + Playwright

### Pitfall 1: Khóa file SQLite `Cookies` trong `Default/Network/Cookies`
- **Hiện tượng**: Khi profile GPM hoặc các tiến trình chrome ngầm đang chạy, mở SQLite trực tiếp đọc cookie `SID` sẽ văng `sqlite3.OperationalError: database is locked` hoặc `PermissionError: [Errno 13]`.
- **Giải pháp**: Luôn copy file ra thư mục tạm (`shutil.copyfile`) trước khi kết nối SQLite, và dọn dẹp file tạm trong khối `finally`:
  ```python
  temp_path = f"C:/Users/Kibe/AppData/Local/Temp/gpm_cookie_check_{os.getpid()}_{idx}.db"
  try:
      shutil.copyfile(cookie_db, temp_path)
      conn = sqlite3.connect(temp_path)
      c = conn.cursor()
      c.execute('SELECT COUNT(*) FROM cookies WHERE host_key LIKE "%google%" AND name = "SID"')
      has_sid = c.fetchone()[0] > 0
      conn.close()
  finally:
      if os.path.exists(temp_path):
          os.remove(temp_path)
  ```

### Pitfall 2: Dọn dẹp tiến trình rác `gpm_browser`
- **Hiện tượng**: API `GET /profiles/stop/{id}` đôi khi không kill sạch các process con `chrome.exe` của GPM, dẫn tới tích tụ hàng trăm process chiếm RAM và khóa database.
- **Giải pháp**: Kill theo đường dẫn executable của GPM:
  ```python
  import psutil
  for p in psutil.process_iter(['name', 'exe']):
      try:
          exe = p.info.get('exe') or ''
          if 'gpm_browser' in exe.lower() and 'chrome.exe' in exe.lower():
              p.kill()
      except Exception:
          pass
  ```

### Pitfall 3: Null-safe khi gọi GPM API `start`
- **Hiện tượng**: `r.json().get('data').get('remote_debugging_address')` quăng `'NoneType' object has no attribute 'get'` khi profile đang khởi động dở hoặc gặp lỗi proxy.
- **Giải pháp**:
  ```python
  res = requests.get(url, timeout=30).json()
  data = res.get("data") or {}
  addr = data.get("remote_debugging_address")
  if not addr:
      # handle failure
  ```

### Pitfall 4: Lỗi Cloudflare Auth WAF ("Oops! We ran into an issue")
- **Hiện tượng**: Bấm `Continue with Google` bị chuyển hướng ngay sang `https://chatgpt.com/auth/error?error=undefined` kèm thông báo *"Oops! We ran into an issue while signing you in, please take a break and try again soon."*
- **Nguyên nhân**: Dải IP proxy di động bị WAF của OpenAI tạm khóa luồng đăng nhập do quá nhiều request auth trong thời gian ngắn.
- **Xử lý**: Cần cho proxy cooldown 1-2 tiếng hoặc xoay IP/cổng proxy sạch, tuyệt đối không retry vòng lặp mù làm tăng thời gian phạt.

### Pitfall 5: Bẫy Onboarding đa ngôn ngữ "About You" (Tiếng Anh vs Tiếng Việt DateField)
- **Hiện tượng**: Sau khi cấp quyền Google, OpenAI mở trang `https://auth.openai.com/about-you`. Nếu script chỉ tìm `input[name="age"]` sẽ bị timeout hoặc bị OpenAI báo lỗi đỏ *"Chúng tôi không thể tạo tài khoản với thông tin đó"*.
- **Nguyên nhân**:
  - Giao diện Tiếng Anh: Render ô input số tuổi đơn giản `input[name="age"]`.
  - Giao diện Tiếng Việt: Render component React-Aria DateField với 3 ô nhập riêng biệt: `div[data-type="day"]`, `div[data-type="month"]`, `div[data-type="year"]`. Mặc định component này load năm hiện tại (2026), nếu không gõ lại năm sinh sẽ bị chặn dưới 18 tuổi.
- **Giải pháp xử lý triệt để cả 2 dạng**:
  ```python
  def handle_about_you_onboarding(page, p_name, email):
      # 1. Họ và tên nếu trống
      name_inp = page.locator('input[name="name"]').first
      if name_inp.count() > 0 and name_inp.is_visible():
          if not name_inp.input_value():
              name_inp.fill(p_name.split('@')[0].replace('-', ' ').strip() or email.split('@')[0])
      # 2. Dạng 1: Ô Age (Tiếng Anh)
      age_inp = page.locator('input[name="age"]').first
      if age_inp.count() > 0 and age_inp.is_visible():
          age_inp.click(force=True)
          page.keyboard.type(str(random.randint(22, 28)), delay=80)
      # 3. Dạng 2: Ngày sinh (Tiếng Việt DateField)
      day_el = page.locator('div[data-type="day"]').first
      if day_el.count() > 0 and day_el.is_visible():
          day_el.click()
          page.keyboard.type(f"{random.randint(10, 28):02d}", delay=80)
          month_el = page.locator('div[data-type="month"]').first
          if month_el.count() > 0:
              month_el.click()
              page.keyboard.type(f"{random.randint(1, 12):02d}", delay=80)
          year_el = page.locator('div[data-type="year"]').first
          if year_el.count() > 0:
              year_el.click()
              page.keyboard.type(str(random.randint(1996, 2002)), delay=80)
      # 4. Submit form
      sb_btn = page.locator('button[type="submit"], button:has-text("Continue"), button:has-text("Tiếp tục")').first
      if sb_btn.count() > 0:
          sb_btn.click(force=True)
  ```

### Pitfall 6: Trình duyệt bị treo ở Title `Loading https://...` (Redirect treo của Google/OpenAI)
- **Hiện tượng**: Page URL vẫn ở `https://chatgpt.com/auth/login` nhưng Title của tab lại là `Loading https://accounts.google.com/v3/signin/accountchooser?...` hoặc `Loading https://auth.openai.com/api/accounts/callback/google?...`, trang web không tự điều hướng tiếp.
- **Giải pháp**: Kiểm tra `page.title()`, nếu chứa `Loading https://` thì ép Playwright điều hướng trực tiếp tới URL đích:
  ```python
  t = page.title()
  if "Loading https://" in t:
      target_url = t.replace("Loading ", "").strip()
      page.goto(target_url, timeout=30000)
  ```

### Pitfall 7: Lỗi `token_exchange_failed` khi chạy batch concurrency cao
- **Hiện tượng**: Hàng loạt tài khoản nhảy vào `https://auth.openai.com/error?payload=...` với payload giải mã là `{"kind": "AuthApiFailure", "errorCode": "token_exchange_failed"}`.
- **Nguyên nhân**: 5 worker chạy song song gửi request đổi authorization code lấy token liên tục qua cùng cụm IP proxy, OpenAI từ chối đổi mã.
- **Giải pháp**: Giảm worker xuống 1–2 hoặc thêm delay giãn cách 20–30s giữa các tài khoản, không chạy dồn dập nhiều worker auth cùng lúc.

### Pitfall 8: Bẫy trích xuất Cookie Chunked NextAuth (>4KB) gây lỗi 401 Unauthorized
- **Hiện tượng**: Tài khoản vừa đăng nhập xong, nạp vào OmniRoute nhưng dashboard báo `apiKeyHealth: { status: "invalid", failures: 2 }`, hoặc test trả về `401 - ChatGPT session expired — log into chatgpt.com and copy a fresh cookie`.
- **Nguyên nhân**: Khi cookie phiên NextAuth vượt quá 4096 bytes, trình duyệt tự động tách thành chunk: `__Secure-next-auth.session-token.0` và `__Secure-next-auth.session-token.1`. Nếu script Playwright chỉ duyệt `for ck in context.cookies(): if 'session-token' in ck['name']: session_token = ck['value']; break`, script dừng ngay ở chunk `.0`, chỉ lấy chuỗi JWT cụt nửa đầu (`eyJhbGci...`) và bỏ quên chunk `.1`. Khi backend NextAuth tiếp nhận cookie cụt, server từ chối giải mã và trả về 401.
- **Giải pháp trích xuất & ghép chunk chuẩn xác**:
  ```python
  session_chunks = {}
  for ck in context.cookies():
      ck_name = ck.get("name") or ""
      ck_val = ck.get("value") or ""
      if "session-token" in ck_name and ck_val:
          session_chunks[ck_name] = ck_val

  session_token = None
  if session_chunks:
      if any(".0" in k for k in session_chunks):
          # Sắp xếp đúng thứ tự chunk .0, .1,...
          sorted_chunks = sorted(session_chunks.items(), key=lambda x: x[0])
          session_token = "; ".join(f"{k}={v}" for k, v in sorted_chunks)
      else:
          # Cookie đơn lẻ unchunked
          k, v = next(iter(session_chunks.items()))
          session_token = f"{k}={v}" if not v.startswith("__Secure") else v
  ```
- **Lưu ý kiểm tra trùng lặp trên OmniRoute**: Khi kiểm tra danh sách connection `chatgpt-web` đã có, phải kiểm tra `key.startswith("eyJhbG") or "__Secure" in key` để không bỏ sót các account đã lưu cookie chuẩn có prefix `__Secure`.

### Pitfall 9: Vị trí SQLite OmniRoute & Phân biệt Quota Exhaustion vs Session Expired
- **Vị trí Database Runtime**: File SQLite của OmniRoute trên Windows **KHÔNG NẰM** trong thư mục repo `C:\Users\Kibe\OmniRoute\storage.sqlite` mà nằm tại `C:\Users\Kibe\.omniroute\storage.sqlite` (do hàm `getLegacyDotDataDir()` ưu tiên giữ nguyên đường dẫn legacy `~/.omniroute`).
- **Kỷ luật chẩn đoán Quota qua Bảng `call_logs`**:
  - Truy vấn `SELECT timestamp, model, account, status, error_summary, error_type FROM call_logs WHERE provider = 'chatgpt-web' ORDER BY timestamp DESC LIMIT 30;`
  - **Lỗi hết quota thực sự**: HTTP `429 Too Many Requests` hoặc HTTP `502 [502]: You've hit your limit. Please try again later.`. Lưu ý: Lỗi 502 này thường xảy ra khi client gọi các model Pro (`gpt-5.6-sol-pro`, `gpt-5.5-pro`) trên tài khoản ChatGPT Free, trong khi các model chuẩn (`gpt-5.6-sol-high`, `gpt-5.6-terra-high`, `gpt-5.6-luna-free`) vẫn trả về `200 OK`.
  - **Lỗi 401 Unauthorized**: Hoàn toàn không phải hết quota, mà là session cookie hết hạn hoặc dính token cụt (Pitfall 8). OmniRoute tự động failover ngay sang account sống kế tiếp trong pool.

### Pitfall 10: Lỗi GPM API chặn khởi động profile "Yêu cầu cập trình duyệt [Chromium] [142]" & Kỹ thuật Bypass bằng Persistent Context
- **Hiện tượng**: Gọi `GET /api/v3/profiles/start/{id}` trả về `{"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}` dù trong `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\` đã có sẵn thư mục `gpm_browser_chromium_core_142\chrome.exe`.
- **Nguyên nhân**: GPMLogin.exe kiểm tra phiên bản và chặn launch qua Local API nếu chưa qua trigger tải/xác nhận core trên UI app.
- **Giải pháp Bypass Triệt Để (Zero-UI & Headless)**:
  - Bỏ qua hoàn toàn GPM Local API `start/stop`. Khởi chạy trực tiếp trình duyệt thông qua Playwright Persistent Context trỏ thẳng vào thư mục profile của GPM:
    ```python
    from playwright.sync_api import sync_playwright

    CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"
    BASE_PROFILE_DIR = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile"

    full_path = os.path.join(BASE_PROFILE_DIR, p_path)

    # Parse raw_proxy (vd: test.taadaa.click:5105:mobi5:TaadaaMobi#2026!)
    proxy_cfg = None
    if raw_proxy:
        parts = raw_proxy.strip().split(":")
        if len(parts) == 4:
            proxy_cfg = {"server": f"http://{parts[0]}:{parts[1]}", "username": parts[2], "password": parts[3]}
        elif len(parts) == 2:
            proxy_cfg = {"server": f"http://{parts[0]}:{parts[1]}"}

    with sync_playwright() as pw:
        launch_kwargs = {
            "user_data_dir": full_path,
            "executable_path": CHROME_EXE,
            "headless": True,
            "args": ["--no-first-run", "--no-default-browser-check"]
        }
        if proxy_cfg:
            launch_kwargs["proxy"] = proxy_cfg

        browser = pw.chromium.launch_persistent_context(**launch_kwargs)
        page = browser.pages[0] if browser.pages else browser.new_page()
        # Thao tác Google SSO, lấy cookie...
        browser.close()
    ```
  - **Lợi ích**:
    1. Hoàn toàn thoát phụ thuộc vào API GPM bị lỗi core 142.
    2. Chạy ngầm `headless: True` tuyệt đối, không bật cửa sổ Chrome làm phiền taskbar hay giật con trỏ chuột.
    3. Giữ nguyên 100% session Google có sẵn trong `user_data_dir`.
    4. Không bị dialog popup "Bạn có muốn khôi phục trang không?" làm treo luồng automation.

### Pitfall 11: Xung đột môi trường Python trên Windows do `PYTHONPATH` trỏ nhầm venv
- **Hiện tượng**: Chạy script Playwright qua Python 3.12 nhưng gặp lỗi `ModuleNotFoundError: No module named 'greenlet._greenlet'`.
- **Nguyên nhân**: Biến môi trường `PYTHONPATH` trong shell kế thừa từ venv của hermes-agent (Python 3.11), khiến Python 3.12 nạp nhầm binary package của 3.11.
- **Giải pháp**:
  - Khi chạy terminal: Luôn chạy với tiền tố `env -u PYTHONPATH "C:/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe" ...`
  - Trong code Python: Đặt bộ lọc loại trừ ở đầu file trước khi import playwright:
    ```python
    import sys
    sys.path = [p for p in sys.path if "hermes-agent" not in p]
    ```

---

## 3. Quy trình tự động làm mới Cookie ChatGPT Web và đồng bộ OmniRoute Combo

### Endpoint chuẩn của GPM Local API v3 (Port 19995):
- Khởi chạy profile: `GET http://127.0.0.1:19995/api/v3/profiles/start/{pid}?win_scale=0.5`
  - Trả về JSON: `data.remote_debugging_address` (vd: `127.0.0.1:59933`), `data.process_id`.
- Đóng profile: `GET http://127.0.0.1:19995/api/v3/profiles/close/{pid}`
  - Luôn bọc trong khối `finally` để giải phóng tiến trình `chrome.exe` ngay sau khi lấy cookie.

### Luồng Refresh & Validate & Database Sync:
1. Kết nối CDP: `p.chromium.connect_over_cdp(f"http://{cdp_addr}")` -> navigate `https://chatgpt.com` -> chờ 5s.
2. Lấy cookie: `cookies = context.cookies()` -> ghép chuỗi `"; ".join([f"{c['name']}={c['value']}" for c in cookies])`.
3. Validate qua OmniRoute:
   ```python
   POST http://127.0.0.1:20129/api/providers/validate
   JSON: {"provider": "chatgpt-web", "apiKey": cookie_str}
   ```
4. Cập nhật SQLite `C:\Users\Kibe\.omniroute\storage.sqlite`:
   - Bảng `provider_connections`:
     ```sql
     UPDATE provider_connections 
     SET api_key=?, is_active=1, test_status='active', 
         last_error=NULL, last_error_at=NULL, backoff_level=0, 
         rate_limited_until=NULL, updated_at=CURRENT_TIMESTAMP 
     WHERE id=?
     ```
   - Bảng `combos`: Kiểm tra và nạp `connectionId` vào combo `chatgpt-web-pool` (cập nhật danh sách models và mô tả tổng số tài khoản).



