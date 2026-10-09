# TikTok 2FA: Chuyển Sang Trình Xác Thực (TOTP) Né Chờ Email OTP

## 1. Vấn đề
- Khi đăng nhập tài khoản TikTok đã kích hoạt 2FA, app TikTok thường mặc định hiển thị phương thức **Xác minh qua Email** ("Sử dụng liên kết này hoặc nhập mã được gửi đến a***r@hotmail.com").
- Nếu email là hotmail không có OAuth token hoặc mail về chậm, việc chờ email OTP rất dễ gây timeout / nghẽn luồng.

## 2. Giải pháp chuyển sang Trình xác thực (Authenticator TOTP)
Nếu tài khoản có lưu trữ chuỗi khóa bí mật 2FA (Secret Key, ví dụ: `25QTIRIDTZZHO6FDAJIO4BV4SHSW6B6T`):
1. **Bấm "Sử dụng phương thức khác"**:
   - Resource-ID: `com.ss.android.ugc.trill:id/dwe`
   - Text: `Sử dụng phương thức khác` (tọa độ khoảng `(399, 1039)`).
2. **Chọn "Trình xác thực"**:
   - Resource-ID: `com.ss.android.ugc.trill:id/a6d`
   - Text: `Trình xác thực` (tọa độ khoảng `(540, 1662)`).
3. **Màn hình Nhập mã Ứng dụng xác thực**:
   - Sinh mã 6 số mới nhất bằng Python:
     ```python
     import pyotp
     code = pyotp.TOTP(secret).now()
     ```
   - Node nhập mã: `EditText` (tọa độ center khoảng `(540, 738)`).
   - Nhập mã vào ô bằng `input text <code>`.
4. **Bấm nút "Tiếp tục"**:
   - Resource-ID: `com.ss.android.ugc.trill:id/fmw`
   - Tọa độ chính xác: `(540, 1806)` (Bounds: `[96, 1728][984, 1884]`).
   - *Lưu ý*: Nút Tiếp tục ở màn hình này nằm sát đáy `y=1806`, không phải `y=1681`.
5. **Nghiệm thu**:
   - Màn hình chuyển vào trang cá nhân hoặc Feed của tài khoản.
