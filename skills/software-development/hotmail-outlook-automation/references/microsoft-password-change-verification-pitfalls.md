# Microsoft Password Change & False-Positive Verification Pitfalls (GPM/Playwright)

## 1. Cạm bẫy False-Positive "Redirect = Đổi Pass Thành Công" (CHẾT NGƯỜI)
- **Hiện tượng**: Khi submit form đổi pass (`#UpdatePasswordAction`), Microsoft thường có 2 hành vi lừa script:
  1. Redirect về `account.live.com/password/change` với form trắng và kèm dòng thông báo: *"Tạm thời có lỗi với dịch vụ / There's a temporary problem with the service"*.
  2. Redirect về `account.microsoft.com/profile` hoặc trang tài khoản do profile browser còn giữ cookie đăng nhập cũ từ phiên trước.
- **Bẫy**: Script thấy URL là `account.microsoft.com/profile` hoặc HTTP 200 liền kết luận "Đã đổi pass thành công", sau đó ghi pass mới vào Excel và cập nhật state `DONE`.
- **Thực tế**: Microsoft **KHÔNG HỀ ĐỔI MẬT KHẨU**! Mật khẩu vẫn là mật khẩu cũ. Pass mới ghi vào Excel là pass rác/ảo làm mất dấu tài khoản.

## 2. Invariant Gate Bắt Buộc Verify Đổi Mật Khẩu Microsoft (3-Step Isolation Gate)
CẤM TUYỆT ĐỐI tin vào trang redirect hay exit code của form submit. Muốn kết luận `CHANGE_PASSWORD_SUCCESS`, bắt buộc phải trải qua quy trình xác minh cách ly:
1. **Bước 1 — Xóa sạch toàn bộ Session & Cookies**:
   ```python
   context.clear_cookies()
   page.goto("https://login.live.com/logout.srf", wait_until="domcontentloaded")
   ```
2. **Bước 2 — Thử đăng nhập lại độc lập bằng Mật Khẩu Mới**:
   - Mở `https://login.live.com/login.srf`.
   - Nhập email -> Enter.
   - Điền **MẬT KHẨU MỚI** vừa đổi -> Enter.
3. **Bước 3 — Đối soát kết quả thực tế qua OCR / URL**:
   - Nếu Microsoft báo lỗi *"Mật khẩu đó không đúng với tài khoản Microsoft của bạn"* -> **ĐỔI PASS THẤT BẠI 100%**. Revert ngay, không ghi Excel, không đổi state.
   - Chỉ khi Microsoft chấp nhận mật khẩu mới và vào được Dashboard/KMSI ("Duy trì đăng nhập") -> Mới được phép ghi nhận thành công vào Excel Cột G và state tracker.

## 3. Microsoft Yêu Cầu OTP Hòm Thư ("Verify your email") Khi Đổi Pass
- Khi vào `account.live.com/password/change`, Microsoft thường yêu cầu xác minh bảo mật cấp 2:
  - Màn hình: *"Verify your email. We'll send a code to mu*****@hotmail.com. To verify this is your email, enter it here."*
  - Yêu cầu nhập lại địa chỉ email đầy đủ -> Bấm `Send code` -> Nhận mã OTP 7 chữ số gửi về chính hòm thư Hotmail/Outlook đó.
- Không thể bypass màn hình này nếu không có handler đọc OTP từ hòm thư qua Graph API / IMAP / Web Outlook.
- Nếu không có luồng lấy OTP, việc cố submit form shortcut sẽ luôn bị Microsoft chặn hoặc từ chối âm thầm.

## 4. Xung đột ghi đè đồng thời File Excel khi chạy nhiều Worker
- Khi chạy song song nhiều worker (ví dụ 5 worker GPM), nếu các worker cùng lúc mở và `wb.save(WORKBOOK_PATH)` vào file `taikhoan_dat_v2_updated .xlsx`:
  - Cấu trúc file zip của `.xlsx` bị hỏng (`Bad CRC-32`, `Bad magic number`).
- **Khắc phục bắt buộc**:
  - Dùng `msvcrt.locking` hoặc `filelock` tạo Exclusive Lock trước khi `load_workbook` và giải phóng sau khi `wb.save()`.
  - Giữ bản backup định kỳ `.bak` để restore tức thì khi có sự cố.
