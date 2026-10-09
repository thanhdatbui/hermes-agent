# TikTok Linked Email Migration via TOTP & Graph API (2026-09-18)

## 1. Mục tiêu & Cơ Chế
- Dành cho các tài khoản TikTok cổ hoặc tài khoản gắn với Hotmail cũ dính recovery email không truy cập được (vd: `khoaleemagic`).
- Không cần tốn thời gian lấy mã hay liên hệ chủ cũ: Thay đổi thẳng Email liên kết của TikTok sang Hotmail mới mua qua API.

## 2. Các Bước Thực Thi Chuẩn
1. **Mua Hotmail có Graph OAuth2 Token:**
   ```bash
   python D:/Taadaa/tools/buy_hotmail.py --buy 1 --target-file <path_to_txt>
   ```
   Định dạng: `email|pass|refresh_token|client_id`.
2. **Vào Cài đặt TikTok:**
   - Mở app `com.ss.android.ugc.trill` -> `Hồ sơ` -> Menu 3 gạch -> `Cài đặt và quyền riêng tư` -> `Tài khoản` -> `Thông tin người dùng` -> `Email` -> `Thay đổi email`.
3. **Bypass Xác minh danh tính bằng 2FA TOTP:**
   - TikTok yêu cầu xác nhận danh tính trước khi đổi mail.
   - Sinh mã TOTP 6 số từ **Secret Key 32 ký tự (Cột E Excel)** bằng `pyotp.TOTP(secret).now()`.
   - Nhập vào ô xác minh -> Vượt qua gate thành công mà không cần mail cũ.
4. **Nhập Hotmail mới & Xác nhận OTP:**
   - Nhập địa chỉ Hotmail mới vừa mua -> Bấm "Gửi mã".
   - Script gọi Microsoft Graph API (`https://graph.microsoft.com/v1.0/me/messages` với access_token sinh từ refresh_token) lấy mã OTP 6 số từ TikTok.
   - Điền OTP vào TikTok -> Hoàn tất đổi email.
5. **Cập nhật Excel:**
   - Ghi đè Email mới vào Cột F và Pass mail mới vào Cột G tại Row tương ứng trong `taikhoan_dat_v2_updated .xlsx`.

## 3. Pitfall Zombie `app_process` Treo uiautomator Dump 600s
- Khi dispatch worker chạy tự động hóa trên Android bị timeout 600s, nguyên nhân là do tiến trình zombie `app_process` chiếm độc quyền `UiAutomationService`.
- Lệnh dọn dẹp trước khi chạy:
  ```bash
  adb shell "pkill -f app_process; killall app_process; am force-stop com.github.uiautomator"
  ```
