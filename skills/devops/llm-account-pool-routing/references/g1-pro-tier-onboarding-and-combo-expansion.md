# Quy Trình Tự Động Nạp Tài Khoản Google AI Pro Mới Vào OmniRoute (:20129)

Tài liệu này chuẩn hóa quy trình tự động hóa end-to-end khi người dùng nâng cấp gói Google One AI Pro / Google AI Pro (`g1-pro-tier`) cho tài khoản Gmail mới, nhằm đưa tài khoản vào OmniRoute và mở rộng combo Pro (`ag-gemini-pool-3`).

---

## 1. Bản chất & Triệu chứng thường gặp
- **Người dùng thắc mắc:** *"Vừa nâng acc gemini pro cho mail này, mà sao ở omni route nó vẫn không hiện lên nhỉ vẫn để tier free"*.
- **Cơ chế chẩn đoán O(1):**
  1. OmniRoute không tự động quét các email ngoài luồng. Tài khoản bắt buộc phải được kết nối qua OAuth Antigravity (`/api/oauth/antigravity/authorize` & `/exchange`).
  2. Người dùng nhìn nhầm tài khoản cũ có tiền tố/tên tương tự (ví dụ `ninhy05102002@gmail.com` là tài khoản free cũ tạo trước đó, khác hoàn toàn với `ninhvan04061999@gmail.com` vừa nâng cấp).
  3. Kiểm tra danh sách connections:
     ```python
     import urllib.request, json
     req = urllib.request.urlopen('http://127.0.0.1:20129/api/providers')
     conns = json.loads(req.read().decode()).get('connections', [])
     found = [c for c in conns if target_email.lower() in c.get('email', '').lower()]
     ```
     Nếu `found` rỗng: tài khoản **CHƯA ĐƯỢC KẾT NỐI** vào OmniRoute, không phải lỗi hiển thị sai tier.

---

## 2. Quy trình Tự động hóa 4 Bước (Headless CDP + GPM API)

### Bước 1: Khởi chạy Profile GPM & Mở CDP Port
- Tìm profile GPM tương ứng qua `/api/v3/profiles`:
  ```python
  import urllib.request, json
  # Tra cứu ID profile theo email
  req = urllib.request.urlopen('http://127.0.0.1:19995/api/v3/profiles?page=1&per_page=100')
  profiles = json.loads(req.read().decode()).get('data', [])
  target_prof = next((p for p in profiles if email in p.get('name', '')), None)
  ```
- Khởi chạy profile: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
- Lấy `remote_debugging_address` (ví dụ `127.0.0.1:57407`).
- *Lưu ý an toàn:* Luôn bọc trong khối `try/finally` để gọi `GET /api/v3/profiles/close/{profile_id}` ngay khi xong, không để profile chạy ngầm chiếm tài nguyên và port.

### Bước 2: Sinh URL Authorize & Tương tác OAuth qua Playwright
- Gọi OmniRoute sinh URL và token PKCE:
  ```python
  auth_req = urllib.request.urlopen('http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri=http%3A%2F%2F127.0.0.1%3A20129%2Fcallback')
  auth_data = json.loads(auth_req.read().decode())
  auth_url = auth_data['authUrl']
  state = auth_data['state']
  code_verifier = auth_data['codeVerifier']
  ```
- Kết nối `async_playwright` qua CDP:
  ```python
  from playwright.async_api import async_playwright
  async with async_playwright() as p:
      browser = await p.chromium.connect_over_cdp(f"http://{remote_debugging_address}")
      context = browser.contexts[0]
      page = await context.new_page()
      
      code_future = asyncio.get_event_loop().create_future()
      async def on_request(req):
          if '/callback' in req.url and 'code=' in req.url:
              parsed = urllib.parse.urlparse(req.url)
              params = urllib.parse.parse_qs(parsed.query)
              if 'code' in params and not code_future.done():
                  code_future.set_result(params['code'][0])
      page.on('request', on_request)
      
      await page.goto(auth_url, wait_until='domcontentloaded')
      # Xử lý Account Chooser và Consent Button nếu xuất hiện
  ```

### Bước 3: Exchange Code & Kích hoạt Model
- Bắt `code` từ query URL và gửi POST tới `/api/oauth/antigravity/exchange`:
  ```json
  {
    "code": "<captured_code>",
    "redirectUri": "http://127.0.0.1:20129/callback",
    "codeVerifier": "<code_verifier>",
    "state": "<state>"
  }
  ```
- Response trả về `connection.id` mới (ví dụ `5a1e3685-981c-4144-a5e7-8a784b6a693b`).
- Gọi Sync Models:
  ```bash
  curl -X POST http://127.0.0.1:20129/api/providers/{connection_id}/sync-models -H "Content-Type: application/json" -d '{}'
  ```
- Kiểm tra lại provider limits:
  OmniRoute tự động gọi `loadCodeAssist` lên Google Cloud Code và trả về:
  `tier: "g1-pro-tier"`, `plan: "Pro"`, `subscriptionTier: "Google AI Pro"`.

### Bước 4: Ping Thử Nghiệm & Nạp Vào Combo Pro
- Test inference xác thực trạng thái hoạt động:
  ```bash
  curl -s -X POST http://127.0.0.1:20129/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "x-omniroute-connection: {connection_id}" \
    -d '{"model": "antigravity/gemini-3.8-flash-tiered", "messages": [{"role": "user", "content": "ping"}]}'
  ```
- Bổ sung connection vào combo **`ag-gemini-pool-3`**:
  - `GET /api/combos/{ag-gemini-pool-3-id}`
  - Thêm model entry:
    ```json
    {
      "id": "ag-gemini-pro-{count}-{short_cid}",
      "kind": "model",
      "model": "antigravity/gemini-3.8-flash-tiered",
      "providerId": "antigravity",
      "connectionId": "{connection_id}",
      "weight": 0,
      "label": "pro-{username}"
    }
    ```
  - `PUT /api/combos/{ag-gemini-pool-3-id}` với payload đã cập nhật.
- Đồng bộ file dự phòng `D:/Taadaa/AI-Tools/tools/omniroute/combos_backup.json`.
- Cập nhật số lượng Pro models trong test suite `D:/Taadaa/AI-Tools/tests/test_omniroute_combos.py` và chạy `pytest` xác thực toàn bộ test pass.
