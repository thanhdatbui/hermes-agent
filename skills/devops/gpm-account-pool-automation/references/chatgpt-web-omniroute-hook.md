# ChatGPT Web Session Hook into OmniRoute (Port 20129)

## 1. Overview
Quy trình tự động kết nối tài khoản ChatGPT Web từ GPM profile vào OmniRoute pool (port `20129`) sử dụng Playwright CDP để trích xuất cookie `__Secure-next-auth.session-token`.
Lưu ý: Endpoint `/api/oauth/codex/authorize` là OAuth code flow của Codex CLI PKCE native, không dùng cho browser web login. Đối với ChatGPT Web, OmniRoute thiết kế dùng provider `chatgpt-web` dạng `authType: "apikey"` chứa session token.

## 2. API Specifications

### OmniRoute Add / Update Provider
- **Add Endpoint:** `POST http://127.0.0.1:20129/api/providers`
- **Update Endpoint:** `PUT http://127.0.0.1:20129/api/providers/{id}`
- **Payload:**
  ```json
  {
    "provider": "chatgpt-web",
    "name": "<email> (<name>)",
    "apiKey": "<__Secure-next-auth.session-token cookie value>",
    "authType": "apikey",
    "priority": 1
  }
  ```

### OmniRoute Verification Ping
- **Endpoint:** `POST http://127.0.0.1:20129/v1/chat/completions`
- **Headers:** `{"Content-Type": "application/json"}`
- **Payload:**
  ```json
  {
    "model": "chatgpt-web/gpt-5.6-luna-free",
    "messages": [{"role": "user", "content": "ping"}],
    "max_tokens": 10
  }
  ```
- *Lưu ý timeout*: Request đầu tiên có thể mất ~15-25s để giải captcha sentinel/pow ngầm, đặt timeout tối thiểu >= 35s.

## 3. Automation Steps & Pitfalls

### Step 1: Start Profile & CDP Attach
- Khởi động profile qua GPM Local API: `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}?win_scale=0.8`.
- Nhận `remote_debugging_address` và kết nối bằng `playwright.chromium.connect_over_cdp(...)`.

### Step 2: Session Check & Google Login
- Điều hướng tới `https://chatgpt.com`.
- Trích xuất cookies từ `context.cookies(["https://chatgpt.com"])`.
- **Xử lý Cookie Chunking**: Trình duyệt có thể phân mảnh cookie lớn thành các mẩu:
  - `__Secure-next-auth.session-token` (nếu không chia mẩu)
  - `__Secure-next-auth.session-token.0`, `__Secure-next-auth.session-token.1`, ...
  - Bắt buộc sort theo số đuôi và ghép chuỗi:
    ```python
    chunks = sorted(
        [c for c in cookies if c['name'].startswith('__Secure-next-auth.session-token.')],
        key=lambda x: int(x['name'].split('.')[-1])
    )
    full_token = ''.join(c['value'] for c in chunks)
    ```
- Nếu chưa có cookie:
  1. Điều hướng tới `https://chatgpt.com/auth/login`.
  2. Click `Continue with Google` / `Tiếp tục với Google` (selector: `button:has-text("Continue with Google")`).
  3. Quét qua `context.pages` tìm tab Google Accounts (`accounts.google.com`).
  4. Click chọn tài khoản Gmail đích (`div[data-email="{email}"]` hoặc `get_by_text(email)`).
  5. Nếu xuất hiện OAuth Consent button (`Tiếp tục`, `Continue`, `Allow`, `#submit_approve_access`), click xác nhận.

### Step 3: Handle Onboarding & Age/Birthday Form
- Form mới của OpenAI (`https://auth.openai.com/about-you`):
  - Input Name: `input[name="name"]` -> Fill Full Name.
  - Input Tuổi: `input[name="age"]` -> Phải nhập **số tuổi nguyên** (ví dụ `24`, `26`), CẤM nhập định dạng ngày sinh `DD/MM/YYYY` vì sẽ gây lỗi validation `! Nhập độ tuổi hợp lệ để tiếp tục`.
  - Submit Onboarding: `button:has-text("Continue")`, `button:has-text("Tiếp tục")` (dùng `force=True` nếu bị overlay).

### Step 4: Extract Cookie & Register
- Lấy chuỗi session token hoàn chỉnh.
- Kiểm tra danh sách connections hiện có qua `GET http://127.0.0.1:20129/api/providers`:
  - Nếu email đã tồn tại: gọi `PUT` cập nhật token mới.
  - Nếu chưa: gọi `POST` thêm mới.
- Ping kiểm tra chat completion với model `chatgpt-web/gpt-5.6-luna-free`.
- Dọn dẹp: Đóng Playwright CDP và gọi GPM Local API `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`.

## 4. Script & Hook Path
- Hook: `D:/Taadaa/GPM auto/src/chatgpt_omniroute_hook.py` (đồng bộ tại `D:/Taadaa/AI-Tools/tools/omniroute/chatgpt_omniroute_hook.py`).
- Runner: `D:/Taadaa/GPM auto/scripts/add_chatgpt_omniroute.py` (đồng bộ tại `D:/Taadaa/AI-Tools/tools/omniroute/add_chatgpt_omniroute.py`).
