# Hotmail Change Info: Recovery Email & 2FA Flow (2026-10-12)

## 1. Đính chính thực tế: Microsoft KHÔNG bắt buộc có Mail khôi phục để bật 2FA
- **Sự thật kỹ thuật:** Microsoft cho phép thiết lập ứng dụng xác thực (Authenticator App / TOTP Secret Key) **TRỰC TIẾP** ngay trên tài khoản Zin trắng chỉ có mật khẩu. Mật khẩu là yếu tố 1, Authenticator App là yếu tố 2.
- Việc trước đây tưởng Microsoft bắt buộc có mail khôi phục là do script cũ `gpm_change_hotmail_security.py` tự chặn cứng (`if not rec_email: return False`) gây ra lỗi `BLOCKED` giả.
- **Chỉ thị của User (2026-10-12):** Bỏ hẳn bước add mail khôi phục trong luồng `CHANGE_INFO`, đi thẳng vào thiết lập 2FA Authenticator TOTP. Điều này giúp loại bỏ 100% sự phụ thuộc vào bên thứ 3 (API domain tạm `fviainboxes.com`), chạy nhanh gấp 3 lần và hoàn toàn không lo nghẽn mạng hay trễ OTP.

## 2. Thứ tự thực thi chuẩn tinh gọn (Đi thẳng vào 2FA)
Không cần ngâm thêm. Thực hiện tuần tự trong cùng 1 phiên:
1. **Thiết lập 2FA Authenticator (TOTP) trực tiếp:**
   - Click "Thêm một cách đăng nhập khác cho tài khoản" (`button:has-text('Thêm một cách đăng nhập khác cho tài khoản')`).
   - Chọn "Sử dụng ứng dụng" -> Chọn "Tôi muốn sử dụng ứng dụng xác thực khác" (`#iSelectProofTypeAlternate`).
   - Bấm tiếp theo -> Chọn hiển thị secret key dạng text (`#iShowPlainLink`).
   - Bóc Secret Key (16 ký tự Base32) -> Lưu vào Cột 4 của `gmail_clean_v2.xlsx`.
   - Sinh mã TOTP 6 số bằng `pyotp` -> Điền vào `#iTOTPField` và xác nhận.
   - Điều hướng tới `https://account.live.com/proofs/EnableTfa` để bật công tắc Two-step verification tổng.
2. **Đổi mật khẩu mới:**
   - Điều hướng `https://account.live.com/password/change` -> Nhập mật khẩu hiện tại -> Điền mật khẩu mới (chuỗi 14 ký tự ngẫu nhiên) -> Submit.
3. **Đăng xuất khỏi mọi nơi (Sign out everywhere):**
   - Quay lại trang `proofs` -> Click `#DeleteTrustedDevices` -> Xác nhận dialog "Đăng xuất" để hủy mọi phiên cũ toàn cầu.
4. **Đăng nhập lại (Relogin & KMSI):**
   - Điều hướng `https://login.live.com` -> Điền email + mật khẩu mới.
   - Nếu Microsoft đòi mã 2FA -> Dùng Secret Key vừa lưu sinh mã TOTP điền vào.
   - Bấm "Có" tại màn hình Duy trì đăng nhập (KMSI) để lưu phiên sống bền vững trên profile GPM.

## 3. Pitfall: Bấm nhầm nút Tiếp theo của Form
- Trong hàm `handle_microsoft_interstitials` (xử lý màn hình điều khoản/KMSI): BẮT BUỘC bỏ qua kiểm tra nút "Tiếp theo" khi URL đang chứa `proofs` (`if "proofs" in page.url.lower(): pass`).
- Nếu không kiểm tra URL, bot sẽ tưởng nút "Tiếp theo" của form proofs là màn hình điều khoản và click trước khi điền dữ liệu, gây lỗi submit rỗng.

## 4. Đóng tab Chrome CDP
- Đóng tab qua CDP endpoint `/json/close/{target_id}` chỉ giải phóng RAM render, hoàn toàn không mất cookies hay session đăng nhập do toàn bộ session được Chrome lưu bền vững trên ổ đĩa Profile.
