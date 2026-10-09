# ChatGPT-Web Session Refresh & OmniRoute Update Flow

## 1. Context & Architecture
OmniRoute manages `chatgpt-web` connections in `C:\Users\Kibe\.omniroute\storage.sqlite` under table `provider_connections`.
- `provider`: `'chatgpt-web'`
- `api_key`: Contains cookie string formatted as `name=value; name2=value2; ...`.
- OmniRoute Encryption: `src/lib/db/encryption.ts` supports AES-256-GCM (`enc:v1:<iv>:<ciphertext>:<tag>`) or plaintext fallback if `STORAGE_ENCRYPTION_KEY` is passthrough. When updating directly via SQLite, updating plaintext cookie string is safely handled by OmniRoute (it will use as-is or auto-encrypt depending on configuration).

## 2. Fast Step-by-Step Refresh Flow

### Bước 1: Mở profile GPM qua Local API
- Local API v3 endpoint: `http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`
- Trích xuất `remote_debugging_address` (hoặc port) từ JSON response.

### Bước 2: Kết nối CDP & Điều hướng Đăng nhập
- Kết nối Playwright/CDP tới endpoint debug của trình duyệt.
- Điều hướng tới: `https://chatgpt.com/auth/login_with?auth_provider=google`
- Chờ Google OAuth tự động hoàn tất hoặc click chọn đúng tài khoản Google trong session profile.
- Đợi chuyển hướng về URL đích `https://chatgpt.com/` (hoặc dashboard chat).

### Bước 3: Thu thập Cookie ChatGPT
- Lấy toàn bộ cookies qua CDP (`Network.getCookies` hoặc `context.cookies()`).
- Lọc các cookie thuộc domain `.chatgpt.com` / `chatgpt.com`.
- Tạo chuỗi cookie string chuẩn: `k1=v1; k2=v2; ...` (đặc biệt cần các session token như `__Secure-next-auth.session-token`, `cf_clearance`, etc.).

### Bước 4: Kiểm tra tính hợp lệ qua OmniRoute Validation Endpoint
- Gửi POST request tới: `http://127.0.0.1:20129/api/providers/validate`
```json
{
  "provider": "chatgpt-web",
  "apiKey": "<cookie_string>"
}
```
- Đảm bảo nhận được `{"valid": true}`.

### Bước 5: Cập nhật SQLite OmniRoute
- Kết nối tới `C:\Users\Kibe\.omniroute\storage.sqlite`:
```sql
UPDATE provider_connections
SET api_key = ?,
    is_active = 1,
    test_status = 'active',
    last_error = NULL
WHERE provider = 'chatgpt-web' AND name LIKE ?;
```

### Bước 6: Đóng Profile GPM
- Gọi API: `http://127.0.0.1:19995/api/v3/profiles/close/{profile_id}`
