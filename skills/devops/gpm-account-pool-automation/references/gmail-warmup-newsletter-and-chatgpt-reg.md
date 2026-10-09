# Warmup Luồng Thư Gmail Mới Reg & Đăng Ký ChatGPT

## 1. Cơ chế Warmup Inbound Mail sau khi Reg Gmail (S7)
- **Vị trí code**: `D:/Taadaa/tools/warmup_newsletter_services.py`, kích hoạt tự động qua hàm `persist_success_result(acc)` trong `gmail_reg_v10.py`.
- **Nguyên lý hoạt động**:
  - Gửi request HTTP POST subscribe email vào các dịch vụ tin tức/tech newsletter công khai uy tín (Cooperpress: Node Weekly, JavaScript Weekly, Ruby Weekly, Postgres Weekly, Frontend Focus; Hacker Newsletter...).
  - Các bên này lập tức gửi mail xác nhận / chào mừng (Inbound Welcome / Double Opt-in Mail) về hòm thư Gmail mới tạo.
  - Tạo lịch sử hoạt động ban đầu (activity history), tăng trust score cho hộp thư để chống checkpoint / hạn chế nhận OTP của Google.

## 2. Luồng Mở Rộng: Đăng ký ChatGPT / Login ChatGPT bằng Gmail mới
- **Mục đích**:
  - Tận dụng Gmail vừa reg để tạo tài khoản ChatGPT (OpenAI).
  - Tăng trust mạnh mẽ cho Gmail nhờ thư xác nhận từ corporate domain uy tín (`openai.com` / `auth0`).
  - Phục vụ cấp tài khoản ChatGPT cho pool AI / OmniRoute.

## 3. Thực Nghiệm & Đánh Giá Giữa Hai Tầng Triển Khai (S7 vs GPM)

### A. Tầng Thiết bị Android (S7) - Kết luận thực nghiệm Canary Máy 26/16:
- **App ChatGPT chính thức (APK)**: Không thể cài do yêu cầu tối thiểu Android 9.0+ (S7 chạy Android 8.0.0 API 26).
- **Trình duyệt Chrome trên S7**:
  - Proxy Mobi 4G vượt Cloudflare Turnstile mượt mà (3-5s).
  - **Blocker kỹ thuật (Root Cause)**: Khi tap vào tài khoản Google tại màn hình Google Account Chooser (`accounts.google.com`), Google Play Services của Android 8.0 bị xung đột Intent, văng sang trang Cài đặt tài khoản của Android (`com.android.settings.Settings$UserAndAccountDashboardActivity`) thay vì callback token OAuth về Chrome. Luồng bị đứt đoạn.
  - Xem chi tiết tại `references/s7-android8-chatgpt-oauth-limitation-and-workaround.md`.

### B. Tầng GPM / Browser Automation (Khuyến nghị chuẩn 100%):
- Không cần chờ ngâm 24h-48h (ngâm 24-48h chỉ áp dụng khi đổi bảo mật 2FA/SMS của Google). Đăng ký bên thứ 3 (OpenAI) qua Google OAuth có thể chạy ngay khi đưa Gmail lên profile.
- Đưa Gmail lên profile GPMLogin qua đúng proxy của máy đó.
- Dùng Playwright CDP điều khiển Chrome GPM click "Continue with Google" tại `https://chatgpt.com`.
- Trình duyệt Desktop Chrome xử lý callback OAuth hoàn hảo 100%, không bị văng intent như Android 8.0.
