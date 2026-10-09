# GPM & Hotmail Graph API Automated OAuth Re-Auth for Cockpit Codex

## 1. Context & Trigger
Khi tài khoản Codex trong Cockpit Tools bị thu hồi session OAuth (`token_revoked` / HTTP 401), hoặc khi add tài khoản Hotmail mới vào Cockpit mà không muốn nhập tay mã OTP xác nhận.

## 2. Full Automated Flow

```text
[GPM Profile Launch (API :19995)]
          │
          ▼
[Cockpit Tools UI: Trigger OAuth (Refresh Auth Link -> Listen :1455)]
          │
          ▼
[Playwright Connect CDP -> Open OAuth URL -> Input Hotmail Email]
          │
          ▼
[Microsoft Graph API (OAuth Token Refresh -> Fetch Latest OTP Inbox Message)]
          │
          ▼
[Playwright Fill 6-Digit OTP -> Click Continue -> Select Personal Workspace]
          │
          ▼
[Callback to http://localhost:1455/auth/callback -> Cockpit Accounts DB Updated]
```

### Bước 1: Khởi động profile GPM qua Local API
- Endpoint: `http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`
- Lấy `remote_debugging_address` (VD: `127.0.0.1:55951`).

### Bước 2: Kích hoạt OAuth listener trên Cockpit
- Cockpit Tools lắng nghe callback tại `http://127.0.0.1:1455/auth/callback`.
- Gọi UIA / Click vào button `Refresh Auth Link` trên cửa sổ Cockpit Tools để tạo state mới và mở cổng 1455.

### Bước 3: Lấy mã OTP tự động qua Microsoft Graph API
Sử dụng `refresh_token` và `client_id` có sẵn từ kho tài khoản:
```python
import urllib.request, urllib.parse, json, re

# 1. Refresh Microsoft Graph Access Token
body = urllib.parse.urlencode({
    'client_id': client_id,
    'grant_type': 'refresh_token',
    'refresh_token': refresh_token,
    'scope': 'openid profile offline_access https://graph.microsoft.com/mail.read'
}).encode()
req = urllib.request.Request('https://login.microsoftonline.com/common/oauth2/v2.0/token', data=body, headers={'Content-Type': 'application/x-www-form-urlencoded'})
access_token = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())['access_token']

# 2. Query Messages
inbox_url = 'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=5&$orderby=receivedDateTime desc'
req = urllib.request.Request(inbox_url, headers={'Authorization': f'Bearer {access_token}'})
data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())

# 3. Extract 6-digit OTP from noreply@tm.openai.com
for m in data.get('value', []):
    text = f"{m.get('subject', '')} {m.get('bodyPreview', '')}"
    codes = re.findall(r'(?<!\d)(\d{6})(?!\d)', text)
    if codes:
        otp_code = codes[0]
        break
```

### Bước 4: Playwright hoàn tất OAuth
- Fill `otp_code` vào form `auth.openai.com/email-verification`.
- Click "Tiếp tục" ➔ Consent screen ➔ Cockpit tự động bắt token và lưu vào `codex_accounts.json`.
