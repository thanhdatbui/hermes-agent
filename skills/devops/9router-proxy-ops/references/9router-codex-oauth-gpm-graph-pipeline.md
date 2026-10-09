# 9Router Codex OAuth + GPM + Microsoft Graph API Pipeline

## 1. Context & Architecture
9Router (`http://127.0.0.1:20128`) supports the `codex` provider (`https://chatgpt.com/backend-api/codex`) with per-connection proxy routing via `proxyPoolId` in `providerConnections.data`.
Unlike Cockpit Tools (which forces all connections through a single global egress proxy), 9Router assigns an individual proxy pool ID to each connection.

When OpenAI access tokens are revoked (e.g., due to previous direct-IP leaks), re-authenticating through 9Router requires OAuth PKCE with automatic OTP retrieval via Microsoft Graph API and workspace consent selection.

## 2. Automated OAuth Flow Specification
### Step 1: Initiate PKCE in 9Router
1. Request PKCE credentials:
   `GET http://127.0.0.1:20128/api/oauth/codex/authorize?redirect_uri=http://localhost:1455/auth/callback`
   Returns JSON with `{ authUrl, state, codeVerifier, redirectUri }`.
2. Start 9Router callback listener on port 1455:
   `GET http://127.0.0.1:20128/api/oauth/codex/start-proxy?app_port=1455&state=<state>&code_verifier=<verifier>&redirect_uri=http://localhost:1455/auth/callback`

### Step 2: Navigate in GPM Profile (Per-Account Proxy)
1. Start GPM profile via GPM Local API (`/api/v3/profiles/start/<pid>?win_scale=0.8`).
2. Connect Playwright over CDP to the profile's remote debugging port.
3. Navigate page to `authUrl`.

### Step 3: Handle Login & Multi-Stage OpenAI Forms
1. **Email Step**: Fill email into `input[type="email"]`, click `Tiếp tục` / `Continue`.
2. **OTP Step (Microsoft Graph API)**:
   - OpenAI sends 6-digit verification code to the Hotmail mailbox.
   - Fetch the code via Microsoft Graph API (`https://graph.microsoft.com/v1.0/me/messages?$top=5&$orderby=receivedDateTime desc`) using the account's OAuth refresh token + client ID.
   - Fill the 6-digit code into `input[name="code"]` / `input[autocomplete="one-time-code"]`, submit.
3. **Deactivation & Phone Gate Detection**:
   - If page displays `account_deactivated` ("Bạn không có tài khoản vì tài khoản đó đã xóa hoặc vô hiệu hóa"), mark as DIED and skip immediately. Do not retry or loop.
   - If page redirects to `/add-phone` or prompts "Cần có số điện thoại", mark as PHONE_GATE.
4. **Workspace Selection (Crucial)**:
   - OpenAI may prompt "Chọn một không gian làm việc" (Choose a workspace).
   - Click the "Tài khoản cá nhân" (Personal account) card, then click `Tiếp tục`.
5. **Consent / Authorization**:
   - Page redirects to `/sign-in-with-chatgpt/codex/consent` and automatically redirects back to `http://localhost:1455/auth/callback` with `code` and `state`.

### Step 4: Verify 9Router Poll Status & Bind Proxy Pool
1. Poll `GET http://127.0.0.1:20128/api/oauth/codex/poll-status?state=<state>`.
   When `status == 'done'`, 9Router creates a connection in `providerConnections` with `id: <connectionId>`.
2. Map Proxy in SQLite (`C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`):
   ```python
   # Locate proxy pool corresponding to the account's port
   pool_id = cur.execute("SELECT id FROM proxyPools WHERE data LIKE ?", (f"%{port}%",)).fetchone()[0]
   # Inject proxyPoolId into connection data
   conn_data = json.loads(cur.execute("SELECT data FROM providerConnections WHERE id = ?", (conn_id,)).fetchone()[0])
   conn_data.setdefault('providerSpecificData', {})
   conn_data['providerSpecificData']['proxyPoolId'] = pool_id
   cur.execute("UPDATE providerConnections SET data = ? WHERE id = ?", (json.dumps(conn_data), conn_id))
   conn.commit()
   ```

### Step 5: Test Verification
Verify inference using 9Router completion endpoint:
```python
req = urllib.request.Request('http://127.0.0.1:20128/v1/chat/completions', data=json.dumps({
    'model': 'gpt-5.6-luna', # or 'cx/gpt-5.6-luna'
    'messages': [{'role': 'user', 'content': 'Test'}],
    'stream': False
}).encode('utf-8'), headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
```

## 3. Fast Triage & Re-Auth Optimizations
### Zero-Browser Ban Pre-Check qua Microsoft Graph API
Thay vì khởi động browser Playwright cho từng tài khoản bị 401/revoked rồi mới phát hiện `account_deactivated`, có thể kiểm tra hòm thư Hotmail O(1) qua Microsoft Graph API trước:
```python
# Gọi Graph API đọc 10 email gần nhất:
res = requests.get('https://graph.microsoft.com/v1.0/me/messages?$top=10&$select=subject,receivedDateTime,from', 
                   headers={'Authorization': f'Bearer {access_token}'}, timeout=8)
msgs = res.json().get('value', [])
is_banned = any('vô hiệu hóa' in (m.get('subject') or '').lower() or 'deactivated' in (m.get('subject') or '').lower() for m in msgs)
```
- Nếu hòm thư nhận được thông báo từ OpenAI Trust & Safety (`trustandsafety@tm.openai.com`) với tiêu đề:
  `OpenAI - Truy cập bị vô hiệu hóa [C-...]`
  -> Tài khoản đã bị OpenAI khóa vĩnh viễn (`account_deactivated`). Đánh dấu `BANNED` ngay lập tức, bỏ qua và không mở browser hay chờ OTP.

### Chuẩn hóa Khởi tạo & Chữ ký hàm `MicrosoftGraphOTPProvider`
Khi dùng class `MicrosoftGraphOTPProvider` từ `chatgpt_gpm_direct_reg.py`:
- `__init__(client_id, refresh_token)`: **KHÔNG** truyền keyword argument `email` (gây `TypeError: unexpected keyword argument 'email'`).
- `fetch_otp(received_after=start_t)`: Sử dụng tham số `received_after`, **KHÔNG** dùng `since` (gây `TypeError: unexpected keyword argument 'since'`).

### Xử lý luồng Password-First trước OTP
Sau khi điền email, nếu OpenAI điều hướng sang `https://auth.openai.com/log-in/password`:
- Lấy password từ workbook `taikhoan_dat_v2_updated.xlsx` (`get_pass_chatgpt_from_updated_workbook(email)` hoặc `get_password_for_email(email)`).
- Điền vào `input[type="password"]` và Enter để chuyển sang bước `email-verification` (OTP) hoặc phát hiện `account_deactivated`.

### Hermes Session Storage `state.db` Lock / Busy Timeout Mitigation
Khi `state.db` của Hermes phình to (>14 GB) và nhiều tiến trình cùng ghi vào WAL:
- Hermes có thể văng lỗi: `"⚠️ No reply: the turn was stopped because session storage could not be written (often a full disk — free some space or fix state.db permissions)"`.
- Thực tế ổ đĩa chưa đầy, mà do SQLite chạm `busy_timeout` (3s).
- **Khắc phục an toàn O(1):** Chạy `PRAGMA wal_checkpoint(PASSIVE)` bằng script Python để xả log WAL về database chính và giải phóng lock ngay lập tức mà không block độc quyền phiên làm việc.

## 4. Pitfalls & Anti-Patterns
- **CẤM LÔI POOL WEB THAY THẾ (INVARIANT)**: Khi User yêu cầu nạp OAuth tài khoản Codex vào 9Router, CẤM TUYỆT ĐỐI tự ý chuyển hướng hoặc đề xuất dùng pool web (`chatgpt-web` / `cgpt-web`) của OmniRoute để thoái thác hay làm thay thế mục tiêu. Phải kiên trì giải quyết đúng mục tiêu nạp đủ số lượng account Codex vào 9Router.
- **TÁI SỬ DỤNG KHO ACC ĐÃ VER SỐ TỪ OMNIROUTE**: Khi gặp Phone Gate (yêu cầu SMS) hoặc 5SIM hết tiền, BẮT BUỘC áp dụng quy trình trích xuất, giải mã và nạp kho tài khoản Codex đã từng ver số từ OmniRoute sang 9Router (chi tiết tại `references/omniroute-to-9router-codex-migration.md`), sau đó xóa tài khoản bị deactive khỏi DB và giữ nguyên profile GPM.
- **Yêu cầu Stream bắt buộc trên Codex API**: Khi gửi probe request trực tiếp lên `https://chatgpt.com/backend-api/codex/responses`, bắt buộc phải set `"stream": true`. Nếu set `false`, OpenAI trả lỗi `400 {"detail":"Stream must be set to true"}`.
- **Form submission sequencing**: On the workspace screen ("Chọn một không gian làm việc"), clicking the card alone does not submit; you must click both the card AND the "Tiếp tục" button.
- **Proxy leak prevention**: Never test tokens with direct requests without proxy; OpenAI instantly flags and revokes access tokens if accessed directly from home IP while registered under a datacenter/mobile proxy.
- **Fail fast on account_deactivated**: Do not retry password or loop OTP when encountering `account_deactivated` or Phone Verification gate. Skip and advance to next GPM candidate immediately.
