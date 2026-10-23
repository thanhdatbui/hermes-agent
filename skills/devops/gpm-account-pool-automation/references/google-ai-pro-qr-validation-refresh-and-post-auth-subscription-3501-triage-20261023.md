# Google AI Pro: Tái Sinh Link QR VALIDATION_REQUIRED (plt Token TTL) & Khắc Phục Lỗi 403 SUBSCRIPTION_REQUIRED (#3501) Sau Khi Quét (2026-10-23)

## 1. Sự Cố & Cạm Bẫy Thời Hạn plt= (Token TTL Expiry)
Khi tài khoản Google One / Gemini Pro mới nâng cấp bị Google tạm giữ để xác minh thiết bị qua lỗi 403 `VALIDATION_REQUIRED`:
- Tham số `plt=...` trong `validation_url` là **one-time token có thời hạn cực ngắn (~2-3 phút)**.
- Nếu người dùng mở quét chậm, Google chuyển hướng sang trang báo lỗi:
  ```text
  Bạn chưa đăng nhập. Phiên của bạn đã kết thúc vì không có hoạt động. Hãy thử đăng nhập lại.
  ```
- **Cạm bẫy đóng trình duyệt Playwright:** Khi dùng Playwright CDP kết nối vào GPM profile để điều hướng, TUYỆT ĐỐI CẤM gọi `browser.close()` vì sẽ đóng cửa sổ trình duyệt Chromium của GPM, làm mất màn hình QR trên desktop và đứt luồng đồng bộ thời gian thực (Live Handshake). Chỉ ngắt kết nối Playwright context.

---

## 2. Kỹ Thuật Tái Sinh validation_url Tươi Tức Thì
Khi link cũ bị hết hạn hoặc người dùng yêu cầu "mở lại link đi":
1. **Bắn 1 request Antigravity chuẩn trực tiếp qua proxy mobile của profile:**
   - Endpoint: `POST https://daily-cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse`
   - Headers: `Authorization: Bearer <access_token>`, `Content-Type: application/json`
   - Proxy: HTTP proxy tương ứng của profile (vd: `http://mobi22:***@test.taadaa.click:5122`)
   - Payload:
     ```json
     {
       "project": "aicode-consumers",
       "model": "gemini-3.8-flash-tiered",
       "request": {
         "contents": [{"role": "user", "parts": [{"text": "hi"}]}]
       }
     }
     ```
2. **Bóc tách `validation_url` mới:**
   - Google Cloud Code lập tức trả về HTTP 403 `VALIDATION_REQUIRED` kèm một chuỗi `plt=` mới tinh trong `error.details[0].metadata.validation_url`.
3. **Điều hướng trên GPM Profile đang mở:**
   - Kết nối Playwright CDP vào cổng GPM (`remote_debugging_address`).
   - `page.goto(fresh_validation_url, wait_until='domcontentloaded')`.
   - Chụp ảnh full màn hình và crop cận cảnh mã QR, soi mắt bằng WinRT OCR xác nhận trước khi gửi `MEDIA:`.

---

## 3. Cạm Bẫy 403 SUBSCRIPTION_REQUIRED (#3501) Sau Khi Quét QR Thành Công
Sau khi người dùng quét mã QR bằng camera điện thoại và màn hình máy tính hiển thị:
```text
Authentication successful | Gemini Code Assist
The authentication was successful, and the following products are now authorized to access your account:
- Gemini Code Assist
- Cloud Code with Gemini Code Assist
- Gemini CLI
- Antigravity (see Plans for availability)
```
- **Hiện tượng:** Nếu lập tức gửi request gọi model với token cũ, Google Cloud Code backend vẫn trả về lỗi:
  ```json
  {
    "code": 403,
    "message": "You do not have a valid license of this product. Please contact your administrator to request a license. If you are not an enterprise user and believe you are receiving this message as an error, please try using the latest version and logging in again. (#3501)",
    "status": "PERMISSION_DENIED",
    "details": [{"reason": "SUBSCRIPTION_REQUIRED", "domain": "cloudcode-pa.googleapis.com"}]
  }
  ```
- **Bản chất:** Token cũ được sinh ra từ thời điểm tài khoản còn là Free Tier (chưa có quyền Pro). Dù Google One đã có 5 TB và quét QR xong, token cũ không tự động mang claim Pro cho dịch vụ Antigravity/Code Assist.

---

## 4. Quy Trình Khép Kín Cấp Mới Token & Nghiệm Thu 200 OK (Post-QR Fresh OAuth Handshake)
Ngay khi người dùng quét QR thành công:
1. **Khởi tạo luồng OAuth từ OmniRoute:**
   - `GET http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri=http://127.0.0.1:20129/callback`
   - Thu thập `authUrl`, `codeVerifier`, `state`.
2. **Tự động điều hướng và bắt code trên GPM Profile:**
   - `page.goto(auth_url)`
   - Xử lý Account Chooser: Click vào tọa độ tài khoản mục tiêu (vd: `hakha18062003@gmail.com`).
   - Xử lý Security Warning: Click `button:has-text("Đăng nhập")`.
   - Bắt Authorization Code từ URL chuyển hướng `/callback?code=4/0AX...`.
3. **Đổi mã lấy Refresh Token Pro mới:**
   - `POST http://127.0.0.1:20129/api/oauth/antigravity/exchange` với `{code, redirectUri, codeVerifier, state}` $\rightarrow$ nhận `HTTP 200 OK`.
4. **Đồng bộ Dual-Pool:**
   - Cập nhật SQLite `provider_connections`: gán `tier: 'g1-pro-tier'`, `project_id: 'aicode-consumers'`, priority, rate_limit_protection.
   - Thêm vào combo `ag-gemini-pool-3` via `PUT /api/combos/:id`.
   - Chạy `setup_agy_profile_creds.py` để trích xuất token mới ra sandbox AGY CLI (`.gemini/`).
5. **Nghiệm thu cô lập (`isolated_chat_test`):**
   - Chạy `vm_rescue_lib.isolated_chat_test(connection_id)`.
   - Xác nhận HTTP 200 OK với model `gemini-3.8-flash-tiered` và `call_logs` ghi nhận `status == 200`, `error_summary IS NULL`.
   - Đóng dọn profile GPM qua Local API `/profiles/stop/:id`.
