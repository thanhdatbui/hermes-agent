# Codex (OpenAI) OAuth Hook vs ChatGPT Web Session on OmniRoute (Port 20129)

## 1. Distinction: `codex` (OAuth) vs `chatgpt-web` (Web Session Cookie)
Rất dễ nhầm lẫn giữa hai provider này trên OmniRoute:
1. **`chatgpt-web`**:
   - Provider dạng Web cookie session (`authType: "apikey"`, `authHeader: "cookie"`).
   - Sử dụng cookie `__Secure-next-auth.session-token` (hoặc chunks `.0`, `.1`).
   - Gọi endpoint web nội bộ `https://chatgpt.com/backend-api/conversation`.
   - Models: `chatgpt-web/gpt-5.6-luna-free`, `chatgpt-web/gpt-5.6-sol-pro`, etc.
   - Cần giải captcha/PoW (sentinel).

2. **`codex` (OpenAI Codex OAuth - YÊU CẦU MẶC ĐỊNH CHO CODEX / CLI PIPELINE)**:
   - Provider dạng OAuth PKCE chính thức (`provider: "codex"`, `authType: "oauth"` hoặc import token).
   - Chạy trên endpoint chuẩn: `https://chatgpt.com/backend-api/codex/responses`.
   - Phục vụ các model lập trình Codex: `gpt-5.5`, `gpt-5.6-sol`, `gpt-5.6-luna`, `gpt-5.5-high`, etc.
   - Cơ chế nạp vào OmniRoute:
     - Endpoint: `POST http://127.0.0.1:20129/api/oauth/codex/import-token`
     - Payload:
       ```json
       {
         "accessToken": "<OAuth JWT accessToken>",
         "refreshToken": "<optional refresh token>",
         "name": "<email> (<name>)"
       }
       ```

## 2. Cách trích xuất OAuth Access Token từ GPM Browser
Khi tài khoản đã đăng nhập ChatGPT trên Profile GPMLogin:
- Truy cập thẳng endpoint: `https://chatgpt.com/api/auth/session`.
- Response trả về JSON dạng:
  ```json
  {
    "user": { "id": "user-...", "name": "...", "email": "..." },
    "expires": "...",
    "accessToken": "eyJhbGciOiJSUzI1Ni..."
  }
  ```
  *(Đây là OAuth JWT do Auth0/OpenAI cấp: `iss: https://auth.openai.com`, `aud: https://api.openai.com/v1`)*.
- Trích xuất trường `accessToken` và đẩy vào endpoint `import-token` của OmniRoute.

## 3. Automation Flow với Playwright CDP
```python
import requests, json, re
from playwright.sync_api import sync_playwright

def extract_codex_access_token(remote_debugging_address: str) -> str:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f"http://{remote_debugging_address}")
        context = browser.contexts[0]
        page = context.new_page()
        page.goto("https://chatgpt.com/api/auth/session", timeout=25000)
        page.wait_for_timeout(1500)
        content = page.content()
        page.close()
        browser.close()

    m = re.search(r"<pre>(.*?)</pre>", content, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1)).get("accessToken", "")
        except Exception:
            pass
    return ""

def import_to_omniroute_codex(access_token: str, label: str):
    return requests.post("http://127.0.0.1:20129/api/oauth/codex/import-token", json={
        "accessToken": access_token,
        "name": label
    }).json()
```

## 4. Verification Ping
Sau khi nạp vào OmniRoute, verify bằng model Codex chuẩn:
- **Endpoint**: `POST http://127.0.0.1:20129/v1/chat/completions`
- **Payload**:
  ```json
  {
    "model": "gpt-5.5",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 10
  }
  ```
- Phản hồi 200 với model `gpt-5.5` và nội dung chat từ Codex engine xác nhận tài khoản hoạt động thành công 100%.

## 5. Artifacts & Code Paths
- Hook: `D:/Taadaa/GPM auto/src/codex_omniroute_hook.py` (đồng bộ tại `D:/Taadaa/AI-Tools/tools/omniroute/codex_omniroute_hook.py`)
- Script GPM ChatGPT Web cũ (nếu cần dùng cookie web): `chatgpt_omniroute_hook.py`
