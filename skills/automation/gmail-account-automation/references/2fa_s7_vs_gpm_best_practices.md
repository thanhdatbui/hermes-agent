# Bật 2FA Google: S7 on-device vs GPM Chrome (Thực tế thực nghiệm 2026)

## 1. Hiện tượng & Nghịch lý thực tế
Trong vận hành farm, có thắc mắc thường gặp:
- *"Tại sao bảo phải bật 2FA trên điện thoại trước khi đưa lên GPM, nhưng thực tế làm trên S7 thì lỗi mà lên GPM lại bật được?"*

### Bản chất cơ chế bảo mật của Google (App Session vs Web Security Session)
1. **Trên điện thoại Android (Samsung S7) qua ADB:**
   - App Gmail / Cài đặt tài khoản Google trên Android dùng OAuth Token cấp di động.
   - Khi bấm vào mục **"Xác minh 2 bước" (2-Step Verification)**: Google **BẮT BUỘC mở một cửa sổ WebView bảo mật** riêng biệt.
   - Cửa sổ WebView này đối với Google là một phiên mới hoàn toàn (chưa có cookie duyệt web trước đó). Khi phát hiện môi trường IP Proxy 4G farm hoặc thiết bị cũ, Google kích hoạt ngay cờ rủi ro:
     - Hiện **reCAPTCHA xác minh danh tính** ("Xác nhận bạn không phải là rô-bốt").
     - Hoặc chặn thẳng: *"Không thể đăng nhập cho bạn. Google không thể xác minh rằng tài khoản này là của bạn..."*.
   - Trên S7 qua ADB, **không có extension hay cơ chế giải audio reCAPTCHA tự động**, dẫn đến luồng bật 2FA on-device bị tắc tử 100%.

2. **Trên GPM Chrome (PC qua Playwright CDP):**
   - Profile GPM khi mở lên mang đầy đủ chuỗi cookie web sống (`SID`, `SSID`, `HSID`, `__Secure-3PSID`...) và Fingerprint Chrome máy tính hoàn chỉnh.
   - Khi điều hướng tới `https://myaccount.google.com/two-step-verification/authenticator`:
     - Nếu Google đòi xác nhận mật khẩu (`challenge/pwd`): Playwright tự động điền mật khẩu từ file Excel.
     - Nếu Google bật reCAPTCHA (`challenge/recaptcha`): Script `run_add_2fa_remaining.py` đã tích hợp sẵn module `solve_recaptcha_audio(page)` giải captcha âm thanh tự động.
     - Playwright bấm "Không thể quét mã", bóc chuỗi Secret Key Base32 (32 ký tự), sinh mã TOTP chuẩn True UTC và hoàn tất xác minh trong ~30-45 giây.

---

## 2. Quy trình chuẩn cho toàn Farm (Best Practice)
1. **Reg Gmail / Nuôi S7:**
   - Tạo Gmail trên S7 và ngâm nuôi tài khoản.
2. **Đưa lên GPM PC:**
   - Tạo profile GPM gắn **ĐÚNG PROXY 4G CỦA MÁY S7 ĐÓ** (ví dụ Máy 5 gắn `test.taadaa.click:5105`).
   - Mở profile GPM để đăng nhập Google (hoặc kiểm tra cookie sống).
3. **Bật 2FA:**
   - Chạy script qua GPM: `python "D:/Taadaa/GPM auto/scripts/run_add_2fa_remaining.py"`.
   - Script tự động giải reCAPTCHA, lấy Secret Key, tính OTP, kích hoạt 2FA và đồng bộ vào `gmail_clean_v2.xlsx` + `master_gmail_manager.xlsx`.
4. **Kết quả:**
   - Tài khoản có 2FA Secret Key + phiên GPM sống sẽ miễn nhiễm hoàn toàn với checkpoint đòi SMS số điện thoại khi đăng nhập OpenAI / ChatGPT hay các dịch vụ khác.

---

## 3. Pitfalls & Tránh sai lầm
- **CẤM cố gắng tự động hóa bấm bật 2FA trực tiếp trên Samsung S7 qua ADB:** Luôn gặp màn hình chặn reCAPTCHA không thể giải tự động.
- **CẤM dùng proxy khác dải khi đưa lên GPM:** Profile GPM phải dùng đúng cổng proxy gán cho máy S7 đó để giữ nguyên độ trust IP.
