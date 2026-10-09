# Audit Đối Soát Account ChatGPT & Tuổi Reg (GPM + OmniRoute + Targeted Logs)

## 1. Bản chất & Nguyên tắc cốt lõi
Khi audit kiểm kê kho tài khoản ChatGPT để lọc ứng viên đủ tuổi (>=48h) và chưa active Codex trên OmniRoute:
1. **Tuyệt đối không dùng mù `created_at` của GPM DB / Local API:**
   - Trong `profile_data.db` (bảng `Profiles`), trường `CreatedAt` phần lớn mang giá trị template/clone mặc định (ví dụ `2024-01-01 10:12:00` hoặc ngày clone profile hàng loạt).
   - Dùng `created_at` của GPM làm tuổi reg ChatGPT dẫn đến sai lệch 100% về độ tuổi tài khoản (false aging).
2. **Nguyên tắc Read-only Strict Invariant:**
   - Cấm mở browser profile hàng loạt (dẫn đến cascade freeze máy, đè port proxy và dính Cloudflare/reCAPTCHA).
   - Cấm quét đệ quy toàn bộ ổ đĩa (recursive disk scan across C:\ / D:\) làm cạn token và timeout. Chỉ kiểm tra các tệp log/manifest/workbook có địa chỉ rõ ràng.
   - Tuyệt đối không để lộ mật khẩu, auth tokens, session tokens, hoặc cookies trong bảng đối soát.

## 2. Các nguồn bằng chứng thực tế (Evidence Hierarchies)
Để xác định ngày/giờ đăng ký (hoặc lần đầu đăng nhập session ChatGPT thực tế) và độ tin cậy:
- **Tầng 1 (Direct Reg Log / Verification Screenshot - Độ tin cậy Cao Nhất / Ground Truth):**
  - File log: `D:/Taadaa/GPM auto/logs/chatgpt_gpm_direct_reg.log` (ghi nhận timestamp reg bằng email + OTP hoặc phát hiện ALREADY_LOGGED_IN khi submit email).
  - Screenshots checkpoint: `D:/Taadaa/GPM auto/debug_screenshots/chatgpt_direct_reg/<email>_step1_email_submitted.png` hoặc `D:/Taadaa/GPM auto/debug_screenshots/chatgpt_<email>_verified.png`.
  - Excel Manager: `D:/OneDrive/TaadaaData/kibe/master_gmail_manager.xlsx` (Cột Ghi chú có `CHATGPT_READY` kèm timestamp cập nhật cột 15).
- **Tầng 2 (Batch Run Logs & Report JSONs):**
  - `D:/Taadaa/GPM auto/logs/batch_chatgpt_5workers.log` (ghi nhận đợt Google SSO batch ngày `2026-09-13`).
  - `D:/Taadaa/GPM auto/logs/batch_chatgpt_web.log` (ngày `2026-09-14`).
  - `D:/Taadaa/GPM auto/logs/batch_chatgpt_web_perfected.log` (ngày `2026-09-15`).
  - `D:/Taadaa/GPM auto/logs/batch_dual_oauth.log` (từ `2026-09-20` đến `2026-09-24`).
- **Tầng 3 (SQLite Cookies Creation Timestamp - Read-only Chrome Database):**
  - File SQLite `Default/Network/Cookies` của profile: đọc trường `creation_utc` (microseconds tính từ 1601-01-01 UTC) của các cookie `__Secure-next-auth.session-token` hoặc `oai-did` sớm nhất.
  - *Lưu ý:* Session token có thể bị cập nhật lại (refreshed) gần đây nếu profile được mở lại, do đó nếu có log/screenshot cũ hơn thì log/screenshot là mốc reg gốc.
- **Tầng 4 (OmniRoute Connection State):**
  - Endpoint: `http://127.0.0.1:20129/api/providers`.
  - Kiểm tra `provider == "codex"`: phân định rõ `isActive: true` + `testStatus: "active"` (Đã có Codex active -> Loại trừ) vs `testStatus: "expired"` / `errorCode: 401.0` (Codex chết token).
  - Kiểm tra `provider == "chatgpt-web"`: ghi nhận connection ID và status (`active` vs `unavailable` vs `banned`).

## 3. Quy chuẩn phân loại ứng viên (Classification Schema)
- **ELIGIBLE (Đủ điều kiện):**
  - Tài khoản ChatGPT đã reg / có session xác minh $\ge 48\text{h}$ (timestamp $\le \text{Now} - 48\text{h}$).
  - Chưa từng có provider Codex active trên OmniRoute (hoặc Codex đã bị expired/banned/chưa từng thêm).
- **EXCLUDED - ACTIVE_CODEX (Loại trừ):**
  - Đã có provider Codex trên OmniRoute với `isActive: true` và `testStatus: "active"`.
- **EXCLUDED - AGE_UNDER_48H (Loại trừ):**
  - Bằng chứng reg ghi nhận trong vòng 48h qua (ví dụ mới reg hôm nay hoặc hôm qua qua `chatgpt_gpm_direct_reg.py`).
- **UNKNOWN_AGE (Cần bổ sung bằng chứng):**
  - Profile có session/cookie nhưng không có timestamp log/screenshot đối chiếu rõ ràng. Tuyệt đối không suy đoán từ GPM `created_at`.
