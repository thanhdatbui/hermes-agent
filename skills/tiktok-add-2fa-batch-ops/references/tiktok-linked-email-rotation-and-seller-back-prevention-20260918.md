# TikTok Linked Email Rotation & Seller Back Prevention (2026-09-18)

## 1. Bản chất: Add 2FA TikTok Không Gỡ Liên Kết Email Gốc
- **Cơ chế TikTok:** Thêm 2FA Authenticator (TOTP) là bổ sung thêm lớp bảo mật, KHÔNG PHẢI gỡ bỏ Email liên kết của tài khoản.
- **Tài khoản No-phone bị chặn tắt 2FA Email:**
  - Trên TikTok v46+, với tài khoản chưa liên kết SĐT, server TikTok bắt buộc giữ lại 1 kênh liên lạc khôi phục (Email).
  - Dù script bấm `Xóa` email trong bảng 2FA và bấm `Xác nhận`, TikTok ném Toast: *"Không thể thay đổi cài đặt vì lý do bảo mật, hãy thử lại sau"* và trạng thái vẫn giữ `Email: Bật`.
  - **Quy tắc vận hành:** Không ép script phải tắt bằng được 2FA Email (tránh văng lỗi `EMAIL_DISABLE_NOT_STABLE`). Chỉ cần `Trình xác thực: Bật` + `Mật khẩu TikTok mạnh: Bật` là tài khoản an toàn tuyệt đối khi đăng nhập.

## 2. Nguy cơ Bị Back & Giải Pháp Chuẩn Bị Bán Cho Khách
- **Nguy cơ thực tế:** Mối đe dọa bị back tài khoản không nằm ở TikTok, mà nằm ở **Bên bán Hotmail** vì họ nắm giữ mật khẩu gốc / token / session cũ.
- **Trường hợp 1 — Hotmail sạch (không có recovery email lạ):**
  - **Luồng đổi pass chuẩn:** Đổi mật khẩu trên Chrome (qua Proxy máy S7) $\rightarrow$ Gỡ mail khôi phục rác $\rightarrow$ Bấm **"Đăng xuất khỏi mọi thiết bị" (Sign out everywhere)**.
  - Sau khi Sign out everywhere, toàn bộ session và token cũ của bên bán bị hủy 100%.
  - Cập nhật Pass mới vào Cột G Excel (`PASS_MAIL`).
  - Đăng nhập vào App Outlook trên điện thoại bằng Pass mới.
- **Trường hợp 2 — Hotmail cũ dính recovery email không truy cập được (vd: `khoale`):**
  - Khi Microsoft bắt OTP từ recovery email cũ để vào trang đổi pass, KHÔNG mất thời gian đi tìm / nhờ lấy mã.
  - **Giải pháp dứt điểm:** Đổi thẳng Email liên kết trên TikTok sang Hotmail mới mua qua API!

## 3. Quy Trình Đổi Email Liên Kết TikTok Sang Hotmail Mới (By-pass Mail Cũ)
1. **Mua Hotmail mới qua API:**
   - Chạy `python D:/Taadaa/tools/buy_hotmail.py --buy 1 --target-file <path>`.
   - Lấy `email|pass|refresh_token|client_id`. Token Graph API được verify live ngay lập tức.
2. **Vào màn Đổi Email trên TikTok:**
   - Điều hướng: `Hồ sơ` $\rightarrow$ Menu 3 gạch $\rightarrow$ `Cài đặt và quyền riêng tư` $\rightarrow$ `Tài khoản` $\rightarrow$ `Thông tin người dùng` $\rightarrow$ `Email` $\rightarrow$ `Thay đổi email`.
3. **Vượt gate danh tính bằng TOTP 2FA (Không cần mail cũ):**
   - Sinh mã 6 số từ **Secret Key TOTP (Cột E Excel)**:
     ```python
     import pyotp
     code = pyotp.TOTP(secret_2fa.strip()).now()
     ```
   - Nhập mã TOTP vào TikTok để mở khóa form nhập Email mới.
4. **Nhập Hotmail mới & Xác nhận OTP:**
   - Điền địa chỉ Hotmail mới vào ô input $\rightarrow$ Bấm "Gửi mã".
   - Script gọi Microsoft Graph API đọc mã xác minh 6 số gửi về Hotmail mới trong 3-5s $\rightarrow$ Điền vào TikTok để hoàn tất liên kết.
5. **Cập nhật Excel:**
   - Cập nhật Cột F (Email) và Cột G (Pass Mail) của dòng tương ứng trong file `taikhoan_dat_v2_updated .xlsx`.

## 4. Triage Lỗi Subagent Timeout 600s Do Zombie `app_process`
- **Hiện tượng:** Worker subagent chạy tác vụ UI tự động hóa trên Android bị kẹt timeout 600s không có log kết quả.
- **Root Cause:** Thiết bị tồn tại tiến trình zombie `app_process` chạy ngầm chiếm độc quyền `UiAutomationService`. Khi đó mọi lệnh `uiautomator dump` từ Python hoặc ADB đều bị treo cứng vô hạn.
- **Quy trình phục hồi O(1):**
  ```bash
  adb shell "pkill -f app_process; killall app_process; am force-stop com.github.uiautomator"
  ```
  Sau khi kill, chạy thử `adb shell "uiautomator dump /sdcard/ui.xml"` để đảm bảo dump trả về XML bình thường (< 2s) trước khi dispatch worker.
