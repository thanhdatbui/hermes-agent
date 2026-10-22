# Google AI Pro: Bypass Thử Thách 403 QR Qua Standard OAuth Re-Auth & Chuẩn Hóa AGY CLI Sandbox

## 1. Bản Chất Sự Cố Upstream 403 VALIDATION_REQUIRED Sau Khi Lên Pro
Khi tài khoản Google vừa kích hoạt thành công gói Google One / Gemini Pro (hoặc link Google AI Pro Family 5TB):
- Lần đầu tiên gọi API Antigravity (`daily-cloudcode-pa.googleapis.com`), Google Cloud Code backend thường chặn lại với mã:
  ```json
  403 PERMISSION_DENIED: "Verify your account to continue." (reason: "VALIDATION_REQUIRED")
  ```
- URL xác minh (`validation_url`) dẫn đến thử thách thiết bị IAP dạng mã QR: `https://accounts.google.com/v3/signin/challenge/iap/qrcode?TL=...`.

### Các cạm bẫy khi cố giải thử thách QR:
1. **Lỗi 500 khi mở link trên điện thoại/máy khác:** Chuỗi tham số `plt=` trong URL xác minh được ký mã hóa và ràng buộc chặt chẽ với IP/fingerprint của trình duyệt desktop vừa gửi yêu cầu. Mở trên thiết bị khác sẽ bị Google từ chối với lỗi `500. That's an error`.
2. **Đứt luồng đồng bộ thời gian thực (Broken Handshake):** Trình duyệt GPM trên máy tính bắt buộc phải giữ mở tab QR trong suốt quá trình quét. Nếu GPM bị đóng hoặc tab bị tắt trước/trong khi quét, handshake WebSocket/long-poll bị ngắt, điện thoại báo lỗi và Google không nhả tài khoản.
3. **Lệch tài khoản đăng nhập trên điện thoại:** Nếu điện thoại của người quét đang đăng nhập tài khoản Google khác, việc quét mã sẽ bị lỗi mismatch tài khoản.

---

## 2. Kỹ Thuật Đột Phá: Bypass Thử Thách QR Qua Standard OAuth Re-Auth
Thay vì cố gắng quét mã QR điện thoại, giải pháp sạch và tự động 100% là **chạy lại luồng OAuth cấp quyền chuẩn (Standard OAuth Authorization Flow)** trực tiếp trên GPM profile:

1. **Khởi chạy luồng cấp mã từ OmniRoute:**
   - Gọi `http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri=http://127.0.0.1:20129/callback`.
   - Lấy `authUrl`, `codeVerifier`, `state`.
2. **Điều hướng trên GPM Profile đang mở sẵn:**
   - Dùng Playwright CDP kết nối vào GPM profile (ví dụ `reauth_quyphuoc_gpm.py`).
   - Tự động click Account Chooser (chọn đúng email mục tiêu).
   - Tự động click bypass cảnh báo bảo mật của Google (`button:has-text("Đăng nhập")` hoặc `"Sign in"`).
   - Tự động giải TOTP 2FA nếu Google yêu cầu (đọc bí mật từ `master_gmail_manager.xlsx`).
   - Bắt Authorization Code từ URL chuyển hướng `/callback?code=4/0AX...`.
3. **Kết quả:**
   - Luồng Standard OAuth này **hoàn toàn không kích hoạt thử thách QR IAP**.
   - OmniRoute nhận `code`, đổi thành công Token mới (`HTTP 200 OK`).
   - Gỡ sạch cờ 403 `VALIDATION_REQUIRED`, tài khoản được Google nâng cấp hạn mức Pro ngay lập tức.

---

## 3. Kích Hoạt Nhận Diện Quota Gemini Advanced Qua Web (Warm-up Invariant)
Sau khi lên Pro, backend Cloud Code đôi khi chưa kích hoạt ngay hạn mức model Pro cho đến khi:
1. Mở GPM profile vào `https://gemini.google.com`.
2. Xác nhận điều khoản AI (Terms of Service) nếu có banner.
3. Mở dropdown mô hình chọn `Gemini 3.1 Pro (Suy luận nâng cao)` hoặc `Gemini 4 Argon (Nhiệm vụ phức tạp)` và gửi 1 câu chat test thử.
4. Thao tác này kích hoạt đầy đủ entitlement của Google AI Pro trên tài khoản.

---

## 4. Chuẩn Hóa Cấu Hình Sandbox AGY CLI & Khắc Phục 429 Ảo Do Thiếu `google_accounts.json`

### Cạm bẫy Quota 429 Ảo:
Khi khởi tạo thư mục sandbox `D:\Taadaa\agy_profiles\acc_XX\.gemini\`:
- Nếu chỉ tạo `oauth_creds.json`, `settings.json`, và `projects.json` mà thiếu `google_accounts.json`:
  - `agy.exe` (Antigravity IDE binary) không xác định được tài khoản active của sandbox.
  - `agy.exe` âm thầm fallback về credentials mặc định của host tại `C:\Users\Kibe\.gemini\`.
  - Nếu token của host đang chạm trần quota (báo `Resets in 32h`), `agy.exe` sẽ ném lỗi `RESOURCE_EXHAUSTED 429: Individual quota reached`, làm Coordinator tưởng nhầm tài khoản Pro mới bị hết quota!

### Bộ 5 file bắt buộc trong sandbox `.gemini/`:
1. `google_accounts.json`: Bắt buộc phải có `{"active": "<email>", "old": []}`.
2. `oauth_creds.json`: `access_token`, `refresh_token`, `token_type: "Bearer"`, `scope`.
3. `settings.json`: `{"security": {"auth": {"selectedType": "oauth-personal"}}}`.
4. `projects.json`: Mapping thư mục dự án (`{"projects": {"d:\\taadaa": "taadaa", ...}}`).
5. `state.json`: Metadata khởi động tránh modal warning.

**Cách triển khai chuẩn:** Luôn chạy `D:/Taadaa/tools/setup_agy_profile_creds.py` sau khi thêm profile vào `PROFILES_MAP` để tự động đồng bộ đủ cả 5 file từ OmniRoute SQLite DB.
