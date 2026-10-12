# Hotmail Change Info: Recovery Email & 2FA Flow (2026-10-12)

## 1. Bản chất bảo mật Microsoft đối với Nick Zin
- Với tài khoản Zin trắng (chỉ có password ban đầu): Microsoft bắt buộc phải có ít nhất 2 phương thức bảo mật hợp lệ mới cho phép bật Two-step verification (2FA).
- Cần add Mail khôi phục trước để tài khoản đủ điều kiện bật 2FA.

## 2. Thứ tự thực thi chuẩn trong cùng 1 phiên CHANGE_INFO
Không cần ngâm thêm sau khi add mail khôi phục. Thực hiện tuần tự trong cùng 1 phiên:
1. **Kiểm tra phương thức sẵn có:**
   - Nếu trang `account.live.com/proofs/Manage` đã có thẻ "Gửi mã qua email" hoặc địa chỉ mail khôi phục trong body text -> **BỎ QUA** bước add mail khôi phục, chuyển thẳng sang Bước 2.
2. **Add Mail khôi phục (nếu chưa có):**
   - Click "Thêm một cách đăng nhập khác cho tài khoản" (`button:has-text('Thêm một cách đăng nhập khác cho tài khoản')`).
   - Chọn "Gửi mã qua email" (`text='Gửi mã qua email'`).
   - Điền địa chỉ domain tạm: `<username_clean><3_random_chars>@fviainboxes.com` (TUYỆT ĐỐI KHÔNG dùng email cá nhân `thanhdatbui...` vì tài khoản sau này để bán).
   - Submit nhận OTP -> Gọi API `https://fviainboxes.com/messages?username=...` bóc OTP 6 số -> Điền OTP và hoàn tất xác nhận.
3. **Thiết lập 2FA Authenticator (TOTP):**
   - Click thêm phương thức -> Chọn "Sử dụng ứng dụng" -> Chọn "Tôi muốn sử dụng ứng dụng xác thực khác" (`#iSelectProofTypeAlternate`).
   - Bấm tiếp theo -> Chọn hiển thị secret key dạng text (`#iShowPlainLink`).
   - Bóc Secret Key -> Sinh mã TOTP 6 số -> Điền vào `#iTOTPField` và xác nhận.
   - Điều hướng tới `https://account.live.com/proofs/EnableTfa` để bật công tắc Two-step verification tổng.
4. **Đổi mật khẩu mới:**
   - Điều hướng `https://account.live.com/password/change` -> Đổi mật khẩu mạnh.
5. **Đăng xuất khỏi mọi nơi (Sign out everywhere).**

## 3. Pitfall: Bấm nhầm nút Tiếp theo của Form
- Trong hàm `handle_microsoft_interstitials` (xử lý màn hình điều khoản/KMSI): BẮT BUỘC bỏ qua kiểm tra nút "Tiếp theo" khi URL đang chứa `proofs` (`if "proofs" in page.url.lower(): pass`).
- Nếu không kiểm tra URL, bot sẽ tưởng nút "Tiếp theo" của form proofs là màn hình điều khoản và click trước khi điền dữ liệu, gây lỗi submit rỗng.

## 4. Đóng tab Chrome CDP
- Đóng tab qua CDP endpoint `/json/close/{target_id}` chỉ giải phóng RAM render, hoàn toàn không mất cookies hay session đăng nhập do toàn bộ session được Chrome lưu bền vững trên ổ đĩa Profile.
